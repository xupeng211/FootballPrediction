# Mainline Reset Decision Audit After TECHDEBT-L3H

## 快照

- 当前 origin/main SHA：`3d2f8754a96002614102c4a0b0ab05959d2a8d06`
- 最新 main CI 状态：`28652360532`，success
- 本次分支：`docs/mainline-reset-decision-audit`
- 本次改动范围：仅 `docs/_reports/mainline_reset_decision_audit.md`

## 1. 背景

从 2026-07-02 到 2026-07-03，我们连续合并了 TECHDEBT-L3A 到 L3H 共 8 个 PR：

| PR | 内容 |
|---|---|
| #1685 L3A | legacy entrypoint 盘点和隔离计划 |
| #1686 L3B | active entrypoint whitelist 确认 |
| #1687 L3C | legacy label 和 guard wording 提案 |
| #1688 L3D | review ownership 和 CODEOWNERS wording 提案 |
| #1689 L3E | unknown entrypoint owner 决策 |
| #1690 L3F | enforcement 七层设计提案 |
| #1691 L3G | warning-only changed-file classifier 实现 |
| #1692 L3H | classifier visibility 提升和 Step Summary |

这些 PR 搭好了一个 warning-only 的治理基础设施。classifier 会在每个 PR 上自动扫描 changed files，输出标签和风险提示，但**不阻断 CI**，**不决定谁能合并**，**不实现 CODEOWNERS**。

现在继续加治理强度是错误的节奏。正确的做法是：

- 进入观察期
- 让 classifier 在真实 PR 上跑一段时间
- 把精力转回项目主线——足球预测、数据、模型、回测

**本报告不是 L3I。本报告不是 L4。本报告不实现 hard gate。本报告不实现 CODEOWNERS。本报告不改代码。本报告不修改 Gatekeeper / AI Workflow Gate。**

## 2. 当前基线

以下信息为本次实际确认到：

- origin/main HEAD：`3d2f8754a96002614102c4a0b0ab05959d2a8d06`
- 最新 main Production Gate CI run：`28652360532`，conclusion = `success`
  - Gatekeeper：success
  - AI Workflow Gate (P0)：success
  - AST / UTF-8 校验：success
  - L3 warning-only classifier：skipped（预期行为——classifier 只在 pull_request 事件运行）
  - Docker Build Validation：success
- 合并到 main 的 L3 系列 PR：8 个（#1685-#1692）
- L3 之前最后一个功能 PR：#1684（fix rate limiter compatibility），另有 #1682/#1681（test time-independence fix）、#1679（mypy changed-line gate）
- 当前分支：`docs/mainline-reset-decision-audit`
- 本次只改一个文件：`docs/_reports/mainline_reset_decision_audit.md`

未确认到的信息会在下文注明，不编造。

## 3. L3 完成后的正确策略

### 现在已经在手上的东西

- L3G/L3H 的 warning-only changed-file classifier 已经装好
- 它会在 PR 上输出：
  - stdout：分类表格 + attention notes
  - Step Summary（如果 GITHUB_STEP_SUMMARY 可用）：结构化的 markdown summary
- classifier 永远 exit 0，**不管多危险的文件都不会阻断 CI**
- classifier 不会改 Gatekeeper、AI Workflow Gate、CODEOWNERS、workflow、branch protection

### 正确的下一步

**让它在真实 PR 中跑，先观察，不要急着升级。**

观察点：

1. 误报：有没有正常文档/测试被标成 restricted-legacy 或 high-risk？
2. 漏报：有没有明显敏感路径没有被标注？
3. 噪音：输出是不是太长了？Step Summary 在 GitHub Actions UI 里是否清楚？
4. 可操作性：reviewer 看到这些 warning 后，知道该做什么吗？

### 升级路径（需要单独授权）

这些都**不是现在要做的事**：

- **soft gate**：把某些 label（比如 restricted-legacy）从 warning 升级为需要在 PR body 里明确 ack 的 soft check
- **hard gate**：让 restricted-legacy 或 unclassified 直接阻断 CI
- **CODEOWNERS 实现**：真的在 CODEOWNERS 文件里按 L3D 提案分配 reviewer
- **Gatekeeper 改造**：在 Gatekeeper 里加 L3 分类逻辑
- **AI Workflow Gate 改造**：在 AI Workflow Gate 里把 classifier 输出变成 hard check
- **branch protection 改造**：加 required status check

**现在不建议启动的事项**：

- hard gate（任何形式）
- CODEOWNERS 实现
- Gatekeeper 改造
- AI Workflow Gate 改造
- branch protection 改造
- L4（API boundary reconciliation）
- legacy entrypoint 删除 / 移动 / 重命名
- scraper 重构
- training 重构
- DB / migration 改造
- Docker 改造
- 大规模清理旧代码

## 4. 主线候选方向对比

以下分析基于 FootballPrediction 项目的真实目标：足球比赛预测、赔率对比、价值投注发现、回测。

| 方向 | 收益 | 主要风险 | 可能触碰的敏感路径 | 是否需要额外授权 | 是否适合作为 L3 后第一个真实主线任务 | 建议理由 |
|---|---|---|---|---|---|---|
| **1. 数据源稳定性（FotMob）** | 确认赛前可用字段、时间边界、数据稳定性；避免用赛后数据偷跑；为后续模型/回测打基础 | 可能触发 scraper 重构冲动；FotMob 采集仍被 blocked | `scripts/ops/fotmob_*.py`（restricted-legacy）、`src/parsers/` | 只读审计不需要；执行 scraper 需要 | **适合**（先 docs-only audit） | 没有稳定数据，模型和回测都是空中楼阁。先从只读审计开始，比直接改 scraper 安全 |
| **2. 赔率数据可行性** | 确认 OddsPortal 数据的完整性、时效性、覆盖范围；赔率是价值投注的核心输入 | OddsPortal 有反爬机制；`oddsportal_decryptor.py` 涉及敏感逻辑；采集脚本在 restricted-legacy | `scripts/ops/odds_*.js`（restricted-legacy + scraper-training-sensitive）、`src/core/oddsportal_decryptor.py` | 只读审计不需要；采集需要 | 适合（docs-only audit 先行） | 赔率对价值投注至关重要，但数据源稳定性应优先确认。可以和 FotMob audit 并行或紧随其后 |
| **3. 回测框架和评估口径** | 建立可靠的回测体系，确认评估指标（准确率、ROI、Brier Score 等）；验证策略有效性 | `src/ml/backtest_engine.py` 已在 active-runtime 路径中；改回测逻辑可能影响运行时 | `src/ml/backtest_engine.py`（active-runtime） | 修改 active-runtime 需要授权 | 可以但需谨慎 | 回测框架已有基础（backtest_engine.py、backtest_v1.py），可以从 docs-only 评估口径设计开始 |
| **4. 特征工程** | 提升模型预测能力；48→12061 维度的 V25.1 引擎已有基础 | 特征工程目录在 `src/feature_engine/`（active-runtime）；改了可能影响预测 API | `src/feature_engine/`、`src/ml/feature_adapter.py`（active-runtime） | 修改 active-runtime 需要授权 | 可以但需谨慎 | 特征工程需要稳定的数据源来验证效果，建议先完成数据源审计 |
| **5. 模型训练** | 更新模型参数，提升准确率；探索新模型架构 | `scripts/ops/train_model.py` 是 restricted-legacy；训练需要 GPU 或大量计算资源；可能触发 DB 写入 | `scripts/ops/train_model.py`（restricted-legacy + scraper-training-sensitive）、`src/ml/` | **需要明确授权** | **不适合**作为第一个任务 | 训练需要稳定数据 + 回测评估体系，前面两个没有确认前，训练没有意义 |
| **6. 测试基线** | 确保核心预测逻辑有测试覆盖；保护已有功能不被破坏 | 测试文件在 `tests/**`（test-only）；写测试相对低风险 | `tests/**`（test-only） | 通常不需要 | 适合作为辅助任务 | 可以在任何阶段补充，不阻塞主线 |
| **7. 部署 / staging 检查** | 确认 staging 环境可用，CI/CD 完整；减少部署风险 | Docker 相关文件是 docker-sensitive；staging 可能需要 .env / secrets | `Dockerfile`、`docker-compose*`（docker-sensitive） | 修改 Docker 配置需要授权 | 可以但要谨慎 | staging 环境检查不紧迫；classifier CI 已经能保证基本门禁 |

## 5. 推荐选择

**L3 后第一个真实主线方向，建议优先选择"数据源稳定性 / FotMob 赛前数据边界审计"。**

理由：

1. FootballPrediction 的核心是预测足球比赛。没有稳定、可靠的数据源，模型训练、回测、赔率对比都是空中楼阁。
2. 当前项目最接近可用的数据源是 FotMob。已经确认 4 条 raw payload 成功写入并审计通过（见 `docs/data/FOTMOB_RETAINED_RAW_STAGE_STATUS.md`），说明解析链路是通的。
3. 但**赛前可用字段、时间边界、字段稳定性**还没有系统文档。这会导致：
   - 模型可能用到了赛后才知道的数据（数据泄露）
   - 回测结果不可靠
   - 新 feature 不知道该从哪个字段取
4. 这个方向可以先从 **docs-only / read-only audit** 开始，不碰 scraper，不改代码，风险最低。
5. FotMob 相关入口（`scripts/ops/fotmob_*.py`）都在 restricted-legacy 里，classifier 会在任何触碰时发出 warning，这提供了安全网。
6. L3 classifier 会在这个方向的工作中持续发挥作用——每次 PR 都能看到哪些路径被触碰、是否有 restricted-legacy 文件被改。

**不推荐把模型训练放在第一位的原因**：没有稳定的数据源和可靠的回测框架，训练出来的模型没法评估真实效果。这不是说训练不重要，而是说时机不对。

## 6. 第一个真实主线任务建议

### 建议任务名称

**DATA-L1A: FotMob Pre-match Data Boundary & Stability Audit**

### 任务目标

只读审计当前 FotMob 相关资源，回答以下问题：

1. FotMob 赛前数据包含哪些字段？（team form、player stats、head-to-head、league table、odds 等）
2. 每个字段在比赛开始前多久可以获取？（小时级别）
3. 哪些字段可能包含赛后信息？（需要标记为"不可用于赛前预测"）
4. 当前项目已经用了哪些字段？在哪里用的？
5. 采集稳定性如何？（是否经常 503、是否需要代理轮换、反爬强度）

### 建议第一步

仍然是 docs-only 或 read-only audit，不改 scraper：

- 阅读现有 FotMob 文档（`docs/data/FOTMOB_CURRENT_STATE.md`、`docs/data/FOTMOB_RETAINED_RAW_STAGE_STATUS.md`）
- 阅读现有 FotMob 相关脚本的源码（不执行）
- 整理字段清单和数据流图
- 标记潜在的数据泄露风险点

### 如果未来要执行 DATA-L1A 的代码修改部分

**需要用户单独授权**，可能涉及以下路径：

- `scripts/ops/fotmob_*.py`（restricted-legacy）
- `src/parsers/`（active-runtime）
- `src/data/`（active-runtime）
- `docs/data/`（documentation）
- `tests/` 相关测试文件

**本次 PR 不修改上述任何文件。**

## 7. L3 Warning-only Classifier Observation

本次 PR 只改 `docs/_reports/mainline_reset_decision_audit.md`，属于 docs-only。这是一个很好的机会来观察 L3 warning-only changed-file classifier 在真实 PR 中的表现。

### 本次 PR 预期分类

classifier 应该将本次改动分类为：

- `documentation`（因为 paths 匹配 `docs/**` 和 `*.md`）
- 可能被 L3 docs pattern 命中为 `l3-docs`（如果 classifier 把文件名里的 "mainline" 误匹配）

### 观察点

如果 CI 输出了 Step Summary，人工检查：

1. 是否误报了 restricted-legacy、high-risk、gate-sensitive 等敏感标签？
2. 输出中 "Attention needed" 是否合理？（本次 docs-only 应该不需要 attention）
3. Step Summary 在 GitHub Actions UI 里是否清楚易读？
4. 本次改动的文件是否应该被更精确地分类？（比如 "mainline_reset" 审计报告可能不应该被标为 l3-docs）

### 校准价值

如果本次 PR 的 classifier 输出一切正常（没有误报敏感标签），可以作为 L3 后第一条真实 PR 的校准样本，证明 classifier 对低风险 docs-only 改动不会产生噪音。

如果出现误报（比如把主报告误标为 l3-docs），则应该在后续 PR 中微调 classification rules。

## 8. 明确不做事项

本次没有做、也不应该做的事情：

- 没有改代码（`src/**`）
- 没有改测试（`tests/**`）
- 没有改 CI（`.github/**`）
- 没有改 workflow
- 没有改 Docker（`Dockerfile`、`docker-compose*`）
- 没有改 DB / migration
- 没有改 scraper
- 没有改 training
- 没有改 pipeline
- 没有改 Gatekeeper
- 没有改 AI Workflow Gate
- 没有碰 staging server
- 没有连接 192.168.10.4
- 没有实现 L3I
- 没有启动 L4
- 没有实现 hard gate
- 没有实现 CODEOWNERS
- 没有删除、移动、重命名任何文件
- 没有运行 Docker / DB / psql / migration
- 没有读 .env 或 secrets
- 没有运行 scraper / training / pipeline

## 9. 下一步建议

1. 先确认本次 PR 的 CI 绿色，观察 L3 warning-only classifier 的输出。
2. 如果 classifier 输出正常，可以把本次 PR 作为 L3 后第一条真实 PR 的校准样本。
3. 下一步由用户决定是否授权 **DATA-L1A: FotMob Pre-match Data Boundary & Stability Audit**。
4. 未授权前，不启动 DATA-L1A，不改任何 FotMob 相关代码。
5. 继续让 L3 classifier 在真实 PR 上积累观察数据，至少跑 5-10 个真实 PR 后再考虑升级为 soft gate。

---

*本报告为 docs-only 决策审计，不代表项目路线图变更。所有实施决策需用户单独授权。*
