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
venv: ## Environment: Create and activate virtual environment
	@if [ ! -d "$(VENV)" ]; then \
		echo "$(YELLOW)Creating virtual environment...$(RESET)"; \
		$(PYTHON) -m venv $(VENV); \
		echo "$(GREEN)✅ Virtual environment created$(RESET)"; \
	else \
		echo "$(BLUE)ℹ️  Virtual environment already exists$(RESET)"; \
	fi

install: venv ## Environment: Install dependencies from requirements.txt
	@$(ACTIVATE) && \
	if pip list | grep -F "$(shell head -n1 requirements.txt | cut -d'=' -f1)" > /dev/null 2>&1; then \
		echo "$(BLUE)ℹ️  Dependencies appear to be installed$(RESET)"; \
	else \
		echo "$(YELLOW)Installing dependencies...$(RESET)"; \
		pip install --upgrade pip && \
		pip install -r requirements.txt && \
		pip install -r requirements-dev.txt; \
		echo "$(GREEN)✅ Dependencies installed$(RESET)"; \
	fi

# ============================================================================
# 🎨 Code Quality
# ============================================================================
lint: ## Quality: Run flake8 and mypy checks
	@$(ACTIVATE) && \
	echo "$(YELLOW)Running flake8...$(RESET)" && \
	flake8 src/ tests/ && \
	echo "$(YELLOW)Running mypy...$(RESET)" && \
	mypy --config-file mypy.ini src/ && \
	echo "$(GREEN)✅ Linting passed$(RESET)"

fmt: ## Quality: Format code with black and isort
	@$(ACTIVATE) && \
	echo "$(YELLOW)Running black...$(RESET)" && \
	black src/ tests/ && \
	echo "$(YELLOW)Running isort...$(RESET)" && \
	isort src/ tests/ && \
	echo "$(GREEN)✅ Code formatted$(RESET)"

check: lint fmt test ## Quality: Complete quality check (lint + format + test)
	@echo "$(GREEN)✅ All quality checks passed$(RESET)"

# ============================================================================
# 🧪 Testing
# ============================================================================
test: ## Test: Run pytest unit tests
	@$(ACTIVATE) && \
	echo "$(YELLOW)Running tests...$(RESET)" && \
	pytest tests/ -v && \
	echo "$(GREEN)✅ Tests passed$(RESET)"

coverage: ## Test: Run tests with coverage report (threshold: 80%)
	@$(ACTIVATE) && \
	echo "$(YELLOW)Running coverage tests...$(RESET)" && \
	pytest tests/ --cov=src --cov-report=term-missing --cov-fail-under=$(COVERAGE_THRESHOLD) && \
	echo "$(GREEN)✅ Coverage passed (>=$(COVERAGE_THRESHOLD)%)$(RESET)"

type-check: ## Quality: Run type checking with mypy
	@$(ACTIVATE) && \
	echo "$(YELLOW)Running mypy type checking...$(RESET)" && \
	mypy src tests && \
	echo "$(GREEN)✅ Type checking passed$(RESET)"

# ============================================================================
# 🔄 CI Simulation
# ============================================================================
ci: ## CI: Simulate GitHub Actions CI pipeline
	@echo "$(BLUE)🔄 Running CI simulation...$(RESET)" && \
	$(MAKE) lint && \
	$(MAKE) type-check && \
	$(MAKE) test && \
	$(MAKE) coverage && \
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
	$(PYTHON) -m pytest tests/test_feedback_loop.py -v --cov=scripts --cov=reports --cov=monitoring --cov-report=term-missing && \
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

# ============================================================================
# 📝 Phony Targets
# ============================================================================
.PHONY: help venv install lint fmt check test coverage type-check ci up down logs sync-issues context clean \
        feedback-update feedback-report performance-report retrain-check retrain-dry model-monitor \
        feedback-test mlops-pipeline mlops-status
