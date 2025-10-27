# SQL 模板 Agent（接入 Doris）

该示例展示如何在 Loom Agent 0.0.2 中结合 `ContextAssembler`、`TaskTool` 与
真实 Doris 元数据/查询工具来生成覆盖整份报告模板的 SQL。

## 功能亮点

- 从 `examples/agents/模板.md` 动态读取中文模板，解析所有占位符。
- 连接 Doris (`192.168.31.160:9030`) 获取 `retail_db` 库的真实表结构。
- 提供 `schema_lookup` 与 `doris_select` 两个工具供主代理和子代理共用。
- 通过 `TaskTool` 启动占位符子代理，结合 `tt` 递归流完成分析→SQL 生成闭环。

## 目录结构

| 文件 | 说明 |
| --- | --- |
| `config.py` | 模板路径、Doris 连接信息、任务约束。 |
| `context_builder.py` | 使用 `ContextAssembler` 组装模板、占位符、schema 等上下文。 |
| `metadata.py` | Doris 元数据访问封装（information_schema 查询）。 |
| `tools.py` | `schema_lookup` 与 `doris_select` 工具实现。 |
| `llms.py` | 基于 `test_new_features.GPT4oMiniLLM` 的 LLM 工厂，可读取环境变量覆盖。 |
| `agent.py` | 主代理 + 子代理构建工厂，注入工具与系统提示。 |
| `runner.py` | CLI 入口，加载模板→拉取 schema→执行 agent→输出最终 SQL。 |

## 运行前准备

1. 确认 `test_new_features.py` 中的 `GPT4oMiniLLM` 可用，或设置环境变量：
   ```bash
   export LOOM_XIAOAI_API_KEY="你的密钥"
   export LOOM_XIAOAI_BASE_URL="https://xiaoai.plus/v1"
   ```
2. 保证当前机器可以访问 Doris：`192.168.31.160:9030`（MySQL 协议）和 `8030`（HTTP 前端）。
3. 安装依赖（项目虚拟环境下已预装 `pymysql`）：
   ```bash
   .venv/bin/pip install pymysql
   ```

## 运行示例

```bash
PYTHONPATH=. .venv/bin/python -m examples.agents.sql_template_agent.runner
```

运行过程中可以看到：

1. coordinator Agent 读取模板与占位符后，主动调用 `TaskTool`。
2. 占位符子代理使用 `schema_lookup`、`doris_select` 探查表结构或试算。
3. 主代理整合子代理输出并生成最终 SQL（`
```sql` 代码块内展示）。

## 更换模板

1. 打开 `examples/agents/模板.md`，按 `{{类别：描述}}` 的格式新增或修改占位符。
2. 运行时 `context_builder.parse_placeholders` 会自动解析，无需改动代码。
3. 如果模板变长，可在 `context_builder.build_coordinator_prompt` 中调整 `max_tokens`
   或组件优先级，保证关键信息不会被截断。

## 更换数据源

1. 编辑 `examples/agents/sql_template_agent/config.py` 中的 `DATA_SOURCE`：
   ```python
   DATA_SOURCE = DorisConnectionConfig(
       hosts=["<新的 FE IP>"],
       http_port=8030,
       mysql_port=9030,
       database="your_db",
       user="xxx",
       password="yyy",
   )
   ```
2. 如需同时切换到 MySQL/ClickHouse 等其他语法，可以保持工具不变；
   只要信息模式兼容，`SchemaLookupTool` 会自动读取表结构。
3. 若需要新增表过滤、列黑白名单等逻辑，可在 `metadata.DorisSchemaExplorer`
   或 `tools.SchemaLookupTool` 中扩展。

## 进一步扩展

- `metadata.py`：加入列级统计、分区信息或数据血缘，帮助 LLM 做更精确决策。
- `tools.py`：添加更多工具（如 metrics dictionary、business glossary）供 LLM 调用。
- `agent.py`：调整系统提示、权限策略或最大迭代次数，适配不同复杂度的任务。
