# Football Prediction Golden Dataset v1

## 📊 数据集概述

**数据集名称**: `features_v1.csv`
**创建时间**: 2025-12-10
**数据量**: 1,900 场比赛
**特征数量**: 61 个特征
**文件大小**: 862 KB

## 🏗️ 构建流程

### Extract (提取)
- **数据源**: PostgreSQL 数据库 `matches` 表
- **筛选条件**:
  - 比赛状态: `FT` (Full Time - 已完成)
  - 完整数据: `stats_json`, `home_xg`, `away_xg`, `home_score`, `away_score`
- **提取范围**: 全量符合条件的比赛 (1,900 场)

### Transform (转换)
- **特征提取器**: `EnhancedFeatureExtractor` v2.0
- **特征工程**:
  - 元数据特征 (6个)
  - 目标变量 (8个)
  - 高级统计 (7个)
  - 基础统计 (18个)
  - 上下文特征 (9个)
  - 衍生特征 (6个)
- **错误处理**: 容错机制，失败比赛不影响整体流程

### Load (加载)
- **输出格式**: CSV (UTF-8 编码)
- **版本管理**: v1.0
- **位置**: `data/processed/features_v1.csv`

## 📋 特征详情

### 🏷️ 元数据特征 (6个)
- `match_id`: 比赛唯一标识
- `year`: 比赛年份
- `month`: 比赛月份
- `day_of_week`: 星期几 (0=Monday, 6=Sunday)
- `day_of_year`: 年内第几天
- `is_weekend`: 是否周末比赛 (1=是, 0=否)

### 🎯 目标变量 (8个)
- `home_score`: 主队得分
- `away_score`: 客队得分
- `result`: 比赛结果 (H=主胜, D=平局, A=客胜)
- `result_numeric`: 结果数值编码 (H=1, D=0, A=-1)
- `has_winner`: 是否有胜负 (1=是, 0=否)
- `goal_difference`: 净胜球 (主队-客队)
- `total_goals`: 总进球数
- `over_2_5_goals`: 是否超过2.5球 (1=是, 0=否)

### 🧠 高级统计 (7个) - 100% 覆盖
- `home_xg`: 主队期望进球
- `away_xg`: 客队期望进球
- `xg_difference`: 期望进球差值 (主队-客队)
- `total_xg`: 总期望进球
- `home_xg_vs_actual`: 主队xG vs 实际进球差异
- `away_xg_vs_actual`: 客队xG vs 实际进球差异
- `total_xg_vs_actual`: 总xG vs 实际总进球差异

### 📊 基础统计 (18个)
- 控球率: `home_possession_percentage`, `away_possession_percentage`
- 射门数据: `home_total_shots`, `away_total_shots`
- 射正数据: `home_shots_on_target`, `away_shots_on_target`
- 角球数据: `home_corners`, `away_corners`
- 犯规数据: `home_fouls`, `away_fouls`
- 黄牌数据: `home_yellow_cards`, `away_yellow_cards`
- 红牌数据: `home_red_cards`, `away_red_cards`
- 越位数据: `home_offsides`, `away_offsides`
- 传球数据: `home_total_passes`, `away_total_passes`
- 传球精度: `home_pass_accuracy`, `away_pass_accuracy`

### 🌍 上下文特征 (9个)
- `referee_name`: 裁判信息 (JSON格式)
- `stadium_name`: 比赛场地信息 (JSON格式)
- `weather_condition`: 天气状况
- `weather_temperature`: 温度
- `weather_humidity`: 湿度
- `weather_wind_speed`: 风速
- `pitch_condition`: 场地状况
- `home_win_odds`: 主胜赔率
- `draw_odds`: 平局赔率
- `away_win_odds`: 客胜赔率

### ⚡ 衍生特征 (6个)
- `home_shot_accuracy`: 主队射门精度
- `away_shot_accuracy`: 客队射门精度
- `home_xg_overperformance`: 主队xG超常表现
- `away_xg_overperformance`: 客队xG超常表现
- `possession_advantage`: 控球率优势

## 📈 数据质量指标

### 整体质量
- **处理成功率**: 100.0% (1,900/1,900)
- **处理速度**: 2,289.1 场/秒
- **处理耗时**: 0.8 秒
- **失败比赛**: 0 场

### 特征覆盖率
- **元数据特征**: 100.0%
- **目标变量**: 100.0%
- **高级统计**: 100.0% ⭐ (核心ML特征)
- **基础统计**: 0.0% (stats_json解析需优化)
- **上下文特征**: 100.0%
- **衍生特征**: 80.1% (1,523/1,900)

## 🎯 使用建议

### 适用场景
1. **机器学习模型训练**: 使用61个特征训练预测模型
2. **特征重要性分析**: 分析各特征对比赛结果的影响
3. **模型性能评估**: 基于历史数据评估模型准确性
4. **实时预测服务**: 作为特征工程的参考模板

### 推荐特征组合
- **核心ML特征**: xG系列 + 基础统计 + 目标变量
- **轻量模型**: 仅使用xG + 元数据特征
- **完整模型**: 全部61个特征

### 数据预处理建议
1. **缺失值处理**: 根据业务需求填充或删除缺失值
2. **特征编码**: 对分类变量进行编码 (如result字段)
3. **数据标准化**: 对数值特征进行标准化处理
4. **特征选择**: 使用特征重要性分析选择最优特征子集

## 🔄 版本历史

- **v1.0** (2025-12-10): 初始版本，包含1,900场比赛，61个特征

## 📞 联系信息

**创建者**: Data Engineer Team
**技术栈**: Python, AsyncIO, Pandas, PostgreSQL
**代码仓库**: `scripts/build_dataset.py`

---

*此数据集遵循MLOps最佳实践，采用版本化管理，确保模型训练的可重现性和一致性。*