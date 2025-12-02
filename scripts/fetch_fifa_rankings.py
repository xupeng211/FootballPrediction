#!/usr/bin/env python3
"""
FIFA排名数据采集器
采集最新的FIFA男足世界排名
"""

import asyncio
import logging
import sys
import json
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.data.collectors.fbref_collector import FBrefCollector
from sqlalchemy import create_engine, text

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)


class FIFARankingFetcher:
    """FIFA排名采集器"""

    def __init__(self):
        self.collector = FBrefCollector()
        # 使用环境变量中的数据库连接
        import os
        db_url = os.environ.get('DATABASE_URL', 'postgresql://postgres:postgres-dev-password@localhost:5432/football_prediction')
        self.engine = create_engine(db_url)

    async def fetch_fifa_ranking_page(self) -> Optional[str]:
        """获取FIFA排名页面"""
        # 尝试多个FIFA排名数据源
        fifa_urls = [
            "https://www.fifa.com/fifa-world-ranking/men",
            "https://en.wikipedia.org/wiki/FIFA_World_Rankings",
            "https://www.espn.com/soccer/fifa-world-ranking/_/list",
        ]

        for i, fifa_url in enumerate(fifa_urls):
            logger.info(f"\n🌍 尝试数据源 {i+1}/{len(fifa_urls)}: {fifa_url}")

            try:
                html_content = await self.collector.fetch_html(fifa_url)

                if html_content:
                    logger.info(f"✅ 成功获取页面: {len(html_content)} 字符")
                    return html_content
                else:
                    logger.warning(f"⚠️ 数据源 {i+1} 返回空内容")

            except Exception as e:
                logger.warning(f"⚠️ 数据源 {i+1} 失败: {e}")
                continue

        logger.error("❌ 所有数据源均失败")
        return None

        # 保存HTML用于调试
        if html_content:
            with open('/tmp/fifa_ranking_page.html', 'w', encoding='utf-8') as f:
                f.write(html_content)
            logger.info("💾 已保存FIFA页面到: /tmp/fifa_ranking_page.html")
            return html_content
        else:
            return None

    def parse_fifa_rankings(self, html_content: str) -> List[Dict]:
        """解析FIFA排名数据"""
        from bs4 import BeautifulSoup

        logger.info("📊 解析FIFA排名数据...")

        soup = BeautifulSoup(html_content, 'html.parser')

        # 查找排名表格
        rankings = []

        # FIFA排名表格可能有多种结构
        # 1. 检查是否有特定ID的表格
        table = soup.find('table', {'class': lambda x: x and ('ranking' in x.lower() or 'table' in x.lower())})

        if not table:
            # 2. 查找所有表格
            tables = soup.find_all('table')
            logger.info(f"  发现 {len(tables)} 个表格")

            for i, tbl in enumerate(tables[:5]):  # 检查前5个表格
                headers = [th.get_text(strip=True).lower() for th in tbl.find_all('th')[:5]]
                logger.info(f"  表格 {i} 表头: {headers}")

                # 检查是否包含排名相关字段
                if any(keyword in ' '.join(headers) for keyword in ['rank', 'position', 'country', 'team', 'points']):
                    table = tbl
                    logger.info(f"  ✅ 选择表格 {i} 作为排名数据源")
                    break

        if not table:
            logger.error("❌ 未找到FIFA排名表格")
            # 尝试从JSON数据中提取
            return self._extract_from_json(html_content)

        # 解析表格数据
        rows = table.find_all('tr')[1:]  # 跳过表头

        for row in rows:
            cells = row.find_all(['td', 'th'])
            if len(cells) >= 3:
                try:
                    rank_data = {
                        'rank': cells[0].get_text(strip=True),
                        'team': cells[1].get_text(strip=True) if len(cells) > 1 else '',
                        'country': cells[2].get_text(strip=True) if len(cells) > 2 else '',
                        'points': cells[3].get_text(strip=True) if len(cells) > 3 else '',
                    }

                    # 验证数据
                    if rank_data['rank'] and rank_data['rank'].isdigit():
                        rankings.append(rank_data)
                        logger.debug(f"  添加排名: {rank_data['rank']} - {rank_data['team']}")

                except Exception as e:
                    logger.debug(f"  跳过行: {e}")
                    continue

        logger.info(f"✅ 解析到 {len(rankings)} 个FIFA排名")

        return rankings

    def _extract_from_json(self, html_content: str) -> List[Dict]:
        """从页面JSON数据中提取FIFA排名"""
        logger.info("🔍 尝试从JSON数据中提取FIFA排名...")

        rankings = []

        # 查找嵌入的JSON数据
        import re
        json_patterns = [
            r'window\.__FIFA_BFF_STATE__\s*=\s*(\{.*?\});',
            r'window\.__INITIAL_STATE__\s*=\s*(\{.*?\});',
            r'__NUXT__\s*=\s*(\{.*?\});',
            r'__DATA__\s*=\s*(\{.*?\});',
        ]

        for pattern in json_patterns:
            matches = re.findall(pattern, html_content, re.DOTALL)
            if matches:
                try:
                    json_str = matches[0]
                    data = json.loads(json_str)

                    # 递归查找排名数据
                    def find_rankings(obj):
                        results = []
                        if isinstance(obj, dict):
                            if 'rankings' in obj and isinstance(obj['rankings'], list):
                                return obj['rankings']
                            if 'data' in obj and isinstance(obj['data'], list):
                                return obj['data']
                            if 'teams' in obj and isinstance(obj['teams'], list):
                                return obj['teams']

                            for value in obj.values():
                                results.extend(find_rankings(value))
                        elif isinstance(obj, list):
                            for item in obj:
                                results.extend(find_rankings(item))
                        return results

                    rankings_data = find_rankings(data)

                    if rankings_data:
                        logger.info(f"  从JSON找到 {len(rankings_data)} 条排名数据")

                        for item in rankings_data[:50]:  # 取前50名
                            if isinstance(item, dict):
                                rankings.append({
                                    'rank': str(item.get('position', item.get('rank', ''))),
                                    'team': item.get('name', item.get('team', item.get('country', ''))),
                                    'country': item.get('name', item.get('team', '')),
                                    'points': str(item.get('points', ''))
                                })

                        return rankings[:50]

                except Exception as e:
                    logger.debug(f"  JSON解析失败: {e}")

        logger.warning("⚠️ 未能从JSON中提取到排名数据")
        return []

    def update_teams_with_fifa_rank(self, rankings: List[Dict]) -> int:
        """更新teams表的FIFA排名"""
        if not rankings:
            logger.warning("⚠️ 没有FIFA排名数据可更新")
            return 0

        logger.info(f"\n💾 更新teams表的FIFA排名...")

        updated_count = 0

        try:
            with self.engine.connect() as conn:
                for rank_data in rankings:
                    try:
                        rank = int(rank_data['rank']) if rank_data['rank'].isdigit() else None
                        team_name = rank_data['team'].strip()

                        if not rank or not team_name:
                            continue

                        # 更新teams表
                        conn.execute(
                            text("""
                                UPDATE teams
                                SET fifa_rank = :rank,
                                    updated_at = NOW()
                                WHERE name ILIKE :team_name
                            """),
                            {
                                'rank': rank,
                                'team_name': f'%{team_name}%'
                            }
                        )

                        if conn.rowcount > 0:
                            updated_count += 1
                            logger.info(f"  ✅ {team_name}: FIFA排名 #{rank}")

                    except Exception as e:
                        logger.debug(f"  更新失败 {rank_data}: {e}")
                        continue

                conn.commit()

        except Exception as e:
            logger.error(f"❌ 数据库更新失败: {e}")
            return 0

        logger.info(f"\n✅ 成功更新 {updated_count} 支球队的FIFA排名")
        return updated_count

    async def run(self) -> bool:
        """运行FIFA排名采集"""
        logger.info("🚀 启动FIFA排名采集任务")
        logger.info("="*80)

        try:
            # Step 1: 获取FIFA排名页面
            html_content = await self.fetch_fifa_ranking_page()
            if not html_content:
                return False

            # Step 2: 解析排名数据
            rankings = self.parse_fifa_rankings(html_content)

            if not rankings:
                logger.error("❌ 未能解析到FIFA排名数据")
                return False

            # Step 3: 保存排名数据
            rankings_file = '/tmp/fifa_rankings.json'
            with open(rankings_file, 'w', encoding='utf-8') as f:
                json.dump(rankings[:50], f, indent=2, ensure_ascii=False)

            logger.info(f"💾 已保存FIFA排名到: {rankings_file}")

            # Step 4: 更新teams表（需要先添加fifa_rank字段）
            logger.info(f"\n⚠️ 需要先为teams表添加fifa_rank字段:")
            logger.info("ALTER TABLE teams ADD COLUMN fifa_rank INTEGER;")
            logger.info(f"然后更新 {len(rankings)} 个排名")

            # 显示前20个排名
            logger.info(f"\n🏆 FIFA排名前20位:")
            for i, rank in enumerate(rankings[:20]):
                logger.info(f"  {rank['rank']:>3}. {rank['team']:30} - {rank['points']} 分")

            return True

        except Exception as e:
            logger.error(f"❌ FIFA排名采集失败: {e}")
            import traceback
            traceback.print_exc()
            return False


if __name__ == "__main__":
    fetcher = FIFARankingFetcher()
    success = asyncio.run(fetcher.run())

    if success:
        logger.info("\n🎉 FIFA排名采集完成!")
        exit(0)
    else:
        logger.error("\n❌ FIFA排名采集失败")
        exit(1)
