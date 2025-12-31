# V51.0 特征提取引擎 - 快速启动指南
## V51.0 Feature Refiner - Quick Start Guide

**版本**: V51.0 (深度脱水版)
**更新日期**: 2025-12-31
**状态**: ✅ Production-Ready

---

## 📋 概览

V51.0 是 FootballPrediction 项目的核心特征提取引擎，负责将 FotMob L2 API 的原始 JSON 数据转换为机器学习可用的数值特征矩阵。

**核心特性**:
- **维度压缩**: 12,061 → 642 维 (-94.7%)
- **自动过滤**: 移除 ID、颜色、文本等噪声特征
- **智能填充**: 自动处理 NaN 值
- **高性能**: ~120ms/场

---

## 🚀 一键生成 9000 场训练集

### 方法 1: 命令行 (推荐)

```bash
# 生成全部 9000 场比赛的特征 CSV
python -m src.processors.v51_feature_refiner \
    --output data/processed/v51_features_9000.csv

# 生成指定赛季
python -m src.processors.v51_feature_refiner \
    --season "23/24" \
    --league "Premier League" \
    --output data/processed/v51_features_epl_2324.csv

# 自定义最大维度
python -m src.processors.v51_feature_refiner \
    --max-features 300 \
    --output data/processed/v51_features_300.csv
```

### 方法 2: Python 代码

```python
from src.processors.v51_feature_refiner import extract_features_from_db

# 提取所有比赛
df, stats = extract_features_from_db(
    limit=None,  # None 表示提取所有
    max_features=500,
    show_progress=True,
)

# 保存到 CSV
df.to_csv("data/processed/v51_features_all.csv", index=False)

# 查看统计
print(stats)
```

### 方法 3: 专用训练集生成脚本

```bash
# 创建并运行生成脚本
python scripts/ml/generate_v51_training_set.py
```

---

## 📊 输出格式

### CSV 文件结构

```
match_id,header_teams_0_score,header_teams_1_score,header_events_...,content_stats_...
4193453,2.0,1.0,0.0,1.0,15.5,...
4193454,1.0,1.0,0.0,0.0,12.3,...
...
```

### 特征说明

| 类别 | 特征数 | 示例 |
|------|--------|------|
| Header 基础 | 8 | 比分、队伍统计 |
| Header 事件 | 93 | 进球事件聚合、前 5 个事件详情 |
| Content 统计 | 481 | 射门、控球、xG 等 |
| Content 射门地图 | 46 | 射门位置、xG |
| 元数据 | 1 | match_id |

详细说明见: [docs/v51_feature_dictionary.md](../docs/v51_feature_dictionary.md)

---

## 🔧 数据质量检查

### 运行健康检查

```bash
# 默认抽取 10 场比赛检查
python scripts/maintenance/check_v51_data_health.py

# 抽取 20 场，详细输出
python scripts/maintenance/check_v51_data_health.py \
    --sample-size 20 \
    --verbose

# 自定义异常值阈值
python scripts/maintenance/check_v51_data_health.py \
    --outlier-threshold 3.0
```

### 报告解读

健康检查报告包含:

1. **数据库统计**: Finished 比赛总数、数据覆盖率
2. **样本提取**: 特征维度、提取速度
3. **NaN 检查**: 是否存在缺失值
4. **异常值检查**: Z-score 方法检测极值
5. **一致性检查**: ID 字段泄露、全零特征
6. **就绪度评分**: A/B/C/D/F 五级评分

**示例输出**:
```
综合评分: 97/100
数据等级: 🟢 A
✅ 数据质量优秀，可以开始模型训练！
```

---

## ⚠️ 错误处理

### 1. 数据缺失

**症状**: `ValueError: No matches found`

**原因**: 数据库中没有 finished 状态的比赛

**解决方案**:
```bash
# 检查数据库状态
docker-compose exec db psql -U football_user -d football_prediction_dev \
    -c "SELECT status, COUNT(*) FROM matches GROUP BY status;"
```

### 2. raw_data 缺失

**症状**: `NoneType has no attribute 'get'`

**原因**: 比赛存在但 raw_match_data 表为空

**解决方案**:
```bash
# 检查 raw_data 覆盖
docker-compose exec db psql -U football_user -d football_prediction_dev \
    -c "SELECT COUNT(*) FROM raw_match_data;"

# 如果为空，运行 L2 数据采集
python -m src.api.collectors.full_l1_l2_harvest
```

### 3. 维度过高警告

**症状**: `⚠️ 特征数 675 超过建议值 500`

**原因**: 不同联赛数据结构差异导致维度膨胀

**解决方案**:
```bash
# 降低 max_features
python -m src.processors.v51_feature_refiner \
    --max-features 300 \
    --output data/processed/v51_features_300.csv
```

### 4. 内存不足

**症状**: `MemoryError` 或系统卡死

**解决方案**:
```python
# 分批处理
from src.processors.v51_feature_refiner import extract_features_from_db

# 分 3 批处理
batch_size = 3000
for i in range(0, 9000, batch_size):
    df, stats = extract_features_from_db(
        limit=batch_size,
        show_progress=True,
    )
    df.to_csv(f"data/processed/v51_features_batch_{i}.csv", index=False)
```

---

## 📈 性能优化建议

### 1. 并行处理 (多进程)

```python
from multiprocessing import Pool
from src.processors.v51_feature_refiner import extract_features_from_db

def extract_batch(season):
    df, _ = extract_features_from_db(
        season_filter=season,
        show_progress=False,
    )
    return df

# 并行提取 5 个赛季
seasons = ["20/21", "21/22", "22/23", "23/24", "24/25"]

with Pool(5) as p:
    results = p.map(extract_batch, seasons)

# 合并结果
import pandas as pd
df_all = pd.concat(results, ignore_index=True)
df_all.to_csv("data/processed/v51_features_all_parallel.csv", index=False)
```

### 2. 数据库查询优化

```sql
-- 创建索引 (如果不存在)
CREATE INDEX IF NOT EXISTS idx_matches_status_finished
ON matches(status, home_score, away_score)
WHERE status = 'finished';

CREATE INDEX IF NOT EXISTS idx_raw_match_data_match_id
ON raw_match_data(match_id);
```

---

## 📚 相关文档

| 文档 | 说明 |
|------|------|
| [docs/v51_feature_dictionary.md](../docs/v51_feature_dictionary.md) | 特征字典 - 642 维特征详解 |
| [tests/processors/test_v51_feature_refiner.py](../tests/processors/test_v51_feature_refiner.py) | 验收测试套件 |
| [archive/legacy_features/](../archive/legacy_features/) | 旧版本归档 |

---

## 🔄 版本历史

| 版本 | 日期 | 主要变更 |
|------|------|----------|
| V51.0 | 2025-12-31 | 初始版本，深度脱水 (12,061 → 642 维) |

---

## 🆘 获取帮助

遇到问题？

1. **查看日志**: `logs/app.log`
2. **运行健康检查**: `python scripts/maintenance/check_v51_data_health.py`
3. **提交 Issue**: 在项目仓库创建 Issue

---

**维护团队**: ML Engineering Team
**最后更新**: 2025-12-31
