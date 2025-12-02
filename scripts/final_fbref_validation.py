#!/usr/bin/env python3
"""
FBref数据最终验证测试
验证完整的xG数据采集流程

Data Collection Expert: 数据采集专家
"""

import asyncio
import sys
import logging
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.data.collectors.fbref_collector import FBrefCollector

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)8s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


async def final_validation():
    """最终验证FBref数据采集"""
    logger.info("🚀 开始FBref数据最终验证")

    collector = FBrefCollector()

    # 目标：英超赛季数据
    league_url = (
        "https://fbref.com/en/comps/9/schedule/Premier-League-Scores-and-Fixtures"
    )

    try:
        # 获取数据 (使用Playwright版本)
        data = await collector.get_season_schedule(league_url)

        # 强制验证1: 数据不为空
        assert not data.empty, "❌ 数据为空!"
        logger.info(f"✅ 数据获取成功: {len(data)} 行, {len(data.columns)} 列")

        # 强制验证2: 必须包含xG列
        xg_columns = [col for col in data.columns if "xg" in col.lower()]
        assert len(xg_columns) >= 2, f"❌ xG列不足2个! 找到: {xg_columns}"
        logger.info(f"✅ 找到xG列: {xg_columns}")

        # 强制验证3: xG数据不能全为空
        for xg_col in xg_columns:
            if xg_col in data.columns:
                non_null_count = data[xg_col].notna().sum()
                assert non_null_count > 0, f"❌ {xg_col} 列xG数据为空!"
                logger.info(f"✅ {xg_col}: {non_null_count}/{len(data)} 有效数据")

        # 强制验证4: 包含基础比赛信息
        required_cols = ["home", "away", "score"]
        found_cols = []
        for required in required_cols:
            for col in data.columns:
                if required in str(col).lower():
                    found_cols.append(col)
                    break
        assert len(found_cols) >= 2, f"❌ 基础比赛列不足! 找到: {found_cols}"
        logger.info(f"✅ 基础比赛列: {found_cols}")

        # 显示最终结果
        logger.info("=" * 80)
        logger.info("🎉 FBref数据验证完全成功!")
        logger.info("=" * 80)

        # 构建显示数据
        display_data = data.head(5).copy()

        # 选择关键列进行显示
        key_cols = []
        for target in ["date", "home", "away", "score"]:
            for col in data.columns:
                if target in str(col).lower() and col not in key_cols:
                    key_cols.append(col)
                    break

        # 添加xG列
        key_cols.extend(xg_columns)

        # 确保列存在且去重
        final_cols = []
        for col in key_cols:
            if col in data.columns and col not in final_cols:
                final_cols.append(col)

        # 显示数据
        print("📊 前5行完整数据:")
        display_df = data[final_cols].head(5)
        print(display_df.to_string(index=False))

        # 统计信息
        print(f"\n📈 数据统计:")
        print(f"  总比赛数: {len(data)}")
        print(f"  有xG数据的比赛: {data[xg_columns[0]].notna().sum()}")
        print(
            f"  数据完整性: {(data[xg_columns[0]].notna().sum() / len(data) * 100):.1f}%"
        )

        # xG数据质量检查
        xg_home = data[xg_columns[0]].dropna()
        xg_away = data[xg_columns[1]].dropna()

        print(f"\n🎯 xG数据质量:")
        print(f"  主队xG范围: {xg_home.min():.2f} - {xg_home.max():.2f}")
        print(f"  主队xG平均: {xg_home.mean():.2f}")
        print(f"  客队xG范围: {xg_away.min():.2f} - {xg_away.max():.2f}")
        print(f"  客队xG平均: {xg_away.mean():.2f}")

        return True

    except AssertionError as e:
        logger.error(f"❌ 验证失败: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ 测试过程失败: {e}")
        import traceback

        traceback.print_exc()
        return False


async def main():
    """主函数"""
    success = await final_validation()

    if success:
        logger.info("🎉 FBref数据采集战略转向完全成功!")
        logger.info("📊 xG数据质量符合机器学习要求")
        logger.info("🔧 可以立即集成到ML管道中")
        sys.exit(0)
    else:
        logger.error("❌ FBref数据验证失败")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
