"""
Context Analyzer for Code Retriever

This module analyzes defects and extracts appropriate source code context
using classification hints from the Issue Parser. Integrates with ParsedDefect
objects to create CodeContext for LLM Fix Generator.
"""

import time
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime

from .config import CodeRetrieverConfig
from .source_file_manager import SourceFileManager
from .language_parser import LanguageParser
from .data_structures import (
    CodeContext, SourceLocation, ContextWindow, 
    FunctionContext, ExtractionStatistics
)
from .exceptions import ContextExtractionError


class ContextAnalyzer:
    """Main analyzer for extracting code context around defects."""
    
    def __init__(self, config: CodeRetrieverConfig = None):
        self.config = config if config else CodeRetrieverConfig()
        self.config.validate()
        
        self.file_manager = SourceFileManager(self.config)
        self.language_parser = LanguageParser(self.config)
        self.stats = ExtractionStatistics()
    
    def extract_context(self, parsed_defect) -> CodeContext:
        """Extract complete code context for a parsed defect.
        
        Args:
            parsed_defect: ParsedDefect object from Issue Parser
            
        Returns:
            CodeContext object ready for LLM Fix Generator
            
        Raises:
            ContextExtractionError: If context extraction fails
        """
        start_time = time.time()
        
        try:
            self.stats.defects_processed += 1
            
            # Create primary source location
            primary_location = SourceLocation(
                file_path=parsed_defect.file_path,
                line_number=parsed_defect.line_number,
                function_name=parsed_defect.function_name
            )
            
            # Read source file content
            try:
                lines, encoding, file_metadata = self.file_manager.read_file_content(parsed_defect.file_path)
                self.stats.files_accessed += 1
            except Exception as e:
                raise ContextExtractionError(f"Failed to read source file {parsed_defect.file_path}: {e}")
            
            # Detect language and get syntax elements
            language = self.language_parser.detect_language(parsed_defect.file_path, lines)
            file_metadata.language = language
            
            # Determine context window size based on classification hints
            before_lines, after_lines = self._get_adaptive_context_size(parsed_defect)
            
            # Extract primary context window
            context_lines, start_line, end_line = self.file_manager.get_context_window(
                parsed_defect.file_path, 
                parsed_defect.line_number,
                before_lines, 
                after_lines
            )
            
            # ADD MARKERS: Mark the problematic line for AI targeting
            marked_context_lines = self._add_defect_markers(
                context_lines, parsed_defect, start_line
            )
            
            # Calculate highlighted line within context
            highlighted_line = parsed_defect.line_number - start_line
            if highlighted_line < 0 or highlighted_line >= len(marked_context_lines):
                highlighted_line = None
            
            primary_context = ContextWindow(
                start_line=start_line,
                end_line=end_line,
                source_lines=marked_context_lines,
                highlighted_line=highlighted_line
            )
            
            # Create base CodeContext
            code_context = CodeContext.from_parsed_defect(
                parsed_defect, primary_location, primary_context, file_metadata
            )
            code_context.language = language
            
            # Add function context if available
            function_context = self._extract_function_context(
                lines, parsed_defect.line_number, language
            )
            if function_context:
                code_context.set_function_context(function_context)
            
            # Extract syntax elements
            syntax_elements = self.language_parser.get_syntax_elements(lines, language) if hasattr(self.language_parser, 'get_syntax_elements') else {}
            code_context.syntax_elements = syntax_elements
            
            # Update statistics
            self.stats.contexts_extracted += 1
            self.stats.total_context_lines += code_context.get_total_context_lines()
            
            return code_context
            
        except Exception as e:
            self.stats.extraction_errors += 1
            if isinstance(e, ContextExtractionError):
                raise
            raise ContextExtractionError(f"Context extraction failed for defect {parsed_defect.defect_id}: {e}")
        
        finally:
            self.stats.processing_time_seconds += time.time() - start_time
    
    def _get_adaptive_context_size(self, parsed_defect) -> Tuple[int, int]:
        """Determine context window size based on defect classification hints.
        
        Args:
            parsed_defect: ParsedDefect with classification hints
            
        Returns:
            Tuple of (before_lines, after_lines)
        """
        # Get base context window size from configuration
        context_config = self.config.context_window
        before_lines, after_lines = context_config.get_window_size(parsed_defect.defect_type)
        
        # Adjust based on classification hints
        if context_config.enable_adaptive_sizing:
            # Increase context for complex defects
            if parsed_defect.events and len(parsed_defect.events) > 3:
                before_lines = min(before_lines + 5, context_config.max_total_lines // 2)
                after_lines = min(after_lines + 5, context_config.max_total_lines // 2)
            
            # Increase context for resource-related defects
            if any(keyword in parsed_defect.defect_type.upper() 
                   for keyword in ['RESOURCE', 'LEAK', 'ALLOC']):
                before_lines = min(before_lines + 3, context_config.max_total_lines // 2)
                after_lines = min(after_lines + 7, context_config.max_total_lines // 2)
        
        return before_lines, after_lines
    
    def _extract_function_context(self, content_lines: List[str], target_line: int, language: str) -> Optional[FunctionContext]:
        """Extract function context containing the target line.
        
        Args:
            content_lines: Source file lines
            target_line: Target line number (1-indexed)
            language: Programming language
            
        Returns:
            FunctionContext if target is within a function, None otherwise
        """
        try:
            parsed_function = self.language_parser.find_function_containing_line(
                content_lines, target_line, language
            )
            
            if parsed_function:
                return FunctionContext(
                    name=parsed_function.name,
                    start_line=parsed_function.start_line,
                    end_line=parsed_function.end_line,
                    parameters=parsed_function.parameters if parsed_function.parameters else [],
                    return_type=parsed_function.return_type,
                    signature=parsed_function.signature,
                    is_complete=parsed_function.is_complete
                )
            
            return None
            
        except Exception:
            # Return None if function extraction fails
            return None
    
    def extract_multiple_contexts(self, parsed_defects: List) -> List[CodeContext]:
        """Extract contexts for multiple defects efficiently.
        
        Args:
            parsed_defects: List of ParsedDefect objects
            
        Returns:
            List of CodeContext objects
        """
        contexts = []
        
        for defect in parsed_defects:
            try:
                context = self.extract_context(defect)
                contexts.append(context)
            except ContextExtractionError:
                # Log error but continue with other defects
                self.stats.extraction_errors += 1
                continue
        
        return contexts
    
    def get_statistics(self) -> ExtractionStatistics:
        """Get extraction statistics.
        
        Returns:
            ExtractionStatistics object
        """
        return self.stats
    
    def reset_statistics(self):
        """Reset extraction statistics."""
        self.stats = ExtractionStatistics()
    
    def clear_caches(self):
        """Clear all internal caches."""
        self.file_manager.clear_cache()
    
    def _add_defect_markers(self, context_lines: List[str], parsed_defect, start_line: int) -> List[str]:
        """Add markers to the problematic line for AI targeting.
        
        Args:
            context_lines: Original context lines
            parsed_defect: ParsedDefect with defect information
            start_line: Starting line number of context
            
        Returns:
            Context lines with markers added to problematic line
        """
        marked_lines = context_lines.copy()
        
        # Calculate the index of the problematic line within context
        defect_line_index = parsed_defect.line_number - start_line
        
        # Validate the index
        if defect_line_index < 0 or defect_line_index >= len(marked_lines):
            return marked_lines  # Return unchanged if out of bounds
        
        # Get the original line
        original_line = marked_lines[defect_line_index]
        
        # Add unified marker for all defect types
        defect_id = parsed_defect.defect_id
        marked_lines[defect_line_index] = f"{original_line}  /* <<<FIX_HERE:{defect_id}>>> */"
        
        return marked_lines


# Convenience function for standalone usage
def extract_code_context(parsed_defect, config: CodeRetrieverConfig = None) -> CodeContext:
    """Convenience function to extract context for a single defect.
    
    Args:
        parsed_defect: ParsedDefect object from Issue Parser
        config: Optional configuration (uses defaults if None)
        
    Returns:
        CodeContext object
        
    Raises:
        ContextExtractionError: If extraction fails
    """
    analyzer = ContextAnalyzer(config)
    return analyzer.extract_context(parsed_defect)
