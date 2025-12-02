-- 创建临时宽表 - 首席数据库架构师
-- 用途：快速加载CSV数据，后续进行ETL转换

-- 删除临时表（如果存在）
DROP TABLE IF EXISTS stg_fbref_matches;

-- 创建临时表，所有字段都是TEXT，对应CSV列名
CREATE TABLE stg_fbref_matches (
    wk TEXT,
    "Day" TEXT,
    "Date" TEXT,
    "Time" TEXT,
    "Home" TEXT,
    "xG" TEXT,
    "Score" TEXT,
    "xG.1" TEXT,
    "Away" TEXT,
    "Attendance" TEXT,
    "Venue" TEXT,
    "Referee" TEXT,
    "Match Report" TEXT,
    "Notes" TEXT,
    source_file TEXT,
    loaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    processed BOOLEAN DEFAULT FALSE
);

-- 创建索引提升查询性能
CREATE INDEX ON stg_fbref_matches ("Home");
CREATE INDEX ON stg_fbref_matches ("Away");
CREATE INDEX ON stg_fbref_matches ("Date");
CREATE INDEX ON stg_fbref_matches (processed);
CREATE INDEX ON stg_fbref_matches (loaded_at);

COMMENT ON TABLE stg_fbref_matches IS 'FBref CSV数据临时存储表';
COMMENT ON COLUMN stg_fbref_matches.source_file IS '源CSV文件名';
COMMENT ON COLUMN stg_fbref_matches.processed IS '是否已处理到正式表';

-- 清理现有数据（如果需要）
TRUNCATE TABLE stg_fbref_matches;