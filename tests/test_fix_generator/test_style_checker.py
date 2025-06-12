"""
Unit tests for style consistency checker.
"""

import pytest

from fix_generator.style_checker import (
    StyleConsistencyChecker, StyleAnalyzer, StyleApplier, StyleProfile
)
from fix_generator.data_structures import FixCandidate, FixComplexity


class TestStyleProfile:
    """Test StyleProfile data structure."""
    
    def test_style_profile_creation(self):
        """Test creating StyleProfile with defaults."""
        profile = StyleProfile()
        
        assert profile.indent_style == "spaces"
        assert profile.indent_size == 4
        assert profile.brace_style == "allman"
        assert profile.variable_naming == "snake_case"
        assert profile.confidence == 0.0
    
    def test_style_profile_to_dict(self):
        """Test StyleProfile serialization."""
        profile = StyleProfile(
            indent_style="tabs",
            indent_size=8,
            brace_style="k&r",
            confidence=0.9
        )
        
        result = profile.to_dict()
        
        assert result["indent_style"] == "tabs"
        assert result["indent_size"] == 8
        assert result["brace_style"] == "k&r"
        assert result["confidence"] == 0.9


class TestStyleAnalyzer:
    """Test StyleAnalyzer class."""
    
    def test_analyze_indentation_spaces(self, sample_code_context):
        """Test analyzing space-based indentation."""
        analyzer = StyleAnalyzer()
        
        # Modify the source lines directly
        sample_code_context.primary_context.source_lines = [
            "int function() {",
            "    int x = 0;",
            "    if (x == 0) {",
            "        return 1;",
            "    }",
            "    return 0;",
            "}"
        ]
        
        lines = sample_code_context.primary_context.source_lines
        indent_info = analyzer._analyze_indentation(lines)
        
        assert indent_info["style"] == "spaces"
        assert indent_info["size"] in [2, 4]  # Common space sizes
    
    def test_analyze_indentation_tabs(self, sample_code_context):
        """Test analyzing tab-based indentation."""
        analyzer = StyleAnalyzer()
        
        # Modify the source lines with tab indentation
        sample_code_context.primary_context.source_lines = [
            "int function() {",
            "\tint x = 0;",
            "\tif (x == 0) {",
            "\t\treturn 1;",
            "\t}",
            "\treturn 0;",
            "}"
        ]
        
        lines = sample_code_context.primary_context.source_lines
        indent_info = analyzer._analyze_indentation(lines)
        
        assert indent_info["style"] == "tabs"
    
    def test_analyze_brace_style_allman(self, sample_code_context):
        """Test analyzing Allman brace style."""
        analyzer = StyleAnalyzer()
        
        sample_code_context.primary_context.source_lines = [
            "int function()",
            "{",
            "    if (condition)",
            "    {",
            "        return 1;",
            "    }",
            "    return 0;",
            "}"
        ]
        
        lines = sample_code_context.primary_context.source_lines
        brace_style = analyzer._analyze_brace_style(lines)
        
        assert brace_style == "allman"
    
    def test_analyze_brace_style_kr(self, sample_code_context):
        """Test analyzing K&R brace style."""
        analyzer = StyleAnalyzer()
        
        sample_code_context.primary_context.source_lines = [
            "int function() {",
            "    if (condition) {",
            "        return 1;",
            "    }",
            "    return 0;",
            "}"
        ]
        
        lines = sample_code_context.primary_context.source_lines
        brace_style = analyzer._analyze_brace_style(lines)
        
        assert brace_style == "k&r"
    
    def test_analyze_naming_conventions(self, sample_code_context):
        """Test analyzing naming conventions."""
        analyzer = StyleAnalyzer()
        
        # Code with snake_case variables
        code = """int my_function(char* input_string) {
    int local_variable = 0;
    char* another_var = NULL;
    return local_variable;
}"""
        
        naming_info = analyzer._analyze_naming_conventions(code)
        
        assert naming_info["variable"] == "snake_case"
        assert naming_info["function"] == "snake_case"
    
    def test_analyze_spacing(self, sample_code_context):
        """Test analyzing spacing patterns."""
        analyzer = StyleAnalyzer()
        
        # Code with consistent spacing
        code = """int function() {
    if (condition) {
        int x = a + b;
        func(arg1, arg2, arg3);
    }
    for (int i = 0; i < n; i++) {
        process(i);
    }
}"""
        
        spacing_info = analyzer._analyze_spacing(code)
        
        assert spacing_info["after_keywords"] is True
        assert spacing_info["around_operators"] is True
        assert spacing_info["after_commas"] is True
    
    def test_analyze_line_length(self, sample_code_context):
        """Test analyzing line length patterns."""
        analyzer = StyleAnalyzer()
        
        # Create code with specific line lengths
        lines = [
            "int function() {",  # Short line
            "    int very_long_variable_name_that_exceeds_normal_limits = some_very_long_function_call(arg1, arg2, arg3);",  # Long line
            "    return 0;",  # Short line
            "}"
        ]
        
        max_length = analyzer._analyze_line_length(lines)
        
        assert max_length >= 80  # Should detect longer lines
    
    def test_analyze_comment_style(self, sample_code_context):
        """Test analyzing comment style preferences."""
        analyzer = StyleAnalyzer()
        
        lines = [
            "int function() {",
            "    // Line comment",
            "    int x = 0;  // Another line comment", 
            "    /* Block comment */",
            "    return x;",
            "}"
        ]
        
        comment_style = analyzer._analyze_comment_style(lines)
        
        assert comment_style == "line"  # More line comments than block
    
    def test_analyze_style_complete(self, sample_code_context):
        """Test complete style analysis."""
        analyzer = StyleAnalyzer()
        
        profile = analyzer.analyze_style(sample_code_context)
        
        assert isinstance(profile, StyleProfile)
        assert 0.0 <= profile.confidence <= 1.0
        assert profile.indent_style in ["spaces", "tabs"]
        assert profile.brace_style in ["allman", "k&r"]
        assert profile.variable_naming in ["snake_case", "camelCase", "PascalCase"]
    
    def test_analyze_style_empty_context(self):
        """Test style analysis with empty context."""
        analyzer = StyleAnalyzer()
        
        from code_retriever.data_structures import CodeContext, SourceLocation, ContextWindow, FileMetadata
        from datetime import datetime
        
        # Create proper CodeContext structure with empty source lines
        primary_location = SourceLocation(
            file_path="",
            line_number=1,
            column_number=0,
            function_name=""
        )
        
        primary_context = ContextWindow(
            start_line=1,
            end_line=1,
            source_lines=[],  # Empty source lines
            highlighted_line=None
        )
        
        file_metadata = FileMetadata(
            file_path="",
            file_size=0,
            encoding="utf-8",
            language="c"
        )
        
        empty_context = CodeContext(
            defect_id="test_empty",
            defect_type="TEST",
            primary_location=primary_location,
            primary_context=primary_context,
            file_metadata=file_metadata,
            language="c"
        )
        
        profile = analyzer.analyze_style(empty_context)
        
        assert profile.confidence == 0.0


class TestStyleApplier:
    """Test StyleApplier class."""
    
    def test_apply_indentation_spaces_to_tabs(self):
        """Test converting spaces to tabs."""
        applier = StyleApplier()
        
        profile = StyleProfile(indent_style="tabs", indent_size=8)
        
        code_with_spaces = """int function() {
    int x = 0;
    if (x == 0) {
        return 1;
    }
    return 0;
}"""
        
        result = applier.apply_style(code_with_spaces, profile)
        
        # Should contain tabs instead of spaces for indentation
        lines = result.split('\n')
        indented_lines = [line for line in lines if line.startswith('\t') or line.startswith(' ')]
        
        # At least some lines should start with tabs now
        assert any(line.startswith('\t') for line in indented_lines)
    
    def test_apply_brace_style_allman_to_kr(self):
        """Test converting Allman brace style to K&R."""
        applier = StyleApplier()
        
        profile = StyleProfile(brace_style="k&r")
        
        allman_code = """int function()
{
    if (condition)
    {
        return 1;
    }
    return 0;
}"""
        
        result = applier.apply_style(allman_code, profile)
        
        # Should have opening braces on same line
        assert "if (condition) {" in result or "condition){" in result
    
    def test_apply_spacing_keywords(self):
        """Test applying spacing after keywords."""
        applier = StyleApplier()
        
        profile = StyleProfile(space_after_keywords=True)
        
        code_no_spaces = """int function() {
    if(condition) {
        for(int i=0;i<n;i++) {
            process(i);
        }
    }
}"""
        
        result = applier.apply_style(code_no_spaces, profile)
        
        assert "if (" in result
        assert "for (" in result
    
    def test_apply_spacing_operators(self):
        """Test applying spacing around operators."""
        applier = StyleApplier()
        
        profile = StyleProfile(space_around_operators=True)
        
        code_no_spaces = """int function() {
    int x=a+b*c;
    int y=x-5;
    return x;
}"""
        
        result = applier.apply_style(code_no_spaces, profile)
        
        # Should have spaces around operators
        assert " = " in result
        assert " + " in result or " - " in result
    
    def test_apply_spacing_commas(self):
        """Test applying spacing after commas."""
        applier = StyleApplier()
        
        profile = StyleProfile(space_after_commas=True)
        
        code_no_spaces = """int function() {
    func(arg1,arg2,arg3);
    another_func(a,b,c,d);
}"""
        
        result = applier.apply_style(code_no_spaces, profile)
        
        assert ", " in result
    
    def test_apply_line_length_breaking(self):
        """Test basic line length breaking."""
        applier = StyleApplier()
        
        profile = StyleProfile(max_line_length=50)
        
        long_line_code = """int function() {
    very_long_function_call(arg1, arg2, arg3, arg4, arg5, arg6);
    return 0;
}"""
        
        result = applier.apply_style(long_line_code, profile)
        
        # Should attempt to break long lines
        lines = result.split('\n')
        long_lines = [line for line in lines if len(line) > profile.max_line_length]
        
        # Should have fewer long lines than before
        original_long_lines = [line for line in long_line_code.split('\n') if len(line) > profile.max_line_length]
        assert len(long_lines) <= len(original_long_lines)


class TestStyleConsistencyChecker:
    """Test StyleConsistencyChecker main class."""
    
    def test_style_consistency_checker_creation(self):
        """Test creating StyleConsistencyChecker."""
        checker = StyleConsistencyChecker()
        
        assert isinstance(checker.analyzer, StyleAnalyzer)
        assert isinstance(checker.applier, StyleApplier)
    
    def test_check_and_fix_style(self, sample_fix_candidate, sample_code_context):
        """Test complete style checking and fixing workflow."""
        checker = StyleConsistencyChecker()
        
        styled_code, consistency_score = checker.check_and_fix_style(
            sample_fix_candidate, sample_code_context
        )
        
        assert isinstance(styled_code, str)
        assert 0.0 <= consistency_score <= 1.0
        
        # Styled code should not be empty
        assert len(styled_code.strip()) > 0
    
    def test_check_and_fix_style_empty_code(self, sample_code_context):
        """Test style checking with empty fix code."""
        checker = StyleConsistencyChecker()
        
        # Use minimal fix code since empty code is not allowed by validation
        empty_fix = FixCandidate(
            fix_code="// Empty fix placeholder",
            explanation="Empty fix",
            confidence_score=0.5,
            complexity=FixComplexity.SIMPLE,
            risk_assessment="Test",
            affected_files=["test.c"],
            line_ranges=[]
        )
        
        styled_code, consistency_score = checker.check_and_fix_style(
            empty_fix, sample_code_context
        )
        
        assert styled_code == "// Empty fix placeholder"
        assert consistency_score >= 0.0  # Should get some score
    
    def test_consistency_score_calculation(self, sample_fix_candidate, sample_code_context):
        """Test consistency score calculation."""
        checker = StyleConsistencyChecker()
        
        # Test with code that should already match style
        well_styled_fix = FixCandidate(
            fix_code="""int test_function(char* input) {
    if (input != NULL) {
        return strlen(input);
    }
    return 0;
}""",
            explanation="Well-styled code",
            confidence_score=0.8,
            complexity=FixComplexity.SIMPLE,
            risk_assessment="Low",
            affected_files=["test.c"],
            line_ranges=[]
        )
        
        styled_code, consistency_score = checker.check_and_fix_style(
            well_styled_fix, sample_code_context
        )
        
        # Should get a reasonable consistency score
        assert 0.0 <= consistency_score <= 1.0
    
    def test_style_transformation_detection(self, sample_code_context):
        """Test detection of style transformations."""
        checker = StyleConsistencyChecker()
        
        # Create fix with inconsistent style
        poorly_styled_fix = FixCandidate(
            fix_code="""int test_function(char* input){
if(input!=NULL){
return strlen(input);
}
return 0;
}""",
            explanation="Poorly styled code",
            confidence_score=0.8,
            complexity=FixComplexity.SIMPLE,
            risk_assessment="Low",
            affected_files=["test.c"],
            line_ranges=[]
        )
        
        styled_code, consistency_score = checker.check_and_fix_style(
            poorly_styled_fix, sample_code_context
        )
        
        # Should improve the code style
        assert "if (" in styled_code  # Should add space after keyword
        assert " != " in styled_code  # Should add spaces around operators
        assert consistency_score > 0.0


class TestStyleCheckerIntegration:
    """Integration tests for style checker components."""
    
    def test_complete_style_workflow(self, sample_code_context):
        """Test complete style analysis and application workflow."""
        # Create code context with specific style
        sample_code_context.primary_context.source_lines = [
            "int well_styled_function(char* input_string) {",
            "    if (input_string != NULL) {",
            "        int string_length = strlen(input_string);",
            "        return string_length;",
            "    }",
            "    return 0;",
            "}"
        ]
        
        # Create fix with different style
        inconsistent_fix = FixCandidate(
            fix_code="""int poorly_styled_function(char* inputString){
if(inputString!=NULL){
int stringLength=strlen(inputString);
return stringLength;
}
return 0;
}""",
            explanation="Fix with inconsistent style",
            confidence_score=0.8,
            complexity=FixComplexity.SIMPLE,
            risk_assessment="Low",
            affected_files=["test.c"],
            line_ranges=[]
        )
        
        checker = StyleConsistencyChecker()
        styled_code, consistency_score = checker.check_and_fix_style(
            inconsistent_fix, sample_code_context
        )
        
        # Should improve style consistency
        assert " != " in styled_code
        assert "if (" in styled_code
        assert consistency_score > 0.3  # Should get reasonable score
    
    def test_style_preservation(self, sample_code_context):
        """Test that good style is preserved."""
        # Create fix that already matches context style
        consistent_fix = FixCandidate(
            fix_code="""int test_function(char* input) {
    if (input != NULL) {
        return strlen(input);
    }
    return 0;
}""",
            explanation="Already well-styled fix",
            confidence_score=0.9,
            complexity=FixComplexity.SIMPLE,
            risk_assessment="Low",
            affected_files=["test.c"],
            line_ranges=[]
        )
        
        checker = StyleConsistencyChecker()
        styled_code, consistency_score = checker.check_and_fix_style(
            consistent_fix, sample_code_context
        )
        
        # Code should remain largely unchanged
        assert "if (input != NULL)" in styled_code
        assert consistency_score >= 0.5  # Should get good score for good style 