from typing import Dict, Any, List, Optional, Union
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class BulletproofFeatureExtractor:
    """
    零损耗特征提取器 (Zero-Loss Extraction) - V7.0 Full Spec
    """
    
    def extract(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        主提取入口
        """
        features = {}
        
        # 0. 基础信息 (Meta)
        meta = self._extract_basic_info(data)
        features.update(meta)
        
        # 1. 提取阵容评分 (Lineups & Ratings)
        ratings = self._extract_ratings(data)
        features.update(ratings)
        
        # 2. 提取战术数据 (Tactical Stats)
        tactical = self._extract_tactical_stats(data)
        features.update(tactical)
        
        # 3. 提取基础xG (作为基准验证)
        xg = self._extract_xg(data)
        features.update(xg)
        
        # 4. 提取事件流 (Incidents)
        incidents = self._extract_match_incidents(data)
        features.update(incidents)
        
        # 5. 计算衍生特征 (Derived)
        derived = self._calculate_derived(features)
        features.update(derived)
        
        return features

    def _extract_basic_info(self, data: Dict[str, Any]) -> Dict[str, Any]:
        result = {}
        general = data.get("general")
        if isinstance(general, dict):
            result["home_team"] = general.get("homeTeam", {}).get("name")
            result["away_team"] = general.get("awayTeam", {}).get("name")
            
            time_str = general.get("matchTimeUTCDate")
            if time_str:
                try:
                    result["match_time"] = datetime.fromisoformat(time_str.replace("Z", "+00:00"))
                except ValueError:
                    pass
        return result

    def _extract_ratings(self, data: Dict[str, Any]) -> Dict[str, float]:
        result = {
            "home_avg_rating": None,
            "away_avg_rating": None
        }
        
        content = data.get("content")
        if not isinstance(content, dict):
            return result
            
        lineup = content.get("lineup")
        if not isinstance(lineup, dict):
            return result
        
        team_mapping = {
            "home": ["home", "homeTeam"],
            "away": ["away", "awayTeam"]
        }
        
        for side, keys in team_mapping.items():
            team_data = {}
            for k in keys:
                if k in lineup:
                    team_data = lineup[k]
                    break
            
            if not team_data:
                continue

            players = []
            if "starters" in team_data:
                players = team_data["starters"]
            elif "players" in team_data:
                players = team_data["players"]
            elif "startingXI" in team_data:
                players = team_data["startingXI"]
                
            if not isinstance(players, list):
                continue
                
            valid_ratings = []
            for p in players:
                if not isinstance(p, dict):
                    continue
                
                rating_val = None
                performance = p.get("performance")
                if isinstance(performance, dict):
                    rating_val = performance.get("rating")
                
                if rating_val is None:
                    rating_val = p.get("rating") or p.get("ratingValue") or p.get("playerRating")
                
                try:
                    if rating_val is not None:
                        val = float(rating_val)
                        if 0 < val <= 10:
                            valid_ratings.append(val)
                except (ValueError, TypeError):
                    continue
            
            if valid_ratings:
                avg = sum(valid_ratings) / len(valid_ratings)
                result[f"{side}_avg_rating"] = round(avg, 2)
                
        return result

    def _extract_tactical_stats(self, data: Dict[str, Any]) -> Dict[str, int]:
        result = {
            "home_big_chances_created": None,
            "away_big_chances_created": None,
            "home_total_shots": None,
            "away_total_shots": None,
            "home_possession": None,
            "away_possession": None
        }
        
        content = data.get("content")
        if not isinstance(content, dict):
            return result

        stats_root = content.get("stats")
        if not isinstance(stats_root, dict):
            return result
        
        all_stats_wrapper = stats_root.get("Periods", {}).get("All", {}).get("stats", [])
        
        if not isinstance(all_stats_wrapper, list):
            return result
            
        for group in all_stats_wrapper:
            items = group.get("stats", [])
            if not isinstance(items, list):
                continue
                
            for item in items:
                key = str(item.get("key", "")).lower()
                values = item.get("stats", [])
                
                if not isinstance(values, list) or len(values) < 2:
                    continue
                
                try:
                    v1 = float(values[0]) if values[0] is not None else 0
                    v2 = float(values[1]) if values[1] is not None else 0
                    
                    if key in ["big_chance", "big_chance_created", "big_chances_created"]:
                        result["home_big_chances_created"] = int(v1)
                        result["away_big_chances_created"] = int(v2)
                    elif key in ["total_shots", "shots"]:
                        result["home_total_shots"] = int(v1)
                        result["away_total_shots"] = int(v2)
                    elif key in ["ballpossesion", "possession"]:
                        result["home_possession"] = v1
                        result["away_possession"] = v2
                        
                except (ValueError, TypeError):
                    pass
                        
        return result

    def _extract_xg(self, data: Dict[str, Any]) -> Dict[str, float]:
        result = {"home_xg": None, "away_xg": None}
        
        content = data.get("content")
        if not isinstance(content, dict):
            return result

        stats_root = content.get("stats")
        if not isinstance(stats_root, dict):
            return result

        all_stats_wrapper = stats_root.get("Periods", {}).get("All", {}).get("stats", [])
        
        if isinstance(all_stats_wrapper, list):
            for group in all_stats_wrapper:
                items = group.get("stats", [])
                for item in items:
                    key = str(item.get("key", "")).lower()
                    values = item.get("stats", [])
                    if len(values) >= 2 and key in ["expected_goals", "expectedgoals", "xg"]:
                        try:
                            result["home_xg"] = float(values[0])
                            result["away_xg"] = float(values[1])
                        except (ValueError, TypeError):
                            pass
        return result

    def _extract_match_incidents(self, data: Dict[str, Any]) -> Dict[str, int]:
        result = {
            "home_red_cards": 0, "away_red_cards": 0,
            "home_substitutions": 0, "away_substitutions": 0,
            "home_early_goal": 0, "away_early_goal": 0,
            "home_penalties": 0, "away_penalties": 0 # Won/Scored roughly
        }
        
        content = data.get("content")
        if not isinstance(content, dict):
            return result
            
        events_root = content.get("matchFacts", {}).get("events", {})
        events_list = events_root.get("events", [])
        
        if not isinstance(events_list, list):
            return result
            
        for ev in events_list:
            if not isinstance(ev, dict):
                continue
                
            etype = str(ev.get("type", "")).lower()
            is_home = ev.get("isHome", False)
            time_min = ev.get("time", 999)
            
            prefix = "home" if is_home else "away"
            
            # Red Cards
            if "card" in etype:
                card_val = str(ev.get("card", "")).lower()
                if "red" in card_val:
                    result[f"{prefix}_red_cards"] += 1
            
            # Substitutions
            if "substitution" in etype:
                result[f"{prefix}_substitutions"] += 1
                
            # Goals & Early Goals
            if "goal" in etype:
                if time_min <= 15:
                    result[f"{prefix}_early_goal"] = 1
                
                # Penalties (heuristic via situation or string)
                # In Shotmap event inside?
                # Or just generic check
                # FotMob structure might put shotmapEvent inside
                shot_event = ev.get("shotmapEvent", {})
                situation = shot_event.get("situation", "").lower()
                if "penalty" in situation:
                    result[f"{prefix}_penalties"] += 1
                    
        return result

    def _calculate_derived(self, features: Dict[str, Any]) -> Dict[str, float]:
        derived = {}
        
        # xG per Shot
        for side in ["home", "away"]:
            xg = features.get(f"{side}_xg")
            shots = features.get(f"{side}_total_shots")
            if xg is not None and shots and shots > 0:
                derived[f"{side}_xg_per_shot"] = round(xg / shots, 3)
            else:
                derived[f"{side}_xg_per_shot"] = None
                
        # Rating Diff
        h_rating = features.get("home_avg_rating")
        a_rating = features.get("away_avg_rating")
        if h_rating is not None and a_rating is not None:
            derived["rating_diff"] = round(h_rating - a_rating, 2)
        else:
            derived["rating_diff"] = None
            
        # Possession Efficiency (Goals / Possession) - Simple version
        # Assuming goals are needed, but let's stick to user request
        
        return derived