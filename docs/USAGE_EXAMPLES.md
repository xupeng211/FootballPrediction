# 📖 使用示例

本文档展示如何使用 FootballPrediction Cursor 闭环开发系统来完成各种开发任务。

## 🎯 基础使用流程

### 1. 环境初始化

```bash
# 项目初始化（仅首次使用）
python scripts/setup_project.py

# 验证环境
python scripts/context_loader.py --summary
python scripts/quality_checker.py --summary
```

### 2. 在Cursor中使用完整提示词

将以下内容复制到Cursor中，替换具体的任务描述：

```
TASK: 实现用户认证系统，包含登录、注册、密码重置功能

CONTEXT:
- 项目目录: /home/user/projects/FootballPrediction
- 当前分支: main
- 已存在模块: src/core, src/models, src/services, src/utils
- 最近提交: 初始化项目结构
- 已有测试: tests/test_example.py
- 依赖关系: 见requirements.txt

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

INSTRUCTIONS:
1. 🔍 加载项目上下文：
   - 运行 python scripts/context_loader.py
   - 分析目录结构和已有模块
   - 检查Git最近提交历史
   - 识别已有测试和依赖

2. 📋 应用规则：
   - 备份即将修改的文件到backup/目录
   - 严格遵守rules.md中的所有规范

3. 🎯 拆解任务：
   - 将用户认证系统分解为：
     * 用户数据模型 (src/models/user.py)
     * 认证服务 (src/services/auth.py)
     * 密码工具 (src/utils/password.py)
     * 对应的单元测试

4. 🔨 生成代码：
   - 创建用户模型，包含字段验证
   - 实现认证服务，包含登录/注册/重置密码
   - 添加密码加密和验证工具
   - 为每个模块编写完整的单元测试

5. ✅ 执行检查点：
   - 运行 python scripts/quality_checker.py
   - 确保所有检查通过

6. 🚀 完成提交：
   - git add .
   - git commit -m "feat(auth): 实现用户认证系统"
   - 记录到 logs/iteration.log

请严格按照上述流程执行，确保代码质量和测试覆盖率达标。
```

## 🔧 高级使用场景

### 场景1：实现数据分析模块

```bash
# 1. 设置任务环境变量
export TASK="实现用户行为数据分析模块"
export TEST_COVERAGE_MIN=90
export MAX_COMPLEXITY=8

# 2. 运行完整闭环
python scripts/cursor_runner.py --task "$TASK" --summary

# 3. 查看执行结果
cat logs/cursor_execution.json | jq '.phases'
```

**Cursor提示词模板：**

```
TASK: 实现用户行为数据分析模块

请按照闭环开发流程实现以下功能：

核心功能：
- 用户访问日志分析
- 行为模式识别
- 数据可视化报告
- 异常行为检测

技术要求：
- 使用pandas进行数据处理
- 实现可配置的分析规则
- 提供REST API接口
- 90%以上测试覆盖率
- 代码复杂度≤8

实现步骤：
1. 加载项目上下文，分析现有结构
2. 设计数据模型 (src/models/analytics.py)
3. 实现分析服务 (src/services/analytics.py)
4. 创建API接口 (src/core/api.py)
5. 编写完整测试套件
6. 运行质量检查，确保所有指标达标
7. 提交代码并记录日志
```

### 场景2：重构现有代码

```bash
# 使用Cursor重构提示词
```

**Cursor重构提示词：**

```
TASK: 重构用户服务模块，提升代码质量和性能

重构目标：
- 降低函数复杂度（目标≤6）
- 提升测试覆盖率至95%
- 优化数据库查询性能
- 改善错误处理机制

重构流程：
1. 运行 python scripts/context_loader.py 分析现状
2. 识别高复杂度函数和低覆盖率代码
3. 制定重构计划，分步骤执行
4. 每次重构后运行质量检查
5. 确保所有现有测试仍然通过
6. 添加必要的新测试用例
7. 性能基准测试对比

请严格遵循：
- 不改变现有API接口
- 保持向后兼容性
- 每个重构步骤独立提交
- 详细记录重构理由和效果
```

### 场景3：修复Bug并添加测试

```bash
# Bug修复场景
```

**Cursor Bug修复提示词：**

```
TASK: 修复登录模块的并发访问问题

问题描述：
- 多用户同时登录时出现数据竞争
- 偶现的session冲突错误
- 用户状态更新不一致

修复流程：
1. 加载项目上下文，定位相关代码
2. 分析并发问题的根本原因
3. 设计线程安全的解决方案
4. 实现修复代码
5. 编写并发测试用例
6. 运行压力测试验证修复效果
7. 更新相关文档
8. 提交修复并记录详细日志

质量要求：
- 修复后的代码必须通过所有测试
- 新增的并发测试用例覆盖率100%
- 性能不能显著下降
- 代码复杂度控制在合理范围
```

## 📊 监控和调试

### 查看执行状态

```bash
# 查看项目整体状态
python scripts/context_loader.py --summary

# 查看最近的质量检查结果
python scripts/quality_checker.py --summary

# 查看完整的闭环执行日志
python scripts/cursor_runner.py --task "状态检查" --summary
```

### 分析日志文件

```bash
# 查看项目统计信息
jq '.project_stats' logs/project_context.json

# 查看质量检查详情
jq '.checks | to_entries[] | {name: .value.name, success: .value.success}' logs/quality_check.json

# 查看迭代历史
tail -20 logs/iteration.log

# 查看最近的闭环执行
jq '.phases | to_entries[] | {name: .value.name, success: .value.success, message: .value.message}' logs/cursor_execution.json
```

### 性能优化建议

```bash
# 1. 代码复杂度分析
python -m radon cc src/ --show-complexity

# 2. 测试覆盖率报告
python -m coverage run -m pytest tests/
python -m coverage report --show-missing

# 3. 内存和性能分析
python -m cProfile -o profile.stats your_script.py
python -c "import pstats; p=pstats.Stats('profile.stats'); p.sort_stats('cumulative').print_stats(10)"
```

## 🎨 自定义配置示例

### 环境配置文件 (.env)

```bash
# 代码质量阈值
CODE_QUALITY_THRESHOLD=85
TEST_COVERAGE_MIN=90
MAX_COMPLEXITY=8

# 自定义目录
BACKUP_DIR=backup/custom
LOG_FILE=logs/custom_iteration.log

# 开发模式
DEBUG=true
VERBOSE=true
AUTO_FIX=true
```

### 项目特定规则 (rules.md 扩展)

```markdown
## 项目特定规则

### 数据库操作
- 所有数据库操作必须使用事务
- 查询必须有超时设置
- 批量操作需要进度报告

### API设计
- 所有API返回统一格式
- 必须包含请求ID用于追踪
- 错误码必须标准化

### 安全要求
- 敏感数据必须加密存储
- 所有输入必须验证和清理
- 日志中不能包含敏感信息
```

## 🚀 高效开发技巧

### 1. 快速原型开发

```bash
# 使用Cursor快速生成原型
```

**原型开发提示词：**

```
TASK: 快速开发内容推荐系统原型

原型要求：
- 30分钟内完成核心功能
- 基础的推荐算法实现
- 简单的API接口
- 基本的单元测试

开发策略：
- 先实现最小可行版本
- 使用现有的工具库
- 简化数据模型
- 快速迭代验证
```

### 2. 增量开发

```bash
# 分阶段实现复杂功能
```

**增量开发提示词：**

```
TASK: 分阶段实现完整的内容管理系统

第一阶段（当前）：
- 基础的CRUD操作
- 简单的权限控制
- 基本测试覆盖

后续阶段计划：
- 高级搜索功能
- 批量操作
- 审计日志
- 性能优化

请专注实现第一阶段，为后续扩展预留接口。
```

### 3. 代码审查准备

```bash
# 准备代码审查
python scripts/quality_checker.py --summary
git log --oneline -10
git diff --stat HEAD~5
```

## 🤝 团队协作最佳实践

### 1. 分支管理

```bash
# 创建功能分支
git checkout -b feature/user-analytics
export TASK="实现用户行为分析功能"
python scripts/cursor_runner.py --task "$TASK"

# 提交前检查
python scripts/quality_checker.py --summary
git add .
git commit -m "feat(analytics): 实现用户行为分析基础功能"
```

### 2. 代码同步

```bash
# 同步最新代码
git pull origin main
python scripts/context_loader.py --summary  # 重新加载上下文

# 解决冲突后重新检查
python scripts/quality_checker.py --summary
```

---

**💡 提示：** 这些示例展示了Cursor闭环系统在各种开发场景中的应用。根据具体项目需求，可以调整和定制相应的流程。
