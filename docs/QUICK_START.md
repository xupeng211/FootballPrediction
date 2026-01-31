# 🚀 快速开始指南

本指南展示如何在5分钟内设置并使用AICultureKit Cursor闭环系统。

## 📋 第一步：环境检查

```bash
# 运行环境检查器，查看当前状态
python scripts/env_checker.py --summary --fix-suggestions
```

**示例输出：**
```
⚠️ 开发环境存在问题，请根据建议修复

🔧 修复建议:
   1. 运行: python -m venv venv && source venv/bin/activate
   2. 运行: pip install -r requirements.txt
   3. 确保当前目录是Git仓库
   4. 安装缺失工具: pip install radon
```

## 🔧 第二步：按建议修复环境

### 1. 创建和激活虚拟环境

```bash
# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
source venv/bin/activate  # Linux/Mac
# 或
venv\Scripts\activate     # Windows
```

### 2. 安装项目依赖

```bash
# 安装所有依赖
pip install -r requirements.txt
```

### 3. 初始化Git仓库

```bash
# 初始化Git仓库
git init

# 添加所有文件
git add .

# 创建初始提交
git commit -m "feat: 初始化AICultureKit闭环系统"

# 创建功能分支
git checkout -b feature/demo-task
```

### 4. 验证环境修复

```bash
# 再次运行环境检查
python scripts/env_checker.py --summary
```

**期望输出：**
```
🎉 开发环境检查全部通过！

📊 环境检查摘要:
   ✅ 虚拟环境检查: 虚拟环境已激活
   ✅ 依赖完整性检查: 所有依赖已安装 (25个包)
   ✅ Git分支检查: 当前在功能分支 'feature/demo-task'
   ✅ Git同步状态检查: Git工作区干净，与远程同步
   ✅ 开发工具检查: 所有开发工具已安装 (6个)
   ✅ 项目结构检查: 项目结构完整
```

## 🎯 第三步：使用Cursor闭环系统

### 方法1：完整自动化闭环

```bash
# 运行完整闭环，包含所有细节规则检查
python scripts/cursor_runner.py --task "实现用户认证模块" --summary
```

### 方法2：在Cursor中使用提示词

将以下完整提示词复制到Cursor：

```
TASK: 实现简单的用户数据模型

CONTEXT:
- 项目目录: AICultureKit
- 当前分支: feature/demo-task
- 已存在模块: src/core, src/models, src/services, src/utils
- 依赖关系: 见requirements.txt

细节规则执行（强制要求）：
1. 🚀 任务启动前检查：
   - ✅ 虚拟环境已激活
   - ✅ 依赖完整性已验证
   - ✅ 当前在feature分支
   - ✅ 代码已同步
   - ✅ 开发工具已就绪

2. 📋 开发准备：
   - 备份要修改的文件到backup/目录
   - 分析src/models/目录结构
   - 检查是否可复用现有代码

3. 💻 开发过程：
   - 创建 src/models/user.py
   - 添加类型注解
   - 实现数据验证
   - 添加异常处理
   - 创建对应测试 tests/test_user.py

4. 🔍 质量检查：
   - 运行 black 格式化
   - 运行 flake8 检查
   - 运行 pytest 测试
   - 确保覆盖率 >= 80%
   - 检查复杂度 <= 10

5. 🚀 提交：
   - 小粒度commit
   - 规范commit message
   - 更新相关文档

请严格按照上述细节规则执行，确保每个步骤都完成。
```

## 🎮 第四步：实战演示

让我们创建一个简单的用户模型来演示完整流程：

### 1. 运行环境检查

```bash
python scripts/env_checker.py --summary
```

### 2. 加载项目上下文

```bash
python scripts/context_loader.py --summary
```

### 3. 在Cursor中执行任务

使用上面的提示词，让Cursor自动：
- 创建用户模型类
- 添加数据验证
- 编写单元测试
- 运行质量检查
- 提交代码

### 4. 验证结果

```bash
# 检查生成的文件
ls -la src/models/
ls -la tests/

# 运行测试
python -m pytest tests/ -v

# 检查代码质量
python scripts/quality_checker.py --summary
```

## ✨ 第五步：高级用法

### 自定义环境变量

```bash
# 设置更严格的质量标准
export TEST_COVERAGE_MIN=90
export MAX_COMPLEXITY=8

# 使用自定义目录
export BACKUP_DIR="backup/$(date +%Y%m%d)"
```

### 团队协作模式

```bash
# 同步最新代码
git pull origin main

# 重新检查环境
python scripts/env_checker.py --summary

# 执行开发任务
python scripts/cursor_runner.py --task "修复用户登录bug" --summary

# 准备代码审查
python scripts/quality_checker.py --summary
git log --oneline -5
```

### 持续集成预演

```bash
# 模拟完整CI流程
python scripts/env_checker.py &&
python scripts/context_loader.py &&
python scripts/quality_checker.py &&
echo "✅ CI预演通过！"
```

## 🎯 最佳实践

### 1. 每日开发流程

```bash
# 1. 激活环境
source venv/bin/activate

# 2. 环境检查
python scripts/env_checker.py --summary

# 3. 同步代码
git pull origin main

# 4. 创建功能分支
git checkout -b feature/new-feature

# 5. 开始开发（使用Cursor）
# 6. 质量检查
python scripts/quality_checker.py --summary

# 7. 提交代码
git add .
git commit -m "feat: 实现新功能"
git push origin feature/new-feature
```

### 2. 问题排查

```bash
# 查看详细错误信息
python scripts/env_checker.py --fix-suggestions
cat logs/quality_check.json | jq '.checks'
cat logs/iteration.log | tail -20
```

### 3. 性能优化

```bash
# 分析代码复杂度
python -m radon cc src/ --show-complexity

# 检查测试覆盖率
python -m coverage run -m pytest
python -m coverage report --show-missing

# 代码格式化
python -m black src/ tests/ scripts/
```

## 🎉 完成！

现在你已经掌握了AICultureKit Cursor闭环系统的使用方法。

**关键要点：**
- ✅ 始终从环境检查开始
- ✅ 严格执行细节规则
- ✅ 保持代码质量标准
- ✅ 使用小粒度提交
- ✅ 定期同步和检查

**下一步：**
- 查看 `docs/USAGE_EXAMPLES.md` 了解更多场景
- 自定义 `rules.md` 适应你的项目需求
- 在实际项目中应用闭环系统

---

**💡 提示：** 如果遇到问题，运行 `python scripts/env_checker.py --fix-suggestions` 获取具体的修复建议。
