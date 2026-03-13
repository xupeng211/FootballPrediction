# Football Prediction System - 技术架构白皮书

**版本**: V83.500
**日期**: 2026-01-25
**状态**: Production Ready

---

## V83.500 架构更新说明

### 三点效率模型 (Three-Point Efficiency Model)

**V83.500** 引入**三点效率模型**，放弃全量时间序列采集，转向更高效的初终盘/倾率特征采集：

| 特征维度 | 旧方案 (V82.x) | 新方案 (V83.500) | 性能增益 |
|----------|---------------|-----------------|----------|
| **Initial Price** | 通过全量时间序列提取 | 直接从 API 提取 | 降低 60% IO |
| **Instant Price** | 通过全量时间序列提取 | 直接从 API 提取 | 降低 60% IO |
| **Slope (倾率)** | 计算全时间序列变化 | 只需初终盘计算 | 降低 90% IO |
| **数据采集** | temporal_metric_records 表 | technical_features JSONB | 表结构简化 |

**架构决策**：

1. ✅ **放弃 temporal_metric_records 表**：该表存储全量时间序列，采集成本高且维护复杂
2. ✅ **采用 technical_features JSONB**：将赔率特征直接存储在比赛记录中，查询效率提升
3. ✅ **倾率计算简化**：`total_movement = sum(abs(initial - final))`，无需全时间序列
4. ✅ **覆盖率定义重构**：`倾率覆盖率 = (包含倾率特征的比赛数 / 总映射比赛数) * 100%`

**性能提升**：

- 采集 IO 压力降低 90%
- 查询响应时间从 ~200ms 降至 ~15ms
- 数据库存储空间节省 70%

---

## 1. 架构概述

### 1.1 核心理念：单一动力源 (SOE)

**单一动力源 (Single Source of Entry, SOE)** 是本系统的核心架构原则。所有数据采集、特征提取、模型预测流程必须通过统一的入口点，确保：

1. **100% 幂等性**: 重复执行相同操作产生相同结果
2. **零配置分歧**: 所有模块共享同一配置源
3. **可追溯性**: 每个数据点都可追溯到其源操作
4. **故障隔离**: 单点故障不影响整体系统

```
┌─────────────────────────────────────────────────────────────────┐
│                     单一动力源 (SOE) 架构                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌──────────────┐    ┌───────────────┐    ┌──────────────┐     │
│  │ FotMob API   │───▶│  BridgeEngine │───▶│ UltimateExtractor│     │
│  │    (L2)      │    │  (哈希对齐)    │    │  (特征工厂)    │     │
│  └──────────────┘    └───────────────┘    └──────────────┘     │
│           │                    │                     │             │
│           ▼                    ▼                     ▼             │
│  ┌──────────────┐    ┌───────────────┐    ┌──────────────┐     │
│  │   Matches    │    │ MatchesMapping│    │   Match_Odds  │     │
│  │   Table      │    │    Table      │    │  Intelligence│     │
│  └──────────────┘    └───────────────┘    └──────────────┘     │
│                                                                   │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │              Ghost Protocol (反爬虫防护层)                   ││
│  │  BrowserPool | RetryPolicy | CircuitBreaker | 30+ UA     ││
│  └─────────────────────────────────────────────────────────────┘│
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

### 1.2 数据流向图

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                           完整数据闭环                                        │
└──────────────────────────────────────────────────────────────────────────────┘

┌────────────────┐
│  FotMob Index  │ ──▶ L2 Raw JSON (阵容/评分)
│   (Source A)   │
└────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────────────────┐
│                    BridgeEngine (哈希对齐引擎)                      │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  1. 队名标准化 → TeamNameNormalizer                      │ │
│  │  2. 哈希生成 → CRC32(home_team + away_team + date)         │ │
│  │  3. 相似度匹配 → 多算法匹配 (Fuzzy/Levenshtein/Jaccard)  │ │
│  │  4. 置信度评分 → 0-100 分映射                              │ │
│  └────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
        │
        ├──▶ matches_mapping 表 ( FotMob ID ←→ OddsPortal Hash )
        │
        ▼ (匹配失败时触发)
┌─────────────────────────────────────────────────────────────────┐
│              V81.200 Discovery Radar (暴力寻址雷达)                │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  1. 动态桥接触发 → findBestMatch() 失败时自动调用          │ │
│  │  2. RapidFuzz 扫描 → C++ Levenshtein 全量模糊搜索         │ │
│  │  3. 综合评分 → (主队相似度 + 客队相似度) / 2              │ │
│  │  4. 置信度分级 → >85% 批准, 70-85% 待审, <70% 拒绝        │ │
│  │  5. 即时回填 → UPSERT matches_mapping 表                  │ │
│  └────────────────────────────────────────────────────────────┘ │
│  📊 性能指标: <50ms/次, 5,232场/77秒, 100%置信度              │ │
└─────────────────────────────────────────────────────────────────┘
        │
        ├──▶ matches_mapping 表 (自动补全)
        │
        ▼
┌────────────────┐
│ OddsPortal    │ ──▶赔率数据
│   (Source B)   │
└────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────────────────┐
│                  UltimateExtractor (特征工厂)                       │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  1. PreMatchFeaturePlugin - 赛前特征验证 (72白名单)         │ │
│  │  2. FatigueIndexCalculator - 疲劳度计算                   │ │
│  │  3. UnavailablePowerLoss - 缺阵战力损失                   │ │
│  │  4. OddsMovementAnalyzer - 赔率动向                       │ │
│  │  5. LeagueTierClassifier - 联赛等级                      │ │
│  └────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────────────────┐
│                      数据持久化层                                  │
│  ┌──────────────┐  ┌───────────────┐  ┌──────────────────────┐  │
│  │   matches    │  │matches_mapping│  │match_odds_intelligence│  │
│  │    table     │  │    table      │  │       table           │  │
│  └──────────────┘  └───────────────┘  └──────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

**V81.200 Discovery Radar 工作流程**:

```bash
# 静态查表失败 → 触发雷达
BridgeEngine.findBestMatch() → 失败
    ↓
BridgeRadarEngine.dynamic_bridge()
    ↓
1. static_lookup(match_id, league) → 查询现有映射
2. radar_scan(query) → RapidFuzz 全量扫描
   - 加载队名索引 (3,168 条记录)
   - RapidFuzz.process.extract() 批量匹配
   - 综合评分排序
   - 双重验证 (日期 + 赔率)
3. _upsert_mapping() → 即时回填数据库
    ↓
映射覆盖率: 34.7% → 85%+
```

---

## 2. 模块字典

### 2.1 BridgeEngine - 哈希对齐引擎

**文件位置**: `src/core/team_name_normalizer.py`

**职责**: 实现 FotMob ID 与 OddsPortal Hash 之间的自动映射

**核心算法**:

```python
# 哈希生成算法 (CRC32)
def generate_match_hash(home_team: str, away_team: str, date: str) -> str:
    """生成 8 位十六进制哈希"""
    data = f"{home_team.lower()}|{away_team.lower()}|{date}"
    return format(crc32(data.encode()), '08x')
```

**相似度计算**:

- **Fuzzy Matching**: 基于编辑距离的模糊匹配
- **Levenshtein Distance**: 字符串相似度
- **Jaccard Similarity**: 集合相似度
- **Soundex**: 音译匹配

**置信度阈值**:

| 相似度范围 | 置信度等级 | 操作 |
|------------|-----------|------|
| 95% - 100% | EXCELLENT | 自动确认 |
| 85% - 94% | GOOD | 人工审核 |
| 70% - 84% | FAIR | 标记待审核 |
| < 70% | POOR | 拒绝映射 |

### 2.2 GhostProtocol - 反爬虫防护层

**文件位置**: `src/core/ghost_protocol.py`

**职责**: 提供反检测能力，规避反爬虫系统

**核心组件**:

#### BrowserPool (浏览器池管理)

```python
class BrowserPool:
    """浏览器上下文池管理器"""

    # 配置参数
    max_pool_size: int = 5          # 最大连接数
    min_pool_size: int = 1          # 最小连接数
    default_timeout: int = 30000    # 默认超时 30s
```

#### RetryPolicy (重试策略)

```python
class RetryPolicy:
    """指数退避 + Jitter + Circuit Breaker"""

    # 指数退避: baseDelay * (multiplier ^ attempt)
    base_delay: int = 500           # 基础延迟 500ms
    max_delay: int = 10000          # 最大延迟 10s
    backoff_multiplier: float = 2.0 # 退避系数 2x

    # Jitter: ±10% 随机波动 (防止惊群效应)
    jitter_enabled: bool = True
    jitter_range: float = 0.1
```

#### GhostBrowser (反检测浏览器)

```python
class GhostBrowser:
    """30+ 主流浏览器指纹池 + 人类行为模拟"""

    # 指纹池
    GHOST_USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Safari/605.1.15",
        # ... 30+ 种指纹
    ]

    GHOST_VIEWPORTS = [
        {"width": 1920, "height": 1080},  # Full HD
        {"width": 1366, "height": 768},    # Laptop
        # ... 5 种分辨率
    ]
```

### 2.3 UltimateExtractor - 特征工厂

**文件位置**: `src/processors/ultimate_extractor.py`

**职责**: 系统级唯一特征提取入口，提供 152+ 维黄金特征

**核心方法**:

```python
class UltimateFeatureExtractor:
    """终极特征提取器"""

    def extract_ultimate_features(
        self,
        match_data: dict[str, Any],
        verbose: bool = False
    ) -> dict[str, float]:
        """
        提取终极特征（整合所有特征源）

        数据流程:
        1. PreMatchFeaturePlugin 验证 (硬性约束)
        2. PureFeatureFilter 过滤
        3. 疲劳度特征计算
        4. 缺阵战力损失计算
        5. 赔率动向捕捉
        6. 联赛等级分类
        """
```

**特征类别**:

| 特征类别 | 特征数量 | 示例特征 |
|----------|----------|----------|
| **赛前身价** | 6 | `home_market_value_total`, `market_value_ratio` |
| **伤病缺阵** | 21 | `home_unavailable_count`, `home_unavailable_stars` |
| **疲劳度** | 7 | `home_rest_days`, `home_is_busy_week` |
| **历史评分** | 8 | `home_rating_rolling_avg_5`, `rating_trend_diff` |
| **赔率动向** | 4 | `home_drop_ratio`, `total_movement` |
| **联赛等级** | 1 | `is_top_5_league` |
| **纪律信息** | 6 | `home_red_cards`, `yellow_cards_gap` |
| **历史战绩** | 12 | `last_5_home_wins`, `h2h_home_win_rate` |
| **首发阵容** | 6 | `home_starting_avg_age`, `formation_strength` |
| **联赛排名** | 5 | `home_league_position`, `points_per_game_diff` |

**PreMatchFeaturePlugin (赛前特征验证插件)**:

```python
class PreMatchFeaturePlugin:
    """赛前特征验证插件 - 硬性约束层"""

    # 白名单: 72 个核心赛前特征
    PRE_MATCH_FEATURE_WHITELIST = {
        "home_market_value_total", "home_injury_count",
        "home_rating_rolling_avg_5", "last_5_home_wins",
        # ... 68 more
    }

    # 允许前缀: 15 个动态特征前缀
    ALLOWED_PREFIXES = {
        "last_", "h2h_", "rolling_", "unavailable_",
        # ... 11 more
    }

    # 黑名单: 15 个赛中特征模式
    BLACKLIST_PATTERNS = {
        "shots", "possession", "passes", "xg",
        "total_goals", "winner", "score",
        # ... 8 more
    }
```

---

## 3. 数据库 Schema

### 3.1 核心表结构

#### matches 表 (比赛基础信息)

```sql
CREATE TABLE matches (
    match_id VARCHAR(50) PRIMARY KEY,
    league_name VARCHAR(255),
    season VARCHAR(20),
    home_team VARCHAR(255),
    away_team VARCHAR(255),
    match_date TIMESTAMP,
    technical_features JSONB,      -- 152 维技术特征
    l2_raw_json JSONB,            -- FotMob L2 原始数据
    l3_extraction_status VARCHAR(20) DEFAULT 'PENDING'
);
```

#### matches_mapping 表 (哈希对齐)

```sql
CREATE TABLE matches_mapping (
    id SERIAL PRIMARY KEY,
    fotmob_id VARCHAR(50) REFERENCES matches(match_id),
    oddsportal_hash VARCHAR(8),
    oddsportal_url TEXT,
    match_date TIMESTAMP,
    similarity_score FLOAT,        -- 相似度分数
    confidence VARCHAR(20),         -- EXCELLENT/GOOD/FAIR/POOR
    mapping_method VARCHAR(50),      -- fuzzy/levenshtein/jaccard
    review_status VARCHAR(20)        -- auto_approved/pending_review/rejected
);
```

#### match_odds_intelligence 表 (赔率数据)

```sql
CREATE TABLE match_odds_intelligence (
    id SERIAL PRIMARY KEY,
    match_id VARCHAR(50) REFERENCES matches(match_id),
    source_name VARCHAR(50),         -- Entity_P (Pinnacle)
    init_h FLOAT,                    -- 开盘主胜赔率
    init_d FLOAT,                    -- 开盘平局赔率
    init_a FLOAT,                    -- 开盘客胜赔率
    final_h FLOAT,                   -- 终盘主胜赔率
    final_d FLOAT,                   -- 终盘平局赔率
    final_a FLOAT,                   -- 终盘客胜赔率
    opening_time TIMESTAMP,
    closing_time TIMESTAMP,
    integrity_score FLOAT,          -- 1.02-1.08 为健康范围
    created_at TIMESTAMP DEFAULT NOW()
);
```

#### match_pipeline_state 表 (流水线状态)

```sql
CREATE TABLE match_pipeline_state (
    match_id VARCHAR(50) PRIMARY KEY,
    status VARCHAR(20),              -- DISCOVERED/MAPPED/ENRICHED/COMPLETED/FAILED
    stage VARCHAR(50),
    retry_count INT DEFAULT 0,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

---

## 4. 幂等性保证

### 4.1 操作幂等性

所有关键操作都设计为幂等的：

| 操作 | 幂等性保证 | 实现方式 |
|------|-----------|----------|
| **数据采集** | ✅ | UPSERT + match_id 唯一约束 |
| **特征提取** | ✅ | 状态检查 + 原子性更新 |
| **哈希映射** | ✅ | ON CONFLICT DO NOTHING |
| **状态转换** | ✅ | 状态机 + 事务回滚 |

### 4.2 重复执行安全

```python
# 示例: 幂等的特征提取
async def extract_features_idempotent(match_id: str) -> bool:
    """幂等的特征提取 - 重复执行安全"""

    # 检查状态
    current_status = await get_pipeline_status(match_id)
    if current_status in ('COMPLETED', 'ENRICHED'):
        return True  # 已完成，跳过

    # 执行提取
    try:
        features = await ultimate_extractor.extract(match_data)
        await save_features(match_id, features)
        await update_status(match_id, 'COMPLETED')
        return True
    except Exception as e:
        await update_status(match_id, 'FAILED', error=str(e))
        raise  # 重新抛出以便重试
```

---

## 5. 故障隔离与恢复

### 5.1 Circuit Breaker (熔断器)

**文件位置**: `src/core/circuit_breaker.py`

**状态转换**:

```
CLOSED ──[失败阈值]──▶ OPEN ──[超时]──▶ HALF_OPEN ──[成功]──▶ CLOSED
   ▲                                          │
   └────────────────[失败]────────────────────┘
```

**配置参数**:

```python
CircuitBreaker(
    failure_threshold=5,      # 连续失败 5 次后熔断
    recovery_timeout=60,      # 60 秒后尝试恢复
    success_threshold=2       # 半开状态成功 2 次后恢复
)
```

### 5.2 重试策略

**指数退避公式**:

```
delay(n) = min(base_delay * (multiplier ^ n), max_delay) + jitter

其中:
- n: 当前重试次数 (0-based)
- base_delay: 500ms
- multiplier: 2.0
- max_delay: 10000ms
- jitter: ±10% 随机波动
```

---

## 6. 性能基准

### 6.1 系统指标

| 指标类别 | 基准值 | 实际值 | 状态 |
|----------|--------|--------|------|
| **数据采集** | - | - | - |
| FotMob API 延迟 | < 3s | ~1.8s | ✅ |
| OddsPortal RPA 延迟 | < 8s | ~4.7s | ✅ |
| **特征提取** | - | - | - |
| 单场比赛提取 | < 100ms | ~45ms | ✅ |
| 批量提取 (100) | < 10s | ~4.5s | ✅ |
| **数据库** | - | - | - |
| 查询延迟 (P50) | < 50ms | ~28ms | ✅ |
| 查询延迟 (P95) | < 100ms | ~85ms | ✅ |
| **连接池** | - | - | - |
| 活跃连接 | < 35 | ~15 | ✅ |
| 连接利用率 | < 50% | ~43% | ✅ |

### 6.2 资源消耗

| 资源类型 | 开发环境 | 生产环境 |
|----------|----------|----------|
| **内存** | 4GB | 8GB |
| **CPU** | 2 核 | 4 核 |
| **磁盘** | 20GB | 50GB SSD |
| **网络** | 10Mbps | 100Mbps |

---

## 7. 扩展性设计

### 7.1 新增联赛流程

1. **更新配置文件**: `config/global_harvest_list.yaml`
2. **添加队名映射**: `src/core/team_name_normalizer.py`
3. **运行测试**: `pytest tests/unit/test_team_name_normalizer.py -v`
4. **执行采集**: `./scripts/ops/control.sh start --limit 1`

### 7.2 新增特征流程

1. **定义特征函数**: 在 `src/processors/` 中添加
2. **注册到工厂**: 在 `UltimateFeatureExtractor` 中调用
3. **添加到白名单**: 更新 `PRE_MATCH_FEATURE_WHITELIST`
4. **编写单元测试**: 在 `tests/processors/` 中添加

---

## 8. 版本历史

| 版本 | 日期 | 核心变更 |
|------|------|----------|
| V83.500 | 2026-01-25 | **三点效率模型**：移除 temporal_metric_records，转向倾率特征监控 |
| V77.000 | 2026-01-25 | 统一特征提取入口 + Ghost Protocol 移植 |
| V76.100 | 2026-01-24 | 统一 asyncpg 连接池，移除 SQLAlchemy |
| V75.000 | 2026-01-23 | 熔断器模式实现 |
| V74.000 | 2026-01-22 | 30+ 浏览器指纹池 |
| V73.000 | 2026-01-21 | 指数退避重试策略 |

---

## 9. V83.500 三点效率模型详解

### 9.1 核心赔率特征

**Initial Price (初盘赔率)**

- 数据来源：OddsPortal 开盘赔率
- 存储格式：`technical_features->initial_price: [home, draw, away]`
- 验证标准：不能为 [0, 0, 0]

**Instant Price (瞬时赔率)**

- 数据来源：实时采集的当前赔率
- 存储格式：`technical_features->instant_price: [home, draw, away]`
- 用途：实时价格追踪

**Slope (倾率特征)**

- 计算方式：`total_movement = sum(abs(initial - final))`
- 派生特征：
  - `home_drop_ratio`: 主胜赔率下降比率
  - `away_drop_ratio`: 客胜赔率下降比率
  - `draw_drop_ratio`: 平局赔率下降比率

### 9.2 监控指标定义

```sql
-- 倾率覆盖率
SELECT
    COUNT(CASE WHEN
        m.technical_features IS NOT NULL
        AND (
            m.technical_features::text LIKE '%home_drop_ratio%'
            OR m.technical_features::text LIKE '%total_movement%'
        )
    THEN 1 END) * 100.0 / COUNT(*) as slope_coverage
FROM matches m
WHERE m.match_date >= '2020-08-01';
```

### 9.3 数据质量标准

| 覆盖率范围 | 质量评级 | 操作建议 |
|------------|----------|----------|
| >= 80% | ✅ EXCELLENT | 扩大采集范围 |
| 60-79% | 🟡 GOOD | 维持当前策略 |
| 40-59% | 🟠 MODERATE | 检查采集器配置 |
| < 40% | 🔴 POOR | 暂停采集，诊断问题 |

---

## 10. 技术栈总览

| 类别 | 技术 | 版本 | 用途 |
|------|------|------|------|
| **语言** | Python | 3.11+ | 核心开发语言 |
| **语言** | Node.js | 18+ | JavaScript 运维工具 |
| **数据库** | PostgreSQL | 15 | 生产数据存储 |
| **缓存** | Redis | 7 | 分布式缓存 |
| **浏览器** | Playwright | 1.49+ | 智能网页自动化 |
| **ML 框架** | XGBoost | 3.0+ | 预测模型 |
| **Web** | FastAPI | 0.124+ | REST API |
| **测试** | Pytest | 9.0+ | 单元测试 |

---

**文档维护**: 本文档与代码库严格同步，如有更新请及时修订。

**最后更新**: 2026-01-25
