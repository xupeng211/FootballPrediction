"""
数据标准化工具
处理队名、联赛名等数据源的标准化和去重
"""

import json
import re
from typing import Dict, List, Optional, Tuple

from loguru import logger


class TeamNameStandardizer:
    """队名标准化器 - 统一不同数据源的队名差异"""

    def __init__(self):
        # 队名映射表：常见变体 → 标准名称
        self.team_name_mapping = self._load_team_mapping()

        # 预编译正则表达式提高性能
        self.patterns = {
            'fc_suffix': re.compile(r'\s+FC$|\s+F\.C\.$', re.IGNORECASE),
            'afc_suffix': re.compile(r'\s+AFC$|\s+A\.F\.C\.$', re.IGNORECASE),
            'united_suffix': re.compile(r'\s+United$|\s+Utd$|\s+U\.T\.D\.$', re.IGNORECASE),
            'city_suffix': re.compile(r'\s+City$|\s+CITY$', re.IGNORECASE),
            'special_chars': re.compile(r'[^\w\s]'),  # 移除特殊字符
            'extra_spaces': re.compile(r'\s+'),  # 合并多余空格
        }

    def _load_team_mapping(self) -> Dict[str, str]:
        """加载队名映射表"""
        mapping = {
            # 英超
            'manchester united': 'Manchester United',
            'man utd': 'Manchester United',
            'manchester utd': 'Manchester United',
            'man u': 'Manchester United',
            'manchester city': 'Manchester City',
            'man city': 'Manchester City',
            'liverpool': 'Liverpool FC',
            'liverpool fc': 'Liverpool FC',
            'chelsea': 'Chelsea FC',
            'chelsea fc': 'Chelsea FC',
            'arsenal': 'Arsenal FC',
            'arsenal fc': 'Arsenal FC',
            'tottenham': 'Tottenham Hotspur',
            'tottenham hotspur': 'Tottenham Hotspur',
            'spurs': 'Tottenham Hotspur',
            'west ham': 'West Ham United',
            'west ham united': 'West Ham United',
            'leicester city': 'Leicester City',
            'leicester': 'Leicester City',
            'everton': 'Everton FC',
            'everton fc': 'Everton FC',
            'wolves': 'Wolverhampton Wanderers',
            'wolverhampton': 'Wolverhampton Wanderers',
            'newcastle': 'Newcastle United',
            'newcastle united': 'Newcastle United',
            'aston villa': 'Aston Villa',
            'southampton': 'Southampton FC',
            'brighton': 'Brighton & Hove Albion',
            'brighton and hove albion': 'Brighton & Hove Albion',
            'burnley': 'Burnley FC',
            'fulham': 'Fulham FC',
            'west brom': 'West Bromwich Albion',
            'west bromwich albion': 'West Bromwich Albion',

            # 西甲
            'real madrid': 'Real Madrid',
            'barcelona': 'Barcelona',
            'fc barcelona': 'Barcelona',
            'atletico madrid': 'Atletico Madrid',
            'atletico': 'Atletico Madrid',
            'valencia': 'Valencia CF',
            'valencia cf': 'Valencia CF',
            'sevilla': 'Sevilla FC',
            'sevilla fc': 'Sevilla FC',
            'real betis': 'Real Betis',
            'betis': 'Real Betis',
            'real sociedad': 'Real Sociedad',
            'athletic bilbao': 'Athletic Bilbao',
            'villarreal': 'Villarreal CF',
            'villarreal cf': 'Villarreal CF',
            'getafe': 'Getafe CF',
            'getafe cf': 'Getafe CF',
            'alaves': 'Deportivo Alaves',
            'deportivo alaves': 'Deportivo Alaves',

            # 德甲
            'bayern munich': 'Bayern Munich',
            'fc bayern munich': 'Bayern Munich',
            'borussia dortmund': 'Borussia Dortmund',
            'dortmund': 'Borussia Dortmund',
            'rb leipzig': 'RB Leipzig',
            'leipzig': 'RB Leipzig',
            'bayer leverkusen': 'Bayer Leverkusen',
            'leverkusen': 'Bayer Leverkusen',
            'eintracht frankfurt': 'Eintracht Frankfurt',
            'frankfurt': 'Eintracht Frankfurt',
            'wolfsburg': 'VfL Wolfsburg',
            'vfl wolfsburg': 'VfL Wolfsburg',
            'borussia monchengladbach': 'Borussia Mönchengladbach',
            'monchengladbach': 'Borussia Mönchengladbach',
            'union berlin': 'Union Berlin',

            # 意甲
            'juventus': 'Juventus',
            'juventus fc': 'Juventus',
            'inter milan': 'Inter Milan',
            'inter': 'Inter Milan',
            'ac milan': 'AC Milan',
            'milan': 'AC Milan',
            'napoli': 'Napoli',
            'naples': 'Napoli',
            'roma': 'AS Roma',
            'as roma': 'AS Roma',
            'lazio': 'Lazio',
            'ss lazio': 'Lazio',
            'atalanta': 'Atalanta',
            'fiorentina': 'ACF Fiorentina',
            'torino': 'Torino FC',

            # 法甲
            'psg': 'Paris Saint-Germain',
            'paris saint-germain': 'Paris Saint-Germain',
            'olympique lyon': 'Olympique Lyon',
            'lyon': 'Olympique Lyon',
            'olympique marseille': 'Olympique Marseille',
            'marseille': 'Olympique Marseille',
            'monaco': 'AS Monaco',
            'lille': 'Lille OSC',
            'bordeaux': 'FC Girondins de Bordeaux',
            'nantes': 'FC Nantes',
            'nice': 'OGC Nice',
            'strasbourg': 'RC Strasbourg',

            # 葡超
            'porto': 'FC Porto',
            'fc porto': 'FC Porto',
            'benfica': 'SL Benfica',
            'sporting': 'Sporting CP',
            'sporting lisbon': 'Sporting CP',
            'braga': 'SC Braga',

            # 荷甲
            'ajax': 'Ajax Amsterdam',
            'ajax amsterdam': 'Ajax Amsterdam',
            'feyenoord': 'Feyenoord Rotterdam',
            'psv': 'PSV Eindhoven',
            'psv eindhoven': 'PSV Eindhoven',

            # 常见变体模式
            'manchester': 'Manchester United',  # 默认映射
            'london': None,  # 需要更多上下文
        }

        return mapping

    def normalize_team_name(self, team_name: str) -> str:
        """
        标准化队名
        Args:
            team_name: 原始队名
        Returns:
            str: 标准化后的队名
        """
        if not team_name:
            return team_name

        original_name = team_name.strip()
        normalized = original_name.lower()

        # 1. 移除常见后缀并清理
        normalized = self.patterns['fc_suffix'].sub('', normalized)
        normalized = self.patterns['afc_suffix'].sub('', normalized)
        normalized = self.patterns['special_chars'].sub(' ', normalized)
        normalized = self.patterns['extra_spaces'].sub(' ', normalized).strip()

        # 2. 处理 united, city 等特殊后缀
        if self.patterns['united_suffix'].search(normalized):
            # 保留 united 后缀
            pass
        elif self.patterns['city_suffix'].search(normalized):
            # 保留 city 后缀
            pass

        # 3. 直接映射查找
        if normalized in self.team_name_mapping:
            standard_name = self.team_name_mapping[normalized]
            if standard_name:  # 排除 None 值
                logger.debug(f"Team name mapped: '{original_name}' → '{standard_name}'")
                return standard_name

        # 4. 模糊匹配（包含关系）
        for key, value in self.team_name_mapping.items():
            if value and (key in normalized or normalized in key):
                if len(key) > 3:  # 避免过短的匹配
                    logger.debug(f"Team name fuzzy matched: '{original_name}' → '{value}'")
                    return value

        # 5. 如果没有找到匹配，返回清理后的原始名称
        cleaned_name = original_name.strip()
        logger.warning(f"No mapping found for team: '{original_name}', using cleaned name: '{cleaned_name}'")
        return cleaned_name

    def normalize_team_pair(self, home_team: str, away_team: str) -> Tuple[str, str]:
        """
        标准化主客队名称对
        Args:
            home_team: 主队名称
            away_team: 客队名称
        Returns:
            Tuple[str, str]: 标准化后的主客队名称
        """
        normalized_home = self.normalize_team_name(home_team)
        normalized_away = self.normalize_team_name(away_team)

        # 检查是否两队相同（可能是数据错误）
        if normalized_home == normalized_away:
            logger.error(f"Same team detected: home='{home_team}' away='{away_team}' both normalized to '{normalized_home}'")

        return normalized_home, normalized_away

    def add_mapping(self, original: str, standard: str):
        """添加新的队名映射"""
        self.team_name_mapping[original.lower()] = standard
        logger.info(f"Added team mapping: '{original}' → '{standard}'")

    def get_alternative_names(self, standard_name: str) -> List[str]:
        """获取标准名称的所有已知变体"""
        alternatives = []
        standard_lower = standard_name.lower()

        for original, standard in self.team_name_mapping.items():
            if standard and standard.lower() == standard_lower:
                alternatives.append(original.title())

        return alternatives


class LeagueNameStandardizer:
    """联赛名称标准化器"""

    def __init__(self):
        self.league_mapping = {
            # 英格兰
            'premier league': 'Premier League',
            'english premier league': 'Premier League',
            'epl': 'Premier League',
            'championship': 'Championship',
            'league one': 'League One',
            'league two': 'League Two',
            'fa cup': 'FA Cup',

            # 西班牙
            'la liga': 'La Liga',
            'laliga': 'La Liga',
            'segunda division': 'Segunda Division',
            'copa del rey': 'Copa del Rey',

            # 德国
            'bundesliga': 'Bundesliga',
            '2. bundesliga': '2. Bundesliga',
            'dfb pokal': 'DFB Pokal',

            # 意大利
            'serie a': 'Serie A',
            'serie a tim': 'Serie A',
            'serie b': 'Serie B',
            'coppa italia': 'Coppa Italia',

            # 法国
            'ligue 1': 'Ligue 1',
            'ligue 1 uber eats': 'Ligue 1',
            'ligue 2': 'Ligue 2',
            'coupe de france': 'Coupe de France',

            # 欧洲赛事
            'champions league': 'UEFA Champions League',
            'uefa champions league': 'UEFA Champions League',
            'europa league': 'UEFA Europa League',
            'uefa europa league': 'UEFA Europa League',
            'europa conference league': 'UEFA Europa Conference League',
            'uefa europa conference league': 'UEFA Europa Conference League',
        }

    def normalize_league_name(self, league_name: str) -> str:
        """标准化联赛名称"""
        if not league_name:
            return league_name

        normalized = league_name.lower().strip()
        return self.league_mapping.get(normalized, league_name.strip())


class DataValidator:
    """数据验证器 - 验证数据完整性和正确性"""

    @staticmethod
    def validate_match_data(match_data: dict) -> Tuple[bool, List[str]]:
        """
        验证比赛数据
        Args:
            match_data: 比赛数据字典
        Returns:
            Tuple[bool, List[str]]: (是否有效, 错误信息列表)
        """
        errors = []

        # 必填字段检查
        required_fields = ['home_team', 'away_team', 'match_date']
        for field in required_fields:
            if field not in match_data or not match_data[field]:
                errors.append(f"Missing required field: {field}")

        # 比分有效性检查
        if 'home_score' in match_data and match_data['home_score'] is not None:
            if not isinstance(match_data['home_score'], int) or match_data['home_score'] < 0:
                errors.append(f"Invalid home_score: {match_data['home_score']}")

        if 'away_score' in match_data and match_data['away_score'] is not None:
            if not isinstance(match_data['away_score'], int) or match_data['away_score'] < 0:
                errors.append(f"Invalid away_score: {match_data['away_score']}")

        # 期望进球值检查
        for field in ['home_xg', 'away_xg']:
            if field in match_data and match_data[field] is not None:
                xg_value = match_data[field]
                if not isinstance(xg_value, (int, float)) or xg_value < 0 or xg_value > 10:
                    errors.append(f"Invalid {field}: {xg_value} (should be between 0 and 10)")

        # 赔率有效性检查
        for field in ['home_win_odds', 'draw_odds', 'away_win_odds']:
            if field in match_data and match_data[field] is not None:
                odds = match_data[field]
                if not isinstance(odds, (int, float)) or odds <= 1:
                    errors.append(f"Invalid {field}: {odds} (should be > 1)")

        return len(errors) == 0, errors


# 全局实例，方便其他模块直接使用
team_standardizer = TeamNameStandardizer()
league_standardizer = LeagueNameStandardizer()
data_validator = DataValidator()