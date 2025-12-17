#!/usr/bin/env python3
"""
🌐 数据收集CLI工具 v2.0 - 服务层解耦版本

基于服务层架构的数据收集工具，实现高内聚低耦合设计。
通过CollectionService统一管理所有数据源收集逻辑。

主要功能：
1. 统一的数据收集接口
2. 多数据源协调收集
3. 任务调度和监控
4. 错误处理和重试机制
5. 数据质量验证

使用示例:
    python scripts/data_collector_v2.py --match-id "12345" --sources "fotmob,oddsportal"
    python scripts/data_collector_v2.py --league-id "39" --sources "all"
    python scripts/data_collector_v2.py --status  # 查看收集状态
"""

import argparse
import asyncio
import sys
import os
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DataCollectorDisplay:
    """数据收集结果展示器"""

    @staticmethod
    def display_collection_results(results: List[Dict[str, Any]]) -> None:
        """展示收集结果"""
        print("\n" + "="*60)
        print("🌐 数据收集结果")
        print("="*60)

        total_tasks = len(results)
        successful_tasks = sum(1 for r in results if r.get('status') == 'success')
        failed_tasks = total_tasks - successful_tasks

        print(f"\n📊 收集统计:")
        print(f"   总任务数: {total_tasks}")
        print(f"   成功任务: {successful_tasks}")
        print(f"   失败任务: {failed_tasks}")
        print(f"   成功率: {successful_tasks/total_tasks*100:.1f}%" if total_tasks > 0 else "   成功率: 0%")

        # 详细结果
        print(f"\n📋 详细结果:")
        for i, result in enumerate(results, 1):
            status = result.get('status', 'unknown')
            task_id = result.get('task_id', f'task_{i}')
            source_type = result.get('source_type', 'unknown')
            duration = result.get('duration_seconds', 0)

            status_icon = "✅" if status == 'success' else "❌"
            print(f"   {i}. {status_icon} {task_id} ({source_type}) - {duration:.2f}s")

            if status == 'failed' and result.get('error'):
                print(f"      错误: {result['error']}")
            elif status == 'success' and result.get('result'):
                result_data = result['result']
                if isinstance(result_data, dict):
                    data_points = len(result_data)
                    print(f"      数据点: {data_points}")
                elif isinstance(result_data, list):
                    data_points = len(result_data)
                    print(f"      数据点: {data_points}")

    @staticmethod
    def display_service_stats(stats: Dict[str, Any]) -> None:
        """展示服务统计信息"""
        print("\n" + "="*60)
        print("📈 数据收集服务统计")
        print("="*60)

        print(f"\n🔧 服务状态:")
        print(f"   状态: {stats.get('service_status', 'unknown')}")
        print(f"   可用收集器: {', '.join(stats.get('available_collectors', []))}")
        print(f"   最大并发任务: {stats.get('max_concurrent_tasks', 0)}")

        print(f"\n📊 任务统计:")
        print(f"   总任务数: {stats.get('total_tasks', 0)}")
        print(f"   成功任务: {stats.get('successful_tasks', 0)}")
        print(f"   失败任务: {stats.get('failed_tasks', 0)}")
        print(f"   运行中任务: {stats.get('running_tasks', 0)}")
        print(f"   待处理任务: {stats.get('pending_tasks', 0)}")

        print(f"\n📈 性能指标:")
        print(f"   成功率: {stats.get('success_rate', 0)*100:.1f}%")
        print(f"   平均执行时间: {stats.get('avg_duration_seconds', 0):.2f}秒")
        print(f"   总数据点: {stats.get('total_data_points', 0)}")

        last_collection = stats.get('last_collection_time')
        if last_collection:
            print(f"   最后收集时间: {last_collection}")


class DataCollectorCLI:
    """数据收集CLI工具 - 服务层版本"""

    def __init__(self):
        self.collection_service = None

    async def initialize(self) -> bool:
        """初始化服务"""
        try:
            # 导入服务层
            from src.services.collection_service import collection_service

            self.collection_service = collection_service

            # 初始化服务
            success = await self.collection_service.initialize()
            if not success:
                logger.error("数据收集服务初始化失败")
                return False

            logger.info("数据收集服务初始化成功")
            return True

        except Exception as e:
            logger.error(f"初始化失败: {e}")
            return False

    async def collect_match_data(
        self,
        match_id: str,
        sources: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        收集比赛数据

        Args:
            match_id: 比赛ID
            sources: 数据源列表，如果为None则使用所有可用源

        Returns:
            List[Dict[str, Any]]: 收集结果列表
        """
        logger.info(f"开始收集比赛数据: {match_id}")

        try:
            # 使用服务层收集数据
            result = await self.collection_service.collect_match_data(match_id, sources)

            logger.info(f"比赛数据收集完成: {match_id}")
            return result.get('results', [])

        except Exception as e:
            logger.error(f"比赛数据收集失败: {e}")
            return []

    async def collect_league_data(
        self,
        league_code: str,
        league_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        收集联赛数据

        Args:
            league_code: 联赛代码
            league_id: 联赛ID

        Returns:
            Dict[str, Any]: 收集结果
        """
        logger.info(f"开始收集联赛数据: {league_code}")

        try:
            # 使用服务层收集数据
            result = await self.collection_service.collect_league_data(league_code, league_id)

            logger.info(f"联赛数据收集完成: {league_code}")
            return result

        except Exception as e:
            logger.error(f"联赛数据收集失败: {e}")
            return {"error": str(e)}

    async def collect_custom_data(
        self,
        source_type: str,
        config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        收集自定义数据

        Args:
            source_type: 数据源类型
            config: 收集配置

        Returns:
            Dict[str, Any]: 收集结果
        """
        logger.info(f"开始收集自定义数据: {source_type}")

        try:
            # 创建自定义任务
            task_id = self.collection_service.create_collection_task(
                source_type=source_type,
                source_config=config
            )

            # 执行任务
            result = await self.collection_service.execute_task(task_id)

            logger.info(f"自定义数据收集完成: {task_id}")
            return result

        except Exception as e:
            logger.error(f"自定义数据收集失败: {e}")
            return {"error": str(e), "success": False}

    async def get_service_stats(self) -> Dict[str, Any]:
        """获取服务统计信息"""
        if not self.collection_service:
            return {"error": "服务未初始化"}

        return self.collection_service.get_stats()

    async def get_task_status(
        self,
        status_filter: Optional[str] = None,
        source_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        获取任务状态

        Args:
            status_filter: 按状态过滤
            source_filter: 按数据源过滤

        Returns:
            List[Dict[str, Any]]: 任务状态列表
        """
        if not self.collection_service:
            return []

        from src.services.collection_service import CollectionStatus, DataSourceType

        # 转换过滤条件
        status_enum = None
        if status_filter:
            try:
                status_enum = CollectionStatus(status_filter)
            except ValueError:
                logger.warning(f"无效的状态过滤条件: {status_filter}")

        source_enum = None
        if source_filter:
            try:
                source_enum = DataSourceType(source_filter)
            except ValueError:
                logger.warning(f"无效的数据源过滤条件: {source_filter}")

        return self.collection_service.get_tasks(
            status=status_enum,
            source_type=source_enum
        )

    async def clear_completed_tasks(self, older_than_hours: int = 24) -> int:
        """清理已完成的任务"""
        if not self.collection_service:
            return 0

        return self.collection_service.clear_completed_tasks(older_than_hours)

    async def shutdown(self) -> None:
        """关闭服务"""
        if self.collection_service:
            await self.collection_service.shutdown()


def create_arg_parser() -> argparse.ArgumentParser:
    """创建命令行参数解析器"""
    parser = argparse.ArgumentParser(
        description="数据收集CLI工具 v2.0 - 服务层解耦版本",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  # 收集比赛数据
  python scripts/data_collector_v2.py --match-id "12345" --sources "fotmob,oddsportal"
  python scripts/data_collector_v2.py --match-id "67890" --sources "all"

  # 收集联赛数据
  python scripts/data_collector_v2.py --league-code "PL" --league-id "39"
  python scripts/data_collector_v2.py --league-code "BL1"

  # 自定义数据收集
  python scripts/data_collector_v2.py --custom "fotmob" --config '{"match_id": "12345"}'

  # 查看状态
  python scripts/data_collector_v2.py --status
  python scripts/data_collector_v2.py --status --filter "success"

  # 清理任务
  python scripts/data_collector_v2.py --cleanup --older-hours 12
        """
    )

    # 数据收集选项
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--match-id",
        type=str,
        help="比赛ID"
    )
    group.add_argument(
        "--league-code",
        type=str,
        help="联赛代码 (如 PL, BL1, SA)"
    )
    group.add_argument(
        "--custom",
        type=str,
        help="自定义数据源类型"
    )
    group.add_argument(
        "--status",
        action="store_true",
        help="查看收集状态"
    )
    group.add_argument(
        "--cleanup",
        action="store_true",
        help="清理已完成任务"
    )

    # 配置选项
    parser.add_argument(
        "--sources",
        type=str,
        help="数据源列表，逗号分隔 (fotmob, oddsportal, football_data, all)"
    )

    parser.add_argument(
        "--league-id",
        type=str,
        help="联赛ID (与--league-code配合使用)"
    )

    parser.add_argument(
        "--config",
        type=str,
        help="自定义收集配置 (JSON格式)"
    )

    parser.add_argument(
        "--filter",
        type=str,
        help="状态过滤条件 (pending, running, success, failed, retry)"
    )

    parser.add_argument(
        "--older-hours",
        type=int,
        default=24,
        help="清理多少小时前的任务 (默认: 24)"
    )

    parser.add_argument(
        "--output",
        type=str,
        help="输出文件路径 (JSON格式)"
    )

    parser.add_argument(
        "--verbose",
        action="store_true",
        help="详细输出模式"
    )

    return parser


def parse_sources(sources_str: str) -> Optional[List[str]]:
    """解析数据源字符串"""
    if not sources_str:
        return None

    sources = [s.strip() for s in sources_str.split(',')]

    # 特殊处理 "all"
    if "all" in sources:
        return None  # 使用所有可用源

    return sources


def parse_config(config_str: str) -> Dict[str, Any]:
    """解析配置字符串"""
    try:
        return json.loads(config_str)
    except json.JSONDecodeError as e:
        logger.error(f"配置格式错误: {e}")
        return {}


async def main():
    """主函数"""
    parser = create_arg_parser()
    args = parser.parse_args()

    # 设置日志级别
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # 创建CLI实例
    cli = DataCollectorCLI()

    try:
        # 初始化服务
        if not await cli.initialize():
            logger.error("服务初始化失败")
            return 1

        results = []

        # 收集比赛数据
        if args.match_id:
            sources = parse_sources(args.sources)
            results = await cli.collect_match_data(args.match_id, sources)

        # 收集联赛数据
        elif args.league_code:
            result = await cli.collect_league_data(args.league_code, args.league_id)
            if 'results' in result:
                results = result['results']
            else:
                print(f"联赛数据收集结果: {result}")

        # 自定义数据收集
        elif args.custom:
            config = parse_config(args.config) if args.config else {}
            result = await cli.collect_custom_data(args.custom, config)
            results = [result]

        # 查看状态
        elif args.status:
            stats = await cli.get_service_stats()
            DataCollectorDisplay.display_service_stats(stats)

            tasks = await cli.get_task_status(args.filter)
            if tasks:
                print(f"\n📋 任务列表 (过滤: {args.filter or '全部'}):")
                for task in tasks:
                    print(f"   - {task.get('task_id', 'unknown')}: {task.get('status', 'unknown')}")

            return 0

        # 清理任务
        elif args.cleanup:
            cleaned_count = await cli.clear_completed_tasks(args.older_hours)
            print(f"已清理 {cleaned_count} 个已完成任务")
            return 0

        # 显示收集结果
        if results:
            DataCollectorDisplay.display_collection_results(results)

            # 保存结果到文件
            if args.output:
                output_path = Path(args.output)
                try:
                    with open(output_path, 'w', encoding='utf-8') as f:
                        json.dump(results, f, indent=2, ensure_ascii=False, default=str)
                    print(f"\n💾 结果已保存到: {output_path}")
                except Exception as e:
                    logger.error(f"文件保存失败: {e}")

        return 0

    except KeyboardInterrupt:
        logger.info("用户中断操作")
        return 130
    except Exception as e:
        logger.error(f"程序异常: {e}")
        return 1
    finally:
        # 清理资源
        await cli.shutdown()


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))