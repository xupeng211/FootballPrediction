# Football Prediction 部署指南

## 概述

本指南详细说明了如何部署Football Prediction系统到开发和生产环境。系统使用Docker容器化部署，包含完整的监控、日志收集和备份策略。

## 系统架构

### 核心服务
- **应用服务**: FastAPI应用 (端口: 8000)
- **数据库**: PostgreSQL 15 (端口: 5432)
- **缓存**: Redis 7 (端口: 6379)
- **反向代理**: Nginx (端口: 80, 443)

### 监控服务
- **Prometheus**: 指标收集 (端口: 9090)
- **Grafana**: 可视化仪表板 (端口: 3000)
- **AlertManager**: 告警管理 (端口: 9093)
- **Loki**: 日志聚合 (端口: 3100)

### 其他服务
- **Node Exporter**: 系统监控 (端口: 9100)
- **Redis Exporter**: Redis监控 (端口: 9121)
- **Postgres Exporter**: 数据库监控 (端口: 9187)
- **cAdvisor**: 容器监控 (端口: 8080)

## 快速开始

### 1. 环境准备

确保系统已安装以下软件：
- Docker (20.10+)
- Docker Compose (2.0+)
- Git
- OpenSSL

### 2. 克隆项目

```bash
git clone https://github.com/your-repo/FootballPrediction.git
cd FootballPrediction
```

### 3. 一键部署

```bash
# 设置环境
./scripts/deployment/deploy_manager.sh setup

# 部署应用
./scripts/deployment/deploy_manager.sh deploy

# 设置监控
./scripts/deployment/deploy_manager.sh monitor
```

## 详细部署步骤

### 开发环境部署

#### 1. 环境设置
```bash
./scripts/deployment/setup_environment.sh --dev
```

#### 2. 启动服务
```bash
docker-compose up -d --build
```

#### 3. 验证部署
```bash
curl http://localhost:8000/api/v1/health
```

### 生产环境部署

#### 1. 环境设置
```bash
./scripts/deployment/setup_environment.sh
```

#### 2. 配置环境变量
编辑 `.env.production` 文件：
```bash
# 必须配置的变量
SECRET_KEY=your-secret-key-here
POSTGRES_PASSWORD=secure-database-password
REDIS_PASSWORD=secure-redis-password
JWT_SECRET_KEY=jwt-secret-key-here

# 可选配置
SLACK_WEBHOOK_URL=your-slack-webhook
EMAIL_SMTP_HOST=smtp.gmail.com
EMAIL_USERNAME=your-email@gmail.com
EMAIL_PASSWORD=your-app-password
```

#### 3. 部署应用
```bash
./scripts/deployment/production_deploy.sh
```

#### 4. 设置监控
```bash
./scripts/deployment/setup_monitoring.sh
docker-compose -f docker-compose.monitoring.yml up -d
```

## 部署管理工具

### 使用部署管理器

```bash
# 查看帮助
./scripts/deployment/deploy_manager.sh help

# 设置环境
./scripts/deployment/deploy_manager.sh setup --env production

# 部署应用
./scripts/deployment/deploy_manager.sh deploy --env production

# 更新应用
./scripts/deployment/deploy_manager.sh update --skip-backup

# 回滚部署
./scripts/deployment/deploy_manager.sh rollback

# 查看状态
./scripts/deployment/deploy_manager.sh status

# 查看日志
./scripts/deployment/deploy_manager.sh logs

# 备份数据
./scripts/deployment/deploy_manager.sh backup

# 停止服务
./scripts/deployment/deploy_manager.sh stop

# 重启服务
./scripts/deployment/deploy_manager.sh restart

# 清理资源
./scripts/deployment/deploy_manager.sh cleanup
```

### 手动操作

#### 应用部署
```bash
# 生产部署
./scripts/deployment/production_deploy.sh

# 跳过备份
./scripts/deployment/production_deploy.sh --skip-backup

# 跳过测试
./scripts/deployment/production_deploy.sh --skip-tests
```

#### 数据库备份
```bash
# 完整备份
./scripts/deployment/backup_database.sh

# 跳过清理
./scripts/deployment/backup_database.sh --skip-cleanup

# 仅周备份
./scripts/deployment/backup_database.sh --weekly-only
```

#### 监控设置
```bash
# 生成监控配置
./scripts/deployment/setup_monitoring.sh

# 启动监控服务
docker-compose -f docker-compose.monitoring.yml up -d
```

## 服务管理

### Docker Compose操作

#### 开发环境
```bash
# 启动服务
docker-compose up -d

# 停止服务
docker-compose down

# 查看日志
docker-compose logs -f

# 重建服务
docker-compose up -d --build
```

#### 生产环境
```bash
# 启动服务
docker-compose -f docker-compose.prod.yml up -d

# 停止服务
docker-compose -f docker-compose.prod.yml down

# 查看日志
docker-compose -f docker-compose.prod.yml logs -f

# 更新服务
docker-compose -f docker-compose.prod.yml pull
docker-compose -f docker-compose.prod.yml up -d
```

#### 监控服务
```bash
# 启动监控
docker-compose -f docker-compose.monitoring.yml up -d

# 停止监控
docker-compose -f docker-compose.monitoring.yml down
```

### 系统服务管理

如果使用systemd服务：

```bash
# 启用服务
sudo systemctl enable football-prediction

# 启动服务
sudo systemctl start football-prediction

# 停止服务
sudo systemctl stop football-prediction

# 重启服务
sudo systemctl restart football-prediction

# 查看状态
sudo systemctl status football-prediction

# 查看日志
sudo journalctl -u football-prediction -f
```

## 监控和日志

### 访问监控界面

- **Grafana**: http://localhost:3000 (admin/admin123)
- **Prometheus**: http://localhost:9090
- **AlertManager**: http://localhost:9093

### 查看应用日志

```bash
# 实时日志
docker-compose logs -f app

# 历史日志
docker-compose logs --tail=100 app

# 特定时间日志
docker-compose logs --since="2024-01-01" app
```

### 日志文件位置

- **应用日志**: `logs/app/`
- **Nginx日志**: `logs/nginx/`
- **数据库日志**: Docker容器内
- **备份日志**: `backups/`

## 备份和恢复

### 自动备份

系统配置了自动备份：
- **每日备份**: 凌晨2点执行
- **周备份**: 每周日执行
- **保留策略**:
  - 日备份保留7天
  - 周备份保留30天

### 手动备份

```bash
# 完整备份
./scripts/deployment/backup_database.sh

# 查看备份文件
ls -la backups/
```

### 数据恢复

```bash
# 停止应用
docker-compose -f docker-compose.prod.yml down

# 恢复数据库
gunzip -c backups/football_prediction_backup_20240101_020000.sql.gz | \
docker exec -i football-prediction-db psql -U postgres -d football_prediction

# 启动应用
docker-compose -f docker-compose.prod.yml up -d
```

## 安全配置

### SSL/TLS配置

生产环境需要配置有效的SSL证书：

1. **获取证书**: 使用Let's Encrypt或其他CA
2. **更新Nginx配置**: 替换自签名证书
3. **配置HTTP重定向**: 强制HTTPS

### 防火墙配置

```bash
# Ubuntu/Debian
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP
sudo ufw allow 443/tcp   # HTTPS
sudo ufw enable

# CentOS/RHEL
sudo firewall-cmd --permanent --add-service=ssh
sudo firewall-cmd --permanent --add-service=http
sudo firewall-cmd --permanent --add-service=https
sudo firewall-cmd --reload
```

### 密码安全

- 使用强密码
- 定期更换密码
- 不要在代码中硬编码密码
- 使用环境变量存储敏感信息

## 性能优化

### 数据库优化

```sql
-- 创建索引
CREATE INDEX idx_predictions_user_id ON predictions(user_id);
CREATE INDEX idx_predictions_match_id ON predictions(match_id);

-- 分析查询性能
EXPLAIN ANALYZE SELECT * FROM predictions WHERE user_id = 1;
```

### Redis优化

```bash
# 配置Redis持久化
redis-cli CONFIG SET save "900 1 300 10 60 10000"

# 监控Redis性能
redis-cli INFO memory
redis-cli INFO stats
```

### Nginx优化

```nginx
# 启用Gzip压缩
gzip on;
gzip_types text/plain text/css application/json;

# 配置缓存
location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg)$ {
    expires 1y;
    add_header Cache-Control "public, immutable";
}
```

## 故障排除

### 常见问题

#### 1. 容器启动失败
```bash
# 查看容器状态
docker ps -a

# 查看容器日志
docker logs container_name

# 重新启动容器
docker restart container_name
```

#### 2. 数据库连接失败
```bash
# 检查数据库容器
docker exec -it football-prediction-db bash

# 测试连接
psql -U postgres -d football_prediction

# 检查网络
docker network ls
docker network inspect network_name
```

#### 3. Redis连接失败
```bash
# 检查Redis容器
docker exec -it football-prediction-redis bash

# 测试连接
redis-cli ping

# 检查配置
redis-cli CONFIG GET "*"
```

#### 4. 应用无响应
```bash
# 检查应用健康状态
curl http://localhost:8000/api/v1/health

# 查看应用日志
docker logs football-prediction-app

# 重启应用
docker restart football-prediction-app
```

### 日志分析

```bash
# 查看错误日志
grep "ERROR" logs/app/app.log

# 查看访问日志
tail -f logs/nginx/access.log

# 分析性能日志
awk '{print $NF}' logs/nginx/access.log | sort | uniq -c | sort -nr
```

## 升级指南

### 应用升级

```bash
# 1. 备份数据
./scripts/deployment/backup_database.sh

# 2. 拉取最新代码
git pull origin main

# 3. 更新应用
./scripts/deployment/production_deploy.sh --skip-backup

# 4. 验证升级
./scripts/deployment/deploy_manager.sh status
```

### 回滚操作

```bash
# 自动回滚
./scripts/deployment/production_deploy.sh --rollback

# 手动回滚
git checkout previous_commit_hash
./scripts/deployment/production_deploy.sh --skip-backup
```

## 维护计划

### 日常维护
- 监控系统资源使用
- 检查日志错误
- 验证备份完整性
- 更新安全补丁

### 周期维护
- 清理旧日志文件
- 优化数据库性能
- 更新SSL证书
- 测试灾难恢复

### 紧急响应
- 监控告警通知
- 快速故障定位
- 服务恢复流程
- 事后分析总结

## 联系支持

如果遇到部署问题，请：

1. 查看本文档的故障排除部分
2. 检查GitHub Issues
3. 联系技术支持团队
4. 提供详细的错误信息和环境描述

---

**注意**: 本指南会随着系统更新而持续改进，请定期查看最新版本。