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
        data-dataset-status data-raw-match-data-completeness-audit data-html-hydration-source-fidelity-live-compare data-raw-storage-strategy-revision-plan data-pageprops-v2-no-write-preview data-pageprops-v2-controlled-write-plan data-raw-match-data-versioned-schema-migration-preflight data-raw-match-data-versioned-schema-migration-execute data-raw-match-data-version-compatibility-audit data-pageprops-v2-single-target-controlled-write data-pageprops-v2-post-write-canonical-read-verification data-remaining-seeded-pageprops-v2-acquisition-preflight data-remaining-seeded-pageprops-v2-controlled-write data-all-seeded-pageprops-v2-canonical-read-verification data-pageprops-v2-raw-completeness-audit data-pageprops-v2-parser-boundary-leakage-plan data-large-scale-pageprops-v2-acquisition-strategy-plan data-large-scale-target-inventory-schema-readiness-audit data-single-league-small-batch-target-manifest-plan data-single-league-target-discovery-source-inventory-preflight data-single-league-small-batch-pageprops-v2-preflight data-single-league-pageprops-v2-controlled-write-plan data-single-league-pageprops-v2-controlled-write-execute data-controlled-matches-identity-seed-prerequisite-plan data-controlled-matches-identity-seed-execute data-post-seed-matches-identity-raw-write-readiness-audit data-renewed-pageprops-v2-raw-write-execute data-renewed-pageprops-v2-baseline-proposal-plan data-training-dataset-dry-run data-training-dataset-export \
        data-acquisition-engines data-acquisition-engine-audit \
        data-l1-discovery-preview data-l1-discovery-candidates-preview data-l1-discovery-candidates-network-preview data-l1-discovery-commit \
        data-l1-matches-seed-commit-plan data-l1-matches-seed-commit-authorization data-l1-matches-seed-commit-execution-preflight data-l1-matches-seed-commit-execute data-l1-matches-seed-commit \
        data-l2-raw-detail-preview data-l2-raw-detail-route-preview-plan data-l2-raw-match-data-ingest-plan data-l2-raw-match-data-ingest-authorization data-l2-raw-match-data-ingest-preflight data-l2-raw-match-data-write data-l2-remaining-raw-match-data-acquisition-plan data-l2-remaining-raw-match-data-acquisition-authorization data-l2-remaining-raw-match-data-acquisition-preflight data-l2-remaining-raw-match-data-write \
        data-fotmob-single-target-adapter-preflight data-fotmob-single-target-adapter-commit \
        data-fotmob-stdout-network-dry-run-authorization-packet-preview data-fotmob-stdout-network-dry-run-authorization-packet-commit \
        data-fotmob-stdout-network-dry-run-execution-plan-preview data-fotmob-stdout-network-dry-run-execution-plan-commit \
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
        data-single-target-acquisition-network-authorization-handoff-checklist-preview data-single-target-acquisition-network-authorization-handoff-checklist-commit \
        data-single-target-acquisition-network-authorization-decision-preview data-single-target-acquisition-network-authorization-decision-commit \
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
        data-risk-report data-schema-help data-schema-status data-schema-plan data-schema-migrate \
        ci-local ci-local-pr pr-body-check pr-merge-preflight pr-ready-check workflow-pr-check pr-post-merge-check

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
NETWORK_AUTHORIZATION_HANDOFF_CHECKLIST_NODE?=$(COMPOSE_DEV) exec -T dev node
NETWORK_AUTHORIZATION_DECISION_NODE?=$(COMPOSE_DEV) exec -T dev node
FOTMOB_SINGLE_TARGET_ADAPTER_NODE?=$(COMPOSE_DEV) exec -T dev node
FOTMOB_STDOUT_NETWORK_AUTH_PACKET_NODE?=$(COMPOSE_DEV) exec -T dev node
FOTMOB_STDOUT_NETWORK_EXECUTION_PLAN_NODE?=$(COMPOSE_DEV) exec -T dev node

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
# 本地 CI 入口
# ============================================
ci-local: ## 运行本地 CI 部分验证（静态检查为主，远程 CI 为最终权威）
	@echo "$(YELLOW)[Local CI] 运行本地部分验证...$(NC)"
	@echo "$(YELLOW)[Local CI] 远程 GitHub Actions 为最终权威。$(NC)"
	@echo "$(YELLOW)[Local CI] 不要将本地 CI 通过等同于远程 CI 通过。$(NC)"
	@GATEKEEPER_LOCAL_CI=1 GATEKEEPER_DIRECT_MODE=1 \
		GATEKEEPER_FAKE_CI=1 \
		bash scripts/devops/gatekeeper.sh --mode=pr || \
		(echo "$(YELLOW)[Local CI] 部分检查失败或跳过。远程 CI 为最终权威。$(NC)"; exit 0)

ci-local-pr: ## PR 前本地验证（同 ci-local）
	$(MAKE) ci-local

pr-merge-preflight: ## PR merge preflight evidence check (read-only, no merge)
	@if [ -z "$(PR)" ]; then \
		echo "ERROR: PR number required. Usage: make pr-merge-preflight PR=<number>"; \
		exit 1; \
	fi
	@python3 scripts/devops/pr_merge_preflight.py --pr $(PR)

pr-ready-check: ## PR ready-to-merge check: pr-body-check + pr-merge-preflight. Usage: make pr-ready-check PR=<number>
	@if [ -z "$(PR)" ]; then \
		echo "ERROR: PR number required. Usage: make pr-ready-check PR=<number>"; \
		exit 1; \
	fi
	@$(MAKE) pr-body-check PR=$(PR)
	@$(MAKE) pr-merge-preflight PR=$(PR)

pr-body-check: ## PR body + current Production Gate evidence check (read-only). Usage: make pr-body-check PR=<number>
	@if [ -z "$(PR)" ]; then \
		echo "ERROR: PR number required. Usage: make pr-body-check PR=<number>"; \
		exit 1; \
	fi
	@python3 scripts/devops/pr_body_check.py --pr $(PR)

workflow-pr-check: ## Workflow PR local validation: ruff check + format check + pytest. Usage: make workflow-pr-check FILES="<python_files>" TESTS="<test_files>"
	@if [ -z "$(FILES)" ]; then \
		echo "ERROR: FILES is required."; \
		echo "Usage: make workflow-pr-check FILES=\"scripts/devops/foo.py tests/unit/test_foo.py\" TESTS=\"tests/unit/test_foo.py\""; \
		echo "  FILES  — space-separated list of Python files to lint/format-check"; \
		echo "  TESTS  — space-separated list of test files/dirs for pytest"; \
		exit 1; \
	fi
	@if [ -z "$(TESTS)" ]; then \
		echo "ERROR: TESTS is required."; \
		echo "Usage: make workflow-pr-check FILES=\"scripts/devops/foo.py tests/unit/test_foo.py\" TESTS=\"tests/unit/test_foo.py\""; \
		echo "  FILES  — space-separated list of Python files to lint/format-check"; \
		echo "  TESTS  — space-separated list of test files/dirs for pytest"; \
		exit 1; \
	fi
	@echo "$(BLUE)[Workflow PR Check] Running ruff check...$(NC)"
	@$(COMPOSE_DEV) exec -T dev ruff check $(FILES)
	@echo "$(BLUE)[Workflow PR Check] Running ruff format --check...$(NC)"
	@$(COMPOSE_DEV) exec -T dev ruff format --check $(FILES)
	@echo "$(BLUE)[Workflow PR Check] Running pytest...$(NC)"
	@$(COMPOSE_DEV) exec -T dev pytest $(TESTS) -v
	@echo "$(GREEN)[Workflow PR Check] All checks PASSED$(NC)"

pr-post-merge-check: ## Post-merge check / cleanup gate. Usage: make pr-post-merge-check PR=<number> MERGE_COMMIT=<sha> BRANCH=<name> [CONFIRM_CLEANUP=1]
	@if [ -z "$(PR)" ]; then \
		echo "ERROR: PR number required. Usage: make pr-post-merge-check PR=<number> MERGE_COMMIT=<sha> BRANCH=<name>"; \
		exit 1; \
	fi
	@if [ -z "$(MERGE_COMMIT)" ]; then \
		echo "ERROR: MERGE_COMMIT required. Usage: make pr-post-merge-check PR=<number> MERGE_COMMIT=<sha> BRANCH=<name>"; \
		exit 1; \
	fi
	@if [ -z "$(BRANCH)" ]; then \
		echo "ERROR: BRANCH required. Usage: make pr-post-merge-check PR=<number> MERGE_COMMIT=<sha> BRANCH=<name>"; \
		exit 1; \
	fi
	@if [ "$(CONFIRM_CLEANUP)" = "1" ]; then \
		python3 scripts/devops/pr_post_merge_check.py --pr $(PR) --merge-commit $(MERGE_COMMIT) --branch $(BRANCH) --confirm-cleanup; \
	else \
		python3 scripts/devops/pr_post_merge_check.py --pr $(PR) --merge-commit $(MERGE_COMMIT) --branch $(BRANCH); \
	fi

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
	@echo "  make data-raw-match-data-completeness-audit SOURCE=fotmob EXPECTED_RAW_COUNT=10 EXPECTED_SEEDED_RAW_COUNT=8 ALLOW_NETWORK=no ALLOW_DB_WRITE=no PRINT_FULL_RAW_DATA=no SAVE_FULL_RAW_DATA=no  # Phase 5.21L2A SELECT-only completeness/source fidelity audit, layered by data_version/provenance, no parser/features/training/prediction"
	@echo "  make data-html-hydration-source-fidelity-live-compare SOURCE=fotmob ROUTE=html_hydration MATCH_ID=53_20252026_4830747 EXTERNAL_ID=4830747 HOME_TEAM=Auxerre AWAY_TEAM=Nice NETWORK_AUTHORIZATION=yes LIVE_COMPARE_AUTHORIZATION=yes ALLOW_DB_WRITE=no ALLOW_RAW_MATCH_DATA_WRITE=no ALLOW_MATCHES_WRITE=no ALLOW_PARSER_FEATURES=no ALLOW_TRAINING=no ALLOW_PREDICTION=no CONCURRENCY=1 RETRY=0 PRINT_BODY=no SAVE_BODY=no PRINT_FULL_JSON=no SAVE_FULL_JSON=no  # Phase 5.21L2B single-target live source fidelity compare, no DB/raw write, no parser/features/training/prediction"
	@echo "  make data-raw-storage-strategy-revision-plan SOURCE=fotmob CURRENT_VERSION=fotmob_html_hyd_v1 RECOMMENDED_VERSION=fotmob_pageprops_v2 RECOMMENDED_HASH_STRATEGY=stable_pageprops_payload_v1 ALLOW_NETWORK=no ALLOW_DB_WRITE=no ALLOW_MIGRATION=no ALLOW_PARSER_FEATURES=no ALLOW_TRAINING=no ALLOW_PREDICTION=no  # Phase 5.21L2C planning-only: recommends full pageProps raw v2, transformed payload derived/helper, no DB write/parser/features/training/prediction"
	@echo "  make data-pageprops-v2-no-write-preview SOURCE=fotmob ROUTE=html_hydration MATCH_ID=53_20252026_4830747 EXTERNAL_ID=4830747 HOME_TEAM=Auxerre AWAY_TEAM=Nice CANDIDATE_VERSION=fotmob_pageprops_v2 HASH_STRATEGY=stable_pageprops_payload_v1 NETWORK_AUTHORIZATION=yes PAGEPROPS_V2_PREVIEW_AUTHORIZATION=yes ALLOW_DB_WRITE=no ALLOW_RAW_MATCH_DATA_WRITE=no ALLOW_MATCHES_WRITE=no ALLOW_PARSER_FEATURES=no ALLOW_TRAINING=no ALLOW_PREDICTION=no CONCURRENCY=1 RETRY=0 PRINT_BODY=no SAVE_BODY=no PRINT_FULL_JSON=no SAVE_FULL_JSON=no  # Phase 5.21L2D single-target pageProps v2 no-write preview, candidate in memory only"
	@echo "  make data-pageprops-v2-controlled-write-plan SOURCE=fotmob CURRENT_VERSION=fotmob_html_hyd_v1 TARGET_VERSION=fotmob_pageprops_v2 HASH_STRATEGY=stable_pageprops_payload_v1 TARGET_MATCH_ID=53_20252026_4830747 TARGET_EXTERNAL_ID=4830747 ALLOW_NETWORK=no ALLOW_DB_WRITE=no ALLOW_MIGRATION=no ALLOW_RAW_MATCH_DATA_WRITE=no ALLOW_PARSER_FEATURES=no ALLOW_TRAINING=no ALLOW_PREDICTION=no  # Phase 5.21L2E planning-only: reviews raw_match_data schema/version coexistence, no DB write/migration/parser/features/training/prediction"
	@echo "  make data-raw-match-data-versioned-schema-migration-preflight SOURCE=fotmob TABLE=raw_match_data CURRENT_UNIQUE=match_id TARGET_UNIQUE=match_id,data_version TARGET_VERSION=fotmob_pageprops_v2 ALLOW_DB_WRITE=no ALLOW_MIGRATION=no ALLOW_RAW_MATCH_DATA_WRITE=no ALLOW_PARSER_FEATURES=no ALLOW_TRAINING=no ALLOW_PREDICTION=no  # Phase 5.21L2F planning/preflight-only: plans UNIQUE(match_id) -> UNIQUE(match_id,data_version), no DB write/ALTER/migration/parser/features/training/prediction"
	@echo "  make data-raw-match-data-versioned-schema-migration-execute SOURCE=fotmob TABLE=raw_match_data CURRENT_UNIQUE=match_id TARGET_UNIQUE=match_id,data_version CURRENT_CONSTRAINT=raw_match_data_match_id_key TARGET_CONSTRAINT=raw_match_data_match_id_data_version_key FINAL_SCHEMA_MIGRATION_CONFIRMATION=yes ALLOW_DB_WRITE=yes ALLOW_SCHEMA_MIGRATION=yes ALLOW_ALTER_TABLE=yes ALLOW_RAW_MATCH_DATA_WRITE=no ALLOW_MATCHES_WRITE=no ALLOW_PARSER_FEATURES=no ALLOW_TRAINING=no ALLOW_PREDICTION=no  # Phase 5.21L2G controlled schema-only migration execution, no raw row write/FotMob/parser/features/training/prediction"
	@echo "  make data-raw-match-data-version-compatibility-audit SOURCE=fotmob TABLE=raw_match_data PREFERRED_VERSION=fotmob_pageprops_v2 FALLBACK_VERSION=fotmob_html_hyd_v1 ALLOW_DB_WRITE=no ALLOW_RAW_MATCH_DATA_WRITE=no ALLOW_PARSER_FEATURES=no ALLOW_TRAINING=no ALLOW_PREDICTION=no  # Phase 5.21L2H SELECT-only version-aware compatibility audit; canonical selector prefers pageProps v2 then html_hyd_v1; no DB write/FotMob/parser/features/training/prediction"
	@echo "  make data-pageprops-v2-single-target-write-preflight SOURCE=fotmob ROUTE=html_hydration MATCH_ID=53_20252026_4830747 EXTERNAL_ID=4830747 HOME_TEAM=Auxerre AWAY_TEAM=Nice CANDIDATE_VERSION=fotmob_pageprops_v2 HASH_STRATEGY=stable_pageprops_payload_v1 PREVIOUS_PREVIEW_HASH=f892b403fe6e420a745888ab31e825843c4fd5387a7518ce61c4b456bb980acc NETWORK_AUTHORIZATION=yes PAGEPROPS_V2_WRITE_PREFLIGHT_AUTHORIZATION=yes ALLOW_DB_WRITE=no ALLOW_RAW_MATCH_DATA_WRITE=no ALLOW_MATCHES_WRITE=no ALLOW_PARSER_FEATURES=no ALLOW_TRAINING=no ALLOW_PREDICTION=no CONCURRENCY=1 RETRY=0 PRINT_BODY=no SAVE_BODY=no PRINT_FULL_JSON=no SAVE_FULL_JSON=no  # Phase 5.21L2I pageProps v2 single-target write preflight, no DB/raw write"
	@echo "  make data-pageprops-v2-single-target-controlled-write SOURCE=fotmob ROUTE=html_hydration MATCH_ID=53_20252026_4830747 EXTERNAL_ID=4830747 HOME_TEAM=Auxerre AWAY_TEAM=Nice CANDIDATE_VERSION=fotmob_pageprops_v2 HASH_STRATEGY=stable_pageprops_payload_v1 BASELINE_PAGEPROPS_HASH=f892b403fe6e420a745888ab31e825843c4fd5387a7518ce61c4b456bb980acc NETWORK_AUTHORIZATION=yes FINAL_DB_WRITE_CONFIRMATION=yes ALLOW_DB_WRITE=yes ALLOW_RAW_MATCH_DATA_WRITE=yes ALLOW_MATCHES_WRITE=no ALLOW_PARSER_FEATURES=no ALLOW_TRAINING=no ALLOW_PREDICTION=no CONCURRENCY=1 RETRY=0 PRINT_BODY=no SAVE_BODY=no PRINT_FULL_JSON=no SAVE_FULL_JSON=no  # Phase 5.21L2J pageProps v2 single-target controlled write, exactly one raw_match_data v2 row"
	@echo "  make data-pageprops-v2-post-write-canonical-read-verification SOURCE=fotmob TABLE=raw_match_data TARGET_MATCH_ID=53_20252026_4830747 TARGET_EXTERNAL_ID=4830747 EXPECTED_TARGET_VERSION=fotmob_pageprops_v2 FALLBACK_VERSION=fotmob_html_hyd_v1 EXPECTED_TARGET_HASH=f892b403fe6e420a745888ab31e825843c4fd5387a7518ce61c4b456bb980acc ALLOW_DB_WRITE=no ALLOW_NETWORK=no ALLOW_PARSER_FEATURES=no ALLOW_TRAINING=no ALLOW_PREDICTION=no  # Phase 5.21L2K SELECT-only canonical read verification, no DB write/network/parser/features/training"
	@echo "  make data-remaining-seeded-pageprops-v2-acquisition-preflight SOURCE=fotmob ROUTE=html_hydration TARGET_EXTERNAL_IDS=4830746,4830748,4830750,4830751,4830752,4830753,4830754 CANDIDATE_VERSION=fotmob_pageprops_v2 HASH_STRATEGY=stable_pageprops_payload_v1 NETWORK_AUTHORIZATION=yes PAGEPROPS_V2_REMAINING_PREFLIGHT_AUTHORIZATION=yes ALLOW_DB_WRITE=no ALLOW_RAW_MATCH_DATA_WRITE=no ALLOW_MATCHES_WRITE=no ALLOW_PARSER_FEATURES=no ALLOW_TRAINING=no ALLOW_PREDICTION=no CONCURRENCY=1 RETRY=0 PRINT_BODY=no SAVE_BODY=no PRINT_FULL_JSON=no SAVE_FULL_JSON=no  # Phase 5.21L2L remaining 7 pageProps v2 acquisition preflight, sequential live recapture, would_insert only, no DB/raw write/parser/features/training"
	@echo "  make data-remaining-seeded-pageprops-v2-controlled-write SOURCE=fotmob ROUTE=html_hydration BASELINE_HASHES='<json>' CANDIDATE_VERSION=fotmob_pageprops_v2 HASH_STRATEGY=stable_pageprops_payload_v1 NETWORK_AUTHORIZATION=yes FINAL_DB_WRITE_CONFIRMATION=yes ALLOW_DB_WRITE=yes ALLOW_RAW_MATCH_DATA_WRITE=yes ALLOW_MATCHES_WRITE=no ALLOW_PARSER_FEATURES=no ALLOW_TRAINING=no ALLOW_PREDICTION=no CONCURRENCY=1 RETRY=0 PRINT_BODY=no SAVE_BODY=no PRINT_FULL_JSON=no SAVE_FULL_JSON=no  # Phase 5.21L2M remaining 7 pageProps v2 controlled write, hash-gated sequential recapture, exactly 7 raw_match_data v2 rows, no parser/features/training/prediction"
	@echo "  make data-all-seeded-pageprops-v2-canonical-read-verification SOURCE=fotmob TABLE=raw_match_data TARGET_EXTERNAL_IDS=4830746,4830747,4830748,4830750,4830751,4830752,4830753,4830754 EXPECTED_TARGET_VERSION=fotmob_pageprops_v2 FALLBACK_VERSION=fotmob_html_hyd_v1 EXPECTED_HASHES='<json>' ALLOW_DB_WRITE=no ALLOW_NETWORK=no ALLOW_PARSER_FEATURES=no ALLOW_TRAINING=no ALLOW_PREDICTION=no  # Phase 5.21L2N SELECT-only canonical read verification for all 8 seeded matches, synthetic/unknown excluded, no DB write/network/parser/features/training"
	@echo "  make data-pageprops-v2-raw-completeness-audit SOURCE=fotmob TABLE=raw_match_data TARGET_EXTERNAL_IDS=4830746,4830747,4830748,4830750,4830751,4830752,4830753,4830754 DATA_VERSION=fotmob_pageprops_v2 ALLOW_DB_WRITE=no ALLOW_NETWORK=no ALLOW_PARSER_FEATURES=no ALLOW_TRAINING=no ALLOW_PREDICTION=no PRINT_FULL_RAW_DATA=no SAVE_FULL_RAW_DATA=no  # Phase 5.21L2O SELECT-only pageProps v2 raw inventory/completeness audit for all 8 seeded matches, local raw_match_data only, no DB write/network/parser/features/training"
	@echo "  make data-pageprops-v2-parser-boundary-leakage-plan SOURCE=fotmob RAW_VERSION=fotmob_pageprops_v2 PLANNING_SCOPE=parser-boundary-leakage-acquisition-odds-roadmap ALLOW_DB_WRITE=no ALLOW_NETWORK=no ALLOW_PARSER_IMPLEMENTATION=no ALLOW_FEATURE_EXTRACTION=no ALLOW_TRAINING=no ALLOW_PREDICTION=no  # Phase 5.21L2P planning-only parser boundary / leakage-safe planning with large-scale acquisition and odds raw roadmap"
	@echo "  make data-large-scale-pageprops-v2-acquisition-strategy-plan SOURCE=fotmob RAW_VERSION=fotmob_pageprops_v2 PLANNING_SCOPE=large-scale-acquisition-strategy ALLOW_DB_WRITE=no ALLOW_NETWORK=no ALLOW_RAW_ACQUISITION=no ALLOW_PARSER_IMPLEMENTATION=no ALLOW_FEATURE_EXTRACTION=no ALLOW_TRAINING=no ALLOW_PREDICTION=no  # Phase 5.21L2Q planning-only large-scale pageProps v2 acquisition strategy, no DB write/network/raw acquisition/parser/features/training"
	@echo "  make data-large-scale-target-inventory-schema-readiness-audit SOURCE=fotmob RAW_VERSION=fotmob_pageprops_v2 PLANNING_SCOPE=target-inventory-schema-readiness ALLOW_DB_WRITE=no ALLOW_NETWORK=no ALLOW_RAW_ACQUISITION=no ALLOW_SCHEMA_MIGRATION=no ALLOW_PARSER_IMPLEMENTATION=no ALLOW_FEATURE_EXTRACTION=no ALLOW_TRAINING=no ALLOW_PREDICTION=no  # Phase 5.21L2R planning/SELECT-only target inventory schema-readiness audit, no DB write/network/raw acquisition/schema migration/parser/features/training"
	@echo "  make data-single-league-small-batch-target-manifest-plan SOURCE=fotmob ROUTE=html_hydration RAW_VERSION=fotmob_pageprops_v2 HASH_STRATEGY=stable_pageprops_payload_v1 LEAGUE_ID=53 LEAGUE_NAME=\"Ligue 1\" SEASON=2025/2026 BATCH_ID=fotmob-pageprops-v2-ligue1-2025-2026-profile-001 BATCH_SIZE_POLICY=20-50 PLANNING_SCOPE=single-league-small-batch-target-manifest ALLOW_DB_WRITE=no ALLOW_NETWORK=no ALLOW_RAW_ACQUISITION=no ALLOW_SCHEMA_MIGRATION=no ALLOW_PARSER_IMPLEMENTATION=no ALLOW_FEATURE_EXTRACTION=no ALLOW_TRAINING=no ALLOW_PREDICTION=no  # Phase 5.21L2S planning/SELECT-only manifest proposal, no DB write/network/raw acquisition/schema migration/parser/features/training, does not invent target IDs"
	@echo "  make data-single-league-target-discovery-source-inventory-preflight SOURCE=fotmob LEAGUE_ID=53 LEAGUE_NAME=\"Ligue 1\" SEASON=2025/2026 ROUTE=source_inventory RAW_VERSION=fotmob_pageprops_v2 HASH_STRATEGY=stable_pageprops_payload_v1 BATCH_ID=fotmob-pageprops-v2-ligue1-2025-2026-profile-001 TARGET_COUNT_MIN=20 TARGET_COUNT_MAX=50 NETWORK_AUTHORIZATION=yes SOURCE_INVENTORY_AUTHORIZATION=yes ALLOW_DB_WRITE=no ALLOW_RAW_MATCH_DATA_WRITE=no ALLOW_MATCH_DETAIL_FETCH=no ALLOW_SCHEMA_MIGRATION=no ALLOW_PARSER_IMPLEMENTATION=no ALLOW_FEATURE_EXTRACTION=no ALLOW_TRAINING=no ALLOW_PREDICTION=no ALLOW_BROWSER_RUNTIME=no ALLOW_PROXY_RUNTIME=no CONCURRENCY=1 RETRY=0 PRINT_FULL_BODY=no SAVE_FULL_BODY=no PRINT_FULL_JSON=no SAVE_FULL_JSON=no  # Phase 5.21L2T0 authorized source inventory only, no DB/raw write, no match detail pageProps fetch, no parser/features/training, updates docs manifest proposal"
	@echo "  make data-single-league-small-batch-pageprops-v2-preflight MANIFEST=docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.proposal.json SOURCE=fotmob LEAGUE_ID=53 LEAGUE_NAME=\"Ligue 1\" SEASON=2025/2026 ROUTE=html_hydration RAW_VERSION=fotmob_pageprops_v2 HASH_STRATEGY=stable_pageprops_payload_v1 BATCH_ID=fotmob-pageprops-v2-ligue1-2025-2026-profile-001 TARGET_COUNT=50 NETWORK_AUTHORIZATION=yes MATCH_DETAIL_PREFLIGHT_AUTHORIZATION=yes ALLOW_DB_WRITE=no ALLOW_RAW_MATCH_DATA_WRITE=no ALLOW_CONTROLLED_WRITE=no ALLOW_SCHEMA_MIGRATION=no ALLOW_PARSER_IMPLEMENTATION=no ALLOW_FEATURE_EXTRACTION=no ALLOW_TRAINING=no ALLOW_PREDICTION=no ALLOW_BROWSER_RUNTIME=no ALLOW_PROXY_RUNTIME=no CONCURRENCY=1 RETRY=0 PRINT_FULL_BODY=no SAVE_FULL_BODY=no PRINT_FULL_JSON=no SAVE_FULL_JSON=no PRINT_FULL_PAGEPROPS=no SAVE_FULL_PAGEPROPS=no  # Phase 5.21L2T single-league small-batch no-write pageProps v2 preflight, manifest candidates only, updates manifest/report, no DB/raw write/parser/features/training"
	@echo "  make data-single-league-pageprops-v2-controlled-write-plan MANIFEST=docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.proposal.json SOURCE=fotmob LEAGUE_ID=53 LEAGUE_NAME=\"Ligue 1\" SEASON=2025/2026 ROUTE=html_hydration RAW_VERSION=fotmob_pageprops_v2 HASH_STRATEGY=stable_pageprops_payload_v1 BATCH_ID=fotmob-pageprops-v2-ligue1-2025-2026-profile-001 TARGET_COUNT=50 WRITE_PLANNING_AUTHORIZATION=yes ALLOW_DB_WRITE=no ALLOW_RAW_MATCH_DATA_WRITE=no ALLOW_CONTROLLED_WRITE=no ALLOW_NETWORK=no ALLOW_MATCH_DETAIL_FETCH=no ALLOW_SCHEMA_MIGRATION=no ALLOW_PARSER_IMPLEMENTATION=no ALLOW_FEATURE_EXTRACTION=no ALLOW_TRAINING=no ALLOW_PREDICTION=no  # Phase 5.21L2U controlled pageProps v2 write authorization/planning, SELECT-only, reads manifest baselines, audits eligibility, no DB write/network/match detail/parser/features/training"
	@echo "  make data-single-league-pageprops-v2-controlled-write-execute MANIFEST=docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.proposal.json SOURCE=fotmob LEAGUE_ID=53 LEAGUE_NAME=\"Ligue 1\" SEASON=2025/2026 ROUTE=html_hydration RAW_VERSION=fotmob_pageprops_v2 HASH_STRATEGY=stable_pageprops_payload_v1 BATCH_ID=fotmob-pageprops-v2-ligue1-2025-2026-profile-001 TARGET_COUNT=50 FINAL_DB_WRITE_CONFIRMATION=yes NETWORK_AUTHORIZATION=yes MATCH_DETAIL_RECAPTURE_AUTHORIZATION=yes ALLOW_DB_WRITE=yes ALLOW_RAW_MATCH_DATA_WRITE=yes ALLOW_CONTROLLED_WRITE=yes ALLOW_MATCHES_WRITE=no ALLOW_BOOKMAKER_ODDS_WRITE=no ALLOW_FEATURE_WRITE=no ALLOW_SCHEMA_MIGRATION=no ALLOW_PARSER_IMPLEMENTATION=no ALLOW_FEATURE_EXTRACTION=no ALLOW_TRAINING=no ALLOW_PREDICTION=no ALLOW_BROWSER_RUNTIME=no ALLOW_PROXY_RUNTIME=no CONCURRENCY=1 RETRY=0 PRINT_FULL_BODY=no SAVE_FULL_BODY=no PRINT_FULL_JSON=no SAVE_FULL_JSON=no PRINT_FULL_PAGEPROPS=no SAVE_FULL_PAGEPROPS=no  # Phase 5.21L2V controlled pageProps v2 write execution, FK gate before network/write, raw_match_data only, no matches/odds/features/training/predictions, no browser/proxy"
	@echo "  make data-controlled-matches-identity-seed-prerequisite-plan MANIFEST=docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.proposal.json SOURCE=fotmob LEAGUE_ID=53 LEAGUE_NAME=\"Ligue 1\" SEASON=2025/2026 BATCH_ID=fotmob-pageprops-v2-ligue1-2025-2026-profile-001 TARGET_COUNT=50 PLANNING_AUTHORIZATION=yes ALLOW_DB_WRITE=no ALLOW_MATCHES_WRITE=no ALLOW_RAW_MATCH_DATA_WRITE=no ALLOW_CONTROLLED_WRITE=no ALLOW_NETWORK=no ALLOW_MATCH_DETAIL_FETCH=no ALLOW_SCHEMA_MIGRATION=no ALLOW_PARSER_IMPLEMENTATION=no ALLOW_FEATURE_EXTRACTION=no ALLOW_TRAINING=no ALLOW_PREDICTION=no  # Phase 5.21L2V0 controlled matches identity seed prerequisite planning, SELECT-only, no DB/matches/raw write, no network/parser/features/training"
	@echo "  make data-controlled-matches-identity-seed-execute MANIFEST=docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.proposal.json SOURCE=fotmob LEAGUE_ID=53 LEAGUE_NAME=\"Ligue 1\" SEASON=2025/2026 BATCH_ID=fotmob-pageprops-v2-ligue1-2025-2026-profile-001 TARGET_COUNT=50 FINAL_DB_WRITE_CONFIRMATION=yes ALLOW_DB_WRITE=yes ALLOW_MATCHES_WRITE=yes ALLOW_RAW_MATCH_DATA_WRITE=no ALLOW_BOOKMAKER_ODDS_WRITE=no ALLOW_FEATURE_WRITE=no ALLOW_NETWORK=no ALLOW_MATCH_DETAIL_FETCH=no ALLOW_CONTROLLED_RAW_WRITE=no ALLOW_SCHEMA_MIGRATION=no ALLOW_PARSER_IMPLEMENTATION=no ALLOW_FEATURE_EXTRACTION=no ALLOW_TRAINING=no ALLOW_PREDICTION=no  # Phase 5.21L2V1 controlled matches identity seed execution, writes matches only, no raw_match_data/network/parser/features/training; raw write retry still requires separate authorization"
	@echo "  make data-post-seed-matches-identity-raw-write-readiness-audit MANIFEST=docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.proposal.json SOURCE=fotmob LEAGUE_ID=53 LEAGUE_NAME=\"Ligue 1\" SEASON=2025/2026 BATCH_ID=fotmob-pageprops-v2-ligue1-2025-2026-profile-001 TARGET_COUNT=50 READINESS_AUDIT_AUTHORIZATION=yes ALLOW_DB_WRITE=no ALLOW_MATCHES_WRITE=no ALLOW_RAW_MATCH_DATA_WRITE=no ALLOW_CONTROLLED_WRITE=no ALLOW_NETWORK=no ALLOW_MATCH_DETAIL_FETCH=no ALLOW_SCHEMA_MIGRATION=no ALLOW_PARSER_IMPLEMENTATION=no ALLOW_FEATURE_EXTRACTION=no ALLOW_TRAINING=no ALLOW_PREDICTION=no  # Phase 5.21L2V2 SELECT-only post-seed readiness audit, verifies matches/FK/no v2 rows, no DB write/network/parser/features/training"
	@echo "  make data-renewed-pageprops-v2-raw-write-execute MANIFEST=docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.proposal.json SOURCE=fotmob LEAGUE_ID=53 LEAGUE_NAME=\"Ligue 1\" SEASON=2025/2026 ROUTE=html_hydration RAW_VERSION=fotmob_pageprops_v2 HASH_STRATEGY=stable_pageprops_payload_v1 BATCH_ID=fotmob-pageprops-v2-ligue1-2025-2026-profile-001 TARGET_COUNT=50 RENEWED_RAW_WRITE_AUTHORIZATION=yes FINAL_DB_WRITE_CONFIRMATION=yes NETWORK_AUTHORIZATION=yes MATCH_DETAIL_RECAPTURE_AUTHORIZATION=yes ALLOW_DB_WRITE=yes ALLOW_RAW_MATCH_DATA_WRITE=yes ALLOW_CONTROLLED_WRITE=yes ALLOW_MATCHES_WRITE=no ALLOW_BOOKMAKER_ODDS_WRITE=no ALLOW_FEATURE_WRITE=no ALLOW_SCHEMA_MIGRATION=no ALLOW_PARSER_IMPLEMENTATION=no ALLOW_FEATURE_EXTRACTION=no ALLOW_TRAINING=no ALLOW_PREDICTION=no ALLOW_BROWSER_RUNTIME=no ALLOW_PROXY_RUNTIME=no CONCURRENCY=1 RETRY=0 PRINT_FULL_BODY=no SAVE_FULL_BODY=no PRINT_FULL_JSON=no SAVE_FULL_JSON=no PRINT_FULL_PAGEPROPS=no SAVE_FULL_PAGEPROPS=no REQUEST_DELAY_MS=750  # Phase 5.21L2V3 renewed controlled raw_match_data pageProps v2 write, post-seed FK-ready retry only"
	@echo "  make data-renewed-pageprops-v2-baseline-proposal-plan MANIFEST=docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.proposal.json PROPOSAL_OUTPUT=docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.renewed_baseline_proposal.phase521l2v3c.json SOURCE=fotmob LEAGUE_ID=53 LEAGUE_NAME=\"Ligue 1\" SEASON=2025/2026 ROUTE=html_hydration RAW_VERSION=fotmob_pageprops_v2 HASH_STRATEGY=stable_pageprops_payload_v1 BATCH_ID=fotmob-pageprops-v2-ligue1-2025-2026-profile-001 TARGET_COUNT=50 PLANNING_AUTHORIZATION=yes NETWORK_AUTHORIZATION=yes MATCH_DETAIL_RECAPTURE_AUTHORIZATION=yes ALLOW_DB_WRITE=no ALLOW_RAW_MATCH_DATA_WRITE=no ALLOW_CONTROLLED_WRITE=no ALLOW_MATCHES_WRITE=no ALLOW_BOOKMAKER_ODDS_WRITE=no ALLOW_FEATURE_WRITE=no ALLOW_SCHEMA_MIGRATION=no ALLOW_PARSER_IMPLEMENTATION=no ALLOW_FEATURE_EXTRACTION=no ALLOW_TRAINING=no ALLOW_PREDICTION=no ALLOW_BROWSER_RUNTIME=no ALLOW_PROXY_RUNTIME=no PRINT_FULL_BODY=no SAVE_FULL_BODY=no PRINT_FULL_JSON=no SAVE_FULL_JSON=no PRINT_FULL_PAGEPROPS=no SAVE_FULL_PAGEPROPS=no REPEAT_COUNT=2 REQUEST_DELAY_MS=750  # Phase 5.21L2V3C no-write renewed baseline proposal, hashes are review-only and not accepted baselines"
	@echo "  make data-pageprops-v2-target-identity-reconciliation-plan MANIFEST=docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.proposal.json RENEWED_PROPOSAL=docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.renewed_baseline_proposal.phase521l2v3c.json SOURCE=fotmob LEAGUE_ID=53 LEAGUE_NAME=\"Ligue 1\" SEASON=2025/2026 ROUTE=html_hydration RAW_VERSION=fotmob_pageprops_v2 HASH_STRATEGY=stable_pageprops_payload_v1 BATCH_ID=fotmob-pageprops-v2-ligue1-2025-2026-profile-001 TARGET_COUNT=50 PLANNING_AUTHORIZATION=yes TARGET_IDENTITY_RECONCILIATION_AUTHORIZATION=yes NETWORK_AUTHORIZATION=yes MATCH_DETAIL_RECAPTURE_AUTHORIZATION=yes ALLOW_DB_WRITE=no ALLOW_RAW_MATCH_DATA_WRITE=no ALLOW_CONTROLLED_WRITE=no ALLOW_MATCHES_WRITE=no ALLOW_BOOKMAKER_ODDS_WRITE=no ALLOW_FEATURE_WRITE=no ALLOW_SCHEMA_MIGRATION=no ALLOW_PARSER_IMPLEMENTATION=no ALLOW_FEATURE_EXTRACTION=no ALLOW_TRAINING=no ALLOW_PREDICTION=no ALLOW_BROWSER_RUNTIME=no ALLOW_PROXY_RUNTIME=no PRINT_FULL_BODY=no SAVE_FULL_BODY=no PRINT_FULL_JSON=no SAVE_FULL_JSON=no PRINT_FULL_PAGEPROPS=no SAVE_FULL_PAGEPROPS=no RETRY=0 REQUEST_DELAY_MS=750  # Phase 5.21L2V3D no-write target identity reconciliation planning, mismatch blocks baseline acceptance/raw write retry"
	@echo "  make data-training-dataset-dry-run"
	@echo "  make data-acquisition-engines"
	@echo "  make data-acquisition-engine-audit"
	@echo "  make data-l1-discovery-preview SOURCE=fotmob SCOPE=<config_only_preview|league_season_date|league_season_window_preview> ...  # Phase 5.05L1 preview-only, no network/browser/proxy/DB, no titan_discovery/DiscoveryService.discover/FixtureRepository.persist"
	@echo "  make data-l1-discovery-candidates-preview SOURCE=fotmob SCOPE=controlled_candidates_preview LEAGUE_ID=<id> SEASON=<season> DATE=<yyyy-mm-dd> NETWORK_AUTHORIZATION=no  # Phase 5.05L1 candidates preview, no external network/browser/proxy/DB, no matches/raw writes"
	@echo "  make data-l1-discovery-candidates-network-preview SOURCE=fotmob SCOPE=controlled_candidates_preview LEAGUE_ID=<id> SEASON=<season> DATE=<yyyy-mm-dd> CONCURRENCY=1 MAX_TARGETS<=10 NETWORK_AUTHORIZATION=yes ALLOW_BROWSER_RUNTIME=no ALLOW_PROXY_RUNTIME=no ALLOW_DB_WRITE=no  # Phase 5.05L1 controlled external network candidates preview only"
	@echo "  make data-l1-matches-seed-commit-plan SOURCE=fotmob SCOPE=<league_season_date|controlled_candidates_preview> LEAGUE_ID=<id> SEASON=<season> DATE=<yyyy-mm-dd> CANDIDATE_COUNT=<n> MAX_SEED_ROWS<=10 COMMIT=no  # Phase 5.06L1 planning-only, no network/DB/matches/raw writes"
	@echo "  make data-l1-matches-seed-commit-authorization SOURCE=fotmob SCOPE=<league_season_date|controlled_candidates_preview> LEAGUE_ID=<id> SEASON=<season> DATE=<yyyy-mm-dd> CANDIDATE_COUNT=<n> MAX_SEED_ROWS<=10 USER_AUTHORIZED_MATCHES_SEED_COMMIT=yes ALLOW_MATCHES_WRITE_NEXT_PHASE=yes ALLOW_DB_WRITE_NOW=no ALLOW_RAW_MATCH_DATA_WRITE=no ALLOW_TRAINING=no ALLOW_PREDICTION=no FINAL_HUMAN_CONFIRMATION=yes  # Phase 5.07L1 authorization-only, stdout-only, no DB/matches/raw writes"
	@echo "  make data-l1-matches-seed-commit-execution-preflight SOURCE=fotmob SCOPE=<league_season_date|controlled_candidates_preview> LEAGUE_ID=<id> SEASON=<season> DATE=<yyyy-mm-dd> CANDIDATE_COUNT=<n> MAX_SEED_ROWS<=10 FINAL_DB_WRITE_CONFIRMATION=no ALLOW_DB_WRITE_NOW=no ALLOW_MATCHES_WRITE_NOW=no ALLOW_RAW_MATCH_DATA_WRITE=no ALLOW_TRAINING=no ALLOW_PREDICTION=no  # Phase 5.08L1 execution preflight only, safe exact candidates + SELECT-only affected matches, no DB writes"
	@echo "  make data-l1-matches-seed-commit-execute SOURCE=fotmob SCOPE=league_season_date LEAGUE_ID=53 SEASON=2025/2026 DATE=2026-05-10 CANDIDATE_COUNT=8 CONTAINS_TARGET_MATCH_ID=4830746 CONTAINS_TARGET_LABEL=\"Angers vs Strasbourg\" MAX_SEED_ROWS=10 FINAL_DB_WRITE_CONFIRMATION=yes ALLOW_DB_WRITE_NOW=yes ALLOW_MATCHES_WRITE_NOW=yes ALLOW_RAW_MATCH_DATA_WRITE=no ALLOW_TRAINING=no ALLOW_PREDICTION=no  # Phase 5.09L1 exact controlled execution only, matches-only transaction"
	@echo ""
	@echo "Preferred L1 safe workflow:"
	@echo "  make data-l1-discovery-candidates-network-preview ...  # controlled external candidates preview"
	@echo "  make data-l1-matches-seed-commit-plan ...              # planning only"
	@echo "  make data-l1-matches-seed-commit-authorization ...     # authorization only"
	@echo "  make data-l1-matches-seed-commit-execution-preflight ... # exact candidates + SELECT-only preview"
	@echo "  make data-l1-matches-seed-commit-execute ...           # exact matches-only controlled execution"
	@echo "  Legacy data entrypoints are deprecated for agents and require explicit human/admin authorization."
	@echo "  Do not run titan_discovery / data-harvest / dev-harvest for agent workflows."
	@echo ""
	@echo "L2 raw JSON acquisition is under planning:"
	@echo "  Do not run legacy raw backfill / production harvest as an agent workflow."
	@echo "  Do not write raw_match_data until a separate controlled authorization/preflight phase."
	@echo "  make data-l2-raw-detail-route-preview-plan  # Phase 5.12L2B route selector plan only, no network"
	@echo "  make data-l2-raw-detail-preview SOURCE=fotmob MATCH_ID=53_20252026_4830746 EXTERNAL_ID=4830746 HOME_TEAM=Angers AWAY_TEAM=Strasbourg ROUTE=auto NETWORK_AUTHORIZATION=yes LIVE_PREVIEW_AUTHORIZATION=no ALLOW_DB_WRITE=no ALLOW_RAW_MATCH_DATA_WRITE=no ALLOW_BROWSER_RUNTIME=no ALLOW_PROXY_RUNTIME=no CONCURRENCY=1 RETRY=0 PRINT_BODY=no SAVE_BODY=no  # route selector preview; live remains blocked without future authorization"
	@echo "  make data-l2-raw-match-data-ingest-plan SOURCE=fotmob ROUTE=html_hydration MATCH_ID=53_20252026_4830746 EXTERNAL_ID=4830746 HOME_TEAM=Angers AWAY_TEAM=Strasbourg PREVIEW_BODY_SHA256=<sha256> PREVIEW_BODY_BYTE_LENGTH=<bytes> HYDRATION_PARSE_OK=yes LOOKS_LIKE_VALID_MATCH_DETAIL=yes ALLOW_DB_WRITE=no ALLOW_RAW_MATCH_DATA_WRITE=no ALLOW_MATCHES_WRITE=no ALLOW_TRAINING=no ALLOW_PREDICTION=no  # Phase 5.13L2 planning-only, no network/DB/raw write"
	@echo "  make data-l2-raw-match-data-ingest-authorization SOURCE=fotmob ROUTE=html_hydration MATCH_ID=53_20252026_4830746 EXTERNAL_ID=4830746 HOME_TEAM=Angers AWAY_TEAM=Strasbourg DATA_VERSION=fotmob_html_hyd_v1 PREVIEW_BODY_SHA256=<sha256> HYDRATION_PARSE_OK=yes LOOKS_LIKE_VALID_MATCH_DETAIL=yes USER_AUTHORIZED_RAW_MATCH_DATA_INGEST=yes ALLOW_RAW_MATCH_DATA_WRITE_NEXT_PHASE=yes ALLOW_DB_WRITE_NOW=no ALLOW_RAW_MATCH_DATA_WRITE_NOW=no ALLOW_MATCHES_WRITE=no ALLOW_TRAINING=no ALLOW_PREDICTION=no FINAL_HUMAN_CONFIRMATION=yes  # Phase 5.14L2 authorization-only, no network/DB/raw write"
	@echo "  make data-l2-raw-match-data-ingest-preflight SOURCE=fotmob ROUTE=html_hydration MATCH_ID=53_20252026_4830746 EXTERNAL_ID=4830746 HOME_TEAM=Angers AWAY_TEAM=Strasbourg DATA_VERSION=fotmob_html_hyd_v1 NETWORK_AUTHORIZATION=yes LIVE_PREVIEW_AUTHORIZATION=yes ALLOW_DB_WRITE=no ALLOW_RAW_MATCH_DATA_WRITE=no ALLOW_MATCHES_WRITE=no ALLOW_TRAINING=no ALLOW_PREDICTION=no CONCURRENCY=1 RETRY=0 PRINT_BODY=no SAVE_BODY=no  # Phase 5.15L2 preflight-only: recapture exact payload/hash and output would_insert/update/skip, no DB/raw write"
	@echo "  make data-l2-raw-match-data-write SOURCE=fotmob ROUTE=html_hydration MATCH_ID=53_20252026_4830746 EXTERNAL_ID=4830746 HOME_TEAM=Angers AWAY_TEAM=Strasbourg DATA_VERSION=fotmob_html_hyd_v1 BASELINE_RAW_DATA_HASH=d40f757adccf5be96d107188196efa905b6b573b62d7b4428014d7ce4f39a1f6 NETWORK_AUTHORIZATION=yes LIVE_PREVIEW_AUTHORIZATION=yes FINAL_DB_WRITE_CONFIRMATION=yes ALLOW_DB_WRITE=yes ALLOW_RAW_MATCH_DATA_WRITE=yes ALLOW_MATCHES_WRITE=no ALLOW_TRAINING=no ALLOW_PREDICTION=no CONCURRENCY=1 RETRY=0 PRINT_BODY=no SAVE_BODY=no  # Phase 5.16L2 controlled single-target raw_match_data write"
	@echo "  make data-l2-remaining-raw-match-data-acquisition-plan SOURCE=fotmob LEAGUE_ID=53 SEASON=2025/2026 DATE=2026-05-10 EXPECTED_SEEDED_COUNT=8 EXPECTED_EXISTING_RAW_COUNT=1 EXPECTED_MISSING_RAW_COUNT=7 ALLOW_NETWORK=no ALLOW_DB_WRITE=no ALLOW_RAW_MATCH_DATA_WRITE=no ALLOW_MATCHES_WRITE=no ALLOW_TRAINING=no ALLOW_PREDICTION=no  # Phase 5.17L2 planning-only: remaining seeded raw acquisition scope"
	@echo "  make data-l2-remaining-raw-match-data-acquisition-authorization SOURCE=fotmob LEAGUE_ID=53 SEASON=2025/2026 DATE=2026-05-10 ROUTE=html_hydration EXPECTED_SEEDED_COUNT=8 EXPECTED_EXISTING_RAW_COUNT=1 EXPECTED_MISSING_RAW_COUNT=7 REMAINING_EXTERNAL_IDS=4830747,4830748,4830750,4830751,4830752,4830753,4830754 USER_AUTHORIZED_REMAINING_RAW_ACQUISITION=yes ALLOW_NETWORK_NEXT_PHASE=yes ALLOW_RAW_MATCH_DATA_WRITE_FUTURE_PHASE=yes ALLOW_NETWORK_THIS_PHASE=no ALLOW_DB_WRITE_THIS_PHASE=no ALLOW_RAW_MATCH_DATA_WRITE_THIS_PHASE=no ALLOW_MATCHES_WRITE=no ALLOW_PARSER_FEATURES=no ALLOW_TRAINING=no ALLOW_PREDICTION=no FINAL_HUMAN_CONFIRMATION=yes  # Phase 5.18L2 authorization-only: remaining 7 targets authorized for future preflight"
	@echo "  make data-l2-remaining-raw-match-data-acquisition-preflight SOURCE=fotmob LEAGUE_ID=53 SEASON=2025/2026 DATE=2026-05-10 ROUTE=html_hydration REMAINING_EXTERNAL_IDS=4830747,4830748,4830750,4830751,4830752,4830753,4830754 EXPECTED_TARGET_COUNT=7 NETWORK_AUTHORIZATION=yes LIVE_PREVIEW_AUTHORIZATION=yes ALLOW_DB_WRITE=no ALLOW_RAW_MATCH_DATA_WRITE=no ALLOW_MATCHES_WRITE=no ALLOW_PARSER_FEATURES=no ALLOW_TRAINING=no ALLOW_PREDICTION=no CONCURRENCY=1 RETRY=0 PRINT_BODY=no SAVE_BODY=no  # Phase 5.19L2 preflight-only: recaptures 7 payloads, computes hashes, outputs would_insert/update/skip, no DB write"
	@echo "  make data-l2-remaining-raw-match-data-write SOURCE=fotmob LEAGUE_ID=53 SEASON=2025/2026 DATE=2026-05-10 ROUTE=html_hydration REMAINING_EXTERNAL_IDS=4830747,4830748,4830750,4830751,4830752,4830753,4830754 EXPECTED_TARGET_COUNT=7 HASH_STRATEGY=stable_raw_payload_v1 BASELINE_RAW_DATA_HASHES=4830747:8dfc7faaf236ee9f8090301cce9dede32a11ed5b66f2a89e1b3324064f788b25,4830748:538fc2c33281f65d56f5fc004378e5933c0d3bbabc81d8e640bcb7abb4ad9bc3,4830750:c04915c0e972566f56bcb88a004f9e7e282777f9ca512c626a6acd4bd05e7304,4830751:5c603f83265887f223776941dde430e7abc8b8b9a9577d649cfd149339ffbd37,4830752:241e21be67a3f854d3320bbe86857a19c4bc357b6647d8b798df9b2dec6f56d6,4830753:358466958ec7b60b4dfa5e847537391b85153a564300804636497dd683311567,4830754:3a0832dc6bc16892491c11905ad8ab2fd80e4b29ea2f0aaa71d5659e57785c30 DATA_VERSION=fotmob_html_hyd_v1 NETWORK_AUTHORIZATION=yes LIVE_PREVIEW_AUTHORIZATION=yes FINAL_DB_WRITE_CONFIRMATION=yes ALLOW_DB_WRITE=yes ALLOW_RAW_MATCH_DATA_WRITE=yes ALLOW_MATCHES_WRITE=no ALLOW_PARSER_FEATURES=no ALLOW_TRAINING=no ALLOW_PREDICTION=no CONCURRENCY=1 RETRY=0 PRINT_BODY=no SAVE_BODY=no  # Phase 5.20L2F controlled remaining raw_match_data write using stable baselines"
	@echo "  L2 raw detail preview is preview-only: no raw_match_data write, no DB write, no browser/proxy, no full body print/save."
	@echo "  L2 raw_match_data ingest authorization is authorization-only in Phase 5.14L2: future write requires preflight + final DB-write confirmation, and raw_match_data write remains blocked this phase."
	@echo "  L2 raw_match_data ingest preflight recomputes exact payload/hash and outputs would_insert/update/skip; it does not write raw_match_data. Future write requires final DB-write confirmation."
	@echo "  L2 raw_match_data write is controlled single-target execution: it requires final DB-write confirmation, writes only raw_match_data, and keeps protected tables untouched."
	@echo "  L2 remaining raw_match_data acquisition planning is raw-first / parse-later. Parser is deferred until training data design."
	@echo "  Phase 5.20L2F remaining write requires HASH_STRATEGY=stable_raw_payload_v1, final DB-write confirmation, FotMobRawDetailFetcher recapture, exact Phase 5.20L2E stable baselines, raw_match_data only rows=7, and no parser/features/training/prediction."
	@echo "  Phase 5.21L2A raw_match_data completeness audit is SELECT-only, layered by data_version/provenance, no network/DB write/parser/features/training/prediction, and checks whether FotMob raw_data is complete enough or transformed/lossy."
	@echo "  Phase 5.21L2B live source fidelity compare is single-target only: compare live __NEXT_DATA__.props.pageProps with stored raw_data path coverage, no DB/raw write, no parser/features/training/prediction."
	@echo "  Phase 5.21L2C raw storage strategy planning is planning-only: future canonical raw should prefer fotmob_pageprops_v2, transformed payload is derived/helper, no rewrite/DB write/parser/features/training/prediction."
	@echo "  Phase 5.21L2D pageProps v2 no-write preview is single-target only: constructs fotmob_pageprops_v2 in memory, computes stable_pageprops_payload_v1 hash, compares v2 candidate vs existing v1, no DB/raw write/parser/features/training/prediction."
	@echo "  Phase 5.21L2E pageProps v2 controlled write planning is planning-only: review raw_match_data unique constraints, plan v1/v2 coexistence, no DB write/migration/parser/features/training/prediction."
	@echo "  Phase 5.21L2F raw_match_data versioned schema migration preflight is planning-only: exact UNIQUE(match_id) -> UNIQUE(match_id,data_version) plan, no DB write/ALTER TABLE/migration/parser/features/training/prediction."
	@echo "  Phase 5.21L2G raw_match_data versioned schema migration execution is schema-only: exact UNIQUE(match_id) -> UNIQUE(match_id,data_version), no raw data writes/FotMob/parser/features/training/prediction."
	@echo "  Phase 5.21L2I pageProps v2 single-target write preflight recaptures target 4830747, constructs v2 candidate in memory, SELECTs existing versions, reports would_insert, and performs no DB/raw write/parser/features/training/prediction."
	@echo "  Phase 5.21L2J pageProps v2 single-target controlled write requires baseline hash + final confirmation, writes exactly one raw_match_data v2 row, and performs no matches/features/training/prediction writes."
	@echo "  Phase 5.21L2K pageProps v2 post-write canonical read verification is SELECT-only: confirms selector picks v2 for 4830747, v1 fallback for remaining seeded matches, and synthetic/unknown exclusion; no DB write/network/parser/features/training."
	@echo "  Phase 5.21L2L remaining seeded pageProps v2 acquisition preflight is no-write: targets only the 7 remaining seeded matches, recaptures sequentially, computes stable_pageprops_payload_v1 hashes, and defers controlled write/parser/features/training."
	@echo "  Phase 5.21L2P parser boundary / leakage-safe planning is planning-only: current 8 seeded pageProps v2 rows are validation samples, not a training dataset; it defines parser module boundaries, prediction-cutoff leakage rules, large-scale acquisition planning, and odds raw roadmap without parser/features/training."
	@echo "  Phase 5.20L2D hash stability audit is local-only: verify stable_raw_payload_v1, keep volatile _meta out of data_hash, no network, no DB writes."
	@echo "  Remaining seeded matches require separate authorization, preflight, and controlled write phases."
	@echo "  Phase 5.11L2 direct matchDetails endpoint returned 403; do not retry or change headers/routes before route audit authorization."
	@echo "  Phase 5.12L2B route selector supports html_hydration before api_match_details; alternate_route remains plan-only."
	@echo "  Live raw detail requests require future explicit authorization; use audited route selector / safe adapter, not legacy harvest/backfill."
	@echo "  raw_match_data write requires future authorization/preflight."
	@echo "  Future preferred path will continue as data-l2-* controlled targets."
	@echo "  make data-fotmob-single-target-adapter-preflight TARGET_SOURCE=fotmob TARGET_SCOPE_TYPE=match_id TARGET_MATCH_ID=<id> ...  # Phase 4.98F hardening, stdout-only, no network/staging/DB/legacy runtime"
	@echo "  make data-fotmob-stdout-network-dry-run-authorization-packet-preview PACKET=<path>  # Phase 4.99F template-only, stdout-only, no network/staging/DB/runtime packet write"
	@echo "  make data-fotmob-stdout-network-dry-run-execution-plan-preview PLAN=<path> PACKET=<path>  # Phase 5.00F template-only, stdout-only, no network/staging/DB/runtime execution plan write"
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
	@echo "  make data-l1-discovery-commit SOURCE=fotmob SCOPE=<scope> CONFIRM_L1_DISCOVERY_COMMIT=1  # blocked in Phase 5.05L1"
	@echo "  make data-l1-matches-seed-commit SOURCE=fotmob SCOPE=<scope> CONFIRM_L1_MATCHES_SEED_COMMIT=1  # blocked in Phase 5.07L1"
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
	@echo "  make data-single-target-acquisition-network-authorization-handoff-checklist-preview HANDOFF_CHECKLIST=<path> REVIEW_RESULT=<path> REVIEW_PLAN=<path> INTAKE=<path> VALIDATION_CLOSURE=<path> BLOCKED_SUMMARY=<path>  # handoff preview, Phase 4.94D"
	@echo "  make data-single-target-acquisition-network-authorization-handoff-checklist-commit ... CONFIRM_SINGLE_TARGET_ACQUISITION_NETWORK_AUTHORIZATION_HANDOFF_CHECKLIST=1  # blocked in Phase 4.94D"
	@echo "  make data-single-target-acquisition-network-authorization-decision-preview AUTHORIZATION_DECISION=<path> HANDOFF_CHECKLIST=<path> REVIEW_RESULT=<path> REVIEW_PLAN=<path> INTAKE=<path> VALIDATION_CLOSURE=<path> BLOCKED_SUMMARY=<path>  # authorization decision preview, Phase 4.95D"
	@echo "  make data-single-target-acquisition-network-authorization-decision-commit ... CONFIRM_SINGLE_TARGET_ACQUISITION_NETWORK_AUTHORIZATION_DECISION=1  # blocked in Phase 4.95D"
	@echo "  make data-fotmob-single-target-adapter-commit TARGET_SOURCE=fotmob TARGET_SCOPE_TYPE=match_id TARGET_MATCH_ID=<id> CONFIRM_FOTMOB_SINGLE_TARGET_ADAPTER=1  # blocked in Phase 4.98F"
	@echo "  make data-fotmob-stdout-network-dry-run-authorization-packet-commit PACKET=<path> CONFIRM_FOTMOB_STDOUT_NETWORK_DRY_RUN_AUTHORIZATION_PACKET=1  # blocked in Phase 4.99F"
	@echo "  make data-fotmob-stdout-network-dry-run-execution-plan-commit PLAN=<path> PACKET=<path> CONFIRM_FOTMOB_STDOUT_NETWORK_DRY_RUN_EXECUTION_PLAN=1  # blocked in Phase 5.00F"
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

data-l1-discovery-preview: ## L1 safe preview wrapper. Phase 5.05L1. Preview-only, no network, no DB, no browser/proxy.
	@if [ -z "$(SOURCE)" ] || [ -z "$(SCOPE)" ]; then \
		echo "ERROR: provide SOURCE=fotmob and SCOPE=<config_only_preview|league_season_date|league_season_window_preview|controlled_candidates_preview>"; \
		exit 1; \
	fi
	@$(COMPOSE_DEV) exec -T dev node scripts/ops/l1_discovery_safe_preview.js \
		--source="$(SOURCE)" \
		--scope="$(SCOPE)" \
		$(if $(LEAGUE_ID),--league-id="$(LEAGUE_ID)") \
		$(if $(SEASON),--season="$(SEASON)") \
		$(if $(DATE),--date="$(DATE)") \
		--concurrency="$(or $(CONCURRENCY),1)" \
		--max-targets="$(or $(MAX_TARGETS),1)" \
		$(if $(LOOKBACK),--lookback="$(LOOKBACK)") \
		$(if $(LOOKAHEAD),--lookahead="$(LOOKAHEAD)") \
		--dry-run=true

data-l1-discovery-candidates-preview: ## L1 controlled candidates preview. Phase 5.05L1. Default no external network, no DB, no browser/proxy.
	@if [ -z "$(SOURCE)" ] || [ -z "$(LEAGUE_ID)" ] || [ -z "$(SEASON)" ] || [ -z "$(DATE)" ]; then \
		echo "ERROR: provide SOURCE=fotmob LEAGUE_ID=<id> SEASON=<season> DATE=<yyyy-mm-dd>"; \
		exit 1; \
	fi
	@$(COMPOSE_DEV) exec -T dev node scripts/ops/l1_discovery_safe_preview.js \
		--source="$(SOURCE)" \
		--scope="$(or $(SCOPE),controlled_candidates_preview)" \
		--league-id="$(LEAGUE_ID)" \
		--season="$(SEASON)" \
		--date="$(DATE)" \
		--concurrency="$(or $(CONCURRENCY),1)" \
		--max-targets="$(or $(MAX_TARGETS),1)" \
		$(if $(LOOKBACK),--lookback="$(LOOKBACK)") \
		$(if $(LOOKAHEAD),--lookahead="$(LOOKAHEAD)") \
		--network-authorization="$(or $(NETWORK_AUTHORIZATION),no)" \
		--dry-run=true

data-l1-discovery-candidates-network-preview: ## L1 controlled external network candidates preview. Phase 5.05L1. No DB, no browser/proxy.
	@if [ -z "$(SOURCE)" ] || [ -z "$(LEAGUE_ID)" ] || [ -z "$(SEASON)" ] || [ -z "$(DATE)" ]; then \
		echo "ERROR: provide SOURCE=fotmob LEAGUE_ID=<id> SEASON=<season> DATE=<yyyy-mm-dd>"; \
		exit 1; \
	fi
	@$(COMPOSE_DEV) exec -T dev node scripts/ops/l1_discovery_safe_preview.js \
		--network-preview=true \
		--source="$(SOURCE)" \
		--scope="$(or $(SCOPE),controlled_candidates_preview)" \
		--league-id="$(LEAGUE_ID)" \
		--season="$(SEASON)" \
		--date="$(DATE)" \
		--concurrency="$(or $(CONCURRENCY),1)" \
		--max-targets="$(or $(MAX_TARGETS),10)" \
		$(if $(LOOKBACK),--lookback="$(LOOKBACK)") \
		$(if $(LOOKAHEAD),--lookahead="$(LOOKAHEAD)") \
		--network-authorization="$(or $(NETWORK_AUTHORIZATION),no)" \
		--allow-browser-runtime="$(or $(ALLOW_BROWSER_RUNTIME),no)" \
		--allow-proxy-runtime="$(or $(ALLOW_PROXY_RUNTIME),no)" \
		--allow-db-write="$(or $(ALLOW_DB_WRITE),no)" \
		--dry-run=true

data-l1-discovery-commit: ## Blocked L1 safe preview commit gate. Remains blocked in Phase 5.05L1.
	@echo "BLOCKED: L1 discovery safe preview wrapper does not execute writes in Phase 5.05L1."
	@echo "  No titan_discovery direct call, no DiscoveryService.discover call, no FixtureRepository.persist call."
	@echo "  Even with CONFIRM_L1_DISCOVERY_COMMIT=1, network execution and DB writes remain blocked."
	@exit 1

data-l1-matches-seed-commit-plan: ## L1 matches seed commit planning. Phase 5.06L1. Planning-only, no network/DB writes.
	@if [ -z "$(SOURCE)" ] || [ -z "$(SCOPE)" ] || [ -z "$(LEAGUE_ID)" ] || [ -z "$(SEASON)" ] || [ -z "$(DATE)" ] || [ -z "$(CANDIDATE_COUNT)" ]; then \
		echo "ERROR: provide SOURCE=fotmob SCOPE=<league_season_date|controlled_candidates_preview> LEAGUE_ID=<id> SEASON=<season> DATE=<yyyy-mm-dd> CANDIDATE_COUNT=<n>"; \
		exit 1; \
	fi
	@$(COMPOSE_DEV) exec -T dev node scripts/ops/l1_matches_seed_commit_plan.js \
		--source="$(SOURCE)" \
		--scope="$(SCOPE)" \
		--league-id="$(LEAGUE_ID)" \
		--season="$(SEASON)" \
		--date="$(DATE)" \
		--candidate-count="$(CANDIDATE_COUNT)" \
		$(if $(CONTAINS_TARGET_MATCH_ID),--contains-target-match-id="$(CONTAINS_TARGET_MATCH_ID)") \
		$(if $(CONTAINS_TARGET_LABEL),--contains-target-label="$(CONTAINS_TARGET_LABEL)") \
		--max-seed-rows="$(or $(MAX_SEED_ROWS),10)" \
		--commit="$(or $(COMMIT),no)" \
		--allow-db-write=no \
		--allow-matches-write=no \
		--allow-raw-match-data-write=no \
		--training=no \
		--prediction=no

data-l1-matches-seed-commit-authorization: ## L1 matches seed commit authorization. Phase 5.07L1. Authorization-only, no network/DB writes.
	@if [ -z "$(SOURCE)" ] || [ -z "$(SCOPE)" ] || [ -z "$(LEAGUE_ID)" ] || [ -z "$(SEASON)" ] || [ -z "$(DATE)" ] || [ -z "$(CANDIDATE_COUNT)" ] || [ -z "$(CONTAINS_TARGET_MATCH_ID)" ] || [ -z "$(CONTAINS_TARGET_LABEL)" ]; then \
		echo "ERROR: provide SOURCE=fotmob SCOPE=<league_season_date|controlled_candidates_preview> LEAGUE_ID=<id> SEASON=<season> DATE=<yyyy-mm-dd> CANDIDATE_COUNT=<n> CONTAINS_TARGET_MATCH_ID=<id> CONTAINS_TARGET_LABEL=<label>"; \
		exit 1; \
	fi
	@$(COMPOSE_DEV) exec -T dev node scripts/ops/l1_matches_seed_commit_authorization.js \
		--source="$(SOURCE)" \
		--scope="$(SCOPE)" \
		--league-id="$(LEAGUE_ID)" \
		--season="$(SEASON)" \
		--date="$(DATE)" \
		--candidate-count="$(CANDIDATE_COUNT)" \
		--contains-target-match-id="$(CONTAINS_TARGET_MATCH_ID)" \
		--contains-target-label="$(CONTAINS_TARGET_LABEL)" \
		--max-seed-rows="$(or $(MAX_SEED_ROWS),10)" \
		--user-authorized-matches-seed-commit="$(or $(USER_AUTHORIZED_MATCHES_SEED_COMMIT),no)" \
		--allow-matches-write-next-phase="$(or $(ALLOW_MATCHES_WRITE_NEXT_PHASE),no)" \
		--allow-db-write-now="$(or $(ALLOW_DB_WRITE_NOW),no)" \
		--allow-raw-match-data-write="$(or $(ALLOW_RAW_MATCH_DATA_WRITE),no)" \
		--allow-training="$(or $(ALLOW_TRAINING),no)" \
		--allow-prediction="$(or $(ALLOW_PREDICTION),no)" \
		--final-human-confirmation="$(or $(FINAL_HUMAN_CONFIRMATION),no)"

data-l1-matches-seed-commit-execution-preflight: ## L1 matches seed commit execution preflight. Phase 5.08L1. Preflight-only, exact candidates + SELECT-only affected matches, no DB writes.
	@if [ -z "$(SOURCE)" ] || [ -z "$(SCOPE)" ] || [ -z "$(LEAGUE_ID)" ] || [ -z "$(SEASON)" ] || [ -z "$(DATE)" ] || [ -z "$(CANDIDATE_COUNT)" ] || [ -z "$(CONTAINS_TARGET_MATCH_ID)" ] || [ -z "$(CONTAINS_TARGET_LABEL)" ]; then \
		echo "ERROR: provide SOURCE=fotmob SCOPE=<league_season_date|controlled_candidates_preview> LEAGUE_ID=<id> SEASON=<season> DATE=<yyyy-mm-dd> CANDIDATE_COUNT=<n> CONTAINS_TARGET_MATCH_ID=<id> CONTAINS_TARGET_LABEL=<label>"; \
		exit 1; \
	fi
	@$(COMPOSE_DEV) exec -T dev node scripts/ops/l1_matches_seed_commit_execution_preflight.js \
		--source="$(SOURCE)" \
		--scope="$(SCOPE)" \
		--league-id="$(LEAGUE_ID)" \
		--season="$(SEASON)" \
		--date="$(DATE)" \
		--candidate-count="$(CANDIDATE_COUNT)" \
		--contains-target-match-id="$(CONTAINS_TARGET_MATCH_ID)" \
		--contains-target-label="$(CONTAINS_TARGET_LABEL)" \
		--max-seed-rows="$(or $(MAX_SEED_ROWS),10)" \
		--final-db-write-confirmation="$(or $(FINAL_DB_WRITE_CONFIRMATION),no)" \
		--allow-db-write-now="$(or $(ALLOW_DB_WRITE_NOW),no)" \
		--allow-matches-write-now="$(or $(ALLOW_MATCHES_WRITE_NOW),no)" \
		--allow-raw-match-data-write="$(or $(ALLOW_RAW_MATCH_DATA_WRITE),no)" \
		--allow-training="$(or $(ALLOW_TRAINING),no)" \
		--allow-prediction="$(or $(ALLOW_PREDICTION),no)" \
		$(if $(CANDIDATES_JSON),--candidates-json='$(CANDIDATES_JSON)') \
		$(if $(EXISTING_MATCHES_JSON),--existing-matches-json='$(EXISTING_MATCHES_JSON)')

data-l1-matches-seed-commit-execute: ## L1 matches seed commit execution. Phase 5.09L1. Exact 2026-05-10 FotMob Ligue 1 candidates only, matches-only transaction.
	@if [ -z "$(SOURCE)" ] || [ -z "$(SCOPE)" ] || [ -z "$(LEAGUE_ID)" ] || [ -z "$(SEASON)" ] || [ -z "$(DATE)" ] || [ -z "$(CANDIDATE_COUNT)" ] || [ -z "$(CONTAINS_TARGET_MATCH_ID)" ] || [ -z "$(CONTAINS_TARGET_LABEL)" ]; then \
		echo "ERROR: provide SOURCE=fotmob SCOPE=league_season_date LEAGUE_ID=53 SEASON=2025/2026 DATE=2026-05-10 CANDIDATE_COUNT=8 CONTAINS_TARGET_MATCH_ID=4830746 CONTAINS_TARGET_LABEL=<label>"; \
		exit 1; \
	fi
	@$(COMPOSE_DEV) exec -T dev node scripts/ops/l1_matches_seed_commit_execute.js \
		--source="$(SOURCE)" \
		--scope="$(SCOPE)" \
		--league-id="$(LEAGUE_ID)" \
		--season="$(SEASON)" \
		--date="$(DATE)" \
		--candidate-count="$(CANDIDATE_COUNT)" \
		--contains-target-match-id="$(CONTAINS_TARGET_MATCH_ID)" \
		--contains-target-label="$(CONTAINS_TARGET_LABEL)" \
		--max-seed-rows="$(or $(MAX_SEED_ROWS),10)" \
		--final-db-write-confirmation="$(or $(FINAL_DB_WRITE_CONFIRMATION),no)" \
		--allow-db-write-now="$(or $(ALLOW_DB_WRITE_NOW),no)" \
		--allow-matches-write-now="$(or $(ALLOW_MATCHES_WRITE_NOW),no)" \
		--allow-raw-match-data-write="$(or $(ALLOW_RAW_MATCH_DATA_WRITE),no)" \
		--allow-training="$(or $(ALLOW_TRAINING),no)" \
		--allow-prediction="$(or $(ALLOW_PREDICTION),no)" \
		--allow-browser-runtime="$(or $(ALLOW_BROWSER_RUNTIME),no)" \
		--allow-proxy-runtime="$(or $(ALLOW_PROXY_RUNTIME),no)" \
		--bulk="$(or $(BULK),no)" \
		$(if $(CANDIDATES_JSON),--candidates-json='$(CANDIDATES_JSON)') \
		$(if $(EXISTING_MATCHES_JSON),--existing-matches-json='$(EXISTING_MATCHES_JSON)')

data-l1-matches-seed-commit: ## Blocked L1 matches seed commit gate. Remains blocked in Phase 5.08L1.
	@echo "BLOCKED: L1 matches seed commit is not executable in Phase 5.06L1 planning."
	@echo "  L1 matches seed commit remains authorization-only in Phase 5.07L1, execution-preflight-only in Phase 5.08L1, and exact execute-only via data-l1-matches-seed-commit-execute in Phase 5.09L1."
	@echo "  Use data-l1-matches-seed-commit-plan, data-l1-matches-seed-commit-authorization, data-l1-matches-seed-commit-execution-preflight, and the exact-scope data-l1-matches-seed-commit-execute gate."
	@echo "  Even with CONFIRM_L1_MATCHES_SEED_COMMIT=1, matches/DB/raw writes remain blocked."
	@exit 1

data-l2-raw-detail-route-preview-plan: ## L2 raw detail route selector plan. Phase 5.12L2B. Stdout only, no network/DB/raw write/browser/proxy.
	@echo "{"
	@echo "  \"phase\": \"PHASE5_12L2B_SAFE_FOTMOB_DETAIL_ROUTE_SELECTOR\","
	@echo "  \"preview_only\": true,"
	@echo "  \"plan_only\": true,"
	@echo "  \"route_selector_enabled\": true,"
	@echo "  \"default_route_order\": [\"html_hydration\", \"api_match_details\"],"
	@echo "  \"alternate_route\": \"plan_only\","
	@echo "  \"live_external_request_allowed\": false,"
	@echo "  \"db_write_allowed\": false,"
	@echo "  \"raw_match_data_write_allowed\": false,"
	@echo "  \"browser_runtime_allowed\": false,"
	@echo "  \"proxy_runtime_allowed\": false"
	@echo "}"

data-l2-raw-detail-preview: ## L2 raw detail preview. Phase 5.12L2B. Route selector, stdout metadata only, live blocked by default.
	@if [ -z "$(SOURCE)" ] || [ -z "$(MATCH_ID)" ] || [ -z "$(EXTERNAL_ID)" ] || [ -z "$(HOME_TEAM)" ] || [ -z "$(AWAY_TEAM)" ]; then \
		echo "ERROR: provide SOURCE=fotmob MATCH_ID=53_20252026_4830746 EXTERNAL_ID=4830746 HOME_TEAM=Angers AWAY_TEAM=Strasbourg"; \
		exit 1; \
	fi
	@$(COMPOSE_DEV) exec -T dev node scripts/ops/l2_raw_detail_preview.js \
		--source="$(SOURCE)" \
		--match-id="$(MATCH_ID)" \
		--external-id="$(EXTERNAL_ID)" \
		--home-team="$(HOME_TEAM)" \
		--away-team="$(AWAY_TEAM)" \
		--route="$(or $(ROUTE),auto)" \
		--network-authorization="$(or $(NETWORK_AUTHORIZATION),no)" \
		--live-preview-authorization="$(or $(LIVE_PREVIEW_AUTHORIZATION),no)" \
		--allow-db-write="$(or $(ALLOW_DB_WRITE),no)" \
		--allow-raw-match-data-write="$(or $(ALLOW_RAW_MATCH_DATA_WRITE),no)" \
		--allow-browser-runtime="$(or $(ALLOW_BROWSER_RUNTIME),no)" \
		--allow-proxy-runtime="$(or $(ALLOW_PROXY_RUNTIME),no)" \
		--concurrency="$(or $(CONCURRENCY),1)" \
			--retry="$(or $(RETRY),0)" \
			--print-body="$(or $(PRINT_BODY),no)" \
			--save-body="$(or $(SAVE_BODY),no)"

data-l2-raw-match-data-ingest-plan: ## L2 raw_match_data ingest planning. Phase 5.13L2. No network/DB/raw write.
	@if [ -z "$(SOURCE)" ] || [ -z "$(ROUTE)" ] || [ -z "$(MATCH_ID)" ] || [ -z "$(EXTERNAL_ID)" ] || [ -z "$(HOME_TEAM)" ] || [ -z "$(AWAY_TEAM)" ] || [ -z "$(PREVIEW_BODY_SHA256)" ] || [ -z "$(PREVIEW_BODY_BYTE_LENGTH)" ]; then \
		echo "ERROR: provide SOURCE=fotmob ROUTE=html_hydration MATCH_ID=53_20252026_4830746 EXTERNAL_ID=4830746 HOME_TEAM=Angers AWAY_TEAM=Strasbourg PREVIEW_BODY_SHA256=<sha256> PREVIEW_BODY_BYTE_LENGTH=<bytes>"; \
		exit 1; \
	fi
	@$(COMPOSE_DEV) exec -T dev node scripts/ops/l2_raw_match_data_ingest_plan.js \
		--source="$(SOURCE)" \
		--route="$(ROUTE)" \
		--match-id="$(MATCH_ID)" \
		--external-id="$(EXTERNAL_ID)" \
		--home-team="$(HOME_TEAM)" \
		--away-team="$(AWAY_TEAM)" \
		--preview-body-sha256="$(PREVIEW_BODY_SHA256)" \
		--preview-body-byte-length="$(PREVIEW_BODY_BYTE_LENGTH)" \
		--hydration-parse-ok="$(or $(HYDRATION_PARSE_OK),yes)" \
		--looks-like-valid-match-detail="$(or $(LOOKS_LIKE_VALID_MATCH_DETAIL),yes)" \
		--allow-db-write="$(or $(ALLOW_DB_WRITE),no)" \
		--allow-raw-match-data-write="$(or $(ALLOW_RAW_MATCH_DATA_WRITE),no)" \
		--allow-matches-write="$(or $(ALLOW_MATCHES_WRITE),no)" \
		--allow-training="$(or $(ALLOW_TRAINING),no)" \
		--allow-prediction="$(or $(ALLOW_PREDICTION),no)" \
		--commit="$(or $(COMMIT),no)" \
		--execute="$(or $(EXECUTE),no)" \
		--network-authorization="$(or $(NETWORK_AUTHORIZATION),no)"

data-l2-raw-match-data-ingest-authorization: ## L2 raw_match_data ingest authorization. Phase 5.14L2. Authorization-only, no network/DB/raw write.
	@if [ -z "$(SOURCE)" ] || [ -z "$(ROUTE)" ] || [ -z "$(MATCH_ID)" ] || [ -z "$(EXTERNAL_ID)" ] || [ -z "$(HOME_TEAM)" ] || [ -z "$(AWAY_TEAM)" ] || [ -z "$(DATA_VERSION)" ] || [ -z "$(PREVIEW_BODY_SHA256)" ]; then \
		echo "ERROR: provide SOURCE=fotmob ROUTE=html_hydration MATCH_ID=53_20252026_4830746 EXTERNAL_ID=4830746 HOME_TEAM=Angers AWAY_TEAM=Strasbourg DATA_VERSION=fotmob_html_hyd_v1 PREVIEW_BODY_SHA256=<sha256>"; \
		exit 1; \
	fi
	@$(COMPOSE_DEV) exec -T dev node scripts/ops/l2_raw_match_data_ingest_authorization.js \
		--source="$(SOURCE)" \
		--route="$(ROUTE)" \
		--match-id="$(MATCH_ID)" \
		--external-id="$(EXTERNAL_ID)" \
		--home-team="$(HOME_TEAM)" \
		--away-team="$(AWAY_TEAM)" \
		--data-version="$(DATA_VERSION)" \
		--preview-body-sha256="$(PREVIEW_BODY_SHA256)" \
		--hydration-parse-ok="$(or $(HYDRATION_PARSE_OK),yes)" \
		--looks-like-valid-match-detail="$(or $(LOOKS_LIKE_VALID_MATCH_DETAIL),yes)" \
		--user-authorized-raw-match-data-ingest="$(or $(USER_AUTHORIZED_RAW_MATCH_DATA_INGEST),no)" \
		--allow-raw-match-data-write-next-phase="$(or $(ALLOW_RAW_MATCH_DATA_WRITE_NEXT_PHASE),no)" \
		--allow-db-write-now="$(or $(ALLOW_DB_WRITE_NOW),no)" \
		--allow-raw-match-data-write-now="$(or $(ALLOW_RAW_MATCH_DATA_WRITE_NOW),no)" \
		--allow-matches-write="$(or $(ALLOW_MATCHES_WRITE),no)" \
		--allow-training="$(or $(ALLOW_TRAINING),no)" \
		--allow-prediction="$(or $(ALLOW_PREDICTION),no)" \
		--final-human-confirmation="$(or $(FINAL_HUMAN_CONFIRMATION),no)" \
		--commit="$(or $(COMMIT),no)" \
		--execute="$(or $(EXECUTE),no)" \
			--network-authorization="$(or $(NETWORK_AUTHORIZATION),no)" \
			--live-preview-authorization="$(or $(LIVE_PREVIEW_AUTHORIZATION),no)"

data-l2-raw-match-data-ingest-preflight: ## L2 raw_match_data ingest preflight. Phase 5.15L2. Live preview + SELECT-only, no DB/raw write.
	@if [ -z "$(SOURCE)" ] || [ -z "$(ROUTE)" ] || [ -z "$(MATCH_ID)" ] || [ -z "$(EXTERNAL_ID)" ] || [ -z "$(HOME_TEAM)" ] || [ -z "$(AWAY_TEAM)" ] || [ -z "$(DATA_VERSION)" ]; then \
		echo "ERROR: provide SOURCE=fotmob ROUTE=html_hydration MATCH_ID=53_20252026_4830746 EXTERNAL_ID=4830746 HOME_TEAM=Angers AWAY_TEAM=Strasbourg DATA_VERSION=fotmob_html_hyd_v1"; \
		exit 1; \
	fi
	@$(COMPOSE_DEV) exec -T dev node scripts/ops/l2_raw_match_data_ingest_preflight.js \
		--source="$(SOURCE)" \
		--route="$(ROUTE)" \
		--match-id="$(MATCH_ID)" \
		--external-id="$(EXTERNAL_ID)" \
		--home-team="$(HOME_TEAM)" \
		--away-team="$(AWAY_TEAM)" \
		--data-version="$(DATA_VERSION)" \
		--network-authorization="$(or $(NETWORK_AUTHORIZATION),no)" \
		--live-preview-authorization="$(or $(LIVE_PREVIEW_AUTHORIZATION),no)" \
		--allow-db-write="$(or $(ALLOW_DB_WRITE),no)" \
		--allow-raw-match-data-write="$(or $(ALLOW_RAW_MATCH_DATA_WRITE),no)" \
		--allow-matches-write="$(or $(ALLOW_MATCHES_WRITE),no)" \
		--allow-training="$(or $(ALLOW_TRAINING),no)" \
		--allow-prediction="$(or $(ALLOW_PREDICTION),no)" \
		--allow-browser-runtime="$(or $(ALLOW_BROWSER_RUNTIME),no)" \
		--allow-proxy-runtime="$(or $(ALLOW_PROXY_RUNTIME),no)" \
		--concurrency="$(or $(CONCURRENCY),1)" \
		--retry="$(or $(RETRY),0)" \
		--print-body="$(or $(PRINT_BODY),no)" \
		--save-body="$(or $(SAVE_BODY),no)" \
		--commit="$(or $(COMMIT),no)" \
		--execute="$(or $(EXECUTE),no)"

data-l2-raw-match-data-write: ## L2 controlled raw_match_data write. Phase 5.16L2. Single-target transaction, raw_match_data only.
	@if [ -z "$(SOURCE)" ] || [ -z "$(ROUTE)" ] || [ -z "$(MATCH_ID)" ] || [ -z "$(EXTERNAL_ID)" ] || [ -z "$(HOME_TEAM)" ] || [ -z "$(AWAY_TEAM)" ] || [ -z "$(DATA_VERSION)" ] || [ -z "$(BASELINE_RAW_DATA_HASH)" ]; then \
		echo "ERROR: provide SOURCE=fotmob ROUTE=html_hydration MATCH_ID=53_20252026_4830746 EXTERNAL_ID=4830746 HOME_TEAM=Angers AWAY_TEAM=Strasbourg DATA_VERSION=fotmob_html_hyd_v1 BASELINE_RAW_DATA_HASH=d40f757adccf5be96d107188196efa905b6b573b62d7b4428014d7ce4f39a1f6"; \
		exit 1; \
	fi
	@$(COMPOSE_DEV) exec -T dev node scripts/ops/l2_raw_match_data_write.js \
		--source="$(SOURCE)" \
		--route="$(ROUTE)" \
		--match-id="$(MATCH_ID)" \
		--external-id="$(EXTERNAL_ID)" \
		--home-team="$(HOME_TEAM)" \
		--away-team="$(AWAY_TEAM)" \
		--data-version="$(DATA_VERSION)" \
		--baseline-raw-data-hash="$(BASELINE_RAW_DATA_HASH)" \
		--network-authorization="$(or $(NETWORK_AUTHORIZATION),no)" \
		--live-preview-authorization="$(or $(LIVE_PREVIEW_AUTHORIZATION),no)" \
		--final-db-write-confirmation="$(or $(FINAL_DB_WRITE_CONFIRMATION),no)" \
		--allow-db-write="$(or $(ALLOW_DB_WRITE),no)" \
		--allow-raw-match-data-write="$(or $(ALLOW_RAW_MATCH_DATA_WRITE),no)" \
		--allow-matches-write="$(or $(ALLOW_MATCHES_WRITE),no)" \
		--allow-training="$(or $(ALLOW_TRAINING),no)" \
		--allow-prediction="$(or $(ALLOW_PREDICTION),no)" \
		--allow-browser-runtime="$(or $(ALLOW_BROWSER_RUNTIME),no)" \
		--allow-proxy-runtime="$(or $(ALLOW_PROXY_RUNTIME),no)" \
		--concurrency="$(or $(CONCURRENCY),1)" \
		--retry="$(or $(RETRY),0)" \
		--print-body="$(or $(PRINT_BODY),no)" \
		--save-body="$(or $(SAVE_BODY),no)" \
		--bulk="$(or $(BULK),no)" \
		--commit="$(or $(COMMIT),no)" \
		--execute="$(or $(EXECUTE),no)"

data-l2-remaining-raw-match-data-acquisition-plan: ## L2 remaining seeded raw_match_data acquisition planning. Phase 5.17L2. SELECT-only DB coverage, no network/write/parser.
	@if [ -z "$(SOURCE)" ] || [ -z "$(LEAGUE_ID)" ] || [ -z "$(SEASON)" ] || [ -z "$(DATE)" ] || [ -z "$(EXPECTED_SEEDED_COUNT)" ] || [ -z "$(EXPECTED_EXISTING_RAW_COUNT)" ] || [ -z "$(EXPECTED_MISSING_RAW_COUNT)" ]; then \
		echo "ERROR: provide SOURCE=fotmob LEAGUE_ID=53 SEASON=2025/2026 DATE=2026-05-10 EXPECTED_SEEDED_COUNT=8 EXPECTED_EXISTING_RAW_COUNT=1 EXPECTED_MISSING_RAW_COUNT=7"; \
		exit 1; \
	fi
	@SEEDED_JSON="$$( $(COMPOSE_DEV) exec -T db sh -lc 'psql -U "$$POSTGRES_USER" -d "$$POSTGRES_DB" -At -c "SELECT COALESCE(json_agg(row_to_json(seeded) ORDER BY seeded.match_id)::text, '\''[]'\'') FROM (SELECT match_id, external_id, home_team, away_team, match_date, status FROM matches WHERE match_id LIKE '\''53_20252026_%'\'' ORDER BY match_id) seeded;"' )"; \
	RAW_COVERAGE_JSON="$$( $(COMPOSE_DEV) exec -T db sh -lc 'psql -U "$$POSTGRES_USER" -d "$$POSTGRES_DB" -At -c "SELECT COALESCE(json_agg(row_to_json(coverage) ORDER BY coverage.match_id)::text, '\''[]'\'') FROM (SELECT m.match_id, m.external_id, m.home_team, m.away_team, m.match_date, m.status, r.id AS raw_id, r.data_version, r.data_hash, r.collected_at, CASE WHEN r.match_id IS NULL THEN '\''missing_raw'\'' ELSE '\''has_raw'\'' END AS raw_status FROM matches m LEFT JOIN raw_match_data r ON r.match_id = m.match_id WHERE m.match_id LIKE '\''53_20252026_%'\'' ORDER BY m.match_id) coverage;"' )"; \
	$(COMPOSE_DEV) exec -T dev node scripts/ops/l2_remaining_raw_match_data_acquisition_plan.js \
		--source="$(SOURCE)" \
		--league-id="$(LEAGUE_ID)" \
		--season="$(SEASON)" \
		--date="$(DATE)" \
		--expected-seeded-count="$(EXPECTED_SEEDED_COUNT)" \
		--expected-existing-raw-count="$(EXPECTED_EXISTING_RAW_COUNT)" \
		--expected-missing-raw-count="$(EXPECTED_MISSING_RAW_COUNT)" \
		--allow-network="$(or $(ALLOW_NETWORK),no)" \
		--allow-db-write="$(or $(ALLOW_DB_WRITE),no)" \
		--allow-raw-match-data-write="$(or $(ALLOW_RAW_MATCH_DATA_WRITE),no)" \
		--allow-matches-write="$(or $(ALLOW_MATCHES_WRITE),no)" \
		--allow-training="$(or $(ALLOW_TRAINING),no)" \
		--allow-prediction="$(or $(ALLOW_PREDICTION),no)" \
		--network-authorization="$(or $(NETWORK_AUTHORIZATION),no)" \
		--live-preview-authorization="$(or $(LIVE_PREVIEW_AUTHORIZATION),no)" \
		--commit="$(or $(COMMIT),no)" \
		--execute="$(or $(EXECUTE),no)" \
		--seeded-matches-json="$$SEEDED_JSON" \
		--raw-coverage-json="$$RAW_COVERAGE_JSON"

data-l2-remaining-raw-match-data-acquisition-authorization: ## L2 remaining raw_match_data acquisition authorization. Phase 5.18L2. Authorization-only, no network/write/parser.
	@if [ -z "$(SOURCE)" ] || [ -z "$(LEAGUE_ID)" ] || [ -z "$(SEASON)" ] || [ -z "$(DATE)" ] || [ -z "$(ROUTE)" ]; then \
		echo "ERROR: provide SOURCE=fotmob LEAGUE_ID=53 SEASON=2025/2026 DATE=2026-05-10 ROUTE=html_hydration"; \
		exit 1; \
	fi
	$(COMPOSE_DEV) exec -T dev node scripts/ops/l2_remaining_raw_match_data_acquisition_authorization.js \
		--source="$(SOURCE)" \
		--league-id="$(LEAGUE_ID)" \
		--season="$(SEASON)" \
		--date="$(DATE)" \
		--route="$(ROUTE)" \
		--expected-seeded-count="$(or $(EXPECTED_SEEDED_COUNT),8)" \
		--expected-existing-raw-count="$(or $(EXPECTED_EXISTING_RAW_COUNT),1)" \
		--expected-missing-raw-count="$(or $(EXPECTED_MISSING_RAW_COUNT),7)" \
		--remaining-external-ids="$(or $(REMAINING_EXTERNAL_IDS),4830747,4830748,4830750,4830751,4830752,4830753,4830754)" \
		--user-authorized-remaining-raw-acquisition="$(or $(USER_AUTHORIZED_REMAINING_RAW_ACQUISITION),yes)" \
		--allow-network-next-phase="$(or $(ALLOW_NETWORK_NEXT_PHASE),yes)" \
		--allow-raw-match-data-write-future-phase="$(or $(ALLOW_RAW_MATCH_DATA_WRITE_FUTURE_PHASE),yes)" \
		--allow-network-this-phase="$(or $(ALLOW_NETWORK_THIS_PHASE),no)" \
		--allow-db-write-this-phase="$(or $(ALLOW_DB_WRITE_THIS_PHASE),no)" \
		--allow-raw-match-data-write-this-phase="$(or $(ALLOW_RAW_MATCH_DATA_WRITE_THIS_PHASE),no)" \
		--allow-matches-write="$(or $(ALLOW_MATCHES_WRITE),no)" \
		--allow-parser-features="$(or $(ALLOW_PARSER_FEATURES),no)" \
		--allow-training="$(or $(ALLOW_TRAINING),no)" \
		--allow-prediction="$(or $(ALLOW_PREDICTION),no)" \
		--final-human-confirmation="$(or $(FINAL_HUMAN_CONFIRMATION),yes)"

data-l2-remaining-raw-match-data-acquisition-preflight: ## L2 remaining raw_match_data preflight. Phase 5.19L2. Recaptures 7 payloads, no DB write.
	@if [ -z "$(SOURCE)" ] || [ -z "$(LEAGUE_ID)" ] || [ -z "$(ROUTE)" ]; then \
		echo "ERROR: provide SOURCE=fotmob LEAGUE_ID=53 ROUTE=html_hydration"; \
		exit 1; \
	fi
	$(COMPOSE_DEV) exec -T dev node scripts/ops/l2_remaining_raw_match_data_acquisition_preflight.js \
		--source="$(SOURCE)" \
		--league-id="$(LEAGUE_ID)" \
		--season="$(or $(SEASON),2025/2026)" \
		--date="$(or $(DATE),2026-05-10)" \
		--route="$(ROUTE)" \
		--remaining-external-ids="$(or $(REMAINING_EXTERNAL_IDS),4830747,4830748,4830750,4830751,4830752,4830753,4830754)" \
		--expected-target-count="$(or $(EXPECTED_TARGET_COUNT),7)" \
		--network-authorization="$(or $(NETWORK_AUTHORIZATION),yes)" \
		--live-preview-authorization="$(or $(LIVE_PREVIEW_AUTHORIZATION),yes)" \
		--allow-db-write="$(or $(ALLOW_DB_WRITE),no)" \
		--allow-raw-match-data-write="$(or $(ALLOW_RAW_MATCH_DATA_WRITE),no)" \
		--allow-matches-write="$(or $(ALLOW_MATCHES_WRITE),no)" \
		--allow-parser-features="$(or $(ALLOW_PARSER_FEATURES),no)" \
		--allow-training="$(or $(ALLOW_TRAINING),no)" \
		--allow-prediction="$(or $(ALLOW_PREDICTION),no)" \
		--concurrency="$(or $(CONCURRENCY),1)" \
		--retry="$(or $(RETRY),0)" \
		--print-body="$(or $(PRINT_BODY),no)" \
		--save-body="$(or $(SAVE_BODY),no)"

data-l2-remaining-raw-match-data-write: ## L2 controlled remaining raw_match_data write. Phase 5.20L2F. Single transaction, stable baselines, raw_match_data only, rows=7.
	@if [ -z "$(SOURCE)" ] || [ -z "$(LEAGUE_ID)" ] || [ -z "$(ROUTE)" ] || [ -z "$(HASH_STRATEGY)" ] || [ -z "$(BASELINE_RAW_DATA_HASHES)" ] || [ -z "$(DATA_VERSION)" ]; then \
		echo "ERROR: provide SOURCE=fotmob LEAGUE_ID=53 ROUTE=html_hydration HASH_STRATEGY=stable_raw_payload_v1 BASELINE_RAW_DATA_HASHES=<7 Phase 5.20L2E hashes> DATA_VERSION=fotmob_html_hyd_v1"; \
		exit 1; \
	fi
	$(COMPOSE_DEV) exec -T dev node scripts/ops/l2_remaining_raw_match_data_write.js \
		--source="$(SOURCE)" \
		--league-id="$(LEAGUE_ID)" \
		--season="$(or $(SEASON),2025/2026)" \
		--date="$(or $(DATE),2026-05-10)" \
		--route="$(ROUTE)" \
		--remaining-external-ids="$(or $(REMAINING_EXTERNAL_IDS),4830747,4830748,4830750,4830751,4830752,4830753,4830754)" \
		--expected-target-count="$(or $(EXPECTED_TARGET_COUNT),7)" \
		--hash-strategy="$(HASH_STRATEGY)" \
		--baseline-raw-data-hashes="$(BASELINE_RAW_DATA_HASHES)" \
		--data-version="$(DATA_VERSION)" \
		--network-authorization="$(or $(NETWORK_AUTHORIZATION),no)" \
		--live-preview-authorization="$(or $(LIVE_PREVIEW_AUTHORIZATION),no)" \
		--final-db-write-confirmation="$(or $(FINAL_DB_WRITE_CONFIRMATION),no)" \
		--allow-db-write="$(or $(ALLOW_DB_WRITE),no)" \
		--allow-raw-match-data-write="$(or $(ALLOW_RAW_MATCH_DATA_WRITE),no)" \
		--allow-matches-write="$(or $(ALLOW_MATCHES_WRITE),no)" \
		--allow-parser-features="$(or $(ALLOW_PARSER_FEATURES),no)" \
		--allow-training="$(or $(ALLOW_TRAINING),no)" \
		--allow-prediction="$(or $(ALLOW_PREDICTION),no)" \
		--allow-browser-runtime="$(or $(ALLOW_BROWSER_RUNTIME),no)" \
		--allow-proxy-runtime="$(or $(ALLOW_PROXY_RUNTIME),no)" \
		--concurrency="$(or $(CONCURRENCY),1)" \
		--retry="$(or $(RETRY),0)" \
		--print-body="$(or $(PRINT_BODY),no)" \
		--save-body="$(or $(SAVE_BODY),no)" \
		--bulk="$(or $(BULK),no)" \
		--commit="$(or $(COMMIT),no)" \
		--execute="$(or $(EXECUTE),no)"

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

data-raw-match-data-completeness-audit: ## Run SELECT-only raw_match_data completeness/source fidelity audit. No network, DB write, parser/features, training, or prediction.
	@if [ -z "$(SOURCE)" ] || [ -z "$(EXPECTED_RAW_COUNT)" ] || [ -z "$(EXPECTED_SEEDED_RAW_COUNT)" ]; then \
		echo "ERROR: provide SOURCE=fotmob EXPECTED_RAW_COUNT=10 EXPECTED_SEEDED_RAW_COUNT=8"; \
		exit 1; \
	fi
	$(COMPOSE_DEV) exec -T dev node scripts/ops/raw_match_data_completeness_fidelity_audit.js \
		--source="$(SOURCE)" \
		--expected-raw-count="$(EXPECTED_RAW_COUNT)" \
		--expected-seeded-raw-count="$(EXPECTED_SEEDED_RAW_COUNT)" \
		--allow-network="$(or $(ALLOW_NETWORK),no)" \
		--allow-db-write="$(or $(ALLOW_DB_WRITE),no)" \
		--print-full-raw-data="$(or $(PRINT_FULL_RAW_DATA),no)" \
		--save-full-raw-data="$(or $(SAVE_FULL_RAW_DATA),no)"

data-html-hydration-source-fidelity-live-compare: ## Run Phase 5.21L2B single-target live source fidelity compare. No DB/raw write or full body/json print/save.
	@if [ -z "$(SOURCE)" ] || [ -z "$(ROUTE)" ] || [ -z "$(MATCH_ID)" ] || [ -z "$(EXTERNAL_ID)" ] || [ -z "$(HOME_TEAM)" ] || [ -z "$(AWAY_TEAM)" ]; then \
		echo "ERROR: provide SOURCE=fotmob ROUTE=html_hydration MATCH_ID=53_20252026_4830747 EXTERNAL_ID=4830747 HOME_TEAM=Auxerre AWAY_TEAM=Nice"; \
		exit 1; \
	fi
	$(COMPOSE_DEV) exec -T dev node scripts/ops/html_hydration_source_fidelity_live_compare.js \
		--source="$(SOURCE)" \
		--route="$(ROUTE)" \
		--match-id="$(MATCH_ID)" \
		--external-id="$(EXTERNAL_ID)" \
		--home-team="$(HOME_TEAM)" \
		--away-team="$(AWAY_TEAM)" \
		--network-authorization="$(or $(NETWORK_AUTHORIZATION),no)" \
		--live-compare-authorization="$(or $(LIVE_COMPARE_AUTHORIZATION),no)" \
		--allow-db-write="$(or $(ALLOW_DB_WRITE),no)" \
		--allow-raw-match-data-write="$(or $(ALLOW_RAW_MATCH_DATA_WRITE),no)" \
		--allow-matches-write="$(or $(ALLOW_MATCHES_WRITE),no)" \
		--allow-parser-features="$(or $(ALLOW_PARSER_FEATURES),no)" \
		--allow-training="$(or $(ALLOW_TRAINING),no)" \
		--allow-prediction="$(or $(ALLOW_PREDICTION),no)" \
		--concurrency="$(or $(CONCURRENCY),1)" \
		--retry="$(or $(RETRY),0)" \
		--print-body="$(or $(PRINT_BODY),no)" \
		--save-body="$(or $(SAVE_BODY),no)" \
			--print-full-json="$(or $(PRINT_FULL_JSON),no)" \
			--save-full-json="$(or $(SAVE_FULL_JSON),no)"

data-raw-storage-strategy-revision-plan: ## Run Phase 5.21L2C raw storage strategy planning. No network, DB write, migration, parser/features, training, or prediction.
	@if [ -z "$(SOURCE)" ] || [ -z "$(CURRENT_VERSION)" ] || [ -z "$(RECOMMENDED_VERSION)" ] || [ -z "$(RECOMMENDED_HASH_STRATEGY)" ]; then \
		echo "ERROR: provide SOURCE=fotmob CURRENT_VERSION=fotmob_html_hyd_v1 RECOMMENDED_VERSION=fotmob_pageprops_v2 RECOMMENDED_HASH_STRATEGY=stable_pageprops_payload_v1"; \
		exit 1; \
	fi
	$(COMPOSE_DEV) exec -T dev node scripts/ops/raw_storage_strategy_revision_plan.js \
		--source="$(SOURCE)" \
		--current-version="$(CURRENT_VERSION)" \
		--recommended-version="$(RECOMMENDED_VERSION)" \
		--recommended-hash-strategy="$(RECOMMENDED_HASH_STRATEGY)" \
		--allow-network="$(or $(ALLOW_NETWORK),no)" \
		--allow-db-write="$(or $(ALLOW_DB_WRITE),no)" \
			--allow-migration="$(or $(ALLOW_MIGRATION),no)" \
			--allow-parser-features="$(or $(ALLOW_PARSER_FEATURES),no)" \
			--allow-training="$(or $(ALLOW_TRAINING),no)" \
			--allow-prediction="$(or $(ALLOW_PREDICTION),no)"

data-pageprops-v2-no-write-preview: ## Run Phase 5.21L2D single-target pageProps v2 no-write preview. No DB/raw write or full body/json print/save.
	@if [ -z "$(SOURCE)" ] || [ -z "$(ROUTE)" ] || [ -z "$(MATCH_ID)" ] || [ -z "$(EXTERNAL_ID)" ] || [ -z "$(HOME_TEAM)" ] || [ -z "$(AWAY_TEAM)" ] || [ -z "$(CANDIDATE_VERSION)" ] || [ -z "$(HASH_STRATEGY)" ]; then \
		echo "ERROR: provide SOURCE=fotmob ROUTE=html_hydration MATCH_ID=53_20252026_4830747 EXTERNAL_ID=4830747 HOME_TEAM=Auxerre AWAY_TEAM=Nice CANDIDATE_VERSION=fotmob_pageprops_v2 HASH_STRATEGY=stable_pageprops_payload_v1"; \
		exit 1; \
	fi
	$(COMPOSE_DEV) exec -T dev node scripts/ops/pageprops_v2_no_write_preview.js \
		--source="$(SOURCE)" \
		--route="$(ROUTE)" \
		--match-id="$(MATCH_ID)" \
		--external-id="$(EXTERNAL_ID)" \
		--home-team="$(HOME_TEAM)" \
		--away-team="$(AWAY_TEAM)" \
		--candidate-version="$(CANDIDATE_VERSION)" \
		--hash-strategy="$(HASH_STRATEGY)" \
		--network-authorization="$(or $(NETWORK_AUTHORIZATION),no)" \
		--pageprops-v2-preview-authorization="$(or $(PAGEPROPS_V2_PREVIEW_AUTHORIZATION),no)" \
		--allow-db-write="$(or $(ALLOW_DB_WRITE),no)" \
		--allow-raw-match-data-write="$(or $(ALLOW_RAW_MATCH_DATA_WRITE),no)" \
		--allow-matches-write="$(or $(ALLOW_MATCHES_WRITE),no)" \
		--allow-parser-features="$(or $(ALLOW_PARSER_FEATURES),no)" \
		--allow-training="$(or $(ALLOW_TRAINING),no)" \
		--allow-prediction="$(or $(ALLOW_PREDICTION),no)" \
		--concurrency="$(or $(CONCURRENCY),1)" \
		--retry="$(or $(RETRY),0)" \
		--print-body="$(or $(PRINT_BODY),no)" \
		--save-body="$(or $(SAVE_BODY),no)" \
		--print-full-json="$(or $(PRINT_FULL_JSON),no)" \
		--save-full-json="$(or $(SAVE_FULL_JSON),no)"

data-pageprops-v2-controlled-write-plan: ## Run Phase 5.21L2E pageProps v2 controlled write planning. No network, DB write, migration, raw write, parser/features, training, or prediction.
	@if [ -z "$(SOURCE)" ] || [ -z "$(CURRENT_VERSION)" ] || [ -z "$(TARGET_VERSION)" ] || [ -z "$(HASH_STRATEGY)" ] || [ -z "$(TARGET_MATCH_ID)" ] || [ -z "$(TARGET_EXTERNAL_ID)" ]; then \
		echo "ERROR: provide SOURCE=fotmob CURRENT_VERSION=fotmob_html_hyd_v1 TARGET_VERSION=fotmob_pageprops_v2 HASH_STRATEGY=stable_pageprops_payload_v1 TARGET_MATCH_ID=53_20252026_4830747 TARGET_EXTERNAL_ID=4830747"; \
		exit 1; \
	fi
	$(COMPOSE_DEV) exec -T dev node scripts/ops/pageprops_v2_controlled_write_plan.js \
		--source="$(SOURCE)" \
		--current-version="$(CURRENT_VERSION)" \
		--target-version="$(TARGET_VERSION)" \
		--hash-strategy="$(HASH_STRATEGY)" \
		--target-match-id="$(TARGET_MATCH_ID)" \
		--target-external-id="$(TARGET_EXTERNAL_ID)" \
		--allow-network="$(or $(ALLOW_NETWORK),no)" \
		--allow-db-write="$(or $(ALLOW_DB_WRITE),no)" \
		--allow-migration="$(or $(ALLOW_MIGRATION),no)" \
		--allow-raw-match-data-write="$(or $(ALLOW_RAW_MATCH_DATA_WRITE),no)" \
		--allow-parser-features="$(or $(ALLOW_PARSER_FEATURES),no)" \
		--allow-training="$(or $(ALLOW_TRAINING),no)" \
		--allow-prediction="$(or $(ALLOW_PREDICTION),no)"

data-raw-match-data-versioned-schema-migration-preflight: ## Run Phase 5.21L2F raw_match_data versioned schema migration preflight. No DB write, ALTER TABLE, migration, raw write, parser/features, training, or prediction.
	@if [ -z "$(SOURCE)" ] || [ -z "$(TABLE)" ] || [ -z "$(CURRENT_UNIQUE)" ] || [ -z "$(TARGET_UNIQUE)" ] || [ -z "$(TARGET_VERSION)" ]; then \
		echo "ERROR: provide SOURCE=fotmob TABLE=raw_match_data CURRENT_UNIQUE=match_id TARGET_UNIQUE=match_id,data_version TARGET_VERSION=fotmob_pageprops_v2"; \
		exit 1; \
	fi
	$(COMPOSE_DEV) exec -T dev node scripts/ops/raw_match_data_versioned_schema_migration_preflight.js \
		--source="$(SOURCE)" \
		--table="$(TABLE)" \
		--current-unique="$(CURRENT_UNIQUE)" \
		--target-unique="$(TARGET_UNIQUE)" \
		--target-version="$(TARGET_VERSION)" \
		--allow-db-write="$(or $(ALLOW_DB_WRITE),no)" \
		--allow-migration="$(or $(ALLOW_MIGRATION),no)" \
		--allow-raw-match-data-write="$(or $(ALLOW_RAW_MATCH_DATA_WRITE),no)" \
		--allow-parser-features="$(or $(ALLOW_PARSER_FEATURES),no)" \
		--allow-training="$(or $(ALLOW_TRAINING),no)" \
		--allow-prediction="$(or $(ALLOW_PREDICTION),no)"

data-raw-match-data-versioned-schema-migration-execute: ## Run Phase 5.21L2G controlled raw_match_data schema migration. Schema-only ALTER, no raw row write, FotMob access, parser/features, training, or prediction.
	@if [ -z "$(SOURCE)" ] || [ -z "$(TABLE)" ] || [ -z "$(CURRENT_UNIQUE)" ] || [ -z "$(TARGET_UNIQUE)" ] || [ -z "$(CURRENT_CONSTRAINT)" ] || [ -z "$(TARGET_CONSTRAINT)" ]; then \
		echo "ERROR: provide SOURCE=fotmob TABLE=raw_match_data CURRENT_UNIQUE=match_id TARGET_UNIQUE=match_id,data_version CURRENT_CONSTRAINT=raw_match_data_match_id_key TARGET_CONSTRAINT=raw_match_data_match_id_data_version_key"; \
		exit 1; \
	fi
	$(COMPOSE_DEV) exec -T dev node scripts/ops/raw_match_data_versioned_schema_migration_execute.js \
		--source="$(SOURCE)" \
		--table="$(TABLE)" \
		--current-unique="$(CURRENT_UNIQUE)" \
		--target-unique="$(TARGET_UNIQUE)" \
		--current-constraint="$(CURRENT_CONSTRAINT)" \
		--target-constraint="$(TARGET_CONSTRAINT)" \
		--final-schema-migration-confirmation="$(or $(FINAL_SCHEMA_MIGRATION_CONFIRMATION),no)" \
		--allow-db-write="$(or $(ALLOW_DB_WRITE),no)" \
		--allow-schema-migration="$(or $(ALLOW_SCHEMA_MIGRATION),no)" \
		--allow-alter-table="$(or $(ALLOW_ALTER_TABLE),no)" \
		--allow-raw-match-data-write="$(or $(ALLOW_RAW_MATCH_DATA_WRITE),no)" \
		--allow-matches-write="$(or $(ALLOW_MATCHES_WRITE),no)" \
		--allow-parser-features="$(or $(ALLOW_PARSER_FEATURES),no)" \
		--allow-training="$(or $(ALLOW_TRAINING),no)" \
		--allow-prediction="$(or $(ALLOW_PREDICTION),no)"

data-raw-match-data-version-compatibility-audit: ## Run Phase 5.21L2H version-aware raw_match_data compatibility audit. SELECT-only, no DB write, FotMob access, parser/features, training, or prediction.
	@if [ -z "$(SOURCE)" ] || [ -z "$(TABLE)" ] || [ -z "$(PREFERRED_VERSION)" ] || [ -z "$(FALLBACK_VERSION)" ]; then \
		echo "ERROR: provide SOURCE=fotmob TABLE=raw_match_data PREFERRED_VERSION=fotmob_pageprops_v2 FALLBACK_VERSION=fotmob_html_hyd_v1"; \
		exit 1; \
	fi
	$(COMPOSE_DEV) exec -T dev node scripts/ops/raw_match_data_version_compatibility_audit.js \
		--source="$(SOURCE)" \
		--table="$(TABLE)" \
		--preferred-version="$(PREFERRED_VERSION)" \
		--fallback-version="$(FALLBACK_VERSION)" \
		--allow-db-write="$(or $(ALLOW_DB_WRITE),no)" \
		--allow-raw-match-data-write="$(or $(ALLOW_RAW_MATCH_DATA_WRITE),no)" \
		--allow-parser-features="$(or $(ALLOW_PARSER_FEATURES),no)" \
		--allow-training="$(or $(ALLOW_TRAINING),no)" \
		--allow-prediction="$(or $(ALLOW_PREDICTION),no)"

data-pageprops-v2-single-target-write-preflight: ## Run Phase 5.21L2I pageProps v2 single-target write preflight. Live recapture, no DB/raw write.
	@if [ -z "$(SOURCE)" ] || [ -z "$(ROUTE)" ] || [ -z "$(MATCH_ID)" ] || [ -z "$(EXTERNAL_ID)" ] || [ -z "$(HOME_TEAM)" ] || [ -z "$(AWAY_TEAM)" ] || [ -z "$(CANDIDATE_VERSION)" ] || [ -z "$(HASH_STRATEGY)" ] || [ -z "$(PREVIOUS_PREVIEW_HASH)" ]; then \
		echo "ERROR: provide SOURCE=fotmob ROUTE=html_hydration MATCH_ID=53_20252026_4830747 EXTERNAL_ID=4830747 HOME_TEAM=Auxerre AWAY_TEAM=Nice CANDIDATE_VERSION=fotmob_pageprops_v2 HASH_STRATEGY=stable_pageprops_payload_v1 PREVIOUS_PREVIEW_HASH=<64-char-hash>"; \
		exit 1; \
	fi
	$(COMPOSE_DEV) exec -T dev node scripts/ops/pageprops_v2_single_target_write_preflight.js \
		--source="$(SOURCE)" \
		--route="$(ROUTE)" \
		--match-id="$(MATCH_ID)" \
		--external-id="$(EXTERNAL_ID)" \
		--home-team="$(HOME_TEAM)" \
		--away-team="$(AWAY_TEAM)" \
		--candidate-version="$(CANDIDATE_VERSION)" \
		--hash-strategy="$(HASH_STRATEGY)" \
		--previous-preview-hash="$(PREVIOUS_PREVIEW_HASH)" \
		--network-authorization="$(or $(NETWORK_AUTHORIZATION),no)" \
		--pageprops-v2-write-preflight-authorization="$(or $(PAGEPROPS_V2_WRITE_PREFLIGHT_AUTHORIZATION),no)" \
		--allow-db-write="$(or $(ALLOW_DB_WRITE),no)" \
		--allow-raw-match-data-write="$(or $(ALLOW_RAW_MATCH_DATA_WRITE),no)" \
		--allow-matches-write="$(or $(ALLOW_MATCHES_WRITE),no)" \
		--allow-parser-features="$(or $(ALLOW_PARSER_FEATURES),no)" \
		--allow-training="$(or $(ALLOW_TRAINING),no)" \
		--allow-prediction="$(or $(ALLOW_PREDICTION),no)" \
		--concurrency="$(or $(CONCURRENCY),1)" \
		--retry="$(or $(RETRY),0)" \
		--print-body="$(or $(PRINT_BODY),no)" \
		--save-body="$(or $(SAVE_BODY),no)" \
		--print-full-json="$(or $(PRINT_FULL_JSON),no)" \
		--save-full-json="$(or $(SAVE_FULL_JSON),no)"

data-pageprops-v2-single-target-controlled-write: ## Run Phase 5.21L2J pageProps v2 single-target controlled write. Writes exactly one raw_match_data v2 row after hash gate.
	@if [ -z "$(SOURCE)" ] || [ -z "$(ROUTE)" ] || [ -z "$(MATCH_ID)" ] || [ -z "$(EXTERNAL_ID)" ] || [ -z "$(HOME_TEAM)" ] || [ -z "$(AWAY_TEAM)" ] || [ -z "$(CANDIDATE_VERSION)" ] || [ -z "$(HASH_STRATEGY)" ] || [ -z "$(BASELINE_PAGEPROPS_HASH)" ]; then \
		echo "ERROR: provide SOURCE=fotmob ROUTE=html_hydration MATCH_ID=53_20252026_4830747 EXTERNAL_ID=4830747 HOME_TEAM=Auxerre AWAY_TEAM=Nice CANDIDATE_VERSION=fotmob_pageprops_v2 HASH_STRATEGY=stable_pageprops_payload_v1 BASELINE_PAGEPROPS_HASH=<64-char-hash>"; \
		exit 1; \
	fi
	$(COMPOSE_DEV) exec -T dev node scripts/ops/pageprops_v2_single_target_controlled_write.js \
		--source="$(SOURCE)" \
		--route="$(ROUTE)" \
		--match-id="$(MATCH_ID)" \
		--external-id="$(EXTERNAL_ID)" \
		--home-team="$(HOME_TEAM)" \
		--away-team="$(AWAY_TEAM)" \
		--candidate-version="$(CANDIDATE_VERSION)" \
		--hash-strategy="$(HASH_STRATEGY)" \
		--baseline-pageprops-hash="$(BASELINE_PAGEPROPS_HASH)" \
		--network-authorization="$(or $(NETWORK_AUTHORIZATION),no)" \
		--final-db-write-confirmation="$(or $(FINAL_DB_WRITE_CONFIRMATION),no)" \
		--allow-db-write="$(or $(ALLOW_DB_WRITE),no)" \
		--allow-raw-match-data-write="$(or $(ALLOW_RAW_MATCH_DATA_WRITE),no)" \
		--allow-matches-write="$(or $(ALLOW_MATCHES_WRITE),no)" \
		--allow-parser-features="$(or $(ALLOW_PARSER_FEATURES),no)" \
		--allow-training="$(or $(ALLOW_TRAINING),no)" \
		--allow-prediction="$(or $(ALLOW_PREDICTION),no)" \
		--concurrency="$(or $(CONCURRENCY),1)" \
		--retry="$(or $(RETRY),0)" \
		--print-body="$(or $(PRINT_BODY),no)" \
		--save-body="$(or $(SAVE_BODY),no)" \
		--print-full-json="$(or $(PRINT_FULL_JSON),no)" \
		--save-full-json="$(or $(SAVE_FULL_JSON),no)"

data-pageprops-v2-post-write-canonical-read-verification: ## Run Phase 5.21L2K pageProps v2 canonical read verification. SELECT-only, no network/write/parser.
	@if [ -z "$(SOURCE)" ] || [ -z "$(TABLE)" ] || [ -z "$(TARGET_MATCH_ID)" ] || [ -z "$(TARGET_EXTERNAL_ID)" ] || [ -z "$(EXPECTED_TARGET_VERSION)" ] || [ -z "$(FALLBACK_VERSION)" ] || [ -z "$(EXPECTED_TARGET_HASH)" ]; then \
		echo "ERROR: provide SOURCE=fotmob TABLE=raw_match_data TARGET_MATCH_ID=53_20252026_4830747 TARGET_EXTERNAL_ID=4830747 EXPECTED_TARGET_VERSION=fotmob_pageprops_v2 FALLBACK_VERSION=fotmob_html_hyd_v1 EXPECTED_TARGET_HASH=<64-char-hash>"; \
		exit 1; \
	fi
	$(COMPOSE_DEV) exec -T dev node scripts/ops/pageprops_v2_post_write_canonical_read_verification.js \
		--source="$(SOURCE)" \
		--table="$(TABLE)" \
		--target-match-id="$(TARGET_MATCH_ID)" \
		--target-external-id="$(TARGET_EXTERNAL_ID)" \
		--expected-target-version="$(EXPECTED_TARGET_VERSION)" \
		--fallback-version="$(FALLBACK_VERSION)" \
		--expected-target-hash="$(EXPECTED_TARGET_HASH)" \
		--allow-db-write="$(or $(ALLOW_DB_WRITE),no)" \
		--allow-network="$(or $(ALLOW_NETWORK),no)" \
		--allow-parser-features="$(or $(ALLOW_PARSER_FEATURES),no)" \
		--allow-training="$(or $(ALLOW_TRAINING),no)" \
		--allow-prediction="$(or $(ALLOW_PREDICTION),no)"

data-remaining-seeded-pageprops-v2-acquisition-preflight: ## Run Phase 5.21L2L remaining seeded pageProps v2 acquisition preflight. Live sequential no-write recapture.
	@if [ -z "$(SOURCE)" ] || [ -z "$(ROUTE)" ] || [ -z "$(TARGET_EXTERNAL_IDS)" ] || [ -z "$(CANDIDATE_VERSION)" ] || [ -z "$(HASH_STRATEGY)" ]; then \
		echo "ERROR: provide SOURCE=fotmob ROUTE=html_hydration TARGET_EXTERNAL_IDS=4830746,4830748,4830750,4830751,4830752,4830753,4830754 CANDIDATE_VERSION=fotmob_pageprops_v2 HASH_STRATEGY=stable_pageprops_payload_v1"; \
		exit 1; \
	fi
	$(COMPOSE_DEV) exec -T dev node scripts/ops/remaining_seeded_pageprops_v2_acquisition_preflight.js \
		--source="$(SOURCE)" \
		--route="$(ROUTE)" \
		--target-external-ids="$(TARGET_EXTERNAL_IDS)" \
		--candidate-version="$(CANDIDATE_VERSION)" \
		--hash-strategy="$(HASH_STRATEGY)" \
		--network-authorization="$(or $(NETWORK_AUTHORIZATION),no)" \
		--pageprops-v2-remaining-preflight-authorization="$(or $(PAGEPROPS_V2_REMAINING_PREFLIGHT_AUTHORIZATION),no)" \
		--allow-db-write="$(or $(ALLOW_DB_WRITE),no)" \
		--allow-raw-match-data-write="$(or $(ALLOW_RAW_MATCH_DATA_WRITE),no)" \
		--allow-matches-write="$(or $(ALLOW_MATCHES_WRITE),no)" \
		--allow-parser-features="$(or $(ALLOW_PARSER_FEATURES),no)" \
		--allow-training="$(or $(ALLOW_TRAINING),no)" \
		--allow-prediction="$(or $(ALLOW_PREDICTION),no)" \
		--concurrency="$(or $(CONCURRENCY),1)" \
		--retry="$(or $(RETRY),0)" \
		--print-body="$(or $(PRINT_BODY),no)" \
		--save-body="$(or $(SAVE_BODY),no)" \
		--print-full-json="$(or $(PRINT_FULL_JSON),no)" \
		--save-full-json="$(or $(SAVE_FULL_JSON),no)"

data-remaining-seeded-pageprops-v2-controlled-write: ## Run Phase 5.21L2M remaining seeded pageProps v2 controlled write. Writes exactly seven hash-gated v2 rows.
	@if [ -z "$(SOURCE)" ] || [ -z "$(ROUTE)" ] || [ -z "$(BASELINE_HASHES)" ] || [ -z "$(CANDIDATE_VERSION)" ] || [ -z "$(HASH_STRATEGY)" ]; then \
			echo "ERROR: provide SOURCE=fotmob ROUTE=html_hydration BASELINE_HASHES='<json>' CANDIDATE_VERSION=fotmob_pageprops_v2 HASH_STRATEGY=stable_pageprops_payload_v1"; \
		exit 1; \
	fi
	$(COMPOSE_DEV) exec -T dev node scripts/ops/remaining_seeded_pageprops_v2_controlled_write.js \
		--source="$(SOURCE)" \
		--route="$(ROUTE)" \
		--baseline-hashes='$(BASELINE_HASHES)' \
		--candidate-version="$(CANDIDATE_VERSION)" \
		--hash-strategy="$(HASH_STRATEGY)" \
		--network-authorization="$(or $(NETWORK_AUTHORIZATION),no)" \
		--final-db-write-confirmation="$(or $(FINAL_DB_WRITE_CONFIRMATION),no)" \
		--allow-db-write="$(or $(ALLOW_DB_WRITE),no)" \
		--allow-raw-match-data-write="$(or $(ALLOW_RAW_MATCH_DATA_WRITE),no)" \
		--allow-matches-write="$(or $(ALLOW_MATCHES_WRITE),no)" \
		--allow-parser-features="$(or $(ALLOW_PARSER_FEATURES),no)" \
		--allow-training="$(or $(ALLOW_TRAINING),no)" \
		--allow-prediction="$(or $(ALLOW_PREDICTION),no)" \
		--concurrency="$(or $(CONCURRENCY),1)" \
		--retry="$(or $(RETRY),0)" \
		--print-body="$(or $(PRINT_BODY),no)" \
		--save-body="$(or $(SAVE_BODY),no)" \
			--print-full-json="$(or $(PRINT_FULL_JSON),no)" \
			--save-full-json="$(or $(SAVE_FULL_JSON),no)"

data-all-seeded-pageprops-v2-canonical-read-verification: ## Run Phase 5.21L2N all-seeded pageProps v2 canonical read verification. SELECT-only, no network/write/parser.
	@if [ -z "$(SOURCE)" ] || [ -z "$(TABLE)" ] || [ -z "$(TARGET_EXTERNAL_IDS)" ] || [ -z "$(EXPECTED_TARGET_VERSION)" ] || [ -z "$(FALLBACK_VERSION)" ] || [ -z "$(EXPECTED_HASHES)" ]; then \
		echo "ERROR: provide SOURCE=fotmob TABLE=raw_match_data TARGET_EXTERNAL_IDS=4830746,4830747,4830748,4830750,4830751,4830752,4830753,4830754 EXPECTED_TARGET_VERSION=fotmob_pageprops_v2 FALLBACK_VERSION=fotmob_html_hyd_v1 EXPECTED_HASHES='<json>'"; \
		exit 1; \
	fi
	$(COMPOSE_DEV) exec -T dev node scripts/ops/all_seeded_pageprops_v2_canonical_read_verification.js \
		--source="$(SOURCE)" \
		--table="$(TABLE)" \
		--target-external-ids="$(TARGET_EXTERNAL_IDS)" \
		--expected-target-version="$(EXPECTED_TARGET_VERSION)" \
		--fallback-version="$(FALLBACK_VERSION)" \
		--expected-hashes='$(EXPECTED_HASHES)' \
		--allow-db-write="$(or $(ALLOW_DB_WRITE),no)" \
			--allow-network="$(or $(ALLOW_NETWORK),no)" \
			--allow-parser-features="$(or $(ALLOW_PARSER_FEATURES),no)" \
			--allow-training="$(or $(ALLOW_TRAINING),no)" \
			--allow-prediction="$(or $(ALLOW_PREDICTION),no)"

data-pageprops-v2-raw-completeness-audit: ## Run Phase 5.21L2O pageProps v2 raw inventory/completeness audit. SELECT-only, no network/write/parser.
	@if [ -z "$(SOURCE)" ] || [ -z "$(TABLE)" ] || [ -z "$(TARGET_EXTERNAL_IDS)" ] || [ -z "$(DATA_VERSION)" ]; then \
		echo "ERROR: provide SOURCE=fotmob TABLE=raw_match_data TARGET_EXTERNAL_IDS=4830746,4830747,4830748,4830750,4830751,4830752,4830753,4830754 DATA_VERSION=fotmob_pageprops_v2"; \
		exit 1; \
	fi
	$(COMPOSE_DEV) exec -T dev node scripts/ops/pageprops_v2_raw_completeness_audit.js \
		--source="$(SOURCE)" \
		--table="$(TABLE)" \
		--target-external-ids="$(TARGET_EXTERNAL_IDS)" \
		--data-version="$(DATA_VERSION)" \
		--allow-db-write="$(or $(ALLOW_DB_WRITE),no)" \
		--allow-network="$(or $(ALLOW_NETWORK),no)" \
		--allow-parser-features="$(or $(ALLOW_PARSER_FEATURES),no)" \
		--allow-training="$(or $(ALLOW_TRAINING),no)" \
		--allow-prediction="$(or $(ALLOW_PREDICTION),no)" \
		--print-full-raw-data="$(or $(PRINT_FULL_RAW_DATA),no)" \
		--save-full-raw-data="$(or $(SAVE_FULL_RAW_DATA),no)"

data-pageprops-v2-parser-boundary-leakage-plan: ## Run Phase 5.21L2P parser boundary / leakage-safe planning. Planning-only, no network/write/parser/features/training.
	@if [ -z "$(SOURCE)" ] || [ -z "$(RAW_VERSION)" ] || [ -z "$(PLANNING_SCOPE)" ]; then \
		echo "ERROR: provide SOURCE=fotmob RAW_VERSION=fotmob_pageprops_v2 PLANNING_SCOPE=parser-boundary-leakage-acquisition-odds-roadmap"; \
		exit 1; \
	fi
	$(COMPOSE_DEV) exec -T dev node scripts/ops/pageprops_v2_parser_boundary_leakage_plan.js \
		--source="$(SOURCE)" \
		--raw-version="$(RAW_VERSION)" \
		--planning-scope="$(PLANNING_SCOPE)" \
		--allow-db-write="$(or $(ALLOW_DB_WRITE),no)" \
		--allow-network="$(or $(ALLOW_NETWORK),no)" \
		--allow-parser-implementation="$(or $(ALLOW_PARSER_IMPLEMENTATION),no)" \
		--allow-feature-extraction="$(or $(ALLOW_FEATURE_EXTRACTION),no)" \
		--allow-training="$(or $(ALLOW_TRAINING),no)" \
		--allow-prediction="$(or $(ALLOW_PREDICTION),no)"

data-large-scale-pageprops-v2-acquisition-strategy-plan: ## Run Phase 5.21L2Q large-scale pageProps v2 acquisition strategy planning. Planning-only, no network/raw acquisition/write/parser/features/training.
	@if [ -z "$(SOURCE)" ] || [ -z "$(RAW_VERSION)" ] || [ -z "$(PLANNING_SCOPE)" ]; then \
		echo "ERROR: provide SOURCE=fotmob RAW_VERSION=fotmob_pageprops_v2 PLANNING_SCOPE=large-scale-acquisition-strategy"; \
		exit 1; \
	fi
	$(COMPOSE_DEV) exec -T dev node scripts/ops/large_scale_pageprops_v2_acquisition_strategy_plan.js \
		--source="$(SOURCE)" \
		--raw-version="$(RAW_VERSION)" \
		--planning-scope="$(PLANNING_SCOPE)" \
		--allow-db-write="$(or $(ALLOW_DB_WRITE),no)" \
		--allow-network="$(or $(ALLOW_NETWORK),no)" \
		--allow-raw-acquisition="$(or $(ALLOW_RAW_ACQUISITION),no)" \
		--allow-parser-implementation="$(or $(ALLOW_PARSER_IMPLEMENTATION),no)" \
		--allow-feature-extraction="$(or $(ALLOW_FEATURE_EXTRACTION),no)" \
		--allow-training="$(or $(ALLOW_TRAINING),no)" \
		--allow-prediction="$(or $(ALLOW_PREDICTION),no)"

data-large-scale-target-inventory-schema-readiness-audit: ## Run Phase 5.21L2R target inventory schema-readiness audit. Planning/SELECT-only, no network/raw acquisition/write/schema migration/parser/features/training.
	@if [ -z "$(SOURCE)" ] || [ -z "$(RAW_VERSION)" ] || [ -z "$(PLANNING_SCOPE)" ]; then \
		echo "ERROR: provide SOURCE=fotmob RAW_VERSION=fotmob_pageprops_v2 PLANNING_SCOPE=target-inventory-schema-readiness"; \
		exit 1; \
	fi
	$(COMPOSE_DEV) exec -T dev node scripts/ops/large_scale_target_inventory_schema_readiness_audit.js \
		--source="$(SOURCE)" \
		--raw-version="$(RAW_VERSION)" \
		--planning-scope="$(PLANNING_SCOPE)" \
		--allow-db-write="$(or $(ALLOW_DB_WRITE),no)" \
		--allow-network="$(or $(ALLOW_NETWORK),no)" \
		--allow-raw-acquisition="$(or $(ALLOW_RAW_ACQUISITION),no)" \
		--allow-schema-migration="$(or $(ALLOW_SCHEMA_MIGRATION),no)" \
		--allow-parser-implementation="$(or $(ALLOW_PARSER_IMPLEMENTATION),no)" \
		--allow-feature-extraction="$(or $(ALLOW_FEATURE_EXTRACTION),no)" \
		--allow-training="$(or $(ALLOW_TRAINING),no)" \
		--allow-prediction="$(or $(ALLOW_PREDICTION),no)"

data-single-league-small-batch-target-manifest-plan: ## Run Phase 5.21L2S single-league target manifest planning. Planning/SELECT-only, no network/raw acquisition/write/schema migration/parser/features/training, no invented targets.
	@if [ -z "$(SOURCE)" ] || [ -z "$(ROUTE)" ] || [ -z "$(RAW_VERSION)" ] || [ -z "$(HASH_STRATEGY)" ] || [ -z "$(LEAGUE_ID)" ] || [ -z "$(LEAGUE_NAME)" ] || [ -z "$(SEASON)" ] || [ -z "$(BATCH_ID)" ] || [ -z "$(BATCH_SIZE_POLICY)" ] || [ -z "$(PLANNING_SCOPE)" ]; then \
		echo "ERROR: provide SOURCE=fotmob ROUTE=html_hydration RAW_VERSION=fotmob_pageprops_v2 HASH_STRATEGY=stable_pageprops_payload_v1 LEAGUE_ID=53 LEAGUE_NAME='Ligue 1' SEASON=2025/2026 BATCH_ID=fotmob-pageprops-v2-ligue1-2025-2026-profile-001 BATCH_SIZE_POLICY=20-50 PLANNING_SCOPE=single-league-small-batch-target-manifest"; \
		exit 1; \
	fi
	$(COMPOSE_DEV) exec -T dev node scripts/ops/single_league_small_batch_target_manifest_plan.js \
		--source="$(SOURCE)" \
		--route="$(ROUTE)" \
		--raw-version="$(RAW_VERSION)" \
		--hash-strategy="$(HASH_STRATEGY)" \
		--league-id="$(LEAGUE_ID)" \
		--league-name="$(LEAGUE_NAME)" \
		--season="$(SEASON)" \
		--batch-id="$(BATCH_ID)" \
		--batch-size-policy="$(BATCH_SIZE_POLICY)" \
		--planning-scope="$(PLANNING_SCOPE)" \
		--allow-db-write="$(or $(ALLOW_DB_WRITE),no)" \
		--allow-network="$(or $(ALLOW_NETWORK),no)" \
		--allow-raw-acquisition="$(or $(ALLOW_RAW_ACQUISITION),no)" \
		--allow-schema-migration="$(or $(ALLOW_SCHEMA_MIGRATION),no)" \
		--allow-parser-implementation="$(or $(ALLOW_PARSER_IMPLEMENTATION),no)" \
		--allow-feature-extraction="$(or $(ALLOW_FEATURE_EXTRACTION),no)" \
		--allow-training="$(or $(ALLOW_TRAINING),no)" \
		--allow-prediction="$(or $(ALLOW_PREDICTION),no)"

data-single-league-target-discovery-source-inventory-preflight: ## Run Phase 5.21L2T0 authorized source inventory via existing L1 adapter. Network source inventory only, no DB/raw write, no match detail fetch.
	@if [ -z "$(SOURCE)" ] || [ -z "$(LEAGUE_ID)" ] || [ -z "$(LEAGUE_NAME)" ] || [ -z "$(SEASON)" ] || [ -z "$(ROUTE)" ] || [ -z "$(RAW_VERSION)" ] || [ -z "$(HASH_STRATEGY)" ] || [ -z "$(BATCH_ID)" ] || [ -z "$(TARGET_COUNT_MIN)" ] || [ -z "$(TARGET_COUNT_MAX)" ]; then \
		echo "ERROR: provide SOURCE=fotmob LEAGUE_ID=53 LEAGUE_NAME='Ligue 1' SEASON=2025/2026 ROUTE=source_inventory RAW_VERSION=fotmob_pageprops_v2 HASH_STRATEGY=stable_pageprops_payload_v1 BATCH_ID=fotmob-pageprops-v2-ligue1-2025-2026-profile-001 TARGET_COUNT_MIN=20 TARGET_COUNT_MAX=50"; \
		exit 1; \
	fi
	$(COMPOSE_DEV) exec -T dev node scripts/ops/single_league_target_discovery_source_inventory_preflight.js \
		--source="$(SOURCE)" \
		--league-id="$(LEAGUE_ID)" \
		--league-name="$(LEAGUE_NAME)" \
		--season="$(SEASON)" \
		--route="$(ROUTE)" \
		--raw-version="$(RAW_VERSION)" \
		--hash-strategy="$(HASH_STRATEGY)" \
		--batch-id="$(BATCH_ID)" \
		--target-count-min="$(TARGET_COUNT_MIN)" \
		--target-count-max="$(TARGET_COUNT_MAX)" \
		--network-authorization="$(or $(NETWORK_AUTHORIZATION),no)" \
		--source-inventory-authorization="$(or $(SOURCE_INVENTORY_AUTHORIZATION),no)" \
		--allow-db-write="$(or $(ALLOW_DB_WRITE),no)" \
		--allow-raw-match-data-write="$(or $(ALLOW_RAW_MATCH_DATA_WRITE),no)" \
		--allow-match-detail-fetch="$(or $(ALLOW_MATCH_DETAIL_FETCH),no)" \
		--allow-schema-migration="$(or $(ALLOW_SCHEMA_MIGRATION),no)" \
		--allow-parser-implementation="$(or $(ALLOW_PARSER_IMPLEMENTATION),no)" \
		--allow-feature-extraction="$(or $(ALLOW_FEATURE_EXTRACTION),no)" \
		--allow-training="$(or $(ALLOW_TRAINING),no)" \
		--allow-prediction="$(or $(ALLOW_PREDICTION),no)" \
		--allow-browser-runtime="$(or $(ALLOW_BROWSER_RUNTIME),no)" \
		--allow-proxy-runtime="$(or $(ALLOW_PROXY_RUNTIME),no)" \
		--concurrency="$(or $(CONCURRENCY),1)" \
		--retry="$(or $(RETRY),0)" \
			--print-full-body="$(or $(PRINT_FULL_BODY),no)" \
			--save-full-body="$(or $(SAVE_FULL_BODY),no)" \
			--print-full-json="$(or $(PRINT_FULL_JSON),no)" \
			--save-full-json="$(or $(SAVE_FULL_JSON),no)"

data-single-league-small-batch-pageprops-v2-preflight: ## Run Phase 5.21L2T single-league small-batch pageProps v2 no-write preflight. Updates manifest/report only.
	@if [ -z "$(MANIFEST)" ] || [ -z "$(SOURCE)" ] || [ -z "$(LEAGUE_ID)" ] || [ -z "$(LEAGUE_NAME)" ] || [ -z "$(SEASON)" ] || [ -z "$(ROUTE)" ] || [ -z "$(RAW_VERSION)" ] || [ -z "$(HASH_STRATEGY)" ] || [ -z "$(BATCH_ID)" ] || [ -z "$(TARGET_COUNT)" ]; then \
		echo "ERROR: provide MANIFEST=docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.proposal.json SOURCE=fotmob LEAGUE_ID=53 LEAGUE_NAME='Ligue 1' SEASON=2025/2026 ROUTE=html_hydration RAW_VERSION=fotmob_pageprops_v2 HASH_STRATEGY=stable_pageprops_payload_v1 BATCH_ID=fotmob-pageprops-v2-ligue1-2025-2026-profile-001 TARGET_COUNT=50"; \
		exit 1; \
	fi
	$(COMPOSE_DEV) exec -T dev node scripts/ops/single_league_small_batch_pageprops_v2_preflight.js \
		--manifest="$(MANIFEST)" \
		--source="$(SOURCE)" \
		--league-id="$(LEAGUE_ID)" \
		--league-name="$(LEAGUE_NAME)" \
		--season="$(SEASON)" \
		--route="$(ROUTE)" \
		--raw-version="$(RAW_VERSION)" \
		--hash-strategy="$(HASH_STRATEGY)" \
		--batch-id="$(BATCH_ID)" \
		--target-count="$(TARGET_COUNT)" \
		--network-authorization="$(or $(NETWORK_AUTHORIZATION),no)" \
		--match-detail-preflight-authorization="$(or $(MATCH_DETAIL_PREFLIGHT_AUTHORIZATION),no)" \
		--allow-db-write="$(or $(ALLOW_DB_WRITE),no)" \
		--allow-raw-match-data-write="$(or $(ALLOW_RAW_MATCH_DATA_WRITE),no)" \
		--allow-controlled-write="$(or $(ALLOW_CONTROLLED_WRITE),no)" \
		--allow-schema-migration="$(or $(ALLOW_SCHEMA_MIGRATION),no)" \
		--allow-parser-implementation="$(or $(ALLOW_PARSER_IMPLEMENTATION),no)" \
		--allow-feature-extraction="$(or $(ALLOW_FEATURE_EXTRACTION),no)" \
		--allow-training="$(or $(ALLOW_TRAINING),no)" \
		--allow-prediction="$(or $(ALLOW_PREDICTION),no)" \
		--allow-browser-runtime="$(or $(ALLOW_BROWSER_RUNTIME),no)" \
		--allow-proxy-runtime="$(or $(ALLOW_PROXY_RUNTIME),no)" \
		--concurrency="$(or $(CONCURRENCY),1)" \
		--retry="$(or $(RETRY),0)" \
		--print-full-body="$(or $(PRINT_FULL_BODY),no)" \
		--save-full-body="$(or $(SAVE_FULL_BODY),no)" \
		--print-full-json="$(or $(PRINT_FULL_JSON),no)" \
		--save-full-json="$(or $(SAVE_FULL_JSON),no)" \
		--print-full-pageprops="$(or $(PRINT_FULL_PAGEPROPS),no)" \
		--save-full-pageprops="$(or $(SAVE_FULL_PAGEPROPS),no)"

data-single-league-pageprops-v2-controlled-write-plan: ## Run Phase 5.21L2U controlled pageProps v2 write authorization/planning. SELECT-only, no DB write/network/match detail.
	@if [ -z "$(MANIFEST)" ] || [ -z "$(SOURCE)" ] || [ -z "$(LEAGUE_ID)" ] || [ -z "$(LEAGUE_NAME)" ] || [ -z "$(SEASON)" ] || [ -z "$(ROUTE)" ] || [ -z "$(RAW_VERSION)" ] || [ -z "$(HASH_STRATEGY)" ] || [ -z "$(BATCH_ID)" ] || [ -z "$(TARGET_COUNT)" ]; then \
		echo "ERROR: provide MANIFEST=docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.proposal.json SOURCE=fotmob LEAGUE_ID=53 LEAGUE_NAME='Ligue 1' SEASON=2025/2026 ROUTE=html_hydration RAW_VERSION=fotmob_pageprops_v2 HASH_STRATEGY=stable_pageprops_payload_v1 BATCH_ID=fotmob-pageprops-v2-ligue1-2025-2026-profile-001 TARGET_COUNT=50"; \
		exit 1; \
	fi
	$(COMPOSE_DEV) exec -T dev node scripts/ops/single_league_pageprops_v2_controlled_write_plan.js \
		--manifest="$(MANIFEST)" \
		--source="$(SOURCE)" \
		--league-id="$(LEAGUE_ID)" \
		--league-name="$(LEAGUE_NAME)" \
		--season="$(SEASON)" \
		--route="$(ROUTE)" \
		--raw-version="$(RAW_VERSION)" \
		--hash-strategy="$(HASH_STRATEGY)" \
		--batch-id="$(BATCH_ID)" \
		--target-count="$(TARGET_COUNT)" \
		--write-planning-authorization="$(or $(WRITE_PLANNING_AUTHORIZATION),no)" \
		--allow-db-write="$(or $(ALLOW_DB_WRITE),no)" \
		--allow-raw-match-data-write="$(or $(ALLOW_RAW_MATCH_DATA_WRITE),no)" \
		--allow-controlled-write="$(or $(ALLOW_CONTROLLED_WRITE),no)" \
		--allow-network="$(or $(ALLOW_NETWORK),no)" \
		--allow-match-detail-fetch="$(or $(ALLOW_MATCH_DETAIL_FETCH),no)" \
		--allow-schema-migration="$(or $(ALLOW_SCHEMA_MIGRATION),no)" \
		--allow-parser-implementation="$(or $(ALLOW_PARSER_IMPLEMENTATION),no)" \
		--allow-feature-extraction="$(or $(ALLOW_FEATURE_EXTRACTION),no)" \
		--allow-training="$(or $(ALLOW_TRAINING),no)" \
		--allow-prediction="$(or $(ALLOW_PREDICTION),no)"

data-single-league-pageprops-v2-controlled-write-execute: ## Run Phase 5.21L2V controlled pageProps v2 raw write execution. Requires final DB write confirmation and FK gate.
	@if [ -z "$(MANIFEST)" ] || [ -z "$(SOURCE)" ] || [ -z "$(LEAGUE_ID)" ] || [ -z "$(LEAGUE_NAME)" ] || [ -z "$(SEASON)" ] || [ -z "$(ROUTE)" ] || [ -z "$(RAW_VERSION)" ] || [ -z "$(HASH_STRATEGY)" ] || [ -z "$(BATCH_ID)" ] || [ -z "$(TARGET_COUNT)" ]; then \
		echo "ERROR: provide MANIFEST=docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.proposal.json SOURCE=fotmob LEAGUE_ID=53 LEAGUE_NAME='Ligue 1' SEASON=2025/2026 ROUTE=html_hydration RAW_VERSION=fotmob_pageprops_v2 HASH_STRATEGY=stable_pageprops_payload_v1 BATCH_ID=fotmob-pageprops-v2-ligue1-2025-2026-profile-001 TARGET_COUNT=50"; \
		exit 1; \
	fi
	$(COMPOSE_DEV) exec -T dev node scripts/ops/single_league_pageprops_v2_controlled_write_execute.js \
		--manifest="$(MANIFEST)" \
		--source="$(SOURCE)" \
		--league-id="$(LEAGUE_ID)" \
		--league-name="$(LEAGUE_NAME)" \
		--season="$(SEASON)" \
		--route="$(ROUTE)" \
		--raw-version="$(RAW_VERSION)" \
		--hash-strategy="$(HASH_STRATEGY)" \
		--batch-id="$(BATCH_ID)" \
		--target-count="$(TARGET_COUNT)" \
		--final-db-write-confirmation="$(or $(FINAL_DB_WRITE_CONFIRMATION),no)" \
		--network-authorization="$(or $(NETWORK_AUTHORIZATION),no)" \
		--match-detail-recapture-authorization="$(or $(MATCH_DETAIL_RECAPTURE_AUTHORIZATION),no)" \
		--allow-db-write="$(or $(ALLOW_DB_WRITE),no)" \
		--allow-raw-match-data-write="$(or $(ALLOW_RAW_MATCH_DATA_WRITE),no)" \
		--allow-controlled-write="$(or $(ALLOW_CONTROLLED_WRITE),no)" \
		--allow-matches-write="$(or $(ALLOW_MATCHES_WRITE),no)" \
		--allow-bookmaker-odds-write="$(or $(ALLOW_BOOKMAKER_ODDS_WRITE),no)" \
		--allow-feature-write="$(or $(ALLOW_FEATURE_WRITE),no)" \
		--allow-schema-migration="$(or $(ALLOW_SCHEMA_MIGRATION),no)" \
		--allow-parser-implementation="$(or $(ALLOW_PARSER_IMPLEMENTATION),no)" \
		--allow-feature-extraction="$(or $(ALLOW_FEATURE_EXTRACTION),no)" \
		--allow-training="$(or $(ALLOW_TRAINING),no)" \
		--allow-prediction="$(or $(ALLOW_PREDICTION),no)" \
		--allow-browser-runtime="$(or $(ALLOW_BROWSER_RUNTIME),no)" \
		--allow-proxy-runtime="$(or $(ALLOW_PROXY_RUNTIME),no)" \
		--concurrency="$(or $(CONCURRENCY),1)" \
		--retry="$(or $(RETRY),0)" \
		--print-full-body="$(or $(PRINT_FULL_BODY),no)" \
		--save-full-body="$(or $(SAVE_FULL_BODY),no)" \
		--print-full-json="$(or $(PRINT_FULL_JSON),no)" \
		--save-full-json="$(or $(SAVE_FULL_JSON),no)" \
		--print-full-pageprops="$(or $(PRINT_FULL_PAGEPROPS),no)" \
		--save-full-pageprops="$(or $(SAVE_FULL_PAGEPROPS),no)"

data-controlled-matches-identity-seed-prerequisite-plan: ## Run Phase 5.21L2V0 controlled matches identity seed prerequisite planning. SELECT-only, no DB/matches/raw write.
	@if [ -z "$(MANIFEST)" ] || [ -z "$(SOURCE)" ] || [ -z "$(LEAGUE_ID)" ] || [ -z "$(LEAGUE_NAME)" ] || [ -z "$(SEASON)" ] || [ -z "$(BATCH_ID)" ] || [ -z "$(TARGET_COUNT)" ]; then \
		echo "ERROR: provide MANIFEST=docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.proposal.json SOURCE=fotmob LEAGUE_ID=53 LEAGUE_NAME='Ligue 1' SEASON=2025/2026 BATCH_ID=fotmob-pageprops-v2-ligue1-2025-2026-profile-001 TARGET_COUNT=50"; \
		exit 1; \
	fi
	$(COMPOSE_DEV) exec -T dev node scripts/ops/controlled_matches_identity_seed_prerequisite_plan.js \
		--manifest="$(MANIFEST)" \
		--source="$(SOURCE)" \
		--league-id="$(LEAGUE_ID)" \
		--league-name="$(LEAGUE_NAME)" \
		--season="$(SEASON)" \
		--batch-id="$(BATCH_ID)" \
		--target-count="$(TARGET_COUNT)" \
		--planning-authorization="$(or $(PLANNING_AUTHORIZATION),no)" \
		--allow-db-write="$(or $(ALLOW_DB_WRITE),no)" \
		--allow-matches-write="$(or $(ALLOW_MATCHES_WRITE),no)" \
		--allow-raw-match-data-write="$(or $(ALLOW_RAW_MATCH_DATA_WRITE),no)" \
		--allow-controlled-write="$(or $(ALLOW_CONTROLLED_WRITE),no)" \
		--allow-network="$(or $(ALLOW_NETWORK),no)" \
		--allow-match-detail-fetch="$(or $(ALLOW_MATCH_DETAIL_FETCH),no)" \
		--allow-schema-migration="$(or $(ALLOW_SCHEMA_MIGRATION),no)" \
		--allow-parser-implementation="$(or $(ALLOW_PARSER_IMPLEMENTATION),no)" \
		--allow-feature-extraction="$(or $(ALLOW_FEATURE_EXTRACTION),no)" \
		--allow-training="$(or $(ALLOW_TRAINING),no)" \
		--allow-prediction="$(or $(ALLOW_PREDICTION),no)"

data-controlled-matches-identity-seed-execute: ## Run Phase 5.21L2V1 controlled matches identity seed execution. Writes matches only after final confirmation.
	@if [ -z "$(MANIFEST)" ] || [ -z "$(SOURCE)" ] || [ -z "$(LEAGUE_ID)" ] || [ -z "$(LEAGUE_NAME)" ] || [ -z "$(SEASON)" ] || [ -z "$(BATCH_ID)" ] || [ -z "$(TARGET_COUNT)" ]; then \
		echo "ERROR: provide MANIFEST=docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.proposal.json SOURCE=fotmob LEAGUE_ID=53 LEAGUE_NAME='Ligue 1' SEASON=2025/2026 BATCH_ID=fotmob-pageprops-v2-ligue1-2025-2026-profile-001 TARGET_COUNT=50"; \
		exit 1; \
	fi
	$(COMPOSE_DEV) exec -T dev node scripts/ops/controlled_matches_identity_seed_execute.js \
		--manifest="$(MANIFEST)" \
		--source="$(SOURCE)" \
		--league-id="$(LEAGUE_ID)" \
		--league-name="$(LEAGUE_NAME)" \
		--season="$(SEASON)" \
		--batch-id="$(BATCH_ID)" \
		--target-count="$(TARGET_COUNT)" \
		--final-db-write-confirmation="$(or $(FINAL_DB_WRITE_CONFIRMATION),no)" \
		--allow-db-write="$(or $(ALLOW_DB_WRITE),no)" \
		--allow-matches-write="$(or $(ALLOW_MATCHES_WRITE),no)" \
		--allow-raw-match-data-write="$(or $(ALLOW_RAW_MATCH_DATA_WRITE),no)" \
		--allow-bookmaker-odds-write="$(or $(ALLOW_BOOKMAKER_ODDS_WRITE),no)" \
		--allow-feature-write="$(or $(ALLOW_FEATURE_WRITE),no)" \
		--allow-network="$(or $(ALLOW_NETWORK),no)" \
		--allow-match-detail-fetch="$(or $(ALLOW_MATCH_DETAIL_FETCH),no)" \
		--allow-controlled-raw-write="$(or $(ALLOW_CONTROLLED_RAW_WRITE),no)" \
		--allow-schema-migration="$(or $(ALLOW_SCHEMA_MIGRATION),no)" \
		--allow-parser-implementation="$(or $(ALLOW_PARSER_IMPLEMENTATION),no)" \
		--allow-feature-extraction="$(or $(ALLOW_FEATURE_EXTRACTION),no)" \
		--allow-training="$(or $(ALLOW_TRAINING),no)" \
		--allow-prediction="$(or $(ALLOW_PREDICTION),no)"

data-post-seed-matches-identity-raw-write-readiness-audit: ## Run Phase 5.21L2V2 post-seed raw write retry readiness audit. SELECT-only, no write/network.
	@if [ -z "$(MANIFEST)" ] || [ -z "$(SOURCE)" ] || [ -z "$(LEAGUE_ID)" ] || [ -z "$(LEAGUE_NAME)" ] || [ -z "$(SEASON)" ] || [ -z "$(BATCH_ID)" ] || [ -z "$(TARGET_COUNT)" ]; then \
		echo "ERROR: provide MANIFEST=docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.proposal.json SOURCE=fotmob LEAGUE_ID=53 LEAGUE_NAME='Ligue 1' SEASON=2025/2026 BATCH_ID=fotmob-pageprops-v2-ligue1-2025-2026-profile-001 TARGET_COUNT=50"; \
		exit 1; \
	fi
	$(COMPOSE_DEV) exec -T dev node scripts/ops/post_seed_matches_identity_raw_write_readiness_audit.js \
		--manifest="$(MANIFEST)" \
		--source="$(SOURCE)" \
		--league-id="$(LEAGUE_ID)" \
		--league-name="$(LEAGUE_NAME)" \
		--season="$(SEASON)" \
		--batch-id="$(BATCH_ID)" \
		--target-count="$(TARGET_COUNT)" \
		--readiness-audit-authorization="$(or $(READINESS_AUDIT_AUTHORIZATION),no)" \
		--allow-db-write="$(or $(ALLOW_DB_WRITE),no)" \
		--allow-matches-write="$(or $(ALLOW_MATCHES_WRITE),no)" \
		--allow-raw-match-data-write="$(or $(ALLOW_RAW_MATCH_DATA_WRITE),no)" \
		--allow-controlled-write="$(or $(ALLOW_CONTROLLED_WRITE),no)" \
		--allow-network="$(or $(ALLOW_NETWORK),no)" \
		--allow-match-detail-fetch="$(or $(ALLOW_MATCH_DETAIL_FETCH),no)" \
		--allow-schema-migration="$(or $(ALLOW_SCHEMA_MIGRATION),no)" \
		--allow-parser-implementation="$(or $(ALLOW_PARSER_IMPLEMENTATION),no)" \
		--allow-feature-extraction="$(or $(ALLOW_FEATURE_EXTRACTION),no)" \
		--allow-training="$(or $(ALLOW_TRAINING),no)" \
		--allow-prediction="$(or $(ALLOW_PREDICTION),no)"

data-renewed-pageprops-v2-raw-write-execute: ## Run Phase 5.21L2V3 renewed controlled pageProps v2 raw write execution. Writes raw_match_data only.
	@if [ -z "$(MANIFEST)" ] || [ -z "$(SOURCE)" ] || [ -z "$(LEAGUE_ID)" ] || [ -z "$(LEAGUE_NAME)" ] || [ -z "$(SEASON)" ] || [ -z "$(ROUTE)" ] || [ -z "$(RAW_VERSION)" ] || [ -z "$(HASH_STRATEGY)" ] || [ -z "$(BATCH_ID)" ] || [ -z "$(TARGET_COUNT)" ]; then \
		echo "ERROR: provide MANIFEST=docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.proposal.json SOURCE=fotmob LEAGUE_ID=53 LEAGUE_NAME='Ligue 1' SEASON=2025/2026 ROUTE=html_hydration RAW_VERSION=fotmob_pageprops_v2 HASH_STRATEGY=stable_pageprops_payload_v1 BATCH_ID=fotmob-pageprops-v2-ligue1-2025-2026-profile-001 TARGET_COUNT=50"; \
		exit 1; \
	fi
	$(COMPOSE_DEV) exec -T dev node scripts/ops/renewed_pageprops_v2_raw_write_execute.js \
		--manifest="$(MANIFEST)" \
		--source="$(SOURCE)" \
		--league-id="$(LEAGUE_ID)" \
		--league-name="$(LEAGUE_NAME)" \
		--season="$(SEASON)" \
		--route="$(ROUTE)" \
		--raw-version="$(RAW_VERSION)" \
		--hash-strategy="$(HASH_STRATEGY)" \
		--batch-id="$(BATCH_ID)" \
		--target-count="$(TARGET_COUNT)" \
		--renewed-raw-write-authorization="$(or $(RENEWED_RAW_WRITE_AUTHORIZATION),no)" \
		--final-db-write-confirmation="$(or $(FINAL_DB_WRITE_CONFIRMATION),no)" \
		--network-authorization="$(or $(NETWORK_AUTHORIZATION),no)" \
		--match-detail-recapture-authorization="$(or $(MATCH_DETAIL_RECAPTURE_AUTHORIZATION),no)" \
		--allow-db-write="$(or $(ALLOW_DB_WRITE),no)" \
		--allow-raw-match-data-write="$(or $(ALLOW_RAW_MATCH_DATA_WRITE),no)" \
		--allow-controlled-write="$(or $(ALLOW_CONTROLLED_WRITE),no)" \
		--allow-matches-write="$(or $(ALLOW_MATCHES_WRITE),no)" \
		--allow-bookmaker-odds-write="$(or $(ALLOW_BOOKMAKER_ODDS_WRITE),no)" \
		--allow-feature-write="$(or $(ALLOW_FEATURE_WRITE),no)" \
		--allow-schema-migration="$(or $(ALLOW_SCHEMA_MIGRATION),no)" \
		--allow-parser-implementation="$(or $(ALLOW_PARSER_IMPLEMENTATION),no)" \
		--allow-feature-extraction="$(or $(ALLOW_FEATURE_EXTRACTION),no)" \
		--allow-training="$(or $(ALLOW_TRAINING),no)" \
		--allow-prediction="$(or $(ALLOW_PREDICTION),no)" \
		--allow-browser-runtime="$(or $(ALLOW_BROWSER_RUNTIME),no)" \
		--allow-proxy-runtime="$(or $(ALLOW_PROXY_RUNTIME),no)" \
		--concurrency="$(or $(CONCURRENCY),1)" \
		--retry="$(or $(RETRY),0)" \
		--request-delay-ms="$(or $(REQUEST_DELAY_MS),750)" \
		--print-full-body="$(or $(PRINT_FULL_BODY),no)" \
		--save-full-body="$(or $(SAVE_FULL_BODY),no)" \
		--print-full-json="$(or $(PRINT_FULL_JSON),no)" \
		--save-full-json="$(or $(SAVE_FULL_JSON),no)" \
		--print-full-pageprops="$(or $(PRINT_FULL_PAGEPROPS),no)" \
		--save-full-pageprops="$(or $(SAVE_FULL_PAGEPROPS),no)" \
		--start-head="$(or $(START_HEAD),)" \
		--branch="$(or $(BRANCH),)"

data-renewed-pageprops-v2-baseline-proposal-plan: ## Run Phase 5.21L2V3C no-write renewed baseline proposal planning. Writes docs only.
	@if [ -z "$(MANIFEST)" ] || [ -z "$(SOURCE)" ] || [ -z "$(LEAGUE_ID)" ] || [ -z "$(LEAGUE_NAME)" ] || [ -z "$(SEASON)" ] || [ -z "$(ROUTE)" ] || [ -z "$(RAW_VERSION)" ] || [ -z "$(HASH_STRATEGY)" ] || [ -z "$(BATCH_ID)" ] || [ -z "$(TARGET_COUNT)" ]; then \
		echo "ERROR: provide MANIFEST=docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.proposal.json SOURCE=fotmob LEAGUE_ID=53 LEAGUE_NAME='Ligue 1' SEASON=2025/2026 ROUTE=html_hydration RAW_VERSION=fotmob_pageprops_v2 HASH_STRATEGY=stable_pageprops_payload_v1 BATCH_ID=fotmob-pageprops-v2-ligue1-2025-2026-profile-001 TARGET_COUNT=50"; \
		exit 1; \
	fi
	$(COMPOSE_DEV) exec -T dev node scripts/ops/renewed_pageprops_v2_baseline_proposal_plan.js \
		--manifest="$(MANIFEST)" \
		--proposal-output="$(or $(PROPOSAL_OUTPUT),docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.renewed_baseline_proposal.phase521l2v3c.json)" \
		--source="$(SOURCE)" \
		--league-id="$(LEAGUE_ID)" \
		--league-name="$(LEAGUE_NAME)" \
		--season="$(SEASON)" \
		--route="$(ROUTE)" \
		--raw-version="$(RAW_VERSION)" \
		--hash-strategy="$(HASH_STRATEGY)" \
		--batch-id="$(BATCH_ID)" \
		--target-count="$(TARGET_COUNT)" \
		--planning-authorization="$(or $(PLANNING_AUTHORIZATION),no)" \
		--network-authorization="$(or $(NETWORK_AUTHORIZATION),no)" \
		--match-detail-recapture-authorization="$(or $(MATCH_DETAIL_RECAPTURE_AUTHORIZATION),no)" \
		--allow-db-write="$(or $(ALLOW_DB_WRITE),no)" \
		--allow-raw-match-data-write="$(or $(ALLOW_RAW_MATCH_DATA_WRITE),no)" \
		--allow-controlled-write="$(or $(ALLOW_CONTROLLED_WRITE),no)" \
		--allow-matches-write="$(or $(ALLOW_MATCHES_WRITE),no)" \
		--allow-bookmaker-odds-write="$(or $(ALLOW_BOOKMAKER_ODDS_WRITE),no)" \
		--allow-feature-write="$(or $(ALLOW_FEATURE_WRITE),no)" \
		--allow-schema-migration="$(or $(ALLOW_SCHEMA_MIGRATION),no)" \
		--allow-parser-implementation="$(or $(ALLOW_PARSER_IMPLEMENTATION),no)" \
		--allow-feature-extraction="$(or $(ALLOW_FEATURE_EXTRACTION),no)" \
		--allow-training="$(or $(ALLOW_TRAINING),no)" \
		--allow-prediction="$(or $(ALLOW_PREDICTION),no)" \
		--allow-browser-runtime="$(or $(ALLOW_BROWSER_RUNTIME),no)" \
		--allow-proxy-runtime="$(or $(ALLOW_PROXY_RUNTIME),no)" \
		--print-full-body="$(or $(PRINT_FULL_BODY),no)" \
		--save-full-body="$(or $(SAVE_FULL_BODY),no)" \
		--print-full-json="$(or $(PRINT_FULL_JSON),no)" \
		--save-full-json="$(or $(SAVE_FULL_JSON),no)" \
		--print-full-pageprops="$(or $(PRINT_FULL_PAGEPROPS),no)" \
		--save-full-pageprops="$(or $(SAVE_FULL_PAGEPROPS),no)" \
		--sample-external-ids="$(or $(SAMPLE_EXTERNAL_IDS),)" \
		--repeat-count="$(or $(REPEAT_COUNT),2)" \
		--request-delay-ms="$(or $(REQUEST_DELAY_MS),750)" \
		--base-head="$(or $(BASE_HEAD),)" \
		--base-branch="$(or $(BASE_BRANCH),)" \
		--branch="$(or $(BRANCH),)" \
		--pr1276-state="$(or $(PR1276_STATE),)" \
		--pr1276-url="$(or $(PR1276_URL),)"

data-pageprops-v2-target-identity-reconciliation-plan: ## Run Phase 5.21L2V3D no-write target identity reconciliation planning. Writes docs only.
	@if [ -z "$(MANIFEST)" ] || [ -z "$(SOURCE)" ] || [ -z "$(LEAGUE_ID)" ] || [ -z "$(LEAGUE_NAME)" ] || [ -z "$(SEASON)" ] || [ -z "$(ROUTE)" ] || [ -z "$(RAW_VERSION)" ] || [ -z "$(HASH_STRATEGY)" ] || [ -z "$(BATCH_ID)" ] || [ -z "$(TARGET_COUNT)" ]; then \
		echo "ERROR: provide MANIFEST=docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.proposal.json SOURCE=fotmob LEAGUE_ID=53 LEAGUE_NAME='Ligue 1' SEASON=2025/2026 ROUTE=html_hydration RAW_VERSION=fotmob_pageprops_v2 HASH_STRATEGY=stable_pageprops_payload_v1 BATCH_ID=fotmob-pageprops-v2-ligue1-2025-2026-profile-001 TARGET_COUNT=50"; \
		exit 1; \
	fi
	$(COMPOSE_DEV) exec -T dev node scripts/ops/pageprops_v2_target_identity_reconciliation_plan.js \
		--manifest="$(MANIFEST)" \
		--renewed-proposal="$(or $(RENEWED_PROPOSAL),docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.renewed_baseline_proposal.phase521l2v3c.json)" \
		--report-output="$(or $(REPORT_OUTPUT),docs/_reports/DATA_ENTRYPOINT_GOVERNANCE_PHASE5_21_L2V3D.md)" \
		--source="$(SOURCE)" \
		--league-id="$(LEAGUE_ID)" \
		--league-name="$(LEAGUE_NAME)" \
		--season="$(SEASON)" \
		--route="$(ROUTE)" \
		--raw-version="$(RAW_VERSION)" \
		--hash-strategy="$(HASH_STRATEGY)" \
		--batch-id="$(BATCH_ID)" \
		--target-count="$(TARGET_COUNT)" \
		--planning-authorization="$(or $(PLANNING_AUTHORIZATION),no)" \
		--target-identity-reconciliation-authorization="$(or $(TARGET_IDENTITY_RECONCILIATION_AUTHORIZATION),no)" \
		--network-authorization="$(or $(NETWORK_AUTHORIZATION),no)" \
		--match-detail-recapture-authorization="$(or $(MATCH_DETAIL_RECAPTURE_AUTHORIZATION),no)" \
		--allow-db-write="$(or $(ALLOW_DB_WRITE),no)" \
		--allow-raw-match-data-write="$(or $(ALLOW_RAW_MATCH_DATA_WRITE),no)" \
		--allow-controlled-write="$(or $(ALLOW_CONTROLLED_WRITE),no)" \
		--allow-matches-write="$(or $(ALLOW_MATCHES_WRITE),no)" \
		--allow-bookmaker-odds-write="$(or $(ALLOW_BOOKMAKER_ODDS_WRITE),no)" \
		--allow-feature-write="$(or $(ALLOW_FEATURE_WRITE),no)" \
		--allow-schema-migration="$(or $(ALLOW_SCHEMA_MIGRATION),no)" \
		--allow-parser-implementation="$(or $(ALLOW_PARSER_IMPLEMENTATION),no)" \
		--allow-feature-extraction="$(or $(ALLOW_FEATURE_EXTRACTION),no)" \
		--allow-training="$(or $(ALLOW_TRAINING),no)" \
		--allow-prediction="$(or $(ALLOW_PREDICTION),no)" \
		--allow-browser-runtime="$(or $(ALLOW_BROWSER_RUNTIME),no)" \
		--allow-proxy-runtime="$(or $(ALLOW_PROXY_RUNTIME),no)" \
		--print-full-body="$(or $(PRINT_FULL_BODY),no)" \
		--save-full-body="$(or $(SAVE_FULL_BODY),no)" \
		--print-full-json="$(or $(PRINT_FULL_JSON),no)" \
		--save-full-json="$(or $(SAVE_FULL_JSON),no)" \
		--print-full-pageprops="$(or $(PRINT_FULL_PAGEPROPS),no)" \
		--save-full-pageprops="$(or $(SAVE_FULL_PAGEPROPS),no)" \
		--retry="$(or $(RETRY),0)" \
		--request-delay-ms="$(or $(REQUEST_DELAY_MS),750)" \
		--target-external-ids="$(or $(TARGET_EXTERNAL_IDS),)" \
		--base-head="$(or $(BASE_HEAD),)" \
		--branch="$(or $(BRANCH),)" \
		--main-head="$(or $(MAIN_HEAD),)" \
		--main-ci-status="$(or $(MAIN_CI_STATUS),)" \
		--pr1276-state="$(or $(PR1276_STATE),)" \
		--pr1276-merge-commit="$(or $(PR1276_MERGE_COMMIT),)" \
		--pr1277-state="$(or $(PR1277_STATE),)" \
		--pr1277-merge-commit="$(or $(PR1277_MERGE_COMMIT),)" \
		--pr1277-retarget-result="$(or $(PR1277_RETARGET_RESULT),)"

data-pageprops-v2-target-source-inventory-reconciliation-plan: ## Run Phase 5.21L2V3E no-write target identity source inventory reconciliation planning. Writes docs only.
	@if [ -z "$(MANIFEST)" ] || [ -z "$(SOURCE)" ] || [ -z "$(LEAGUE_ID)" ] || [ -z "$(LEAGUE_NAME)" ] || [ -z "$(SEASON)" ] || [ -z "$(RAW_VERSION)" ] || [ -z "$(HASH_STRATEGY)" ] || [ -z "$(BATCH_ID)" ] || [ -z "$(TARGET_COUNT)" ]; then \
		echo "ERROR: provide MANIFEST=docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.proposal.json SOURCE=fotmob LEAGUE_ID=53 LEAGUE_NAME='Ligue 1' SEASON=2025/2026 RAW_VERSION=fotmob_pageprops_v2 HASH_STRATEGY=stable_pageprops_payload_v1 BATCH_ID=fotmob-pageprops-v2-ligue1-2025-2026-profile-001 TARGET_COUNT=50"; \
		exit 1; \
	fi
	$(COMPOSE_DEV) exec -T dev node scripts/ops/pageprops_v2_target_source_inventory_reconciliation_plan.js \
		--manifest="$(MANIFEST)" \
		--renewed-proposal="$(or $(RENEWED_PROPOSAL),docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.renewed_baseline_proposal.phase521l2v3c.json)" \
		--report-output="$(or $(REPORT_OUTPUT),docs/_reports/DATA_ENTRYPOINT_GOVERNANCE_PHASE5_21_L2V3E.md)" \
		--source="$(SOURCE)" \
		--league-id="$(LEAGUE_ID)" \
		--league-name="$(LEAGUE_NAME)" \
		--season="$(SEASON)" \
		--raw-version="$(RAW_VERSION)" \
		--hash-strategy="$(HASH_STRATEGY)" \
		--batch-id="$(BATCH_ID)" \
		--target-count="$(TARGET_COUNT)" \
		--planning-authorization="$(or $(PLANNING_AUTHORIZATION),no)" \
		--source-inventory-reconciliation-authorization="$(or $(SOURCE_INVENTORY_RECONCILIATION_AUTHORIZATION),no)" \
		--network-authorization="$(or $(NETWORK_AUTHORIZATION),no)" \
		--allow-db-write="$(or $(ALLOW_DB_WRITE),no)" \
		--allow-raw-match-data-write="$(or $(ALLOW_RAW_MATCH_DATA_WRITE),no)" \
		--allow-controlled-write="$(or $(ALLOW_CONTROLLED_WRITE),no)" \
		--allow-matches-write="$(or $(ALLOW_MATCHES_WRITE),no)" \
		--allow-bookmaker-odds-write="$(or $(ALLOW_BOOKMAKER_ODDS_WRITE),no)" \
		--allow-feature-write="$(or $(ALLOW_FEATURE_WRITE),no)" \
		--allow-schema-migration="$(or $(ALLOW_SCHEMA_MIGRATION),no)" \
		--allow-parser-implementation="$(or $(ALLOW_PARSER_IMPLEMENTATION),no)" \
		--allow-feature-extraction="$(or $(ALLOW_FEATURE_EXTRACTION),no)" \
		--allow-training="$(or $(ALLOW_TRAINING),no)" \
		--allow-prediction="$(or $(ALLOW_PREDICTION),no)" \
		--allow-browser-runtime="$(or $(ALLOW_BROWSER_RUNTIME),no)" \
		--allow-proxy-runtime="$(or $(ALLOW_PROXY_RUNTIME),no)" \
		--print-full-body="$(or $(PRINT_FULL_BODY),no)" \
		--save-full-body="$(or $(SAVE_FULL_BODY),no)" \
		--print-full-json="$(or $(PRINT_FULL_JSON),no)" \
		--save-full-json="$(or $(SAVE_FULL_JSON),no)" \
		--print-full-pageprops="$(or $(PRINT_FULL_PAGEPROPS),no)" \
		--save-full-pageprops="$(or $(SAVE_FULL_PAGEPROPS),no)" \
		--retry="$(or $(RETRY),0)" \
		--request-delay-ms="$(or $(REQUEST_DELAY_MS),0)" \
		--target-external-ids="$(or $(TARGET_EXTERNAL_IDS),)" \
		--base-head="$(or $(BASE_HEAD),)" \
		--branch="$(or $(BRANCH),)" \
		--main-head="$(or $(MAIN_HEAD),)" \
		--main-ci-status="$(or $(MAIN_CI_STATUS),)" \
		--pr1278-state="$(or $(PR1278_STATE),)" \
		--pr1278-merge-commit="$(or $(PR1278_MERGE_COMMIT),)"

data-pageprops-v2-schedule-detail-identity-normalization-plan: ## Run Phase 5.21L2V3F no-write schedule/detail identity normalization planning. Writes docs only.
	@if [ -z "$(MANIFEST)" ] || [ -z "$(SOURCE)" ] || [ -z "$(LEAGUE_ID)" ] || [ -z "$(LEAGUE_NAME)" ] || [ -z "$(SEASON)" ] || [ -z "$(RAW_VERSION)" ] || [ -z "$(HASH_STRATEGY)" ] || [ -z "$(BATCH_ID)" ] || [ -z "$(TARGET_COUNT)" ]; then \
		echo "ERROR: provide MANIFEST=docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.proposal.json SOURCE=fotmob LEAGUE_ID=53 LEAGUE_NAME='Ligue 1' SEASON=2025/2026 RAW_VERSION=fotmob_pageprops_v2 HASH_STRATEGY=stable_pageprops_payload_v1 BATCH_ID=fotmob-pageprops-v2-ligue1-2025-2026-profile-001 TARGET_COUNT=50"; \
		exit 1; \
	fi
	$(COMPOSE_DEV) exec -T dev node scripts/ops/pageprops_v2_schedule_detail_identity_normalization_plan.js \
		--manifest="$(MANIFEST)" \
		--renewed-proposal="$(or $(RENEWED_PROPOSAL),docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.renewed_baseline_proposal.phase521l2v3c.json)" \
		--report-output="$(or $(REPORT_OUTPUT),docs/_reports/DATA_ENTRYPOINT_GOVERNANCE_PHASE5_21_L2V3F.md)" \
		--normalization-proposal-output="$(or $(NORMALIZATION_PROPOSAL_OUTPUT),docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.schedule_detail_identity_normalization_proposal.phase521l2v3f.json)" \
		--source-inventory-reconciliation-report="$(or $(SOURCE_INVENTORY_RECONCILIATION_REPORT),docs/_reports/DATA_ENTRYPOINT_GOVERNANCE_PHASE5_21_L2V3E.md)" \
		--source="$(SOURCE)" \
		--league-id="$(LEAGUE_ID)" \
		--league-name="$(LEAGUE_NAME)" \
		--season="$(SEASON)" \
		--raw-version="$(RAW_VERSION)" \
		--hash-strategy="$(HASH_STRATEGY)" \
		--batch-id="$(BATCH_ID)" \
		--target-count="$(TARGET_COUNT)" \
		--planning-authorization="$(or $(PLANNING_AUTHORIZATION),no)" \
		--schedule-detail-normalization-authorization="$(or $(SCHEDULE_DETAIL_NORMALIZATION_AUTHORIZATION),no)" \
		--network-authorization="$(or $(NETWORK_AUTHORIZATION),no)" \
		--allow-db-write="$(or $(ALLOW_DB_WRITE),no)" \
		--allow-raw-match-data-write="$(or $(ALLOW_RAW_MATCH_DATA_WRITE),no)" \
		--allow-controlled-write="$(or $(ALLOW_CONTROLLED_WRITE),no)" \
		--allow-matches-write="$(or $(ALLOW_MATCHES_WRITE),no)" \
		--allow-bookmaker-odds-write="$(or $(ALLOW_BOOKMAKER_ODDS_WRITE),no)" \
		--allow-feature-write="$(or $(ALLOW_FEATURE_WRITE),no)" \
		--allow-schema-migration="$(or $(ALLOW_SCHEMA_MIGRATION),no)" \
		--allow-parser-implementation="$(or $(ALLOW_PARSER_IMPLEMENTATION),no)" \
		--allow-feature-extraction="$(or $(ALLOW_FEATURE_EXTRACTION),no)" \
		--allow-training="$(or $(ALLOW_TRAINING),no)" \
		--allow-prediction="$(or $(ALLOW_PREDICTION),no)" \
		--allow-browser-runtime="$(or $(ALLOW_BROWSER_RUNTIME),no)" \
		--allow-proxy-runtime="$(or $(ALLOW_PROXY_RUNTIME),no)" \
		--print-full-body="$(or $(PRINT_FULL_BODY),no)" \
		--save-full-body="$(or $(SAVE_FULL_BODY),no)" \
		--print-full-json="$(or $(PRINT_FULL_JSON),no)" \
		--save-full-json="$(or $(SAVE_FULL_JSON),no)" \
		--print-full-pageprops="$(or $(PRINT_FULL_PAGEPROPS),no)" \
		--save-full-pageprops="$(or $(SAVE_FULL_PAGEPROPS),no)" \
		--retry="$(or $(RETRY),0)" \
		--request-delay-ms="$(or $(REQUEST_DELAY_MS),0)" \
		--branch="$(or $(BRANCH),)" \
		--base-head="$(or $(BASE_HEAD),)" \
		--main-head="$(or $(MAIN_HEAD),)" \
		--main-ci-status="$(or $(MAIN_CI_STATUS),)" \
		--pr1279-state="$(or $(PR1279_STATE),)" \
		--pr1279-merge-commit="$(or $(PR1279_MERGE_COMMIT),)"

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

data-fotmob-single-target-adapter-preflight: ## Hardened no-network FotMob adapter preflight. Phase 4.98F.
	@$(FOTMOB_SINGLE_TARGET_ADAPTER_NODE) scripts/ops/fotmob_single_target_adapter_scaffold.js \
		--target-source "$(TARGET_SOURCE)" \
		--target-scope-type "$(TARGET_SCOPE_TYPE)" \
		$(if $(TARGET_MATCH_ID),--target-match-id "$(TARGET_MATCH_ID)") \
		$(if $(TARGET_LEAGUE),--target-league "$(TARGET_LEAGUE)") \
		$(if $(TARGET_SEASON),--target-season "$(TARGET_SEASON)") \
		$(if $(TARGET_DATE),--target-date "$(TARGET_DATE)") \
		$(if $(TARGET_COUNT),--target-count "$(TARGET_COUNT)") \
		$(if $(BULK_SCOPE_ALLOWED),--bulk-scope-allowed "$(BULK_SCOPE_ALLOWED)") \
		$(if $(MAX_TARGETS),--max-targets "$(MAX_TARGETS)") \
		--terms-approval "$(or $(TERMS_APPROVAL),no)" \
		--network-authorization "$(or $(NETWORK_AUTHORIZATION),no)" \
		--allow-browser-runtime "$(or $(ALLOW_BROWSER_RUNTIME),no)" \
		--allow-proxy-runtime "$(or $(ALLOW_PROXY_RUNTIME),no)" \
		--allow-external-network "$(or $(ALLOW_EXTERNAL_NETWORK),no)" \
		--allow-staging-write "$(or $(ALLOW_STAGING_WRITE),no)" \
		--allow-db-write "$(or $(ALLOW_DB_WRITE),no)" \
		--allow-training "$(or $(ALLOW_TRAINING),no)" \
		--allow-prediction "$(or $(ALLOW_PREDICTION),no)" \
		--final-human-confirmation "$(or $(FINAL_HUMAN_CONFIRMATION),no)" \
		$(if $(SOURCE_HOMEPAGE_URL),--source-homepage-url "$(SOURCE_HOMEPAGE_URL)") \
		$(if $(TERMS_URL),--terms-url "$(TERMS_URL)") \
		$(if $(LICENSE_URL),--license-url "$(LICENSE_URL)") \
		$(if $(ALLOWED_USE_SUMMARY),--allowed-use-summary "$(ALLOWED_USE_SUMMARY)") \
		$(if $(RATE_LIMIT_POLICY),--rate-limit-policy "$(RATE_LIMIT_POLICY)") \
		$(if $(RETRY_POLICY),--retry-policy "$(RETRY_POLICY)") \
		$(if $(USER_AGENT_POLICY),--user-agent-policy "$(USER_AGENT_POLICY)") \
		$(if $(OUTPUT_ROOT),--output-root "$(OUTPUT_ROOT)") \
		$(if $(EXPECTED_RESPONSE_KIND),--expected-response-kind "$(EXPECTED_RESPONSE_KIND)") \
		$(if $(PARSER_CONFIDENCE_THRESHOLD),--parser-confidence-threshold "$(PARSER_CONFIDENCE_THRESHOLD)")

data-fotmob-single-target-adapter-commit: ## Blocked FotMob trusted single-target adapter execution gate. Remains blocked in Phase 4.98F.
	@echo "BLOCKED: FotMob adapter preflight hardening is not executable in Phase 4.98F."
	@echo "  Even with CONFIRM_FOTMOB_SINGLE_TARGET_ADAPTER=1, this path remains blocked."
	@echo "  Future FotMob network dry-run requires separate user target, terms, allowed-use, and network authorization."
	@exit 1

data-fotmob-stdout-network-dry-run-authorization-packet-preview: ## Validate FotMob stdout-only network dry-run authorization packet template. Phase 4.99F.
	@if [ -z "$(PACKET)" ]; then \
		echo "ERROR: provide PACKET=<path>"; \
		exit 1; \
	fi
	@$(FOTMOB_STDOUT_NETWORK_AUTH_PACKET_NODE) scripts/ops/fotmob_stdout_network_dry_run_authorization_packet.js --packet "$(PACKET)"

data-fotmob-stdout-network-dry-run-authorization-packet-commit: ## Blocked FotMob stdout-only network dry-run authorization packet execution gate. Remains blocked in Phase 4.99F.
	@echo "BLOCKED: FotMob stdout-only network dry-run authorization packet is not executable in Phase 4.99F."
	@echo "  Even with CONFIRM_FOTMOB_STDOUT_NETWORK_DRY_RUN_AUTHORIZATION_PACKET=1, this path remains blocked."
	@echo "  The packet is template-only and does not authorize or execute a network dry-run."
	@exit 1

data-fotmob-stdout-network-dry-run-execution-plan-preview: ## Validate FotMob stdout-only network dry-run execution plan template. Phase 5.00F.
	@if [ -z "$(PLAN)" ] || [ -z "$(PACKET)" ]; then \
		echo "ERROR: provide PLAN=<path> and PACKET=<path>"; \
		exit 1; \
	fi
	@$(FOTMOB_STDOUT_NETWORK_EXECUTION_PLAN_NODE) scripts/ops/fotmob_stdout_network_dry_run_execution_plan.js --plan "$(PLAN)" --packet "$(PACKET)"

data-fotmob-stdout-network-dry-run-execution-plan-commit: ## Blocked FotMob stdout-only network dry-run execution plan execution gate. Remains blocked in Phase 5.00F.
	@echo "BLOCKED: FotMob stdout-only network dry-run execution plan is not executable in Phase 5.00F."
	@echo "  Even with CONFIRM_FOTMOB_STDOUT_NETWORK_DRY_RUN_EXECUTION_PLAN=1, this path remains blocked."
	@echo "  The execution plan is template-only and does not authorize or execute a network dry-run."
	@exit 1

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

data-single-target-acquisition-network-authorization-handoff-checklist-preview: ## Preview-only authorization handoff checklist. Phase 4.94D. No network, no writes, no DB.
	@if [ -z "$(HANDOFF_CHECKLIST)" ] || [ -z "$(REVIEW_RESULT)" ] || [ -z "$(REVIEW_PLAN)" ] || [ -z "$(INTAKE)" ] || [ -z "$(VALIDATION_CLOSURE)" ] || [ -z "$(BLOCKED_SUMMARY)" ]; then \
		echo "ERROR: provide HANDOFF_CHECKLIST=<path>, REVIEW_RESULT=<path>, REVIEW_PLAN=<path>, INTAKE=<path>, VALIDATION_CLOSURE=<path>, and BLOCKED_SUMMARY=<path>"; \
		exit 1; \
	fi
	@echo "Phase 4.94D: network authorization handoff checklist (template-only, local-only, no writes, no network, no DB)"
	$(NETWORK_AUTHORIZATION_HANDOFF_CHECKLIST_NODE) scripts/ops/single_target_acquisition_network_authorization_handoff_checklist.js \
		--handoff-checklist "$(HANDOFF_CHECKLIST)" \
		--review-result "$(REVIEW_RESULT)" \
		--review-plan "$(REVIEW_PLAN)" \
		--intake "$(INTAKE)" \
		--validation-closure "$(VALIDATION_CLOSURE)" \
		--blocked-summary "$(BLOCKED_SUMMARY)"

data-single-target-acquisition-network-authorization-handoff-checklist-commit: ## Blocked authorization handoff checklist gate. Remains not wired in Phase 4.94D.
	@echo "BLOCKED: single-target acquisition authorization handoff checklist execution is not wired in Phase 4.94D."
	@echo "  Even with CONFIRM_SINGLE_TARGET_ACQUISITION_NETWORK_AUTHORIZATION_HANDOFF_CHECKLIST=1, this path remains blocked."
	@echo "  Phase 4.94D previews the authorization handoff checklist template only and does not authorize any network dry-run, staging write, authorization handoff checklist file write, or DB write."
	@exit 1

data-single-target-acquisition-network-authorization-decision-preview: ## Preview-only network authorization decision. Phase 4.95D. No network, no writes, no DB.
	@if [ -z "$(AUTHORIZATION_DECISION)" ] || [ -z "$(HANDOFF_CHECKLIST)" ] || [ -z "$(REVIEW_RESULT)" ] || [ -z "$(REVIEW_PLAN)" ] || [ -z "$(INTAKE)" ] || [ -z "$(VALIDATION_CLOSURE)" ] || [ -z "$(BLOCKED_SUMMARY)" ]; then \
		echo "ERROR: provide AUTHORIZATION_DECISION=<path>, HANDOFF_CHECKLIST=<path>, REVIEW_RESULT=<path>, REVIEW_PLAN=<path>, INTAKE=<path>, VALIDATION_CLOSURE=<path>, and BLOCKED_SUMMARY=<path>"; \
		exit 1; \
	fi
	@echo "Phase 4.95D: network authorization decision (template-only, local-only, no writes, no network, no DB)"
	$(NETWORK_AUTHORIZATION_DECISION_NODE) scripts/ops/single_target_acquisition_network_authorization_decision.js \
		--authorization-decision "$(AUTHORIZATION_DECISION)" \
		--handoff-checklist "$(HANDOFF_CHECKLIST)" \
		--review-result "$(REVIEW_RESULT)" \
		--review-plan "$(REVIEW_PLAN)" \
		--intake "$(INTAKE)" \
		--validation-closure "$(VALIDATION_CLOSURE)" \
		--blocked-summary "$(BLOCKED_SUMMARY)"

data-single-target-acquisition-network-authorization-decision-commit: ## Blocked network authorization decision gate. Remains not wired in Phase 4.95D.
	@echo "BLOCKED: single-target acquisition network authorization decision execution is not wired in Phase 4.95D."
	@echo "  Even with CONFIRM_SINGLE_TARGET_ACQUISITION_NETWORK_AUTHORIZATION_DECISION=1, this path remains blocked."
	@echo "  Phase 4.95D previews the authorization decision template only and does not authorize any network dry-run, staging write, network authorization decision file write, or DB write."
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
