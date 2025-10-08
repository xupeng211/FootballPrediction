# 🧠 Cursor 闭环系统提示词

## 📋 任务配置

```
TASK: {task_description}

CONTEXT:
- 项目目录: {project_root}
- 当前分支: {current_branch}
- 已存在模块: {existing_modules}
- 最近提交: {recent_commits}
- 已有测试: {existing_tests}
- 依赖关系: {dependencies}
```

## ⚖️ 核心规则

```
RULES:
- 禁止随意创建新文件，除非任务明确
- 修改已有文件前自动备份
- 每个新功能必须写单元测试
- 小功能小 commit，描述明确
- 遵守项目已有代码风格
- 优先复用已有函数/模块
- 必须处理异常和边界情况
- 写日志便于排查错误
- 每次生成代码前加载项目上下文
- lint & test 必须通过才能提交
```

## 🔄 执行指令

```
INSTRUCTIONS:
1. 🚀 任务启动前（细节规则执行）：
   - **激活虚拟环境**: `source venv/bin/activate` 或 `conda activate <env>`
   - **确认依赖完整**: 检查requirements.txt中所有包已正确安装
   - **切换feature分支**: 避免直接在main/master分支开发
   - **拉取最新代码**: `git pull origin main` 确保代码同步
   - **加载项目上下文**: 运行 `python scripts/context_loader.py`
   - **验证开发环境**: 确认所有工具链完整可用

2. 📋 开发准备阶段：
   - **自动备份文件**: 将要修改的文件备份到backup/目录
   - **分析现有结构**: 了解相关模块和依赖关系
   - **检查代码复用**: 识别可复用的现有函数/模块
   - **合理拆解任务**: 将大任务分解为可独立测试的小模块
   - **严格遵守规范**: 应用rules.md中的所有开发规则

3. 💻 开发过程中（逐步执行）：
   - **模块化设计**: 按照清晰的职责分离原则编写代码
   - **即时添加测试**: 每个新功能立即编写对应单元测试
   - **完整类型注解**: 为所有函数添加类型提示
   - **异常处理机制**: 考虑边界条件、错误场景和资源释放
   - **结构化日志**: 添加便于调试和监控的日志记录
   - **安全边界检查**: 网络请求、文件操作、数据库连接的安全验证
   - **即时代码格式化**: 使用black自动格式化新增代码

4. 🔍 开发完成后（自动化检查）：
   - **代码格式化**: `black src/ tests/ scripts/`
   - **风格检查**: `flake8 src/ tests/ scripts/`
   - **类型检查**: `mypy src/`
   - **单元测试**: `pytest tests/ -v`
   - **覆盖率分析**: `coverage run -m pytest && coverage report`
   - **复杂度检查**: `radon cc src/`
   - **安全扫描**: `bandit -r src/`

5. 🔧 自动修复机制：
   - **智能问题识别**: 分析检查失败的具体原因
   - **自动修复尝试**: 修复可自动处理的问题（格式、导入顺序等）
   - **迭代日志记录**: 每次修复尝试都记录到logs/iteration.log
   - **重试直至成功**: 最多重试3次，确保本地绿灯
   - **详细错误报告**: 无法自动修复的问题提供具体指导

6. 🚀 提交准备前（协作友好）：
   - **本地CI预演**: 模拟完整CI流程确保远程通过
   - **小粒度commit**: 只包含当前任务的相关改动
   - **规范commit message**: 遵循conventional commits格式
   - **文档同步更新**: 更新README、API文档等相关文档
   - **避免冲突**: 推送前再次同步远程代码
   - **功能分支独立**: 确保不混合多个功能改动

7. 📊 质量保证原则：
   - **代码质量**: 所有检查点必须通过
   - **可维护性**: 代码清晰、注释完整、结构合理
   - **协作友好**: 考虑团队成员的理解成本
   - **详细记录**: 生成完整的执行和修复报告

8. 🌿 最终验证：
   - **环境一致性**: 确保在不同环境下都能正常运行
   - **向后兼容**: 不破坏现有功能和API接口
   - **性能影响**: 新代码不显著影响系统性能
   - **安全合规**: 满足项目安全和合规要求
```

## 🎨 使用模板

### 基础使用

```bash
# 设置任务描述
TASK="实现用户认证模块，包含登录、注册、密码重置功能"

# 加载项目上下文
PROJECT_ROOT=$(pwd)
CURRENT_BRANCH=$(git branch --show-current)
EXISTING_MODULES=$(find src/ -name "*.py" | head -10)
RECENT_COMMITS=$(git log --oneline -5)
EXISTING_TESTS=$(find tests/ -name "*.py" | head -10)
DEPENDENCIES=$(cat requirements.txt 2>/dev/null || echo "未找到requirements.txt")

# 执行闭环开发
echo "开始执行Cursor闭环开发流程..."
```

### 高级配置

```bash
# 自定义检查规则
export CODE_QUALITY_THRESHOLD=80
export TEST_COVERAGE_MIN=85
export MAX_COMPLEXITY=10

# 自定义输出目录
export BACKUP_DIR="backup/$(date +%Y%m%d_%H%M%S)"
export LOG_FILE="logs/iteration_$(date +%Y%m%d).log"
```

## 📝 执行日志模板

```json
{
  "timestamp": "2024-01-20T10:30:00Z",
  "task": "实现用户认证模块",
  "phase": "代码生成",
  "status": "成功",
  "details": {
    "files_created": ["src/auth/login.py", "tests/test_login.py"],
    "files_modified": ["src/__init__.py"],
    "backup_location": "backup/20240120_103000/",
    "test_coverage": "92%",
    "complexity_score": "7.2",
    "commit_hash": "abc123def"
  },
  "next_steps": ["实现密码重置功能", "添加集成测试"]
}
```

## 🚨 错误处理

### 常见错误及解决方案

1. **测试失败**

   ```bash
   错误: pytest失败
   解决: 分析失败用例，修复代码逻辑，重新运行测试
   ```

2. **代码风格问题**

   ```bash
   错误: flake8检查失败
   解决: 运行black格式化，修复剩余风格问题
   ```

3. **依赖冲突**

   ```bash
   错误: 包导入失败
   解决: 检查requirements.txt，更新依赖版本
   ```

4. **Git推送失败**

   ```bash
   错误: 推送被拒绝
   解决: 拉取最新代码，解决冲突，重新推送
   ```

## 🎯 成功标准

- ✅ 所有检查点通过
- ✅ 测试覆盖率 >= 80%
- ✅ 代码复杂度 <= 10
- ✅ 无代码风格问题
- ✅ Git提交成功
- ✅ 日志记录完整

## 📚 相关文件

- `rules.md` - 详细开发规则
- `scripts/context_loader.py` - 项目上下文加载器
- `scripts/quality_checker.py` - 代码质量检查器
- `logs/iteration.log` - 开发迭代日志
