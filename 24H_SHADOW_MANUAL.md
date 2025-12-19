# 🏆 24小时影子实战操作手册 v2.3.1

> **版本**: v2.3.1
> **更新**: 2025-12-19
> **状态**: 生产就绪

## 📋 快速对账单查看

### 明早如何查看昨晚的预测成果？

```bash
# 1. 进入项目目录
cd /home/user/projects/FootballPrediction

# 2. 一键查看完整对账单
./scripts/check_health_live.sh

# 3. 查看具体预测记录
docker logs footballprediction-app | grep "✅ 预测成功" | tail -10
```

**关键输出指标**：
- 🏆 成功预测次数: 显示总预测数量
- ❤️ 最后心跳: 显示最后预测时间
- ⏰ 下次预测: 显示下次预测时间
- 💾 内存使用: 系统资源状态

### 详细数据查询

```bash
# 查看数据库中的预测记录
docker exec footballprediction-db psql -U football_user -d football_prediction_dev -c "
SELECT match_date, home_team, away_team, prediction, confidence
FROM matches
WHERE match_date > NOW() - INTERVAL '24 hours'
ORDER BY match_date DESC
LIMIT 20;"

# 导出预测对账单
docker exec footballprediction-db psql -U football_user -d football_prediction_dev -c "
COPY (
    SELECT
        match_date,
        home_team,
        away_team,
        prediction,
        confidence,
        created_at
    FROM matches
    WHERE match_date > NOW() - INTERVAL '24 hours'
    ORDER BY match_date DESC
) TO '/tmp/predictions_24h.csv' WITH CSV HEADER;"

docker cp footballprediction-db:/tmp/predictions_24h.csv ./predictions_$(date +%Y%m%d).csv
```

## 🛑 紧急停止操作

### 场景1: 立即停止所有服务
```bash
# 紧急停止命令
docker-compose down

# 确认所有容器已停止
docker-compose ps
```

### 场景2: 只停止自动化守护进程
```bash
# 优雅停止应用容器（保留数据）
docker-compose stop app

# 重启应用容器
docker-compose start app
```

### 场景3: 清理并完全重置
```bash
# 完全清理（数据会保留在本地目录）
docker-compose down -v --remove-orphans

# 重新启动
docker-compose up -d
```

## 🔧 系统监控与维护

### 日常监控命令
```bash
# 1. 实时监控日志
docker logs -f footballprediction-app

# 2. 查看容器资源使用
docker stats footballprediction-app

# 3. 检查磁盘空间
df -h ./data

# 4. 查看服务健康状态
docker-compose ps
```

### 性能优化建议
- **内存使用**: 正常应在50-200MB之间
- **CPU使用**: 正常应低于5%
- **磁盘空间**: 确保至少有5GB可用空间
- **预测间隔**: 15分钟（可在docker-compose.yml中调整）

## 📊 预测结果分析

### 预测输出格式
```json
{
  "success": true,
  "home_team": "Manchester United",
  "away_team": "Arsenal",
  "probabilities": {
    "HOME_WIN": 64.4,
    "DRAW": 5.0,
    "AWAY_WIN": 35.6
  },
  "prediction": "HOME_WIN",
  "confidence": 0.644,
  "model_info": {
    "version": "simulation_mode",
    "status": "mock"
  }
}
```

### 置信度解释
- **>60%**: 高置信度预测
- **50-60%**: 中等置信度
- **<50%**: 低置信度，建议谨慎参考

## 🚨 常见问题处理

### 问题1: 容器启动失败
```bash
# 检查Docker服务
sudo systemctl status docker

# 查看详细错误
docker-compose up --no-deps app
```

### 问题2: 数据库连接失败
```bash
# 重启数据库服务
docker-compose restart db

# 检查数据库连接
docker exec footballprediction-db pg_isready -U football_user
```

### 问题3: 预测服务异常
```bash
# 查看应用日志
docker logs footballprediction-app --tail 50

# 重启应用服务
docker-compose restart app
```

## 📈 数据备份与恢复

### 数据库备份
```bash
# 创建数据库备份
docker exec footballprediction-db pg_dump -U football_user football_prediction_dev > backup_$(date +%Y%m%d_%H%M%S).sql

# 恢复数据库备份
docker exec -i footballprediction-db psql -U football_user football_prediction_dev < backup_20251219_033000.sql
```

### 完整系统备份
```bash
# 备份项目数据和配置
tar -czf footballprediction_backup_$(date +%Y%m%d).tar.gz \
  ./data/ \
  ./logs/ \
  ./docker-compose.yml \
  ./.env* \
  ./scripts/check_health_live.sh
```

## 🎯 系统架构概览

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   应用容器       │    │   PostgreSQL    │    │     Redis       │
│                 │    │                 │    │                 │
│ 🤖 自动化守护    │◄──►│ 🗄️ 预测数据存储   │◄──►│ 🔴 缓存服务      │
│ 每15分钟预测     │    │                 │    │                 │
│                 │    │                 │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
        │                       │                       │
        └───────────────────────┼───────────────────────┘
                                │
                       ┌─────────────────┐
                       │   运维监控       │
                       │                 │
                       │ 📊 check_health_ │
                       │   live.sh       │
                       │                 │
                       └─────────────────┘
```

## 📞 紧急联系

### 系统状态检查
```bash
# 一键系统健康检查
./scripts/check_health_live.sh

# 查看完整系统状态
docker-compose ps && echo "--------" && df -h && echo "--------" && free -h
```

### 关键文件位置
- **配置文件**: `docker-compose.yml`
- **预测脚本**: `scripts/predict_match_v2.py`
- **监控脚本**: `scripts/check_health_live.sh`
- **数据存储**: `./data/postgres/` 和 `./data/redis/`
- **日志存储**: `./logs/`

---

## 🎉 总结

**FootballPrediction v2.3.1** 已实现：
- ✅ 24小时无人值守自动化运行
- ✅ 每15分钟智能预测分析
- ✅ 完整的监控和对账系统
- ✅ 生产级容器化部署
- ✅ 紧急故障处理机制

**系统特点**：
- 🔒 安全的非root用户运行
- 📊 实时监控仪表盘
- 🗄️ 持久化数据存储
- 🚀 高可用架构设计

**使用建议**：
1. 每日查看 `./scripts/check_health_live.sh` 输出
2. 定期备份数据和配置文件
3. 关注系统资源使用情况
4. 出现异常时参考"常见问题处理"部分

**系统已准备好进行24小时无人值守运行！** 🏆