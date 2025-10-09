"""
特征处理器
Feature Processor

处理预测所需的特征数据。
"""



logger = get_logger(__name__)


class FeatureProcessor:
    """
    特征处理器 / Feature Processor

    负责处理模型预测所需的特征数据。
    Responsible for processing feature data required for model prediction.
    """

    def __init__(self):
        """初始化特征处理器 / Initialize feature processor"""
        self.feature_names = [
            # 基础特征
            "home_team_strength",
            "away_team_strength",
            "home_form",
            "away_form",
            "head_to_head_home_wins",
            "head_to_head_away_wins",
            "head_to_head_draws",

            # 进阶特征
            "home_goals_scored_avg",
            "home_goals_conceded_avg",
            "away_goals_scored_avg",
            "away_goals_conceded_avg",
            "home_shots_avg",
            "away_shots_avg",
            "home_possession_avg",
            "away_possession_avg",

            # 比赛特征
            "is_home_match",
            "match_importance",
            "days_since_last_match",
            "travel_distance",
            "weather_condition",
        ]

    def get_default_features(self) -> Dict[str, Any]:
        """
        获取默认特征值 / Get default feature values

        Returns:
            Dict[str, Any]: 默认特征字典 / Default feature dictionary
        """
        return {
            "home_team_strength": 0.5,
            "away_team_strength": 0.5,
            "home_form": 0.0,
            "away_form": 0.0,
            "head_to_head_home_wins": 0,
            "head_to_head_away_wins": 0,
            "head_to_head_draws": 0,
            "home_goals_scored_avg": 1.0,
            "home_goals_conceded_avg": 1.0,
            "away_goals_scored_avg": 1.0,
            "away_goals_conceded_avg": 1.0,
            "home_shots_avg": 10.0,
            "away_shots_avg": 10.0,
            "home_possession_avg": 50.0,
            "away_possession_avg": 50.0,
            "is_home_match": 1,
            "match_importance": 0.5,
            "days_since_last_match": 7,
            "travel_distance": 0,
            "weather_condition": 1,  # 1: 晴天, 2: 雨天, 3: 雪天
        }

    def prepare_features_for_prediction(self, features: Dict[str, Any]) -> np.ndarray:
        """
        准备用于预测的特征 / Prepare features for prediction

        Args:
            features (Dict[str, Any]): 特征字典 / Feature dictionary

        Returns:
            np.ndarray: 准备好的特征数组 / Prepared feature array
        """
        try:
            # 确保所有必要的特征都存在
            default_features = self.get_default_features()
            processed_features = {}

            for feature_name in self.feature_names:
                value = features.get(feature_name, default_features.get(feature_name, 0))
                processed_features[feature_name] = float(value)

            # 转换为numpy数组
            feature_array = np.array([processed_features[name] for name in self.feature_names])

            # 归一化处理（如果需要）
            feature_array = self._normalize_features(feature_array)

            return feature_array.reshape(1, -1)

        except Exception as e:
            logger.error(f"准备特征失败: {e}")
            raise

    def _normalize_features(self, features: np.ndarray) -> np.ndarray:
        """
        归一化特征 / Normalize features

        Args:
            features (np.ndarray): 原始特征数组 / Original feature array

        Returns:
            np.ndarray: 归一化后的特征数组 / Normalized feature array
        """
        # 这里可以实现各种归一化方法
        # 例如：标准化、最小-最大归一化等

        # 最小-最大归一化（示例）
        # 实际应用中应该使用训练时的统计信息
        normalized = features.copy()

        # 示例归一化范围
        feature_ranges = {
            0: (0, 1),   # home_team_strength
            1: (0, 1),   # away_team_strength
            2: (-3, 3),  # home_form
            3: (-3, 3),  # away_form
            4: (0, 10),  # head_to_head_home_wins
            5: (0, 10),  # head_to_head_away_wins
            6: (0, 10),  # head_to_head_draws
            7: (0, 5),   # home_goals_scored_avg
            8: (0, 5),   # home_goals_conceded_avg
            9: (0, 5),   # away_goals_scored_avg
            10: (0, 5),  # away_goals_conceded_avg
            11: (0, 30), # home_shots_avg
            12: (0, 30), # away_shots_avg
            13: (0, 100), # home_possession_avg
            14: (0, 100), # away_possession_avg
            15: (0, 1),  # is_home_match
            16: (0, 1),  # match_importance
            17: (0, 30), # days_since_last_match
            18: (0, 5000), # travel_distance
            19: (1, 3),  # weather_condition
        }

        for i, (min_val, max_val) in feature_ranges.items():
            if i < len(normalized):
                if max_val > min_val:
                    normalized[i] = (normalized[i] - min_val) / (max_val - min_val)
                else:
                    normalized[i] = 0.5

        return normalized

    def extract_features_from_match_data(self, match_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        从比赛数据中提取特征 / Extract features from match data

        Args:
            match_data (Dict[str, Any]): 比赛数据 / Match data

        Returns:
            Dict[str, Any]: 提取的特征 / Extracted features
        """
        features = {}

        try:
            # 基本信息
            features["home_team_id"] = match_data.get("home_team_id")
            features["away_team_id"] = match_data.get("away_team_id")
            features["match_date"] = match_data.get("match_date")

            # 队伍实力特征
            if "home_team" in match_data:
                home_team = match_data["home_team"]
                features["home_team_strength"] = home_team.get("strength", 0.5)
                features["home_form"] = home_team.get("form", 0.0)
                features["home_goals_scored_avg"] = home_team.get("goals_scored_avg", 1.0)
                features["home_goals_conceded_avg"] = home_team.get("goals_conceded_avg", 1.0)
                features["home_shots_avg"] = home_team.get("shots_avg", 10.0)
                features["home_possession_avg"] = home_team.get("possession_avg", 50.0)

            if "away_team" in match_data:
                away_team = match_data["away_team"]
                features["away_team_strength"] = away_team.get("strength", 0.5)
                features["away_form"] = away_team.get("form", 0.0)
                features["away_goals_scored_avg"] = away_team.get("goals_scored_avg", 1.0)
                features["away_goals_conceded_avg"] = away_team.get("goals_conceded_avg", 1.0)
                features["away_shots_avg"] = away_team.get("shots_avg", 10.0)
                features["away_possession_avg"] = away_team.get("possession_avg", 50.0)

            # 历史交锋数据
            if "head_to_head" in match_data:
                h2h = match_data["head_to_head"]
                features["head_to_head_home_wins"] = h2h.get("home_wins", 0)
                features["head_to_head_away_wins"] = h2h.get("away_wins", 0)
                features["head_to_head_draws"] = h2h.get("draws", 0)

            # 比赛上下文
            features["is_home_match"] = 1  # 默认是主场
            features["match_importance"] = match_data.get("importance", 0.5)
            features["days_since_last_match"] = match_data.get("days_since_last_match", 7)
            features["travel_distance"] = match_data.get("travel_distance", 0)
            features["weather_condition"] = match_data.get("weather", 1)

            return features

        except Exception as e:
            logger.error(f"提取特征失败: {e}")
            return self.get_default_features()

    def validate_features(self, features: Dict[str, Any]) -> bool:
        """
        验证特征数据 / Validate feature data

        Args:
            features (Dict[str, Any]): 特征字典 / Feature dictionary

        Returns:
            bool: 特征是否有效 / Whether features are valid
        """
        required_features = self.feature_names[:10]  # 检查前10个重要特征

        for feature_name in required_features:
            if feature_name not in features:



                logger.warning(f"缺少特征: {feature_name}")
                return False

            value = features[feature_name]
            if not isinstance(value, (int, float)):
                logger.warning(f"特征 {feature_name} 不是数值类型: {type(value)}")
                return False

            if np.isnan(value) or np.isinf(value):
                logger.warning(f"特征 {feature_name} 包含无效值: {value}")
                return False

        return True