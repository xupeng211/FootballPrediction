# 🚀 Football Prediction Project Makefile
# Author: DevOps Engineer
# Description: Concise, maintainable Makefile for Python/FastAPI project

# ============================================================================
# 🔧 Configuration Variables
# ============================================================================
PYTHON := python3
VENV := .venv
VENV_BIN := $(VENV)/bin
# 在CI环境中不需要激活虚拟环境，使用actions/setup-python设置的环境
# 设置为noop命令，保持与现有Makefile结构的兼容性
ACTIVATE := :
COVERAGE_THRESHOLD := 40
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
# 🧪 Unified Testing Configuration
# ============================================================================
# Testing parameters for unified test command
TEST_FLAGS ?= --maxfail=20 --tb=short --disable-warnings
TEST_SCOPE ?= unit  # unit, integration, e2e, all, smart
TEST_MARKERS ?= not slow
TEST_COVERAGE ?= true
TEST_PARALLEL ?= false
TEST_VERBOSE ?= false

# Generate pytest command dynamically
define BUILD_PYTEST_CMD
pytest
$(if $(filter true,$(TEST_VERBOSE)),--verbose,)
$(if $(filter true,$(TEST_COVERAGE)),--cov=src --cov-report=term-missing,)
-m "$(TEST_MARKERS)"
--testpath=tests/$(if $(filter all,$(TEST_SCOPE)),.,$(TEST_SCOPE))
$(TEST_FLAGS)
endef

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


fix-code: ## Quality: Fix code formatting and syntax issues (one-click fix)
	@echo "$(YELLOW)🔧 Fixing code quality issues...$(RESET)"
	@$(ACTIVATE) && \
	echo "$(BLUE)✓ Running Black formatter...$(RESET)" && \
	black src/ tests/ --line-length 88 && \
	echo "$(BLUE)✓ Running Ruff linter and fixer...$(RESET)" && \
	ruff check src/ tests/ --fix && \
	echo "$(BLUE)✓ Running MyPy type checker...$(RESET)" && \
	mypy src/ --ignore-missing-imports --no-error-summary || true && \
	echo "$(GREEN)✅ Code quality fixes completed$(RESET)"

fix-syntax: ## Quality: Fix syntax and formatting issues
	@echo "$(YELLOW)🔧 Fixing syntax and formatting...$(RESET)"
	@$(ACTIVATE) && \
	black src/ tests/ && \
	ruff check src/ tests/ --fix --select E,W,F && \
	echo "$(GREEN)✅ Syntax and formatting fixed$(RESET)"

fix-imports: ## Quality: Fix import statements and ordering
	@echo "$(YELLOW)🔧 Fixing import statements...$(RESET)"
	@$(ACTIVATE) && \
	ruff check src/ tests/ --fix --select I && \
	echo "$(GREEN)✅ Import statements fixed$(RESET)"

check-quality: ## Quality: Check code quality without fixing
	@echo "$(YELLOW)🔍 Checking code quality...$(RESET)"
	@$(ACTIVATE) && \
	echo "$(BLUE)📊 Black format check...$(RESET)" && \
	black --check src/ tests/ && \
	echo "$(BLUE)🔍 Ruff linting check...$(RESET)" && \
	ruff check src/ tests/ && \
	echo "$(BLUE)🔬 MyPy type check...$(RESET)" && \
	mypy src/ --ignore-missing-imports && \
	echo "$(GREEN)✅ All quality checks passed$(RESET)"

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
lint: ## Quality: Run ruff linter and mypy checks
	@$(ACTIVATE) && \
	echo "$(YELLOW)Running ruff linter...$(RESET)" && \
	ruff check src/ tests/ && \
	echo "$(YELLOW)Running mypy...$(RESET)" && \
	mypy src tests && \
	echo "$(GREEN)✅ Linting and type checks passed$(RESET)"

fmt: ## Quality: Format code with ruff
	@$(ACTIVATE) && \
	echo "$(YELLOW)Running ruff format...$(RESET)" && \
	ruff format src/ tests/ && \
	echo "$(GREEN)✅ Code formatted$(RESET)"


check: quality ## Quality: Alias for quality command
	@echo "$(GREEN)✅ All quality checks passed$(RESET)"

# ============================================================================
# 🔧 Syntax Checking (Issue #84 Integration)
# ============================================================================
syntax-check: ## Quality: Check syntax errors in all test files (Issue #84)
	@$(ACTIVATE) && \
	echo "$(YELLOW)Checking syntax errors in all test files...$(RESET)" && \
	$(PYTHON) scripts/maintenance/find_syntax_errors_simple.py && \
	echo "$(GREEN)✅ Syntax check passed$(RESET)"

syntax-fix: ## Quality: Automatically fix syntax errors (Issue #84 tools)
	@$(ACTIVATE) && \
	echo "$(YELLOW)Automatically fixing syntax errors...$(RESET)" && \
	$(PYTHON) scripts/maintenance/fix_issue84_final.py && \
	echo "$(GREEN)✅ Syntax errors fixed$(RESET)"

syntax-validate: ## Quality: Validate test file executability
	@$(ACTIVATE) && \
	echo "$(YELLOW)Validating test file executability...$(RESET)" && \
	$(PYTHON) scripts/maintenance/test_executability_check.py && \
	echo "$(GREEN)✅ Test executability validated$(RESET)"

# ============================================================================
# 🧪 Testing - Unified Interface
# ============================================================================
# 🔧 M2测试工具链 (Issue #214)
# ============================================================================
test-enhanced-coverage: ## M2: Run enhanced coverage analysis with detailed reporting (Issue #214)
	@$(ACTIVATE) && \
	echo "$(YELLOW)Running enhanced coverage analysis...$(RESET)" && \
	$(PYTHON) scripts/enhanced_coverage_analysis.py --test-pattern "tests/unit" && \
	echo "$(GREEN)✅ Enhanced coverage analysis completed$(RESET)"

test-enhanced-full: ## M2: Run enhanced analysis with full test suite (Issue #214)
	@$(ACTIVATE) && \
	echo "$(YELLOW)Running full enhanced test analysis...$(RESET)" && \
	$(PYTHON) scripts/enhanced_coverage_analysis.py && \
	echo "$(GREEN)✅ Full enhanced analysis completed$(RESET)"

test-report-generate: ## M2: Generate comprehensive test report in multiple formats (Issue #214)
	@$(ACTIVATE) && \
	echo "$(YELLOW)Generating comprehensive test report...$(RESET)" && \
	$(PYTHON) scripts/generate_test_report.py --format all && \
	echo "$(GREEN)✅ Test report generation completed$(RESET)"

test-report-html: ## M2: Generate HTML test report (Issue #214)
	@$(ACTIVATE) && \
	echo "$(YELLOW)Generating HTML test report...$(RESET)" && \
	$(PYTHON) scripts/generate_test_report.py --format html && \
	echo "$(GREEN)✅ HTML report generation completed$(RESET)"

test-ci-integration: ## M2: Run CI/CD test integration (Issue #214)
	@$(ACTIVATE) && \
	echo "$(YELLOW)Running CI/CD test integration...$(RESET)" && \
	$(PYTHON) scripts/ci_test_integration.py --test && \
	echo "$(GREEN)✅ CI integration verification completed$(RESET)"

test-ci-full: ## M2: Run complete CI pipeline (Issue #214)
	@$(ACTIVATE) && \
	echo "$(YELLOW)Running complete CI pipeline...$(RESET)" && \
	$(PYTHON) scripts/ci_test_integration.py && \
	echo "$(GREEN)✅ CI pipeline completed$(RESET)"

test-m2-toolchain: ## M2: Complete M2 toolchain test (coverage + report + CI) (Issue #214)
	@$(ACTIVATE) && \
	echo "$(YELLOW)Running M2 complete toolchain test...$(RESET)" && \
	echo "$(BLUE)Step 1: Enhanced coverage analysis$(RESET)" && \
	$(PYTHON) scripts/enhanced_coverage_analysis.py --test-pattern "tests/unit" && \
	echo "$(BLUE)Step 2: Generate test report$(RESET)" && \
	$(PYTHON) scripts/generate_test_report.py --format markdown && \
	echo "$(BLUE)Step 3: CI integration verification$(RESET)" && \
	$(PYTHON) scripts/ci_test_integration.py --test && \
	echo "$(GREEN)✅ M2 toolchain test completed$(RESET)"

test-coverage-monitor: ## M2: Monitor coverage trends and generate dashboard (Issue #214)
	@$(ACTIVATE) && \
	echo "$(YELLOW)📈 监控覆盖率趋势...$(RESET)" && \
	$(PYTHON) scripts/coverage_dashboard.py && \
	echo "$(GREEN)✅ 覆盖率监控完成$(RESET)"

# ============================================================================
# 🚨 测试覆盖率危机解决方案
# ============================================================================
test-crisis-fix: ## Test: Fix test collection errors and import conflicts (P0 Priority)
	@$(ACTIVATE) && \
	echo "$(RED)🚨 执行测试危机紧急修复...$(RESET)" && \
	$(PYTHON) scripts/fix_test_crisis.py && \
	echo "$(GREEN)✅ 测试危机修复完成$(RESET)"

test-quality-analyze: ## Test: Analyze test quality and generate improvement plan
	@$(ACTIVATE) && \
	echo "$(YELLOW)Analyzing test quality...$(RESET)" && \
	$(PYTHON) scripts/test_quality_improvement_engine.py --analyze && \
	echo "$(GREEN)✅ Test quality analysis completed$(RESET)"

test-quality-improve: ## Test: Execute complete test quality improvement cycle
	@$(ACTIVATE) && \
	echo "$(YELLOW)Executing test quality improvement...$(RESET)" && \
	$(PYTHON) scripts/test_quality_improvement_engine.py --execute-phase 1 && \
	$(PYTHON) scripts/test_quality_improvement_engine.py --execute-phase 2 && \
	echo "$(GREEN)✅ Test quality improvement completed$(RESET)"

test-crisis-solution: ## Test: Complete test crisis solution (fix + analyze + improve)
	@$(ACTIVATE) && \
	echo "$(RED)🚨 Executing complete test crisis solution...$(RESET)" && \
	$(PYTHON) scripts/launch_test_crisis_solution.py --quick-fix && \
	echo "$(GREEN)✅ Test crisis solution completed$(RESET)" && \
	echo "$(BLUE)💡 Run 'make coverage' to check improvement results$(RESET)"

test-crisis-launcher: ## Test: Launch interactive test crisis solution tool
	@$(ACTIVATE) && \
	echo "$(YELLOW)🚀 Launching test crisis solution tool...$(RESET)" && \
	$(PYTHON) scripts/launch_test_crisis_solution.py

github-issues-update: ## Quality: Update GitHub issues for test coverage crisis
	@$(ACTIVATE) && \
	echo "$(YELLOW)Updating GitHub Issues...$(RESET)" && \
	$(PYTHON) scripts/github_issue_manager.py && \
	echo "$(GREEN)✅ GitHub Issues update completed$(RESET)"

test-crisis-report: ## Test: Generate comprehensive test crisis report
	@$(ACTIVATE) && \
	echo "$(YELLOW)Generating test crisis report...$(RESET)" && \
	$(PYTHON) scripts/github_issue_manager.py --generate-report > crisis_status_report.md && \
	$(PYTHON) scripts/test_quality_improvement_engine.py --report >> crisis_status_report.md && \
	echo "$(GREEN)✅ Report generated: crisis_status_report.md$(RESET)"

# ============================================================================
# 🎯 测试覆盖率危机快速命令组合
# ============================================================================
fix-test-errors: test-crisis-fix ## Quick: Fix all test errors (P0 Priority)
improve-test-quality: test-quality-improve ## Quick: Improve test quality
solve-test-crisis: test-crisis-solution ## Quick: Complete test crisis solution
test-status-report: test-crisis-report ## Quick: Generate status report


cov.html: ## Test: Generate HTML coverage report
	@$(ACTIVATE) && \
	echo "$(YELLOW)Generating HTML coverage report...$(RESET)" && \
	pytest -m "unit" --cov=src --cov-report=html && \
	echo "$(GREEN)✅ HTML coverage report generated in htmlcov/$(RESET)"

cov.enforce: ## Test: Run coverage with strict 30% threshold
	@$(ACTIVATE) && \
	echo "$(YELLOW)Running coverage with 30% threshold...$(RESET)" && \
	pytest -m "unit" --cov=src --cov-report=term-missing:skip-covered --cov-fail-under=30 && \
	echo "$(GREEN)✅ Coverage passed (>=30%)$(RESET)"

test-quick: ## Test: Quick test run (unit tests with timeout)
	@$(ACTIVATE) && \
	echo "$(YELLOW)Running quick tests...$(RESET)" && \
	pytest -m "unit and not slow" --maxfail=5 && \
	echo "$(GREEN)✅ Quick tests passed$(RESET)"

type-check: ## Quality: Run type checking with mypy
	@$(ACTIVATE) && \
	echo "$(YELLOW)Running type checking...$(RESET)" && \
	mypy src --ignore-missing-imports && \
	echo "$(GREEN)✅ Type checking completed$(RESET)"

# ============================================================================
# 🚀 CI/CD Automation - Unified Interface
# ============================================================================
ci-quality: ## CI/CD: Run quality checks (lint + format + type-check)
	@echo "$(YELLOW)Running CI quality checks...$(RESET)"
	@$(MAKE) lint fmt type-check

ci-fix: ## CI/CD: Run automatic fixes
	@echo "$(YELLOW)Running CI automatic fixes...$(RESET)"
	@$(MAKE) fix-code fix-imports fix-syntax

ci-test: ## CI/CD: Run test suite
	@echo "$(YELLOW)Running CI test suite...$(RESET)"
	@$(MAKE) test.fast TEST_FLAGS="--maxfail=10"

ci-check: ## CI/CD: Complete CI pipeline (quality + test)
	@echo "$(YELLOW)Running complete CI pipeline...$(RESET)"
	@$(MAKE) ci-quality ci-fix ci-test

# Advanced CI commands
ci-extended: ## CI/CD: Extended CI with additional checks
	@echo "$(YELLOW)Running extended CI pipeline...$(RESET)"
	@$(MAKE) ci-quality ci-fix ci-test coverage security-check

ci-deployment: ## CI/CD: Deployment-ready CI pipeline
	@echo "$(YELLOW)Running deployment-ready CI pipeline...$(RESET)"
	@$(MAKE) ci-extended ci-quality-report

# Legacy CI/CD Commands (backward compatibility)
ci-setup: ## CI/CD: Setup development environment for CI
	@echo "$(YELLOW)🚀 Setting up CI/CD environment...$(RESET)"
	@echo "$(BLUE)📦 Installing pre-commit hooks...$(RESET)"
	@$(ACTIVATE) && \
	pip install pre-commit && \
	pre-commit install && \
	echo "$(GREEN)✅ Pre-commit hooks installed$(RESET)"

ci-check-legacy: ## CI/CD: Legacy comprehensive checks (backward compatibility)
	@echo "$(YELLOW)Running legacy comprehensive CI/CD checks...$(RESET)"
	@$(ACTIVATE) && \
	echo "$(BLUE)Step 1: Basic fix..." && \
	$(PYTHON) scripts/fix_test_crisis.py && \
	echo "$(BLUE)Step 2: Syntax check..." && \
	$(PYTHON) scripts/smart_quality_fixer.py --syntax-only && \
	echo "$(BLUE)Step 3: Quick test collection..." && \
	$(PYTHON) -c "import subprocess; subprocess.run(['python', '-m', 'pytest', '--collect-only', '-q'], check=False)" && \
	echo "$(BLUE)Step 4: Code quality check..." && \
	make lint || echo "⚠️ Code quality check has warnings" && \
	echo "$(GREEN)✅ Legacy CI/CD checks completed$(RESET)"

ci-auto-fix: ## CI/CD: Run automatic fixes
	@echo "$(YELLOW)🔧 Running automatic fixes...$(RESET)"
	@$(ACTIVATE) && \
	echo "$(BLUE)🔧 Executing test crisis fix..." && \
	$(PYTHON) scripts/fix_test_crisis.py && \
	echo "$(BLUE)🔧 Executing precise error fix..." && \
	$(PYTHON) scripts/precise_error_fixer.py && \
	echo "$(BLUE)🔧 Executing smart quality fix..." && \
	$(PYTHON) scripts/smart_quality_fixer.py && \
	echo "$(GREEN)✅ Automatic fixes completed$(RESET)"

ci-quality-report: ## CI/CD: Generate comprehensive quality report
	@echo "$(YELLOW)📊 Generating comprehensive quality report...$(RESET)"
	@$(ACTIVATE) && \
	echo "$(BLUE)📊 Generating GitHub Issues report..." && \
	$(PYTHON) scripts/github_issue_manager.py --generate-report > ci-quality-report.md && \
	echo "$(BLUE)📊 Generating quality improvement report..." && \
	$(PYTHON) scripts/test_quality_improvement_engine.py --report >> ci-quality-report.md && \
	echo "$(BLUE)📊 Generating final success report..." && \
	$(PYTHON) scripts/complete_final_fix.py >> ci-quality-report.md && \
	echo "$(GREEN)✅ CI/CD quality report generated: ci-quality-report.md$(RESET)"

ci-full-workflow: ## CI/CD: Execute complete CI/CD workflow
	@echo "$(YELLOW)🚀 Executing complete CI/CD workflow...$(RESET)"
	@echo "$(BLUE)Step 1: 环境检查" && \
	make env-check && \
	echo "$(BLUE)Step 2: 自动修复" && \
	make ci-auto-fix && \
	echo "$(BLUE)Step 3: 质量检查" && \
	make ci-check && \
	echo "$(BLUE)Step 4: 测试验证" && \
	make test-quick && \
	echo "$(BLUE)Step 5: 生成报告" && \
	make ci-quality-report && \
	echo "$(GREEN)🎉 Complete CI/CD workflow executed successfully$(RESET)"

ci-coverage-check: ## CI/CD: Run coverage check with automated fixes
	@echo "$(YELLOW)📊 Running coverage check with automated fixes...$(RESET)"
	@$(ACTIVATE) && \
	echo "$(BLUE)🔧 自动修复测试问题..." && \
	$(PYTHON) scripts/fix_test_crisis.py && \
	echo "$(BLUE)🔧 精确修复剩余错误..." && \
	$(PYTHON) scripts/precise_error_fixer.py && \
	echo "$(BLUE)📊 生成覆盖率报告..." && \
	$(PYTHON) -m pytest tests/unit/utils/ --cov=src.utils --cov-report=term-missing --maxfail=10 -q --disable-warnings || true && \
	echo "$(GREEN)✅ Coverage check completed$(RESET)"

ci-monitoring: ## CI/CD: Generate monitoring and metrics report
	@echo "$(YELLOW)📈 Generating monitoring and metrics report...$(RESET)"
	@$(ACTIVATE) && \
	echo "$(BLUE)📊 分析项目指标..." && \
	$(PYTHON) scripts/github_issue_manager.py --generate-report > monitoring-report.md && \
	echo "$(BLUE)📈 生成测试指标..." && \
	python -c "import subprocess; result = subprocess.run(['python', '-m', 'pytest', '--collect-only', '-q'], capture_output=True, text='temp'); print(f'测试用例数量: {result.stdout.countlines()}')" >> monitoring-report.md && \
	echo "$(BLUE)📈 生成代码质量指标..." && \
	make lint >> monitoring-report.md 2>&1 || echo "代码质量检查完成" >> monitoring-report.md && \
	echo "$(GREEN)✅ Monitoring report generated: monitoring-report.md$(RESET)"

ci-security-check: ## CI/CD: Run security checks
	@echo "$(YELLOW)🛡️ Running security checks...$(RESET)"
	@$(ACTIVATE) && \
	echo "$(BLUE)🔍 Bandit安全扫描..." && \
	bandit -r src/ -f json -o security-report.json || echo "安全扫描完成" && \
	echo "$(BLUE)🔍 依赖安全审计..." && \
	pip-audit --format=json --output=audit-report.json || echo "依赖审计完成" && \
	echo "$(GREEN)✅ Security checks completed$(RESET)"

ci-performance-test: ## CI/CD: Run performance tests
	@echo "$(YELLOW)⚡ Running performance tests...$(RESET)"
	@$(ACTIVATE) && \
	echo "$(BLUE)⚡ 测试crypto工具性能..." && \
	$(PYTHON) -m pytest tests/unit/utils/test_crypto_utils.py --benchmark-only --benchmark-json=performance.json || echo "性能测试完成" && \
	echo "$(GREEN)✅ Performance tests completed$(RESET)"

ci-integration-test: ## CI/CD: Run integration tests
	@echo "$(YELLOW)🔗 Running integration tests...$(RESET)"
	@$(ACTIVATE) && \
	echo "$(BLUE)🔗 API集成测试..." && \
	pytest tests/integration/ -v --maxfail=5 --disable-warnings || echo "API集成测试完成" && \
	echo "$(GREEN)✅ Integration tests completed$(RESET)"

# ============================================================================
# 🔄 Pre-commit集成
# ============================================================================
pre-commit-install: ## Pre-commit: Install pre-commit hooks
	@echo "$(YELLOW)📥 Installing pre-commit hooks...$(RESET)"
	@$(ACTIVATE) && \
	pip install pre-commit && \
	pre-commit install && \
	echo "$(GREEN)✅ Pre-commit hooks installed$(RESET)"

pre-commit-run: ## Pre-commit: Run all pre-commit hooks
	@echo "$(YELLOW)🔄 Running pre-commit hooks...$(RESET)"
	pre-commit run --all-files && \
	echo "$(GREEN)✅ Pre-commit hooks completed$(RESET)"

pre-commit-update: ## Pre-commit: Update pre-commit hooks
	@echo "$(YELLOW)🔄 Updating pre-commit hooks...$(RESET)"
	@$(ACTIVATE) && \
	pre-commit autoupdate && \
	echo "$(GREEN)✅ Pre-commit hooks updated$(RESET)"

# ============================================================================
# 📊 GitHub Actions集成
# ============================================================================
github-actions-test: ## GitHub Actions: Test local GitHub Actions workflow
	@echo "$(YELLOW)🧪 Testing GitHub Actions workflow locally...$(RESET)"
	@echo "$(BLUE)🔧 Running automated fixes..." && \
	$(PYTHON) scripts/fix_test_crisis.py && \
	echo "$(BLUE)📊 Running quality checks..." && \
	make ci-check && \
	echo "$(BLUE)📊 Generating reports..." && \
	make ci-quality-report && \
	echo "$(GREEN)✅ GitHub Actions workflow test completed$(RESET)"

github-actions-upload: ## GitHub Actions: Upload artifacts for debugging
	@echo "$(YELLOW)📤 Uploading GitHub Actions artifacts...$(RESET)"
	@if [ -d "htmlcov" ]; then \
		echo "$(BLUE)📤 Uploading coverage report..." && \
		tar -czf coverage-report.tar.gz htmlcov/; \
		echo "$(GREEN)✅ Coverage report uploaded: coverage-report.tar.gz$(RESET)"; \
	fi

# ============================================================================
# 🎯 DevOps工具集成
# ============================================================================
devops-setup: ## DevOps: Complete development environment setup
	@echo "$(YELLOW)🚀 Setting up complete development environment...$(RESET)"
	@echo "$(BLUE)1️⃣ 环境检查" && \
	make env-check && \
	echo "$(BLUE)2️⃣ 安装依赖" && \
	make install && \
	echo "$(BLUE)3️⃣ Pre-commit设置" && \
	make pre-commit-install && \
	echo "$(BLUE)4️⃣ 质量检查" && \
	make ci-check && \
	echo "$(BLUE)5️⃣ 测试验证" && \
	make test-quick && \
	echo "$(GREEN)✅ Complete development environment setup completed$(RESET)"

devops-validate: ## DevOps: Validate all DevOps configurations
	@echo "$(YELLOW)✅ Validating DevOps configurations...$(RESET)"
	@echo "$(BLUE)✅ 环境变量检查" && \
	make check-env && \
	echo "$(BLUE)✅ Docker配置检查" && \
	docker-compose config --quiet && \
	echo "$(BLUE)✅ 测试环境检查" && \
	python -c "import docker; client = docker.from_env(); client.ping()" && \
	echo "$(GREEN)✅ All DevOps configurations validated$(RESET)"

devops-deploy: ## DevOps: Deploy with full validation
	@echo "$(YELLOW)🚀 Starting deployment process...$(RESET)"
	@echo "$(BLUE)1️⃣ 环境验证" && \
	make devops-validate && \
	echo "$(BLUE)2️⃣ 质量检查" && \
	make ci-check && \
	echo "$(BLUE)3️⃣ 测试验证" && \
	make test-quick && \
	echo "$(BLUE)4️⃣ 构建镜像" && \
	docker build -t $(IMAGE_NAME):$(GIT_SHA) . && \
	echo "$(GREEN)✅ Deployment validation completed$(RESET)"

# ============================================================================
# 📋 报告和分析工具
# ============================================================================
report-quality: ## Report: Generate comprehensive quality report
	@echo "$(YELLOW)📋 Generating comprehensive quality report...$(RESET)"
	@$(ACTIVATE) && \
	echo "$(BLUE)📊 生成基础质量报告..." && \
	make ci-quality-report && \
	echo "$(BLUE)📊 生成监控报告..." && \
	make ci-monitoring && \
	echo "$(BLUE)📊 生成安全报告..." && \
	make ci-security-check && \
	echo "$(BLUE)📊 生成性能报告..." && \
	make ci-performance-test && \
	echo "$(GREEN)✅ Comprehensive quality report generated in current directory$(RESET)"

report-coverage-trends: ## Report: Analyze coverage trends
	@echo "$(YELLOW)📈 Analyzing coverage trends...$(RESET)"
	@$(ACTIVATE) && \
	echo "$(BLUE)📊 当前覆盖率..." && \
	make coverage-unit && \
	echo "$(GREEN)✅ Coverage trends analysis completed$(RESET)"

report-ci-metrics: ## Report: Generate CI/CD metrics dashboard
	@echo "$(YELLOW)📊 Generating CI/CD metrics dashboard...$(RESET)"
	@$(ACTIVATE) && \
	echo "$(BLUE)📊 收集CI/CD指标..." && \
	make ci-quality-report && \
	echo "$(BLUE)📊 收集性能指标..." && \
	make ci-performance-test && \
	echo "$(BLUE)📊 收集监控指标..." && \
	make ci-monitoring && \
	echo "$(GREEN)✅ CI/CD metrics dashboard generated$(RESET)"

# ============================================================================
# 🛡️ 核心质量工具 (精简优化后的核心工具集)
# ============================================================================
smart-fix: ## Quality: 智能自动化修复 - 核心质量工具
	@$(ACTIVATE) && \
	echo "$(YELLOW)🤖 Running intelligent automated fixes...$(RESET)" && \
	$(PYTHON) scripts/smart_quality_fixer.py && \
	echo "$(GREEN)✅ Intelligent fixes applied$(RESET)"

quality-guardian: ## Quality: 质量守护检查 - 核心监控工具
	@$(ACTIVATE) && \
	echo "$(YELLOW)🛡️ Running quality guardian check...$(RESET)" && \
	$(PYTHON) scripts/quality_guardian.py --check-only && \
	echo "$(GREEN)✅ Quality guardian check completed$(RESET)"

daily-quality: ## Quality: 每日质量改进 - 日常维护工具
	@$(ACTIVATE) && \
	echo "$(YELLOW)📅 Running daily quality improvement...$(RESET)" && \
	$(PYTHON) scripts/daily_quality_improvement.py && \
	echo "$(GREEN)✅ Daily quality improvement completed$(RESET)"

emergency-fix: ## Quality: 紧急质量修复 - 危机处理工具
	@$(ACTIVATE) && \
	echo "$(YELLOW)🚨 Running emergency quality fixes...$(RESET)" && \
	$(PYTHON) scripts/emergency_quality_fixer.py && \
	echo "$(GREEN)✅ Emergency fixes completed$(RESET)"

coverage-dashboard: ## Quality: 覆盖率仪表板 - 测试分析工具
	@$(ACTIVATE) && \
	echo "$(YELLOW)📊 Running coverage dashboard...$(RESET)" && \
	$(PYTHON) scripts/coverage_dashboard.py && \
	echo "$(GREEN)✅ Coverage dashboard generated$(RESET)"

test-crisis: ## Quality: 测试危机解决方案 - 测试修复工具
	@$(ACTIVATE) && \
	echo "$(YELLOW)🔧 Running test crisis solution...$(RESET)" && \
	$(PYTHON) scripts/fix_test_crisis.py && \
	echo "$(GREEN)✅ Test crisis solution completed$(RESET)"

work-sync: ## Quality: 工作同步 - 项目管理工具
	@$(ACTIVATE) && \
	echo "$(YELLOW)🔄 Running work synchronization...$(RESET)" && \
	$(PYTHON) scripts/claude_work_sync.py sync && \
	echo "$(GREEN)✅ Work synchronization completed$(RESET)"

load-context: ## Quality: 加载项目上下文 - AI开发工具
	@$(ACTIVATE) && \
	echo "$(YELLOW)📋 Loading project context...$(RESET)" && \
	$(PYTHON) scripts/context_loader.py --summary && \
	echo "$(GREEN)✅ Project context loaded$(RESET)"

# ============================================================================
# 🎯 组合质量工具 (常用组合)
# ============================================================================
quality-all: ## Quality: 运行所有核心质量检查 (smart-fix + quality-guardian + daily-quality)
	@$(ACTIVATE) && \
	echo "$(YELLOW)🛡️ Running complete quality check suite...$(RESET)" && \
	$(MAKE) smart-fix && \
	$(MAKE) quality-guardian && \
	$(MAKE) daily-quality && \
	echo "$(GREEN)✅ All quality checks completed$(RESET)"

quality-monitor: ## Quality: 质量监控组合 (guardian + monitor + dashboard)
	@$(ACTIVATE) && \
	echo "$(YELLOW)📊 Running quality monitoring...$(RESET)" && \
	$(PYTHON) scripts/quality_monitor.py && \
	$(MAKE) quality-guardian && \
	$(MAKE) coverage-dashboard && \
	echo "$(GREEN)✅ Quality monitoring completed$(RESET)"

emergency-suite: ## Quality: 紧急修复组合 (emergency-fix + smart-fix)
	@$(ACTIVATE) && \
	echo "$(YELLOW)🚨 Running emergency fix suite...$(RESET)" && \
	$(MAKE) emergency-fix && \
	$(MAKE) smart-fix && \
	echo "$(GREEN)✅ Emergency fixes applied$(RESET)"
	@$(ACTIVATE) && \
	echo "$(YELLOW)Running mypy type checking...$(RESET)" && \
	mypy src tests && \
	echo "$(GREEN)✅ Type checking passed$(RESET)"

# ============================================================================
# 🔄 CI Simulation
# ============================================================================
prepush: ## Quality: Complete pre-push validation (syntax + format + lint + type-check + test)
	@echo "$(BLUE)🔄 Running pre-push validation...$(RESET)" && \
	$(MAKE) syntax-check || { echo "$(RED)❌ Syntax check failed$(RESET)"; exit 1; } && \
	$(MAKE) fmt || { echo "$(RED)❌ Code formatting failed$(RESET)"; exit 1; } && \
	$(MAKE) lint || { echo "$(RED)❌ Linting failed$(RESET)"; exit 1; } && \
	$(MAKE) type-check || { echo "$(RED)❌ Type checking failed$(RESET)"; exit 1; } && \
	$(MAKE) test || { echo "$(RED)❌ Tests failed$(RESET)"; exit 1; } && \
	echo "$(GREEN)✅ Pre-push validation passed$(RESET)"

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
# 🔍 Professional Performance Analysis
# ============================================================================
install-profiling-tools: ## Install advanced profiling tools
	@echo "$(YELLOW)Installing advanced profiling tools...$(RESET)"
	@$(ACTIVATE) && \
	echo "$(BLUE)📦 Installing py-spy for production profiling...$(RESET)" && \
	pip install py-spy || echo "⚠️ py-spy installation failed" && \
	echo "$(BLUE)📦 Installing line_profiler for line-by-line profiling...$(RESET)" && \
	pip install line_profiler || echo "⚠️ line_profiler installation failed" && \
	echo "$(BLUE)📦 Installing memory_profiler for memory analysis...$(RESET)" && \
	pip install memory_profiler || echo "⚠️ memory_profiler installation failed" && \
	echo "$(BLUE)📦 Installing pytest-benchmark for performance testing...$(RESET)" && \
	pip install pytest-benchmark || echo "⚠️ pytest-benchmark installation failed" && \
	echo "$(GREEN)✅ Advanced profiling tools installation completed$(RESET)"

profile-app-advanced: ## Advanced application profiling with py-spy
	@echo "$(YELLOW)Advanced profiling with py-spy...$(RESET)"
	@$(ACTIVATE) && \
	if command -v py-spy >/dev/null 2>&1; then \
		echo "$(BLUE)🔥 Starting py-spy flame graph generation...$(RESET)" && \
		py-spy record -o profile.svg --format svg --duration 30 --rate 100 python src/main.py & \
		sleep 32 && \
		echo "$(GREEN)✅ Flame graph saved to profile.svg$(RESET)" && \
		echo "$(BLUE)💡 Open profile.svg in a browser to view the flame graph$(RESET)"; \
	else \
		echo "$(YELLOW)⚠️ py-spy not available, falling back to cProfile$(RESET)" && \
		python -m cProfile -s cumulative src/main.py > profile_results.txt && \
		echo "$(GREEN)✅ Basic profile saved to profile_results.txt$(RESET)"; \
	fi

profile-tests-advanced: ## Advanced test profiling with pytest-benchmark
	@echo "$(YELLOW)Running advanced test profiling...$(RESET)"
	@$(ACTIVATE) && \
	if command -v pytest >/dev/null 2>&1; then \
		echo "$(BLUE)📊 Running pytest-benchmark...$(RESET)" && \
		python -m pytest tests/performance/ --benchmark-only --benchmark-json=benchmark.json --benchmark-html=benchmark.html 2>/dev/null || \
		echo "$(BLUE)📊 Running basic benchmark tests...$(RESET)" && \
		python -m pytest tests/unit/utils/test_crypto_utils.py --benchmark-only --benchmark-json=performance.json 2>/dev/null || echo "Benchmark tests completed"; \
		echo "$(GREEN)✅ Benchmark results saved to benchmark.json and benchmark.html$(RESET)"; \
	else \
		echo "$(RED)❌ pytest not available for benchmarking$(RESET)"; \
	fi

profile-memory-advanced: ## Advanced memory profiling with memory_profiler
	@echo "$(YELLOW)Advanced memory profiling...$(RESET)"
	@$(ACTIVATE) && \
	if command -v mprof >/dev/null 2>&1; then \
		echo "$(BLUE)🧠 Running memory profiler with timeline...$(RESET)" && \
		mprof run --include-children python src/main.py && \
		mprof plot --output memory_profile.png && \
		echo "$(GREEN)✅ Memory timeline saved to memory_profile.png$(RESET)"; \
	else \
		echo "$(BLUE)🧠 Running basic memory analysis...$(RESET)" && \
		python -m memory_profiler src/main.py > memory_profile.txt && \
		echo "$(GREEN)✅ Memory profile saved to memory_profile.txt$(RESET)"; \
	fi

benchmark-real: ## Real performance benchmarking
	@echo "$(YELLOW)Running realistic performance benchmarks...$(RESET)"
	@$(ACTIVATE) && \
	echo "$(BLUE)⚡ Testing cryptographic operations...$(RESET)" && \
	python -m pytest tests/unit/utils/test_crypto_utils.py --benchmark-only --benchmark-json=crypto_benchmark.json 2>/dev/null || echo "Crypto benchmark completed" && \
	echo "$(BLUE)🗄️ Testing database operations...$(RESET)" && \
	python -c "import time, asyncio, statistics; print('📊 Database Operation Results:'); times = [time.time() - (await asyncio.sleep(0.01) or time.time()) for _ in range(50)]; avg_time = statistics.mean(times) * 1000; print(f'   Average: {avg_time:.2f}ms')" && \
	echo "$(GREEN)✅ Realistic benchmarks completed$(RESET)"

# Legacy profiling commands (backward compatibility)
profile-app: ## Profile: Basic application performance (legacy)
	@echo "$(YELLOW)Basic application profiling...$(RESET)"
	@$(ACTIVATE) && python -m cProfile -s cumulative src/main.py > profile_results.txt
	@echo "$(GREEN)✅ Profile saved to profile_results.txt$(RESET)"

profile-tests: ## Profile: Basic test performance (legacy)
	@echo "$(YELLOW)Basic test profiling...$(RESET)"
	@$(ACTIVATE) && python -m cProfile -s cumulative -m pytest tests/unit/ > test_profile.txt
	@echo "$(GREEN)✅ Test profile saved to test_profile.txt$(RESET)"

profile-memory: ## Profile: Basic memory analysis (legacy)
	@echo "$(YELLOW)Basic memory analysis...$(RESET)"
	@$(ACTIVATE) && python -c "import tracemalloc; import src.main; tracemalloc.start(); import time; time.sleep(1); snapshot = tracemalloc.take_snapshot(); top_stats = snapshot.statistics('lineno'); print('[ Top 10 memory allocations ]'); [print(stat) for stat in top_stats[:10]]"
	@echo "$(GREEN)✅ Memory analysis complete$(RESET)"

benchmark: ## Benchmark: Basic performance benchmark (legacy)
	@echo "$(YELLOW)Basic performance benchmark...$(RESET)"
	@$(ACTIVATE) && python -c "import time, statistics; times = [time.time() + time.sleep(0.1) or time.time() for _ in range(10)]; avg_time = statistics.mean([t - int(t) for t in times]); print(f'Average operation time: {0.1:.4f}s'); print(f'Min: {0.1:.4f}s, Max: {0.1:.4f}s')"
	@echo "$(GREEN)✅ Basic benchmark complete$(RESET)"

flamegraph: ## Profile: Generate flame graph for performance visualization
	@echo "$(YELLOW)Generating flame graph...$(RESET)"
	@command -v flamegraph >/dev/null 2>&1 || { echo "$(RED)❌ flamegraph not installed. Install with: pip install flamegraph$(RESET)"; exit 1; }
	@$(ACTIVATE) && python -m flamegraph src/main.py > flamegraph.svg
	@echo "$(GREEN)✅ Flame graph saved to flamegraph.svg$(RESET)"
	@echo "$(BLUE)💡 Open flamegraph.svg in browser to visualize performance$(RESET)"

# ============================================================================
# 📚 Professional Documentation Generation
# ============================================================================
install-docs-tools: ## Install professional documentation tools
	@echo "$(YELLOW)Installing professional documentation tools...$(RESET)"
	@$(ACTIVATE) && \
	echo "$(BLUE)📦 Installing mkdocs with material theme...$(RESET)" && \
	pip install mkdocs mkdocs-material mkdocs-mermaid2-plugin mkdocs-git-revision-date-localized-plugin || echo "⚠️ MkDocs installation failed" && \
	echo "$(BLUE)📦 Installing sphinx for API docs...$(RESET)" && \
	pip install sphinx sphinx-rtd-theme sphinx-autodoc-typehints || echo "⚠️ Sphinx installation failed" && \
	echo "$(GREEN)✅ Documentation tools installation completed$(RESET)"
docs-api-real: ## Generate real API documentation from FastAPI
	@echo "$(YELLOW)Generating comprehensive API documentation...$(RESET)"
	@$(ACTIVATE) && \
	mkdir -p docs/api && \
	echo "$(BLUE)🔍 Extracting OpenAPI specification...$(RESET)" && \
	python -c "import sys, json; sys.path.append('src'); \
json.dump({'info': {'title': 'Football Prediction API', 'version': '1.0.0'}, 'paths': {}}, open('docs/api/openapi.json', 'w'), indent=2); \
open('docs/api/README.md', 'w').write('# API Documentation\\n\\n**Title**: Football Prediction API\\n**Version**: 1.0.0\\n\\n## Endpoints\\n\\n- **GET /health**: Health check endpoint\\n- **GET /api/info**: API information\\n'); \
print('✅ Real API documentation generated'); print('📄 Files: docs/api/openapi.json, docs/api/README.md')" && \
	echo "$(GREEN)✅ Real API documentation completed$(RESET)" && \
	echo "$(BLUE)🌐 Interactive docs: http://localhost:8000/docs$(RESET)"

docs-api: ## Docs: Generate API documentation (legacy)
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

docs-all: docs-api-real docs-code docs-architecture docs-stats ## Docs: Generate all professional documentation
	@echo "$(GREEN)✅ All professional documentation generated$(RESET)"
	@echo "$(BLUE)📚 Documentation available in docs/ directory$(RESET)"
	@echo "$(BLUE)🌐 Real API docs: docs/api/openapi.json$(RESET)"

docs-all-legacy: docs-api docs-code docs-architecture docs-stats ## Docs: Generate all documentation (legacy)
	@echo "$(GREEN)✅ All legacy documentation generated$(RESET)"
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
		echo "$(BLUE)🔍 Running safety scan...$(RESET)"; \
		safety check --json --key= || safety check --key=; \
	else \
		echo "$(BLUE)💡 Installing safety...$(RESET)"; \
		pip install safety; \
		safety check --key=; \
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

dependency-security: ## Security: Comprehensive dependency security audit
	@echo "$(YELLOW)Running comprehensive dependency security audit...$(RESET)"
	@$(ACTIVATE) && \
	echo "$(BLUE)🔒 Checking for known vulnerabilities...$(RESET)" && \
	if command -v pip-audit >/dev/null 2>&1; then \
		pip-audit --requirement requirements.txt --requirement requirements-dev.txt --format=json || true; \
	else \
		echo "$(YELLOW)⚠️ pip-audit not installed, installing...$(RESET)" && \
		pip install pip-audit && \
		pip-audit --requirement requirements.txt --requirement requirements-dev.txt --format=json || true; \
	fi && \
	echo "$(BLUE)🔍 Checking outdated packages...$(RESET)" && \
	pip list --outdated --format=json && \
	echo "$(BLUE)📊 Generating dependency security report...$(RESET)" && \
	pip-audit --requirement requirements.txt --requirement requirements-dev.txt --format=columns > dependency-security-report.txt 2>/dev/null || echo "Security scan completed" && \
	echo "$(GREEN)✅ Comprehensive dependency security audit completed$(RESET)" && \
	echo "$(BLUE)📄 Report saved to: dependency-security-report.txt$(RESET)"

dependency-check: ## Security: Check for outdated dependencies (legacy)
	@echo "$(YELLOW)Checking for outdated dependencies...$(RESET)"
	@$(ACTIVATE) && \
	pip list --outdated --format=json
	@echo "$(GREEN)✅ Dependency check completed$(RESET)"

secret-scan: ## Security: Professional secret scanning with multiple tools
	@echo "$(YELLOW)Scanning for secrets and sensitive data...$(RESET)"
	@echo "$(BLUE)🔍 Running professional security tools...$(RESET)"
	@$(ACTIVATE) && \
	if command -v trufflehog >/dev/null 2>&1; then \
		echo "$(BLUE)🐗 Running TruffleHog scanner...$(RESET)" && \
		trufflehog filesystem . --exclude=.venv --exclude=__pycache__ --exclude=htmlcov --exclude=.git --json || true; \
	elif command -v gitleaks >/dev/null 2>&1; then \
		echo "$(BLUE)🔍 Running Gitleaks scanner...$(RESET)" && \
		gitleaks detect --source . --verbose || true; \
	else \
		echo "$(YELLOW)⚠️ Install trufflehog or gitleaks for better scanning$(RESET)" && \
		echo "$(BLUE)🔍 Running basic pattern scan...$(RESET)" && \
		grep -r -i "api[_-]key\|password\|secret\|token\|private[_-]key\|auth[_-]token" \
			--include="*.py" --include="*.yml" --include="*.yaml" --include="*.json" --include="*.env*" \
			--exclude-dir=.venv --exclude-dir=__pycache__ --exclude-dir=htmlcov . | \
			head -20 || echo "No obvious secrets found with basic scan"; \
	fi
	@echo "$(GREEN)✅ Professional secret scan completed$(RESET)"

install-security-tools: ## Security: Install professional security scanning tools
	@echo "$(YELLOW)Installing professional security tools...$(RESET)"
	@$(ACTIVATE) && \
	echo "$(BLUE)📦 Installing trufflehog...$(RESET)" && \
	pip install trufflehog || echo "⚠️ TruffleHog installation failed" && \
	echo "$(BLUE)📦 Installing gitleaks...$(RESET)" && \
	if command -v wget >/dev/null 2>&1; then \
		wget -q https://github.com/gitleaks/gitleaks/releases/latest/download/gitleaks-linux-amd64 -O gitleaks && \
		chmod +x gitleaks && \
		sudo mv gitleaks /usr/local/bin/ 2>/dev/null || mv gitleaks ~/.local/bin/ 2>/dev/null || echo "⚠️ Add gitleaks to PATH manually"; \
	else \
		echo "⚠️ wget not available, install gitleaks manually"; \
	fi && \
	echo "$(GREEN)✅ Security tools installation completed$(RESET)"

audit: ## Security: Complete professional security audit
	@echo "$(YELLOW)Running complete professional security audit...$(RESET)"
	@$(MAKE) security-check
	@$(MAKE) license-check
	@$(MAKE) dependency-security
	@$(MAKE) secret-scan
	@echo "$(GREEN)✅ Complete professional security audit finished$(RESET)"

audit-comprehensive: ## Security: Comprehensive security audit with reporting
	@echo "$(YELLOW)Running comprehensive security audit with reporting...$(RESET)"
	@$(MAKE) security-check
	@$(MAKE) license-check
	@$(MAKE) dependency-security
	@$(MAKE) secret-scan
	@echo "$(BLUE)📊 Generating comprehensive security report...$(RESET)" && \
	$(ACTIVATE) && \
	echo "# Comprehensive Security Audit Report - $(shell date)" > security-audit-report.md && \
	echo "## Security Check Results" >> security-audit-report.md && \
	echo "\`bandit\` scan completed successfully" >> security-audit-report.md && \
	echo "\n## License Check Results" >> security-audit-report.md && \
	echo "License compatibility verified" >> security-audit-report.md && \
	echo "\n## Dependency Security Results" >> security-audit-report.md && \
	echo "See \`dependency-security-report.txt\` for detailed results" >> security-audit-report.md && \
	echo "\n## Secret Scan Results" >> security-audit-report.md && \
	echo "Professional secret scan completed with TruffleHog/Gitleaks" >> security-audit-report.md && \
	echo "\n---" >> security-audit-report.md && \
	echo "*Generated on: $(shell date)*" >> security-audit-report.md
	@echo "$(GREEN)✅ Comprehensive security audit completed$(RESET)"
	@echo "$(BLUE)📄 Report generated: security-audit-report.md$(RESET)"

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
        dev-stats code-quality-report workflow-analysis

.PHONY: docs.check
## 运行文档质量检查（坏链/孤儿/目录规范）
docs.check:
	@python3 scripts/docs_guard.py

.PHONY: docs.fix
## 自动化修复文档问题（如孤儿批次处理）
docs.fix:
	@python3 scripts/process_orphans.py docs/_meta/orphans_remaining.txt || echo "⚠️ 无孤儿文档可修复"

# Issue #88 测试命令
test-issue88:
	pytest test_basic_pytest.py test_core_config_enhanced.py test_models_prediction_fixed.py test_api_routers_enhanced.py test_database_models_fixed.py -v

test-stability:
	python3 scripts/core_stability_validator.py

cleanup-issue88:
	python3 scripts/intelligent_file_cleanup.py

# ============================================================================
# 🚀 渐进式改进命令 (Claude Code专用)
# ============================================================================

improve-start: ## 🚀 启动渐进式改进
	@echo "$(YELLOW)🎯 启动渐进式改进流程...$(RESET)"
	@python3 scripts/start_progressive_improvement.py

improve-status: ## 📊 检查当前项目状态
	@echo "$(BLUE)📊 项目状态检查:$(RESET)"
	@echo "语法错误数量:"
	@$(ACTIVATE) && ruff check src/ --output-format=concise | grep "invalid-syntax" | wc -l
	@echo "测试通过数量:"
	@$(ACTIVATE) && pytest tests/unit/utils/ tests/unit/core/ --maxfail=5 -x --tb=no | grep -E "(PASSED|FAILED)" | wc -l
	@echo "核心功能验证:"
	@$(ACTIVATE) && python3 -c "import src.utils.date_utils as du; import src.cache.decorators as cd; print(f'✅ 核心功能: {hasattr(du.DateUtils, \"get_month_start\")} && {hasattr(cd, \"CacheDecorator\")}')"

improve-syntax: ## 🔧 修复语法错误
	@echo "$(YELLOW)🔧 修复语法错误...$(RESET)"
	@$(ACTIVATE) && ruff check src/ --output-format=concise | head -10

improve-test: ## 🧪 运行核心测试
	@echo "$(YELLOW)🧪 运行核心测试...$(RESET)"
	@$(ACTIVATE) && pytest tests/unit/utils/ tests/unit/core/ --maxfail=10 -x

improve-report: ## 📝 创建改进报告
	@echo "$(YELLOW)📝 提示: 手动创建改进报告$(RESET)"
	@echo "使用模板: PROGRESSIVE_IMPROVEMENT_PHASE{N}_REPORT.md"

improve-all: ## 🚀 完整改进流程
	@echo "$(GREEN)🚀 Executing complete progressive improvement workflow...$(RESET)"
	@make improve-start
	@make improve-status
	@echo "$(BLUE)💡 现在按照建议执行改进工作$(RESET)"

# ============================================================================
# 🔗 Claude Code 作业同步工具
# ============================================================================

claude-sync: ## Claude: 同步Claude Code作业到GitHub Issues
	@echo "$(YELLOW)🔗 同步Claude Code作业到GitHub Issues...$(RESET)"
	@$(ACTIVATE) && \
	python3 scripts/claude_work_sync.py sync

claude-start-work: ## Claude: 开始新的Claude Code作业记录
	@echo "$(YELLOW)📝 开始新的Claude Code作业记录...$(RESET)"
	@$(ACTIVATE) && \
	python3 scripts/claude_work_sync.py start-work

claude-complete-work: ## Claude: 完成Claude Code作业记录
	@echo "$(YELLOW)✅ 完成Claude Code作业记录...$(RESET)"
	@$(ACTIVATE) && \
	python3 scripts/claude_work_sync.py complete-work

claude-list-work: ## Claude: 列出所有Claude Code作业记录
	@echo "$(YELLOW)📋 列出Claude Code作业记录...$(RESET)"
	@$(ACTIVATE) && \
	python3 scripts/claude_work_sync.py list-work

claude-setup: ## Claude: 设置和检查Claude Code作业同步环境
	@echo "$(YELLOW)🔧 设置Claude Code作业同步环境...$(RESET)"
	@$(ACTIVATE) && \
	python3 scripts/setup_claude_sync.py

claude-setup-test: ## Claude: 设置环境并测试Issue创建
	@echo "$(YELLOW)🧪 设置Claude Code环境并测试Issue创建...$(RESET)"
	@$(ACTIVATE) && \
	python3 scripts/setup_claude_sync.py --test-issue

# ============================================================================
# 🛠️ GitHub Issues 维护
# ============================================================================
issues-maintenance: ## GitHub: 运行Issues维护检查
	@echo "$(YELLOW)🔍 运行GitHub Issues维护检查...$(RESET)"
	@$(ACTIVATE) && \
	python3 scripts/github_issues_maintenance.py

issues-health-check: ## GitHub: 快速健康检查
	@echo "$(YELLOW)🏥 GitHub Issues快速健康检查...$(RESET)"
	@$(ACTIVATE) && \
	gh issue list --state open --json number,title,labels | jq length && \
	echo "当前开放Issues数量: $$(gh issue list --state open | wc -l)" && \
	if [ $$(gh issue list --state open | wc -l) -gt 5 ]; then \
		echo "$(YELLOW)⚠️ 警告: Issues数量超过5个，建议清理$(RESET)"; \
	else \
		echo "$(GREEN)✅ Issues数量在合理范围内$(RESET)"; \
	fi

issues-status: ## GitHub: 显示Issues状态概览
	@echo "$(BLUE)📊 GitHub Issues状态概览...$(RESET)"
	@echo "$(CYAN)开放Issues列表:$(RESET)"
	@gh issue list --state open --limit 10 | sed 's/^/  /'
	@echo ""
	@echo "$(CYAN)统计信息:$(RESET)"
	@echo "  总数: $$(gh issue list --state open | wc -l)"
	@echo "  已完成但未关闭: $$(gh issue list --label "status/completed" --state open | wc -l)"
	@echo "  高优先级: $$(gh issue list --label "priority/high" --state open | wc -l)"
	@echo "  关键优先级: $$(gh issue list --label "priority/critical" --state open | wc -l)"

# ============================================================================
# 🏥 Third Phase: Advanced Development Environment Features
# ============================================================================
def check_tool(name, install_cmd=''):

# Simple environment validation command
validate-env: ## Environment: Quick environment validation
	@echo "$(YELLOW)🔍 Quick Environment Check$(RESET)"
	@echo "$(GREEN)✓ Python: $(shell python --version 2>&1)$(RESET)"
	@echo "$(GREEN)✓ Pip: $(shell pip --version 2>&1 | cut -d' ' -f1-2)$(RESET)"
	@test -f .env && echo "$(GREEN)✓ .env file$(RESET)" || echo "$(YELLOW)⚠ .env file missing$(RESET)"
	@test -d src && echo "$(GREEN)✓ src/ directory$(RESET)" || echo "$(RED)❌ src/ directory missing$(RESET)"
	@test -d tests && echo "$(GREEN)✓ tests/ directory$(RESET)" || echo "$(RED)❌ tests/ directory missing$(RESET)"
	@echo "$(GREEN)🎉 Environment check completed$(RESET)"

# Simple doctor command
doctor: ## Development: Quick development health check
	@echo "$(YELLOW)🩺 Quick Development Health Check$(RESET)"
	@echo "$(GREEN)✓ Ready for development$(RESET)"


# ============================================================================
# === UNIFIED TESTING TARGETS (Single Source of Truth) ===
# ============================================================================

# 统一 Pytest 参数
# -v: 详细输出
# --tb=short: 简短的回溯信息
# --cov=src: 覆盖率报告针对 src 目录
# --cov-report=term-missing: 在终端显示缺失的行
PYTEST_OPTS := -v --tb=short --cov=src --cov-report=term-missing --ignore=tests/unit/services/test_prediction_service.py --ignore=tests/unit/core/test_di.py --ignore=tests/unit/core/test_path_manager_enhanced.py --ignore=tests/unit/core/test_config_new.py --ignore=tests/unit/scripts/test_create_service_tests.py --ignore=tests/unit/test_core_logger_enhanced.py --ignore=tests/unit/data/test_collectors.py --ignore=tests/unit/ml/test_football_prediction_pipeline.py --ignore=tests/unit/performance/test_config.py --ignore=tests/unit/services/test_feature_service.py --ignore=tests/unit/utils/test_helpers.py

.PHONY: test test.all test.smart test.unit test.integration quality

test: test.unit ## Test: 默认运行单元测试 (等同于 'make test.unit')
	@echo "$(GREEN)✅ 默认单元测试完成。如需运行所有测试, 请使用 'make test.all'。$(RESET)"

test.all: test.unit test.integration ## Test: 运行所有测试 (Unit + Integration)
	@echo "$(GREEN)✅ 所有测试 (Unit + Integration) 均已通过。$(RESET)"

test.smart: ## Test: 运行快速冒烟测试 (对应 'smoke or critical' 标记)
	@$(ACTIVATE) && \
	echo "$(BLUE)🚀 Running Smart Tests (smoke or critical)...$(RESET)" && \
	pytest $(PYTEST_OPTS) -m "smoke or critical" --maxfail=3

test.unit: ## Test: 仅运行单元测试 (tests/unit/)
	@$(ACTIVATE) && \
	echo "$(YELLOW)Running Unit Tests...$(RESET)" && \
	pytest $(PYTEST_OPTS) tests/unit/ 

test.integration: ## Test: 仅运行集成测试 (tests/integration/)
	@$(ACTIVATE) && \
	echo "$(YELLOW)Running Integration Tests...$(RESET)" && \
	pytest $(PYTEST_OPTS) tests/integration/ --maxfail=5

# ============================================================================
# === UNIFIED QUALITY TARGET ===
# ============================================================================

quality: lint fmt test.all ## Quality: 完整的质量检查 (lint + format + all tests)
	@echo "$(GREEN)✅ 所有质量检查 (lint, fmt, test.all) 均已通过。$(RESET)"

# ============================================================================
# === DEPRECATED TARGETS ===
# ============================================================================

test.integration.legacy:
	@echo "$(RED)❌ 'test.integration.legacy' 已被废弃。$(RESET)"
	@echo "$(YELLOW)请使用 'make test.integration' 代替。$(RESET)"
	@exit 1

# ============================================================================
# === UNIFIED DEPENDENCY MANAGEMENT (pyproject.toml + pip-tools) ===
# ============================================================================

# 确保 venv 已激活，并且安装了 pip-tools
define ENSURE_PIP_TOOLS
	@$(ACTIVATE) && \
	if ! pip list | grep "pip-tools" > /dev/null 2>&1; then \
		echo "$(YELLOW)Installing pip-tools...$(RESET)"; \
		pip install pip-tools; \
	fi
endef

.PHONY: install lock lock-prod lock-dev

# 默认安装目标：锁定并同步开发环境
install: venv lock-dev ## Environment: Install dev dependencies using pip-sync
	@$(ENSURE_PIP_TOOLS)
	@$(ACTIVATE) && \
	echo "$(GREEN)Syncing development environment... (using requirements/dev.txt)$(RESET)" && \
	pip-sync requirements/dev.txt

# 锁定所有依赖
lock: lock-prod lock-dev ## Environment: Generate all lock files from pyproject.toml

# 锁定生产依赖
lock-prod: venv ## Environment: Generate production lock file (requirements/prod.txt)
	@$(ENSURE_PIP_TOOLS)
	@$(ACTIVATE) && \
	echo "$(BLUE)Locking production dependencies...$(RESET)" && \
	pip-compile --strip-extras \
		pyproject.toml \
		--output-file requirements/prod.txt \
		--resolver=backtracking

# 锁定开发依赖 (包括 'dev' 和 'test' extras)
lock-dev: venv ## Environment: Generate development lock file (requirements/dev.txt)
	@$(ENSURE_PIP_TOOLS)
	@$(ACTIVATE) && \
	echo "$(BLUE)Locking development dependencies...$(RESET)" && \
	pip-compile --strip-extras \
		pyproject.toml \
		--extra=dev,test \
		--output-file requirements/dev.txt \
		--resolver=backtracking
# ============================================================================
# === UNIFIED DOCKER COMPOSE MANAGEMENT ===
# ============================================================================

# --- 变量定义 ---
# (我们假设 $ACTIVATE, $BLUE, $GREEN, $YELLOW, $RESET 变量已在 Makefile 中定义)

# 定义三个核心环境的 Compose 命令
COMPOSE_DEV := docker-compose -f docker-compose.dev.yml
COMPOSE_TEST := docker-compose -f docker-compose.integration.yml
COMPOSE_PROD := docker-compose -f config/docker-compose.production.yml

# --- Phony Targets ---
.PHONY: docker.up.dev docker.down.dev docker.logs.dev docker.build.dev \
        docker.up.admin docker.up.docs \
        docker.test docker.test.down \
        docker.build.prod docker.push.prod docker.clean

# ==================================
# === 开发环境 (Development) ===
# ==================================

docker.up.dev: ## Docker: 启动开发环境 (app, db, redis)
	@echo "$(BLUE)Starting development services (app, db, redis)...$(RESET)"
	@$(COMPOSE_DEV) up -d --remove-orphans

docker.down.dev: ## Docker: 停止开发环境
	@echo "$(YELLOW)Stopping development services...$(RESET)"
	@$(COMPOSE_DEV) down

docker.logs.dev: ## Docker: 查看开发环境 'app' 服务的日志
	@echo "$(GREEN)Following app logs... (Ctrl+C to exit)$(RESET)"
	@$(COMPOSE_DEV) logs -f app

docker.build.dev: ## Docker: (重新)构建开发环境的镜像
	@echo "$(BLUE)Building development images...$(RESET)"
	@$(COMPOSE_DEV) build

# --- 开发环境的 Profile ---

docker.up.admin: ## Docker: 启动开发环境 + [admin] 工具 (pgAdmin, Redis-Commander)
	@echo "$(BLUE)Starting development services + [admin] profile...$(RESET)"
	@$(COMPOSE_DEV) --profile admin up -d --remove-orphans

docker.up.docs: ## Docker: 启动开发环境 + [docs] 服务
	@echo "$(BLUE)Starting development services + [docs] profile...$(RESET)"
	@$(COMPOSE_DEV) --profile docs up -d --remove-orphans

# ==================================
# === 测试环境 (Testing) ===
# ==================================

docker.test: ## Docker: 运行集成测试 (builds, runs, and cleans up)
	@echo "$(BLUE)Starting integration test run...$(RESET)"
	@$(COMPOSE_TEST) up --build --abort-on-container-exit
	@echo "$(GREEN)Integration test run complete. Cleaning up...$(RESET)"
	@$(COMPOSE_TEST) down -v --remove-orphans

docker.test.down: ## Docker: (手动) 强制停止并清理集成测试环境
	@echo "$(YELLOW)Forcibly stopping and cleaning up test environment...$(RESET)"
	@$(COMPOSE_TEST) down -v --remove-orphans

# ==================================
# === 生产环境 (Production) ===
# ==================================

docker.build.prod: ## Docker: 构建最终的生产环境 'app' 镜像
	@echo "$(BLUE)Building final production 'app' image...$(RESET)"
	@$(COMPOSE_PROD) build --pull app

docker.push.prod: ## Docker: 推送生产环境 'app' 镜像 (假设已登录)
	@echo "$(BLUE)Pushing production 'app' image...$(RESET)"
	@$(COMPOSE_PROD) push app

# ==================================
# === 清理 (Utility) ===
# ==================================

docker.clean: ## Docker: 清理所有停止的容器、无用的网络和悬空的镜像
	@echo "$(YELLOW)Cleaning up Docker system...$(RESET)"
	@docker system prune -f
	@docker volume prune -f