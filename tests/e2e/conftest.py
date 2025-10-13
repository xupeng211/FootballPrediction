"""
E2E 测试配置文件
提供 E2E 测试的共享 fixtures 和配置
"""

import pytest
import asyncio
import os
import sys
from pathlib import Path
from typing import AsyncGenerator, Dict, Any
import tempfile
import logging
from datetime import datetime, timezone

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
sys.path.insert(0, "src")

# 配置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# E2E 测试配置
os.environ["TESTING"] = "true"
os.environ["TEST_ENV"] = "e2e"
os.environ["E2E_MODE"] = "full"


@pytest.fixture(scope="session")
def event_loop():
    """创建事件循环"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def api_client():
    """API 客户端 fixture"""
    from httpx import AsyncClient, TimeoutException
    from tenacity import retry, stop_after_attempt, wait_exponential

    # API 基础 URL
    base_url = os.getenv("E2E_BASE_URL", "http://localhost")
    api_base = f"{base_url}:8000"

    # 创建客户端
    client = AsyncClient(base_url=api_base, timeout=60.0, follow_redirects=True)

    # 等待服务就绪
    @retry(
        stop=stop_after_attempt(30), wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    async def wait_for_api():
        try:
            response = await client.get("/health")
            response.raise_for_status()
            return True
        except (TimeoutException, Exception):
            logger.warning("API not ready, waiting...")
            raise

    try:
        await wait_for_api()
        logger.info("✅ API 服务就绪")
    except Exception as e:
        logger.error(f"❌ API 服务未就绪: {e}")
        raise

    yield client

    await client.aclose()


@pytest.fixture(scope="session")
async def auth_tokens(api_client) -> Dict[str, str]:
    """创建各种角色的认证 tokens"""
    tokens = {}

    # 创建普通用户
    user_data = {
        "username": "e2e_user",
        "email": "e2e@example.com",
        "password": "E2ETestPass123!",
    }

    # 注册
    try:
        await api_client.post("/api/v1/auth/register", json=user_data)
    except Exception:
        pass  # 用户可能已存在

    # 登录获取 token
    login_data = {"username": user_data["username"], "password": user_data["password"]}
    response = await api_client.post("/api/v1/auth/login", _data =login_data)
    if response.status_code == 200:
        tokens["user"] = response.json()["access_token"]
        logger.info("✅ 用户 token 获取成功")

    # 创建管理员用户
    admin_data = {
        "username": "e2e_admin",
        "email": "e2e_admin@example.com",
        "password": "E2EAdminPass123!",
    }

    try:
        await api_client.post(
            "/api/v1/auth/register", json={**admin_data, "role": "admin"}
        )
    except Exception:
        pass

    # 登录管理员
    admin_login = {
        "username": admin_data["username"],
        "password": admin_data["password"],
    }
    response = await api_client.post("/api/v1/auth/login", _data =admin_login)
    if response.status_code == 200:
        tokens["admin"] = response.json()["access_token"]
        logger.info("✅ 管理员 token 获取成功")

    # 创建分析师用户
    analyst_data = {
        "username": "e2e_analyst",
        "email": "e2e_analyst@example.com",
        "password": "E2EAnalystPass123!",
    }

    try:
        await api_client.post(
            "/api/v1/auth/register", json={**analyst_data, "role": "analyst"}
        )
    except Exception:
        pass

    # 登录分析师
    analyst_login = {
        "username": analyst_data["username"],
        "password": analyst_data["password"],
    }
    response = await api_client.post("/api/v1/auth/login", _data =analyst_login)
    if response.status_code == 200:
        tokens["analyst"] = response.json()["access_token"]
        logger.info("✅ 分析师 token 获取成功")

    return tokens


@pytest.fixture
async def user_headers(auth_tokens):
    """普通用户请求头"""
    return {"Authorization": f"Bearer {auth_tokens['user']}"}


@pytest.fixture
async def admin_headers(auth_tokens):
    """管理员请求头"""
    return {"Authorization": f"Bearer {auth_tokens['admin']}"}


@pytest.fixture
async def analyst_headers(auth_tokens):
    """分析师请求头"""
    return {"Authorization": f"Bearer {auth_tokens['analyst']}"}


@pytest.fixture(scope="session")
async def test_data_loader(api_client, auth_tokens):
    """测试数据加载器"""

    class DataLoader:
        def __init__(self, client, tokens):
            self.client = client
            self.tokens = tokens
            self.created_data = {}

        async def create_teams(self):
            """创建测试队伍"""
            teams_data = [
                {"name": "E2E Team Alpha", "city": "Alpha City", "founded": 2020},
                {"name": "E2E Team Beta", "city": "Beta City", "founded": 2021},
                {"name": "E2E Team Gamma", "city": "Gamma City", "founded": 2019},
                {"name": "E2E Team Delta", "city": "Delta City", "founded": 2022},
                {"name": "E2E Team Epsilon", "city": "Epsilon City", "founded": 2020},
                {"name": "E2E Team Zeta", "city": "Zeta City", "founded": 2021},
            ]

            headers = {"Authorization": f"Bearer {self.tokens['admin']}"}
            self.created_data["teams"] = []

            for team_data in teams_data:
                response = await self.client.post(
                    "/api/v1/teams", json=team_data, headers=headers
                )
                if response.status_code == 201:
                    self.created_data["teams"].append(response.json())
                    logger.info(f"✅ 创建队伍: {team_data['name']}")

            return self.created_data["teams"]

        async def create_leagues(self):
            """创建测试联赛"""
            leagues_data = [
                {"name": "E2E Premier League", "country": "E2E Land", "level": 1},
                {"name": "E2E Championship", "country": "E2E Land", "level": 2},
            ]

            headers = {"Authorization": f"Bearer {self.tokens['admin']}"}
            self.created_data["leagues"] = []

            for league_data in leagues_data:
                response = await self.client.post(
                    "/api/v1/leagues", json=league_data, headers=headers
                )
                if response.status_code == 201:
                    self.created_data["leagues"].append(response.json())
                    logger.info(f"✅ 创建联赛: {league_data['name']}")

            return self.created_data["leagues"]

        async def create_matches(self):
            """创建测试比赛"""
            if not self.created_data.get("teams"):
                await self.create_teams()

            matches_data = [
                {
                    "home_team_id": self.created_data["teams"][0]["id"],
                    "away_team_id": self.created_data["teams"][1]["id"],
                    "match_date": (
                        datetime.now(timezone.utc) + timedelta(days=1)
                    ).isoformat(),
                    "competition": "E2E Premier League",
                    "season": "2024/2025",
                    "status": "UPCOMING",
                    "venue": "E2E Stadium Alpha",
                },
                {
                    "home_team_id": self.created_data["teams"][2]["id"],
                    "away_team_id": self.created_data["teams"][3]["id"],
                    "match_date": (
                        datetime.now(timezone.utc) + timedelta(days=2)
                    ).isoformat(),
                    "competition": "E2E Premier League",
                    "season": "2024/2025",
                    "status": "UPCOMING",
                    "venue": "E2E Stadium Beta",
                },
                {
                    "home_team_id": self.created_data["teams"][4]["id"],
                    "away_team_id": self.created_data["teams"][5]["id"],
                    "match_date": (
                        datetime.now(timezone.utc) - timedelta(days=1)
                    ).isoformat(),
                    "competition": "E2E Premier League",
                    "season": "2024/2025",
                    "status": "COMPLETED",
                    "home_score": 2,
                    "away_score": 1,
                    "venue": "E2E Stadium Gamma",
                },
            ]

            headers = {"Authorization": f"Bearer {self.tokens['admin']}"}
            self.created_data["matches"] = []

            for match_data in matches_data:
                response = await self.client.post(
                    "/api/v1/matches", json=match_data, headers=headers
                )
                if response.status_code == 201:
                    self.created_data["matches"].append(response.json())
                    logger.info(f"✅ 创建比赛: {match_data['competition']}")

            return self.created_data["matches"]

        async def create_predictions(self):
            """创建测试预测"""
            if not self.created_data.get("matches"):
                await self.create_matches()

            predictions_data = []
            headers = {"Authorization": f"Bearer {self.tokens['user']}"}

            for match in self.created_data["matches"][:2]:  # 只对未开始的比赛做预测
                pred_data = {
                    "match_id": match["id"],
                    "prediction": "HOME_WIN" if match["id"] % 2 == 0 else "DRAW",
                    "confidence": 0.75 + (match["id"] * 0.05),
                }
                response = await self.client.post(
                    "/api/v1/predictions", json=pred_data, headers=headers
                )
                if response.status_code == 201:
                    predictions_data.append(response.json())
                    logger.info(f"✅ 创建预测: 比赛 {match['id']}")

            self.created_data["predictions"] = predictions_data
            return predictions_data

        async def cleanup(self):
            """清理测试数据"""
            logger.info("🧹 清理 E2E 测试数据...")
            # 这里可以实现清理逻辑，或者在每个测试方法后单独清理
            pass

    from datetime import timedelta

    loader = DataLoader(api_client, auth_tokens)

    yield loader

    # await loader.cleanup()


@pytest.fixture(scope="session")
async def websocket_client():
    """WebSocket 客户端 fixture"""
    try:
        import websockets
        import json

        base_url = os.getenv("E2E_BASE_URL", "localhost")
        ws_url = f"ws://{base_url}:8000/ws"

        async with websockets.connect(ws_url) as websocket:
            logger.info("✅ WebSocket 连接成功")
            yield websocket

    except ImportError:
        logger.warning("websockets 库未安装，跳过 WebSocket 测试")
        yield None
    except Exception as e:
        logger.warning(f"WebSocket 连接失败: {e}")
        yield None


@pytest.fixture
def performance_metrics():
    """性能指标收集器"""
    import time

    class MetricsCollector:
        def __init__(self):
            self.metrics = {}

        def start_timer(self, name):
            self.metrics[f"{name}_start"] = time.time()

        def end_timer(self, name):
            if f"{name}_start" in self.metrics:
                duration = time.time() - self.metrics[f"{name}_start"]
                self.metrics[f"{name}_duration"] = duration
                return duration
            return 0

        def get_duration(self, name):
            return self.metrics.get(f"{name}_duration", 0)

        def get_all_metrics(self):
            return {k: v for k, v in self.metrics.items() if "_duration" in k}

    return MetricsCollector()


@pytest.fixture(autouse=True)
async def test_case_logger(request):
    """自动记录测试用例开始和结束"""
    test_name = request.node.name
    logger.info(f"\n{'=' * 60}")
    logger.info(f"🧪 开始 E2E 测试: {test_name}")
    logger.info(f"{'=' * 60}")

    yield

    logger.info(f"\n{'=' * 60}")
    logger.info(f"✅ 完成 E2E 测试: {test_name}")
    logger.info(f"{'=' * 60}\n")


# E2E 测试标记
pytest.mark.e2e = pytest.mark.e2e
pytest.mark.smoke = pytest.mark.smoke  # 冒烟测试
pytest.mark.regression = pytest.mark.regression  # 回归测试
pytest.mark.performance = pytest.mark.performance  # 性能测试
pytest.mark.critical = pytest.mark.critical  # 关键路径测试
