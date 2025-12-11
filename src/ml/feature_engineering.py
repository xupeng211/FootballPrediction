"""
特征工程模块
Feature Engineering Module

提供足球博彩预测系统的核心特征转换功能，包括：
- 隐含概率计算
- 赔率熵计算
- 历史进球统计特征
- 数据验证和预处理

作者: Football Prediction Team
创建时间: 2024-12-11
版本: 1.0.0
"""

import pandas as pd
import numpy as np
from typing import List, Union
import logging


# 配置日志
logger = logging.getLogger(__name__)


class FeatureTransformer:
    """
    特征转换器类

    用于将原始比赛数据和赔率数据转换为机器学习模型可用的特征。
    实现足球博彩预测的核心特征工程逻辑。

    主要功能：
    1. 隐含概率计算 (Implied Probability)
    2. 赔率熵计算 (Odds Entropy)
    3. 历史进球差统计 (Goals Difference)
    4. 数据验证和清洗

    Attributes:
        required_columns (List[str]): 必需的输入列名
    """

    def __init__(self):
        """
        初始化 FeatureTransformer

        定义所需的输入数据列名，用于数据验证。
        """
        self.required_columns = [
            "match_id",
            "home_odds",
            "away_odds",
            "draw_odds",
            "home_goals_last_5",
            "away_goals_last_5",
        ]
        logger.info("FeatureTransformer 初始化完成")

    def _validate_input(self, data: pd.DataFrame) -> None:
        """
        验证输入数据的有效性

        Args:
            data (pd.DataFrame): 输入的数据框

        Raises:
            ValueError: 当数据验证失败时抛出异常
        """
        # 检查数据框是否为空
        if data.empty:
            raise ValueError("输入数据框不能为空")

        # 检查必需的列是否存在
        missing_columns = set(self.required_columns) - set(data.columns)
        if missing_columns:
            raise ValueError(f"缺少必需的列: {', '.join(missing_columns)}")

        # 检查赔率列是否包含负数或零
        odds_columns = ["home_odds", "away_odds", "draw_odds"]
        for col in odds_columns:
            if (data[col] <= 0).any():
                raise ValueError(f"赔率不能为负数或零，发现问题在列: {col}")

        # 检查是否包含缺失值
        if data[self.required_columns].isnull().any().any():
            missing_info = data[self.required_columns].isnull().sum()
            missing_cols = missing_info[missing_info > 0].index.tolist()
            raise ValueError(f"输入数据包含缺失值，问题列: {', '.join(missing_cols)}")

        logger.debug(f"输入数据验证通过，数据形状: {data.shape}")

    def _calculate_implied_probability(
        self, odds: Union[float, pd.Series]
    ) -> Union[float, pd.Series]:
        """
        计算隐含概率

        隐含概率 = 1 / 赔率

        Args:
            odds (Union[float, pd.Series]): 赔率值或赔率序列

        Returns:
            Union[float, pd.Series]: 隐含概率值或概率序列

        Raises:
            ValueError: 当赔率无效时抛出异常
        """
        if isinstance(odds, (pd.Series, np.ndarray)):
            if np.any(odds <= 0):
                raise ValueError("所有赔率必须大于0")
            return 1.0 / odds
        else:
            if odds <= 0:
                raise ValueError("赔率必须大于0")
            return 1.0 / odds

    def _calculate_odds_entropy(self, probabilities: List[float]) -> float:
        """
        计算赔率的信息熵

        熵 = -Σ(p_i * log2(p_i))

        Args:
            probabilities (List[float]): 概率列表 [home_prob, draw_prob, away_prob]

        Returns:
            float: 信息熵值

        Raises:
            ValueError: 当概率无效时抛出异常
        """
        # 验证概率的有效性
        if len(probabilities) != 3:
            raise ValueError("概率列表必须包含3个值 (home, draw, away)")

        if not all(0 <= p <= 1 for p in probabilities):
            raise ValueError("概率必须在0和1之间")

        prob_sum = sum(probabilities)
        if not np.isclose(prob_sum, 1.0, atol=1e-10):
            # 如果概率和不为1，进行归一化
            probabilities = [p / prob_sum for p in probabilities]
            logger.warning(f"概率和不为1 ({prob_sum})，已进行归一化")

        # 计算信息熵
        entropy = -sum(p * np.log2(p) for p in probabilities if p > 0)

        return entropy

    def _calculate_avg_goals_diff_l5(
        self, home_goals: Union[int, pd.Series], away_goals: Union[int, pd.Series]
    ) -> Union[int, pd.Series]:
        """
        计算最近5场比赛的平均进球差

        Args:
            home_goals (Union[int, pd.Series]): 主队最近5场进球数
            away_goals (Union[int, pd.Series]): 客队最近5场进球数

        Returns:
            Union[int, pd.Series]: 进球差 (正值表示主队优势)
        """
        return home_goals - away_goals

    def transform(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        执行特征转换

        将输入的比赛数据转换为包含工程化特征的数据框。

        Args:
            data (pd.DataFrame): 输入的比赛数据，必须包含必需的列

        Returns:
            pd.DataFrame: 包含原始数据和新特征的数据框

        Raises:
            ValueError: 当输入数据无效时抛出异常

        Example:
            >>> transformer = FeatureTransformer()
            >>> data = pd.DataFrame({
            ...     'match_id': [1, 2],
            ...     'home_odds': [2.5, 1.8],
            ...     'away_odds': [2.8, 4.5],
            ...     'draw_odds': [3.2, 3.6],
            ...     'home_goals_last_5': [8, 12],
            ...     'away_goals_last_5': [7, 5]
            ... })
            >>> result = transformer.transform(data)
            >>> print(result.columns)
            Index(['match_id', 'home_odds', 'away_odds', 'draw_odds',
                   'home_goals_last_5', 'away_goals_last_5',
                   'Implied_Prob_Home', 'Implied_Prob_Away', 'Odds_Entropy',
                   'Avg_Goals_Diff_L5'],
                  dtype='object')
        """
        logger.info("开始特征转换")
        logger.debug(f"输入数据形状: {data.shape}")

        # 验证输入数据
        self._validate_input(data)

        # 创建结果数据框的副本
        result = data.copy()

        try:
            # 1. 计算隐含概率
            logger.debug("计算隐含概率")
            result["Implied_Prob_Home"] = self._calculate_implied_probability(
                result["home_odds"]
            )
            result["Implied_Prob_Away"] = self._calculate_implied_probability(
                result["away_odds"]
            )

            # 2. 计算赔率熵
            logger.debug("计算赔率熵")
            # 计算每一行的赔率熵
            entropies = []
            for _, row in result.iterrows():
                home_prob = 1 / row["home_odds"]
                draw_prob = 1 / row["draw_odds"]
                away_prob = 1 / row["away_odds"]

                # 归一化概率
                total_prob = home_prob + draw_prob + away_prob
                probabilities = [
                    home_prob / total_prob,
                    draw_prob / total_prob,
                    away_prob / total_prob,
                ]

                entropy = self._calculate_odds_entropy(probabilities)
                entropies.append(entropy)

            result["Odds_Entropy"] = entropies

            # 3. 计算平均进球差
            logger.debug("计算平均进球差")
            result["Avg_Goals_Diff_L5"] = self._calculate_avg_goals_diff_l5(
                result["home_goals_last_5"], result["away_goals_last_5"]
            )

            logger.info(f"特征转换完成，输出数据形状: {result.shape}")
            logger.debug(
                f"新增特征列: {['Implied_Prob_Home', 'Implied_Prob_Away', 'Odds_Entropy', 'Avg_Goals_Diff_L5']}"
            )

            return result

        except Exception as e:
            logger.error(f"特征转换过程中发生错误: {str(e)}")
            raise

    def get_feature_names(self) -> List[str]:
        """
        获取所有特征名称

        Returns:
            List[str]: 特征名称列表
        """
        return [
            "Implied_Prob_Home",
            "Implied_Prob_Away",
            "Odds_Entropy",
            "Avg_Goals_Diff_L5",
        ]

    def get_feature_descriptions(self) -> dict:
        """
        获取特征描述信息

        Returns:
            dict: 特征名称到描述的映射
        """
        return {
            "Implied_Prob_Home": "主队隐含获胜概率，计算公式: 1 / home_odds",
            "Implied_Prob_Away": "客队隐含获胜概率，计算公式: 1 / away_odds",
            "Odds_Entropy": "赔率信息熵，反映比赛结果的不确定性。熵值越高，比赛结果越难预测",
            "Avg_Goals_Diff_L5": "最近5场比赛主客队平均进球差。正值表示主队攻击力优势，负值表示客队优势",
        }

    def validate_output(self, data: pd.DataFrame) -> bool:
        """
        验证输出数据的有效性

        Args:
            data (pd.DataFrame): 输出数据框

        Returns:
            bool: 验证是否通过
        """
        try:
            feature_names = self.get_feature_names()

            # 检查特征列是否存在
            missing_features = set(feature_names) - set(data.columns)
            if missing_features:
                logger.error(f"输出数据缺少特征列: {missing_features}")
                return False

            # 检查隐含概率范围
            if not data["Implied_Prob_Home"].between(0, 1).all():
                logger.error("主队隐含概率超出有效范围 (0, 1]")
                return False

            if not data["Implied_Prob_Away"].between(0, 1).all():
                logger.error("客队隐含概率超出有效范围 (0, 1]")
                return False

            # 检查熵值是否为正数
            if not (data["Odds_Entropy"] > 0).all():
                logger.error("赔率熵应该为正数")
                return False

            logger.info("输出数据验证通过")
            return True

        except Exception as e:
            logger.error(f"输出数据验证失败: {str(e)}")
            return False


def create_sample_data(n_samples: int = 10) -> pd.DataFrame:
    """
    创建示例数据用于测试

    Args:
        n_samples (int): 样本数量，默认为10

    Returns:
        pd.DataFrame: 示例数据框
    """
    np.random.seed(42)  # 确保可重复性

    data = pd.DataFrame(
        {
            "match_id": range(1, n_samples + 1),
            "home_odds": np.random.uniform(1.2, 5.0, n_samples),
            "away_odds": np.random.uniform(1.2, 8.0, n_samples),
            "draw_odds": np.random.uniform(2.5, 4.5, n_samples),
            "home_goals_last_5": np.random.randint(0, 20, n_samples),
            "away_goals_last_5": np.random.randint(0, 20, n_samples),
        }
    )

    return data


if __name__ == "__main__":
    # 示例使用
    print("特征工程模块示例")

    # 创建示例数据
    sample_data = create_sample_data(5)
    print("示例数据:")
    print(sample_data)

    # 创建转换器并转换数据
    transformer = FeatureTransformer()
    transformed_data = transformer.transform(sample_data)

    print("\n转换后的数据:")
    print(
        transformed_data[
            [
                "match_id",
                "Implied_Prob_Home",
                "Implied_Prob_Away",
                "Odds_Entropy",
                "Avg_Goals_Diff_L5",
            ]
        ]
    )

    # 显示特征描述
    print("\n特征描述:")
    for name, desc in transformer.get_feature_descriptions().items():
        print(f"{name}: {desc}")
