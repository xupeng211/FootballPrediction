# ⚡ 质量工具快速参考指南

**版本**: v2.0 | **更新**: 2025-10-24

## 🚀 日常命令速查

### 环境检查
```bash
make context          # 加载项目上下文 ⭐
make env-check        # 检查环境健康状态
make help             # 查看所有命令
```

### 质量检查
```bash
make lint             # Ruff + MyPy 检查
make fmt              # 代码格式化
make test             # 运行测试
make coverage         # 查看覆盖率
make prepush          # 预推送验证 ⭐
```

### 智能工具
```bash
# 全面质量检查
python scripts/quality_guardian.py --check-only

# 自动修复问题
python scripts/smart_quality_fixer.py

# 优化质量标准
python scripts/quality_standards_optimizer.py --report-only
```

## 📊 质量状态速查

### 当前质量标准 (v2.0)
- **测试覆盖率**: ≥ 15% (目标: 25%)
- **Ruff错误**: ≤ 10个
- **MyPy错误**: ≤ 1500个 (分阶段改进)
- **安全漏洞**: 高危=0, 中危≤2

### 质量分数等级
- 🟢 **9-10分**: 优秀
- 🟡 **7-8分**: 良好
- 🟠 **5-6分**: 一般
- 🔴 **0-4分**: 需要改进

## 🚨 常见问题快速解决

### MyPy错误过多
```bash
# 1. 智能修复
python scripts/smart_quality_fixer.py --mypy-only

# 2. 批量修复
python scripts/batch_mypy_fixer.py --target src/api

# 3. 调整标准 (如需要)
python scripts/quality_standards_optimizer.py --update-scripts
```

### 覆盖率不足
```bash
# 1. 查看覆盖率详情
make coverage

# 2. 针对特定模块
make coverage-targeted MODULE=src/api

# 3. 运行覆盖率改进
python scripts/coverage_improver.py
```

### CI构建失败
```bash
# 1. 本地重现
./ci-verify.sh

# 2. 全面修复
python scripts/quality_guardian.py

# 3. 验证修复
make ci
```

## 📋 开发流程清单

### 开始开发前
- [ ] `make context` - 加载项目上下文
- [ ] `make env-check` - 检查环境
- [ ] `git pull` - 拉取最新代码

### 开发过程中
- [ ] 定期运行 `make lint`
- [ ] 及时运行 `make fmt`
- [ ] 相关测试 `make test-phase1`

### 提交代码前
- [ ] `make prepush` - 完整验证 ⭐
- [ ] 确保质量分数达标
- [ ] 推送代码 `git push`

## 🎯 质量目标追踪

### 个人质量目标
- 每日提交: 质量分数 ≥ 7分
- 每周目标: 覆盖率提升 2-3%
- 每月目标: MyPy错误减少 20%

### 团队质量目标
- CI成功率: ≥ 90%
- 平均覆盖率: ≥ 25%
- 代码质量: ≥ 8分

## 📞 快速帮助

### 工具问题
```bash
# 查看工具帮助
python scripts/quality_guardian.py --help
python scripts/smart_quality_fixer.py --help
python scripts/quality_standards_optimizer.py --help
```

### 质量报告
```bash
# 查看最新质量报告
cat quality-reports/quality_report_*.json

# 查看修复报告
cat smart_quality_fix_report.json
```

### 团队支持
- 📧 技术问题: 提交GitHub Issue
- 💬 流程问题: 联系DevOps团队
- 📚 文档问题: 更新相关文档

---

**⭐ 记住**: `make prepush` 是提交前的最后一道防线！

**💡 提示**: 遇到问题时，首先运行 `python scripts/quality_guardian.py --check-only` 获取详细诊断。

---
*快速参考指南 | 团队质量工具套件*
