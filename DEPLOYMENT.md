# 🌐 Production Deployment Guide

生产环境部署指南 - 足球预测系统

## 📋 目录

- [🚀 快速部署](#-快速部署)
- [📋 部署前检查](#-部署前检查)
- [🔧 环境准备](#-环境准备)
- [🚀 部署步骤](#-部署步骤)
- [🔍 部署验证](#-部署验证)
- [⚠️ 故障排查](#️-故障排查)
- [🔄 更新流程](#-更新流程)
- [📊 监控和维护](#-监控和维护)

## 🚀 快速部署

### 一键部署 (推荐)

```bash
# 1. 克隆项目
git clone https://github.com/xupeng211/FootballPrediction.git
cd FootballPrediction

# 2. 运行部署验证
./scripts/production-deployment-verification.sh

# 3. 启动生产环境
ENV=production docker-compose --profile production up -d

# 4. 验证部署
./scripts/verify-deployment.sh
```

## 📋 部署前检查

### 🔧 系统要求

- **操作系统**: Ubuntu 20.04+ / CentOS 8+ / Amazon Linux 2
- **内存**: 最低 4GB，推荐 8GB+
- **存储**: 最低 20GB，推荐 50GB+
- **CPU**: 最低 2核，推荐 4核+

### 📦 软件依赖

```bash
# 安装Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# 安装Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/download/v2.21.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# 安装其他工具
sudo apt update && sudo apt install -y curl jq openssl htop
```

### 🔒 安全准备

1. **域名和SSL**
   ```bash
   # 配置域名DNS指向服务器IP
   # 确保防火墙开放80和443端口
   sudo ufw allow 80
   sudo ufw allow 443
   ```

2. **SSL证书 (Let's Encrypt)**
   ```bash
   # 安装Certbot
   sudo apt install certbot python3-certbot-nginx

   # 获取SSL证书
   sudo certbot --nginx -d your-domain.com -d www.your-domain.com
   ```

## 🔧 环境准备

### 📝 环境变量配置

创建生产环境配置文件：

```bash
# 复制环境变量模板
cp .env.example .env.production

# 编辑生产环境配置
nano .env.production
```

**必需配置**：

```bash
# .env.production
ENVIRONMENT=production
DEBUG=false

# 数据库配置
DATABASE_URL=postgresql://username:password@localhost:5432/football_prediction
REDIS_URL=redis://localhost:6379/0

# 安全配置
SECRET_KEY=your-super-secret-key-here
JWT_SECRET_KEY=your-jwt-secret-key-here

# API配置
API_HOSTNAME=your-domain.com
ALLOWED_HOSTS=your-domain.com,www.your-domain.com

# SSL配置
SSL_CERT_PATH=/etc/letsencrypt/live/your-domain.com/fullchain.pem
SSL_KEY_PATH=/etc/letsencrypt/live/your-domain.com/privkey.pem
```

### 🗄️ 数据库准备

```bash
# 创建数据库
sudo -u postgres createdb football_prediction

# 创建用户
sudo -u postgres createuser --interactive

# 设置权限
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE football_prediction TO your_user;"
```

## 🚀 部署步骤

### 1️⃣ 基础设施部署

```bash
# 创建必要目录
sudo mkdir -p /opt/football-prediction/{data,logs,ssl,backups}
sudo chown -R $USER:$USER /opt/football-prediction

# 创建网络
docker network create football-prediction-net

# 启动基础服务 (数据库 + Redis)
docker-compose -f docker-compose.yml up -d db redis
```

### 2️⃣ 数据库初始化

```bash
# 等待数据库启动
sleep 30

# 运行数据库迁移
docker-compose exec app alembic upgrade head

# 创建初始数据 (可选)
docker-compose exec app python scripts/init_data.py
```

### 3️⃣ 应用部署

```bash
# 构建生产镜像
docker-compose -f docker-compose.yml build

# 启动应用服务
docker-compose -f docker-compose.yml up -d app nginx

# 启动监控服务 (可选)
docker-compose --profile monitoring up -d prometheus grafana loki
```

### 4️⃣ 服务验证

```bash
# 检查服务状态
docker-compose ps

# 检查应用健康
curl -f http://localhost/health

# 检查HTTPS
curl -I https://your-domain.com
```

## 🔍 部署验证

### 🏥 健康检查

```bash
# 应用健康检查
curl -f https://your-domain.com/health || echo "❌ 应用健康检查失败"

# 数据库连接检查
docker-compose exec db pg_isready -U postgres || echo "❌ 数据库连接失败"

# Redis连接检查
docker-compose exec redis redis-cli ping || echo "❌ Redis连接失败"
```

### 🧪 功能测试

```bash
# API端点测试
curl -X GET https://your-domain.com/api/v1/predictions

# 用户认证测试
curl -X POST https://your-domain.com/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"test","password":"test"}'

# 预测功能测试
curl -X POST https://your-domain.com/api/v1/predictions \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"match_id":123,"prediction":"home_win"}'
```

### 📊 性能验证

```bash
# 负载测试
ab -n 100 -c 10 https://your-domain.com/health

# 内存使用检查
docker stats --no-stream

# 磁盘使用检查
df -h
```

## ⚠️ 故障排查

### 🐛 常见问题

#### 应用无法启动

```bash
# 查看应用日志
docker-compose logs app

# 检查配置
docker-compose config

# 重启服务
docker-compose restart app
```

#### 数据库连接失败

```bash
# 检查数据库状态
docker-compose exec db pg_isready

# 查看数据库日志
docker-compose logs db

# 测试连接
docker-compose exec app python -c "
from src.database.connection import get_db_connection
print(get_db_connection())
"
```

#### SSL证书问题

```bash
# 检查证书状态
sudo certbot certificates

# 手动续期
sudo certbot renew

# 检查Nginx配置
docker-compose exec nginx nginx -t
```

#### 性能问题

```bash
# 查看系统资源
htop
iotop
docker stats

# 查看慢查询
docker-compose exec db psql -c "
SELECT query, mean_time, calls
FROM pg_stat_statements
ORDER BY mean_time DESC
LIMIT 10;"
```

### 🚨 紧急恢复

```bash
# 快速回滚到上一个版本
git checkout PREVIOUS_VERSION_TAG
docker-compose down
docker-compose up -d

# 从备份恢复数据库
docker-compose exec db psql -d football_prediction < backup.sql

# 重启所有服务
docker-compose restart
```

## 🔄 更新流程

### 📦 标准更新

```bash
# 1. 备份当前版本
./scripts/backup-current-version.sh

# 2. 拉取最新代码
git fetch origin
git checkout main
git pull origin main

# 3. 运行更新前检查
./scripts/pre-update-check.sh

# 4. 更新服务
docker-compose pull
docker-compose up -d

# 5. 运行数据库迁移
docker-compose exec app alembic upgrade head

# 6. 验证更新
./scripts/post-update-verification.sh
```

### 🔄 滚动更新

```bash
# 零停机更新
docker-compose up -d --no-deps app
docker-compose up -d --no-deps nginx

# 验证新版本
curl -f https://your-domain.com/health

# 清理旧镜像
docker image prune -f
```

## 📊 监控和维护

### 📈 监控指标

#### 应用监控
- **响应时间**: < 200ms (95th percentile)
- **错误率**: < 1%
- **吞吐量**: > 100 requests/second
- **可用性**: > 99.9%

#### 系统监控
- **CPU使用率**: < 80%
- **内存使用率**: < 85%
- **磁盘使用率**: < 90%
- **网络延迟**: < 50ms

### 🔔 告警配置

```yaml
# Prometheus告警规则示例
groups:
- name: football-prediction
  rules:
  - alert: HighErrorRate
    expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.01
    for: 2m
    labels:
      severity: critical
    annotations:
      summary: "High error rate detected"

  - alert: HighResponseTime
    expr: histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m])) > 0.2
    for: 5m
    labels:
      severity: warning
    annotations:
      summary: "High response time detected"
```

### 🗂️ 日志管理

```bash
# 查看应用日志
docker-compose logs -f app

# 查看访问日志
docker-compose logs -f nginx

# 查看错误日志
docker-compose logs -f app | grep ERROR

# 日志轮转配置
# /etc/logrotate.d/football-prediction
/opt/football-prediction/logs/*.log {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    notifempty
    create 644 root root
    postrotate
        docker-compose restart nginx
    endscript
}
```

### 💾 备份策略

```bash
#!/bin/bash
# 自动备份脚本 (backup_database.sh)

BACKUP_DIR="/opt/football-prediction/backups"
DATE=$(date +%Y%m%d_%H%M%S)

# 数据库备份
docker-compose exec -T db pg_dump -U postgres football_prediction > "$BACKUP_DIR/db_backup_$DATE.sql"

# 压缩备份
gzip "$BACKUP_DIR/db_backup_$DATE.sql"

# 删除30天前的备份
find "$BACKUP_DIR" -name "db_backup_*.sql.gz" -mtime +30 -delete

echo "数据库备份完成: $BACKUP_DIR/db_backup_$DATE.sql.gz"
```

### 🔧 定期维护

```bash
# 每周维护任务
0 2 * * 0 /opt/football-prediction/scripts/weekly-maintenance.sh

# 每日备份
0 3 * * * /opt/football-prediction/scripts/backup_database.sh

# SSL证书续期
0 4 1 * * /opt/football-prediction/scripts/renew_ssl_certificates.sh
```

## 📞 支持联系

### 🆘 紧急联系

- **技术负责人**: [联系方式]
- **运维团队**: [联系方式]
- **GitHub Issues**: [项目Issues页面]

### 📚 文档资源

- [API文档](https://your-domain.com/docs)
- [架构文档](./docs/architecture/)
- [开发指南](./CONTRIBUTING.md)
- [故障排查手册](./docs/troubleshooting.md)

---

**部署版本**: v1.0
**最后更新**: 2025-10-31
**维护团队**: FootballPrediction开发团队

---

*🎉 祝您部署顺利！如有问题，请参考故障排查部分或联系技术支持。*
