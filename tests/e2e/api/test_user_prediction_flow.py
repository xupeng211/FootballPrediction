"""
用户注册到预测的完整流程 E2E 测试
测试用户从注册到创建预测的完整业务流程
"""

import asyncio
from datetime import datetime, timedelta, timezone

import pytest
from httpx import AsyncClient


@pytest.mark.e2e
@pytest.mark.critical
class TestUserPredictionFlow:
    """用户预测流程 E2E 测试"""

    @pytest.mark.asyncio
    async def test_complete_user_flow(
        self, api_client: AsyncClient, test_data_loader, performance_metrics
    ):
        """测试完整的用户流程:注册 -> 登录 -> 查看比赛 -> 创建预测"""
        # 1. 用户注册
        performance_metrics.start_timer("user_registration")

        user_data = {
            "username": "flow_test_user",
            "email": "flowtest@example.com",
            "password": "SecurePass123!",
            "first_name": "Test",
            "last_name": "User",
        }

        response = await api_client.post("/api/v1/auth/register", json=user_data)
        assert response.status_code == 201, f"注册失败: {response.text}"
        user_info = response.json()
        assert user_info["username"] == user_data["username"]
        assert user_info["email"] == user_data["email"]

        reg_duration = performance_metrics.end_timer("user_registration")
        print(f"✅ 用户注册完成 ({reg_duration:.2f}s)")

        # 2. 用户登录
        performance_metrics.start_timer("user_login")

        login_data = {
            "username": user_data["username"],
            "password": user_data["password"],
        }

        response = await api_client.post("/api/v1/auth/login", _data=login_data)
        assert response.status_code == 200, f"登录失败: {response.text}"
        login_info = response.json()
        assert "access_token" in login_info
        assert "refresh_token" in login_info

        token = login_info["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        login_duration = performance_metrics.end_timer("user_login")
        print(f"✅ 用户登录完成 ({login_duration:.2f}s)")

        # 3. 获取用户信息
        performance_metrics.start_timer("get_user_info")

        response = await api_client.get("/api/v1/users/me", headers=headers)
        assert response.status_code == 200
        profile = response.json()
        assert profile["username"] == user_data["username"]

        info_duration = performance_metrics.end_timer("get_user_info")
        print(f"✅ 获取用户信息完成 ({info_duration:.2f}s)")

        # 4. 查看即将到来的比赛
        performance_metrics.start_timer("get_upcoming_matches")

        # 先创建测试数据
        _teams = await test_data_loader.create_teams()
        _matches = await test_data_loader.create_matches()

        response = await api_client.get("/api/v1/matches/upcoming", headers=headers)
        assert response.status_code == 200
        matches_data = response.json()
        assert "data" in matches_data
        assert len(matches_data["data"]) > 0

        matches_duration = performance_metrics.end_timer("get_upcoming_matches")
        print(f"✅ 获取比赛列表完成 ({matches_duration:.2f}s)")

        # 5. 获取特定比赛详情
        performance_metrics.start_timer("get_match_details")

        match_id = matches_data["data"][0]["id"]
        response = await api_client.get(f"/api/v1/matches/{match_id}", headers=headers)
        assert response.status_code == 200
        match_details = response.json()
        assert match_details["id"] == match_id
        assert match_details["status"] == "UPCOMING"

        details_duration = performance_metrics.end_timer("get_match_details")
        print(f"✅ 获取比赛详情完成 ({details_duration:.2f}s)")

        # 6. 创建预测
        performance_metrics.start_timer("create_prediction")

        prediction_data = {
            "match_id": match_id,
            "prediction": "HOME_WIN",
            "confidence": 0.85,
        }

        response = await api_client.post(
            "/api/v1/predictions", json=prediction_data, headers=headers
        )
        assert response.status_code == 201, f"创建预测失败: {response.text}"
        _prediction = response.json()
        assert prediction["match_id"] == match_id
        assert prediction["prediction"] == "HOME_WIN"
        assert prediction["confidence"] == 0.85

        prediction_duration = performance_metrics.end_timer("create_prediction")
        print(f"✅ 创建预测完成 ({prediction_duration:.2f}s)")

        # 7. 验证预测已保存
        performance_metrics.start_timer("verify_prediction")

        response = await api_client.get(f"/api/v1/predictions/{prediction['id']}", headers=headers)
        assert response.status_code == 200
        saved_prediction = response.json()
        assert saved_prediction["id"] == prediction["id"]
        assert saved_prediction["prediction"] == "HOME_WIN"

        verify_duration = performance_metrics.end_timer("verify_prediction")
        print(f"✅ 验证预测完成 ({verify_duration:.2f}s)")

        # 8. 获取用户预测历史
        performance_metrics.start_timer("get_prediction_history")

        response = await api_client.get("/api/v1/users/me/predictions", headers=headers)
        assert response.status_code == 200
        history = response.json()
        assert "data" in history
        assert len(history["data"]) >= 1
        assert any(p["id"] == prediction["id"] for p in history["data"])

        history_duration = performance_metrics.end_timer("get_prediction_history")
        print(f"✅ 获取预测历史完成 ({history_duration:.2f}s)")

        # 9. 获取用户统计信息
        performance_metrics.start_timer("get_user_stats")

        response = await api_client.get("/api/v1/users/me/statistics", headers=headers)
        assert response.status_code == 200
        _stats = response.json()
        assert "total_predictions" in stats
        assert stats["total_predictions"] >= 1

        stats_duration = performance_metrics.end_timer("get_user_stats")
        print(f"✅ 获取统计信息完成 ({stats_duration:.2f}s)")

        # 10. 性能断言
        total_time = (
            performance_metrics.get_duration("user_registration")
            + performance_metrics.get_duration("user_login")
            + performance_metrics.get_duration("get_upcoming_matches")
            + performance_metrics.get_duration("create_prediction")
        )

        print("\n📊 流程性能指标:")
        print(f"  - 注册时间: {performance_metrics.get_duration('user_registration'):.2f}s")
        print(f"  - 登录时间: {performance_metrics.get_duration('user_login'):.2f}s")
        print(f"  - 获取比赛: {performance_metrics.get_duration('get_upcoming_matches'):.2f}s")
        print(f"  - 创建预测: {performance_metrics.get_duration('create_prediction'):.2f}s")
        print(f"  - 总流程时间: {total_time:.2f}s")

        # 关键路径性能要求
        assert total_time < 10.0, f"完整流程耗时过长: {total_time:.2f}s"
        assert performance_metrics.get_duration("create_prediction") < 2.0, "创建预测耗时过长"

    @pytest.mark.asyncio
    async def test_multiple_predictions_flow(
        self, api_client: AsyncClient, test_data_loader, user_headers
    ):
        """测试用户创建多个预测的流程"""
        # 准备测试数据
        _teams = await test_data_loader.create_teams()

        # 创建多个即将到来的比赛
        matches_data = []
        for i in range(5):
            match_data = {
                "home_team_id": teams[i % len(teams)]["id"],
                "away_team_id": teams[(i + 1) % len(teams)]["id"],
                "match_date": (datetime.now(timezone.utc) + timedelta(days=i + 1)).isoformat(),
                "competition": "E2E Multi League",
                "season": "2024/2025",
                "status": "UPCOMING",
            }
            matches_data.append(match_data)

        # 使用管理员权限创建比赛
        admin_token = (
            await api_client.post(
                "/api/v1/auth/login",
                _data={"username": "e2e_admin", "password": "E2EAdminPass123!"},
            )
        ).json()["access_token"]
        admin_headers = {"Authorization": f"Bearer {admin_token}"}

        created_matches = []
        for match_data in matches_data:
            response = await api_client.post(
                "/api/v1/matches", json=match_data, headers=admin_headers
            )
            if response.status_code == 201:
                created_matches.append(response.json())

        assert len(created_matches) >= 3, "需要至少3场比赛进行测试"

        # 批量创建预测
        predictions = []
        for i, match in enumerate(created_matches[:3]):
            prediction_types = ["HOME_WIN", "DRAW", "AWAY_WIN"]
            pred_data = {
                "match_id": match["id"],
                "prediction": prediction_types[i % 3],
                "confidence": 0.6 + (i * 0.1),
            }

            response = await api_client.post(
                "/api/v1/predictions", json=pred_data, headers=user_headers
            )
            assert response.status_code == 201, f"创建预测 {i} 失败: {response.text}"
            predictions.append(response.json())

        # 验证所有预测都已创建
        assert len(predictions) == 3

        # 获取用户预测列表
        response = await api_client.get("/api/v1/users/me/predictions", headers=user_headers)
        assert response.status_code == 200
        user_predictions = response.json()["data"]

        # 验证新创建的预测都在列表中
        prediction_ids = {p["id"] for p in predictions}
        user_prediction_ids = {p["id"] for p in user_predictions}
        assert prediction_ids.issubset(user_prediction_ids)

        # 测试分页
        response = await api_client.get(
            "/api/v1/users/me/predictions?page=1&size=2", headers=user_headers
        )
        assert response.status_code == 200
        paginated = response.json()
        assert len(paginated["data"]) == 2
        assert paginated["pagination"]["total"] >= 3

    @pytest.mark.asyncio
    async def test_prediction_update_flow(
        self, api_client: AsyncClient, test_data_loader, user_headers
    ):
        """测试预测更新流程（在比赛开始前修改预测）"""
        # 创建测试数据
        _teams = await test_data_loader.create_teams()
        _matches = await test_data_loader.create_matches()

        # 选择一个未来的比赛
        upcoming_match = None
        for match in matches:
            if match["status"] == "UPCOMING":
                upcoming_match = match
                break

        assert upcoming_match is not None, "需要找到即将到来的比赛"

        # 创建预测
        pred_data = {
            "match_id": upcoming_match["id"],
            "prediction": "HOME_WIN",
            "confidence": 0.75,
        }

        response = await api_client.post(
            "/api/v1/predictions", json=pred_data, headers=user_headers
        )
        assert response.status_code == 201
        _prediction = response.json()

        # 等待一段时间后更新预测（模拟用户改变主意）
        await asyncio.sleep(0.1)

        # 更新预测
        update_data = {"prediction": "DRAW", "confidence": 0.80}

        response = await api_client.patch(
            f"/api/v1/predictions/{prediction['id']}",
            json=update_data,
            headers=user_headers,
        )
        assert response.status_code == 200, f"更新预测失败: {response.text}"
        updated_prediction = response.json()
        assert updated_prediction["prediction"] == "DRAW"
        assert updated_prediction["confidence"] == 0.80

        # 验证更新后的预测
        response = await api_client.get(
            f"/api/v1/predictions/{prediction['id']}", headers=user_headers
        )
        assert response.status_code == 200
        final_prediction = response.json()
        assert final_prediction["prediction"] == "DRAW"

        # 检查预测历史（如果有审计功能）
        response = await api_client.get(
            f"/api/v1/predictions/{prediction['id']}/history", headers=user_headers
        )
        # 根据实际API调整断言
        if response.status_code == 200:
            history = response.json()
            assert len(history) >= 1

    @pytest.mark.asyncio
    async def test_invalid_prediction_scenarios(
        self, api_client: AsyncClient, user_headers, test_data_loader
    ):
        """测试各种无效预测场景"""
        _teams = await test_data_loader.create_teams()
        _matches = await test_data_loader.create_matches()

        # 测试1: 对已完成的比赛创建预测
        completed_match = None
        for match in matches:
            if match["status"] == "COMPLETED":
                completed_match = match
                break

        if completed_match:
            pred_data = {
                "match_id": completed_match["id"],
                "prediction": "HOME_WIN",
                "confidence": 0.75,
            }

            response = await api_client.post(
                "/api/v1/predictions", json=pred_data, headers=user_headers
            )
            assert response.status_code == 400, "应该不允许对已完成的比赛创建预测"

        # 测试2: 重复预测同一比赛
        upcoming_match = None
        for match in matches:
            if match["status"] == "UPCOMING":
                upcoming_match = match
                break

        if upcoming_match:
            pred_data = {
                "match_id": upcoming_match["id"],
                "prediction": "HOME_WIN",
                "confidence": 0.75,
            }

            # 第一次预测
            response1 = await api_client.post(
                "/api/v1/predictions", json=pred_data, headers=user_headers
            )
            assert response1.status_code == 201

            # 第二次预测同一比赛
            response2 = await api_client.post(
                "/api/v1/predictions", json=pred_data, headers=user_headers
            )
            assert response2.status_code == 400, "不允许重复预测"

        # 测试3: 无效的置信度
        if upcoming_match:
            invalid_pred_data = {
                "match_id": upcoming_match["id"],
                "prediction": "HOME_WIN",
                "confidence": 1.5,  # 超出范围
            }

            response = await api_client.post(
                "/api/v1/predictions", json=invalid_pred_data, headers=user_headers
            )
            assert response.status_code == 422, "置信度应该在0-1之间"

        # 测试4: 无效的预测类型
        if upcoming_match:
            invalid_pred_data = {
                "match_id": upcoming_match["id"],
                "prediction": "INVALID_TYPE",
                "confidence": 0.75,
            }

            response = await api_client.post(
                "/api/v1/predictions", json=invalid_pred_data, headers=user_headers
            )
            assert response.status_code == 422, "预测类型无效"

    @pytest.mark.asyncio
    async def test_concurrent_predictions(
        self, api_client: AsyncClient, test_data_loader, performance_metrics
    ):
        """测试并发创建预测的性能"""
        # 准备测试数据
        _teams = await test_data_loader.create_teams()

        # 创建多个用户
        users = []
        for i in range(5):
            user_data = {
                "username": f"concurrent_user_{i}",
                "email": f"concurrent{i}@example.com",
                "password": "ConcurrentPass123!",
            }
            response = await api_client.post("/api/v1/auth/register", json=user_data)
            if response.status_code == 201:
                users.append(user_data)

        # 登录所有用户
        user_tokens = []
        for user in users:
            login_data = {"username": user["username"], "password": user["password"]}
            response = await api_client.post("/api/v1/auth/login", _data=login_data)
            if response.status_code == 200:
                user_tokens.append(response.json()["access_token"])

        assert len(user_tokens) >= 3, "至少需要3个用户进行并发测试"

        # 创建比赛
        matches_data = []
        for i in range(3):
            match_data = {
                "home_team_id": teams[i]["id"],
                "away_team_id": teams[i + 1]["id"],
                "match_date": (datetime.now(timezone.utc) + timedelta(days=i + 1)).isoformat(),
                "competition": "Concurrent League",
                "season": "2024/2025",
                "status": "UPCOMING",
            }
            matches_data.append(match_data)

        # 使用管理员创建比赛
        admin_token = (
            await api_client.post(
                "/api/v1/auth/login",
                _data={"username": "e2e_admin", "password": "E2EAdminPass123!"},
            )
        ).json()["access_token"]
        admin_headers = {"Authorization": f"Bearer {admin_token}"}

        created_matches = []
        for match_data in matches_data:
            response = await api_client.post(
                "/api/v1/matches", json=match_data, headers=admin_headers
            )
            if response.status_code == 201:
                created_matches.append(response.json())

        # 并发创建预测
        performance_metrics.start_timer("concurrent_predictions")

        async def create_prediction_for_user(token, match):
            headers = {"Authorization": f"Bearer {token}"}
            pred_data = {
                "match_id": match["id"],
                "prediction": "HOME_WIN",
                "confidence": 0.75,
            }
            return await api_client.post("/api/v1/predictions", json=pred_data, headers=headers)

        # 并发执行
        tasks = []
        for i, token in enumerate(user_tokens[:3]):
            for j, match in enumerate(created_matches):
                tasks.append(create_prediction_for_user(token, match))

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 验证结果
        success_count = sum(
            1
            for r in results
            if isinstance(r, object) and hasattr(r, "status_code") and r.status_code == 201
        )
        total_predictions = len(tasks)

        concurrent_duration = performance_metrics.end_timer("concurrent_predictions")
        print(
            f"✅ 并发预测完成: {success_count}/{total_predictions} 成功 ({concurrent_duration:.2f}s)"
        )

        # 性能断言
        assert success_count >= total_predictions * 0.8, "并发成功率应该至少80%"
        assert concurrent_duration < 5.0, "并发预测应该快速完成"
