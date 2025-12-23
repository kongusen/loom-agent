# Security & Safety

Running agents, especially those with shell access or free-form APIs, carries risks.

## Prompt Injection
Agents can be tricked by malicious input.

### Mitigation
1.  **Delimiters**: Wrap user input in XML tags.
    ```python
    prompt = f"""
    Analyze the following text inside <user_input> tags:
    <user_input>{sanitized_input}</user_input>
    """
    ```
2.  **Output Validation**: Use validators to ensure the agent doesn't output forbidden strings.

## Tool Sandboxing
Never give an agent root access or unrestricted file system access.

### Docker Sandbox
Run sensitive tools inside a container.
```python
class DockerTool(ToolNode):
    async def process(self, event):
        # Run command in isolated container
        cmd = f"docker run --rm alpine {event.data['cmd']}"
        ...
```

## Secrets Management
- **Never** put API keys in code or prompt templates.
- **Use Environment Variables**: `os.getenv("API_KEY")`.
- **Masking**: Ensure logging libraries mask known secrets.
