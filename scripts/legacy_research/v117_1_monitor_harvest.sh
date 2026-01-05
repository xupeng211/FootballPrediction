#!/bin/bash
# V117.1 Phase 1 收割进度实时监控脚本
#
# 用途：快速查看 Entity_P 库存和收割进度
# 使用方法：
#   chmod +x scripts/v117_1_monitor_harvest.sh
#   ./scripts/v117_1_monitor_harvest.sh

# 加载项目环境变量
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
fi

# 默认数据库连接参数（可通过环境变量覆盖）
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"
DB_NAME="${DB_NAME:-football_db}"
DB_USER="${DB_USER:-football_user}"

echo ""
echo "============================================================================"
echo "V117.1 Phase 1 收割进度 - 快速监控"
echo "============================================================================"
echo ""

# 单行摘要查询
echo ">>> Entity_P 总库存 & Phase 1 待收割"
echo "--------------------------------------------------------------------"
psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -t -c "
SELECT
    CONCAT('Entity_P 库存: ', COUNT(*), ' 场') as entity_p_inventory
FROM metrics_multi_source_data
WHERE source_name = 'Entity_P' AND final_h IS NOT NULL

UNION ALL

SELECT
    CONCAT('Phase 1 待收割: ', COUNT(*), ' 场')
FROM matches m
WHERE m.oddsportal_url IS NOT NULL
  AND m.oddsportal_url LIKE '%oddsportal.com%'
  AND m.is_finished = true
  AND NOT EXISTS (
      SELECT 1 FROM metrics_multi_source_data msd
      WHERE msd.match_id = m.match_id
        AND msd.source_name = 'Entity_P'
        AND msd.final_h IS NOT NULL
  );
"

echo ""
echo ">>> 今日收割统计"
echo "--------------------------------------------------------------------"
psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -t -c "
SELECT
    CONCAT('今日新增: ', COUNT(*), ' 场') as today_harvest
FROM metrics_multi_source_data
WHERE DATE(extracted_at) = CURRENT_DATE
  AND source_name = 'Entity_P'

UNION ALL

SELECT
    CONCAT('最近 24 小时: ', COUNT(*), ' 场')
FROM metrics_multi_source_data
WHERE extracted_at >= CURRENT_TIMESTAMP - INTERVAL '1 day'
  AND source_name = 'Entity_P';
"

echo ""
echo ">>> 各 Entity 库存对比"
echo "--------------------------------------------------------------------"
psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -t -c "
SELECT
    CONCAT(source_name, ': ', COUNT(*), ' 场') as entity_inventory
FROM metrics_multi_source_data
WHERE source_name IN ('Entity_P', 'Entity_W', 'Entity_B', 'Entity_L', 'Entity_AVG')
  AND final_h IS NOT NULL
GROUP BY source_name
ORDER BY COUNT(*) DESC;
"

echo ""
echo "============================================================================"
echo "提示：运行完整监控请执行"
echo "  psql -h $DB_HOST -U $DB_USER -d $DB_NAME -f scripts/v117_1_monitor_harvest.sql"
echo "============================================================================"
echo ""
