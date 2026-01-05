#!/usr/bin/env python3
"""
V69.1 Advanced Fuzzy Matcher - 高级模糊匹配引擎

核心特性：
1. 名称归一化（移除 FC、Utd、变音符号等）
2. Levenshtein 距离相似度匹配
3. 双向匹配策略（主队/客队）
4. 详细的匹配日志
"""

import logging
import re
import unicodedata
from typing import Optional, Tuple, List
from fuzzywuzzy import fuzz, process

logger = logging.getLogger(__name__)


class AdvancedFuzzyMatcher:
    """高级模糊匹配器"""

    def __init__(self, similarity_threshold: float = 0.85):
        """
        初始化模糊匹配器

        Args:
            similarity_threshold: 相似度阈值 (0-1)，默认 0.85
        """
        self.threshold = similarity_threshold
        self.match_cache = {}

        # 扩充的球队名称映射表
        self.team_aliases = {
            # 德甲
            "bayern": ["bayern munchen", "bayern munich", "fc bayern", "fc bayern munchen"],
            "bayern münchen": ["bayern munchen", "bayern munich", "fc bayern"],
            "bayer leverkusen": ["leverkusen", "bayer 04", "bayer04 leverkusen"],
            "borussia dortmund": ["dortmund", "bvb", "borussia"],
            "borussia monchengladbach": ["monchengladbach", "gladbach", "borussia mg",
                                        "b. monchengladbach", "fcm"],
            "union berlin": ["union", "fc union berlin"],
            "rb leipzig": ["leipzig", "rasenballsport", "rb"],
            "vfb stuttgart": ["stuttgart", "vfb"],
            "eintracht frankfurt": ["frankfurt", "eintracht", "sg frankfurt"],
            "werder bremen": ["bremen", "werder", "sv werder"],
            "vfl wolfsburg": ["wolfsburg", "vfl"],
            "sc freiburg": ["freiburg", "sportclub", "sc"],
            "mainz 05": ["mainz", "fsv mainz", "mainz 05"],
            "1 fc koln": ["koln", "fc koln", "cologne", "1. fc koln"],
            "tsg hoffenheim": ["hoffenheim", "tsg", "hof"],
            "vfl bochum": ["bochum", "vfl"],
            "fc augsburg": ["augsburg", "fca", "fvs"],
            "fc heidenheim": ["heidenheim", "fch"],
            "darmstadt 98": ["darmstadt", "sv darmstadt"],

            # 英超
            "manchester city": ["man city", "manchester", "mcfc", "city"],
            "manchester united": ["man united", "manchester utd", "man utd", "united", "mufc"],
            "liverpool": ["fc liverpool", "lfc", "reds"],
            "chelsea": ["fc chelsea", "the blues", "cfc"],
            "arsenal": ["arsenal fc", "gunners", "afc"],
            "tottenham hotspur": ["tottenham", "spurs", "tot"],
            "west ham united": ["west ham", "whu", "the hammers"],
            "newcastle united": ["newcastle", "newcastle utd", "the magpies", "nufc"],
            "aston villa": ["villa", "aston", "avfc"],
            "brighton hove albion": ["brighton", "seagulls", "bha"],
            "wolverhampton wanderers": ["wolves", "wolverhampton", "wwfc"],
            "crystal palace": ["palace", "cpfc", "eagles"],
            "afc bournemouth": ["bournemouth", "the cherries"],
            "fulham": ["fulham fc", "the cottagers"],
            "leeds united": ["leeds", "leeds utd", "whites"],
            "southampton": ["southampton fc", "saints"],
            "nottingham forest": ["nottingham", "nottingham forest", "nffc", "forest"],
            "leicester city": ["leicester", "lcfc", "foxes"],
            "everton": ["everton fc", "the toffees"],
            "luton town": ["luton", "the hatters"],
            "burnley": ["burnley fc", "the clarets"],
            "sheffield united": ["sheffield", "sheffield utd", "the blades"],
            "west bromwich albion": ["west brom", "wba", "the baggies"],
            "norwich city": ["norwich", "ncfc", "canaries"],
            "watford": ["watford fc", "the hornets"],

            # 西甲
            "real madrid": ["madrid", "real", "los blancos", "rm"],
            "fc barcelona": ["barcelona", "barca", "fcb"],
            "atletico madrid": ["atletico", "atleti", "atletico de madrid"],
            "sevilla fc": ["sevilla", "sevilla fc"],
            "real betis": ["betis", "real betis balompie"],
            "valencia cf": ["valencia", "valencia cf", "los murcielagos"],
            "athletic bilbao": ["athletic", "bilbao", "athletic club"],
            "real sociedad": ["sociedad", "real sociedad", "errealak"],
            "villarreal cf": ["villarreal", "villareal", "yellow submarine"],
            "real valladolid": ["valladolid", "real valladolid"],
            "getafe cf": ["getafe", "getafe cf"],
            "rcd mallorca": ["mallorca", "rcd mallorca"],
            "rayo vallecano": ["rayo", "rayo vallecano"],
            "ca osasuna": ["osasuna", "ca osasuna", "rojillos"],
            "ud almeria": ["almeria", "ud almeria"],
            "rcd espanyol": ["espanyol", "espanyol", "pericos"],
            "cd leganes": ["leganes", "cd leganes", "pepineros"],

            # 意甲
            "juventus": ["juve", "juventus fc", "bianconeri"],
            "inter milan": ["inter", "internazionale", "nerazzurri"],
            "ac milan": ["milan", "milan ac", "rossoneri"],
            "ssc napoli": ["napoli", "naples", " partenopei"],
            "as roma": ["roma", "roma fc", "giallorossi"],
            "ss lazio": ["lazio", "lazio fc", "biancocelesti"],
            "atalanta bc": ["atalanta", "atalanta bergamo", "la dea"],
            "fiorentina": ["ac fiorentina", "viola"],
            "torino fc": ["torino", "torino fc", "granata"],
            "bologna fc": ["bologna", "bologna fc 1909"],
            "sassuolo": ["us sassuolo", "sassuolo calcio"],
            "udinese calcio": ["udinese", "udinese fc"],
            "sampdoria": ["uc sampdoria", "sampdoria", "blucerchiati"],
            "genoa cfc": ["genoa", "genoa cfc", "rossoblu"],
            "hellas verona": ["verona", "hellas verona fc", "scaligeri"],
            "usc crema": ["cremonese", "usc crema 1919"],

            # 法甲
            "psg": ["paris saint-germain", "paris sg", "paris"],
            "as monaco": ["monaco", "as monaco fc", "les rouge et blanc"],
            "olympique marseille": ["marseille", "om", "olympique de marseille"],
            "olympique lyon": ["lyon", "ol", "olympique lyonnais"],
            "stade rennais": ["rennes", "stade rennais fc", "les rouge et noir"],
            "fc lorient": ["lorient", "fc lorient", "les merlus"],
            "ogc nice": ["nice", "nice fc", "les aiglons"],
            "as saint-etienne": ["saint-etienne", "as saint-etienne", "les verts"],
            "fc nantes": ["nantes", "fc nantes", "les canaris"],
            "montpellier hsc": ["montpellier", "montpellier hsc", "paillade"],
            "rc strasbourg": ["strasbourg", "rc strasbourg alsace", "racing"],
            "stade brestois": ["brest", "stade brestois 29", "brestois"],
            "stade de reims": ["reims", "stade de reims", "rouges"],
            "toulouse fc": ["toulouse", "tfc", "le tet"],
            "fc metz": ["metz", "fc metz", "les grenats"],
        }

    def normalize_team_name(self, name: str) -> str:
        """
        归一化球队名称

        处理步骤：
        1. 转小写
        2. 移除变音符号 (München -> Munchen)
        3. 移除常见缩写后缀 (FC, Utd, BSC 等)
        4. 统一空格和连字符
        """
        if not name:
            return ""

        # 转小写
        normalized = name.lower()

        # 移除变音符号
        normalized = unicodedata.normalize('NFKD', normalized)
        normalized = ''.join([c for c in normalized if not unicodedata.combining(c)])

        # 移除常见后缀（保留核心名称）
        suffixes = [
            r'\s+fc$', r'\s+f\.c\.$', r'\s+f\.c$',
            r'\s+utd$', r'\s+united$',
            r'\s+bsc$',
            r'\s+ac$',
            r'\s+cf$',
            r'\s+sc$',
            r'\s+sv$',
            r'\s+as$',
            r'\s+bc$',
            r'\s+rc$',
            r'\s+cd$',
            r'\s+uc$',
            r'\s+usc$',
            r'\s+hsc$',
            r'\s+sg$',
            r'\s+afcf?$',
            r'\s+\d{2}$',  # 移除 05, 98 等年份后缀
        ]

        for suffix in suffixes:
            normalized = re.sub(suffix, '', normalized, flags=re.IGNORECASE)

        # 统一空格和连字符
        normalized = re.sub(r'[\s\-]+', ' ', normalized)

        # 移除首尾空格
        normalized = normalized.strip()

        return normalized

    def get_team_variants(self, team_name: str) -> List[str]:
        """获取球队名称的所有变体"""
        normalized = self.normalize_team_name(team_name)
        variants = [normalized]

        # 从映射表中查找变体
        for key, aliases in self.team_aliases.items():
            key_norm = self.normalize_team_name(key)
            if normalized == key_norm or normalized in [self.normalize_team_name(a) for a in aliases]:
                variants.extend([self.normalize_team_name(a) for a in aliases])
                break

        return list(set(variants))  # 去重

    def calculate_similarity(self, str1: str, str2: str) -> float:
        """
        计算两个字符串的相似度

        使用多种算法的组合：
        1. Token Sort Ratio (忽略词序)
        2. Partial Ratio (部分匹配)
        3. Simple Ratio (完全匹配)

        返回最高相似度 (0-100)
        """
        # 缓存键
        cache_key = f"{str1}|{str2}"
        if cache_key in self.match_cache:
            return self.match_cache[cache_key]

        # 多种算法组合
        ratios = [
            fuzz.token_sort_ratio(str1, str2),      # 忽略词序
            fuzz.partial_ratio(str1, str2),          # 部分匹配
            fuzz.ratio(str1, str2),                  # 完全匹配
            fuzz.token_set_ratio(str1, str2),        # 集合匹配
        ]

        max_ratio = max(ratios)
        self.match_cache[cache_key] = max_ratio

        return max_ratio / 100.0  # 转换为 0-1 范围

    def match_teams(self, url_team: str, db_home: str, db_away: str) -> Tuple[bool, Optional[str], float]:
        """
        匹配 URL 中的球队名称与数据库中的主客队

        Args:
            url_team: URL 中提取的球队名称（可能被连字符分割）
            db_home: 数据库中的主队名称
            db_away: 数据库中的客队名称

        Returns:
            (is_match, matched_team_name, similarity_score)
        """
        # 归一化 URL 球队名称
        url_normalized = self.normalize_team_name(url_team)

        # 获取变体
        url_variants = self.get_team_variants(url_team)

        # 获取数据库球队变体
        home_variants = self.get_team_variants(db_home)
        away_variants = self.get_team_variants(db_away)

        # 尝试所有组合
        best_match = None
        best_score = 0.0

        for url_var in url_variants:
            for home_var in home_variants:
                score = self.calculate_similarity(url_var, home_var)
                if score > best_score:
                    best_score = score
                    best_match = db_home

                # 精确匹配直接返回
                if url_var == home_var:
                    return True, db_home, 1.0

            for away_var in away_variants:
                score = self.calculate_similarity(url_var, away_var)
                if score > best_score:
                    best_score = score
                    best_match = db_away

                # 精确匹配直接返回
                if url_var == away_var:
                    return True, db_away, 1.0

        # 判断是否达到阈值
        is_match = best_score >= self.threshold

        return is_match, best_match, best_score

    def parse_match_from_url(self, url_path: str) -> Tuple[Optional[str], Optional[str], str]:
        """
        从 URL 路径中解析球队名称

        Args:
            url_path: URL 路径，如 "/football/england/premier-league-2024-2025/manchester-united-liverpool-AbCdEfG/"

        Returns:
            (home_team, away_team, league_season)
        """
        # 提取最后一段（球队名称部分）
        parts = url_path.strip('/').split('/')
        if len(parts) < 2:
            return None, None, ""

        match_part = parts[-1]

        # 移除哈希后缀（7 位字母数字，大小写混合）
        match_part = re.sub(r'-[A-Za-z0-9]{7,}$', '', match_part)

        # 分割球队名称
        teams = match_part.split('-')

        if len(teams) < 2:
            return None, None, ""

        # 尝试不同的分割点
        best_split = 1
        best_score = 0

        for split_idx in range(1, min(len(teams), 5)):
            home_candidate = ' '.join(teams[:split_idx])
            away_candidate = ' '.join(teams[split_idx:])

            # 检查是否是已知的球队名称
            home_norm = self.normalize_team_name(home_candidate)
            away_norm = self.normalize_team_name(away_candidate)

            # 检查是否在别名表中
            home_in_aliases = any(home_norm in [self.normalize_team_name(a) for a in aliases]
                                  for aliases in self.team_aliases.values())
            away_in_aliases = any(away_norm in [self.normalize_team_name(a) for a in aliases]
                                  for aliases in self.team_aliases.values())

            score = (1.0 if home_in_aliases else 0.5) + (1.0 if away_in_aliases else 0.5)

            if score > best_score:
                best_score = score
                best_split = split_idx

        # 构建最终球队名称
        home_team = ' '.join(teams[:best_split])
        away_team = ' '.join(teams[best_split:])

        # 提取联赛和赛季信息
        league_season = ""
        if len(parts) >= 5:
            league_season = parts[-2]  # premier-league-2024-2025

        return home_team, away_team, league_season


def test_matcher():
    """测试模糊匹配器"""
    matcher = AdvancedFuzzyMatcher(similarity_threshold=0.85)

    test_cases = [
        # (url_team, db_home, db_awway, expected_match, expected_team)
        ("manchester-united", "Manchester United", "Liverpool", True, "Manchester United"),
        ("manchester-utd", "Manchester United", "Liverpool", True, "Manchester United"),
        ("man-utd", "Manchester United", "Liverpool", True, "Manchester United"),
        ("manchester", "Manchester City", "Liverpool", True, "Manchester City"),
        ("bayern-munchen", "Bayern München", "Dortmund", True, "Bayern München"),
        ("bayer-04", "Bayer Leverkusen", "Mainz 05", True, "Bayer Leverkusen"),
        ("borussia-mg", "Borussia Mönchengladbach", "Leverkusen", True, "Borussia Mönchengladbach"),
        ("fc-koln", "1. FC Köln", "Leverkusen", True, "1. FC Köln"),
        (" Tottenham", "Tottenham Hotspur", "Arsenal", True, "Tottenham Hotspur"),
        ("inter-milan", "Inter Milan", "AC Milan", True, "Inter Milan"),
    ]

    print("=" * 80)
    print("V69.1 Advanced Fuzzy Matcher - 测试报告")
    print("=" * 80)

    passed = 0
    failed = 0

    for url_team, db_home, db_away, expected, expected_team in test_cases:
        is_match, matched_name, score = matcher.match_teams(url_team, db_home, db_away)

        status = "✅" if is_match == expected else "❌"
        if is_match == expected:
            passed += 1
        else:
            failed += 1

        print(f"{status} '{url_team}' vs ('{db_home}', '{db_away}')")
        print(f"   匹配: {is_match} | 得分: {score:.2f} | 匹配到: {matched_name}")

        if is_match != expected:
            print(f"   预期: {expected} (匹配到: {expected_team})")

    print("=" * 80)
    print(f"通过: {passed}/{len(test_cases)} | 失败: {failed}/{len(test_cases)}")
    print(f"测试通过率: {100.0 * passed / len(test_cases):.1f}%")
    print("=" * 80)


if __name__ == "__main__":
    test_matcher()
