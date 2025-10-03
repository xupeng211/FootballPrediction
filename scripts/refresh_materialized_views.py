import os
#!/usr/bin/env python3
"""
物化视图刷新脚本

用于定期刷新数据库中的物化视图，确保高频查询的数据保持最新状态。

主要功能：
1. 刷新球队近期战绩物化视图 (mv_team_recent_performance)
2. 刷新赔率趋势分析物化视图 (mv_odds_trends)
3. 提供并发刷新和错误处理
4. 记录刷新日志和性能指标

使用方法：
    python scripts/refresh_materialized_views.py
    python scripts/refresh_materialized_views.py --view team_performance
    python scripts/refresh_materialized_views.py --view odds_trends
    python scripts/refresh_materialized_views.py --concurrent
"""

import argparse
import asyncio
import logging
import time
from datetime import datetime
from typing import List, Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from src.database.config import get_database_config

# 配置日志
logging.basicConfig(
    level=logging.INFO, format = os.getenv("REFRESH_MATERIALIZED_VIEWS_FORMAT_34")
)
logger = logging.getLogger(__name__)


class MaterializedViewRefresher:
    """物化视图刷新器"""

    # 支持的物化视图定义
    MATERIALIZED_VIEWS = {
        "team_performance": {
            "name": "mv_team_recent_performance",
            "description": "球队近期战绩统计",
            "estimated_duration": 30,  # 秒
        },
        "odds_trends": {
            "name": "mv_odds_trends",
            "description": "赔率趋势分析",
            "estimated_duration": 45,  # 秒
        },
    }

    def __init__(self):
        """初始化刷新器"""
        self.config = get_database_config()

    async def _get_async_engine(self):
        """获取异步数据库引擎"""
        database_url = (
            f"postgresql+asyncpg://{self.config.user}:{self.config.password}"
            f"@{self.config.host}:{self.config.port}/{self.config.database}"
        )
        return create_async_engine(database_url, echo=False)

    async def refresh_view(self, view_key: str, concurrent: bool = False) -> dict:
        """
        刷新指定的物化视图

        Args:
            view_key: 物化视图的键名 ('team_performance' 或 'odds_trends')
            concurrent: 是否使用并发刷新

        Returns:
            dict: 刷新结果和性能指标
        """
        if view_key not in self.MATERIALIZED_VIEWS:
            raise ValueError(f"不支持的物化视图: {view_key}")

        view_info = self.MATERIALIZED_VIEWS[view_key]
        view_name = view_info["name"]
        description = view_info["description"]

        logger.info(f"开始刷新物化视图: {description} ({view_name})")
        start_time = time.time()

        try:
            engine = await self._get_async_engine()

            async with engine.begin() as conn:
                # 检查物化视图是否存在
                exists_query = text(
                    """
                    SELECT EXISTS (
                        SELECT 1 FROM pg_matviews
                        WHERE matviewname = :view_name
                    );
                """
                )

                result = await conn.execute(exists_query, {"view_name": view_name})
                exists = result.scalar()

                if not exists:
                    logger.error(f"物化视图 {view_name} 不存在")
                    return {
                        "success": False,
                        "view_name": view_name,
                        "error": "物化视图不存在",
                        "duration": 0,
                    }

                # 获取刷新前的行数
                count_before_query = text(f"SELECT COUNT(*) FROM {view_name};")
                count_before = await conn.execute(count_before_query)
                rows_before = count_before.scalar()

                # 执行刷新
                if concurrent:
                    refresh_query = text(
                        f"REFRESH MATERIALIZED VIEW CONCURRENTLY {view_name};"
                    )
                    logger.info(f"使用并发模式刷新 {view_name}")
                else:
                    refresh_query = text(f"REFRESH MATERIALIZED VIEW {view_name};")
                    logger.info(f"使用标准模式刷新 {view_name}")

                await conn.execute(refresh_query)

                # 获取刷新后的行数
                count_after = await conn.execute(count_before_query)
                rows_after = count_after.scalar()

            await engine.dispose()

            duration = time.time() - start_time

            logger.info(
                f"✅ 物化视图 {view_name} 刷新完成 "
                f"(耗时: {duration:.2f}秒, 行数: {rows_before} -> {rows_after})"
            )

            return {
                "success": True,
                "view_name": view_name,
                "description": description,
                "duration": duration,
                "rows_before": rows_before,
                "rows_after": rows_after,
                "concurrent": concurrent,
                "timestamp": datetime.now().isoformat(),
            }

        except Exception as e:
            duration = time.time() - start_time
            error_msg = str(e)

            logger.error(f"❌ 刷新物化视图 {view_name} 失败: {error_msg}")

            return {
                "success": False,
                "view_name": view_name,
                "description": description,
                "error": error_msg,
                "duration": duration,
                "concurrent": concurrent,
                "timestamp": datetime.now().isoformat(),
            }

    async def refresh_all_views(self, concurrent: bool = False) -> List[dict]:
        """
        刷新所有物化视图

        Args:
            concurrent: 是否使用并发刷新

        Returns:
            List[dict]: 所有视图的刷新结果
        """
        logger.info("开始刷新所有物化视图")
        start_time = time.time()

        results = []

        # 按依赖顺序刷新（team_performance 不依赖其他视图，可以先刷新）
        view_order = ["team_performance", "odds_trends"]

        for view_key in view_order:
            result = await self.refresh_view(view_key, concurrent)
            results.append(result)

            # 如果刷新失败，记录但继续其他视图
            if not result["success"]:
                logger.warning(f"视图 {view_key} 刷新失败，继续处理其他视图")

        total_duration = time.time() - start_time
        successful_refreshes = sum(1 for r in results if r["success"])

        logger.info(
            f"🎉 物化视图刷新完成: {successful_refreshes}/{len(results)} 成功 "
            f"(总耗时: {total_duration:.2f}秒)"
        )

        return results

    async def get_view_info(self, view_key: Optional[str] = None) -> dict:
        """
        获取物化视图信息

        Args:
            view_key: 指定视图的键名，None则返回所有视图信息

        Returns:
            dict: 视图信息和统计数据
        """
        logger.info("获取物化视图信息")

        try:
            engine = await self._get_async_engine()

            async with engine.begin() as conn:
                # 查询所有物化视图的元数据
                metadata_query = text(
                    """
                    SELECT
                        matviewname as view_name,
                        definition as view_definition,
                        hasindexes as has_indexes,
                        ispopulated as is_populated
                    FROM pg_matviews
                    WHERE schemaname = os.getenv("REFRESH_MATERIALIZED_VIEWS_SCHEMANAME_233")
                    ORDER BY matviewname;
                """
                )

                metadata_result = await conn.execute(metadata_query)
                metadata_rows = metadata_result.fetchall()

                view_info = {}

                for row in metadata_rows:
                    view_name = row.view_name

                    # 检查是否是我们管理的视图
                    managed_view_key = None
                    for key, info in self.MATERIALIZED_VIEWS.items():
                        if info["name"] == view_name:
                            managed_view_key = key
                            break

                    if view_key and managed_view_key != view_key:
                        continue

                    # 获取行数
                    if row.is_populated:
                        count_query = text(f"SELECT COUNT(*) FROM {view_name};")
                        count_result = await conn.execute(count_query)
                        row_count = count_result.scalar()
                    else:
                        row_count = 0

                    # 获取最后更新时间（如果视图有 last_updated 字段）
                    last_updated = None
                    try:
                        last_updated_query = text(
                            f"SELECT MAX(last_updated) FROM {view_name};"
                        )
                        last_updated_result = await conn.execute(last_updated_query)
                        last_updated = last_updated_result.scalar()
                        if last_updated:
                            last_updated = last_updated.isoformat()
                    except Exception:
                        # 某些视图可能没有 last_updated 字段
                        pass

                    view_info[view_name] = {
                        "managed_key": managed_view_key,
                        "description": self.MATERIALIZED_VIEWS.get(
                            managed_view_key, {}
                        ).get("description", "未知"),
                        "has_indexes": row.has_indexes,
                        "is_populated": row.is_populated,
                        "row_count": row_count,
                        "last_updated": last_updated,
                        "estimated_refresh_duration": self.MATERIALIZED_VIEWS.get(
                            managed_view_key, {}
                        ).get("estimated_duration", 0),
                    }

            await engine.dispose()

            return {
                "success": True,
                "views": view_info,
                "timestamp": datetime.now().isoformat(),
            }

        except Exception as e:
            logger.error(f"获取物化视图信息失败: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            }


async def main():
    """主函数"""
    parser = argparse.ArgumentParser(description = os.getenv("REFRESH_MATERIALIZED_VIEWS_DESCRIPTION_310"))
    parser.add_argument(
        "--view",
        choices=["team_performance", "odds_trends"],
        help = os.getenv("REFRESH_MATERIALIZED_VIEWS_HELP_312"),
    )
    parser.add_argument(
        "--concurrent",
        action = os.getenv("REFRESH_MATERIALIZED_VIEWS_ACTION_315"),
        help = os.getenv("REFRESH_MATERIALIZED_VIEWS_HELP_315"),
    )
    parser.add_argument("--info", action = os.getenv("REFRESH_MATERIALIZED_VIEWS_ACTION_315"), help = os.getenv("REFRESH_MATERIALIZED_VIEWS_HELP_318"))

    args = parser.parse_args()

    refresher = MaterializedViewRefresher()

    try:
        if args.info:
            # 显示视图信息
            info = await refresher.get_view_info(args.view)
            if info["success"]:
                print("\n📊 物化视图信息:")
                print("=" * 60)
                for view_name, details in info["views"].items():
                    print(f"视图名称: {view_name}")
                    print(f"描述: {details['description']}")
                    print(f"管理键: {details['managed_key']}")
                    print(f"已填充: {'是' if details['is_populated'] else '否'}")
                    print(f"行数: {details['row_count']:,}")
                    print(f"有索引: {'是' if details['has_indexes'] else '否'}")
                    print(f"最后更新: {details['last_updated'] or '未知'}")
                    print(f"预计刷新时间: {details['estimated_refresh_duration']}秒")
                    print("-" * 40)
            else:
                print(f"❌ 获取视图信息失败: {info['error']}")

        elif args.view:
            # 刷新指定视图
            result = await refresher.refresh_view(args.view, args.concurrent)
            if result["success"]:
                print(f"✅ 视图 {args.view} 刷新成功")
                print(f"   耗时: {result['duration']:.2f}秒")
                print(f"   行数变化: {result['rows_before']} -> {result['rows_after']}")
            else:
                print(f"❌ 视图 {args.view} 刷新失败: {result['error']}")

        else:
            # 刷新所有视图
            results = await refresher.refresh_all_views(args.concurrent)

            print("\n🎯 刷新结果汇总:")
            print("=" * 60)
            total_duration = sum(r["duration"] for r in results)
            successful = [r for r in results if r["success"]]
            failed = [r for r in results if not r["success"]]

            print(f"总共刷新: {len(results)} 个视图")
            print(f"成功: {len(successful)} 个")
            print(f"失败: {len(failed)} 个")
            print(f"总耗时: {total_duration:.2f}秒")

            if successful:
                print("\n✅ 成功的视图:")
                for result in successful:
                    print(f"  - {result['description']}: {result['duration']:.2f}秒")

            if failed:
                print("\n❌ 失败的视图:")
                for result in failed:
                    print(f"  - {result['description']}: {result['error']}")

    except KeyboardInterrupt:
        logger.info("用户中断操作")
    except Exception as e:
        logger.error(f"程序执行失败: {str(e)}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
