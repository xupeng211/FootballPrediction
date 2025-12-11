"""
赔率业务服务层
Odds Business Service Layer

提供赔率数据的业务逻辑处理，连接AbstractFetcher接口和OddsDAO，
实现数据清洗、去重、验证和持久化等核心业务功能。

核心功能:
1. 赔率数据摄取和预处理
2. 数据质量验证和清洗
3. 去重和冲突解决
4. 数据库持久化操作
5. 多数据源集成

作者: Business Logic Team
创建时间: 2025-12-07
版本: 1.0.0
"""

import logging
from datetime import datetime
from typing import Any, Optional

from decimal import Decimal, InvalidOperation

from src.collectors.abstract_fetcher import (
    AbstractFetcher,
    OddsData,
    FetcherFactory,
    FetcherError,
    DataNotFoundError,
    ConnectionError,
)
from src.database.dao.odds_dao import OddsDAO
from src.database.dao.match_dao import MatchDAO
from src.database.dao.exceptions import (
    RecordNotFoundError,
    DatabaseConnectionError,
    ValidationError,
    DuplicateRecordError,
)
from src.database.models.odds import Odds

logger = logging.getLogger(__name__)


class OddsIngestionResult:
    """赔率数据摄取结果"""

    def __init__(
        self,
        total_processed: int = 0,
        successful_inserts: int = 0,
        successful_updates: int = 0,
        duplicates_found: int = 0,
        validation_errors: int = 0,
        database_errors: int = 0,
        processing_time_ms: float = 0.0,
    ):
        self.total_processed = total_processed
        self.successful_inserts = successful_inserts
        self.successful_updates = successful_updates
        self.duplicates_found = duplicates_found
        self.validation_errors = validation_errors
        self.database_errors = database_errors
        self.processing_time_ms = processing_time_ms
        self.errors: list[dict[str, Any]] = []

    def add_error(
        self, error_type: str, error_message: str, data: dict[str, Any] = None
    ):
        """记录错误信息"""
        self.errors.append(
            {
                "error_type": error_type,
                "error_message": error_message,
                "data": data or {},
                "timestamp": datetime.now().isoformat(),
            }
        )

    def to_dict(self) -> dict[str, Any]:
        """转换为字典格式"""
        return {
            "total_processed": self.total_processed,
            "successful_inserts": self.successful_inserts,
            "successful_updates": self.successful_updates,
            "duplicates_found": self.duplicates_found,
            "validation_errors": self.validation_errors,
            "database_errors": self.database_errors,
            "processing_time_ms": self.processing_time_ms,
            "success_rate": (self.successful_inserts + self.successful_updates)
            / max(self.total_processed, 1),
            "error_details": self.errors,
        }


class OddsService:
    """
    赔率业务服务类

    作为业务逻辑的中枢，协调数据获取、数据处理和数据持久化。
    """

    def __init__(self, odds_dao: OddsDAO, match_dao: MatchDAO):
        """
        初始化赔率服务

        Args:
            odds_dao: 赔率数据访问对象
            match_dao: 比赛数据访问对象
        """
        self.odds_dao = odds_dao
        self.match_dao = match_dao
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    async def ingest_odds_data(
        self, odds_data_list: list[OddsData]
    ) -> OddsIngestionResult:
        """
        处理赔率数据摄取

        实现数据清洗、去重、验证和持久化的完整流程。

        Args:
            odds_data_list: 待处理的赔率数据列表

        Returns:
            OddsIngestionResult: 处理结果统计信息

        Raises:
            ValidationError: 数据验证失败
            DatabaseConnectionError: 数据库连接错误
        """
        start_time = datetime.now()
        result = OddsIngestionResult()

        self.logger.info(f"开始处理赔率数据摄取，共 {len(odds_data_list)} 条记录")

        try:
            # 预处理数据
            processed_data = await self._preprocess_odds_data(odds_data_list, result)
            result.total_processed = len(processed_data)

            # 批量处理数据
            for odds_data in processed_data:
                try:
                    await self._process_single_odds_record(odds_data, result)
                except Exception as e:
                    self.logger.error(
                        f"处理赔率记录失败: {odds_data.match_id}, error: {e}"
                    )
                    result.database_errors += 1
                    result.add_error("processing_error", str(e), odds_data.dict())

        except Exception as e:
            self.logger.error(f"赔率数据摄取过程发生严重错误: {e}")
            raise DatabaseConnectionError(f"赔率数据摄取失败: {e}")

        finally:
            # 计算处理时间
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            result.processing_time_ms = processing_time

            self.logger.info(f"赔率数据摄取完成: {result.to_dict()}")

        return result

    async def fetch_and_save_odds(
        self, source_name: str, match_id: str
    ) -> OddsIngestionResult:
        """
        从指定数据源获取并保存赔率数据

        使用FetcherFactory创建适配器实例，获取数据后自动处理和保存。

        Args:
            source_name: 数据源名称
            match_id: 比赛ID

        Returns:
            OddsIngestionResult: 处理结果统计信息

        Raises:
            ValidationError: 参数验证失败
            ConnectionError: 数据源连接失败
            DatabaseConnectionError: 数据库操作失败
        """
        self.logger.info(
            f"开始从数据源 '{source_name}' 获取比赛 '{match_id}' 的赔率数据"
        )

        datetime.now()

        try:
            # 验证比赛是否存在
            await self._validate_match_exists(match_id)

            # 创建数据获取器
            fetcher = await self._create_fetcher(source_name)

            # 获取赔率数据
            odds_data_list = await self._fetch_odds_data(fetcher, match_id)

            # 处理和保存数据
            result = await self.ingest_odds_data(odds_data_list)

            # 记录数据源信息
            self.logger.info(
                f"成功从 '{source_name}' 获取并处理了 {len(odds_data_list)} 条赔率记录"
            )

            return result

        except RecordNotFoundError:
            self.logger.warning(f"比赛不存在: {match_id}")
            raise

        except FetcherError as e:
            self.logger.error(
                f"数据获取失败: source={source_name}, match_id={match_id}, error={e}"
            )
            raise ConnectionError(f"无法从数据源 '{source_name}' 获取数据: {e}")

        except Exception as e:
            self.logger.error(
                f"获取并保存赔率数据失败: source={source_name}, match_id={match_id}, error={e}"
            )
            raise DatabaseConnectionError(f"操作失败: {e}")

    async def _validate_match_exists(self, match_id: str) -> bool:
        """
        验证比赛是否存在

        Args:
            match_id: 比赛ID

        Returns:
            bool: 比赛是否存在

        Raises:
            RecordNotFoundError: 比赛不存在
        """
        try:
            # 尝试将match_id转换为整数（如果是字符串ID的话）
            try:
                match_id_int = int(match_id)
                match = await self.match_dao.get(match_id_int)
            except ValueError:
                # 如果不能转换为整数，假设是字符串ID
                match = await self.match_dao.get_by_external_id(match_id)

            if not match:
                raise RecordNotFoundError("Match", match_id)

            return True

        except RecordNotFoundError:
            raise
        except Exception as e:
            self.logger.error(
                f"验证比赛存在性时发生错误: match_id={match_id}, error={e}"
            )
            raise DatabaseConnectionError(f"验证比赛存在性失败: {e}")

    async def _create_fetcher(self, source_name: str) -> AbstractFetcher:
        """
        创建数据获取器实例

        Args:
            source_name: 数据源名称

        Returns:
            AbstractFetcher: 数据获取器实例

        Raises:
            ValidationError: 数据源名称无效
        """
        if not source_name or not source_name.strip():
            raise ValidationError("Fetcher", {"source_name": "数据源名称不能为空"})

        try:
            fetcher = FetcherFactory.create(source_name)
            self.logger.debug(f"成功创建数据获取器: {source_name}")
            return fetcher

        except ValueError as e:
            self.logger.error(
                f"创建数据获取器失败: source_name={source_name}, error={e}"
            )
            raise ValidationError(
                "Fetcher", {"source_name": f"未知的数据源: {source_name}"}
            )
        except Exception as e:
            self.logger.error(
                f"创建数据获取器时发生错误: source_name={source_name}, error={e}"
            )
            raise DatabaseConnectionError(f"创建数据获取器失败: {e}")

    async def _fetch_odds_data(
        self, fetcher: AbstractFetcher, match_id: str
    ) -> list[OddsData]:
        """
        从获取器获取赔率数据

        Args:
            fetcher: 数据获取器实例
            match_id: 比赛ID

        Returns:
            list[OddsData]: 赔率数据列表

        Raises:
            ConnectionError: 数据获取失败
            DataNotFoundError: 数据不存在
        """
        try:
            odds_data_list = await fetcher.fetch_odds(match_id)

            if not odds_data_list:
                self.logger.warning(f"未找到比赛 '{match_id}' 的赔率数据")
                return []

            self.logger.info(f"成功获取到 {len(odds_data_list)} 条赔率记录")
            return odds_data_list

        except DataNotFoundError:
            self.logger.warning(f"数据源中未找到比赛 '{match_id}' 的赔率数据")
            return []
        except Exception as e:
            self.logger.error(f"获取赔率数据失败: match_id={match_id}, error={e}")
            raise ConnectionError(f"获取赔率数据失败: {e}")

    async def _preprocess_odds_data(
        self, odds_data_list: list[OddsData], result: OddsIngestionResult
    ) -> list[OddsData]:
        """
        预处理赔率数据

        执行数据清洗、验证和去重。

        Args:
            odds_data_list: 原始赔率数据列表
            result: 处理结果对象

        Returns:
            list[OddsData]: 处理后的赔率数据列表
        """
        processed_data = []
        seen_records = set()  # 用于去重

        for odds_data in odds_data_list:
            try:
                # 验证数据
                if not self._validate_odds_data(odds_data):
                    result.validation_errors += 1
                    result.add_error(
                        "validation_error", "数据验证失败", odds_data.dict()
                    )
                    continue

                # 创建去重键
                dedupe_key = self._create_deduplication_key(odds_data)

                # 检查重复
                if dedupe_key in seen_records:
                    result.duplicates_found += 1
                    result.add_error(
                        "duplicate_error", "发现重复记录", odds_data.dict()
                    )
                    continue

                seen_records.add(dedupe_key)

                # 清洗和标准化数据
                cleaned_data = await self._clean_odds_data(odds_data)
                processed_data.append(cleaned_data)

            except Exception as e:
                self.logger.error(
                    f"预处理赔率数据失败: {odds_data.match_id}, error={e}"
                )
                result.validation_errors += 1
                result.add_error("preprocessing_error", str(e), odds_data.dict())

        self.logger.info(
            f"预处理完成: 原始 {len(odds_data_list)} 条，处理后 {len(processed_data)} 条"
        )
        return processed_data

    def _validate_odds_data(self, odds_data: OddsData) -> bool:
        """
        验证赔率数据

        Args:
            odds_data: 待验证的赔率数据

        Returns:
            bool: 验证是否通过
        """
        # 基础字段验证
        if not odds_data.match_id or not odds_data.source:
            return False

        # 赔率值验证（至少要有一个有效的赔率值）
        odds_values = [
            odds_data.home_win,
            odds_data.draw,
            odds_data.away_win,
            odds_data.asian_handicap_home,
            odds_data.asian_handicap_away,
            odds_data.over_odds,
            odds_data.under_odds,
        ]

        # 过滤None值并验证剩余的赔率值
        valid_odds = [v for v in odds_values if v is not None]

        if not valid_odds:
            return False

        # 验证赔率值范围（1.0 - 1000.0）
        for odds in valid_odds:
            try:
                odds_float = float(odds)
                if not (1.0 <= odds_float <= 1000.0):
                    return False
            except ValueError:
                return False

        return True

    def _create_deduplication_key(self, odds_data: OddsData) -> str:
        """
        创建去重键

        Args:
            odds_data: 赔率数据

        Returns:
            str: 去重键
        """
        # 使用比赛ID、数据源、博彩公司和市场类型创建唯一键
        bookmaker = odds_data.bookmaker or "unknown"
        market_type = odds_data.market_type or "default"

        return f"{odds_data.match_id}_{odds_data.source}_{bookmaker}_{market_type}"

    async def _clean_odds_data(self, odds_data: OddsData) -> OddsData:
        """
        清洗赔率数据

        Args:
            odds_data: 原始赔率数据

        Returns:
            OddsData: 清洗后的赔率数据
        """
        # 确保时间戳存在
        if not odds_data.timestamp:
            odds_data.timestamp = datetime.now()

        # 标准化博彩公司名称
        if odds_data.bookmaker:
            odds_data.bookmaker = odds_data.bookmaker.strip().title()

        # 标准化市场类型
        if odds_data.market_type:
            odds_data.market_type = odds_data.market_type.strip().lower()

        # 清洗赔率值（移除前导零，格式化等）
        cleaned_data = odds_data.dict(exclude_unset=True)

        for field in [
            "home_win",
            "draw",
            "away_win",
            "asian_handicap_home",
            "asian_handicap_away",
            "over_odds",
            "under_odds",
        ]:
            if field in cleaned_data and cleaned_data[field] is not None:
                try:
                    # 转换为Decimal确保精度
                    decimal_value = Decimal(str(cleaned_data[field]))
                    # 舍入到4位小数
                    cleaned_data[field] = float(
                        decimal_value.quantize(Decimal("0.0001"))
                    )
                except (InvalidOperation, ValueError):
                    # 如果转换失败，保持原值
                    pass

        return OddsData(**cleaned_data)

    async def _process_single_odds_record(
        self, odds_data: OddsData, result: OddsIngestionResult
    ):
        """
        处理单条赔率记录

        检查是否为更新操作，然后执行相应的数据库操作。

        Args:
            odds_data: 赔率数据
            result: 处理结果对象
        """
        try:
            # 检查是否已存在相同记录
            existing_odds = await self._find_existing_odds(odds_data)

            if existing_odds:
                # 更新现有记录
                await self._update_existing_odds(existing_odds, odds_data)
                result.successful_updates += 1
                self.logger.debug(
                    f"更新赔率记录: match_id={odds_data.match_id}, bookmaker={odds_data.bookmaker}"
                )
            else:
                # 创建新记录
                await self._create_new_odds(odds_data)
                result.successful_inserts += 1
                self.logger.debug(
                    f"创建赔率记录: match_id={odds_data.match_id}, bookmaker={odds_data.bookmaker}"
                )

        except DuplicateRecordError:
            result.duplicates_found += 1
            self.logger.warning(f"发现重复赔率记录: match_id={odds_data.match_id}")
        except Exception as e:
            self.logger.error(
                f"处理赔率记录失败: match_id={odds_data.match_id}, error={e}"
            )
            result.database_errors += 1
            result.add_error("database_error", str(e), odds_data.dict())
            raise

    async def _find_existing_odds(self, odds_data: OddsData) -> Optional[Odds]:
        """
        查找现有的赔率记录

        Args:
            odds_data: 赔率数据

        Returns:
            Optional[Odds]: 现有记录或None
        """
        try:
            # 首先尝试通过match_id和bookmaker查找
            if odds_data.bookmaker:
                # 注意：这里需要将match_id转换为整数，因为Odds模型使用Integer类型
                try:
                    match_id_int = int(odds_data.match_id)
                    return await self.odds_dao.get_by_match_and_bookmaker(
                        match_id_int, odds_data.bookmaker
                    )
                except ValueError:
                    # 如果match_id不是整数，记录警告并返回None
                    self.logger.warning(f"match_id不是有效整数: {odds_data.match_id}")
                    return None

            return None

        except Exception as e:
            self.logger.error(f"查找现有赔率记录失败: {e}")
            return None

    async def _update_existing_odds(self, existing_odds: Odds, odds_data: OddsData):
        """
        更新现有赔率记录

        Args:
            existing_odds: 现有赔率记录
            odds_data: 新的赔率数据
        """
        try:
            # 准备更新数据
            update_data = {
                "home_win": odds_data.home_win,
                "draw": odds_data.draw,
                "away_win": odds_data.away_win,
                "asian_handicap": odds_data.asian_handicap_line,
                "over_under": odds_data.over_under_line,
                "last_updated": odds_data.timestamp,
                "updated_at": datetime.now(),
                "is_active": True,
            }

            # 如果有原始数据，更新price_movement字段
            if odds_data.raw_data:
                if existing_odds.price_movement:
                    # 将现有数据添加到历史中
                    price_history = existing_odds.price_movement
                    if isinstance(price_history, dict):
                        price_history["history"] = price_history.get("history", [])
                        price_history["history"].append(
                            {
                                "timestamp": datetime.now().isoformat(),
                                "data": odds_data.raw_data,
                            }
                        )
                        update_data["price_movement"] = price_history
                else:
                    update_data["price_movement"] = {
                        "current": odds_data.raw_data,
                        "history": [],
                    }

            # 执行更新
            await self.odds_dao.update(existing_odds.id, update_data)

        except Exception as e:
            self.logger.error(f"更新赔率记录失败: {e}")
            raise DatabaseConnectionError(f"更新赔率记录失败: {e}")

    async def _create_new_odds(self, odds_data: OddsData):
        """
        创建新的赔率记录

        Args:
            odds_data: 赔率数据
        """
        try:
            # 准备创建数据
            create_data = {
                "match_id": int(odds_data.match_id),  # 确保转换为整数
                "bookmaker": odds_data.bookmaker or odds_data.source,
                "home_win": odds_data.home_win,
                "draw": odds_data.draw,
                "away_win": odds_data.away_win,
                "asian_handicap": odds_data.asian_handicap_line,
                "over_under": odds_data.over_under_line,
                "last_updated": odds_data.timestamp,
                "is_active": True,
                "live_odds": False,  # 默认非实时
                "data_quality_score": 0.8,  # 默认质量分数
                "source_reliability": odds_data.source,
            }

            # 添加原始数据到price_movement
            if odds_data.raw_data:
                create_data["price_movement"] = {
                    "current": odds_data.raw_data,
                    "history": [],
                }

            # 执行创建
            await self.odds_dao.create(create_data)

        except ValueError as e:
            self.logger.error(f"创建赔率记录失败 - 数据转换错误: {e}")
            raise ValidationError(
                "Odds", {"match_id": f"无效的比赛ID: {odds_data.match_id}"}
            )
        except Exception as e:
            self.logger.error(f"创建赔率记录失败: {e}")
            raise DatabaseConnectionError(f"创建赔率记录失败: {e}")


# 导出服务类
__all__ = ["OddsService", "OddsIngestionResult"]
