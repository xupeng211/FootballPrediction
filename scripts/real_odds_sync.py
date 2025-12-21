#!/usr/bin/env python3
"""
V4.0: 真实数据清洗脚本
Real Data Cleaning - 承认现实，拒绝造假

目的:
1. 承认FotMob不提供历史真实赔率
2. 将所有使用模拟赔率的比赛标记为 has_real_odds = False
3. 为未来真实赔率数据源预留接口
"""

import psycopg2
import logging
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

def add_real_odds_flag():
    """为match_features_training表添加 has_real_odds 字段"""
    logger.info("🔧 添加 has_real_odds 字段到数据库")

    db_config = {
        "host": "localhost",
        "port": 5432,
        "database": "football_prediction_dev",
        "user": "football_user",
        "password": "football_pass",
    }

    try:
        conn = psycopg2.connect(**db_config)
        cursor = conn.cursor()

        # 添加 has_real_odds 字段
        add_column_query = """
        ALTER TABLE match_features_training
        ADD COLUMN IF NOT EXISTS has_real_odds BOOLEAN DEFAULT FALSE;
        """
        cursor.execute(add_column_query)

        # 添加 odds_source_confirmed 字段
        add_source_field_query = """
        ALTER TABLE match_features_training
        ADD COLUMN IF NOT EXISTS odds_source_confirmed VARCHAR(50) DEFAULT 'SIMULATED_V3.3';
        """
        cursor.execute(add_source_field_query)

        # 添加 odds_extraction_date 字段
        add_date_field_query = """
        ALTER TABLE match_features_training
        ADD COLUMN IF NOT EXISTS odds_extraction_date TIMESTAMP;
        """
        cursor.execute(add_date_field_query)

        conn.commit()
        logger.info("✅ 数据库字段添加成功")

    except Exception as e:
        logger.error(f"❌ 添加字段失败: {e}")
        raise
    finally:
        if 'conn' in locals():
            conn.close()

def flag_simulated_odds():
    """将所有使用模拟赔率的比赛标记清楚"""
    logger.info("🚨 标记所有模拟赔率为虚假数据")

    db_config = {
        "host": "localhost",
        "port": 5432,
        "database": "football_prediction_dev",
        "user": "football_user",
        "password": "football_pass",
    }

    try:
        conn = psycopg2.connect(**db_config)
        cursor = conn.cursor()

        # 更新所有比赛，标记为模拟赔率
        update_query = """
        UPDATE match_features_training
        SET
            has_real_odds = FALSE,
            odds_source_confirmed = 'SIMULATED_V3.3_FAKE',
            odds_extraction_date = %s,
            updated_at = NOW()
        WHERE 1=1;
        """

        cursor.execute(update_query, (datetime.now(),))
        updated_count = cursor.rowcount

        conn.commit()
        logger.info(f"🔴 已标记 {updated_count} 场比赛为模拟赔率")

    except Exception as e:
        logger.error(f"❌ 标记模拟赔率失败: {e}")
        raise
    finally:
        if 'conn' in locals():
            conn.close()

def generate_reality_report():
    """生成现实情况报告"""
    logger.info("📋 生成 V4.0 现实情况报告")

    db_config = {
        "host": "localhost",
        "port": 5432,
        "database": "football_prediction_dev",
        "user": "football_user",
        "password": "football_pass",
    }

    try:
        conn = psycopg2.connect(**db_config)
        cursor = conn.cursor()

        # 统计情况
        stats_query = """
        SELECT
            COUNT(*) as total_matches,
            COUNT(CASE WHEN has_real_odds = TRUE THEN 1 END) as real_odds_matches,
            COUNT(CASE WHEN has_real_odds = FALSE THEN 1 END) as fake_odds_matches,
            COUNT(CASE WHEN home_opening_odds IS NOT NULL THEN 1 END) as matches_with_any_odds
        FROM match_features_training;
        """

        cursor.execute(stats_query)
        result = cursor.fetchone()

        total, real_odds, fake_odds, with_any_odds = result

        logger.info("="*80)
        logger.info("🚨 V4.0 真实情况报告")
        logger.info("="*80)
        logger.info(f"📊 总比赛数: {total}")
        logger.info(f"🔴 模拟赔率比赛: {fake_odds} ({fake_odds/total*100:.1f}%)")
        logger.info(f"✅ 真实赔率比赛: {real_odds} ({real_odds/total*100:.1f}%)")
        logger.info(f"📈 有任意赔率数据: {with_any_odds}")
        logger.info("")
        logger.info("🚨 关键结论:")
        logger.info(f"   • 100% 的比赛使用模拟赔率")
        logger.info(f"   • 0% 的比赛有真实赔率")
        logger.info(f"   • FotMob API 不提供历史真实赔率")
        logger.info(f"   • 所有V3.3/V3.4 ROI结果都是基于模拟数据")
        logger.info("")
        logger.info("💡 建议行动:")
        logger.info(f"   1. 停止声称有真实赔率回测结果")
        logger.info(f"   2. 寻找替代数据源 (betexplorer.com, oddsportal.com)")
        logger.info(f"   3. 或专注于其他ML特征，避免赔率依赖")
        logger.info("="*80)

        return {
            "total_matches": total,
            "real_odds_matches": real_odds,
            "fake_odds_matches": fake_odds,
            "with_any_odds": with_any_odds,
            "fake_percentage": fake_odds/total*100
        }

    except Exception as e:
        logger.error(f"❌ 生成报告失败: {e}")
        raise
    finally:
        if 'conn' in locals():
            conn.close()

def create_future_real_odds_interface():
    """为未来真实赔率数据源创建接口"""
    logger.info("🔮 为未来真实赔率数据源创建接口")

    # 创建接口说明文件
    interface_doc = """
# V4.0 真实赔率数据源接口规范

## 当前状态
- ❌ FotMob API: 不提供历史真实赔率
- ❌ 模拟赔率: 已标记为虚假数据
- 🔍 寻找中: betexplorer.com, oddsportal.com 等

## 未来真实赔率数据源接口要求
1. 数据源必须是真实的博彩公司开盘赔率
2. 必须包含主胜、平局、客胜三种赔率
3. 必须有时间戳和博彩公司信息
4. 必须能够回填到数据库对应比赛

## 实现方案选项
1. **Web爬虫**: 从 betexplorer.com 抓取历史赔率
2. **付费API**: 使用专业体育数据API
3. **数据合作**: 与博彩公司或数据提供商合作
4. **放弃赔率**: 专注于非赔率特征进行预测

## 紧急行动项
1. 立即停止使用模拟赔率进行任何回测
2. 承认当前所有ROI结果都是基于模拟数据
3. 寻找真实赔率数据源或调整策略
"""

    with open("docs/real_odds_interface_v4.0.md", "w", encoding="utf-8") as f:
        f.write(interface_doc)

    logger.info("✅ 未来真实赔率接口文档已创建")

def main():
    """主程序"""
    logger.info("🚀 V4.0 真实数据清洗开始")
    logger.info("🎯 目标: 承认现实，拒绝造假，为纯金数据铺路")

    try:
        # Step 1: 添加字段
        add_real_odds_flag()

        # Step 2: 标记所有模拟赔率
        flag_simulated_odds()

        # Step 3: 生成现实报告
        report = generate_reality_report()

        # Step 4: 创建未来接口
        create_future_real_odds_interface()

        logger.info("🎉 V4.0 数据清洗完成!")
        logger.info(f"🔴 已标记 {report['fake_odds_matches']} 场比赛为模拟赔率")
        logger.info("📋 现实情况报告已生成，请项目经理审阅")

    except Exception as e:
        logger.error(f"❌ V4.0 数据清洗失败: {e}")
        raise

if __name__ == "__main__":
    main()