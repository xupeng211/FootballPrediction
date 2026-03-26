# L1 发现层数据契约 (L1 Discovery Layer Data Contract)

> **版本**: V6.4  
> **状态**: 生产就绪 (Production Ready)  
> **最后更新**: 2026-03-18

---

## 1. 概述

本文档定义 FootballPrediction 系统 L1 (Discovery) 层的数据契约，包括：
- `match_id` 生成算法
- 数据生命周期管理
- L1 → L2 数据输出格式

---

## 2. Match ID 生成算法

### 2.1 算法定义

```javascript
function generateMatchId(leagueId, season, externalId) {
    // 1. 赛季格式标准化: "2024/2025" → "20242025"
    const seasonTag = season.replace(/\//g, '');
    
    // 2. 确定性拼接
    return `${leagueId}_${seasonTag}_${externalId}`;
}
```

### 2.2 示例

| 联赛 | 赛季 | 外部ID | 生成的 match_id |
|------|------|--------|----------------|
| 英超 (47) | 2024/2025 | 123456789 | `47_20242025_123456789` |
| 英超 (47) | 2024/2025 | 987654321 | `47_20242025_987654321` |
| 西甲 (87) | 2024/2025 | 123456789 | `87_20242025_123456789` |

### 2.3 契约保证

- **唯一性**: 全局唯一，跨联赛/赛季/比赛不碰撞
- **确定性**: 相同输入始终产生相同输出 (幂等性)
- **可读性**: 一眼可识别联赛和赛季
- **稳定性**: 不随系统重启或重新运行而改变

### 2.4 碰撞风险分析

```
风险场景: ID 123 匹配到 4123?
分析: "47_20242025_123" vs "47_20242025_4123"
结果: 前缀不同，不会碰撞 (下划线分隔符保证边界)
```

---

## 3. 数据生命周期

### 3.1 实体关系图

```
┌─────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   matches   │◄────┤ raw_match_data   │     │  predictions    │
│   (L1)      │     │   (L2原始数据)    │     │   (L3预测)      │
└──────┬──────┘     └──────────────────┘     └─────────────────┘
       │
       │         ┌──────────────────┐
       └────────►│  l2_match_data   │
                 │ (L2结构化数据)   │
                 └──────────────────┘
```

### 3.2 ON DELETE CASCADE 影响

```sql
-- 子表外键定义
CREATE TABLE raw_match_data (
    match_id VARCHAR(50) REFERENCES matches(match_id) ON DELETE CASCADE
);

CREATE TABLE predictions (
    match_id VARCHAR(50) REFERENCES matches(match_id) ON DELETE CASCADE
);
```

**级联删除影响范围**:

| 操作 | 影响 |
|------|------|
| `DELETE FROM matches WHERE match_id = '47_20242025_123'` | 仅删除该比赛 |
| `TRUNCATE TABLE matches CASCADE` | **危险**: 删除所有比赛 + 级联删除所有子表数据 |
| `DELETE FROM matches WHERE season = '2024/2025'` | 删除该赛季所有比赛及关联数据 |

### 3.3 生产环境警告 ⚠️

**高危操作**:
```sql
-- ❌ 危险: 将级联删除 380+ 场比赛及其所有关联数据
TRUNCATE TABLE matches CASCADE;

-- ❌ 危险: 误删整个赛季
DELETE FROM matches WHERE season = '2024/2025';
```

**推荐操作**:
```sql
-- ✅ 安全: 仅删除指定比赛 (级联删除关联数据)
DELETE FROM matches WHERE match_id = '47_20242025_123456789';

-- ✅ 安全: 先备份再删除
BEGIN;
  CREATE TEMP TABLE backup_matches AS SELECT * FROM matches WHERE season = '2024/2025';
  DELETE FROM matches WHERE season = '2024/2025';
COMMIT;
```

---

## 4. L1 → L2 输出格式

### 4.1 标准输出结构

```typescript
interface L1MatchOutput {
    // 核心标识
    match_id: string;           // 例如: "47_20242025_123456789"
    external_id: string;        // FotMob 原始 ID: "123456789"
    
    // 联赛信息
    league_name: string;        // "Premier League"
    season: string;             // "2024/2025"
    
    // 对阵双方
    home_team: string;          // "Manchester City"
    away_team: string;          // "Liverpool"
    
    // 时间信息
    match_date: Date;           // 2024-10-15T15:00:00.000Z
    
    // 比分信息 (可能为 null)
    home_score: number | null;  // 2
    away_score: number | null;  // 1
    
    // 状态
    status: 'scheduled' | 'live' | 'finished' | 'cancelled' | 'postponed';
    
    // 元数据
    data_source: 'FotMob';
    created_at: Date;
    updated_at: Date;
}
```

### 4.2 JSON 示例

```json
{
    "match_id": "47_20242025_123456789",
    "external_id": "123456789",
    "league_name": "Premier League",
    "season": "2024/2025",
    "home_team": "Manchester City",
    "away_team": "Liverpool",
    "match_date": "2024-10-15T15:00:00.000Z",
    "home_score": null,
    "away_score": null,
    "status": "scheduled",
    "data_source": "FotMob",
    "created_at": "2024-10-01T10:00:00.000Z",
    "updated_at": "2024-10-01T10:00:00.000Z"
}
```

### 4.3 L2 回填器消费契约

L2 层 (数据收割) 应使用 `match_id` 作为主键进行数据对齐：

```javascript
// L2 回填器示例
async function backfillL2Data(l1Match, oddsData) {
    const matchId = l1Match.match_id; // "47_20242025_123456789"
    
    // 使用 match_id 关联 L2 数据
    await db.query(`
        INSERT INTO l2_match_data (match_id, odds_data)
        VALUES ($1, $2)
        ON CONFLICT (match_id) DO UPDATE
        SET odds_data = EXCLUDED.odds_data
    `, [matchId, JSON.stringify(oddsData)]);
}
```

---

## 5. 质量指标

| 指标 | 目标值 | 验证方式 |
|------|--------|----------|
| match_id 唯一性 | 100% | 数据库唯一约束 |
| ID 生成确定性 | 100% | 单元测试验证 |
| 数据完整性 | ≥99% | 外键约束检查 |
| 幂等性 | 100% | UPSERT 语义 |

---

## 6. 变更日志

| 版本 | 日期 | 变更内容 |
|------|------|----------|
| V6.0 | 2026-03-15 | 初始版本，引入三道铁门验证 |
| V6.4 | 2026-03-18 | 增加熔断机制、连接池保护、日志计数器隔离 |

---

## 7. 附录

### 7.1 相关文件

- `src/core/validation/MatchValidator.js` - 验证逻辑
- `src/infrastructure/services/DiscoveryService.js` - 数据播种协调器
- `scripts/ops/seed_fixtures.js` - 命令行入口
- `config/season_windows.json` - 赛季窗口配置

### 7.2 运行测试

```bash
# 运行 MatchValidator 单元测试
npm test tests/unit/MatchValidator.test.js

# 查看覆盖率报告
npx jest --coverage tests/unit/MatchValidator.test.js
```

---

*本契约由 FootballPrediction 工程团队维护*
