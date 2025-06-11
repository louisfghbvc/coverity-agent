"""
Unit tests for LLM response parser and validator.
"""

import json
import pytest

from fix_generator.response_parser import (
    LLMResponseParser, ResponseValidator, ParsedResponse
)
from fix_generator.data_structures import FixComplexity


class TestResponseValidator:
    """Test ResponseValidator class."""
    
    def test_validate_defect_analysis_valid(self):
        """Test validating valid defect analysis."""
        analysis = {
            "category": "null_pointer_dereference",
            "severity": "high",
            "complexity": "simple",
            "confidence": 0.85,
            "root_cause": "Missing null check"
        }
        
        errors = ResponseValidator.validate_defect_analysis(analysis)
        assert len(errors) == 0
    
    def test_validate_defect_analysis_missing_fields(self):
        """Test validation with missing required fields."""
        analysis = {
            "category": "null_pointer_dereference",
            # Missing severity, complexity, confidence
        }
        
        errors = ResponseValidator.validate_defect_analysis(analysis)
        assert len(errors) == 3
        assert any("Missing required field" in error for error in errors)
    
    def test_validate_defect_analysis_invalid_confidence(self):
        """Test validation with invalid confidence score."""
        analysis = {
            "category": "test",
            "severity": "high", 
            "complexity": "simple",
            "confidence": 1.5  # Invalid
        }
        
        errors = ResponseValidator.validate_defect_analysis(analysis)
        assert any("Confidence score must be 0.0-1.0" in error for error in errors)
        
        # Test non-numeric confidence
        analysis["confidence"] = "high"
        errors = ResponseValidator.validate_defect_analysis(analysis)
        assert any("Invalid confidence score format" in error for error in errors)
    
    def test_validate_defect_analysis_invalid_severity(self):
        """Test validation with invalid severity."""
        analysis = {
            "category": "test",
            "severity": "invalid_severity",
            "complexity": "simple", 
            "confidence": 0.8
        }
        
        errors = ResponseValidator.validate_defect_analysis(analysis)
        assert any("Invalid severity" in error for error in errors)
    
    def test_validate_defect_analysis_invalid_complexity(self):
        """Test validation with invalid complexity."""
        analysis = {
            "category": "test",
            "severity": "high",
            "complexity": "invalid_complexity",
            "confidence": 0.8
        }
        
        errors = ResponseValidator.validate_defect_analysis(analysis)
        assert any("Invalid complexity" in error for error in errors)
    
    def test_validate_fix_candidate_valid(self):
        """Test validating valid fix candidate."""
        candidate = {
            "fix_code": "if (ptr) return strlen(ptr); return 0;",
            "explanation": "Added null check",
            "confidence": 0.85,
            "complexity": "simple",
            "risk_assessment": "Low risk",
            "affected_files": ["/path/to/test.c"],
            "line_ranges": [{"start": 42, "end": 42}]
        }
        
        errors = ResponseValidator.validate_fix_candidate(candidate, 0)
        assert len(errors) == 0
    
    def test_validate_fix_candidate_missing_fields(self):
        """Test validation with missing required fields."""
        candidate = {
            "fix_code": "test code",
            # Missing explanation and confidence
        }
        
        errors = ResponseValidator.validate_fix_candidate(candidate, 0)
        assert len(errors) >= 2
        assert any("missing required field" in error for error in errors)
    
    def test_validate_fix_candidate_empty_fields(self):
        """Test validation with empty required fields."""
        candidate = {
            "fix_code": "",  # Empty
            "explanation": "",  # Empty
            "confidence": 0.8
        }
        
        errors = ResponseValidator.validate_fix_candidate(candidate, 0)
        assert len(errors) >= 2
        assert any("has empty fix_code" in error for error in errors)
        assert any("has empty explanation" in error for error in errors)
    
    def test_validate_fix_candidate_invalid_confidence(self):
        """Test validation with invalid confidence."""
        candidate = {
            "fix_code": "test",
            "explanation": "test",
            "confidence": 2.0  # Invalid
        }
        
        errors = ResponseValidator.validate_fix_candidate(candidate, 0)
        assert any("confidence must be 0.0-1.0" in error for error in errors)
    
    def test_validate_fix_candidate_invalid_line_ranges(self):
        """Test validation with invalid line ranges."""
        candidate = {
            "fix_code": "test",
            "explanation": "test", 
            "confidence": 0.8,
            "line_ranges": [{"start": 50, "end": 40}]  # start > end
        }
        
        errors = ResponseValidator.validate_fix_candidate(candidate, 0)
        assert any("start > end" in error for error in errors)
        
        # Test negative line numbers
        candidate["line_ranges"] = [{"start": -5, "end": 10}]
        errors = ResponseValidator.validate_fix_candidate(candidate, 0)
        assert any("must be positive" in error for error in errors)
    
    def test_validate_syntax_c_code(self):
        """Test C code syntax validation."""
        # Valid C code
        valid_code = """
        if (ptr != NULL) {
            return strlen(ptr);
        }
        return 0;
        """
        
        is_valid, errors = ResponseValidator.validate_syntax(valid_code, "c")
        assert is_valid is True
        assert len(errors) == 0
        
        # Invalid C code - mismatched braces
        invalid_code = """
        if (ptr != NULL) {
            return strlen(ptr);
        // Missing closing brace
        return 0;
        """
        
        is_valid, errors = ResponseValidator.validate_syntax(invalid_code, "c")
        assert is_valid is False
        assert any("Mismatched braces" in error for error in errors)
        
        # Invalid C code - mismatched parentheses
        invalid_code2 = """
        if (ptr != NULL {
            return strlen(ptr);
        }
        """
        
        is_valid, errors = ResponseValidator.validate_syntax(invalid_code2, "c")
        assert is_valid is False
        assert any("Mismatched parentheses" in error for error in errors)
    
    def test_validate_syntax_empty_code(self):
        """Test syntax validation with empty code."""
        is_valid, errors = ResponseValidator.validate_syntax("", "c")
        assert is_valid is False
        assert "Empty code" in errors[0]


class TestLLMResponseParser:
    """Test LLMResponseParser class."""
    
    def test_parser_creation(self):
        """Test creating LLMResponseParser."""
        parser = LLMResponseParser(enable_validation=True)
        assert parser.enable_validation is True
        
        parser = LLMResponseParser(enable_validation=False)
        assert parser.enable_validation is False
    
    def test_parse_json_response_valid(self, sample_parsed_defect):
        """Test parsing valid JSON response."""
        response_data = {
            "defect_analysis": {
                "category": "null_pointer_dereference",
                "severity": "high",
                "complexity": "simple",
                "confidence": 0.85
            },
            "fix_candidates": [{
                "fix_code": "if (ptr) return strlen(ptr); return 0;",
                "explanation": "Added null check",
                "confidence": 0.85,
                "complexity": "simple",
                "risk_assessment": "Low",
                "affected_files": ["/path/to/test.c"],
                "line_ranges": [{"start": 42, "end": 42}]
            }],
            "reasoning": "Added safety check for null pointer"
        }
        
        raw_response = json.dumps(response_data)
        parser = LLMResponseParser()
        
        parsed = parser.parse_response(raw_response, sample_parsed_defect)
        
        assert isinstance(parsed, ParsedResponse)
        assert parsed.defect_analysis["category"] == "null_pointer_dereference"
        assert len(parsed.fix_candidates) == 1
        assert parsed.confidence_score == 0.85
        assert len(parsed.parsing_errors) == 0
    
    def test_parse_markdown_json_response(self, sample_parsed_defect):
        """Test parsing JSON embedded in markdown."""
        raw_response = """
        Here's the analysis:
        
        ```json
        {
            "defect_analysis": {
                "category": "null_pointer_dereference",
                "severity": "high",
                "complexity": "simple",
                "confidence": 0.85
            },
            "fix_candidates": [{
                "fix_code": "if (ptr) return strlen(ptr); return 0;",
                "explanation": "Added null check",
                "confidence": 0.85
            }],
            "reasoning": "Safety check needed"
        }
        ```
        """
        
        parser = LLMResponseParser()
        parsed = parser.parse_response(raw_response, sample_parsed_defect)
        
        assert isinstance(parsed, ParsedResponse)
        assert parsed.defect_analysis["category"] == "null_pointer_dereference"
        assert len(parsed.fix_candidates) == 1
    
    def test_parse_structured_text_response(self, sample_parsed_defect):
        """Test parsing structured text response."""
        raw_response = """
        DEFECT ANALYSIS:
        Category: null_pointer_dereference
        Severity: high
        Complexity: simple
        Confidence: 0.85
        
        FIX CANDIDATE 1:
        Explanation: Added null check to prevent dereference
        Confidence: 0.85
        ```c
        if (ptr != NULL) {
            return strlen(ptr);
        }
        return 0;
        ```
        
        REASONING:
        The pointer needs to be checked before use to prevent crashes.
        """
        
        parser = LLMResponseParser()
        parsed = parser.parse_response(raw_response, sample_parsed_defect)
        
        assert isinstance(parsed, ParsedResponse)
        assert parsed.defect_analysis.get("category") == "null_pointer_dereference"
        assert len(parsed.fix_candidates) >= 1
        assert "if (ptr != NULL)" in parsed.fix_candidates[0]["fix_code"]
    
    def test_parse_fallback_response(self, sample_parsed_defect):
        """Test fallback parsing for unstructured response."""
        raw_response = """
        This is an unstructured response that doesn't match any format.
        
        ```c
        if (ptr != NULL) {
            return strlen(ptr);
        }
        return 0;
        ```
        
        Some explanation text here.
        """
        
        parser = LLMResponseParser()
        parsed = parser.parse_response(raw_response, sample_parsed_defect)
        
        assert isinstance(parsed, ParsedResponse)
        assert len(parsed.fix_candidates) >= 1
        assert "if (ptr != NULL)" in parsed.fix_candidates[0]["fix_code"]
        assert "Fallback extraction" in parsed.fix_candidates[0]["explanation"]
        assert len(parsed.parsing_errors) > 0  # Should have parsing errors
    
    def test_parse_response_no_code_blocks(self, sample_parsed_defect):
        """Test parsing response with no code blocks."""
        raw_response = "This response has no code blocks or structured content."
        
        parser = LLMResponseParser()
        parsed = parser.parse_response(raw_response, sample_parsed_defect)
        
        assert isinstance(parsed, ParsedResponse)
        assert len(parsed.fix_candidates) == 1  # Should create fallback candidate
        assert "No code extracted" in parsed.fix_candidates[0]["fix_code"]
        assert parsed.confidence_score == 0.1  # Low confidence
    
    def test_parse_response_with_validation_disabled(self, sample_parsed_defect):
        """Test parsing with validation disabled."""
        response_data = {
            "defect_analysis": {
                "category": "test",
                "confidence": 2.0  # Invalid confidence (>1.0)
            },
            "fix_candidates": [{
                "fix_code": "",  # Empty code
                "explanation": "test",
                "confidence": 0.8
            }]
        }
        
        raw_response = json.dumps(response_data)
        parser = LLMResponseParser(enable_validation=False)
        
        parsed = parser.parse_response(raw_response, sample_parsed_defect)
        
        # Should parse without validation errors
        assert isinstance(parsed, ParsedResponse)
        assert len(parsed.parsing_errors) == 0
    
    def test_parse_invalid_json(self, sample_parsed_defect):
        """Test parsing invalid JSON."""
        raw_response = '{"invalid": json syntax}'
        
        parser = LLMResponseParser()
        parsed = parser.parse_response(raw_response, sample_parsed_defect)
        
        # Should fall back to other parsing strategies
        assert isinstance(parsed, ParsedResponse)
        assert len(parsed.parsing_errors) > 0


class TestParsedResponse:
    """Test ParsedResponse data structure."""
    
    def test_parsed_response_creation(self):
        """Test creating ParsedResponse."""
        response = ParsedResponse(
            defect_analysis={"category": "test"},
            fix_candidates=[{"fix_code": "test", "explanation": "test", "confidence": 0.8}],
            reasoning="test reasoning",
            confidence_score=0.8,
            parsing_errors=[],
            raw_response="raw response"
        )
        
        assert response.defect_analysis["category"] == "test"
        assert len(response.fix_candidates) == 1
        assert response.confidence_score == 0.8
        assert response.raw_response == "raw response"


class TestResponseParserIntegration:
    """Integration tests for response parser."""
    
    def test_end_to_end_parsing_workflow(self, sample_parsed_defect):
        """Test complete parsing workflow from various response formats."""
        parser = LLMResponseParser()
        
        # Test different response formats
        test_cases = [
            # Direct JSON
            json.dumps({
                "defect_analysis": {"category": "test", "severity": "high", "complexity": "simple", "confidence": 0.8},
                "fix_candidates": [{"fix_code": "test", "explanation": "test", "confidence": 0.8}]
            }),
            
            # Markdown with JSON
            f"""```json
            {json.dumps({
                "defect_analysis": {"category": "test", "severity": "high", "complexity": "simple", "confidence": 0.8},
                "fix_candidates": [{"fix_code": "test", "explanation": "test", "confidence": 0.8}]
            })}
            ```""",
            
            # Structured text
            """
            DEFECT ANALYSIS:
            Category: test
            Severity: high
            Confidence: 0.8
            
            FIX CANDIDATE:
            Explanation: test fix
            Confidence: 0.8
            if (test) { return; }
            """,
            
            # Fallback case
            """
            Some unstructured response with code:
            ```c
            if (test) { return; }
            ```
            """
        ]
        
        for i, response in enumerate(test_cases):
            parsed = parser.parse_response(response, sample_parsed_defect)
            
            assert isinstance(parsed, ParsedResponse)
            assert len(parsed.fix_candidates) >= 1
            
            # First two should have minimal parsing errors
            if i < 2:
                assert len(parsed.parsing_errors) == 0
            
            # All should have some confidence score
            assert 0.0 <= parsed.confidence_score <= 1.0 