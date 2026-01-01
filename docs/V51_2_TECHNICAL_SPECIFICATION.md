# V51.2 赔率组件接入技术规格书
**Technical Specification for Odds Integration - V51.2**

---

**版本**: V51.2
**发布日期**: 2025-12-31
**状态**: Design Review
**作者**: Senior Quant Architect & Data Engineer

---

## 目录

1. [执行摘要](#1-执行摘要)
2. [背景与目标](#2-背景与目标)
3. [系统架构](#3-系统架构)
4. [数据库设计](#4-数据库设计)
5. [实体对齐方案](#5-实体对齐方案)
6. [Docker 容器化](#6-docker-容器化)
7. [价值计算逻辑](#7-价值计算逻辑)
8. [实施路线图](#8-实施路线图)
9. [风险评估](#9-风险评估)
10. [附录](#10-附录)

---

## 1. 执行摘要

### 1.1 核心问题

V51.1 系统已完成 9,000+ 场比赛的竞技特征提取，但缺乏真实市场赔率数据，无法计算：

- **真实 ROI** (Return on Investment)
- **Expected Value** (期望值)
- **Kelly Criterion** 最优下注比例

### 1.2 解决方案

引入 **OddsPortal** 历史赔率数据作为 V51.2 的核心补丁：

| 组件 | 描述 | 状态 |
|------|------|------|
| `team_name_mapping` 表 | 解决 FotMob vs OddsPortal 球队名不统一 | 📋 已设计 |
| `prematch_features` 扩展 | 添加初赔/终赔字段 | 📋 已设计 |
| Odds Scraper 服务 | Playwright 容器化采集器 | 📋 已设计 |
| EV Calculator | 价值投注计算引擎 | ✅ 已实现 |

### 1.3 预期收益

| 指标 | V51.1 (当前) | V51.2 (目标) |
|------|-------------|-------------|
| 特征维度 | 49 维 (纯竞技) | **69 维** (+20 赔率特征) |
| ROI 可计算性 | ❌ 否 | ✅ 是 |
| 价值投注识别 | ❌ 否 | ✅ 是 |
| Kelly Criterion 支持 | ❌ 否 | ✅ 是 |

---

## 2. 背景与目标

### 2.1 当前系统状态

**V51.1 架构**:
```
FotMob API → L1/L2 → V25.1 特征提取 → prematch_features (49维) → XGBoost 训练
```

**核心痛点**:
- 无法验证模型在真实市场环境下的盈利能力
- 无法识别"价值投注"机会
- 无法进行资金管理 (Kelly Criterion)

### 2.2 V51.2 目标

1. **无损接入**: 确保 9,000+ 场数据与赔率数据 100% 准确接头
2. **解耦设计**: 采集器作为独立 Docker 服务，不污染 ML 环境
3. **可扩展性**: 支持未来接入其他赔率源 (Bet365, Pinnacle)

### 2.3 设计原则

| 原则 | 说明 | 优先级 |
|------|------|--------|
| 解耦 | Scraper 与 ML 运行环境完全隔离 | P0 |
| 一致性 | 通过 Entity Mapping 表统一球队名 | P0 |
| 无损 | 数据接头准确率 100% | P0 |
| 可扩展 | 支持多数据源接入 | P1 |

---

## 3. 系统架构

### 3.1 整体架构图

```
┌─────────────────────────────────────────────────────────────────┐
│                        V51.2 系统架构                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────────┐    ┌──────────────────┐                  │
│  │ FotMob API       │    │ OddsPortal       │                  │
│  │ (L1/L2 竞技数据) │    │ (历史赔率)       │                  │
│  └────────┬─────────┘    └────────┬─────────┘                  │
│           │                       │                             │
│           ▼                       ▼                             │
│  ┌──────────────────┐    ┌──────────────────┐                  │
│  │ V25.1 Extractor  │    │ Odds Scraper     │                  │
│  │ (642维特征)      │    │ (Playwright)     │                  │
│  └────────┬─────────┘    └────────┬─────────┘                  │
│           │                       │                             │
│           ▼                       ▼                             │
│  ┌──────────────────┐    ┌──────────────────┐                  │
│  │ prematch_features│◄───┤ team_name_mapping│ (实体对齐)        │
│  │ (49维 → 69维)    │    └──────────────────┘                  │
│  └────────┬─────────┘                                           │
│           │                                                     │
│           ▼                                                     │
│  ┌──────────────────┐    ┌──────────────────┐                  │
│  │ XGBoost Model    │───▶│ EV Calculator     │                  │
│  │                 │    │ (价值投注)       │                  │
│  └──────────────────┘    └──────────────────┘                  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 3.2 数据流

**阶段 1: 实体对齐**
```
scripts/ml/v51_2_team_mapping_generator.py
  ↓
1. 提取所有 FotMob 球队名
  ↓
2. RapidFuzz 模糊匹配 OddsPortal 标准队名
  ↓
3. 生成 team_name_mapping 表 (标记置信度 <90% 需人工审核)
  ↓
4. 输出审计报告 (Markdown + SQL)
```

**阶段 2: 赔率采集**
```
odds_scraper Docker 服务
  ↓
1. 使用 Playwright 访问 OddsPortal
  ↓
2. 按 team_name_mapping 转换球队名
  ↓
3. 提取 Opening/Closing Odds
  ↓
4. UPSERT 到 match_odds 表
```

**阶段 3: 特征合并**
```
prematch_features 表扩展
  ↓
1. 新增 opening_h/d/a, closing_h/d/a 字段
  ↓
2. 关联 match_odds 表填充赔率数据
  ↓
3. 计算隐含概率、赔率变动特征
  ↓
4. 调用 EV Calculator 计算价值指标
```

---

## 4. 数据库设计

### 4.1 team_name_mapping 表

**用途**: 解决 FotMob 与 OddsPortal 球队命名不统一问题

**DDL**:
```sql
CREATE TABLE IF NOT EXISTS team_name_mapping (
    id SERIAL PRIMARY KEY,
    fotmob_name VARCHAR(200) NOT NULL UNIQUE,
    fotmob_league VARCHAR(100),
    oddsportal_name VARCHAR(200) NOT NULL,
    oddsportal_league VARCHAR(100),
    confidence_score FLOAT CHECK (confidence_score BETWEEN 0 AND 100),
    needs_review BOOLEAN DEFAULT FALSE,
    mapping_status VARCHAR(20) DEFAULT 'pending',  -- pending, approved, rejected
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    reviewed_by VARCHAR(100),
    reviewed_at TIMESTAMP WITH TIME ZONE,
    notes TEXT
);

CREATE INDEX idx_team_mapping_fotmob ON team_name_mapping(fotmob_name);
CREATE INDEX idx_team_mapping_status ON team_name_mapping(mapping_status, needs_review);
```

**数据示例**:
| fotmob_name | oddsportal_name | confidence_score | needs_review |
|-------------|-----------------|------------------|--------------|
| Arsenal FC | Arsenal | 100.0 | FALSE |
| Man Utd | Man United | 95.5 | FALSE |
| Spurs | Tottenham | 92.0 | FALSE |
| Nottm Forest | Nottingham Forest | 88.5 | **TRUE** |

### 4.2 prematch_features 表扩展

**新增字段 (20个)**:

| 类别 | 字段名 | 类型 | 说明 |
|------|--------|------|------|
| 初赔 | `opening_home_odds` | FLOAT | 初盘主胜赔率 |
| 初赔 | `opening_draw_odds` | FLOAT | 初盘平局赔率 |
| 初赔 | `opening_away_odds` | FLOAT | 初盘客胜赔率 |
| 终赔 | `closing_home_odds` | FLOAT | 终盘主胜赔率 |
| 终赔 | `closing_draw_odds` | FLOAT | 终盘平局赔率 |
| 终赔 | `closing_away_odds` | FLOAT | 终盘客胜赔率 |
| 隐含概率 | `market_implied_prob_home` | FLOAT | 1/closing_home_odds |
| 隐含概率 | `market_implied_prob_draw` | FLOAT | 1/closing_draw_odds |
| 隐含概率 | `market_implied_prob_away` | FLOAT | 1/closing_away_odds |
| 赔率变动 | `odds_movement_home` | FLOAT | (closing-opening)/opening |
| 价值投注 | `ev_home` | FLOAT | 期望值 (主胜) |
| 价值投注 | `ev_draw` | FLOAT | 期望值 (平局) |
| 价值投注 | `ev_away` | FLOAT | 期望值 (客胜) |
| Kelly | `kelly_home` | FLOAT | Kelly Criterion |
| 推荐 | `value_bet_outcome` | VARCHAR(10) | home/draw/away/null |
| 推荐 | `value_level` | VARCHAR(20) | negative/low/moderate/high/excellent |

**迁移脚本**: `scripts/sql/v51_2/00_add_prematch_odds_fields.sql`

---

## 5. 实体对齐方案

### 5.1 球队名映射生成器

**文件**: `scripts/ml/v51_2_team_mapping_generator.py`

**核心逻辑**:
```python
# 1. 提取所有 FotMob 球队
fotmob_teams = generator.extract_fotmob_teams()

# 2. RapidFuzz 模糊匹配
result = process.extractOne(
    fotmob_team,
    ODDSPORTAL_ALL_TEAMS,
    scorer=fuzz.WRatio  # 对缩写、词序变化鲁棒
)

# 3. 置信度分类
if confidence_score >= 90:
    mapping_status = "approved"
elif confidence_score >= 70:
    mapping_status = "pending"
    needs_review = True
else:
    # 未匹配，记录到审计报告
```

**输出文件**:
| 文件 | 路径 | 说明 |
|------|------|------|
| DDL | `scripts/sql/v51_2/01_create_team_mapping_table.sql` | 表结构 |
| INSERT | `scripts/sql/v51_2/02_insert_team_mappings.sql` | 映射数据 |
| 审计报告 | `scripts/sql/v51_2/03_team_mapping_audit_report.md` | 人工审核指南 |
| JSON | `scripts/sql/v51_2/team_mapping_data.json` | 程序化处理 |

### 5.2 OddsPortal 标准队名库

**英超 (20队)**:
```python
ODDSPORTAL_TEAMS_EPL = [
    "Arsenal", "Aston Villa", "Bournemouth", "Brentford", "Brighton",
    "Chelsea", "Crystal Palace", "Everton", "Fulham", "Liverpool",
    "Man City", "Man United", "Newcastle", "Nottingham Forest", "Tottenham",
    "West Ham", "Wolves", "Ipswich", "Leicester", "Southampton",
]
```

**西甲 (18队) + 德甲 (18队) + 法甲 (18队) + 意甲 (20队)**:
```python
ODDSPORTAL_ALL_TEAMS = (
    ODDSPORTAL_TEAMS_EPL +
    ODDSPORTAL_TEAMS_LALIGA +
    ODDSPORTAL_TEAMS_BUNDESLIGA +
    ODDSPORTAL_TEAMS_LIGUE1 +
    ODDSPORTAL_TEAMS_SERIEA
)  # 总计 94 支标准球队
```

### 5.3 人工审核流程

**Step 1**: 运行映射生成器
```bash
python scripts/ml/v51_2_team_mapping_generator.py
```

**Step 2**: 查看审计报告
```bash
cat scripts/sql/v51_2/03_team_mapping_audit_report.md
```

**Step 3**: 执行 SQL
```bash
psql -U football_user -d football_prediction_dev \
  -f scripts/sql/v51_2/01_create_team_mapping_table.sql

psql -U football_user -d football_prediction_dev \
  -f scripts/sql/v51_2/02_insert_team_mappings.sql
```

**Step 4**: 审核并批准
```sql
-- 批准高置信度映射 (>85%)
UPDATE team_name_mapping
SET mapping_status = 'approved', needs_review = FALSE
WHERE confidence_score >= 85;

-- 手动批准特定映射
UPDATE team_name_mapping
SET mapping_status = 'approved', needs_review = FALSE,
    reviewed_by = 'your_name'
WHERE id = <mapping_id>;
```

---

## 6. Docker 容器化

### 6.1 odds_scraper 服务

**配置文件**: `docs/V51_2_DOCKER_COMPOSE_PATCH.yml`

**服务定义**:
```yaml
odds_scraper:
  build:
    context: .
    dockerfile: deploy/docker/Dockerfile
    target: runner
  image: footballprediction:v51.2-odds
  container_name: football_prediction_odds_scraper
  restart: unless-stopped
  environment:
    - ODDS_SCRAPER_SCHEDULE=${ODDS_SCRAPER_SCHEDULE:-0 */4 * * *}
    - ODDS_SOURCE=${ODDS_SOURCE:-oddsportal}
    - BATCH_SIZE=${ODDS_BATCH_SIZE:-50}
    - REQUEST_DELAY_MIN=${ODDS_DELAY_MIN:-2}
    - REQUEST_DELAY_MAX=${ODDS_DELAY_MAX:-5}
  volumes:
    - odds_data:/app/data/odds
  profiles:
    - odds
    - all
```

**启动方式**:
```bash
# 构建镜像
docker-compose build odds_scraper

# 启动服务
docker-compose --profile odds up -d

# 查看日志
docker-compose logs -f odds_scraper
```

### 6.2 Playwright 采集器

**文件**: `src/api/collectors/odds_scraper_playwright.py` (待实现)

**核心接口**:
```python
class OddsPortalScraper:
    async def collect_recent_matches(self) -> list[dict]:
        """采集最近比赛的赔率数据"""

    async def collect_match_odds(self, match_url: str) -> dict:
        """采集单场比赛赔率"""

    async def close(self):
        """关闭浏览器"""
```

**反爬虫策略**:
1. User-Agent 轮换 (继承 V37.0 UA_POOL)
2. 随机延迟 (2-5 秒)
3. 代理支持 (HTTP_PROXY 环境变量)
4. 请求限流 (100 req/min)

### 6.3 资源限制

| 资源 | 限制 | 说明 |
|------|------|------|
| CPU | 1 core | Playwright 浏览器运行 |
| Memory | 1GB | Chromium + Python |
| Storage | odds_data volume | 赔率数据持久化 |

---

## 7. 价值计算逻辑

### 7.1 EV (Expected Value) 计算

**文件**: `src/ml/features/value_bet_features.py`

**公式**:
```
EV = (Model_Probability × Market_Odds) - 1
```

**示例**:
| 结果 | 模型概率 | 市场赔率 | EV 计算 | EV 值 |
|------|----------|----------|---------|-------|
| 主胜 | 0.55 | 2.20 | (0.55 × 2.20) - 1 | **+21%** |
| 平局 | 0.25 | 3.40 | (0.25 × 3.40) - 1 | -15% |
| 客胜 | 0.20 | 3.80 | (0.20 × 3.80) - 1 | -24% |

**决策**: 主胜为正价值 (+21%)，建议投注

### 7.2 Kelly Criterion

**公式**:
```
Kelly = (Model_Prob × Odds - 1) / (Odds - 1)
Kelly_Conserative = Kelly × 0.25  # 保守策略
```

**示例**:
```
Kelly = (0.55 × 2.20 - 1) / (2.20 - 1) = 0.21 / 1.20 = 17.5%
Kelly_Conservative = 17.5% × 0.25 = 4.4%
```

**解释**: 建议下注 4.4% 的资金

### 7.3 价值等级分类

| EV 范围 | 等级 | 说明 |
|---------|------|------|
| EV < 0 | negative | 负价值，不建议投注 |
| 0% ≤ EV < 2% | low | 低价值 |
| 2% ≤ EV < 5% | moderate | 中等价值 |
| 5% ≤ EV < 10% | high | 高价值 |
| EV ≥ 10% | excellent | 极高价值 |

### 7.4 集成接口

```python
from src.ml.features.value_bet_features import calculate_value_gap

# 输入
model_probs = {"home": 0.55, "draw": 0.25, "away": 0.20}
market_odds = {"home": 2.20, "draw": 3.40, "away": 3.80}

# 计算
value_features = calculate_value_gap(model_probs, market_odds)

# 输出
print(value_features['ev_home'])        # 0.21 (21%)
print(value_features['kelly_home'])     # 0.044 (4.4%)
print(value_features['value_level_code'])  # 3 (high)
```

---

## 8. 实施路线图

### Phase 1: 数据库准备 (Week 1)

| 任务 | 脚本 | 预期时间 |
|------|------|----------|
| 创建 team_name_mapping 表 | `01_create_team_mapping_table.sql` | 5 分钟 |
| 生成球队映射 | `v51_2_team_mapping_generator.py` | 30 分钟 |
| 人工审核映射 | 审计报告 | 2-4 小时 |
| 扩展 prematch_features | `00_add_prematch_odds_fields.sql` | 5 分钟 |

### Phase 2: 赔率采集器 (Week 2)

| 任务 | 文件 | 预期时间 |
|------|------|----------|
| 实现 Playwright Scraper | `odds_scraper_playwright.py` | 1-2 天 |
| 集成到 docker-compose | `V51_2_DOCKER_COMPOSE_PATCH.yml` | 30 分钟 |
| 测试采集流程 | 手动验证 | 2 小时 |

### Phase 3: 特征计算 (Week 3)

| 任务 | 文件 | 预期时间 |
|------|------|----------|
| 实现填充脚本 | `fill_prematch_odds.py` | 1 天 |
| 运行 EV Calculator | `value_bet_features.py` | 已完成 |
| 验证数据质量 | SQL 查询 | 2 小时 |

### Phase 4: 模型重训练 (Week 4)

| 任务 | 说明 | 预期时间 |
|------|------|----------|
| 生成 V51.2 训练集 | 69 维特征 | 1 天 |
| 训练新 XGBoost 模型 | 包含赔率特征 | 2 小时 |
| 回测验证 | 计算 ROI | 1 天 |

---

## 9. 风险评估

### 9.1 技术风险

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| OddsPortal 封禁 IP | 高 | 1. 代理轮换 2. 请求限流 3. User-Agent 轮换 |
| 球队名匹配失败 | 中 | 1. RapidFuzz WRatio 2. 人工审核 |
| 数据接头不准确 | 高 | 1. Entity Mapping 表 2. 完整性检查 |

### 9.2 数据质量风险

| 风险 | 检测 | 处理 |
|------|------|------|
| 缺失赔率数据 | `WHERE closing_home_odds IS NULL` | 回退到历史平均值 |
| 异常赔率值 | `WHERE closing_home_odds < 1.1` | 标记为无效 |
| 初赔终赔倒置 | `opening < closing` | 数据清洗脚本 |

### 9.3 合规风险

| 风险 | 说明 |
|------|------|
| 数据采集合法性 | OddsPortal 为公开数据，但仍需遵守 robots.txt |
| 使用条款限制 | 仅用于个人研究，不商用 |

---

## 10. 附录

### A. SQL 迁移脚本

**创建 team_name_mapping 表**: 见 `scripts/sql/v51_2/01_create_team_mapping_table.sql`

**扩展 prematch_features 表**: 见 `scripts/sql/v51_2/00_add_prematch_odds_fields.sql`

### B. RapidFuzz 匹配参数

| 参数 | 值 | 说明 |
|------|-----|------|
| Scorer | `fuzz.WRatio` | 加权比率，对缩写、词序鲁棒 |
| 阈值 (自动批准) | ≥90 | 无需人工审核 |
| 阈值 (待审核) | 70-89 | 需要人工审核 |
| 阈值 (失败) | <70 | 视为未匹配 |

### C. 环境变量配置

```bash
# .env 文件新增配置
ODDS_SCRAPER_SCHEDULE="0 */4 * * *"  # 每4小时执行一次
ODDS_SOURCE="oddsportal"              # 数据源
ODDS_BATCH_SIZE=50                    # 批处理大小
ODDS_DELAY_MIN=2                      # 请求延迟 (秒)
ODDS_DELAY_MAX=5

HTTP_PROXY=http://proxy.example.com:8080  # 可选代理
HTTPS_PROXY=http://proxy.example.com:8080
```

### D. Docker 命令参考

```bash
# 构建
docker-compose build odds_scraper

# 启动
docker-compose --profile odds up -d

# 查看日志
docker-compose logs -f odds_scraper

# 停止
docker-compose --profile odds down

# 重启
docker-compose restart odds_scraper
```

---

## 版本历史

| 版本 | 日期 | 变更 |
|------|------|------|
| V51.2 | 2025-12-31 | 初始版本 |

---

**文档维护**: ML Platform Team
**最后更新**: 2025-12-31
