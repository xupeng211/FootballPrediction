# GitHub Issues 双向同步工具

`sync_issues.py` 是一个功能强大的 GitHub Issues 双向同步工具，支持本地 YAML 文件与 GitHub Issues 之间的完整同步。

## 🌟 主要功能

- **Pull**: 从 GitHub 拉取所有 Issues 到本地 `issues.yaml` 文件
- **Push**: 将本地 `issues.yaml` 文件推送到 GitHub Issues
- **Sync**: 双向同步（先 Pull 再 Push），保持数据一致性

## 📦 依赖安装

```bash
# 激活虚拟环境
source .venv/bin/activate

# 安装依赖
pip install PyGithub pyyaml
```

## ⚙️ 环境配置

设置以下环境变量：

```bash
# GitHub Personal Access Token (必需)
export GITHUB_TOKEN="ghp_xxxxxxxxxxxxxxxxxxxx"

# GitHub 仓库路径 (必需，格式: owner/repo)
export GITHUB_REPO="your-username/your-repo-name"
```

### 获取 GitHub Token

1. 访问 [GitHub Settings > Personal Access Tokens](https://github.com/settings/tokens)
2. 点击 "Generate new token (classic)"
3. 选择权限：`repo` (完整仓库访问权限)
4. 复制生成的 token

## 📄 本地文件格式

本地 `issues.yaml` 文件采用简洁的列表格式：

```yaml
- id: 123                              # GitHub Issue ID (新建时为 null)
  title: "示例标题"                     # Issue 标题
  body: |                              # Issue 内容 (支持多行)
    详细描述内容
    支持 Markdown 格式
  state: "open"                        # 状态: open 或 closed
  labels: ["bug", "enhancement"]       # 标签列表

- id: null                             # 新建 Issue (无 ID)
  title: "新功能需求"
  body: "功能描述..."
  state: "open"
  labels: ["feature"]
```

## 🚀 使用方法

### 1. 从 GitHub 拉取到本地

```bash
python scripts/sync_issues.py pull
```

**执行效果：**
- 获取 GitHub 仓库中的所有 Issues (包括 open 和 closed)
- 覆盖本地 `issues.yaml` 文件
- 保持与远程完全一致

### 2. 推送本地到 GitHub

```bash
python scripts/sync_issues.py push
```

**执行效果：**
- 本地新增 Issues (id 为 null) → 在 GitHub 创建新 Issue
- 本地已有 Issues → 检查差异并更新 GitHub
- 更新本地文件，为新创建的 Issues 添加 ID

### 3. 双向同步

```bash
python scripts/sync_issues.py sync
```

**执行效果：**
1. 先执行 Pull 操作，获取最新的远程数据
2. 再执行 Push 操作，推送本地修改
3. 确保本地和远程完全同步

## 💡 实际使用场景

### 场景1：团队协作管理
```bash
# 1. 从 GitHub 拉取最新 Issues
python scripts/sync_issues.py pull

# 2. 本地编辑 issues.yaml 文件，添加新需求

# 3. 推送到 GitHub
python scripts/sync_issues.py push
```

### 场景2：批量管理 Issues
```bash
# 使用编辑器批量修改 issues.yaml
vim issues.yaml

# 一键同步所有修改
python scripts/sync_issues.py sync
```

### 场景3：备份和迁移
```bash
# 备份当前仓库的所有 Issues
python scripts/sync_issues.py pull

# 切换到新仓库
export GITHUB_REPO="new-owner/new-repo"

# 迁移 Issues 到新仓库
python scripts/sync_issues.py push
```

## 🔧 与 Makefile 集成

脚本已集成到项目 Makefile 中：

```bash
# 使用 Makefile 命令
make sync-issues
```

等价于：
```bash
python scripts/sync_issues.py sync
```

## ⚠️ 注意事项

1. **权限要求**: GitHub Token 需要 `repo` 权限
2. **数据安全**: 操作前建议备份重要数据
3. **冲突处理**: 双向同步时，以 GitHub 版本为准
4. **网络连接**: 需要稳定的网络连接访问 GitHub API
5. **API 限制**: 遵守 GitHub API 速率限制

## 🐛 故障排除

### 问题1：环境变量未设置
```
❌ 缺少环境变量: GITHUB_TOKEN
```
**解决方案**: 检查并设置正确的环境变量

### 问题2：仓库路径格式错误
```
❌ 仓库路径格式错误: invalid-format
```
**解决方案**: 使用正确格式 `owner/repo`

### 问题3：权限不足
```
❌ 403 Forbidden
```
**解决方案**: 检查 GitHub Token 权限，确保包含 `repo` 权限

### 问题4：网络连接问题
```
❌ 获取远程 Issues 失败: Connection timeout
```
**解决方案**: 检查网络连接，必要时使用代理

## 📊 输出示例

```
🚀 GitHub Issues 同步工具启动
📋 执行操作: sync
📁 本地文件: issues.yaml
🔗 连接到仓库: microsoft/vscode
🔄 开始双向同步...
⬇️  第一步: 从 GitHub 拉取最新数据...
🔍 成功获取 45 个远程 Issues
💾 成功保存 45 个 Issues 到 issues.yaml
⬆️  第二步: 推送本地修改到 GitHub...
📂 成功加载 45 个本地 Issues
✅ 成功创建新 Issue #46: 新功能需求
🔄 成功更新 Issue #23: 修复的bug
📤 完成推送，处理了 45 个 Issues
💾 成功保存 45 个 Issues 到 issues.yaml
✅ 双向同步完成
```

## 🎯 最佳实践

1. **定期同步**: 建议每日运行一次 `sync` 操作
2. **版本控制**: 将 `issues.yaml` 加入 Git 版本控制
3. **团队协作**: 团队成员使用相同的同步流程
4. **备份策略**: 重要操作前创建备份
5. **分批处理**: 大量 Issues 时分批同步，避免API限制

---

**作者**: DevOps Engineer
**版本**: 1.0.0
**更新**: 2024年9月
