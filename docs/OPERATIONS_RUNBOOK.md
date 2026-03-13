# TITAN-V4.46.4 运维手册 (Operations Runbook)

**版本**: V4.46.4-HYPER-DRIVE
**最后更新**: 2026-03-09
**维护者**: TITAN-SRE Team

---

## 📋 目录

1. [系统概览](#系统概览)
2. [快速诊断](#快速诊断)
3. [故障-对策矩阵](#故障-对策矩阵)
4. [日常运维](#日常运维)
5. [紧急恢复](#紧急恢复)

---

## 系统概览

### 架构简图

```
┌─────────────────────────────────────────────────────────────────┐
│                    TITAN-V4.46.4 HYPER-DRIVE                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐         │
│  │  L1 Discovery│───▶│  L2 Harvest │───▶│  L3 Smelt   │         │
│  │  (FotMob)   │    │  (22 Proxy) │    │  (Features) │         │
│  └─────────────┘    └─────────────┘    └─────────────┘         │
│         │                  │                  │                 │
│         ▼                  ▼                  ▼                 │
│  ┌─────────────────────────────────────────────────────┐       │
│  │              PostgreSQL (1900 场比赛)               │       │
│  │  matches | raw_match_data | l3_features             │       │
│  └─────────────────────────────────────────────────────┘       │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 核心组件

| 组件 | 位置 | 端口 | 健康检查 |
|------|------|------|----------|
| PostgreSQL | Docker `db` | 5432 | `pg_isready -U football_user` |
| Redis | Docker `redis` | 6379 | `redis-cli ping` |
| Dev Container | Docker `dev` | 8000 | `curl localhost:8000/health` |

### 代理池配置

| 节点范围 | 用途 | 数量 |
|----------|------|------|
| 7890-7911 | 数据收割 | 22 个独立 IP |

---

## 快速诊断

### 一键健康检查

```bash
# 执行完整系统诊断
docker-compose -f docker-compose.dev.yml exec dev python scripts/maintenance/integrity_guard.py

# 预期输出:
# ✅ L1=1900, L2=1900, L3=1900
# ✅ 数据完整性: 100%
```

### 关键指标查询

```sql
-- 查看收割进度
SELECT
    (SELECT COUNT(*) FROM matches) as L1,
    (SELECT COUNT(*) FROM raw_match_data) as L2,
    (SELECT COUNT(*) FROM l3_features) as L3;

-- 查看待收割比赛
SELECT COUNT(*) FROM matches m
LEFT JOIN raw_match_data r ON m.match_id = r.match_id
WHERE r.match_id IS NULL;

-- 查看代理池状态
SELECT * FROM proxy_health ORDER BY last_check DESC LIMIT 22;
```

---

## 故障-对策矩阵

### 🔴 故障 A: CIRCUIT_BREAKER_OPEN (全线熔断)

**症状**:

```
🚨 全局熔断：所有代理节点不可用 (已重试 3 次)
CIRCUIT_BREAKER_OPEN: 所有代理节点不可用，全局熔断已开启
```

**根因分析**:

- 代理服务器宕机
- 网络中断
- 代理端口配置错误

**对策流程**:

```bash
# Step 1: 检查代理节点状态
for port in {7890..7911}; do
    curl -x http://172.25.16.1:$port https://httpbin.org/ip --connect-timeout 5 && echo "Port $port: OK" || echo "Port $port: FAILED"
done

# Step 2: 验证 .env 端口范围
grep PROXY_PORTS .env
# 预期: PROXY_PORTS=7890,7891,...,7911

# Step 3: 检查代理服务状态 (宿主机)
systemctl status clash  # 或你的代理服务

# Step 4: 等待 60s 冷却后重试
# 熔断器会在 60 秒后自动恢复
sleep 60

# Step 5: 重新启动收割
docker-compose -f docker-compose.dev.yml exec dev node scripts/ops/hyper_swarm.js
```

**预防措施**:

- 配置代理服务自动重启
- 设置 Prometheus 告警规则
- 定期执行代理健康检查

---

### 🟠 故障 B: SIZE_TOO_SMALL 错误 (403 拦截)

**症状**:

```
❌ SIZE_TOO_SMALL:160
[FotMobStrategy] 响应状态: 403
[FotMobStrategy] 响应体大小: 61 字节
```

**根因分析**:

- FotMob 反爬虫检测
- Cookie 过期
- 单 IP 请求频率过高

**对策流程**:

```bash
# Step 1: 切换到低并发模式
docker-compose -f docker-compose.dev.yml exec dev node scripts/ops/hyper_swarm_stealth.js

# Step 2: 如果仍然失败，更新 IdentityStore Cookie
# (需要在宿主机有 X Server 的环境下运行)
node scripts/capture_auth.js

# Step 3: 验证 Cookie 已加载
ls -la /app/data/sessions/
# 应该看到 session_port_7890.json 等文件

# Step 4: 重新尝试收割
docker-compose -f docker-compose.dev.yml exec dev node scripts/ops/hyper_swarm_stealth.js
```

**配置优化**:

```javascript
// 调整 hyper_swarm_stealth.js 配置
const swarm = new SwarmHarvester({
    concurrency: 2,        // 降低到 2 并发
    initStaggerMs: 3000,   // 增加错峰时间
    harvesterOptions: {
        minDelayMs: 8000,  // 增加延迟到 8-15s
        maxDelayMs: 15000,
        maxRetries: 5
    }
});
```

---

### 🟡 故障 C: Python API 无法连接数据库

**症状**:

```
psycopg2.OperationalError: could not connect to server: Connection refused
Is the server running on host "localhost" (127.0.0.1) and accepting TCP/IP connections on port 5432?
```

**根因分析**:

- Docker 网络配置错误
- PostgreSQL 容器未启动
- 防火墙阻断

**对策流程**:

```bash
# Step 1: 验证 Docker 内部网段
docker network inspect footballprediction_default | grep Subnet

# Step 2: 检查 db 容器健康度
docker-compose -f docker-compose.dev.yml exec db pg_isready -U football_user

# Step 3: 检查容器间连通性
docker-compose -f docker-compose.dev.yml exec dev ping -c 3 db

# Step 4: 验证环境变量
docker-compose -f docker-compose.dev.yml exec dev env | grep DB_

# Step 5: 如果仍失败，重启数据库容器
docker-compose -f docker-compose.dev.yml restart db

# Step 6: 等待数据库就绪后重试
sleep 10
docker-compose -f docker-compose.dev.yml exec dev python scripts/ops/smelt_l3.py
```

**正确配置**:

```env
# .env 文件
DB_HOST=db                    # Docker 内部使用服务名
DB_PORT=5432
DB_NAME=football_db
DB_USER=football_user
DB_PASSWORD=your_secure_password
```

---

### 🟢 故障 D: 浏览器启动失败

**症状**:

```
Error: Failed to launch the browser process!
[ERROR] browser: undefined
```

**对策流程**:

```bash
# Step 1: 检查 Playwright 浏览器
docker-compose -f docker-compose.dev.yml exec dev npx playwright install chromium

# Step 2: 验证依赖
docker-compose -f docker-compose.dev.yml exec dev ldd /root/.cache/ms-playwright/chromium-*/chrome

# Step 3: 清理残留进程
docker-compose -f docker-compose.dev.yml exec dev node -e "require('./src/core/process/ZombieKiller').preFlightCleanup(0)"

# Step 4: 重启开发容器
docker-compose -f docker-compose.dev.yml restart dev
```

---

## 日常运维

### 每日检查清单

```bash
# 1. 数据完整性检查
docker-compose -f docker-compose.dev.yml exec dev python scripts/maintenance/integrity_guard.py

# 2. 系统健康状态
docker-compose -f docker-compose.dev.yml ps

# 3. 日志检查 (最近 1 小时的错误)
docker-compose -f docker-compose.dev.yml logs --since 1h dev 2>&1 | grep -i error | tail -20

# 4. 磁盘空间
df -h /var/lib/docker

# 5. 代理池状态
for port in {7890..7911}; do
    timeout 2 curl -x http://172.25.16.1:$port https://httpbin.org/ip &>/dev/null && echo "✅ $port" || echo "❌ $port"
done
```

### 每周维护

```bash
# 1. 数据库备份
docker-compose -f docker-compose.dev.yml exec db pg_dump -U football_user football_db > backup_$(date +%Y%m%d).sql

# 2. 日志轮转
docker-compose -f docker-compose.dev.yml exec dev find /app/logs -name "*.log" -mtime +7 -delete

# 3. 清理 Docker 资源
docker system prune -f

# 4. 更新依赖 (谨慎)
docker-compose -f docker-compose.dev.yml exec dev npm outdated
```

---

## 紧急恢复

### 场景 1: 完全数据丢失

```bash
# 1. 停止所有服务
docker-compose -f docker-compose.dev.yml down

# 2. 恢复数据库
cat backup_YYYYMMDD.sql | docker-compose -f docker-compose.dev.yml exec -T db psql -U football_user football_db

# 3. 重启服务
docker-compose -f docker-compose.dev.yml up -d

# 4. 验证数据完整性
docker-compose -f docker-compose.dev.yml exec dev python scripts/maintenance/integrity_guard.py
```

### 场景 2: 容器无法启动

```bash
# 1. 查看容器状态
docker-compose -f docker-compose.dev.yml ps -a

# 2. 查看容器日志
docker-compose -f docker-compose.dev.yml logs dev

# 3. 重建容器
docker-compose -f docker-compose.dev.yml up -d --force-recreate dev

# 4. 如果仍失败，重新构建镜像
docker-compose -f docker-compose.dev.yml build --no-cache dev
docker-compose -f docker-compose.dev.yml up -d dev
```

### 场景 3: 收割进程卡死

```bash
# 1. 查找卡死的 Node 进程
docker-compose -f docker-compose.dev.yml exec dev ps aux | grep node

# 2. 强制终止
docker-compose -f docker-compose.dev.yml exec dev pkill -9 -f "node scripts/ops"

# 3. 清理僵尸浏览器进程
docker-compose -f docker-compose.dev.yml exec dev pkill -9 chromium

# 4. 清理锁文件
docker-compose -f docker-compose.dev.yml exec dev rm -f /app/data/network/*.lock /app/config/*.lock

# 5. 重新启动
docker-compose -f docker-compose.dev.yml exec dev node scripts/ops/hyper_swarm.js
```

---

## 联系信息

| 角色 | 联系方式 |
|------|----------|
| SRE On-Call | <sre@titan.example.com> |
| 开发团队 | <dev@titan.example.com> |
| 紧急热线 | +86-xxx-xxxx-xxxx |

---

**文档版本历史**:

- V4.46.4 (2026-03-09): 初始版本，Hyper-Drive 架构
