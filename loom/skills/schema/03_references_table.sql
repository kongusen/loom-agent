-- Loom Skill System - References Table
--
-- 存储Skill的参考资料

-- ============================================
-- References表
-- ============================================
CREATE TABLE IF NOT EXISTS skill_references (
    id SERIAL PRIMARY KEY,
    skill_id VARCHAR(255) NOT NULL REFERENCES skills(skill_id) ON DELETE CASCADE,
    filename VARCHAR(255) NOT NULL,
    content TEXT NOT NULL,
    reference_type VARCHAR(50) DEFAULT 'markdown',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- 确保同一个skill下的filename唯一
    CONSTRAINT skill_references_unique UNIQUE (skill_id, filename)
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_skill_references_skill_id ON skill_references(skill_id);

-- 注释
COMMENT ON TABLE skill_references IS 'Skill参考资料存储表';
COMMENT ON COLUMN skill_references.skill_id IS '关联的Skill ID';
COMMENT ON COLUMN skill_references.filename IS '参考资料文件名';
COMMENT ON COLUMN skill_references.content IS '参考资料内容';
COMMENT ON COLUMN skill_references.reference_type IS '资料类型（markdown/json/text等）';
