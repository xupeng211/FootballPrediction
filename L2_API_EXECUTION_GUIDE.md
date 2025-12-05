# L2 API采集器执行指南
# L2 API Collector Execution Guide

## 🚀 快速开始

### 1. 环境准备
```bash
# 启动开发环境
make dev

# 确保服务正常运行
make status

# 验证API健康状态
curl http://localhost:8000/health
```

### 2. 立即执行L2采集
```bash
# 试运行模式（不写入数据库，仅测试API连接）
docker-compose exec app python3 src/jobs/run_l2_api_details.py dry-run

# 完整采集（写入数据库）
docker-compose exec app python3 src/jobs/run_l2_api_details.py full

# 增量回填（处理失败的比赛）
docker-compose exec app python3 src/jobs/run_l2_api_details.py backfill
```

## 📋 执行模式详解

### 🔍 试运行模式 (dry-run)
**用途**: 测试API连接和数据解析，不写入数据库

```bash
# 基本试运行
docker-compose exec app python3 src/jobs/run_l2_api_details.py dry-run

# 带参数的试运行
LIMIT=100 BATCH_SIZE=20 docker-compose exec app python3 src/jobs/run_l2_api_details.py dry-run
```

**输出示例**:
```
🎯 开始L2 API详情采集流程
📋 参数: limit=100, batch_size=20, max_concurrent=10
🔧 模式: 试运行
📊 找到 100 场待处理比赛
🚀 开始批量采集 100 场比赛详情
📦 处理批次 1/5 (20 场比赛)
✅ 成功采集: 123456
🧪 试运行模式，跳过数据库写入
🎉 L2详情采集流程完成!
📊 采集统计: 成功 95/100 (95.0%)
⏱️ 总耗时: 45.2秒
```

### 🎯 完整采集模式 (full)
**用途**: 正式数据采集，写入数据库

```bash
# 标准完整采集
docker-compose exec app python3 src/jobs/run_l2_api_details.py full

# 自定义参数采集
LIMIT=5000 BATCH_SIZE=100 MAX_CONCURRENT=15 docker-compose exec app python3 src/jobs/run_l2_api_details.py full
```

**环境变量参数**:
- `LIMIT`: 最大处理比赛数量（默认10000）
- `BATCH_SIZE`: 批处理大小（默认50）
- `MAX_CONCURRENT`: 最大并发数（默认10）

### 🔄 增量回填模式 (backfill)
**用途**: 处理之前失败的比赛数据

```bash
# 标准回填
docker-compose exec app python3 src/jobs/run_l2_api_details.py backfill

# 指定回填参数
BATCH_SIZE=30 MAX_CONCURRENT=5 docker-compose exec app python3 src/jobs/run_l2_api_details.py backfill
```

## 🔧 参数配置详解

### 性能调优参数

```bash
# 高性能配置（适用于强大服务器）
LIMIT=50000 BATCH_SIZE=200 MAX_CONCURRENT=20 docker-compose exec app python3 src/jobs/run_l2_api_details.py full

# 保守配置（适用于有限资源）
LIMIT=1000 BATCH_SIZE=20 MAX_CONCURRENT=3 docker-compose exec app python3 src/jobs/run_l2_api_details.py full

# 调试配置（单步执行）
LIMIT=10 BATCH_SIZE=5 MAX_CONCURRENT=1 docker-compose exec app python3 src/jobs/run_l2_api_details.py dry-run
```

### 代理配置（可选）

```bash
# 设置代理列表
export PROXY_LIST="proxy1.example.com:8080,proxy2.example.com:8080,proxy3.example.com:8080"

# 设置认证代理
export PROXY_LIST="user:pass@proxy1.example.com:8080,user:pass@proxy2.example.com:8080"

# 执行采集
docker-compose exec app python3 src/jobs/run_l2_api_details.py full
```

## 📊 监控和状态检查

### 实时监控
```bash
# 查看采集日志
make logs

# 监控容器资源使用
docker stats footballprediction-app-1

# 检查数据库连接
make db-shell
SELECT COUNT(*) FROM matches WHERE data_completeness = 'complete';
SELECT COUNT(*) FROM matches WHERE data_completeness = 'partial';
```

### 数据库查询
```sql
-- 查看采集进度
SELECT
    data_completeness,
    COUNT(*) as count,
    data_source
FROM matches
GROUP BY data_completeness, data_source
ORDER BY data_completeness;

-- 查看最新采集的数据
SELECT fotmob_id, home_score, away_score, status, updated_at
FROM matches
WHERE data_completeness = 'complete'
ORDER BY updated_at DESC
LIMIT 10;

-- 检查数据质量
SELECT
    COUNT(*) as total,
    COUNT(CASE WHEN home_score > 0 OR away_score > 0 THEN 1 END) as with_scores,
    COUNT(CASE WHEN lineups IS NOT NULL THEN 1 END) as with_lineups,
    COUNT(CASE WHEN stats IS NOT NULL THEN 1 END) as with_stats
FROM matches
WHERE data_completeness = 'complete';
```

## 🚨 故障排除

### 常见问题及解决方案

#### 1. API速率限制 (429错误)
**症状**: 日志显示"请求被限制"
**解决方案**:
```bash
# 减少并发数
MAX_CONCURRENT=3 docker-compose exec app python3 src/jobs/run_l2_api_details.py dry-run

# 增加批次间延迟
# 编辑 src/collectors/fotmob_api_collector.py
# 调整 base_delay 参数
```

#### 2. 代理连接失败
**症状**: "代理连接超时"或"代理不可用"
**解决方案**:
```bash
# 禁用代理
export PROXY_LIST=""

# 更新代理列表
export PROXY_LIST="new-proxy1.com:8080,new-proxy2.com:8080"

# 检查代理状态
docker-compose exec app python3 -c "
import asyncio
from src.collectors.proxy_pool import ProxyPool, ProxyConfig
async def test():
    configs = [ProxyConfig(host='proxy.example.com', port=8080)]
    pool = ProxyPool(configs)
    stats = await pool.get_proxy()
    print(f'Available proxy: {stats}')
asyncio.run(test())
"
```

#### 3. 数据库连接问题
**症状**: "数据库连接失败"或"事务超时"
**解决方案**:
```bash
# 检查数据库状态
make db-shell

# 重启数据库
docker-compose restart db

# 检查连接池配置
# 编辑 src/database/async_manager.py
```

#### 4. 内存不足
**症状**: "内存不足"或容器被杀死
**解决方案**:
```bash
# 减少批次大小
BATCH_SIZE=10 docker-compose exec app python3 src/jobs/run_l2_api_details.py full

# 减少并发数
MAX_CONCURRENT=2 docker-compose exec app python3 src/jobs/run_l2_api_details.py full

# 增加Docker内存限制
# 编辑 docker-compose.yml
```

### 调试命令

#### 1. API连接测试
```bash
# 测试FotMob API
docker-compose exec app python3 -c "
import httpx
import asyncio
async def test():
    async with httpx.AsyncClient() as client:
        response = await client.get('https://www.fotmob.com/api/matchDetails?matchId=123456')
        print(f'Status: {response.status_code}')
        if response.status_code == 200:
            data = response.json()
            print(f'Data keys: {list(data.keys())}')
asyncio.run(test())
"
```

#### 2. 数据库连接测试
```bash
# 测试数据库连接
docker-compose exec app python3 -c "
import asyncio
from src.database.async_manager import get_db_session
from sqlalchemy import text
async def test():
    async with get_db_session() as session:
        result = await session.execute(text('SELECT COUNT(*) FROM matches'))
        count = result.scalar()
        print(f'Total matches: {count}')
asyncio.run(test())
"
```

#### 3. 速率限制器测试
```bash
# 测试速率限制器
docker-compose exec app python3 -c "
import asyncio
from src.collectors.rate_limiter import get_rate_limiter
async def test():
    limiter = get_rate_limiter()
    for i in range(5):
        await limiter.wait_for_slot('fotmob.com')
        print(f'Request {i+1} completed')
asyncio.run(test())
"
```

## 📈 性能优化

### 1. 并发优化
```bash
# 根据服务器性能调整并发数
# 低配置服务器 (2GB RAM)
MAX_CONCURRENT=3 BATCH_SIZE=20

# 中等配置服务器 (4GB RAM)
MAX_CONCURRENT=8 BATCH_SIZE=50

# 高配置服务器 (8GB+ RAM)
MAX_CONCURRENT=15 BATCH_SIZE=100
```

### 2. 批处理优化
```bash
# 小批量（适合不稳定网络）
BATCH_SIZE=20

# 中等批量（标准配置）
BATCH_SIZE=50

# 大批量（稳定网络和强大服务器）
BATCH_SIZE=100-200
```

### 3. 内存优化
```bash
# 监控内存使用
docker stats footballprediction-app-1 --no-stream

# 如果内存使用>80%，减少参数
BATCH_SIZE=30 MAX_CONCURRENT=5
```

## 📋 执行检查清单

### 执行前检查 ✅
- [ ] Docker服务正常运行 (`make status`)
- [ ] 数据库连接正常 (`make db-shell`)
- [ ] 网络连接稳定 (测试API访问)
- [ ] 足够的磁盘空间 (>1GB)
- [ ] 足够的内存 (>2GB可用)

### 执行中监控 📊
- [ ] 观察日志输出正常
- [ ] 监控错误率 <5%
- [ ] 检查内存使用 <80%
- [ ] 验证数据写入正常

### 执行后验证 🎯
- [ ] 检查采集成功率
- [ ] 验证数据完整性
- [ ] 查看错误日志
- [ ] 更新监控指标

## 🎯 生产环境部署

### 1. 定时任务设置
```bash
# 添加到crontab
# 每天凌晨2点执行增量回填
0 2 * * * cd /path/to/project && make run-l2-api-backfill

# 每周日凌晨1点执行完整采集
0 1 * * 0 cd /path/to/project && make run-l2-api-full
```

### 2. 监控告警
```bash
# 设置监控脚本
cat > monitor_l2_collection.sh << 'EOF'
#!/bin/bash
# 检查L2采集状态

# 检查最近24小时的数据量
RECENT_COUNT=$(docker-compose exec -T db psql -U postgres -d football_prediction -t -c "
    SELECT COUNT(*) FROM matches
    WHERE updated_at > NOW() - INTERVAL '24 hours'
    AND data_completeness = 'complete'
" | tr -d ' ')

if [ "$RECENT_COUNT" -lt 100 ]; then
    echo "警告：最近24小时只采集了${RECENT_COUNT}条数据"
    # 发送告警邮件或Slack通知
fi
EOF

chmod +x monitor_l2_collection.sh
```

### 3. 备份策略
```bash
# 数据库备份
make db-backup

# 采集结果导出
docker-compose exec db psql -U postgres -d football_prediction -c "
    COPY (
        SELECT fotmob_id, home_score, away_score, status, venue, attendance,
               lineups, stats, events, updated_at
        FROM matches
        WHERE data_completeness = 'complete'
        AND updated_at > NOW() - INTERVAL '7 days'
    ) TO '/tmp/l2_recent_data.csv' WITH CSV HEADER;
"
```

## 📞 支持和联系

如果遇到问题，请按以下步骤操作：

1. **检查日志**: `make logs` 查看详细错误信息
2. **运行诊断**: 使用上述调试命令进行诊断
3. **查看状态**: 检查数据库和API状态
4. **参考文档**: 查看 `L2_API_COLLECTOR_PATCH.md` 了解技术细节

---

**💡 记住**: 这个L2 API采集器系统设计为高可用和容错，即使在部分失败的情况下也能继续工作并自动恢复。