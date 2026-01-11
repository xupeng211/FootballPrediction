# ⚽ FootballPrediction V151.3 快速参考卡片

## 📊 当前状态快照 (2026-01-11)

```
英超数据分布:
├── matches 表: 2,086 场 (源头数据)
├── matches_mapping 表: 2,247 场
│   ├── 待获取哈希 URL: 1,868 场 ⚠️ 优先处理
│   ├── 待采集 (有 URL): 247 场 ✅ 可立即采集
│   └── 已完成采集: 132 场
```

---

## 🚀 一键执行命令

### 方案 A: 全自动补齐计划 (推荐)
```bash
./scripts/ops/v151_premier_full_plan.sh
```
> 自动完成哈希狩猎 + 并发收割，直到采集率 > 60%

---

### 方案 B: 分步执行

**第 1 步：快速验证 (2 分钟)**
```bash
# 检查环境
docker-compose exec db pg_isready -U football_user -d football_db

# 查看状态
./scripts/ops/v151_status_dashboard.sh
```

**第 2 步：哈希狩猎 (3-4 小时)**
```bash
# 单次测试 (10 场)
python scripts/ops/hunt_league_hashes.py --premier --limit 10 --delay-min 5 --delay-max 10

# 正式执行 (200 场/批)
python scripts/ops/hunt_league_hashes.py --premier --limit 200 --delay-min 5 --delay-max 10
```

**第 3 步：并发收割 (持续运行)**
```bash
# 单次测试 (50 场)
python scripts/ops/harvest_pinnacle_concurrent.py --workers 3 --limit 50

# 正式执行 (200 场/批)
python scripts/ops/harvest_pinnacle_concurrent.py --workers 3 --limit 200
```

---

### 方案 C: 手动调试

**查看日志**
```bash
# 哈希狩猎日志
tail -f logs/hunt_league_hashes.log

# 并发收割日志
tail -f logs/harvest_pinnacle_concurrent.log

# Worker 进程日志
tail -f logs/harvest_worker_7890.log
```

**数据库查询**
```bash
docker-compose exec db psql -U football_user -d football_db

# 查看待采集队列
SELECT fotmob_id, home_team, away_team, status
FROM matches_mapping
WHERE league_name = 'Premier League' AND oddsportal_url IS NOT NULL AND l2_raw_json IS NULL
ORDER BY updated_at DESC
LIMIT 10;

# 查看重试分布
SELECT retry_count, COUNT(*)
FROM matches_mapping
WHERE league_name = 'Premier League' AND status IN ('malformed', 'abandoned')
GROUP BY retry_count;
```

---

## 🎯 关键指标

| 指标 | 当前值 | 目标值 |
|------|--------|--------|
| 待获取 URL | 1,868 场 | 0 |
| 待采集 | 247 场 | - |
| 已完成 | 132 场 | > 60% |
| 采集率 | ~6% | > 60% |

---

## ⚠️ 故障排查

| 问题 | 解决方案 |
|------|----------|
| 数据库连接失败 | `make up` |
| 代理不可用 | 检查 Windows 代理软件是否允许局域网连接 |
| 连续 10 场失败 | 检查代理 IP 是否被封，等待 30 分钟冷却 |
| 缓存未同步 | `python scripts/ops/hunt_league_hashes.py --sync-cache` |

---

## 📝 版本信息

- **V151.1**: Hash Hunting Edition
- **V151.3**: Concurrent Harvester + Cache Protection
- **V30.2**: Harvester Supervisor (Auto-restart + Circuit Breaker)

---

## 🔗 相关文件

```
scripts/ops/
├── v151_premier_full_plan.sh          # 全自动补齐计划 ⭐
├── hunt_league_hashes.py              # 哈希猎人
├── harvest_pinnacle_concurrent.py     # 并发收割器
├── harvester_supervisor.py            # 守护进程
└── v151_status_dashboard.sh           # 状态仪表盘

logs/
├── hunt_league_hashes.log             # 哈希狩猎日志
├── harvest_pinnacle_concurrent.log    # 并发收割日志
├── harvest_worker_*.log               # Worker 进程日志
├── hash_hunt_cache.json               # 哈希缓存
└── concurrent_harvest_report.json     # 采集报告
```

---

*最后更新: 2026-01-11*
