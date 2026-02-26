# V51.1 特征库维护手册 (Maintenance Runbook)

**版本**: V51.1
**发布日期**: 2025-12-31
**维护团队**: ML Platform Team

---

## 目录

1. [快速响应](#快速响应)
2. [日常运维](#日常运维)
3. [故障排查](#故障排查)
4. [性能优化](#性能优化)
5. [应急处理](#应急处理)

---

## 快速响应

### 手动触发全量 9000 场计算

**场景**: 新增比赛数据需要重新计算特征

**单进程模式**（约 3 小时）:
```bash
cd /home/user/projects/FootballPrediction
PYTHONPATH=. python -m scripts.ml.v51_1_rolling_feature_engine --limit 9000
```

**多进程并行模式**（约 25 分钟，推荐）:
```bash
cd /home/user/projects/FootballPrediction
PYTHONPATH=. python -m scripts.ml.v51_1_rolling_feature_engine \
    --limit 9000 \
    --parallel \
    --processes 8
```

**一键重建脚本**（最简单）:
```bash
cd /home/user/projects/FootballPrediction
bash scripts/ml/rebuild_all_features.sh
```

---

### 指定联赛计算

**场景**: 只更新特定联赛的特征

```bash
PYTHONPATH=. python -m scripts.ml.v51_1_rolling_feature_engine \
    --limit 1000 \
    --league "Premier League"
```

---

## 日常运维

### 数据质量监控

**每日健康检查**:
```bash
# 1. 检查数据量
docker-compose exec -T db psql -U football_user -d football_prediction_dev -c "
SELECT
    'prematch_features' AS table_name,
    COUNT(*) AS total_records,
    COUNT(CASE WHEN is_valid THEN 1 END) AS valid_records,
    ROUND(AVG(home_history_count), 2) AS avg_home_history,
    ROUND(AVG(away_history_count), 2) AS avg_away_history
FROM prematch_features;
"

# 2. 检查特征覆盖度
docker-compose exec -T db psql -U football_user -d football_prediction_dev -c "
SELECT
    'Feature Coverage' AS metric,
    ROUND(COUNT(home_rolling_xg) * 100.0 / COUNT(*), 2) AS xg_pct,
    ROUND(COUNT(home_recent_form_points) * 100.0 / COUNT(*), 2) AS form_pct,
    ROUND(COUNT(home_fatigue_index) * 100.0 / COUNT(*), 2) AS fatigue_pct
FROM prematch_features;
"

# 3. 检查最新数据时间
docker-compose exec -T db psql -U football_user -d football_prediction_dev -c "
SELECT
    MAX(match_date) AS latest_match_date,
    COUNT(*) AS matches_last_7_days
FROM prematch_features
WHERE match_date >= CURRENT_DATE - INTERVAL '7 days';
"
```

---

### 增量更新

**场景**: 每天新增少量比赛，只需增量计算

```bash
# 1. 查询最新计算时间
LATEST_DATE=$(docker-compose exec -T db psql -U football_user -d football_prediction_dev -t -c "
SELECT MAX(match_date)::date FROM prematch_features;
" | tr -d ' ')

# 2. 查询该时间之后的新比赛
NEW_MATCHES=$(docker-compose exec -T db psql -U football_user -d football_prediction_dev -t -c "
SELECT COUNT(*) FROM matches
WHERE status = 'finished'
  AND match_date > '$LATEST_DATE';
" | tr -d ' ')

# 3. 增量计算新比赛
echo "发现 $NEW_MATCHES 场新比赛，开始增量计算..."
PYTHONPATH=. python -m scripts.ml.v51_1_rolling_feature_engine \
    --limit "$NEW_MATCHES"
```

---

## 故障排查

### 数据库连接超时

**症状**:
```
psycopg2.OperationalError: server closed the connection unexpectedly
```

**诊断步骤**:

1. **检查数据库容器状态**:
```bash
docker-compose ps db
```

2. **检查数据库连接数**:
```bash
docker-compose exec -T db psql -U football_user -d football_prediction_dev -c "
SELECT
    COUNT(*) AS active_connections,
    (SELECT setting::int FROM pg_settings WHERE name = 'max_connections') AS max_connections
FROM pg_stat_activity
WHERE state = 'active';
"
```

3. **检查长时间运行的查询**:
```bash
docker-compose exec -T db psql -U football_user -d football_prediction_dev -c "
SELECT
    pid,
    now() - query_start AS duration,
    state,
    query
FROM pg_stat_activity
WHERE state = 'active'
  AND now() - query_start > interval '5 minutes'
ORDER BY duration DESC;
"
```

**解决方案**:

1. **增加连接池大小** (编辑 `src/config_unified.py`):
```python
database = DatabaseConfig(
    ...
    pool_size=20,  # 增加到 20
    max_overflow=10,
)
```

2. **启用连接持久化** (编辑计算引擎):
```python
# 在 batch_calculate() 中复用连接
def batch_calculate(self, limit=None, league_name=None):
    conn = self.get_connection()
    try:
        # 批量处理时保持连接
        for match in matches:
            self.calculate_prematch_features(..., conn=conn)
    finally:
        conn.close()
```

3. **重启数据库** (最后手段):
```bash
docker-compose restart db
# 等待数据库恢复
sleep 10
# 验证连接
docker-compose exec db pg_isready -U football_user
```

---

### 特征计算结果为 NULL

**症状**: `home_rolling_xg` 等字段为 NULL

**诊断步骤**:

1. **检查 raw_data 是否有数据**:
```bash
docker-compose exec -T db psql -U football_user -d football_prediction_dev -c "
SELECT
    m.match_id,
    m.home_team,
    r.raw_data ? 'stats' AS has_stats,
    (r.raw_data->'stats') ? 'xg' AS has_xg,
    jsonb_typeof(r.raw_data->'stats'->'xg') AS xg_type
FROM matches m
INNER JOIN raw_match_data r ON m.match_id = r.match_id
WHERE m.match_id = '4507126';
"
```

2. **检查数组格式是否正确**:
```bash
docker-compose exec -T db psql -U football_user -d football_prediction_dev -c "
SELECT
    r.raw_data->'stats'->>'xg' AS xg_array,
    r.raw_data->'stats'->>'possession' AS possession_array
FROM matches m
INNER JOIN raw_match_data r ON m.match_id = r.match_id
WHERE m.match_id = '4507126';
"
```

3. **检查历史比赛数量**:
```bash
docker-compose exec -T db psql -U football_user -d football_prediction_dev -c "
WITH target_match AS (
    SELECT match_id, match_date, home_team
    FROM matches
    WHERE match_id = '4507126'
)
SELECT
    COUNT(*) AS history_count,
    MIN(m.match_date) AS earliest_history,
    MAX(m.match_date) AS latest_history
FROM target_match t
INNER JOIN matches m ON (
    (m.home_team = t.home_team OR m.away_team = t.home_team)
    AND m.match_date < t.match_date
    AND m.status = 'finished'
);
"
```

**解决方案**:

1. **如果 raw_data 格式错误**:
```bash
# 重新采集数据
python -m experiments.marrow_cleaning_v37_harvester --match-id 4507126
```

2. **如果历史数据不足**:
```bash
# 设置 min_history 参数降低要求
PYTHONPATH=. python -m scripts.ml.v51_1_rolling_feature_engine \
    --limit 100
# 然后修改代码中的 min_history=5 改为 min_history=3
```

---

### 内存溢出 (OOM)

**症状**:
```
MemoryError: Killed worker
```

**解决方案**:

1. **减少进程数**:
```bash
# 从 8 进程减少到 4 进程
PYTHONPATH=. python -m scripts.ml.v51_1_rolling_feature_engine \
    --parallel \
    --processes 4
```

2. **分批处理**:
```bash
# 每次处理 1000 场
for i in {1..9}; do
    echo "Processing batch $i..."
    PYTHONPATH=. python -m scripts.ml.v51_1_rolling_feature_engine \
        --limit 1000
    sleep 5
done
```

3. **增加 Docker 内存限制** (编辑 `docker-compose.yml`):
```yaml
services:
  pipeline_worker:
    mem_limit: 4g  # 增加到 4GB
```

---

## 性能优化

### 数据库查询优化

**1. 创建函数索引**:
```sql
-- 加速时空隔离查询
CREATE INDEX idx_matches_temporal_lookup
ON matches(match_date DESC, home_team, away_team)
WHERE status = 'finished';

-- 加速历史比赛查询
CREATE INDEX idx_matches_team_history
ON matches(home_team, match_date DESC)
WHERE status = 'finished';
```

**2. 启用查询缓存**:
```python
# 在 PreMatchFeatureCalculator 中添加
from functools import lru_cache

@lru_cache(maxsize=1000)
def get_team_history_cached(self, team_name, before_match_time):
    return self.get_team_history(team_name, before_match_time)
```

---

### 计算引擎优化

**1. 批量查询**:
```python
# 一次性查询所有需要的历史数据
def batch_get_team_history(self, team_names, before_match_time):
    # 使用 WHERE IN 查询多个球队
    ...
```

**2. 预加载 raw_data**:
```python
# 预先将 raw_data 加载到内存
def preload_raw_data(self, match_ids):
    conn = self.get_connection()
    ...
```

---

## 应急处理

### 回滚到上一版本

**场景**: V51.1 计算结果有严重问题

```bash
# 1. 停止计算进程
pkill -f v51_1_rolling_feature_engine

# 2. 备份当前数据
docker-compose exec db pg_dump -U football_user football_prediction_dev \
    > backup_$(date +%Y%m%d)_prematch_features.sql

# 3. 清空错误数据
docker-compose exec -T db psql -U football_user -d football_prediction_dev -c "
TRUNCATE TABLE prematch_features;
"

# 4. 恢复旧版本代码
git checkout HEAD~1 scripts/ml/v51_1_rolling_feature_engine.py

# 5. 重新计算
PYTHONPATH=. python -m scripts.ml.v51_1_rolling_feature_engine --limit 9000
```

---

### 数据修复

**场景**: 部分比赛特征计算错误

```bash
# 1. 删除错误数据
docker-compose exec -T db psql -U football_user -d football_prediction_dev -c "
DELETE FROM prematch_features
WHERE match_id IN ('4507126', '4535602', '4535605');
"

# 2. 重新计算指定比赛
PYTHONPATH=. python -c "
from scripts.ml.v51_1_rolling_feature_engine import PreMatchFeatureCalculator

calc = PreMatchFeatureCalculator()
match_ids = ['4507126', '4535602', '4535605']

for mid in match_ids:
    # 查询比赛信息
    ...
    # 重新计算
    features = calc.calculate_prematch_features(...)
    calc.save_to_database(features)
"
```

---

## 监控告警

### 关键指标

| 指标 | 阈值 | 告警级别 |
|------|------|----------|
| 计算成功率 | < 95% | WARNING |
| 特征覆盖率 | < 90% | CRITICAL |
| 数据库连接数 | > 80% max_connections | WARNING |
| 单次计算耗时 | > 5 秒/场 | INFO |

### 告警配置

```python
# src/ops/alert_manager.py
from src.ops.alert_manager import send_alert_sync, AlertSeverity

# 计算完成后的告警
if stats['failed'] / stats['total'] > 0.05:
    send_alert_sync(
        severity=AlertSeverity.WARNING,
        title="V51.1 特征计算失败率过高",
        message=f"失败率: {stats['failed']/stats['total']*100:.2f}%",
        metadata={
            "total": stats['total'],
            "failed": stats['failed'],
            "success": stats['success']
        }
    )
```

---

## 附录

### 相关文档

- [V51_DATA_SCHEMA.md](V51_DATA_SCHEMA.md) - 数据架构文档
- [CHANGELOG.md](CHANGELOG.md) - 版本变更记录

### 联系方式

| 角色 | 联系方式 |
|------|----------|
| Platform Lead | platform-lead@example.com |
| DBA | dba-team@example.com |
| On-Call | on-call@example.com |

---

**文档维护**: ML Platform Team
**最后更新**: 2025-12-31
