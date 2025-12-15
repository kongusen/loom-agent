# Loom Agent 主流 LLM 支持 - 架构总结

## 核心设计理念

**"支持主流 LLM，让用户通过简单配置即可使用"**

- 主流 LLM 提供商直接支持（无需去 examples 找示例）
- 支持两种处理方式：OpenAI 兼容格式（统一处理）+ 非兼容格式（专门适配）
- 极简配置：一行代码即可使用
- 灵活扩展：支持自定义 base_url，适配任何 OpenAI 兼容服务

---

## 架构设计

### 1. 分层架构

```
用户代码（SimpleAgent）
    ↓
UnifiedLLM（统一接口）
    ↓
OpenAI SDK（兼容层）
    ↓
各种 LLM 提供商（OpenAI, DeepSeek, Qwen, 自定义...）
```

### 2. 提供商分类

#### OpenAI 兼容提供商（使用 UnifiedLLM）

**已内置支持**：
- OpenAI (原生)
- DeepSeek (深度求索) - 国产
- Qwen/通义千问 (阿里) - 国产
- Kimi/月之暗面 - 国产
- 智谱/GLM - 国产
- 豆包 (字节跳动) - 国产
- 零一万物 Yi - 国产
- **custom** - 任何 OpenAI 兼容服务

**特点**：
- 使用 `openai` SDK（只需 `pip install openai`）
- 通过配置 `base_url` 区分不同提供商
- 统一的 API 接口

#### 非兼容提供商（使用专门适配器）

**计划支持**：
- Anthropic Claude（使用 Anthropic SDK）
- Google Gemini（使用 Google SDK）

---

## 使用方式

### 方式 1：极简配置（推荐）

```python
import loom

agent = loom.agent(
    name="assistant",
    llm="deepseek",      # 提供商名称
    api_key="sk-..."     # API 密钥
)
```

**支持的提供商名称**：
- `"openai"` - OpenAI
- `"deepseek"` - DeepSeek
- `"qwen"` - 通义千问
- `"kimi"` - Kimi
- `"zhipu"` - 智谱 GLM
- `"doubao"` - 豆包
- `"yi"` - 零一万物
- `"custom"` - 自定义服务

### 方式 2：详细配置

```python
agent = loom.agent(
    name="assistant",
    llm="deepseek",
    api_key="sk-...",
    model="deepseek-chat",   # 指定模型
    temperature=0.7,          # 温度
    max_tokens=2000,          # 最大 tokens
    top_p=0.9                 # Top-p 采样
)
```

### 方式 3：自定义 base_url

```python
# 使用代理
agent = loom.agent(
    name="assistant",
    llm="openai",
    api_key="sk-...",
    base_url="https://your-proxy.com/v1"
)

# 使用完全自定义的服务
agent = loom.agent(
    name="assistant",
    llm="custom",
    api_key="your-key",
    base_url="https://your-service.com/v1",
    model="your-model"
)
```

### 方式 4：字典配置

```python
agent = loom.agent(
    name="assistant",
    llm={
        "provider": "qwen",
        "api_key": "sk-...",
        "model": "qwen-turbo",
        "base_url": "https://proxy.com/v1",  # 可选
        "temperature": 0.7
    }
)
```

### 方式 5：LLM 实例

```python
from loom.builtin import UnifiedLLM

llm = UnifiedLLM(
    provider="openai",
    api_key="sk-...",
    model="gpt-4"
)

agent = loom.agent(name="assistant", llm=llm)
```

---

## 核心组件

### 1. UnifiedLLM 类

**位置**：`loom/builtin/llms/unified.py`

**功能**：统一处理所有 OpenAI 兼容的提供商

**特点**：
- 使用 OpenAI SDK
- 支持配置不同的 `base_url`
- 支持流式输出
- 支持工具调用
- 支持 JSON 模式

**示例**：
```python
from loom.builtin import UnifiedLLM

llm = UnifiedLLM(
    provider="deepseek",
    api_key="sk-...",
    model="deepseek-chat",
    base_url=None,  # 使用默认 URL
    temperature=0.7
)
```

### 2. 提供商配置

**位置**：`loom/builtin/llms/providers.py`

**内容**：
```python
OPENAI_COMPATIBLE_PROVIDERS = {
    "openai": {
        "name": "OpenAI",
        "base_url": "https://api.openai.com/v1",
        "default_model": "gpt-4",
        "models": ["gpt-4", "gpt-4-turbo", ...],
    },
    "deepseek": {
        "name": "DeepSeek",
        "base_url": "https://api.deepseek.com/v1",
        "default_model": "deepseek-chat",
        "models": ["deepseek-chat", "deepseek-coder"],
    },
    "custom": {
        "name": "自定义 OpenAI 兼容服务",
        "base_url": None,  # 必须由用户提供
        "default_model": "gpt-3.5-turbo",
        "models": [],
    },
    # ... 其他提供商
}
```

**扩展方式**：添加新的提供商配置即可

### 3. 便捷别名

**位置**：`loom/builtin/llms/__init__.py`

**提供**：
```python
from loom.builtin import (
    UnifiedLLM,      # 统一 LLM
    OpenAILLM,       # OpenAI 别名
    DeepSeekLLM,     # DeepSeek 别名
    QwenLLM,         # Qwen 别名
    KimiLLM,         # Kimi 别名
    ZhipuLLM,        # 智谱 别名
    DoubaoLLM,       # 豆包 别名
    YiLLM,           # 零一万物 别名
)
```

**用途**：提供更简洁的 API

**示例**：
```python
from loom.builtin import DeepSeekLLM

llm = DeepSeekLLM(api_key="sk-...", model="deepseek-chat")
```

### 4. SimpleAgent 增强

**增强点**：
1. 支持字符串配置 LLM（提供商名称）
2. 支持字典配置 LLM
3. 支持 `base_url` 参数
4. 自动实例化 `UnifiedLLM`

**签名**：
```python
def __init__(
    self,
    name: str,
    llm: Union[str, Dict[str, Any], BaseLLM],
    api_key: Optional[str] = None,
    model: Optional[str] = None,
    base_url: Optional[str] = None,  # 新增
    tools: Optional[List[BaseTool]] = None,
    system_prompt: Optional[str] = None,
    ...
    **llm_kwargs: Any,  # 其他 LLM 参数
)
```

---

## 依赖管理

### pyproject.toml

```toml
[tool.poetry.dependencies]
python = "^3.11"
pydantic = "^2.5.0"

# LLM 支持（可选）
openai = {version = "^1.6.0", optional = true}
anthropic = {version = "^0.7.0", optional = true}

[tool.poetry.extras]
llm = ["openai"]           # 支持主流 LLM
anthropic = ["anthropic"]  # 支持 Anthropic
all = ["openai", "anthropic"]
```

### 安装方式

```bash
# 基础安装（只有核心框架）
pip install loom-agent

# 带 LLM 支持（推荐）
pip install "loom-agent[llm]"

# 完整安装
pip install "loom-agent[all]"
```

---

## 文件结构

```
loom/builtin/llms/
├── __init__.py          # 导出所有 LLM 类和别名
├── unified.py           # UnifiedLLM 统一 LLM 类
├── providers.py         # 提供商配置
└── anthropic.py         # (待实现) Anthropic 适配器

loom/agents/
└── simple.py            # SimpleAgent 增强，支持极简配置

examples/
├── integrations/
│   └── compression.py   # 压缩器示例（保留）
└── skills/              # 预设 Skills（保留）

文档/
├── LLM_SUPPORT.md       # 主流 LLM 支持文档
└── CUSTOM_BASEURL.md    # 自定义 base_url 文档
```

---

## 使用示例

### 示例 1：OpenAI

```python
agent = loom.agent(
    name="assistant",
    llm="openai",
    api_key="sk-...",
    model="gpt-4"
)
```

### 示例 2：DeepSeek（国产）

```python
agent = loom.agent(
    name="coder",
    llm="deepseek",
    api_key="sk-...",
    model="deepseek-coder"
)
```

### 示例 3：通义千问（阿里）

```python
agent = loom.agent(
    name="assistant",
    llm="qwen",
    api_key="sk-...",
    model="qwen-max"
)
```

### 示例 4：使用代理

```python
agent = loom.agent(
    name="assistant",
    llm="openai",
    api_key="sk-...",
    base_url="https://api.openai-proxy.com/v1"
)
```

### 示例 5：自建服务（vLLM）

```python
agent = loom.agent(
    name="assistant",
    llm="custom",
    api_key="EMPTY",
    base_url="http://localhost:8000/v1",
    model="Qwen/Qwen2-7B-Instruct"
)
```

### 示例 6：多 Agent 协作

```python
from loom.patterns import Crew

# 研究员使用 DeepSeek（性价比）
researcher = loom.agent(
    name="researcher",
    llm="deepseek",
    api_key="sk-..."
)

# 撰写员使用 GPT-4（质量）
writer = loom.agent(
    name="writer",
    llm="openai",
    api_key="sk-...",
    model="gpt-4"
)

crew = Crew(agents=[researcher, writer], mode="sequential")
```

---

## 优势

### 1. 极简使用

**之前（方案 A）**：
```python
from examples.integrations.openai_llm import OpenAILLM

llm = OpenAILLM(api_key="...")
agent = loom.agent(name="assistant", llm=llm)
```

**现在**：
```python
agent = loom.agent(
    name="assistant",
    llm="openai",
    api_key="..."
)
```

### 2. 主流支持

- 内置支持 8 个主流 LLM 提供商
- 覆盖国内外主流模型
- 国产模型全覆盖（DeepSeek, Qwen, Kimi, 智谱, 豆包, 零一万物）

### 3. 灵活扩展

- 支持自定义 `base_url`
- 支持任何 OpenAI 兼容服务
- 易于添加新提供商

### 4. 统一接口

- 所有提供商使用相同的 API
- 切换提供商只需改一个参数
- 降低学习成本

### 5. 生产就绪

- 支持流式输出
- 支持工具调用
- 支持 JSON 模式
- 完善的错误处理

---

## 扩展指南

### 添加新的 OpenAI 兼容提供商

**步骤 1**：在 `providers.py` 中添加配置

```python
"new_provider": {
    "name": "New Provider",
    "base_url": "https://api.newprovider.com/v1",
    "default_model": "model-name",
    "models": ["model-1", "model-2"],
    "description": "描述"
}
```

**步骤 2**：（可选）添加便捷别名

```python
class NewProviderLLM(UnifiedLLM):
    def __init__(self, api_key: str, **kwargs):
        super().__init__(provider="new_provider", api_key=api_key, **kwargs)
```

**步骤 3**：使用

```python
agent = loom.agent(
    name="assistant",
    llm="new_provider",
    api_key="..."
)
```

### 添加非兼容提供商

**步骤 1**：实现 `BaseLLM` Protocol

```python
class CustomLLM:
    @property
    def model_name(self) -> str:
        return "custom-model"

    async def stream(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        **kwargs: Any
    ) -> AsyncGenerator[Dict[str, Any], None]:
        # 实现流式生成逻辑
        yield {"type": "content_delta", "content": "..."}
        yield {"type": "finish", "finish_reason": "stop"}
```

**步骤 2**：使用

```python
llm = CustomLLM(...)
agent = loom.agent(name="assistant", llm=llm)
```

---

## 与方案 A 的对比

| 方面 | 方案 A（激进重构） | 当前方案（平衡方案） |
|------|-------------------|---------------------|
| **核心依赖** | Python + Pydantic | Python + Pydantic |
| **LLM 支持** | 移到 examples，用户自己集成 | 内置支持，开箱即用 |
| **使用复杂度** | 需要从 examples 导入 | 一行代码配置 |
| **灵活性** | 完全自由 | 平衡易用性和灵活性 |
| **适用场景** | 高度定制需求 | 主流使用场景 |

**结论**：当前方案在保持核心简洁的同时，提供了主流 LLM 的开箱即用支持，更符合用户需求。

---

## 总结

1. **支持主流 LLM**：内置 8 个主流提供商，覆盖国内外
2. **极简配置**：一行代码即可使用
3. **灵活扩展**：支持自定义 base_url 和任何 OpenAI 兼容服务
4. **统一接口**：所有提供商使用相同的 API
5. **生产就绪**：完善的功能和错误处理

这个架构完美实现了："**对于主流 LLM，用户可以直接通过简单配置即可使用**"的目标。
