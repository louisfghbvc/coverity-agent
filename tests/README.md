# Coverity Agent Tests

This directory contains comprehensive tests for the Coverity Agent pipeline.

## Test Structure

```
tests/
├── test_integration/           # End-to-end integration tests
│   ├── test_real_coverity_integration.py
│   ├── conftest.py
│   └── __init__.py
├── test_issue_parser/          # Issue Parser unit tests
│   ├── test_data_structures.py
│   ├── fixtures/               # Test data
│   ├── conftest.py
│   └── __init__.py
└── README.md
```

## Running Tests

### Run All Tests
```bash
# Run all tests with verbose output
pytest tests/ -v

# Run all tests with coverage
pytest tests/ --cov=src
```

### Run Integration Tests
```bash
# Run pytest integration tests
pytest tests/test_integration/ -v

# Run manual integration test (more detailed output)
python tests/test_integration/test_real_coverity_integration.py
```

### Run Unit Tests
```bash
# Run Issue Parser tests
pytest tests/test_issue_parser/ -v
```

## Integration Test Features

The integration test (`test_real_coverity_integration.py`) validates:

1. **Real Coverity Report Processing**: Uses actual report from production environment
2. **Issue Parser Functionality**: Parses and validates Coverity defects
3. **Code Retriever Integration**: Extracts source code context for defects
4. **End-to-End Workflow**: Complete pipeline from JSON report to code context

### Integration Test Modes

**PyTest Mode** (recommended for CI/CD):
```bash
pytest tests/test_integration/test_real_coverity_integration.py -v
```

**Manual Mode** (detailed output for debugging):
```bash
python tests/test_integration/test_real_coverity_integration.py
```

## Test Configuration

Integration tests use the following configuration:
- **Real Report Path**: `/home/scratch.louiliu_vlsi_1/work/nvtools_louiliu_2/nvtools/cad/cadlib/vector/coverity/libvector.so/report.json`
- **Max Defects to Test**: 5 per category
- **Minimum Success Rate**: 50%
- **Timeout**: 30 seconds

## Test Requirements

- Python 3.8+
- pytest
- All project dependencies installed in virtual environment

## Sample Output

Integration test successfully validates:
- ✅ Report validation and parsing
- ✅ Defect categorization and filtering  
- ✅ Source code context extraction
- ✅ Language detection (C/C++)
- ✅ Function boundary detection
- ✅ File encoding detection
- ✅ Performance requirements

Expected results:
- **Issue Categories**: ~6 different types (RESOURCE_LEAK, FORWARD_NULL, etc.)
- **Success Rate**: 100% for available source files
- **Processing Time**: <1 second for parsing, <100ms for context extraction
- **Context Lines**: 40-50 lines per defect with function boundaries 