---
id: 7.7
title: 'Build Style Consistency Checker'
status: pending
priority: medium
feature: LLM Fix Generator - Style Analysis
dependencies:
  - 7.3
  - 7.4
assigned_agent: null
created_at: "2025-06-16T09:27:12Z"
started_at: null
completed_at: null
error_log: null
---

## Description

Implement LangChain-based style analysis using dedicated prompt templates with Pydantic models for structured style recommendations and language-specific guidelines.

## Details

### Core Style Analysis Components

1. **LangChain Style Analysis**
   - Dedicated PromptTemplate for style detection
   - ChatPromptTemplate for style consistency checking
   - Language-specific style guideline templates
   - Style recommendation generation using LLM

2. **Pydantic Style Models**
   - StyleAnalysisResult with structured style information
   - StyleViolation for specific style issues
   - StyleRecommendation for improvement suggestions
   - DetectedStyle for automatic style pattern recognition

3. **Language-Specific Guidelines**
   - C/C++ style guidelines (Google, LLVM, etc.)
   - Python style guidelines (PEP 8, Black, etc.)
   - Java style guidelines (Google Java Style, etc.)
   - JavaScript/TypeScript style guidelines
   - Custom style pattern detection

4. **Style Application System**
   - Generated fix style consistency checking
   - Style hint application to LLM-generated fixes
   - Automatic style correction suggestions
   - Style consistency scoring and validation

### Implementation Requirements

- **LangChain Integration**: Use PromptTemplate and ChatPromptTemplate for style analysis
- **Pydantic Models**: Structured output using models from Task 7.1
- **Language Detection**: Automatic programming language identification
- **Style Pattern Recognition**: ML-based style pattern detection
- **Consistency Scoring**: Quantitative style consistency measurement
- **Integration**: Seamless integration with defect analysis workflow

### File Structure

```
src/fix_generator/
└── style_checker.py         # LangChain-based style analysis implementation
```

### Style Analysis Classes

1. **LangChainStyleAnalyzer**
   - Main style analysis orchestrator
   - Language-specific template selection
   - LangChain prompt template management
   - Style analysis result processing

2. **StylePromptTemplateManager**
   - Language-specific prompt template management
   - Style guideline template composition
   - Dynamic template selection based on language
   - Template customization for different style guides

3. **StyleConsistencyChecker**
   - Style consistency validation for generated fixes
   - Consistency scoring and measurement
   - Style deviation detection and reporting
   - Integration with fix generation pipeline

4. **StyleRecommendationEngine**
   - LangChain-based style recommendation generation
   - Context-aware improvement suggestions
   - Style guide compliance checking
   - Automated style correction proposals

### LangChain Template Examples

```python
# Style analysis prompt template
style_analysis_template = PromptTemplate(
    input_variables=["code_context", "language", "style_guide"],
    template="""
    Analyze the coding style in this {language} code following {style_guide} guidelines:
    
    Code:
    {code_context}
    
    Provide a structured analysis including:
    1. Detected style patterns
    2. Style consistency score (0.0-1.0)
    3. Specific style violations
    4. Recommendations for improvement
    
    Format your response as JSON matching the StyleAnalysisResult schema.
    """
)

# Style consistency checking template
consistency_template = ChatPromptTemplate.from_messages([
    SystemMessage(content="""You are a code style expert specializing in {language} 
    style consistency analysis following {style_guide} guidelines."""),
    HumanMessage(content="""
    Original Code Style:
    {original_style}
    
    Generated Fix:
    {generated_fix}
    
    Check if the generated fix maintains style consistency with the original code.
    Provide specific style recommendations if inconsistencies are found.
    """)
])
```

### Style Detection Logic

1. **Automatic Style Detection**
   - Indentation pattern analysis (spaces vs tabs, width)
   - Brace style detection (K&R, Allman, GNU, etc.)
   - Naming convention analysis (camelCase, snake_case, PascalCase)
   - Spacing and formatting pattern detection

2. **Language-Specific Analysis**
   - C/C++: Pointer style, header guards, namespace usage
   - Python: Import style, docstring format, line length
   - Java: Package naming, access modifier usage
   - JavaScript: Arrow functions, semicolon usage

3. **Style Scoring Algorithm**
   ```python
   def calculate_style_score(detected_patterns, violations):
       base_score = 1.0
       penalty_per_violation = 0.1
       
       consistency_score = base_score - (len(violations) * penalty_per_violation)
       return max(0.0, min(1.0, consistency_score))
   ```

### Style Application Workflow

1. **Pre-Analysis Style Detection**
   - Analyze existing code context for style patterns
   - Generate style hints for LLM prompt templates
   - Create language-specific style guidelines

2. **Fix Generation Integration**
   - Inject style hints into defect analysis prompts
   - Apply detected style patterns to fix generation
   - Ensure generated fixes match existing code style

3. **Post-Generation Validation**
   - Validate generated fix style consistency
   - Score style compliance and consistency
   - Generate style improvement recommendations

### Pydantic Models Integration

```python
# From Task 7.1 - StyleAnalysisResult
class StyleAnalysisResult(BaseModel):
    detected_style: DetectedStyle
    consistency_score: float = Field(ge=0.0, le=1.0)
    style_violations: List[StyleViolation]
    recommendations: List[StyleRecommendation]
    language_detected: str
    style_guide_used: Optional[str]

class DetectedStyle(BaseModel):
    indentation_type: str  # "spaces" or "tabs"
    indentation_width: int
    brace_style: str  # "K&R", "Allman", "GNU", etc.
    naming_convention: str  # "camelCase", "snake_case", etc.
    line_length_preference: int
    spacing_patterns: Dict[str, Any]
```

## Test Strategy

### Unit Tests Required

1. **Style Template Tests**
   - LangChain PromptTemplate creation for style analysis
   - Template variable substitution and validation
   - Language-specific template selection
   - Style guideline template composition

2. **Style Detection Tests**
   - Automatic style pattern detection accuracy
   - Language-specific style analysis
   - Style consistency scoring validation
   - Style violation detection accuracy

3. **LangChain Integration Tests**
   - Style analysis using LangChain prompts
   - Pydantic model parsing from LLM responses
   - Template composition and selection logic
   - Error handling and fallback strategies

4. **Style Application Tests**
   - Style hint generation for fix prompts
   - Style consistency validation for generated fixes
   - Style recommendation generation
   - Integration with defect analysis workflow

5. **Language Coverage Tests**
   - C/C++ style analysis and recommendations
   - Python style guideline compliance
   - Java style pattern detection
   - JavaScript/TypeScript style validation

### Success Criteria

- Style analysis accurately detects coding patterns across supported languages
- LangChain templates generate appropriate style analysis prompts
- Pydantic models parse style analysis results correctly
- Style consistency scoring provides meaningful measurements (0.0-1.0 range)
- Generated fixes maintain style consistency with original code
- Style recommendations are actionable and language-appropriate
- Integration with defect analysis workflow is seamless
- Comprehensive test coverage >95%
- Performance meets requirements (<2s for style analysis)
- Documentation includes style guideline configuration and usage examples 