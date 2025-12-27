# 生产环境部署

> **问题导向** - 学会在生产环境中部署 loom-agent

## 部署准备

### 环境检查清单

- [ ] Python 3.11+ 已安装
- [ ] 依赖已安装（`pip install loom-agent[all]`）
- [ ] 环境变量已配置
- [ ] API Key 已设置
- [ ] 测试通过

## 配置管理

### 使用环境变量

```bash
# 生产环境 .env.prod
OPENAI_API_KEY=sk-prod-...
OPENAI_BASE_URL=https://api.openai.com/v1
LOG_LEVEL=INFO
```

### 配置文件

```yaml
# config.prod.yaml
version: "1.0"
control:
  budget: 10000
  depth: 5
```

## 部署方式

### 方式 1：直接部署

```bash
# 激活虚拟环境
source venv/bin/activate

# 加载生产配置
export $(cat .env.prod | xargs)

# 启动应用
python main.py
```

### 方式 2：使用 Docker

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
# 构建和运行
docker build -t loom-agent .
docker run -d --env-file .env.prod loom-agent
```

## 监控和日志

### 配置日志

```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
```

### 监控指标

- Token 使用量
- 响应时间
- 错误率
- System 2 启动次数

## 最佳实践

1. **使用环境变量**：不要硬编码密钥
2. **限制资源**：设置 Token 预算和超时
3. **监控日志**：及时发现问题
4. **定期备份**：保存重要数据
5. **灰度发布**：逐步切换流量

## 相关文档

- [环境配置](../configuration/environment-setup.md) - 环境配置指南
- [配置 LLM](../configuration/llm-providers.md) - LLM 配置
