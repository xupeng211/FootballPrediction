# 🔧 Operations Handbook

## 运维手册

**版本**: v1.0
**最后更新**: 2025-10-31
**维护团队**: FootballPrediction DevOps Team

---

## 📋 目录

- [🚀 系统架构概览](#-系统架构概览)
- [📊 监控体系](#-监控体系)
- [🔧 日常运维](#-日常运维)
- [📱 备份与恢复](#-备份与恢复)
- [🔄 更新与部署](#-更新与部署)
- [🛡️ 安全管理](#-安全管理)
- [📊 性能优化](#-性能优化)
- [🔍 故障排查](#-故障排查)
- [📋 定期维护](#-定期维护)

## 🚀 系统架构概览

### 整体架构图
```
┌─────────────────┐    ┌─────────────┐    ┌─────────────┐
│    用户请求      │    │   Nginx      │    │  Grafana     │
│                 │    │   (80/443)   │    │  (3000)     │
└─────────────────┘    └─────────────┘    └─────────────┘
         │                   │               │
         ▼                   ▼               ▼
┌─────────────────┐    ┌─────────────┐    ┌─────────────┐
│   FastAPI       │    │  Prometheus  │    │  Loki        │
│   (8000)        │    │   (9090)    │    │  (3100)      │
└─────────────────┘�    └─────────────┘    └─────────────┘
         │                   │               │
         ▼                   ▼               ▼
┌─────────────────────────────────────────────────────────────┐
│                 Docker Compose Stack                      │
├─────────────────┬─────────────────┬─────────────────┬─────────────────┤
│      App       │      Database    │      Redis     │   Monitoring  │
│   (Python)    │   (PostgreSQL)   │     Cache     │   (Prometheus)  │
│   port: 8000  │   port: 5432    │    port: 6379  │   port: 9090   │
└─────────────────┴─────────────────┴─────────────────┴─────────────────┘
```

### 服务说明

| 服务 | 端口 | 描述 | 状态监控 |
|------|------|------|----------|
| Nginx | 80/443 | 反向代理和负载均衡 | ✅ |
| FastAPI | 8000 | 主应用服务 | ✅ |
| PostgreSQL | 5432 | 主数据库 | ✅ |
| Redis | 6379 | 缓存和会话存储 | ✅ |
| Prometheus | 9090 | 指标收集 | ✅ |
| Grafana | 3000 | 可视化面板 | ✅ |
| Loki | 3100 | 日志聚合 | ✅ |

## 📊 监控体系

### 监控架构
```
应用服务 → 指标导出 → Prometheus → Grafana → 告警通知
     ↓              ↓            ↓           ↓
   健康检查      日志文件      Loki → 可视化    Slack邮件
```

### 关键指标

#### 应用层指标
- **响应时间**: 95th百分位 < 200ms
- **错误率**: < 1%
- **吞吐量**: > 100 req/s
- **可用性**: > 99.9%

#### 系统层指标
- **CPU使用率**: < 80%
- **内存使用率**: < 85%
- **磁盘使用率**: < 90%
- **网络延迟**: < 50ms

#### 业务层指标
- **用户注册数**: 实时统计
- **预测请求数**: 实时统计
- **API调用量**: 实时统计
- **错误类型分布**: 分类统计

### 告警规则

#### 服务可用性告警
```yaml
groups:
  - name: service_availability
    rules:
      - alert: ServiceDown
        expr: up{job="football-prediction"} == 0
        for: 1m
        labels:
          severity: critical
          team: devops

      - alert: HighErrorRate
        expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.01
        for: 2m
        labels:
          severity: warning
          team: devops
```

#### 性能告警
```yaml
groups:
  - name: performance
    rules:
      - alert: HighResponseTime
        expr: histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m])) > 0.2
        for: 5m
        labels:
          severity: warning
          team: devops

      - alert: HighCPUUsage
        expr: 100 - (avg by instance) (rate(cpu_usage_total{job="football-prediction"}[5m])) > 80
        for: 10m
        labels:
          severity: warning
          team: devops
```

## 🔧 日常运维

### 每日检查清单 (9:00 AM)
```bash
#!/bin/bash
echo "🔍 每日系统检查 - $(date '+%Y-%m-%d %H:%M:%S')"

# 1. 服务状态检查
echo "📊 检查服务状态..."
docker-compose ps

# 2. 资源使用检查
echo "💾 检查资源使用..."
docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}"

# 3. 健康检查
echo "🏥 执行健康检查..."
curl -f http://localhost/health || echo "❌ 健康检查失败"

# 4. 日志检查
echo "📋 检查错误日志..."
error_count=$(docker-compose logs app 2>/dev/null | grep -c "ERROR" || echo "0")
if [ "$error_count" -gt 10 ]; then
    echo "⚠️ 发现 $error_count 个错误，需要关注"
fi

# 5. 备份状态检查
echo "💾 检查备份状态..."
last_backup=$(ls -lt /opt/football-prediction/backups/ | head -2 | tail -1 | awk '{print $9}')
echo "最新备份: $last_backup"

echo "✅ 每日检查完成"
```

### 每周维护任务 (周一 10:00 AM)
```bash
#!/bin/bash
echo "🔧 每周维护 - $(date '+%Y-%m-%d %H:%M:%S')"

# 1. 系统更新
echo "🔄 更新系统软件包..."
sudo apt update && sudo apt upgrade -y

# 2. Docker清理
echo "🧹 清理Docker资源..."
docker system prune -f
docker volume prune -f

# 3. 日志轮转
echo "📋 处理日志轮转..."
find /var/log/ -name "*.log" -mtime +30 -delete

# 4. 磁盘空间检查
echo "💽 检查磁盘空间..."
df -h

# 5. 备份验证
echo "💾 验证备份完整性..."
/opt/football-prediction/scripts/backup_verification.sh

echo "✅ 每周维护完成"
```

### 每月维护任务 (每月1号 10:00 AM)
```bash
#!/bin/bash
echo "📅 每月维护 - $(date '+%Y-%m-%d %H:%M:%S')"

# 1. 安全更新
echo "🔒 检查安全更新..."
sudo apt list --upgradable

# 2. 证书检查
echo "🔐 检查SSL证书..."
sudo certbot certificates

# 3. 性能报告
echo "📊 生成性能报告..."
/opt/football-prediction/scripts/generate_performance_report.sh

# 4. 容量规划
echo "📈 容量规划分析..."
df -h
docker system df

# 5. 监控报告
echo "📈 生成监控报告..."
/opt/football-prediction/scripts/generate_monitoring_report.sh

echo "✅ 每月维护完成"
```

## 📱 备份与恢复

### 备份策略

#### 数据库备份
```bash
#!/bin/bash
# backup_database.sh
BACKUP_DIR="/opt/football-prediction/backups"
DATE=$(date +%Y%m%d_%H%M%S)

# 创建备份目录
mkdir -p "$BACKUP_DIR"

# 执行数据库备份
docker-compose exec -T db pg_dump -U postgres football_prediction > "$BACKUP_DIR/db_backup_$DATE.sql"

# 压缩备份
gzip "$BACKUP_DIR/db_backup_$DATE.sql"

# 清理30天前的备份
find "$BACKUP_DIR" -name "db_backup_*.sql.gz" -mtime +30 -delete

echo "✅ 数据库备份完成: db_backup_$DATE.sql.gz"
```

#### 应用配置备份
```bash
#!/bin/bash
# backup_config.sh
BACKUP_DIR="/opt/football-prediction/backups"
DATE=$(date +%Y%m%d_%H%M%S)

# 备份配置文件
tar -czf "$BACKUP_DIR/config_backup_$DATE.tar.gz" \
    .env* \
    docker-compose*.yml \
    nginx/ \
    scripts/

echo "✅ 配置备份完成: config_backup_$DATE.tar.gz"
```

#### 自动备份配置
```bash
# /etc/cron.d/football-prediction
0 2 * * * /opt/football-prediction/scripts/backup_database.sh
0 14 * * * /opt/football-prediction/scripts/backup_config.sh
0 3 1 * * /opt/football-prediction/scripts/backup_verification.sh
```

### 恢复流程

#### 数据库恢复
```bash
#!/bin/bash
# restore_database.sh
BACKUP_FILE=$1

if [ -z "$BACKUP_FILE" ]; then
    echo "❌ 请提供备份文件路径"
    echo "用法: $0 <backup_file>"
    exit 1
fi

# 停止应用服务
echo "⏹ 停止应用服务..."
docker-compose down

# 恢复数据库
echo "🗄️ 恢复数据库..."
gunzip -c "$BACKUP_FILE" | docker-compose exec -T db psql -U postgres -d football_prediction

# 重启服务
echo "🚀 重启服务..."
docker-compose up -d

# 验证恢复
echo "🔍 验证恢复..."
docker-compose exec db psql -U postgres -d football_prediction -c "SELECT COUNT(*) FROM users;"

echo "✅ 数据库恢复完成"
```

#### 配置恢复
```bash
#!/bin/bash
# restore_config.sh
BACKUP_FILE=$1

if [ -z "$BACKUP_FILE" ]; then
    echo "❌ 请提供配置备份文件路径"
    echo "用法: $0 <config_backup.tar.gz>"
    exit 1
fi

# 恢复配置文件
echo "⚙️ 恢复配置文件..."
tar -xzf "$BACKUP_FILE" -C /

# 重启服务应用新配置
echo "🔄 重启服务..."
docker-compose down
docker-compose up -d

echo "✅ 配置恢复完成"
```

### 备份验证
```bash
#!/bin/bash
# backup_verification.sh
BACKUP_DIR="/opt/football-prediction/backups"

# 检查备份文件数量
backup_count=$(find "$BACKUP_DIR" -name "*.gz" | wc -l)
echo "📦 备份文件数量: $backup_count"

# 检查最近备份时间
latest_backup=$(find "$BACKUP_DIR" -name "*.gz" -printf "%T\n" | sort -n -r | head -1)
if [ -n "$latest_backup" ]; then
    echo "📅 最新备份时间: $(date -d @$latest_backup '+%Y-%m-%d %H:%M:%S')"
else
    echo "⚠️ 未找到备份文件"
fi

# 检查备份文件完整性
echo "🔍 检查备份文件完整性..."
find "$BACKUP_DIR" -name "*.gz" -exec gzip -t {} \; | grep -v OK | head -5
```

## 🔄 更新与部署

### 更新流程

#### 标准更新流程
```bash
#!/bin/bash
# update_application.sh
VERSION=$1

if [ -z "$VERSION" ]; then
    echo "❌ 请指定版本号"
    echo "用法: $0 <version>"
    exit 1
fi

echo "🔄 开始更新到版本: $VERSION"

# 1. 备份当前版本
echo "💾 备份当前版本..."
/opt/football-prediction/scripts/backup_database.sh
/opt/football-prediction/scripts/backup_config.sh

# 2. 获取新版本
echo "📥 获取新版本代码..."
git fetch origin
git checkout "$VERSION"

# 3. 构建新镜像
echo "🏗️ 构建Docker镜像..."
docker-compose build

# 4. 运行数据库迁移
echo "🗄️ 运行数据库迁移..."
docker-compose exec app alembic upgrade head

# 5. 重启服务
echo "🚀 重启服务..."
docker-compose down
docker-compose up -d

# 6. 验证部署
echo "🔍 验证部署..."
sleep 30
curl -f http://localhost/health || echo "❌ 部署验证失败"

echo "✅ 更新完成"
```

#### 蓝绿部署
```bash
#!/bin/bash
# blue_green_deploy.sh
NEW_VERSION=$1

if [ -z "$NEW_VERSION" ]; then
    echo "❌ 请指定新版本号"
    exit 1
fi

echo "🔵 执行蓝绿部署到: $NEW_VERSION"

# 1. 获取当前运行的容器
CURRENT_CONTAINERS=$(docker-compose ps -q)
ACTIVE_CONTAINER=$(echo "$CURRENT_CONTAINERS" | head -1)
BACKUP_CONTAINER=$(echo "$CURRENT_CONTAINERS" | tail -1)

echo "当前活跃容器: $ACTIVE_CONTAINER"
echo "备份容器: $BACKUP_CONTAINER"

# 2. 部署新版本到备份容器
echo "🚀 部署新版本到备份容器..."
docker-compose up -d --scale app=2

# 3. 等待新版本就绪
echo "⏳ 等待新版本就绪..."
sleep 60

# 4. 健康检查
for i in {1..30}; do
    if curl -f http://localhost/health; then
        echo "✅ 新版本就绪"
        break
    fi
    sleep 2
done

# 5. 切换流量到新版本
echo "🔄 切换流量到新版本..."
# 这里需要实际的负载均衡器配置

# 6. 停止旧版本
echo "⏹ 停止旧版本..."
docker-compose up -d --scale app=1

echo "✅ 蓝绿部署完成"
```

### 部署脚本

#### 快速部署脚本
```bash
#!/bin/bash
# deploy_quick.sh

echo "🚀 快速部署..."

# 更新代码
git pull origin main

# 重新构建并部署
docker-compose down
docker-compose up -d --build

# 验证部署
sleep 30
curl -f http://localhost/health

echo "✅ 快速部署完成"
```

#### 生产部署脚本
```bash
#!/bin/bash
# deploy_production.sh

echo "🏭️ 生产环境部署..."

# 环境检查
/opt/football-prediction/scripts/production-deployment-verification.sh

# 执行部署
ENV=production docker-compose --profile production up -d

# 验证部署
/opt/football-prediction/scripts/verify-deployment.sh

echo "✅ 生产部署完成"
```

## 🛡️ 安全管理

### 安全检查清单

#### 每日安全检查
```bash
#!/bin/bash
# daily_security_check.sh

echo "🔒 每日安全检查 - $(date '+%Y-%m-%d')"

# 1. 检查异常登录
echo "👥 检查异常登录..."
sudo grep "Failed password" /var/log/auth.log | tail -10

# 2. 检查开放端口
echo "🌐 检查开放端口..."
ss -tulpn | grep LISTEN

# 3. 检查文件权限
echo "📁 检查文件权限..."
find /opt/football-prediction -type f -perm /o+w -ls -l

# 4. 安全扫描
echo "🔍 运行安全扫描..."
python3 scripts/security_scan.py

echo "✅ 每日安全检查完成"
```

#### 每周安全扫描
```bash
#!/bin/bash
# weekly_security_scan.sh

echo "🔒 每周安全扫描 - $(date '+%Y-%m-%d')"

# 1. 代码安全扫描
echo "🐍 运行代码安全扫描..."
bandit -r src/ -f json -o bandit_report.json

# 2. 依赖安全扫描
echo "📦 检查依赖安全..."
safety check --json --output safety_report.json

# 3. 容器安全扫描
echo "🐳 扫行容器安全扫描..."
docker run --rm -v /var/run/docker.sock:/var/run/docker.sock \
    aquasecsec scan football-prediction:latest

# 4. 生成安全报告
echo "📊 生成安全报告..."
python3 scripts/generate_security_report.py

echo "✅ 每周安全扫描完成"
```

### 安全配置

#### SSH安全配置
```bash
# /etc/ssh/sshd_config
Port 2222                    # 非标准端口
PermitRootLogin no
PasswordAuthentication no
PubkeyAuthentication yes
MaxAuthTries 3
ClientAliveInterval 300
ClientAliveCountMax 2
```

#### 防火墙配置
```bash
#!/bin/bash
# setup_firewall.sh

echo "🔥 配置防火墙..."

# 基础规则
ufw default deny incoming
ufw allow ssh
ufw allow 80/tcp
ufw allow 443/tcp

# 允许已建立的连接
ufw allow established
ufw allow related

# 启用防火墙
ufw enable

echo "✅ 防火墙配置完成"
```

## 📊 性能优化

### 性能监控
```python
# performance_monitor.py
import psutil
import time
import requests

def check_performance():
    while True:
        # 系统指标
        cpu_percent = psutil.cpu_percent(interval=1)
        memory_percent = psutil.virtual_memory().percent
        disk_percent = psutil.disk_usage('/').percent

        # 应用指标
        response_time = measure_response_time()

        # 记录指标
        print(f"CPU: {cpu_percent}%, Memory: {memory_percent}%, Disk: {disk_percent}%, Response: {response_time:.3f}s")

        # 检查告警条件
        if cpu_percent > 80:
            send_alert(f"High CPU usage: {cpu_percent}%")
        if memory_percent > 85:
            send_alert(f"High memory usage: {memory_percent}%")
        if response_time > 2.0:
            send_alert(f"High response time: {response_time:.3f}s")

        time.sleep(60)

def measure_response_time():
    try:
        start_time = time.time()
        response = requests.get("http://localhost/health", timeout=10)
        end_time = time.time()
        return end_time - start_time
    except:
        return 0.0

def send_alert(message):
    print(f"🚨 ALERT: {message}")
    # 这里可以添加Slack/邮件通知
```

### 性能优化建议

#### 数据库优化
```sql
-- 创建索引优化
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_predictions_created_at ON predictions(created_at);

-- 分析慢查询
SELECT query, mean_time, calls
FROM pg_stat_statements
WHERE mean_time > 100
ORDER BY mean_time DESC
LIMIT 10;
```

#### 缓存优化
```python
# cache_optimization.py
import redis
from datetime import timedelta

class CacheOptimizer:
    def __init__(self):
        self.redis = redis.Redis()
        self.default_ttl = 3600  # 1小时

    def cache_with_ttl(self, key, value, ttl=None):
        ttl = ttl or self.default_ttl
        self.redis.setex(key, ttl, value)

    def cache_result(self, func, ttl=None):
        def wrapper(*args, **kwargs):
            cache_key = f"result:{func.__name__}:{hash(str(args) + str(kwargs))}"

            # 尝试从缓存获取
            cached_result = self.redis.get(cache_key)
            if cached_result:
                return json.loads(cached_result)

            # 执行函数并缓存结果
            result = func(*args, **kwargs)
            self.cache_with_ttl(cache_key, json.dumps(result), ttl)
            return result

        return wrapper
```

## 🔍 故障排查

### 常见问题诊断

#### 服务无法启动
```bash
#!/bin/bash
# troubleshoot_service_startup.sh

echo "🔍 服务启动故障排查"

# 1. 检查日志
echo "📋 检查服务日志..."
docker-compose logs app | tail -50

# 2. 检查配置
echo "⚙️ 检查配置文件..."
docker-compose config

# 3. 检查端口占用
echo "🌐 检查端口占用..."
netstat -tulpn | grep -E ":8000|:80|:443"

# 4. 检查资源
echo "💾 检查系统资源..."
free -h
df -h
docker stats --no-stream

# 5. 检查依赖
echo "📦 检查服务依赖..."
docker-compose exec app python -c "
try:
    import requests
    requests.get('http://localhost:8080', timeout=5)
    print('✅ HTTP服务正常')
except:
    print('❌ HTTP服务异常')
"
```

#### 数据库连接问题
```bash
#!/bin/bash
# troubleshoot_database.sh

echo "🗄️ 数据库连接故障排查"

# 1. 检查数据库状态
echo "📊 检查数据库状态..."
docker-compose exec db pg_isready -U postgres

# 2. 检查连接数
echo "🔗 检查连接数..."
docker-compose exec db psql -U postgres -c "SELECT count(*) FROM pg_stat_activity;"

# 3. 检查慢查询
echo "🐌 检查慢查询..."
docker-compose exec db psql -U postgres -c "
SELECT query, mean_time, calls
FROM pg_stat_statements
WHERE mean_time > 1000
ORDER BY mean_time DESC
LIMIT 5;
"

# 4. 检查磁盘空间
echo "💾 检查磁盘空间..."
docker-compose exec db df -h
```

### 故障排查工具

#### 系统诊断脚本
```bash
#!/bin/bash
# system_diagnosis.sh

echo "🔍 系统诊断报告"
echo "========================"

# 系统信息
echo "📊 系统信息:"
uname -a
uptime

# 资源使用
echo ""
echo "💾 资源使用:"
echo "CPU: $(top -bn1 | grep "Cpu(s)" | awk '{print $2}')"
echo "内存: $(free -h | grep "Mem:" | awk '{print $3" "/" $2}')"
echo "磁盘: $(df -h | grep '/$' | awk '{print $3 "/" $2}')"

# Docker状态
echo ""
echo "🐳 Docker状态:"
docker-compose ps

# 网络连接
echo ""
echo "🌐 网络连接:"
ping -c 4 8.8.8.8

# 服务健康检查
echo ""
echo "🏥 服务健康检查:"
curl -f http://localhost/health 2>/dev/null && echo "✅ 应用正常" || echo "❌ 应用异常"
curl -f http://localhost:8000 2>/dev/null && echo "✅ FastAPI正常" || echo "❌ FastAPI异常"
```

## 📋 定期维护

### 维护时间表

| 频率 | 任务 | 负责人 | 时间 | 检查方法 |
|------|------|--------|------|----------|
| 每日 | 系统检查 | DevOps | 9:00 AM | 自动脚本 |
| 每日 | 备份验证 | DevOps | 9:30 AM | 自动脚本 |
| 每周 | 系统更新 | DevOps | 周一 10:00 AM | 手动 |
| 每周 | Docker清理 | DevOps | 周一 10:30 AM | 自动脚本 |
| 每月 | 安全更新 | Security | 每月1日 10:00 AM | 手动 |
| 每月 | 性能报告 | DevOps | 每月1日 14:00 PM | 自动脚本 |
| 每季 | 容量规划 | 全体 | 每季第一周 | 会议 |
| 每年 | 架构评审 | 全体 | 每年1月 | 会议 |

### 自动化维护脚本

```bash
# maintenance_automation.sh
#!/bin/bash

# 每日维护
run_daily_maintenance() {
    /opt/football-prediction/scripts/daily_check.sh
    /opt/football-prediction/scripts/backup_verification.sh
    /opt/football-prediction/scripts/log_rotation.sh
}

# 每周维护
run_weekly_maintenance() {
    /opt/football-prediction/scripts/weekly_maintenance.sh
    /opt/football-prediction/scripts/security_scan.sh
    /opt/football-prediction/scripts/performance_analysis.sh
}

# 每月维护
run_monthly_maintenance() {
    /opt/footprediction/scripts/monthly_maintenance.sh
    /opt/footprediction/scripts/security_audit.sh
    /opt/footprediction/scripts/capacity_planning.sh
}

# 主函数
case "$1" in
    daily)
        run_daily_maintenance
        ;;
    weekly)
        run_weekly_maintenance
        ;;
    monthly)
        run_monthly_maintenance
        ;;
    *)
        echo "用法: $0 {daily|weekly|monthly}"
        exit 1
        ;;
esac
```

---

*此手册应该定期审查和更新，以反映系统架构和运维流程的变化。*

## 📞 联系信息

- **DevOps团队**: devops@company.com
- **技术支持**: support@company.com
- **紧急联系**: emergency@company.com

---

*最后更新: 2025-10-31*
