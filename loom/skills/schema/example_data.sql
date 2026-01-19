-- Loom Skill System - Example Data
--
-- 示例Skill数据，展示如何插入完整的Skill

-- 插入一个示例Skill
INSERT INTO skills (skill_id, name, description, activation_criteria, instructions, metadata)
VALUES (
    'example_calculator',
    'Calculator Skill',
    'Perform mathematical calculations',
    'When user asks to calculate or compute numbers',
    E'# Calculator Skill\n\n## Purpose\nPerform mathematical calculations for the user.\n\n## Steps\n1. Parse the mathematical expression\n2. Calculate the result\n3. Return the answer\n\n## Expected Output\nA clear numerical result',
    '{"version": "1.0", "author": "Loom Framework"}'::jsonb
);

-- 插入脚本
INSERT INTO skill_scripts (skill_id, filename, content, script_type)
VALUES (
    'example_calculator',
    'calculate.py',
    E'def calculate(expression):\n    """Calculate mathematical expression"""\n    return eval(expression)',
    'python'
);

-- 插入参考资料
INSERT INTO skill_references (skill_id, filename, content, reference_type)
VALUES (
    'example_calculator',
    'examples.md',
    E'# Examples\n\n## Example 1\nInput: 2 + 2\nOutput: 4\n\n## Example 2\nInput: 10 * 5\nOutput: 50',
    'markdown'
);

-- 插入需要的工具
INSERT INTO skill_tools (skill_id, tool_name)
VALUES
    ('example_calculator', 'python_executor'),
    ('example_calculator', 'math_validator');
