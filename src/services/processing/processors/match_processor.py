"""
比赛数据处理器 - 重写版本

处理原始比赛数据的清洗、转换和标准化
Match Data Processor - Rewritten Version
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union

import pandas as pd


class MatchProcessor:
    """比赛数据处理器 - 简化版本

    负责原始比赛数据的清洗、转换和标准化处理
    """

    def __init__(self):
        """初始化处理器"""
        self.logger = logging.getLogger(f"processing.{self.__class__.__name__}")
        self.required_fields = {
            "match_id",
            "home_team",
            "away_team",
            "match_date",
            "home_score",
            "away_score"
        }
        self.optional_fields = {
            "venue",
            "competition",
            "season",
            "match_status"
        }

    async def process_raw_match_data(self, raw_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """处理原始比赛数据"""
        processed_matches = []

        for match_data in raw_data:
            try:
                processed_match = await self._process_single_match(match_data)
                if processed_match:
                    processed_matches.append(processed_match)
            except Exception as e:
                self.logger.warning(f"处理比赛数据失败: {e}")
                continue

        return processed_matches

    async def _process_single_match(self, match_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """处理单个比赛数据"""
        # 验证必需字段
        if not await self._validate_required_fields(match_data):
            return None

        # 数据清洗和转换
        processed_data = await self._clean_match_data(match_data)

        # 标准化格式
        standardized_data = await self._standardize_match_data(processed_data)

        return standardized_data

    async def _validate_required_fields(self, match_data: Dict[str, Any]) -> bool:
        """验证必需字段"""
        return all(field in match_data for field in self.required_fields)

    async def _clean_match_data(self, match_data: Dict[str, Any]) -> Dict[str, Any]:
        """清洗比赛数据"""
        cleaned_data = {}

        # 清洗字符串字段
        for field in ["home_team", "away_team", "venue", "competition", "match_status"]:
            if field in match_data:
                cleaned_data[field] = str(match_data[field]).strip()

        # 清洗数值字段
        for field in ["home_score", "away_score"]:
            if field in match_data:
                try:
                    cleaned_data[field] = int(match_data[field])
                except (ValueError, TypeError):
                    cleaned_data[field] = 0

        # 清洗日期字段
        if "match_date" in match_data:
            cleaned_data["match_date"] = await self._parse_date(match_data["match_date"])

        # 清洗其他字段
        for field, value in match_data.items():
            if field not in cleaned_data:
                cleaned_data[field] = value

        return cleaned_data

    async def _parse_date(self, date_value: Union[str, datetime]) -> Optional[datetime]:
        """解析日期字段"""
        if isinstance(date_value, datetime):
            return date_value

        if isinstance(date_value, str):
            # 尝试多种日期格式
            date_formats = [
                "%Y-%m-%d",
                "%Y-%m-%d %H:%M:%S",
                "%d/%m/%Y",
                "%d/%m/%Y %H:%M:%S",
                "%Y%m%d"
            ]

            for fmt in date_formats:
                try:
                    return datetime.strptime(date_value.strip(), fmt)
                except ValueError:
                    continue

        self.logger.warning(f"无法解析日期: {date_value}")
        return None

    async def _standardize_match_data(self, match_data: Dict[str, Any]) -> Dict[str, Any]:
        """标准化比赛数据格式"""
        standardized = {
            "match_id": str(match_data.get("match_id", "")),
            "home_team": str(match_data.get("home_team", "")).title(),
            "away_team": str(match_data.get("away_team", "")).title(),
            "match_date": match_data.get("match_date"),
            "home_score": int(match_data.get("home_score", 0)),
            "away_score": int(match_data.get("away_score", 0)),
            "venue": str(match_data.get("venue", "")).title(),
            "competition": str(match_data.get("competition", "")).title(),
            "season": str(match_data.get("season", "")),
            "match_status": str(match_data.get("match_status", "finished")).lower(),
            "processed_at": datetime.utcnow()
        }

        # 计算衍生字段
        standardized["total_goals"] = standardized["home_score"] + standardized["away_score"]
        standardized["goal_difference"] = standardized["home_score"] - standardized["away_score"]
        standardized["winner"] = await self._determine_winner(
            standardized["home_score"],
            standardized["away_score"]
        )

        return standardized

    async def _determine_winner(self, home_score: int, away_score: int) -> str:
        """确定比赛获胜者"""
        if home_score > away_score:
            return "home"
        elif away_score > home_score:
            return "away"
        else:
            return "draw"

    async def process_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """处理DataFrame格式的比赛数据"""
        try:
            # 转换为字典列表处理
            raw_data = df.to_dict('records')
            processed_data = await self.process_raw_match_data(raw_data)

            # 转换回DataFrame
            if processed_data:
                return pd.DataFrame(processed_data)
            else:
                return pd.DataFrame()

        except Exception as e:
            self.logger.error(f"处理DataFrame失败: {e}")
            return pd.DataFrame()

    async def validate_match_integrity(self, match_data: Dict[str, Any]) -> bool:
        """验证比赛数据完整性"""
        try:
            # 检查比分合理性
            home_score = int(match_data.get("home_score", 0))
            away_score = int(match_data.get("away_score", 0))

            if home_score < 0 or away_score < 0:
                return False

            # 检查日期合理性
            match_date = match_data.get("match_date")
            if match_date and isinstance(match_date, datetime):
                # 检查比赛日期是否在合理范围内
                now = datetime.utcnow()
                if match_date > now + timedelta(days=30):  # 不允许未来30天以上的比赛
                    return False

            return True

        except Exception as e:
            self.logger.warning(f"比赛数据完整性验证失败: {e}")
            return False

    async def get_processing_stats(self, original_count: int, processed_count: int) -> Dict[str, Any]:
        """获取处理统计信息"""
        success_rate = (processed_count / original_count * 100) if original_count > 0 else 0

        return {
            "original_count": original_count,
            "processed_count": processed_count,
            "failed_count": original_count - processed_count,
            "success_rate": round(success_rate, 2),
            "processed_at": datetime.utcnow()
        }

    async def batch_process(self, data_batches: List[List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
        """批量处理多批次数据"""
        all_processed = []
        total_stats = {"original": 0, "processed": 0}

        for i, batch in enumerate(data_batches):
            self.logger.info(f"处理批次 {i+1}/{len(data_batches)}, 数据量: {len(batch)}")

            batch_processed = await self.process_raw_match_data(batch)
            all_processed.extend(batch_processed)

            total_stats["original"] += len(batch)
            total_stats["processed"] += len(batch_processed)

        # 记录整体统计
        stats = await self.get_processing_stats(
            total_stats["original"],
            total_stats["processed"]
        )
        self.logger.info(f"批量处理完成: {stats}")

        return all_processed