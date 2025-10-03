# 测试工具快速参考卡 📋

## 🚀 快速开始

```bash
# 激活环境
source .venv/bin/activate

# 运行所有测试
make test

# 查看测试质量
make test.monitor
```

## 📊 核心命令

### 测试执行
| 命令 | 功能 | 用法 |
|------|------|------|
| `make test` | 运行所有测试 | 日常开发 |
| `make test.layered` | 分层测试 | CI/CD |
| `make test.unit` | 仅单元测试 | 快速验证 |
| `make test.quality-gate` | 质量门禁 | 提交前 |

### 质量监控
| 命令 | 功能 | 输出 |
|------|------|------|
| `make test.monitor` | 生成质量报告 | 终端+JSON |
| `make test.report` | 综合报告 | HTML+JSON+MD |
| `make test.dashboard` | 质量仪表板 | 静态HTML |

### 覆盖率优化
| 命令 | 功能 | 说明 |
|------|------|------|
| `make test.coverage-plan` | 优化计划 | 识别低覆盖模块 |
| `make test.cov` | 覆盖率报告 | 显示覆盖率详情 |

## 🛠️ 工具使用

### 1. 质量监控器
```bash
python tests/monitoring/test_quality_monitor.py
```
**输出**: 质量评分、覆盖率、性能指标

### 2. 覆盖率优化器
```bash
# 查看优化计划
python tests/monitoring/coverage_optimization.py --plan

# 生成测试模板
python tests/monitoring/coverage_optimization.py -m src.api.predictions
```

### 3. 质量仪表板
```bash
# 静态HTML
python tests/monitoring/quality_dashboard.py --static

# Web服务器
python tests/monitoring/quality_dashboard.py --serve --port 8080
```

### 4. 智能测试运行器
```bash
# 仅运行失败测试
python scripts/test_runner.py --failing-only

# 并行执行
python scripts/test_runner.py --parallel

# 质量检查
python scripts/test_runner.py --quality-gate
```

## 📈 质量指标

| 指标 | 目标 | 当前 |
|------|------|------|
| 质量评分 | 80+ | 4.5/5星 |
| 覆盖率 | 20%+ | ~8% |
| 稳定性 | 99%+ | 99.5% |
| 执行时间 | <60s | ~45s |

## 🔧 常用选项

### pytest
```bash
pytest -v                  # 详细输出
pytest -s                  # 显示print
pytest --tb=short          # 简短错误信息
pytest -x                  # 首次失败停止
pytest --lf                # 运行上次失败的
```

### 覆盖率
```bash
pytest --cov=src           # 生成覆盖率
pytest --cov-report=html    # HTML报告
pytest --cov-fail-under=20  # 覆盖率门禁
```

## 🐛 故障排除

### 常见问题
```bash
# ModuleNotFoundError
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

# Permission denied
chmod +x scripts/*.py
chmod +x tests/monitoring/*.py

# 端口占用
python tests/monitoring/quality_dashboard.py --serve --port 8081
```

### 调试技巧
```bash
# 调试模式
pytest --pdb

# 显示慢速测试
pytest --durations=10

# 运行特定测试
pytest tests/unit/api/test_cache.py::TestCacheAPI::test_cache_stats
```

## 📚 文档索引

- **完整说明书**: `docs/testing/TEST_TOOLS_USER_GUIDE.md`
- **测试策略**: `docs/testing/TEST_LAYERING_STRATEGY.md`
- **最佳实践**: `docs/testing/TESTING_BEST_PRACTICES_GUIDE.md`
- **优化总结**: `docs/TEST_OPTIMIZATION_COMPLETE.md`

## 💡 快速提示

1. **提交前检查**: `make test.quality-gate`
2. **查看质量**: `make test.monitor`
3. **提升覆盖**: `make test.coverage-plan`
4. **启动仪表板**: `make test.dashboard`

## 🆘 获取帮助

```bash
# 查看所有命令
make help

# pytest帮助
pytest --help

# 工具特定帮助
python scripts/test_runner.py --help
```

---
*快速参考 - 随时可用* 📖