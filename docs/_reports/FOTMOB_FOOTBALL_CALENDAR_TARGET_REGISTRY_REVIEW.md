<!-- markdownlint-disable MD013 -->

# FotMob Football Calendar Target Registry Review

- lifecycle: current-state
- phase: FOTMOB-FOOTBALL-CALENDAR-TARGET-REGISTRY-REVIEW
- reviewed PR: #1423
- reviewed migration path: `database/migrations/V26.6__create_football_calendar_target_registry.sql`
- reviewed design doc path: `docs/data/FOTMOB_FOOTBALL_CALENDAR_TARGET_REGISTRY_DESIGN.md`
- reviewed manifest path: `docs/_manifests/fotmob_football_calendar_target_registry_design_manifest.json`
- registry_foundation_status: `foundation_solid`

## Migration Review

V26.6 创建了 7 张目标注册基础表：`football_teams`、`football_competitions`、`football_competition_editions`、`football_team_competition_participation`、`football_match_targets`、`football_match_target_teams`、`football_source_identities`。

迁移内容只包含 create table、create index 和 comment。未发现 destructive SQL、seed data insert、既有表数据改写或无关表结构变更。表间关系覆盖 team、competition、edition、participation、match target 和 source identity，能作为长期 target registry 基础。

## Club Calendar Coverage Review

设计支持 `team_type = club` 的俱乐部全年赛程。俱乐部可通过 `football_team_competition_participation` 进入多个赛事届次，再通过 `football_match_targets` 与 `football_match_target_teams` 关联到具体比赛。

这意味着 Manchester United 这类球队不应只采 Premier League；同一球队可覆盖 FA Cup、EFL Cup、UEFA competitions、Community Shield 和未来授权的重要友谊赛。该结构能表达联赛、国内杯赛、洲际俱乐部赛事、超级杯和可扩展友谊赛。

## National Team Coverage Review

设计支持 `team_type = national` 的国家队。国家队赛事可作为 `football_competitions` 登记，并通过 `competition_type` 表达 `international_tournament`、`international_qualifier`、`nations_league` 和 `friendly`。

国家队 match target 可进入同一 raw JSON 采集系统；世界杯、洲际杯赛、预选赛、欧国联和重要友谊赛不会被联赛模型排除。

## Secondary / Global Coverage Review

schema 不绑定单一联赛，也不绑定欧洲主流赛事。`football_competitions.country`、`confederation`、`tier` 和 `competition_type` 能表达英冠、J1/J2、K League、MLS、Brasileirao Serie A、Argentine Primera Division、AFC Champions League、Copa Libertadores 以及后续扩展赛事。

本阶段不要求 seed 这些赛事；审查结论是 schema 能表达这些对象。

## Team Full-Calendar Reconstruction Review

球队全年日历可通过以下关系还原：`football_teams` -> `football_match_target_teams` -> `football_match_targets` -> `football_competitions` / `football_competition_editions`。

查询某支球队最近 N 场比赛时，可以按 team id 聚合 home、away 或 participant 角色，并跨赛事按 `match_date` 排序，而不是只查某一个 league。

## Raw JSON DB Integration Review

registry 只管理采集目标和状态，不保存完整 raw JSON、pageProps 或 HTML body。raw table `fotmob_raw_match_payloads` 保存原始 JSON。

关联路径明确：`football_match_targets.source + source_match_id` 对应 `fotmob_raw_match_payloads.source + match_id`。这满足 raw-first、parse-later 的长期采集设计。

## State Machine Review

`target_state` 覆盖 discovered、pending_raw_fetch、raw_fetched、raw_json_stored、blocked、failed、retired。

`participation_state` 覆盖 expected、confirmed、eliminated、completed、unknown。

`competition_type` 覆盖 league、domestic_cup、continental_club、international_tournament、international_qualifier、nations_league、friendly、super_cup、other。

`team_type` 覆盖 club、national。

## Safety Review

本 review 阶段未执行网络请求、DB 写入、migration、raw JSON 写入、scheduler、feature parser、raw_match_data 写入、l3_features 写入、match_features_training 写入或 predictions 写入。`raw_write_ready` 保持 false。

## Business Fit Review / 业务适配审查

这套 registry 满足“全年都有比赛可分析和预测”的基础目标：它把球队放在中心位置，不再把采集目标限制在单一联赛。杯赛、欧战、国家队比赛和次级联赛都能进入同一目标注册体系，从而为后续 raw JSON 长期采集提供完整的跨赛事上下文。

它能支撑俱乐部全年比赛还原、国家队比赛还原、杯赛纳入基本面、次级联赛未来扩展，以及 FotMob raw JSON target 管理。当前阶段没有开启 parser/feature；parser/feature 是未来阶段，不属于当前 review。

## Remaining Gaps

- 没有 seed 任何真实 team、competition 或 match target。
- 没有 discovery crawler。
- 没有 dry-run collector。
- 没有 live fetch。
- 没有 scheduler。
- 没有 target registry review 后的 collector dry-run。
- 没有全量国家队、杯赛、J1/J2、K League、MLS、南美赛事覆盖数据。
- 没有 parser/feature layer。

## Recommended Next Phase

推荐下一阶段：`FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-DRY-RUN`。

该 dry-run 不应 live fetch，除非未来单独授权。它应只读取 target registry schema，生成 synthetic/sample targets，验证 target selection query，验证 team full-calendar query，验证 pending_raw_fetch 队列逻辑，并生成 dry-run collection plan；不得访问 FotMob，不得写 raw JSON，不得写 raw_match_data。
