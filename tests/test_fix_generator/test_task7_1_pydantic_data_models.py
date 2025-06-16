"""
Unit tests for Task 7.1: Pydantic Data Models

Tests all Pydantic BaseModel classes for type-safe structured output,
validation, JSON schema generation, and LangChain integration compatibility.
"""

import pytest
from datetime import datetime
from decimal import Decimal
from typing import Dict, Any
from uuid import uuid4

from pydantic import ValidationError
import json

from src.fix_generator.data_models import (
    # Enums
    DefectSeverity, FixComplexity, ConfidenceLevel, ProviderType, 
    FixType, StyleGuideType,
    # Core Models
    NIMMetadata, FixCandidate, StyleAnalysisResult, DefectAnalysisResult,
    GenerationStatistics,
    # Utilities
    get_defect_analysis_schema, get_style_analysis_schema, get_fix_candidate_schema,
    validate_confidence_score, create_sample_defect_analysis
)


class TestEnums:
    """Test all enum classes."""
    
    def test_defect_severity_enum(self):
        """Test DefectSeverity enum values."""
        assert DefectSeverity.CRITICAL == "critical"
        assert DefectSeverity.HIGH == "high"
        assert DefectSeverity.MEDIUM == "medium"
        assert DefectSeverity.LOW == "low"
        assert DefectSeverity.INFO == "info"
    
    def test_fix_complexity_enum(self):
        """Test FixComplexity enum values."""
        assert FixComplexity.SIMPLE == "simple"
        assert FixComplexity.MODERATE == "moderate"
        assert FixComplexity.COMPLEX == "complex"
        assert FixComplexity.EXPERIMENTAL == "experimental"
    
    def test_confidence_level_enum(self):
        """Test ConfidenceLevel enum values."""
        assert ConfidenceLevel.VERY_LOW == "very_low"
        assert ConfidenceLevel.LOW == "low"
        assert ConfidenceLevel.MEDIUM == "medium"
        assert ConfidenceLevel.HIGH == "high"
        assert ConfidenceLevel.VERY_HIGH == "very_high"
    
    def test_provider_type_enum(self):
        """Test ProviderType enum values."""
        assert ProviderType.NVIDIA_NIM == "nvidia_nim"
        assert ProviderType.OPENAI == "openai"
        assert ProviderType.ANTHROPIC == "anthropic"
        assert ProviderType.LOCAL == "local"


class TestNIMMetadata:
    """Test NIMMetadata Pydantic model."""
    
    def test_valid_nim_metadata_creation(self):
        """Test creating valid NIMMetadata."""
        metadata = NIMMetadata(
            model_used="nvidia/llama-3.3-nemotron-super-49b-v1",
            tokens_consumed=1500,
            generation_time=2.5,
            provider_used=ProviderType.NVIDIA_NIM,
            input_tokens=800,
            output_tokens=700,
            api_cost=Decimal('0.045')
        )
        
        assert metadata.model_used == "nvidia/llama-3.3-nemotron-super-49b-v1"
        assert metadata.tokens_consumed == 1500
        assert metadata.generation_time == 2.5
        assert metadata.provider_used == ProviderType.NVIDIA_NIM
        assert metadata.input_tokens == 800
        assert metadata.output_tokens == 700
        assert metadata.api_cost == Decimal('0.045')
        assert metadata.tokens_per_second == 600.0  # 1500 / 2.5
    
    def test_nim_metadata_auto_calculation(self):
        """Test automatic calculation of output tokens and tokens_per_second."""
        metadata = NIMMetadata(
            model_used="test-model",
            tokens_consumed=1000,
            generation_time=2.0,
            provider_used=ProviderType.NVIDIA_NIM,
            input_tokens=400
            # output_tokens not provided - should be auto-calculated
        )
        
        assert metadata.output_tokens == 600  # 1000 - 400
        assert metadata.tokens_per_second == 500.0  # 1000 / 2.0
    
    def test_nim_metadata_validation_errors(self):
        """Test validation errors for invalid data."""
        # Test negative tokens
        with pytest.raises(ValidationError) as exc_info:
            NIMMetadata(
                model_used="test-model",
                tokens_consumed=-100,
                generation_time=1.0,
                provider_used=ProviderType.NVIDIA_NIM
            )
        assert "Input should be greater than 0" in str(exc_info.value)
        
        # Test token mismatch
        with pytest.raises(ValidationError) as exc_info:
            NIMMetadata(
                model_used="test-model",
                tokens_consumed=1000,
                generation_time=1.0,
                provider_used=ProviderType.NVIDIA_NIM,
                input_tokens=400,
                output_tokens=700  # Should be 600
            )
        assert "Token mismatch" in str(exc_info.value)
    
    def test_nim_metadata_json_serialization(self):
        """Test JSON serialization of NIMMetadata."""
        metadata = NIMMetadata(
            model_used="test-model",
            tokens_consumed=1000,
            generation_time=2.0,
            provider_used=ProviderType.NVIDIA_NIM
        )
        
        json_data = metadata.model_dump()
        assert json_data["model_used"] == "test-model"
        assert json_data["tokens_consumed"] == 1000
        assert json_data["provider_used"] == "nvidia_nim"


class TestFixCandidate:
    """Test FixCandidate Pydantic model."""
    
    def test_valid_fix_candidate_creation(self):
        """Test creating valid FixCandidate."""
        fix = FixCandidate(
            file_path="/path/to/file.cpp",
            original_code="char* ptr = nullptr;\n*ptr = 'x';",
            fixed_code="char* ptr = nullptr;\nif (ptr != nullptr) {\n    *ptr = 'x';\n}",
            explanation="Added null pointer check before dereferencing",
            confidence_score=0.85,
            complexity=FixComplexity.SIMPLE,
            line_start=42,
            line_end=43,
            estimated_risk=0.1
        )
        
        assert fix.file_path == "/path/to/file.cpp"
        assert fix.confidence_score == 0.85
        assert fix.confidence_level == ConfidenceLevel.HIGH
        assert fix.lines_affected == 2  # 43 - 42 + 1
        assert fix.fix_type == FixType.CODE_FIX
        assert isinstance(fix.fix_id, str)
    
    def test_fix_candidate_validation_errors(self):
        """Test validation errors for invalid fix candidates."""
        # Test invalid confidence score
        with pytest.raises(ValidationError) as exc_info:
            FixCandidate(
                file_path="/path/to/file.cpp",
                original_code="code",
                fixed_code="fixed code",
                explanation="explanation",
                confidence_score=1.5,  # Invalid: > 1.0
                complexity=FixComplexity.SIMPLE,
                line_start=1,
                line_end=2
            )
        assert "Input should be less than or equal to 1" in str(exc_info.value)
        
        # Test invalid line range
        with pytest.raises(ValidationError) as exc_info:
            FixCandidate(
                file_path="/path/to/file.cpp",
                original_code="code",
                fixed_code="fixed code",
                explanation="explanation",
                confidence_score=0.8,
                complexity=FixComplexity.SIMPLE,
                line_start=10,
                line_end=5  # Invalid: end < start
            )
        assert "line_end must be >= line_start" in str(exc_info.value)
        
        # Test empty explanation
        with pytest.raises(ValidationError) as exc_info:
            FixCandidate(
                file_path="/path/to/file.cpp",
                original_code="code",
                fixed_code="fixed code",
                explanation="short",  # Too short (< 10 chars)
                confidence_score=0.8,
                complexity=FixComplexity.SIMPLE,
                line_start=1,
                line_end=2
            )
        assert "String should have at least 10 characters" in str(exc_info.value)
    
    def test_confidence_level_property(self):
        """Test confidence level property calculation."""
        test_cases = [
            (0.95, ConfidenceLevel.VERY_HIGH),
            (0.85, ConfidenceLevel.HIGH),
            (0.65, ConfidenceLevel.MEDIUM),
            (0.45, ConfidenceLevel.LOW),
            (0.15, ConfidenceLevel.VERY_LOW)
        ]
        
        for score, expected_level in test_cases:
            fix = FixCandidate(
                file_path="/test.cpp",
                original_code="test code",
                fixed_code="fixed test code",
                explanation="test explanation",
                confidence_score=score,
                complexity=FixComplexity.SIMPLE,
                line_start=1,
                line_end=1
            )
            assert fix.confidence_level == expected_level


class TestStyleAnalysisResult:
    """Test StyleAnalysisResult Pydantic model."""
    
    def test_valid_style_analysis_creation(self):
        """Test creating valid StyleAnalysisResult."""
        detected_style = {
            "indentation_type": "spaces",
            "indentation_width": 4,
            "brace_style": "K&R"
        }
        
        style_analysis = StyleAnalysisResult(
            detected_style=detected_style,
            consistency_score=0.85,
            language_detected="cpp",
            style_guide_used=StyleGuideType.GOOGLE_CPP,
            style_violations=[
                {"type": "indentation", "line": 10, "message": "Inconsistent indentation"}
            ],
            recommendations=[
                {"type": "fix", "description": "Use consistent 4-space indentation"}
            ],
            lines_analyzed=100
        )
        
        assert style_analysis.detected_style == detected_style
        assert style_analysis.consistency_score == 0.85
        assert style_analysis.language_detected == "cpp"
        assert style_analysis.has_violations == True
        assert style_analysis.violation_count == 1
        assert style_analysis.lines_analyzed == 100
    
    def test_style_analysis_validation_errors(self):
        """Test validation errors for invalid style analysis."""
        # Test missing required style keys
        with pytest.raises(ValidationError) as exc_info:
            StyleAnalysisResult(
                detected_style={"indentation_type": "spaces"},  # Missing required keys
                consistency_score=0.8,
                language_detected="cpp"
            )
        assert "Missing required style key" in str(exc_info.value)
        
        # Test invalid consistency score
        with pytest.raises(ValidationError) as exc_info:
            StyleAnalysisResult(
                detected_style={
                    "indentation_type": "spaces",
                    "indentation_width": 4,
                    "brace_style": "K&R"
                },
                consistency_score=1.5,  # Invalid: > 1.0
                language_detected="cpp"
            )
        assert "Input should be less than or equal to 1" in str(exc_info.value)


class TestDefectAnalysisResult:
    """Test DefectAnalysisResult Pydantic model."""
    
    def create_valid_fix_candidate(self, file_path: str = "/test/file.cpp") -> FixCandidate:
        """Helper to create valid FixCandidate."""
        return FixCandidate(
            file_path=file_path,
            original_code="test code",
            fixed_code="fixed test code",
            explanation="test fix explanation",
            confidence_score=0.8,
            complexity=FixComplexity.SIMPLE,
            line_start=10,
            line_end=12
        )
    
    def create_valid_nim_metadata(self) -> NIMMetadata:
        """Helper to create valid NIMMetadata."""
        return NIMMetadata(
            model_used="test-model",
            tokens_consumed=1000,
            generation_time=2.0,
            provider_used=ProviderType.NVIDIA_NIM
        )
    
    def test_valid_defect_analysis_creation(self):
        """Test creating valid DefectAnalysisResult."""
        file_path = "/test/file.cpp"
        fix_candidate = self.create_valid_fix_candidate(file_path)
        metadata = self.create_valid_nim_metadata()
        
        result = DefectAnalysisResult(
            defect_id="TEST_001",
            defect_type="NULL_POINTER_DEREFERENCE",
            file_path=file_path,
            line_number=10,
            severity=DefectSeverity.HIGH,
            confidence_level=ConfidenceLevel.HIGH,
            fix_candidates=[fix_candidate],
            metadata=metadata
        )
        
        assert result.defect_id == "TEST_001"
        assert result.defect_type == "NULL_POINTER_DEREFERENCE"
        assert result.file_path == file_path
        assert result.line_number == 10
        assert result.severity == DefectSeverity.HIGH
        assert len(result.fix_candidates) == 1
        assert result.recommended_fix == fix_candidate
        assert result.is_ready_for_application == True
    
    def test_defect_analysis_validation_errors(self):
        """Test validation errors for invalid defect analysis."""
        file_path = "/test/file.cpp"
        fix_candidate = self.create_valid_fix_candidate(file_path)
        metadata = self.create_valid_nim_metadata()
        
        # Test empty fix candidates
        with pytest.raises(ValidationError) as exc_info:
            DefectAnalysisResult(
                defect_id="TEST_001",
                defect_type="NULL_POINTER_DEREFERENCE",
                file_path=file_path,
                line_number=10,
                severity=DefectSeverity.HIGH,
                confidence_level=ConfidenceLevel.HIGH,
                fix_candidates=[],  # Empty list
                metadata=metadata
            )
        assert "List should have at least 1 item" in str(exc_info.value)
        
        # Test invalid recommended fix index
        with pytest.raises(ValidationError) as exc_info:
            DefectAnalysisResult(
                defect_id="TEST_001",
                defect_type="NULL_POINTER_DEREFERENCE",
                file_path=file_path,
                line_number=10,
                severity=DefectSeverity.HIGH,
                confidence_level=ConfidenceLevel.HIGH,
                fix_candidates=[fix_candidate],
                recommended_fix_index=5,  # Invalid: >= len(fix_candidates)
                metadata=metadata
            )
        assert "Recommended fix index 5 >= fix count 1" in str(exc_info.value)
    
    def test_file_path_consistency_validation(self):
        """Test file path consistency validation across fix candidates."""
        file_path = "/test/file.cpp"
        wrong_file_path = "/different/file.cpp"
        fix_candidate = self.create_valid_fix_candidate(wrong_file_path)
        metadata = self.create_valid_nim_metadata()
        
        with pytest.raises(ValidationError) as exc_info:
            DefectAnalysisResult(
                defect_id="TEST_001",
                defect_type="NULL_POINTER_DEREFERENCE",
                file_path=file_path,
                line_number=10,
                severity=DefectSeverity.HIGH,
                confidence_level=ConfidenceLevel.HIGH,
                fix_candidates=[fix_candidate],
                metadata=metadata
            )
        assert "Fix candidate 0 file path mismatch" in str(exc_info.value)
    
    def test_properties_and_methods(self):
        """Test DefectAnalysisResult properties and methods."""
        file_path = "/test/file.cpp"
        
        # Create multiple fix candidates with different confidence scores
        fix1 = self.create_valid_fix_candidate(file_path)
        fix1.confidence_score = 0.9  # High confidence
        
        fix2 = self.create_valid_fix_candidate(file_path)
        fix2.confidence_score = 0.6  # Medium confidence
        
        fix3 = self.create_valid_fix_candidate(file_path)
        fix3.confidence_score = 0.8  # High confidence
        
        metadata = self.create_valid_nim_metadata()
        
        result = DefectAnalysisResult(
            defect_id="TEST_001",
            defect_type="NULL_POINTER_DEREFERENCE",
            file_path=file_path,
            line_number=10,
            severity=DefectSeverity.HIGH,
            confidence_level=ConfidenceLevel.HIGH,
            fix_candidates=[fix1, fix2, fix3],
            recommended_fix_index=0,
            metadata=metadata
        )
        
        # Test high confidence fixes
        high_confidence = result.high_confidence_fixes
        assert len(high_confidence) == 2  # fix1 and fix3
        assert fix1 in high_confidence
        assert fix3 in high_confidence
        
        # Test overall confidence score
        assert 0.0 <= result.overall_confidence_score <= 1.0
        
        # Test summary
        summary = result.get_summary()
        assert summary["defect_id"] == "TEST_001"
        assert summary["num_fix_candidates"] == 3
        assert summary["high_confidence_fixes"] == 2


class TestGenerationStatistics:
    """Test GenerationStatistics Pydantic model."""
    
    def test_generation_statistics_creation(self):
        """Test creating GenerationStatistics."""
        stats = GenerationStatistics()
        assert stats.total_defects_processed == 0
        assert stats.success_rate == 0.0
        assert stats.average_generation_time == 0.0
    
    def test_add_result_functionality(self):
        """Test adding results to statistics."""
        stats = GenerationStatistics()
        
        # Create sample result
        sample_result = create_sample_defect_analysis()
        
        # Add successful result
        stats.add_result(sample_result, success=True)
        
        assert stats.total_defects_processed == 1
        assert stats.successful_generations == 1
        assert stats.failed_generations == 0
        assert stats.success_rate == 1.0
        
        # Add failed result
        stats.add_result(sample_result, success=False)
        
        assert stats.total_defects_processed == 2
        assert stats.successful_generations == 1
        assert stats.failed_generations == 1
        assert stats.success_rate == 0.5


class TestJSONSchemaGeneration:
    """Test JSON schema generation for LangChain integration."""
    
    def test_defect_analysis_schema_generation(self):
        """Test JSON schema generation for DefectAnalysisResult."""
        schema = get_defect_analysis_schema()
        
        assert isinstance(schema, dict)
        assert "properties" in schema
        assert "defect_id" in schema["properties"]
        assert "fix_candidates" in schema["properties"]
        assert "metadata" in schema["properties"]
        
        # Check required fields
        assert "required" in schema
        required_fields = schema["required"]
        assert "defect_id" in required_fields
        assert "defect_type" in required_fields
        assert "fix_candidates" in required_fields
    
    def test_style_analysis_schema_generation(self):
        """Test JSON schema generation for StyleAnalysisResult."""
        schema = get_style_analysis_schema()
        
        assert isinstance(schema, dict)
        assert "properties" in schema
        assert "detected_style" in schema["properties"]
        assert "consistency_score" in schema["properties"]
    
    def test_fix_candidate_schema_generation(self):
        """Test JSON schema generation for FixCandidate."""
        schema = get_fix_candidate_schema()
        
        assert isinstance(schema, dict)
        assert "properties" in schema
        assert "fix_id" in schema["properties"]
        assert "confidence_score" in schema["properties"]


class TestUtilityFunctions:
    """Test utility functions."""
    
    def test_validate_confidence_score(self):
        """Test confidence score validation utility."""
        test_cases = [
            (0.95, ConfidenceLevel.VERY_HIGH),
            (0.85, ConfidenceLevel.HIGH),
            (0.65, ConfidenceLevel.MEDIUM),
            (0.45, ConfidenceLevel.LOW),
            (0.15, ConfidenceLevel.VERY_LOW)
        ]
        
        for score, expected_level in test_cases:
            assert validate_confidence_score(score) == expected_level
    
    def test_create_sample_defect_analysis(self):
        """Test sample defect analysis creation."""
        sample = create_sample_defect_analysis()
        
        assert isinstance(sample, DefectAnalysisResult)
        assert sample.defect_id == "DEFECT_001"
        assert sample.defect_type == "NULL_POINTER_DEREFERENCE"
        assert len(sample.fix_candidates) == 1
        assert sample.is_ready_for_application == True


class TestLangChainIntegration:
    """Test LangChain integration compatibility."""
    
    def test_pydantic_output_parser_compatibility(self):
        """Test compatibility with LangChain PydanticOutputParser."""
        # Test that our models can be serialized/deserialized properly
        sample = create_sample_defect_analysis()
        
        # Serialize to JSON
        json_data = sample.model_dump()
        json_str = json.dumps(json_data, default=str)
        
        # Deserialize back
        parsed_data = json.loads(json_str)
        
        # Validate structure
        assert "defect_id" in parsed_data
        assert "fix_candidates" in parsed_data
        assert "metadata" in parsed_data
        
        # Test schema availability for LangChain
        schema = DefectAnalysisResult.model_json_schema()
        assert "properties" in schema
        assert "required" in schema
    
    def test_model_validation_with_json_input(self):
        """Test model validation with JSON input (LangChain use case)."""
        # Simulate JSON input from LLM
        json_input = {
            "defect_id": "TEST_001",
            "defect_type": "NULL_POINTER_DEREFERENCE",
            "file_path": "/test/file.cpp",
            "line_number": 10,
            "severity": "high",
            "confidence_level": "high",
            "fix_candidates": [
                {
                    "file_path": "/test/file.cpp",
                    "original_code": "char* ptr = nullptr; *ptr = 'x';",
                    "fixed_code": "char* ptr = nullptr; if (ptr) *ptr = 'x';",
                    "explanation": "Added null pointer check",
                    "confidence_score": 0.85,
                    "complexity": "simple",
                    "line_start": 10,
                    "line_end": 11
                }
            ],
            "metadata": {
                "model_used": "test-model",
                "tokens_consumed": 1000,
                "generation_time": 2.0,
                "provider_used": "nvidia_nim"
            }
        }
        
        # This should work with LangChain PydanticOutputParser
        result = DefectAnalysisResult.model_validate(json_input)
        
        assert result.defect_id == "TEST_001"
        assert result.severity == DefectSeverity.HIGH
        assert len(result.fix_candidates) == 1
        assert result.metadata.provider_used == ProviderType.NVIDIA_NIM


# Integration test to verify all components work together
def test_complete_pydantic_integration():
    """Integration test for all Pydantic models working together."""
    # Create metadata
    metadata = NIMMetadata(
        model_used="nvidia/llama-3.3-nemotron-super-49b-v1",
        tokens_consumed=2000,
        generation_time=3.0,
        provider_used=ProviderType.NVIDIA_NIM,
        input_tokens=1000,
        output_tokens=1000,
        api_cost=Decimal('0.06')
    )
    
    # Create fix candidate
    fix_candidate = FixCandidate(
        file_path="/src/example.cpp",
        original_code="int x; printf(\"%d\", x);",
        fixed_code="int x = 0; printf(\"%d\", x);",
        explanation="Initialize variable x to prevent undefined behavior",
        confidence_score=0.92,
        complexity=FixComplexity.SIMPLE,
        line_start=15,
        line_end=16,
        estimated_risk=0.05
    )
    
    # Create style analysis
    style_analysis = StyleAnalysisResult(
        detected_style={
            "indentation_type": "spaces",
            "indentation_width": 4,
            "brace_style": "K&R",
            "naming_convention": "snake_case"
        },
        consistency_score=0.95,
        language_detected="cpp",
        style_guide_used=StyleGuideType.GOOGLE_CPP,
        lines_analyzed=50
    )
    
    # Create comprehensive defect analysis
    result = DefectAnalysisResult(
        defect_id="INTEGRATION_TEST_001",
        defect_type="UNINITIALIZED_VARIABLE",
        file_path="/src/example.cpp",
        line_number=15,
        severity=DefectSeverity.MEDIUM,
        confidence_level=ConfidenceLevel.VERY_HIGH,
        fix_candidates=[fix_candidate],
        metadata=metadata,
        style_analysis=style_analysis,
        reasoning_trace="Variable 'x' is used without initialization, which leads to undefined behavior."
    )
    
    # Test all functionality
    assert result.is_ready_for_application == True
    assert result.overall_confidence_score >= 0.9  # Should be at least 0.9 for a 0.92 confidence fix
    assert len(result.high_confidence_fixes) == 1
    
    # Test JSON serialization for LangChain
    json_data = result.model_dump()
    assert json_data["defect_id"] == "INTEGRATION_TEST_001"
    
    # Test schema generation
    schema = result.model_json_schema()
    assert "properties" in schema
    
    # Test statistics integration
    stats = GenerationStatistics()
    stats.add_result(result, success=True)
    assert stats.success_rate == 1.0
    assert stats.high_confidence_fixes == 1
    
    print("✅ All Pydantic models integration test passed!")


if __name__ == "__main__":
    # Run the integration test
    test_complete_pydantic_integration()
    print("🎉 Task 7.1 Pydantic Data Models implementation successful!") 