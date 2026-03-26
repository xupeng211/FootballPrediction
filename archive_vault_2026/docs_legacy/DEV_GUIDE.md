# TITAN V4.46.6 开发者核心指南

> **版本**: V4.46.6-REAL-COMBAT
> **最后更新**: 2026-03-11
> **适用范围**: 核心训练、预测流水线、特征工程

---

## 目录

1. [快速开始](#快速开始)
2. [核心流水线](#核心流水线)
3. [特征工程规范](#特征工程规范)
4. [训练规范](#训练规范)
5. [数据诚信准则](#数据诚信准则)
6. [API 参考](#api-参考)

---

## 快速开始

### 环境准备

```bash
# 启动开发环境
docker-compose -f docker-compose.dev.yml up -d

# 进入容器
docker-compose -f docker-compose.dev.yml exec dev bash

# 验证环境
python --version  # Python 3.11+
node --version    # Node 18+
```

### 一键训练

```bash
# 执行核心训练 (时序隔离)
python scripts/ops/TITAN_CORE_TRAIN.py

# 输出位置
# models/titan_v4466_real_combat.joblib
```

### 一键预测

```bash
# 周末预测
python scripts/ops/predict_weekend.py

# 单场预测
python scripts/ops/predict_match.py --match "55_20242025_4803413"
```

---

## 核心流水线

### 数据层级

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  L1 Discovery   │───▶│  L2 Harvest     │───▶│  L3 Smelt       │
│  (赛程发现)      │    │  (数据收割)     │    │  (特征熔炼)     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
        │                       │                       │
        ▼                       ▼                       ▼
   matches 表             l2_match_data          l3_features
                          raw_match_data
```

### 核心脚本索引

| 脚本 | 功能 | 输入 | 输出 |
|------|------|------|------|
| `TITAN_CORE_TRAIN.py` | 模型训练 | l3_features | models/*.joblib |
| `predict_pipeline.py` | 批量预测 | models + l3_features | predictions 表 |
| `smelt_l3.py` | 特征熔炼 | l2_match_data | l3_features |
| `recalculate_elo.js` | Elo 重算 | matches | l3_features.elo |

---

## 特征工程规范

### 11 维纯净特征集

```python
TITAN_COMBAT_FEATURES = [
    # === Elo 核心 (5 维) ===
    "home_elo_pre",        # 主队赛前 Elo (1500 基准)
    "away_elo_pre",        # 客队赛前 Elo
    "elo_diff",            # Elo 差值 (主 - 客)
    "expected_home_win",   # 主队预期胜率 (Elo 公式计算)
    "expected_away_win",   # 客队预期胜率

    # === 身价力量 (3 维) ===
    "log_home_squad_value",  # log10(主队身价)
    "log_away_squad_value",  # log10(客队身价)
    "home_mv_share",         # 主队身价占比 = home / (home + away)

    # === 历史交锋 (3 维) ===
    "h2h_home_win_ratio",    # 主队历史胜率
    "h2h_draw_ratio",        # 历史平局率
    "h2h_avg_goal_diff",     # 平均净胜球 (主队视角)
]
```

### 字段命名规范

| 类别 | 字段名 | 类型 | 单位 | 说明 |
|------|--------|------|------|------|
| 身价 | `home_squad_value_eur` | numeric | **欧元** | 非百万! |
| 身价 | `away_squad_value_eur` | numeric | **欧元** | 非百万! |
| Elo | `home_elo_pre` | float | 分 | 赛前评分 |
| H2H | `h2h_avg_goal_diff` | float | 球 | 主队视角 |

### 身价计算逻辑

```python
def extract_market_value_features(lineup_data: dict) -> dict:
    """
    提取身价特征

    严禁使用:
    - home_market_value (旧字段)
    - 百万欧元单位 (必须转换为欧元)
    """
    home_mv = float(lineup_data.get('home_squad_value_eur', 0))
    away_mv = float(lineup_data.get('away_squad_value_eur', 0))

    # 对数转换 (防止极端值)
    log_home = math.log10(home_mv) if home_mv > 0 else 18.0
    log_away = math.log10(away_mv) if away_mv > 0 else 18.0

    # 动态占比 (核心!)
    total_mv = home_mv + away_mv
    mv_share = home_mv / total_mv if total_mv > 0 else 0.5

    return {
        'log_home_squad_value': log_home,
        'log_away_squad_value': log_away,
        'home_mv_share': mv_share
    }
```

### H2H 计算逻辑

```python
def calculate_h2h_features(h2h_data: dict) -> dict:
    """
    计算 H2H 特征

    注意: h2h_avg_goal_diff 必须是历史数据，严禁包含当场结果
    """
    return {
        'h2h_home_win_ratio': float(h2h_data.get('h2h_home_win_ratio', 0.4)),
        'h2h_draw_ratio': float(h2h_data.get('h2h_draw_ratio', 0.25)),
        'h2h_avg_goal_diff': float(h2h_data.get('h2h_avg_goal_diff', 0.0))
    }
```

---

## 训练规范

### 严禁事项 (FORBIDDEN)

```python
# ❌ 严禁随机划分
X_train, X_test = train_test_split(X, test_size=0.2)  # 禁止!

# ❌ 严禁使用赛后统计
features = ['possession_pct', 'shots_total', 'xg']  # 禁止!

# ❌ 严禁过拟合参数
model = XGBClassifier(n_estimators=500, max_depth=10)  # 禁止!
```

### 强制标准 (REQUIRED)

```python
# ✅ 时序隔离
train: WHERE match_date <= '2025-12-31'
test:  WHERE match_date >= '2026-01-01'

# ✅ 降温参数
model = XGBClassifier(
    n_estimators=80,      # 固定
    max_depth=3,          # 固定
    learning_rate=0.05,
    reg_alpha=0.5,        # L1 正则化
    reg_lambda=2.0        # L2 正则化
)

# ✅ H2H 除毒审计
audit_h2h_leakage(test_data)
```

### 训练输出规范

```python
# 模型保存路径
MODEL_PATH = "models/titan_v4466_real_combat.joblib"
SCALER_PATH = "models/titan_v4466_real_combat_scaler.joblib"
META_PATH = "models/titan_v4466_real_combat_metadata.json"

# 元数据必须包含
metadata = {
    'version': 'V4.46.6-REAL-COMBAT',
    'temporal_split': {
        'train': '<= 2025-12-31',
        'test': '>= 2026-01-01'
    },
    'training_params': {...},
    'feature_importance': {...}
}
```

---

## 数据诚信准则

### 特征泄露检测

| 特征类型 | 安全性 | 检测方法 |
|----------|--------|----------|
| Elo 评分 | ✅ 安全 | 赛前计算 |
| 身价数据 | ✅ 安全 | 赛前已知 |
| H2H 历史 | ⚠️ 需审计 | 确保不含当场 |
| 控球率 | ❌ 泄露 | 赛后统计 |
| 射门数 | ❌ 泄露 | 赛后统计 |
| xG | ❌ 泄露 | 赛后统计 |

### 性能预警阈值

```
┌─────────────────────────────────────────────────────────────┐
│                    准确率预警系统                            │
├─────────────────────────────────────────────────────────────┤
│  45% - 55%  │  ✅ 正常范围 (真实能力)                       │
│  55% - 60%  │  ⚠️ 需审查 (可能轻微泄露)                    │
│  60% - 70%  │  🚨 高度可疑 (建议重审特征)                  │
│  > 70%      │  ❌ 几乎必然泄露 (必须重构)                  │
└─────────────────────────────────────────────────────────────┘
```

---

## API 参考

### 模型加载

```python
import joblib

# 加载生产模型
model = joblib.load('models/titan_v4466_real_combat.joblib')
scaler = joblib.load('models/titan_v4466_real_combat_scaler.joblib')

# 预测
features = extract_features(match_data)
features_scaled = scaler.transform([features])
probs = model.predict_proba(features_scaled)[0]

# 输出: [P(Away), P(Draw), P(Home)]
```

### Elo 重算

```bash
# 全量重算
node scripts/maintenance/recalculate_elo.js

# 增量更新
node scripts/maintenance/recalculate_elo.js --incremental

# 预览模式
node scripts/maintenance/recalculate_elo.js --dry-run
```

### 特征熔炼

```bash
# 熔炼单场比赛
python scripts/ops/smelt_target.py --match "55_20242025_4803413"

# 批量熔炼
python scripts/ops/smelt_l3.py --league "Premier League"
```

---

## 故障排查

### 常见问题

| 问题 | 原因 | 解决方案 |
|------|------|----------|
| 身价占比 50% | 数据缺失/默认值 | 检查 `home_squad_value_eur` 字段 |
| H2H 全 0 | 计算逻辑缺失 | 运行 `combat_ready_fix.py` |
| 准确率 >70% | 特征泄露 | 审查 `tactical_features` |
| Elo 不更新 | 联赛未识别 | 运行 `recalculate_elo.js` |

---

## 版本历史

| 版本 | 日期 | 主要变更 |
|------|------|----------|
| V4.46.6 | 2026-03-11 | 时序隔离 + 降温参数 |
| V4.46.5 | 2026-03-10 | 身价字段对齐 |
| V4.46.0 | 2026-03-09 | H2H 修复 |

---

**文档维护者**: ML Engineering Team
**最后审核**: 2026-03-11
