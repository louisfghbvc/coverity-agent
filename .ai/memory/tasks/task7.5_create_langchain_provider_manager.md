---
id: 7.5
title: 'Create LangChain Provider Manager'
status: pending
priority: critical
feature: LLM Fix Generator - Provider Management
dependencies:
  - 7.2
  - 7.4
assigned_agent: null
created_at: "2025-06-16T09:27:12Z"
started_at: null
completed_at: null
error_log: null
---

## Description

Implement ChatOpenAI configuration for NVIDIA NIM endpoints with multi-provider fallback system, streaming support, and unified provider interface.

## Details

### Core Provider Management Components

1. **NVIDIA NIM Provider**
   - ChatOpenAI configured with custom base_url for NIM endpoints
   - Authentication using NVIDIA NIM API keys
   - Model selection (Llama 3.3, Mistral, CodeLlama)
   - Streaming support with real-time response handling
   - NIM-specific parameter optimization

2. **Fallback Provider System**
   - Primary: NVIDIA NIM
   - Secondary: OpenAI (ChatOpenAI with standard endpoints)
   - Tertiary: Anthropic (ChatAnthropic)
   - Automatic provider switching on failures
   - Health checking and provider availability monitoring

3. **Unified Provider Interface**
   - Consistent API across all providers
   - Standardized parameter handling
   - Uniform error handling and reporting
   - Provider-agnostic response processing

4. **Streaming and Real-time Support**
   - LangChain streaming callbacks integration
   - Real-time response processing
   - Chunked response handling
   - Streaming error recovery

### Implementation Requirements

- **LangChain Integration**: Use ChatOpenAI and ChatAnthropic classes
- **Provider Abstraction**: Unified interface for all LLM providers
- **Failover Logic**: Automatic switching on provider failures
- **Health Monitoring**: Provider availability and performance tracking
- **Configuration**: Dynamic provider configuration from config management
- **Performance**: Optimized for low latency and high throughput

### File Structure

```
src/fix_generator/
└── langchain_manager.py     # LangChain provider management implementation
```

### Provider Classes

1. **LangChainProviderManager**
   - Main provider orchestration class
   - Provider selection and fallback logic
   - Health monitoring and performance tracking
   - Configuration integration with Task 7.2

2. **NIMProvider**
   - NVIDIA NIM-specific ChatOpenAI configuration
   - Custom base_url and authentication
   - NIM model parameter optimization
   - Streaming support implementation

3. **OpenAIProvider**
   - Standard OpenAI ChatOpenAI configuration
   - Fallback provider implementation
   - Standard OpenAI model support

4. **AnthropicProvider**
   - ChatAnthropic configuration for Claude models
   - Final fallback implementation
   - Anthropic-specific parameter handling

5. **ProviderHealthMonitor**
   - Real-time provider availability checking
   - Performance metrics collection
   - Failure detection and reporting
   - Provider ranking based on performance

### Provider Configuration

```python
# NVIDIA NIM Provider
nim_provider = ChatOpenAI(
    base_url="https://integrate.api.nvidia.com/v1",
    api_key=os.getenv("NVIDIA_NIM_API_KEY"),
    model="nvidia/llama-3.3-nemotron-super-49b-v1",
    temperature=0.6,
    max_tokens=4096,
    streaming=True,
    callbacks=[token_counting_callback, cost_tracking_callback]
)

# OpenAI Fallback Provider
openai_provider = ChatOpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
    model="gpt-4",
    temperature=0.1,
    max_tokens=2000,
    callbacks=[token_counting_callback, cost_tracking_callback]
)

# Anthropic Fallback Provider
anthropic_provider = ChatAnthropic(
    api_key=os.getenv("ANTHROPIC_API_KEY"),
    model="claude-3-sonnet-20240229",
    temperature=0.1,
    max_tokens=2000,
    callbacks=[token_counting_callback, cost_tracking_callback]
)
```

### Failover Logic

1. **Provider Priority**
   - Primary: NVIDIA NIM (lowest cost, highest performance)
   - Secondary: OpenAI (reliable fallback)
   - Tertiary: Anthropic (final fallback)

2. **Failure Detection**
   - API authentication failures
   - Network timeout errors
   - Rate limiting responses
   - Model unavailability

3. **Automatic Switching**
   - Immediate failover on critical errors
   - Gradual degradation on performance issues
   - Provider recovery detection
   - Load balancing when multiple providers available

### Streaming Implementation

```python
# Streaming response handling
async def stream_generate(self, prompt: str) -> AsyncIterator[str]:
    try:
        async for chunk in self.current_provider.astream(prompt):
            yield chunk.content
    except Exception as e:
        # Fallback to next provider
        await self._switch_provider()
        async for chunk in self.current_provider.astream(prompt):
            yield chunk.content
```

## Test Strategy

### Unit Tests Required

1. **Provider Configuration Tests**
   - NVIDIA NIM ChatOpenAI configuration
   - OpenAI provider setup with standard endpoints
   - Anthropic provider configuration
   - Provider parameter validation

2. **Failover Logic Tests**
   - Automatic provider switching on failures
   - Provider health checking
   - Recovery detection and provider restoration
   - Multi-level fallback scenarios

3. **Streaming Tests**
   - Real-time response streaming
   - Streaming error handling
   - Chunked response processing
   - Streaming callback integration

4. **Performance Tests**
   - Provider response time comparison
   - Concurrent request handling
   - Load balancing effectiveness
   - Failure recovery time measurement

5. **Integration Tests**
   - Integration with configuration management (Task 7.2)
   - Integration with output parsers (Task 7.4)
   - End-to-end provider workflow
   - Real API endpoint testing

### Success Criteria

- NVIDIA NIM provider connects successfully with custom base_url
- Automatic failover works reliably on provider failures
- Streaming responses process in real-time without blocking
- Provider health monitoring accurately detects availability
- Configuration integration loads providers dynamically
- Performance meets latency requirements (<2s response time)
- Error handling provides clear provider-specific diagnostics
- Comprehensive test coverage >95%
- All three providers (NIM, OpenAI, Anthropic) work correctly
- Documentation includes provider setup and troubleshooting guides 