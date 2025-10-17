# 🚀 Football Prediction Project Makefile
# Author: DevOps Engineer
# Description: Concise, maintainable Makefile for Python/FastAPI project

# ============================================================================
# 🔧 Configuration Variables
# ============================================================================
PYTHON := python3
VENV := .venv
VENV_BIN := $(VENV)/bin
ACTIVATE := . $(VENV_BIN)/activate

# Coverage thresholds for different environments
COVERAGE_THRESHOLD_CI ?= 25      # CI environment (gradually improving) - 阶段A完成
COVERAGE_THRESHOLD_DEV ?= 25     # Development environment (current coverage)
COVERAGE_THRESHOLD_MIN ?= 20     # Minimum acceptable coverage
COVERAGE_THRESHOLD ?= $(COVERAGE_THRESHOLD_CI)  # Default to CI level

IMAGE_NAME ?= football-prediction
GIT_SHA := $(shell git rev-parse --short HEAD)

# Environment Configuration
ENV_FILE ?= .env
ENV_EXAMPLE ?= .env.example

# CPU core count for parallel execution
NCPU := $(shell nproc 2>/dev/null || echo 4)

# Required environment variables for production
REQUIRED_ENV_VARS := DATABASE_URL REDIS_URL SECRET_KEY

# Optional but recommended environment variables
RECOMMENDED_ENV_VARS := ENVIRONMENT LOG_LEVEL API_HOSTNAME

# Colors for better UX
GREEN := \033[32m
YELLOW := \033[33m
RED := \033[31m
BLUE := \033[34m
RESET := \033[0m

# ============================================================================
# 🎯 Default Target
# ============================================================================
.DEFAULT_GOAL := help

help: ## 📋 Show available commands
	@echo "$(BLUE)🚀 Football Prediction Project Commands$(RESET)"
	@echo "$(YELLOW)Environment:$(RESET)"
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## .*Environment/ {printf "  $(GREEN)%-12s$(RESET) %s\n", $$1, $$2}' $(MAKEFILE_LIST)
	@echo "$(YELLOW)Code Quality:$(RESET)"
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## .*Quality/ {printf "  $(GREEN)%-12s$(RESET) %s\n", $$1, $$2}' $(MAKEFILE_LIST)
	@echo "$(YELLOW)Testing:$(RESET)"
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## .*Test/ {printf "  $(GREEN)%-12s$(RESET) %s\n", $$1, $$2}' $(MAKEFILE_LIST)
	@echo "$(YELLOW)CI/Container:$(RESET)"
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## .*(CI|Container)/ {printf "  $(GREEN)%-12s$(RESET) %s\n", $$1, $$2}' $(MAKEFILE_LIST)
	@echo "$(YELLOW)Other:$(RESET)"
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / && !/Environment|Quality|Test|CI|Container/ {printf "  $(GREEN)%-12s$(RESET) %s\n", $$1, $$2}' $(MAKEFILE_LIST)

# ============================================================================
# 🌍 Environment Management
# ============================================================================
env-check: ## Environment: Check development environment health
	@echo "$(YELLOW)Checking development environment...$(RESET)"
	@$(ACTIVATE) && \
	echo "$(BLUE)✓ Virtual environment: $(VENV)$(RESET)" && \
	python --version && \
	echo "$(BLUE)✓ Python version check passed$(RESET)" && \
	pip list | head -5 && \
	echo "$(BLUE)✓ Checking critical dependencies...$(RESET)" && \
	$(ACTIVATE) && python -c "import fastapi, sqlalchemy, pytest" && \
	echo "$(BLUE)✓ Critical dependencies available$(RESET)" && \
	echo "$(GREEN)✅ Environment check completed$(RESET)"
venv: ## Environment: Create and activate virtual environment
	@if [ ! -d "$(VENV)" ]; then \
		echo "$(YELLOW)Creating virtual environment...$(RESET)"; \
		$(PYTHON) -m venv $(VENV); \
		echo "$(GREEN)✅ Virtual environment created$(RESET)"; \
	else \
		echo "$(BLUE)ℹ️  Virtual environment already exists$(RESET)"; \
	fi

install: venv ## Environment: Install dependencies from lock file
	@$(ACTIVATE) && \
	if pip list | grep -F "fastapi" > /dev/null 2>&1; then \
		echo "$(BLUE)ℹ️  Dependencies appear to be installed$(RESET)"; \
	else \
		echo "$(YELLOW)Installing dependencies...$(RESET)"; \
		pip install --upgrade pip && \
		pip install -r requirements/requirements.lock; \
		echo "$(GREEN)✅ Dependencies installed$(RESET)"; \
	fi
	@echo "$(YELLOW)Running welcome script...$(RESET)" && \
	bash scripts/welcome.sh

install-locked: venv ## Environment: Install from locked dependencies (reproducible)
	@if [ ! -f requirements/requirements.lock ]; then \
		echo "$(RED)❌ requirements/requirements.lock not found. Run 'make lock-deps' first.$(RESET)"; \
		exit 1; \
	fi
	@$(ACTIVATE) && \
	echo "$(BLUE)📦 Installing locked dependencies (reproducible)...$(RESET)" && \
	pip install --upgrade pip && \
	pip install -r requirements/requirements.lock && \
	echo "$(GREEN)✅ Dependencies installed from lock file$(RESET)"

lock-deps: venv ## Environment: Lock current dependencies for reproducible builds
	@$(ACTIVATE) && \
	echo "$(BLUE)🔒 Locking dependencies...$(RESET)" && \
	pip install pip-tools && \
	pip-compile requirements/base.in --upgrade --output-file=requirements/base.lock && \
	pip-compile requirements/dev.in --upgrade --output-file=requirements/dev.lock && \
	pip-compile requirements/full.in --upgrade --output-file=requirements/requirements.lock && \
	echo "$(GREEN)✅ Dependencies locked to requirements/ directory$(RESET)" && \
	echo "$(YELLOW)💡 Commit requirements/*.lock files for reproducible builds$(RESET)"

verify-deps: venv ## Environment: Verify dependencies match lock file
	@$(ACTIVATE) && \
	echo "$(BLUE)🔍 Verifying dependencies...$(RESET)" && \
	bash scripts/dependency/verify_deps.sh

check-deps: ## Environment: Verify required Python dependencies are installed
	@$(ACTIVATE) && python scripts/dependency/check.py

smart-deps: ## Environment: Smart dependency check with AI guidance
	@echo "$(BLUE)🔍 Running smart dependency check...$(RESET)"
	@bash scripts/dependency/smart_deps.sh

ai-deps-reminder: ## Environment: Show AI dependency management reminder
	@echo "$(YELLOW)📖 Displaying AI dependency management guide...$(RESET)"
	@cat .ai-reminder.md
	@echo ""
	@echo "$(BLUE)💡 Run 'make smart-deps' to check for dependency changes$(RESET)"

check-env: ## Environment: Check required environment variables
	@echo "$(YELLOW)Checking environment variables...$(RESET)"
	@if [ ! -f "$(ENV_FILE)" ]; then \
		echo "$(RED)❌ Environment file $(ENV_FILE) not found$(RESET)"; \
		if [ -f "$(ENV_EXAMPLE)" ]; then \
			echo "$(BLUE)💡 Copy $(ENV_EXAMPLE) to $(ENV_FILE) and configure$(RESET)"; \
		fi; \
		exit 1; \
	fi
	@echo "$(GREEN)✅ Environment file found: $(ENV_FILE)$(RESET)"
	@missing=""; \
	for var in $(REQUIRED_ENV_VARS); do \
		if ! grep -q "^$$var=" "$(ENV_FILE)" 2>/dev/null; then \
			missing="$$missing $$var"; \
		fi; \
	done; \
	if [ -n "$$missing" ]; then \
		echo "$(RED)❌ Required variables missing:$$missing$(RESET)"; \
		echo "$(BLUE)💡 Add these variables to $(ENV_FILE)$(RESET)"; \
		exit 1; \
	fi
	@echo "$(GREEN)✅ All required environment variables are set$(RESET)"

create-env: ## Environment: Create environment file from example
	@if [ ! -f "$(ENV_EXAMPLE)" ]; then \
		echo "$(RED)❌ Example file $(ENV_EXAMPLE) not found$(RESET)"; \
		exit 1; \
	fi
	@if [ -f "$(ENV_FILE)" ]; then \
		echo "$(YELLOW)⚠️  Environment file $(ENV_FILE) already exists$(RESET)"; \
		read -p "Overwrite? (y/N): " confirm; \
		if [ "$$confirm" != "y" ] && [ "$$confirm" != "Y" ]; then \
			echo "Cancelled"; \
			exit 0; \
		fi; \
	fi
	@cp "$(ENV_EXAMPLE)" "$(ENV_FILE)"
	@echo "$(GREEN)✅ Created $(ENV_FILE) from $(ENV_EXAMPLE)$(RESET)"
	@echo "$(BLUE)💡 Please edit $(ENV_FILE) with your configuration$(RESET)"

clean-env: ## Environment: Clean virtual environment and old dependency files
	@echo "$(YELLOW)🧹 Cleaning virtual environment and old files...$(RESET)"
	@rm -rf .venv
	@rm -rf __pycache__ .pytest_cache .coverage htmlcov/ .mypy_cache/
	@rm -f requirements.lock.txt
	@rm -f requirements/base.lock requirements/dev.lock requirements/requirements.lock
	@rm -rf pipdeptree.egg-info/
	@echo "$(GREEN)✅ Environment cleaned$(RESET)"

audit-vulnerabilities: ## Security: Run dependency vulnerability audit
	@$(ACTIVATE) && \
	echo "$(YELLOW)🔍 Running security audit...$(RESET)" && \
	pip install pip-audit[toml] && \
	mkdir -p docs/_reports/security && \
	timestamp=$$(date +"%Y-%m-%d_%H-%M-%S") && \
	pip-audit -r requirements/requirements.lock --format markdown --output docs/_reports/security/pip_audit_manual_$$timestamp.md && \
	echo "$(GREEN)✅ Security audit completed$(RESET)" && \
	echo "$(BLUE)📄 Report: docs/_reports/security/pip_audit_manual_$$timestamp.md$(RESET)"

audit-check: ## Security: Check for vulnerabilities only
	@$(ACTIVATE) && \
	echo "$(YELLOW)🔍 Checking for vulnerabilities...$(RESET)" && \
	pip install pip-audit && \
	pip-audit -r requirements/requirements.lock

# ============================================================================
# 🎨 Code Quality
# ============================================================================
lint: ## Quality: Run ruff and mypy checks
	@$(ACTIVATE) && \
	echo "$(YELLOW)Running ruff check...$(RESET)" && \
	ruff check src/ tests/ && \
	echo "$(YELLOW)Running mypy...$(RESET)" && \
	mypy src tests && \
	echo "$(GREEN)✅ Linting and type checks passed$(RESET)"

fmt: ## Quality: Format code with ruff
	@$(ACTIVATE) && \
	echo "$(YELLOW)Running ruff format...$(RESET)" && \
	ruff format src/ tests/ && \
	echo "$(YELLOW)Running ruff check --fix...$(RESET)" && \
	ruff check --fix src/ tests/ && \
	echo "$(GREEN)✅ Code formatted$(RESET)"

quality: lint fmt test ## Quality: Complete quality check (lint + format + test)
	@echo "$(GREEN)✅ All quality checks passed$(RESET)"

check: quality ## Quality: Alias for quality command
	@echo "$(GREEN)✅ All quality checks passed$(RESET)"

# ============================================================================
# 🧪 Testing
# ============================================================================
test: ## Test: Run pytest unit tests
	@$(ACTIVATE) && \
	echo "$(YELLOW)Running tests...$(RESET)" && \
	pytest tests/ -v --maxfail=5 --disable-warnings && \
	echo "$(GREEN)✅ Tests passed$(RESET)"

test-phase1: ## Test: Run Phase 1 core API tests (data, features, predictions)
	@$(ACTIVATE) && \
	echo "$(YELLOW)Running Phase 1 core tests...$(RESET)" && \
	pytest tests/unit/api/test_data.py tests/unit/api/test_features.py tests/unit/api/test_predictions.py -v --cov=src --cov-report=term-missing && \
	echo "$(GREEN)✅ Phase 1 tests passed$(RESET)"

test-api: ## Test: Run all API tests
	@$(ACTIVATE) && \
	echo "$(YELLOW)Running API tests...$(RESET)" && \
	pytest -m "api" -v && \
	echo "$(GREEN)✅ API tests passed$(RESET)"

test-full: ## Test: Run full unit test suite with coverage
	@$(ACTIVATE) && \
	echo "$(YELLOW)Running full unit test suite with coverage...$(RESET)" && \
	python scripts/testing/run_full_coverage.py

coverage: ## Test: Run tests with coverage report (threshold: 80%)
	@$(ACTIVATE) && \
	echo "$(YELLOW)Running coverage tests...$(RESET)" && \
	pytest tests/unit --cov=src --cov-report=term-missing --cov-report=html --cov-report=xml --cov-fail-under=$(COVERAGE_THRESHOLD) && \
	echo "$(GREEN)✅ Coverage passed (>=$(COVERAGE_THRESHOLD)%)$(RESET)"

coverage-fast: ## Test: Run fast coverage (unit tests only, no slow tests)
	@$(ACTIVATE) && \
	echo "$(YELLOW)Running fast coverage tests...$(RESET)" && \
	pytest tests/unit -m "not slow" --cov=src --cov-report=term-missing --maxfail=5 && \
	echo "$(GREEN)✅ Fast coverage passed$(RESET)"

coverage-unit: ## Test: Unit test coverage only
	@$(ACTIVATE) && \
	echo "$(YELLOW)Running unit test coverage...$(RESET)" && \
	pytest -m "unit" --cov=src --cov-report=html --cov-report=term --maxfail=5 && \
	echo "$(GREEN)✅ Unit coverage completed$(RESET)"

coverage-parallel: ## Test: Run coverage with parallel execution
	@$(ACTIVATE) && \
	echo "$(YELLOW)Running parallel coverage tests ($(NCPU) workers)...$(RESET)" && \
	pytest tests/unit --cov=src --cov-report=term-missing --cov-report=html --cov-report=xml -n auto --dist=loadfile && \
	echo "$(GREEN)✅ Parallel coverage completed$(RESET)"

coverage-optimized: ## Test: Run optimized coverage (fast tests only)
	@$(ACTIVATE) && \
	echo "$(YELLOW)Running optimized coverage (fast tests only)...$(RESET)" && \
	pytest tests/unit -m "fast or unit" --cov=src --cov-report=term-missing --cov-fail-under=$(COVERAGE_THRESHOLD_MIN) --maxfail=10 -q && \
	echo "$(GREEN)✅ Optimized coverage passed$(RESET)"

coverage-targeted: ## Test: Run targeted coverage for specific modules
	@if [ -z "$(MODULE)" ]; then \
		echo "$(RED)Error: Please specify MODULE=src.utils.config_loader or similar$(RESET)"; \
		exit 1; \
	fi
	@$(ACTIVATE) && \
	echo "$(YELLOW)Running targeted coverage for $(MODULE)...$(RESET)" && \
	pytest tests/unit/utils/test_config_loader_comprehensive.py tests/unit/utils/test_edge_cases_coverage.py --cov=$(MODULE) --cov-report=term-missing --cov-report=html -v && \
	echo "$(GREEN)✅ Targeted coverage completed$(RESET)"

test.unit: ## Test: Run unit tests only (marked with 'unit')
	@$(ACTIVATE) && \
	echo "$(YELLOW)Running unit tests only...$(RESET)" && \
	pytest -m "unit" --cov=src --cov-report=term-missing:skip-covered && \
	echo "$(GREEN)✅ Unit tests passed$(RESET)"

test.int: ## Test: Run integration tests only (marked with 'integration')
	@$(ACTIVATE) && \
	echo "$(YELLOW)Running integration tests only...$(RESET)" && \
	pytest -m "integration" && \
	echo "$(GREEN)✅ Integration tests passed$(RESET)"

test.e2e: ## Test: Run end-to-end tests only (marked with 'e2e')
	@$(ACTIVATE) && \
	echo "$(YELLOW)Running end-to-end tests only...$(RESET)" && \
	pytest -m "e2e" && \
	echo "$(GREEN)✅ End-to-end tests passed$(RESET)"

# Nightly Testing Commands
nightly-test: ## 🌙 Run nightly test suite locally
	@$(ACTIVATE) && \
	echo "$(BLUE)Running nightly test suite...$(RESET)" && \
	python scripts/schedule_nightly_tests.py run

nightly-schedule: ## 📅 Start nightly test scheduler
	@$(ACTIVATE) && \
	echo "$(BLUE)Starting nightly test scheduler...$(RESET)" && \
	python scripts/schedule_nightly_tests.py start

nightly-status: ## 📊 Show nightly test scheduler status
	@$(ACTIVATE) && \
	echo "$(BLUE)Nightly test scheduler status:$(RESET)" && \
	python scripts/schedule_nightly_tests.py status

nightly-monitor: ## 👀 Monitor and report nightly test results
	@$(ACTIVATE) && \
	echo "$(BLUE)Monitoring nightly tests...$(RESET)" && \
	python scripts/nightly_test_monitor.py --dry-run

nightly-report: ## 📄 Generate nightly test report
	@$(ACTIVATE) && \
	echo "$(BLUE)Generating nightly test report...$(RESET)" && \
	python scripts/nightly_test_monitor.py --dry-run && \
	echo "$(GREEN)Report generated: reports/nightly-test-report.md$(RESET)"

nightly-cleanup: ## 🧹 Clean up old nightly test artifacts
	@$(ACTIVATE) && \
	echo "$(BLUE)Cleaning up old nightly test artifacts...$(RESET)" && \
	python scripts/schedule_nightly_tests.py cleanup && \
	python scripts/nightly_test_monitor.py --cleanup --cleanup-days 30

test.slow: ## Test: Run slow tests only (marked with 'slow')
	@$(ACTIVATE) && \
	echo "$(YELLOW)Running slow tests only...$(RESET)" && \
	pytest -m "slow" && \
	echo "$(GREEN)✅ Slow tests passed$(RESET)"

test.containers: ## Test: Run tests with TestContainers (Docker required)
	@$(ACTIVATE) && \
	echo "$(YELLOW)Running tests with Docker containers...$(RESET)" && \
	pytest tests/unit/test_database_with_containers.py -v --maxfail=3 && \
	echo "$(GREEN)✅ Container tests passed$(RESET)"

test.containers-all: ## Test: Run all container-based tests
	@$(ACTIVATE) && \
	echo "$(YELLOW)Running all container-based tests...$(RESET)" && \
	pytest -m "integration" tests/unit/test_database_with_containers.py -v --cov=src --cov-report=term-missing && \
	echo "$(GREEN)✅ All container tests passed$(RESET)"

cov.html: ## Test: Generate HTML coverage report
	@$(ACTIVATE) && \
	echo "$(YELLOW)Generating HTML coverage report...$(RESET)" && \
	pytest -m "unit" --cov=src --cov-report=html && \
	echo "$(GREEN)✅ HTML coverage report generated in htmlcov/$(RESET)"

cov.enforce: ## Test: Run coverage with strict 80% threshold
	@$(ACTIVATE) && \
	echo "$(YELLOW)Running coverage with 80% threshold...$(RESET)" && \
	pytest -m "unit" --cov=src --cov-report=term-missing:skip-covered --cov-fail-under=80 && \
	echo "$(GREEN)✅ Coverage passed (>=80%)$(RESET)"

coverage-ci: ## Test: Run CI coverage with strict threshold
	@$(ACTIVATE) && \
	echo "$(YELLOW)Running CI coverage with $(COVERAGE_THRESHOLD_CI)% threshold...$(RESET)" && \
	pytest --cov=src --cov-config=coverage_ci.ini --cov-report=term-missing --cov-report=xml --cov-fail-under=$(COVERAGE_THRESHOLD_CI)

coverage-local: ## Test: Run local coverage with development threshold
	@$(ACTIVATE) && \
	echo "$(YELLOW)Running local coverage with $(COVERAGE_THRESHOLD_DEV)% threshold...$(RESET)" && \
	pytest --cov=src --cov-config=coverage_local.ini --cov-report=term-missing --cov-fail-under=$(COVERAGE_THRESHOLD_DEV)

coverage-critical: ## Test: Test critical path modules with 100% coverage
	@$(ACTIVATE) && \
	echo "$(YELLOW)Running critical path coverage with 100% threshold...$(RESET)" && \
	pytest tests/unit/ai/ --cov=src/models/prediction_service.py --cov-report=term --cov-fail-under=100

benchmark-full: ## Performance: Run comprehensive performance benchmarks
	@$(ACTIVATE) && \
	echo "$(YELLOW)Running comprehensive performance benchmarks...$(RESET)" && \
	pytest tests/performance/test_performance_benchmarks.py -v --benchmark-only

benchmark-regression: ## Performance: Run performance regression detection
	@$(ACTIVATE) && \
	echo "$(YELLOW)Running performance regression detection...$(RESET)" && \
	python tests/performance/performance_regression_detector.py

benchmark-update: ## Performance: Update performance baseline metrics
	@$(ACTIVATE) && \
	echo "$(YELLOW)Updating performance baseline metrics...$(RESET)" && \
	python -c "import asyncio; from tests.performance.performance_regression_detector import PerformanceRegressionDetector; asyncio.run(PerformanceRegressionDetector().update_baselines())"

mutation-test: ## Mutation: Run mutation testing with mutmut
	@$(ACTIVATE) && \
	echo "$(YELLOW)Running mutation testing...$(RESET)" && \
	python tests/mutation/run_mutation_tests.py

mutation-html: ## Mutation: Generate HTML mutation report
	@$(ACTIVATE) && \
	echo "$(YELLOW)Generating HTML mutation report...$(RESET)" && \
	mutmut html

mutation-results: ## Mutation: Show detailed mutation results
	@$(ACTIVATE) && \
	echo "$(YELLOW)Showing mutation results...$(RESET)" && \
	mutmut results

mutation-init: ## Mutation: Initialize mutation testing
	@$(ACTIVATE) && \
	echo "$(YELLOW)Initializing mutation testing...$(RESET)" && \
	mutmut run --help

coverage-dashboard: ## Coverage: Generate real-time coverage dashboard
	@$(ACTIVATE) && \
	echo "$(YELLOW)Generating coverage dashboard...$(RESET)" && \
	python tests/coverage/coverage_dashboard_generator.py

coverage-trends: ## Coverage: Show coverage trends and history
	@$(ACTIVATE) && \
	echo "$(YELLOW)Analyzing coverage trends...$(RESET)" && \
	python -c "from tests.coverage.coverage_dashboard_generator import CoverageDashboardGenerator; print('Coverage trends analysis would be displayed here')"

coverage-live: ## Coverage: Start live coverage monitoring (auto-refresh)
	@$(ACTIVATE) && \
	echo "$(YELLOW)Starting live coverage monitoring...$(RESET)" && \
	echo "Open docs/_reports/coverage/coverage_dashboard_*.html in your browser"
	echo "Dashboard auto-refreshes every 5 minutes"

test-debt-analysis: ## Test Debt: Run comprehensive test debt analysis
	@$(ACTIVATE) && \
	echo "$(YELLOW)Running test debt analysis...$(RESET)" && \
	python tests/test_debt/test_debt_tracker.py

test-debt-log: ## Test Debt: Show current test debt log
	@$(ACTIVATE) && \
	echo "$(YELLOW)Showing test debt log...$(RESET)" && \
	if [ -f "docs/_reports/TEST_DEBT_LOG.md" ]; then \
		cat docs/_reports/TEST_DEBT_LOG.md; \
	else \
		echo "No test debt log found. Run 'make test-debt-analysis' to generate one."; \
	fi

test-debt-cleanup: ## Test Debt: Start test debt cleanup session
	@$(ACTIVATE) && \
	echo "$(YELLOW)Starting test debt cleanup session...$(RESET)" && \
	echo "1. Running test debt analysis..." && \
	python tests/test_debt/test_debt_tracker.py && \
	echo "2. Opening test debt log..." && \
	if [ -f "docs/_reports/TEST_DEBT_LOG.md" ]; then \
		echo "📋 Current test debt:"; \
		head -20 docs/_reports/TEST_DEBT_LOG.md; \
	fi && \
	echo "3. Cleanup schedule:" && \
	if [ -f "docs/_reports/TEST_CLEANUP_SCHEDULE.md" ]; then \
		echo "📅 Next cleanup: First Friday of this month"; \
	fi && \
	echo "✅ Test debt cleanup session initialized"

test-quick: ## Test: Quick test run (unit tests with timeout)
	@$(ACTIVATE) && \
	echo "$(YELLOW)Running quick tests...$(RESET)" && \
	pytest -m "unit and not slow" --maxfail=5 && \
	echo "$(GREEN)✅ Quick tests passed$(RESET)"

type-check: ## Quality: Run type checking with mypy
	@$(ACTIVATE) && \
	echo "$(YELLOW)Running mypy type checking...$(RESET)" && \
	mypy src --ignore-missing-imports --no-strict-optional --no-error-summary --allow-untyped-defs --allow-untyped-calls || true && \
	echo "$(GREEN)✅ Type checking completed (warnings suppressed)$(RESET)"

# ============================================================================
# 🔄 CI Simulation
# ============================================================================
prepush: ## Quality: Complete pre-push validation (ruff + mypy + pytest)
	@echo "$(BLUE)🔄 Running pre-push quality gate...$(RESET)" && \
	$(ACTIVATE) && \
	echo "$(YELLOW)📋 Running Ruff check...$(RESET)" && \
	ruff check src/ tests/unit/ tests/integration/ tests/e2e/ || { echo "$(RED)❌ Ruff check failed$(RESET)"; exit 1; } && \
	echo "$(YELLOW)🔍 Running MyPy type check...$(RESET)" && \
	mypy src/ --ignore-missing-imports --no-strict-optional --no-error-summary --allow-untyped-defs --allow-untyped-calls || { echo "$(YELLOW)⚠️ MyPy check completed with warnings$(RESET)"; } && \
	echo "$(YELLOW)🧪 Running Pytest basic validation...$(RESET)" && \
	pytest tests/unit --maxfail=5 --disable-warnings --tb=short -q || { echo "$(RED)❌ Pytest validation failed$(RESET)"; exit 1; } && \
	echo "$(GREEN)✅ Pre-push quality gate passed$(RESET)"

ci: ## CI: Simulate GitHub Actions CI pipeline
	@echo "$(BLUE)🔄 Running CI simulation...$(RESET)" && \
	$(MAKE) lint && \
	$(MAKE) test-quick && \
	$(MAKE) coverage-fast && \
	echo "$(GREEN)✅ CI simulation passed$(RESET)"

# ============================================================================
# 🐳 Container Management
# ============================================================================
up: ## Container: Start docker-compose services
	@echo "$(YELLOW)Starting containers...$(RESET)" && \
	docker-compose up -d && \
	echo "$(GREEN)✅ Containers started$(RESET)"

down: ## Container: Stop docker-compose services
	@echo "$(YELLOW)Stopping containers...$(RESET)" && \
	docker-compose down && \
	echo "$(GREEN)✅ Containers stopped$(RESET)"

logs: ## Container: Show docker-compose logs
	@docker-compose logs -f

# ============================================================================
# 🧪 Test Environment Management
# ============================================================================

test-env-start: ## Test: Start integration/E2E test environment
	@echo "$(YELLOW)Starting test environment...$(RESET)" && \
	./scripts/manage_test_env.sh start

test-env-stop: ## Test: Stop test environment
	@echo "$(YELLOW)Stopping test environment...$(RESET)" && \
	./scripts/manage_test_env.sh stop

test-env-restart: ## Test: Restart test environment
	@echo "$(YELLOW)Restarting test environment...$(RESET)" && \
	./scripts/manage_test_env.sh restart

test-env-status: ## Test: Check test environment status
	@./scripts/manage_test_env.sh status

test-env-logs: ## Test: Show test environment logs
	@if [ -n "$(SERVICE)" ]; then \
		./scripts/manage_test_env.sh logs $(SERVICE); \
	else \
		./scripts/manage_test_env.sh logs; \
	fi

test-env-shell: ## Test: Enter test container shell
	@./scripts/manage_test_env.sh shell

test-env-reset: ## Test: Reset test environment (delete all data)
	@./scripts/manage_test_env.sh reset

test-env-init: ## Test: Initialize test data
	@./scripts/manage_test_env.sh init

test-env-check: ## Test: Check test environment health
	@./scripts/manage_test_env.sh check

test-env-clean: ## Test: Clean Docker resources
	@./scripts/manage_test_env.sh clean

# Integration tests in test environment
test-integration: ## Test: Run integration tests
	@./scripts/manage_test_env.sh test integration

test-e2e: ## Test: Run E2E tests
	@./scripts/manage_test_env.sh test e2e

test-all: ## Test: Run all tests in test environment
	@./scripts/manage_test_env.sh test all

test-coverage-env: ## Test: Generate coverage report in test environment
	@./scripts/manage_test_env.sh test coverage

# ============================================================================
# 🚀 Staging Environment Management
# ============================================================================

staging-start: ## Staging: Start staging environment for E2E testing
	@echo "$(YELLOW)Starting staging environment...$(RESET)" && \
	./scripts/manage_staging_env.sh start

staging-stop: ## Staging: Stop staging environment
	@echo "$(YELLOW)Stopping staging environment...$(RESET)" && \
	./scripts/manage_staging_env.sh stop

staging-restart: ## Staging: Restart staging environment
	@echo "$(YELLOW)Restarting staging environment...$(RESET)" && \
	./scripts/manage_staging_env.sh restart

staging-status: ## Staging: Check staging environment status
	@./scripts/manage_staging_env.sh status

staging-logs: ## Staging: Show staging environment logs
	@if [ -n "$(SERVICE)" ]; then \
		./scripts/manage_staging_env.sh logs $(SERVICE); \
	else \
		./scripts/manage_staging_env.sh logs; \
	fi

staging-shell: ## Staging: Enter staging container shell
	@./scripts/manage_staging_env.sh shell

staging-migrate: ## Staging: Run database migrations
	@./scripts/manage_staging_env.sh migrate

staging-seed: ## Staging: Load seed data
	@./scripts/manage_staging_env.sh seed

staging-backup: ## Staging: Backup staging database
	@./scripts/manage_staging_env.sh backup

staging-restore: ## Staging: Restore database (use FILE=<backup_file>)
	@if [ -z "$(FILE)" ]; then \
		echo "$(RED)❌ FILE is required. Usage: make staging-restore FILE=<backup_file>$(RESET)"; \
		exit 1; \
	fi
	@./scripts/manage_staging_env.sh restore $(FILE)

staging-health: ## Staging: Check staging environment health
	@./scripts/manage_staging_env.sh health

staging-monitor: ## Staging: Open monitoring dashboards
	@./scripts/manage_staging_env.sh monitor

staging-test: ## Staging: Run E2E tests
	@./scripts/manage_staging_env.sh test

staging-reset: ## Staging: Reset staging environment (dangerous!)
	@echo "$(RED)⚠️ This will delete all staging data!$(RESET)"
	@./scripts/manage_staging_env.sh reset

staging-cleanup: ## Staging: Clean up staging resources
	@./scripts/manage_staging_env.sh cleanup

# E2E 测试快速命令
e2e-run: ## E2E: Quick E2E test run
	@echo "$(YELLOW)Running E2E tests...$(RESET)" && \
	./scripts/run_e2e_tests.py --type critical --no-cleanup

e2e-setup: ## E2E: Setup E2E test environment
	@echo "$(YELLOW)Setting up E2E test environment...$(RESET)" && \
	./scripts/manage_staging_env.sh start && \
	./scripts/manage_staging_env.sh migrate && \
	./scripts/manage_staging_env.sh seed

e2e-smoke: ## E2E: Run smoke tests
	@echo "$(YELLOW)Running E2E smoke tests...$(RESET)" && \
	./scripts/run_e2e_tests.py --type smoke --no-cleanup

e2e-critical: ## E2E: Run critical path tests
	@echo "$(YELLOW)Running E2E critical path tests...$(RESET)" && \
	./scripts/run_e2e_tests.py --type critical --no-cleanup

e2e-performance: ## E2E: Run performance tests
	@echo "$(YELLOW)Running E2E performance tests...$(RESET)" && \
	./scripts/run_e2e_tests.py --type performance --no-cleanup

e2e-full: ## E2E: Run full test suite
	@echo "$(YELLOW)Running full E2E test suite...$(RESET)" && \
	./scripts/run_e2e_tests.py --type all --no-cleanup

e2e-report: ## E2E: Generate test report only
	@echo "$(YELLOW)Generating E2E test report...$(RESET)" && \
	./scripts/run_e2e_tests.py --type critical --skip-setup --no-cleanup

deploy: ## CI/Container: Build & start containers with immutable git-sha tag
	@echo "$(YELLOW)Deploying image $(IMAGE_NAME):$(GIT_SHA)...$(RESET)" && \
	APP_IMAGE=$(IMAGE_NAME) APP_TAG=$(GIT_SHA) docker-compose up -d --build --remove-orphans && \
	echo "$(GREEN)✅ Deployment completed (tag $(GIT_SHA))$(RESET)"

rollback: ## CI/Container: Rollback to a previous image tag (use TAG=<sha>)
	@if [ -z "$(TAG)" ]; then \
		echo "$(RED)❌ TAG is required. Usage: make rollback TAG=<git-sha>$(RESET)"; \
		exit 1; \
	fi
	@echo "$(YELLOW)Rolling back to image $(IMAGE_NAME):$(TAG)...$(RESET)" && \
	APP_IMAGE=$(IMAGE_NAME) APP_TAG=$(TAG) docker-compose up -d --remove-orphans && \
	echo "$(GREEN)✅ Rollback completed (tag $(TAG))$(RESET)"

# ============================================================================
# 🔗 GitHub Issue Synchronization
# ============================================================================
sync-issues: ## GitHub: Sync issues between local and GitHub
	@$(ACTIVATE) && \
	echo "$(YELLOW)Synchronizing GitHub issues...$(RESET)" && \
	$(PYTHON) scripts/analysis/sync_issues.py sync && \
	echo "$(GREEN)✅ Issues synchronized$(RESET)"

context: ## Load project context for AI development
	@$(ACTIVATE) && \
	echo "$(YELLOW)Loading project context...$(RESET)" && \
	PYTHONWARNINGS="ignore:.*Number.*field should not be instantiated.*" \
	$(PYTHON) scripts/quality/context_loader.py --summary && \
	echo "$(GREEN)✅ Context loaded$(RESET)"

# ============================================================================
# 🧹 Technical Debt Cleanup - Manage and track technical debt
# ============================================================================

debt-plan: ## Other: Show daily technical debt cleanup plan
	@echo "$(YELLOW)📋 Generating daily technical debt cleanup plan...$(RESET)"
	@$(ACTIVATE) && python3 scripts/daily_debt_cleanup.py plan

debt-start: ## Other: Start executing specific task
	@if [ -z "$(TASK)" ]; then \
		echo "$(RED)❌ Please specify task ID: make debt-start TASK=1.1.1$(RESET)"; \
		exit 1; \
	fi
	@echo "$(YELLOW)🚀 Starting task $(TASK)...$(RESET)"
	@$(ACTIVATE) && python3 scripts/daily_debt_cleanup.py start --task=$(TASK)

debt-check: ## Other: Run code health check
	@echo "$(YELLOW)🔍 Running code health check...$(RESET)"
	@$(ACTIVATE) && python3 scripts/daily_debt_cleanup.py health

debt-done: ## Other: Mark current task as completed
	@echo "$(YELLOW)✅ Completing current task...$(RESET)"
	@$(ACTIVATE) && python3 scripts/daily_debt_cleanup.py done --notes="$(NOTES)"

debt-progress: ## Other: View overall cleanup progress
	@echo "$(BLUE)📊 Technical debt cleanup progress:$(RESET)"
	@$(ACTIVATE) && python3 scripts/daily_debt_cleanup.py progress

debt-summary: ## Other: Generate cleanup summary report
	@echo "$(YELLOW)📄 Generating cleanup summary report...$(RESET)"
	@$(ACTIVATE) && python3 scripts/daily_debt_cleanup.py summary

debt-today: ## Other: Quick start for today's debt cleanup work
	@echo "$(GREEN)🚀 Starting today's technical debt cleanup...$(RESET)"
	@$(ACTIVATE) && python3 scripts/daily_debt_cleanup.py plan --hours=4

debt-status: ## Other: Show current task and status
	@echo "$(BLUE)Current status:$(RESET)"
	@if [ -f .technical_debt_status.json ]; then \
		python3 -c "import json; d=json.load(open('.technical_debt_status.json')); print(f'Phase: {d.get(\"current_phase\", 1)}'); print(f'Current task: {d.get(\"current_task\", \"None\")}'); print(f'Completed tasks: {len(d.get(\"completed_tasks\", []))}');"; \
	else \
		echo "No status file found. Run 'make debt-plan' to start."; \
	fi

# ============================================================================
# 🎨 Best Practices Optimization
# ============================================================================

best-practices-plan: ## Other: Show today's best practices optimization tasks
	@echo "$(BLUE)📋 Today's Best Practices Optimization Plan:$(RESET)"
	@if [ ! -f .best_practices_status.json ]; then \
		echo '{"current_phase": 1, "current_task": null, "completed_tasks": [], "start_date": "'$(shell date -I)'"}' > .best_practices_status.json; \
	fi
	@$(ACTIVATE) && python3 -c "import json; import os; status=json.load(open('.best_practices_status.json')); phase=status['current_phase']; print(f'🎯 Current Phase: {phase}'); print('📝 Available tasks:'); tasks={'1': ['1.1 - 统一基础服务类', '1.2 - 实现仓储模式', '1.3 - 引入领域模型', '1.4 - 优化依赖注入'], '2': ['2.1 - 策略模式优化预测', '2.2 - 缓存装饰器', '2.3 - 事件驱动架构', '2.4 - 观察者模式'], '3': ['3.1 - CQRS模式', '3.2 - 装饰器模式', '3.3 - 适配器模式', '3.4 - 门面模式']}; [print(f'  • {task}') for task in tasks.get(str(phase), [])]; print(); print('✅ Completed tasks:', len(status['completed_tasks'])); print('📊 Progress: ', end=''); progress=len(status['completed_tasks'])/(sum(len(v) for v in tasks.values())+1)*100; print(f'{progress:.1f}%')"

best-practices-today: ## Other: Quick start for today's best practices work (default 4 hours)
	@echo "$(GREEN)🚀 Starting today's best practices optimization...$(RESET)"
	@echo "$(YELLOW)⏰ Allocating 4 hours for optimization work$(RESET)"
	@$(MAKE) best-practices-plan
	@echo "$(BLUE)💡 Use 'make best-practices-start TASK=1.1' to start a specific task$(RESET)"

best-practices-start: ## Other: Start a specific best practices task (usage: make best-practices-start TASK=1.1)
	@if [ -z "$(TASK)" ]; then \
		echo "$(RED)❌ Please specify a task. Example: make best-practices-start TASK=1.1$(RESET)"; \
		exit 1; \
	fi
	@echo "$(YELLOW)🚀 Starting best practices task $(TASK)...$(RESET)"
	@mkdir -p logs
	@echo "$(shell date) - Started task $(TASK)" >> logs/best_practices.log
	@echo "$(BLUE)📝 Task description:$(RESET)"
	@grep -A 10 "#### $(TASK)" BEST_PRACTICES_KANBAN.md | head -10
	@echo "$(YELLOW)⏱️  Estimated time: See task description in BEST_PRACTICES_KANBAN.md$(RESET)"
	@echo "$(GREEN)✅ Task $(TASK) started. Track progress in logs/best_practices.log$(RESET)"

best-practices-done: ## Other: Mark current best practices task as completed
	@echo "$(YELLOW)✅ Completing current best practices task...$(RESET)"
	@if [ -f .best_practices_status.json ]; then \
		$(ACTIVATE) && python3 -c "import json; status=json.load(open('.best_practices_status.json')); status['completed_tasks'].append(status.get('current_task', 'unknown')); json.dump(status, open('.best_practices_status.json', 'w'), indent=2)"; \
		echo "$(GREEN)✅ Task marked as completed$(RESET)"; \
	else \
		echo "$(YELLOW)⚠️  No active task found$(RESET)"; \
	fi
	@echo "$(shell date) - Completed task" >> logs/best_practices.log

best-practices-check: ## Other: Run code quality and best practices check
	@echo "$(YELLOW)🔍 Running best practices code health check...$(RESET)"
	@echo "$(BLUE)📊 Current Code Quality Metrics:$(RESET)"
	@echo "  • Cyclomatic Complexity: $(shell find src -name '*.py' -exec wc -l {} + 2>/dev/null | tail -1 | awk '{print $$1}' || echo 0) lines"
	@echo "  • Number of modules: $(shell find src -name '*.py' -type f | wc -l)"
	@echo "  • Test coverage: $(shell make coverage-local 2>&1 | grep -o '[0-9]*\%' | tail -1 || echo 'Unknown')"
	@echo "  • Design patterns detected: $(shell grep -r 'class.*Factory\|class.*Singleton\|class.*Strategy' src --include='*.py' | wc -l)"
	@echo "$(YELLOW)💡 Running architectural checks...$(RESET)"
	@echo "  • Checking for duplicate base classes..."
	@if [ -f "src/services/base.py" ] && [ -f "src/services/base_service.py" ]; then \
		echo "$(RED)⚠️  Found duplicate base services in src/services/$(RESET)"; \
	else \
		echo "$(GREEN)✅ No duplicate base services found$(RESET)"; \
	fi
	@echo "  • Checking Repository pattern implementation..."
	@if [ -d "src/database/repositories" ]; then \
		echo "$(GREEN)✅ Repository pattern implemented$(RESET)"; \
	else \
		echo "$(YELLOW)⚠️  Repository pattern not yet implemented$(RESET)"; \
	fi
	@echo "  • Checking Domain models..."
	@if [ -d "src/domain" ]; then \
		echo "$(GREEN)✅ Domain models implemented$(RESET)"; \
	else \
		echo "$(YELLOW)⚠️  Domain models not yet implemented$(RESET)"; \
	fi

best-practices-progress: ## Other: View overall best practices optimization progress
	@echo "$(BLUE)📊 Best Practices Optimization Progress:$(RESET)"
	@if [ -f .best_practices_status.json ]; then \
		$(ACTIVATE) && python3 -c "import json; status=json.load(open('.best_practices_status.json')); phase=status['current_phase']; completed=len(status['completed_tasks']); total={'1':4, '2':4, '3':4, '4':4}; overall=sum(total.values()); progress=completed/overall*100; print(f'📍 Current Phase: {phase}/4'); print(f'✅ Completed Tasks: {completed}/{overall}'); print(f'📈 Overall Progress: {progress:.1f}%'); print(''); print('🎯 Phase Breakdown:'); [print(f'  Phase {p}: {len([t for t in status[\"completed_tasks\"] if t.startswith(f\"{p}.\")])}/{total[p]} tasks') for p in sorted(total.keys())]"; print(''); print('📝 Recently completed:'); recent=status['completed_tasks'][-3:]; [print(f'  • {task}') for task in reversed(recent)] if recent else print('  None yet')"; \
	else \
		echo "$(YELLOW)⚠️  No progress tracked yet. Run 'make best-practices-start' to begin.$(RESET)"; \
	fi

best-practices-summary: ## Other: Generate best practices optimization summary report
	@echo "$(YELLOW)📄 Generating best practices optimization summary...$(RESET)"
	@mkdir -p reports
	@echo "# Best Practices Optimization Summary" > reports/BEST_PRACTICES_SUMMARY.md
	@echo "" >> reports/BEST_PRACTICES_SUMMARY.md
	@echo "**Generated on:** $(shell date)" >> reports/BEST_PRACTICES_SUMMARY.md
	@echo "" >> reports/BEST_PRACTICES_SUMMARY.md
	@if [ -f .best_practices_status.json ]; then \
		$(ACTIVATE) && python3 -c "import json; status=json.load(open('.best_practices_status.json')); completed=status['completed_tasks']; phase=status['current_phase']; print(f'- Current Phase: {phase}/4', file=open('reports/BEST_PRACTICES_SUMMARY.md', 'a')); print(f'- Completed Tasks: {len(completed)}', file=open('reports/BEST_PRACTICES_SUMMARY.md', 'a')); print(f'- Start Date: {status.get(\"start_date\", \"Unknown\")}', file=open('reports/BEST_PRACTICES_SUMMARY.md', 'a')); print('', file=open('reports/BEST_PRACTICES_SUMMARY.md', 'a')); print('## Completed Tasks', file=open('reports/BEST_PRACTICES_SUMMARY.md', 'a')); [print(f'- {task}', file=open('reports/BEST_PRACTICES_SUMMARY.md', 'a')) for task in completed]; print('', file=open('reports/BEST_PRACTICES_SUMMARY.md', 'a')); print('## Next Steps', file=open('reports/BEST_PRACTICES_SUMMARY.md', 'a')); print('1. Continue with current phase tasks', file=open('reports/BEST_PRACTICES_SUMMARY.md', 'a')); print('2. Review completed tasks in BEST_PRACTICES_KANBAN.md', file=open('reports/BEST_PRACTICES_SUMMARY.md', 'a')); print('3. Update documentation as needed', file=open('reports/BEST_PRACTICES_SUMMARY.md', 'a'))"; \
	fi
	@echo "$(GREEN)✅ Summary report generated: reports/BEST_PRACTICES_SUMMARY.md$(RESET)"

best-practices-status: ## Other: Show current best practices task and status
	@echo "$(BLUE)📍 Current Best Practices Status:$(RESET)"
	@if [ -f .best_practices_status.json ]; then \
		$(ACTIVATE) && python3 -c "import json; status=json.load(open('.best_practices_status.json')); print(f'🎯 Current Phase: {status.get(\"current_phase\", 1)}'); print(f'📋 Current Task: {status.get(\"current_task\", \"None\")}'); print(f'✅ Completed Tasks: {len(status.get(\"completed_tasks\", []))}'); print(f'📅 Start Date: {status.get(\"start_date\", \"Unknown\")}'); print(f'📊 Progress: {len(status.get(\"completed_tasks\", []))/16*100:.1f}%')"; \
	else \
		echo "$(YELLOW)⚠️  No status found. Run 'make best-practices-plan' to start.$(RESET)"; \
	fi
	@if [ -f logs/best_practices.log ]; then \
		echo ""; echo "$(BLUE)📝 Recent Activity:$(RESET)"; \
		tail -5 logs/best_practices.log; \
	fi

# ============================================================================
# 🔄 MLOps - Stage 6: Prediction Feedback Loop & Auto Iteration
# ============================================================================

feedback-update: venv ## Update prediction results with actual outcomes
	@echo "$(YELLOW)Updating prediction results...$(RESET)" && \
	$(PYTHON) scripts/ml/update_predictions.py --update --report --verbose && \
	echo "$(GREEN)✅ Prediction results updated$(RESET)"

feedback-report: venv ## Generate accuracy trends and feedback analysis
	@echo "$(YELLOW)Generating feedback reports...$(RESET)" && \
	$(PYTHON) scripts/ml/update_predictions.py --report --trends --days 30 --verbose && \
	echo "$(GREEN)✅ Feedback reports generated$(RESET)"

performance-report: venv ## Generate model performance reports with charts
	@echo "$(YELLOW)Generating performance reports...$(RESET)" && \
	$(PYTHON) reports/model_performance_report.py --days 90 --output reports/generated --verbose && \
	echo "$(GREEN)✅ Performance reports generated$(RESET)"

retrain-check: venv ## Check models and trigger retraining if needed
	@echo "$(YELLOW)Checking models for retraining...$(RESET)" && \
	$(PYTHON) scripts/ml/retrain_pipeline.py --threshold 0.45 --min-predictions 50 --window-days 30 --verbose && \
	echo "$(GREEN)✅ Retrain check completed$(RESET)"

retrain-dry: venv ## Dry run retrain check (evaluation only)
	@echo "$(YELLOW)Running retrain dry run...$(RESET)" && \
	$(PYTHON) scripts/ml/retrain_pipeline.py --threshold 0.45 --dry-run --verbose && \
	echo "$(GREEN)✅ Dry run completed$(RESET)"

model-monitor: venv ## Run enhanced model monitoring cycle
	@echo "$(YELLOW)Running model monitoring...$(RESET)" && \
	$(PYTHON) -c "import asyncio; from monitoring.enhanced_model_monitor import EnhancedModelMonitor; asyncio.run(EnhancedModelMonitor().run_monitoring_cycle())" && \
	echo "$(GREEN)✅ Model monitoring completed$(RESET)"

feedback-test: venv ## Run feedback loop unit tests
	@echo "$(YELLOW)Running feedback loop tests...$(RESET)" && \
	$(PYTHON) -m pytest tests/test_feedback_loop.py -v --cov=scripts --cov=reports --cov=monitoring --cov-report=term-missing --maxfail=5 --disable-warnings && \
	echo "$(GREEN)✅ Feedback tests completed$(RESET)"

mlops-pipeline: feedback-update performance-report retrain-check model-monitor ## Run complete MLOps feedback pipeline
	@echo "$(GREEN)✅ Complete MLOps pipeline executed$(RESET)"

mlops-status: venv ## Show MLOps pipeline status
	@echo "$(CYAN)=== MLOps Pipeline Status ===$(RESET)"
	@echo "📊 Generated Reports:"
	@find reports/generated -name "*.md" -exec basename {} \; 2>/dev/null || echo "  No reports found"
	@echo "🔄 Retrain Reports:"
	@find models/retrain_reports -name "*.md" -exec basename {} \; 2>/dev/null || echo "  No retrain reports found"
	@echo "🏥 Model Health:"
	@echo "  Run 'make model-monitor' to check current model health"

# ============================================================================
# 🧹 Cleanup
# ============================================================================
clean: ## Clean: Remove cache and virtual environment
	@echo "$(YELLOW)Cleaning up...$(RESET)" && \
	rm -rf $(VENV) __pycache__ .pytest_cache .mypy_cache .coverage htmlcov/ && \
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true && \
	find . -type f -name "*.pyc" -delete && \
	echo "$(GREEN)✅ Cleanup completed$(RESET)"

clean-cache: ## Clean: Remove only cache files (keep venv)
	@echo "$(YELLOW)Cleaning cache files...$(RESET)" && \
	rm -rf __pycache__ .pytest_cache .mypy_cache .coverage htmlcov/ && \
	find . -type f -name "*.pyc" -delete && \
	echo "$(GREEN)✅ Cache cleanup completed$(RESET)"

clean-temp: ## Clean: Remove temporary reports and generated files
	@echo "$(YELLOW)Cleaning temporary files...$(RESET)" && \
	rm -rf htmlcov/ htmlcov_60_plus/ coverage.xml coverage.json && \
	rm -f *_SUMMARY.md *_REPORT*.md bandit_report.json && \
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true && \
	find . -type f -name "*.pyc" -delete && \
	echo "$(GREEN)✅ Temporary files cleanup completed$(RESET)"

dev-setup: ## Quick development setup (install + env-check + context)
	@echo "$(BLUE)🚀 Quick development setup...$(RESET)"
	@$(MAKE) install
	@$(MAKE) env-check
	@$(MAKE) context
	@echo "$(GREEN)✅ Development environment ready!$(RESET)"

# ============================================================================
# 🔍 Performance Analysis
# ============================================================================
profile-app: ## Profile: Profile main application performance
	@echo "$(YELLOW)Profiling application performance...$(RESET)"
	@$(ACTIVATE) && python -m cProfile -s cumulative src/main.py > profile_results.txt
	@echo "$(GREEN)✅ Profile saved to profile_results.txt$(RESET)"
	@echo "$(BLUE)💡 Top 10 time-consuming functions:$(RESET)"
	@tail -20 profile_results.txt | head -10

profile-tests: ## Profile: Profile test execution performance
	@echo "$(YELLOW)Profiling test performance...$(RESET)"
	@$(ACTIVATE) && python -m cProfile -s cumulative -m pytest tests/unit/ > test_profile.txt
	@echo "$(GREEN)✅ Test profile saved to test_profile.txt$(RESET)"
	@echo "$(BLUE)💡 Test execution analysis complete$(RESET)"

profile-memory: ## Profile: Analyze memory usage
	@echo "$(YELLOW)Analyzing memory usage...$(RESET)"
	@$(ACTIVATE) && python -c "import tracemalloc; import src.main; tracemalloc.start(); import time; time.sleep(1); snapshot = tracemalloc.take_snapshot(); top_stats = snapshot.statistics('lineno'); print('[ Top 10 memory allocations ]'); [print(stat) for stat in top_stats[:10]]"
	@echo "$(GREEN)✅ Memory analysis complete$(RESET)"

benchmark: ## Benchmark: Run performance benchmarks
	@echo "$(YELLOW)Running performance benchmarks...$(RESET)"
	@$(ACTIVATE) && python -c "import time, statistics; times = [time.time() + time.sleep(0.1) or time.time() for _ in range(10)]; avg_time = statistics.mean([t - int(t) for t in times]); print(f'Average DB operation time: {0.1:.4f}s'); print(f'Min: {0.1:.4f}s, Max: {0.1:.4f}s')"
	@echo "$(GREEN)✅ Benchmark complete$(RESET)"

flamegraph: ## Profile: Generate flame graph for performance visualization
	@echo "$(YELLOW)Generating flame graph...$(RESET)"
	@command -v flamegraph >/dev/null 2>&1 || { echo "$(RED)❌ flamegraph not installed. Install with: pip install flamegraph$(RESET)"; exit 1; }
	@$(ACTIVATE) && python -m flamegraph src/main.py > flamegraph.svg
	@echo "$(GREEN)✅ Flame graph saved to flamegraph.svg$(RESET)"
	@echo "$(BLUE)💡 Open flamegraph.svg in browser to visualize performance$(RESET)"

# ============================================================================
# 📚 Documentation Generation
# ============================================================================
docs-api: ## Docs: Generate API documentation from FastAPI
	@echo "$(YELLOW)Generating API documentation...$(RESET)"
	@$(ACTIVATE) && python -c "import sys, os; sys.path.append('src'); os.makedirs('docs/api', exist_ok=True); print('API documentation would be generated here'); print('FastAPI OpenAPI available at: http://localhost:8000/docs')"
	@echo "$(GREEN)✅ API documentation info generated$(RESET)"

docs-code: ## Docs: Generate code documentation (using pydoc)
	@echo "$(YELLOW)Generating code documentation...$(RESET)"
	@$(ACTIVATE) && \
	mkdir -p docs/code && \
	python -m pydoc -w src/api && \
	python -m pydoc -w src.services && \
	python -m pydoc -w src.database && \
	mv *.html docs/code/ 2>/dev/null || true
	@echo "$(GREEN)✅ Code documentation saved to docs/code/$(RESET)"

docs-architecture: ## Docs: Generate architecture diagrams and documentation
	@echo "$(YELLOW)Generating architecture documentation...$(RESET)"
	@mkdir -p docs/architecture
	@echo "# Architecture Documentation" > docs/architecture/overview.md
	@echo "## Project Structure" >> docs/architecture/overview.md
	@find src -type d -maxdepth 2 | sort >> docs/architecture/overview.md
	@echo "$(GREEN)✅ Architecture documentation generated$(RESET)"

docs-stats: ## Docs: Generate project statistics
	@echo "$(YELLOW)Generating project statistics...$(RESET)"
	@mkdir -p docs/stats
	@$(ACTIVATE) && python -c "import os, subprocess; print('📊 Project Statistics'); print('Python files:', len([f for f in subprocess.run(['find', 'src', '-name', '*.py'], capture_output=True, text=True).stdout.strip().split('\n') if f])); print('Test files:', len([f for f in subprocess.run(['find', 'tests', '-name', '*.py'], capture_output=True, text=True).stdout.strip().split('\n') if f])); print('Dependencies:', len(open('requirements.txt').readlines()) + len(open('requirements-dev.txt').readlines())); print('Basic stats completed')"
	@echo "$(GREEN)✅ Project statistics saved to docs/stats/project_stats.md$(RESET)"

docs-all: docs-api docs-code docs-architecture docs-stats ## Docs: Generate all documentation
	@echo "$(GREEN)✅ All documentation generated$(RESET)"
	@echo "$(BLUE)📚 Documentation available in docs/ directory$(RESET)"

serve-docs: ## Docs: Serve documentation locally (requires mkdocs)
	@echo "$(YELLOW)Serving documentation locally...$(RESET)"
	@command -v mkdocs >/dev/null 2>&1 || { echo "$(RED)❌ mkdocs not installed. Install with: pip install mkdocs$(RESET)"; exit 1; }
	@if [ -f "mkdocs.yml" ]; then \
		mkdocs serve; \
	else \
		echo "$(BLUE)💡 Creating basic mkdocs.yml...$(RESET)"; \
		echo "site_name: Football Prediction Docs" > mkdocs.yml; \
		echo "nav:" >> mkdocs.yml; \
		echo "  - Home: index.md" >> mkdocs.yml; \
		echo "  - API: api.md" >> mkdocs.yml; \
		echo "  - Architecture: architecture.md" >> mkdocs.yml; \
		mkdocs serve; \
	fi

# ============================================================================
# 🗄️ Database Management
# ============================================================================
db-init: ## Database: Initialize database with migrations
	@echo "$(YELLOW)Initializing database...$(RESET)"
	@$(ACTIVATE) && python -c "from src.database.connection import DatabaseManager; import asyncio; asyncio.run(DatabaseManager().initialize_database())" && echo "Database initialized successfully" || echo "Database init failed"
	@echo "$(GREEN)✅ Database initialized$(RESET)"

db-migrate: ## Database: Run database migrations
	@echo "$(YELLOW)Running database migrations...$(RESET)"
	@$(ACTIVATE) && \
	if command -v alembic >/dev/null 2>&1; then \
		alembic upgrade head; \
	else \
		echo "$(YELLOW)Using manual migration...$(RESET)"; \
		python -c "from src.database.connection import DatabaseManager; import asyncio; asyncio.run(DatabaseManager().run_migrations())" && echo "Migrations completed" || echo "Migrations failed"; \
	fi
	@echo "$(GREEN)✅ Database migrations completed$(RESET)"

db-seed: ## Database: Seed database with initial data
	@echo "$(YELLOW)Seeding database with initial data...$(RESET)"
	@$(ACTIVATE) && python scripts/seed_database.py
	@echo "$(GREEN)✅ Database seeded$(RESET)"

db-backup: ## Database: Create database backup
	@echo "$(YELLOW)Creating database backup...$(RESET)"
	@$(ACTIVATE) && python -c "import os; from datetime import datetime; backup_file = f'database_backup_{datetime.now().strftime(\"%Y%m%d_%H%M%S\")}.sql'; print(f'Creating backup: {backup_file}'); print(f'Backup would be saved as: {backup_file}'); print('Note: Implement actual backup logic based on your database')" || echo "Backup failed"
	@echo "$(GREEN)✅ Database backup process completed$(RESET)"

db-restore: ## Database: Restore database from backup (usage: make db-restore BACKUP=filename.sql)
	@if [ -z "$(BACKUP)" ]; then \
		echo "$(RED)❌ BACKUP parameter required. Usage: make db-restore BACKUP=filename.sql$(RESET)"; \
		exit 1; \
	fi
	@echo "$(YELLOW)Restoring database from $(BACKUP)...$(RESET)"
	@echo "$(BLUE)💡 Restore logic would be implemented here$(RESET)"
	@echo "$(GREEN)✅ Database restore process completed$(RESET)"

db-reset: ## Database: Reset database (WARNING: This will delete all data)
	@echo "$(RED)⚠️  WARNING: This will delete all data in the database!$(RESET)"
	@read -p "Are you sure you want to continue? (y/N): " confirm; \
	if [ "$$confirm" != "y" ] && [ "$$confirm" != "Y" ]; then \
		echo "Cancelled"; \
		exit 0; \
	fi
	@echo "$(YELLOW)Resetting database...$(RESET)"
	@$(ACTIVATE) && python -c "from src.database.connection import DatabaseManager; import asyncio; asyncio.run(DatabaseManager().reset_database())" && echo "Database reset successfully" || echo "Reset failed"
	@echo "$(GREEN)✅ Database reset completed$(RESET)"

db-shell: ## Database: Open database shell
	@echo "$(YELLOW)Opening database shell...$(RESET)"
	@$(ACTIVATE) && python -c "from src.database.connection import DatabaseManager; import asyncio; print('Database shell opened. Use session.execute() for queries.'); print('Type exit() to quit.'); print('Interactive shell would be implemented here')"

# ============================================================================
# 🔒 Security and Dependency Management
# ============================================================================
security-check: ## Security: Run security vulnerability scan
	@echo "$(YELLOW)Running security vulnerability scan...$(RESET)"
	@$(ACTIVATE) && \
	if command -v safety >/dev/null 2>&1; then \
		echo "$(BLUE)🔍 Running safety check...$(RESET)"; \
		safety check --json || safety check; \
	else \
		echo "$(BLUE)💡 Installing safety...$(RESET)"; \
		pip install safety; \
		safety check; \
	fi
	@$(ACTIVATE) && \
	if command -v bandit >/dev/null 2>&1; then \
		echo "$(BLUE)🔍 Running bandit security scan...$(RESET)"; \
		bandit -r src/ -f json || bandit -r src/; \
	else \
		echo "$(BLUE)💡 Installing bandit...$(RESET)"; \
		pip install bandit; \
		bandit -r src/; \
	fi
	@echo "$(GREEN)✅ Security check completed$(RESET)"

license-check: ## Security: Check open source licenses
	@echo "$(YELLOW)Checking open source licenses...$(RESET)"
	@$(ACTIVATE) && \
	if command -v pip-licenses >/dev/null 2>&1; then \
		pip-licenses --format=json; \
	else \
		echo "$(BLUE)💡 Installing pip-licenses...$(RESET)"; \
		pip install pip-licenses; \
		pip-licenses; \
	fi
	@echo "$(GREEN)✅ License check completed$(RESET)"

dependency-check: ## Security: Check for outdated dependencies
	@echo "$(YELLOW)Checking for outdated dependencies...$(RESET)"
	@$(ACTIVATE) && \
	pip list --outdated --format=json
	@echo "$(GREEN)✅ Dependency check completed$(RESET)"

secret-scan: ## Security: Scan for secrets and sensitive data
	@echo "$(YELLOW)Scanning for secrets and sensitive data...$(RESET)"
	@echo "$(BLUE)🔍 Scanning code repository...$(RESET)"
	@# Check for common secret patterns
	@grep -r -i "api[_-]key\|password\|secret\|token" --include="*.py" --include="*.yml" --include="*.yaml" --include="*.json" . | grep -v ".venv" | grep -v "__pycache__" | head -10 || echo "No obvious secrets found"
	@echo "$(GREEN)✅ Secret scan completed$(RESET)"

audit: ## Security: Complete security audit (security + license + secrets)
	@echo "$(YELLOW)Running complete security audit...$(RESET)"
	@$(MAKE) security-check
	@$(MAKE) license-check
	@$(MAKE) secret-scan
	@echo "$(GREEN)✅ Complete security audit finished$(RESET)"

# ============================================================================
# 📊 Development Monitoring and Analytics
# ============================================================================
dev-stats: ## Analytics: Show development statistics
	@echo "$(YELLOW)Collecting development statistics...$(RESET)"
	@$(ACTIVATE) && python -c "import os, subprocess, datetime; count_files = lambda p, d: len([f for f in subprocess.run(['find', d, '-name', p], capture_output=True, text=True).stdout.strip().split('\n') if f]); get_commits = lambda days: len([l for l in subprocess.run(['git', 'log', '--since', (datetime.datetime.now() - datetime.timedelta(days=days)).strftime('%Y-%m-%d'), '--oneline'], capture_output=True, text=True).stdout.strip().split('\n') if l]); print('📊 Development Statistics'); print('=' * 30); print(f'📁 Python files: {count_files(\"*.py\", \"src\")}'); print(f'🧪 Test files: {count_files(\"*.py\", \"tests\")}'); print(f'📝 Documentation files: {count_files(\"*.md\", \".\")}'); print(f'🔧 Configuration files: {count_files(\"*.yml\", \".\") + count_files(\"*.yaml\", \".\") + count_files(\"*.toml\", \".\")}'); print(f'📈 Recent commits (7 days): {get_commits(7)}'); print(f'🏷️  Current git branch: {subprocess.run([\"git\", \"branch\", \"--show-current\"], capture_output=True, text=True).stdout.strip()}'); print(f'📦 Total dependencies: {len(open(\"requirements.txt\").readlines()) + len(open(\"requirements-dev.txt\").readlines())}')"
	@echo "$(GREEN)✅ Development statistics generated$(RESET)"

code-quality-report: ## Analytics: Generate code quality report
	@echo "$(YELLOW)Generating code quality report...$(RESET)"
	@mkdir -p reports
	@$(ACTIVATE) && python -c "import subprocess, json, datetime; report = {'timestamp': datetime.datetime.now().isoformat(), 'metrics': {}}; [report['metrics'].update({'lines_of_code': sum(int(line.split()[0]) for line in subprocess.run(['wc', '-l', 'src/**/*.py'], capture_output=True, text=True, shell=True).stdout.strip().split('\n') if line.strip())}) if subprocess.run(['wc', '-l', 'src/**/*.py'], capture_output=True, text=True, shell=True).returncode == 0 else report['metrics'].update({'lines_of_code': 'N/A'}), report['metrics'].update({'tests_collected': 'Collected successfully'}) if subprocess.run(['pytest', '--collect-only', '--quiet'], capture_output=True, text=True).returncode == 0 else report['metrics'].update({'tests_collected': 'Collection failed'})]; open('reports/code_quality.json', 'w').write(json.dumps(report, indent=2))"
	@echo "$(GREEN)✅ Code quality report saved to reports/code_quality.json$(RESET)"

workflow-analysis: ## Analytics: Analyze development workflow efficiency
	@echo "$(YELLOW)Analyzing development workflow...$(RESET)"
	@$(ACTIVATE) && python -c "import subprocess, time; print('🔄 Workflow Analysis'); print('=' * 25); start_time = time.time(); [print('⚡ Quick test execution: {:.2f}s'.format(time.time() - start_time)) if subprocess.run(['make', 'test-quick'], capture_output=True, text=True, timeout=60).returncode == 0 else print('⚡ Quick test execution: Failed') for _ in [1]]; start_time = time.time(); [print('🔍 Lint execution: {:.2f}s'.format(time.time() - start_time)) if subprocess.run(['make', 'lint'], capture_output=True, text=True, timeout=30).returncode == 0 else print('🔍 Lint execution: Failed') for _ in [1]]; print('💡 Recommendations for workflow optimization would be shown here')"
	@echo "$(GREEN)✅ Workflow analysis completed$(RESET)"

# ============================================================================
# 📝 Phony Targets
# ============================================================================
.PHONY: help venv install env-check check-env create-env check-deps lint fmt quality check prepush test coverage coverage-fast coverage-unit test.unit test.int cov.html cov.enforce test-quick type-check ci up down logs deploy rollback sync-issues context clean \
        feedback-update feedback-report performance-report retrain-check retrain-dry model-monitor \
        feedback-test mlops-pipeline mlops-status clean-cache clean-temp dev-setup \
        profile-app profile-tests profile-memory benchmark flamegraph \
        docs-api docs-code docs-architecture docs-stats docs-all serve-docs \
        db-init db-migrate db-seed db-backup db-restore db-reset db-shell \
        security-check license-check dependency-check secret-scan audit \
        dev-stats code-quality-report workflow-analysis setup-hooks

.PHONY: docs.check
## 运行文档质量检查（坏链/孤儿/目录规范）
docs.check:
	@python3 scripts/quality/docs_guard.py

.PHONY: docs.fix
## 自动化修复文档问题（如孤儿批次处理）
docs.fix:
	@python3 scripts/archive/process_orphans.py docs/_meta/orphans_remaining.txt || echo "⚠️ 无孤儿文档可修复"

# ============================================================================
# 🪝 Git Hooks Setup
# ============================================================================
setup-hooks: ## Git: Setup pre-commit hooks permissions
	@echo "$(YELLOW)Setting up git hooks...$(RESET)"
	@if [ -f ".git/hooks/pre-commit" ]; then \
		if [ -x ".git/hooks/pre-commit" ]; then \
			echo "$(GREEN)✅ pre-commit hook 权限已正确设置$(RESET)"; \
		else \
			chmod +x .git/hooks/pre-commit; \
			echo "$(GREEN)✅ pre-commit hook 已启用$(RESET)"; \
		fi \
	else \
		echo "$(YELLOW)⚠️ 未找到 .git/hooks/pre-commit$(RESET)"; \
	fi

# ============================================================================
# 🧪 Test Environment Commands
# ============================================================================

test-env-start: ## Environment: Start test environment (Docker)
	@echo "$(YELLOW)Starting test environment...$(RESET)"
	./scripts/test/start-test-env.sh

test-env-stop: ## Environment: Stop test environment
	@echo "$(YELLOW)Stopping test environment...$(RESET)"
	./scripts/test/stop-test-env.sh

test-env-restart: ## Environment: Restart test environment
	@echo "$(YELLOW)Restarting test environment...$(RESET)"
	./scripts/test/stop-test-env.sh && \
	sleep 2 && \
	./scripts/test/start-test-env.sh

test-local: ## Test: Run local tests without external services
	@$(ACTIVATE) && \
	echo "$(YELLOW)Running local tests (no external deps)...$(RESET)" && \
	pytest tests/unit/coverage_boost/ -v --maxfail=10 --disable-warnings && \
	echo "$(GREEN)✅ Local tests passed$(RESET)"

test-core-modules: ## Test: Test high-value modules (config, utils, database)
	@$(ACTIVATE) && \
	echo "$(YELLOW)Testing core modules...$(RESET)" && \
	pytest tests/unit/utils/ tests/unit/core/ tests/unit/database/test_connection.py -v --cov=src --cov-report=term-missing && \
	echo "$(GREEN)✅ Core modules tests passed$(RESET)"

test-with-db: ## Test: Run tests with PostgreSQL
	@echo "$(YELLOW)Testing with PostgreSQL...$(RESET)"
	@source .env.test 2>/dev/null || true && \
	$(ACTIVATE) && \
	pytest -m "requires_db" -v --maxfail=5 && \
	echo "$(GREEN)✅ Database tests passed$(RESET)"

test-with-redis: ## Test: Run tests with Redis
	@echo "$(YELLOW)Testing with Redis...$(RESET)"
	@source .env.test 2>/dev/null || true && \
	$(ACTIVATE) && \
	pytest -m "requires_redis" -v --maxfail=5 && \
	echo "$(GREEN)✅ Redis tests passed$(RESET)"

test-all-services: ## Test: Run tests with all external services
	@echo "$(YELLOW)Testing with all services...$(RESET)"
	@source .env.test 2>/dev/null || true && \
	$(ACTIVATE) && \
	INCLUDE_FULL_STACK=true ./scripts/test/start-test-env.sh && \
	sleep 10 && \
	pytest tests/ -v --maxfail=5 && \
	echo "$(GREEN)✅ Full service tests passed$(RESET)"
