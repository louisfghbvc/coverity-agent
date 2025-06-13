"""
Unit tests for LLM Manager with NVIDIA NIM integration.
"""

import json
import time
import pytest
from unittest.mock import Mock, patch, MagicMock
import openai

from fix_generator.llm_manager import (
    UnifiedLLMManager, NIMProvider, NIMAPIException
)
from fix_generator.data_structures import DefectAnalysisResult
from fix_generator.config import LLMFixGeneratorConfig, NIMProviderConfig


class TestNIMProvider:
    """Test NIMProvider class."""
    
    def test_nim_provider_creation(self, test_config):
        """Test creating NIMProvider."""
        provider_config = test_config.get_provider_config("test_nim")
        provider = NIMProvider(provider_config)
        
        assert provider.config == provider_config
        assert provider.last_request_time == 0.0
        assert provider.request_count == 0
        assert provider.client is not None
        assert provider.client.base_url == provider_config.base_url
    
    def test_rate_limiting(self, test_config):
        """Test rate limiting functionality."""
        provider_config = test_config.get_provider_config("test_nim")
        provider_config.max_requests_per_minute = 2  # Very low limit for testing
        provider = NIMProvider(provider_config)
        
        # Simulate requests within the window
        provider.request_count = 2
        provider.request_window_start = time.time()
        
        # This should trigger rate limiting (but we'll mock sleep)
        with patch('time.sleep') as mock_sleep:
            provider._check_rate_limit()
            # Should reset counter and not sleep since we're at the limit
            
        # Simulate exceeding rate limit
        provider.request_count = 3
        with patch('time.sleep') as mock_sleep:
            provider._check_rate_limit()
            # Should sleep and reset
            assert mock_sleep.called
            assert provider.request_count == 0
    
    @patch('fix_generator.llm_manager.OpenAI')
    def test_generate_response_success(self, mock_openai_class, test_config, mock_nim_success_response):
        """Test successful response generation."""
        from fix_generator.prompt_engineering import PromptComponents
        
        # Setup mock OpenAI client
        mock_client = Mock()
        mock_openai_class.return_value = mock_client
        
        # Setup mock response
        mock_completion = Mock()
        mock_completion.choices = [Mock()]
        mock_completion.choices[0].message.content = mock_nim_success_response["choices"][0]["message"]["content"]
        mock_completion.usage.total_tokens = mock_nim_success_response["usage"]["total_tokens"]
        
        mock_client.chat.completions.create.return_value = mock_completion
        
        provider_config = test_config.get_provider_config("test_nim")
        provider = NIMProvider(provider_config)
        
        prompt_components = PromptComponents(
            system_prompt="Test system",
            user_prompt="Test user",
            context_data={},
            estimated_tokens=100,
            template_used="test"
        )
        
        content, metadata = provider.generate_response(prompt_components)
        
        # Verify response content
        expected_content = mock_nim_success_response["choices"][0]["message"]["content"]
        assert content == expected_content
        
        # Verify metadata
        assert metadata.model_used == provider_config.model
        assert metadata.tokens_consumed == 450
        assert metadata.generation_time > 0
        assert metadata.api_endpoint == provider_config.base_url
        assert metadata.request_id is not None
    
    @patch('fix_generator.llm_manager.OpenAI')
    def test_generate_response_api_error(self, mock_openai_class, test_config):
        """Test handling API errors."""
        from fix_generator.prompt_engineering import PromptComponents
        
        # Setup mock OpenAI client
        mock_client = Mock()
        mock_openai_class.return_value = mock_client
        
        # Setup mock error  
        mock_client.chat.completions.create.side_effect = openai.APIConnectionError(request=None)
        
        provider_config = test_config.get_provider_config("test_nim")
        provider_config.retry_attempts = 1  # Minimize retries for testing
        provider = NIMProvider(provider_config)
        
        prompt_components = PromptComponents(
            system_prompt="Test", user_prompt="Test",
            context_data={}, estimated_tokens=100, template_used="test"
        )
        
        with pytest.raises(NIMAPIException, match="Generation failed"):
            provider.generate_response(prompt_components)
    
    @patch('fix_generator.llm_manager.OpenAI')
    def test_generate_response_rate_limit_retry(self, mock_openai_class, test_config):
        """Test handling rate limit with retry."""
        from fix_generator.prompt_engineering import PromptComponents
        
        # Setup mock OpenAI client
        mock_client = Mock()
        mock_openai_class.return_value = mock_client
        
        # Setup rate limit error followed by success
        mock_completion = Mock()
        mock_completion.choices = [Mock()]
        mock_completion.choices[0].message.content = "success"
        mock_completion.usage.total_tokens = 100
        
        # Create a mock response for the rate limit error
        mock_response = Mock()
        mock_response.request = Mock()
        
        mock_client.chat.completions.create.side_effect = [
            openai.RateLimitError("Rate limit exceeded", response=mock_response, body=None),
            mock_completion
        ]
        
        provider_config = test_config.get_provider_config("test_nim")
        provider = NIMProvider(provider_config)
        
        prompt_components = PromptComponents(
            system_prompt="Test", user_prompt="Test",
            context_data={}, estimated_tokens=100, template_used="test"
        )
        
        with patch('time.sleep'):  # Mock sleep to speed up test
            content, metadata = provider.generate_response(prompt_components)
            
        assert content == "success"
        assert mock_client.chat.completions.create.call_count == 2
    
    def test_calculate_cost(self, test_config):
        """Test cost calculation."""
        provider_config = test_config.get_provider_config("test_nim")
        provider_config.estimated_cost_per_1k_tokens = 0.002
        provider = NIMProvider(provider_config)
        
        cost = provider._calculate_cost(1000)
        assert cost == 0.002
        
        cost = provider._calculate_cost(500)
        assert cost == 0.001
        
        # Test with no cost configured
        provider_config.estimated_cost_per_1k_tokens = None
        cost = provider._calculate_cost(1000)
        assert cost is None


class TestUnifiedLLMManager:
    """Test UnifiedLLMManager class."""
    
    def test_unified_llm_manager_creation(self, test_config):
        """Test creating UnifiedLLMManager."""
        manager = UnifiedLLMManager(test_config)
        
        assert manager.config == test_config
        assert len(manager.providers) == 1  # test_nim
        assert "test_nim" in manager.providers
        assert isinstance(manager.providers["test_nim"], NIMProvider)
    
    def test_get_provider_chain(self, test_config):
        """Test provider chain generation."""
        # Add fallback provider
        test_config.fallback_providers = ["fallback1", "fallback2"]
        
        manager = UnifiedLLMManager(test_config)
        chain = manager._get_provider_chain()
        
        assert chain == ["test_nim", "fallback1", "fallback2"]
    
    @patch.object(NIMProvider, 'generate_response')
    def test_analyze_defect_success(self, mock_generate, test_config, 
                                  sample_parsed_defect, sample_code_context, 
                                  mock_nim_success_response):
        """Test successful defect analysis."""
        # Setup mock response
        mock_nim_metadata = Mock()
        mock_nim_metadata.model_used = "test-model"
        mock_nim_metadata.tokens_consumed = 450
        mock_nim_metadata.generation_time = 2.0
        mock_nim_metadata.api_endpoint = "test-endpoint"
        mock_nim_metadata.request_id = "test-123"
        mock_nim_metadata.estimated_cost = 0.001
        
        mock_generate.return_value = (
            mock_nim_success_response["choices"][0]["message"]["content"],
            mock_nim_metadata
        )
        
        manager = UnifiedLLMManager(test_config)
        result = manager.analyze_defect(sample_parsed_defect, sample_code_context)
        
        assert isinstance(result, DefectAnalysisResult)
        assert result.defect_id == sample_parsed_defect.defect_id
        assert result.defect_type == sample_parsed_defect.defect_type
        assert len(result.fix_candidates) >= 1
        assert result.nim_metadata is not None
    
    @patch.object(NIMProvider, 'generate_response')
    def test_analyze_defect_provider_fallback(self, mock_generate, sample_parsed_defect, 
                                             sample_code_context, mock_nim_success_response):
        """Test provider fallback functionality."""
        # Create config with fallback
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
        mock_nim_metadata = Mock()
        mock_nim_metadata.model_used = "model2"
        mock_nim_metadata.tokens_consumed = 400
        mock_nim_metadata.generation_time = 1.5
        mock_nim_metadata.api_endpoint = "https://fallback.com"
        mock_nim_metadata.request_id = "fallback-123"
        mock_nim_metadata.estimated_cost = 0.0008
        
        mock_generate.side_effect = [
            NIMAPIException("Primary failed"),
            (
                mock_nim_success_response["choices"][0]["message"]["content"],
                mock_nim_metadata
            )
        ]
        
        manager = UnifiedLLMManager(config)
        result = manager.analyze_defect(sample_parsed_defect, sample_code_context)
        
        assert isinstance(result, DefectAnalysisResult)
        assert mock_generate.call_count == 2  # Primary + fallback
    
    @patch.object(NIMProvider, 'generate_response')
    def test_analyze_defect_all_providers_fail(self, mock_generate, test_config,
                                              sample_parsed_defect, sample_code_context):
        """Test behavior when all providers fail."""
        mock_generate.side_effect = NIMAPIException("All providers failed")
        
        manager = UnifiedLLMManager(test_config)
        
        with pytest.raises(NIMAPIException, match="All providers failed"):
            manager.analyze_defect(sample_parsed_defect, sample_code_context)
    
    def test_generate_fix_candidates(self, test_config, sample_parsed_defect, sample_code_context):
        """Test generating multiple fix candidates."""
        manager = UnifiedLLMManager(test_config)
        
        # Mock the analyze_defect method to avoid actual API calls
        mock_result = Mock(spec=DefectAnalysisResult)
        with patch.object(manager, 'analyze_defect', return_value=mock_result):
            results = manager.generate_fix_candidates(sample_parsed_defect, sample_code_context, 3)
            
        assert len(results) == 1  # Currently returns one comprehensive result
        assert results[0] == mock_result
    
    def test_statistics_tracking(self, test_config):
        """Test statistics tracking functionality."""
        manager = UnifiedLLMManager(test_config)
        
        # Initial state
        stats = manager.get_statistics()
        assert stats.total_defects_processed == 0
        assert stats.successful_generations == 0
        
        # Reset statistics
        manager.reset_statistics()
        stats = manager.get_statistics()
        assert stats.total_defects_processed == 0


class TestLLMManagerIntegration:
    """Integration tests for LLM Manager components."""
    
    @patch('fix_generator.llm_manager.OpenAI')
    def test_end_to_end_defect_analysis(self, mock_openai_class, test_config, 
                                       sample_parsed_defect, sample_code_context):
        """Test end-to-end defect analysis flow."""
        # Setup mock OpenAI client
        mock_client = Mock()
        mock_openai_class.return_value = mock_client
        
        # Setup comprehensive mock response
        mock_completion = Mock()
        mock_completion.choices = [Mock()]
        mock_completion.choices[0].message.content = json.dumps({
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
                "fix_strategy": "null_check",
                "potential_side_effects": []
            }],
            "reasoning": "The ptr variable needs null checking before use"
        })
        mock_completion.usage.total_tokens = 450
        
        mock_client.chat.completions.create.return_value = mock_completion
        
        manager = UnifiedLLMManager(test_config)
        result = manager.analyze_defect(sample_parsed_defect, sample_code_context)
        
        # Verify complete result structure
        assert isinstance(result, DefectAnalysisResult)
        assert result.defect_category == "null_pointer_dereference"
        assert result.confidence_score == 0.85
        assert len(result.fix_candidates) == 1
        
        fix_candidate = result.fix_candidates[0]
        assert fix_candidate.fix_code == "if (ptr != NULL) return strlen(ptr); return 0;"
        assert fix_candidate.confidence_score == 0.85
        assert fix_candidate.fix_strategy == "null_check"
        
        # Verify NIM metadata
        assert result.nim_metadata is not None
        assert result.nim_metadata.tokens_consumed == 450
        assert result.nim_metadata.model_used == test_config.get_provider_config("test_nim").model 