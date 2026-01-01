# Model Zoo Registry

## 概述
此目录存储 FootballPrediction 系统的所有历史模型文件。

## 模型清单

### V51.x 系列 (实验性)
| 文件 | 描述 | 训练日期 | ROI/准确率 |
|------|------|----------|------------|
| `v51_3_full_power_model.pkl` | V51.3 Full Power 模型 | 2025-12-31 | 32% 真实 ROI (标签打乱验证) |
| `v51_1_athletic_model.pkl` | V51.1 Athletic 模型 | 2025-12-31 | - |
| `v51_athletic_v1.pkl` | V51.0 Athletic v1 | 2025-12-31 | - |

**V51.x 特征**:
- V51.1: 49-56 维滚动特征，时空隔离协议
- V51.0: 642 维深度脱水特征
- 标签打乱实验通过，模型真实有效

### V26.x 系列 (生产)
| 文件 | 描述 | 训练日期 | 准确率 |
|------|------|----------|--------|
| `v26.8_epl_production.pkl` | V26.8 英超专项模型 | 2025-12-30 | - |
| `v26.8_la_liga_production.pkl` | V26.8 西甲专项模型 | 2025-12-30 | - |
| `v26.8_ligue1_production.pkl` | V26.8 法甲专项模型 | 2025-12-30 | - |
| `v26.8_bund_production.pkl` | V26.8 德甲专项模型 | 2025-12-30 | - |
| `v26.7_aligned_production.pkl` | V26.7 通用对齐模型 | 2025-12-29 | 56% |
| `v26.6_pre_match.pkl` | V26.6 赛前模型 | 2025-12-28 | - |
| `v26.5_production.pkl` | V26.5 生产模型 | 2025-12-28 | - |
| `v26.5_mini.pkl` | V26.5 Mini 模型 | 2025-12-28 | - |
| `v26.4_mini.pkl` | V26.4 Mini 模型 | 2025-12-27 | - |
| `v26.3_prematch_baseline.pkl` | V26.3 赛前基线 | 2025-12-27 | - |
| `v26.2_baseline.pkl` | V26.2 基线模型 | 2025-12-26 | - |

**V26.x 特征**:
- V26.7: 19 维完全对齐的赛前特征
- V26.8: ModelDispatcher 智能模型分发

### V19.x 系列 (历史)
| 文件 | 描述 | 训练日期 | 准确率 |
|------|------|----------|--------|
| `v19.4_draw_sensitivity_model.pkl` | V19.4 平局敏感度模型 | 2025-12-24 | **65.52%** |
| `v19.4_draw_sensitivity_scaler.pkl` | 特征缩放器 | 2025-12-24 | - |
| `v19.3_hardened_model.pkl` | V19.3 强化模型 | 2025-12-23 | - |
| `v19.1_final_model.pkl` | V19.1 最终模型 | 2025-12-23 | 65.52% |
| `v19.1_calibrator.pkl` | 概率校准器 | 2025-12-23 | - |
| `v19.0_reconstruction.pkl` | V19.0 重构模型 | 2025-12-23 | - |
| `v19.0_calibrator.pkl` | 概率校准器 | 2025-12-23 | - |

**注**: V19.x 系列为历史版本，已被 V26.x 和 V51.x 取代。

## 模型格式

- `.pkl` - XGBoost 模型文件（使用 joblib 或 pickle 序列化）
- `.json` - 模型元数据和配置
- `.joblib` - Scikit-learn 缩放器和校准器

## 使用方式

```python
import joblib
import json

# 加载 V51.x 模型
model = joblib.load('model_zoo/v51_3_full_power_model.pkl')

# 加载 V26.8 模型
epl_model = joblib.load('model_zoo/v26.8_epl_production.pkl')

# 使用 ModelDispatcher (推荐)
from src.ml.engine import ModelDispatcher

dispatcher = ModelDispatcher()
prediction = dispatcher.predict(
    home_team="Arsenal",
    away_team="Chelsea",
    league_name="Premier League"  # 自动选择 EPL 专项模型
)
```

## 版本历史

- **V51.3** (2025-12-31): Full Power 模型，标签打乱验证通过
- **V51.1** (2025-12-31): 滚动特征架构，49 维时空隔离特征
- **V51.0** (2025-12-31): 深度脱水特征 (642 维)
- **V26.8** (2025-12-30): 联赛专项模型
- **V26.7** (2025-12-29): 训练-推理完全对齐，19 维动态特征
- **V19.4** (2025-12-24): 平局敏感度版本（生产基线）
- **V19.1** (2025-12-23): 最终稳定版本

## 当前生产模型

**推荐使用**:
- **预测**: V26.8 联赛专项模型 (通过 ModelDispatcher)
- **实验**: V51.3 Full Power 模型 (标签打乱验证通过)

**路径**: 所有模型统一存储在 `model_zoo/` 目录中。

---

*最后更新: 2025-12-31*
*包含 V51.x 实验性模型*
