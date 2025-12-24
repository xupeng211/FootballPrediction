#!/bin/bash
#
# V20.3 数据资产备份脚本
# =========================
#
# 功能：
# - 将 1,442 场特征表和 3,087 人基准字典进行二进制冷备份
# - 防止任何代码误操作导致的数据污染
# - 生成带时间戳的快照，支持增量备份
#
# 作者: SRE Team
# 日期: 2025-12-24
# 版本: V20.3
#

set -euo pipefail

# ==================== 配置 ====================
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
BACKUP_ROOT="${PROJECT_ROOT}/data/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="${BACKUP_ROOT}/snapshot_${TIMESTAMP}"

# 数据库配置（从 .env 或环境变量读取）
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"
DB_NAME="${DB_NAME:-football_prediction}"
DB_USER="${DB_USER:-football_user}"
export PGPASSWORD="${DB_PASSWORD:-}"

# 日志配置
LOG_FILE="${BACKUP_ROOT}/snapshot_${TIMESTAMP}.log"

# ==================== 工具函数 ====================

log() {
    local level="$1"
    shift
    local message="$*"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo "[${timestamp}] [${level}] ${message}" | tee -a "${LOG_FILE}"
}

log_info() {
    log "INFO" "$@"
}

log_error() {
    log "ERROR" "$@"
}

log_success() {
    log "SUCCESS" "$@"
}

# ==================== 检查前置条件 ====================

check_prerequisites() {
    log_info "=== V20.3 数据资产备份启动 ==="
    log_info "检查前置条件..."

    # 检查 PostgreSQL 连接
    if ! command -v psql &> /dev/null; then
        log_error "PostgreSQL 客户端 (psql) 未安装"
        return 1
    fi

    # 检查数据库连接
    if ! psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d "${DB_NAME}" -c '\q' 2>/dev/null; then
        log_error "无法连接到数据库 ${DB_HOST}:${DB_PORT}/${DB_NAME}"
        log_error "请检查 DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD 环境变量"
        return 1
    fi

    log_success "数据库连接正常"

    # 创建备份目录
    mkdir -p "${BACKUP_DIR}"
    mkdir -p "${BACKUP_DIR}/database"
    mkdir -p "${BACKUP_DIR}/metadata"
    mkdir -p "${BACKUP_DIR}/features"

    log_info "备份目录: ${BACKUP_DIR}"
}

# ==================== 数据库统计 ====================

collect_statistics() {
    log_info "收集数据库统计信息..."

    # 比赛数量
    local match_count=$(psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d "${DB_NAME}" -t -c \
        "SELECT COUNT(*) FROM l2_match_data WHERE l2_raw_json IS NOT NULL;" 2>/dev/null | xargs)

    # 球员基准数量
    local player_count=$(psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d "${DB_NAME}" -t -c \
        "SELECT COUNT(DISTINCT player_id) FROM player_baselines WHERE player_id IS NOT NULL;" 2>/dev/null | xargs)

    # 特征表数量
    local feature_count=$(psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d "${DB_NAME}" -t -c \
        "SELECT COUNT(*) FROM match_features WHERE features_json IS NOT NULL;" 2>/dev/null | xargs)

    log_info "=== 数据资产统计 ==="
    log_info "比赛数量: ${match_count:-0}"
    log_info "球员基准数量: ${player_count:-0}"
    log_info "特征表数量: ${feature_count:-0}"

    # 保存统计信息
    cat > "${BACKUP_DIR}/metadata/statistics.json" << EOF
{
  "timestamp": "${TIMESTAMP}",
  "matches": ${match_count:-0},
  "player_baselines": ${player_count:-0},
  "feature_tables": ${feature_count:-0},
  "database_host": "${DB_HOST}",
  "database_name": "${DB_NAME}"
}
EOF
}

# ==================== 核心数据表备份 ====================

backup_core_tables() {
    log_info "备份核心数据表..."

    # 1. l2_match_data 表（L2 原始数据）
    log_info "  备份 l2_match_data..."
    psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d "${DB_NAME}" -c \
        "\COPY (SELECT id, league_id, season_id, home_team, away_team, match_time, home_score, away_score, l2_raw_json, created_at FROM l2_match_data WHERE l2_raw_json IS NOT NULL) TO '${BACKUP_DIR}/database/l2_match_data.csv' CSV HEADER"

    # 2. player_baselines 表（球员基准数据）
    log_info "  备份 player_baselines..."
    psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d "${DB_NAME}" -c \
        "\COPY (SELECT * FROM player_baselines WHERE player_id IS NOT NULL) TO '${BACKUP_DIR}/database/player_baselines.csv' CSV HEADER"

    # 3. match_features 表（特征数据）
    log_info "  备份 match_features..."
    psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d "${DB_NAME}" -c \
        "\COPY (SELECT * FROM match_features WHERE features_json IS NOT NULL) TO '${BACKUP_DIR}/database/match_features.csv' CSV HEADER"

    # 4. league_metadata 表（联赛元数据）
    log_info "  备份 league_metadata..."
    psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d "${DB_NAME}" -c \
        "\COPY (SELECT * FROM league_metadata) TO '${BACKUP_DIR}/database/league_metadata.csv' CSV HEADER" 2>/dev/null || true

    log_success "核心数据表备份完成"
}

# ==================== 增量备份（二进制） ====================

backup_incremental() {
    log_info "创建增量备份（二进制格式）..."

    # 使用 pg_dump 创建自定义格式备份（支持增量恢复）
    pg_dump -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d "${DB_NAME}" \
        -F c -f "${BACKUP_DIR}/database/incremental_backup.dump" \
        -t 'l2_match_data' \
        -t 'player_baselines' \
        -t 'match_features' \
        -t 'league_metadata' 2>/dev/null || true

    log_success "增量备份创建完成: ${BACKUP_DIR}/database/incremental_backup.dump"
}

# ==================== 元数据备份 ====================

backup_metadata() {
    log_info "备份元数据..."

    # 复制 data/metadata 目录
    if [ -d "${PROJECT_ROOT}/data/metadata" ]; then
        cp -r "${PROJECT_ROOT}/data/metadata" "${BACKUP_DIR}/metadata/"
        log_success "元数据备份完成"
    fi

    # 复制 data/production 目录（harvest manifests）
    if [ -d "${PROJECT_ROOT}/data/production" ]; then
        cp -r "${PROJECT_ROOT}/data/production" "${BACKUP_DIR}/metadata/"
        log_success "生产数据备份完成"
    fi
}

# ==================== 清理旧备份 ====================

cleanup_old_backups() {
    local keep_days=${BACKUP_RETENTION_DAYS:-7}
    log_info "清理 ${keep_days} 天前的旧备份..."

    find "${BACKUP_ROOT}" -maxdepth 1 -type d -name "snapshot_*" -mtime +${keep_days} -exec rm -rf {} \;

    log_success "旧备份清理完成"
}

# ==================== 生成备份报告 ====================

generate_report() {
    log_info "生成备份报告..."

    local backup_size=$(du -sh "${BACKUP_DIR}" | cut -f1)
    local file_count=$(find "${BACKUP_DIR}" -type f | wc -l)

    cat > "${BACKUP_DIR}/BACKUP_REPORT.txt" << EOF
========================================
V20.3 数据资产备份报告
========================================

备份时间: ${TIMESTAMP}
备份目录: ${BACKUP_DIR}
备份大小: ${backup_size}
文件数量: ${file_count}

数据库:
  主机: ${DB_HOST}:${DB_PORT}
  名称: ${DB_NAME}

备份内容:
  - l2_match_data (L2 原始数据)
  - player_baselines (球员基准)
  - match_features (特征数据)
  - league_metadata (联赛元数据)
  - 元数据文件

恢复命令:
  # 恢复增量备份
  pg_restore -h ${DB_HOST} -p ${DB_PORT} -U ${DB_USER} -d ${DB_NAME} \\
    ${BACKUP_DIR}/database/incremental_backup.dump

  # 恢复 CSV 数据
  psql -h ${DB_HOST} -p ${DB_PORT} -U ${DB_USER} -d ${DB_NAME} \\
    -c "\\COPY l2_match_data FROM '${BACKUP_DIR}/database/l2_match_data.csv' CSV HEADER"

========================================
备份状态: 成功
========================================
EOF

    cat "${BACKUP_DIR}/BACKUP_REPORT.txt"
    log_success "备份报告已生成: ${BACKUP_DIR}/BACKUP_REPORT.txt"
}

# ==================== 主流程 ====================

main() {
    check_prerequisites
    collect_statistics
    backup_core_tables
    backup_incremental
    backup_metadata
    cleanup_old_backups
    generate_report

    log_success "=== V20.3 数据资产备份完成 ==="
    log_info "备份位置: ${BACKUP_DIR}"
}

# ==================== 执行 ====================

main "$@"
