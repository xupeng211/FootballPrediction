#!/usr/bin/env python3
"""
TeamNameRegistry - 五大联赛队名标准化映射表

任务：
1. 建立五大联赛96队的标准映射（FotMob ID <-> OddsPortal Slug）
2. 废弃split('-')的解析逻辑
3. 支持100%准确的队名识别

Author: 首席逆向架构师
Version: V41.0
Date: 2026-01-13
"""

import logging
from typing import Dict, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class TeamMapping:
    """队名映射数据类"""
    fotmob_id: int           # FotMob ID
    fotmob_name: str         # FotMob标准队名
    oddsportal_slug: str     # OddsPortal URL slug
    oddsportal_name: str     # OddsPortal显示队名
    league: str              # 联赛名称

    def __post_init__(self):
        """后处理：标准化队名"""
        self.fotmob_name = self.fotmob_name.strip()
        self.oddsportal_slug = self.oddsportal_slug.strip()


class TeamNameRegistry:
    """
    队名注册表 - 五大联赛96队完整映射

    设计原则：
    - 单一数据源（Single Source of Truth）
    - TDD测试覆盖（100%映射准确率）
    - 支持模糊匹配（处理边缘情况）
    """

    # 五大联赛完整映射表（96队）
    _TEAM_MAPPINGS: Dict[str, TeamMapping] = {}

    @classmethod
    def initialize(cls):
        """初始化队名映射表"""
        if cls._TEAM_MAPPINGS:
            return

        logger.info("[TeamNameRegistry] 📋 初始化五大联赛96队映射表...")

        # La Liga (20队)
        cls._register_laliga_teams()

        # Ligue 1 (18队)
        cls._register_ligue1_teams()

        # Premier League (20队)
        cls._register_premier_league_teams()

        # Bundesliga (18队)
        cls._register_bundesliga_teams()

        # Serie A (20队)
        cls._register_serie_a_teams()

        logger.info(f"[TeamNameRegistry] ✅ 已注册 {len(cls._TEAM_MAPPINGS)} 支球队")

    @classmethod
    def _register_laliga_teams(cls):
        """注册西甲20队"""
        teams = [
            # FotMob ID, FotMob Name, OddsPortal Slug, OddsPortal Name
            (529, "Real Madrid", "real-madrid", "Real Madrid"),
            (530, "Barcelona", "barcelona", "Barcelona"),
            (538, "Atlético Madrid", "atl-madrid", "Atl. Madrid"),
            (544, "Sevilla", "sevilla", "Sevilla"),
            (545, "Real Betis", "betis", "Betis"),
            (534, "Athletic Bilbao", "ath-bilbao", "Ath Bilbao"),
            (537, "Valencia", "valencia", "Valencia"),
            (540, "Villarreal", "villarreal", "Villarreal"),
            (543, "Real Sociedad", "real-sociedad", "Real Sociedad"),
            (535, "Real Valladolid", "valladolid", "Valladolid"),
            (546, "Getafe", "getafe", "Getafe"),
            (539, "Celta Vigo", "celta-vigo", "Celta Vigo"),
            (541, "Osasuna", "osasuna", "Osasuna"),
            (542, "Rayo Vallecano", "rayo-vallecano", "Rayo Vallecano"),
            (532, "Girona", "girona", "Girona"),
            (547, "Almeria", "almeria", "Almeria"),
            (548, "Las Palmas", "las-palmas", "Las Palmas"),
            (533, "Mallorca", "mallorca", "Mallorca"),
            (536, "Alaves", "alaves", "Alaves"),
            (531, "Cadiz", "cadiz", "Cadiz"),
            (549, "Granada", "granada", "Granada CF"),
        ]

        for fotmob_id, fotmob_name, op_slug, op_name in teams:
            mapping = TeamMapping(
                fotmob_id=fotmob_id,
                fotmob_name=fotmob_name,
                oddsportal_slug=op_slug,
                oddsportal_name=op_name,
                league="La Liga"
            )
            cls._register_mapping(mapping)

    @classmethod
    def _register_ligue1_teams(cls):
        """注册法甲18队（23/24赛季）"""
        teams = [
            (523, "Paris Saint Germain", "psg", "PSG"),
            (524, "Monaco", "monaco", "Monaco"),
            (525, "Lyon", "lyon", "Lyon"),
            (526, "Marseille", "marseille", "Marseille"),
            (527, "Lille", "lille", "Lille"),
            (528, "Lens", "lens", "Lens"),
            (560, "Rennes", "rennes", "Rennes"),
            (561, "Nice", "nice", "Nice"),
            (562, "Strasbourg", "strasbourg", "Strasbourg"),
            (563, "Toulouse", "toulouse", "Toulouse"),
            (564, "Nantes", "nantes", "Nantes"),
            (565, "Montpellier", "montpellier", "Montpellier"),
            (566, "Brest", "brest", "Brest"),
            (567, "Reims", "reims", "Reims"),
            (568, "Lorient", "lorient", "Lorient"),
            (569, "Le Havre", "le-havre", "Le Havre"),
            (570, "Metz", "metz", "Metz"),
            (571, "Clermont", "clermont", "Clermont"),
            (1616, "Saint-Etienne", "st-etienne", "St Etienne"),
        ]

        for fotmob_id, fotmob_name, op_slug, op_name in teams:
            mapping = TeamMapping(
                fotmob_id=fotmob_id,
                fotmob_name=fotmob_name,
                oddsportal_slug=op_slug,
                oddsportal_name=op_name,
                league="Ligue 1"
            )
            cls._register_mapping(mapping)

    @classmethod
    def _register_premier_league_teams(cls):
        """注册英超20队"""
        teams = [
            (2, "Arsenal", "arsenal", "Arsenal"),
            (6, "Aston Villa", "aston-villa", "Aston Villa"),
            (33, "Bournemouth", "bournemouth", "Bournemouth"),
            (8, "Brentford", "brentford", "Brentford"),
            (12, "Brighton", "brighton", "Brighton"),
            (9, "Chelsea", "chelsea", "Chelsea"),
            (14, "Crystal Palace", "crystal-palace", "Crystal Palace"),
            (25, "Everton", "everton", "Everton"),
            (26, "Fulham", "fulham", "Fulham"),
            (17, "Liverpool", "liverpool", "Liverpool"),
            (18, "Man City", "man-city", "Man City"),
            (19, "Man United", "man-utd", "Man Utd"),
            (35, "Newcastle", "newcastle", "Newcastle"),
            (31, "Nottingham Forest", "nottm-forest", "Nottm Forest"),
            (22, "Tottenham", "tottenham", "Tottenham"),
            (27, "West Ham", "west-ham", "West Ham"),
            (28, "Wolves", "wolves", "Wolves"),
            (29, "Ipswich Town", "ipswich", "Ipswich"),
            (30, "Leicester City", "leicester", "Leicester"),
            (34, "Southampton", "southampton", "Southampton"),
        ]

        for fotmob_id, fotmob_name, op_slug, op_name in teams:
            mapping = TeamMapping(
                fotmob_id=fotmob_id,
                fotmob_name=fotmob_name,
                oddsportal_slug=op_slug,
                oddsportal_name=op_name,
                league="Premier League"
            )
            cls._register_mapping(mapping)

    @classmethod
    def _register_bundesliga_teams(cls):
        """注册德甲18队"""
        teams = [
            (164, "Bayern Munich", "bayern", "Bayern Munich"),
            (165, "Borussia Dortmund", "dortmund", "Dortmund"),
            (168, "RB Leipzig", "rb-leipzig", "RB Leipzig"),
            (172, "Bayer Leverkusen", "leverkusen", "Leverkusen"),
            (173, "Union Berlin", "union-berlin", "Union Berlin"),
            (170, "Freiburg", "freiburg", "Freiburg"),
            (171, "Eintracht Frankfurt", "frankfurt", "Frankfurt"),
            (175, "Wolfsburg", "wolfsburg", "Wolfsburg"),
            (176, "Mainz", "mainz", "Mainz"),
            (177, "Borussia M'gladbach", "borgladbach", "M'gladbach"),
            (178, "Köln", "koln", "Köln"),
            (179, "Hoffenheim", "hoffenheim", "Hoffenheim"),
            (180, "Werder Bremen", "bremen", "Bremen"),
            (181, "Bochum", "bochum", "Bochum"),
            (182, "Augsburg", "augsburg", "Augsburg"),
            (183, "Stuttgart", "stuttgart", "Stuttgart"),
            (184, "Darmstadt", "darmstadt", "Darmstadt"),
            (185, "Heidenheim", "heidenheim", "Heidenheim"),
        ]

        for fotmob_id, fotmob_name, op_slug, op_name in teams:
            mapping = TeamMapping(
                fotmob_id=fotmob_id,
                fotmob_name=fotmob_name,
                oddsportal_slug=op_slug,
                oddsportal_name=op_name,
                league="Bundesliga"
            )
            cls._register_mapping(mapping)

    @classmethod
    def _register_serie_a_teams(cls):
        """注册意甲20队"""
        teams = [
            (85, "Napoli", "napoli", "Napoli"),
            (86, "Lazio", "lazio", "Lazio"),
            (87, "Inter", "inter", "Inter"),
            (89, "AC Milan", "milan", "AC Milan"),
            (90, "Juventus", "juventus", "Juventus"),
            (91, "Roma", "roma", "Roma"),
            (92, "Atalanta", "atalanta", "Atalanta"),
            (94, "Fiorentina", "fiorentina", "Fiorentina"),
            (95, "Torino", "torino", "Torino"),
            (96, "Bologna", "bologna", "Bologna"),
            (97, "Sassuolo", "sassuolo", "Sassuolo"),
            (98, "Udinese", "udinese", "Udinese"),
            (99, "Sampdoria", "sampdoria", "Sampdoria"),
            (100, "Genoa", "genoa", "Genoa"),
            (101, "Cagliari", "cagliari", "Cagliari"),
            (102, "Venezia", "venezia", "Venezia"),
            (103, "Hellas Verona", "verona", "Verona"),
            (104, "Empoli", "empoli", "Empoli"),
            (105, "Salernitana", "salernitana", "Salernitana"),
            (106, "Lecce", "lecce", "Lecce"),
        ]

        for fotmob_id, fotmob_name, op_slug, op_name in teams:
            mapping = TeamMapping(
                fotmob_id=fotmob_id,
                fotmob_name=fotmob_name,
                oddsportal_slug=op_slug,
                oddsportal_name=op_name,
                league="Serie A"
            )
            cls._register_mapping(mapping)

    @classmethod
    def _register_mapping(cls, mapping: TeamMapping):
        """注册单个映射"""
        # 使用OddsPortal slug作为键
        cls._TEAM_MAPPINGS[mapping.oddsportal_slug] = mapping

    @classmethod
    def get_mapping_by_slug(cls, slug: str) -> Optional[TeamMapping]:
        """
        通过OddsPortal slug获取映射

        Args:
            slug: OddsPortal URL slug (e.g., "real-madrid", "rayo-vallecano")

        Returns:
            TeamMapping对象，如果不存在则返回None
        """
        cls.initialize()

        # 标准化slug（移除多余字符）
        normalized_slug = slug.strip().lower()

        # 直接匹配
        if normalized_slug in cls._TEAM_MAPPINGS:
            return cls._TEAM_MAPPINGS[normalized_slug]

        # 尝试模糊匹配（处理连字符差异）
        for key, mapping in cls._TEAM_MAPPINGS.items():
            # 移除连字符后比较
            if key.replace('-', '') == normalized_slug.replace('-', ''):
                return mapping

        return None

    @classmethod
    def get_fotmob_id_by_slug(cls, slug: str) -> Optional[int]:
        """
        通过OddsPortal slug获取FotMob ID

        Args:
            slug: OddsPortal URL slug

        Returns:
            FotMob ID，如果不存在则返回None
        """
        mapping = cls.get_mapping_by_slug(slug)
        return mapping.fotmob_id if mapping else None

    @classmethod
    def normalize_team_name(cls, raw_name: str) -> Optional[str]:
        """
        标准化队名（废弃split('-')逻辑）

        Args:
            raw_name: 原始队名（可能来自URL解析）

        Returns:
            标准化的FotMob队名，如果无法识别则返回None
        """
        cls.initialize()

        # 标准化输入
        normalized = raw_name.strip().lower()

        # 直接查找
        for mapping in cls._TEAM_MAPPINGS.values():
            if (mapping.oddsportal_slug == normalized or
                mapping.oddsportal_slug.replace('-', '') == normalized.replace('-', '')):
                return mapping.fotmob_name

        # 无法识别
        logger.warning(f"[TeamNameRegistry] ⚠️ 无法识别队名: {raw_name}")
        return None

    @classmethod
    def get_all_teams(cls, league: Optional[str] = None) -> list[TeamMapping]:
        """
        获取所有支球队

        Args:
            league: 可选的联赛过滤器

        Returns:
            TeamMapping列表
        """
        cls.initialize()

        if league:
            return [m for m in cls._TEAM_MAPPINGS.values() if m.league == league]
        return list(cls._TEAM_MAPPINGS.values())


# 单例模式
_registry_instance: Optional[TeamNameRegistry] = None


def get_team_registry() -> TeamNameRegistry:
    """获取TeamNameRegistry单例"""
    global _registry_instance
    if _registry_instance is None:
        _registry_instance = TeamNameRegistry()
        _registry_instance.initialize()
    return _registry_instance
