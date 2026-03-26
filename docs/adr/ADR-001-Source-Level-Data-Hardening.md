# ADR-001: L1 层数据源级硬化 (Source-Level Data Hardening)

## 状态 (Status)

**已接受** (Accepted) - V6.5 (2026-03-19)

## 上下文 (Context)

在 V6.4 及之前版本，L1 发现层存在以下数据一致性问题：

1. **赛季格式混乱**: 同一赛季存在多种表示方式
   - `2324` (4位简写)
   - `2023-2024` (短横线分隔)
   - `20232024` (8位数字)
   - `2023/2024` (斜杠分隔，标准格式)
   
   这导致 L3 特征提取时，按赛季索引出现遗漏或重复。

2. **状态大小写不一**: 
   - `finished` vs `Finished` vs `FINISHED`
   - 统计口径偏差，聚合查询结果不准确

3. **布尔值不同步**: 
   - `status='finished'` 但 `is_finished=false`
   - 下游 L2/L3 层逻辑判断混乱

这些问题造成了**数据污染**，增加了下游清洗成本，影响了预测模型准确性。

## 决策 (Decision)

在 L1 层实现**双重防护**的数据硬化策略：

### 第一层：应用层防护 (Node.js)

在 L1 发现层中实现：

1. **`normalizeSeason()` 方法**: 强制转换所有赛季格式为标准 `YYYY/YYYY` 格式
2. **`determineStatus()` 方法**: 强制返回小写状态字符串
3. **`parseMatch()` 方法**: 自动计算 `is_finished` 布尔值

### 第二层：数据库层防护 (PostgreSQL)

添加数据库约束和触发器：

1. **CHECK 约束**:
   ```sql
   -- 强制 status 全小写
   ALTER TABLE matches ADD CONSTRAINT status_lowercase 
   CHECK (status = LOWER(status));
   
   -- 强制 season 符合 YYYY/YYYY 格式
   ALTER TABLE matches ADD CONSTRAINT season_format 
   CHECK (season ~ '^\d{4}/\d{4}$');
   ```

2. **同步触发器**:
   ```sql
   -- 自动同步 is_finished 与 status
   CREATE TRIGGER trg_sync_is_finished 
   BEFORE INSERT OR UPDATE ON matches
   FOR EACH ROW EXECUTE FUNCTION sync_is_finished();
   ```

## 后果 (Consequences)

### 优点 (Pros)

1. **"非标准数据进不来，标准数据改不掉"**: 实现了工业级数据一致性保障
2. **降低下游成本**: L2/L3 层无需再处理格式不一致问题
3. **幂等性保证**: 重复执行不会引入脏数据
4. **自文档化**: 数据库约束本身就是数据规范的强制执行

### 缺点 (Cons)

1. **开发约束**: 手动执行 SQL 插入时必须遵守规范，否则会触发报错
2. **迁移成本**: 存量数据需要一次性清洗（已在 V6.5 完成）
3. **灵活性降低**: 无法临时存储非标准格式的数据

### 缓解措施

- 所有数据插入**必须通过** `DiscoveryService + FixtureRepository.persist()` 或标准化工具
- 提供了 `normalizeSeason()` 工具方法处理格式转换
- 数据库迁移脚本已版本化归档 (`database/migrations/`)

## 替代方案 (Alternatives)

| 方案 | 优缺点 | 未选择原因 |
|------|--------|-----------|
| 仅应用层校验 | 简单，但无法防止手动 SQL 插入的脏数据 | 不能彻底解决数据污染 |
| ETL 清洗后置 | 灵活，但增加了 L2/L3 复杂度 | 治标不治本，成本转嫁 |
| 应用层 + 软约束 | 兼容性好，但无强制力 | 无法保证 100% 规范 |

## 影响范围 (Impact)

- **直接影响**: `matches` 表结构和 L1 发现持久化逻辑
- **间接受益**: L2 收割层、L3 特征层、预测模型层
- **运维影响**: 数据库写入操作需遵守新规范

## 相关资源 (References)

- [L1_DISCOVERY_ENGINE.md](/src/infrastructure/L1_DISCOVERY_ENGINE.md) - V6.5 章节
- [V6.5__hardened_matches_schema.sql](/database/migrations/V6.5__hardened_matches_schema.sql) - 数据库迁移脚本
- [DiscoveryService.test.js](/tests/unit/DiscoveryService.test.js) - 当前 L1 单元测试入口

## 决策记录 (Decision Log)

| 日期 | 作者 | 变更 |
|------|------|------|
| 2026-03-19 | V6.5 架构组 | 初始决策，实施双重防护策略 |

---

*"数据质量是预测准确性的基石。在 L1 层投入 1 分的硬化成本，能在下游节省 10 分的清洗成本。"* — V6.5 架构设计原则
