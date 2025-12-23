# Frequently Asked Questions

### Can I use Loom without an LLM?
Yes, technically. `Node` logic can be purely deterministic python code. However, `AgentNode` is designed for LLMs.

### How do I stop infinite loops?
1.  Set `max_iterations` in your Agent.
2.  Use the `BudgetInterceptor` to kill tasks exceeding token limits.

### How does Metabolic Memory differ from RAG?
RAG acts like a search engine (passive). Metabolic Memory acts like a digestive system (active), compressing and integrating information into a project state over time.

### Is Loom production-ready?
The core protocols are stable. The built-in nodes are in Beta. We recommend thorough testing of your agents before deploying.
