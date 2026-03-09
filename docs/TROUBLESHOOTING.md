# TITAN 故障诊断手册 (Troubleshooting Guide)

> **版本**: V4.46.6 | **最后更新**: 2026-03-09
>
> 本手册涵盖生产环境中最常见的故障场景及解决方案。

---

## 🚨 快速诊断决策树

```
问题发生
    │
    ├─ 网络问题? ──────────────────────→ 见 §1 网络层
    │   ├─ 代理连接失败
    │   ├─ Turnstile 拦截
    │   └─ DNS 解析错误
    │
    ├─ 内存问题? ──────────────────────→ 见 §2 内存层
    │   ├─ Context Eviction 过高
    │   ├─ OOM (Out of Memory)
    │   └─ 浏览器崩溃
    │
    ├─ 数据问题? ──────────────────────→ 见 §3 数据层
    │   ├─ L1/L2/L3 不对齐
    │   ├─ 解析器失效
    │   └─ 数据格式异常
    │
    └─ 监控问题? ──────────────────────→ 见 §4 监控层
        ├─ Prometheus 抓取失败
        ├─ Grafana 无数据
        └─ 指标缺失
```

---

## §1 网络层故障

### 1.1 代理池诊断

**症状**: 收割成功率骤降，大量连接超时

**诊断命令**:
```bash
# 检查单个代理节点
curl -x http://172.25.16.1:7890 --connect-timeout 5 https://httpbin.org/ip

# 批量检查所有 22 个节点
for port in $(seq 7890 7911); do
    result=$(curl -x http://172.25.16.1:$port --connect-timeout 3 -s https://httpbin.org/ip 2>/dev/null)
    if [ -n "$result" ]; then
        echo "✅ Port $port: OK"
    else
        echo "❌ Port $port: FAILED"
    fi
done
```

**解决方案**:
```bash
# 重启代理服务 (Windows 端 Clash Verge)
# WSL2 中刷新网络
sudo systemctl restart networking

# 或重置 Docker 网络
docker-compose -f docker-compose.dev.yml down
docker network prune -f
docker-compose -f docker-compose.dev.yml up -d
```

### 1.2 NetworkShield 熔断重置

**症状**: 日志显示 "Circuit Breaker TRIPPED"

**诊断**:
```bash
# 查看熔断状态
docker-compose -f docker-compose.dev.yml exec dev cat /app/data/circuit_breaker.json 2>/dev/null || echo "无熔断记录"

# 检查熔断日志
docker-compose -f docker-compose.dev.yml exec dev grep -r "Circuit Breaker" /app/logs/ | tail -20
```

**解决方案**:
```bash
# 方法1: 清除熔断记录 (等待冷却期)
rm -f /app/data/circuit_breaker.json

# 方法2: 重启开发容器
docker-compose -f docker-compose.dev.yml restart dev

# 方法3: 调整熔断阈值 (config/factory_config.js)
# CIRCUIT_BREAKER.failureThreshold: 5 → 10
# CIRCUIT_BREAKER.cooldownMs: 60000 → 30000
```

### 1.3 Turnstile 拦截

**症状**: 返回 HTML 而非 JSON，日志显示 "JSON 解析失败"

**诊断**:
```bash
# 检查会话文件
docker-compose -f docker-compose.dev.yml exec dev ls -la /app/data/sessions/

# 检查 Cookie 有效性
docker-compose -f docker-compose.dev.yml exec dev cat /app/data/sessions/session_port_7890.json | head -50
```

**解决方案**:
```bash
# 方法1: 宿主机手动刷新身份
# 需要在有图形界面的环境中运行
node scripts/capture_auth.js

# 方法2: 使用 hyper_swarm_stealth.js (增强隐蔽模式)
node scripts/ops/hyper_swarm_stealth.js

# 方法3: 增加行为模拟
# 在 SessionManager 中启用更多鼠标移动和滚动
```

---

## §2 内存层故障

### 1.1 Context Eviction 频率过高

**症状**: 日志频繁显示 "Context evicted from pool"

**诊断**:
```bash
# 检查当前内存使用
docker stats football_prediction_dev --no-stream

# 查看日志中的 Eviction 记录
docker-compose -f docker-compose.dev.yml exec dev grep "Context evicted" /app/logs/*.log | wc -l
```

**解决方案**:

编辑 `src/infrastructure/harvesters/AbstractHarvester.js`:
```javascript
// 调整 Context 池大小 (默认 50)
this._contextPoolMaxSize = 100;  // 增加到 100

// 调整 LRU 淘汰阈值
this._contextPoolEvictionThreshold = 0.8;  // 80% 时开始淘汰
```

重启服务:
```bash
docker-compose -f docker-compose.dev.yml restart dev
```

### 2.2 OOM (内存溢出)

**症状**: 容器被 kill，dmesg 显示 "Out of memory"

**诊断**:
```bash
# 查看容器内存限制
docker-compose -f docker-compose.dev.yml config | grep -A5 memory

# 监控内存使用
watch -n 5 'docker stats --no-stream'
```

**解决方案**:

编辑 `docker-compose.dev.yml`:
```yaml
deploy:
  resources:
    limits:
      memory: 12G  # 从 8G 增加到 12G
```

重启:
```bash
docker-compose -f docker-compose.dev.yml up -d
```

### 2.3 浏览器崩溃

**症状**: "Browser closed unexpectedly" 或 "Target closed"

**诊断**:
```bash
# 检查僵尸进程
docker-compose -f docker-compose.dev.yml exec dev ps aux | grep -E 'chromium|chrome' | grep defunct

# 检查浏览器日志
docker-compose -f docker-compose.dev.yml exec dev cat /app/logs/browser.log 2>/dev/null | tail -50
```

**解决方案**:
```bash
# 清理僵尸进程
docker-compose -f docker-compose.dev.yml exec dev node -e "
const { preFlightCleanup } = require('./src/core/process/ZombieKiller');
preFlightCleanup().then(() => console.log('清理完成'));
"

# 重新安装浏览器
docker-compose -f docker-compose.dev.yml exec dev npx playwright install chromium --force
```

---

## §3 数据层故障

### 3.1 L1/L2/L3 不对齐

**症状**: `npm run status` 显示 L1 ≠ L2 或 L2 ≠ L3

**诊断**:
```bash
# 详细对比
docker-compose -f docker-compose.dev.yml exec db psql -U football_user -d football_db -c "
SELECT 
    'L1 only' as type, COUNT(*) as count
FROM matches m LEFT JOIN raw_match_data r ON m.match_id = r.match_id
WHERE r.match_id IS NULL
UNION ALL
SELECT 
    'L2 only', COUNT(*)
FROM raw_match_data r LEFT JOIN l3_features l ON r.match_id = l.match_id
WHERE l.match_id IS NULL;
"
```

**解决方案**:

根据诊断结果:

```bash
# L1 > L2: 有比赛未收割
npm run harvest

# L2 > L3: 有数据未熔炼
npm run smelt

# L2 > L1: 有孤立的 raw_match_data (数据异常)
# 需要手动清理
docker-compose -f docker-compose.dev.yml exec db psql -U football_user -d football_db -c "
DELETE FROM raw_match_data 
WHERE match_id NOT IN (SELECT match_id FROM matches);
"
```

### 3.2 解析器失效

**症状**: 数据体积正常但字段为空或格式错误

**诊断**:
```bash
# 检查最近收割的数据
docker-compose -f docker-compose.dev.yml exec db psql -U football_user -d football_db -c "
SELECT match_id, LENGTH(raw_data::text) as size, 
       raw_data->'odds'->>'home_open' as home_odds
FROM raw_match_data 
ORDER BY collected_at DESC LIMIT 5;
"

# 测试解析器
docker-compose -f docker-compose.dev.yml exec dev node -e "
const { FotMobParser } = require('./src/parsers/FotMobParser');
const parser = new FotMobParser();
console.log('Parser loaded:', typeof parser.extractMatchData === 'function');
"
```

**解决方案**:

1. 检查源网站是否更新了 HTML 结构
2. 更新解析器 `src/parsers/*.js`
3. 运行测试验证: `npm run test:l1`

### 3.3 数据格式异常

**症状**: JSON 解析错误或字段类型不匹配

**诊断**:
```bash
# 检查 JSON 有效性
docker-compose -f docker-compose.dev.yml exec db psql -U football_user -d football_db -c "
SELECT match_id, 
       CASE WHEN raw_data::text ~ '^\{.*\}$' THEN 'VALID' ELSE 'INVALID' END as json_status
FROM raw_match_data 
ORDER BY collected_at DESC LIMIT 10;
"
```

**解决方案**:
```bash
# 清理无效数据
docker-compose -f docker-compose.dev.yml exec db psql -U football_user -d football_db -c "
DELETE FROM raw_match_data 
WHERE NOT raw_data::text ~ '^\{.*\}$';
"

# 重新收割
npm run harvest
```

---

## §4 监控层故障

### 4.1 Prometheus 抓取失败

**症状**: Grafana 无数据，Prometheus targets 显示 DOWN

**诊断**:
```bash
# 检查 Prometheus targets 状态
curl -s http://localhost:9090/api/v1/targets | python3 -c "
import sys, json
data = json.load(sys.stdin)
for t in data['data']['activeTargets']:
    print(f\"{t['labels']['job']}: {t['health']} - {t.get('lastError', 'OK')}\")
"

# 检查 metrics 服务是否运行
curl -s http://localhost:8000/metrics | head -10
```

**解决方案**:
```bash
# 重启 metrics 服务
docker-compose -f docker-compose.dev.yml exec -d dev node scripts/ops/metrics_server.js

# 重启 Prometheus
docker-compose -f docker-compose.dev.yml restart prometheus

# 完整重启监控栈
npm run monitor:down
npm run monitor:up
```

### 4.2 Grafana 无数据

**症状**: Dashboard 面板显示 "No data"

**诊断**:
```bash
# 检查数据源连接
curl -s -u admin:titan2024 http://localhost:3001/api/datasources/proxy/1/api/v1/query?query=up | head -50

# 检查 Prometheus 是否有数据
curl -s 'http://localhost:9090/api/v1/query?query=titan_data_l1_total'
```

**解决方案**:
```bash
# 重新导入 Dashboard
./scripts/ops/import_dashboard.sh

# 检查数据源配置
docker-compose -f docker-compose.dev.yml exec grafana cat /etc/grafana/provisioning/datasources/datasource.yml
```

### 4.3 指标缺失

**症状**: 某些 `titan_*` 指标不存在

**诊断**:
```bash
# 列出所有可用指标
curl -s http://localhost:8000/metrics | grep '^titan_' | cut -d'{' -f1 | sort -u
```

**解决方案**:

确保 metrics_server.js 和 MetricsClient.js 中的指标定义一致。如果需要添加新指标，编辑:
- `src/infrastructure/monitoring/MetricsClient.js` (收割时记录)
- `scripts/ops/metrics_server.js` (暴露端点)

---

## 📞 紧急恢复命令

```bash
# 完全重置环境
docker-compose -f docker-compose.dev.yml down -v
docker-compose -f docker-compose.dev.yml up -d

# 仅重启应用层
docker-compose -f docker-compose.dev.yml restart dev

# 仅重启监控层
npm run monitor:down && npm run monitor:up

# 数据库紧急备份
docker-compose -f docker-compose.dev.yml exec db pg_dump -U football_user football_db > backup_$(date +%Y%m%d).sql

# 清理所有日志
docker-compose -f docker-compose.dev.yml exec dev rm -rf /app/logs/*
```

---

## 🔍 日志位置

| 组件 | 日志路径 |
|------|----------|
| 收割器 | `/app/logs/harvester.log` |
| 浏览器 | `/app/logs/browser.log` |
| 系统 | `docker-compose logs dev` |
| Prometheus | `docker-compose logs prometheus` |
| Grafana | `docker-compose logs grafana` |

---

**文档维护者**: TITAN SRE Team
**紧急联系**: GitHub Issues
