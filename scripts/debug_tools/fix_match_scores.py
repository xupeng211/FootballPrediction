#!/usr/bin/env python3
"""
修复比赛比分数据
Fix Match Scores Data

使用FotMob matchDetails API获取正确的比分数据
"""

import asyncio
import sys
import os
import json
from datetime import datetime
import logging
from typing import List, Dict, Any, Optional, Tuple

import httpx
import psycopg2
from psycopg2.extras import RealDictCursor

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# 数据库连接配置
DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "database": "football_prediction",
    "user": "postgres",
    "password": "postgres"
}

# FotMob API配置
FOTMOB_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'application/json',
    'Accept-Language': 'en-GB,en;q=0.9',
    'x-mas': 'eyJib2R5Ijp7InVybCI6Ii9hcGkvZGF0YS9sZWFndWVzP2lkPTg3IiwiY29kZSI6MTc2NTEyMTc0OTUyNSwiZm9vIjoicHJvZHVjdGlvbjo0MjhmYTAzNTVmMDljYTg4Zjk3YjE3OGViNWE3OWVmMGNmYmQwZGZjIn0sInNpZ25hdHVyZSI6IkIwQzkyMzkxMTM4NTdCNUFBMjk5Rjc5M0QxOTYwRkZCIn0=',
    'x-foo': 'eyJmb28iOiJwcm9kdWN0aW9uOjQyOGZhMDM1NWYwOWNhODhmOTdiMTc4ZWI1YTc5ZWYwY2ZiZDBkZmMiLCJ0aW1lc3RhbXAiOjE3NjUxMjE4MTJ9'
}

class MatchScoreFixer:
    """比赛比分修复器"""

    def __init__(self):
        self.client = None
        self.db_conn = None

    async def initialize(self):
        """初始化连接"""
        self.client = httpx.AsyncClient(timeout=30)
        self.db_conn = psycopg2.connect(**DB_CONFIG)
        logger.info("✅ 比分修复器初始化完成")

    async def close(self):
        """关闭连接"""
        if self.client:
            await self.client.aclose()
        if self.db_conn:
            self.db_conn.close()
        logger.info("✅ 比分修复器关闭完成")

    async def get_match_details(self, fotmob_id: str) -> Optional[dict[str, Any]]:
        """获取比赛详情数据"""
        api_url = f"https://www.fotmob.com/api/matchDetails?matchId={fotmob_id}"

        try:
            response = await self.client.get(api_url, headers=FOTMOB_HEADERS)

            if response.status_code == 200:
                data = response.json()
                return data
            else:
                logger.error(f"❌ 获取比赛 {fotmob_id} 详情失败: HTTP {response.status_code}")
                return None

        except Exception as e:
            logger.error(f"❌ 获取比赛 {fotmob_id} 详情异常: {e}")
            return None

    def extract_match_score(self, match_details: dict[str, Any]) -> Optional[tuple[int, int]]:
        """从比赛详情中提取比分"""
        try:
            header = match_details.get('header', {})
            teams = header.get('teams', [])

            if len(teams) >= 2:
                home_score = teams[0].get('score', 0)
                away_score = teams[1].get('score', 0)

                # 验证比分是否有效
                if home_score is not None and away_score is not None:
                    if isinstance(home_score, int) and isinstance(away_score, int):
                        return home_score, away_score
                    else:
                        logger.warning(f"⚠️ 比分不是整数类型: {home_score}-{away_score}")
                        return None
                else:
                    logger.warning(f"⚠️ 比分为None: {home_score}-{away_score}")
                    return None
            else:
                logger.warning(f"⚠️ teams数据结构异常: {len(teams)} 个队伍")
                return None

        except Exception as e:
            logger.error(f"❌ 提取比分异常: {e}")
            return None

    def get_matches_to_fix(self) -> list[dict[str, Any]]:
        """获取需要修复比分的比赛"""
        try:
            with self.db_conn.cursor(cursor_factory=RealDictCursor) as cur:
                # 获取所有状态为Finished但比分为0-0的比赛
                cur.execute("""
                    SELECT fotmob_id, home_team_id, away_team_id, status, season
                    FROM matches
                    WHERE (status = 'Finished' OR status = 'FT')
                    AND (home_score = 0 AND away_score = 0)
                    AND fotmob_id IS NOT NULL
                    ORDER BY season DESC
                """)

                matches = cur.fetchall()
                logger.info(f"📊 找到 {len(matches)} 场需要修复比分的比赛")
                return list(matches)

        except Exception as e:
            logger.error(f"❌ 获取需要修复的比赛失败: {e}")
            return []

    def update_match_score(self, fotmob_id: str, home_score: int, away_score: int) -> bool:
        """更新比赛比分"""
        try:
            # 重新建立数据库连接以确保连接有效
            conn = psycopg2.connect(**DB_CONFIG)
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE matches
                    SET home_score = %s, away_score = %s, updated_at = NOW()
                    WHERE fotmob_id = %s
                """, (home_score, away_score, fotmob_id))

                if cur.rowcount > 0:
                    logger.info(f"✅ 更新比分: {fotmob_id} -> {home_score}-{away_score}")
                    conn.commit()
                    return True
                else:
                    logger.warning(f"⚠️ 未找到比赛记录: {fotmob_id}")
                    conn.commit()
                    return False

        except Exception as e:
            logger.error(f"❌ 更新比分失败: {e}")
            return False
        finally:
            if 'conn' in locals():
                conn.close()

    async def fix_match_scores(self) -> dict[str, Any]:
        """修复所有比赛比分"""
        logger.info("🔄 开始修复比赛比分...")

        # 获取需要修复的比赛
        matches_to_fix = self.get_matches_to_fix()
        if not matches_to_fix:
            logger.info("✅ 没有需要修复比分的比赛")
            return {"success": True, "total_matches": 0, "fixed_matches": 0}

        total_matches = len(matches_to_fix)
        fixed_matches = 0
        failed_matches = 0

        logger.info(f"🎯 目标修复 {total_matches} 场比赛比分")

        # 批量处理比赛
        batch_size = 10  # 避免过快的API请求
        for i in range(0, total_matches, batch_size):
            batch = matches_to_fix[i:i + batch_size]
            logger.info(f"🔄 处理批次 {i//batch_size + 1}/{(total_matches-1)//batch_size + 1}")

            for match in batch:
                fotmob_id = match['fotmob_id']
                season = match['season']

                try:
                    # 获取比赛详情
                    match_details = await self.get_match_details(fotmob_id)
                    if not match_details:
                        failed_matches += 1
                        continue

                    # 提取比分
                    score = self.extract_match_score(match_details)
                    if not score:
                        logger.warning(f"⚠️ 无法提取比分: {fotmob_id}")
                        failed_matches += 1
                        continue

                    home_score, away_score = score

                    # 更新数据库
                    if self.update_match_score(fotmob_id, home_score, away_score):
                        fixed_matches += 1

                        # 只显示前10场的详细信息
                        if fixed_matches <= 10:
                            logger.info(f"✅ [{season}] {fotmob_id}: {home_score}-{away_score}")

                except Exception as e:
                    logger.error(f"❌ 处理比赛 {fotmob_id} 失败: {e}")
                    failed_matches += 1

            # 批次间延迟
            if i + batch_size < total_matches:
                await asyncio.sleep(1)

        # 提交所有更改
        try:
            self.db_conn.commit()
            logger.info("✅ 所有比分更新已提交到数据库")
        except Exception as e:
            logger.error(f"❌ 提交更改失败: {e}")
            self.db_conn.rollback()

        result = {
            "success": True,
            "total_matches": total_matches,
            "fixed_matches": fixed_matches,
            "failed_matches": failed_matches,
            "success_rate": round(fixed_matches / total_matches * 100, 2) if total_matches > 0 else 0
        }

        logger.info("🎊 **比分修复完成！**")
        logger.info(f"   📊 总比赛数: {total_matches}")
        logger.info(f"   ✅ 修复成功: {fixed_matches}")
        logger.info(f"   ❌ 修复失败: {failed_matches}")
        logger.info(f"   📈 成功率: {result['success_rate']}%")

        return result

async def main():
    """主函数"""
    logger.info("🚀 启动比赛比分修复任务")
    logger.info("🎯 目标：为完赛比赛添加正确的比分数据")

    fixer = MatchScoreFixer()
    try:
        await fixer.initialize()

        # 执行比分修复
        result = await fixer.fix_match_scores()

        if result["success"]:
            logger.info(f"✅ 比分修复任务完成: {result['fixed_matches']}/{result['total_matches']} 场比赛已修复")
            return 0
        else:
            logger.error("❌ 比分修复任务失败")
            return 1

    finally:
        await fixer.close()

    return 0

if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        logger.info("⚠️ 用户中断")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ 程序异常退出: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
