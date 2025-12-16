# 🚀 FootballPrediction 精简工作流 Makefile
# 核心MLOps工作流 - 保留27个核心targets

PYTHON := python3
VENV := venv
ACTIVATE := . $(VENV)/bin/activate
PROJECT_NAME := FootballPrediction

# 颜色定义
RED := \033[31m
GREEN := \033[32m
YELLOW := \033[33m
BLUE := \033[34m
RESET := \033[0m

# ==================================================
# 核心开发原则：简洁、高效、可维护
# ==================================================

# -------------------------------
# 📋 帮助信息
# -------------------------------
.PHONY: help
help: ## 显示帮助信息
	@echo "$(BLUE)🚀 $(PROJECT_NAME) 核心工作流$(RESET)"
	@echo ""
	@echo "$(YELLOW)环境管理:$(RESET)"
	@echo "  venv        创建虚拟环境"
	@echo "  install     安装项目依赖"
	@echo "  dev         开发环境快速准备"
	@echo "  clean       清理环境和缓存"
	@echo ""
	@echo "$(YELLOW)代码质量:$(RESET)"
	@echo "  format      代码格式化"
	@echo "  lint        代码风格检查"
	@echo "  typecheck   类型检查 (别名: type-check)"
	@echo "  security    安全检查"
	@echo "  quality     完整质量检查"
	@echo ""
	@echo "$(YELLOW)测试:$(RESET)"
	@echo "  test        运行单元测试 (630个测试)"
	@echo "  coverage    运行覆盖率测试 (96.35%)"
	@echo ""
	@echo "$(YELLOW)核心工作流:$(RESET)"
	@echo "  env-check   环境检查"
	@echo "  ci          完整CI流程检查"
	@echo "  prepush     提交前完整检查"
	@echo ""
	@echo "$(YELLOW)项目管理:$(RESET)"
	@echo "  status      查看项目状态"
	@echo "  ci-status   查看CI运行状态"
	@echo "  ci-monitor  实时监控CI执行"

# -------------------------------
# 🌐 环境管理
# -------------------------------
$(VENV)/bin/activate:
	@echo "$(BLUE)>>> 创建虚拟环境...$(RESET)"
	$(PYTHON) -m venv $(VENV)
	@echo "$(GREEN)✅ 虚拟环境创建完成$(RESET)"

.PHONY: venv
venv: $(VENV)/bin/activate ## 创建虚拟环境
	@echo "$(GREEN)>>> 虚拟环境已准备就绪$(RESET)"

.PHONY: install
install: venv ## 安装项目依赖
	@echo "$(BLUE)>>> 安装依赖包...$(RESET)"
	$(ACTIVATE) && pip install -U pip setuptools wheel
	$(ACTIVATE) && pip install -r requirements.txt -r requirements-dev.txt
	@echo "$(GREEN)✅ 依赖安装完成$(RESET)"

.PHONY: lock
lock: venv ## 生成依赖锁定文件
	@echo "$(BLUE)>>> 生成依赖锁定文件...$(RESET)"
	$(ACTIVATE) && pip-compile requirements.txt --output-file requirements.lock --strip-extras --upgrade
	@echo "$(GREEN)✅ 依赖锁定文件已生成$(RESET)"

# -------------------------------
# 🔍 环境检查
# -------------------------------
.PHONY: env-check
env-check: venv ## 环境检查
	@echo "$(BLUE)>>> 运行环境检查...$(RESET)"
	@if $(ACTIVATE) && python scripts/env_checker.py --summary --fix-suggestions; then \
		echo "$(GREEN)✅ 环境检查通过$(RESET)"; \
	else \
		echo "$(RED)❌ 环境检查失败$(RESET)"; \
		echo "$(YELLOW)   请根据上述建议修复环境问题$(RESET)"; \
		exit 1; \
	fi

# -------------------------------
# 🔧 代码质量
# -------------------------------
.PHONY: format
format: venv ## 代码格式化
	@echo "$(BLUE)>>> 代码格式化...$(RESET)"
	$(ACTIVATE) && python -m black src/core/ src/utils/ src/database/ src/api/ tests/ scripts/ || echo "跳过不存在的目录"
	@if [ -d "src/models" ]; then \
		$(ACTIVATE) && python -m black src/models/; \
	fi
	@if [ -d "src/services" ]; then \
		$(ACTIVATE) && python -m black src/services/; \
	fi
	@echo "$(GREEN)✅ 代码格式化完成$(RESET)"

.PHONY: lint
lint: venv ## 代码风格检查
	@echo "$(BLUE)>>> 代码风格检查...$(RESET)"
	$(ACTIVATE) && python -m flake8 src/core/ src/utils/ src/database/ src/api/ tests/ --max-line-length=120 --ignore=E402,F541,F401,W503,F841,E501,E721,E712,F821,F601,E265,E722,F811
	@echo "$(GREEN)✅ 代码风格检查通过$(RESET)"

.PHONY: typecheck type-check
typecheck: venv ## 类型检查
	@echo "$(BLUE)>>> 类型检查...$(RESET)"
	@if $(ACTIVATE) && python -c "import mypy" 2>/dev/null; then \
		$(ACTIVATE) && python -m mypy src/core/ src/models/ src/services/ src/utils/ src/database/ src/api/ --ignore-missing-imports --explicit-package-bases --check-untyped-defs; \
		echo "$(GREEN)✅ 类型检查完成$(RESET)"; \
	else \
		echo "$(YELLOW)⚠️ mypy未安装，跳过类型检查$(RESET)"; \
	fi

type-check: typecheck

.PHONY: security
security: venv ## 安全检查
	@echo "$(BLUE)>>> 安全漏洞扫描...$(RESET)"
	@if $(ACTIVATE) && python -c "import bandit" 2>/dev/null; then \
		$(ACTIVATE) && python -m bandit -r src/ --severity-level medium; \
		echo "$(GREEN)✅ 代码安全检查完成$(RESET)"; \
	else \
		echo "$(YELLOW)⚠️ bandit未安装，跳过安全检查$(RESET)"; \
	fi
	@echo "$(BLUE)>>> 依赖安全检查...$(RESET)"
	@if $(ACTIVATE) && python -c "import safety" 2>/dev/null; then \
		$(ACTIVATE) && safety check; \
		echo "$(GREEN)✅ 依赖安全检查完成$(RESET)"; \
	else \
		echo "$(YELLOW)⚠️ safety未安装，跳过依赖安全检查$(RESET)"; \
	fi

.PHONY: complexity
complexity: venv ## 复杂度分析
	@echo "$(BLUE)>>> 代码复杂度分析...$(RESET)"
	@if $(ACTIVATE) && python -c "import radon" 2>/dev/null; then \
		$(ACTIVATE) && python -m radon cc src/ -s --total-average; \
		echo "$(GREEN)✅ 复杂度分析完成$(RESET)"; \
	else \
		echo "$(YELLOW)⚠️ radon未安装，跳过复杂度检查$(RESET)"; \
	fi

.PHONY: deadcode
deadcode: venv ## 死代码检测
	@echo "$(BLUE)>>> 死代码检测...$(RESET)"
	@if $(ACTIVATE) && python -c "import vulture" 2>/dev/null; then \
		$(ACTIVATE) && vulture src/ --min-confidence 70 --sort-by-size; \
		echo "$(GREEN)✅ 死代码检测完成$(RESET)"; \
	else \
		echo "$(YELLOW)⚠️ vulture未安装，跳过死代码检测$(RESET)"; \
	fi

# -------------------------------
# 🧪 测试
# -------------------------------
.PHONY: test
test: venv ## 运行单元测试 (630个测试)
	@echo "$(BLUE)>>> 运行单元测试...$(RESET)"
	@if [ -d "tests" ] && [ -n "$$(find tests -name '*.py' -type f)" ]; then \
		if $(ACTIVATE) && python -m pytest tests/ -v --tb=short; then \
			echo "$(GREEN)✅ 单元测试通过$(RESET)"; \
		else \
			echo "$(RED)❌ 单元测试失败$(RESET)"; \
			echo "$(YELLOW)   请修复失败的测试后重试$(RESET)"; \
			exit 1; \
		fi; \
	else \
		echo "$(YELLOW)⚠️ 未找到测试文件，跳过测试$(RESET)"; \
	fi

.PHONY: coverage
coverage: venv ## 运行覆盖率测试 (96.35%)
	@echo "$(BLUE)>>> 运行覆盖率测试...$(RESET)"
	@if [ -d "tests" ] && [ -n "$$(find tests -name '*.py' -type f)" ]; then \
		if $(ACTIVATE) && python -c "import pytest_cov" 2>/dev/null; then \
			if $(ACTIVATE) && python -m pytest --cov=src --cov-fail-under=80 --cov-report=term-missing --cov-report=xml --cov-report=html tests/; then \
				echo "$(GREEN)✅ 覆盖率测试通过$(RESET)"; \
			else \
				echo "$(RED)❌ 覆盖率测试失败$(RESET)"; \
				echo "$(YELLOW)   请修复测试问题或提高覆盖率到 >=80%$(RESET)"; \
				exit 1; \
			fi; \
		else \
			echo "$(YELLOW)⚠️ pytest-cov未安装，运行普通测试$(RESET)"; \
			if $(ACTIVATE) && python -m pytest tests/ -v; then \
				echo "$(GREEN)✅ 测试通过$(RESET)"; \
			else \
				echo "$(RED)❌ 测试失败$(RESET)"; \
				exit 1; \
			fi; \
		fi; \
	else \
		echo "$(YELLOW)⚠️ 未找到测试文件，跳过测试$(RESET)"; \
	fi

# -------------------------------
# ✅ 完整质量检查
# -------------------------------
.PHONY: quality
quality: venv format lint typecheck security complexity ## 完整质量检查
	@echo "$(BLUE)>>> 运行质量检查器...$(RESET)"
	@if $(ACTIVATE) && python scripts/quality_checker.py --summary; then \
		echo "$(GREEN)✅ 完整质量检查通过$(RESET)"; \
	else \
		echo "$(RED)❌ 质量检查失败$(RESET)"; \
		echo "$(YELLOW)   请修复上述质量问题后重试$(RESET)"; \
		exit 1; \
	fi

# -------------------------------
# 🚀 CI 流程
# -------------------------------
.PHONY: ci
ci: env-check quality test coverage ## 完整CI流程
	@echo "$(GREEN)>>> 完整CI检查全部通过 ✅$(RESET)"
	@echo "$(GREEN)>>> 代码质量验证完成，可以安全推送$(RESET)"

# -------------------------------
# 📊 项目状态和监控
# -------------------------------
.PHONY: status
status: venv ## 查看项目状态
	@echo "$(BLUE)>>> 项目状态总览$(RESET)"
	@echo ""
	@echo "$(YELLOW)📁 项目信息:$(RESET)"
	@echo "  项目名称: $(PROJECT_NAME)"
	@echo "  Python版本: $$($(ACTIVATE) && python --version)"
	@echo "  虚拟环境: $(VENV)"
	@echo ""
	@echo "$(YELLOW)📊 代码统计:$(RESET)"
	@echo "  Python文件: $$(find . -name "*.py" -not -path "./$(VENV)/*" | wc -l)"
	@echo "  代码行数: $$(find . -name "*.py" -not -path "./$(VENV)/*" -exec wc -l {} + | tail -1 | awk '{print $$1}')"
	@echo ""
	@echo "$(YELLOW)🌿 Git状态:$(RESET)"
	@if [ -d ".git" ]; then \
		echo "  当前分支: $$(git branch --show-current)"; \
		echo "  最近提交: $$(git log -1 --pretty=format:'%h %s')"; \
		uncommitted=$$(git status --porcelain | wc -l); \
		echo "  未提交文件: $$uncommitted"; \
	else \
		echo "  $(RED)未初始化Git仓库$(RESET)"; \
	fi
	@echo ""
	@echo "$(YELLOW)📦 依赖状态:$(RESET)"
	@if [ -f "requirements.txt" ]; then \
		echo "  依赖文件: requirements.txt"; \
		echo "  依赖数量: $$(cat requirements.txt | grep -v '^#' | grep -v '^$$' | wc -l)"; \
	else \
		echo "  $(RED)未找到requirements.txt$(RESET)"; \
	fi

# -------------------------------
# 🔍 CI监控工具
# -------------------------------
.PHONY: ci-status ci-monitor ci-analyze
ci-status: venv ## 查看最新CI运行状态
	@echo "$(BLUE)>>> GitHub Actions CI状态监控$(RESET)"
	@$(ACTIVATE) && python scripts/ci_monitor.py

ci-monitor: venv ## 实时监控CI执行过程
	@echo "$(BLUE)>>> 启动CI实时监控$(RESET)"
	@echo "$(YELLOW)💡 按 Ctrl+C 停止监控$(RESET)"
	@$(ACTIVATE) && python scripts/ci_monitor.py --monitor

ci-analyze: venv ## 深度分析指定的CI运行（需要RUN_ID参数）
	@echo "$(BLUE)>>> CI失败原因深度分析$(RESET)"
	@if [ -z "$(RUN_ID)" ]; then \
		echo "$(YELLOW)⚠️  请提供CI运行ID: make ci-analyze RUN_ID=123456$(RESET)"; \
		echo "$(YELLOW)💡 或运行 make ci-status 查看可用的运行ID$(RESET)"; \
	else \
		$(ACTIVATE) && python scripts/ci_monitor.py --analyze $(RUN_ID); \
	fi

# -------------------------------
# 🎯 提交和推送
# -------------------------------
.PHONY: prepush
prepush: ## 提交前完整检查、推送（带失败保护）
	@echo "$(BLUE)>>> 开始prepush流程（包含失败保护机制）...$(RESET)"
	@echo "$(YELLOW)>>> 第1步: 执行CI检查...$(RESET)"
	@if $(MAKE) ci; then \
		echo "$(GREEN)✅ CI检查通过，继续推送流程$(RESET)"; \
		echo "$(YELLOW)>>> 第2步: 检查Git状态...$(RESET)"; \
		if [ -z "$$(git status --porcelain)" ]; then \
			echo "$(YELLOW)⚠️ 工作区干净，无需提交$(RESET)"; \
		else \
			echo "$(BLUE)>>> 添加文件到暂存区...$(RESET)"; \
			git add .; \
			echo "$(BLUE)>>> 创建提交...$(RESET)"; \
			git commit -m "chore: prepush auto commit - $$(date '+%Y-%m-%d %H:%M:%S')"; \
			echo "$(BLUE)>>> 推送到远程仓库...$(RESET)"; \
			git push origin HEAD; \
			echo "$(GREEN)✅ 代码推送完成$(RESET)"; \
		fi; \
		echo "$(GREEN)🎉 prepush完整流程成功完成！$(RESET)"; \
	else \
		echo "$(RED)❌ CI检查失败，停止推送流程$(RESET)"; \
		echo "$(RED)   请修复上述问题后重新运行 make prepush$(RESET)"; \
		echo "$(YELLOW)💡 快速修复建议:$(RESET)"; \
		echo "$(YELLOW)   - 代码格式问题: make format$(RESET)"; \
		echo "$(YELLOW)   - 测试失败: make test$(RESET)"; \
		echo "$(YELLOW)   - 环境问题: make env-check$(RESET)"; \
		exit 1; \
	fi

# -------------------------------
# 🧹 清理
# -------------------------------
.PHONY: clean
clean: ## 清理环境和缓存
	@echo "$(BLUE)>>> 清理环境...$(RESET)"
	rm -rf $(VENV)
	rm -rf .pytest_cache
	rm -rf .mypy_cache
	rm -rf .coverage
	rm -rf htmlcov
	rm -rf dist
	rm -rf build
	rm -rf *.egg-info
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true
	@echo "$(GREEN)✅ 清理完成$(RESET)"

# -------------------------------
# 🎯 快捷方式
# -------------------------------
.PHONY: dev
dev: install env-check ## 开发环境快速准备
	@echo "$(GREEN)✅ 开发环境已准备就绪$(RESET)"
	@echo "$(BLUE)>>> 可以开始编码了！建议运行: make status$(RESET)"

# 默认目标
.DEFAULT_GOAL := help