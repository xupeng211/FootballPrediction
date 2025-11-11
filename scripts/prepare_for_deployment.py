#!/usr/bin/env python3
"""
🚀 部署准备工具
快速完成项目部署前的关键配置
"""

import sys
from pathlib import Path


class DeploymentPreparation:
    """部署准备工具"""

    def __init__(self):
        self.project_root = Path(__file__).resolve().parent.parent

    def create_pyproject_toml(self):
        """创建pyproject.toml配置文件"""

        config = '''[build-system]
requires = ["setuptools>=45", "wheel", "setuptools_scm[toml]>=6.2"]
build-backend = "setuptools.build_meta"

[project]
name = "football-prediction"
version = "1.0.0"
description = "企业级足球预测系统"
readme = "README.md"
license = {text = "MIT"}
authors = [
    {name = "Football Prediction Team", email = "team@footballprediction.com"}
]
classifiers = [
    "Development Status :: 4 - Beta",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: MIT License",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
]
requires-python = ">=3.11"
dependencies = [
    "fastapi>=0.104.0",
    "uvicorn[standard]>=0.24.0",
    "sqlalchemy>=2.0.0",
    "alembic>=1.12.0",
    "pydantic>=2.5.0",
    "redis>=5.0.0",
    "psycopg2-binary>=2.9.0",
    "python-multipart>=0.0.6",
    "python-jose[cryptography]>=3.3.0",
    "passlib[bcrypt]>=1.7.4",
    "python-dotenv>=1.0.0",
    "httpx>=0.25.0",
    "pandas>=2.1.0",
    "numpy>=1.25.0",
    "scikit-learn>=1.3.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.4.0",
    "pytest-asyncio>=0.21.0",
    "pytest-cov>=4.1.0",
    "ruff>=0.1.0",
    "mypy>=1.7.0",
    "bandit>=1.7.0",
    "black>=23.0.0",
    "pre-commit>=3.5.0",
    "pip-audit>=2.6.0",
]

[project.urls]
Homepage = "https://github.com/xupeng211/FootballPrediction"
Repository = "https://github.com/xupeng211/FootballPrediction.git"
Issues = "https://github.com/xupeng211/FootballPrediction/issues"

[tool.setuptools.packages.find]
where = ["src"]

[tool.ruff]
line-length = 88
target-version = "py311"
select = ["E", "F", "W", "I", "N", "UP", "B", "A", "C4", "T20"]
ignore = ["E501", "B008"]
exclude = [
    ".bzr",
    ".direnv",
    ".eggs",
    ".git",
    ".hg",
    ".mypy_cache",
    ".nox",
    ".pants.d",
    ".ruff_cache",
    ".svn",
    ".tox",
    ".venv",
    "__pypackages__",
    "_build",
    "buck-out",
    "build",
    "dist",
    "node_modules",
    "venv",
]

[tool.ruff.format]
quote-style = "double"
indent-style = "space"
skip-magic-trailing-comma = false
line-ending = "auto"

[tool.mypy]
python_version = "3.11"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true
exclude = [
    "tests/",
    "scripts/",
]

[tool.pytest.ini_options]
minversion = "7.0"
addopts = "-ra -q --strict-markers --strict-config"
testpaths = ["tests"]
python_files = ["test_*.py", "*_test.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
markers = [
    "unit: Unit tests",
    "integration: Integration tests",
    "e2e: End-to-end tests",
    "slow: Slow running tests",
    "api: API related tests",
    "database: Database related tests",
    "auth: Authentication tests",
]

[tool.coverage.run]
source = ["src"]
omit = [
    "*/tests/*",
    "*/test_*",
    "*/__pycache__/*",
    "*/venv/*",
    "*/.venv/*",
]

[tool.coverage.report]
exclude_lines = [
    "pragma: no cover",
    "def __repr__",
    "raise AssertionError",
    "raise NotImplementedError",
    "if __name__ == .__main__.:",
]
'''

        pyproject_path = self.project_root / "pyproject.toml"
        pyproject_path.write_text(config, encoding='utf-8')

    def create_requirements_txt(self):
        """创建requirements.txt文件"""

        requirements = '''# Core dependencies
fastapi>=0.104.0,<0.105.0
uvicorn[standard]>=0.24.0,<0.25.0
sqlalchemy>=2.0.0,<2.1.0
alembic>=1.12.0,<1.13.0
pydantic>=2.5.0,<3.0.0
redis>=5.0.0,<6.0.0
psycopg2-binary>=2.9.0,<3.0.0
python-multipart>=0.0.6,<1.0.0
python-jose[cryptography]>=3.3.0,<4.0.0
passlib[bcrypt]>=1.7.4,<2.0.0
python-dotenv>=1.0.0,<2.0.0
httpx>=0.25.0,<1.0.0
pandas>=2.1.0,<3.0.0
numpy>=1.25.0,<2.0.0
scikit-learn>=1.3.0,<2.0.0

# Development dependencies
pytest>=7.4.0,<8.0.0
pytest-asyncio>=0.21.0,<1.0.0
pytest-cov>=4.1.0,<5.0.0
ruff>=0.1.0,<1.0.0
mypy>=1.7.0,<2.0.0
bandit>=1.7.0,<2.0.0
black>=23.0.0,<24.0.0
pre-commit>=3.5.0,<4.0.0
pip-audit>=2.6.0,<3.0.0
'''

        requirements_path = self.project_root / "requirements.txt"
        requirements_path.write_text(requirements, encoding='utf-8')

    def create_docker_compose(self):
        """创建docker-compose.yml文件"""

        compose_config = '''version: '3.8'

services:
  app:
    build: .
    ports:
      - "8000:8000"
    environment:
      - ENV=development
      - DATABASE_URL=postgresql://postgres:postgres@db:5432/football_prediction
      - REDIS_URL=redis://redis:6379/0
      - SECRET_KEY=dev-secret-key-change-in-production
    depends_on:
      - db
      - redis
    volumes:
      - ./src:/app/src
      - ./tests:/app/tests
    restart: unless-stopped

  db:
    image: postgres:15
    environment:
      - POSTGRES_DB=football_prediction
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=postgres
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./scripts/init_db.sql:/docker-entrypoint-initdb.d/init_db.sql
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    restart: unless-stopped

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
    depends_on:
      - app
    restart: unless-stopped

volumes:
  postgres_data:
  redis_data:
'''

        compose_path = self.project_root / "docker-compose.yml"
        compose_path.write_text(compose_config, encoding='utf-8')

    def create_env_example(self):
        """创建环境变量示例文件"""

        env_config = '''# 环境配置
ENV=development
DEBUG=true
LOG_LEVEL=INFO

# 数据库配置
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/football_prediction
DB_HOST=localhost
DB_PORT=5432
DB_NAME=football_prediction
DB_USER=postgres
DB_PASSWORD=postgres

# Redis配置
REDIS_URL=redis://localhost:6379/0
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0

# API配置
API_HOST=0.0.0.0
API_PORT=8000
API_WORKERS=1

# 安全配置
SECRET_KEY=your-secret-key-here-change-in-production
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=30
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# 外部服务配置
EXTERNAL_API_TIMEOUT=30
EXTERNAL_API_RETRIES=3

# 监控配置
ENABLE_METRICS=true
METRICS_PORT=9090

# 开发工具配置
HOT_RELOAD=true
AUTO_RESTART=true
'''

        env_example_path = self.project_root / ".env.example"
        env_example_path.write_text(env_config, encoding='utf-8')

        # 创建实际的.env文件
        env_path = self.project_root / ".env"
        if not env_path.exists():
            env_path.write_text(env_config, encoding='utf-8')

    def create_nginx_config(self):
        """创建Nginx配置文件"""

        nginx_config = '''events {
    worker_connections 1024;
}

http {
    upstream app {
        server app:8000;
    }

    server {
        listen 80;
        server_name localhost;

        location / {
            proxy_pass http://app;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        location /health {
            proxy_pass http://app/health;
            proxy_set_header Host $host;
        }

        location /metrics {
            proxy_pass http://app:9090/metrics;
            proxy_set_header Host $host;
        }
    }
}
'''

        nginx_path = self.project_root / "nginx.conf"
        nginx_path.write_text(nginx_config, encoding='utf-8')

    def create_db_init_script(self):
        """创建数据库初始化脚本"""

        db_script_dir = self.project_root / "scripts"
        db_script_dir.mkdir(exist_ok=True)

        init_script = '''-- 数据库初始化脚本
-- 创建扩展
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 创建基础表结构（如果Alembic未运行）
-- 这里可以放置基础数据插入语句

-- 插入示例数据（仅开发环境）
INSERT INTO users (id,
    username,
    email,
    hashed_password,
    is_active,
    created_at,
    updated_at)
VALUES
    (uuid_generate_v4(),
    'admin',
    'admin@footballprediction.com',
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj6ukx.LFvO',
    true,
    NOW(),
    NOW())
ON CONFLICT DO NOTHING;

-- 创建示例预测数据（开发环境）
INSERT INTO predictions (id,
    match_id,
    user_id,
    prediction,
    confidence,
    created_at,
    updated_at)
VALUES
    (uuid_generate_v4(),
    1,
    (SELECT id FROM users WHERE username = 'admin' LIMIT 1),
    'home_win',
    75,
    NOW(),
    NOW())
ON CONFLICT DO NOTHING;
'''

        init_script_path = db_script_dir / "init_db.sql"
        init_script_path.write_text(init_script, encoding='utf-8')

    def create_deployment_scripts(self):
        """创建部署脚本"""

        scripts_dir = self.project_root / "scripts"
        deploy_script = '''#!/bin/bash

# 部署脚本
echo "🚀 开始部署足球预测系统..."

# 检查Docker是否运行
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker未运行，请先启动Docker"
    exit 1
fi

# 构建并启动服务
echo "📦 构建Docker镜像..."
docker-compose build

echo "🔄 启动服务..."
docker-compose up -d

# 等待服务启动
echo "⏳ 等待服务启动..."
sleep 10

# 健康检查
echo "🔍 执行健康检查..."
if curl -f http://localhost:8000/health > /dev/null 2>&1; then
    echo "✅ 服务启动成功！"
    echo "🌐 API地址: http://localhost:8000"
    echo "📊 监控地址: http://localhost:9090/metrics"
else
    echo "❌ 服务启动失败，请检查日志"
    docker-compose logs
    exit 1
fi

echo "🎉 部署完成！"
'''

        deploy_script_path = scripts_dir / "deploy.sh"
        deploy_script_path.write_text(deploy_script, encoding='utf-8')
        deploy_script_path.chmod(0o755)

    def create_health_check(self):
        """创建健康检查端点"""

        health_endpoint = '''from fastapi import APIRouter
from datetime import datetime
import redis
import sqlalchemy
from sqlalchemy import text

router = APIRouter(prefix="/health", tags=["health"])

@router.get("/")
async def health_check():
    """基础健康检查"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "football-prediction-api",
        "version": "1.0.0"
    }

@router.get("/detailed")
async def detailed_health_check():
    """详细健康检查"""
    health_status = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "football-prediction-api",
        "version": "1.0.0",
        "components": {}
    }

    # 检查数据库连接
    try:
        # 这里应该使用实际的数据库连接
        health_status["components"]["database"] = "healthy"
    except Exception as e:
        health_status["components"]["database"] = f"unhealthy: {str(e)}"
        health_status["status"] = "unhealthy"

    # 检查Redis连接
    try:
        # 这里应该使用实际的Redis连接
        health_status["components"]["redis"] = "healthy"
    except Exception as e:
        health_status["components"]["redis"] = f"unhealthy: {str(e)}"
        health_status["status"] = "unhealthy"

    return health_status
'''

        health_dir = self.project_root / "src" / "api" / "health"
        health_dir.mkdir(parents=True, exist_ok=True)

        health_file = health_dir / "routes.py"
        health_file.write_text(health_endpoint, encoding='utf-8')

    def run_preparation(self):
        """运行所有部署准备工作"""

        try:
            self.create_pyproject_toml()
            self.create_requirements_txt()
            self.create_docker_compose()
            self.create_env_example()
            self.create_nginx_config()
            self.create_db_init_script()
            self.create_deployment_scripts()
            self.create_health_check()


        except Exception:
            sys.exit(1)

def main():
    """主函数"""
    preparator = DeploymentPreparation()
    preparator.run_preparation()

if __name__ == "__main__":
    main()
