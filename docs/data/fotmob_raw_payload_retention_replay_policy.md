# FotMob Raw Payload Retention and Replay Policy

- lifecycle: source-of-truth
- scope: docs-only, FotMob raw payload 保留与回放策略
- parent audits: DATA-L1A（`docs/_reports/data_l1a_fotmob_prematch_boundary_audit.md`）
- parent contract: DATA-L1B（`docs/data/fotmob_prematch_field_contract.md`）
- branch: `docs/data-l1c-fotmob-raw-retention-replay-policy`

---

## 1. 背景

DATA-L1A 已经完成并合并（PR #1694）。它在仓库里做了一次只读审计，发现 FotMob raw payload、pageProps、HTML hydration、parser 输出之间存在字段边界风险。

DATA-L1B 已经完成并合并（PR #1695）。它建立了一份 FotMob 赛前字段合同，把字段分成 5 类：safe_prematch_candidate、unsafe_postmatch、unknown_timing、metadata_only、debug_or_raw_only。

DATA-L1C 的目标不是继续分类字段（那是 DATA-L1B 的工作）。DATA-L1C 要规定的是：**原始 payload 怎么保留、怎么留证据、以后 parser 坏了怎么回放、字段的时间边界怎么追溯**。

可以用一个类比来理解这三步的关系：

```text
DATA-L1A = 查到仓库里有危险食材的审计报告
DATA-L1B = 写食材安全清单（什么能吃、什么不能吃、什么不确定）
DATA-L1C = 规定进货小票、原包装、监控录像怎么保存，方便以后追责和复盘
```

本文件是 raw payload 保留与回放策略。它不改造 scraper、不改造 parser、不改造 DB / migration、不改造 feature engine、不运行 training。它不运行任何采集。它不证明 raw payload 已经被系统正确保存。它只立规则。

---

## 2. 为什么必须保留 raw payload

这个问题值得说清楚，因为它决定了后续所有工作的可信度。

### 2.1 六个必须保留的原因

1. **parser 回放。** 如果只保存 parser 处理后的字段（比如 xG、score、lineup），未来 parser 代码改了，你无法确认"旧 parser 当时从这个 raw payload 里解析出了什么"。没有原始输入，回放就是一句空话。

2. **schema drift 检测。** FotMob 可能会改页面结构——新增字段、删除字段、重命名字段、移动字段位置。如果你不保存当时的 raw payload，等你发现 parser 坏了的时候，你已经拿不到那时候的页面结构了。

3. **字段来源审计。** 如果模型结果异常——比如回测 AUC 突然从 0.67 跳到 0.85——你需要追溯：这个 feature 是从哪个 raw payload 的哪一层解析出来的？在 cutoff 之前这个字段存在吗？

4. **cutoff safety audit。** raw payload 的 `captured_at` 不等于其中每个字段的 `observed_at`。一张赛后抓取的 JSON 可能同时包含赛前的 league/season 和赛后的 xG/shots/score。没有 raw payload + metadata，你无法证明某个字段在 cutoff 前是安全可用的。

5. **data_version 和 source fidelity。** DATA-L1A 发现 `raw_match_data` 存在 mixed provenance（不同来源的数据混在同一个表里）。如果不保留原始 payload 和 data_version，你无法区分哪个字段来自哪个版本的 FotMob。

6. **事故复盘。** 如果线上预测出了严重的偏差，你必须能回答：当时输入的 raw payload 是什么样的？parser 提取了什么？feature engine 生成了什么？如果没有原始 payload，你只能对着最终数字干瞪眼。

### 2.2 一个简单类比

```text
raw payload      = 监控录像 / 原始试卷 / 事故现场照片
parser 输出      = 笔录 / 调查报告
training dataset = 总结分析

没有原始证据，后面很难复盘。
```

---

## 3. 核心原则

这些原则是本策略的基石。优先级高于具体操作细节。

1. **raw payload 是审计证据，不是模型特征。** 它不能被直接喂给模型。它的角色是"证据"，不是"食材"。

2. **raw payload / pageProps / `__NEXT_DATA__` / HTML hydration 不能直接进入模型。** 这些原始数据同时包含赛前和赛后字段。整块喂给模型等于把 DATA-L1B 的所有禁用规则全部绕过。

3. **每份 raw payload 必须尽量保留 `captured_at`。** 没有采集时间，这份 payload 什么都证明不了。

4. **每份 raw payload 必须尽量保留 `source_url` / `final_url` / `match_id` / `source` / `data_version`。** 这些是追溯字段来源的最小信息集。

5. **每份 raw payload 必须尽量有 `payload_hash`。** 用于去重（同一场比赛抓了两次拿到的相同内容）、完整性校验（文件有没有损坏）、版本比较。

6. **raw payload 必须支持 parser replay。** 这是它最重要的使用场景：未来换 parser、修 bug、加字段、做回归测试，都要靠历史 payload。

7. **raw payload 必须支持 schema drift 检测。** 不同时间采集的同一 league/route 的 payload 可以用来比较 FotMob 结构变化。

8. **raw payload 必须支持字段来源审计。** 每一个从 raw payload 派生出来的 feature，都应该能追溯到 raw payload 的位置 + 采集时间 + parser 版本。

9. **raw payload 必须支持 cutoff safety audit。** 结合 DATA-L1B 字段合同，判断字段在特定 prediction_cutoff_time 是否安全可用。

10. **任何从 raw payload 派生出来的 feature，都必须能追溯到 `observed_at` / `captured_at` / `parser_version`。** 没有这条，无法做 cutoff 检查。

11. **如果无法证明字段在 `prediction_cutoff_time` 前可用，默认不允许进入模型。** 这是 DATA-L1B 的规则，本合同直接引用。

12. **保留策略必须服务 DATA-L1B 字段合同。** raw payload 的 metadata 应该包含 `contains_postmatch_fields`、`contains_live_fields`、`contains_prematch_fields` 等标记，帮助判断这份 payload 的风险等级。

---

## 4. raw payload 范围定义

下面定义 DATA-L1C 要管理的东西是什么。这些概念在仓库和 DATA-L1A 中反复出现，但含义不完全相同。这里给出正式定义。

| 概念 | 含义 | 是否应该保留 | 是否允许进入模型 | 用途 | 风险 |
| --- | --- | --- | --- | --- | --- |
| **raw payload** | FotMob API 返回的完整 JSON 或等效原始数据 | ⚠️ 按 retention_class 决定（见 §6） | **不允许。** 属于 debug_or_raw_only | parser replay / schema drift / 来源审计 | 包含赛后字段，整块喂模型 = 泄露 |
| **pageProps** | FotMob SSR 页面中的 `pageProps` 对象（Next.js 服务端渲染数据） | ⚠️ 按 retention_class 决定 | **不允许。** 属于 debug_or_raw_only | parser replay / SSR 结构审计 | 混合了 match/league/content/stats/live 等多个模块 |
| **`__NEXT_DATA__`** | FotMob 页面内联的 Next.js 序列化数据（`<script id="__NEXT_DATA__">`） | ⚠️ 按 retention_class 决定 | **不允许。** 属于 debug_or_raw_only | Next.js SSR 结构审计 / parser 对比 | 与 pageProps 有重叠但不完全相同 |
| **HTML hydration** | FotMob SSR 页面完整 HTML（包含水合数据、NEXT_DATA、内联 JSON） | ⚠️ 按 retention_class 决定（通常更大） | **不允许。** 属于 debug_or_raw_only | 完整页面结构审计 / anti-bot 分析 | 体积大，可能包含动态 token/cookie 痕迹 |
| **raw JSON**（与 raw payload 同义） | FotMob API 返回的纯 JSON（不嵌在 HTML 里） | ⚠️ 按 retention_class 决定 | **不允许。** 属于 debug_or_raw_only | API route discovery / schema 对比 | 不同 API route 的结构不同 |
| **parser input** | parser 接收的输入数据（可能是 raw payload 的子集或转换产物） | ✅ 应该保留（以便 replay） | 作为 parser 输入，不作为模型特征 | parser 回归测试 | 如果已转换，不等同于原始 raw payload |
| **parser output** | parser 解析后的结构化字段 | ✅ 可以作为中间数据保留 | 只有通过 DATA-L1B 字段合同允许的字段才可进入模型 | feature engine 输入 | parser 输出不等于"赛前字段"，需要过合同过滤 |
| **parser replay fixture** | 专门用于 parser 回归测试的 raw payload 快照 + expected output | ✅ **强烈建议保留**（特别是 critical 等级） | **不允许** | parser 回归测试 / CI | 如果是"手工构造的理想输入"，不代表真实 raw payload 的质量 |
| **schema snapshot** | 某个时间点、某个 route、某个 data_version 的 raw payload 字段清单 | ✅ 建议保留（JSON schema / field list） | 作为审计证据，不作为模型特征 | schema drift 检测 | schema snapshot 本身不包含字段值，不能替代 raw payload |
| **debug trace** | parser 运行过程中产生的中间调试信息 | ⚠️ short_lived 等级 | **不允许。** 属于 debug_or_raw_only | parser 调试 | 可能包含敏感信息或大量中间数据 |
| **capture metadata** | 与 raw payload 一起保存的元信息（captured_at、source_url、payload_hash 等） | ✅ **必须保留**（见 §5） | 可以用于审计/时间校验（metadata_only），不作为模型特征 | 来源追溯、cutoff 校验、去重 | metadata 本身不泄露比赛结果 |

### 重要说明

- 以上所有 raw/x 概念都属于 DATA-L1B 定义的 `debug_or_raw_only` 分类。
- 它们唯一合法的用途是：parser replay、schema drift 检测、字段来源审计、cutoff safety audit、事故复盘。
- "⚠️ 按 retention_class 决定" 的意思是：critical 等级必须保留，standard 等级尽量保留，short_lived 临时保留，discard_candidate 可在未来清理任务中删除。
- 本策略不删除任何数据，不移动文件，只定义保留等级。

---

## 5. 每份 raw payload 必须保留的 metadata

每一份 raw payload 都应该附带一个 metadata 记录。以下表格定义什么字段应该保留、为什么需要它。

### 5.1 必需字段

| metadata 字段 | 用途 | 示例 | 风险说明 |
| --- | --- | --- | --- |
| `source` | 标识数据来源（FotMob API / FotMob SSR / OddsPortal / 其他） | `"fotmob_matchdetails_api"` | 如果标错来源，后续所有追溯都错 |
| `match_id` / `external_id` | 标识这场比赛 | `"123456"` | 同一场比赛可能在不同 data_version 下有不同 id |
| `captured_at` | payload 被抓取的时间戳（ISO 8601） | `"2026-07-03T14:30:00Z"` | 这是判断 cutoff 安全的基础，缺失则 payload 无法用于审计 |
| `payload_type` | payload 的类型（raw_json / pageProps / NEXT_DATA / html_hydration / parser_input） | `"pageProps"` | 不同类型对应不同的 parser 入口 |
| `payload_hash` | SHA-256 或其他强哈希，用于去重和完整性校验 | `"a1b2c3..."` | 如果 hash 变了但 match_id 相同，说明 FotMob 数据可能更新了 |
| `storage_path` | payload 在存储中的位置（可以是文件路径、DB 引用等） | `"raw/fotmob/2026/ligue1/123456/20260703_143000_a1b2c3.json"` | 如果路径丢失，payload 就是"找不到的证据" |
| `is_replayable` | 这份 payload 能不能被 parser 成功读取（true/false） | `true` | 不能 replay 的 payload 保留价值大打折扣 |

### 5.2 强烈建议字段

| metadata 字段 | 用途 | 示例 | 风险说明 |
| --- | --- | --- | --- |
| `source_url` | 原始请求 URL（可能会变、可能会过期） | `"https://www.fotmob.com/api/matchDetails?matchId=123456"` | 同一 route 的参数可能随时间变化 |
| `final_url` | 经过 redirect 后的最终 URL | `"https://www.fotmob.com/en-us/matches/liverpool-vs-man-city/..."` | 用于确认 route 是否正确 |
| `capture_method` | 采集方式（api_direct / ssr_page / browser / proxy / local_file） | `"api_direct"` | 不同采集方式可能导致 payload 结构不同 |
| `parser_version` | 成功解析该 payload 的 parser 版本 | `"fotmob_raw_parser_v3.1"` | 如果 parser 升级了，需要知道"哪个版本当时能解析这份 payload" |
| `content_length` | payload 的字节数 | `145230` | 如果同样的 match_id 突然从 50KB 变成 200KB，说明 FotMob 结构可能变了 |
| `http_status` | HTTP 状态码 | `200` | 404/403/429 的 payload 可能不应该保留 |
| `language` / `locale` | payload 的语言/地区 | `"en-us"` | 不同 locale 的字段名称可能不同 |
| `data_version` | 数据版本标记 | `"fotmob_live_v1"` | 用于区分同一场比赛的不同版本 raw payload |
| `contains_postmatch_fields` | 是否包含赛后字段（基于 DATA-L1B 判断） | `true` / `false` / `unknown` | 标记为 true 的 payload 提取 feature 时必须特别小心 |
| `contains_live_fields` | 是否包含比赛实时字段 | `true` / `false` / `unknown` | 赛中抓取的 payload 和赛前抓取的不一样 |
| `contains_prematch_fields` | 是否包含赛前字段 | `true` / `false` / `unknown` | 用于确认这份 payload 是否可以作为赛前信息的证据 |

### 5.3 可选但有价值的字段

| metadata 字段 | 用途 | 风险说明 |
| --- | --- | --- |
| `request_started_at` | 请求开始时间 | 帮助判断采集耗时，区分"采集慢了"还是"数据晚了" |
| `request_finished_at` | 请求结束时间 | 同上 |
| `timezone` | 时区信息 | 不同时区的 `captured_at` 可能不一致 |
| `payload_version` | payload 自身的版本号（如果 FotMob 内部有版本标记） | 与 data_version 不同，这是 FotMob 侧的结构版本 |
| `user_agent_family` | User-Agent 类型 | 不同 UA 可能得到不同的 payload |
| `proxy_region` | 代理所在地区 | 不同地区的 FotMob 可能有不同的数据 |
| `browser_mode` | 是否使用了浏览器采集 | browser 模式可能得到更多字段（如 cookie 相关） |
| `anti_bot_status` | 是否触发反爬（200 但内容为验证页 / 403 / 429 等） | 触发了反爬的 payload 可能内容不完整 |
| `retention_class` | 保留等级（critical / standard / short_lived / discard_candidate） | 见 §6 |
| `notes` | 自由文本备注 | 记录特殊情况 |

### 5.4 metadata 设计原则

- 不要为了省事把所有字段都标 "unknown"。`contains_postmatch_fields` 为 unknown 时，这份 payload 对 cutoff audit 的价值有限。
- metadata 可以用 sidecar 文件（与 payload 同目录，不同的 `.meta.json` 文件）或 DB 行来存储。本策略不规定具体实现方式。
- metadata 字段本身属于 DATA-L1B 的 metadata_only 分类。它们用于联合查询、审计、时间校验，不作为模型特征。

---

## 6. raw payload 分类与保留等级

不是所有 raw payload 都同等重要。以下定义 4 个保留等级。

| 保留等级 | 含义 | 保留建议 | 典型场景 | 清理规则 |
| --- | --- | --- | --- | --- |
| **critical** | 顶级重要，不能丢 | **必须保留**，不可删除 | 已进入训练/回测链路的样本的 raw payload；字段合同验证的关键比赛；parser 回归测试 fixture；有已知 schema 异常的 payload | 永久保留，除非被正式的 data life cycle cleanup PR 明确授权清理 |
| **standard** | 正常保留 | **尽量保留**，存储允许的情况下不删除 | 普通联赛比赛的 raw payload，用于后续 parser 验证和 schema 审计 | 可以先保留，未来 CLEANUP 任务中评估是否降级 |
| **short_lived** | 临时保留 | 保留一段时间后可清理 | 调试用的临时 payload；格式损坏但仍可部分解析的 payload；重复抓取 3 次以上的同一 match_id 重复 payload | 可在清理任务中删除 |
| **discard_candidate** | 标记为可丢弃 | 未来清理任务中优先删除 | 无 match_id 的 payload；无 captured_at 的 payload；HTTP 4xx/5xx 且内容为错误页面的 payload；payload_hash 为 null 或空的记录；is_replayable = false 且内容不可恢复 | 等待清理任务确认后删除 |

### 6.1 分类原则

- 同一场比赛可能有多个 raw payload（赛前抓的 API、赛后抓的 pageProps、赛中抓的 HTML hydration）。每个 payload 独立判断 retention_class。
- 一条 raw payload 如果曾被用于 training / backtest，自动升为 critical。
- **本 PR 不删除任何 raw payload。** 不移动文件。不修改数据。不实现清理脚本。只定义规则。

---

## 7. parser replay 策略

### 7.1 什么是 parser replay

parser replay 的意思是：不用重新访问 FotMob 网络，用保存好的历史 raw payload，重新跑一次 parser，看结果是不是和之前一样。

### 7.2 replay 最少需要什么

| 项目 | 说明 |
| --- | --- |
| raw payload 内容 | 必须有，这是最基本的 |
| payload_type | 告诉 replay runner 用哪个 parser 入口 |
| captured_at | 记录这份 payload 是什么时候抓的 |
| match_id / external_id | 标识比赛 |
| parser_version | 当时用哪个版本的 parser 解析的 |
| expected parser output shape | parser 输出的字段清单，用于对比 |
| schema snapshot 或字段清单 | 最好是当时保存的 schema snapshot |

### 7.3 replay 可以用于什么

1. **parser 回归测试**：parser 代码改了，用历史 payload 跑一遍看有没有 break。
2. **FotMob 页面结构变更排查**：parser 突然不能解析某类 payload 了，拿出旧 payload 对比新 payload 的结构差异。
3. **old parser vs new parser 对比**：确认新 parser 的输出和旧 parser 一致（或知道哪里不一样）。
4. **字段来源追溯**：某个 feature 值是从 raw payload 的哪一层提取的？用 replay 追回去。
5. **schema drift 检测**：不同时间的 payload 字段清单比较（见 §8）。
6. **数据泄露审计**：确认 parser 是否错误地把赛后字段当成赛前字段输出了。

### 7.4 本 PR 不做什么

- 不创建 replay runner。
- 不新增测试。
- 不运行 parser。
- 不修改 `src/parsers/**`。
- 不修改 `tests/**`。
- 只定义 replay 策略。

---

## 8. schema drift 检测策略

### 8.1 什么是 schema drift

FotMob 不是静态的。它可能会：

- 新增字段（比如突然多了一个 `xG_alternative`）
- 删除字段（以前的 `expectedGoals` 改名了或者没了）
- 重命名字段（`homeTeam` 变成 `home_team`）
- 字段类型变化（`matchId` 从数字变成字符串）
- 字段路径变化（`content.matchFacts.infoBox` 变成 `content.stats.infoBox`）
- pageProps 模块重组（原来在 `general` 里的信息跑到 `header` 了）
- `__NEXT_DATA__` 结构变化
- match stats block 新增/删除统计项
- odds block 结构变化
- lineup block 字段变化

### 8.2 怎么检测

保存不同时间点的 raw payload，提取它们的字段清单（schema snapshot），比较差异。

未来可以做一个简单的工具：

```text
输入：两个不同时间的同 league/route raw payload
输出：字段差异清单（新增 / 删除 / 重命名 / 类型变化 / 路径变化）
```

### 8.3 重要警告

schema drift 检测只告诉我们**结构变了**。它不告诉我们新字段能不能用于赛前模型。**字段进入模型仍然必须遵守 DATA-L1B 字段合同。**

举例：FotMob 新增了一个 `xG_expected_by_home_team`，schema drift 检测发现了。但根据 DATA-L1B，xG 相关字段属于 `unsafe_postmatch`，仍然不能进入模型。不能因为"这是个新字段，之前没有规则覆盖"就默认安全。

---

## 9. cutoff safety audit 策略

这是 DATA-L1C 最重要的部分之一。raw payload 的保留最终是为了回答这个问题：

**这个字段，在 prediction_cutoff_time 之前，存在吗？**

### 9.1 三个关键时间概念

| 时间概念 | 含义 | 用途 |
| --- | --- | --- |
| `prediction_cutoff_time` | 模型预测的时间点。这个时间之后的信息，模型不能"知道" | 决定哪些信息不可用 |
| `captured_at` | raw payload 被采集的时间 | 帮助判断 payload 整体是否赛前存在 |
| `observed_at` | 某个具体字段被观察到的时间 | 判断这个字段在 cutoff 时是否存在 |

### 9.2 关键规则

1. **`captured_at` 不等于所有字段的 `observed_at`。** 赛后抓取的 raw payload 可能包含赛前字段和赛后字段混合在一起。`captured_at` 只告诉你"什么时候拿到了这份数据"，不能代替字段级的 `observed_at`。

2. **如果 `payload.captured_at > match_end_time`（即比赛结束后才抓的），则该 payload 不能用来证明其中任何字段赛前可用。** 即使 league、season 这种显而易见的赛前字段，如果 payload 是赛后抓的，你没法从这份 payload 本身证明"league 字段在赛前也在"。

3. **`captured_at <= prediction_cutoff_time` 时，可以初步判断该 payload 整体在 cutoff 前存在。** 但这里有一个坑：payload 内的字段可能在 cutoff 后更新过（比如 kickoff_time 因为比赛延期而更新了）。

4. **对有些字段，即使 `captured_at` 早也不行。** lineup 接近开赛才公布 → 需要 lineup_timestamp。odds 波动 → 需要 odds_timestamp。injury/table/form → 需要 snapshot 时间。

5. **对 xG / shots / score / events / player stats，即使 `captured_at` 早在 cutoff 前，也按 DATA-L1B 绝对禁止进入赛前模型。** 因为它们是另一场比赛的数据（如果 payload 来自已完赛的比赛），或者它们根本是本场比赛进行中/结束后的数据。

### 9.3 audit 流程建议（未来实现）

```text
1. 选定一个 prediction_cutoff_time。
2. 对每个 feature：
   a. 追到它的来源 raw payload。
   b. 检查 raw payload.captured_at <= cutoff？
   c. 如果 payload 可以赛前拿到，进一步检查 feature 的 observed_at <= cutoff？
   d. 根据 DATA-L1B 字段合同，确认该字段的分类。
   e. 如果 safe_prematch_candidate + observed_at <= cutoff → 可用。
   f. 如果 unsafe_postmatch / unknown_timing / debug_or_raw_only → 禁止。
   g. 如果 metadata_only 但不作为特征 → 允许用于管线。
3. 记录 audit trail：哪个 feature 来自哪个 payload，为什么可用/为什么禁用。
```

本 PR 不实现上述流程。只定义策略。

---

## 10. raw payload 与 DATA-L1B 字段合同的关系

这是一个常见的误解：**"raw payload 里有这个字段，所以这个字段可以用"。** 错。

两者的关系如下：

| 问题 | 回答 |
| --- | --- |
| raw payload 里有 xG，能用吗？ | **不能。** xG 是 `unsafe_postmatch`，不管 raw payload 什么时候抓的。 |
| raw payload 里有 lineup，能用吗？ | **不一定。** lineup 是 `unknown_timing`，除非有 lineup_timestamp ≤ cutoff 证据。 |
| raw payload 里有 odds，能用吗？ | **不一定。** odds 是 `unknown_timing`，必须拆成 opening/current/closing 且每条有 captured_at。 |
| raw payload 里有 league/season，能用吗？ | **通常可以。** league/season 是 `safe_prematch_candidate`，但建议确认 payload 是赛前抓的。 |

**规则**：DATA-L1B 决定字段能不能用。DATA-L1C 规定的保留 metadata（captured_at、payload_hash 等）提供判断证据。两者合作才有完整的 audit trail。

---

## 11. 推荐存储逻辑（只建议，不实现）

以下只写建议路径和结构。本 PR 不创建目录、不移动数据、不改 DB schema。

### 11.1 文件系统存储建议

```text
raw/fotmob/{season}/{league}/{match_id}/{captured_at_compact}_{payload_hash_short}.json
raw/fotmob/{season}/{league}/{match_id}/{captured_at_compact}_{payload_hash_short}.meta.json
```

示例：

```text
raw/fotmob/2026/ligue1/123456/20260703_143000Z_a1b2c3d4e5f6.json
raw/fotmob/2026/ligue1/123456/20260703_143000Z_a1b2c3d4e5f6.meta.json
```

### 11.2 DB 行建议（如果使用 raw_match_data 表）

已有 `raw_match_data` 表（按 DATA-L1A §3 线索），建议每个 raw payload 至少对应一行记录，包含 §5 中的必需字段。

### 11.3 建议的配套文件

| 文件 | 内容 | 是否建议现在创建 |
| --- | --- | --- |
| content file | raw payload 主体 | 由未来的 collector/acquisition PR 创建 |
| metadata sidecar | `.meta.json` 包含 §5 字段 | 由未来的 retention adapter PR 创建 |
| parser output snapshot | parser 解析该 payload 的完整输出 | useful for replay regression |
| schema summary | 该 payload 的字段清单（JSON Schema 或字段列表） | useful for schema drift 检测 |

### 11.4 本 PR 不做什么

- 不创建 `raw/fotmob/` 目录。
- 不移动现有数据。
- 不写 raw 文件。
- 不改 DB schema。
- 不改 `raw_match_data` 表结构。

---

## 12. 隐私、体积、成本和清理风险

### 12.1 体积问题

raw payload 可能很大。一次完整的 pageProps 可能有 100KB~500KB。一个赛季几十场比赛的 raw payload 堆起来就是几百 MB。

### 12.2 敏感信息风险

raw payload 可能包含：
- 动态 token / session cookie 痕迹
- debug 信息（FotMob 开发者的调试字段）
- 地理位置暗示
- 用户跟踪信息

这些需要未来单独隐私审计。本策略不处理隐私风险，但标记为已知风险。

### 12.3 成本权衡

保留所有 raw payload 的存储成本 vs. 丢掉后无法复盘的损失：
- critical 等级的 raw payload 无论成本多少都必须保留。
- standard 等级在存储紧张时可以降级或抽样。
- 不要为了省空间直接删除 raw payload——清理必须等未来 CLEANUP 或 DATA 后续任务单独授权。

### 12.4 清理规则

清理 raw payload 前必须回答：
- 这份 payload 是否被用于 training/backtest？
- 是否还有对应的 parser 版本可以 replay？
- 是否在 cutoff audit 中被引用过？
- 是否有同一 match_id 的其他 payload（不依赖这份也可以复盘）？

回答不清楚就先不删。

---

## 13. 后续代码实现建议（不实现）

以下只建议，不写代码。本 PR 是一份策略文档。

1. **DATA-L1D（未来）**：让 FotMobRawParser 输出每个字段的 timing label 和 field provenance（这个字段来自 raw payload 的哪一层，采集时间是什么）。

2. **raw payload retention adapter（未来）**：实现一个适配器，在采集 raw payload 时自动生成 §5 的 metadata sidecar。自动计算 payload_hash、content_length、标记 contains_postmatch_fields 等。

3. **replay runner（未来）**：创建一个工具，可以用历史 raw payload 和指定的 parser_version 重新跑 parser，输出对比结果。

4. **schema drift checker（未来）**：创建一个工具，比较不同时间采集的同 route raw payload 的字段清单，报告差异。

5. **payload hash / metadata sidecar 完整性校验（未来）**：定期检查 raw payload 文件和 metadata 是否一致（hash 匹配、文件存在）。

6. **training lineage 记录（未来）**：在 training pipeline 中记录每个 feature 的来源 payload + hash + parser_version，形成完整的 audit trail。

7. **CI fixture replay check（未来）**：在 CI 中增加一个轻量级步骤，用少数 critical fixture payload 验证 parser 没有 break。

**重要**：以上所有建议需要单独授权、单独 PR。**本 PR 不实现这些代码。**

---

## 14. 与 DATA-L1A / DATA-L1B 的关系

```text
DATA-L1A (审计报告)     = 查出仓库里有危险食材
DATA-L1B (字段合同)     = 写食材安全清单
DATA-L1C (本策略)       = 规定进货小票、原包装、监控录像怎么保存

三者不互相替代，但互相引用。
```

具体关系：

| 维度 | DATA-L1A | DATA-L1B | DATA-L1C（本合同） |
| --- | --- | --- | --- |
| 类型 | 审计报告 | 字段合同 | raw payload 保留与回放策略 |
| 产物 | `docs/_reports/data_l1a_fotmob_prematch_boundary_audit.md` | `docs/data/fotmob_prematch_field_contract.md` | `docs/data/fotmob_raw_payload_retention_replay_policy.md` |
| 是否替代对方 | 不替代 | 不替代 | 不替代 |
| 被哪些后续工作引用 | 此后的所有 FotMob 改造 | parser/feature/training/backtest | parser replay / schema drift / retention adapter / cutoff audit |
| 修改条件 | 发现新风险或风险过时 | 发现字段分类错误或新字段加入 | 发现 raw payload 生命周期需要调整 |

---

## 15. 本次明确不做事项

本 PR（DATA-L1C）只创建这一份 raw payload 保留与回放策略文档。以下全部不做：

- 没有改代码
- 没有改测试
- 没有改 CI
- 没有改 Docker
- 没有改 DB / migration
- 没有改 scraper / collector
- 没有运行 FotMob 采集
- 没有访问真实 FotMob 网络接口
- 没有运行浏览器采集
- 没有生成 raw payload 样本
- 没有写入数据目录
- 没有创建文件存储目录
- 没有改 parser
- 没有改 feature
- 没有改 training
- 没有跑 backtest
- 没有碰 staging server
- 没有启动 DATA-L1D
- 没有启动 DATA-L2
- 没有启动 CLEANUP-L1A
- 没有启动 L3I
- 没有启动 L4
- 没有做 legacy 删除 / 移动 / 重命名

---

## 16. 下一步建议

Do not start automatically.

Recommended next task only after user confirmation:

- **DATA-L1D: FotMob Parser Field Provenance and Timing Labels Design**
  - 目标：基于 DATA-L1B 字段合同和 DATA-L1C 保留策略，设计 parser 输出的 timing label 和 field provenance 方案。
  - 仍然建议 docs-only，不改代码。

如果用户认为仓库里旧文件需要整理，也可以选择：

- **CLEANUP-L1A: Repository File Usage Audit**
  - 目标：审计仓库中旧脚本/测试/文档的使用状态，标记可清理项。

但以上建议只供参考，不应自动启动。DATA-L1C 合并后具体做什么，由用户决定。
