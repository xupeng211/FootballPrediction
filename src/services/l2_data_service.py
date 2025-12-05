#!/usr/bin/env python3
"""
L2 数据写入服务
L2 Data Writing Service

负责将FotMob API采集的比赛详情数据写入PostgreSQL数据库
"""

import asyncio
import logging
from datetime import datetime
from typing import List, Optional, Dict, Any
from sqlalchemy import text
from sqlalchemy.orm import selectinload

from src.database.async_manager import get_db_session
from src.collectors.fotmob_api_collector import MatchDetailData

logger = logging.getLogger(__name__)


class L2DataService:
    """L2 数据写入服务"""

    def __init__(self):
        self.logger = logger

    async def save_match_details(self, match_data: MatchDetailData) -> bool:
        """保存单个比赛详情"""
        async with get_db_session() as session:
            try:
                # 构建更新SQL
                update_query = text("""
                    UPDATE matches SET
                        home_score = :home_score,
                        away_score = :away_score,
                        status = :status,
                        match_date = COALESCE(:match_date, match_date),
                        venue = :venue,
                        attendance = :attendance,
                        referee_name = :referee_name,
                        weather = :weather,
                        home_yellow_cards = :home_yellow_cards,
                        away_yellow_cards = :away_yellow_cards,
                        home_red_cards = :home_red_cards,
                        away_red_cards = :away_red_cards,
                        home_team_rating = :home_team_rating,
                        away_team_rating = :away_team_rating,
                        home_avg_player_rating = :home_avg_player_rating,
                        away_avg_player_rating = :away_avg_player_rating,
                        home_big_chances = :home_big_chances,
                        away_big_chances = :away_big_chances,
                        lineups = :lineups,
                        stats = :stats,
                        events = :events,
                        match_metadata = :match_metadata,
                        data_completeness = :data_completeness,
                        updated_at = :updated_at
                    WHERE fotmob_id = :fotmob_id
                    RETURNING id
                """)

                # 提取match_date（从现有数据或使用当前时间）
                existing_date_query = text("SELECT match_date FROM matches WHERE fotmob_id = :fotmob_id")
                existing_result = await session.execute(existing_date_query, {"fotmob_id": match_data.fotmob_id})
                match_date = existing_result.scalar()

                # 执行更新
                result = await session.execute(update_query, {
                    "fotmob_id": match_data.fotmob_id,
                    "home_score": match_data.home_score,
                    "away_score": match_data.away_score,
                    "status": match_data.status,
                    "match_date": match_date,
                    "venue": match_data.venue,
                    "attendance": match_data.attendance,
                    "referee_name": match_data.referee,
                    "weather": match_data.weather,
                    "home_yellow_cards": match_data.home_yellow_cards,
                    "away_yellow_cards": match_data.away_yellow_cards,
                    "home_red_cards": match_data.home_red_cards,
                    "away_red_cards": match_data.away_red_cards,
                    "home_team_rating": match_data.home_team_rating,
                    "away_team_rating": match_data.away_team_rating,
                    "home_avg_player_rating": match_data.home_avg_player_rating,
                    "away_avg_player_rating": match_data.away_avg_player_rating,
                    "home_big_chances": match_data.home_big_chances,
                    "away_big_chances": match_data.away_big_chances,
                    "lineups": match_data.lineups,
                    "stats": match_data.stats,
                    "events": match_data.events,
                    "match_metadata": match_data.match_metadata,
                    "data_completeness": "complete",  # L2完成后标记为complete
                    "updated_at": datetime.now()
                })

                if result.rowcount > 0:
                    self.logger.info(f"✅ 成功更新比赛详情: {match_data.fotmob_id}")
                    return True
                else:
                    self.logger.warning(f"⚠️ 未找到比赛记录: {match_data.fotmob_id}")
                    return False

            except Exception as e:
                self.logger.error(f"❌ 保存比赛详情失败 {match_data.fotmob_id}: {e}")
                await session.rollback()
                return False

    async def save_batch_match_details(self, matches_data: list[MatchDetailData]) -> dict[str, int]:
        """批量保存比赛详情"""
        success_count = 0
        failed_count = 0
        errors = []

        self.logger.info(f"💾 开始批量保存 {len(matches_data)} 场比赛详情")

        for i, match_data in enumerate(matches_data):
            try:
                success = await self.save_match_details(match_data)
                if success:
                    success_count += 1
                else:
                    failed_count += 1
                    errors.append(f"{match_data.fotmob_id}: 未找到比赛记录")
            except Exception as e:
                failed_count += 1
                errors.append(f"{match_data.fotmob_id}: {str(e)}")

            # 每100场记录输出一次进度
            if (i + 1) % 100 == 0:
                self.logger.info(f"📊 进度: {i + 1}/{len(matches_data)}, 成功: {success_count}, 失败: {failed_count}")

        success_rate = success_count / len(matches_data) * 100 if matches_data else 0
        self.logger.info(f"💾 批量保存完成: 成功 {success_count}/{len(matches_data)} ({success_rate:.1f}%)")

        if errors and len(errors) <= 10:
            for error in errors:
                self.logger.warning(f"⚠️ {error}")

        return {
            "total": len(matches_data),
            "success": success_count,
            "failed": failed_count,
            "success_rate": success_rate
        }

    async def get_pending_matches(self, limit: int = 10000) -> list[str]:
        """获取待处理的比赛ID列表"""
        async with get_db_session() as session:
            try:
                query = text("""
                    SELECT fotmob_id
                    FROM matches
                    WHERE data_completeness = 'partial'
                    AND data_source = 'fotmob_v2'
                    AND fotmob_id IS NOT NULL
                    ORDER BY match_date DESC
                    LIMIT :limit
                """)

                result = await session.execute(query, {"limit": limit})
                matches = [row[0] for row in result.fetchall()]

                self.logger.info(f"📊 找到 {len(matches)} 场待处理的比赛")
                return matches

            except Exception as e:
                self.logger.error(f"❌ 查询待处理比赛失败: {e}")
                return []

    async def update_data_completeness_status(self, fotmob_ids: list[str], status: str) -> int:
        """更新数据完整度状态"""
        async with get_db_session() as session:
            try:
                placeholders = ','.join([f":id_{i}" for i in range(len(fotmob_ids))])
                query = text(f"""
                    UPDATE matches
                    SET data_completeness = :status, updated_at = :updated_at
                    WHERE fotmob_id IN ({placeholders})
                """)

                params = {
                    "status": status,
                    "updated_at": datetime.now()
                }

                # 添加参数
                for i, fotmob_id in enumerate(fotmob_ids):
                    params[f"id_{i}"] = fotmob_id

                result = await session.execute(query, params)
                updated_count = result.rowcount

                self.logger.info(f"✅ 更新数据完整度 {status}: {updated_count} 场比赛")
                return updated_count

            except Exception as e:
                self.logger.error(f"❌ 更新数据完整度失败: {e}")
                return 0

    async def get_collection_statistics(self) -> dict[str, Any]:
        """获取采集统计信息"""
        async with get_db_session() as session:
            try:
                # 总体统计
                total_query = text("SELECT COUNT(*) FROM matches")
                total_result = await session.execute(total_query)
                total_count = total_result.scalar()

                # 完整度统计
                completeness_query = text("""
                    SELECT data_completeness, COUNT(*)
                    FROM matches
                    GROUP BY data_completeness
                """)
                completeness_result = await session.execute(completeness_query)
                completeness_stats = {row[0]: row[1] for row in completeness_result.fetchall()}

                # 数据源统计
                source_query = text("""
                    SELECT data_source, COUNT(*)
                    FROM matches
                    GROUP BY data_source
                """)
                source_result = await session.execute(source_query)
                source_stats = {row[0]: row[1] for row in source_result.fetchall()}

                # 比分统计
                scores_query = text("""
                    SELECT
                        COUNT(*) as total,
                        COUNT(CASE WHEN home_score > 0 OR away_score > 0 THEN 1 END) as with_scores,
                        COUNT(CASE WHEN home_score > 0 OR away_score > 0 AND status = 'finished' THEN 1 END) as finished_with_scores
                    FROM matches
                """)
                scores_result = await session.execute(scores_query)
                scores_row = scores_result.fetchone()

                return {
                    "total_matches": total_count,
                    "completeness": completeness_stats,
                    "data_sources": source_stats,
                    "scores": {
                        "total": scores_row[0],
                        "with_scores": scores_row[1],
                        "finished_with_scores": scores_row[2] if scores_row else 0
                    },
                    "collection_time": datetime.now().isoformat()
                }

            except Exception as e:
                self.logger.error(f"❌ 获取统计信息失败: {e}")
                return {}
