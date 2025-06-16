"""
Unified LLM Manager with NVIDIA NIM integration.

This module provides the main interface for interacting with NVIDIA Inference
Microservices for defect analysis and fix generation.
"""

import json
import time
import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
import re

try:
    from openai import OpenAI
except ImportError:
    raise ImportError("OpenAI library is required. Install with: pip install openai>=1.0.0")

from issue_parser.data_structures import ParsedDefect
from code_retriever.data_structures import CodeContext
from .data_structures import (
    DefectAnalysisResult, FixCandidate, NIMMetadata, 
    FixComplexity, DefectSeverity, GenerationStatistics
)
from .config import LLMFixGeneratorConfig, NIMProviderConfig
from .prompt_engineering import PromptEngineer, PromptComponents
from .response_parser import LLMResponseParser


logger = logging.getLogger(__name__)


class NIMAPIException(Exception):
    """Exception raised for NVIDIA NIM API errors."""
    pass


class NIMProvider:
    """Interface to a single NVIDIA NIM provider using OpenAI client."""
    
    def __init__(self, config: NIMProviderConfig):
        self.config = config
        
        # Initialize OpenAI client for NVIDIA NIM
        self.client = OpenAI(
            base_url=config.base_url,
            api_key=config.api_key,
            timeout=config.timeout
        )
        
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
    
    def _handle_streaming_response(self, completion) -> str:
        """Handle streaming response from NVIDIA NIM API."""
        content_parts = []
        
        try:
            for chunk in completion:
                if hasattr(chunk, 'choices') and chunk.choices:
                    delta = chunk.choices[0].delta
                    if hasattr(delta, 'content') and delta.content:
                        content_parts.append(delta.content)
            
            return ''.join(content_parts)
        
        except Exception as e:
            logger.error(f"Error handling streaming response: {e}")
            # Return partial content if available
            return ''.join(content_parts) if content_parts else ""
    
    def generate_response(self, prompt_components: PromptComponents) -> Tuple[str, NIMMetadata]:
        """Generate response from NVIDIA NIM API using OpenAI client."""
        self._check_rate_limit()
        
        start_time = time.time()
        request_id = f"nim-{int(start_time * 1000)}"
        
        # Prepare messages
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
        
        try:
            for attempt in range(self.config.retry_attempts):
                try:
                    # Log prompt for debugging if enabled
                    if logger.isEnabledFor(logging.DEBUG):
                        logger.debug(f"=== PROMPT DEBUG ===")
                        logger.debug(f"System prompt:\n{prompt_components.system_prompt}")
                        logger.debug(f"User prompt:\n{prompt_components.user_prompt}")
                        logger.debug(f"=== END PROMPT ===")
                    
                    # Make API call using OpenAI client
                    completion = self.client.chat.completions.create(
                        model=self.config.model,
                        messages=messages,
                        temperature=self.config.temperature,
                        top_p=self.config.top_p,
                        max_tokens=self.config.max_tokens,
                        frequency_penalty=self.config.frequency_penalty,
                        presence_penalty=self.config.presence_penalty,
                        stream=self.config.use_streaming
                    )
                    
                    # Handle streaming vs non-streaming response
                    if self.config.use_streaming:
                        content = self._handle_streaming_response(completion)
                    else:
                        content = completion.choices[0].message.content
                    
                    # Log response for debugging if enabled
                    if logger.isEnabledFor(logging.DEBUG):
                        logger.debug(f"=== LLM RESPONSE DEBUG ===")
                        logger.debug(f"Raw response:\n{content}")
                        logger.debug(f"=== END RESPONSE ===")
                    
                    # Extract usage information
                    tokens_consumed = getattr(completion.usage, 'total_tokens', 0) if hasattr(completion, 'usage') and completion.usage else 0
                    
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
                    logger.debug(f"Successfully generated response using {self.config.name}")
                    
                    return content, nim_metadata
                
                except Exception as e:
                    error_str = str(e)
                    if "rate" in error_str.lower() and "limit" in error_str.lower():
                        # Rate limit error
                        retry_delay = self.config.retry_delay * (2 ** attempt)
                        logger.warning(f"Rate limited by {self.config.name}, retrying after {retry_delay}s")
                        time.sleep(retry_delay)
                        continue
                    elif attempt < self.config.retry_attempts - 1:
                        # Other retryable errors
                        retry_delay = self.config.retry_delay * (2 ** attempt)
                        logger.warning(f"Request error for {self.config.name}: {e}, retrying in {retry_delay}s...")
                        time.sleep(retry_delay)
                        continue
                    else:
                        # Final attempt failed
                        raise NIMAPIException(f"All attempts failed: {e}")
            
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
        self.response_parser = LLMResponseParser(enable_validation=True)
        
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
                    raw_response, defect, nim_metadata
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
                       nim_metadata: NIMMetadata) -> DefectAnalysisResult:
        """Parse the LLM response into a DefectAnalysisResult using LLMResponseParser."""
        
        logger.debug(f"Parsing response using LLMResponseParser, length: {len(raw_response)}")
        
        if not raw_response or not raw_response.strip():
            logger.error("Empty response received from AI")
            return self._create_fallback_result(defect, Exception("Empty response from AI"), nim_metadata)

        try:
            parsed_response = self.response_parser.parse_response(raw_response, defect)
            
            # Map ParsedResponse to DefectAnalysisResult
            if not parsed_response.fix_candidates:
                raise ValueError("No valid fix candidates found after parsing.")

            # Create FixCandidate objects from parsed data
            fix_candidates = []
            for cand_data in parsed_response.fix_candidates:
                # Handle potentially incomplete explanation field
                explanation = cand_data.get('explanation', '')
                if not explanation or not explanation.strip():
                    explanation = 'AI-generated fix (explanation incomplete)'
                
                # Handle fix_type field
                fix_type_str = cand_data.get('fix_type', 'code_fix').lower()
                try:
                    from .data_structures import FixType
                    fix_type = FixType.CODE_FIX if fix_type_str == 'code_fix' else FixType.SUPPRESSION
                except:
                    fix_type = FixType.CODE_FIX  # Default fallback
                
                fix_candidates.append(FixCandidate(
                    fix_code='\n'.join(cand_data.get('fix_code', [])) if isinstance(cand_data.get('fix_code'), list) else cand_data.get('fix_code', ''),
                    explanation=explanation,
                    confidence_score=float(cand_data.get('confidence', 0.5)),
                    complexity=FixComplexity(cand_data.get('complexity', 'moderate').lower()),
                    risk_assessment=cand_data.get('risk_assessment', 'N/A'),
                    affected_files=cand_data.get('affected_files', [defect.file_path]),
                    line_ranges=cand_data.get('line_ranges', []),
                    fix_type=fix_type
                ))

            analysis = parsed_response.defect_analysis
            severity = DefectSeverity(analysis.get('severity', 'medium').lower())
            complexity = FixComplexity(analysis.get('complexity', 'moderate').lower())

            # Handle false positive detection
            is_false_positive = analysis.get('is_false_positive', False)
            false_positive_reason = analysis.get('false_positive_reason', '')

            analysis_result = DefectAnalysisResult(
                defect_id=defect.defect_id,
                defect_type=defect.defect_type,
                file_path=defect.file_path,
                line_number=defect.line_number,
                defect_category=analysis.get('category', defect.defect_type),
                severity_assessment=severity,
                fix_complexity=complexity,
                confidence_score=parsed_response.confidence_score,
                is_false_positive=is_false_positive,
                false_positive_reason=false_positive_reason,
                fix_candidates=fix_candidates,
                recommended_fix_index=0,  # Default to first
                reasoning_trace=parsed_response.reasoning,
                nim_metadata=nim_metadata,
                validation_errors=parsed_response.parsing_errors
            )
            
            return analysis_result

        except Exception as e:
            logger.error(f"Failed to parse response with LLMResponseParser: {e}")
            logger.error(f"Response preview (first 500 chars): {raw_response[:500]}")
            return self._create_fallback_result(defect, e, nim_metadata)
    
    def _clean_and_extract_json(self, text: str) -> Optional[str]:
        """
        Extracts and cleans a JSON object from a string.
        Handles markdown code blocks and removes comments.
        """
        # 1. Extract content within ```json ... ```, or find the largest JSON-like block
        json_str = None
        match = re.search(r'```json\s*(\{.*?\})\s*```', text, re.DOTALL)
        if match:
            json_str = match.group(1)
        else:
            # Fallback to find the largest '{...}' block
            match = re.search(r'(\{.*\})', text, re.DOTALL)
            if match:
                json_str = match.group(0)

        if not json_str:
            return None

        # 2. Remove // comments from the extracted JSON string
        # This is a common failure mode of LLMs.
        lines = json_str.split('\n')
        cleaned_lines = []
        for line in lines:
            # Remove any trailing // comments
            line = re.sub(r'\s*//.*$', '', line)
            cleaned_lines.append(line)
        
        json_str_no_comments = '\n'.join(cleaned_lines)

        # 3. Remove trailing commas from the last element in an object or array
        # Another common failure mode.
        json_str_no_trailing_commas = re.sub(r',\s*([\}\]])', r'\1', json_str_no_comments)
        
        return json_str_no_trailing_commas

    def _extract_json_from_response(self, text: str) -> Optional[str]:
        # This function is now replaced by _clean_and_extract_json
        return self._clean_and_extract_json(text)
    
    def _parse_fallback_response(self, raw_response: str, defect: ParsedDefect, 
                                nim_metadata: NIMMetadata) -> DefectAnalysisResult:
        """Parse non-JSON response as fallback."""
        
        # Check if response is empty or error message
        if not raw_response or raw_response.strip() == "Empty response":
            confidence = 0.1
            fix_code = "// Empty AI response - manual review required"
            explanation = "AI returned empty response"
        else:
            # Try to extract meaningful content
            
            # Look for JSON-like structures in the response
            import re
            json_match = re.search(r'\{.*"fix_candidates".*\}', raw_response, re.DOTALL)
            if json_match:
                try:
                    # Try to parse the extracted JSON
                    potential_json = json_match.group(0)
                    response_data = json.loads(potential_json)
                    
                    # Extract fix candidates if found
                    candidates_data = response_data.get('fix_candidates', [])
                    if candidates_data and len(candidates_data) > 0:
                        first_candidate = candidates_data[0]
                        fix_code = self._clean_code_formatting(first_candidate.get('fix_code', ''))
                        explanation = first_candidate.get('explanation', 'Partial JSON parsing successful')
                        confidence = 0.6  # Higher confidence for partial JSON success
                    else:
                        confidence = 0.4
                        fix_code = "// JSON found but no fix candidates"
                        explanation = "Partial JSON parsing - no fix candidates found"
                        
                except json.JSONDecodeError:
                    # Fall back to code block extraction
                    confidence = 0.4
                    fix_code, explanation = self._extract_code_blocks(raw_response)
            else:
                # Simple extraction - look for code blocks
                confidence = 0.4
                fix_code, explanation = self._extract_code_blocks(raw_response)
        
        fix_candidate = FixCandidate(
            fix_code=fix_code,
            explanation=explanation,
            confidence_score=confidence,
            complexity=FixComplexity.MODERATE,
            risk_assessment="Unknown - requires manual review",
            affected_files=[defect.file_path],
            line_ranges=[{'start': defect.line_number, 'end': defect.line_number}]
        )
        
        validation_errors = []
        if confidence < 0.5:
            validation_errors.append(f"Low confidence fallback parsing: {confidence:.2f}")
        if "Empty response" in explanation:
            validation_errors.append("AI returned empty response")
        else:
            validation_errors.append("Fallback parsing used - manual review recommended")
        
        return DefectAnalysisResult(
            defect_id=defect.defect_id,
            defect_type=defect.defect_type,
            file_path=defect.file_path,
            line_number=defect.line_number,
            defect_category="unknown",
            severity_assessment=DefectSeverity.MEDIUM,
            fix_complexity=FixComplexity.MODERATE,
            confidence_score=confidence,
            fix_candidates=[fix_candidate],
            nim_metadata=nim_metadata,
            validation_errors=validation_errors
        )
    
    def _extract_code_blocks(self, raw_response: str) -> tuple[str, str]:
        """Extract code blocks from response text."""
        lines = raw_response.split('\n')
        code_lines = []
        in_code_block = False
        
        for line in lines:
            if line.strip().startswith('```'):
                in_code_block = not in_code_block
                continue
            if in_code_block:
                code_lines.append(line)
        
        if code_lines:
            fix_code = '\n'.join(code_lines)
            explanation = "Code block extraction from non-JSON response"
        else:
            # Look for any meaningful content
            meaningful_lines = [line.strip() for line in lines if line.strip() and not line.strip().startswith('#')]
            if meaningful_lines:
                fix_code = '\n'.join(meaningful_lines[:5])  # Take first 5 meaningful lines
                explanation = "Text extraction from non-JSON response"
            else:
                fix_code = raw_response[:200] if len(raw_response) > 10 else "// No meaningful content found"
                explanation = "Raw text fallback - minimal content found"
        
        return fix_code, explanation
    
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
                               num_candidates: int = 1) -> List[DefectAnalysisResult]:
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

    def _clean_code_formatting(self, code) -> str:
        """Convert fix code to string format, handling different input types.
        
        Args:
            code: Fix code as string or list of strings
            
        Returns:
            Code as string
        """
        # Handle different input types
        if not code:
            return ""
        
        # Convert list to string if needed
        if isinstance(code, list):
            # Join list elements with newlines
            return '\n'.join(str(line) for line in code)
        elif isinstance(code, str):
            return code
        else:
            # Handle other types by converting to string
            return str(code)
    
    def _resolve_affected_files(self, raw_affected_files: List[str], defect_file_path: str) -> List[str]:
        """Resolve relative file paths to absolute paths based on the defect file path."""
        from pathlib import Path
        
        resolved_files = []
        defect_file = Path(defect_file_path)
        defect_dir = defect_file.parent
        
        for file_path in raw_affected_files:
            if not file_path:
                continue
                
            file_path = file_path.strip()
            path_obj = Path(file_path)
            
            # If it's already an absolute path, use it
            if path_obj.is_absolute():
                resolved_files.append(file_path)
                continue
            
            # If it's just a filename (no directory separators), try to find it in the defect's directory
            if '/' not in file_path and '\\' not in file_path:
                # It's likely just a filename, try to find it in the same directory as the defect file
                potential_path = defect_dir / file_path
                if potential_path.exists():
                    resolved_files.append(str(potential_path))
                    logger.info(f"Resolved relative filename '{file_path}' to '{potential_path}'")
                    continue
                else:
                    # Look for common related files (e.g., .cpp for .h, .h for .cpp)
                    if file_path.endswith('.cpp') or file_path.endswith('.c'):
                        # Try looking in common source directories
                        for src_subdir in ['', 'src', '../src', 'source', '../source']:
                            if src_subdir:
                                search_dir = defect_dir / src_subdir
                            else:
                                search_dir = defect_dir
                            
                            potential_path = search_dir / file_path
                            if potential_path.exists():
                                resolved_files.append(str(potential_path))
                                logger.info(f"Found '{file_path}' in '{search_dir}'")
                                break
                        else:
                            # Not found, use relative to defect directory anyway
                            fallback_path = defect_dir / file_path
                            resolved_files.append(str(fallback_path))
                            logger.warning(f"Could not find '{file_path}', using fallback path: {fallback_path}")
                    else:
                        # For header files or other types, assume same directory
                        fallback_path = defect_dir / file_path
                        resolved_files.append(str(fallback_path))
                        logger.warning(f"Could not find '{file_path}', using fallback path: {fallback_path}")
            else:
                # It's a relative path with directories, resolve relative to defect file directory
                resolved_path = defect_dir / file_path
                resolved_files.append(str(resolved_path.resolve()))
                logger.info(f"Resolved relative path '{file_path}' to '{resolved_path.resolve()}'")
        
        # Ensure we always have at least the original defect file
        if not resolved_files:
            resolved_files.append(defect_file_path)
        
        return resolved_files