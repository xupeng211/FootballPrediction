#!/usr/bin/env python3
"""
启动高级质量监控系统
Issue #123: Phase 3: 高级质量监控系统开发

使用方法:
  python scripts/start_advanced_monitoring.py [--port 8080] [--host 0.0.0.0]
"""

import argparse
import asyncio
import logging
import signal
import sys
from pathlib import Path

# 添加src到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from src.monitoring.advanced_monitoring_system import monitoring_system

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('logs/monitoring.log', encoding='utf-8')
    ]
)

logger = logging.getLogger(__name__)


def signal_handler(signum, frame):
    """信号处理器"""
    logger.info("接收到停止信号，正在关闭监控系统...")
    monitoring_system.monitoring_active = False
    sys.exit(0)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="启动高级质量监控系统")
    parser.add_argument("--host", default="0.0.0.0", help="监听主机地址 (默认: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=8080, help="监听端口 (默认: 8080)")
    parser.add_argument("--debug", action="store_true", help="启用调试模式")

    args = parser.parse_args()

    # 设置日志级别
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)

    # 注册信号处理器
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # 确保日志目录存在
    Path("logs").mkdir(exist_ok=True)

    logger.info("=" * 60)
    logger.info("🚀 启动高级质量监控系统")
    logger.info("=" * 60)
    logger.info(f"📊 监控面板: http://{args.host}:{args.port}")
    logger.info(f"📡 API端点: http://{args.host}:{args.port}/api")
    logger.info(f"🛡️ 质量门禁: 自动启用")
    logger.info(f"📈 实时监控: 自动启动")
    logger.info("=" * 60)

    try:
        # 启动监控系统
        monitoring_system.run(host=args.host, port=args.port)
    except KeyboardInterrupt:
        logger.info("用户停止监控系统")
    except Exception as e:
        logger.error(f"监控系统启动失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()