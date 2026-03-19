# 更新日志 (Changelog)

所有重要的更改都将记录在此文件中。

---

## [V6.6] - 2026-03-20 - L2 Raw Storage Hardening

### 🏗️ L2 原始数据存储层硬化 (Raw Storage Hardening)

V6.6 版本实现了 L2 Harvesting Layer 的工业级硬化，确保"非标准数据无法进入 L2"。

#### 新增数据库约束 (8 道防线)

| 约束名 | 类型 | 作用 |
|--------|------|------|
| `match_id_format` | CHECK | 强制 `match_id` 必须符合 `'^\d+_\d{8}_\d+$'` 正则格式 |
| `raw_data_not_empty` | CHECK | 强制 `raw_data` 不能为 NULL 或空 JSONB |
| `collected_at_not_null` | CHECK | 强制 `collected_at` 采集时间不能为空 |

#### 新增字段

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `data_version` | VARCHAR(20) | 数据版本标记，固定值 `'V26.1'`，用于数据溯源 |
| `external_id` | VARCHAR(50) | 外部数据源原始 ID，便于追溯 |

#### 新增索引

| 索引名 | 类型 | 用途 |
|--------|------|------|
| `idx_raw_data_version_collected` | BTREE | 支持按版本和时间范围查询 |

#### 新增触发器

| 触发器名 | 触发时机 | 功能 |
|----------|----------|------|
| `trg_update_raw_data_timestamp` | BEFORE UPDATE | 自动更新 `collected_at` 时间戳 |

---

### 🧰 Normalizer 工具类解耦 (Shared Utility)

#### 新增文件

| 文件 | 功能 |
|------|------|
| `src/utils/Normalizer.js` | 共享标准化工具类，L1/L2/L3 全层复用 |

#### 核心方法

| 方法 | 功能 |
|------|------|
| `isValidMatchId(matchId)` | 验证 match_id 格式是否符合 `'^\d+_\d{8}_\d+$'` |
| `normalizeSeason(season)` | 将各种赛季格式统一转换为 `'YYYY/YYYY'` 标准格式 |
| `buildMatchId(leagueId, season, externalId)` | 构建标准化的 match_id |
| `normalizeTeamName(name)` | 标准化队名（统一大小写、去除特殊字符） |

#### 代码层预检机制

在 `Persistence.saveToDatabase()` 中引入双重预检：

```javascript
// 预检 1: match_id 格式
if (!Normalizer.isValidMatchId(matchId)) {
    throw new Error('[VALIDATION] match_id 格式非法: ${matchId}');
}

// 预检 2: raw_data 非空
if (!rawData || Object.keys(rawData).length === 0) {
    throw new Error('[VALIDATION] raw_data 不能为空: ${matchId}');
}
```

**优势**:
- 提供清晰的 `[VALIDATION]` 错误标记，便于日志筛选
- 在数据到达数据库前拦截，减少数据库错误日志
- 业务语义验证（如"raw_data 不能为空对象"）

---

### 🔄 双保险存储强化 (Dual Persistence)

#### 数据库 + 文件系统冗余

| 维度 | 数据库 (raw_match_data) | 文件系统 (data/matches/) |
|------|------------------------|-------------------------|
| **版本标记** | `data_version = 'V26.1'` | `data_version = 'V26.1'` |
| **格式** | JSONB | JSON |
| **失败处理** | 阻塞流程 | 记录错误，继续执行 |

#### 变更文件

| 文件 | 变更 |
|------|------|
| `src/infrastructure/harvesters/components/Persistence.js` | 重构 `saveToDatabase()` 和 `dualSave()`，引入 Normalizer 预检，强制 `data_version` |
| `src/infrastructure/harvesters/ProductionHarvester.js` | 集成 Normalizer，`saveData()` 方法添加预检逻辑 |

---

### 📊 100% 数据一致性对齐 (Full Alignment)

#### L1-L2 对齐验证

- **match_id 格式对齐**: L1 `matches` 表与 L2 `raw_match_data` 表使用完全相同的 match_id 格式
- **外键约束**: `raw_match_data.match_id` → `matches.match_id`，确保数据一致性
- **赛季标准化**: 所有赛季统一为 `'YYYY/YYYY'` 格式（如 `'2024/2025'`）

#### 单元测试覆盖

| 测试文件 | 测试数 | 说明 |
|----------|--------|------|
| `tests/unit/L2_Normalizer_Persistence.test.js` | 30 | Normalizer 边界测试 + Persistence 预检测试 |

**测试结果**: ✅ 30/30 全部通过

---

### 📚 文档与决策记录

#### 新增文档

| 文件 | 内容 |
|------|------|
| `src/infrastructure/harvesters/L2_HARVESTING_ENGINE.md` | L2 架构设计文档，包含数据流、硬化规则、版本控制策略 |
| `docs/adr/ADR-002-L2-Raw-Storage-Hardening.md` | 架构决策记录，详述硬化决策背景、方案对比、实施计划 |

---

## [V6.5] - 2026-03-19 - Data Consistency Hardening

### 🏗️ 数据库硬核加固 (Database Hardening)

V6.5 版本在 PostgreSQL 数据库层面建立了工业级数据一致性保障机制。

#### 新增约束 (Constraints)

| 约束名 | 类型 | 作用 |
|--------|------|------|
| `status_lowercase` | CHECK | 强制 `status` 字段必须全小写 (`status = LOWER(status)`) |
| `season_format` | CHECK | 强制 `season` 字段必须符合 `'YYYY/YYYY'` 正则格式 |

#### 新增触发器 (Trigger)

| 触发器名 | 触发时机 | 功能 |
|----------|----------|------|
| `trg_sync_is_finished` | BEFORE INSERT OR UPDATE | 自动同步 `is_finished` 字段与 `status` 字段 |

**触发器逻辑**:
```sql
NEW.is_finished := (NEW.status = 'finished');
```

#### 新增字段

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `is_finished` | BOOLEAN | 与 `status` 字段保持 100% 同步，数据库层自动维护 |

---

### 🔄 L1 引擎解析逻辑全量归一化 (Parser Normalization)

#### 新增方法

| 方法 | 文件 | 功能 |
|------|------|------|
| `normalizeSeason()` | `FixtureSeeder.js` | 将各种赛季格式统一转换为 `'YYYY/YYYY'` 标准格式 |
| `determineStatus()` (增强) | `FixtureSeeder.js` | 返回强制小写的状态值 |

#### 归一化规则

**赛季格式**:

| 输入 | 输出 | 说明 |
|------|------|------|
| `2023/2024` | `2023/2024` | 标准格式，直接通过 |
| `2324` | `2023/2024` | 4位简写，自动补全世纪 |
| `20232024` | `2023/2024` | 8位数字，自动分割 |
| `2023-2024` | `2023/2024` | 短横线分隔，自动替换 |
| `23/24` | ❌ Error | 非法格式，抛出异常 |

**状态值**:
- 所有状态值强制转换为小写: `'finished'`, `'scheduled'`, `'live'`, `'cancelled'`, `'postponed'`, `'awarded'`

---

### 🛡️ 双重防护架构 (Dual Protection)

```
┌─────────────────────────────────────────────────────────────┐
│ 第一层: 应用层防护 (Node.js)                                 │
│ - normalizeSeason() 强制格式转换                            │
│ - determineStatus() 强制小写输出                            │
│ - parseMatch() 计算 is_finished 布尔值                      │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│ 第二层: 数据库层防护 (PostgreSQL)                            │
│ - CHECK 约束拦截非法数据                                    │
│ - TRIGGER 自动修正不一致字段                                │
└─────────────────────────────────────────────────────────────┘
```

**目标实现**: "非标准数据进不来，标准数据改不掉" 的工业级鲁棒性。

---

### 📁 文件变更清单

```
M src/infrastructure/FixtureSeeder.js    # 核心归一化逻辑
M src/infrastructure/L1_DISCOVERY_ENGINE.md  # 文档更新
M CHANGELOG.md                           # 本文件
A tests/unit/FixtureSeeder.test.js       # 新增 V6.5 测试用例
A database/migrations/V6.5__hardened_matches_schema.sql  # 迁移脚本
```

---

## [V4.46.8] - 2026-03-11 - INDUSTRIAL Edition

### 🏭 架构整肃 (Architecture Consolidation)

**核心交付: 工业化全自动巡航系统**

完成架构整肃，实现工业化全自动巡航，技术债务清零。

### ✨ 新增模块 (New Modules)

| 模块 | 位置 | 功能 |
|------|------|------|
| **model_config** | `src/constants/model_config.py` | 模型配置常量唯一源 |
| **H2HEstimator** | `src/ml/feature_engine/h2h_estimator.py` | H2H 智能补位引擎 |
| **TitanModelLoader** | `src/ml/inference/titan_loader.py` | TITAN 模型加载器 |
| **prediction_repo** | `src/database/repositories/prediction_repo.py` | 预测数据仓储层 |
| **titan_cruise_control** | `scripts/ops/titan_cruise_control.py` | 全自动巡航控制器 |
| **show_today_summary** | `scripts/maintenance/show_today_summary.py` | 终端作战简报 |

### 🔧 架构改进 (Architecture Improvements)

1. **配置统一化**: 从 predict_pipeline.py 剥离模型配置常量至独立模块
2. **H2H 冷启动解决**: 基于 Elo 差值线性推演，消除 H2H 数据缺失阻塞
3. **模块职责分离**: 数据访问层与业务逻辑层解耦
4. **巡航自动化**: 无人值守运行，支持 cron 定时调度
5. **熔断保护**: 连续 3 次失败自动熔断，1 小时后重置

### 📁 文件变更清单

```
+ VERSION                              # 版本锚点
+ BUILD_DATE                           # 构建日期
+ src/constants/model_config.py        # 模型配置
+ src/ml/feature_engine/h2h_estimator.py
+ src/ml/inference/titan_loader.py
+ src/database/repositories/__init__.py
+ src/database/repositories/prediction_repo.py
+ scripts/ops/titan_cruise_control.py
+ scripts/maintenance/show_today_summary.py
M scripts/ops/predict_pipeline.py      # 重构，引用新模块
M scripts/ops/train_model.py           # 重构
M scripts/maintenance/check_system_health.py
M src/ml/feature_engine/__init__.py
M src/ml/inference/__init__.py
M src/utils/notifier.py
```

### 🧪 测试体系重构

- 测试目录标准化: `tests/unit/`, `tests/integration/`, `tests/integrity/`
- 历史归档: `tests/Z_LEGACY_ARCHIVE_PRE_V4.46.8/`
- pytest 配置: `pytest.ini` 排除归档目录

### 📊 最终状态

- 健康度: **100%**
- 技术债务: **清零**
- 巡航模式: **工业化全自动**

---

## [V4.46.4] - 2026-03-09 - HYPER-DRIVE Edition

### 🚀 架构重构 (Architecture Refactor)

**最核心变更: Worker 池化 + 浏览器只启动一次**

之前的架构中，每场比赛收割都会启动和关闭一个浏览器，导致约 50% 的时间浪费在初始化/清理上。

V4.46.4 彏底重构了这一模式：

- 15 个 Worker 在启动时预初始化
- 浏览器只启动一次
- 任务分发复用已初始化的 Worker
- 所有任务完成后统一销毁

### 📊 性能对比

| 指标 | V4.46.3 | V4.46.4 | 提升 |
|------|---------|---------|------|
| 浏览器启动次数 | 每场 1 次 | 全局 1 次 | **99% ↓** |
| Worker 初始化 | 每场 1 次 | 全局 15 次 | **99% ↓** |
| 单场平均耗时 | ~10s | ~3.5s | **65% ↓** |
| 吞吐量 | 0.08 场/秒 | ~0.3 场/秒 | **3.75x ↑** |

### ✨ 新增功能 (Features)

#### 1. Worker 池化架构 (`SwarmHarvester.js`)

- `_initializeWorkerPool()`: 预创建并初始化固定数量的 Worker
- `_pooledHarvest()`: 使用池化 Worker 执行收割，无需重复初始化
- `_cleanupWorkerPool()`: 统一销毁 Worker 池

#### 2. 意甲专项收割器 (`hyper_swarm_stealth.js`)

- 针对被 403 拦截的比赛
- 低并发 (3 Worker) + 长延迟 (5-10s)
- 成功收割 8 场难缠比赛

#### 3. 数据完整性卫士 (`integrity_guard.py`)

- 每日自动运行
- 对比 L1/L2/L3 三张表的记录数
- 自动列出缺失的 match_id
- 生成修复建议

#### 4. 运维手册 (`OPERATIONS_RUNBOOK.md`)

- 完整的故障-对策矩阵
- 4 大类故障的诊断流程
- 紧急恢复指南
- 日常运维检查清单

#### 5. Grafana Dashboard (`grafana_dashboard.json`)

- 实时吞吐量曲线
- 采集成功率饼图
- 代理池负载分布
- L1/L2/L3 对齐率

### 🔧 修复 (Fixes)

#### 1. 端口切换日志 bug

- 位置: `AbstractHarvester.js:497`
- 问题: `forceReassignPort()` 返回对象而非端口号，导致日志显示 `[object Object]`
- 修复: 使用 `newPort?.port || newPort` 正确显示端口号

#### 2. 移除无效的错峰延迟

- 位置: `SwarmHarvester.js:262-270`
- 问题: `_calculateStaggerDelay` 导致批次间产生不必要的延迟
- 修复: 在池化模式下，Worker 空闲立即处理下一条 MatchID

### 📁 文件变更清单

#### 新增文件

```
+ docs/OPERATIONS_RUNBOOK.md       # 运维手册
+ config/monitoring/grafana_dashboard.json  # Grafana 看板
+ scripts/ops/hyper_swarm_stealth.js  # 意甲专项收割器
+ scripts/maintenance/integrity_guard.py  # 数据完整性卫士
```

#### 修改文件

```
M src/infrastructure/harvesters/SwarmHarvester.js
  - 重构为 Worker 池化架构
  - 移除无效的错峰延迟

M src/infrastructure/harvesters/base/AbstractHarvester.js
  - 修复: 端口切换日志显示 bug

M scripts/ops/hyper_swarm.js
  - 更新为 V4.46.4 HYPER-DRIVE 配置

M README.md
  - 更新版本号至 V4.46.4
  - 添加新文档索引
```

### 📈 最终状态

```
┌───────────────────────────────────────────────────────────────┐
│  🎯 TITAN-V4.46.4 HYPER-DRIVE 终极状态                        │
├───────────────────────────────────────────────────────────────┤
│  L1 (matches)        │ 1900  ✅                              │
│  L2 (raw_match_data) │ 1900  ✅                              │
│  L3 (l3_features)    │ 1900  ✅                              │
├───────────────────────────────────────────────────────────────┤
│  数据完整率          │ 100%                                  │
└───────────────────────────────────────────────────────────────┘
```

---

## [V173.0.0] - 2026-02-28 - Sentinel Edition

### 🚀 重大突破 (Breaking Changes)

- **网页渗透模式 (Web Infiltration Mode)**: 绕过 FotMob API 层的 Turnstile 拦截，直接从网页 `__NEXT_DATA__` 提取数据
  - 新增 `_extractNextData()` 方法提取 Next.js 数据
  - 新增 `_transformNextDataToApiFormat()` 转换数据格式
  - 新增 `_simulateHumanBehavior()` 模拟真人行为（滚动、阅读延时）
  - 新增 `_checkCloudflareBlock()` 检测 Cloudflare 拦截页面

### 🛡️ 系统加固 (Security Hardening)

- **preFlightCleanup (自动清道夫)**: 启动前物理清空 Chrome/Chromium 僵尸进程
  - 清理残留的 `chrome-headless` 进程
  - 清理残留的 `harvest_fleet_master` 和 `harvest_worker` 进程
  - 确保每一轮收割都在"洁净室"环境下开始

- **熔断机制优化**: 提高熔断阈值至 10 次，避免过早触发
- **动态 UA 轮换**: 20 个主流 User-Agent 随机切换
- **随机视口尺寸**: 每次创建 Context 时随机选择视口

### 📊 运维升级 (Operations)

- **中央监控大屏 (Dashboard)**:
  - 新增 `npm run watch` 命令启动实时监控
  - 支持 22 个代理端口状态监控
  - 实时显示 Worker 状态、成功/失败计数

- **心跳机制**: 每 10 秒写入 `/app/logs/live_status.json`
  - 包含进度百分比、预估剩余时间
  - Worker 状态快照、代理端口状态

### 🗄️ 数据治理 (Data Governance)

- **任务查询优化**: 简化 SQL 查询，任务加载速度提升 80%
- **质量门禁增强**: 智能错误关键字检查，只检测核心数据区域

### 🔧 配置变更 (Configuration)

- **安全默认值调整**:
  - `MAX_WORKERS`: 5 → 1 (最稳模式)
  - `MIN_DELAY_MS`: 5000 → 10000 (潜行频率)
  - `MAX_DELAY_MS`: 12000 → 15000 (潜行频率)

### 📦 依赖清理 (Dependencies)

- 移除未使用的依赖: `js-yaml`, `playwright-extra`, `puppeteer-extra-plugin-stealth`
- 保留核心依赖: `dotenv`, `jsdom`, `p-limit`, `pg`, `playwright`

### 🧪 测试覆盖 (Testing)

- 新增 `tests/v173_core.test.js`: 6 个核心测试用例
  - ID 格式校验测试
  - URL 拼接逻辑测试
  - 配置加载测试
  - 质量门禁验证测试
  - 代理端口映射测试
  - 重试逻辑测试

---

## [V172.1.0] - 2026-02-27

### 新增功能

- 装甲群收割器 (Master-Worker 模式)
- 任务重试队列 (质量门禁失败自动回队)
- 指数退避重试策略
- 连接池 100% 释放保障

### 修复

- 修复 `page` 未定义 Bug
- 数据库组件正规化

---

## [V171.2.0] - 2026-02-25

### 新增功能

- L1 Discovery: 自动发现未来 7 天的比赛
- C++ Fuzzy Bridge: RapidFuzz 高性能队名匹配
- L2/L3 Harvest: 多源数据采集 (FotMob + OddsPortal)
- V171 Prediction: 3 模型共识预测
- NetworkShield: 22 节点代理池熔断保护

---

## 版本命名规范

- **主版本号 (Major)**: 架构重大变更
- **次版本号 (Minor)**: 新功能添加
- **修订号 (Patch)**: Bug 修复和小改进

---

**维护者**: V173 Engineering Team
**许可证**: MIT
