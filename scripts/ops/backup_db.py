#!/usr/bin/env python3
"""
V33.1 Database Backup Engine - Python 接口

提供备份验证和辅助功能，供测试和 bash 脚本调用。

Author: 高级 SRE & 数据库专家
Date: 2026-01-11
Version: V33.1 (Database Insurance)
"""

import gzip
import os
from pathlib import Path
from typing import Dict, Any


def validate_backup(backup_path: str) -> Dict[str, Any]:
    """验证备份文件的有效性

    Args:
        backup_path: 备份文件路径

    Returns:
        包含验证结果的字典:
        - valid: bool, 是否有效
        - size: int, 文件大小
        - error: str, 错误信息（如果无效）
    """
    valid = True
    errors = []

    if not os.path.exists(backup_path):
        return {'valid': False, 'error': '文件不存在'}

    size = os.path.getsize(backup_path)

    # 检查大小
    if size < 100:
        return {'valid': False, 'size': size, 'error': '文件太小'}

    # 检查内容
    try:
        if backup_path.endswith('.gz'):
            with gzip.open(backup_path, 'rt') as f:
                content = f.read(1000)  # 读取前 1000 字符
        else:
            with open(backup_path, 'r') as f:
                content = f.read(1000)

        if 'PostgreSQL database dump' not in content:
            return {'valid': False, 'size': size, 'error': '不是有效的 pg_dump 文件'}
    except Exception as e:
        return {'valid': False, 'size': size, 'error': str(e)}

    return {'valid': True, 'size': size}


def backup_database(output_dir: str = None, db_name: str = 'football_db') -> str:
    """执行数据库备份（需要 docker-compose 环境）

    Args:
        output_dir: 输出目录，默认为项目根目录/backups
        db_name: 数据库名称

    Returns:
        备份文件路径

    Raises:
        Exception: 备份失败时抛出异常
    """
    import subprocess
    from datetime import datetime

    # 确定输出目录
    if output_dir is None:
        project_root = Path(__file__).parent.parent.parent
        output_dir = str(project_root / "backups")

    os.makedirs(output_dir, exist_ok=True)

    # 生成备份文件名
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_file = os.path.join(output_dir, f'football_db_{timestamp}.sql')

    # 执行备份（使用 docker-compose exec）
    result = subprocess.run([
        'docker-compose', 'exec', '-T', 'db', 'pg_dump',
        '-U', 'football_user',
        '--dbname=' + db_name,
        '--no-owner',
        '--no-acl'
    ], stdout=open(backup_file, 'w'), stderr=subprocess.PIPE)

    if result.returncode != 0:
        error_msg = result.stderr.decode() if result.stderr else '未知错误'
        raise Exception(f'备份失败: {error_msg}')

    return backup_file


if __name__ == "__main__":
    # 命令行接口
    import argparse

    parser = argparse.ArgumentParser(description="V33.1 Database Backup Engine")
    parser.add_argument("--validate", type=str, help="验证备份文件")
    parser.add_argument("--backup", action="store_true", help="执行备份")
    parser.add_argument("--output-dir", type=str, help="输出目录")

    args = parser.parse_args()

    if args.validate:
        result = validate_backup(args.validate)
        print(f"验证结果: {'✅ 通过' if result['valid'] else '❌ 失败'}")
        if 'size' in result:
            print(f"文件大小: {result['size']} bytes")
        if 'error' in result:
            print(f"错误: {result['error']}")

    elif args.backup:
        try:
            backup_file = backup_database(output_dir=args.output_dir)
            print(f"✅ 备份成功: {backup_file}")
        except Exception as e:
            print(f"❌ 备份失败: {e}")
            exit(1)

    else:
        parser.print_help()
