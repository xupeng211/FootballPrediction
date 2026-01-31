# 核心模块参考文档

本文档提供 FootballPrediction 项目核心模块的详细说明。

---

## 📋 目录

- [命令入口](#命令入口)
- [数据采集层](#数据采集层)
- [ML 引擎](#ml-引擎)
- [特征工程](#特征工程)
- [配置管理](#配置管理)
- [运维脚本](#运维脚本)

---

## 命令入口

### main.py - V144.7 Multi-Source Command Center

项目的主要入口点，提供统一命令行界面，支持多数据源路由。

#### 基本用法

```bash
# V144.7: 多数据源支持
python main.py --source fotmob --mode single --limit 10      # FotMob API 数据源
python main.py --source oddsportal --mode single --limit 10  # OddsPortal RPA 数据源
python main.py --source fotmob --mode cruise                 # FotMob 24h 巡航模式

# 单次收割模式
python main.py --mode single --league "Premier League" --season "23/24"

# 24h 全自动巡航模式
python main.py --mode cruise

# 数据质量检查
python main.py --mode check

# 测试代理 (V144.7)
python main.py --test-proxy

# 禁用 Ghost Protocol (调试用)
python main.py --mode single --no-ghost

# 限制处理数量
python main.py --mode single --limit 50

# 干跑模式 (不实际采集)
python main.py --mode single --dry-run
```

#### V144.7 新特性
- `--source` 参数支持数据源切换 (oddsportal/fotmob)
- 路由到 `run_oddsportal_mode()` 或 `run_fotmob_mode()` 处理器
- Ghost Protocol 统一验证日志

#### 环境预检功能
- WSL2 环境检测
- 代理自动发现 (环境变量 → WSL2 自动探测 → 直连)
- IP 地址检测
- 数据库连接检查
- 日志目录自动创建

---

## 数据采集层

### HarvesterService - V142.0 统一收割服务

位于 `src/api/services/harvester_service.py`，是数据收割的核心服务。

#### 基本用法

```python
from src.api.services.harvester_service import HarvesterService

service = HarvesterService(
    mode="single",              # single / cruise
    enable_ghost_protocol=True, # 启用 Ghost Protocol
    enable_queue=True,          # 启用队列系统
    limit=None,                 # 最大处理数量
    dry_run=False,              # 干跑模式
    proxy_file="proxies.txt"    # 代理配置文件
)
await service.run()
```

#### 核心特性
- 队列驱动架构 (match_search_queue)
- Ghost Protocol 集成 (BaseExtractor V141.0)
- 全路径试错匹配 (TeamNameNormalizer V140.0)
- 信号处理 (SIGINT/SIGTERM)
- 优雅关闭机制
- 流量弹性 (V142.5)

---

### BaseExtractor - V141.0 Ghost Protocol

位于 `src/api/collectors/base_extractor.py`，提供反爬检测基础能力。

#### 基本用法

```python
from src.api.collectors.base_extractor import BaseExtractor

extractor = BaseExtractor(auto_proxy=True)

# 获取随机 UA
ua = extractor.get_random_user_agent()

# 获取随机视口
viewport = extractor.get_random_viewport()

# 获取代理配置 (WSL2 自动发现)
proxy_config = extractor.get_proxy_config()

# 创建浏览器上下文
context = await browser.new_context(
    user_agent=ua,
    viewport=viewport,
    proxy=proxy_config
)
```

#### Ghost Protocol 特性
- 30+ 主流浏览器指纹池 (Chrome/Edge/Safari/Firefox)
- 5 种常见屏幕分辨率随机化
- 人类行为模拟 (滚动 + 点击噪声)
- 深度拦截检测 (Cloudflare, IP 封禁)
- 自动错误截图 (logs/error_screens/)
- WSL2 自动代理发现

---

### TeamNameNormalizer - V140.0 全路径试错匹配

位于 `src/utils/text_processor.py`，处理队名标准化和匹配。

#### 基本用法

```python
from src.utils.text_processor import TeamNameNormalizer

normalizer = TeamNameNormalizer()

# 标准化队名
normalized = normalizer.normalize_team_name("Manchester United")

# 全路径试错匹配
matched = normalizer.fuzzy_match_team_name(
    raw_name="man-utd",
    candidates=["Manchester United", "Manchester City", ...]
)
```

---

### OddsProductionExtractor - V82.6 统一提取引擎

位于 `src/api/collectors/odds_production_extractor.py`。

#### 基本用法

```python
from src.api.collectors.odds_production_extractor import OddsProductionExtractor

extractor = OddsProductionExtractor()

# L2: FotMob 开盘赔率 (悬停提取)
result = await extractor.extract_opening_via_hover(
    page=page,
    entity_code="Entity_P",
    match_date=datetime(2024, 4, 20)
)

# L3: OddsPortal 终盘赔率 (直接提取)
result = await extractor.extract_oddsportal_final_odds(
    url="https://www.oddsportal.com/match/...",
    match_id=12345
)
```

#### V82.6 核心修复
- 只选择 `.odds-text` 元素（排除 `.odds-cell`）
- 避免同一值被重复提取
- 正确提取主、平、客赔率

---

### FotMobHistoricalBackfill - V26.6 历史回填引擎

位于 `scripts/maintenance/fotmob_historical_backfill.py`。

#### 基本用法

```bash
# 回填所有启用的联赛（默认 3 年）
python scripts/maintenance/fotmob_historical_backfill.py

# 回填指定联赛
python scripts/maintenance/fotmob_historical_backfill.py --league-id 47 --years 5

# 干跑模式（不实际采集）
python scripts/maintenance/fotmob_historical_backfill.py --dry-run

# 禁用哨兵系统
python scripts/maintenance/fotmob_historical_backfill.py --no-sentry
```

#### 核心特性
- 自动发现历史比赛 ID（3-5 年）
- 批量采集比赛数据
- 哨兵系统集成（自动停机保护）
- 断点续传支持
- 干跑模式（测试用）

---

### V151.1 Retry + Hash Hunting Edition

V151.1 引入**重试机制**和**哈希狩猎**功能。

#### 核心架构

```
V151.1 Hash Hunting Engine
├── 从 matches 表找出缺失比赛
├── 使用 OddsPortalScraper.search_match_url() 搜索 URL
├── V151.3 哈希缓存保护（防止数据丢失）
└── 批量插入 matches_mapping 表

V151.3 Concurrent Harvester
├── 多进程并发采集（默认 3 进程）
├── 进程间代理隔离 (7890-7899)
├── 重试计数器（最多 3 次）
└── 自动放弃 (abandoned 状态)
```

#### 使用方法

```bash
# 搜索比赛 URL（通过队名）
python scripts/ops/hunt_league_hashes.py --leagues "La Liga" "Serie A" --limit 50

# 英超数据复活
python scripts/ops/hunt_league_hashes.py --premier

# V151.3: 同步缓存到数据库
python scripts/ops/hunt_league_hashes.py --sync-cache

# V151.3 并发收割器（3 进程保守方案）
python scripts/ops/harvest_pinnacle_concurrent.py --workers 3 --limit 100

# 10 进程激进方案
python scripts/ops/harvest_pinnacle_concurrent.py --workers 10 --limit 500
```

#### V151.1 核心特性
- **Hash Hunting**: 通过队名搜索自动发现 OddsPortal URL
- **重试机制**: retry_count 字段记录重试次数（最多 3 次）
- **自动放弃**: 超过 3 次失败后标记为 `abandoned` 状态
- **并发采集**: 多进程独立代理隔离，提升采集效率
- **缓存保护**: V151.3 哈希缓存防止数据库连接中断导致数据丢失

#### 数据库迁移

```bash
# V151.2: 英超数据"复活"
psql -U football_user -d football_db -f scripts/sql/v151_2_resurrect_premier_league.sql

# V151.3: 添加重试计数和放弃状态
psql -U football_user -d football_db -f scripts/sql/v151_3_add_retry_count.sql
```

#### 准入红线
**禁止在不使用 `matches` 表作为底座的情况下进行任何"抢救"工作！**

---

### V40 系列 DOM 收割器

V40 系列提供完整的 DOM 数据采集解决方案，位于 `scripts/ops/`。

#### 脚本清单

| 脚本 | 版本 | 功能 | 状态 |
|------|------|------|------|
| `v40_15_api_sniffer.py` | V40.15 | API 嗅探，发现 Archive API | ✅ 完成 |
| `v40_15_dom_extractor.py` | V40.15 | DOM 提取器，50 场/页 | ✅ 完成 |
| `v40_16_api_breaker.py` | V40.16 | API 破解尝试（失败） | ❌ 失败 |
| `v40_17_dom_harvester.py` | V40.17 | DOM 收割器（URL 解析 bug） | ⚠️ 部分成功 |
| `v40_18_vue_inspector.py` | V40.18 | Vue 检查器 | ✅ 完成 |
| `v40_19_pagination_clicker.py` | V40.19 | 分页点击器（30 场） | ⚠️ 部分成功 |
| `v40_20_pagination_research.py` | V40.20 | **分页研究（突破）** | ✅ **突破** |
| `v40_21_full_harvester.py` | V40.21 | 全量收割器（110 场，数据重复） | ⚠️ 部分成功 |
| `v40_22_improved_harvester.py` | V40.22 | **改进收割器（490 场）** | ✅ **成功** |
| `v40_24_import_fixed.py` | V40.24 | **数据入库（完成）** | ✅ **完成** |

#### 使用示例

```bash
# V40.22 改进收割器（推荐）
python scripts/ops/v40_22_improved_harvester.py --leagues "La Liga" "Ligue 1"

# V40.24 数据入库
python scripts/ops/v40_24_import_fixed.py --source logs/v40_22_improved_results.json

# 查看入库统计
docker-compose exec -T db psql -U football_user -d football_db -c "
SELECT league_name, season, COUNT(*) as total_matches
FROM matches_mapping
WHERE mapping_method = 'v40.22_dom_harvest'
GROUP BY league_name, season;
"
```

#### V40 核心特性
- ✅ **DOM 直接提取**: 绕过 OddsPortal Archive API 加密限制
- ✅ **分页点击突破**: V40.20 找到真正的翻页方法
- ✅ **Hash 去重**: 避免重复数据，每页新增 50 场
- ✅ **高覆盖率**: La Liga 94.7%，总计 71.4%
- ✅ **数据质量**: 100% 完整性，0.95 置信度

#### DOM 提取方法（绕过 API 加密）

```javascript
// V40.22 最终方案
const links = document.querySelectorAll('a[href*="/football/"]');
links.forEach(link => {
    const href = link.getAttribute('href');
    // 只处理比赛详情页（8位hash）
    if (href && href.match(/-[a-zA-Z0-9]{8}\/?$/)) {
        results.push({ href: href });
    }
});
```

#### 分页点击突破（V40.20）

```python
# 成功的点击方法
elements = await page.locator(f"text={page_num}").all()
for element in elements:
    class_name = await element.get_attribute('class')
    if 'pagination' in class_name:
        await element.click()
        await asyncio.sleep(5)  # 关键：等待页面加载
```

#### V40 系列成果统计

| 联赛 | 目标 | 实际 | 覆盖率 | 状态 |
|------|------|------|--------|------|
| La Liga | 380 | 360 | 94.7% | ✅ 优秀 |
| Ligue 1 | 306 | 130 | 42.5% | 🔶 中等 |
| 总计 | 686 | 490 | 71.4% | ✅ 良好 |

#### 遗留问题
- ⚠️ Ligue 1 覆盖率低（42.5%），第 4 页无新数据
- ⚠️ Archive API 加密未破解（`lscompressor.min.js` 逆向待研究）
- ⚠️ 队名解析需改进（"Rayo Vallecano Ath" 问题）

---

## ML 引擎

### ModelDispatcher - V26.8 联赛专项模型分发器

位于 `src/ml/engine.py:668`，自动选择联赛专项模型。

#### 基本用法

```python
from src.ml.engine import ModelDispatcher

dispatcher = ModelDispatcher()
prediction = dispatcher.predict(
    home_team="Arsenal",
    away_team="Chelsea",
    league_name="Premier League"  # 自动选择 EPL 专项模型
)
```

#### 支持的联赛专项模型
- `model_zoo/v26.8_epl_production.pkl` - 英超
- `model_zoo/v26.8_la_liga_production.pkl` - 西甲
- `model_zoo/v26.8_ligue1_production.pkl` - 法甲
- `model_zoo/v26.8_bund_production.pkl` - 德甲

#### ML 引擎多版本代码说明

`src/ml/engine.py` 包含多个历史版本（**这是有意保留的**）：

| 类名 | 版本 | 用途 |
|------|------|------|
| `V17MLEngine` | V17.0 | 滚动特征训练引擎（16维特征） |
| `V26Predictor` | V26.4 | 统一推理接口 |
| `ModelDispatcher` | V26.8 | 联赛专项模型分发器 |

**新增代码应遵循**: 优先使用 `ModelDispatcher` 进行预测，训练新模型时可参考 `V17MLEngine`。

---

### V26.7 核心特征

19 维完全对齐的赛前特征，通过 `src/database/schema_manager.py` 动态计算。

#### 特征列表

```python
V26_7_FEATURES = [
    # 滚动特征 (8个) - 最近 N 场历史平均值
    "rolling_xg_home", "rolling_xg_away",
    "rolling_shots_on_target_home", "rolling_shots_on_target_away",
    "rolling_possession_home", "rolling_possession_away",
    "rolling_team_rating_home", "rolling_team_rating_away",

    # 积分榜特征 (7个) - 赛前已知
    "home_table_position", "away_table_position", "table_position_diff",
    "home_points", "away_points", "points_diff",
    "home_recent_form_points",

    # 高级特征 (4个) - 动态计算
    "raw_elo_gap", "adjusted_elo_gap",
    "home_fatigue_index", "away_fatigue_index",
]
```

---

### V26.7 特征清单管理器

位于 `src/processors/feature_manifest.py`，实现"特征字典锁定"确保不同批次间的特征严格对齐。

#### 基本用法

```python
from src.processors.feature_manifest import FeatureManifest

# 加载特征清单
manifest = FeatureManifest.from_file("config/v26_feature_manifest.json")

# 获取必需特征列表
required_features = manifest.get_required_features()

# 获取特征别名映射
aliases = manifest.get_feature_aliases()

# 验证特征清单完整性
is_valid = manifest.validate()
```

#### 核心特性
- 固定特征清单（6346 维锁定）
- 验证提取的特征是否符合清单
- 填充缺失特征，确保所有比赛的特征维度一致
- 导出标准化特征字典（用于离线解析）
- 特征别名映射（API 字段名 → 标准特征名）

---

### V26.7 离线解析能力

位于 `scripts/maintenance/reprocess_from_local.py`，实现"零网络请求"下的特征重解析。

#### 基本用法

```bash
# 从数据库读取 l2_raw_json，使用 V25ProductionExtractor 离线生成特征
python scripts/maintenance/reprocess_from_local.py

# 指定比赛 ID
python scripts/maintenance/reprocess_from_local.py --match-id 12345

# 干跑模式
python scripts/maintenance/reprocess_from_local.py --dry-run
```

#### 核心特性
- 零网络请求的离线特征重解析
- 从数据库读取 `l2_raw_json` 数据
- 使用 `V25ProductionExtractor` 生成特征
- 支持单场比赛或批量处理
- 干跑模式验证

---

### V26.7 数据库一致性工具

位于 `scripts/ops/check_db_consistency.py`，检查数据库特征一致性。

#### 基本用法

```bash
# 检查数据库一致性
python scripts/ops/check_db_consistency.py

# 检查指定联赛
python scripts/ops/check_db_consistency.py --league "Premier League"

# 修复不一致
python scripts/ops/check_db_consistency.py --fix
```

#### 核心特性
- 检查特征维度一致性
- 检测缺失或多余特征
- 自动修复不一致数据
- 生成一致性报告

---

## 配置管理

### src/config_unified.py - 统一配置管理

提供项目范围的配置管理。

#### 基本用法

```python
from src.config_unified import get_settings

settings = get_settings()
# 访问配置
db_host = settings.database.host
db_name = settings.database.name
```

#### 重要环境差异

| 环境 | `DB_HOST` | `DB_NAME` |
|------|-----------|-----------|
| Docker | `db` | `football_db` |
| 本地开发 | `localhost` | `football_db` |
| WSL2 | `172.25.16.1` | `football_db` |

---

### HarvestConfigManager - V26.6 配置管理系统

位于 `src/config/harvest_config.py`，管理全球联赛采集配置。

#### 基本用法

```python
from src.config.harvest_config import get_config_manager

# 获取配置管理器单例
config_manager = get_config_manager()

# 查看配置摘要
config_manager.print_summary()

# 获取启用的联赛
enabled_leagues = config_manager.get_enabled_leagues()

# 按 Tier 获取联赛
tier1_leagues = config_manager.get_leagues_by_tier(tier=1)  # 5 大联赛

# 生成采集任务列表
tasks = config_manager.get_harvest_tasks()
```

#### 核心特性
- YAML 配置文件驱动 (`config/global_harvest_list.yaml`)
- 31 个全球联赛元数据管理
- 联赛启用/禁用状态控制
- 采集任务列表自动生成
- V26.5 哨兵配置集成

---

### CollectionSentry - V26.5 自动巡航哨兵

位于 `src/api/collectors/collection_sentry.py`。

#### 基本用法

```python
from src.api.collectors.collection_sentry import CollectionSentry

# 初始化哨兵系统
sentry = CollectionSentry(
    window_size=100,
    success_rate_threshold=0.7,
    consecutive_failure_threshold=5,
    pause_duration_hours=12
)

# 记录采集结果
sentry.record_result(success=True)

# 检查是否应该停机
if sentry.should_stop():
    logger.warning("⚠️ 哨兵触发：成功率过低，自动停机保护")
```

#### 核心特性
- 滑动窗口统计（最近 N 个结果）
- 成功率监控（低于 70% 触发停机）
- 连续失败监控（超过 6 次触发停机）
- 自动设置冷却期（12 小时）

---

## 运维脚本

### src/core - V105.0 核心基础设施

位于 `src/core/__init__.py`，提供系统级基础设施。

#### 基本用法

```python
from src.core import Config, Logger, config, logger
from src.core import CircuitBreaker, GracefulShutdownManager, get_logger
```

#### 核心功能

**配置管理** (`Config`):
- 配置文件存储在 `~/.footballprediction/config.json`
- 自动处理文件不存在或格式错误的情况
- 支持内存配置更新和持久化

**日志系统** (`Logger`, `ComponentLogger`):
- 支持多种日志级别 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- 事件代码系统 (EventCode) 用于日志分类
- 性能计时器 (performance_timer) 用于性能监控

**熔断器** (`CircuitBreaker`):
- 防止级联故障
- 自动恢复机制
- 预定义熔断器: `api_breaker`, `database_breaker`, `network_breaker`

**优雅关闭** (`GracefulShutdownManager`):
- SIGINT/SIGTERM 信号处理
- 资源清理保证
- 上下文管理器支持

#### 使用示例

```python
from src.core import get_logger, log_context, performance_timer

logger = get_logger("my_module")

# 结构化日志上下文
with log_context(module="my_module", operation="harvest"):
    logger.info("开始数据采集")

# 性能计时
with performance_timer("operation_name"):
    # 执行操作
    pass
```

---

### V36.1 Final Guard & Test Suite Pass 系统

V36.1 实现了测试套件全绿和生产级守护系统。

#### 核心架构

```
1. 数据采集层 (V151.3 并发收割器)
   • 8 Workers 并发采集
   • hover_wait=4.0s 确保数据完整性
   • 输出: matches_mapping.l2_raw_json

2. 数据同步层 (auto_sync_and_alchemy_v2.sh)
   • 过期锁自动突破 (kill -0 动态验证)
   • 纯 SQL 同步 (避免配置问题)
   • 输出: matches.l3_odds_data
   • 状态标记: l3_extraction_status = 'synced'

3. 特征提取层 (extract_features_v1.py V29.1)
   • 多格式解析 (Array/Pinnacle/Average Odds)
   • 增量模式 (避免重复处理)
   • 失败记录 (logs/failed_features.json)
   • 输出: match_features.payout_ratio

4. 自动循环 (15min 定时)
   • EXIT 完整处理 (trap cleanup EXIT)
   • 鲁棒性清理保证 (正常/异常都清理)
   • 详细日志 (logs/auto_sync_v2_nohup.log)
```

#### 使用方法

```bash
# 单次执行（冒烟测试）
./scripts/ops/auto_sync_and_alchemy_v2.sh --once

# 启动后台循环（15分钟）
nohup ./scripts/ops/auto_sync_and_alchemy_v2.sh --interval 15 > logs/auto_sync_v2_nohup.log 2>&1 &

# 查看日志
tail -f logs/auto_sync_v2_nohup.log

# 停止自动化
kill $(cat logs/auto_sync_and_alchemy_v2.pid)
```

#### V36.1 核心特性

1. **测试套件全绿**
   - 所有单元测试通过
   - 集成测试验证
   - 代码质量检查通过

2. **动态 PID 验证** (`kill -0`)
   - 使用 POSIX 标准 `kill -0 $PID` 验证进程是否存在
   - 替代旧版本的 `ps -p` 方法，更标准可靠

3. **过期锁自动突破**
   - 检测到过期 PID 文件时自动清理
   - 无需手动干预，自动重新启动
   - **TDD 验证通过**: 模拟 PID 99999 过期锁成功突破

4. **EXIT 信号完整处理**
   - `trap cleanup SIGINT SIGTERM EXIT` (三种退出方式)
   - 确保脚本正常退出时也能清理 PID 文件

5. **清理保证**
   - 清理函数根据退出状态记录不同信息
   - 无论正常退出 (exit 0) 还是异常退出 (exit 1) 都会清理
   - PID 文件永不残留

#### V36.0 传承特性（继续支持）

1. **多格式解析支持**
   - Array 格式: `{"home": [{"odds": "3.64"}]}`
   - Pinnacle 格式: `{"pinnacle": {"home_odds": 1.5}}`
   - Average Odds 格式: `{"closing_odds": {"Average Odds": {"home": 1.51}}}`

2. **TDD 失败追踪**
   - 失败记录自动写入 `logs/failed_features.json`
   - 保留最近 100 条失败记录
   - 包含 format_type, reason, raw_data_sample

3. **自动化运维**
   - 每 15 分钟自动执行数据同步和特征提取
   - 支持单次执行模式: `--once`
   - 支持自定义间隔: `--interval N`

#### 准入红线
- ❌ 禁止在不执行 `--once` 验证的情况下启动后台循环
- ✅ 只有在 payout_ratio 突破 0% 后才能启动 8 Workers
- ✅ 数据同步必须使用纯 SQL 方式（避免配置问题）

---

### 新增运维脚本

V150.0+ 新增运维脚本，位于 `scripts/ops/`：

| 脚本 | 功能 |
|------|------|
| `e2e_link_test.py` | 端到端链接测试 |
| `check_url_health.py` | URL 健康检查 |
| `smoke_test_production.py` | 生产环境冒烟测试 |
| `dashboard_quality.py` | 数据质量仪表盘 |
| `harvest_fotmob_full.py` | FotMob 全量收割 |
| `harvest_pinnacle_odds.py` | Pinnacle 赔率收割 |
| `harvest_pinnacle_concurrent.py` | **V151.3** 并发收割器（多进程） |
| `hunt_league_hashes.py` | **V151.1** 哈希狩猎（队名搜索 URL） |
| `v151_3_audit_report.py` | **V151.3** 审计报告生成器 |
| `v151_3_concurrent_safety_audit.py` | **V151.3** 并发安全审计 |
| `morning_report.py` | **V36.0** 晨报脚本（每日数据汇总） |
| `sync_matches_mapping_to_matches.py` | **V36.3** 数据同步桥 |
| `auto_sync_and_alchemy_v2.sh` | **V36.3** 数据链路全自动闭环 |

---

**最后更新**: 2026-01-14
