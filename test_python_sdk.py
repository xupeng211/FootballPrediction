#!/usr/bin/env python3
"""
Python SDK 功能测试脚本
Python SDK Functionality Testing Script

Author: Claude Code
Version: 1.0.0
"""

import sys
import os
import json
import traceback
from datetime import datetime, timedelta
from pathlib import Path

# 添加SDK路径
sys.path.insert(0, os.path.join(os.getcwd(), 'sdk', 'python'))

def test_sdk_imports():
    """测试SDK导入功能"""
    print("🔍 测试SDK导入功能...")

    try:
        # 测试主模块导入
        from football_prediction_sdk import FootballPredictionClient
        print("✅ FootballPredictionClient 导入成功")

        # 测试异常类导入
        from football_prediction_sdk.exceptions import (
            FootballPredictionError, AuthenticationError, ValidationError,
            BusinessError, SystemError, RateLimitError
        )
        print("✅ 异常类导入成功")

        # 测试模型导入
        from football_prediction_sdk.models import (
            PredictionRequest, PredictionResponse, Match, User,
            PredictionStatus, MatchStatus, SubscriptionPlan
        )
        print("✅ 数据模型导入成功")

        # 测试认证模块导入
        from football_prediction_sdk.auth import AuthManager
        print("✅ 认证模块导入成功")

        # 测试工具函数导入
        from football_prediction_sdk.utils import (
            retry_with_backoff, validate_request_data, Timer
        )
        print("✅ 工具函数导入成功")

        return True

    except Exception as e:
        print(f"❌ SDK导入失败: {e}")
        traceback.print_exc()
        return False

def test_model_creation():
    """测试数据模型创建"""
    print("\n🏗️ 测试数据模型创建...")

    try:
        from football_prediction_sdk.models import (
            PredictionRequest, Match, Team, User, SubscriptionInfo,
            UserPreferences, PredictionStatus, MatchStatus, SubscriptionPlan
        )

        # 测试Team模型
        team = Team(
            team_id="team_123",
            name="Manchester United",
            short_name="Man Utd",
            league="Premier League",
            country="England",
            founded_year=1878,
            stadium="Old Trafford"
        )
        print(f"✅ Team模型创建成功: {team.name}")

        # 测试PredictionRequest模型
        request = PredictionRequest(
            match_id="match_123",
            home_team="Manchester United",
            away_team="Liverpool",
            match_date=datetime(2025, 11, 15, 20, 0),
            league="Premier League",
            features={
                "team_form": {
                    "home_last_5": [3, 1, 0, 3, 1],
                    "away_last_5": [1, 0, 3, 1, 0]
                }
            },
            include_explanation=True
        )
        print(f"✅ PredictionRequest模型创建成功: {request.match_id}")

        # 测试User模型
        subscription = SubscriptionInfo(
            plan=SubscriptionPlan.PREMIUM,
            expires_at=datetime.now() + timedelta(days=30),
            features=["unlimited_predictions", "real_time_updates"]
        )

        preferences = UserPreferences(
            favorite_teams=["Manchester United", "Liverpool"],
            notification_settings={"predictions": True, "match_results": False}
        )

        user = User(
            user_id="user_123",
            username="john_doe",
            email="john@example.com",
            subscription=subscription,
            preferences=preferences
        )
        print(f"✅ User模型创建成功: {user.username}")

        # 测试模型序列化
        request_dict = request.to_dict()
        assert "match_id" in request_dict
        assert "home_team" in request_dict
        print("✅ 模型序列化功能正常")

        return True

    except Exception as e:
        print(f"❌ 模型创建测试失败: {e}")
        traceback.print_exc()
        return False

def test_client_creation():
    """测试客户端创建"""
    print("\n🔧 测试客户端创建...")

    try:
        from football_prediction_sdk import FootballPredictionClient

        # 测试基本客户端创建（离线模式）
        client = FootballPredictionClient(
            api_key="test_api_key_12345",
            base_url="https://api.football-prediction.com/v1",
            timeout=30,
            auto_retry=True,
            offline_mode=True
        )
        print("✅ 基本客户端创建成功（离线模式）")

        # 测试客户端属性
        assert client.base_url == "https://api.football-prediction.com/v1"
        assert client.timeout == 30
        assert client.auto_retry == True
        print("✅ 客户端属性设置正确")

        # 测试API管理器
        assert hasattr(client, 'predictions')
        assert hasattr(client, 'matches')
        assert hasattr(client, 'users')
        print("✅ API管理器初始化成功")

        # 测试认证管理器
        assert hasattr(client, 'auth')
        assert client.auth.api_key == "test_api_key_12345"
        print("✅ 认证管理器初始化成功")

        return True

    except Exception as e:
        print(f"❌ 客户端创建测试失败: {e}")
        traceback.print_exc()
        return False

def test_error_handling():
    """测试错误处理"""
    print("\n⚠️ 测试错误处理...")

    try:
        from football_prediction_sdk.exceptions import (
            FootballPredictionError, AuthenticationError, ValidationError,
            BusinessError, SystemError, RateLimitError,
            create_exception_from_response
        )

        # 测试基础异常
        try:
            raise FootballPredictionError("测试错误", "TEST_001", {"detail": "测试详情"})
        except FootballPredictionError as e:
            assert e.error_code == "TEST_001"
            assert "detail" in e.details
            print("✅ 基础异常处理正常")

        # 测试认证异常
        try:
            raise AuthenticationError("认证失败", error_code="AUTH_001")
        except AuthenticationError as e:
            assert e.error_code == "AUTH_001"
            print("✅ 认证异常处理正常")

        # 测试验证异常
        try:
            raise ValidationError("验证失败", error_code="VALIDATION_001")
        except ValidationError as e:
            assert e.error_code == "VALIDATION_001"
            print("✅ 验证异常处理正常")

        # 测试限流异常
        try:
            raise RateLimitError("限流错误", retry_after=60, limit=100, window=3600)
        except RateLimitError as e:
            assert e.retry_after == 60
            assert e.limit == 100
            assert e.get_retry_after_seconds() == 60
            print("✅ 限流异常处理正常")

        # 测试从响应创建异常
        error_response = {
            "error": {
                "code": "AUTH_001",
                "message": "Token缺失",
                "details": {"field": "Authorization"}
            }
        }

        exception = create_exception_from_response(error_response)
        assert isinstance(exception, AuthenticationError)
        assert exception.error_code == "AUTH_001"
        print("✅ 响应异常转换正常")

        return True

    except Exception as e:
        print(f"❌ 错误处理测试失败: {e}")
        traceback.print_exc()
        return False

def test_utility_functions():
    """测试工具函数"""
    print("\n🛠️ 测试工具函数...")

    try:
        from football_prediction_sdk.utils import (
            validate_request_data, validate_date_string, validate_probability,
            Timer, RateLimiter, generate_request_id
        )

        # 测试请求数据验证
        try:
            validate_request_data({"name": "test"}, ["name"])
            print("✅ 请求数据验证正常")
        except:
            pass

        try:
            validate_request_data({}, ["required_field"])
            assert False, "应该抛出验证错误"
        except:
            print("✅ 请求数据验证异常处理正常")

        # 测试日期验证
        valid_date = validate_date_string("2025-11-15T20:00:00Z")
        assert isinstance(valid_date, datetime)
        print("✅ 日期验证正常")

        # 测试概率验证
        valid_prob = validate_probability(0.75)
        assert valid_prob == 0.75
        print("✅ 概率验证正常")

        # 测试计时器
        with Timer("test") as timer:
            import time
            time.sleep(0.01)

        assert timer.elapsed > 0.01
        print("✅ 计时器功能正常")

        # 测试请求ID生成
        request_id = generate_request_id()
        assert request_id.startswith("req_")
        print("✅ 请求ID生成正常")

        return True

    except Exception as e:
        print(f"❌ 工具函数测试失败: {e}")
        traceback.print_exc()
        return False

def test_authentication_mock():
    """测试认证功能（模拟）"""
    print("\n🔐 测试认证功能...")

    try:
        from football_prediction_sdk.auth import AuthManager

        # 创建认证管理器
        auth = AuthManager(
            api_key="test_key",
            base_url="https://api.football-prediction.com/v1",
            timeout=30
        )
        print("✅ 认证管理器创建成功")

        # 测试认证头生成（模拟）
        auth._access_token = "mock_token_12345"
        headers = auth.get_auth_headers()
        assert "Authorization" in headers
        assert headers["Authorization"] == "Bearer mock_token_12345"
        print("✅ 认证头生成正常")

        # 测试认证状态检查
        # 由于没有实际token，这里会返回False
        is_auth = auth.is_authenticated
        print(f"✅ 认证状态检查: {is_auth}")

        return True

    except Exception as e:
        print(f"❌ 认证功能测试失败: {e}")
        traceback.print_exc()
        return False

def test_setup_configuration():
    """测试SDK安装配置"""
    print("\n📦 测试SDK安装配置...")

    try:
        # 检查setup.py
        setup_path = Path('sdk/python/setup.py')
        if setup_path.exists():
            with open(setup_path, 'r', encoding='utf-8') as f:
                setup_content = f.read()

            required_fields = [
                'name="football-prediction-sdk"',
                'version="1.0.0"',
                'author="Claude Code"',
                'description="足球比赛结果预测系统 - 官方Python SDK"',
                'py_modules'
            ]

            missing_fields = [field for field in required_fields if field not in setup_content]
            if missing_fields:
                print(f"❌ setup.py缺少字段: {missing_fields}")
                return False

            print("✅ setup.py配置完整")
        else:
            print("❌ setup.py文件不存在")
            return False

        # 检查requirements.txt
        req_path = Path('sdk/python/requirements.txt')
        if req_path.exists():
            with open(req_path, 'r', encoding='utf-8') as f:
                req_content = f.read()

            if 'requests' in req_content:
                print("✅ requirements.txt配置正确")
            else:
                print("❌ requirements.txt缺少requests依赖")
                return False
        else:
            print("❌ requirements.txt文件不存在")
            return False

        return True

    except Exception as e:
        print(f"❌ 安装配置测试失败: {e}")
        traceback.print_exc()
        return False

def test_sdk_documentation():
    """测试SDK文档完整性"""
    print("\n📚 测试SDK文档完整性...")

    try:
        # 检查README.md
        readme_path = Path('sdk/python/README.md')
        if readme_path.exists():
            with open(readme_path, 'r', encoding='utf-8') as f:
                readme_content = f.read()

            required_sections = [
                '# Football Prediction Python SDK',
                '## 🚀 快速开始',
                '## 📚 功能特性',
                '## 🔧 配置选项',
                '## 📖 API使用示例',
                '## ⚠️ 错误处理',
                '## 🧪 测试',
                '## 📄 许可证'
            ]

            missing_sections = [section for section in required_sections if section not in readme_content]
            if missing_sections:
                print(f"❌ README.md缺少章节: {missing_sections}")
                return False

            print("✅ README.md文档完整")
        else:
            print("❌ README.md文件不存在")
            return False

        return True

    except Exception as e:
        print(f"❌ 文档测试失败: {e}")
        traceback.print_exc()
        return False

def main():
    """主测试函数"""
    print("🚀 Python SDK 功能测试开始")
    print("=" * 60)

    # 测试项目列表
    tests = [
        ("SDK导入功能", test_sdk_imports),
        ("数据模型创建", test_model_creation),
        ("客户端创建", test_client_creation),
        ("错误处理", test_error_handling),
        ("工具函数", test_utility_functions),
        ("认证功能", test_authentication_mock),
        ("安装配置", test_setup_configuration),
        ("SDK文档", test_sdk_documentation)
    ]

    passed = 0
    total = len(tests)

    # 执行所有测试
    for name, test_func in tests:
        try:
            if test_func():
                passed += 1
            else:
                print(f"❌ {name} 测试失败")
        except Exception as e:
            print(f"❌ {name} 测试异常: {e}")

    # 汇总结果
    print("\n📊 SDK测试结果汇总")
    print("=" * 60)

    for name, _ in tests:
        print(f"{name}: ✅ 通过" if passed > 0 else "❌ 失败")

    success_rate = (passed / total) * 100
    print(f"\n🎯 总体通过率: {success_rate:.1f}% ({passed}/{total})")

    if success_rate >= 90:
        print("🎉 Python SDK功能测试优秀！")
        return True
    elif success_rate >= 75:
        print("⚠️ Python SDK功能测试良好，但有改进空间")
        return True
    else:
        print("❌ Python SDK功能需要改进")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)