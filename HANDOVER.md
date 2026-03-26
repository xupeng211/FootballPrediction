# V6.6 项目交付快速索引 (HANDOVER.md)

> **最后更新**: 2026-03-20 | **版本**: V6.6 | **状态**: 生产就绪

---

## 1. 项目当前状态

### 🏗️ L1 发现层已封顶

| 指标 | 数值 | 状态 |
|------|------|------|
| **英超赛季覆盖** | 5 个赛季 (2021/22 ~ 2025/26) | ✅ 完整 |
| **总比赛场次** | 1,900 场 | ✅ 完美 |
| **每赛季场次** | 380 场 | ✅ 标准 |
| **数据一致性** | 100% | ✅ V6.5 硬化 |

### 🔒 L2 采集层已硬化 (V6.6)

| 指标 | 数值 | 状态 |
|------|------|------|
| **数据库约束** | 8 道 CHECK 约束 | ✅ V6.6 硬化 |
| **版本标记** | 全部 `data_version: 'V26.1'` | ✅ 全链路对齐 |
| **标准化工具** | Normalizer 全层复用 | ✅ L1/L2/L3 统一 |
| **单元测试** | 30 个测试 100% 通过 | ✅ 质量认证 |

### 📊 数据质量认证

- ✅ **赛季格式**: 100% `YYYY/YYYY` 标准格式
- ✅ **状态小写**: 100% 小写 (`finished`/`scheduled`/`live`)
- ✅ **布尔同步**: `is_finished` 与 `status` 100% 同步
- ✅ **版本统一**: 全部 `V25.1`

---

## 2. 核心运行命令

### 2.1 L1 赛程发现

```bash
# 默认运行（使用配置文件中的赛季）
npm run seed

# 指定单个赛季
node scripts/ops/seed_fixtures.js --season="2024/2025" --league=47

# 指定多个赛季
node scripts/ops/seed_fixtures.js --season="2024/2025,2025/2026" --league=47

# 全量收割（配置文件中所有活跃联赛和赛季）
npm run seed:all
```

### 2.2 参数规范

| 参数 | 说明 | 示例 |
|------|------|------|
| `--season` | 目标赛季，必须是 `YYYY/YYYY` 格式 | `"2024/2025"` |
| `--league` | 联赛 ID，英超固定为 47 | `47` |
| `--all` | 全量模式，处理配置文件中所有联赛 | - |

### 2.3 常用维护命令

```bash
# 健康检查
npm run titan:check

# 查看数据库状态
npm run status:db

# 运行单元测试
npm test

# 代码质量检查
npm run qa
```

---

## 3. 维护者警示 ⚠️

### 🔴 三大不可触碰红线

#### 红线 1: 不可随意修改 `matches` 表约束

**原因**: V6.5 在数据库层添加了硬约束，修改会导致 L1 写入失败

```sql
-- ❌ 危险操作：删除约束
ALTER TABLE matches DROP CONSTRAINT status_lowercase;

-- ❌ 危险操作：修改约束
ALTER TABLE matches DROP CONSTRAINT season_format;
```

**后果**: 
- 手动 SQL 插入非标准数据会通过
- 下游 L2/L3 层出现索引失效
- 预测模型准确性下降

**正确做法**: 
- 所有数据插入必须通过 `DiscoveryService + FixtureRepository.persist()`
- 如需修改约束，先更新 `Normalizer.normalizeSeason()` 与状态标准化链路

#### 红线 2: 不可直接操作 `is_finished` 字段

**原因**: 该字段由数据库触发器自动维护

```sql
-- ❌ 危险操作：手动更新 is_finished
UPDATE matches SET is_finished = true WHERE match_id = 'xxx';
```

**后果**:
- 触发器会覆盖你的修改
- 数据逻辑混乱

**正确做法**:
- 只更新 `status` 字段
- 触发器会自动同步 `is_finished`

#### 红线 3: 不可使用非标准赛季格式

**原因**: 数据库有 `CHECK (season ~ '^\d{4}/\d{4}$')` 约束

```javascript
// ❌ 危险代码：非标准格式
const season = '2324';  // 会被拒绝
const season = '2023-2024';  // 会被拒绝

// ✅ 正确做法：使用 Normalizer.normalizeSeason()
const season = Normalizer.normalizeSeason('2324');  // 返回 '2023/2024'
```

**后果**:
- 数据库报错：`violates check constraint "season_format"`
- 插入失败

#### 红线 4: 不可触碰 L2 `raw_match_data` 表约束 (V6.6 新增)

**原因**: V6.6 在 L2 层添加了 8 道硬约束，确保原始数据质量

```sql
-- ❌ 危险操作：删除约束
ALTER TABLE raw_match_data DROP CONSTRAINT match_id_format;
ALTER TABLE raw_match_data DROP CONSTRAINT raw_data_not_empty;

-- ❌ 危险操作：绕过代码层直接插入
INSERT INTO raw_match_data (match_id, raw_data) 
VALUES ('invalid-id', '{}');  -- 会被拒绝
```

**后果**:
- 非标准 match_id 进入系统，导致 L3 特征提取失败
- 空 raw_data 污染数据集
- 下游预测模型准确性下降

**正确做法**:
- 所有原始数据采集必须通过 `ProductionHarvester`
- 使用 `Normalizer.isValidMatchId()` 预检 match_id 格式
- 确保 `data_version: 'V26.1'` 标记存在

---

## 4. 关键文件索引

### 4.1 核心代码

| 文件 | 说明 |
|------|------|
| `src/infrastructure/services/DiscoveryService.js` | L1 核心服务，配置驱动并通过 Repository 落库 |
| `src/infrastructure/harvesters/ProductionHarvester.js` | L2 收割引擎，V6.6 硬化版本 |
| `src/utils/Normalizer.js` | V6.6 共享标准化工具类 |
| `scripts/ops/seed_fixtures.js` | L1 命令行入口 |
| `scripts/ops/run_production.js` | L2 命令行入口 |
| `config/leagues.json` | 联赛配置 |

### 4.2 文档

| 文件 | 说明 |
|------|------|
| `docs/adr/ADR-001-Source-Level-Data-Hardening.md` | V6.5 架构决策记录 |
| `docs/adr/ADR-002-L2-Raw-Storage-Hardening.md` | V6.6 架构决策记录 |
| `src/infrastructure/L1_DISCOVERY_ENGINE.md` | L1 技术文档 |
| `src/infrastructure/harvesters/L2_HARVESTING_ENGINE.md` | L2 技术文档 |
| `CHANGELOG.md` | 版本变更历史 |

### 4.3 数据库

| 文件 | 说明 |
|------|------|
| `database/migrations/V6.5__hardened_matches_schema.sql` | V6.5 迁移脚本 |
| `database/migrations/V6.6__hardened_l2_raw_storage.sql` | V6.6 迁移脚本 |

---

## 5. 故障排查速查表

| 问题 | 诊断 | 解决方案 |
|------|------|----------|
| `violates check constraint "season_format"` | 赛季格式错误 | 使用 `Normalizer.normalizeSeason()` 转换 |
| `violates check constraint "status_lowercase"` | 状态大小写错误 | 使用 `determineStatus()` 获取小写状态 |
| `violates check constraint "match_id_format"` | L2 match_id 格式错误 | 使用 `Normalizer.buildMatchId()` 构建 |
| `violates check constraint "raw_data_not_empty"` | L2 空数据插入 | 检查原始数据是否有效 |
| `is_finished` 不同步 | 手动修改导致 | 只更新 `status`，触发器会自动同步 |
| 数据插入失败 | 约束冲突 | 检查是否通过标准 Seeder/Harvester 操作 |

---

## 6. 架构决策 (ADR)

**核心决策**: 在 L1 层实现"双重防护"数据硬化

```
应用层 (Node.js)                    数据库层 (PostgreSQL)
├─ normalizeSeason()                ├─ CHECK (season ~ '^\d{4}/\d{4}$')
├─ determineStatus()    ───────▶    ├─ CHECK (status = LOWER(status))
└─ is_finished 计算                 └─ TRIGGER sync_is_finished
```

**目标**: "非标准数据进不来，标准数据改不掉"

---

## 7. 交接清单

### 对于新开发者

- [ ] 阅读 `docs/adr/ADR-001-Source-Level-Data-Hardening.md`
- [ ] 阅读 `src/infrastructure/L1_DISCOVERY_ENGINE.md` V6.5 章节
- [ ] 运行 `npm test` 确认测试通过
- [ ] 尝试运行 `npm run seed -- --season="2024/2025" --league=47`

### 对于运维人员

- [ ] 熟悉三大不可触碰红线
- [ ] 掌握 `npm run titan:check` 健康检查
- [ ] 了解 `database/migrations/` 目录结构
- [ ] 备份策略确认

---

## 8. 联系与支持

| 资源 | 位置 |
|------|------|
| 技术文档 | `docs/adr/`, `src/infrastructure/L1_DISCOVERY_ENGINE.md` |
| 测试用例 | `tests/unit/DiscoveryService.test.js` |
| 数据库迁移 | `database/migrations/` |

---

*"数据质量是预测准确性的基石。V6.5 的硬化投入，为下游节省了 10 倍的清洗成本。"*

**V6.5 兵团已达到"开箱即用、无痛交接"的最终状态！** 🚀
