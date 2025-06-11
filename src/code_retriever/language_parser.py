"""
Language Parser for Code Retriever

This module provides language detection and basic parsing capabilities for C/C++
source code. Handles function boundary detection and syntax analysis.
"""

import re
from typing import List, Optional, Tuple, Dict, Any
from pathlib import Path
from dataclasses import dataclass

from .config import CodeRetrieverConfig
from .data_structures import FunctionContext
from .exceptions import LanguageDetectionError, ParsingError


@dataclass
class ParsedFunction:
    """Represents a parsed function with its boundaries and metadata."""
    
    name: str
    start_line: int
    end_line: int
    signature: str
    return_type: str = ""
    parameters: List[str] = None
    is_complete: bool = True
    
    def __post_init__(self):
        if self.parameters is None:
            self.parameters = []


class LanguageParser:
    """Language-specific parser for source code analysis."""
    
    def __init__(self, config: CodeRetrieverConfig):
        self.config = config
    
    def detect_language(self, file_path: str, content_lines: List[str]) -> str:
        """Detect programming language from file path and content."""
        try:
            # First try file extension
            path = Path(file_path)
            extension = path.suffix.lower()
            
            if extension in self.config.extension_mappings:
                return self.config.extension_mappings[extension]
            
            # Default to C for unknown
            return "c"
            
        except Exception as e:
            raise LanguageDetectionError(f"Failed to detect language for {file_path}: {e}")
    
    def find_functions(self, content_lines: List[str], language: str) -> List[ParsedFunction]:
        """Find function boundaries in source code."""
        if language not in self.config.primary_languages:
            return []
        
        try:
            return self._find_functions_by_braces(content_lines, language)
        except Exception as e:
            raise ParsingError(f"Failed to parse functions in {language}: {e}")
    
    def _find_functions_by_braces(self, content_lines: List[str], language: str) -> List[ParsedFunction]:
        """Find functions using brace counting method."""
        functions = []
        
        i = 0
        while i < len(content_lines):
            line = content_lines[i].strip()
            
            # Skip empty lines and comments
            if not line or line.startswith('//') or line.startswith('/*'):
                i += 1
                continue
            
            # Look for function-like patterns
            if self._looks_like_function_start(line, language):
                function = self._parse_function_from_line(content_lines, i, language)
                if function:
                    functions.append(function)
                    i = function.end_line
                else:
                    i += 1
            else:
                i += 1
        
        return functions
    
    def _looks_like_function_start(self, line: str, language: str) -> bool:
        """Check if line looks like start of a function definition."""
        if not line or line.startswith('#'):
            return False
        
        if '(' not in line:
            return False
        
        if any(keyword in line for keyword in ['if ', 'while ', 'for ', 'switch ']):
            return False
        
        if line.rstrip().endswith('{') or (')' in line and not line.rstrip().endswith(';')):
            return True
        
        return False
    
    def _parse_function_from_line(self, content_lines: List[str], start_idx: int, language: str) -> Optional[ParsedFunction]:
        """Parse function starting from given line index."""
        try:
            # Find the opening brace
            brace_line = start_idx
            while brace_line < len(content_lines):
                if '{' in content_lines[brace_line]:
                    break
                brace_line += 1
            else:
                return None
            
            # Count braces to find function end
            brace_count = 0
            end_line = brace_line
            
            for line_idx in range(brace_line, len(content_lines)):
                line = content_lines[line_idx]
                
                for char in line:
                    if char == '{':
                        brace_count += 1
                    elif char == '}':
                        brace_count -= 1
                        if brace_count == 0:
                            end_line = line_idx + 1
                            break
                
                if brace_count == 0:
                    break
            
            # Extract function signature
            signature_lines = content_lines[start_idx:brace_line + 1]
            signature = ' '.join(line.strip() for line in signature_lines).replace('{', '').strip()
            
            # Extract function name
            name = self._extract_function_name(signature)
            
            if name and end_line > start_idx:
                return ParsedFunction(
                    name=name,
                    start_line=start_idx + 1,
                    end_line=end_line,
                    signature=signature,
                    is_complete=True
                )
            
            return None
            
        except Exception:
            return None
    
    def _extract_function_name(self, signature: str) -> Optional[str]:
        """Extract function name from signature."""
        match = re.search(r'(\w+)\s*\(', signature)
        if match:
            return match.group(1)
        return None
    
    def find_function_containing_line(self, content_lines: List[str], target_line: int, language: str) -> Optional[ParsedFunction]:
        """Find the function that contains the given line number."""
        functions = self.find_functions(content_lines, language)
        
        for function in functions:
            if function.start_line <= target_line <= function.end_line:
                return function
        
        return None
    
    def get_syntax_elements(self, content_lines: List[str], language: str) -> Dict[str, Any]:
        """Extract basic syntax elements for the given language.
        
        Args:
            content_lines: Lines of source code
            language: Programming language
            
        Returns:
            Dictionary of syntax elements
        """
        elements = {
            "language": language,
            "total_lines": len(content_lines),
            "functions": [],
            "includes": [],
            "comments": []
        }
        
        try:
            # Find functions
            functions = self.find_functions(content_lines, language)
            elements["functions"] = [
                {
                    "name": func.name,
                    "start_line": func.start_line,
                    "end_line": func.end_line,
                    "signature": func.signature
                }
                for func in functions
            ]
            
            # Find include statements
            for i, line in enumerate(content_lines, 1):
                stripped = line.strip()
                if stripped.startswith('#include'):
                    elements["includes"].append({
                        "line": i,
                        "content": stripped
                    })
            
            # Basic comment detection
            for i, line in enumerate(content_lines, 1):
                stripped = line.strip()
                if stripped.startswith('//') or stripped.startswith('/*'):
                    elements["comments"].append({
                        "line": i,
                        "type": "single" if stripped.startswith('//') else "multi"
                    })
            
        except Exception:
            # Return basic elements on error
            pass
        
        return elements
