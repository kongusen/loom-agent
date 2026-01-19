-- Loom Skill System - PostgreSQL Schema
--
-- 这个Schema定义了Skill系统的数据库结构
-- 支持动态配置和管理Skills

-- ============================================
-- 主表：skills
-- ============================================
CREATE TABLE IF NOT EXISTS skills (
    skill_id VARCHAR(255) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    activation_criteria TEXT,
    instructions TEXT NOT NULL,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- 索引
    CONSTRAINT skills_name_unique UNIQUE (name)
);

-- 为常用查询创建索引
CREATE INDEX IF NOT EXISTS idx_skills_name ON skills(name);
CREATE INDEX IF NOT EXISTS idx_skills_created_at ON skills(created_at DESC);

-- 添加注释
COMMENT ON TABLE skills IS 'Skill定义主表';
COMMENT ON COLUMN skills.skill_id IS 'Skill唯一标识';
COMMENT ON COLUMN skills.name IS 'Skill名称';
COMMENT ON COLUMN skills.description IS 'Skill描述（用于激活判断）';
COMMENT ON COLUMN skills.activation_criteria IS '激活条件（何时使用此Skill）';
COMMENT ON COLUMN skills.instructions IS '执行指令（Markdown格式）';
COMMENT ON COLUMN skills.metadata IS '其他元数据（JSONB格式）';
