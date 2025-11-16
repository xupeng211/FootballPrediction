# GitHub Issues 标准化执行指南

## 📋 Issues 分类体系

### 🚨 严重级别分类
- **Critical**: 阻塞项目运行的语法错误（invalid-syntax, F821等）
- **High**: 影响功能的代码质量问题（B904, E402等）
- **Medium**: 代码规范和最佳实践问题（N801, W293等）
- **Low**: 优化建议和非必要改进

### 🏷️ 问题类型分类
1. **语法修复类**: Syntax Fix
2. **代码质量类**: Code Quality
3. **测试改进类**: Test Improvement
4. **文档完善类**: Documentation
5. **性能优化类**: Performance

## 🎯 标准化Issue模板

### 语法修复类Issue模板

```markdown
## 🚨 语法修复任务: [错误类型]

### 📊 问题概述
- **错误代码**: [如F821, E999等]
- **影响文件**: [受影响的文件列表]
- **错误数量**: [具体数量]
- **严重级别**: Critical/High

### 🔧 执行步骤
1. **环境检查**
   ```bash
   source .venv/bin/activate
   ruff check [file_path] --output-format=concise
   ```

2. **错误定位**
   ```bash
   # 查看具体错误
   ruff check [file_path] --output-format=detailed
   # 或使用行号定位
   sed -n '[line_number]p' [file_path]
   ```

3. **修复工具**
   ```bash
   # 自动修复（如果支持）
   ruff check [file_path] --fix

   # 手动修复指南
   # 根据错误代码查阅: https://docs.astral.sh/ruff/rules/
   ```

4. **验证修复**
   ```bash
   # 重新检查该错误类型
   ruff check src/ --select=[error_code] | grep [file_path]

   # 运行相关测试
   pytest tests/unit/[related_tests] -v
   ```

### ✅ 完成标准
- [ ] 所有目标错误已修复
- [ ] 相关测试通过
- [ ] 无新增错误
- [ ] 代码可以正常导入

### 📚 参考资料
- [Ruff规则文档](https://docs.astral.sh/ruff/rules/)
- [Python语法指南](https://docs.python.org/3/reference/)
- [项目编码规范](./DEVELOPMENT_GUIDELINES.md)
```

### 代码质量类Issue模板

```markdown
## 🔍 代码质量改进: [问题类型]

### 📊 问题概述
- **质量指标**: [如代码复杂度、命名规范等]
- **影响范围**: [文件/模块范围]
- **当前状态**: [具体问题描述]
- **目标状态**: [期望达到的标准]

### 🛠️ 标准工具链
1. **检查工具**: `ruff check [file_path]`
2. **格式化工具**: `ruff format [file_path]`
3. **类型检查**: `mypy [file_path]`
4. **测试验证**: `pytest tests/unit/[related]`

### 📋 执行清单
- [ ] 运行质量检查确认问题
- [ ] 使用自动化工具修复（如可能）
- [ ] 手动修复剩余问题
- [ ] 运行完整测试套件
- [ ] 检查代码覆盖率影响

### 🎯 质量标准
- 代码符合PEP8规范
- 函数/变量命名清晰
- 类型注解完整
- 文档字符串齐全
- 测试覆盖率达标
```

### 测试改进类Issue模板

```markdown
## 🧪 测试改进任务: [测试类型]

### 📊 测试状态
- **当前覆盖率**: [具体百分比]
- **失败测试**: [数量和描述]
- **测试类型**: 单元/集成/端到端
- **目标模块**: [具体模块]

### 🔧 测试工具链
```bash
# 运行测试
pytest tests/[path] -v --cov=[module]

# 覆盖率报告
pytest tests/[path] --cov=[module] --cov-report=html

# 调试特定测试
pytest tests/[path]::test_name -v -s
```

### 📋 改进步骤
1. **分析失败原因**
   ```bash
   pytest tests/[path] --tb=short
   ```

2. **修复测试代码**
   - 更新测试用例
   - 修复断言逻辑
   - 完善Mock/Stub

3. **增强覆盖率**
   - 添加缺失的测试场景
   - 提高边界条件覆盖
   - 增加异常处理测试

4. **验证改进**
   ```bash
   pytest tests/[path] --cov=[module] --cov-fail-under=[target]
   ```

### ✅ 完成标准
- [ ] 所有测试通过
- [ ] 覆盖率达到目标
- [ ] 测试质量良好（无脆弱测试）
- [ ] 性能测试在时限内完成
```

## 🚀 标准执行流程

### Phase 1: 准备阶段
1. **领取任务**: 在Issue中评论 `@take-task`
2. **环境准备**: 确保开发环境就绪
3. **问题确认**: 运行检查工具确认问题存在

### Phase 2: 执行阶段
1. **创建分支**: `git checkout -b fix/issue-[number]`
2. **逐步修复**: 按照Issue模板步骤执行
3. **频繁验证**: 每个修复后立即验证
4. **进度更新**: 在Issue中报告进度

### Phase 3: 验证阶段
1. **本地测试**: 运行完整测试套件
2. **质量检查**: 确保无回归问题
3. **文档更新**: 如需要则更新文档

### Phase 4: 完成阶段
1. **提交代码**: `git commit -m "fix: resolve #issue-number"`
2. **创建PR**: 关联对应的Issue
3. **代码审查**: 等待团队审查
4. **合并部署**: 审查通过后合并

## 📊 进度追踪

### 每日进度模板
```markdown
## 📅 [日期] 进度报告

### ✅ 已完成任务
- #issue-number: [简要描述]

### 🔄 进行中任务
- #issue-number: [进度百分比]

### 🚧 遇到的阻碍
- [具体问题和需要的帮助]

### 📋 明日计划
- [计划处理的任务]
```

### 质量指标仪表板
- **语法错误数量**: [当前数量]
- **代码质量评分**: [A/B/C/D]
- **测试覆盖率**: [百分比]
- **Issues完成率**: [百分比]

## 🎯 质量标准

### 代码质量门槛
- ✅ 零语法错误 (invalid-syntax, F821)
- ✅ 零导入错误 (E402, F405)
- ✅ 基础代码规范 (N801, N806)
- ✅ 测试覆盖率 ≥ 30%

### 完成标准
- 所有检查工具通过
- 相关测试通过
- 代码审查通过
- 文档更新完整

---

*最后更新: 2025-11-05*
*维护者: Claude Code*
