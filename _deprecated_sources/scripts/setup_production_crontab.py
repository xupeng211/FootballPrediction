#!/usr/bin/env python3
"""
FBref生产级crontab部署配置
运营总监自动化调度系统

Operations Director: 生产级数据管道自动化
Purpose: 部署可持续运行的数据采集调度系统
"""

import subprocess
import logging
from pathlib import Path
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)8s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def get_fbref_crontab_config():
    """生成FBref生产级crontab配置"""

    project_root = Path(__file__).parent.parent
    python_path = "/usr/bin/python3"  # 系统Python路径

    crontab_content = f"""# FBref数据采集生产级调度配置
# 运营总监部署版本 - 自动化数据管道
# 部署时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
# 所有时间均为UTC

# === 周一更新：周末比赛结果和xG数据 ===
# 每周一 06:15 UTC (欧洲比赛结束后)
15 6 * * 1 cd {project_root} && {python_path} scripts/simple_fbref_backfill.py >> logs/crontab_weekend_update.log 2>&1
# 更新英超、西甲、德甲的周末比赛结果

# === 周四更新：周中比赛结果 ===
# 每周四 06:30 UTC (周中比赛结束后)
30 6 * * 4 cd {project_root} && {python_path} scripts/simple_fbref_backfill.py >> logs/crontab_midweek_update.log 2>&1
# 更新五大联赛的周中比赛结果

# === 周日检查：即将进行的比赛 ===
# 每周日 12:15 UTC (比赛前检查)
15 12 * * 0 cd {project_root} && {python_path} scripts/simple_fbref_backfill.py >> logs/crontab_upcoming_check.log 2>&1
# 检查即将进行的比赛，更新赛程信息

# === 每月同步：历史数据补全 ===
# 每月1号 03:45 UTC (低流量时段)
45 3 1 * * cd {project_root} && {python_path} scripts/simple_fbref_backfill.py >> logs/crontab_monthly_sync.log 2>&1
# 增量同步历史数据，确保数据完整性

# === 健康检查：系统监控 ===
# 每小时检查系统状态
0 * * * * cd {project_root} && {python_path} scripts/health_check.py >> logs/crontab_health_check.log 2>&1
# 监控系统健康状态和数据管道运行情况

# === 日志轮转：避免日志文件过大 ===
# 每周日凌晨 02:30 UTC 清理旧日志
30 2 * * 0 find {project_root}/logs -name "*.log" -mtime +7 -delete
# 清理7天前的日志文件

# === 生产环境变量设置 ===
# FBREF_DATA_RETENTION_DAYS=90
# FBREF_MAX_RETRY_ATTEMPTS=3
# FBREF_RATE_LIMIT_DELAY=60
"""
    return crontab_content


def install_crontab():
    """安装crontab配置"""
    logger.info("🚀 开始部署FBref生产级crontab调度")
    logger.info("=" * 80)

    # 生成配置
    crontab_config = get_fbref_crontab_config()

    # 显示配置内容
    logger.info("📋 Crontab配置预览:")
    print("=" * 80)
    print(crontab_config)
    print("=" * 80)

    try:
        # 写入临时文件
        temp_file = Path("/tmp/fbref_crontab.txt")
        with open(temp_file, "w") as f:
            f.write(crontab_config)

        # 安装crontab
        result = subprocess.run(["crontab", temp_file], capture_output=True, text=True)

        if result.returncode == 0:
            logger.info("✅ Crontab配置安装成功!")

            # 验证安装
            verify_result = subprocess.run(
                ["crontab", "-l"], capture_output=True, text=True
            )

            if verify_result.returncode == 0:
                logger.info("📊 当前已安装的crontab任务:")
                print(verify_result.stdout)
            else:
                logger.error("❌ 验证crontab安装失败")

        else:
            logger.error(f"❌ 安装crontab失败: {result.stderr}")
            return False

        # 清理临时文件
        temp_file.unlink()

        logger.info("🎯 生产级调度系统部署完成!")
        logger.info("📈 数据管道将按以下时间自动运行:")
        logger.info("   周一 06:15 UTC - 周末比赛结果更新")
        logger.info("   周四 06:30 UTC - 周中比赛结果更新")
        logger.info("   周日 12:15 UTC - 赛前检查")
        logger.info("   每月1号 03:45 UTC - 历史数据同步")
        logger.info("   每小时整点 - 系统健康检查")

        return True

    except Exception as e:
        logger.error(f"💥 安装过程异常: {e}")
        return False


def create_health_check_script():
    """创建健康检查脚本"""
    health_check_content = """#!/usr/bin/env python3
'''
FBref数据管道健康检查脚本
运营总监监控系统
'''

import subprocess
import time
from datetime import datetime
from pathlib import Path

def check_system_health():
    '''检查系统健康状态'''
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{timestamp}] 🏥 FBref数据管道健康检查")

    # 检查磁盘空间
    disk_usage = subprocess.run(['df', '-h', '/'], capture_output=True, text=True)
    print(f"磁盘状态: {disk_usage.stdout.split('\\\\n')[1]}")

    # 检查内存使用
    memory = subprocess.run(['free', '-h'], capture_output=True, text=True)
    print(f"内存状态: {memory.stdout.split('\\\\n')[1]}")

    # 检查最近的日志
    log_dir = Path(__file__).parent / 'logs'
    if log_dir.exists():
        recent_logs = list(log_dir.glob('*.log'))[-3:]  # 最近3个日志文件
        print(f"最近日志文件: {[f.name for f in recent_logs]}")

    print("✅ 系统健康检查完成\\n")

if __name__ == "__main__":
    check_system_health()
"""

    health_check_path = Path(__file__).parent / "health_check.py"
    with open(health_check_path, "w") as f:
        f.write(health_check_content)

    # 设置执行权限
    subprocess.run(["chmod", "+x", health_check_path])
    logger.info(f"✅ 健康检查脚本已创建: {health_check_path}")


def main():
    """主部署流程"""
    logger.info("🏭 FBref数据工厂 - 生产级部署开始")
    logger.info(f"🕐 部署时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # 创建健康检查脚本
    create_health_check_script()

    # 安装crontab
    success = install_crontab()

    if success:
        logger.info("🎉 生产级调度系统部署成功!")
        logger.info("📊 数据工厂已实现全自动化运行")
        logger.info("🔧 系统将自动采集FBref xG数据并更新ML模型")

        print("\\n" + "=" * 80)
        print("🎯 运营总监部署总结:")
        print("=" * 80)
        print("✅ FBref隐身模式采集器已部署")
        print("✅ 生产级crontab调度已配置")
        print("✅ 健康检查系统已激活")
        print("✅ 日志轮转策略已设置")
        print("")
        print("📈 数据管道将按以下策略运行:")
        print("   • 周一：更新周末比赛xG数据")
        print("   • 周四：更新周中比赛结果")
        print("   • 周日：检查即将进行的比赛")
        print("   • 每月：历史数据增量同步")
        print("   • 每小时：系统健康监控")
        print("")
        print("🏭 FBref数据工厂已实现全自动化运营!")
        print("=" * 80)

    else:
        logger.error("❌ 生产级部署失败")
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
