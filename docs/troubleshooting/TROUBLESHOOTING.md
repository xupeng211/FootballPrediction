# Football Prediction System 故障排除指南

## 概述
本指南提供Football Prediction系统常见问题的诊断和解决方案。

## 快速诊断

### 健康检查脚本
```bash
#!/bin/bash
# health_check.sh

echo "🔍 系统健康检查..."

# 检查服务状态
echo "📊 检查服务状态:"
docker-compose ps

# 检查应用健康
echo "🏥 检查应用健康:"
curl -s http://localhost:8000/health || echo "❌ 应用健康检查失败"

# 检查数据库连接
echo "🗄️ 检查数据库连接:"
docker-compose exec -T db pg_isready -U postgres || echo "❌ 数据库连接失败"

# 检查Redis连接
echo "🔴 检查Redis连接:"
docker-compose exec -T redis redis-cli ping || echo "❌ Redis连接失败"

echo "✅ 健康检查完成"
```

## 常见问题

### 1. 应用无法启动

#### 症状
- Docker容器启动失败
- 健康检查失败
- 无法访问应用

#### 诊断步骤
```bash
# 查看容器状态
docker-compose ps

# 查看启动日志
docker-compose logs app

# 检查端口占用
netstat -tlnp | grep :8000

# 检查环境变量
docker-compose config
```

#### 解决方案
```bash
# 重启服务
docker-compose down && docker-compose up -d

# 清理并重建
docker-compose down -v
docker system prune -f
docker-compose up -d

# 检查配置文件
docker-compose config
```

### 2. 数据库连接问题

#### 症状
- 应用日志显示数据库连接错误
- 数据库查询失败
- 无法连接到数据库

#### 诊断步骤
```bash
# 检查数据库容器状态
docker-compose ps db

# 检查数据库日志
docker-compose logs db

# 测试数据库连接
docker-compose exec db psql -U postgres -d football_prediction -c "SELECT 1;"

# 检查网络连接
docker network ls
docker network inspect football-prediction_default
```

#### 解决方案
```bash
# 重启数据库
docker-compose restart db

# 检查数据库配置
docker-compose exec db cat /var/lib/postgresql/data/postgresql.conf

# 重建数据库
docker-compose down -v
docker-compose up -d db
docker-compose exec app python -m alembic upgrade head
```

### 3. Redis连接问题

#### 症状
- 缓存操作失败
- 会话丢失
- 性能下降

#### 诊断步骤
```bash
# 检查Redis容器
docker-compose ps redis

# 测试Redis连接
docker-compose exec redis redis-cli ping

# 检查Redis内存使用
docker-compose exec redis redis-cli info memory

# 查看Redis日志
docker-compose logs redis
```

#### 解决方案
```bash
# 重启Redis
docker-compose restart redis

# 清理Redis内存
docker-compose exec redis redis-cli FLUSHALL

# 检查Redis配置
docker-compose exec redis redis-cli CONFIG GET "*"
```

### 4. 性能问题

#### 症状
- 响应时间慢
- CPU使用率高
- 内存使用率高

#### 诊断步骤
```bash
# 检查系统资源
docker stats

# 查看应用性能指标
curl http://localhost:8000/metrics

# 分析慢查询
docker-compose exec db psql -U postgres -d football_prediction -c "
SELECT query, mean_time, calls
FROM pg_stat_statements
ORDER BY mean_time DESC
LIMIT 10;"

# 检查缓存命中率
docker-compose exec redis redis-cli info stats | grep keyspace
```

#### 解决方案
```bash
# 扩容应用实例
docker-compose up -d --scale app=3

# 优化数据库
docker-compose exec db psql -U postgres -d football_prediction -c "VACUUM ANALYZE;"

# 清理缓存
docker-compose exec redis redis-cli FLUSHDB
```

### 5. 内存泄漏

#### 症状
- 内存使用持续增长
- 应用重启后内存下降
- OOM错误

#### 诊断步骤
```bash
# 监控内存使用
docker stats --format "table {{.Container}}	{{.CPUPerc}}	{{.MemUsage}}"

# 查看内存详情
docker-compose exec app cat /proc/meminfo

# 检查Python内存使用
docker-compose exec app python -c "
import psutil
import os
process = psutil.Process(os.getpid())
print(f'Memory: {process.memory_info().rss / 1024 / 1024:.2f} MB')
"
```

#### 解决方案
```bash
# 重启应用
docker-compose restart app

# 设置内存限制
# 在docker-compose.yml中添加:
# deploy:
#   resources:
#     limits:
#       memory: 1G

# 监控内存使用
docker stats --no-stream
```

### 6. 磁盘空间不足

#### 症状
- 磁盘使用率 > 90%
- 无法写入日志
- 数据库操作失败

#### 诊断步骤
```bash
# 检查磁盘使用
df -h

# 查看大文件
find / -type f -size +1G 2>/dev/null

# 检查Docker空间使用
docker system df

# 查看日志大小
du -sh /var/lib/docker/containers/*
```

#### 解决方案
```bash
# 清理Docker
docker system prune -a -f

# 清理日志
docker-compose exec app find /app/logs -name "*.log" -mtime +7 -delete

# 清理数据库
docker-compose exec db psql -U postgres -d football_prediction -c "VACUUM FULL;"
```

## 日志分析

### 应用日志格式
```
2025-10-30 03:00:00 [INFO] Request: GET /api/predictions - Status: 200 - Time: 0.05s
2025-10-30 03:00:01 [ERROR] Database connection failed: connection timeout
2025-10-30 03:00:02 [WARNING] Cache miss for key: prediction_123
```

### 日志分析命令
```bash
# 查看错误日志
docker-compose logs app | grep ERROR

# 统计HTTP状态码
docker-compose logs app | grep -o "Status: [0-9]*" | sort | uniq -c

# 查看慢请求
docker-compose logs app | grep "Time: [0-9]*\." | awk '$NF > 1.0'

# 实时监控日志
docker-compose logs -f app | grep -E "(ERROR|WARNING)"
```

## 性能优化

### 数据库优化
```sql
-- 创建索引
CREATE INDEX CONCURRENTLY idx_predictions_created_at ON predictions(created_at);

-- 分析查询性能
EXPLAIN ANALYZE SELECT * FROM predictions WHERE created_at > NOW() - INTERVAL '1 day';

-- 更新统计信息
ANALYZE predictions;
```

### 应用优化
```python
# 缓存优化
from functools import lru_cache

@lru_cache(maxsize=1000)
def get_prediction(match_id: int):
    # 缓存预测结果
    pass

# 连接池优化
DATABASE_CONFIG = {
    "pool_size": 20,
    "max_overflow": 30,
    "pool_timeout": 30,
    "pool_recycle": 3600
}
```

## 应急响应

### 严重故障处理流程
1. **立即响应** (5分钟内)
   - 确认故障范围
   - 启动应急预案
   - 通知相关人员

2. **故障隔离** (30分钟内)
   - 隔离故障组件
   - 启用备用服务
   - 保留故障现场

3. **快速修复** (2小时内)
   - 应用快速修复
   - 验证修复效果
   - 恢复正常服务

4. **根因分析** (24小时内)
   - 分析故障原因
   - 制定预防措施
   - 更新运维文档

### 联系方式
- **技术负责人**: [联系方式]
- **运维团队**: [联系方式]
- **产品负责人**: [联系方式]

---

*更新时间: 2025-10-30*
