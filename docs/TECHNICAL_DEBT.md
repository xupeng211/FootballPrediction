# V171 技术债务清单 (Technical Debt Backlog)

> **审计日期**: 2026-02-25
> **审计范围**: 代码质量、DRY、错误处理、数据验证、测试质量

---

## 🔴 高优先级 (P0) - 需立即修复

### 1. DRY 违规: 数据库连接代码分散

**问题**: 8 个文件中重复实现数据库连接逻辑

```
scripts/ops/v171_live_fire.js
scripts/ops/v171_live_harvest.js
scripts/ops/v171_mass_harvest.js
scripts/ops/v171_production_harvest.js
scripts/ops/v171_quick_harvest.js
scripts/ops/v171_real_fire.js
scripts/ops/v171_real_url_extractor.js
scripts/ops/v171_scheduler.js
```

**影响**:
- 修改数据库配置需要改 8 个文件
- 容易出现不一致
- 违反 DRY 原则

**建议**:
- 统一使用 `config/database.js` 模块
- 创建 `getDbConnection()` 工厂函数

---

### 2. DRY 违规: URL 提取器双版本

**问题**: Node.js 和 Python 双版本实现相同功能

```
scripts/ops/v171_real_url_extractor.js  (Node.js)
scripts/ops/v171_real_url_extractor.py  (Python)
```

**影响**:
- 维护成本翻倍
- 行为可能不一致

**建议**:
- 保留 Node.js 版本 (与收割流程一致)
- Python 版本标记为废弃

---

### 3. 错误处理: 缺少重试策略

**问题**: 所有 catch 块只打印日志，无重试

```javascript
// 当前实现
catch (e) {
    console.error('❌ FATAL ERROR:', e.message);
    // 无重试!
}
```

**影响**:
- 网络抖动导致整个流程失败
- 需要手动重启

**建议**:
- 实现 `withRetry(fn, maxRetries, delay)` 包装器
- 区分可重试错误和不可重试错误

---

## 🟠 中优先级 (P1) - 本周修复

### 4. 错误处理: 缺少 Timeout

**问题**: 异步操作没有超时保护

```javascript
// 当前实现 (无超时)
await this.client.connect();
await page.goto(url);
```

**影响**:
- 挂起风险
- 资源泄漏

**建议**:
- 所有网络操作添加 timeout
- 使用 `Promise.race([op, timeout(ms)])`

---

### 5. 数据验证: 缺少 Schema 校验

**问题**: 网络数据直接写入数据库，无校验

```javascript
// 当前实现 (裸奔)
await client.query(`
    INSERT INTO predictions (...)
    VALUES ($1, $2, ...)
`, [match_id, result, confidence]);  // 无校验!
```

**影响**:
- 脏数据风险
- 类型不匹配导致运行时错误

**建议**:
- 创建 `PredictionSchema` 使用 Zod/Joi
- 写入前验证: `validatePrediction(data)`

---

### 6. 函数复杂度: 超大文件

**问题**: 部分文件过大，难以维护

| 文件 | 行数 | 风险 |
|------|------|------|
| v171_scheduler.js | 805 | 高 |
| v171_mass_harvest.js | 705 | 高 |
| QuantHarvester.js | 595 | 中 |

**影响**:
- 难以理解
- 测试困难
- 容易引入 Bug

**建议**:
- 拆分为多个小模块
- 单一职责原则

---

## 🟡 低优先级 (P2) - 下周修复

### 7. 测试质量: Mock 机制不完善

**问题**: 测试覆盖率虽高，但 Mock 使用有限

```
tests/test_v171_cpp_bridge.py: 10 个 Mock
tests/test_v171_integration.py: 12 个 Mock
```

**影响**:
- 集成测试可能依赖真实环境
- CI/CD 不稳定

**建议**:
- 所有外部依赖 Mock
- 使用 fixture 隔离测试数据

---

### 8. 环境变量: 分散读取

**问题**: 环境变量读取点分散在 8 个文件

```
v171_live_fire.js: 5 处
v171_mass_harvest.js: 8 处
...
```

**影响**:
- 配置难以追踪
- 环境不一致风险

**建议**:
- 集中在 `config/database.js`
- 启动时验证必需变量

---

## 📊 技术债务汇总

| 优先级 | 问题数 | 预计工时 |
|--------|--------|----------|
| P0 (高) | 3 | 16h |
| P1 (中) | 3 | 12h |
| P2 (低) | 2 | 8h |
| **总计** | **8** | **36h** |

---

## 🎯 需重构的 3 个病灶文件

### 1. scripts/ops/v171_mass_harvest.js (705 行)

**问题**:
- 文件过大
- 数据库连接重复
- 错误处理不完善

**重构方向**:
- 拆分为: `HarvestOrchestrator.js`, `HarvestRepository.js`
- 使用 `config/database.js`
- 添加重试策略

---

### 2. scripts/ops/v171_scheduler.js (805 行)

**问题**:
- 最大文件
- 包含调度、收割、数据库逻辑

**重构方向**:
- 拆分为: `Scheduler.js`, `TaskQueue.js`, `HealthChecker.js`
- 单一职责

---

### 3. src/infrastructure/engines/QuantHarvester.js (595 行)

**问题**:
- 核心引擎复杂度高
- 缺少超时控制

**重构方向**:
- 提取: `PageNavigator.js`, `DataExtractor.js`, `ProxyManager.js`
- 所有网络操作添加 timeout

---

## 📋 重构建议方案

### 第一阶段 (P0): 统一数据库连接 (4h)

```javascript
// 创建 scripts/ops/lib/db.js
const { DatabaseConfig } = require('../../config/database');

async function getDbConnection() {
    const { Client } = require('pg');
    const client = new Client({
        host: DatabaseConfig.host,
        port: DatabaseConfig.port,
        database: DatabaseConfig.database,
        user: DatabaseConfig.user,
        password: DatabaseConfig.password
    });
    await client.connect();
    return client;
}

module.exports = { getDbConnection };
```

### 第二阶段 (P0): 实现重试包装器 (4h)

```javascript
// 创建 scripts/ops/lib/retry.js
async function withRetry(fn, maxRetries = 3, delay = 1000) {
    let lastError;
    for (let i = 0; i < maxRetries; i++) {
        try {
            return await fn();
        } catch (e) {
            lastError = e;
            if (i < maxRetries - 1) {
                await new Promise(r => setTimeout(r, delay * (i + 1)));
            }
        }
    }
    throw lastError;
}
```

### 第三阶段 (P1): 添加超时包装器 (2h)

```javascript
// 创建 scripts/ops/lib/timeout.js
function withTimeout(promise, ms) {
    return Promise.race([
        promise,
        new Promise((_, reject) =>
            setTimeout(() => reject(new Error('Timeout')), ms)
        )
    ]);
}
```

---

*最后更新: 2026-02-25*
