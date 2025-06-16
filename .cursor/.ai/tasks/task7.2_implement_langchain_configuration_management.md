---
id: 7.2
title: 'Implement LangChain Configuration Management'
status: pending
priority: critical
feature: LLM Fix Generator - Configuration
dependencies:
  - 7.1
assigned_agent: null
created_at: "2025-06-16T09:27:12Z"
started_at: null
completed_at: null
error_log: null
---

## Description

Set up comprehensive configuration system with dotenv integration, environment variable validation, and YAML-based LangChain provider configurations for NVIDIA NIM, OpenAI, and Anthropic.

## Details

### Core Configuration Components

1. **LangChain Provider Configuration**
   - ChatOpenAI configuration for NVIDIA NIM endpoints with custom base_url
   - ChatAnthropic configuration for fallback scenarios
   - Provider-specific parameter management (temperature, max_tokens, streaming)
   - Dynamic provider switching and fallback mechanisms

2. **Environment Variable Management**
   - Dotenv integration with python-dotenv for secure token loading
   - Environment variable validation and type checking
   - Secure API key management with masked logging
   - Configuration drift detection and validation

3. **YAML Configuration Integration**
   - YAML-based configuration files with environment variable resolution
   - Template expansion for ${VARIABLE_NAME} patterns
   - Configuration validation and schema checking
   - Multiple configuration file support (dev, staging, prod)

4. **LangChain-Specific Settings**
   - Callback configurations for monitoring and cost tracking
   - Prompt template configurations with dynamic variable binding
   - Output parser configurations with retry mechanisms
   - Provider-specific optimization settings

### Implementation Requirements

- **Secure Token Handling**: API keys loaded securely without exposure in logs
- **Configuration Validation**: Runtime validation of all configuration parameters
- **Multi-Environment Support**: Different configs for development, testing, production
- **Hot Reload**: Configuration changes without application restart (where safe)
- **Fallback Support**: Graceful degradation when primary providers unavailable
- **Schema Validation**: Comprehensive validation of YAML configuration structure

### File Structure

```
src/fix_generator/
└── config.py                # Configuration management classes

# Configuration files
config/
├── llm_fix_generator_config.yaml    # Main configuration
├── dev_config.yaml                  # Development overrides
└── prod_config.yaml                 # Production settings

# Environment configuration
.env                          # Environment variables
.env.example                  # Example environment template
```

### Configuration Classes

1. **LLMFixGeneratorConfig**
   - Main configuration class with provider management
   - Environment variable expansion and validation
   - Provider selection and fallback logic

2. **NIMProviderConfig**
   - NVIDIA NIM-specific settings
   - Custom base_url and model configuration
   - NIM-specific optimization parameters

3. **LangChainConfig**
   - LangChain framework configuration
   - Callback system configuration
   - Prompt template and parser settings

4. **ProviderManager**
   - Dynamic provider instantiation
   - Fallback provider selection
   - Provider health checking and monitoring

### Environment Variables

```bash
# NVIDIA NIM Configuration
NVIDIA_NIM_API_KEY=your_nim_api_token_here
NVIDIA_NIM_BASE_URL=https://integrate.api.nvidia.com/v1
NVIDIA_NIM_MODEL=nvidia/llama-3.3-nemotron-super-49b-v1
NVIDIA_NIM_MAX_TOKENS=4096
NVIDIA_NIM_TEMPERATURE=0.6
NVIDIA_NIM_TOP_P=0.95
NVIDIA_NIM_FREQUENCY_PENALTY=0.0
NVIDIA_NIM_PRESENCE_PENALTY=0.0
NVIDIA_NIM_STREAMING=true
NVIDIA_NIM_TIMEOUT=30

# Fallback Providers
OPENAI_API_KEY=your_openai_key_here
ANTHROPIC_API_KEY=your_anthropic_key_here

# Pipeline Configuration
DEFECT_ANALYSIS_CACHE_DURATION=24h
ENABLE_MULTIPLE_CANDIDATES=true
NUM_FIX_CANDIDATES=3
CONFIDENCE_THRESHOLD=0.7
```

## Test Strategy

### Unit Tests Required

1. **Configuration Loading Tests**
   - Environment variable loading with dotenv
   - YAML configuration file parsing
   - Environment variable expansion in YAML
   - Missing configuration file handling

2. **Validation Tests**
   - API key validation (format and presence)
   - Configuration schema validation
   - Invalid parameter handling
   - Required field validation

3. **Provider Configuration Tests**
   - NVIDIA NIM provider configuration
   - OpenAI/Anthropic fallback provider setup
   - Provider parameter validation
   - Custom base_url handling

4. **Security Tests**
   - API key masking in logs
   - Secure token storage
   - Configuration file permissions
   - Environment variable sanitization

5. **Integration Tests**
   - LangChain provider instantiation
   - Provider switching mechanisms
   - Configuration hot reload
   - Multi-environment configuration

### Success Criteria

- Environment variables load correctly from .env files
- YAML configuration parses with proper variable expansion
- All LangChain providers instantiate with correct parameters
- API keys are securely managed without exposure in logs
- Configuration validation catches invalid settings
- Provider fallback mechanisms work reliably
- Multiple configuration environments supported
- Comprehensive test coverage >95%
- Documentation includes setup and configuration examples 