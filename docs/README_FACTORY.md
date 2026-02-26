# V173 增量数据工厂 - 生产交付文档

## 📋 概述

增量数据工厂 (Incremental Data Factory) 是一个生产级的数据采集系统，支持：
- **增量模式**：每日自动收割新结束的比赛
- **补漏模式**：自动修复失败的采集任务
- **全量模式**：周期性完整扫描
- **哨兵监控**：自动健康检测和告警

## 🚀 快速启动

### 增量模式 (推荐)
```bash
docker exec football_prediction_dev node scripts/ops/incremental_factory.js
```

### 补漏模式
```bash
docker exec -e FACTORY_MODE=repair football_prediction_dev node scripts/ops/incremental_factory.js
```

### 全量模式
```bash
docker exec -e FACTORY_MODE=full football_prediction_dev node scripts/ops/incremental_factory.js
```

## ⚙️ 配置

### 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `FACTORY_MODE` | `incremental` | 运行模式 |
| `MAX_WORKERS` | `3` | Worker 数量 |
| `PROXY_PORTS` | `7890,7891,7892` | 代理端口池 |
| `MIN_DELAY_MS` | `5000` | 最小延时 (ms) |
| `MAX_DELAY_MS` | `12000` | 最大延时 (ms) |
| `MIN_SIZE_BYTES` | `5000` | 质量门禁最小体积 |
| `MAX_FAILURE_RATE` | `0.10` | 最大失败率 |
| `MAX_CONSECUTIVE_403` | `5` | 最大连续 403 次数 |
| `LOG_RETENTION_DAYS` | `7` | 日志保留天数 |

### 配置文件

```javascript
// config/factory_config.js
module.exports = {
    PROXY_CONFIG: { ... },
    WORKER_CONFIG: { ... },
    QUALITY_GATE: { ... },
    SENTINEL_CONFIG: { ... }
};
```

## 📊 健康监控

### 健康报告位置
```
/app/logs/factory_health.json
```

### 报告结构
```json
{
  "version": "V173-A1",
  "timestamp": "2026-02-27T04:00:00.000Z",
  "mode": "incremental",
  "health": "healthy",
  "alerts": [],
  "metrics": {
    "totalTasks": 50,
    "processed": 50,
    "success": 48,
    "failed": 2,
    "successRate": "96.00%",
    "avgResponseTime": "12s",
    "duration": "600s"
  },
  "errors": [...],
  "cookieStatus": {
    "exists": true,
    "ageHours": 12,
    "fresh": true
  }
}
```

### 健康状态

| 状态 | 说明 | 行动 |
|------|------|------|
| `healthy` | 一切正常 | 无需操作 |
| `degraded` | 失败率 > 10% | 检查日志 |
| `critical` | 连续 403 > 5 次 | **立即更换 Cookie** |

## 🛠️ 常见问题

### Q: 出现 `SIZE_TOO_SMALL` 错误
**A**: 数据体积小于 5KB，可能是 Turnstile 拦截。检查 Cookie 是否有效。

### Q: 出现 `TURNSTILE_REQUIRED` 错误
**A**: 需要重新注入 Cookie。
```bash
# 1. 在浏览器中提取 Cookie
# 2. 注入 Cookie
node scripts/inject_cookie.js "your_cookies"
# 3. 重新运行
```

### Q: 出现 `CONTAINS_ERROR` 错误
**A**: API 返回错误信息。检查代理是否正常。

### Q: 健康状态变为 `critical`
**A**: 立即更换 Cookie，否则会触发自动停止保护。

## 📅 Cron 调度

```bash
# 编辑 crontab
crontab -e

# 添加以下内容
0 4 * * * docker exec football_prediction_dev node scripts/ops/incremental_factory.js >> /var/log/factory/incremental.log 2>&1
0 5 * * * docker exec -e FACTORY_MODE=repair football_prediction_dev node scripts/ops/incremental_factory.js >> /var/log/factory/repair.log 2>&1
```

## 📁 文件结构

```
scripts/ops/
├── incremental_factory.js    # 主程序
├── harvest_worker.js         # Worker 进程
└── harvest_fleet_master.js   # 旧版 (已弃用)

config/
└── factory_config.js         # 配置文件

src/infrastructure/repositories/
└── FactoryQueries.js         # SQL 查询

logs/
├── factory_health.json       # 健康报告
└── factory_*.log            # 运行日志

data/browser_profile/
└── browser_state.json        # Cookie 存储
```

## 🔒 安全注意事项

1. **Cookie 保护**：`browser_state.json` 包含敏感信息，不要提交到版本控制
2. **代理安全**：确保代理端口仅内网可访问
3. **日志脱敏**：日志中不包含 Cookie 内容

## 📈 性能优化

| 参数 | 调优建议 |
|------|----------|
| `MAX_WORKERS` | 根据代理 IP 数量设置，建议 ≤ IP 数量 |
| `MIN_DELAY_MS` | 网络稳定时可以减小 |
| `MIN_SIZE_BYTES` | 不要低于 5000 |

## 🆘 紧急操作

### 立即停止工厂
```bash
docker exec football_prediction_dev pkill -f incremental_factory
```

### 清理坏账数据
```sql
DELETE FROM raw_match_data
WHERE LENGTH(l2_raw_json::text) < 5000
   OR l2_raw_json::text LIKE '%error%';
```

### 重置 Cookie
```bash
rm /app/data/browser_profile/browser_state.json
node scripts/inject_cookie.js "new_cookies"
```

---

**版本**: V173.200
**更新日期**: 2026-02-27
**维护者**: Claude AI
