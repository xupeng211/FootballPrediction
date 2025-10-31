# Issue #184: Docker环境稳定性优化

## 🚨 问题描述

Issue #180验证和后续测试过程中发现，Docker容器存在稳定性问题，主要表现为应用容器持续重启、环境配置不一致、健康检查失败等问题，影响系统在容器化环境中的稳定运行。

## 📊 问题影响范围

### Docker环境问题统计
- **容器重启频率**: 持续重启，无法稳定运行
- **健康检查状态**: 健康检查失败，服务不可用
- **环境配置问题**: 路径和依赖配置不一致
- **资源使用**: 内存和CPU使用异常

### 典型错误模式
```
Container is restarting (1) Less than a second ago
健康检查失败: Connection refused
导入错误: No module named 'src'
启动失败: uvicorn启动超时
资源限制: Memory limit exceeded
```

## 🎯 修复目标

### 成功标准
- **容器稳定性**: 容器能够稳定运行且不重启
- **健康检查**: 健康检查100%通过
- **环境一致性**: Docker环境与本地环境一致
- **资源优化**: 内存和CPU使用在合理范围内

### 验收标准
1. ✅ Docker容器稳定运行超过30分钟
2. ✅ 应用健康检查100%通过
3. ✅ 所有环境配置文件正确加载
4. ✅ 内存使用不超过限制
5. ✅ 启动时间在合理范围内

## 🔧 修复计划

### Phase 1: Docker配置优化 (P0-A)

#### 1.1 Dockerfile优化
```dockerfile
# Dockerfile.production
FROM python:3.11-slim

# 设置工作目录
WORKDIR /app

# 系统依赖
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    libpq-dev \
    git \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# 复制依赖文件
COPY requirements/ requirements/

# 安装Python依赖
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements/requirements.lock

# 复制应用代码
COPY . .

# 创建非root用户
RUN groupadd -r -g 1001 appuser && \
    useradd -r -u 1001 -g appuser appuser

# 设置权限
RUN chown -R appuser:appuser /app
USER appuser

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# 暴露端口
EXPOSE 8000

# 启动命令
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

#### 1.2 Docker Compose配置优化
```yaml
# docker-compose.yml
version: '3.8'

services:
  app:
    build:
      context: .
      dockerfile: Dockerfile.production
    container_name: footballprediction-app
    ports:
      - "8000:8000"
    environment:
      - PYTHONPATH=/app/src
      - REDIS_URL=redis://redis:6379/0
      - DATABASE_URL=postgresql://postgres:5432/football_prediction
      - LOG_LEVEL=INFO
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy
    volumes:
      - ./logs:/app/logs
      - ./tmp:/app/tmp
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

  db:
    image: postgres:15-alpine
    container_name: footballprediction-db
    environment:
      - POSTGRES_DB=football_prediction
      - POSTGRES_USER=appuser
      - POSTGRES_PASSWORD=securepassword
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U appuser -d football_prediction"]
      interval: 10s
      timeout: 5s
      retries: 5
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    container_name: footballprediction-redis
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    command: redis-server --appendonly yes
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 3s
      retries: 3
    restart: unless-stopped

volumes:
  postgres_data:
  redis_data:
```

### Phase 2: 应用启动优化 (P0-B)

#### 2.1 启动脚本优化
```bash
#!/bin/bash
# docker/entrypoint.sh
set -e

echo "🚀 启动Football Prediction应用..."

# 等待依赖服务启动
echo "⏳ 等待数据库连接..."
while ! pg_isready -h db -U appuser -d football_prediction; do
  echo "等待数据库启动..."
  sleep 2
done

echo "⏳ 等待Redis连接..."
while ! redis-cli -h redis ping; do
  echo "等待Redis启动..."
  sleep 2
done

# 设置环境变量
export PYTHONPATH=/app/src
echo "✅ Python路径设置: $PYTHONPATH"

# 创建必要目录
mkdir -p logs tmp

# 运行数据库迁移
if [ "$1" = "migrate" ]; then
    echo "🗄️ 运行数据库迁移..."
    alembic upgrade head
fi

# 启动应用
echo "🌟 启动应用服务..."
exec "$@"
```

#### 2.2 应用配置优化
```python
# src/config/docker_config.py
import os
from typing import Dict, Any

class DockerConfig:
    """Docker环境配置"""

    def __init__(self):
        self.load_environment()

    def load_environment(self):
        """加载环境变量"""
        self.database_url = os.getenv("DATABASE_URL")
        self.redis_url = os.getenv("REDIS_URL")
        self.log_level = os.getenv("LOG_LEVEL", "INFO")
        self.python_path = os.getenv("PYTHONPATH", "/app/src")

    @property
    def database_config(self) -> Dict[str, Any]:
        """数据库配置"""
        return {
            "url": self.database_url,
            "echo": True,
            "pool_size": 20,
            "max_overflow": 30,
            "pool_timeout": 30,
            "pool_recycle": 3600,
        }

    @property
    def redis_config(self) -> Dict[str, Any]:
        """Redis配置"""
        return {
            "url": self.redis_url,
            "decode_responses": True,
            "encoding": "utf-8",
            "socket_keepalive": True,
            "socket_keepalive_options": {},
        }
```

### Phase 3: 健康检查和监控 (P0-C)

#### 3.1 应用健康检查端点
```python
# src/api/health.py
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from datetime import datetime
import asyncio
import psutil

router = APIRouter(prefix="/health", tags=["health"])

class HealthResponse(BaseModel):
    status: str
    timestamp: datetime
    version: str
    uptime: float
    memory_usage: Dict[str, float]
    database_status: str
    redis_status: str

@router.get("/", response_model=HealthResponse)
async def health_check():
    """系统健康检查"""
    try:
        # 检查数据库连接
        db_status = await check_database_connection()

        # 检查Redis连接
        redis_status = await check_redis_connection()

        # 获取系统信息
        memory_info = psutil.virtual_memory()

        # 计算运行时间
        uptime = psutil.boot_time()

        return HealthResponse(
            status="healthy",
            timestamp=datetime.utcnow(),
            version="1.0.0",
            uptime=uptime,
            memory_usage={
                "total": memory_info.total,
                "available": memory_info.available,
                "used": memory_info.used,
                "percent": memory_info.percent
            },
            database_status=db_status,
            redis_status=redis_status
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Health check failed: {str(e)}"
        )

async def check_database_connection() -> str:
    """检查数据库连接"""
    try:
        from src.database.base import get_database
        db = get_database()
        await db.execute("SELECT 1")
        return "healthy"
    except Exception:
        return "unhealthy"

async def check_redis_connection() -> str:
    """检查Redis连接"""
    try:
        from src.cache.redis.manager import get_redis_manager
        redis = get_redis_manager()
        await redis.ping()
        return "healthy"
    except Exception:
        return "unhealthy"
```

#### 3.2 启动脚本优化
```python
# src/main.py (修改版)
import asyncio
import logging
import sys
import os
from pathlib import Path

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 设置Python路径
src_path = Path(__file__).parent / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

async def startup_event():
    """应用启动事件"""
    logger.info("🚀 Football Prediction应用启动中...")

    # 初始化组件
    await initialize_components()

    logger.info("✅ 应用启动完成")

async def shutdown_event():
    """应用关闭事件"""
    logger.info("🔄 应用正在关闭...")

    # 清理资源
    await cleanup_resources()

    logger.info("✅ 应用关闭完成")

async def initialize_components():
    """初始化应用组件"""
    try:
        # 初始化缓存
        from src.cache.cache_manager import get_cache_manager
        cache_manager = get_cache_manager()
        await cache_manager.initialize()

        # 初始化数据库连接
        from src.database.base import initialize_database
        await initialize_database()

        logger.info("✅ 组件初始化完成")

    except Exception as e:
        logger.error(f"❌ 组件初始化失败: {e}")
        raise

async def cleanup_resources():
    """清理资源"""
    try:
        # 清理缓存连接
        from src.cache.cache_manager import get_cache_manager
        cache_manager = get_cache_manager()
        if hasattr(cache_manager, 'disconnect'):
            await cache_manager.disconnect()

        logger.info("✅ 资源清理完成")

    except Exception as e:
        logger.error(f"❌ 资源清理失败: {e}")

if __name__ == "__main__":
    import uvicorn

    app = create_application()

    # 添加启动和关闭事件
    app.add_event_handler("startup", startup_event)
    app.add_event_handler("shutdown", shutdown_event)

    # 启动应用
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )
```

### Phase 4: 资源和性能优化 (P0-D)

#### 4.1 资源限制配置
```yaml
# docker-compose.override.yml (生产环境)
version: '3.8'

services:
  app:
    deploy:
      resources:
        limits:
          cpus: '1.0'
          memory: 1G
        reservations:
          cpus: '0.5'
          memory: 512M
    environment:
      - WORKERS=4
      - MAX_CONNECTIONS=100
      - KEEP_ALIVE=2
    ulimits:
      nofile:
        soft: 65536
        hard: 65536
```

#### 4.2 性能监控配置
```python
# src/monitoring/docker_metrics.py
import psutil
import asyncio
from datetime import datetime

class DockerMetricsCollector:
    """Docker环境指标收集器"""

    def __init__(self):
        self.start_time = datetime.utcnow()

    def get_container_metrics(self) -> Dict[str, Any]:
        """获取容器指标"""
        memory = psutil.virtual_memory()
        cpu = psutil.cpu_percent()
        disk = psutil.disk_usage('/')

        uptime = (datetime.utcnow() - self.start_time).total_seconds()

        return {
            "uptime_seconds": uptime,
            "memory": {
                "total_gb": memory.total / (1024**3),
                "used_gb": memory.used / (1024**3),
                "available_gb": memory.available / (1024**3),
                "percent": memory.percent
            },
            "cpu": {
                "percent": cpu,
                "count": psutil.cpu_count()
            },
            "disk": {
                "total_gb": disk.total / (1024**3),
                "used_gb": disk.used / (1024**3),
                "free_gb": disk.free / (1024**3),
                "percent": (disk.used / disk.total) * 100
            }
        }

    async def collect_metrics(self):
        """定期收集指标"""
        while True:
            try:
                metrics = self.get_container_metrics()
                # 发送到监控系统或日志
                logger.info(f"📊 系统指标: CPU {metrics['cpu']['percent']:.1f}%, 内存 {metrics['memory']['percent']:.1f}%")
                await asyncio.sleep(60)  # 每分钟收集一次
            except Exception as e:
                logger.error(f"指标收集失败: {e}")
                await asyncio.sleep(60)
```

## 📋 详细任务清单

### 🔥 P0-A Docker配置优化 (优先级高)
- [ ] 优化Dockerfile构建过程
- [ ] 更新Docker Compose配置
- [ ] 设置健康检查配置
- [ ] 配置环境变量和路径

### 🔥 P0-B 应用启动优化 (优先级高)
- [ ] 创建优化的启动脚本
- [ ] 优化应用启动顺序
- [ ] 实现优雅关闭机制
- [ ] 添加启动错误处理

### 🔥 P0-C 健康检查监控 (优先级高)
- [ ] 实现健康检查端点
- [ ] 添加数据库和Redis健康检查
- [ ] 实现系统指标监控
- [ ] 配置告警机制

### 🔥 P0-D 资源性能优化 (优先级高)
- [ ] 配置资源限制
- [ ] 优化内存和CPU使用
- [ ] 实现性能监控
- [ ] 优化启动时间

## 🧪 测试策略

### 1. 容器稳定性测试
```bash
# 测试脚本
#!/bin/bash
echo "🧪 容器稳定性测试"

# 启动容器
docker-compose up -d

# 监控30分钟
for i in {1..180}; do
    if docker-compose ps | grep -q "Up"; then
        echo "✅ 容器稳定运行 ($i/180 分钟)"
    else
        echo "❌ 容器异常"
        docker-compose logs app --tail 20
        exit 1
    fi
    sleep 10
done

echo "🎉 容器稳定性测试通过"
```

### 2. 健康检查测试
```bash
# 健康检查脚本
for i in {1..10}; do
    curl -f http://localhost:8000/health
    if [ $? -eq 0 ]; then
        echo "✅ 健康检查通过 ($i/10)"
    else
        echo "❌ 健康检查失败 ($i/10)"
        exit 1
    fi
    sleep 5
done
```

### 3. 性能压力测试
```bash
# 性能测试
python -m pytest tests/test_performance.py -v
```

## 📈 预期修复效果

### 修复前后对比
| 指标 | 修复前 | 修复后目标 | 改善幅度 |
|------|--------|-----------|----------|
| 容器稳定性 | 持续重启 | 稳定运行30分钟+ | 100% |
| 健康检查 | 失败 | 100%通过 | 100% |
| 启动时间 | 不确定 | <60秒 | 显著改善 |
| 资源使用 | 异常 | 正常范围 | 显著改善 |

### Docker环境改善预期
- **容器稳定性**: 从不可用到稳定运行
- **部署可靠性**: 完全的部署和监控
- **开发体验**: 与本地环境一致
- **运维效率**: 完善的健康检查和监控

## 🔄 依赖关系

### 前置依赖
- 🔄 Issue #181: Python路径配置 (待完成)
- 🔄 Issue #182: 依赖包安装 (待完成)
- 🔄 Issue #183: 缓存模块修复 (待完成)
- ✅ Issue #180: 系统验证 (已完成)

### 后续影响
- 为生产部署提供Docker基础
- 为CI/CD流水线提供容器支持
- 为微服务架构提供容器化基础

## 📊 时间线

### Day 1: Docker配置优化
- 上午: 优化Dockerfile和Compose配置
- 下午: 测试基础配置和启动

### Day 2: 应用启动优化
- 上午: 实现启动脚本和健康检查
- 下午: 测试应用启动和关闭

### Day 3: 资源性能优化
- 上午: 配置资源限制和监控
- 下午: 压力测试和性能调优

## 🛡️ 安全考虑

### 安全配置
- 非root用户运行
- 资源限制配置
- 健康检查安全
- 敏感信息保护

### 监控告警
- 资源使用监控
- 健康状态监控
- 错误日志收集
- 性能指标跟踪

## 🎯 相关链接

- **Docker配置**: [Dockerfile.production](./Dockerfile.production) (待创建)
- **Docker Compose**: [docker-compose.yml](./docker-compose.yml) (待优化)
- **启动脚本**: [docker/entrypoint.sh](./docker/entrypoint.sh) (待创建)
- **健康检查**: [src/api/health.py](./src/api/health.py) (待优化)

---

**优先级**: 🔴 P0 - 阻塞性问题
**预计工作量**: 2-3天
**负责工程师**: Claude AI Assistant
**创建时间**: 2025-10-31
**状态**: 🔄 待开始
**预期影响**: 实现稳定的Docker容器化部署