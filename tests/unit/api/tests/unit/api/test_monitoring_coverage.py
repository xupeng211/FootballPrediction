import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch, AsyncMock
import pytest

"""
Monitoring模块覆盖率测试
临时修复相对导入以提升覆盖率
"""


# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

# 设置测试环境变量
os.environ["TESTING"] = "true"
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

# Mock外部依赖
sys.modules["psutil"] = Mock(
    cpu_percent=Mock(return_value=25.5),
    virtual_memory=Mock(
        return_value=Mock(total=8000000000, available=4000000000, percent=50.0)
    ),
    disk_usage=Mock(
        return_value=Mock(total=1000000000000, used=500000000000, percent=50.0)
    ),
    Process=Mock(
        return_value=Mock(
            memory_info=Mock(return_value=Mock(rss=200000000)),
            memory_percent=Mock(return_value=2.5),
        )
    ),
)

sys.modules["redis"] = Mock(
    Redis=Mock(
        return_value=Mock(
            ping=Mock(return_value=True),
            info=Mock(
                return_value={
                    "connected_clients": 5,
                    "used_memory": 1000000,
                    "used_memory_human": "1M",
                }
            ),
        )
    )
)

# Mock内部模块
mock_metrics_collector = Mock()
mock_metrics_collector.get_metrics_collector = Mock(
    return_value=Mock(
        collect_all_metrics=AsyncMock(return_value={}),
        get_metric_value=Mock(return_value=0),
        register_metric=Mock(),
    )
)
sys.modules["src.monitoring.metrics_collector"] = mock_metrics_collector

mock_metrics_exporter = Mock()
mock_metrics_exporter.get_metrics_exporter = Mock(
    return_value=Mock(
        generate_prometheus_metrics=Mock(
            return_value="# HELP test_metric\n# TYPE test_metric counter\ntest_metric 1\n"
        ),
        export_metrics=Mock(),
    )
)
sys.modules["src.monitoring.metrics_exporter"] = mock_metrics_exporter

sys.modules["src.core.logging"] = Mock(
    get_logger=Mock(return_value=Mock(info=Mock(), warning=Mock(), error=Mock()))
)

sys.modules["src.database.connection"] = Mock(get_db_session=Mock())


@pytest.fixture(scope="module", autouse=True)
def setup_monitoring_module():
    """设置monitoring模块"""
    # 读取monitoring.py文件
    monitoring_file = project_root / "src" / "api" / "monitoring.py"
    with open(monitoring_file, "r", encoding="utf-8") as f:
        code = f.read()

    # 修复相对导入
    code = code.replace(
        "from ..monitoring.metrics_collector import get_metrics_collector",
        "from src.monitoring.metrics_collector import get_metrics_collector",
    )
    code = code.replace(
        "from ..monitoring.metrics_exporter import get_metrics_exporter",
        "from src.monitoring.metrics_exporter import get_metrics_exporter",
    )

    # 创建临时模块
    module_name = "monitoring_test"
    import importlib.util

    spec = importlib.util.spec_from_loader(module_name, loader=None)
    monitoring_mod = importlib.util.module_from_spec(spec)

    # 执行代码
    exec(code, monitoring_mod.__dict__)

    # 添加到sys.modules
    sys.modules[module_name] = monitoring_mod

    yield monitoring_mod

    # 清理
    if module_name in sys.modules:
        del sys.modules[module_name]


class TestMonitoringCoverage:
    """监控模块覆盖率测试"""

    @pytest.mark.asyncio
    async def test_database_metrics_coverage(self, setup_monitoring_module):
        """测试数据库指标覆盖率"""
        monitoring = setup_monitoring_module

        # 创建mock session
        mock_session = MagicMock()

        # 模拟健康检查成功
        def mock_execute(query):
            if "SELECT 1" in query:
                return MagicMock(fetchone=lambda: (1,))
            elif "teams" in query:
                return MagicMock(fetchone=lambda: (10,))
            elif "matches" in query:
                return MagicMock(fetchone=lambda: (20,))
            elif "predictions" in query:
                return MagicMock(fetchone=lambda: (30,))
            elif "pg_stat_activity" in query:
                return MagicMock(fetchone=lambda: (5,))
            else:
                return MagicMock(fetchone=lambda: (0,))

        mock_session.execute.side_effect = mock_execute

        # 测试成功路径
        result = await monitoring._get_database_metrics(mock_session)
        assert result["healthy"] is True
        assert result["statistics"]["teams_count"] == 10
        assert result["statistics"]["matches_count"] == 20
        assert result["statistics"]["predictions_count"] == 30
        assert result["statistics"]["active_connections"] == 5
        assert "response_time_ms" in result

        # 测试失败路径
        mock_session.execute.side_effect = Exception("Database error")
        result = await monitoring._get_database_metrics(mock_session)
        assert result["healthy"] is False
        assert "error" in result

    @pytest.mark.asyncio
    async def test_business_metrics_coverage(self, setup_monitoring_module):
        """测试业务指标覆盖率"""
        monitoring = setup_monitoring_module

        # 创建mock session
        mock_session = MagicMock()

        # 测试正常数据
        mock_session.execute.side_effect = [
            MagicMock(fetchone=lambda: (100,)),  # 24h predictions
            MagicMock(fetchone=lambda: (25,)),  # upcoming matches
            MagicMock(fetchone=lambda: (75.0,)),  # accuracy rate
        ]

        result = await monitoring._get_business_metrics(mock_session)
        assert result["24h_predictions"] == 100
        assert result["upcoming_matches_7d"] == 25
        assert result["model_accuracy_30d"] == 75.0
        assert "last_updated" in result

        # 测试NULL值
        mock_session.execute.side_effect = [
            MagicMock(fetchone=lambda: (None,)),
            MagicMock(fetchone=lambda: (None,)),
            MagicMock(fetchone=lambda: (None,)),
        ]

        result = await monitoring._get_business_metrics(mock_session)
        assert result["24h_predictions"] is None
        assert result["upcoming_matches_7d"] is None
        assert result["model_accuracy_30d"] is None

    @pytest.mark.asyncio
    async def test_system_metrics_coverage(self, setup_monitoring_module):
        """测试系统指标覆盖率"""
        monitoring = setup_monitoring_module

        # 测试正常情况
        result = await monitoring._get_system_metrics()
        assert "cpu" in result
        assert "memory" in result
        assert "disk" in result
        assert "process" in result

        # 测试CPU错误
        original_cpu = sys.modules["psutil"].cpu_percent
        sys.modules["psutil"].cpu_percent = Mock(side_effect=Exception("CPU error"))
        result = await monitoring._get_system_metrics()
        assert "error" in result.get("cpu", {})
        sys.modules["psutil"].cpu_percent = original_cpu

        # 测试内存错误
        original_memory = sys.modules["psutil"].virtual_memory
        sys.modules["psutil"].virtual_memory = Mock(
            side_effect=Exception("Memory error")
        )
        result = await monitoring._get_system_metrics()
        assert "error" in result.get("memory", {})
        sys.modules["psutil"].virtual_memory = original_memory

        # 测试磁盘错误
        original_disk = sys.modules["psutil"].disk_usage
        sys.modules["psutil"].disk_usage = Mock(side_effect=Exception("Disk error"))
        result = await monitoring._get_system_metrics()
        assert "error" in result.get("disk", {})
        sys.modules["psutil"].disk_usage = original_disk

        # 测试进程错误
        original_process = sys.modules["psutil"].Process
        sys.modules["psutil"].Process = Mock(side_effect=Exception("Process error"))
        result = await monitoring._get_system_metrics()
        assert "error" in result.get("process", {})
        sys.modules["psutil"].Process = original_process

    @pytest.mark.asyncio
    async def test_redis_metrics_coverage(self, setup_monitoring_module):
        """测试Redis指标覆盖率"""
        monitoring = setup_monitoring_module

        # 测试连接成功
        result = await monitoring._get_redis_metrics()
        assert result["healthy"] is True
        assert "connected_clients" in result
        assert "used_memory" in result

        # 测试连接失败
        original_redis = sys.modules["redis"]
        sys.modules["redis"] = Mock(
            Redis=Mock(side_effect=Exception("Redis connection failed"))
        )
        result = await monitoring._get_redis_metrics()
        assert result["healthy"] is False
        assert "error" in result
        sys.modules["redis"] = original_redis

    @pytest.mark.asyncio
    async def test_get_metrics_endpoint_coverage(self, setup_monitoring_module):
        """测试/metrics端点覆盖率"""
        monitoring = setup_monitoring_module

        # 创建mock session
        mock_session = MagicMock()
        mock_session.execute.return_value.fetchone.return_value = (1,)

        # Mock所有依赖
        with patch.object(monitoring, "_get_database_metrics") as mock_db:
            with patch.object(monitoring, "_get_system_metrics") as mock_sys:
                with patch.object(monitoring, "_get_redis_metrics") as mock_redis:
                    with patch.object(
                        monitoring, "_get_business_metrics"
                    ) as mock_business:
                        # 设置返回值
                        mock_db.return_value = {"healthy": True, "statistics": {}}
                        mock_sys.return_value = {"cpu": {"usage": 25.5}}
                        mock_redis.return_value = {"healthy": True}
                        mock_business.return_value = {"24h_predictions": 100}

                        # 测试所有健康
                        result = await monitoring.get_metrics(mock_session)
                        assert result["status"] == "healthy"
                        assert "system" in result
                        assert "database" in result
                        assert "business" in result

                        # 测试部分不健康
                        mock_db.return_value = {"healthy": False, "error": "DB error"}
                        result = await monitoring.get_metrics(mock_session)
                        assert result["status"] == "degraded"

                        # 测试全部不健康
                        mock_sys.return_value = {"error": "System error"}
                        mock_redis.return_value = {
                            "healthy": False,
                            "error": "Redis error",
                        }
                        result = await monitoring.get_metrics(mock_session)
                        assert result["status"] == "unhealthy"

    @pytest.mark.asyncio
    async def test_get_status_endpoint_coverage(self, setup_monitoring_module):
        """测试/status端点覆盖率"""
        monitoring = setup_monitoring_module

        # 创建mock session
        mock_session = MagicMock()

        # 测试正常状态
        result = await monitoring.get_status(mock_session)
        assert "status" in result
        assert "timestamp" in result
        assert "services" in result
        assert "database" in result["services"]
        assert "system" in result["services"]

    @pytest.mark.asyncio
    async def test_prometheus_endpoint_coverage(self, setup_monitoring_module):
        """测试Prometheus端点覆盖率"""
        monitoring = setup_monitoring_module

        # 创建mock session
        mock_session = MagicMock()

        # 测试成功生成Prometheus指标
        result = await monitoring.get_prometheus_metrics(mock_session)
        assert isinstance(result, PlainTextResponse)
        assert "text/plain" in result.media_type

    def test_router_configuration_coverage(self, setup_monitoring_module):
        """测试路由配置覆盖率"""
        monitoring = setup_monitoring_module

        # 验证路由
        assert hasattr(monitoring, "router")
        assert hasattr(monitoring.router, "routes")
        assert hasattr(monitoring.router, "tags")
        assert "monitoring" in monitoring.router.tags

    @pytest.mark.asyncio
    async def test_collector_endpoints_coverage(self, setup_monitoring_module):
        """测试收集器端点覆盖率"""
        monitoring = setup_monitoring_module

        # 创建mock session
        mock_session = MagicMock()

        # 测试收集器状态
        mock_metrics_collector.get_metrics_collector()

        # 测试触发收集
        result = await monitoring.trigger_collection(mock_session)
        assert "message" in result

        # 测试收集器状态
        result = await monitoring.get_collector_status(mock_session)
        assert "status" in result

        # 测试启用/禁用
        result = await management.enable_collector(mock_session, "test_metric")
        assert "message" in result

        result = await management.disable_collector(mock_session, "test_metric")
        assert "message" in result
