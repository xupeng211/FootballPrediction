"""
质量检查任务

负责数据质量检查和生成质量报告。
"""

import asyncio
import logging
from datetime import datetime

from src.database.connection import get_async_session
from src.data.quality.data_quality_monitor import DataQualityMonitor
from ...celery_config import app
from ..base.base_task import BaseDataTask

logger = logging.getLogger(__name__)


async def _check_data_integrity(session, monitor):
    """检查数据完整性"""
    integrity_results = {}

    # 检查比赛数据完整性
    integrity_results["matches"] = await monitor.check_data_integrity(
        session=session,
        table_name="matches",
        checks=["not_null", "unique", "referential"]
    )

    # 检查赔率数据完整性
    integrity_results["odds"] = await monitor.check_data_integrity(
        session=session,
        table_name="odds",
        checks=["not_null", "referential"]
    )

    return integrity_results


async def _check_data_consistency(session, monitor):
    """检查数据一致性"""
    consistency_results = {}

    # 检查比赛与赔率数据的一致性
    consistency_results["match_odds"] = await monitor.check_cross_table_consistency(
        session=session,
        table1="matches",
        table2="odds",
        join_key="match_id",
        checks=["match_consistency"]
    )

    # 检查比赛与比分数据的一致性
    consistency_results["match_scores"] = await monitor.check_cross_table_consistency(
        session=session,
        table1="matches",
        table2="raw_scores_data",
        join_key="match_id",
        checks=["match_consistency"]
    )

    return consistency_results


async def _check_data_freshness(session, monitor):
    """检查数据新鲜度"""
    freshness_results = {}

    # 检查各种数据的最新更新时间
    tables_to_check = ["matches", "odds", "raw_scores_data"]

    for table in tables_to_check:
        freshness_results[table] = await monitor.check_data_freshness(
            session=session,
            table_name=table,
            max_age_hours=24
        )

    return freshness_results


async def _generate_quality_report(session, monitor):
    """生成质量报告"""
    # 执行所有检查
    integrity_results = await _check_data_integrity(session, monitor)
    consistency_results = await _check_data_consistency(session, monitor)
    freshness_results = await _check_data_freshness(session, monitor)

    # 汇总结果
    quality_report = {
        "timestamp": datetime.now().isoformat(),
        "integrity": integrity_results,
        "consistency": consistency_results,
        "freshness": freshness_results
    }

    # 计算总体质量分数
    total_checks = 0
    passed_checks = 0

    for category_results in [integrity_results, consistency_results, freshness_results]:
        for table_result in category_results.values():
            if isinstance(table_result, dict):
                total_checks += len(table_result.get("checks", {}))
                passed_checks += sum(
                    1 for check_result in table_result.get("checks", {}).values()
                    if check_result.get("status") == "pass"
                )

    quality_score = (passed_checks / total_checks * 100) if total_checks > 0 else 0
    quality_report["overall_score"] = round(quality_score, 2)
    quality_report["summary"] = {
        "total_checks": total_checks,
        "passed_checks": passed_checks,
        "failed_checks": total_checks - passed_checks
    }

    return quality_report


@app.task(base=BaseDataTask)
def run_quality_checks():
    """
    运行数据质量检查任务
    """
    logger.info("开始执行数据质量检查任务")

    try:
        async def _quality_check_task():
            monitor = DataQualityMonitor()

            async with get_async_session() as session:
                # 生成质量报告
                quality_report = await _generate_quality_report(session, monitor)

                # 保存质量报告
                await monitor.save_quality_report(session, quality_report)

                # 检查是否需要发送告警
                if quality_report["overall_score"] < 80:
                    await monitor.send_quality_alert(quality_report)

                return quality_report

        # 运行异步质量检查
        report = asyncio.run(_quality_check_task())

        logger.info(
            f"数据质量检查完成: 总体质量分数 {report['overall_score']}%, "
            f"通过 {report['summary']['passed_checks']}/{report['summary']['total_checks']} 项检查"
        )

        return {
            "status": "success",
            "quality_score": report["overall_score"],
            "summary": report["summary"],
            "execution_time": datetime.now().isoformat(),
        }

    except Exception as exc:
        logger.error(f"数据质量检查任务失败: {str(exc)}")
        raise