# V7.0 Data Infrastructure SOP (Standard Operating Procedure)

**最后更新日期**: 2025-12-21
**适用版本**: V7.0+

本文档规范了 FootballPrediction 系统的数据获取与特征提取标准。所有后续开发必须严格遵守以下物理铁律。

## 1. 核心铁律 (Critical Mandates)

### 🚨 User-Agent 伪装是物理前提
FotMob API 具有严格的反爬虫机制。获取不到数据（或仅获取到几百字节的空壳 JSON）的根本原因通常是 User-Agent 被识别为机器人。
- **必须**在所有 API 请求头中包含真实的浏览器 User-Agent。
- **严禁**使用默认的 `aiohttp` 或 `requests` UA。

### 🛡️ BulletproofFeatureExtractor 是唯一的解析真相
所有特征提取逻辑必须收口于 `src/data_access/processors/bulletproof_feature_extractor.py`。
- **严禁**在脚本中散落临时的 `json.get` 逻辑。
- 提取器实现了多路径嗅探、动态容错和衍生特征自动计算，是数据质量的唯一保障。

## 2. 180 维特征体系 (Feature Schema)

V7.0 数据基座实现了 180 维特征的全量实心化（100% 填充率）。

### 📊 特征板块构成

| 板块 (Category) | 维度 (Dimensions) | 核心字段示例 | 数据来源 |
| :--- | :--- | :--- | :--- |
| **Meta (基础信息)** | 5+ | `match_time`, `home_team`, `score` | `general` / `header` |
| **Ratings (评分)** | 3+ | `home_avg_rating`, `rating_diff` | `content.lineup` |
| **Tactical (战术)** | 8+ | `big_chances`, `possession`, `shots` | `content.stats` |
| **xG (预期进球)** | 4+ | `home_xg`, `xg_per_shot` | `content.stats` |
| **Events (事件流)** | 8+ | `red_cards`, `penalties`, `early_goal` | `content.matchFacts` |
| **Derived (衍生)** | 40+ | `xg_efficiency`, `possession_dominance` | 自动计算 |

## 3. 数据运维 (Data Ops)

### 全量重采样 (The Great Re-Harvest)
当发现历史数据存在“空心化”现象时，应运行 `great_reharvest.py` (需集成到生产环境)。
- **逻辑**: 物理覆盖 `data/raw_json/` -> 调用 Extractor -> UPSERT 数据库。
- **策略**: 必须配合随机延迟 (2-5s) 以防止 IP 封禁。

### 质量审计 (Audit)
定期运行热力图生成脚本，确保核心指标（如 `home_avg_rating`）的非空率始终保持在 >95% 的水平。

---
**FootballPrediction Data Team**
*Building the Truth Engine*
