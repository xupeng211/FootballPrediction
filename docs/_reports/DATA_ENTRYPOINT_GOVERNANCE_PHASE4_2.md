# DATA ENTRYPOINT GOVERNANCE - PHASE 4.2

> 日期: 2026-04-30
>
> 范围: 数据收割 / ETL / ingest / backfill / recon / odds / feature / ELO 入口安全分级
>
> 结论: 当前项目入口能力完整，但高风险入口较多，真实执行前必须先补统一安全门禁和 runbook。

## 1. 审计范围

本轮只读审计了以下入口来源：

- `Makefile`
- `package.json`
- `scripts/ops/`
- `scripts/maintenance/recalculate_elo.js`
- `src/infrastructure/harvesters/`
- `src/infrastructure/recon/`
- `src/infrastructure/services/`
- `src/feature_engine/`
- `config/`
- 相关文档: `AGENTS.md`, `docs/EXPANSION_GUIDE.md`, `docs/harvesters/oddsportal_archive.md`, `docs/ops/backfill_v6_manual.md`

本轮只执行了基础状态检查、入口收集、源码只读审计，以及以下安全 help：

- `node scripts/ops/recon_scanner.js --help`
- `node scripts/ops/batch_historical_backfill.js --help`
- `node scripts/ops/csv_bulk_loader.js --help`
- `node scripts/ops/local_dom_ingestor.js --help`

## 2. 当前环境

| 项 | 结果 |
|---|---|
| 项目目录 | `/home/xupeng/FootballPrediction.clean-dev` |
| 审计起始分支 | `main` |
| 草案写入分支 | `docs/data-entrypoint-governance-phase42` |
| HEAD | `9f92e3c docs(agents): align docker development entrypoints (#1132)` |
| 起始 git status | clean |
| Docker dev stack | `dev`, `db`, `redis`, `prometheus`, `grafana` 均 healthy |
| dev Node | `v20.20.2` |
| dev npm | `10.8.2` |
| dev Python | `3.11.15` |
| `.env` | 存在，未读取内容 |

## 3. 安全分级定义

| 分级 | 含义 |
|---|---|
| `SAFE_READONLY` | 只读检查，不访问外网，不写数据库，不写项目文件。 |
| `SAFE_LOCAL_DRY_RUN` | 只使用本地样本文件，不访问外网，不写数据库。允许 stdout 预览；不应写项目状态文件。 |
| `NETWORK_DRY_RUN` | 不是安全 dry-run；只是理论上不写数据库，但会访问外网。必须有显式授权、limit、scope、代理/限速说明，AI 默认不能执行。 |
| `DB_WRITE_SMALL` | 会写数据库，但可通过 `--commit`、`--limit`、league/season/date 范围控制。 |
| `BULK_HARVEST` | 大规模收割、批量回填、多阶段 pipeline。需要人工审批、备份、监控、停止条件。 |
| `DEPRECATED_OR_UNSAFE` | dry-run 不可信、默认写数据、会写 DB 但没有 `--commit`、语义不清或硬编码范围，不建议直接运行。 |

补充硬规则：

- 只要源码会写数据库但没有 `--commit` 开关，默认归类为 `DEPRECATED_OR_UNSAFE`，推荐状态为 `BLOCK_UNTIL_REFACTORED`。
- 多表写入、删除、修复、批量回填、L3/ELO 重算前，必须先确认 DB 备份或快照策略。
- `NETWORK_DRY_RUN` 不等于安全 dry-run；它仍可能触发目标站点速率限制、代理消耗、浏览器初始化和外网请求。

## 4. 入口分级表

| 入口 | 命令 | 用途 | 数据源 | 访问外网 | 写 DB | 写文件 | 依赖代理 | 支持 dry-run | dry-run 是否可信 | 支持 limit / scope | 默认是否安全 | 建议分级 | 推荐状态 | 备注 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 生产 L2 收割 | `make dev-harvest`, `npm start`, `node scripts/ops/run_production.js` | 批量补齐 `raw_match_data` | FotMob / 浏览器 / DB pending | 是 | 是 | 可能写 `data/matches`, logs | 可能 | 是 | 不完全可信；仍初始化 DB/浏览器/外网 | `--limit`, `--workers`, `--league-ids`, `--season`, `--date-*` | 否 | `DEPRECATED_OR_UNSAFE` | `BLOCK_UNTIL_REFACTORED` | 真实能力属于 bulk harvest，但入口写 DB 无 `--commit`，必须先包装。 |
| 生产 L2 dry-run | `node scripts/ops/run_production.js --dry-run --limit N ...` | 预览 L2 收割 | FotMob / DB pending | 是 | 理论不写 | 可能写日志/会话 | 可能 | 是 | 只能视为 network dry-run | 同上 | 否 | `NETWORK_DRY_RUN` | `REQUIRE_EXPLICIT_NETWORK_APPROVAL` | 不是安全 dry-run；需要授权、limit、scope、代理/限速说明。 |
| Discovery 只读帮助 | `node scripts/ops/titan_discovery.js --help`, `--list` | 查看 L1 参数/联赛 | 本地配置 | 否 | 否 | 否 | 否 | 不适用 | 可信 | 无 | 是 | `SAFE_READONLY` | `ALLOW_READONLY` | `--list` 只读配置。 |
| Discovery 扫描 | `node scripts/ops/titan_discovery.js --dry-run`, `--all`, `--league=ID` | L1 赛程发现/播种 | FotMob / DiscoveryService | 是 | 是 | 可能写日志 | 可能 | 声称支持 | 不可信；源码仅打印 dry-run 提示，仍调用 `discover()` 和 `persist()` | `--league`, `--season`, `--tier`, `--concurrency`, `--lookback`, `--lookahead` | 否 | `DEPRECATED_OR_UNSAFE` | `BLOCK_UNTIL_REFACTORED` | 必须修复 dry-run 门禁后再允许。 |
| L1 seed | `npm run seed`, `node scripts/ops/seed_fixtures.js --season=... --league=...` | 配置驱动 L1 播种 | DiscoveryService / FotMob | 是 | 是 | 可能写日志 | 可能 | 否 | 无 | `--season`, `--league`, `--all` | 否 | `DEPRECATED_OR_UNSAFE` | `BLOCK_UNTIL_REFACTORED` | 会写 DB 但无 `--commit`，需先包装；`--all` 还应升级为 bulk 审批。 |
| 硬编码 L1 fixture harvester | `node scripts/ops/fixture_harvester_l1.js` | 德甲 25/26 赛程补齐 | OddsPortal 页面 | 是 | 是 | 可能写日志 | 可能 | 否 | 无 | 无，范围硬编码 | 否 | `DEPRECATED_OR_UNSAFE` | `BLOCK_UNTIL_REFACTORED` | 硬编码联赛、赛季、URL，默认写库。 |
| Total War dry-run | `node scripts/ops/total_war_pipeline.js --season ... --once --dry-run` | 预览多阶段编排 | DB 状态 / tmp 状态 | 否 | 否 | 是，`tmp/total_war_pipeline` | 可能 | 是 | 不应视为安全 dry-run；会写运行状态/锁/日志 | `--season`, `--task-stage`, `--limit` 类参数 | 否 | `DEPRECATED_OR_UNSAFE` | `BLOCK_UNTIL_REFACTORED` | dry-run 应改为纯 stdout 或 `/tmp`。 |
| Total War 真实编排 | `npm run titan:total-war -- --season ...` | Discovery/Harvest/Recon/Smelt 编排 | 多数据源 | 是 | 是 | 是 | 可能 | 是 | 真实运行最高风险 | 多阶段参数 | 否 | `DEPRECATED_OR_UNSAFE` | `BLOCK_UNTIL_REFACTORED` | 真实能力属于 bulk harvest，但入口缺少统一 `--commit` 门禁。 |
| Odds pipeline dry-run | `node scripts/ops/odds_harvest_pipeline.js --dry-run --limit N --season ...` | OddsPortal 赔率预览 | OddsPortal / DB targets | 是 | 理论不写 | 可能写日志 | 可能 | 是 | network dry-run，非安全 dry-run | `--season`, `--league`, `--limit`, `--workers`, `--skip-l3` | 否 | `NETWORK_DRY_RUN` | `REQUIRE_EXPLICIT_NETWORK_APPROVAL` | `--dry-run` 跳过 upsert，但仍抓页面/API。 |
| Odds pipeline 真实 | `npm run odds:harvest -- --season ... --limit N` | 写 mapping + odds，可触发 L3 | OddsPortal / DB | 是 | 是 | 可能写日志 | 可能 | 是 | 真实写入需审批 | 同上 | 否 | `DEPRECATED_OR_UNSAFE` | `BLOCK_UNTIL_REFACTORED` | 写 DB 无 `--commit`，小范围写入前应先加门禁。 |
| Odds sniper dry-run | `node scripts/ops/odds_sniper.js --match-id ... --dry-run` | 定点赔率提取预览 | OddsPortal / DB | 是 | 否 | 可能写日志 | 可选 | 是 | network dry-run，非安全 dry-run | `--match-id`, `--targets-file`, `--skip-*` | 否 | `NETWORK_DRY_RUN` | `REQUIRE_EXPLICIT_NETWORK_APPROVAL` | 用于单场修补前预览，但 AI 默认不能执行。 |
| Odds sniper 真实 | `node scripts/ops/odds_sniper.js --match-id ...` | 定点写 mapping/odds/L3 | OddsPortal / DB | 是 | 是 | 可能写日志 | 可选 | 是 | 真实写入需审批 | `--match-id`, `--targets-file`, `--skip-*` | 否 | `DEPRECATED_OR_UNSAFE` | `BLOCK_UNTIL_REFACTORED` | 写 DB 无 `--commit`，必须限制 match_id 并先加门禁。 |
| Recon help | `node scripts/ops/recon_scanner.js --help` | 查看 Recon 参数 | 本地源码 | 否 | 否 | 否 | 否 | 不适用 | 可信 | 无 | 是 | `SAFE_READONLY` | `ALLOW_READONLY` | 本轮已验证 help 安全。 |
| Recon scan | `node scripts/ops/recon_scanner.js --season ... --league ... --limit ...` | OddsPortal 映射与状态推进 | OddsPortal / DB / Redis | 是 | 是 | 可能写日志/备份 | 可选 `--use-proxy` | 否 | 无 | `--season`, `--league`, `--limit`, `--concurrency`, `--threshold` | 否 | `DEPRECATED_OR_UNSAFE` | `BLOCK_UNTIL_REFACTORED` | 无 dry-run、写 DB 且无 `--commit`；成功后可能触发 DB vault 备份。 |
| CSV loader help | `node scripts/ops/csv_bulk_loader.js --help` | 查看 CSV loader 参数 | 本地源码 | 否 | 否 | 否 | 否 | 不适用 | 可信 | 无 | 是 | `SAFE_READONLY` | `ALLOW_READONLY` | 本轮已验证 help 安全。 |
| CSV loader default | `node scripts/ops/csv_bulk_loader.js --file <path-to-local-csv> --error-log /tmp/csv_errors.jsonl` | 本地 CSV 解析和对齐预览 | 本地 CSV + DB read | 否 | 否 | 是，error log | 否 | 默认 dry-run | 有条件可信；会读 DB，默认 error log 在 `logs/` | `--file`, `--batch-size`, `--error-log` | 仅有条件 | `SAFE_LOCAL_DRY_RUN` | `ALLOW_LOCAL_DRY_RUN` | 执行前确认本地 CSV 已存在，不为示例下载外网数据。 |
| CSV loader commit | `node scripts/ops/csv_bulk_loader.js --file ... --commit --batch-size ...` | 写 matches 战术字段和 odds history | 本地 CSV + DB | 否 | 是 | 是 | 否 | 默认 dry-run | commit 需审批 | `--file`, `--batch-size`, `--error-log` | 否 | `DB_WRITE_SMALL` | `REQUIRE_EXPLICIT_DB_WRITE_APPROVAL` | 必须先 dry-run，再 DB 统计，再 commit。 |
| Local DOM help | `node scripts/ops/local_dom_ingestor.js --help` | 查看本地 HTML 入口参数 | 本地源码 | 否 | 否 | 否 | 否 | 不适用 | 可信 | 无 | 是 | `SAFE_READONLY` | `ALLOW_READONLY` | 本轮已验证 help 安全。 |
| Local DOM default | `node scripts/ops/local_dom_ingestor.js --file <path-to-local-html>` | 本地 HTML/clipboard 赔率预览 | 本地 HTML / clipboard | 否 | 否 | 否 | 否 | 默认 dry-run | 可信 | `--dir`, `--file`, `--clipboard` | 是 | `SAFE_LOCAL_DRY_RUN` | `ALLOW_LOCAL_DRY_RUN` | 当前最适合作为第一条本地 dry-run 链路；执行前确认文件存在。 |
| Local DOM commit | `node scripts/ops/local_dom_ingestor.js --file <path-to-local-html> --commit` | 写 bookmaker odds history | 本地 HTML / DB | 否 | 是 | 否 | 否 | 默认 dry-run | commit 需审批 | `--dir`, `--file`, `--clipboard` | 否 | `DB_WRITE_SMALL` | `REQUIRE_EXPLICIT_DB_WRITE_APPROVAL` | 必须限制本地文件数量。 |
| football-data CSV adapter | `node scripts/ops/fetch_and_adapt_euro_leagues.js --league-code ... --season-code ... --output ...` | 下载 football-data CSV 并适配 | football-data.co.uk + DB read | 是 | 否 | 是，输出 CSV/temp | 否 | 否 | 无 | `--league-code`, `--season-code`, `--output` | 否 | `NETWORK_DRY_RUN` | `REQUIRE_EXPLICIT_NETWORK_APPROVAL` | 无 DB 写，但默认外网下载和文件输出。 |
| Backfill help | `node scripts/ops/batch_historical_backfill.js --help` | 查看批量回填参数 | 本地源码 | 否 | 否 | 否 | 否 | 不适用 | 可信 | 无 | 是 | `SAFE_READONLY` | `ALLOW_READONLY` | 本轮已验证 help 安全。 |
| Backfill dry-run | `node scripts/ops/batch_historical_backfill.js --dry-run ...` | 预览历史扩军回填 | 多入口组合 | 是 | 理论不写 | 是，CSV/report/log | 可能 | 是 | 不可信；会触发下载/文件输出，且下游 dry-run 不全可信 | `--leagues`, `--seasons`, `--output-dir`, `--harvest-limit`, `--skip-*` | 否 | `DEPRECATED_OR_UNSAFE` | `BLOCK_UNTIL_REFACTORED` | 应先拆成本地 CSV dry-run 与网络 dry-run。 |
| Backfill commit | `node scripts/ops/batch_historical_backfill.js --commit ...` | 历史 CSV/FotMob/ELO/L3 批量编排 | 多数据源 | 是 | 是 | 是 | 可能 | 是 | commit 最高风险 | 同上 | 否 | `BULK_HARVEST` | `REQUIRE_RUNBOOK_AND_BACKUP` | 多阶段批处理，必须审批。 |
| Historical raw L2 default | `node scripts/ops/backfill_historical_raw_match_data.js --season=... --league=... --limit=...` | 从 FotMob GSM 补 raw_match_data 预览 | FotMob GSM / DB pending | 是 | 否 | 可能写日志 | 否 | 默认不 commit | 网络 dry-run | `--season`, `--league`, `--limit`, `--workers` | 否 | `NETWORK_DRY_RUN` | `REQUIRE_EXPLICIT_NETWORK_APPROVAL` | 即使不写 DB，仍访问 `data.fotmob.com`。 |
| Historical raw L2 commit | `node scripts/ops/backfill_historical_raw_match_data.js --commit --limit ...` | 写 raw_match_data 并推进状态 | FotMob GSM / DB | 是 | 是 | 可能写日志 | 否 | 默认不 commit | commit 需审批 | 同上 | 否 | `DB_WRITE_SMALL` | `REQUIRE_EXPLICIT_DB_WRITE_APPROVAL` | 无 limit 时可能升级为 bulk。 |
| Smelt all | `npm run smelt`, `node scripts/ops/smelt_all.js --dry-run` | L3 特征熔炼 | DB raw/l3 | 否 | 是 | logs | 否 | 声称支持 | 不可信；`FeatureSmelter.run()` 未使用 `dryRun` 参数，仍保存特征 | `--full-recalculate`；缺 CLI limit | 否 | `DEPRECATED_OR_UNSAFE` | `BLOCK_UNTIL_REFACTORED` | 必须先修复 dry-run 和 limit。 |
| L3 stitch | `npm run l3:stitch`, `node scripts/ops/l3_stitch_pipeline.js` | L3 stitch + incremental Elo | DB raw/odds | 否 | 是 | logs | 否 | 否 | 无 | env: `L3_STITCH_SEASON`, `L3_STITCH_WORKERS`, `L3_STITCH_FULL_RECALCULATE` | 否 | `DEPRECATED_OR_UNSAFE` | `BLOCK_UNTIL_REFACTORED` | 创建/更新 `l3_features` 且会回填 scores，无 `--commit` 门禁。 |
| Elo dry-run | `npm run elo:recalc:dry` | Elo 计算预览 | DB read | 否 | 否 | stdout/log | 否 | 是 | 只读 DB 计算，非轻量 help 类只读 | `--incremental` | 有条件 | `SAFE_READONLY` | `ALLOW_READONLY` | 不写 DB，但会读 DB 并可能进行较重计算；执行前确认 DB 目标和数据规模。 |
| Elo real | `npm run elo:recalc` | 更新 `l3_features.elo_features` 和 `team_elo_ratings` | DB | 否 | 是 | stdout/log | 否 | 是 | real 写库 | `--incremental` | 否 | `DEPRECATED_OR_UNSAFE` | `BLOCK_UNTIL_REFACTORED` | 写 DB 无 `--commit`；全量重算需先加门禁、DB 统计和备份。 |
| FotMob sample default | `node scripts/ops/seed_fotmob_sample.js ...` | 本地 `data/matches` 样本预览 | 本地 JSON | 否 | 否 | stdout | 否 | 默认 dry-run | 可信度中等 | `--source-dir`, `--league-id`, `--season`, `--limit` | 有条件 | `SAFE_LOCAL_DRY_RUN` | `ALLOW_LOCAL_DRY_RUN` | 只用本地样本时可作为 dry-run。 |
| FotMob sample commit | `node scripts/ops/seed_fotmob_sample.js --commit --limit ...` | 写 matches/raw_match_data | 本地 JSON / DB | 否 | 是 | stdout | 否 | 默认 dry-run | commit 需审批 | 同上 | 否 | `DB_WRITE_SMALL` | `REQUIRE_EXPLICIT_DB_WRITE_APPROVAL` | 必须使用 `--limit` 和明确 league/season。 |
| Bulk import matches | `node scripts/ops/bulk_import_matches.js` | `data/matches/*.json` 批量入库 raw_match_data | 本地 JSON | 否 | 是 | stdout/log | 否 | 否 | 无 | 仅 env `DATA_MATCHES_PATH` | 否 | `DEPRECATED_OR_UNSAFE` | `BLOCK_UNTIL_REFACTORED` | 默认批量写库，无 `--commit`/`--limit`。 |
| 清理脚本 dry-run | `cleanup_csv_bulk_loader_import.js`, `purge_orphans.js`, `purge_ghost_data.js` 不带 `--commit` | 查看可删除范围 | DB read | 否 | 否 | stdout | 否 | 默认 inspect | 可信度较高 | `--season`, `--league`, `--expected-count` 等 | 是 | `SAFE_READONLY` | `ALLOW_READONLY` | 删除类脚本只允许先 inspect。 |
| 清理脚本 commit | 同上加 `--commit` | 删除 matches/odds/ref rows | DB | 否 | 是，删除 | stdout | 否 | 默认 inspect | commit 高风险 | 同上 | 否 | `DB_WRITE_SMALL` | `REQUIRE_EXPLICIT_DB_WRITE_APPROVAL` | 删除前必须备份和核对 expected count。 |
| Canonical janitor audit | `node scripts/ops/run_match_canonical_janitor.js --season ... --audit-only` | 查 canonical identity 冲突 | DB read | 否 | 否 | stdout | 否 | 默认 audit-only | 可信 | `--season`, `--source-provider`, `--limit` | 是 | `SAFE_READONLY` | `ALLOW_READONLY` | 可作为 DB 只读验证。 |
| Canonical janitor repair | `node scripts/ops/run_match_canonical_janitor.js --season ... --repair --limit ...` | 修复 canonical identity | DB | 否 | 是 | stdout | 否 | 默认 audit-only | repair 需审批 | 同上 | 否 | `DEPRECATED_OR_UNSAFE` | `BLOCK_UNTIL_REFACTORED` | 写 DB 但没有 `--commit` 开关，必须先 audit-only 并补门禁。 |
| Gold pilot / odds backfill | `node scripts/ops/gold_pilot_50.js` | OddsPortal pilot/backfill，写 market sentiment | OddsPortal / DB | 是 | 是 | 可能写 logs/checkpoints | 是 | 不明确 | 不可信 | 源码内范围有限但非统一 CLI | 否 | `DEPRECATED_OR_UNSAFE` | `BLOCK_UNTIL_REFACTORED` | 旧 backfill 手册入口，写 DB 无 `--commit`，需纳入统一 data-* 包装。 |
| Marathon dry-run | `node scripts/ops/titan_marathon.js --dry-run --limit=...` | 查询待收割规模 | DB read | 否 | 否 | stdout | 否 | 是 | 可信度中等 | `--limit`, `--league`, `--season` | 有条件 | `SAFE_READONLY` | `ALLOW_READONLY` | 仅用于估算 backlog，不收割。 |
| Marathon real | `node scripts/ops/titan_marathon.js --workers=... --limit=...` | 多轮饱和 L2 收割 | FotMob / DB | 是 | 是 | logs/checkpoints | 可能 | 是 | 真实运行高风险 | `--limit`, `--league`, `--season`, `--rounds` | 否 | `DEPRECATED_OR_UNSAFE` | `BLOCK_UNTIL_REFACTORED` | 长时任务且写 DB 无 `--commit`，禁止默认运行。 |
| Titan 40 workers | `node scripts/ops/titan_40_workers.js` | 40 worker 物理隔离收割 | FotMob / DB | 是 | 是 | logs | 是 | 否 | 无 | env: `TITAN_*`, `PROXY_*` | 否 | `DEPRECATED_OR_UNSAFE` | `BLOCK_UNTIL_REFACTORED` | 无 CLI dry-run，默认 `dryRun: false` 且无 `--commit`。 |
| Predict pipeline | `python scripts/ops/predict_pipeline.py --dry-run --limit ...` | 读取 L3 并输出预测 | DB read / model artifacts | 否 | 否 | logs | 否 | 是 | 目前不写 predictions 表 | `--limit`, `--league` | 有条件 | `SAFE_READONLY` | `ALLOW_READONLY` | 不是收割入口；dry-run 参数当前主要是语义占位。 |
| Train pipeline | `python scripts/ops/train_model.py --name ...` | 训练模型并写 artifact | DB read / model artifacts | 否 | 否 | 是，模型和 metadata | 否 | 否 | 无 | `--min-samples`, `--name` | 否 | `DEPRECATED_OR_UNSAFE` | `BLOCK_UNTIL_REFACTORED` | 非收割，但会改模型产物；需独立 artifact 审批。 |

## 5. 高风险入口说明

### 5.1 最高风险入口

- `make dev-harvest`
- `npm start`
- `node scripts/ops/run_production.js`
- `npm run titan:total-war`
- `npm run odds:harvest`
- `node scripts/ops/recon_scanner.js --season ...`
- `node scripts/ops/batch_historical_backfill.js --commit`
- `node scripts/ops/titan_marathon.js`
- `node scripts/ops/titan_40_workers.js`

这些入口具备以下至少一个特征：

- 默认就可能执行真实任务。
- 会访问 FotMob / OddsPortal / football-data.co.uk。
- 会写 `matches`, `raw_match_data`, `matches_oddsportal_mapping`, `odds`, `bookmaker_odds_history`, `l3_features`, `team_elo_ratings`。
- 可能长期运行、批量下载、启动 Playwright 浏览器或代理池。

### 5.2 dry-run 可信度问题

当前按以下五类看待 dry-run / 只读计算：

- 可信本地 dry-run: `local_dom_ingestor.js` 默认模式，只处理本地 HTML / clipboard，不访问外网、不写 DB。
- 有条件可信本地 dry-run: `csv_bulk_loader.js` 默认模式会读 DB，并默认写 `logs/csv_bulk_loader_errors.jsonl`，建议将 `--error-log` 指向 `/tmp`。
- 只读 DB 计算: `recalculate_elo.js --dry-run` 不写 DB，但会读 DB 并可能进行较重计算；执行前需要确认 DB 目标和数据规模，不能和 help/version 这种轻量只读混为一类。
- network dry-run: `run_production.js --dry-run`、`odds_harvest_pipeline.js --dry-run`、`odds_sniper.js --dry-run`、`backfill_historical_raw_match_data.js` 默认模式理论上不写 DB，但会访问外网，不是安全 dry-run。
- 不可信 dry-run: `titan_discovery.js --dry-run` 仍调用 `DiscoveryService.discover()` 并落到 `FixtureRepository.persist()`；`smelt_all.js --dry-run` 传入参数但 `FeatureSmelter.run()` 未使用；`batch_historical_backfill.js --dry-run` 会组合触发下载、文件输出和下游不可信 dry-run。

## 6. 数据源和外部依赖

| 数据源 | 相关入口 | 风险 |
|---|---|---|
| FotMob / FotMob web data | `run_production.js`, `titan_discovery.js`, `backfill_historical_raw_match_data.js`, `titan_marathon.js`, `titan_40_workers.js` | 外网、速率限制、可能需要代理或合规模式。 |
| OddsPortal | `recon_scanner.js`, `odds_harvest_pipeline.js`, `odds_sniper.js`, `fixture_harvester_l1.js`, `gold_pilot_50.js` | 外网、反爬、代理、Playwright 浏览器、页面结构变化。 |
| football-data.co.uk | `fetch_and_adapt_euro_leagues.js`, `batch_historical_backfill.js` | 外网 CSV 下载，可能写本地 CSV。 |
| 本地 CSV | `csv_bulk_loader.js` | 本地文件解析，会查 DB 对齐；commit 写 DB。 |
| 本地 HTML / clipboard | `local_dom_ingestor.js` | 默认安全，本地解析；commit 写 DB。 |
| 本地 JSON | `seed_fotmob_sample.js`, `bulk_import_matches.js` | 默认或真实批量写 DB 风险取决于脚本。 |

未发现必须填写的第三方 API key 才能运行当前主入口；主要敏感配置是 DB/Redis/代理/浏览器会话。

## 7. 数据落地位置

| 位置 | 说明 |
|---|---|
| PostgreSQL `matches` | L1 赛程、状态、比分、战术字段。 |
| PostgreSQL `raw_match_data` | L2 原始 FotMob/结构化 raw payload。 |
| PostgreSQL `matches_oddsportal_mapping` | Recon / OddsPortal 映射。 |
| PostgreSQL `odds` | canonical opening/current odds。 |
| PostgreSQL `bookmaker_odds_history` | CSV / Local DOM 导入的 bookmaker odds history。 |
| PostgreSQL `l3_features` | L3 golden/tactical/odds/Elo/stitch 特征。 |
| PostgreSQL `team_elo_ratings` | Elo 当前球队评分。 |
| PostgreSQL `backfill_progress` | 旧 backfill checkpoint。 |
| Redis | Recon 分布式锁、运行时协调、健康检查。 |
| `data/matches` | ProductionHarvester 辅助文件输出、Bulk import 输入。 |
| `data/historical_csv/adapted` | historical backfill 适配 CSV 默认输出。 |
| `data/mock/real_euro_league_adapted.csv` | football-data adapter 默认输出。 |
| `logs/` | loader error log、backfill report、train/predict logs、sentinel log。 |
| `tmp/total_war_pipeline` | Total War lock/state/log/session buffer。 |
| `models/` 或配置模型目录 | 训练产物和 metadata。 |

## 8. 推荐安全执行原则

1. 默认不访问外网。
2. 默认不写数据库。
3. 默认不批量下载。
4. `NETWORK_DRY_RUN` 不是安全 dry-run；它只是理论上不写 DB，但会访问外网。
5. 真实写入必须显式 `--commit`，没有 `--commit` 的写库脚本默认 `BLOCK_UNTIL_REFACTORED`。
6. 外网访问必须显式授权，并说明目标站点、league/season/date/limit、代理策略和速率限制。
7. DB 写入必须先做只读统计，执行后再做只读统计。
8. 多表写入、删除、修复、批量回填、L3/ELO 重算前必须确认 DB 备份或快照策略。
9. 批量任务必须有备份、limit、日志、监控、失败阈值和停止条件。
10. dry-run 如果仍访问外网、写项目文件或初始化真实浏览器/代理，不能视为安全 dry-run。
11. AI/Codex 不得直接运行 `NETWORK_DRY_RUN`、`BULK_HARVEST` 或 `DEPRECATED_OR_UNSAFE` 入口。

## 9. 后续改造建议

### 9.1 Makefile

建议新增统一数据入口：

```bash
make data-help
make data-check
make data-local-dry-run
make data-network-dry-run
make data-db-write-small
make data-harvest
```

建议策略：

- `data-help`: 只列可用入口和风险等级。
- `data-check`: 只做配置、依赖、DB 只读连通性检查。
- `data-local-dry-run`: 只允许本地样本，不允许外网，不允许 DB 写。
- `data-network-dry-run`: 必须要求 `CONFIRM_NETWORK=1`、`LIMIT`、`LEAGUE`、`SEASON`、代理/限速说明。
- `data-db-write-small`: 必须要求 `CONFIRM_DB_WRITE=1`、`--commit`、`LIMIT`、范围参数、前后 DB 统计。
- `data-harvest`: 必须要求 `CONFIRM_BULK_HARVEST=1`、备份存在、runbook 路径、监控开关。

高风险入口如 `dev-harvest` 应加醒目警告，或者从默认 help 中隐藏到 `danger-*` 命名空间。

### 9.2 AGENTS.md

建议加入规则：

- AI 禁止直接运行高风险数据入口。
- AI 默认不能执行 `NETWORK_DRY_RUN`。
- `BULK_HARVEST` 必须由用户提供明确授权句。
- 所有 DB 写入必须显式 `--commit`。
- 会写 DB 但没有 `--commit` 的脚本默认 `BLOCK_UNTIL_REFACTORED`。
- 不可信 dry-run 入口必须先重构或通过 `make data-*` 安全包装。
- 删除类脚本必须先输出 inspect 结果，再要求二次确认。

### 9.3 脚本层改造

- 修复 `titan_discovery.js --dry-run`，让 dry-run 只打印计划，不调用 `persist()`。
- 修复 `smelt_all.js --dry-run`，让 `FeatureSmelter.run()` 真正跳过 `saveFeatures()`。
- 给 `bulk_import_matches.js`, `fixture_harvester_l1.js`, `l3_stitch_pipeline.js` 增加 `--commit` / `--dry-run` / `--limit`。
- 让 `batch_historical_backfill.js --dry-run` 不下载、不写项目文件，或明确改名为 `--network-dry-run`。
- 将 CSV loader 默认 error log 改到 `/tmp`，或仅在 `--error-log` 显式传入时写文件。

## 10. 本阶段未执行事项

本阶段没有执行：

- 真实 harvest
- 真实 scrape
- 真实 ingest
- 外网数据收割
- 数据库写入
- 大规模下载
- `git push`
- `git pull`
- `git fetch --all`
- `docker compose down -v`
- Docker prune
- 删除文件
- 提交 commit
