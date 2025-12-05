#!/usr/bin/env python3
"""
L2 详情采集任务 - API版本
L2 Details Collection Job - API Version

使用新的FotMob API进行高性能详情数据采集
"""

import asyncio
import logging
import os
import sys
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from prefect import flow, task, get_run_logger
from prefect.client.orchestration import PrefectClient

from src.collectors.fotmob_api_collector import FotMobAPICollector
from src.services.l2_data_service import L2DataService

logger = logging.getLogger(__name__)


@task(
    name="获取待处理比赛ID",
    retries=3,
    retry_delay_seconds=30,
    cache_key_fn=lambda: "pending_matches",
    cache_expiration=timedelta(minutes=30)
)
async def get_pending_matches(limit: int = 10000) -> list[str]:
    """获取待处理的比赛ID列表"""
    log = get_run_logger()
    log.info(f"🔍 获取待处理比赛列表，限制: {limit}")

    service = L2DataService()
    matches = await service.get_pending_matches(limit)

    log.info(f"📊 找到 {len(matches)} 场待处理比赛")
    return matches


@task(
    name="API数据采集",
    retries=2,
    retry_delay_seconds=60
)
async def collect_match_details_batch(
    fotmob_ids: list[str],
    batch_size: int = 50,
    max_concurrent: int = 10
) -> dict[str, Any]:
    """批量采集比赛详情数据"""
    log = get_run_logger()
    log.info(f"🚀 开始批量采集 {len(fotmob_ids)} 场比赛详情")

    collector = FotMobAPICollector(
        max_concurrent=max_concurrent,
        timeout=30,
        max_retries=3,
        base_delay=1.0,
        enable_proxy=True,
        enable_jitter=True
    )

    try:
        await collector.initialize()

        # 分批处理
        all_results = []
        total_batches = (len(fotmob_ids) + batch_size - 1) // batch_size

        for i in range(0, len(fotmob_ids), batch_size):
            batch_ids = fotmob_ids[i:i + batch_size]
            batch_num = i // batch_size + 1

            log.info(f"📦 处理批次 {batch_num}/{total_batches} ({len(batch_ids)} 场比赛)")

            batch_results = await collector.collect_batch(batch_ids)
            all_results.extend(batch_results)

            # 批次间暂停
            if batch_num < total_batches:
                await asyncio.sleep(2)

        # 获取采集统计
        stats = collector.get_stats()
        log.info(f"📊 采集完成: 成功 {stats['matches_collected']}/{len(fotmob_ids)} 场")
        log.info(f"📈 请求统计: 成功 {stats['successful_requests']}, 失败 {stats['failed_requests']}")

        return {
            "results": all_results,
            "stats": stats,
            "total_requested": len(fotmob_ids),
            "success_count": len(all_results),
            "success_rate": len(all_results) / len(fotmob_ids) * 100 if fotmob_ids else 0
        }

    finally:
        await collector.close()


@task(
    name="数据库写入",
    retries=3,
    retry_delay_seconds=30
)
async def save_match_details_to_db(match_details_data: dict[str, Any]) -> dict[str, Any]:
    """将采集的详情数据保存到数据库"""
    log = get_run_logger()

    service = L2DataService()
    results = await service.save_batch_match_details(match_details_data["results"])

    log.info(f"💾 数据库写入完成: {results}")

    return {
        "db_results": results,
        "collection_stats": match_details_data["stats"],
        "total_success": results["success"],
        "total_failed": results["failed"]
    }


@task(
    name="更新数据状态",
    retries=2,
    retry_delay_seconds=10
)
async def update_data_completeness(
    fotmob_ids: list[str],
    success_count: int,
    failed_count: int
) -> dict[str, Any]:
    """更新数据完整度状态"""
    log = get_run_logger()

    service = L2DataService()

    # 更新成功的记录为complete
    completed_ids = fotmob_ids[:success_count]  # 简化处理，实际应该基于具体成功的ID
    updated_complete = await service.update_data_completeness_status(
        completed_ids, "complete"
    )

    # 更新失败的记录为failed
    if failed_count > 0:
        failed_ids = fotmob_ids[success_count:]
        updated_failed = await service.update_data_completeness_status(
            failed_ids, "failed"
        )
    else:
        updated_failed = 0

    log.info(f"✅ 状态更新完成: complete={updated_complete}, failed={updated_failed}")

    return {
        "updated_complete": updated_complete,
        "updated_failed": updated_failed,
        "total_processed": len(fotmob_ids)
    }


@flow(
    name="L2 API详情采集流程",
    description="使用FotMob API进行L2详情数据采集",
    log_prints=True
)
async def run_l2_api_details(
    limit: int = 10000,
    batch_size: int = 50,
    max_concurrent: int = 10,
    dry_run: bool = False
) -> dict[str, Any]:
    """
    L2详情数据采集主流程

    Args:
        limit: 最大处理比赛数量
        batch_size: 批处理大小
        max_concurrent: 最大并发数
        dry_run: 是否为试运行（只采集不写入数据库）

    Returns:
        采集结果统计信息
    """
    log = get_run_logger()
    start_time = datetime.now()

    log.info("🎯 开始L2 API详情采集流程")
    log.info(f"📋 参数: limit={limit}, batch_size={batch_size}, max_concurrent={max_concurrent}")
    log.info(f"🔧 模式: {'试运行' if dry_run else '正式运行'}")

    try:
        # 1. 获取待处理的比赛ID
        fotmob_ids = await get_pending_matches(limit)

        if not fotmob_ids:
            log.info("📝 没有待处理的比赛，流程结束")
            return {
                "status": "completed",
                "message": "没有待处理的比赛",
                "processed_count": 0,
                "duration": (datetime.now() - start_time).total_seconds()
            }

        # 2. 批量采集详情数据
        collection_result = await collect_match_details_batch(
            fotmob_ids, batch_size, max_concurrent
        )

        # 3. 如果不是试运行，保存到数据库
        if not dry_run and collection_result["results"]:
            save_result = await save_match_details_to_db(collection_result)

            # 4. 更新数据完整度状态
            await update_data_completeness(
                fotmob_ids[:collection_result["success_count"]],  # 简化处理
                save_result["total_success"],
                save_result["total_failed"]
            )
        else:
            log.info("🧪 试运行模式，跳过数据库写入")
            save_result = {"db_results": {"success": collection_result["success_count"]}}

        # 5. 生成最终报告
        duration = (datetime.now() - start_time).total_seconds()

        final_report = {
            "status": "completed",
            "start_time": start_time.isoformat(),
            "duration_seconds": duration,
            "total_requested": len(fotmob_ids),
            "collection_success": collection_result["success_count"],
            "collection_success_rate": collection_result["success_rate"],
            "db_success": save_result["db_results"].get("success", 0),
            "db_failed": save_result["db_results"].get("failed", 0),
            "collection_stats": collection_result["stats"],
            "dry_run": dry_run
        }

        log.info("🎉 L2详情采集流程完成!")
        log.info(f"📊 采集统计: {collection_result['success_count']}/{len(fotmob_ids)} ({collection_result['success_rate']:.1f}%)")
        log.info(f"⏱️ 总耗时: {duration:.1f}秒")

        return final_report

    except Exception as e:
        log.error(f"❌ L2详情采集流程失败: {e}")
        duration = (datetime.now() - start_time).total_seconds()

        return {
            "status": "failed",
            "error": str(e),
            "duration_seconds": duration,
            "start_time": start_time.isoformat()
        }


@flow(
    name="L2增量回填流程",
    description="对特定日期范围的失败比赛进行增量回填",
    log_prints=True
)
async def run_l2_incremental_backfill(
    days_back: int = 7,
    batch_size: int = 50,
    max_concurrent: int = 5
) -> dict[str, Any]:
    """
    L2增量回填流程

    Args:
        days_back: 回溯天数
        batch_size: 批处理大小
        max_concurrent: 最大并发数（回填时更保守）

    Returns:
        回填结果统计信息
    """
    log = get_run_logger()
    start_time = datetime.now()

    log.info("🔄 开始L2增量回填流程")
    log.info(f"📋 参数: days_back={days_back}, batch_size={batch_size}")

    try:
        # 获取失败的比赛
        service = L2DataService()

        # 这里应该实现获取失败比赛ID的逻辑
        # 暂时使用简化的方式获取所有partial状态的比赛
        failed_ids = await service.get_pending_matches(limit=5000)

        if not failed_ids:
            log.info("📝 没有需要回填的比赛，流程结束")
            return {
                "status": "completed",
                "message": "没有需要回填的比赛",
                "processed_count": 0
            }

        log.info(f"🔄 找到 {len(failed_ids)} 场需要回填的比赛")

        # 使用更保守的并发设置进行回填
        result = await run_l2_api_details(
            limit=len(failed_ids),
            batch_size=batch_size,
            max_concurrent=max_concurrent,
            dry_run=False
        )

        result["backfill_type"] = "incremental"
        result["days_back"] = days_back

        return result

    except Exception as e:
        log.error(f"❌ L2增量回填流程失败: {e}")
        return {
            "status": "failed",
            "error": str(e),
            "backfill_type": "incremental",
            "days_back": days_back
        }


# CLI入口点
if __name__ == "__main__":
    import asyncio
    import sys

    async def main():
        if len(sys.argv) < 2:
            print("用法:")
            print("  python src/jobs/run_l2_api_details.py full           # 完整采集")
            print("  python src/jobs/run_l2_api_details.py backfill       # 增量回填")
            print("  python src/jobs/run_l2_api_details.py dry-run        # 试运行")
            print("")
            print("环境变量:")
            print("  LIMIT=10000         # 处理数量限制")
            print("  BATCH_SIZE=50       # 批处理大小")
            print("  MAX_CONCURRENT=10   # 最大并发数")
            sys.exit(1)

        command = sys.argv[1]

        # 从环境变量获取参数
        limit = int(os.getenv("LIMIT", "10000"))
        batch_size = int(os.getenv("BATCH_SIZE", "50"))
        max_concurrent = int(os.getenv("MAX_CONCURRENT", "10"))

        if command == "full":
            result = await run_l2_api_details(
                limit=limit,
                batch_size=batch_size,
                max_concurrent=max_concurrent,
                dry_run=False
            )
        elif command == "backfill":
            result = await run_l2_incremental_backfill(
                days_back=7,
                batch_size=batch_size,
                max_concurrent=max_concurrent // 2  # 回填时使用更保守的并发
            )
        elif command == "dry-run":
            result = await run_l2_api_details(
                limit=limit,
                batch_size=batch_size,
                max_concurrent=max_concurrent,
                dry_run=True
            )
        else:
            print(f"未知命令: {command}")
            sys.exit(1)

        # 输出结果
        print("\n" + "="*60)
        print("🎯 L2 API详情采集结果")
        print("="*60)
        print(f"状态: {result.get('status', 'unknown')}")
        print(f"总耗时: {result.get('duration_seconds', 0):.1f}秒")

        if result.get("status") == "completed":
            print(f"请求总数: {result.get('total_requested', 0)}")
            print(f"采集成功: {result.get('collection_success', 0)} ({result.get('collection_success_rate', 0):.1f}%)")
            print(f"写入成功: {result.get('db_success', 0)}")
            print(f"写入失败: {result.get('db_failed', 0)}")

            # 显示采集统计
            if "collection_stats" in result:
                stats = result["collection_stats"]
                print("\n📊 采集统计:")
                print(f"  API请求: {stats.get('requests_made', 0)}")
                print(f"  成功请求: {stats.get('successful_requests', 0)}")
                print(f"  失败请求: {stats.get('failed_requests', 0)}")
                print(f"  速率限制: {stats.get('rate_limited', 0)}")
                print(f"  数据大小: {stats.get('total_data_size', 0) / 1024:.1f}KB")
        else:
            print(f"错误: {result.get('error', 'unknown error')}")

        print("="*60)

    # 运行主函数
    asyncio.run(main())
