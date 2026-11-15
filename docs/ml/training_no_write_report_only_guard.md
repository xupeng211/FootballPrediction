# Training No-write Report-only Guard

- lifecycle: permanent
- scope: training entrypoint safety / GOLD-AUDIT-2AE
- status: active

## Contract

Training entrypoints must not treat readiness audits as training execution.

`--report-only --no-write` is the only mode intended for filtered feature matrix
inspection. It:

- reads eligible L3 rows with SELECT-only queries;
- applies `l3_prematch_safe_contract.v0.json`;
- builds matrix statistics in memory;
- prints the report to stdout;
- does not fit, train, calibrate, or save models;
- does not write datasets, reports, metadata, scalers, or model artifacts.

## Artifact Guard

Any path that saves model artifacts must require both confirmations:

```text
ALLOW_TRAINING_WRITE=yes
FINAL_TRAINING_WRITE_CONFIRMATION=yes
```

Without both values, artifact save paths fail closed.

This guard does not authorize training. It only prevents accidental writes when
future training execution is separately authorized.

## PR-6 Candidate Boundary

The canonical PR-6 producer is a separate permanent runtime path at
`src/ml/training/canonical_training_producer.py`. It accepts only an explicit
offline pre-match feature frame, validates the exact API contract, performs a
chronological/OOS split, and writes only to an explicitly supplied
non-production candidate path. Its atomic candidate write and whole-file SHA256
are candidate-production mechanics, not activation authority.

The default `npm run train` command does not query the business database or
fetch live data, has no production/activation flag, and fails without an
explicit input and candidate output. The tracked manifest remains unchanged;
`status=active`, a real production checksum, production artifact generation,
and model loading remain separately authorized operations. Existing legacy
training write guards and their `ALLOW_TRAINING_WRITE` confirmations remain
applicable to those legacy paths; they do not make those paths canonical.

## 兼容 L3 矩阵报告的数值分类

`build_filtered_feature_matrix_report` 仅当列至少有一个非缺失值，且每个非缺失值
均经既有 `_as_number` 成功转换为有限数值时，才把该列计入 numeric。
`None`、空字符串及不存在的键仍按原缺失规则统计；布尔、坏文本和非有限值
不视为缺失，但使所在列计入 non-numeric。合法数值字符串仍可转换，不增加清洗或填补。
低方差示例仍只接受 numeric 列，并保留原有唯一值数阈值及示例数量上限。
例如两行仅含同值 `home_market_value_source="totalStarterMarketValue"` 和
`home_injury_count=0/1`，数值列与非数值列各为 1，仅 injury count 进入数值低方差示例。

此修复只纠正转换成功判断，保留 allowlist、列身份、缺失率、常量与全零规则、
标签、readiness、全部 `SAFE_FOR_*` 和 no-write 边界；不提供新的训练授权。
直接回归位于 `tests/unit/ml/test_filtered_matrix_report_only.py`，通过公开 helper
验证上述边界和输入不变，不连接数据库或执行训练。

### Documentation Impact（本地候选）

- `EXISTING_CAPABILITIES_REVIEWED=YES`：复用既有矩阵报告、转换和 L3 过滤能力。
- `CURRENT_MILESTONE_REVIEWED=YES`：本修复不推进 M3、Stage D 或离线研究结论。
- `CAPABILITY_INDEX_UPDATE_REQUIRED=NO`：修正既有统计判断，没有新增能力或成熟度。
- `ACTIVE_MILESTONE_UPDATE_REQUIRED=NO`：未推进里程碑或解决主要 blocker。
- `PROJECT_STATUS_UPDATE_REQUIRED=NO`：未改变项目就绪状态、生产状态或主要 blocker。
- `README_ENTRYPOINT_UPDATE_REQUIRED=NO`：没有新增或改变 canonical 业务入口。
- `PROJECT_MAP_UPDATE_REQUIRED=NO`：沿用原模块及直接测试，模块导航没有变化。
- `PROJECT_VISION_UPDATE_REQUIRED=NO`：未改变愿景分层、数据/模型合同或授权合同。

本次 `Workflow class = STRICT`，仅交本地候选；正式隔离 `verify-strict` /
`verify-pr`、exact-head 独审及远端 CI 由 Controller 后续执行。
`formal_review=NOT_AUTHORIZED`，`remote_write=FORBIDDEN`；本说明不声明正式验收通过。
