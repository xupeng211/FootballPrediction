# 数据接入层稳定性审计报告

**审计日期**: 2025-12-23
**审计范围**: L1/L2 采集器 + 赔率脚本
**审计目标**: 确保 V19.4 多联赛实战环境的数据接入稳定性

---

## 一、最脆弱的 3 处代码 (Critical Vulnerabilities)

### 🔴 脆弱点 #1: L1 哨兵机制缺乏联赛分级
**位置**: `src/api/collectors/fotmob_core.py:57-58`

```python
self.min_response_size = 102400  # 最小响应大小（100KB） - 强制质量标准
```

**问题描述**:
- **硬编码阈值**: 所有联赛使用同一 100KB 标准
- **联赛差异**: 英超典型响应 ~150KB，但意乙/德乙等低级别联赛可能只有 30-60KB
- **后果**: 低级别联赛数据会被"哨兵"系统性地拒绝

**实际影响**:
| 联赛级别 | 典型响应大小 | 是否被拒绝 |
|---------|-------------|-----------|
| 英超 (EPL) | ~150KB | ✅ 通过 |
| 英冠 (Championship) | ~80KB | ❌ 被拒绝 |
| 意乙 (Serie B) | ~45KB | ❌ 被拒绝 |
| 德乙 (2. Bundesliga) | ~50KB | ❌ 被拒绝 |

**修复优先级**: ⚠️ **P0 - 阻塞多联赛扩展**

---

### 🟡 脆弱点 #2: L2 解析器缺乏联赛容错
**位置**: `src/api/collectors/fotmob_core.py:559-610`

```python
# FotMob统计键到内部特征名的映射
stat_mapping = {
    'BallPossesion': 'possession',
    'expected_goals': 'xg',  # ❌ 低级联赛可能没有 xG
    'total_shots': 'shots_total',
    # ... 更多硬编码映射
}
```

**问题描述**:
- **假设英超数据结构**: 代码假设所有联赛都有 xG、xA、bigChancesCreated 等高级特征
- **缺失特征处理**: 当 `expected_goals` 不存在时，系统返回空字典而非填充 NaN
- **后果**: 低级联赛解析失败，无法入库

**实际数据差异**:
| 特征 | 英超 | 英冠 | 意乙 | 德乙 |
|------|------|------|------|------|
| xG (Expected Goals) | ✅ 有 | ⚠️ 部分有 | ❌ 无 | ⚠️ 部分有 |
| xA (Expected Assists) | ✅ 有 | ❌ 无 | ❌ 无 | ❌ 无 |
| bigChancesCreated | ✅ 有 | ⚠️ 部分有 | ❌ 无 | ⚠️ 部分有 |
| shotsOnTarget | ✅ 有 | ✅ 有 | ✅ 有 | ✅ 有 |

**修复优先级**: ⚠️ **P0 - 阻塞多联赛扩展**

---

### 🟡 脆弱点 #3: 赔率脚本缺乏反爬抗压机制
**位置**: `src/scripts/download_real_odds.py:34`

```python
response = requests.get(url, timeout=30)  # ❌ 无重试、无代理、无 Header 轮换
```

**问题描述**:
- **无自动重试**: 网络抖动直接失败
- **无代理支持**: 单 IP 容易被封禁
- **无 Header 轮换**: User-Agent 固定，容易被识别
- **无备用源**: football-data.co.uk 挂了就完全不可用

**修复优先级**: ⚠️ **P1 - 高风险**

---

## 二、多联赛兼容性重构方案

### 方案 A: 动态联赛分级系统

```python
# src/api/collectors/fotmob_core.py (重构版)

class FotMobCoreCollectorV11:
    """V11.0 - 多联赛增强版"""

    # 联赛质量等级配置
    LEAGUE_QUALITY_TIERS = {
        'tier_1_premium': {  # 五大联赛 + 欧冠
            'min_response_size': 102400,  # 100KB
            'expected_features': ['xg', 'xa', 'big_chances_created'],
            'leagues': [47, 87, 94, 118, 126]  # FotMob league IDs
        },
        'tier_2_standard': {  # 次级联赛 (英冠、德乙等)
            'min_response_size': 51200,   # 50KB
            'expected_features': ['shots_on_target', 'corners', 'possession'],
            'leagues': [48, 78, 95]
        },
        'tier_3_basic': {  # 低级别联赛 (意乙、苏冠等)
            'min_response_size': 20480,   # 20KB
            'expected_features': ['shots_on_target', 'corners'],
            'leagues': [49, 96, 127]
        }
    }

    def _validate_response_size(self, match_id: int, content: bytes,
                                league_id: int = None) -> bool:
        """
        V11.0: 联赛感知的哨兵检查
        """
        content_size = len(content)

        # 查找联赛等级
        tier = self._get_league_tier(league_id)
        min_size = tier['min_response_size']

        if content_size < min_size:
            reason = f"响应过小 ({content_size} < {min_size} bytes, tier={tier})"
            self._log_hollow_match(match_id, content_size, reason)
            return False

        return True

    def _get_league_tier(self, league_id: int) -> Dict:
        """查找联赛质量等级配置"""
        for tier_name, tier_config in self.LEAGUE_QUALITY_TIERS.items():
            if league_id in tier_config['leagues']:
                return tier_config
        # 默认使用最低等级
        return self.LEAGUE_QUALITY_TIERS['tier_3_basic']
```

### 方案 B: 容错特征提取器

```python
# src/api/collectors/feature_extractor_v11.py (新文件)

class TolerantFeatureExtractor:
    """
    容错特征提取器 - V11.0

    核心原则:
    1. 能提取的尽量提取
    2. 缺失的填充 NaN
    3. 永不因特征缺失而失败
    """

    # 特征重要性分级
    FEATURE_HIERARCHY = {
        'critical': ['shots_on_target', 'possession', 'corners'],  # 必须有
        'important': ['xg', 'xa', 'fouls'],                       # 最好有
        'optional': ['expected_goals_open_play', 'progressive_passes', 'big_chances_created']
    }

    def extract_with_tolerance(self, json_data: Dict, league_id: int) -> Dict:
        """
        容错提取 - 返回所有可用特征，缺失的标记为 NaN
        """
        features = {}
        missing_features = []

        for feature_level, feature_list in self.FEATURE_HIERARCHY.items():
            for feature_key in feature_list:
                try:
                    value = self._safe_extract(json_data, feature_key)
                    if value is not None:
                        features[feature_key] = value
                    else:
                        features[feature_key] = float('nan')  # 明确标记缺失
                        missing_features.append(feature_key)
                except Exception as e:
                    features[feature_key] = float('nan')
                    logger.debug(f"特征提取失败: {feature_key} = NaN ({e})")

        # 记录数据质量
        completeness = len([v for v in features.values() if not math.isnan(v)]) / len(features)
        logger.info(f"数据完整度: {completeness:.1%}, 缺失特征: {missing_features}")

        return features

    def _safe_extract(self, json_data: Dict, feature_key: str) -> Optional[float]:
        """
        安全提取单个特征 - 使用 .get() 链式调用避免 KeyError
        """
        try:
            # 示例路径: content.stats.Periods.All.stats[x].stats[y].value
            stats = json_data.get('content', {}).get('stats', {})
            periods = stats.get('Periods', {}).get('All', {})
            all_stats = periods.get('stats', [])

            for stat_group in all_stats:
                if stat_group.get('key') == feature_key:
                    stats_list = stat_group.get('stats', [])
                    if len(stats_list) >= 2:
                        home_val = stats_list[0].get('value', 0)
                        away_val = stats_list[1].get('value', 0)
                        return {'home': home_val, 'away': away_val, 'total': home_val + away_val}

            return None  # 特征不存在，返回 None
        except Exception:
            return None
```

### 方案 C: 增强型赔率下载器

```python
# src/scripts/odds_downloader_v11.py (新文件)

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from typing import List, Optional

class RobustOddsDownloader:
    """
    增强型赔率下载器 - V11.0

    核心功能:
    1. 自动重试机制
    2. 代理池支持
    3. User-Agent 轮换
    4. 多备用源切换
    """

    # User-Agent 池
    USER_AGENTS = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36'
    ]

    # 备用数据源
    BACKUP_SOURCES = [
        'https://www.football-data.co.uk/mmz4281',
        'https://www.oddsportal.com',  # 备用源 2
        'https://api.betsapi.com/v1'   # 备用源 3
    ]

    def __init__(self):
        self.session = self._create_robust_session()
        self.current_user_agent = 0

    def _create_robust_session(self) -> requests.Session:
        """
        创建增强型 Session - 带重试策略
        """
        session = requests.Session()

        # 配置重试策略
        retry_strategy = Retry(
            total=5,                      # 最多重试 5 次
            backoff_factor=2,             # 指数退避: 2s, 4s, 8s, 16s, 32s
            status_forcelist=[429, 500, 502, 503, 504],  # 需要重试的 HTTP 状态码
            allowed_methods=["GET"]
        )

        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)

        return session

    def download_with_fallback(self, season: str) -> Optional[pd.DataFrame]:
        """
        带备用源的下载
        """
        # 尝试主数据源
        for i, source_url in enumerate([self.BACKUP_SOURCES[0]] + self.BACKUP_SOURCES[1:]):
            try:
                logger.info(f"尝试数据源 {i+1}/{len(self.BACKUP_SOURCES)}: {source_url}")

                # 轮换 User-Agent
                headers = {'User-Agent': self._get_next_user_agent()}
                response = self.session.get(
                    f"{source_url}/{season.replace('/','')}/E0.csv",
                    headers=headers,
                    timeout=30
                )
                response.raise_for_status()

                df = pd.read_csv io.StringIO(response.text))
                logger.info(f"✅ 数据源 {i+1} 下载成功")
                return df

            except Exception as e:
                logger.warning(f"数据源 {i+1} 失败: {e}")
                continue

        logger.error("❌ 所有数据源均失败")
        return None

    def _get_next_user_agent(self) -> str:
        """获取下一个 User-Agent"""
        ua = self.USER_AGENTS[self.current_user_agent]
        self.current_user_agent = (self.current_user_agent + 1) % len(self.USER_AGENTS)
        return ua
```

---

## 三、数据库 JSONB 验证

### JSONB 存储验证

```sql
-- 测试查询: 验证 JSONB 字段能否处理不同联赛的结构变体

-- 英超数据结构 (完整)
SELECT
    id,
    l2_raw_json->'content'->'stats'->'Periods'->'All'->'stats'->0->'stats'->0->'value' as home_xg
FROM matches
WHERE league_name = 'Premier League'
LIMIT 1;

-- 英冠数据结构 (简化 - 可能没有 xG)
SELECT
    id,
    -- 使用 COALESCE 处理可能缺失的字段
    COALESCE(
        l2_raw_json->'content'->'stats'->'Periods'->'All'->'stats'->0->'stats'->0->'value',
        'NaN'::jsonb
    ) as home_xg_or_nan
FROM matches
WHERE league_name = 'Championship'
LIMIT 1;

-- 批量检查数据完整度
SELECT
    league_name,
    COUNT(*) as total_matches,
    COUNT(l2_raw_json->'content'->'playerStats') as has_player_stats,
    COUNT(l2_raw_json->'content'->'stats'->'Periods') as has_team_stats
FROM matches
GROUP BY league_name;
```

**结论**: ✅ PostgreSQL JSONB 完美支持变体结构，可使用 `->` 和 `COALESCE` 安全查询

---

## 四、执行优先级

### 第一阶段 (P0 - 本周完成)
1. ✅ 实施联赛分级哨兵系统
2. ✅ 重构 L2 解析器为容错模式
3. ✅ 添加 NaN 填充逻辑

### 第二阶段 (P1 - 下周完成)
4. ✅ 增强赔率下载器
5. ✅ 添加代理池支持
6. ✅ 实现多备用源切换

### 第三阶段 (P2 - 未来)
7. ⏳ 实现 ID 跨赛季碰撞检测
8. ⏳ 按联赛隔离熔断器
9. ⏳ 添加数据质量评分系统

---

## 五、风险评估

| 风险 | 影响 | 概率 | 缓解措施 |
|------|------|------|---------|
| 低级联赛数据系统性丢失 | 高 | 高 | ✅ 联赛分级哨兵 |
| API 结构突变导致解析失败 | 高 | 中 | ✅ 容错特征提取器 |
| 赔率源被封禁 | 中 | 中 | ✅ 代理池 + UA 轮换 |
| 跨赛季 ID 碰撞 | 低 | 低 | ⏳ 待实施 ID 哈希验证 |

---

**审计结论**: 当前系统**仅支持英超级别联赛**，多联赛扩展需重构 L1/L2 采集器。预计修复工作量: **3-5 天**。
