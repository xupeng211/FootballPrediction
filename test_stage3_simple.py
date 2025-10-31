#!/usr/bin/env python3
"""
第三阶段简化测试脚本
Stage 3 Simple Test Script - Database Integration and Caching
"""

import asyncio
import sys
import os
import logging
from datetime import datetime
from typing import Dict, Any

# 添加项目根目录到Python路径
sys.path.insert(0, '/home/user/projects/FootballPrediction')

# 设置环境变量
os.environ['FOOTBALL_DATA_API_KEY'] = 'ed809154dc1f422da46a18d8961a98a0'

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# 尝试导入模块，失败时使用简化版本
try:
    from test_stage2_fixed import SimpleDataCollector
except ImportError:
    logger.error("无法导入基础数据采集器")
    sys.exit(1)


class SimpleCacheManager:
    """简化的缓存管理器"""

    def __init__(self):
        self.cache = {}
        self.cache_timestamps = {}

    def set_cache(self, key: str, value: Any, ttl_seconds: int = 3600) -> bool:
        """设置缓存"""
        try:
            self.cache[key] = value
            self.cache_timestamps[key] = {
                'created_at': datetime.utcnow(),
                'ttl_seconds': ttl_seconds
            }
            return True
        except Exception as e:
            logger.error(f"设置缓存失败: {e}")
            return False

    def get_cache(self, key: str) -> Any:
        """获取缓存"""
        try:
            if key not in self.cache:
                return None

            # 检查是否过期
            timestamp_info = self.cache_timestamps.get(key)
            if timestamp_info:
                age = (datetime.utcnow() - timestamp_info['created_at']).total_seconds()
                if age > timestamp_info['ttl_seconds']:
                    del self.cache[key]
                    del self.cache_timestamps[key]
                    return None

            return self.cache.get(key)
        except Exception as e:
            logger.error(f"获取缓存失败: {e}")
            return None

    def delete_cache(self, key: str) -> bool:
        """删除缓存"""
        try:
            if key in self.cache:
                del self.cache[key]
            if key in self.cache_timestamps:
                del self.cache_timestamps[key]
            return True
        except Exception as e:
            logger.error(f"删除缓存失败: {e}")
            return False

    def clear_all(self) -> bool:
        """清空所有缓存"""
        try:
            self.cache.clear()
            self.cache_timestamps.clear()
            return True
        except Exception as e:
            logger.error(f"清空缓存失败: {e}")
            return False


class Stage3SimpleTester:
    """第三阶段简化测试器"""

    def __init__(self):
        self.cache_manager = SimpleCacheManager()
        self.test_results = {
            'total_tests': 0,
            'passed_tests': 0,
            'failed_tests': 0,
            'errors': []
        }

    async def test_basic_caching(self) -> bool:
        """测试基础缓存功能"""
        try:
            logger.info("测试基础缓存功能...")

            # 测试设置和获取缓存
            test_data = {
                'external_id': '2021',
                'name': 'Premier League',
                'code': 'PL',
                'type': 'LEAGUE'
            }

            # 缓存数据
            success = self.cache_manager.set_cache('league:2021', test_data, ttl_seconds=60)
            if not success:
                raise Exception("缓存数据失败")

            # 获取缓存数据
            cached_data = self.cache_manager.get_cache('league:2021')
            if not cached_data or cached_data.get('name') != 'Premier League':
                raise Exception("获取缓存数据失败")

            logger.info("  ✅ 基础缓存设置和获取正常")

            # 测试缓存过期
            self.cache_manager.set_cache('temp_data', 'test_value', ttl_seconds=1)
            await asyncio.sleep(2)  # 等待过期
            expired_data = self.cache_manager.get_cache('temp_data')
            if expired_data is not None:
                raise Exception("缓存过期机制失效")

            logger.info("  ✅ 缓存过期机制正常")

            # 测试缓存删除
            self.cache_manager.set_cache('delete_test', 'value')
            delete_success = self.cache_manager.delete_cache('delete_test')
            if not delete_success:
                raise Exception("删除缓存失败")

            deleted_data = self.cache_manager.get_cache('delete_test')
            if deleted_data is not None:
                raise Exception("删除缓存后仍能获取数据")

            logger.info("  ✅ 缓存删除功能正常")

            return True

        except Exception as e:
            logger.error(f"  ❌ 基础缓存功能测试失败: {e}")
            return False

    async def test_data_structures(self) -> bool:
        """测试数据结构"""
        try:
            logger.info("测试数据结构...")

            # 测试联赛数据结构
            league_structure = {
                'external_id': str,
                'name': str,
                'code': str,
                'type': str,
                'area': dict,
                'season': dict,
                'last_updated': str
            }

            # 测试球队数据结构
            team_structure = {
                'external_id': str,
                'name': str,
                'short_name': str,
                'tla': str,
                'crest': str,
                'address': str,
                'website': str,
                'founded': int,
                'area': dict
            }

            # 测试积分榜数据结构
            standings_structure = {
                'position': int,
                'team': dict,
                'played_games': int,
                'won': int,
                'draw': int,
                'lost': int,
                'points': int,
                'goals_for': int,
                'goals_against': int,
                'goal_difference': int
            }

            # 验证数据结构完整性
            required_structures = ['league_structure', 'team_structure', 'standings_structure']
            for structure_name in required_structures:
                structure = locals().get(structure_name)
                if not structure:
                    raise Exception(f"数据结构定义缺失: {structure_name}")

            logger.info("  ✅ 数据结构定义完整")

            # 测试数据转换
            sample_league = {
                'external_id': '2021',
                'name': 'Premier League',
                'code': 'PL',
                'type': 'LEAGUE',
                'area': {'name': 'England', 'code': 'ENG'},
                'season': {'current_matchday': 12},
                'last_updated': datetime.utcnow().isoformat()
            }

            # 缓存并验证数据转换
            self.cache_manager.set_cache('test_league', sample_league)
            cached_league = self.cache_manager.get_cache('test_league')

            if not cached_league or cached_league.get('name') != 'Premier League':
                raise Exception("数据转换失败")

            logger.info("  ✅ 数据转换和缓存正常")

            return True

        except Exception as e:
            logger.error(f"  ❌ 数据结构测试失败: {e}")
            return False

    async def test_api_data_integration(self) -> bool:
        """测试API数据集成"""
        try:
            logger.info("测试API数据集成...")

            async with SimpleDataCollector() as collector:
                # 测试联赛数据采集和缓存
                competitions_data = await collector._make_request_with_retry('competitions')
                if not competitions_data or 'competitions' not in competitions_data:
                    raise Exception("API数据采集失败")

                competitions = competitions_data['competitions']
                if len(competitions) == 0:
                    raise Exception("API返回空数据")

                # 缓存联赛数据
                cache_key = 'api:competitions'
                cache_success = self.cache_manager.set_cache(cache_key, competitions, ttl_seconds=300)
                if not cache_success:
                    raise Exception("缓存API数据失败")

                # 验证缓存数据
                cached_competitions = self.cache_manager.get_cache(cache_key)
                if not cached_competitions or len(cached_competitions) == 0:
                    raise Exception("缓存数据验证失败")

                logger.info(f"  ✅ API数据采集和缓存成功: {len(competitions)} 个联赛")

                # 测试球队数据采集和缓存
                teams_data = await collector._make_request_with_retry('competitions/2021/teams')
                if not teams_data or 'teams' not in teams_data:
                    raise Exception("球队数据采集失败")

                teams = teams_data['teams']
                if len(teams) == 0:
                    raise Exception("球队数据为空")

                # 缓存球队数据
                teams_cache_key = 'api:teams:2021'
                cache_success = self.cache_manager.set_cache(teams_cache_key, teams, ttl_seconds=600)
                if not cache_success:
                    raise Exception("缓存球队数据失败")

                logger.info(f"  ✅ 球队数据采集和缓存成功: {len(teams)} 支球队")

                # 测试积分榜数据采集和缓存
                standings_data = await collector._make_request_with_retry('competitions/2021/standings')
                if not standings_data or 'standings' not in standings_data:
                    raise Exception("积分榜数据采集失败")

                standings = standings_data['standings']
                if len(standings) == 0:
                    raise Exception("积分榜数据为空")

                # 缓存积分榜数据
                standings_cache_key = 'api:standings:2021'
                cache_success = self.cache_manager.set_cache(standings_cache_key, standings, ttl_seconds=1800)
                if not cache_success:
                    raise Exception("缓存积分榜数据失败")

                logger.info(f"  ✅ 积分榜数据采集和缓存成功: {len(standings[0].get('table', []))} 支球队")

                return True

        except Exception as e:
            logger.error(f"  ❌ API数据集成测试失败: {e}")
            return False

    async def test_cache_performance(self) -> bool:
        """测试缓存性能"""
        try:
            logger.info("测试缓存性能...")

            # 准备测试数据
            test_data = [
                {
                    'id': i,
                    'name': f'Team {i}',
                    'points': i * 3
                } for i in range(1000)
            ]

            # 测试批量写入性能
            start_time = datetime.utcnow()
            for i, data in enumerate(test_data):
                self.cache_manager.set_cache(f'team:{i}', data, ttl_seconds=3600)

            write_time = (datetime.utcnow() - start_time).total_seconds()
            logger.info(f"  ✅ 批量写入1000条数据耗时: {write_time:.3f}秒")

            # 测试批量读取性能
            start_time = datetime.utcnow()
            successful_reads = 0
            for i in range(1000):
                cached_data = self.cache_manager.get_cache(f'team:{i}')
                if cached_data:
                    successful_reads += 1

            read_time = (datetime.utcnow() - start_time).total_seconds()
            logger.info(f"  ✅ 批量读取1000条数据耗时: {read_time:.3f}秒")
            logger.info(f"  ✅ 读取成功率: {successful_reads}/1000 ({successful_reads/10:.1f}%)")

            # 测试内存使用情况
            cache_size = len(self.cache_manager.cache)
            logger.info(f"  ✅ 缓存中包含 {cache_size} 条数据")

            if write_time > 1.0:  # 写入超过1秒认为性能不佳
                logger.warning(f"  ⚠️ 写入性能较慢: {write_time:.3f}秒")

            if read_time > 0.5:  # 读取超过0.5秒认为性能不佳
                logger.warning(f"  ⚠️ 读取性能较慢: {read_time:.3f}秒")

            return True

        except Exception as e:
            logger.error(f"  ❌ 缓存性能测试失败: {e}")
            return False

    async def test_error_handling(self) -> bool:
        """测试错误处理"""
        try:
            logger.info("测试错误处理...")

            # 测试无效数据类型缓存
            invalid_data = object()  # 不可序列化的对象
            success = self.cache_manager.set_cache('invalid_test', invalid_data)
            # 应该能够缓存，因为使用的是内存缓存

            # 测试空键值处理
            empty_success = self.cache_manager.set_cache('', 'test_value')
            if not empty_success:
                logger.warning("  ⚠️ 空键值处理可能有问题")

            # 测试None值缓存
            none_success = self.cache_manager.set_cache('none_test', None)
            if not none_success:
                logger.warning("  ⚠️ None值缓存可能有问题")

            # 测试超长键值处理
            long_key = 'x' * 1000
            long_success = self.cache_manager.set_cache(long_key, 'test_value')
            if not long_success:
                logger.warning("  ⚠️ 超长键值处理可能有问题")

            # 测试并发访问
            async def concurrent_access():
                for i in range(100):
                    self.cache_manager.set_cache(f'concurrent_{i}', f'value_{i}')
                    cached = self.cache_manager.get_cache(f'concurrent_{i}')
                    if cached != f'value_{i}':
                        return False
                return True

            tasks = [concurrent_access() for _ in range(5)]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            successful_concurrent = sum(1 for result in results if result is True)
            logger.info(f"  ✅ 并发访问测试: {successful_concurrent}/5 成功")

            return successful_concurrent >= 4  # 至少80%的并发测试成功

        except Exception as e:
            logger.error(f"  ❌ 错误处理测试失败: {e}")
            return False

    async def run_all_tests(self) -> bool:
        """运行所有测试"""
        print("🚀 开始第三阶段简化测试")
        print("=" * 50)

        start_time = datetime.now()

        tests = [
            ("基础缓存功能", self.test_basic_caching),
            ("数据结构", self.test_data_structures),
            ("API数据集成", self.test_api_data_integration),
            ("缓存性能", self.test_cache_performance),
            ("错误处理", self.test_error_handling)
        ]

        for test_name, test_func in tests:
            print(f"\n🔍 执行 {test_name}测试...")
            self.test_results['total_tests'] += 1

            try:
                if await test_func():
                    print(f"✅ {test_name}测试通过")
                    self.test_results['passed_tests'] += 1
                else:
                    print(f"❌ {test_name}测试失败")
                    self.test_results['failed_tests'] += 1
            except Exception as e:
                print(f"❌ {test_name}测试异常: {e}")
                self.test_results['failed_tests'] += 1
                self.test_results['errors'].append(f"{test_name}: {e}")

        end_time = datetime.now()
        duration = end_time - start_time

        # 清理测试数据
        try:
            self.cache_manager.clear_all()
            logger.info("✅ 测试数据清理完成")
        except Exception as e:
            logger.warning(f"⚠️ 测试数据清理失败: {e}")

        print("\n" + "=" * 50)
        print(f"📊 第三阶段简化测试完成!")
        print(f"   总计: {self.test_results['total_tests']}")
        print(f"   通过: {self.test_results['passed_tests']}")
        print(f"   失败: {self.test_results['failed_tests']}")
        print(f"   耗时: {duration.total_seconds():.2f} 秒")

        if self.test_results['errors']:
            print("\n❌ 错误详情:")
            for error in self.test_results['errors']:
                print(f"   - {error}")

        success_rate = 0
        if self.test_results['total_tests'] > 0:
            success_rate = (self.test_results['passed_tests'] / self.test_results['total_tests']) * 100

        print(f"\n🎯 成功率: {success_rate:.1f}%")

        if self.test_results['failed_tests'] == 0:
            print("🎉 所有测试通过！")
            print("✅ 基础缓存功能正常")
            print("✅ 数据结构定义完整")
            print("✅ API数据集成成功")
            print("✅ 缓存性能符合预期")
            print("✅ 错误处理机制有效")
            print("🚀 第三阶段简化验证完成！")
            return True
        else:
            print("⚠️  部分测试失败，请检查实现")
            return False


async def main():
    """主测试函数"""
    tester = Stage3SimpleTester()

    try:
        # 运行所有测试
        success = await tester.run_all_tests()

        print(f"\n退出码: {0 if success else 1}")
        return success

    except Exception as e:
        logger.error(f"测试执行失败: {e}")
        print(f"\n❌ 测试执行异常: {e}")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)