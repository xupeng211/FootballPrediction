"""
赔率数据解析器
Odds Data Parser

提供 HTML 内容解析功能，专门用于从网页中提取赔率信息。
该解析器专注于解析逻辑，不涉及网络请求。

支持的数据类型:
- 1X2 胜负平赔率
- Asian Handicap 亚洲让分盘
- Over/Under 大小球
- Both Teams to Score 双方进球

作者: Data Integration Team
创建时间: 2025-12-07
版本: 1.0.0
"""

import re
from datetime import datetime
from typing import Any,  Optional, Union

from bs4 import BeautifulSoup, Tag

from src.core.logging import get_logger

logger = get_logger(__name__)


class OddsData:
    """赔率数据结构"""

    def __init__(
        self,
        bookmaker: str,
        market: str,
        selection: str,
        odds: float,
        timestamp: Optional[datetime] = None,
    ):
        """
        初始化赔率数据

        Args:
            bookmaker: 博彩公司名称
            market: 市场类型
            selection: 投注选择
            odds: 赔率值
            timestamp: 数据时间戳
        """
        self.bookmaker = bookmaker
        self.market = market
        self.selection = selection
        self.odds = odds
        self.timestamp = timestamp or datetime.now()

    def to_dict(self) -> dict[str, Any]:
        """转换为字典格式"""
        return {
            "bookmaker": self.bookmaker,
            "market": self.market,
            "selection": self.selection,
            "odds": self.odds,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
        }


class OddsParser:
    """
    赔率数据解析器

    专门用于解析包含赔率信息的 HTML 内容。
    该类仅负责解析逻辑，不执行任何网络请求。
    """

    def __init__(self):
        """初始化解析器"""
        self.logger = get_logger(f"{__name__}.{self.__class__.__name__}")

        # 常见市场类型映射
        self.market_mapping = {
            "1x2": "1X2",
            "h2h": "1X2",
            "match_odds": "1X2",
            "asian_handicap": "Asian Handicap",
            "ah": "Asian Handicap",
            "over_under": "Over/Under",
            "ou": "Over/Under",
            "total_goals": "Over/Under",
            "both_teams_to_score": "Both Teams to Score",
            "btts": "Both Teams to Score",
            "correct_score": "Correct Score",
        }

        # 选择结果映射
        self.selection_mapping = {
            "home": "Home",
            "away": "Away",
            "draw": "Draw",
            "1": "Home",
            "x": "Draw",
            "2": "Away",
            "over": "Over",
            "under": "Under",
            "yes": "Yes",
            "no": "No",
        }

        logger.info("📊 OddsParser 初始化完成")

    def _normalize_odds(self, odds_str: str) -> Optional[float]:
        """
        标准化赔率值

        Args:
            odds_str: 赔率字符串

        Returns:
            标准化的赔率值，如果无效则返回 None
        """
        if not odds_str:
            return None

        try:
            # 移除常见的非数字字符
            clean_odds = re.sub(r'[^\d.]', '', str(odds_str))
            if not clean_odds:
                return None

            odds = float(clean_odds)
            if odds <= 1.0:
                return None  # 赔率必须大于1

            return odds

        except (ValueError, typeError):
            self.logger.warning(f"⚠️ 无效赔率值: {odds_str}")
            return None

    def _normalize_bookmaker(self, bookmaker_str: str) -> str:
        """
        标准化博彩公司名称

        Args:
            bookmaker_str: 博彩公司名称字符串

        Returns:
            标准化的博彩公司名称
        """
        if not bookmaker_str:
            return "Unknown"

        # 移除多余空格和特殊字符
        cleaned = re.sub(r'\s+', ' ', str(bookmaker_str).strip())
        return cleaned

    def _normalize_market(self, market_str: str) -> str:
        """
        标准化市场类型

        Args:
            market_str: 市场类型字符串

        Returns:
            标准化的市场类型
        """
        if not market_str:
            return "Unknown"

        normalized = str(market_str).lower().strip()
        return self.market_mapping.get(normalized, market_str.title())

    def _normalize_selection(self, selection_str: str) -> str:
        """
        标准化投注选择

        Args:
            selection_str: 投注选择字符串

        Returns:
            标准化的投注选择
        """
        if not selection_str:
            return "Unknown"

        normalized = str(selection_str).lower().strip()
        return self.selection_mapping.get(normalized, selection_str.title())

    def _parse_odds_table(self, table: Tag) -> list[OddsData]:
        """
        解析赔率表格

        Args:
            table: BeautifulSoup 表格元素

        Returns:
            解析出的赔率数据列表
        """
        odds_data = []

        try:
            rows = table.find_all("tr")[1:]  # 跳过表头
            for row in rows:
                cells = row.find_all(["td", "th"])
                if len(cells) < 4:  # 至少需要：博彩公司、市场、选择、赔率
                    continue

                bookmaker = self._normalize_bookmaker(cells[0].get_text(strip=True))
                market = self._normalize_market(cells[1].get_text(strip=True))
                selection = self._normalize_selection(cells[2].get_text(strip=True))
                odds = self._normalize_odds(cells[3].get_text(strip=True))

                if odds:
                    odds_data.append(OddsData(bookmaker, market, selection, odds))

        except Exception as e:
            self.logger.error(f"❌ 解析赔率表格失败: {e}")

        return odds_data

    def _parse_div_based_odds(self, container: Tag) -> list[OddsData]:
        """
        解析基于 div 的赔率数据

        Args:
            container: 包含赔率数据的容器元素

        Returns:
            解析出的赔率数据列表
        """
        odds_data = []

        try:
            # 查找博彩公司元素
            bookmaker_elements = container.find_all(class_=re.compile(r'bookmaker|provider'))
            if not bookmaker_elements:
                # 尝试其他常见的类名模式
                bookmaker_elements = container.find_all(attrs={"data-bookmaker": True})

            for element in bookmaker_elements:
                bookmaker = self._normalize_bookmaker(
                    element.get("data-bookmaker") or
                    element.get("data-provider") or
                    element.get_text(strip=True)
                )

                # 查找赔率值
                odds_elements = element.find_all(class_=re.compile(r'odds|price'))
                for odds_elem in odds_elements:
                    odds = self._normalize_odds(odds_elem.get_text(strip=True))
                    market = self._normalize_market(
                        odds_elem.get("data-market") or
                        odds_elem.get("data-typing.Type") or
                        "Unknown"
                    )
                    selection = self._normalize_selection(
                        odds_elem.get("data-selection") or
                        odds_elem.get("data-outcome") or
                        "Unknown"
                    )

                    if odds:
                        odds_data.append(OddsData(bookmaker, market, selection, odds))

        except Exception as e:
            self.logger.error(f"❌ 解析 div 赔率数据失败: {e}")

        return odds_data

    def parse_match_page(self, html_content: str) -> list[dict[str, Any]]:
        """
        解析比赛页面的赔率数据

        Args:
            html_content: HTML 内容字符串

        Returns:
            解析出的赔率数据字典列表
        """
        if not html_content:
            self.logger.warning("⚠️ HTML 内容为空")
            return []

        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            all_odds_data = []

            # 策略1: 查找标准的赔率表格
            odds_table = soup.find("table", {"id": "odds-data-table"})
            if odds_table:
                self.logger.info("📊 找到标准赔率表格")
                all_odds_data.extend(self._parse_odds_table(odds_table))

            # 策略2: 查找其他可能的表格
            if not all_odds_data:
                for table in soup.find_all("table"):
                    if any(keyword in table.get_text().lower() for keyword in ['odds', 'price', 'bet']):
                        self.logger.info("📊 找到可能的赔率表格")
                        all_odds_data.extend(self._parse_odds_table(table))

            # 策略3: 查找基于 div 的赔率容器
            if not all_odds_data:
                odds_container = soup.find("div", {"id": "odds-container"})
                if not odds_container:
                    odds_container = soup.find("div", class_=re.compile(r'odds|betting'))

                if odds_container:
                    self.logger.info("📊 找到赔率容器")
                    all_odds_data.extend(self._parse_div_based_odds(odds_container))

            # 转换为字典格式
            result = [odds.to_dict() for odds in all_odds_data]

            self.logger.info(
                "✅ 赔率解析完成",
                extra={
                    "total_odds": len(result),
                    "unique_bookmakers": len({d["bookmaker"] for d in result}),
                    "markets": list({d["market"] for d in result}),
                }
            )

            return result

        except Exception as e:
            self.logger.error(f"❌ 解析比赛页面失败: {e}")
            return []

    def parse_multiple_matches(self, html_content: str) -> list[dict[str, Any]]:
        """
        解析包含多个比赛赔率的页面

        Args:
            html_content: HTML 内容字符串

        Returns:
            解析出的赔率数据字典列表
        """
        if not html_content:
            self.logger.warning("⚠️ HTML 内容为空")
            return []

        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            all_odds_data = []

            # 查找比赛容器
            match_containers = soup.find_all(
                attrs={"class": re.compile(r'match|game|fixture')},
                limit=100  # 限制处理数量以避免性能问题
            )

            for i, container in enumerate(match_containers):
                self.logger.debug(f"📊 解析比赛容器 {i+1}/{len(match_containers)}")

                # 提取比赛容器中的 HTML 并解析
                container_html = str(container)
                container_odds = self.parse_match_page(container_html)
                all_odds_data.extend(container_odds)

            # 转换为字典格式
            result = [odds.to_dict() for odds in all_odds_data]

            self.logger.info(
                "✅ 多比赛赔率解析完成",
                extra={
                    "matches_processed": len(match_containers),
                    "total_odds": len(result),
                }
            )

            return result

        except Exception as e:
            self.logger.error(f"❌ 解析多比赛页面失败: {e}")
            return []

    def validate_odds_data(self, odds_data: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """
        验证和清理赔率数据

        Args:
            odds_data: 原始赔率数据列表

        Returns:
            验证后的赔率数据列表
        """
        valid_data = []

        for data in odds_data:
            try:
                # 检查必要字段
                if not all(key in data for key in ["bookmaker", "market", "selection", "odds"]):
                    self.logger.warning(f"⚠️ 赔率数据缺少必要字段: {data}")
                    continue

                # 检查赔率值
                if not isinstance(data["odds"], (int, float)) or data["odds"] <= 1.0:
                    self.logger.warning(f"⚠️ 无效赔率值: {data['odds']}")
                    continue

                # 检查字符串字段
                if not all(data[field] for field in ["bookmaker", "market", "selection"]):
                    self.logger.warning(f"⚠️ 空字符串字段: {data}")
                    continue

                valid_data.append(data)

            except Exception as e:
                self.logger.error(f"❌ 验证赔率数据失败: {e}, 数据: {data}")

        self.logger.info(
            "✅ 赔率数据验证完成",
            extra={
                "original_count": len(odds_data),
                "valid_count": len(valid_data),
                "invalid_count": len(odds_data) - len(valid_data),
            }
        )

        return valid_data
