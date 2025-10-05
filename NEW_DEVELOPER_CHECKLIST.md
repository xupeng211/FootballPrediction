# 新开发者检查清单

## ✅ 入门清单（首次进入项目）

### 📖 阅读文档（必读）
- [ ] [README.md](README.md) - 项目概述
- [ ] [TEST_RUN_GUIDE.md](TEST_RUN_GUIDE.md) - **⭐ 最重要：测试运行指南**
- [ ] [docs/QUICK_START_FOR_DEVELOPERS.md](docs/QUICK_START_FOR_DEVELOPERS.md) - 5分钟快速上手
- [ ] [CLAUDE.md](CLAUDE.md) - AI辅助开发指南

### 🛠️ 环境设置
```bash
# 1. 克隆项目
git clone <repository-url>
cd FootballPrediction

# 2. 安装依赖（会自动显示欢迎信息）
make install

# 3. 验证测试环境
make test-phase1
```

### 🧪 测试验证
- [ ] `make test-quick` 通过
- [ ] `make test-phase1` 通过
- [ ] 查看覆盖率报告：`open htmlcov/index.html`
- [ ] 理解**为什么不能**单独运行 `pytest tests/unit/api/test_xxx.py --cov=src`

## ⚠️ 重要提醒（请牢记）

1. **始终使用 Makefile 命令运行测试**
   ```bash
   ✅ make test-phase1
   ✅ make coverage
   ❌ pytest tests/unit/api/test_health.py --cov=src  # 绝对不要！
   ```

2. **理解 pytest.ini 配置**
   - 自动配置了 `--cov=src`
   - 自动排除 `tests/legacy`
   - 默认使用 `-m "not legacy"`

3. **测试标记系统**
   - `unit`: 单元测试
   - `integration`: 集成测试
   - `api`: API测试
   - `slow`: 慢速测试

## 📋 日常开发清单

### 编写新功能时
- [ ] 编写测试用例
- [ ] 使用 `make test-quick` 快速验证
- [ ] 提交前运行 `make prepush`
- [ ] 确保覆盖率不下降

### 修复 Bug 时
- [ ] 使用 `pytest --lf` 只运行失败的测试
- [ ] 使用 `pytest -x` 在第一个失败时停止
- [ ] 添加回归测试防止再次出现

## 🔍 故障排除

| 问题 | 解决方案 |
|------|----------|
| 测试失败 | `pytest -v -s --tb=long` |
| 覆盖率不显示 | 使用 `make coverage` 而不是单独 pytest |
| 依赖问题 | `make verify-deps` |
| 环境问题 | `make env-check` |

## 💡 进阶技巧

1. **并行测试**：`pytest -n auto`（需要 pytest-xdist）
2. **只运行修改的测试**：`pytest --testmon`（需要 pytest-testmon）
3. **覆盖率分析**：查看 `htmlcov/index.html` 中的红色部分
4. **性能分析**：`pytest --benchmark`（需要 pytest-benchmark）

## 🎯 成功标准

当你能回答以下问题时，说明已经掌握了项目的测试体系：

1. 为什么不应该单独运行 `pytest tests/unit/api/test_xxx.py --cov=src`？
2. Phase 1 的三个核心模块是什么？它们的覆盖率是多少？
3. 什么情况下应该使用 `make test-quick` 而不是 `make coverage`？
4. 如何查看哪些代码没有被测试覆盖？

## 📞 获取帮助

- 查看 `make help` 了解所有可用命令
- 阅读 [docs/TESTING_COMMANDS.md](docs/TESTING_COMMANDS.md)
- 在项目中提问前先运行 `make env-check`

---

> 💡 **记住**：测试是项目的生命线，正确运行测试是每个开发者的责任！
