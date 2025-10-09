"""
异常检测器主类
Anomaly Detector Main Class

提供异常检测的主要接口和协调功能。
"""



logger = logging.getLogger(__name__)


class AnomalyDetector:
    """
    统计学异常检测器主类

    提供多种异常检测方法：
    - 3σ规则检测
    - IQR方法检测
    - Z-score分析
    - 时间序列异常检测
    - 频率分布异常检测
    """

    def __init__(self):
        """初始化异常检测器"""
        self.db_manager = DatabaseManager()
        self.table_analyzer = TableAnalyzer()
        self.summarizer = AnomalySummarizer()

        # 检测配置
        self.detection_config = {
            "matches": {
                "numeric_columns": ["home_score", "away_score", "minute"],
                "time_columns": ["match_time"],
                "categorical_columns": ["match_status"],
                "thresholds": {
                    "home_score": {"min": 0, "max": 20},
                    "away_score": {"min": 0, "max": 20},
                    "minute": {"min": 0, "max": 120},
                },
            },
            "odds": {
                "numeric_columns": ["home_odds", "draw_odds", "away_odds"],
                "time_columns": ["collected_at"],
                "categorical_columns": ["bookmaker", "market_type"],
                "thresholds": {
                    "home_odds": {"min": 1.01, "max": 100.0},
                    "draw_odds": {"min": 1.01, "max": 100.0},
                    "away_odds": {"min": 1.01, "max": 100.0},
                },
            },
            "predictions": {
                "numeric_columns": [
                    "home_win_probability",
                    "draw_probability",
                    "away_win_probability",
                ],
                "time_columns": ["created_at"],
                "categorical_columns": ["model_name"],
                "thresholds": {
                    "home_win_probability": {"min": 0.0, "max": 1.0},
                    "draw_probability": {"min": 0.0, "max": 1.0},
                    "away_win_probability": {"min": 0.0, "max": 1.0},
                },
            },
        }

        logger.info("异常检测器初始化完成")

    async def detect_anomalies(
        self,
        table_names: Optional[List[str]] = None,
        methods: Optional[List[str]] = None,
    ) -> List[AnomalyResult]:
        """
        执行异常检测

        Args:
            table_names: 要检测的表名列表
            methods: 要使用的检测方法列表

        Returns:
            List[AnomalyResult]: 异常检测结果列表
        """
        if table_names is None:
            table_names = list(self.detection_config.keys())

        if methods is None:
            methods = ["three_sigma", "iqr", "z_score", "range_check"]

        all_anomalies = []

        async with self.db_manager.get_async_session() as session:
            for table_name in table_names:
                try:
                    table_anomalies = await self._detect_table_anomalies(
                        session, table_name, methods
                    )
                    all_anomalies.extend(table_anomalies)
                    logger.debug(
                        f"表 {table_name} 异常检测完成，发现 {len(table_anomalies)} 个异常"
                    )
                except Exception as e:
                    logger.error(f"检测表 {table_name} 异常失败: {e}")

        logger.info(f"异常检测完成，总共发现 {len(all_anomalies)} 个异常")
        return all_anomalies

    async def _detect_table_anomalies(
        self, session, table_name: str, methods: List[str]
    ) -> List[AnomalyResult]:
        """
        检测单个表的异常

        Args:
            session: 数据库会话
            table_name: 表名
            methods: 检测方法列表

        Returns:
            List[AnomalyResult]: 异常检测结果
        """
        config = self.detection_config.get(str(table_name), {})

        if not config:
            logger.warning(f"表 {table_name} 没有检测配置")
            return []

        # 使用表分析器进行检测
        return await self.table_analyzer.analyze_table(
            session=session,
            table_name=table_name,
            config=config,
            methods=methods,
        )

    async def get_anomaly_summary(
        self, anomalies: List[AnomalyResult]
    ) -> Dict[str, Any]:
        """
        获取异常摘要

        Args:
            anomalies: 异常结果列表

        Returns:
            Dict[str, Any]: 异常摘要
        """
        return await self.summarizer.generate_summary(anomalies)

from .analyzers import TableAnalyzer
from .summary import AnomalySummarizer
from src.database.connection import DatabaseManager

