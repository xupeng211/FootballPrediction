# 依赖管理最佳实践指南

## 概述

本文档提供了Python项目依赖管理的完整最佳实践，确保开发、测试和生产环境的一致性和可重现性。

## 核心原则

### 1. 可重现性
- **锁定所有依赖** - 包括直接和间接依赖
- **版本精确** - 避免版本范围，使用确切的版本号
- **环境一致** - 确保所有开发者使用相同版本

### 2. 安全性
- **及时更新** - 定期更新依赖以修复安全漏洞
- **审计依赖** - 使用工具检查已知漏洞
- **最小权限** - 只安装必要的依赖

### 3. 可维护性
- **清晰分离** - 区分生产、开发和测试依赖
- **文档完整** - 记录每个依赖的用途
- **自动化** - 使用工具管理依赖生命周期

## 文件结构

```
project/
├── requirements.txt           # 生产依赖（核心）
├── requirements-dev.txt       # 开发依赖
├── requirements-test.txt      # 测试依赖
├── requirements.lock.txt      # 完整依赖锁定（自动生成）
├── requirements_frozen.txt    # 临时文件（不提交）
└── scripts/dependency/        # 依赖管理脚本
    ├── check_consistency.py
    ├── update_lock.py
    └── audit_deps.py
```

## 依赖文件说明

### requirements.txt
```txt
# 核心运行时依赖
fastapi>=0.104.0,<0.110.0
sqlalchemy[asyncio]>=2.0.0,<2.1.0
redis>=5.0.0,<6.0.0
pydantic>=2.4.0,<3.0.0
```

### requirements-dev.txt
```txt
# 开发工具依赖
-r requirements.txt
black>=23.0.0
ruff>=0.1.0
mypy>=1.5.0
pytest>=7.4.0
```

### requirements.lock.txt
```txt
# 自动生成的完整依赖锁定文件
# 包含208个包的精确版本
# 确保完全可重现的构建
```

## 工作流程

### 日常开发

```bash
# 1. 克隆项目后
git clone <repository>
cd project

# 2. 创建虚拟环境
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# 或
.venv\Scripts\activate     # Windows

# 3. 安装锁定依赖
make install-locked

# 4. 验证环境
make verify-deps
make env-check
```

### 添加新依赖

```bash
# 1. 安装新包
pip install new-package==1.2.3

# 2. 更新requirements文件
echo "new-package==1.2.3" >> requirements.txt

# 3. 立即锁定所有依赖
make lock-deps

# 4. 验证并测试
make verify-deps
make test-quick

# 5. 提交更改
git add requirements.txt requirements.lock.txt
git commit -m "feat: add new-package dependency"
```

### 更新依赖

```bash
# 1. 更新特定包
pip install --upgrade package-name

# 2. 或更新所有依赖
pip install --upgrade -r requirements.txt

# 3. 重新锁定
make lock-deps

# 4. 运行完整测试
make test

# 5. 提交更新
git add requirements.lock.txt
git commit -m "chore: update dependencies"
```

## Make命令参考

### 本项目提供的Make命令

```makefile
# 安装依赖
install:              # 常规安装
install-locked:       # 安装锁定版本（推荐）
install-dev:          # 安装开发依赖
install-all:          # 安装所有依赖

# 管理依赖
lock-deps:            # 锁定当前依赖
verify-deps:          # 验证依赖一致性
check-deps:           # 检查必需依赖
update-deps:          # 更新依赖
audit-deps:           # 审计安全漏洞

# 环境检查
env-check:            # 检查开发环境
clean-deps:           # 清理依赖缓存
```

## CI/CD集成

### GitHub Actions示例

```yaml
name: CI Pipeline

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install pip-tools
        run: pip install pip-tools

      - name: Check dependency consistency
        run: |
          if [ -f "requirements.lock.txt" ]; then
            make verify-deps
          fi

      - name: Install dependencies
        run: |
          if [ -f "requirements.lock.txt" ]; then
            make install-locked
          else
            make install
          fi

      - name: Run tests
        run: make test
```

### 缓存策略

```yaml
- name: Cache dependencies
  uses: actions/cache@v3
  with:
    path: |
      ~/.cache/pip
      .venv
    key: ${{ runner.os }}-deps-${{ hashFiles('**/requirements*.txt') }}
```

## 安全最佳实践

### 1. 定期审计

```bash
# 使用safety检查已知漏洞
pip install safety
safety check

# 使用pip-audit
pip install pip-audit
pip-audit

# 或使用make命令
make audit-deps
```

### 2. 管理私有包

```bash
# 配置私有索引
pip config set global.index-url https://pypi.example.com/simple
pip config set global.extra-index-url https://pypi.org/simple

# 使用认证令牌
pip install --index-url https://user:token@pypi.example.com/simple package-name
```

### 3. 锁定文件安全

- **提交锁文件** - 确保团队使用相同版本
- **签名验证** - 对锁文件进行数字签名
- **定期审查** - 检查锁文件的变化

## 故障排除

### 常见问题

#### 1. 依赖冲突

```bash
# 症状：ERROR: pip's dependency resolver does not currently take into account...
# 解决方案：
rm -rf .venv
python -m venv .venv
source .venv/bin/activate
make install-locked
```

#### 2. 锁文件过时

```bash
# 症状：make verify-deps 失败
# 解决方案：
make lock-deps
git add requirements.lock.txt
git commit -m "chore: update dependency lock"
```

#### 3. 平台特定依赖

```txt
# requirements.txt
pywin32==306; sys_platform == "win32"
uvloop==0.19.0; sys_platform != "win32"
```

#### 4. 构建依赖问题

```bash
# 安装构建工具
pip install build wheel setuptools

# 或使用系统包管理器
# Ubuntu/Debian
sudo apt-get install build-essential python3-dev

# macOS
xcode-select --install
```

### 调试技巧

```bash
# 查看依赖树
pip install pipdeptree
pipdeptree

# 检查包来源
pip show package-name

# 查看安装历史
pip list --outdated

# 干运行安装
pip install --dry-run package-name
```

## 高级主题

### 1. 条件依赖

```txt
# requirements.txt
# 生产环境
uvicorn[standard]>=0.24.0; environment == "production"

# 开发环境
pytest>=7.4.0; environment == "development"
black>=23.0.0; environment == "development"

# 特定功能
mlflow>=2.7.0; extra == "ml"
psycopg2-binary>=2.9.0; extra == "postgres"
```

### 2. 可选依赖

```txt
# setup.py 或 pyproject.toml
extras_require={
    "ml": ["mlflow>=2.7.0", "scikit-learn>=1.3.0"],
    "postgres": ["psycopg2-binary>=2.9.0"],
    "dev": ["black>=23.0.0", "pytest>=7.4.0"],
}
```

### 3. 依赖版本策略

```txt
# 严格版本（推荐用于关键依赖）
fastapi==0.104.1

# 兼容版本
sqlalchemy>=2.0.0,<2.1.0

# 最低版本（谨慎使用）
pydantic>=2.4.0
```

### 4. 依赖分组

```txt
# requirements-dev.txt
-r requirements.txt

# 格式化工具
black>=23.0.0
isort>=5.12.0

# 代码质量
ruff>=0.1.0
mypy>=1.5.0
bandit>=1.7.0

# 测试工具
pytest>=7.4.0
pytest-cov>=4.1.0
pytest-asyncio>=0.21.0

# 文档生成
mkdocs>=1.5.0
mkdocs-material>=9.2.0
```

## 工具对比

| 工具 | 优点 | 缺点 | 适用场景 |
|------|------|------|----------|
| pip + requirements.lock.txt | 简单，标准，无需额外工具 | 需要手动管理锁文件 | 通用项目 |
| Pipenv | 集成虚拟环境，Pipfile锁定 | 较慢，有时有bug | 简单项目 |
| Poetry | 现代化，功能丰富，依赖解析强大 | 改变工作流，学习成本 | 新项目 |
| PDM | 快速，支持PEP 582 | 较新，生态不成熟 | 性能敏感项目 |

## 迁移指南

### 从pip到pip-tools

```bash
# 1. 安装pip-tools
pip install pip-tools

# 2. 生成初始锁文件
pip-compile requirements.in -o requirements.lock.txt

# 3. 使用锁文件安装
pip install -r requirements.lock.txt
```

### 从Pipenv到pip

```bash
# 1. 导出依赖
pipenv requirements > requirements.txt
pipenv requirements --dev-only > requirements-dev.txt

# 2. 生成锁文件
make lock-deps

# 3. 安装依赖
make install-locked
```

## 最佳实践总结

### ✅ 必须做

1. **始终使用虚拟环境**
2. **锁定所有依赖版本**
3. **定期更新依赖**
4. **运行安全审计**
5. **使用CI/CD验证依赖**
6. **文档化依赖用途**
7. **分离不同环境的依赖**

### ❌ 不要做

1. **不要手动编辑锁文件**
2. **不要使用sudo pip**
3. **不要在全局安装包**
4. **不要忽略版本冲突**
5. **不要提交缓存文件**
6. **不要使用过时的依赖**

## 相关资源

- [Python打包指南](https://packaging.python.org/)
- [pip文档](https://pip.pypa.io/)
- [PyPI安全公告](https://py.org/advisories/)
- [Dependabot配置](https://docs.github.com/en/code-security/dependabot)
- [Safety安全检查](https://pyup.io/safety/)
- [pip-audit工具](https://github.com/trailofbits/pip-audit)

---

版本: 1.0
最后更新: 2025-10-05
作者: Claude Code Assistant
