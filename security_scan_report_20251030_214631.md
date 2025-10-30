
# 安全扫描报告
# Security Scan Report

**扫描时间**: 2025-10-30T21:46:30.675622
**项目根目录**: /home/user/projects/FootballPrediction

## 📊 扫描结果摘要

### Bandit安全扫描
- **状态**: ❌ 失败
- **发现问题**: 0 个

### 依赖漏洞扫描 (pip-audit)
- **状态**: ❌ 失败
- **发现漏洞**: 0 个

### 文件权限检查
- **发现问题**: 0 个

## 🔍 详细结果

### Bandit扫描结果
❌ 扫描失败: bandit扫描失败: Command '['/home/user/projects/FootballPrediction/.venv/bin/python', '-m', 'pip', 'install', 'bandit']' returned non-zero exit status 1.

### 依赖漏洞扫描结果
❌ 扫描失败: pip-audit失败: Command '['/home/user/projects/FootballPrediction/.venv/bin/python', '-m', 'pip', 'install', 'pip-audit']' returned non-zero exit status 1.

## 💡 安全建议

1. 在 src/utils/_retry/__init__.py 中使用secrets模块替代random模块
2. 在 src/performance/middleware.py 中使用secrets模块替代random模块
3. 在 src/ml/enhanced_real_model_training.py 中使用secrets模块替代random模块
4. 在 src/ml/lstm_predictor.py 中使用secrets模块替代random模块
5. 在 src/ml/model_training.py 中使用secrets模块替代random模块
6. 在 src/ml/real_model_training.py 中使用secrets模块替代random模块
7. 在 src/models/prediction_model.py 中使用secrets模块替代random模块
8. 在 src/realtime/match_service.py 中使用secrets模块替代random模块
9. 在 src/database/migrations/versions/007_improve_phase3_implementations.py 中使用参数化查询


## 🎯 总结

- **安全问题**: 0 个
- **依赖漏洞**: 0 个
- **应用修复**: 0 个

**总体安全状态**: 🟢 良好

---

*报告生成时间: 2025-10-30 21:46:31*
