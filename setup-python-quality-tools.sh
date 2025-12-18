#!/bin/bash
"""
Python代码质量工具安装配置脚本
基于发现的Claude Skills的最佳实践配置
"""

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

print_header() {
    echo -e "${PURPLE}========================================${NC}"
    echo -e "${PURPLE}$1${NC}"
    echo -e "${PURPLE}========================================${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

# 安装基础Python代码质量工具
install_basic_tools() {
    print_header "🔧 安装基础Python代码质量工具"

    print_info "安装Black代码格式化器..."
    pip install "black[jupyter]" --upgrade

    print_info "安装Flake8代码风格检查器..."
    pip install flake8 --upgrade

    print_info "安装flake8-black插件（Black和Flake8集成）..."
    pip install flake8-black --upgrade

    print_info "安装isort导入排序器..."
    pip install isort --upgrade

    print_info "安装MyPy类型检查器..."
    pip install mypy --upgrade

    print_success "基础工具安装完成"
}

# 安装现代化代码质量工具
install_modern_tools() {
    print_header "🚀 安装现代化Python代码质量工具"

    print_info "安装Ruff（超快的linter和formatter）..."
    pip install ruff --upgrade

    print_info "安装Pyright（微软类型检查器）..."
    pip install pyright --upgrade

    print_info "安装Bandit安全扫描器..."
    pip install bandit[toml] --upgrade

    print_info "安装Safety（依赖漏洞检查）..."
    pip install safety --upgrade

    print_success "现代化工具安装完成"
}

# 安装高级代码质量工具
install_advanced_tools() {
    print_header "🎯 安装高级代码质量工具"

    print_info "安装pre-commit（Git钩子自动化）..."
    pip install pre-commit --upgrade

    print_info "安装vulture（死代码检测）..."
    pip install vulture --upgrade

    print_info "安装radon（代码复杂度分析）..."
    pip install radon --upgrade

    print_info "安装pylint（深度代码分析）..."
    pip install pylint --upgrade

    print_info "安装pydocstyle（文档字符串检查）..."
    pip install pydocstyle --upgrade

    print_success "高级工具安装完成"
}

# 创建配置文件
create_config_files() {
    print_header "📋 创建代码质量配置文件"

    # 创建Black配置
    cat > pyproject.toml << 'EOF'
[tool.black]
line-length = 120
target-version = ['py311']
include = '\.pyi?$'
extend-exclude = '''
/(
  # directories
  \.eggs
  | \.git
  | \.hg
  | \.mypy_cache
  | \.tox
  | \.venv
  | build
  | dist
)/
'''

[tool.isort]
profile = "black"
line_length = 120
multi_line_output = 3
include_trailing_comma = true
force_grid_wrap = 0
use_parentheses = true
ensure_newline_before_comments = true

[tool.mypy]
python_version = "3.11"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true
disallow_incomplete_defs = true
check_untyped_defs = true
disallow_untyped_decorators = true
no_implicit_optional = true
warn_redundant_casts = true
warn_unused_ignores = true
warn_no_return = true
warn_unreachable = true
strict_equality = true

[tool.ruff]
line-length = 120
select = [
    "E",  # pycodestyle errors
    "W",  # pycodestyle warnings
    "F",  # pyflakes
    "I",  # isort
    "B",  # flake8-bugbear
    "C4", # flake8-comprehensions
    "UP", # pyupgrade
]
ignore = [
    "E501",  # line too long, handled by black
    "B008",  # do not perform function calls in argument defaults
    "C901",  # too complex
]

[tool.ruff.per-file-ignores]
"__init__.py" = ["F401"]
"tests/*" = ["B011"]

[tool.ruff.isort]
known-first-party = ["src"]

[tool.bandit]
exclude_dirs = ["tests", "test_*"]
skips = ["B101", "B601"]

[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py", "*_test.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
addopts = "--strict-markers --strict-config"
markers = [
    "slow: marks tests as slow (deselect with '-m \"not slow\"')",
    "integration: marks tests as integration tests",
]
EOF

    # 创建Flake8配置
    cat > .flake8 << 'EOF'
[flake8]
max-line-length = 120
extend-ignore = E203, E266, E501, W503, F403, F401
max-complexity = 18
select = B,C,E,F,W,T4,B9
exclude =
    .git,
    __pycache__,
    .venv,
    .eggs,
    *.egg,
    build,
    dist,
    migrations
per-file-ignores =
    __init__.py:F401
    tests/*:S101
EOF

    # 创建MyPy配置
    cat > mypy.ini << 'EOF'
[mypy]
python_version = 3.11
warn_return_any = True
warn_unused_configs = True
disallow_untyped_defs = True
disallow_incomplete_defs = True
check_untyped_defs = True
disallow_untyped_decorators = True
no_implicit_optional = True
warn_redundant_casts = True
warn_unused_ignores = True
warn_no_return = True
warn_unreachable = True
strict_equality = True

[mypy-tests.*]
disallow_untyped_defs = False

[[tool.mypy.overrides]]
module = [
    "numpy.*",
    "pandas.*",
    "sklearn.*",
    "matplotlib.*",
    "seaborn.*",
]
ignore_missing_imports = True
EOF

    # 创建pre-commit配置
    cat > .pre-commit-config.yaml << 'EOF'
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.5.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-added-large-files
      - id: check-merge-conflict
      - id: debug-statements

  - repo: https://github.com/psf/black
    rev: 24.4.2
    hooks:
      - id: black
        language_version: python3.11

  - repo: https://github.com/pycqa/isort
    rev: 5.13.2
    hooks:
      - id: isort
        args: ["--profile", "black"]

  - repo: https://github.com/pycqa/flake8
    rev: 7.0.0
    hooks:
      - id: flake8

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.10.0
    hooks:
      - id: mypy
        additional_dependencies: [types-all]

  - repo: https://github.com/pycqa/bandit
    rev: 1.7.8
    hooks:
      - id: bandit
        args: ["-c", "pyproject.toml"]

  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.6.2
    hooks:
      - id: ruff
        args: [--fix, --exit-non-zero-on-fix]
      - id: ruff-format
EOF

    print_success "配置文件创建完成"
}

# 创建Makefile质量目标
create_makefile_targets() {
    print_header "🛠️ 创建Makefile质量目标"

    # 检查Makefile是否已存在
    if [ -f "Makefile" ]; then
        print_warning "Makefile已存在，将添加质量检查目标"
    else
        print_info "创建新的Makefile"
    fi

    # 添加质量检查目标到Makefile
    cat >> Makefile << 'EOF'

# Python代码质量检查目标
.PHONY: format lint format-check lint-check typecheck security quality quality-fix pre-commit-install

# 代码格式化
format:
	@echo "🔧 格式化Python代码..."
	. venv/bin/activate && python -m black src/ tests/ scripts/
	. venv/bin/activate && python -m isort src/ tests/ scripts/

# 代码风格检查
lint:
	@echo "🔍 检查代码风格..."
	. venv/bin/activate && python -m flake8 src/ tests/ scripts/

# 格式化检查
format-check:
	@echo "🔍 检查代码格式..."
	. venv/bin/activate && python -m black --check src/ tests/ scripts/

# Lint检查
lint-check:
	@echo "🔍 运行lint检查..."
	. venv/bin/activate && python -m flake8 src/ tests/ scripts/

# 类型检查
typecheck:
	@echo "🔍 运行类型检查..."
	. venv/bin/activate && python -m mypy src/ --ignore-missing-imports

# 安全检查
security:
	@echo "🔒 运行安全检查..."
	. venv/bin/activate && python -m bandit -r src/ -f json -o bandit-report.json
	. venv/bin/activate && python -m safety check

# 综合质量检查
quality: format-check lint-check typecheck security
	@echo "✅ 所有质量检查完成"

# 自动修复
quality-fix:
	@echo "🔧 自动修复质量问题..."
	. venv/bin/activate && python -m black src/ tests/ scripts/
	. venv/bin/activate && python -m isort src/ tests/ scripts/
	. venv/bin/activate && python -m ruff check src/ tests/ scripts/ --fix
	@echo "✅ 自动修复完成"

# 安装pre-commit钩子
pre-commit-install:
	@echo "🔧 安装pre-commit钩子..."
	. venv/bin/activate && pre-commit install
	@echo "✅ pre-commit钩子安装完成"

# 运行pre-commit检查
pre-commit-check:
	@echo "🔍 运行pre-commit检查..."
	. venv/bin/activate && pre-commit run --all-files
EOF

    print_success "Makefile质量目标添加完成"
}

# 创建Python代码质量Claude Skill模拟配置
create_claude_skill_config() {
    print_header "🤖 创建Python代码质量Claude Skill配置"

    # 创建.claude目录结构
    mkdir -p .claude/skills

    # 创建Python代码质量Skill配置
    cat > .claude/skills/python-code-quality.md << 'EOF'
# Python代码质量Claude Skill

## 🎯 Skill描述
基于最佳实践的Python代码质量自动化工具集，提供企业级的代码质量保障。

## 🔧 包含工具

### 基础工具
- **Black**: 代码格式化器
- **Flake8**: 代码风格检查器
- **isort**: 导入排序器
- **MyPy**: 类型检查器

### 现代化工具
- **Ruff**: 超快的linter和formatter
- **Pyright**: 微软类型检查器
- **Bandit**: 安全扫描器
- **Safety**: 依赖漏洞检查

### 高级工具
- **pre-commit**: Git钩子自动化
- **vulture**: 死代码检测
- **radon**: 代码复杂度分析
- **pylint**: 深度代码分析

## 🚀 使用方法

### 快速质量检查
```bash
# 基础检查
make format          # 格式化代码
make lint            # 检查代码风格
make typecheck       # 类型检查
make security        # 安全检查

# 综合检查
make quality         # 运行所有质量检查
make quality-fix     # 自动修复问题
```

### CI/CD集成
```bash
# pre-commit安装
make pre-commit-install

# pre-commit检查
make pre-commit-check
```

## 📋 质量标准

### 代码格式化
- Black格式化通过
- 行长度限制: 120字符
- Python版本: 3.11+

### 代码风格
- Flake8检查通过
- PEP 8标准遵守
- 导入排序: isort

### 类型安全
- MyPy类型检查通过
- 严格的类型注解
- 类型覆盖率: 80%+

### 安全标准
- Bandit安全扫描通过
- Safety依赖检查通过
- 无已知安全漏洞

## 🎯 质量门禁

### 必须通过
- ✅ 代码格式化检查
- ✅ 代码风格检查
- ✅ 基础类型检查
- ✅ 安全扫描检查

### 建议通过
- ⭐ 深度类型检查
- ⭐ 代码复杂度检查
- ⭐ 死代码检查
- ⭐ 文档字符串检查

## 📊 质量报告

### 自动生成报告
- `bandit-report.json`: 安全扫描报告
- `complexity-report.txt`: 复杂度分析报告
- `quality-report.html`: 质量综合报告

### 集成监控
- 实时质量分数监控
- 质量趋势分析
- 技术债务跟踪

## 🔧 配置文件

### pyproject.toml
Black, isort, MyPy, Ruff统一配置

### .flake8
Flake8详细配置

### mypy.ini
MyPy严格模式配置

### .pre-commit-config.yaml
Git钩子自动化配置

## 📈 质量目标

### 短期目标 (1周)
- 质量分数: 50 → 70
- 代码风格问题: < 10个
- 类型检查覆盖率: > 80%

### 中期目标 (1月)
- 质量分数: 70 → 85
- 安全扫描: 100%通过
- 文档覆盖率: > 90%

### 长期目标 (3月)
- 质量分数: > 90
- 零技术债务
- 企业级质量标准

## 🎊 最佳实践

### 开发流程
1. 编写代码 → 2. 自动格式化 → 3. 质量检查 → 4. 提交代码

### 团队协作
1. 统一配置文件
2. pre-commit钩子
3. 定期质量审查
4. 持续改进流程

### 质量文化
1. 质量优先原则
2. 自动化工具辅助
3. 数据驱动决策
4. 持续学习改进

---

*基于Claude Skills最佳实践的企业级Python代码质量解决方案*
EOF

    print_success "Python代码质量Claude Skill配置完成"
}

# 主函数
main() {
    print_header "🤖 Python代码质量Claude Skills配置"

    print_info "基于发现的Claude Skills，配置企业级Python代码质量工具集..."

    # 检查虚拟环境
    if [ ! -d "venv" ]; then
        print_warning "未找到虚拟环境，将创建..."
        python -m venv venv
        source venv/bin/activate
        pip install --upgrade pip
    else
        print_info "使用现有虚拟环境..."
        source venv/bin/activate
        pip install --upgrade pip
    fi

    # 安装工具
    install_basic_tools
    install_modern_tools
    install_advanced_tools

    # 创建配置文件
    create_config_files
    create_makefile_targets
    create_claude_skill_config

    # 安装pre-commit
    print_info "安装pre-commit钩子..."
    pre-commit install

    print_header "🎉 Python代码质量Claude Skills配置完成"
    print_success "✅ 基础工具安装完成"
    print_success "✅ 现代化工具安装完成"
    print_success "✅ 高级工具安装完成"
    print_success "✅ 配置文件创建完成"
    print_success "✅ Makefile目标创建完成"
    print_success "✅ Claude Skill配置完成"

    echo ""
    print_info "🚀 现在可以使用以下命令："
    echo "   make format          # 格式化代码"
    echo "   make lint            # 检查代码风格"
    echo "   make quality         # 运行所有质量检查"
    echo "   make quality-fix     # 自动修复问题"
    echo ""
    print_info "📋 配置详情请查看: .claude/skills/python-code-quality.md"
}

if [ "${BASH_SOURCE[0]}" = "${0}" ]; then
    main "$@"
fi