# 🚀 足球预测系统 - 生产环境部署指南

**版本**: v2.0.0-Stable
**更新时间**: 2025-12-17
**部署方式**: Docker Compose + Nginx 反向代理

## 📋 概览

本指南提供了足球预测系统的完整生产环境部署配置，包括：

- ✅ Nginx 反向代理配置
- ✅ 优化的 Docker Compose 配置
- ✅ Multi-stage 前端 Dockerfile
- ✅ 完整的容器网络和安全配置
- ✅ 一键启动命令

## 🏗️ 架构组件

### 核心服务
- **Frontend**: Next.js 14 + TypeScript (端口 3000)
- **Backend**: FastAPI + Python 3.11 (端口 8000)
- **Database**: PostgreSQL 15 (内部端口 5432)
- **Cache**: Redis 7 (内部端口 6379)
- **Proxy**: Nginx (端口 80, 可扩展 443)

### 可选服务
- **Celery Worker**: 后台任务处理器
- **Celery Beat**: 定时任务调度器

## 📁 文件结构

```
FootballPrediction/
├── docker-compose.prod.yml          # 生产环境 Docker Compose
├── frontend/
│   ├── Dockerfile.prod              # 生产前端 Dockerfile
│   └── next.config.ts               # Next.js 生产配置
├── deploy/
│   └── nginx/
│       └── nginx.conf               # Nginx 反向代理配置
└── docs/
    └── production-deployment.md     # 本部署指南
```

## ⚙️ 环境准备

### 1. 环境变量配置

创建 `.env.production` 文件：

```bash
# 数据库配置
DB_PASSWORD=your_secure_password_here

# Redis 配置
REDIS_PASSWORD=your_redis_password_here

# CORS 配置
CORS_ORIGINS=http://localhost,https://yourdomain.com

# 外部 API 配置
FOTMOB_X_MAS_HEADER=your_fotmob_header
FOTMOB_X_FOO_HEADER=your_fotmob_header
```

### 2. 端口检查

确保以下端口可用：
- `80` - Nginx 主端口
- `443` - HTTPS (可选)
- 内部端口由 Docker 管理

## 🚀 一键部署

### 基础部署

```bash
# 启动完整生产环境
docker-compose -f docker-compose.prod.yml up -d

# 查看服务状态
docker-compose -f docker-compose.prod.yml ps

# 查看日志
docker-compose -f docker-compose.prod.yml logs -f
```

### 包含后台任务

```bash
# 启动包含 Celery 服务的完整环境
docker-compose -f docker-compose.prod.yml --profile celery up -d
```

## 🛠️ 配置详解

### Nginx 配置特点

- **反向代理**: API 请求代理到后端 (8000 端口)
- **静态资源**: 前端资源直接服务 (3000 端口)
- **Gzip 压缩**: 自动压缩响应内容
- **安全头部**: XSS 保护、内容类型检查等
- **健康检查**: 自动检测后端服务状态

### Docker 优化

#### Frontend (`frontend/Dockerfile.prod`)
- **Multi-stage 构建**: 依赖构建 + 运行环境分离
- **Standalone 模式**: 只保留必要的运行时文件
- **镜像大小**: 目标 < 150MB
- **Non-root 用户**: 增强安全性

#### Backend (主 Dockerfile)
- **健康检查**: 内置服务状态检测
- **资源限制**: CPU 和内存使用限制
- **重启策略**: 自动故障恢复

### 安全配置

- **网络隔离**: 使用自定义 Docker 网络
- **权限控制**: 非 root 用户运行容器
- **环境变量**: 敏感信息通过环境变量传递
- **健康监控**: 全面的服务健康检查

## 🔍 验证部署

### 健康检查

```bash
# 检查服务状态
docker-compose -f docker-compose.prod.yml exec app curl -f http://localhost:8000/health

# 检查前端
docker-compose -f docker-compose.prod.yml exec frontend curl -f http://localhost:3000

# 检查 Nginx
curl -f http://localhost/health
```

### 访问应用

- **主应用**: http://localhost
- **API 文档**: http://localhost/api/docs (生产环境建议关闭)
- **健康检查**: http://localhost/health

## 📊 监控和日志

### 日志查看

```bash
# 查看所有服务日志
docker-compose -f docker-compose.prod.yml logs

# 实时跟踪特定服务
docker-compose -f docker-compose.prod.yml logs -f app
docker-compose -f docker-compose.prod.yml logs -f frontend
docker-compose -f docker-compose.prod.yml logs -f nginx

# 查看最近的错误日志
docker-compose -f docker-compose.prod.yml logs --tail=50 app | grep ERROR
```

### 性能监控

```bash
# 查看资源使用情况
docker stats

# 查看容器详细信息
docker-compose -f docker-compose.prod.yml ps
```

## 🔄 维护操作

### 滚动更新

```bash
# 更新应用代码
docker-compose -f docker-compose.prod.yml pull
docker-compose -f docker-compose.prod.yml up -d --no-deps app frontend

# 重启特定服务
docker-compose -f docker-compose.prod.yml restart nginx
```

### 数据备份

```bash
# 备份数据库
docker-compose -f docker-compose.prod.yml exec db pg_dump -U football_user football_prediction_prod > backup_$(date +%Y%m%d).sql

# 恢复数据库
docker-compose -f docker-compose.prod.yml exec -T db psql -U football_user football_prediction_prod < backup_20251217.sql
```

### 清理操作

```bash
# 清理未使用的镜像和容器
docker system prune -f

# 清理所有资源（包括未使用的数据卷）
docker system prune -a -f --volumes
```

## 🔧 故障排除

### 常见问题

#### 1. 端口冲突
```bash
# 检查端口占用
sudo netstat -tulpn | grep :80
# 修改 docker-compose.prod.yml 中的端口映射
```

#### 2. 数据库连接失败
```bash
# 检查数据库容器状态
docker-compose -f docker-compose.prod.yml ps db
# 查看数据库日志
docker-compose -f docker-compose.prod.yml logs db
```

#### 3. 前端构建失败
```bash
# 重新构建前端镜像
docker-compose -f docker-compose.prod.yml build --no-cache frontend
```

#### 4. Nginx 配置错误
```bash
# 测试 Nginx 配置
docker-compose -f docker-compose.prod.yml exec nginx nginx -t
# 重新加载配置
docker-compose -f docker-compose.prod.yml exec nginx nginx -s reload
```

## 🚨 生产环境建议

### 安全增强
1. **HTTPS**: 配置 SSL 证书
2. **防火墙**: 限制不必要的端口访问
3. **监控**: 部署 Prometheus + Grafana
4. **备份**: 定期自动备份策略

### 性能优化
1. **CDN**: 使用内容分发网络
2. **缓存**: Redis 缓存优化
3. **负载均衡**: 多实例部署
4. **数据库**: PostgreSQL 性能调优

### 扩展性
1. **微服务**: 拆分为独立服务
2. **容器编排**: 使用 Kubernetes
3. **CI/CD**: 自动化部署流水线

## 📞 支持

如有部署问题，请检查：
1. Docker 和 Docker Compose 版本
2. 系统资源可用性
3. 网络连接和防火墙设置
4. 环境变量配置

---

**部署成功后，您的足球预测系统将在 http://localhost 可用！** 🎉