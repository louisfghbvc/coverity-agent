# Issue Classifier - Feature Plan

## Overview
Categorize parsed defects into specific problem types to enable targeted fix strategy selection and improve fix success rates.

## Requirements

### Functional Requirements
- **FR1**: Classify null pointer dereference issues
- **FR2**: Identify uninitialized value problems  
- **FR3**: Categorize memory leak and resource management issues
- **FR4**: Detect buffer overflow and bounds checking issues
- **FR5**: Identify dead code and unreachable statements
- **FR6**: Classify concurrency and threading issues
- **FR7**: Support extensible classification rule system
- **FR8**: Generate confidence scores for classifications
- **FR9**: Handle multi-category defects (composite issues)

### Non-Functional Requirements
- **NFR1**: Classify 500+ defects per second
- **NFR2**: >95% classification accuracy
- **NFR3**: Extensible rule engine for new defect types
- **NFR4**: Memory efficient processing for large batches

## Technical Design

### Classification Taxonomy
```python
class DefectCategory(Enum):
    NULL_POINTER = "null_pointer"
    UNINITIALIZED_VALUE = "uninitialized_value"
    MEMORY_LEAK = "memory_leak"
    BUFFER_OVERFLOW = "buffer_overflow"
    RESOURCE_LEAK = "resource_leak" 
    DEAD_CODE = "dead_code"
    CONCURRENCY = "concurrency"
    LOGIC_ERROR = "logic_error"
    TYPE_CONFUSION = "type_confusion"
    UNKNOWN = "unknown"

class FixComplexity(Enum):
    SIMPLE = "simple"      # Single line fix
    MODERATE = "moderate"  # Function-level changes
    COMPLEX = "complex"    # Multi-function/file changes
    CRITICAL = "critical"  # Architecture-level changes

@dataclass
class ClassificationResult:
    primary_category: DefectCategory
    secondary_categories: List[DefectCategory]
    confidence_score: float  # 0.0 to 1.0
    fix_complexity: FixComplexity
    fix_strategy_hints: List[str]
    reasoning: str
    classification_timestamp: datetime
```

### Core Components

#### 1. Rule Engine
```python
class ClassificationRule:
    def __init__(self, name: str, category: DefectCategory, 
                 priority: int, patterns: List[str]):
        self.name = name
        self.category = category
        self.priority = priority
        self.patterns = patterns
    
    def matches(self, defect: ParsedDefect) -> float:
        """Return confidence score (0.0-1.0) if rule matches"""
        pass

class RuleEngine:
    def __init__(self):
        self.rules: List[ClassificationRule] = []
        self.load_default_rules()
    
    def classify(self, defect: ParsedDefect) -> ClassificationResult:
        """Apply classification rules to defect"""
        pass
    
    def add_rule(self, rule: ClassificationRule):
        """Add custom classification rule"""
        pass
```

#### 2. Pattern Matcher
```python
class PatternMatcher:
    def __init__(self):
        self.null_patterns = [
            r"NULL_RETURNS", r"FORWARD_NULL", r"REVERSE_INULL",
            r"null.*pointer", r"dereference.*null"
        ]
        self.uninit_patterns = [
            r"UNINIT", r"uninitialized.*variable", r"use.*before.*init"
        ]
        # More pattern definitions...
    
    def match_checker_name(self, checker: str, patterns: List[str]) -> float:
        """Match checker name against patterns"""
        pass
    
    def match_description(self, description: str, patterns: List[str]) -> float:
        """Match defect description against patterns"""
        pass
```

#### 3. Context Analyzer
```python
class ContextAnalyzer:
    def analyze_function_context(self, defect: ParsedDefect) -> Dict[str, Any]:
        """Analyze function-level context for classification hints"""
        return {
            "has_null_checks": False,
            "has_memory_allocation": False,
            "has_loops": False,
            "return_type": "void",
            "parameter_count": 0
        }
    
    def analyze_code_patterns(self, defect: ParsedDefect) -> Dict[str, Any]:
        """Analyze code patterns around defect location"""
        pass
```

#### 4. Machine Learning Classifier (Optional)
```python
class MLClassifier:
    def __init__(self, model_path: str = None):
        self.model = None
        if model_path:
            self.load_model(model_path)
    
    def train(self, training_data: List[Tuple[ParsedDefect, DefectCategory]]):
        """Train classification model on labeled data"""
        pass
    
    def predict(self, defect: ParsedDefect) -> Tuple[DefectCategory, float]:
        """Predict category and confidence using ML model"""
        pass
```

## Default Classification Rules

### Null Pointer Rules
```python
null_pointer_rules = [
    ClassificationRule(
        name="coverity_null_checkers",
        category=DefectCategory.NULL_POINTER,
        priority=100,
        patterns=["NULL_RETURNS", "FORWARD_NULL", "REVERSE_INULL"]
    ),
    ClassificationRule(
        name="null_description_patterns", 
        category=DefectCategory.NULL_POINTER,
        priority=80,
        patterns=[r"null.*pointer", r"dereference.*null", r"nullptr"]
    )
]
```

### Memory Management Rules
```python
memory_rules = [
    ClassificationRule(
        name="memory_leak_checkers",
        category=DefectCategory.MEMORY_LEAK,
        priority=100,
        patterns=["RESOURCE_LEAK", "MEMORY_LEAK", "ALLOC_FREE_MISMATCH"]
    ),
    ClassificationRule(
        name="buffer_overflow_checkers",
        category=DefectCategory.BUFFER_OVERFLOW, 
        priority=100,
        patterns=["BUFFER_SIZE_WARNING", "OVERRUN", "NEGATIVE_RETURNS"]
    )
]
```

## Implementation Plan

### Phase 1: Rule Engine Foundation (Week 1)
- Implement core rule engine
- Create default rule sets for top 5 defect types
- Basic pattern matching system
- Unit tests for classification logic

### Phase 2: Advanced Classification (Week 2)
- Context analysis implementation
- Confidence scoring algorithms
- Fix complexity assessment
- Extended rule coverage (top 15 defect types)

### Phase 3: ML Integration (Week 3)
- Optional ML classifier implementation
- Training data collection framework
- Hybrid rule-based + ML approach
- Performance optimization

### Phase 4: Production Features (Week 4)
- Rule configuration management
- Classification statistics and reporting
- Integration testing with Issue Parser
- Documentation and examples

## Configuration System

```yaml
# classifier_config.yaml
issue_classifier:
  classification_mode: "rule_based"  # "rule_based", "ml", "hybrid"
  
  rules:
    enable_default_rules: true
    custom_rules_path: "custom_rules/"
    rule_priority_threshold: 50
    
  ml_model:
    enabled: false
    model_path: "models/defect_classifier.pkl"
    confidence_threshold: 0.7
    
  performance:
    batch_size: 100
    enable_caching: true
    cache_size: 1000
    
  output:
    include_reasoning: true
    include_alternative_categories: true
    confidence_threshold: 0.6
```

## Testing Strategy

### Unit Tests
- Individual rule matching
- Pattern matching accuracy
- Confidence score calculation
- Context analysis components

### Integration Tests
- End-to-end classification workflow
- Performance with large defect sets
- Rule priority resolution
- Multi-category defect handling

### Accuracy Tests
- Known defect classification validation
- Cross-validation with manual classification
- Precision/recall metrics per category
- Edge case handling

## Integration Points

### Upstream Dependencies
- Issue Parser (ParsedDefect objects)
- Configuration system
- Optional training data sources

### Downstream Consumers  
- Fix Planner (ClassificationResult objects)
- Reporting system (classification statistics)
- Code Retriever (category-specific context hints)

## Success Metrics

- **Accuracy**: >95% correct primary category classification
- **Coverage**: Support for top 20 Coverity defect types
- **Performance**: <2ms average classification time per defect
- **Confidence**: >90% of classifications above 0.8 confidence threshold

## Extension Points

### Custom Rule Development
```python
# Example custom rule
class CustomMemoryRule(ClassificationRule):
    def matches(self, defect: ParsedDefect) -> float:
        # Custom classification logic
        if "malloc" in defect.description and "free" not in defect.description:
            return 0.9
        return 0.0
```

### Domain-Specific Classifications
- Project-specific defect patterns
- Language-specific categorization
- Industry-specific classification schemas
- Custom fix complexity assessments

## Risk Mitigation

### Technical Risks
- **Classification Accuracy**: Extensive test coverage with known cases
- **Performance Degradation**: Efficient pattern matching and caching
- **Rule Conflicts**: Clear priority system and conflict resolution
- **False Positives**: Conservative confidence thresholds

### Implementation Approach
- Start with high-confidence, common defect types
- Incremental rule addition with validation
- A/B testing for classification improvements
- User feedback integration for rule refinement 