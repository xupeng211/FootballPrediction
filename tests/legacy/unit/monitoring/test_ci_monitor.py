from datetime import datetime, timedelta, timezone
from pathlib import Path

from scripts.ci_monitor import GitHubCIMonitor
from unittest.mock import Mock, patch
import pytest
import tempfile
import os

pytestmark = pytest.mark.unit
class TestGitHubCIMonitor:
    """GitHubCIMonitor类测试 - 验证CI监控器的核心功能和API集成"""
    def setup_method(self):
        """设置测试环境 - 为每个测试方法创建独立的监控器实例"""
        self.temp_dir = tempfile.mkdtemp()
        self.test_project_root = Path(self.temp_dir)
        # 创建模拟的Git仓库结构
        (self.test_project_root / ".git[").mkdir()": with patch.dict("]os.environ[", {"]GITHUB_TOKEN[": "]test_token_123[")):": self.monitor = GitHubCIMonitor(str(self.test_project_root))": def test_monitor_initialization(self):""
        "]""测试监控器初始化 - 确保基本属性正确设置和环境配置生效"""
    assert self.monitor.project_root ==self.test_project_root
    assert self.monitor.api_base =="https_/api.github.com[" assert "]Bearer test_token_123[" in self.monitor.headers.get("]Authorization[", "]")": def test_github_token_detection(self):"""
        """测试GitHub令牌检测 - 验证多种令牌配置方式的优先级和兼容性"""
        # 测试环境变量GITHUB_TOKEN
        with patch.dict("os.environ[", {"]GITHUB_TOKEN[": "]env_token[")):": monitor = GitHubCIMonitor(str(self.test_project_root))": assert monitor.token =="]env_token["""""
        # 测试环境变量GH_TOKEN
        with patch.dict("]os.environ[", {"]GH_TOKEN[": "]gh_token["), clear = True)": monitor = GitHubCIMonitor(str(self.test_project_root))": assert monitor.token =="]gh_token["""""
        # 测试无令牌情况
        with patch.dict("]os.environ[", {), clear = True)": with patch("]subprocess.run[") as mock_run:": mock_run.return_value.returncode = 1[": monitor = GitHubCIMonitor(str(self.test_project_root))": assert monitor.token is None"
    @patch("]]subprocess.run[")": def test_repository_info_parsing(self, mock_run):"""
        "]""测试仓库信息解析 - 验证HTTPS和SSH格式URL的正确解析"""
        # 测试HTTPS格式URL
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = os.getenv("TEST_CI_MONITOR_STDOUT_32"): monitor = GitHubCIMonitor(str(self.test_project_root))": repo_info = monitor._get_repository_info()": assert repo_info["]owner["] =="]owner[" assert repo_info["]repo["] =="]repo[" assert repo_info["]full_name["] =="]owner/repo["""""
        # 测试SSH格式URL
        mock_run.return_value.stdout = os.getenv("TEST_CI_MONITOR_STDOUT_34"): monitor = GitHubCIMonitor(str(self.test_project_root))": repo_info = monitor._get_repository_info()": assert repo_info["]owner["] =="]owner[" assert repo_info["]repo["] =="]repo["""""
    @patch("]requests.get[")": def test_get_latest_workflows(self, mock_get):"""
        "]""测试获取工作流列表 - 验证GitHub API调用和响应数据处理"""
        # 模拟GitHub API响应
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
        "workflow_runs[": [""""
        {
        "]id[": 123456,""""
        "]run_number[": 42,""""
            "]status[": ["]completed[",""""
                "]conclusion[": ["]success[",""""
                    "]head_commit[": {"]message[": "]feat["},""""
                    "]head_branch[": ["]main[",""""
                    "]created_at[: "2024-01-01T12:00:00Z[","]"""
                    "]html_url[: "https:_/github.com/owner/repo/actions/runs/123456["}"]"""
            ]
        }
        mock_get.return_value = mock_response
        # 设置必要的属性确保API调用能够执行
        self.monitor.token = os.getenv("TEST_CI_MONITOR_TOKEN_55"): self.monitor.repo_info = {"]full_name[: "owner/repo["}"]": workflows = self.monitor.get_latest_workflows(limit=5)": assert len(workflows) ==1"
    assert workflows[0]"]id[" ==123456[" assert workflows[0]"]]status[" =="]completed[" assert workflows[0]"]conclusion[" =="]success["""""
        # 验证API调用参数
        mock_get.assert_called_once()
        call_args = mock_get.call_args
    assert call_args[1]"]params""per_page[" ==5[" def test_failure_analysis_dependency_conflict(self):"""
        "]]""测试依赖冲突分析 - 验证常见依赖版本冲突的识别和建议"""
        logs = """
        ERROR: pip's dependency resolver does not currently handle this dependency conflict.
        ERROR: packaging version conflict detected = black=23.12.1 requires packaging>=22.0
        but safety==2.3.5 requires packaging<22.0,>=21.0
        """
        analysis = self.monitor.analyze_failure_reason(logs)
    assert analysis["failure_type["] =="]dependency_conflict[" assert analysis["]severity["] =="]high[" assert any(""""
        "]requirements.txt[": in suggestion for suggestion in analysis["]suggestions["]:""""
        )
    assert any("]版本冲突[" in suggestion for suggestion in analysis["]suggestions["])": def test_failure_analysis_missing_dependency(self):"""
        "]""测试缺失依赖分析 - 验证ImportError和ModuleNotFoundError的识别"""
        logs = """
        ModuleNotFoundError: No module named 'requests'
        ImportError: cannot import name 'structlog' from 'structlog'
        """
        analysis = self.monitor.analyze_failure_reason(logs)
    assert analysis["failure_type["] =="]missing_dependency[" assert analysis["]severity["] =="]high[" assert any(""""
        "]requirements[": in suggestion for suggestion in analysis["]suggestions["]:""""
        )
    def test_failure_analysis_code_style(self):
        "]""测试代码风格分析 - 验证black、isort、flake8等工具错误的识别"""
        logs = """
        flake8 error: line too long (88 > 79 characters)
        black would reformat src_main.py
        isort would reformat imports in src/utils.py
        """
        analysis = self.monitor.analyze_failure_reason(logs)
    assert analysis["failure_type["] =="]code_style[" assert analysis["]severity["] =="]low[" assert any("]make fix[" in suggestion for suggestion in analysis["]suggestions["])": def test_failure_analysis_test_failure(self):"""
        "]""测试测试失败分析 - 验证pytest错误和断言失败的识别"""
        logs = """
        FAILED tests_test_basic.py:TestConfig:test_config_creation - AssertionError
        pytest failed with 2 test failures:
        test session failed
        """
        analysis = self.monitor.analyze_failure_reason(logs)
    assert analysis["failure_type["] =="]test_failure[" assert analysis["]severity["] =="]medium[" assert any("]make test[" in suggestion for suggestion in analysis["]suggestions["])": def test_time_formatting(self):"""
        "]""测试时间格式化 - 验证相对时间显示的准确性和可读性"""
        # 测试不同时间间隔的格式化
        now = datetime.now(timezone.utc)
        # 5分钟前
        five_min_ago = now - timedelta(minutes=5)
    assert "5分钟前[" in self.monitor._format_time_ago(five_min_ago)""""
        # 2小时前
        two_hours_ago = now - timedelta(hours=2)
    assert "]2小时前[" in self.monitor._format_time_ago(two_hours_ago)""""
        # 3天前
        three_days_ago = now - timedelta(days=3)
    assert "]3天前[" in self.monitor._format_time_ago(three_days_ago)""""
    @patch("]requests.get[")": def test_api_error_handling(self, mock_get):"""
        "]""测试API错误处理 - 验证网络错误和认证失败的优雅处理"""
        # 模拟网络错误
        mock_get.side_effect = Exception("网络连接失败[")": self.monitor.token = os.getenv("TEST_CI_MONITOR_TOKEN_55"): self.monitor.repo_info = {"]full_name[": ["]owner_repo["}": workflows = self.monitor.get_latest_workflows()": assert workflows ==[]  # 错误时应返回空列表[""
        # 模拟认证错误
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = Exception("]]认证失败[")": mock_get.return_value = mock_response[": mock_get.side_effect = None[": workflows = self.monitor.get_latest_workflows()"
    assert workflows ==[]
    def test_monitor_without_token(self):
        "]]]""测试无令牌场景 - 验证缺少GitHub令牌时的降级处理"""
        with patch.dict("os.environ[", {), clear = True)": with patch("]subprocess.run[") as mock_run:": mock_run.return_value.returncode = 1[": monitor = GitHubCIMonitor(str(self.test_project_root))""
                # 无令牌时应返回空结果而不是抛出异常
    assert monitor.get_latest_workflows() ==[]
    assert monitor.get_workflow_jobs(123) ==[]
    assert monitor.get_job_logs(456) =="]]" def test_monitor_without_repo_info("
    """"
        """测试无仓库信息场景 - 验证非Git仓库环境下的错误处理"""
        with patch("subprocess.run[") as mock_run:": mock_run.return_value.returncode = 1  # 模拟非Git仓库[": monitor = GitHubCIMonitor(str(self.test_project_root))""
            # 无仓库信息时应该有适当的错误处理
    assert monitor.repo_info =={}
    assert monitor.get_latest_workflows() ==[]
class TestCIMonitorIntegration:
    "]]""CI监控集成测试 - 验证完整工作流程和真实场景适配性"""
    @patch("subprocess.run[")": def test_git_repository_detection(self, mock_run):"""
        "]""测试Git仓库检测 - 验证不同Git配置下的仓库信息获取"""
        # 模拟成功的Git命令
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = os.getenv("TEST_CI_MONITOR_STDOUT_136"): with tempfile.TemporaryDirectory() as temp_dir:": monitor = GitHubCIMonitor(temp_dir)": repo_info = monitor._get_repository_info()": assert repo_info["]owner["] =="]test[" assert repo_info["]repo["] =="]repo[" def test_full_workflow_status_display("
    """"
        "]""测试完整工作流状态显示 - 验证状态格式化和用户界面输出"""
        mock_workflows = [
        {
        "id[": 123,""""
        "]run_number[": 1,""""
        "]status[": ["]completed[",""""
            "]conclusion[": ["]success[",""""
                "]head_commit[": {"]message[": "]初始提交["},""""
                "]head_branch[": ["]main[",""""
                "]created_at[: "2024-01-01T12:00:00Z[","]"""
                "]html_url[: "https:_/github.com/test/repo/actions/runs/123["},"]"""
            {
                "]id[": 124,""""
                "]run_number[": 2,""""
                "]status[": ["]completed[",""""
                "]conclusion[": ["]failure[",""""
                "]head_commit[": {"]message[": "]修复bug["},""""
                "]head_branch[": ["]develop[",""""
                "]created_at[: "2024-01-01T13:00:00Z[","]"""
                "]html_url[: "https://github.com/test/repo/actions/runs/124["}]"]"""
        # 这里主要测试不会抛出异常，实际输出会在控制台显示
        monitor = GitHubCIMonitor()
        monitor.display_workflow_status(mock_workflows)  # 应该正常执行完成
    def test_empty_workflow_display(self):
        "]""测试空工作流显示 - 验证无CI记录时的用户友好提示"""
        monitor = GitHubCIMonitor()
        monitor.display_workflow_status([])  # 应该显示友好的空状态提示