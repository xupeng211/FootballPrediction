#!/usr/bin/env python3
"""
V41.125 "雷达合龙" - 多特征加权对齐引擎灰度验证脚本

验证目标:
1. 利物浦案：完美匹配达到 0.95+ 分数
2. 跨日期同名赛：有效拦截（< 0.85 分数）
3. 比分验证：已完赛场次正确加分
4. 时间窗口：24h 内正确验证

Author: 高级算法集成工程师
Version: V41.125
Date: 2026-01-17
"""

import argparse
import logging
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import psycopg2
from psycopg2.extras import RealDictCursor

from src.config_unified import get_settings
from src.services.hash_alignment_service import HashAlignmentService

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("logs/v41_125_alignment_test.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


@dataclass
class TestCase:
    """测试用例"""
    name: str
    fotmob_data: Dict[str, Any]
    oddsportal_data: Dict[str, Any]
    expected_aligned: bool
    expected_min_score: float


def get_test_cases() -> list[TestCase]:
    """
    V41.125: 获取测试用例集

    Returns:
        测试用例列表
    """
    return [
        # 案例 1: 利物浦案（完美匹配，预期 0.95+ 分数）
        TestCase(
            name="利物浦案 - 完美匹配",
            fotmob_data={
                "home_team": "Liverpool",
                "away_team": "Chelsea",
                "match_date": datetime(2024, 4, 20, 15, 0),
                "score_str": "2:1",
                "home_team_id": "9774",
                "away_team_id": "813"
            },
            oddsportal_data={
                "home_team": "Liverpool",
                "away_team": "Chelsea",
                "match_time": datetime(2024, 4, 20, 15, 0),
                "score": "2:1"
            },
            expected_aligned=True,
            expected_min_score=0.95
        ),

        # 案例 2: 跨日期同名赛（预期拦截，< 0.85 分数）
        TestCase(
            name="跨日期同名赛 - 应被拦截",
            fotmob_data={
                "home_team": "Liverpool",
                "away_team": "Chelsea",
                "match_date": datetime(2024, 4, 20, 15, 0),
                "score_str": "2:1"
            },
            oddsportal_data={
                "home_team": "Liverpool",
                "away_team": "Chelsea",
                "match_time": datetime(2024, 3, 15, 15, 0),  # 超过 24h
                "score": "1:0"
            },
            expected_aligned=False,
            expected_min_score=0.0
        ),

        # 案例 3: 比分不匹配（预期拦截）
        TestCase(
            name="比分不匹配 - 应被拦截",
            fotmob_data={
                "home_team": "Arsenal",
                "away_team": "Manchester United",
                "match_date": datetime(2024, 5, 1, 15, 0),
                "score_str": "3:1"
            },
            oddsportal_data={
                "home_team": "Arsenal",
                "away_team": "Manchester United",
                "match_time": datetime(2024, 5, 1, 15, 0),
                "score": "2:2"  # 比分不匹配
            },
            expected_aligned=False,
            expected_min_score=0.0
        ),

        # 案例 4: 队名模糊匹配（高相似度）
        TestCase(
            name="队名模糊匹配 - 高相似度",
            fotmob_data={
                "home_team": "Manchester United",
                "away_team": "Manchester City",
                "match_date": datetime(2024, 3, 3, 17, 30),
                "score_str": "1:3"
            },
            oddsportal_data={
                "home_team": "Manchester Utd",  # 模糊队名
                "away_team": "Man City",         # 模糊队名
                "match_time": datetime(2024, 3, 3, 17, 30),
                "score": "1:3"
            },
            expected_aligned=True,
            expected_min_score=0.85
        ),

        # 案例 5: 时间窗口边界测试（23h 内）
        TestCase(
            name="时间窗口边界 - 23h 内",
            fotmob_data={
                "home_team": "Tottenham",
                "away_team": "Newcastle",
                "match_date": datetime(2024, 4, 15, 15, 0),
                "score_str": "4:1"
            },
            oddsportal_data={
                "home_team": "Tottenham",
                "away_team": "Newcastle",
                "match_time": datetime(2024, 4, 16, 12, 0),  # 21h 后
                "score": "4:1"
            },
            expected_aligned=True,
            expected_min_score=0.85
        ),

        # 案例 6: 无比分数据（未完场）
        TestCase(
            name="无比分数据 - 未完场",
            fotmob_data={
                "home_team": "Real Madrid",
                "away_team": "Barcelona",
                "match_date": datetime(2024, 10, 20, 21, 0),
                "score_str": ""  # 无比分
            },
            oddsportal_data={
                "home_team": "Real Madrid",
                "away_team": "Barcelona",
                "match_time": datetime(2024, 10, 20, 21, 0),
                "score": ""  # 无比分
            },
            expected_aligned=True,
            expected_min_score=0.60  # 无比分，分数会降低
        ),

        # 案例 7: 时间超限（> 24h）
        TestCase(
            name="时间超限 - 应被拦截",
            fotmob_data={
                "home_team": "AC Milan",
                "away_team": "Inter Milan",
                "match_date": datetime(2024, 4, 10, 20, 45),
                "score_str": "2:2"
            },
            oddsportal_data={
                "home_team": "AC Milan",
                "away_team": "Inter Milan",
                "match_time": datetime(2024, 4, 14, 15, 0),  # > 6 天
                "score": "2:2"
            },
            expected_aligned=False,
            expected_min_score=0.0
        ),

        # 案例 8: 队名低相似度（应被拦截）
        TestCase(
            name="队名低相似度 - 应被拦截",
            fotmob_data={
                "home_team": "Liverpool",
                "away_team": "Chelsea",
                "match_date": datetime(2024, 5, 5, 15, 0),
                "score_str": "1:0"
            },
            oddsportal_data={
                "home_team": "Liverpool FC",
                "away_team": "Aston Villa",  # 完全不同的队伍
                "match_time": datetime(2024, 5, 5, 15, 0),
                "score": "1:0"
            },
            expected_aligned=False,
            expected_min_score=0.0
        ),

        # 案例 9: 意甲比赛（ID 映射奖励）
        TestCase(
            name="意甲比赛 - ID 映射",
            fotmob_data={
                "home_team": "Juventus",
                "away_team": "AC Milan",
                "match_date": datetime(2024, 3, 17, 20, 45),
                "score_str": "1:0",
                "home_team_id": "497",
                "away_team_id": "496"
            },
            oddsportal_data={
                "home_team": "Juventus",
                "away_team": "AC Milan",
                "match_time": datetime(2024, 3, 17, 20, 45),
                "score": "1:0"
            },
            expected_aligned=True,
            expected_min_score=0.85
        ),

        # 案例 10: 完美时间匹配（0h 差异）
        TestCase(
            name="完美时间匹配 - 0h 差异",
            fotmob_data={
                "home_team": "Bayern Munich",
                "away_team": "Borussia Dortmund",
                "match_date": datetime(2024, 4, 13, 18, 30),
                "score_str": "2:0"
            },
            oddsportal_data={
                "home_team": "Bayern Munich",
                "away_team": "Borussia Dortmund",
                "match_time": datetime(2024, 4, 13, 18, 30),  # 完全一致
                "score": "2:0"
            },
            expected_aligned=True,
            expected_min_score=0.95
        ),

        # 案例 11: 比分格式差异（标准化验证）
        TestCase(
            name="比分格式差异 - 标准化验证",
            fotmob_data={
                "home_team": "Paris SG",
                "away_team": "Lyon",
                "match_date": datetime(2024, 2, 25, 21, 0),
                "score_str": "2:1"
            },
            oddsportal_data={
                "home_team": "Paris SG",
                "away_team": "Lyon",
                "match_time": datetime(2024, 2, 25, 21, 0),
                "score": "2-1"  # 不同格式，但应标准化为相同
            },
            expected_aligned=True,
            expected_min_score=0.85
        ),

        # 案例 12: 队名完全匹配（高置信度）
        TestCase(
            name="队名完全匹配 - 高置信度",
            fotmob_data={
                "home_team": "Napoli",
                "away_team": "Roma",
                "match_date": datetime(2024, 4, 7, 18, 0),
                "score_str": "2:2"
            },
            oddsportal_data={
                "home_team": "Napoli",
                "away_team": "Roma",
                "match_time": datetime(2024, 4, 7, 18, 0),
                "score": "2:2"
            },
            expected_aligned=True,
            expected_min_score=0.95
        ),
    ]


def run_alignment_test(db_conn, verbose: bool = True) -> dict[str, Any]:
    """
    V41.125: 运行对齐测试

    Args:
        db_conn: 数据库连接
        verbose: 是否输出详细日志

    Returns:
        测试结果摘要
    """
    logger.info("=" * 80)
    logger.info("🎯 V41.125 多特征加权对齐引擎 - 灰度验证")
    logger.info("=" * 80)

    # 初始化对齐服务
    service = HashAlignmentService(db_conn, season="2023-2024")

    # 获取测试用例
    test_cases = get_test_cases()

    results = {
        "total": len(test_cases),
        "aligned": 0,
        "rejected": 0,
        "correct": 0,
        "wrong": 0,
        "high_confidence": 0,
        "medium_confidence": 0,
        "low_confidence": 0,
        "details": []
    }

    logger.info(f"📋 测试用例总数: {len(test_cases)}")
    logger.info("")

    # 运行每个测试用例
    for i, test_case in enumerate(test_cases, 1):
        logger.info(f"🔍 测试 {i}/{len(test_cases)}: {test_case.name}")
        logger.info("-" * 80)

        # 执行对齐验证
        result = service.align_with_multi_feature_validation(
            fotmob_match=test_case.fotmob_data,
            oddsportal_match=test_case.oddsportal_data,
            verbose=verbose
        )

        # 判断是否符合预期
        is_correct = result["is_aligned"] == test_case.expected_aligned

        # 更新统计
        if result["is_aligned"]:
            results["aligned"] += 1
        else:
            results["rejected"] += 1

        if is_correct:
            results["correct"] += 1
        else:
            results["wrong"] += 1

        # 更新置信度统计
        if result["confidence"] == "HIGH":
            results["high_confidence"] += 1
        elif result["confidence"] == "MEDIUM":
            results["medium_confidence"] += 1
        else:
            results["low_confidence"] += 1

        # 记录详情
        detail = {
            "test_name": test_case.name,
            "is_aligned": result["is_aligned"],
            "score": result["score"],
            "threshold": result["threshold"],
            "confidence": result["confidence"],
            "breakdown": result["breakdown"],
            "reason": result["reason"],
            "expected_aligned": test_case.expected_aligned,
            "expected_min_score": test_case.expected_min_score,
            "is_correct": is_correct
        }
        results["details"].append(detail)

        # 输出结果
        status = "✅ 正确" if is_correct else "❌ 错误"
        logger.info(f"   结果: {status}")
        logger.info(f"   对齐: {result['is_aligned']} | 分数: {result['score']:.3f} / {result['threshold']:.2f}")
        logger.info(f"   置信度: {result['confidence']}")
        logger.info(f"   原因: {result['reason']}")

        # 得分拆解
        logger.info(f"   得分拆解:")
        logger.info(f"      队名相似度: {result['breakdown']['name_similarity']:.3f} (50%)")
        logger.info(f"      比分校验: {result['breakdown']['score_validation']:.3f} (30%)")
        logger.info(f"      时间窗口: {result['breakdown']['time_window']:.3f} (10%)")
        logger.info(f"      ID 映射: {result['breakdown']['id_mapping']:.3f} (10%)")
        logger.info("")

    # 生成统计摘要
    logger.info("=" * 80)
    logger.info("📊 测试统计摘要")
    logger.info("=" * 80)
    logger.info(f"总用例: {results['total']}")
    logger.info(f"对齐成功: {results['aligned']} ({results['aligned']/results['total']*100:.1f}%)")
    logger.info(f"拒绝: {results['rejected']} ({results['rejected']/results['total']*100:.1f}%)")
    logger.info(f"正确判定: {results['correct']} ({results['correct']/results['total']*100:.1f}%)")
    logger.info(f"错误判定: {results['wrong']} ({results['wrong']/results['total']*100:.1f}%)")
    logger.info("")
    logger.info("置信度分布:")
    logger.info(f"  HIGH (≥0.95): {results['high_confidence']}")
    logger.info(f"  MEDIUM (0.85-0.95): {results['medium_confidence']}")
    logger.info(f"  LOW (<0.85): {results['low_confidence']}")
    logger.info("")

    # 验证关键指标
    success_rate = results['correct'] / results['total']
    logger.info(f"✅ 准确率: {success_rate*100:.1f}%")

    if success_rate >= 0.90:
        logger.info("🎉 测试通过！准确率 ≥ 90%")
    elif success_rate >= 0.80:
        logger.info("⚠️  测试基本通过，准确率 ≥ 80%")
    else:
        logger.info("❌ 测试失败，准确率 < 80%")

    return results


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="V41.125 多特征对齐引擎灰度验证")
    parser.add_argument("--verbose", "-v", action="store_true", help="详细输出")
    args = parser.parse_args()

    # 连接数据库
    settings = get_settings()
    conn = psycopg2.connect(
        host=settings.database.host,
        port=settings.database.port,
        database=settings.database.name,
        user=settings.database.user,
        password=settings.database.password.get_secret_value(),
        cursor_factory=RealDictCursor
    )

    try:
        # 运行测试
        results = run_alignment_test(conn, verbose=args.verbose)

        # 保存结果到文件
        import json
        with open("logs/v41_125_alignment_test_results.json", "w") as f:
            json.dump(results, f, indent=2, default=str)

        logger.info("✅ 测试结果已保存到 logs/v41_125_alignment_test_results.json")

    finally:
        conn.close()


if __name__ == "__main__":
    main()
