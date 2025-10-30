"""
批量数据处理流程 E2E 测试
测试批量导入预测,数据导出等批量处理功能
"""

import asyncio
import csv
import io
import json
from datetime import datetime, timedelta, timezone

import pytest
from httpx import AsyncClient


@pytest.mark.e2e
@pytest.mark.regression
class TestBatchProcessingFlow:
    """批量数据处理流程 E2E 测试"""

    @pytest.mark.asyncio
    async def test_batch_prediction_import(
        self,
        api_client: AsyncClient,
        test_data_loader,
        analyst_headers,
        performance_metrics,
    ):
        """测试批量导入预测"""
        # 1. 准备测试数据
        _teams = await test_data_loader.create_teams()
        _matches = await test_data_loader.create_matches()

        # 创建批量预测数据 (CSV格式)
        batch_predictions = []
        for i, match in enumerate(matches[:10]):  # 10场比赛
            for j in range(3):  # 每场比赛3个不同的预测
                pred = {
                    "match_id": match["id"],
                    "prediction": ["HOME_WIN", "DRAW", "AWAY_WIN"][j],
                    "confidence": round(0.5 + (i * 0.05) + (j * 0.1), 2),
                    "notes": f"Batch prediction {i}-{j}",
                }
                batch_predictions.append(pred)

        # 创建CSV文件
        csv_file = io.StringIO()
        fieldnames = ["match_id", "prediction", "confidence", "notes"]
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(batch_predictions)
        csv_content = csv_file.getvalue()

        print(f"✅ 准备了 {len(batch_predictions)} 个批量预测")

        # 2. 上传批量预测文件
        performance_metrics.start_timer("batch_upload")

        files = {"file": ("batch_predictions.csv", csv_content, "text/csv")}

        response = await api_client.post(
            "/api/v1/batch/predictions/upload", files=files, headers=analyst_headers
        )

        upload_duration = performance_metrics.end_timer("batch_upload")
        print(f"✅ 文件上传完成 ({upload_duration:.2f}s)")

        assert response.status_code == 202, f"批量上传失败: {response.text}"
        batch_info = response.json()
        assert "batch_id" in batch_info
        assert "status" in batch_info
        batch_id = batch_info["batch_id"]

        print(f"✅ 批量任务已创建: {batch_id}")

        # 3. 监控批量处理进度
        performance_metrics.start_timer("batch_processing")

        max_wait = 60  # 最多等待60秒
        wait_interval = 2
        elapsed = 0

        while elapsed < max_wait:
            await asyncio.sleep(wait_interval)
            elapsed += wait_interval

            response = await api_client.get(
                f"/api/v1/batch/predictions/{batch_id}/status", headers=analyst_headers
            )

            if response.status_code == 200:
                status = response.json()
                print(
                    f"📊 处理进度: {status.get('processed', 0)}/{status.get('total', 0)} "
                    f"({status.get('status', 'unknown')})"
                )

                if status.get("status") == "COMPLETED":
                    break
                elif status.get("status") == "FAILED":
                    assert False, f"批量处理失败: {status.get('error', 'Unknown error')}"

        processing_duration = performance_metrics.end_timer("batch_processing")
        print(f"✅ 批量处理完成 ({processing_duration:.2f}s)")

        # 4. 获取批量处理结果
        response = await api_client.get(
            f"/api/v1/batch/predictions/{batch_id}/results", headers=analyst_headers
        )

        assert response.status_code == 200
        results = response.json()
        assert "summary" in results
        assert "details" in results

        summary = results["summary"]
        print("✅ 处理结果摘要:")
        print(f"   - 总数: {summary.get('total', 0)}")
        print(f"   - 成功: {summary.get('successful', 0)}")
        print(f"   - 失败: {summary.get('failed', 0)}")
        print(
            f"   - 成功率: {(summary.get('successful', 0) / max(summary.get('total', 1), 1) * 100):.1f}%"
        )

        # 验证成功处理的预测
        assert summary.get("successful", 0) > 0
        assert summary.get("failed", 0) < summary.get("total", 0) * 0.1  # 失败率应低于10%

        # 5. 验证预测已导入
        response = await api_client.get(
            "/api/v1/predictions",
            params={"batch_id": batch_id},
            headers=analyst_headers,
        )

        if response.status_code == 200:
            imported_predictions = response.json()
            assert len(imported_predictions.get("data", [])) >= summary.get("successful", 0)
            print(f"✅ 成功导入了 {len(imported_predictions.get('data', []))} 个预测")

        # 性能断言
        assert upload_duration < 10.0, "上传耗时过长"
        assert processing_duration < 120.0, "处理耗时过长"

    @pytest.mark.asyncio
    async def test_batch_data_export(
        self, api_client: AsyncClient, test_data_loader, analyst_headers
    ):
        """测试批量数据导出"""
        # 1. 准备测试数据
        _teams = await test_data_loader.create_teams()
        _matches = await test_data_loader.create_matches()

        # 创建一些预测数据
        user_token = (
            await api_client.post(
                "/api/v1/auth/login",
                _data={"username": "e2e_user", "password": "E2ETestPass123!"},
            )
        ).json()["access_token"]
        user_headers = {"Authorization": f"Bearer {user_token}"}

        for i, match in enumerate(matches[:5]):
            pred_data = {
                "match_id": match["id"],
                "prediction": "HOME_WIN" if i % 2 == 0 else "AWAY_WIN",
                "confidence": 0.7 + (i * 0.05),
            }
            await api_client.post("/api/v1/predictions", json=pred_data, headers=user_headers)

        # 2. 创建导出任务
        export_request = {
            "data_type": "predictions",
            "format": "csv",
            "filters": {
                "date_from": (datetime.now(timezone.utc) - timedelta(days=1)).isoformat(),
                "date_to": (datetime.now(timezone.utc) + timedelta(days=1)).isoformat(),
            },
            "fields": [
                "id",
                "match_id",
                "prediction",
                "confidence",
                "status",
                "created_at",
            ],
        }

        response = await api_client.post(
            "/api/v1/batch/export", json=export_request, headers=analyst_headers
        )

        assert response.status_code == 202, f"创建导出任务失败: {response.text}"
        export_info = response.json()
        assert "export_id" in export_info
        export_id = export_info["export_id"]
        print(f"✅ 导出任务已创建: {export_id}")

        # 3. 监控导出进度
        max_wait = 30
        wait_interval = 1
        elapsed = 0

        while elapsed < max_wait:
            await asyncio.sleep(wait_interval)
            elapsed += wait_interval

            response = await api_client.get(
                f"/api/v1/batch/export/{export_id}/status", headers=analyst_headers
            )

            if response.status_code == 200:
                status = response.json()
                if status.get("status") == "COMPLETED":
                    break
                elif status.get("status") == "FAILED":
                    assert False, f"导出失败: {status.get('error')}"

        # 4. 下载导出文件
        response = await api_client.get(
            f"/api/v1/batch/export/{export_id}/download", headers=analyst_headers
        )

        assert response.status_code == 200
        assert "text/csv" in response.headers.get("content-type", "")

        # 验证CSV内容
        csv_content = response.text
        lines = csv_content.strip().split("\n")
        assert len(lines) > 1  # 至少有标题行和一行数据

        print(f"✅ 导出文件下载成功 ({len(lines)} 行)")

    @pytest.mark.asyncio
    async def test_bulk_user_import(
        self, api_client: AsyncClient, admin_headers, performance_metrics
    ):
        """测试批量用户导入"""
        # 1. 创建批量用户数据
        users_data = []
        for i in range(50):
            _user = {
                "username": f"bulk_user_{i:03d}",
                "email": f"bulkuser{i:03d}@example.com",
                "password": "BulkUser123!",
                "first_name": f"User{i}",
                "last_name": f"Test{i}",
                "role": "user" if i % 10 != 0 else "analyst",
            }
            users_data.append(user)

        # 创建JSON格式数据
        json_content = json.dumps(
            {
                "users": users_data,
                "options": {
                    "send_welcome_email": False,
                    "require_password_change": False,
                },
            }
        )

        print(f"✅ 准备导入 {len(users_data)} 个用户")

        # 2. 上传批量用户文件
        performance_metrics.start_timer("bulk_import")

        files = {"file": ("bulk_users.json", json_content, "application/json")}

        response = await api_client.post(
            "/api/v1/batch/users/import", files=files, headers=admin_headers
        )

        import_duration = performance_metrics.end_timer("bulk_import")
        print(f"✅ 用户批量导入开始 ({import_duration:.2f}s)")

        assert response.status_code == 202
        import_info = response.json()
        import_id = import_info["import_id"]

        # 3. 监控导入进度
        processed = 0
        total = len(users_data)
        wait_time = 0

        while processed < total and wait_time < 60:
            await asyncio.sleep(2)
            wait_time += 2

            response = await api_client.get(
                f"/api/v1/batch/users/{import_id}/status", headers=admin_headers
            )

            if response.status_code == 200:
                status = response.json()
                processed = status.get("processed", 0)
                print(f"📊 导入进度: {processed}/{total} ({processed / total * 100:.1f}%)")

                if status.get("status") == "COMPLETED":
                    break

        # 4. 获取导入结果
        response = await api_client.get(
            f"/api/v1/batch/users/{import_id}/results", headers=admin_headers
        )

        assert response.status_code == 200
        results = response.json()
        summary = results.get("summary", {})

        print("✅ 用户导入完成:")
        print(f"   - 成功: {summary.get('successful', 0)}")
        print(f"   - 失败: {summary.get('failed', 0)}")
        print(f"   - 跳过: {summary.get('skipped', 0)}")

        # 验证导入结果
        assert summary.get("successful", 0) >= total * 0.95  # 至少95%成功

    @pytest.mark.asyncio
    async def test_scheduled_batch_job(
        self, api_client: AsyncClient, test_data_loader, analyst_headers
    ):
        """测试定时批量任务（如每日统计报告）"""
        # 1. 创建定时任务
        job_config = {
            "name": "daily_statistics_report",
            "type": "report_generation",
            "schedule": "0 2 * * *",  # 每天凌晨2点
            "parameters": {
                "report_type": "daily",
                "recipients": ["admin@example.com", "analyst@example.com"],
                "format": "pdf",
                "include_charts": True,
            },
        }

        response = await api_client.post(
            "/api/v1/batch/schedule", json=job_config, headers=analyst_headers
        )

        if response.status_code == 201:
            job = response.json()
            job_id = job["id"]
            print(f"✅ 定时任务已创建: {job_id}")

            # 2. 获取任务列表
            response = await api_client.get("/api/v1/batch/schedule", headers=analyst_headers)

            if response.status_code == 200:
                jobs = response.json()
                assert any(j["id"] == job_id for j in jobs)
                print(f"✅ 找到 {len(jobs)} 个定时任务")

            # 3. 手动触发任务执行
            response = await api_client.post(
                f"/api/v1/batch/schedule/{job_id}/trigger", headers=analyst_headers
            )

            if response.status_code == 202:
                execution = response.json()
                execution_id = execution["execution_id"]
                print(f"✅ 任务执行已触发: {execution_id}")

                # 4. 监控执行状态
                for _ in range(30):  # 最多等待30秒
                    await asyncio.sleep(1)

                    response = await api_client.get(
                        f"/api/v1/batch/execution/{execution_id}",
                        headers=analyst_headers,
                    )

                    if response.status_code == 200:
                        exec_status = response.json()
                        if exec_status.get("status") == "COMPLETED":
                            print("✅ 任务执行完成")
                            break
                        elif exec_status.get("status") == "FAILED":
                            print(f"❌ 任务执行失败: {exec_status.get('error')}")
                            break

    @pytest.mark.asyncio
    async def test_bulk_notification_sending(
        self, api_client: AsyncClient, test_data_loader, admin_headers
    ):
        """测试批量发送通知"""
        # 1. 创建多个用户（模拟需要通知的用户）
        users = []
        for i in range(10):
            user_data = {
                "username": f"notify_user_{i}",
                "email": f"notifyuser{i}@example.com",
                "password": "NotifyPass123!",
                "notifications_enabled": True,
            }

            response = await api_client.post("/api/v1/auth/register", json=user_data)
            if response.status_code == 201:
                users.append(user_data)

        assert len(users) >= 5, "至少需要5个用户进行通知测试"

        # 2. 创建批量通知
        notification_data = {
            "title": "系统维护通知",
            "message": "系统将于今晚进行例行维护,预计耗时2小时",
            "type": "system",
            "priority": "normal",
            "channels": ["email", "in_app"],
            "send_immediately": True,
        }

        # 添加目标用户
        notification_data["recipients"] = [u["username"] for u in users[:5]]

        response = await api_client.post(
            "/api/v1/batch/notifications/send",
            json=notification_data,
            headers=admin_headers,
        )

        if response.status_code == 202:
            batch_info = response.json()
            batch_id = batch_info["batch_id"]
            print(f"✅ 批量通知任务已创建: {batch_id}")

            # 3. 监控发送状态
            max_wait = 30
            elapsed = 0

            while elapsed < max_wait:
                await asyncio.sleep(2)
                elapsed += 2

                response = await api_client.get(
                    f"/api/v1/batch/notifications/{batch_id}/status",
                    headers=admin_headers,
                )

                if response.status_code == 200:
                    status = response.json()
                    if status.get("status") == "COMPLETED":
                        break

            # 4. 获取发送结果
            response = await api_client.get(
                f"/api/v1/batch/notifications/{batch_id}/results", headers=admin_headers
            )

            if response.status_code == 200:
                results = response.json()
                summary = results.get("summary", {})
                print("✅ 通知发送结果:")
                print(f"   - 总数: {summary.get('total', 0)}")
                print(f"   - 成功: {summary.get('sent', 0)}")
                print(f"   - 失败: {summary.get('failed', 0)}")

                assert summary.get("sent", 0) > 0
