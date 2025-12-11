# 🛡️ 灾备与恢复手册
## Football Prediction System V1.1 - Disaster Recovery Manual

> **版本**: V1.1-STABLE
> **更新日期**: 2025-12-03
> **状态**: ✅ 生产就绪
> **数据资产**: 26,000+ 足球比赛记录

---

## 📊 快速恢复命令 (Quick Recovery)

### 🔥 最快恢复方式 (服务器重启后)
```bash
# 单行命令恢复一切
./scripts/restart_pipeline.sh
```

### 🔄 完整恢复方式 (含数据回滚)
```bash
# 恢复到黄金快照状态 (26,000条记录)
./scripts/restart_pipeline.sh --restore-from-backup
```

---

## 📁 备份文件位置 (Backup Files Location)

### 🏆 黄金快照 (Golden Snapshot)
```
📂 data/backup/v1.1_stable_snapshot_26k.sql
📏 大小: 8.0MB
📅 创建时间: 2025-12-03
📊 记录数: 26,000+
```

### 📋 系统备份文件清单
```
data/backup/
├── v1.1_stable_snapshot_26k.sql    # 🏆 主数据库快照 (8.0MB)
├── recovery_history.txt            # 📝 恢复历史记录
└── README.md                       # 📖 备份说明文档

logs/
├── recovery_YYYYMMDD_HHMMSS.log    # 📋 每次恢复的详细日志
└── recovery_history.txt            # 📊 恢复操作历史
```

---

## 🚨 灾难场景与解决方案

### 场景 1: 服务器重启/断电恢复
**症状**: 所有服务停止，需要快速恢复
```bash
# ✅ 解决方案: 一键恢复
./scripts/restart_pipeline.sh
```
**预期结果**: 2-3分钟内系统完全恢复

### 场景 2: 数据库损坏/数据丢失
**症状**: 数据异常或记录数量不对
```bash
# ✅ 解决方案: 完整恢复到黄金快照
./scripts/restart_pipeline.sh --restore-from-backup
```
**预期结果**: 恢复到26,000+条记录的稳定状态

### 场景 3: 应用程序异常
**症状**: API无响应，服务报错
```bash
# ✅ 解决方案: 重启应用服务
docker-compose restart app
# 如果无效，使用完整恢复
./scripts/restart_pipeline.sh
```

### 场景 4: 部分服务异常
**症状**: 某些功能不工作
```bash
# ✅ 解决方案: 检查并重启特定服务
docker-compose ps              # 查看服务状态
docker-compose logs app        # 查看应用日志
docker-compose restart app     # 重启应用服务
```

---

## 🔧 手动恢复步骤 (Manual Recovery)

### 如果自动脚本失败，请按以下步骤手动操作：

#### Step 1: 启动基础服务
```bash
# 启动所有容器
docker-compose up -d

# 等待数据库就绪 (约30秒)
docker-compose exec db pg_isready -U postgres
```

#### Step 2: 恢复数据库 (如需要)
```bash
# 删除损坏的数据库
docker-compose exec db psql -U postgres -d postgres -c "DROP DATABASE IF EXISTS football_prediction;"

# 创建新数据库
docker-compose exec db psql -U postgres -d postgres -c "CREATE DATABASE football_prediction;"

# 从备份恢复 (需要5-10分钟)
docker-compose exec db psql -U postgres -d football_prediction < data/backup/v1.1_stable_snapshot_26k.sql
```

#### Step 3: 验证数据
```bash
# 检查记录数量
docker-compose exec db psql -U postgres -d football_prediction -c "SELECT COUNT(*) FROM matches;"

# 检查最新数据
docker-compose exec db psql -U postgres -d football_prediction -c "SELECT MAX(match_date) FROM matches;"
```

#### Step 4: 启动应用服务
```bash
# 运行数据库迁移
docker-compose exec app bash -c "cd /app && python -m alembic upgrade head"

# 等待应用健康检查
curl http://localhost:8000/health
```

---

## 📊 系统健康检查命令

### 🏥 基础健康检查
```bash
# API健康状态
curl http://localhost:8000/health

# 数据库连接测试
docker-compose exec db pg_isready -U postgres

# Redis连接测试
docker-compose exec redis redis-cli ping
```

### 📈 数据统计检查
```bash
# 比赛记录数量
docker-compose exec db psql -U postgres -d football_prediction -c "SELECT COUNT(*) FROM matches;"

# 数据日期范围
docker-compose exec db psql -U postgres -d football_prediction -c "SELECT MIN(match_date), MAX(match_date) FROM matches;"

# L1/L2数据统计
docker-compose exec db psql -U postgres -d football_prediction -c "SELECT data_source, COUNT(*) FROM matches GROUP BY data_source;"
```

### 🔄 服务状态检查
```bash
# 所有Docker容器状态
docker-compose ps

# 应用日志 (最后50行)
docker-compose logs --tail=50 app

# 数据库日志 (最后50行)
docker-compose logs --tail=50 db
```

---

## 🎯 关键端点与服务地址

### 🌐 用户界面
- **前端应用**: http://localhost:3000
- **后端API**: http://localhost:8000
- **API文档**: http://localhost:8000/docs

### 🔧 管理端点
- **健康检查**: http://localhost:8000/health
- **系统指标**: http://localhost:8000/api/v1/metrics
- **数据ETL**: http://localhost:8000/api/v1/data/etl

### 📊 数据管理
```bash
# 触发L1数据采集
curl -X POST http://localhost:8000/api/v1/data/collect/l1

# 触发L2数据补全
curl -X POST http://localhost:8000/api/v1/data/backfill/l2

# 数据统计API
curl http://localhost:8000/api/v1/data/stats
```

---

## 🚨 应急联系人 (Emergency Contacts)

### 📞 系统维护
- **主要负责人**: DevOps Team
- **紧急恢复**: 使用 `./scripts/restart_pipeline.sh`
- **数据备份**: 检查 `data/backup/` 目录

### 📚 参考文档
- **系统架构**: `CLAUDE.md`
- **API文档**: http://localhost:8000/docs
- **恢复日志**: `logs/recovery_*.log`

---

## ⚡ 恢复时间预估 (Recovery Time Estimates)

| 恢复场景 | 预估时间 | 说明 |
|---------|---------|------|
| 服务器重启恢复 | 2-3分钟 | 自动恢复所有服务 |
| 数据库恢复 | 5-10分钟 | 从8MB备份文件恢复 |
| 完整系统重建 | 10-15分钟 | 包含数据恢复和验证 |
| 应急快速恢复 | 30秒 | 仅重启服务，不恢复数据 |

---

## 🔒 备份策略说明

### 🏆 黄金快照策略
- **创建时间**: 每个主要版本发布后
- **保存内容**: 完整数据库结构 + 所有业务数据
- **文件大小**: 约8MB (26,000条记录)
- **恢复速度**: 5-10分钟

### 📋 增量备份建议
```bash
# 创建每日增量备份 (可选)
docker-compose exec db pg_dump -U postgres -d football_prediction > data/backup/daily_$(date +%Y%m%d).sql

# 创建备份压缩包
tar -czf data/backup/football_prediction_backup_$(date +%Y%m%d).tar.gz data/backup/
```

---

## ✅ 恢复验证清单

恢复完成后，请逐项检查：

- [ ] **服务状态**: 所有Docker容器运行正常
- [ ] **API健康**: http://localhost:8000/health 返回200
- [ ] **数据完整性**: 记录数量正确 (26,000+)
- [ ] **数据新鲜度**: 最新数据日期合理
- [ ] **功能测试**: API端点响应正常
- [ ] **日志检查**: 无严重错误日志
- [ ] **性能验证**: 响应时间正常

---

## 🎉 恢复成功标志

当您看到以下信息时，说明恢复成功：

```
🎉 Football Prediction System V1.1 is now operational!

System Status:
  📊 Database: Online
  🌐 API: Healthy (http://localhost:8000/health)
  📈 Records: 26,000+
```

---

## 📞 恢复失败处理

如果自动恢复失败：

1. **检查日志**: `tail -f logs/recovery_*.log`
2. **手动恢复**: 按照"手动恢复步骤"操作
3. **联系支持**: 查看恢复日志中的错误信息
4. **回滚策略**: 可以使用 `git checkout v1.1-STABLE` 回滚代码

---

**💡 重要提醒**:
- 定期检查 `data/backup/` 目录中的备份文件
- 每次恢复操作都会记录在 `logs/recovery_history.txt` 中
- 建议在每次重大操作前创建新的备份

---
**维护团队**: DevOps & Release Management Team
**最后更新**: 2025-12-03
**下次备份计划**: V1.2 发布前