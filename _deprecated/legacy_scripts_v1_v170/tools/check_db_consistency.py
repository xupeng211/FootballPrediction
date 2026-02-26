#!/usr/bin/env python3
"""
V26.7 数据库一致性检测脚本

目的：确保所有代码、配置和实际使用的数据库名称完全一致

架构要求：
1. .env 文件中的 DB_NAME 必须与 docker-compose.yml 中的 POSTGRES_DB 一致
2. Python 代码读取的配置必须与 .env 文件一致
3. 实际连接的数据库必须与配置一致

作者：高级数据库专家 & 全栈架构师
日期：2026-01-07
"""

import os
import sys
import psycopg2
from pathlib import Path

# V29.0 P0 整改: 标准化 .env 加载
from dotenv import load_dotenv
load_dotenv(override=True)

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.config_unified import get_settings


def check_env_file():
    """检查 .env 文件中的数据库配置"""
    print("\n" + "="*70)
    print("📋 Step 1: 检查 .env 文件配置")
    print("="*70)

    env_path = Path(__file__).parent.parent.parent / ".env"
    if not env_path.exists():
        print("❌ .env 文件不存在！")
        return None

    env_config = {}
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line.startswith("DB_") and "=" in line and not line.startswith("#"):
                key, value = line.split("=", 1)
                env_config[key] = value

    print(f"✅ .env 文件路径: {env_path}")
    print(f"  • DB_HOST = {env_config.get('DB_HOST', 'NOT SET')}")
    print(f"  • DB_PORT = {env_config.get('DB_PORT', 'NOT SET')}")
    print(f"  • DB_NAME = {env_config.get('DB_NAME', 'NOT SET')} ⚠️ 关键配置")
    print(f"  • DB_USER = {env_config.get('DB_USER', 'NOT SET')}")

    return env_config


def check_docker_compose():
    """检查 docker-compose.yml 中的数据库配置"""
    print("\n" + "="*70)
    print("🐳 Step 2: 检查 docker-compose.yml 配置")
    print("="*70)

    compose_path = Path(__file__).parent.parent.parent / "docker-compose.yml"
    if not compose_path.exists():
        print("❌ docker-compose.yml 文件不存在！")
        return None

    compose_config = {}
    with open(compose_path) as f:
        in_db_section = False
        for line in f:
            if "db:" in line and "container_name" not in line:
                in_db_section = True
            elif in_db_section:
                if "POSTGRES_DB" in line:
                    value = line.split("=")[1].strip(" '\"}")
                    compose_config['POSTGRES_DB'] = value
                elif "POSTGRES_USER" in line:
                    value = line.split("=")[1].strip(" '\"}")
                    compose_config['POSTGRES_USER'] = value
                elif line.startswith("  #"):
                    continue
                elif line.startswith("  ") and "=" not in line:
                    # 离开 db section
                    break

    print(f"✅ docker-compose.yml 路径: {compose_path}")
    print(f"  • POSTGRES_DB = {compose_config.get('POSTGRES_DB', 'NOT SET')} ⚠️ 关键配置")
    print(f"  • POSTGRES_USER = {compose_config.get('POSTGRES_USER', 'NOT SET')}")

    return compose_config


def check_python_config():
    """检查 Python 代码读取的配置"""
    print("\n" + "="*70)
    print("🐍 Step 3: 检查 Python 配置 (config_unified.py)")
    print("="*70)

    try:
        settings = get_settings()
        db_config = settings.database

        print(f"✅ 配置加载成功")
        print(f"  • host = {db_config.host} ⚠️ 关键配置")
        print(f"  • port = {db_config.port}")
        print(f"  • name = {db_config.name} ⚠️ 关键配置")
        print(f"  • user = {db_config.user}")

        return db_config
    except Exception as e:
        print(f"❌ 配置加载失败: {e}")
        return None


def check_actual_database(db_config):
    """检查实际连接的数据库"""
    print("\n" + "="*70)
    print("🔗 Step 4: 检查实际数据库连接")
    print("="*70)

    if not db_config:
        print("❌ 无法检查数据库连接（配置未加载）")
        return None

    try:
        conn = psycopg2.connect(
            host=db_config.host,
            port=db_config.port,
            database=db_config.name,
            user=db_config.user,
            password=db_config.password.get_secret_value()
        )

        with conn.cursor() as cur:
            # 查询当前数据库名称
            cur.execute("SELECT current_database();")
            actual_db_name = cur.fetchone()[0]

            # 查询 matches 表记录数
            cur.execute("SELECT COUNT(*) FROM matches;")
            match_count = cur.fetchone()[0]

            # 查询其他数据库列表
            cur.execute("SELECT datname FROM pg_database WHERE datistemplate = false ORDER BY datname;")
            all_databases = [row[0] for row in cur.fetchall()]

        print(f"✅ 数据库连接成功")
        print(f"  • 连接主机: {db_config.host}")
        print(f"  • 当前数据库: {actual_db_name} ⚠️ 实际使用")
        print(f"  • matches 表记录数: {match_count}")
        print(f"  • 所有数据库: {', '.join(all_databases)}")

        conn.close()

        return {
            'actual_db_name': actual_db_name,
            'match_count': match_count,
            'all_databases': all_databases
        }
    except Exception as e:
        print(f"❌ 数据库连接失败: {e}")
        return None


def validate_consistency(env_config, compose_config, db_config, actual_info):
    """验证所有配置是否一致"""
    print("\n" + "="*70)
    print("✅ Step 5: 一致性验证")
    print("="*70)

    issues = []

    # 检查 .env vs docker-compose.yml
    if env_config and compose_config:
        env_db = env_config.get('DB_NAME')
        compose_db = compose_config.get('POSTGRES_DB')
        if env_db != compose_db:
            issues.append(f"❌ .env DB_NAME ({env_db}) != docker-compose POSTGRES_DB ({compose_db})")
        else:
            print(f"✅ .env 与 docker-compose.yml 一致: {env_db}")

    # 检查 .env vs Python config
    if env_config and db_config:
        env_db = env_config.get('DB_NAME')
        py_db = db_config.name
        if env_db != py_db:
            issues.append(f"❌ .env DB_NAME ({env_db}) != Python config ({py_db})")
        else:
            print(f"✅ .env 与 Python 配置一致: {env_db}")

    # 检查 Python config vs actual database
    if db_config and actual_info:
        py_db = db_config.name
        actual_db = actual_info['actual_db_name']
        if py_db != actual_db:
            issues.append(f"❌ Python config ({py_db}) != 实际连接 ({actual_db})")
        else:
            print(f"✅ Python 配置与实际连接一致: {py_db}")

    # 最终判定
    print("\n" + "="*70)
    if issues:
        print("❌ 数据库配置不一致！发现以下问题：")
        for issue in issues:
            print(f"  {issue}")
        print("\n建议修复方案：")
        print("  1. 统一 .env 中的 DB_NAME")
        print("  2. 确保 docker-compose.yml 使用相同的环境变量")
        print("  3. 重启数据库服务：docker-compose restart db")
        return False
    else:
        print("✅ 数据库配置完全一致！")
        print(f"\n统一配置: {db_config.name}")
        return True


def main():
    """主函数"""
    print("="*70)
    print("🔍 V26.7 数据库一致性检测")
    print("="*70)

    # Step 1: 检查 .env
    env_config = check_env_file()

    # Step 2: 检查 docker-compose.yml
    compose_config = check_docker_compose()

    # Step 3: 检查 Python 配置
    db_config = check_python_config()

    # Step 4: 检查实际连接
    actual_info = check_actual_database(db_config)

    # Step 5: 验证一致性
    is_consistent = validate_consistency(env_config, compose_config, db_config, actual_info)

    # 返回状态码
    sys.exit(0 if is_consistent else 1)


if __name__ == "__main__":
    main()
