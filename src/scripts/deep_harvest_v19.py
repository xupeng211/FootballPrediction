#!/usr/bin/env python3
"""
深度收割计划 - V19.1 数据完整化

目标：对数据库中已有的 761 场比赛进行"全量数据重刷"
使用 FotMobCoreCollector V11.0 重新采集完整的 FotMob API 数据，
替换当前数据库中的简化格式数据。

执行方式：
    python src/scripts/deep_harvest_v19.py

Author: V19.1 Data Recovery Team
Date: 2025-12-23
"""

import sys
import time
import logging
import psycopg2
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Tuple

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.api.collectors.fotmob_core import FotMobCoreCollector, LEAGUE_ID_TO_TIER

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 数据库连接配置
DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'football_db',
    'user': 'football_user',
    'password': 'football_pass'
}

# 深度收割配置
REQUEST_INTERVAL = 1.5  # 请求间隔（秒），防止被封禁
LEAGUE_ID = 47  # 英超 league_id
BATCH_SIZE = 50  # 每批次处理数量


def get_database_connection():
    """获取数据库连接"""
    return psycopg2.connect(**DB_CONFIG)


def get_all_match_ids() -> List[Tuple[int, int]]:
    """
    获取数据库中所有比赛 ID

    Returns:
        List[Tuple[int, int]]: (内部ID, FotMob外部ID) 列表
    """
    logger.info("📋 正在获取数据库中所有比赛 ID...")

    try:
        conn = get_database_connection()
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, external_id, home_team, away_team, match_time
                FROM matches
                WHERE status = 'Finished'
                ORDER BY match_time ASC
            """)

            matches = cur.fetchall()
            # 返回 (内部ID, 外部ID) 元组列表
            match_ids = [(row[0], row[1]) for row in matches]

            logger.info(f"✅ 找到 {len(match_ids)} 场比赛")

            # 打印时间范围
            if matches:
                first_match = matches[0]
                last_match = matches[-1]
                logger.info(f"   时间范围: {first_match[4]} 到 {last_match[4]}")
                logger.info(f"   外部ID示例: {first_match[1]}, {last_match[1]}")

            return match_ids

    except Exception as e:
        logger.error(f"❌ 获取比赛 ID 失败: {e}")
        return []
    finally:
        if 'conn' in locals():
            conn.close()


def get_current_data_quality(sample_size: int = 10) -> Dict[str, any]:
    """
    检查当前数据质量

    Args:
        sample_size: 抽样检查数量

    Returns:
        Dict: 数据质量报告
    """
    logger.info(f"🔍 检查当前数据质量（抽样 {sample_size} 场）...")

    try:
        conn = get_database_connection()
        with conn.cursor() as cur:
            # 获取抽样比赛
            cur.execute("""
                SELECT id, home_team, away_team, l2_raw_json
                FROM matches
                WHERE status = 'Finished'
                ORDER BY RANDOM()
                LIMIT %s
            """, (sample_size,))

            sampled_matches = cur.fetchall()

            simple_format_count = 0
            full_format_count = 0
            empty_count = 0

            for match_id, home_team, away_team, raw_json in sampled_matches:
                if raw_json is None:
                    empty_count += 1
                    continue

                # 检查数据格式
                if isinstance(raw_json, str):
                    try:
                        raw_json = eval(raw_json)
                    except:
                        pass

                # 简化格式：有 home_stats/away_stats 字段
                if 'home_stats' in raw_json and 'away_stats' in raw_json:
                    simple_format_count += 1
                # 完整格式：有 l2_json 嵌套结构
                elif 'l2_json' in raw_json or 'content' in raw_json:
                    full_format_count += 1

            return {
                'total_sampled': len(sampled_matches),
                'simple_format': simple_format_count,
                'full_format': full_format_count,
                'empty': empty_count,
                'simple_format_ratio': simple_format_count / len(sampled_matches) if sampled_matches else 0
            }

    except Exception as e:
        logger.error(f"❌ 检查数据质量失败: {e}")
        return {}
    finally:
        if 'conn' in locals():
            conn.close()


def check_match_data_quality(internal_id: int) -> Dict[str, any]:
    """
    检查单场比赛数据质量

    Args:
        internal_id: 数据库内部 ID

    Returns:
        Dict: 数据质量信息
    """
    try:
        conn = get_database_connection()
        with conn.cursor() as cur:
            cur.execute("""
                SELECT l2_raw_json
                FROM matches
                WHERE id = %s
            """, (internal_id,))

            result = cur.fetchone()
            if not result or result[0] is None:
                return {'has_data': False, 'format': 'empty'}

            raw_json = result[0]
            if isinstance(raw_json, str):
                try:
                    raw_json = eval(raw_json)
                except:
                    raw_json = {}

            # 检查格式
            if 'home_stats' in raw_json and 'away_stats' in raw_json:
                return {'has_data': True, 'format': 'simple'}
            elif 'l2_json' in raw_json or 'content' in raw_json:
                return {'has_data': True, 'format': 'full'}
            else:
                return {'has_data': True, 'format': 'unknown'}

    except Exception as e:
        logger.error(f"❌ 检查比赛 {internal_id} 数据质量失败: {e}")
        return {'has_data': False, 'format': 'error'}
    finally:
        if 'conn' in locals():
            conn.close()


def deep_harvest_batch(
    collector: FotMobCoreCollector,
    match_ids: List[Tuple[int, int]],
    start_index: int = 0
) -> Tuple[int, int, int]:
    """
    批量深度收割比赛

    Args:
        collector: FotMobCoreCollector 实例
        match_ids: (内部ID, 外部ID) 元组列表
        start_index: 起始索引（用于断点续传）

    Returns:
        Tuple[int, int, int]: (成功数量, 失败数量, 跳过数量)
    """
    success_count = 0
    failure_count = 0
    skipped_count = 0

    total_matches = len(match_ids)

    logger.info(f"🚀 开始批量深度收割（共 {total_matches} 场）...")

    for i, (internal_id, external_id) in enumerate(match_ids):
        current_index = start_index + i
        progress_pct = (current_index / total_matches) * 100

        logger.info(f"")
        logger.info(f"📊 进度: [{current_index}/{total_matches}] ({progress_pct:.1f}%)")
        logger.info(f"   内部ID: {internal_id}, 外部ID: {external_id}")

        # 检查当前数据质量
        quality = check_match_data_quality(internal_id)
        logger.info(f"   当前格式: {quality.get('format', 'unknown')}")

        # 执行深度收割 - 使用外部ID调用 FotMob API
        success = collector.harvest_match_with_league(external_id, league_id=LEAGUE_ID)

        if success:
            success_count += 1
        else:
            failure_count += 1

        # 请求间隔，防止被封禁
        if i < len(match_ids) - 1:  # 最后一个不等待
            logger.debug(f"⏱️  等待 {REQUEST_INTERVAL} 秒后继续...")
            time.sleep(REQUEST_INTERVAL)

    logger.info(f"")
    logger.info(f"📊 批次收割完成:")
    logger.info(f"   成功: {success_count}")
    logger.info(f"   失败: {failure_count}")
    logger.info(f"   跳过: {skipped_count}")

    return success_count, failure_count, skipped_count


def verify_feature_completeness(sample_size: int = 10) -> bool:
    """
    验证特征完整性

    Args:
        sample_size: 抽样验证数量

    Returns:
        bool: 特征是否完整
    """
    logger.info(f"")
    logger.info("=" * 60)
    logger.info("特征完整性校验")
    logger.info("=" * 60)

    try:
        conn = get_database_connection()
        with conn.cursor() as cur:
            # 随机抽取比赛
            cur.execute("""
                SELECT id, home_team, away_team, l2_raw_json
                FROM matches
                WHERE status = 'Finished'
                ORDER BY RANDOM()
                LIMIT %s
            """, (sample_size,))

            sampled_matches = cur.fetchall()

            logger.info(f"📊 随机抽样 {sample_size} 场比赛进行验证...")

            all_valid = True

            for match_id, home_team, away_team, raw_json in sampled_matches:
                if raw_json is None:
                    logger.warning(f"❌ [{match_id}] {home_team} vs {away_team}: 数据为空")
                    all_valid = False
                    continue

                # 解析 JSON
                if isinstance(raw_json, str):
                    try:
                        raw_json = eval(raw_json)
                    except:
                        logger.warning(f"❌ [{match_id}] {home_team} vs {away_team}: JSON 解析失败")
                        all_valid = False
                        continue

                # 检查是否有完整格式
                if 'l2_json' in raw_json:
                    l2_data = raw_json['l2_json']
                    has_content = 'content' in l2_data
                    has_stats = 'stats' in l2_data.get('content', {})
                    logger.info(f"✅ [{match_id}] {home_team} vs {away_team}: 完整格式 (content={has_content}, stats={has_stats})")
                elif 'content' in raw_json:
                    has_content = True
                    has_stats = 'stats' in raw_json.get('content', {})
                    logger.info(f"✅ [{match_id}] {home_team} vs {away_team}: 完整格式 (content={has_content}, stats={has_stats})")
                else:
                    logger.warning(f"⚠️  [{match_id}] {home_team} vs {away_team}: 仍是简化格式")
                    all_valid = False

            return all_valid

    except Exception as e:
        logger.error(f"❌ 特征完整性校验失败: {e}")
        return False
    finally:
        if 'conn' in locals():
            conn.close()


def generate_final_report(
    total_matches: int,
    success_count: int,
    failure_count: int,
    pre_quality: Dict,
    post_quality: Dict
):
    """
    生成最终报告

    Args:
        total_matches: 总比赛数
        success_count: 成功数量
        failure_count: 失败数量
        pre_quality: 收割前数据质量
        post_quality: 收割后数据质量
    """
    logger.info(f"")
    logger.info("=" * 60)
    logger.info("深度收割计划 - 最终报告")
    logger.info("=" * 60)
    logger.info(f"")
    logger.info(f"📊 总体统计:")
    logger.info(f"   目标比赛数: {total_matches}")
    logger.info(f"   成功更新: {success_count}")
    logger.info(f"   更新失败: {failure_count}")
    logger.info(f"   成功率: {success_count / total_matches * 100:.1f}%")
    logger.info(f"")
    logger.info(f"📈 数据质量对比:")
    logger.info(f"   收割前:")
    logger.info(f"     简化格式占比: {pre_quality.get('simple_format_ratio', 0) * 100:.1f}%")
    logger.info(f"     完整格式: {pre_quality.get('full_format', 0)} 场")
    logger.info(f"   收割后:")
    logger.info(f"     简化格式占比: {post_quality.get('simple_format_ratio', 0) * 100:.1f}%")
    logger.info(f"     完整格式: {post_quality.get('full_format', 0)} 场")
    logger.info(f"")
    logger.info(f"✅ 深度收割计划完成！")


def main():
    """主函数"""
    logger.info("")
    logger.info("=" * 60)
    logger.info("深度收割计划 - V19.1 数据完整化")
    logger.info("=" * 60)
    logger.info("")

    # 1. 获取所有比赛 ID
    match_ids = get_all_match_ids()

    if not match_ids:
        logger.error("❌ 没有找到比赛数据，退出")
        return 1

    # 2. 检查收割前数据质量
    pre_quality = get_current_data_quality(sample_size=20)

    logger.info(f"")
    logger.info(f"📊 收割前数据质量:")
    logger.info(f"   简化格式: {pre_quality.get('simple_format', 0)}/{pre_quality.get('total_sampled', 0)} ({pre_quality.get('simple_format_ratio', 0) * 100:.1f}%)")
    logger.info(f"   完整格式: {pre_quality.get('full_format', 0)}")
    logger.info(f"   空/未知: {pre_quality.get('empty', 0)}")

    # 3. 初始化采集器
    collector = FotMobCoreCollector()

    # 4. 执行深度收割
    success_count, failure_count, skipped_count = deep_harvest_batch(
        collector,
        match_ids
    )

    # 5. 检查收割后数据质量
    post_quality = get_current_data_quality(sample_size=20)

    logger.info(f"")
    logger.info(f"📊 收割后数据质量:")
    logger.info(f"   简化格式: {post_quality.get('simple_format', 0)}/{post_quality.get('total_sampled', 0)} ({post_quality.get('simple_format_ratio', 0) * 100:.1f}%)")
    logger.info(f"   完整格式: {post_quality.get('full_format', 0)}")
    logger.info(f"   空/未知: {post_quality.get('empty', 0)}")

    # 6. 特征完整性校验
    is_valid = verify_feature_completeness(sample_size=10)

    # 7. 生成最终报告
    generate_final_report(
        total_matches=len(match_ids),
        success_count=success_count,
        failure_count=failure_count,
        pre_quality=pre_quality,
        post_quality=post_quality
    )

    logger.info(f"")
    if is_valid:
        logger.info(f"✅ 特征完整性校验通过！")
        logger.info(f"   可以继续执行 V19.2 重新训练")
    else:
        logger.warning(f"⚠️  特征完整性校验未完全通过")
        logger.warning(f"   建议检查失败的比赛并重新采集")

    return 0 if success_count > 0 else 1


if __name__ == "__main__":
    sys.exit(main())
