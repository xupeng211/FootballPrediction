# 第二批次修复文件清单 (UNIT_BATCH2_FILES)

**选择时间**: 2025-09-30 16:10
**选择标准**: 包含语法错误的文件（跳过已修复文件）
**批次**: Phase 1 第二批次

## 📋 文件清单

| 序号 | 文件名 | 错误数 | 错误密度 | 修复优先级 |
|------|--------|--------|----------|------------|
| 1 | tests/unit/test_analyze_coverage_precise.py | 197 | 高 | 高 |
| 2 | tests/unit/test_scripts_cursor_runner.py | 2 | 低 | 中 |
| 3 | tests/unit/test_src_tasks_streaming_tasks.py | 2 | 低 | 中 |
| 4 | tests/unit/test_src_models_prediction_service.py | 2 | 低 | 中 |
| 5 | tests/unit/api/test_predictions_core.py | 待查 | 未知 | 中 |
| 6 | tests/unit/api/test_schemas.py | 待查 | 未知 | 中 |
| 7 | tests/unit/api/test_health_comprehensive.py | 待查 | 未知 | 中 |
| 8 | tests/unit/api/test_features_improved_simple.py | 待查 | 未知 | 中 |
| 9 | tests/unit/api/test_monitoring_comprehensive.py | 待查 | 未知 | 中 |
| 10 | tests/unit/api/test_features.py | 待查 | 未知 | 中 |
| 11 | tests/unit/api/test_features_comprehensive.py | 待查 | 未知 | 中 |
| 12 | tests/unit/api/test_predictions_comprehensive.py | 待查 | 未知 | 中 |
| 13 | tests/unit/api/test_api_monitoring.py | 待查 | 未知 | 中 |
| 14 | tests/unit/api/test_features_error_coverage.py | 待查 | 未知 | 中 |
| 15 | tests/unit/api/test_models_comprehensive.py | 待查 | 未知 | 中 |
| 16 | tests/unit/api/test_features_improved.py | 待查 | 未知 | 中 |
| 17 | tests/unit/api/test_api_predictions.py | 待查 | 未知 | 中 |
| 18 | tests/unit/api/test_buggy_api.py | 待查 | 未知 | 中 |
| 19 | tests/unit/api/test_api_data.py | 待查 | 未知 | 中 |
| 20 | tests/unit/api/test_models_extended.py | 待查 | 未知 | 中 |

## 📊 统计信息

- **文件总数**: 20 个
- **总错误数**: 待检查
- **平均错误数**: 待检查
- **错误范围**: 2 - 197 个

## 🎯 修复策略

### 保守修复模式
- **重点修复**: 括号不匹配、引号缺失、逗号缺失
- **禁用**: 复杂推断和大规模重写
- **工具**: scripts/fix_syntax_ast.py 保守模式

### 质量控制
- **每文件验证**: 修复后立即运行 ruff check 验证
- **批量验证**: 每修复5个文件运行完整测试
- **回滚机制**: 如果错误增加超过10%，回滚修复

## 📈 预期目标

- **错误减少目标**: ≥ 200 个错误
- **成功率目标**: ≥ 70% 文件显示错误减少
- **质量目标**: 不引入新的语法错误

---
**生成时间**: 2025-09-30 16:05
**下一步**: 开始保守模式修复
