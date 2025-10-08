# 故障排除手册

本手册提供了足球预测系统常见问题的诊断和解决方案。

## 目录

1. [快速诊断](#快速诊断)
2. [服务启动问题](#服务启动问题)
3. [数据库问题](#数据库问题)
4. [Redis 缓存问题](#redis-缓存问题)
5. [预测服务问题](#预测服务问题)
6. [API 问题](#api-问题)
7. [性能问题](#性能问题)
8. [监控和告警](#监控和告警)

## 快速诊断

### 健康检查脚本

```bash
#!/bin/bash
# health_check.sh - 系统健康检查脚本

echo "=== 足球预测系统健康检查 ==="
echo "时间: $(date)"
echo ""

# 1. 检查服务状态
echo "1. 检查服务状态..."
systemctl is-active football-prediction || echo "❌ 服务未运行"
systemctl is-enabled football-prediction || echo "❌ 服务未启用"

# 2. 检查端口
echo -e "\n2. 检查端口..."
netstat -tlnp | grep :8000 > /dev/null && echo "✅ API 端口 8000 正常" || echo "❌ API 端口 8000 未监听"
netstat -tlnp | grep :5432 > /dev/null && echo "✅ PostgreSQL 端口 5432 正常" || echo "❌ PostgreSQL 端口 5432 未监听"
netstat -tlnp | grep :6379 > /dev/null && echo "✅ Redis 端口 6379 正常" || echo "❌ Redis 端口 6379 未监听"

# 3. 检查 API 健康端点
echo -e "\n3. 检查 API 健康..."
if curl -s http://localhost:8000/api/health > /dev/null; then
    echo "✅ API 健康检查通过"
else
    echo "❌ API 健康检查失败"
fi

# 4. 检查数据库连接
echo -e "\n4. 检查数据库..."
if PGPASSWORD=$POSTGRES_PASSWORD psql -h $DB_HOST -U $DB_USER -d $DB_NAME -c "SELECT 1" > /dev/null 2>&1; then
    echo "✅ 数据库连接正常"
else
    echo "❌ 数据库连接失败"
fi

# 5. 检查 Redis
echo -e "\n5. 检查 Redis..."
if redis-cli -h $REDIS_HOST ping > /dev/null 2>&1; then
    echo "✅ Redis 连接正常"
else
    echo "❌ Redis 连接失败"
fi

echo -e "\n=== 健康检查完成 ==="
```

### 一键诊断脚本

```bash
# 保存为 diagnose.sh
curl -sSL https://raw.githubusercontent.com/your-org/football-prediction/main/scripts/diagnose.sh | bash
```

## 服务启动问题

### 问题 1: 服务无法启动

**症状：**
```bash
$ systemctl start football-prediction
Job for football-prediction.service failed.
```

**诊断步骤：**

1. 查看服务状态
```bash
systemctl status football-prediction
journalctl -u football-prediction -f
```

2. 检查配置文件
```bash
cat /etc/systemd/system/football-prediction.service
```

3. 查看应用日志
```bash
tail -f /var/log/football-prediction/app.log
```

**常见原因和解决方案：**

| 原因 | 解决方案 |
|------|----------|
| 端口被占用 | `sudo netstat -tlnp \| grep :8000`，然后 `sudo kill -9 <PID>` |
| 环境变量缺失 | 检查 `.env` 文件，确保所有必需变量都已设置 |
| 依赖服务未启动 | 先启动 PostgreSQL 和 Redis |
| 权限不足 | `sudo chown -R user:user /var/log/football-prediction` |

### 问题 2: 应用启动后立即崩溃

**诊断步骤：**

```bash
# 检查最近的崩溃日志
dmesg | grep football-prediction
journalctl -u football-prediction --since "1 minute ago"

# 检查 Python 路径
which python
python --version

# 检查依赖
pip freeze | grep -E "(fastapi|uvicorn|sqlalchemy)"
```

**解决方案：**

```bash
# 重新安装依赖
pip install -r requirements/dev.lock

# 使用调试模式启动
python -m uvicorn src.api.app:app --reload --log-level debug
```

## 数据库问题

### 问题 1: 数据库连接失败

**症状：**
```
sqlalchemy.exc.OperationalError: (psycopg2.OperationalError) could not connect to server
```

**诊断脚本：**

```bash
#!/bin/bash
# db_diagnose.sh

echo "=== 数据库诊断 ==="

# 检查连接字符串
echo "DATABASE_URL: $DATABASE_URL"

# 检查 PostgreSQL 服务
systemctl is-active postgresql || echo "PostgreSQL 服务未运行"

# 检查监听端口
ss -tlnp | grep :5432

# 尝试连接
psql $DATABASE_URL -c "SELECT version();" || echo "连接失败"

# 检查连接数
psql $DATABASE_URL -c "SELECT count(*) FROM pg_stat_activity;"
```

**解决方案：**

1. 检查 PostgreSQL 配置
```bash
sudo vim /etc/postgresql/14/main/postgresql.conf
# 确保以下配置：
listen_addresses = '*'
port = 5432
max_connections = 100
```

2. 检查 pg_hba.conf
```bash
sudo vim /etc/postgresql/14/main/pg_hba.conf
# 添加：
host    all             all             0.0.0.0/0               md5
```

3. 重启 PostgreSQL
```bash
sudo systemctl restart postgresql
```

### 问题 2: 数据库迁移失败

**症状：**
```
alembic upgrade head
FAILED: Target database is not up to date
```

**诊断步骤：**

```bash
# 查看当前版本
alembic current

# 查看待执行的迁移
alembic history

# 检查迁移脚本
ls src/database/migrations/versions/
```

**解决方案：**

```bash
# 标记为已执行（谨慎使用）
alembic stamp <revision>

# 或者重新创建迁移
alembic revision --autogenerate -m "Initial migration"
alembic upgrade head
```

### 问题 3: 数据库性能问题

**诊断查询：**

```sql
-- 查看慢查询
SELECT query, mean_time, calls, total_time
FROM pg_stat_statements
WHERE mean_time > 1000  -- 超过1秒的查询
ORDER BY mean_time DESC
LIMIT 10;

-- 查看连接数
SELECT state, count(*)
FROM pg_stat_activity
GROUP BY state;

-- 查看锁等待
SELECT blocked_locks.pid AS blocked_pid,
       blocked_activity.usename AS blocked_user,
       blocking_locks.pid AS blocking_pid,
       blocking_activity.usename AS blocking_user,
       blocked_activity.query AS blocked_statement,
       blocking_activity.query AS current_statement_in_blocking_process
FROM pg_catalog.pg_locks blocked_locks
JOIN pg_catalog.pg_stat_activity blocked_activity ON blocked_activity.pid = blocked_locks.pid
JOIN pg_catalog.pg_locks blocking_locks ON blocking_locks.locktype = blocked_locks.locktype
JOIN pg_catalog.pg_stat_activity blocking_activity ON blocking_activity.pid = blocking_locks.pid
WHERE NOT blocked_locks.granted;
```

## Redis 缓存问题

### 问题 1: Redis 连接超时

**诊断脚本：**

```bash
# redis_diagnose.sh

echo "=== Redis 诊断 ==="

# 测试连接
redis-cli -h $REDIS_HOST ping || echo "Redis 无法连接"

# 检查内存使用
redis-cli -h $REDIS_HOST info memory

# 检查连接数
redis-cli -h $REDIS_HOST info clients

# 检查慢查询
redis-cli -h $REDIS_HOST slowlog get 10
```

**解决方案：**

1. 增加 Redis 连接池大小
```python
# config.py
REDIS_POOL_SIZE = 20
REDIS_MAX_CONNECTIONS = 50
```

2. 优化 Redis 配置
```conf
# redis.conf
timeout 300
tcp-keepalive 60
maxclients 10000
```

### 问题 2: 缓存未命中

**诊断代码：**

```python
import logging

logger = logging.getLogger(__name__)

def diagnose_cache_hits():
    """诊断缓存命中率"""
    from src.cache.redis_manager import get_redis_manager

    redis = get_redis_manager()

    # 模拟请求
    test_keys = ["test:1", "test:2", "test:3"]
    hits = 0

    for key in test_keys:
        if redis.get(key):
            hits += 1

    hit_rate = hits / len(test_keys)
    logger.info(f"缓存命中率: {hit_rate:.2%}")

    if hit_rate < 0.5:
        logger.warning("缓存命中率过低！")
        # 检查缓存配置
        logger.info(f"缓存配置: TTL={settings.CACHE_TTL}")
```

## 预测服务问题

### 问题 1: MLflow 模型加载失败

**症状：**
```
mlflow.exceptions.MlflowException: No model version found for model 'football_baseline_model' with stage 'Production'
```

**解决方案：**

```bash
# 1. 检查 MLflow 服务
curl http://localhost:5002/api/2.0/search/experiments

# 2. 注册模型
python scripts/register_model.py \
  --model-path models/football_model.pkl \
  --model-name football_baseline_model \
  --stage Production

# 3. 验证模型
python scripts/test_model.py
```

### 问题 2: 预测服务响应慢

**诊断代码：**

```python
import time
import asyncio
from src.core.prediction_engine import get_prediction_engine

async def diagnose_prediction_performance():
    """诊断预测性能"""
    engine = await get_prediction_engine()

    match_ids = list(range(1000, 1010))
    start_time = time.time()

    # 测试批量预测
    results = await engine.batch_predict(match_ids)

    duration = time.time() - start_time
    avg_time = duration / len(results)

    print(f"批量预测性能:")
    print(f"  总时间: {duration:.2f}s")
    print(f"  平均延迟: {avg_time*1000:.2f}ms")
    print(f"  吞吐量: {len(results)/duration:.2f} predictions/sec")

    # 获取性能统计
    stats = engine.get_performance_stats()
    print(f"\n统计信息: {stats}")

# 运行诊断
asyncio.run(diagnose_prediction_performance())
```

**优化方案：**

1. 增加缓存命中率
2. 使用批量预测
3. 优化特征计算
4. 启用模型预加载

## API 问题

### 问题 1: 429 Too Many Requests

**解决方案：**

1. 实现速率限制
```python
# ratelimit.py
from fastapi import HTTPException, Request
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

@app.exception_handler(_rate_limit_exceeded_handler)
async def rate_limit_exception_handler(request: Request, exc):
    raise HTTPException(
        status_code=429,
        detail="Too many requests. Please try again later."
    )
```

2. 增加缓存
```python
# 带缓存的 API 端点
@app.get("/api/v1/predictions/match/{match_id}")
@limiter.limit("100/minute")
async def get_match_prediction(
    match_id: int,
    current_user: User = Depends(get_current_user)
):
    # 检查缓存
    cache_key = f"prediction:{match_id}"
    cached = await redis.get(cache_key)
    if cached:
        return cached

    # 执行预测
    result = await predict_match(match_id)
    await redis.set(cache_key, result, ex=1800)
    return result
```

### 问题 2: 503 Service Unavailable

**诊断步骤：**

```bash
# 检查服务状态
curl -I http://localhost:8000/api/health

# 检查进程
ps aux | grep uvicorn

# 检查端口
netstat -tlnp | grep :8000

# 检查系统资源
df -h
free -m
top
```

## 性能问题

### 1. 内存泄漏诊断

**诊断脚本：**

```python
# memory_profiler.py
import psutil
import tracemalloc

def diagnose_memory():
    """诊断内存使用"""
    process = psutil.Process()

    # 内存信息
    memory_info = process.memory_info()
    print(f"RSS: {memory_info.rss / 1024 / 1024:.1f} MB")
    print(f"VMS: {memory_info.vms / 1024 / 1024:.1f} MB")

    # 内存跟踪
    snapshot = tracemalloc.take_snapshot()
    top_stats = snapshot.statistics('lineno')
    print("\nTop memory allocations:")
    for stat in top_stats[:10]:
        print(f"  {stat.traceback}")
```

### 2. CPU 使用率高

**诊断步骤：**

```bash
# 查看进程状态
top -p $(pgrep -f football-prediction)

# 查看线程状态
ps -eLf | grep football-prediction

# 使用 py-spy 进行性能分析
pip install py-spy
py-spy top -- python -m uvicorn src.api.app:app
```

### 3. 响应时间慢

**端到端监控：**

```python
# performance_monitor.py
import time
from functools import wraps

def monitor_performance(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        start = time.time()
        try:
            result = await func(*args, **kwargs)
            status = "success"
        except Exception as e:
            result = None
            status = "error"
        finally:
            duration = time.time() - start
            logger.info(
                f"Performance: {func.__name__}",
                duration=duration,
                status=status
            )
        return result
    return wrapper

# 使用装饰器
@monitor_performance
async def predict_match(match_id: int):
    # ... 预测逻辑
    pass
```

## 监控和告警

### 设置 Grafana 告警

```json
{
  "dashboard": {
    "alerting": {
      "rules": [
        {
          "name": "预测服务异常",
          "conditions": [
            {
              "query": "up{job=\"football-prediction\"} == 0",
              "for": "1m"
            }
          ],
          "notifications": ["slack"]
        },
        {
          "name": "高错误率",
          "conditions": [
            {
              "query": "rate(http_requests_total{status=~\"5..\"}[5m]) / rate(http_requests_total[5m]) > 0.05",
              "for": "2m"
            }
          ]
        },
        {
          "name": "响应时间过长",
          "conditions": [
            {
              "query": "histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m])) > 1",
              "for": "5m"
            }
          ]
        }
      ]
    }
  }
}
```

### Slack 集成

```python
# slack_notifier.py
import requests
import json

class SlackNotifier:
    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url

    def send_alert(self, message: str, severity: str = "warning"):
        color = {
            "info": "good",
            "warning": "warning",
            "error": "danger"
        }.get(severity, "warning")

        payload = {
            "text": f"足球预测系统告警",
            "attachments": [
                {
                    "color": color,
                    "fields": [
                        {
                            "title": "严重程度",
                            "value": severity.upper(),
                            "short": True
                        },
                        {
                            "title": "时间",
                            "value": datetime.now().isoformat(),
                            "short": True
                        },
                        {
                            "title": "消息",
                            "value": message,
                            "short": False
                        }
                    ]
                }
            ]
        }

        try:
            requests.post(self.webhook_url, json=payload)
        except Exception as e:
            logger.error(f"发送 Slack 告警失败: {e}")

# 使用示例
notifier = SlackNotifier(os.getenv("SLACK_WEBHOOK_URL"))
notifier.send_alert("预测服务响应时间超过5秒", "warning")
```

## 常用命令速查

```bash
# 查看服务状态
systemctl status football-prediction

# 查看最新日志
tail -f /var/log/football-prediction/app.log

# 重启服务
sudo systemctl restart football-prediction

# 查看进程
ps aux | grep football

# 查看端口
netstat -tlnp | grep :8000

# 测试 API
curl http://localhost:8000/api/health

# 查看数据库连接
psql $DATABASE_URL -c "SELECT count(*) FROM matches;"

# 查看 Redis
redis-cli info memory

# 运行测试
pytest tests/

# 查看系统资源
htop
```

## 联系支持

如果问题仍未解决，请收集以下信息：

1. **系统信息**
   ```bash
   uname -a
   python --version
   pip list | grep -E "(fastapi|uvicorn|sqlalchemy|redis)"
   ```

2. **配置信息**
   ```bash
   cat .env | grep -v "PASSWORD\|SECRET\|TOKEN"
   ```

3. **日志文件**
   ```bash
   journalctl -u football-prediction --since "10 minutes ago" > system.log
   tail -100 /var/log/football-prediction/app.log > app.log
   ```

4. **错误信息**
   ```bash
   # 提供完整的错误堆栈
   ```

发送至：support@football-prediction.com