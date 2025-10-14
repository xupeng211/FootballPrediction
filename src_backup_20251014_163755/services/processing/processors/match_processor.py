# mypy: ignore-errors
"""
比赛数据处理器

处理原始比赛数据的清洗、转换和标准化。
"""

import logging
from datetime import datetime
from typing import List, Optional, Any, Union

import pandas as pd


class MatchProcessor:
    """比赛数据处理器"""

    def __init__(self) -> None:
        """初始化处理器"""
        self.logger = logging.getLogger(f"processing.{self.__class__.__name__}")
        # self.data_cleaner = FootballDataCleaner()  # type: ignore
        self.required_fields = {
            "match_id",
            "home_team",
            "away_team",
            "match_date",
            "competition",
        }
        self.optional_fields = {
            "venue",
            "attendance",
            "referee",
            "weather",
            "home_formation",
            "away_formation",
        }

    async def process_raw_match_data(
        self,
        raw_data: Union[Dict[str, Any], List[Dict[str, Any]  # type: ignore
    ) -> Optional[Union[Dict[str, Any], pd.DataFrame]:  # type: ignore
        """
        处理原始比赛数据

        Args:
            raw_data: 原始比赛数据（字典或字典列表）

        Returns:
            处理后的数据
        """
        try:
            if isinstance(raw_data, list):
                # 批量处理
                results: List[Any] = {}]  # type: ignore
                for item in raw_data:
                    processed = await self._process_single_match_data(item)
                    if processed:
                        results.append(processed)
                return pd.DataFrame(results) if results else None  # type: ignore
            else:
                # 单个处理
                return await self._process_single_match_data(raw_data)

        except (ValueError, TypeError, AttributeError, KeyError, RuntimeError) as e:
            self.logger.error(f"处理原始比赛数据失败: {e}", exc_info=True)
            return None

    async def _process_single_match_data(
        self,
        raw_data: Dict[str, Any],  # type: ignore
    ) -> Optional[Dict[str, Any]:  # type: ignore
        """
        处理单个比赛数据

        Args:
            raw_data: 原始比赛数据

        Returns:
            处理后的数据
        """
        try:
            # 1. 数据验证
            if not await self._validate_match_data(raw_data):
                return None

            # 2. 数据清洗
            cleaneddata= await self._clean_match_data(raw_data)

            # 3. 数据标准化
            standardizeddata= await self._standardize_match_data(cleaned_data)

            # 4. 添加派生字段
            enriched_data = await self._enrich_match_data(standardized_data)

            return enriched_data

        except (ValueError, TypeError, AttributeError, KeyError, RuntimeError) as e:
            self.logger.error(f"处理单个比赛数据失败: {e}", exc_info=True)
            return None

    async def _validate_match_data(self, data: Dict[str, Any]) -> bool:  # type: ignore
        """
        验证比赛数据

        Args:
            data: 原始数据

        Returns:
            是否验证通过
        """
        # 检查必需字段
        missing_fields = self.required_fields - set(data.keys())
        if missing_fields:
            self.logger.warning(f"缺少必需字段: {missing_fields}")
            return False

        # 验证数据类型
        if not isinstance(data.get("match_date"), (str, datetime)):  # type: ignore
            self.logger.error("match_date 必须是字符串或 datetime 对象")
            return False

        # 验证队伍名称
        home_team = data.get("home_team")
        away_team = data.get("away_team")
        if not home_team or not away_team or home_team == away_team:
            self.logger.error("无效的队伍信息")
            return False

        return True

    async def _clean_match_data(self, data: Dict[str, Any]) -> Dict[str, Any]:  # type: ignore
        """
        清洗比赛数据

        Args:
            data: 原始数据

        Returns:
            清洗后的数据
        """
        cleaned = data.copy()

        # 清洗队伍名称
        cleaned["home_team"] = self._clean_team_name(cleaned.get("home_team", ""))
        cleaned["away_team"] = self._clean_team_name(cleaned.get("away_team", ""))

        # 清洗比赛日期
        cleaned["match_date"] = self._clean_match_date(cleaned.get("match_date"))

        # 清洗比分
        if "home_score" in cleaned:
            cleaned["home_score"] = self._clean_score(cleaned["home_score"])
        if "away_score" in cleaned:
            cleaned["away_score"] = self._clean_score(cleaned["away_score"])

        # 清洗其他字段
        for field in ["venue", "referee", "competition"]:
            if field in cleaned:
                cleaned[field] = self._clean_text_field(cleaned[field])

        return cleaned

    async def _standardize_match_data(self, data: Dict[str, Any]) -> Dict[str, Any]:  # type: ignore
        """
        标准化比赛数据

        Args:
            data: 清洗后的数据

        Returns:
            标准化后的数据
        """
        standardized = data.copy()

        # 标准化日期格式
        if isinstance(standardized.get("match_date"), str):
            standardized["match_date"] = datetime.fromisoformat(  # type: ignore
                standardized["match_date"]
            )

        # 标准化队伍名称（统一大小写）
        standardized["home_team"] = standardized["home_team"].strip().title()
        standardized["away_team"] = standardized["away_team"].strip().title()

        # 标准化竞赛名称
        if "competition" in standardized:
            standardized["competition"] = standardized["competition"].strip().upper()

        # 添加处理时间戳
        standardized["processed_at"] = datetime.utcnow()  # type: ignore

        return standardized

    async def _enrich_match_data(self, data: Dict[str, Any]) -> Dict[str, Any]:  # type: ignore
        """
        丰富比赛数据

        Args:
            data: 标准化后的数据

        Returns:
            丰富后的数据
        """
        enriched = data.copy()

        # 添加比赛ID（如果没有）
        if "match_id" not in enriched:
            enriched["match_id"] = self._generate_match_id(
                enriched["home_team"],
                enriched["away_team"],
                enriched["match_date"],
            )

        # 添加赛季信息
        enriched["season"] = self._extract_season(enriched["match_date"])

        # 添加比赛日
        enriched["match_day"] = enriched["match_date"].weekday()

        # 添加月份
        enriched["match_month"] = enriched["match_date"].month

        return enriched

    def _clean_team_name(self, team_name: str) -> str:
        """清洗队伍名称"""
        if not team_name:
            return ""
        # 移除特殊字符和多余空格
        return " ".join(team_name.strip().split())

    def _clean_match_date(self, date_value: Any) -> datetime:  # type: ignore
        """清洗比赛日期"""
        if isinstance(date_value, datetime):  # type: ignore
            return date_value
        elif isinstance(date_value, str):
            # 尝试多种日期格式
            formats = [
                "%Y-%m-%d %H:%M:%S",
                "%Y-%m-%d",
                "%d/%m/%Y",
                "%d-%m-%Y",
            ]
            for fmt in formats:
                try:
                    return datetime.strptime(date_value, fmt)  # type: ignore
                except ValueError:
                    continue
            raise ValueError(f"无法解析日期: {date_value}")
        else:
            raise ValueError(f"无效的日期类型: {type(date_value)}")

    def _clean_score(self, score: Any) -> Optional[int]:  # type: ignore
        """清洗比分"""
        if score is None:
            return None
        if isinstance(score, int):
            return max(0, score)  # 比分不能为负
        if isinstance(score, str):
            try:
                return max(0, int(score))
            except ValueError:
                return None
        return None

    def _clean_text_field(self, value: Any) -> str:  # type: ignore
        """清洗文本字段"""
        if value is None:
            return ""
        if isinstance(value, str):
            return " ".join(value.strip().split())
        return str(value)

    def _generate_match_id(
        self,
        home_team: str,
        away_team: str,
        match_date: datetime,  # type: ignore
    ) -> str:
        """生成比赛ID"""
        # 使用队伍名称和日期生成唯一ID
        team_string = f"{home_team"_{away_team}"
        date_string = match_date.strftime("%Y%m%d")
        return f"{team_string"_{date_string}".replace(" ", "_").lower()

    def _extract_season(self, match_date: datetime) -> int:  # type: ignore
        """提取赛季"""
        # 简单的赛季规则：8月开始的比赛属于下一个赛季
        year = match_date.year
        if match_date.month >= 8:
            return year + 1  # type: ignore
        return year  # type: ignore

    async def process_batch_matches(
        self,
        matches: List[Dict[str, Any],
        batch_size: int = 50,  # type: ignore
    ) -> List[Dict[str, Any]:  # type: ignore
        """
        批量处理比赛数据

        Args:
            matches: 比赛数据列表
            batch_size: 批处理大小

        Returns:
            处理后的比赛数据列表
        """
        processed_matches: List[Any] = {}]  # type: ignore
        total = len(matches)

        self.logger.info(f"开始批量处理 {total} 场比赛，批大小: {batch_size}")

        for i in range(0, total, batch_size):
            batch = matches[i : i + batch_size]
            batch_num = i // batch_size + 1

            self.logger.info(
                f"处理批次 {batch_num}/{(total + batch_size - 1) // batch_size}"
            )

            batch_results: List[Any] = {}]  # type: ignore
            for match in batch:
                processed = await self._process_single_match_data(match)
                if processed:
                    batch_results.append(processed)

            processed_matches.extend(batch_results)

        self.logger.info(
            f"批量处理完成，成功处理 {len(processed_matches)}/{total} 场比赛"
        )
        return processed_matches

    async def detect_duplicate_matches(
        self,
        matches: List[Dict[str, Any]  # type: ignore
    ) -> List[Dict[str, Any]:  # type: ignore
        """
        检测重复的比赛

        Args:
            matches: 比赛数据列表

        Returns:
            重复的比赛列表
        """
        seen_matches = set()
        duplicates: List[Any] = {}]  # type: ignore

        for match in matches:
            # 创建唯一标识
            identifier = (
                match.get("home_team", ""),
                match.get("away_team", ""),
                match.get("match_date"),
            )

            if identifier in seen_matches:
                duplicates.append(match)
            else:
                seen_matches.add(identifier)

        if duplicates:
            self.logger.warning(f"发现 {len(duplicates)} 场重复比赛")

        return duplicates
