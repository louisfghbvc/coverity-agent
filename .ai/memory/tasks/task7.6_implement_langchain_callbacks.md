---
id: 7.6
title: 'Implement LangChain Callbacks'
status: pending
priority: medium
feature: LLM Fix Generator - Monitoring
dependencies:
  - 7.5
assigned_agent: null
created_at: "2025-06-16T09:27:12Z"
started_at: null
completed_at: null
error_log: null
---

## Description

Create custom LangChain callbacks for token counting, cost tracking, performance monitoring, and streaming support with comprehensive observability.

## Details

### Core Callback Components

1. **TokenCountingCallback**
   - Accurate token usage tracking across all providers
   - Input/output token separation
   - Provider-specific token counting logic
   - Cumulative token usage statistics

2. **CostTrackingCallback**
   - Provider-specific cost calculation
   - Real-time cost monitoring and alerting
   - Cost optimization recommendations
   - Budget threshold management

3. **PerformanceCallback**
   - Response time measurement and tracking
   - Throughput monitoring (requests/minute)
   - Latency percentile analysis
   - Performance regression detection

4. **StreamingCallback**
   - Real-time response handling for streaming APIs
   - Chunk processing and aggregation
   - Streaming error detection and recovery
   - User experience optimization

5. **DefectAnalysisCallback**
   - Custom callback for defect analysis pipeline monitoring
   - Fix quality scoring and tracking
   - Success rate measurement
   - Defect-specific performance metrics

### Implementation Requirements

- **LangChain Integration**: Extend BaseCallbackHandler for all callbacks
- **Thread Safety**: Safe concurrent usage across multiple requests
- **Performance**: Minimal overhead on main processing pipeline
- **Configurability**: Flexible callback configuration and selection
- **Persistence**: Optional metric persistence for historical analysis
- **Alerting**: Configurable alerts on thresholds and anomalies

### File Structure

```
src/fix_generator/
└── callbacks.py             # LangChain callback implementations
```

### Callback Classes

1. **TokenCountingCallback(BaseCallbackHandler)**
   - Track tokens for all LLM calls
   - Provider-specific token counting
   - Real-time usage reporting
   - Token limit monitoring

2. **CostTrackingCallback(BaseCallbackHandler)**
   - Real-time cost calculation
   - Provider-specific pricing models
   - Cost alerts and budget management
   - Usage optimization insights

3. **PerformanceCallback(BaseCallbackHandler)**
   - Response time tracking
   - Throughput measurement
   - Performance analytics
   - Bottleneck identification

4. **StreamingCallback(BaseCallbackHandler)**
   - Streaming response processing
   - Chunk aggregation and validation
   - Real-time user feedback
   - Streaming error handling

5. **CompositeCallback(BaseCallbackHandler)**
   - Combine multiple callbacks
   - Coordinated callback execution
   - Error isolation between callbacks
   - Unified reporting interface

### Token Counting Implementation

```python
class TokenCountingCallback(BaseCallbackHandler):
    def __init__(self):
        self.total_tokens = 0
        self.input_tokens = 0
        self.output_tokens = 0
        self.provider_usage = {}
    
    def on_llm_start(self, serialized, prompts, **kwargs):
        # Track input tokens
        self.input_tokens += self._count_tokens(prompts)
    
    def on_llm_end(self, response, **kwargs):
        # Track output tokens and update totals
        output_tokens = self._count_response_tokens(response)
        self.output_tokens += output_tokens
        self.total_tokens += output_tokens
```

### Cost Tracking Implementation

```python
class CostTrackingCallback(BaseCallbackHandler):
    PRICING = {
        "nvidia_nim": {"input": 0.0002, "output": 0.0002},
        "openai": {"input": 0.03, "output": 0.06},
        "anthropic": {"input": 0.008, "output": 0.024}
    }
    
    def __init__(self):
        self.total_cost = 0.0
        self.provider_costs = {}
    
    def calculate_cost(self, provider, input_tokens, output_tokens):
        pricing = self.PRICING.get(provider, {"input": 0, "output": 0})
        return (input_tokens * pricing["input"] + 
                output_tokens * pricing["output"]) / 1000
```

### Performance Monitoring

```python
class PerformanceCallback(BaseCallbackHandler):
    def __init__(self):
        self.start_times = {}
        self.response_times = []
        self.throughput_tracker = ThroughputTracker()
    
    def on_llm_start(self, serialized, prompts, run_id, **kwargs):
        self.start_times[run_id] = time.time()
    
    def on_llm_end(self, response, run_id, **kwargs):
        if run_id in self.start_times:
            duration = time.time() - self.start_times[run_id]
            self.response_times.append(duration)
            self.throughput_tracker.record_completion()
```

### Streaming Support

```python
class StreamingCallback(BaseCallbackHandler):
    def __init__(self, on_token_callback=None):
        self.on_token_callback = on_token_callback
        self.streaming_buffer = []
    
    def on_llm_new_token(self, token, **kwargs):
        if self.on_token_callback:
            self.on_token_callback(token)
        self.streaming_buffer.append(token)
    
    def on_llm_end(self, response, **kwargs):
        # Process complete streaming response
        complete_response = "".join(self.streaming_buffer)
        self.streaming_buffer.clear()
```

## Test Strategy

### Unit Tests Required

1. **Callback Creation Tests**
   - All callback class instantiation
   - Callback configuration validation
   - BaseCallbackHandler inheritance verification
   - Thread safety initialization

2. **Token Counting Tests**
   - Token counting accuracy across providers
   - Input/output token separation
   - Cumulative usage tracking
   - Provider-specific counting logic

3. **Cost Tracking Tests**
   - Cost calculation accuracy
   - Provider-specific pricing application
   - Real-time cost updates
   - Budget threshold detection

4. **Performance Monitoring Tests**
   - Response time measurement accuracy
   - Throughput calculation validation
   - Performance metric aggregation
   - Anomaly detection functionality

5. **Streaming Tests**
   - Real-time token processing
   - Streaming response aggregation
   - Error handling during streaming
   - User callback integration

6. **Integration Tests**
   - Callback integration with LangChain chains
   - Multi-callback coordination
   - Real API endpoint monitoring
   - End-to-end observability validation

### Success Criteria

- Token counting provides accurate usage metrics for all providers
- Cost tracking calculates costs correctly with real-time updates
- Performance monitoring captures response times and throughput accurately
- Streaming callbacks process real-time responses without blocking
- All callbacks operate with minimal performance overhead (<50ms)
- Thread safety ensures correct operation under concurrent requests
- Integration with provider manager (Task 7.5) works seamlessly
- Comprehensive test coverage >95%
- Callback system provides actionable insights for optimization
- Documentation includes callback configuration and usage examples 