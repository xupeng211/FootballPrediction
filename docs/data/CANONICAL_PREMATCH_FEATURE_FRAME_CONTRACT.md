# Canonical Prematch Training Feature Frame Contract

<!-- lifecycle: permanent -->

本文档定义第一版离线 training feature frame 的业务边界。它是 GD-A03
`TARGET_KICKOFF_EXCLUSIVE` prior-state foundation 的一个版本化投影，不改变
V1 默认模型 contract，不激活 V-next，也不把历史 kickoff 顺序冒充为真实
model decision time。

## Authority and entrypoint

特征名称、顺序、历史/runtime readiness 与训练决策仍只有一个 authority：

```text
config/model_feature_contracts.json
  contracts[canonical_prematch/vnext-v1]
```

frame artifact schema 是 `canonical-prematch-training-feature-frame/v1`，这是
输出/receipt schema，不是第二套 feature registry。入口为：

```bash
npm run feature:frame -- build \
  --gd-a03-artifact <absolute repository-external artifact> \
  --gd-a03-receipt <absolute repository-external receipt> \
  --output <absolute repository-external frame> \
  --receipt <absolute repository-external frame-receipt> \
  --code-revision <full 40-hex Git SHA>

npm run feature:frame -- validate \
  --artifact <absolute repository-external frame> \
  --receipt <absolute repository-external frame-receipt> \
  --gd-a03-artifact <absolute repository-external GD-A03 artifact> \
  --gd-a03-receipt <absolute repository-external GD-A03 receipt>
```

Build 和 validate 都重新验证 GD-A03 artifact/receipt，并由同一 registry、GD-A03
source rows、engine 与 runtime adapter 重新投影/逐字节比对；只做 selected features
的 file-first projection。它不抓取数据、不连接数据库、不写 raw/L3、不训练、不预测、
不 backtest、不激活模型。

## First training decision matrix

V-next 的 17 个定义按当前证据被严格分成三类：

| Feature | Final decision | Reason |
|---|---|---|
| `rolling_xg_home` | `ACCEPTED_FOR_TRAINING` | GD-A03 exact previous-five historical xG lineage；typed-context runtime formula 与 deterministic fixture numeric parity 已证明 |
| `rolling_xg_away` | `ACCEPTED_FOR_TRAINING` | 同上，team identity 按每场 home/away side 解析 |
| `home_points` | `ACCEPTED_FOR_TRAINING` | prior result `3/1/0` 累加；runtime typed path 对没有可验证 prior history 的情况返回 unavailable，不隐含填 0 |
| `away_points` | `ACCEPTED_FOR_TRAINING` | 同上 |
| `points_diff` | `ACCEPTED_FOR_TRAINING` | `home_points - away_points` |
| `home_recent_form_points` | `ACCEPTED_FOR_TRAINING` | exact previous-five result points；不足五场为 unavailable |
| `home_fatigue_index` | `ACCEPTED_FOR_TRAINING` | prior scheduled matches in `[cutoff-7d, cutoff)` / 7, capped at 1 |
| `away_fatigue_index` | `ACCEPTED_FOR_TRAINING` | 同上 |
| `fatigue_diff` | `ACCEPTED_FOR_TRAINING` | `home_fatigue_index - away_fatigue_index` |
| `rolling_possession_home` | `EXCLUDED_FROM_TRAINING` | 当前没有 accepted numeric historical + runtime source；禁止比例、均值和 proxy |
| `rolling_possession_away` | `EXCLUDED_FROM_TRAINING` | 同上 |
| `rolling_shots_on_target_home` | `BLOCKED_PENDING_EVIDENCE` | frozen source 没有独立可靠 team identity/own-goal closure；不得用 goals 或 total shots |
| `rolling_shots_on_target_away` | `BLOCKED_PENDING_EVIDENCE` | 同上 |
| `home_table_position` | `BLOCKED_PENDING_EVIDENCE` | historical semantic contract 已冻结，但当前 runtime numeric materialization/parity 未证明 |
| `away_table_position` | `BLOCKED_PENDING_EVIDENCE` | 同上 |
| `table_position_diff` | `BLOCKED_PENDING_EVIDENCE` | 依赖两侧 standings runtime parity |
| `raw_elo_gap` | `BLOCKED_PENDING_EVIDENCE` | initialization、season transition、K、home treatment 与 update order 未形成 Owner-approved complete contract |

因此第一版 frame 的 feature order 是 registry 原顺序中过滤后的 9 个名字，绝不
为了维度保留 proxy、默认值或 0 fill。其余 8 个仍保留在 decision matrix，便于
未来有独立证据时按 registry 演化，而不创建 parallel feature authority。

## Point-in-time policy

每行至少绑定：

```text
canonical_match_id
target_match_identity
target_kickoff_utc
feature_contract_id/version
feature_as_of_utc
feature_as_of_status
model_decision_time_utc
model_decision_time_status
每个 feature 的 value/availability/source IDs/source identities/provenance
postmatch-only target_label
```

当前 frame 的唯一可证明关系是：

```text
FEATURE_CUTOFF_POLICY=TARGET_KICKOFF_EXCLUSIVE
source_match_kickoff < target_match_kickoff
FEATURE_AS_OF_STATUS=KICKOFF_REFERENCE_ONLY
MODEL_DECISION_TIME_UTC=null
MODEL_DECISION_TIME_STATUS=NOT_PROVEN_KICKOFF_REFERENCE_ONLY
```

这不声称 T-24H、T-1H、source observed time、capture time 或实际 bookmaker
decision-time availability。未来明确的 decision-time context 必须令
`FEATURE_AS_OF_UTC == MODEL_DECISION_TIME_UTC < TARGET_KICKOFF_UTC`，并为 source
facts 提供不晚于该时间的 availability proof；否则 fail closed。

## Eligibility and population conservation

`ROW_ACCOUNTED` 与 `ROW_TRAINING_ELIGIBLE` 分开。feature history 不足的行仍保留，
但列为 `INELIGIBLE`，并记录具体 unavailable feature；不做 mean/median/zero/
forward/league-average/synthetic imputation。

真实 frozen validation 使用现有 repository-external GD-A03 A artifact：

```text
GD-A03 artifact business hash = 2a21672302563c3ecf30e0a3f1962adefad1d5f719c2dd3897ac136f442dde53
TARGET_POPULATION=888
ROWS_ACCOUNTED=888
TRAINING_ELIGIBLE=545
TRAINING_INELIGIBLE=343
UNACCOUNTED=0
DUPLICATE=0
EXTRA=0
```

这 888 行没有因为 early-history gap 被静默丢弃。每个 frame receipt 都重新绑定
target/accounted ID-set hash，并要求 population conservation。

## Leakage, labels, provenance, and determinism

- 所有 selected source identities 必须严格早于 target kickoff；source IDs 不得包含 target ID。
- target label 只作为 `TRAINING_LABEL_POSTMATCH` 独立字段；修改 target score/result/xG/shots/shotmap/player stats 不得改变 prematch feature lines。
- 每条投影 line 带 `source_line_sha256`，并保留 GD-A03 source IDs、identities、cutoff proof、derivation、provenance digest。
- frame business hash 覆盖 contract decision、rows、values、availability、provenance、population 和 readiness；receipt 另绑定 artifact bytes、source bindings 与 code revision。
- 对相同冻结输入和相同 code revision，BUILD_A/BUILD_B 要求 artifact/receipt 字节、business hash、row set、values、availability 与 provenance 完全一致。

## Runtime parity boundary

`V26_6_PreMatchAdapter.adapt_canonical_typed_context` 是现有 adapter 上隔离的 canonical
typed-context 入口，委托 `src/ml/inference/canonical_prematch_feature_engine.py` 的纯
semantic engine；它不是 provider/capture adapter，也没有接管默认 production runtime。
typed context 必须携带 competition/season、`canonical-schedule-history/v1` 的完整
history closure、包含 target 与 target-team prior schedule rows 的 canonical schedule
以及由规范化 schedule 内容重算的 source schedule digest；digest 不是只检查格式的
self-reported token。prior facts 的 identity/kickoff/team fields 还必须逐项匹配该
schedule；缺失或不完整的 history closure 仍 fail closed。若 closure 明确证明某队
没有任何 prior fixture，points/fatigue 使用 GD-A03 冻结的 cold-start `0`；这不是
imputation 或默认值。它复用 registry accepted order，使用与 GD-A03 相同的 xG、points/form、fatigue 公式；在 deterministic
fixture 上逐 feature 验证 GD-A03 historical producer 与该 adapter runtime path 的数值
和 unavailable reason 一致。

因此：

```text
GD_A03_TO_CANONICAL_ADAPTER_TYPED_CONTEXT_PARITY=PROVEN
REAL_DECISION_TIME_PROVIDER_AVAILABILITY=NOT_PROVEN
V1_DEFAULT_RUNTIME_SWITCH=NO
MODEL_SCHEMA_SWITCH=NO
```

这足以闭合第一版 kickoff-exclusive offline frame，但不等于真实线上 provider
已接通，也不允许在本任务中启动训练或预测。

## 离线特征质量诊断

现有 CLI 增加来源绑定的报告 consumer，不改变 build/validate 输出或上述合同：

```bash
npm run feature:frame -- diagnose \
  --artifact <absolute repository-external frame> \
  --receipt <absolute repository-external frame-receipt> \
  --gd-a03-artifact <absolute repository-external GD-A03 artifact> \
  --gd-a03-receipt <absolute repository-external GD-A03 receipt> \
  --expected-targets 888 \
  --output <absolute repository-external new quality.json> \
  --markdown-output <absolute repository-external new quality.zh.md>
```

`diagnose` 先执行与 validate 相同的 GD-A03 验证、registry/engine/adapter 绑定、
frame 逐字节重投影与 leakage/eligibility 校验，以及 clean worktree / receipt
`code_revision == HEAD` 检查。仅检查自洽 hash 的 frame 不足以生成报告。
文件边界复用原 CLI：输入是仓库外普通文件；输出父目录预先存在、仓库外、无 symlink，
两个输出必须不同且不存在，使用 `wx` 拒绝覆盖。两次写入不是事务；若第二次写入发生
I/O 失败，第一次输出可能保留，命令失败不代表双报告已交付，须使用新的输出名重跑。
纯模块 `buildQualityDiagnostics` 接收已验证的 GD-A03 输入与 frame 字节，内部继续复用
`validateFrameAgainstInputs`；GD-A03 文件校验和真实 HEAD 探针由 CLI 承担。

### 报告语义

JSON schema 为 `canonical-prematch-feature-quality-diagnostics/v1`，绑定完整代码 SHA、
frame/receipt bytes SHA、frame business hash 与原 source bindings；业务 hash 覆盖其余所有
报告字段。中文 Markdown 是同一 JSON 对象的展示，均不包含当前时间、输出路径或随机数。
同一输入、同一代码版本，JSON 与 Markdown 字节确定。

- `features`：仅 registry 接受的 9 项，分母为所有 accounted 比赛；`AVAILABLE` 的有限数值
  为有效值，包括合法 `0` 和负差值。缺失只按权威 `UNAVAILABLE` 统计，不推断或填补。
  给出有效/缺失数、缺失率（空总体为 null）、缺失比赛、逐特征不可用原因；其他 8 项只在
  `non_selected_features` 复制 registry 已有决策和理由，不计算其数值质量。
- `numeric_quality`：观测数、不同值数、零值数、min/max、均值、总体标准差，以及线性插值
  Q1/中位数/Q3。无观测统计值为 null；少于 2 个观测不宣称常量或全零。
  至少 2 个有效观测且不同值数为 1 才标为常量；全零还要求所有有效观测等于 0，
  缺失观测不在数值证据中。至少 4 个有效观测时，以严格小于 Q1−1.5×IQR 或大于
  Q3+1.5×IQR 标出离群位置；小样本不做 IQR 标记。这些线索不自动判错或改 eligibility。
- `eligibility`：保留 canonical population accounting、eligible/ineligible 比赛 ID、
  canonical eligibility 原因命中与完整组合。标签不可用独立记录，不误算为特征缺失。
- `unavailability`：原因命中单位是不同 `(比赛, 特征, 原因)`；同一 line 重复 code 去重，
  同一原因命中多个特征仍是多次，但 `affected_match_count` 对比赛去重。标签以独立类型
  单列，防止与同名 feature reason 混淆。每类原因保留比赛/特征定位。
  `reason_combinations` 是每场全部去重原因集合的精确分区，不枚举子集；每场只进入一个
  非空组合，组合计场数可加，单原因影响量不能直接相加。
- `investigation`：不可用原因、常量、全零和 IQR 离群按各项受影响的不同比赛数降序排列，
  同数按稳定 `issue_id` 排序；每项列 eligible/ineligible 影响量、完整比赛/特征/原因或
  观测值证据。跨项合计影响量取比赛并集；`match_diagnostics` 反向定位所有问题。

**受影响比赛数不等于修复后可新增训练样本数。** 同场其他问题、标签或后续独立证据仍可
阻断 eligibility；无恢复样本数估计。常量/全零可以是合法冷启动或历史分布，仅提示调查。
报告显式保留 `KICKOFF_REFERENCE_ONLY`、`NOT_PROVEN_KICKOFF_REFERENCE_ONLY` 和真实决策时点
可用性 `NOT_PROVEN`，不授予训练、预测、回测、采集、DB/raw 写入或生产切换权限。

### 恢复的 GD-A03 v4 冻结源复现

本 mission 使用已恢复源，不重新采集或检索；下面两个文件预期 bytes SHA-256 分别为：

```text
8d8f4b4f3861f49e2b7d0c2247de55c85fc8de3ac7d6c5ced81e01e4bedf768e  /home/xupeng/fsc-v1-validation.final.0mEajJ/A/gd-a03-artifact.json
6213b4a6da188d6e9bd0aec94882fca567299aac67e706c53194f7d2c1650825  /home/xupeng/fsc-v1-validation.final.0mEajJ/A/gd-a03-receipt.json
```

Controller 在最终 checkpoint、clean worktree 和可访问源的可信环境中执行；任何最终 HEAD
变化后必须重新 build/validate/diagnose，禁止修改旧 receipt 或绕过 `CODE_REVISION_MISMATCH`。
在仓库根目录执行以下命令，`quality_run_dir` 必须是全新目录；在 dev 容器执行时使用同一
可见路径挂载源、候选仓库与输出，不需要 DB 或网络：

```bash
quality_head=$(git rev-parse HEAD)
quality_run_dir="/home/xupeng/autonomous-delivery/football-canonical-feature-quality-20261023T175922Z/business-artifacts/${quality_head}"
mkdir -m 700 "$quality_run_dir"
npm run feature:frame -- build \
  --gd-a03-artifact /home/xupeng/fsc-v1-validation.final.0mEajJ/A/gd-a03-artifact.json \
  --gd-a03-receipt /home/xupeng/fsc-v1-validation.final.0mEajJ/A/gd-a03-receipt.json \
  --expected-targets 888 --code-revision "$quality_head" \
  --output "$quality_run_dir/frame.json" --receipt "$quality_run_dir/frame-receipt.json"
npm run feature:frame -- validate \
  --artifact "$quality_run_dir/frame.json" --receipt "$quality_run_dir/frame-receipt.json" \
  --gd-a03-artifact /home/xupeng/fsc-v1-validation.final.0mEajJ/A/gd-a03-artifact.json \
  --gd-a03-receipt /home/xupeng/fsc-v1-validation.final.0mEajJ/A/gd-a03-receipt.json \
  --expected-targets 888
npm run feature:frame -- diagnose \
  --artifact "$quality_run_dir/frame.json" --receipt "$quality_run_dir/frame-receipt.json" \
  --gd-a03-artifact /home/xupeng/fsc-v1-validation.final.0mEajJ/A/gd-a03-artifact.json \
  --gd-a03-receipt /home/xupeng/fsc-v1-validation.final.0mEajJ/A/gd-a03-receipt.json \
  --expected-targets 888 --output "$quality_run_dir/quality.json" \
  --markdown-output "$quality_run_dir/quality.zh.md"
make verify-strict
make verify-pr
```

诊断的直接测试覆盖数值/计数/组合/排序、JSON/Markdown 确定性、来源/标签/eligibility
协调重 hash 篡改，以及实际 GD-A03 assembler → frame build/validate → 双报告文件链与
路径/版本失败边界；测试中的 Git 身份替身不作为真实 clean HEAD 或冻结源验收证据。

## Readiness boundary

本 frame 可以报告：

```text
FEATURE_FRAME_READINESS=READY
REAL_TRAINING_READINESS=READY_FOR_OFFLINE_CANDIDATE_INPUT
TRAINING_EXECUTION_AUTHORIZED=NO
STRICT_DECISION_TIME_VALUE_EVALUATION=NOT_READY
GOLDEN_DATASET_COMPLETE=NO
```

这里的 `REAL_TRAINING_READINESS` 仅表示已经有可信的 offline candidate input；它
不是训练已执行、不是 metrics 已生成，也不是 model artifact 已激活。后续
`CANONICAL_TRAINING_CANDIDATE_PRODUCTION` 需要 Owner 单独授权。
