#!/bin/bash
# 设置自动化清理任务的脚本
# 使用方法: ./scripts/setup_auto_cleanup.sh

set -e

echo "🕐 开始设置自动化清理任务..."

# 获取当前项目路径
PROJECT_PATH="$(pwd)"
echo "📁 项目路径: $PROJECT_PATH"

# 创建Cron任务配置文件
CRON_FILE="/tmp/football_prediction_cron.txt"

cat > "$CRON_FILE" << EOF
# 足球预测项目自动化清理任务
# 每周五下午6点执行周清理
0 18 * * 5 cd $PROJECT_PATH && $PROJECT_PATH/scripts/weekly_cleanup.sh

# 每月最后一天下午6点执行月清理
0 18 28-31 * * cd $PROJECT_PATH && [[ \$(date -d tomorrow +\%d) -eq 1 ]] && $PROJECT_PATH/scripts/monthly_cleanup.sh

EOF

echo "📋 创建的Cron任务:"
cat "$CRON_FILE"

# 检查crontab是否已存在类似任务
echo ""
echo "🔍 检查现有Cron任务..."
if crontab -l 2>/dev/null | grep -q "weekly_cleanup.sh\|monthly_cleanup.sh"; then
    echo "⚠️  发现现有清理任务，将替换它们"
    # 备份现有crontab
    crontab -l 2>/dev/null > /tmp/crontab_backup_$(date +%Y%m%d_%H%M%S).txt || true

    # 创建新的crontab（排除旧的清理任务）
    crontab -l 2>/dev/null | grep -v "weekly_cleanup.sh\|monthly_cleanup.sh" > /tmp/new_crontab.txt || touch /tmp/new_crontab.txt
    cat "$CRON_FILE" >> /tmp/new_crontab.txt
    crontab /tmp/new_crontab.txt
    echo "✅ Cron任务已更新"
else
    # 直接添加新的清理任务
    (crontab -l 2>/dev/null; cat "$CRON_FILE") | crontab -
    echo "✅ Cron任务已添加"
fi

# 清理临时文件
rm -f "$CRON_FILE" /tmp/new_crontab.txt

echo ""
echo "📅 设置的自动化清理任务:"
echo "   - 周清理: 每周五下午6:00"
echo "   - 月清理: 每月最后一天下午6:00"
echo ""
echo "🔧 管理 Cron 任务:"
echo "   - 查看所有任务: crontab -l"
echo "   - 编辑任务: crontab -e"
echo "   - 删除所有任务: crontab -r (谨慎使用)"
echo ""
echo "🧪 测试清理脚本:"
echo "   - 手动执行周清理: $PROJECT_PATH/scripts/weekly_cleanup.sh"
echo "   - 手动执行月清理: $PROJECT_PATH/scripts/monthly_cleanup.sh"

# 验证脚本权限
for script in weekly_cleanup.sh monthly_cleanup.sh; do
    if [ -f "$PROJECT_PATH/scripts/$script" ]; then
        if [ -x "$PROJECT_PATH/scripts/$script" ]; then
            echo "✅ $script 脚本有执行权限"
        else
            echo "⚠️  $script 脚本没有执行权限，正在修复..."
            chmod +x "$PROJECT_PATH/scripts/$script"
        fi
    else
        echo "❌ $script 脚本不存在"
    fi
done

echo ""
echo "🎉 自动化清理设置完成！"
echo "📧 系统将在预定时间自动执行清理任务"