# V174-REFRESH 运维手册

> **版本**: V174.0.0 | **最后更新**: 2026-03-01

---

## 1. 快速启动

### 1.1 启动开发环境

```bash
# 启动 Docker 容器
docker-compose -f docker-compose.dev.yml up -d

# 进入开发容器
docker-compose -f docker-compose.dev.yml exec dev bash
```

### 1.2 启动收割集群

```bash
# 默认配置 (1 Worker, 最稳模式)
docker-compose -f docker-compose.dev.yml exec dev npm run harvest

# 自定义 Worker 数量
docker-compose -f docker-compose.dev.yml exec -e MAX_WORKERS=5 dev npm run harvest

# 限制收割场次
docker-compose -f docker-compose.dev.yml exec dev npm run harvest:limit 10

# 自定义延时
docker-compose -f docker-compose.dev.yml exec \
    -e MIN_DELAY_MS=8000 \
    -e MAX_DELAY_MS=15000 \
    dev npm run harvest
```

---

## 2. 集群配置

### 2.1 核心参数

| 参数 | 环境变量 | 默认值 | 说明 |
|------|----------|--------|------|
| Worker 数量 | `MAX_WORKERS` | 1 | 最大 22 (对应代理端口数) |
| 最小延时 | `MIN_DELAY_MS` | 10000 | 潜行模式，避免封禁 |
| 最大延时 | `MAX_DELAY_MS` | 15000 | 随机抖动上限 |
| 错峰启动 | `STAGGER_START_MS` | 10000 | Worker 间隔 10 秒启动 |
| 质量门禁 | `MIN_SIZE_BYTES` | 5000 | 最小有效数据体积 |
| 熔断阈值 | `CIRCUIT_BREAKER_THRESHOLD` | 5 | 连续失败次数触发熔断 |

### 2.2 代理配置

```bash
# 22 个独立 IP 代理端口
PROXY_PORTS=7890,7891,7892,...,7911

# 代理服务器地址
PROXY_HOST=172.25.16.1
PROXY_SERVER=http://172.25.16.1:{port}
```

### 2.3 推荐配置

| 场景 | Worker 数量 | 延时范围 | 说明 |
|------|-------------|----------|------|
| **最稳模式** | 1 | 10-15s | 最低封禁风险 |
| **平衡模式** | 3-5 | 8-15s | 效率与稳定性兼顾 |
| **极速模式** | 10-22 | 5-10s | 高风险，仅限紧急情况 |

---

## 3. 日志与监控

### 3.1 实时状态文件

```bash
# 查看实时状态
docker-compose -f docker-compose.dev.yml exec dev cat /app/logs/live_status.json

# 持续监控
watch -n 5 'docker-compose -f docker-compose.dev.yml exec -T dev cat /app/logs/live_status.json'
```

**状态文件结构:**
```json
{
  "version": "V174.0.0",
  "timestamp": "2026-03-01T10:30:00.000Z",
  "total": 100,
  "processed": 45,
  "success": 42,
  "failed": 3,
  "progressPct": "45.0",
  "elapsedMs": 450000,
  "workers": {
    "1": { "status": "RUNNING", "port": 7890, "success": 20 },
    "2": { "status": "READY", "port": 7891, "success": 22 }
  }
}
```

### 3.2 日志文件

```bash
# 收割日志
docker-compose -f docker-compose.dev.yml exec dev tail -f /app/logs/harvest.log

# 错误日志
docker-compose -f docker-compose.dev.yml exec dev cat /app/logs/error.log | tail -100

# Docker 容器日志
docker-compose -f docker-compose.dev.yml logs -f dev
```

---

## 4. 故障排查

### 4.1 代理故障

**症状:** 大量 `CF_BLOCK` 或 `SIZE_TOO_SMALL` 错误

**排查步骤:**
```bash
# 1. 测试单个代理
curl -x http://172.25.16.1:7890 https://httpbin.org/ip

# 2. 检查所有代理
for port in {7890..7911}; do
    echo -n "Port $port: "
    curl -x http://172.25.16.1:$port --connect-timeout 5 https://httpbin.org/ip 2>/dev/null | jq -r '.origin' || echo "FAILED"
done

# 3. 重置代理健康状态
docker-compose -f docker-compose.dev.yml restart dev
```

### 4.2 Worker 熔断

**症状:** 日志显示 `Worker X 触发熔断`

**解决方案:**
```bash
# 等待自动恢复 (默认 30 秒)
# 或手动重启
docker-compose -f docker-compose.dev.yml restart dev
```

### 4.3 数据库连接问题

**症状:** `ECONNREFUSED` 或 `Connection terminated unexpectedly`

**排查步骤:**
```bash
# 1. 检查数据库状态
docker-compose -f docker-compose.dev.yml exec db pg_isready -U football_user

# 2. 测试连接
docker-compose -f docker-compose.dev.yml exec dev node -e "
const { Client } = require('pg');
const client = new Client({ host: 'db', port: 5432, database: 'football_db', user: 'football_user', password: process.env.DB_PASSWORD });
client.connect().then(() => { console.log('OK'); process.exit(0); }).catch(e => { console.error(e.message); process.exit(1); });
"

# 3. 重启数据库
docker-compose -f docker-compose.dev.yml restart db
```

### 4.4 僵尸进程

**症状:** 内存占用异常，CPU 100%

**解决方案:**
```bash
# 查找僵尸进程
ps aux | grep -E "chrome|chromium|harvest"

# 强制清理
pkill -9 -f "chrome|chromium"
pkill -9 -f "harvest_worker"
pkill -9 -f "harvest_fleet_master"

# 重启容器
docker-compose -f docker-compose.dev.yml restart dev
```

---

## 5. 性能调优

### 5.1 数据库连接池

```bash
# 增加连接池大小 (高并发场景)
DB_POOL_MAX=20
DB_POOL_MIN=5
DB_IDLE_TIMEOUT=30000
```

### 5.2 浏览器资源

```bash
# 减少内存占用 (低配服务器)
# 已在 BrowserManager 中配置:
# --js-flags=--max-old-space-size=256
# --disable-gpu
# --disable-dev-shm-usage
```

### 5.3 并发策略

| 并发数 | 内存需求 | CPU 需求 | 网络带宽 | 推荐场景 |
|--------|----------|----------|----------|----------|
| 1 | 512MB | 1 核 | 低 | 测试/调试 |
| 5 | 2GB | 2 核 | 中 | 日常收割 |
| 10 | 4GB | 4 核 | 高 | 批量回填 |
| 22 | 8GB+ | 8 核 | 极高 | 紧急任务 |

---

## 6. 常用命令速查

```bash
# === 启动/停止 ===
docker-compose -f docker-compose.dev.yml up -d          # 启动
docker-compose -f docker-compose.dev.yml down           # 停止
docker-compose -f docker-compose.dev.yml restart dev    # 重启开发容器

# === 收割 ===
npm run harvest              # 批量收割
npm run harvest:limit 10     # 限制 10 场
npm run harvest:quick        # 快速测试

# === 监控 ===
npm run watch                # 启动监控大屏
cat /app/logs/live_status.json  # 查看实时状态

# === 数据库 ===
docker-compose -f docker-compose.dev.yml exec db psql -U football_user -d football_db

# === 日志 ===
tail -f /app/logs/harvest.log
cat /app/logs/error.log | tail -100
```

---

## 7. 告警与通知

### 7.1 关键告警指标

| 指标 | 阈值 | 说明 |
|------|------|------|
| 失败率 | > 10% | 检查代理/网络 |
| 连续 403 | > 5 次 | 可能被封禁 |
| Worker 熔断 | > 2 个 | 系统过载 |
| 内存使用 | > 80% | 需要扩容 |

### 7.2 告警配置

在 `.env` 中配置:
```bash
# 告警邮件 (可选)
ALERT_EMAIL=your-email@example.com

# 健康报告路径
HEALTH_REPORT_PATH=/app/logs/factory_health.json
```
