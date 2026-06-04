<!-- markdownlint-disable MD013 -->

# FotMob Registry Seed Dry-run 设计

- lifecycle: permanent / governance
- phase: FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-REGISTRY-SEED-DRY-RUN
- version: 1.0.0
- no network fetch / no DB write / no SQL execution / no raw JSON write / no scheduler enable / no feature parse
- raw_write_ready remains false

## 1. 本阶段目标

本阶段不是 live collection，不是 DB seed execution，而是 **registry seed plan dry-run**。

核心目标：用少量真实/半真实 football entity metadata 验证 football calendar target registry 的 7 张表是否能支撑全年赛程采集。

具体验证：

1. teams、competitions、editions、participations、match_targets、match_target_teams、source_identities 的结构是否足够
2. 是否能从 registry-like 数据生成 pending_raw_fetch 队列
3. 是否能按球队还原全年跨赛事比赛日历
4. 是否能保持 no-live-fetch、no-db-write、no-raw-json-write

## 2. 为什么需要 registry seed dry-run

当前状态：

- registry 7 张表已创建（V26.6 migration），但完全是空的
- dry-run collector（#1425）使用 synthetic flat targets fixture 验证了选择/预算/跳过逻辑
- 但 flat targets 无法验证 registry 的表间关系查询

真正长期采集发生时，collector 必须从 registry 表中 JOIN 查询目标，而不是从 flat JSON 中选择。因此需要先验证 registry-like 数据结构能否支撑这些查询。

## 3. Seed coverage

必须覆盖以下案例：

### 3.1 Manchester United 俱乐部赛程

- football_teams：Manchester United（club）
- football_competitions：Premier League、FA Cup、EFL Cup、UEFA Europa League
- football_competition_editions：每个赛事 2025/2026 season
- football_team_competition_participation：Man United 参与以上全部 4 个赛事届次
- football_match_targets：至少 4 个 match targets（跨 4 个赛事）
- football_match_target_teams：每个 target home/away 两行

### 3.2 England 国家队赛程

- football_teams：England（national）
- football_competitions：World Cup Qualifier、UEFA Nations League、International Friendly
- 至少 3 个 match targets

### 3.3 Japanese club / J League

- football_teams：Kashima Antlers（club）
- football_competitions：J1 League、Emperor's Cup
- 至少 2 个 match targets

### 3.4 Secondary league

- football_teams：Leeds United（club）
- football_competitions：EFL Championship、FA Cup
- 至少 2 个 match targets

### 3.5 Skip cases

- 1 个 target_state=blocked 的 match target
- 1 个 target_state=raw_json_stored 的 match target
- 1 个 raw_json_status=failed 的 match target（应可重试）
- 1 个 raw_json_status=stale 的 match target（应可重新采集）

## 4. Registry-like seed output

Seed plan 生成以下实体：

- `football_teams`：至少 5 个（4 club + 1 national）
- `football_competitions`：至少 8 个
- `football_competition_editions`：至少 8 个
- `football_team_competition_participation`：至少 10 条
- `football_match_targets`：至少 12 个
- `football_match_target_teams`：至少 24 条（每个 target home+away）
- `football_source_identities`：若干

所有 source_match_id 均为 synthetic/fixture-only 前缀（如 `fixture-mun-epl-001`）。

## 5. Future DB execution policy

- 本 PR 只 dry-run，不执行 INSERT
- 不连接 DB
- SQL preview 文件顶部必须标注 `-- DRY-RUN SQL PREVIEW ONLY`
- 所有 INSERT statements 必须全部注释
- 后续单独 PR `FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-REGISTRY-SEED-DEV-EXECUTION-NO-LIVE-FETCH` 才允许 dev/local seed execution
- seed execution PR 也必须 no live fetch、no raw JSON write、no feature parse

## 6. Target selection dry-run

从 generated registry-like match_targets 中选择：

- `target_state = pending_raw_fetch`
- `raw_json_status in (missing, stale, failed)`
- 跳过 `target_state = blocked`
- 跳过 `target_state = raw_json_stored`
- 按 priority 升序，再按 match_date 升序
- 应用 request_budget / per_team_budget / per_competition_budget

## 7. Team full-calendar query dry-run

验证以下查询：

- Manchester United：查 match_target_teams + match_targets → 跨 Premier League + FA Cup + EFL Cup + UEFA Europa League
- England：查 match_target_teams + match_targets → 跨 WC qualifier + Nations League + Friendly
- Kashima Antlers：跨 J1 League + Emperor's Cup
- Leeds United：跨 EFL Championship + FA Cup

## 8. 安全边界

本阶段明确不做：

- no network fetch
- no DB write
- no SQL execution
- no raw JSON write
- no fotmob_raw_match_payloads write
- no raw_match_data write
- no l3_features write
- no match_features_training write
- no predictions write
- no scheduler enable
- no parser / feature extraction
- no raw_write_ready marking

## 9. 下一阶段建议

推荐：

1. **FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-REGISTRY-SEED-DRY-RUN-REVIEW**（审查本 PR）
2. 审查通过后，**FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-REGISTRY-SEED-DEV-EXECUTION-NO-LIVE-FETCH**（dev seed execution，仍 no live fetch）
3. 然后 **FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-ONE-DAY-NO-FEATURE-PARSE-PREFLIGHT**（one-day preflight authorization）

当前阶段不允许直接 live fetch。
