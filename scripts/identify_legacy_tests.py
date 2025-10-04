#!/usr/bin/env python3
"""
识别并标记依赖真实服务的遗留测试
"""

import os
import re
from pathlib import Path
from typing import List

# 需要标记为 legacy 的模式
LEGACY_PATTERNS = [
    r'redis\.Redis\(',          # 真实 Redis 连接
    r'mlflow\.client\.',        # MLflow 客户端
    r'mlflow\.tracking\.',      # MLflow 跟踪
    r'mlflow\.experiment\.',    # MLflow 实验
    r'kafka\.KafkaProducer\(',  # Kafka 生产者
    r'kafka\.KafkaConsumer\(',  # Kafka 消费者
    r'psycopg2\.connect\(',     # PostgreSQL 连接
    r'sqlalchemy\.create_engine\(',  # SQLAlchemy 创建引擎（非 SQLite）
    r'requests\.',              # HTTP 请求库
    r'httpx\.',                 # httpx 客户端
    r'urllib\.',                # urllib 请求
    r'@patch\.object\(.*\.[^M]', # Patch 非Mock对象
    r'os\.environ\[.*DB',       # 数据库环境变量
    r'os\.environ\[.*REDIS',    # Redis 环境变量
    r'os\.environ\[.*KAFKA',    # Kafka 环境变量
    r'os\.environ\[.*MLFLOW',   # MLflow 环境变量
]

# Mock 相关模式（不应标记为 legacy）
MOCK_PATTERNS = [
    r'MockRedis',
    r'MockMlflow',
    r'MockKafka',
    r'patch\(',
    r'AsyncMock',
    r'MagicMock',
    r'pytest\.mock',
]

def find_test_files(test_dir: Path) -> List[Path]:
    """查找所有测试文件"""
    test_files = []
    for root, dirs, files in os.walk(test_dir):
        # 跳过 __pycache__ 和 legacy 目录
        dirs[:] = [d for d in dirs if d != '__pycache__' and d != 'legacy']

        for file in files:
            if file.endswith('.py') and file.startswith('test_'):
                test_files.append(Path(root) / file)

    return test_files

def is_legacy_test(file_path: Path) -> bool:
    """判断测试文件是否包含真实服务依赖"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 检查是否包含 legacy 模式
    for pattern in LEGACY_PATTERNS:
        if re.search(pattern, content):
            # 排除 Mock 相关的行
            lines = content.split('\n')
            for line_num, line in enumerate(lines, 1):
                if re.search(pattern, line):
                    # 检查该行是否包含 mock 关键字
                    if not any(re.search(mock_pat, line) for mock_pat in MOCK_PATTERNS):
                        print(f"  📌 发现真实依赖: {file_path}:{line_num} - {line.strip()}")
                        return True

    return False

def add_legacy_marker(file_path: Path) -> bool:
    """为测试文件添加 legacy 标记"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 检查是否已经有 legacy 标记
    if '@pytest.mark.legacy' in content:
        print(f"  ✅ {file_path} 已有 legacy 标记")
        return False

    lines = content.split('\n')
    new_lines = []
    added = False

    for line in lines:
        new_lines.append(line)
        # 在类定义后添加标记
        if line.startswith('class Test') and not added:
            new_lines.append('    @pytest.mark.legacy')
            added = True

    if added:
        new_content = '\n'.join(new_lines)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f"  ✅ 已添加 legacy 标记: {file_path}")
        return True

    return False

def main():
    """主函数"""
    print("🔍 开始识别遗留测试...")

    base_dir = Path.cwd()
    test_dir = base_dir / 'tests/unit'
    test_files = find_test_files(test_dir)

    legacy_files = []

    print(f"\n📁 找到 {len(test_files)} 个测试文件")

    for test_file in test_files:
        print(f"\n🔍 检查: {test_file.relative_to(base_dir)}")
        if is_legacy_test(test_file):
            legacy_files.append(test_file)

    print("\n📊 识别结果:")
    print(f"  - 总测试文件: {len(test_files)}")
    print(f"  - 遗留测试: {len(legacy_files)}")

    if legacy_files:
        print("\n📋 遗留测试列表:")
        for f in legacy_files:
            print(f"  - {f.relative_to(base_dir)}")

        # 询问是否添加标记
        response = input("\n❓ 是否为这些测试添加 legacy 标记? (y/N): ")
        if response.lower() == 'y':
            for test_file in legacy_files:
                add_legacy_marker(test_file)
            print("\n✅ 已完成标记添加")
        else:
            print("\n⏭️  跳过标记添加")
    else:
        print("\n✅ 未发现需要标记的遗留测试")

    print("\n🎯 后续步骤:")
    print("  1. 运行测试: pytest tests/unit -m 'not legacy'")
    print("  2. 查看遗留测试: pytest tests/unit -m legacy")
    print("  3. 在 CI 中跳过: pytest tests/unit -m 'not legacy'")

if __name__ == '__main__':
    main()