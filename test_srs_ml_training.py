#!/usr/bin/env python3
"""
SRS ML Training Test Script
SRS机器学习训练测试脚本

测试Issue #115的特征工程算法和真实模型训练功能是否符合SRS要求：
- 模型准确率 ≥ 65%
- 模型AUC ≥ 0.70
- 特征工程完整性
- XGBoost/LightGBM集成

生成时间: 2025-10-29 04:10:00
"""

import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.append(str(Path(__file__).parent))

try:
    from src.ml.enhanced_real_model_training import SRSCompliantModelTrainer
    from src.core.logging_system import get_logger

    logger = get_logger(__name__)
except ImportError as e:
    print(f"导入错误: {e}")
    print("请确保在项目根目录运行此脚本")
    sys.exit(1)


async def test_srs_ml_training():
    """测试SRS机器学习训练功能"""
    print("=" * 80)
    print("SRS机器学习训练功能测试")
    print("Issue #115 特征工程算法和真实模型训练验证")
    print("=" * 80)

    # 初始化训练器
    trainer = SRSCompliantModelTrainer()

    print(f"\n📋 SRS目标要求:")
    print(f"  - 模型准确率: ≥ {trainer.SRS_TARGETS['min_accuracy']*100}%")
    print(f"  - 模型AUC: ≥ {trainer.SRS_TARGETS['min_auc']*100}%")
    print(f"  - 模型F1分数: ≥ {trainer.SRS_TARGETS['min_f1_score']*100}%")
    print(f"  - 特征工程: 完整实现")
    print(f"  - 模型支持: XGBoost/LightGBM")

    print(f"\n🚀 开始SRS符合性训练测试...")

    try:
        # 运行SRS符合性训练管道
        results = await trainer.run_srs_compliant_training_pipeline(n_samples=1500)

        if results["training_status"] == "completed":
            print(f"\n✅ 训练成功完成！")

            # 验证SRS要求
            print(f"\n📊 SRS符合性验证结果:")

            # 检查数据质量
            data_quality_ok = (
                results["data_summary"]["total_matches"] >= 1000
                and results["data_summary"]["feature_count"] >= 20
            )
            print(f"  📈 数据质量: {'✅ 通过' if data_quality_ok else '❌ 不通过'}")
            print(f"    - 总比赛数: {results['data_summary']['total_matches']} (要求: ≥1000)")
            print(f"    - 特征数量: {results['data_summary']['feature_count']} (要求: ≥20)")

            # 检查模型性能
            best_model = results["best_model"]
            accuracy_ok = best_model["accuracy"] >= trainer.SRS_TARGETS["min_accuracy"]
            auc_ok = best_model.get("auc", 0) >= trainer.SRS_TARGETS["min_auc"]
            f1_ok = best_model.get("f1_score", 0) >= trainer.SRS_TARGETS["min_f1_score"]

            print(f"  🎯 准确率要求: {'✅ 达成' if accuracy_ok else '❌ 未达成'}")
            print(
                f"    - 实际准确率: {best_model['accuracy']*100:.2f}% (目标: ≥{trainer.SRS_TARGETS['min_accuracy']*100}%)"
            )

            print(f"  📈 AUC要求: {'✅ 达成' if auc_ok else '❌ 未达成'}")
            print(
                f"    - 实际AUC: {best_model.get('auc', 0)*100:.2f}% (目标: ≥{trainer.SRS_TARGETS['min_auc']*100}%)"
            )

            print(f"  🎪 F1分数要求: {'✅ 达成' if f1_ok else '❌ 未达成'}")
            print(
                f"    - 实际F1分数: {best_model.get('f1_score', 0)*100:.2f}% (目标: ≥{trainer.SRS_TARGETS['min_f1_score']*100}%)"
            )

            # 检查模型支持
            xgb_available = "xgboost" in results["model_results"]
            lgb_available = "lightgbm" in results["model_results"]
            model_support_ok = xgb_available or lgb_available

            print(f"  🤖 模型支持: {'✅ 通过' if model_support_ok else '❌ 不通过'}")
            print(f"    - XGBoost: {'✅ 可用' if xgb_available else '❌ 不可用'}")
            print(f"    - LightGBM: {'✅ 可用' if lgb_available else '❌ 不可用'}")

            # 检查模型保存
            model_saved = best_model["model_saved"]
            print(f"  💾 模型保存: {'✅ 已保存' if model_saved else '❌ 未保存'}")
            if model_saved:
                print(f"    - 保存路径: {best_model['model_path']}")

            # 总体评估
            all_requirements_met = (
                data_quality_ok
                and accuracy_ok
                and auc_ok
                and f1_ok
                and model_support_ok
                and model_saved
            )

            print(
                f"\n🎉 总体SRS符合性评估: {'✅ 完全符合' if all_requirements_met else '❌ 部分符合'}"
            )

            if all_requirements_met:
                print(f"\n🚀 Issue #115 成功完成！")
                print(f"  ✅ 特征工程算法: 完整实现")
                print(f"  ✅ 真实模型训练: 成功完成")
                print(f"  ✅ XGBoost/LightGBM: 已集成")
                print(f"  ✅ 模型评估指标: 达标")
                print(f"  ✅ 模型自动保存: 已完成")
                print(f"  ✅ SRS符合性: 完全达成")
            else:
                print(f"\n⚠️ Issue #115 部分完成，需要进一步优化")
                failed_requirements = []
                if not data_quality_ok:
                    failed_requirements.append("数据质量")
                if not accuracy_ok:
                    failed_requirements.append("准确率")
                if not auc_ok:
                    failed_requirements.append("AUC")
                if not f1_ok:
                    failed_requirements.append("F1分数")
                if not model_support_ok:
                    failed_requirements.append("模型支持")
                if not model_saved:
                    failed_requirements.append("模型保存")

                print(f"  ❌ 需要改进: {', '.join(failed_requirements)}")

            # 生成测试报告
            test_report = {
                "test_name": "SRS ML Training Compliance Test",
                "issue_number": 115,
                "test_date": datetime.now().isoformat(),
                "test_status": "passed" if all_requirements_met else "partially_passed",
                "srs_targets": trainer.SRS_TARGETS,
                "test_results": {
                    "data_quality": data_quality_ok,
                    "accuracy_target_met": accuracy_ok,
                    "auc_target_met": auc_ok,
                    "f1_target_met": f1_ok,
                    "model_support": model_support_ok,
                    "model_saved": model_saved,
                    "overall_compliance": all_requirements_met,
                },
                "best_model": {
                    "name": best_model["name"],
                    "accuracy": best_model["accuracy"],
                    "auc": best_model.get("auc", 0),
                    "f1_score": best_model.get("f1_score", 0),
                    "srs_compliance": best_model["srs_compliance"],
                },
                "data_summary": results["data_summary"],
                "model_results": results["model_results"],
                "recommendations": results["recommendations"],
                "next_steps": results["next_steps"],
            }

            # 保存测试报告
            report_path = Path("test_srs_ml_training_report.json")
            with open(report_path, "w", encoding="utf-8") as f:
                json.dump(test_report, f, indent=2, ensure_ascii=False)

            print(f"\n📄 测试报告已保存到: {report_path}")

            return test_report

        else:
            print(f"\n❌ 训练失败!")
            print(f"错误信息: {results.get('error', '未知错误')}")
            return {
                "test_status": "failed",
                "error": results.get("error"),
                "timestamp": datetime.now().isoformat(),
            }

    except Exception as e:
        print(f"\n💥 测试执行失败!")
        print(f"错误信息: {str(e)}")
        logger.error(f"SRS ML训练测试失败: {e}")
        return {
            "test_status": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
        }


async def main():
    """主函数"""
    print("开始执行SRS机器学习训练测试...")
    print("测试Issue #115: 完善特征工程算法和真实模型训练")

    # 执行测试
    test_result = await test_srs_ml_training()

    print("\n" + "=" * 80)
    if test_result["test_status"] in ["passed", "partially_passed"]:
        print("🎉 测试完成！")
        print(f"测试状态: {'通过' if test_result['test_status'] == 'passed' else '部分通过'}")
        if test_result.get("overall_compliance", False):
            print("✅ SRS要求完全达成")
        else:
            print("⚠️ SRS要求部分达成，需要进一步优化")
    else:
        print("❌ 测试失败")
        print(f"错误: {test_result.get('error', '未知错误')}")

    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
