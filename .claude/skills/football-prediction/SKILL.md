---
name: football-prediction
description: Professional football match prediction and analysis using XGBoost 2.0+ ML model. Use when predicting match results, analyzing team performance, or calculating win probabilities. Features 67.2% accuracy with <100ms response time.
---

# Football Prediction Skill

## 技能概述
专业的足球比赛预测和分析技能，基于XGBoost 2.0+机器学习模型，提供高精度的比赛结果预测。

## 核心能力
- **比赛预测**: 基于历史数据和高级特征工程的精准预测
- **概率分析**: 提供主胜、平局、客胜的详细概率分布
- **置信度评估**: 量化的预测可信度评分
- **实时推理**: <100ms的快速响应时间
- **批量处理**: 支持多场比赛批量预测

## 模型规格
- **算法**: XGBoost 2.0+ classifier
- **特征维度**: 12+ 专业特征
- **当前准确率**: 67.2% (目标65%+)
- **响应时间**: <100ms (单次预测)
- **缓存命中率**: >80%

## 关键特征工程
### Phase 5 高级特征
1. **主客场分离统计** - 解决场地偏见
2. **历史交锋分析(H2H)** - "克星"效应建模
3. **联赛形态特征** - 积分替代进球数
4. **Elo评级系统** - 动态实力评估
5. ** rolling统计** - 近期状态量化

## 使用场景

### 1. 单场比赛预测
```bash
python scripts/predict_match_v2.py --home "Manchester United" --away "Arsenal"
```

### 2. 批量预测
```bash
python scripts/predict_match_v2.py --batch matches.json
```

### 3. API集成
```python
from src.services.inference_service_v2 import InferenceServiceV2
service = InferenceServiceV2()
result = await service.predict_single_match(home_team, away_team)
```

## 输出格式

### 控制台输出
```
🏟️  比赛: Manchester United vs Arsenal
📅  日期: 2024-01-15

📊 预测概率:
主胜 (HOME) : 65.2% |███████████████████████████████████░░░|
平局 (DRAW) : 22.1% |███████████████░░░░░░░░░░░░░░░░░░░░░░|
客胜 (AWAY) : 12.7% |███████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░|

🎯 预测结果: HOME_WIN
💡 置信度: 65.2%
📈 模型版本: xgboost_v2
```

### JSON API响应
```json
{
  "match": {
    "home_team": "Manchester United",
    "away_team": "Arsenal",
    "date": "2024-01-15"
  },
  "prediction": {
    "outcome": "HOME_WIN",
    "probabilities": {
      "home_win": 0.652,
      "draw": 0.221,
      "away_win": 0.127
    },
    "confidence": 0.85
  },
  "model_info": {
    "version": "xgboost_v2",
    "accuracy": 0.672,
    "features_used": 15
  }
}
```

## 数据架构
### 输入数据要求
- **最少历史数据**: 6个月比赛记录
- **数据源**: FotMob API (L2级别数据提取)
- **存储**: PostgreSQL (历史数据) + Redis (缓存)
- **更新频率**: 实时数据同步

### 特征数据流
```
FotMob API → 数据收集器 → 特征工程 → PostgreSQL → 特征缓存 → 模型推理
```

## 性能优化
### 缓存策略
- **Redis缓存**: 比赛特征和预测结果
- **本地缓存**: 模型和常用数据
- **TTL设置**: 24小时特征缓存，1小时预测缓存

### 并发处理
- **异步架构**: FastAPI + async/await
- **连接池**: PostgreSQL连接池管理
- **批量推理**: 优化GPU/CPU利用率

## 质量保证
### 模型验证
- **交叉验证**: 5折交叉验证
- **回测分析**: 历史数据性能评估
- **A/B测试**: 新模型vs旧模型对比
- **监控仪表板**: Grafana实时性能监控

### 数据质量
- **异常检测**: 自动识别异常比赛数据
- **数据清洗**: 标准化和去重
- **完整性检查**: 必要字段验证

## 集成点
### 1. CLI工具
- `scripts/predict_match_v2.py` - 主要预测CLI
- `scripts/test_real_model.py` - 模型测试工具
- `scripts/train_model_from_csv.py` - 模型训练工具

### 2. API服务
- `/api/v2/predict` - 预测端点
- `/api/v2/batch-predict` - 批量预测
- `/api/health` - 模型健康检查

### 3. 监控集成
- **Prometheus指标**: 预测请求量、准确率、延迟
- **Grafana仪表板**: 实时性能可视化
- **Alertmanager**: 性能异常告警

## 扩展能力
### 正在开发
- **实时赔率集成**: 博彩公司数据融合
- **球员伤病数据**: 阵容完整性评估
- **天气因素**: 比赛条件影响分析
- **情绪分析**: 社交媒体情绪指标

### 未来规划
- **多模型集成**: XGBoost + Neural Network
- **联赛特定模型**: 不同联赛专用模型
- **实时预测**: 比赛进行中的动态预测
- **解释性AI**: SHAP值可视化

## 最佳实践
### 使用建议
1. **数据新鲜度**: 确保使用最新的球队数据
2. **置信度阈值**: 建议只使用置信度>70%的预测
3. **联赛专长**: 模型在主流联赛表现更佳
4. **批次大小**: 批量预测建议不超过100场

### 常见问题
**Q: 预测准确率如何？**
A: 当前准确率67.2%，持续优化中

**Q: 支持哪些联赛？**
A: 支持50+主流足球联赛

**Q: 如何提高预测精度？**
A: 结合实时数据、伤病情况和专家分析

## 技术栈
- **机器学习**: XGBoost 2.0+, scikit-learn, SHAP
- **数据处理**: pandas, numpy, asyncio
- **数据库**: PostgreSQL, Redis
- **API框架**: FastAPI, uvicorn
- **监控**: Prometheus, Grafana
- **容器化**: Docker, docker-compose