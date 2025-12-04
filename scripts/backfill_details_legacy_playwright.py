#!/usr/bin/env python3
"""
Playwright L2 深度补全脚本

使用Playwright浏览器自动化来绕过反爬虫机制，获取Lineups/Stats数据
目标：处理26,000+条记录，特别是data_completeness = 'partial'的记录
"""

import asyncio
import json
import logging
import sys
import os
import time
import psycopg2
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass

# 添加项目路径
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

try:
    from playwright.async_api import async_playwright, Page, Browser, BrowserContext
except ImportError as e:
    print("❌ 需要安装playwright: pip install playwright")
    print("然后运行: playwright install chromium")
    sys.exit(1)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('playwright_l2_backfill.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


@dataclass
class L2MatchResult:
    """L2处理结果数据结构"""
    match_id: int
    success: bool
    lineups_count: int
    stats_count: int
    events_count: int
    processing_time: float
    error_message: Optional[str] = None


class PlaywrightL2Processor:
    """Playwright L2深度处理器"""

    def __init__(self):
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.processed_count = 0
        self.success_count = 0
        self.total_time = 0

    async def initialize(self):
        """初始化Playwright浏览器"""
        logger.info("🚀 初始化Playwright浏览器...")

        try:
            playwright = await async_playwright().start()

            # 启动浏览器（使用无头模式）
            self.browser = await playwright.chromium.launch(
                headless=True,
                args=[
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-accelerated-2d-canvas',
                    '--disable-gpu',
                    '--window-size=1920,1080'
                ]
            )

            # 创建浏览器上下文
            self.context = await self.browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            )

            # 创建页面
            self.page = await self.context.new_page()

            # 设置网络拦截
            await self.page.route('**/*', self._handle_request)

            logger.info("✅ Playwright浏览器初始化成功")

        except Exception as e:
            logger.error(f"❌ Playwright初始化失败: {e}")
            raise

    async def _handle_request(self, route):
        """处理网络请求"""
        await route.continue_()

    async def get_partial_matches(self, limit: int = 100) -> List[Dict[str, Any]]:
        """获取需要处理的partial记录"""
        try:
            conn = psycopg2.connect(
                host='db',
                database='football_prediction',
                user='postgres',
                password='postgres-dev-password',
                port='5432'
            )
            cursor = conn.cursor()

            query = """
            SELECT id, home_team_id, away_team_id, match_date, home_score, away_score,
                   stats, lineups, events, original_url, data_completeness
            FROM matches
            WHERE data_completeness = 'partial'
                AND home_score IS NOT NULL
                AND away_score IS NOT NULL
            LIMIT %s
            """

            cursor.execute(query, (limit,))
            columns = [desc[0] for desc in cursor.description]
            matches = [dict(zip(columns, row)) for row in cursor.fetchall()]

            cursor.close()
            conn.close()

            logger.info(f"📊 找到 {len(matches)} 条需要处理的记录")
            return matches

        except Exception as e:
            logger.error(f"❌ 获取记录失败: {e}")
            return []

    async def construct_match_url(self, match_data: Dict[str, Any]) -> Optional[str]:
        """构造比赛详情页面URL"""
        match_id = match_data['id']

        # 尝试多种URL构造方式
        urls_to_try = [
            f"https://fbref.com/en/matches/{match_id}",
            f"https://www.fbref.com/en/matches/{match_id}",
            f"https://fbref.com/match/{match_id}",
        ]

        return urls_to_try[0]  # 返回第一个尝试的URL

    async def extract_match_details(self, url: str) -> Optional[Dict[str, Any]]:
        """从比赛页面提取详细信息"""
        if not self.page:
            return None

        try:
            logger.info(f"🌐 访问页面: {url}")
            start_time = time.time()

            # 访问页面
            response = await self.page.goto(url, timeout=30000)

            if response.status != 200:
                logger.warning(f"⚠️ 页面状态码: {response.status}")
                return None

            # 等待页面加载
            await self.page.wait_for_load_state('networkidle', timeout=10000)

            # 尝试等待关键元素
            try:
                await self.page.wait_for_selector('table', timeout=5000)
            except:
                # 如果没有找到table，可能需要不同的选择器
                pass

            # 提取页面内容
            page_content = await self.page.content()

            # 基础HTML解析
            details = {
                'url': url,
                'page_title': await self.page.title(),
                'content_length': len(page_content),
                'lineups': await self._extract_lineups(),
                'stats': await self._extract_stats(),
                'events': await self._extract_events(),
                'access_time': time.time() - start_time
            }

            logger.info(f"✅ 页面访问成功，耗时: {details['access_time']:.2f}s")
            return details

        except Exception as e:
            logger.error(f"❌ 页面提取失败: {e}")
            return None

    async def _extract_lineups(self) -> Optional[Dict[str, Any]]:
        """提取阵容数据"""
        try:
            # 尝试查找阵容相关元素
            lineups_selectors = [
                'table.lineups',
                '[id*="lineup"]',
                '.lineup',
                'table:has(th:contains("Player"))'
            ]

            for selector in lineups_selectors:
                try:
                    element = await self.page.query_selector(selector)
                    if element:
                        text = await element.text_content()
                        if text and len(text.strip()) > 50:  # 有意义的阵容数据
                            return {
                                'extracted': True,
                                'selector': selector,
                                'text_length': len(text),
                                'sample': text[:200] + '...' if len(text) > 200 else text
                            }
                except:
                    continue

            return {'extracted': False, 'message': 'No lineup data found'}

        except Exception as e:
            logger.warning(f"⚠️ 阵容提取警告: {e}")
            return {'extracted': False, 'error': str(e)}

    async def _extract_stats(self) -> Optional[Dict[str, Any]]:
        """提取统计数据"""
        try:
            # 尝试查找统计相关元素
            stats_selectors = [
                'table.stats',
                '[id*="stats"]',
                '.stats',
                'table:has(th:contains("Stat"))',
                'div.stats'
            ]

            for selector in stats_selectors:
                try:
                    elements = await self.page.query_selector_all(selector)
                    if elements:
                        stats_data = []
                        for element in elements[:3]:  # 只取前3个避免过多
                            text = await element.text_content()
                            if text and len(text.strip()) > 20:
                                stats_data.append({
                                    'selector': selector,
                                    'text_length': len(text),
                                    'sample': text[:100] + '...' if len(text) > 100 else text
                                })

                        if stats_data:
                            return {
                                'extracted': True,
                                'data_count': len(stats_data),
                                'data': stats_data
                            }
                except:
                    continue

            return {'extracted': False, 'message': 'No stats data found'}

        except Exception as e:
            logger.warning(f"⚠️ 统计提取警告: {e}")
            return {'extracted': False, 'error': str(e)}

    async def _extract_events(self) -> Optional[Dict[str, Any]]:
        """提取事件数据"""
        try:
            # 尝试查找事件相关元素
            events_selectors = [
                'table.events',
                '[id*="event"]',
                '.events',
                'table:has(th:contains("Minute"))'
            ]

            for selector in events_selectors:
                try:
                    element = await self.page.query_selector(selector)
                    if element:
                        text = await element.text_content()
                        if text and len(text.strip()) > 30:  # 有意义的事件数据
                            return {
                                'extracted': True,
                                'selector': selector,
                                'text_length': len(text),
                                'sample': text[:200] + '...' if len(text) > 200 else text
                            }
                except:
                    continue

            return {'extracted': False, 'message': 'No events data found'}

        except Exception as e:
            logger.warning(f"⚠️ 事件提取警告: {e}")
            return {'extracted': False, 'error': str(e)}

    async def update_match_with_details(self, match_id: int, details: Dict[str, Any]) -> bool:
        """更新比赛记录的详细信息"""
        try:
            conn = psycopg2.connect(
                host='db',
                database='football_prediction',
                user='postgres',
                password='postgres-dev-password',
                port='5432'
            )
            cursor = conn.cursor()

            # 获取现有数据
            cursor.execute("SELECT stats, lineups, events FROM matches WHERE id = %s", (match_id,))
            result = cursor.fetchone()

            if result:
                existing_stats, existing_lineups, existing_events = result

                # 更新数据（如果提取到了新数据）
                new_stats = existing_stats or {}
                new_lineups = existing_lineups or {}
                new_events = existing_events or {}

                # 更新字段
                if details.get('lineups', {}).get('extracted'):
                    new_lineups.update({
                        'playwright_extracted': True,
                        'extraction_time': datetime.now().isoformat(),
                        'extraction_details': details['lineups']
                    })

                if details.get('stats', {}).get('extracted'):
                    new_stats.update({
                        'playwright_extracted': True,
                        'extraction_time': datetime.now().isoformat(),
                        'extraction_details': details['stats']
                    })

                if details.get('events', {}).get('extracted'):
                    new_events.update({
                        'playwright_extracted': True,
                        'extraction_time': datetime.now().isoformat(),
                        'extraction_details': details['events']
                    })

                # 判断是否应该标记为complete
                has_new_data = any([
                    details.get('lineups', {}).get('extracted'),
                    details.get('stats', {}).get('extracted'),
                    details.get('events', {}).get('extracted')
                ])

                new_completeness = 'complete' if has_new_data else 'partial'

                # 更新数据库
                from psycopg2.extras import Json
                update_query = """
                UPDATE matches
                SET stats = %s, lineups = %s, events = %s,
                    data_completeness = %s, updated_at = NOW()
                WHERE id = %s
                """

                cursor.execute(update_query, (
                    Json(new_stats),
                    Json(new_lineups),
                    Json(new_events),
                    new_completeness,
                    match_id
                ))
                conn.commit()

                logger.info(f"✅ 成功更新比赛 {match_id}，完整度: {new_completeness}")
                return True

            else:
                logger.error(f"❌ 找不到比赛记录 {match_id}")
                return False

        except Exception as e:
            logger.error(f"❌ 更新数据库失败: {e}")
            return False
        finally:
            if 'conn' in locals():
                conn.close()

    async def process_single_match(self, match_data: Dict[str, Any]) -> L2MatchResult:
        """处理单条比赛记录"""
        match_id = match_data['id']
        start_time = time.time()

        logger.info(f"🎯 开始处理比赛 {match_id}")

        try:
            # 构造URL
            url = await self.construct_match_url(match_data)
            if not url:
                return L2MatchResult(
                    match_id=match_id,
                    success=False,
                    lineups_count=0,
                    stats_count=0,
                    events_count=0,
                    processing_time=0,
                    error_message="无法构造URL"
                )

            # 提取详情
            details = await self.extract_match_details(url)
            if not details:
                return L2MatchResult(
                    match_id=match_id,
                    success=False,
                    lineups_count=0,
                    stats_count=0,
                    events_count=0,
                    processing_time=time.time() - start_time,
                    error_message="页面访问失败"
                )

            # 更新数据库
            update_success = await self.update_match_with_details(match_id, details)

            # 统计提取的数据量
            lineups_count = 1 if details.get('lineups', {}).get('extracted') else 0
            stats_count = len(details.get('stats', {}).get('data', [])) if details.get('stats', {}).get('extracted') else 0
            events_count = 1 if details.get('events', {}).get('extracted') else 0

            processing_time = time.time() - start_time

            return L2MatchResult(
                match_id=match_id,
                success=update_success,
                lineups_count=lineups_count,
                stats_count=stats_count,
                events_count=events_count,
                processing_time=processing_time
            )

        except Exception as e:
            logger.error(f"💥 处理比赛 {match_id} 异常: {e}")
            return L2MatchResult(
                match_id=match_id,
                success=False,
                lineups_count=0,
                stats_count=0,
                events_count=0,
                processing_time=time.time() - start_time,
                error_message=str(e)
            )

    async def process_matches_batch(self, batch_size: int = 50):
        """批量处理比赛记录"""
        logger.info(f"🚀 开始批量处理，批次大小: {batch_size}")

        await self.initialize()

        try:
            while True:
                # 获取待处理记录
                matches = await self.get_partial_matches(batch_size)

                if not matches:
                    logger.info("✅ 没有更多待处理记录")
                    break

                logger.info(f"📋 处理批次: {len(matches)} 条记录")

                # 处理每条记录
                batch_results = []
                for i, match in enumerate(matches, 1):
                    logger.info(f"📝 处理进度: {i}/{len(matches)}")

                    result = await self.process_single_match(match)
                    batch_results.append(result)

                    # 更新统计
                    self.processed_count += 1
                    if result.success:
                        self.success_count += 1
                    self.total_time += result.processing_time

                    # 短暂休息
                    await asyncio.sleep(2)

                # 输出批次结果
                self._print_batch_summary(batch_results)

                # 如果成功处理了一些记录，继续下一批
                if self.success_count > 0:
                    logger.info("🎯 本批次有成功记录，继续下一批...")
                else:
                    logger.warning("⚠️ 本批次没有成功记录，可能需要调整策略")
                    break

        except KeyboardInterrupt:
            logger.info("⏹️ 用户中断处理")
        except Exception as e:
            logger.error(f"💥 批量处理异常: {e}")
        finally:
            await self.cleanup()

    def _print_batch_summary(self, results: List[L2MatchResult]):
        """输出批次处理总结"""
        successful = sum(1 for r in results if r.success)
        total_lineups = sum(r.lineups_count for r in results)
        total_stats = sum(r.stats_count for r in results)
        total_events = sum(r.events_count for r in results)
        avg_time = sum(r.processing_time for r in results) / len(results) if results else 0

        print("\n" + "="*60)
        print("🏆 批次处理总结")
        print("="*60)
        print(f"📊 本批次记录数: {len(results)}")
        print(f"✅ 成功处理: {successful}")
        print(f"📈 成功率: {successful/len(results)*100:.1f}%")
        print(f"👥 阵容数据: {total_lineups} 条")
        print(f"📊 统计数据: {total_stats} 条")
        print(f"⚡ 事件数据: {total_events} 条")
        print(f"⏱️  平均耗时: {avg_time:.2f}s/记录")
        print("="*60)

    async def cleanup(self):
        """清理资源"""
        if self.page:
            await self.page.close()
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        logger.info("🧹 浏览器资源已清理")

    async def print_final_summary(self):
        """输出最终总结"""
        print("\n" + "="*80)
        print("🏆 Playwright L2 处理最终总结")
        print("="*80)
        print(f"📊 总处理记录数: {self.processed_count}")
        print(f"✅ 成功处理记录数: {self.success_count}")
        print(f"📈 总体成功率: {self.success_count/max(1, self.processed_count)*100:.1f}%")
        print(f"⏱️  总处理时间: {self.total_time:.2f}s")
        if self.processed_count > 0:
            print(f"📊 平均处理时间: {self.total_time/self.processed_count:.2f}s/记录")
        print("="*80)


async def main():
    """主函数"""
    print("🎯 Playwright L2 深度补全引擎启动")
    print("这是获取Lineups/Stats的最后一线希望！")
    print("="*60)

    processor = PlaywrightL2Processor()

    try:
        # 处理前几条记录作为验证
        await processor.process_matches_batch(batch_size=10)

        # 输出最终总结
        await processor.print_final_summary()

    except Exception as e:
        logger.error(f"💥 主程序异常: {e}")
    finally:
        await processor.cleanup()


if __name__ == "__main__":
    asyncio.run(main())