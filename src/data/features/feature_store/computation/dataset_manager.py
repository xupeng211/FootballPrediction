"""
特征仓库数据集管理模块
Feature Store Dataset Management Module
"""

from datetime import datetime, timedelta
from typing import List, Optional
import pandas as pd

from src.core.logging_system import get_logger

logger = get_logger(__name__)


class FeatureDatasetManager:
    """特征数据集管理器"""

    def __init__(self, query_manager):
        """
        初始化数据集管理器

        Args:
            query_manager: 查询管理器实例
        """
        self.query_manager = query_manager
        self.logger = logger

    def create_training_dataset(
        self,
        start_date: datetime,
        end_date: datetime,
        match_ids: Optional[List[int]] = None,
    ) -> pd.DataFrame:
        """
        创建训练数据集

        Args:
            start_date: 开始日期
            end_date: 结束日期
            match_ids: 指定的比赛ID列表，如果为None则获取时间范围内所有比赛

        Returns:
            pd.DataFrame: 训练数据集
        """
        try:
            # 构建实体DataFrame
            entity_data = []
            if match_ids:
                for match_id in match_ids:
                    entity_data.append(
                        {
                            "match_id": match_id,
                            "event_timestamp": end_date,  # 使用结束时间作为特征时间点
                        }
                    )
            else:
                # 如果没有指定比赛ID，从数据库获取时间范围内的比赛
                # TODO: 实现从数据库查询比赛的逻辑
                # 这里提供一个示例
                for i in range(1, 100):  # 示例：100场比赛
                    entity_data.append(
                        {
                            "match_id": i,
                            "event_timestamp": start_date + timedelta(days=i % 30),
                        }
                    )

            entity_df = pd.DataFrame(entity_data)

            # 获取训练特征
            training_df = self.query_manager.get_historical_features(
                feature_service_name="match_prediction_v1",
                entity_df=entity_df,
                full_feature_names=True,
            )

            self.logger.info(f"创建训练数据集成功，包含 {len(training_df)} 条记录")
            return training_df if isinstance(training_df, dict) else {}
        except Exception as e:
            self.logger.error(f"创建训练数据集失败: {str(e)}")
            raise

    def create_prediction_dataset(
        self,
        match_ids: List[int],
        prediction_time: Optional[datetime] = None,
    ) -> pd.DataFrame:
        """
        创建预测数据集

        Args:
            match_ids: 需要预测的比赛ID列表
            prediction_time: 预测时间，默认为当前时间

        Returns:
            pd.DataFrame: 预测数据集
        """
        try:
            if prediction_time is None:
                prediction_time = datetime.now()

            # 构建实体DataFrame
            entity_data = []
            for match_id in match_ids:
                entity_data.append(
                    {
                        "match_id": match_id,
                        "event_timestamp": prediction_time,
                    }
                )

            entity_df = pd.DataFrame(entity_data)

            # 获取在线特征
            prediction_df = self.query_manager.get_online_features(
                feature_service_name="match_prediction_v1",
                entity_df=entity_df,
            )

            self.logger.info(f"创建预测数据集成功，包含 {len(prediction_df)} 条记录")
            return prediction_df
        except Exception as e:
            self.logger.error(f"创建预测数据集失败: {str(e)}")
            raise

    def create_validation_dataset(
        self,
        start_date: datetime,
        end_date: datetime,
        validation_split: float = 0.2,
    ) -> pd.DataFrame:
        """
        创建验证数据集

        Args:
            start_date: 开始日期
            end_date: 结束日期
            validation_split: 验证集比例

        Returns:
            pd.DataFrame: 验证数据集
        """
        try:
            # 首先创建完整的数据集
            full_dataset = self.create_training_dataset(
                start_date=start_date,
                end_date=end_date,
            )

            # 按时间分割验证集
            if len(full_dataset) > 0:
                split_index = int(len(full_dataset) * (1 - validation_split))
                validation_df = full_dataset.iloc[split_index:]
            else:
                validation_df = pd.DataFrame()

            self.logger.info(f"创建验证数据集成功，包含 {len(validation_df)} 条记录")
            return validation_df
        except Exception as e:
            self.logger.error(f"创建验证数据集失败: {str(e)}")
            raise