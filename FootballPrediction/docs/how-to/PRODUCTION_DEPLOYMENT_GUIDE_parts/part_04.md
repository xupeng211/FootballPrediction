1. 容器回滚

#### ✅ 检查清单：容器回滚准备

- [ ] **镜像备份**: 确保有可用的回滚镜像
- [ ] **版本记录**: 记录当前部署版本信息
- [ ] **回滚脚本**: 回滚脚本准备就绪
- [ ] **数据备份**: 数据库和缓存已备份
- [ ] **回滚验证**: 回滚验证步骤明确

#### 🐳 使用上一版本镜像快速回退

```bash#
#=============================================================================
=============================================================================#
#1. 回滚准备
1. 回滚准备#
#=============================================================================

=============================================================================
#
#记录当前版本信息
echo "=== Current Deployment Information ===" > rollback_log.txt
echo "Timestamp: $(date)" >> rollback_log.txt
echo "Current Git SHA: $(git rev-parse HEAD)" >> rollback_log.txt
echo "Current Docker Images:" >> rollback_log.txt
docker-compose images >> rollback_log.txt

记录当前版本信息
echo "=== Current Deployment Information ===" > rollback_log.txt
echo "Timestamp: $(date)" >> rollback_log.txt
echo "Current Git SHA: $(git rev-parse HEAD)" >> rollback_log.txt
echo "Current Docker Images:" >> rollback_log.txt
docker-compose images >> rollback_log.txt
#
#保存当前配置
cp docker-compose.yml docker-compose.yml.current
cp .env.production .env.production.backup

保存当前配置
cp docker-compose.yml docker-compose.yml.current
cp .env.production .env.production.backup
#
#获取上一个可用的Git SHA
PREVIOUS_SHA=$(git rev-parse HEAD^)
echo "Previous SHA: $PREVIOUS_SHA" >> rollback_log.txt

获取上一个可用的Git SHA
PREVIOUS_SHA=$(git rev-parse HEAD^)
echo "Previous SHA: $PREVIOUS_SHA" >> rollback_log.txt
#
#=============================================================================
=============================================================================#
#2. Docker Compose 回滚
2. Docker Compose 回滚#
#=============================================================================

=============================================================================
#
#方法1: 使用Makefile回滚
make rollback TAG=$PREVIOUS_SHA

方法1: 使用Makefile回滚
make rollback TAG=$PREVIOUS_SHA
#
#方法2: 手动回滚步骤
echo "=== Starting Docker Compose Rollback ===" >> rollback_log.txt

方法2: 手动回滚步骤
echo "=== Starting Docker Compose Rollback ===" >> rollback_log.txt
#
#停止当前服务
docker-compose down

停止当前服务
docker-compose down
#
#拉取上一个版本的镜像
docker pull football-predict:phase6-$PREVIOUS_SHA

拉取上一个版本的镜像
docker pull football-predict:phase6-$PREVIOUS_SHA
#
#修改docker-compose.yml使用上一个版本
sed -i "s/football-predict:phase6-.*/football-predict:phase6-$PREVIOUS_SHA/g" docker-compose.yml

修改docker-compose.yml使用上一个版本
sed -i "s/football-predict:phase6-.*/football-predict:phase6-$PREVIOUS_SHA/g" docker-compose.yml
#
#重新启动服务
docker-compose up -d

重新启动服务
docker-compose up -d
#
#等待服务启动
sleep 30

等待服务启动
sleep 30
#
#验证服务状态
docker-compose ps >> rollback_log.txt

验证服务状态
docker-compose ps >> rollback_log.txt
#
#=============================================================================
=============================================================================#
#3. 验证回滚成功
3. 验证回滚成功#
#=============================================================================

echo "=== Verifying Rollback ===" >> rollback_log.txt

=============================================================================

echo "=== Verifying Rollback ===" >> rollback_log.txt
#
#检查服务健康状态
curl -f http://localhost:8000/health >> rollback_log.txt 2>&1

检查服务健康状态
curl -f http://localhost:8000/health >> rollback_log.txt 2>&1
#
#检查API版本信息
curl -s http://localhost:8000/ | jq -r '.version' >> rollback_log.txt 2>&1

检查API版本信息
curl -s http://localhost:8000/ | jq -r '.version' >> rollback_log.txt 2>&1
#
#验证数据库连接
docker exec football_prediction_db pg_isready -U football_user >> rollback_log.txt 2>&1

验证数据库连接
docker exec football_prediction_db pg_isready -U football_user >> rollback_log.txt 2>&1
#
#运行基本功能测试
python -c "
import asyncio
import sys
sys.path.append('/home/user/projects/FootballPrediction')
from src.database.connection import get_async_session

async def test_connection():
    try:
        async with get_async_session() as session:
            result = await session.execute('SELECT 1')
            print('✅ Database connection successful')
            return True
    except Exception as e:
        print(f'❌ Database connection failed: {e}')
        return False

asyncio.run(test_connection())
" >> rollback_log.txt 2>&1

echo "Rollback completed at $(date)" >> rollback_log.txt
echo "Rollback log saved to rollback_log.txt"
```

#### ☸️ Kubernetes 回滚

```bash
运行基本功能测试
python -c "
import asyncio
import sys
sys.path.append('/home/user/projects/FootballPrediction')
from src.database.connection import get_async_session

async def test_connection():
    try:
        async with get_async_session() as session:
            result = await session.execute('SELECT 1')
            print('✅ Database connection successful')
            return True
    except Exception as e:
        print(f'❌ Database connection failed: {e}')
        return False

asyncio.run(test_connection())
" >> rollback_log.txt 2>&1

echo "Rollback completed at $(date)" >> rollback_log.txt
echo "Rollback log saved to rollback_log.txt"
```

#### ☸️ Kubernetes 回滚

```bash#
#=============================================================================
=============================================================================#
#1. Kubernetes 回滚准备
1. Kubernetes 回滚准备#
#=============================================================================

=============================================================================
#
#记录当前状态
echo "=== Current Kubernetes State ===" > k8s_rollback_log.txt
echo "Timestamp: $(date)" >> k8s_rollback_log.txt
kubectl get pods -o wide >> k8s_rollback_log.txt
kubectl get deployments >> k8s_rollback_log.txt

记录当前状态
echo "=== Current Kubernetes State ===" > k8s_rollback_log.txt
echo "Timestamp: $(date)" >> k8s_rollback_log.txt
kubectl get pods -o wide >> k8s_rollback_log.txt
kubectl get deployments >> k8s_rollback_log.txt
#
#获取当前部署版本
CURRENT_REVISION=$(kubectl rollout history deployment/football-prediction | grep "REVISION" | tail -1 | awk '{print $1}')
echo "Current revision: $CURRENT_REVISION" >> k8s_rollback_log.txt

获取当前部署版本
CURRENT_REVISION=$(kubectl rollout history deployment/football-prediction | grep "REVISION" | tail -1 | awk '{print $1}')
echo "Current revision: $CURRENT_REVISION" >> k8s_rollback_log.txt
#
#=============================================================================
=============================================================================#
#2. 执行回滚
2. 执行回滚#
#=============================================================================

echo "=== Starting Kubernetes Rollback ===" >> k8s_rollback_log.txt

=============================================================================

echo "=== Starting Kubernetes Rollback ===" >> k8s_rollback_log.txt
#
#方法1: 回滚到上一个版本
kubectl rollout undo deployment/football-prediction

方法1: 回滚到上一个版本
kubectl rollout undo deployment/football-prediction
#
#方法2: 回滚到特定版本
方法2: 回滚到特定版本#
#kubectl rollout undo deployment/football-prediction --to-revision=2

kubectl rollout undo deployment/football-prediction --to-revision=2
#
#等待回滚完成
kubectl rollout status deployment/football-prediction --timeout=300s

等待回滚完成
kubectl rollout status deployment/football-prediction --timeout=300s
#
#=============================================================================
=============================================================================#
#3. 验证回滚
3. 验证回滚#
#=============================================================================

echo "=== Verifying Kubernetes Rollback ===" >> k8s_rollback_log.txt

=============================================================================

echo "=== Verifying Kubernetes Rollback ===" >> k8s_rollback_log.txt
#
#检查Pod状态
kubectl get pods -l app=football-prediction >> k8s_rollback_log.txt

检查Pod状态
kubectl get pods -l app=football-prediction >> k8s_rollback_log.txt
#
#检查新版本
NEW_REVISION=$(kubectl rollout history deployment/football-prediction | grep "REVISION" | tail -1 | awk '{print $1}')
echo "New revision: $NEW_REVISION" >> k8s_rollback_log.txt

检查新版本
NEW_REVISION=$(kubectl rollout history deployment/football-prediction | grep "REVISION" | tail -1 | awk '{print $1}')
echo "New revision: $NEW_REVISION" >> k8s_rollback_log.txt
#
#检查服务访问
SERVICE_IP=$(kubectl get service football-prediction -o jsonpath='{.status.loadBalancer.ingress[0].ip}')
if [ -z "$SERVICE_IP" ]; then
    SERVICE_IP=$(kubectl get service football-prediction -o jsonpath='{.status.clusterIP}')
fi

curl -f http://$SERVICE_IP:8000/health >> k8s_rollback_log.txt 2>&1

echo "Kubernetes rollback completed at $(date)" >> k8s_rollback_log.txt
```

检查服务访问
SERVICE_IP=$(kubectl get service football-prediction -o jsonpath='{.status.loadBalancer.ingress[0].ip}')
if [ -z "$SERVICE_IP" ]; then
    SERVICE_IP=$(kubectl get service football-prediction -o jsonpath='{.status.clusterIP}')
fi

curl -f http://$SERVICE_IP:8000/health >> k8s_rollback_log.txt 2>&1

echo "Kubernetes rollback completed at $(date)" >> k8s_rollback_log.txt
```
###
###2. 数据库回滚

#### ✅ 检查清单：数据库回滚准备

- [ ] **完整备份**: 有时间点最近的完整数据库备份
- [ **WAL归档**: WAL日志归档正常
- [ ] **回滚脚本**: 数据库回滚脚本准备就绪
- [ ] **迁移记录**: 数据库迁移版本记录完整
- [ ] **数据一致性**: 回滚后数据一致性验证方法

#### 🗄️ 从备份恢复

```bash
2. 数据库回滚

#### ✅ 检查清单：数据库回滚准备

- [ ] **完整备份**: 有时间点最近的完整数据库备份
- [ **WAL归档**: WAL日志归档正常
- [ ] **回滚脚本**: 数据库回滚脚本准备就绪
- [ ] **迁移记录**: 数据库迁移版本记录完整
- [ ] **数据一致性**: 回滚后数据一致性验证方法

#### 🗄️ 从备份恢复

```bash#
#=============================================================================
=============================================================================#
#1. 数据库备份检查
1. 数据库备份检查#
#=============================================================================

=============================================================================
#
#检查最新备份
ls -la data/db-backups/full/ | tail -5

检查最新备份
ls -la data/db-backups/full/ | tail -5
#
#检查备份完整性
docker exec football_prediction_dbBackup sh -c "
ls -la /backups/full/ | tail -5
for backup in /backups/full/*.sql; do
    echo \"Checking \$backup\"
    head -10 \"\$backup\"
done
"

检查备份完整性
docker exec football_prediction_dbBackup sh -c "
ls -la /backups/full/ | tail -5
for backup in /backups/full/*.sql; do
    echo \"Checking \$backup\"
    head -10 \"\$backup\"
done
"
#
#=============================================================================
=============================================================================#
#2. 数据库回滚步骤
2. 数据库回滚步骤#
#=============================================================================

=============================================================================
#
#创建数据库回滚脚本
cat > db_rollback.sh << 'EOF'
#!/bin/bash
set -e  # 遇到错误立即退出

echo "=== Database Rollback Started at $(date) ==="

创建数据库回滚脚本
cat > db_rollback.sh << 'EOF'
#!/bin/bash
set -e  # 遇到错误立即退出

echo "=== Database Rollback Started at $(date) ==="
#
#停止应用服务以避免写入
echo "Stopping application services..."
docker-compose stop app celery-worker celery-beat

停止应用服务以避免写入
echo "Stopping application services..."
docker-compose stop app celery-worker celery-beat
#
#等待应用完全停止
sleep 10

等待应用完全停止
sleep 10
#
#记录回滚前状态
echo "Recording pre-rollback state..."
docker exec football_prediction_db pg_dump -U football_user -d football_prediction_dev > pre_rollback_backup_$(date +%Y%m%d_%H%M%S).sql

记录回滚前状态
echo "Recording pre-rollback state..."
docker exec football_prediction_db pg_dump -U football_user -d football_prediction_dev > pre_rollback_backup_$(date +%Y%m%d_%H%M%S).sql
#
#选择回滚点
echo "Available backups:"
ls -la data/db-backups/full/ | tail -10

选择回滚点
echo "Available backups:"
ls -la data/db-backups/full/ | tail -10
#
#提示用户选择备份文件
read -p "Enter backup file to restore (e.g., football_prediction_dev_20250925_120000.sql): " BACKUP_FILE

if [ ! -f "data/db-backups/full/$BACKUP_FILE" ]; then
    echo "❌ Backup file not found: $BACKUP_FILE"
    exit 1
fi

提示用户选择备份文件
read -p "Enter backup file to restore (e.g., football_prediction_dev_20250925_120000.sql): " BACKUP_FILE

if [ ! -f "data/db-backups/full/$BACKUP_FILE" ]; then
    echo "❌ Backup file not found: $BACKUP_FILE"
    exit 1
fi
#
#执行回滚
echo "Starting database restore from $BACKUP_FILE..."

执行回滚
echo "Starting database restore from $BACKUP_FILE..."
#
#创建临时数据库
docker exec football_prediction_db psql -U postgres -c "DROP DATABASE IF EXISTS football_prediction_dev_temp;"
docker exec football_prediction_db psql -U postgres -c "CREATE DATABASE football_prediction_dev_temp WITH TEMPLATE football_prediction_dev;"

创建临时数据库
docker exec football_prediction_db psql -U postgres -c "DROP DATABASE IF EXISTS football_prediction_dev_temp;"
docker exec football_prediction_db psql -U postgres -c "CREATE DATABASE football_prediction_dev_temp WITH TEMPLATE football_prediction_dev;"
#
#恢复到临时数据库
docker exec -i football_prediction_db psql -U football_user -d football_prediction_dev_temp < data/db-backups/full/$BACKUP_FILE

恢复到临时数据库
docker exec -i football_prediction_db psql -U football_user -d football_prediction_dev_temp < data/db-backups/full/$BACKUP_FILE
#
#验证恢复的数据
echo "Verifying restored data..."
docker exec football_prediction_db psql -U football_user -d football_prediction_dev_temp -c "SELECT COUNT(*) FROM matches;"

验证恢复的数据
echo "Verifying restored data..."
docker exec football_prediction_db psql -U football_user -d football_prediction_dev_temp -c "SELECT COUNT(*) FROM matches;"
#
#如果验证成功，替换原数据库
echo "Replacing production database..."
docker exec football_prediction_db psql -U postgres -c "DROP DATABASE football_prediction_dev;"
docker exec football_prediction_db psql -U postgres -c "ALTER DATABASE football_prediction_dev_temp RENAME TO football_prediction_dev;"

如果验证成功，替换原数据库
echo "Replacing production database..."
docker exec football_prediction_db psql -U postgres -c "DROP DATABASE football_prediction_dev;"
docker exec football_prediction_db psql -U postgres -c "ALTER DATABASE football_prediction_dev_temp RENAME TO football_prediction_dev;"
#
#重新启动应用服务
echo "Restarting application services..."
docker-compose up -d app celery-worker celery-beat

重新启动应用服务
echo "Restarting application services..."
docker-compose up -d app celery-worker celery-beat
#
#等待服务启动
sleep 30

等待服务启动
sleep 30
#
#验证服务状态
echo "Verifying service health..."
curl -f http://localhost:8000/health

echo "✅ Database rollback completed successfully at $(date)"
EOF

验证服务状态
echo "Verifying service health..."
curl -f http://localhost:8000/health

echo "✅ Database rollback completed successfully at $(date)"
EOF
#
#使脚本可执行
chmod +x db_rollback.sh

使脚本可执行
chmod +x db_rollback.sh
#
#=============================================================================
=============================================================================#
#3. 执行数据库回滚
3. 执行数据库回滚#
#=============================================================================

=============================================================================
#
#注意：这是一个危险操作，请谨慎执行
注意：这是一个危险操作，请谨慎执行#
#./db_rollback.sh

./db_rollback.sh
#
#=============================================================================
=============================================================================#
#4. 使用时间点恢复 (PITR)
4. 使用时间点恢复 (PITR)#
#=============================================================================

=============================================================================
#
#如果启用了WAL归档，可以使用时间点恢复
cat > point_in_time_recovery.sh << 'EOF'
#!/bin/bash
set -e

echo "=== Point-in-Time Recovery Started ==="

如果启用了WAL归档，可以使用时间点恢复
cat > point_in_time_recovery.sh << 'EOF'
#!/bin/bash
set -e

echo "=== Point-in-Time Recovery Started ==="
#
#停止应用
docker-compose stop app celery-worker celery-beat

停止应用
docker-compose stop app celery-worker celery-beat
#
#创建恢复目录
mkdir -p recovery/$(date +%Y%m%d_%H%M%S)
cd recovery/$(date +%Y%m%d_%H%M%S)

创建恢复目录
mkdir -p recovery/$(date +%Y%m%d_%H%M%S)
cd recovery/$(date +%Y%m%d_%H%M%S)
#
#复制备份文件
cp ../../data/db-backups/full/football_prediction_dev_20250925_120000.sql .

复制备份文件
cp ../../data/db-backups/full/football_prediction_dev_20250925_120000.sql .
#
#设置恢复时间
read -p "Enter recovery time (YYYY-MM-DD HH:MM:SS): " RECOVERY_TIME

设置恢复时间
read -p "Enter recovery time (YYYY-MM-DD HH:MM:SS): " RECOVERY_TIME
#
#创建恢复配置文件
cat > recovery.conf << EOF
restore_command = 'cp /backups/wal/%f %p'
recovery_target_time = '$RECOVERY_TIME'
recovery_target_action = 'promote'
EOF

创建恢复配置文件
cat > recovery.conf << EOF
restore_command = 'cp /backups/wal/%f %p'
recovery_target_time = '$RECOVERY_TIME'
recovery_target_action = 'promote'
EOF
#
#执行恢复
echo "Starting point-in-time recovery..."
docker exec football_prediction_db sh -c "
    # 停止PostgreSQL
    pg_ctl stop -D /var/lib/postgresql/data

    # 恢复基础备份
    rm -rf /var/lib/postgresql/data/*
    initdb -D /var/lib/postgresql/data

    # 配置恢复
    cp recovery.conf /var/lib/postgresql/data/

    # 启动恢复模式
    pg_ctl start -D /var/lib/postgresql/data

    # 等待恢复完成
    while [ ! -f /var/lib/postgresql/data/recovery.done ]; do
        sleep 5
    done

    # 重启为正常模式
    pg_ctl restart -D /var/lib/postgresql/data
"

echo "✅ Point-in-time recovery completed"
EOF

chmod +x point_in_time_recovery.sh
```

#### 🔄 Alembic Downgrade 示例

```bash
执行恢复
echo "Starting point-in-time recovery..."
docker exec football_prediction_db sh -c "
    # 停止PostgreSQL
    pg_ctl stop -D /var/lib/postgresql/data

    # 恢复基础备份
    rm -rf /var/lib/postgresql/data/*
    initdb -D /var/lib/postgresql/data

    # 配置恢复
    cp recovery.conf /var/lib/postgresql/data/

    # 启动恢复模式
    pg_ctl start -D /var/lib/postgresql/data

    # 等待恢复完成
    while [ ! -f /var/lib/postgresql/data/recovery.done ]; do
        sleep 5
    done

    # 重启为正常模式
    pg_ctl restart -D /var/lib/postgresql/data
"

echo "✅ Point-in-time recovery completed"
EOF

chmod +x point_in_time_recovery.sh
```

#### 🔄 Alembic Downgrade 示例

```bash#
#=============================================================================
=============================================================================#
#1. 检查当前迁移状态
1. 检查当前迁移状态#
#=============================================================================

=============================================================================
#
#查看当前迁移版本
alembic current

查看当前迁移版本
alembic current
#
#查看迁移历史
alembic history --verbose

查看迁移历史
alembic history --verbose
#
#=============================================================================
=============================================================================#
#2. 执行回滚迁移
2. 执行回滚迁移#
#=============================================================================

=============================================================================
#
#回滚到上一个版本
alembic downgrade -1

回滚到上一个版本
alembic downgrade -1
#
#回滚到特定版本
alembic downgrade d56c8d0d5aa0  # 回滚到初始版本

回滚到特定版本
alembic downgrade d56c8d0d5aa0  # 回滚到初始版本
#
#查看回滚后的状态
alembic current

查看回滚后的状态
alembic current
#
#=============================================================================
=============================================================================#
#3. 验证回滚结果
3. 验证回滚结果#
#=============================================================================

=============================================================================
#
#检查数据库表结构
docker exec football_prediction_db psql -U football_user -d football_prediction_dev -c "
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public'
ORDER BY table_name;
"

检查数据库表结构
docker exec football_prediction_db psql -U football_user -d football_prediction_dev -c "
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public'
ORDER BY table_name;
"
#
#检查索引
docker exec football_prediction_db psql -U football_user -d football_prediction_dev -c "
SELECT indexname, tablename
FROM pg_indexes
WHERE schemaname = 'public'
ORDER BY tablename, indexname;
"

检查索引
docker exec football_prediction_db psql -U football_user -d football_prediction_dev -c "
SELECT indexname, tablename
FROM pg_indexes
WHERE schemaname = 'public'
ORDER BY tablename, indexname;
"
#
#=============================================================================
=============================================================================#
#4. 批量迁移回滚脚本
4. 批量迁移回滚脚本#
#=============================================================================

cat > migration_rollback.sh << 'EOF'
#!/bin/bash
set -e

echo "=== Migration Rollback Script ==="

=============================================================================

cat > migration_rollback.sh << 'EOF'
#!/bin/bash
set -e

echo "=== Migration Rollback Script ==="
#
#记录当前状态
echo "Current migration status:"
alembic current > migration_status_before.txt

记录当前状态
echo "Current migration status:"
alembic current > migration_status_before.txt
#
#获取目标版本（回滚3个版本）
TARGET_VERSION=$(alembic history | head -4 | tail -1 | awk '{print $1}')
echo "Target version: $TARGET_VERSION"

获取目标版本（回滚3个版本）
TARGET_VERSION=$(alembic history | head -4 | tail -1 | awk '{print $1}')
echo "Target version: $TARGET_VERSION"
#
#执行回滚
echo "Executing migration rollback..."
alembic downgrade $TARGET_VERSION

执行回滚
echo "Executing migration rollback..."
alembic downgrade $TARGET_VERSION
#
#验证回滚
echo "Verifying rollback..."
alembic current > migration_status_after.txt

验证回滚
echo "Verifying rollback..."
alembic current > migration_status_after.txt
#
#比较回滚前后状态
echo "Migration status comparison:"
echo "Before: $(cat migration_status_before.txt)"
echo "After: $(cat migration_status_after.txt)"

比较回滚前后状态
echo "Migration status comparison:"
echo "Before: $(cat migration_status_before.txt)"
echo "After: $(cat migration_status_after.txt)"
#
#数据库结构验证
echo "Database structure verification:"
docker exec football_prediction_db psql -U football_user -d football_prediction_dev -c "
SELECT COUNT(*) as table_count FROM information_schema.tables WHERE table_schema = 'public';
"

echo "✅ Migration rollback completed"
EOF

chmod +x migration_rollback.sh
```

数据库结构验证
echo "Database structure verification:"
docker exec football_prediction_db psql -U football_user -d football_prediction_dev -c "
SELECT COUNT(*) as table_count FROM information_schema.tables WHERE table_schema = 'public';
"

echo "✅ Migration rollback completed"
EOF

chmod +x migration_rollback.sh
```
###
###3. 配置回滚

#### ✅ 检查清单：配置回滚准备

- [ ] **配置备份**: 当前环境配置文件已备份
- [ ] **版本控制**: 配置文件在版本控制中
- [ ] **回滚脚本**: 配置回滚脚本准备就绪
- [ ] **环境变量**: 环境变量回滚方案明确
- [ ] **配置验证**: 配置回滚后的验证方法

#### 🔄 环境变量恢复流程

```bash
3. 配置回滚

#### ✅ 检查清单：配置回滚准备

- [ ] **配置备份**: 当前环境配置文件已备份
- [ ] **版本控制**: 配置文件在版本控制中
- [ ] **回滚脚本**: 配置回滚脚本准备就绪
- [ ] **环境变量**: 环境变量回滚方案明确
- [ ] **配置验证**: 配置回滚后的验证方法

#### 🔄 环境变量恢复流程

```bash#
#=============================================================================
=============================================================================#
#1. 配置文件备份
1. 配置文件备份#
#=============================================================================

=============================================================================
#
#创建配置备份目录
mkdir -p config_backup/$(date +%Y%m%d_%H%M%S)

创建配置备份目录
mkdir -p config_backup/$(date +%Y%m%d_%H%M%S)
#
#备份当前配置
cp .env.production config_backup/$(date +%Y%m%d_%H%M%S)/
cp docker-compose.yml config_backup/$(date +%Y%m%d_%H%M%S)/
cp configs/* config_backup/$(date +%Y%m%d_%H%M%S)/

echo "Configuration backed up to config_backup/$(date +%Y%m%d_%H%M%S)/"

备份当前配置
cp .env.production config_backup/$(date +%Y%m%d_%H%M%S)/
cp docker-compose.yml config_backup/$(date +%Y%m%d_%H%M%S)/
cp configs/* config_backup/$(date +%Y%m%d_%H%M%S)/

echo "Configuration backed up to config_backup/$(date +%Y%m%d_%H%M%S)/"
#
#=============================================================================
=============================================================================#
#2. 配置回滚脚本
2. 配置回滚脚本#
#=============================================================================

cat > config_rollback.sh << 'EOF'
#!/bin/bash
set -e

echo "=== Configuration Rollback Script ==="

=============================================================================

cat > config_rollback.sh << 'EOF'
#!/bin/bash
set -e

echo "=== Configuration Rollback Script ==="
#
#记录当前配置
echo "Current configuration backup:"
ls -la config_backup/ | tail -5

记录当前配置
echo "Current configuration backup:"
ls -la config_backup/ | tail -5
#
#选择回滚点
read -p "Enter backup timestamp to restore (e.g., 20250925_120000): " BACKUP_TIMESTAMP

BACKUP_DIR="config_backup/$BACKUP_TIMESTAMP"

if [ ! -d "$BACKUP_DIR" ]; then
    echo "❌ Backup directory not found: $BACKUP_DIR"
    exit 1
fi

选择回滚点
read -p "Enter backup timestamp to restore (e.g., 20250925_120000): " BACKUP_TIMESTAMP

BACKUP_DIR="config_backup/$BACKUP_TIMESTAMP"

if [ ! -d "$BACKUP_DIR" ]; then
    echo "❌ Backup directory not found: $BACKUP_DIR"
    exit 1
fi
#
#验证备份文件
echo "Verifying backup files..."
for file in .env.production docker-compose.yml; do
    if [ ! -f "$BACKUP_DIR/$file" ]; then
        echo "❌ Missing backup file: $file"
        exit 1
    fi
done

验证备份文件
echo "Verifying backup files..."
for file in .env.production docker-compose.yml; do
    if [ ! -f "$BACKUP_DIR/$file" ]; then
        echo "❌ Missing backup file: $file"
        exit 1
    fi
done
#
#停止服务
echo "Stopping services..."
docker-compose down

停止服务
echo "Stopping services..."
docker-compose down
#
#恢复配置文件
echo "Restoring configuration files..."
cp "$BACKUP_DIR/.env.production" .env.production
cp "$BACKUP_DIR/docker-compose.yml" docker-compose.yml

if [ -d "$BACKUP_DIR/configs" ]; then
    cp -r "$BACKUP_DIR/configs/"* configs/
fi

恢复配置文件
echo "Restoring configuration files..."
cp "$BACKUP_DIR/.env.production" .env.production
cp "$BACKUP_DIR/docker-compose.yml" docker-compose.yml

if [ -d "$BACKUP_DIR/configs" ]; then
    cp -r "$BACKUP_DIR/configs/"* configs/
fi
#
#验证恢复的配置
echo "Verifying restored configuration..."
echo "Environment file:"
grep -E "ENVIRONMENT|DB_PASSWORD|REDIS_PASSWORD" .env.production

echo "Docker Compose configuration:"
grep -E "image.*football-predict" docker-compose.yml

验证恢复的配置
echo "Verifying restored configuration..."
echo "Environment file:"
grep -E "ENVIRONMENT|DB_PASSWORD|REDIS_PASSWORD" .env.production

echo "Docker Compose configuration:"
grep -E "image.*football-predict" docker-compose.yml
#
#重新启动服务
echo "Restarting services with restored configuration..."
docker-compose up -d

重新启动服务
echo "Restarting services with restored configuration..."
docker-compose up -d
#
#等待服务启动
sleep 30

等待服务启动
sleep 30
#
#验证服务状态
echo "Verifying service health..."
curl -f http://localhost:8000/health

echo "✅ Configuration rollback completed successfully"
EOF

chmod +x config_rollback.sh

验证服务状态
echo "Verifying service health..."
curl -f http://localhost:8000/health

echo "✅ Configuration rollback completed successfully"
EOF

chmod +x config_rollback.sh
#
#=============================================================================
=============================================================================#
#3. 部分配置回滚
3. 部分配置回滚#
