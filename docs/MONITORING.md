# V145.1 L2 数据质量监控面板

**版本**: V145.1 Production Gold
**创建日期**: 2026-01-06
**用途**: 生产环境 L2 数据质量实时监控

---

## 📊 核心指标监控

### 1. L2 数据采集概览

```sql
-- 1.1 L2 采集总体统计
SELECT
    COUNT(*) AS total_matches,                          -- 总比赛数
    COUNT(l2_raw_json) AS l2_collected,                 -- L2 已采集数
    COUNT(*) - COUNT(l2_raw_json) AS l2_missing,        -- L2 缺失数
    ROUND(100.0 * COUNT(l2_raw_json) / COUNT(*), 2) AS l2_coverage_pct  -- L2 覆盖率
FROM matches;

-- 预期输出示例：
-- total_matches | l2_collected | l2_missing | l2_coverage_pct
-- --------------|--------------|------------|-----------------
-- 5884          | 3200         | 2684       | 54.38
```

### 2. 数据版本分布

```sql
-- 2.1 L2 数据版本分布
SELECT
    l2_data_version,              -- 数据收割版本
    COUNT(*) AS count,            -- 记录数
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER(), 2) AS pct  -- 占比
FROM matches
WHERE l2_raw_json IS NOT NULL
GROUP BY l2_data_version
ORDER BY count DESC;

-- 预期输出示例：
-- l2_data_version | count | pct
-- -----------------|-------|-----
-- V145.0           | 2000  | 62.50
-- V145.1           | 1200  | 37.50
```

### 3. 数据完整性审计

```sql
-- 3.1 损坏数据检测（< 10KB）
SELECT
    COUNT(*) AS corrupt_records,
    MIN(octet_length(l2_raw_json::text)) AS min_size_bytes,
    MAX(octet_length(l2_raw_json::text)) AS max_size_bytes,
    ROUND(AVG(octet_length(l2_raw_json::text)), 2) AS avg_size_bytes
FROM matches
WHERE l2_raw_json IS NOT NULL
  AND octet_length(l2_raw_json::text) < 10240;  -- 小于 10KB

-- 3.2 正常数据统计（>= 10KB）
SELECT
    COUNT(*) AS valid_records,
    ROUND(AVG(octet_length(l2_raw_json::text)) / 1024, 2) AS avg_size_kb
FROM matches
WHERE l2_raw_json IS NOT NULL
  AND octet_length(l2_raw_json::text) >= 10240;
```

### 4. 数据大小分布

```sql
-- 4.1 L2 数据大小分段统计
SELECT
    CASE
        WHEN octet_length(l2_raw_json::text) < 10240 THEN '小型 (<10KB)'
        WHEN octet_length(l2_raw_json::text) < 102400 THEN '中型 (10-100KB)'
        WHEN octet_length(l2_raw_json::text) < 1048576 THEN '大型 (100KB-1MB)'
        ELSE '超大型 (>=1MB)'
    END AS size_category,
    COUNT(*) AS count,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER(), 2) AS pct
FROM matches
WHERE l2_raw_json IS NOT NULL
GROUP BY size_category
ORDER BY
    CASE size_category
        WHEN '小型 (<10KB)' THEN 1
        WHEN '中型 (10-100KB)' THEN 2
        WHEN '大型 (100KB-1MB)' THEN 3
        ELSE 4
    END;
```

### 5. 联赛维度 L2 覆盖率

```sql
-- 5.1 按联赛统计 L2 采集进度
SELECT
    league_name,
    season,
    COUNT(*) AS total_matches,
    COUNT(l2_raw_json) AS l2_collected,
    ROUND(100.0 * COUNT(l2_raw_json) / COUNT(*), 2) AS l2_coverage_pct
FROM matches
GROUP BY league_name, season
ORDER BY l2_coverage_pct DESC, total_matches DESC;
```

---

## 🔍 详细诊断查询

### 6. 损坏记录明细

```sql
-- 6.1 查看所有损坏记录（< 10KB）
SELECT
    id,
    external_id,
    home_team,
    away_team,
    league_name,
    match_time,
    l2_data_version,
    octet_length(l2_raw_json::text) AS l2_size_bytes,
    pg_size_pretty(octet_length(l2_raw_json::text)) AS l2_size_pretty
FROM matches
WHERE l2_raw_json IS NOT NULL
  AND octet_length(l2_raw_json::text) < 10240
ORDER BY l2_size_bytes ASC
LIMIT 100;
```

### 7. 采集时间分布

```sql
-- 7.1 L2 数据采集时间分布
SELECT
    DATE(l2_collected_at) AS collect_date,
    COUNT(*) AS collected_count
FROM matches
WHERE l2_collected_at IS NOT NULL
GROUP BY DATE(l2_collected_at)
ORDER BY collect_date DESC
LIMIT 30;
```

### 8. JSONB 内容验证

```sql
-- 8.1 验证 L2 JSON 结构完整性
SELECT
    COUNT(*) FILTER (
        WHERE l2_raw_json ? 'header'
        AND l2_raw_json ? 'content'
    ) AS valid_structure,
    COUNT(*) FILTER (
        WHERE NOT (l2_raw_json ? 'header')
        OR NOT (l2_raw_json ? 'content')
    ) AS invalid_structure
FROM matches
WHERE l2_raw_json IS NOT NULL;
```

---

## 📈 性能监控

### 9. 索引使用情况

```sql
-- 9.1 L2 相关索引统计
SELECT
    schemaname,
    tablename,
    indexname,
    idx_scan AS index_scans,
    idx_tup_read AS tuples_read,
    idx_tup_fetch AS tuples_fetched
FROM pg_stat_user_indexes
WHERE tablename = 'matches'
  AND indexname LIKE '%l2%'
ORDER BY idx_scan DESC;
```

### 10. 表存储空间

```sql
-- 10.1 L2 数据存储空间统计
SELECT
    pg_size_pretty(pg_total_relation_size('matches')) AS total_table_size,
    pg_size_pretty(pg_relation_size('matches')) AS table_size,
    pg_size_pretty(pg_total_relation_size('matches') - pg_relation_size('matches')) AS indexes_size,
    (
        SELECT pg_size_pretty(SUM(octet_length(l2_raw_json::text)))
        FROM matches
        WHERE l2_raw_json IS NOT NULL
    ) AS l2_data_size;
```

---

## 🎯 快速诊断命令

### 单命令快速检查

```bash
# 快速检查 L2 覆盖率
psql -h localhost -U football_user -d football_db -c "
SELECT
    COUNT(*) AS total,
    COUNT(l2_raw_json) AS l2_collected,
    ROUND(100.0 * COUNT(l2_raw_json) / COUNT(*), 2) AS pct
FROM matches;
"

# 检查损坏数据数量
psql -h localhost -U football_user -d football_db -c "
SELECT COUNT(*) AS corrupt_count
FROM matches
WHERE l2_raw_json IS NOT NULL
  AND octet_length(l2_raw_json::text) < 10240;
"

# 检查版本分布
psql -h localhost -U football_user -d football_db -c "
SELECT l2_data_version, COUNT(*), ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER(), 2) AS pct
FROM matches
WHERE l2_raw_json IS NOT NULL
GROUP BY l2_data_version
ORDER BY count DESC;
"
```

---

## 🔧 维护操作

### 清理损坏数据

```bash
# 使用清理脚本（预览模式）
python scripts/maintenance/clean_corrupt_l2.py --dry-run --min-size 10

# 实际清理（需要确认）
python scripts/maintenance/clean_corrupt_l2.py --min-size 10

# 查看统计信息
python scripts/maintenance/clean_corrupt_l2.py --stats
```

---

## 📋 监控检查清单

### 每日检查项

- [ ] L2 覆盖率 > 50%
- [ ] 损坏数据 (< 10KB) < 1%
- [ ] 数据版本分布合理（单一版本 > 90%）
- [ ] 采集时间分布正常（最近 7 天有数据）

### 每周检查项

- [ ] 运行完整数据质量报告
- [ ] 检查索引使用情况
- [ ] 分析存储空间增长趋势

### 每月检查项

- [ ] 清理历史损坏数据
- [ ] 优化索引策略
- [ ] 归档过期数据

---

**V145.1 Production Gold | 监控面板版本: 1.0.0**
**维护者: Senior Big Data Architect**
**更新时间: 2026-01-06**
