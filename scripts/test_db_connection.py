#!/usr/bin/env python3
"""
PostgresDataLoader 测试脚本

用于验证 PostgresDataLoader 能否正确从数据库加载数据。
显示真实数据的前5行记录。
"""

import asyncio
import sys
import os
import logging
from datetime import datetime

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.ml.data.postgres_loader import PostgresDataLoader

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


async def test_database_connection():
    """测试数据库连接和数据加载"""
    print("🔗 开始测试 PostgresDataLoader...")
    print("=" * 60)

    try:
        # 1. 创建加载器实例
        print("1️⃣ 创建 PostgresDataLoader 实例...")
        loader = PostgresDataLoader(
            batch_size=100,
            selected_columns=[
                'id', 'home_team_id', 'away_team_id', 'home_score', 'away_score',
                'match_date', 'status', 'home_team_name', 'away_team_name', 'league_id'
            ],
            max_records=1000
        )
        print("✅ PostgresDataLoader 创建成功")

        # 2. 测试数据库连接
        print("\n2️⃣ 测试数据库连接...")
        connection_ok = await loader.test_connection()
        if connection_ok:
            print("✅ 数据库连接成功")
        else:
            print("❌ 数据库连接失败")
            return False

        # 3. 获取数据摘要
        print("\n3️⃣ 获取数据摘要...")
        summary = await loader.get_data_summary()
        print(f"📊 数据状态: {summary['status']}")
        print(f"📈 总记录数: {summary['total_records']}")

        if summary['status'] == 'success':
            print(f"📋 可用列: {summary['available_columns']}")

        if summary.get('sample_data'):
            print("📄 样本数据结构:")
            for key, value in summary['sample_data'][0].items():
                print(f"   {key}: {value} ({type(value).__name__})")

        # 4. 加载真实数据
        print("\n4️⃣ 加载真实比赛数据...")
        df = await loader.load_data(limit=10)  # 只加载前10条用于测试

        if df.empty:
            print("⚠️ 没有加载到数据，返回空 DataFrame")
            return True  # 连接成功但没有数据不算失败

        print(f"✅ 成功加载 {len(df)} 条记录")
        print(f"📊 DataFrame 形状: {df.shape}")
        print(f"📋 DataFrame 列: {list(df.columns)}")

        # 5. 显示前5行数据
        print("\n5️⃣ 显示前5行真实数据:")
        print("=" * 80)

        display_df = df.head(5).copy()

        # 格式化日期显示
        if 'match_date' in display_df.columns:
            display_df['match_date'] = display_df['match_date'].dt.strftime('%Y-%m-%d %H:%M:%S')

        # 格式化数值显示
        for col in ['home_score', 'away_score', 'home_team_id', 'away_team_id']:
            if col in display_df.columns:
                display_df[col] = display_df[col].astype(int)

        print(display_df.to_string(index=False))
        print("=" * 80)

        # 6. 数据质量检查
        print("\n6️⃣ 数据质量检查:")
        null_counts = df.isnull().sum()
        if null_counts.any():
            print("⚠️ 发现空值:")
            for col, count in null_counts.items():
                if count > 0:
                    print(f"   {col}: {count} 个空值")
        else:
            print("✅ 数据完整，没有空值")

        # 检查得分数据
        if 'home_score' in df.columns and 'away_score' in df.columns:
            negative_scores = (df['home_score'] < 0) | (df['away_score'] < 0)
            if negative_scores.any():
                print("⚠️ 发现负分数据")
            else:
                print("✅ 得分数据正常 (非负)")

        print("\n🎉 PostgresDataLoader 测试完成！")
        return True

    except Exception as e:
        print(f"\n❌ 测试过程中发生错误: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """主函数"""
    print("🚀 PostgresDataLoader 验证脚本启动")
    print(f"⏰ 开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    success = await test_database_connection()

    print(f"\n⏰ 结束时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    if success:
        print("✅ 验证成功！PostgresDataLoader 可以正常工作")
        sys.exit(0)
    else:
        print("❌ 验证失败！请检查数据库连接和配置")
        sys.exit(1)


if __name__ == "__main__":
    # 运行异步测试
    asyncio.run(main())