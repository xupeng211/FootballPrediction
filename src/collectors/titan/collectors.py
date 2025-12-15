"""
Titan007 具体采集器实现 - 支持 ID 映射

包含欧赔、亚盘、大小球三个具体采集器，继承自 BaseTitanCollector。
每个采集器负责解析特定类型的赔率数据。
新增了 NowGoal ID 映射功能，解决 ID 不匹配问题。
"""

from typing import Optional, Dict, Any, List, Tuple
import logging
import re
from datetime import datetime
from urllib.parse import urljoin

from src.collectors.titan.base_collector import BaseTitanCollector
from src.collectors.titan.constants import CompanyID, TitanFieldMapping
from src.schemas.titan import EuroOddsRecord, AsianHandicapRecord, OverUnderRecord

logger = logging.getLogger(__name__)


class TitanEuroCollector(BaseTitanCollector):
    """
    Titan007 欧赔采集器 - 支持 ID 映射

    欧赔 (European Odds) 也叫 1X2 胜平负盘口：
    - h (home): 主胜赔率
    - d (draw): 平局赔率
    - a (away): 客胜赔率

    新增功能：自动 ID 映射，通过 NowGoal 找到正确的 Titan ID

    Example:
        >>> async with TitanEuroCollector() as collector:
        >>>     odds = await collector.fetch_euro_odds_with_mapping(
        ...         home_team="Manchester United",
        ...         away_team="Liverpool",
        ...         match_date="2024-12-14"
        ...     )
        >>>     print(f"主胜: {odds['home_win']}, 平局: {odds['draw']}, 客胜: {odds['away_win']}")
    """

    async def find_titan_match_id(
        self,
        home_team: str,
        away_team: str,
        match_date: datetime
    ) -> Optional[str]:
        """
        通过 NowGoal 查找对应的 Titan 比赛ID

        Args:
            home_team: 主队名称 (英文)
            away_team: 客队名称 (英文)
            match_date: 比赛日期

        Returns:
            Optional[str]: Titan 比赛ID，如果未找到返回 None
        """
        try:
            # 尝试多个 Titan/NowGoal 接口
            urls_to_try = [
                "https://interface.nowgoal.com/football/Today_Match",
                "https://www.nowgoal.com/data/bet_cur.xml",  # NowGoal XML 数据接口
                "https://data.nowgoal.com/1x2.xml",        # NowGoal 1x2 数据
                "https://interface.bet007.com/nba/xml",  # 备用接口
            ]

            print(f"\n=== Titan/NowGoal ID 映射调试 ===")
            print(f"查找比赛: {home_team} vs {away_team}")
            print(f"比赛日期: {match_date.strftime('%Y-%m-%d')}")
            print("=" * 35)

            # 使用 httpx 获取数据
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "application/json, text/html, application/xml, */*",
                "Accept-Language": "en-US,en;q=0.5",
            }

            for i, nowgoal_url in enumerate(urls_to_try):
                try:
                    print(f"尝试接口 {i+1}: {nowgoal_url}")

                    async with self.rate_limiter.acquire("nowgoal"):
                        response = await self.http_client.get(nowgoal_url, headers=headers)

                    if response.status_code != 200:
                        print(f"⚠️ 接口 {i+1} 状态码异常: {response.status_code}")
                        continue

                    content = response.text
                    print(f"✅ 接口 {i+1} 响应大小: {len(content)} 字符")

                    # 如果响应为空，继续尝试下一个
                    if not content or len(content) < 10:
                        print(f"⚠️ 接口 {i+1} 响应为空")
                        continue

                    # 尝试解析数据
                    try:
                        # 首先尝试解析为 JSON
                        import json
                        data = json.loads(content)
                        print(f"✅ 接口 {i+1} JSON 数据解析成功")

                        # 在 JSON 数据中搜索匹配的比赛
                        result = self._find_match_in_nowgoal_json(
                            data, home_team, away_team, match_date
                        )
                        if result:
                            return result

                    except json.JSONDecodeError:
                        print(f"⚠️ 接口 {i+1} 不是 JSON 格式，尝试 XML/文本解析")

                        # 尝试 XML 解析
                        try:
                            result = self._find_match_in_xml(
                                content, home_team, away_team, match_date
                            )
                            if result:
                                return result
                        except Exception as xml_e:
                            print(f"⚠️ 接口 {i+1} XML 解析失败: {xml_e}")

                        # 最后尝试文本解析
                        result = self._find_match_in_nowgoal_text(
                            content, home_team, away_team, match_date
                        )
                        if result:
                            return result

                except Exception as e:
                    print(f"❌ 接口 {i+1} 请求失败: {str(e)}")
                    continue

            print("❌ 所有接口都尝试失败")
            return None

        except Exception as e:
            print(f"❌ NowGoal ID 映射失败: {str(e)}")
            logger.error(f"NowGoal ID mapping failed: {e}")
            return None

    def _find_match_in_nowgoal_json(
        self,
        data: Dict[str, Any],
        home_team: str,
        away_team: str,
        match_date: datetime
    ) -> Optional[str]:
        """在 NowGoal JSON 数据中查找比赛"""
        try:
            # NowGoal JSON 结构可能是 {"list": [...] }
            matches = data.get("list", data.get("data", []))

            if not matches:
                print("⚠️ NowGoal JSON 中没有找到比赛列表")
                return None

            date_str = match_date.strftime("%Y-%m-%d")

            for match in matches:
                match_home = match.get("home", "").lower()
                match_away = match.get("away", "").lower()
                match_date_str = match.get("date", "")
                titan_id = str(match.get("id", ""))

                # 模糊匹配队名 (匹配前几个字符)
                home_match = (
                    home_team.lower() in match_home or
                    match_home in home_team.lower() or
                    self._fuzzy_team_match(home_team, match_home)
                )

                away_match = (
                    away_team.lower() in match_away or
                    match_away in away_team.lower() or
                    self._fuzzy_team_match(away_team, match_away)
                )

                date_match = date_str in match_date_str or match_date_str in date_str

                if home_match and away_match and date_match and titan_id:
                    print(f"✅ 找到匹配: {match_home} vs {match_away} (ID: {titan_id})")
                    return titan_id

            print(f"❌ 未找到匹配的比赛: {home_team} vs {away_team} ({date_str})")
            return None

        except Exception as e:
            print(f"❌ JSON 解析失败: {str(e)}")
            return None

    def _find_match_in_xml(
        self,
        content: str,
        home_team: str,
        away_team: str,
        match_date: datetime
    ) -> Optional[str]:
        """在 XML 数据中查找比赛"""
        try:
            import xml.etree.ElementTree as ET

            # 尝试解析 XML
            root = ET.fromstring(content)
            print("✅ XML 解析成功")

            # 搜索比赛节点 - 常见的 XML 结构
            for match in root.findall('.//match'):
                match_home = match.get('home', '').lower()
                match_away = match.get('away', '').lower()
                titan_id = match.get('id', '')

                # 简单匹配
                if (home_team.lower() in match_home and
                    away_team.lower() in match_away and
                    titan_id):
                    print(f"✅ 在 XML 中找到匹配: {match_home} vs {match_away} (ID: {titan_id})")
                    return titan_id

            # 如果没有找到，尝试其他可能的节点名
            for node_name in ['game', 'fixture', 'event']:
                for match in root.findall(f'.//{node_name}'):
                    match_home = match.get('home', match.get('team1', '')).lower()
                    match_away = match.get('away', match.get('team2', '')).lower()
                    titan_id = match.get('id', match.get('matchid', ''))

                    if (home_team.lower() in match_home and
                        away_team.lower() in match_away and
                        titan_id):
                        print(f"✅ 在 XML 节点 {node_name} 中找到匹配: {match_home} vs {match_away} (ID: {titan_id})")
                        return titan_id

            print("❌ 在 XML 中未找到匹配的比赛")
            return None

        except ET.ParseError as e:
            print(f"⚠️ XML 解析失败: {str(e)}")
            return None
        except Exception as e:
            print(f"❌ XML 处理失败: {str(e)}")
            return None

    def _find_match_in_nowgoal_text(
        self,
        content: str,
        home_team: str,
        away_team: str,
        match_date: datetime
    ) -> Optional[str]:
        """在 NowGoal 文本数据中查找比赛"""
        try:
            # 在文本中搜索队名模式
            home_pattern = re.escape(home_team)
            away_pattern = re.escape(away_team)

            # 搜索包含两个队名的行
            lines = content.split('\n')

            for line in lines:
                if home_team.lower() in line.lower() and away_team.lower() in line.lower():
                    # 尝试提取 ID (通常在行首或特定位置)
                    # 寻找数字模式
                    id_match = re.search(r'(\d+)', line)
                    if id_match:
                        titan_id = id_match.group(1)
                        print(f"✅ 在文本中找到匹配 (ID: {titan_id}): {line[:100]}...")
                        return titan_id

            print(f"❌ 在文本中未找到匹配的比赛")
            return None

        except Exception as e:
            print(f"❌ 文本解析失败: {str(e)}")
            return None

    def _fuzzy_team_match(self, team1: str, team2: str) -> bool:
        """模糊队名匹配"""
        try:
            # 移除常见后缀和前缀
            clean_team1 = re.sub(r'\b(fc|club|united|city|athletic)\b', '', team1.lower()).strip()
            clean_team2 = re.sub(r'\b(fc|club|united|city|athletic)\b', '', team2.lower()).strip()

            # 检查是否有足够的重叠
            if len(clean_team1) >= 3 and len(clean_team2) >= 3:
                return (
                    clean_team1 in clean_team2 or
                    clean_team2 in clean_team1 or
                    abs(len(clean_team1) - len(clean_team2)) <= 2
                )

            return team1.lower() in team2.lower() or team2.lower() in team1.lower()

        except Exception:
            return False

    async def fetch_euro_odds_with_mapping(
        self,
        home_team: str,
        away_team: str,
        match_date: datetime,
        company_id: Optional[CompanyID] = None
    ) -> Optional[Dict[str, Any]]:
        """
        获取欧赔数据 - 自动 ID 映射版本

        Args:
            home_team: 主队名称 (英文)
            away_team: 客队名称 (英文)
            match_date: 比赛日期
            company_id: 指定博彩公司ID，None表示获取所有公司

        Returns:
            Optional[Dict[str, Any]]: 欧赔数据
        """
        try:
            # Step 1: 通过 NowGoal 找到正确的 Titan ID
            titan_id = await self.find_titan_match_id(home_team, away_team, match_date)

            if not titan_id:
                print(f"❌ 无法找到 {home_team} vs {away_team} 的 Titan ID")
                return None

            print(f"✅ 找到 Titan ID: {titan_id} for {home_team} vs {away_team}")

            # Step 2: 使用找到的 Titan ID 获取欧赔数据
            return await self.fetch_euro_odds(titan_id, company_id)

        except Exception as e:
            logger.error(f"获取欧赔数据失败 (映射版): {home_team} vs {away_team}, error={str(e)}")
            return None

    async def fetch_euro_odds(
        self, match_id: str, company_id: Optional[CompanyID] = None
    ) -> Optional[Dict[str, Any]]:
        """
        获取欧赔数据 (原始版本)

        Args:
            match_id: Titan 比赛ID
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
