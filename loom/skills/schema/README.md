# Loom Skill System - Database Schema

## 快速开始

### 1. 初始化数据库

```bash
# PostgreSQL
psql -U your_user -d your_database -f schema/init.sql

# 或者逐个执行
psql -U your_user -d your_database -f schema/01_skills_table.sql
psql -U your_user -d your_database -f schema/02_scripts_table.sql
psql -U your_user -d your_database -f schema/03_references_table.sql
psql -U your_user -d your_database -f schema/04_tools_table.sql
```

### 2. 插入示例数据（可选）

```bash
psql -U your_user -d your_database -f schema/example_data.sql
```

## 表结构

### skills（主表）
- `skill_id`: Skill唯一标识
- `name`: Skill名称
- `description`: 描述（用于激活判断）
- `activation_criteria`: 激活条件
- `instructions`: 执行指令（Markdown）
- `metadata`: 元数据（JSONB）

### skill_scripts（脚本表）
- `skill_id`: 关联的Skill
- `filename`: 脚本文件名
- `content`: 脚本内容
- `script_type`: 脚本类型

### skill_references（参考资料表）
- `skill_id`: 关联的Skill
- `filename`: 文件名
- `content`: 内容
- `reference_type`: 资料类型

### skill_tools（工具关联表）
- `skill_id`: 关联的Skill
- `tool_name`: 工具名称

## 使用示例

```python
from loom.skills import DatabaseSkillLoader, SkillRegistry
import asyncpg

# 连接数据库
conn = await asyncpg.connect('postgresql://user:pass@localhost/db')

# 创建加载器
loader = DatabaseSkillLoader(conn)
registry = SkillRegistry()
registry.register_loader(loader)

# 使用
skills = await registry.get_all_skills()
```
