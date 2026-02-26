# V172-FINAL 交付清单

> **版本**: V172.100 (Production Ready)
> **日期**: 2026-02-27
> **状态**: 已通过 PRR (Production Readiness Review)

---

## 1. 核心表结构定义

### 1.1 matches (比赛索引表)

```sql
CREATE TABLE matches (
    match_id          VARCHAR(50) PRIMARY KEY,
    external_id       VARCHAR(50),           -- FotMob Match ID
    home_team         VARCHAR(100) NOT NULL,
    away_team         VARCHAR(100) NOT NULL,
    league_name       VARCHAR(100),
    match_date        TIMESTAMP,
    status            VARCHAR(20),            -- scheduled/finished/cancelled

    -- L2 解析字段
    xg_home           DECIMAL(5,2),
    xg_away           DECIMAL(5,2),

    -- 元数据
    created_at        TIMESTAMP DEFAULT NOW(),
    updated_at        TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_matches_external_id ON matches(external_id);
CREATE INDEX idx_matches_status ON matches(status);
CREATE INDEX idx_matches_date ON matches(match_date);
```

### 1.2 raw_match_data (原始数据表)

```sql
CREATE TABLE raw_match_data (
    match_id          VARCHAR(50) PRIMARY KEY REFERENCES matches(match_id),
    l2_raw_json       JSONB,                  -- 完整的 FotMob API 响应
    collected_at      TIMESTAMP,

    -- 质量检查
    CONSTRAINT valid_json CHECK (l2_raw_json IS NOT NULL)
);

CREATE INDEX idx_raw_collected ON raw_match_data(collected_at);
```

### 1.3 metrics_multi_source_data (多源指标表)

```sql
CREATE TABLE metrics_multi_source_data (
    id                SERIAL PRIMARY KEY,
    match_id          VARCHAR(50) REFERENCES matches(match_id),
    source            VARCHAR(50),            -- FotMob/OddsPortal
    metric_type       VARCHAR(50),            -- l2_stats/odds
    metric_value      JSONB,
    collected_at      TIMESTAMP DEFAULT NOW(),

    UNIQUE(match_id, source, metric_type)
);
```

---

## 2. 生产运行命令

### 2.1 环境准备

```bash
# 1. 启动核心服务
docker-compose up -d db redis

# 2. 启动开发容器
docker-compose -f docker-compose.dev.yml up -d

# 3. 验证数据库连接
docker-compose exec db psql -U football_user -d football_db -c "SELECT 1"
```

### 2.2 数据收割

```bash
# 标准收割模式 (50 场批量)
docker-compose exec dev node scripts/ops/harvest_fleet_master.js

# 查看收割进度 (实时仪表盘)
# 仪表盘会在终端自动显示

# 检查收割结果
docker-compose exec db psql -U football_user -d football_db -c "
    SELECT
        COUNT(*) as total,
        COUNT(l2_raw_json) as harvested,
        COUNT(*) FILTER (WHERE LENGTH(l2_raw_json::text) > 5000) as valid
    FROM raw_match_data
"
```

### 2.3 数据验证

```bash
# 验证数据质量
docker-compose exec db psql -U football_user -d football_db -c "
    SELECT
        m.home_team,
        m.away_team,
        m.xg_home,
        m.xg_away,
        LENGTH(r.l2_raw_json::text) as json_size
    FROM matches m
    JOIN raw_match_data r ON m.match_id = r.match_id
    WHERE LENGTH(r.l2_raw_json::text) > 5000
    ORDER BY m.match_date DESC
    LIMIT 10
"
```

### 2.4 配置调整

```bash
# 查看当前配置
docker-compose exec dev node -e "
    const cfg = require('/app/config/factory_config');
    console.log('延时范围:', cfg.TIMING.minDelayMs, '-', cfg.TIMING.maxDelayMs, 'ms');
    console.log('质量门禁:', cfg.QUALITY_GATE.minSizeBytes, 'bytes');
    console.log('重试次数:', cfg.RETRY.maxAttempts);
    console.log('Worker 数量:', cfg.CONCURRENCY.maxWorkers);
"

# 通过环境变量调整配置
docker-compose exec -e MIN_DELAY_MS=8000 -e MAX_DELAY_MS=15000 dev node scripts/ops/harvest_fleet_master.js
```

---

## 3. 异常排查手册

### 3.1 代理熔断 (Connection Refused)

**症状:**
```
Error: connect ECONNREFUSED 172.25.16.1:7890
```

**诊断:**
```bash
# 1. 检查代理服务状态
curl -x http://172.25.16.1:7890 https://httpbin.org/ip

# 2. 检查 Clash 是否运行
# (在宿主机上检查 Clash Verge)
```

**解决方案:**
```bash
# 方案 1: 重启开发容器
docker-compose restart dev

# 方案 2: 重置代理健康状态
docker-compose exec dev node -e "
    const cfg = require('/app/config/factory_config');
    console.log('可用代理端口:', cfg.PROXY_CONFIG.ports);
"

# 方案 3: 更换代理端口
docker-compose exec -e PROXY_PORTS=7895,7896,7897 dev node scripts/ops/harvest_fleet_master.js
```

---

### 3.2 质量门禁拦截 (SIZE_TOO_SMALL)

**症状:**
```
🚫 质量门禁拦截: SIZE_TOO_SMALL (size: 1200)
```

**可能原因:**
1. 比赛数据尚未生成 (未开始)
2. API 返回了错误信息
3. 网络问题导致数据截断

**解决方案:**
```bash
# 1. 检查数据内容
docker-compose exec db psql -U football_user -d football_db -c "
    SELECT match_id, l2_raw_json::text
    FROM raw_match_data
    WHERE LENGTH(l2_raw_json::text) < 5000
    LIMIT 1
"

# 2. 手动重试单场比赛
docker-compose exec dev node -e "
    const { MatchDetailEngine } = require('/app/src/domain/services/harvesting/MatchDetailEngine');
    const engine = new MatchDetailEngine();
    engine.harvestMatch({
        match_id: 'xxx',
        external_id: '1234567',
        home_team: 'Team A',
        away_team: 'Team B'
    }).then(console.log).finally(() => engine.close());
"

# 3. 调整质量门禁阈值 (不推荐)
docker-compose exec -e MIN_SIZE_BYTES=3000 dev node scripts/ops/harvest_fleet_master.js
```

---

### 3.3 Turnstile 拦截

**症状:**
```
检测到 Turnstile 拦截
CONTAINS_TURNSTILE
```

**可能原因:**
1. 请求频率过高
2. 浏览器指纹被识别
3. Cookie 过期

**解决方案:**
```bash
# 1. 增加延时
docker-compose exec -e MIN_DELAY_MS=10000 -e MAX_DELAY_MS=20000 dev node scripts/ops/harvest_fleet_master.js

# 2. 重新捕获认证状态
docker-compose exec dev node scripts/capture_auth.js

# 3. 检查 Cookie 状态
docker-compose exec dev ls -la /app/data/browser_profile/

# 4. 减少并发数
docker-compose exec -e MAX_WORKERS=2 dev node scripts/ops/harvest_fleet_master.js
```

---

### 3.4 数据库连接超时

**症状:**
```
Error: Connection terminated unexpectedly
Error: connect ETIMEDOUT
```

**诊断:**
```bash
# 1. 检查数据库状态
docker-compose ps db

# 2. 检查连接数
docker-compose exec db psql -U football_user -d football_db -c "
    SELECT count(*) FROM pg_stat_activity WHERE datname = 'football_db'
"

# 3. 检查连接池
docker-compose exec db psql -U football_user -d football_db -c "
    SELECT state, count(*)
    FROM pg_stat_activity
    WHERE datname = 'football_db'
    GROUP BY state
"
```

**解决方案:**
```bash
# 方案 1: 重启数据库
docker-compose restart db

# 方案 2: 清理空闲连接
docker-compose exec db psql -U football_user -d football_db -c "
    SELECT pg_terminate_backend(pid)
    FROM pg_stat_activity
    WHERE datname = 'football_db'
      AND state = 'idle'
      AND query_start < NOW() - INTERVAL '5 minutes'
"

# 方案 3: 调整连接池配置
docker-compose exec -e DB_POOL_MAX=5 -e DB_IDLE_TIMEOUT=60000 dev node scripts/ops/harvest_fleet_master.js
```

---

### 3.5 Worker 进程异常退出

**症状:**
```
⚠️ Worker 3 异常退出 (code: 1), 准备重启...
```

**诊断:**
```bash
# 1. 查看 Worker 日志
docker-compose logs dev | grep "Worker 3"

# 2. 检查内存使用
docker stats dev
```

**解决方案:**
```bash
# 方案 1: 减少 Worker 数量
docker-compose exec -e MAX_WORKERS=3 dev node scripts/ops/harvest_fleet_master.js

# 方案 2: 增加重启延迟
docker-compose exec -e WORKER_RESTART_DELAY_MS=60000 dev node scripts/ops/harvest_fleet_master.js

# 方案 3: 检查浏览器资源
docker-compose exec dev pkill -f chromium
```

---

## 4. 配置参考

### 4.1 环境变量完整列表

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `MIN_DELAY_MS` | 5000 | 最小延时 (ms) |
| `MAX_DELAY_MS` | 12000 | 最大延时 (ms) |
| `MIN_SIZE_BYTES` | 5000 | 质量门禁阈值 (bytes) |
| `MAX_WORKERS` | 5 | 最大 Worker 数量 |
| `MAX_RETRY_ATTEMPTS` | 3 | 最大重试次数 |
| `CIRCUIT_BREAKER_THRESHOLD` | 3 | 熔断阈值 |
| `PROXY_PORTS` | 7890-7894 | 代理端口池 |
| `COOKIE_SAVE_INTERVAL` | 3 | Cookie 保存间隔 |
| `DB_CONNECT_TIMEOUT` | 10000 | 数据库连接超时 (ms) |
| `LOG_LEVEL` | info | 日志级别 |

### 4.2 配置文件位置

```
config/
├── factory_config.js      # 工厂级配置中心
├── database.js            # 数据库连接配置
└── active_registry.json   # 代理池配置
```

---

## 5. 验收确认

- [x] **配置标准化**: 所有魔术数字已提取到 `factory_config.js`
- [x] **异常自愈闭环**: 质量门禁失败任务自动回队重试
- [x] **连接池管理**: 所有异常分支确保 100% 资源释放
- [x] **交付文档**: 表结构、运行命令、异常手册已补齐
- [x] **代码审查**: 注释完整，结构清晰

---

**V172 版本已达到大厂生产交付标准，原始数据入库链路已完全闭环。**

---

*Generated by V172 Engineering Team*
