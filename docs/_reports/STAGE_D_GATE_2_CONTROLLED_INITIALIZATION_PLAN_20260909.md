# GATE_2：Stage D 受控初始化计划与证据

~~~text
MISSION=FINAL_BOUNDED_STAGE_D_AUTHORIZATION_AND_CONTROLLED_INITIALIZATION_PLAN
CLASSIFICATION=BLOCKED
GATE_1_ACCEPTANCE_CONFIRMED=YES
STAGE_D_AUTHORIZED=NO
PROVIDER_REQUEST_AUTHORIZED=NO
REAL_PROVIDER_REQUEST_EXECUTED=NO
GATE_3_REQUIRES_SEPARATE_OWNER_AND_CHIEF_ENGINEER_AUTHORIZATION=YES
~~~

本文件是 GATE_2 的 durable planning/evidence artifact，不是 GATE_3 授权，不是 provider request 命令，也不改变 production authority。BLOCKED 的原因是：仓库存在受控 live adapter 的内部实现，但没有可由未来执行者直接、安全调用的 production binder/CLI；该 adapter 需要模块私有的运行时授权 Symbol，而公开入口明确保持 offline-only。当前 authority transaction package 对普通 xupeng runtime user 也不可读，不能靠临时 sudo 或自造 node -e 入口绕过。这两项都必须在另一个明确授权的 remediation mission 中处理。

## 1. 起始状态与治理回流

~~~text
PROJECT_ROOT=/home/xupeng/FootballPrediction.clean-dev
CURRENT_BRANCH=ops/remote-backup-host-rediscovery-strict-gate-recovery
CURRENT_HEAD=21d8f030d5877d1059d1037d128980d756c35860
CURRENT_DIRTY_STATE=clean at task start
BASE_SHA=21d8f030d5877d1059d1037d128980d756c35860
ORIGIN_MAIN=21d8f030d5877d1059d1037d128980d756c35860
~~~

起始 branch 不是 main。任务开始时 git status --short --branch 没有文件变更；未切换 branch、未覆盖文件、未执行 reset/clean/force-push。此 artifact 是本任务唯一新增文件，位于 docs/_reports/，不在 production authority root。

~~~text
EXISTING_CAPABILITIES_REVIEWED=YES
CURRENT_MILESTONE_REVIEWED=YES
VISION_ALIGNMENT_REVIEWED=YES
~~~

已阅读并回流 docs/CAPABILITY_INDEX.md、docs/ACTIVE_MILESTONE.md、docs/PROJECT_STATUS.md、docs/PROJECT_VISION.md、docs/AGENT_WORKFLOW.md、README.md、Stage C pilot 和 Stage D contract。任务对应 PROJECT_VISION 的 canonical market-evidence / controlled operations 层；没有新增能力、入口、数据合同或 production authority。

## 2. 机器事实、accepted authority 与 backup 证据

### 2.1 Git 与 primary worktree

~~~text
EXPECTED_MAIN=21d8f030d5877d1059d1037d128980d756c35860
HEAD=21d8f030d5877d1059d1037d128980d756c35860
ORIGIN_MAIN=21d8f030d5877d1059d1037d128980d756c35860
HEAD == origin/main == EXPECTED_MAIN=YES
WORKTREE_CLEAN_AT_START=YES
UNRELATED_USER_WORK_PRESERVED=YES
~~~

### 2.2 canonical authority pre-state

以下值与任务给定的 accepted start state 完全一致；当前工作树 authority 通过只读 authority reader 在受控读取身份下复核，accepted restore root 也成功冷加载出相同 head/state/count。没有写入任何 authority 文件。

~~~text
HEAD=tx_0ba8d4ad78aef57d1bbadf6637198b08d9586c5debf3e343d07033ed98a6bb64
STATE_HASH=df5084b6d752d698bfde4646fb508f3a41396f160fbee3cca9ee1b3b412e5ddd
OBSERVATIONS=903
STORE_SHA256=ed014a6f151143aa30cefcebc47374059aa18c38a83560610571331a665199e4
ALLOCATION_AUTHORITY_SHA256=89e4276c8fe637318339821fe40d783d2f7fd8de65f6fc593b2035bd9445dad3
MATCHES_ACCEPTED_STATE=YES
~~~

### 2.3 accepted snapshot

~~~text
SNAPSHOT_ID=stage-d-preauth-20260909-20260909T012915Z-df5084b6d752
SNAPSHOT_ROOT=/home/xupeng/FootballPrediction.artifacts/independent-backup-execution-restore-proof-20260909/restored/stage-d-preauth-20260909-20260909T012915Z-df5084b6d752
SNAPSHOT_MANIFEST_SHA256=4397f0a432f22154492e80abfd8f79100b20fe7ce30dff5d67487231bdd1fa74
SNAPSHOT_COMPLETE_MARKER=present
SNAPSHOT_SHA256SUMS_SHA256=9545ffc9794dc78a59aab2f30dfba00c1917bb7e4cdf9a6c5c2aabad93cf90e8
VERIFIED_FOR_PLANNING=YES
~~~

已验证 BACKUP_CONTENT_MANIFEST.json、SNAPSHOT_COMPLETE.json 和 SHA256SUMS；sha256sum -c SHA256SUMS 对 snapshot 中的 10 个文件全部通过。manifest 绑定了 source authority 的 head/state/903、STORE、allocation、transaction-v1 packages、accounting epoch、entries、quota config；restore root 可被 authority reader 冷加载出同一 authority identity。

边界：当前 repo 与该 external artifact 均位于 /dev/nvme0n1p5。因此 VERIFIED_FOR_PLANNING=YES 只表示 accepted snapshot 的内容、完整性和 cold-load evidence 足够用于本计划；PHYSICALLY_INDEPENDENT_FAILURE_DOMAIN=NOT_PROVEN。未来 live 前必须有 Owner/基础设施批准的物理或管理独立 backup target；不得覆盖或使本 preauth snapshot 失效。

### 2.4 request accounting

~~~text
PRE_EPOCH_REQUEST_TOTAL_LOWER_BOUND=AT_LEAST_2_CONFIRMED
PRE_EPOCH_REQUEST_EXACT_TOTAL=UNKNOWN
POST_EPOCH_ID=sde_b10b6bd109a6c60498fbd9e8c9ec87894e79ca1091aedbdb229083199cd00406
POST_EPOCH_START=2026-09-08T05:56:56Z
POST_EPOCH_ENTRY_COUNT=0
POST_EPOCH_LAST_ENTRY_HASH=e0cc9d8b901e9acb2126eacbb37fa8b0a1dc5241362c19726ed2e9de25cfad9e
POST_EPOCH_REQUEST_COUNT=0
POST_EPOCH_CONSUMED_COUNT=0
POST_EPOCH_AMBIGUOUS_COUNT=0
~~~

post-epoch durable path 是 data/market_evidence/live/request-accounting/REQUEST_ACCOUNTING_EPOCH.json 与同目录 entries/000000000001.json 形式的 immutable hash-chain entries。当前 entries/ 为空；历史 UNKNOWN 没有被重写成 0 或 2。当前 epoch file 的只读 SHA256 为 f22044bacf26b5bacc65766c13e9be4d7a54a771c4182e2bcb0278bcf39aa459。

## 3. 已确认的现有 Stage D 路径

### 3.1 公开入口

真实存在且已核对的公开命令只有 offline contract：

~~~bash
node scripts/ops/stage_d_cycle.js --dry-run \
  --authority-root data/market_evidence/live/transactions \
  --ledger-root data/market_evidence/live/request-accounting \
  --quota-config config/stage_d_quota_budget.json \
  --operation-root <explicit-operation-root> \
  --run-lock-trust-root <approved-trust-root> \
  --run-id <single-use-run-id> \
  --now <utc-now>
~~~

该脚本在 scripts/ops/stage_d_cycle.js:3-6,40-43 明确声明 offline-only；它只加载 authority、读取 quota/ledger、创建并释放 offline planning lock，然后输出 no-provider/no-canonical-write plan。--initialize-request-accounting-epoch 是另一个会写入 ledger epoch 的受控初始化选项，但不属于本 GATE_2，也没有运行。脚本对其它模式直接报 live execution is disabled，不选择 provider client。

### 3.2 已存在但不可直接调用的 internal live path

src/infrastructure/market_evidence/stageDOperations.js:1973 的 executeStageDOneCycle 是唯一已发现的受控 live cycle engine；它绑定四个 reviewed factory：

~~~text
createStageDOddsApiTransport
createStageDEvidencePersistence
createStageDProspectiveCandidateBuilder
createStageDTransactionPublisher
~~~

其实际顺序已经在代码中固定为：

~~~text
trusted run lock
→ authority reopen and verified snapshot
→ exact request ledger read
→ quota budget gate
→ REQUEST_INTENT append
→ local credential preflight
→ TRANSMISSION_STARTED_OR_MAY_HAVE_STARTED append
→ exactly one transport.send(..., private call token)
→ provider header reconciliation
→ immutable RAW + receipt persistence
→ RESPONSE_RECEIVED or consumed failure terminal ledger entry
→ fresh authority reopen
→ duplicate RAW classification OR prospective candidate build
→ transaction-v1 atomic publisher
→ fresh authority check
→ lock release, or abandon/reconcile on ambiguity
~~~

这是真实代码路径，不是本任务执行路径。STAGE_D_RUNTIME_AUTHORIZATION 是 stageDOperations.js:71 的模块私有 Symbol；生产代码中没有获得它的 binder、CLI 或 caller。公开的 createStageDTestRuntimeAuthorization 仅在 NODE_ENV=test 下存在，不能用来授权生产 provider。仓库搜索只发现该函数在 Stage D 单测、导出和 README/contract 文档中，没有 production invocation。

### 3.3 退役路径

src/infrastructure/market_evidence/theOddsApiClient.js 的 MAX_REQUESTS=3 属于已退役 client；所有 live transport/capture 函数均调用 failRetiredLiveTransport()。它不是当前 Stage D 的 one-request boundary，也不得作为 GATE_3 入口。src/infrastructure/market_evidence/preflightRunner.js 有 networkless/preflight helper 和局部 MAX_PROVIDER_REQUESTS=1，但没有被 Stage D public entrypoint 或 executeStageDOneCycle 作为 live caller 使用，不能冒充 canonical live executor。

## 4. 未来一次受控请求的 preflight freeze

下列步骤只描述未来 GATE_3/GATE_4 在另行授权后必须完成的证据，不在本 GATE_2 执行：

1. 读取并比较完整 40 字符 Git HEAD、origin/main 和批准的 expected main；任何不等立即停止。
2. 读取 feature worktree 的 git status --short --branch；任何未获保护的用户修改、未预期 source change、dirty authority/runtime root 或可疑 lock 都停止。不得清理或覆盖。
3. 以现有 authority reader cold-load data/market_evidence/live/transactions，验证 HEAD、STATE_HASH、903 observations、STORE SHA256、allocation authority SHA256。读取必须在实际 future executor identity 下成功；不能用临时 root、sudo 或宽泛权限替代实际 runtime contract。
4. 验证 accepted preauth snapshot 仍存在、manifest/complete marker/checksums/restore cold-load 全部通过；新 post-live snapshot 必须写入另一个已批准的独立 target，不能覆盖 preauth snapshot。
5. 读取 exact accounting epoch、entries、last hash、lock/trust-fence 状态；任意 active/stale/ambiguous lock 或 ledger rollback 都停止。
6. 读取版本化 quota config，确认 provider/plan/region/market/cost/max/billing period/ceiling/reserve 仍与批准值一致；配置、ledger 或 provider knowledge 任一无法解释时 fail closed。
7. 取得独立 Owner 与 Chief Engineer 的 GATE_3 authorization，并在同一受信过程持有 runtime authorization。该授权对象不是环境变量字符串，不能复制、猜测或由测试 helper 替代。

## 5. quota gate 与 request accounting

### 5.1 quota gate

真实配置 config/stage_d_quota_budget.json 的合同为：

~~~text
PROVIDER=the-odds-api
PLAN=starter_free
MONTHLY_QUOTA=500
RESERVED_SAFETY_CREDITS=50
AUTOMATED_CEILING=450
REGION=uk
MARKET=h2h
EXPECTED_REQUEST_COST=1
MAX_REQUESTS_PER_STAGE_D_RUN=1
MAX_REQUESTS_PER_CYCLE=1
QUOTA_RESET_RULE=PROVIDER_RECONCILED__NO_UNVERIFIED_AUTOMATIC_RESET
AUTOMATIC_ZERO_ON_CALENDAR_CHANGE=false
~~~

真实 gate 是 readRequestLedger + assertRequestBudget，不是日历推断，也不是 API 余额探测。它必须满足：ledger epoch/schema/hash chain/root identity 有效；无 ambiguous consumed request；当前 run_id 未使用；monthly_used + 1 <= automated_spend_limit；run/cycle 最大值为 1；configured h2h × uk 与 expected cost 为 1。当前 local ledger 为 used 0，因此相对于 450 ceiling 的本地预算计算会得到 remaining_after=499；这个 499 不是 provider live balance。

provider live headers x-requests-used、x-requests-remaining、x-requests-last 在授权 response 之前明确保持 UNKNOWN_UNTIL_AUTHORIZED_RESPONSE。现有机制不发起 pre-request quota probe；增加 quota probe 会破坏最多一次 provider request 边界。故：

- static config、exact post-epoch local ledger 或 provider headers 任一无法读取/验证，立即 FAIL_CLOSED；
- 不以月初、日期切换或 billing period 名称推断 reset；
- response 后必须验证 used + remaining = 500、last = 1、provider used 不低于本地 consumed-after-request、remaining 不低于安全余量规则，并与上一次 provider reconciliation 单调一致；
- 任何 provider/local divergence、缺 header、非法整数、quota exhausted 或 unknown 都停止，不 retry，不第二请求。

### 5.2 request-accounting precommit

现有代码会在 transmission 前追加 REQUEST_INTENT，然后进行 credential-only transport.preflight()；credential 失败会追加 CANCELLED_BEFORE_TRANSMISSION。只有在此之后，才追加 TRANSMISSION_STARTED_OR_MAY_HAVE_STARTED，该状态将一次请求视为 consumed/可能 consumed，随后才允许调用 transport。transport 返回后必须追加 RESPONSE_RECEIVED、HTTP_FAILURE_AFTER_TRANSMISSION 或 consumed transport/persistence/parser failure terminal state。

这个 epoch 只对 post-epoch exact accounting 负责：

~~~text
PRE_EPOCH: AT_LEAST_2_CONFIRMED / EXACT_TOTAL=UNKNOWN
POST_EPOCH: 每个 request 的 append-only hash-chain exact
~~~

任何 intent append、terminal append、read-back、root identity 或 lock generation 结果不确定，都保留 lock 并进入人工 reconciliation；不得把未知结果当作未消费，也不得自动重试。

## 6. single-request boundary

已验证的结构性边界有三层：

1. config max_provider_requests_per_cycle=1 与 module constant MAX_PROVIDER_REQUESTS_PER_CYCLE=1；
2. executeStageDOneCycle 每次成功通过 gate 后只调用一次 transport.send(...)，provider transport 内部只执行一次 https.request，没有 retry loop；
3. transmission 前 request ledger、run lock、generation anchor 和 consumed terminal semantics 阻止同一 run 重复执行；失败后不自动 retry，新的 request 必须是另一个授权周期且重新过 quota gate。

上述边界在内部函数和单测中已证明，但“未来生产执行一定只能进入该函数一次”的 caller/binder 不存在。因此：

~~~text
INTERNAL_ONE_REQUEST_BOUNDARY=PROVEN
PRODUCTION_EXECUTABLE_ONE_REQUEST_BOUNDARY=NOT_PROVEN
SAFE_SINGLE_REQUEST_BOUND_PROVEN=NO
~~~

这正是当前 mission 的 BLOCKED blocker；不能用 retired client、test authorization、node -e、手工 require 或第二个脚本补上。

## 7. RAW 与 receipt

未来若通过真实受控 adapter，createStageDEvidencePersistence({ evidenceRoot }) 会在显式 approved evidence root 下建立 raw/ 与 receipts/：

~~~text
raw/<raw_sha256>.json             immutable RAW response, mode 0400
receipts/<capture_id>.json        immutable canonical capture receipt, mode 0400
~~~

receipt 必须绑定 capture_id、request_started_at、response_received_at、ingested_at、HTTP status、sanitized {regions: uk, markets: h2h, oddsFormat: decimal}、response size、RAW SHA/reference、sanitized quota headers、software version。RAW 与 receipt 均 hash/read-back validated；同名不同内容立即 fail closed。不能记录 API key、完整 secret、未清洗 credential 或完整 HTML。

真实 provider transport 在 stageDOperations.js:1758 固定 The Odds API EPL odds endpoint、uk、h2h、decimal odds，credential 名称为 THE_ODDS_API_KEY；它要求 ProxyProvider 的 health probes disabled，并执行单次 HTTPS request。该事实仅用于未来路径核对，本任务没有创建 transport、没有传入 key、没有调用 endpoint。

## 8. identity resolution

theOddsApiAdapter.js 与现有 registry/decision ledger 形成以下未来合同：

~~~text
CANONICAL_EVENT_ID=FootballPrediction-owned immutable opaque ID
THE_ODDS_API_ID=provider alias only
FOTMOB_ID=provider alias only
AUTO_GUESS=FORBIDDEN
AMBIGUOUS_IDENTITY=QUARANTINE
CORRECTION=SUPERSEDE_NOT_DELETE
~~~

每个 returned event 的 The Odds API ID 必须经 registry.resolve('event', 'the-odds-api', event.id) 命中既有、active、MATCHED identity decision；home/away/kickoff 必须与 registry 一致；bookmaker/market/selection 也必须由 registry resolve。unknown ID、duplicate provider ID、label/kickoff conflict、缺 decision、ambiguous identity 均 fail closed 或 quarantine，不自动创建 canonical ID。

“无 unsafe identity guess”的证据是：最终 transaction candidate/manifest 中每个 observation 的 canonical_event_id、provider_event_id、identity_decision_id、ruleset/resolver version 与 active MATCHED decision 精确相等；authority reader 再次验证这些绑定，并且 quarantine evidence 被保留。仅有 provider event ID 或 team label 不能作为证明。

## 9. canonical MarketObservation

未来路径是 persisted receipt + immutable RAW → prospectiveBatch → adaptTheOddsApiRaw → verified candidate → transaction-v1 publisher：

- adapter 只接受 JSON event array、EPL、有效 provider event ID/home/away/commence、唯一 provider IDs；
- 只接受 configured h2h / 1X2 / HOME-DRAW-AWAY，缺少完整结果、市场或 registry identity 时不生成可发布 observation；
- observation 绑定 canonical event、provider alias、decision、registry version/hash、adapter version、RAW SHA、receipt reference、capture times 和 provenance；
- response_received_at 是 response capture evidence；knowledge_time 由 publisher 在完成现有 authority/receipt/raw/candidate checks 后确定，不能早于输入证据；
- projection_available_at 必须等于 publisher-owned knowledge_time；
- strict as-of reader 只允许 knowledge_time <= decision_time，未来 response 不能回写到更早 decision time；
- malformed/partial/ambiguous data 的 coverage/quarantine evidence 必须与 accepted observations 一起验证，不能通过猜测补全。

## 10. transaction publication

GATE_2 没有、也不得有 transaction publication。未来只有在以下检查全部通过后才允许进入 publisher：

1. pre-request authority snapshot 与 fresh pre-publication authority reopen 都 verified；
2. RAW、receipt、quota reconciliation、identity decision、registry、observation provenance 全部 hash/reference 一致；
3. duplicate raw/capture/transaction classification 已完成；duplicate raw 只能返回 NO_OP_DUPLICATE_RAW_HASH，request 仍 accounted，不创建第二 canonical transaction；
4. candidate 的 parent transaction/state/allocation/registry/decision/observation hashes 与 authority snapshot 精确绑定；
5. publishProspectiveMarketEvidenceTransaction 以 transaction-v1 atomic staging/fsync/rename 写入 committed/，而非 .staging/；
6. rename 后 fresh authority reader 证明新 transaction 成为唯一 verified head；任一失败保留 consumed ledger/lock reconciliation 状态，不自动 retry。

成功 publication 的 future result 必须提供 transaction ID、parent ID、transaction/content/batch hashes、post state hash、accepted/quarantine observation counts、knowledge time、receipt/RAW references 与 publisher verification。它不包括 BET/NO BET、de-vig、Value Engine、staking、ROI 或 bankroll。

## 11. authority transition evidence

未来执行不得预填或猜测 after hash。必须持有如下 before→after 带完整 40 字符/hash 的 evidence：

~~~text
BEFORE_HEAD=tx_0ba8d4ad78aef57d1bbadf6637198b08d9586c5debf3e343d07033ed98a6bb64
AFTER_HEAD=<future fresh authority reader result; not invented>

BEFORE_STATE_HASH=df5084b6d752d698bfde4646fb508f3a41396f160fbee3cca9ee1b3b412e5ddd
AFTER_STATE_HASH=<future fresh authority reader result; not invented>

BEFORE_OBSERVATIONS=903
AFTER_OBSERVATIONS=<future fresh authority reader result; not invented>

BEFORE_STORE_SHA256=ed014a6f151143aa30cefcebc47374059aa18c38a83560610571331a665199e4
AFTER_STORE_SHA256=<future exact read; not invented>

BEFORE_ALLOCATION_AUTHORITY_SHA256=89e4276c8fe637318339821fe40d783d2f7fd8de65f6fc593b2035bd9445dad3
AFTER_ALLOCATION_AUTHORITY_SHA256=<future exact read; not invented>
~~~

After publication 必须再次读取 authority、STORE、allocation、committed transaction 和 ledger；如果 duplicate no-op，则 after authority 预计保持相同，但仍需 fresh read 证明，不能预先假定。

## 12. post-live quota reconciliation

未来成功或失败的唯一 provider transmission 都必须保存并交叉核对：

~~~text
provider x-requests-used
provider x-requests-remaining
provider x-requests-last
request ledger consumed/terminal record
pre-request local budget decision
post-request local durable ledger state
~~~

必须验证 expected cost 为 1；provider used/remaining 与 monthly limit 500 相加正确；last=1；provider used 至少覆盖 local consumed-after-request；remaining 满足 reserve/automated ceiling policy；和历史 provider reconciliation 单调。缺任一 header、数值非整数、不同步、回退、与 ledger 不一致或 response 不能可靠判断 transmission outcome 时，状态为 fail closed/人工 reconciliation，停止所有后续请求。

## 13. backup/recovery

未来 post-live backup 不是本 GATE_2 的写入动作。另行授权后必须：

1. 不触碰 accepted preauth snapshot；选择 Owner 批准的物理/管理独立 target；
2. 只从 cold-load-valid authority source 复制 transaction-v1 immutable packages、STORE、allocation authority、request epoch/entries、required run state、非 secret quota config；secrets 单独 provision，不进入 snapshot；
3. 写入 source identity、before/after authority identity、manifest、SHA256SUMS，最后写 SNAPSHOT_COMPLETE marker；任何缺项或 source identity 变化都使 snapshot invalid；
4. restore 到 isolated root，重新 cold-load authority、registry/provenance、STORE/allocation、exact post-epoch ledger 和 quota interpretation；
5. restore validation 必须证明 request-accounting epoch 与 immutable entries 在恢复后仍然存在，不能把历史 UNKNOWN 改成数字；
6. backup/restore 失败或 source/target identity 不明时停止，不再发请求、不自动恢复、不覆盖旧 snapshot。

当前仓库没有生产 backup/restore writer 或 canonical backup command；docs/data/STAGE_D_CONTINUOUS_OPERATIONS_CONTRACT.md 只定义了 contract，accepted artifact 是一次已完成的 external restore proof，不是可复用的未来执行入口。因此 future backup command 也不能在本计划中伪造。

## 14. final stop 与 fail-closed

未来在一次授权 provider transmission 及其 evidence capture、terminal ledger、quota reconciliation、identity/observation validation、publication/duplicate classification、fresh authority read 和 backup evidence 完成后，立即 STOP：

~~~text
不要第二次 provider request
不要第二个 Stage D cycle
不要启动或 enable scheduler
不要自动 retry
不要开始 value engine/de-vig/BET/NO BET/staking/backtest/model activation
~~~

以下任一情况立即 BLOCKED，不修复、不猜测、不扩大范围：main/head 不匹配；用户 dirty work 需改写；authority/hash/count 不匹配；snapshot/manifest/restore 不可验证；epoch 不明；历史 UNKNOWN 需猜数；quota/config/header 不明；runtime binder/one-request caller 不存在；provider/transport outcome ambiguous；identity 需 auto-guess；RAW/receipt/ledger/transaction/backup 任一持久化失败；当前 executor identity 无法读取 authority；任何测试可能接触 provider；需要 source-code repair 或 production authority mutation。

## 15. Future GATE_3 commands：全部未执行

下列只列已验证存在的命令和明确的 blocked placeholder；本文件中的任何 command 都没有在本 mission 执行 provider request。

### 已验证存在、但仅 offline 的 command

~~~bash
node scripts/ops/stage_d_cycle.js --dry-run \
  --authority-root data/market_evidence/live/transactions \
  --ledger-root data/market_evidence/live/request-accounting \
  --quota-config config/stage_d_quota_budget.json \
  --operation-root <explicit-operation-root> \
  --run-lock-trust-root <approved-trust-root> \
  --run-id <single-use-run-id> \
  --now <utc-now>
~~~

它可用于未来 owner/Chief Engineer review 前的 offline recheck，不会传输、不写 RAW、不写 canonical authority。当前 worktree 的 transaction package 普通 user 权限问题尚未解决，因此执行者必须先解决 executor identity；本任务使用受控只读读取进行 evidence verification，不把 sudo 变成 canonical future command。

### 明确 blocked、不得执行的 live action

~~~text
BLOCKED_LIVE_COMMAND=不存在可验证的 production shell/CLI command
BLOCKED_LIVE_CALL=executeStageDOneCycle(...)
BLOCKED_REASON=该函数需要 stageDOperations.js 模块私有 STAGE_D_RUNTIME_AUTHORIZATION Symbol；仓库没有生产 binder/caller，test-only authorization 不能用于 provider。
~~~

不要把上述 function text 改写为 node -e、heredoc、临时脚本、单测调用或手工注入 Symbol；那会形成未审核的第二入口并违反本计划的 authorization boundary。生产 backup/restore command 同样 BLOCKED_NOT_IMPLEMENTED_IN_REPOSITORY。

## 16. 检查过的文件、模块和外部 evidence

### 代码与配置

~~~text
scripts/ops/stage_d_cycle.js
src/infrastructure/market_evidence/stageDOperations.js
src/infrastructure/market_evidence/theOddsApiClient.js
src/infrastructure/market_evidence/theOddsApiAdapter.js
src/infrastructure/market_evidence/preflightRunner.js
src/infrastructure/market_evidence/evidenceStore.js
src/infrastructure/market_evidence/prospectiveBatch.js
src/infrastructure/market_evidence/atomicPublisher.js
src/infrastructure/market_evidence/transactionContract.js
src/infrastructure/market_evidence/transactionStore.js
src/infrastructure/market_evidence/authorityReader.js
src/infrastructure/market_evidence/downstreamReadiness.js
src/infrastructure/network/ProxyProvider.js
config/stage_d_quota_budget.json
data/market_evidence/live/transactions/STORE.json
data/market_evidence/live/transactions/allocation.authority.json
data/market_evidence/live/request-accounting/REQUEST_ACCOUNTING_EPOCH.json
data/market_evidence/live/request-accounting/entries/
~~~

### 文档与治理

~~~text
docs/CAPABILITY_INDEX.md
docs/PROJECT_VISION.md
docs/AGENT_WORKFLOW.md
docs/ACTIVE_MILESTONE.md
docs/PROJECT_STATUS.md
README.md
docs/data/STAGE_C_CANONICAL_MARKET_EVIDENCE_PILOT.md
docs/data/STAGE_D_CONTINUOUS_OPERATIONS_CONTRACT.md
~~~

### 测试

~~~text
tests/unit/market_evidence/stage_d_operations.test.js
tests/unit/market_evidence/stage_d_boundary_security.test.js
tests/unit/market_evidence/atomic_publisher.test.js
tests/unit/market_evidence/authority_reader.test.js
tests/unit/market_evidence/market_evidence.test.js
tests/unit/market_evidence/the_odds_api_adapter.test.js
tests/unit/market_evidence/preflight_runner.test.js
tests/unit/market_evidence/downstream_readiness.test.js
tests/unit/network/proxy_provider.test.js
~~~

### accepted backup/restore evidence

~~~text
/home/xupeng/FootballPrediction.artifacts/independent-backup-execution-restore-proof-20260909/VERIFY_STRICT_RUN.txt
/home/xupeng/FootballPrediction.artifacts/independent-backup-execution-restore-proof-20260909/restored/stage-d-preauth-20260909-20260909T012915Z-df5084b6d752/BACKUP_CONTENT_MANIFEST.json
/home/xupeng/FootballPrediction.artifacts/independent-backup-execution-restore-proof-20260909/restored/stage-d-preauth-20260909-20260909T012915Z-df5084b6d752/SNAPSHOT_COMPLETE.json
/home/xupeng/FootballPrediction.artifacts/independent-backup-execution-restore-proof-20260909/restored/stage-d-preauth-20260909-20260909T012915Z-df5084b6d752/SHA256SUMS
~~~

## 17. 本 mission 已执行的测试与只读检查

~~~text
git status --short --branch
结果：开始时只有当前非 main branch 行，无 dirty file；用户修改未被触碰。

git log -1 --format=%H; git rev-parse origin/main
结果：两者均为 21d8f030d5877d1059d1037d128980d756c35860。

test_area=$(mktemp -d /home/xupeng/FootballPrediction.artifacts/gate2-tests.XXXXXX)
mkdir -p "$test_area/a/b"
trap 'find "$test_area" -depth -type d -empty -delete 2>/dev/null || true' EXIT
TMPDIR="$test_area/a/b" NODE_ENV=test node --test \
  tests/unit/market_evidence/stage_d_operations.test.js \
  tests/unit/market_evidence/stage_d_boundary_security.test.js \
  tests/unit/market_evidence/atomic_publisher.test.js \
  tests/unit/market_evidence/authority_reader.test.js \
  tests/unit/market_evidence/market_evidence.test.js \
  tests/unit/market_evidence/the_odds_api_adapter.test.js \
  tests/unit/market_evidence/preflight_runner.test.js \
  tests/unit/market_evidence/downstream_readiness.test.js \
  tests/unit/network/proxy_provider.test.js
结果：115/115 pass，0 fail；使用 networkless fake/test-only paths，没有 provider request。

operation_root=$(sudo -n mktemp -d /root/gate2-offline-operation.XXXXXX)
trust_root=$(sudo -n mktemp -d /root/gate2-offline-trust.XXXXXX)
sudo -n env -u THE_ODDS_API_KEY -u THE_ODDS_API_PROXY_URL node scripts/ops/stage_d_cycle.js --dry-run --authority-root "$PWD/data/market_evidence/live/transactions" --ledger-root "$PWD/data/market_evidence/live/request-accounting" --quota-config "$PWD/config/stage_d_quota_budget.json" --operation-root "$operation_root" --run-lock-trust-root "$trust_root" --run-id gate2-readonly-offline-plan --now 2026-09-09T02:00:00Z
sudo -n rm -rf "$operation_root" "$trust_root"
结果：offline plan；provider_requests=0，canonical_authority_writes=0，authority=tx_0ba8...，state=当前 accepted state，observations=903，ledger usage=0，budget allowed=true；临时 operation/trust roots 在外部临时目录中清理，未写 production authority。

sha256sum -c <accepted snapshot>/SHA256SUMS
结果：10/10 files OK；之后用 restored root 做 authority cold-load，head/state/903 一致。
~~~

首轮没有使用 task-specific writable TMPDIR 的测试尝试在 / fallback trust root 上失败了 4 个权限相关 setup cases；随后以可写临时目录完整重跑，115/115 通过。该失败没有触碰 provider、production authority 或用户文件。

## 18. 本 mission 的副作用核对

~~~text
REAL_PROVIDER_REQUEST_EXECUTED=NO
PROVIDER_QUOTA_CONSUMED=NO
PRODUCTION_AUTHORITY_MUTATED=NO
SCHEDULER_STARTED=NO
STAGE_D_STARTED=NO
RAW_APPEND_FROM_LIVE_REQUEST=NO
CANONICAL_TRANSACTION_PUBLISHED=NO
REQUEST_LEDGER_MUTATION_FROM_REAL_REQUEST=NO
STAGE_D_AUTHORIZED=NO
PROVIDER_REQUEST_AUTHORIZED=NO
~~~

artifact 创建不在 production authority root；没有 source-code change、commit、push、schema migration、DB write、raw write、training、prediction、backtest、model activation、provider fallback 或 second provider。

## 19. Documentation Impact

~~~text
CAPABILITY_INDEX_UPDATE_REQUIRED=NO
ACTIVE_MILESTONE_UPDATE_REQUIRED=NO
PROJECT_STATUS_UPDATE_REQUIRED=NO
README_ENTRYPOINT_UPDATE_REQUIRED=NO
PROJECT_MAP_UPDATE_REQUIRED=NO
PROJECT_VISION_UPDATE_REQUIRED=NO
~~~

理由：本任务只新增 GATE_2 evidence/plan artifact，不改变 canonical entrypoint、runtime behavior、能力状态、数据合同、authority、milestone、project status 或 vision；现有文档仍准确地把 public CLI 定义为 offline-only 并把 live adapter 定义为 operationally disabled。当前 artifact 中的 BLOCKED 结论不能替代 owner/Chief Engineer 对上述 current-state 文档的正式状态更新。

## 20. 结论

~~~text
MISSION_STATUS=BLOCKED
BLOCKER_COUNT=3
BLOCKER_1=没有 production binder/CLI 可持有模块私有 runtime authorization；无法证明未来实际 caller 只发一次 request；修复需要另行授权的 source/governance mission。
BLOCKER_2=当前 committed transaction package 对普通 xupeng runtime user 为 root-owned/0400，authority reader 在该 identity 下无法安全 cold-load；executor identity/permission contract 未建立，不能以临时 sudo 绕过。
BLOCKER_3=accepted snapshot 的内容与 restore 已验证，但当前证据与 primary worktree 共享 /dev/nvme0n1p5，物理独立故障域未证明；future post-live backup target/restore policy 仍需单独 owner/infrastructure authorization。
~~~

最小后续 remediation mission：由 Owner/Chief Engineer 单独授权，先定义并审核唯一 production live binder/entrypoint（同一受信 process 内获取 private runtime authorization、绑定实际 executor identity、显式 one-request invocation 和 post-live stop），解决 authority read permission contract，再指定不同故障域 backup target 并重做 isolated restore proof。该 remediation 不属于本 GATE_2，本文件不实施。
