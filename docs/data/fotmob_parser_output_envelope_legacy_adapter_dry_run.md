# FotMob Parser Output Envelope Legacy Adapter Dry Run

- lifecycle: source-of-truth
- scope: dry-run-only adapter implementation for DATA-L1E-2
- parent documents: DATA-L1F-2B (`docs/data/fotmob_nextdata_thin_parsers_output_shape_audit.md`), DATA-L1E-1 (`src/parsers/fotmob/FotMobParserOutputEnvelope.js`)
- branch: `feat/data-l1e-2-fotmob-envelope-legacy-adapter-dry-run`

---

## 1. 背景

用户已接受 DATA-L1F-2B 推荐的 Boundary A：`NextDataParser.transformToApiFormat` 输出。

本 PR 实现 DATA-L1E-2：一个 dry-run-only legacy adapter，把 `transformToApiFormat` 输出包装成 `FotMobParserOutputEnvelope` 兼容结构。

**这不是 production integration。** Adapter 是纯函数，不接入 runtime，不修改 `NextDataParser`、`FotMobStrategy`、`FotMobRawDetailFetcher`、parser index exports、feature engine、training、backtest、DB、raw storage、scraper、collector、CI。

---

## 2. Adapter boundary

| 维度 | 值 |
| --- | --- |
| **输入边界** | `NextDataParser.transformToApiFormat` 输出 `{ matchId, content, general, header, _meta }` |
| **Adapter 文件** | `src/parsers/fotmob/FotMobParserOutputEnvelopeLegacyAdapter.js` |
| **测试文件** | `tests/unit/parsers/fotmob/FotMobParserOutputEnvelopeLegacyAdapter.test.js` |
| **文档文件** | `docs/data/fotmob_parser_output_envelope_legacy_adapter_dry_run.md` |
| **依赖** | `FotMobParserOutputEnvelope.js`（使用其 constants、factory、validator） |
| **不依赖** | NextDataParser（不 import、不调用 transformToApiFormat）、FotMobStrategy、FotMobRawDetailFetcher、feature engine、DB |

---

## 3. Mapping strategy

### 3.1 matchId

`transformOutput.matchId` → `envelope.match_id`（字符串形式）。作为 `metadata_only` / `audit_only` 字段进入 fields 数组——允许用于 join/filter，禁止作为模型特征。

### 3.2 content / general / header

整块进入 fields 数组，标记为 `raw_only` / `forbidden_raw_only`。这些是原始 pageProps 数据块，只能作为审计证据，不能直接作为模型特征。

### 3.3 content.stats / content.shotmap / content.events / content.playerStats

标记为 `postmatch` / `forbidden_postmatch`。这些是比赛中或比赛后才能产生的数据（xG/shots/possession/shotmap/events/playerStats），绝对禁止进入赛前模型。

### 3.4 content.lineup / content.injury / content.odds / content.table / content.form

标记为 `unknown_timing` / `forbidden_unknown_timing`。这些字段可能在赛前可知（如 lineup 在开赛前 1 小时公布），但没有 `observed_at`/`cutoff` 证据，第一版保守禁止。

### 3.5 _meta 子字段

`source` / `hasStats` / `hasLineup` / `hasShotmap` 逐个展平进入 fields 数组，标记为 `audit_only`。

### 3.6 _meta.extractedAt

作为 `audit_only` 字段始终保留，附带明确的 warning：
- 如果 `captured_at` 或 `fetched_at` 存在：标注为补充审计证据
- 如果两者都不存在：明确警告不要将 `extractedAt` 当作 `captured_at`/`fetched_at`

### 3.7 payload metadata 缺失处理

| 字段 | 预期来源 | 缺失时的值 | 处理原则 |
| --- | --- | --- | --- |
| `payload_type` | 硬编码 | `parser_input` | adapter 已知输入类型 |
| `data_version` | FotMobRawDetailFetcher | `'unknown'`（未传 options 时）；`null`（显式传 null 时） | 不伪造 |
| `payload_hash` | FotMobRawDetailFetcher | `null` | 不伪造 |
| `storage_path` | FotMobRawDetailFetcher | `null` | 不伪造 |
| `captured_at` | FotMobRawDetailFetcher | `null` | 不伪造；不从 `extractedAt` 冒充 |
| `fetched_at` | FotMobRawDetailFetcher | `null` | 不伪造 |
| `source_url` | FotMobRawDetailFetcher | `null` | adapter 没有 |
| `final_url` | FotMobRawDetailFetcher | `null` | adapter 没有 |

### 3.8 parser metadata

| 字段 | 值 | 说明 |
| --- | --- | --- |
| `parser_name` | `NextDataParser.transformToApiFormat` | adapter 明确标注 parser 来源 |
| `parser_version` | `legacy-static` | 标注这是静态 legacy 分析版本 |
| `parsed_at` | `null` | 不伪造 parser 执行时间 |

---

## 4. Safety strategy

### 4.1 分类优先级

1. **postmatch 前缀匹配** → `forbidden_postmatch`（最高优先级）
2. **unknown_timing 前缀匹配** → `forbidden_unknown_timing`
3. **raw_only 前缀匹配** → `forbidden_raw_only`
4. **默认** → `forbidden_unknown_timing`（保守兜底）

### 4.2 明确 forbidden_postmatch 的字段

```text
content.stats          — 比赛统计数据（xG/shots/possession/corners/fouls 等）
content.shotmap        — 射门图数据
content.events         — 比赛事件时间线
content.playerStats    — 球员评分/统计
content.momentum       — 比赛动量数据
content.matchFacts     — 比赛事实数据
header.teams.score     — 比分（赛后才知道）
header.status.scoreStr — 比分字符串
header.status.winner   — 胜者
header.status.result   — 比赛结果
general.score/result/winner — 同上
```

这些字段全部标记：
- `field_contract_class`: `unsafe_postmatch`
- `timing_class`: `postmatch`
- `model_eligibility`: `forbidden_postmatch`

### 4.3 明确 forbidden_unknown_timing 的字段

```text
content.lineup        — lineup 时机不确定（可能赛前 1h 公告，也可能赛后更新）
content.injury        — 伤病信息时机不确定
content.odds          — 赔率数据时机不确定
content.table         — 积分榜快照时机不确定
content.form          — 近期战绩快照时机不确定
content.standings     — 排名数据时机不确定
```

标记为：
- `field_contract_class`: `unknown_timing`
- `timing_class`: `unknown_timing`
- `model_eligibility`: `forbidden_unknown_timing`

### 4.4 第一版保守策略

- **本 adapter 不产生任何 `ALLOWED_CANDIDATE` 或 `CANDIDATE_IF_CUTOFF_VALID` 标记。**
- 所有看似赛前可知的字段（matchId、team name、match date）也被保守标记（`audit_only` 或 `forbidden_raw_only`）。
- 目标不是最大化 safe fields，而是防止假 safe 泄漏。

---

## 5. What changed

| 文件 | 操作 | 说明 |
| --- | --- | --- |
| `src/parsers/fotmob/FotMobParserOutputEnvelopeLegacyAdapter.js` | 新增 | Dry-run adapter 纯函数模块 |
| `tests/unit/parsers/fotmob/FotMobParserOutputEnvelopeLegacyAdapter.test.js` | 新增 | 57 个单元测试 |
| `docs/data/fotmob_parser_output_envelope_legacy_adapter_dry_run.md` | 新增 | 本文档 |

---

## 6. What did not change

- 没有改 `NextDataParser.js`
- 没有改 `FotMobStrategy.js`
- 没有改 `FotMobRawDetailFetcher.js`
- 没有改 `FotMobParserOutputEnvelope.js`
- 没有改 `src/parsers/fotmob/index.js`
- 没有接 runtime
- 没有访问 FotMob 网络
- 没有运行采集
- 没有写 DB/raw/data
- 没有改 feature/training/backtest

---

## 7. Test coverage

| 测试类 | 测试数 | 覆盖内容 |
| --- | --- | --- |
| `classifyField` | 18 | 所有路径前缀匹配（postmatch/unknown/raw）、优先级、默认 fallback |
| `flattenTransformOutputFields` | 12 | happy path 各区块、matchId、content 整块、stats/shotmap/lineup/events 标记、\_meta 展平、精简输入保守性 |
| `adaptTransformToApiFormatOutputToEnvelope` | 27 | happy path envelope shape、payload/parser metadata 默认值、warnings、matchId 保留、安全标记验证、metadata 保留/不覆盖、options 覆盖、invalid input（null/undefined/空/字符串/数字/最小合法）、保守策略、schema validation（3 种场景）、data_version 处理 |

全部 57 个测试通过。

---

## 8. Remaining gaps

| gap | 说明 |
| --- | --- |
| 只验证 transformToApiFormat output | 没有证明真实 DB 中所有 raw_match_data 都能适配 |
| 没有运行真实 parser | 测试使用手工构造的 fixture，不是真实 FotMob 数据 |
| 没有确认 production scheduler | 不确定生产环境中哪个 scheduler/cron 实际调用 NextDataParser |
| 没有确认 feature engine 消费 envelope | Feature engine 仍通过 SQL 直接读 raw_match_data，不 import adapter |
| 没有生成 safe_prematch 白名单 | 第一版全部保守标记，没有字段被放行 |
| 没有 field-level flatten | 只有顶层和高风险区块展平，嵌套字段未深度展开 |
| metadata 主要来自 options | adapter 本身不查询 FotMobRawDetailFetcher 或 DB 来补 metadata |

---

## 9. Next recommended task

推荐：

```text
DATA-L1E-3: Fixture-Based Envelope Dry-Run Evidence
```

DATA-L1E-3 应该：
1. 使用真实 transformToApiFormat 输出的 snapshot fixture（从已审计的文档或测试中提取）。
2. 验证 adapter 对真实 FotMob 数据结构的兼容性。
3. 确认 envelope 是否足够支持后续字段级合同校验。
4. 仍然 dry-run——不接 runtime、不写 DB。

**Do not start automatically.**

**Recommended next task only after user confirmation.**
