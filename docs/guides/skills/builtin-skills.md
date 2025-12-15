# 内置 Skills

**版本**: v0.1.6
**难度**: 初级

了解和使用 Loom Agent 内置的 Skills。

---

## 📋 目录

1. [概述](#概述)
2. [PDF Analyzer](#pdf-analyzer)
3. [Web Research](#web-research)
4. [Data Processor](#data-processor)
5. [使用方式](#使用方式)
6. [常见用例](#常见用例)
7. [启用和禁用](#启用和禁用)
8. [故障排除](#故障排除)

---

## 概述

Loom Agent v0.1.6 内置 **3 个** Skills，开箱即用：

| Skill | 分类 | 功能 | 依赖 |
|-------|------|------|------|
| **pdf_analyzer** | analysis | PDF 文档分析与提取 | PyPDF2, pdfplumber |
| **web_research** | tools | Web 研究和信息收集 | requests, beautifulsoup4 |
| **data_processor** | tools | 结构化数据处理 | pandas, openpyxl |

### 自动集成

```python
import loom
from loom.builtin import OpenAILLM

agent = loom.agent(
    name="assistant",
    llm=OpenAILLM(api_key="..."),
    enable_skills=True,        # ✅ 默认启用
    skills_dir="./skills"      # ✅ 默认路径
)

# 3 个 Skills 自动加载到系统提示
# Agent 可以按需使用
```

### 三层渐进式披露

每个 Skill 都采用三层架构：

```
第一层（索引）→ 系统提示，~50 tokens
第二层（详细文档）→ SKILL.md，按需加载，~500-2000 tokens
第三层（资源文件）→ resources/，按需访问，任意大小
```

**优势**：最小化上下文使用，Agent 需要时才加载详细信息。

---

## PDF Analyzer

### 概述

**名称**: `pdf_analyzer`
**分类**: `analysis`
**版本**: `1.0.0`

**功能**：
- 文本提取
- 表格提取
- 元数据提取
- 逐页处理
- OCR 支持（可选）

### 第一层：索引

Agent 在系统提示中看到：

```
## Analysis

- **pdf_analyzer**: Analyze and extract information from PDF documents
  💡 Quick: Use PyPDF2 or pdfplumber to extract text, tables, and metadata from PDF files. Check resources/examples.json for common patterns.
  📄 Details: `cat skills/pdf_analyzer/SKILL.md`
  📦 Resources: `ls skills/pdf_analyzer/resources/`
```

### 第二层：详细文档

Agent 需要时会执行：
```bash
cat skills/pdf_analyzer/SKILL.md
```

内容包括：
- **文本提取**：使用 PyPDF2 提取纯文本
- **表格提取**：使用 pdfplumber 提取表格数据
- **元数据提取**：获取作者、标题、创建日期等
- **OCR 处理**：对扫描版 PDF 使用 pytesseract

### 第三层：资源文件

```
skills/pdf_analyzer/resources/
  examples.json        # 常见使用模式示例
```

### 核心能力

#### 1. 文本提取

```python
import PyPDF2

def extract_text(pdf_path: str) -> str:
    """从 PDF 提取所有文本"""
    with open(pdf_path, 'rb') as f:
        reader = PyPDF2.PdfReader(f)
        text = ""
        for page in reader.pages:
            text += page.extract_text()
    return text
```

#### 2. 表格提取

```python
import pdfplumber

def extract_tables(pdf_path: str) -> list:
    """提取 PDF 中的所有表格"""
    tables = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            tables.extend(page.extract_tables())
    return tables
```

#### 3. 元数据提取

```python
def extract_metadata(pdf_path: str) -> dict:
    """提取 PDF 元数据"""
    with open(pdf_path, 'rb') as f:
        reader = PyPDF2.PdfReader(f)
        metadata = reader.metadata
    return {
        'author': metadata.get('/Author'),
        'title': metadata.get('/Title'),
        'subject': metadata.get('/Subject'),
        'creator': metadata.get('/Creator'),
        'pages': len(reader.pages)
    }
```

### 使用场景

| 场景 | 示例任务 |
|------|----------|
| **文档处理** | "提取这份合同的关键条款" |
| **发票分析** | "从这 10 张发票中提取金额和日期" |
| **简历解析** | "从简历中提取候选人的工作经验" |
| **报告汇总** | "汇总这份 PDF 报告的主要结论" |

### 依赖安装

```bash
# 基础功能
pip install PyPDF2 pdfplumber

# OCR 功能（可选）
pip install pytesseract pdf2image
# macOS: brew install tesseract
# Ubuntu: sudo apt-get install tesseract-ocr
```

### 示例：完整 PDF 分析

```python
from loom import Message, SimpleAgent
from loom.builtin import OpenAILLM

agent = loom.agent(
    name="pdf-analyst",
    llm=OpenAILLM(api_key="..."),
    enable_skills=True
)

# 任务
msg = Message(
    role="user",
    content="""
    分析 report.pdf，提取：
    1. 文档标题和作者
    2. 所有表格数据
    3. 关键结论（在第 5 页）
    """
)

response = await agent.run(msg)
print(response.content)

# Agent 会：
# 1. 识别 pdf_analyzer skill
# 2. 读取 SKILL.md 了解详细用法
# 3. 使用 PyPDF2 提取元数据
# 4. 使用 pdfplumber 提取表格
# 5. 提取第 5 页的文本并总结
```

---

## Web Research

### 概述

**名称**: `web_research`
**分类**: `tools`
**版本**: `1.0.0`

**功能**：
- 搜索引擎查询（Google, Bing, DuckDuckGo）
- Web 抓取和内容提取
- 动态内容处理（JavaScript 渲染页面）
- 多源信息综合
- 引用和来源追踪

### 第一层：索引

```
## Tools

- **web_research**: Conduct web research and gather information from online sources
  💡 Quick: Use search APIs (Google, Bing) for queries, requests/beautifulsoup4 for scraping, and selenium for dynamic content. See resources/search_templates.json for query patterns.
  📄 Details: `cat skills/web_research/SKILL.md`
  📦 Resources: `ls skills/web_research/resources/`
```

### 第二层：详细文档

包含：
- **搜索引擎查询**：如何构建有效的搜索查询
- **Web 抓取**：使用 requests 和 BeautifulSoup
- **动态内容**：使用 Selenium 处理 JavaScript
- **多源研究**：综合多个来源的信息

### 第三层：资源文件

```
skills/web_research/resources/
  search_templates.json    # 搜索查询模板
```

### 核心能力

#### 1. 搜索引擎查询

```python
import requests
from bs4 import BeautifulSoup

def google_search(query: str, num_results: int = 10) -> list:
    """执行 Google 搜索并返回结果"""
    url = f"https://www.google.com/search?q={query}&num={num_results}"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.text, 'html.parser')

    results = []
    for g in soup.find_all('div', class_='g'):
        title = g.find('h3')
        link = g.find('a')
        if title and link:
            results.append({
                'title': title.get_text(),
                'link': link.get('href')
            })
    return results
```

#### 2. Web 抓取

```python
def scrape_article(url: str) -> dict:
    """从 URL 提取文章内容"""
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')

    # 提取主要内容
    article = soup.find('article') or soup.find('main')

    return {
        'title': soup.find('h1').get_text() if soup.find('h1') else '',
        'content': article.get_text() if article else '',
        'url': url
    }
```

#### 3. 动态内容处理

```python
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def scrape_dynamic_page(url: str) -> str:
    """抓取 JavaScript 渲染的内容"""
    driver = webdriver.Chrome()
    driver.get(url)

    # 等待内容加载
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CLASS_NAME, "content"))
    )

    content = driver.find_element(By.CLASS_NAME, "content").text
    driver.quit()

    return content
```

#### 4. 多源研究

```python
def research_topic(topic: str, num_sources: int = 5) -> dict:
    """从多个来源研究主题"""
    # 1. 搜索来源
    search_results = google_search(topic, num_sources)

    # 2. 提取内容
    sources = []
    for result in search_results:
        try:
            content = scrape_article(result['link'])
            sources.append(content)
        except Exception as e:
            print(f"Failed to scrape {result['link']}: {e}")

    # 3. 综合信息
    return {
        'topic': topic,
        'num_sources': len(sources),
        'sources': sources
    }
```

### 使用场景

| 场景 | 示例任务 |
|------|----------|
| **市场研究** | "研究 AI Agent 市场的最新趋势" |
| **竞品分析** | "对比 3 个主流项目管理工具的特性" |
| **事实核查** | "验证这条新闻的真实性" |
| **趋势分析** | "分析最近 6 个月 React 框架的发展" |

### 依赖安装

```bash
# 基础功能
pip install requests beautifulsoup4

# 动态内容（可选）
pip install selenium
# 需要下载 ChromeDriver: https://chromedriver.chromium.org/
```

### 示例：市场研究

```python
from loom import Message, SimpleAgent
from loom.builtin import OpenAILLM

agent = loom.agent(
    name="researcher",
    llm=OpenAILLM(api_key="..."),
    enable_skills=True
)

msg = Message(
    role="user",
    content="""
    研究"AI Agent 框架"这个主题：
    1. 找到 5 个相关的技术文章
    2. 总结主要趋势
    3. 列出主流框架的优缺点
    """
)

response = await agent.run(msg)
print(response.content)

# Agent 会：
# 1. 识别 web_research skill
# 2. 读取 SKILL.md 和搜索模板
# 3. 执行 Google 搜索
# 4. 抓取文章内容
# 5. 综合分析并给出报告
```

### 注意事项

- **遵守 robots.txt**：始终检查网站的爬虫政策
- **速率限制**：避免频繁请求，添加延迟
- **User-Agent**：使用合适的 User-Agent 头
- **代理**：大规模抓取时考虑使用代理
- **缓存**：缓存结果以减少重复请求

---

## Data Processor

### 概述

**名称**: `data_processor`
**分类**: `tools`
**版本**: `1.0.0`

**功能**：
- CSV/Excel 文件读写
- JSON 数据操作
- 数据清洗和验证
- 数据转换和聚合
- 格式转换
- 数据质量分析

### 第一层：索引

```
## Tools

- **data_processor**: Process and transform structured data (CSV, JSON, Excel)
  💡 Quick: Use pandas for tabular data, json module for JSON, and openpyxl for Excel. Check resources/transformation_patterns.json for common operations like filtering, aggregation, and merging.
  📄 Details: `cat skills/data_processor/SKILL.md`
  📦 Resources: `ls skills/data_processor/resources/`
```

### 第二层：详细文档

包含：
- **CSV 处理**：读取、清洗、转换、保存
- **JSON 处理**：解析、转换、扁平化
- **数据聚合**：分组、统计、计算
- **数据合并**：多数据集合并
- **数据验证**：规则检查、质量分析
- **格式转换**：CSV ↔ JSON ↔ Excel

### 第三层：资源文件

```
skills/data_processor/resources/
  transformation_patterns.json    # 常见数据转换模式
```

### 核心能力

#### 1. CSV 处理

```python
import pandas as pd

def process_csv(input_path: str, output_path: str) -> dict:
    """读取、处理并保存 CSV 数据"""
    # 读取 CSV
    df = pd.read_csv(input_path)

    # 基础清洗
    df = df.drop_duplicates()
    df = df.dropna(subset=['important_column'])

    # 转换
    df['new_column'] = df['col1'] + df['col2']

    # 保存结果
    df.to_csv(output_path, index=False)

    return {
        'rows_processed': len(df),
        'columns': list(df.columns),
        'output_file': output_path
    }
```

#### 2. JSON 处理

```python
import json

def process_json(input_path: str, transform_func=None) -> dict:
    """读取并转换 JSON 数据"""
    with open(input_path, 'r') as f:
        data = json.load(f)

    # 应用转换
    if transform_func:
        data = transform_func(data)

    return data

def flatten_json(nested_json: dict, prefix: str = '') -> dict:
    """扁平化嵌套的 JSON 结构"""
    flattened = {}
    for key, value in nested_json.items():
        new_key = f"{prefix}.{key}" if prefix else key
        if isinstance(value, dict):
            flattened.update(flatten_json(value, new_key))
        else:
            flattened[new_key] = value
    return flattened
```

#### 3. 数据聚合

```python
def aggregate_data(df: pd.DataFrame, group_by: list, agg_funcs: dict) -> pd.DataFrame:
    """按指定列聚合数据"""
    # 示例: group_by=['category'], agg_funcs={'sales': 'sum', 'quantity': 'mean'}
    result = df.groupby(group_by).agg(agg_funcs).reset_index()
    return result
```

#### 4. 数据合并

```python
def merge_datasets(df1: pd.DataFrame, df2: pd.DataFrame,
                  on: str, how: str = 'inner') -> pd.DataFrame:
    """合并两个数据集"""
    merged = pd.merge(df1, df2, on=on, how=how)
    return merged
```

#### 5. 数据验证

```python
def validate_data(df: pd.DataFrame, rules: dict) -> dict:
    """根据规则验证数据"""
    validation_results = {
        'valid': True,
        'errors': []
    }

    # 检查必需列
    if 'required_columns' in rules:
        missing = set(rules['required_columns']) - set(df.columns)
        if missing:
            validation_results['valid'] = False
            validation_results['errors'].append(f"Missing columns: {missing}")

    # 检查数据类型
    if 'data_types' in rules:
        for col, expected_type in rules['data_types'].items():
            if col in df.columns and df[col].dtype != expected_type:
                validation_results['valid'] = False
                validation_results['errors'].append(
                    f"Column {col} has type {df[col].dtype}, expected {expected_type}"
                )

    return validation_results
```

#### 6. 格式转换

```python
def convert_format(input_path: str, output_path: str,
                  input_format: str, output_format: str) -> bool:
    """在数据格式之间转换"""
    # 读取输入
    if input_format == 'csv':
        df = pd.read_csv(input_path)
    elif input_format == 'json':
        df = pd.read_json(input_path)
    elif input_format == 'excel':
        df = pd.read_excel(input_path)

    # 写入输出
    if output_format == 'csv':
        df.to_csv(output_path, index=False)
    elif output_format == 'json':
        df.to_json(output_path, orient='records', indent=2)
    elif output_format == 'excel':
        df.to_excel(output_path, index=False)

    return True
```

### 使用场景

| 场景 | 示例任务 |
|------|----------|
| **数据清洗** | "清洗这个 CSV 文件：删除重复项和空值" |
| **ETL 管道** | "从 3 个 Excel 文件提取、转换并加载到数据库" |
| **数据聚合** | "按类别汇总销售数据，计算总额和平均值" |
| **格式转换** | "将这个 CSV 转换为 JSON" |

### 依赖安装

```bash
# 基础功能
pip install pandas

# Excel 支持
pip install openpyxl

# 高级分析
pip install numpy
```

### 示例：数据分析管道

```python
from loom import Message, SimpleAgent
from loom.builtin import OpenAILLM

agent = loom.agent(
    name="data-analyst",
    llm=OpenAILLM(api_key="..."),
    enable_skills=True
)

msg = Message(
    role="user",
    content="""
    处理 sales_data.csv：
    1. 清洗数据（删除重复项和空值）
    2. 按产品类别聚合销售额
    3. 计算每个类别的平均价格
    4. 保存结果到 sales_summary.xlsx
    """
)

response = await agent.run(msg)
print(response.content)

# Agent 会：
# 1. 识别 data_processor skill
# 2. 读取 SKILL.md 了解 pandas 用法
# 3. 读取并清洗 CSV
# 4. 执行聚合操作
# 5. 保存为 Excel 格式
```

### 性能优化

```python
# 大文件（>1GB）：使用分块
df = pd.read_csv('large_file.csv', chunksize=10000)
for chunk in df:
    process(chunk)

# 优化内存：指定数据类型
df = pd.read_csv('file.csv', dtype={
    'id': 'int32',
    'value': 'float32'
})

# 日期解析
df = pd.read_csv('file.csv', parse_dates=['date_column'])
```

---

## 使用方式

### 默认使用

Skills 默认自动加载：

```python
import loom
from loom.builtin import OpenAILLM

agent = loom.agent(
    name="assistant",
    llm=OpenAILLM(api_key="...")
    # enable_skills=True    # ✅ 默认
    # skills_dir="./skills" # ✅ 默认
)

# 3 个内置 Skills 已加载
```

### 自定义 Skills 目录

```python
agent = loom.agent(
    name="assistant",
    llm=OpenAILLM(api_key="..."),
    enable_skills=True,
    skills_dir="/path/to/my/skills"  # 自定义路径
)
```

### 禁用 Skills

```python
agent = loom.agent(
    name="assistant",
    llm=OpenAILLM(api_key="..."),
    enable_skills=False  # 禁用所有 Skills
)
```

### 列出 Skills

```python
# 列出所有 Skills
skills = agent.list_skills()
for skill in skills:
    print(f"{skill.metadata.name}: {skill.metadata.description}")

# 按分类筛选
analysis_skills = agent.list_skills(category="analysis")
tool_skills = agent.list_skills(category="tools")
```

### 查看 Skill 详情

```python
# 获取特定 Skill
skill = agent.get_skill("pdf_analyzer")

print(f"Name: {skill.metadata.name}")
print(f"Description: {skill.metadata.description}")
print(f"Category: {skill.metadata.category}")
print(f"Version: {skill.metadata.version}")
print(f"Tags: {skill.metadata.tags}")

# 加载详细文档
detailed_doc = skill.load_detailed_doc()
print(detailed_doc)

# 查看资源文件
resource_path = skill.get_resource_path("examples.json")
if resource_path:
    print(f"Resource: {resource_path}")
```

---

## 常见用例

### 用例 1：文档处理工作流

```python
from loom import Message, SimpleAgent
from loom.builtin import OpenAILLM

agent = loom.agent(
    name="document-processor",
    llm=OpenAILLM(api_key="..."),
    enable_skills=True
)

# 任务：处理一批发票
msg = Message(
    role="user",
    content="""
    处理 invoices/ 目录下的所有 PDF 发票：
    1. 提取每张发票的：公司名、金额、日期
    2. 汇总到 Excel 文件
    3. 计算总金额
    """
)

response = await agent.run(msg)

# Agent 使用：
# - pdf_analyzer: 提取 PDF 数据
# - data_processor: 汇总到 Excel
```

### 用例 2：市场调研报告

```python
agent = loom.agent(
    name="market-researcher",
    llm=OpenAILLM(api_key="..."),
    enable_skills=True
)

msg = Message(
    role="user",
    content="""
    创建一份"AI Agent 框架"市场调研报告：
    1. 搜索并分析 10 篇相关文章
    2. 总结主要趋势和挑战
    3. 对比 3 个主流框架
    4. 生成 Markdown 报告
    """
)

response = await agent.run(msg)

# Agent 使用：
# - web_research: 搜索和抓取文章
# - data_processor: 结构化分析结果
```

### 用例 3：数据分析自动化

```python
agent = loom.agent(
    name="data-analyst",
    llm=OpenAILLM(api_key="..."),
    enable_skills=True
)

msg = Message(
    role="user",
    content="""
    分析销售数据：
    1. 从 sales_2024.xlsx 读取数据
    2. 按月份和产品类别聚合
    3. 识别销售趋势
    4. 生成可视化报告（描述性）
    """
)

response = await agent.run(msg)

# Agent 使用：
# - data_processor: Excel 处理和聚合
```

### 用例 4：混合任务

```python
agent = loom.agent(
    name="research-analyst",
    llm=OpenAILLM(api_key="..."),
    enable_skills=True
)

msg = Message(
    role="user",
    content="""
    完整的竞品分析：
    1. 从网上收集 3 个竞品的信息
    2. 下载他们的产品白皮书（PDF）
    3. 提取关键特性和定价
    4. 整理到对比表（CSV）
    5. 生成分析报告
    """
)

response = await agent.run(msg)

# Agent 使用所有 3 个 Skills：
# - web_research: 收集在线信息
# - pdf_analyzer: 分析白皮书
# - data_processor: 整理对比表
```

---

## 启用和禁用

### 运行时启用/禁用

```python
agent = loom.agent(
    name="assistant",
    llm=OpenAILLM(api_key="..."),
    enable_skills=True
)

# 禁用特定 Skill
agent.disable_skill("web_research")
print(agent.list_skills())  # 只显示 pdf_analyzer 和 data_processor

# 启用 Skill
agent.enable_skill("web_research")
print(agent.list_skills())  # 显示所有 3 个 Skills

# 重新加载 Skills（从磁盘）
agent.reload_skills()
```

### 永久禁用

编辑 `skills/<skill_name>/skill.yaml`：

```yaml
metadata:
  name: web_research
  # ...
  enabled: false  # ✅ 禁用
```

然后重新加载：
```python
agent.reload_skills()
```

### 按场景选择

```python
# 场景 1：只需要文档处理
agent = loom.agent(
    name="doc-processor",
    llm=llm,
    enable_skills=True
)
agent.disable_skill("web_research")
agent.disable_skill("data_processor")
# 只保留 pdf_analyzer

# 场景 2：只需要数据分析
agent = loom.agent(
    name="data-analyst",
    llm=llm,
    enable_skills=True
)
agent.disable_skill("pdf_analyzer")
agent.disable_skill("web_research")
# 只保留 data_processor
```

---

## 故障排除

### Q1: Skills 没有加载？

**症状**：`agent.list_skills()` 返回空列表

**排查步骤**：

1. 检查 Skills 目录是否存在：
```bash
ls -la ./skills/
# 应该看到 pdf_analyzer/, web_research/, data_processor/
```

2. 确认 `enable_skills=True`：
```python
agent = loom.agent(
    name="assistant",
    llm=llm,
    enable_skills=True  # ✅ 必须启用
)
```

3. 检查 `skills_dir` 路径：
```python
# 使用绝对路径
import os
skills_dir = os.path.abspath("./skills")
agent = loom.agent(
    name="assistant",
    llm=llm,
    skills_dir=skills_dir
)
```

### Q2: Agent 没有使用 Skill？

**症状**：Agent 完成了任务但没有使用 Skills

**可能原因**：
1. quick_guide 不够明确
2. 任务描述不清楚
3. Skill 被禁用

**解决方法**：

```python
# 1. 检查 Skill 是否启用
skills = agent.list_skills()
print([s.metadata.name for s in skills])

# 2. 更明确的任务描述
msg = Message(
    role="user",
    content="使用 pdf_analyzer skill 提取 document.pdf 的文本"  # ✅ 明确提到 skill
)

# 3. 检查系统提示
print(agent.system_prompt)
# 应该包含 Skills 索引
```

### Q3: 依赖包未安装？

**症状**：Agent 尝试使用 Skill 但报错

**解决方法**：

```bash
# PDF Analyzer
pip install PyPDF2 pdfplumber

# Web Research
pip install requests beautifulsoup4

# Data Processor
pip install pandas openpyxl

# 全部安装
pip install PyPDF2 pdfplumber requests beautifulsoup4 pandas openpyxl
```

### Q4: 如何调试 Skill 使用？

**使用事件监控**：

```python
from loom.core.events import AgentEventType

def event_handler(event):
    if event.type == AgentEventType.AGENT_START:
        print(f"🚀 Agent started")
    elif event.type == AgentEventType.TOOL_START:
        tool_name = event.data.get('tool_name')
        print(f"🔧 Calling tool: {tool_name}")
        # 检查是否包含 Bash 工具调用（读取 SKILL.md）
        if tool_name == "bash":
            command = event.data.get('command', '')
            if 'skills/' in command:
                print(f"   📖 Reading Skill: {command}")

agent = loom.agent(
    name="assistant",
    llm=llm,
    enable_skills=True,
    event_handler=event_handler
)

msg = Message(role="user", content="分析 report.pdf")
response = await agent.run(msg)

# 输出会显示 Agent 是否读取了 SKILL.md
```

### Q5: Skill 文档更新后没有生效？

**解决方法**：

```python
# 重新加载 Skills
agent.reload_skills()

# 或者重新创建 Agent
agent = loom.agent(
    name="assistant",
    llm=llm,
    enable_skills=True
)
```

### Q6: 如何查看 Skill 统计信息？

```python
# Agent 统计
stats = agent.get_stats()
print(stats)

# 输出示例：
# {
#   'name': 'assistant',
#   'num_tools': 0,
#   'executor_stats': {...},
#   'skills': {
#       'total_skills': 3,
#       'enabled_skills': 3,
#       'disabled_skills': 0,
#       'categories': 2
#   }
# }
```

### Q7: Skills 占用太多上下文？

**不会！这就是三层架构的优势：**

```python
# 检查系统提示大小
prompt = agent.system_prompt
import tiktoken
encoder = tiktoken.get_encoding("cl100k_base")
tokens = len(encoder.encode(prompt))
print(f"System prompt tokens: {tokens}")

# 3 个 Skills 的索引只占用约 150-200 tokens
# 详细文档只在 Agent 需要时才加载（按需）
```

---

## 下一步

### 深入学习
- [Skills 概述](./overview.md) - Skills 系统完整介绍
- [创建 Skills](./creating-skills.md) - 自定义 Skills
- [Skills 快速参考](./quick-reference.md) - API 速查

### 相关主题
- [SimpleAgent 指南](../agents/simple-agent.md) - Agent 完整功能
- [工具开发](../tools/development.md) - Tools vs Skills
- [事件系统](../advanced/events.md) - 监控 Skills 使用

### 示例
- [示例库](../../examples/) - 完整示例代码
- [Skills 源码](../../../skills/) - 查看内置 Skills 实现

---

## 总结

**内置 Skills 概览**：

| Skill | 功能 | 适用场景 | 主要依赖 |
|-------|------|----------|----------|
| **pdf_analyzer** | PDF 文档分析 | 发票、合同、报告处理 | PyPDF2, pdfplumber |
| **web_research** | Web 信息收集 | 市场研究、竞品分析 | requests, beautifulsoup4 |
| **data_processor** | 结构化数据处理 | 数据清洗、ETL、分析 | pandas, openpyxl |

**关键要点**：
1. **开箱即用**：Skills 默认启用，无需配置
2. **三层架构**：最小化上下文使用（索引 ~150 tokens）
3. **按需加载**：Agent 只在需要时读取详细文档
4. **灵活控制**：可以启用/禁用特定 Skills
5. **易于扩展**：可以添加自定义 Skills

**记住**：Skills 是"知识"，让 Agent 更聪明；Tools 是"能力"，让 Agent 更强大。

---

**开始使用内置 Skills 吧！** 🚀
