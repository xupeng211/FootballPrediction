#!/usr/bin/env python3
"""
V41.77 环境检测模块 - 数据库隔离验证
========================================

本模块确保数据库连接的安全性：
1. 检测 5432 端口被非 Docker 进程占用
2. 验证 Docker 数据库连接
3. 拒绝启动如果环境不安全

Author: 首席系统架构师
Version: V41.77
Date: 2026-01-15
"""

import logging
import socket
from dataclasses import dataclass
from enum import Enum
from typing import Optional

logger = logging.getLogger(__name__)


class EnvironmentValidationError(Exception):
    """环境验证失败异常"""
    pass


class ProcessType(Enum):
    """进程类型"""
    DOCKER = "docker"
    SYSTEMD = "systemd"
    POSTGRES = "postgres"
    UNKNOWN = "unknown"


@dataclass
class PortInfo:
    """端口信息"""
    port: int
    is_in_use: bool
    process_type: ProcessType
    process_name: str
    is_docker: bool


def check_port_in_use(port: int, timeout: float = 1.0) -> PortInfo:
    """
    检查端口是否被占用

    Args:
        port: 端口号
        timeout: 连接超时时间

    Returns:
        PortInfo 对象
    """
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex(('127.0.0.1', port))
        sock.close()

        is_in_use = (result == 0)

        if is_in_use:
            # 尝试识别进程类型
            process_type = _identify_process_on_port(port)
        else:
            process_type = ProcessType.UNKNOWN

        return PortInfo(
            port=port,
            is_in_use=is_in_use,
            process_type=process_type,
            process_name=_get_process_name(process_type),
            is_docker=(process_type == ProcessType.DOCKER)
        )

    except (socket.error, OSError) as e:
        logger.warning(f"⚠️  检查端口 {port} 时出错: {e}")
        return PortInfo(
            port=port,
            is_in_use=False,
            process_type=ProcessType.UNKNOWN,
            process_name="unknown",
            is_docker=False
        )


def _identify_process_on_port(port: int) -> ProcessType:
    """
    识别占用端口的进程类型

    Args:
        port: 端口号

    Returns:
        ProcessType 枚举值
    """
    try:
        import subprocess
        result = subprocess.run(
            ['lsof', '-i', f':{port}', '-t', '-c'],
            capture_output=True,
            text=True,
            timeout=5
        )

        if result.returncode == 0:
            command = result.stdout.strip().lower()

            if 'docker' in command or 'dockerd' in command:
                return ProcessType.DOCKER
            elif 'postgres' in command or 'postmaster' in command:
                return ProcessType.POSTGRES
            elif 'systemd' in command:
                return ProcessType.SYSTEMD
            else:
                return ProcessType.UNKNOWN
        else:
            return ProcessType.UNKNOWN

    except (FileNotFoundError, subprocess.TimeoutExpired) as e:
        logger.debug(f"无法识别端口 {port} 的进程类型: {e}")
        return ProcessType.UNKNOWN


def _get_process_name(process_type: ProcessType) -> str:
    """
    获取进程类型的可读名称

    Args:
        process_type: ProcessType 枚举值

    Returns:
        进程名称字符串
    """
    return {
        ProcessType.DOCKER: "Docker",
        ProcessType.SYSTEMD: "Systemd",
        ProcessType.POSTGRES: "PostgreSQL",
        ProcessType.UNKNOWN: "Unknown"
    }.get(process_type, "Unknown")


def validate_database_environment(
    db_host: str,
    db_port: int = 5432,
    allow_docker: bool = True,
    allow_local: bool = False
) -> None:
    """
    验证数据库环境是否安全

    Args:
        db_host: 数据库主机
        db_port: 数据库端口
        allow_docker: 是否允许 Docker 进程
        allow_local: 是否允许本地 PostgreSQL 进程

    Raises:
        EnvironmentValidationError: 环境不安全时
    """
    logger.info(f"🔍 验证数据库环境: {db_host}:{db_port}")

    # 如果连接到本地，检查端口
    if db_host in ('localhost', '127.0.0.1'):
        port_info = check_port_in_use(db_port)

        if not port_info.is_in_use:
            raise EnvironmentValidationError(
                f"❌ 数据库端口 {db_port} 未被占用，可能数据库未启动"
            )

        logger.info(f"   端口 {db_port} 被 {port_info.process_name} 占用")

        # 检查进程类型
        if port_info.is_docker and not allow_docker:
            raise EnvironmentValidationError(
                f"❌ 数据库由 Docker 管理，但当前配置不允许 Docker 连接\n"
                f"   进程类型: {port_info.process_name}"
            )

        if port_info.process_type == ProcessType.POSTGRES and not allow_local:
            raise EnvironmentValidationError(
                f"❌ 数据库由本地 PostgreSQL 管理，但当前配置不允许本地连接\n"
                f"   进程类型: {port_info.process_name}\n"
                f"   💡 建议: 停止本地 PostgreSQL 服务 (sudo service postgresql stop)\n"
                f"   💡 或启动 Docker 数据库 (make up)"
            )

        logger.info(f"✅ 数据库环境验证通过: {port_info.process_name}")

    else:
        # 远程主机，跳过端口检查
        logger.info(f"ℹ️  远程数据库主机 {db_host}，跳过端口检查")


def validate_docker_database_running() -> None:
    """
    验证 Docker 数据库正在运行

    Raises:
        EnvironmentValidationError: Docker 数据库未运行时
    """
    try:
        import subprocess
        result = subprocess.run(
            ['docker', 'ps', '--filter', 'name=db', '--format', '{{.Status}}'],
            capture_output=True,
            text=True,
            timeout=10
        )

        if result.returncode != 0:
            raise EnvironmentValidationError(
                "❌ Docker 未运行或无法执行 docker 命令"
            )

        status = result.stdout.strip()
        if not status or 'Up' not in status:
            raise EnvironmentValidationError(
                "❌ Docker 数据库容器未运行\n"
                "   💡 建议: 启动 Docker 数据库 (make up)"
            )

        logger.info("✅ Docker 数据库正在运行")

    except FileNotFoundError:
        raise EnvironmentValidationError(
            "❌ Docker 命令未找到，请确保 Docker 已安装"
        )
    except subprocess.TimeoutExpired:
        raise EnvironmentValidationError(
            "❌ Docker 命令超时"
        )


def validate_no_local_postgres_conflict(db_port: int = 5432) -> None:
    """
    验证没有本地 PostgreSQL 服务与 Docker 冲突

    Args:
        db_port: 数据库端口

    Raises:
        EnvironmentValidationError: 检测到冲突时
    """
    try:
        import subprocess
        result = subprocess.run(
            ['sudo', 'service', 'postgresql', 'status'],
            capture_output=True,
            text=True,
            timeout=5
        )

        # 检查服务是否在运行
        is_running = (
            result.returncode == 0 and
            ('running' in result.stdout.lower() or 'active' in result.stdout.lower())
        )

        if is_running:
            raise EnvironmentValidationError(
                f"❌ 检测到本地 PostgreSQL 服务正在运行并占用端口 {db_port}\n"
                "   这可能导致连接到错误的数据库（本地空库）\n"
                "   💡 建议: 停止本地 PostgreSQL 服务\n"
                "   命令: sudo service postgresql stop"
            )

        logger.info(f"✅ 无本地 PostgreSQL 冲突")

    except FileNotFoundError:
        # service 命令不存在，可能不是 systemd 系统
        logger.debug("service 命令不可用，跳过本地 PostgreSQL 检查")
    except subprocess.TimeoutExpired:
        logger.warning("⚠️  检查 PostgreSQL 服务超时")
    except PermissionError:
        # 没有 sudo 权限，尝试其他方法
        _check_postgres_via_ps(db_port)


def _check_postgres_via_ps(db_port: int = 5432) -> None:
    """
    通过 ps 命令检查 PostgreSQL 进程

    Args:
        db_port: 数据库端口

    Raises:
        EnvironmentValidationError: 检测到冲突时
    """
    try:
        import subprocess
        result = subprocess.run(
            ['ps', 'aux'],
            capture_output=True,
            text=True,
            timeout=5
        )

        if 'postgres' in result.stdout.lower() and f'-p {db_port}' in result.stdout:
            raise EnvironmentValidationError(
                f"❌ 检测到 PostgreSQL 进程正在使用端口 {db_port}\n"
                "   这可能导致连接到错误的数据库\n"
                "   💡 建议: 停止本地 PostgreSQL 服务"
            )

        logger.info(f"✅ 无 PostgreSQL 进程冲突")

    except subprocess.TimeoutExpired:
        logger.warning("⚠️  ps 命令超时")


def validate_database_identity(conn, expected_db: str) -> None:
    """
    验证数据库身份

    Args:
        conn: 数据库连接
        expected_db: 期望的数据库名称

    Raises:
        EnvironmentValidationError: 数据库身份不匹配时
    """
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT current_database();")
            actual_db = cur.fetchone()[0]

            if actual_db != expected_db:
                raise EnvironmentValidationError(
                    f"❌ 数据库身份不匹配\n"
                    f"   期望: {expected_db}\n"
                    f"   实际: {actual_db}\n"
                    f"   这可能连接到错误的数据库"
                )

            logger.info(f"✅ 数据库身份验证通过: {actual_db}")

    except Exception as e:
        raise EnvironmentValidationError(
            f"❌ 无法验证数据库身份: {e}"
        )


# ============================================================================
# 便捷函数
# ============================================================================

def validate_production_environment(
    db_host: str,
    db_name: str,
    db_port: int = 5432
) -> None:
    """
    生产环境完整验证

    Args:
        db_host: 数据库主机
        db_name: 数据库名称
        db_port: 数据库端口

    Raises:
        EnvironmentValidationError: 环境验证失败时
    """
    logger.info("=" * 60)
    logger.info("V41.77: 生产环境验证")
    logger.info("=" * 60)

    # 1. 检查本地 PostgreSQL 冲突
    validate_no_local_postgres_conflict(db_port)

    # 2. 验证数据库环境
    validate_database_environment(
        db_host=db_host,
        db_port=db_port,
        allow_docker=True,
        allow_local=False
    )

    logger.info("=" * 60)
    logger.info("✅ 生产环境验证通过")
    logger.info("=" * 60)


if __name__ == "__main__":
    # 测试环境检测
    import sys

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s | %(levelname)-8s | %(message)s'
    )

    try:
        validate_production_environment(
            db_host="localhost",
            db_name="football_db",
            db_port=5432
        )
        print("✅ 环境验证通过")
        sys.exit(0)
    except EnvironmentValidationError as e:
        print(f"❌ 环境验证失败: {e}")
        sys.exit(1)
