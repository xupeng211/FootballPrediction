<!-- markdownlint-disable MD013 -->

# FotMob Football Calendar Target Registry 设计

- lifecycle: permanent / governance
- phase: FOTMOB-FOOTBALL-CALENDAR-TARGET-REGISTRY-DESIGN-AND-MIGRATION
- version: 1.0.0
- scope: target registry schema design and migration
- no network fetch / no DB data write / no raw JSON write / no scheduler enable / no feature parse
- raw_write_ready remains false

## 1. 为什么不能只按联赛采集

长期预测系统不能只从某一个联赛赛程里找比赛。球队基本面来自全年所有正式比赛，联赛只是其中一条赛程线。

杯赛、欧战、洲际俱乐部赛事、超级杯、国家队比赛都会影响近期状态、体能、轮换、伤停和教练选择。只采联赛会漏掉赛程密度、连续客场、加时赛消耗、杯赛轮换和国际比赛日影响，最终让 Raw Layer 缺少解释基本面的关键上下文。

例如 Manchester United 的全年比赛不只来自 Premier League，还会来自 FA Cup、EFL Cup、UEFA competitions、Community Shield 或其他赛事。系统必须能按球队还原跨赛事最近 N 场，而不是只看联赛内最近 N 场。

国家队也是独立球队实体。国家队的状态来自世界杯、欧洲杯、美洲杯、亚洲杯、非洲杯、世界杯预选赛、洲际杯赛预选赛、欧国联和重要友谊赛。系统必须能还原国际比赛日和预选赛窗口，不能把国家队比赛排除在长期采集目标之外。

## 2. 总体目标

本阶段建立长期采集目标注册体系，为 future FotMob raw JSON collector 提供稳定、可审计、可扩展的目标来源。

目标注册体系包含以下表：

- `football_teams`
- `football_competitions`
- `football_competition_editions`
- `football_team_competition_participation`
- `football_match_targets`
- `football_match_target_teams`
- `football_source_identities`

这些表只管理目标、身份和赛程关系，不保存 FotMob 原始 JSON，不解析业务字段，不写 features/training/predictions。

## 3. 覆盖范围分层

### 3.1 Tier 0

Tier 0 是必须优先支持的全年采集范围：

- 五大联赛
- UEFA Champions League / Europa League / Conference League
- 主要国内杯赛
- FIFA World Cup / UEFA Euro / Copa America / AFC Asian Cup
- World Cup qualifiers
- UEFA Nations League
- 国家队重要正式比赛

### 3.2 Tier 1

Tier 1 是长期系统应尽快纳入的扩展范围：

- Eredivisie、Primeira Liga、Belgian Pro League、Turkish Super Lig、Scottish Premiership、EFL Championship
- J1 League
- K League
- Major League Soccer
- Brasileirao Serie A / Argentine Primera Division
- AFC Champions League
- Copa Libertadores

### 3.3 Tier 2

Tier 2 作为后续扩展范围：

- 次级联赛
- 各国杯赛早期轮次
- 其他亚洲、欧洲、美洲联赛
- 重要友谊赛，视 FotMob 数据质量和采集成本决定

## 4. 数据模型说明

### 4.1 `football_teams`

用途：保存 FotMob 源上的球队身份，覆盖俱乐部和国家队。

关键字段：

- `source`: 数据源，默认 `fotmob`
- `source_team_id`: FotMob team id
- `team_name`: 球队名称
- `team_type`: `club` 或 `national`
- `country`: 国家或地区
- `gender`: 默认 `men`
- `active`: 是否仍参与采集
- `metadata`: 额外身份信息

唯一约束：`unique(source, source_team_id)`。

状态枚举：`team_type in ('club', 'national')`。

主要索引：`team_type`、`country`、`active`。

### 4.2 `football_competitions`

用途：保存 FotMob 源上的赛事身份，覆盖联赛、杯赛、洲际俱乐部赛事和国家队赛事。

关键字段：

- `source`: 数据源，默认 `fotmob`
- `source_competition_id`: FotMob league/competition id
- `competition_name`: 赛事名称
- `competition_type`: 赛事类型
- `country`: 国内赛事所属国家或地区
- `confederation`: UEFA、CONMEBOL、AFC 等
- `tier`: 采集优先级层级
- `active`: 是否仍参与采集
- `metadata`: 额外赛事信息

唯一约束：`unique(source, source_competition_id)`。

状态枚举：

- `league`
- `domestic_cup`
- `continental_club`
- `international_tournament`
- `international_qualifier`
- `nations_league`
- `friendly`
- `super_cup`
- `other`

主要索引：`competition_type`、`country`、`confederation`、`tier`、`active`。

### 4.3 `football_competition_editions`

用途：保存赛事的具体赛季或届次，例如 `Premier League 2025/2026`、`FA Cup 2025/2026`、`World Cup 2026`。

关键字段：

- `competition_id`: 所属赛事
- `season`: 赛季或届次标签
- `edition_name`: 展示名称
- `start_date` / `end_date`: 赛程时间范围
- `calendar_type`: season、calendar_year、tournament_window 等
- `active`: 是否仍参与采集
- `metadata`: 额外届次信息

唯一约束：`unique(competition_id, season)`。

主要索引：`competition_id`、`season`、`start_date`、`end_date`、`active`。

### 4.4 `football_team_competition_participation`

用途：登记某支球队参加某个赛事届次。它是球队全年日历还原的关键桥梁。

关键字段：

- `team_id`: 球队
- `competition_id`: 赛事
- `edition_id`: 赛事届次
- `participation_state`: 参赛状态
- `qualification_source`: 参赛来源，例如 league table、cup winner、draw、seeded
- `first_seen_at` / `last_seen_at`: 采集系统首次和最近观察时间
- `metadata`: 额外参赛信息

唯一约束：`unique(team_id, competition_id, edition_id)`。

状态枚举：

- `expected`
- `confirmed`
- `eliminated`
- `completed`
- `unknown`

主要索引：`team_id`、`competition_id`、`edition_id`、`participation_state`。

### 4.5 `football_match_targets`

用途：登记未来 raw JSON collector 应采集的 FotMob match detail 目标。它只管理目标，不保存 raw JSON。

关键字段：

- `source`: 数据源，默认 `fotmob`
- `source_match_id`: FotMob match id
- `competition_id`: 赛事
- `edition_id`: 赛事届次
- `match_date`: 比赛时间
- `home_team_id` / `away_team_id`: 主客队
- `match_status`: scheduled、live、finished、postponed、cancelled 等源状态
- `target_state`: 采集目标状态
- `priority`: 采集优先级，数值越小优先级越高
- `discovery_source`: league_schedule、team_calendar、cup_draw、manual 等
- `source_url`: FotMob detail URL
- `raw_json_status`: raw JSON storage 状态摘要
- `last_attempt_at` / `last_success_at`: 采集尝试和成功时间
- `attempt_count`: 尝试次数
- `last_error_code` / `last_error_message`: 最近失败信息
- `metadata`: 额外目标信息

唯一约束：`unique(source, source_match_id)`。

状态枚举：

- `discovered`
- `pending_raw_fetch`
- `raw_fetched`
- `raw_json_stored`
- `blocked`
- `failed`
- `retired`

主要索引：`source/source_match_id`、`competition_id`、`edition_id`、`match_date`、`home_team_id`、`away_team_id`、`target_state`、`raw_json_status`。

### 4.6 `football_match_target_teams`

用途：保存比赛目标和球队的多角色关系。常规足球比赛通常是 home/away，未来也可支持中立场或多参与方上下文。

关键字段：

- `match_target_id`: 比赛目标
- `team_id`: 球队
- `role`: `home`、`away` 或 `participant`

唯一约束：`unique(match_target_id, team_id, role)`。

状态枚举：`role in ('home', 'away', 'participant')`。

主要索引：`match_target_id`、`team_id`、`role`。

### 4.7 `football_source_identities`

用途：保存跨表源身份映射，避免未来引入新 source 或新实体类型时把源 id 写散。

关键字段：

- `source`: 数据源
- `entity_type`: team、competition、edition、match_target 等
- `entity_id`: 本地实体 id
- `source_entity_id`: 源系统实体 id
- `source_url`: 源系统 URL
- `metadata`: 额外映射信息

唯一约束：`unique(source, entity_type, source_entity_id)`。

主要索引：`entity_type/entity_id`、`source/source_entity_id`。

## 5. 球队全年赛程还原逻辑

球队全年赛程必须以 team 为核心：

1. 先识别 `football_teams` 中的 team。
2. 再识别该 team 所属的全部 `football_competitions`。
3. 再识别每个赛事的 `football_competition_editions`。
4. 再通过 `football_team_competition_participation` 记录该队参加哪些赛事届次。
5. 最后把该队关联到 `football_match_targets` 和 `football_match_target_teams`。

这样可以查询某支球队跨赛事最近 N 场比赛。查询 Manchester United 时，结果不应只来自 Premier League，也要覆盖 FA Cup、EFL Cup、UEFA competitions、Community Shield 和未来授权的重要友谊赛。

此模型避免把 `matches` 或单一联赛赛程当作 uncontrolled workflow queue。长期采集目标应由 target registry 明确登记、审计和状态推进。

## 6. 国家队赛程还原逻辑

国家队使用同一套 team 模型，`team_type = 'national'`。

国家队赛事通过 `competition_type` 区分：

- `international_tournament`
- `international_qualifier`
- `nations_league`
- `friendly`

系统应能登记 World Cup、continental tournaments、qualifiers、Nations League 和重要友谊赛。国家队比赛窗口会影响球员负荷和俱乐部赛前基本面，后续 feature 层必须能知道这些比赛存在；当前阶段只建立 raw target registry。

## 7. 与 Raw JSON DB 的关系

`football_match_targets` 只管理采集目标和状态。

`fotmob_raw_match_payloads` 保存 FotMob match detail 原始 JSON，包括 `next_data_json` 和 `page_props_json`。

二者通过以下身份关联：

- `football_match_targets.source`
- `football_match_targets.source_match_id`
- `fotmob_raw_match_payloads.source`
- `fotmob_raw_match_payloads.match_id`

Target registry 不保存原始 JSON，不保存完整 pageProps，不保存 HTML body。Raw JSON DB 是 raw layer 的持久化来源；target registry 是 collector 的目标和审计控制面。

## 8. 状态机

### 8.1 `target_state`

```text
discovered
  -> pending_raw_fetch
  -> raw_fetched
  -> raw_json_stored
```

异常分支：

- `blocked`: 403、429、captcha、source policy blocker、identity blocker
- `failed`: 单目标失败，可在后续授权下重试
- `retired`: 比赛取消、目标废弃或源身份不再有效

### 8.2 `participation_state`

```text
expected -> confirmed -> eliminated
expected -> confirmed -> completed
unknown  -> expected
unknown  -> confirmed
```

解释：

- `expected`: 预计参赛，但还未被可靠源确认
- `confirmed`: 已确认参赛
- `eliminated`: 杯赛或淘汰赛出局
- `completed`: 该届赛事已完成
- `unknown`: 发现早期信息不足

### 8.3 `competition_type`

允许值：

- `league`
- `domestic_cup`
- `continental_club`
- `international_tournament`
- `international_qualifier`
- `nations_league`
- `friendly`
- `super_cup`
- `other`

### 8.4 `team_type`

允许值：

- `club`
- `national`

## 9. 安全边界

本阶段只新增设计、schema migration、manifest、只读本地 helper 和测试。

本阶段不做：

- no FotMob network fetch
- no live fetch
- no writes to `fotmob_raw_match_payloads`
- no raw JSON payload write
- no writes to `raw_match_data`
- no writes to `l3_features`
- no writes to `match_features_training`
- no writes to `predictions`
- no scheduler enable
- no parser implementation
- no feature parsing
- no model training
- no raw_write_ready marking

## 10. 下一阶段

下一阶段应是 `FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-DRY-RUN`。

前提条件：

- target registry migration 通过 review
- 新表结构能支持 club 和 national team calendars
- collector dry-run 只读取 registry，不触 FotMob live source
- raw write 仍需单独授权，且 raw_write_ready remains false
