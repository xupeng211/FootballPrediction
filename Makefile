# 🐳 Football Prediction Docker Makefile
# 用于标准化 Docker 开发环境的管理工具

.PHONY: help dev prod clean shell logs db-shell test lint build

# 默认目标
.DEFAULT_GOAL := help

# 颜色定义
GREEN := \033[32m
YELLOW := \033[33m
BLUE := \033[34m
RED := \033[31m
RESET := \033[0m

# 项目配置
PROJECT_NAME := football-prediction
APP_NAME := $(PROJECT_NAME)_app
DB_NAME := $(PROJECT_NAME)_db
REDIS_NAME := $(PROJECT_NAME)_redis

# .PHONY声明所有命令
.PHONY: help dev prod clean shell logs db-shell test lint build format fix-code type-check security-check coverage test.unit test.all

help: ## 📋 显示可用命令
	@echo "$(BLUE)🐳 Football Prediction Docker Commands$(RESET)"
	@echo "$(YELLOW)开发环境:$(RESET)"
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## .*开发/ {printf "  $(GREEN)%-12s$(RESET) %s\n", $$1, $$2}' $(MAKEFILE_LIST)
	@echo "$(YELLOW)生产环境:$(RESET)"
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## .*生产/ {printf "  $(GREEN)%-12s$(RESET) %s\n", $$1, $$2}' $(MAKEFILE_LIST)
	@echo "$(YELLOW)管理工具:$(RESET)"
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## .*管理/ {printf "  $(GREEN)%-12s$(RESET) %s\n", $$1, $$2}' $(MAKEFILE_LIST)

# 开发环境命令
dev: ## 开发/启动完整的开发环境 (app + db + redis + nginx)
	@echo "$(YELLOW)🚀 启动开发环境...$(RESET)"
	docker-compose up -d
	@echo "$(GREEN)✅ 开发环境已启动$(RESET)"
	@echo "$(BLUE)📝 前端: http://localhost:3000$(RESET)"
	@echo "$(BLUE)🔧 后端 API: http://localhost:8000$(RESET)"
	@echo "$(BLUE)📊 API 文档: http://localhost:8000/docs$(RESET)"

dev-rebuild: ## 开发/重新构建镜像并启动开发环境
	@echo "$(YELLOW)🔨 重新构建并启动开发环境...$(RESET)"
	docker-compose up --build -d
	@echo "$(GREEN)✅ 开发环境已重新构建并启动$(RESET)"

dev-logs: ## 开发/查看开发环境日志
	docker-compose logs -f

dev-stop: ## 开发/停止开发环境
	@echo "$(YELLOW)⏹️ 停止开发环境...$(RESET)"
	docker-compose down
	@echo "$(GREEN)✅ 开发环境已停止$(RESET)"

# 生产环境命令
prod: ## 生产/启动生产环境 (使用 docker-compose.prod.yml)
	@echo "$(YELLOW)🚀 启动生产环境...$(RESET)"
	docker-compose -f docker-compose.prod.yml up -d
	@echo "$(GREEN)✅ 生产环境已启动$(RESET)"

prod-rebuild: ## 生产/重新构建生产环境
	@echo "$(YELLOW)🔨 重新构建并启动生产环境...$(RESET)"
	docker-compose -f docker-compose.prod.yml up --build -d
	@echo "$(GREEN)✅ 生产环境已重新构建并启动$(RESET)"

# 管理工具
shell: ## 管理/进入后端容器终端
	@echo "$(YELLOW)🐚 进入后端容器...$(RESET)"
	docker-compose exec app /bin/bash

shell-db: ## 管理/进入数据库容器
	@echo "$(YELLOW)🐚 进入数据库容器...$(RESET)"
	docker-compose exec db /bin/bash

db-shell: ## 管理/连接到 PostgreSQL 数据库
	@echo "$(YELLOW)🗄️ 连接到 PostgreSQL...$(RESET)"
	docker-compose exec db psql -U postgres -d football_prediction

redis-shell: ## 管理/连接到 Redis
	@echo "$(YELLOW)🔴 连接到 Redis...$(RESET)"
	docker-compose exec redis redis-cli

logs: ## 管理/查看应用日志
	docker-compose logs -f app

logs-db: ## 管理/查看数据库日志
	docker-compose logs -f db

logs-redis: ## 管理/查看 Redis 日志
	docker-compose logs -f redis

status: ## 管理/查看所有服务状态
	@echo "$(BLUE)📊 容器状态:$(RESET)"
	docker-compose ps
	@echo "$(BLUE)🔍 健康检查:$(RESET)"
	@docker-compose exec app python -c "import urllib.request; print('✅ API健康')" 2>/dev/null || echo "❌ API不可访问"

test: ## 管理/在容器中运行测试
	@echo "$(YELLOW)🧪 在容器中运行测试...$(RESET)"
	docker-compose exec app bash -c 'export PATH=$$PATH:/home/app/.local/bin && cd /app && pytest tests/ -v --tb=short'

lint: ## 管理/在容器中运行代码检查
	@echo "$(YELLOW)🔍 在容器中运行代码检查...$(RESET)"
	docker-compose exec app bash -c 'export PATH=$$PATH:/home/app/.local/bin && cd /app && ruff check .'

format: ## 管理/在容器中运行代码格式化
	@echo "$(YELLOW)🎨 在容器中运行代码格式化...$(RESET)"
	docker-compose exec app bash -c 'export PATH=$$PATH:/home/app/.local/bin && cd /app && ruff format .'

fix-code: ## 管理/在容器中运行代码自动修复
	@echo "$(YELLOW)🔧 在容器中运行代码自动修复...$(RESET)"
	docker-compose exec app bash -c 'export PATH=$$PATH:/home/app/.local/bin && cd /app && ruff check --fix .'

type-check: ## 管理/在容器中运行类型检查
	@echo "$(YELLOW)🔍 在容器中运行类型检查...$(RESET)"
	docker-compose exec app bash -c 'export PATH=$$PATH:/home/app/.local/bin && cd /app && mypy src/ --ignore-missing-imports'

security-check: ## 管理/在容器中运行安全检查
	@echo "$(YELLOW)🔒 在容器中运行安全检查...$(RESET)"
	docker-compose exec app bash -c 'export PATH=$$PATH:/home/app/.local/bin && cd /app && bandit -r src/'

coverage: ## 管理/在容器中生成覆盖率报告
	@echo "$(YELLOW)📊 在容器中生成覆盖率报告...$(RESET)"
	docker-compose exec app bash -c 'export PATH=$$PATH:/home/app/.local/bin && cd /app && pytest tests/ --cov=src --cov-report=html --cov-report=term-missing'

test.unit: ## 管理/在容器中运行单元测试
	@echo "$(YELLOW)🧪 在容器中运行单元测试...$(RESET)"
	docker-compose exec app bash -c 'export PATH=$$PATH:/home/app/.local/bin && cd /app && pytest tests/unit/ -v'

test.integration: ## 管理/在容器中运行集成测试
	@echo "$(YELLOW)🧪 在容器中运行集成测试...$(RESET)"
	docker-compose exec app bash -c 'export PATH=$$PATH:/home/app/.local/bin && cd /app && pytest tests/integration/ -v'

test.all: ## 管理/在容器中运行所有测试
	@echo "$(YELLOW)🧪 在容器中运行所有测试...$(RESET)"
	docker-compose exec app bash -c 'export PATH=$$PATH:/home/app/.local/bin && cd /app && pytest tests/ -v'

# 清理命令
clean: ## 管理/清理容器和缓存
	@echo "$(YELLOW)🧹 清理 Docker 资源...$(RESET)"
	docker-compose down -v --remove-orphans
	docker system prune -f
	@echo "$(GREEN)✅ 清理完成$(RESET)"

clean-all: ## 管理/彻底清理所有相关资源
	@echo "$(RED)⚠️ 彻底清理所有资源...$(RESET)"
	docker-compose down -v --remove-orphans --rmi all
	docker system prune -af --volumes
	docker volume prune -f
	@echo "$(GREEN)✅ 彻底清理完成$(RESET)"

# 构建命令
build: ## 管理/构建应用镜像
	@echo "$(YELLOW)🔨 构建应用镜像...$(RESET)"
	docker-compose build app
	@echo "$(GREEN)✅ 镜像构建完成$(RESET)"

build-no-cache: ## 管理/无缓存构建镜像
	@echo "$(YELLOW)🔨 无缓存构建镜像...$(RESET)"
	docker-compose build --no-cache app
	@echo "$(GREEN)✅ 无缓存构建完成$(RESET)"

# 数据库管理
db-reset: ## 管理/重置数据库
	@echo "$(YELLOW)🗄️ 重置数据库...$(RESET)"
	docker-compose down -v
	docker-compose up -d db redis
	sleep 5
	docker-compose exec app python -m alembic upgrade head
	@echo "$(GREEN)✅ 数据库重置完成$(RESET)"

db-migrate: ## 管理/运行数据库迁移
	@echo "$(YELLOW)🔄 运行数据库迁移...$(RESET)"
	docker-compose exec app python -m alembic upgrade head
	@echo "$(GREEN)✅ 数据库迁移完成$(RESET)"

# 监控命令
monitor: ## 管理/实时监控应用资源使用
	docker stats $(APP_NAME)

monitor-all: ## 管理/监控所有容器资源使用
	docker stats

# 快捷命令
quick-start: dev ## 快捷/快速启动开发环境 (别名)
quick-stop: dev-stop ## 快捷/快速停止开发环境 (别名)
quick-clean: clean ## 快捷/快速清理 (别名)