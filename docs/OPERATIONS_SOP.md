# Football Prediction System - 运维 SOP (Runbook)

**版本**: V70.300+
**维护者**: DevOps Team
**最后更新**: 2026-01-25

---

## 1. 一键控制中心

### 1.1 control.sh 命令速查

```bash
./scripts/ops/control.sh <command> [options]

Commands:
  start       # 启动编排器守护进程
  stop        # 优雅停止所有服务
  restart     # 重启编排器
  status      # 显示系统状态和健康仪表盘
  health      # 快速健康检查 (JSON 格式)
  repair      # 重置 FAILED 记录以便重试
  logs [N]    # 显示最后 N 行日志 (默认: 50)
  backup      # 创建数据库备份
  clean       # 清理旧日志和临时文件
  help        # 显示帮助信息
```

### 1.2 启动系统

```bash
# 正常启动 (守护进程模式)
./scripts/ops/control.sh start

# 试运行模式 (前台，处理 N 场后停止)
./scripts/ops/control.sh start --limit 10

# 查看启动状态
./scripts/ops/control.sh status
```

**预期输出**:

```
╔══════════════════════════════════════════════════════════════════════════════╗
║          Football Prediction System - Control Center Status                 ║
╚══════════════════════════════════════════════════════════════════════════════╝

[SUCCESS] Orchestrator is running (PID: 12345)

Process Information:
  PID  ELAPSED     %CPU %MEM COMMAND
12345  01:23:45   2.3  1.8  node src/ops/v69_000_pipeline_orchestrator.js daemon
```

### 1.3 停止系统

```bash
# 优雅停止
./scripts/ops/control.sh stop

# 预期输出:
# [INFO] Stopping Football Prediction Orchestrator...
# [SUCCESS] Orchestrator stopped
```

### 1.4 查看系统状态

```bash
# 完整状态仪表盘
./scripts/ops/control.sh status

# 快速健康检查 (JSON)
./scripts/ops/control.sh health
```

**健康检查输出示例**:

```json
{
  "health_score": 95,
  "progress": "78%",
  "corrupted": 3,
  "mph": 120,
  "eta": "2026-01-30"
}
```

---

## 2. 异常处理看板

### 2.1 相似度低于 70%

**症状**: 哈希映射相似度 < 70%，大量记录被拒绝

**诊断步骤**:

```sql
-- 查看相似度分布
SELECT
    confidence,
    COUNT(*) as count,
    ROUND(AVG(similarity_score), 2) as avg_similarity
FROM matches_mapping
GROUP BY confidence
ORDER BY confidence;
```

**处理方案**:

1. **检查队名映射表**

   ```bash
   # 编辑映射表
   vim src/core/team_name_normalizer.py
   ```

2. **调整相似度阈值**

   ```python
   # 在 BridgeEngine 中临时降低阈值
   SIMILARITY_THRESHOLD = 0.65  # 从 0.70 降到 0.65
   ```

3. **运行修复**

   ```bash
   ./scripts/ops/control.sh repair --failed-only
   ```

### 2.2 Payout 异常报警

**症状**: `integrity_score` 不在 1.02-1.08 范围内

**诊断步骤**:

```sql
-- 查看完整性分数分布
SELECT
    CASE
        WHEN integrity_score < 1.02 THEN 'TOO_LOW'
        WHEN integrity_score > 1.08 THEN 'TOO_HIGH'
        ELSE 'VALID'
    END as score_category,
    COUNT(*) as count,
    ROUND(AVG(integrity_score), 4) as avg_score
FROM match_odds_intelligence
WHERE integrity_score IS NOT NULL
GROUP BY score_category
ORDER BY score_category;
```

**处理方案**:

1. **识别异常比赛**

   ```sql
   -- 查看异常记录详情
   SELECT
       moi.match_id,
       m.home_team,
       m.away_team,
       moi.init_h,
       moi.final_h,
       moi.integrity_score
   FROM match_odds_intelligence moi
   JOIN matches m ON m.match_id = moi.match_id
   WHERE moi.integrity_score NOT BETWEEN 1.02 AND 1.08
   ORDER BY moi.integrity_score DESC
   LIMIT 20;
   ```

2. **标记为人工审核**

   ```sql
   -- 更新映射状态
   UPDATE matches_mapping
   SET review_status = 'payout_anomaly'
   WHERE fotmob_id IN (
       SELECT match_id FROM match_odds_intelligence
       WHERE integrity_score NOT BETWEEN 1.02 AND 1.08
   );
   ```

3. **重新采集赔率**

   ```bash
   # 对异常比赛重新采集
   python -m src.harvesters.oddsportal_archive --league "Premier League" --season "2024" --remap
   ```

### 2.3 数据库连接池水位过高

**症状**: 连接池利用率 > 80%

**诊断步骤**:

```bash
# 检查活跃连接数
docker exec football_db psql -U football_user -d football_db -c "
SELECT
    count(*) as active_connections,
    state
FROM pg_stat_activity
WHERE datname = 'football_db'
GROUP BY state;
"
```

**处理方案**:

1. **识别长时间运行的查询**

   ```sql
   SELECT
       pid,
       now() - query_start as duration,
       state,
       query
   FROM pg_stat_activity
   WHERE datname = 'football_db'
     AND state != 'idle'
   ORDER BY duration DESC
   LIMIT 10;
   ```

2. **终止长时间运行的查询**

   ```sql
   -- 谨慎使用！
   SELECT pg_terminate_backend(pid)
   FROM pg_stat_activity
   WHERE pid = <problem_pid>;
   ```

3. **调整连接池配置**

   ```bash
   # 编辑 .env
   DB_POOL_SIZE=20        # 增加连接池大小
   DB_POOL_MAX_OVERFLOW=30  # 增加溢出连接数
   ```

4. **重启服务**

   ```bash
   ./scripts/ops/control.sh restart
   ```

### 2.4 爬虫被检测 (429/403)

**症状**: 频繁出现 HTTP 429 或 403 错误

**诊断步骤**:

```bash
# 查看最近的错误日志
grep -E "429|403|blocked|banned" logs/orchestrator.log | tail -20
```

**处理方案**:

1. **启用 Ghost Protocol**

   ```python
   # 确保使用 GhostBrowser
   from src.core.ghost_protocol import GhostBrowser

   browser = GhostBrowser()
   async with browser.context() as context:
       page = await context.new_page()
       # ... 执行采集 ...
   ```

2. **增加延迟**

   ```python
   # 在采集间隔增加随机延迟
   import asyncio
   import random

   await asyncio.sleep(random.uniform(5, 15))  # 5-15 秒随机延迟
   ```

3. **检查代理配置**

   ```bash
   # 测试代理连通性
   python -c "
   from src.core.proxy_manager import ProxyManager
   pm = ProxyManager()
   print(pm.get_healthy_proxy())
   "
   ```

4. **启用熔断器保护**

   ```python
   # 等待熔断器自动恢复
   from src.core.circuit_breaker import CircuitBreaker

   breaker = CircuitBreaker(
       failure_threshold=3,
       recovery_timeout=300  # 5 分钟
   )
   ```

### 2.5 内存泄漏检测

**症状**: 系统运行一段时间后内存占用持续增长

**诊断步骤**:

```bash
# 查看 Python 进程内存
ps aux | grep python | awk '{print $6}'

# 查看 Docker 容器内存
docker stats --no-stream | grep football
```

**处理方案**:

1. **清理 Python 缓存**

   ```bash
   find . -type d -name "__pycache__" -exec rm -rf {} +
   find . -name "*.pyc" -delete
   ```

2. **清理浏览器进程**

   ```bash
   pkill -f playwright
   pkill -f chromium
   ```

3. **清理 Redis 缓存**

   ```bash
   docker exec football_redis redis-cli FLUSHDB
   ```

4. **重启服务**

   ```bash
   ./scripts/ops/control.sh restart
   ```

---

## 3. 修复操作 (REPAIR)

### 3.1 重置 FAILED 记录

```bash
# 仅修复 FAILED 记录（重置为 DISCOVERED）
./scripts/ops/control.sh repair --failed-only

# 修复 FAILED 记录 + 清理临时文件
./scripts/ops/control.sh repair --cleanup-temp
```

**修复逻辑**:

```
FAILED → DISCOVERED    (重试整个流程)
FAILED → MAPPED       (如果已有哈希映射，跳过 Bridge)
FAILED → ENRICHED     (如果已有 L2 数据，跳过采集)
```

### 3.2 批量修复

```sql
-- 手动批量修复
-- 将所有 FAILED 记录重置为 DISCOVERED
UPDATE match_pipeline_state
SET status = 'DISCOVERED',
    updated_at = NOW(),
    retry_count = COALESCE(retry_count, 0) + 1,
    error_message = NULL
WHERE status = 'FAILED';

-- 查看修复结果
SELECT status, COUNT(*) as count
FROM match_pipeline_state
GROUP BY status
ORDER BY status;
```

---

## 4. 备份与恢复

### 4.1 创建备份

```bash
# 使用 control.sh
./scripts/ops/control.sh backup

# 预期输出:
# [INFO] Creating database backup...
# [SUCCESS] Backup created: data/backups/football_db_20260125_123456.sql
# [SUCCESS] Backup compressed: data/backups/football_db_20260125_123456.sql.gz
```

### 4.2 恢复备份

```bash
# 解压备份
gunzip data/backups/football_db_20260125_123456.sql.gz

# 恢复数据库
docker exec -i football_db psql -U football_user -d football_db < data/backups/football_db_20260125_123456.sql
```

### 4.3 自动备份策略

```bash
# 添加到 crontab (每天凌晨 2 点备份)
0 2 * * * /path/to/FootballPrediction/scripts/ops/control.sh backup
```

---

## 5. 清理操作

### 5.1 清理旧日志

```bash
# 清理 7 天前的日志
./scripts/ops/control.sh clean

# 手动清理
find logs/ -name "*.log" -mtime +7 -delete
```

### 5.2 清理临时文件

```bash
# 清理 Python 缓存
find . -type d -name "__pycache__" -exec rm -rf {} +
find . -name "*.pyc" -delete

# 清理临时文件
find /tmp -name "football_*" -mtime +1 -delete
```

### 5.3 清理旧备份

```bash
# 保留最近 5 个备份，删除其余
find data/backups -name "*.sql.gz" -type f | sort | head -n -5 | xargs rm -f
```

---

## 6. 监控与告警

### 6.1 系统健康检查

```bash
# 完整健康检查
./scripts/ops/control.sh status

# 快速健康检查 (JSON)
./scripts/ops/control.sh health
```

### 6.2 数据质量检查

```bash
# 运行数据质量检查
python -m src.utils.data_quality_checker --full-check
```

### 6.3 性能监控

```bash
# 查看 CPU/内存使用
docker stats --no-stream

# 查看数据库查询性能
docker exec football_db psql -U football_user -d football_db -c "
SELECT
    query,
    calls,
    total_time,
    mean_time,
    max_time
FROM pg_stat_statements
ORDER BY mean_time DESC
LIMIT 10;
"
```

---

## 7. 应急预案

### 7.1 系统完全宕机

```bash
# 1. 检查服务状态
docker-compose ps

# 2. 重启所有服务
docker-compose down
docker-compose up -d

# 3. 验证恢复
./scripts/ops/control.sh status
```

### 7.2 数据库损坏

```bash
# 1. 停止所有服务
./scripts/ops/control.sh stop

# 2. 从最新备份恢复
gunzip data/backups/football_db_YYYYMMDD_HHMMSS.sql.gz
docker-compose down -v
docker-compose up -d
docker exec -i football_db psql -U football_user -d football_db < data/backups/football_db_YYYYMMDD_HHMMSS.sql

# 3. 重启服务
./scripts/ops/control.sh start
```

### 7.3 回滚到稳定版本

```bash
# 1. 查看最近的提交
git log --oneline -10

# 2. 回滚到稳定版本
git checkout <stable-commit-hash>

# 3. 重启服务
./scripts/ops/control.sh restart
```

---

## 8. 运维日历

### 8.1 每日任务

```bash
# 每天凌晨 2 点
0 2 * * * ./scripts/ops/control.sh backup

# 每天早上 9 点
0 9 * * * ./scripts/ops/control.sh status
```

### 8.2 每周任务

```bash
# 每周日凌晨 3 点
0 3 * * 0 ./scripts/ops/control.sh clean

# 每周一早上 10 点
0 10 * * 1 python -m pytest tests/ --cov=src
```

### 8.3 每月任务

```bash
# 每月 1 号凌晨 4 点
0 4 1 * * python -m src.utils.data_quality_checker --full-check
```

---

## 9. V81.200 暴力寻址任务管理

### 9.1 概述

V81.200 Discovery Radar 是系统的**标准长期能力**，用于自动补全 `matches_mapping` 表中缺失的 OddsPortal URL。

**核心特性**:

- **动态桥接**: 静态查表失败 → 自动触发雷达扫描
- **RapidFuzz C++ 引擎**: 高性能模糊匹配（<50ms/次）
- **即时回填**: 验证通过立即 UPSERT 到数据库
- **置信度分级**: >85% 批准, 70-85% 待审, <70% 拒绝

### 9.2 手动触发全量重扫描

```bash
# 方法 1: 使用暴力寻址总攻脚本（推荐）
python3 scripts/ops/v81_200_mapping_blitz.py

# 方法 2: 测试模式（限制处理数量）
python3 scripts/ops/v81_200_mapping_blitz.py --limit 100

# 方法 3: 干跑模式（不回填数据库）
python3 scripts/ops/v81_200_mapping_blitz.py --dry-run
```

**执行输出示例**:

```
================================================================================
V81.200 Mapping Blitz - 暴力寻址总攻启动
================================================================================
获取到 5232 场待映射比赛
开始扫描 5232 场比赛...
Mapping Blitz: 100%|████████████████████| 5232/5232 [01:17<00:00, 68.51it/s]
================================================================================
V81.200 Mapping Blitz - 执行完成
================================================================================
总处理: 5232 场
自动批准: 4821 场 (>85.0%)
待审核: 312 场 (70.0-85.0%)
失败: 99 场 (<70.0%)
映射覆盖率: 98.11%
总耗时: 77.2 秒
================================================================================
```

### 9.3 调整雷达阈值

**配置文件**: `scripts/ops/v81_200_mapping_blitz.py`

```python
BLITZ_CONFIG = {
    # 阈值配置（可调整）
    'auto_approve_threshold': 85.0,  # > 85% 自动批准
    'pending_review_threshold': 70.0,  # 70-85% 待审核
    'min_threshold': 65.0,  # 最低阈值（低于此值不记录）

    # 联赛过滤（可扩展）
    'target_leagues': [
        'Premier League',
        'La Liga',
        'Serie A',
        'Bundesliga',
        'Ligue 1'
        # 添加更多联赛...
    ]
}
```

**阈值调整指南**:

| 场景 | auto_approve | pending_review | min_threshold |
|------|--------------|-----------------|----------------|
| **严格模式** | 90.0 | 80.0 | 70.0 | 高准确性，低覆盖率 |
| **标准模式** (默认) | 85.0 | 70.0 | 65.0 | 平衡准确性和覆盖率 |
| **宽松模式** | 80.0 | 65.0 | 60.0 | 高覆盖率，需人工审核 |

### 9.4 查看雷达统计

```bash
# 查看映射覆盖率
docker-compose exec -T db psql -U football_user -d football_db -c "
SELECT
    league_name,
    COUNT(*) as total_matches,
    COUNT(CASE WHEN oddsportal_url IS NOT NULL THEN 1 END) as with_url,
    ROUND(100.0 * COUNT(CASE WHEN oddsportal_url IS NOT NULL THEN 1 END) / COUNT(*), 2) as coverage_rate
FROM matches m
LEFT JOIN matches_mapping mm ON m.match_id = mm.fotmob_id
WHERE m.league_name IN ('Premier League', 'La Liga', 'Serie A', 'Bundesliga', 'Ligue 1')
GROUP BY m.league_name
ORDER BY coverage_rate DESC;
"
```

### 9.5 审计待审核记录

```bash
# 查看待审核的映射（70-85% 置信度）
docker-compose exec -T db psql -U football_user -d football_db -c "
SELECT
    fotmob_id,
    home_team,
    away_team,
    league_name,
    oddsportal_url,
    ROUND(confidence * 100, 2) as confidence_percent,
    mapping_method,
    review_status
FROM matches_mapping
WHERE review_status = 'pending_review'
ORDER BY confidence DESC
LIMIT 20;
"
```

**批量批准待审核记录**:

```bash
# 批量批准所有待审核记录
docker-compose exec -T db psql -U football_user -d football_db -c "
UPDATE matches_mapping
SET review_status = 'approved'
WHERE review_status = 'pending_review';
"
```

### 9.6 故障排除

| 问题 | 症状 | 解决方案 |
|------|------|----------|
| **扫描速度慢** | >100ms/次 | 检查数据库连接池，增加 `pool_size` |
| **覆盖率低** | <70% | 降低 `min_threshold` 到 60.0 |
| **误报率高** | 待审核太多 | 提高 `auto_approve_threshold` 到 90.0 |
| **队名索引空** | 0 条记录 | 检查 `matches_mapping` 表是否有基础数据 |

### 9.7 性能基准

**V81.200 生产环境性能指标**:

| 指标 | 基准值 | 实际值 | 状态 |
|------|--------|--------|------|
| **单次扫描延迟** | <50ms | ~30ms | ✅ 优秀 |
| **吞吐量** | >60 场/秒 | ~68 场/秒 | ✅ 优秀 |
| **映射覆盖率** | >85% | 98.11% | ✅ 超预期 |
| **准确率** | >95% | 99.8% | ✅ 优秀 |

---

## 10. 联系与支持

### 9.1 技术支持

- **GitHub Issues**: <https://github.com/your-repo/issues>
- **文档中心**: docs/
- **SLA**: 99.5% 可用性

### 9.2 紧急联系

- **值班电话**: +86 XXX XXXX XXXX
- **紧急邮件**: <oncall@example.com>

---

**最后更新**: 2026-01-25
