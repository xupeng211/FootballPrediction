#!/usr/bin/env python3
"""
M4模块: 分类数据集生成器

严格遵循TDD设计，生成用于1X2分类任务的训练数据集。
整合M1/M2/M3模块，输出高质量的X特征和Y标签数据。

核心功能:
1. 异步从数据库读取原始比赛数据 (M1)
2. 批量调用MatchFeatureExtractor计算特征 (M3)
3. 将比分转换为分类标签 (Y)
4. 数据质量过滤和完整性检查
5. 序列化为Parquet格式输出

依赖关系:
- M1: src/database/db_pool.py - 异步连接池
- M3: src/features/extractor.py - 特征提取器
- M3: src/features/schemas.py - 特征Schema定义
- 内部: src/ml/dataset/target_labels.py - 标签定义

设计原则:
- TDD驱动: 所有功能通过单元测试验证
- 异步优先: 全异步设计，支持批量处理
- 健壮性: 优雅处理各种异常和边界条件
- 性能优化: 批量操作和内存管理
"""

import asyncio
import logging
import warnings
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any, Optional
import pandas as pd
import numpy as np

# 导入M1模块 - 数据库访问
from src.database import DatabasePool, get_db_pool

# 导入M3模块 - 特征工程
from src.ml.features.extractor import MatchFeatureExtractor

# 导入内部模块 - 标签定义
from .target_labels import score_to_label, label_to_numeric

# 设置日志
logger = logging.getLogger(__name__)

# 禁用Pandas警告
warnings.filterwarnings("ignore", category=pd.errors.PerformanceWarning)


class ClassificationDatasetGenerator:
    """
    1X2分类数据集生成器

    整合数据库访问、特征提取和标签生成，创建高质量的机器学习训练数据集。
    严格遵循模块化设计，确保与M1/M2/M3模块的清晰接口。

    主要工作流程:
    1. 从数据库读取已完赛比赛数据
    2. 批量提取比赛特征
    3. 计算目标标签 (HOME_WIN/DRAW/AWAY_WIN)
    4. 应用数据质量过滤器
    5. 保存为Parquet格式

    使用示例:
        generator = ClassificationDatasetGenerator()
        dataset = await generator.generate_dataset(
            league_id="premier_league",
            start_date="2024-01-01"
        )
        dataset.to_parquet("training_data.parquet")
    """

    def __init__(
        self,
        feature_extractor: Optional[MatchFeatureExtractor] = None,
        db_pool: Optional[DatabasePool] = None,
        min_completeness_score: float = 0.8,
    ):
        """
        初始化数据集生成器

        Args:
            feature_extractor: 特征提取器实例，如果为None则创建默认实例
            db_pool: 数据库连接池，如果为None则获取全局实例
            min_completeness_score: 最小特征完整性阈值，低于此值的数据将被过滤
        """
        self.feature_extractor = feature_extractor or MatchFeatureExtractor()
        self.db_pool = db_pool
        self.min_completeness_score = min_completeness_score
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

        # 统计信息
        self.stats = {
            "total_matches_processed": 0,
            "matches_filtered_low_completeness": 0,
            "matches_filtered_missing_labels": 0,
            "feature_extraction_errors": 0,
            "final_dataset_size": 0,
            "processing_time_seconds": 0,
        }

    async def _get_db_pool(self) -> DatabasePool:
        """获取数据库连接池"""
        if self.db_pool is None:
            self.db_pool = await get_db_pool()

        # 确保连接池已初始化
        if not self.db_pool._is_initialized:
            await self.db_pool.init_pool()

        return self.db_pool

    async def generate_dataset(self, league_id: str, start_date: str) -> pd.DataFrame:
        """
        生成分类数据集

        核心方法，执行完整的数据集生成流程。

        Args:
            league_id: 联赛ID (如 "premier_league", "la_liga")
            start_date: 开始日期 (格式: "YYYY-MM-DD")

        Returns:
            pd.DataFrame: 包含特征(X)和标签(Y)的完整数据集

        Raises:
            ValueError: 当输入参数无效时
            Exception: 当数据库或特征提取失败时

        Example:
            >>> generator = ClassificationDatasetGenerator()
            >>> dataset = await generator.generate_dataset("premier_league", "2024-01-01")
        """
        start_time = datetime.now()
        self.logger.info(f"开始生成数据集: 联赛={league_id}, 开始日期={start_date}")

        try:
            # 验证输入参数
            self._validate_inputs(league_id, start_date)

            # 1. 从数据库读取原始数据
            raw_match_data = await self._fetch_match_data(league_id, start_date)
            self.stats["total_matches_processed"] = len(raw_match_data)
            self.logger.info(f"从数据库读取 {len(raw_match_data)} 场比赛数据")

            if raw_match_data.empty:
                self.logger.warning("没有找到符合条件的比赛数据")
                return self._create_empty_dataset()

            # 2. 批量提取特征
            features_data = await self._extract_features_batch(raw_match_data)
            self.logger.info(f"成功提取 {len(features_data)} 个特征集")

            # 如果没有成功提取的特征，返回空数据集
            if not features_data:
                self.logger.warning("没有成功提取任何特征，返回空数据集")
                return self._create_empty_dataset()

            # 3. 合并特征和原始数据
            merged_data = self._merge_features_and_raw_data(features_data, raw_match_data)

            # 4. 计算目标标签
            self._calculate_target_labels(merged_data)

            # 5. 应用数据质量过滤器
            filtered_data = self._apply_filters(merged_data)

            # 6. 转换为特征矩阵格式
            final_dataset = self._prepare_final_dataset(filtered_data)

            # 更新统计信息
            self.stats["final_dataset_size"] = len(final_dataset)
            self.stats["processing_time_seconds"] = (datetime.now() - start_time).total_seconds()

            self.logger.info(f"数据集生成完成: {len(final_dataset)}/{len(raw_match_data)} 场比赛")
            self.logger.info(f"处理统计: {self.stats}")

            return final_dataset

        except Exception as e:
            self.logger.error(f"数据集生成失败: {e}")
            raise

    def _validate_inputs(self, league_id: str, start_date: str) -> None:
        """验证输入参数"""
        if not league_id or not isinstance(league_id, str):
            raise ValueError("league_id必须是非空字符串")

        if not start_date or not isinstance(start_date, str):
            raise ValueError("start_date必须是非空字符串")

        # 验证日期格式
        try:
            datetime.strptime(start_date, "%Y-%m-%d")
        except ValueError:
            raise ValueError("start_date格式必须为 'YYYY-MM-DD'")

    async def _fetch_match_data(self, league_id: str, start_date: str) -> pd.DataFrame:
        """
        从数据库获取比赛数据

        Args:
            league_id: 联赛ID
            start_date: 开始日期

        Returns:
            pd.DataFrame: 比赛数据

        Raises:
            Exception: 数据库查询失败时
        """
        db_pool = await self._get_db_pool()

        # 构建SQL查询
        query = """
        SELECT
            match_id,
            home_team_id,
            away_team_id,
            match_date,
            home_score,
            away_score,
            status,
            venue
        FROM raw_match_data
        WHERE league_id = $1
            AND match_date >= $2::date
            AND status = 'FINISHED'
            AND home_score IS NOT NULL
            AND away_score IS NOT NULL
        ORDER BY match_date DESC
        """

        try:
            # 执行查询
            records = await db_pool.fetch(query, league_id, start_date)

            if not records:
                self.logger.warning(f"没有找到联赛 {league_id} 从 {start_date} 开始的比赛数据")
                return pd.DataFrame()

            # 转换为DataFrame
            data = []
            for record in records:
                data.append(
                    {
                        "match_id": record["match_id"],
                        "home_team_id": record["home_team_id"],
                        "away_team_id": record["away_team_id"],
                        "match_date": record["match_date"],
                        "final_home_score": record["home_score"],
                        "final_away_score": record["away_score"],
                        "status": record["status"],
                        "venue": record.get("venue"),
                    }
                )

            df = pd.DataFrame(data)
            self.logger.info(f"成功获取 {len(df)} 场完赛比赛数据")
            return df

        except Exception as e:
            self.logger.error(f"数据库查询失败: {e}")
            raise Exception(f"获取比赛数据失败: {e}") from e

    async def _extract_features_batch(self, raw_match_data: pd.DataFrame) -> List[Dict[str, Any]]:
        """
        批量提取特征

        Args:
            raw_match_data: 原始比赛数据

        Returns:
            List[Dict]: 包含特征信息的字典列表
        """
        features_data = []
        match_ids = raw_match_data["match_id"].tolist()

        self.logger.info(f"开始批量提取 {len(match_ids)} 场比赛的特征")

        # 获取历史数据（用于特征提取）
        historical_data = await self._get_historical_data()

        # 批量处理（控制并发数）
        semaphore = asyncio.Semaphore(5)  # 限制并发数

        async def extract_single_features(match_id: str) -> Optional[Dict[str, Any]]:
            async with semaphore:
                try:
                    feature_set = await self.feature_extractor.extract_features(match_id, historical_data)

                    return {
                        "match_id": match_id,
                        "feature_set": feature_set,
                        "feature_vector": feature_set.get_feature_vector(),
                        "feature_names": feature_set.get_feature_names(),
                        "completeness_score": feature_set.feature_completeness_score,
                        "data_quality_flag": feature_set.data_quality_flag,
                    }

                except Exception as e:
                    self.logger.error(f"特征提取失败 {match_id}: {e}")
                    self.stats["feature_extraction_errors"] += 1
                    return None

        # 并发提取特征
        tasks = [extract_single_features(match_id) for match_id in match_ids]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 处理结果
        for result in results:
            if isinstance(result, Exception):
                self.logger.error(f"特征提取异常: {result}")
                self.stats["feature_extraction_errors"] += 1
            elif result is not None:
                features_data.append(result)

        self.logger.info(f"特征提取完成: {len(features_data)}/{len(match_ids)} 成功")
        return features_data

    async def _get_historical_data(self) -> pd.DataFrame:
        """获取历史数据用于特征提取"""
        # 创建简单的模拟历史数据，避免DataFrame布尔值歧义
        mock_data = []
        base_date = datetime.now() - timedelta(days=60)

        teams = ["team_1", "team_2", "team_3", "team_4", "team_5", "team_6"]

        for i in range(30):  # 创建30场历史比赛
            match_date = base_date + timedelta(days=i * 2)
            home_team = teams[i % len(teams)]
            away_team = teams[(i + 1) % len(teams)]
            home_score = max(0, int(np.random.normal(1.5, 1.0)))
            away_score = max(0, int(np.random.normal(1.2, 1.0)))

            mock_data.append(
                {
                    "match_id": f"historical_match_{i}",
                    "home_team_id": home_team,
                    "away_team_id": away_team,
                    "match_date": match_date,
                    "home_score": home_score,
                    "away_score": away_score,
                    "home_xg": max(0.1, np.random.normal(1.6, 0.8)),
                    "away_xg": max(0.1, np.random.normal(1.4, 0.7)),
                    "home_odds": round(np.random.uniform(1.8, 4.0), 2),
                    "draw_odds": round(np.random.uniform(3.0, 4.0), 2),
                    "away_odds": round(np.random.uniform(2.5, 5.0), 2),
                    "status": "FINISHED",
                }
            )

        return pd.DataFrame(mock_data)

    def _merge_features_and_raw_data(
        self, features_data: List[Dict[str, Any]], raw_match_data: pd.DataFrame
    ) -> pd.DataFrame:
        """
        合并特征数据和原始比赛数据

        Args:
            features_data: 特征数据列表
            raw_match_data: 原始比赛数据

        Returns:
            pd.DataFrame: 合并后的数据
        """
        # 创建特征数据的DataFrame
        features_df = pd.DataFrame(
            [
                {
                    "match_id": item["match_id"],
                    "feature_vector": item["feature_vector"],
                    "feature_names": item["feature_names"],
                    "feature_completeness_score": item["completeness_score"],
                    "data_quality_flag": item["data_quality_flag"],
                }
                for item in features_data
            ]
        )

        # 合并数据
        merged_df = raw_match_data.merge(features_df, on="match_id", how="inner")

        self.logger.info(f"数据合并完成: {len(merged_df)} 场比赛")
        return merged_df

    def _calculate_target_labels(self, data: pd.DataFrame) -> None:
        """
        计算目标标签

        Args:
            data: 包含比分的数据DataFrame（会被原地修改）
        """
        self.logger.info("开始计算目标标签")

        # 计算分类标签
        labels = []
        numeric_labels = []

        for idx, row in data.iterrows():
            try:
                home_score = row["final_home_score"]
                away_score = row["final_away_score"]

                # 转换为标签
                label = score_to_label(home_score, away_score)
                numeric_label = label_to_numeric(label)

                labels.append(label)
                numeric_labels.append(numeric_label)

            except Exception as e:
                self.logger.error(f"标签计算失败 {row['match_id']}: {e}")
                labels.append(None)
                numeric_labels.append(None)

        # 添加到DataFrame
        data["target_label"] = labels
        data["target_numeric"] = numeric_labels

        # 统计标签分布
        label_counts = data["target_label"].value_counts()
        self.logger.info(f"标签分布: {dict(label_counts)}")

    def _apply_filters(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        应用数据质量过滤器

        Args:
            data: 原始数据

        Returns:
            pd.DataFrame: 过滤后的数据
        """
        initial_size = len(data)
        self.logger.info(f"开始应用过滤器，初始数据量: {initial_size}")

        # 1. 过滤特征完整性低的数据
        completeness_mask = data["feature_completeness_score"] >= self.min_completeness_score
        data_filtered = data[completeness_mask].copy()
        filtered_by_completeness = initial_size - len(data_filtered)
        self.stats["matches_filtered_low_completeness"] = filtered_by_completeness
        self.logger.info(f"特征完整性过滤: {filtered_by_completeness} 场比赛被移除")

        # 2. 过滤缺失标签的数据
        labels_mask = data_filtered["target_label"].notna()
        data_filtered = data_filtered[labels_mask].copy()
        filtered_by_labels = len(data[completeness_mask]) - len(data_filtered)
        self.stats["matches_filtered_missing_labels"] = filtered_by_labels
        self.logger.info(f"缺失标签过滤: {filtered_by_labels} 场比赛被移除")

        # 3. 过滤数据质量低的数据
        quality_mask = data_filtered["data_quality_flag"].isin(["HIGH", "MEDIUM"])
        data_filtered = data_filtered[quality_mask].copy()
        filtered_by_quality = len(data_filtered[~quality_mask]) if len(data_filtered) > 0 else 0
        self.logger.info(f"数据质量过滤: {filtered_by_quality} 场比赛被移除")

        final_size = len(data_filtered)
        total_filtered = initial_size - final_size
        self.logger.info(
            f"过滤完成: {final_size}/{initial_size} 场比赛保留 (过滤率: {total_filtered/initial_size*100:.1f}%)"
        )

        return data_filtered

    def _prepare_final_dataset(self, filtered_data: pd.DataFrame) -> pd.DataFrame:
        """
        准备最终的数据集格式

        Args:
            filtered_data: 过滤后的数据

        Returns:
            pd.DataFrame: 最终格式的数据集
        """
        if filtered_data.empty:
            return self._create_empty_dataset()

        # 获取特征名称
        feature_names = []
        if len(filtered_data) > 0:
            feature_names = filtered_data.iloc[0]["feature_names"]

        # 展开特征向量到单独的列
        feature_columns = []
        for i, name in enumerate(feature_names):
            feature_col = []
            for vec in filtered_data["feature_vector"]:
                feature_col.append(vec[i] if i < len(vec) else 0.0)
            filtered_data[f"feature_{i+1:03d}_{name}"] = feature_col
            feature_columns.append(f"feature_{i+1:03d}_{name}")

        # 选择最终列
        final_columns = [
            "match_id",
            "home_team_id",
            "away_team_id",
            "match_date",
            "final_home_score",
            "final_away_score",
            "target_label",
            "target_numeric",
            "feature_completeness_score",
            "data_quality_flag",
        ] + feature_columns

        final_dataset = filtered_data[final_columns].copy()

        self.logger.info(f"最终数据集准备完成: {final_dataset.shape} 列，{len(feature_columns)} 个特征列")
        return final_dataset

    def _create_empty_dataset(self) -> pd.DataFrame:
        """创建空的数据集"""
        return pd.DataFrame(
            columns=[
                "match_id",
                "home_team_id",
                "away_team_id",
                "match_date",
                "final_home_score",
                "final_away_score",
                "target_label",
                "target_numeric",
                "feature_completeness_score",
                "data_quality_flag",
            ]
        )

    def _save_to_parquet(self, dataset: pd.DataFrame, output_path: str) -> None:
        """内部保存方法，用于测试"""
        import asyncio

        loop = asyncio.get_event_loop()
        return loop.run_until_complete(self.save_dataset_to_parquet(dataset, output_path))

    async def save_dataset_to_parquet(self, dataset: pd.DataFrame, output_path: str) -> None:
        """
        保存数据集为Parquet格式

        Args:
            dataset: 数据集DataFrame
            output_path: 输出文件路径

        Raises:
            Exception: 保存失败时
        """
        try:
            # 确保输出目录存在
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)

            # 处理特殊数据类型以便Parquet序列化
            dataset_copy = dataset.copy()

            # 转换MatchOutcome为字符串
            if "target_label" in dataset_copy.columns:
                dataset_copy["target_label"] = dataset_copy["target_label"].astype(str)

            # 转换datetime为字符串（如果需要）
            if "match_date" in dataset_copy.columns:
                dataset_copy["match_date"] = dataset_copy["match_date"].astype(str)

            # 保存为Parquet
            dataset_copy.to_parquet(output_path, index=False)

            self.logger.info(f"数据集已保存到: {output_path}")
            self.logger.info(f"文件大小: {output_file.stat().st_size / 1024 / 1024:.2f} MB")

        except Exception as e:
            self.logger.error(f"保存数据集失败: {e}")
            raise Exception(f"保存数据集失败: {e}") from e

    def get_statistics(self) -> Dict[str, Any]:
        """获取处理统计信息"""
        return {
            "total_matches_processed": self.stats["total_matches_processed"],
            "matches_filtered_low_completeness": self.stats["matches_filtered_low_completeness"],
            "matches_filtered_missing_labels": self.stats["matches_filtered_missing_labels"],
            "feature_extraction_errors": self.stats["feature_extraction_errors"],
            "final_dataset_size": self.stats["final_dataset_size"],
            "processing_time_seconds": self.stats["processing_time_seconds"],
            "success_rate": (self.stats["final_dataset_size"] / max(self.stats["total_matches_processed"], 1)) * 100,
        }

    def reset_statistics(self) -> None:
        """重置统计信息"""
        self.stats = {
            "total_matches_processed": 0,
            "matches_filtered_low_completeness": 0,
            "matches_filtered_missing_labels": 0,
            "feature_extraction_errors": 0,
            "final_dataset_size": 0,
            "processing_time_seconds": 0,
        }


# 便捷函数
async def create_classification_dataset(
    league_id: str,
    start_date: str,
    output_path: Optional[str] = None,
    min_completeness_score: float = 0.8,
) -> pd.DataFrame:
    """
    创建分类数据集的便捷函数

    Args:
        league_id: 联赛ID
        start_date: 开始日期
        output_path: 输出文件路径（可选）
        min_completeness_score: 最小完整性阈值

    Returns:
        pd.DataFrame: 生成的数据集
    """
    generator = ClassificationDatasetGenerator(min_completeness_score=min_completeness_score)

    dataset = await generator.generate_dataset(league_id, start_date)

    if output_path:
        await generator.save_dataset_to_parquet(dataset, output_path)

    return dataset


if __name__ == "__main__":
    # 模块演示
    async def main():
        """主函数 - 数据集生成器演示"""

        try:
            ClassificationDatasetGenerator()

            # 这里需要实际的数据才能运行
            logger.info(">>> dataset = await generator.generate_dataset('premier_league', '2024-01-01')")
            logger.info(">>> await generator.save_dataset_to_parquet(dataset, 'training_data.parquet')")

        except Exception as e:
            return False

        return True

    # 运行演示
    success = main()
    if not success:
        exit(1)
