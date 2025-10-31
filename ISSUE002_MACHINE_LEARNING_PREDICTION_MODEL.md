# 🤖 集成机器学习预测算法模型

## 问题描述
基于历史比赛数据实现实际的预测算法，包括统计模型和机器学习模型，提供准确的比赛结果预测。

## 当前状态
- ✅ 本地Docker试运营环境已成功部署
- ✅ PostgreSQL数据库集成完成 (端口5433)
- ✅ 基础的预测CRUD功能已实现
- ✅ Issue #001: 足球数据API集成已规划
- ❌ 缺少实际的预测算法模型

## 验收标准
- [ ] 实现基础统计预测模型 (泊松分布、ELO评分等)
- [ ] 集成机器学习模型 (随机森林、XGBoost等)
- [ ] 实现模型训练和评估管道
- [ ] 添加预测置信度计算
- [ ] 通过回测验证模型准确性 (目标准确率 > 55%)

## 技术栈选择
- **机器学习框架**: scikit-learn, XGBoost, LightGBM
- **数据处理**: pandas, numpy
- **模型存储**: joblib, pickle
- **特征工程**: 基于历史数据的统计特征
- **模型评估**: 准确率、精确率、召回率、AUC

## 实现步骤

### 第一阶段：特征工程设计 (2-3天)
1. 分析历史比赛数据特征
2. 设计以下特征类别：
   - 球队历史表现特征
   - 主客场优势特征
   - 近期状态特征
   - 对战历史特征
3. 实现特征提取和计算逻辑
4. 创建特征存储和管理系统

### 第二阶段：统计模型实现 (2-3天)
1. 实现泊松分布预测模型
2. 实现ELO评分系统
3. 实现线性回归模型
4. 添加模型集成逻辑
5. 创建模型评估框架

### 第三阶段：机器学习模型实现 (3-4天)
1. 实现随机森林分类器
2. 实现XGBoost梯度提升模型
3. 实现神经网络模型 (可选)
4. 添加超参数调优
5. 实现模型选择和集成

### 第四阶段：预测服务集成 (2-3天)
1. 创建预测服务API
2. 集成模型预测管道
3. 添加预测结果存储
4. 实现预测置信度计算
5. 创建预测结果展示接口

### 第五阶段：模型评估和优化 (2-3天)
1. 进行历史数据回测
2. 分析模型性能指标
3. 优化模型参数
4. 创建模型监控机制
5. 实现模型自动更新

## 文件结构计划
```
src/
├── ml/
│   ├── __init__.py
│   ├── models/
│   │   ├── __init__.py
│   │   ├── base_model.py              # 基础模型类
│   │   ├── poisson_model.py           # 泊松分布模型
│   │   ├── elo_model.py               # ELO评分模型
│   │   ├── random_forest_model.py     # 随机森林模型
│   │   ├── xgboost_model.py           # XGBoost模型
│   │   └── ensemble_model.py          # 集成模型
│   ├── features/
│   │   ├── __init__.py
│   │   ├── feature_extractor.py       # 特征提取器
│   │   ├── team_features.py           # 球队特征
│   │   ├── match_features.py          # 比赛特征
│   │   └── historical_features.py     # 历史特征
│   ├── training/
│   │   ├── __init__.py
│   │   ├── data_preprocessor.py       # 数据预处理
│   │   ├── model_trainer.py           # 模型训练器
│   │   └── model_evaluator.py         # 模型评估器
│   ├── prediction/
│   │   ├── __init__.py
│   │   ├── prediction_service.py      # 预测服务
│   │   └── confidence_calculator.py   # 置信度计算
│   └── utils/
│       ├── __init__.py
│       ├── model_utils.py             # 模型工具
│       └── metrics.py                 # 评估指标
```

## 特征工程详细设计

### 球队历史特征
```python
def extract_team_historical_features(team_id, date, lookback_days=30):
    """
    提取球队历史特征
    """
    features = {
        # 进攻特征
        'avg_goals_scored': calculate_avg_goals_scored(team_id, lookback_days),
        'avg_shots_on_target': calculate_avg_shots_on_target(team_id, lookback_days),
        'avg_possession': calculate_avg_possession(team_id, lookback_days),

        # 防守特征
        'avg_goals_conceded': calculate_avg_goals_conceded(team_id, lookback_days),
        'avg_clean_sheets': calculate_avg_clean_sheets(team_id, lookback_days),
        'avg_tackles': calculate_avg_tackles(team_id, lookback_days),

        # 状态特征
        'recent_form': calculate_recent_form(team_id, lookback_days),
        'home_performance': calculate_home_performance(team_id, lookback_days),
        'away_performance': calculate_away_performance(team_id, lookback_days),

        # 伤病情况
        'key_players_available': calculate_available_key_players(team_id),
        'injury_impact': calculate_injury_impact(team_id)
    }
    return features
```

### 比赛特征
```python
def extract_match_features(home_team_id, away_team_id, match_date):
    """
    提取比赛特征
    """
    features = {
        # 主客场优势
        'home_advantage': calculate_home_advantage(home_team_id),

        # 对战历史
        'head_to_head_wins': calculate_head_to_head_wins(home_team_id, away_team_id),
        'head_to_head_goals': calculate_head_to_head_goals(home_team_id, away_team_id),
        'last_meeting_result': get_last_meeting_result(home_team_id, away_team_id),

        # 实力对比
        'team_strength_diff': calculate_team_strength_diff(home_team_id, away_team_id),
        'form_diff': calculate_form_diff(home_team_id, away_team_id),
        'ranking_diff': calculate_ranking_diff(home_team_id, away_team_id)
    }
    return features
```

## 模型实现示例

### 泊松分布模型
```python
import numpy as np
from scipy.stats import poisson
from sklearn.base import BaseEstimator

class PoissonModel(BaseEstimator):
    """
    基于泊松分布的足球预测模型
    """
    def __init__(self):
        self.home_avg_goals = None
        self.away_avg_goals = None

    def fit(self, X, y):
        """
        训练模型：计算平均进球数
        """
        # 这里简化实现，实际应该基于历史数据计算
        self.home_avg_goals = np.mean(y['home_goals'])
        self.away_avg_goals = np.mean(y['away_goals'])
        return self

    def predict(self, X):
        """
        预测比赛结果
        """
        predictions = []
        for _, match in X.iterrows():
            # 使用特征调整基础进球率
            home_exp_goals = self.home_avg_goals * match['home_attack_factor']
            away_exp_goals = self.away_avg_goals * match['away_attack_factor']

            # 计算各种结果的概率
            prob_home_win = self._calculate_poisson_probability(
                home_exp_goals, away_exp_goals, 'home_win'
            )
            prob_draw = self._calculate_poisson_probability(
                home_exp_goals, away_exp_goals, 'draw'
            )
            prob_away_win = self._calculate_poisson_probability(
                home_exp_goals, away_exp_goals, 'away_win'
            )

            predictions.append({
                'home_win_prob': prob_home_win,
                'draw_prob': prob_draw,
                'away_win_prob': prob_away_win,
                'predicted_outcome': np.argmax([prob_home_win, prob_draw, prob_away_win])
            })

        return predictions

    def _calculate_poisson_probability(self, home_goals, away_goals, outcome):
        """
        基于泊松分布计算结果概率
        """
        max_goals = 10
        total_prob = 0

        for hg in range(max_goals):
            for ag in range(max_goals):
                prob = poisson.pmf(hg, home_goals) * poisson.pmf(ag, away_goals)

                if outcome == 'home_win' and hg > ag:
                    total_prob += prob
                elif outcome == 'draw' and hg == ag:
                    total_prob += prob
                elif outcome == 'away_win' and hg < ag:
                    total_prob += prob

        return total_prob
```

### XGBoost模型
```python
import xgboost as xgb
from sklearn.model_selection import GridSearchCV
from sklearn.preprocessing import StandardScaler

class XGBoostModel(BaseEstimator):
    """
    基于XGBoost的足球预测模型
    """
    def __init__(self, n_estimators=100, max_depth=6, learning_rate=0.1):
        self.n_estimators = n_estimators
        self.max_depth = max_depth
        self.learning_rate = learning_rate
        self.model = None
        self.scaler = StandardScaler()

    def fit(self, X, y):
        """
        训练XGBoost模型
        """
        # 数据预处理
        X_scaled = self.scaler.fit_transform(X)

        # 初始化模型
        self.model = xgb.XGBClassifier(
            n_estimators=self.n_estimators,
            max_depth=self.max_depth,
            learning_rate=self.learning_rate,
            random_state=42,
            eval_metric='mlogloss'
        )

        # 训练模型
        self.model.fit(X_scaled, y)
        return self

    def predict_proba(self, X):
        """
        预测概率
        """
        X_scaled = self.scaler.transform(X)
        return self.model.predict_proba(X_scaled)

    def predict(self, X):
        """
        预测结果
        """
        X_scaled = self.scaler.transform(X)
        return self.model.predict(X_scaled)

    def get_feature_importance(self):
        """
        获取特征重要性
        """
        if self.model:
            return self.model.feature_importances_
        return None
```

## 模型评估框架
```python
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score

class ModelEvaluator:
    """
    模型评估器
    """
    def __init__(self):
        self.metrics = {}

    def evaluate_model(self, model, X_test, y_test):
        """
        评估模型性能
        """
        y_pred = model.predict(X_test)
        y_pred_proba = model.predict_proba(X_test)

        metrics = {
            'accuracy': accuracy_score(y_test, y_pred),
            'precision': precision_score(y_test, y_pred, average='weighted'),
            'recall': recall_score(y_test, y_pred, average='weighted'),
            'f1_score': f1_score(y_test, y_pred, average='weighted'),
            'roc_auc': roc_auc_score(y_test, y_pred_proba, multi_class='ovr')
        }

        return metrics

    def cross_validate_model(self, model, X, y, cv=5):
        """
        交叉验证
        """
        from sklearn.model_selection import cross_val_score

        scores = cross_val_score(model, X, y, cv=cv, scoring='accuracy')
        return {
            'mean_score': scores.mean(),
            'std_score': scores.std(),
            'scores': scores.tolist()
        }
```

## 数据库设计
```sql
-- 模型表
CREATE TABLE ml_models (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    type VARCHAR(50) NOT NULL,
    version VARCHAR(20) NOT NULL,
    file_path VARCHAR(255),
    parameters JSONB,
    accuracy FLOAT,
    precision_score FLOAT,
    recall_score FLOAT,
    f1_score FLOAT,
    is_active BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 特征数据表
CREATE TABLE match_features (
    id SERIAL PRIMARY KEY,
    match_id INTEGER,
    features JSONB NOT NULL,
    feature_version VARCHAR(20),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (match_id) REFERENCES matches(id)
);

-- 预测结果表
CREATE TABLE predictions (
    id SERIAL PRIMARY KEY,
    match_id INTEGER NOT NULL,
    model_id INTEGER NOT NULL,
    predicted_outcome VARCHAR(20),
    home_win_prob FLOAT,
    draw_prob FLOAT,
    away_win_prob FLOAT,
    confidence FLOAT,
    actual_outcome VARCHAR(20),
    is_correct BOOLEAN,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (match_id) REFERENCES matches(id),
    FOREIGN KEY (model_id) REFERENCES ml_models(id)
);
```

## API接口设计
```python
from fastapi import APIRouter, Depends, HTTPException
from typing import List, Optional

router = APIRouter(prefix="/ml", tags=["机器学习"])

@router.post("/predict/{match_id}")
async def predict_match(match_id: int, model_name: Optional[str] = None):
    """
    预测比赛结果
    """
    prediction_service = PredictionService()
    prediction = await prediction_service.predict(match_id, model_name)
    return prediction

@router.get("/models")
async def get_available_models():
    """
    获取可用模型列表
    """
    model_service = ModelService()
    models = await model_service.get_active_models()
    return models

@router.post("/models/{model_id}/train")
async def train_model(model_id: int):
    """
    训练模型
    """
    training_service = ModelTrainingService()
    result = await training_service.train_model(model_id)
    return result
```

## 测试计划
1. **单元测试**: 测试特征提取、模型训练、预测逻辑
2. **集成测试**: 测试完整的预测流程
3. **性能测试**: 测试模型响应时间和内存使用
4. **回测验证**: 使用历史数据验证模型准确性

## 完成时间预估
- **总时间**: 12-16天
- **关键路径**: 特征工程 → 模型实现 → 预测服务集成

## 风险和缓解措施
1. **数据质量**: 添加数据验证和清洗
2. **过拟合**: 使用交叉验证和正则化
3. **模型性能**: 集成多个模型提高准确性
4. **计算资源**: 优化模型复杂度和推理速度

## 后续集成
完成后可以接入：
- Issue #1: 足球数据API集成 (数据源)
- Issue #8: 系统监控和告警 (模型监控)
- Issue #13: API文档完善 (预测接口文档)

---

**优先级**: High
**标签**: feature, machine-learning, prediction, core-functionality
**负责人**: 待分配
**创建时间**: 2025-10-31
**预计完成**: 2025-11-16