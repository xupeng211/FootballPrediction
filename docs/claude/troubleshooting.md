# 故障排除指南

本文档提供FootballPrediction项目的常见问题解决方案、故障诊断方法和应急处理流程。

---

## 📋 目录

- [🚨 快速故障响应](#-快速故障响应)
- [🔍 常见问题诊断](#-常见问题诊断)
- [⚡ 紧急修复方案](#-紧急修复方案)
- [🔧 系统故障排查](#-系统故障排查)
- [🗄️ 数据库问题](#️-数据库问题)
- [💾 缓存问题](#-缓存问题)
- [🌐 API问题](#-api问题)
- [🧪 测试问题](#-测试问题)
- [🔧 开发环境问题](#-开发环境问题)
- [📊 性能问题](#-性能问题)
- [🛡️ 安全问题](#-安全问题)
- [📋 预防性维护](#-预防性维护)

---

## 🚨 快速故障响应

### 5分钟快速诊断流程

```bash
# 1️⃣ 系统健康检查（30秒）
make quick-health-check
# 等效命令：
curl -f http://localhost:8000/health && echo "✅ API正常" || echo "❌ API异常"

# 2️⃣ 容器状态检查（30秒）
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
# 检查所有关键容器是否运行正常

# 3️⃣ 资源使用检查（1分钟）
docker stats --no-stream | grep -E "(app|db|redis)"
# 确认CPU和内存使用率是否正常

# 4️⃣ 错误日志检查（2分钟）
docker-compose logs --tail=50 app | grep -i error
# 快速定位最近的应用错误

# 5️⃣ 数据库连接检查（1分钟）
docker-compose exec db pg_isready -U postgres && echo "✅ 数据库正常" || echo "❌ 数据库异常"
```

### 紧急命令备忘录

```bash
# 🚨 紧急重启（1分钟内解决）
make emergency-restart
# 等效命令：
docker-compose restart app db redis

# 🚨 紧急回滚（5分钟内解决）
make emergency-rollback
# 需要预先准备备份文件

# 🚨 快速恢复到可用状态
make quick-recovery
# 智能恢复脚本，自动诊断并修复常见问题

# 🚨 紧急测试验证
make emergency-test
# 运行核心功能的快速验证测试
```

---

## 🔍 常见问题诊断

### 问题分类诊断树

```
🚨 系统故障
├── 🔥 API无法访问
│   ├── 检查应用容器状态 → docker ps | grep app
│   ├── 检查端口占用 → netstat -tulpn | grep 8000
│   ├── 检查健康检查 → curl http://localhost:8000/health
│   └── 检查应用日志 → docker logs app
├── 🗄️ 数据库连接失败
│   ├── 检查数据库容器 → docker ps | grep db
│   ├── 检查连接字符串 → echo $DATABASE_URL
│   ├── 测试数据库连接 → docker exec db pg_isready
│   └── 检查数据库日志 → docker logs db
├── 💾 缓存连接失败
│   ├── 检查Redis容器 → docker ps | grep redis
│   ├── 测试Redis连接 → docker exec redis redis-cli ping
│   ├── 检查Redis内存 → docker exec redis redis-cli info memory
│   └── 检查Redis日志 → docker logs redis
└── 🐳 Docker容器问题
    ├── 检查Docker服务 → systemctl status docker
    ├── 检查磁盘空间 → df -h
    ├── 检查Docker日志 → journalctl -u docker
    └── 重启Docker服务 → systemctl restart docker
```

### 常见错误代码对照表

| 错误代码 | 错误描述 | 可能原因 | 解决方案 |
|---------|---------|---------|---------|
| **500** | 内部服务器错误 | 代码异常、数据库连接失败 | 检查应用日志、数据库连接 |
| **502** | 网关错误 | 后端服务不可用 | 检查应用容器状态 |
| **503** | 服务不可用 | 服务过载、配置错误 | 扩容、检查配置 |
| **504** | 网关超时 | 响应时间过长 | 优化性能、增加超时时间 |
| **429** | 请求过多 | API限流触发 | 减少请求频率、提升限流阈值 |

### 快速问题定位脚本

```bash
#!/bin/bash
# scripts/quick_diagnosis.sh

echo "🔍 快速问题诊断开始..."

# 问题类型检查
check_api() {
    echo "🌐 检查API服务..."
    if curl -f http://localhost:8000/health > /dev/null 2>&1; then
        echo "✅ API服务正常"
        return 0
    else
        echo "❌ API服务异常"
        return 1
    fi
}

check_database() {
    echo "🗄️ 检查数据库..."
    if docker-compose exec -T db pg_isready -U postgres > /dev/null 2>&1; then
        echo "✅ 数据库正常"
        return 0
    else
        echo "❌ 数据库异常"
        return 1
    fi
}

check_redis() {
    echo "💾 检查Redis..."
    if docker-compose exec -T redis redis-cli ping > /dev/null 2>&1; then
        echo "✅ Redis正常"
        return 0
    else
        echo "❌ Redis异常"
        return 1
    fi
}

check_containers() {
    echo "🐳 检查容器状态..."
    local failed_containers=$(docker ps --filter "status=exited" --format "{{.Names}}")
    if [ -z "$failed_containers" ]; then
        echo "✅ 所有容器正常运行"
        return 0
    else
        echo "❌ 以下容器异常: $failed_containers"
        return 1
    fi
}

check_resources() {
    echo "💾 检查资源使用..."
    local high_cpu=$(docker stats --no-stream --format "table {{.CPUPerc}}\t{{.Name}}" | grep -E "[8-9][0-9]+\.[0-9]+%")
    local high_mem=$(docker stats --no-stream --format "table {{.MemUsage}}\t{{.Name}}" | grep -E "G[8-9]|[0-9]+G")

    if [ -n "$high_cpu" ]; then
        echo "⚠️ CPU使用率过高: $high_cpu"
        return 1
    fi

    if [ -n "$high_mem" ]; then
        echo "⚠️ 内存使用过高: $high_mem"
        return 1
    fi

    echo "✅ 资源使用正常"
    return 0
}

# 执行检查
failed_checks=0

check_api || ((failed_checks++))
check_database || ((failed_checks++))
check_redis || ((failed_checks++))
check_containers || ((failed_checks++))
check_resources || ((failed_checks++))

echo ""
echo "📊 诊断结果: $failed_checks 个检查失败"

if [ $failed_checks -gt 0 ]; then
    echo "🔧 建议执行: make quick-recovery"
    exit 1
else
    echo "✅ 系统运行正常"
    exit 0
fi
```

---

## ⚡ 紧急修复方案

### 1级紧急修复（测试大量失败 >30%）

```bash
#!/bin/bash
# scripts/emergency_fix_level1.sh

set -e

echo "🚨 执行1级紧急修复..."

# 1. 智能质量修复
echo "🔧 执行智能质量修复..."
python3 scripts/smart_quality_fixer.py

# 2. 环境一致性检查
echo "🔍 检查环境一致性..."
make env-check

# 3. 依赖重新安装
echo "📦 重新安装依赖..."
pip install -r requirements.txt --force-reinstall

# 4. 缓存清理
echo "🧹 清理缓存..."
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -type f -name "*.pyc" -delete 2>/dev/null || true

# 5. 配置文件重置
echo "📝 重置配置文件..."
if [ ! -f .env ]; then
    cp .env.example .env
fi

# 6. 数据库重新初始化（仅测试环境）
if [ "$ENVIRONMENT" = "development" ] || [ "$ENVIRONMENT" = "test" ]; then
    echo "🗄️ 重新初始化测试数据库..."
    docker-compose down -v
    docker-compose up -d db
    sleep 10
    make migrate
fi

# 7. 服务重启
echo "🔄 重启服务..."
docker-compose restart

# 8. 验证修复结果
echo "🔍 验证修复结果..."
sleep 30
make test.smart

echo "✅ 1级紧急修复完成"
```

### 2级智能修复（代码质量问题）

```bash
#!/bin/bash
# scripts/intelligent_fix_level2.sh

set -e

echo "🔧 执行2级智能修复..."

# 1. 代码格式化
echo "📝 代码格式化..."
ruff format src/ tests/
ruff check src/ tests/ --fix

# 2. 导入优化
echo "📦 优化导入语句..."
ruff format src/ tests/

# 3. 语法检查和修复
echo "✅ 语法检查..."
python3 -m py_compile src/**/*.py || true

# 4. 类型检查修复
echo "🔍 类型检查..."
mypy src/ --ignore-missing-imports || true

# 5. 安全检查修复
echo "🛡️ 安全检查修复..."
bandit -r src/ -f json -o bandit-report.json || true

# 6. 依赖冲突解决
echo "🔧 解决依赖冲突..."
pip-check --update || true

# 7. 测试数据清理
echo "🧹 清理测试数据..."
pytest --collect-only -q | grep test_ | head -20

echo "✅ 2级智能修复完成"
```

### 3级环境修复（环境配置问题）

```bash
#!/bin/bash
# scripts/environment_fix_level3.sh

set -e

echo "🌍 执行3级环境修复..."

# 1. 环境变量检查和修复
echo "🔍 检查环境变量..."
required_vars=("DATABASE_URL" "REDIS_URL" "SECRET_KEY" "ENVIRONMENT")

for var in "${required_vars[@]}"; do
    if [ -z "${!var}" ]; then
        echo "❌ 缺少环境变量: $var"
        echo "🔧 设置默认值..."
        case $var in
            "DATABASE_URL")
                export DATABASE_URL="postgresql://postgres:password@localhost:5432/football_prediction"
                ;;
            "REDIS_URL")
                export REDIS_URL="redis://localhost:6379/0"
                ;;
            "SECRET_KEY")
                export SECRET_KEY="dev-secret-key-$(date +%s)"
                ;;
            "ENVIRONMENT")
                export ENVIRONMENT="development"
                ;;
        esac
    fi
done

# 2. Python环境检查
echo "🐍 检查Python环境..."
python_version=$(python3 --version 2>&1 | grep -oP '\d+\.\d+')
required_version="3.11"

if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" != "$required_version" ]; then
    echo "❌ Python版本过低，需要 >= $required_version"
    echo "🔧 建议升级Python版本"
else
    echo "✅ Python版本正常: $python_version"
fi

# 3. 虚拟环境检查
echo "📦 检查虚拟环境..."
if [ -z "$VIRTUAL_ENV" ]; then
    echo "⚠️ 未激活虚拟环境"
    if [ -d "venv" ]; then
        echo "🔧 激活虚拟环境..."
        source venv/bin/activate
    else
        echo "🔧 创建虚拟环境..."
        python3 -m venv venv
        source venv/bin/activate
        pip install -r requirements.txt
    fi
else
    echo "✅ 虚拟环境已激活"
fi

# 4. Docker环境检查
echo "🐳 检查Docker环境..."
if ! command -v docker &> /dev/null; then
    echo "❌ Docker未安装"
    echo "🔧 请安装Docker: https://docs.docker.com/get-docker/"
elif ! docker info &> /dev/null; then
    echo "❌ Docker服务未运行"
    echo "🔧 启动Docker服务..."
    sudo systemctl start docker
    sudo systemctl enable docker
else
    echo "✅ Docker环境正常"
fi

# 5. 端口冲突检查
echo "🔍 检查端口冲突..."
ports=(8000 5432 6379)
for port in "${ports[@]}"; do
    if lsof -i :$port &> /dev/null; then
        echo "⚠️ 端口 $port 已被占用"
        echo "🔧 检查占用进程..."
        lsof -i :$port
    else
        echo "✅ 端口 $port 可用"
    fi
done

# 6. 权限检查
echo "🔐 检查权限..."
if [ ! -w . ]; then
    echo "❌ 当前目录无写权限"
    echo "🔧 修复权限..."
    chmod -R 755 .
else
    echo "✅ 目录权限正常"
fi

echo "✅ 3级环境修复完成"
```

### 4级性能修复（性能优化）

```bash
#!/bin/bash
# scripts/performance_fix_level4.sh

set -e

echo "⚡ 执行4级性能修复..."

# 1. 数据库性能优化
echo "🗄️ 优化数据库性能..."
docker-compose exec db psql -U postgres -d football_prediction -c "
ANALYZE;
REINDEX DATABASE football_prediction;
VACUUM ANALYZE;
"

# 2. Redis内存优化
echo "💾 优化Redis内存..."
docker-compose exec redis redis-cli CONFIG SET maxmemory 256mb
docker-compose exec redis redis-cli CONFIG SET maxmemory-policy allkeys-lru

# 3. 应用缓存清理
echo "🧹 清理应用缓存..."
docker-compose exec redis redis-cli FLUSHDB

# 4. 日志清理
echo "📝 清理日志文件..."
find ./logs -name "*.log" -type f -mtime +7 -delete 2>/dev/null || true
docker system prune -f

# 5. 临时文件清理
echo "🗂️ 清理临时文件..."
find /tmp -name "*football_prediction*" -type f -mtime +1 -delete 2>/dev/null || true

# 6. 进程优化
echo "⚙️ 优化进程配置..."
# 调整worker进程数量
cpu_cores=$(nproc)
export API_WORKERS=$((cpu_cores * 2 + 1))

# 7. 内存优化
echo "💾 内存优化..."
# 清理系统缓存
sudo sh -c 'echo 1 > /proc/sys/vm/drop_caches' 2>/dev/null || true

echo "✅ 4级性能修复完成"
```

---

## 🔧 系统故障排查

### Docker相关故障

#### 容器启动失败
```bash
# 诊断步骤
echo "🔍 诊断容器启动失败..."

# 1. 检查Docker服务状态
systemctl status docker

# 2. 检查容器日志
docker logs football-prediction-app
docker logs football-prediction-db
docker logs football-prediction-redis

# 3. 检查容器配置
docker-compose config

# 4. 强制清理并重启
docker-compose down -v
docker system prune -f
docker-compose up -d

# 5. 进入容器手动调试
docker-compose exec app bash
```

#### 磁盘空间不足
```bash
# 磁盘空间诊断和清理
echo "💾 磁盘空间诊断..."

# 1. 检查磁盘使用情况
df -h
du -sh /var/lib/docker/

# 2. 清理Docker资源
docker system prune -a -f
docker volume prune -f
docker network prune -f

# 3. 清理应用日志
find ./logs -name "*.log" -size +100M -delete
docker-compose exec app find /app/logs -name "*.log" -size +50M -delete

# 4. 清理数据库日志
docker-compose exec db psql -U postgres -c "
SELECT pg_size_pretty(pg_database_size('football_prediction'));
"

# 5. 设置日志轮转
echo "📝 配置日志轮转..."
cat > /etc/logrotate.d/football-prediction << EOF
./logs/*.log {
    daily
    missingok
    rotate 7
    compress
    delaycompress
    notifempty
    copytruncate
}
EOF
```

### 网络连接问题

#### 端口占用和冲突
```bash
# 网络问题诊断
echo "🌐 网络问题诊断..."

# 1. 检查端口占用
netstat -tulpn | grep -E ":(8000|5432|6379)"

# 2. 检查防火墙状态
sudo ufw status
sudo iptables -L

# 3. 检查Docker网络
docker network ls
docker network inspect football-prediction_default

# 4. 重建网络
docker-compose down
docker network prune -f
docker-compose up -d

# 5. 测试连接
curl -I http://localhost:8000/health
telnet localhost 5432
telnet localhost 6379
```

---

## 🗄️ 数据库问题

### 连接问题

#### 数据库连接超时
```bash
# 数据库连接诊断
echo "🗄️ 数据库连接诊断..."

# 1. 检查数据库容器状态
docker ps | grep postgres

# 2. 检查数据库配置
docker-compose exec db cat /var/lib/postgresql/data/postgresql.conf | grep -E "(max_connections|listen_addresses)"

# 3. 测试连接
docker-compose exec db pg_isready -U postgres

# 4. 检查连接数
docker-compose exec db psql -U postgres -c "
SELECT count(*) FROM pg_stat_activity;
"

# 5. 检查慢查询
docker-compose exec db psql -U postgres -d football_prediction -c "
SELECT query, mean_time, calls
FROM pg_stat_statements
ORDER BY mean_time DESC
LIMIT 10;
"

# 6. 优化连接配置
echo "🔧 优化数据库连接..."
docker-compose exec db psql -U postgres -c "
ALTER SYSTEM SET max_connections = 200;
ALTER SYSTEM SET shared_buffers = '256MB';
ALTER SYSTEM SET effective_cache_size = '1GB';
SELECT pg_reload_conf();
"
```

#### 数据库锁问题
```bash
# 锁问题诊断
echo "🔒 数据库锁诊断..."

# 1. 检查当前锁
docker-compose exec db psql -U postgres -d football_prediction -c "
SELECT
    blocked_locks.pid AS blocked_pid,
    blocked_activity.usename AS blocked_user,
    blocking_locks.pid AS blocking_pid,
    blocking_activity.usename AS blocking_user,
    blocked_activity.query AS blocked_statement,
    blocking_activity.query AS current_statement_in_blocking_process
FROM pg_catalog.pg_locks blocked_locks
    JOIN pg_catalog.pg_stat_activity blocked_activity ON blocked_activity.pid = blocked_locks.pid
    JOIN pg_catalog.pg_locks blocking_locks
        ON blocking_locks.locktype = blocked_locks.locktype
        AND blocking_locks.DATABASE IS NOT DISTINCT FROM blocked_locks.DATABASE
        AND blocking_locks.relation IS NOT DISTINCT FROM blocked_locks.relation
        AND blocking_locks.page IS NOT DISTINCT FROM blocked_locks.page
        AND blocking_locks.tuple IS NOT DISTINCT FROM blocked_locks.tuple
        AND blocking_locks.virtualxid IS NOT DISTINCT FROM blocked_locks.virtualxid
        AND blocking_locks.transactionid IS NOT DISTINCT FROM blocked_locks.transactionid
        AND blocking_locks.classid IS NOT DISTINCT FROM blocked_locks.classid
        AND blocking_locks.objid IS NOT DISTINCT FROM blocked_locks.objid
        AND blocking_locks.objsubid IS NOT DISTINCT FROM blocked_locks.objsubid
        AND blocking_locks.pid != blocked_locks.pid
    JOIN pg_catalog.pg_stat_activity blocking_activity ON blocking_activity.pid = blocking_locks.pid
WHERE NOT blocked_locks.GRANTED;
"

# 2. 终止长时间运行的查询
docker-compose exec db psql -U postgres -c "
SELECT pg_terminate_backend(pid)
FROM pg_stat_activity
WHERE state = 'active'
AND query_start < now() - interval '5 minutes';
"
```

### 数据损坏恢复

#### 数据文件损坏
```bash
# 数据恢复流程
echo "🔄 数据恢复流程..."

# 1. 停止应用避免进一步损坏
docker-compose stop app

# 2. 备份当前损坏数据
docker-compose exec db pg_dump -U postgres -Fc football_prediction > /tmp/corrupted_backup.dump

# 3. 检查数据完整性
docker-compose exec db psql -U postgres -d football_prediction -c "
SELECT
    schemaname,
    tablename,
    attname,
    n_distinct,
    correlation
FROM pg_stats
WHERE schemaname = 'public';
"

# 4. 从备份恢复
LATEST_BACKUP=$(ls -t /opt/backups/*.dump | head -1)
if [ -f "$LATEST_BACKUP" ]; then
    echo "🔄 从备份恢复数据: $LATEST_BACKUP"
    docker-compose exec -T db dropdb -U postgres football_prediction
    docker-compose exec -T db createdb -U postgres football_prediction
    docker-compose exec -T db pg_restore -U postgres -d football_prediction < "$LATEST_BACKUP"
else
    echo "❌ 找不到可用备份"
    exit 1
fi

# 5. 验证数据完整性
docker-compose exec db psql -U postgres -d football_prediction -c "
SELECT count(*) FROM predictions;
SELECT count(*) FROM matches;
SELECT count(*) FROM teams;
"

echo "✅ 数据恢复完成"
```

---

## 💾 缓存问题

### Redis连接和性能问题

#### Redis内存溢出
```bash
# Redis问题诊断
echo "💾 Redis问题诊断..."

# 1. 检查Redis状态
docker-compose exec redis redis-cli info server | grep -E "(redis_version|uptime_in_days)"

# 2. 检查内存使用
docker-compose exec redis redis-cli info memory | grep -E "(used_memory|maxmemory)"

# 3. 检查连接数
docker-compose exec redis redis-cli info clients

# 4. 检查慢查询
docker-compose exec redis redis-cli slowlog get 10

# 5. 清理过期键
docker-compose exec redis redis-cli --scan --pattern "fp:*" | wc -l
docker-compose exec redis redis-cli --scan --pattern "fp:*" | xargs docker-compose exec -T redis redis-cli del

# 6. 优化Redis配置
echo "🔧 优化Redis配置..."
docker-compose exec redis redis-cli CONFIG SET maxmemory 512mb
docker-compose exec redis redis-cli CONFIG SET maxmemory-policy allkeys-lru
docker-compose exec redis redis-cli CONFIG SET timeout 300

# 7. 重启Redis服务
docker-compose restart redis
```

#### 缓存一致性问题
```bash
# 缓存一致性修复
echo "🔄 缓存一致性修复..."

# 1. 清理应用缓存
docker-compose exec redis redis-cli FLUSHDB

# 2. 重新预热缓存
docker-compose exec app python3 -c "
import asyncio
from src.cache.redis_client import RedisClient
from src.cache.warmup import CacheWarmup

async def main():
    redis = RedisClient()
    warmup = CacheWarmup(redis)
    await warmup.warm_all()
    print('缓存预热完成')

asyncio.run(main())
"

# 3. 验证缓存状态
docker-compose exec redis redis-cli info keyspace
docker-compose exec redis redis-cli dbsize
```

---

## 🌐 API问题

### 应用服务故障

#### FastAPI启动失败
```bash
# API启动问题诊断
echo "🌐 API启动问题诊断..."

# 1. 检查应用日志
docker-compose logs app | tail -50

# 2. 检查配置文件
docker-compose exec app cat /app/.env

# 3. 检查Python环境
docker-compose exec app python3 --version
docker-compose exec app pip list | grep -E "(fastapi|uvicorn|sqlalchemy)"

# 4. 检查端口监听
docker-compose exec app netstat -tulpn | grep 8000

# 5. 手动启动测试
docker-compose exec app python3 -m uvicorn src.main:app --host 0.0.0.0 --port 8000

# 6. 检查导入问题
docker-compose exec app python3 -c "
try:
    from src.main import app
    print('✅ 主应用导入成功')
except Exception as e:
    print(f'❌ 主应用导入失败: {e}')

try:
    from src.database.base import Base
    print('✅ 数据库模型导入成功')
except Exception as e:
    print(f'❌ 数据库模型导入失败: {e}')
"
```

#### 性能问题
```bash
# API性能问题诊断
echo "⚡ API性能问题诊断..."

# 1. 检查响应时间
time curl -s http://localhost:8000/health

# 2. 检查并发处理能力
ab -n 100 -c 10 http://localhost:8000/health

# 3. 检查内存使用
docker stats football-prediction-app

# 4. 分析慢请求
docker-compose logs app | grep -E "(slow|timeout)" | tail -10

# 5. 检查数据库查询性能
docker-compose exec db psql -U postgres -d football_prediction -c "
SELECT
    query,
    mean_time,
    calls,
    total_time
FROM pg_stat_statements
ORDER BY mean_time DESC
LIMIT 5;
"

# 6. 优化应用配置
echo "🔧 优化应用配置..."
# 增加worker进程数量
export API_WORKERS=4

# 调整数据库连接池
export DB_POOL_SIZE=20
export DB_MAX_OVERFLOW=40
```

---

## 🧪 测试问题

### 测试执行失败

#### 测试环境问题
```bash
# 测试问题诊断
echo "🧪 测试问题诊断..."

# 1. 检查测试环境
make test-env-check

# 2. 检查测试数据库
docker-compose -f docker-compose.test.yml ps

# 3. 运行单个测试文件调试
pytest tests/unit/utils/test_date_utils.py -v -s

# 4. 检查测试覆盖率配置
pytest --collect-only | head -10

# 5. 清理测试数据
pytest --cleanup-on-failure

# 6. 重新创建测试环境
docker-compose -f docker-compose.test.yml down -v
docker-compose -f docker-compose.test.yml up -d
sleep 10
make test.db-init
```

#### 测试数据问题
```bash
# 测试数据修复
echo "📊 测试数据修复..."

# 1. 重新创建测试数据库
docker-compose exec -T test_db dropdb -U postgres test_fp
docker-compose exec -T test_db createdb -U postgres test_fp

# 2. 运行数据库迁移
docker-compose exec test_db alembic upgrade head

# 3. 生成测试数据
docker-compose exec app python3 -c "
from tests.factories.data_generator import TestDataGenerator
generator = TestDataGenerator()
generator.generate_all()
print('测试数据生成完成')
"

# 4. 验证测试数据
docker-compose exec test_db psql -U postgres -d test_fp -c "
SELECT count(*) FROM teams;
SELECT count(*) FROM matches;
SELECT count(*) FROM predictions;
"
```

---

## 🔧 开发环境问题

### 依赖和安装问题

#### Python依赖冲突
```bash
# 依赖问题修复
echo "📦 依赖问题修复..."

# 1. 清理pip缓存
pip cache purge

# 2. 重新创建虚拟环境
deactivate 2>/dev/null || true
rm -rf venv
python3 -m venv venv
source venv/bin/activate

# 3. 升级pip
pip install --upgrade pip setuptools wheel

# 4. 重新安装依赖
pip install -r requirements.txt
pip install -r requirements-dev.txt

# 5. 验证安装
python3 -c "import fastapi, sqlalchemy, redis; print('✅ 核心依赖安装成功')"

# 6. 检查依赖冲突
pip-check
```

### 配置问题

#### 环境变量配置错误
```bash
# 配置问题修复
echo "⚙️ 配置问题修复..."

# 1. 重新创建环境文件
cp .env.example .env

# 2. 设置开发环境变量
cat >> .env << EOF
# 开发环境配置
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=INFO
DATABASE_URL=postgresql://postgres:password@localhost:5432/football_prediction
REDIS_URL=redis://localhost:6379/0
SECRET_KEY=dev-secret-key-$(date +%s)
EOF

# 3. 验证配置
python3 -c "
import os
from dotenv import load_dotenv
load_dotenv()
required_vars = ['DATABASE_URL', 'REDIS_URL', 'SECRET_KEY']
missing = [var for var in required_vars if not os.getenv(var)]
if missing:
    print(f'❌ 缺少环境变量: {missing}')
else:
    print('✅ 环境变量配置正确')
"
```

---

## 📊 性能问题

### 系统性能优化

#### CPU和内存优化
```bash
# 性能问题诊断
echo "⚡ 性能问题诊断..."

# 1. 系统资源检查
top -b -n1 | head -20
free -h
iostat -x 1 5

# 2. Docker资源使用
docker stats --no-stream

# 3. 应用性能分析
docker-compose exec app python3 -c "
import psutil
import os
process = psutil.Process(os.getpid())
print(f'CPU使用率: {process.cpu_percent()}%')
print(f'内存使用: {process.memory_info().rss / 1024 / 1024:.2f}MB')
print(f'线程数: {process.num_threads()}')
"

# 4. 数据库性能检查
docker-compose exec db psql -U postgres -c "
SELECT
    datname,
    numbackends,
    xact_commit,
    xact_rollback,
    blks_read,
    blks_hit,
    tup_returned,
    tup_fetched,
    tup_inserted,
    tup_updated,
    tup_deleted
FROM pg_stat_database
WHERE datname = 'football_prediction';
"

# 5. 优化建议
echo "🔧 性能优化建议..."
echo "1. 增加应用worker数量: export API_WORKERS=4"
echo "2. 优化数据库连接池: export DB_POOL_SIZE=20"
echo "3. 启用应用缓存: export CACHE_ENABLED=true"
echo "4. 压缩日志文件: logrotate"
echo "5. 使用Redis缓存: export REDIS_CACHE_TTL=3600"
```

### 数据库性能调优

#### 查询优化
```bash
# 数据库性能优化
echo "🗄️ 数据库性能优化..."

# 1. 分析慢查询
docker-compose exec db psql -U postgres -d football_prediction -c "
SELECT
    query,
    calls,
    total_time,
    mean_time,
    stddev_time
FROM pg_stat_statements
WHERE mean_time > 1000
ORDER BY mean_time DESC
LIMIT 10;
"

# 2. 检查索引使用情况
docker-compose exec db psql -U postgres -d football_prediction -c "
SELECT
    schemaname,
    tablename,
    attname,
    n_distinct,
    correlation
FROM pg_stats
WHERE schemaname = 'public'
ORDER BY tablename, attname;
"

# 3. 创建必要索引
docker-compose exec db psql -U postgres -d football_prediction -c "
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_predictions_match_created
ON predictions(match_id, created_at);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_matches_date_status
ON matches(match_date, status);

ANALYZE predictions;
ANALYZE matches;
"

# 4. 更新表统计信息
docker-compose exec db psql -U postgres -d football_prediction -c "
ANALYZE;
VACUUM ANALYZE;
"
```

---

## 🛡️ 安全问题

### 安全漏洞修复

#### 依赖安全漏洞
```bash
# 安全问题修复
echo "🛡️ 安全问题修复..."

# 1. 检查依赖漏洞
pip-audit
safety check

# 2. 修复安全漏洞
pip install --upgrade package_name

# 3. 代码安全扫描
bandit -r src/ -f json -o security_report.json

# 4. 配置安全检查
# 检查敏感信息泄露
grep -r -i "password\|secret\|key" --exclude-dir=.git src/ || echo "✅ 未发现硬编码敏感信息"

# 5. 权限检查
find . -type f -name "*.py" -exec chmod 644 {} \;
find . -type d -exec chmod 755 {} \;

# 6. SSL证书检查
if [ -f "./nginx/ssl/cert.pem" ]; then
    openssl x509 -in ./nginx/ssl/cert.pem -text -noout | grep -E "(Not Before|Not After)"
else
    echo "⚠️ 未找到SSL证书"
fi
```

### 访问控制问题

#### 认证授权问题
```bash
# 访问控制修复
echo "🔐 访问控制修复..."

# 1. 检查JWT密钥强度
if [ ${#SECRET_KEY} -lt 32 ]; then
    echo "❌ JWT密钥强度不足"
    echo "🔧 生成新的强密钥..."
    export SECRET_KEY=$(openssl rand -hex 32)
fi

# 2. 检查密码策略
# 验证密码复杂度要求
python3 -c "
import re
def check_password_strength(password):
    if len(password) < 8:
        return False
    if not re.search(r'[A-Z]', password):
        return False
    if not re.search(r'[a-z]', password):
        return False
    if not re.search(r'\d', password):
        return False
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        return False
    return True

test_passwords = ['Password123!', 'weak', 'STRONG123!']
for pwd in test_passwords:
    result = check_password_strength(pwd)
    print(f'密码 {pwd}: {\"通过\" if result else \"失败\"}')
"

# 3. 检查API访问控制
curl -H "Authorization: Bearer invalid_token" http://localhost:8000/api/predictions
# 应该返回401未授权

# 4. 检查CORS配置
curl -H "Origin: http://malicious-site.com" http://localhost:8000/health
# 检查CORS头是否正确设置
```

---

## 📋 预防性维护

### 定期维护任务

#### 每日维护
```bash
#!/bin/bash
# scripts/daily_maintenance.sh

echo "🔧 执行每日维护任务..."

# 1. 系统健康检查
make quick-health-check

# 2. 清理临时文件
find /tmp -name "*football_prediction*" -mtime +1 -delete

# 3. 检查磁盘空间
df -h | grep -E "9[0-9]%" && echo "⚠️ 磁盘空间不足" || echo "✅ 磁盘空间充足"

# 4. 备份关键数据
make backup

# 5. 更新安全扫描
make security-scan

# 6. 性能监控
make performance-check

echo "✅ 每日维护完成"
```

#### 每周维护
```bash
#!/bin/bash
# scripts/weekly_maintenance.sh

echo "🔧 执行每周维护任务..."

# 1. 完整系统检查
make full-health-check

# 2. 依赖更新检查
pip list --outdated

# 3. 数据库优化
docker-compose exec db psql -U postgres -c "
VACUUM ANALYZE;
REINDEX DATABASE football_prediction;
"

# 4. 日志轮转
logrotate /etc/logrotate.d/football-prediction

# 5. 缓存清理
docker-compose exec redis redis-cli FLUSHDB

# 6. 备份验证
make backup-verify

echo "✅ 每周维护完成"
```

### 监控和告警

#### 系统监控配置
```python
# src/monitoring/health_monitor.py
import asyncio
import aiohttp
import logging
from typing import List, Dict

class HealthMonitor:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.checks = [
            self.check_api_health,
            self.check_database_health,
            self.check_redis_health,
            self.check_disk_space,
            self.check_memory_usage
        ]

    async def monitor(self):
        """持续监控系统健康状态"""
        while True:
            try:
                await self.run_health_checks()
                await asyncio.sleep(60)  # 每分钟检查一次
            except Exception as e:
                self.logger.error(f"健康监控异常: {e}")

    async def run_health_checks(self):
        """运行所有健康检查"""
        failed_checks = []

        for check in self.checks:
            try:
                result = await check()
                if not result:
                    failed_checks.append(check.__name__)
            except Exception as e:
                self.logger.error(f"健康检查失败 {check.__name__}: {e}")
                failed_checks.append(check.__name__)

        if failed_checks:
            await self.send_alert("健康检查失败", f"失败的检查: {', '.join(failed_checks)}")

    async def check_api_health(self) -> bool:
        """检查API健康状态"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get('http://localhost:8000/health') as response:
                    return response.status == 200
        except:
            return False

    async def check_database_health(self) -> bool:
        """检查数据库健康状态"""
        try:
            import asyncpg
            conn = await asyncpg.connect("postgresql://postgres:password@localhost:5432/football_prediction")
            await conn.execute('SELECT 1')
            await conn.close()
            return True
        except:
            return False

    async def check_redis_health(self) -> bool:
        """检查Redis健康状态"""
        try:
            import aioredis
            redis = aioredis.from_url("redis://localhost:6379/0")
            await redis.ping()
            await redis.close()
            return True
        except:
            return False

    async def check_disk_space(self) -> bool:
        """检查磁盘空间"""
        import shutil
        total, used, free = shutil.disk_usage("/")
        return (free / total) > 0.1  # 剩余空间大于10%

    async def check_memory_usage(self) -> bool:
        """检查内存使用"""
        import psutil
        return psutil.virtual_memory().percent < 90

    async def send_alert(self, title: str, message: str):
        """发送告警"""
        # 这里可以集成邮件、Slack或其他告警系统
        self.logger.error(f"告警: {title} - {message}")
```

---

## 🎯 故障排除最佳实践

### 1. 问题分类优先级

| 级别 | 问题类型 | 响应时间 | 解决方案 |
|------|---------|---------|---------|
| **P0** | 系统完全不可用 | 5分钟 | 紧急重启、回滚 |
| **P1** | 核心功能异常 | 30分钟 | 智能修复、配置调整 |
| **P2** | 性能下降 | 2小时 | 优化调优、资源扩容 |
| **P3** | 非核心问题 | 1天 | 计划修复、版本更新 |

### 2. 故障响应流程

```bash
# 标准故障响应流程
1. 🚨 问题发现和确认
   make quick-diagnosis

2. 🔍 问题定位和分析
   make detailed-diagnosis

3. 🔧 实施修复方案
   make emergency-fix 或 make intelligent-fix

4. ✅ 验证修复效果
   make post-fix-verification

5. 📊 根因分析和文档化
   make root-cause-analysis

6. 🔒 预防措施实施
   make preventive-measures
```

### 3. 关键命令速查

```bash
# 紧急情况快速命令
make emergency-restart        # 紧急重启所有服务
make quick-recovery          # 智能恢复常用问题
make solve-test-crisis       # 解决测试危机
make ci-auto-fix            # CI自动修复
make emergency-rollback      # 紧急回滚
make health-check           # 完整健康检查
make backup                # 紧急备份
make monitor-logs          # 实时日志监控
```

### 4. 联系信息和升级路径

- **开发团队**: dev-team@company.com
- **运维团队**: ops-team@company.com
- **紧急热线**: +86-xxx-xxxx-xxxx
- **升级路径**: 本地修复 → 团队协助 → 管理层介入

---

*文档版本: v1.0 | 更新时间: 2025-11-16*