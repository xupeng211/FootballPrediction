#!/usr/bin/env python3
"""
V41.59: 环境检测模块 - 智能识别 Docker/WSL2/本地环境
====================================================
用途: 彻底终结"敲错门"问题，智能选择数据库连接
"""

import os
import socket
from enum import Enum
from pathlib import Path
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class EnvironmentType(str, Enum):
    """环境类型枚举"""
    DOCKER = "docker"
    WSL2 = "wsl2"
    LOCAL = "local"
    UNKNOWN = "unknown"


class EnvironmentDetector:
    """V41.59: 环境检测器 - 智能识别运行环境"""

    # Docker 容器标识文件
    DOCKERMARKER_FILES = [
        "/.dockerenv",
        "/proc/1/cgroup"
    ]

    # WSL2 标识文件
    WSL2_MARKER = "/proc/version"
    WSL2_SIGNATURE = "microsoft"

    # 本地 Postgres 默认端口
    LOCAL_PG_PORT = 5432

    @staticmethod
    def detect_environment() -> EnvironmentType:
        """
        智能检测当前运行环境

        优先级: Docker > WSL2 > Local > Unknown

        Returns:
            EnvironmentType: 检测到的环境类型
        """
        # 1. 检测 Docker 环境
        if EnvironmentDetector._is_docker():
            logger.debug("🐳 检测到 Docker 环境")
            return EnvironmentType.DOCKER

        # 2. 检测 WSL2 环境
        if EnvironmentDetector._is_wsl2():
            logger.debug("🟡 检测到 WSL2 环境")
            return EnvironmentType.WSL2

        # 3. 默认为本地环境
        logger.debug("🏠 检测到本地环境")
        return EnvironmentType.LOCAL

    @staticmethod
    def _is_docker() -> bool:
        """检测是否在 Docker 容器内运行"""
        # 方法 1: 检查 /.dockerenv 文件
        if Path("/.dockerenv").exists():
            return True

        # 方法 2: 检查 /proc/1/cgroup 内容
        try:
            cgroup_path = Path("/proc/1/cgroup")
            if cgroup_path.exists():
                cgroup_content = cgroup_path.read_text()
                if "docker" in cgroup_content.lower() or "kubepods" in cgroup_content.lower():
                    return True
        except Exception:
            pass

        return False

    @staticmethod
    def _is_wsl2() -> bool:
        """检测是否在 WSL2 环境运行"""
        try:
            version_path = Path(EnvironmentDetector.WSL2_MARKER)
            if version_path.exists():
                version_content = version_path.read_text().lower()
                if EnvironmentDetector.WSL2_SIGNATURE in version_content:
                    return True
        except Exception:
            pass

        return False

    @staticmethod
    def get_optimal_db_host(
        preferred_host: Optional[str] = None,
        env_var_host: Optional[str] = None
    ) -> str:
        """
        获取最优数据库主机地址

        Args:
            preferred_host: 用户首选的主机地址
            env_var_host: 环境变量中的主机地址

        Returns:
            str: 最优数据库主机地址
        """
        env = EnvironmentDetector.detect_environment()

        # 优先级 1: 用户显式指定
        if preferred_host and preferred_host != "localhost":
            return preferred_host

        # 优先级 2: 环境变量（非 localhost）
        if env_var_host and env_var_host != "localhost":
            return env_var_host

        # 优先级 3: 环境智能推荐
        if env == EnvironmentType.DOCKER:
            # Docker 容器内使用服务名
            logger.info("🐳 Docker 环境: 使用 'db' 作为数据库主机")
            return "db"

        elif env == EnvironmentType.WSL2:
            # WSL2 环境: 检查端口占用情况
            if EnvironmentDetector._is_port_in_use("localhost", 5432):
                logger.warning("⚠️  检测到本地 PostgreSQL 服务占用 5432 端口")
                logger.warning("🚨 可能导致连接到错误的数据库（本地空库）")
                logger.warning("💡 建议: 停止本地 PostgreSQL 服务 (sudo service postgresql stop)")
                # 仍然返回 localhost，让用户自己处理
                return "localhost"
            else:
                logger.info("✅ WSL2 环境: 5432 端口未被占用，安全使用 localhost")
                return "localhost"

        else:
            # 本地环境: 使用 localhost
            return "localhost"

    @staticmethod
    def _is_port_in_use(host: str, port: int) -> bool:
        """检测端口是否被占用"""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(1)
                result = s.connect_ex((host, port))
                return result == 0
        except Exception:
            return False

    @staticmethod
    def verify_database_identity(
        db_host: str,
        db_name: str,
        db_user: str,
        db_password: str,
        db_port: int = 5432
    ) -> tuple[bool, str]:
        """
        验证数据库身份（检测是否连接到正确的数据库）

        Args:
            db_host: 数据库主机
            db_name: 数据库名称
            db_user: 数据库用户
            db_password: 数据库密码（普通字符串或 SecretStr）
            db_port: 数据库端口

        Returns:
            tuple[bool, str]: (是否为真实库, 错误消息)
        """
        # 处理 SecretStr 类型
        password = db_password
        if hasattr(db_password, 'get_secret_value'):
            password = db_password.get_secret_value()

        try:
            import psycopg2
            from psycopg2.extras import RealDictCursor

            # 尝试连接
            conn = psycopg2.connect(
                host=db_host,
                port=db_port,
                database=db_name,
                user=db_user,
                password=password,
                cursor_factory=RealDictCursor,
                connect_timeout=5
            )

            try:
                with conn.cursor() as cursor:
                    # 1. 检查 matches 表是否存在
                    cursor.execute("SELECT to_regclass('public.matches');")
                    result = cursor.fetchone()
                    matches_table = result['to_regclass'] if result else None

                    if matches_table is None:
                        conn.close()
                        return False, (
                            "🚨 端口冲突：检测到本地空库！\n"
                            f"   连接主机: {db_host}:{db_port}\n"
                            f"   数据库: {db_name}\n"
                            "   问题: public.matches 表不存在\n"
                            "   解决: 请关闭本地 PostgreSQL 服务\n"
                            "   命令: sudo service postgresql stop"
                        )

                    # 2. 检查 matches 表记录数
                    cursor.execute("SELECT COUNT(*) as count FROM matches;")
                    result = cursor.fetchone()
                    match_count = result['count'] if result else 0

                    if match_count < 100:
                        conn.close()
                        return False, (
                            f"⚠️  数据库疑似空库或测试库\n"
                            f"   matches 表仅有 {match_count} 条记录\n"
                            f"   期望: >= 100 条记录\n"
                            f"   请检查是否连接到正确的数据库实例"
                        )

                    return True, f"✅ 数据库验证通过 ({match_count} 场比赛)"

            finally:
                conn.close()

        except Exception as e:
            return False, f"❌ 数据库连接失败: {str(e)}"


# 单例模式简化导出
_detector = EnvironmentDetector()

detect_environment = _detector.detect_environment
get_optimal_db_host = _detector.get_optimal_db_host
verify_database_identity = _detector.verify_database_identity


if __name__ == "__main__":
    """测试环境检测"""
    print("=" * 60)
    print("V41.59: 环境检测测试")
    print("=" * 60)

    # 1. 环境检测
    env = detect_environment()
    print(f"当前环境: {env.value}")

    # 2. 最优主机
    host = get_optimal_db_host()
    print(f"推荐数据库主机: {host}")

    # 3. 数据库验证
    is_valid, message = verify_database_identity(
        db_host=host,
        db_name="football_db",
        db_user="football_user",
        db_password="football_pass"
    )
    print(f"数据库验证: {message}")

    print("=" * 60)
