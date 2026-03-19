# L2 Harvesting Engine (数据收割层)

> **版本**: V6.6.0  
> **定位**: L2 原始数据采集与存储硬化层  
> **核心理念**: "搬运工"逻辑 - 只搬运，不创造，全链路可追溯

---

## 目录

1. [架构概述](#架构概述)
2. [数据双保险设计](#数据双保险设计)
3. [V6.6 硬化规则](#v66-硬化规则)
4. [版本控制策略](#版本控制策略)
5. [依赖关系](#依赖关系)
6. [核心组件](#核心组件)
7. [数据流](#数据流)

---

## 架构概述

L2 Harvesting Engine 是足球预测系统的数据采集层，负责：

- **原始数据抓取**: 从 FotMob、OddsPortal 等外部 API 获取原始 JSON 数据
- **数据标准化**: 通过 `Normalizer` 工具类统一数据格式
- **双保险存储**: 数据库 JSONB + 磁盘 JSON 冗余存储
- **质量守门**: 8 道 CHECK 约束确保数据完整性

```
┌─────────────────────────────────────────────────────────────────┐
│                     L2 Harvesting Engine                        │
├─────────────────────────────────────────────────────────────────┤
│  Input: L1 match_id (47_20242025_4506263)                       │
│                         ↓                                       │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐      │
│  │   FotMob     │ or │ OddsPortal   │ or │   Other      │      │
│  │  Strategy    │    │  Strategy    │    │  Strategies  │      │
│  └──────┬───────┘    └──────┬───────┘    └──────┬───────┘      │
│         ↓                   ↓                   ↓               │
│  ┌──────────────────────────────────────────────────────┐      │
│  │              Normalizer (标准化层)                    │      │
│  │  • match_id 格式验证: ^\d+_\d{8}_\d+$                │      │
│  │  • 赛季标准化: 2425 → 2024/2025                      │      │
│  │  • 队名清洗: 统一大小写、去除特殊字符                 │      │
│  └──────────────────────────────────────────────────────┘      │
│                         ↓                                       │
│  ┌──────────────────────────────────────────────────────┐      │
│  │              Persistence (持久化层)                   │      │
│  │  • 代码层预检: VALIDATION 错误提前拦截                │      │
│  │  • 数据库: raw_match_data (JSONB + 8道约束)          │      │
│  │  • 文件系统: data/matches/{match_id}.json            │      │
│  └──────────────────────────────────────────────────────┘      │
│                         ↓                                       │
│  Output: 带 data_version: 'V26.1' 标记的标准化原始数据          │
└─────────────────────────────────────────────────────────────────┘
```

---

## 数据双保险设计

### 为什么需要双保险？

原始数据是预测系统的"黄金资产"，任何丢失都是不可逆的。双保险确保：

1. **数据库为主**: PostgreSQL JSONB 提供结构化查询和事务保证
2. **文件为辅**: 磁盘 JSON 提供物理级备份和离线分析能力

### 双保险实现

```javascript
// Persistence.dualSave() 实现逻辑
async dualSave(pool, leagueId, season, externalId, rawData, metadata) {
    // 1. 数据库保存（主存储，失败即抛错，阻塞流程）
    const matchId = await this.saveToDatabase(client, leagueId, season, externalId, rawData);
    
    // 2. 文件保存（辅存储，失败不阻塞，异步执行）
    this.saveToFile(matchId, rawData, metadata).then(
        filePath => console.log(`[SAVE-FILE] ✓ ${matchId}.json 已保存`),
        err => console.error(`[SAVE-FILE] ${matchId} 保存失败: ${err.message}`)
    );
}
```

### 存储格式对比

| 维度 | 数据库 (raw_match_data) | 文件系统 (data/matches/) |
|------|------------------------|-------------------------|
| **格式** | JSONB | JSON |
| **约束** | 8 道 CHECK 约束 | 无（依赖代码层） |
| **版本标记** | `data_version` 字段 | `data_version` 字段 |
| **查询能力** | 强（SQL + GIN 索引） | 弱（需遍历文件） |
| **备份策略** | PostgreSQL 备份 | Git + 云存储同步 |
| **失败处理** | 阻塞整个流程 | 记录错误，继续执行 |

---

## V6.6 硬化规则

### 数据库 CHECK 约束 (8 道防线)

```sql
-- 1. match_id 格式约束: {leagueId}_{season}_{externalId}
-- 示例: 47_20242025_4506263
CONSTRAINT match_id_format CHECK (match_id ~ '^\d+_\d{8}_\d+$')

-- 2. raw_data 非空约束
CONSTRAINT raw_data_not_empty CHECK (
    raw_data IS NOT NULL AND 
    raw_data <> '{}'::jsonb
)

-- 3. 采集时间非空约束
CONSTRAINT collected_at_not_null CHECK (collected_at IS NOT NULL)

-- 4. 主键非空（系统默认）
-- 5. match_id 非空（系统默认）
-- 6. raw_data 非空（系统默认）
-- 7. 外键约束: match_id → matches.match_id
-- 8. 唯一约束: match_id 唯一
```

### 代码层预检 (Normalizer)

在数据到达数据库之前，代码层进行多重验证：

```javascript
// ProductionHarvester.saveData() 预检
async saveData(matchId, rawData) {
    // 预检 1: match_id 格式
    if (!Normalizer.isValidMatchId(matchId)) {
        throw new Error('[V6.6-VALIDATION] match_id 格式非法，无法保存: ${matchId}');
    }
    
    // 预检 2: raw_data 非空
    if (!rawData || Object.keys(rawData).length === 0) {
        throw new Error('[V6.6-VALIDATION] raw_data 不能为空: ${matchId}');
    }
    
    // 预检 3: 解析并标准化组件
    const parts = matchId.split('_');
    const leagueId = parts[0];
    const seasonTag = parts[1];
    const externalId = parts[2];
    
    // 继续保存流程...
}
```

### 错误分类体系

| 错误代码 | 层级 | 说明 | 处理策略 |
|---------|------|------|---------|
| `[V6.6-VALIDATION]` | 代码层 | 预检失败 | 立即拒绝，记录日志 |
| `[DB-ERROR]` | 数据库 | SQL 执行错误 | 根据错误类型重试或熔断 |
| `[DB-DUPLICATE]` | 数据库 | 唯一约束冲突 | 更新现有记录 |
| `[FILE-ERROR]` | 文件系统 | 磁盘写入失败 | 记录错误，不阻塞流程 |

---

## 版本控制策略

### data_version: 'V26.1'

所有 L2 原始数据必须携带版本标记，用于：

1. **数据溯源**: 知道数据产生于哪个系统版本
2. **迁移识别**: 区分新旧格式数据
3. **质量追踪**: 关联版本与数据质量指标

```sql
-- 按版本统计数据采集量
SELECT 
    data_version,
    COUNT(*) as count,
    MIN(collected_at) as first_collected,
    MAX(collected_at) as last_collected
FROM raw_match_data
GROUP BY data_version
ORDER BY data_version;
```

### 版本演进历史

| 版本 | 说明 | 主要变更 |
|------|------|---------|
| V25.1 | L1 基础版 | 原始 match 表版本 |
| **V26.1** | **L2 硬化版** | **新增 8 道约束 + Normalizer** |
| V27.x | 未来版本 | 待定 |

---

## 依赖关系

### L2 → L1 依赖

L2 层**严格依赖** L1 层的 `matches` 表：

```sql
-- 外键约束确保数据一致性
ALTER TABLE raw_match_data
ADD CONSTRAINT raw_match_data_match_id_fkey
FOREIGN KEY (match_id) REFERENCES matches(match_id);
```

这意味着：
1. **必须先有 L1**: 在收割原始数据前，matches 表中必须先存在对应记录
2. **ID 必须对齐**: L2 的 match_id 必须与 L1 的 match_id 像素级一致
3. **级联影响**: 如果 L1 数据被删除，L2 数据也会受外键约束影响

### 数据对齐验证

```sql
-- 检查 L1-L2 对齐情况
SELECT 
    m.match_id as l1_match_id,
    r.match_id as l2_match_id,
    CASE 
        WHEN r.match_id IS NULL THEN 'PENDING'
        ELSE 'HARVESTED'
    END as status
FROM matches m
LEFT JOIN raw_match_data r ON m.match_id = r.match_id
WHERE m.season = '2024/2025';
```

---

## 核心组件

### 1. Normalizer (标准化工具)

**路径**: `src/utils/Normalizer.js`

**职责**:
- `isValidMatchId(matchId)`: 验证 match_id 格式
- `normalizeSeason(season)`: 标准化赛季格式
- `normalizeTeamName(name)`: 标准化队名
- `buildMatchId(leagueId, season, externalId)`: 构建标准 match_id

**设计原则**:
- 纯函数，无副作用
- 与业务逻辑解耦
- L1/L2/L3 全层复用

### 2. Persistence (持久化器)

**路径**: `src/infrastructure/harvesters/components/Persistence.js`

**职责**:
- `saveToDatabase()`: 数据库保存（主存储）
- `saveToFile()`: 文件保存（辅存储）
- `dualSave()`: 双保险保存

**硬化特性**:
- 代码层预检（V6.6-VALIDATION）
- 强制 data_version 标记
- 异步文件存储不阻塞主流程

### 3. ProductionHarvester (收割指挥部)

**路径**: `src/infrastructure/harvesters/ProductionHarvester.js`

**职责**:
- 协调收割流程
- 集成 Normalizer 预检
- 调用 Persistence 保存

---

## 数据流

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   外部 API   │────▶│  Strategy    │────▶│  Extractor   │
│  (FotMob)    │     │  (FotMob)    │     │  (数据提取)   │
└──────────────┘     └──────────────┘     └──────┬───────┘
                                                  │
                                                  ▼
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   L3 特征层   │◀────│  PostgreSQL  │◀────│  Normalizer  │
│  (特征工程)   │     │ (raw_match_  │     │  (标准化)    │
└──────────────┘     │   data)      │     └──────┬───────┘
                     └──────────────┘            │
                            ▲                    │
                            │            ┌───────┴───────┐
                            │            │               │
                     ┌──────┴───────┐    │    ┌──────────┴──┐
                     │   磁盘备份    │◀───┘    │  代码层预检  │
                     │ (JSON 文件)  │         │ (V6.6 硬化)  │
                     └──────────────┘         └─────────────┘
```

---

## 相关文档

- [ADR-002: L2 原始数据存储硬化决策](../../docs/adr/ADR-002-L2-Raw-Storage-Hardening.md)
- [L1 Discovery Engine](../core/L1_DISCOVERY_ENGINE.md)
- [V6.6 测试套件](../../../tests/unit/L2_Normalizer_Persistence.test.js)

---

**维护者**: V6.6 Engineering Team  
**最后更新**: 2026-03-19
