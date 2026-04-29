# Data Harvesting Guide

> 适用范围: FootballPrediction 数据收割、ETL、ingest、backfill、Recon、Odds、L3、ELO 相关入口。
>
> 默认立场: 不访问外网、不写数据库、不批量下载。任何真实写入都必须显式授权。

## 1. 数据收割总原则

1. 先做只读检查，再做本地 dry-run，再申请网络 dry-run，最后才允许小范围写入。
2. 真实写入必须显式 `--commit`。没有 `--commit` 保护的写库脚本不得直接运行。
3. 外网访问必须显式授权，并声明目标站点、league、season、date/limit、代理和限速策略。
4. 批量任务必须有 DB 备份、前后统计、日志路径、监控方式和停止条件。
5. dry-run 如果仍访问外网、写项目文件、初始化真实浏览器或触发下游任务，不能视为安全 dry-run。
6. 如果脚本会写数据库但没有 `--commit` 开关，默认归类为 `DEPRECATED_OR_UNSAFE`，必须先包装或重构。
7. 所有 Node/Python 业务命令优先在 `dev` 容器内执行。

## 2. 安全分级

| 分级 | 允许条件 |
|---|---|
| `SAFE_READONLY` | help/version/status/config/list，不能访问外网，不能写 DB，不能写项目文件。 |
| `SAFE_LOCAL_DRY_RUN` | 只读本地样本文件，不访问外网，不写 DB。输出仅到 stdout 或 `/tmp`。 |
| `NETWORK_DRY_RUN` | 不是安全 dry-run；只是理论上不写 DB，但会访问外网。必须有用户显式授权、limit、scope、代理/限速说明。AI 默认不能执行。 |
| `DB_WRITE_SMALL` | 小范围 DB 写入。必须有 `--commit`、`--limit`、league/season/date 范围、前后 DB 统计。 |
| `BULK_HARVEST` | 批量收割/回填/多阶段 pipeline。必须有 runbook、备份、监控、失败阈值。 |
| `DEPRECATED_OR_UNSAFE` | dry-run 不可信、默认写数据、会写 DB 但没有 `--commit`、无 scope 或语义不清。默认阻止。 |

## 3. 默认禁止直接运行

以下命令不得直接执行，除非用户明确进入对应阶段并给出书面授权：

```bash
make dev-harvest
npm start
node scripts/ops/run_production.js
node scripts/ops/titan_discovery.js
npm run titan:total-war
npm run odds:harvest
node scripts/ops/recon_scanner.js --season ...
node scripts/ops/batch_historical_backfill.js
node scripts/ops/fetch_and_adapt_euro_leagues.js
node scripts/ops/fixture_harvester_l1.js
node scripts/ops/bulk_import_matches.js
node scripts/ops/titan_marathon.js
node scripts/ops/titan_40_workers.js
node scripts/ops/csv_bulk_loader.js --commit
node scripts/ops/local_dom_ingestor.js --commit
```

## 4. 首选验证顺序

严格按以下顺序推进，不要跳过前置层级：

1. `--help` 检查。
2. 本地 HTML 预览: `local_dom_ingestor.js` 默认模式。
3. 本地 CSV 预览: `csv_bulk_loader.js` 默认模式，但 `--error-log` 必须指向 `/tmp`。
4. ELO dry-run: `recalculate_elo.js --dry-run`，只读 DB 但可能进行较重计算，执行前确认 DB 目标和数据规模。
5. Network dry-run: 必须由用户授权，并声明 limit、scope、代理和限速说明。
6. `DB_WRITE_SMALL`: 必须由用户授权，包含 `--commit`、limit、前后 DB 统计。

禁止优先使用 `make dev-harvest`、`npm start`、`npm run titan:total-war`、`batch_historical_backfill.js` 这类生产或批量入口。

## 5. 推荐命令模板

只读 help：

```bash
docker compose -f docker-compose.dev.yml exec -T dev \
  node scripts/ops/local_dom_ingestor.js --help
```

本地 HTML dry-run：

```bash
docker compose -f docker-compose.dev.yml exec -T dev \
  node scripts/ops/local_dom_ingestor.js --file <path-to-local-html>
```

本地 CSV dry-run：

```bash
docker compose -f docker-compose.dev.yml exec -T dev \
  node scripts/ops/csv_bulk_loader.js \
    --file <path-to-local-csv> \
    --batch-size 50 \
    --error-log /tmp/csv_bulk_loader_errors.jsonl
```

ELO dry-run：

```bash
docker compose -f docker-compose.dev.yml exec -T dev \
  node scripts/maintenance/recalculate_elo.js --dry-run
```

执行本地 HTML / CSV 示例前，必须确认 `<path-to-local-html>` 或 `<path-to-local-csv>` 已经存在。不要为了跑通示例去下载外网数据。

ELO dry-run 不写 DB，但会读取 DB 并可能扫描较多比赛和球队评分；执行前必须确认连接的是目标 DB，且数据规模可接受。它不是 help/version 这种轻量只读检查。

网络 dry-run 必须先获得授权，模板如下：

```bash
docker compose -f docker-compose.dev.yml exec -T dev \
  node scripts/ops/odds_harvest_pipeline.js \
    --dry-run \
    --season 2024/2025 \
    --league "Premier League" \
    --limit 5 \
    --workers 1 \
    --skip-l3
```

小范围 DB 写入模板：

```bash
# 1. 写入前 DB 只读统计
# 2. 用户确认范围和 --commit
docker compose -f docker-compose.dev.yml exec -T dev \
  node scripts/ops/local_dom_ingestor.js \
    --file <path-to-local-html> \
    --commit
# 3. 写入后 DB 只读统计
```

## 6. 真实写入前置条件

真实写入前必须同时满足：

- 当前 Git 工作区状态已确认，且不会把输出文件误纳入 Git。
- Docker dev stack healthy。
- `.env` 存在且 DB/Redis/代理配置已确认，不显示 secret。
- 命令包含 `--commit`，或脚本已经被确认不会写 DB。
- 会写 DB 但没有 `--commit` 开关的脚本已被包装或重构，否则不得执行。
- 命令包含 `--limit` 或等价范围控制。
- 明确 league / season / date / match_id 范围。
- 任何多表写入、删除、修复、批量回填、L3/ELO 重算前，已确认 DB 备份或快照策略。
- 已执行 dry-run，并记录结果。
- 已执行写入前 DB 只读统计。
- 已确认回滚或重跑策略。

## 7. 小范围写入流程

1. 选择 `DB_WRITE_SMALL` 入口，不使用 `BULK_HARVEST` 入口。
2. 读取源码确认 `--commit` 只控制预期表。
3. 执行 help。
4. 执行本地 dry-run 或网络 dry-run。
5. 执行写入前 DB 统计。
6. 使用最小 scope 运行 `--commit`。
7. 执行写入后 DB 统计。
8. 检查日志和异常行。
9. 如有异常，立即停止，不扩大范围。

## 8. 批量收割流程

批量任务只允许在专门阶段执行：

1. 写 runbook，列出命令、范围、limit、代理、预期写入表、停止条件。
2. 做 DB 备份或快照。
3. 做单 league / 小 limit 试运行。
4. 做小范围 `--commit`。
5. 检查 PostgreSQL、Redis、日志、Prometheus/Grafana。
6. 分批扩大范围。
7. 每批结束做 DB 统计和错误审计。
8. 达到失败阈值、速率限制、代理异常或数据异常时立即停止。

## 9. 回滚和停止条件

出现以下任一情况必须停止：

- 外网站点返回大量 403/429/timeout。
- DB 写入数量超过预期。
- `RECON_MISMATCH` 异常飙升。
- `raw_match_data` 或 `l3_features` 缺口没有按预期变化。
- 日志出现重复写入、hash 冲突、identity 冲突。
- 代理池健康率低于 runbook 阈值。
- Docker 服务不再 healthy。

删除或修复类脚本必须先运行 inspect/audit-only，再备份，再显式 `--commit`。

## 10. AI / Codex 操作规则

AI 默认只能执行：

- `SAFE_READONLY`
- 用户明确允许的 `SAFE_LOCAL_DRY_RUN`

AI 不能直接执行：

- `NETWORK_DRY_RUN`。它不是安全 dry-run；除非用户明确授权外网访问并给出 limit、scope、代理/限速说明。
- `DB_WRITE_SMALL`，除非用户明确授权 DB 写入并给出范围。
- `BULK_HARVEST`，除非用户提供 runbook、备份和执行批准。
- `DEPRECATED_OR_UNSAFE`，除非先完成重构或安全包装。

AI 必须拒绝或暂停的情况：

- 命令没有 `--commit` 保护但源码会写 DB。
- dry-run 仍会写项目状态文件或触发外网批量访问。
- 命令缺少 limit / season / league / date / match_id 范围。
- 用户要求运行删除、清理 volume、prune 或破坏性 Git 命令。

## 11. 后续改造目标

建议引入统一 Makefile 门禁：

```bash
make data-help
make data-check
make data-local-dry-run
make data-network-dry-run
make data-db-write-small
make data-harvest
```

并要求：

- 所有 DB 写入脚本都支持显式 `--commit`。
- 所有网络 dry-run 都显式命名为 network dry-run。
- 所有 dry-run 默认不写项目文件。
- 所有批量任务都只能从 `make data-harvest` 进入。
