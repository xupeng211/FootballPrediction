# V171 实验性代码归档

⚠️ **警告**: 本目录包含 V171 开发阶段的实验性脚本，**不建议在生产环境使用**。

## 归档原因

这些脚本存在以下问题，已不符合 V172 的工业级标准：

| 问题 | 文件 | 说明 |
|------|------|------|
| 默认密码 | v171_real_backfill_live.js | 包含硬编码的数据库密码 |
| 默认密码 | v171_xg_harvest.js | 包含硬编码的数据库密码 |
| 默认密码 | v171_stealth_harvest.js | 包含硬编码的数据库密码 |
| 硬编码路径 | incremental_factory.js | 使用 `/app/` 绝对路径 |
| 硬编码路径 | harvest_all_l2.js | 使用 `/app/` 绝对路径 |

## V172 替代方案

| V171 脚本 | V172 替代方案 |
|-----------|--------------|
| v171_real_backfill_live.js | `harvest_fleet_master.js` (无密码硬编码) |
| v171_xg_harvest.js | `harvest_worker.js` + `MatchDetailEngine.js` |
| v171_stealth_harvest.js | `MatchDetailEngine.js` (Stealth 2.0) |
| incremental_factory.js | 计划在 V173 重新设计 |
| harvest_all_l2.js | `harvest_fleet_master.js` |

## 如果必须使用

1. **不要**直接运行这些脚本
2. 如需参考，请将其复制到临时目录并手动修复硬编码问题
3. 使用 `.env` 文件注入数据库密码

## 归档日期

2026-02-27 (V172-GOLD 发布)
