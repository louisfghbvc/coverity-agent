"""
Test configuration and fixtures for LLM Fix Generator tests.
"""

import os
import sys
from datetime import datetime
from unittest.mock import Mock, MagicMock
import pytest

# Add src to Python path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from fix_generator.data_structures import (
    DefectAnalysisResult, FixCandidate, NIMMetadata, GenerationStatistics,
    FixComplexity, DefectSeverity, ConfidenceLevel
)
from fix_generator.config import (
    LLMFixGeneratorConfig, NIMProviderConfig, AnalysisConfig, 
    QualityConfig, OptimizationConfig
)
from issue_parser.data_structures import ParsedDefect
from code_retriever.data_structures import CodeContext


@pytest.fixture
def sample_parsed_defect():
    """Create a sample ParsedDefect for testing."""
    return ParsedDefect(
        defect_type="NULL_POINTER_DEREFERENCE",
        file_path="/path/to/test.c", 
        line_number=42,
        function_name="test_function",
        events=["Variable 'ptr' is assigned NULL", "Variable 'ptr' is dereferenced"],
        subcategory="Null pointer dereference",
        defect_id="test_defect_001",
        confidence_score=0.9,
        parsing_timestamp=datetime.utcnow(),
        raw_data={"original": "data"}
    )


@pytest.fixture
def sample_code_context():
    """Create a sample CodeContext for testing."""
    from code_retriever.data_structures import SourceLocation, ContextWindow, FileMetadata
    
    # Create the components
    primary_location = SourceLocation(
        file_path="/path/to/test.c",
        line_number=42,
        column_number=0,
        function_name="test_function"
    )
    
    primary_context = ContextWindow(
        start_line=35,
        end_line=43,
        source_lines=[
            "int test_function(char* input) {",
            "    char* ptr = NULL;",
            "    if (input != NULL) {",
            "        ptr = malloc(strlen(input) + 1);",
            "        strcpy(ptr, input);",
            "    }",
            "    return strlen(ptr);  // Null pointer dereference here",
            "}"
        ],
        highlighted_line=6  # Index of the defect line
    )
    
    file_metadata = FileMetadata(
        file_path="/path/to/test.c",
        file_size=1024,
        encoding="utf-8",
        language="c"
    )
    
    return CodeContext(
        defect_id="test_defect_001",
        defect_type="NULL_POINTER_DEREFERENCE",
        primary_location=primary_location,
        primary_context=primary_context,
        file_metadata=file_metadata,
        language="c"
    )


@pytest.fixture
def sample_fix_candidate():
    """Create a sample FixCandidate for testing."""
    return FixCandidate(
        fix_code="""int test_function(char* input) {
    char* ptr = NULL;
    if (input != NULL) {
        ptr = malloc(strlen(input) + 1);
        strcpy(ptr, input);
        return strlen(ptr);  // Safe now
    }
    return 0;  // Safe default
}""",
        explanation="Added null check before using ptr to prevent null pointer dereference",
        confidence_score=0.85,
        complexity=FixComplexity.SIMPLE,
        risk_assessment="Low risk - adds safety check",
        affected_files=["/path/to/test.c"],
        line_ranges=[{"start": 35, "end": 43}],
        fix_strategy="null_check",
        estimated_effort="5 minutes",
        potential_side_effects=[]
    )


@pytest.fixture
def sample_nim_metadata():
    """Create sample NIM metadata for testing."""
    return NIMMetadata(
        model_used="codellama-13b-instruct",
        tokens_consumed=450,
        generation_time=2.5,
        api_endpoint="https://test-nim-endpoint.com",
        request_id="test-req-123",
        estimated_cost=0.0009
    )


@pytest.fixture
def sample_defect_analysis_result(sample_parsed_defect, sample_fix_candidate, sample_nim_metadata):
    """Create a sample DefectAnalysisResult for testing."""
    return DefectAnalysisResult(
        defect_id=sample_parsed_defect.defect_id,
        defect_type=sample_parsed_defect.defect_type,
        file_path=sample_parsed_defect.file_path,
        line_number=sample_parsed_defect.line_number,
        defect_category="null_pointer_dereference",
        severity_assessment=DefectSeverity.HIGH,
        fix_complexity=FixComplexity.SIMPLE,
        confidence_score=0.85,
        fix_candidates=[sample_fix_candidate],
        recommended_fix_index=0,
        reasoning_trace="Detected null pointer usage without proper checking",
        nim_metadata=sample_nim_metadata,
        style_consistency_score=0.8,
        safety_checks_passed=True,
        validation_errors=[]
    )


@pytest.fixture
def test_config():
    """Create a test configuration for LLM Fix Generator."""
    # Create provider config that skips validation
    provider_config = NIMProviderConfig(
        name="test_nim",
        base_url="https://test-nim-endpoint.com",
        api_key="test-api-key",
        model="test-model",
        max_tokens=1000,
        temperature=0.1,
        timeout=30,
        use_streaming=False  # Disable streaming for tests
    )
    # Skip validation for testing
    provider_config.__dict__['_skip_validation'] = True
    
    return LLMFixGeneratorConfig(
        providers={
            "test_nim": provider_config
        },
        primary_provider="test_nim",
        fallback_providers=[],
        analysis=AnalysisConfig(
            generate_multiple_candidates=True,
            num_candidates=3,
            confidence_threshold=0.6
        ),
        quality=QualityConfig(
            enforce_style_consistency=True,
            validate_syntax=True,
            safety_checks=True
        ),
        optimization=OptimizationConfig(
            cache_similar_defects=False,  # Disable for testing
            enable_performance_tracking=True
        )
    )


@pytest.fixture
def mock_requests_session():
    """Create a mock requests session for NIM API testing."""
    mock_session = Mock()
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "choices": [{
            "message": {
                "content": """{
                    "defect_analysis": {
                        "category": "null_pointer_dereference",
                        "severity": "high",
                        "complexity": "simple",
                        "confidence": 0.85,
                        "root_cause": "Missing null check before pointer usage"
                    },
                    "fix_candidates": [{
                        "fix_code": "if (ptr != NULL) { return strlen(ptr); } else { return 0; }",
                        "explanation": "Added null check to prevent dereference",
                        "confidence": 0.85,
                        "complexity": "simple",
                        "risk_assessment": "Low risk",
                        "affected_files": ["/path/to/test.c"],
                        "line_ranges": [{"start": 42, "end": 42}],
                        "fix_strategy": "null_check"
                    }],
                    "reasoning": "The variable ptr can be NULL and is used without checking"
                }"""
            }
        }],
        "usage": {
            "total_tokens": 450
        }
    }
    
    mock_session.post.return_value = mock_response
    return mock_session


@pytest.fixture
def mock_nim_success_response():
    """Mock successful NIM API response."""
    return {
        "choices": [{
            "message": {
                "content": """{
                    "defect_analysis": {
                        "category": "null_pointer_dereference",
                        "severity": "high", 
                        "complexity": "simple",
                        "confidence": 0.85
                    },
                    "fix_candidates": [{
                        "fix_code": "if (ptr != NULL) return strlen(ptr); return 0;",
                        "explanation": "Added null check",
                        "confidence": 0.85,
                        "complexity": "simple",
                        "risk_assessment": "Low",
                        "affected_files": ["/path/to/test.c"],
                        "line_ranges": [{"start": 42, "end": 42}]
                    }],
                    "reasoning": "Added safety check"
                }"""
            }
        }],
        "usage": {"total_tokens": 450}
    }


@pytest.fixture
def mock_nim_error_response():
    """Mock error NIM API response."""
    return {
        "error": {
            "message": "Rate limit exceeded",
            "type": "rate_limit_error"
        }
    } 