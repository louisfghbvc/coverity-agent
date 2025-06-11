"""
Style consistency checker for generated code fixes.

This module analyzes existing code style and ensures generated fixes
maintain consistency with the codebase's formatting and conventions.
"""

import re
import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from collections import Counter

from code_retriever.data_structures import CodeContext
from .data_structures import FixCandidate


logger = logging.getLogger(__name__)


@dataclass
class StyleProfile:
    """Code style analysis profile."""
    
    # Indentation
    indent_style: str = "spaces"  # "spaces" or "tabs"
    indent_size: int = 4
    
    # Brace style
    brace_style: str = "allman"  # "allman", "k&r", "stroustrup"
    
    # Naming conventions
    variable_naming: str = "snake_case"  # "snake_case", "camelCase", "PascalCase"
    function_naming: str = "snake_case"
    constant_naming: str = "UPPER_CASE"
    
    # Spacing
    space_after_keywords: bool = True
    space_around_operators: bool = True
    space_after_commas: bool = True
    
    # Line breaks
    max_line_length: int = 100
    blank_lines_after_functions: int = 1
    
    # Comments
    comment_style: str = "line"  # "line" (//) or "block" (/* */)
    
    # Confidence in style detection
    confidence: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert style profile to dictionary."""
        return {
            'indent_style': self.indent_style,
            'indent_size': self.indent_size,
            'brace_style': self.brace_style,
            'variable_naming': self.variable_naming,
            'function_naming': self.function_naming,
            'constant_naming': self.constant_naming,
            'space_after_keywords': self.space_after_keywords,
            'space_around_operators': self.space_around_operators,
            'space_after_commas': self.space_after_commas,
            'max_line_length': self.max_line_length,
            'blank_lines_after_functions': self.blank_lines_after_functions,
            'comment_style': self.comment_style,
            'confidence': self.confidence
        }


class StyleAnalyzer:
    """Analyzes code to determine style patterns."""
    
    def analyze_style(self, code_context: CodeContext) -> StyleProfile:
        """Analyze code context to determine style profile."""
        if not code_context.context_code:
            return StyleProfile(confidence=0.0)
        
        code = code_context.context_code
        lines = code.split('\n')
        
        profile = StyleProfile()
        
        # Analyze indentation
        indent_info = self._analyze_indentation(lines)
        profile.indent_style = indent_info['style']
        profile.indent_size = indent_info['size']
        
        # Analyze brace style
        profile.brace_style = self._analyze_brace_style(lines)
        
        # Analyze naming conventions
        naming_info = self._analyze_naming_conventions(code)
        profile.variable_naming = naming_info['variable']
        profile.function_naming = naming_info['function']
        profile.constant_naming = naming_info['constant']
        
        # Analyze spacing
        spacing_info = self._analyze_spacing(code)
        profile.space_after_keywords = spacing_info['after_keywords']
        profile.space_around_operators = spacing_info['around_operators'] 
        profile.space_after_commas = spacing_info['after_commas']
        
        # Analyze line length
        profile.max_line_length = self._analyze_line_length(lines)
        
        # Analyze comment style
        profile.comment_style = self._analyze_comment_style(lines)
        
        # Calculate overall confidence
        profile.confidence = self._calculate_style_confidence(code, profile)
        
        return profile
    
    def _analyze_indentation(self, lines: List[str]) -> Dict[str, Any]:
        """Analyze indentation patterns."""
        indented_lines = [line for line in lines if line.startswith((' ', '\t'))]
        
        if not indented_lines:
            return {'style': 'spaces', 'size': 4}
        
        # Count spaces vs tabs
        space_lines = [line for line in indented_lines if line.startswith(' ')]
        tab_lines = [line for line in indented_lines if line.startswith('\t')]
        
        if len(tab_lines) > len(space_lines):
            return {'style': 'tabs', 'size': 8}  # Default tab size
        
        # Analyze space indentation sizes
        space_counts = []
        for line in space_lines:
            spaces = len(line) - len(line.lstrip(' '))
            if spaces > 0:
                space_counts.append(spaces)
        
        if space_counts:
            # Find most common indentation size
            common_sizes = Counter(space_counts)
            most_common = common_sizes.most_common(1)[0][0]
            
            # Check for multiples (2, 4, 8)
            if most_common % 4 == 0:
                return {'style': 'spaces', 'size': 4}
            elif most_common % 2 == 0:
                return {'style': 'spaces', 'size': 2}
            else:
                return {'style': 'spaces', 'size': most_common}
        
        return {'style': 'spaces', 'size': 4}
    
    def _analyze_brace_style(self, lines: List[str]) -> str:
        """Analyze brace placement style."""
        opening_braces = []
        
        for i, line in enumerate(lines):
            stripped = line.strip()
            if '{' in stripped:
                # Check if opening brace is on same line as control structure
                if any(keyword in stripped for keyword in ['if', 'for', 'while', 'else', 'switch']):
                    if stripped.endswith('{'):
                        opening_braces.append('k&r')
                    elif i + 1 < len(lines) and lines[i + 1].strip() == '{':
                        opening_braces.append('allman')
                elif stripped == '{':
                    opening_braces.append('allman')
                elif stripped.endswith('{'):
                    opening_braces.append('k&r')
        
        if opening_braces:
            style_counter = Counter(opening_braces)
            return style_counter.most_common(1)[0][0]
        
        return 'allman'  # Default
    
    def _analyze_naming_conventions(self, code: str) -> Dict[str, str]:
        """Analyze naming conventions for variables, functions, and constants."""
        # Variable patterns
        var_pattern = r'\b(?:int|char|float|double|void|const)\s+(\w+)'
        variables = re.findall(var_pattern, code)
        
        # Function patterns  
        func_pattern = r'\b(\w+)\s*\([^)]*\)\s*{'
        functions = re.findall(func_pattern, code)
        
        # Constant patterns (uppercase definitions)
        const_pattern = r'#define\s+(\w+)'
        constants = re.findall(const_pattern, code)
        
        def determine_naming_style(names: List[str]) -> str:
            if not names:
                return 'snake_case'
            
            snake_case = sum(1 for name in names if '_' in name and name.islower())
            camel_case = sum(1 for name in names if any(c.isupper() for c in name[1:]) and '_' not in name)
            upper_case = sum(1 for name in names if name.isupper())
            
            total = len(names)
            if upper_case / total > 0.6:
                return 'UPPER_CASE'
            elif camel_case / total > 0.6:
                return 'camelCase'
            else:
                return 'snake_case'
        
        return {
            'variable': determine_naming_style(variables),
            'function': determine_naming_style(functions),
            'constant': determine_naming_style(constants) if constants else 'UPPER_CASE'
        }
    
    def _analyze_spacing(self, code: str) -> Dict[str, bool]:
        """Analyze spacing patterns."""
        # Space after keywords
        keyword_pattern = r'\b(if|for|while|switch)\s*\('
        keywords_with_space = len(re.findall(r'\b(if|for|while|switch)\s+\(', code))
        keywords_no_space = len(re.findall(r'\b(if|for|while|switch)\(', code))
        
        space_after_keywords = keywords_with_space > keywords_no_space
        
        # Space around operators
        operators_with_space = len(re.findall(r'\w\s+[+\-*/=]\s+\w', code))
        operators_no_space = len(re.findall(r'\w[+\-*/=]\w', code))
        
        space_around_operators = operators_with_space > operators_no_space
        
        # Space after commas
        commas_with_space = len(re.findall(r',\s+', code))
        commas_no_space = len(re.findall(r',[^\s]', code))
        
        space_after_commas = commas_with_space > commas_no_space
        
        return {
            'after_keywords': space_after_keywords,
            'around_operators': space_around_operators,
            'after_commas': space_after_commas
        }
    
    def _analyze_line_length(self, lines: List[str]) -> int:
        """Analyze typical line length limits."""
        line_lengths = [len(line) for line in lines if line.strip()]
        
        if not line_lengths:
            return 100
        
        # Find 90th percentile line length
        sorted_lengths = sorted(line_lengths)
        percentile_90 = sorted_lengths[int(len(sorted_lengths) * 0.9)]
        
        # Round to common limits
        if percentile_90 <= 80:
            return 80
        elif percentile_90 <= 100:
            return 100
        elif percentile_90 <= 120:
            return 120
        else:
            return 150
    
    def _analyze_comment_style(self, lines: List[str]) -> str:
        """Analyze preferred comment style."""
        line_comments = sum(1 for line in lines if '//' in line)
        block_comments = sum(1 for line in lines if '/*' in line or '*/' in line)
        
        return 'line' if line_comments > block_comments else 'block'
    
    def _calculate_style_confidence(self, code: str, profile: StyleProfile) -> float:
        """Calculate confidence in style detection."""
        # Basic confidence based on code size and pattern consistency
        code_lines = len([line for line in code.split('\n') if line.strip()])
        
        if code_lines < 5:
            return 0.3
        elif code_lines < 15:
            return 0.6
        elif code_lines < 30:
            return 0.8
        else:
            return 0.9


class StyleApplier:
    """Applies style profile to generated code."""
    
    def apply_style(self, fix_code: str, style_profile: StyleProfile) -> str:
        """Apply style profile to fix code."""
        if not fix_code.strip():
            return fix_code
        
        lines = fix_code.split('\n')
        
        # Apply indentation
        lines = self._apply_indentation(lines, style_profile)
        
        # Apply brace style
        lines = self._apply_brace_style(lines, style_profile)
        
        # Apply spacing
        lines = self._apply_spacing(lines, style_profile)
        
        # Apply line length limits
        lines = self._apply_line_length(lines, style_profile)
        
        return '\n'.join(lines)
    
    def _apply_indentation(self, lines: List[str], profile: StyleProfile) -> List[str]:
        """Apply indentation style."""
        if profile.indent_style == 'tabs':
            indent_char = '\t'
            indent_unit = 1
        else:
            indent_char = ' '
            indent_unit = profile.indent_size
        
        result = []
        for line in lines:
            if line.strip():
                # Count current indentation level
                stripped = line.lstrip()
                current_indent = len(line) - len(stripped)
                
                # Convert to indent levels (approximate)
                if profile.indent_style == 'spaces' and '\t' in line[:current_indent]:
                    # Convert tabs to spaces
                    indent_level = line[:current_indent].count('\t')
                    new_indent = indent_char * (indent_level * indent_unit)
                elif profile.indent_style == 'tabs' and ' ' in line[:current_indent]:
                    # Convert spaces to tabs (approximate)
                    indent_level = current_indent // 4  # Assume 4 spaces per level
                    new_indent = indent_char * indent_level
                else:
                    # Keep existing if already correct style
                    new_indent = line[:current_indent]
                
                result.append(new_indent + stripped)
            else:
                result.append(line)
        
        return result
    
    def _apply_brace_style(self, lines: List[str], profile: StyleProfile) -> List[str]:
        """Apply brace placement style."""
        result = []
        i = 0
        
        while i < len(lines):
            line = lines[i]
            stripped = line.strip()
            
            # Check for control structures with braces
            if any(keyword in stripped for keyword in ['if', 'for', 'while', 'else']) and '{' in stripped:
                if profile.brace_style == 'allman':
                    # Move opening brace to next line
                    if stripped.endswith('{'):
                        control_part = stripped[:-1].rstrip()
                        indent = line[:len(line) - len(line.lstrip())]
                        result.append(indent + control_part)
                        result.append(indent + '{')
                    else:
                        result.append(line)
                elif profile.brace_style == 'k&r':
                    # Keep opening brace on same line
                    if i + 1 < len(lines) and lines[i + 1].strip() == '{':
                        # Merge with next line
                        result.append(line + ' {')
                        i += 1  # Skip the standalone brace line
                    else:
                        result.append(line)
                else:
                    result.append(line)
            else:
                result.append(line)
            
            i += 1
        
        return result
    
    def _apply_spacing(self, lines: List[str], profile: StyleProfile) -> List[str]:
        """Apply spacing conventions."""
        result = []
        
        for line in lines:
            modified_line = line
            
            # Space after keywords
            if profile.space_after_keywords:
                modified_line = re.sub(r'\b(if|for|while|switch)\(', r'\1 (', modified_line)
            else:
                modified_line = re.sub(r'\b(if|for|while|switch)\s+\(', r'\1(', modified_line)
            
            # Space around operators
            if profile.space_around_operators:
                modified_line = re.sub(r'(\w)([+\-*/=])(\w)', r'\1 \2 \3', modified_line)
            else:
                modified_line = re.sub(r'(\w)\s*([+\-*/=])\s*(\w)', r'\1\2\3', modified_line)
            
            # Space after commas
            if profile.space_after_commas:
                modified_line = re.sub(r',([^\s])', r', \1', modified_line)
            else:
                modified_line = re.sub(r',\s+', ',', modified_line)
            
            result.append(modified_line)
        
        return result
    
    def _apply_line_length(self, lines: List[str], profile: StyleProfile) -> List[str]:
        """Apply line length limits (basic implementation)."""
        result = []
        
        for line in lines:
            if len(line) <= profile.max_line_length:
                result.append(line)
            else:
                # Simple line breaking at logical points
                if ',' in line and not line.strip().startswith('//'):
                    # Break at commas
                    parts = line.split(',')
                    current_line = parts[0]
                    indent = ' ' * (len(line) - len(line.lstrip()) + 4)  # Add extra indent
                    
                    for part in parts[1:]:
                        if len(current_line + ',' + part.strip()) <= profile.max_line_length:
                            current_line += ',' + part.strip()
                        else:
                            result.append(current_line + ',')
                            current_line = indent + part.strip()
                    
                    result.append(current_line)
                else:
                    # Just add the line as-is if we can't break it nicely
                    result.append(line)
        
        return result


class StyleConsistencyChecker:
    """Main style consistency checker that combines analysis and application."""
    
    def __init__(self):
        self.analyzer = StyleAnalyzer()
        self.applier = StyleApplier()
    
    def check_and_fix_style(self, fix_candidate: FixCandidate, 
                          code_context: CodeContext) -> Tuple[str, float]:
        """
        Check style consistency and apply fixes.
        
        Returns:
            Tuple of (styled_code, consistency_score)
        """
        # Analyze existing code style
        style_profile = self.analyzer.analyze_style(code_context)
        
        # Apply style to fix code
        styled_code = self.applier.apply_style(fix_candidate.fix_code, style_profile)
        
        # Calculate consistency score
        consistency_score = self._calculate_consistency_score(
            fix_candidate.fix_code, styled_code, style_profile
        )
        
        logger.debug(f"Style consistency score: {consistency_score:.2f}")
        
        return styled_code, consistency_score
    
    def _calculate_consistency_score(self, original_code: str, styled_code: str, 
                                   profile: StyleProfile) -> float:
        """Calculate how well the styled code matches the profile."""
        if not original_code.strip():
            return 1.0
        
        # Base score from profile confidence
        score = profile.confidence * 0.3
        
        # Add points for successful transformations
        if original_code != styled_code:
            score += 0.4  # Style was successfully applied
        else:
            score += 0.2  # Code already matched style
        
        # Add points for specific style elements
        lines = styled_code.split('\n')
        
        # Check indentation consistency
        indented_lines = [line for line in lines if line.startswith((' ', '\t'))]
        if indented_lines:
            if profile.indent_style == 'tabs':
                correct_indent = all('\t' in line for line in indented_lines if line.strip())
            else:
                correct_indent = all(' ' in line and '\t' not in line for line in indented_lines)
            
            if correct_indent:
                score += 0.2
        
        # Check brace style
        brace_lines = [line for line in lines if '{' in line]
        if brace_lines:
            score += 0.1  # Basic points for having braces
        
        return min(score, 1.0) 