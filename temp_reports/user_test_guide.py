#!/usr/bin/env python3
"""
用户测试指南
User Testing Guide

为小范围用户测试提供的交互式测试脚本。
"""

import json
import time
from datetime import datetime
import requests
from typing import Dict, Any


class UserTestGuide:
    """用户测试指南类"""

    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.test_results = []

    def print_header(self, title: str):
        """打印标题"""
        print("\n" + "=" * 50)
        print(f"🧪 {title}")
        print("=" * 50)

    def print_step(self, step: int, title: str):
        """打印步骤"""
        print(f"\n{step}. {title}")
        print("-" * 30)

    def test_health_check(self):
        """测试健康检查"""
        self.print_step(1, "测试系统健康状态")
        print("正在检查系统是否正常运行...")

        try:
            response = requests.get(f"{self.base_url}/api/v1/predictions/health")
            if response.status_code == 200:
                data = response.json()
                print("✅ 系统健康检查通过")
                print(f"   状态: {data.get('status', '未知')}")
                print(f"   服务: {data.get('service', '未知')}")
                print(f"   数据库: {data.get('checks', {}).get('database', '未知')}")
                print(f"   响应时间: {data.get('response_time_ms', 0):.2f}ms")

                self.test_results.append(
                    {"测试": "健康检查", "状态": "通过", "详情": "系统运行正常"}
                )
                return True
            else:
                print(f"❌ 健康检查失败: HTTP {response.status_code}")
                self.test_results.append(
                    {"测试": "健康检查", "状态": "失败", "详情": f"HTTP {response.status_code}"}
                )
                return False
        except Exception as e:
            print(f"❌ 健康检查异常: {str(e)}")
            self.test_results.append({"测试": "健康检查", "状态": "异常", "详情": str(e)})
            return False

    def test_single_prediction(self):
        """测试单个预测"""
        self.print_step(2, "测试单个比赛预测")
        print("正在为比赛 12345 生成预测...")

        try:
            response = requests.get(f"{self.base_url}/api/v1/predictions/12345")
            if response.status_code == 200:
                data = response.json()
                print("✅ 单个预测生成成功")
                print(f"   比赛ID: {data.get('match_id', '未知')}")
                print(f"   预测结果: {data.get('predicted_outcome', '未知')}")
                print(f"   主队胜率: {data.get('home_win_prob', 0):.2%}")
                print(f"   平局概率: {data.get('draw_prob', 0):.2%}")
                print(f"   客队胜率: {data.get('away_win_prob', 0):.2%}")
                print(f"   置信度: {data.get('confidence', 0):.2%}")

                self.test_results.append(
                    {
                        "测试": "单个预测",
                        "状态": "通过",
                        "详情": f"预测结果: {data.get('predicted_outcome', '未知')}",
                    }
                )
                return True
            else:
                print(f"❌ 单个预测失败: HTTP {response.status_code}")
                self.test_results.append(
                    {"测试": "单个预测", "状态": "失败", "详情": f"HTTP {response.status_code}"}
                )
                return False
        except Exception as e:
            print(f"❌ 单个预测异常: {str(e)}")
            self.test_results.append({"测试": "单个预测", "状态": "异常", "详情": str(e)})
            return False

    def test_create_prediction(self):
        """测试创建新预测"""
        self.print_step(3, "测试创建新预测")
        print("正在为比赛 99999 创建新预测...")

        try:
            response = requests.post(f"{self.base_url}/api/v1/predictions/99999/predict")
            if response.status_code == 201:
                data = response.json()
                print("✅ 新预测创建成功")
                print(f"   比赛ID: {data.get('match_id', '未知')}")
                print(f"   预测结果: {data.get('predicted_outcome', '未知')}")
                print(f"   模型版本: {data.get('model_version', '未知')}")
                print(f"   创建时间: {data.get('created_at', '未知')}")

                self.test_results.append(
                    {
                        "测试": "创建预测",
                        "状态": "通过",
                        "详情": f"新预测: 比赛{data.get('match_id', '未知')}",
                    }
                )
                return True
            else:
                print(f"❌ 创建预测失败: HTTP {response.status_code}")
                self.test_results.append(
                    {"测试": "创建预测", "状态": "失败", "详情": f"HTTP {response.status_code}"}
                )
                return False
        except Exception as e:
            print(f"❌ 创建预测异常: {str(e)}")
            self.test_results.append({"测试": "创建预测", "状态": "异常", "详情": str(e)})
            return False

    def test_batch_prediction(self):
        """测试批量预测"""
        self.print_step(4, "测试批量预测")
        print("正在为3场比赛生成批量预测...")

        try:
            batch_request = {"match_ids": [11111, 22222, 33333], "model_version": "default"}
            response = requests.post(
                f"{self.base_url}/api/v1/predictions/batch", json=batch_request
            )
            if response.status_code == 200:
                data = response.json()
                print("✅ 批量预测成功")
                print(f"   总比赛数: {data.get('total', 0)}")
                print(f"   成功预测: {data.get('success_count', 0)}")
                print(f"   失败数量: {data.get('failed_count', 0)}")
                print(f"   成功率: {data.get('success_count', 0)/data.get('total', 1)*100:.1f}%")

                self.test_results.append(
                    {
                        "测试": "批量预测",
                        "状态": "通过",
                        "详情": f"成功率: {data.get('success_count', 0)/data.get('total', 1)*100:.1f}%",
                    }
                )
                return True
            else:
                print(f"❌ 批量预测失败: HTTP {response.status_code}")
                self.test_results.append(
                    {"测试": "批量预测", "状态": "失败", "详情": f"HTTP {response.status_code}"}
                )
                return False
        except Exception as e:
            print(f"❌ 批量预测异常: {str(e)}")
            self.test_results.append({"测试": "批量预测", "状态": "异常", "详情": str(e)})
            return False

    def test_prediction_verification(self):
        """测试预测验证"""
        self.print_step(5, "测试预测验证")
        print("正在验证比赛 12345 的预测结果...")

        try:
            response = requests.post(
                f"{self.base_url}/api/v1/predictions/12345/verify?actual_result=home"
            )
            if response.status_code == 200:
                data = response.json()
                print("✅ 预测验证成功")
                print(f"   比赛ID: {data.get('match_id', '未知')}")
                print(f"   实际结果: {data.get('actual_result', '未知')}")
                print(f"   预测正确: {'是' if data.get('is_correct') else '否'}")
                print(f"   准确度评分: {data.get('accuracy_score', 0):.2f}")

                self.test_results.append(
                    {
                        "测试": "预测验证",
                        "状态": "通过",
                        "详情": f"准确度: {data.get('accuracy_score', 0):.2f}",
                    }
                )
                return True
            else:
                print(f"❌ 预测验证失败: HTTP {response.status_code}")
                self.test_results.append(
                    {"测试": "预测验证", "状态": "失败", "详情": f"HTTP {response.status_code}"}
                )
                return False
        except Exception as e:
            print(f"❌ 预测验证异常: {str(e)}")
            self.test_results.append({"测试": "预测验证", "状态": "异常", "详情": str(e)})
            return False

    def run_comprehensive_test(self):
        """运行综合测试"""
        self.print_header("足球预测系统 - 用户测试")
        print("本测试将验证系统的主要功能...")
        print(f"测试目标: {self.base_url}")

        # 执行所有测试
        tests = [
            self.test_health_check,
            self.test_single_prediction,
            self.test_create_prediction,
            self.test_batch_prediction,
            self.test_prediction_verification,
        ]

        passed = 0
        total = len(tests)

        for test in tests:
            if test():
                passed += 1
            time.sleep(1)  # 间隔1秒

        # 显示测试结果
        self.print_header("测试结果总结")
        print(f"总测试数: {total}")
        print(f"通过数量: {passed}")
        print(f"失败数量: {total - passed}")
        print(f"成功率: {passed/total*100:.1f}%")

        print("\n📋 详细结果:")
        for result in self.test_results:
            status_emoji = "✅" if result["状态"] == "通过" else "❌"
            print(f"   {status_emoji} {result['测试']}: {result['状态']} - {result['详情']}")

        # 整体评估
        success_rate = passed / total
        if success_rate >= 0.8:
            print("\n🎉 测试结果: 优秀！系统已准备好投入使用")
        elif success_rate >= 0.6:
            print("\n👍 测试结果: 良好！系统基本可用")
        elif success_rate >= 0.4:
            print("\n⚠️  测试结果: 一般！建议修复问题后使用")
        else:
            print("\n❌ 测试结果: 较差！系统需要重大改进")

        return success_rate


def main():
    """主函数"""
    print("🏆 足球预测系统用户测试指南")
    print("=" * 50)

    base_url = input("请输入系统URL (默认: http://localhost:8000): ").strip()
    if not base_url:
        base_url = "http://localhost:8000"

    guide = UserTestGuide(base_url)

    try:
        guide.run_comprehensive_test()

        print("\n💡 提示: 如果测试失败，请检查:")
        print("   1. 系统是否正在运行")
        print("   2. URL是否正确")
        print("   3. 网络连接是否正常")

    except KeyboardInterrupt:
        print("\n\n👋 测试已取消")
    except Exception as e:
        print(f"\n❌ 测试过程中发生错误: {str(e)}")


if __name__ == "__main__":
    main()
