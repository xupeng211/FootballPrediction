#!/usr/bin/env python3
"""
启动质量监控面板
Start Quality Monitoring Dashboard

启动实时质量监控面板API和前端服务
"""

import os
import sys
import subprocess
import time
import signal
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.core.logging_system import get_logger

logger = get_logger(__name__)


class QualityDashboardLauncher:
    """质量监控面板启动器"""

    def __init__(self):
        self.api_process = None
        self.frontend_process = None
        self.running = True

    def start_api_server(self):
        """启动API服务器"""
        logger.info("启动质量监控面板API服务器...")

        api_path = project_root / "src" / "quality_dashboard" / "api"
        api_main = api_path / "main.py"

        if not api_main.exists():
            logger.error(f"API服务器文件不存在: {api_main}")
            return False

        try:
            # 设置环境变量
            env = os.environ.copy()
            env["PYTHONPATH"] = str(project_root)

            # 启动API服务器
            self.api_process = subprocess.Popen(
                [sys.executable, str(api_main)],
                cwd=project_root,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

            logger.info(f"API服务器已启动 (PID: {self.api_process.pid})")

            # 等待服务器启动
            time.sleep(3)

            # 检查服务器是否正常运行
            if self.api_process.poll() is None:
                logger.info("✅ API服务器启动成功")
                return True
            else:
                stdout, stderr = self.api_process.communicate()
                logger.error("API服务器启动失败:")
                logger.error(f"stdout: {stdout}")
                logger.error(f"stderr: {stderr}")
                return False

        except Exception as e:
            logger.error(f"启动API服务器时发生错误: {e}")
            return False

    def start_frontend_server(self):
        """启动前端服务器"""
        logger.info("启动前端开发服务器...")

        frontend_path = project_root / "src" / "quality_dashboard" / "frontend"

        if not frontend_path.exists():
            logger.warning(f"前端目录不存在: {frontend_path}")
            logger.info("跳过前端服务器启动")
            return True

        try:
            # 检查是否已安装依赖
            package_json = frontend_path / "package.json"
            node_modules = frontend_path / "node_modules"

            if not package_json.exists():
                logger.error("package.json 不存在")
                return False

            if not node_modules.exists():
                logger.info("安装前端依赖...")
                install_process = subprocess.run(
                    ["npm", "install"], cwd=frontend_path, capture_output=True, text=True
                )

                if install_process.returncode != 0:
                    logger.error(f"安装前端依赖失败: {install_process.stderr}")
                    return False

                logger.info("✅ 前端依赖安装完成")

            # 启动前端开发服务器
            self.frontend_process = subprocess.Popen(
                ["npm", "start"],
                cwd=frontend_path,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

            logger.info(f"前端服务器已启动 (PID: {self.frontend_process.pid})")
            logger.info("✅ 前端服务器启动成功")
            return True

        except Exception as e:
            logger.error(f"启动前端服务器时发生错误: {e}")
            return False

    def stop_services(self):
        """停止所有服务"""
        logger.info("正在停止服务...")
        self.running = False

        if self.api_process:
            logger.info("停止API服务器...")
            self.api_process.terminate()
            try:
                self.api_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.api_process.kill()
            logger.info("✅ API服务器已停止")

        if self.frontend_process:
            logger.info("停止前端服务器...")
            self.frontend_process.terminate()
            try:
                self.frontend_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.frontend_process.kill()
            logger.info("✅ 前端服务器已停止")

    def print_access_info(self):
        """打印访问信息"""
        print("\n" + "=" * 60)
        print("🚀 质量监控面板已启动")
        print("=" * 60)
        print("📊 API服务器: http://localhost:8001")
        print("🌐 前端界面: http://localhost:3000")
        print("📡 WebSocket: ws://localhost:8001/ws")
        print("🔗 API文档: http://localhost:8001/docs")
        print("=" * 60)
        print("按 Ctrl+C 停止服务")
        print("=" * 60 + "\n")

    def run(self):
        """运行质量监控面板"""
        try:
            # 注册信号处理器
            def signal_handler(signum, frame):
                logger.info("接收到停止信号")
                self.stop_services()
                sys.exit(0)

            signal.signal(signal.SIGINT, signal_handler)
            signal.signal(signal.SIGTERM, signal_handler)

            # 启动API服务器
            if not self.start_api_server():
                logger.error("API服务器启动失败，退出")
                return False

            # 启动前端服务器
            if not self.start_frontend_server():
                logger.warning("前端服务器启动失败，但API服务器仍在运行")

            # 打印访问信息
            self.print_access_info()

            # 保持运行
            while self.running:
                time.sleep(1)

                # 检查API服务器状态
                if self.api_process and self.api_process.poll() is not None:
                    logger.error("API服务器意外停止")
                    break

                # 检查前端服务器状态
                if self.frontend_process and self.frontend_process.poll() is not None:
                    logger.warning("前端服务器已停止")

            return True

        except KeyboardInterrupt:
            logger.info("用户中断")
            return True
        except Exception as e:
            logger.error(f"运行过程中发生错误: {e}")
            return False
        finally:
            self.stop_services()


def main():
    """主函数"""
    launcher = QualityDashboardLauncher()

    try:
        success = launcher.run()
        if success:
            logger.info("质量监控面板运行完成")
        else:
            logger.error("质量监控面板启动失败")
            sys.exit(1)
    except Exception as e:
        logger.error(f"启动质量监控面板时发生错误: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
