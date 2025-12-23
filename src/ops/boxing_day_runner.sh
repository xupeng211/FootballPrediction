#!/bin/bash
################################################################################
# Boxing Day 自动化执行脚本 (V19.4.1 Production)
# =====================================================
# 用途: 12月26日 Boxing Day 比赛日的全自动运维流程
#
# 时间线:
#   08:00 AM - L1/L2 数据采集收割
#   10:30 AM - 启动市场巡检 (开赛前2小时)
#   12:30 PM - 比赛开哨时刻 (实时监控中)
#
# 作者: V19.4.1 SRE Team
# 日期: 2025-12-26
# 版本: 1.0.0
################################################################################

set -euo pipefail  # 严格模式: 遇到错误立即退出

# ============================================
# 配置区域
# ============================================

# 项目根目录
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$PROJECT_ROOT"

# 日志目录
LOG_DIR="$PROJECT_ROOT/logs/boxing_day"
mkdir -p "$LOG_DIR"

# 日志文件
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
MAIN_LOG="$LOG_DIR/boxing_day_$TIMESTAMP.log"
DATA_LOG="$LOG_DIR/data_collection_$TIMESTAMP.log"
MONITOR_LOG="$LOG_DIR/market_monitor_$TIMESTAMP.log"
ALERT_LOG="$LOG_DIR/alerts_$TIMESTAMP.log"

# 比赛配置
TARGET_MATCH_ID="4813551"
MATCH_TIME="2025-12-26 12:30"
LEAGUE="EPL"
SEASON="2324"

# 阈值配置
DELTA_THRESHOLD=5.0  # 5% 偏差阈值
MIN_BALANCE=1000.0   # 最小初始资金

# ============================================
# 工具函数
# ============================================

log() {
    local level=$1
    shift
    local message="$@"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo "[$timestamp] [$level] $message" | tee -a "$MAIN_LOG"
}

log_header() {
    local title="$1"
    local width=70
    echo "" | tee -a "$MAIN_LOG"
    echo "=$(printf '%.0s' $(seq 1 $width))=" | tee -a "$MAIN_LOG"
    echo "  $title" | tee -a "$MAIN_LOG"
    echo "=$(printf '%.0s' $(seq 1 $width))=" | tee -a "$MAIN_LOG"
    echo "" | tee -a "$MAIN_LOG"
}

alert() {
    local message="$1"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo "[$timestamp] [ALERT] $message" | tee -a "$ALERT_LOG"
    # 简单的可视化告警
    echo "  >>>>>>>>>> <<<<<<<<<<" | tee -a "$ALERT_LOG"
    echo "  >>> $message <<<" | tee -a "$ALERT_LOG"
    echo "  >>>>>>>>>> <<<<<<<<<<" | tee -a "$ALERT_LOG"
}

check_python() {
    if ! command -v python &> /dev/null; then
        log "ERROR" "Python 未安装或不在 PATH 中"
        exit 1
    fi
    log "INFO" "Python 版本: $(python --version)"
}

check_docker() {
    if ! command -v docker &> /dev/null; then
        log "WARNING" "Docker 未安装，跳过容器检查"
        return 1
    fi

    # 检查容器状态
    if docker-compose ps | grep -q "Up"; then
        log "INFO" "Docker 服务正在运行"
        docker-compose ps | tee -a "$MAIN_LOG"
        return 0
    else
        log "WARNING" "Docker 服务未运行"
        return 1
    fi
}

wait_for_db() {
    local max_attempts=30
    local attempt=1

    log "INFO" "等待数据库就绪..."

    while [ $attempt -le $max_attempts ]; do
        if docker-compose exec -T db pg_isready -U football_user &> /dev/null; then
            log "INFO" "数据库已就绪"
            return 0
        fi
        log "DEBUG" "尝试 $attempt/$max_attempts: 数据库未就绪，等待中..."
        sleep 2
        ((attempt++))
    done

    log "ERROR" "数据库在 ${max_attempts} 次尝试后仍未就绪"
    return 1
}

# ============================================
# Phase 1: 系统健康检查 (08:00 AM)
# ============================================

phase1_health_check() {
    log_header "Phase 1: 系统健康检查"

    # 1. Python 环境
    check_python

    # 2. 虚拟环境
    if [ -d "venv" ]; then
        log "INFO" "激活虚拟环境: venv"
        source venv/bin/activate
    else
        log "WARNING" "虚拟环境不存在，使用系统 Python"
    fi

    # 3. 依赖检查
    log "INFO" "检查关键依赖..."
    python -c "import xgboost, pandas, numpy, psycopg2, redis" 2>> "$MAIN_LOG" || {
        log "ERROR" "关键依赖缺失，请运行 make install"
        exit 1
    }
    log "INFO" "所有依赖正常"

    # 4. 配置检查
    log "INFO" "检查配置文件..."
    if [ ! -f ".env" ]; then
        log "ERROR" ".env 文件不存在"
        exit 1
    fi

    # 5. 模型检查
    log "INFO" "检查生产模型..."
    if [ ! -f "src/production_models/v19.4_draw_sensitivity_model.pkl" ]; then
        log "ERROR" "V19.4.1 生产模型不存在"
        exit 1
    fi
    log "INFO" "V19.4.1 生产模型已就绪"

    # 6. Docker 服务检查
    check_docker && wait_for_db

    log "INFO" "✅ 系统健康检查完成"
}

# ============================================
# Phase 2: L1/L2 数据采集 (08:00 AM)
# ============================================

phase2_data_collection() {
    log_header "Phase 2: L1/L2 数据采集"

    log "INFO" "目标联赛: $LEAGUE"
    log "INFO" "目标赛季: $SEASON"

    # 执行数据采集
    log "INFO" "开始数据采集..."
    python main_production.py l1-harvest \
        --season "$SEASON" \
        --league "$LEAGUE" \
        --target 10 \
        >> "$DATA_LOG" 2>&1 || {
        log "WARNING" "数据采集遇到问题，检查日志: $DATA_LOG"
    }

    # 执行 L2 特征解析
    log "INFO" "开始 L2 特征解析..."
    python main_production.py l2-parse \
        >> "$DATA_LOG" 2>&1 || {
        log "WARNING" "L2 解析遇到问题，检查日志: $DATA_LOG"
    }

    # 统计数据
    log "INFO" "数据采集完成，统计结果:"
    docker-compose exec -T db psql -U football_user -d football_db -c "
        SELECT
            league_id,
            season,
            COUNT(*) as total_matches,
            COUNT(CASE WHEN l2_features IS NOT NULL THEN 1 END) as with_l2_features,
            MIN(match_time) as earliest,
            MAX(match_time) as latest
        FROM matches
        WHERE league_id = 47 AND season = '$SEASON'
        GROUP BY league_id, season;
    " | tee -a "$MAIN_LOG"

    log "INFO" "✅ L1/L2 数据采集完成"
}

# ============================================
# Phase 3: 市场巡检 (10:30 AM - 12:30 PM)
# ============================================

phase3_market_monitor() {
    log_header "Phase 3: 市场实时巡检"

    log "INFO" "目标比赛 ID: $TARGET_MATCH_ID"
    log "INFO" "比赛时间: $MATCH_TIME"
    log "INFO" "巡检窗口: 开场前 90 分钟"
    log "INFO" "轮询间隔: 5 分钟"
    log "INFO" "偏差阈值: ${DELTA_THRESHOLD}%"

    # 检查比赛是否还存在
    log "INFO" "验证比赛数据..."
    MATCH_EXISTS=$(docker-compose exec -T db psql -U football_user -d football_db -t -c "
        SELECT COUNT(*) FROM matches WHERE external_id = '$TARGET_MATCH_ID';
    " 2>> "$MAIN_LOG" | xargs)

    if [ "$MATCH_EXISTS" -eq 0 ]; then
        log "ERROR" "比赛 $TARGET_MATCH_ID 在数据库中不存在"
        return 1
    fi
    log "INFO" "比赛数据验证通过"

    # 启动市场监控
    log "INFO" "启动市场监控..."
    log "INFO" "监控日志: $MONITOR_LOG"

    python main_production.py monitor \
        --match-id "$TARGET_MATCH_ID" \
        --match-time "$MATCH_TIME" \
        --initial-balance "$MIN_BALANCE" \
        >> "$MONITOR_LOG" 2>&1 || {
        log "WARNING" "市场监控异常退出，检查日志: $MONITOR_LOG"
    }

    log "INFO" "✅ 市场监控完成"
}

# ============================================
# Phase 4: 监控后分析 (12:30 PM+)
# ============================================

phase4_post_analysis() {
    log_header "Phase 4: 监控后分析"

    # 1. 汇总告警
    log "INFO" "告警汇总:"
    if [ -f "$ALERT_LOG" ]; then
        local alert_count=$(wc -l < "$ALERT_LOG")
        log "INFO" "总告警数: $alert_count"
        if [ $alert_count -gt 0 ]; then
            echo "=== 最近告警 ===" | tee -a "$MAIN_LOG"
            tail -20 "$ALERT_LOG" | tee -a "$MAIN_LOG"
        fi
    else
        log "INFO" "无告警记录"
    fi

    # 2. 风控状态
    log "INFO" "风控状态:"
    python main_production.py risk-status \
        --initial-balance "$MIN_BALANCE" \
        2>&1 | tee -a "$MAIN_LOG"

    # 3. 生成每日报告
    log "INFO" "生成每日报告..."
    python src/ops/daily_workflow.py \
        2>&1 | tee -a "$MAIN_LOG"

    log "INFO" "✅ 分析完成"
}

# ============================================
# Phase 5: 清理和归档
# ============================================

phase5_cleanup() {
    log_header "Phase 5: 清理和归档"

    # 1. 压缩日志
    log "INFO" "压缩日志文件..."
    tar -czf "$LOG_DIR/boxing_day_logs_$TIMESTAMP.tar.gz" \
        "$MAIN_LOG" "$DATA_LOG" "$MONITOR_LOG" "$ALERT_LOG" 2>/dev/null || true

    # 2. 清理旧日志（保留最近 7 天）
    log "INFO" "清理旧日志..."
    find "$LOG_DIR" -name "boxing_day_logs_*.tar.gz" -mtime +7 -delete 2>/dev/null || true

    # 3. 备份数据库
    if [ "${BACKUP_DB:-false}" = "true" ]; then
        log "INFO" "备份数据库..."
        docker-compose exec -T db pg_dump -U football_user football_db \
            > "$LOG_DIR/db_backup_$TIMESTAMP.sql" 2>/dev/null || {
            log "WARNING" "数据库备份失败"
        }
    fi

    log "INFO" "✅ 清理完成"
}

# ============================================
# 主执行流程
# ============================================

main() {
    log_header "V19.4.1 Boxing Day 自动化执行流程"
    log "INFO" "执行时间: $(date '+%Y-%m-%d %H:%M:%S')"
    log "INFO" "项目路径: $PROJECT_ROOT"
    log "INFO" "日志目录: $LOG_DIR"

    # 参数解析
    local skip_health=false
    local skip_data=false
    local skip_monitor=false
    local backup_db=false

    while [[ $# -gt 0 ]]; do
        case $1 in
            --skip-health)
                skip_health=true
                shift
                ;;
            --skip-data)
                skip_data=true
                shift
                ;;
            --skip-monitor)
                skip_monitor=true
                shift
                ;;
            --backup-db)
                backup_db=true
                export BACKUP_DB=true
                shift
                ;;
            --help)
                echo "用法: $0 [选项]"
                echo ""
                echo "选项:"
                echo "  --skip-health    跳过系统健康检查"
                echo "  --skip-data      跳过数据采集"
                echo "  --skip-monitor   跳过市场监控"
                echo "  --backup-db      执行数据库备份"
                echo "  --help           显示帮助信息"
                exit 0
                ;;
            *)
                log "ERROR" "未知选项: $1"
                exit 1
                ;;
        esac
    done

    # 执行各阶段
    [ "$skip_health" = false ] && phase1_health_check
    [ "$skip_data" = false ] && phase2_data_collection
    [ "$skip_monitor" = false ] && phase3_market_monitor
    phase4_post_analysis
    phase5_cleanup

    log_header "执行完成"
    log "INFO" "完成时间: $(date '+%Y-%m-%d %H:%M:%S')"
    log "INFO" "所有日志已保存到: $LOG_DIR"
    log "INFO" "主日志: $MAIN_LOG"

    exit 0
}

# ============================================
# 信号处理
# ============================================

trap 'log "ERROR" "脚本被中断"; exit 130' INT TERM

# ============================================
# 执行入口
# ============================================

main "$@"
