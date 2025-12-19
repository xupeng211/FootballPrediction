# 🏆 FootballPrediction v2.3.1 - 每日巡检清单

> **版本**: v2.3.1
> **更新**: 2025-12-19
> **适用**: 生产环境监控
> **用时**: 5分钟

---

## ⚡ 快速检查 (< 3分钟)

### 1. 容器健康检查 (30秒)
```bash
# 检查所有服务状态
docker-compose ps --format table | grep -E "(app|db|redis)"

# 预期输出: 所有服务显示 (healthy)
# ✅ footballprediction-app     Up (healthy)
# ✅ footballprediction-db        Up (healthy)
# ✅ footballprediction-redis      Up (healthy)
```

### 2. 自动化守护进程检查 (30秒)
```bash
# 查看守护进程最新状态
docker logs footballprediction-app --tail 10 | grep -E "(预测成功|守护进程|等待.*秒)"

# 预期输出: 看到最新的预测记录
# ✅ 预测成功: HOME_WIN
# ⏰ 等待 899.1 秒后执行下次预测
```

### 3. 预测数据库检查 (1分钟)
```bash
# 检查今日预测统计
docker exec footballprediction-db psql -U football_user -d football_prediction_shadow -c "
SELECT
    COUNT(*) as today_predictions,
    AVG(confidence)::numeric(3,2) as avg_confidence,
    COUNT(CASE WHEN prediction = 'HOME_WIN' THEN 1 END) as home_wins,
    COUNT(CASE WHEN prediction = 'DRAW' THEN 1 END) as draws,
    COUNT(CASE WHEN prediction = 'AWAY_WIN' THEN 1 END) as away_wins
FROM realtime_predictions
WHERE created_at >= CURRENT_DATE;
"

# 预期输出: 显示今日预测统计
# today_predictions | avg_confidence | home_wins | draws | away_wins
#-------------------+---------------+-----------+-------+----------
#                0 |          null |         0 |     0 |         0
```

---

## 📊 详细检查 (< 2分钟)

### 4. 系统资源检查 (30秒)
```bash
# 检查磁盘空间
./scripts/disk_space_monitor.sh

# 检查容器资源使用
docker stats footballprediction-app --no-stream --format "table {{.Name}}\t{{.MemUsage}}\t{{.CPUPerc}}"
```

### 5. 对账报告检查 (30秒)
```bash
# 检查今日对账报告
ls -la REPORTS/daily_settlement_$(date +%Y%m%d)* 2>/dev/null || echo "⚠️ 今日对账报告尚未生成"
```

### 6. 网络连接检查 (30秒)
```bash
# 检查数据库连接
docker exec footballprediction-db pg_isready -U football_user

# 检查Redis连接
docker exec footballprediction-redis redis-cli ping
```

---

## 🔧 问题排查指南

### 容器状态异常
```bash
# 重启异常服务
docker-compose restart app

# 查看详细错误日志
docker logs footballprediction-app --tail 50

# 检查容器资源
docker-compose ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}"
```

### 预测数据异常
```bash
# 手动触发一次预测测试
docker exec footballprediction-app python scripts/predict_match_v2.py --home "Test Team A" --away "Test Team B" --json-only

# 检查数据库连接
docker exec footballprediction-db psql -U football_user -d football_prediction_shadow -c "\dt realtime_predictions"
```

### 监控告警
```bash
# 手动触发磁盘监控
./scripts/disk_space_monitor.sh

# 查看监控日志
tail -20 logs/disk_monitor.log
```

---

## 📋 巡作流程 (5分钟)

1. **快速检查 (3分钟)**
   - [ ] `docker-compose ps`
   - [ ] `docker logs footballprediction-app --tail 10`
   - [ ] 数据库统计查询

2. **详细检查 (2分钟)**
   - [ ] `./scripts/disk_space_monitor.sh`
   - [ ] 容器资源检查
   - [ ] 对账报告确认
   - [ ] 网络连接验证

3. **问题记录**
   - [ ] 如果发现问题，记录在 `logs/daily_inspection_$(date +%Y%m%d).log`
   - [ ] 严重问题立即处理或上报

---

## 🎯 关键指标正常范围

### 健康状态 ✅
- **容器状态**: 3/3 services healthy
- **守护进程**: 每15分钟执行预测
- **数据库连接**: PostgreSQL accepting connections
- **Redis连接**: PONG响应

### 性能指标 ✅
- **磁盘使用**: < 80% (警告: >90%)
- **内存使用**: < 1.5GB (应用容器)
- **CPU使用**: < 20% (常规运行)
- **预测间隔**: 15分钟 ± 30秒

### 数据指标 ✅
- **每日预测数**: 96次 (24小时 × 4次/小时)
- **平均置信度**: 50% - 75%
- **数据完整性**: 100% (无缺失记录)
- **对账报告**: 每日08:00生成

---

## 🚨 紧急处理

### 系统完全停止
```bash
# 立即停止所有服务
docker-compose down

# 查看详细错误
docker-compose logs --tail=100
```

### 数据库连接失败
```bash
# 检查数据库容器
docker-compose restart db

# 验证数据库连接
docker exec footballprediction-db psql -U football_user -c "SELECT 1;"
```

### 自动化守护进程停止
```bash
# 检查进程
docker exec footballprediction-app python -c "
import os, glob, subprocess, sys
try:
    result = subprocess.run(['pgrep', '-f', 'automation_daemon_24h.py'], capture_output=True)
    if result.returncode == 0:
        print('✅ 守护进程运行中')
    else:
        print('❌ 守护进程未运行')
        sys.exit(1)
except:
    print('⚠️ 无法检查守护进程状态')
    sys.exit(1)
"
```

---

## 📞 紧急联系

### 日常问题
- 使用 `./scripts/check_health_live.sh` 获取完整状态报告
- 查看日志: `docker logs -f footballprediction-app`
- 重启服务: `docker-compose restart`

### 严重问题
- 检查 GitHub Issues
- 联系系统管理员
- 查看项目文档: `24H_SHADOW_MANUAL.md`

---

## 🏆 巡检完成确认

### 每日巡检清单
- [ ] 容器状态: 3/3 healthy
- [ ] 守护进程: 正常运行 (每15分钟预测)
- [ ] 数据库连接: 正常
- [ ] 预测数据: 今日统计正常
- [ ] 系统资源: 磁盘、内存、CPU正常
- [ ] 对账报告: 已生成/计划生成
- [ ] 网络连接: PostgreSQL和Redis正常
- [ ] 监控告警: 无异常

**✅ 每日巡检完成 - 系统运行正常**
**⚠️ 发现问题 - 请按照指南处理**
**🚨 系统异常 - 立即启动紧急处理流程**

---

*FootballPrediction v2.3.1 - Production Monitoring*
*最后更新: 2025-12-19*