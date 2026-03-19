# L1 Discovery Engine - 发现引擎文档

> **版本**: V6.4  
> **状态**: 生产就绪 (Production Ready)  
> **最后更新**: 2026-03-18

---

## 1. 核心架构

### 1.1 系统定位

L1 Discovery Engine 是 FootballPrediction 系统的数据入口层，负责：
- 从外部 API (FotMob) 发现即将进行的足球比赛
- 执行三道铁门数据验证
- 生成标准化的 `match_id`
- 将纯净数据写入 `matches` 表

### 1.2 架构图

```
┌─────────────────────────────────────────────────────────────────┐
│                     L1 Discovery Engine V6.4                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐      │
│  │   FotMob API │───▶│ 三道铁门验证  │───▶│  PostgreSQL  │      │
│  │   (Source)   │    │ (Validation) │    │  (matches表) │      │
│  └──────────────┘    └──────────────┘    └──────────────┘      │
│                             │                                    │
│                    ┌────────┴────────┐                          │
│                    ▼                 ▼                          │
│           ┌─────────────┐   ┌─────────────┐                     │
│           │ MatchValidator│  │CircuitBreaker│                   │
│           │   (V6.4)      │  │   (V6.4)     │                   │
│           └─────────────┘   └─────────────┘                     │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 2. V6.4 防御特性

### 2.1 三道铁门验证 (Three Gates Validation)

**Gate 1: LeagueID 校验**
```javascript
// 无罪推定原则 - 只有明确不匹配才拦截
function isTargetLeague(match, expectedLeagueId) {
    const actualId = match.leagueId || match.parent?.leagueId;
    return !actualId || actualId === expectedLeagueId;
}
```

**Gate 2: 时间窗口校验**
```javascript
// 支持多种时间格式 + 缓冲期机制
function validateSeasonWindow(match, window) {
    // ISO 字符串: '2024-10-15T15:00:00Z'
    // Unix 秒: 1728908400
    // Unix 毫秒: 1728908400000
    // + 14天缓冲期
}
```

**Gate 3: 占位符检测**
```javascript
// 自动拦截 TBD/TBC/待定等占位符比赛
const PLACEHOLDER_KEYWORDS = ['tbd', 'tbc', '待定', 'winner', 'runner-up'];
```

### 2.2 熔断机制 (Circuit Breaker)

```javascript
// V6.4: 自动熔断保护
class FixtureSeeder {
    constructor() {
        this._consecutiveFailures = 0;
        this._circuitBreakerOpen = false;
        this._circuitBreakerOpenedAt = null;
    }

    async execute() {
        // 连续5次失败触发熔断
        if (this._consecutiveFailures >= 5) {
            this._circuitBreakerOpen = true;
            this._circuitBreakerOpenedAt = Date.now();
        }

        // 熔断后5分钟自动重置
        if (this._circuitBreakerOpen && 
            Date.now() - this._circuitBreakerOpenedAt > 5 * 60 * 1000) {
            this._circuitBreakerOpen = false;
            this._consecutiveFailures = 0;
        }
    }
}
```

### 2.3 连接池 (Connection Pool)

```javascript
// V6.4: PostgreSQL 连接池
const pool = new Pool({
    max: 20,              // 最大连接数
    idleTimeoutMillis: 30000,  // 30秒空闲超时
    connectionTimeoutMillis: 5000  // 5秒连接超时
});
```

### 2.4 日志隔离

```javascript
// 每轮调用独立的 stats 对象
const stats = {
    wrongLeague: 0,
    outsideWindow: 0,
    placeholder: 0,
    invalidData: 0,
    _debugLogCount: 0  // 内部调试日志计数器
};

// 调用后 stats 完全隔离
const result = threeGatesFilter(matches, leagueInfo, season, stats, log);
```

---

## 3. ID 生成算法

### 3.1 算法定义

```javascript
function generateMatchId(leagueId, season, externalId) {
    // 1. 赛季格式标准化: "2024/2025" → "20242025"
    const seasonTag = season.replace(/\//g, '');
    
    // 2. 确定性拼接
    return `${leagueId}_${seasonTag}_${externalId}`;
}
```

### 3.2 示例

| 联赛 | 赛季 | 外部ID | match_id |
|------|------|--------|----------|
| 英超 (47) | 2024/2025 | 123456789 | `47_20242025_123456789` |
| 英超 (47) | 2024/2025 | 987654321 | `47_20242025_987654321` |

### 3.3 契约保证

- **唯一性**: 全局唯一，跨联赛/赛季不碰撞
- **确定性**: 相同输入始终产生相同输出
- **可读性**: 一眼识别联赛和赛季
- **稳定性**: 不随系统重启而改变

---

## 4. 快速操作指南

### 4.1 运行 L1 发现

```bash
# 标准模式 (发现未来7天比赛)
node scripts/ops/seed_fixtures.js

# 指定日期范围
node scripts/ops/seed_fixtures.js --start 2024-08-01 --end 2024-08-31

# 调试模式
LOG_LEVEL=debug node scripts/ops/seed_fixtures.js
```

### 4.2 运行单元测试

```bash
# 运行 MatchValidator 测试
node --test tests/unit/MatchValidator.test.js

# 预期输出: 50/50 通过
# ℹ tests 50
# ℹ pass 50
# ℹ fail 0
```

### 4.3 验证数据质量

```bash
# 查看已发现比赛数量
docker-compose exec db psql -U football_user -d football_db -c "
    SELECT 
        season,
        COUNT(*) as match_count,
        COUNT(*) FILTER (WHERE l2_harvested = true) as l2_ready
    FROM matches 
    WHERE match_date >= CURRENT_DATE
    GROUP BY season;
"
```

### 4.4 检查三道铁门拦截统计

```javascript
// 日志中会输出拦截统计
{
    "totalScanned": 380,
    "accepted": 345,
    "rejected": {
        "wrongLeague": 10,      // Gate 1 拦截
        "outsideWindow": 15,    // Gate 2 拦截
        "placeholder": 5,       // Gate 3 拦截
        "invalidData": 5        // 基础验证拦截
    }
}
```

---

## 5. 配置文件

### 5.1 season_windows.json

```json
{
    "seasons": {
        "2024/2025": {
            "start": "2024-08-16",
            "end": "2025-05-25"
        }
    },
    "validation_rules": {
        "buffer_days": 14,
        "placeholder_keywords": ["tbd", "tbc", "待定"],
        "max_daily_matches_per_league": 15
    }
}
```

### 5.2 环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `DB_HOST` | 数据库主机 | `localhost` |
| `DB_PORT` | 数据库端口 | `5432` |
| `DB_NAME` | 数据库名称 | `football_db` |
| `DB_USER` | 数据库用户 | `football_user` |
| `DB_PASSWORD` | 数据库密码 | *(必填)* |
| `LOG_LEVEL` | 日志级别 | `info` |

---

## 6. 故障排查

### 6.1 熔断触发

**症状**: `Circuit breaker is OPEN. Waiting for cooldown...`

**解决**:
1. 检查 FotMob API 可用性
2. 等待 5 分钟自动重置
3. 或手动重启进程

### 6.2 连接池耗尽

**症状**: `Error: timeout exceeded when trying to connect`

**解决**:
```bash
# 检查当前连接数
docker-compose exec db psql -U football_user -d football_db -c "
    SELECT count(*) FROM pg_stat_activity WHERE usename = 'football_user';
"

# 重启应用释放连接
docker-compose restart dev
```

### 6.3 三道铁门拦截过多

**症状**: 发现比赛数远低于预期

**排查**:
```bash
# 查看详细拦截日志
grep "拦截" logs/combined-$(date +%Y-%m-%d).log

# 检查时间窗口配置
cat config/season_windows.json | jq '.seasons'
```

---

## 7. 版本历史

| 版本 | 日期 | 变更 |
|------|------|------|
| V6.4 | 2026-03-18 | 熔断机制、连接池、100% 测试覆盖 |
| V5.0 | 2026-03-10 | 集成 MatchValidator 三道铁门 |
| V4.0 | 2026-03-01 | 基础 L1 发现功能 |

---

**维护者**: V6 Engineering Team  
**文档状态**: ✅ 已同步最新代码
