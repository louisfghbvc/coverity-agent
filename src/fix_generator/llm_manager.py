"""
Unified LLM Manager with NVIDIA NIM integration.

This module provides the main interface for interacting with NVIDIA Inference
Microservices for defect analysis and fix generation.
"""

import json
import time
import logging
import requests
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta

from issue_parser.data_structures import ParsedDefect
from code_retriever.data_structures import CodeContext
from .data_structures import (
    DefectAnalysisResult, FixCandidate, NIMMetadata, 
    FixComplexity, DefectSeverity, GenerationStatistics
)
from .config import LLMFixGeneratorConfig, NIMProviderConfig
from .prompt_engineering import PromptEngineer, PromptComponents


logger = logging.getLogger(__name__)


class NIMAPIException(Exception):
    """Exception raised for NVIDIA NIM API errors."""
    pass


class NIMProvider:
    """Interface to a single NVIDIA NIM provider."""
    
    def __init__(self, config: NIMProviderConfig):
        self.config = config
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Bearer {config.api_key}',
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })
        
        # Rate limiting
        self.last_request_time = 0.0
        self.request_count = 0
        self.request_window_start = time.time()
    
    def _check_rate_limit(self):
        """Check and enforce rate limiting."""
        current_time = time.time()
        
        # Reset counter if window has passed
        if current_time - self.request_window_start >= 60:
            self.request_count = 0
            self.request_window_start = current_time
        
        # Check if we're at the limit
        if self.request_count >= self.config.max_requests_per_minute:
            sleep_time = 60 - (current_time - self.request_window_start)
            if sleep_time > 0:
                logger.warning(f"Rate limit reached for {self.config.name}, sleeping {sleep_time:.1f}s")
                time.sleep(sleep_time)
                self.request_count = 0
                self.request_window_start = time.time()
    
    def _prepare_request_payload(self, prompt_components: PromptComponents) -> Dict[str, Any]:
        """Prepare the request payload for NIM API."""
        # Construct messages for chat completion format
        messages = [
            {
                "role": "system",
                "content": prompt_components.system_prompt
            },
            {
                "role": "user", 
                "content": prompt_components.user_prompt
            }
        ]
        
        payload = {
            "model": self.config.model,
            "messages": messages,
            "max_tokens": self.config.max_tokens,
            "temperature": self.config.temperature,
            "stream": self.config.use_streaming
        }
        
        return payload
    
    def generate_response(self, prompt_components: PromptComponents) -> Tuple[str, NIMMetadata]:
        """Generate response from NVIDIA NIM API."""
        self._check_rate_limit()
        
        payload = self._prepare_request_payload(prompt_components)
        
        start_time = time.time()
        request_id = f"nim-{int(start_time * 1000)}"
        
        try:
            for attempt in range(self.config.retry_attempts):
                try:
                    response = self.session.post(
                        self.config.base_url,
                        json=payload,
                        timeout=self.config.timeout
                    )
                    
                    if response.status_code == 200:
                        break
                    elif response.status_code == 429:  # Rate limited
                        retry_after = int(response.headers.get('Retry-After', self.config.retry_delay))
                        logger.warning(f"Rate limited by {self.config.name}, retrying after {retry_after}s")
                        time.sleep(retry_after)
                        continue
                    else:
                        logger.warning(f"HTTP {response.status_code} from {self.config.name}: {response.text}")
                        if attempt < self.config.retry_attempts - 1:
                            time.sleep(self.config.retry_delay * (2 ** attempt))
                            continue
                        else:
                            raise NIMAPIException(f"HTTP {response.status_code}: {response.text}")
                
                except requests.exceptions.Timeout:
                    if attempt < self.config.retry_attempts - 1:
                        logger.warning(f"Timeout for {self.config.name}, retrying...")
                        time.sleep(self.config.retry_delay * (2 ** attempt))
                        continue
                    else:
                        raise NIMAPIException(f"Timeout after {self.config.retry_attempts} attempts")
                
                except requests.exceptions.RequestException as e:
                    if attempt < self.config.retry_attempts - 1:
                        logger.warning(f"Request error for {self.config.name}: {e}, retrying...")
                        time.sleep(self.config.retry_delay * (2 ** attempt))
                        continue
                    else:
                        raise NIMAPIException(f"Request failed: {e}")
            
            response.raise_for_status()
            response_data = response.json()
            
            # Extract response content
            if 'choices' in response_data and response_data['choices']:
                content = response_data['choices'][0]['message']['content']
            else:
                raise NIMAPIException("Invalid response format: missing choices")
            
            # Extract usage information
            usage = response_data.get('usage', {})
            tokens_consumed = usage.get('total_tokens', 0)
            
            generation_time = time.time() - start_time
            
            # Create metadata
            nim_metadata = NIMMetadata(
                model_used=self.config.model,
                tokens_consumed=tokens_consumed,
                generation_time=generation_time,
                api_endpoint=self.config.base_url,
                request_id=request_id,
                estimated_cost=self._calculate_cost(tokens_consumed)
            )
            
            self.request_count += 1
            
            return content, nim_metadata
        
        except Exception as e:
            generation_time = time.time() - start_time
            logger.error(f"Failed to generate response from {self.config.name}: {e}")
            
            # Return error metadata
            nim_metadata = NIMMetadata(
                model_used=self.config.model,
                tokens_consumed=0,
                generation_time=generation_time,
                api_endpoint=self.config.base_url,
                request_id=request_id
            )
            
            raise NIMAPIException(f"Generation failed: {e}") from e
    
    def _calculate_cost(self, tokens: int) -> Optional[float]:
        """Calculate estimated cost for the request."""
        if self.config.estimated_cost_per_1k_tokens is not None:
            return (tokens / 1000.0) * self.config.estimated_cost_per_1k_tokens
        return None


class UnifiedLLMManager:
    """
    Unified LLM Manager for defect analysis and fix generation using NVIDIA NIM.
    
    This class handles provider selection, fallbacks, prompt generation,
    and response parsing for the complete defect analysis pipeline.
    """
    
    def __init__(self, config: Optional[LLMFixGeneratorConfig] = None, 
                 env_file_path: Optional[str] = None):
        """
        Initialize UnifiedLLMManager with configuration.
        
        Args:
            config: LLMFixGeneratorConfig instance. If None, loads from environment
            env_file_path: Path to .env file for environment-based configuration
        """
        if config is None:
            # Load configuration from environment variables
            config = LLMFixGeneratorConfig.create_from_env(env_file_path)
            
            # Validate environment configuration
            env_errors = config.validate_nvidia_nim_environment()
            if env_errors:
                error_msg = "NVIDIA NIM environment validation failed:\n" + "\n".join(f"  - {error}" for error in env_errors)
                raise ValueError(error_msg)
        
        self.config = config
        self.prompt_engineer = PromptEngineer(config.analysis)
        self.statistics = GenerationStatistics()
        
        # Initialize providers
        self.providers = {}
        for name, provider_config in config.providers.items():
            try:
                self.providers[name] = NIMProvider(provider_config)
                logger.info(f"Initialized provider: {name}")
            except Exception as e:
                logger.error(f"Failed to initialize provider {name}: {e}")
                # Don't fail initialization if fallback providers fail
                if name != config.primary_provider:
                    continue
                raise
        
        # Setup logging
        logging.basicConfig(level=getattr(logging, config.log_level))
        logger.setLevel(getattr(logging, config.log_level))
        
        logger.info(f"UnifiedLLMManager initialized with primary provider: {config.primary_provider}")
        logger.info(f"Available fallback providers: {config.fallback_providers}")
    
    @classmethod
    def create_from_env(cls, env_file_path: Optional[str] = None) -> 'UnifiedLLMManager':
        """
        Create UnifiedLLMManager from environment variables.
        
        Args:
            env_file_path: Path to .env file. If None, looks for .env in current directory.
        """
        return cls(config=None, env_file_path=env_file_path)
    
    def _get_provider_chain(self) -> List[str]:
        """Get the chain of providers to try (primary + fallbacks)."""
        chain = [self.config.primary_provider]
        chain.extend(self.config.fallback_providers)
        return chain
    
    def analyze_defect(self, defect: ParsedDefect, code_context: CodeContext) -> DefectAnalysisResult:
        """
        Unified defect analysis and fix generation.
        
        Performs both classification and fix generation in a single LLM call
        for optimal context preservation and performance.
        """
        logger.info(f"Analyzing defect {defect.defect_id}: {defect.defect_type}")
        
        # Generate prompt
        prompt_components = self.prompt_engineer.generate_prompt(defect, code_context)
        
        # Optimize prompt length if needed
        max_tokens = min(provider.config.max_tokens for provider in self.providers.values())
        if prompt_components.estimated_tokens > max_tokens * 0.6:  # Leave room for response
            prompt_components = self.prompt_engineer.optimize_prompt_length(
                prompt_components, int(max_tokens * 0.6)
            )
        
        # Try providers in order
        provider_chain = self._get_provider_chain()
        last_exception = None
        
        for provider_name in provider_chain:
            if provider_name not in self.providers:
                logger.warning(f"Provider {provider_name} not configured, skipping")
                continue
            
            try:
                logger.debug(f"Trying provider: {provider_name}")
                provider = self.providers[provider_name]
                
                raw_response, nim_metadata = provider.generate_response(prompt_components)
                
                # Parse the response
                analysis_result = self._parse_response(
                    raw_response, defect, nim_metadata, prompt_components.template_used
                )
                
                # Update statistics
                self.statistics.add_result(analysis_result, success=True)
                
                logger.info(f"Successfully analyzed defect {defect.defect_id} using {provider_name}")
                return analysis_result
            
            except Exception as e:
                last_exception = e
                logger.warning(f"Provider {provider_name} failed for defect {defect.defect_id}: {e}")
                continue
        
        # All providers failed
        self.statistics.add_result(
            self._create_fallback_result(defect, last_exception), success=False
        )
        raise NIMAPIException(f"All providers failed for defect {defect.defect_id}. Last error: {last_exception}")
    
    def _parse_response(self, raw_response: str, defect: ParsedDefect, 
                       nim_metadata: NIMMetadata, template_used: str) -> DefectAnalysisResult:
        """Parse the LLM response into a DefectAnalysisResult."""
        try:
            # Try to parse as JSON
            response_data = json.loads(raw_response)
            
            # Extract defect analysis
            defect_analysis = response_data.get('defect_analysis', {})
            
            # Parse severity and complexity
            severity_str = defect_analysis.get('severity', 'medium').lower()
            severity = DefectSeverity(severity_str) if severity_str in [e.value for e in DefectSeverity] else DefectSeverity.MEDIUM
            
            complexity_str = defect_analysis.get('complexity', 'moderate').lower()
            complexity = FixComplexity(complexity_str) if complexity_str in [e.value for e in FixComplexity] else FixComplexity.MODERATE
            
            # Parse fix candidates
            fix_candidates = []
            candidates_data = response_data.get('fix_candidates', [])
            
            for i, candidate_data in enumerate(candidates_data):
                try:
                    candidate_complexity_str = candidate_data.get('complexity', 'moderate').lower()
                    candidate_complexity = FixComplexity(candidate_complexity_str) if candidate_complexity_str in [e.value for e in FixComplexity] else FixComplexity.MODERATE
                    
                    fix_candidate = FixCandidate(
                        fix_code=candidate_data.get('fix_code', ''),
                        explanation=candidate_data.get('explanation', ''),
                        confidence_score=float(candidate_data.get('confidence', 0.5)),
                        complexity=candidate_complexity,
                        risk_assessment=candidate_data.get('risk_assessment', 'Unknown risk'),
                        affected_files=candidate_data.get('affected_files', [defect.file_path]),
                        line_ranges=candidate_data.get('line_ranges', [{'start': defect.line_number, 'end': defect.line_number}]),
                        fix_strategy=candidate_data.get('fix_strategy', ''),
                        estimated_effort=candidate_data.get('estimated_effort', ''),
                        potential_side_effects=candidate_data.get('potential_side_effects', [])
                    )
                    fix_candidates.append(fix_candidate)
                except Exception as e:
                    logger.warning(f"Failed to parse fix candidate {i}: {e}")
                    continue
            
            # Ensure we have at least one candidate
            if not fix_candidates:
                raise ValueError("No valid fix candidates found in response")
            
            # Create the analysis result
            analysis_result = DefectAnalysisResult(
                defect_id=defect.defect_id,
                defect_type=defect.defect_type,
                file_path=defect.file_path,
                line_number=defect.line_number,
                defect_category=defect_analysis.get('category', defect.defect_type),
                severity_assessment=severity,
                fix_complexity=complexity,
                confidence_score=float(defect_analysis.get('confidence', 0.5)),
                fix_candidates=fix_candidates,
                recommended_fix_index=0,  # First candidate is recommended by default
                reasoning_trace=response_data.get('reasoning', ''),
                nim_metadata=nim_metadata
            )
            
            return analysis_result
        
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            # Try to extract fix code from non-JSON response
            return self._parse_fallback_response(raw_response, defect, nim_metadata)
        
        except Exception as e:
            logger.error(f"Failed to parse response: {e}")
            return self._create_fallback_result(defect, e, nim_metadata)
    
    def _parse_fallback_response(self, raw_response: str, defect: ParsedDefect, 
                                nim_metadata: NIMMetadata) -> DefectAnalysisResult:
        """Parse non-JSON response as fallback."""
        # Simple extraction - look for code blocks
        lines = raw_response.split('\n')
        code_lines = []
        in_code_block = False
        
        for line in lines:
            if line.strip().startswith('```'):
                in_code_block = not in_code_block
                continue
            if in_code_block:
                code_lines.append(line)
        
        fix_code = '\n'.join(code_lines) if code_lines else raw_response[:500]
        
        fix_candidate = FixCandidate(
            fix_code=fix_code,
            explanation="Fallback parsing - manual review recommended",
            confidence_score=0.3,
            complexity=FixComplexity.MODERATE,
            risk_assessment="Unknown - requires manual review",
            affected_files=[defect.file_path],
            line_ranges=[{'start': defect.line_number, 'end': defect.line_number}]
        )
        
        return DefectAnalysisResult(
            defect_id=defect.defect_id,
            defect_type=defect.defect_type,
            file_path=defect.file_path,
            line_number=defect.line_number,
            defect_category="unknown",
            severity_assessment=DefectSeverity.MEDIUM,
            fix_complexity=FixComplexity.MODERATE,
            confidence_score=0.3,
            fix_candidates=[fix_candidate],
            nim_metadata=nim_metadata,
            validation_errors=["Fallback parsing used - manual review recommended"]
        )
    
    def _create_fallback_result(self, defect: ParsedDefect, error: Exception, 
                               nim_metadata: Optional[NIMMetadata] = None) -> DefectAnalysisResult:
        """Create a fallback result when analysis fails."""
        fix_candidate = FixCandidate(
            fix_code="// Fix generation failed - manual review required",
            explanation=f"Automated fix generation failed: {str(error)}",
            confidence_score=0.0,
            complexity=FixComplexity.HIGH_RISK,
            risk_assessment="High risk - requires manual analysis",
            affected_files=[defect.file_path],
            line_ranges=[{'start': defect.line_number, 'end': defect.line_number}]
        )
        
        return DefectAnalysisResult(
            defect_id=defect.defect_id,
            defect_type=defect.defect_type,
            file_path=defect.file_path,
            line_number=defect.line_number,
            defect_category="unknown",
            severity_assessment=DefectSeverity.HIGH,
            fix_complexity=FixComplexity.HIGH_RISK,
            confidence_score=0.0,
            fix_candidates=[fix_candidate],
            nim_metadata=nim_metadata,
            safety_checks_passed=False,
            validation_errors=[f"Analysis failed: {str(error)}"]
        )
    
    def generate_fix_candidates(self, defect: ParsedDefect, code_context: CodeContext,
                               num_candidates: int = 3) -> List[DefectAnalysisResult]:
        """Generate multiple fix approaches for comparison."""
        results = []
        
        # Temporarily override the number of candidates in config
        original_num = self.config.analysis.num_candidates
        self.config.analysis.num_candidates = num_candidates
        
        try:
            # For now, generate one comprehensive result with multiple candidates
            # Could be enhanced to generate completely separate analyses
            result = self.analyze_defect(defect, code_context)
            results.append(result)
            
        finally:
            # Restore original config
            self.config.analysis.num_candidates = original_num
        
        return results
    
    def get_statistics(self) -> GenerationStatistics:
        """Get current generation statistics."""
        return self.statistics
    
    def reset_statistics(self):
        """Reset generation statistics."""
        self.statistics = GenerationStatistics() 