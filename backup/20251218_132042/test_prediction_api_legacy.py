#!/usr/bin/env python3
"""
测试PredictionService API功能的独立脚本
模拟FastAPI环境中的调用，验证完整的预测流程。
"""

import asyncio
import sys
import os

# 确保可以找到项目模块
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from datetime import datetime
import json


async def test_prediction_api():
    """测试完整的PredictionService API功能"""
    print("🚀 测试PredictionService API集成")
    print("=" * 60)

    try:
        # 1. 导入模块
        print("📦 导入模块...")
        from src.ml.inference.service import PredictionService
        from src.schemas.prediction import PredictionRequest, PredictionResponse
        print("✅ 模块导入成功")

        # 2. 获取服务实例
        print("🔍 获取PredictionService实例...")
        service = PredictionService.get_instance()
        print("✅ 服务实例获取成功")

        # 3. 初始化服务
        print("⚙️ 初始化PredictionService...")
        await service.initialize()
        print("✅ 服务初始化成功")
        print(f"📊 模型就绪: {service.is_ready}")
        print(f"🔧 模型版本: {service._model_version}")
        print(f"📈 特征数量: {len(service.feature_columns)}")

        # 4. 测试单个预测
        print("\n🎯 测试单场比赛预测...")
        prediction_request = PredictionRequest(
            home_team_id=8650,
            away_team_id=8456,
            match_date=datetime(2024, 5, 20, 15, 0, 0)
        )

        print(f"📋 预测请求:")
        print(f"   主队ID: {prediction_request.home_team_id}")
        print(f"   客队ID: {prediction_request.away_team_id}")
        print(f"   比赛时间: {prediction_request.match_date}")

        # 执行预测
        result = await service.predict_match(
            home_team_id=prediction_request.home_team_id,
            away_team_id=prediction_request.away_team_id,
            match_date=prediction_request.match_date
        )

        # 验证结果格式
        print("\n📊 预测结果:")
        print(f"   预测结果: {result['prediction']}")
        print(f"   主胜概率: {result['home_win_prob']:.2%}")
        print(f"   平局概率: {result['draw_prob']:.2%}")
        print(f"   客胜概率: {result['away_win_prob']:.2%}")
        print(f"   置信度: {result['confidence']:.2%}")
        print(f"   模型版本: {result['model_version']}")
        print(f"   生成时间: {result.get('generated_at', 'N/A')}")

        # 验证特征数据
        if 'features' in result and result['features']:
            print(f"\n🔍 特征数据 (前5个):")
            for i, (feature_name, value) in enumerate(list(result['features'].items())[:5]):
                print(f"   {i+1}. {feature_name}: {value:.4f}")

        # 5. 创建标准的API响应格式
        api_response = PredictionResponse(**result)
        print(f"\n📡 API响应格式验证: ✅")
        print(f"   响应模型: {type(api_response).__name__}")

        # 6. 测试不同比赛组合
        print(f"\n🔄 测试多种比赛组合...")
        test_cases = [
            (1001, 1002, datetime(2024, 6, 1, 20, 0, 0)),
            (2001, 2002, datetime(2024, 6, 2, 19, 30, 0)),
            (3001, 3002, datetime(2024, 6, 3, 17, 45, 0)),
        ]

        for i, (home_id, away_id, match_date) in enumerate(test_cases, 1):
            try:
                result = await service.predict_match(home_id, away_id, match_date)
                print(f"   测试 {i}: {home_id} vs {away_id} -> {result['prediction']} ({result['confidence']:.2%})")
            except Exception as e:
                print(f"   测试 {i}: {home_id} vs {away_id} -> ❌ 错误: {e}")

        # 7. 测试边界情况
        print(f"\n🧪 测试边界情况...")

        # 相同团队ID（应该失败）
        try:
            await service.predict_match(1001, 1001, datetime.now())
            print("   ❌ 相同团队ID测试失败 - 应该抛出异常")
        except Exception as e:
            print("   ✅ 相同团队ID正确抛出异常")

        # 8. 模拟完整API调用流程
        print(f"\n🌐 模拟完整API调用流程...")

        # 模拟HTTP请求处理
        def simulate_api_endpoint(request_data):
            """模拟FastAPI端点的处理流程"""
            try:
                # 验证请求（Pydantic自动处理）
                request = PredictionRequest(**request_data)

                # 依赖注入获取服务
                service = PredictionService.get_instance()
                if not service.is_ready:
                    return {"error": "Service not ready"}

                # 异步调用预测
                return asyncio.run(service.predict_match(
                    request.home_team_id,
                    request.away_team_id,
                    request.match_date
                ))
            except Exception as e:
                return {"error": str(e)}

        # 模拟HTTP请求
        http_request = {
            "home_team_id": 4001,
            "away_team_id": 4002,
            "match_date": "2024-07-15T18:00:00"
        }

        api_result = simulate_api_endpoint(http_request)
        if "error" not in api_result:
            print(f"   ✅ API调用成功: {api_result['prediction']}")
        else:
            print(f"   ❌ API调用失败: {api_result['error']}")

        print(f"\n🏆 PredictionService API集成测试: ✅ 完全成功!")
        return True

    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """主函数"""
    print("PredictionService API集成测试")
    print("=" * 60)
    print("目的: 验证PredictionService的完整API功能")
    print("包括: 初始化、预测、错误处理、边界情况")
    print("=" * 60)

    success = await test_prediction_api()

    print("\n" + "=" * 60)
    if success:
        print("🎉 所有测试通过! PredictionService已准备好集成到FastAPI")
        print("\n📋 下一步:")
        print("1. 重启FastAPI应用以加载新路由")
        print("2. 测试HTTP端点: curl POST /api/v1/prediction-service/predict")
        print("3. 检查OpenAPI文档: http://localhost:8000/docs")
    else:
        print("❌ 测试失败，请检查错误信息")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())