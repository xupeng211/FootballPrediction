#!/usr/bin/env python3
"""
Phase 7.2: 设置测试环境并启动集成测试
"""

import os
import subprocess
import time
import socket
import sys

def run_command(cmd, description, check=True):
    """运行命令"""
    print(f"\n{'='*60}")
    print(f"🔧 {description}")
    print(f"执行: {' '.join(cmd)}")

    result = subprocess.run(cmd, capture_output=True, text=True)

    if check and result.returncode != 0:
        print(f"❌ 失败: {result.stderr}")
        return False

    print(f"✅ 成功")
    if result.stdout:
        print(result.stdout[:200])
    return True

def check_port(port, service):
    """检查端口是否开放"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(1)
    try:
        result = sock.connect_ex(('localhost', port))
        return result == 0
    finally:
        sock.close()

def wait_for_service(port, service, timeout=30):
    """等待服务启动"""
    print(f"⏳ 等待 {service} 端口 {port}...")
    for i in range(timeout):
        if check_port(port, service):
            print(f"✅ {service} 已就绪")
            return True
        time.sleep(1)
    print(f"⚠️ {service} 启动超时")
    return False

def phase7_2_setup_env():
    """Phase 7.2: 设置测试环境"""
    print("\n" + "="*80)
    print("Phase 7.2: 启动集成环境 (Docker)")
    print("="*80)

    # 1. 创建测试环境配置
    print("\n1️⃣ 创建测试环境配置...")

    # 创建.env.test
    env_test = """# 测试环境配置
DATABASE_URL=postgresql+asyncpg://test_user:test_pass@localhost:5432/football_test
REDIS_URL=redis://localhost:6379/1
KAFKA_BROKER=localhost:9092
KAFKA_TOPIC_PREFIX=test_

# 测试特定配置
TEST_ENV=pytest
PYTEST_CURRENT_TEST=integration
PYTEST_DISABLE_PLUGIN_AUTOLOAD=
"""

    with open(".env.test", "w") as f:
        f.write(env_test)
    print("✅ 创建了 .env.test")

    # 2. 创建pytest测试配置
    pytest_ini = """[tool:pytest]
testpaths = tests
python_files = test_*.py *_test.py
python_classes = Test*
python_functions = test_*
addopts =
    -ra
    --strict-markers
    --strict-config
    --ignore=tests/e2e/*.skip
    --ignore=tests/e2e/api/*.skip
    --ignore=tests/e2e/performance/*.skip
    --ignore=tests/e2e/workflows/*.skip
    --ignore=tests/e2e/test_prediction_workflow.skip
markers =
    unit: Unit tests
    integration: Integration tests
    e2e: End-to-end tests
    slow: Slow tests
    smoke: Smoke tests
asyncio_mode = auto
asyncio_default_fixture_loop_scope = function
filterwarnings =
    ignore::UserWarning
    ignore::DeprecationWarning
    ignore::PendingDeprecationWarning
"""

    with open("pytest.ini", "w") as f:
        f.write(pytest_ini)
    print("✅ 更新了 pytest.ini")

    # 3. 创建测试启动脚本
    test_script = """#!/bin/bash
# 测试环境启动脚本

echo "🚀 启动测试环境..."

# 启动Docker服务
docker-compose -f docker-compose.test.yml up -d

# 等待服务就绪
echo "⏳ 等待服务启动..."
sleep 10

# 检查服务状态
docker-compose -f docker-compose.test.yml ps

echo ""
echo "✅ 测试环境已启动！"
echo ""
echo "运行测试："
echo "  pytest tests/unit/                    # 单元测试"
echo "  pytest tests/integration/             # 集成测试"
echo "  pytest --cov=src --cov-report=html   # 覆盖率测试"
echo ""
echo "停止环境："
echo "  docker-compose -f docker-compose.test.yml down"
"""

    with open("scripts/start_test_env.sh", "w") as f:
        f.write(test_script)
    os.chmod("scripts/start_test_env.sh", 0o755)
    print("✅ 创建了测试启动脚本")

    return True

def phase7_2_start_services():
    """启动Docker服务"""
    print("\n2️⃣ 启动Docker服务...")

    # 停止可能存在的旧容器
    run_command(["docker-compose", "-f", "docker-compose.test.yml", "down"],
                  "停止旧容器", check=False)

    # 启动新容器
    if not run_command(["docker-compose", "-f", "docker-compose.test.yml", "up", "-d"],
                    "启动Docker服务"):
        return False

    print("\n⏳ 等待服务启动...")

    # 等待关键服务
    services = [
        (5432, "PostgreSQL"),
        (6379, "Redis"),
        (9092, "Kafka")
    ]

    for port, service in services:
        if not wait_for_service(port, service, timeout=30):
            print(f"⚠️ {service} 可能未完全启动，但继续...")

    # 显示服务状态
    run_command(["docker-compose", "-f", "docker-compose.test.yml", "ps"],
                "检查服务状态", check=False)

    return True

def main():
    """主函数"""
    # Phase 7.2
    phase7_2_setup_env()

    # 尝试启动Docker（如果可用）
    if os.system("docker --version > /dev/null 2>&1") == 0:
        if os.path.exists("docker-compose.test.yml"):
            phase7_2_start_services()
        else:
            print("\n⚠️ docker-compose.test.yml 不存在，跳过Docker启动")
    else:
        print("\n⚠️ Docker未安装，请手动安装或使用本地测试数据库")

    print("\n" + "="*80)
    print("Phase 7.2 完成!")
    print("="*80)

    print("\n测试环境配置完成！")
    print("\n下一步：")
    print("1. 运行: python phase7_create_new_tests.py")
    print("2. 创建services、domain、monitoring等模块的测试")
    print("3. 逐步提升覆盖率到50%+")

if __name__ == "__main__":
    main()