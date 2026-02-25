# 废弃文件隔离区

**迁移日期**: 2026-02-25
**迁移分支**: feat/refactor-core-v2
**迁移原因**: [V171-Governance-03] 代码库清理与架构标准化

---

## 文件清单

### root/ (5个)
| 文件 | 原因 |
|------|------|
| `canary_stress_test.js` | 旧版压力测试，与现在架构不符 |
| `launch_pure_l3.js` | 废弃的 L3 启动器，包含硬编码数据库配置 |
| `ignite_full_harvest.js` | 废弃的收割启动器，已被新收割引擎取代 |
| `proxy_scrub.js` | 废弃的代理清理脚本，功能已集成到 NetworkShield |
| `test_network_shield.js` | 测试文件位置错误，应在 tests/ 目录 |

### scripts_ops/ (7个)
| 文件 | 原因 |
|------|------|
| `demo_telemetry.js` | 演示性质，仅用于展示遥测功能 |
| `odds_stealth_engine_debug.js` | 调试脚本，开发调试时使用 |
| `gen_proxies.js` | 代理生成器，功能已集成 |
| `force_deep_capture.js` | 临时修复脚本，用于修复特定问题 |
| `fix_parser.js` | 一次性解析器修复工具 |
| `test_helper.js` | 旧版测试辅助，已被新版本取代 |
| `test_helper_v43_100.js` | V43.100 版本测试辅助 |

### research/ (42个)
完整的 `scripts/ops/_research/deprecated/` 目录内容，包括：
- 各版本的实验性代码 (v39_*, v48_*, v64_*, v67_*, v68_*, v69_*, v71_*, v73_*, v77_*, v84_*, v85_*, v88_*)
- 诊断脚本和调查脚本
- DOM 检查和模拟测试
- 过时的生产脚本

### zombie_l1/ (4个) - V171-Governance-05 新增
| 文件 | 原因 |
|------|------|
| `test_l1_discovery.js` | 旧版 L1 测试，功能已合并到 v171_l1_api_fetch.js |
| `v171_l1_expand_pool.js` | 旧版比赛池扩充，已被全量快照取代 |
| `v86_turbo_harvest.js` | V86 版本收割器，已被 V171 架构取代 |
| `v86_master_harvest.js` | V86 版本主收割器，已被 V171 架构取代 |

---

## 保留期限

**这些文件将在 30 天后（2026-03-27）确认无问题后永久删除。**

如需恢复任何文件，请从本目录复制回原位置：
```bash
# 恢复示例
cp _deprecated/root/canary_stress_test.js ./
```

---

## 统计

- **总计**: 58 个文件
- **根目录**: 5 个
- **scripts/ops**: 7 个
- **research**: 42 个
- **zombie_l1**: 4 个 (V171-Governance-05 新增)
