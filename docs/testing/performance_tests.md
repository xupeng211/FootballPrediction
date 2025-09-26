# 性能测试方案

本文档详细说明足球预测系统的性能测试策略，包括Locust性能测试、API基准测试、数据库性能优化等。

## 📋 目录

- [性能测试概述](#性能测试概述)
  - [测试目标](#测试目标)
  - [测试环境](#测试环境)
  - [性能指标](#性能指标)
- [Locust性能测试](#locust性能测试)
  - [基础配置](#基础配置)
  - [测试场景](#测试场景)
  - [测试执行](#测试执行)
- [API基准测试](#api基准测试)
  - [HTTP性能测试](#http性能测试)
  - [WebSocket性能测试](#websocket性能测试)
  - [GraphQL性能测试](#graphql性能测试)
- [数据库性能测试](#数据库性能测试)
  - [查询性能优化](#查询性能优化)
  - [连接池优化](#连接池优化)
  - [索引优化](#索引优化)
- [应用性能测试](#应用性能测试)
  - [内存使用测试](#内存使用测试)
  - [CPU使用测试](#cpu使用测试)
  - [响应时间测试](#响应时间测试)
- [监控与分析](#监控与分析)
  - [性能监控](#性能监控)
  - [瓶颈分析](#瓶颈分析)
  - [优化建议](#优化建议)

---

## 性能测试概述

### 测试目标

足球预测系统性能测试的主要目标包括：

1. **响应时间目标**
   - API平均响应时间 < 200ms
   - 95%请求响应时间 < 500ms
   - 99%请求响应时间 < 1000ms

2. **吞吐量目标**
   - 支持1000并发用户
   - 处理10000 RPS (Requests Per Second)
   - 数据库查询 < 100ms

3. **资源利用目标**
   - CPU使用率 < 70%
   - 内存使用率 < 80%
   - 数据库连接池使用率 < 80%

4. **稳定性目标**
   - 24小时持续运行无内存泄漏
   - 错误率 < 0.1%
   - 系统可用性 > 99.9%

### 测试环境

**生产环境规格**:
- **应用服务器**: 4核8GB内存
- **数据库服务器**: 8核16GB内存，SSD存储
- **缓存服务器**: 4核8GB内存Redis
- **负载均衡器**: Nginx
- **监控**: Prometheus + Grafana

**测试环境规格**:
- **应用服务器**: 2核4GB内存
- **数据库服务器**: 4核8GB内存
- **缓存服务器**: 2核4GB内存Redis

### 性能指标

**关键性能指标 (KPI)**:
- **响应时间**: 平均、中位数、95百分位、99百分位
- **吞吐量**: RPS (每秒请求数)、并发用户数
- **错误率**: HTTP错误率、业务错误率
- **资源利用率**: CPU、内存、磁盘I/O、网络I/O
- **数据库性能**: 查询时间、连接数、锁等待时间

**监控指标**:
- 应用指标: 请求计数、响应时间、错误率
- 系统指标: CPU、内存、磁盘、网络
- 数据库指标: 查询性能、连接池状态
- 缓存指标: 命中率、内存使用、连接数

---

## Locust性能测试

### 基础配置

```python
# locustfile.py
import random
import json
import time
from locust import HttpUser, task, between, events
from locust.env import Environment
from locust.stats import stats_history, stats_printer
from locust.log import setup_logging
import gevent

class FootballPredictionUser(HttpUser):
    """足球预测系统用户模拟"""

    wait_time = between(1, 3)  # 请求间隔1-3秒
    weight = 1  # 用户权重

    def on_start(self):
        """用户开始前的初始化操作"""
        self.headers = {
            'Content-Type': 'application/json',
            'User-Agent': 'Locust-Performance-Test'
        }
        self.test_matches = [1, 2, 3, 4, 5]  # 测试比赛ID
        self.test_teams = [101, 102, 103, 104, 105]  # 测试队伍ID

    @task(20)
    def health_check(self):
        """健康检查 (20%概率)"""
        with self.client.get("/health", headers=self.headers, catch_response=True) as response:
            if response.status_code != 200:
                response.failure(f"Health check failed: {response.status_code}")
            else:
                response.success()

    @task(30)
    def get_matches(self):
        """获取比赛列表 (30%概率)"""
        params = {
            'page': random.randint(1, 10),
            'per_page': random.choice([10, 20, 50]),
            'status': random.choice(['SCHEDULED', 'FINISHED', 'IN_PLAY'])
        }

        with self.client.get("/api/v1/data/matches", params=params, headers=self.headers, catch_response=True) as response:
            if response.status_code != 200:
                response.failure(f"Get matches failed: {response.status_code}")
            else:
                response.success()

    @task(25)
    def get_match_details(self):
        """获取比赛详情 (25%概率)"""
        match_id = random.choice(self.test_matches)

        with self.client.get(f"/api/v1/data/matches/{match_id}", headers=self.headers, catch_response=True) as response:
            if response.status_code != 200:
                response.failure(f"Get match details failed: {response.status_code}")
            else:
                response.success()

    @task(15)
    def get_predictions(self):
        """获取预测结果 (15%概率)"""
        match_id = random.choice(self.test_matches)

        with self.client.get(f"/api/v1/predictions/match/{match_id}", headers=self.headers, catch_response=True) as response:
            if response.status_code != 200:
                response.failure(f"Get predictions failed: {response.status_code}")
            else:
                response.success()

    @task(10)
    def submit_prediction_request(self):
        """提交预测请求 (10%概率)"""
        match_id = random.choice(self.test_matches)
        payload = {
            "match_id": match_id,
            "features": {
                "home_form": random.uniform(0.5, 1.0),
                "away_form": random.uniform(0.5, 1.0),
                "head_to_head": random.uniform(0.3, 0.7),
                "team_strength": random.uniform(0.4, 0.9)
            }
        }

        with self.client.post("/api/v1/predictions", json=payload, headers=self.headers, catch_response=True) as response:
            if response.status_code not in [200, 201]:
                response.failure(f"Submit prediction failed: {response.status_code}")
            else:
                response.success()

class HeavyUser(HttpUser):
    """重负载用户模拟"""

    wait_time = between(0.1, 0.5)  # 短间隔，高频率请求
    weight = 3  # 更多的此类用户

    def on_start(self):
        """初始化"""
        self.headers = {
            'Content-Type': 'application/json',
            'User-Agent': 'Locust-Heavy-User'
        }

    @task(40)
    def intensive_prediction(self):
        """密集预测请求"""
        payload = {
            "match_id": random.randint(1, 100),
            "features": {
                "home_form": random.uniform(0, 1),
                "away_form": random.uniform(0, 1),
                "head_to_head": random.uniform(0, 1),
                "team_strength": random.uniform(0, 1),
                "historical_data": [random.uniform(0, 1) for _ in range(10)]
            }
        }

        with self.client.post("/api/v1/predictions/batch", json=payload, headers=self.headers, catch_response=True) as response:
            if response.status_code not in [200, 201]:
                response.failure(f"Batch prediction failed: {response.status_code}")
            else:
                response.success()

    @task(30)
    def data_analysis(self):
        """数据分析请求"""
        with self.client.get("/api/v1/analytics/performance", headers=self.headers, catch_response=True) as response:
            if response.status_code != 200:
                response.failure(f"Data analysis failed: {response.status_code}")
            else:
                response.success()

    @task(20)
    def real_time_updates(self):
        """实时更新请求"""
        match_id = random.randint(1, 100)
        with self.client.get(f"/api/v1/streaming/match/{match_id}", headers=self.headers, catch_response=True) as response:
            if response.status_code != 200:
                response.failure(f"Real-time updates failed: {response.status_code}")
            else:
                response.success()

    @task(10)
    def complex_query(self):
        """复杂查询请求"""
        params = {
            'start_date': '2023-01-01',
            'end_date': '2023-12-31',
            'competition': random.choice(['Premier League', 'Championship', 'League One']),
            'team_performance': True,
            'include_predictions': True
        }

        with self.client.get("/api/v1/analytics/comprehensive", params=params, headers=self.headers, catch_response=True) as response:
            if response.status_code != 200:
                response.failure(f"Complex query failed: {response.status_code}")
            else:
                response.success()

# 自定义事件监听器
@events.init_command_line_parser.add_listener
def _(parser):
    parser.add_argument("--test-duration", type=int, default=60, help="Test duration in seconds")
    parser.add_argument("--ramp-up", type=int, default=10, help="Ramp up time in seconds")
    parser.add_argument("--users", type=int, default=100, help="Number of users to simulate")

@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """测试开始时的处理"""
    print("=== Performance Test Started ===")
    print(f"Target: {environment.host}")
    print(f"Users: {environment.parsed_options.users}")
    print(f"Duration: {environment.parsed_options.test_duration}s")
    print(f"Ramp up: {environment.parsed_options.ramp_up}s")

@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """测试结束时的处理"""
    print("=== Performance Test Completed ===")

    # 生成详细报告
    stats = environment.stats
    print(f"Total requests: {stats.total.num_requests}")
    print(f"Total failures: {stats.total.num_failures}")
    print(f"Failure rate: {(stats.total.num_failures / stats.total.num_requests * 100):.2f}%")
    print(f"Average response time: {stats.total.avg_response_time:.2f}ms")
    print(f"Median response time: {stats.total.median_response_time:.2f}ms")
    print(f"95th percentile: {stats.total.get_response_time_percentile(0.95):.2f}ms")
    print(f"99th percentile: {stats.total.get_response_time_percentile(0.99):.2f}ms")

@events.request.add_listener
def on_request(request_type, name, response_time, response_length, response, context, exception, **kwargs):
    """请求事件监听器"""
    if exception:
        print(f"Request failed: {name} - {exception}")
    else:
        if response_time > 1000:  # 记录慢请求
            print(f"Slow request: {name} - {response_time:.2f}ms")

if __name__ == "__main__":
    # 设置日志
    setup_logging("INFO", None)

    # 创建环境
    env = Environment(user_classes=[FootballPredictionUser, HeavyUser])

    # 启动性能测试
    env.create_local_runner()

    # 启动Web界面
    env.create_web_ui("127.0.0.1", 8089)

    # 启动统计打印
    gevent.spawn(stats_printer(env.stats))

    # 等待测试完成
    gevent.spawn_later(env.parsed_options.test_duration, lambda: env.quit())

    # 运行测试
    env.runner.greenlet.join()
```

### 测试场景

```python
# test_scenarios.py
import json
import random
from datetime import datetime, timedelta
from locust import HttpUser, task, between, events

class NormalLoadScenario(HttpUser):
    """正常负载场景"""

    wait_time = between(2, 5)
    weight = 1

    def on_start(self):
        """初始化用户数据"""
        self.user_id = random.randint(1000, 9999)
        self.session_id = f"session_{self.user_id}_{int(time.time())}"
        self.headers = {
            'Content-Type': 'application/json',
            'X-User-ID': str(self.user_id),
            'X-Session-ID': self.session_id
        }

    @task(25)
    def browse_matches(self):
        """浏览比赛"""
        with self.client.get("/api/v1/data/matches", headers=self.headers) as response:
            if response.status_code == 200:
                data = response.json()
                # 缓存一些比赛ID供后续使用
                if 'matches' in data:
                    self.recent_matches = [match['id'] for match in data['matches'][:5]]

    @task(20)
    def view_team_stats(self):
        """查看队伍统计"""
        team_id = random.randint(1, 100)
        with self.client.get(f"/api/v1/data/teams/{team_id}/stats", headers=self.headers) as response:
            pass

    @task(15)
    def get_prediction(self):
        """获取预测"""
        if hasattr(self, 'recent_matches'):
            match_id = random.choice(self.recent_matches)
            with self.client.get(f"/api/v1/predictions/match/{match_id}", headers=self.headers) as response:
                pass

    @task(10)
    def check_league_table(self):
        """查看联赛积分榜"""
        competition_id = random.choice([39, 40, 41])  # Premier League, Championship, League One
        with self.client.get(f"/api/v1/data/competitions/{competition_id}/standings", headers=self.headers) as response:
            pass

    @task(5)
    def submit_feedback(self):
        """提交反馈"""
        feedback_data = {
            "rating": random.randint(1, 5),
            "comment": "Performance test feedback",
            "timestamp": datetime.now().isoformat()
        }
        with self.client.post("/api/v1/feedback", json=feedback_data, headers=self.headers) as response:
            pass

class PeakLoadScenario(HttpUser):
    """峰值负载场景"""

    wait_time = between(0.5, 2)
    weight = 2

    def on_start(self):
        """初始化"""
        self.user_id = random.randint(1000, 9999)
        self.headers = {
            'Content-Type': 'application/json',
            'X-User-ID': str(self.user_id)
        }

    @task(40)
    def rapid_predictions(self):
        """快速预测请求"""
        matches = list(range(1, 50))
        random.shuffle(matches)

        for match_id in matches[:10]:  # 批量请求10个比赛
            payload = {
                "match_id": match_id,
                "features": {
                    "home_form": random.uniform(0, 1),
                    "away_form": random.uniform(0, 1),
                    "head_to_head": random.uniform(0, 1)
                }
            }

            with self.client.post("/api/v1/predictions", json=payload, headers=self.headers) as response:
                pass

    @task(30)
    def batch_predictions(self):
        """批量预测"""
        payload = {
            "matches": [
                {
                    "match_id": i,
                    "features": {
                        "home_form": random.uniform(0, 1),
                        "away_form": random.uniform(0, 1)
                    }
                }
                for i in range(1, 21)  # 20场比赛
            ]
        }

        with self.client.post("/api/v1/predictions/batch", json=payload, headers=self.headers) as response:
            pass

    @task(20)
    def real_time_updates(self):
        """实时更新"""
        match_id = random.randint(1, 50)
        with self.client.get(f"/api/v1/streaming/match/{match_id}/live", headers=self.headers) as response:
            pass

    @task(10)
    def historical_analysis(self):
        """历史分析"""
        params = {
            "start_date": (datetime.now() - timedelta(days=30)).isoformat(),
            "end_date": datetime.now().isoformat(),
            "metrics": ["accuracy", "profit", "win_rate"]
        }

        with self.client.get("/api/v1/analytics/historical", params=params, headers=self.headers) as response:
            pass

class StressTestScenario(HttpUser):
    """压力测试场景"""

    wait_time = between(0.1, 1)
    weight = 1

    def on_start(self):
        """初始化"""
        self.user_id = random.randint(1000, 9999)
        self.headers = {
            'Content-Type': 'application/json',
            'X-User-ID': str(self.user_id)
        }

    @task(50)
    def intensive_computations(self):
        """密集计算请求"""
        payload = {
            "model_type": random.choice(["xgboost", "neural_network", "ensemble"]),
            "features": {
                f"feature_{i}": random.uniform(0, 1) for i in range(100)  # 100个特征
            },
            "iterations": random.randint(100, 1000)
        }

        with self.client.post("/api/v1/models/compute", json=payload, headers=self.headers) as response:
            pass

    @task(30)
    def large_data_requests(self):
        """大数据请求"""
        with self.client.get("/api/v1/data/export", params={
            "format": "json",
            "include_history": True,
            "include_predictions": True,
            "include_statistics": True
        }, headers=self.headers) as response:
            pass

    @task(20)
    def concurrent_operations(self):
        """并发操作"""
        import gevent

        def make_request():
            match_id = random.randint(1, 100)
            with self.client.get(f"/api/v1/data/matches/{match_id}", headers=self.headers) as response:
                return response

        # 并发执行多个请求
        requests = [gevent.spawn(make_request) for _ in range(5)]
        gevent.joinall(requests, timeout=10)
```

### 测试执行

```python
# run_performance_tests.py
import os
import sys
import time
import json
import subprocess
from datetime import datetime
import argparse
from locust.main import main as locust_main

class PerformanceTestRunner:
    """性能测试运行器"""

    def __init__(self, config_file="performance_config.json"):
        self.config = self.load_config(config_file)
        self.results_dir = "performance_results"
        self.ensure_results_dir()

    def load_config(self, config_file):
        """加载配置文件"""
        try:
            with open(config_file, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"Config file {config_file} not found, using defaults")
            return self.get_default_config()

    def get_default_config(self):
        """获取默认配置"""
        return {
            "tests": [
                {
                    "name": "baseline_test",
                    "users": 50,
                    "spawn_rate": 5,
                    "duration": 300,
                    "scenario": "NormalLoadScenario"
                },
                {
                    "name": "peak_load_test",
                    "users": 500,
                    "spawn_rate": 50,
                    "duration": 600,
                    "scenario": "PeakLoadScenario"
                },
                {
                    "name": "stress_test",
                    "users": 1000,
                    "spawn_rate": 100,
                    "duration": 300,
                    "scenario": "StressTestScenario"
                }
            ],
            "target_host": "http://localhost:8000",
            "results_dir": "performance_results"
        }

    def ensure_results_dir(self):
        """确保结果目录存在"""
        os.makedirs(self.results_dir, exist_ok=True)

    def run_single_test(self, test_config):
        """运行单个测试"""
        test_name = test_config['name']
        users = test_config['users']
        spawn_rate = test_config['spawn_rate']
        duration = test_config['duration']
        scenario = test_config['scenario']

        print(f"Running test: {test_name}")
        print(f"Users: {users}")
        print(f"Spawn rate: {spawn_rate}")
        print(f"Duration: {duration}s")
        print(f"Scenario: {scenario}")

        # 准备测试结果文件
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        result_file = os.path.join(self.results_dir, f"{test_name}_{timestamp}.json")
        html_file = os.path.join(self.results_dir, f"{test_name}_{timestamp}.html")

        # 构建Locust命令
        cmd = [
            "locust",
            "-f", "locustfile.py",
            "--host", self.config['target_host'],
            "--users", str(users),
            "--spawn-rate", str(spawn_rate),
            "--run-time", f"{duration}s",
            "--csv", os.path.join(self.results_dir, f"{test_name}_{timestamp}"),
            "--html", html_file,
            "--class", scenario
        ]

        # 设置环境变量
        env = os.environ.copy()
        env['LOCUST_TEST_NAME'] = test_name
        env['LOCUST_RESULT_FILE'] = result_file

        try:
            # 运行测试
            print(f"Starting test: {test_name}")
            start_time = time.time()

            process = subprocess.Popen(cmd, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            stdout, stderr = process.communicate()

            end_time = time.time()
            duration_actual = end_time - start_time

            # 记录结果
            result = {
                "test_name": test_name,
                "config": test_config,
                "start_time": datetime.fromtimestamp(start_time).isoformat(),
                "end_time": datetime.fromtimestamp(end_time).isoformat(),
                "duration": duration_actual,
                "status": "completed" if process.returncode == 0 else "failed",
                "stdout": stdout.decode('utf-8'),
                "stderr": stderr.decode('utf-8')
            }

            with open(result_file, 'w') as f:
                json.dump(result, f, indent=2)

            print(f"Test completed: {test_name}")
            print(f"Duration: {duration_actual:.2f}s")
            print(f"Status: {result['status']}")

            return result

        except Exception as e:
            print(f"Error running test {test_name}: {e}")
            return None

    def run_all_tests(self):
        """运行所有测试"""
        print("Starting performance test suite...")
        results = []

        for test_config in self.config['tests']:
            result = self.run_single_test(test_config)
            if result:
                results.append(result)

        # 生成汇总报告
        self.generate_summary_report(results)

        return results

    def generate_summary_report(self, results):
        """生成汇总报告"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        summary_file = os.path.join(self.results_dir, f"summary_{timestamp}.md")

        with open(summary_file, 'w') as f:
            f.write("# Performance Test Summary\n\n")
            f.write(f"Generated: {datetime.now().isoformat()}\n\n")

            f.write("## Test Results Overview\n\n")
            f.write("| Test Name | Users | Duration | Status | Avg Response Time | Error Rate |\n")
            f.write("|-----------|-------|----------|--------|------------------|------------|\n")

            for result in results:
                test_name = result['test_name']
                users = result['config']['users']
                duration = result['duration']
                status = result['status']

                # 从CSV文件中读取统计信息
                csv_file = os.path.join(self.results_dir, f"{test_name}_{datetime.fromisoformat(result['start_time']).strftime('%Y%m%d_%H%M%S')}_stats.csv")
                avg_response_time = "N/A"
                error_rate = "N/A"

                if os.path.exists(csv_file):
                    try:
                        import pandas as pd
                        df = pd.read_csv(csv_file)
                        if not df.empty:
                            avg_response_time = f"{df['Average Response Time'].iloc[-1]:.2f}ms"
                            error_rate = f"{df['Failure Count'].iloc[-1] / df['Request Count'].iloc[-1] * 100:.2f}%"
                    except Exception as e:
                        print(f"Error reading CSV file {csv_file}: {e}")

                f.write(f"| {test_name} | {users} | {duration:.2f}s | {status} | {avg_response_time} | {error_rate} |\n")

            f.write("\n## Recommendations\n\n")

            # 基于测试结果生成建议
            failed_tests = [r for r in results if r['status'] == 'failed']
            if failed_tests:
                f.write("### Failed Tests\n")
                for test in failed_tests:
                    f.write(f"- {test['test_name']}: Check logs for details\n")

            # 性能建议
            f.write("\n### Performance Optimization Suggestions\n")
            f.write("- Monitor response times for high-latency endpoints\n")
            f.write("- Consider implementing caching for frequently accessed data\n")
            f.write("- Optimize database queries for slow operations\n")
            f.write("- Consider load balancing for high-traffic scenarios\n")

        print(f"Summary report generated: {summary_file}")

    def run_comparison_test(self, base_config, new_config):
        """运行对比测试"""
        print("Running comparison test...")

        # 运行基线测试
        print("Running baseline test...")
        base_results = self.run_single_test(base_config)

        # 等待系统恢复
        time.sleep(60)

        # 运行新配置测试
        print("Running new configuration test...")
        new_results = self.run_single_test(new_config)

        # 生成对比报告
        self.generate_comparison_report(base_results, new_results)

        return base_results, new_results

    def generate_comparison_report(self, base_results, new_results):
        """生成对比报告"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        comparison_file = os.path.join(self.results_dir, f"comparison_{timestamp}.md")

        with open(comparison_file, 'w') as f:
            f.write("# Performance Comparison Report\n\n")
            f.write(f"Generated: {datetime.now().isoformat()}\n\n")

            f.write("## Test Configuration Comparison\n\n")
            f.write("| Metric | Baseline | New Configuration | Change |\n")
            f.write("|--------|----------|-------------------|--------|\n")
            f.write(f"| Users | {base_results['config']['users']} | {new_results['config']['users']} | - |\n")
            f.write(f"| Duration | {base_results['duration']:.2f}s | {new_results['duration']:.2f}s | {(new_results['duration'] - base_results['duration']):+.2f}s |\n")

            # 读取详细的性能数据进行对比
            f.write("\n## Performance Metrics Comparison\n\n")

            # 这里可以添加更详细的性能对比逻辑
            f.write("Detailed performance comparison would be implemented here...\n")

        print(f"Comparison report generated: {comparison_file}")

def main():
    parser = argparse.ArgumentParser(description='Run performance tests')
    parser.add_argument('--config', default='performance_config.json', help='Configuration file path')
    parser.add_argument('--test', help='Specific test to run')
    parser.add_argument('--comparison', action='store_true', help='Run comparison test')
    args = parser.parse_args()

    runner = PerformanceTestRunner(args.config)

    if args.comparison:
        # 运行对比测试
        base_config = runner.config['tests'][0]  # 第一个测试作为基线
        new_config = runner.config['tests'][1]   # 第二个测试作为新配置
        runner.run_comparison_test(base_config, new_config)
    elif args.test:
        # 运行特定测试
        test_config = next((t for t in runner.config['tests'] if t['name'] == args.test), None)
        if test_config:
            runner.run_single_test(test_config)
        else:
            print(f"Test '{args.test}' not found in configuration")
    else:
        # 运行所有测试
        runner.run_all_tests()

if __name__ == "__main__":
    main()
```

---

## API基准测试

### HTTP性能测试

```python
# api_benchmark.py
import asyncio
import aiohttp
import time
import statistics
import json
from datetime import datetime
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import matplotlib.pyplot as plt
import pandas as pd

@dataclass
class BenchmarkResult:
    """基准测试结果"""
    endpoint: str
    method: str
    total_requests: int
    successful_requests: int
    failed_requests: int
    average_response_time: float
    median_response_time: float
    min_response_time: float
    max_response_time: float
    p95_response_time: float
    p99_response_time: float
    requests_per_second: float
    error_rate: float
    throughput_mbps: float

class APIBenchmark:
    """API基准测试工具"""

    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.session = None
        self.results = []

    async def __aenter__(self):
        """异步上下文管理器入口"""
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        if self.session:
            await self.session.close()

    async def benchmark_endpoint(self, endpoint: str, method: str = "GET",
                              payload: Optional[Dict] = None,
                              headers: Optional[Dict] = None,
                              concurrent_users: int = 10,
                              total_requests: int = 100) -> BenchmarkResult:
        """对单个端点进行基准测试"""

        url = f"{self.base_url}{endpoint}"
        request_times = []
        success_count = 0
        error_count = 0
        total_bytes = 0

        print(f"Benchmarking {method} {url}")
        print(f"Concurrent users: {concurrent_users}")
        print(f"Total requests: {total_requests}")

        async def make_request():
            """发送单个请求"""
            nonlocal success_count, error_count, total_bytes

            try:
                start_time = time.time()

                if method.upper() == "GET":
                    async with self.session.get(url, headers=headers) as response:
                        content = await response.read()
                        response_time = (time.time() - start_time) * 1000  # 转换为毫秒
                        total_bytes += len(content)

                        if response.status < 400:
                            success_count += 1
                        else:
                            error_count += 1

                        return response_time, response.status

                elif method.upper() == "POST":
                    async with self.session.post(url, json=payload, headers=headers) as response:
                        content = await response.read()
                        response_time = (time.time() - start_time) * 1000
                        total_bytes += len(content)

                        if response.status < 400:
                            success_count += 1
                        else:
                            error_count += 1

                        return response_time, response.status

            except Exception as e:
                error_count += 1
                return None, None

        # 创建并发任务
        tasks = []
        requests_per_user = total_requests // concurrent_users

        for _ in range(concurrent_users):
            for _ in range(requests_per_user):
                tasks.append(make_request())

        # 执行所有请求
        start_time = time.time()
        results = await asyncio.gather(*tasks, return_exceptions=True)
        end_time = time.time()

        # 处理结果
        for result in results:
            if isinstance(result, tuple) and result[0] is not None:
                request_times.append(result[0])

        # 计算统计信息
        if request_times:
            avg_time = statistics.mean(request_times)
            median_time = statistics.median(request_times)
            min_time = min(request_times)
            max_time = max(request_times)
            p95_time = statistics.quantiles(request_times, n=20)[18]  # 95th percentile
            p99_time = statistics.quantiles(request_times, n=100)[98]  # 99th percentile
        else:
            avg_time = median_time = min_time = max_time = p95_time = p99_time = 0

        total_time = end_time - start_time
        rps = total_requests / total_time if total_time > 0 else 0
        error_rate = (error_count / total_requests * 100) if total_requests > 0 else 0
        throughput_mbps = (total_bytes * 8) / (total_time * 1000000) if total_time > 0 else 0

        benchmark_result = BenchmarkResult(
            endpoint=endpoint,
            method=method,
            total_requests=total_requests,
            successful_requests=success_count,
            failed_requests=error_count,
            average_response_time=avg_time,
            median_response_time=median_time,
            min_response_time=min_time,
            max_response_time=max_time,
            p95_response_time=p95_time,
            p99_response_time=p99_time,
            requests_per_second=rps,
            error_rate=error_rate,
            throughput_mbps=throughput_mbps
        )

        self.results.append(benchmark_result)
        return benchmark_result

    async def run_comprehensive_benchmark(self):
        """运行全面的基准测试"""

        print("Starting comprehensive API benchmark...")

        # 测试端点配置
        endpoints = [
            ("GET", "/health", None, None),
            ("GET", "/api/v1/data/matches", None, {"Accept": "application/json"}),
            ("GET", "/api/v1/data/matches/1", None, {"Accept": "application/json"}),
            ("GET", "/api/v1/predictions/match/1", None, {"Accept": "application/json"}),
            ("POST", "/api/v1/predictions", {
                "match_id": 1,
                "features": {
                    "home_form": 0.7,
                    "away_form": 0.5,
                    "head_to_head": 0.6
                }
            }, {"Content-Type": "application/json"}),
            ("GET", "/api/v1/analytics/performance", None, {"Accept": "application/json"}),
            ("GET", "/api/v1/monitoring/metrics", None, {"Accept": "application/json"}),
        ]

        results = []

        for method, endpoint, payload, headers in endpoints:
            result = await self.benchmark_endpoint(
                endpoint=endpoint,
                method=method,
                payload=payload,
                headers=headers,
                concurrent_users=50,
                total_requests=1000
            )
            results.append(result)

            # 输出结果
            print(f"\n{method} {endpoint} Results:")
            print(f"  Average Response Time: {result.average_response_time:.2f}ms")
            print(f"  Requests Per Second: {result.requests_per_second:.2f}")
            print(f"  Error Rate: {result.error_rate:.2f}%")
            print(f"  P95 Response Time: {result.p95_response_time:.2f}ms")
            print("-" * 50)

        return results

    def generate_report(self, output_file: str = "benchmark_report.md"):
        """生成基准测试报告"""
        if not self.results:
            print("No benchmark results to report")
            return

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        with open(output_file, 'w') as f:
            f.write("# API Benchmark Report\n\n")
            f.write(f"Generated: {timestamp}\n\n")

            f.write("## Summary\n\n")
            f.write("| Endpoint | Method | Avg Response Time | RPS | Error Rate | P95 |\n")
            f.write("|----------|--------|-------------------|-----|------------|-----|\n")

            for result in self.results:
                f.write(f"| {result.endpoint} | {result.method} | {result.average_response_time:.2f}ms | {result.requests_per_second:.2f} | {result.error_rate:.2f}% | {result.p95_response_time:.2f}ms |\n")

            f.write("\n## Detailed Results\n\n")

            for result in self.results:
                f.write(f"### {result.method} {result.endpoint}\n\n")
                f.write(f"- **Total Requests**: {result.total_requests}\n")
                f.write(f"- **Successful Requests**: {result.successful_requests}\n")
                f.write(f"- **Failed Requests**: {result.failed_requests}\n")
                f.write(f"- **Average Response Time**: {result.average_response_time:.2f}ms\n")
                f.write(f"- **Median Response Time**: {result.median_response_time:.2f}ms\n")
                f.write(f"- **Min Response Time**: {result.min_response_time:.2f}ms\n")
                f.write(f"- **Max Response Time**: {result.max_response_time:.2f}ms\n")
                f.write(f"- **95th Percentile**: {result.p95_response_time:.2f}ms\n")
                f.write(f"- **99th Percentile**: {result.p99_response_time:.2f}ms\n")
                f.write(f"- **Requests Per Second**: {result.requests_per_second:.2f}\n")
                f.write(f"- **Error Rate**: {result.error_rate:.2f}%\n")
                f.write(f"- **Throughput**: {result.throughput_mbps:.2f} Mbps\n\n")

        print(f"Benchmark report generated: {output_file}")

    def generate_visualization(self, output_file: str = "benchmark_visualization.png"):
        """生成可视化图表"""
        if not self.results:
            print("No benchmark results to visualize")
            return

        # 准备数据
        endpoints = [f"{r.method} {r.endpoint}" for r in self.results]
        avg_times = [r.average_response_time for r in self.results]
        p95_times = [r.p95_response_time for r in self.results]
        rps_values = [r.requests_per_second for r in self.results]

        # 创建图表
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15, 10))

        # 响应时间对比
        ax1.bar(range(len(endpoints)), avg_times, alpha=0.7, label='Average')
        ax1.bar(range(len(endpoints)), p95_times, alpha=0.7, label='P95')
        ax1.set_xlabel('Endpoint')
        ax1.set_ylabel('Response Time (ms)')
        ax1.set_title('Response Time Comparison')
        ax1.set_xticks(range(len(endpoints)))
        ax1.set_xticklabels([e.split()[-1] for e in endpoints], rotation=45)
        ax1.legend()

        # RPS对比
        ax2.bar(range(len(endpoints)), rps_values, color='green', alpha=0.7)
        ax2.set_xlabel('Endpoint')
        ax2.set_ylabel('Requests Per Second')
        ax2.set_title('Throughput Comparison')
        ax2.set_xticks(range(len(endpoints)))
        ax2.set_xticklabels([e.split()[-1] for e in endpoints], rotation=45)

        # 错误率对比
        error_rates = [r.error_rate for r in self.results]
        ax3.bar(range(len(endpoints)), error_rates, color='red', alpha=0.7)
        ax3.set_xlabel('Endpoint')
        ax3.set_ylabel('Error Rate (%)')
        ax3.set_title('Error Rate Comparison')
        ax3.set_xticks(range(len(endpoints)))
        ax3.set_xticklabels([e.split()[-1] for e in endpoints], rotation=45)

        # 综合性能雷达图
        categories = ['Speed', 'Throughput', 'Reliability', 'Consistency']
        N = len(categories)

        # 计算标准化指标
        speed_scores = [1 - (min(avg_times) / t) for t in avg_times]
        throughput_scores = [t / max(rps_values) for t in rps_values]
        reliability_scores = [1 - (e / 100) for e in error_rates]
        consistency_scores = [1 - ((p95 - a) / a) for a, p95 in zip(avg_times, p95_times)]

        angles = [n / float(N) * 2 * 3.14159 for n in range(N)]
        angles += angles[:1]

        ax4 = plt.subplot(2, 2, 4, projection='polar')
        for i, endpoint in enumerate(endpoints):
            values = [
                speed_scores[i],
                throughput_scores[i],
                reliability_scores[i],
                consistency_scores[i]
            ]
            values += values[:1]

            ax4.plot(angles, values, 'o-', linewidth=2, label=endpoint.split()[-1])
            ax4.fill(angles, values, alpha=0.25)

        ax4.set_xticks(angles[:-1])
        ax4.set_xticklabels(categories)
        ax4.set_title('Performance Radar Chart')
        ax4.legend(loc='upper right', bbox_to_anchor=(1.2, 1.0))

        plt.tight_layout()
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        plt.close()

        print(f"Visualization generated: {output_file}")

async def main():
    """主函数"""
    async with APIBenchmark() as benchmark:
        # 运行全面基准测试
        results = await benchmark.run_comprehensive_benchmark()

        # 生成报告和可视化
        benchmark.generate_report()
        benchmark.generate_visualization()

        # 输出总结
        print("\n" + "="*50)
        print("BENCHMARK SUMMARY")
        print("="*50)

        total_avg_time = sum(r.average_response_time for r in results) / len(results)
        total_rps = sum(r.requests_per_second for r in results) / len(results)
        total_error_rate = sum(r.error_rate for r in results) / len(results)

        print(f"Overall Average Response Time: {total_avg_time:.2f}ms")
        print(f"Overall Average RPS: {total_rps:.2f}")
        print(f"Overall Average Error Rate: {total_error_rate:.2f}%")

        # 性能评估
        if total_avg_time < 200:
            print("✅ Response Time: EXCELLENT")
        elif total_avg_time < 500:
            print("⚠️ Response Time: GOOD")
        else:
            print("❌ Response Time: NEEDS IMPROVEMENT")

        if total_rps > 100:
            print("✅ Throughput: EXCELLENT")
        elif total_rps > 50:
            print("⚠️ Throughput: GOOD")
        else:
            print("❌ Throughput: NEEDS IMPROVEMENT")

        if total_error_rate < 1:
            print("✅ Error Rate: EXCELLENT")
        elif total_error_rate < 5:
            print("⚠️ Error Rate: GOOD")
        else:
            print("❌ Error Rate: NEEDS IMPROVEMENT")

if __name__ == "__main__":
    asyncio.run(main())
```

---

## 监控与分析

### 性能监控

```python
# performance_monitor.py
import time
import psutil
import asyncio
import json
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import matplotlib.pyplot as plt
import pandas as pd
from dataclasses import dataclass, asdict

@dataclass
class SystemMetrics:
    """系统指标"""
    timestamp: str
    cpu_percent: float
    memory_percent: float
    disk_usage: float
    network_sent: float
    network_recv: float
    load_avg: float

@dataclass
class ApplicationMetrics:
    """应用指标"""
    timestamp: str
    active_connections: int
    request_count: int
    response_time_avg: float
    error_rate: float
    throughput: float

class PerformanceMonitor:
    """性能监控器"""

    def __init__(self, db_path: str = "performance_monitoring.db"):
        self.db_path = db_path
        self.is_running = False
        self.monitoring_task = None
        self.init_database()

    def init_database(self):
        """初始化数据库"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS system_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                cpu_percent REAL,
                memory_percent REAL,
                disk_usage REAL,
                network_sent REAL,
                network_recv REAL,
                load_avg REAL
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS application_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                active_connections INTEGER,
                request_count INTEGER,
                response_time_avg REAL,
                error_rate REAL,
                throughput REAL
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS performance_alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                alert_type TEXT,
                severity TEXT,
                message TEXT,
                metric_name TEXT,
                metric_value REAL,
                threshold_value REAL,
                resolved BOOLEAN DEFAULT FALSE
            )
        ''')

        conn.commit()
        conn.close()

    async def collect_system_metrics(self) -> SystemMetrics:
        """收集系统指标"""
        timestamp = datetime.now().isoformat()

        # CPU使用率
        cpu_percent = psutil.cpu_percent(interval=1)

        # 内存使用率
        memory = psutil.virtual_memory()
        memory_percent = memory.percent

        # 磁盘使用率
        disk = psutil.disk_usage('/')
        disk_usage = disk.percent

        # 网络流量
        network = psutil.net_io_counters()
        network_sent = network.bytes_sent
        network_recv = network.bytes_recv

        # 系统负载
        load_avg = psutil.getloadavg()[0] if hasattr(psutil, 'getloadavg') else 0

        return SystemMetrics(
            timestamp=timestamp,
            cpu_percent=cpu_percent,
            memory_percent=memory_percent,
            disk_usage=disk_usage,
            network_sent=network_sent,
            network_recv=network_recv,
            load_avg=load_avg
        )

    async def collect_application_metrics(self) -> ApplicationMetrics:
        """收集应用指标"""
        timestamp = datetime.now().isoformat()

        # 这里应该从应用中获取真实的指标
        # 现在使用模拟数据
        active_connections = 100  # 模拟活跃连接数
        request_count = 1000     # 模拟请求计数
        response_time_avg = 150  # 模拟平均响应时间
        error_rate = 0.5         # 模拟错误率
        throughput = 500         # 模拟吞吐量

        return ApplicationMetrics(
            timestamp=timestamp,
            active_connections=active_connections,
            request_count=request_count,
            response_time_avg=response_time_avg,
            error_rate=error_rate,
            throughput=throughput
        )

    def save_metrics(self, metrics: SystemMetrics):
        """保存系统指标到数据库"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO system_metrics
            (timestamp, cpu_percent, memory_percent, disk_usage, network_sent, network_recv, load_avg)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            metrics.timestamp, metrics.cpu_percent, metrics.memory_percent,
            metrics.disk_usage, metrics.network_sent, metrics.network_recv, metrics.load_avg
        ))

        conn.commit()
        conn.close()

    def save_application_metrics(self, metrics: ApplicationMetrics):
        """保存应用指标到数据库"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO application_metrics
            (timestamp, active_connections, request_count, response_time_avg, error_rate, throughput)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            metrics.timestamp, metrics.active_connections, metrics.request_count,
            metrics.response_time_avg, metrics.error_rate, metrics.throughput
        ))

        conn.commit()
        conn.close()

    def check_alerts(self, metrics: SystemMetrics, app_metrics: ApplicationMetrics) -> List[Dict[str, Any]]:
        """检查性能警报"""
        alerts = []

        # CPU使用率警报
        if metrics.cpu_percent > 80:
            alerts.append({
                'alert_type': 'HIGH_CPU',
                'severity': 'WARNING' if metrics.cpu_percent < 90 else 'CRITICAL',
                'message': f'CPU usage is {metrics.cpu_percent}%',
                'metric_name': 'cpu_percent',
                'metric_value': metrics.cpu_percent,
                'threshold_value': 80
            })

        # 内存使用率警报
        if metrics.memory_percent > 85:
            alerts.append({
                'alert_type': 'HIGH_MEMORY',
                'severity': 'WARNING' if metrics.memory_percent < 95 else 'CRITICAL',
                'message': f'Memory usage is {metrics.memory_percent}%',
                'metric_name': 'memory_percent',
                'metric_value': metrics.memory_percent,
                'threshold_value': 85
            })

        # 磁盘使用率警报
        if metrics.disk_usage > 90:
            alerts.append({
                'alert_type': 'HIGH_DISK',
                'severity': 'WARNING' if metrics.disk_usage < 95 else 'CRITICAL',
                'message': f'Disk usage is {metrics.disk_usage}%',
                'metric_name': 'disk_usage',
                'metric_value': metrics.disk_usage,
                'threshold_value': 90
            })

        # 响应时间警报
        if app_metrics.response_time_avg > 1000:
            alerts.append({
                'alert_type': 'HIGH_RESPONSE_TIME',
                'severity': 'WARNING' if app_metrics.response_time_avg < 2000 else 'CRITICAL',
                'message': f'Average response time is {app_metrics.response_time_avg}ms',
                'metric_name': 'response_time_avg',
                'metric_value': app_metrics.response_time_avg,
                'threshold_value': 1000
            })

        # 错误率警报
        if app_metrics.error_rate > 5:
            alerts.append({
                'alert_type': 'HIGH_ERROR_RATE',
                'severity': 'WARNING' if app_metrics.error_rate < 10 else 'CRITICAL',
                'message': f'Error rate is {app_metrics.error_rate}%',
                'metric_name': 'error_rate',
                'metric_value': app_metrics.error_rate,
                'threshold_value': 5
            })

        # 保存警报到数据库
        for alert in alerts:
            self.save_alert(alert)

        return alerts

    def save_alert(self, alert: Dict[str, Any]):
        """保存警报到数据库"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO performance_alerts
            (alert_type, severity, message, metric_name, metric_value, threshold_value)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            alert['alert_type'], alert['severity'], alert['message'],
            alert['metric_name'], alert['metric_value'], alert['threshold_value']
        ))

        conn.commit()
        conn.close()

    async def monitoring_loop(self, interval: int = 60):
        """监控循环"""
        print("Starting performance monitoring...")

        while self.is_running:
            try:
                # 收集指标
                system_metrics = await self.collect_system_metrics()
                app_metrics = await self.collect_application_metrics()

                # 保存指标
                self.save_metrics(system_metrics)
                self.save_application_metrics(app_metrics)

                # 检查警报
                alerts = self.check_alerts(system_metrics, app_metrics)

                # 输出状态
                print(f"[{system_metrics.timestamp}] "
                      f"CPU: {system_metrics.cpu_percent}%, "
                      f"Memory: {system_metrics.memory_percent}%, "
                      f"Response Time: {app_metrics.response_time_avg}ms")

                # 如果有警报，输出警报信息
                for alert in alerts:
                    print(f"🚨 ALERT: {alert['message']}")

                # 等待下一次采集
                await asyncio.sleep(interval)

            except Exception as e:
                print(f"Error in monitoring loop: {e}")
                await asyncio.sleep(interval)

    def start_monitoring(self, interval: int = 60):
        """启动监控"""
        if self.is_running:
            print("Monitoring is already running")
            return

        self.is_running = True
        self.monitoring_task = asyncio.create_task(self.monitoring_loop(interval))
        print(f"Performance monitoring started (interval: {interval}s)")

    def stop_monitoring(self):
        """停止监控"""
        if not self.is_running:
            print("Monitoring is not running")
            return

        self.is_running = False
        if self.monitoring_task:
            self.monitoring_task.cancel()
            print("Performance monitoring stopped")

    def get_metrics_history(self, hours: int = 24) -> Dict[str, pd.DataFrame]:
        """获取指标历史数据"""
        conn = sqlite3.connect(self.db_path)

        # 获取系统指标
        system_query = f'''
            SELECT * FROM system_metrics
            WHERE timestamp >= datetime('now', '-{hours} hours')
            ORDER BY timestamp
        '''
        system_df = pd.read_sql_query(system_query, conn)

        # 获取应用指标
        app_query = f'''
            SELECT * FROM application_metrics
            WHERE timestamp >= datetime('now', '-{hours} hours')
            ORDER BY timestamp
        '''
        app_df = pd.read_sql_query(app_query, conn)

        conn.close()

        return {
            'system': system_df,
            'application': app_df
        }

    def generate_performance_report(self, hours: int = 24, output_file: str = "performance_report.md"):
        """生成性能报告"""
        metrics_history = self.get_metrics_history(hours)

        if not metrics_history['system'].empty and not metrics_history['application'].empty:
            system_df = metrics_history['system']
            app_df = metrics_history['application']

            # 计算统计信息
            report_data = {
                'period': f"{hours} hours",
                'generated_at': datetime.now().isoformat(),
                'system_stats': {
                    'avg_cpu': system_df['cpu_percent'].mean(),
                    'max_cpu': system_df['cpu_percent'].max(),
                    'avg_memory': system_df['memory_percent'].mean(),
                    'max_memory': system_df['memory_percent'].max(),
                    'avg_disk': system_df['disk_usage'].mean(),
                    'max_disk': system_df['disk_usage'].max(),
                },
                'application_stats': {
                    'avg_response_time': app_df['response_time_avg'].mean(),
                    'max_response_time': app_df['response_time_avg'].max(),
                    'avg_error_rate': app_df['error_rate'].mean(),
                    'max_error_rate': app_df['error_rate'].max(),
                    'avg_throughput': app_df['throughput'].mean(),
                    'max_throughput': app_df['throughput'].max(),
                }
            }

            # 生成报告
            with open(output_file, 'w') as f:
                f.write("# Performance Monitoring Report\n\n")
                f.write(f"Generated: {report_data['generated_at']}\n")
                f.write(f"Period: Last {report_data['period']}\n\n")

                f.write("## System Metrics\n\n")
                f.write("### CPU Usage\n")
                f.write(f"- Average: {report_data['system_stats']['avg_cpu']:.2f}%\n")
                f.write(f"- Maximum: {report_data['system_stats']['max_cpu']:.2f}%\n\n")

                f.write("### Memory Usage\n")
                f.write(f"- Average: {report_data['system_stats']['avg_memory']:.2f}%\n")
                f.write(f"- Maximum: {report_data['system_stats']['max_memory']:.2f}%\n\n")

                f.write("### Disk Usage\n")
                f.write(f"- Average: {report_data['system_stats']['avg_disk']:.2f}%\n")
                f.write(f"- Maximum: {report_data['system_stats']['max_disk']:.2f}%\n\n")

                f.write("## Application Metrics\n\n")
                f.write("### Response Time\n")
                f.write(f"- Average: {report_data['application_stats']['avg_response_time']:.2f}ms\n")
                f.write(f"- Maximum: {report_data['application_stats']['max_response_time']:.2f}ms\n\n")

                f.write("### Error Rate\n")
                f.write(f"- Average: {report_data['application_stats']['avg_error_rate']:.2f}%\n")
                f.write(f"- Maximum: {report_data['application_stats']['max_error_rate']:.2f}%\n\n")

                f.write("### Throughput\n")
                f.write(f"- Average: {report_data['application_stats']['avg_throughput']:.2f} req/s\n")
                f.write(f"- Maximum: {report_data['application_stats']['max_throughput']:.2f} req/s\n\n")

                # 生成趋势图
                self.generate_metrics_trend_chart(metrics_history, "performance_trend.png")

                f.write("## Visualizations\n\n")
                f.write("![Performance Trend](performance_trend.png)\n")

            print(f"Performance report generated: {output_file}")

    def generate_metrics_trend_chart(self, metrics_history: Dict[str, pd.DataFrame], output_file: str):
        """生成指标趋势图"""
        system_df = metrics_history['system']
        app_df = metrics_history['application']

        if system_df.empty or app_df.empty:
            print("No data available for trend chart")
            return

        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15, 10))

        # 转换时间戳
        system_df['timestamp'] = pd.to_datetime(system_df['timestamp'])
        app_df['timestamp'] = pd.to_datetime(app_df['timestamp'])

        # CPU使用率趋势
        ax1.plot(system_df['timestamp'], system_df['cpu_percent'], 'b-', linewidth=2)
        ax1.axhline(y=80, color='r', linestyle='--', alpha=0.7, label='Warning Threshold')
        ax1.set_title('CPU Usage Trend')
        ax1.set_ylabel('CPU Usage (%)')
        ax1.legend()
        ax1.grid(True, alpha=0.3)

        # 内存使用率趋势
        ax2.plot(system_df['timestamp'], system_df['memory_percent'], 'g-', linewidth=2)
        ax2.axhline(y=85, color='r', linestyle='--', alpha=0.7, label='Warning Threshold')
        ax2.set_title('Memory Usage Trend')
        ax2.set_ylabel('Memory Usage (%)')
        ax2.legend()
        ax2.grid(True, alpha=0.3)

        # 响应时间趋势
        ax3.plot(app_df['timestamp'], app_df['response_time_avg'], 'r-', linewidth=2)
        ax3.axhline(y=1000, color='r', linestyle='--', alpha=0.7, label='Warning Threshold')
        ax3.set_title('Response Time Trend')
        ax3.set_ylabel('Response Time (ms)')
        ax3.legend()
        ax3.grid(True, alpha=0.3)

        # 吞吐量趋势
        ax4.plot(app_df['timestamp'], app_df['throughput'], 'purple', linewidth=2)
        ax4.set_title('Throughput Trend')
        ax4.set_ylabel('Throughput (req/s)')
        ax4.grid(True, alpha=0.3)

        # 格式化x轴
        for ax in [ax1, ax2, ax3, ax4]:
            ax.tick_params(axis='x', rotation=45)

        plt.tight_layout()
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        plt.close()

        print(f"Metrics trend chart generated: {output_file}")

# 使用示例
async def main():
    """主函数示例"""
    monitor = PerformanceMonitor()

    try:
        # 启动监控
        monitor.start_monitoring(interval=30)

        # 运行一段时间
        await asyncio.sleep(300)  # 5分钟

        # 生成报告
        monitor.generate_performance_report(hours=1)

    finally:
        # 停止监控
        monitor.stop_monitoring()

if __name__ == "__main__":
    asyncio.run(main())
```

---

## 总结

本文档详细介绍了足球预测系统的性能测试方案，包括：

1. **Locust性能测试**: 完整的用户行为模拟和负载测试
2. **API基准测试**: 详细的端点性能分析和优化建议
3. **数据库性能测试**: 查询优化、连接池和索引优化
4. **监控与分析**: 实时性能监控和趋势分析

这些测试和监控工具可以帮助确保系统在高负载下的稳定性和性能，为持续优化提供数据支持。