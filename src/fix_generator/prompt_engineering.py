"""
Unified prompt engineering framework for LLM Fix Generator.

This module provides a simplified, unified approach to generating prompts
for different types of code defects with consistent formatting.
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


def get_unified_system_prompt(defect_type: str, specific_guidance: str = "") -> str:
    """Generate unified system prompt for all defect types."""
    return f"""You are an expert C/C++ code analysis assistant. Your task is to analyze {defect_type} defects and provide precise fixes.

ANALYSIS APPROACH:
1. Identify the specific issue in the code
2. Generate targeted fixes that address the root cause
3. Provide minimal changes - only modify what's necessary
4. Include proper defect analysis with your assessment.

{specific_guidance}

RESPONSE FORMAT REQUIREMENTS:
You MUST respond with ONLY a valid JSON object - no markdown, no explanations, no code blocks.
Your response must start with {{ and end with }}.

Required JSON structure:
{{
  "defect_analysis": {{
    "category": "defect category",
    "severity": "low|medium|high|critical", 
    "complexity": "simple|moderate|complex|high_risk",
    "confidence": 0.8
  }},
  "fix_candidates": [
    {{
      "fix_code": ["line 1 of fix", "line 2 of fix"],
      "explanation": "clear explanation of the fix",
      "confidence": 0.9,
      "line_ranges": [{{"start": line_num, "end": line_num}}],
      "affected_files": ["file_path"]
    }}
  ]
}}

CRITICAL FORMATTING RULES:
- Return ONLY the JSON object, nothing else
- Do NOT include markdown headers, code blocks, or explanations outside JSON
- Do NOT add comments (//) inside JSON
- Preserve ALL existing comments in the original code
- Focus on minimal necessary changes to fix the defect
- Use line_ranges to specify exactly which lines to replace"""


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
    def get_defect_type_name(self) -> str:
        """Get the display name for this defect type."""
        pass
    
    @abstractmethod
    def get_specific_guidance(self) -> str:
        """Get specific guidance for this defect type."""
        pass
    
    def generate_system_prompt(self) -> str:
        """Generate the system prompt for this defect type."""
        return get_unified_system_prompt(
            self.get_defect_type_name(),
            self.get_specific_guidance()
        )
    
    def generate_user_prompt(self, defect: ParsedDefect, code_context: CodeContext, 
                           config: AnalysisConfig) -> str:
        """Generate the user prompt with defect and context information."""
        return f"""ANALYZE AND FIX {self.get_defect_type_name().upper()}:

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

FUNCTION SIGNATURE:
{get_function_signature(code_context)}

Generate {config.num_candidates} targeted fix candidates."""
    
    def matches_defect(self, defect_type: str) -> bool:
        """Check if this template matches the given defect type."""
        if "*" in self.defect_types:
            return True
        
        defect_lower = defect_type.lower()
        return any(dt.lower() in defect_lower for dt in self.defect_types)


class NullPointerTemplate(PromptTemplate):
    """Template for null pointer and dereference defects."""
    
    def __init__(self):
        super().__init__(
            "null_pointer",
            ["null_pointer", "null_dereference", "dereference", "nullptr", "segfault", "forward_null"]
        )
    
    def get_defect_type_name(self) -> str:
        return "NULL POINTER DEREFERENCE"
    
    def get_specific_guidance(self) -> str:
        return """SPECIFIC APPROACH:
- Add null checks before pointer usage
- Use appropriate return values or error handling
- Consider the function's return type and context

EXAMPLE FIX PATTERN:
If fixing `ptr->method()` at line 42, replace with:
"fix_code": [
  "if (ptr == nullptr) { return false; }",
  "ptr->method();"
],
"line_ranges": [{"start": 42, "end": 42}]"""


class MemoryLeakTemplate(PromptTemplate):
    """Template for memory management and leak defects."""
    
    def __init__(self):
        super().__init__(
            "memory_leak",
            ["memory_leak", "resource_leak", "malloc", "free", "new", "delete", "alloc"]
        )
    
    def get_defect_type_name(self) -> str:
        return "MEMORY/RESOURCE LEAK"
    
    def get_specific_guidance(self) -> str:
        return """SPECIFIC APPROACH:
- Add proper deallocation (delete/free) calls
- Usually in destructors or cleanup functions
- Match allocation type (new/delete, malloc/free)

EXAMPLE FIX PATTERN:
To add cleanup in destructor before closing brace at line 50:
"fix_code": [
  "delete m_data;",
  "}"
],
"line_ranges": [{"start": 50, "end": 50}]"""


class BufferOverflowTemplate(PromptTemplate):
    """Template for buffer overflow and bounds checking defects."""
    
    def __init__(self):
        super().__init__(
            "buffer_overflow",
            ["buffer_overflow", "array_bounds", "out_of_bounds", "overrun", "underrun"]
        )
    
    def get_defect_type_name(self) -> str:
        return "BUFFER OVERFLOW"
    
    def get_specific_guidance(self) -> str:
        return """SPECIFIC APPROACH:
- Add bounds checking before array/buffer access
- Use safe string functions (strncpy vs strcpy)
- Validate array indices and buffer sizes
- Consider safer alternatives

EXAMPLE FIX PATTERN:
To add bounds check before array access at line 30:
"fix_code": [
  "if (index >= 0 && index < array_size) {",
  "    array[index] = value;",
  "}"
],
"line_ranges": [{"start": 30, "end": 30}]"""


class UninitializedVariableTemplate(PromptTemplate):
    """Template for uninitialized variable defects."""
    
    def __init__(self):
        super().__init__(
            "uninitialized",
            ["uninitialized", "uninit", "undefined", "not_initialized"]
        )
    
    def get_defect_type_name(self) -> str:
        return "UNINITIALIZED VARIABLE"
    
    def get_specific_guidance(self) -> str:
        return """SPECIFIC APPROACH:
- Initialize variables at declaration or before first use
- Choose appropriate default values
- Ensure all code paths initialize variables
- Consider variable scope and lifetime

EXAMPLE FIX PATTERN:
To initialize variable at declaration on line 15:
"fix_code": [
  "int result = 0;"
],
"line_ranges": [{"start": 15, "end": 15}]"""


class GenericTemplate(PromptTemplate):
    """Generic template for defects that don't match specific patterns."""
    
    def __init__(self):
        super().__init__(
            "generic",
            ["*"]  # Matches any defect type
        )
    
    def get_defect_type_name(self) -> str:
        return "CODE DEFECT"
    
    def get_specific_guidance(self) -> str:
        return """GENERAL APPROACH:
- Understand the defect type and its implications
- Analyze the code context and data flow
- Identify the root cause of the issue
- Generate safe and maintainable fixes
- Consider potential side effects and edge cases

EXAMPLE FIX PATTERN:
Provide targeted fixes based on the specific defect type and context."""


class PromptEngineer:
    """Unified prompt engineering class that selects and applies appropriate templates."""
    
    def __init__(self, config: AnalysisConfig):
        self.config = config
        self.templates = [
            NullPointerTemplate(),
            MemoryLeakTemplate(),
            BufferOverflowTemplate(),
            UninitializedVariableTemplate(),
            GenericTemplate(),  # Must be last as it matches everything
        ]
    
    def select_template(self, defect: ParsedDefect) -> PromptTemplate:
        """Select the most appropriate template for the given defect."""
        for template in self.templates:
            if template.matches_defect(defect.defect_type):
                return template
        # Fallback to generic template
        return self.templates[-1]
    
    def generate_prompt(self, defect: ParsedDefect, code_context: CodeContext) -> PromptComponents:
        """Generate a complete prompt for the given defect and context."""
        template = self.select_template(defect)
        
        system_prompt = template.generate_system_prompt()
        user_prompt = template.generate_user_prompt(defect, code_context, self.config)
        
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
        """Optimize prompt length if needed (simplified version)."""
        if prompt_components.estimated_tokens <= max_tokens:
            return prompt_components
        
        # Simple truncation strategy - could be enhanced
        return prompt_components 