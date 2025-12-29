#!/usr/bin/env python3
"""
Docker优化器
专门为足球预测系统设计的Docker容器和部署优化工具
"""

import logging
import os
from dataclasses import dataclass
from typing import Any

import docker
import yaml

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class OptimizationResult:
    """优化结果"""

    success: bool
    message: str
    recommendations: list[str]
    metrics: dict[str, Any]


class DockerOptimizer:
    """Docker优化器"""

    def __init__(self):
        self.client = None
        self.compose_file = "docker-compose.yml"
        self.dockerfile_path = "Dockerfile"

    def initialize(self):
        """初始化Docker客户端"""
        try:
            self.client = docker.from_env()
            self.client.ping()
            logger.info("🐳 Docker客户端连接成功")
            return True
        except Exception as e:
            logger.error(f"Docker连接失败: {e}")
            return False

    def analyze_dockerfile(self) -> OptimizationResult:
        """分析Dockerfile并提供优化建议"""
        if not os.path.exists(self.dockerfile_path):
            return OptimizationResult(
                success=False, message="Dockerfile不存在", recommendations=["创建Dockerfile"], metrics={}
            )

        with open(self.dockerfile_path) as f:
            content = f.read()

        recommendations = []
        metrics = {
            "lines": len(content.splitlines()),
            "from_count": content.count("FROM"),
            "run_count": content.count("RUN"),
            "copy_count": content.count("COPY"),
            "add_count": content.count("ADD"),
            "expose_count": content.count("EXPOSE"),
            "has_healthcheck": "HEALTHCHECK" in content,
            "has_user": "USER" in content,
            "uses_multistage": content.count("FROM") > 1,
            "uses_alpine": "alpine" in content,
            "uses_slim": "slim" in content,
        }

        # 分析并提供建议
        if metrics["add_count"] > 0:
            recommendations.append("考虑使用COPY替代ADD以提高安全性")

        if not metrics["has_healthcheck"]:
            recommendations.append("添加HEALTHCHECK以监控容器健康状态")

        if not metrics["has_user"]:
            recommendations.append("使用非root用户运行容器以提高安全性")

        if not metrics["uses_multistage"]:
            recommendations.append("考虑使用多阶段构建减少镜像大小")

        if metrics["run_count"] > 5:
            recommendations.append("合并多个RUN指令以减少镜像层数")

        if "apt-get" in content and "rm -rf /var/lib/apt/lists/*" not in content:
            recommendations.append("在apt-get后清理缓存以减少镜像大小")

        success = len(recommendations) == 0
        message = "Dockerfile已优化" if success else "Dockerfile需要优化"

        return OptimizationResult(success=success, message=message, recommendations=recommendations, metrics=metrics)

    def analyze_docker_compose(self) -> OptimizationResult:
        """分析docker-compose.yml并提供优化建议"""
        if not os.path.exists(self.compose_file):
            return OptimizationResult(
                success=False,
                message="docker-compose.yml不存在",
                recommendations=["创建docker-compose.yml"],
                metrics={},
            )

        try:
            with open(self.compose_file) as f:
                compose_config = yaml.safe_load(f)
        except Exception as e:
            return OptimizationResult(
                success=False, message=f"无法解析docker-compose.yml: {e}", recommendations=[], metrics={}
            )

        recommendations = []
        metrics = {
            "services_count": len(compose_config.get("services", {})),
            "volumes_count": len(compose_config.get("volumes", {})),
            "networks_count": len(compose_config.get("networks", {})),
            "has_restart_policy": False,
            "has_resource_limits": False,
            "has_healthcheck": False,
            "has_environment_vars": False,
            "uses_custom_networks": "networks" in compose_config,
            "version": compose_config.get("version", ""),
        }

        # 分析每个服务
        services = compose_config.get("services", {})
        for service_name, service_config in services.items():
            # 检查重启策略
            if "restart" in service_config:
                metrics["has_restart_policy"] = True
            else:
                recommendations.append(f"服务 {service_name} 缺少重启策略")

            # 检查资源限制
            if "deploy" in service_config and "resources" in service_config["deploy"]:
                metrics["has_resource_limits"] = True
            else:
                recommendations.append(f"服务 {service_name} 缺少资源限制")

            # 检查健康检查
            if "healthcheck" in service_config:
                metrics["has_healthcheck"] = True
            else:
                recommendations.append(f"服务 {service_name} 缺少健康检查")

            # 检查环境变量
            if "environment" in service_config:
                metrics["has_environment_vars"] = True

        # 检查网络配置
        if not metrics["uses_custom_networks"]:
            recommendations.append("使用自定义网络提高安全性")

        success = len(recommendations) == 0
        message = "docker-compose.yml已优化" if success else "docker-compose.yml需要优化"

        return OptimizationResult(success=success, message=message, recommendations=recommendations, metrics=metrics)

    def generate_optimized_dockerfile(self, base_image: str = "python:3.11-slim") -> str:
        """生成优化的Dockerfile模板"""
        return f"""# 优化的多阶段Dockerfile
FROM {base_image} as builder

# 设置工作目录
WORKDIR /app

# 安装构建依赖
RUN apt-get update && apt-get install -y \\
    gcc \\
    && rm -rf /var/lib/apt/lists/*

# 安装Python依赖
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# 生产阶段
FROM {base_image}

# 创建非root用户
RUN groupadd -r appuser && useradd -r -g appuser appuser

# 安装运行时依赖
RUN apt-get update && apt-get install -y \\
    curl \\
    && rm -rf /var/lib/apt/lists/* \\
    && apt-get clean

# 设置工作目录
WORKDIR /app

# 复制Python包
COPY --from=builder /root/.local /root/.local

# 复制应用代码
COPY --chown=appuser:appuser . .

# 设置环境变量
ENV PATH=/root/.local/bin:$PATH
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# 暴露端口
EXPOSE 8000

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \\
    CMD curl -f http://localhost:8000/health || exit 1

# 非root用户运行
USER appuser

# 启动命令
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
"""

    def generate_optimized_docker_compose(self) -> str:
        """生成优化的docker-compose.yml模板"""
        return """# 优化的Docker Compose配置
version: '3.8'

services:
  # 主应用服务
  app:
    build:
      context: .
      dockerfile: Dockerfile
      target: production
    restart: unless-stopped
    deploy:
      replicas: 3
      resources:
        limits:
          cpus: '0.5'
          memory: 512M
        reservations:
          cpus: '0.25'
          memory: 256M
      restart_policy:
        condition: on-failure
        delay: 5s
        max_attempts: 3
    environment:
      - DATABASE_URL=postgresql://football_user:football_pass@db:5432/football_prediction_dev
      - REDIS_URL=redis://redis:6379
      - ENVIRONMENT=production
    ports:
      - "8000:8000"
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    networks:
      - app-network

  # PostgreSQL数据库
  db:
    image: postgres:15-alpine
    restart: unless-stopped
    environment:
      POSTGRES_DB: football_prediction_dev
      POSTGRES_USER: football_user
      POSTGRES_PASSWORD: football_pass
      POSTGRES_INITDB_ARGS: "--encoding=UTF-8"
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./scripts/init.sql:/docker-entrypoint-initdb.d/init.sql
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U football_user -d football_prediction_dev"]
      interval: 10s
      timeout: 5s
      retries: 5
    deploy:
      resources:
        limits:
          cpus: '1.0'
          memory: 2G
        reservations:
          cpus: '0.5'
          memory: 1G
    networks:
      - app-network
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"

  # Redis缓存
  redis:
    image: redis:7-alpine
    restart: unless-stopped
    command: redis-server --maxmemory 256mb --maxmemory-policy allkeys-lru --appendonly yes
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 3
    deploy:
      resources:
        limits:
          cpus: '0.25'
          memory: 256M
        reservations:
          cpus: '0.1'
          memory: 128M
    networks:
      - app-network
    logging:
      driver: "json-file"
      options:
        max-size: "5m"
        max-file: "2"

  # Prometheus监控
  prometheus:
    image: prom/prometheus:latest
    restart: unless-stopped
    ports:
      - "9090:9090"
    volumes:
      - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--web.console.libraries=/etc/prometheus/console_libraries'
      - '--web.enable-lifecycle'
    healthcheck:
      test: ["CMD", "wget", "--quiet", "--tries=1", "--spider", "http://localhost:9090/-/healthy"]
      interval: 30s
      timeout: 10s
      retries: 3
    networks:
      - app-network

  # Grafana可视化
  grafana:
    image: grafana/grafana:latest
    restart: unless-stopped
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin123
      - GF_USERS_ALLOW_SIGN_UP=false
    volumes:
      - grafana_data:/var/lib/grafana
      - ./monitoring/grafana:/etc/grafana/provisioning
    healthcheck:
      test: ["CMD", "wget", "--quiet", "--tries=1", "--spider", "http://localhost:3000/api/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    networks:
      - app-network

volumes:
  postgres_data:
    driver: local
  redis_data:
    driver: local
  prometheus_data:
    driver: local
  grafana_data:
    driver: local

networks:
  app-network:
    driver: bridge
    ipam:
      config:
        - subnet: 172.20.0.0/16
"""

    def optimize_existing_dockerfile(self) -> OptimizationResult:
        """优化现有的Dockerfile"""
        if not os.path.exists(self.dockerfile_path):
            return OptimizationResult(
                success=False, message="Dockerfile不存在", recommendations=["创建Dockerfile"], metrics={}
            )

        # 备份原文件
        backup_path = f"{self.dockerfile_path}.backup"
        os.replace(self.dockerfile_path, backup_path)

        try:
            # 生成优化版本
            optimized_content = self.generate_optimized_dockerfile()
            with open(self.dockerfile_path, "w") as f:
                f.write(optimized_content)

            return OptimizationResult(
                success=True,
                message="Dockerfile优化完成，原文件已备份",
                recommendations=[f"原文件已备份至 {backup_path}"],
                metrics={"original_lines": len(open(backup_path).readlines())},
            )
        except Exception as e:
            # 恢复原文件
            os.replace(backup_path, self.dockerfile_path)
            return OptimizationResult(
                success=False, message=f"优化失败: {e}", recommendations=["手动检查Dockerfile"], metrics={}
            )

    def optimize_existing_docker_compose(self) -> OptimizationResult:
        """优化现有的docker-compose.yml"""
        if not os.path.exists(self.compose_file):
            return OptimizationResult(
                success=False,
                message="docker-compose.yml不存在",
                recommendations=["创建docker-compose.yml"],
                metrics={},
            )

        # 备份原文件
        backup_path = f"{self.compose_file}.backup"
        os.replace(self.compose_file, backup_path)

        try:
            # 生成优化版本
            optimized_content = self.generate_optimized_docker_compose()
            with open(self.compose_file, "w") as f:
                f.write(optimized_content)

            return OptimizationResult(
                success=True,
                message="docker-compose.yml优化完成，原文件已备份",
                recommendations=[f"原文件已备份至 {backup_path}"],
                metrics={"original_services": len(yaml.safe_load(open(backup_path)).get("services", {}))},
            )
        except Exception as e:
            # 恢复原文件
            os.replace(backup_path, self.compose_file)
            return OptimizationResult(
                success=False, message=f"优化失败: {e}", recommendations=["手动检查docker-compose.yml"], metrics={}
            )

    def get_container_stats(self) -> dict[str, Any]:
        """获取容器统计信息"""
        if not self.client:
            return {"error": "Docker客户端未初始化"}

        try:
            containers = self.client.containers.list(all=True)
            stats = {
                "total_containers": len(containers),
                "running_containers": len([c for c in containers if c.status == "running"]),
                "stopped_containers": len([c for c in containers if c.status == "exited"]),
                "containers": [],
            }

            for container in containers:
                try:
                    container_stats = container.stats(stream=False)
                    c_info = {
                        "id": container.short_id,
                        "name": container.name,
                        "status": container.status,
                        "image": container.image.tags[0] if container.image.tags else "unknown",
                        "cpu_usage": 0,
                        "memory_usage": 0,
                        "memory_limit": 0,
                    }

                    # 计算CPU使用率
                    if "cpu_stats" in container_stats and "precpu_stats" in container_stats:
                        cpu_delta = (
                            container_stats["cpu_stats"]["cpu_usage"]["total_usage"]
                            - container_stats["precpu_stats"]["cpu_usage"]["total_usage"]
                        )
                        system_delta = (
                            container_stats["cpu_stats"]["system_cpu_usage"]
                            - container_stats["precpu_stats"]["system_cpu_usage"]
                        )
                        if system_delta > 0:
                            c_info["cpu_usage"] = (cpu_delta / system_delta) * 100.0

                    # 计算内存使用
                    if "memory_stats" in container_stats:
                        c_info["memory_usage"] = container_stats["memory_stats"]["usage"]
                        c_info["memory_limit"] = container_stats["memory_stats"]["limit"]

                    stats["containers"].append(c_info)

                except Exception as e:
                    logger.warning(f"获取容器 {container.name} 统计失败: {e}")

            return stats

        except Exception as e:
            return {"error": f"获取容器统计失败: {e}"}

    def cleanup_docker_resources(self) -> OptimizationResult:
        """清理Docker资源"""
        if not self.client:
            return OptimizationResult(success=False, message="Docker客户端未初始化", recommendations=[], metrics={})

        try:
            # 清理停止的容器
            stopped_containers = self.client.containers.list(filters={"status": "exited"})
            container_count = 0
            for container in stopped_containers:
                container.remove()
                container_count += 1

            # 清理未使用的镜像
            images = self.client.images.prune()
            image_count = len(images.get("ImagesDeleted", []))

            # 清理未使用的卷
            volumes = self.client.volumes.prune()
            volume_count = len(volumes.get("VolumesDeleted", []))

            # 清理未使用的网络
            networks = self.client.networks.prune()
            network_count = len(networks.get("NetworksDeleted", []))

            metrics = {
                "containers_removed": container_count,
                "images_removed": image_count,
                "volumes_removed": volume_count,
                "networks_removed": network_count,
            }

            message = "Docker资源清理完成"
            recommendations = []

            if container_count == 0 and image_count == 0 and volume_count == 0:
                recommendations.append("没有需要清理的资源")
            else:
                recommendations.append("定期清理Docker资源以释放磁盘空间")

            return OptimizationResult(success=True, message=message, recommendations=recommendations, metrics=metrics)

        except Exception as e:
            return OptimizationResult(
                success=False, message=f"清理失败: {e}", recommendations=["检查Docker权限"], metrics={}
            )

    def generate_production_configs(self) -> dict[str, str]:
        """生成生产环境配置文件"""
        configs = {
            ".dockerignore": """# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# Virtual environments
.env
.venv
env/
venv/
ENV/
env.bak/
venv.bak/

# IDE
.vscode/
.idea/
*.swp
*.swo

# Git
.git/
.gitignore

# Docker
Dockerfile*
docker-compose*.yml
.dockerignore

# Logs
*.log
logs/

# OS
.DS_Store
Thumbs.db

# Project specific
.pytest_cache/
.coverage
htmlcov/
.env.local
.env.development
""",
            "docker-compose.prod.yml": """# 生产环境Docker Compose配置
version: '3.8'

services:
  app:
    image: football-prediction:latest
    restart: always
    deploy:
      replicas: 3
      resources:
        limits:
          cpus: '1.0'
          memory: 1G
        reservations:
          cpus: '0.5'
          memory: 512M
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - REDIS_URL=${REDIS_URL}
      - SECRET_KEY=${SECRET_KEY}
      - ENVIRONMENT=production
    networks:
      - production-network
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"

  nginx:
    image: nginx:alpine
    restart: always
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
      - ./nginx/ssl:/etc/nginx/ssl:ro
    depends_on:
      - app
    networks:
      - production-network

networks:
  production-network:
    external: true
""",
            "nginx/nginx.conf": """events {
    worker_connections 1024;
}

http {
    upstream app {
        server app:8000;
    }

    server {
        listen 80;
        server_name api.football-prediction.com;
        return 301 https://$server_name$request_uri;
    }

    server {
        listen 443 ssl http2;
        server_name api.football-prediction.com;

        ssl_certificate /etc/nginx/ssl/cert.pem;
        ssl_certificate_key /etc/nginx/ssl/key.pem;
        ssl_protocols TLSv1.2 TLSv1.3;
        ssl_ciphers HIGH:!aNULL:!MD5;

        location / {
            proxy_pass http://app;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        location /health {
            access_log off;
            proxy_pass http://app/health;
        }
    }
}""",
        }

        return configs

    def run_optimization_audit(self) -> dict[str, OptimizationResult]:
        """运行完整的优化审计"""
        if not self.initialize():
            return {"error": "无法初始化Docker客户端"}

        results = {
            "dockerfile": self.analyze_dockerfile(),
            "docker_compose": self.analyze_docker_compose(),
            "container_stats": self.get_container_stats(),
            "resource_cleanup": self.cleanup_docker_resources(),
        }

        return results


async def main():
    """主函数示例"""
    print("🐳 Docker优化器")
    print("=" * 50)

    optimizer = DockerOptimizer()

    # 运行完整审计
    results = optimizer.run_optimization_audit()

    print("\n📊 优化审计结果:")
    for category, result in results.items():
        if isinstance(result, OptimizationResult):
            print(f"\n{category.upper()}:")
            print(f"  状态: {'✅' if result.success else '❌'} {result.message}")
            if result.recommendations:
                print("  建议:")
                for rec in result.recommendations:
                    print(f"    • {rec}")
            if result.metrics:
                print(f"  指标: {result.metrics}")
        else:
            print(f"\n{category.upper()}:")
            print(f"  {result}")

    # 生成优化配置文件
    print("\n📝 生成生产配置文件...")
    configs = optimizer.generate_production_configs()
    for filename, content in configs.items():
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        with open(filename, "w") as f:
            f.write(content)
        print(f"  ✓ {filename}")

    print("\n✅ Docker优化完成")


if __name__ == "__main__":
    asyncio.run(main())
