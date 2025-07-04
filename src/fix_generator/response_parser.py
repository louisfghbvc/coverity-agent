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
        
        # Validate false positive fields
        is_false_positive = analysis.get('is_false_positive')
        if is_false_positive is not None:
            if not isinstance(is_false_positive, bool):
                errors.append(f"is_false_positive must be boolean, got {type(is_false_positive)}")
            
            # If marked as false positive, reason should be provided
            if is_false_positive and not analysis.get('false_positive_reason'):
                errors.append("false_positive_reason required when is_false_positive is true")
        
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
        
        # Validate fix type (new field for suppression support)
        fix_type = candidate.get('fix_type', '').lower()
        valid_fix_types = ['code_fix', 'suppression']
        if fix_type and fix_type not in valid_fix_types:
            errors.append(f"Fix candidate {index} invalid fix_type '{fix_type}', must be one of: {valid_fix_types}")
        
        # If fix_type is suppression, validate that fix_code contains coverity comment
        if fix_type == 'suppression':
            fix_code = candidate.get('fix_code', [])
            if isinstance(fix_code, list):
                fix_code_str = '\n'.join(fix_code)
            else:
                fix_code_str = str(fix_code)
            
            if '// coverity[' not in fix_code_str:
                errors.append(f"Fix candidate {index} marked as suppression but missing '// coverity[' comment")
        
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
        
        # Debug: Log the raw response for investigation
        logger.info(f"Raw AI response for defect {defect.defect_id} (first 500 chars): {raw_response[:500]}")
        logger.info(f"Raw AI response length: {len(raw_response)} characters")
        
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
            result = self._parse_structured_text_response(raw_response, defect)
            logger.info(f"Successfully parsed using structured text parsing for defect {defect.defect_id}")
            return result
        except Exception as e:
            parsing_errors.append(f"Structured text parsing failed: {e}")
            logger.debug(f"Structured text parsing failed for defect {defect.defect_id}: {e}")
        
        # Strategy 4: Fallback - extract code blocks
        logger.warning(f"All parsing strategies failed for defect {defect.defect_id}, using fallback")
        return self._parse_fallback_response(raw_response, defect, parsing_errors)
    
    def _parse_json_response(self, raw_response: str, defect: ParsedDefect) -> ParsedResponse:
        """Parse direct JSON response with robust error handling."""
        try:
            response_data = json.loads(raw_response)
            return self._validate_and_create_parsed_response(response_data, raw_response, defect)
        except json.JSONDecodeError as e:
            # Try to fix common JSON issues
            cleaned_json = self._clean_json_response(raw_response)
            if cleaned_json:
                try:
                    response_data = json.loads(cleaned_json)
                    logger.info(f"Successfully parsed JSON after cleaning for defect {defect.defect_id}")
                    return self._validate_and_create_parsed_response(response_data, raw_response, defect)
                except json.JSONDecodeError:
                    pass
            
            # If still failing, re-raise the original error
            raise e
    
    def _clean_json_response(self, raw_response: str) -> Optional[str]:
        """Clean and fix common JSON formatting issues."""
        try:
            # Remove any leading/trailing whitespace
            cleaned = raw_response.strip()
            
            # Remove trailing commas before closing brackets/braces
            cleaned = re.sub(r',(\s*[}\]])', r'\1', cleaned)
            
            # Fix unescaped quotes in strings (basic attempt)
            # This is a simple fix - more sophisticated parsing might be needed
            lines = cleaned.split('\n')
            fixed_lines = []
            
            for line in lines:
                # Skip lines that are clearly not JSON content
                if line.strip().startswith('//') or line.strip().startswith('#'):
                    continue
                
                # Remove inline comments (// comments)
                if '//' in line and not line.strip().startswith('"'):
                    # Find // that's not inside a string
                    in_string = False
                    escape_next = False
                    comment_pos = -1
                    
                    for i, char in enumerate(line):
                        if escape_next:
                            escape_next = False
                            continue
                        if char == '\\':
                            escape_next = True
                            continue
                        if char == '"':
                            in_string = not in_string
                            continue
                        if not in_string and char == '/' and i + 1 < len(line) and line[i + 1] == '/':
                            comment_pos = i
                            break
                    
                    if comment_pos >= 0:
                        line = line[:comment_pos].rstrip()
                
                fixed_lines.append(line)
            
            cleaned = '\n'.join(fixed_lines)
            
            # Try to validate the cleaned JSON
            json.loads(cleaned)
            return cleaned
            
        except Exception:
            return None
    
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
        # First check if this looks like a malformed JSON that we should try to extract from
        if raw_response.strip().startswith('{') and 'fix_candidates' in raw_response:
            logger.debug(f"Structured text parser detected JSON-like content, attempting extraction")
            try:
                return self._extract_from_malformed_json(raw_response, defect)
            except Exception as e:
                logger.debug(f"JSON extraction failed: {e}, falling back to text parsing")
        
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
            
            # Skip JSON-like lines that shouldn't be treated as code
            if line.startswith('{') or line.startswith('}') or line.startswith('"fix_code":'):
                continue
            
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
    
    def _extract_from_malformed_json(self, raw_response: str, defect: ParsedDefect) -> ParsedResponse:
        """Extract data from malformed JSON response."""
        # Try to find the fix_code array in the response
        fix_code_pattern = r'"fix_code":\s*\[(.*?)\]'
        match = re.search(fix_code_pattern, raw_response, re.DOTALL)
        
        if match:
            fix_code_content = match.group(1)
            # Extract individual lines from the array
            line_pattern = r'"([^"]*)"'
            lines = re.findall(line_pattern, fix_code_content)
            
            if lines:
                fix_code = '\n'.join(lines)
                
                # Try to extract other fields
                explanation_match = re.search(r'"explanation":\s*"([^"]*)"', raw_response)
                explanation = explanation_match.group(1) if explanation_match else "Extracted from malformed JSON"
                
                confidence_match = re.search(r'"confidence":\s*([0-9.]+)', raw_response)
                confidence = float(confidence_match.group(1)) if confidence_match else 0.5
                
                # Create response data
                response_data = {
                    'defect_analysis': {
                        'category': 'extracted',
                        'severity': 'medium',
                        'complexity': 'moderate',
                        'confidence': confidence
                    },
                    'fix_candidates': [{
                        'fix_code': fix_code,
                        'explanation': explanation,
                        'confidence': confidence
                    }],
                    'reasoning': 'Extracted from malformed JSON response'
                }
                
                logger.info(f"Successfully extracted fix from malformed JSON for defect {defect.defect_id}")
                return self._validate_and_create_parsed_response(response_data, raw_response, defect)
        
        raise ValueError("Could not extract valid data from malformed JSON")
    
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