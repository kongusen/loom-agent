-- Loom Skill System - Tools Table
--
-- 存储Skill需要的工具列表

-- ============================================
-- Tools关联表
-- ============================================
CREATE TABLE IF NOT EXISTS skill_tools (
    id SERIAL PRIMARY KEY,
    skill_id VARCHAR(255) NOT NULL REFERENCES skills(skill_id) ON DELETE CASCADE,
    tool_name VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- 确保同一个skill下的tool_name唯一
    CONSTRAINT skill_tools_unique UNIQUE (skill_id, tool_name)
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_skill_tools_skill_id ON skill_tools(skill_id);
CREATE INDEX IF NOT EXISTS idx_skill_tools_tool_name ON skill_tools(tool_name);

-- 注释
COMMENT ON TABLE skill_tools IS 'Skill工具关联表';
COMMENT ON COLUMN skill_tools.skill_id IS '关联的Skill ID';
COMMENT ON COLUMN skill_tools.tool_name IS '工具名称';
