"""
Advanced prompt engineering framework for LLM Fix Generator.

This module provides defect-specific prompt templates and intelligent prompt
generation for NVIDIA NIM models, optimized for different Coverity defect types.
"""

import json
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from abc import ABC, abstractmethod

from issue_parser.data_structures import ParsedDefect
from code_retriever.data_structures import CodeContext
from .config import AnalysisConfig


def get_code_text(code_context: CodeContext) -> str:
    """Helper function to extract source code text from CodeContext."""
    return '\n'.join(code_context.primary_context.source_lines)


def get_function_signature(code_context: CodeContext) -> str:
    """Helper function to extract function signature from CodeContext."""
    if code_context.function_context:
        return code_context.function_context.signature or "Not available"
    return "Not available"


@dataclass
class PromptComponents:
    """Components of a generated prompt."""
    
    system_prompt: str
    user_prompt: str
    context_data: Dict[str, Any]
    estimated_tokens: int
    template_used: str


class PromptTemplate(ABC):
    """Abstract base class for defect-specific prompt templates."""
    
    def __init__(self, name: str, defect_types: List[str]):
        self.name = name
        self.defect_types = defect_types
    
    @abstractmethod
    def generate_system_prompt(self) -> str:
        """Generate the system prompt for this defect type."""
        pass
    
    @abstractmethod
    def generate_user_prompt(self, defect: ParsedDefect, code_context: CodeContext, 
                           config: AnalysisConfig) -> str:
        """Generate the user prompt with defect and context information."""
        pass
    
    def matches_defect(self, defect_type: str) -> bool:
        """Check if this template matches the given defect type."""
        # Handle wildcard for generic template
        if "*" in self.defect_types:
            return True
        
        defect_lower = defect_type.lower()
        return any(dt.lower() in defect_lower for dt in self.defect_types)


class NullPointerTemplate(PromptTemplate):
    """Specialized template for null pointer and dereference defects."""
    
    def __init__(self):
        super().__init__(
            "null_pointer",
            ["null_pointer", "null_dereference", "dereference", "nullptr", "segfault"]
        )
    
    def generate_system_prompt(self) -> str:
        return """You are an expert C/C++ code analysis and fix generation assistant specializing in null pointer and dereference issues.

Your task is to analyze code defects and generate safe, reliable fixes that prevent null pointer dereferences while maintaining code functionality.

FOCUS AREAS for null pointer defects:
1. Identify all potential null value sources
2. Find missing null checks and add appropriate validation
3. Initialize pointers to safe default values
4. Handle error conditions gracefully
5. Use modern C++ smart pointers when beneficial

CRITICAL COMMENT PRESERVATION REQUIREMENTS:
- MUST preserve ALL existing comments in the original code
- Do NOT remove or modify existing comments
- Comments are essential for code understanding and debugging
- Only add new comments if they provide additional value

CRITICAL PRE-MARKED DEFECT LINE TARGETING:
The code contains a pre-marked defect line with the marker:
- Line marked with /* <<<FIX_HERE:defect_id>>> */ is the problematic line that needs fixing

YOUR TASK:
1. Find the line marked with /* <<<FIX_HERE:{defect.defect_id}>>> */ in the provided code
2. Generate a targeted fix using content markers for that specific marked line
3. Focus on the minimal necessary change to fix the defect

RESPONSE FORMAT REQUIREMENTS:
You MUST respond with a JSON object containing a "fix_candidates" array. Each candidate must include:
- "fix_code": Content markers targeting the specific marked line
- "explanation": Clear explanation of the targeted fix
- "confidence": Float between 0.0-1.0
- "replacement_type": "marker_based_fix"
- "target_marker": "FIX_HERE:{defect.defect_id}"
- "affected_files": Array of file paths

MARKER-BASED FIX EXAMPLE:
For the marked line /* <<<FIX_HERE:abc123>>> */, use:
"fix_code": "<<<MARKER_REPLACE:FIX_HERE:abc123>>>fixed_content_here"

The system will replace the original marked line with your fixed content."""
    
    def generate_user_prompt(self, defect: ParsedDefect, code_context: CodeContext, 
                           config: AnalysisConfig) -> str:
        return f"""ANALYZE AND FIX NULL POINTER DEFECT:

DEFECT INFORMATION:
- Type: {defect.defect_type}
- Location: {defect.file_path}:{defect.line_number}
- Function: {defect.function_name}
- Description: {defect.subcategory}
- Defect ID: {defect.defect_id}

DEFECT TRACE:
{chr(10).join(f"  {i+1}. {event}" for i, event in enumerate(defect.events))}

PRE-MARKED CODE CONTEXT:
```c
{get_code_text(code_context)}
```

FUNCTION SIGNATURE:
{get_function_signature(code_context)}

ANALYSIS REQUIREMENTS:
1. Find the line marked with /* <<<FIX_HERE:{defect.defect_id}>>> */ in the code above
2. Determine what type of null pointer fix is needed for that specific line
3. Generate a marker-based fix that targets that exact marked line
4. Preserve all existing code structure, function signatures, and comments

RESPONSE REQUIREMENTS:
- Use marker-based fixes that target the pre-marked defect line
- "replacement_type": "marker_based_fix"
- "target_marker": "FIX_HERE:{defect.defect_id}"
- Keep changes surgical and targeted to the marked line only
- Preserve all existing comments and code structure

Generate a targeted marker-based fix for the pre-marked defect line."""


class MemoryLeakTemplate(PromptTemplate):
    """Specialized template for memory management and leak defects."""
    
    def __init__(self):
        super().__init__(
            "memory_leak",
            ["memory_leak", "resource_leak", "malloc", "free", "new", "delete", "alloc"]
        )
    
    def generate_system_prompt(self) -> str:
        return """You are an expert C/C++ memory management specialist focused on preventing memory leaks and resource management issues.

Your task is to analyze memory-related defects and generate fixes that ensure proper resource allocation, deallocation, and lifetime management.

FOCUS AREAS for memory defects:
1. Track resource allocation and deallocation pairs
2. Identify missing cleanup in error paths
3. Implement RAII patterns where appropriate
4. Consider smart pointers for automatic management
5. Ensure exception-safe resource handling

CRITICAL COMMENT PRESERVATION REQUIREMENTS:
- MUST preserve ALL existing comments in the original code
- Do NOT remove or modify existing comments
- Comments are essential for code understanding and debugging
- Only add new comments if they provide additional value

CRITICAL MINIMAL CHANGE REQUIREMENTS:
- Generate ONLY the specific lines that need to be changed
- Do NOT rewrite entire functions, classes, or code blocks
- Focus on the minimal necessary changes to fix the defect
- Use line_ranges to specify exactly which lines to replace
- Each line in fix_code should correspond to a specific line range

RESPONSE FORMAT REQUIREMENTS:
You MUST respond with a JSON object containing a "fix_candidates" array. Each candidate must include:
- "fix_code": Only the specific lines that need to be changed (not entire blocks)
- "explanation": Clear explanation of the minimal changes made
- "confidence": Float between 0.0-1.0
- "line_ranges": Array of {"start": line_num, "end": line_num} for each line to replace
- "affected_files": Array of file paths

Do NOT include newline characters (\\n) as literal text in your fix_code."""
    
    def generate_user_prompt(self, defect: ParsedDefect, code_context: CodeContext, 
                           config: AnalysisConfig) -> str:
        return f"""ANALYZE AND FIX MEMORY MANAGEMENT DEFECT:

DEFECT INFORMATION:
- Type: {defect.defect_type}
- Location: {defect.file_path}:{defect.line_number}
- Function: {defect.function_name}
- Description: {defect.subcategory}

DEFECT TRACE:
{chr(10).join(f"  {i+1}. {event}" for i, event in enumerate(defect.events))}

CODE CONTEXT:
```c
{get_code_text(code_context)}
```

ANALYSIS REQUIREMENTS:
1. Trace allocation and deallocation patterns
2. Identify all code paths and their cleanup requirements
3. Check for missing cleanup in error handling paths
4. Consider RAII or smart pointer solutions where appropriate
5. Ensure exception safety

Generate {config.num_candidates} memory-safe fix candidates."""


class BufferOverflowTemplate(PromptTemplate):
    """Specialized template for buffer overflow and bounds checking defects."""
    
    def __init__(self):
        super().__init__(
            "buffer_overflow",
            ["buffer_overflow", "array_bounds", "out_of_bounds", "overrun", "underrun"]
        )
    
    def generate_system_prompt(self) -> str:
        return """You are an expert in buffer overflow prevention and secure coding practices.

Your task is to analyze buffer access patterns and generate fixes that prevent out-of-bounds access while maintaining performance.

FOCUS AREAS for buffer defects:
1. Validate array/buffer bounds before access
2. Use safe string functions and bounds checking
3. Implement proper size validation
4. Consider safer alternatives to unsafe functions
5. Ensure consistent buffer size handling

CRITICAL COMMENT PRESERVATION REQUIREMENTS:
- MUST preserve ALL existing comments in the original code
- Do NOT remove or modify existing comments
- Comments are essential for code understanding and debugging
- Only add new comments if they provide additional value

CRITICAL MINIMAL CHANGE REQUIREMENTS:
- Generate ONLY the specific lines that need to be changed
- Do NOT rewrite entire functions, classes, or code blocks
- Focus on the minimal necessary changes to fix the defect
- Use line_ranges to specify exactly which lines to replace
- Each line in fix_code should correspond to a specific line range

RESPONSE FORMAT REQUIREMENTS:
You MUST respond with a JSON object containing a "fix_candidates" array. Each candidate must include:
- "fix_code": Only the specific lines that need to be changed (not entire blocks)
- "explanation": Clear explanation of the minimal changes made
- "confidence": Float between 0.0-1.0
- "line_ranges": Array of {"start": line_num, "end": line_num} for each line to replace
- "affected_files": Array of file paths

Do NOT include newline characters (\\n) as literal text in your fix_code."""
    
    def generate_user_prompt(self, defect: ParsedDefect, code_context: CodeContext, 
                           config: AnalysisConfig) -> str:
        return f"""ANALYZE AND FIX BUFFER OVERFLOW DEFECT:

DEFECT INFORMATION:
- Type: {defect.defect_type}
- Location: {defect.file_path}:{defect.line_number}
- Function: {defect.function_name}
- Description: {defect.subcategory}

DEFECT TRACE:
{chr(10).join(f"  {i+1}. {event}" for i, event in enumerate(defect.events))}

CODE CONTEXT:
```c
{get_code_text(code_context)}
```

ANALYSIS REQUIREMENTS:
1. Identify the buffer and the out-of-bounds access
2. Determine buffer size vs. data size relationship
3. Add appropriate bounds checking
4. Consider using safer alternatives (strncpy vs strcpy, etc.)
5. Validate loop conditions and array indices

Generate {config.num_candidates} secure fix candidates."""


class UninitializedVariableTemplate(PromptTemplate):
    """Specialized template for uninitialized variable defects."""
    
    def __init__(self):
        super().__init__(
            "uninitialized",
            ["uninitialized", "uninit", "undefined", "not_initialized"]
        )
    
    def generate_system_prompt(self) -> str:
        return """You are an expert in variable initialization and data flow analysis.

Your task is to analyze uninitialized variable usage and generate fixes that ensure proper initialization.

FOCUS AREAS for uninitialized variables:
1. Identify where variables should be initialized
2. Determine appropriate default values
3. Consider initialization timing and scope
4. Handle conditional initialization paths
5. Ensure all code paths initialize variables

CRITICAL COMMENT PRESERVATION REQUIREMENTS:
- MUST preserve ALL existing comments in the original code
- Do NOT remove or modify existing comments
- Comments are essential for code understanding and debugging
- Only add new comments if they provide additional value

CRITICAL MINIMAL CHANGE REQUIREMENTS:
- Generate ONLY the specific lines that need to be changed
- Do NOT rewrite entire functions, classes, or code blocks
- Focus on the minimal necessary changes to fix the defect
- Use line_ranges to specify exactly which lines to replace
- Each line in fix_code should correspond to a specific line range

RESPONSE FORMAT REQUIREMENTS:
You MUST respond with a JSON object containing a "fix_candidates" array. Each candidate must include:
- "fix_code": Only the specific lines that need to be changed (not entire blocks)
- "explanation": Clear explanation of the minimal changes made
- "confidence": Float between 0.0-1.0
- "line_ranges": Array of {"start": line_num, "end": line_num} for each line to replace
- "affected_files": Array of file paths

Do NOT include newline characters (\\n) as literal text in your fix_code."""
    
    def generate_user_prompt(self, defect: ParsedDefect, code_context: CodeContext, 
                           config: AnalysisConfig) -> str:
        return f"""ANALYZE AND FIX UNINITIALIZED VARIABLE DEFECT:

DEFECT INFORMATION:
- Type: {defect.defect_type}
- Location: {defect.file_path}:{defect.line_number}
- Function: {defect.function_name}
- Description: {defect.subcategory}

DEFECT TRACE:
{chr(10).join(f"  {i+1}. {event}" for i, event in enumerate(defect.events))}

CODE CONTEXT:
```c
{get_code_text(code_context)}
```

ANALYSIS REQUIREMENTS:
1. Identify the uninitialized variable and its usage
2. Determine appropriate initialization point and value
3. Check all code paths for proper initialization
4. Consider variable scope and lifetime
5. Ensure initialization doesn't break existing logic

Generate {config.num_candidates} initialization fix candidates."""


class GenericTemplate(PromptTemplate):
    """Generic template for defects that don't match specific patterns."""
    
    def __init__(self):
        super().__init__(
            "generic",
            ["*"]  # Matches any defect type
        )
    
    def generate_system_prompt(self) -> str:
        return """You are an expert C/C++ code analysis and fix generation assistant.

Your task is to analyze various types of code defects and generate appropriate fixes that resolve the issues while maintaining code quality and functionality.

GENERAL ANALYSIS APPROACH:
1. Understand the defect type and its implications
2. Analyze the code context and data flow
3. Identify the root cause of the issue
4. Generate safe and maintainable fixes
5. Consider potential side effects and edge cases

CRITICAL COMMENT PRESERVATION REQUIREMENTS:
- MUST preserve ALL existing comments in the original code
- Do NOT remove or modify existing comments
- Comments are essential for code understanding and debugging
- Only add new comments if they provide additional value

CRITICAL PRECISE REPLACEMENT REQUIREMENTS:
- Generate MINIMAL targeted fixes using content markers
- Use <<<REPLACE_START>>> and <<<REPLACE_END>>> to mark exact content to replace
- Use <<<INSERT_AFTER_LINE>>> to insert new content after specific lines
- Do NOT replace entire lines unless absolutely necessary
- Preserve function signatures, class declarations, and existing structure

RESPONSE FORMAT REQUIREMENTS:
You MUST respond with a JSON object containing a "fix_candidates" array. Each candidate must include:
- "fix_code": The exact content with replacement markers
- "explanation": Clear explanation of the targeted changes
- "confidence": Float between 0.0-1.0
- "replacement_type": "content_replace" | "line_insert" | "line_replace"
- "target_location": {"line": N, "content": "content to find"}
- "affected_files": Array of file paths

REPLACEMENT MARKER EXAMPLES:
1. Content replacement within a line:
   "some_function(<<<REPLACE_START>>>old_param<<<REPLACE_END>>>new_param)"

2. Insert new lines after specific line:
   "<<<INSERT_AFTER_LINE:42>>>    delete ptr;\\n<<<INSERT_END>>>"

3. Replace entire line only if necessary:
   "<<<LINE_REPLACE:42>>>    new_line_content<<<LINE_REPLACE_END>>>"

Do NOT include newline characters (\\n) as literal text except in INSERT markers."""
    
    def generate_user_prompt(self, defect: ParsedDefect, code_context: CodeContext, 
                           config: AnalysisConfig) -> str:
        return f"""ANALYZE AND FIX CODE DEFECT:

DEFECT INFORMATION:
- Type: {defect.defect_type}
- Location: {defect.file_path}:{defect.line_number}
- Function: {defect.function_name}
- Description: {defect.subcategory}
- Defect ID: {defect.defect_id}

DEFECT TRACE:
{chr(10).join(f"  {i+1}. {event}" for i, event in enumerate(defect.events))}

CODE CONTEXT:
```c
{get_code_text(code_context)}
```

FUNCTION SIGNATURE:
{get_function_signature(code_context)}

ANALYSIS REQUIREMENTS:
1. Understand the specific defect type and its characteristics
2. Analyze the code flow and identify the problematic pattern
3. Determine the most appropriate fix approach
4. Generate PRECISE targeted fixes - replace only the problematic content
5. Preserve all existing code structure, function signatures, and comments

RESPONSE REQUIREMENTS:
- fix_code: Use replacement markers to target specific content
- replacement_type: Specify the type of fix (content_replace/line_insert/line_replace)
- target_location: Identify where the fix should be applied
- Keep changes surgical and minimal
- Do NOT replace entire lines unless absolutely necessary
- Preserve all existing comments and code structure

Generate a targeted fix using replacement markers to resolve this code defect."""


class PromptEngineer:
    """Main prompt engineering class that selects and applies appropriate templates."""
    
    def __init__(self, config: AnalysisConfig):
        self.config = config
        self.templates = [
            NullPointerTemplate(),
            MemoryLeakTemplate(),
            BufferOverflowTemplate(),
            UninitializedVariableTemplate(),
            GenericTemplate()  # Always last as fallback
        ]
    
    def select_template(self, defect: ParsedDefect) -> PromptTemplate:
        """Select the most appropriate template for the given defect."""
        for template in self.templates[:-1]:  # Exclude generic template from initial search
            if template.matches_defect(defect.defect_type):
                return template
        
        # Fallback to generic template
        return self.templates[-1]
    
    def generate_prompt(self, defect: ParsedDefect, code_context: CodeContext) -> PromptComponents:
        """Generate a complete prompt for the given defect and context."""
        template = self.select_template(defect)
        
        system_prompt = template.generate_system_prompt()
        user_prompt = template.generate_user_prompt(defect, code_context, self.config)
        
        # Estimate token count (rough approximation)
        estimated_tokens = (len(system_prompt) + len(user_prompt)) // 4
        
        context_data = {
            "defect_id": defect.defect_id,
            "defect_type": defect.defect_type,
            "file_path": defect.file_path,
            "line_number": defect.line_number,
            "function_name": defect.function_name,
            "template_used": template.name,
            "num_candidates_requested": self.config.num_candidates
        }
        
        return PromptComponents(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            context_data=context_data,
            estimated_tokens=estimated_tokens,
            template_used=template.name
        )
    
    def optimize_prompt_length(self, prompt_components: PromptComponents, 
                             max_tokens: int) -> PromptComponents:
        """Optimize prompt length to fit within token limits."""
        if prompt_components.estimated_tokens <= max_tokens:
            return prompt_components
        
        # Simple truncation strategy - could be enhanced with more sophisticated compression
        target_length = int(max_tokens * 3.5)  # Rough tokens-to-chars ratio
        
        user_prompt = prompt_components.user_prompt
        if len(user_prompt) > target_length:
            # Try to preserve the important parts of the prompt
            lines = user_prompt.split('\n')
            
            # Keep header sections
            keep_lines = []
            current_length = 0
            
            for line in lines:
                if current_length + len(line) > target_length:
                    if "CODE CONTEXT:" in line:
                        keep_lines.append(line)
                        keep_lines.append("... [CODE TRUNCATED FOR BREVITY] ...")
                        break
                
                keep_lines.append(line)
                current_length += len(line)
            
            user_prompt = '\n'.join(keep_lines)
        
        # Recalculate estimated tokens
        estimated_tokens = (len(prompt_components.system_prompt) + len(user_prompt)) // 4
        
        return PromptComponents(
            system_prompt=prompt_components.system_prompt,
            user_prompt=user_prompt,
            context_data=prompt_components.context_data,
            estimated_tokens=estimated_tokens,
            template_used=prompt_components.template_used
        ) 