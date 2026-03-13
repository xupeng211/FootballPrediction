# CLAUDE_JS_TOOLS.md

## 🌐 JavaScript 运维工具完整参考

本文档提供 FootballPrediction 项目中 JavaScript 运维工具的完整参考指南。

---

## 📑 快速导航

### 按版本系列查找

| 版本系列 | 组件范围 | 当前版本 |
|----------|----------|----------|
| **V48/V49.x** | JavaScript 任务调度与时间同步 | V49.000 |
| **V69.x** | Pipeline 编排器 | V69.000 |
| **V84/V85.x** | JavaScript 诊断和视觉提取 | V85.000 |
| **V86/V87.x** | Master Pipeline | V87.203 |
| **V132-V160.x** | QuantHarvester 系列 | V160.000 |

---

## 🔧 环境准备

### Node.js 环境验证

JavaScript 运维工具系列需要 Node.js 18+ 环境：

```bash
# 验证 Node.js 版本（需要 18+）
node --version
# 输出示例: v18.17.0 或更高

# 验证 npm 版本
npm --version
# 输出示例: 9.6.7 或更高

# 验证 Playwright 安装
npx playwright --version
# 输出示例: Version 1.49.0 或更高

# 如果 Playwright 未安装，运行以下命令安装
cd scripts/ops
npm install

# 安装 Playwright 浏览器
npx playwright install chromium
```

### 环境故障排除

| 问题 | 解决方案 |
|------|----------|
| `node: command not found` | 安装 Node.js 18+：`sudo apt install nodejs npm` (Ubuntu) |
| `Cannot find module 'playwright'` | 运行 `npm install` 在 `scripts/ops/` 目录 |
| `Executable doesn't exist` | 运行 `npx playwright install chromium` |
| 权限错误 | 避免使用 `sudo`，改用 `npx` 运行命令 |

---

## 📦 Jest 测试框架

### 运行 Jest 测试

```bash
# 进入 ops 目录
cd scripts/ops

# 运行 Jest 测试 (V87.203)
npm test                       # 运行所有测试
npm run test:watch             # 监视模式
npm run test:coverage          # 生成覆盖率报告
npm run test:verbose           # 详细输出

# 运行特定测试文件
npx jest tests/interaction_v52.test.js
npx jest tests/orchestrator.test.js

# 安装依赖 (首次运行)
npm install
```

---

## 🔄 V48/V49 JavaScript 运维工具系列

### V49.000 Full-Spectrum Temporal Sync Engine - 全谱时间同步引擎

**说明**: V49.000 是基于 Node.js + Playwright 的时间同步引擎，实现全量三维时间序列提取（Home/Draw/Away）

**核心特性**:

- ✅ **全量三维时间序列**: Home/Draw/Away 完整赔率变化
- ✅ **返还率计算**: 自动计算 Payout 验证数据质量
- ✅ **DOM List Mapping**: 废弃正则表达式，使用稳定 DOM 锚点
- ✅ **人类行为模拟**: 随机延迟 + 智能重试
- ✅ **批量事务存储**: PostgreSQL UPSERT 优化

**核心架构**:

```
scripts/ops/
├── temporal_sync_engine_v49.js     # 主引擎 (协调器)
└── modules/
    ├── parser_v49.js                # V49.000 解析器 (DOM List Mapping)
    ├── interaction.js               # V43.200 交互模块 (悬停/重试)
    ├── storage.js                   # V43.200 存储模块 (连接池/事务)
    └── logger.js                    # 结构化日志
```

**使用方式**:

```bash
# 1. 单场比赛时间序列提取
node scripts/ops/temporal_sync_engine_v49.js "<TARGET_URL>" "<SOURCE_ID>"

# 2. 批量自动化收割 (配合 V48.000)
bash scripts/ops/v48_000_auto_task_pump.sh
```

### V48.100 URL Reconnaissance - URL 侦察

**说明**: V48.100 是自动化寻址脚本，通过 OddsPortal 联赛页面查找缺失的比赛 URL

**核心特性**:

- ✅ **智能 URL 搜索**: 通过队名查找比赛链接
- ✅ **数据库自动更新**: 找到 URL 后自动更新 `entities_mapping` 表
- ✅ **批量处理**: 支持多场比赛批量寻址

**使用方式**:

```bash
node scripts/ops/v48_100_url_reconnaissance.js
```

### V48.000 The Task Pump - 自动化任务泵

**说明**: V48.000 是 Bash 自动化任务调度脚本，实现自动寻标、串行收割和故障隔离

**核心特性**:

- ✅ **自动寻标**: 查询 `entities_mapping` 表找出待收割记录
- ✅ **串行收割**: 逐场执行时间同步引擎（3 秒人类延迟）
- ✅ **故障隔离**: 单场失败不影响整体执行
- ✅ **最终审计**: 自动生成收割报告

**使用方式**:

```bash
bash scripts/ops/v48_000_auto_task_pump.sh
```

### V43.200 Modules - 核心模块

#### Interaction Module (交互模块)

- **Smart Hover**: 指数退避重试机制
- **Timeout Degradation**: 优雅降级（失败跳过）
- **Error Recovery**: 结构化错误日志

#### Storage Module (存储模块)

- **Connection Pool**: PgBouncer 兼容连接池
- **Transaction Management**: BEGIN/COMMIT/ROLLBACK
- **Batch Operations**: 批量 UPSERT 冲突处理

---

## 🔄 V69/V70 Pipeline 编排系列

### V69.000 Pipeline Orchestrator - The Master Switch

**说明**: V69.000 是全链路自动化状态流转系统，实现从数据采集到特征提取的完整自动化

**核心特性**:

- ✅ **全链路状态流转**: DISCOVERED → ENRICHED → MAPPED → HARVESTED
- ✅ **自动化触发器**: L2 Enrichment、Bridge、Odds Harvest
- ✅ **批次处理**: 50 matches (L2) / 100 matches (Bridge) / 20 matches (Odds)
- ✅ **容错机制**: FAILED 状态 + 人工干预重试

**数据流状态图**:

```
┌─────────────────────────────────────────────────────────────────┐
│  INPUT: match_search_queue (Source_F)                           │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  STATE: DISCOVERED (初始状态)                                   │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  Step A: L2 Enrichment Trigger (v69_010_l2_trigger.py)         │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  STATE: ENRICHED (L2 数据已采集)                                │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  Step B: Bridge Trigger (v69_020_bridge_trigger.js)            │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  STATE: MAPPED (oddsportal_hash 已获取)                         │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  Step C: Odds Harvest Trigger (V66.000)                        │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  STATE: HARVESTED (全链路数据流完成)                            │
└─────────────────────────────────────────────────────────────────┘
```

### V70.200 Data Sentinel - 质量门禁

**说明**: V70.200 是数据质量门禁系统，提供完整性扫描和质量检查

**核心特性**:

- ✅ **Completeness Scan**: 数据完整性扫描
- ✅ **Quality Check**: 质量评分计算
- ✅ **Throughput Tracker**: 采集吞吐量监控

**使用方式**:

```bash
# 启动 V70.200 数据哨兵
node src/ops/v70_200_data_sentinel.js
```

---

## 🎨 V84/V85 JavaScript 视觉提取系列

### V85.000 Visual-First Extraction - 视觉优先提取

**说明**: V85.000 将原有的 API 拦截方案替换为"视觉定位 + 悬停取证"方案，实现更稳定的赔率数据提取。

**核心特性**:

- ✅ **视觉定位优先**: 使用 Logo-based detection 替代不稳定 ID
- ✅ **悬停取证**: 通过悬停操作触发赔率变化并捕获数据
- ✅ **提供商映射**: 支持 Pinnacle、bet365、Bwin、William Hill、1xBet
- ✅ **优雅降级**: 视觉提取失败时自动回退到 UI hover 方式

**核心架构**:

```
scripts/ops/
├── temporal_sync_engine_v49.js     # 主引擎 (V85.000 集成)
└── modules/
    ├── parser_v51.js                # V51.000 解析器 (视觉取证数据解析)
    ├── interaction_v51.js           # V51.000 交互模块 (视觉定位 + 悬停)
    ├── interaction.js               # V43.200 交互模块 (备用)
    ├── storage.js                   # V43.200 存储模块
    └── logger.js                    # 结构化日志
```

**使用方式**:

```bash
# 单场比赛时间序列提取（V85.000 模式）
node scripts/ops/temporal_sync_engine_v49.js "<TARGET_URL>" "<SOURCE_ID>"

# 预期输出:
# [V85.000] Visual extraction SUCCESS - 2 providers captured
```

### V84.x 系列诊断和测试工具

V84.x 系列提供完整的诊断、测试和取证工具集：

| 脚本 | 版本 | 功能 | 状态 |
|------|------|------|------|
| `v84_500_canary_test.py` | V84.500 | 金丝雀测试 - 小规模验证 | ✅ 可用 |
| `v84_600_diagnostic.js` | V84.600 | 综合诊断工具 | ✅ 可用 |
| `v84_710_hover_diagnostic.js` | V84.710 | 悬停功能诊断 | ✅ 可用 |
| `v84_800_api_strike.py` | V84.800 | API 突击测试 | ✅ 可用 |
| `v84_900_state_forensic.js` | V84.900 | 状态取证分析 | ✅ 可用 |
| `v84_910_deep_extractor.js` | V84.910 | 深度数据提取 | ✅ 可用 |
| `v85_500_visual_strike_test.js` | V85.500 | 视觉定位测试 | ✅ 可用 |

**使用方式**:

```bash
# V84.500 金丝雀测试（小规模验证）
python scripts/ops/v84_500_canary_test.py --limit 5

# V84.600 综合诊断
node scripts/ops/v84_600_diagnostic.js

# V84.710 悬停功能诊断
node scripts/ops/v84_710_hover_diagnostic.js

# V84.800 API 突击测试
python scripts/ops/v84_800_api_strike.py --target "<URL>"

# V84.900 状态取证分析
node scripts/ops/v84_900_state_forensic.js --match-id "<MATCH_ID>"

# V85.500 视觉定位测试
python scripts/ops/v85_500_visual_strike_test.js
```

---

## 🚀 V86/V87 Master Pipeline Series

### V87.510 Component Sync Verification - E2E 验证脚本

**说明**: V87.510 是独立的 E2E 验证脚本，用于验证复杂 SPA 组件状态同步与数据持久化

**核心特性**:

- ✅ **环境隔离**: 单 Headless 实例，锁定端口 7891
- ✅ **状态捕获**: 监测浮层组件 opacity/visibility 变化
- ✅ **持久化对账**: 模拟数据库 upsert 并查询记录总数
- ✅ **CircuitBreaker**: 连续 2 次无响应自动降级 (DEGRADED)
- ✅ **Full-round 计时**: 记录交互到数据库响应的完整耗时

**使用方式**:

```bash
# 运行验证脚本
node scripts/ops/verify_component_sync.js

# 自定义目标 URL
TARGET_URL_1="https://example.com/page1" TARGET_URL_2="https://example.com/page2" node scripts/ops/verify_component_sync.js

# 自定义数据库配置
DB_HOST=172.25.16.1 DB_NAME=football_db node scripts/ops/verify_component_sync.js
```

### V87.600 Component Sync Verification - 数据库约束修复

**说明**: V87.600 是 V87.510 的增强版本，修复了数据库约束和解析器对齐问题

**核心修复**:

- ✅ **数据库约束修复**: 创建 `v87_600_unique_metric_record` 唯一约束支持 UPSERT
- ✅ **延迟验货**: `validateContentIntegrity()` - 检测 border/odd 子元素，防止空壳弹窗
- ✅ **解析器对齐**: 支持 V87.500 DOM 结构 (`div.border-black-borders`)
- ✅ **强制要求 N > 0**: `fieldCount > 0` 才算验证成功

**使用方式**:

```bash
# 运行验证脚本
node scripts/ops/verify_component_sync.js

# 应用数据库约束修复
docker-compose exec -T db psql -U football_user -d football_db -f scripts/sql/v87_600_constraint_fix.sql
```

---

## 🌐 V132-V160 JavaScript 工具系列 - 模块化重构与取证分析

### V132.000 Forensic Analyzer - 取证分析工具

**说明**: V132.000 是深度取证分析工具，用于调查空收割结果的根本原因

**核心特性**:

- ✅ **V132.1 显式分页循环捕获**: 强制跳转 URL + 深度滚动触发
- ✅ **V132.2 全赛季数据脱水**: 解密所有分页并汇总到全局列表
- ✅ **V132.3 高精度原子对账**: 标准规范化 + Fuzzy Matching (80% 阈值)
- ✅ **V132.4 巡航大盘**: 实时统计和匹配率显示
- ✅ **截图和 HTML 保存**: 完整的取证证据链

**使用方式**:

```bash
node scripts/ops/v132_000_forensic_analyzer.js
```

### V134.000 Debug Runner - 调试运行器

**使用方式**:

```bash
# 调试运行器
node scripts/ops/v134_000_debug_runner.js

# Modal 诊断
node scripts/ops/v134_001_modal_diagnostic.js
```

### V135.000 Canary Validation - 金丝雀验证

**使用方式**:

```bash
node scripts/ops/v135_000_canary_validation.js
```

### V136.000 Precision Canary - 精密金丝雀

**使用方式**:

```bash
# 精密金丝雀
node scripts/ops/v136_000_precision_canary.js

# 诊断工具
node scripts/ops/v136_001_diagnostic.js
```

### V138.000 Modular Strike - 模块化打击

**说明**: V138.000 引入模块化架构，将 QuantHarvester 重构为独立模块

**核心特性**:

- ✅ **Golden Zone**: 2024-2026 高收益比赛过滤
- ✅ **代理轮换**: 支持多代理轮换
- ✅ **模块化设计**: Targeting, Precision & Golden Zone

**使用方式**:

```bash
node src/engines/QuantHarvester.js
```

### V139.000 Total Offensive - 全面进攻

**使用方式**:

```bash
node scripts/ops/v139_000_total_offensive.js
```

### V140.000 Data Purity Calibration - 数据纯度校准

**说明**: V140.000 是数据纯度校准工具，确保 UTC 时间强制执行和年份检测

**核心特性**:

- ✅ **UTC 强制执行**: 统一时间标准
- ✅ **年份检测**: 自动检测和修正年份
- ✅ **数据纯度验证**: 确保数据质量

**使用方式**:

```bash
node scripts/ops/v140_000_purity_verification.js
```

### V141.000 Slender Commander - 模块化重构

**说明**: V141.000 是 QuantHarvester 的模块化重构版本，从 1608 行精简到 679 行

**核心特性**:

- ✅ **TelemetryService 提取**: 遥测服务独立模块
- ✅ **SurgicalInteraction 提取**: 精确交互服务
- ✅ **SignalRadar 提取**: 信号雷达服务
- ✅ **模块化架构**: 清晰的职责分离

**核心架构**:

```
src/engines/
├── QuantHarvester.js           # V141.000 主收割机 (精简版)
├── services/
│   ├── TelemetryService      # 遥测服务
│   ├── SurgicalInteraction   # 精确交互
│   └── SignalRadar           # 信号雷达
└── parsers/
    └── TrajectoryParser     # 轨迹解析器
```

### V142.000 Final Canary - 最终金丝雀

**使用方式**:

```bash
node scripts/ops/v142_000_final_canary.js
```

### V143.000 Proxy Auditor - 代理健康审计

**使用方式**:

```bash
node scripts/ops/v143_proxy_auditor.js
```

### V144.000 Final Backfill - 最终回填

**使用方式**:

```bash
node scripts/ops/v144_000_final_backfill.js
```

### V145.000 Quick Strike - 快速打击

**使用方式**:

```bash
node scripts/ops/v145_000_quick_strike.js
```

### V146.000 React Adaptation Series - React 适配系列

**说明**: V146.000-V146.007 是 React SPA 适配系列，针对 OddsPortal 的 React 架构优化

**核心特性**:

- ✅ **React SPA 索引配置**: `AXIS_INDEX_OFFSETS`, `CELLS_PER_ROW`
- ✅ **Modal 检测**: Modal 弹窗检测和数据提取
- ✅ **DOM 监控**: DOM 变化监控
- ✅ **Hover 差异**: 悬停操作差异分析

**使用方式**:

```bash
# React 适配
node scripts/ops/v146_000_react_adaptation.js

# Modal 诊断
node scripts/ops/v146_001_modal_diagnostic.js

# Modal 查找器
node scripts/ops/v146_002_modal_finder.js

# 目标捕获
node scripts/ops/v146_003_targeted_capture.js

# DOM 监控
node scripts/ops/v146_004_dom_monitor.js

# Hover 差异
node scripts/ops/v146_005_hover_diff.js

# 内容变化
node scripts/ops/v146_006_content_changes.js

# 附近监控
node scripts/ops/v146_007_nearby_monitor.js
```

### V148.000 Modal Remapping - Modal 重新映射

**使用方式**:

```bash
node scripts/ops/v148_000_modal_remapping.js
```

### V149.000 Diagnostic - 诊断工具

**使用方式**:

```bash
node scripts/ops/v149_000_diagnostic.js
```

### V150.000 Depth Patch - 深度补丁系列

**说明**: V150.000 是深度补丁，解决完整轨迹等待问题

**核心特性**:

- ✅ **V150.004**: 修复 whitelistedProviders 空检查
- ✅ **V150.003**: 修复 modal HTML 捕获选择器
- ✅ **完整轨迹等待**: 深度渲染等待

**使用方式**:

```bash
# 金丝雀测试
node scripts/ops/v150_001_canary_test.js

# 顺序收割
node scripts/ops/v150_005_sequential_harvest.js
```

### V151.000 Patch Verification - 补丁验证

**使用方式**:

```bash
node scripts/ops/v151_000_patch_verification.js
```

### V152.000 Canary Test - 金丝雀测试

**使用方式**:

```bash
node scripts/ops/v152_000_canary_test.js
```

### V153.000 Full Power Audit - 全力审计

**使用方式**:

```bash
node scripts/ops/v153_000_full_power_audit.js
```

### V155.000 Total Offensive V151 - 全面进攻 V151

**使用方式**:

```bash
node scripts/ops/v155_000_total_offensive_v151.js
```

### V156.000 Verification Test - 验证测试

**使用方式**:

```bash
node scripts/ops/v156_000_verification_test.js
```

### V157.100 Canary Test & Full Sync - 金丝雀与全量同步

**使用方式**:

```bash
# 金丝雀测试
node scripts/ops/v157_100_canary_test.js

# 全量同步
node scripts/ops/v157_100_full_sync.js
```

### V158.000 Stealth Bypass Series - 潜行绕过取证系列

**说明**: V158.000-V158.002 是潜行绕过取证系列，提供深度取证分析

**核心特性**:

- ✅ **V158.000**: 金丝雀测试
- ✅ **V158.000**: 金丝雀验证
- ✅ **V158.000**: 取证调查
- ✅ **V158.001**: DOM 取证
- ✅ **V158.001a**: 增强取证
- ✅ **V158.002**: 潜行绕过

**使用方式**:

```bash
# 金丝雀测试
node scripts/ops/v158_000_canary_test.js

# 金丝雀验证
node scripts/ops/v158_000_canary_validation.js

# 取证调查
node scripts/ops/v158_000_forensic_investigation.js

# DOM 取证
node scripts/ops/v158_001_dom_forensic.js

# 增强取证
node scripts/ops/v158_001a_enhanced_forensic.js

# 潜行绕过
node scripts/ops/v158_002_stealth_bypass.js
```

### V159.000 Canary Validation - 金丝雀验证

**使用方式**:

```bash
node scripts/ops/v159_000_canary_validation.js
node scripts/ops/v159_000_modal_text_forensics.js
```

### V160.000 Identity Bridge - 身份桥接 (Row-to-Shop Recognition)

**说明**: V160.000 是最新的 Identity Bridge 版本，修复了"面部识别"问题

**V160.000 核心特性**:

- ✅ **Row-to-Shop Recognition**: 从父行提取提供商名称
- ✅ **Enhanced Parent Row Selectors**: React SPA 结构父行选择器
- ✅ **Multi-level Fallback**: 多级回退提供商名称检测
- ✅ **7 Core Providers**: Entity_B365, Entity_P, Entity_WH, Entity_BWIN, Entity_1XBT, Entity_UH, Entity_LADB
- ✅ **V141.000 模块化重构**: 提取 TelemetryService, SurgicalInteraction, SignalRadar

**核心架构**:

```
src/engines/
├── QuantHarvester.js           # V160.000 主收割机
├── config/
│   └── ReactIndexConfig       # React SPA 索引配置
├── parsers/
│   └── TrajectoryParser       # 轨迹解析器
├── selectors/
│   └── OddsPortalSelectors    # OddsPortal 选择器
└── services/
    ├── TelemetryService       # 遥测服务
    ├── SurgicalInteraction    # 精确交互
    └── SignalRadar            # 信号雷达
```

**使用方式**:

```bash
# 运行 QuantHarvester (V160.000)
node src/engines/QuantHarvester.js

# 查看巡航大盘
# ╔═══════════════════════════════════════════════════════════╗
# ║  V160.000 巡航大盘                                           ║
# ║  联赛: Premier League                                        ║
# ║  理论总数: 380                                               ║
# ║  实际提取: 380                                               ║
# ║  状态:     ✅ SUCCESS                                        ║
# ╚═══════════════════════════════════════════════════════════╝
```

**V160.000 Identity Bridge 核心改进**:

```javascript
// 修复 "面部识别" 问题 - 从父行提取提供商名称
const MARKET_VENUE_WHITELIST = {
    PINNACLE: {
        id: 'Entity_P',
        name: 'Pinnacle',
        priority: 1,
        keywords: ['pinnacle', 'pinny', 'pinn', '平博', 'pin', 'pina']
    },
    BET365: {
        id: 'Entity_B365',
        name: 'bet365',
        priority: 2,
        keywords: ['bet365', 'b365', '365', 'bet 365', '365bet']
    },
    // ... 其他 5 个提供商
};
```

---

## 📊 核心模块对比

### JavaScript 运维工具版本对比

| 版本 | 核心功能 | 主要用途 | 状态 |
|------|----------|----------|------|
| **V49.000** | 时间同步引擎 | 全量三维时间序列提取 | ✅ 生产 |
| **V69.000** | Pipeline 编排 | 全链路自动化状态流转 | ✅ 生产 |
| **V70.200** | 数据质量门禁 | 完整性扫描和质量检查 | ✅ 生产 |
| **V84.910** | 深度数据提取 | 诊断和测试工具集 | ✅ 可用 |
| **V85.000** | 视觉优先提取 | Logo-based detection | ✅ 生产 |
| **V87.203** | Master Pipeline | 全量收割 + Jest 测试 | ✅ 生产 |
| **V132.000** | 取证分析工具 | 全页码收割引擎 | ✅ 可用 |
| **V160.000** | Identity Bridge | Row-to-Shop Recognition | ✅ 生产 |

---

## 🔧 常见问题排除

### JavaScript 运维工具常见问题

| 问题 | 可能原因 | 解决方案 |
|------|----------|----------|
| `node: command not found` | Node.js 未安装 | 安装 Node.js 18+ |
| `Cannot find module 'playwright'` | 依赖未安装 | `cd scripts/ops && npm install` |
| `Executable doesn't exist` | 浏览器未安装 | `npx playwright install chromium` |
| `Timeout exceeded` | 页面加载超时 | 检查代理配置 |
| `Modal not found` | DOM 结构变化 | 运行诊断工具 |

### 调试命令

```bash
# 运行诊断工具
node scripts/ops/v84_600_diagnostic.js

# Modal 诊断
node scripts/ops/v134_001_modal_diagnostic.js

# 悬停功能诊断
node scripts/ops/v84_710_hover_diagnostic.js
```

---

## 📚 延伸阅读

### 相关文档

| 文档 | 内容 |
|------|------|
| [CLAUDE.md](../CLAUDE.md) | 项目主文档 |
| [docs/onboarding.md](onboarding.md) | 新开发者快速上手 |
| [docs/troubleshooting.md](troubleshooting.md) | 故障排除指南 |

---

**最后更新**: 2026-01-31
**文档版本**: V1.0
