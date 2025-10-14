"""
API负载测试脚本
使用Locust进行性能测试
"""

import json
import time
import random
from typing import Dict, Any
from locust import HttpUser, task, between, events
from locust.env import Environment
from locust.stats import stats_printer, stats_history
import gevent

# 测试数据
TEST_MATCHES = [
    {
        "id": 1,
        "home_team": "Manchester United",
        "away_team": "Liverpool",
        "date": "2024-03-15",
    },
    {
        "id": 2,
        "home_team": "Barcelona",
        "away_team": "Real Madrid",
        "date": "2024-03-16",
    },
    {
        "id": 3,
        "home_team": "Bayern Munich",
        "away_team": "Paris Saint Germain",
        "date": "2024-03-17",
    },
]

TEST_PREDICTIONS = [
    {
        "match_id": 1,
        "predicted_home_score": 2,
        "predicted_away_score": 1,
        "confidence": 0.75,
    },
    {
        "match_id": 2,
        "predicted_home_score": 1,
        "predicted_away_score": 1,
        "confidence": 0.65,
    },
    {
        "match_id": 3,
        "predicted_home_score": 3,
        "predicted_away_score": 2,
        "confidence": 0.80,
    },
]

TEST_USERS = [
    {"username": "testuser1", "password": "testpass123", "email": "test1@example.com"},
    {"username": "testuser2", "password": "testpass456", "email": "test2@example.com"},
    {"username": "testuser3", "password": "testpass789", "email": "test3@example.com"},
]


class FootballAPIUser(HttpUser):
    """足球预测API用户模拟"""

    wait_time = between(1, 3)  # 请求间隔1-3秒
    weight = 1

    def on_start(self):
        """用户开始时的初始化操作"""
        # 注册并登录
        self.user_data = random.choice(TEST_USERS)
        self.token = None

        # 尝试登录
        self.login()

        # 如果失败，尝试注册
        if not self.token:
            self.register()
            self.login()

    def login(self) -> bool:
        """用户登录"""
        response = self.client.post(
            "/api/auth/login",
            json={
                "username": self.user_data["username"],
                "password": self.user_data["password"],
            },
        )

        if response.status_code == 200:
            data = response.json()
            self.token = data.get("access_token")
            if self.token:
                self.client.headers.update({"Authorization": f"Bearer {self.token}"})
                print(f"✓ 用户 {self.user_data['username']} 登录成功")
                return True

        print(f"✗ 用户 {self.user_data['username']} 登录失败")
        return False

    def register(self):
        """用户注册"""
        response = self.client.post("/api/auth/register", json=self.user_data)

        if response.status_code == 201:
            print(f"✓ 用户 {self.user_data['username']} 注册成功")
        else:
            print(f"✗ 用户 {self.user_data['username']} 注册失败: {response.text}")

    @task(10)
    def get_matches(self):
        """获取比赛列表"""
        self.client.get("/api/matches")

    @task(8)
    def get_match_detail(self):
        """获取比赛详情"""
        match_id = random.choice(TEST_MATCHES)["id"]
        self.client.get(f"/api/matches/{match_id}")

    @task(7)
    def get_predictions(self):
        """获取预测列表"""
        self.client.get("/api/predictions")

    @task(6)
    def create_prediction(self):
        """创建预测"""
        prediction = random.choice(TEST_PREDICTIONS)
        response = self.client.post("/api/predictions", json=prediction)

        if response.status_code == 201:
            print(f"✓ 创建预测成功: 比赛 {prediction['match_id']}")

    @task(5)
    def get_teams(self):
        """获取球队列表"""
        self.client.get("/api/teams")

    @task(4)
    def get_team_detail(self):
        """获取球队详情"""
        team_names = ["Manchester United", "Liverpool", "Barcelona", "Real Madrid"]
        team_name = random.choice(team_names)
        self.client.get(f"/api/teams/{team_name}")

    @task(3)
    def get_statistics(self):
        """获取统计数据"""
        self.client.get("/api/statistics")

    @task(3)
    def get_leaderboard(self):
        """获取排行榜"""
        self.client.get("/api/leaderboard")

    @task(2)
    def update_prediction(self):
        """更新预测"""
        # 先获取用户的预测
        response = self.client.get("/api/predictions/mine")

        if response.status_code == 200:
            predictions = response.json()
            if predictions:
                # 随机选择一个预测更新
                prediction = random.choice(predictions)
                prediction_id = prediction["id"]

                updated_data = {
                    "predicted_home_score": random.randint(0, 5),
                    "predicted_away_score": random.randint(0, 5),
                    "confidence": round(random.uniform(0.5, 1.0), 2),
                }

                self.client.put(f"/api/predictions/{prediction_id}", json=updated_data)

    @task(1)
    def get_odds(self):
        """获取赔率信息"""
        match_id = random.choice(TEST_MATCHES)["id"]
        self.client.get(f"/api/odds?match_id={match_id}")

    @task(1)
    def search(self):
        """搜索功能"""
        query = random.choice(["Manchester", "Barcelona", "Liverpool", "Real"])
        self.client.get(f"/api/search?q={query}")


class FootballAPIAdminUser(HttpUser):
    """管理员用户模拟"""

    wait_time = between(2, 5)
    weight = 0.1  # 管理员用户比例较少

    def on_start(self):
        """管理员登录"""
        self.login()

    def login(self):
        """管理员登录"""
        response = self.client.post(
            "/api/auth/login", json={"username": "admin", "password": "admin123"}
        )

        if response.status_code == 200:
            data = response.json()
            self.token = data.get("access_token")
            if self.token:
                self.client.headers.update({"Authorization": f"Bearer {self.token}"})
                print("✓ 管理员登录成功")
                return True

        print("✗ 管理员登录失败")
        return False

    @task(5)
    def get_all_users(self):
        """获取所有用户"""
        self.client.get("/api/admin/users")

    @task(4)
    def get_system_stats(self):
        """获取系统统计"""
        self.client.get("/api/admin/statistics")

    @task(3)
    def get_audit_logs(self):
        """获取审计日志"""
        self.client.get("/api/admin/audit-logs")

    @task(2)
    def manage_match(self):
        """管理比赛"""
        match_id = random.choice(TEST_MATCHES)["id"]
        update_data = {
            "status": random.choice(["scheduled", "live", "finished"]),
            "home_score": random.randint(0, 5),
            "away_score": random.randint(0, 5),
        }
        self.client.put(f"/api/admin/matches/{match_id}", json=update_data)

    @task(1)
    def generate_report(self):
        """生成报告"""
        self.client.post("/api/admin/reports/generate")


class StressTestUser(HttpUser):
    """压力测试用户 - 轻量级高频请求"""

    wait_time = between(0.1, 0.5)  # 高频请求
    weight = 0.05  # 少量用户用于压力测试

    @task(20)
    def ping(self):
        """健康检查"""
        self.client.get("/api/health")

    @task(15)
    def get_light_data(self):
        """获取轻量级数据"""
        self.client.get("/api/teams?limit=10")

    @task(10)
    def check_predictions(self):
        """检查预测（只读）"""
        match_id = random.choice(TEST_MATCHES)["id"]
        self.client.get(f"/api/predictions?match_id={match_id}")


# 测试事件处理
@events.request.add_listener
def on_request(request_type, name, response_time, response_length, exception, **kwargs):
    """请求事件监听"""
    if exception:
        print(f"❌ 请求失败: {name} - {exception}")
    elif response_time > 1000:  # 超过1秒的请求
        print(f"⚠️ 慢请求: {name} - {response_time:.2f}ms")


@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """测试开始事件"""
    print("=" * 60)
    print("开始API负载测试")
    print("=" * 60)


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """测试结束事件"""
    print("\n" + "=" * 60)
    print("负载测试完成")
    print("=" * 60)

    # 打印统计摘要
    stats = environment.stats

    print("\n测试统计摘要:")
    print(f"  总请求数: {stats.total.num_requests}")
    print(f"  失败请求数: {stats.total.num_failures}")
    print(f"  平均响应时间: {stats.total.avg_response_time:.2f}ms")
    print(f"  最小响应时间: {stats.total.min_response_time:.2f}ms")
    print(f"  最大响应时间: {stats.total.max_response_time:.2f}ms")
    print(f"  95%响应时间: {stats.total.get_response_time_percentile(0.95):.2f}ms")
    print(f"  请求/秒: {stats.total.current_rps:.2f}")

    # 打印各端点统计
    print("\n各端点统计:")
    for endpoint in stats.entries.keys():
        if endpoint != "Total":
            stat = stats.entries[endpoint]
            print(f"  {endpoint}:")
            print(f"    请求数: {stat.num_requests}")
            print(f"    平均响应时间: {stat.avg_response_time:.2f}ms")
            print(f"    失败率: {stat.num_failures/stat.num_requests*100:.2f}%")

    # 生成HTML报告
    if hasattr(environment, "stats_html"):
        html_path = "reports/locust_report.html"
        environment.stats_html.write_html(html_path)
        print(f"\n📊 HTML报告已生成: {html_path}")


if __name__ == "__main__":
    # 设置测试环境
    env = Environment(
        user_classes=[FootballAPIUser, FootballAPIAdminUser, StressTestUser]
    )

    # 创建统计历史记录器
    stats_history(env)

    # 设置Web界面
    env.create_local_runner()

    # 设置Web UI
    env.create_web_ui("127.0.0.1", 8089)

    # 设置用户数量和孵化率
    env.runner.start(100, spawn_rate=10)  # 100个用户，每秒孵化10个

    # 打印实时统计
    gevent.spawn(stats_printer(env.stats))

    # 运行测试60秒
    gevent.sleep(60)

    # 停止测试
    env.runner.stop()
    env.runner.greenlet.join()

    print("\n测试完成!")
