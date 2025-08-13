# Fix Planner - Feature Plan [DEPRECATED - MVP ARCHITECTURE]

## 🚫 DEPRECATED NOTICE
**This component has been removed from the MVP architecture and its functionality integrated into the LLM Fix Generator.**

In the MVP approach, fix planning and strategy selection is handled directly by the LLM Fix Generator through sophisticated prompting, eliminating the need for a separate planning component. This provides:

- **Intelligent Planning**: LLM can create adaptive fix strategies based on full context
- **Dynamic Approach**: Not limited to predefined fix templates
- **Contextual Awareness**: Plans consider both defect type and surrounding code
- **Integrated Workflow**: Planning and generation happen in single step

**Migration Path**: The fix strategies, templates, and planning logic defined below can be converted into LLM prompt engineering patterns within the Fix Generator component.

---

# [ORIGINAL PLAN - FOR REFERENCE ONLY]

## Overview
Develop comprehensive fix strategies based on defect classifications and code context, providing structured plans and templates that guide the LLM-based fix generation process.

## Requirements

### Functional Requirements
- **FR1**: Generate fix strategies for classified defect types
- **FR2**: Create fix templates for common defect patterns
- **FR3**: Assess fix complexity and risk levels
- **FR4**: Plan multi-step fixes for complex defects
- **FR5**: Consider coding standards and project conventions
- **FR6**: Generate alternative fix approaches
- **FR7**: Integrate with project-specific fix policies
- **FR8**: Provide fix validation criteria

### Non-Functional Requirements
- **NFR1**: Generate fix plans for 200+ defects per minute
- **NFR2**: Support extensible strategy definitions
- **NFR3**: Maintain fix strategy consistency across similar defects
- **NFR4**: Provide explainable fix reasoning

## Technical Design

### Output Data Structures
```python
@dataclass
class FixPlan:
    defect_id: str
    strategy_name: str
    fix_approach: FixApproach
    complexity: FixComplexity
    risk_level: RiskLevel
    
    # Fix steps
    primary_fix: FixStep
    alternative_fixes: List[FixStep]
    validation_criteria: List[ValidationCriterion]
    
    # Context
    affected_files: List[str]
    dependencies: List[str]
    coding_standards: List[str]
    
    # Metadata
    confidence_score: float
    estimated_effort: int  # minutes
    plan_timestamp: datetime

@dataclass
class FixStep:
    step_id: str
    description: str
    action_type: ActionType  # "add", "modify", "delete", "refactor"
    target_location: CodeLocation
    template: str
    priority: int
    
    # LLM guidance
    prompt_template: str
    context_hints: List[str]
    constraints: List[str]

@dataclass
class ValidationCriterion:
    criterion_type: str  # "compile", "test", "static_analysis", "pattern"
    description: str
    success_condition: str
    failure_action: str

class FixApproach(Enum):
    DEFENSIVE_PROGRAMMING = "defensive"  # Add checks and guards
    CORRECTIVE_LOGIC = "corrective"      # Fix the actual logic error
    RESOURCE_MANAGEMENT = "resource"     # Fix resource handling
    REFACTORING = "refactoring"          # Restructure problematic code
    PATTERN_APPLICATION = "pattern"      # Apply established patterns

class RiskLevel(Enum):
    LOW = "low"           # Single line, well-understood fix
    MEDIUM = "medium"     # Function-level changes
    HIGH = "high"         # Multi-function or complex logic changes
    CRITICAL = "critical" # Architectural or cross-component changes
```

### Core Components

#### 1. Strategy Selector
```python
class StrategySelector:
    def __init__(self):
        self.strategies = self._load_fix_strategies()
        self.strategy_matrix = self._build_strategy_matrix()
    
    def select_strategy(self, classification: ClassificationResult, 
                       context: CodeContext) -> str:
        """Select optimal fix strategy based on defect and context"""
        pass
    
    def _build_strategy_matrix(self) -> Dict[str, List[str]]:
        """Build matrix mapping defect types to fix strategies"""
        return {
            DefectCategory.NULL_POINTER: [
                "null_check_insertion",
                "defensive_programming", 
                "early_return_pattern",
                "assertion_based"
            ],
            DefectCategory.MEMORY_LEAK: [
                "raii_pattern",
                "smart_pointer_conversion",
                "explicit_cleanup",
                "scope_based_management"
            ],
            DefectCategory.UNINITIALIZED_VALUE: [
                "initialization_at_declaration",
                "constructor_initialization",
                "default_value_assignment",
                "conditional_initialization"
            ]
        }
```

#### 2. Template Engine
```python
class TemplateEngine:
    def __init__(self):
        self.templates = self._load_fix_templates()
        self.jinja_env = self._setup_jinja_environment()
    
    def generate_fix_template(self, strategy: str, context: CodeContext) -> str:
        """Generate fix template for given strategy and context"""
        pass
    
    def customize_template(self, template: str, 
                          variables: Dict[str, Any]) -> str:
        """Customize template with context-specific variables"""
        pass

# Example templates
NULL_CHECK_TEMPLATE = """
// Add null pointer check before dereference
if ({{ variable_name }} != NULL) {
    {{ original_code }}
} else {
    // Handle null pointer case
    {{ error_handling }}
}
"""

MEMORY_CLEANUP_TEMPLATE = """
// Add cleanup for allocated memory
{{ allocation_code }}
if ({{ variable_name }} != NULL) {
    // Use the allocated memory
    {{ usage_code }}
    // Clean up
    free({{ variable_name }});
    {{ variable_name }} = NULL;
}
"""
```

#### 3. Risk Assessor
```python
class RiskAssessor:
    def __init__(self):
        self.risk_factors = self._load_risk_factors()
    
    def assess_fix_risk(self, fix_plan: FixPlan, 
                       context: CodeContext) -> RiskAssessment:
        """Assess risk level and potential impact of proposed fix"""
        factors = []
        
        # Code complexity factors
        if self._involves_multiple_functions(fix_plan):
            factors.append(RiskFactor("multiple_functions", 0.3))
        
        # Dependency factors  
        if self._affects_external_apis(fix_plan, context):
            factors.append(RiskFactor("external_api", 0.4))
            
        # Testing factors
        if not self._has_test_coverage(context):
            factors.append(RiskFactor("no_test_coverage", 0.2))
            
        return self._calculate_risk_level(factors)
    
    def suggest_risk_mitigation(self, risk: RiskAssessment) -> List[str]:
        """Suggest steps to mitigate identified risks"""
        pass

@dataclass
class RiskFactor:
    name: str
    weight: float
    description: str = ""

@dataclass
class RiskAssessment:
    overall_risk: RiskLevel
    risk_factors: List[RiskFactor]
    mitigation_suggestions: List[str]
    confidence: float
```

#### 4. Complexity Analyzer
```python
class ComplexityAnalyzer:
    def analyze_fix_complexity(self, defect: ParsedDefect, 
                             classification: ClassificationResult,
                             context: CodeContext) -> FixComplexity:
        """Analyze complexity of required fix"""
        
        complexity_score = 0
        
        # Defect type complexity
        type_complexity = {
            DefectCategory.NULL_POINTER: 1,      # Usually simple checks
            DefectCategory.UNINITIALIZED_VALUE: 2, # May need deeper analysis  
            DefectCategory.MEMORY_LEAK: 3,       # Complex resource management
            DefectCategory.CONCURRENCY: 4,       # Very complex threading issues
        }
        complexity_score += type_complexity.get(classification.primary_category, 2)
        
        # Context complexity
        if len(context.function_calls) > 10:
            complexity_score += 1
        if len(context.dependencies) > 5:
            complexity_score += 1
        if context.primary_function in ["main", "init", "cleanup"]:
            complexity_score += 1  # Critical functions
            
        return self._score_to_complexity(complexity_score)
```

#### 5. Standards Checker
```python
class CodingStandardsChecker:
    def __init__(self, project_config: Dict[str, Any]):
        self.standards = project_config.get("coding_standards", {})
        self.style_guide = project_config.get("style_guide", "default")
    
    def get_applicable_standards(self, context: CodeContext) -> List[str]:
        """Get coding standards applicable to the code context"""
        standards = []
        
        # Language-specific standards
        if context.language == "c":
            standards.extend(["MISRA-C", "CERT-C"])
        elif context.language == "cpp":
            standards.extend(["MISRA-C++", "CERT-C++", "Google-Style"])
            
        # Project-specific standards
        standards.extend(self.standards.get("required", []))
        
        return standards
    
    def validate_fix_against_standards(self, fix_plan: FixPlan, 
                                     standards: List[str]) -> List[str]:
        """Validate proposed fix against coding standards"""
        violations = []
        # Check for standard violations and return list
        return violations
```

## Fix Strategy Library

### Null Pointer Strategies
```python
null_pointer_strategies = {
    "null_check_insertion": {
        "description": "Add explicit null checks before dereference",
        "complexity": FixComplexity.SIMPLE,
        "risk": RiskLevel.LOW,
        "template": NULL_CHECK_TEMPLATE,
        "validation": ["compile_check", "null_test"]
    },
    
    "early_return_pattern": {
        "description": "Return early if pointer is null",
        "complexity": FixComplexity.SIMPLE,
        "risk": RiskLevel.LOW,
        "template": EARLY_RETURN_TEMPLATE,
        "validation": ["compile_check", "return_value_test"]
    },
    
    "defensive_programming": {
        "description": "Add comprehensive defensive checks",
        "complexity": FixComplexity.MODERATE,
        "risk": RiskLevel.MEDIUM,
        "template": DEFENSIVE_TEMPLATE,
        "validation": ["compile_check", "edge_case_test", "performance_test"]
    }
}
```

### Memory Management Strategies
```python
memory_strategies = {
    "raii_pattern": {
        "description": "Apply RAII pattern for automatic resource management",
        "complexity": FixComplexity.MODERATE,
        "risk": RiskLevel.MEDIUM,
        "applicable_languages": ["cpp"],
        "template": RAII_TEMPLATE,
        "validation": ["compile_check", "memory_leak_test", "exception_safety_test"]
    },
    
    "smart_pointer_conversion": {
        "description": "Convert raw pointers to smart pointers",
        "complexity": FixComplexity.COMPLEX,
        "risk": RiskLevel.HIGH,
        "applicable_languages": ["cpp"],
        "template": SMART_POINTER_TEMPLATE,
        "validation": ["compile_check", "memory_test", "performance_impact_test"]
    }
}
```

## Implementation Plan

### Phase 1: Strategy Framework (Week 1)
- Core strategy selection engine
- Basic template system
- Risk assessment foundation
- Default strategy library for top 5 defect types

### Phase 2: Template Engine (Week 2)
- Advanced template customization
- Context-aware template selection
- Template validation system
- Extended strategy coverage

### Phase 3: Risk & Complexity Analysis (Week 3)
- Comprehensive risk assessment
- Fix complexity analysis
- Coding standards integration
- Multi-step fix planning

### Phase 4: Advanced Features (Week 4)
- Alternative fix generation
- Project-specific customization
- Performance optimization
- Integration testing

## Configuration

```yaml
# fix_planner_config.yaml
fix_planner:
  strategy_selection:
    prefer_simple_fixes: true
    max_alternatives: 3
    confidence_threshold: 0.7
    
  risk_assessment:
    enable_risk_analysis: true
    risk_factors:
      multiple_files: 0.3
      external_dependencies: 0.4
      critical_functions: 0.5
      no_tests: 0.2
      
  templates:
    template_directory: "fix_templates/"
    enable_custom_templates: true
    template_validation: true
    
  coding_standards:
    enforce_standards: true
    standards_config: "standards.yaml"
    violation_handling: "warn"  # "warn", "error", "ignore"
    
  complexity_analysis:
    complexity_factors:
      function_size: 0.2
      dependency_count: 0.3
      defect_type: 0.4
      code_patterns: 0.1
```

## Testing Strategy

### Unit Tests
- Strategy selection accuracy
- Template generation correctness
- Risk assessment precision
- Complexity calculation validation

### Integration Tests
- End-to-end fix planning workflow
- Multi-strategy coordination
- Standards compliance checking
- Performance with large defect sets

### Validation Tests
- Fix plan effectiveness measurement
- Template customization accuracy
- Risk prediction validation
- Complexity estimation accuracy

## Integration Points

### Upstream Dependencies
- Issue Classifier (classification results)
- Code Retriever (code context information)
- Project configuration (standards, policies)

### Downstream Consumers
- Fix Generator (structured fix plans and templates)
- Verification system (validation criteria)
- Reporting system (fix statistics and metrics)

## Success Metrics

- **Strategy Accuracy**: >90% appropriate strategy selection
- **Fix Success Rate**: >85% successful fixes from generated plans
- **Risk Prediction**: >80% accurate risk level assessment
- **Performance**: <100ms average plan generation time

## Extension Points

### Custom Strategy Development
```python
class CustomFixStrategy:
    def __init__(self, name: str, category: DefectCategory):
        self.name = name
        self.category = category
    
    def is_applicable(self, defect: ParsedDefect, context: CodeContext) -> bool:
        """Determine if strategy applies to this defect"""
        pass
    
    def generate_plan(self, defect: ParsedDefect, context: CodeContext) -> FixPlan:
        """Generate custom fix plan"""
        pass
```

### Domain-Specific Planning
- Project-specific fix policies
- Industry-specific compliance requirements
- Language-specific optimization strategies
- Team-specific coding conventions

## Risk Mitigation

### Technical Risks
- **Strategy Selection Errors**: Comprehensive validation and fallback strategies
- **Template Incompatibility**: Extensive template testing and validation
- **Risk Assessment Inaccuracy**: Continuous calibration with actual outcomes
- **Complexity Underestimation**: Conservative estimates with safety margins

### Implementation Approach
- Start with well-understood defect types and proven strategies
- Incremental strategy library expansion
- Continuous validation against real-world fix outcomes
- User feedback integration for strategy refinement 