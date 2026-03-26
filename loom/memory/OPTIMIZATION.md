# Memory System Optimization

## Changes

### 1. Tokenizer Abstraction
- Created `tokenizers.py` with pluggable implementations
- `EstimatorTokenizer`: Fast char-ratio (default, no deps)
- `TiktokenTokenizer`: Accurate tiktoken-based counting
- `create_tokenizer()`: Factory function

### 2. MemoryManager Enhancement
- Added `tokenizer` parameter to constructor
- Replaced `_estimate_tokens()` with `tokenizer.count()`
- More accurate token counting across L1→L2→L3 pipeline

## Usage

```python
from loom import MemoryManager
from loom.memory import create_tokenizer

# Default: fast estimation
memory = MemoryManager()

# Accurate tiktoken (requires: pip install tiktoken)
tokenizer = create_tokenizer("tiktoken", model="gpt-4")
memory = MemoryManager(tokenizer=tokenizer)
```

## Benefits

- **Accuracy**: Real token counts for budget management
- **Flexibility**: Swap tokenizers without code changes
- **Performance**: Choose speed vs accuracy tradeoff
- **Backward Compatible**: Defaults to estimator

## Next Steps

- [ ] Embedding layer for semantic retrieval
- [ ] Complete Context EMA scoring
- [ ] LLM-based memory compression
