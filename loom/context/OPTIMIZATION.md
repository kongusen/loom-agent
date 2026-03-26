# Context Orchestrator Optimization

## Changes

### 1. EMA Score Update Fix
**Problem**: Sources without selected fragments had scores decay to 0

**Solution**:
- Gentle decay (10% of alpha) when source doesn't contribute
- Floor score at 0.1 to prevent complete elimination
- Boost based on avg relevance when source contributes

### 2. Tokenizer Integration
- Added optional `tokenizer` parameter
- Accurate system prompt token counting
- Falls back to estimation if tokenizer not provided

## Algorithm

```python
# EMA update per source:
if source_contributed:
    new_score = (1 - α) * old + α * avg_relevance
else:
    new_score = (1 - 0.1α) * old  # gentle decay
new_score = max(new_score, 0.1)  # floor
```

## Usage

```python
from loom import ContextOrchestrator
from loom.memory import create_tokenizer

# With accurate tokenizer
tokenizer = create_tokenizer("tiktoken")
orchestrator = ContextOrchestrator(
    context_window=128_000,
    adaptive_alpha=0.3,
    tokenizer=tokenizer
)
```

## Benefits

- Sources don't disappear after temporary low relevance
- More stable budget allocation over time
- Accurate token budget computation
