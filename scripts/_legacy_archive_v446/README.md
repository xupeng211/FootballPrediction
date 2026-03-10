# V4.46 归档文件

本目录包含从 `scripts/ops/` 清理出的历史版本和实验性脚本。

## 归档时间
- 2026-03-11

## 归档原因
- 版本已过期 (v1, v26, v40, v45, v187 等)
- 实验性功能未进入生产
- 一次性修复脚本
- 被新版本替代

## 归档文件清单

### 回测/实验脚本
- `run_v187_backtest.py` - V187 回测实验
- `v40_dissection.py` - V4.0 特征解剖引擎
- `backtest_v45_pit.py` - V45 PIT 回测
- `walk_forward_backtest.py` - Walk-forward 回测

### 预测实验
- `predict_laliga.py` - 西甲专项预测
- `predict_match.py` - 单场预测
- `predict_weekend.py` - 周末预测
- `elo_prediction.py` - 纯 Elo 预测

### 特征熔炼实验
- `smelt_l3.py` - L3 熔炼 (被 smelt_all.js 替代)
- `smelt_serie_a.js/py` - 意甲专项熔炼
- `smelt_target.js/py` - 目标熔炼

### 测试/调试工具
- `circuit_breaker_test.js` - 熔断器测试
- `stress_test_seriea.js` - 意甲压力测试
- `fingerprint_check.js` - 指纹检查
- `final_sweep.js` - 一次性清理

### 专项收割
- `hyper_swarm_stealth.js` - 意甲 403 专项收割

### 其他
- `autonomous_engine.js` - 全自动编排器 (实验性)
- `TITAN_CORE_TRAIN.py` - 旧版训练脚本
- `model_audit.py` - 模型审计
- `proxy_health_audit.js` - 代理健康审计
- `regression_test.py` - 回归测试
- `smoke_test_features.py` - 特征冒烟测试
- `audit_leakage.py` - 数据泄露审计
- `cleanup_console_logs.py` - 控制台日志清理
- `extract_core_features.py` - 核心特征提取
- `extract_lineup_features.py` - 阵容特征提取

## 恢复方法
如需恢复某个脚本:
```bash
mv scripts/_legacy_archive_v446/<script_name> scripts/ops/
```

## ⚠️ 警告
本目录下的脚本可能存在依赖问题，不建议直接运行。
