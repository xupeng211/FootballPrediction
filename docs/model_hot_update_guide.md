# 模型热更新指南

## 🎯 概述

本文档描述如何更新足球预测系统的机器学习模型，实现无缝的热更新功能。

## 📋 模型信息

### 当前模型
- **模型类型**: XGBoost分类器
- **版本**: 1.0.0
- **特征数量**: 5个 (xG相关特征)
- **训练准确率**: 100%
- **模型文件**: `/app/data/models/football_prediction_model.pkl`
- **特征列**:
  - `home_xg` - 主队期望进球数
  - `away_xg` - 客队期望进球数
  - `total_xg` - 总期望进球数
  - `xg_difference` - 期望进球差值
  - `xg_ratio` - 期望进球比率

## 🔄 热更新流程

### 方法1：直接替换模型文件

#### 步骤1：准备新模型
```bash
# 训练新模型（使用现有数据）
python scripts/train_model_from_csv.py

# 或使用自定义训练脚本
python your_custom_training_script.py
```

#### 步骤2：验证新模型
```bash
# 测试新模型性能
python scripts/test_real_model.py
```

#### 步骤3：更新模型文件
```bash
# 备份当前模型
docker exec football-prediction-app cp /app/data/models/football_prediction_model.pkl /app/data/models/football_prediction_model.pkl.backup

# 复制新模型到容器
docker cp /path/to/new_model.pkl football-prediction-app:/app/data/models/football_prediction_model.pkl
```

#### 步骤4：重启预测服务
```bash
# 重启应用容器以加载新模型
docker-compose -f docker-compose.trial.yml restart app
```

#### 步骤5：验证更新
```bash
# 测试预测功能
docker exec football-prediction-app python scripts/predict_match_v2.py --home "Manchester United" --away "Arsenal"
```

### 方法2：版本化模型管理

#### 步骤1：创建版本化模型文件
```bash
# 使用版本号命名模型文件
docker cp /path/to/new_model_v2.pkl football-prediction-app:/app/data/models/football_prediction_model_v2.pkl
```

#### 步骤2：更新配置文件
```bash
# 更新环境变量
echo "MODEL_VERSION=v2" >> .env.trial
echo "MODEL_PATH=/app/data/models/football_prediction_model_v2.pkl" >> .env.trial
```

#### 步骤3：重启服务
```bash
docker-compose -f docker-compose.trial.yml restart app
```

## 📊 模型训练指南

### 数据准备
```python
# 1. 收集历史比赛数据
df = pd.read_csv('historical_matches.csv')

# 2. 特征工程
df['home_xg'] = extract_home_xg(df)
df['away_xg'] = extract_away_xg(df)
df['total_xg'] = df['home_xg'] + df['away_xg']
df['xg_difference'] = df['home_xg'] - df['away_xg']
df['xg_ratio'] = df['home_xg'] / (df['away_xg'] + 0.01)

# 3. 创建目标标签
label_mapping = {'Home': 0, 'Draw': 1, 'Away': 2}
df['target'] = df['match_result'].map(label_mapping)
```

### 模型训练
```python
import xgboost as xgb
from sklearn.model_selection import train_test_split

# 选择特征
feature_cols = ['home_xg', 'away_xg', 'total_xg', 'xg_difference', 'xg_ratio']
X = df[feature_cols]
y = df['target']

# 分割数据
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# 训练模型
model = xgb.XGBClassifier(
    objective='multi:softprob',
    num_class=3,
    n_estimators=100,
    max_depth=6,
    learning_rate=0.1,
    random_state=42
)

model.fit(X_train, y_train)

# 评估模型
accuracy = model.score(X_test, y_test)
print(f"模型准确率: {accuracy:.4f}")
```

### 保存模型
```python
import pickle

# 保存完整模型数据
model_data = {
    'model': model,
    'feature_columns': feature_cols,
    'accuracy': accuracy,
    'version': '2.0.0',
    'training_date': datetime.now().isoformat()
}

with open('football_prediction_model_v2.pkl', 'wb') as f:
    pickle.dump(model_data, f)
```

## 🧪 质量验证

### 模型性能指标
```python
# 计算各种指标
from sklearn.metrics import classification_report, confusion_matrix

# 详细分类报告
report = classification_report(y_test, y_pred, target_names=['Away', 'Draw', 'Home'])

# 混淆矩阵
cm = confusion_matrix(y_test, y_pred)
```

### A/B测试
```python
# 比较新旧模型性能
old_predictions = old_model.predict(X_test)
new_predictions = new_model.predict(X_test)

old_accuracy = accuracy_score(y_test, old_predictions)
new_accuracy = accuracy_score(y_test, new_predictions)

print(f"旧模型准确率: {old_accuracy:.4f}")
print(f"新模型准确率: {new_accuracy:.4f}")
print(f"性能提升: {((new_accuracy - old_accuracy) / old_accuracy * 100):.2f}%")
```

## 🔧 配置管理

### 环境变量配置
```bash
# .env.trial
MODEL_PATH=/app/data/models/football_prediction_model.pkl
MODEL_VERSION=1.0.0
MODEL_ACCURACY=1.0
FEATURE_COUNT=5
```

### 应用配置
```python
# src/config.py
class ModelConfig:
    def __init__(self):
        self.model_path = os.getenv("MODEL_PATH", "/app/data/models/football_prediction_model.pkl")
        self.model_version = os.getenv("MODEL_VERSION", "1.0.0")
        self.auto_reload = os.getenv("MODEL_AUTO_RELOAD", "false").lower() == "true"
        self.reload_interval = int(os.getenv("MODEL_RELOAD_INTERVAL", "300"))  # 5分钟
```

## 🚨 故障排除

### 常见问题

#### 1. 模型加载失败
**症状**: `模型加载失败: 模型文件不存在`
**解决方案**:
```bash
# 检查模型文件是否存在
docker exec football-prediction-app ls -la /app/data/models/

# 重新复制模型文件
docker cp football_prediction_model.pkl football-prediction-app:/app/data/models/
```

#### 2. 特征不匹配
**症状**: `ValueError: 特征数量不匹配`
**解决方案**:
```python
# 检查特征列是否一致
required_features = ['home_xg', 'away_xg', 'total_xg', 'xg_difference', 'xg_ratio']
current_features = list(X.columns)

# 确保特征顺序一致
X = X[required_features]
```

#### 3. 模型格式错误
**症状**: `pickle.UnpicklingError: invalid load key`
**解决方案**:
```python
# 验证模型文件格式
with open('model.pkl', 'rb') as f:
    data = pickle.load(f)
    assert 'model' in data
    assert 'feature_columns' in data
```

### 回滚策略
```bash
# 如果新模型有问题，快速回滚
docker exec football-prediction-app cp /app/data/models/football_prediction_model.pkl.backup /app/data/models/football_prediction_model.pkl
docker-compose -f docker-compose.trial.yml restart app
```

## 📈 性能监控

### 预测性能指标
- **准确率**: 预测正确的比例
- **响应时间**: 单次预测耗时
- **吞吐量**: 每秒预测数量

### 监控命令
```bash
# 查看预测日志
docker logs football-prediction-app | grep "真实模型预测完成"

# 监控系统资源
docker stats football-prediction-app

# 查看Grafana监控面板
open http://localhost:3000
```

## 🔄 自动化热更新脚本

### 创建自动化脚本
```bash
#!/bin/bash
# scripts/auto_model_update.sh

set -e

NEW_MODEL_PATH=$1
BACKUP_DIR="/app/data/models/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

echo "🔄 开始模型热更新流程..."

# 1. 创建备份目录
docker exec football-prediction-app mkdir -p $BACKUP_DIR

# 2. 备份当前模型
echo "📦 备份当前模型..."
docker exec football-prediction-app cp /app/data/models/football_prediction_model.pkl $BACKUP_DIR/backup_$TIMESTAMP.pkl

# 3. 复制新模型
echo "📥 部署新模型..."
docker cp $NEW_MODEL_PATH football-prediction-app:/app/data/models/football_prediction_model.pkl

# 4. 重启服务
echo "🔄 重启服务..."
docker-compose -f docker-compose.trial.yml restart app

# 5. 验证更新
echo "🧪 验证模型更新..."
sleep 10
docker exec football-prediction-app python scripts/test_real_model.py

echo "✅ 模型热更新完成!"
```

### 使用自动化脚本
```bash
# 运行自动更新
./scripts/auto_model_update.sh /path/to/new_model.pkl

# 监控更新过程
./scripts/auto_model_update.sh /path/to/new_model.pkl 2>&1 | tee model_update.log
```

## 📝 总结

### 关键要点
1. **备份优先**: 更新前始终备份当前模型
2. **测试验证**: 更新后立即测试模型功能
3. **渐进式部署**: 考虑使用A/B测试验证新模型
4. **监控指标**: 持续监控模型性能和系统健康状态
5. **快速回滚**: 准备快速回滚到稳定版本的能力

### 最佳实践
- 使用版本化命名管理多个模型版本
- 实施自动化测试确保模型质量
- 建立监控告警机制跟踪模型性能
- 定期评估和重新训练模型以保持准确性
- 文档化所有模型更新操作和配置变更

---

**更新时间**: 2025-12-18
**版本**: v2.1.0
**维护者**: ML Engineering Team