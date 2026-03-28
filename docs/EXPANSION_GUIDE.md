# TITAN 联赛扩张指南

> 版本: `V11.0`
>
> 目标: 新增联赛时优先改配置，不改核心 Recon/Harvest 代码。

## 1. 适用前提

这份指南适用于以下场景：

- 新增一个已经被 FotMob / OddsPortal 正常支持的联赛
- 调整现有联赛的 OddsPortal slug、国家路径或队名映射
- 为 Recon DOM fallback 增加 selector，而不改 `ReconNavigator` / `ReconEngine`

如果目标站点结构发生根本变化，先评估是否需要扩展 [src/infrastructure/recon/README.md](/home/xupeng/projects/FootballPrediction/src/infrastructure/recon/README.md) 中定义的服务边界，再决定是否改代码。

## 2. 配置唯一入口

新增联赛时，优先修改以下配置源：

- [config/leagues.json](/home/xupeng/projects/FootballPrediction/config/leagues.json)
  控制 L1 Discovery / Harvest 的联赛启用状态和联赛元数据。
- [config/recon_config.json](/home/xupeng/projects/FootballPrediction/config/recon_config.json)
  控制 Recon URL 模板、队名映射、DOM selector、超时、滚动参数和匹配阈值。

禁止直接把以下内容写进 JS：

- OddsPortal URL 模板
- CSS selector
- 滚动轮次、步长、等待时间
- 相似度阈值、日期权重、熔断等待时间

## 3. 新增联赛的标准步骤

### 3.1 更新 `config/leagues.json`

补齐联赛的基础元数据：

- `id`
- `name`
- `country`
- `slug`
- `enabled`

### 3.2 更新 `config/recon_config.json`

最少需要检查以下字段：

- `leagues.<CODE>`
  Recon 侧联赛名称、国家、slug、league_id
- `team_slugs`
  目标联赛常见队名 slug 列表
- `team_mappings`
  常见缩写、别名、历史名映射
- `recon_runtime.dom_scraper`
  如果该联赛页面结构特殊，补 selector 而不是改 `ReconDomScraper.js`
- `recon_runtime.task_planner.results_path`
  如果 URL 模板变化，先改模板

### 3.3 验证配置能被系统读取

```bash
docker-compose -f docker-compose.dev.yml exec -T dev node -e "const fs=require('fs'); JSON.parse(fs.readFileSync('config/recon_config.json','utf8')); JSON.parse(fs.readFileSync('config/leagues.json','utf8')); console.log('config_ok')"
```

## 4. Recon 配置驱动点

V11.0 之后，Recon 新服务已经全部配置驱动：

- `ReconBrowserContext`
  读取 `recon_runtime.browser_context`
- `ReconNetworkMonitor`
  读取 `recon_runtime.network_monitor`
- `ReconDomScraper`
  读取 `recon_runtime.dom_scraper`
- `ReconStateProber`
  读取 `recon_runtime.state_prober`
- `ReconMatchEvaluator`
  读取 `matching` 与 `recon_runtime.match_evaluator`
- `ReconMirrorManager`
  读取 `matching` 与 `recon_runtime.mirror_manager`
- `ReconTaskPlanner`
  读取 `recon_runtime.task_planner`
- `ReconEngine`
  读取 `recon_runtime.engine`

结论很简单：如果只是扩张联赛，不应该再改这些文件。

## 5. 最小验证路径

### 5.1 L1 Discovery

```bash
docker-compose -f docker-compose.dev.yml exec -T dev npm run seed
```

### 5.2 Recon 单联赛验证

```bash
docker-compose -f docker-compose.dev.yml exec -T dev \
  node scripts/ops/recon_scanner.js --season 2025-2026 --league <LEAGUE_CODE> --limit 20 --concurrency 3
```

### 5.3 数据库状态验证

```bash
docker-compose -f docker-compose.dev.yml exec db \
  psql -U football_user -d football_db \
  -c "SELECT pipeline_status, COUNT(*) FROM matches WHERE league_name = '<LEAGUE_NAME>' GROUP BY 1 ORDER BY 1;"
```

重点看：

- 是否能从 `harvested` 正常推进到 `RECON_LINKED`
- 是否出现大量 `RECON_MISMATCH`
- 是否生成 `matches_oddsportal_mapping`

## 6. 常见扩张问题

### 6.1 URL 正确但候选为空

优先检查：

- `config/recon_config.json` 中的 `leagues.<CODE>.country`
- `leagues.<CODE>.slug`
- `recon_runtime.task_planner.results_path`

### 6.2 页面有比赛但 DOM fallback 仍为空

优先修改：

- `recon_runtime.dom_scraper.result_anchor_selectors`
- `recon_runtime.dom_scraper.home_selectors`
- `recon_runtime.dom_scraper.away_selectors`
- `recon_runtime.dom_scraper.participant_selectors`

不要直接改 [ReconDomScraper.js](/home/xupeng/projects/FootballPrediction/src/infrastructure/recon/services/ReconDomScraper.js)，除非配置已经无法表达目标结构。

### 6.3 队名别名导致大量 mismatch

优先修改：

- `team_mappings`
- `team_slugs`
- `matching.common_suffixes`

不要先去改 [ReconMatchEvaluator.js](/home/xupeng/projects/FootballPrediction/src/infrastructure/recon/services/ReconMatchEvaluator.js)。

## 7. 合并前检查

满足以下条件才算扩张完成：

- 配置能正常加载
- 新联赛能跑通 `recon_scanner`
- `RECON_MISMATCH` 没有异常飙升
- 没有为了适配联赛而把 selector / 阈值写回 service 文件
- 文档与配置同步更新
