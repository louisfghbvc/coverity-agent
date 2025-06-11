"""
Integration tests for LLM Fix Generator.
"""

import json
import tempfile
import pytest
from unittest.mock import Mock, patch, MagicMock
import yaml

from fix_generator import LLMFixGenerator, LLMFixGeneratorConfig, NIMAPIException
from fix_generator.data_structures import DefectAnalysisResult


class TestLLMFixGeneratorInitialization:
    """Test LLMFixGenerator initialization and configuration."""
    
    def test_llm_fix_generator_creation_with_config(self, test_config):
        """Test creating LLMFixGenerator with provided config."""
        generator = LLMFixGenerator(test_config)
        
        assert generator.config == test_config
        assert generator.llm_manager is not None
        assert generator.style_checker is not None
    
    def test_llm_fix_generator_creation_default_config(self):
        """Test creating LLMFixGenerator with default config."""
        # Mock environment variables for default config
        with patch.dict('os.environ', {
            'NIM_API_ENDPOINT': 'https://test-endpoint.com',
            'NIM_API_KEY': 'test-key'
        }):
            generator = LLMFixGenerator()
            
            assert generator.config is not None
            assert generator.config.primary_provider == "nvidia_nim"
            assert len(generator.config.providers) >= 1
    
    def test_llm_fix_generator_environment_validation(self):
        """Test environment validation during initialization."""
        # Create config with missing environment variables
        from fix_generator.config import NIMProviderConfig
        
        invalid_config = LLMFixGeneratorConfig(
            providers={
                "test": NIMProviderConfig(
                    name="test",
                    base_url="${MISSING_URL}",
                    api_key="${MISSING_KEY}",
                    model="test-model"
                )
            },
            primary_provider="test",
            fallback_providers=[]
        )
        
        with pytest.raises(ValueError, match="Configuration errors"):
            LLMFixGenerator(invalid_config)
    
    def test_create_with_config_file(self):
        """Test creating generator from config file."""
        config_data = {
            "llm_fix_generator": {
                "providers": {
                    "primary": "test_nim",
                    "fallback": []
                },
                "providers_config": {
                    "test_nim": {
                        "base_url": "https://test.com",
                        "api_key": "test-key",
                        "model": "test-model"
                    }
                }
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_data, f)
            temp_path = f.name
        
        try:
            generator = LLMFixGenerator.create_with_config_file(temp_path)
            assert generator.config.primary_provider == "test_nim"
        finally:
            import os
            os.unlink(temp_path)
    
    def test_create_default(self):
        """Test creating generator with default configuration."""
        with patch.dict('os.environ', {
            'NIM_API_ENDPOINT': 'https://test-endpoint.com',
            'NIM_API_KEY': 'test-key'
        }):
            generator = LLMFixGenerator.create_default()
            assert isinstance(generator, LLMFixGenerator)


class TestLLMFixGeneratorCore:
    """Test core LLMFixGenerator functionality."""
    
    @patch('fix_generator.llm_manager.UnifiedLLMManager.analyze_defect')
    def test_analyze_and_fix_basic(self, mock_analyze, test_config, 
                                  sample_parsed_defect, sample_code_context,
                                  sample_defect_analysis_result):
        """Test basic analyze_and_fix functionality."""
        mock_analyze.return_value = sample_defect_analysis_result
        
        generator = LLMFixGenerator(test_config)
        result = generator.analyze_and_fix(sample_parsed_defect, sample_code_context)
        
        assert isinstance(result, DefectAnalysisResult)
        assert result.defect_id == sample_parsed_defect.defect_id
        assert len(result.fix_candidates) >= 1
        
        # Verify LLM manager was called
        mock_analyze.assert_called_once_with(sample_parsed_defect, sample_code_context)
    
    @patch('fix_generator.llm_manager.UnifiedLLMManager.analyze_defect')
    def test_analyze_and_fix_with_style_consistency(self, mock_analyze, sample_parsed_defect, 
                                                   sample_code_context, sample_defect_analysis_result):
        """Test analyze_and_fix with style consistency enabled."""
        mock_analyze.return_value = sample_defect_analysis_result
        
        config = LLMFixGeneratorConfig.create_default()
        config.quality.enforce_style_consistency = True
        
        generator = LLMFixGenerator(config)
        
        with patch.object(generator.style_checker, 'check_and_fix_style') as mock_style:
            mock_style.return_value = ("styled_code", 0.8)
            
            result = generator.analyze_and_fix(sample_parsed_defect, sample_code_context)
            
            # Style checker should have been called for each fix candidate
            assert mock_style.call_count == len(result.fix_candidates)
            assert result.style_consistency_score > 0
    
    @patch('fix_generator.llm_manager.UnifiedLLMManager.analyze_defect')
    def test_analyze_and_fix_with_quality_checks(self, mock_analyze, sample_parsed_defect,
                                                sample_code_context, sample_defect_analysis_result):
        """Test analyze_and_fix with quality checks enabled."""
        mock_analyze.return_value = sample_defect_analysis_result
        
        config = LLMFixGeneratorConfig.create_default()
        config.quality.safety_checks = True
        
        generator = LLMFixGenerator(config)
        result = generator.analyze_and_fix(sample_parsed_defect, sample_code_context)
        
        # Quality checks should have been performed
        assert hasattr(result, 'safety_checks_passed')
        assert isinstance(result.validation_errors, list)
    
    @patch('fix_generator.llm_manager.UnifiedLLMManager.analyze_defect')
    def test_analyze_and_fix_api_failure(self, mock_analyze, test_config,
                                        sample_parsed_defect, sample_code_context):
        """Test handling of API failures."""
        mock_analyze.side_effect = NIMAPIException("API failed")
        
        generator = LLMFixGenerator(test_config)
        
        with pytest.raises(NIMAPIException, match="API failed"):
            generator.analyze_and_fix(sample_parsed_defect, sample_code_context)
    
    @patch('fix_generator.llm_manager.UnifiedLLMManager.generate_fix_candidates')
    def test_generate_multiple_fixes(self, mock_generate, test_config,
                                    sample_parsed_defect, sample_code_context,
                                    sample_defect_analysis_result):
        """Test generating multiple fix approaches."""
        mock_generate.return_value = [sample_defect_analysis_result]
        
        generator = LLMFixGenerator(test_config)
        results = generator.generate_multiple_fixes(sample_parsed_defect, sample_code_context, 3)
        
        assert len(results) >= 1
        assert all(isinstance(result, DefectAnalysisResult) for result in results)
        mock_generate.assert_called_once_with(sample_parsed_defect, sample_code_context, 3)


class TestLLMFixGeneratorQualityChecks:
    """Test quality check functionality."""
    
    def test_quality_checks_low_confidence(self, test_config, sample_defect_analysis_result):
        """Test quality checks with low confidence fixes."""
        generator = LLMFixGenerator(test_config)
        
        # Set low confidence
        sample_defect_analysis_result.confidence_score = 0.3
        sample_defect_analysis_result.fix_candidates[0].confidence_score = 0.3
        
        generator._perform_quality_checks(sample_defect_analysis_result)
        
        assert len(sample_defect_analysis_result.validation_errors) > 0
        assert sample_defect_analysis_result.safety_checks_passed is False
        assert any("Low overall confidence" in error for error in sample_defect_analysis_result.validation_errors)
    
    def test_quality_checks_empty_fix_code(self, test_config, sample_defect_analysis_result):
        """Test quality checks with empty fix code."""
        generator = LLMFixGenerator(test_config)
        
        # Set empty fix code
        sample_defect_analysis_result.fix_candidates[0].fix_code = ""
        
        generator._perform_quality_checks(sample_defect_analysis_result)
        
        assert len(sample_defect_analysis_result.validation_errors) > 0
        assert any("has empty code" in error for error in sample_defect_analysis_result.validation_errors)
    
    def test_quality_checks_dangerous_patterns(self, test_config, sample_defect_analysis_result):
        """Test quality checks with dangerous code patterns."""
        generator = LLMFixGenerator(test_config)
        
        # Add dangerous pattern
        sample_defect_analysis_result.fix_candidates[0].fix_code = """
        if (condition) {
            system("rm -rf /");  // Dangerous!
            return 0;
        }
        """
        
        generator._perform_quality_checks(sample_defect_analysis_result)
        
        assert len(sample_defect_analysis_result.validation_errors) > 0
        assert any("dangerous pattern" in error for error in sample_defect_analysis_result.validation_errors)
        
        # Check that potential side effects were added
        fix_candidate = sample_defect_analysis_result.fix_candidates[0]
        assert any("dangerous pattern" in effect for effect in fix_candidate.potential_side_effects)
    
    def test_quality_checks_passing(self, test_config, sample_defect_analysis_result):
        """Test quality checks with good fixes."""
        generator = LLMFixGenerator(test_config)
        
        # Ensure good confidence and safe code
        sample_defect_analysis_result.confidence_score = 0.9
        sample_defect_analysis_result.fix_candidates[0].confidence_score = 0.9
        sample_defect_analysis_result.fix_candidates[0].fix_code = "if (ptr) return strlen(ptr); return 0;"
        
        generator._perform_quality_checks(sample_defect_analysis_result)
        
        assert len(sample_defect_analysis_result.validation_errors) == 0
        assert sample_defect_analysis_result.safety_checks_passed is True


class TestLLMFixGeneratorStatistics:
    """Test statistics tracking functionality."""
    
    def test_get_statistics(self, test_config):
        """Test getting generation statistics."""
        generator = LLMFixGenerator(test_config)
        
        stats = generator.get_statistics()
        
        assert stats.total_defects_processed == 0
        assert stats.successful_generations == 0
        assert stats.success_rate == 0.0
    
    def test_reset_statistics(self, test_config):
        """Test resetting statistics."""
        generator = LLMFixGenerator(test_config)
        
        # Simulate some activity by directly updating internal stats
        generator.llm_manager.statistics.total_defects_processed = 5
        generator.llm_manager.statistics.successful_generations = 4
        
        generator.reset_statistics()
        
        stats = generator.get_statistics()
        assert stats.total_defects_processed == 0
        assert stats.successful_generations == 0


class TestLLMFixGeneratorEndToEnd:
    """End-to-end integration tests."""
    
    @patch('requests.Session.post')
    def test_full_pipeline_mock_nim(self, mock_post, test_config,
                                   sample_parsed_defect, sample_code_context):
        """Test complete pipeline with mocked NIM API."""
        # Setup mock NIM response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{
                "message": {
                    "content": json.dumps({
                        "defect_analysis": {
                            "category": "null_pointer_dereference",
                            "severity": "high",
                            "complexity": "simple",
                            "confidence": 0.85,
                            "root_cause": "Missing null check"
                        },
                        "fix_candidates": [{
                            "fix_code": "if (ptr != NULL) return strlen(ptr); return 0;",
                            "explanation": "Added null check to prevent dereference",
                            "confidence": 0.85,
                            "complexity": "simple",
                            "risk_assessment": "Low risk - adds safety check",
                            "affected_files": ["/path/to/test.c"],
                            "line_ranges": [{"start": 42, "end": 42}],
                            "fix_strategy": "null_check"
                        }],
                        "reasoning": "Pointer needs validation before use"
                    })
                }
            }],
            "usage": {"total_tokens": 450}
        }
        mock_post.return_value = mock_response
        
        generator = LLMFixGenerator(test_config)
        result = generator.analyze_and_fix(sample_parsed_defect, sample_code_context)
        
        # Verify complete result
        assert isinstance(result, DefectAnalysisResult)
        assert result.defect_id == sample_parsed_defect.defect_id
        assert result.defect_category == "null_pointer_dereference"
        assert result.confidence_score == 0.85
        assert len(result.fix_candidates) == 1
        
        fix_candidate = result.fix_candidates[0]
        assert "if (ptr != NULL)" in fix_candidate.fix_code
        assert fix_candidate.confidence_score == 0.85
        assert fix_candidate.fix_strategy == "null_check"
        
        # Verify NIM metadata
        assert result.nim_metadata is not None
        assert result.nim_metadata.tokens_consumed == 450
        
        # Verify statistics were updated
        stats = generator.get_statistics()
        assert stats.total_defects_processed == 1
        assert stats.successful_generations == 1
    
    @patch('requests.Session.post')
    def test_full_pipeline_with_style_and_quality(self, mock_post, sample_parsed_defect, sample_code_context):
        """Test complete pipeline with style consistency and quality checks."""
        # Setup mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{
                "message": {
                    "content": json.dumps({
                        "defect_analysis": {
                            "category": "null_pointer_dereference",
                            "severity": "high",
                            "complexity": "simple",
                            "confidence": 0.85
                        },
                        "fix_candidates": [{
                            "fix_code": "if(ptr!=NULL)return strlen(ptr);return 0;",  # Poor style
                            "explanation": "Added null check",
                            "confidence": 0.85,
                            "complexity": "simple",
                            "risk_assessment": "Low",
                            "affected_files": ["/path/to/test.c"],
                            "line_ranges": [{"start": 42, "end": 42}]
                        }]
                    })
                }
            }],
            "usage": {"total_tokens": 400}
        }
        mock_post.return_value = mock_response
        
        # Create config with quality checks enabled
        config = LLMFixGeneratorConfig.create_default()
        config.quality.enforce_style_consistency = True
        config.quality.safety_checks = True
        
        generator = LLMFixGenerator(config)
        result = generator.analyze_and_fix(sample_parsed_defect, sample_code_context)
        
        # Style should have been improved
        fix_code = result.fix_candidates[0].fix_code
        assert "if (" in fix_code  # Should have space after keyword
        
        # Quality checks should have passed
        assert result.safety_checks_passed is True
        assert result.style_consistency_score > 0.0
    
    def test_error_handling_configuration_errors(self):
        """Test error handling for configuration issues."""
        # Test with completely invalid config
        with pytest.raises(ValueError):
            invalid_config = LLMFixGeneratorConfig(
                providers={},  # Empty providers
                primary_provider="nonexistent",
                fallback_providers=[]
            )
            LLMFixGenerator(invalid_config)
    
    @patch('requests.Session.post')
    def test_provider_fallback_integration(self, mock_post, sample_parsed_defect, sample_code_context):
        """Test provider fallback in integration scenario."""
        from fix_generator.config import NIMProviderConfig
        
        # Create config with primary and fallback providers
        config = LLMFixGeneratorConfig(
            providers={
                "primary": NIMProviderConfig(
                    name="primary", base_url="https://primary.com",
                    api_key="key1", model="model1"
                ),
                "fallback": NIMProviderConfig(
                    name="fallback", base_url="https://fallback.com",
                    api_key="key2", model="model2"
                )
            },
            primary_provider="primary",
            fallback_providers=["fallback"]
        )
        
        # First call fails, second succeeds
        error_response = Mock()
        error_response.status_code = 500
        error_response.text = "Server Error"
        
        success_response = Mock()
        success_response.status_code = 200
        success_response.json.return_value = {
            "choices": [{"message": {"content": '{"defect_analysis": {"category": "test", "severity": "medium", "complexity": "simple", "confidence": 0.7}, "fix_candidates": [{"fix_code": "fallback_fix", "explanation": "Fallback fix", "confidence": 0.7}]}'}}],
            "usage": {"total_tokens": 300}
        }
        
        mock_post.side_effect = [error_response, success_response]
        
        generator = LLMFixGenerator(config)
        result = generator.analyze_and_fix(sample_parsed_defect, sample_code_context)
        
        # Should have succeeded using fallback
        assert isinstance(result, DefectAnalysisResult)
        assert "fallback_fix" in result.fix_candidates[0].fix_code
        assert mock_post.call_count == 2  # Primary + fallback


class TestLLMFixGeneratorPerformance:
    """Performance-related tests."""
    
    @patch('fix_generator.llm_manager.UnifiedLLMManager.analyze_defect')
    def test_performance_monitoring(self, mock_analyze, test_config,
                                   sample_parsed_defect, sample_code_context,
                                   sample_defect_analysis_result):
        """Test performance monitoring functionality."""
        mock_analyze.return_value = sample_defect_analysis_result
        
        generator = LLMFixGenerator(test_config)
        
        # Process multiple defects
        for i in range(3):
            generator.analyze_and_fix(sample_parsed_defect, sample_code_context)
        
        stats = generator.get_statistics()
        assert stats.total_defects_processed >= 3
        assert stats.successful_generations >= 3
        assert 0.0 <= stats.success_rate <= 1.0 