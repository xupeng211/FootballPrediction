# TITAN-V4.46.6 故障排查手册

> **版本**: V4.46.6-INDUSTRIAL | **最后更新**: 2026-03-09

本文档涵盖生产环境中最常见的四类故障及其解决方案。

---

## 目录

1. [网络封锁 (Network Blocking)](#1-网络封锁-network-blocking)
2. [数据库不对齐 (Data Misalignment)](#2-数据库不对齐-data-misalignment)
3. [内存溢出 (OOM)](#3-内存溢出-oom)
4. [监控断连 (Monitoring Disconnection)](#4-监控断连-monitoring-disconnection)

---

## 1. 网络封锁 (Network Blocking)

### 症状

- `Playwright` 浏览器卡在 Turnstile 验证页面
- 请求返回 403/429 状态码
- 代理连接超时 (`ETIMEDOUT`)
- `NetworkShield` 报告高失败率

### 诊断命令

```bash
# 检查代理连通性
for port in 7890 7891 7892; do
  echo "Testing port $port..."
  curl -x http://172.25.16.1:$port https://httpbin.org/ip --connect-timeout 5
done

# 检查熔断状态
docker-compose -f docker-compose.dev.yml exec dev cat /app/data/circuit_breaker.json 2>/dev/null || echo "无熔断记录"

# 检查会话文件
ls -la /app/data/sessions/ 2>/dev/null || echo "无会话目录"
```

### 解决方案

| 问题 | 解决方案 |
|------|----------|
| **代理全部熔断** | 重启容器: `docker-compose -f docker-compose.dev.yml restart dev` |
| **Turnstile 拦截** | 宿主机手动捕获身份: `node scripts/capture_auth.js` |
| **IP 被封** | 等待 24 小时冷却，或更换代理节点 |
| **DNS 解析失败** | 使用静态 IP: `echo "104.26.12.88 oddsportal.com" >> /etc/hosts` |

### 预防措施

- 保持 22 节点代理池健康
- 定期刷新 Session (每 4 小时)
- 使用 `SWARM_CONCURRENCY=1` 降低请求频率

---

## 2. 数据库不对齐 (Data Misalignment)

### 症状

- L1/L2/L3 层级数量不一致
- `match_id` 外键约束失败
- 预测报告显示 "无待预测比赛"
- `integrity_guard.py` 报告数据缺失

### 诊断命令

```bash
# 检查各层级数据量
docker-compose -f docker-compose.dev.yml exec db psql -U football_user -d football_db -c "
SELECT
  'L1 (matches)' as layer, COUNT(*) as count FROM matches
UNION ALL
SELECT 'L2 (raw_match_data)', COUNT(*) FROM raw_match_data
UNION ALL
SELECT 'L3 (l3_features)', COUNT(*) FROM l3_features
UNION ALL
SELECT 'Predictions', COUNT(*) FROM predictions;
"

# 检查孤立记录
docker-compose -f docker-compose.dev.yml exec db psql -U football_user -d football_db -c "
SELECT COUNT(*) as orphan_l2 FROM raw_match_data r
WHERE NOT EXISTS (SELECT 1 FROM matches m WHERE m.match_id = r.match_id);
"

# 检查数据完整性
docker-compose -f docker-compose.dev.yml exec dev python scripts/maintenance/integrity_guard.py
```

### 解决方案

| 问题 | 解决方案 |
|------|----------|
| **L2 缺失** | 重新收割: `docker-compose -f docker-compose.dev.yml exec dev npm start -- --limit 100` |
| **L3 缺失** | 重新熔炼: `docker-compose -f docker-compose.dev.yml exec dev npm run smelt` |
| **孤立记录** | 清理: `DELETE FROM raw_match_data WHERE match_id NOT IN (SELECT match_id FROM matches)` |
| **特征为空** | 检查 L2 JSON 完整性: `SELECT match_id, jsonb_array_length(odds_data) FROM raw_match_data WHERE odds_data IS NOT NULL LIMIT 5` |

### 数据修复脚本

```sql
-- 重建 L3 特征 (针对特定比赛)
DELETE FROM l3_features WHERE match_id = 'TARGET_MATCH_ID';
-- 然后重新运行 smelt

-- 清理过期预测
DELETE FROM predictions WHERE created_at < NOW() - INTERVAL '30 days';
```

---

## 3. 内存溢出 (OOM)

### 症状

- 容器被 OOM Killer 杀死 (`Exit Code 137`)
- 浏览器进程崩溃
- 系统响应极慢
- `dmesg` 显示 `Out of memory`

### 诊断命令

```bash
# 检查容器内存使用
docker stats football_prediction_dev --no-stream

# 检查系统内存
free -h

# 检查浏览器进程数
docker-compose -f docker-compose.dev.yml exec dev ps aux | grep -c chromium

# 检查 Python 内存使用
docker-compose -f docker-compose.dev.yml exec dev python -c "
import psutil
print(f'Memory: {psutil.virtual_memory().percent}%')
print(f'Available: {psutil.virtual_memory().available / 1024**3:.1f} GB')
"
```

### 解决方案

| 问题 | 解决方案 |
|------|----------|
| **浏览器内存泄漏** | 限制并发: `SWARM_CONCURRENCY=1` |
| **Docker 内存不足** | 增加限制: `mem_limit: 4g` in docker-compose |
| **Pandas 大数据集** | 使用 chunked processing |
| **特征维度过高** | 减少 batch_size: `--batch-size 50` |

### 配置优化

```yaml
# docker-compose.dev.yml
services:
  dev:
    deploy:
      resources:
        limits:
          memory: 4G
        reservations:
          memory: 2G
```

```bash
# 环境变量
export NODE_OPTIONS="--max-old-space-size=4096"
export SWARM_CONCURRENCY=1
```

---

## 4. 监控断连 (Monitoring Disconnection)

### 症状

- Grafana 仪表盘无数据
- Prometheus targets 显示 `DOWN`
- `/metrics` 端点无响应
- 告警规则不触发

### 诊断命令

```bash
# 检查 Prometheus 状态
curl -s http://localhost:9090/-/healthy

# 检查 targets
curl -s http://localhost:9090/api/v1/targets | jq '.data.activeTargets[].health'

# 检查 metrics 端点
curl -s http://localhost:8000/metrics | head -20

# 检查容器网络
docker network inspect footballprediction_default | jq '.[0].Containers'
```

### 解决方案

| 问题 | 解决方案 |
|------|----------|
| **Prometheus 无法抓取** | 检查 `prometheus.yml` 中的 targets 配置 |
| **Grafana 数据源断开** | 重新配置: Admin → Data Sources → Prometheus |
| **Metrics 端点无数据** | 重启 metrics 服务: `docker-compose restart dev` |
| **网络隔离** | 确保容器在同一网络: `docker network connect` |

### Prometheus 配置验证

```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'football-prediction'
    static_configs:
      - targets: ['dev:8000']  # 确保使用容器服务名
    scrape_interval: 15s
```

### 快速修复

```bash
# 重启监控栈
docker-compose -f docker-compose.dev.yml restart prometheus grafana

# 重新导入仪表盘
./scripts/ops/import_dashboard.sh

# 验证数据流
curl -s 'http://localhost:9090/api/v1/query?query=up' | jq '.data.result'
```

---

## 快速参考卡片

| 故障类型 | 一键诊断 | 一键修复 |
|----------|----------|----------|
| 网络封锁 | `make test-proxy` | `docker-compose restart dev` |
| 数据不对齐 | `npm run status:db` | `npm run smelt` |
| 内存溢出 | `docker stats --no-stream` | `SWARM_CONCURRENCY=1 npm start` |
| 监控断连 | `curl localhost:9090/-/healthy` | `docker-compose restart prometheus` |

---

## 联系支持

如遇无法解决的问题，请提供以下信息：

1. 完整错误日志 (`/app/logs/`)
2. 诊断命令输出
3. `docker-compose logs` 输出
4. 系统环境 (`uname -a`, `docker version`)

---

**最后更新**: 2026-03-09 | **维护者**: TITAN Engineering Team
