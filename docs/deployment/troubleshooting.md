# 故障排查指南

## 目录

1. [快速诊断](#快速诊断)
2. [常见问题](#常见问题)
3. [系统故障](#系统故障)
4. [应用故障](#应用故障)
5. [数据库故障](#数据库故障)
6. [网络故障](#网络故障)
7. [性能问题](#性能问题)
8. [安全事故](#安全事故)
9. [联系支持](#联系支持)

## 快速诊断

### 系统状态检查脚本

```bash
#!/bin/bash
# quick_diagnosis.sh

echo "=== Football Prediction 系统快速诊断 ==="
echo "时间: $(date)"
echo ""

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# 检查函数
check_service() {
    local service=$1
    local port=$2

    if nc -z localhost $port 2>/dev/null; then
        echo -e "${GREEN}✓${NC} $service (端口 $port) - 正常"
        return 0
    else
        echo -e "${RED}✗${NC} $service (端口 $port) - 异常"
        return 1
    fi
}

# 1. 检查关键服务
echo "=== 服务状态检查 ==="
check_service "API服务" 8000
check_service "PostgreSQL" 5432
check_service "Redis" 6379
check_service "Nginx" 80
check_service "Prometheus" 9090
check_service "Grafana" 3000

echo ""

# 2. 检查Docker容器
echo "=== Docker容器状态 ==="
docker-compose ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}"

echo ""

# 3. 检查系统资源
echo "=== 系统资源 ==="
echo "CPU使用率:"
top -bn1 | grep "Cpu(s)" | awk '{print "  " $2}'

echo "内存使用:"
free -h | grep "Mem:" | awk '{print "  " $2 " / " $3 " (" int($3/$2 * 100) "%)"}'

echo "磁盘使用:"
df -h | grep -E "/dev/" | awk '{print "  " $1 " " $5 " (" $4 " 可用)"}'

echo ""

# 4. 检查错误日志
echo "=== 最近错误日志 ==="
if [ -f "logs/api/app.log" ]; then
    ERROR_COUNT=$(tail -n 1000 logs/api/app.log | grep -c "ERROR" || echo 0)
    echo "API服务最近1000行日志中的错误数: $ERROR_COUNT"

    if [ $ERROR_COUNT -gt 0 ]; then
        echo "最近的错误:"
        tail -n 1000 logs/api/app.log | grep ERROR | tail -5
    fi
fi

echo ""

# 5. 检查网络连接
echo "=== 网络连接 ==="
echo "监听端口:"
netstat -tuln | grep LISTEN | grep -E ":(80|443|8000|5432|6379|9090|3000)"

echo ""

# 6. 快速健康检查
echo "=== 快速健康检查 ==="
HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/api/health 2>/dev/null)
if [ "$HTTP_STATUS" = "200" ]; then
    echo -e "${GREEN}✓${NC} API健康检查通过"
else
    echo -e "${RED}✗${NC} API健康检查失败 (HTTP $HTTP_STATUS)"
fi

echo ""
echo "=== 诊断完成 ==="
```

## 常见问题

### 1. 服务无法启动

#### API服务启动失败

**症状**：
- Docker容器启动后立即退出
- 端口8000无法访问
- 日志显示启动错误

**排查步骤**：

```bash
# 1. 查看详细日志
docker-compose logs api

# 2. 检查配置文件
docker-compose config

# 3. 检查环境变量
docker-compose exec api env | grep -E "(DATABASE_URL|REDIS_URL|SECRET_KEY)"

# 4. 检查端口占用
netstat -tulpn | grep 8000

# 5. 手动启动调试
docker-compose run --rm api bash
python -m uvicorn src.api.app:app --host 0.0.0.0 --port 8000
```

**常见原因**：
- 数据库连接失败
- 端口被占用
- 环境变量配置错误
- 依赖包缺失
- 权限问题

**解决方案**：

```bash
# 数据库连接问题
# 检查数据库是否运行
docker-compose ps postgres

# 测试连接
docker-compose exec postgres pg_isready

# 重建数据库容器
docker-compose down postgres
docker-compose up -d postgres

# 端口占用问题
# 找到占用进程
lsof -i :8000

# 终止进程
kill -9 <PID>

# 环境变量问题
# 验证配置
docker-compose config

# 重新加载环境变量
docker-compose down
docker-compose up -d
```

#### 数据库启动失败

**症状**：
- PostgreSQL容器无法启动
- 数据目录权限错误
- 配置文件错误

**排查步骤**：

```bash
# 1. 查看PostgreSQL日志
docker-compose logs postgres

# 2. 检查数据目录权限
ls -la docker/volumes/postgres/

# 3. 检查配置文件
docker-compose exec postgres cat /var/lib/postgresql/data/postgresql.conf

# 4. 初始化数据目录
docker-compose down postgres
sudo rm -rf docker/volumes/postgres/
docker-compose up -d postgres
```

#### Redis启动失败

**症状**：
- Redis容器启动失败
- 内存不足
- 配置错误

**排查步骤**：

```bash
# 1. 查看Redis日志
docker-compose logs redis

# 2. 检查系统内存
free -h

# 3. 测试配置文件
redis-server config/redis/redis.conf --test-memory

# 4. 清理Redis数据
docker-compose exec redis redis-cli FLUSHALL
```

### 2. 性能问题

#### API响应缓慢

**症状**：
- 请求响应时间 > 5秒
- CPU使用率高
- 数据库查询慢

**排查步骤**：

```bash
# 1. 检查系统负载
uptime
top

# 2. 检查API进程
ps aux | grep uvicorn

# 3. 查看慢查询
docker-compose exec postgres psql -U postgres -d football_prediction -c "
SELECT query, mean_time, calls
FROM pg_stat_statements
WHERE mean_time > 1000
ORDER BY mean_time DESC
LIMIT 10;
"

# 4. 检查缓存命中率
redis-cli -a $REDIS_PASSWORD info stats | grep keyspace
```

**解决方案**：

```bash
# 1. 优化数据库
python scripts/optimize-database.py

# 2. 增加缓存
redis-cli -a $REDIS_PASSWORD CONFIG SET maxmemory 2gb
redis-cli -a $REDIS_PASSWORD CONFIG SET maxmemory-policy allkeys-lru

# 3. 扩展API服务
docker-compose up -d --scale api=3
```

#### 数据库查询慢

**症状**：
- 查询执行时间长
- 锁等待
- 高CPU使用

**排查步骤**：

```bash
# 1. 查看活动查询
docker-compose exec postgres psql -U postgres -d football_prediction -c "
SELECT pid, age(clock_timestamp(), query_start), query
FROM pg_stat_activity
WHERE state = 'active'
ORDER BY age DESC;
"

# 2. 查看锁等待
docker-compose exec postgres psql -U postgres -d football_prediction -c "
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
"

# 3. 分析查询计划
docker-compose exec postgres psql -U postgres -d football_prediction -c "
EXPLAIN ANALYZE SELECT * FROM matches WHERE match_date > '2024-01-01';
"
```

### 3. 内存问题

#### 内存泄漏

**症状**：
- 内存使用持续增长
- 系统变慢
- OOM错误

**排查步骤**：

```bash
# 1. 监控内存使用
watch -n 1 'free -h'

# 2. 查看进程内存使用
ps aux --sort=-%mem | head -20

# 3. 查看Docker容器内存使用
docker stats

# 4. 检查Python对象泄漏
docker-compose exec api python -c "
import tracemalloc
tracemalloc.start()
# 运行一段时间后
snapshot = tracemalloc.take_snapshot()
top_stats = snapshot.statistics('lineno')
for stat in top_stats[:10]:
    print(stat)
"
```

#### Redis内存不足

**症状**：
- Redis内存使用率 > 90%
- 键被驱逐
- 性能下降

**排查步骤**：

```bash
# 1. 查看内存使用
redis-cli -a $REDIS_PASSWORD info memory

# 2. 查看大键
redis-cli -a $REDIS_PASSWORD --bigkeys

# 3. 查看键空间
redis-cli -a $REDIS_PASSWORD info keyspace

# 4. 分析内存使用
redis-cli -a $REDIS_PASSWORD memory usage *
```

**解决方案**：

```bash
# 1. 清理过期键
redis-cli -a $REDIS_PASSWORD --scan --pattern "*:expired*" | xargs redis-cli -a $REDIS_PASSWORD del

# 2. 优化内存使用
redis-cli -a $REDIS_PASSWORD CONFIG SET maxmemory-policy allkeys-lru

# 3. 增加内存
docker-compose stop redis
docker-compose up -d redis
```

## 系统故障

### 1. 完全服务中断

#### 所有服务不可访问

**紧急恢复步骤**：

```bash
#!/bin/bash
# emergency_restore.sh

echo "=== 紧急恢复程序启动 ==="

# 1. 检查系统状态
echo "1. 检查系统状态..."
systemctl status docker
systemctl status nginx

# 2. 重启Docker服务
echo "2. 重启Docker..."
systemctl restart docker

# 3. 清理Docker资源
echo "3. 清理Docker资源..."
docker system prune -f

# 4. 重新启动所有服务
echo "4. 启动服务..."
docker-compose down
docker-compose up -d

# 5. 等待服务启动
echo "5. 等待服务就绪..."
sleep 60

# 6. 验证服务
echo "6. 验证服务..."
services=("api:8000" "postgres:5432" "redis:6379")

for service in "${services[@]}"; do
    name=$(echo $service | cut -d: -f1)
    port=$(echo $service | cut -d: -f2)

    if nc -z localhost $port; then
        echo "✓ $name 恢复正常"
    else
        echo "✗ $name 仍有问题"
    fi
done

echo "=== 紧急恢复完成 ==="
```

### 2. 网络故障

#### 无法访问服务

**排查步骤**：

```bash
# 1. 检查网络接口
ip addr show

# 2. 检查路由表
ip route show

# 3. 检查防火墙
sudo ufw status
sudo iptables -L

# 4. 检查DNS
nslookup api.footballprediction.com

# 5. 检查负载均衡器
if systemctl status nginx >/dev/null 2>&1; then
    nginx -t
fi

# 6. 检查SSL证书
openssl s_client -connect api.footballprediction.com:443 -servername api.footballprediction.com
```

### 3. 磁盘故障

#### 磁盘空间不足

**紧急清理**：

```bash
#!/bin/bash
# emergency_cleanup.sh

echo "=== 紧急磁盘清理 ==="

# 1. 清理Docker
echo "清理Docker..."
docker system prune -a -f
docker volume prune -f

# 2. 清理日志
echo "清理日志..."
find logs/ -name "*.log" -mtime +7 -delete
journalctl --vacuum-time=7d

# 3. 清理临时文件
echo "清理临时文件..."
find /tmp -type f -mtime +1 -delete
find /var/tmp -type f -mtime +1 -delete

# 4. 清理备份文件
echo "清理旧备份..."
find backups/ -type f -mtime +30 -delete

# 5. 清理包缓存
echo "清理包缓存..."
sudo apt autoclean
sudo apt autoremove -y

# 6. 检查磁盘使用
echo "当前磁盘使用："
df -h

echo "=== 清理完成 ==="
```

## 应用故障

### 1. API错误

#### 5xx服务器错误

**排查步骤**：

```bash
# 1. 查看API错误日志
tail -f logs/api/error.log

# 2. 查看应用异常
docker-compose logs api | grep ERROR

# 3. 检查应用健康状态
curl http://localhost:8000/api/health

# 4. 查看进程状态
docker-compose exec api ps aux
```

#### 4xx客户端错误

**排查步骤**：

```bash
# 1. 查看访问日志
tail -f logs/api/access.log | grep " 4[0-9][0-9] "

# 2. 检查认证问题
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"test","password":"test"}'

# 3. 检查API限流
curl -I http://localhost:8000/api/health
```

### 2. 认证失败

#### JWT令牌问题

**排查步骤**：

```bash
# 1. 检查JWT密钥配置
grep JWT_SECRET_KEY .env

# 2. 验证令牌
python -c "
import jwt
token = 'your-token-here'
try:
    payload = jwt.decode(token, 'your-secret-key', algorithms=['HS256'])
    print('Token valid:', payload)
except jwt.ExpiredSignatureError:
    print('Token expired')
except jwt.InvalidTokenError:
    print('Token invalid')
"

# 3. 检查令牌过期时间
python -c "
import jwt
import datetime
payload = {
    'exp': datetime.datetime.utcnow() + datetime.timedelta(minutes=30)
}
token = jwt.encode(payload, 'your-secret-key', algorithm='HS256')
print('New token:', token)
"
```

### 3. 任务队列问题

#### Celery任务失败

**排查步骤**：

```bash
# 1. 查看Celery日志
docker-compose logs celery-worker
docker-compose logs celery-beat

# 2. 检查任务状态
docker-compose exec celery-worker celery -A src.tasks.celery_app inspect active

# 3. 查看失败任务
docker-compose exec celery-worker celery -A src.tasks.celery_app inspect failed

# 4. 清空任务队列
docker-compose exec celery-worker celery -A src.tasks.celery_app purge

# 5. 重启Celery
docker-compose restart celery-worker celery-beat
```

## 数据库故障

### 1. 连接问题

#### 连接池耗尽

**症状**：
- 无法连接数据库
- "too many connections"错误

**排查步骤**：

```bash
# 1. 查看当前连接数
docker-compose exec postgres psql -U postgres -d football_prediction -c "
SELECT count(*) FROM pg_stat_activity;
"

# 2. 查看连接详情
docker-compose exec postgres psql -U postgres -d football_prediction -c "
SELECT pid, state, query
FROM pg_stat_activity
WHERE state = 'active';
"

# 3. 终止空闲连接
docker-compose exec postgres psql -U postgres -d football_prediction -c "
SELECT pg_terminate_backend(pid)
FROM pg_stat_activity
WHERE state = 'idle' AND query_start < now() - interval '1 hour';
"
```

### 2. 数据损坏

#### 表损坏

**恢复步骤**：

```bash
# 1. 停止应用
docker-compose stop api

# 2. 备份当前数据
docker-compose exec postgres pg_dump -U postgres football_prediction > emergency_backup.sql

# 3. 检查表完整性
docker-compose exec postgres psql -U postgres -d football_prediction -c "
SELECT schemaname, tablename, attname, n_distinct, correlation
FROM pg_stats
WHERE tablename = 'matches';
"

# 4. 重建表（如果需要）
docker-compose exec postgres psql -U postgres -d football_prediction -c "
CREATE TABLE matches_backup AS SELECT * FROM matches;
DROP TABLE matches;
CREATE TABLE matches (...); -- 重新创建
INSERT INTO matches SELECT * FROM matches_backup;
DROP TABLE matches_backup;
"

# 5. 恢复数据
docker-compose exec postgres psql -U postgres football_prediction < emergency_backup.sql
```

### 3. 主从复制问题

#### 复制延迟

**排查步骤**：

```bash
# 1. 查看复制状态
docker-compose exec postgres-replica psql -U postgres -c "
SELECT * FROM pg_stat_replication;
"

# 2. 查看延迟字节
docker-compose exec postgres-replica psql -U postgres -c "
SELECT * FROM pg_replication_slots;
"

# 3. 重建复制
docker-compose exec postgres-replica psql -U postgres -c "
SELECT pg_stop_backup();
"
```

## 网络故障

### 1. 负载均衡器问题

#### Nginx配置错误

**排查步骤**：

```bash
# 1. 测试Nginx配置
sudo nginx -t

# 2. 查看Nginx错误日志
sudo tail -f /var/log/nginx/error.log

# 3. 检查upstream状态
curl http://localhost/api/health

# 4. 重新加载配置
sudo nginx -s reload
```

### 2. SSL/TLS问题

#### 证书过期

**解决步骤**：

```bash
# 1. 检查证书有效期
openssl x509 -in config/ssl/server.crt -noout -dates

# 2. 更新Let's Encrypt证书
sudo certbot renew

# 3. 重新生成自签名证书
openssl req -x509 -newkey rsa:4096 -keyout config/ssl/server.key \
    -out config/ssl/server.crt -days 365 -nodes

# 4. 重启Nginx
sudo systemctl restart nginx
```

## 性能问题

### 1. 慢查询优化

#### 查询优化步骤

```sql
-- 1. 分析查询计划
EXPLAIN (ANALYZE, BUFFERS) SELECT * FROM matches WHERE date > '2024-01-01';

-- 2. 添加索引
CREATE INDEX CONCURRENTLY idx_matches_date ON matches(date);

-- 3. 优化查询
SELECT * FROM matches WHERE date >= '2024-01-01' AND date < '2024-02-01';

-- 4. 使用物化视图
CREATE MATERIALIZED VIEW daily_matches AS
SELECT date, COUNT(*) as match_count
FROM matches
GROUP BY date;

-- 5. 定期刷新物化视图
REFRESH MATERIALIZED VIEW daily_matches;
```

### 2. 缓存优化

#### Redis缓存策略

```bash
# 1. 查看缓存命中率
redis-cli -a $REDIS_PASSWORD info stats | grep keyspace

# 2. 优化缓存键设计
# 使用合理的TTL
redis-cli -a $REDIS_PASSWORD SET key value EX 3600

# 3. 使用批量操作
redis-cli -a $REDIS_PASSWORD MGET key1 key2 key3

# 4. 使用管道
redis-cli -a $REDIS_PASSWORD --pipe < commands.txt
```

## 安全事故

### 1. 安全漏洞处理

#### 发现漏洞后的应急响应

```bash
#!/bin/bash
# security_incident_response.sh

echo "=== 安全事件响应程序 ==="

# 1. 隔离系统
echo "1. 隔离受影响系统..."
# 断开网络或限制访问

# 2. 保存证据
echo "2. 保存证据..."
mkdir -p incident/evidence/$(date +%Y%m%d_%H%M%S)
docker logs > incident/evidence/$(date +%Y%m%d_%H%M%S)/docker_logs.log
cp -r logs/ incident/evidence/$(date +%Y%m%d_%H%M%S)/

# 3. 分析日志
echo "3. 分析访问日志..."
grep "ERROR\|WARNING" logs/api/*.log > incident/suspicious_activities.log

# 4. 更改密钥
echo "4. 更改所有密钥..."
openssl rand -base64 32 > new_jwt_secret
# 更新所有密码和密钥

# 5. 修补漏洞
echo "5. 修补漏洞..."
# 更新系统包
sudo apt update && sudo apt upgrade -y

# 6. 恢复服务
echo "6. 安全恢复服务..."
# 逐步恢复服务
```

### 2. DDoS攻击

#### DDoS防护措施

```bash
# 1. 识别攻击源
netstat -an | grep ESTABLISHED | awk '{print $5}' | cut -d: -f1 | sort | uniq -c | sort -nr

# 2. 配置Nginx限速
# 在nginx.conf中添加
limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
limit_req zone=api burst=20 nodelay;

# 3. 使用fail2ban
sudo apt install fail2ban
sudo systemctl enable fail2ban

# 4. 配置防火墙规则
sudo ufw limit 22/tcp
sudo ufw limit 80/tcp
sudo ufw limit 443/tcp
```

## 联系支持

### 紧急联系方式

- **DevOps团队**: devops@footballprediction.com
- **开发团队**: dev@footballprediction.com
- **安全团队**: security@footballprediction.com

### 报告问题

请提供以下信息：

1. 问题描述
2. 发生时间
3. 错误日志
4. 系统环境
5. 复现步骤

### 日志收集脚本

```bash
#!/bin/bash
# collect_logs.sh

LOG_DIR="incident_logs/$(date +%Y%m%d_%H%M%S)"
mkdir -p $LOG_DIR

echo "收集日志到 $LOG_DIR..."

# 收集系统日志
journalctl --since "1 hour ago" > $LOG_DIR/system.log

# 收集Docker日志
docker-compose logs --no-color > $LOG_DIR/docker.log

# 收集应用日志
cp -r logs/ $LOG_DIR/

# 收集配置文件
cp .env $LOG_DIR/env.txt
cp docker-compose.yml $LOG_DIR/

# 收集系统信息
uname -a > $LOG_DIR/system_info.txt
docker version > $LOG_DIR/docker_version.txt
df -h > $LOG_DIR/disk_usage.txt
free -h > $LOG_DIR/memory_usage.txt

# 压缩日志
tar -czf $LOG_DIR.tar.gz $LOG_DIR/

echo "日志已收集: $LOG_DIR.tar.gz"
```

---

**更新时间**: 2024-03-15
**版本**: 1.0.0
**维护者**: Football Prediction DevOps Team
