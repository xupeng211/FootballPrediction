#!/usr/bin/env python3
"""
性能测试运行脚本
使用Locust进行API性能测试
"""

import subprocess
import time
import json
import logging
from pathlib import Path

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class PerformanceTestRunner:
    """性能测试运行器"""

    def __init__(self):
        self.results = {}
        self.start_time = time.time()

    def run_locust_test(self, host_url, users, spawn_rate, duration, test_name):
        """运行Locust性能测试"""
        logger.info(f"🚀 Starting {test_name} with {users} users for {duration}s")

        cmd = [
            'locust',
            '--host', host_url,
            '--users', str(users),
            '--spawn-rate', str(spawn_rate),
            '--run-time', f'{duration}s',
            '--headless',
            '--csv', f'reports/{test_name}_results',
            '--html', f'reports/{test_name}_report.html'
        ]

        try:
            # 创建报告目录
            Path('reports').mkdir(exist_ok=True)

            # 运行测试
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=duration + 60  # 额外60秒超时缓冲
            )

            if result.returncode == 0:
                logger.info(f"✅ {test_name} completed successfully")
                self.results[test_name] = {
                    'status': 'success',
                    'users': users,
                    'duration': duration,
                    'output': result.stdout
                }
            else:
                logger.error(f"❌ {test_name} failed: {result.stderr}")
                self.results[test_name] = {
                    'status': 'failed',
                    'error': result.stderr,
                    'return_code': result.returncode
                }

        except subprocess.TimeoutExpired:
            logger.error(f"❌ {test_name} timed out")
            self.results[test_name] = {
                'status': 'timeout',
                'error': 'Test timed out'
            }
        except Exception as e:
            logger.error(f"❌ {test_name} failed with exception: {e}")
            self.results[test_name] = {
                'status': 'error',
                'error': str(e)
            }

    def run_performance_tests(self):
        """运行所有性能测试"""
        host_url = "http://localhost:8000"

        # 测试场景配置
        test_scenarios = [
            {
                'name': 'smoke_test',
                'users': 10,
                'spawn_rate': 2,
                'duration': 30
            },
            {
                'name': 'load_test',
                'users': 50,
                'spawn_rate': 5,
                'duration': 60
            },
            {
                'name': 'stress_test',
                'users': 100,
                'spawn_rate': 10,
                'duration': 120
            },
            {
                'name': 'spike_test',
                'users': 200,
                'spawn_rate': 20,
                'duration': 60
            }
        ]

        logger.info("🚀 Starting comprehensive performance tests...")

        for scenario in test_scenarios:
            self.run_locust_test(
                host_url=host_url,
                users=scenario['users'],
                spawn_rate=scenario['spawn_rate'],
                duration=scenario['duration'],
                test_name=scenario['name']
            )

            # 测试间等待
            time.sleep(10)

        self.generate_summary_report()

    def generate_summary_report(self):
        """生成性能测试总结报告"""
        logger.info("\n" + "="*60)
        logger.info("📊 Performance Test Summary")
        logger.info("="*60)

        successful_tests = [name for name, result in self.results.items() if result['status'] == 'success']
        failed_tests = [name for name, result in self.results.items() if result['status'] != 'success']

        logger.info(f"✅ Successful tests: {len(successful_tests)}/{len(self.results)}")
        logger.info(f"❌ Failed tests: {len(failed_tests)}/{len(self.results)}")

        for test_name, result in self.results.items():
            status = result['status']
            if status == 'success':
                users = result['users']
                duration = result['duration']
                logger.info(f"✅ {test_name}: {users} users, {duration}s")
            else:
                error = result.get('error', 'Unknown error')
                logger.error(f"❌ {test_name}: {error}")

        # 保存结果到JSON文件
        with open('reports/performance_test_summary.json', 'w', encoding='utf-8') as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False)

        logger.info(f"\n📄 Detailed reports saved to 'reports/' directory")
        logger.info(f"📄 Summary saved to 'reports/performance_test_summary.json'")

        total_time = time.time() - self.start_time
        logger.info(f"\n⏱️  Total test time: {total_time:.1f}s")

    def check_service_availability(self):
        """检查服务可用性"""
        logger.info("🔍 Checking service availability...")

        try:
            import requests
            response = requests.get("http://localhost:8000/health", timeout=5)
            if response.status_code == 200:
                logger.info("✅ Service is available for performance testing")
                return True
            else:
                logger.error(f"❌ Service returned status {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"❌ Service not available: {e}")
            return False


def main():
    """主函数"""
    runner = PerformanceTestRunner()

    # 检查服务可用性
    if not runner.check_service_availability():
        logger.error("❌ Service not available, cannot run performance tests")
        return 1

    # 运行性能测试
    runner.run_performance_tests()

    # 判断总体结果
    successful_count = sum(1 for result in runner.results.values() if result['status'] == 'success')
    total_count = len(runner.results)

    if successful_count >= total_count * 0.75:  # 75%以上测试成功
        logger.info("🎉 Performance tests completed successfully!")
        return 0
    else:
        logger.error("❌ Too many performance tests failed")
        return 1


if __name__ == "__main__":
    try:
        exit_code = main()
        exit(exit_code)
    except KeyboardInterrupt:
        logger.info("Performance test interrupted")
        exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        exit(1)