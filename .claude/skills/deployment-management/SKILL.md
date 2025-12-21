---
name: deployment-management
description: Manage application deployment including Docker containers, production environments, and service orchestration. Use when deploying to production, managing Docker services, or handling deployment rollbacks.
---

# Deployment Management Skill

## 概述
专业的应用部署管理技能，支持Docker容器化部署、生产环境管理和自动化运维操作。

## 核心功能

### 1. Docker容器管理
- **容器编排**: docker-compose服务管理
- **镜像构建**: 自动化Docker镜像构建
- **服务健康检查**: 容器健康状态监控
- **资源管理**: CPU和内存限制配置

### 2. 生产环境部署
- **蓝绿部署**: 零停机部署策略
- **滚动更新**: 渐进式服务更新
- **回滚机制**: 快速回滚到稳定版本
- **环境配置**: 多环境部署配置管理

### 3. 自动化运维
- **一键部署**: 自动化部署脚本
- **服务发现**: 自动服务注册和发现
- **负载均衡**: 流量分发和负载管理
- **日志管理**: 集中化日志收集

## 部署架构

### 环境分层
```
Development → Staging → Production
    ↓            ↓           ↓
 开发环境      测试环境      生产环境
docker-compose  docker-compose  docker-compose.trial
```

### 服务组件
- **App Service**: 核心应用服务
- **Database**: PostgreSQL数据库
- **Cache**: Redis缓存服务
- **Monitoring**: 监控服务栈
- **Load Balancer**: 负载均衡器

## 使用方法

### 开发环境部署
```bash
# 快速启动开发环境
./scripts/docker-manager.sh dev

# 带数据收集器的完整环境
./scripts/docker-manager.sh dev --collectors

# 调试模式启动
./scripts/docker-manager.sh dev --debug
```

### 生产环境部署
```bash
# 部署到试运营环境
./scripts/docker-manager.sh trial

# 生产环境部署
python scripts/deploy_production.py

# 查看部署状态
./scripts/docker-manager.sh status
```

### 服务管理
```bash
# 查看服务日志
./scripts/docker-manager.sh logs -f app

# 重启所有服务
./scripts/docker-manager.sh restart

# 进入容器shell
./scripts/docker-manager.sh shell

# 健康检查
./scripts/docker-manager.sh health
```

## 配置管理

### 环境配置文件
```yaml
# docker-compose.yml (开发环境)
version: '3.8'
services:
  app:
    build: .
    environment:
      - ENVIRONMENT=development
      - DEBUG=true
    volumes:
      - ./src:/app/src

# docker-compose.trial.yml (试运营环境)
version: '3.8'
services:
  app:
    image: football-prediction:latest
    environment:
      - ENVIRONMENT=trial
      - DEBUG=false
    deploy:
      resources:
        limits:
          cpus: '1.5'
          memory: 2G
```

### 环境变量配置
```bash
# .env.dev (开发环境)
ENVIRONMENT=development
DEBUG=true
API_HOST=0.0.0.0
API_PORT=8000

# .env.trial (试运营环境)
ENVIRONMENT=trial
DEBUG=false
API_HOST=0.0.0.0
API_PORT=8000
DB_NAME=football_prediction_prod
```

## 部署脚本

### 主部署脚本
```python
# scripts/deploy_production.py
import os
import subprocess
import logging

class ProductionDeployment:
    def __init__(self):
        self.env = os.getenv('ENVIRONMENT', 'production')

    def deploy(self):
        """生产环境部署流程"""
        try:
            # 1. 构建镜像
            self.build_image()

            # 2. 运行测试
            self.run_tests()

            # 3. 备份当前版本
            self.backup_current()

            # 4. 部署新版本
            self.deploy_new_version()

            # 5. 健康检查
            self.health_check()

        except Exception as e:
            # 6. 回滚操作
            self.rollback()
            raise e
```

### Docker管理脚本
```bash
#!/bin/bash
# scripts/docker-manager.sh

case "$1" in
  dev)
    echo "Starting development environment..."
    docker-compose -f docker-compose.yml up -d --build
    ;;
  trial)
    echo "Starting trial environment..."
    docker-compose -f docker-compose.trial.yml up -d
    ;;
  status)
    echo "Checking service status..."
    docker-compose ps
    ;;
  logs)
    docker-compose logs -f ${2:-app}
    ;;
esac
```

## 部署策略

### 1. 滚动更新（Rolling Update）
```yaml
# docker-compose.yml
deploy:
  update_config:
    parallelism: 1
    delay: 10s
    failure_action: rollback
    order: start-first
```

### 2. 蓝绿部署（Blue-Green）
```python
def blue_green_deployment():
    """蓝绿部署实现"""
    # 1. 部署绿色环境
    deploy_to_green()

    # 2. 验证绿色环境
    if health_check('green'):
        # 3. 切换流量
        switch_traffic('green')
        # 4. 清理蓝色环境
        cleanup_blue()
    else:
        # 5. 回滚
        rollback_to_blue()
```

### 3. 金丝雀发布（Canary）
```python
def canary_deployment():
    """金丝雀发布实现"""
    # 1. 部署金丝雀版本
    deploy_canary(percentage=10)

    # 2. 监控金丝雀性能
    if monitor_canary(duration='5m'):
        # 3. 逐步扩大流量
        expand_canary(percentage=50, 100)
    else:
        # 4. 回滚金丝雀
        rollback_canary()
```

## 健康检查

### 应用健康检查
```python
# Dockerfile
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

# docker-compose.yml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
  interval: 30s
  timeout: 10s
  retries: 3
  start_period: 40s
```

### 服务依赖检查
```bash
#!/bin/bash
# scripts/health_check.sh

# 检查数据库连接
docker-compose exec -T db pg_isready -U football_user

# 检查Redis连接
docker-compose exec -T redis redis-cli ping

# 检查应用健康
curl -f http://localhost:8000/api/health
```

## 监控和日志

### 部署监控
```python
# 部署指标收集
DEPLOYMENT_METRICS = {
    'deployment_duration': Histogram('deployment_duration_seconds'),
    'deployment_success': Counter('deployment_success_total'),
    'rollback_count': Counter('rollback_count_total'),
    'service_uptime': Gauge('service_uptime_seconds')
}
```

### 日志聚合
```yaml
# docker-compose.yml
logging:
  driver: "json-file"
  options:
    max-size: "10m"
    max-file: "3"
    labels: "service,environment"
```

## 安全配置

### 网络安全
```yaml
# docker-compose.yml
networks:
  frontend:
    driver: bridge
  backend:
    driver: bridge
    internal: true  # 内部网络，不访问外网
```

### 密钥管理
```bash
# 使用Docker secrets
echo "db_password" | docker secret create db_password -

# 或使用环境变量文件
docker-compose --env-file .env.prod up -d
```

## 故障处理

### 常见部署问题

1. **镜像构建失败**
   ```bash
   # 查看构建日志
   docker-compose build --no-cache app

   # 清理Docker缓存
   docker system prune -a
   ```

2. **服务启动失败**
   ```bash
   # 查看服务日志
   docker-compose logs app

   # 检查端口占用
   netstat -tulpn | grep :8000
   ```

3. **数据库连接问题**
   ```bash
   # 检查数据库状态
   docker-compose exec db pg_isready

   # 查看数据库日志
   docker-compose logs db
   ```

### 自动恢复机制
```python
def auto_recovery(service_name):
    """服务自动恢复"""
    max_retries = 3
    retry_count = 0

    while retry_count < max_retries:
        if is_service_healthy(service_name):
            return True

        print(f"Service {service_name} unhealthy, restarting...")
        restart_service(service_name)
        retry_count += 1
        time.sleep(10)

    return False
```

## 性能优化

### 构建优化
```dockerfile
# 多阶段构建减少镜像大小
FROM python:3.11-slim as builder
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

FROM python:3.11-slim
WORKDIR /app
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY . .
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 运行时优化
```yaml
# 资源限制
deploy:
  resources:
    limits:
      cpus: '2.0'
      memory: 2G
    reservations:
      cpus: '1.0'
      memory: 1G
```

## 最佳实践

### 1. 部署前检查
- **测试验证**: 所有测试必须通过
- **代码审查**: 代码必须经过审查
- **环境准备**: 目标环境已就绪
- **回滚准备**: 回滚方案已准备

### 2. 部署过程
- **渐进式部署**: 避免一次性全量更新
- **实时监控**: 密切关注部署指标
- **快速响应**: 问题及时发现和处理
- **记录日志**: 详细记录部署过程

### 3. 部署后验证
- **功能测试**: 验证核心功能正常
- **性能测试**: 确认性能符合预期
- **监控检查**: 监控指标正常
- **用户验证**: 用户反馈收集

## 相关工具

- **Docker**: 容器化平台
- **Docker Compose**: 多容器编排
- **Kubernetes**: 大规模容器编排（可选）
- **Jenkins/CI/CD**: 自动化部署流水线
- **Terraform**: 基础设施即代码

## 注意事项

### 部署安全
- **密钥保护**: 绝不提交密钥到代码库
- **网络隔离**: 生产环境网络隔离
- **访问控制**: 限制部署权限
- **审计日志**: 记录所有部署操作

### 数据安全
- **备份策略**: 定期数据备份
- **加密传输**: 敏感数据传输加密
- **权限最小化**: 最小权限原则
- **合规要求**: 满足数据保护法规