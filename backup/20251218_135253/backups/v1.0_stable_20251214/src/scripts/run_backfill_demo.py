#!/usr/bin/env python3
"""
L2数据回填演示脚本
Demo script for L2 data backfill
"""

import asyncio
import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.scripts.backfill_l2_matches import (
    BackfillManager,
    BackfillConfig,
    create_sample_input_file,
)


async def demo_basic_usage():
    """基本使用演示"""
    print("🚀 L2数据回填演示开始...")

    # 1. 创建示例输入文件
    print("\n📝 创建示例输入文件...")
    sample_file = "data/demo_matches.csv"
    create_sample_input_file(sample_file, 20)

    # 2. 配置回填参数
    print("\n⚙️ 配置回填参数...")
    config = BackfillConfig(
        input_file=sample_file,
        output_dir="data/demo_output",
        max_concurrent=3,  # 演示用低并发
        batch_size=10,
        request_timeout=10.0,
        enable_progress_bar=True,
        save_interval=5,
    )

    # 3. 创建回填管理器
    print("\n🏗️ 初始化回填管理器...")
    manager = BackfillManager(config)

    # 4. 运行回填
    print("\n🔄 开始数据回填...")
    try:
        stats = await manager.run_backfill()

        # 5. 显示结果
        print("\n✅ 回填完成!")
        print("📊 处理统计:")
        print(f"   总处理数: {stats.total_processed}")
        print(f"   成功数: {stats.successful}")
        print(f"   失败数: {stats.failed}")
        print(f"   成功率: {stats.success_rate:.1f}%")
        print(f"   处理速度: {stats.processing_rate:.2f} 个/秒")
        print(f"   总用时: {stats.elapsed_time:.1f} 秒")

    except KeyboardInterrupt:
        print("\n⏹️ 用户中断回填")
    except Exception as e:
        print(f"\n❌ 回填失败: {e}")


async def demo_error_handling():
    """错误处理演示"""
    print("\n🛡️ 错误处理演示...")

    # 创建包含无效ID的文件
    invalid_file = "data/invalid_matches.csv"
    Path(invalid_file).parent.mkdir(parents=True, exist_ok=True)

    with open(invalid_file, "w", encoding="utf-8") as f:
        f.write("match_id\n")
        f.write("invalid_id\n")  # 无效ID
        f.write("999999999\n")  # 不存在的ID
        f.write("1234567\n")  # 有效ID（如果存在）

    config = BackfillConfig(
        input_file=invalid_file,
        output_dir="data/error_demo_output",
        max_concurrent=2,
        enable_progress_bar=True,
    )

    manager = BackfillManager(config)

    print("测试包含无效ID的文件处理...")
    stats = await manager.run_backfill()

    print(f"错误处理结果: {stats.failed} 个失败, {stats.successful} 个成功")


def show_architecture_diagram():
    """显示架构图"""
    print("\n🏗️ L2回填架构图:")
    print("""
    ┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
    │   输入CSV文件    │───▶│   流式读取器     │───▶│   并发处理器     │
    │  match_ids     │    │ (Generator)      │    │ (Semaphore控制) │
    └─────────────────┘    └──────────────────┘    └─────────────────┘
                                      │                        │
                                      ▼                        ▼
    ┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
    │   L2Fetcher     │◀───┤   FotMob API      │◀───┤   重试机制       │
    │  (HTTP请求)      │    │  (数据获取)        │    │ (tenacity)       │
    └─────────────────┘    └──────────────────┘    └─────────────────┘
                                      │                        │
                                      ▼                        ▼
    ┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
    │   L2Parser      │◀───┤   Pydantic模型     │◀───┤   数据验证       │
    │  (数据解析)      │    │  (结构化处理)      │    │ (类型检查)       │
    └─────────────────┘    └──────────────────┘    └─────────────────┘
                                      │                        │
                                      ▼                        ▼
    ┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
    │   JSON文件       │◀───┤   进度监控        │◀───┤   日志记录       │
    │  (数据存储)      │    │  (tqdm进度条)     │    │ (结构化日志)     │
    └─────────────────┘    └──────────────────┘    └─────────────────┘
    """)


def print_usage_examples():
    """打印使用示例"""
    print("\n💡 使用示例:")
    print("""
# 1. 基本使用
python src/scripts/backfill_l2_matches.py

# 2. 自定义参数
python src/scripts/backfill_l2_matches.py \\
    --input data/matches_2024.csv \\
    --output data/l2_2024 \\
    --concurrent 20

# 3. 创建测试文件
python src/scripts/backfill_l2_matches.py --create-sample

# 4. 低并发模式（适合调试）
python src/scripts/backfill_l2_matches.py --concurrent 3

# 5. 高并发模式（生产环境）
python src/scripts/backfill_l2_matches.py --concurrent 30
    """)


async def main():
    """主函数"""
    print("🎯 L2数据回填脚本演示")
    print("=" * 50)

    # 显示架构
    show_architecture_diagram()

    # 显示使用示例
    print_usage_examples()

    # 询问用户是否运行演示
    try:
        choice = input("\n是否运行演示? (y/n): ").lower().strip()
        if choice == "y":
            await demo_basic_usage()
            await demo_error_handling()
        else:
            print("演示已跳过。请查看文档了解详细使用方法。")
    except KeyboardInterrupt:
        print("\n演示已取消")
    except Exception as e:
        print(f"\n演示失败: {e}")


if __name__ == "__main__":
    print("🚀 启动L2数据回填演示脚本")
    asyncio.run(main())
