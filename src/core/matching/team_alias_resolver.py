"""
V38.0 智能球队名映射系统
========================
解决不同数据源中球队名称不一致的模糊匹配问题

技术栈:
- RapidFuzz: 字符串相似度计算
- Double Metaphone: 语音编码匹配（处理拼写错误）
- 别名映射表: 预置常见缩写和多数据源命名

@module core.matching.team_alias_resolver
@version V38.0-MATCHING
@date 2026-03-17
"""

from typing import Dict, List, Optional, Tuple
from rapidfuzz import fuzz
from metaphone import doublemetaphone


class TeamAliasResolver:
    """
    智能球队名解析器
    
    功能:
    1. 缩写识别 (Man Utd -> Manchester United)
    2. 拼写容错 (Leisester -> Leicester City)
    3. 语音匹配 (使用 Double Metaphone)
    4. 跨数据源对齐 (FotMob vs Bet365)
    """
    
    # 欧冠/英超球队别名映射表
    ALIAS_TABLE = {
        # 英超 Big 6
        "Manchester United": {
            "aliases": ["Man Utd", "Man United", "Man U", "MUFC", "Manchester Utd"],
            "phonetic_key": "MNXT",
            "sources": {
                "fotmob": "Manchester United",
                "espn": "Manchester United",
                "oddsportal": "Manchester United",
                "bet365": "Man Utd"
            }
        },
        "Manchester City": {
            "aliases": ["Man City", "MCFC", "Manchester C", "City"],
            "phonetic_key": "MNXT",
            "sources": {
                "fotmob": "Manchester City",
                "espn": "Manchester City",
                "oddsportal": "Manchester City",
                "bet365": "Man City"
            }
        },
        "Liverpool": {
            "aliases": ["Liverpool FC", "LFC"],
            "phonetic_key": "LFRP",
            "sources": {
                "fotmob": "Liverpool",
                "espn": "Liverpool",
                "oddsportal": "Liverpool",
                "bet365": "Liverpool"
            }
        },
        "Chelsea": {
            "aliases": ["Chelsea FC", "CFC", "Chelsey"],  # Chelsey=拼写容错
            "phonetic_key": "XLS",
            "sources": {
                "fotmob": "Chelsea",
                "espn": "Chelsea",
                "oddsportal": "Chelsea",
                "bet365": "Chelsea"
            }
        },
        "Arsenal": {
            "aliases": ["Arsenal FC", "AFC"],
            "phonetic_key": "ARSN",
            "sources": {
                "fotmob": "Arsenal",
                "espn": "Arsenal",
                "oddsportal": "Arsenal",
                "bet365": "Arsenal"
            }
        },
        "Tottenham Hotspur": {
            "aliases": ["Tottenham", "Spurs", "Tottenham Hotspurs"],
            "phonetic_key": "TTNM",
            "sources": {
                "fotmob": "Tottenham Hotspur",
                "espn": "Tottenham Hotspur",
                "oddsportal": "Tottenham Hotspur",
                "bet365": "Spurs"
            }
        },
        # 西甲豪门
        "Real Madrid": {
            "aliases": ["R. Madrid", "Real Madird", "RM", "RMA"],  # Madird=拼写容错
            "phonetic_key": "RL",
            "sources": {
                "fotmob": "Real Madrid",
                "espn": "Real Madrid",
                "oddsportal": "Real Madrid",
                "bet365": "R. Madrid"
            }
        },
        "Barcelona": {
            "aliases": ["Barca", "FC Barcelona", "FCB"],
            "phonetic_key": "PRSL",
            "sources": {
                "fotmob": "Barcelona",
                "espn": "Barcelona",
                "oddsportal": "Barcelona",
                "bet365": "Barcelona"
            }
        },
        # 德甲
        "Bayern Munich": {
            "aliases": ["Bayern München", "Bayern Muenchen", "FC Bayern", "Bayern M"],
            "phonetic_key": "PN",
            "sources": {
                "fotmob": "Bayern Munich",
                "espn": "Bayern Munich",
                "oddsportal": "Bayern Munich",
                "bet365": "Bayern Munich"
            }
        },
        # 其他英超球队（拼写容错测试用）
        "Leicester City": {
            "aliases": ["Leicester", "Leisester", "Foxes"],  # Leisester=常见拼写错误
            "phonetic_key": "LSTR",
            "sources": {
                "fotmob": "Leicester City",
                "espn": "Leicester City",
                "oddsportal": "Leicester City",
                "bet365": "Leicester"
            }
        },
        "Brighton": {
            "aliases": ["Brighton & Hove Albion", "Brighten"],  # Brighten=发音相似
            "phonetic_key": "PRTN",
            "sources": {
                "fotmob": "Brighton",
                "espn": "Brighton",
                "oddsportal": "Brighton",
                "bet365": "Brighton"
            }
        },
        # 英超其他球队（补充完整）
        "Everton": {
            "aliases": ["Everton FC", "EFC", "Toffees"],
            "phonetic_key": "EVRT",
            "sources": {
                "fotmob": "Everton",
                "espn": "Everton",
                "oddsportal": "Everton",
                "bet365": "Everton"
            }
        },
        "West Ham United": {
            "aliases": ["West Ham", "WHU", "Hammers"],
            "phonetic_key": "WSTH",
            "sources": {
                "fotmob": "West Ham United",
                "espn": "West Ham United",
                "oddsportal": "West Ham United",
                "bet365": "West Ham"
            }
        },
        "AFC Bournemouth": {
            "aliases": ["Bournemouth", "AFCB", "Cherries"],
            "phonetic_key": "PRNM",
            "sources": {
                "fotmob": "AFC Bournemouth",
                "espn": "AFC Bournemouth",
                "oddsportal": "Bournemouth",
                "bet365": "Bournemouth"
            }
        },
        "Newcastle United": {
            "aliases": ["Newcastle", "NUFC", "Magpies"],
            "phonetic_key": "NKSL",
            "sources": {
                "fotmob": "Newcastle United",
                "espn": "Newcastle United",
                "oddsportal": "Newcastle United",
                "bet365": "Newcastle"
            }
        },
        "Aston Villa": {
            "aliases": ["Villa", "AVFC"],
            "phonetic_key": "ASTF",
            "sources": {
                "fotmob": "Aston Villa",
                "espn": "Aston Villa",
                "oddsportal": "Aston Villa",
                "bet365": "Aston Villa"
            }
        },
        "Wolverhampton Wanderers": {
            "aliases": ["Wolves", "Wolverhampton", "WWFC"],
            "phonetic_key": "WLFR",
            "sources": {
                "fotmob": "Wolverhampton Wanderers",
                "espn": "Wolverhampton Wanderers",
                "oddsportal": "Wolves",
                "bet365": "Wolves"
            }
        },
        "Crystal Palace": {
            "aliases": ["Palace", "CPFC", "Eagles"],
            "phonetic_key": "KRST",
            "sources": {
                "fotmob": "Crystal Palace",
                "espn": "Crystal Palace",
                "oddsportal": "Crystal Palace",
                "bet365": "Crystal Palace"
            }
        },
        "Fulham": {
            "aliases": ["Fulham FC", "FFC", "Cottagers"],
            "phonetic_key": "FLM",
            "sources": {
                "fotmob": "Fulham",
                "espn": "Fulham",
                "oddsportal": "Fulham",
                "bet365": "Fulham"
            }
        },
        "Brentford": {
            "aliases": ["Brentford FC", "BFC", "Bees"],
            "phonetic_key": "PRNT",
            "sources": {
                "fotmob": "Brentford",
                "espn": "Brentford",
                "oddsportal": "Brentford",
                "bet365": "Brentford"
            }
        },
        "Nottingham Forest": {
            "aliases": ["Nott'm Forest", "Forest", "NFFC"],
            "phonetic_key": "NTFN",
            "sources": {
                "fotmob": "Nottingham Forest",
                "espn": "Nottingham Forest",
                "oddsportal": "Nottingham Forest",
                "bet365": "Nott'm Forest"
            }
        },
        "Ipswich Town": {
            "aliases": ["Ipswich", "ITFC", "Tractor Boys"],
            "phonetic_key": "IPSW",
            "sources": {
                "fotmob": "Ipswich Town",
                "espn": "Ipswich Town",
                "oddsportal": "Ipswich",
                "bet365": "Ipswich"
            }
        },
        "Southampton": {
            "aliases": ["Southampton FC", "SFC", "Saints"],
            "phonetic_key": "STHM",
            "sources": {
                "fotmob": "Southampton",
                "espn": "Southampton",
                "oddsportal": "Southampton",
                "bet365": "Southampton"
            }
        },
        # 2023-2026赛季升降级球队
        "Luton Town": {
            "aliases": ["Luton", "Luton FC", "Hatters", "Lutton"],
            "phonetic_key": "LTN",
            "sources": {
                "fotmob": "Luton Town",
                "espn": "Luton Town",
                "oddsportal": "Luton Town",
                "bet365": "Luton"
            }
        },
        "Burnley": {
            "aliases": ["Burnley FC", "Clarets", "Burnly"],
            "phonetic_key": "PRNL",
            "sources": {
                "fotmob": "Burnley",
                "espn": "Burnley",
                "oddsportal": "Burnley",
                "bet365": "Burnley"
            }
        },
        "Sheffield United": {
            "aliases": ["Sheffield Utd", "Sheffield", "Blades", "Sheff Utd", "Sheff United"],
            "phonetic_key": "XFLT",
            "sources": {
                "fotmob": "Sheffield United",
                "espn": "Sheffield United",
                "oddsportal": "Sheffield United",
                "bet365": "Sheffield Utd"
            }
        },
        "Leeds United": {
            "aliases": ["Leeds", "Leeds Utd", "LUFC", "Whites", "Leads"],
            "phonetic_key": "LTS",
            "sources": {
                "fotmob": "Leeds United",
                "espn": "Leeds United",
                "oddsportal": "Leeds United",
                "bet365": "Leeds"
            }
        },
        "Sunderland": {
            "aliases": ["Sunderland AFC", "Black Cats", "Sunderland FC", "Sunderand"],
            "phonetic_key": "SNTR",
            "sources": {
                "fotmob": "Sunderland",
                "espn": "Sunderland",
                "oddsportal": "Sunderland",
                "bet365": "Sunderland"
            }
        },
        "West Bromwich Albion": {
            "aliases": ["West Brom", "WBA", "West Bromwich", "Baggies"],
            "phonetic_key": "WSTB",
            "sources": {
                "fotmob": "West Bromwich Albion",
                "espn": "West Bromwich Albion",
                "oddsportal": "West Brom",
                "bet365": "West Brom"
            }
        },
        "Watford": {
            "aliases": ["Watford FC", "Hornets"],
            "phonetic_key": "WTRT",
            "sources": {
                "fotmob": "Watford",
                "espn": "Watford",
                "oddsportal": "Watford",
                "bet365": "Watford"
            }
        },
        "Norwich City": {
            "aliases": ["Norwich", "Canaries", "Norwich FC"],
            "phonetic_key": "NRKX",
            "sources": {
                "fotmob": "Norwich City",
                "espn": "Norwich City",
                "oddsportal": "Norwich",
                "bet365": "Norwich"
            }
        }
    }
    
    def __init__(self, similarity_threshold: float = 0.7):
        """
        初始化解析器
        
        Args:
            similarity_threshold: 相似度阈值（0-1），低于此值视为不匹配
        """
        self.similarity_threshold = similarity_threshold
        
        # 构建反向查找表（从别名到标准名）
        self._alias_to_standard = {}
        for standard_name, data in self.ALIAS_TABLE.items():
            # 标准名映射到自己
            self._alias_to_standard[standard_name.lower()] = standard_name
            # 别名映射到标准名
            for alias in data.get("aliases", []):
                self._alias_to_standard[alias.lower()] = standard_name
    
    def resolve(self, raw_name: str) -> Optional[str]:
        """
        解析球队名，返回标准化名称
        
        匹配策略（按优先级）:
        1. 直接映射表查找（O(1)）
        2. 模糊字符串匹配（RapidFuzz）
        3. 语音编码匹配（Double Metaphone）
        
        Args:
            raw_name: 原始输入的球队名
            
        Returns:
            标准化球队名，或 None（如果无法匹配）
        """
        if not raw_name:
            return None
            
        raw_lower = raw_name.lower().strip()
        
        # 策略 1: 直接映射表查找
        if raw_lower in self._alias_to_standard:
            return self._alias_to_standard[raw_lower]
        
        # 策略 2: 模糊字符串匹配
        best_match = None
        best_score = 0.0
        
        for alias, standard in self._alias_to_standard.items():
            # 使用 token_set_ratio 处理词序变化
            score = fuzz.token_set_ratio(raw_lower, alias) / 100.0
            
            if score > best_score:
                best_score = score
                best_match = standard
        
        if best_score >= self.similarity_threshold:
            return best_match
        
        # 策略 3: 语音编码匹配（处理拼写错误）
        phonetic_match = self._phonetic_match(raw_name)
        if phonetic_match:
            return phonetic_match
        
        # 无匹配，返回 None
        return None
    
    def resolve_for_source(self, raw_name: str, source: str) -> Optional[str]:
        """
        针对特定数据源解析球队名
        
        不同数据源可能有不同的命名习惯，此方法先解析为标准名，
        然后返回该数据源对应的命名。
        
        Args:
            raw_name: 原始球队名
            source: 数据源标识 (fotmob, espn, bet365, oddsportal, ...)
            
        Returns:
            该数据源的标准命名
        """
        # 先解析为标准名
        standard = self.resolve(raw_name)
        if not standard:
            return raw_name  # 无法解析，返回原样
        
        # 查找该数据源对应的命名
        team_data = self.ALIAS_TABLE.get(standard)
        if team_data and "sources" in team_data:
            source_name = team_data["sources"].get(source.lower())
            if source_name:
                return source_name
        
        return standard  # 返回标准名作为 fallback
    
    def resolve_batch(self, raw_names: List[str]) -> List[Optional[str]]:
        """
        批量解析球队名
        
        Args:
            raw_names: 原始球队名列表
            
        Returns:
            标准化名称列表
        """
        return [self.resolve(name) for name in raw_names]
    
    def calculate_similarity(self, name1: str, name2: str) -> float:
        """
        计算两个球队名的相似度
        
        Args:
            name1: 第一个名称
            name2: 第二个名称
            
        Returns:
            相似度分数 (0-1)
        """
        if not name1 or not name2:
            return 0.0
            
        return fuzz.token_set_ratio(name1.lower(), name2.lower()) / 100.0
    
    def _phonetic_match(self, raw_name: str) -> Optional[str]:
        """
        使用 Double Metaphone 进行语音匹配
        
        Double Metaphone 是一种语音算法，将相似发音的单词编码为相同的键。
        例如：
        - "Leicester" -> ['LSTR', '']
        - "Leisester" -> ['LSTR', ''] (相同编码)
        
        Args:
            raw_name: 原始名称
            
        Returns:
            匹配的标准名，或 None
        """
        # 获取输入的语音编码
        raw_phonetic = doublemetaphone(raw_name)
        
        best_match = None
        best_score = 0.0
        
        for standard_name, data in self.ALIAS_TABLE.items():
            # 计算标准名的语音编码
            standard_phonetic = data.get("phonetic_key", "")
            
            # 计算语音相似度
            score = self._phonetic_similarity(raw_phonetic, standard_phonetic)
            
            if score > best_score and score >= self.similarity_threshold:
                best_score = score
                best_match = standard_name
        
        return best_match
    
    def _phonetic_similarity(self, phonetic1: Tuple[str, str], phonetic2: str) -> float:
        """
        计算两个语音编码的相似度
        
        Args:
            phonetic1: (primary, secondary) 元组
            phonetic2: 目标语音键
            
        Returns:
            相似度 (0-1)
        """
        primary, secondary = phonetic1
        
        # 主编码匹配
        if primary == phonetic2:
            return 1.0
        
        # 次编码匹配
        if secondary and secondary == phonetic2:
            return 0.9
        
        # 部分匹配（前缀）
        if primary and phonetic2 and (primary.startswith(phonetic2) or phonetic2.startswith(primary)):
            return 0.7
        
        return 0.0
    
    def add_team(self, standard_name: str, aliases: List[str], 
                 phonetic_key: str = "", sources: Dict[str, str] = None):
        """
        动态添加球队映射
        
        Args:
            standard_name: 标准球队名
            aliases: 别名列表
            phonetic_key: 语音编码（可选，会自动计算）
            sources: 各数据源对应的命名（可选）
        """
        if not phonetic_key:
            # 自动计算语音编码
            phonetic_key = doublemetaphone(standard_name)[0]
        
        self.ALIAS_TABLE[standard_name] = {
            "aliases": aliases,
            "phonetic_key": phonetic_key,
            "sources": sources or {}
        }
        
        # 更新反向查找表
        self._alias_to_standard[standard_name.lower()] = standard_name
        for alias in aliases:
            self._alias_to_standard[alias.lower()] = standard_name
    
    def get_all_teams(self) -> List[str]:
        """获取所有已知的标准球队名"""
        return list(self.ALIAS_TABLE.keys())


# 便捷函数：全局解析器实例
_resolver_instance = None

def get_resolver() -> TeamAliasResolver:
    """获取全局 TeamAliasResolver 实例"""
    global _resolver_instance
    if _resolver_instance is None:
        _resolver_instance = TeamAliasResolver()
    return _resolver_instance


def resolve_team(raw_name: str) -> Optional[str]:
    """快捷函数：解析球队名"""
    return get_resolver().resolve(raw_name)
