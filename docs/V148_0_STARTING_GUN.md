# V148.0 总攻起跑口令
## 🎯 Operation '总攻' - 明日启动协议

**发布时间**: 2026-01-06 14:00 UTC
**启动窗口**: 2026-01-07 00:00 - 06:00 UTC
**目标**: 收割 5884 场比赛数据

---

## 📋 启动检查清单

### Step 1: 起床自检 (5 分钟)

| 序号 | 命令 | 预期结果 | 状态 |
|------|------|----------|------|
| 1.1 | `docker-compose ps` | db 和 redis 都是 Up | ⬜ |
| 1.2 | `docker-compose exec db pg_isready -U football_user` | 返回 "accepting connections" | ⬜ |
| 1.3 | `df -h /home/user/projects/FootballPrediction` | Available > 800GB | ⬜ |
| 1.4 | `ping -c 1 8.8.8.8` | 外网连通 | ⬜ |

**通过标准**: 全部 ✅ 后才能进入 Step 2

---

### Step 2: 开启监控 (1 分钟)

| 序号 | 命令 | 说明 |
|------|------|------|
| 2.1 | `cd /home/user/projects/FootballPrediction` | 进入项目目录 |
| 2.2 | `mkdir -p logs` | 创建日志目录 |
| 2.3 | `nohup python scripts/maintenance/monitor_war_room.py > logs/monitor_war_room.log 2>&1 &` | 启动监控后台 |
| 2.4 | `echo $! > .monitor_war_room.pid` | 保存 PID |

**验证监控启动**:
```bash
tail -f logs/monitor_war_room.log
# 应该看到: 🎯 启动总攻作战室监控仪表盘...
```

**状态**: ⬜ 待执行

---

### Step 3: 启动 OddsPortal 巡航 (2 分钟)

| 序号 | 命令 | 说明 |
|------|------|------|
| 3.1 | `python -m src.api.collectors.odds_production_extractor --source oddsportal --mode cruise --circuit-breaker-enabled --limit 100` | 首波测试 (100场) |
| 3.2 | `tail -f logs/auto_harvest.log` | 观察收割日志 |

**预期输出**:
```
✓ 启动 OddsPortal 终盘赔率收割
✓ 熔断器已启用
✓ 目标: 100 场比赛
```

**状态**: ⬜ 待执行

---

### Step 4: 启动 FotMob L2 回填 (持续)

| 序号 | 命令 | 说明 |
|------|------|------|
| 4.1 | `python scripts/production_harvester.py --mode cruise --source fotmob --l2-version V145.1 --circuit-breaker-enabled` | L2 全量回填 |
| 4.2 | `tail -f logs/auto_harvest.log` | 观察收割日志 |

**预期输出**:
```
✓ 启动 FotMob L2 详情数据收割
✓ L2 数据版本: V145.1
✓ 熔断器已启用
✓ 巡航模式: 自适应速率
```

**状态**: ⬜ 待执行

---

### Step 5: 全速巡航模式 (可选)

**命令**:
```bash
python scripts/production_harvester.py --mode cruise --source all --circuit-breaker-enabled
```

**说明**:
- 同时收割 L1 (FotMob 基础)
- 同时收割 L2 (FotMob 详情)
- 同时收割 L3 (OddsPortal 终盘)
- 智能轮询 + 自适应速率

**状态**: ⬜ 待执行

---

## 🚨 应急响应协议

### 熔断器触发 (EXIT 99)

**症状**:
- 日志显示 "CIRCUIT_BREAKER: IP Hard Ban Detected"
- 收割进程自动退出

**处理**:
```bash
# 1. 确认熔断触发
tail -100 logs/app.log | grep "CIRCUIT_BREAKER"

# 2. 进入冷却期 (6小时)
echo "冷却期: $(date -d '+6 hours' '+%Y-%m-%d %H:%M:%S')"

# 3. 检查 IP 状态
python scripts/diagnose_network.py

# 4. 冷却期结束后手动重启
python scripts/production_harvester.py --mode cruise --source all
```

### 数据库连接失败

**症状**:
- 日志显示 "connection refused"
- pg_isready 返回错误

**处理**:
```bash
# 1. 重启数据库
docker-compose restart db

# 2. 等待启动
sleep 10

# 3. 验证连接
docker-compose exec db pg_isready -U football_user

# 4. 恢复收割
# (收割进程会自动重连)
```

### 磁盘空间不足

**症状**:
- df -h 显示 Used > 90%
- 数据库写入失败

**处理**:
```bash
# 1. 检查空间使用
df -h /home/user/projects/FootballPrediction

# 2. 清理日志
rm -rf logs/*.log

# 3. 数据库真空清理
docker-compose exec db psql -U football_user -d football_db -c "VACUUM FULL;"

# 4. 验证空间
df -h /home/user/projects/FootballPrediction
```

---

## 📊 监控指标

### 实时监控命令

```bash
# 监控仪表盘
tail -f logs/monitor_war_room.log

# 收割进度
tail -f logs/auto_harvest.log | grep -E "收割|Collected|进度"

# 数据库写入
tail -f logs/auto_harvest.log | grep -E "INSERT|UPDATE|upsert"

# IP 健康
tail -f logs/auto_harvest.log | grep -E "IP|ban|circuit"
```

### SQL 查询检查

```bash
# 收割进度
docker-compose exec db psql -U football_user -d football_db -c "
SELECT
    COUNT(*) as total_matches,
    COUNT(l2_raw_json) as l2_collected,
    COUNT(l2_raw_json)::float / COUNT(*) * 100 as l2_coverage_pct
FROM matches
WHERE match_time >= '2024-01-01';
"

# 最近收割活动
docker-compose exec db psql -U football_user -d football_db -c "
SELECT
    DATE_TRUNC('hour', match_time) as hour,
    COUNT(*) as matches_added
FROM matches
WHERE match_time >= NOW() - INTERVAL '24 hours'
GROUP BY hour
ORDER BY hour DESC
LIMIT 12;
"
```

---

## 🎯 成功标准

### 最小可行性产品 (MVP)

| 指标 | 目标 | 当前 |
|------|------|------|
| 收割总数 | > 1000 | 0 |
| L2 覆盖率 | > 80% | 0% |
| 成功率 | > 90% | - |
| IP 健康度 | 零硬封 | - |

### 完整目标 (Full Target)

| 指标 | 目标 | 预计时间 |
|------|------|----------|
| 收割总数 | 5884 | 24-48 小时 |
| L2 覆盖率 | > 90% | - |
| 成功率 | > 95% | - |
| 平均速率 | > 50 场/小时 | - |

---

## 📞 联系方式

**War Room Commander**: Senior SRE
**紧急联系**: @system (24/7)
**备份联系**: @db-admin (工作时间)

---

## 🎉 启动确认

**确认人**: _______________
**确认时间**: _______________
**启动状态**: ⬜ 待启动 / ✅ 已启动 / ⚠️  异常

---

**文档版本**: V148.0-FINAL
**生成时间**: 2026-01-06 14:00 UTC
**状态**: 🎯 READY TO LAUNCH
