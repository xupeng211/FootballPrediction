#!/bin/bash
# =============================================================================
# V51.1 特征库一键重建脚本
# =============================================================================
# 功能:
#   1. 清空旧特征表
#   2. 启动 8 进程并行计算全量 9,000 场特征
#   3. 自动生成《数据质量自检报告》
#
# 使用方法:
#   bash scripts/ml/rebuild_all_features.sh
#
# 预计耗时: ~25 分钟 (8 进程并行)
# =============================================================================

set -e  # 遇到错误立即退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 打印横幅
print_banner() {
    echo ""
    echo "============================================================================"
    echo "                    V51.1 特征库一键重建脚本"
    echo "============================================================================"
    echo ""
}

# 步骤 1: 环境检查
check_environment() {
    log_info "【步骤 1/4】环境检查"

    # 检查 Python 环境
    if ! command -v python &> /dev/null; then
        log_error "Python 未安装"
        exit 1
    fi

    # 检查 Docker 环境
    if ! docker-compose ps &> /dev/null; then
        log_error "Docker Compose 未运行"
        exit 1
    fi

    # 检查数据库连接
    if ! docker-compose exec -T db pg_isready -U football_user &> /dev/null; then
        log_error "数据库连接失败"
        exit 1
    fi

    log_success "环境检查通过"
    echo ""
}

# 步骤 2: 备份现有数据
backup_existing_data() {
    log_info "【步骤 2/4】备份现有数据"

    BACKUP_DIR="backups/v51_1_rebuild_$(date +%Y%m%d_%H%M%S)"
    mkdir -p "$BACKUP_DIR"

    # 检查是否有现有数据需要备份
    EXISTING_COUNT=$(docker-compose exec -T db psql -U football_user -d football_prediction_dev -t -c "
        SELECT COUNT(*) FROM prematch_features;
    " 2>/dev/null | tr -d ' ')

    if [ -n "$EXISTING_COUNT" ] && [ "$EXISTING_COUNT" -gt 0 ]; then
        log_warning "发现 $EXISTING_COUNT 条现有特征记录，开始备份..."

        # 备份到 SQL 文件
        docker-compose exec -T db pg_dump -U football_user football_prediction_dev \
            -t prematch_features > "$BACKUP_DIR/prematch_features_backup.sql" 2>/dev/null || true

        log_success "备份完成: $BACKUP_DIR/prematch_features_backup.sql"
    else
        log_info "无现有数据需要备份"
    fi

    echo ""
}

# 步骤 3: 清空旧特征表
clear_old_features() {
    log_info "【步骤 3/4】清空旧特征表"

    # 确认提示
    read -p "是否清空 prematch_features 表? (y/N): " -n 1 -r
    echo

    if [[ $REPLY =~ ^[Yy]$ ]]; then
        docker-compose exec -T db psql -U football_user -d football_prediction_dev -c "
            TRUNCATE TABLE prematch_features;
        " > /dev/null 2>&1

        log_success "旧特征表已清空"
    else
        log_warning "跳过清空，将执行增量更新"
    fi

    echo ""
}

# 步骤 4: 启动并行计算
run_feature_calculation() {
    log_info "【步骤 4/4】启动特征计算"

    # 查询总比赛数
    TOTAL_MATCHES=$(docker-compose exec -T db psql -U football_user -d football_prediction_dev -t -c "
        SELECT COUNT(*) FROM matches
        WHERE status = 'finished'
          AND home_score IS NOT NULL
          AND away_score IS NOT NULL;
    " 2>/dev/null | tr -d ' ')

    log_info "待计算比赛总数: $TOTAL_MATCHES 场"

    # 询问是否使用并行模式
    read -p "是否使用 8 进程并行模式? (推荐，约 25 分钟) [Y/n]: " -n 1 -r
    echo

    if [[ $REPLY =~ ^[Nn]$ ]]; then
        # 单进程模式
        log_warning "使用单进程模式（预计约 3 小时）"
        PYTHONPATH=. python -m scripts.ml.v51_1_rolling_feature_engine --limit "$TOTAL_MATCHES"
    else
        # 并行模式
        log_info "使用 8 进程并行模式（预计约 25 分钟）"
        PYTHONPATH=. python -m scripts.ml.v51_1_rolling_feature_engine \
            --limit "$TOTAL_MATCHES" \
            --parallel \
            --processes 8
    fi

    log_success "特征计算完成"
    echo ""
}

# 生成数据质量自检报告
generate_quality_report() {
    log_info "生成《数据质量自检报告》"

    REPORT_FILE="backups/v51_1_quality_report_$(date +%Y%m%d_%H%M%S).txt"

    {
        echo "============================================================================"
        echo "                    V51.1 数据质量自检报告"
        echo "============================================================================"
        echo "生成时间: $(date '+%Y-%m-%d %H:%M:%S')"
        echo ""

        # 1. 记录统计
        echo "【1. 记录统计】"
        docker-compose exec -T db psql -U football_user -d football_prediction_dev -c "
            SELECT
                COUNT(*) AS total_records,
                COUNT(CASE WHEN is_valid THEN 1 END) AS valid_records,
                ROUND(COUNT(CASE WHEN is_valid THEN 1 END) * 100.0 / COUNT(*), 2) AS valid_pct
            FROM prematch_features;
        "
        echo ""

        # 2. 特征覆盖度
        echo "【2. 特征覆盖度】"
        docker-compose exec -T db psql -U football_user -d football_prediction_dev -c "
            SELECT
                'home_rolling_xg' AS feature_name,
                COUNT(*) AS total,
                COUNT(home_rolling_xg) AS non_null,
                ROUND(COUNT(home_rolling_xg) * 100.0 / COUNT(*), 2) AS coverage_pct
            FROM prematch_features
            UNION ALL
            SELECT
                'away_rolling_xg',
                COUNT(*),
                COUNT(away_rolling_xg),
                ROUND(COUNT(away_rolling_xg) * 100.0 / COUNT(*), 2)
            FROM prematch_features
            UNION ALL
            SELECT
                'home_recent_form_points',
                COUNT(*),
                COUNT(home_recent_form_points),
                ROUND(COUNT(home_recent_form_points) * 100.0 / COUNT(*), 2)
            FROM prematch_features
            UNION ALL
            SELECT
                'home_fatigue_index',
                COUNT(*),
                COUNT(home_fatigue_index),
                ROUND(COUNT(home_fatigue_index) * 100.0 / COUNT(*), 2)
            FROM prematch_features;
        "
        echo ""

        # 3. 联赛分布
        echo "【3. 联赛分布】"
        docker-compose exec -T db psql -U football_user -d football_prediction_dev -c "
            SELECT
                league_name,
                COUNT(*) AS match_count,
                ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER(), 2) AS percentage
            FROM prematch_features
            GROUP BY league_name
            ORDER BY match_count DESC;
        "
        echo ""

        # 4. 样本数据
        echo "【4. 样本数据验证】"
        docker-compose exec -T db psql -U football_user -d football_prediction_dev -c "
            SELECT
                match_id,
                match_date,
                home_team,
                away_team,
                home_rolling_xg,
                away_rolling_xg,
                rolling_xg_diff,
                home_history_count,
                away_history_count,
                is_valid
            FROM prematch_features
            ORDER BY RANDOM()
            LIMIT 3;
        "
        echo ""

        echo "============================================================================"
        echo "                        报告结束"
        echo "============================================================================"

    } > "$REPORT_FILE" 2>&1

    # 显示报告内容
    cat "$REPORT_FILE"

    log_success "质量报告已保存: $REPORT_FILE"
    echo ""
}

# 主函数
main() {
    print_banner

    # 记录开始时间
    START_TIME=$(date +%s)

    # 执行各步骤
    check_environment
    backup_existing_data
    clear_old_features
    run_feature_calculation

    # 生成质量报告
    generate_quality_report

    # 计算耗时
    END_TIME=$(date +%s)
    DURATION=$((END_TIME - START_TIME))
    MINUTES=$((DURATION / 60))
    SECONDS=$((DURATION % 60))

    # 最终总结
    echo ""
    echo "============================================================================"
    log_success "V51.1 特征库重建完成！"
    echo "============================================================================"
    echo "总耗时: ${MINUTES} 分 ${SECONDS} 秒"
    echo ""
    echo "下一步操作："
    echo "  1. 查看质量报告: cat $REPORT_FILE"
    echo "  2. 启动预测服务: python -m src.ops.production_service"
    echo "  3. 查看数据文档: cat docs/V51_DATA_SCHEMA.md"
    echo "============================================================================"
    echo ""
}

# 执行主函数
main "$@"
