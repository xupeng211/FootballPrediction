"""
足球预测系统数据处理服务模块

提供数据清洗、处理和特征提取功能。
集成了足球数据清洗器和缺失值处理器。

基于 DATA_DESIGN.md 第4节设计。
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

import pandas as pd

from src.cache import CacheKeyManager, RedisManager
from src.data.processing.football_data_cleaner import FootballDataCleaner
from src.data.processing.missing_data_handler import MissingDataHandler
from src.data.storage.data_lake_storage import DataLakeStorage
from src.database.connection import DatabaseManager
from src.database.models.raw_data import (RawMatchData, RawOddsData,
                                          RawScoresData)

from .base import BaseService


class DataProcessingService(BaseService):
    """
    数据处理服务

    负责足球数据的完整处理流程：
    - 原始数据清洗和标准化
    - 缺失值检测和处理
    - 数据质量验证
    - 特征数据准备
    """

    def __init__(self):
        super().__init__("DataProcessingService")
        self.data_cleaner: Optional[FootballDataCleaner] = None
        self.missing_handler: Optional[MissingDataHandler] = None
        self.data_lake: Optional[DataLakeStorage] = None
        self.db_manager: Optional[DatabaseManager] = None
        self.cache_manager: Optional[RedisManager] = None

    async def initialize(self) -> bool:
        """初始化服务"""
        self.logger.info(f"正在初始化 {self.name}")

        try:
            # 初始化数据清洗器和缺失值处理器
            self.data_cleaner = FootballDataCleaner()
            self.missing_handler = MissingDataHandler()

            # 初始化数据湖存储
            self.data_lake = DataLakeStorage()

            # 初始化数据库连接
            self.db_manager = DatabaseManager()

            # 初始化缓存管理器
            self.cache_manager = RedisManager()

            self.logger.info("数据处理服务初始化完成：清洗器、缺失值处理器、数据湖存储、数据库连接、缓存管理器")
            return True

        except Exception as e:
            self.logger.error(f"初始化数据处理服务失败: {str(e)}")
            return False

    async def shutdown(self) -> None:
        """关闭服务"""
        self.logger.info(f"正在关闭 {self.name}")
        self.data_cleaner = None
        self.missing_handler = None
        self.data_lake = None

        # 关闭数据库连接
        if self.db_manager:
            await self.db_manager.close()
            self.db_manager = None

    async def process_raw_match_data(
        self, raw_data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        处理原始比赛数据

        Args:
            raw_data: 原始比赛数据

        Returns:
            Optional[Dict]: 处理后的数据，失败返回None
        """
        if not self.data_cleaner:
            self.logger.error("数据清洗器未初始化")
            return None

        try:
            # 生成缓存Key
            match_id = raw_data.get("external_match_id")
            if match_id and self.cache_manager:
                cache_key = CacheKeyManager.build_key("match", match_id, "processed")

                # 尝试从缓存获取已处理的数据
                cached_data = await self.cache_manager.aget(cache_key)
                if cached_data:
                    self.logger.debug(f"从缓存获取已处理的比赛数据: {match_id}")
                    return cached_data

            # 第一步：数据清洗
            cleaned_data = await self.data_cleaner.clean_match_data(raw_data)
            if not cleaned_data:
                self.logger.warning("比赛数据清洗失败")
                return None

            # 第二步：处理缺失值
            if self.missing_handler:
                processed_data = await self.missing_handler.handle_missing_match_data(
                    cleaned_data
                )
            else:
                processed_data = cleaned_data

            # 将处理后的数据存入缓存
            if match_id and self.cache_manager and processed_data:
                await self.cache_manager.aset(
                    cache_key, processed_data, cache_type="match_info"
                )

            self.logger.debug(f"成功处理比赛数据: {processed_data.get('external_match_id')}")
            return processed_data

        except Exception as e:
            self.logger.error(f"处理比赛数据失败: {str(e)}")
            return None

    async def process_raw_odds_data(
        self, raw_odds: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        处理原始赔率数据

        Args:
            raw_odds: 原始赔率数据列表

        Returns:
            List[Dict]: 处理后的赔率数据列表
        """
        if not self.data_cleaner:
            self.logger.error("数据清洗器未初始化")
            return []

        try:
            # 清洗赔率数据
            cleaned_odds = await self.data_cleaner.clean_odds_data(raw_odds)

            self.logger.info(f"成功处理 {len(cleaned_odds)} 条赔率数据")
            return cleaned_odds

        except Exception as e:
            self.logger.error(f"处理赔率数据失败: {str(e)}")
            return []

    async def process_features_data(
        self, match_id: int, features_df: pd.DataFrame
    ) -> pd.DataFrame:
        """
        处理特征数据

        Args:
            match_id: 比赛ID
            features_df: 特征数据DataFrame

        Returns:
            pd.DataFrame: 处理后的特征数据
        """
        if not self.missing_handler:
            self.logger.error("缺失值处理器未初始化")
            return features_df

        try:
            # 处理缺失值
            processed_features = await self.missing_handler.handle_missing_features(
                match_id, features_df
            )

            self.logger.debug(f"成功处理比赛 {match_id} 的特征数据")
            return processed_features

        except Exception as e:
            self.logger.error(f"处理特征数据失败: {str(e)}")
            return features_df

    async def process_batch_matches(
        self, raw_matches: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        批量处理比赛数据

        Args:
            raw_matches: 原始比赛数据列表

        Returns:
            List[Dict]: 处理后的比赛数据列表
        """
        processed_matches = []

        for raw_match in raw_matches:
            try:
                processed_match = await self.process_raw_match_data(raw_match)
                if processed_match:
                    processed_matches.append(processed_match)
            except Exception as e:
                self.logger.error(f"批量处理比赛数据时出错: {str(e)}")
                continue

        self.logger.info(f"批量处理完成: {len(processed_matches)}/{len(raw_matches)} 条记录成功")
        return processed_matches

    async def validate_data_quality(
        self, data: Dict[str, Any], data_type: str
    ) -> Dict[str, Any]:
        """
        验证数据质量

        Args:
            data: 待验证的数据
            data_type: 数据类型（match/odds/features）

        Returns:
            Dict: 质量检查结果
        """
        quality_report = {
            "data_type": data_type,
            "is_valid": True,
            "issues": [],
            "warnings": [],
        }

        try:
            if data_type == "match":
                # 检查比赛数据必需字段
                required_fields = [
                    "external_match_id",
                    "home_team_id",
                    "away_team_id",
                    "match_time",
                ]
                for field in required_fields:
                    if not data.get(field):
                        quality_report["issues"].append(
                            f"Missing required field: {field}"
                        )
                        quality_report["is_valid"] = False

                # 检查比分合理性
                home_score = data.get("home_score")
                away_score = data.get("away_score")
                if home_score is not None and away_score is not None:
                    if home_score < 0 or away_score < 0:
                        quality_report["issues"].append("Negative scores detected")
                        quality_report["is_valid"] = False
                    elif home_score > 20 or away_score > 20:
                        quality_report["warnings"].append(
                            "Unusually high scores detected"
                        )

            elif data_type == "odds":
                # 检查赔率数据
                outcomes = data.get("outcomes", [])
                if not outcomes:
                    quality_report["issues"].append("No odds outcomes found")
                    quality_report["is_valid"] = False
                else:
                    for outcome in outcomes:
                        price = outcome.get("price")
                        if not price or price < 1.01:
                            quality_report["issues"].append(
                                f"Invalid odds price: {price}"
                            )
                            quality_report["is_valid"] = False

            return quality_report

        except Exception as e:
            self.logger.error(f"数据质量验证失败: {str(e)}")
            quality_report["issues"].append(f"Validation error: {str(e)}")
            quality_report["is_valid"] = False
            return quality_report

    # 保留原有方法以保持向后兼容
    async def process_text(self, text: str) -> Dict[str, Any]:
        """处理文本数据（向后兼容）"""
        return {
            "processed_text": text.strip(),
            "word_count": len(text.split()),
            "character_count": len(text),
        }

    async def process_batch(self, data_list: List[Any]) -> List[Dict[str, Any]]:
        """批量处理数据（向后兼容）"""
        results: List[Any] = []
        for data in data_list:
            if isinstance(data, str):
                result = await self.process_text(data)
                results.append(result)
        return results

    async def process_bronze_to_silver(self, batch_size: int = 100) -> Dict[str, int]:
        """
        将Bronze层数据处理到Silver层

        从Bronze层读取未处理的数据，经过清洗和缺失值处理后，
        写入Silver层，并标记Bronze数据为已处理。

        Args:
            batch_size: 批处理大小

        Returns:
            Dict[str, int]: 处理结果统计
        """
        if not all(
            [self.data_cleaner, self.missing_handler, self.data_lake, self.db_manager]
        ):
            self.logger.error("数据处理服务未完全初始化")
            return {"error": 1}

        results = {
            "processed_matches": 0,
            "processed_odds": 0,
            "processed_scores": 0,
            "errors": 0,
        }

        try:
            # 处理比赛数据
            matches_processed = await self._process_raw_matches_bronze_to_silver(
                batch_size
            )
            results["processed_matches"] = matches_processed

            # 处理赔率数据
            odds_processed = await self._process_raw_odds_bronze_to_silver(batch_size)
            results["processed_odds"] = odds_processed

            # 处理比分数据
            scores_processed = await self._process_raw_scores_bronze_to_silver(
                batch_size
            )
            results["processed_scores"] = scores_processed

            self.logger.info(f"Bronze到Silver层处理完成: {results}")
            return results

        except Exception as e:
            self.logger.error(f"Bronze到Silver层处理失败: {str(e)}")
            results["errors"] += 1
            return results

    async def _process_raw_matches_bronze_to_silver(self, batch_size: int) -> int:
        """处理原始比赛数据：从Bronze到Silver层"""
        processed_count = 0

        try:
            # 从数据库获取未处理的原始比赛数据
            if self.db_manager is None:
                raise RuntimeError("Database manager not initialized")
            with self.db_manager.get_session() as session:
                raw_matches = (
                    session.query(RawMatchData)
                    .filter(RawMatchData.processed.is_(False))
                    .limit(batch_size)
                    .all()
                )

                if not raw_matches:
                    self.logger.debug("没有未处理的比赛数据")
                    return 0

                processed_matches = []

                for raw_match in raw_matches:
                    try:
                        # 清洗比赛数据
                        if self.data_cleaner is None:
                            raise RuntimeError("Data cleaner not initialized")
                        cleaned_data = await self.data_cleaner.clean_match_data(
                            raw_match.raw_data
                        )

                        if not cleaned_data:
                            self.logger.warning(f"比赛数据清洗失败: {raw_match.id}")
                            continue

                        # 处理缺失值
                        if self.missing_handler is None:
                            raise RuntimeError("Missing data handler not initialized")
                        final_data = (
                            await self.missing_handler.handle_missing_match_data(
                                cleaned_data
                            )
                        )

                        # 添加元数据
                        final_data.update(
                            {
                                "bronze_id": raw_match.id,
                                "original_source": raw_match.data_source,
                                "processed_at": datetime.now().isoformat(),
                            }
                        )

                        processed_matches.append(final_data)

                        # 标记Bronze数据为已处理
                        raw_match.mark_processed()
                        processed_count += 1

                    except Exception as e:
                        self.logger.error(f"处理比赛数据失败 (ID: {raw_match.id}): {str(e)}")
                        continue

                if processed_matches:
                    # 保存到Silver层
                    if self.data_lake is None:
                        raise RuntimeError("Data lake not initialized")
                    await self.data_lake.save_historical_data(
                        table_name="processed_matches", data=processed_matches
                    )

                # 提交数据库事务
                session.commit()

                self.logger.info(f"成功处理 {processed_count} 条比赛数据到Silver层")

        except Exception as e:
            self.logger.error(f"处理比赛数据到Silver层失败: {str(e)}")
            if "session" in locals():
                session.rollback()

        return processed_count

    async def _process_raw_odds_bronze_to_silver(self, batch_size: int) -> int:
        """处理原始赔率数据：从Bronze到Silver层"""
        processed_count = 0

        try:
            # 从数据库获取未处理的原始赔率数据
            if self.db_manager is None:
                raise RuntimeError("Database manager not initialized")
            with self.db_manager.get_session() as session:
                raw_odds_list = (
                    session.query(RawOddsData)
                    .filter(RawOddsData.processed.is_(False))
                    .limit(batch_size)
                    .all()
                )

                if not raw_odds_list:
                    self.logger.debug("没有未处理的赔率数据")
                    return 0

                # 按比赛分组处理赔率数据
                odds_by_match: Dict[int, List[Any]] = {}
                for raw_odds in raw_odds_list:
                    match_id = raw_odds.external_match_id
                    if match_id not in odds_by_match:
                        odds_by_match[match_id] = []
                    odds_by_match[match_id].append(raw_odds)

                all_processed_odds: List[Any] = []

                for match_id, match_odds in odds_by_match.items():
                    try:
                        # 准备批量赔率数据
                        odds_data_list = [odds.raw_data for odds in match_odds]

                        # 清洗赔率数据
                        cleaned_odds = await self.data_cleaner.clean_odds_data(
                            odds_data_list
                        )

                        if not cleaned_odds:
                            self.logger.warning(f"比赛 {match_id} 的赔率数据清洗失败")
                            continue

                        # 添加元数据
                        for i, cleaned_odd in enumerate(cleaned_odds):
                            if i < len(match_odds):
                                cleaned_odd.update(
                                    {
                                        "bronze_id": match_odds[i].id,
                                        "original_source": match_odds[i].data_source,
                                        "processed_at": datetime.now().isoformat(),
                                    }
                                )

                        all_processed_odds.extend(cleaned_odds)

                        # 标记所有相关Bronze数据为已处理
                        for raw_odds in match_odds:
                            raw_odds.mark_processed()
                            processed_count += 1

                    except Exception as e:
                        self.logger.error(f"处理比赛 {match_id} 的赔率数据失败: {str(e)}")
                        continue

                if all_processed_odds:
                    # 保存到Silver层
                    await self.data_lake.save_historical_data(
                        table_name="processed_odds", data=all_processed_odds
                    )

                # 提交数据库事务
                session.commit()

                self.logger.info(f"成功处理 {processed_count} 条赔率数据到Silver层")

        except Exception as e:
            self.logger.error(f"处理赔率数据到Silver层失败: {str(e)}")
            if "session" in locals():
                session.rollback()

        return processed_count

    async def _process_raw_scores_bronze_to_silver(self, batch_size: int) -> int:
        """处理原始比分数据：从Bronze到Silver层"""
        processed_count = 0

        try:
            # 从数据库获取未处理的原始比分数据
            with self.db_manager.get_session() as session:
                raw_scores_list = (
                    session.query(RawScoresData)
                    .filter(RawScoresData.processed.is_(False))
                    .limit(batch_size)
                    .all()
                )

                if not raw_scores_list:
                    self.logger.debug("没有未处理的比分数据")
                    return 0

                processed_scores = []

                for raw_scores in raw_scores_list:
                    try:
                        # 验证比分数据
                        score_info = raw_scores.get_score_info()
                        if not score_info:
                            self.logger.warning(f"比分数据无效: {raw_scores.id}")
                            continue

                        # 构建清洗后的比分数据
                        cleaned_score_data = {
                            "external_match_id": raw_scores.external_match_id,
                            "home_score": self.data_cleaner._validate_score(
                                score_info.get("home_score")
                            ),
                            "away_score": self.data_cleaner._validate_score(
                                score_info.get("away_score")
                            ),
                            "half_time_home": self.data_cleaner._validate_score(
                                score_info.get("half_time_home")
                            ),
                            "half_time_away": self.data_cleaner._validate_score(
                                score_info.get("half_time_away")
                            ),
                            "match_status": self.data_cleaner._standardize_match_status(
                                score_info.get("status")
                            ),
                            "match_minute": score_info.get("minute"),
                            "events": score_info.get("events", []),
                            "is_live": raw_scores.is_live,
                            "is_finished": raw_scores.is_finished,
                            # 元数据
                            "bronze_id": raw_scores.id,
                            "original_source": raw_scores.data_source,
                            "processed_at": datetime.now().isoformat(),
                            "collected_at": raw_scores.collected_at.isoformat(),
                        }

                        processed_scores.append(cleaned_score_data)

                        # 标记Bronze数据为已处理
                        raw_scores.mark_processed()
                        processed_count += 1

                    except Exception as e:
                        self.logger.error(f"处理比分数据失败 (ID: {raw_scores.id}): {str(e)}")
                        continue

                if processed_scores:
                    # 保存到Silver层（可以考虑单独建一个processed_scores表）
                    await self.data_lake.save_historical_data(
                        table_name="processed_matches",  # 合并到matches表中
                        data=processed_scores,
                    )

                # 提交数据库事务
                session.commit()

                self.logger.info(f"成功处理 {processed_count} 条比分数据到Silver层")

        except Exception as e:
            self.logger.error(f"处理比分数据到Silver层失败: {str(e)}")
            if "session" in locals():
                session.rollback()

        return processed_count

    async def get_bronze_layer_status(self) -> Dict[str, Any]:
        """
        获取Bronze层数据状态

        Returns:
            Dict: Bronze层数据统计信息
        """
        if not self.db_manager:
            return {"error": "数据库连接未初始化"}

        try:
            with self.db_manager.get_session() as session:
                # 统计各表的处理状态
                match_total = session.query(RawMatchData).count()
                match_processed = (
                    session.query(RawMatchData)
                    .filter(RawMatchData.processed.is_(True))
                    .count()
                )
                match_pending = match_total - match_processed

                odds_total = session.query(RawOddsData).count()
                odds_processed = (
                    session.query(RawOddsData)
                    .filter(RawOddsData.processed.is_(True))
                    .count()
                )
                odds_pending = odds_total - odds_processed

                scores_total = session.query(RawScoresData).count()
                scores_processed = (
                    session.query(RawScoresData)
                    .filter(RawScoresData.processed.is_(True))
                    .count()
                )
                scores_pending = scores_total - scores_processed

                return {
                    "matches": {
                        "total": match_total,
                        "processed": match_processed,
                        "pending": match_pending,
                    },
                    "odds": {
                        "total": odds_total,
                        "processed": odds_processed,
                        "pending": odds_pending,
                    },
                    "scores": {
                        "total": scores_total,
                        "processed": scores_processed,
                        "pending": scores_pending,
                    },
                    "updated_at": datetime.now().isoformat(),
                }

        except Exception as e:
            self.logger.error(f"获取Bronze层状态失败: {str(e)}")
            return {"error": str(e)}
