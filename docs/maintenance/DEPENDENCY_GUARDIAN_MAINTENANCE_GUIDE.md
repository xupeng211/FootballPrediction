# 📚 依赖守护者维护指南

> **FootballPrediction 项目依赖冲突防御工作流长期运维手册**

**版本**: v1.0
**编写日期**: 2025-01-04
**维护团队**: FootballPrediction 开发团队
**文档状态**: 正式发布

---

## 🧱 1. 前言

### 1.1 设计目的

本指南旨在建立和维护一个**零依赖冲突**的开发环境，通过自动化防御机制确保：
- 本地、CI、生产环境的依赖版本完全一致
- 依赖更新过程可控、可追溯
- 安全漏洞及时发现和修复

### 1.2 系统架构概览

我们采用了 `pip-tools + Makefile + CI Guardian` 三层防御体系：

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   开发者操作      │    │   Makefile      │    │  pip-tools     │
│                 │───▶│                 │───▶│                 │
│ 编辑 .in 文件    │    │ lock-deps       │    │ pip-compile     │
│ 提交代码         │    │ verify-deps     │    │ pip-sync        │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                                       │
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  生产/CI环境     │    │  GitHub CI      │    │   .lock 文件     │
│                 │◀───│                 │◀───│                 │
│ pip install     │    │ deps_guardian   │    │ 版本锁定         │
│ venv 激活       │    │ 自动验证         │    │ 依赖解析         │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### 1.3 核心原则

1. **锁定优先**: 所有环境必须使用 `.lock` 文件安装依赖
2. **最小变更**: 只在必要时更新依赖，避免不必要的风险
3. **自动防御**: CI 自动阻止不一致的依赖提交
4. **定期审计**: 定期检查安全漏洞和依赖更新

---

## 🔄 2. 依赖体系总览

### 2.1 目录结构

```
requirements/
├── base.in          # 基础生产依赖定义
├── base.lock        # 基础生产依赖锁定文件
├── dev.in           # 开发依赖定义
├── dev.lock         # 开发依赖锁定文件
├── full.in          # 完整依赖定义
├── requirements.lock # 完整依赖锁定文件
└── README.md        # 依赖管理说明

scripts/
└── verify_deps.sh   # 依赖一致性验证脚本

.github/workflows/
└── deps_guardian.yml # CI 自动防御工作流

Makefile             # 依赖管理命令集合
```

### 2.2 文件职责说明

| 文件 | 用途 | 使用环境 | 说明 |
|------|------|----------|------|
| `base.in` | 核心生产依赖定义 | 开发 | 定义 FastAPI、SQLAlchemy 等核心包 |
| `base.lock` | 核心生产依赖锁定 | 生产/CI | 包含精确版本号，用于生产部署 |
| `dev.in` | 开发工具依赖定义 | 开发 | 包含 pytest、black、mypy 等工具 |
| `dev.lock` | 开发工具依赖锁定 | 开发/CI | 开发环境完整依赖列表 |
| `requirements.lock` | 完整依赖锁定 | 备用 | 包含所有依赖的超级锁定文件 |

### 2.3 环境映射关系

```yaml
生产环境: requirements/base.lock
开发环境: requirements/dev.lock
CI 环境: requirements/requirements.lock (默认)
本地测试: make test-quick (使用 dev.lock)
```

---

## 🧰 3. 日常维护流程

### 3.1 开发阶段依赖更新

#### 添加新依赖

```bash
# 1. 编辑对应的 .in 文件
echo "new-package==1.2.3" >> requirements/base.in

# 2. 重新生成锁定文件
make lock-deps

# 3. 验证一致性
make verify-deps

# 4. 提交更改
git add requirements/
git commit -m "chore(deps): add new-package v1.2.3"
```

#### 更新现有依赖

```bash
# 1. 修改版本号
vim requirements/base.in  # 修改 package==1.2.3 -> package==2.0.0

# 2. 重新生成锁定文件（会自动处理依赖传递）
make lock-deps

# 3. 检查是否有破坏性变更
make verify-deps

# 4. 运行测试确保兼容性
make test-quick

# 5. 提交
git add requirements/
git commit -m "chore(deps): update package from 1.2.3 to 2.0.0"
```

### 3.2 依赖管理最佳实践

#### ✅ 推荐做法

```bash
# 使用精确版本号
package==1.2.3

# 使用范围约束（必要时）
package>=1.2.3,<2.0.0

# 通过 Makefile 管理
make lock-deps
make verify-deps
make install
```

#### ❌ 禁止行为

```bash
# 不要直接安装到环境
pip install package  # 禁止！

# 不要使用无版本约束
package  # 禁止！

# 不要手动编辑 .lock 文件
vim requirements/base.lock  # 禁止！
```

### 3.3 本地环境重建

```bash
# 完全清理并重建
make clean-env
make install

# 或分步执行
rm -rf .venv
python -m venv .venv
source .venv/bin/activate
make install
```

---

## 🔒 4. 自动防御机制

### 4.1 verify_deps.sh 详解

位置: `scripts/verify_deps.sh`

```bash
#!/usr/bin/env bash
set -e
echo "🔍 Verifying dependency consistency..."

# 1. 检查依赖冲突
pip check || (echo "❌ pip check failed" && exit 1)

# 2. 验证 .lock 文件与 .in 文件一致
if [ -f requirements/base.in ]; then
  pip-compile requirements/base.in --quiet --output-file=/tmp/base.lock
  # 忽略头部注释差异，只比较依赖内容
  if ! tail -n +7 requirements/base.lock | diff -q - <(tail -n +7 /tmp/base.lock) >/dev/null; then
    echo "⚠️  base.lock 与 base.in 不一致，请执行 make lock-deps"
    exit 1
  fi
fi

echo "✅ Dependencies are consistent"
```

**功能说明**:
- 自动运行 `pip check` 检测循环依赖和版本冲突
- 验证 `.lock` 文件是否是最新生成的
- 忽略头部注释差异，避免误报

### 4.2 GitHub Workflow 详解

位置: `.github/workflows/deps_guardian.yml`

```yaml
name: Dependency Guardian

on:
  push:
    paths:
      - "requirements/**"
      - "scripts/**"
      - ".github/workflows/deps_guardian.yml"
  pull_request:
    paths:
      - "requirements/**"

jobs:
  verify:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - name: Install pip-tools
        run: pip install pip-tools
      - name: Verify dependencies
        run: bash scripts/verify_deps.sh
      - name: Check lock files
        run: |
          pip check
          echo "✅ All dependencies verified"
```

**触发条件**:
- 修改 `requirements/` 目录下任何文件
- 修改 `scripts/verify_deps.sh`
- 修改工作流文件本身

**执行逻辑**:
1. 设置 Python 3.11 环境
2. 安装 pip-tools
3. 运行验证脚本
4. 失败时 PR 自动标记为错误状态

### 4.3 Makefile 命令参考

| 命令 | 功能 | 使用场景 |
|------|------|----------|
| `make install` | 安装锁定依赖 | 新环境初始化 |
| `make install-locked` | 可重现构建 | CI/CD 部署 |
| `make lock-deps` | 重新生成锁定文件 | 依赖更新后 |
| `make verify-deps` | 本地检查一致性 | 提交前验证 |
| `make clean-env` | 清理环境 | 故障排查 |
| `make env-check` | 检查环境配置 | 问题诊断 |

---

## 🧪 5. 安全与审计机制

### 5.1 安全审计流程

#### 安装审计工具

```bash
pip install pip-audit
```

#### 执行安全检查

```bash
# 检查所有依赖的已知漏洞
pip-audit

# 检查特定环境
pip-audit -r requirements/base.lock

# 生成报告
pip-audit --format=json --output=audit-report.json
```

#### 处理安全漏洞

```bash
# 示例：修复 requests 包的漏洞
# 1. 查找受影响的版本
pip-audit -v

# 2. 更新到安全版本
vim requirements/base.in  # 修改 requests==2.28.1 -> requests==2.31.0

# 3. 重新生成锁定文件
make lock-deps

# 4. 验证修复
pip-audit
```

### 5.2 Dependabot 配置

创建 `.github/dependabot.yml`:

```yaml
version: 2
updates:
  # Python 依赖更新
  - package-ecosystem: "pip"
    directory: "/requirements"
    schedule:
      interval: "weekly"
      day: "monday"
      time: "09:00"
    open-pull-requests-limit: 5
    reviewers:
      - "tech-lead"
    assignees:
      - "maintainer"
    commit-message:
      prefix: "chore"
      include: "scope"
    # 允许自动合并补丁版本
    auto-merge: true
    # 忽略某些包的更新
    ignore:
      - dependency-name: "redis"
        versions: ["5.x"]

  # GitHub Actions 更新
  - package-ecosystem: "github-actions"
    directory: "/"
    schedule:
      interval: "monthly"
```

### 5.3 风险防护策略

#### 版本锁定策略

```yaml
生产环境: 使用精确版本 (==)
开发环境: 使用精确版本 (==)
测试环境: 使用精确版本 (==)
```

#### 包审查清单

- [ ] 是否真的需要这个包？
- [ ] 是否有更轻量的替代方案？
- [ ] 包的维护状态是否活跃？
- [ ] 是否有已知的安全漏洞？
- [ ] 许可证是否兼容？

#### 禁用策略

```bash
# .gitignore 中添加
requirements.txt
!requirements/*.in
!requirements/*.lock

# pre-commit hook 中检查
- repo: local
  hooks:
    - id: no-requirements-txt
      name: 禁止 requirements.txt
      entry: |
        if [ -f requirements.txt ]; then
          echo "❌ 请使用 requirements/ 目录结构"
          exit 1
        fi
      language: system
```

---

## 📆 6. 定期维护计划

### 6.1 维护矩阵

| 周期 | 任务 | 负责人 | 工具 | 检查项 |
|------|------|--------|------|--------|
| **每日** | `make verify-deps` | 所有开发者 | 本地 | 依赖一致性 |
| **每周** | Dependabot PR 审查 | Tech Lead | GitHub | 依赖更新 |
| **每月** | `pip-audit` + `make lock-deps` | 维护者 | CI | 安全漏洞 |
| **每季度** | 依赖树审查 | 架构组 | 手动 | 废包清理 |
| **每半年** | Python 版本兼容性 | 架构组 | CI | 重大升级 |

### 6.2 月度维护脚本

创建 `scripts/monthly_deps_check.sh`:

```bash
#!/usr/bin/env bash
set -e

echo "🗓️  Monthly Dependency Maintenance"
echo "=================================="

# 1. 检查安全漏洞
echo "1. Checking security vulnerabilities..."
pip-audit -r requirements/requirements.lock || true

# 2. 更新依赖（可选）
read -p "2. Update dependencies? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
  make lock-deps
fi

# 3. 运行完整测试
echo "3. Running full test suite..."
make test

# 4. 生成报告
echo "4. Generating dependency report..."
pip list --format=freeze > deps-report-$(date +%Y%m).txt

echo "✅ Monthly maintenance completed!"
```

### 6.3 季度审查清单

- [ ] 依赖数量趋势（是否过多）
- [ ] 包大小统计（是否过大）
- [ ] 启动时间影响
- [ ] 许可证合规检查
- [ ] 替代方案调研
- [ ] 技术债务评估

---

## 🧭 7. 故障排查指南

### 7.1 常见问题诊断

#### 问题 1: pip check 报错

**症状**:
```
ERROR: pip's dependency resolver does not currently take into account all the packages that are installed...
```

**处理步骤**:
```bash
# 1. 检查具体冲突
pip check

# 2. 重新生成锁定文件
make lock-deps

# 3. 同步环境
pip-sync requirements/requirements.lock

# 4. 验证修复
pip check
```

#### 问题 2: CI 失败 - deps_guardian.yml

**症状**:
```
⚠️  base.lock 与 base.in 不一致，请执行 make lock-deps
```

**处理步骤**:
```bash
# 1. 检查差异
git diff requirements/base.in requirements/base.lock

# 2. 本地重新生成
make lock-deps

# 3. 提交更新
git add requirements/
git commit -m "fix(deps): sync lock files with in files"
```

#### 问题 3: 虚拟环境激活失败

**症状**:
```
ModuleNotFoundError: No module named 'redis'
```

**处理步骤**:
```bash
# 1. 检查环境
which python
python --version

# 2. 重新激活
source .venv/bin/activate

# 3. 重新安装
make install

# 4. 验证
python -c "import redis; print(redis.__version__)"
```

#### 问题 4: 依赖版本冲突

**症状**:
```
ERROR: Package 'package-a' requires 'package-b>=2.0', but you have 'package-b 1.9'...
```

**处理步骤**:
```bash
# 1. 查看依赖树
pip show package-b

# 2. 找出冲突方
pip depends package-a

# 3. 更新 .in 文件
vim requirements/base.in

# 4. 重新解析
make lock-deps
```

### 7.2 应急处理流程

#### 生产环境依赖问题

```bash
# 1. 快速回滚
git checkout previous-stable-tag
pip install -r requirements/base.lock

# 2. 问题定位
pip freeze > current-deps.txt
diff current-deps.txt requirements/base.lock

# 3. 修复后验证
make verify-deps
```

#### 大规模依赖更新

```bash
# 1. 创建分支
git checkout -b deps/major-update-$(date +%Y%m)

# 2. 更新核心依赖
vim requirements/base.in

# 3. 逐步更新锁定文件
make lock-deps

# 4. 全面测试
make test
make integration-test

# 5. 创建 PR
git push origin deps/major-update-$(date +%Y%m)
```

---

## 📚 8. 附录

### 8.1 依赖生命周期图

```
编辑阶段:
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│ 编辑 .in 文件│───▶│ make        │───▶│ 生成 .lock  │
│ 指定版本     │    │ lock-deps   │    │ 文件        │
└─────────────┘    └─────────────┘    └─────────────┘
                                             │
验证阶段:                                    ▼
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│ 提交到仓库   │───▶│ CI 自动验证  │◀───│ make        │
│ 触发 GitHub │    │ 阻止错误提交 │    │ verify-deps │
│ Actions     │    │             │    │             │
└─────────────┘    └─────────────┘    └─────────────┘
                                             │
使用阶段:                                    ▼
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│ 各环境安装   │◀───│ pip install │◀───│ .lock 文件   │
│ 确保一致性   │    │ -r lockfile │    │ 版本精确     │
└─────────────┘    └─────────────┘    └─────────────┘
```

### 8.2 Makefile 完整目标列表

```makefile
# 环境管理
make venv           # 创建虚拟环境
make install        # 安装依赖
make install-locked # 可重现安装
make clean-env      # 清理环境

# 依赖管理
make lock-deps      # 锁定依赖
make verify-deps    # 验证一致性
make check-deps     # 检查必需依赖

# 测试相关
make test-quick     # 快速测试
make test           # 完整测试
make coverage       # 覆盖率测试

# 代码质量
make fmt            # 格式化代码
make lint           # 代码检查
make type-check     # 类型检查
make prepush        # 提交前检查
```

### 8.3 命令速查表

| 场景 | 命令 | 说明 |
|------|------|------|
| **新环境** | `make install` | 安装所有依赖 |
| **添加包** | `echo "pkg==1.0" >> requirements/base.in && make lock-deps` | 添加新依赖 |
| **更新包** | `vim requirements/base.in && make lock-deps` | 更新版本 |
| **检查** | `make verify-deps` | 验证一致性 |
| **审计** | `pip-audit` | 安全检查 |
| **清理** | `make clean-env` | 重置环境 |
| **测试** | `make test-quick` | 运行测试 |

### 8.4 优秀实践示例

#### 语义化提交信息

```bash
chore(deps): add pytest-cov for coverage reporting
chore(deps): update fastapi from 0.104.0 to 0.104.1
fix(deps): resolve redis compatibility issue
chore(deps)!: upgrade python from 3.10 to 3.11  # 破坏性更新
```

#### 依赖分组管理

```ini
# requirements/base.in
# Core framework
fastapi==0.115.6
uvicorn[standard]==0.34.0

# Database
sqlalchemy==2.0.36
alembic==1.16.5

# Cache
redis==5.0.1
aioredis==2.0.1

# Authentication
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
```

### 8.5 故障恢复脚本

创建 `scripts/emergency_deps_recovery.sh`:

```bash
#!/usr/bin/env bash
set -e

echo "🚨 Emergency Dependency Recovery"
echo "================================"

# 1. 备份当前状态
pip freeze > emergency-backup-$(date +%Y%m%d-%H%M%S).txt

# 2. 清理环境
deactivate 2>/dev/null || true
rm -rf .venv

# 3. 重建环境
python -m venv .venv
source .venv/bin/activate

# 4. 安装基础工具
pip install --upgrade pip pip-tools

# 5. 重新生成所有锁定文件
make lock-deps

# 6. 安装依赖
make install

# 7. 验证
make verify-deps

echo "✅ Emergency recovery completed!"
```

---

## 🏁 9. 总结

### 9.1 成果回顾

通过实施本指南，我们已经实现了：

- ✅ **零依赖冲突**: 自动化防御机制确保依赖一致性
- ✅ **环境一致性**: 开发、测试、生产环境完全同步
- ✅ **安全防护**: 定期审计和 CVE 检测
- ✅ **流程标准化**: 清晰的更新和维护流程
- ✅ **自动化**: CI/CD 集成的自动验证

### 9.2 团队责任

1. **开发者**:
   - 遵循依赖添加流程
   - 提交前运行 `make verify-deps`
   - 及时处理 Dependabot PR

2. **维护者**:
   - 执行月度安全审计
   - 审核依赖更新请求
   - 维护文档更新

3. **架构师**:
   - 制定依赖策略
   - 评估新技术栈
   - 规划重大升级

### 9.3 持续改进

本指南是活文档，需要根据实际情况持续更新：
- 新工具的引入
- 流程的优化
- 经验的积累
- 反馈的收集

### 9.4 联系方式

如有问题或建议，请：
1. 创建 Issue 进行讨论
2. 在团队会议上提出
3. 直接联系维护团队

---

**记住：依赖管理不是一次性任务，而是持续的过程。让我们一起维护一个稳定、安全、高效的开发环境！** 🚀

---

*本文档最后更新：2025-01-04*
*下次审查日期：2025-04-04*
