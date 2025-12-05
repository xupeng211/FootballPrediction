# 🛡️ Disaster Recovery Guide

## 灾备恢复手册

### ⚡ 紧急恢复命令

#### **系统完全崩溃恢复**
```bash
# 1. 一键恢复到V2.1.0稳定状态
sh scripts/emergency_restore.sh

# 或者手动恢复：
# 恢复数据库快照
docker-compose exec -T db psql -U postgres -d football_prediction < data/backup/v2.1_stable_snapshot_dual_engine.sql

# 重启所有服务
docker-compose down && docker-compose up -d
```

#### **版本控制恢复**
```bash
# 恢复到V2.1.0稳定版本
git checkout v2.1.0-Stable

# 查看所有稳定版本标签
git tag --list "v*-Stable"
```

### 📊 数据资产备份

#### **自动备份**
- **位置**: `data/backup/`
- **最新快照**: `v2.1_stable_snapshot_dual_engine.sql` (18MB)
- **数据规模**: 26,000+ 比赛, 78,733 球员记录

#### **手动备份创建**
```bash
# 创建新的数据库快照
docker-compose exec db pg_dump -U postgres -d football_prediction > data/backup/manual_snapshot_$(date +%Y%m%d_%H%M%S).sql
```

### 🔧 服务恢复

#### **L2数据采集器恢复**
```bash
# 检查服务状态
docker-compose ps data-collector-l2

# 重启服务（如果需要）
docker-compose restart data-collector-l2

# 查看服务日志
docker-compose logs -f data-collector-l2
```

#### **完整服务重启**
```bash
# 完全重启所有服务
docker-compose down
docker-compose up -d

# 检查服务健康状态
make status
```

### 🚨 关键修复记录

#### **V2.1.0 关键修复 (2025-12-04)**
1. **日期解析Bug修复**: 支持 `datetime` 对象格式
2. **SQL语法修复**: 所有SQL查询使用 `text()` 包装
3. **浏览器指纹**: Chrome 131 隐身伪装
4. **重试机制**: 指数退避处理 429/403 错误

#### **相关文件**
- `src/utils/fotmob_match_matcher.py` - 日期解析修复
- `scripts/backfill_details_fotmob_v2.py` - L2采集器
- `src/data/collectors/fotmob_details_collector.py` - Chrome 131头部

### 📞 应急联系

#### **系统恢复流程**
1. 立即执行 `sh scripts/emergency_restore.sh`
2. 检查服务状态 `make status`
3. 验证数据完整性
4. 监控系统日志

#### **恢复验证**
```bash
# 验证数据库连接
docker-compose exec db psql -U postgres -d football_prediction -c "SELECT COUNT(*) FROM matches;"

# 验证API健康状态
curl http://localhost:8000/health

# 验证L2采集器状态
docker-compose ps data-collector-l2
```

---

**⚠️ 重要提醒**: 此文档保存了V2.1.0版本的所有关键恢复信息。定期更新备份和验证恢复流程。