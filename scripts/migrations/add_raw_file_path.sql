-- 添加原始HTML文件路径字段
-- ELT架构转型 - 原始数据保存支持

-- 为matches表添加raw_file_path字段
ALTER TABLE matches
ADD COLUMN IF NOT EXISTS raw_file_path VARCHAR(512);

-- 添加索引以提高查询性能 (可选)
CREATE INDEX IF NOT EXISTS idx_matches_raw_file_path
ON matches(raw_file_path)
WHERE raw_file_path IS NOT NULL;

-- 添加注释说明
COMMENT ON COLUMN matches.raw_file_path IS '原始HTML文件路径 (ELT架构 - 原始数据保存)';

-- 验证表结构
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns
WHERE table_name = 'matches'
  AND column_name = 'raw_file_path';