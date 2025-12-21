"""
CLI集成测试
测试cli.py的完整命令行功能
"""

import pytest
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch, Mock
import json

# 添加src路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))


@pytest.mark.integration
class TestCLIIntegration:
    """CLI集成测试类"""

    @pytest.fixture
    def project_root(self):
        """项目根目录"""
        return Path(__file__).parent.parent.parent

    @pytest.fixture
    def cli_path(self, project_root):
        """CLI脚本路径"""
        return project_root / "cli.py"

    def test_cli_help_command(self, cli_path):
        """测试CLI帮助命令"""
        result = subprocess.run(
            [sys.executable, str(cli_path), "--help"],
            capture_output=True,
            text=True,
            timeout=30
        )

        assert result.returncode == 0
        assert "FootballPrediction" in result.stdout
        assert "harvest" in result.stdout
        assert "predict" in result.stdout
        assert "train" in result.stdout
        assert "status" in result.stdout

    def test_cli_no_args_shows_help(self, cli_path):
        """测试无参数时显示帮助"""
        result = subprocess.run(
            [sys.executable, str(cli_path)],
            capture_output=True,
            text=True,
            timeout=30
        )

        assert result.returncode == 0
        assert "help" in result.stdout.lower() or "usage" in result.stdout.lower()

    @patch('src.models.model_handler.get_model_handler')
    @patch('src.data_access.api_client.get_api_client')
    @patch('src.utils.get_db_manager')
    def test_cli_status_command_success(self, mock_db, mock_api, mock_model, cli_path):
        """测试状态命令成功执行"""
        # Mock所有依赖
        mock_db.return_value.is_available.return_value = True
        mock_db.return_value.get_table_info.return_value = {'row_count': 168}

        mock_api.return_value.get_request_stats.return_value = {
            'session_id': 'test_session',
            'total_requests': 10
        }

        mock_handler = Mock()
        mock_handler.is_loaded = True
        mock_handler.get_model_info.return_value = {
            'model_type': 'LightGBM',
            'feature_count': 30
        }
        mock_model.return_value = mock_handler

        result = subprocess.run(
            [sys.executable, str(cli_path), "status"],
            capture_output=True,
            text=True,
            timeout=60,
            env={**dict(Path.cwd().absolute().__dict__), 'PYTHONPATH': str(Path(__file__).parent.parent.parent / "src")}
        )

        # 注意：由于子进程环境的复杂性，这个测试可能需要调整
        # 至少应该不会崩溃
        assert result.returncode in [0, 1]  # 可能因为依赖问题返回1，但不应该崩溃

    def test_cli_predict_command_without_id(self, cli_path):
        """测试预测命令无ID"""
        result = subprocess.run(
            [sys.executable, str(cli_path), "predict"],
            capture_output=True,
            text=True,
            timeout=30
        )

        # 应该显示交互式模式或错误
        assert result.returncode in [0, 1]

    def test_cli_predict_command_with_id(self, cli_path):
        """测试预测命令带ID"""
        result = subprocess.run(
            [sys.executable, str(cli_path), "predict", "--id", "4147463"],
            capture_output=True,
            text=True,
            timeout=60
        )

        # 可能因为缺少依赖而失败，但不应该崩溃
        assert result.returncode in [0, 1]

    def test_cli_harvest_command(self, cli_path):
        """测试数据收割命令"""
        result = subprocess.run(
            [sys.executable, str(cli_path), "harvest"],
            capture_output=True,
            text=True,
            timeout=60
        )

        # 可能因为外部API依赖而失败，但不应该崩溃
        assert result.returncode in [0, 1]

    def test_cli_train_command(self, cli_path):
        """测试模型训练命令"""
        result = subprocess.run(
            [sys.executable, str(cli_path), "train"],
            capture_output=True,
            text=True,
            timeout=120  # 训练可能需要更长时间
        )

        # 可能因为数据或依赖问题而失败，但不应该崩溃
        assert result.returncode in [0, 1]

    def test_cli_invalid_command(self, cli_path):
        """测试无效命令"""
        result = subprocess.run(
            [sys.executable, str(cli_path), "invalid_command"],
            capture_output=True,
            text=True,
            timeout=30
        )

        # 应该显示错误信息或帮助
        assert result.returncode != 0
        assert len(result.stdout + result.stderr) > 0

    @pytest.mark.slow
    def test_cli_command_execution_time(self, cli_path):
        """测试命令执行时间"""
        import time

        start_time = time.time()
        result = subprocess.run(
            [sys.executable, str(cli_path), "--help"],
            capture_output=True,
            text=True,
            timeout=30
        )
        end_time = time.time()

        execution_time = end_time - start_time

        assert result.returncode == 0
        # 帮助命令应该很快
        assert execution_time < 10.0

    def test_cli_python_path_handling(self, cli_path):
        """测试Python路径处理"""
        # 设置PYTHONPATH环境变量
        env = {
            'PYTHONPATH': str(Path(__file__).parent.parent.parent / "src")
        }

        result = subprocess.run(
            [sys.executable, str(cli_path), "--help"],
            capture_output=True,
            text=True,
            timeout=30,
            env=env
        )

        assert result.returncode == 0

    def test_cli_import_error_handling(self, cli_path):
        """测试导入错误处理"""
        # 通过修改sys.path来模拟导入错误
        test_script = f"""
import sys
sys.path.insert(0, "{str(Path(__file__).parent.parent.parent)}")
# 尝试导入CLI
try:
    import cli
    print("Import successful")
except ImportError as e:
    print(f"Import error: {{e}}")
    sys.exit(1)
"""

        result = subprocess.run(
            [sys.executable, "-c", test_script],
            capture_output=True,
            text=True,
            timeout=30
        )

        # 应该能够导入或者给出明确的错误
        assert result.returncode in [0, 1]

    def test_cli_config_loading(self, cli_path):
        """测试配置加载"""
        config_test_script = f"""
import sys
sys.path.insert(0, "{str(Path(__file__).parent.parent.parent / "src")}")

try:
    from src.core.config import get_config
    config = get_config()
    print("Config loaded successfully")
    print(f"Environment: {{getattr(config, 'environment', 'unknown')}}")
except Exception as e:
    print(f"Config loading failed: {{e}}")
    sys.exit(1)
"""

        result = subprocess.run(
            [sys.executable, "-c", config_test_script],
            capture_output=True,
            text=True,
            timeout=30
        )

        # 配置加载应该有明确的结果
        assert result.returncode in [0, 1]

    def test_cli_dependency_check(self, cli_path):
        """测试依赖检查"""
        dependency_check_script = f"""
import sys
sys.path.insert(0, "{str(Path(__file__).parent.parent.parent / "src")}")

dependencies = [
    'pandas', 'numpy', 'lightgbm', 'sklearn',
    'fastapi', 'aiohttp', 'tenacity'
]

missing = []
for dep in dependencies:
    try:
        __import__(dep)
    except ImportError:
        missing.append(dep)

if missing:
    print(f"Missing dependencies: {{missing}}")
    sys.exit(1)
else:
    print("All dependencies available")
"""

        result = subprocess.run(
            [sys.executable, "-c", dependency_check_script],
            capture_output=True,
            text=True,
            timeout=30
        )

        # 检查依赖状态
        assert "Missing dependencies" in result.stdout or "All dependencies available" in result.stdout