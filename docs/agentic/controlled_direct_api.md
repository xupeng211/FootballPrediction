# 受控 Direct API 执行候选

- lifecycle: permanent
- owner: engineering workflow governance
- status: OFFLINE_CANDIDATE / UNQUALIFIED / LIVE_DISABLED
- readers: 执行 Controller、审核工具链维护者

此候选不解除 #1946 / #1941 的正式审核阻断。工作流仍以 AGENTS.md 为准；本页不授予
费用、网络或审核资格。已经实现并验证本地 TLS broker；没有真实 Provider admission、真实 API Key 加载或 live 开关。

## 实现和复用

`controlled_api_policy.py` 复用现有 canonical JSON / SHA 校验；Runner 复用
`independent_review_protocol.validate_result`。旧 Direct DeepSeek 冻结代码中的 SQLite
BEGIN IMMEDIATE、发送前 claim、不退款原则被局部复用，没有搬运旧资格或 Receipt。
Registry、正式 Runner、Review Policy、AI Gate 的审核判定保持原样；DB-write scanner 增加下述精确执行状态分类。

本分支从 main 独立派生，不包含 #1946 的 placeholder 修复；正式输出资格接入前必须
依赖该修复交付或验证等价完整校验。当前任何结果都不能变成正式 PASS。
COMPLETE 只表示离线 HTTP / 响应校验完成，真实 P2 响应也可 COMPLETE；它不是审核 PASS。
execution evidence 始终包含 `current_approval_eligible=false` 和 `qualification_required=true`。

## 预算与执行边界

可信 Controller 调用 `Budget(root, initialize=True).create(source, plans, requests=..., tokens=...,
nano_usd=...)` 一次性建账。完整 source（repository、mission、base/head、diff/scope SHA）
和所有计划冻结；同 repository/base/head/diff 不能更换 mission/scope/run 名称重领预算。
不同 Provider 与分块共享该任务总帽。source 是 Controller 提交的绑定声明，此模块不提取
Git diff，不是正式 source-binding 证明。

`execute` 在实际 POST 前原子计入请求、全窗口 Token 和条件性 USD 预留；未授权、
超预算或已认领的槽拒绝发出请求。每个槽只认领一次，不重试、不跟随重定向、不执行工具。
超时、断流、崩溃、Usage 缺失/超限、格式错误、记录失败不退款、不重发。claim 后 send
前崩溃也按最大可能费用保留；恢复沿用同账本；状态缺失不自动新建，初始化只接受全新目录。目录 0700、数据库 0600，不存 Provider
原始响应或凭据；只保存请求计划、源身份、安全状态、响应 SHA。

内部入口：`python3 -m scripts.devops.controlled_api_runner --state-root <root> --task <id>
--slot <n> --plan <json> --offline-socket <mock.sock>`，要求事先建账。
仅支持 AF_UNIX HTTP 上的本地 Mock OpenAI Responses / DeepSeek Chat，无 SDK 隐式重试。
任何新账本都不得指向历史审核或业务 Ledger。

`controlled_api_sandbox.run_offline` 使用 bwrap 网络 namespace、最小只读系统挂载和
清空环境，不暴露 HOME、真实密钥、宿主 socket，只暴露选定 mock socket 和任务状态。
无 namespace 时拒绝执行，无宿主降级。直接 CLI 是可信离线测试入口；可选 sandbox
helper 不等于未来生产出口的不可绕过部署。新 broker worker 入口见下；真实 Provider 的 production admission/部署仍未完成。

信任 Controller、owner 文件系统及 mock socket；同 UID 恶意改库/删库、备份回退不是
抗攻击保证。不同目录/新 source 的建账必须由未来唯一授权根约束；本阶段没有生产
Controller，不能声称跨目录、跨来源的不可绕过预算。任意 Unix relay 也不自动成为可信
Provider broker。

## Token 和条件性价格

金额仅为 nano-USD（1 USD = 1,000,000,000 nano-USD）的固定快照预留，不等于 Standard
credits；两者不能直接兑换。输入保守预留整个 context，不依赖未经认证的 tokenizer。

| 模型 | 输入预留上界 | 输出参数上限 | 条件性费率 USD / 1M tokens（输入 / 输出） |
| --- | --- | --- | --- |
| gpt-5.6-terra | 1,050,000 | max_output_tokens: 128,000，含 reasoning | 5.00 / 18.00，含长上下文、cache write 最坏乘数 |
| deepseek-flash | 1,048,576 | max_tokens: 393,216 | 0.30 / 1.20，cache miss / peak |

OpenAI 使用 default tier、truncation disabled、medium reasoning；DeepSeek thinking
显式 enabled。不请求工具、音频、图像、批处理或其他附加收费服务。新旧审核质量是否
等价仍须重新 Qualification，不能用参数设置代替。

快照依据 2026-10-21 已获取的
[OpenAI 模型页](https://developers.openai.com/api/docs/models/gpt-5.6-terra)、
[Responses](https://developers.openai.com/api/reference/resources/responses/methods/create)、
[DeepSeek 价格](https://api-docs.deepseek.com/quick_start/pricing)及
[Chat](https://api-docs.deepseek.com/api/create-chat-completion)。公开参数/单价不能证明
执行期间锁价或所有实际收费项有界。两路及合计实际金额硬帽均 **NOT_PROVEN**。

## 验收和迁移

现有 `gatekeeper.sh` 的 canonical Python 清单追加这三个测试文件，确保 PR CI 实际执行
新控制逻辑；原有测试和门禁不删除、不降级。

`CONTROLLED_API_REQUIRE_SANDBOX_TESTS=1 python3 -m pytest -q tests/unit/test_controlled_api_*.py`
强制实际 namespace 验收。普通 CI 缺 bwrap/namespace 时明确 skip 集成项，不能计为隔离
已通过。本地 HTTP mock 测试不是 Provider 计费保证。

真实审核仍缺：供应商计费上界/价格保证、唯一授权根与跨任务总预算、真实 HTTPS broker
凭据隔离及不可绕过出站部署、正式 Git/source binding 和完整结果持久化、两个新通道
的独立 Qualification、Registry/Receipt/Policy 的合法迁移。环境变量、mock PASS 或旧 CLI
资格不能代替以上条件。

下一步先审阅本候选，围绕具体价格保证和局部 broker/admission 补齐缺口；不开发新调度
框架。#1946 和 #1941 保持原 HEAD 与审核状态。不得手工改 AI Gate 或自动 merge。

## PR1947：专用写入分类与 TLS broker

预算库是必要的执行状态，不是历史业务 Ledger、正式 Receipt 或历史 Evidence。
初始化只接受全新目录、O_EXCL 文件；新增 `.execution-state` 私有标记与 SQLite
application_id，每次连接重验目录、文件、marker 权限/类型/身份。任意现有目录、
无标记/错误标记、普通 SQLite 或 symlink 替换都拒绝；旧离线库不自动迁移或重置。

现有 python_db_write_allowlist 的 entries 历史条目内容和30项计数保持不变；独立
execution_state_entries 列表中的新增分类是
`local_execution_state_write_runtime_guarded`，不是 historical 豁免。scanner 仅接受
精确 budget.py 路径、完整 storage_contract、禁止业务 store 标记和代码 SHA256。
该文件任何后续改动都须显式更新分类并重新验证，未知路径/错误 hash 仍 fail-closed。
此分类不授予任意数据库写入或 Provider 权限。

`controlled_api_broker.Broker` 由可信 Controller 持有固定账本、任务、计划和凭据。
worker 只能通过私有 AF_UNIX socket 提交 task/slot；无法选择 URL、替换请求体、
传凭据、修改价格或发建账指令。claim 持久提交后才允许唯一的 HTTPS POST。
多个 broker 共享 SQLite 原子预算；崩溃/重启/重复 worker 不重新获得额度。
完整规范化结果写入私有独占文件并 fsync 后才 COMPLETE；原始 HTTP 响应不保存。
凭据出现在模型响应中时拒绝结果持久化；所有错误仅返回安全类别。

`controlled_api_https` 使用标准 TLS 验证（CA chain + hostname，TLS>=1.2），
固定 IP socket、固定 hostname/path、忽略代理/DNS、不重定向、不重试。
目前 admission **只接受 127.0.0.1 / localhost、自签测试 CA 和 fixture- 合成凭据**。
官方主机、外网 IP、真实凭据和无 fixture 路径均在发送前拒绝。
因此 HTTPS 传输机制已实测，但不能声称生产 Provider 出口已经获得 admission。
生产 host/credential/锁价接入不得通过环境变量解锁，必须单独证明计费和部署条件。

`broker_worker_command` 创建无网络的真实 bwrap 进程，仅挂载 scripts 与 broker socket；
不挂载预算库、凭据、HOME 或整个 Git 工作树。本地实测直连 TLS 服务失败，固定任务
经 broker 成功。可信 broker 的源码和 Controller/owner 仍属信任边界；没有证明能抵御
恶意同 UID Controller、其他目录重新建账或替换宿主 broker。未来生产应以唯一任务
授权根和独立凭据/出站部署约束它们，不能把本地 namespace 测试当作生产部署证明。

## 新通道身份、Source Binding 与自举边界

`controlled_api_binding.bind_source` 从 clean exact HEAD 的 Git object 读取 scope，
复用 exact_head、MissionScope 与路径授权校验；三点 binary diff 的哈希格式与正式
Receipt 校验一致。未知/旧 HEAD、dirty、非普通 scope、scope 不匹配或越界改动拒绝。
该 helper 为 Controller 准备绑定，不使旧离线 caller 声明自动获得正式效力。

TLS 结果的独立身份为 `controlled-direct-api/https-candidate-v1/<provider>`（artifact
channel 不带 provider，model 单独记录）。两路均 NOT_RUN / UNQUALIFIED，无旧资格继承，
无正式 Receipt emitter，也不接入现有 AI Gate 作为 PASS。
`qualification_requirements` 明确列出供应商保证、唯一出站、付费授权、独立资格、
Registry/Receipt 合法迁移和自举独立审核的前置条件；不是 Qualification 通过证明。

合法自举在当前约束下仍未闭环：新通道不能审自己并自授资格；旧 CLI 无已证明硬帽，
Owner 也未接受风险例外。必须先取得能约束既有合格审核通道的强制供应商/网关硬帽，
或由 Owner 定义不降低 CRITICAL 独立性与资格的新迁移合同并单独审查。两者尚未具备，
不通过修改 Gate 或添加假 Receipt 解除。继续扩写应用预算代码不能补齐此外部信任来源。

最短交付顺序：审阅本候选及本地状态分类 → 确认供应商强制计费上界/部署边界与合法
自举路线 → 单独授权新身份 Qualification 和工具链正式独立双审 → exact-head CI/Docker
→ Owner 决定工具链交付 → #1946 正式审核 → #1941 版本整合和审核。不得先改两旧 PR。
