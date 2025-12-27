# Data Engineering Module

**V28.0 生产级特征提取与时间对齐流水线**

---

## 模块职责

`src/data_engineering/` 模块负责从 `raw_match_data` 表中提取 L2 统计数据，并计算时间对齐的滚动特征。

### 核心功能

1. **多路径 JSONB 提取** - 针对 FotMob API 数据的鲁棒解析
2. **时间对齐滚动特征** - 严格防止数据泄露的滚动窗口计算
3. **批量处理机制** - 内存安全的分批处理
4. **连接池管理** - 基于 `SyncDatabasePool` 的高效数据库连接

### 验收指标

| 指标 | 目标值 | 说明 |
|------|--------|------|
| **填充率** | 80%+ | 通过多路径降级实现 |
| **数据泄露** | 0% | 严格 `match_date < current_match_date` |
| **内存安全** | 稳定 | 批量处理 500 条/批次 |

---

## 文件结构

```
src/data_engineering/
├── __init__.py                 # 模块导出
├── multipath_extractor.py      # 多路径 JSONB 提取器
├── feature_pipeline.py         # V28.0 生产级特征流水线
└── README.md                   # 本文档
```

---

## 核心组件

### 1. MultiPathExtractor (`multipath_extractor.py`)

多路径 JSONB 提取器，针对 FotMob API 数据结构设计。

#### 提取路径优先级

```
┌─────────────────────────────────────────────────────────────────┐
│                    多路径探测优先级                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │  路径 1 (核心统计路径)                                     │ │
│  │  content -> stats -> Periods -> All -> stats              │ │
│  │                                                           │ │
│  │  提取内容: xG, possession, shots, shots_on_target,       │ │
│  │            passes, team_rating                            │ │
│  └───────────────────────────────────────────────────────────┘ │
│                           ↓ 失败时降级                          │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │  路径 2 (备用路径)                                        │ │
│  │  content -> matchFacts -> stats                           │ │
│  │                                                           │ │
│  │  提取内容: xG (有限的备用数据)                            │ │
│  └───────────────────────────────────────────────────────────┘ │
│                           ↓ 失败时降级                          │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │  路径 3 (比分正则解析)                                    │ │
│  │  content -> header -> status -> scoreStr                  │ │
│  │                                                           │ │
│  │  提取内容: home_score, away_score (正则表达式)           │ │
│  └───────────────────────────────────────────────────────────┘ │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

#### 关键类

| 类名 | 职责 |
|------|------|
| `ExtractionPath` | 提取路径枚举 (CORE_STATS / MATCH_FACTS / SCORE_STRING) |
| `MatchStats` | 单场比赛统计数据容器 |
| `ExtractionStats` | 提取统计和成功率计算 |
| `MultiPathExtractor` | 核心提取器，实现多路径降级逻辑 |

---

### 2. V28FeaturePipeline (`feature_pipeline.py`)

生产级特征流水线，负责端到端的特征提取和计算。

#### 流水线阶段

```
┌─────────────────────────────────────────────────────────────────┐
│                    V28.0 流水线三阶段                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │  阶段 1: L2 统计数据提取                                  │ │
│  │  - 从 raw_match_data 表读取 JSONB 数据                   │ │
│  │  - 使用 MultiPathExtractor 提取统计数据                   │ │
│  │  - UPSERT 到 match_features_training 表                  │ │
│  └───────────────────────────────────────────────────────────┘ │
│                           ↓                                     │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │  阶段 2: 滚动特征计算 (时间对齐)                          │ │
│  │  - 创建临时历史统计表                                    │ │
│  │  - 严格 match_date < current_match_date                  │ │
│  │  - 计算滚动窗口统计 (xG, shots, possession, rating)      │ │
│  └───────────────────────────────────────────────────────────┘ │
│                           ↓                                     │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │  阶段 3: 合并与报告                                      │ │
│  │  - 计算填充率                                            │ │
│  │  - 生成执行报告                                          │ │
│  │  - 验证 80% 填充率目标                                    │ │
│  └───────────────────────────────────────────────────────────┘ │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

#### 时间隔离安全约束

**核心原则**：严格防止数据泄露

```python
# 滚动特征计算 SQL 示例
SELECT AVG(hm.home_xg)
FROM tmp_l2_stats hm
WHERE hm.home_team = mft.home_team
  AND hm.match_date < (  # 严格小于！
      SELECT m.match_date
      FROM matches m
      WHERE m.match_id = mft.match_id::text
  )
ORDER BY hm.match_date DESC
LIMIT 5
```

**保证**：
- 只使用 `match_date` 严格早于当前比赛的历史数据
- 避免使用未来信息（当前比赛的数据）预测当前比赛
- 符合机器学习时间序列交叉验证原则

#### 关键类

| 类名 | 职责 |
|------|------|
| `PipelineConfig` | 流水线配置 (batch_size, rolling_window) |
| `PipelineReport` | 执行报告 (成功率、填充率、路径分布) |
| `V28FeaturePipeline` | 核心流水线实现 |

---

## 使用示例

### 基本用法

```python
from src.database.db_pool import SyncDatabasePool
from src.data_engineering.feature_pipeline import V28FeaturePipeline

# 初始化数据库连接池
db_pool = SyncDatabasePool()

# 创建流水线实例
pipeline = V28FeaturePipeline(db_pool)

# 执行完整流水线
report = pipeline.run_full_pipeline()

# 查看报告
print(f"总处理: {report.total_processed}")
print(f"成功率: {report.successful_extractions / report.total_processed * 100:.2f}%")
print(f"平均填充率: {sum(report.fill_rates.values()) / len(report.fill_rates):.2f}%")
```

### 便捷函数

```python
from src.database.db_pool import SyncDatabasePool
from src.data_engineering.feature_pipeline import run_v28_pipeline

# 一键运行（使用默认配置）
db_pool = SyncDatabasePool()
report = run_v28_pipeline(db_pool, batch_size=500, rolling_window=5)
```

### 单独使用 MultiPathExtractor

```python
from src.data_engineering.multipath_extractor import MultiPathExtractor

# 创建提取器
extractor = MultiPathExtractor()

# 提取单场比赛统计
stats = extractor.extract_from_jsonb(
    match_id="123456",
    raw_data={"content": {"stats": {...}}},
    match_date="2024-01-15",
    home_team="Arsenal",
    away_team="Chelsea"
)

if stats.extraction_success:
    print(f"xG: {stats.home_xg} vs {stats.away_xg}")
    print(f"路径: {stats.extraction_path.value}")

# 获取提取报告
report = extractor.get_extraction_report()
print(f"成功率: {report['path_success_rates']}")
```

---

## 配置选项

### PipelineConfig 参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `batch_size` | 500 | 批量处理大小（内存优化） |
| `rolling_window` | 5 | 滚动窗口大小（场次） |
| `min_matches_required` | 3 | 最小历史场次要求 |
| `strict_temporal_isolation` | True | 严格时间隔离模式 |

---

## 数据库 Schema

### 输入表

**`raw_match_data`** - L2 原始 JSONB 数据
```
- match_id (TEXT, PK)
- raw_data (JSONB) - FotMob API 原始数据
```

**`matches`** - 比赛基础信息
```
- match_id (BIGINT, PK)
- match_date (DATE)
- home_team (TEXT)
- away_team (TEXT)
- home_score (INTEGER)
- away_score (INTEGER)
- is_finished (BOOLEAN)
```

### 输出表

**`match_features_training`** - 特征训练表
```
- match_id (BIGINT, PK)
- season (TEXT)
- match_date (DATE)
- home_team (TEXT)
- away_team (TEXT)

-- L2 统计特征
- home_xg, away_xg (FLOAT)
- home_possession, away_possession (FLOAT)
- home_shots, away_shots (INTEGER)
- home_shots_on_target, away_shots_on_target (INTEGER)
- home_passes, away_passes (INTEGER)
- home_team_rating, away_team_rating (FLOAT)

-- 滚动特征（时间对齐）
- rolling_xg_home, rolling_xg_away (FLOAT)
- rolling_shots_on_target_home, rolling_shots_on_target_away (FLOAT)
- rolling_possession_home, rolling_possession_away (FLOAT)
- rolling_team_rating_home, rolling_team_rating_away (FLOAT)
```

---

## 性能优化

### 批量处理

- 默认批次大小：500 条记录
- 内存自适应：根据系统资源调整
- 进度报告：每个批次完成后输出日志

### 索引优化

流水线自动创建临时表索引：
```sql
CREATE INDEX idx_tmp_date ON tmp_l2_stats(match_date);
CREATE INDEX idx_tmp_home ON tmp_l2_stats(home_team);
CREATE INDEX idx_tmp_away ON tmp_l2_stats(away_team);
```

### 连接池管理

- 使用 `SyncDatabasePool` 复用连接
- 自动连接释放和异常处理
- 支持事务管理和提交

---

## 错误处理

### 多路径降级

当核心路径失败时，自动降级到备用路径：

```
路径 1 (CORE_STATS) → 失败
    ↓
路径 2 (MATCH_FACTS) → 失败
    ↓
路径 3 (SCORE_STRING) → 失败
    ↓
返回部分数据（extraction_success=False）
```

### 日志记录

```python
import logging
logging.basicConfig(level=logging.INFO)

# 流水线会输出详细日志
# - 批次处理进度
# - 提取成功率
# - 路径分布统计
# - 填充率分析
```

---

## 质量保证

### Mypy 类型检查

```bash
# 验证类型注解完整性
mypy src/data_engineering/
# 预期结果：0 Errors
```

### Pytest 单元测试

```bash
# 运行 data_engineering 测试
pytest tests/data_engineering/ -v
```

### CI/CD 集成

- 代码格式化：Ruff
- 类型检查：Mypy
- 单元测试：pytest
- 覆盖率目标：≥ 40%

---

## 版本历史

| 版本 | 日期 | 核心变更 |
|------|------|----------|
| **V28.0** | 2025-12-27 | 生产级特征提取与时间对齐流水线 |
| V27.0 | - | 预留版本 |
| V26.1 | 2025-12-27 | 零缺陷收割流水线 |

---

## 作者与维护

- **作者**: Senior Data Engineer
- **版本**: V28.0
- **日期**: 2025-12-27
- **状态**: Production Ready

---

## 相关文档

- [CLAUDE.md](../../CLAUDE.md) - 项目主文档
- [src/database/db_pool.py](../database/db_pool.py) - 连接池管理
- [tests/data_engineering/](../../tests/data_engineering/) - 单元测试
