-- V55.0 多维度数据矩阵提取引擎 - 数据库表结构
-- ============================================================
--
-- 功能: 存储多个数据源的初盘/终赔数值矩阵
-- 支持数据源: Entity_P, Entity_WH, Entity_LB, Entity_B3, Entity_AVG
--
-- Author: Senior Data Engineer
-- Version: V55.0
-- Date: 2026-01-01

-- 创建多源数据矩阵表
CREATE TABLE IF NOT EXISTS metrics_multi_source_data (
    -- 主键关联
    match_id INTEGER NOT NULL,
    source_name TEXT NOT NULL,

    -- 初盘数据 (Initial Values - 从 title 属性提取)
    init_h NUMERIC,
    init_d NUMERIC,
    init_a NUMERIC,

    -- 终赔数据 (Final Values - 页面可见文本)
    final_h NUMERIC,
    final_d NUMERIC,
    final_a NUMERIC,

    -- 完整性审计分数 (1/P1 + 1/P2 + 1/P3)
    -- 有效范围: 1.02 < integrity_score < 1.08
    integrity_score NUMERIC,

    -- 元数据
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- 联合唯一索引: 同一场比赛的同一数据源只能有一条记录
    CONSTRAINT UNIQUE_multisource_match_source UNIQUE (match_id, source_name)
);

-- 创建索引以优化查询性能
CREATE INDEX IF NOT EXISTS idx_multisource_match_id ON metrics_multi_source_data(match_id);
CREATE INDEX IF NOT EXISTS idx_multisource_source_name ON metrics_multi_source_data(source_name);
CREATE INDEX IF NOT EXISTS idx_multisource_integrity ON metrics_multi_source_data(integrity_score);

-- 添加注释
COMMENT ON TABLE metrics_multi_source_data IS 'V55.0 多维度数据矩阵 - 存储多个数据源的初盘/终赔数据';
COMMENT ON COLUMN metrics_multi_source_data.match_id IS '关联比赛 ID (外部键)';
COMMENT ON COLUMN metrics_multi_source_data.source_name IS '数据源名称 (Entity_P, Entity_WH, Entity_LB, Entity_B3, Entity_AVG)';
COMMENT ON COLUMN metrics_multi_source_data.init_h IS '初盘主胜赔率';
COMMENT ON COLUMN metrics_multi_source_data.init_d IS '初盘平局赔率';
COMMENT ON COLUMN metrics_multi_source_data.init_a IS '初盘客胜赔率';
COMMENT ON COLUMN metrics_multi_source_data.final_h IS '终盘主胜赔率 (页面可见)';
COMMENT ON COLUMN metrics_multi_source_data.final_d IS '终盘平局赔率 (页面可见)';
COMMENT ON COLUMN metrics_multi_source_data.final_a IS '终盘客胜赔率 (页面可见)';
COMMENT ON COLUMN metrics_multi_source_data.integrity_score IS '完整性审计分数 (1/P1 + 1/P2 + 1/P3), 有效范围 1.02-1.08';
COMMENT ON COLUMN metrics_multi_source_data.created_at IS '记录创建时间';
COMMENT ON COLUMN metrics_multi_source_data.updated_at IS '记录更新时间';

-- 创建更新时间戳触发器
CREATE OR REPLACE FUNCTION update_multisource_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_update_multisource_timestamp ON metrics_multi_source_data;
CREATE TRIGGER trigger_update_multisource_timestamp
    BEFORE UPDATE ON metrics_multi_source_data
    FOR EACH ROW
    EXECUTE FUNCTION update_multisource_timestamp();

-- 数据有效性检查视图
CREATE OR REPLACE VIEW v55_0_valid_multisource_data AS
SELECT
    match_id,
    source_name,
    init_h, init_d, init_a,
    final_h, final_d, final_a,
    integrity_score,
    CASE
        WHEN integrity_score BETWEEN 1.02 AND 1.08 THEN 'VALID'
        ELSE 'INVALID'
    END AS validation_status
FROM metrics_multi_source_data
WHERE final_h IS NOT NULL
  AND final_d IS NOT NULL
  AND final_a IS NOT NULL;

COMMENT ON VIEW v55_0_valid_multisource_data IS 'V55.0 多源数据有效性检查视图';
