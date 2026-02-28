# V173 文档地图

> 最后更新: 2026-02-28

## 📁 核心文档 (必读)

| 文档 | 说明 |
|------|------|
| **CLAUDE.md** (根目录) | AI 助手操作指引 |
| **ARCHITECTURE.md** | 系统架构总览 |
| **QUICKSTART_GUIDE.md** | 5 分钟快速上手 |
| **OPERATIONS_MANUAL.md** | 运维手册 |

## 📁 发布记录

| 文档 | 说明 |
|------|------|
| **V173_DELIVERY_CHECKLIST.md** | V173 交付清单（网页渗透模式） |
| **V172_DELIVERY_CHECKLIST.md** | V172 交付清单 |
| **V171_DELIVERY_CERTIFICATE.md** | V171 交付证书 |

## 📁 核心运维组件 (严禁移除)

> ⚠️ 以下组件是系统运维的核心基础设施，严禁在后续清理中移除

| 组件 | 文件 | 功能 |
|------|------|------|
| **中央监控大屏** | `scripts/ops/monitor_dashboard.js` | 实时状态监控 (npm run watch) |
| **资产报告器** | `scripts/ops/asset_report.js` | 数据净值统计 (npm run report) |
| **收割器 Master** | `scripts/ops/harvest_fleet_master.js` | 装甲群收割调度 |
| **收割器 Worker** | `scripts/ops/harvest_worker.js` | 网页渗透模式执行 |
| **配置中心** | `config/factory_config.js` | 工厂级参数归口 |

## 📁 快捷命令

```bash
npm run watch      # 启动中央监控大屏
npm run report     # 生成资产净值报告
npm run harvest    # 启动收割任务
```

## 📁 架构参考

| 文档 | 说明 |
|------|------|
| **ENGINE_ARCHITECTURE.md** | 引擎架构设计 |
| **FINGERPRINT_EXTRACTOR.md** | 指纹提取器说明 |
| **L1_INDEX_LAYER_SPEC.md** | L1 索引层规范 |

## 📁 操作指南

| 文档 | 说明 |
|------|------|
| **OPERATIONS_SOP.md** | 运维标准操作程序 |
| **README_FACTORY.md** | 数据工厂说明 |
| **README_PROD.md** | 生产环境说明 |
| **SYSTEM_STABILITY_guide.md** | 系统稳定性指南 |
| **troubleshooting.md** | 故障排除指南 |

## 📁 其他参考

| 文档 | 说明 |
|------|------|
| **API_REFERENCE.md** | API 参考文档 |
| **onboarding.md** | 新人入职指南 |
| **monitoring.md** | 监控配置说明 |
| **xgboost_optimization_guide.md** | XGBoost 优化指南 |
| **MCP_ARCHITECTURE.md** | MCP 架构说明 |

## 📁 历史文档

所有 V1-V170 时代的历史文档已移至 `_deprecated/legacy_docs_v1_v170/`

---

*本文档地图由 V173-SENTINEL 清理流程自动生成*
