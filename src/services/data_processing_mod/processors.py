"""
数据处理器
Data Processors

提供各类数据的处理功能。
"""




logger = get_logger(__name__)


class BaseDataProcessor:
    """数据处理器基类 / Base Data Processor"""

    def __init__(self, name: str):
        """初始化处理器 / Initialize processor"""
        self.name = name
        self.logger = get_logger(f"{__name__}.{name}")


class MatchDataProcessor(BaseDataProcessor):
    """
    比赛数据处理器 / Match Data Processor

    处理原始比赛数据，包括清洗、标准化和验证。
    Processes raw match data including cleaning, standardization, and validation.
    """

    def __init__(self):
        super().__init__("MatchDataProcessor")
        self.data_cleaner: Optional[FootballDataCleaner] = None

    async def initialize(self):
        """初始化处理器 / Initialize processor"""
        self.data_cleaner = FootballDataCleaner()
        self.logger.info("比赛数据处理器初始化完成")

    async def process_raw_match_data(
        self, raw_data: Union[Dict[str, Any], List[Dict[str, Any]]]
    ) -> Optional[Union[Dict[str, Any], pd.DataFrame]]:
        """
        处理原始比赛数据 / Process Raw Match Data

        Args:
            raw_data: 原始比赛数据（字典或字典列表） / Raw match data (dict or list of dicts)

        Returns:
            处理后的数据 / Processed data
        """
        try:
            if not raw_data:
                self.logger.warning("输入数据为空")
                return None

            # 如果是单个字典，转换为列表
            if isinstance(raw_data, dict):
                raw_data = [raw_data]

            # 转换为DataFrame
            df = pd.DataFrame(raw_data)

            # 数据清洗
            if self.data_cleaner:
                df = self.data_cleaner.clean_match_data(df)

            # 标准化字段
            df = self._standardize_match_fields(df)

            # 验证数据质量
            validation_errors = self._validate_match_data(df)
            if validation_errors:
                self.logger.warning(f"数据验证失败: {validation_errors}")

            self.logger.info(f"处理了 {len(df)} 条比赛数据")
            return df

        except Exception as e:
            self.logger.error(f"处理比赛数据失败: {e}")
            return None

    def _standardize_match_fields(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        标准化比赛字段 / Standardize Match Fields

        Args:
            df: 原始数据框 / Raw DataFrame

        Returns:
            标准化后的数据框 / Standardized DataFrame
        """
        # 字段映射
        field_mapping = {
            "match_id": "id",
            "fixture_id": "id",
            "home_team": "home_team_name",
            "away_team": "away_team_name",
            "home_team_id": "home_team",
            "away_team_id": "away_team",
            "match_date": "match_time",
            "kickoff": "match_time",
        }

        # 重命名列
        df = df.rename(columns=field_mapping)

        # 确保必要字段存在
        required_fields = ["id", "home_team", "away_team", "match_time"]
        for field in required_fields:
            if field not in df.columns:
                self.logger.warning(f"缺少必要字段: {field}")
                df[field] = None

        return df

    def _validate_match_data(self, df: pd.DataFrame) -> List[str]:
        """
        验证比赛数据 / Validate Match Data

        Args:
            df: 数据框 / DataFrame

        Returns:
            验证错误列表 / List of validation errors
        """
        errors = []

        # 检查必要字段
        required_fields = ["id", "home_team", "away_team"]
        for field in required_fields:
            if field not in df.columns:
                errors.append(f"缺少字段: {field}")

        # 检查空值
        if "id" in df.columns:
            null_count = df["id"].isnull().sum()
            if null_count > 0:
                errors.append(f"比赛ID有 {null_count} 个空值")

        # 检查重复
        if "id" in df.columns:
            duplicate_count = df["id"].duplicated().sum()
            if duplicate_count > 0:
                errors.append(f"有 {duplicate_count} 个重复的比赛ID")

        return errors


class OddsDataProcessor(BaseDataProcessor):
    """
    赔率数据处理器 / Odds Data Processor

    处理博彩赔率数据。
    Processes betting odds data.
    """

    def __init__(self):
        super().__init__("OddsDataProcessor")

    async def process_raw_odds_data(
        self, raw_data: Union[Dict[str, Any], List[Dict[str, Any]]]
    ) -> Optional[pd.DataFrame]:
        """
        处理原始赔率数据 / Process Raw Odds Data

        Args:
            raw_data: 原始赔率数据 / Raw odds data

        Returns:
            处理后的数据框 / Processed DataFrame
        """
        try:
            if not raw_data:
                self.logger.warning("输入赔率数据为空")
                return None

            # 转换为DataFrame
            if isinstance(raw_data, dict):
                raw_data = [raw_data]

            df = pd.DataFrame(raw_data)

            # 标准化字段
            df = self._standardize_odds_fields(df)

            # 验证赔率数据
            validation_errors = self._validate_odds_data(df)
            if validation_errors:
                self.logger.warning(f"赔率数据验证失败: {validation_errors}")

            self.logger.info(f"处理了 {len(df)} 条赔率数据")
            return df

        except Exception as e:
            self.logger.error(f"处理赔率数据失败: {e}")
            return None

    def _standardize_odds_fields(self, df: pd.DataFrame) -> pd.DataFrame:
        """标准化赔率字段 / Standardize Odds Fields"""
        # 字段映射
        field_mapping = {
            "fixture_id": "match_id",
            "home_win": "home_odds",
            "draw": "draw_odds",
            "away_win": "away_odds",
            "over_2_5": "over_odds",
            "under_2_5": "under_odds",
        }

        df = df.rename(columns=field_mapping)

        # 确保必要字段
        required_fields = ["match_id", "home_odds", "draw_odds", "away_odds"]
        for field in required_fields:
            if field not in df.columns:
                self.logger.warning(f"赔率数据缺少字段: {field}")
                df[field] = None

        return df

    def _validate_odds_data(self, df: pd.DataFrame) -> List[str]:
        """验证赔率数据 / Validate Odds Data"""
        errors = []

        # 检查赔率值是否合理
        odds_fields = ["home_odds", "draw_odds", "away_odds"]
        for field in odds_fields:
            if field in df.columns:
                # 检查负值
                negative_count = (df[field] < 0).sum()
                if negative_count > 0:
                    errors.append(f"{field} 有 {negative_count} 个负值")

                # 检查过小的值
                small_count = (df[field] < 1.01).sum()
                if small_count > 0:
                    errors.append(f"{field} 有 {small_count} 个过小值 (<1.01)")

        return errors


class ScoresDataProcessor(BaseDataProcessor):
    """
    比分数据处理器 / Scores Data Processor

    处理比赛比分数据。
    Processes match scores data.
    """

    def __init__(self):
        super().__init__("ScoresDataProcessor")

    async def process_raw_scores_data(
        self, raw_data: Union[Dict[str, Any], List[Dict[str, Any]]]
    ) -> Optional[pd.DataFrame]:
        """
        处理原始比分数据 / Process Raw Scores Data

        Args:
            raw_data: 原始比分数据 / Raw scores data

        Returns:
            处理后的数据框 / Processed DataFrame
        """
        try:
            if not raw_data:
                self.logger.warning("输入比分数据为空")
                return None

            # 转换为DataFrame
            if isinstance(raw_data, dict):
                raw_data = [raw_data]

            df = pd.DataFrame(raw_data)

            # 标准化字段
            df = self._standardize_scores_fields(df)

            # 验证比分数据
            validation_errors = self._validate_scores_data(df)
            if validation_errors:
                self.logger.warning(f"比分数据验证失败: {validation_errors}")

            self.logger.info(f"处理了 {len(df)} 条比分数据")
            return df

        except Exception as e:
            self.logger.error(f"处理比分数据失败: {e}")
            return None

    def _standardize_scores_fields(self, df: pd.DataFrame) -> pd.DataFrame:
        """标准化比分字段 / Standardize Scores Fields"""
        # 字段映射
        field_mapping = {
            "fixture_id": "match_id",
            "home_score": "home_score",
            "away_score": "away_score",
            "home_ht_score": "home_half_time_score",
            "away_ht_score": "away_half_time_score",
            "minute": "match_minute",
        }

        df = df.rename(columns=field_mapping)

        # 确保必要字段
        required_fields = ["match_id", "home_score", "away_score"]
        for field in required_fields:
            if field not in df.columns:
                self.logger.warning(f"比分数据缺少字段: {field}")
                df[field] = None

        return df

    def _validate_scores_data(self, df: pd.DataFrame) -> List[str]:
        """验证比分数据 / Validate Scores Data"""
        errors = []

        # 检查比分是否为负数
        if "home_score" in df.columns:
            negative_home = (df["home_score"] < 0).sum()
            if negative_home > 0:
                errors.append(f"主队比分有 {negative_home} 个负值")

        if "away_score" in df.columns:
            negative_away = (df["away_score"] < 0).sum()
            if negative_away > 0:
                errors.append(f"客队比分有 {negative_away} 个负值")

        # 检查分钟是否合理
        if "match_minute" in df.columns:
            over_120 = (df["match_minute"] > 120).sum()
            if over_120 > 0:
                errors.append(f"有 {over_120} 个超过120分钟的比分记录")

        return errors


class FeaturesDataProcessor(BaseDataProcessor):
    """
    特征数据处理器 / Features Data Processor

    处理机器学习特征数据。
    Processes machine learning features data.
    """

    def __init__(self):
        super().__init__("FeaturesDataProcessor")

    async def process_features_data(
        self, raw_data: Union[Dict[str, Any], List[Dict[str, Any]]]
    ) -> Optional[pd.DataFrame]:
        """
        处理特征数据 / Process Features Data

        Args:
            raw_data: 原始特征数据 / Raw features data

        Returns:
            处理后的数据框 / Processed DataFrame
        """
        try:
            if not raw_data:
                self.logger.warning("输入特征数据为空")
                return None

            # 转换为DataFrame
            if isinstance(raw_data, dict):
                raw_data = [raw_data]

            df = pd.DataFrame(raw_data)

            # 特征处理
            df = self._process_features(df)

            self.logger.info(f"处理了 {len(df)} 条特征数据")
            return df

        except Exception as e:
            self.logger.error(f"处理特征数据失败: {e}")
            return None

    def _process_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        处理特征 / Process Features

        Args:
            df: 原始特征数据框 / Raw features DataFrame

        Returns:
            处理后的特征数据框 / Processed features DataFrame
        """
        # 处理缺失值
        df = self._handle_missing_features(df)

        # 标准化数值特征
        df = self._normalize_numeric_features(df)

        # 创建衍生特征
        df = self._create_derived_features(df)

        return df

    def _handle_missing_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """处理缺失特征 / Handle Missing Features"""
        # 数值特征用中位数填充
        numeric_columns = df.select_dtypes(include=['number']).columns
        for col in numeric_columns:
            if df[col].isnull().sum() > 0:
                median_value = df[col].median()
                df[col] = df[col].fillna(median_value)
                self.logger.info(f"特征 {col} 用中位数 {median_value:.2f} 填充缺失值")

        # 分类特征用众数填充
        categorical_columns = df.select_dtypes(include=['object']).columns
        for col in categorical_columns:
            if df[col].isnull().sum() > 0:
                mode_value = df[col].mode().iloc[0]
                df[col] = df[col].fillna(mode_value)
                self.logger.info(f"特征 {col} 用众数 {mode_value} 填充缺失值")

        return df

    def _normalize_numeric_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """标准化数值特征 / Normalize Numeric Features"""
        numeric_columns = df.select_dtypes(include=['number']).columns

        for col in numeric_columns:
            if col != "match_id":  # 不标准化ID字段
                # 最小-最大标准化
                min_val = df[col].min()
                max_val = df[col].max()
                if max_val > min_val:
                    df[col] = (df[col] - min_val) / (max_val - min_val)

        return df

    def _create_derived_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """创建衍生特征 / Create Derived Features"""
        # 示例：创建主客队实力差
        if "home_team_strength" in df.columns and "away_team_strength" in df.columns:
            df["strength_difference"] = df["home_team_strength"] - df["away_team_strength"]

        # 示例：创建历史交锋胜率
        if "head_to_head_home_wins" in df.columns and "head_to_head_total" in df.columns:



            df["h2h_home_win_rate"] = df["head_to_head_home_wins"] / df["head_to_head_total"]

        return df