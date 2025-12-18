#!/usr/bin/env python3
"""
推理API测试脚本
模拟真实的API请求来验证推理服务功能

功能:
1. 测试模型信息端点
2. 测试单场比赛预测
3. 测试批量预测
4. 测试健康检查
5. 错误处理测试

作者: Backend Engineer
创建时间: 2025-12-10
版本: 1.0.0 - Phase 3 Inference
"""

import asyncio
import json
import time
from datetime import datetime, timedelta
import requests
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


class InferenceAPITester:
    """推理API测试器"""

    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json",
            "Accept": "application/json"
        })

    def test_health_check(self) -> bool:
        """测试健康检查端点"""
        print("🔍 测试健康检查端点...")
        try:
            response = self.session.get(f"{self.base_url}/health")

            if response.status_code == 200:
                data = response.json()
                print(f"   ✅ 健康检查通过: {data['status']}")
                print(f"   📊 服务: {data.get('service', 'unknown')}")
                print(f"   🤖 模型状态: {data.get('model_status', 'unknown')}")
                return True
            else:
                print(f"   ❌ 健康检查失败: {response.status_code}")
                print(f"   响应: {response.text}")
                return False

        except Exception as e:
            print(f"   ❌ 健康检查异常: {e}")
            return False

    def test_model_info(self) -> bool:
        """测试模型信息端点"""
        print("\n🔍 测试模型信息端点...")
        try:
            response = self.session.get(f"{self.base_url}/api/v1/inference/model/info")

            if response.status_code == 200:
                data = response.json()
                print(f"   ✅ 模型信息获取成功:")
                print(f"      状态: {data['status']}")
                print(f"      模型类型: {data['model_type']}")
                print(f"      版本: {data['model_version']}")
                print(f"      特征数量: {data['feature_count']}")
                print(f"      目标类别: {data['target_classes']}")

                if data.get('performance_metrics'):
                    perf = data['performance_metrics']
                    print(f"      性能指标:")
                    print(f"         准确率: {perf.get('accuracy', 'N/A')}")
                    print(f"         Log Loss: {perf.get('log_loss', 'N/A')}")

                return True
            else:
                print(f"   ❌ 模型信息获取失败: {response.status_code}")
                return False

        except Exception as e:
            print(f"   ❌ 模型信息获取异常: {e}")
            return False

    def create_sample_match_data(self, match_id: int) -> dict:
        """创建样本比赛数据"""
        return {
            "match_id": match_id,
            "home_team_name": "Manchester United",
            "away_team_name": "Liverpool",
            "match_date": "2024-01-15T15:00:00",
            "home_score": 0,
            "away_score": 0,
            "home_xg": 1.8,
            "away_xg": 1.2,
            "home_total_shots": 15,
            "away_total_shots": 12,
            "home_shots_on_target": 6,
            "away_shots_on_target": 4,
            "league_id": "PL",
            "league_name": "Premier League",
            "stats_json": {
                "possession": {"home": 55, "away": 45},
                "passes": {"home": 450, "away": 380},
                "corners": {"home": 6, "away": 4}
            }
        }

    def test_single_prediction(self) -> bool:
        """测试单场比赛预测"""
        print("\n🔍 测试单场比赛预测...")

        try:
            # 创建测试数据
            test_data = self.create_sample_match_data(12345)

            print(f"   📊 测试数据:")
            print(f"      比赛ID: {test_data['match_id']}")
            print(f"      对阵: {test_data['home_team_name']} vs {test_data['away_team_name']}")
            print(f"      主队xG: {test_data['home_xg']}, 客队xG: {test_data['away_xg']}")

            start_time = time.time()
            response = self.session.post(
                f"{self.base_url}/api/v1/inference/predict",
                json=test_data
            )
            processing_time = (time.time() - start_time) * 1000

            if response.status_code == 200:
                data = response.json()
                print(f"   ✅ 预测成功:")
                print(f"      预测结果: {data['prediction']}")
                print(f"      置信度: {data['confidence']:.3f}")
                print(f"      概率分布: {data['probabilities']}")
                print(f"      模型版本: {data['model_version']}")
                print(f"      特征数量: {data['feature_count']}")
                print(f"      缺失特征: {data['missing_features']}")
                print(f"      API处理时间: {data.get('processing_time_ms', 0):.1f}ms")
                print(f"      实际测试时间: {processing_time:.1f}ms")
                return True
            else:
                print(f"   ❌ 预测失败: {response.status_code}")
                print(f"   响应: {response.text}")
                return False

        except Exception as e:
            print(f"   ❌ 预测异常: {e}")
            return False

    def test_batch_prediction(self) -> bool:
        """测试批量预测"""
        print("\n🔍 测试批量预测...")

        try:
            # 创建批量测试数据
            batch_data = [
                self.create_sample_match_data(i)
                for i in [12345, 12346, 12347]
            ]

            print(f"   📊 批量测试数据: {len(batch_data)} 场比赛")

            start_time = time.time()
            response = self.session.post(
                f"{self.base_url}/api/v1/inference/predict/batch",
                json=batch_data
            )
            processing_time = (time.time() - start_time) * 1000

            if response.status_code == 200:
                data = response.json()
                print(f"   ✅ 批量预测成功:")
                print(f"      总比赛数: {data['total_matches']}")
                print(f"      处理时间: {data['processing_time_ms']:.1f}ms")
                print(f"      实际测试时间: {processing_time:.1f}ms")
                print(f"      预测分布: {data['prediction_distribution']}")

                # 显示每场比赛的预测
                for i, pred in enumerate(data['predictions']):
                    print(f"      比赛 {pred['match_id']}: {pred['prediction']} "
                              f"(置信度: {pred['confidence']:.3f})")

                return True
            else:
                print(f"   ❌ 批量预测失败: {response.status_code}")
                print(f"   响应: {response.text}")
                return False

        except Exception as e:
            print(f"   ❌ 批量预测异常: {e}")
            return False

    def test_error_handling(self) -> bool:
        """测试错误处理"""
        print("\n🔍 测试错误处理...")

        # 测试1: 缺少必要字段
        print("   测试1: 缺少必要字段...")
        try:
            invalid_data = {"match_id": 12345}  # 缺少team_name
            response = self.session.post(
                f"{self.base_url}/api/v1/inference/predict",
                json=invalid_data
            )

            if response.status_code == 422:
                print("      ✅ 正确处理验证错误")
            else:
                print(f"      ⚠️ 预期422错误，实际: {response.status_code}")
                return False

        except Exception as e:
            print(f"      ❌ 测试异常: {e}")
            return False

        # 测试2: 无效的比赛ID
        print("   测试2: 完全无效数据...")
        try:
            invalid_data = {"invalid": "data"}
            response = self.session.post(
                f"{self.base_url}/api/v1/inference/predict",
                json=invalid_data
            )

            if response.status_code >= 400:
                print("      ✅ 正确处理无效数据")
            else:
                print(f"      ⚠️ 预期错误，实际: {response.status_code}")
                return False

        except Exception as e:
            print(f"      ❌ 测试异常: {e}")
            return False

        print("   ✅ 错误处理测试通过")
        return True

    def run_all_tests(self) -> dict:
        """运行所有测试"""
        print("🧪 开始推理API测试")
        print("=" * 60)

        results = {
            "health_check": False,
            "model_info": False,
            "single_prediction": False,
            "batch_prediction": False,
            "error_handling": False
        }

        try:
            results["health_check"] = self.test_health_check()
            results["model_info"] = self.test_model_info()
            results["single_prediction"] = self.test_single_prediction()
            results["batch_prediction"] = self.test_batch_prediction()
            results["error_handling"] = self.test_error_handling()

        except KeyboardInterrupt:
            print("\n⚠️ 测试被用户中断")
        except Exception as e:
            print(f"\n❌ 测试过程中发生异常: {e}")

        # 汇总结果
        self.print_summary(results)
        return results

    def print_summary(self, results: dict):
        """打印测试摘要"""
        print("\n" + "=" * 60)
        print("📊 推理API测试摘要")
        print("=" * 60)

        total_tests = len(results)
        passed_tests = sum(1 for result in results.values() if result)
        success_rate = (passed_tests / total_tests) * 100 if total_tests > 0 else 0

        print(f"\n📈 测试结果:")
        for test_name, passed in results.items():
            status = "✅ PASS" if passed else "❌ FAIL"
            print(f"   {test_name:<20}: {status}")

        print(f"\n📊 总体统计:")
        print(f"   通过: {passed_tests}/{total_tests} ({success_rate:.1f}%)")
        print(f"   失败: {total_tests - passed_tests}/{total_tests} ({100-success_rate:.1f}%)")

        if success_rate >= 80:
            print(f"\n🎉 推理API测试通过! 系统准备就绪。")
        elif success_rate >= 60:
            print(f"\n⚠️ 推理API部分通过，需要进一步优化。")
        else:
            print(f"\n❌ 推理API测试失败，需要修复问题。")

        print("=" * 60)


def main():
    """主函数"""
    # 检查API是否运行
    tester = InferenceAPITester()

    print("🔗 检查API服务状态...")
    try:
        health_response = requests.get(f"{tester.base_url}/health", timeout=5)
        if health_response.status_code != 200:
            print(f"❌ API服务未运行在 {tester.base_url}")
            print("请确保FastAPI服务已启动:")
            print("   make dev")
            print("   或")
            print("   uvicorn src.main:app --reload --host 0.0.0.0 --port 8000")
            return
    except requests.exceptions.RequestException:
        print(f"❌ 无法连接到API服务 {tester.base_url}")
        print("请确保FastAPI服务已启动")
        return

    # 运行测试
    results = tester.run_all_tests()

    # 返回测试结果
    success_rate = sum(1 for result in results.values() if result) / len(results) * 100
    return success_rate >= 80


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)