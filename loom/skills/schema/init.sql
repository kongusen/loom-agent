-- Loom Skill System - Complete Schema Initialization
--
-- 完整的数据库初始化脚本
-- 执行此脚本将创建所有必需的表

\echo 'Creating Loom Skill System tables...'

-- 1. Skills主表
\i 01_skills_table.sql

-- 2. Scripts表
\i 02_scripts_table.sql

-- 3. References表
\i 03_references_table.sql

-- 4. Tools关联表
\i 04_tools_table.sql

\echo 'Loom Skill System tables created successfully!'
