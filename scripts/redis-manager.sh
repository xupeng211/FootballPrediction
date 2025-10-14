#!/bin/bash

# Redis集群管理脚本
# Football Prediction Project

set -euo pipefail

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${GREEN}[INFO]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

log_step() {
    echo -e "${BLUE}[STEP]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

# 配置
REDIS_PASSWORD=${REDIS_PASSWORD:-redis123456}
REDIS_MASTER_HOST=${REDIS_MASTER_HOST:-localhost}
REDIS_MASTER_PORT=${REDIS_MASTER_PORT:-6379}
REDIS_SENTINEL_PORT=${REDIS_SENTINEL_PORT:-26379}

# 检查Redis连接
check_redis_connection() {
    local host=${1:-$REDIS_MASTER_HOST}
    local port=${2:-$REDIS_MASTER_PORT}

    if redis-cli -h "$host" -p "$port" -a "$REDIS_PASSWORD" ping > /dev/null 2>&1; then
        return 0
    else
        return 1
    fi
}

# 获取Redis信息
get_redis_info() {
    local host=${1:-$REDIS_MASTER_HOST}
    local port=${2:-$REDIS_MASTER_PORT}

    redis-cli -h "$host" -p "$port" -a "$REDIS_PASSWORD" info all
}

# 启动Redis集群
start_cluster() {
    log_step "启动Redis集群..."

    # 检查是否已经运行
    if docker-compose -f docker-compose.redis-cluster.yml ps | grep -q "Up"; then
        log_warn "Redis集群已经在运行"
        return 0
    fi

    # 创建必要目录
    mkdir -p logs/redis
    mkdir -p config/redis

    # 创建Sentinel配置
    create_sentinel_config

    # 启动集群
    docker-compose -f docker-compose.redis-cluster.yml up -d

    # 等待服务启动
    log_info "等待Redis服务启动..."
    sleep 10

    # 检查服务状态
    check_cluster_status

    log_info "Redis集群启动完成"
}

# 创建Sentinel配置
create_sentinel_config() {
    cat > config/redis/sentinel.conf <<EOF
# Redis Sentinel配置
port 26379
bind 0.0.0.0
sentinel monitor mymaster redis-master 6379 2
sentinel auth-pass mymaster $REDIS_PASSWORD
sentinel down-after-milliseconds mymaster 5000
sentinel parallel-syncs mymaster 1
sentinel failover-timeout mymaster 10000
sentinel deny-scripts-reconfig yes
sentinel announce-ip redis-sentinel
sentinel announce-port 26379
EOF
}

# 检查集群状态
check_cluster_status() {
    log_step "检查Redis集群状态..."

    # 检查主节点
    if check_redis_connection redis-master 6379; then
        log_info "✓ 主节点运行正常"
    else
        log_error "✗ 主节点连接失败"
    fi

    # 检查从节点
    for replica in redis-replica-1:6380 redis-replica-2:6381; do
        host=$(echo "$replica" | cut -d: -f1)
        port=$(echo "$replica" | cut -d: -f2)

        if check_redis_connection "$host" "$port"; then
            log_info "✓ 从节点 $host:$port 运行正常"
        else
            log_error "✗ 从节点 $host:$port 连接失败"
        fi
    done

    # 检查复制状态
    check_replication_status

    # 检查Sentinel状态
    check_sentinel_status
}

# 检查复制状态
check_replication_status() {
    log_step "检查复制状态..."

    # 获取主节点信息
    master_info=$(get_redis_info redis-master 6379)

    # 提取从节点信息
    echo "$master_info" | grep -E "^connected_slaves|^slave0|^slave1" | while read line; do
        log_info "复制信息: $line"
    done
}

# 检查Sentinel状态
check_sentinel_status() {
    log_step "检查Sentinel状态..."

    for sentinel in redis-sentinel-1:26379 redis-sentinel-2:26380 redis-sentinel-3:26381; do
        host=$(echo "$sentinel" | cut -d: -f1)
        port=$(echo "$sentinel" | cut -d: -f2)

        # 检查Sentinel是否运行
        if redis-cli -h "$host" -p "$port" ping > /dev/null 2>&1; then
            log_info "✓ Sentinel $host:$port 运行正常"

            # 获取Sentinel监控的主节点信息
            masters=$(redis-cli -h "$host" -p "$port" sentinel masters)
            echo "$masters" | while read -r master; do
                if [[ -n "$master" ]]; then
                    log_info "监控主节点: $master"
                fi
            done
        else
            log_error "✗ Sentinel $host:$port 连接失败"
        fi
    done
}

# 执行故障转移
failover() {
    log_step "执行手动故障转移..."

    # 通过Sentinel执行故障转移
    redis-cli -h redis-sentinel-1 -p "$REDIS_SENTINEL_PORT" sentinel failover mymaster

    log_info "故障转移命令已发送"

    # 等待故障转移完成
    sleep 5

    # 检查新的主节点
    check_new_master
}

# 检查新的主节点
check_new_master() {
    log_step "检查新的主节点..."

    master=$(redis-cli -h redis-sentinel-1 -p "$REDIS_SENTINEL_PORT" sentinel get-master-addr-by-name mymaster | head -1)

    if [[ -n "$master" ]]; then
        log_info "新的主节点是: $master"

        # 检查是否可以连接
        if check_redis_connection "$master" 6379; then
            log_info "✓ 新主节点连接正常"

            # 检查角色
            role=$(redis-cli -h "$master" -p 6379 -a "$REDIS_PASSWORD" role | head -1)
            log_info "节点角色: $role"
        else
            log_error "✗ 无法连接到新主节点"
        fi
    fi
}

# 监控Redis性能
monitor_performance() {
    log_step "监控Redis性能..."

    # 获取性能指标
    info=$(get_redis_info redis-master 6379)

    # 提取关键指标
    memory_used=$(echo "$info" | grep "^used_memory:" | cut -d: -f2 | tr -d '\r')
    memory_human=$(echo "$info" | grep "^used_memory_human:" | cut -d: -f2 | tr -d '\r')
    keyspace_hits=$(echo "$info" | grep "^keyspace_hits:" | cut -d: -f2 | tr -d '\r')
    keyspace_misses=$(echo "$info" | grep "^keyspace_misses:" | cut -d: -f2 | tr -d '\r')
    connected_clients=$(echo "$info" | grep "^connected_clients:" | cut -d: -f2 | tr -d '\r')

    # 计算命中率
    total_requests=$((keyspace_hits + keyspace_misses))
    if [[ $total_requests -gt 0 ]]; then
        hit_rate=$((keyspace_hits * 100 / total_requests))
    else
        hit_rate=0
    fi

    # 显示指标
    echo ""
    echo "Redis性能指标："
    echo "=============="
    echo "内存使用: $memory_human ($memory_used bytes)"
    echo "连接客户端: $connected_clients"
    echo "缓存命中: $keyspace_hits"
    echo "缓存未命中: $keyspace_misses"
    echo "命中率: ${hit_rate}%"
    echo ""

    # 获取慢查询
    slow_log=$(redis-cli -h redis-master -p 6379 -a "$REDIS_PASSWORD" slowlog get 10)
    if [[ -n "$slow_log" ]]; then
        echo "慢查询日志（最近10条）："
        echo "$slow_log" | while read -r entry; do
            if [[ -n "$entry" ]]; then
                log_info "慢查询: $entry"
            fi
        done
    fi
}

# 备份Redis数据
backup_redis() {
    log_step "备份Redis数据..."

    backup_dir="backups/redis"
    mkdir -p "$backup_dir"

    # 创建备份文件名
    timestamp=$(date +%Y%m%d_%H%M%S)
    backup_file="$backup_dir/redis_backup_$timestamp.rdb"

    # 执行备份
    docker exec football-redis-master redis-cli --rdb /tmp/dump_$timestamp.rdb

    # 复制备份文件
    docker cp football-redis-master:/tmp/dump_$timestamp.rdb "$backup_file"

    # 压缩备份
    gzip "$backup_file"

    log_info "Redis备份完成: ${backup_file}.gz"

    # 清理旧备份（保留7天）
    find "$backup_dir" -name "*.gz" -mtime +7 -delete

    # 上传到S3（如果配置了）
    if [[ -n "${BACKUP_S3_BUCKET:-}" ]]; then
        aws s3 cp "${backup_file}.gz" "s3://$BACKUP_S3_BUCKET/redis-backups/"
        log_info "备份已上传到S3"
    fi
}

# 恢复Redis数据
restore_redis() {
    local backup_file=${1:-}

    if [[ -z "$backup_file" ]]; then
        log_error "请指定备份文件"
        echo "用法: $0 restore <backup_file>"
        return 1
    fi

    if [[ ! -f "$backup_file" ]]; then
        log_error "备份文件不存在: $backup_file"
        return 1
    fi

    log_step "恢复Redis数据..."

    # 停止Redis服务
    docker-compose -f docker-compose.redis-cluster.yml stop redis-master

    # 解压备份文件（如果是压缩的）
    if [[ "$backup_file" == *.gz ]]; then
        gunzip -c "$backup_file" > /tmp/redis_restore.rdb
    else
        cp "$backup_file" /tmp/redis_restore.rdb
    fi

    # 复制到容器
    docker cp /tmp/redis_restore.rdb football-redis-master:/data/dump.rdb

    # 启动Redis服务
    docker-compose -f docker-compose.redis-cluster.yml start redis-master

    # 清理临时文件
    rm -f /tmp/redis_restore.rdb

    log_info "Redis数据恢复完成"
}

# 清理Redis数据
cleanup_redis() {
    log_step "清理Redis数据..."

    echo "警告: 此操作将删除所有Redis数据!"
    read -p "确认继续? (y/N): " -n 1 -r
    echo

    if [[ $REPLY =~ ^[Yy]$ ]]; then
        # 清空所有数据库
        redis-cli -h redis-master -p 6379 -a "$REDIS_PASSWORD" flushall

        # 清空从节点
        redis-cli -h redis-replica-1 -p 6380 -a "$REDIS_PASSWORD" flushall
        redis-cli -h redis-replica-2 -p 6381 -a "$REDIS_PASSWORD" flushall

        log_info "Redis数据已清理"
    else
        log_info "操作已取消"
    fi
}

# 重置集群
reset_cluster() {
    log_step "重置Redis集群..."

    # 停止所有服务
    docker-compose -f docker-compose.redis-cluster.yml down -v

    # 清理数据目录
    sudo rm -rf docker/volumes/redis_*

    # 重新启动
    start_cluster

    log_info "Redis集群已重置"
}

# 性能测试
benchmark() {
    log_step "执行Redis性能测试..."

    # 启动benchmark容器
    docker-compose -f docker-compose.redis-cluster.yml --profile benchmark up --build

    log_info "性能测试完成"
}

# 显示日志
show_logs() {
    local service=${1:-redis-master}

    docker-compose -f docker-compose.redis-cluster.yml logs -f "$service"
}

# 显示帮助
show_help() {
    echo "Redis集群管理工具"
    echo ""
    echo "用法: $0 <命令> [参数]"
    echo ""
    echo "命令:"
    echo "  start        启动Redis集群"
    echo "  stop         停止Redis集群"
    echo "  restart      重启Redis集群"
    echo "  status       检查集群状态"
    echo "  failover     执行故障转移"
    echo "  monitor      监控性能"
    echo "  backup       备份数据"
    echo "  restore      恢复数据"
    echo "  cleanup      清理数据"
    echo "  reset        重置集群"
    echo "  benchmark    性能测试"
    echo "  logs         显示日志"
    echo "  help         显示帮助"
    echo ""
    echo "示例:"
    echo "  $0 start                 # 启动集群"
    echo "  $0 status                # 查看状态"
    echo "  $0 restore backup.rdb    # 恢复备份"
    echo ""
}

# 主函数
main() {
    case "${1:-help}" in
        start)
            start_cluster
            ;;
        stop)
            docker-compose -f docker-compose.redis-cluster.yml down
            ;;
        restart)
            docker-compose -f docker-compose.redis-cluster.yml restart
            ;;
        status)
            check_cluster_status
            ;;
        failover)
            failover
            ;;
        monitor)
            monitor_performance
            ;;
        backup)
            backup_redis
            ;;
        restore)
            restore_redis "$2"
            ;;
        cleanup)
            cleanup_redis
            ;;
        reset)
            reset_cluster
            ;;
        benchmark)
            benchmark
            ;;
        logs)
            show_logs "$2"
            ;;
        help|--help|-h)
            show_help
            ;;
        *)
            log_error "未知命令: $1"
            show_help
            exit 1
            ;;
    esac
}

# 执行主函数
main "$@"
