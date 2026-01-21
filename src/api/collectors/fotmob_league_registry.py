#!/usr/bin/env python3
"""
FotMob 全球联赛 ID 映射库 - V26.6 全球扩充
===========================================

核心功能：
    1. 完整的全球联赛 league_id 映射（5 大洲 + 30+ 国家）
    2. 联赛元数据（名称、国家、赛季格式、FotMob API ID）
    3. 质量等级分层（Tier 1-3）
    4. 赛季代码生成规则

Author: Data Engineering Expert
Version: V26.6
Date: 2026-01-06
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class LeagueInfo:
    """联赛信息数据类"""

    league_id: int  # FotMob league ID
    name: str  # 联赛名称（英文）
    name_zh: str  # 联赛名称（中文）
    country: str  # 国家代码（ISO 3166-1 alpha-2）
    country_name: str  # 国家名称（中文）
    tier: int  # 质量等级（1=Premium, 2=Standard, 3=Basic）
    season_format: str  # 赛季代码格式（例如 "2324" 代表 23/24）
    has_xg: bool = True  # 是否支持 xG 数据
    has_stats: bool = True  # 是否支持高级统计
    fotmob_url: str = ""  # FotMob URL（可选）

    def get_season_code(self, year_start: int, year_end: int | None = None) -> str:
        """
        生成赛季代码

        Args:
            year_start: 赛季开始年份（例如 2023）
            year_end: 赛季结束年份（可选，例如 2024）

        Returns:
            赛季代码（例如 "2324"）

        Examples:
            >>> league = LeagueInfo(47, "Premier League", "英超", "GB", "英国", 1, "YYyy")
            >>> league.get_season_code(2023, 2024)
            '2324'
            >>> league.get_season_code(2023)
            '23'
        """
        if year_end is None:
            # 单年制赛季（例如某些跨年赛事）
            return str(year_start)[-2:]
        # 双年制赛季（例如 2023-2024）
        return f"{year_start % 100:02d}{year_end % 100:02d}"


# ============================================================================
# 全球联赛映射库（按大洲分类）
# ============================================================================

FOTMOB_LEAGUE_REGISTRY: dict[int, LeagueInfo] = {
    # ========================================
    # 欧洲 (Europe)
    # ========================================
    # 🇬🇧 英格兰 (England)
    47: LeagueInfo(
        league_id=47,
        name="Premier League",
        name_zh="英超",
        country="GB",
        country_name="英国",
        tier=1,
        season_format="YYyy",
        has_xg=True,
        has_stats=True,
        fotmob_url="https://www.fotmob.com/leagues/47/premier-league/",
    ),
    48: LeagueInfo(
        league_id=48,
        name="Championship",
        name_zh="英冠",
        country="GB",
        country_name="英国",
        tier=2,
        season_format="YYyy",
        has_xg=True,
        has_stats=True,
        fotmob_url="https://www.fotmob.com/leagues/48/championship/",
    ),
    # 🇪🇸 西班牙 (Spain)
    87: LeagueInfo(
        league_id=87,
        name="La Liga",
        name_zh="西甲",
        country="ES",
        country_name="西班牙",
        tier=1,
        season_format="YYyy",
        has_xg=True,
        has_stats=True,
        fotmob_url="https://www.fotmob.com/leagues/87/la-liga/",
    ),
    94: LeagueInfo(
        league_id=94,
        name="Segunda División",
        name_zh="西乙",
        country="ES",
        country_name="西班牙",
        tier=2,
        season_format="YYyy",
        has_xg=True,
        has_stats=False,
        fotmob_url="https://www.fotmob.com/leagues/94/segunda-division/",
    ),
    # 🇩🇪 德国 (Germany)
    78: LeagueInfo(
        league_id=78,
        name="Bundesliga",
        name_zh="德甲",
        country="DE",
        country_name="德国",
        tier=1,
        season_format="YYyy",
        has_xg=True,
        has_stats=True,
        fotmob_url="https://www.fotmob.com/leagues/78/bundesliga/",
    ),
    95: LeagueInfo(
        league_id=95,
        name="2. Bundesliga",
        name_zh="德乙",
        country="DE",
        country_name="德国",
        tier=2,
        season_format="YYyy",
        has_xg=True,
        has_stats=False,
        fotmob_url="https://www.fotmob.com/leagues/95/2-bundesliga/",
    ),
    # 🇮🇹 意大利 (Italy)
    126: LeagueInfo(
        league_id=126,
        name="Serie A",
        name_zh="意甲",
        country="IT",
        country_name="意大利",
        tier=1,
        season_format="YYyy",
        has_xg=True,
        has_stats=True,
        fotmob_url="https://www.fotmob.com/leagues/126/serie-a/",
    ),
    127: LeagueInfo(
        league_id=127,
        name="Serie B",
        name_zh="意乙",
        country="IT",
        country_name="意大利",
        tier=2,
        season_format="YYyy",
        has_xg=True,
        has_stats=False,
        fotmob_url="https://www.fotmob.com/leagues/127/serie-b/",
    ),
    # 🇫🇷 法国 (France)
    53: LeagueInfo(
        league_id=53,
        name="Ligue 1",
        name_zh="法甲",
        country="FR",
        country_name="法国",
        tier=1,
        season_format="YYyy",
        has_xg=True,
        has_stats=True,
        fotmob_url="https://www.fotmob.com/leagues/53/ligue-1/",
    ),
    # 🇵🇹 葡萄牙 (Portugal)
    155: LeagueInfo(
        league_id=155,
        name="Liga Portugal",
        name_zh="葡超",
        country="PT",
        country_name="葡萄牙",
        tier=2,
        season_format="YYyy",
        has_xg=True,
        has_stats=True,
        fotmob_url="https://www.fotmob.com/leagues/155/liga-portugal/",
    ),
    # 🇳🇱 荷兰 (Netherlands)
    129: LeagueInfo(
        league_id=129,
        name="Eredivisie",
        name_zh="荷甲",
        country="NL",
        country_name="荷兰",
        tier=2,
        season_format="YYyy",
        has_xg=True,
        has_stats=True,
        fotmob_url="https://www.fotmob.com/leagues/129/eredivisie/",
    ),
    # 🇧🇪 比利时 (Belgium)
    118: LeagueInfo(
        league_id=118,
        name="Jupiler Pro League",
        name_zh="比甲",
        country="BE",
        country_name="比利时",
        tier=2,
        season_format="YYyy",
        has_xg=True,
        has_stats=True,
        fotmob_url="https://www.fotmob.com/leagues/118/jupiler-pro-league/",
    ),
    # 🇸🇨 苏格兰 (Scotland)
    157: LeagueInfo(
        league_id=157,
        name="Scottish Premiership",
        name_zh="苏超",
        country="GB",
        country_name="苏格兰",
        tier=2,
        season_format="YYyy",
        has_xg=True,
        has_stats=True,
        fotmob_url="https://www.fotmob.com/leagues/157/scottish-premiership/",
    ),
    # 🇹🇷 土耳其 (Turkey)
    157: LeagueInfo(
        league_id=201,
        name="Süper Lig",
        name_zh="土超",
        country="TR",
        country_name="土耳其",
        tier=2,
        season_format="YYyy",
        has_xg=True,
        has_stats=False,
        fotmob_url="https://www.fotmob.com/leagues/201/super-lig/",
    ),
    # 🇬🇷 希腊 (Greece)
    96: LeagueInfo(
        league_id=96,
        name="Super League Greece",
        name_zh="希超",
        country="GR",
        country_name="希腊",
        tier=2,
        season_format="YYyy",
        has_xg=False,
        has_stats=True,
        fotmob_url="https://www.fotmob.com/leagues/96/super-league-greece/",
    ),
    # 🇷🇺 俄罗斯 (Russia)
    153: LeagueInfo(
        league_id=153,
        name="Premier League Russia",
        name_zh="俄超",
        country="RU",
        country_name="俄罗斯",
        tier=2,
        season_format="YY",
        has_xg=False,
        has_stats=True,
        fotmob_url="https://www.fotmob.com/leagues/153/premier-league-russia/",
    ),
    # 🇺🇦 乌克兰 (Ukraine)
    186: LeagueInfo(
        league_id=186,
        name="Premier Liha",
        name_zh="乌超",
        country="UA",
        country_name="乌克兰",
        tier=2,
        season_format="YY",
        has_xg=False,
        has_stats=True,
        fotmob_url="https://www.fotmob.com/leagues/186/premier-liha/",
    ),
    # ========================================
    # 美洲 (Americas)
    # ========================================
    # 🇺🇸 美国 (USA) - MLS
    203: LeagueInfo(
        league_id=203,
        name="MLS",
        name_zh="美职联",
        country="US",
        country_name="美国",
        tier=2,
        season_format="YYYY",
        has_xg=True,
        has_stats=True,
        fotmob_url="https://www.fotmob.com/leagues/203/mls/",
    ),
    # 🇧🇷 巴西 (Brazil)
    274: LeagueInfo(
        league_id=274,
        name="Serie A Brazil",
        name_zh="巴甲",
        country="BR",
        country_name="巴西",
        tier=2,
        season_format="YYYY",
        has_xg=True,
        has_stats=True,
        fotmob_url="https://www.fotmob.com/leagues/274/serie-a-brazil/",
    ),
    # 🇦🇷 阿根廷 (Argentina)
    275: LeagueInfo(
        league_id=275,
        name="Liga Profesional",
        name_zh="阿甲",
        country="AR",
        country_name="阿根廷",
        tier=2,
        season_format="YYYY",
        has_xg=False,
        has_stats=True,
        fotmob_url="https://www.fotmob.com/leagues/275/liga-profesional/",
    ),
    # 🇲exico 墨西哥
    298: LeagueInfo(
        league_id=298,
        name="Liga MX",
        name_zh="墨超",
        country="MX",
        country_name="墨西哥",
        tier=2,
        season_format="YYYY",
        has_xg=True,
        has_stats=True,
        fotmob_url="https://www.fotmob.com/leagues/298/liga-mx/",
    ),
    # ========================================
    # 亚洲 (Asia)
    # ========================================
    # 🇯🇵 日本 (Japan) - J-League
    345: LeagueInfo(
        league_id=345,
        name="J-League Division 1",
        name_zh="日职联",
        country="JP",
        country_name="日本",
        tier=2,
        season_format="YYYY",
        has_xg=True,
        has_stats=True,
        fotmob_url="https://www.fotmob.com/leagues/345/j-league-division-1/",
    ),
    # 🇨🇳 中国 (China) - CSL
    322: LeagueInfo(
        league_id=322,
        name="Chinese Super League",
        name_zh="中超",
        country="CN",
        country_name="中国",
        tier=2,
        season_format="YYYY",
        has_xg=False,
        has_stats=True,
        fotmob_url="https://www.fotmob.com/leagues/322/chinese-super-league/",
    ),
    # 🇰🇷 韩国 (South Korea) - K-League
    353: LeagueInfo(
        league_id=353,
        name="K-League 1",
        name_zh="K联赛",
        country="KR",
        country_name="韩国",
        tier=2,
        season_format="YYYY",
        has_xg=False,
        has_stats=True,
        fotmob_url="https://www.fotmob.com/leagues/353/k-league-1/",
    ),
    # 🇸🇦 沙特阿拉伯 (Saudi Arabia) - Saudi Pro League
    410: LeagueInfo(
        league_id=410,
        name="Saudi Pro League",
        name_zh="沙特超",
        country="SA",
        country_name="沙特阿拉伯",
        tier=2,
        season_format="YYYY",
        has_xg=True,
        has_stats=True,
        fotmob_url="https://www.fotmob.com/leagues/410/saudi-pro-league/",
    ),
    # 🇦🇪 阿联酋 (UAE) - ADNOC Pro League
    411: LeagueInfo(
        league_id=411,
        name="ADNOC Pro League",
        name_zh="阿联酋职业联赛",
        country="AE",
        country_name="阿联酋",
        tier=3,
        season_format="YYYY",
        has_xg=False,
        has_stats=True,
        fotmob_url="https://www.fotmob.com/leagues/411/adnoc-pro-league/",
    ),
    # 🇦🇺 澳大利亚 (Australia) - A-League
    312: LeagueInfo(
        league_id=312,
        name="A-League",
        name_zh="澳超",
        country="AU",
        country_name="澳大利亚",
        tier=2,
        season_format="YY",
        has_xg=True,
        has_stats=True,
        fotmob_url="https://www.fotmob.com/leagues/312/a-league/",
    ),
    # 🇮🇳 印度 (India) - ISL
    397: LeagueInfo(
        league_id=397,
        name="Indian Super League",
        name_zh="印超",
        country="IN",
        country_name="印度",
        tier=3,
        season_format="YYYY",
        has_xg=False,
        has_stats=True,
        fotmob_url="https://www.fotmob.com/leagues/397/indian-super-league/",
    ),
    # ========================================
    # 非洲 (Africa)
    # ========================================
    # 🇿🇦 南非 (South Africa)
    288: LeagueInfo(
        league_id=288,
        name="Premier Soccer League",
        name_zh="南非超",
        country="ZA",
        country_name="南非",
        tier=3,
        season_format="YY",
        has_xg=False,
        has_stats=False,
        fotmob_url="https://www.fotmob.com/leagues/288/premier-soccer-league/",
    ),
    # 🇪🇬 埃及 (Egypt)
    287: LeagueInfo(
        league_id=287,
        name="Premier League",
        name_zh="埃及超",
        country="EG",
        country_name="埃及",
        tier=3,
        season_format="YYYY",
        has_xg=False,
        has_stats=True,
        fotmob_url="https://www.fotmob.com/leagues/287/premier-league/",
    ),
    # 🇳🇬 尼日利亚 (Nigeria)
    412: LeagueInfo(
        league_id=412,
        name="NPFL",
        name_zh="尼日利亚职业足球联赛",
        country="NG",
        country_name="尼日利亚",
        tier=3,
        season_format="YYYY",
        has_xg=False,
        has_stats=False,
        fotmob_url="https://www.fotmob.com/leagues/412/npfl/",
    ),
}


# ============================================================================
# 辅助函数
# ============================================================================


def get_league_info(league_id: int) -> LeagueInfo | None:
    """
    根据 league_id 获取联赛信息

    Args:
        league_id: FotMob league ID

    Returns:
        LeagueInfo 对象，如果未找到返回 None
    """
    return FOTMOB_LEAGUE_REGISTRY.get(league_id)


def get_leagues_by_tier(tier: int) -> list[LeagueInfo]:
    """
    根据质量等级获取联赛列表

    Args:
        tier: 质量等级（1=Premium, 2=Standard, 3=Basic）

    Returns:
        该等级的所有联赛
    """
    return [info for info in FOTMOB_LEAGUE_REGISTRY.values() if info.tier == tier]


def get_leagues_by_country(country_code: str) -> list[LeagueInfo]:
    """
    根据国家代码获取联赛列表

    Args:
        country_code: ISO 3166-1 alpha-2 国家代码

    Returns:
        该国家的所有联赛
    """
    return [info for info in FOTMOB_LEAGUE_REGISTRY.values() if info.country == country_code]


def get_all_leagues() -> list[LeagueInfo]:
    """
    获取所有联赛信息

    Returns:
        所有联赛的列表
    """
    return list(FOTMOB_LEAGUE_REGISTRY.values())


def print_league_registry():
    """打印联赛注册表摘要"""
    get_all_leagues()


    # 按大洲分组
    continents = {
        "欧洲": ["GB", "ES", "DE", "IT", "FR", "PT", "NL", "BE", "GB", "TR", "GR", "RU", "UA"],
        "美洲": ["US", "BR", "AR", "MX"],
        "亚洲": ["JP", "CN", "KR", "SA", "AE", "AU", "IN"],
        "非洲": ["ZA", "EG", "NG"],
    }

    for countries in continents.values():

        for country in countries:
            country_leagues = get_leagues_by_country(country)
            if not country_leagues:
                continue

            for league in country_leagues:
                {1: "⭐", 2: "✅", 3: "○"}.get(league.tier, "?")



# ============================================================================
# 主函数（测试用）
# ============================================================================

if __name__ == "__main__":
    print_league_registry()
