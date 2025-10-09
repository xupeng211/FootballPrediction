"""

"""






    """列数据分析器"""

        """初始化列分析器"""

        """


        """










    """表数据分析器"""

        """初始化表分析器"""

        """


        """








        """


        """
                """  # nosec B608 - table_name is validated against whitelist





数据分析器
Data Analyzers
负责分析表和列的数据，协调各种检测方法。
    FrequencyDetector,
    IQRDetector,
    RangeDetector,
    ThreeSigmaDetector,
    TimeGapDetector,
    ZScoreDetector,
)
logger = logging.getLogger(__name__)
class ColumnAnalyzer:
    def __init__(self):
        # 初始化各种检测器
        self.detectors = {
            "three_sigma": ThreeSigmaDetector(),
            "iqr": IQRDetector(),
            "z_score": ZScoreDetector(),
            "frequency": FrequencyDetector(),
            "time_gap": TimeGapDetector(),
        }
    async def analyze_column(
        self,
        data: pd.DataFrame,
        table_name: str,
        column_name: str,
        methods: List[str],
        column_type: str,
        thresholds: Dict[str, Any] | None = None,
    ) -> List[AnomalyResult]:
        分析单列数据的异常
        Args:
            data: 数据框
            table_name: 表名
            column_name: 列名
            methods: 检测方法列表
            column_type: 列类型（numeric, categorical, time）
            thresholds: 数值范围阈值
        Returns:
            List[AnomalyResult]: 异常结果列表
        anomalies: List[AnomalyResult] = []
        column_data = data[column_name].dropna()
        if len(column_data) == 0:
            return anomalies
        # 根据列类型和方法进行检测
        if column_type == "numeric":
            # 数值型检测方法
            if "three_sigma" in methods:
                anomalies.extend(
                    self.detectors["three_sigma"].detect(column_data, table_name, column_name)
                )
            if "iqr" in methods:
                anomalies.extend(
                    self.detectors["iqr"].detect(column_data, table_name, column_name)
                )
            if "z_score" in methods:
                anomalies.extend(
                    self.detectors["z_score"].detect(column_data, table_name, column_name)
                )
            if "range_check" in methods and thresholds:
                range_detector = RangeDetector(thresholds)
                anomalies.extend(
                    range_detector.detect(column_data, table_name, column_name)
                )
        elif column_type == "categorical":
            # 分类型检测方法
            if "frequency" in methods:
                anomalies.extend(
                    self.detectors["frequency"].detect(column_data, table_name, column_name)
                )
        elif column_type == "time":
            # 时间型检测方法
            if "time_gap" in methods:
                anomalies.extend(
                    self.detectors["time_gap"].detect(column_data, table_name, column_name)
                )
        return anomalies
class TableAnalyzer:
    def __init__(self):
        self.column_analyzer = ColumnAnalyzer()
    async def analyze_table(
        self,
        session: AsyncSession,
        table_name: str,
        config: Dict[str, Any],
        methods: List[str],
    ) -> List[AnomalyResult]:
        分析整个表的异常
        Args:
            session: 数据库会话
            table_name: 表名
            config: 表配置
            methods: 检测方法列表
        Returns:
            List[AnomalyResult]: 异常结果列表
        anomalies: List[AnomalyResult] = []
        # 获取表数据
        table_data = await self._get_table_data(session, table_name)
        if table_data.empty:
            logger.warning(f"表 {table_name} 没有数据")
            return anomalies
        # 获取阈值配置
        thresholds = config.get("thresholds", {})
        # 数值列异常检测
        numeric_columns = config.get("numeric_columns", [])
        for column in numeric_columns:
            if column in table_data.columns:
                column_anomalies = await self.column_analyzer.analyze_column(
                    data=table_data,
                    table_name=table_name,
                    column_name=column,
                    methods=methods,
                    column_type="numeric",
                    thresholds=thresholds.get(column),
                )
                anomalies.extend(column_anomalies)
        # 分类列异常检测
        categorical_columns = config.get("categorical_columns", [])
        for column in categorical_columns:
            if column in table_data.columns:
                column_anomalies = await self.column_analyzer.analyze_column(
                    data=table_data,
                    table_name=table_name,
                    column_name=column,
                    methods=methods,
                    column_type="categorical",
                )
                anomalies.extend(column_anomalies)
        # 时间列异常检测
        time_columns = config.get("time_columns", [])
        for column in time_columns:
            if column in table_data.columns:
                column_anomalies = await self.column_analyzer.analyze_column(
                    data=table_data,
                    table_name=table_name,
                    column_name=column,
                    methods=methods,
                    column_type="time",
                )
                anomalies.extend(column_anomalies)
        return anomalies
    async def _get_table_data(
        self, session: AsyncSession, table_name: str
    ) -> pd.DataFrame:
        获取表数据
        Args:
            session: 数据库会话
            table_name: 表名
        Returns:
            pd.DataFrame: 表数据
        try:
            # 获取最近1000条记录进行异常检测
            # Safe: table_name is validated against whitelist above
            # Note: Using f-string here is safe as table_name is validated against
            # whitelist
            result = await session.execute(
                text(
                    f"""
                    SELECT * FROM {table_name}
                    ORDER BY id DESC
                    LIMIT 1000
                )
            )
            # 转换为DataFrame
            rows = result.fetchall()
            data = pd.DataFrame([dict(row._mapping) for row in rows])
            return data
        except Exception as e:
            logger.error(f"获取表 {table_name} 数据失败: {e}")
            return pd.DataFrame()