"""
Titan007 具体采集器实现

包含欧赔、亚盘、大小球三个具体采集器，继承自 BaseTitanCollector。
每个采集器负责解析特定类型的赔率数据。
"""

from typing import Optional, Dict, Any, List
import logging
from datetime import datetime

from src.collectors.titan.base_collector import BaseTitanCollector
from src.collectors.titan.constants import CompanyID, TitanFieldMapping
from src.schemas.titan import EuroOddsRecord, AsianHandicapRecord, OverUnderRecord

logger = logging.getLogger(__name__)


class TitanEuroCollector(BaseTitanCollector):
    """
    Titan007 欧赔采集器

    欧赔 (European Odds) 也叫 1X2 胜平负盘口：
    - h (home): 主胜赔率
    - d (draw): 平局赔率
    - a (away): 客胜赔率

    Example:
        >>> async with TitanEuroCollector() as collector:
        >>>     odds = await collector.fetch_euro_odds("2971465", CompanyID.BET365)
        >>>     print(f"主胜: {odds['home_win']}, 平局: {odds['draw']}, 客胜: {odds['away_win']}")
    """

    async def fetch_euro_odds(
        self, match_id: str, company_id: Optional[CompanyID] = None
    ) -> Optional[Dict[str, Any]]:
        """
        获取欧赔数据

        Args:
            match_id: 比赛ID
            company_id: 指定博彩公司ID，None表示获取所有公司

        Returns:
            Dict[str, Any]: 欧赔数据，包含字段：
                - match_id: 比赛ID
                - company_id: 公司ID
                - company_name: 公司名称
                - home_win: 主胜赔率
                - draw: 平局赔率
                - away_win: 客胜赔率
                - update_time: 更新时间

        Raises:
            TitanNetworkError: 网络请求错误
            TitanParsingError: 数据解析错误
            TitanScrapingError: 反爬拦截
            TitanRateLimitError: 触发限流

        Example:
            >>> collector = TitanEuroCollector()
            >>> odds = await collector.fetch_euro_odds("2971465", CompanyID.BET365)
            >>> print(f"Bet365主胜赔率: {odds['home_win']}")
        """
        params = {"matchid": match_id}
        if company_id:
            params["companyid"] = int(company_id)

        try:
            # 调用基类的 _fetch_json 方法
            response_data = await self._fetch_json("/euro", params)

            # 解析欧赔数据
            return self._parse_euro_response(response_data, match_id, company_id)

        except Exception as e:
            logger.error(
                f"获取欧赔数据失败: match_id={match_id}, company_id={company_id}, error={str(e)}"
            )
            raise

    async def fetch_euro_odds_bulk(
        self, match_id: str, company_ids: List[CompanyID]
    ) -> List[Dict[str, Any]]:
        """
        批量获取多个公司的欧赔数据

        Args:
            match_id: 比赛ID
            company_ids: 博彩公司ID列表

        Returns:
            List[Dict[str, Any]]: 多个公司的欧赔数据列表

        Example:
            >>> companies = [CompanyID.BET365, CompanyID.WILLIAM_HILL]
            >>> odds_list = await collector.fetch_euro_odds_bulk("2971465", companies)
            >>> for odds in odds_list:
            >>>     print(f"{odds['company_name']}: {odds['home_win']}")
        """
        params = {"matchid": match_id}

        try:
            # 调用基类的 _fetch_json 方法
            response_data = await self._fetch_json("/euro", params)

            # 解析批量欧赔数据
            return self._parse_euro_bulk_response(response_data, match_id, company_ids)

        except Exception as e:
            logger.error(
                f"批量获取欧赔数据失败: match_id={match_id}, companies={company_ids}, error={str(e)}"
            )
            raise

    def _safe_parse_float(self, value: Any) -> Optional[float]:
        """
        安全地解析浮点数

        Args:
            value: 要解析的值

        Returns:
            Optional[float]: 解析后的浮点数，失败返回 None
        """
        if value is None or value == "":
            return None

        try:
            return float(value)
        except (ValueError, TypeError):
            logger.warning(f"无法解析为浮点数: {value}")
            return None

    def _parse_euro_response(
        self,
        response_data: Dict[str, Any],
        match_id: str,
        company_id: Optional[CompanyID] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        解析单个欧赔响应

        Args:
            response_data: API响应数据
            match_id: 比赛ID
            company_id: 指定的公司ID

        Returns:
            Optional[Dict[str, Any]]: 解析后的欧赔数据
        """
        if not response_data or "data" not in response_data:
            return None

        data_list = response_data.get("data", [])
        if not data_list:
            return None

        # 查找指定公司的数据
        target_data = None
        if company_id:
            for item in data_list:
                if item.get("cid") == int(company_id):
                    target_data = item
                    break
        else:
            # 如果没有指定公司，返回第一个
            target_data = data_list[0]

        if not target_data:
            return None

        # 解析字段
        return self._extract_euro_fields(target_data, match_id)

    def _parse_euro_bulk_response(
        self, response_data: Dict[str, Any], match_id: str, company_ids: List[CompanyID]
    ) -> List[Dict[str, Any]]:
        """
        解析批量欧赔响应

        Args:
            response_data: API响应数据
            match_id: 比赛ID
            company_ids: 需要的公司ID列表

        Returns:
            List[Dict[str, Any]]: 解析后的欧赔数据列表
        """
        if not response_data or "data" not in response_data:
            return []

        data_list = response_data.get("data", [])
        if not data_list:
            return []

        results = []
        company_id_set = {int(cid) for cid in company_ids}

        for item in data_list:
            if item.get("cid") in company_id_set:
                parsed_data = self._extract_euro_fields(item, match_id)
                if parsed_data:
                    results.append(parsed_data)

        return results

    def _extract_euro_fields(
        self, item: Dict[str, Any], match_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        提取欧赔字段

        Args:
            item: 单个数据项
            match_id: 比赛ID

        Returns:
            Optional[Dict[str, Any]]: 提取后的数据
        """
        try:
            # 获取公司信息
            company_id = item.get("cid")
            company_name = item.get("cname", "Unknown")

            # 获取赔率字段，使用 TitanFieldMapping
            h_field = TitanFieldMapping.get_field_name("EUROPEAN", "home_win")  # "h"
            d_field = TitanFieldMapping.get_field_name("EUROPEAN", "draw")  # "d"
            a_field = TitanFieldMapping.get_field_name("EUROPEAN", "away_win")  # "a"

            # 提取赔率值，处理可能的缺失或无效值
            home_win = self._safe_parse_float(item.get(h_field))
            draw = self._safe_parse_float(item.get(d_field))
            away_win = self._safe_parse_float(item.get(a_field))

            # 如果所有赔率都缺失，返回 None
            if home_win is None and draw is None and away_win is None:
                return None

            return {
                "match_id": match_id,
                "company_id": company_id,
                "company_name": company_name,
                "home_win": home_win,
                "draw": draw,
                "away_win": away_win,
                "update_time": item.get("utime"),
            }

        except Exception as e:
            logger.warning(f"提取欧赔字段失败: {item}, error={str(e)}")
            return None

    def to_dto(
        self, raw_data: Dict[str, Any], match_id: str
    ) -> Optional[EuroOddsRecord]:
        """
        将原始API数据转换为标准欧赔DTO

        Args:
            raw_data: Titan API返回的原始数据
            match_id: 比赛ID

        Returns:
            Optional[EuroOddsRecord]: 标准化的欧赔DTO
        """
        try:
            # 提取必要字段
            company_id = raw_data.get("cid")
            company_name = raw_data.get("cname", "")
            home_win = self._safe_parse_float(raw_data.get("h"))
            draw = self._safe_parse_float(raw_data.get("d"))
            away_win = self._safe_parse_float(raw_data.get("a"))

            # 验证必要字段
            if not all([company_id, company_name, home_win, draw, away_win]):
                logger.warning(f"欧赔数据不完整: {raw_data}")
                return None

            # 解析更新时间
            update_time_str = raw_data.get("utime", "")
            if update_time_str:
                try:
                    last_updated = datetime.strptime(
                        update_time_str, "%Y-%m-%d %H:%M:%S"
                    )
                except ValueError:
                    last_updated = datetime.now()
            else:
                last_updated = datetime.now()

            # 创建DTO
            return EuroOddsRecord(
                companyid=company_id,
                companyname=company_name,
                homeodds=home_win,
                drawodds=draw,
                awayodds=away_win,
                updatetime=last_updated,
            )

        except Exception as e:
            logger.error(f"欧赔DTO转换失败: {raw_data}, error={str(e)}")
            return None


class TitanAsianCollector(BaseTitanCollector):
    """
    Titan007 亚盘采集器

    亚盘 (Asian Handicap) 让球盘口：
    - h (home_odds): 上盘赔率
    - a (away_odds): 下盘赔率
    - l (line): 盘口 (如 0.5, -0.5, 1.5 等)

    Example:
        >>> async with TitanAsianCollector() as collector:
        >>>     handicap = await collector.fetch_asian_handicap("2971465", CompanyID.CROWN)
        >>>     print(f"盘口: {handicap['handicap']}, 上盘: {handicap['home_odds']}")
    """

    def _safe_parse_float(self, value: Any) -> Optional[float]:
        """
        安全地解析浮点数

        Args:
            value: 要解析的值

        Returns:
            Optional[float]: 解析后的浮点数，失败返回 None
        """
        if value is None or value == "":
            return None

        try:
            return float(value)
        except (ValueError, TypeError):
            logger.warning(f"无法解析为浮点数: {value}")
            return None

    async def fetch_asian_handicap(
        self, match_id: str, company_id: Optional[CompanyID] = None
    ) -> Optional[Dict[str, Any]]:
        """
        获取亚盘数据

        Args:
            match_id: 比赛ID
            company_id: 指定博彩公司ID，None表示获取所有公司

        Returns:
            Dict[str, Any]: 亚盘数据，包含字段：
                - match_id: 比赛ID
                - company_id: 公司ID
                - company_name: 公司名称
                - home_odds: 上盘赔率
                - away_odds: 下盘赔率
                - handicap: 盘口
                - update_time: 更新时间
        """
        params = {"matchid": match_id}
        if company_id:
            params["companyid"] = int(company_id)

        try:
            response_data = await self._fetch_json("/handicap", params)
            return self._parse_asian_response(response_data, match_id, company_id)

        except Exception as e:
            logger.error(
                f"获取亚盘数据失败: match_id={match_id}, company_id={company_id}, error={str(e)}"
            )
            raise

    def _parse_asian_response(
        self,
        response_data: Dict[str, Any],
        match_id: str,
        company_id: Optional[CompanyID] = None,
    ) -> Optional[Dict[str, Any]]:
        """解析亚盘响应"""
        if not response_data or "data" not in response_data:
            return None

        data_list = response_data.get("data", [])
        if not data_list:
            return None

        # 查找指定公司的数据
        target_data = None
        if company_id:
            for item in data_list:
                if item.get("cid") == int(company_id):
                    target_data = item
                    break
        else:
            target_data = data_list[0]

        if not target_data:
            return None

        return self._extract_asian_fields(target_data, match_id)

    def _extract_asian_fields(
        self, item: Dict[str, Any], match_id: str
    ) -> Optional[Dict[str, Any]]:
        """提取亚盘字段"""
        try:
            company_id = item.get("cid")
            company_name = item.get("cname", "Unknown")

            # 获取字段映射
            h_field = TitanFieldMapping.get_field_name("ASIAN", "home_odds")  # "h"
            a_field = TitanFieldMapping.get_field_name("ASIAN", "away_odds")  # "a"
            l_field = TitanFieldMapping.get_field_name("ASIAN", "handicap")  # "l"

            # 提取字段值
            home_odds = self._safe_parse_float(item.get(h_field))
            away_odds = self._safe_parse_float(item.get(a_field))
            handicap = item.get(l_field)  # 盘口通常是字符串，如 "0.5", "-0.5"

            # 验证盘口有效性
            if not handicap or str(handicap).strip() == "":
                return None

            return {
                "match_id": match_id,
                "company_id": company_id,
                "company_name": company_name,
                "home_odds": home_odds,
                "away_odds": away_odds,
                "handicap": str(handicap).strip(),
                "update_time": item.get("utime"),
            }

        except Exception as e:
            logger.warning(f"提取亚盘字段失败: {item}, error={str(e)}")
            return None

    def to_dto(
        self, raw_data: Dict[str, Any], match_id: str
    ) -> Optional[AsianHandicapRecord]:
        """
        将原始API数据转换为标准亚盘DTO

        Args:
            raw_data: Titan API返回的原始数据
            match_id: 比赛ID

        Returns:
            Optional[AsianHandicapRecord]: 标准化的亚盘DTO
        """
        try:
            # 提取必要字段
            company_id = raw_data.get("cid")
            company_name = raw_data.get("cname", "")
            upper_odds = self._safe_parse_float(raw_data.get("h"))
            lower_odds = self._safe_parse_float(raw_data.get("a"))
            handicap = str(raw_data.get("l", "")).strip()

            # 验证必要字段
            if not all([company_id, company_name, upper_odds, lower_odds, handicap]):
                logger.warning(f"亚盘数据不完整: {raw_data}")
                return None

            # 解析更新时间
            update_time_str = raw_data.get("utime", "")
            if update_time_str:
                try:
                    last_updated = datetime.strptime(
                        update_time_str, "%Y-%m-%d %H:%M:%S"
                    )
                except ValueError:
                    last_updated = datetime.now()
            else:
                last_updated = datetime.now()

            # 创建DTO
            return AsianHandicapRecord(
                companyid=company_id,
                companyname=company_name,
                upperodds=upper_odds,
                lowerodds=lower_odds,
                handicap=handicap,
                updatetime=last_updated,
            )

        except Exception as e:
            logger.error(f"亚盘DTO转换失败: {raw_data}, error={str(e)}")
            return None


class TitanOverUnderCollector(BaseTitanCollector):
    """
    Titan007 大小球采集器

    大小球 (Over/Under) 进球数盘口：
    - o (over_odds): 大球赔率
    - u (under_odds): 小球赔率
    - l (line): 盘口 (如 2.5, 3.0 等)

    Example:
        >>> async with TitanOverUnderCollector() as collector:
        >>>     ou = await collector.fetch_over_under("2971465", CompanyID.PINNACLE)
        >>>     print(f"盘口: {ou['handicap']}球, 大球: {ou['over_odds']}")
    """

    def _safe_parse_float(self, value: Any) -> Optional[float]:
        """
        安全地解析浮点数

        Args:
            value: 要解析的值

        Returns:
            Optional[float]: 解析后的浮点数，失败返回 None
        """
        if value is None or value == "":
            return None

        try:
            return float(value)
        except (ValueError, TypeError):
            logger.warning(f"无法解析为浮点数: {value}")
            return None

    async def fetch_over_under(
        self, match_id: str, company_id: Optional[CompanyID] = None
    ) -> Optional[Dict[str, Any]]:
        """
        获取大小球数据

        Args:
            match_id: 比赛ID
            company_id: 指定博彩公司ID，None表示获取所有公司

        Returns:
            Dict[str, Any]: 大小球数据，包含字段：
                - match_id: 比赛ID
                - company_id: 公司ID
                - company_name: 公司名称
                - over_odds: 大球赔率
                - under_odds: 小球赔率
                - handicap: 盘口 (进球数)
                - update_time: 更新时间
        """
        params = {"matchid": match_id}
        if company_id:
            params["companyid"] = int(company_id)

        try:
            response_data = await self._fetch_json("/overunder", params)
            return self._parse_overunder_response(response_data, match_id, company_id)

        except Exception as e:
            logger.error(
                f"获取大小球数据失败: match_id={match_id}, company_id={company_id}, error={str(e)}"
            )
            raise

    def _parse_overunder_response(
        self,
        response_data: Dict[str, Any],
        match_id: str,
        company_id: Optional[CompanyID] = None,
    ) -> Optional[Dict[str, Any]]:
        """解析大小球响应"""
        if not response_data or "data" not in response_data:
            return None

        data_list = response_data.get("data", [])
        if not data_list:
            return None

        # 查找指定公司的数据
        target_data = None
        if company_id:
            for item in data_list:
                if item.get("cid") == int(company_id):
                    target_data = item
                    break
        else:
            target_data = data_list[0]

        if not target_data:
            return None

        return self._extract_overunder_fields(target_data, match_id)

    def _extract_overunder_fields(
        self, item: Dict[str, Any], match_id: str
    ) -> Optional[Dict[str, Any]]:
        """提取大小球字段"""
        try:
            company_id = item.get("cid")
            company_name = item.get("cname", "Unknown")

            # 获取字段映射
            o_field = TitanFieldMapping.get_field_name("OVER_UNDER", "over_odds")  # "o"
            u_field = TitanFieldMapping.get_field_name(
                "OVER_UNDER", "under_odds"
            )  # "u"
            l_field = TitanFieldMapping.get_field_name("OVER_UNDER", "handicap")  # "l"

            # 提取字段值
            over_odds = self._safe_parse_float(item.get(o_field))
            under_odds = self._safe_parse_float(item.get(u_field))
            handicap = item.get(l_field)  # 盘口通常是字符串，如 "2.5", "3.0"

            # 验证盘口有效性
            if not handicap or str(handicap).strip() == "":
                return None

            return {
                "match_id": match_id,
                "company_id": company_id,
                "company_name": company_name,
                "over_odds": over_odds,
                "under_odds": under_odds,
                "handicap": str(handicap).strip(),
                "update_time": item.get("utime"),
            }

        except Exception as e:
            logger.warning(f"提取大小球字段失败: {item}, error={str(e)}")
            return None

    def to_dto(
        self, raw_data: Dict[str, Any], match_id: str
    ) -> Optional[OverUnderRecord]:
        """
        将原始API数据转换为标准大小球DTO

        Args:
            raw_data: Titan API返回的原始数据
            match_id: 比赛ID

        Returns:
            Optional[OverUnderRecord]: 标准化的大小球DTO
        """
        try:
            # 提取必要字段
            company_id = raw_data.get("cid")
            company_name = raw_data.get("cname", "")
            over_odds = self._safe_parse_float(raw_data.get("o"))
            under_odds = self._safe_parse_float(raw_data.get("u"))
            handicap = str(raw_data.get("l", "")).strip()

            # 验证必要字段
            if not all([company_id, company_name, over_odds, under_odds, handicap]):
                logger.warning(f"大小球数据不完整: {raw_data}")
                return None

            # 解析更新时间
            update_time_str = raw_data.get("utime", "")
            if update_time_str:
                try:
                    last_updated = datetime.strptime(
                        update_time_str, "%Y-%m-%d %H:%M:%S"
                    )
                except ValueError:
                    last_updated = datetime.now()
            else:
                last_updated = datetime.now()

            # 创建DTO
            return OverUnderRecord(
                companyid=company_id,
                companyname=company_name,
                overodds=over_odds,
                underodds=under_odds,
                handicap=handicap,
                updatetime=last_updated,
            )

        except Exception as e:
            logger.error(f"大小球DTO转换失败: {raw_data}, error={str(e)}")
            return None

    def _safe_parse_float(self, value: Any) -> Optional[float]:
        """
        安全地解析浮点数

        Args:
            value: 要解析的值

        Returns:
            Optional[float]: 解析后的浮点数，失败返回 None

        Example:
            >>> collector._safe_parse_float("2.15")  # 2.15
            >>> collector._safe_parse_float(None)    # None
            >>> collector._safe_parse_float("")      # None
        """
        if value is None or value == "":
            return None

        try:
            return float(value)
        except (ValueError, TypeError):
            logger.warning(f"无法解析为浮点数: {value}")
            return None
