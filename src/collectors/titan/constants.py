"""
Titan007 常量定义

包含博彩公司ID、盘口类型等枚举定义。
"""

from enum import IntEnum
from typing import Dict


class CompanyID(IntEnum):
    """
    博彩公司ID枚举

    这些ID对应Titan007接口中的公司标识符。

    Titan007 API 使用数字ID来标识不同的博彩公司。
    在实际请求中，需要通过 companyid 参数指定要查询的公司。

    Examples:
        >>> CompanyID.BET365  # 8
        >>> CompanyID.PINNACLE  # 17

    Reference:
        - Titan007 接口文档中的公司映射表
        - 常见公司: Bet365(8) 市场占有率最高
        - Pinnacle(17) 以水位精准著称 (专业投注者首选)
    """

    CROWN = 1  # 皇冠 (Crown) - 亚洲知名博彩公司

    WILLIAM_HILL = 3  # 威廉希尔 (William Hill) - 英国老牌博彩公司

    BET365 = 8  # Bet365 - 全球最大在线博彩公司之一

    LIVE = 14  # 立博 (Ladbrokes) - 英国老牌博彩公司

    PINNACLE = 17  # 平博/Pinnacle - 以高水位、低利润著称，专业投注者常用

    @classmethod
    def get_company_name(cls, company_id: int) -> str:
        """
        根据公司ID获取公司名称

        Args:
            company_id: 博彩公司ID

        Returns:
            str: 公司名称，如果未找到返回 "Unknown"

        Example:
            >>> CompanyID.get_company_name(8)
            'Bet365'
            >>> CompanyID.get_company_name(999)
            'Unknown'
        """
        company_map: Dict[int, str] = {
            cls.CROWN: "Crown",
            cls.WILLIAM_HILL: "William Hill",
            cls.BET365: "Bet365",
            cls.LIVE: "Ladbrokes",
            cls.PINNACLE: "Pinnacle",
        }
        return company_map.get(company_id, "Unknown")

    @classmethod
    def get_all_companies(cls) -> Dict[int, str]:
        """
        获取所有可用的博彩公司映射

        Returns:
            Dict[int, str]: {company_id: company_name}

        Example:
            >>> CompanyID.get_all_companies()
            {1: 'Crown', 3: 'William Hill', 8: 'Bet365', 14: 'Ladbrokes', 17: 'Pinnacle'}
        """
        return {
            cls.CROWN: "Crown",
            cls.WILLIAM_HILL: "William Hill",
            cls.BET365: "Bet365",
            cls.LIVE: "Ladbrokes",
            cls.PINNACLE: "Pinnacle",
        }


class MarketType:
    """
    盘口类型常量

    定义了三种核心盘口类型。
    """

    EUROPEAN = "euro"  # 欧赔 (1X2) - 胜平负

    ASIAN_HANDICAP = "handicap"  # 亚盘 - 让球盘

    OVER_UNDER = "overunder"  # 大小球 - 进球数


class TitanFieldMapping:
    """
    Titan007 字段映射

    Titan007 返回的 JSON 字段通常比较简略，需要映射到标准字段名。

    Titan 的字段缩写说明：
    - 欧赔: h = home (主胜), d = draw (平局), a = away (客胜)
    - 亚盘: h = home_odds (上盘赔率), a = away_odds (下盘赔率), l = line (盘口)
    - 大小球: o = over_odds (大球赔率), u = under_odds (小球赔率), l = line (盘口)

    Examples:
        >>> TitanFieldMapping.EUROPEAN["home_win"]  # "h"
        >>> TitanFieldMapping.ASIAN["handicap"]  # "l"
    """

    # 欧赔字段映射
    EUROPEAN: Dict[str, str] = {
        "home_win": "h",  # 主胜 (Home win)
        "draw": "d",  # 平局 (Draw)
        "away_win": "a",  # 客胜 (Away win)
    }

    # 亚盘字段映射
    ASIAN: Dict[str, str] = {
        "home_odds": "h",  # 上盘赔率 (Home/Upper odds)
        "away_odds": "a",  # 下盘赔率 (Away/Lower odds)
        "handicap": "l",  # 盘口 (Handicap line)
    }

    # 大小球字段映射
    OVER_UNDER: Dict[str, str] = {
        "over_odds": "o",  # 大球赔率 (Over odds)
        "under_odds": "u",  # 小球赔率 (Under odds)
        "handicap": "l",  # 盘口 (Total goals line)
    }

    @classmethod
    def get_field_name(cls, mapping_name: str, field_key: str) -> str:
        """
        根据映射名称和字段键获取字段名

        Args:
            mapping_name: 映射名称 (e.g., "EUROPEAN", "ASIAN", "OVER_UNDER")
            field_key: 标准字段名 (e.g., "home_win", "handicap")

        Returns:
            str: Titan接口中的字段名

        Example:
            >>> TitanFieldMapping.get_field_name("EUROPEAN", "home_win")
            'h'
            >>> TitanFieldMapping.get_field_name("ASIAN", "handicap")
            'l'
        """
        mapping: Dict[str, Dict[str, str]] = {
            "EUROPEAN": cls.EUROPEAN,
            "ASIAN": cls.ASIAN,
            "OVER_UNDER": cls.OVER_UNDER,
        }
        field_mapping = mapping.get(mapping_name.upper())
        if not field_mapping:
            raise ValueError(f"Unknown mapping: {mapping_name}")

        return field_mapping.get(field_key, field_key)


# 常用公司列表 (便于批量查询)
POPULAR_COMPANIES = [
    CompanyID.BET365,  # Bet365 (市场占有率最高)
    CompanyID.WILLIAM_HILL,  # 威廉希尔 (欧洲老牌)
    CompanyID.PINNACLE,  # Pinnacle (专业投注者首选)
    CompanyID.LIVE,  # 立博 (欧洲老牌)
    CompanyID.CROWN,  # 皇冠 (亚洲市场)
]

# 核心盘口类型
CORE_MARKETS = [
    MarketType.EUROPEAN,
    MarketType.ASIAN_HANDICAP,
    MarketType.OVER_UNDER,
]
