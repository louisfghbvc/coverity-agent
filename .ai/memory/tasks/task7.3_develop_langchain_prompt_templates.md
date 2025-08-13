---
id: 7.3
title: 'Develop LangChain Prompt Templates'
status: pending
priority: high
feature: LLM Fix Generator - Prompt Engineering
dependencies:
  - 7.1
  - 7.2
assigned_agent: null
created_at: "2025-06-16T09:27:12Z"
started_at: null
completed_at: null
error_log: null
---

## Description

Create defect-specific ChatPromptTemplate and PromptTemplate systems optimized for NVIDIA NIM models with dynamic variable substitution and template composition.

## Details

### Core Prompt Template Components

1. **Defect-Specific ChatPromptTemplates**
   - NullPointerTemplate: For null pointer dereference defects
   - MemoryLeakTemplate: For memory allocation/deallocation issues
   - BufferOverflowTemplate: For buffer boundary violations
   - UninitializedVariableTemplate: For uninitialized variable usage
   - GenericTemplate: Fallback for other defect types

2. **System Message Templates**
   - Role definition optimized for NVIDIA NIM models
   - Context setting for code analysis and fix generation
   - Output format instructions for structured JSON responses
   - Safety guidelines and code quality requirements

3. **Human Message Templates**
   - Defect context injection (file path, line number, surrounding code)
   - Code style hints and language-specific guidelines
   - Multi-candidate generation instructions
   - Confidence scoring requirements

4. **Template Composition System**
   - Modular template components for reusability
   - Dynamic variable substitution with type validation
   - Template inheritance and customization
   - Context-aware template selection logic

### Implementation Requirements

- **LangChain Integration**: Use ChatPromptTemplate and PromptTemplate classes
- **Variable Validation**: Type checking for template variables
- **NIM Optimization**: Templates optimized for Llama/Mistral/CodeLlama models
- **Dynamic Selection**: Intelligent template selection based on defect type
- **Output Formatting**: Structured JSON output instructions integrated
- **Context Awareness**: Code language detection and style adaptation

### File Structure

```
src/fix_generator/
└── prompt_templates.py      # LangChain prompt template definitions

# Template files (optional external storage)
templates/
├── defect_analysis/
│   ├── null_pointer.yaml
│   ├── memory_leak.yaml
│   ├── buffer_overflow.yaml
│   ├── uninitialized_variable.yaml
│   └── generic.yaml
└── style_analysis/
    └── style_consistency.yaml
```

### Template Classes

1. **DefectAnalysisTemplateManager**
   - Template selection based on defect type
   - Variable validation and substitution
   - Context-aware template customization
   - Template composition and inheritance

2. **Defect-Specific Template Classes**
   - NullPointerTemplate with specialized instructions
   - MemoryLeakTemplate with allocation/deallocation focus
   - BufferOverflowTemplate with boundary checking
   - UninitializedVariableTemplate with initialization patterns

3. **StyleAnalysisTemplate**
   - Code style detection and consistency checking
   - Language-specific style guidelines
   - Style recommendation generation

4. **TemplateComposer**
   - Dynamic template composition
   - Variable injection and validation
   - Output format standardization

### Template Variables

**Standard Variables:**
- `defect_type`: Type of defect being analyzed
- `code_context`: Surrounding code context
- `file_content`: Relevant file content
- `style_hints`: Code style guidelines
- `language`: Programming language detected
- `fix_candidates_count`: Number of fix candidates to generate

**Advanced Variables:**
- `confidence_threshold`: Minimum confidence requirement
- `complexity_limit`: Maximum allowed fix complexity
- `safety_checks`: Additional safety validation requirements
- `performance_considerations`: Performance impact guidelines

### LangChain Template Examples

```python
# ChatPromptTemplate for defect analysis
defect_analysis_template = ChatPromptTemplate.from_messages([
    SystemMessage(content="You are an expert code analyst..."),
    HumanMessage(content="Analyze this {defect_type} defect in {language}..."),
])

# PromptTemplate for style analysis
style_template = PromptTemplate(
    input_variables=["code_context", "language"],
    template="Analyze the coding style in this {language} code..."
)
```

## Test Strategy

### Unit Tests Required

1. **Template Creation Tests**
   - ChatPromptTemplate instantiation for all defect types
   - PromptTemplate creation for style analysis
   - Variable validation and type checking
   - Template composition functionality

2. **Variable Substitution Tests**
   - Dynamic variable injection
   - Type validation for template variables
   - Missing variable handling
   - Invalid variable format detection

3. **Template Selection Tests**
   - Defect type-based template selection
   - Fallback to generic template
   - Template customization based on context
   - Language-specific template adaptation

4. **Output Format Tests**
   - Structured JSON output instruction generation
   - LangChain PydanticOutputParser compatibility
   - Template output validation
   - Multi-candidate generation instructions

5. **Integration Tests**
   - Template usage with LangChain chains
   - Prompt generation with real defect data
   - Template performance with different NIM models
   - End-to-end prompt template workflow

### Success Criteria

- All defect-specific templates generate properly formatted prompts
- Variable substitution works correctly with type validation
- Template selection logic chooses appropriate templates
- Generated prompts are optimized for NVIDIA NIM models
- JSON output instructions produce parseable responses
- Template system integrates seamlessly with LangChain
- Comprehensive test coverage >95%
- Templates generate high-quality, consistent results
- Documentation includes template usage examples and customization guides 