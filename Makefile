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
        data-finished-csv-dry-run data-finished-csv-commit \
        data-finished-backfill-dry-run data-finished-backfill-commit \
        data-raw-fixture-dry-run data-raw-fixture-commit \
        data-synthetic-l3-dry-run data-synthetic-l3-commit \
        data-synthetic-training-feature-dry-run data-synthetic-training-feature-commit \
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
	@echo "  make data-finished-csv-dry-run SAMPLE_CSV=<path>"
	@echo "  make data-finished-backfill-dry-run MATCH_ID=<id>"
	@echo "  make data-finished-backfill-dry-run MATCH_ID=<id> FIXTURE=<path>"
	@echo "  make data-raw-fixture-dry-run MATCH_ID=<id> FIXTURE=<path>"
	@echo "  make data-raw-fixture-dry-run MATCH_ID=<id> FIXTURE=<path> ALLOW_SYNTHETIC=1"
	@echo "  make data-synthetic-l3-dry-run MATCH_ID=<id>"
	@echo "  make data-synthetic-training-feature-dry-run MATCH_ID=<id>"
	@echo ""
	@echo "Requires explicit authorization:"
	@echo "  make data-raw-fixture-commit MATCH_ID=<id> FIXTURE=<path> CONFIRM_RAW_FIXTURE_COMMIT=1  # blocked in Phase 4.41"
	@echo "  make data-finished-backfill-commit MATCH_ID=<id> CONFIRM_FINISHED_BACKFILL=1  # blocked in Phase 4.40"
	@echo "  make data-synthetic-l3-commit MATCH_ID=<id> CONFIRM_SYNTHETIC_L3=1  # blocked in Phase 4.44"
	@echo "  make data-synthetic-training-feature-commit MATCH_ID=<id> CONFIRM_SYNTHETIC_TRAINING_FEATURE=1  # blocked in Phase 4.46"
	@echo "  make data-finished-csv-commit SAMPLE_CSV=<path> CONFIRM_FINISHED_CSV_COMMIT=1  # blocked in Phase 4.38"
	@echo "  make data-training-dataset-export CONFIRM_DATASET_EXPORT=1  # blocked in Phase 4.36"
	@echo "  make data-prediction-write-commit MATCH_ID=<id> CONFIRM_PREDICTION_WRITE=1  # blocked in Phase 4.32"
	@echo "  make data-training-feature-commit MATCH_ID=<id> CONFIRM_TRAINING_FEATURE=1  # blocked in Phase 4.30"
	@echo "  make data-training-commit CONFIRM_TRAINING=1  # blocked in Phase 4.29"
	@echo "  make data-prediction-commit CONFIRM_PREDICTION=1  # blocked in Phase 4.29"
	@echo "  make data-l3-write-commit SAMPLE_RAW=<path> MATCH_ID=<id> CONFIRM_L3_WRITE=1  # blocked in Phase 4.26"
	@echo "  make data-l3-commit SAMPLE_RAW=<path> MATCH_ID=<id> CONFIRM_L3_COMMIT=1  # blocked in Phase 4.24"
	@echo "  make data-raw-commit SAMPLE_RAW=<path> MATCH_ID=<id> CONFIRM_RAW_COMMIT=1  # blocked in Phase 4.21"
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
