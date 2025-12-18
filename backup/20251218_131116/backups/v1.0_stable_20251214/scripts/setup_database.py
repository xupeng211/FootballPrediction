"""
数据库初始化脚本
创建 SQLite 数据库文件和所有表结构
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到 Python 路径，确保可以正确导入 src 模块
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 现在可以安全地使用绝对路径导入
from src.database.models import Base

# 简单的日志配置，避免依赖未创建的utils模块
import logging

# 配置彩色日志输出
class ColoredFormatter(logging.Formatter):
    """彩色日志格式化器"""

    # ANSI颜色代码
    COLORS = {
        'DEBUG': '\033[36m',    # 青色
        'INFO': '\033[32m',     # 绿色
        'WARNING': '\033[33m',  # 黄色
        'ERROR': '\033[31m',    # 红色
        'CRITICAL': '\033[35m', # 紫色
        'RESET': '\033[0m'      # 重置
    }

    def format(self, record):
        # 添加颜色
        if record.levelname in self.COLORS:
            record.levelname = f"{self.COLORS[record.levelname]}{record.levelname}{self.COLORS['RESET']}"

        return super().format(record)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

# 应用彩色格式化器
logger = logging.getLogger(__name__)
handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(ColoredFormatter('%(asctime)s - %(levelname)s - %(message)s'))
logger.handlers.clear()
logger.addHandler(handler)

# 添加成功方法
def success(message):
    logger.info(f"✅ {message}")

def info(message):
    logger.info(f"ℹ️  {message}")

def warning(message):
    logger.warning(f"⚠️  {message}")

def error(message):
    logger.error(f"❌ {message}")


def create_database():
    """创建数据库和所有表"""
    try:
        # 数据库文件路径
        db_path = project_root / "data" / "football_prediction.db"

        # 确保 data 目录存在
        db_path.parent.mkdir(parents=True, exist_ok=True)

        # 数据库连接字符串
        database_url = f"sqlite:///{db_path}"

        # 创建数据库引擎
        from sqlalchemy import create_engine, text
        engine = create_engine(
            database_url,
            echo=False,  # 设为 True 可以看到 SQL 执行日志
            pool_pre_ping=True,  # 连接池预检查
        )

        # 创建所有表
        info(f"正在创建数据库表结构...")
        Base.metadata.create_all(bind=engine)

        # 测试数据库连接
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        info("数据库连接测试成功")

        success(f"数据库初始化成功！数据库文件: {db_path}")
        info(f"已创建以下表:")

        # 打印所有创建的表名
        table_names = Base.metadata.tables.keys()
        for table_name in sorted(table_names):
            info(f"   - {table_name}")

        # 打印数据库文件大小
        if db_path.exists():
            file_size = db_path.stat().st_size
            info(f"数据库文件大小: {file_size} bytes")

        return engine

    except Exception as e:
        error(f"数据库初始化失败: {str(e)}")
        raise


def create_directories():
    """创建项目所需的目录结构"""
    try:
        directories = [
            "data/raw",
            "data/processed",
            "data/models",
            "logs",
            "exports"
        ]

        for directory in directories:
            dir_path = project_root / directory
            dir_path.mkdir(parents=True, exist_ok=True)
            logger.debug(f"目录已创建: {dir_path}")

        info("项目目录结构创建完成")

    except Exception as e:
        error(f"创建目录结构失败: {str(e)}")
        raise


def check_dependencies():
    """检查必要的依赖"""
    try:
        import sqlalchemy
        info(f"✅ SQLAlchemy 版本: {sqlalchemy.__version__}")

        # 检查能否正确导入模型
        from src.database.base import Base
        from src.database.models import League, Team, Match
        info("✅ 数据模型导入成功")

        return True

    except ImportError as e:
        error(f"依赖检查失败: {str(e)}")
        return False


def main():
    """主函数"""
    info("🚀 开始初始化足球预测系统...")

    # 检查依赖
    if not check_dependencies():
        error("依赖检查失败，请确保已安装所有必要的包")
        sys.exit(1)

    try:
        # 1. 创建目录结构
        create_directories()

        # 2. 创建数据库
        engine = create_database()

        # 3. 显示初始化完成信息
        success("🎉 系统初始化完成！")
        info("📝 下一步操作:")
        info("   1. 运行冒烟测试: python scripts/test_ingestion.py")
        info("   2. 启动数据采集: python scripts/collect_data.py")
        info("   3. 启动Web界面: streamlit run src/web/app.py")

        return engine

    except Exception as e:
        error(f"系统初始化失败: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    engine = main()