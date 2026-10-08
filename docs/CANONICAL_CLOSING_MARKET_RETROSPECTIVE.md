# 冻结 XGBoost 与历史收盘市场：回顾性概率诊断

- lifecycle: permanent（正式研究结果与可复现用法；不是 workflow authority）
- readers: Owner、概率模型研究者
- mission: `CANONICAL_CANDIDATE_VS_CLOSING_MARKET_RETROSPECTIVE_DIAGNOSTIC`
- analysis type: **RETROSPECTIVE_DIAGNOSTIC**

冻结模型在这批比赛上比真实历史收盘市场差。109 场全部配对、全部使用相同赛果；没有补抓、
筛选有利比赛、重新训练或推理。这个结果支持继续研究模型的市场相对概率质量，
不支持投入真实下注或宣称生产盈利。

## 结果（CONFIRMED：已有真实文件的离线重算）

| 指标（109 个配对） | 冻结模型 | 去水收盘市场 | 模型减市场 | 配对差值 95% bootstrap 区间 |
|---|---:|---:|---:|---:|
| Multiclass Log Loss | 0.978340037241 | 0.899730233518 | +0.078609803723 | [+0.015476340689, +0.140815637412] |
| Multiclass Brier（未缩放） | 0.584557279738 | 0.527801063082 | +0.056756216656 | [+0.012991949077, +0.099896344981] |
| Argmax accuracy（辅助） | 55.9633%（61/109） | 59.6330%（65/109） | -3.6697 百分点 | 不作独立优势检验 |

Log Loss、Brier 越低越好；模型减市场为正，表示市场评分更好。主结论依据 Log Loss，
分类为 `MARKET_BETTER_THAN_MODEL`。不是靠单一均值宣布稳定优势：区间在所述假设下也在正侧。
Brier 是 `mean(sum_k((p_k-one_hot(y)_k)^2))`，不除以 3，也不除以 2，范围 [0,2]。
Log Loss 使用原 canonical 的 natural log 与 `1e-15` 下限；不修补或重新归一化模型概率。
保留原模型输出的 float32 累加容差 `1e-6`。冻结预测序列化到 12 位带来约 `1e-13` 的评分差异，
与原评价的 `0.9783400372406917` 一致到业务精度，不是重推理。

## 全量核算与身份

- 原冻结全集：888 accounted；545 eligible / 343 ineligible；436 training / 109 reserved evaluation。
- 本次 population：2024-02-18 至 2024-05-19，Premier League 2023/24，109 accounted / 109 paired / 0 excluded。
- 109 个 canonical ID 按原 chronological reserved split 重建；row-ID SHA-256：
  `ea42247460b9993b4963bf4c26a372d58498865526e1401312055125a466bbde`。
- canonical ID、GD-A01 exact match link、FotMob ID、freeze snapshot、raw payload SHA、frame target-label ID
  逐场一致；home/away team order 一致；所有 kickoff 以带 timezone 的同一 instant 比较（Z 与 +00:00 等价），
  不容忍分钟偏移。没有发现 identity/kickoff/outcome 冲突。
- 冻结预测 actual label 与 frame 的 postmatch outcome、score 一致；市场对应 CSV 的 FTR/FTHG/FTAG
  也与同场最终比分一致。
- 模型顺序 **AWAY/DRAW/HOME = 0/1/2**；读取命名字段 `P_AWAY/P_DRAW/P_HOME`；市场函数原顺序
  HOME/DRAW/AWAY 显式转换到 A/D/H。源 CSV 的 selection→column mapping 直接复用原 adapter，
  每一项赔率回查原列值，避免 H/A/D 错位。

逐场 JSON 保留 canonical/FotMob ID、kickoff、teams、最终比分、outcome provenance digest、
模型/市场 A/D/H 概率、逐场 Log Loss/Brier/delta、每家公司报价三元组、去水概率、overround、margin、
原 source URL、CSV row locator、raw SHA、idempotency key、重复证据与最终状态。
每个预定 ID 均有 `PAIRED` 或带明确 reason 的 `EXCLUDED`；没有 silently dropped 行。

## 市场合同与原始数据问题

来源为 `football-data.co.uk` 的 source-native C 系列，全场 **1X2**、line=null，
合同 `football-data-provider-contract/v1`（GD-A01 已采用 M3-R2 v3 receipt）。
这是 provider-defined closing，**精确 capture/observation/closing tick 均 UNPROVEN**。
没有把 first_collection/plain 系列当作 closing，也没有推断缺失时间。

沿用已批准 `config/value_mvp_1_evaluation_protocol.json` 的市场规则（不修改其任何字节）：
每个完整的同 source/row/bookmaker/series 三元组有限且 decimal odds>1；
`q_k=1/odds_k`、overround=`sum(q)`、margin=`overround-1`、`p_k=q_k/overround`；
各家分别去水后做等权算术平均，再归一化最终向量。至少 2 家，排除 Max/Avg 聚合列。
不挑表现最好的公司；不会跨公司、跨 CSV row 或跨 quote series 拼三元组。

真实资产有两点需要明确：

1. **38 场在 raw_odds_2324 与 real_odds_raw 中重复出现。**两处的合法 closing 报价经源列校验后
   数值一致，且已有 `buildSemanticDuplicateKey` 给出的语义身份一致。
   只折叠完整三元组等价的重复证据；保留两份来源、同一公司只计一次权重。
   不把这 38 场排除，不让 duplicate source 增加公司权重。不同数值/语义报价会明确排除，
   不以文件顺序覆盖或猜测。初版 71 场结果是开发中发现此问题的中间产物，**不是正式结论**。
2. **原 source commit/blob 在当前 Git object store 已不可读。**本次使用已保存 CSV 镜像，
   三份文件分别匹配 GD-A01 收据的 SHA-256、byte size 和 `git hash-object --stdin`（无 -w）的
   原 blob ID。由此可以确认字节身份；原 commit→path→blob 的历史链接只由冻结收据记录，
   本次不能从当前 Git 重新独立证明（UNKNOWN）。不补抓、不修复或重写原历史。

## 数据与模型 provenance

candidate=`canonical-prematch-vnext-a74c9a9ad63dd48a86f15d41`；family=`xgboost_multiclass_1x2`；
feature contract=`canonical_prematch/vnext-v1`，9 accepted features。

| 资产 | SHA-256（实际字节） |
|---|---|
| candidate-a.joblib | a841169d51d90ddfad89dfa48defbe8875d10e1c0ed6d205a06b15a307f7160c |
| candidate metadata | 1b3343eb4f050f0b32372b66a1ba84c68656ddad745fc83083680f5a1fdf97df |
| consumed-holdout hardened replay predictions | 574a20ebde1e055e61e16789e23f21d9d7023f8cef4c379a4a14d0db15a11155 |
| evaluation receipt | 730f9c3620c3821b7dd96a6882750508f411d87aeb297df5f11450eb3e9401d5 |
| canonical feature frame | 206c65788d8f815f79e3281401fbca8e540a2ebd5f24af4421077ac428bc0524 |
| frame receipt | 7dd88606ffc74f4ed1a015898b0950af98f41af65405df81aa5e59f3ce14b159 |
| GD-A03 | 8d8f4b4f3861f49e2b7d0c2247de55c85fc8de3ac7d6c5ced81e01e4bedf768e |
| GD-A03 receipt | 6213b4a6da188d6e9bd0aec94882fca567299aac67e706c53194f7d2c1650825 |
| GD-A02 | 99ec2cbec3526661c31ebe9ec4a34903e4e4ec417a7451395305c53e2fdaadf6 |
| GD-A02 receipt | 5ed440ce2e85a758c3f9adaea01890920e69bad229b720703957f64b4fad1516 |
| GD-A01 | 59f64d3ef127cbec26eab6bb465882730b9d8f9ab7c3b35bd96f59af444ab950 |
| GD-A01 receipt | 2650b717c90c2cc7f37cad89a2dd562ed580db5d45973fd4d3d39da4afbc6582 |
| raw_odds_2223.csv | e51361323bcdcdcec2faf8f58e7bcfc4f5b193ed6017b284c71538ed70d98ea2 |
| raw_odds_2324.csv | 0b669038e94bf305603d841f02006c7d35ebd41c8722c76e479f2393079b995f |
| real_odds_raw.csv | 045cb84f6a75dc947e5aa5c4170c844237c1dcd489ae3264a795f39a20114361 |

评价 receipt 由已有 builder 纯函数重算并全等比较；模型只读取字节/metadata，**不反序列化**。
frame 经 canonical loader 的纯合同路径验证并重建 split；GD-A01/A02/A03 artifact+receipt
均经原 JS validators，GD-A01→GD-A03→frame 的 source binding SHA 逐层匹配。
FotMob 原始 capture 未逐份重放；本次依据冻结 GD/frame provenance，不宣称重新采集或独立验证原网站。

## 不确定性与解释限制

10,000 次 paired percentile bootstrap，seed=`20261008`，95% 区间。每次重采样的是同场
模型减市场的差值，两个指标分别评分；不是独立抽两批比赛。只含一个 season，复用既有
season-stratified bootstrap 时是单层（2023/24），未混入 VALUE_MVP 的其它样本。

统计假设是这批比赛条件下的 iid 配对观测；同队重复、赛程/时间依赖可能令 iid 区间偏窄，
不包含模型选择、训练过程、赔率来源或其它赛季的不确定性。小于 30 对时 consumer 返回
`INSUFFICIENT_EVIDENCE` 且不给指标；30 只是描述性最低门槛，**不是 power 保证**。
109 场的 outcomes 已在 2026-08-23 被消费，本次没有新的 untouched holdout 或 fresh forward evidence。
市场时间更接近开赛，且 frame 的 decision-time readiness 未证明，比较回答的是历史概率诊断，
不是相同交易决策时点的可执行策略比较。不能宣称 tradable edge、ROI、长期盈利或 CLV。

VALUE_MVP-1 是 13-feature multinomial logistic baseline，按 season 的 511-row OOS；
其 model Log Loss=1.0691605748、market=0.9423141889、delta=+0.1268463858。
本次是 9-feature frozen XGBoost / 109-row consumed cohort，市场规则复用，但模型、训练与样本合同不同；
不能混合统计，也不能把两者均值直接解释成模型迭代收益。

## 实现、复用、验证和复现

新增最小 consumer 为 `src/ml/evaluation/canonical_closing_retrospective.py` 与同名 CLI，
入口 `npm run diagnose:closing -- ...`（dev 容器，所有来源和输出路径显式）。
新增的只有配对核验、逐场 accounting、市场与冻结预测 consumer、两项配对差值报告；
身份、赔率列映射/合同、去水/共识、metrics、bootstrap、frame/candidate 校验均复用。
已有 offline evaluator 会调用模型、重新打开 outcomes，VALUE_MVP producer 会训练另一模型；
两者不能直接用于本订单，所以新 consumer 只读取已保存预测。

可复现命令（下面 DATA_ROOT 是容器内只读证据根，OUT_ROOT 是新 external 输出目录；
在已准备依赖的 dev 容器中执行，PYTHONPATH 指向当前候选代码，容器应 `--network none`）：

```bash
python scripts/model_evaluation/canonical_closing_retrospective.py \
 --evaluation "$DATA_ROOT/canonical-offline-model-evaluation-20260823-replay-hardened-a/canonical-offline-model-evaluation.json" \
 --evaluation-receipt "$DATA_ROOT/canonical-offline-model-evaluation-20260823-replay-hardened-a/canonical-offline-model-evaluation.receipt.json" \
 --candidate "$DATA_ROOT/canonical-training-candidate-20260823-blind-final/candidate-a.joblib" \
 --metadata "$DATA_ROOT/canonical-training-candidate-20260823-blind-final/candidate-a.joblib.metadata.json" \
 --frame "$DATA_ROOT/canonical-training-input-20260823/canonical-prematch-feature-frame.json" \
 --frame-receipt "$DATA_ROOT/canonical-training-input-20260823/canonical-prematch-feature-frame.receipt.json" \
 --gd03 "$DATA_ROOT/fsc-v1-validation.final.0mEajJ/A/gd-a03-artifact.json" \
 --gd03-receipt "$DATA_ROOT/fsc-v1-validation.final.0mEajJ/A/gd-a03-receipt.json" \
 --gd02 "$DATA_ROOT/fsc-v1-validation.final.1BUs8u/gd-a02-artifact-A.json" \
 --gd02-receipt "$DATA_ROOT/fsc-v1-validation.final.1BUs8u/gd-a02-receipt-A.json" \
 --gd01 "$DATA_ROOT/FootballPrediction.gd-a02-validation/gd-a01-artifact.json" \
 --gd01-receipt "$DATA_ROOT/FootballPrediction.gd-a02-validation/gd-a01-receipt.json" \
 --csv-dir "$DATA_ROOT/FootballPrediction.artifacts/fotmob-five-match-real-e2e-trial-resumed-20260806T160028Z/evidence-sources" \
 --output "$OUT_ROOT/verified-a.json"
```

本机证据根为 `/home/xupeng`，使用已有 dev 依赖镜像 `footballprediction-runtime-deps:20260907`；
挂载候选仓库到 `/app`、证据到只读 `/evidence`、external 输出到 `/output`，`PYTHONPATH=/app`。
完整命令保存在 `/home/xupeng/canonical-closing-retrospective-20261008/reproduce.sh`；
逐场证据为同目录 `verified-a.json`、`verified-b.json`（不提交原始研究数据到仓库）。
两次全链路运行 exit=0，`cmp` exit=0、SHA-256 均为
`1c079607ee2dba5211503fc9b23536e98cc44601521645638fcf5f83d5602a62`。
不含业务字段 wall-clock，固定输入/代码/seed 输出字节一致。

聚焦测试覆盖合法配对、三分类顺序、ID/provider/kickoff、赛果、赔率列值/缺项/异常、
概率有限性/范围/归一化、source artifact/receipt hash、重复/额外连接、missing accounting、
等价报价不双计与冲突失败、确定性及不足证据。
negative tests 显式阻断 socket、sqlite、子进程、joblib model loading、XGBoost fit/predict 与 producer。
测试 fixture 只用于单元语义，研究结果全部来自上述真实文件。

实际验证：隔离 dev 依赖容器内 `make verify-targeted` exit=0（37 项新 Python tests、
313 项 affected JS tests、lint/Ruff/format）；新增 consumer 加既有 market/evaluation/bootstrap
聚焦回归 `pytest` exit=0（57 passed）；直接 mypy 与 strict profile changed-line mypy 均通过。
`make verify-strict` exit=2：静态通过，但 network-none 容器无 DB，现有 cold-start integrity guard 失败；
没有把 full validation 标为 PASS，也没有为此接入真实数据库。
扩展旧 evaluator/replay 回归为 81 passed / 7 failed（exit=1），失败均涉及当前 Git 无法读取
原 `82fbcd55db98b710089483b9c7d13f1ad6937e11` freeze commit。
用正式 base `c626e3109f2fc0c298551d0a9746e76540dfe410` 的只读 archive 重跑相同旧测试，
同样 24 passed / 同七项失败：这是已确认的 baseline 历史对象缺口，不由本 consumer 引入。
原 evaluator、tests、protocol 均不修改；诊断消费已冻结 artifact/receipt 的字节身份，
不谎称重新验证历史 freeze commit ancestry。

Workflow class=`STRICT`（现行 classifier 将此 src/ml source 归入 STRICT）；必需 reviewer 为 codex-cli。
本次 Owner 未授权付费独立审核，**没有执行正式 reviewer、API 资格实验或模型费用探测**。
独立审核保持 PENDING；候选 PR 为 Draft，不是 MERGE_READY 或 DONE。
正式 CI、最终 test exit 与候选完整 SHA 以候选 PR 的 Tests/check runs 为机器证据，
不在研究报告内伪造 PASS。预计仍需一次针对最终完整 HEAD 的 canonical Codex 独立审核；
是否产生费用与金额 UNKNOWN，必须有 Owner 单独预算授权。

## 下一步业务判断（INFERRED）

值得投入的是 **市场相对校准与信息增量研究设计**：先对已有逐场误差做可解释的 calibration /
feature-quality 诊断，锁定研究假设与新评价协议，再在单独授权的训练和未来未消费样本上检验。
不能围绕这 109 场调参并把改善称为泛化收益。现有 candidate 的 `PROMISING` 是对训练 prior 的评价，
本次市场基准更强，不改写原评价协议或 status 来掩盖差距。
不建议当前投入 value/staking/真实资金执行；Stage D、生产激活与旧 Harness 任务均没有启动。
