# Code Retriever - Feature Plan (MVP Architecture)

## Overview
Locate and extract relevant source code context around defects to provide comprehensive information for LLM fix generation, including function definitions, dependencies, and related code patterns. **MVP Enhancement**: Leverages classification hints from Issue Parser for intelligent context extraction.

## Requirements

### Functional Requirements
- **FR1**: Extract function-level context around defect locations
- **FR2**: Retrieve variable declarations and type definitions
- **FR3**: Include related function dependencies and call chains
- **FR4**: Handle cross-file dependencies and includes
- **FR5**: Extract code patterns and idioms relevant to fix strategies
- **FR6**: Support multiple programming languages (C, C++, Java, Python)
- **FR7**: Provide syntax-highlighted code snippets
- **FR8**: Generate code context summaries
- **FR9**: Use classification hints for intelligent context sizing (MVP Addition)

### Non-Functional Requirements
- **NFR1**: Retrieve context for 100+ defects per minute
- **NFR2**: Support large codebases (>1M lines of code)
- **NFR3**: Memory efficient processing
- **NFR4**: Robust handling of malformed or incomplete source files
- **NFR5**: Adaptive context extraction based on defect hints (<50ms overhead)

## Technical Design

### Output Data Structures
```python
@dataclass
class CodeContext:
    defect_id: str
    primary_file: str
    primary_function: str
    context_lines: Tuple[int, int]  # (start_line, end_line)
    
    # Code content
    source_code: str
    highlighted_code: str
    affected_lines: List[int]
    
    # Analysis results
    variables: List[VariableInfo]
    function_calls: List[FunctionCall]
    dependencies: List[Dependency]
    code_patterns: List[CodePattern]
    
    # Metadata
    language: str
    file_encoding: str
    extraction_timestamp: datetime

@dataclass 
class VariableInfo:
    name: str
    type: str
    declaration_line: int
    scope: str  # "local", "parameter", "global", "member"
    is_initialized: bool
    usage_lines: List[int]

@dataclass
class FunctionCall:
    function_name: str
    line_number: int
    arguments: List[str]
    return_type: str
    is_external: bool
    source_file: str = ""

@dataclass
class Dependency:
    type: str  # "include", "import", "function_call", "variable_ref"
    target: str
    source_file: str
    line_number: int
    is_external: bool

@dataclass
class CodePattern:
    pattern_type: str  # "null_check", "memory_alloc", "error_handling"
    confidence: float
    lines: List[int]
    description: str
```

### Core Components

#### 1. Source File Manager
```python
class SourceFileManager:
    def __init__(self, project_root: str):
        self.project_root = project_root
        self.file_cache: Dict[str, str] = {}
        self.encoding_cache: Dict[str, str] = {}
    
    def read_file(self, file_path: str) -> Tuple[str, str]:
        """Read file content and detect encoding"""
        pass
    
    def get_line_range(self, file_path: str, start: int, end: int) -> str:
        """Extract specific line range from file"""
        pass
    
    def find_function_bounds(self, file_path: str, function_name: str, 
                           start_line: int) -> Tuple[int, int]:
        """Find start and end lines of function containing given line"""
        pass
```

#### 2. Language Parser
```python
class LanguageParser:
    def __init__(self, language: str):
        self.language = language
        self.parser = self._get_parser(language)
    
    def parse_function(self, source_code: str, line_number: int) -> FunctionInfo:
        """Parse function containing the specified line"""
        pass
    
    def extract_variables(self, source_code: str) -> List[VariableInfo]:
        """Extract variable declarations and usage"""
        pass
    
    def find_function_calls(self, source_code: str) -> List[FunctionCall]:
        """Find all function calls in code"""
        pass
    
    def analyze_dependencies(self, source_code: str) -> List[Dependency]:
        """Analyze includes, imports, and dependencies"""
        pass
```

#### 3. Context Analyzer (Updated for MVP)
```python
class ContextAnalyzer:
    def __init__(self, project_root: str):
        self.project_root = project_root
        self.symbol_index: Dict[str, List[str]] = {}
        
    def build_symbol_index(self):
        """Build index of symbols across project"""
        pass
    
    def get_optimal_context_size(self, defect: ParsedDefect) -> int:
        """Determine optimal context lines based on classification hints"""
        hints = defect.classification_hints or {}
        
        # Use classification hints instead of separate classification component
        likely_categories = hints.get('likely_categories', [])
        complexity_hints = hints.get('complexity_hints', [])
        
        if 'null_pointer' in likely_categories:
            return 20  # Need less context for null checks
        elif 'memory_management' in likely_categories:
            return 50  # Need more context for memory management
        elif 'multi_step' in complexity_hints:
            return 40  # More context for complex issues
        elif 'function_level' in complexity_hints:
            return 35  # Moderate context for function-level issues
        
        return 30  # Default context size
    
    def find_related_functions(self, function_name: str, 
                             file_path: str) -> List[str]:
        """Find functions related to the defective function"""
        pass
```

#### 4. Pattern Detector (Updated for MVP)
```python
class PatternDetector:
    def __init__(self):
        self.pattern_rules = self._load_pattern_rules()
    
    def detect_patterns(self, source_code: str, 
                       classification_hints: Dict[str, Any]) -> List[CodePattern]:
        """Detect relevant code patterns based on classification hints"""
        patterns = []
        likely_categories = classification_hints.get('likely_categories', [])
        
        for category in likely_categories:
            if category == 'null_pointer':
                patterns.extend(self._detect_null_check_patterns(source_code))
            elif category == 'memory_management':
                patterns.extend(self._detect_memory_patterns(source_code))
            elif category == 'buffer_overflow':
                patterns.extend(self._detect_buffer_patterns(source_code))
                
        return patterns
    
    def _detect_null_check_patterns(self, source_code: str) -> List[CodePattern]:
        """Detect null checking patterns"""
        patterns = []
        # Look for: if (ptr != NULL), if (ptr), assert(ptr), etc.
        return patterns
    
    def _detect_memory_patterns(self, source_code: str) -> List[CodePattern]:
        """Detect memory management patterns"""
        pass
    
    def _detect_buffer_patterns(self, source_code: str) -> List[CodePattern]:
        """Detect buffer-related patterns"""
        pass
```

#### 5. Syntax Highlighter
```python
class SyntaxHighlighter:
    def __init__(self):
        from pygments import highlight
        from pygments.lexers import get_lexer_by_name
        from pygments.formatters import HtmlFormatter
        
    def highlight_code(self, source_code: str, language: str, 
                      highlight_lines: List[int] = None) -> str:
        """Generate syntax-highlighted HTML code"""
        pass
    
    def highlight_defect_line(self, source_code: str, defect_line: int, 
                            context_start: int) -> str:
        """Highlight specific defect line within context"""
        pass
```

## Context Extraction Strategies

### Strategy Selection by Defect Hints (Updated for MVP)
```python
class ContextStrategy:
    def get_context_for_defect(self, defect: ParsedDefect) -> CodeContext:
        """Select context strategy based on classification hints"""
        hints = defect.classification_hints or {}
        likely_categories = hints.get('likely_categories', [])
        
        if 'null_pointer' in likely_categories:
            return self._null_pointer_context(defect)
        elif 'memory_management' in likely_categories:
            return self._memory_leak_context(defect)
        elif 'uninitialized' in likely_categories:
            return self._uninitialized_context(defect)
        elif 'buffer_overflow' in likely_categories:
            return self._buffer_context(defect)
        else:
            return self._default_context(defect)
    
    def _null_pointer_context(self, defect: ParsedDefect) -> CodeContext:
        """Extract context optimized for null pointer issues"""
        # Focus on: pointer declarations, null checks, dereferences
        pass
    
    def _memory_leak_context(self, defect: ParsedDefect) -> CodeContext:
        """Extract context optimized for memory management issues"""
        # Focus on: allocation/deallocation pairs, error paths, cleanup
        pass
    
    def _buffer_context(self, defect: ParsedDefect) -> CodeContext:
        """Extract context optimized for buffer overflow issues"""
        # Focus on: array bounds, buffer allocations, loop conditions
        pass
```

### Multi-File Context Handling
```python
class CrossFileAnalyzer:
    def analyze_cross_file_dependencies(self, defect: ParsedDefect) -> List[CodeContext]:
        """Analyze dependencies across multiple files"""
        contexts = []
        
        # 1. Find header file dependencies
        header_deps = self._find_header_dependencies(defect.file_path)
        
        # 2. Find function definitions in other files
        func_deps = self._find_function_definitions(defect.function_name)
        
        # 3. Find related test files
        test_deps = self._find_related_tests(defect.file_path)
        
        return contexts
```

## Implementation Plan

### Phase 1: Core File Reading (Week 1)
- Source file manager implementation
- Basic context extraction (function-level)
- Language detection and parsing foundation
- File encoding handling
- Integration with Issue Parser classification hints

### Phase 2: Language Parsing (Week 2)
- C/C++ parsing with Tree-sitter or libclang
- Variable and function analysis
- Cross-file dependency tracking
- Pattern detection framework with hint-based optimization

### Phase 3: Advanced Context (Week 3)
- Adaptive context size determination using hints
- Cross-file analysis implementation
- Code pattern detection with category-specific rules
- Syntax highlighting integration

### Phase 4: Optimization & Integration (Week 4)
- Performance optimization and caching
- Memory usage optimization
- Integration testing with LLM Fix Generator
- Error handling and edge cases

## Configuration

```yaml
# code_retriever_config.yaml
code_retriever:
  context:
    default_lines: 30
    max_lines: 100
    min_lines: 10
    include_function_signature: true
    include_variable_declarations: true
    
  languages:
    c:
      parser: "tree_sitter"
      extensions: [".c", ".h"]
      context_multiplier: 1.0
    cpp:
      parser: "tree_sitter" 
      extensions: [".cpp", ".hpp", ".cc", ".hh"]
      context_multiplier: 1.2
    python:
      parser: "ast"
      extensions: [".py"]
      context_multiplier: 0.8
      
  performance:
    enable_file_caching: true
    cache_size_mb: 256
    parallel_processing: true
    max_concurrent_files: 10
    
  patterns:
    enable_pattern_detection: true
    confidence_threshold: 0.7
    max_patterns_per_context: 5
    
  syntax_highlighting:
    enabled: true
    format: "html"
    highlight_defect_lines: true
    include_line_numbers: true
```

## Testing Strategy

### Unit Tests
- File reading and encoding detection
- Function boundary detection
- Variable extraction accuracy
- Pattern detection precision

### Integration Tests
- End-to-end context extraction
- Cross-file dependency analysis
- Large codebase performance
- Memory usage validation

### Language-Specific Tests
- C/C++ parsing accuracy
- Python AST analysis
- Java parsing capability
- Cross-language project handling

## Integration Points

### Upstream Dependencies
- Issue Parser (defect location information with classification hints)
- Project file system access
- Configuration system

### Downstream Consumers
- LLM Fix Generator (source code context for integrated analysis and patch generation)
- Verification system (code context for validation)
- Reporting system (context statistics and metrics)

## Success Metrics

- **Accuracy**: >98% correct function boundary detection
- **Coverage**: Extract meaningful context for >95% of defects
- **Performance**: <500ms average context extraction time
- **Completeness**: Include all relevant dependencies for >90% of cases
- **Adaptive Efficiency**: >15% improvement in context relevance using classification hints

## Language Support

### Tier 1 Support (Full Features)
- **C/C++**: Complete parsing, cross-file analysis, pattern detection
- **Python**: AST-based analysis, import tracking, pattern detection

### Tier 2 Support (Basic Features)  
- **Java**: Basic parsing, class-level context, import analysis
- **JavaScript**: Function-level context, require/import tracking

### Extension Framework
```python
class LanguageExtension:
    def get_function_bounds(self, source: str, line: int) -> Tuple[int, int]:
        pass
    
    def extract_variables(self, source: str) -> List[VariableInfo]:
        pass
    
    def find_dependencies(self, source: str) -> List[Dependency]:
        pass
```

## Risk Mitigation

### Technical Risks
- **Parsing Errors**: Fallback to simple line-based extraction
- **Large Files**: Streaming and chunked processing
- **Encoding Issues**: Robust encoding detection and fallbacks
- **Complex Dependencies**: Configurable depth limits

### Implementation Approach
- Start with C/C++ as primary target
- Incremental language support addition  
- Extensive testing with real-world codebases
- Performance monitoring and optimization throughout development 