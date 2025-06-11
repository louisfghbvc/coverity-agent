"""
Unit tests for LLM Fix Generator prompt engineering.
"""

import pytest

from fix_generator.prompt_engineering import (
    PromptEngineer, PromptComponents,
    NullPointerTemplate, MemoryLeakTemplate, BufferOverflowTemplate,
    UninitializedVariableTemplate, GenericTemplate
)
from fix_generator.config import AnalysisConfig


class TestPromptTemplates:
    """Test individual prompt templates."""
    
    def test_null_pointer_template(self, sample_parsed_defect, sample_code_context):
        """Test NullPointerTemplate functionality."""
        template = NullPointerTemplate()
        
        assert template.name == "null_pointer"
        assert "null_pointer" in template.defect_types
        assert "dereference" in template.defect_types
        
        # Test defect matching
        assert template.matches_defect("NULL_POINTER_DEREFERENCE") is True
        assert template.matches_defect("null_dereference") is True
        assert template.matches_defect("MEMORY_LEAK") is False
        
        # Test system prompt generation
        system_prompt = template.generate_system_prompt()
        assert "null pointer" in system_prompt.lower()
        assert "defensive programming" in system_prompt.lower()
        assert "JSON" in system_prompt
        
        # Test user prompt generation
        config = AnalysisConfig(num_candidates=3)
        user_prompt = template.generate_user_prompt(sample_parsed_defect, sample_code_context, config)
        
        assert "NULL_POINTER_DEREFERENCE" in user_prompt
        assert "/path/to/test.c:42" in user_prompt
        assert "test_function" in user_prompt
        assert "3 fix candidates" in user_prompt
        # Check that source code is included in the prompt
        assert "test_function" in user_prompt
        assert "strlen(ptr)" in user_prompt
    
    def test_generic_template(self, sample_parsed_defect, sample_code_context):
        """Test GenericTemplate functionality."""
        template = GenericTemplate()
        
        assert template.name == "generic"
        assert template.matches_defect("ANY_DEFECT_TYPE") is True  # Should match anything
        
        system_prompt = template.generate_system_prompt()
        assert "code analysis" in system_prompt.lower()
        assert "JSON" in system_prompt
        
        config = AnalysisConfig(num_candidates=2)
        user_prompt = template.generate_user_prompt(sample_parsed_defect, sample_code_context, config)
        
        assert "ANALYZE AND FIX CODE DEFECT" in user_prompt
        assert sample_parsed_defect.defect_type in user_prompt
        assert "2 fix candidates" in user_prompt


class TestPromptEngineer:
    """Test PromptEngineer main class."""
    
    def test_prompt_engineer_creation(self):
        """Test creating PromptEngineer."""
        config = AnalysisConfig()
        engineer = PromptEngineer(config)
        
        assert engineer.config == config
        assert len(engineer.templates) == 5  # 4 specific + 1 generic
        assert isinstance(engineer.templates[-1], GenericTemplate)  # Generic is last
    
    def test_template_selection(self, sample_parsed_defect):
        """Test template selection based on defect type."""
        config = AnalysisConfig()
        engineer = PromptEngineer(config)
        
        # Test null pointer defect
        sample_parsed_defect.defect_type = "NULL_POINTER_DEREFERENCE"
        template = engineer.select_template(sample_parsed_defect)
        assert isinstance(template, NullPointerTemplate)
        
        # Test unknown defect type
        sample_parsed_defect.defect_type = "UNKNOWN_DEFECT_TYPE"
        template = engineer.select_template(sample_parsed_defect)
        assert isinstance(template, GenericTemplate)
    
    def test_generate_prompt(self, sample_parsed_defect, sample_code_context):
        """Test complete prompt generation."""
        config = AnalysisConfig(num_candidates=3)
        engineer = PromptEngineer(config)
        
        prompt_components = engineer.generate_prompt(sample_parsed_defect, sample_code_context)
        
        assert isinstance(prompt_components, PromptComponents)
        assert prompt_components.system_prompt
        assert prompt_components.user_prompt
        assert prompt_components.estimated_tokens > 0
        assert prompt_components.template_used == "null_pointer"  # For NULL_POINTER_DEREFERENCE
        
        # Check context data
        context_data = prompt_components.context_data
        assert context_data["defect_id"] == sample_parsed_defect.defect_id
        assert context_data["defect_type"] == sample_parsed_defect.defect_type
        assert context_data["file_path"] == sample_parsed_defect.file_path
        assert context_data["line_number"] == sample_parsed_defect.line_number
        assert context_data["num_candidates_requested"] == 3 