# Project Vision — FootballPrediction North Star

- lifecycle: permanent
- intended readers: Owner + all AI Agents + developers
- role: North Star / target-system blueprint
- authority scope: project target state / end-state vision

## 一句话愿景

FootballPrediction 最终要成为一个持续运行的足球价值投注决策支持系统：在严格的
decision-time / as-of 边界内估计 `P(HOME)`、`P(DRAW)`、`P(AWAY)`，将概率与真实市场价格
比较，识别可能的 mispricing、edge 和 expected value，并在不确定性、市场质量、风险暴露
与 bankroll 约束下输出 `BET` 或 `NO BET`。

这不是盈利保证。正确目标是建立一个可验证、可审计、能识别正期望机会、知道什么时候不
下注，并持续判断自身 edge 是否仍然存在的系统。

## 文档边界

本文件只回答“FootballPrediction 最终要变成什么”。它不替代：

- `AGENTS.md`：唯一 operational workflow authority，回答怎么安全行动。
- README 的 `Canonical Business Entrypoints`：业务正式入口 authority。
- `docs/AGENT_WORKFLOW.md`：详细工作方法。
- `docs/PROJECT_MAP.md`：东西在哪里。
- `docs/CAPABILITY_INDEX.md`：已经有什么能力和资产。
- `docs/ACTIVE_MILESTONE.md`：当前正在推进哪一个缺口。
- `docs/PROJECT_STATUS.md`：完整 current-state、证据和 blockers。

PROJECT_VISION 不是 TODO list、sprint plan、issue tracker、active milestone、具体 PR
roadmap，也不负责仓库的操作规则。它不授予网络、DB、训练、预测、backtest、
模型激活或生产执行权限。

## Mission 与长期成功证据

### Mission

构建一个持续运行的足球价值投注决策支持系统，利用严格 decision-time 数据、可信概率模型
和真实市场价格，识别可能的正期望机会，输出 `BET` / `NO BET` 与风险控制建议，并通过
forward evidence、CLV、ROI、calibration 和 drawdown 持续验证系统是否仍值得信任。

### `BET` 输出的最小概念

当 Decision Policy 允许 `BET` 时，决策记录至少应能表达：

- selection
- market odds
- model probability
- fair odds
- minimum acceptable odds
- estimated edge
- estimated EV
- confidence / risk grade
- recommended stake

`NO BET` 是合法且重要的系统输出，不是异常，也不是为了提高推荐数量而需要绕过的状态。

赛后系统应持续记录和评价 Log Loss、Brier、Calibration、CLV、ROI、Yield、Max Drawdown、
edge buckets、league segmentation、odds-range segmentation 和 model drift，并具备
`KEEP`、`REDUCE RISK`、`RETRAIN`、`STOP BETTING` 等模型健康决策能力。

长期成功不是一次漂亮回测、一次高准确率、某个模型击败 baseline 或短期盈利。至少需要
持续的新鲜 forward decisions、不可事后修改的 prediction/odds ledger、稳定 calibration、
positive market-relative evidence、positive CLV evidence、positive long-run net performance、
可接受的 drawdown、跨时间 robustness 和 risk discipline。

## Non-goals

FootballPrediction 不是：

- 每天强制推荐比赛的系统。
- 单纯追求最高命中率的系统。
- 只预测比赛赢家的系统。
- 比分预测软件。
- 用已知 test set 反复调出漂亮结果的系统。
- 用历史 ROI 过拟合策略的系统。
- 保证盈利的系统。

核心边界必须保持清楚：

```text
Prediction quality ≠ Betting value
Betting value ≠ Proven profitability
High win probability ≠ Good bet
```

## 目标架构

这是目标系统的稳定分层，不代表这些层已经在当前仓库中全部实现：

1. **Fixture Universe**：确定待决策比赛全集、身份、联赛和目标 kickoff。
2. **Decision-Time Data Layer**：在每个 decision time 冻结赛前信息和 as-of 边界，拒绝未来信息泄漏。
3. **Probability Engine**：输出 `P(HOME)`、`P(DRAW)`、`P(AWAY)` 及可审计的模型版本和概率来源。
4. **Market / Odds Engine**：保留真实市场价格、时间线、来源质量和适用市场语义。
5. **Fair-Probability / De-vig Layer**：从合法市场价格计算可解释的 fair market probability 基准。
6. **Value Engine**：比较模型概率与市场概率/价格，计算 fair odds、minimum odds、edge 和 EV。
7. **Decision Policy**：综合阈值、校准、不确定性、市场质量与约束，输出 `BET` 或 `NO BET`。
8. **Risk / Staking Engine**：结合 bankroll、暴露、相关性、限额和 risk grade 计算或拒绝 stake。
9. **Decision Ledger**：不可事后修改地记录决策时的输入、概率、赔率、版本、理由和输出。
10. **Forward Testing & Monitoring**：只用未来未见数据评价预测、价值和决策结果。
11. **Model Health / Stop-Betting Controls**：监测 drift、calibration、CLV、drawdown 和 edge 衰减，支持 KEEP / REDUCE RISK / RETRAIN / STOP BETTING。
12. **User Decision Interface**：呈现可审计的 BET / NO BET、风险边界、证据和当前系统健康状态。

## 当前研究证据：不可混合解读

### A. Canonical prematch model path

当前已有 canonical candidate：

- candidate：`canonical-prematch-vnext-a74c9a9ad63dd48a86f15d41`
- model family：`xgboost_multiclass_1x2`
- feature contract：`canonical_prematch/vnext-v1`
- accepted-for-training features：9
- population：888 accounted、545 eligible、343 ineligible
- split：436 training、109 reserved evaluation
- holdout：109 `CONSUMED_FOR_OFFLINE_EVALUATION`
- formal offline quality：`MODEL_OFFLINE_QUALITY_STATUS=PROMISING`
- formal metrics：log loss 约 `0.97834`、Brier 约 `0.58456`、accuracy 约 `55.96%`

这些是当前 offline evidence，不是 quality、profitability 或 production proof：

```text
MODEL_QUALITY_PROVEN=NO
PROFITABILITY_PROVEN=NO
PRODUCTION_READY=NO
MODEL_ACTIVATED=NO
```

### B. VALUE_MVP-1 market research path

`VALUE_MVP-1` 是另一套历史研究路径：13-feature baseline 对 provider-defined closing market，
结果为 `MARKET_BETTER_THAN_MODEL`。

它不是上述 9-feature canonical candidate 的评价，也不是 canonical value engine。两项研究
共同说明：football-only predictive signal 目前有正向 evidence，但 beating market pricing
明显更难；最终系统必须严格验证 market edge。

## Target vs Current Gap

下表把目标 maturity 与当前仓库事实分开。`Current State` 只描述已审计事实，不把愿景当成现状。

| Capability | Target State | Current State | Gap |
|---|---|---|---|
| Decision-time football data | 每次决策都有严格 as-of、不可泄漏的赛前快照 | canonical prematch frame 已完成，但 kickoff-reference rows 的 `model_decision_time` 仍未充分证明 | strict decision-time evidence 与 future validation |
| Prematch feature set | 稳定、可追溯、只消费决策时刻可用特征 | canonical 9-feature frame 已有，GD-A01/A02/A03 已完成 | 需要在 market-relative forward evidence 中继续验证 |
| Probability model | 输出 H/D/A 概率、版本、校准和不确定性 | canonical XGBoost candidate 已有，offline quality 为 `PROMISING` | quality proven、fresh evidence、production boundary |
| Uncertainty | 概率不确定性和 risk grade 进入 policy | 当前有离线概率指标，没有完整 decision-time uncertainty contract | uncertainty / calibration policy |
| Market odds timeline | 真实 provider price 的 decision-time/as-of 时间线 | historical odds 研究资产与 Stage C canonical decision-time/as-of spine 已存在；maturity 为 `REPRODUCIBLE_PILOT` | continuous durable capture 尚未就绪；Stage D 未启动，须先完成 Owner 门禁 |
| De-vig | 可解释的 fair-market probability 基准 | canonical de-vig layer `NOT_ESTABLISHED` | 建立并验证市场概率语义 |
| Value engine | 计算 fair odds、minimum odds、edge、EV | canonical value engine `NOT_ESTABLISHED`；VALUE_MVP-1 为独立研究 | canonical market-relative engine |
| `NO BET` policy | 缺少 edge、质量或风险条件时稳定输出 `NO BET` | canonical policy `NOT_ESTABLISHED` | policy contract 与 forward evidence |
| Canonical backtest | 防泄漏、可重复、市场相对的 backtest | `NOT_ESTABLISHED` | 不能用一次历史 ROI 代替证明 |
| Forward test | 新鲜未来 holdout 和不可变 decision ledger | 109 holdout 已 consumed；fresh independent future holdout 未建立 | forward holdout、ledger、监控 |
| CLV | 每个决策持续记录并评价 CLV | `NOT_ESTABLISHED` | odds timeline + ledger + evaluator |
| Bankroll / staking | 风险暴露、stake、drawdown 受约束 | `NOT_ESTABLISHED` | risk/staking contract |
| Drift / stop-betting control | 支持 KEEP / REDUCE RISK / RETRAIN / STOP BETTING | `NOT_ESTABLISHED` | health monitors and fail-safe policy |
| Production decision surface | 只在 readiness/activation 条件满足后输出受控决策 | 当前模型 API 为只读 observability，artifact API row pending；production activation `NO` | production decision interface and activation governance |

## 当前主要缺口

依据 current-state 文档，当前只记录、不在本 vision 任务中启动的缺口包括：

- continuous durable decision-time odds evidence（已有 Stage C pilot）and market/de-vig semantics
- canonical value engine and `NO BET` policy
- canonical backtest / market-relative evaluation engine
- fresh independent forward holdout and prediction/odds ledger
- CLV tracking
- bankroll / staking controls
- drift and stop-betting controls
- production decision interface and model activation boundary

这些缺口属于 target-state gap，不构成执行授权。本任务不启动 odds capture、de-vig、value
engine、staking、CLV、backtest、forward testing 或 UI 实现。

## Vision 的维护规则

PROJECT_VISION 应保持低频、稳定、面向 end-state。只有 North Star、target architecture，
或某一项 vision capability 的 maturity 语义发生真实变化时才更新它。普通 bugfix、单个
current-state 状态变化和 active milestone 推进不应无意义修改本文件；它们应分别回写
`CAPABILITY_INDEX.md`、`ACTIVE_MILESTONE.md` 或 `PROJECT_STATUS.md`。

建议的高层 maturity vocabulary 是 `NOT_ESTABLISHED`、`FOUNDATION`、`CANONICAL`、
`VALIDATED`、`PRODUCTION`。本文件使用这些词表达 target/current gap，不未经审计重标记
现有全部能力；current capability authority 仍是 `docs/CAPABILITY_INDEX.md`。
