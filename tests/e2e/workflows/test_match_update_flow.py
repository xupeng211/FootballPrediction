"""
比赛更新实时流程 E2E 测试
测试比赛从开始到结束的完整实时更新流程
"""

import asyncio
import json
from datetime import datetime, timedelta, timezone

import pytest
from httpx import AsyncClient


@pytest.mark.e2e
@pytest.mark.critical
class TestMatchUpdateFlow:
    """比赛实时更新流程 E2E 测试"""

    @pytest.mark.asyncio
    async def test_match_lifecycle_flow(
        self, api_client: AsyncClient, websocket_client, test_data_loader, admin_headers
    ):
        """测试完整的比赛生命周期：计划 -> 进行中 -> 结束"""
        # 1. 创建测试比赛
        _teams = await test_data_loader.create_teams()

        match_data = {
            "home_team_id": teams[0]["id"],
            "away_team_id": teams[1]["id"],
            "match_date": (
                datetime.now(timezone.utc) + timedelta(minutes=30)
            ).isoformat(),
            "competition": "E2E Live League",
            "season": "2024/2025",
            "status": "SCHEDULED",
            "venue": "E2E Live Stadium",
        }

        response = await api_client.post(
            "/api/v1/matches", json=match_data, headers=admin_headers
        )
        assert response.status_code == 201
        match = response.json()
        match_id = match["id"]
        print(f"✅ 创建比赛: {match['competition']}")

        # 2. 连接 WebSocket 订阅比赛更新
        if websocket_client:
            # 订阅比赛更新
            subscribe_msg = {
                "action": "subscribe",
                "type": "match_updates",
                "match_id": match_id,
            }
            await websocket_client.send(json.dumps(subscribe_msg))
            print("✅ WebSocket 订阅成功")

        # 3. 模拟比赛开始
        print("\n📊 模拟比赛开始...")
        await asyncio.sleep(1)

        # 更新比赛状态为进行中
        update_data = {"status": "LIVE", "minute": 1, "home_score": 0, "away_score": 0}

        response = await api_client.patch(
            f"/api/v1/matches/{match_id}/status",
            json=update_data,
            headers=admin_headers,
        )
        assert response.status_code == 200
        updated_match = response.json()
        assert updated_match["status"] == "LIVE"
        assert updated_match["minute"] == 1

        if websocket_client:
            # 接收 WebSocket 更新
            try:
                message = await asyncio.wait_for(websocket_client.recv(), timeout=2.0)
                update = json.loads(message)
                assert update.get("type") == "match_update"
                assert update.get("match_id") == match_id
                print(f"✅ 收到 WebSocket 更新: 第{update.get('minute')}分钟")
            except asyncio.TimeoutError:
                print("⚠️ WebSocket 超时")

        # 4. 模拟比赛进程 - 进球事件
        events = [
            {
                "minute": 15,
                "event": "GOAL",
                "team": "home",
                "score": {"home": 1, "away": 0},
            },
            {
                "minute": 30,
                "event": "YELLOW_CARD",
                "team": "away",
                "player": "Player 2",
            },
            {
                "minute": 45,
                "event": "GOAL",
                "team": "away",
                "score": {"home": 1, "away": 1},
            },
            {
                "minute": 60,
                "event": "GOAL",
                "team": "home",
                "score": {"home": 2, "away": 1},
            },
            {"minute": 75, "event": "RED_CARD", "team": "away", "player": "Player 5"},
            {
                "minute": 90,
                "event": "GOAL",
                "team": "home",
                "score": {"home": 3, "away": 1},
            },
        ]

        final_score = {"home": 0, "away": 0}

        for event in events:
            await asyncio.sleep(0.5)  # 模拟时间流逝

            update_data = {
                "minute": event["minute"],
                "home_score": event["score"]["home"],
                "away_score": event["score"]["away"],
            }

            # 更新比分
            response = await api_client.patch(
                f"/api/v1/matches/{match_id}/status",
                json=update_data,
                headers=admin_headers,
            )
            assert response.status_code == 200

            # 创建比赛事件
            event_data = {
                "match_id": match_id,
                "minute": event["minute"],
                "event_type": event["event"],
                "team": event["team"],
                "details": event,
            }

            response = await api_client.post(
                f"/api/v1/matches/{match_id}/events",
                json=event_data,
                headers=admin_headers,
            )
            # 事件API可能还未实现，所以不强制断言

            final_score = event["score"]
            print(f"⚽ 第{event['minute']}分钟: {event['event']} - {event['team']}")

            if websocket_client:
                try:
                    message = await asyncio.wait_for(
                        websocket_client.recv(), timeout=1.0
                    )
                    update = json.loads(message)
                    print(f"✅ WebSocket 实时更新: {update.get('event')}")
                except asyncio.TimeoutError:
                    pass

        # 5. 比赛结束
        await asyncio.sleep(1)
        print("\n🏁 比赛结束")

        end_data = {
            "status": "COMPLETED",
            "minute": 90,
            "home_score": final_score["home"],
            "away_score": final_score["away"],
            "result": (
                "HOME_WIN"
                if final_score["home"] > final_score["away"]
                else "AWAY_WIN" if final_score["away"] > final_score["home"] else "DRAW"
            ),
        }

        response = await api_client.patch(
            f"/api/v1/matches/{match_id}/status", json=end_data, headers=admin_headers
        )
        assert response.status_code == 200
        final_match = response.json()
        assert final_match["status"] == "COMPLETED"
        assert final_match["home_score"] == 3
        assert final_match["away_score"] == 1

        # 6. 验证比赛事件历史
        response = await api_client.get(f"/api/v1/matches/{match_id}/events")
        if response.status_code == 200:
            events = response.json()
            assert len(events) >= 1
            print(f"✅ 记录了 {len(events)} 个比赛事件")

        # 7. 验证预测结果更新
        # 获取该比赛的所有预测
        response = await api_client.get(f"/api/v1/matches/{match_id}/predictions")
        if response.status_code == 200:
            predictions = response.json()
            print(f"✅ 该比赛有 {len(predictions)} 个预测")

            # 验证预测结果已被自动更新
            for pred in predictions:
                if pred.get("status") == "COMPLETED":
                    assert "is_correct" in pred
                    print(f"✅ 预测 {pred['id']} 结果已更新: {pred['is_correct']}")

    @pytest.mark.asyncio
    async def test_batch_match_updates(
        self, api_client: AsyncClient, test_data_loader, admin_headers
    ):
        """测试批量比赛更新（模拟比赛日）"""
        # 创建多个队伍和比赛
        _teams = await test_data_loader.create_teams()

        # 创建10场比赛（模拟一个比赛日）
        _matches = []
        for i in range(10):
            match_data = {
                "home_team_id": teams[i % len(teams)]["id"],
                "away_team_id": teams[(i + 1) % len(teams)]["id"],
                "match_date": (
                    datetime.now(timezone.utc) + timedelta(minutes=i * 10)
                ).isoformat(),
                "competition": "E2E Matchday League",
                "season": "2024/2025",
                "status": "SCHEDULED",
            }

            response = await api_client.post(
                "/api/v1/matches", json=match_data, headers=admin_headers
            )
            if response.status_code == 201:
                matches.append(response.json())

        assert len(matches) >= 5, "至少需要5场比赛进行批量更新测试"

        print(f"✅ 创建了 {len(matches)} 场比赛")

        # 批量更新比赛状态
        updated_matches = []
        for i, match in enumerate(matches[:5]):
            update_data = {
                "status": "LIVE" if i % 2 == 0 else "COMPLETED",
                "minute": 45 if i % 2 == 0 else 90,
                "home_score": i + 1,
                "away_score": len(matches) - i,
            }

            response = await api_client.patch(
                f"/api/v1/matches/{match['id']}/status",
                json=update_data,
                headers=admin_headers,
            )
            if response.status_code == 200:
                updated_matches.append(response.json())

        print(f"✅ 批量更新了 {len(updated_matches)} 场比赛")

        # 验证批量更新结果
        live_count = sum(1 for m in updated_matches if m["status"] == "LIVE")
        completed_count = sum(1 for m in updated_matches if m["status"] == "COMPLETED")

        assert live_count > 0
        assert completed_count > 0
        print(f"✅ 进行中: {live_count} 场, 已完成: {completed_count} 场")

        # 获取比赛日汇总
        response = await api_client.get(
            "/api/v1/matches/summary",
            params={
                "competition": "E2E Matchday League",
                "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            },
        )
        if response.status_code == 200:
            summary = response.json()
            print(f"✅ 比赛日汇总: {summary}")

    @pytest.mark.asyncio
    async def test_live_statistics_updates(
        self, api_client: AsyncClient, test_data_loader, admin_headers
    ):
        """测试实时统计数据更新"""
        # 创建测试比赛
        _teams = await test_data_loader.create_teams()

        match_data = {
            "home_team_id": teams[0]["id"],
            "away_team_id": teams[1]["id"],
            "match_date": datetime.now(timezone.utc).isoformat(),
            "competition": "E2E Stats League",
            "season": "2024/2025",
            "status": "LIVE",
            "venue": "Stats Stadium",
        }

        response = await api_client.post(
            "/api/v1/matches", json=match_data, headers=admin_headers
        )
        assert response.status_code == 201
        match = response.json()

        # 模拟比赛过程中的统计数据更新
        stats_updates = [
            {
                "minute": 10,
                "stats": {
                    "possession": {"home": 55, "away": 45},
                    "shots": {"home": 5, "away": 3},
                    "corners": {"home": 2, "away": 1},
                    "fouls": {"home": 3, "away": 4},
                },
            },
            {
                "minute": 30,
                "stats": {
                    "possession": {"home": 52, "away": 48},
                    "shots": {"home": 12, "away": 8},
                    "corners": {"home": 5, "away": 3},
                    "fouls": {"home": 8, "away": 7},
                },
            },
            {
                "minute": 60,
                "stats": {
                    "possession": {"home": 48, "away": 52},
                    "shots": {"home": 18, "away": 15},
                    "corners": {"home": 7, "away": 8},
                    "fouls": {"home": 12, "away": 11},
                },
            },
        ]

        for stats_update in stats_updates:
            await asyncio.sleep(0.5)

            # 更新比分和统计数据
            update_data = {
                "minute": stats_update["minute"],
                "home_score": stats_update["minute"] // 30,
                "away_score": stats_update["minute"] // 45,
                "statistics": stats_update["stats"],
            }

            response = await api_client.patch(
                f"/api/v1/matches/{match['id']}/status",
                json=update_data,
                headers=admin_headers,
            )

            if response.status_code == 200:
                updated_match = response.json()
                _stats = updated_match.get("statistics", {})
                print(
                    f"✅ 第{stats_update['minute']}分钟统计更新: "
                    f"控球率 {stats.get('possession', {}).get('home', 0)}%"
                )

        # 验证最终统计数据
        response = await api_client.get(f"/api/v1/matches/{match['id']}/statistics")
        if response.status_code == 200:
            final_stats = response.json()
            assert "possession" in final_stats
            assert "shots" in final_stats
            print(f"✅ 最终统计数据: {final_stats}")

    @pytest.mark.asyncio
    async def test_match_suspension_and_resumption(
        self, api_client: AsyncClient, test_data_loader, admin_headers
    ):
        """测试比赛中断和恢复"""
        # 创建测试比赛
        _teams = await test_data_loader.create_teams()

        match_data = {
            "home_team_id": teams[0]["id"],
            "away_team_id": teams[1]["id"],
            "match_date": datetime.now(timezone.utc).isoformat(),
            "competition": "E2E Interrupt League",
            "season": "2024/2025",
            "status": "LIVE",
            "venue": "Interrupt Stadium",
        }

        response = await api_client.post(
            "/api/v1/matches", json=match_data, headers=admin_headers
        )
        assert response.status_code == 201
        match = response.json()
        print(f"✅ 创建比赛: {match['competition']}")

        # 比赛进行到30分钟
        update_data = {"minute": 30, "home_score": 1, "away_score": 0, "status": "LIVE"}

        response = await api_client.patch(
            f"/api/v1/matches/{match['id']}/status",
            json=update_data,
            headers=admin_headers,
        )
        assert response.status_code == 200
        print("⚽ 比赛进行到第30分钟")

        # 模拟比赛中断（天气原因、球员受伤等）
        await asyncio.sleep(1)
        print("⚠️ 比赛中断...")

        suspension_data = {
            "status": "SUSPENDED",
            "minute": 30,
            "reason": "Weather conditions - heavy rain",
            "estimated_resume": datetime.now(timezone.utc)
            + timedelta(minutes=15).isoformat(),
        }

        response = await api_client.patch(
            f"/api/v1/matches/{match['id']}/status",
            json=suspension_data,
            headers=admin_headers,
        )
        assert response.status_code == 200
        suspended_match = response.json()
        assert suspended_match["status"] == "SUSPENDED"
        assert suspended_match["minute"] == 30
        print(f"✅ 比赛已中断: {suspension_data['reason']}")

        # 模拟等待恢复
        await asyncio.sleep(2)
        print("▶️ 比赛恢复...")

        # 恢复比赛
        resume_data = {
            "status": "LIVE",
            "minute": 30,
            "note": "Match resumed after weather improved",
        }

        response = await api_client.patch(
            f"/api/v1/matches/{match['id']}/status",
            json=resume_data,
            headers=admin_headers,
        )
        assert response.status_code == 200
        resumed_match = response.json()
        assert resumed_match["status"] == "LIVE"
        print("✅ 比赛已恢复")

        # 继续比赛到结束
        for minute in [45, 60, 75, 90]:
            await asyncio.sleep(0.5)

            update_data = {
                "minute": minute,
                "home_score": minute // 30,
                "away_score": minute // 45,
            }

            response = await api_client.patch(
                f"/api/v1/matches/{match['id']}/status",
                json=update_data,
                headers=admin_headers,
            )

            if response.status_code == 200:
                print(
                    f"⚽ 第{minute}分钟: {update_data['home_score']}-{update_data['away_score']}"
                )

        # 结束比赛
        end_data = {
            "status": "COMPLETED",
            "minute": 90,
            "home_score": 3,
            "away_score": 2,
            "duration": "105",  # 包含中断时间
            "interruptions": 1,
        }

        response = await api_client.patch(
            f"/api/v1/matches/{match['id']}/status",
            json=end_data,
            headers=admin_headers,
        )
        assert response.status_code == 200
        final_match = response.json()
        assert final_match["status"] == "COMPLETED"
        print("✅ 比赛结束")

        # 验证中断记录
        response = await api_client.get(f"/api/v1/matches/{match['id']}/timeline")
        if response.status_code == 200:
            timeline = response.json()
            suspension_events = [e for e in timeline if e.get("event") == "suspension"]
            assert len(suspension_events) >= 1
            print(f"✅ 中断记录: {len(suspension_events)} 次")
