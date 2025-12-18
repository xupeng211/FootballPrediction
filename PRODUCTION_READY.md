# 🚀 Production Ready部署指南

## 📋 Sprint 8 最终部署清单

足球预测系统v2.0 - 生产级24/7自动化预测服务

---

## 🎯 部署概览

本系统已通过Sprint 1-8的全面开发和测试，具备生产环境部署的所有条件：
- ✅ **核心算法优化** (Sprint 2) - Elo评分、泊松分布、凯利准则
- ✅ **服务解耦架构** (Sprint 3) - 微服务化、异步处理
- ✅ **大数据性能优化** (Sprint 4) - 高并发、低延迟
- ✅ **回测策略验证** (Sprint 5) - 历史数据验证
- ✅ **实时工作流** (Sprint 6) - 自动化数据处理
- ✅ **全自动化测试** (Sprint 7) - 覆盖率>85%
- ✅ **生产安全加固** (Sprint 8) - 风险控制、安全审计

---

## 🏗️ 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                    负载均衡器 (Nginx)                        │
└─────────────────────┬───────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────┐
│                  应用服务器集群                               │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐           │
│  │   App Pod 1 │ │   App Pod 2 │ │   App Pod N │           │
│  │  (FastAPI)  │ │  (FastAPI)  │ │  (FastAPI)  │           │
│  └─────────────┘ └─────────────┘ └─────────────┘           │
└─────────────────────┬───────────────────────────────────────┘
                      │
          ┌───────────▼─────────────┐
          │     数据存储层           │
          │ ┌─────────┐ ┌─────────┐  │
          │ │PostgreSQL│ │ Redis   │  │
          │ │(主数据)  │ │(缓存)   │  │
          │ └─────────┘ └─────────┘  │
          └─────────────────────────┘
```

---

## 📦 环境要求

### 最低配置要求
- **CPU**: 4核心 (推荐8核心)
- **内存**: 8GB RAM (推荐16GB)
- **存储**: 100GB SSD (推荐200GB)
- **网络**: 100Mbps带宽
- **操作系统**: Ubuntu 20.04+ / CentOS 8+ / Docker支持

### 软件依赖
- **Docker**: 20.10+
- **Docker Compose**: 2.0+
- **Python**: 3.11+ (容器内)
- **PostgreSQL**: 15+
- **Redis**: 7+

---

## 🔧 部署步骤

### 1. 服务器准备

```bash
# 更新系统
sudo apt update && sudo apt upgrade -y

# 安装Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# 安装Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# 创建项目目录
sudo mkdir -p /opt/football-prediction
sudo chown $USER:$USER /opt/football-prediction
cd /opt/football-prediction
```

### 2. 代码部署

```bash
# 克隆项目
git clone https://github.com/your-org/football-prediction.git .

# 创建必要目录
mkdir -p logs data/cache data/models backups

# 设置权限
chmod +x scripts/*.sh
chmod -R 755 data/
```

### 3. 环境配置

```bash
# 复制环境配置模板
cp .env.example .env.production

# 编辑生产环境配置
nano .env.production
```

**关键配置项**:
```bash
# 环境设置
ENVIRONMENT=production
DEBUG=false

# 安全配置（必须修改）
SECRET_KEY=your-super-secret-key-must-change-in-production-32-chars
JWT_SECRET_KEY=your-jwt-secret-key-must-be-32-chars-different

# 数据库配置
DB_HOST=postgres
DB_PORT=5432
DB_NAME=football_prediction_prod
DB_USER=football_user
DB_PASSWORD=your-secure-database-password

# Redis配置
REDIS_HOST=redis
REDIS_PORT=6379

# API配置
API_HOST=0.0.0.0
API_PORT=8000
CORS_ORIGINS=https://yourdomain.com

# FotMob API配置（必须配置）
FOTMOB_BASE_URL=https://www.fotmob.com/api
FOTMOB_X_MAS_HEADER=your-fotmob-mas-header-value
FOTMOB_X_FOO_HEADER=your-fotmob-foo-header-value

# Kelly安全控制
KELLY_MAX_STAKE_PERCENTAGE=0.05
KELLY_EMERGENCY_STOP=true
KELLY_MANUAL_OVERRIDE=false
```

### 4. Docker部署

创建生产环境Docker Compose文件：

```yaml
# docker-compose.prod.yml
version: '3.8'

services:
  app:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: football-prediction-app
    restart: unless-stopped
    env_file:
      - .env.production
    ports:
      - "8000:8000"
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
      - ./backups:/app/backups
    depends_on:
      - postgres
      - redis
    networks:
      - football-net
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  postgres:
    image: postgres:15
    container_name: football-prediction-db
    restart: unless-stopped
    environment:
      POSTGRES_DB: football_prediction_prod
      POSTGRES_USER: football_user
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./backups:/backups
    networks:
      - football-net

  redis:
    image: redis:7-alpine
    container_name: football-prediction-redis
    restart: unless-stopped
    command: redis-server --appendonly yes
    volumes:
      - redis_data:/data
    networks:
      - football-net

  nginx:
    image: nginx:alpine
    container_name: football-prediction-nginx
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/nginx/ssl
    depends_on:
      - app
    networks:
      - football-net

volumes:
  postgres_data:
  redis_data:

networks:
  football-net:
    driver: bridge
```

### 5. 启动服务

```bash
# 构建并启动服务
docker-compose -f docker-compose.prod.yml up -d --build

# 检查服务状态
docker-compose -f docker-compose.prod.yml ps

# 查看日志
docker-compose -f docker-compose.prod.yml logs -f app
```

### 6. 数据库初始化

```bash
# 运行数据库迁移
docker-compose -f docker-compose.prod.yml exec app python -m alembic upgrade head

# 创建初始数据
docker-compose -f docker-compose.prod.yml exec app python scripts/init_production_data.py
```

---

## ⚡ 定时任务配置

### Cron任务设置

```bash
# 编辑crontab
crontab -e

# 添加以下任务
# 数据收集任务 (每30分钟)
*/30 * * * * cd /opt/football-prediction && docker-compose -f docker-compose.prod.yml exec -T app python scripts/collectors/scheduled_data_collector.py

# 模型重训练 (每天凌晨2点)
0 2 * * * cd /opt/football-prediction && docker-compose -f docker-compose.prod.yml exec -T app python scripts/retrain_models.py

# 数据备份 (每天凌晨3点)
0 3 * * * cd /opt/football-prediction && docker-compose -f docker-compose.prod.yml exec -T postgres pg_dump -U football_user football_prediction_prod > backups/backup_$(date +\%Y\%m\%d).sql

# 系统健康检查 (每5分钟)
*/5 * * * * cd /opt/football-prediction && python scripts/health_check.py

# 清理旧日志 (每周日凌晨4点)
0 4 * * 0 find /opt/football-prediction/logs -name "*.log" -mtime +7 -delete

# Kelly日计数器重置 (每天凌晨0点)
0 0 * * * cd /opt/football-prediction && python scripts/reset_kelly_counters.py
```

---

## 🔒 安全配置

### SSL证书配置

```bash
# 使用Let's Encrypt获取免费SSL证书
sudo apt install certbot python3-certbot-nginx

# 获取证书
sudo certbot --nginx -d yourdomain.com

# 自动续期
sudo crontab -e
# 添加: 0 12 * * * /usr/bin/certbot renew --quiet
```

### 防火墙配置

```bash
# 配置UFW防火墙
sudo ufw enable
sudo ufw allow ssh
sudo ufw allow 80
sudo ufw allow 443
sudo ufw deny 5432  # 禁止外部访问数据库
sudo ufw deny 6379  # 禁止外部访问Redis
```

---

## 📊 监控配置

### Prometheus + Grafana监控

```yaml
# monitoring/docker-compose.monitoring.yml
version: '3.8'

services:
  prometheus:
    image: prom/prometheus
    container_name: prometheus
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--web.console.libraries=/etc/prometheus/console_libraries'
      - '--web.console.templates=/etc/prometheus/consoles'

  grafana:
    image: grafana/grafana
    container_name: grafana
    ports:
      - "3000:3000"
    volumes:
      - grafana_data:/var/lib/grafana
      - ./grafana/dashboards:/etc/grafana/provisioning/dashboards
      - ./grafana/datasources:/etc/grafana/provisioning/datasources
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin123

volumes:
  prometheus_data:
  grafana_data:
```

### 关键监控指标

1. **应用性能指标**
   - API响应时间
   - 请求成功率
   - 并发用户数
   - 错误率

2. **业务指标**
   - 预测准确率
   - 每日预测数量
   - Kelly安全拦截次数
   - 系统可用性

3. **系统资源指标**
   - CPU使用率
   - 内存使用率
   - 磁盘使用率
   - 网络流量

---

## 🔧 运维管理

### 常用管理命令

```bash
# 查看服务状态
docker-compose -f docker-compose.prod.yml ps

# 查看应用日志
docker-compose -f docker-compose.prod.yml logs -f app

# 重启应用
docker-compose -f docker-compose.prod.yml restart app

# 更新代码
git pull
docker-compose -f docker-compose.prod.yml up -d --build

# 数据库备份
docker-compose -f docker-compose.prod.yml exec postgres pg_dump -U football_user football_prediction_prod > backup.sql

# 数据库恢复
docker-compose -f docker-compose.prod.yml exec -T postgres psql -U football_user football_prediction_prod < backup.sql

# 清理Docker资源
docker system prune -f
```

### 紧急操作

```bash
# 紧急停止所有预测
curl -X POST http://localhost:8000/api/v1/emergency-stop \
  -H "Authorization: Bearer your-admin-token" \
  -d '{"reason": "Emergency stop activated"}'

# 查看Kelly安全状态
curl -H "Authorization: Bearer your-admin-token" \
  http://localhost:8000/api/v1/kelly/safety-status

# 重置日计数器
curl -X POST http://localhost:8000/api/v1/kelly/reset-daily-counters \
  -H "Authorization: Bearer your-admin-token"
```

---

## 📋 部署检查清单

### 部署前检查

- [ ] 服务器配置满足最低要求
- [ ] Docker和Docker Compose已安装
- [ ] 环境变量已正确配置
- [ ] SSL证书已配置
- [ ] 防火墙规则已设置
- [ ] 数据库密码已更改
- [ ] API密钥已配置
- [ ] 备份策略已制定

### 部署后验证

- [ ] 所有服务正常运行
- [ ] API健康检查通过
- [ ] 数据库连接正常
- [ ] Redis缓存正常
- [ ] 监控系统工作
- [ ] 日志记录正常
- [ ] 预测功能正常
- [ ] Kelly安全系统启用

### 性能测试

- [ ] API响应时间 < 200ms
- [ ] 并发处理能力 > 100 req/s
- [ ] 内存使用率 < 80%
- [ ] CPU使用率 < 70%
- [ ] 数据库查询优化

---

## 🚨 故障排查

### 常见问题

1. **应用启动失败**
   ```bash
   # 检查日志
   docker-compose -f docker-compose.prod.yml logs app

   # 检查环境变量
   docker-compose -f docker-compose.prod.yml exec app env | grep -E "(DB_|REDIS_|FOTMOB_)"
   ```

2. **数据库连接失败**
   ```bash
   # 检查数据库状态
   docker-compose -f docker-compose.prod.yml exec postgres pg_isready -U football_user

   # 检查网络连接
   docker-compose -f docker-compose.prod.yml exec app ping postgres
   ```

3. **预测准确率下降**
   ```bash
   # 检查模型数据更新状态
   curl -H "Authorization: Bearer your-admin-token" \
     http://localhost:8000/api/v1/models/status

   # 重新训练模型
   docker-compose -f docker-compose.prod.yml exec app python scripts/retrain_models.py
   ```

### 紧急恢复

1. **服务完全宕机**
   ```bash
   # 强制重启所有服务
   docker-compose -f docker-compose.prod.yml down
   docker-compose -f docker-compose.prod.yml up -d

   # 检查系统资源
   df -h
   free -h
   docker system df
   ```

2. **数据损坏**
   ```bash
   # 从备份恢复
   docker-compose -f docker-compose.prod.yml down
   # 恢复数据库文件
   docker-compose -f docker-compose.prod.yml up -d
   ```

---

## 📞 联系支持

- **技术支持**: tech-support@football-prediction.com
- **紧急响应**: emergency@football-prediction.com
- **文档地址**: https://docs.football-prediction.com
- **监控面板**: https://monitor.football-prediction.com

---

## 📝 更新日志

### v2.0.0 (Sprint 8)
- ✅ 添加生产环境安全控制
- ✅ 集成Kelly风险控制阀门
- ✅ 完善API压力测试
- ✅ 清理技术债务
- ✅ 生成生产部署文档

### 部署状态
- **最后更新**: 2024-12-18
- **版本**: v2.0.0-production
- **状态**: ✅ Production Ready

---

**⚠️ 重要提醒**:
1. 在生产环境部署前，请务必修改所有默认密码和密钥
2. 定期备份重要数据和配置文件
3. 监控系统运行状态，及时处理异常
4. 保持系统和依赖的及时更新

**🎉 祝您部署成功！**