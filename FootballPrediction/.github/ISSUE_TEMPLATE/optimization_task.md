---
name: 🚀 优化任务
about: 项目优化任务的标准化模板
title: "[OPT] "
labels: ["optimization", "enhancement"]
assignees: ''

---

## 🎯 任务描述

### 任务目标
<!-- 简洁明确地描述这个任务要达成的具体目标 -->

### 背景说明
<!-- 为什么需要这个优化？解决什么问题？ -->

---

## 📋 执行指南

### 🔧 必备工具
```bash
# 1. 环境检查
make env-check

# 2. 代码质量工具
make fix-code
make check-quality

# 3. 测试工具
make test.unit
make coverage

# 4. 性能测试工具
python3 scripts/performance_benchmark.py
```

### 📝 开发步骤
1. [ ] **准备工作**
   - [ ] 拉取最新代码: `git pull origin main`
   - [ ] 创建功能分支: `git checkout -b feat/task-name`
   - [ ] 运行环境检查: `make env-check`

2. [ ] **代码开发**
   - [ ] 按照CLAUDE.md规范编写代码
   - [ ] 运行代码质量检查: `make fix-code`
   - [ ] 编写/更新测试用例

3. [ ] **验证测试**
   - [ ] 运行单元测试: `make test.unit`
   - [ ] 检查测试覆盖率: `make coverage`
   - [ ] 运行性能测试（如适用）

4. [ ] **代码审查**
   - [ ] 自我检查代码质量
   - [ ] 确认所有检查通过
   - [ ] 更新相关文档

5. [ ] **提交代码**
   - [ ] 添加文件: `git add .`
   - [ ] 提交: `git commit -m "feat: 实现功能描述"`
   - [ ] 推送: `git push origin feat/task-name`
   - [ ] 创建Pull Request

---

## 🎨 实现规范

### 代码规范
- ✅ 遵循CLAUDE.md防呆约束
- ✅ 使用双引号、正确的冒号、逗号分隔import
- ✅ 添加类型注解
- ✅ 编写完整的docstring

### 测试规范
- ✅ 测试覆盖率 ≥ 目标值
- ✅ 测试用例命名清晰
- ✅ 包含边界条件和异常测试
- ✅ 使用适当的测试标记

### 文档规范
- ✅ 更新相关API文档
- ✅ 添加必要的注释
- ✅ 更新README（如需要）

---

## 📊 验收标准

### ✅ 功能验收
- [ ] 功能按需求实现
- [ ] 所有测试用例通过
- [ ] 代码质量检查100%通过

### ✅ 性能验收
- [ ] 响应时间 ≤ 目标值
- [ ] 内存使用合理
- [ ] 无明显性能瓶颈

### ✅ 质量验收
- [ ] 测试覆盖率 ≥ 目标值
- [ ] 无安全漏洞
- [ ] 代码规范符合要求

---

## 🔗 相关资源

### 📚 参考文档
- [项目优化路线图](../project-optimization-roadmap.md)
- [执行计划](../optimization-execution-plan.md)
- [质量策略](../quality-improvement-strategy.md)

### 🛠️ 有用脚本
- [快速优化脚本](../quick_optimize.sh)
- [覆盖率优化器](../scripts/coverage_optimizer.py)
- [性能基准测试](../scripts/performance_benchmark.py)

### 🔗 相关Issues
<!-- 如果有相关的Issues，在这里引用 -->

---

## 💡 实现提示

### 常见问题解决方案
1. **测试失败**: 运行 `make fix-code` 修复代码质量问题
2. **覆盖率不足**: 使用 `python3 scripts/coverage_optimizer.py` 分析未覆盖代码
3. **性能问题**: 使用 `python3 scripts/performance_benchmark.py` 进行基准测试

### 推荐工作流
```bash
# 开发循环
make fix-code          # 修复质量问题
make test.unit         # 运行测试
make coverage          # 检查覆盖率
git add . && git commit # 提交代码
```

### 🆘 获取帮助
- 查看项目文档: `cat CLAUDE.md`
- 运行帮助命令: `make help`
- 查看质量报告: `python3 scripts/generate_quality_report.py`

---

## 📝 备注

<!-- 任何额外的说明、注意事项或特殊要求 -->
