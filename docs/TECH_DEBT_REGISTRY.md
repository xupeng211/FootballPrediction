# V171 技术债自查报告 (Tech Debt Registry)

**审计日期**: 2026-02-25
**审计范围**: V171 全量代码
**审计人**: V171 Architecture Team

---

## 1. 技术债清单

### 1.1 硬编码配置 (Hardcoded Configurations)

| 文件 | 问题 | 严重程度 | V172 优化建议 |
|------|------|----------|---------------|
| `v171_l1_api_fetch.js` | 请求间隔 2000ms 硬编码 | 中 | 迁移到 `config/harvest_settings.json` |
| `QuantHarvester.js` | 超时时间 75000ms 硬编码 | 中 | 使用 `HarvestConfig` 配置 |
| `SignalRadar.js` | 重试次数 3 次硬编码 | 低 | 使用 `RetryConfig` 配置 |
| `storage.js` | 连接池大小 20 硬编码 | 低 | 使用环境变量 |

**示例修复**:
```javascript
// ❌ 当前 (Bad)
await new Promise(r => setTimeout(r, 2000));

// ✅ V172 建议
const { HarvestConfig } = require('../../config/harvest_settings');
await new Promise(r => setTimeout(r, HarvestConfig.requestDelayMs));
```

### 1.2 简单错误重试 (Naive Retry Logic)

| 文件 | 问题 | 严重程度 | V172 优化建议 |
|------|------|----------|---------------|
| `v171_l1_api_fetch.js` | 无重试机制 | 高 | 实现 `withRetry` 包装器 |
| `QuantHarvester.js` | 仅重试 1 次 | 中 | 实现指数退避 |
| `FundamentalHarvester.js` | 捕获异常后无重试 | 中 | 添加重试装饰器 |

**示例修复**:
```javascript
// ❌ 当前 (Bad)
try {
    const response = await fetch(url);
} catch (e) {
    log.error(e.message);
}

// ✅ V172 建议
const { withRetry } = require('../lib/retry');
const response = await withRetry(
    () => fetch(url),
    { maxAttempts: 3, delay: 1000, backoff: 'exponential' }
);
```

### 1.3 魔法数字 (Magic Numbers)

| 文件 | 位置 | 魔法数字 | 含义 |
|------|------|----------|------|
| `v171_l1_api_fetch.js` | Line ~197 | `2000` | 请求间隔 (ms) |
| `QuantHarvester.js` | 多处 | `5` | 并发数 |
| `SignalRadar.js` | 多处 | `20`, `75` | 超时相关 |
| `storage.js` | 多处 | `100` | 批量大小 |

**V172 优化建议**:
```javascript
// 创建 config/constants.js
module.exports = {
    REQUEST_DELAY_MS: 2000,
    MAX_CONCURRENT: 5,
    TIMEOUT_MS: 75000,
    BATCH_SIZE: 100
};
```

### 1.4 错误处理不完整 (Incomplete Error Handling)

| 场景 | 当前行为 | V172 建议 |
|------|----------|-----------|
| API 返回 500 | 抛出异常 | 区分 5xx 和 4xx |
| 数据库连接失败 | 直接退出 | 实现连接池重连 |
| 网络超时 | 抛出通用错误 | 区分超时类型 |

### 1.5 日志不一致 (Inconsistent Logging)

| 问题 | 位置 | V172 建议 |
|------|------|-----------|
| 混用 console.log 和 logger | 多处 | 统一使用 `RadarLogger` |
| 缺少 trace_id | 多处 | 添加请求追踪 |
| 中文/英文混用 | 多处 | 统一中文 |

---

## 2. 架构债务

### 2.1 模块耦合

```
当前状态:
QuantHarvester.js → 直接依赖 storage.js, NetworkShield.js
FundamentalHarvester.js → 直接依赖 pg.Client

V172 目标:
QuantHarvester → DatabaseService (抽象层)
FundamentalHarvester → DatabasePool (统一接口)
```

### 2.2 配置分散

| 配置位置 | 文件数 | V172 建议 |
|----------|--------|-----------|
| 硬编码在代码中 | 15+ | 迁移到 `config/` |
| 环境变量 | 8 | 统一 `config/settings.js` |
| JSON 配置文件 | 5 | 合并为 `config/app.json` |

### 2.3 测试覆盖不足

| 模块 | 当前覆盖率 | 目标覆盖率 |
|------|-----------|-----------|
| `v171_l1_api_fetch.js` | 85% (新增) | 95% |
| `QuantHarvester.js` | ~40% | 80% |
| `storage.js` | ~30% | 70% |
| `SignalRadar.js` | ~20% | 60% |

---

## 3. 性能债务

### 3.1 同步操作

| 问题 | 位置 | 影响 | V172 建议 |
|------|------|------|-----------|
| 同步数据库写入 | `upsertMatch` | 阻塞 | 批量写入 |
| 同步 API 调用 | `fetchLeagueSeason` | 低吞吐 | 并发请求 |

### 3.2 内存泄漏风险

| 风险点 | 位置 | V172 建议 |
|--------|------|-----------|
| 未关闭的 Playwright 页面 | `QuantHarvester` | 确保 `page.close()` |
| 未释放的数据库连接 | 多处 | 使用连接池 |
| 缓存无限增长 | `NetworkShield` | 添加 LRU 淘汰 |

---

## 4. 安全债务

### 4.1 已修复

- ✅ 硬编码密码 (V172 已统一到 `config/database.js`)
- ✅ SQL 注入 (使用参数化查询)

### 4.2 待修复

| 问题 | 位置 | 优先级 | V172 建议 |
|------|------|--------|-----------|
| API 无认证 | FotMob API | 低 | 添加 API Key 支持 |
| 日志包含敏感信息 | 多处 | 中 | 脱敏处理 |

---

## 5. V172 优化路线图

### 5.1 第一优先级 (P0)

1. **配置集中化**
   - 创建 `config/harvest_settings.json`
   - 消除所有魔法数字

2. **重试机制标准化**
   - 实现 `lib/retry.js` 模块
   - 所有 API 调用使用 `withRetry`

### 5.2 第二优先级 (P1)

3. **日志标准化**
   - 统一使用 `RadarLogger`
   - 添加 `trace_id` 支持

4. **测试覆盖提升**
   - QuantHarvester 测试覆盖率达到 80%

### 5.3 第三优先级 (P2)

5. **性能优化**
   - 批量数据库写入
   - 并发 API 请求

---

## 6. 技术债统计

| 类别 | 数量 | 预计修复时间 |
|------|------|--------------|
| 硬编码配置 | 8 处 | 2 小时 |
| 简单重试 | 5 处 | 4 小时 |
| 魔法数字 | 12 处 | 1 小时 |
| 错误处理 | 6 处 | 3 小时 |
| 日志不一致 | 15+ 处 | 2 小时 |
| **总计** | **46+ 处** | **12 小时** |

---

**审计结论**: V171 版本存在一定技术债，但不影响核心功能稳定性。建议在 V172 版本中逐步清理，优先解决 P0 级别问题。

---

**维护者**: V171 Architecture Team
**下次审计**: V172 发布后
