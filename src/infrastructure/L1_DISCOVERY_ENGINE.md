# L1 Discovery Engine - 技术说明文档

> **版本**: V178.0.0 | **最后更新**: 2026-03-02

---

## 1. 概述

### 1.1 什么是 L1 发现层？

L1 Discovery Engine 是 FootballPrediction 三层架构中的第一层，负责**比赛索引发现**。

```
┌─────────────────────────────────────────────────────────────────────┐
│                        三层架构 (3-Layer Architecture)               │
├─────────────────────────────────────────────────────────────────────┤
│  L1 Discovery   │  从 FotMob API 发现比赛索引，写入 matches 表      │
│  L2 Harvest     │  从 OddsPortal 采集赔率数据，写入 l2_match_data   │
│  L3 Feature     │  特征工程，生成 12061 维特征向量                  │
└─────────────────────────────────────────────────────────────────────┘
```

### 1.2 核心职责

| 职责 | 说明 |
|------|------|
| **比赛发现** | 从 FotMob API 获取指定联赛的完整赛程 |
| **索引构建** | 生成唯一的 `match_id` 作为后续层级的关联键 |
| **数据持久化** | 将比赛索引写入 PostgreSQL `matches` 表 |

---

## 2. 架构设计

### 2.1 数据流向

```
┌──────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  FotMob API  │────▶│  FixtureSeeder   │────▶│   PostgreSQL    │
│              │     │                  │     │   matches 表    │
│ /api/leagues │     │  - fetchLeague() │     │                 │
│              │     │  - parseMatch()  │     │  - match_id PK  │
│              │     │  - upsert()      │     │  - external_id  │
└──────────────┘     └──────────────────┘     └─────────────────┘
```

### 2.2 核心组件

| 组件 | 文件 | 职责 |
|------|------|------|
| **FixtureSeeder** | `src/infrastructure/FixtureSeeder.js` | L1 核心类，唯一数据源 |
| **seed_fixtures** | `scripts/ops/seed_fixtures.js` | 命令行入口脚本 |
| **leagues.json** | `config/leagues.json` | 联赛配置（配置分离） |

### 2.3 设计原则

- **Single Source of Truth**: `FixtureSeeder` 是 L1 层的唯一实现
- **Configuration as Code**: 联赛列表从配置文件加载，不硬编码
- **Idempotency**: 支持重复执行，使用 UPSERT 避免重复数据

---

## 3. 核心特性

### 3.1 ID 唯一性规则

`match_id` 是整个系统的核心关联键，格式为：

```
${league_id}_${season}_${externalId}
```

**示例**:

- 英超 2024/25 赛季第 1 轮: `47_20242025_123456789`
- 西甲 2023/24 赛季第 10 轮: `87_20232024_987654321`

**优势**:

- 跨联赛唯一性
- 可读性强，一眼识别联赛和赛季
- 支持数据溯源

### 3.2 联赛过滤机制

联赛过滤通过 `config/leagues.json` 的 `enabled` 字段控制：

```json
{
  "active_leagues": [
    { "id": 47, "name": "Premier League", "enabled": true }
  ],
  "inactive_leagues": [
    { "id": 87, "name": "La Liga", "enabled": false }
  ]
}
```

**过滤逻辑**:

1. 加载配置文件
2. 过滤 `enabled !== false` 的联赛
3. 只处理过滤后的联赛列表

### 3.3 配置分离设计

**Before (硬编码)**:

```javascript
// ❌ 硬编码联赛 ID
const leagues = [{ id: 47, name: 'Premier League' }];
```

**After (配置分离)**:

```javascript
// ✅ 从配置文件加载
const { active_leagues } = loadLeagueConfig();
```

**优势**:

- 新增联赛只需修改配置文件
- 不需要修改代码
- 支持多环境配置

---

## 4. 配置手册

### 4.1 leagues.json 结构

```json
{
  "version": "V178.0.0",
  "description": "L1 发现层联赛配置 - 单一数据源",
  "active_leagues": [...],
  "inactive_leagues": [...],
  "active_seasons": ["2023/2024", "2024/2025"]
}
```

### 4.2 字段说明

| 字段 | 类型 | 说明 |
|------|------|------|
| `version` | string | 配置版本号 |
| `active_leagues` | array | 当前活跃的联赛列表 |
| `inactive_leagues` | array | 已停用的联赛列表（保留历史） |
| `active_seasons` | array | 要处理的赛季列表 |

### 4.3 联赛对象结构

```json
{
  "id": 47,
  "name": "Premier League",
  "country": "England",
  "enabled": true
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | number | FotMob 联赛 ID |
| `name` | string | 联赛显示名称 |
| `country` | string | 所属国家 |
| `enabled` | boolean | 是否启用（默认 true） |

### 4.4 常用联赛 ID

| 联赛 | ID |
|------|-----|
| 英超 (Premier League) | 47 |
| 西甲 (La Liga) | 87 |
| 意甲 (Serie A) | 55 |
| 德甲 (Bundesliga) | 54 |
| 法甲 (Ligue 1) | 53 |
| 欧冠 (Champions League) | 42 |

---

## 5. 操作手册

### 5.1 运行指令

```bash
# 进入开发容器
docker-compose -f docker-compose.dev.yml exec dev bash

# 默认运行（使用配置文件）
node scripts/ops/seed_fixtures.js

# 指定联赛
node scripts/ops/seed_fixtures.js --league=47

# 指定赛季
node scripts/ops/seed_fixtures.js --season=2024/2025

# 全量收割
node scripts/ops/seed_fixtures.js --all
```

### 5.2 测试指令

```bash
# 运行单元测试
node --test tests/unit/FixtureSeeder.test.js

# 运行所有测试
npm test
```

### 5.3 日志查看

```bash
# 实时查看日志
docker-compose -f docker-compose.dev.yml exec dev tail -f logs/harvest.log

# 查看最近 100 行
docker-compose -f docker-compose.dev.yml exec dev tail -100 logs/harvest.log
```

### 5.4 日志格式

```
[2026-03-02T10:00:00.000Z] [INFO] [FixtureSeeder] 配置加载成功: 1 个活跃联赛
[2026-03-02T10:00:01.000Z] [INFO] [FixtureSeeder] 获取联赛 47 赛季 2024/2025...
[2026-03-02T10:00:02.000Z] [SUCCESS] [FixtureSeeder] Premier League - 2024/2025: 380 场已处理
[2026-03-02T10:00:03.000Z] [ERROR] [FixtureSeeder] UPSERT 失败: 47_20242025_123 | {"error":"...","stack":"..."}
```

| 级别 | 说明 |
|------|------|
| INFO | 常规信息 |
| WARN | 警告信息（不影响运行） |
| ERROR | 错误信息（含堆栈追踪） |
| SUCCESS | 成功信息 |

---

## 6. 数据库表结构

### 6.1 matches 表

```sql
CREATE TABLE matches (
    match_id VARCHAR(100) PRIMARY KEY,
    external_id VARCHAR(50),
    league_name VARCHAR(100),
    season VARCHAR(20),
    home_team VARCHAR(100),
    away_team VARCHAR(100),
    match_date TIMESTAMP,
    home_score INTEGER,
    away_score INTEGER,
    status VARCHAR(20),
    data_source VARCHAR(50),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

### 6.2 字段说明

| 字段 | 类型 | 说明 |
|------|------|------|
| `match_id` | VARCHAR(100) | 主键，格式: `${league}_${season}_${id}` |
| `external_id` | VARCHAR(50) | FotMob 原始 ID |
| `league_name` | VARCHAR(100) | 联赛名称 |
| `season` | VARCHAR(20) | 赛季，格式: 2024/2025 |
| `home_team` | VARCHAR(100) | 主队名称 |
| `away_team` | VARCHAR(100) | 客队名称 |
| `match_date` | TIMESTAMP | 比赛时间 (UTC) |
| `home_score` | INTEGER | 主队得分 (已完赛时) |
| `away_score` | INTEGER | 客队得分 (已完赛时) |
| `status` | VARCHAR(20) | 状态: scheduled/live/finished/cancelled |
| `data_source` | VARCHAR(50) | 数据来源，固定为 'FotMob' |

---

## 7. 故障排查

### 7.1 常见问题

| 问题 | 诊断 | 解决方案 |
|------|------|----------|
| 配置加载失败 | 检查 `config/leagues.json` 格式 | 修复 JSON 语法错误 |
| 数据库连接失败 | `docker-compose exec db pg_isready` | 重启数据库容器 |
| API 请求超时 | 检查网络连接 | 增大 timeout 配置 |
| 数据重复 | 检查 match_id 格式 | 确保使用正确的 ID 规则 |

### 7.2 调试模式

```bash
# 启用 Node.js 调试
NODE_DEBUG=* node scripts/ops/seed_fixtures.js
```

---

## 8. 数据合约 (Data Contract)

### 8.1 match_id 唯一性设计

`match_id` 是 L1 层的核心契约，作为整个系统的主键关联 L2/L3 层。

**格式规范**:

```
${league_id}_${season}_${externalId}
```

**组成部分**:

| 组件 | 来源 | 示例 |
|------|------|------|
| `league_id` | FotMob 联赛 ID | 47 (英超) |
| `season` | 赛季标签 (无斜杠) | 20242025 |
| `externalId` | FotMob 比赛 ID | 123456789 |

**完整示例**:

```
47_20242025_123456789   # 英超 2024/25 赛季某场比赛
87_20232024_987654321   # 西甲 2023/24 赛季某场比赛
```

**唯一性保证**:

- 跨联赛唯一
- 跨赛季唯一
- 跨数据源唯一（所有来源使用相同格式）

### 8.2 status 状态机

比赛状态遵循严格的状态机流转逻辑：

```
                    ┌──────────────┐
                    │  cancelled   │ (比赛取消)
                    └──────────────┘
                           ↑
┌────────────┐    ┌────────────┐    ┌────────────┐
│ scheduled  │───▶│    live    │───▶│  finished  │
│  (未开始)   │    │  (进行中)   │    │  (已结束)   │
└────────────┘    └────────────┘    └────────────┘
       │                │
       │                ↓
       │         ┌────────────┐
       └────────▶│  awarded   │ (判罚结果)
                 └────────────┘
```

**状态定义**:

| 状态 | 触发条件 | 后续操作 |
|------|---------|----------|
| `scheduled` | 比赛未开始 | 等待 L2 层采集赔率 |
| `live` | 比赛进行中 | 实时更新 L2 数据 |
| `finished` | 比赛正常结束 | 触发 L3 特征计算 |
| `cancelled` | 比赛取消 | 标记无效，不参与预测 |
| `awarded` | 判罚结果 | 特殊处理 |

**状态转换规则**:

1. `scheduled` → `live`: 比赛开始时间到达
2. `live` → `finished`: 比赛结束，比分确定
3. `scheduled` → `cancelled`: 比赛取消（不可逆）
4. `scheduled`/`live` → `awarded`: 判罚结果（罕见）

### 8.3 数据质量契约

| 指标 | 阈值 | 说明 |
|------|------|------|
| `success_rate` | ≥ 95% | 任务成功率 |
| `match_id` | 100% 唯一 | 主键约束 |
| `home_team/away_team` | 非空 | 必填字段 |
| `data_source` | 固定值 | 必须为 'FotMob' |

**数据验证规则**:

```javascript
// match_id 格式验证
const MATCH_ID_PATTERN = /^\d+_\d{8}_\d+$/;

// 有效: 47_20242025_123456789
// 无效: 47-20242025-123456789
// 无效: premier_league_2024_123
```

---

## 9. 度量指标 (Metrics)

### 9.1 getSummary() 输出示例

```javascript
{
  "total": 380,
  "inserted": 10,
  "updated": 370,
  "errors": 0,
  "success_rate": 100.00,
  "status": "success",
  "leagues": 2,
  "timestamp": "2026-03-02T10:00:00.000Z"
}
```

### 9.2 状态判断规则

| success_rate | status | 说明 |
|--------------|--------|------|
| 100% | `success` | 完美执行 |
| ≥ 95% | `warning` | 有少量错误 |
| < 95% | `failed` | 需要排查 |
| 0% (total=0) | `empty` | 无数据处理 |

### 9.3 日志追踪

每条 ERROR 日志携带唯一 `request_id`：

```
[2026-03-02T10:00:00Z] [ERROR] [FixtureSeeder] [req_m5x2k9_abc123] UPSERT 失败
```

用于：

- 错误溯源
- 日志聚合
- 告警关联

---

## 10. 数据归一化 (V6.5)

V6.5 版本引入了强制数据归一化机制，确保入库数据格式统一。

### 10.1 赛季格式归一化

**问题背景**: 不同数据源可能使用不同的赛季格式（如 '2324'、'20242025'、'2024-2025'），导致数据混乱。

**解决方案**: `normalizeSeason()` 函数强制统一为 `'YYYY/YYYY'` 格式。

```javascript
// V6.5: 赛季格式标准化
normalizeSeason(season) {
    // 已经是标准格式
    if (/^\d{4}\/\d{4}$/.test(season)) return season;
    
    // '2324' → '2023/2024'
    if (/^\d{4}$/.test(season)) {
        return `20${season.substring(0, 2)}/20${season.substring(2, 4)}`;
    }
    
    // '20242025' → '2024/2025'
    if (/^\d{8}$/.test(season)) {
        return `${season.substring(0, 4)}/${season.substring(4, 8)}`;
    }
    
    // '2024-2025' → '2024/2025'
    if (/^\d{4}-\d{4}$/.test(season)) {
        return season.replace('-', '/');
    }
    
    throw new Error(`Unrecognized season format: ${season}`);
}
```

**转换示例**:

| 输入格式 | 输出格式 | 说明 |
|----------|----------|------|
| `2023/2024` | `2023/2024` | 标准格式，直接通过 |
| `2324` | `2023/2024` | 4位简写，自动补全世纪 |
| `20232024` | `2023/2024` | 8位数字，自动分割 |
| `2023-2024` | `2023/2024` | 短横线分隔，自动替换 |
| `23/24` | ❌ 报错 | 非法格式，抛出 Error |

**数据库约束**:
```sql
ALTER TABLE matches ADD CONSTRAINT season_format 
CHECK (season ~ '^\d{4}/\d{4}$');
```

### 10.2 状态值归一化

**问题背景**: FotMob API 返回的状态值可能存在大小写不一致（'finished' vs 'Finished'）。

**解决方案**: `determineStatus()` 方法强制返回小写状态值。

```javascript
determineStatus(match, homeScore, awayScore) {
    // ... 状态判断逻辑 ...
    
    // V6.5: 强制小写归一化
    return result.toLowerCase();
}
```

**标准化状态值**:

| 状态 | 说明 |
|------|------|
| `scheduled` | 比赛未开始 |
| `live` | 比赛进行中 |
| `finished` | 比赛已结束 |
| `cancelled` | 比赛已取消 |
| `postponed` | 比赛已延期 |
| `awarded` | 判罚结果 |

**数据库约束**:
```sql
ALTER TABLE matches ADD CONSTRAINT status_lowercase 
CHECK (status = LOWER(status));
```

---

## 11. 数据一致性保障 (V6.5)

V6.5 版本在数据库层面建立了双重防护机制，确保 `status` 和 `is_finished` 字段 100% 同步。

### 11.1 双重防护架构

```
┌─────────────────────────────────────────────────────────────┐
│ 第一层: 应用层 (Node.js FixtureSeeder.js)                    │
├─────────────────────────────────────────────────────────────┤
│ parseMatch() {                                               │
│   const status = this.determineStatus(...);  // 'finished'  │
│   const isFinished = status === 'finished';  // true        │
│   return { ..., status, is_finished: isFinished };          │
│ }                                                            │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│ 第二层: 数据库层 (PostgreSQL Trigger)                        │
├─────────────────────────────────────────────────────────────┤
│ BEFORE INSERT OR UPDATE                                      │
│   NEW.is_finished := (NEW.status = 'finished');             │
│                                                              │
│ 说明：即使应用层忘记设置，触发器也会自动修正                 │
└─────────────────────────────────────────────────────────────┘
```

### 11.2 触发器实现

```sql
-- 创建触发器函数
CREATE OR REPLACE FUNCTION sync_is_finished()
RETURNS TRIGGER AS $$
BEGIN
    NEW.is_finished := (NEW.status = 'finished');
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 挂载触发器
CREATE TRIGGER trg_sync_is_finished
    BEFORE INSERT OR UPDATE ON matches
    FOR EACH ROW
    EXECUTE FUNCTION sync_is_finished();
```

### 11.3 字段定义更新

V6.5 版本在 `matches` 表中新增 `is_finished` 字段：

```sql
CREATE TABLE matches (
    match_id VARCHAR(100) PRIMARY KEY,
    external_id VARCHAR(50),
    league_name VARCHAR(100),
    season VARCHAR(20),
    home_team VARCHAR(100),
    away_team VARCHAR(100),
    match_date TIMESTAMP,
    home_score INTEGER,
    away_score INTEGER,
    status VARCHAR(20),
    is_finished BOOLEAN,           -- ✅ V6.5 新增：与 status 同步
    data_source VARCHAR(50),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

**字段说明**:

| 字段 | 类型 | 来源 | 说明 |
|------|------|------|------|
| `status` | VARCHAR(20) | 应用层 + DB CHECK | 比赛状态（强制小写） |
| `is_finished` | BOOLEAN | 应用层计算 + DB Trigger | 是否完赛（`status='finished'` 时为 true） |

### 11.4 一致性验证

**测试验证**:

```sql
-- 插入测试数据
INSERT INTO matches (..., status, ...) VALUES (..., 'finished', ...);

-- 验证 is_finished 自动同步
SELECT status, is_finished FROM matches WHERE ...;
-- 结果: status='finished', is_finished=true ✅

-- 更新状态
UPDATE matches SET status = 'scheduled' WHERE ...;

-- 验证 is_finished 自动更新
SELECT status, is_finished FROM matches WHERE ...;
-- 结果: status='scheduled', is_finished=false ✅
```

---

## 12. 变更历史

| 版本 | 日期 | 变更内容 |
|------|------|----------|
| **V6.5** | **2026-03-19** | **数据库硬核加固：CHECK 约束 + 触发器同步；L1 引擎全量归一化** |
| V178.0.0 | 2026-03-02 | 配置分离、日志分级、JSDoc、数据合约、度量指标 |
| V177.0.0 | 2026-03-02 | 移除野生脚本，单一数据源确权 |
| V176.0.0 | 2026-02-28 | 初始重构 |

---

*文档维护: FootballPrediction Engineering Team*
