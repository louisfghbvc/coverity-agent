"""
Response parser and validator for NVIDIA NIM API responses.

This module provides structured parsing and validation of LLM responses
for defect analysis and fix generation.
"""

import json
import re
import ast
import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass

from .data_structures import (
    DefectAnalysisResult, FixCandidate, FixComplexity, 
    DefectSeverity, NIMMetadata
)
from issue_parser.data_structures import ParsedDefect


logger = logging.getLogger(__name__)


@dataclass
class ParsedResponse:
    """Container for parsed LLM response components."""
    
    defect_analysis: Dict[str, Any]
    fix_candidates: List[Dict[str, Any]]
    reasoning: str
    confidence_score: float
    parsing_errors: List[str]
    raw_response: str


class ResponseValidator:
    """Validates parsed responses for correctness and completeness."""
    
    @staticmethod
    def validate_defect_analysis(analysis: Dict[str, Any]) -> List[str]:
        """Validate defect analysis section."""
        errors = []
        
        required_fields = ['category', 'severity', 'complexity', 'confidence']
        for field in required_fields:
            if field not in analysis:
                errors.append(f"Missing required field in defect_analysis: {field}")
        
        # Validate confidence score
        confidence = analysis.get('confidence')
        if confidence is not None:
            try:
                conf_float = float(confidence)
                if not (0.0 <= conf_float <= 1.0):
                    errors.append(f"Confidence score must be 0.0-1.0, got {conf_float}")
            except (ValueError, TypeError):
                errors.append(f"Invalid confidence score format: {confidence}")
        
        # Validate severity
        severity = analysis.get('severity', '').lower()
        valid_severities = [e.value for e in DefectSeverity]
        if severity and severity not in valid_severities:
            errors.append(f"Invalid severity '{severity}', must be one of: {valid_severities}")
        
        # Validate complexity
        complexity = analysis.get('complexity', '').lower()
        valid_complexities = [e.value for e in FixComplexity]
        if complexity and complexity not in valid_complexities:
            errors.append(f"Invalid complexity '{complexity}', must be one of: {valid_complexities}")
        
        return errors
    
    @staticmethod
    def validate_fix_candidate(candidate: Dict[str, Any], index: int) -> List[str]:
        """Validate a single fix candidate."""
        errors = []
        
        required_fields = ['fix_code', 'explanation', 'confidence']
        for field in required_fields:
            if field not in candidate:
                errors.append(f"Fix candidate {index} missing required field: {field}")
            elif not candidate[field]:
                errors.append(f"Fix candidate {index} has empty {field}")
        
        # Validate confidence score
        confidence = candidate.get('confidence')
        if confidence is not None:
            try:
                conf_float = float(confidence)
                if not (0.0 <= conf_float <= 1.0):
                    errors.append(f"Fix candidate {index} confidence must be 0.0-1.0, got {conf_float}")
            except (ValueError, TypeError):
                errors.append(f"Fix candidate {index} invalid confidence format: {confidence}")
        
        # Validate complexity
        complexity = candidate.get('complexity', '').lower()
        valid_complexities = [e.value for e in FixComplexity]
        if complexity and complexity not in valid_complexities:
            errors.append(f"Fix candidate {index} invalid complexity '{complexity}'")
        
        # Validate replacement type (new field)
        replacement_type = candidate.get('replacement_type', '').lower()
        valid_replacement_types = ['content_replace', 'line_insert', 'line_replace']
        if replacement_type and replacement_type not in valid_replacement_types:
            errors.append(f"Fix candidate {index} invalid replacement_type '{replacement_type}', must be one of: {valid_replacement_types}")
        
        # Validate target location (new field)
        target_location = candidate.get('target_location')
        if target_location and isinstance(target_location, dict):
            if 'line' not in target_location:
                errors.append(f"Fix candidate {index} target_location missing 'line' field")
            else:
                try:
                    line_num = int(target_location['line'])
                    if line_num <= 0:
                        errors.append(f"Fix candidate {index} target_location line must be positive")
                except (ValueError, TypeError):
                    errors.append(f"Fix candidate {index} target_location line must be a number")
        
        # Validate line ranges (legacy support)
        line_ranges = candidate.get('line_ranges', [])
        if line_ranges:
            for i, line_range in enumerate(line_ranges):
                if not isinstance(line_range, dict):
                    errors.append(f"Fix candidate {index} line_range {i} must be a dict")
                    continue
                
                if 'start' not in line_range or 'end' not in line_range:
                    errors.append(f"Fix candidate {index} line_range {i} missing start/end")
                    continue
                
                try:
                    start = int(line_range['start'])
                    end = int(line_range['end'])
                    if start > end:
                        errors.append(f"Fix candidate {index} line_range {i} start > end")
                    if start <= 0 or end <= 0:
                        errors.append(f"Fix candidate {index} line_range {i} must be positive")
                except (ValueError, TypeError):
                    errors.append(f"Fix candidate {index} line_range {i} invalid numbers")
        
        # Validate content markers in fix_code
        fix_code = candidate.get('fix_code', '')
        if fix_code:
            # Check for valid marker patterns
            has_replace_markers = '<<<REPLACE_START>>>' in fix_code and '<<<REPLACE_END>>>' in fix_code
            has_insert_markers = '<<<INSERT_AFTER_LINE:' in fix_code and '<<<INSERT_END>>>' in fix_code
            has_line_replace_markers = '<<<LINE_REPLACE:' in fix_code and '<<<LINE_REPLACE_END>>>' in fix_code
            
            # If replacement_type is specified, validate corresponding markers
            if replacement_type == 'content_replace' and not has_replace_markers:
                errors.append(f"Fix candidate {index} specified content_replace but missing REPLACE_START/REPLACE_END markers")
            elif replacement_type == 'line_insert' and not has_insert_markers:
                errors.append(f"Fix candidate {index} specified line_insert but missing INSERT_AFTER_LINE markers")
            elif replacement_type == 'line_replace' and not has_line_replace_markers:
                errors.append(f"Fix candidate {index} specified line_replace but missing LINE_REPLACE markers")
        
        return errors
    
    @staticmethod
    def validate_syntax(code: str, language: str = 'c') -> Tuple[bool, List[str]]:
        """Basic syntax validation for generated code."""
        errors = []
        
        if not code.strip():
            return False, ["Empty code"]
        
        # Basic C/C++ syntax checks
        if language.lower() in ['c', 'cpp', 'c++']:
            # Check for balanced braces
            open_braces = code.count('{')
            close_braces = code.count('}')
            if open_braces != close_braces:
                errors.append(f"Mismatched braces: {open_braces} open, {close_braces} close")
            
            # Check for balanced parentheses
            open_parens = code.count('(')
            close_parens = code.count(')')
            if open_parens != close_parens:
                errors.append(f"Mismatched parentheses: {open_parens} open, {close_parens} close")
            
            # Check for semicolons (basic check)
            lines = [line.strip() for line in code.split('\n') if line.strip()]
            statement_lines = [line for line in lines 
                             if not line.startswith('//') and not line.startswith('/*') 
                             and not line.startswith('#') and not line.endswith('{') 
                             and not line.endswith('}') and line != '}']
            
            missing_semicolons = [line for line in statement_lines 
                                if not line.endswith(';') and not line.endswith(',')]
            
            if len(missing_semicolons) > len(statement_lines) * 0.3:  # More than 30% missing
                errors.append("Many statements appear to be missing semicolons")
        
        return len(errors) == 0, errors


class LLMResponseParser:
    """Main parser for LLM responses with fallback strategies."""
    
    def __init__(self, enable_validation: bool = True):
        self.enable_validation = enable_validation
        self.validator = ResponseValidator()
    
    def parse_response(self, raw_response: str, defect: ParsedDefect) -> ParsedResponse:
        """Parse LLM response with multiple strategies."""
        parsing_errors = []
        
        # Strategy 1: Try JSON parsing
        try:
            return self._parse_json_response(raw_response, defect)
        except Exception as e:
            parsing_errors.append(f"JSON parsing failed: {e}")
            logger.debug(f"JSON parsing failed for defect {defect.defect_id}: {e}")
        
        # Strategy 2: Try extracting JSON from markdown
        try:
            return self._parse_markdown_json_response(raw_response, defect)
        except Exception as e:
            parsing_errors.append(f"Markdown JSON parsing failed: {e}")
            logger.debug(f"Markdown JSON parsing failed for defect {defect.defect_id}: {e}")
        
        # Strategy 3: Try structured text parsing
        try:
            return self._parse_structured_text_response(raw_response, defect)
        except Exception as e:
            parsing_errors.append(f"Structured text parsing failed: {e}")
            logger.debug(f"Structured text parsing failed for defect {defect.defect_id}: {e}")
        
        # Strategy 4: Fallback - extract code blocks
        logger.warning(f"All parsing strategies failed for defect {defect.defect_id}, using fallback")
        return self._parse_fallback_response(raw_response, defect, parsing_errors)
    
    def _parse_json_response(self, raw_response: str, defect: ParsedDefect) -> ParsedResponse:
        """Parse direct JSON response."""
        response_data = json.loads(raw_response)
        return self._validate_and_create_parsed_response(response_data, raw_response, defect)
    
    def _parse_markdown_json_response(self, raw_response: str, defect: ParsedDefect) -> ParsedResponse:
        """Extract JSON from markdown code blocks."""
        # Look for JSON in code blocks
        json_pattern = r'```(?:json)?\s*(\{.*?\})\s*```'
        matches = re.findall(json_pattern, raw_response, re.DOTALL | re.IGNORECASE)
        
        for match in matches:
            try:
                response_data = json.loads(match)
                return self._validate_and_create_parsed_response(response_data, raw_response, defect)
            except json.JSONDecodeError:
                continue
        
        # Try finding JSON without code blocks
        json_pattern = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'
        matches = re.findall(json_pattern, raw_response, re.DOTALL)
        
        for match in matches:
            try:
                response_data = json.loads(match)
                if 'defect_analysis' in response_data or 'fix_candidates' in response_data:
                    return self._validate_and_create_parsed_response(response_data, raw_response, defect)
            except json.JSONDecodeError:
                continue
        
        raise ValueError("No valid JSON found in response")
    
    def _parse_structured_text_response(self, raw_response: str, defect: ParsedDefect) -> ParsedResponse:
        """Parse structured text response using patterns."""
        lines = raw_response.split('\n')
        
        # Extract sections
        defect_analysis = {}
        fix_candidates = []
        reasoning = ""
        current_section = None
        current_candidate = None
        current_code = []
        
        for line in lines:
            line = line.strip()
            
            # Section headers
            if line.lower().startswith('defect analysis') or 'analysis:' in line.lower():
                current_section = 'analysis'
            elif line.lower().startswith('fix candidate') or 'candidate' in line.lower():
                # Save previous candidate if exists
                if current_candidate and current_code:
                    current_candidate['fix_code'] = '\n'.join(current_code)
                    fix_candidates.append(current_candidate)
                
                current_candidate = {'fix_code': '', 'explanation': '', 'confidence': 0.5}
                current_code = []
                current_section = 'candidate'
            elif line.lower().startswith('reasoning') or 'reason:' in line.lower():
                current_section = 'reasoning'
            
            # Extract values
            if current_section == 'analysis':
                if ':' in line:
                    key, value = line.split(':', 1)
                    key = key.strip().lower().replace(' ', '_')
                    value = value.strip()
                    
                    if key in ['category', 'severity', 'complexity']:
                        defect_analysis[key] = value
                    elif key == 'confidence':
                        try:
                            defect_analysis['confidence'] = float(value)
                        except ValueError:
                            defect_analysis['confidence'] = 0.5
            
            elif current_section == 'candidate' and current_candidate:
                if line.startswith('```') or line.startswith('```c'):
                    continue  # Skip code block markers
                elif ':' in line and not any(c in line for c in ['{', '}', ';']):
                    key, value = line.split(':', 1)
                    key = key.strip().lower().replace(' ', '_')
                    value = value.strip()
                    
                    if key == 'explanation':
                        current_candidate['explanation'] = value
                    elif key == 'confidence':
                        try:
                            current_candidate['confidence'] = float(value)
                        except ValueError:
                            current_candidate['confidence'] = 0.5
                else:
                    current_code.append(line)
            
            elif current_section == 'reasoning':
                reasoning += line + '\n'
        
        # Save last candidate
        if current_candidate and current_code:
            current_candidate['fix_code'] = '\n'.join(current_code)
            fix_candidates.append(current_candidate)
        
        if not fix_candidates:
            raise ValueError("No fix candidates found in structured text")
        
        response_data = {
            'defect_analysis': defect_analysis,
            'fix_candidates': fix_candidates,
            'reasoning': reasoning.strip()
        }
        
        return self._validate_and_create_parsed_response(response_data, raw_response, defect)
    
    def _parse_fallback_response(self, raw_response: str, defect: ParsedDefect, 
                                parsing_errors: List[str]) -> ParsedResponse:
        """Fallback parsing - extract any code blocks found."""
        # Extract code blocks
        code_pattern = r'```(?:c|cpp|c\+\+)?\s*(.*?)\s*```'
        code_blocks = re.findall(code_pattern, raw_response, re.DOTALL | re.IGNORECASE)
        
        if not code_blocks:
            # Try to find any code-like content
            lines = raw_response.split('\n')
            code_lines = []
            for line in lines:
                if any(keyword in line for keyword in ['if', 'for', 'while', 'return', '{', '}', ';']):
                    code_lines.append(line)
            
            if code_lines:
                code_blocks = ['\n'.join(code_lines)]
            else:
                code_blocks = [raw_response[:200]]  # Use first 200 chars as fallback
        
        # Create basic fix candidates from code blocks
        fix_candidates = []
        for i, code in enumerate(code_blocks):
            fix_candidates.append({
                'fix_code': code.strip(),
                'explanation': f'Fallback extraction {i+1} - manual review required',
                'confidence': 0.2,
                'complexity': 'moderate',
                'risk_assessment': 'High - requires manual verification',
                'affected_files': [defect.file_path],
                'line_ranges': [{'start': defect.line_number, 'end': defect.line_number}]
            })
        
        if not fix_candidates:
            fix_candidates.append({
                'fix_code': '// No code extracted - manual analysis required',
                'explanation': 'Automated parsing failed completely',
                'confidence': 0.0,
                'complexity': 'high_risk',
                'risk_assessment': 'Very high - complete manual review needed',
                'affected_files': [defect.file_path],
                'line_ranges': [{'start': defect.line_number, 'end': defect.line_number}]
            })
        
        return ParsedResponse(
            defect_analysis={
                'category': 'unknown',
                'severity': 'medium', 
                'complexity': 'moderate',
                'confidence': 0.1
            },
            fix_candidates=fix_candidates,
            reasoning='Fallback parsing used - original response could not be parsed',
            confidence_score=0.1,
            parsing_errors=parsing_errors,
            raw_response=raw_response
        )
    
    def _validate_and_create_parsed_response(self, response_data: Dict[str, Any], 
                                           raw_response: str, defect: ParsedDefect) -> ParsedResponse:
        """Validate parsed data and create ParsedResponse."""
        errors = []
        
        # Extract sections with defaults
        defect_analysis = response_data.get('defect_analysis', {})
        fix_candidates = response_data.get('fix_candidates', [])
        reasoning = response_data.get('reasoning', '')
        
        # Validate if enabled
        if self.enable_validation:
            errors.extend(self.validator.validate_defect_analysis(defect_analysis))
            
            for i, candidate in enumerate(fix_candidates):
                errors.extend(self.validator.validate_fix_candidate(candidate, i))
        
        # Ensure minimum required data
        if not fix_candidates:
            errors.append("No fix candidates provided")
            fix_candidates = [{
                'fix_code': '// No fix provided',
                'explanation': 'No fix candidates were generated',
                'confidence': 0.0
            }]
        
        # Calculate overall confidence
        if fix_candidates and 'confidence' in defect_analysis:
            confidence_score = float(defect_analysis['confidence'])
        elif fix_candidates:
            # Average candidate confidence
            candidate_confidences = []
            for candidate in fix_candidates:
                try:
                    candidate_confidences.append(float(candidate.get('confidence', 0.5)))
                except (ValueError, TypeError):
                    candidate_confidences.append(0.5)
            confidence_score = sum(candidate_confidences) / len(candidate_confidences)
        else:
            confidence_score = 0.0
        
        return ParsedResponse(
            defect_analysis=defect_analysis,
            fix_candidates=fix_candidates,
            reasoning=reasoning,
            confidence_score=confidence_score,
            parsing_errors=errors,
            raw_response=raw_response
        ) 