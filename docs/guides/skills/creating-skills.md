# 创建 Skills

**版本**: v0.1.6
**难度**: 中级

学习如何创建自定义 Skills，为你的 Agent 扩展专业能力。

---

## 📋 目录

1. [Skills 概述](#skills-概述)
2. [目录结构](#目录结构)
3. [三层渐进式披露](#三层渐进式披露)
4. [创建方式](#创建方式)
5. [完整示例](#完整示例)
6. [最佳实践](#最佳实践)
7. [测试与验证](#测试与验证)
8. [常见问题](#常见问题)

---

## Skills 概述

### 什么是 Skill？

Skill 是 Agent 可以学习和使用的**专业能力模块**，特点：

- **模块化**: 独立的能力单元，可组合
- **可扩展**: 无需修改 Agent 核心代码
- **零侵入**: 通过系统提示自动集成
- **按需加载**: 三层渐进式披露，最小化上下文

### 为什么需要 Skills？

```python
# ❌ 传统方式：将所有文档塞入系统提示
agent = loom.agent(
    name="agent",
    llm=llm,
    system_prompt="""
    你是一个助手。

    # PDF 分析
    使用 PyPDF2 提取文本...（1000+ tokens）

    # Web 研究
    使用 requests 抓取网页...（1000+ tokens）

    # 数据处理
    使用 pandas 处理数据...（1000+ tokens）

    总计：3000+ tokens，且大部分任务用不到
    """
)

# ✅ Skills 方式：索引 + 按需加载
agent = loom.agent(
    name="agent",
    llm=llm,
    enable_skills=True,
    skills_dir="./skills"
)
# 系统提示只包含索引（~150 tokens）
# Agent 需要时自动读取详细文档
```

**优势**：
- 上下文使用量从 3000+ tokens → 150 tokens（20x 减少）
- Agent 可以按需加载详细信息
- 更容易维护和共享

---

## 目录结构

### 标准 Skill 目录

```
skills/
  my_skill/                # Skill 名称（唯一标识）
    skill.yaml             # 元数据 + 快速指南（必需）
    SKILL.md              # 详细文档（推荐）
    resources/            # 附加资源（可选）
      examples.json
      templates/
        template1.txt
      data/
        sample.csv
```

### 文件说明

| 文件 | 必需性 | 大小 | 用途 |
|------|--------|------|------|
| `skill.yaml` | ✅ 必需 | ~50 tokens | 元数据 + 快速指南，用于索引 |
| `SKILL.md` | 推荐 | ~500-2000 tokens | 详细文档，按需加载 |
| `resources/` | 可选 | 任意 | 示例、模板、数据文件 |

---

## 三层渐进式披露

Skills 系统采用**三层渐进式披露**架构，最小化上下文使用：

### 第一层：索引（默认加载）

**内容**: 元数据 + 快速指南
**大小**: ~50 tokens/skill
**位置**: 系统提示
**用途**: Agent 快速浏览可用 Skills

```
## Analysis

- **pdf_analyzer**: Analyze and extract information from PDF documents
  💡 Quick: Use PyPDF2 or pdfplumber to extract text, tables, and metadata
  📄 Details: `cat skills/pdf_analyzer/SKILL.md`
  📦 Resources: `ls skills/pdf_analyzer/resources/`
```

### 第二层：详细文档（按需加载）

**内容**: 完整使用说明、示例代码、最佳实践
**大小**: ~500-2000 tokens
**位置**: `SKILL.md` 文件
**用途**: Agent 需要详细信息时读取

Agent 会自动使用 Bash 工具：
```bash
cat skills/pdf_analyzer/SKILL.md
```

### 第三层：资源文件（按需访问）

**内容**: 示例数据、模板、配置文件
**大小**: 任意
**位置**: `resources/` 目录
**用途**: Agent 需要具体资源时访问

Agent 会自动使用 Bash 工具：
```bash
ls skills/pdf_analyzer/resources/
cat skills/pdf_analyzer/resources/examples.json
```

### 上下文使用对比

| 任务 | 传统方式 | Skills 方式 | 节省 |
|------|----------|-------------|------|
| 列出可用能力 | 3000 tokens | 150 tokens | 20x |
| 使用 1 个能力 | 3000 tokens | 150 + 500 = 650 tokens | 4.6x |
| 使用 2 个能力 | 3000 tokens | 150 + 500 + 500 = 1150 tokens | 2.6x |

---

## 创建方式

### 方式 1：手动创建（推荐学习）

适合理解 Skills 结构，完全控制细节。

#### 步骤 1：创建目录

```bash
mkdir -p skills/my_skill/resources
```

#### 步骤 2：编写 skill.yaml

`skills/my_skill/skill.yaml`：

```yaml
metadata:
  name: my_skill                    # 唯一标识（必需）
  description: Short description    # 简短描述（必需）
  category: general                 # 分类（必需）
  version: 1.0.0                   # 版本号
  author: Your Name                # 作者
  tags:                            # 标签（用于搜索）
    - tag1
    - tag2
  dependencies: []                 # 依赖的其他 Skills
  enabled: true                    # 是否启用

quick_guide: One-sentence usage guide (~200 tokens max)
```

**字段说明**：

- `name`: Skill 唯一标识，必须与目录名一致
- `description`: 1-2 句话简短描述（~50 tokens）
- `category`: 分类（tools, analysis, communication, etc.）
- `quick_guide`: 快速使用指南（~200 tokens）
- `tags`: 标签列表，方便搜索
- `dependencies`: 依赖的其他 Skills（如果有）

#### 步骤 3：编写 SKILL.md

`skills/my_skill/SKILL.md`：

```markdown
# My Skill

Detailed description of what this skill does.

## Overview

Explain the skill's purpose, use cases, and capabilities.

## Usage

### Basic Usage

\`\`\`python
# Example code
import library

def example_function():
    pass
\`\`\`

### Advanced Usage

\`\`\`python
# More complex examples
\`\`\`

## Examples

See `resources/examples.json` for more examples.

## Dependencies

- library1: `pip install library1`
- library2: `pip install library2`

## Notes

- Important considerations
- Limitations
- Best practices
```

**内容建议**：

- **Overview**: 能力概述和使用场景
- **Usage**: 具体使用方法和代码示例
- **Examples**: 完整示例或指向 resources/
- **Dependencies**: Python 包依赖
- **Notes**: 注意事项和最佳实践

#### 步骤 4：添加资源文件（可选）

`skills/my_skill/resources/examples.json`：

```json
{
  "basic_example": {
    "description": "Basic usage",
    "code": "...",
    "expected_output": "..."
  },
  "advanced_example": {
    "description": "Advanced usage",
    "code": "...",
    "expected_output": "..."
  }
}
```

#### 步骤 5：使用 Skill

```python
import loom
from loom.builtin import OpenAILLM

agent = loom.agent(
    name="agent",
    llm=OpenAILLM(api_key="..."),
    enable_skills=True,
    skills_dir="./skills"
)

# Skill 会自动加载到系统提示（第一层）
# Agent 需要时会自动读取 SKILL.md（第二层）
# Agent 需要时会自动访问 resources/（第三层）

response = await agent.run(Message(
    role="user",
    content="使用 my_skill 完成任务"
))
```

---

### 方式 2：程序化创建

适合批量创建或集成到工具中。

```python
import loom
from loom.builtin import OpenAILLM

agent = loom.agent(
    name="agent",
    llm=OpenAILLM(api_key="..."),
    enable_skills=True,
    skills_dir="./skills"
)

# 创建新 Skill
skill = agent.create_skill(
    name="my_skill",
    description="Short description of the skill",
    category="tools",
    quick_guide="One-sentence usage guide",
    version="1.0.0",
    author="Your Name",
    tags=["tag1", "tag2"],
    detailed_content="""# My Skill

Detailed documentation goes here...

## Usage

Examples and instructions...
"""
)

print(f"Created: {skill}")
# Output: Skill(name='my_skill', category='tools', enabled=True)
```

**自动创建的文件**：
- `skills/my_skill/skill.yaml` - 元数据
- `skills/my_skill/SKILL.md` - 详细文档
- `skills/my_skill/resources/` - 空目录

**手动补充**：
- 编辑 `SKILL.md` 添加更详细的文档
- 在 `resources/` 添加示例、模板等

---

## 完整示例

### 示例 1：PDF 分析 Skill

**目录结构**：
```
skills/pdf_analyzer/
  skill.yaml
  SKILL.md
  resources/
    examples.json
```

**skill.yaml**：
```yaml
metadata:
  name: pdf_analyzer
  description: Analyze and extract information from PDF documents
  category: analysis
  version: 1.0.0
  author: Loom Team
  tags:
    - pdf
    - document
    - analysis
    - extraction
  dependencies: []
  enabled: true

quick_guide: Use PyPDF2 or pdfplumber to extract text, tables, and metadata from PDF files. Check resources/examples.json for common patterns.
```

**SKILL.md**（简化版）：
```markdown
# PDF Analyzer

Analyze and extract information from PDF documents.

## Overview

This skill enables PDF document analysis through:
- Text extraction
- Table extraction
- Metadata extraction
- Page-by-page processing

## Usage

### Text Extraction

\`\`\`python
import PyPDF2

def extract_text(pdf_path: str) -> str:
    with open(pdf_path, 'rb') as f:
        reader = PyPDF2.PdfReader(f)
        text = ""
        for page in reader.pages:
            text += page.extract_text()
    return text
\`\`\`

### Table Extraction

\`\`\`python
import pdfplumber

def extract_tables(pdf_path: str) -> list:
    tables = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            tables.extend(page.extract_tables())
    return tables
\`\`\`

## Examples

See `resources/examples.json` for complete examples.

## Dependencies

- PyPDF2: `pip install PyPDF2`
- pdfplumber: `pip install pdfplumber`

## Notes

- For OCR, use `pytesseract` with `pdf2image`
- Large PDFs should be processed in chunks
```

**resources/examples.json**：
```json
{
  "basic_extraction": {
    "description": "Extract text from simple PDF",
    "code": "extract_text('document.pdf')",
    "use_case": "Simple text documents"
  },
  "table_extraction": {
    "description": "Extract tables from PDF",
    "code": "extract_tables('report.pdf')",
    "use_case": "Reports with structured data"
  }
}
```

**使用效果**：

```python
# Agent 在系统提示中看到（第一层）：
"""
## Analysis

- **pdf_analyzer**: Analyze and extract information from PDF documents
  💡 Quick: Use PyPDF2 or pdfplumber to extract text, tables, and metadata
  📄 Details: `cat skills/pdf_analyzer/SKILL.md`
  📦 Resources: `ls skills/pdf_analyzer/resources/`
"""

# 用户任务
msg = Message(role="user", content="分析这个 PDF: report.pdf")
response = await agent.run(msg)

# Agent 会：
# 1. 看到 pdf_analyzer 在索引中
# 2. 执行: cat skills/pdf_analyzer/SKILL.md（读取详细文档）
# 3. 执行: cat skills/pdf_analyzer/resources/examples.json（查看示例）
# 4. 使用学到的知识完成任务
```

---

### 示例 2：Web 研究 Skill

**skill.yaml**：
```yaml
metadata:
  name: web_research
  description: Conduct web research and gather information from online sources
  category: tools
  version: 1.0.0
  author: Loom Team
  tags:
    - web
    - research
    - search
    - scraping
  dependencies: []
  enabled: true

quick_guide: Use search APIs (Google, Bing) for queries, requests/beautifulsoup4 for scraping, and selenium for dynamic content. See resources/search_templates.json for query patterns.
```

**SKILL.md**（节选）：
```markdown
# Web Research

Conduct comprehensive web research and gather information from online sources.

## Overview

- Search engine queries (Google, Bing, DuckDuckGo)
- Web scraping and content extraction
- Dynamic content handling (JavaScript-rendered pages)
- Multi-source information synthesis

## Usage

### Search Engine Queries

\`\`\`python
import requests
from bs4 import BeautifulSoup

def google_search(query: str, num_results: int = 10) -> list:
    # Implementation...
    pass
\`\`\`

### Web Scraping

\`\`\`python
def scrape_article(url: str) -> dict:
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    # Extract content...
    return {'title': ..., 'content': ...}
\`\`\`

## Dependencies

- requests: `pip install requests`
- beautifulsoup4: `pip install beautifulsoup4`
- selenium: `pip install selenium` (for dynamic content)

## Notes

- Always respect robots.txt
- Add rate limiting to avoid overwhelming servers
- Use appropriate User-Agent headers
```

---

### 示例 3：自定义业务 Skill

假设你的业务需要频繁访问内部 API：

**skill.yaml**：
```yaml
metadata:
  name: company_api
  description: Access company internal APIs for customer data, orders, and inventory
  category: business
  version: 1.0.0
  author: Your Company
  tags:
    - api
    - internal
    - business
  dependencies: []
  enabled: true

quick_guide: Use the internal API client to query customer info, orders, and inventory. Authentication is automatic via API_KEY env var.
```

**SKILL.md**：
```markdown
# Company Internal API

Access company internal APIs.

## Overview

Available endpoints:
- Customer API: `/api/customers/`
- Order API: `/api/orders/`
- Inventory API: `/api/inventory/`

## Usage

### Authentication

\`\`\`python
import os
import requests

API_KEY = os.environ.get("COMPANY_API_KEY")
BASE_URL = "https://api.company.com"

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}
\`\`\`

### Get Customer Info

\`\`\`python
def get_customer(customer_id: str) -> dict:
    url = f"{BASE_URL}/api/customers/{customer_id}"
    response = requests.get(url, headers=headers)
    return response.json()
\`\`\`

### Query Orders

\`\`\`python
def get_orders(customer_id: str, status: str = "active") -> list:
    url = f"{BASE_URL}/api/orders/"
    params = {"customer_id": customer_id, "status": status}
    response = requests.get(url, headers=headers, params=params)
    return response.json()["orders"]
\`\`\`

## Examples

See `resources/api_examples.json` for complete examples.

## Notes

- API_KEY must be set in environment
- Rate limit: 100 requests/minute
- Use pagination for large result sets
```

**resources/api_examples.json**：
```json
{
  "get_customer": {
    "endpoint": "/api/customers/{id}",
    "method": "GET",
    "example": {
      "customer_id": "CUST-12345",
      "expected_response": {
        "id": "CUST-12345",
        "name": "John Doe",
        "email": "john@example.com"
      }
    }
  },
  "create_order": {
    "endpoint": "/api/orders/",
    "method": "POST",
    "example": {
      "body": {
        "customer_id": "CUST-12345",
        "items": [{"product_id": "PROD-001", "quantity": 2}]
      }
    }
  }
}
```

**使用**：
```python
agent = loom.agent(
    name="customer-service",
    llm=OpenAILLM(api_key="..."),
    enable_skills=True,
    skills_dir="./skills"
)

# Agent 可以回答诸如：
# "查询客户 CUST-12345 的所有待处理订单"
# "为客户 CUST-67890 创建新订单"
```

---

## 最佳实践

### 1. 设计原则

#### ✅ 单一职责
每个 Skill 专注于一个领域：

```
✅ 好的设计
- pdf_analyzer: 只处理 PDF
- web_research: 只处理 Web 研究
- data_processor: 只处理数据

❌ 不好的设计
- document_handler: PDF + Word + Excel + ...（太宽泛）
```

#### ✅ 适当粒度
不要太细也不要太粗：

```
❌ 太细
- pdf_text_extractor
- pdf_table_extractor
- pdf_image_extractor
→ 应该合并为 pdf_analyzer

❌ 太粗
- document_processor: PDF + Web + Excel + API + ...
→ 应该拆分为多个 Skills

✅ 合适
- pdf_analyzer: PDF 文档的所有操作
- web_research: Web 研究的所有操作
```

#### ✅ 清晰命名
使用描述性名称：

```
✅ 好的命名
- pdf_analyzer（清晰）
- web_research（描述性）
- api_client（明确）

❌ 不好的命名
- skill1（无意义）
- helper（太宽泛）
- utils（不清楚）
```

---

### 2. 文档编写

#### 第一层（skill.yaml）
- **description**: 1-2 句话（~50 tokens）
- **quick_guide**: 1-3 句话使用指南（~200 tokens）
- 重点：快速理解这个 Skill 是做什么的

```yaml
# ✅ 好的描述
description: Analyze and extract information from PDF documents
quick_guide: Use PyPDF2 or pdfplumber to extract text, tables, and metadata from PDF files.

# ❌ 不好的描述
description: A skill
quick_guide: Does stuff
```

#### 第二层（SKILL.md）
- 包含完整使用说明
- 提供代码示例
- 说明依赖和注意事项
- 500-2000 tokens 适中

**模板**：
```markdown
# Skill Name

Brief description.

## Overview
- What it does
- Use cases
- Key features

## Usage
### Basic Usage
\`\`\`python
# Code example
\`\`\`

### Advanced Usage
\`\`\`python
# More examples
\`\`\`

## Examples
- Example 1
- Example 2

## Dependencies
- package1: `pip install package1`

## Notes
- Important notes
- Limitations
```

#### 第三层（resources/）
- 示例数据：`examples.json`
- 模板文件：`templates/`
- 配置文件：`config.yaml`
- 测试数据：`test_data/`

---

### 3. 组织结构

#### 按分类组织

```
skills/
  # Tools
  pdf_analyzer/
  web_research/
  image_processor/

  # Analysis
  data_analyzer/
  sentiment_analyzer/

  # Communication
  email_sender/
  slack_notifier/

  # Business
  crm_api/
  payment_processor/
```

#### 使用 category 字段

```yaml
# Tools
category: tools

# Analysis
category: analysis

# Communication
category: communication

# Business
category: business
```

Agent 会按分类显示：
```
## Tools
- pdf_analyzer: ...
- web_research: ...

## Analysis
- data_analyzer: ...
- sentiment_analyzer: ...
```

---

### 4. 依赖管理

#### 声明依赖

如果 Skill 依赖其他 Skills：

```yaml
metadata:
  name: advanced_research
  dependencies:
    - web_research      # 需要 web_research
    - data_processor    # 需要 data_processor
```

#### Python 包依赖

在 SKILL.md 中清晰列出：

```markdown
## Dependencies

- requests: `pip install requests`
- beautifulsoup4: `pip install beautifulsoup4`
- pandas: `pip install pandas`

Or install all:
\`\`\`bash
pip install requests beautifulsoup4 pandas
\`\`\`
```

#### 可选依赖

```markdown
## Dependencies

### Required
- requests: `pip install requests`

### Optional
- selenium: `pip install selenium` (for dynamic content)
- pytesseract: `pip install pytesseract` (for OCR)
```

---

### 5. 版本控制

#### 语义化版本

```yaml
version: 1.0.0  # MAJOR.MINOR.PATCH
```

- **MAJOR**: 不兼容的 API 变更
- **MINOR**: 新增功能（向后兼容）
- **PATCH**: Bug 修复（向后兼容）

#### 变更日志

在 SKILL.md 底部添加：

```markdown
## Changelog

### v1.2.0 (2024-12-14)
- Added table extraction support
- Improved text extraction accuracy

### v1.1.0 (2024-12-01)
- Added metadata extraction
- Fixed encoding issues

### v1.0.0 (2024-11-15)
- Initial release
```

---

## 测试与验证

### 1. 测试 Skill 加载

```python
import loom
from loom.builtin import OpenAILLM

agent = loom.agent(
    name="test-agent",
    llm=OpenAILLM(api_key="..."),
    enable_skills=True,
    skills_dir="./skills"
)

# 列出所有 Skills
skills = agent.list_skills()
for skill in skills:
    print(f"✓ {skill.metadata.name}: {skill.metadata.description}")

# 检查特定 Skill
skill = agent.get_skill("my_skill")
if skill:
    print(f"✓ Skill loaded: {skill}")
    print(f"  Category: {skill.metadata.category}")
    print(f"  Tags: {skill.metadata.tags}")
else:
    print("✗ Skill not found")
```

### 2. 验证系统提示

```python
# 查看生成的系统提示
print(agent.system_prompt)

# 应该看到 Skills 索引：
"""
# Available Skills

## Analysis
- **my_skill**: Short description
  💡 Quick: One-sentence usage guide
  📄 Details: `cat skills/my_skill/SKILL.md`
  📦 Resources: `ls skills/my_skill/resources/`
"""
```

### 3. 测试 Skill 使用

```python
from loom import Message

# 测试 Agent 是否能使用 Skill
msg = Message(
    role="user",
    content="使用 my_skill 完成一个简单任务"
)

response = await agent.run(msg)
print(response.content)

# 检查 Agent 是否读取了详细文档
# 查看 event_handler 或日志
```

### 4. 单元测试

创建 `tests/test_skills.py`：

```python
import pytest
from pathlib import Path
from loom.skills import Skill, SkillManager

def test_skill_loading():
    """测试 Skill 加载"""
    skill_dir = Path("skills/my_skill")
    skill = Skill.from_directory(skill_dir)

    assert skill.metadata.name == "my_skill"
    assert skill.metadata.category == "general"
    assert skill.quick_guide is not None

def test_skill_manager():
    """测试 SkillManager"""
    manager = SkillManager("./skills")
    manager.load_all()

    skills = manager.list_skills()
    assert len(skills) > 0

    skill = manager.get_skill("my_skill")
    assert skill is not None

def test_detailed_doc_loading():
    """测试详细文档加载"""
    skill = Skill.from_directory(Path("skills/my_skill"))

    detailed_doc = skill.load_detailed_doc()
    assert detailed_doc is not None
    assert len(detailed_doc) > 0

def test_resources():
    """测试资源文件"""
    skill = Skill.from_directory(Path("skills/my_skill"))

    # 检查资源是否存在
    resource_path = skill.get_resource_path("examples.json")
    if resource_path:
        assert resource_path.exists()
```

运行测试：
```bash
pytest tests/test_skills.py -v
```

---

## 常见问题

### Q1: Skill 没有被加载？

**排查步骤**：
1. 检查目录名是否与 `metadata.name` 一致
2. 确认 `skill.yaml` 格式正确
3. 检查 `skills_dir` 路径是否正确
4. 查看 `enabled: true`

```python
# 调试
agent = loom.agent(
    name="agent",
    llm=llm,
    enable_skills=True,
    skills_dir="./skills"
)

skills = agent.list_skills()
print(f"Loaded {len(skills)} skills:")
for s in skills:
    print(f"  - {s.metadata.name}")
```

### Q2: Agent 没有使用 Skill？

**可能原因**：
1. 系统提示不够清晰
2. quick_guide 不够具体
3. Skill 与任务不匹配

**解决方法**：
```yaml
# 改进 quick_guide
quick_guide: "Use PyPDF2 or pdfplumber to extract text and tables from PDF files. For OCR, use pytesseract. Check resources/examples.json for code examples."
```

### Q3: 如何更新 Skill？

```python
# 方式 1：手动编辑文件后重新加载
agent.reload_skills()

# 方式 2：程序化编辑
from loom.skills import SkillManager

manager = SkillManager("./skills")
manager.edit_skill_metadata(
    name="my_skill",
    description="Updated description",
    tags=["new-tag"]
)
```

### Q4: 如何禁用/启用 Skill？

```python
# 禁用
agent.disable_skill("my_skill")

# 启用
agent.enable_skill("my_skill")

# 或直接编辑 skill.yaml
# enabled: false
```

### Q5: 如何删除 Skill？

```python
# 方式 1：程序化删除
from loom.skills import SkillManager

manager = SkillManager("./skills")
manager.delete_skill("my_skill")

# 方式 2：手动删除目录
rm -rf skills/my_skill/
```

### Q6: Skill 文档太长，影响性能？

**这就是三层架构的价值！**

- 第一层（索引）总是加载：~50 tokens
- 第二层（详细文档）按需加载：只在 Agent 需要时加载
- 第三层（资源）按需访问：完全不占用上下文

即使你有 10 个 Skills，系统提示也只有 ~500 tokens。

### Q7: 如何共享 Skills？

```bash
# 方式 1：直接复制目录
cp -r skills/my_skill /path/to/other/project/skills/

# 方式 2：打包为 tar.gz
tar -czf my_skill.tar.gz skills/my_skill/

# 方式 3：Git 仓库（推荐）
git clone https://github.com/username/loom-skills.git skills/
```

### Q8: Skill 可以包含代码吗？

**不推荐**。Skills 应该是**文档和指南**，不是代码库。

```
❌ 不推荐
skills/my_skill/
  skill.yaml
  SKILL.md
  code/              # 不要这样做
    implementation.py

✅ 推荐
skills/my_skill/
  skill.yaml
  SKILL.md           # 包含代码示例和使用说明
  resources/
    examples.json    # 示例数据
```

**原因**：
- Agent 通过阅读文档学习，而不是执行代码
- 代码应该作为 Tools 提供
- Skills 是"知识"，Tools 是"能力"

### Q9: Skills vs Tools 的区别？

| 维度 | Skills | Tools |
|------|--------|-------|
| 本质 | 知识、文档、指南 | 可执行函数 |
| 形式 | Markdown + YAML | Python 函数 |
| 使用 | Agent 阅读学习 | Agent 调用执行 |
| 示例 | "如何使用 API" | `call_api()` 函数 |
| 场景 | 提供背景知识 | 提供具体能力 |

**组合使用**：
```python
# Skill: 提供知识
skills/api_usage/
  skill.yaml: "How to use our API..."
  SKILL.md: Complete API documentation

# Tool: 提供能力
@tool(name="call_api")
async def call_api(endpoint: str, method: str, data: dict):
    # 实际执行 API 调用
    ...

# Agent 组合使用：
# 1. 从 Skill 学习 API 使用方法
# 2. 使用 Tool 实际调用 API
```

### Q10: 如何组织大量 Skills？

**方式 1：子目录组织**（推荐）

```
skills/
  tools/
    pdf_analyzer/
    web_research/
  analysis/
    data_analyzer/
    sentiment_analyzer/
  business/
    crm_api/
    payment/
```

```python
# 加载时指定子目录
agent = loom.agent(
    name="agent",
    llm=llm,
    enable_skills=True,
    skills_dir="./skills"  # 会递归扫描所有子目录
)
```

**方式 2：多个 Skills 目录**

```python
from loom.skills import SkillManager

# 合并多个 Skills 目录
manager1 = SkillManager("./skills/tools")
manager2 = SkillManager("./skills/business")

# 在 Agent 中使用
agent = loom.agent(
    name="agent",
    llm=llm,
    enable_skills=True,
    skills_dir="./skills"  # 主目录
)

# 手动合并
for skill_name, skill in manager2.skills.items():
    agent.skill_manager.skills[skill_name] = skill
```

---

## 下一步

### 深入学习
- [Skills 概述](./overview.md) - Skills 系统完整介绍
- [内置 Skills](./builtin-skills.md) - 使用内置 Skills
- [Skills 快速参考](./quick-reference.md) - API 速查

### 相关主题
- [SimpleAgent 指南](../agents/simple-agent.md) - Agent 与 Skills 集成
- [工具开发](../tools/development.md) - Tools vs Skills
- [事件系统](../advanced/events.md) - 监控 Skill 使用

### 示例
- [示例库](../../examples/) - 完整示例代码
- [Skills 目录](../../../skills/) - 内置 Skills 源码

---

## 总结

创建 Skills 的关键要点：

1. **三层架构**：索引（~50 tokens）→ 详细文档（~500 tokens）→ 资源（按需）
2. **单一职责**：每个 Skill 专注一个领域
3. **清晰文档**：description 简洁，quick_guide 实用，SKILL.md 详细
4. **适当粒度**：不要太细也不要太粗
5. **按需加载**：最小化上下文使用
6. **易于维护**：标准结构，版本控制，单元测试

**记住**：Skills 是知识，Tools 是能力。Skills 让 Agent 更聪明，Tools 让 Agent 更强大。

---

**开始创建你的第一个 Skill 吧！** 🎯
