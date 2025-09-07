# 🐳 AICultureKit Docker 部署指南

## 🎯 快速开始

### 1. 🚀 生产环境部署
```bash
# 克隆项目
git clone https://github.com/xupeng211/AICultureKit.git
cd AICultureKit

# 配置环境变量
cp env.example .env
# 编辑 .env 文件设置实际值

# 启动生产环境
docker-compose up -d

# 访问应用
open http://localhost:8000
```

### 2. 🛠️ 开发环境
```bash
# 启动开发环境（支持热重载）
docker-compose -f docker-compose.dev.yml up -d

# 查看服务状态
docker-compose ps

# 访问开发工具
open http://localhost:8000      # 主应用
open http://localhost:8080      # Adminer (数据库管理)
open http://localhost:8081      # Redis Commander
```

## 🏗️ CI/CD 自动化

### GitHub Actions 工作流

#### 🔄 主要流水线 (`.github/workflows/ci.yml`)
- **触发条件**: Push到main/develop分支，PR到main/develop
- **流程**:
  1. 代码质量检查 (black, flake8, mypy, bandit)
  2. 单元测试 + 覆盖率检查
  3. Docker镜像构建
  4. 推送到GitHub Container Registry

#### 📦 发布流水线 (`.github/workflows/release.yml`)
- **触发条件**: 创建Release或手动触发
- **功能**: 构建带版本标签的镜像

### 🐳 Docker镜像

构建完成后，镜像会自动推送到：
- `ghcr.io/xupeng211/aiculturekit:latest` (最新版本)
- `ghcr.io/xupeng211/aiculturekit:main` (主分支)
- `ghcr.io/xupeng211/aiculturekit:develop` (开发分支)

## 📋 可用命令

### Docker操作命令
```bash
# 使用Makefile.docker中的命令
make -f Makefile.docker docker-build    # 构建生产镜像
make -f Makefile.docker docker-dev      # 启动开发环境
make -f Makefile.docker docker-logs     # 查看日志
make -f Makefile.docker docker-shell    # 进入容器
make -f Makefile.docker docker-health   # 健康检查
make -f Makefile.docker docker-clean    # 清理资源
```

### 直接使用Docker命令
```bash
# 构建镜像
docker build -t aiculturekit:latest .

# 运行容器
docker run -p 8000:8000 aiculturekit:latest

# 查看运行状态
docker ps

# 查看日志
docker logs <container_id>
```

## 🌐 服务端点

| 服务 | 端口 | 说明 |
|------|------|------|
| 主应用 | 8000 | FastAPI应用 |
| PostgreSQL | 5432 | 数据库 |
| Redis | 6379 | 缓存 |
| Adminer | 8080 | 数据库管理 (仅开发环境) |
| Redis Commander | 8081 | Redis管理 (仅开发环境) |

## 🔧 环境配置

### 必需环境变量
```bash
# 从 env.example 复制并修改
cp env.example .env

# 关键配置项
ENVIRONMENT=production          # 环境类型
SECRET_KEY=your-secret-key     # 应用密钥
DATABASE_URL=postgresql://...   # 数据库连接
REDIS_URL=redis://...          # Redis连接
```

### 生产环境配置
```bash
# 生产环境建议配置
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO
CORS_ORIGINS=https://yourdomain.com
```

## 📊 监控和健康检查

### 健康检查端点
- `GET /health` - 基础健康检查
- `GET /api/status` - 详细状态信息

### 日志监控
```bash
# 查看实时日志
docker-compose logs -f app

# 查看特定服务日志
docker-compose logs postgres
docker-compose logs redis
```

## 🚀 部署到生产环境

### 使用预构建镜像
```yaml
# docker-compose.prod.yml
version: '3.8'
services:
  app:
    image: ghcr.io/xupeng211/aiculturekit:latest
    ports:
      - "8000:8000"
    environment:
      - ENVIRONMENT=production
    # 其他配置...
```

### 使用Docker Swarm
```bash
# 初始化Swarm
docker swarm init

# 部署Stack
docker stack deploy -c docker-compose.yml aiculturekit
```

### 使用Kubernetes
```bash
# 创建命名空间
kubectl create namespace aiculturekit

# 部署应用
kubectl apply -f k8s/
```

## 🔒 安全配置

### 生产环境安全清单
- [ ] 更改默认密码和密钥
- [ ] 配置HTTPS (SSL/TLS)
- [ ] 设置防火墙规则
- [ ] 启用容器安全扫描
- [ ] 配置日志聚合
- [ ] 设置监控告警

### 镜像安全
- ✅ 非root用户运行
- ✅ 最小化镜像体积
- ✅ 多阶段构建
- ✅ 安全依赖扫描
- ✅ 定期更新基础镜像

## 🐛 故障排除

### 常见问题

#### 1. 容器启动失败
```bash
# 查看详细错误
docker-compose logs app

# 检查配置
docker-compose config
```

#### 2. 数据库连接错误
```bash
# 检查数据库容器状态
docker-compose ps postgres

# 测试数据库连接
docker-compose exec app python -c "import psycopg2; print('OK')"
```

#### 3. 端口冲突
```bash
# 查看端口占用
netstat -tulpn | grep :8000

# 修改端口映射
# 编辑 docker-compose.yml 中的端口配置
```

### 性能优化

#### 1. 镜像优化
```dockerfile
# 使用多阶段构建
FROM python:3.11-slim as builder
# 构建阶段

FROM python:3.11-slim as runtime
# 运行阶段
```

#### 2. 缓存优化
```bash
# 启用Docker BuildKit
export DOCKER_BUILDKIT=1

# 使用缓存挂载
docker build --cache-from aiculturekit:latest .
```

## 📈 监控和指标

### 内置监控
- Docker健康检查
- 应用健康端点
- 日志聚合

### 可选监控方案
- Prometheus + Grafana
- ELK Stack (Elasticsearch, Logstash, Kibana)
- Datadog
- New Relic

---

## 🎯 下一步

1. **配置GitHub Secrets** - 为自动部署设置密钥
2. **设置域名和SSL** - 配置HTTPS访问
3. **添加监控** - 集成APM和日志系统
4. **扩展功能** - 根据业务需求添加新功能

**🎉 恭喜！您的AICultureKit已经具备了企业级的容器化CI/CD能力！**
