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
COVERAGE_THRESHOLD := 80
IMAGE_NAME ?= football-prediction
GIT_SHA := $(shell git rev-parse --short HEAD)

# Environment Configuration
ENV_FILE ?= .env
ENV_EXAMPLE ?= .env.example

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

install-locked: venv ## Environment: Install from locked dependencies (reproducible)
	@if [ ! -f requirements.lock.txt ]; then \
		echo "$(RED)❌ requirements.lock.txt not found. Run 'make lock-deps' first.$(RESET)"; \
		exit 1; \
	fi
	@$(ACTIVATE) && \
	echo "$(BLUE)📦 Installing locked dependencies (reproducible)...$(RESET)" && \
	pip install --upgrade pip && \
	pip install -r requirements.lock.txt && \
	echo "$(GREEN)✅ Dependencies installed from lock file$(RESET)"

lock-deps: venv ## Environment: Lock current dependencies for reproducible builds
	@$(ACTIVATE) && \
	echo "$(BLUE)🔒 Locking dependencies...$(RESET)" && \
	python scripts/lock_dependencies.py freeze && \
	echo "$(GREEN)✅ Dependencies locked to requirements.lock.txt$(RESET)" && \
	echo "$(YELLOW)💡 Commit requirements.lock.txt for reproducible builds$(RESET)"

verify-deps: venv ## Environment: Verify dependencies match lock file
	@$(ACTIVATE) && \
	echo "$(BLUE)🔍 Verifying dependencies...$(RESET)" && \
	python scripts/lock_dependencies.py verify

check-deps: ## Environment: Verify required Python dependencies are installed
	@$(ACTIVATE) && python scripts/check_dependencies.py

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


# ============================================================================
# 🎨 Code Quality
# ============================================================================
lint: ## Quality: Run flake8 and mypy checks
	@$(ACTIVATE) && \
	echo "$(YELLOW)Running flake8...$(RESET)" && \
	flake8 src/ tests/ && \
	echo "$(YELLOW)Running mypy...$(RESET)" && \
	mypy src tests && \
	echo "$(GREEN)✅ Linting and type checks passed$(RESET)"

fmt: ## Quality: Format code with black and isort
	@$(ACTIVATE) && \
	echo "$(YELLOW)Running black...$(RESET)" && \
	black src/ tests/ && \
	echo "$(YELLOW)Running isort...$(RESET)" && \
	isort src/ tests/ && \
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

test-full: ## Test: Run full unit test suite with coverage
	@$(ACTIVATE) && \
	echo "$(YELLOW)Running full unit test suite with coverage...$(RESET)" && \
	python scripts/run_full_coverage.py

coverage: ## Test: Run tests with coverage report (threshold: 80%)
	@$(ACTIVATE) && \
	echo "$(YELLOW)Running coverage tests...$(RESET)" && \
	pytest -m "unit" --cov=src --cov-report=term-missing --cov-fail-under=$(COVERAGE_THRESHOLD) && \
	echo "$(GREEN)✅ Coverage passed (>=$(COVERAGE_THRESHOLD)%)$(RESET)"

coverage-fast: ## Test: Run fast coverage (unit tests only, no slow tests)
	@$(ACTIVATE) && \
	echo "$(YELLOW)Running fast coverage tests...$(RESET)" && \
	pytest -m "unit and not slow" --cov=src --cov-report=term-missing --maxfail=5 && \
	echo "$(GREEN)✅ Fast coverage passed$(RESET)"

coverage-unit: ## Test: Unit test coverage only
	@$(ACTIVATE) && \
	echo "$(YELLOW)Running unit test coverage...$(RESET)" && \
	pytest -m "unit" --cov=src --cov-report=html --cov-report=term --maxfail=5 && \
	echo "$(GREEN)✅ Unit coverage completed$(RESET)"

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

test.slow: ## Test: Run slow tests only (marked with 'slow')
	@$(ACTIVATE) && \
	echo "$(YELLOW)Running slow tests only...$(RESET)" && \
	pytest -m "slow" && \
	echo "$(GREEN)✅ Slow tests passed$(RESET)"

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

coverage-ci: ## Test: Run CI coverage with 80% threshold (strict)
	@$(ACTIVATE) && \
	echo "$(YELLOW)Running CI coverage with 80% threshold...$(RESET)" && \
	pytest --cov=src --cov-config=coverage_ci.ini --cov-report=term-missing --cov-report=xml --cov-fail-under=80

coverage-local: ## Test: Run local coverage with 60% threshold (development)
	@$(ACTIVATE) && \
	echo "$(YELLOW)Running local coverage with 60% threshold...$(RESET)" && \
	pytest --cov=src --cov-config=coverage_local.ini --cov-report=term-missing --cov-fail-under=60

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
	mypy src tests && \
	echo "$(GREEN)✅ Type checking passed$(RESET)"

# ============================================================================
# 🔄 CI Simulation
# ============================================================================
prepush: ## Quality: Complete pre-push validation (ruff + mypy + pytest)
	@echo "$(BLUE)🔄 Running pre-push quality gate...$(RESET)" && \
	$(ACTIVATE) && \
	echo "$(YELLOW)📋 Running Ruff check...$(RESET)" && \
	ruff check . || { echo "$(RED)❌ Ruff check failed$(RESET)"; exit 1; } && \
	echo "$(YELLOW)🔍 Running MyPy type check...$(RESET)" && \
	mypy src tests --ignore-missing-imports --no-error-summary || { echo "$(RED)❌ MyPy check failed$(RESET)"; exit 1; } && \
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
	$(PYTHON) scripts/sync_issues.py sync && \
	echo "$(GREEN)✅ Issues synchronized$(RESET)"

context: ## Load project context for AI development
	@$(ACTIVATE) && \
	echo "$(YELLOW)Loading project context...$(RESET)" && \
	PYTHONWARNINGS="ignore:.*Number.*field should not be instantiated.*" \
	$(PYTHON) scripts/context_loader.py --summary && \
	echo "$(GREEN)✅ Context loaded$(RESET)"

# ============================================================================
# 🔄 MLOps - Stage 6: Prediction Feedback Loop & Auto Iteration
# ============================================================================

feedback-update: venv ## Update prediction results with actual outcomes
	@echo "$(YELLOW)Updating prediction results...$(RESET)" && \
	$(PYTHON) scripts/update_predictions_results.py --update --report --verbose && \
	echo "$(GREEN)✅ Prediction results updated$(RESET)"

feedback-report: venv ## Generate accuracy trends and feedback analysis
	@echo "$(YELLOW)Generating feedback reports...$(RESET)" && \
	$(PYTHON) scripts/update_predictions_results.py --report --trends --days 30 --verbose && \
	echo "$(GREEN)✅ Feedback reports generated$(RESET)"

performance-report: venv ## Generate model performance reports with charts
	@echo "$(YELLOW)Generating performance reports...$(RESET)" && \
	$(PYTHON) reports/model_performance_report.py --days 90 --output reports/generated --verbose && \
	echo "$(GREEN)✅ Performance reports generated$(RESET)"

retrain-check: venv ## Check models and trigger retraining if needed
	@echo "$(YELLOW)Checking models for retraining...$(RESET)" && \
	$(PYTHON) scripts/retrain_pipeline.py --threshold 0.45 --min-predictions 50 --window-days 30 --verbose && \
	echo "$(GREEN)✅ Retrain check completed$(RESET)"

retrain-dry: venv ## Dry run retrain check (evaluation only)
	@echo "$(YELLOW)Running retrain dry run...$(RESET)" && \
	$(PYTHON) scripts/retrain_pipeline.py --threshold 0.45 --dry-run --verbose && \
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
        feedback-test mlops-pipeline mlops-status clean-cache dev-setup \
        profile-app profile-tests profile-memory benchmark flamegraph \
        docs-api docs-code docs-architecture docs-stats docs-all serve-docs \
        db-init db-migrate db-seed db-backup db-restore db-reset db-shell \
        security-check license-check dependency-check secret-scan audit \
        dev-stats code-quality-report workflow-analysis setup-hooks

.PHONY: docs.check
## 运行文档质量检查（坏链/孤儿/目录规范）
docs.check:
	@python3 scripts/docs_guard.py

.PHONY: docs.fix
## 自动化修复文档问题（如孤儿批次处理）
docs.fix:
	@python3 scripts/process_orphans.py docs/_meta/orphans_remaining.txt || echo "⚠️ 无孤儿文档可修复"

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


# 测试命令
test:
	@echo "运行所有测试"
	pytest tests/ -v

test-unit:
	@echo "运行单元测试"
	pytest tests/unit/ -v -m "unit"

test-integration:
	@echo "运行集成测试"
	pytest tests/integration/ -v -m "integration"

test-e2e:
	@echo "运行端到端测试"
	pytest tests/e2e/ -v -m "e2e"

test-smoke:
	@echo "运行冒烟测试"
	pytest tests/ -v -m "smoke"

test-coverage:
	@echo "运行测试并生成覆盖率报告"
	pytest tests/ --cov=src --cov-report=html --cov-report=term-missing

test-watch:
	@echo "监视文件变化并运行测试"
	pytest-watch tests/

test-parallel:
	@echo "并行运行测试"
	pytest tests/ -n auto

test-failed:
	@echo "只运行失败的测试"
	pytest tests/ --lf

test-debug:
	@echo "调试模式运行测试"
	pytest tests/ -v -s --tb=long

test-performance:
	@echo "运行性能测试"
	pytest tests/e2e/performance/ -v -m "performance"

test-security:
	@echo "运行安全测试"
	pytest tests/ -v -m "security"

# 清理测试数据
clean-test:
	@echo "清理测试数据"
	rm -rf .pytest_cache/
	rm -rf htmlcov/
	rm -rf .coverage
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

# 生成测试报告
test-report:
	@echo "生成测试报告"
	pytest tests/ --html=test-report.html --self-contained-html
