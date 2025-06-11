"""
Advanced prompt engineering framework for LLM Fix Generator.

This module provides defect-specific prompt templates and intelligent prompt
generation for NVIDIA NIM models, optimized for different Coverity defect types.
"""

import json
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from abc import ABC, abstractmethod

from ..issue_parser.data_structures import ParsedDefect
from ..code_retriever.data_structures import CodeContext
from .config import AnalysisConfig


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
2. Find missing null checks and validation
3. Propose defensive programming approaches
4. Consider error handling and recovery strategies
5. Ensure pointer validity before access

RESPONSE FORMAT:
Return a JSON object with the following structure:
{
    "defect_analysis": {
        "category": "null_pointer_dereference",
        "severity": "high|medium|low",
        "complexity": "simple|moderate|complex|high_risk",
        "confidence": 0.0-1.0,
        "root_cause": "detailed explanation"
    },
    "fix_candidates": [
        {
            "fix_code": "actual code fix",
            "explanation": "detailed explanation of the fix",
            "confidence": 0.0-1.0,
            "complexity": "simple|moderate|complex|high_risk",
            "risk_assessment": "risk analysis",
            "affected_files": ["file1.c"],
            "line_ranges": [{"start": 10, "end": 15}],
            "fix_strategy": "null_check|validation|redesign",
            "potential_side_effects": ["list of potential issues"]
        }
    ],
    "reasoning": "step-by-step analysis"
}

PRIORITIZE safety and robustness over minimal code changes."""
    
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

CODE CONTEXT:
```c
{code_context.context_code}
```

FUNCTION SIGNATURE:
{code_context.function_signature or "Not available"}

ANALYSIS REQUIREMENTS:
1. Identify the exact line where null dereference occurs
2. Trace back to find all possible null value sources
3. Determine appropriate null checking strategy
4. Generate 2-3 fix approaches focusing on safety
5. Consider error handling and graceful degradation
6. Ensure fixes don't break existing functionality

Generate {config.num_candidates} fix candidates prioritizing robustness and maintainability."""


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
3. Ensure exception safety and RAII principles
4. Handle ownership transfer correctly
5. Prevent double-free and use-after-free issues

RESPONSE FORMAT: JSON with defect_analysis, fix_candidates, and reasoning sections.

PRIORITIZE memory safety and follow RAII principles where applicable."""
    
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
{code_context.context_code}
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
4. Consider buffer size vs. data size mismatches
5. Ensure loop bounds are correct

RESPONSE FORMAT: JSON with defect_analysis, fix_candidates, and reasoning sections.

PRIORITIZE security and bounds safety."""
    
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
{code_context.context_code}
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
5. Ensure all code paths initialize variables before use

RESPONSE FORMAT: JSON with defect_analysis, fix_candidates, and reasoning sections.

PRIORITIZE correctness and initialization safety."""
    
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
{code_context.context_code}
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

RESPONSE FORMAT:
Return a JSON object with the following structure:
{
    "defect_analysis": {
        "category": "defect category",
        "severity": "critical|high|medium|low",
        "complexity": "simple|moderate|complex|high_risk",
        "confidence": 0.0-1.0,
        "root_cause": "detailed explanation"
    },
    "fix_candidates": [
        {
            "fix_code": "actual code fix",
            "explanation": "detailed explanation",
            "confidence": 0.0-1.0,
            "complexity": "simple|moderate|complex|high_risk",
            "risk_assessment": "risk analysis",
            "affected_files": ["file.c"],
            "line_ranges": [{"start": N, "end": M}],
            "fix_strategy": "strategy description",
            "potential_side_effects": ["list of issues"]
        }
    ],
    "reasoning": "step-by-step analysis"
}

PRIORITIZE code safety, maintainability, and minimal impact."""
    
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
{code_context.context_code}
```

FUNCTION SIGNATURE:
{code_context.function_signature or "Not available"}

ANALYSIS REQUIREMENTS:
1. Understand the specific defect type and its characteristics
2. Analyze the code flow and identify the problematic pattern
3. Determine the most appropriate fix strategy
4. Generate {config.num_candidates} fix candidates with varying approaches
5. Consider maintainability and minimal code changes
6. Ensure fixes address the root cause, not just symptoms

Provide comprehensive analysis and practical fix solutions."""


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