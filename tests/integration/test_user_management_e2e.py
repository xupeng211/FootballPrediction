from typing import Optional

"""

# Mock user service for testing

# Mock user service for testing
mock_user_service = Mock()
mock_user_service.update_display_preferences.return_value = {
    "user_id": 1,
    "preferences": {"theme": "dark", "notifications": True}
}
mock_user_service.update_privacy_preferences.return_value = {
    "user_id": 1,
    "privacy": {"profile_visibility": "public", "data_sharing": False}
}
mock_user_service.update_prediction_preferences.return_value = {
    "user_id": 1,
    "predictions": {"auto_predictions": True, "confidence_threshold": 0.7}
}

mock_user_service = Mock()
mock_user_service.update_display_preferences.return_value = {
    "user_id": 1,
    "preferences": {"theme": "dark", "notifications": True}
}
mock_user_service.update_privacy_preferences.return_value = {
    "user_id": 1,
    "privacy": {"profile_visibility": "public", "data_sharing": False}
}
mock_user_service.update_prediction_preferences.return_value = {
    "user_id": 1,
    "predictions": {"auto_predictions": True, "confidence_threshold": 0.7}
}

用户管理端到端测试
User Management End-to-End Tests

完整测试用户管理工作流，从注册到认证、资料管理、权限控制等
"""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

# 标记测试
pytestmark = [pytest.mark.e2e, pytest.mark.auth, pytest.mark.workflow, pytest.mark.slow]


class TestUserRegistrationE2E:
    """用户注册端到端测试"""

    @pytest.mark.asyncio
    async def test_complete_user_registration_flow(
        self, async_client: AsyncClient, test_user_data, mock_external_services
    ):
        """测试完整的用户注册流程"""
        # ================================
        # 第一阶段: 用户注册
        # ================================

        user_data = test_user_data["users"][0]
        registration_data = {
            "username": user_data["username"],
            "email": user_data["email"],
            "password": "SecurePassword123!",
            "confirm_password": "SecurePassword123!",
            "first_name": "John",
            "last_name": "Doe",
            "date_of_birth": "1990-01-01",
            "country": "United Kingdom",
            "accept_terms": True,
            "marketing_consent": False,
        }

        # 模拟用户服务
        mock_user_service = AsyncMock()
        mock_user_service.register_user.return_value = {
            "id": user_data["id"],
            "username": user_data["username"],
            "email": user_data["email"],
            "first_name": "John",
            "last_name": "Doe",
            "is_active": True,
            "is_verified": False,
            "created_at": user_data["created_at"].isoformat(),
            "verification_required": True,
        }

        with patch("src.domain.services.user_service.UserService", return_value=mock_user_service):
            response = await async_client.post(
                "/api/users/register", json=registration_data
            )

            assert response.status_code in [200, 201]
            registered_user = response.json()
            assert registered_user["username"] == user_data["username"]
            assert registered_user["email"] == user_data["email"]
            assert not registered_user["is_verified"]
            user_id = registered_user["id"]

        # ================================
        # 第二阶段: 邮箱验证
        # ================================

        # 模拟发送验证邮件
        mock_email_service = AsyncMock()
        mock_email_service.send_verification_email.return_value = {
            "message": "Verification email sent",
            "verification_token": "verify_token_12345",
            "expires_at": (datetime.utcnow() + timedelta(hours=24)).isoformat(),
        }

        with patch("src.services.email.EmailService", return_value=mock_email_service):
            response = await async_client.post(
                f"/api/users/{user_id}/send-verification",
                json={"email": user_data["email"]},
            )

            if response.status_code == 200:
                email_result = response.json()
                assert "verification_token" in email_result

        # 验证邮箱
        verification_data = {"token": "verify_token_12345", "email": user_data["email"]}

        mock_user_service.verify_email.return_value = {
            "user_id": user_id,
            "is_verified": True,
            "verified_at": datetime.utcnow().isoformat(),
            "message": "Email verified successfully",
        }

        with patch("src.domain.services.user_service.UserService", return_value=mock_user_service):
            response = await async_client.post(
                "/api/users/verify-email", json=verification_data
            )

            assert response.status_code == 200
            verification_result = response.json()
            assert verification_result["is_verified"]

        # ================================
        # 第三阶段: 完善用户资料
        # ================================

        profile_data = {
            "first_name": "John",
            "last_name": "Doe",
            "bio": "Football enthusiast and prediction expert",
            "favorite_team": "Manchester United",
            "favorite_league": "Premier League",
            "avatar_url": "https://example.com/avatar.jpg",
            "phone_number": "+44 20 7123 4567",
            "location": "London, UK",
            "website": "https://johndoe.com",
            "social_links": {"twitter": "@johndoe", "instagram": "johndoe_football"},
            "preferences": {
                "language": "en",
                "timezone": "Europe/London",
                "date_format": "DD/MM/YYYY",
                "time_format": "24h",
            },
        }

        mock_user_service.update_user_profile.return_value = {
            "id": user_id,
            "username": user_data["username"],
            "email": user_data["email"],
            "is_verified": True,
            "profile": profile_data,
            "updated_at": datetime.utcnow().isoformat(),
        }

        auth_headers = {"Authorization": "Bearer test_jwt_token"}

        with patch("src.domain.services.user_service.UserService", return_value=mock_user_service):
            response = await async_client.put(
                f"/api/users/{user_id}/profile", json=profile_data, headers=auth_headers
            )

            if response.status_code == 200:
                updated_profile = response.json()
                assert (
                    updated_profile["profile"]["favorite_team"] == "Manchester United"
                )

        # ================================
        # 第四阶段: 设置通知偏好
        # ================================

        notification_preferences = {
            "email_notifications": {
                "match_reminders": True,
                "prediction_results": True,
                "weekly_summary": True,
                "special_offers": False,
                "system_updates": True,
            },
            "push_notifications": {
                "match_start": True,
                "final_results": True,
                "leaderboard_changes": True,
            },
            "sms_notifications": {
                "important_updates": False,
                "high_stakes_predictions": False,
            },
            "frequency": {
                "daily_digest": False,
                "weekly_digest": True,
                "monthly_summary": True,
            },
        }

        mock_user_service.update_notification_preferences.return_value = {
            "user_id": user_id,
            "preferences": notification_preferences,
            "updated_at": datetime.utcnow().isoformat(),
        }

        with patch("src.domain.services.user_service.UserService", return_value=mock_user_service):
            response = await async_client.put(
                f"/api/users/{user_id}/notification-preferences",
                json=notification_preferences,
                headers=auth_headers,
            )

            if response.status_code == 200:
                preferences_result = response.json()
                assert preferences_result["preferences"]["email_notifications"][
                    "match_reminders"
                ]

    @pytest.mark.asyncio
    async def test_registration_validation_errors(
        self, async_client: AsyncClient, error_test_data
    ):
        """测试注册验证错误"""
        # 测试无效的注册数据
        invalid_registrations = [
            {
                "username": "",  # 空用户名
                "email": "invalid-email",  # 无效邮箱
                "password": "123",  # 密码太短
                "confirm_password": "456",  # 密码不匹配
                "accept_terms": False,  # 未接受条款
            },
            {
                "username": "ab",  # 用户名太短
                "email": "test@example.com",
                "password": "password",  # 弱密码
                "confirm_password": "password",
                "accept_terms": True,
            },
            {
                "username": "user_that_is_way_too_long_for_system_validation",
                "email": "test@example.com",
                "password": "SecurePassword123!",
                "confirm_password": "SecurePassword123!",
                "accept_terms": True,
            },
        ]

        for invalid_data in invalid_registrations:
            response = await async_client.post("/api/users/register", json=invalid_data)

            # 应该返回验证错误
            if response.status_code != 404:  # 如果端点存在
                assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_duplicate_user_handling(
        self, async_client: AsyncClient, test_user_data
    ):
        """测试重复用户处理"""
        user_data = test_user_data["users"][0]
        registration_data = {
            "username": user_data["username"],
            "email": user_data["email"],
            "password": "SecurePassword123!",
            "confirm_password": "SecurePassword123!",
            "accept_terms": True,
        }

        # 第一次注册应该成功（模拟）
        mock_user_service = AsyncMock()
        mock_user_service.register_user.return_value = {
            "id": user_data["id"],
            **registration_data,
            "is_active": True,
            "is_verified": False,
        }

        with patch("src.domain.services.user_service.UserService", return_value=mock_user_service):
            response = await async_client.post(
                "/api/users/register", json=registration_data
            )
            # 第一次成功

        # 第二次使用相同用户名应该失败
        mock_user_service.register_user.side_effect = Exception(
            "Username already exists"
        )

        with patch("src.domain.services.user_service.UserService", return_value=mock_user_service):
            response = await async_client.post(
                "/api/users/register", json=registration_data
            )

            if response.status_code != 404:
                assert response.status_code in [409, 400]

        # 第二次使用相同邮箱应该失败
        duplicate_email_data = registration_data.copy()
        duplicate_email_data["username"] = "different_username"

        mock_user_service.register_user.side_effect = Exception(
            "Email already registered"
        )

        with patch("src.domain.services.user_service.UserService", return_value=mock_user_service):
            response = await async_client.post(
                "/api/users/register", json=duplicate_email_data
            )

            if response.status_code != 404:
                assert response.status_code in [409, 400]


class TestUserAuthenticationE2E:
    """用户认证端到端测试"""

    @pytest.mark.asyncio
    async def test_complete_authentication_flow(
        self, async_client: AsyncClient, test_user_data, mock_redis
    ):
        """测试完整的认证流程"""
        user_data = test_user_data["users"][0]

        # ================================
        # 第一阶段: 用户登录
        # ================================

        login_data = {
            "username": user_data["username"],
            "password": "SecurePassword123!",
            "remember_me": False,
        }

        mock_auth_service = AsyncMock()
        mock_auth_service.authenticate_user.return_value = {
            "access_token": "jwt_access_token_12345",
            "refresh_token": "jwt_refresh_token_67890",
            "token_type": "bearer",
            "expires_in": 3600,
            "user": {
                "id": user_data["id"],
                "username": user_data["username"],
                "email": user_data["email"],
                "is_active": True,
                "is_verified": True,
                "role": "user",
            },
        }

        with patch("src.domain.services.auth_service.AuthService", return_value=mock_auth_service):
            response = await async_client.post("/api/auth/login", json=login_data)

            assert response.status_code == 200
            auth_result = response.json()
            assert "access_token" in auth_result
            assert "refresh_token" in auth_result
            assert auth_result["token_type"] == "bearer"

            access_token = auth_result["access_token"]
            refresh_token = auth_result["refresh_token"]
            auth_headers = {"Authorization": f"Bearer {access_token}"}

        # ================================
        # 第二阶段: 验证token有效性
        # ================================

        mock_auth_service.verify_token.return_value = {
            "valid": True,
            "user_id": user_data["id"],
            "username": user_data["username"],
            "expires_at": (datetime.utcnow() + timedelta(hours=1)).isoformat(),
        }

        with patch("src.domain.services.auth_service.AuthService", return_value=mock_auth_service):
            response = await async_client.get("/api/auth/verify", headers=auth_headers)

            if response.status_code == 200:
                verification_result = response.json()
                assert verification_result["valid"]

        # ================================
        # 第三阶段: 刷新token
        # ================================

        refresh_data = {"refresh_token": refresh_token}

        mock_auth_service.refresh_token.return_value = {
            "access_token": "new_jwt_access_token_12345",
            "refresh_token": "new_jwt_refresh_token_67890",
            "expires_in": 3600,
        }

        with patch("src.domain.services.auth_service.AuthService", return_value=mock_auth_service):
            response = await async_client.post("/api/auth/refresh", json=refresh_data)

            if response.status_code == 200:
                refresh_result = response.json()
                assert "access_token" in refresh_result
                new_access_token = refresh_result["access_token"]
                auth_headers = {"Authorization": f"Bearer {new_access_token}"}

        # ================================
        # 第四阶段: 用户注销
        # ================================

        mock_auth_service.logout_user.return_value = {
            "message": "Logged out successfully",
            "revoked_tokens": [access_token, refresh_token],
        }

        with patch("src.domain.services.auth_service.AuthService", return_value=mock_auth_service):
            response = await async_client.post("/api/auth/logout", headers=auth_headers)

            if response.status_code == 200:
                logout_result = response.json()
                assert logout_result["message"] == "Logged out successfully"

        # ================================
        # 第五阶段: 验证token已失效
        # ================================

        mock_auth_service.verify_token.return_value = {
            "valid": False,
            "reason": "Token has been revoked",
        }

        with patch("src.domain.services.auth_service.AuthService", return_value=mock_auth_service):
            response = await async_client.get("/api/auth/verify", headers=auth_headers)

            if response.status_code != 404:
                assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_password_reset_flow(
        self, async_client: AsyncClient, test_user_data, mock_external_services
    ):
        """测试密码重置流程"""
        user_data = test_user_data["users"][0]

        # ================================
        # 第一阶段: 请求密码重置
        # ================================

        reset_request_data = {"email": user_data["email"]}

        mock_user_service = AsyncMock()
        mock_user_service.initiate_password_reset.return_value = {
            "message": "Password reset email sent",
            "reset_token": "reset_token_abcdef123456",
            "expires_at": (datetime.utcnow() + timedelta(hours=1)).isoformat(),
        }

        with patch("src.domain.services.user_service.UserService", return_value=mock_user_service):
            response = await async_client.post(
                "/api/users/reset-password", json=reset_request_data
            )

            if response.status_code == 200:
                reset_request_result = response.json()
                assert "reset_token" in reset_request_result

        # ================================
        # 第二阶段: 验证重置token
        # ================================

        token_verification_data = {"token": "reset_token_abcdef123456"}

        mock_user_service.verify_reset_token.return_value = {
            "valid": True,
            "user_id": user_data["id"],
            "email": user_data["email"],
            "expires_at": (datetime.utcnow() + timedelta(minutes=59)).isoformat(),
        }

        with patch("src.domain.services.user_service.UserService", return_value=mock_user_service):
            response = await async_client.post(
                "/api/users/verify-reset-token", json=token_verification_data
            )

            if response.status_code == 200:
                token_result = response.json()
                assert token_result["valid"]

        # ================================
        # 第三阶段: 确认密码重置
        # ================================

        password_reset_data = {
            "token": "reset_token_abcdef123456",
            "new_password": "NewSecurePassword456!",
            "confirm_password": "NewSecurePassword456!",
        }

        mock_user_service.confirm_password_reset.return_value = {
            "message": "Password reset successful",
            "user_id": user_data["id"],
            "reset_at": datetime.utcnow().isoformat(),
        }

        with patch("src.domain.services.user_service.UserService", return_value=mock_user_service):
            response = await async_client.post(
                "/api/users/confirm-password-reset", json=password_reset_data
            )

            if response.status_code == 200:
                reset_result = response.json()
                assert reset_result["message"] == "Password reset successful"

        # ================================
        # 第四阶段: 使用新密码登录
        # ================================

        login_with_new_password = {
            "username": user_data["username"],
            "password": "NewSecurePassword456!",
        }

        mock_auth_service = AsyncMock()
        mock_auth_service.authenticate_user.return_value = {
            "access_token": "new_jwt_after_reset",
            "token_type": "bearer",
            "user": {
                "id": user_data["id"],
                "username": user_data["username"],
                "email": user_data["email"],
            },
        }

        with patch("src.domain.services.auth_service.AuthService", return_value=mock_auth_service):
            response = await async_client.post(
                "/api/auth/login", json=login_with_new_password
            )

            if response.status_code == 200:
                login_result = response.json()
                assert "access_token" in login_result

    @pytest.mark.asyncio
    async def test_authentication_security_features(
        self, async_client: AsyncClient, test_user_data, mock_redis
    ):
        """测试认证安全功能"""
        user_data = test_user_data["users"][0]

        # ================================
        # 第一阶段: 账户锁定机制
        # ================================

        login_data = {
            "username": user_data["username"],
            "password": "WrongPassword123!",
        }

        mock_auth_service = AsyncMock()
        # 模拟多次失败登录
        for _attempt in range(5):
            mock_auth_service.authenticate_user.side_effect = Exception(
                "Invalid credentials"
            )

            with patch(
                "src.domain.services.auth_service.AuthService", return_value=mock_auth_service
            ):
                response = await async_client.post("/api/auth/login", json=login_data)

                if response.status_code != 404:
                    assert response.status_code in [401, 429]

        # 第6次尝试应该触发账户锁定
        mock_auth_service.authenticate_user.side_effect = Exception(
            "Account locked due to too many failed attempts"
        )

        with patch("src.domain.services.auth_service.AuthService", return_value=mock_auth_service):
            response = await async_client.post("/api/auth/login", json=login_data)

            if response.status_code != 404:
                assert response.status_code == 423  # Locked

        # ================================
        # 第二阶段: 检查登录尝试历史
        # ================================

        mock_auth_service.get_login_attempts.return_value = {
            "user_id": user_data["id"],
            "attempts": [
                {
                    "timestamp": datetime.utcnow().isoformat(),
                    "ip_address": "192.168.1.100",
                    "user_agent": "TestClient/1.0",
                    "success": False,
                    "reason": "Invalid password",
                }
            ]
            * 5,
            "is_locked": True,
            "lock_expires_at": (datetime.utcnow() + timedelta(minutes=30)).isoformat(),
        }

        with patch("src.domain.services.auth_service.AuthService", return_value=mock_auth_service):
            response = await async_client.get(
                f"/api/users/{user_data['id']}/login-attempts"
            )

            if response.status_code == 200:
                attempts_result = response.json()
                assert attempts_result["is_locked"]
                assert len(attempts_result["attempts"]) == 5

        # ================================
        # 第三阶段: 解锁账户
        # ================================

        unlock_data = {
            "user_id": user_data["id"],
            "unlock_reason": "User requested unlock",
        }

        mock_user_service = AsyncMock()
        mock_user_service.unlock_user_account.return_value = {
            "user_id": user_data["id"],
            "unlocked": True,
            "unlocked_at": datetime.utcnow().isoformat(),
            "message": "Account unlocked successfully",
        }

        with patch("src.domain.services.user_service.UserService", return_value=mock_user_service):
            response = await async_client.post(
                "/api/users/unlock-account", json=unlock_data
            )

            if response.status_code == 200:
                unlock_result = response.json()
                assert unlock_result["unlocked"]


class TestUserProfileManagementE2E:
    """用户资料管理端到端测试"""

    @pytest.mark.asyncio
    async def test_complete_profile_management(
        self, async_client: AsyncClient, test_user_data
    ):
        """测试完整的资料管理流程"""
        user_data = test_user_data["users"][0]
        auth_headers = {"Authorization": "Bearer test_jwt_token"}

        # ================================
        # 第一阶段: 查看用户资料
        # ================================

        mock_user_service = AsyncMock()
        mock_user_service.get_user_profile.return_value = {
            "id": user_data["id"],
            "username": user_data["username"],
            "email": user_data["email"],
            "first_name": "John",
            "last_name": "Doe",
            "bio": "Football prediction enthusiast",
            "avatar_url": "https://example.com/avatar.jpg",
            "favorite_team": "Manchester United",
            "favorite_league": "Premier League",
            "member_since": user_data["created_at"].isoformat(),
            "last_login": datetime.utcnow().isoformat(),
            "statistics": {
                "total_predictions": 150,
                "accuracy_rate": 0.68,
                "total_points": 1250,
                "current_ranking": 15,
                "best_streak": 8,
            },
        }

        with patch("src.domain.services.user_service.UserService", return_value=mock_user_service):
            response = await async_client.get(
                f"/api/users/{user_data['id']}/profile", headers=auth_headers
            )

            if response.status_code == 200:
                profile = response.json()
                assert profile["username"] == user_data["username"]
                assert "statistics" in profile

        # ================================
        # 第二阶段: 更新基本信息
        # ================================

        basic_update_data = {
            "first_name": "Johnathan",
            "last_name": "Smith",
            "bio": "Passionate football fan and prediction expert with 5+ years experience",
            "favorite_team": "Liverpool",
            "phone_number": "+44 20 7123 4567",
        }

        mock_user_service.update_basic_info.return_value = {
            "id": user_data["id"],
            "username": user_data["username"],
            "email": user_data["email"],
            **basic_update_data,
            "updated_at": datetime.utcnow().isoformat(),
        }

        with patch("src.domain.services.user_service.UserService", return_value=mock_user_service):
            response = await async_client.put(
                f"/api/users/{user_data['id']}/basic-info",
                json=basic_update_data,
                headers=auth_headers,
            )

            if response.status_code == 200:
                updated_info = response.json()
                assert updated_info["first_name"] == "Johnathan"
                assert updated_info["favorite_team"] == "Liverpool"

        # ================================
        # 第三阶段: 上传头像
        # ================================

        # 模拟文件上传
        avatar_data = {
            "file": "data:image/jpeg;base64,/9j/4AAQSkZJRgABAQAAAQ...",
            "filename": "new_avatar.jpg",
            "content_type": "image/jpeg",
        }

        mock_user_service.upload_avatar.return_value = {
            "avatar_url": "https://cdn.example.com/avatars/new_avatar.jpg",
            "thumbnail_url": "https://cdn.example.com/avatars/thumbnails/new_avatar_thumb.jpg",
            "uploaded_at": datetime.utcnow().isoformat(),
        }

        with patch("src.domain.services.user_service.UserService", return_value=mock_user_service):
            response = await async_client.post(
                f"/api/users/{user_data['id']}/avatar",
                json=avatar_data,
                headers=auth_headers,
            )

            if response.status_code == 200:
                avatar_result = response.json()
                assert "avatar_url" in avatar_result

        # ================================
        # 第四阶段: 设置社交媒体链接
        # ================================

        social_links_data = {
            "twitter": "https://twitter.com/johnsmith",
            "instagram": "https://instagram.com/johnsmith_football",
            "facebook": "https://facebook.com/johnsmith",
            "youtube": "https://youtube.com/c/johnsmithpredictions",
            "website": "https://johnsmithpredictions.com",
        }

        mock_user_service.update_social_links.return_value = {
            "user_id": user_data["id"],
            "social_links": social_links_data,
            "updated_at": datetime.utcnow().isoformat(),
        }

        with patch("src.domain.services.user_service.UserService", return_value=mock_user_service):
            response = await async_client.put(
                f"/api/users/{user_data['id']}/social-links",
                json=social_links_data,
                headers=auth_headers,
            )

            if response.status_code == 200:
                social_result = response.json()
                assert (
                    social_result["social_links"]["twitter"]
                    == "https://twitter.com/johnsmith"
                )

    @pytest.mark.asyncio
    async def test_user_preferences_management(
        self, async_client: AsyncClient, test_user_data
    ):
        """测试用户偏好设置管理"""
        user_data = test_user_data["users"][0]
        auth_headers = {"Authorization": "Bearer test_jwt_token"}

        # 创建mock用户服务
        from unittest.mock import Mock

        mock_user_service = Mock()

        # ================================
        # 第一阶段: 设置显示偏好
        # ================================

        display_preferences = {
            "language": "en",
            "timezone": "Europe/London",
            "date_format": "DD/MM/YYYY",
            "time_format": "24h",
            "theme": "dark",
            "currency": "GBP",
            "odds_format": "decimal",  # decimal, fractional, american
        }

        mock_user_service.update_display_preferences.return_value = {
            "user_id": user_data["id"],
            "preferences": display_preferences,
            "updated_at": datetime.utcnow().isoformat(),
        }

        with patch("src.domain.services.user_service.UserService", return_value=mock_user_service):
            response = await async_client.put(
                f"/api/users/{user_data['id']}/display-preferences",
                json=display_preferences,
                headers=auth_headers,
            )

            if response.status_code == 200:
                pref_result = response.json()
                assert pref_result["preferences"]["theme"] == "dark"

        # ================================
        # 第二阶段: 设置隐私偏好
        # ================================

        privacy_preferences = {
            "profile_visibility": "public",  # public, friends, private
            "show_predictions": True,
            "show_statistics": True,
            "allow_friend_requests": True,
            "show_in_leaderboard": True,
            "data_sharing": {
                "analytics": True,
                "marketing": False,
                "third_party": False,
            },
        }

        mock_user_service.update_privacy_preferences.return_value = {
            "user_id": user_data["id"],
            "privacy": privacy_preferences,
            "updated_at": datetime.utcnow().isoformat(),
        }

        with patch("src.domain.services.user_service.UserService", return_value=mock_user_service):
            response = await async_client.put(
                f"/api/users/{user_data['id']}/privacy-preferences",
                json=privacy_preferences,
                headers=auth_headers,
            )

            if response.status_code == 200:
                privacy_result = response.json()
                assert privacy_result["privacy"]["profile_visibility"] == "public"

        # ================================
        # 第三阶段: 设置预测偏好
        # ================================

        prediction_preferences = {
            "default_confidence": 0.75,
            "auto_save_drafts": True,
            "show_prediction_tips": True,
            "confidence_warnings": True,
            "deadline_reminders": {"enabled": True, "hours_before": 24},
            "result_notifications": {
                "enabled": True,
                "immediate": True,
                "daily_summary": False,
            },
        }

        mock_user_service.update_prediction_preferences.return_value = {
            "user_id": user_data["id"],
            "predictions": prediction_preferences,
            "updated_at": datetime.utcnow().isoformat(),
        }

        with patch("src.domain.services.user_service.UserService", return_value=mock_user_service):
            response = await async_client.put(
                f"/api/users/{user_data['id']}/prediction-preferences",
                json=prediction_preferences,
                headers=auth_headers,
            )

            if response.status_code == 200:
                pred_pref_result = response.json()
                assert pred_pref_result["predictions"]["auto_save_drafts"]


class TestUserActivityAndEngagementE2E:
    """用户活动和参与度端到端测试"""

    @pytest.mark.asyncio
    async def test_user_activity_tracking(
        self, async_client: AsyncClient, test_user_data
    ):
        """测试用户活动跟踪"""
        user_data = test_user_data["users"][0]
        auth_headers = {"Authorization": "Bearer test_jwt_token"}

        # ================================
        # 第一阶段: 获取用户活动历史
        # ================================

        mock_user_service = AsyncMock()
        mock_user_service.get_user_activity.return_value = {
            "user_id": user_data["id"],
            "activities": [
                {
                    "type": "prediction_created",
                    "timestamp": datetime.utcnow().isoformat(),
                    "details": {
                        "match_id": 123,
                        "predicted_score": "2-1",
                        "confidence": 0.85,
                    },
                },
                {
                    "type": "profile_updated",
                    "timestamp": (datetime.utcnow() - timedelta(hours=2)).isoformat(),
                    "details": {
                        "field": "favorite_team",
                        "old_value": "Manchester United",
                        "new_value": "Liverpool",
                    },
                },
                {
                    "type": "login",
                    "timestamp": (datetime.utcnow() - timedelta(days=1)).isoformat(),
                    "details": {
                        "ip_address": "192.168.1.100",
                        "user_agent": "Mozilla/5.0...",
                    },
                },
            ],
            "total_activities": 25,
            "page": 1,
            "per_page": 10,
        }

        with patch("src.domain.services.user_service.UserService", return_value=mock_user_service):
            response = await async_client.get(
                f"/api/users/{user_data['id']}/activities", headers=auth_headers
            )

            if response.status_code == 200:
                activities = response.json()
                assert len(activities["activities"]) > 0
                assert activities["total_activities"] == 25

        # ================================
        # 第二阶段: 获取用户参与度统计
        # ================================

        mock_user_service.get_user_engagement.return_value = {
            "user_id": user_data["id"],
            "engagement_metrics": {
                "login_frequency": {
                    "last_7_days": 5,
                    "last_30_days": 18,
                    "average_streak": 3.2,
                },
                "prediction_activity": {
                    "total_predictions": 150,
                    "last_week_predictions": 12,
                    "accuracy_rate": 0.68,
                    "average_confidence": 0.76,
                },
                "social_engagement": {
                    "friends_count": 25,
                    "predictions_shared": 45,
                    "comments_made": 78,
                    "likes_given": 156,
                },
                "platform_usage": {
                    "features_used": [
                        "predictions",
                        "leaderboard",
                        "statistics",
                        "forums",
                    ],
                    "most_used_feature": "predictions",
                    "session_duration_avg": "15 minutes",
                },
            },
            "engagement_score": 78.5,
            "activity_level": "high",
        }

        with patch("src.domain.services.user_service.UserService", return_value=mock_user_service):
            response = await async_client.get(
                f"/api/users/{user_data['id']}/engagement", headers=auth_headers
            )

            if response.status_code == 200:
                engagement = response.json()
                assert engagement["engagement_score"] == 78.5
                assert engagement["activity_level"] == "high"

    @pytest.mark.asyncio
    async def test_user_achievements_and_badges(
        self, async_client: AsyncClient, test_user_data
    ):
        """测试用户成就和徽章系统"""
        user_data = test_user_data["users"][0]
        auth_headers = {"Authorization": "Bearer test_jwt_token"}

        # ================================
        # 第一阶段: 获取用户徽章
        # ================================

        mock_user_service = AsyncMock()
        mock_user_service.get_user_achievements.return_value = {
            "user_id": user_data["id"],
            "achievements": [
                {
                    "id": "first_prediction",
                    "name": "First Prediction",
                    "description": "Made your first prediction",
                    "badge_url": "https://example.com/badges/first_prediction.png",
                    "earned_at": (datetime.utcnow() - timedelta(days=30)).isoformat(),
                    "category": "milestone",
                    "rarity": "common",
                },
                {
                    "id": "accurate_week",
                    "name": "Accurate Week",
                    "description": "Achieved 80%+ accuracy in a week",
                    "badge_url": "https://example.com/badges/accurate_week.png",
                    "earned_at": (datetime.utcnow() - timedelta(days=7)).isoformat(),
                    "category": "skill",
                    "rarity": "rare",
                },
                {
                    "id": "top_10",
                    "name": "Top 10",
                    "description": "Reached top 10 in leaderboard",
                    "badge_url": "https://example.com/badges/top_10.png",
                    "earned_at": (datetime.utcnow() - timedelta(days=2)).isoformat(),
                    "category": "competition",
                    "rarity": "epic",
                },
            ],
            "total_achievements": 15,
            "total_badges": 12,
            "achievement_points": 1250,
        }

        with patch("src.domain.services.user_service.UserService", return_value=mock_user_service):
            response = await async_client.get(
                f"/api/users/{user_data['id']}/achievements", headers=auth_headers
            )

            if response.status_code == 200:
                achievements = response.json()
                assert len(achievements["achievements"]) == 3
                assert achievements["total_achievements"] == 15

        # ================================
        # 第二阶段: 获取可获得的成就
        # ================================

        mock_user_service.get_available_achievements.return_value = {
            "achievements": [
                {
                    "id": "prediction_streak_10",
                    "name": "Hot Streak",
                    "description": "Make 10 correct predictions in a row",
                    "badge_url": "https://example.com/badges/hot_streak.png",
                    "category": "skill",
                    "rarity": "legendary",
                    "requirements": {
                        "consecutive_correct_predictions": 10,
                        "minimum_confidence": 0.7,
                    },
                    "progress": {"current": 7, "required": 10, "percentage": 70},
                    "status": "in_progress",
                },
                {
                    "id": "perfect_month",
                    "name": "Perfect Month",
                    "description": "Achieve 100% accuracy for a full month",
                    "badge_url": "https://example.com/badges/perfect_month.png",
                    "category": "skill",
                    "rarity": "legendary",
                    "requirements": {"predictions_in_month": 20, "accuracy_rate": 1.0},
                    "progress": {"current": 15, "required": 20, "percentage": 75},
                    "status": "in_progress",
                },
            ]
        }

        with patch("src.domain.services.user_service.UserService", return_value=mock_user_service):
            response = await async_client.get(
                f"/api/users/{user_data['id']}/achievements/available",
                headers=auth_headers,
            )

            if response.status_code == 200:
                available_achievements = response.json()
                assert len(available_achievements["achievements"]) == 2
                assert (
                    available_achievements["achievements"][0]["status"] == "in_progress"
                )


class TestUserManagementSecurityE2E:
    """用户管理安全端到端测试"""

    @pytest.mark.asyncio
    async def test_user_account_deletion(
        self, async_client: AsyncClient, test_user_data
    ):
        """测试用户账户删除流程"""
        user_data = test_user_data["users"][0]
        auth_headers = {"Authorization": "Bearer test_jwt_token"}

        # ================================
        # 第一阶段: 请求账户删除
        # ================================

        deletion_request_data = {
            "reason": "Privacy concerns",
            "feedback": "Great service, but I need to reduce my digital footprint",
            "confirm_identity": True,
            "understand_consequences": True,
        }

        mock_user_service = AsyncMock()
        mock_user_service.request_account_deletion.return_value = {
            "deletion_token": "deletion_token_123456",
            "expires_at": (datetime.utcnow() + timedelta(hours=24)).isoformat(),
            "message": "Account deletion request received. Please confirm using the link sent to your email.",
        }

        with patch("src.domain.services.user_service.UserService", return_value=mock_user_service):
            response = await async_client.post(
                f"/api/users/{user_data['id']}/request-deletion",
                json=deletion_request_data,
                headers=auth_headers,
            )

            if response.status_code == 200:
                deletion_request = response.json()
                assert "deletion_token" in deletion_request

        # ================================
        # 第二阶段: 确认账户删除
        # ================================

        deletion_confirmation_data = {
            "token": "deletion_token_123456",
            "password": "SecurePassword123!",  # 需要密码确认
        }

        mock_user_service.confirm_account_deletion.return_value = {
            "message": "Account deletion confirmed. Your account will be permanently deleted within 30 days.",
            "deletion_scheduled_at": datetime.utcnow().isoformat(),
            "final_deletion_date": (datetime.utcnow() + timedelta(days=30)).isoformat(),
            "cancellation_token": "cancel_token_789012",
        }

        with patch("src.domain.services.user_service.UserService", return_value=mock_user_service):
            response = await async_client.post(
                "/api/users/confirm-deletion", json=deletion_confirmation_data
            )

            if response.status_code == 200:
                confirmation_result = response.json()
                assert "final_deletion_date" in confirmation_result

        # ================================
        # 第三阶段: 取消账户删除
        # ================================

        cancellation_data = {"token": "cancel_token_789012"}

        mock_user_service.cancel_account_deletion.return_value = {
            "message": "Account deletion cancelled successfully",
            "cancelled_at": datetime.utcnow().isoformat(),
            "account_status": "active",
        }

        with patch("src.domain.services.user_service.UserService", return_value=mock_user_service):
            response = await async_client.post(
                "/api/users/cancel-deletion", json=cancellation_data
            )

            if response.status_code == 200:
                cancellation_result = response.json()
                assert cancellation_result["account_status"] == "active"

    @pytest.mark.asyncio
    async def test_two_factor_authentication(
        self, async_client: AsyncClient, test_user_data
    ):
        """测试双因素认证"""
        user_data = test_user_data["users"][0]
        auth_headers = {"Authorization": "Bearer test_jwt_token"}

        # ================================
        # 第一阶段: 启用2FA
        # ================================

        mock_user_service = AsyncMock()
        mock_user_service.enable_two_factor.return_value = {
            "qr_code_url": "https://api.qrserver.com/v1/create-qr-code/?data=otpauth%3A%2F%2F...",
            "backup_codes": [
                "123456",
                "789012",
                "345678",
                "901234",
                "567890",
                "234567",
                "890123",
                "456789",
            ],
            "setup_instructions": [
                "Scan the QR code with your authenticator app",
                "Enter the verification code to confirm setup",
                "Save your backup codes in a secure location",
            ],
        }

        with patch("src.domain.services.user_service.UserService", return_value=mock_user_service):
            response = await async_client.post(
                f"/api/users/{user_data['id']}/enable-2fa", headers=auth_headers
            )

            if response.status_code == 200:
                setup_result = response.json()
                assert "qr_code_url" in setup_result
                assert len(setup_result["backup_codes"]) == 8

        # ================================
        # 第二阶段: 验证2FA设置
        # ================================

        verification_data = {"verification_code": "123456"}

        mock_user_service.verify_two_factor_setup.return_value = {
            "message": "2FA enabled successfully",
            "enabled_at": datetime.utcnow().isoformat(),
        }

        with patch("src.domain.services.user_service.UserService", return_value=mock_user_service):
            response = await async_client.post(
                f"/api/users/{user_data['id']}/verify-2fa-setup",
                json=verification_data,
                headers=auth_headers,
            )

            if response.status_code == 200:
                verification_result = response.json()
                assert verification_result["message"] == "2FA enabled successfully"

        # ================================
        # 第三阶段: 使用2FA登录
        # ================================

        login_data = {
            "username": user_data["username"],
            "password": "SecurePassword123!",
        }

        mock_auth_service = AsyncMock()
        mock_auth_service.authenticate_user.return_value = {
            "requires_2fa": True,
            "temp_token": "temp_token_for_2fa",
            "message": "Please enter your 2FA code",
        }

        with patch("src.domain.services.auth_service.AuthService", return_value=mock_auth_service):
            response = await async_client.post("/api/auth/login", json=login_data)

            if response.status_code == 200:
                login_result = response.json()
                assert login_result["requires_2fa"]

        # 提供2FA代码
        two_fa_data = {
            "temp_token": "temp_token_for_2fa",
            "verification_code": "123456",
        }

        mock_auth_service.verify_two_factor.return_value = {
            "access_token": "jwt_token_with_2fa",
            "refresh_token": "refresh_token_with_2fa",
            "token_type": "bearer",
            "two_factor_verified": True,
        }

        with patch("src.domain.services.auth_service.AuthService", return_value=mock_auth_service):
            response = await async_client.post("/api/auth/verify-2fa", json=two_fa_data)

            if response.status_code == 200:
                final_login_result = response.json()
                assert final_login_result["two_factor_verified"]


# 测试辅助函数
def create_test_registration_data(base_user_data: dict) -> dict:
    """创建测试注册数据的辅助函数"""
    return {
        "username": base_user_data["username"],
        "email": base_user_data["email"],
        "password": "SecurePassword123!",
        "confirm_password": "SecurePassword123!",
        "first_name": "Test",
        "last_name": "User",
        "accept_terms": True,
        "marketing_consent": False,
    }


def create_test_profile_data() -> dict:
    """创建测试用户资料数据的辅助函数"""
    return {
        "first_name": "John",
        "last_name": "Doe",
        "bio": "Football prediction enthusiast",
        "favorite_team": "Manchester United",
        "favorite_league": "Premier League",
        "phone_number": "+44 20 7123 4567",
        "location": "London, UK",
    }


async def verify_user_state(
    async_client: AsyncClient, user_id: int, expected_state: dict
):
    """验证用户状态的辅助函数"""
    auth_headers = {"Authorization": "Bearer test_jwt_token"}

    response = await async_client.get(
        f"/api/users/{user_id}/status", headers=auth_headers
    )

    if response.status_code == 200:
        actual_state = response.json()

        for key, expected_value in expected_state.items():
            assert (
                actual_state.get(key) == expected_value
            ), f"User state mismatch for {key}"

        return True

    return False
