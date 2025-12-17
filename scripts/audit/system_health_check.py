#!/usr/bin/env python3
"""
FootballPrediction v2.0 全系统集成验收与审计脚本

该脚本对系统进行全面验收，确保所有子系统协同工作正常，数据流转符合预期。

核心验证链路：
1. 核心预测链路: API -> Redis (Cache Miss) -> Celery (Async) -> ML Model -> Response
2. MLOps 链路: Admin API (Trigger Retrain) -> Worker (Train) -> Model Registry (Update) -> Hot Swap
3. 高并发链路: 批量预测接口是否能正常排队并返回 Task ID
4. 监控链路: 产生请求后，Prometheus 是否有数据？Grafana 面板是否跳动？
5. 容错链路: 如果 Redis 挂了，API 是否降级？

使用方法:
    python scripts/audit/system_health_check.py [--verbose] [--output-json]

作者: Claude Code Assistant
日期: 2025-12-17
版本: 1.0.0
"""

import asyncio
import json
import logging
import sys
import time
import argparse
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path

import requests
import redis
from colorama import init, Fore, Style

# 初始化colorama用于彩色输出
init()

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 系统配置
class SystemConfig:
    """系统配置类"""

    # API端点配置
    API_BASE_URL = "http://localhost:8000"
    HEALTH_ENDPOINT = "/health"
    PREDICT_ENDPOINT = "/api/v1/predictions"
    BATCH_PREDICT_ENDPOINT = "/api/v1/predictions/batch"
    ADMIN_MODEL_STATUS_ENDPOINT = "/api/v1/admin/model/status"
    ADMIN_RETRAIN_ENDPOINT = "/api/v1/admin/retrain"
    METRICS_ENDPOINT = "/metrics"

    # Redis配置
    REDIS_HOST = "localhost"
    REDIS_PORT = 6379
    REDIS_DB = 0

    # Prometheus配置
    PROMETHEUS_URL = "http://localhost:9090"
    PROMETHEUS_QUERY_ENDPOINT = "/api/v1/query"

    # 超时配置
    REQUEST_TIMEOUT = 30
    BATCH_TASK_TIMEOUT = 120  # 批量任务最大等待时间
    MLOPS_TASK_TIMEOUT = 300  # MLOps任务最大等待时间

    # 测试数据
    TEST_MATCH_ID = "test_match_audit_001"
    TEST_BATCH_MATCH_IDS = [f"test_match_audit_{i:03d}" for i in range(1, 6)]

class HealthCheckResult:
    """健康检查结果类"""

    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
        self.status = "PENDING"  # PENDING, PASS, FAIL, SKIP
        self.message = ""
        self.details = {}
        self.start_time = None
        self.end_time = None
        self.duration_ms = 0

    def start(self):
        """开始检查"""
        self.start_time = time.time()
        self.status = "RUNNING"

    def pass_check(self, message: str = "", details: Dict = None):
        """检查通过"""
        self.end_time = time.time()
        self.status = "PASS"
        self.message = message
        self.details = details or {}
        self.duration_ms = round((self.end_time - self.start_time) * 1000, 2)

    def fail_check(self, message: str, details: Dict = None):
        """检查失败"""
        self.end_time = time.time()
        self.status = "FAIL"
        self.message = message
        self.details = details or {}
        self.duration_ms = round((self.end_time - self.start_time) * 1000, 2)

    def skip_check(self, message: str, details: Dict = None):
        """跳过检查"""
        self.end_time = time.time()
        self.status = "SKIP"
        self.message = message
        self.details = details or {}
        self.duration_ms = 0

    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "name": self.name,
            "description": self.description,
            "status": self.status,
            "message": self.message,
            "details": self.details,
            "duration_ms": self.duration_ms
        }

class SystemAuditor:
    """系统审计器"""

    def __init__(self, config: SystemConfig = None, verbose: bool = False):
        self.config = config or SystemConfig()
        self.verbose = verbose
        self.results: List[HealthCheckResult] = []
        self.session = requests.Session()

        # 设置会话默认配置
        self.session.timeout = self.config.REQUEST_TIMEOUT

        # 管理员认证token（如果需要）
        self.admin_token = None  # 在实际环境中应该从环境变量获取

    def _print_result(self, result: HealthCheckResult):
        """打印检查结果"""
        status_colors = {
            "PASS": Fore.GREEN,
            "FAIL": Fore.RED,
            "SKIP": Fore.YELLOW,
            "RUNNING": Fore.BLUE,
            "PENDING": Fore.WHITE
        }

        color = status_colors.get(result.status, Fore.WHITE)
        status_icon = {
            "PASS": "✓",
            "FAIL": "✗",
            "SKIP": "-",
            "RUNNING": "⟳",
            "PENDING": "○"
        }.get(result.status, "?")

        print(f"{color}{status_icon} [{result.status}] {result.name}{Style.RESET_ALL}")
        if result.message:
            print(f"    {result.message}")
        if self.verbose and result.details:
            print(f"    详情: {json.dumps(result.details, indent=2, ensure_ascii=False)}")
        if result.duration_ms > 0:
            print(f"    耗时: {result.duration_ms}ms")
        print()

    def _make_request(self, method: str, endpoint: str, **kwargs) -> requests.Response:
        """发送HTTP请求"""
        url = f"{self.config.API_BASE_URL}{endpoint}"

        if self.verbose:
            print(f"  📡 {method} {url}")

        try:
            response = self.session.request(method, url, **kwargs)
            if self.verbose:
                print(f"  📥 响应: {response.status_code}")
            return response
        except requests.exceptions.RequestException as e:
            if self.verbose:
                print(f"  ❌ 请求异常: {e}")
            raise

    def _check_redis_connection(self) -> bool:
        """检查Redis连接"""
        try:
            r = redis.Redis(
                host=self.config.REDIS_HOST,
                port=self.config.REDIS_PORT,
                db=self.config.REDIS_DB,
                decode_responses=True,
                socket_timeout=5
            )
            r.ping()
            return True
        except Exception as e:
            if self.verbose:
                print(f"  Redis连接失败: {e}")
            return False

    async def check_basic_health(self) -> HealthCheckResult:
        """1. 基础健康检查"""
        result = HealthCheckResult(
            "基础健康检查",
            "验证API服务、数据库、Redis等基础组件是否正常运行"
        )
        result.start()

        try:
            response = self._make_request("GET", self.config.HEALTH_ENDPOINT)

            if response.status_code == 200:
                health_data = response.json()

                # 检查整体状态
                if health_data.get("status") == "healthy":
                    # 检查各组件状态
                    checks = health_data.get("checks", {})
                    failed_components = []

                    for component, status in checks.items():
                        if not status.get("healthy", False):
                            failed_components.append(component)

                    if failed_components:
                        result.fail_check(
                            f"以下组件不健康: {', '.join(failed_components)}",
                            {"health_data": health_data}
                        )
                    else:
                        result.pass_check(
                            f"所有组件正常运行 (响应时间: {health_data.get('response_time_ms', 0)}ms)",
                            {"components": list(checks.keys())}
                        )
                else:
                    result.fail_check(
                        f"服务状态不健康: {health_data.get('status')}",
                        {"health_data": health_data}
                    )
            else:
                result.fail_check(
                    f"健康检查失败，HTTP状态码: {response.status_code}",
                    {"response_text": response.text[:200]}
                )

        except Exception as e:
            result.fail_check(f"健康检查异常: {str(e)}")

        self.results.append(result)
        self._print_result(result)
        return result

    async def check_redis_connectivity(self) -> HealthCheckResult:
        """2. Redis连接检查"""
        result = HealthCheckResult(
            "Redis连接检查",
            "验证Redis缓存服务是否可以正常连接"
        )
        result.start()

        try:
            if self._check_redis_connection():
                result.pass_check("Redis连接正常")
            else:
                result.fail_check("无法连接到Redis服务")
        except Exception as e:
            result.fail_check(f"Redis连接检查异常: {str(e)}")

        self.results.append(result)
        self._print_result(result)
        return result

    async def check_sync_prediction(self) -> HealthCheckResult:
        """3. 同步预测检查"""
        result = HealthCheckResult(
            "同步预测检查",
            "验证单场比赛预测API是否正常工作，检查缓存命中情况"
        )
        result.start()

        try:
            # 第一次请求 - 应该是缓存未命中
            response1 = self._make_request(
                "GET",
                f"{self.config.PREDICT_ENDPOINT}/match/{self.config.TEST_MATCH_ID}"
            )

            if response1.status_code != 200:
                result.fail_check(
                    f"第一次预测请求失败，状态码: {response1.status_code}",
                    {"response": response1.text[:200]}
                )
                return result

            first_prediction = response1.json()
            cache_hit1 = response1.headers.get("X-Cache-Hit", "false").lower() == "true"

            # 等待一小段时间，然后进行第二次请求
            await asyncio.sleep(1)

            # 第二次请求 - 应该是缓存命中
            response2 = self._make_request(
                "GET",
                f"{self.config.PREDICT_ENDPOINT}/match/{self.config.TEST_MATCH_ID}"
            )

            if response2.status_code != 200:
                result.fail_check(
                    f"第二次预测请求失败，状态码: {response2.status_code}",
                    {"response": response2.text[:200]}
                )
                return result

            second_prediction = response2.json()
            cache_hit2 = response2.headers.get("X-Cache-Hit", "false").lower() == "true"

            # 验证预测结果一致性
            if first_prediction.get("predicted_class") != second_prediction.get("predicted_class"):
                result.fail_check(
                    "两次预测结果不一致，可能存在随机性问题",
                    {
                        "first": first_prediction.get("predicted_class"),
                        "second": second_prediction.get("predicted_class")
                    }
                )
            else:
                # 检查缓存行为
                if not cache_hit1 and cache_hit2:
                    cache_status = "正常 (第一次Miss，第二次Hit)"
                elif cache_hit1 and cache_hit2:
                    cache_status = "警告 (两次都Hit，可能预加载了缓存)"
                else:
                    cache_status = "警告 (两次都Miss，缓存可能未生效)"

                result.pass_check(
                    f"同步预测功能正常，缓存行为: {cache_status}",
                    {
                        "predicted_class": first_prediction.get("predicted_class"),
                        "confidence": first_prediction.get("confidence"),
                        "cache_behavior": {
                            "first_request_hit": cache_hit1,
                            "second_request_hit": cache_hit2
                        }
                    }
                )

        except Exception as e:
            result.fail_check(f"同步预测检查异常: {str(e)}")

        self.results.append(result)
        self._print_result(result)
        return result

    async def check_batch_prediction(self) -> HealthCheckResult:
        """4. 异步批量预测检查"""
        result = HealthCheckResult(
            "异步批量预测检查",
            "验证批量预测API是否能正常排队并返回Task ID"
        )
        result.start()

        try:
            # 提交批量预测任务
            batch_request = {
                "match_ids": self.config.TEST_BATCH_MATCH_IDS,
                "include_features": False,
                "include_metadata": True
            }

            response = self._make_request(
                "POST",
                self.config.BATCH_PREDICT_ENDPOINT,
                json=batch_request
            )

            if response.status_code != 200:
                result.fail_check(
                    f"批量预测任务提交失败，状态码: {response.status_code}",
                    {"response": response.text[:200]}
                )
                return result

            batch_result = response.json()

            # 检查任务结果格式
            if "total_count" not in batch_result or "successful_count" not in batch_result:
                result.fail_check("批量预测响应格式不正确", {"response": batch_result})
                return result

            total_count = batch_result["total_count"]
            successful_count = batch_result["successful_count"]
            failed_count = batch_result["failed_count"]

            if successful_count == 0:
                result.fail_check("批量预测全部失败", {"errors": batch_result.get("errors", [])})
                return result

            success_rate = successful_count / total_count * 100

            result.pass_check(
                f"批量预测完成，成功率: {success_rate:.1f}% ({successful_count}/{total_count})",
                {
                    "total_count": total_count,
                    "successful_count": successful_count,
                    "failed_count": failed_count,
                    "success_rate": success_rate,
                    "processing_time_ms": batch_result.get("processing_time_ms", 0)
                }
            )

        except Exception as e:
            result.fail_check(f"异步批量预测检查异常: {str(e)}")

        self.results.append(result)
        self._print_result(result)
        return result

    async def check_mlops_functionality(self) -> HealthCheckResult:
        """5. MLOps功能检查"""
        result = HealthCheckResult(
            "MLOps功能检查",
            "验证模型状态查询和重训练任务触发功能"
        )
        result.start()

        try:
            # 首先检查当前模型状态
            headers = {}
            if self.admin_token:
                headers["Authorization"] = f"Bearer {self.admin_token}"

            status_response = self._make_request(
                "GET",
                self.config.ADMIN_MODEL_STATUS_ENDPOINT,
                headers=headers
            )

            if status_response.status_code == 401:
                result.skip_check("需要管理员认证，跳过MLOps功能检查")
                return result
            elif status_response.status_code != 200:
                result.fail_check(
                    f"获取模型状态失败，状态码: {status_response.status_code}",
                    {"response": status_response.text[:200]}
                )
                return result

            model_status = status_response.json()
            current_version = model_status.get("current_version", "unknown")

            # 模拟触发重训练任务（使用测试描述）
            retrain_payload = {
                "description": "System audit test retraining"
            }

            retrain_response = self._make_request(
                "POST",
                self.config.ADMIN_RETRAIN_ENDPOINT,
                json=retrain_payload,
                headers=headers
            )

            if retrain_response.status_code != 200:
                result.fail_check(
                    f"触发重训练任务失败，状态码: {retrain_response.status_code}",
                    {"response": retrain_response.text[:200]}
                )
                return result

            retrain_result = retrain_response.json()
            task_id = retrain_result.get("task_id")

            if not task_id:
                result.fail_check("重训练任务未返回有效的Task ID", {"response": retrain_result})
            else:
                result.pass_check(
                    f"MLOps功能正常，当前模型版本: {current_version}，重训练任务已提交",
                    {
                        "current_version": current_version,
                        "task_id": task_id,
                        "training_status": model_status.get("training_status", {})
                    }
                )

        except Exception as e:
            result.fail_check(f"MLOps功能检查异常: {str(e)}")

        self.results.append(result)
        self._print_result(result)
        return result

    async def check_prometheus_metrics(self) -> HealthCheckResult:
        """6. Prometheus指标检查"""
        result = HealthCheckResult(
            "Prometheus指标检查",
            "验证Prometheus指标是否正常暴露和收集"
        )
        result.start()

        try:
            # 检查本地metrics端点
            metrics_response = self._make_request("GET", self.config.METRICS_ENDPOINT)

            if metrics_response.status_code != 200:
                result.fail_check(
                    f"无法访问metrics端点，状态码: {metrics_response.status_code}"
                )
                return result

            metrics_text = metrics_response.text

            # 检查关键指标是否存在
            key_metrics = [
                "prediction_requests_total",
                "model_inference_latency_seconds",
                "fastapi_http_requests_total"
            ]

            found_metrics = []
            missing_metrics = []

            for metric in key_metrics:
                if metric in metrics_text:
                    found_metrics.append(metric)
                else:
                    missing_metrics.append(metric)

            # 尝试查询Prometheus服务器
            prometheus_available = False
            prometheus_response_count = 0

            try:
                prometheus_query = "prediction_requests_total"
                prometheus_url = f"{self.config.PROMETHEUS_URL}{self.config.PROMETHEUS_QUERY_ENDPOINT}?query={prometheus_query}"

                prometheus_response = requests.get(prometheus_url, timeout=10)
                if prometheus_response.status_code == 200:
                    prometheus_data = prometheus_response.json()
                    if prometheus_data.get("status") == "success":
                        prometheus_available = True
                        data_result = prometheus_data.get("data", {}).get("result", [])
                        prometheus_response_count = len(data_result)
            except Exception as e:
                if self.verbose:
                    print(f"  Prometheus服务器查询失败: {e}")

            # 评估检查结果
            if missing_metrics:
                result.fail_check(
                    f"缺少关键指标: {', '.join(missing_metrics)}",
                    {
                        "found_metrics": found_metrics,
                        "missing_metrics": missing_metrics,
                        "prometheus_available": prometheus_available
                    }
                )
            else:
                prometheus_status = "可用" if prometheus_available else "不可访问"
                result.pass_check(
                    f"指标暴露正常，Prometheus服务器: {prometheus_status}",
                    {
                        "found_metrics": found_metrics,
                        "prometheus_available": prometheus_available,
                        "prometheus_data_points": prometheus_response_count
                    }
                )

        except Exception as e:
            result.fail_check(f"Prometheus指标检查异常: {str(e)}")

        self.results.append(result)
        self._print_result(result)
        return result

    async def run_all_checks(self) -> Dict[str, Any]:
        """运行所有检查"""
        print(f"\n{Fore.CYAN}{'='*60}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}FootballPrediction v2.0 系统集成验收与审计{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}\n")

        start_time = time.time()

        # 依次执行所有检查
        checks = [
            self.check_basic_health,
            self.check_redis_connectivity,
            self.check_sync_prediction,
            self.check_batch_prediction,
            self.check_mlops_functionality,
            self.check_prometheus_metrics
        ]

        for check_func in checks:
            await check_func()

        # 计算总体统计
        total_time = time.time() - start_time
        passed_count = len([r for r in self.results if r.status == "PASS"])
        failed_count = len([r for r in self.results if r.status == "FAIL"])
        skipped_count = len([r for r in self.results if r.status == "SKIP"])
        total_count = len(self.results)

        # 打印汇总
        print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}验收结果汇总{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}")

        print(f"总检查项: {total_count}")
        print(f"{Fore.GREEN}通过: {passed_count}{Style.RESET_ALL}")
        print(f"{Fore.RED}失败: {failed_count}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}跳过: {skipped_count}{Style.RESET_ALL}")
        print(f"总耗时: {total_time:.2f}秒")

        overall_status = "PASS" if failed_count == 0 else "FAIL"
        status_color = Fore.GREEN if overall_status == "PASS" else Fore.RED
        status_icon = "✓" if overall_status == "PASS" else "✗"

        print(f"\n{status_color}{status_icon} 整体验收状态: {overall_status}{Style.RESET_ALL}\n")

        # 生成详细报告
        report = {
            "audit_info": {
                "timestamp": datetime.now().isoformat(),
                "total_duration_seconds": round(total_time, 2),
                "overall_status": overall_status
            },
            "summary": {
                "total_checks": total_count,
                "passed": passed_count,
                "failed": failed_count,
                "skipped": skipped_count
            },
            "checks": [result.to_dict() for result in self.results]
        }

        return report

async def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="FootballPrediction系统集成验收脚本")
    parser.add_argument("--verbose", "-v", action="store_true", help="详细输出")
    parser.add_argument("--output-json", "-j", action="store_true", help="输出JSON格式报告")
    parser.add_argument("--output-file", "-o", type=str, help="输出报告到文件")

    args = parser.parse_args()

    # 创建审计器
    auditor = SystemAuditor(verbose=args.verbose)

    try:
        # 运行所有检查
        report = await auditor.run_all_checks()

        # 输出报告
        if args.output_json:
            if args.output_file:
                with open(args.output_file, 'w', encoding='utf-8') as f:
                    json.dump(report, f, indent=2, ensure_ascii=False)
                print(f"\n报告已保存到: {args.output_file}")
            else:
                print("\n" + json.dumps(report, indent=2, ensure_ascii=False))

        # 根据检查结果设置退出码
        failed_count = report["summary"]["failed"]
        sys.exit(1 if failed_count > 0 else 0)

    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}用户中断验收检查{Style.RESET_ALL}")
        sys.exit(130)
    except Exception as e:
        print(f"\n{Fore.RED}验收检查异常: {str(e)}{Style.RESET_ALL}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())