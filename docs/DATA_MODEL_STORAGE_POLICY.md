# Data & Model Storage Policy

本仓库只保存可审查、可复现、体积稳定的工程资产。生产数据、训练数据、模型产物和运行缓存必须放在 Git 仓库外部，避免仓库膨胀和敏感信息泄露。

## Git 中允许保存

- 源代码、脚本入口和测试代码。
- 配置模板，例如 `.env.example`、`config/.env.example`。
- 文档、架构说明、运行手册和审计报告。
- 小型、脱敏、稳定的测试 fixtures，例如 `tests/fixtures/`。
- 小型 mock 数据，例如 `data/mock/`。

## Git 中禁止保存

- 生产采集数据、回填数据、原始 HTML、浏览器抓取产物。
- 大型 CSV、TSV、JSONL、Parquet、SQLite 或数据库 dump。
- 模型权重和训练产物，包括 `joblib`、`pkl`、`onnx`、`pt`、`pth`、`h5`、`ckpt`。
- 浏览器 session、cookie、用户 profile、代理凭据。
- 真实 token、password、SSH key、GitHub token、API key。
- 日志、coverage、`htmlcov/`、缓存、临时目录。
- 备份 bundle、压缩包、二进制插件、构建产物。

## 推荐存储位置

- 本地开发数据：`/mnt/data/football_prediction/` 或其他项目外部目录。
- 结构化业务数据：PostgreSQL。
- 模型产物：项目外部 artifact 目录、对象存储或 GitHub Release artifact。
- CI 报告：GitHub Actions artifacts。
- 监控数据：Docker volume 或外部监控存储。
- 临时浏览器 profile 和缓存：项目外部目录或 Docker volume。

## 开发规范

- 新增数据文件前，先确认该文件是否应该进入 Git。
- 大文件不得直接提交；如必须共享，使用 artifact、对象存储或外部数据目录。
- 真实 cookie、token、password、private key 不得提交。
- 只允许提交脱敏、小型、稳定的测试 fixtures 和 mock 数据。
- 如果某个样例文件必须进入 Git，需要说明用途、体积和脱敏状态。
- 清理已跟踪数据或模型文件时，优先使用独立 PR；历史清理必须提前备份并通知协作者。
