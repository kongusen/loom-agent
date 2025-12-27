# Production Deployment

> **Problem-Oriented** - Learn to deploy loom-agent in production environments

## Deployment Preparation

### Environment Checklist

- [ ] Python 3.11+ installed
- [ ] Dependencies installed (`pip install loom-agent[all]`)
- [ ] Environment variables configured
- [ ] API Key set
- [ ] Tests passed

## Configuration Management

### Using Environment Variables

```bash
# Production environment .env.prod
OPENAI_API_KEY=sk-prod-...
OPENAI_BASE_URL=https://api.openai.com/v1
LOG_LEVEL=INFO
```

### Configuration File

```yaml
# config.prod.yaml
version: "1.0"
control:
  budget: 10000
  depth: 5
```

## Deployment Methods

### Method 1: Direct Deployment

```bash
# Activate virtual environment
source venv/bin/activate

# Load production configuration
export $(cat .env.prod | xargs)

# Start application
python main.py
```

### Method 2: Using Docker

```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
CMD ["python", "main.py"]
```

```bash
# Build and run
docker build -t loom-agent .
docker run -d --env-file .env.prod loom-agent
```

## Monitoring and Logging

### Configure Logging

```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
```

### Monitoring Metrics

- Token usage
- Response time
- Error rate
- System 2 activation count

## Best Practices

1. **Use environment variables**: Don't hardcode secrets
2. **Limit resources**: Set token budget and timeout
3. **Monitor logs**: Detect issues promptly
4. **Regular backups**: Save important data
5. **Gradual rollout**: Gradually switch traffic

## Related Documentation

- [Environment Setup](../configuration/environment-setup.md) - Environment configuration guide
- [Configuring LLM](../configuration/llm-providers.md) - LLM configuration

