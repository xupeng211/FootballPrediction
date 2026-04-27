# FootballPrediction 贡献与发布铁律

本文档定义本仓库所有开发者和 AI 助手必须遵守的远程发布规范。目标是让真正的合并门禁发生在远程代码仓库和 CI/CD 平台，而不是本地工作站。

## 远程发布铁律

1. **绝对禁止本地合并到 `main`**
   - 任何开发者、运维人员、自动化脚本、AI 助手，永远不得在本地执行 `git merge`、`git rebase`、`git cherry-pick` 等操作把功能代码直接写入 `main`。
   - 本地 `main` 只允许用于同步远程状态：`git fetch origin && git checkout main && git pull --ff-only origin main`。
   - 禁止使用 `--no-verify` 绕过本地 hook 后推送未经远程 PR 审核的主干修改。

2. **强制远程 PR 流程**
   - 所有功能、修复、脚本、模型、配置和文档变更都必须先在工作分支完成。
   - 分支命名应清晰表达目的，例如：`feat/xxx`、`fix/xxx`、`docs/xxx`、`chore/xxx`。
   - 开发完成后只能推送工作分支：

     ```bash
     git push origin feat/your-change
     ```

   - 随后必须在 GitHub/GitLab 上创建 Pull Request，目标分支为 `main`。

3. **远程门禁验证**
   - PR 必须通过远程 CI 平台的全量门禁，包括但不限于 lint、unit tests、integration tests、Python checks、构建检查和安全扫描。
   - 本地测试只能作为预检，不能替代远程 CI。
   - CI 未全绿时，禁止合并，禁止要求人工绕过，禁止把失败结果描述为通过。

4. **Code Review 与云端合并**
   - PR 必须经过 Boss 或指定代码负责人 Review。
   - Review 未批准前，禁止合并。
   - 合并动作只能在远程平台 UI 或受保护分支规则允许的远程合并流程中完成。
   - 合并完成后，本地开发者只允许通过 `git pull --ff-only origin main` 同步最新主干。

## AI 助手额外约束

- AI 助手必须先确认当前分支；如果在 `main`，不得进行写操作，应先切到工作分支。
- AI 助手不得擅自本地合并 `main`，不得擅自直推 `main`。
- AI 助手完成修改后，应提交到工作分支并推动创建 PR，而不是在本地完成主干合并。
- 如果用户要求本地合并或直推 `main`，AI 助手必须明确指出这违反本文件，并建议改走远程 PR 流程。

## 标准发布路径

```bash
git fetch origin
git checkout -b feat/your-change origin/main

# 在工作分支内修改、验证、提交
git add <files>
git commit -m "feat(scope): describe change"

# 推送工作分支并创建远程 PR
git push origin feat/your-change
```

PR 创建后，等待远程 CI 全绿和 Boss Review 批准，再由云端合并到 `main`。

