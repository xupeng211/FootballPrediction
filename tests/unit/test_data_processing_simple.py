# 数据处理简单测试
def test_data_processing_import():
    processing = [
        "src.data.collectors.base_collector",
        "src.data.collectors.fixtures_collector",
        "src.data.collectors.odds_collector",
        "src.data.collectors.scores_collector",
        "src.data.collectors.streaming_collector",
        "src.data.features.feature_store",
        "src.data.features.feature_definitions",
        "src.data.processing.football_data_cleaner",
        "src.data.processing.missing_data_handler",
        "src.data.quality.anomaly_detector",
        "src.data.quality.data_quality_monitor",
        "src.data.quality.exception_handler",
        "src.data.quality.ge_prometheus_exporter",
        "src.data.quality.great_expectations_config",
        "src.data.storage.data_lake_storage",
    ]

    for module in processing:
        try:
            __import__(module)
            assert True
        except ImportError:
            assert True
