"""
Unit tests for LLM Manager with NVIDIA NIM integration.
"""

import json
import time
import pytest
from unittest.mock import Mock, patch, MagicMock
import requests

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
        assert "Authorization" in provider.session.headers
        assert f"Bearer {provider_config.api_key}" in provider.session.headers["Authorization"]
    
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
    
    def test_prepare_request_payload(self, test_config):
        """Test request payload preparation."""
        from fix_generator.prompt_engineering import PromptComponents
        
        provider_config = test_config.get_provider_config("test_nim")
        provider = NIMProvider(provider_config)
        
        prompt_components = PromptComponents(
            system_prompt="Test system prompt",
            user_prompt="Test user prompt",
            context_data={},
            estimated_tokens=100,
            template_used="test"
        )
        
        payload = provider._prepare_request_payload(prompt_components)
        
        assert payload["model"] == provider_config.model
        assert payload["max_tokens"] == provider_config.max_tokens
        assert payload["temperature"] == provider_config.temperature
        assert len(payload["messages"]) == 2
        assert payload["messages"][0]["role"] == "system"
        assert payload["messages"][1]["role"] == "user"
        assert payload["messages"][0]["content"] == "Test system prompt"
        assert payload["messages"][1]["content"] == "Test user prompt"
    
    @patch('requests.Session.post')
    def test_generate_response_success(self, mock_post, test_config, mock_nim_success_response):
        """Test successful response generation."""
        from fix_generator.prompt_engineering import PromptComponents
        
        # Setup mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_nim_success_response
        mock_post.return_value = mock_response
        
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
    
    @patch('requests.Session.post')
    def test_generate_response_http_error(self, mock_post, test_config):
        """Test handling HTTP errors."""
        from fix_generator.prompt_engineering import PromptComponents
        
        # Setup mock error response
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_post.return_value = mock_response
        
        provider_config = test_config.get_provider_config("test_nim")
        provider_config.retry_attempts = 1  # Minimize retries for testing
        provider = NIMProvider(provider_config)
        
        prompt_components = PromptComponents(
            system_prompt="Test", user_prompt="Test",
            context_data={}, estimated_tokens=100, template_used="test"
        )
        
        with pytest.raises(NIMAPIException, match="HTTP 500"):
            provider.generate_response(prompt_components)
    
    @patch('requests.Session.post')
    def test_generate_response_rate_limit_retry(self, mock_post, test_config):
        """Test handling rate limit with retry."""
        from fix_generator.prompt_engineering import PromptComponents
        
        # Setup rate limit response followed by success
        rate_limit_response = Mock()
        rate_limit_response.status_code = 429
        rate_limit_response.headers = {'Retry-After': '1'}
        
        success_response = Mock()
        success_response.status_code = 200
        success_response.json.return_value = {
            "choices": [{"message": {"content": "success"}}],
            "usage": {"total_tokens": 100}
        }
        
        mock_post.side_effect = [rate_limit_response, success_response]
        
        provider_config = test_config.get_provider_config("test_nim")
        provider = NIMProvider(provider_config)
        
        prompt_components = PromptComponents(
            system_prompt="Test", user_prompt="Test",
            context_data={}, estimated_tokens=100, template_used="test"
        )
        
        with patch('time.sleep'):  # Mock sleep to speed up test
            content, metadata = provider.generate_response(prompt_components)
            
        assert content == "success"
        assert mock_post.call_count == 2
    
    @patch('requests.Session.post')
    def test_generate_response_timeout(self, mock_post, test_config):
        """Test handling request timeout."""
        from fix_generator.prompt_engineering import PromptComponents
        
        mock_post.side_effect = requests.exceptions.Timeout()
        
        provider_config = test_config.get_provider_config("test_nim")
        provider_config.retry_attempts = 1
        provider = NIMProvider(provider_config)
        
        prompt_components = PromptComponents(
            system_prompt="Test", user_prompt="Test",
            context_data={}, estimated_tokens=100, template_used="test"
        )
        
        with pytest.raises(NIMAPIException, match="Timeout"):
            provider.generate_response(prompt_components)
    
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
    
    @patch('requests.Session.post')
    def test_end_to_end_defect_analysis(self, mock_post, test_config, 
                                       sample_parsed_defect, sample_code_context):
        """Test end-to-end defect analysis flow."""
        # Setup comprehensive mock response
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
                            "fix_strategy": "null_check",
                            "potential_side_effects": []
                        }],
                        "reasoning": "The ptr variable needs null checking before use"
                    })
                }
            }],
            "usage": {"total_tokens": 450}
        }
        mock_post.return_value = mock_response
        
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