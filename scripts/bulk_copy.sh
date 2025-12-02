#!/bin/bash
#!/bin/bash

# 批量COPY入库脚本 - 首席数据库架构师专用
# 使用PostgreSQL原生COPY命令极速导入CSV数据

set -e

echo "🚀 启动批量COPY导入 - 首席数据库架构师模式"
echo "=================================================="

# 数据目录
CSV_DIR="/home/user/projects/FootballPrediction/data/fbref"

# 检查目录是否存在
if [ ! -d "$CSV_DIR" ]; then
    echo "❌ 错误: CSV目录不存在: $CSV_DIR"
    exit 1
fi

# 计算CSV文件数量
FILE_COUNT=$(find "$CSV_DIR" -name "*.csv" | wc -l)
echo "📁 发现 $FILE_COUNT 个CSV文件"

if [ "$FILE_COUNT" -eq 0 ]; then
    echo "❌ 错误: 未找到CSV文件"
    exit 1
fi

# 记录开始时间
START_TIME=$(date +%s)

# 临时计数器
SUCCESS_FILES=0
TOTAL_ROWS=0

# 创建临时表的SQL（如果不存在）
docker-compose exec db psql -U postgres -d football_prediction << 'EOF'
-- 确保临时表存在
CREATE TABLE IF NOT EXISTS stg_fbref_matches (
    wk TEXT,
    "Day" TEXT,
    "Date" TEXT,
    "Time" TEXT,
    "Home" TEXT,
    "xG" TEXT,
    "Score" TEXT,
    "xG.1" TEXT,
    "Away" TEXT,
    "Attendance" TEXT,
    "Venue" TEXT,
    "Referee" TEXT,
    "Match Report" TEXT,
    "Notes" TEXT,
    source_file TEXT,
    loaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    processed BOOLEAN DEFAULT FALSE
);
EOF

echo "📋 临时表已准备就绪"

# 遍历所有CSV文件并执行COPY
for csv_file in "$CSV_DIR"/*.csv; do
    filename=$(basename "$csv_file")
    echo "📄 导入文件: $filename"

    # 计算文件大小
    file_size=$(stat -c%s "$csv_file")
    echo "📊 文件大小: $((file_size/1024))KB"

    # 执行COPY命令
    rows_copied=$(docker-compose exec -T db psql -U postgres -d football_prediction <<SQL
    -- 设置source_file列和loaded_at为当前时间
    ALTER TABLE stg_fbref_matches
    ADD COLUMN IF NOT EXISTS temp_source TEXT,
    ADD COLUMN IF NOT EXISTS temp_time TIMESTAMP;

    -- 使用COPY命令导入
    COPY stg_fbref_matches (wk, "Day", "Date", "Time", "Home", "xG", "Score", "xG.1", "Away", "Attendance", "Venue", "Referee", "Match Report", "Notes", temp_source, temp_time)
    FROM STDIN WITH CSV HEADER;
SQL
    echo "$csv_file" | docker-compose exec -T db psql -U postgres -d football_prediction -c "COPY stg_fbref_matches (wk, \"Day\", \"Date\", \"Time\", \"Home\", \"xG\", \"Score\", \"xG.1\", \"Away\", \"Attendance\", \"Venue\", \"Referee\", \"Match Report\", \"Notes\", temp_source, temp_time) FROM STDIN WITH CSV HEADER" > /dev/null

    if [ $? -eq 0 ]; then
        # 更新source_file字段
        docker-compose exec db psql -U postgres -d football_prediction -c "UPDATE stg_fbref_matches SET source_file = '$filename' WHERE source_file IS NULL OR loaded_at >= CURRENT_TIMESTAMP - INTERVAL '1 second';" > /dev/null

        # 获取导入的行数
        file_rows=$(docker-compose exec db psql -U postgres -d football_prediction -tAc "SELECT COUNT(*) FROM stg_fbref_matches WHERE source_file = '$filename';" | tr -d ' ')

        echo "✅ 导入完成: $file_rows 行"

        SUCCESS_FILES=$((SUCCESS_FILES + 1))
        TOTAL_ROWS=$((TOTAL_ROWS + file_rows))
    else
        echo "❌ 导入失败: $filename"
    fi

    echo "---"
done

# 计算总耗时
END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))

# 获取最终统计
echo "=================================================="
echo "🎉 批量COPY导入完成！"
echo "=================================================="
echo "⏱️  总耗时: ${DURATION}秒"
echo "📁 成功文件: $SUCCESS_FILES"
echo "❌ 失败文件: $((FILE_COUNT - SUCCESS_FILES))"
echo "⚽ 总数据行: $TOTAL_ROWS"
echo "🚀 平均速度: $((TOTAL_ROWS / DURATION)) 行/秒"

# 显示导入的数据样本
echo ""
echo "📊 导入数据预览:"
docker-compose exec db psql -U postgres -d football_prediction -c "SELECT source_file, COUNT(*) as rows FROM stg_fbref_models GROUP BY source_file ORDER BY rows DESC LIMIT 5;" 2>/dev/null || \
docker-compose exec db psql -U postgres -d football_prediction -c "SELECT source_file, COUNT(*) as rows FROM stg_fbref_matches GROUP BY source_file ORDER BY rows DESC LIMIT 5;"

echo ""
echo "🔧 下一步: 执行数据清洗与迁移SQL"
echo "💡 运行命令: python scripts/migrate_from_staging.py"

exit 0