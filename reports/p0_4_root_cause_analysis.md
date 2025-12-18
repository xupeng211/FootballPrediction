# ML Pipeline 失败原因分析 (P0-4)

**分析时间**: 2025-12-06
**分析范围**: FootballPrediction 项目训练流水线
**严重级别**: P0-Critical (阻断所有模型训练)

---

## 1. 数据加载失败（Feature Loading）

### 🔴 具体错误：
- **数据源不统一**: 7个不同训练脚本使用7种不同的数据加载方式
- **FeatureStore缺失**: 所有脚本都未使用新的P0-2 FeatureStore
- **同步/异步不兼容**: FeatureStore (async) vs 训练脚本 (sync)

### 🔍 原因：
1. **历史遗留**: 训练脚本早于FeatureStore开发
2. **异步鸿沟**: 现代异步接口与同步脚本无法直接集成
3. **数据质量缺失**: 无DataQualityMonitor集成，数据错误无法及时发现

### 🛠️ 修复方案：
```python
# 创建统一FeatureLoader桥接异步FeatureStore
class FeatureLoader:
    def __init__(self, store: FeatureStoreProtocol):
        self.store = store

    # 桥接异步到同步
    def load_training_data_sync(self, match_ids: List[int]) -> Tuple[pd.DataFrame, pd.Series]:
        return asyncio.run(self.load_training_data(match_ids))
```

---

## 2. 特征不一致（Feature Mismatch）

### 🔴 哪些特征缺失/多余：
- **特征工程分散**: 每个脚本都有独立的特征工程逻辑
- **列名不统一**: 同一特征在不同脚本中使用不同列名
- **版本冲突**: 新FeatureStore特征定义与旧脚本不匹配

### 🔍 可能原因：
1. **缺乏统一接口**: 无feature_loader.py统一特征管理
2. **演进不协调**: FeatureStore更新后脚本未同步
3. **数据质量缺失**: 无自动化特征验证机制

### 🛠️ 修复方案：
```python
# 统一特征配置
FEATURE_CONFIG = {
    "required_features": [
        "home_team_strength", "away_team_strength",
        "home_form", "away_form", "h2h_win_rate"
    ],
    "feature_mappings": {
        "home_goals": "home_score",
        "away_goals": "away_score"
    }
}
```

---

## 3. 模型训练失败

### 🔴 在 fit() 哪一步报错：
- **数据格式错误**: XGBoost期望的数据格式与实际输入不匹配
- **缺失值处理**: 不同脚本对缺失值处理不一致
- **内存溢出**: 大数据集训练时内存管理不当

### 🔍 可能原因：
1. **数据预处理不统一**: 标准化、编码方式各异
2. **内存管理缺失**: 无分批训练机制
3. **错误处理不足**: 训练异常时无清晰错误信息

### 🛠️ 修复方案：
```python
class Trainer:
    def train_with_validation(self, X, y):
        # 数据验证
        self._validate_input_data(X, y)

        # 内存优化
        if len(X) > 100000:
            return self._train_in_batches(X, y)
        else:
            return self._train_direct(X, y)
```

---

## 4. Artifact 失败（模型无法保存）

### 🔴 使用什么路径？
- **路径混乱**: 不同脚本使用不同保存路径
  - `models/trained/` (某些脚本)
  - `models/enhanced/` (其他脚本)
  - `models/` (基础脚本)

### 🔍 权限 / MLflow / 相对路径问题？
1. **无MLflow集成**: 无统一模型注册表
2. **权限问题**: Docker容器内文件权限不一致
3. **版本管理缺失**: 模型文件覆盖，无历史追踪

### 🛠️ 修复方案：
```python
class ModelRegistry:
    def __init__(self, root_dir="artifacts/models"):
        self.root_dir = Path(root_dir)
        self.root_dir.mkdir(parents=True, exist_ok=True)

    def save_model(self, model, name: str, version: str = None):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        version = version or timestamp
        model_dir = self.root_dir / f"{name}/{version}"

        # 保存模型 + 元数据
        joblib.dump(model, model_dir / "model.joblib")
        self._save_metadata(model, model_dir, name, version)
```

---

## 5. Prefect 流程失败

### 🔴 哪个 Flow 无法运行？
- **无Prefect Flow**: 整个项目缺少工作流编排
- **手动执行**: 所有训练脚本都需要手动触发
- **无依赖管理**: 数据收集->特征工程->训练无自动化流水线

### 🔍 Prefect 环境问题？
1. **未安装Prefect**: requirements.txt中可能缺失
2. **版本冲突**: Prefect 1.x vs 2.x API不兼容
3. **配置缺失**: 无Prefect server配置

### 🛠️ 修复方案：
```python
# 新增Prefect 2.x Flow
from prefect import flow, task

@flow
def train_flow(season: str, league_id: str):
    match_ids = get_season_matches(season, league_id)
    X, y = load_features(match_ids)
    model = train_model(X, y)
    model_path = save_model(model, f"xgboost_{season}")
    return model_path
```

---

## 🚨 总结：P0-Critical 失败模式

| 失败类别 | 影响范围 | 修复优先级 | 预估工时 |
|---------|---------|-----------|---------|
| FeatureStore集成 | 所有训练脚本 | P0 | 4小时 |
| 特征不一致 | 模型性能 | P0 | 3小时 |
| 异步/同步桥接 | 数据加载 | P0 | 2小时 |
| 模型保存机制 | 模型管理 | P1 | 2小时 |
| Prefect工作流 | 自动化 | P1 | 3小时 |

**总阻断风险**: 100% (当前无训练脚本可正常运行)

**下一步行动**: 立即开始第3步 - 统一训练流水线目录结构