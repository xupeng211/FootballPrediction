# CANONICAL_OFFLINE_MODEL_EVALUATION

本文件记录当前业务节点 `CANONICAL_OFFLINE_MODEL_EVALUATION` 的代码合同。
它只评价已经冻结的 `canonical-prematch-vnext-a74c9a9ad63dd48a86f15d41`，不训练新模型，也不把离线概率结果解释成下注或生产结论。

## 冻结协议

机器可读协议位于
`config/canonical_offline_model_evaluation_protocol.json`，实现位于
`src/ml/evaluation/canonical_offline_model_evaluation.py`。正式执行顺序是：

1. 校验 candidate、metadata、canonical frame、receipt 的完整 SHA-256 和 provenance。
2. 只读取 frame 的特征、时间和 row identity；`target_label.outcome` 保持 opaque。
3. 按 candidate producer 的 `chronological_reserved_evaluation_holdout/v1` 重建 545 eligible rows 的 436/109 split，并绑定两个 row-ID hash。
4. 将 protocol freeze SHA 记录到 evaluation source。
5. 运行 candidate inference，完成 probability sanity check。
6. 仅由 `OutcomeAccessGate.open_reserved_outcomes()` 第一次读取 109 个 reserved outcomes，然后生成 evidence。

协议固定的身份是：

- feature contract：`canonical_prematch/vnext-v1` / 9 features；class order：`0/1/2 = AWAY/DRAW/HOME`；probability columns：`P_AWAY/P_DRAW/P_HOME`；
- primary metric：`multiclass_log_loss`；secondary metrics：multiclass Brier、accuracy、per-class diagnostics、confusion matrix、固定 5-bin calibration；
- baseline 只使用 436 training rows：class-prior constant probability 与 majority-class constant prediction；不读取 reserved outcomes 计算 baseline；
- uncertainty 是固定 seed `20260823` 的 5000-resample percentile bootstrap，只是 uncertainty estimate；
- `ROI`、`yield`、`PnL`、`CLV`、stake、Kelly、edge、bet count、backtest 和 activation 都属于禁止范围。

## 入口和输出

入口是内部离线 research surface：

```bash
npm run evaluate:offline -- \
  --candidate /absolute/path/candidate-a.joblib \
  --metadata /absolute/path/candidate-a.joblib.metadata.json \
  --frame /absolute/path/canonical-prematch-feature-frame.json \
  --receipt /absolute/path/canonical-prematch-feature-frame.receipt.json \
  --protocol /app/config/canonical_offline_model_evaluation_protocol.json \
  --output-dir /absolute/path/new-evaluation-output \
  --protocol-freeze-sha <full-40-char-sha> \
  --outcome-opened-at <RFC3339-timestamp> \
  --json
```

输出目录必须是新的 repository-external 目录。输出是
`canonical-offline-model-evaluation.json` 与对应 receipt；不会写
`config/model_artifacts.json`、production manifest、candidate 文件或 frame 文件。
evaluation artifact 的 holdout 状态为
`CONSUMED_FOR_OFFLINE_EVALUATION`；以后不得再称这 109 行为 untouched/blind/unopened。

## 解释边界

`PROMISING`、`MIXED`、`WEAK`、`CLEARLY_UNDERPERFORMING` 由协议中的固定规则产生。
109 行的 calibration 只作诊断；占用样本不足的 bin 标记为 `INSUFFICIENT_SAMPLE`。
本节点永远输出 `model_quality_proven=false`、`profitability_proven=false`、
`production_ready=false`、`model_selected=false`。

`src/ml/value_mvp/` 不能作为本节点的 producer 或 protocol：它是另一套
13-feature、按 season 的 market benchmark，含 closing-market 语义；本节点必须保持
candidate metadata、9-feature frame 和 109-row reserved holdout 的独立绑定。
