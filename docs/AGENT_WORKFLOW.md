# Agent Workflow — Detailed Reference

> 状态：current / permanent。`AGENTS.md` 是唯一 operational authority；本文件只解释其规则、示例和异常处理，不创建第二套 policy。

## 1. 设计边界

工作流只有四种 authority：

| Authority | 责任 | 不负责 |
| --- | --- | --- |
| TEST | 证明代码行为正确 | 决定是否合并 |
| CI | 在可重复环境执行验证 | 替代 review 或 owner |
| REVIEW | STRICT 任务判断语义、边界和失败场景 | 运行全部测试或决定合并 |
| OWNER | 接受风险并决定 merge | 伪造测试、review 或 HEAD 证据 |

脚本可以编排这些步骤，但不能成为第五种 correctness authority。Git/GitHub/Actions 是状态事实来源；Markdown 只描述规则，不保存 workflow state、SHA、review state 或 CI state。

## 2. 任务分类

NORMAL 适合局部、低风险变更。STRICT 适合 DB/schema/write、ingestion、identity/auth/security、生产 runtime、training/model activation、关键架构和高影响破坏性行为。无法安全分类时按 STRICT 处理，并在 PR `Risk` 说明原因。

NORMAL：

```text
branch/worktree → implementation → make verify-targeted → commit/push
→ PR → required CI → owner decision → squash/approved merge policy
→ main Production Gate exact merge SHA → DONE
```

STRICT：

```text
branch/worktree → base/head snapshot → implementation
→ make verify-strict → one exact-head independent adversarial review
→ fix findings and revalidate current HEAD → PR → required CI
→ owner decision → main Production Gate exact merge SHA → DONE
```

NORMAL 不默认运行本地 Codex review、DeepSeek、codex-loop、manifest/audit package 或 GitHub Codex Review。STRICT 只要求一个 primary independent reviewer；额外意见只能是 advisory，并且不能改变 owner 的 merge authority。

## 3. 验证 profile

WF02 目标是把公开入口收敛为：

```bash
make verify-targeted
make verify-pr
make verify-strict
```

profile 的边界：

- `verify-targeted`：受影响测试、必要 static check 和最小 targeted regression；快反馈，不宣称完整 CI。
- `verify-pr`：本地和 GitHub PR gate 尽可能调用同一 canonical implementation；required failure 必须返回非零。
- `verify-strict`：只用于 STRICT；包含与风险相关的完整测试、完整性、安全或 runtime smoke，不把昂贵检查默认施加给 NORMAL。

旧 `npm`/`make` 入口可以作为 alias 或 internal implementation，但不得各自维护另一套 test semantics。弃用入口在没有 caller inventory 前只标记，不直接删除。

## 4. PR 模板和内容

唯一默认模板是 `.github/pull_request_template.md`，正文五个部分：

```markdown
## Summary
## Scope
## Tests
## Risk
## Rollback
```

内容必须是实际事实：命令、exit code、覆盖范围、runtime 影响和回滚办法。普通 PR 不生成空 finding、manifest、snapshot 或 phase report。高风险路径需要的授权信息只在该 PR 的 `Risk` 之外按模板提示增加，不为 NORMAL 增加状态机式正文。

## 5. Review freshness

review 记录必须绑定完整 PR HEAD。有效性不依赖 reviewer 口头说 PASS，而依赖：

```text
reviewed_full_sha == current_pr_head_full_sha
```

source change、rebase、amend 或 force-push 后，旧 review 自动视为 stale；必须重新 review 或明确降级为 advisory。GitHub Codex Review 当前是可选 second opinion，不是 required check，也不等于 approval。

## 6. CI 和 merge freshness

当前 GitHub ruleset 观察到的 required checks 是：

```text
Environment / Proxy / Static / Unit Gate
Docker Build Validation
```

规则可能由 owner 在 GitHub 上改变；报告时以 ruleset API 和实际 run 为准。PR source change 必须产生验证新 HEAD 的 run，不能复用历史 green run。merge 后必须记录实际 merge SHA，并确认 main push Production Gate 验证同一完整 SHA；仅有 PR green 或“已 merged”不算 DONE。

## 7. `pr-ready` 的职责

WF03 目标是只暴露一个只读 preflight（命名可为 `make pr-ready`）。它可以检查 PR 存在、非 draft、当前 PR HEAD、required checks 的 SHA、工作区意外 dirty 和必要 metadata；它不重跑测试、不重跑 review、不生成 audit package、不修改 PR、不 merge、不清理 branch。

preflight 是 governance check，不是 TEST、CI 或 REVIEW。任何 wrapper 只能编排 canonical implementation，不能通过吞掉 exit code 或写 Markdown 状态来制造 PASS。

## 8. 异常处理

- Docker 不可用：报告环境 blocker，不绕过容器限制运行业务命令。
- required test 失败：保留非零 exit，修复或停止；不得把 advisory 命令命名为 `ci`/`verify`。
- PR HEAD 改变：重新计算 exact-head 状态并使旧 review/CI 结果失效。
- GitHub API 无权限：标记 `UNKNOWN`，不把缺失数据当作 green 或 approval。
- 文档与机器状态冲突：以 Git/GitHub/Actions 为准，修正文档时保留证据，不创建新的平行规则。
- 不能安全完成 runtime change：No-Go；不得用 report、manifest、test-only 或 phase metadata 伪装进展。

## 9. 证据格式

每个阶段至少记录 branch、base SHA、head SHA、changed files、命令和 exit code、GitHub PR/run、验证 SHA、remaining risks 和 deferred items。判断使用三种标签：

- `CONFIRMED`：机器输出、文件引用或 GitHub API 直接证明。
- `INFERRED`：由多个证据推断，但没有单一强制点。
- `UNKNOWN`：证据不足或权限不可用。

最终报告必须把 TEST、STATIC CHECK、REVIEW、CI、GOVERNANCE CHECK 分开，不能统称“验证”。

## 10. 变更与回滚

workflow 收敛按 WF01–WF06 分阶段完成。每阶段独立 branch/commit/PR，先通过本阶段 acceptance 再进入下一阶段；前四阶段不大规模重写 `scripts/devops/gatekeeper.sh`。任何阶段发现真实 caller、远端规则或生产风险与旧假设不符，应记录 `AUDIT_ASSUMPTION_CHANGED`，停止危险 cleanup，保留 UNKNOWN 项。
