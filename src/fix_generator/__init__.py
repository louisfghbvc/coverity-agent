"""
LLM Fix Generator with NVIDIA NIM Integration.

This module provides the central AI-powered component for analyzing Coverity defects
and generating code fixes using NVIDIA Inference Microservices.
"""

import sys
import os

# Add src directory to Python path for proper imports
src_path = os.path.join(os.path.dirname(os.path.dirname(__file__)))
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from .llm_manager import UnifiedLLMManager, NIMAPIException
from .data_structures import (
    DefectAnalysisResult, FixCandidate, NIMMetadata, GenerationStatistics,
    FixComplexity, DefectSeverity, ConfidenceLevel
)
from .config import LLMFixGeneratorConfig, NIMProviderConfig
from .prompt_engineering import PromptEngineer
from .response_parser import LLMResponseParser, ResponseValidator
from .style_checker import StyleConsistencyChecker, StyleProfile


# Main public interface
class LLMFixGenerator:
    """
    Main LLM Fix Generator class that provides the public API for defect analysis and fix generation.
    
    This class integrates all components to provide a unified interface for:
    - Defect analysis and classification
    - Fix generation with multiple candidates
    - Style consistency checking
    - Performance monitoring and statistics
    """
    
    def __init__(self, config: LLMFixGeneratorConfig = None, env_file_path: str = None, 
                 use_env: bool = False):
        """
        Initialize the LLM Fix Generator.
        
        Args:
            config: Configuration object. If None, loads based on use_env flag.
            env_file_path: Path to .env file for environment-based configuration
            use_env: If True, force loading from environment variables
        """
        if config is None:
            if use_env or env_file_path is not None:
                # Load from environment variables
                config = LLMFixGeneratorConfig.create_from_env(env_file_path)
            else:
                # Use default configuration
                config = LLMFixGeneratorConfig.create_default()
        
        self.config = config
        self.llm_manager = UnifiedLLMManager(config)
        self.style_checker = StyleConsistencyChecker()
        
        # Validate environment if using NIM provider
        if config.primary_provider == "nvidia_nim":
            nim_errors = config.validate_nvidia_nim_environment()
            if nim_errors:
                raise ValueError(f"NVIDIA NIM configuration errors: {'; '.join(nim_errors)}")
        
        # General environment validation
        env_errors = config.validate_environment()
        if env_errors:
            raise ValueError(f"Configuration errors: {'; '.join(env_errors)}")
    
    def analyze_and_fix(self, defect, code_context) -> DefectAnalysisResult:
        """
        Analyze a defect and generate fixes.
        
        Args:
            defect: ParsedDefect object from Issue Parser
            code_context: CodeContext object from Code Retriever
            
        Returns:
            DefectAnalysisResult with analysis and fix candidates
            
        Raises:
            NIMAPIException: If all NIM providers fail
        """
        # Perform LLM analysis
        analysis_result = self.llm_manager.analyze_defect(defect, code_context)
        
        # Apply style consistency to fix candidates if enabled
        if self.config.quality.enforce_style_consistency:
            self._apply_style_consistency(analysis_result, code_context)
        
        # Perform quality validation if enabled
        if self.config.quality.safety_checks:
            self._perform_quality_checks(analysis_result)
        
        return analysis_result
    
    def generate_multiple_fixes(self, defect, code_context, num_candidates: int = 1):
        """
        Generate multiple fix approaches for comparison.
        
        Args:
            defect: ParsedDefect object
            code_context: CodeContext object
            num_candidates: Number of fix candidates to generate
            
        Returns:
            List of DefectAnalysisResult objects
        """
        return self.llm_manager.generate_fix_candidates(defect, code_context, num_candidates)
    
    def get_statistics(self) -> GenerationStatistics:
        """Get current generation statistics."""
        return self.llm_manager.get_statistics()
    
    def reset_statistics(self):
        """Reset generation statistics."""
        self.llm_manager.reset_statistics()
    
    def _apply_style_consistency(self, analysis_result: DefectAnalysisResult, code_context):
        """Apply style consistency to all fix candidates."""
        total_style_score = 0.0
        
        for candidate in analysis_result.fix_candidates:
            styled_code, consistency_score = self.style_checker.check_and_fix_style(
                candidate, code_context
            )
            
            # Update the fix code with styled version
            candidate.fix_code = styled_code
            total_style_score += consistency_score
        
        # Update overall style consistency score
        if analysis_result.fix_candidates:
            analysis_result.style_consistency_score = total_style_score / len(analysis_result.fix_candidates)
    
    def _perform_quality_checks(self, analysis_result: DefectAnalysisResult):
        """Perform safety and quality checks on the analysis result."""
        validation_errors = []
        
        # Check for minimum confidence threshold
        if analysis_result.confidence_score < self.config.quality.min_confidence_for_auto_apply:
            validation_errors.append(f"Low overall confidence: {analysis_result.confidence_score:.2f}")
        
        # Check individual fix candidates
        for i, candidate in enumerate(analysis_result.fix_candidates):
            # Check for empty or suspicious code
            if not candidate.fix_code.strip():
                validation_errors.append(f"Fix candidate {i+1} has empty code")
                continue
            
            # Check for dangerous patterns
            dangerous_patterns = [
                'system(',
                'exec(',
                'eval(',
                'rm -rf',
                'delete *',
                'DROP TABLE'
            ]
            
            code_lower = candidate.fix_code.lower()
            for pattern in dangerous_patterns:
                if pattern.lower() in code_lower:
                    validation_errors.append(f"Fix candidate {i+1} contains dangerous pattern: {pattern}")
                    candidate.potential_side_effects.append(f"Contains dangerous pattern: {pattern}")
            
            # Check for very low confidence
            if candidate.confidence_score < 0.3:
                validation_errors.append(f"Fix candidate {i+1} has very low confidence: {candidate.confidence_score:.2f}")
        
        # Update analysis result with validation errors
        analysis_result.validation_errors.extend(validation_errors)
        analysis_result.safety_checks_passed = len(validation_errors) == 0
    
    @classmethod
    def create_from_env(cls, env_file_path: str = None) -> 'LLMFixGenerator':
        """
        Create LLM Fix Generator from environment variables using dotenv.
        
        Args:
            env_file_path: Path to .env file. If None, looks for .env in current directory.
            
        Returns:
            Configured LLMFixGenerator instance with dotenv-based configuration
        """
        return cls(config=None, env_file_path=env_file_path, use_env=True)
    
    @classmethod
    def create_with_config_file(cls, config_path: str, load_env: bool = True, 
                               env_file_path: str = None) -> 'LLMFixGenerator':
        """
        Create LLM Fix Generator from configuration file.
        
        Args:
            config_path: Path to YAML configuration file
            load_env: Whether to load environment variables from .env file
            env_file_path: Path to .env file (defaults to .env in current directory)
            
        Returns:
            Configured LLMFixGenerator instance
        """
        config = LLMFixGeneratorConfig.from_yaml_file(config_path, load_env, env_file_path)
        return cls(config)
    
    @classmethod
    def create_default(cls) -> 'LLMFixGenerator':
        """
        Create LLM Fix Generator with default configuration.
        
        Returns:
            LLMFixGenerator with default NIM configuration
        """
        config = LLMFixGeneratorConfig.create_default()
        return cls(config)


# Export main classes and functions
__all__ = [
    # Main interface
    'LLMFixGenerator',
    
    # Core data structures
    'DefectAnalysisResult',
    'FixCandidate', 
    'NIMMetadata',
    'GenerationStatistics',
    
    # Enums
    'FixComplexity',
    'DefectSeverity', 
    'ConfidenceLevel',
    
    # Configuration
    'LLMFixGeneratorConfig',
    'NIMProviderConfig',
    
    # Exceptions
    'NIMAPIException',
    
    # Advanced components (for custom integrations)
    'UnifiedLLMManager',
    'PromptEngineer',
    'LLMResponseParser',
    'ResponseValidator', 
    'StyleConsistencyChecker',
    'StyleProfile'
]


# Version information
__version__ = "1.0.0"
__author__ = "Coverity Agent Team"
__description__ = "LLM Fix Generator with NVIDIA NIM Integration" 