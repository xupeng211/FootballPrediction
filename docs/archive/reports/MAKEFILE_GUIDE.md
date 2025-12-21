# 📖 Makefile 使用指南

本指南详细介绍AICultureKit项目中Makefile的所有命令和使用场景。

## 🎯 核心理念

Makefile将所有开发流程中的"细节规则"自动化，让你专注于编码而不是环境配置和质量检查。

## 🚀 快速开始

```bash
# 查看所有可用命令
make help

# 一键初始化开发环境
make init

# 快速开发环境准备
make dev

# 提交前完整检查
make prepush
```

## 📋 命令详解

### 🌐 环境管理

#### `make venv`
创建Python虚拟环境

```bash
make venv
```

**功能：**
- 在项目根目录创建`venv`虚拟环境
- 自动使用python3
- 幂等操作，重复执行安全

#### `make install`
安装项目依赖

```bash
make install
```

**功能：**
- 自动创建虚拟环境（如果不存在）
- 升级pip、setuptools、wheel到最新版本
- 安装requirements.txt中的所有依赖
- 适合首次设置和依赖更新

#### `make init`
初始化项目（首次使用）

```bash
make init
```

**功能：**
- 执行`make install`
- 运行`scripts/setup_project.py`创建基础文件结构
- 适合全新项目的初始化

#### `make clean`
清理环境和缓存

```bash
make clean
```

**功能：**
- 删除虚拟环境
- 清理所有Python缓存（__pycache__、*.pyc）
- 删除测试和工具缓存（.pytest_cache、.mypy_cache等）
- 清理构建产物

### 🔍 环境检查

#### `make env-check`
开发环境检查

```bash
make env-check
```

**功能：**
- 检查虚拟环境状态
- 验证依赖完整性
- 检查Git分支和同步状态
- 验证开发工具完整性
- 检查项目结构
- 提供详细的修复建议

#### `make context`
加载项目上下文

```bash
make context
```

**功能：**
- 扫描项目结构
- 分析Git历史
- 识别已有模块和测试
- 生成上下文快照到`logs/project_context.json`

#### `make status`
查看项目状态

```bash
make status
```

**输出信息：**
- 项目基本信息（名称、Python版本）
- 代码统计（文件数、行数）
- Git状态（分支、最近提交、未提交文件）
- 依赖状态（依赖文件、包数量）

### 🔧 代码质量

#### `make format`
代码格式化

```bash
make format
```

**功能：**
- 使用black格式化Python代码（line-length=88）
- 使用isort整理导入语句
- 自动修复格式问题

#### `make lint`
代码风格检查

```bash
make lint
```

**功能：**
- 使用flake8检查代码风格
- 最大行长度88字符
- 忽略E203、W503规则（与black兼容）

#### `make typecheck`
类型检查

```bash
make typecheck
```

**功能：**
- 使用mypy进行静态类型检查
- 忽略缺失的类型注解导入
- 如果mypy未安装则跳过

#### `make security`
安全检查

```bash
make security
```

**功能：**
- 使用bandit扫描安全漏洞
- 输出JSON格式报告
- 如果bandit未安装则跳过

#### `make complexity`
复杂度检查

```bash
make complexity
```

**功能：**
- 使用radon分析代码复杂度
- 显示每个函数的复杂度评分
- 如果radon未安装则跳过

### 🧪 测试

#### `make test`
运行单元测试

```bash
make test
```

**功能：**
- 使用pytest运行tests/目录下的所有测试
- 详细输出模式（-v）
- 简短回溯信息（--tb=short）
- 如果无测试文件则跳过

#### `make coverage`
运行覆盖率测试

```bash
make coverage
```

**功能：**
- 使用coverage + pytest运行测试
- 生成覆盖率报告
- 显示缺失覆盖的行号
- 如果coverage未安装则运行普通测试

#### `make test-watch`
监控模式运行测试

```bash
make test-watch
```

**功能：**
- 使用pytest-watch监控文件变化
- 自动重新运行测试
- 适合开发时持续测试

### ✅ 完整流程

#### `make quality`
完整质量检查

```bash
make quality
```

**执行顺序：**
1. 代码格式化（format）
2. 代码风格检查（lint）
3. 类型检查（typecheck）
4. 安全检查（security）
5. 复杂度检查（complexity）
6. 运行质量检查器脚本

#### `make ci`
本地CI模拟

```bash
make ci
```

**执行顺序：**
1. 环境检查（env-check）
2. 加载项目上下文（context）
3. 完整质量检查（quality）
4. 运行单元测试（test）
5. 运行覆盖率测试（coverage）

#### `make prepush`
提交前完整检查、推送和Issue同步

```bash
make prepush
```

**执行顺序：**
1. 运行完整CI检查（ci）
2. 检查Git工作区状态
3. 如果有更改：
   - 添加所有文件到暂存区
   - 创建自动提交（时间戳）
   - 推送到远程仓库
4. 自动同步ISSUES.md到远程仓库（sync）
5. 显示完成状态

#### `make prepush-with-message`
使用自定义消息的提交前检查

```bash
make prepush-with-message
```

**功能：**
- 与prepush相同，但允许输入自定义提交消息
- 交互式输入提交信息
- 完成后自动同步Issues

### 🎯 快捷方式

#### `make dev`
开发环境快速准备

```bash
make dev
```

**功能：**
- 安装依赖（install）
- 环境检查（env-check）
- 适合每日开发开始时使用

#### `make fix`
快速修复代码问题

```bash
make fix
```

**功能：**
- 代码格式化（format）
- 代码风格检查（lint）
- 快速修复常见问题

#### `make check`
快速质量检查

```bash
make check
```

**功能：**
- 完整质量检查（quality）
- 运行测试（test）
- 适合提交前快速验证

### 🚀 高级用法

#### `make cursor-run`
运行Cursor闭环系统

```bash
make cursor-run
```

**功能：**
- 交互式输入任务描述
- 运行完整的Cursor闭环流程
- 生成执行报告

#### `make sync`
同步ISSUES.md到远程仓库

```bash
make sync
```

**功能：**
- 读取项目根目录的ISSUES.md文件
- 根据GIT_PLATFORM环境变量选择平台（github/gitee）
- 使用对应的CLI工具（gh/tea）创建Issues
- 自动跳过注释行和空行
- 提供详细的执行反馈

**前置要求：**
```bash
# GitHub平台
export GIT_PLATFORM=github
brew install gh  # 或 apt install gh
gh auth login

# Gitee平台
export GIT_PLATFORM=gitee
# 下载安装 tea CLI from https://gitea.com/gitea/tea
tea login add
```

**ISSUES.md格式：**
```markdown
实现用户认证功能
添加数据导出功能
# 这是注释，会被跳过
修复移动端显示问题

优化数据库查询性能
```

#### `make sync-config`
配置Issue同步环境

```bash
make sync-config
```

**功能：**
- 显示详细的配置向导
- 提供平台选择指导
- 说明CLI工具安装方法
- 展示认证配置步骤
- 提供ISSUES.md格式示例

#### `make clean-logs`
清理日志文件

```bash
make clean-logs
```

**功能：**
- 清理logs/目录下的所有日志文件
- 包括*.log和*.json文件

## 📈 使用场景

### 🌅 每日开发流程

```bash
# 1. 开始开发
make dev

# 2. 编写代码...

# 3. 持续测试（可选）
make test-watch

# 4. 提交前检查
make prepush
```

### 🔧 代码问题修复

```bash
# 1. 快速修复格式问题
make fix

# 2. 完整质量检查
make quality

# 3. 运行测试确认
make test
```

### 🚀 CI/CD准备

```bash
# 1. 本地CI模拟
make ci

# 2. 如果通过，准备推送
make prepush-with-message
```

### 🆕 新团队成员入职

```bash
# 1. 项目初始化
make init

# 2. 查看项目状态
make status

# 3. 运行环境检查
make env-check
```

### 🧹 环境重置

```bash
# 1. 清理所有缓存
make clean

# 2. 重新安装
make install

# 3. 验证环境
make env-check
```

## 🎨 自定义和扩展

### 环境变量配置

```bash
# 设置更严格的质量标准
export TEST_COVERAGE_MIN=90
export MAX_COMPLEXITY=8

# 使用自定义目录
export BACKUP_DIR="backup/$(date +%Y%m%d)"
```

### 修改Makefile变量

编辑项目根目录的`Makefile`：

```makefile
# 自定义Python版本
PYTHON := python3.11

# 自定义虚拟环境目录
VENV := .venv

# 自定义项目名称
PROJECT_NAME := MyProject
```

## 🚨 故障排除

### 常见问题

1. **虚拟环境激活失败**
   ```bash
   # 检查shell类型
   echo $SHELL

   # 手动激活测试
   . venv/bin/activate
   ```

2. **依赖安装失败**
   ```bash
   # 清理缓存重试
   make clean
   make install
   ```

3. **测试失败**
   ```bash
   # 查看详细错误
   make test

   # 检查测试文件
   ls -la tests/
   ```

### 调试技巧

```bash
# 查看make命令执行过程
make -n prepush

# 启用详细输出
make V=1 install

# 检查Makefile语法
make -p | grep "^[a-zA-Z]"
```

## 💡 最佳实践

1. **使用prepush进行提交**
   - 确保代码质量
   - 避免CI失败
   - 保持团队代码一致性

2. **定期运行env-check**
   - 及时发现环境问题
   - 保持开发环境健康

3. **利用快捷方式**
   - `make dev` 开始开发
   - `make fix` 快速修复
   - `make check` 快速验证

4. **监控项目状态**
   - `make status` 了解项目概况
   - `make context` 分析项目结构

---

**💡 提示：** 所有命令都设计为幂等操作，可以安全地重复执行。如果遇到问题，运行`make clean && make install`重置环境。

## 🛡️ 失败保护机制

### 核心概念

AICultureKit的Makefile采用**分层失败保护机制**：

```
make prepush
    ↓
CI检查 (env-check + context + quality + test + coverage)
    ↓ (如果失败 → 自动停止)
Git推送 (add + commit + push)
    ↓
Issues同步 (sync)
    ↓
完成报告
```

**关键特性：**
- ✅ **零容忍半成品**：任何检查失败都会阻止推送
- ✅ **智能错误提示**：每种失败都有具体的修复建议
- ✅ **防护远程仓库**：确保推送的代码都是高质量的
- ✅ **完整性保证**：Issues同步只在代码成功推送后进行

### 失败检测点

#### 1. 环境检查失败
```bash
make env-check
# 如果失败：
❌ 环境检查失败
   请根据上述建议修复环境问题
```

**常见问题：**
- 虚拟环境未激活
- 依赖包缺失
- 在错误的Git分支（如main/master）
- Git仓库未初始化

#### 2. 代码质量检查失败
```bash
make quality
# 如果失败：
❌ 质量检查失败
   请修复代码质量问题后重试
```

**常见问题：**
- 代码格式不规范
- Lint规则违反
- 类型检查错误
- 安全漏洞
- 代码复杂度过高

#### 3. 测试失败
```bash
make test
# 如果失败：
❌ 单元测试失败
   请修复失败的测试后重试
```

**常见问题：**
- 测试用例失败
- 测试覆盖率不足
- 测试环境问题

### 修复建议系统

每种失败都提供针对性的修复建议：

```bash
💡 快速修复建议:
   - 代码格式问题: make fix
   - 测试失败: make test
   - 环境问题: make env-check
```

### 示例：完整的失败保护演示

```bash
# 1. 创建问题代码（演示用）
echo "def bad_function( x,y ):" > src/bad_code.py
echo "  return x+y" >> src/bad_code.py

# 2. 运行prepush
make prepush

# 结果：
>>> 开始prepush流程（包含失败保护机制）...
>>> 第1步: 执行CI检查...
>>> 代码格式化...
>>> 代码风格检查...
src/bad_code.py:1:18: E201 whitespace after '('
src/bad_code.py:1:21: E202 whitespace before ')'
❌ 质量检查失败
❌ CI检查失败，停止推送流程
💡 快速修复建议:
   - 代码格式问题: make fix

# 3. 修复问题
make fix

# 4. 重新运行
make prepush
# 现在会成功通过所有检查并推送
```

### 高级配置

#### 自定义失败阈值

```bash
# 设置更严格的测试覆盖率要求
export MIN_COVERAGE=90

# 设置更严格的复杂度限制
export MAX_COMPLEXITY=5

make prepush
```

#### 调试失败

```bash
# 单独运行各个检查，定位问题
make env-check    # 环境问题
make quality      # 代码质量问题
make test         # 测试问题
make ci           # 完整CI检查
```
