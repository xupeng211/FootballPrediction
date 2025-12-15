# Football Prediction System 运维手册

## 概述
本手册提供Football Prediction系统的日常运维指南，包括监控、维护、故障处理等操作。

## 系统架构

### 服务组件
- **App**: FastAPI应用服务 (端口8000)
- **DB**: PostgreSQL数据库 (端口5432)
- **Redis**: 缓存服务 (端口6379)
- **Nginx**: 反向代理 (端口80/443)

### 数据流
```
用户请求 → Nginx → FastAPI App → PostgreSQL/Redis
                ↓
            日志 → 监控 → 告警
```

## 日常运维

### 服务管理
```bash
# 查看服务状态
docker-compose ps

# 重启服务
docker-compose restart app

# 更新服务
docker-compose pull && docker-compose up -d
```

### 日志管理
```bash
# 实时查看应用日志
docker-compose logs -f app

# 查看错误日志
docker-compose logs app | grep ERROR

# 清理旧日志
docker system prune -f
```

### 性能监控

#### 系统指标
- CPU使用率 < 80%
- 内存使用率 < 85%
- 磁盘使用率 < 90%
- 网络延迟 < 100ms

#### 应用指标
- 响应时间 < 1s (95th percentile)
- 错误率 < 5%
- 可用性 > 99.9%
- 并发用户数监控

### 数据库维护

#### 定期任务
```bash
# 数据库备份 (每日)
0 2 * * * docker-compose exec db pg_dump -U postgres football_prediction_prod > /backup/$(date +\%Y\%m\%d).sql

# 清理旧备份 (每周)
0 3 * * 0 find /backup -name "*.sql" -mtime +7 -delete

# 数据库优化 (每月)
0 4 1 * * docker-compose exec db psql -U postgres -d football_prediction_prod -c "VACUUM ANALYZE;"
```

#### 性能调优
```sql
-- 查看慢查询
SELECT query, mean_time, calls FROM pg_stat_statements ORDER BY mean_time DESC LIMIT 10;

-- 查看索引使用情况
SELECT schemaname, tablename, attname, n_distinct, correlation FROM pg_stats;

-- 重建索引
REINDEX DATABASE football_prediction_prod;
```

### 缓存管理

#### Redis监控
```bash
# 查看Redis信息
docker-compose exec redis redis-cli info

# 查看内存使用
docker-compose exec redis redis-cli info memory

# 清理过期键
docker-compose exec redis redis-cli FLUSHEXPIRED
```

#### 缓存策略
- 热数据TTL: 1小时
- 预测结果TTL: 30分钟
- 用户会话TTL: 24小时

## 安全管理

### 访问控制
- 定期更新密码
- 使用强密码策略
- 启用双因素认证
- 限制管理员权限

### 数据安全
```bash
# 数据加密
docker-compose exec db psql -U postgres -c "CREATE EXTENSION IF NOT EXISTS pgcrypto;"

# 定期安全扫描
docker run --rm -v $(pwd):/app clair-scanner:latest /app
```

### 网络安全
```bash
# 防火墙配置
ufw allow 80
ufw allow 443
ufw deny 5432  # 禁止外部访问数据库
ufw enable
```

## 告警处理

### 告警级别
- **Critical**: 立即响应 (1小时内)
- **Warning**: 工作时间响应 (4小时内)
- **Info**: 定期检查 (24小时内)

### 告警流程
1. 接收告警通知
2. 确认告警详情
3. 执行应急预案
4. 记录处理过程
5. 分析根本原因

### 应急预案

#### 应用宕机
```bash
# 快速重启
docker-compose restart app

# 检查日志
docker-compose logs app --tail=100

# 回滚版本
docker-compose down && docker-compose up -d
```

#### 数据库故障
```bash
# 切换到备用数据库
# 修改连接配置
docker-compose restart app

# 恢复主数据库
# 从备份恢复数据
```

## 容量规划

### 资源评估
- 用户增长率: 10%/月
- 数据增长率: 5%/月
- 峰值并发: 1000用户

### 扩容策略
- 水平扩展: 增加应用实例
- 垂直扩展: 增加单实例资源
- 数据库分片: 按业务模块分离

## 版本发布

### 发布流程
1. 代码审查
2. 自动化测试
3. 预发布验证
4. 生产发布
5. 监控验证

### 回滚策略
```bash
# 快速回滚到上一个版本
docker-compose down
docker pull ghcr.io/xupeng211/football-prediction:previous-tag
docker-compose up -d
```

---

*更新时间: 2025-10-30*
