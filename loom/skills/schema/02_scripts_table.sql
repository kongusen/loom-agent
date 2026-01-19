-- Loom Skill System - Scripts Table
--
-- 存储Skill的可执行脚本

-- ============================================
-- Scripts表
-- ============================================
CREATE TABLE IF NOT EXISTS skill_scripts (
    id SERIAL PRIMARY KEY,
    skill_id VARCHAR(255) NOT NULL REFERENCES skills(skill_id) ON DELETE CASCADE,
    filename VARCHAR(255) NOT NULL,
    content TEXT NOT NULL,
    script_type VARCHAR(50) DEFAULT 'python',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- 确保同一个skill下的filename唯一
    CONSTRAINT skill_scripts_unique UNIQUE (skill_id, filename)
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_skill_scripts_skill_id ON skill_scripts(skill_id);

-- 注释
COMMENT ON TABLE skill_scripts IS 'Skill脚本存储表';
COMMENT ON COLUMN skill_scripts.skill_id IS '关联的Skill ID';
COMMENT ON COLUMN skill_scripts.filename IS '脚本文件名';
COMMENT ON COLUMN skill_scripts.content IS '脚本内容';
COMMENT ON COLUMN skill_scripts.script_type IS '脚本类型（python/shell/javascript等）';
