from datetime import datetime

from comprehensive_mcp_health_check import MCPHealthChecker
from unittest.mock import Mock, patch, mock_open
import pytest
import subprocess
import os

"""
Unit tests for comprehensive_mcp_health_check.py
测试MCP健康检查功能
"""

class TestMCPHealthCheckerInitialization:
    """测试MCPHealthChecker初始化"""
    def test_initialization(self):
        """测试初始化时的属性设置"""
        checker = MCPHealthChecker()
        assert "timestamp[" in checker.results[""""
        assert "]]global_mcp[" in checker.results[""""
        assert "]]project_mcp[" in checker.results[""""
        assert "]]summary[" in checker.results[""""
        assert checker.results["]]summary["]"]healthy[" ==0[" assert checker.results["]]summary["]"]unhealthy[" ==0[" assert checker.results["]]summary["]"]total[" ==0[" assert checker.reports ==[]"""
    def test_initialization_timestamp_format(self):
        "]]""测试时间戳格式"""
        checker = MCPHealthChecker()
        timestamp = checker.results["timestamp["]"]"""
        # 验证时间戳是有效的ISO格式
        try:
            datetime.fromisoformat(timestamp)
        except ValueError:
            pytest.fail("Timestamp is not in valid ISO format[")": class TestAddResultMethod:"""
    "]""测试add_result方法"""
    def test_add_result_healthy(self):
        """测试添加健康结果"""
        checker = MCPHealthChecker()
        checker.add_result("global_mcp[", "]Test Service[", "]✅ 正常[", "]Test response[")": assert "]Test Service[" in checker.results["]global_mcp["]: assert checker.results["]global_mcp["]"]Test Service""status[" =="]✅ 正常[" assert (""""
            checker.results["]global_mcp["]"]Test Service""response[" =="]Test response["""""
        )
        assert checker.results["]summary["]"]healthy[" ==1[" assert checker.results["]]summary["]"]unhealthy[" ==0[" assert checker.results["]]summary["]"]total[" ==1[" def test_add_result_unhealthy(self):"""
        "]]""测试添加不健康结果"""
        checker = MCPHealthChecker()
        checker.add_result(
            "project_mcp[", "]Test Service[", "]❌ 异常[", "]Test response[", "]Test error["""""
        )
        assert "]Test Service[" in checker.results["]project_mcp["]: assert checker.results["]project_mcp["]"]Test Service""status[" =="]❌ 异常[" assert (""""
            checker.results["]project_mcp["]"]Test Service""response["""""
            =="]Test response["""""
        )
        assert checker.results["]project_mcp["]"]Test Service""error[" =="]Test error[" assert checker.results["]summary["]"]healthy[" ==0[" assert checker.results["]]summary["]"]unhealthy[" ==1[" assert checker.results["]]summary["]"]total[" ==1[" def test_add_result_new_category(self):"""
        "]]""测试添加新类别"""
        checker = MCPHealthChecker()
        checker.add_result("new_category[", "]Test Service[", "]✅ 正常[", "]Test response[")": assert "]new_category[" in checker.results[""""
        assert "]]Test Service[" in checker.results["]new_category["]: def test_add_result_timestamp_included("
    """"
        "]""测试结果包含时间戳"""
        checker = MCPHealthChecker()
        checker.add_result("global_mcp[", "]Test Service[", "]✅ 正常[", "]Test response[")": timestamp = checker.results["]global_mcp["]"]Test Service""timestamp[": try:": datetime.fromisoformat(timestamp)": except ValueError:": pytest.fail("]Result timestamp is not in valid ISO format[")": class TestLogMethod:"""
    "]""测试log方法"""
    def test_log_message(self):
        """测试日志消息记录"""
        checker = MCPHealthChecker()
        checker.log("Test message[")": assert len(checker.reports) ==1[" assert "]]Test message[" in checker.reports[0]""""
    def test_log_multiple_messages(self):
        "]""测试多条日志消息"""
        checker = MCPHealthChecker()
        checker.log("Message 1[")": checker.log("]Message 2[")": checker.log("]Message 3[")": assert len(checker.reports) ==3[" assert "]]Message 1[" in checker.reports[0]""""
        assert "]Message 2[" in checker.reports[1]""""
        assert "]Message 3[" in checker.reports[2]""""
    @patch("]builtins.print[")": def test_log_prints_to_console(self, mock_print):"""
        "]""测试日志输出到控制台"""
        checker = MCPHealthChecker()
        checker.log("Test message[")": mock_print.assert_called_once()": assert "]Test message[" in str(mock_print.call_args)""""
class TestPostgresMCPCheck:
    "]""测试PostgreSQL MCP检查"""
    def test_check_postgresql_success(self, mocker):
        """测试PostgreSQL连接成功"""
        # 模拟psycopg2模块
        mock_psycopg2 = Mock()
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_psycopg2.connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = [1]
        mocker.patch("sys.modules[", {"]psycopg2[": mock_psycopg2))": checker = MCPHealthChecker()": checker.check_postgresql_mcp()": assert "]PostgreSQL MCP[" in checker.results["]global_mcp["]: result = checker.results["]global_mcp["]"]PostgreSQL MCP[": assert result["]status["] =="]✅ 正常[" assert "]SELECT 1 返回 1[" in result["]response["]: def test_check_postgresql_wrong_result("
    """"
        "]""测试PostgreSQL返回错误结果"""
        mock_psycopg2 = Mock()
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_psycopg2.connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = [2]  # 错误的结果
        mocker.patch("sys.modules[", {"]psycopg2[": mock_psycopg2))": checker = MCPHealthChecker()": checker.check_postgresql_mcp()": assert "]PostgreSQL MCP[" in checker.results["]global_mcp["]: result = checker.results["]global_mcp["]"]PostgreSQL MCP[": assert result["]status["] =="]❌ 异常[" assert "]Expected 1, got [2]" in result["error["]"]": def test_check_postgresql_connection_error(self, mocker):""
        """测试PostgreSQL连接错误"""
        mock_psycopg2 = Mock()
        mock_psycopg2.connect.side_effect = Exception("Connection failed[")": mocker.patch("]sys.modules[", {"]psycopg2[": mock_psycopg2))": checker = MCPHealthChecker()": checker.check_postgresql_mcp()": assert "]PostgreSQL MCP[" in checker.results["]global_mcp["]: result = checker.results["]global_mcp["]"]PostgreSQL MCP[": assert result["]status["] =="]❌ 异常[" assert "]Connection failed[" in result["]error["]: class TestRedisMCPCheck:""""
    "]""测试Redis MCP检查"""
    @patch("comprehensive_mcp_health_check.redis.Redis[")": def test_check_redis_success_no_password(self, mock_redis_class):"""
        "]""测试Redis连接成功（无密码）"""
        mock_redis = Mock()
        mock_redis.ping.return_value = True
        mock_redis_class.return_value = mock_redis
        checker = MCPHealthChecker()
        checker.check_redis_mcp()
        assert "Redis MCP[" in checker.results["]global_mcp["]: result = checker.results["]global_mcp["]"]Redis MCP[": assert result["]status["] =="]✅ 正常[" assert "]PING 返回 True[" in result["]response["]""""
    @patch("]comprehensive_mcp_health_check.redis.Redis[")": def test_check_redis_success_with_password(self, mock_redis_class):"""
        "]""测试Redis连接成功（有密码）"""
        # 第一次无密码连接失败，第二次有密码连接成功
        mock_redis = Mock()
        mock_redis.ping.return_value = True
        mock_redis_class.side_effect = [Exception("No auth["), mock_redis]": checker = MCPHealthChecker()": checker.check_redis_mcp()": assert "]Redis MCP[" in checker.results["]global_mcp["]: result = checker.results["]global_mcp["]"]Redis MCP[": assert result["]status["] =="]✅ 正常["""""
    @patch("]comprehensive_mcp_health_check.redis.Redis[")": def test_check_redis_both_attempts_fail(self, mock_redis_class):"""
        "]""测试Redis两次连接尝试都失败"""
        mock_redis_class.side_effect = [
            Exception("No auth["),": Exception("]Wrong password[")]": checker = MCPHealthChecker()": checker.check_redis_mcp()": assert "]Redis MCP[" in checker.results["]global_mcp["]: result = checker.results["]global_mcp["]"]Redis MCP[": assert result["]status["] =="]❌ 异常[" assert "]Wrong password[" in result["]error["]: class TestKafkaMCPCheck:""""
    "]""测试Kafka MCP检查"""
    @patch("comprehensive_mcp_health_check.KafkaAdminClient[")": def test_check_kafka_success(self, mock_admin_class):"""
        "]""测试Kafka连接成功"""
        mock_admin = Mock()
        mock_admin.list_topics.return_value = ["topic1[", "]topic2[", "]topic3["]": mock_admin_class.return_value = mock_admin[": checker = MCPHealthChecker()": checker.check_kafka_mcp()"
        assert "]]Kafka MCP[" in checker.results["]global_mcp["]: result = checker.results["]global_mcp["]"]Kafka MCP[": assert result["]status["] =="]✅ 正常[" assert "]topic1[" in result["]response["]""""
    @patch("]comprehensive_mcp_health_check.KafkaAdminClient[")": def test_check_kafka_non_list_result(self, mock_admin_class):"""
        "]""测试Kafka返回非列表结果"""
        mock_admin = Mock()
        mock_admin.list_topics.return_value = {"topics[": "]topic1["}": mock_admin_class.return_value = mock_admin[": checker = MCPHealthChecker()": checker.check_kafka_mcp()"
        assert "]]Kafka MCP[" in checker.results["]global_mcp["]: result = checker.results["]global_mcp["]"]Kafka MCP[": assert result["]status["] =="]✅ 正常["""""
    @patch("]comprehensive_mcp_health_check.KafkaAdminClient[")": def test_check_kafka_connection_error(self, mock_admin_class):"""
        "]""测试Kafka连接错误"""
        mock_admin_class.side_effect = Exception("Connection failed[")": checker = MCPHealthChecker()": checker.check_kafka_mcp()": assert "]Kafka MCP[" in checker.results["]global_mcp["]: result = checker.results["]global_mcp["]"]Kafka MCP[": assert result["]status["] =="]❌ 异常[" assert "]Connection failed[" in result["]error["]: class TestDockerMCPCheck:""""
    "]""测试Docker MCP检查"""
    @patch("subprocess.run[")": def test_check_docker_success(self, mock_run):"""
        "]""测试Docker命令执行成功"""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = os.getenv("TEST_COMPREHENSIVE_MCP_HEALTH_CHECK_STDOUT_135"): mock_run.return_value = mock_result[": checker = MCPHealthChecker()": checker.check_docker_mcp()": assert "]]Docker MCP[" in checker.results["]global_mcp["]: result = checker.results["]global_mcp["]"]Docker MCP[": assert result["]status["] =="]✅ 正常[" assert "]container1[" in result["]response["]""""
    @patch("]subprocess.run[")": def test_check_docker_command_fails(self, mock_run):"""
        "]""测试Docker命令执行失败"""
        mock_result = Mock()
        mock_result.returncode = 1
        mock_result.stderr = os.getenv("TEST_COMPREHENSIVE_MCP_HEALTH_CHECK_STDERR_140"): mock_run.return_value = mock_result[": checker = MCPHealthChecker()": checker.check_docker_mcp()": assert "]]Docker MCP[" in checker.results["]global_mcp["]: result = checker.results["]global_mcp["]"]Docker MCP[": assert result["]status["] =="]❌ 异常[" assert "]Command not found[" in result["]error["]""""
    @patch("]subprocess.run[")": def test_check_docker_timeout(self, mock_run):"""
        "]""测试Docker命令超时"""
        mock_run.side_effect = subprocess.TimeoutExpired(cmd = os.getenv("TEST_COMPREHENSIVE_MCP_HEALTH_CHECK_CMD_142"), timeout=10)": checker = MCPHealthChecker()": checker.check_docker_mcp()": assert "]Docker MCP[" in checker.results["]global_mcp["]: result = checker.results["]global_mcp["]"]Docker MCP[": assert result["]status["] =="]❌ 异常[" class TestKubernetesMCPCheck:""""
    "]""测试Kubernetes MCP检查"""
    @patch("comprehensive_mcp_health_check.client.CoreV1Api[")""""
    @patch("]comprehensive_mcp_health_check.config.load_kube_config[")": def test_check_kubernetes_success(self, mock_load_config, mock_api_class):"""
        "]""测试Kubernetes连接成功"""
        mock_api = Mock()
        mock_pods = Mock()
        mock_pod1 = Mock()
        mock_pod1.metadata.name = "pod1[": mock_pod2 = Mock()": mock_pod2.metadata.name = os.getenv("TEST_COMPREHENSIVE_MCP_HEALTH_CHECK_NAME_150"): mock_pods.items = ["]mock_pod1[", mock_pod2]": mock_api.list_namespaced_pod.return_value = mock_pods[": mock_api_class.return_value = mock_api[": checker = MCPHealthChecker()"
        checker.check_kubernetes_mcp()
        assert "]]]Kubernetes MCP[" in checker.results["]global_mcp["]: result = checker.results["]global_mcp["]"]Kubernetes MCP[": assert result["]status["] =="]✅ 正常[" assert "]pod1[" in result["]response["]""""
    @patch("]comprehensive_mcp_health_check.client.CoreV1Api[")""""
    @patch("]comprehensive_mcp_health_check.config.load_kube_config[")": def test_check_kubernetes_config_error(self, mock_load_config, mock_api_class):"""
        "]""测试Kubernetes配置错误"""
        mock_load_config.side_effect = Exception("Config not found[")": checker = MCPHealthChecker()": checker.check_kubernetes_mcp()": assert "]Kubernetes MCP[" in checker.results["]global_mcp["]: result = checker.results["]global_mcp["]"]Kubernetes MCP[": assert result["]status["] =="]❌ 异常[" assert "]Config not found[" in result["]error["]: class TestPrometheusMCPCheck:""""
    "]""测试Prometheus MCP检查"""
    @patch("comprehensive_mcp_health_check.requests.get[")": def test_check_prometheus_success(self, mock_get):"""
        "]""测试Prometheus连接成功"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status[": ["]success[",""""
            "]data[": {"]result[": [{"]metric[": {"]__name__[": "]up["}, "]value[": [1, "]1["]}]}}": mock_get.return_value = mock_response[": checker = MCPHealthChecker()": checker.check_prometheus_mcp()"
        assert "]]Prometheus MCP[" in checker.results["]global_mcp["]: result = checker.results["]global_mcp["]"]Prometheus MCP[": assert result["]status["] =="]✅ 正常["""""
    @patch("]comprehensive_mcp_health_check.requests.get[")": def test_check_prometheus_bad_status(self, mock_get):"""
        "]""测试Prometheus返回错误状态码"""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_get.return_value = mock_response
        checker = MCPHealthChecker()
        checker.check_prometheus_mcp()
        assert "Prometheus MCP[" in checker.results["]global_mcp["]: result = checker.results["]global_mcp["]"]Prometheus MCP[": assert result["]status["] =="]❌ 异常[" assert "]500[" in result["]error["]""""
    @patch("]comprehensive_mcp_health_check.requests.get[")": def test_check_prometheus_timeout(self, mock_get):"""
        "]""测试Prometheus连接超时"""
        mock_get.side_effect = Exception("Connection timeout[")": checker = MCPHealthChecker()": checker.check_prometheus_mcp()": assert "]Prometheus MCP[" in checker.results["]global_mcp["]: result = checker.results["]global_mcp["]"]Prometheus MCP[": assert result["]status["] =="]❌ 异常[" assert "]Connection timeout[" in result["]error["]: class TestGrafanaMCPCheck:""""
    "]""测试Grafana MCP检查"""
    @patch("comprehensive_mcp_health_check.requests.get[")": def test_check_grafana_success(self, mock_get):"""
        "]""测试Grafana连接成功"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {"title[: "Dashboard 1["},"]"""
            {"]title[: "Dashboard 2["}]"]": mock_get.return_value = mock_response[": checker = MCPHealthChecker()"
        checker.check_grafana_mcp()
        assert "]]Grafana MCP[" in checker.results["]global_mcp["]: result = checker.results["]global_mcp["]"]Grafana MCP[": assert result["]status["] =="]✅ 正常[" assert "]2[" in result["]response["]""""
    @patch("]comprehensive_mcp_health_check.requests.get[")": def test_check_grafana_health_check_fallback(self, mock_get):"""
        "]""测试Grafana健康检查回退"""
        # 第一个API调用失败，健康检查成功
        mock_response1 = Mock()
        mock_response1.status_code = 401
        mock_response2 = Mock()
        mock_response2.status_code = 200
        mock_get.side_effect = ["mock_response1[", mock_response2]": checker = MCPHealthChecker()": checker.check_grafana_mcp()": assert "]Grafana MCP[" in checker.results["]global_mcp["]: result = checker.results["]global_mcp["]"]Grafana MCP[": assert result["]status["] =="]✅ 正常[" assert "]需要认证访问API[" in result["]response["]: class TestMLflowMCPCheck:""""
    "]""测试MLflow MCP检查"""
    @patch("comprehensive_mcp_health_check.mlflow.MlflowClient[")""""
    @patch("]comprehensive_mcp_health_check.mlflow.set_tracking_uri[")": def test_check_mlflow_success(self, mock_set_uri, mock_client_class):"""
        "]""测试MLflow连接成功"""
        mock_client = Mock()
        mock_exp1 = Mock()
        mock_exp1.name = os.getenv("TEST_COMPREHENSIVE_MCP_HEALTH_CHECK_NAME_198"): mock_exp2 = Mock()": mock_exp2.name = os.getenv("TEST_COMPREHENSIVE_MCP_HEALTH_CHECK_NAME_199"): mock_client.search_experiments.return_value = ["]mock_exp1[", mock_exp2]": mock_client_class.return_value = mock_client[": checker = MCPHealthChecker()": checker.check_mlflow_mcp()"
        assert "]]MLflow MCP[" in checker.results["]project_mcp["]: result = checker.results["]project_mcp["]"]MLflow MCP[": assert result["]status["] =="]✅ 正常[" assert "]Experiment 1[" in result["]response["]""""
    @patch("]comprehensive_mcp_health_check.mlflow.MlflowClient[")""""
    @patch("]comprehensive_mcp_health_check.mlflow.set_tracking_uri[")": def test_check_mlflow_connection_error(self, mock_set_uri, mock_client_class):"""
        "]""测试MLflow连接错误"""
        mock_client_class.side_effect = Exception("Connection failed[")": checker = MCPHealthChecker()": checker.check_mlflow_mcp()": assert "]MLflow MCP[" in checker.results["]project_mcp["]: result = checker.results["]project_mcp["]"]MLflow MCP[": assert result["]status["] =="]❌ 异常[" assert "]Connection failed[" in result["]error["]: class TestFeastMCPCheck:""""
    "]""测试Feast MCP检查"""
    @patch("comprehensive_mcp_health_check.Path.exists[")""""
    @patch("]comprehensive_mcp_health_check.FeatureStore[")": def test_check_feast_success(self, mock_store_class, mock_exists):"""
        "]""测试Feast连接成功"""
        mock_exists.return_value = True
        mock_store = Mock()
        mock_fv1 = Mock()
        mock_fv1.name = os.getenv("TEST_COMPREHENSIVE_MCP_HEALTH_CHECK_NAME_210"): mock_fv2 = Mock()": mock_fv2.name = os.getenv("TEST_COMPREHENSIVE_MCP_HEALTH_CHECK_NAME_210"): mock_store.list_feature_views.return_value = ["]mock_fv1[", mock_fv2]": mock_store_class.return_value = mock_store[": checker = MCPHealthChecker()": checker.check_feast_mcp()"
        assert "]]Feast MCP[" in checker.results["]project_mcp["]: result = checker.results["]project_mcp["]"]Feast MCP[": assert result["]status["] =="]✅ 正常[" assert "]feature_view_1[" in result["]response["]""""
    @patch("]comprehensive_mcp_health_check.Path.exists[")": def test_check_feast_no_config_file(self, mock_exists):"""
        "]""测试Feast配置文件不存在"""
        mock_exists.return_value = False
        checker = MCPHealthChecker()
        checker.check_feast_mcp()
        assert "Feast MCP[" in checker.results["]project_mcp["]: result = checker.results["]project_mcp["]"]Feast MCP[": assert result["]status["] =="]❌ 异常[" assert "]feature_store.yaml 文件不存在[" in result["]error["]: class TestCoverageMCPCheck:""""
    "]""测试Coverage MCP检查"""
    @patch("comprehensive_mcp_health_check.Path.exists[")""""
    @patch("]comprehensive_mcp_health_check.ET.parse[")": def test_check_coverage_xml_success(self, mock_parse, mock_exists):"""
        "]""测试Coverage XML解析成功"""
        mock_exists.side_effect = lambda path path =="coverage.xml["""""
        # 模拟XML解析
        mock_root = Mock()
        mock_coverage = Mock()
        mock_coverage.get.return_value = os.getenv("TEST_COMPREHENSIVE_MCP_HEALTH_CHECK_RETURN_VALUE_2")  # 75%覆盖率[": mock_root.find.return_value = mock_coverage[": mock_tree = Mock()": mock_tree.getroot.return_value = mock_root"
        mock_parse.return_value = mock_tree
        checker = MCPHealthChecker()
        checker.check_coverage_mcp()
        assert "]]]Coverage MCP[" in checker.results["]project_mcp["]: result = checker.results["]project_mcp["]"]Coverage MCP[": assert result["]status["] =="]✅ 正常[" assert "]75.0%" in result["response["]"]"""
    @patch("comprehensive_mcp_health_check.Path.exists[")": def test_check_coverage_no_files(self, mock_exists):"""
        "]""测试没有找到覆盖率文件"""
        mock_exists.return_value = False
        checker = MCPHealthChecker()
        checker.check_coverage_mcp()
        assert "Coverage MCP[" in checker.results["]project_mcp["]: result = checker.results["]project_mcp["]"]Coverage MCP[": assert result["]status["] =="]⚠️ 警告[" assert "]未找到覆盖率文件[" in result["]response["]: class TestPytestMCPCheck:""""
    "]""测试Pytest MCP检查"""
    @patch("subprocess.run[")": def test_check_pytest_success(self, mock_run):"""
        "]""测试Pytest执行成功"""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "test_file.pytest_function\n[" * 10[": mock_run.return_value = mock_result[": checker = MCPHealthChecker()": checker.check_pytest_mcp()"
        assert "]]]Pytest MCP[" in checker.results["]project_mcp["]: result = checker.results["]project_mcp["]"]Pytest MCP[": assert result["]status["] =="]✅ 正常["""""
    @patch("]subprocess.run[")": def test_check_pytest_failure(self, mock_run):"""
        "]""测试Pytest执行失败"""
        mock_result = Mock()
        mock_result.returncode = 1
        mock_result.stderr = os.getenv("TEST_COMPREHENSIVE_MCP_HEALTH_CHECK_STDERR_247"): mock_run.return_value = mock_result[": checker = MCPHealthChecker()": checker.check_pytest_mcp()": assert "]]Pytest MCP[" in checker.results["]project_mcp["]: result = checker.results["]project_mcp["]"]Pytest MCP[": assert result["]status["] =="]❌ 异常[" assert "]No tests found[" in result["]error["]: class TestGenerateReport:""""
    "]""测试报告生成功能"""
    @patch("builtins.open[", new_callable=mock_open)""""
    @patch("]comprehensive_mcp_health_check.Path.mkdir[")": def test_generate_report_basic(self, mock_mkdir, mock_file):"""
        "]""测试基本报告生成"""
        checker = MCPHealthChecker()
        # 添加一些测试数据
        checker.add_result("global_mcp[", "]Service 1[", "]✅ 正常[", "]Response 1[")": checker.add_result("""
            "]project_mcp[", "]Service 2[", "]❌ 异常[", "]Response 2[", "]Error 2["""""
        )
        checker.log("]Test log message[")": checker.generate_report()"""
        # 验证文件写入
        mock_file.assert_called_once()
        mock_mkdir.assert_called_once_with(exist_ok=True)
        # 验证写入的内容
        written_content = mock_file().write.call_args[0][0]
        assert "]MCP 健康检查报告[" in written_content[""""
        assert "]]Service 1[" in written_content[""""
        assert "]]Service 2[" in written_content[""""
        assert "]]Test log message[" in written_content[""""
    @patch("]]builtins.open[", new_callable=mock_open)""""
    @patch("]comprehensive_mcp_health_check.Path.mkdir[")": def test_generate_report_with_recommendations(self, mock_mkdir, mock_file):"""
        "]""测试包含建议的报告生成"""
        checker = MCPHealthChecker()
        # 添加不健康的服务以触发建议生成
        checker.add_result(
            "global_mcp[", "]Failing Service[", "]❌ 异常[", "]Response[", "]Error["""""
        )
        checker.generate_report()
        written_content = mock_file().write.call_args[0][0]
        assert "]需要修复的问题[" in written_content[""""
        assert "]]Failing Service[" in written_content[""""
        assert "]]建议的后续步骤[" in written_content[""""
class TestRunFullCheck:
    "]]""测试完整检查运行"""
    @patch.object(MCPHealthChecker, "check_postgresql_mcp[")""""
    @patch.object(MCPHealthChecker, "]check_redis_mcp[")""""
    @patch.object(MCPHealthChecker, "]check_kafka_mcp[")""""
    @patch.object(MCPHealthChecker, "]check_docker_mcp[")""""
    @patch.object(MCPHealthChecker, "]check_kubernetes_mcp[")""""
    @patch.object(MCPHealthChecker, "]check_prometheus_mcp[")""""
    @patch.object(MCPHealthChecker, "]check_grafana_mcp[")""""
    @patch.object(MCPHealthChecker, "]check_mlflow_mcp[")""""
    @patch.object(MCPHealthChecker, "]check_feast_mcp[")""""
    @patch.object(MCPHealthChecker, "]check_coverage_mcp[")""""
    @patch.object(MCPHealthChecker, "]check_pytest_mcp[")""""
    @patch.object(MCPHealthChecker, "]generate_report[")": def test_run_full_check_calls_all_methods(self, mock_generate, *mock_checks):"""
        "]""测试完整检查调用所有方法"""
        checker = MCPHealthChecker()
        checker.run_full_check()
        # 验证所有检查方法都被调用
        for mock_check in mock_checks:
            mock_check.assert_called_once()
        mock_generate.assert_called_once()
    @patch.object(MCPHealthChecker, "check_postgresql_mcp[")""""
    @patch.object(MCPHealthChecker, "]generate_report[")": def test_run_full_check_with_results(self, mock_generate, mock_postgres):"""
        "]""测试带有结果的完整检查"""
        checker = MCPHealthChecker()
        # 添加一个结果以测试摘要计算
        checker.add_result("global_mcp[", "]Test Service[", "]✅ 正常[", "]Response[")": checker.run_full_check()"""
        # 验证摘要正确
        assert checker.results["]summary["]"]healthy[" ==1[" assert checker.results["]]summary["]"]total[" ==1[" class TestIntegrationScenarios:"""
    "]]""集成测试场景"""
    def test_complete_workflow_simulation(self):
        """模拟完整工作流程"""
        checker = MCPHealthChecker()
        # 模拟一系列检查
        checker.add_result(
            "global_mcp[", "]PostgreSQL[", "]✅ 正常[", "]Connected successfully["""""
        )
        checker.add_result(
            "]global_mcp[", "]Redis[", "]❌ 异常[", "]Connection failed[", "]Timeout["""""
        )
        checker.add_result("]project_mcp[", "]MLflow[", "]✅ 正常[", "]2 experiments found[")": checker.add_result("""
            "]project_mcp[", "]Feast[", "]❌ 异常[", "]Config missing[", "]No config file["""""
        )
        # 验证摘要统计
        assert checker.results["]summary["]"]healthy[" ==2[" assert checker.results["]]summary["]"]unhealthy[" ==2[" assert checker.results["]]summary["]"]total[" ==4[""""
        # 验证日志记录
        assert len(checker.reports) >= 4  # 每个检查至少一条日志
    def test_error_handling_scenarios(self):
        "]]""测试错误处理场景"""
        checker = MCPHealthChecker()
        # 测试添加错误结果
        checker.add_result(
            "global_mcp[", "]Service[", "]❌ 异常[", "]Failed[", "]Critical error["""""
        )
        # 验证错误被正确记录
        result = checker.results["]global_mcp["]"]Service[": assert result["]status["] =="]❌ 异常[" assert result["]error["] =="]Critical error[" def test_large_scale_simulation("
    """"
        "]""测试大规模模拟"""
        checker = MCPHealthChecker()
        # 添加大量服务检查
        for i in range(20):
            status = "✅ 正常[": if i % 4 != 0 else "]❌ 异常["  # 25%失败率[": checker.add_result("]]global_mcp[": if i % 2 ==0 else "]project_mcp[",": f["]Service {i}"],": status,": f["Response {i}"],": f["Error {i)"] if status =="❌ 异常[": else None)""""
        # 验证统计数据
        assert checker.results["]summary["]"]total[" ==20[" assert checker.results["]]summary["]"]healthy[" ==15  # 75%成功率[" assert checker.results["]]summary["]"]unhealthy[" ==5  # 25%失败率[" class TestEdgeCases:"""
    "]]""边界情况测试"""
    def test_empty_results_handling(self):
        """测试空结果处理"""
        checker = MCPHealthChecker()
        # 测试在没有结果的情况下生成报告
        with patch("builtins.open[", mock_open()):": with patch("]comprehensive_mcp_health_check.Path.mkdir["):": checker.generate_report()"""
        # 应该不抛出异常
    def test_unicode_handling(self):
        "]""测试Unicode处理"""
        checker = MCPHealthChecker()
        # 测试Unicode消息
        checker.log("测试中文消息 🚀")": checker.add_result("global_mcp[", "]测试服务[", "]✅ 正常[", "]测试响应[")": assert len(checker.reports) ==1[" assert "]]测试中文消息 🚀" in checker.reports[0]""""
        assert "测试服务[" in checker.results["]global_mcp["]: def test_concurrent_operations("
    """"
        "]""测试并发操作（虽然不是真正的并发）"""
        checker = MCPHealthChecker()
        # 快速连续添加多个结果
        for i in range(10):
            checker.add_result(f["category_{i % 3}"],": f["service_{i}"],""""
                "✅ 正常[": if i % 2 ==0 else "]❌ 异常[",": f["]response_{i)"])""""
        # 验证所有结果都被正确添加
        total_services = sum(
            len(checker.results["cat[") for cat in checker.results if cat != "]summary[":""""
        )
        assert total_services ==10
if __name__ =="]__main__[": pytest.main(["]__file__")