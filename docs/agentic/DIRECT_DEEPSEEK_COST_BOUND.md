# Direct DeepSeek 条件性费用上界与离线实现

lifecycle: permanent
owner: engineering workflow governance

MISSION=CANONICAL_DEEPSEEK_CONSERVATIVE_COST_BOUND_RECOVERY
WORKFLOW_CLASS=CRITICAL
PROJECT_ROOT=/home/xupeng/FootballPrediction.deepseek-direct-bound
CURRENT_BRANCH=feat/deepseek-conservative-cost-bound
CURRENT_HEAD_AT_START=05dc75eb9c2e9e5ec042840d91fee4a3d480ce60
CURRENT_DIRTY_STATE_AT_START=CLEAN
BASE_SHA=05dc75eb9c2e9e5ec042840d91fee4a3d480ce60

## 官方证据，2026-10-09 只读复核

- https://api-docs.deepseek.com/quick_start/pricing ：`deepseek-flash` 当前是
  DeepSeek-V4.1-Flash，context length 1M；峰值输入 cache miss $0.30/百万，
  cache hit $0.006/百万，输出 $1.20/百万。价格可调整；旧别名也可路由到新模型。
- https://api-docs.deepseek.com/api/list-models ：`context_window` 是输入与输出的
  总 token 容量；`max_output_tokens` 是服务器单次允许的输出上限。
  本轮只读文档，未请求需要凭据的 `/models`，没有取得当前账户的实际 metadata。
- https://api-docs.deepseek.com/api/create-chat-completion ：`max_tokens` 限制生成 token，
  输入和生成的总长度受 model context 限制，允许 1..393216；usage 的 completion
  details 可包含 reasoning。`finish_reason=length` 表示输出或上下文限制导致生成结束。
- https://api-docs.deepseek.com/quick_start/token_usage ：字符换算是近似值；实际以 usage
  为准。离线 tokenizer 可以估算，不是本实现的金额安全依据。
- https://api-docs.deepseek.com/guides/thinking_mode ：thinking 默认开启，可明确禁用。
  本实现只允许 disabled + reasoning_effort=none；无工具、图片、prefix、stream 或多轮对话。

直接保证：文档规定总上下文容量、生成上限和 token 计价方式。合理推导：若全部可计费输入
受公布窗口限制，全部输出受 max_tokens 限制，价格不高于冻结峰值，则可以按完整窗口预留。

未获保证：超窗口输入的具体拒绝/截断语义、拒绝或中断请求的窗口外可计费处理、未披露费用，
以及价格/别名在 Provider 侧锁定。API 的 reasoning usage 字段不能单独当作全部物理计费保证；
此实现禁用 thinking，发现任何 reasoning 内容/usage 则 UNKNOWN，但事后检测不能撤销费用。

因此结论只能是 **CONDITIONAL_COST_BOUND / NO_GO_FOR_LIVE**。

## 保守计算

1M 按更保守的 1,048,576 计算。每请求固定 max_tokens=8192：

`ceil((1048576 * 300000 + 8192 * 1200000) / 1000000) = 324404 microUSD`

整轮为冻结请求数 N × 324404 microUSD，N<=64；64 请求预留 $20.761856。
全部缓存均按峰值 miss，不预期低谷优惠。输入+输出同时按各自上界预留，允许保守重复计算。
这是指定计价/窗口合同成立时的条件性预留，不是 Provider 无条件美元硬帽，也不是整个 Factory
所有 lane 的费用上界。没有调整现有预算；超过 grant 或 Factory token admission 一律拒绝。

## 发送与 UNKNOWN

现有 canonical chunk planner、aggregate、generic receipt、source/HEAD verifier 被复用。
新 backend `direct-deepseek-api` / harness `footballprediction-direct-deepseek` 不调用 Claude CLI。
旧入口、历史 receipt 和旧身份校验保持；没有静默 fallback，也没有自动切换默认审核 policy。
新 registry entry 为 `reserved`，`LIVE_EXECUTION_APPROVED=False`，正式 consumer 拒绝 fixture。

固定标准库 HTTPSConnection 向 api.deepseek.com:443 发一次 POST /chat/completions；不使用 SDK、
代理发现或重试循环，3xx 不跟随。完整 payload/manifest/hash/runtime/条件性费用预留在第一笔
发送前冻结。实际 max_tokens、禁用 thinking 和 JSON 格式写入 Provider body。

固定外部状态目录为 `/home/xupeng/.local/share/footballprediction-reviewer-state/direct-deepseek`；
SQLite FULL/DELETE journal 和 BEGIN IMMEDIATE 保留 authority。每行先 RESERVED，然后发送前
commit UNKNOWN；成功原始 response 另写 append-only completed。任何没有完成记录的 UNKNOWN
阻断全局新发送/新授权。异常文字仅为固定分类，不保存错误正文，拒绝直接及 JSON escaped Key。

A=manifest backend/chunk 数；B=发送前持久化 UNKNOWN 行数；C<=B，但失败请求是否已被 Provider
接受仍 UNKNOWN；D=完成响应的 usage。四者不混同。完成记录可在恢复时读取，不再发 HTTP；
发出后但完成记录丢失则保留 UNKNOWN，不退款、不重发。恢复需逐字节匹配原 manifest、grant、
model/policy/runtime 和 exact source identity，不能以新授权扩大旧预留或洗掉 UNKNOWN。
本地声明的 model/price contract 改变导致 hash 失配；无法离线检测 Provider 的静默变化，所以
没有解除 live 阻断。与原 ENGINEERING_INDEPENDENT_REVIEW 一样，不声称抵抗同 uid 恶意删除
或篡改 authority 文件。

## 身份和交接

runtime digest 绑定 runner、发送层、validator、chunk/protocol/source helper、Python binary、
HTTP/TLS 实现和 OpenSSL version。receipt 原始字节/哈希、完整 request bytes、响应原始字节、
scope 和 exact HEAD 被重新校验；旧 Claude SHA 不作为任何 Direct 证明。

离线 tests 只在内存中将测试 registry 激活，并显式使用 OFFLINE_FIXTURE。它们证明代码兼容，
没有批准新生产身份，也没有真实 Provider provenance。生产 registry/resolver/paid preflight
仍拒绝。未来接替原 default/CRITICAL DeepSeek lane 须独立审查和明确 policy 决策；本轮保留原
双回执门禁，不让 Direct fixture 自动满足旧 Claude 门禁。

Harness 显式 plan-only 预算桥复用可信 base runner，把完整物理 request count 和整轮容量
绑定 Controller target；仅在 max_run_tokens 能覆盖整轮且 max_total_tokens 足够时返回 admission。
普通 Factory dispatcher 没有自动切换；现有 first_paid_execution HARD_BLOCKER 保持字节不变。

## Documentation Impact

EXISTING_CAPABILITIES_REVIEWED=YES
CURRENT_MILESTONE_REVIEWED=YES
CAPABILITY_INDEX_UPDATE_REQUIRED=YES：登记独立离线基础设施及 BLOCKED 状态。
ACTIVE_MILESTONE_UPDATE_REQUIRED=NO：未改变 closing research、Stage D 或任何业务交付状态。
PROJECT_STATUS_UPDATE_REQUIRED=NO：未运行真实 Provider，未获得新的生产可用性证据。
README_ENTRYPOINT_UPDATE_REQUIRED=NO：新身份 reserved，不建立新的正式业务或默认审核入口。
PROJECT_MAP_UPDATE_REQUIRED=NO：文件均位于既有 scripts/devops、unit tests 和 agentic 文档边界。
PROJECT_VISION_UPDATE_REQUIRED=NO：只修复已有审核执行边界，不改变业务目标架构。

## 本轮验证与本地提交边界

- Host 离线专项：`python3 -B -m pytest --noconftest -q -o addopts=''`，选择 Direct bound、
  原 Claude runner/isolation、generic protocol、chunk、review policy、Codex auth isolation 和
  agentic workflow 八个模块：182 passed。32 个 Direct 用例包括实际 HTTPSConnection 边界的
  fake connection 全路径、并发拒绝、部分多 chunk 恢复、价格变化和 fixture/live 身份隔离。
  不加载数据库 fixture/.env，不连接真实 Provider。
- 六个修改/新增 Python 文件的 Ruff check、format check 和 git diff --check 通过。
- 项目 `make verify VALIDATION_PROFILE_RUNNER='python3 -B scripts/devops/validation_profiles.py'`
  在 bwrap 断网、只读隔离中执行了原 strict dispatcher；缺少 worktree Node QA 依赖，npm
  初始化被隔离阻断，make exit 2。没有启动 Docker、连接或写入 DB，也没有安装依赖。
- 原 commit hook 的 hermetic gate 同样在隔离中尝试，因缺少 eslint 拒绝。为了保存用户要求的
  本地离线审查 checkpoint，commit 仅此次命令禁用 hook，不永久修改 hooksPath/config。
  这不是任何 gate PASS，不是正式项目验证、Full Review、生产审批或 merge authorization。


### 一次性 Standalone Direct 候选（离线，默认关闭）

仅对含 `STANDALONE_DIRECT_V1` 冻结合同的 CRITICAL scope，已验证的
`direct-deepseek-api` 可以替代旧 CLI 的 DeepSeek 身份；不冒充 `claude-code-deepseek`，
不改变 NORMAL/STRICT 或无该合同的 CRITICAL。Registry 仍 reserved、全局 live 仍 false。
该限定路线需要未来单独批准的 owner-only `standalone-informed-risk/v1` 授权：准确同币种 USD 或 CNY 金额、
账户余额及可接受暴露、价格摘要、完整最终执行身份/plan hash、runtime、source、请求清单、
到期时间、容量以及一次 canonical Codex。没有授权默认拒绝；离线 fixture 永不构成 current approval。

复用原 Journal，整轮在首个 HTTP 前预留；最多 13 POST：4 Qualification、
8 FootballPrediction review、1 Harness companion review。完整固定清单使用 17 次逻辑 HTTP：
启动 price/models/balance 三次 GET、全部 13 POST、结束余额一次 GET；仅公开价格允许
一次白名单 302 follow-up，物理 HTTP 最多 18。12 POST 的较小合法计划仍可准入。
13 POST 整轮保守容量为 13 × (1,048,576 + 8,192) = 13,737,984 单位，需未来独立批准。
正文上限 40,000 bytes、每次输出上限 8,192 tokens 不变；未使用名额不得补救或挪用。
无 retry/模型 POST redirect/格式修复/续写；资格、审查失败或
UNKNOWN 后立即停止；一次 Codex 认领持久化后不重新认领。全部响应、来源及资格语义由 consumer 重算。

`PHYSICAL_COST_BOUND=UNPROVEN`。客户端整轮条件性预留不是 Provider 账单硬帽；金额不写死为
USD5 或历史估算。账单未结算保持 UNKNOWN，不能记零或退还失败请求预留。Standalone 独立容量
必须明确批准，不能自动绕过 Factory 2,000,000 cap 或 first_paid_execution HARD_BLOCKER。
最终提交后重新计算完整 scope/source/chunks/请求/条件金额；旧 receipt 和旧 strict 仅为历史证据。
此候选不授予真实调用、充值、production、merge 或正式验收权限。

公开价格准入仅允许官方HTTPS价格白名单（既有 pricing、zh-cn/pricing及其尾斜杠），
最多一次302；额外GET发送前持久化并计入18 HTTP上限，不授权POST重试。需真实核验最终URL；
未知目标/模型/币种/计费档位/时间/正文或缺少完整价格快照一律拒绝生产执行。
CNY使用独立microCNY字段，USD保留microUSD字段；整轮预留、余额、授权和ledger同币种，
没有自动汇率或合并。生产需24小时内、完整六档价格且首次GET正文重验；旧价格仅可离线兼容。
CNY固定中文入口，USD保留英文入口；中文空闲/高峰六档原币价格由原验证器校验，
最终URL与计划及快照绑定。已观察中文公开报价；新HEAD正式strict及生产价格重验仍待授权，
费用候选不是grant，模拟价格不是官方报价或真实调用授权。


### Direct / Reviewer V2 最小争议适配（离线资格候选）

新 RUNNER_VERSION=1.2.0，与 Registry 对应版本相等。只复用冻结 Harness
`ea507645cc143b883927fbb67b164cc85d4503a5` 的 `reviewer_v2_contract`：
`bind_findings`、`parse_synthesis(structured_evidence=True)`、`validate_source_binding`
和 `validate_bound_result`。不调用 V2 CLI，不把 Direct receipt 冒充 HMAC V2 receipt，
也不修改 Harness。认证仍由 Direct exact runtime、一次性 grant、append-only Journal
与原 consumer 的完整重算共同提供；沿用同 UID 本地工程 assurance model。

启用须在新的已提交 CRITICAL scope 的 protected_invariants 加入
`DIRECT_DISPUTE_V2={"version":"direct-dispute-v2/v1","groups":{...}}`。
每个 `football:<index>` 和 `harness:<index>` 必须恰有一个 group。
其值为来源列表 `[{"source":"football"或"harness","start":整数,"end":整数}]`，
半开 UTF-8 范围引用同一已批准来源的 canonical 完整 Git diff；也可显式带 `path`
引用同一 Source Binding 已列出的 HEAD blob（详见下方最终 scope 合同）。
只允许冻结 Scope 中明确批准的 diff/blob bytes；每组最多16个范围，
包括身份头在内的 exact source 总计最多16,000 bytes。显式批准的其他 chunk 来源
可以加入同组；不会自动搜索任意文件或扩大 scope。范围必须在付费前选择并被 grant
所绑定。来源不足时只能维持阻断，不能改范围后复用旧授权。

原始 review 的 protocol/severity/title/evidence 和完整 response 一律保留；
V2 投影和机器 CxxxFxxx ID 是系统派生记录，附原 response/request hash、group、
execution、mission、HEAD/tree、scope、runtime 与 source 身份，绝非模型原生字段。
每个 chunk 后有一次独立 group 调用，覆盖全部 blocking finding；UPHELD 阻断，
DISPUTED 必须有模型独立语义判断及 exact source_id/UTF-8 byte range/quote。
引用还必须完全落入批准的代码范围，身份头与范围标签不能成为免责证据。
UNDETERMINED/缺失/伪造/新P0/P1/P2/预算或容量不足均停止。
只有 group PASS 可以继续下一个 chunk，最后固定一次 cross-group 调用重新检查
全部原始 finding 与裁定；没有源码的最终阶段不能争议，只能维持问题或提出新问题。
本适配没有人工 override、历史裁定导入、模型白名单或自动重试。

计划预留显式模板槽；动态正文仅由持久完成的原始响应和固定模板确定性派生，
实际 bytes 在 materialized 表中 append-only 持久化后才认领 UNKNOWN 和物理发送。
HTTP transport、consumer 都重算这些 bytes，不能由调用者替换 prompt。
原 requests 保存模板，completed 保存全部真实原 response，原始 response 不被覆盖。
consumer 重新构造来源、machine IDs、裁定、最终原协议结果、动态正文及完整账本，
provenance 增加 dispute_audit_sha256。审计记录可由完整 raw evidence 重新派生。
OFFLINE_FIXTURE 可以在显式测试 context 验证，但正式 consume_direct 永远拒绝它。

新 grant 必须使用 `standalone-informed-risk/dispute-v2` 并明确
`dispute_authority_approved=true`，绑定整个新计划、runtime、来源、币种、价格、
余额风险、budget、expiry 和全部物理上限。旧 v1 grant/receipt/FAIL 不能升级或导入。
旧 V1 13 POST/18 HTTP 合同保持；没有新 scope marker 不能隐式启用争议。
历史两轮 FAIL 和 ledger/receipt 不变。本实现不签发任何生产 grant。

若 R 为完整双仓库 review chunk 数，新计划为4 Qualification + R Review + R group
+ 1 cross-group：模型 POST = 5+2R，逻辑 HTTP = 9+2R，最多一次价格302后
物理 HTTP = 10+2R。R 最多16，因此硬上限37 POST/42 HTTP；原九块时为23/28。
每项正文仍≤40,000 bytes、output≤8,192 tokens，max requests=64不变。
容量=(5+2R)×(1,048,576+8,192)；九块=24,305,664，绝对准入最大39,100,416。
这不是实际token消耗；Factory 2,000,000和 first_paid_execution HARD_BLOCKER 不变。
模板和实际正文使用同一max_tokens，按整轮最坏价格预留，不退款失败或未结算风险。
金额计算复用 request_cost 的同币种整数上取整：每项
ceil((context_capacity×peak_cache_miss_rate + max_output×peak_output_rate)/1,000,000)。
未来按官方CNY价格/余额重新批准；历史¥29不适用于新计划。

动态finding或最终复核内容若不能装进40,000 bytes：在发送前停止，不裁剪原finding、
不隐藏证据、不另增请求。一次group最多16,000 bytes原finding；任何来源、证据或
最后摘要容量不足仍fail-closed。本合同不保证所有有效模型输出都能完成整轮。
完整scope及具体跨chunk证据范围仍须在未来候选中被独立审批。

Documentation Impact：只增加既有工程审查能力的离线候选，未改变业务逻辑、训练、
数据入口或生产可用性；CAPABILITY_INDEX更新对应状态，其余current-state/README/
PROJECT_MAP/PROJECT_VISION不变。正式strict、新Qualification、真实完整review、
独立Codex、required CI和用户批准合并均未完成，不得声明CRITICAL正式验收成功。

### 最终完整 scope 与支持来源（离线冻结候选）

`DEEPSEEK_DIRECT_V2_FINAL_SCOPE_REQUEST_BOUND_AND_FREEZE` 保留原 Option B
`82b007a27232e5fdd7568c0797cb35c7a8fd26d6` 至最终 HEAD 的全部 canonical diff，
不以适配基线替代完整范围。八个 Football chunk 是旧计划事实；新 chunk 数由
现有 32,000-byte 确定性算法计算，不隐藏新增代码以维持八块。

争议引用可用 `{source,start,end}` 指向完整 diff，或用
`{source,path,start,end}` 指向 Source Binding `files` 已列出的冻结 HEAD 普通 blob。
后者用于 diff 没展示的未改动版本 gate；不是任意路径读取，也不扩大必审 diff。
同一 HEAD 的 blob/mode、源码范围、UTF-8 边界、组来源 hash 与执行身份均重新验证；
仍由冻结 V2 验证精确引用。组支持证据包含 Registry、Runner 版本/runtime、双仓库
Source Binding 和版本验收条件。未知 finding 若不能由已批准证据证明，仍阻断。
支持范围不是原审查覆盖，重复提供支持证据不会重复认领 canonical bytes。
所有组 source（含身份头）最多16,000 bytes，实际 JSON 正文最多40,000 bytes，
每 POST 输出仍最多8,192 tokens；超限停止，不截断、续写、扩组或补发。

令 R 为实际 Football + Harness Review chunks：四项 Qualification、R项 Review、
R项独立组复核和一次最终复核，共 `5+2R` POST；四项余额/价格/模型 GET，
逻辑 HTTP=`9+2R`，最多一次价格302则物理 HTTP=`10+2R`。
组复核在无 finding 时也执行，最终复核只在全部前缀有效后执行。
R<=16 的实现包络为37 POST/41逻辑/42物理 HTTP；它不授权某一 grant 使用整个包络。
具体 grant 必须精确绑定实际 canonical plan 的请求数和全部唯一 ledger 槽，不能追加调用。
Standalone 容量=`(5+2R)×1,056,768`，每 POST 同币种费用预留由生产
`request_cost` 逐项算出；这是容量/条件性预留，不是实际 Provider tokens 或账单硬帽。
旧27/32数值仅为旧 HEAD 的大小估算；以后必须以最终 manifest 为准。
本次没有人民币批准、官方价格核验、真实请求、strict 或正式 receipt；均须未来独立准入。

## 本地交付测试来源（F1/F2）

Direct standalone/dispute 的离线测试显式要求 `CMH_OFFLINE_HARNESS_ROOT`。
缺少来源或冻结身份不符会失败，不会跳过。当前依赖是 Harness
`ea507645cc143b883927fbb67b164cc85d4503a5` 加 tracked diff SHA-256
`311f336d73c3a353d4f3f17c3111d4e7d33c914ca2e2bb43279e491f65841b25`。
该来源只提供原资格合同和 task-budget 集成代码；H1/H2 尚未交付，不能把本机工作树
当作 PR 的隐式依赖。测试时应先核验来源、复制到临时目录，再通过环境变量显式传入。
两仓库最终版本完成后重新冻结测试来源并复跑，状态为
`CROSS_REPO_FINAL_INTEGRATION=PENDING_HARNESS_DELIVERY`。

`tests/helpers/direct_harness_source.py` 从验证过的源码创建临时 Git companion，
以真实 Git base/head/tree/diff 经过原 source binding。companion 的改动和 Provider
响应均明确为测试输入；生成的 `OFFLINE_FIXTURE` 不构成正式 Qualification、Receipt
或付费授权，正式消费者继续拒绝。整个测试运行必须断网、隔离真实 HOME/凭据，
并禁止真实 Codex、DeepSeek、Docker 和 GitHub 写入。正式消费者正向验收仍为
`PENDING`；此处不新增生产测试模式或授权。
