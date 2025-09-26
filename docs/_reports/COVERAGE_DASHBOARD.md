# 📊 Test Coverage Dashboard

生成时间: 2025-09-27 01:49:37

本仪表盘用于追踪项目测试覆盖率趋势和各模块差异。

## 1. 总体覆盖率

当前总覆盖率: **16.8%**

## 2. 模块覆盖率排名

### 🏆 Top 5 覆盖率最高模块

| 文件 | 覆盖率 | 缺失行数 |
|------|--------|----------|
| src/utils/__init__.py | 100.0% | 0 |
| src/tasks/__init__.py | 100.0% | 0 |
| src/streaming/__init__.py | 100.0% | 0 |
| src/services/__init__.py | 100.0% | 0 |
| src/monitoring/__init__.py | 100.0% | 0 |

### ⚠️ Bottom 5 覆盖率最低模块

| 文件 | 覆盖率 | 缺失行数 |
|------|--------|----------|
| scripts/alert_verification.py | 0.0% | 154 |
| scripts/analyze_dependencies.py | 0.0% | 58 |
| scripts/auto_ci_updater.py | 0.0% | 376 |
| scripts/ci_guardian.py | 0.0% | 299 |
| scripts/ci_issue_analyzer.py | 0.0% | 313 |

## 3. 按目录覆盖率统计

| 目录 | 文件数 | 总行数 | 覆盖率 | 缺失行数 |
|------|--------|--------|--------|----------|
| scripts | 26 | 1014 | 38.5% | 4582 |
| setup.py | 1 | 39 | 38.5% | 2 |
| src | 94 | 3666 | 38.5% | 7500 |

## 4. 改进建议

- 优先修复覆盖率最低的模块 (Bottom 5)
- 持续提升覆盖率，每周 +5% 为目标
- 新增代码必须 ≥80% 覆盖率 (CI 已守护)