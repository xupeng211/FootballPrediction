# ============================================
# FootballPrediction V51.0 - Makefile 指挥塔
# ============================================
# 归一化部署命令中心
# 生成时间: 2025-12-26
# 状态: V51.0 Industrial Grade Ready
# ============================================

.PHONY: help up down restart logs test clean build db-reset db-shell lint format security \
        dev-config dev-up dev-down dev-shell dev-logs dev-build dev-ps dev-harvest dev-test \
        data-help data-check data-local-dry-run data-l3-dry-run data-l3-commit \
        data-l3-write-dry-run data-l3-write-commit \
        data-training-dry-run data-training-commit data-prediction-dry-run data-prediction-commit \
        data-training-feature-dry-run data-training-feature-commit \
        data-prediction-write-dry-run data-prediction-write-commit \
        data-dataset-status data-training-dataset-dry-run data-training-dataset-export \
        data-acquisition-engines data-acquisition-engine-audit \
        data-single-target-network-dry-run data-single-target-network-commit \
        data-single-target-acquisition-runtime-scaffold data-single-target-acquisition-runtime-commit \
        data-single-target-acquisition-staging-schema-validate data-single-target-acquisition-staging-schema-commit \
        data-single-target-acquisition-staging-writer-preflight data-single-target-acquisition-staging-writer-commit \
        data-single-target-acquisition-staging-packet-preview data-single-target-acquisition-staging-packet-commit \
        data-single-target-acquisition-pre-network-runbook-validate data-single-target-acquisition-pre-network-runbook-commit \
        data-single-target-acquisition-network-auth-form-validate data-single-target-acquisition-network-auth-form-commit \
        data-single-target-acquisition-network-readiness-checklist-validate data-single-target-acquisition-network-readiness-checklist-commit \
        data-single-target-acquisition-network-execution-plan-validate data-single-target-acquisition-network-execution-plan-commit \
        data-single-target-acquisition-network-approval-packet-preview data-single-target-acquisition-network-approval-packet-commit \
        data-single-target-acquisition-network-user-input-closure-preview data-single-target-acquisition-network-user-input-closure-commit \
        data-single-target-acquisition-network-blocked-final-preflight-summary data-single-target-acquisition-network-blocked-final-preflight-commit \
        data-single-target-acquisition-network-real-parameter-intake-preview data-single-target-acquisition-network-real-parameter-intake-commit \
        data-single-target-acquisition-network-real-parameter-validation-closure-preview data-single-target-acquisition-network-real-parameter-validation-closure-commit \
        data-single-target-acquisition-network-filled-intake-review-plan-preview data-single-target-acquisition-network-filled-intake-review-plan-commit \
        data-single-target-acquisition-network-filled-intake-review-result-preview data-single-target-acquisition-network-filled-intake-review-result-commit \
        data-real-source-audit data-real-finished-csv-dry-run data-real-finished-csv-commit \
        data-football-data-csv-dry-run data-football-data-csv-commit \
        data-football-data-db-write-preflight data-football-data-db-write-commit \
        data-football-data-duplicate-precheck data-football-data-duplicate-precheck-commit \
        data-football-data-small-write-auth-preview data-football-data-small-write-commit \
        data-football-data-small-write-runbook-validate data-football-data-small-write-runbook-commit \
        data-football-data-small-write-packet-preview data-football-data-small-write-packet-commit \
        data-football-data-packet-file-preflight data-football-data-packet-file-commit \
        data-football-data-packet-file-auth-validate data-football-data-packet-file-auth-commit \
        data-football-data-packet-file-auth-review data-football-data-packet-file-auth-review-commit \
        data-football-data-packet-file-readiness-review data-football-data-packet-file-readiness-commit \
        data-football-data-packet-file-auth-packet-draft data-football-data-packet-file-auth-packet-draft-commit \
        data-football-data-packet-file-auth-review-consolidation data-football-data-packet-file-auth-review-consolidation-commit \
        data-football-data-packet-file-preauth-closure data-football-data-packet-file-preauth-closure-commit \
        data-football-data-insert-policy-precheck data-football-data-insert-policy-commit \
        data-finished-csv-dry-run data-finished-csv-commit \
        data-finished-backfill-dry-run data-finished-backfill-commit \
        data-raw-fixture-dry-run data-raw-fixture-commit \
        data-synthetic-l3-dry-run data-synthetic-l3-commit \
        data-synthetic-training-feature-dry-run data-synthetic-training-feature-commit \
        data-synthetic-prediction-dry-run data-synthetic-prediction-commit \
        data-raw-dry-run data-raw-commit data-network-dry-run data-db-write-small data-harvest \
        data-risk-report data-schema-help data-schema-status data-schema-plan data-schema-migrate

# 默认目标
.DEFAULT_GOAL := help

# ============================================
# 颜色定义
# ============================================
GREEN  := \033[0;32m
YELLOW := \033[1;33m
BLUE   := \033[0;34m
NC     := \033[0m # No Color

# ============================================
# 帮助信息
# ============================================
help: ## 显示帮助信息
	@echo ""
	@echo "$(BLUE)FootballPrediction V51.0 - Makefile 指挥塔$(NC)"
	@echo ""
	@echo "$(GREEN)使用方法:$(NC)"
	@echo "  make <target>"
	@echo ""
	@echo "$(GREEN)可用命令:$(NC)"
	@awk 'BEGIN {FS = ":.*##"} /^[a-zA-Z_-]+:.*?##/ { printf "  $(YELLOW)%-20s$(NC) %s\n", $$1, $$2 }' $(MAKEFILE_LIST)
	@echo ""

# ============================================
# Docker 命令
# ============================================
COMPOSE_DEV=docker compose -f docker-compose.dev.yml
PRE_NETWORK_RUNBOOK_NODE?=$(COMPOSE_DEV) exec -T dev node
NETWORK_AUTH_FORM_NODE?=$(COMPOSE_DEV) exec -T dev node
NETWORK_READINESS_CHECKLIST_NODE?=$(COMPOSE_DEV) exec -T dev node
NETWORK_EXECUTION_PLAN_NODE?=$(COMPOSE_DEV) exec -T dev node
NETWORK_APPROVAL_PACKET_NODE?=$(COMPOSE_DEV) exec -T dev node
NETWORK_USER_INPUT_CLOSURE_NODE?=$(COMPOSE_DEV) exec -T dev node
NETWORK_BLOCKED_PREFLIGHT_NODE?=$(COMPOSE_DEV) exec -T dev node
NETWORK_REAL_PARAMETER_INTAKE_NODE?=$(COMPOSE_DEV) exec -T dev node
NETWORK_REAL_PARAMETER_VALIDATION_CLOSURE_NODE?=$(COMPOSE_DEV) exec -T dev node
NETWORK_FILLED_INTAKE_REVIEW_PLAN_NODE?=$(COMPOSE_DEV) exec -T dev node
NETWORK_FILLED_INTAKE_REVIEW_RESULT_NODE?=$(COMPOSE_DEV) exec -T dev node

up: ## 启动核心服务 (db + redis)
	docker-compose up -d

up-pipeline: ## 启动核心服务 + 数据流水线
	docker-compose --profile pipeline up -d

up-api: ## 启动核心服务 + API
	docker-compose --profile api up -d

up-dev: ## 启动开发环境 (包含管理工具)
	docker-compose --profile dev up -d

up-all: ## 启动所有服务
	docker-compose --profile all up -d

down: ## 停止所有服务
	docker-compose down

restart: ## 重启核心服务
	docker-compose restart pipeline_worker

logs: ## 查看核心服务日志
	docker-compose logs -f pipeline_worker

logs-api: ## 查看 API 日志
	docker-compose logs -f predictor_api

logs-all: ## 查看所有服务日志
	docker-compose logs -f

ps: ## 查看容器状态
	docker-compose ps

# ============================================
# 构建命令
# ============================================
build: ## 构建生产镜像
	docker-compose build

build-test: ## 构建测试镜像
	docker build --target test -f deploy/Dockerfile -t footballprediction:test .

build-no-cache: ## 无缓存构建
	docker-compose build --no-cache

# ============================================
# 测试与检查
# ============================================
test: ## 运行全量测试
	@echo "$(BLUE)运行测试门禁...$(NC)"
	./scripts/run_checks.sh

test-unit: ## 运行单元测试
	pytest tests/ml/test_backtest_engine.py tests/ops/test_signal_generator.py -v

lint: ## 运行 Lint 检查
	@echo "$(BLUE)运行 Lint 检查...$(NC)"
	ruff check src/ tests/ || flake8 src/ tests/ --max-line-length=120

format: ## 格式化代码
	@echo "$(BLUE)格式化代码...$(NC)"
	ruff format src/ tests/ || black src/ tests/
	isort src/ tests/

security: ## 运行安全扫描
	@echo "$(BLUE)运行安全扫描...$(NC)"
	bandit -r src/ -f screen -ll

verify: ## 运行完整验证
	$(MAKE) lint
	$(MAKE) test-unit
	$(MAKE) security

# ============================================
# 数据库命令
# ============================================
db-reset: ## 重置数据库 (危险操作!)
	@echo "$(YELLOW)警告: 这将删除所有数据!$(NC)"
	@read -p "确定要继续吗? [y/N] " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		docker-compose down -v; \
		docker-compose up -d db; \
		sleep 5; \
		echo "数据库已重置"; \
	fi

db-shell: ## 进入 PostgreSQL Shell
	docker-compose exec db psql -U football_user -d football_db

db-backup: ## 备份数据库
	@mkdir -p data/backups
	docker-compose exec db pg_dump -U football_user football_db > data/backups/backup_$$(date +%Y%m%d_%H%M%S).sql

# ============================================
# Redis 命令
# ============================================
redis-shell: ## 进入 Redis CLI
	docker-compose exec redis redis-cli

# ============================================
# 清理命令
# ============================================
clean: ## 清理所有垃圾文件、缓存和僵尸资产
	@echo "$(BLUE)清理垃圾文件...$(NC)"
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.bak" -delete
	find . -type f -name "*.覆盖" -delete 2>/dev/null || true
	@echo "$(NC)  清理 Python 字节码和缓存..."
	@echo "$(GREEN)✓ 垃圾文件已清理$(NC)"

clean-csv: ## 清理临时测试生成的 CSV 文件
	@echo "$(BLUE)清理临时预测 CSV 文件...$(NC)"
	@find predictions -type f -name "*test*.csv" -delete 2>/dev/null || true
	@find predictions -type f -name "*temp*.csv" -delete 2>/dev/null || true
	@find predictions -type f -name "*_summary.txt" -mtime +30 -delete 2>/dev/null || true
	@echo "$(GREEN)✓ 临时 CSV 文件已清理$(NC)"

clean-logs: ## 清理超过 7 天的日志文件
	@echo "$(BLUE)清理过期日志文件...$(NC)"
	@find logs -type f -name "*.log" -mtime +7 -delete 2>/dev/null || true
	@find logs -type f -name "*.txt" -mtime +30 -delete 2>/dev/null || true
	@echo "$(GREEN)✓ 过期日志已清理$(NC)"

clean-docker: ## 清理 Docker 资源
	@echo "$(BLUE)清理 Docker 资源...$(NC)"
	docker-compose down -v 2>/dev/null || true
	docker system prune -f
	@echo "$(GREEN)✓ Docker 资源已清理$(NC)"

clean-all: ## 完全清理 (包括临时文件和日志)
	$(MAKE) clean
	$(MAKE) clean-csv
	$(MAKE) clean-logs
	$(MAKE) clean-docker
	@echo "$(GREEN)✓ 完全清理完成$(NC)"

# ============================================
# 部署命令
# ============================================
deploy: ## 部署到生产环境
	@echo "$(BLUE)部署到生产环境...$(NC)"
	$(MAKE) verify
	$(MAKE) build
	$(MAKE) up
	@echo "$(GREEN)部署完成!$(NC)"

# ============================================
# 标准 Docker 开发入口
# ============================================
dev-config: ## 验证开发 Compose 配置
	$(COMPOSE_DEV) config

dev-build: ## 构建开发镜像
	$(COMPOSE_DEV) build

dev-up: ## 启动容器化开发环境
	$(COMPOSE_DEV) up -d --build --remove-orphans

dev-ps: ## 查看开发容器状态
	$(COMPOSE_DEV) ps

dev-down: ## 停止开发容器
	$(COMPOSE_DEV) down

dev-shell: ## 进入开发容器 Shell
	$(COMPOSE_DEV) exec dev bash

dev-logs: ## 查看开发容器日志
	$(COMPOSE_DEV) logs -f --tail=200

dev-harvest: ## 在容器中运行生产收割器
	$(COMPOSE_DEV) exec dev npm start

dev-test: ## 在容器中运行测试
	$(COMPOSE_DEV) exec dev python main.py --test-proxy

# ============================================
# 数据入口安全门禁
# ============================================
data-help: ## Show safe data harvesting entrypoint policy
	@echo "FootballPrediction data entrypoints are safety-gated."
	@echo ""
	@echo "Allowed by default:"
	@echo "  make data-help"
	@echo "  make data-check"
	@echo "  make data-local-dry-run SAMPLE_HTML=<path> or SAMPLE_CSV=<path>"
	@echo "  make data-l3-dry-run SAMPLE_RAW=<path> MATCH_ID=<id>"
	@echo "  make data-l3-write-dry-run SAMPLE_RAW=<path> MATCH_ID=<id>"
	@echo "  make data-raw-dry-run SAMPLE_RAW=<path> MATCH_ID=<id>"
	@echo "  make data-training-dry-run"
	@echo "  make data-prediction-dry-run"
	@echo "  make data-training-feature-dry-run MATCH_ID=<id>"
	@echo "  make data-prediction-write-dry-run MATCH_ID=<id>"
	@echo "  make data-dataset-status"
	@echo "  make data-training-dataset-dry-run"
	@echo "  make data-acquisition-engines"
	@echo "  make data-acquisition-engine-audit"
	@echo "  make data-real-source-audit SOURCE_MANIFEST=<path>"
	@echo "  make data-real-finished-csv-dry-run SOURCE_MANIFEST=<path> SAMPLE_CSV=<path>"
	@echo "  make data-football-data-csv-dry-run SOURCE_MANIFEST=<path> LOCAL_CSV=<path>"
	@echo "  make data-football-data-db-write-preflight SOURCE_MANIFEST=<path> LOCAL_CSV=<path>"
	@echo "  make data-football-data-duplicate-precheck SOURCE_MANIFEST=<path> LOCAL_CSV=<path>"
	@echo "  make data-football-data-small-write-auth-preview SOURCE_MANIFEST=<path> LOCAL_CSV=<path>"
	@echo "  make data-football-data-small-write-runbook-validate APPROVAL_FORM=<path>"
	@echo "  make data-football-data-small-write-packet-preview SOURCE_MANIFEST=<path> LOCAL_CSV=<path> APPROVAL_FORM=<path> RUNBOOK_TEMPLATE=<path>"
	@echo "  make data-football-data-packet-file-preflight SOURCE_MANIFEST=<path> LOCAL_CSV=<path> APPROVAL_FORM=<path> RUNBOOK_TEMPLATE=<path>"
	@echo "  make data-football-data-packet-file-auth-validate AUTH_FORM=<path>"
	@echo "  make data-football-data-packet-file-auth-review AUTH_FORM=<path> SOURCE_MANIFEST=<path> LOCAL_CSV=<path> APPROVAL_FORM=<path> RUNBOOK_TEMPLATE=<path>"
	@echo "  make data-football-data-packet-file-readiness-review READINESS_CHECKLIST=<path> AUTH_FORM=<path> SOURCE_MANIFEST=<path> LOCAL_CSV=<path> APPROVAL_FORM=<path> RUNBOOK_TEMPLATE=<path>"
	@echo "  make data-football-data-insert-policy-precheck SOURCE_MANIFEST=<path> LOCAL_CSV=<path>"
	@echo "  make data-finished-csv-dry-run SAMPLE_CSV=<path>"
	@echo "  make data-finished-backfill-dry-run MATCH_ID=<id>"
	@echo "  make data-finished-backfill-dry-run MATCH_ID=<id> FIXTURE=<path>"
	@echo "  make data-raw-fixture-dry-run MATCH_ID=<id> FIXTURE=<path>"
	@echo "  make data-raw-fixture-dry-run MATCH_ID=<id> FIXTURE=<path> ALLOW_SYNTHETIC=1"
	@echo "  make data-synthetic-l3-dry-run MATCH_ID=<id>"
	@echo "  make data-synthetic-training-feature-dry-run MATCH_ID=<id>"
	@echo "  make data-synthetic-prediction-dry-run MATCH_ID=<id>"
	@echo ""
	@echo "Requires explicit authorization:"
	@echo "  make data-raw-fixture-commit MATCH_ID=<id> FIXTURE=<path> CONFIRM_RAW_FIXTURE_COMMIT=1  # blocked in Phase 4.41"
	@echo "  make data-finished-backfill-commit MATCH_ID=<id> CONFIRM_FINISHED_BACKFILL=1  # blocked in Phase 4.40"
	@echo "  make data-synthetic-l3-commit MATCH_ID=<id> CONFIRM_SYNTHETIC_L3=1  # blocked in Phase 4.44"
	@echo "  make data-synthetic-training-feature-commit MATCH_ID=<id> CONFIRM_SYNTHETIC_TRAINING_FEATURE=1  # blocked in Phase 4.46"
	@echo "  make data-synthetic-prediction-commit MATCH_ID=<id> CONFIRM_SYNTHETIC_PREDICTION=1  # blocked in Phase 4.48"
	@echo "  make data-finished-csv-commit SAMPLE_CSV=<path> CONFIRM_FINISHED_CSV_COMMIT=1  # blocked in Phase 4.38"
	@echo "  make data-real-finished-csv-commit SOURCE_MANIFEST=<path> SAMPLE_CSV=<path> CONFIRM_REAL_CSV_COMMIT=1  # blocked in Phase 4.52"
	@echo "  make data-football-data-csv-commit SOURCE_MANIFEST=<path> LOCAL_CSV=<path> CONFIRM_FOOTBALL_DATA_CSV_COMMIT=1  # blocked in Phase 4.63C"
	@echo "  make data-football-data-db-write-commit SOURCE_MANIFEST=<path> LOCAL_CSV=<path> CONFIRM_FOOTBALL_DATA_DB_WRITE=1  # blocked in Phase 4.64C"
	@echo "  make data-football-data-duplicate-precheck-commit SOURCE_MANIFEST=<path> LOCAL_CSV=<path> CONFIRM_FOOTBALL_DATA_DUPLICATE_PRECHECK=1  # blocked in Phase 4.65C"
	@echo "  make data-football-data-insert-policy-commit SOURCE_MANIFEST=<path> LOCAL_CSV=<path> CONFIRM_FOOTBALL_DATA_INSERT_POLICY=1  # blocked in Phase 4.66C"
	@echo "  make data-football-data-small-write-runbook-commit APPROVAL_FORM=<path> CONFIRM_FOOTBALL_DATA_SMALL_WRITE_RUNBOOK=1  # blocked in Phase 4.68C"
	@echo "  make data-football-data-small-write-packet-commit SOURCE_MANIFEST=<path> LOCAL_CSV=<path> APPROVAL_FORM=<path> RUNBOOK_TEMPLATE=<path> CONFIRM_FOOTBALL_DATA_SMALL_WRITE_PACKET=1  # blocked in Phase 4.69C"
	@echo "  make data-football-data-packet-file-commit SOURCE_MANIFEST=<path> LOCAL_CSV=<path> APPROVAL_FORM=<path> RUNBOOK_TEMPLATE=<path> CONFIRM_FOOTBALL_DATA_PACKET_FILE=1  # blocked in Phase 4.70C"
	@echo "  make data-football-data-packet-file-auth-commit AUTH_FORM=<path> CONFIRM_FOOTBALL_DATA_PACKET_FILE_AUTH=1  # blocked in Phase 4.71C"
	@echo "  make data-football-data-packet-file-auth-review-commit AUTH_FORM=<path> SOURCE_MANIFEST=<path> LOCAL_CSV=<path> APPROVAL_FORM=<path> RUNBOOK_TEMPLATE=<path> CONFIRM_FOOTBALL_DATA_PACKET_FILE_AUTH_REVIEW=1  # blocked in Phase 4.72C"
	@echo "  make data-football-data-packet-file-readiness-review-commit READINESS_CHECKLIST=<path> AUTH_FORM=<path> SOURCE_MANIFEST=<path> LOCAL_CSV=<path> APPROVAL_FORM=<path> RUNBOOK_TEMPLATE=<path> CONFIRM_FOOTBALL_DATA_PACKET_FILE_READINESS=1  # blocked in Phase 4.73C"
	@echo "  make data-football-data-packet-file-auth-packet-draft DRAFT_TEMPLATE=<path> READINESS_CHECKLIST=<path> AUTH_FORM=<path> SOURCE_MANIFEST=<path> LOCAL_CSV=<path> APPROVAL_FORM=<path> RUNBOOK_TEMPLATE=<path>"
	@echo "  make data-football-data-packet-file-auth-packet-draft-commit DRAFT_TEMPLATE=<path> READINESS_CHECKLIST=<path> AUTH_FORM=<path> SOURCE_MANIFEST=<path> LOCAL_CSV=<path> APPROVAL_FORM=<path> RUNBOOK_TEMPLATE=<path> CONFIRM_FOOTBALL_DATA_PACKET_FILE_AUTH_PACKET_DRAFT=1  # blocked in Phase 4.74C"
	@echo "  make data-football-data-packet-file-auth-review-consolidation CONSOLIDATION_TEMPLATE=<path> DRAFT_TEMPLATE=<path> READINESS_CHECKLIST=<path> AUTH_FORM=<path> SOURCE_MANIFEST=<path> LOCAL_CSV=<path> APPROVAL_FORM=<path> RUNBOOK_TEMPLATE=<path>"
	@echo "  make data-football-data-packet-file-auth-review-consolidation-commit CONSOLIDATION_TEMPLATE=<path> DRAFT_TEMPLATE=<path> READINESS_CHECKLIST=<path> AUTH_FORM=<path> SOURCE_MANIFEST=<path> LOCAL_CSV=<path> APPROVAL_FORM=<path> RUNBOOK_TEMPLATE=<path> CONFIRM_FOOTBALL_DATA_PACKET_FILE_AUTH_REVIEW_CONSOLIDATION=1  # blocked in Phase 4.75C"
	@echo "  make data-football-data-packet-file-preauth-closure CLOSURE_TEMPLATE=<path> CONSOLIDATION_TEMPLATE=<path> DRAFT_TEMPLATE=<path> READINESS_CHECKLIST=<path> AUTH_FORM=<path> SOURCE_MANIFEST=<path> LOCAL_CSV=<path> APPROVAL_FORM=<path> RUNBOOK_TEMPLATE=<path>"
	@echo "  make data-football-data-packet-file-preauth-closure-commit CLOSURE_TEMPLATE=<path> CONSOLIDATION_TEMPLATE=<path> DRAFT_TEMPLATE=<path> READINESS_CHECKLIST=<path> AUTH_FORM=<path> SOURCE_MANIFEST=<path> LOCAL_CSV=<path> APPROVAL_FORM=<path> RUNBOOK_TEMPLATE=<path> CONFIRM_FOOTBALL_DATA_PACKET_FILE_PREAUTH_CLOSURE=1  # blocked in Phase 4.76C"
	@echo "  make data-training-dataset-export CONFIRM_DATASET_EXPORT=1  # blocked in Phase 4.36"
	@echo "  make data-prediction-write-commit MATCH_ID=<id> CONFIRM_PREDICTION_WRITE=1  # blocked in Phase 4.32"
	@echo "  make data-training-feature-commit MATCH_ID=<id> CONFIRM_TRAINING_FEATURE=1  # blocked in Phase 4.30"
	@echo "  make data-training-commit CONFIRM_TRAINING=1  # blocked in Phase 4.29"
	@echo "  make data-prediction-commit CONFIRM_PREDICTION=1  # blocked in Phase 4.29"
	@echo "  make data-l3-write-commit SAMPLE_RAW=<path> MATCH_ID=<id> CONFIRM_L3_WRITE=1  # blocked in Phase 4.26"
	@echo "  make data-l3-commit SAMPLE_RAW=<path> MATCH_ID=<id> CONFIRM_L3_COMMIT=1  # blocked in Phase 4.24"
	@echo "  make data-raw-commit SAMPLE_RAW=<path> MATCH_ID=<id> CONFIRM_RAW_COMMIT=1  # blocked in Phase 4.21"
	@echo "  make data-single-target-network-dry-run ENGINE=<engine> TARGET_MATCH_ID=<id> SOURCE_MANIFEST=<path>  # scaffold-only / blocked in Phase 4.54"
	@echo "  make data-single-target-network-commit ENGINE=<engine> TARGET_MATCH_ID=<id> SOURCE_MANIFEST=<path> CONFIRM_SINGLE_TARGET_NETWORK=1  # blocked in Phase 4.54"
	@echo "  make data-single-target-acquisition-runtime-scaffold TARGET_SOURCE=<src> TARGET_ENGINE_FAMILY=titan_discovery TARGET_SCOPE_TYPE=<type> ...  # scaffold-only, Phase 4.79D"
	@echo "  make data-single-target-acquisition-runtime-commit ... CONFIRM_SINGLE_TARGET_ACQUISITION_RUNTIME=1  # blocked in Phase 4.79D"
	@echo "  make data-single-target-acquisition-staging-schema-validate ARTIFACT_SCHEMA=<path> MANIFEST_SCHEMA=<path> ARTIFACT=<path> MANIFEST=<path>  # local-only, Phase 4.80D"
	@echo "  make data-single-target-acquisition-staging-schema-commit ... CONFIRM_SINGLE_TARGET_ACQUISITION_STAGING_SCHEMA=1  # blocked in Phase 4.80D"
	@echo "  make data-single-target-acquisition-staging-writer-preflight ARTIFACT_SCHEMA=<path> ... OUTPUT_ROOT=<path> ...  # preflight-only, Phase 4.81D"
	@echo "  make data-single-target-acquisition-staging-writer-commit ... CONFIRM_SINGLE_TARGET_ACQUISITION_STAGING_WRITE=1  # blocked in Phase 4.81D"
	@echo "  make data-single-target-acquisition-staging-packet-preview ARTIFACT_SCHEMA=<path> ... OUTPUT_ROOT=<path> ...  # packet preview, Phase 4.82D"
	@echo "  make data-single-target-acquisition-staging-packet-commit ... CONFIRM_SINGLE_TARGET_ACQUISITION_STAGING_PACKET=1  # blocked in Phase 4.82D"
	@echo "  make data-single-target-acquisition-pre-network-runbook-validate RUNBOOK=<path> ARTIFACT_SCHEMA=<path> MANIFEST_SCHEMA=<path> ARTIFACT=<path> MANIFEST=<path> OUTPUT_ROOT=<path> TARGET_SOURCE=<src> TARGET_ENGINE_FAMILY=titan_discovery TARGET_SCOPE_TYPE=<type> TARGET_MATCH_ID=<id> ...  # draft-only validate, Phase 4.83D"
	@echo "  make data-single-target-acquisition-pre-network-runbook-commit ... CONFIRM_SINGLE_TARGET_ACQUISITION_PRE_NETWORK_RUNBOOK=1  # blocked in Phase 4.83D"
	@echo "  make data-single-target-acquisition-network-auth-form-validate AUTH_FORM=<path> RUNBOOK=<path> TARGET_SOURCE=<src> TARGET_ENGINE_FAMILY=titan_discovery TARGET_SCOPE_TYPE=<type> TARGET_MATCH_ID=<id> ...  # template-only validate, Phase 4.84D"
	@echo "  make data-single-target-acquisition-network-auth-form-commit ... CONFIRM_SINGLE_TARGET_ACQUISITION_NETWORK_AUTH_FORM=1  # blocked in Phase 4.84D"
	@echo "  make data-single-target-acquisition-network-readiness-checklist-validate CHECKLIST=<path> RUNBOOK=<path> AUTH_FORM=<path> TARGET_SOURCE=<src> TARGET_ENGINE_FAMILY=titan_discovery TARGET_SCOPE_TYPE=<type> TARGET_MATCH_ID=<id> ...  # template-only validate, Phase 4.85D"
	@echo "  make data-single-target-acquisition-network-readiness-checklist-commit ... CONFIRM_SINGLE_TARGET_ACQUISITION_NETWORK_READINESS=1  # blocked in Phase 4.85D"
	@echo "  make data-single-target-acquisition-network-execution-plan-validate EXECUTION_PLAN=<path> CHECKLIST=<path> RUNBOOK=<path> AUTH_FORM=<path> TARGET_SOURCE=<src> TARGET_ENGINE_FAMILY=titan_discovery TARGET_SCOPE_TYPE=<type> TARGET_MATCH_ID=<id> ...  # draft-only validate, Phase 4.86D"
	@echo "  make data-single-target-acquisition-network-execution-plan-commit ... CONFIRM_SINGLE_TARGET_ACQUISITION_NETWORK_EXECUTION_PLAN=1  # blocked in Phase 4.86D"
	@echo "  make data-single-target-acquisition-network-approval-packet-preview APPROVAL_PACKET=<path> EXECUTION_PLAN=<path> CHECKLIST=<path> RUNBOOK=<path> AUTH_FORM=<path> TARGET_SOURCE=<src> TARGET_ENGINE_FAMILY=titan_discovery TARGET_SCOPE_TYPE=<type> TARGET_MATCH_ID=<id> ...  # preview-only validate, Phase 4.87D"
	@echo "  make data-single-target-acquisition-network-approval-packet-commit ... CONFIRM_SINGLE_TARGET_ACQUISITION_NETWORK_APPROVAL_PACKET=1  # blocked in Phase 4.87D"
	@echo "  make data-single-target-acquisition-network-user-input-closure-preview INPUT_CLOSURE=<path> APPROVAL_PACKET=<path> EXECUTION_PLAN=<path> CHECKLIST=<path> RUNBOOK=<path> AUTH_FORM=<path> TARGET_SOURCE=<src> TARGET_ENGINE_FAMILY=titan_discovery TARGET_SCOPE_TYPE=<type> TARGET_MATCH_ID=<id> ...  # closure-preview-only validate, Phase 4.88D"
	@echo "  make data-single-target-acquisition-network-user-input-closure-commit ... CONFIRM_SINGLE_TARGET_ACQUISITION_NETWORK_USER_INPUT_CLOSURE=1  # blocked in Phase 4.88D"
	@echo "  make data-single-target-acquisition-network-blocked-final-preflight-summary BLOCKED_SUMMARY=<path> INPUT_CLOSURE=<path> APPROVAL_PACKET=<path> EXECUTION_PLAN=<path> CHECKLIST=<path> RUNBOOK=<path> AUTH_FORM=<path> TARGET_SOURCE=<src> TARGET_ENGINE_FAMILY=titan_discovery TARGET_SCOPE_TYPE=<type> TARGET_MATCH_ID=<id> ...  # blocked final preflight summary, Phase 4.89D"
	@echo "  make data-single-target-acquisition-network-blocked-final-preflight-commit ... CONFIRM_SINGLE_TARGET_ACQUISITION_NETWORK_BLOCKED_FINAL_PREFLIGHT=1  # blocked in Phase 4.89D"
	@echo "  make data-single-target-acquisition-network-real-parameter-intake-preview INTAKE=<path> BLOCKED_SUMMARY=<path>  # real-parameter intake template preview, Phase 4.90D"
	@echo "  make data-single-target-acquisition-network-real-parameter-intake-commit ... CONFIRM_SINGLE_TARGET_ACQUISITION_NETWORK_REAL_PARAMETER_INTAKE=1  # blocked in Phase 4.90D"
	@echo "  make data-single-target-acquisition-network-real-parameter-validation-closure-preview VALIDATION_CLOSURE=<path> INTAKE=<path> BLOCKED_SUMMARY=<path>  # validation closure preview, Phase 4.91D"
	@echo "  make data-single-target-acquisition-network-real-parameter-validation-closure-commit ... CONFIRM_SINGLE_TARGET_ACQUISITION_NETWORK_REAL_PARAMETER_VALIDATION_CLOSURE=1  # blocked in Phase 4.91D"
	@echo "  make data-single-target-acquisition-network-filled-intake-review-plan-preview REVIEW_PLAN=<path> INTAKE=<path> VALIDATION_CLOSURE=<path> BLOCKED_SUMMARY=<path>  # review plan preview, Phase 4.92D"
	@echo "  make data-single-target-acquisition-network-filled-intake-review-plan-commit ... CONFIRM_SINGLE_TARGET_ACQUISITION_NETWORK_FILLED_INTAKE_REVIEW_PLAN=1  # blocked in Phase 4.92D"
	@echo "  make data-single-target-acquisition-network-filled-intake-review-result-preview REVIEW_RESULT=<path> REVIEW_PLAN=<path> INTAKE=<path> VALIDATION_CLOSURE=<path> BLOCKED_SUMMARY=<path>  # review result preview, Phase 4.93D"
	@echo "  make data-single-target-acquisition-network-filled-intake-review-result-commit ... CONFIRM_SINGLE_TARGET_ACQUISITION_NETWORK_FILLED_INTAKE_REVIEW_RESULT=1  # blocked in Phase 4.93D"
	@echo "  make data-network-dry-run CONFIRM_NETWORK=1 LIMIT=<n> SCOPE=<scope>"
	@echo "  make data-db-write-small CONFIRM_DB_WRITE=1 LIMIT=<n> SCOPE=<scope>"
	@echo "  make data-harvest CONFIRM_BULK_HARVEST=1 RUNBOOK=<path>"
	@echo ""
	@echo "Read docs/DATA_HARVESTING_GUIDE.md before running any data task."
	@echo "For DB schema migration safety gates, run: make data-schema-help"

data-check: ## Read-only data environment check
	@echo "Checking data environment in dev container..."
	$(COMPOSE_DEV) ps
	$(COMPOSE_DEV) exec -T dev node --version
	$(COMPOSE_DEV) exec -T dev npm --version
	$(COMPOSE_DEV) exec -T dev python --version
	$(COMPOSE_DEV) exec -T dev node scripts/ops/local_dom_ingestor.js --help >/tmp/fp_data_local_dom_help.txt
	$(COMPOSE_DEV) exec -T dev node scripts/ops/csv_bulk_loader.js --help >/tmp/fp_data_csv_loader_help.txt
	@echo "OK: read-only data environment check completed."

data-local-dry-run: ## Run a safe local-only dry-run. Requires SAMPLE_HTML or SAMPLE_CSV.
	@if [ -n "$(SAMPLE_HTML)" ]; then \
		echo "Running local HTML preview only: $(SAMPLE_HTML)"; \
		$(COMPOSE_DEV) exec -T dev test -f "$(SAMPLE_HTML)"; \
		$(COMPOSE_DEV) exec -T dev node scripts/ops/local_dom_ingestor.js --file "$(SAMPLE_HTML)"; \
	elif [ -n "$(SAMPLE_CSV)" ]; then \
		echo "Running local CSV preview only: $(SAMPLE_CSV)"; \
		$(COMPOSE_DEV) exec -T dev test -f "$(SAMPLE_CSV)"; \
		$(COMPOSE_DEV) exec -T dev node scripts/ops/csv_bulk_loader.js --file "$(SAMPLE_CSV)" --batch-size 50 --error-log /tmp/csv_bulk_loader_errors.jsonl; \
	else \
		echo "ERROR: provide SAMPLE_HTML=<path> or SAMPLE_CSV=<path>"; \
		exit 1; \
	fi

data-l3-dry-run: ## Run safe local L3 dry-run from fixture. Requires SAMPLE_RAW and MATCH_ID.
	@if [ -z "$(SAMPLE_RAW)" ] || [ -z "$(MATCH_ID)" ]; then \
		echo "ERROR: provide SAMPLE_RAW=<path> and MATCH_ID=<id>"; \
		exit 1; \
	fi
	@echo "Running safe local L3 dry-run: SAMPLE_RAW=$(SAMPLE_RAW), MATCH_ID=$(MATCH_ID)"
	$(COMPOSE_DEV) exec -T dev test -f "$(SAMPLE_RAW)"
	$(COMPOSE_DEV) exec -T dev node scripts/ops/l3_local_dry_run.js --fixture "$(SAMPLE_RAW)" --match-id "$(MATCH_ID)"

data-l3-commit: ## Blocked l3_features commit gate. Requires SAMPLE_RAW, MATCH_ID, CONFIRM_L3_COMMIT=1.
	@if [ "$(CONFIRM_L3_COMMIT)" != "1" ]; then \
		echo "BLOCKED: l3_features commit requires CONFIRM_L3_COMMIT=1 and is not wired in Phase 4.24."; \
		exit 1; \
	fi
	@echo "BLOCKED: l3_features commit is not wired in Phase 4.24."
	@exit 1

data-l3-write-dry-run: ## Run safe local l3_features write preview. Requires SAMPLE_RAW and MATCH_ID.
	@if [ -z "$(SAMPLE_RAW)" ] || [ -z "$(MATCH_ID)" ]; then \
		echo "ERROR: provide SAMPLE_RAW=<path> and MATCH_ID=<id>"; \
		exit 1; \
	fi
	@echo "Running safe local l3_features write dry-run: SAMPLE_RAW=$(SAMPLE_RAW), MATCH_ID=$(MATCH_ID)"
	$(COMPOSE_DEV) exec -T dev test -f "$(SAMPLE_RAW)"
	$(COMPOSE_DEV) exec -T dev node scripts/ops/l3_features_local_write_gate.js --fixture "$(SAMPLE_RAW)" --match-id "$(MATCH_ID)"

data-l3-write-commit: ## Blocked l3_features write gate. Requires SAMPLE_RAW, MATCH_ID, CONFIRM_L3_WRITE=1.
	@if [ "$(CONFIRM_L3_WRITE)" != "1" ]; then \
		echo "BLOCKED: l3_features write requires CONFIRM_L3_WRITE=1 and is not wired in Phase 4.26."; \
		exit 1; \
	fi
	@if [ -z "$(SAMPLE_RAW)" ] || [ -z "$(MATCH_ID)" ]; then \
		echo "BLOCKED: provide SAMPLE_RAW=<path> and MATCH_ID=<id>; l3_features commit is not wired in Phase 4.26."; \
		exit 1; \
	fi
	@echo "BLOCKED: l3_features commit is not wired in Phase 4.26."
	@exit 1

data-training-dry-run: ## Safe training preflight placeholder. Does not train or write DB.
	@echo "SAFE PREVIEW ONLY: training dry-run is not wired in Phase 4.29."
	@echo "No npm run train, model training, model artifact generation, or DB writes are executed."
	@echo "Current local sample is insufficient for training; requires multi-match finished historical dataset and explicit model artifact policy."
	@echo "Recommended next step: create a training runbook with dataset scope, artifact paths, backup plan, and validation gates."

data-training-commit: ## Blocked training gate. Requires CONFIRM_TRAINING=1 but remains blocked in Phase 4.29.
	@if [ "$(CONFIRM_TRAINING)" != "1" ]; then \
		echo "BLOCKED: training requires CONFIRM_TRAINING=1 and is not wired in Phase 4.29."; \
		exit 1; \
	fi
	@echo "BLOCKED: training commit is not wired in Phase 4.29."
	@exit 1

data-prediction-dry-run: ## Safe prediction preflight placeholder. Does not predict or write DB.
	@echo "SAFE PREVIEW ONLY: prediction dry-run is not wired in Phase 4.29."
	@echo "No npm run predict, model inference, prediction write, or DB writes are executed."
	@echo "Prediction requires l3_features, trusted model artifacts, target window policy, and explicit output/write policy."
	@echo "Recommended next step: create a prediction runbook with match scope, artifact manifest, and no-write verification gates."

data-prediction-commit: ## Blocked prediction gate. Requires CONFIRM_PREDICTION=1 but remains blocked in Phase 4.29.
	@if [ "$(CONFIRM_PREDICTION)" != "1" ]; then \
		echo "BLOCKED: prediction requires CONFIRM_PREDICTION=1 and is not wired in Phase 4.29."; \
		exit 1; \
	fi
	@echo "BLOCKED: prediction commit is not wired in Phase 4.29."
	@exit 1

data-training-feature-dry-run: ## Run safe local match_features_training write preview. Requires MATCH_ID.
	@if [ -z "$(MATCH_ID)" ]; then \
		echo "ERROR: provide MATCH_ID=<id>"; \
		exit 1; \
	fi
	@echo "Running safe local match_features_training write dry-run: MATCH_ID=$(MATCH_ID)"
	$(COMPOSE_DEV) exec -T dev node scripts/ops/match_features_training_local_write_gate.js --match-id "$(MATCH_ID)"

data-training-feature-commit: ## Blocked match_features_training write gate. Requires MATCH_ID, CONFIRM_TRAINING_FEATURE=1.
	@if [ "$(CONFIRM_TRAINING_FEATURE)" != "1" ]; then \
		echo "BLOCKED: match_features_training write requires CONFIRM_TRAINING_FEATURE=1 and is not wired in Phase 4.30."; \
		exit 1; \
	fi
	@if [ -z "$(MATCH_ID)" ]; then \
		echo "BLOCKED: provide MATCH_ID=<id>; match_features_training commit is not wired in Phase 4.30."; \
		exit 1; \
	fi
	@echo "BLOCKED: match_features_training commit is not wired in Phase 4.30."
	@exit 1

data-synthetic-training-feature-dry-run: ## Run safe synthetic L3 to training feature preflight. Requires MATCH_ID.
	@if [ -z "$(MATCH_ID)" ]; then \
		echo "ERROR: provide MATCH_ID=<id>"; \
		exit 1; \
	fi
	@echo "Running safe synthetic L3 to training feature preflight: MATCH_ID=$(MATCH_ID)"
	$(COMPOSE_DEV) exec -T dev node scripts/ops/synthetic_training_feature_preflight.js --match-id "$(MATCH_ID)"

data-synthetic-training-feature-commit: ## Blocked synthetic training feature gate. Requires MATCH_ID, CONFIRM_SYNTHETIC_TRAINING_FEATURE=1.
	@if [ "$(CONFIRM_SYNTHETIC_TRAINING_FEATURE)" != "1" ]; then \
		echo "BLOCKED: synthetic training feature commit requires CONFIRM_SYNTHETIC_TRAINING_FEATURE=1 and is not wired in Phase 4.46."; \
		exit 1; \
	fi
	@echo "BLOCKED: synthetic training feature commit is not wired in Phase 4.46."
	@exit 1

data-synthetic-prediction-dry-run: ## Run safe synthetic training feature to prediction preflight. Requires MATCH_ID.
	@if [ -z "$(MATCH_ID)" ]; then \
		echo "ERROR: provide MATCH_ID=<id>"; \
		exit 1; \
	fi
	@echo "Running safe synthetic training feature to prediction preflight: MATCH_ID=$(MATCH_ID)"
	$(COMPOSE_DEV) exec -T dev node scripts/ops/synthetic_prediction_preflight.js --match-id "$(MATCH_ID)"

data-synthetic-prediction-commit: ## Blocked synthetic prediction gate. Requires MATCH_ID, CONFIRM_SYNTHETIC_PREDICTION=1.
	@if [ "$(CONFIRM_SYNTHETIC_PREDICTION)" != "1" ]; then \
		echo "BLOCKED: synthetic prediction commit requires CONFIRM_SYNTHETIC_PREDICTION=1 and is not wired in Phase 4.48."; \
		exit 1; \
	fi
	@echo "BLOCKED: synthetic prediction commit is not wired in Phase 4.48."
	@exit 1

data-prediction-write-dry-run: ## Run safe local predictions write preview. Requires MATCH_ID.
	@if [ -z "$(MATCH_ID)" ]; then \
		echo "ERROR: provide MATCH_ID=<id>"; \
		exit 1; \
	fi
	@echo "Running safe local prediction write dry-run: MATCH_ID=$(MATCH_ID)"
	$(COMPOSE_DEV) exec -T dev node scripts/ops/prediction_local_write_gate.js --match-id "$(MATCH_ID)"

data-prediction-write-commit: ## Blocked predictions write gate. Requires MATCH_ID, CONFIRM_PREDICTION_WRITE=1.
	@if [ "$(CONFIRM_PREDICTION_WRITE)" != "1" ]; then \
		echo "BLOCKED: prediction write requires CONFIRM_PREDICTION_WRITE=1 and is not wired in Phase 4.32."; \
		exit 1; \
	fi
	@if [ -z "$(MATCH_ID)" ]; then \
		echo "BLOCKED: provide MATCH_ID=<id>; prediction commit is not wired in Phase 4.32."; \
		exit 1; \
	fi
	@echo "BLOCKED: prediction commit is not wired in Phase 4.32."
	@exit 1

data-dataset-status: ## Run SELECT-only dataset status audit. Does not train, export, predict, or write DB.
	$(COMPOSE_DEV) exec -T dev node scripts/ops/dataset_status_audit.js

data-training-dataset-dry-run: ## Run SELECT-only training dataset readiness audit. Does not train, export, or write DB.
	$(COMPOSE_DEV) exec -T dev node scripts/ops/dataset_status_audit.js

data-training-dataset-export: ## Blocked dataset export gate. Remains not wired in Phase 4.36.
	@if [ "$(CONFIRM_DATASET_EXPORT)" != "1" ]; then \
		echo "BLOCKED: dataset export requires CONFIRM_DATASET_EXPORT=1 and is not wired in Phase 4.36."; \
		exit 1; \
	fi
	@echo "BLOCKED: dataset export is not wired in Phase 4.36."
	@exit 1

data-real-source-audit: ## Run local source manifest audit for real finished CSV staging. Requires SOURCE_MANIFEST.
	@if [ -z "$(SOURCE_MANIFEST)" ]; then \
		echo "ERROR: provide SOURCE_MANIFEST=<path>"; \
		exit 1; \
	fi
	@echo "Running safe real source manifest audit: SOURCE_MANIFEST=$(SOURCE_MANIFEST)"
	$(COMPOSE_DEV) exec -T dev test -f "$(SOURCE_MANIFEST)"
	$(COMPOSE_DEV) exec -T dev node scripts/ops/real_finished_csv_staging_dry_run.js --source-manifest "$(SOURCE_MANIFEST)" --audit-source

data-real-finished-csv-dry-run: ## Run local real finished CSV staging dry-run. Requires SOURCE_MANIFEST and SAMPLE_CSV.
	@if [ -z "$(SOURCE_MANIFEST)" ] || [ -z "$(SAMPLE_CSV)" ]; then \
		echo "ERROR: provide SOURCE_MANIFEST=<path> and SAMPLE_CSV=<path>"; \
		exit 1; \
	fi
	@echo "Running safe real finished CSV staging dry-run: SOURCE_MANIFEST=$(SOURCE_MANIFEST), SAMPLE_CSV=$(SAMPLE_CSV)"
	$(COMPOSE_DEV) exec -T dev test -f "$(SOURCE_MANIFEST)"
	$(COMPOSE_DEV) exec -T dev test -f "$(SAMPLE_CSV)"
	$(COMPOSE_DEV) exec -T dev node scripts/ops/real_finished_csv_staging_dry_run.js --source-manifest "$(SOURCE_MANIFEST)" --sample-csv "$(SAMPLE_CSV)"

data-real-finished-csv-commit: ## Blocked real finished CSV commit gate. Requires SOURCE_MANIFEST, SAMPLE_CSV, CONFIRM_REAL_CSV_COMMIT=1.
	@if [ "$(CONFIRM_REAL_CSV_COMMIT)" != "1" ]; then \
		echo "BLOCKED: real finished CSV commit requires CONFIRM_REAL_CSV_COMMIT=1 and is not wired in Phase 4.52."; \
		exit 1; \
	fi
	@echo "BLOCKED: real finished CSV commit is not wired in Phase 4.52."
	@exit 1

data-football-data-csv-dry-run: ## Run local Football-Data source manifest + CSV dry-run gate. Requires SOURCE_MANIFEST and LOCAL_CSV.
	@if [ -z "$(SOURCE_MANIFEST)" ] || [ -z "$(LOCAL_CSV)" ]; then \
		echo "ERROR: provide SOURCE_MANIFEST=<path> and LOCAL_CSV=<path>"; \
		exit 1; \
	fi
	@echo "Running safe Football-Data local CSV dry-run: SOURCE_MANIFEST=$(SOURCE_MANIFEST), LOCAL_CSV=$(LOCAL_CSV)"
	$(COMPOSE_DEV) exec -T dev test -f "$(SOURCE_MANIFEST)"
	$(COMPOSE_DEV) exec -T dev test -f "$(LOCAL_CSV)"
	$(COMPOSE_DEV) exec -T dev node scripts/ops/football_data_adapter_dry_run.js --source-manifest "$(SOURCE_MANIFEST)" --local-csv "$(LOCAL_CSV)"

data-football-data-csv-commit: ## Blocked Football-Data CSV commit gate. Requires SOURCE_MANIFEST, LOCAL_CSV, CONFIRM_FOOTBALL_DATA_CSV_COMMIT=1 but remains not wired.
	@if [ "$(CONFIRM_FOOTBALL_DATA_CSV_COMMIT)" != "1" ]; then \
		echo "BLOCKED: football-data CSV commit requires CONFIRM_FOOTBALL_DATA_CSV_COMMIT=1 and is not wired in Phase 4.63C."; \
		exit 1; \
	fi
	@echo "BLOCKED: football-data CSV commit is not wired in Phase 4.63C."
	@exit 1

data-football-data-db-write-preflight: ## Preview future Football-Data small DB write runbook. Requires SOURCE_MANIFEST and LOCAL_CSV.
	@if [ -z "$(SOURCE_MANIFEST)" ] || [ -z "$(LOCAL_CSV)" ]; then \
		echo "ERROR: provide SOURCE_MANIFEST=<path> and LOCAL_CSV=<path>"; \
		exit 1; \
	fi
	@echo "Running Football-Data DB write preflight preview: SOURCE_MANIFEST=$(SOURCE_MANIFEST), LOCAL_CSV=$(LOCAL_CSV)"
	$(COMPOSE_DEV) exec -T dev test -f "$(SOURCE_MANIFEST)"
	$(COMPOSE_DEV) exec -T dev test -f "$(LOCAL_CSV)"
	$(COMPOSE_DEV) exec -T dev node scripts/ops/football_data_db_write_preflight.js --source-manifest "$(SOURCE_MANIFEST)" --local-csv "$(LOCAL_CSV)"

data-football-data-db-write-commit: ## Blocked Football-Data DB write gate. Requires SOURCE_MANIFEST, LOCAL_CSV, CONFIRM_FOOTBALL_DATA_DB_WRITE=1 but remains not wired.
	@if [ "$(CONFIRM_FOOTBALL_DATA_DB_WRITE)" != "1" ]; then \
		echo "BLOCKED: football-data DB write requires CONFIRM_FOOTBALL_DATA_DB_WRITE=1 and is not wired in Phase 4.64C."; \
		exit 1; \
	fi
	@echo "BLOCKED: football-data DB write commit is not wired in Phase 4.64C."
	@exit 1

data-football-data-duplicate-precheck: ## Run SELECT-only Football-Data duplicate/existing match precheck. Requires SOURCE_MANIFEST and LOCAL_CSV.
	@if [ -z "$(SOURCE_MANIFEST)" ] || [ -z "$(LOCAL_CSV)" ]; then \
		echo "ERROR: provide SOURCE_MANIFEST=<path> and LOCAL_CSV=<path>"; \
		exit 1; \
	fi
	@echo "Running Football-Data SELECT-only duplicate precheck: SOURCE_MANIFEST=$(SOURCE_MANIFEST), LOCAL_CSV=$(LOCAL_CSV)"
	$(COMPOSE_DEV) exec -T dev test -f "$(SOURCE_MANIFEST)"
	$(COMPOSE_DEV) exec -T dev test -f "$(LOCAL_CSV)"
	$(COMPOSE_DEV) exec -T dev node scripts/ops/football_data_duplicate_precheck.js --source-manifest "$(SOURCE_MANIFEST)" --local-csv "$(LOCAL_CSV)"

data-football-data-duplicate-precheck-commit: ## Blocked Football-Data duplicate precheck commit gate. Requires CONFIRM_FOOTBALL_DATA_DUPLICATE_PRECHECK=1 but remains not wired.
	@if [ "$(CONFIRM_FOOTBALL_DATA_DUPLICATE_PRECHECK)" != "1" ]; then \
		echo "BLOCKED: football-data duplicate precheck requires CONFIRM_FOOTBALL_DATA_DUPLICATE_PRECHECK=1 and is not wired in Phase 4.65C."; \
		exit 1; \
	fi
	@echo "BLOCKED: football-data duplicate precheck commit is not wired in Phase 4.65C."
	@exit 1

data-football-data-small-write-auth-preview: ## Preview future Football-Data small DB write authorization checklist. Requires SOURCE_MANIFEST and LOCAL_CSV.
	@if [ -z "$(SOURCE_MANIFEST)" ] || [ -z "$(LOCAL_CSV)" ]; then \
		echo "ERROR: provide SOURCE_MANIFEST=<path> and LOCAL_CSV=<path>"; \
		exit 1; \
	fi
	@echo "Running Football-Data small DB write authorization preview: SOURCE_MANIFEST=$(SOURCE_MANIFEST), LOCAL_CSV=$(LOCAL_CSV)"
	$(COMPOSE_DEV) exec -T dev test -f "$(SOURCE_MANIFEST)"
	$(COMPOSE_DEV) exec -T dev test -f "$(LOCAL_CSV)"
	$(COMPOSE_DEV) exec -T dev node scripts/ops/football_data_small_write_auth_preview.js --source-manifest "$(SOURCE_MANIFEST)" --local-csv "$(LOCAL_CSV)"

data-football-data-small-write-commit: ## Blocked Football-Data small DB write commit gate. Requires CONFIRM_FOOTBALL_DATA_SMALL_WRITE=1 but remains not wired.
	@if [ "$(CONFIRM_FOOTBALL_DATA_SMALL_WRITE)" != "1" ]; then \
		echo "BLOCKED: football-data small DB write requires CONFIRM_FOOTBALL_DATA_SMALL_WRITE=1 and is not wired in Phase 4.67C."; \
		exit 1; \
	fi
	@echo "BLOCKED: football-data small DB write commit is not wired in Phase 4.67C."
	@exit 1

data-football-data-small-write-runbook-validate: ## Validate Football-Data small DB write approval form template. Requires APPROVAL_FORM.
	@if [ -z "$(APPROVAL_FORM)" ]; then \
		echo "ERROR: provide APPROVAL_FORM=<path>"; \
		exit 1; \
	fi
	@echo "Validating Football-Data small DB write runbook approval form: APPROVAL_FORM=$(APPROVAL_FORM)"
	$(COMPOSE_DEV) exec -T dev test -f "$(APPROVAL_FORM)"
	$(COMPOSE_DEV) exec -T dev node scripts/ops/football_data_small_write_runbook_validate.js --approval-form "$(APPROVAL_FORM)"

data-football-data-small-write-runbook-commit: ## Blocked Football-Data small DB write runbook commit gate. Requires CONFIRM_FOOTBALL_DATA_SMALL_WRITE_RUNBOOK=1 but remains not wired.
	@if [ "$(CONFIRM_FOOTBALL_DATA_SMALL_WRITE_RUNBOOK)" != "1" ]; then \
		echo "BLOCKED: football-data small write runbook commit requires CONFIRM_FOOTBALL_DATA_SMALL_WRITE_RUNBOOK=1 and is not wired in Phase 4.68C."; \
		exit 1; \
	fi
	@echo "BLOCKED: football-data small write runbook commit is not wired in Phase 4.68C."
	@exit 1

data-football-data-small-write-packet-preview: ## Assemble Football-Data small write dry-run packet preview to stdout only. Requires SOURCE_MANIFEST, LOCAL_CSV, APPROVAL_FORM, RUNBOOK_TEMPLATE.
	@if [ -z "$(SOURCE_MANIFEST)" ] || [ -z "$(LOCAL_CSV)" ] || [ -z "$(APPROVAL_FORM)" ] || [ -z "$(RUNBOOK_TEMPLATE)" ]; then \
		echo "ERROR: provide SOURCE_MANIFEST=<path>, LOCAL_CSV=<path>, APPROVAL_FORM=<path>, and RUNBOOK_TEMPLATE=<path>"; \
		exit 1; \
	fi
	@echo "Running Football-Data small write packet preview: SOURCE_MANIFEST=$(SOURCE_MANIFEST), LOCAL_CSV=$(LOCAL_CSV), APPROVAL_FORM=$(APPROVAL_FORM), RUNBOOK_TEMPLATE=$(RUNBOOK_TEMPLATE)"
	$(COMPOSE_DEV) exec -T dev test -f "$(SOURCE_MANIFEST)"
	$(COMPOSE_DEV) exec -T dev test -f "$(LOCAL_CSV)"
	$(COMPOSE_DEV) exec -T dev test -f "$(APPROVAL_FORM)"
	$(COMPOSE_DEV) exec -T dev test -f "$(RUNBOOK_TEMPLATE)"
	$(COMPOSE_DEV) exec -T dev node scripts/ops/football_data_small_write_packet_assembly.js --source-manifest "$(SOURCE_MANIFEST)" --local-csv "$(LOCAL_CSV)" --approval-form "$(APPROVAL_FORM)" --runbook-template "$(RUNBOOK_TEMPLATE)"

data-football-data-small-write-packet-commit: ## Blocked Football-Data small write packet commit gate. Requires CONFIRM_FOOTBALL_DATA_SMALL_WRITE_PACKET=1 but remains not wired.
	@if [ "$(CONFIRM_FOOTBALL_DATA_SMALL_WRITE_PACKET)" != "1" ]; then \
		echo "BLOCKED: football-data small write packet commit requires CONFIRM_FOOTBALL_DATA_SMALL_WRITE_PACKET=1 and is not wired in Phase 4.69C."; \
		exit 1; \
	fi
	@echo "BLOCKED: football-data small write packet commit is not wired in Phase 4.69C."
	@exit 1

data-football-data-packet-file-preflight: ## Preview future Football-Data packet file generation metadata/path only. Requires SOURCE_MANIFEST, LOCAL_CSV, APPROVAL_FORM, RUNBOOK_TEMPLATE.
	@if [ -z "$(SOURCE_MANIFEST)" ] || [ -z "$(LOCAL_CSV)" ] || [ -z "$(APPROVAL_FORM)" ] || [ -z "$(RUNBOOK_TEMPLATE)" ]; then \
		echo "ERROR: provide SOURCE_MANIFEST=<path>, LOCAL_CSV=<path>, APPROVAL_FORM=<path>, and RUNBOOK_TEMPLATE=<path>"; \
		exit 1; \
	fi
	@echo "Running Football-Data packet file preflight: SOURCE_MANIFEST=$(SOURCE_MANIFEST), LOCAL_CSV=$(LOCAL_CSV), APPROVAL_FORM=$(APPROVAL_FORM), RUNBOOK_TEMPLATE=$(RUNBOOK_TEMPLATE)"
	$(COMPOSE_DEV) exec -T dev test -f "$(SOURCE_MANIFEST)"
	$(COMPOSE_DEV) exec -T dev test -f "$(LOCAL_CSV)"
	$(COMPOSE_DEV) exec -T dev test -f "$(APPROVAL_FORM)"
	$(COMPOSE_DEV) exec -T dev test -f "$(RUNBOOK_TEMPLATE)"
	$(COMPOSE_DEV) exec -T dev node scripts/ops/football_data_packet_file_preflight.js --source-manifest "$(SOURCE_MANIFEST)" --local-csv "$(LOCAL_CSV)" --approval-form "$(APPROVAL_FORM)" --runbook-template "$(RUNBOOK_TEMPLATE)"

data-football-data-packet-file-commit: ## Blocked Football-Data packet file generation gate. Requires CONFIRM_FOOTBALL_DATA_PACKET_FILE=1 but remains not wired.
	@if [ "$(CONFIRM_FOOTBALL_DATA_PACKET_FILE)" != "1" ]; then \
		echo "BLOCKED: football-data packet file generation requires CONFIRM_FOOTBALL_DATA_PACKET_FILE=1 and is not wired in Phase 4.70C."; \
		exit 1; \
	fi
	@echo "BLOCKED: football-data packet file generation is not wired in Phase 4.70C."
	@exit 1

data-football-data-packet-file-auth-validate: ## Validate Football-Data packet file creation authorization form template. Requires AUTH_FORM.
	@if [ -z "$(AUTH_FORM)" ]; then \
		echo "ERROR: provide AUTH_FORM=<path>"; \
		exit 1; \
	fi
	@echo "Validating Football-Data packet file creation authorization form: AUTH_FORM=$(AUTH_FORM)"
	$(COMPOSE_DEV) exec -T dev test -f "$(AUTH_FORM)"
	$(COMPOSE_DEV) exec -T dev node scripts/ops/football_data_packet_file_auth_validate.js --auth-form "$(AUTH_FORM)"

data-football-data-packet-file-auth-commit: ## Blocked Football-Data packet file creation authorization commit gate. Requires CONFIRM_FOOTBALL_DATA_PACKET_FILE_AUTH=1 but remains not wired.
	@if [ "$(CONFIRM_FOOTBALL_DATA_PACKET_FILE_AUTH)" != "1" ]; then \
		echo "BLOCKED: football-data packet file creation authorization requires CONFIRM_FOOTBALL_DATA_PACKET_FILE_AUTH=1 and is not wired in Phase 4.71C."; \
		exit 1; \
	fi
	@echo "BLOCKED: football-data packet file creation authorization commit is not wired in Phase 4.71C."
	@exit 1

data-football-data-packet-file-auth-review: ## Run Football-Data packet file creation dry-run authorization review. Requires AUTH_FORM, SOURCE_MANIFEST, LOCAL_CSV, APPROVAL_FORM, RUNBOOK_TEMPLATE.
	@if [ -z "$(AUTH_FORM)" ] || [ -z "$(SOURCE_MANIFEST)" ] || [ -z "$(LOCAL_CSV)" ] || [ -z "$(APPROVAL_FORM)" ] || [ -z "$(RUNBOOK_TEMPLATE)" ]; then \
		echo "ERROR: provide AUTH_FORM=<path>, SOURCE_MANIFEST=<path>, LOCAL_CSV=<path>, APPROVAL_FORM=<path>, and RUNBOOK_TEMPLATE=<path>"; \
		exit 1; \
	fi
	@echo "Running Football-Data packet file authorization review: AUTH_FORM=$(AUTH_FORM), SOURCE_MANIFEST=$(SOURCE_MANIFEST), LOCAL_CSV=$(LOCAL_CSV), APPROVAL_FORM=$(APPROVAL_FORM), RUNBOOK_TEMPLATE=$(RUNBOOK_TEMPLATE)"
	$(COMPOSE_DEV) exec -T dev test -f "$(AUTH_FORM)"
	$(COMPOSE_DEV) exec -T dev test -f "$(SOURCE_MANIFEST)"
	$(COMPOSE_DEV) exec -T dev test -f "$(LOCAL_CSV)"
	$(COMPOSE_DEV) exec -T dev test -f "$(APPROVAL_FORM)"
	$(COMPOSE_DEV) exec -T dev test -f "$(RUNBOOK_TEMPLATE)"
	$(COMPOSE_DEV) exec -T dev node scripts/ops/football_data_packet_file_auth_review.js --auth-form "$(AUTH_FORM)" --source-manifest "$(SOURCE_MANIFEST)" --local-csv "$(LOCAL_CSV)" --approval-form "$(APPROVAL_FORM)" --runbook-template "$(RUNBOOK_TEMPLATE)"

data-football-data-packet-file-auth-review-commit: ## Blocked Football-Data packet file authorization review commit gate. Requires CONFIRM_FOOTBALL_DATA_PACKET_FILE_AUTH_REVIEW=1 but remains not wired.
	@if [ "$(CONFIRM_FOOTBALL_DATA_PACKET_FILE_AUTH_REVIEW)" != "1" ]; then \
		echo "BLOCKED: football-data packet file authorization review requires CONFIRM_FOOTBALL_DATA_PACKET_FILE_AUTH_REVIEW=1 and is not wired in Phase 4.72C."; \
		exit 1; \
	fi
	@echo "BLOCKED: football-data packet file authorization review commit is not wired in Phase 4.72C."
	@exit 1

data-football-data-packet-file-readiness-review: ## Run Football-Data packet file creation readiness checklist consolidation review. Requires READINESS_CHECKLIST, AUTH_FORM, SOURCE_MANIFEST, LOCAL_CSV, APPROVAL_FORM, RUNBOOK_TEMPLATE.
	@if [ -z "$(READINESS_CHECKLIST)" ] || [ -z "$(AUTH_FORM)" ] || [ -z "$(SOURCE_MANIFEST)" ] || [ -z "$(LOCAL_CSV)" ] || [ -z "$(APPROVAL_FORM)" ] || [ -z "$(RUNBOOK_TEMPLATE)" ]; then \
		echo "ERROR: provide READINESS_CHECKLIST=<path>, AUTH_FORM=<path>, SOURCE_MANIFEST=<path>, LOCAL_CSV=<path>, APPROVAL_FORM=<path>, and RUNBOOK_TEMPLATE=<path>"; \
		exit 1; \
	fi
	@echo "Running Football-Data packet file readiness review: READINESS_CHECKLIST=$(READINESS_CHECKLIST), AUTH_FORM=$(AUTH_FORM), SOURCE_MANIFEST=$(SOURCE_MANIFEST), LOCAL_CSV=$(LOCAL_CSV), APPROVAL_FORM=$(APPROVAL_FORM), RUNBOOK_TEMPLATE=$(RUNBOOK_TEMPLATE)"
	$(COMPOSE_DEV) exec -T dev test -f "$(READINESS_CHECKLIST)"
	$(COMPOSE_DEV) exec -T dev test -f "$(AUTH_FORM)"
	$(COMPOSE_DEV) exec -T dev test -f "$(SOURCE_MANIFEST)"
	$(COMPOSE_DEV) exec -T dev test -f "$(LOCAL_CSV)"
	$(COMPOSE_DEV) exec -T dev test -f "$(APPROVAL_FORM)"
	$(COMPOSE_DEV) exec -T dev test -f "$(RUNBOOK_TEMPLATE)"
	$(COMPOSE_DEV) exec -T dev node scripts/ops/football_data_packet_file_readiness_review.js --readiness-checklist "$(READINESS_CHECKLIST)" --auth-form "$(AUTH_FORM)" --source-manifest "$(SOURCE_MANIFEST)" --local-csv "$(LOCAL_CSV)" --approval-form "$(APPROVAL_FORM)" --runbook-template "$(RUNBOOK_TEMPLATE)"

data-football-data-packet-file-readiness-commit: ## Blocked Football-Data packet file readiness commit gate. Requires CONFIRM_FOOTBALL_DATA_PACKET_FILE_READINESS=1 but remains not wired.
	@if [ "$(CONFIRM_FOOTBALL_DATA_PACKET_FILE_READINESS)" != "1" ]; then \
		echo "BLOCKED: football-data packet file readiness requires CONFIRM_FOOTBALL_DATA_PACKET_FILE_READINESS=1 and is not wired in Phase 4.73C."; \
		exit 1; \
	fi
	@echo "BLOCKED: football-data packet file readiness commit is not wired in Phase 4.73C."
	@exit 1

data-football-data-packet-file-auth-packet-draft: ## Run Football-Data packet file creation authorization packet draft review. Requires DRAFT_TEMPLATE, READINESS_CHECKLIST, AUTH_FORM, SOURCE_MANIFEST, LOCAL_CSV, APPROVAL_FORM, RUNBOOK_TEMPLATE.
	@if [ -z "$(DRAFT_TEMPLATE)" ] || [ -z "$(READINESS_CHECKLIST)" ] || [ -z "$(AUTH_FORM)" ] || [ -z "$(SOURCE_MANIFEST)" ] || [ -z "$(LOCAL_CSV)" ] || [ -z "$(APPROVAL_FORM)" ] || [ -z "$(RUNBOOK_TEMPLATE)" ]; then \
		echo "ERROR: provide DRAFT_TEMPLATE=<path>, READINESS_CHECKLIST=<path>, AUTH_FORM=<path>, SOURCE_MANIFEST=<path>, LOCAL_CSV=<path>, APPROVAL_FORM=<path>, and RUNBOOK_TEMPLATE=<path>"; \
		exit 1; \
	fi
	@echo "Running Football-Data auth packet draft review: DRAFT_TEMPLATE=$(DRAFT_TEMPLATE), READINESS_CHECKLIST=$(READINESS_CHECKLIST), AUTH_FORM=$(AUTH_FORM), SOURCE_MANIFEST=$(SOURCE_MANIFEST), LOCAL_CSV=$(LOCAL_CSV), APPROVAL_FORM=$(APPROVAL_FORM), RUNBOOK_TEMPLATE=$(RUNBOOK_TEMPLATE)"
	$(COMPOSE_DEV) exec -T dev test -f "$(DRAFT_TEMPLATE)"
	$(COMPOSE_DEV) exec -T dev test -f "$(READINESS_CHECKLIST)"
	$(COMPOSE_DEV) exec -T dev test -f "$(AUTH_FORM)"
	$(COMPOSE_DEV) exec -T dev test -f "$(SOURCE_MANIFEST)"
	$(COMPOSE_DEV) exec -T dev test -f "$(LOCAL_CSV)"
	$(COMPOSE_DEV) exec -T dev test -f "$(APPROVAL_FORM)"
	$(COMPOSE_DEV) exec -T dev test -f "$(RUNBOOK_TEMPLATE)"
	$(COMPOSE_DEV) exec -T dev node scripts/ops/football_data_packet_file_auth_packet_draft.js --draft-template "$(DRAFT_TEMPLATE)" --readiness-checklist "$(READINESS_CHECKLIST)" --auth-form "$(AUTH_FORM)" --source-manifest "$(SOURCE_MANIFEST)" --local-csv "$(LOCAL_CSV)" --approval-form "$(APPROVAL_FORM)" --runbook-template "$(RUNBOOK_TEMPLATE)"

data-football-data-packet-file-auth-packet-draft-commit: ## Blocked Football-Data auth packet draft commit gate. Requires CONFIRM_FOOTBALL_DATA_PACKET_FILE_AUTH_PACKET_DRAFT=1 but remains not wired.
	@if [ "$(CONFIRM_FOOTBALL_DATA_PACKET_FILE_AUTH_PACKET_DRAFT)" != "1" ]; then \
		echo "BLOCKED: football-data auth packet draft requires CONFIRM_FOOTBALL_DATA_PACKET_FILE_AUTH_PACKET_DRAFT=1 and is not wired in Phase 4.74C."; \
		exit 1; \
	fi
	@echo "BLOCKED: football-data auth packet draft commit is not wired in Phase 4.74C."
	@exit 1

data-football-data-packet-file-auth-review-consolidation: ## Run Football-Data packet file creation authorization review consolidation. Requires CONSOLIDATION_TEMPLATE, DRAFT_TEMPLATE, READINESS_CHECKLIST, AUTH_FORM, SOURCE_MANIFEST, LOCAL_CSV, APPROVAL_FORM, RUNBOOK_TEMPLATE.
	@if [ -z "$(CONSOLIDATION_TEMPLATE)" ] || [ -z "$(DRAFT_TEMPLATE)" ] || [ -z "$(READINESS_CHECKLIST)" ] || [ -z "$(AUTH_FORM)" ] || [ -z "$(SOURCE_MANIFEST)" ] || [ -z "$(LOCAL_CSV)" ] || [ -z "$(APPROVAL_FORM)" ] || [ -z "$(RUNBOOK_TEMPLATE)" ]; then \
		echo "ERROR: provide CONSOLIDATION_TEMPLATE=<path>, DRAFT_TEMPLATE=<path>, READINESS_CHECKLIST=<path>, AUTH_FORM=<path>, SOURCE_MANIFEST=<path>, LOCAL_CSV=<path>, APPROVAL_FORM=<path>, and RUNBOOK_TEMPLATE=<path>"; \
		exit 1; \
	fi
	@echo "Running Football-Data auth review consolidation: CONSOLIDATION_TEMPLATE=$(CONSOLIDATION_TEMPLATE)"
	$(COMPOSE_DEV) exec -T dev test -f "$(CONSOLIDATION_TEMPLATE)"
	$(COMPOSE_DEV) exec -T dev test -f "$(DRAFT_TEMPLATE)"
	$(COMPOSE_DEV) exec -T dev test -f "$(READINESS_CHECKLIST)"
	$(COMPOSE_DEV) exec -T dev test -f "$(AUTH_FORM)"
	$(COMPOSE_DEV) exec -T dev test -f "$(SOURCE_MANIFEST)"
	$(COMPOSE_DEV) exec -T dev test -f "$(LOCAL_CSV)"
	$(COMPOSE_DEV) exec -T dev test -f "$(APPROVAL_FORM)"
	$(COMPOSE_DEV) exec -T dev test -f "$(RUNBOOK_TEMPLATE)"
	$(COMPOSE_DEV) exec -T dev node scripts/ops/football_data_packet_file_auth_review_consolidation.js --consolidation-template "$(CONSOLIDATION_TEMPLATE)" --draft-template "$(DRAFT_TEMPLATE)" --readiness-checklist "$(READINESS_CHECKLIST)" --auth-form "$(AUTH_FORM)" --source-manifest "$(SOURCE_MANIFEST)" --local-csv "$(LOCAL_CSV)" --approval-form "$(APPROVAL_FORM)" --runbook-template "$(RUNBOOK_TEMPLATE)"

data-football-data-packet-file-auth-review-consolidation-commit: ## Blocked Football-Data auth review consolidation commit gate. Requires CONFIRM_FOOTBALL_DATA_PACKET_FILE_AUTH_REVIEW_CONSOLIDATION=1 but remains not wired.
	@if [ "$(CONFIRM_FOOTBALL_DATA_PACKET_FILE_AUTH_REVIEW_CONSOLIDATION)" != "1" ]; then \
		echo "BLOCKED: football-data auth review consolidation requires CONFIRM_FOOTBALL_DATA_PACKET_FILE_AUTH_REVIEW_CONSOLIDATION=1 and is not wired in Phase 4.75C."; \
		exit 1; \
	fi
	@echo "BLOCKED: football-data auth review consolidation commit is not wired in Phase 4.75C."
	@exit 1

data-football-data-packet-file-preauth-closure: ## Run Football-Data packet file creation pre-authorization closure. Requires CLOSURE_TEMPLATE, CONSOLIDATION_TEMPLATE, DRAFT_TEMPLATE, READINESS_CHECKLIST, AUTH_FORM, SOURCE_MANIFEST, LOCAL_CSV, APPROVAL_FORM, RUNBOOK_TEMPLATE.
	@if [ -z "$(CLOSURE_TEMPLATE)" ] || [ -z "$(CONSOLIDATION_TEMPLATE)" ] || [ -z "$(DRAFT_TEMPLATE)" ] || [ -z "$(READINESS_CHECKLIST)" ] || [ -z "$(AUTH_FORM)" ] || [ -z "$(SOURCE_MANIFEST)" ] || [ -z "$(LOCAL_CSV)" ] || [ -z "$(APPROVAL_FORM)" ] || [ -z "$(RUNBOOK_TEMPLATE)" ]; then \
		echo "ERROR: provide CLOSURE_TEMPLATE=<path>, CONSOLIDATION_TEMPLATE=<path>, DRAFT_TEMPLATE=<path>, READINESS_CHECKLIST=<path>, AUTH_FORM=<path>, SOURCE_MANIFEST=<path>, LOCAL_CSV=<path>, APPROVAL_FORM=<path>, and RUNBOOK_TEMPLATE=<path>"; \
		exit 1; \
	fi
	@echo "Running Football-Data packet file pre-authorization closure: CLOSURE_TEMPLATE=$(CLOSURE_TEMPLATE)"
	$(COMPOSE_DEV) exec -T dev test -f "$(CLOSURE_TEMPLATE)"
	$(COMPOSE_DEV) exec -T dev test -f "$(CONSOLIDATION_TEMPLATE)"
	$(COMPOSE_DEV) exec -T dev test -f "$(DRAFT_TEMPLATE)"
	$(COMPOSE_DEV) exec -T dev test -f "$(READINESS_CHECKLIST)"
	$(COMPOSE_DEV) exec -T dev test -f "$(AUTH_FORM)"
	$(COMPOSE_DEV) exec -T dev test -f "$(SOURCE_MANIFEST)"
	$(COMPOSE_DEV) exec -T dev test -f "$(LOCAL_CSV)"
	$(COMPOSE_DEV) exec -T dev test -f "$(APPROVAL_FORM)"
	$(COMPOSE_DEV) exec -T dev test -f "$(RUNBOOK_TEMPLATE)"
	$(COMPOSE_DEV) exec -T dev node scripts/ops/football_data_packet_file_preauthorization_closure.js --closure-template "$(CLOSURE_TEMPLATE)" --consolidation-template "$(CONSOLIDATION_TEMPLATE)" --draft-template "$(DRAFT_TEMPLATE)" --readiness-checklist "$(READINESS_CHECKLIST)" --auth-form "$(AUTH_FORM)" --source-manifest "$(SOURCE_MANIFEST)" --local-csv "$(LOCAL_CSV)" --approval-form "$(APPROVAL_FORM)" --runbook-template "$(RUNBOOK_TEMPLATE)"

data-football-data-packet-file-preauth-closure-commit: ## Blocked Football-Data pre-authorization closure commit gate. Requires CONFIRM_FOOTBALL_DATA_PACKET_FILE_PREAUTH_CLOSURE=1 but remains not wired.
	@if [ "$(CONFIRM_FOOTBALL_DATA_PACKET_FILE_PREAUTH_CLOSURE)" != "1" ]; then \
		echo "BLOCKED: football-data packet file pre-authorization closure requires CONFIRM_FOOTBALL_DATA_PACKET_FILE_PREAUTH_CLOSURE=1 and is not wired in Phase 4.76C."; \
		exit 1; \
	fi
	@echo "BLOCKED: football-data packet file pre-authorization closure commit is not wired in Phase 4.76C."
	@exit 1

data-football-data-insert-policy-precheck: ## Run SELECT-only Football-Data deterministic match_id + insert policy precheck. Requires SOURCE_MANIFEST and LOCAL_CSV.
	@if [ -z "$(SOURCE_MANIFEST)" ] || [ -z "$(LOCAL_CSV)" ]; then \
		echo "ERROR: provide SOURCE_MANIFEST=<path> and LOCAL_CSV=<path>"; \
		exit 1; \
	fi
	@echo "Running Football-Data insert policy precheck: SOURCE_MANIFEST=$(SOURCE_MANIFEST), LOCAL_CSV=$(LOCAL_CSV)"
	$(COMPOSE_DEV) exec -T dev test -f "$(SOURCE_MANIFEST)"
	$(COMPOSE_DEV) exec -T dev test -f "$(LOCAL_CSV)"
	$(COMPOSE_DEV) exec -T dev node scripts/ops/football_data_insert_policy_precheck.js --source-manifest "$(SOURCE_MANIFEST)" --local-csv "$(LOCAL_CSV)"

data-football-data-insert-policy-commit: ## Blocked Football-Data insert policy commit gate. Requires CONFIRM_FOOTBALL_DATA_INSERT_POLICY=1 but remains not wired.
	@if [ "$(CONFIRM_FOOTBALL_DATA_INSERT_POLICY)" != "1" ]; then \
		echo "BLOCKED: football-data insert policy requires CONFIRM_FOOTBALL_DATA_INSERT_POLICY=1 and is not wired in Phase 4.66C."; \
		exit 1; \
	fi
	@echo "BLOCKED: football-data insert policy commit is not wired in Phase 4.66C."
	@exit 1

data-acquisition-engines: ## List acquisition engine registry entries. No network, no DB writes.
	$(COMPOSE_DEV) exec -T dev node scripts/ops/acquisition_engine_gate.js --list

data-acquisition-engine-audit: ## Audit acquisition engine registry. No network, no DB writes.
	$(COMPOSE_DEV) exec -T dev node scripts/ops/acquisition_engine_gate.js --audit

data-single-target-network-dry-run: ## Scaffold-only single-target network dry-run gate. Requires ENGINE, TARGET_MATCH_ID, SOURCE_MANIFEST.
	@if [ -z "$(ENGINE)" ] || [ -z "$(TARGET_MATCH_ID)" ] || [ -z "$(SOURCE_MANIFEST)" ]; then \
		echo "ERROR: provide ENGINE=<engine>, TARGET_MATCH_ID=<id>, and SOURCE_MANIFEST=<path>"; \
		exit 1; \
	fi
	@echo "Running Phase 4.54 scaffold-only single-target network gate: ENGINE=$(ENGINE), TARGET_MATCH_ID=$(TARGET_MATCH_ID), SOURCE_MANIFEST=$(SOURCE_MANIFEST)"
	$(COMPOSE_DEV) exec -T dev test -f "$(SOURCE_MANIFEST)"
	$(COMPOSE_DEV) exec -T dev node scripts/ops/acquisition_engine_gate.js --engine "$(ENGINE)" --target-match-id "$(TARGET_MATCH_ID)" --source-manifest "$(SOURCE_MANIFEST)"

data-single-target-network-commit: ## Blocked acquisition network commit gate. Requires CONFIRM_SINGLE_TARGET_NETWORK=1 but remains not wired in Phase 4.54.
	@if [ "$(CONFIRM_SINGLE_TARGET_NETWORK)" != "1" ]; then \
		echo "BLOCKED: acquisition network commit requires CONFIRM_SINGLE_TARGET_NETWORK=1 and is not wired in Phase 4.54."; \
		exit 1; \
	fi
	@echo "BLOCKED: acquisition network commit is not wired in Phase 4.54."
	@exit 1

data-single-target-acquisition-runtime-scaffold: ## Scaffold-only single-target acquisition runtime plan preview. Phase 4.79D. Requires TARGET_SOURCE, TARGET_ENGINE_FAMILY, TARGET_SCOPE_TYPE, plus scope fields and yes/no fields.
	@if [ -z "$(TARGET_SOURCE)" ] || [ -z "$(TARGET_ENGINE_FAMILY)" ] || [ -z "$(TARGET_SCOPE_TYPE)" ]; then \
		echo "ERROR: provide TARGET_SOURCE=<src>, TARGET_ENGINE_FAMILY=titan_discovery, TARGET_SCOPE_TYPE=<match_id|league_season_date>"; \
		echo "  plus scope-specific fields and yes/no authorization fields."; \
		echo "  See docs/_reports/SINGLE_TARGET_ACQUISITION_RUNTIME_DESIGN_PHASE4_78D.md for full parameter contract."; \
		exit 1; \
	fi
	@echo "Phase 4.79D: single-target acquisition runtime scaffold (scaffold-only, no network, no DB, no staging)"
	$(COMPOSE_DEV) exec -T dev node scripts/ops/single_target_acquisition_runtime_scaffold.js \
		--target-source "$(TARGET_SOURCE)" \
		--target-engine-family "$(TARGET_ENGINE_FAMILY)" \
		--target-scope-type "$(TARGET_SCOPE_TYPE)" \
		$(if $(TARGET_MATCH_ID),--target-match-id "$(TARGET_MATCH_ID)") \
		$(if $(TARGET_LEAGUE),--target-league "$(TARGET_LEAGUE)") \
		$(if $(TARGET_SEASON),--target-season "$(TARGET_SEASON)") \
		$(if $(TARGET_DATE),--target-date "$(TARGET_DATE)") \
		--terms-approval "$(or $(TERMS_APPROVAL),no)" \
		--network-dry-run-authorization "$(or $(NETWORK_DRY_RUN_AUTHORIZATION),no)" \
		--allow-browser-runtime "$(or $(ALLOW_BROWSER_RUNTIME),no)" \
		--allow-proxy-runtime "$(or $(ALLOW_PROXY_RUNTIME),no)" \
		--allow-external-network "$(or $(ALLOW_EXTERNAL_NETWORK),no)" \
		--allow-staging-write "$(or $(ALLOW_STAGING_WRITE),no)" \
		--confirm-single-target-scope "$(or $(CONFIRM_SINGLE_TARGET_SCOPE),no)"

data-single-target-acquisition-runtime-commit: ## Blocked single-target acquisition runtime commit gate. Remains not wired in Phase 4.79D.
	@echo "BLOCKED: single-target acquisition runtime commit/execution is not wired in Phase 4.79D."
	@echo "  Even with CONFIRM_SINGLE_TARGET_ACQUISITION_RUNTIME=1, this path remains blocked."
	@echo "  Real network dry-run requires a separate future phase with explicit source/target/terms/network/staging authorization."
	@exit 1

data-single-target-acquisition-staging-schema-validate: ## Local-only staging artifact / manifest schema validation. Phase 4.80D. Requires ARTIFACT_SCHEMA, MANIFEST_SCHEMA, ARTIFACT, MANIFEST (at least one pair).
	@if [ -z "$(ARTIFACT_SCHEMA)" ] && [ -z "$(MANIFEST_SCHEMA)" ]; then \
		echo "ERROR: provide at least one pair: ARTIFACT_SCHEMA=<path> + ARTIFACT=<path> and/or MANIFEST_SCHEMA=<path> + MANIFEST=<path>"; \
		exit 1; \
	fi
	@echo "Phase 4.80D: staging schema validator (local-only, no network, no DB, no staging writes)"
	$(COMPOSE_DEV) exec -T dev node scripts/ops/single_target_acquisition_staging_schema_validator.js \
		$(if $(ARTIFACT_SCHEMA),--artifact-schema "$(ARTIFACT_SCHEMA)") \
		$(if $(MANIFEST_SCHEMA),--manifest-schema "$(MANIFEST_SCHEMA)") \
		$(if $(ARTIFACT),--artifact "$(ARTIFACT)") \
		$(if $(MANIFEST),--manifest "$(MANIFEST)")

data-single-target-acquisition-staging-schema-commit: ## Blocked staging schema commit gate. Remains not wired in Phase 4.80D.
	@echo "BLOCKED: single-target acquisition staging schema commit/execution is not wired in Phase 4.80D."
	@echo "  Even with CONFIRM_SINGLE_TARGET_ACQUISITION_STAGING_SCHEMA=1, this path remains blocked."
	@echo "  Real staging write requires a separate future phase with explicit source/target/terms/network/staging authorization."
	@exit 1

data-single-target-acquisition-staging-writer-preflight: ## Preflight-only staging writer preflight. Phase 4.81D. Validates schema, target consistency, output root policy, and previews future paths.
	@if [ -z "$(ARTIFACT_SCHEMA)" ] || [ -z "$(MANIFEST_SCHEMA)" ] || [ -z "$(ARTIFACT)" ] || [ -z "$(MANIFEST)" ] || [ -z "$(OUTPUT_ROOT)" ]; then \
		echo "ERROR: provide ARTIFACT_SCHEMA=<path>, MANIFEST_SCHEMA=<path>, ARTIFACT=<path>, MANIFEST=<path>, OUTPUT_ROOT=<path>"; \
		exit 1; \
	fi
	@echo "Phase 4.81D: staging writer preflight (preflight-only, no writes, no network, no DB)"
	$(COMPOSE_DEV) exec -T dev node scripts/ops/single_target_acquisition_staging_writer_preflight.js \
		--artifact-schema "$(ARTIFACT_SCHEMA)" \
		--manifest-schema "$(MANIFEST_SCHEMA)" \
		--artifact "$(ARTIFACT)" \
		--manifest "$(MANIFEST)" \
		--output-root "$(OUTPUT_ROOT)" \
		$(if $(TARGET_SOURCE),--target-source "$(TARGET_SOURCE)") \
		$(if $(TARGET_ENGINE_FAMILY),--target-engine-family "$(TARGET_ENGINE_FAMILY)") \
		$(if $(TARGET_SCOPE_TYPE),--target-scope-type "$(TARGET_SCOPE_TYPE)") \
		$(if $(TARGET_MATCH_ID),--target-match-id "$(TARGET_MATCH_ID)") \
		$(if $(TARGET_LEAGUE),--target-league "$(TARGET_LEAGUE)") \
		$(if $(TARGET_SEASON),--target-season "$(TARGET_SEASON)") \
		$(if $(TARGET_DATE),--target-date "$(TARGET_DATE)") \
		--staging-write-authorization "$(or $(STAGING_WRITE_AUTHORIZATION),no)" \
		--final-human-confirmation "$(or $(FINAL_HUMAN_CONFIRMATION),no)"

data-single-target-acquisition-staging-writer-commit: ## Blocked staging writer commit gate. Remains not wired in Phase 4.81D.
	@echo "BLOCKED: single-target acquisition staging writer commit/execution is not wired in Phase 4.81D."
	@echo "  Even with CONFIRM_SINGLE_TARGET_ACQUISITION_STAGING_WRITE=1, this path remains blocked."
	@echo "  Real staging write requires a separate future phase with explicit source/target/terms/network/staging authorization."
	@exit 1

data-single-target-acquisition-staging-packet-preview: ## Packet preview aggregating 4.79D scaffold + 4.80D schema + 4.81D preflight. Phase 4.82D. No writes, no network, no DB.
	@if [ -z "$(ARTIFACT_SCHEMA)" ] || [ -z "$(MANIFEST_SCHEMA)" ] || [ -z "$(ARTIFACT)" ] || [ -z "$(MANIFEST)" ] || [ -z "$(OUTPUT_ROOT)" ]; then \
		echo "ERROR: provide ARTIFACT_SCHEMA=<path>, MANIFEST_SCHEMA=<path>, ARTIFACT=<path>, MANIFEST=<path>, OUTPUT_ROOT=<path>"; \
		exit 1; \
	fi
	@echo "Phase 4.82D: staging packet preview (aggregated preview-only, no writes, no network, no DB)"
	$(COMPOSE_DEV) exec -T dev node scripts/ops/single_target_acquisition_staging_packet_preview.js \
		--artifact-schema "$(ARTIFACT_SCHEMA)" \
		--manifest-schema "$(MANIFEST_SCHEMA)" \
		--artifact "$(ARTIFACT)" \
		--manifest "$(MANIFEST)" \
		--output-root "$(OUTPUT_ROOT)" \
		$(if $(TARGET_SOURCE),--target-source "$(TARGET_SOURCE)") \
		$(if $(TARGET_ENGINE_FAMILY),--target-engine-family "$(TARGET_ENGINE_FAMILY)") \
		$(if $(TARGET_SCOPE_TYPE),--target-scope-type "$(TARGET_SCOPE_TYPE)") \
		$(if $(TARGET_MATCH_ID),--target-match-id "$(TARGET_MATCH_ID)") \
		$(if $(TARGET_LEAGUE),--target-league "$(TARGET_LEAGUE)") \
		$(if $(TARGET_SEASON),--target-season "$(TARGET_SEASON)") \
		$(if $(TARGET_DATE),--target-date "$(TARGET_DATE)") \
		--terms-approval "$(or $(TERMS_APPROVAL),no)" \
		--network-dry-run-authorization "$(or $(NETWORK_DRY_RUN_AUTHORIZATION),no)" \
		--allow-browser-runtime "$(or $(ALLOW_BROWSER_RUNTIME),no)" \
		--allow-proxy-runtime "$(or $(ALLOW_PROXY_RUNTIME),no)" \
		--allow-external-network "$(or $(ALLOW_EXTERNAL_NETWORK),no)" \
		--allow-staging-write "$(or $(ALLOW_STAGING_WRITE),no)" \
		--confirm-single-target-scope "$(or $(CONFIRM_SINGLE_TARGET_SCOPE),no)" \
		--staging-write-authorization "$(or $(STAGING_WRITE_AUTHORIZATION),no)" \
		--final-human-confirmation "$(or $(FINAL_HUMAN_CONFIRMATION),no)"

data-single-target-acquisition-staging-packet-commit: ## Blocked staging packet commit gate. Remains not wired in Phase 4.82D.
	@echo "BLOCKED: single-target acquisition staging packet commit/execution is not wired in Phase 4.82D."
	@echo "  Even with CONFIRM_SINGLE_TARGET_ACQUISITION_STAGING_PACKET=1, this path remains blocked."
	@exit 1

data-single-target-acquisition-pre-network-runbook-validate: ## Draft-only pre-network runbook validation. Phase 4.83D. No network, no writes, no DB.
	@if [ -z "$(RUNBOOK)" ] || [ -z "$(ARTIFACT_SCHEMA)" ] || [ -z "$(MANIFEST_SCHEMA)" ] || [ -z "$(ARTIFACT)" ] || [ -z "$(MANIFEST)" ] || [ -z "$(OUTPUT_ROOT)" ] || [ -z "$(TARGET_SOURCE)" ] || [ -z "$(TARGET_ENGINE_FAMILY)" ] || [ -z "$(TARGET_SCOPE_TYPE)" ] || [ -z "$(TARGET_MATCH_ID)" ]; then \
		echo "ERROR: provide RUNBOOK=<path>, ARTIFACT_SCHEMA=<path>, MANIFEST_SCHEMA=<path>, ARTIFACT=<path>, MANIFEST=<path>, OUTPUT_ROOT=<path>, TARGET_SOURCE=<src>, TARGET_ENGINE_FAMILY=titan_discovery, TARGET_SCOPE_TYPE=<type>, TARGET_MATCH_ID=<id>"; \
		exit 1; \
	fi
	@echo "Phase 4.83D: pre-network runbook validate (draft-only, local-only, no writes, no network, no DB)"
	$(PRE_NETWORK_RUNBOOK_NODE) scripts/ops/single_target_acquisition_pre_network_runbook_validate.js \
		--runbook "$(RUNBOOK)" \
		--artifact-schema "$(ARTIFACT_SCHEMA)" \
		--manifest-schema "$(MANIFEST_SCHEMA)" \
		--artifact "$(ARTIFACT)" \
		--manifest "$(MANIFEST)" \
		--output-root "$(OUTPUT_ROOT)" \
		--target-source "$(TARGET_SOURCE)" \
		--target-engine-family "$(TARGET_ENGINE_FAMILY)" \
		--target-scope-type "$(TARGET_SCOPE_TYPE)" \
		--target-match-id "$(TARGET_MATCH_ID)" \
		$(if $(TARGET_LEAGUE),--target-league "$(TARGET_LEAGUE)") \
		$(if $(TARGET_SEASON),--target-season "$(TARGET_SEASON)") \
		$(if $(TARGET_DATE),--target-date "$(TARGET_DATE)") \
		--terms-approval "$(or $(TERMS_APPROVAL),no)" \
		--network-dry-run-authorization "$(or $(NETWORK_DRY_RUN_AUTHORIZATION),no)" \
		--allow-browser-runtime "$(or $(ALLOW_BROWSER_RUNTIME),no)" \
		--allow-proxy-runtime "$(or $(ALLOW_PROXY_RUNTIME),no)" \
		--allow-external-network "$(or $(ALLOW_EXTERNAL_NETWORK),no)" \
		--allow-staging-write "$(or $(ALLOW_STAGING_WRITE),no)" \
		--confirm-single-target-scope "$(or $(CONFIRM_SINGLE_TARGET_SCOPE),no)" \
		--staging-write-authorization "$(or $(STAGING_WRITE_AUTHORIZATION),no)" \
		--final-human-confirmation "$(or $(FINAL_HUMAN_CONFIRMATION),no)"

data-single-target-acquisition-pre-network-runbook-commit: ## Blocked pre-network runbook execution gate. Remains not wired in Phase 4.83D.
	@echo "BLOCKED: single-target acquisition pre-network runbook execution is not wired in Phase 4.83D."
	@echo "  Even with CONFIRM_SINGLE_TARGET_ACQUISITION_PRE_NETWORK_RUNBOOK=1, this path remains blocked."
	@echo "  Phase 4.83D validates a draft only and does not authorize any network dry-run, staging write, or DB write."
	@exit 1

data-single-target-acquisition-network-auth-form-validate: ## Template-only network auth form validation. Phase 4.84D. No network, no writes, no DB.
	@if [ -z "$(AUTH_FORM)" ] || [ -z "$(RUNBOOK)" ] || [ -z "$(TARGET_SOURCE)" ] || [ -z "$(TARGET_ENGINE_FAMILY)" ] || [ -z "$(TARGET_SCOPE_TYPE)" ] || [ -z "$(TARGET_MATCH_ID)" ]; then \
		echo "ERROR: provide AUTH_FORM=<path>, RUNBOOK=<path>, TARGET_SOURCE=<src>, TARGET_ENGINE_FAMILY=titan_discovery, TARGET_SCOPE_TYPE=<type>, TARGET_MATCH_ID=<id>"; \
		exit 1; \
	fi
	@echo "Phase 4.84D: network auth form validate (template-only, local-only, no writes, no network, no DB)"
	$(NETWORK_AUTH_FORM_NODE) scripts/ops/single_target_acquisition_network_auth_form_validate.js \
		--auth-form "$(AUTH_FORM)" \
		--runbook "$(RUNBOOK)" \
		--target-source "$(TARGET_SOURCE)" \
		--target-engine-family "$(TARGET_ENGINE_FAMILY)" \
		--target-scope-type "$(TARGET_SCOPE_TYPE)" \
		--target-match-id "$(TARGET_MATCH_ID)" \
		$(if $(TARGET_LEAGUE),--target-league "$(TARGET_LEAGUE)") \
		$(if $(TARGET_SEASON),--target-season "$(TARGET_SEASON)") \
		$(if $(TARGET_DATE),--target-date "$(TARGET_DATE)") \
		--terms-approval "$(or $(TERMS_APPROVAL),no)" \
		--network-dry-run-authorization "$(or $(NETWORK_DRY_RUN_AUTHORIZATION),no)" \
		--allow-browser-runtime "$(or $(ALLOW_BROWSER_RUNTIME),no)" \
		--allow-proxy-runtime "$(or $(ALLOW_PROXY_RUNTIME),no)" \
		--allow-external-network "$(or $(ALLOW_EXTERNAL_NETWORK),no)" \
		--allow-staging-write "$(or $(ALLOW_STAGING_WRITE),no)" \
		--final-human-confirmation "$(or $(FINAL_HUMAN_CONFIRMATION),no)"

data-single-target-acquisition-network-auth-form-commit: ## Blocked network auth form execution gate. Remains not wired in Phase 4.84D.
	@echo "BLOCKED: single-target acquisition network dry-run authorization execution is not wired in Phase 4.84D."
	@echo "  Even with CONFIRM_SINGLE_TARGET_ACQUISITION_NETWORK_AUTH_FORM=1, this path remains blocked."
	@echo "  Phase 4.84D validates a template only and does not authorize any network dry-run, staging write, or DB write."
	@exit 1

data-single-target-acquisition-network-readiness-checklist-validate: ## Template-only final readiness checklist validation. Phase 4.85D. No network, no writes, no DB.
	@if [ -z "$(CHECKLIST)" ] || [ -z "$(RUNBOOK)" ] || [ -z "$(AUTH_FORM)" ] || [ -z "$(TARGET_SOURCE)" ] || [ -z "$(TARGET_ENGINE_FAMILY)" ] || [ -z "$(TARGET_SCOPE_TYPE)" ] || [ -z "$(TARGET_MATCH_ID)" ]; then \
		echo "ERROR: provide CHECKLIST=<path>, RUNBOOK=<path>, AUTH_FORM=<path>, TARGET_SOURCE=<src>, TARGET_ENGINE_FAMILY=titan_discovery, TARGET_SCOPE_TYPE=<type>, TARGET_MATCH_ID=<id>"; \
		exit 1; \
	fi
	@echo "Phase 4.85D: network readiness checklist validate (template-only, local-only, no writes, no network, no DB)"
	$(NETWORK_READINESS_CHECKLIST_NODE) scripts/ops/single_target_acquisition_network_readiness_checklist_validate.js \
		--checklist "$(CHECKLIST)" \
		--runbook "$(RUNBOOK)" \
		--auth-form "$(AUTH_FORM)" \
		--target-source "$(TARGET_SOURCE)" \
		--target-engine-family "$(TARGET_ENGINE_FAMILY)" \
		--target-scope-type "$(TARGET_SCOPE_TYPE)" \
		--target-match-id "$(TARGET_MATCH_ID)" \
		$(if $(TARGET_LEAGUE),--target-league "$(TARGET_LEAGUE)") \
		$(if $(TARGET_SEASON),--target-season "$(TARGET_SEASON)") \
		$(if $(TARGET_DATE),--target-date "$(TARGET_DATE)") \
		--terms-approval "$(or $(TERMS_APPROVAL),no)" \
		--network-dry-run-authorization "$(or $(NETWORK_DRY_RUN_AUTHORIZATION),no)" \
		--allow-browser-runtime "$(or $(ALLOW_BROWSER_RUNTIME),no)" \
		--allow-proxy-runtime "$(or $(ALLOW_PROXY_RUNTIME),no)" \
		--allow-external-network "$(or $(ALLOW_EXTERNAL_NETWORK),no)" \
		--allow-staging-write "$(or $(ALLOW_STAGING_WRITE),no)" \
		--final-human-confirmation "$(or $(FINAL_HUMAN_CONFIRMATION),no)"

data-single-target-acquisition-network-readiness-checklist-commit: ## Blocked network readiness checklist execution gate. Remains not wired in Phase 4.85D.
	@echo "BLOCKED: single-target acquisition network dry-run final readiness execution is not wired in Phase 4.85D."
	@echo "  Even with CONFIRM_SINGLE_TARGET_ACQUISITION_NETWORK_READINESS=1, this path remains blocked."
	@echo "  Phase 4.85D validates a template only and does not authorize any network dry-run, staging write, or DB write."
	@exit 1

data-single-target-acquisition-network-execution-plan-validate: ## Draft-only network execution plan validation. Phase 4.86D. No network, no writes, no DB.
	@if [ -z "$(EXECUTION_PLAN)" ] || [ -z "$(CHECKLIST)" ] || [ -z "$(RUNBOOK)" ] || [ -z "$(AUTH_FORM)" ] || [ -z "$(TARGET_SOURCE)" ] || [ -z "$(TARGET_ENGINE_FAMILY)" ] || [ -z "$(TARGET_SCOPE_TYPE)" ] || [ -z "$(TARGET_MATCH_ID)" ]; then \
		echo "ERROR: provide EXECUTION_PLAN=<path>, CHECKLIST=<path>, RUNBOOK=<path>, AUTH_FORM=<path>, TARGET_SOURCE=<src>, TARGET_ENGINE_FAMILY=titan_discovery, TARGET_SCOPE_TYPE=<type>, TARGET_MATCH_ID=<id>"; \
		exit 1; \
	fi
	@echo "Phase 4.86D: network execution plan validate (draft-only, local-only, no writes, no network, no DB)"
	$(NETWORK_EXECUTION_PLAN_NODE) scripts/ops/single_target_acquisition_network_execution_plan_validate.js \
		--execution-plan "$(EXECUTION_PLAN)" \
		--checklist "$(CHECKLIST)" \
		--runbook "$(RUNBOOK)" \
		--auth-form "$(AUTH_FORM)" \
		--target-source "$(TARGET_SOURCE)" \
		--target-engine-family "$(TARGET_ENGINE_FAMILY)" \
		--target-scope-type "$(TARGET_SCOPE_TYPE)" \
		--target-match-id "$(TARGET_MATCH_ID)" \
		$(if $(TARGET_LEAGUE),--target-league "$(TARGET_LEAGUE)") \
		$(if $(TARGET_SEASON),--target-season "$(TARGET_SEASON)") \
		$(if $(TARGET_DATE),--target-date "$(TARGET_DATE)") \
		--terms-approval "$(or $(TERMS_APPROVAL),no)" \
		--network-dry-run-authorization "$(or $(NETWORK_DRY_RUN_AUTHORIZATION),no)" \
		--allow-browser-runtime "$(or $(ALLOW_BROWSER_RUNTIME),no)" \
		--allow-proxy-runtime "$(or $(ALLOW_PROXY_RUNTIME),no)" \
		--allow-external-network "$(or $(ALLOW_EXTERNAL_NETWORK),no)" \
		--allow-staging-write "$(or $(ALLOW_STAGING_WRITE),no)" \
		--final-human-confirmation "$(or $(FINAL_HUMAN_CONFIRMATION),no)"

data-single-target-acquisition-network-execution-plan-commit: ## Blocked network execution plan gate. Remains not wired in Phase 4.86D.
	@echo "BLOCKED: single-target acquisition network dry-run execution is not wired in Phase 4.86D."
	@echo "  Even with CONFIRM_SINGLE_TARGET_ACQUISITION_NETWORK_EXECUTION_PLAN=1, this path remains blocked."
	@echo "  Phase 4.86D validates a draft only and does not authorize any network dry-run, staging write, or DB write."
	@exit 1

data-single-target-acquisition-network-approval-packet-preview: ## Preview-only human approval packet validation. Phase 4.87D. No network, no writes, no DB.
	@if [ -z "$(APPROVAL_PACKET)" ] || [ -z "$(EXECUTION_PLAN)" ] || [ -z "$(CHECKLIST)" ] || [ -z "$(RUNBOOK)" ] || [ -z "$(AUTH_FORM)" ] || [ -z "$(TARGET_SOURCE)" ] || [ -z "$(TARGET_ENGINE_FAMILY)" ] || [ -z "$(TARGET_SCOPE_TYPE)" ] || [ -z "$(TARGET_MATCH_ID)" ]; then \
		echo "ERROR: provide APPROVAL_PACKET=<path>, EXECUTION_PLAN=<path>, CHECKLIST=<path>, RUNBOOK=<path>, AUTH_FORM=<path>, TARGET_SOURCE=<src>, TARGET_ENGINE_FAMILY=titan_discovery, TARGET_SCOPE_TYPE=<type>, TARGET_MATCH_ID=<id>"; \
		exit 1; \
	fi
	@echo "Phase 4.87D: network approval packet preview (preview-only, local-only, no writes, no network, no DB)"
	$(NETWORK_APPROVAL_PACKET_NODE) scripts/ops/single_target_acquisition_network_approval_packet_preview.js \
		--approval-packet "$(APPROVAL_PACKET)" \
		--execution-plan "$(EXECUTION_PLAN)" \
		--checklist "$(CHECKLIST)" \
		--runbook "$(RUNBOOK)" \
		--auth-form "$(AUTH_FORM)" \
		--target-source "$(TARGET_SOURCE)" \
		--target-engine-family "$(TARGET_ENGINE_FAMILY)" \
		--target-scope-type "$(TARGET_SCOPE_TYPE)" \
		--target-match-id "$(TARGET_MATCH_ID)" \
		$(if $(TARGET_LEAGUE),--target-league "$(TARGET_LEAGUE)") \
		$(if $(TARGET_SEASON),--target-season "$(TARGET_SEASON)") \
		$(if $(TARGET_DATE),--target-date "$(TARGET_DATE)") \
		--terms-approval "$(or $(TERMS_APPROVAL),no)" \
		--network-dry-run-authorization "$(or $(NETWORK_DRY_RUN_AUTHORIZATION),no)" \
		--allow-browser-runtime "$(or $(ALLOW_BROWSER_RUNTIME),no)" \
		--allow-proxy-runtime "$(or $(ALLOW_PROXY_RUNTIME),no)" \
		--allow-external-network "$(or $(ALLOW_EXTERNAL_NETWORK),no)" \
		--allow-staging-write "$(or $(ALLOW_STAGING_WRITE),no)" \
		--final-human-confirmation "$(or $(FINAL_HUMAN_CONFIRMATION),no)"

data-single-target-acquisition-network-approval-packet-commit: ## Blocked network approval packet gate. Remains not wired in Phase 4.87D.
	@echo "BLOCKED: single-target acquisition network dry-run human approval packet execution is not wired in Phase 4.87D."
	@echo "  Even with CONFIRM_SINGLE_TARGET_ACQUISITION_NETWORK_APPROVAL_PACKET=1, this path remains blocked."
	@echo "  Phase 4.87D previews a packet only and does not authorize any network dry-run, staging write, approval packet write, or DB write."
	@exit 1

data-single-target-acquisition-network-user-input-closure-preview: ## Preview-only user input requirements closure validation. Phase 4.88D. No network, no writes, no DB.
	@if [ -z "$(INPUT_CLOSURE)" ] || [ -z "$(APPROVAL_PACKET)" ] || [ -z "$(EXECUTION_PLAN)" ] || [ -z "$(CHECKLIST)" ] || [ -z "$(RUNBOOK)" ] || [ -z "$(AUTH_FORM)" ] || [ -z "$(TARGET_SOURCE)" ] || [ -z "$(TARGET_ENGINE_FAMILY)" ] || [ -z "$(TARGET_SCOPE_TYPE)" ] || [ -z "$(TARGET_MATCH_ID)" ]; then \
		echo "ERROR: provide INPUT_CLOSURE=<path>, APPROVAL_PACKET=<path>, EXECUTION_PLAN=<path>, CHECKLIST=<path>, RUNBOOK=<path>, AUTH_FORM=<path>, TARGET_SOURCE=<src>, TARGET_ENGINE_FAMILY=titan_discovery, TARGET_SCOPE_TYPE=<type>, TARGET_MATCH_ID=<id>"; \
		exit 1; \
	fi
	@echo "Phase 4.88D: network user input requirements closure preview (preview-only, local-only, no writes, no network, no DB)"
	$(NETWORK_USER_INPUT_CLOSURE_NODE) scripts/ops/single_target_acquisition_network_user_input_requirements_closure.js \
		--input-closure "$(INPUT_CLOSURE)" \
		--approval-packet "$(APPROVAL_PACKET)" \
		--execution-plan "$(EXECUTION_PLAN)" \
		--checklist "$(CHECKLIST)" \
		--runbook "$(RUNBOOK)" \
		--auth-form "$(AUTH_FORM)" \
		--target-source "$(TARGET_SOURCE)" \
		--target-engine-family "$(TARGET_ENGINE_FAMILY)" \
		--target-scope-type "$(TARGET_SCOPE_TYPE)" \
		--target-match-id "$(TARGET_MATCH_ID)" \
		$(if $(TARGET_LEAGUE),--target-league "$(TARGET_LEAGUE)") \
		$(if $(TARGET_SEASON),--target-season "$(TARGET_SEASON)") \
		$(if $(TARGET_DATE),--target-date "$(TARGET_DATE)") \
		--terms-approval "$(or $(TERMS_APPROVAL),no)" \
		--network-dry-run-authorization "$(or $(NETWORK_DRY_RUN_AUTHORIZATION),no)" \
		--allow-browser-runtime "$(or $(ALLOW_BROWSER_RUNTIME),no)" \
		--allow-proxy-runtime "$(or $(ALLOW_PROXY_RUNTIME),no)" \
		--allow-external-network "$(or $(ALLOW_EXTERNAL_NETWORK),no)" \
		--allow-staging-write "$(or $(ALLOW_STAGING_WRITE),no)" \
		--final-human-confirmation "$(or $(FINAL_HUMAN_CONFIRMATION),no)"

data-single-target-acquisition-network-user-input-closure-commit: ## Blocked network user input requirements closure gate. Remains not wired in Phase 4.88D.
	@echo "BLOCKED: single-target acquisition network dry-run user input requirements closure execution is not wired in Phase 4.88D."
	@echo "  Even with CONFIRM_SINGLE_TARGET_ACQUISITION_NETWORK_USER_INPUT_CLOSURE=1, this path remains blocked."
	@echo "  Phase 4.88D previews required user inputs only and does not authorize any network dry-run, staging write, user input closure file write, or DB write."
	@exit 1

data-single-target-acquisition-network-blocked-final-preflight-summary: ## Preview-only blocked final preflight summary validation. Phase 4.89D. No network, no writes, no DB.
	@if [ -z "$(BLOCKED_SUMMARY)" ] || [ -z "$(INPUT_CLOSURE)" ] || [ -z "$(APPROVAL_PACKET)" ] || [ -z "$(EXECUTION_PLAN)" ] || [ -z "$(CHECKLIST)" ] || [ -z "$(RUNBOOK)" ] || [ -z "$(AUTH_FORM)" ] || [ -z "$(TARGET_SOURCE)" ] || [ -z "$(TARGET_ENGINE_FAMILY)" ] || [ -z "$(TARGET_SCOPE_TYPE)" ] || [ -z "$(TARGET_MATCH_ID)" ]; then \
		echo "ERROR: provide BLOCKED_SUMMARY=<path>, INPUT_CLOSURE=<path>, APPROVAL_PACKET=<path>, EXECUTION_PLAN=<path>, CHECKLIST=<path>, RUNBOOK=<path>, AUTH_FORM=<path>, TARGET_SOURCE=<src>, TARGET_ENGINE_FAMILY=titan_discovery, TARGET_SCOPE_TYPE=<type>, TARGET_MATCH_ID=<id>"; \
		exit 1; \
	fi
	@echo "Phase 4.89D: network blocked final preflight summary (preview-only, local-only, no writes, no network, no DB)"
	$(NETWORK_BLOCKED_PREFLIGHT_NODE) scripts/ops/single_target_acquisition_network_blocked_final_preflight_summary.js \
		--blocked-summary "$(BLOCKED_SUMMARY)" \
		--input-closure "$(INPUT_CLOSURE)" \
		--approval-packet "$(APPROVAL_PACKET)" \
		--execution-plan "$(EXECUTION_PLAN)" \
		--checklist "$(CHECKLIST)" \
		--runbook "$(RUNBOOK)" \
		--auth-form "$(AUTH_FORM)" \
		--target-source "$(TARGET_SOURCE)" \
		--target-engine-family "$(TARGET_ENGINE_FAMILY)" \
		--target-scope-type "$(TARGET_SCOPE_TYPE)" \
		--target-match-id "$(TARGET_MATCH_ID)" \
		$(if $(TARGET_LEAGUE),--target-league "$(TARGET_LEAGUE)") \
		$(if $(TARGET_SEASON),--target-season "$(TARGET_SEASON)") \
		$(if $(TARGET_DATE),--target-date "$(TARGET_DATE)") \
		--terms-approval "$(or $(TERMS_APPROVAL),no)" \
		--network-dry-run-authorization "$(or $(NETWORK_DRY_RUN_AUTHORIZATION),no)" \
		--allow-browser-runtime "$(or $(ALLOW_BROWSER_RUNTIME),no)" \
		--allow-proxy-runtime "$(or $(ALLOW_PROXY_RUNTIME),no)" \
		--allow-external-network "$(or $(ALLOW_EXTERNAL_NETWORK),no)" \
		--allow-staging-write "$(or $(ALLOW_STAGING_WRITE),no)" \
		--final-human-confirmation "$(or $(FINAL_HUMAN_CONFIRMATION),no)"

data-single-target-acquisition-network-blocked-final-preflight-commit: ## Blocked network blocked final preflight gate. Remains not wired in Phase 4.89D.
	@echo "BLOCKED: single-target acquisition network dry-run blocked final preflight summary execution is not wired in Phase 4.89D."
	@echo "  Even with CONFIRM_SINGLE_TARGET_ACQUISITION_NETWORK_BLOCKED_FINAL_PREFLIGHT=1, this path remains blocked."
	@echo "  Phase 4.89D previews blocked status only and does not authorize any network dry-run, staging write, blocked summary file write, or DB write."
	@exit 1

data-single-target-acquisition-network-real-parameter-intake-preview: ## Preview-only real-parameter intake template validation. Phase 4.90D. No network, no writes, no DB.
	@if [ -z "$(INTAKE)" ] || [ -z "$(BLOCKED_SUMMARY)" ]; then \
		echo "ERROR: provide INTAKE=<path> and BLOCKED_SUMMARY=<path>"; \
		exit 1; \
	fi
	@echo "Phase 4.90D: network real-parameter intake template (template-only, local-only, no writes, no network, no DB)"
	$(NETWORK_REAL_PARAMETER_INTAKE_NODE) scripts/ops/single_target_acquisition_network_real_parameter_intake.js \
		--intake "$(INTAKE)" \
		--blocked-summary "$(BLOCKED_SUMMARY)"

data-single-target-acquisition-network-real-parameter-intake-commit: ## Blocked network real-parameter intake gate. Remains not wired in Phase 4.90D.
	@echo "BLOCKED: single-target acquisition real-parameter intake execution is not wired in Phase 4.90D."
	@echo "  Even with CONFIRM_SINGLE_TARGET_ACQUISITION_NETWORK_REAL_PARAMETER_INTAKE=1, this path remains blocked."
	@echo "  Phase 4.90D previews the intake template only and does not authorize any network dry-run, staging write, real parameter intake file write, or DB write."
	@exit 1

data-single-target-acquisition-network-real-parameter-validation-closure-preview: ## Preview-only real-parameter intake validation closure. Phase 4.91D. No network, no writes, no DB.
	@if [ -z "$(VALIDATION_CLOSURE)" ] || [ -z "$(INTAKE)" ] || [ -z "$(BLOCKED_SUMMARY)" ]; then \
		echo "ERROR: provide VALIDATION_CLOSURE=<path>, INTAKE=<path>, and BLOCKED_SUMMARY=<path>"; \
		exit 1; \
	fi
	@echo "Phase 4.91D: network real-parameter intake validation closure (template-only, local-only, no writes, no network, no DB)"
	$(NETWORK_REAL_PARAMETER_VALIDATION_CLOSURE_NODE) scripts/ops/single_target_acquisition_network_real_parameter_intake_validation_closure.js \
		--validation-closure "$(VALIDATION_CLOSURE)" \
		--intake "$(INTAKE)" \
		--blocked-summary "$(BLOCKED_SUMMARY)"

data-single-target-acquisition-network-real-parameter-validation-closure-commit: ## Blocked network real-parameter validation closure gate. Remains not wired in Phase 4.91D.
	@echo "BLOCKED: single-target acquisition real-parameter intake validation closure execution is not wired in Phase 4.91D."
	@echo "  Even with CONFIRM_SINGLE_TARGET_ACQUISITION_NETWORK_REAL_PARAMETER_VALIDATION_CLOSURE=1, this path remains blocked."
	@echo "  Phase 4.91D previews the validation closure template only and does not authorize any network dry-run, staging write, validation closure file write, or DB write."
	@exit 1

data-single-target-acquisition-network-filled-intake-review-plan-preview: ## Preview-only filled-intake review plan. Phase 4.92D. No network, no writes, no DB.
	@if [ -z "$(REVIEW_PLAN)" ] || [ -z "$(INTAKE)" ] || [ -z "$(VALIDATION_CLOSURE)" ] || [ -z "$(BLOCKED_SUMMARY)" ]; then \
		echo "ERROR: provide REVIEW_PLAN=<path>, INTAKE=<path>, VALIDATION_CLOSURE=<path>, and BLOCKED_SUMMARY=<path>"; \
		exit 1; \
	fi
	@echo "Phase 4.92D: network filled-intake review plan (template-only, local-only, no writes, no network, no DB)"
	$(NETWORK_FILLED_INTAKE_REVIEW_PLAN_NODE) scripts/ops/single_target_acquisition_network_filled_intake_review_plan.js \
		--review-plan "$(REVIEW_PLAN)" \
		--intake "$(INTAKE)" \
		--validation-closure "$(VALIDATION_CLOSURE)" \
		--blocked-summary "$(BLOCKED_SUMMARY)"

data-single-target-acquisition-network-filled-intake-review-plan-commit: ## Blocked network filled-intake review plan gate. Remains not wired in Phase 4.92D.
	@echo "BLOCKED: single-target acquisition filled-intake review plan execution is not wired in Phase 4.92D."
	@echo "  Even with CONFIRM_SINGLE_TARGET_ACQUISITION_NETWORK_FILLED_INTAKE_REVIEW_PLAN=1, this path remains blocked."
	@echo "  Phase 4.92D previews the filled-intake review plan template only and does not authorize any network dry-run, staging write, filled-intake review file write, or DB write."
	@exit 1

data-single-target-acquisition-network-filled-intake-review-result-preview: ## Preview-only filled-intake review result. Phase 4.93D. No network, no writes, no DB.
	@if [ -z "$(REVIEW_RESULT)" ] || [ -z "$(REVIEW_PLAN)" ] || [ -z "$(INTAKE)" ] || [ -z "$(VALIDATION_CLOSURE)" ] || [ -z "$(BLOCKED_SUMMARY)" ]; then \
		echo "ERROR: provide REVIEW_RESULT=<path>, REVIEW_PLAN=<path>, INTAKE=<path>, VALIDATION_CLOSURE=<path>, and BLOCKED_SUMMARY=<path>"; \
		exit 1; \
	fi
	@echo "Phase 4.93D: network filled-intake review result (template-only, local-only, no writes, no network, no DB)"
	$(NETWORK_FILLED_INTAKE_REVIEW_RESULT_NODE) scripts/ops/single_target_acquisition_network_filled_intake_review_result.js \
		--review-result "$(REVIEW_RESULT)" \
		--review-plan "$(REVIEW_PLAN)" \
		--intake "$(INTAKE)" \
		--validation-closure "$(VALIDATION_CLOSURE)" \
		--blocked-summary "$(BLOCKED_SUMMARY)"

data-single-target-acquisition-network-filled-intake-review-result-commit: ## Blocked network filled-intake review result gate. Remains not wired in Phase 4.93D.
	@echo "BLOCKED: single-target acquisition filled-intake review result execution is not wired in Phase 4.93D."
	@echo "  Even with CONFIRM_SINGLE_TARGET_ACQUISITION_NETWORK_FILLED_INTAKE_REVIEW_RESULT=1, this path remains blocked."
	@echo "  Phase 4.93D previews the filled-intake review result template only and does not authorize any network dry-run, staging write, filled-intake review result file write, or DB write."
	@exit 1

data-finished-csv-dry-run: ## Run local finished CSV sample import preview. Requires SAMPLE_CSV.
	@if [ -z "$(SAMPLE_CSV)" ]; then \
		echo "ERROR: provide SAMPLE_CSV=<path>"; \
		exit 1; \
	fi
	@echo "Running safe local finished CSV dry-run: SAMPLE_CSV=$(SAMPLE_CSV)"
	$(COMPOSE_DEV) exec -T dev test -f "$(SAMPLE_CSV)"
	$(COMPOSE_DEV) exec -T dev node scripts/ops/finished_csv_local_dry_run.js --csv "$(SAMPLE_CSV)"

data-finished-csv-commit: ## Blocked finished CSV commit gate. Requires SAMPLE_CSV, CONFIRM_FINISHED_CSV_COMMIT=1.
	@if [ "$(CONFIRM_FINISHED_CSV_COMMIT)" != "1" ]; then \
		echo "BLOCKED: finished CSV commit requires CONFIRM_FINISHED_CSV_COMMIT=1 and is not wired in Phase 4.38."; \
		exit 1; \
	fi
	@echo "BLOCKED: finished CSV commit is not wired in Phase 4.38."
	@exit 1

data-finished-backfill-dry-run: ## Run finished match raw/L3/training backfill preflight. Requires MATCH_ID.
	@if [ -z "$(MATCH_ID)" ]; then \
		echo "ERROR: provide MATCH_ID=<id>"; \
		exit 1; \
	fi
	@echo "Running safe finished match backfill preflight: MATCH_ID=$(MATCH_ID)"
	@if [ -n "$(FIXTURE)" ]; then \
		$(COMPOSE_DEV) exec -T dev test -f "$(FIXTURE)"; \
		$(COMPOSE_DEV) exec -T dev node scripts/ops/finished_match_backfill_preflight.js --match-id "$(MATCH_ID)" --fixture "$(FIXTURE)"; \
	else \
		$(COMPOSE_DEV) exec -T dev node scripts/ops/finished_match_backfill_preflight.js --match-id "$(MATCH_ID)"; \
	fi

data-finished-backfill-commit: ## Blocked finished match backfill gate. Requires MATCH_ID, CONFIRM_FINISHED_BACKFILL=1.
	@if [ "$(CONFIRM_FINISHED_BACKFILL)" != "1" ]; then \
		echo "BLOCKED: finished match backfill requires CONFIRM_FINISHED_BACKFILL=1 and is not wired in Phase 4.40."; \
		exit 1; \
	fi
	@echo "BLOCKED: finished match backfill commit is not wired in Phase 4.40."
	@exit 1

data-raw-fixture-dry-run: ## Run raw fixture adapter dry-run. Requires MATCH_ID and FIXTURE.
	@if [ -z "$(MATCH_ID)" ] || [ -z "$(FIXTURE)" ]; then \
		echo "ERROR: provide MATCH_ID=<id> and FIXTURE=<path>"; \
		exit 1; \
	fi
	@echo "Running safe raw fixture adapter dry-run: MATCH_ID=$(MATCH_ID), FIXTURE=$(FIXTURE)"
	$(COMPOSE_DEV) exec -T dev test -f "$(FIXTURE)"
	@if [ "$(ALLOW_SYNTHETIC)" = "1" ]; then \
		$(COMPOSE_DEV) exec -T dev node scripts/ops/raw_fixture_adapter_dry_run.js --match-id "$(MATCH_ID)" --fixture "$(FIXTURE)" --allow-synthetic; \
	else \
		$(COMPOSE_DEV) exec -T dev node scripts/ops/raw_fixture_adapter_dry_run.js --match-id "$(MATCH_ID)" --fixture "$(FIXTURE)"; \
	fi

data-raw-fixture-commit: ## Blocked raw fixture adapter gate. Requires MATCH_ID, FIXTURE, CONFIRM_RAW_FIXTURE_COMMIT=1.
	@if [ "$(CONFIRM_RAW_FIXTURE_COMMIT)" != "1" ]; then \
		echo "BLOCKED: raw fixture commit requires CONFIRM_RAW_FIXTURE_COMMIT=1 and is not wired in Phase 4.41."; \
		exit 1; \
	fi
	@echo "BLOCKED: raw fixture adapter commit is not wired in Phase 4.41."
	@exit 1

data-synthetic-l3-dry-run: ## Run safe synthetic raw to L3 preflight. Requires MATCH_ID.
	@if [ -z "$(MATCH_ID)" ]; then \
		echo "ERROR: provide MATCH_ID=<id>"; \
		exit 1; \
	fi
	@echo "Running safe synthetic raw to L3 preflight: MATCH_ID=$(MATCH_ID)"
	$(COMPOSE_DEV) exec -T dev node scripts/ops/synthetic_l3_preflight.js --match-id "$(MATCH_ID)"

data-synthetic-l3-commit: ## Blocked synthetic L3 commit gate. Requires MATCH_ID, CONFIRM_SYNTHETIC_L3=1.
	@if [ "$(CONFIRM_SYNTHETIC_L3)" != "1" ]; then \
		echo "BLOCKED: synthetic L3 commit requires CONFIRM_SYNTHETIC_L3=1 and is not wired in Phase 4.44."; \
		exit 1; \
	fi
	@echo "BLOCKED: synthetic L3 commit is not wired in Phase 4.44."
	@exit 1

data-raw-dry-run: ## Run safe local raw_match_data ingest dry-run. Requires SAMPLE_RAW and MATCH_ID.
	@if [ -z "$(SAMPLE_RAW)" ] || [ -z "$(MATCH_ID)" ]; then \
		echo "ERROR: provide SAMPLE_RAW=<path> and MATCH_ID=<id>"; \
		exit 1; \
	fi
	@echo "Running safe local raw_match_data ingest dry-run: SAMPLE_RAW=$(SAMPLE_RAW), MATCH_ID=$(MATCH_ID)"
	$(COMPOSE_DEV) exec -T dev test -f "$(SAMPLE_RAW)"
	$(COMPOSE_DEV) exec -T dev node scripts/ops/raw_match_data_local_ingest.js --fixture "$(SAMPLE_RAW)" --match-id "$(MATCH_ID)"

data-raw-commit: ## Blocked raw_match_data commit gate. Requires SAMPLE_RAW, MATCH_ID, CONFIRM_RAW_COMMIT=1.
	@if [ "$(CONFIRM_RAW_COMMIT)" != "1" ]; then \
		echo "BLOCKED: raw_match_data commit requires CONFIRM_RAW_COMMIT=1 and is not wired in Phase 4.21."; \
		exit 1; \
	fi
	@if [ -z "$(SAMPLE_RAW)" ] || [ -z "$(MATCH_ID)" ]; then \
		echo "BLOCKED: provide SAMPLE_RAW=<path> and MATCH_ID=<id>; raw_match_data commit is not wired in Phase 4.21."; \
		exit 1; \
	fi
	@echo "BLOCKED: raw_match_data commit is not wired in Phase 4.21."
	@exit 1

data-network-dry-run: ## Blocked unless explicitly authorized. Does not run by default.
	@if [ "$(CONFIRM_NETWORK)" != "1" ]; then \
		echo "BLOCKED: NETWORK_DRY_RUN requires CONFIRM_NETWORK=1 plus LIMIT and SCOPE."; \
		echo "Read docs/DATA_HARVESTING_GUIDE.md."; \
		exit 1; \
	fi
	@if [ -z "$(LIMIT)" ] || [ -z "$(SCOPE)" ]; then \
		echo "BLOCKED: provide LIMIT=<n> and SCOPE=<league/season/date/match scope>."; \
		exit 1; \
	fi
	@echo "NETWORK_DRY_RUN authorized for SCOPE=$(SCOPE), LIMIT=$(LIMIT)."
	@echo "No default network command is wired in Phase 4.3. Create a runbook before execution."
	@exit 1

data-db-write-small: ## Blocked unless explicitly authorized. Requires --commit-capable runbook.
	@if [ "$(CONFIRM_DB_WRITE)" != "1" ]; then \
		echo "BLOCKED: DB_WRITE_SMALL requires CONFIRM_DB_WRITE=1."; \
		exit 1; \
	fi
	@if [ -z "$(LIMIT)" ] || [ -z "$(SCOPE)" ]; then \
		echo "BLOCKED: provide LIMIT=<n> and SCOPE=<league/season/date/match scope>."; \
		exit 1; \
	fi
	@echo "DB_WRITE_SMALL authorized for SCOPE=$(SCOPE), LIMIT=$(LIMIT)."
	@echo "No default DB write command is wired in Phase 4.3. Confirm backup, pre/post DB stats, and --commit before execution."
	@exit 1

data-harvest: ## Blocked bulk harvesting gate. Requires runbook and explicit authorization.
	@if [ "$(CONFIRM_BULK_HARVEST)" != "1" ]; then \
		echo "BLOCKED: BULK_HARVEST requires CONFIRM_BULK_HARVEST=1."; \
		exit 1; \
	fi
	@if [ -z "$(RUNBOOK)" ]; then \
		echo "BLOCKED: provide RUNBOOK=<path>."; \
		exit 1; \
	fi
	@echo "BULK_HARVEST authorization detected with RUNBOOK=$(RUNBOOK)."
	@echo "No bulk command is wired in Phase 4.3. Review runbook, backup, monitoring, and stop conditions first."
	@exit 1

data-risk-report: ## Print location of data entrypoint governance docs
	@echo "Data harvesting guide: docs/DATA_HARVESTING_GUIDE.md"
	@echo "Governance report: docs/_reports/DATA_ENTRYPOINT_GOVERNANCE_PHASE4_2.md"
	@echo "DB schema migration runbook: docs/_reports/DB_SCHEMA_MIGRATION_RUNBOOK_PHASE4_8.md"

data-schema-help: ## Show DB schema migration safety gate policy
	@echo "FootballPrediction DB schema migration is safety-gated."
	@echo ""
	@echo "Allowed by default:"
	@echo "  make data-schema-help"
	@echo "  make data-schema-status"
	@echo "  make data-schema-plan"
	@echo ""
	@echo "Blocked by default:"
	@echo "  make data-schema-migrate"
	@echo ""
	@echo "Future migration execution requires all of:"
	@echo "  CONFIRM_SCHEMA_MIGRATION=1"
	@echo "  BACKUP_CONFIRMED=1"
	@echo "  RUNBOOK=docs/_reports/DB_SCHEMA_MIGRATION_RUNBOOK_PHASE4_8.md"
	@echo ""
	@echo "Phase 4.9 does not wire migration execution. Read the runbook first."

data-schema-status: ## Read-only DB schema status check
	@echo "Checking DB schema status with read-only SQL..."
	$(COMPOSE_DEV) exec -T db sh -lc 'psql -U "$$POSTGRES_USER" -d "$$POSTGRES_DB" -c "\dt"'
	$(COMPOSE_DEV) exec -T db sh -lc 'psql -U "$$POSTGRES_USER" -d "$$POSTGRES_DB" -c "SELECT table_name FROM information_schema.tables WHERE table_schema = '\''public'\'' AND table_name IN ('\''bookmaker_odds_history'\'', '\''matches_oddsportal_mapping'\'', '\''l3_features'\'', '\''alembic_version'\'', '\''schema_migrations'\'', '\''knex_migrations'\'') ORDER BY table_name;"'
	$(COMPOSE_DEV) exec -T db sh -lc 'psql -U "$$POSTGRES_USER" -d "$$POSTGRES_DB" -c "SELECT '\''matches'\'' AS table_name, COUNT(*) AS rows FROM matches UNION ALL SELECT '\''raw_match_data'\'', COUNT(*) FROM raw_match_data UNION ALL SELECT '\''odds'\'', COUNT(*) FROM odds UNION ALL SELECT '\''match_features_training'\'', COUNT(*) FROM match_features_training UNION ALL SELECT '\''predictions'\'', COUNT(*) FROM predictions UNION ALL SELECT '\''league_config'\'', COUNT(*) FROM league_config UNION ALL SELECT '\''feature_registry'\'', COUNT(*) FROM feature_registry UNION ALL SELECT '\''data_collection_log'\'', COUNT(*) FROM data_collection_log;"'
	$(COMPOSE_DEV) exec -T db sh -lc 'psql -U "$$POSTGRES_USER" -d "$$POSTGRES_DB" -c "SELECT table_name, column_name, data_type FROM information_schema.columns WHERE table_schema = '\''public'\'' AND table_name IN ('\''matches'\'', '\''raw_match_data'\'', '\''odds'\'') ORDER BY table_name, ordinal_position;"'
	@echo "OK: read-only DB schema status check completed."

data-schema-plan: ## Print planned DB schema migration order without executing SQL
	@echo "Recommended DB schema migration order from docs/_reports/DB_SCHEMA_MIGRATION_RUNBOOK_PHASE4_8.md:"
	@echo "  database/migrations/V6.5__hardened_matches_schema.sql"
	@echo "  database/migrations/V6.6__hardened_l2_raw_storage.sql"
	@echo "  database/migrations/V12.2__add_matches_pipeline_status.sql"
	@echo "  database/migrations/V12.3__expand_matches_pipeline_status_for_recon.sql"
	@echo "  database/migrations/V12.4__create_matches_oddsportal_mapping.sql"
	@echo "  database/migrations/V12.5__create_bookmaker_odds_history.sql"
	@echo "  database/migrations/V12.6__allow_numeric_fotmob_ids_in_raw_match_data.sql"
	@echo "  database/migrations/V12.7__add_tactical_stats_to_matches.sql"
	@echo "  database/migrations/V12.8__add_alignment_meta_to_bookmaker_odds_history.sql"
	@echo "  database/migrations/V26.4__create_l3_features_table.sql"
	@echo "No SQL was executed."

data-schema-migrate: ## Blocked DB schema migration gate. Execution is not wired in Phase 4.9.
	@if [ "$(CONFIRM_SCHEMA_MIGRATION)" != "1" ]; then \
		echo "BLOCKED: schema migration requires CONFIRM_SCHEMA_MIGRATION=1."; \
		exit 1; \
	fi
	@if [ "$(BACKUP_CONFIRMED)" != "1" ]; then \
		echo "BLOCKED: schema migration requires BACKUP_CONFIRMED=1."; \
		exit 1; \
	fi
	@if [ "$(RUNBOOK)" != "docs/_reports/DB_SCHEMA_MIGRATION_RUNBOOK_PHASE4_8.md" ]; then \
		echo "BLOCKED: provide RUNBOOK=docs/_reports/DB_SCHEMA_MIGRATION_RUNBOOK_PHASE4_8.md."; \
		exit 1; \
	fi
	@echo "Phase 4.9 safety gate reached. Migration execution is not wired in this phase."
	@echo "No CREATE/ALTER/INSERT/UPDATE/DELETE was executed."
	@exit 1

# ============================================
# 监控命令
# ============================================
health: ## 检查服务健康状态
	@echo "$(BLUE)服务健康状态:$(NC)"
	@docker-compose ps

dashboard: ## 启动战神仪表盘
	docker-compose --profile dashboard up -d dashboard
