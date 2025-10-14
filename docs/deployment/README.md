# Football Prediction System 部署文档

## 📋 目录

1. [系统概述](#系统概述)
2. [系统架构](#系统架构)
3. [环境要求](#环境要求)
4. [快速部署](#快速部署)
5. [详细部署指南](#详细部署指南)
6. [配置管理](#配置管理)
7. [监控与日志](#监控与日志)
8. [备份与恢复](#备份与恢复)
9. [故障排查](#故障排查)
10. [运维手册](#运维手册)

## 系统概述

Football Prediction System 是一个企业级的足球预测平台，基于微服务架构设计，具备高可用、高性能和可扩展的特性。

### 核心功能
- 足球比赛预测
- 实时赔率分析
- 用户积分排行榜
- 统计数据展示
- 历史数据分析

### 技术栈
- **后端框架**: FastAPI (Python 3.11+)
- **数据库**: PostgreSQL 15+
- **缓存**: Redis 7.2+
- **消息队列**: Celery + Redis
- **容器化**: Docker + Docker Compose
- **监控**: Prometheus + Grafana + Loki
- **追踪**: Jaeger + OpenTelemetry

## 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                    Load Balancer (Nginx)                     │
└─────────────────────┬───────────────────────────────────────┘
                      │
    ┌─────────────────┼─────────────────┐
    │                 │                 │
┌───▼───┐         ┌───▼───┐         ┌───▼───┐
│API-1  │         │API-2  │         │API-3  │
└───┬───┘         └───┬───┘         └───┬───┘
    │                 │                 │
    └─────────────────┼─────────────────┘
                      │
              ┌───────▼───────┐
              │   Database    │
              │  PostgreSQL   │
              └───────┬───────┘
                      │
              ┌───────▼───────┐
              │     Cache     │
              │    Redis      │
              └───────────────┘

监控和日志服务：
- Prometheus (指标收集)
- Grafana (可视化)
- Loki (日志聚合)
- Jaeger (分布式追踪)
```

## 环境要求

### 硬件要求

#### 最低配置（开发/测试）
- CPU: 2 cores
- 内存: 4GB RAM
- 存储: 50GB SSD
- 网络: 100Mbps

#### 推荐配置（生产）
- CPU: 8+ cores
- 内存: 16GB+ RAM
- 存储: 500GB+ SSD
- 网络: 1Gbps

#### 高可用配置
- API服务: 3+ 节点
- 数据库: 主从复制
- Redis: 哨兵模式或集群模式
- 负载均衡器: 多实例

### 软件要求

- **操作系统**: Ubuntu 20.04+ / CentOS 8+ / RHEL 8+
- **Docker**: 20.10+
- **Docker Compose**: 2.0+
- **Python**: 3.11+
- **Git**: 2.25+

## 快速部署

### 1. 克隆项目

```bash
git clone https://github.com/your-org/FootballPrediction.git
cd FootballPrediction
```

### 2. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env 文件，配置必要的环境变量
vim .env
```

### 3. 启动服务

```bash
# 启动所有服务
docker-compose up -d

# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f
```

### 4. 初始化数据库

```bash
# 运行数据库迁移
docker-compose exec api python -m alembic upgrade head

# 创建初始数据
docker-compose exec api python scripts/init_data.py
```

### 5. 验证部署

```bash
# 健康检查
curl http://localhost:8000/api/health

# 访问API文档
open http://localhost:8000/docs

# 访问监控面板
open http://localhost:3000  # Grafana
open http://localhost:16686  # Jaeger
```

## 详细部署指南

### 1. 系统准备

#### 1.1 安装Docker

```bash
# Ubuntu/Debian
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# CentOS/RHEL
sudo yum install -y yum-utils
sudo yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
sudo yum install -y docker-ce docker-ce-cli containerd.io
sudo systemctl start docker
sudo systemctl enable docker
```

#### 1.2 安装Docker Compose

```bash
# 下载Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```

#### 1.3 配置系统参数

```bash
# 编辑系统限制
sudo vim /etc/sysctl.conf

# 添加以下内容
fs.file-max = 65536
net.core.somaxconn = 65535
net.ipv4.tcp_max_syn_backlog = 65535
vm.max_map_count = 262144

# 应用配置
sudo sysctl -p
```

### 2. 应用部署

#### 2.1 构建镜像

```bash
# 构建应用镜像
docker build -t football-prediction:latest .

# 或使用多阶段构建
docker build -f Dockerfile.prod -t football-prediction:prod .
```

#### 2.2 配置SSL证书

```bash
# 使用Let's Encrypt
sudo apt install certbot
sudo certbot certonly --standalone -d api.footballprediction.com

# 或使用自签名证书
mkdir -p config/ssl
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout config/ssl/server.key \
    -out config/ssl/server.crt
```

#### 2.3 配置Nginx

```bash
# 复制Nginx配置
sudo cp config/nginx/nginx.conf /etc/nginx/sites-available/football-prediction
sudo ln -s /etc/nginx/sites-available/football-prediction /etc/nginx/sites-enabled/

# 测试配置
sudo nginx -t

# 重启Nginx
sudo systemctl restart nginx
```

### 3. 数据库部署

#### 3.1 PostgreSQL部署

```bash
# 使用Docker部署
docker-compose -f docker-compose.database.yml up -d

# 或在独立服务器部署
sudo apt install postgresql postgresql-contrib
sudo systemctl start postgresql
sudo systemctl enable postgresql

# 创建数据库
sudo -u postgres createdb football_prediction
sudo -u postgres createuser --interactive
```

#### 3.2 数据库优化

```bash
# 复制优化配置
sudo cp config/database/postgresql.conf /etc/postgresql/15/main/
sudo chown postgres:postgres /etc/postgresql/15/main/postgresql.conf

# 重启PostgreSQL
sudo systemctl restart postgresql

# 运行优化脚本
python scripts/optimize-database.py
```

### 4. 缓存部署

```bash
# 启动Redis集群
./scripts/redis-manager.sh start

# 验证集群状态
./scripts/redis-manager.sh status

# 配置Redis哨兵（可选）
docker-compose -f docker-compose.redis-sentinel.yml up -d
```

### 5. 监控部署

```bash
# 启动监控栈
docker-compose -f docker-compose.monitoring.yml up -d

# 启动日志收集
./scripts/start-loki.sh start

# 启动分布式追踪
./scripts/start-tracing.sh start
```

## 配置管理

### 环境变量配置

创建 `.env` 文件：

```bash
# 应用配置
ENVIRONMENT=production
DEBUG=false
SECRET_KEY=your-super-secret-key-here
API_HOST=0.0.0.0
API_PORT=8000

# 数据库配置
DATABASE_URL=postgresql://user:password@localhost:5432/football_prediction
DB_HOST=localhost
DB_PORT=5432
DB_NAME=football_prediction
DB_USER=postgres
DB_PASSWORD=your-db-password

# Redis配置
REDIS_URL=redis://localhost:6379/0
REDIS_PASSWORD=your-redis-password
REDIS_HOST=localhost
REDIS_PORT=6379

# JWT配置
JWT_SECRET_KEY=your-jwt-secret-key
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7

# 邮件配置
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password

# 监控配置
PROMETHEUS_URL=http://localhost:9090
GRAFANA_URL=http://localhost:3000
JAEGER_ENDPOINT=http://localhost:14268/api/traces

# 备份配置
BACKUP_S3_BUCKET=football-prediction-backups
BACKUP_RETENTION_DAYS=30
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key
```

### 配置文件结构

```
config/
├── api/
│   ├── appsettings.json
│   └── logging.yaml
├── database/
│   ├── postgresql.conf
│   └── pg_hba.conf
├── redis/
│   ├── redis.conf
│   └── sentinel.conf
├── nginx/
│   ├── nginx.conf
│   └── ssl/
├── monitoring/
│   ├── prometheus.yml
│   ├── alertmanager.yml
│   └── grafana/
└── ssl/
    ├── server.crt
    └── server.key
```

## 监控与日志

### 监控配置

#### Prometheus指标

- 系统指标：CPU、内存、磁盘、网络
- 应用指标：请求量、响应时间、错误率
- 数据库指标：连接数、查询时间、锁等待
- 缓存指标：命中率、内存使用、键数量

#### 告警规则

- 服务不可用
- 响应时间过长
- 错误率过高
- 资源使用率过高
- 数据库连接问题

### 日志管理

#### 日志级别

- DEBUG：调试信息
- INFO：一般信息
- WARNING：警告信息
- ERROR：错误信息
- CRITICAL：严重错误

#### 日志轮转

```bash
# 配置logrotate
sudo vim /etc/logrotate.d/football-prediction

/var/log/football-prediction/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 644 app app
    postrotate
        systemctl reload football-prediction
    endscript
}
```

## 备份与恢复

### 自动备份配置

```bash
# 配置定时备份
crontab -e

# 添加以下内容
0 2 * * * /path/to/scripts/backup-database.py backup
0 3 * * 0 /path/to/scripts/backup-cleanup.sh
```

### 备份策略

- **全量备份**：每天凌晨2点
- **增量备份**：每6小时
- **WAL日志**：实时归档
- **保留策略**：本地30天，云存储90天

### 恢复流程

1. 停止应用服务
2. 恢复数据库
3. 验证数据完整性
4. 重启应用服务
5. 验证系统功能

## 故障排查

详细故障排查指南请参考 [故障排查手册](troubleshooting.md)

## 运维手册

详细运维操作指南请参考 [运维手册](operations.md)

## 部署检查清单

### 部署前检查

- [ ] 系统资源满足要求
- [ ] 依赖软件已安装
- [ ] 网络配置正确
- [ ] 防火墙规则配置
- [ ] SSL证书准备
- [ ] 环境变量配置
- [ ] 数据库备份准备

### 部署后验证

- [ ] 所有服务正常启动
- [ ] 健康检查通过
- [ ] 数据库连接正常
- [ ] 缓存服务正常
- [ ] 监控系统运行
- [ ] 日志收集正常
- [ ] API功能测试
- [ ] 性能基准测试

### 上线检查

- [ ] 负载均衡配置
- [ ] 域名解析配置
- [ ] HTTPS证书有效
- [ ] 告警通知配置
- [ ] 备份任务运行
- [ ] 运维文档更新
- [ ] 团队培训完成

## 支持与帮助

如遇到部署问题，请：

1. 查阅故障排查手册
2. 检查日志文件
3. 联系技术支持团队
4. 提交Issue到GitHub

---

**更新时间**: 2024-03-15
**版本**: 1.0.0
**维护者**: Football Prediction Team
