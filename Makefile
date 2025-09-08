# 🚀 AICultureKit 项目通用 Makefile
# 使用方法：make <target>
# 推荐目标：make prepush

PYTHON := python3
VENV := venv
ACTIVATE := . $(VENV)/bin/activate
PROJECT_NAME := AICultureKit

# 颜色定义
RED := \033[31m
GREEN := \033[32m
YELLOW := \033[33m
BLUE := \033[34m
RESET := \033[0m

# ==================================================
# 本项目开发全局原则
# 1. 所有代码必须带中文注释，注释解释设计意图与逻辑
# 2. 生成的文件必须遵循既定目录结构，不得乱建目录
# 3. 所有模块必须配套测试，测试放在 tests/ 目录下
# 4. 所有命令都通过 Makefile 统一执行
# ==================================================

# -------------------------------
# 📋 帮助信息
# -------------------------------
.PHONY: help
help: ## 显示帮助信息
	@echo "$(BLUE)🚀 $(PROJECT_NAME) 开发工具$(RESET)"
	@echo ""
	@echo "$(YELLOW)环境管理:$(RESET)"
	@echo "  venv        创建虚拟环境"
	@echo "  install     安装项目依赖"
	@echo "  clean       清理环境和缓存"
	@echo ""
	@echo "$(YELLOW)代码质量:$(RESET)"
	@echo "  format      代码格式化"
	@echo "  lint        代码风格检查"
	@echo "  typecheck   类型检查"
	@echo "  security    安全检查"
	@echo ""
	@echo "$(YELLOW)测试:$(RESET)"
	@echo "  test        运行单元测试"
	@echo "  coverage    运行覆盖率测试"
	@echo "  test-watch  监控模式运行测试"
	@echo ""
	@echo "$(YELLOW)闭环流程:$(RESET)"
	@echo "  env-check   环境检查"
	@echo "  quality     完整质量检查"
	@echo "  ci          本地CI模拟"
	@echo "  ci-local    本地执行与远程完全相同的CI流程"
	@echo "  prepush     提交前完整检查+Issue同步"
	@echo ""
	@echo "$(YELLOW)项目管理:$(RESET)"
	@echo "  init        初始化项目"
	@echo "  context     加载项目上下文"
	@echo "  status      查看项目状态"
	@echo "  ci-status   查看GitHub Actions CI状态"
	@echo "  ci-monitor  实时监控CI执行过程"
	@echo "  ci-analyze  深度分析CI失败原因"
	@echo "  sync        同步Issues到远程仓库"
	@echo "  sync-config 配置Issue同步"
	@echo ""
	@echo "$(YELLOW)CI Guardian 防御系统:$(RESET)"
	@echo "  ci-guardian         运行完整CI守护检查"
	@echo "  validate-defenses   验证所有防御机制"
	@echo "  run-validation-tests 运行增强验证测试"
	@echo "  check-defense-coverage 检查防御覆盖率"
	@echo "  analyze-ci-issues   分析CI问题"
	@echo "  generate-defenses   生成防御机制"
	@echo "  update-defenses     更新防御机制"
	@echo "  integrate-defenses  集成防御机制到项目配置"
	@echo "  validate-integration 验证防御机制集成"

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

.PHONY: init
init: install ## 初始化项目（首次使用）
	@echo "$(BLUE)>>> 初始化项目结构...$(RESET)"
	$(ACTIVATE) && python scripts/setup_project.py
	@echo "$(GREEN)✅ 项目初始化完成$(RESET)"

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

.PHONY: context
context: venv ## 加载项目上下文
	@echo "$(BLUE)>>> 加载项目上下文...$(RESET)"
	$(ACTIVATE) && python scripts/context_loader.py --summary
	@echo "$(GREEN)✅ 上下文加载完成$(RESET)"

# -------------------------------
# 🔧 代码质量
# -------------------------------
.PHONY: format
format: venv ## 代码格式化
	@echo "$(BLUE)>>> 代码格式化...$(RESET)"
	$(ACTIVATE) && python -m black core/ models/ services/ utils/ database/ api/ tests/ scripts/
	@echo "$(GREEN)✅ 代码格式化完成$(RESET)"

.PHONY: lint
lint: venv ## 代码风格检查
	@echo "$(BLUE)>>> 代码风格检查...$(RESET)"
	$(ACTIVATE) && python -m flake8 core/ models/ services/ utils/ database/ api/ tests/ scripts/
	@echo "$(GREEN)✅ 代码风格检查通过$(RESET)"

.PHONY: typecheck
typecheck: venv ## 类型检查
	@echo "$(BLUE)>>> 类型检查...$(RESET)"
	@if $(ACTIVATE) && python -c "import mypy" 2>/dev/null; then \
		$(ACTIVATE) && python -m mypy core/ models/ services/ utils/ database/ api/ --ignore-missing-imports --explicit-package-bases; \
		echo "$(GREEN)✅ 类型检查完成$(RESET)"; \
	else \
		echo "$(YELLOW)⚠️ mypy未安装，跳过类型检查$(RESET)"; \
	fi

.PHONY: security
security: venv ## 安全检查
	@echo "$(BLUE)>>> 安全检查...$(RESET)"
	@if $(ACTIVATE) && python -c "import bandit" 2>/dev/null; then \
		$(ACTIVATE) && python -m bandit -r core/ models/ services/ utils/ database/ api/ -f json | python -m json.tool || true; \
		echo "$(GREEN)✅ 安全检查完成$(RESET)"; \
	else \
		echo "$(YELLOW)⚠️ bandit未安装，跳过安全检查$(RESET)"; \
	fi

.PHONY: complexity
complexity: venv ## 复杂度检查
	@echo "$(BLUE)>>> 复杂度分析...$(RESET)"
	@if $(ACTIVATE) && python -c "import radon" 2>/dev/null; then \
		$(ACTIVATE) && python -m radon cc core/ models/ services/ utils/ database/ api/ --show-complexity; \
		echo "$(GREEN)✅ 复杂度分析完成$(RESET)"; \
	else \
		echo "$(YELLOW)⚠️ radon未安装，跳过复杂度检查$(RESET)"; \
	fi

# -------------------------------
# 🧪 测试
# -------------------------------
.PHONY: test
test: venv ## 运行单元测试
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
coverage: venv ## 运行覆盖率测试
	@echo "$(BLUE)>>> 运行覆盖率测试...$(RESET)"
	@if [ -d "tests" ] && [ -n "$$(find tests -name '*.py' -type f)" ]; then \
		if $(ACTIVATE) && python -c "import pytest_cov" 2>/dev/null; then \
			if $(ACTIVATE) && python -m pytest --cov=core --cov=models --cov=services --cov=utils --cov=database --cov=api --cov-fail-under=78 --cov-report=xml --cov-report=html -v; then \
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

.PHONY: test-watch
test-watch: venv ## 监控模式运行测试
	@echo "$(BLUE)>>> 监控模式运行测试...$(RESET)"
	@if $(ACTIVATE) && python -c "import pytest_watch" 2>/dev/null; then \
		$(ACTIVATE) && ptw tests/; \
	else \
		echo "$(YELLOW)⚠️ pytest-watch未安装，运行普通测试$(RESET)"; \
		$(MAKE) test; \
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
		echo "$(YELLOW)   请修复代码质量问题后重试$(RESET)"; \
		exit 1; \
	fi

# -------------------------------
# 🚀 CI 模拟和闭环流程
# -------------------------------
.PHONY: ci
ci: env-check context quality test coverage ## 本地CI模拟
	@echo "$(GREEN)>>> 本地CI检查全部通过 ✅$(RESET)"
	@echo "$(GREEN)>>> 代码质量验证完成，可以安全推送$(RESET)"

.PHONY: ci-local
ci-local: ci ## 本地执行与远程完全相同的CI流程
	@echo "$(GREEN)>>> 本地CI-LOCAL检查全部通过 ✅$(RESET)"
	@echo "$(GREEN)>>> 与GitHub Actions CI流程保持一致$(RESET)"

.PHONY: cursor-run
cursor-run: venv ## 运行Cursor闭环系统
	@echo "$(BLUE)>>> 运行Cursor闭环系统...$(RESET)"
	@read -p "请输入任务描述: " task; \
	$(ACTIVATE) && python scripts/cursor_runner.py --task "$$task" --summary
	@echo "$(GREEN)✅ Cursor闭环执行完成$(RESET)"

.PHONY: prepush
prepush: ## 提交前完整检查、推送和Issue同步（带失败保护）
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
		echo "$(YELLOW)>>> 第3步: 同步Issues...$(RESET)"; \
		$(MAKE) sync; \
		echo "$(GREEN)🎉 prepush完整流程成功完成！$(RESET)"; \
	else \
		echo "$(RED)❌ CI检查失败，停止推送流程$(RESET)"; \
		echo "$(RED)   请修复上述问题后重新运行 make prepush$(RESET)"; \
		echo "$(YELLOW)💡 快速修复建议:$(RESET)"; \
		echo "$(YELLOW)   - 代码格式问题: make fix$(RESET)"; \
		echo "$(YELLOW)   - 测试失败: make test$(RESET)"; \
		echo "$(YELLOW)   - 环境问题: make env-check$(RESET)"; \
		exit 1; \
	fi

.PHONY: prepush-with-message
prepush-with-message: ## 提交前检查并使用自定义消息推送（带失败保护）
	@echo "$(BLUE)>>> 开始prepush流程（自定义消息+失败保护）...$(RESET)"
	@echo "$(YELLOW)>>> 第1步: 执行CI检查...$(RESET)"
	@if $(MAKE) ci; then \
		echo "$(GREEN)✅ CI检查通过，继续推送流程$(RESET)"; \
		echo "$(YELLOW)>>> 第2步: 准备提交...$(RESET)"; \
		read -p "请输入提交消息: " message; \
		if [ -z "$$(git status --porcelain)" ]; then \
			echo "$(YELLOW)⚠️ 工作区干净，无需提交$(RESET)"; \
		else \
			git add .; \
			git commit -m "$$message"; \
			git push origin HEAD; \
			echo "$(GREEN)✅ 代码推送完成$(RESET)"; \
		fi; \
		echo "$(YELLOW)>>> 第3步: 同步Issues...$(RESET)"; \
		$(MAKE) sync; \
		echo "$(GREEN)🎉 prepush完整流程成功完成！$(RESET)"; \
	else \
		echo "$(RED)❌ CI检查失败，停止推送流程$(RESET)"; \
		echo "$(RED)   请修复上述问题后重新运行 make prepush-with-message$(RESET)"; \
		echo "$(YELLOW)💡 快速修复建议:$(RESET)"; \
		echo "$(YELLOW)   - 代码格式问题: make fix$(RESET)"; \
		echo "$(YELLOW)   - 测试失败: make test$(RESET)"; \
		echo "$(YELLOW)   - 环境问题: make env-check$(RESET)"; \
		exit 1; \
	fi

# -------------------------------
# 📊 项目状态
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
.PHONY: ci-status ci-monitor ci-analyze ci-help
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

ci-help: ## 显示CI监控工具使用帮助
	@echo "$(BLUE)🔍 CI监控工具使用指南$(RESET)"
	@echo "==============================="
	@echo "$(YELLOW)📋 可用命令:$(RESET)"
	@echo "  make ci-status          查看最新CI状态"
	@echo "  make ci-monitor         实时监控CI执行"
	@echo "  make ci-analyze RUN_ID  分析特定CI运行"
	@echo ""
	@echo "$(YELLOW)💡 使用示例:$(RESET)"
	@echo "  make ci-status                    # 快速查看CI状态"
	@echo "  make ci-monitor                   # 推送后实时监控"
	@echo "  make ci-analyze RUN_ID=1234567    # 分析失败原因"
	@echo ""
	@echo "$(YELLOW)🔧 环境配置:$(RESET)"
	@echo "  export GITHUB_TOKEN=your_token    # 设置GitHub访问令牌"

# -------------------------------
# 📋 Issue 同步管理
# -------------------------------
.PHONY: sync
sync: ## 同步ISSUES.md到远程仓库
	@echo "$(BLUE)>>> 检查Issue同步配置...$(RESET)"
	@if [ -f "ISSUES.md" ]; then \
		echo "$(BLUE)>>> 发现 ISSUES.md，准备同步...$(RESET)"; \
		if [ -z "$$GIT_PLATFORM" ]; then \
			echo "$(YELLOW)⚠️ 未设置 GIT_PLATFORM 环境变量$(RESET)"; \
			echo "$(YELLOW)   请设置: export GIT_PLATFORM=github 或 export GIT_PLATFORM=gitee$(RESET)"; \
		elif [ "$$GIT_PLATFORM" = "github" ]; then \
			if command -v gh >/dev/null 2>&1; then \
				echo "$(BLUE)>>> 使用 GitHub CLI 同步Issues...$(RESET)"; \
				while IFS= read -r line; do \
					if [ -n "$$line" ] && [ "$${line#\#}" = "$$line" ]; then \
						echo "$(BLUE)   创建Issue: $$line$(RESET)"; \
						gh issue create --title "$$line" --body "Auto-synced from ISSUES.md" || echo "$(YELLOW)   ⚠️ Issue创建失败: $$line$(RESET)"; \
					fi; \
				done < ISSUES.md; \
				echo "$(GREEN)✅ GitHub Issues同步完成$(RESET)"; \
			else \
				echo "$(RED)❌ GitHub CLI (gh) 未安装$(RESET)"; \
				echo "$(YELLOW)   安装: brew install gh 或 apt install gh$(RESET)"; \
			fi; \
		elif [ "$$GIT_PLATFORM" = "gitee" ]; then \
			if command -v tea >/dev/null 2>&1; then \
				echo "$(BLUE)>>> 使用 Gitee CLI 同步Issues...$(RESET)"; \
				while IFS= read -r line; do \
					if [ -n "$$line" ] && [ "$${line#\#}" = "$$line" ]; then \
						echo "$(BLUE)   创建Issue: $$line$(RESET)"; \
						tea issue create --title "$$line" --body "Auto-synced from ISSUES.md" || echo "$(YELLOW)   ⚠️ Issue创建失败: $$line$(RESET)"; \
					fi; \
				done < ISSUES.md; \
				echo "$(GREEN)✅ Gitee Issues同步完成$(RESET)"; \
			else \
				echo "$(RED)❌ Gitee CLI (tea) 未安装$(RESET)"; \
				echo "$(YELLOW)   安装: https://gitea.com/gitea/tea$(RESET)"; \
			fi; \
		else \
			echo "$(RED)❌ 不支持的平台: $$GIT_PLATFORM$(RESET)"; \
			echo "$(YELLOW)   支持的平台: github, gitee$(RESET)"; \
		fi; \
	else \
		echo "$(YELLOW)>>> 未发现 ISSUES.md 文件，跳过Issue同步$(RESET)"; \
		echo "$(YELLOW)   创建 ISSUES.md 文件，每行一个Issue标题即可自动同步$(RESET)"; \
	fi

.PHONY: sync-config
sync-config: ## 配置Issue同步环境变量
	@echo "$(BLUE)>>> Issue同步配置向导$(RESET)"
	@echo ""
	@echo "$(YELLOW)请按照以下步骤配置:$(RESET)"
	@echo ""
	@echo "$(YELLOW)1. 选择平台并设置环境变量:$(RESET)"
	@echo "   GitHub: export GIT_PLATFORM=github"
	@echo "   Gitee:  export GIT_PLATFORM=gitee"
	@echo ""
	@echo "$(YELLOW)2. 安装对应的CLI工具:$(RESET)"
	@echo "   GitHub: brew install gh 或 apt install gh"
	@echo "   Gitee:  下载 tea CLI from https://gitea.com/gitea/tea"
	@echo ""
	@echo "$(YELLOW)3. 登录认证:$(RESET)"
	@echo "   GitHub: gh auth login"
	@echo "   Gitee:  tea login add"
	@echo ""
	@echo "$(YELLOW)4. 创建 ISSUES.md 文件:$(RESET)"
	@echo "   每行一个Issue标题，例如:"
	@echo "   实现用户认证功能"
	@echo "   修复登录页面bug"
	@echo "   添加数据导出功能"
	@echo ""
	@echo "$(YELLOW)5. 运行同步:$(RESET)"
	@echo "   make sync 或 make prepush"

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
	find . -type d -name __pycache__ -delete
	find . -type f -name "*.pyc" -delete
	@echo "$(GREEN)✅ 清理完成$(RESET)"

.PHONY: clean-logs
clean-logs: ## 清理日志文件
	@echo "$(BLUE)>>> 清理日志文件...$(RESET)"
	rm -rf logs/*.log
	rm -rf logs/*.json
	@echo "$(GREEN)✅ 日志清理完成$(RESET)"

# -------------------------------
# 🛡️ CI Guardian 防御系统
# -------------------------------
.PHONY: validate-defenses
validate-defenses: venv ## 验证所有防御机制
	@echo "$(BLUE)>>> 验证防御机制...$(RESET)"
	@if $(ACTIVATE) && python scripts/ci_guardian.py --validate; then \
		echo "$(GREEN)✅ 防御机制验证通过$(RESET)"; \
	else \
		echo "$(RED)❌ 防御机制验证失败$(RESET)"; \
		exit 1; \
	fi

.PHONY: run-validation-tests
run-validation-tests: venv ## 运行增强验证测试
	@echo "$(BLUE)>>> 运行验证测试...$(RESET)"
	$(ACTIVATE) && pytest tests/test_*_validation.py -v --tb=short

.PHONY: check-defense-coverage
check-defense-coverage: venv ## 检查防御覆盖率
	@echo "$(BLUE)>>> 检查防御覆盖率...$(RESET)"
	@if $(ACTIVATE) && python scripts/ci_issue_analyzer.py -s; then \
		echo "$(GREEN)✅ 防御覆盖率检查完成$(RESET)"; \
	else \
		echo "$(RED)❌ 防御覆盖率检查失败$(RESET)"; \
		exit 1; \
	fi

.PHONY: update-defenses
update-defenses: venv ## 更新防御机制
	@echo "$(BLUE)>>> 更新防御机制...$(RESET)"
	$(ACTIVATE) && python scripts/defense_generator.py -i logs/ci_issues.json -s

.PHONY: ci-guardian
ci-guardian: venv ## 运行完整CI守护检查
	@echo "$(BLUE)>>> 运行CI守护检查...$(RESET)"
	$(ACTIVATE) && python scripts/ci_guardian.py -c "make quality" -s

.PHONY: analyze-ci-issues
analyze-ci-issues: venv ## 分析CI问题
	@echo "$(BLUE)>>> 分析CI问题...$(RESET)"
	$(ACTIVATE) && python scripts/ci_issue_analyzer.py -l logs/quality_check.json -s -r

.PHONY: generate-defenses
generate-defenses: venv ## 生成防御机制
	@echo "$(BLUE)>>> 生成防御机制...$(RESET)"
	$(ACTIVATE) && python scripts/defense_generator.py -i logs/ci_issues.json

.PHONY: integrate-defenses
integrate-defenses: venv ## 集成防御机制到项目配置
	@echo "$(BLUE)>>> 集成防御机制...$(RESET)"
	$(ACTIVATE) && python scripts/auto_ci_updater.py -d logs/defenses_generated.json

.PHONY: validate-integration
validate-integration: venv ## 验证防御机制集成
	@echo "$(BLUE)>>> 验证防御机制集成...$(RESET)"
	$(ACTIVATE) && python scripts/defense_validator.py -d logs/defenses_generated.json -s

# -------------------------------
# 🎯 快捷方式
# -------------------------------
.PHONY: dev
dev: install env-check ## 开发环境快速准备
	@echo "$(GREEN)✅ 开发环境已准备就绪$(RESET)"
	@echo "$(BLUE)>>> 可以开始编码了！建议运行: make status$(RESET)"

.PHONY: fix
fix: format lint ## 快速修复代码问题
	@echo "$(GREEN)✅ 代码问题修复完成$(RESET)"

.PHONY: check
check: quality test ## 快速质量检查
	@echo "$(GREEN)✅ 快速检查完成$(RESET)"

# 默认目标
.DEFAULT_GOAL := help
