"""
Unit tests for LLM Fix Generator data structures.
"""

import pytest
from datetime import datetime

from fix_generator.data_structures import (
    DefectAnalysisResult, FixCandidate, NIMMetadata, GenerationStatistics,
    FixComplexity, DefectSeverity, ConfidenceLevel
)


class TestFixCandidate:
    """Test FixCandidate data structure."""
    
    def test_fix_candidate_creation(self, sample_fix_candidate):
        """Test creating a valid FixCandidate."""
        assert sample_fix_candidate.confidence_score == 0.85
        assert sample_fix_candidate.complexity == FixComplexity.SIMPLE
        assert sample_fix_candidate.confidence_level == ConfidenceLevel.HIGH
        assert len(sample_fix_candidate.affected_files) == 1
        assert sample_fix_candidate.affected_files[0] == "/path/to/test.c"
    
    def test_fix_candidate_validation(self):
        """Test FixCandidate validation."""
        # Test invalid confidence score
        with pytest.raises(ValueError, match="Confidence score must be 0.0-1.0"):
            FixCandidate(
                fix_code="test code",
                explanation="test explanation",
                confidence_score=1.5,  # Invalid
                complexity=FixComplexity.SIMPLE,
                risk_assessment="low",
                affected_files=["test.c"],
                line_ranges=[{"start": 1, "end": 2}]
            )
        
        # Test empty fix code
        with pytest.raises(ValueError, match="Fix code cannot be empty"):
            FixCandidate(
                fix_code="",  # Invalid
                explanation="test explanation",
                confidence_score=0.8,
                complexity=FixComplexity.SIMPLE,
                risk_assessment="low",
                affected_files=["test.c"],
                line_ranges=[{"start": 1, "end": 2}]
            )
        
        # Test empty explanation
        with pytest.raises(ValueError, match="Fix explanation cannot be empty"):
            FixCandidate(
                fix_code="test code",
                explanation="",  # Invalid
                confidence_score=0.8,
                complexity=FixComplexity.SIMPLE,
                risk_assessment="low",
                affected_files=["test.c"],
                line_ranges=[{"start": 1, "end": 2}]
            )
    
    def test_confidence_level_mapping(self):
        """Test confidence level enum mapping."""
        # Very high confidence
        candidate = FixCandidate(
            fix_code="test", explanation="test", confidence_score=0.95,
            complexity=FixComplexity.SIMPLE, risk_assessment="low",
            affected_files=["test.c"], line_ranges=[]
        )
        assert candidate.confidence_level == ConfidenceLevel.VERY_HIGH
        
        # High confidence
        candidate.confidence_score = 0.8
        assert candidate.confidence_level == ConfidenceLevel.HIGH
        
        # Medium confidence
        candidate.confidence_score = 0.6
        assert candidate.confidence_level == ConfidenceLevel.MEDIUM
        
        # Low confidence
        candidate.confidence_score = 0.4
        assert candidate.confidence_level == ConfidenceLevel.LOW
        
        # Very low confidence
        candidate.confidence_score = 0.2
        assert candidate.confidence_level == ConfidenceLevel.VERY_LOW
    
    def test_to_dict(self, sample_fix_candidate):
        """Test FixCandidate serialization to dictionary."""
        result = sample_fix_candidate.to_dict()
        
        assert result["confidence_score"] == 0.85
        assert result["confidence_level"] == "high"
        assert result["complexity"] == "simple"
        assert result["fix_strategy"] == "null_check"
        assert "fix_code" in result
        assert "explanation" in result


class TestNIMMetadata:
    """Test NIMMetadata data structure."""
    
    def test_nim_metadata_creation(self, sample_nim_metadata):
        """Test creating NIMMetadata."""
        assert sample_nim_metadata.model_used == "codellama-13b-instruct"
        assert sample_nim_metadata.tokens_consumed == 450
        assert sample_nim_metadata.generation_time == 2.5
        assert sample_nim_metadata.tokens_per_second == 180.0  # 450/2.5
    
    def test_tokens_per_second_calculation(self):
        """Test tokens per second calculation."""
        metadata = NIMMetadata(
            model_used="test-model",
            tokens_consumed=100,
            generation_time=2.0,
            api_endpoint="test-endpoint"
        )
        assert metadata.tokens_per_second == 50.0
        
        # Test zero generation time
        metadata = NIMMetadata(
            model_used="test-model",
            tokens_consumed=100,
            generation_time=0.0,
            api_endpoint="test-endpoint"
        )
        assert metadata.tokens_per_second == 0.0
    
    def test_to_dict(self, sample_nim_metadata):
        """Test NIMMetadata serialization."""
        result = sample_nim_metadata.to_dict()
        
        assert result["model_used"] == "codellama-13b-instruct"
        assert result["tokens_consumed"] == 450
        assert result["generation_time"] == 2.5
        assert result["tokens_per_second"] == 180.0
        assert result["estimated_cost"] == 0.0009


class TestDefectAnalysisResult:
    """Test DefectAnalysisResult data structure."""
    
    def test_defect_analysis_result_creation(self, sample_defect_analysis_result):
        """Test creating DefectAnalysisResult."""
        assert sample_defect_analysis_result.defect_id == "test_defect_001"
        assert sample_defect_analysis_result.severity_assessment == DefectSeverity.HIGH
        assert sample_defect_analysis_result.fix_complexity == FixComplexity.SIMPLE
        assert len(sample_defect_analysis_result.fix_candidates) == 1
        assert sample_defect_analysis_result.recommended_fix_index == 0
    
    def test_defect_analysis_result_validation(self, sample_fix_candidate):
        """Test DefectAnalysisResult validation."""
        # Test invalid confidence score
        with pytest.raises(ValueError, match="Confidence score must be 0.0-1.0"):
            DefectAnalysisResult(
                defect_id="test",
                defect_type="test",
                file_path="test.c",
                line_number=1,
                defect_category="test",
                severity_assessment=DefectSeverity.HIGH,
                fix_complexity=FixComplexity.SIMPLE,
                confidence_score=1.5,  # Invalid
                fix_candidates=[sample_fix_candidate]
            )
        
        # Test empty fix candidates
        with pytest.raises(ValueError, match="At least one fix candidate is required"):
            DefectAnalysisResult(
                defect_id="test",
                defect_type="test",
                file_path="test.c",
                line_number=1,
                defect_category="test",
                severity_assessment=DefectSeverity.HIGH,
                fix_complexity=FixComplexity.SIMPLE,
                confidence_score=0.8,
                fix_candidates=[]  # Invalid
            )
        
        # Test invalid recommended fix index
        with pytest.raises(ValueError, match="Invalid recommended fix index"):
            DefectAnalysisResult(
                defect_id="test",
                defect_type="test",
                file_path="test.c",
                line_number=1,
                defect_category="test",
                severity_assessment=DefectSeverity.HIGH,
                fix_complexity=FixComplexity.SIMPLE,
                confidence_score=0.8,
                fix_candidates=[sample_fix_candidate],
                recommended_fix_index=5  # Invalid - out of range
            )
    
    def test_recommended_fix_property(self, sample_defect_analysis_result):
        """Test recommended_fix property."""
        recommended = sample_defect_analysis_result.recommended_fix
        assert recommended == sample_defect_analysis_result.fix_candidates[0]
        assert recommended.confidence_score == 0.85
    
    def test_high_confidence_fixes_property(self, sample_defect_analysis_result):
        """Test high_confidence_fixes property."""
        high_conf_fixes = sample_defect_analysis_result.high_confidence_fixes
        assert len(high_conf_fixes) == 1  # One fix with confidence 0.85 >= 0.7
        
        # Add a low confidence fix
        low_conf_fix = FixCandidate(
            fix_code="test", explanation="test", confidence_score=0.5,
            complexity=FixComplexity.SIMPLE, risk_assessment="medium",
            affected_files=["test.c"], line_ranges=[]
        )
        sample_defect_analysis_result.fix_candidates.append(low_conf_fix)
        
        high_conf_fixes = sample_defect_analysis_result.high_confidence_fixes
        assert len(high_conf_fixes) == 1  # Still only one high confidence fix
    
    def test_is_ready_for_application(self, sample_defect_analysis_result):
        """Test is_ready_for_application property."""
        # Should be ready with default values
        assert sample_defect_analysis_result.is_ready_for_application is True
        
        # Test with validation errors
        sample_defect_analysis_result.validation_errors = ["Test error"]
        assert sample_defect_analysis_result.is_ready_for_application is False
        
        # Reset and test with low confidence
        sample_defect_analysis_result.validation_errors = []
        sample_defect_analysis_result.fix_candidates[0].confidence_score = 0.3
        assert sample_defect_analysis_result.is_ready_for_application is False
        
        # Reset and test with low style score
        sample_defect_analysis_result.fix_candidates[0].confidence_score = 0.8
        sample_defect_analysis_result.style_consistency_score = 0.4
        assert sample_defect_analysis_result.is_ready_for_application is False
    
    def test_get_analysis_summary(self, sample_defect_analysis_result):
        """Test get_analysis_summary method."""
        summary = sample_defect_analysis_result.get_analysis_summary()
        
        assert summary["defect_id"] == "test_defect_001"
        assert summary["defect_type"] == "NULL_POINTER_DEREFERENCE"
        assert summary["location"] == "/path/to/test.c:42"
        assert summary["severity"] == "high"
        assert summary["complexity"] == "simple"
        assert summary["num_candidates"] == 1
        assert summary["ready_for_application"] is True
        assert "analysis_timestamp" in summary
    
    def test_to_dict(self, sample_defect_analysis_result):
        """Test DefectAnalysisResult serialization."""
        result = sample_defect_analysis_result.to_dict()
        
        assert result["defect_id"] == "test_defect_001"
        assert result["severity_assessment"] == "high"
        assert result["fix_complexity"] == "simple"
        assert len(result["fix_candidates"]) == 1
        assert "analysis_summary" in result
        assert "nim_metadata" in result


class TestGenerationStatistics:
    """Test GenerationStatistics data structure."""
    
    def test_generation_statistics_creation(self):
        """Test creating GenerationStatistics."""
        stats = GenerationStatistics()
        
        assert stats.total_defects_processed == 0
        assert stats.successful_generations == 0
        assert stats.failed_generations == 0
        assert stats.success_rate == 0.0
        assert stats.average_generation_time == 0.0
    
    def test_add_result_success(self, sample_defect_analysis_result):
        """Test adding successful results to statistics."""
        stats = GenerationStatistics()
        
        stats.add_result(sample_defect_analysis_result, success=True)
        
        assert stats.total_defects_processed == 1
        assert stats.successful_generations == 1
        assert stats.failed_generations == 0
        assert stats.success_rate == 1.0
        assert stats.high_confidence_fixes == 1  # confidence 0.85 >= 0.7
        
        # Check NIM metadata integration
        if sample_defect_analysis_result.nim_metadata:
            assert stats.total_tokens_consumed == 450
            assert stats.total_generation_time == 2.5
            assert stats.average_generation_time == 2.5
    
    def test_add_result_failure(self, sample_defect_analysis_result):
        """Test adding failed results to statistics."""
        stats = GenerationStatistics()
        
        stats.add_result(sample_defect_analysis_result, success=False)
        
        assert stats.total_defects_processed == 1
        assert stats.successful_generations == 0
        assert stats.failed_generations == 1
        assert stats.success_rate == 0.0
        assert stats.high_confidence_fixes == 0
    
    def test_multiple_results(self, sample_defect_analysis_result):
        """Test statistics with multiple results."""
        stats = GenerationStatistics()
        
        # Add successful result
        stats.add_result(sample_defect_analysis_result, success=True)
        
        # Add failed result (using same object, but marked as failed)
        stats.add_result(sample_defect_analysis_result, success=False)
        
        assert stats.total_defects_processed == 2
        assert stats.successful_generations == 1
        assert stats.failed_generations == 1
        assert stats.success_rate == 0.5
        
        # Check averages
        assert stats.total_generation_time == 5.0  # 2.5 * 2
        assert stats.average_generation_time == 2.5  # 5.0 / 2
    
    def test_to_dict(self):
        """Test GenerationStatistics serialization."""
        stats = GenerationStatistics()
        stats.total_defects_processed = 5
        stats.successful_generations = 4
        stats.failed_generations = 1
        stats.update_metrics()
        
        result = stats.to_dict()
        
        assert result["total_defects_processed"] == 5
        assert result["successful_generations"] == 4
        assert result["failed_generations"] == 1
        assert result["success_rate"] == 0.8 