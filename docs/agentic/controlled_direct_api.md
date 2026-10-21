# 受控 Direct API 离线执行核心

- lifecycle: permanent
- owner: engineering workflow governance
- status: OFFLINE_CANDIDATE / UNQUALIFIED / LIVE_DISABLED
- readers: 执行 Controller、审核工具链维护者

此候选不解除 #1946 / #1941 的正式审核阻断。工作流仍以 AGENTS.md 为准；本页不授予
费用、网络或审核资格。没有真实 HTTPS transport、API Key 加载或 live 开关。

## 实现和复用

`controlled_api_policy.py` 复用现有 canonical JSON / SHA 校验；Runner 复用
`independent_review_protocol.validate_result`。旧 Direct DeepSeek 冻结代码中的 SQLite
BEGIN IMMEDIATE、发送前 claim、不退款原则被局部复用，没有搬运旧资格或 Receipt。
Registry、正式 Runner、Policy、AI Gate 保持原样。

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
helper 不等于未来生产出口的不可绕过部署。真实 Provider 的出口/凭据隔离仍未实现。

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
