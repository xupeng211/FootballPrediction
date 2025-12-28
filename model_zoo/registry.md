# Model Zoo Registry

## 概述
此目录存储 FootballPrediction 系统的所有历史模型文件。

## 模型清单

### V19.0 系列
| 文件 | 描述 | 训练日期 | 准确率 |
|------|------|----------|--------|
| `v19.0_reconstruction.pkl` | V19.0 重构模型 | 2025-12-23 | - |
| `v19.0_calibrator.pkl` | 概率校准器 | 2025-12-23 | - |
| `v19.0_reconstruction_metadata.json` | 模型元数据 | 2025-12-23 | - |

### V19.1 系列
| 文件 | 描述 | 训练日期 | 准确率 |
|------|------|----------|--------|
| `v19.1_final_model.pkl` | V19.1 最终模型 | 2025-12-23 | 65.52% |
| `v19.1_calibrator.pkl` | 概率校准器 | 2025-12-23 | - |
| `v19.1_final_metadata.json` | 模型元数据 | 2025-12-23 | - |

### V19.2 系列
| 文件 | 描述 | 训练日期 | 准确率 |
|------|------|----------|--------|
| `v19.2_audit_report.json` | V19.2 审计报告 | 2025-12-23 | - |

### V19.3 系列
| 文件 | 描述 | 训练日期 | 准确率 |
|------|------|----------|--------|
| `v19.3_hardened_model.pkl` | V19.3 强化模型 | 2025-12-23 | - |
| `v19.3_hardened_metadata.json` | 模型元数据 | 2025-12-23 | - |

### V19.4 系列
| 文件 | 描述 | 训练日期 | 准确率 |
|------|------|----------|--------|
| `v19.4_draw_sensitivity_model.pkl` | V19.4 平局敏感度模型 | 2025-12-24 | **65.52%** |
| `v19.4_draw_sensitivity_scaler.pkl` | 特征缩放器 | 2025-12-24 | - |
| `v19.4_draw_sensitivity_metadata.json` | 模型元数据 | 2025-12-24 | - |

**注**: V19.4 是最后一个存储在 `src/production_models/` 中的版本，之后系统迁移到 `model_zoo/` 统一管理。

## 模型格式

- `.pkl` - XGBoost 模型文件（使用 joblib 或 pickle 序列化）
- `.json` - 模型元数据和配置
- `.joblib` - Scikit-learn 缩放器和校准器

## 使用方式

```python
import joblib
import json

# 加载模型
model = joblib.load('model_zoo/v19.4_draw_sensitivity_model.pkl')
metadata = json.load(open('model_zoo/v19.4_draw_sensitivity_metadata.json'))

# 查看元数据
print(metadata['feature_names'])
print(metadata['accuracy'])
```

## 版本历史

- **V19.0** (2025-12-23): 初始重构版本
- **V19.1** (2025-12-23): 最终稳定版本
- **V19.2** (2025-12-23): 审计版本
- **V19.3** (2025-12-23): 强化版本
- **V19.4** (2025-12-24): 平局敏感度版本（生产基线）

## 当前生产模型

当前系统使用 **V26.1** 版本的特征提取流水线，但核心模型算法仍基于 V19.4 架构。

**路径**: 生产模型应存储在 `data/models/` 目录中。

---

*最后更新: 2025-12-28*
*Phase 1.1b 清理后迁移*
