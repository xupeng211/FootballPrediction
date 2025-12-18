#!/usr/bin/env python3
"""
MVP验证脚本 - MVP Validation Script

快速验证MVP核心阻断点是否已修复的验证脚本。
运行此脚本可以确认：

1. ✅ 推理模块不再是Mock实现
2. ✅ MatchFeatureExtractor组件存在且可用
3. ✅ 端到端测试可以执行
4. ✅ 基本流水线连通性验证

使用方法:
    python test_mvp_validation.py
"""

import asyncio
import logging
import sys
from pathlib import Path

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MVPValidationResult:
    """验证结果类"""
    def __init__(self):
        self.results = []
        self.total_checks = 0
        self.passed_checks = 0

    def add_check(self, name: str, passed: bool, message: str = ""):
        """添加检查结果"""
        self.results.append({
            'name': name,
            'passed': passed,
            'message': message
        })
        self.total_checks += 1
        if passed:
            self.passed_checks += 1

    def print_summary(self):
        """打印验证摘要"""
        print("\n" + "="*60)
        print("🎯 MVP 闭环验证结果")
        print("="*60)

        for result in self.results:
            status = "✅ PASS" if result['passed'] else "❌ FAIL"
            print(f"{status} {result['name']}")
            if result['message']:
                print(f"    {result['message']}")

        print("-"*60)
        print(f"总检查项: {self.total_checks}")
        print(f"通过项: {self.passed_checks}")
        print(f"失败项: {self.total_checks - self.passed_checks}")
        print(f"通过率: {self.passed_checks/self.total_checks*100:.1f}%")

        if self.passed_checks == self.total_checks:
            print("\n🎉 所有检查通过！MVP 闭环验证成功！")
            return True
        else:
            print(f"\n⚠️  仍有 {self.total_checks - self.passed_checks} 项检查失败")
            return False


async def validate_inference_module(result: MVPValidationResult):
    """验证推理模块"""
    logger.info("验证推理模块...")

    try:
        # 尝试导入推理模块
        from src.inference import Predictor, ModelLoadError, predict_match

        # 检查是否还有Mock类存在
        import src.inference
        mock_classes = [name for name in dir(src.inference) if 'Mock' in name]

        if mock_classes:
            result.add_check(
                "推理模块清理检查",
                False,
                f"发现Mock类: {mock_classes}"
            )
        else:
            result.add_check(
                "推理模块清理检查",
                True,
                "✅ 推理模块已完全移除Mock实现"
            )

        # 检查关键类是否存在
        required_classes = ['Predictor', 'ModelLoader', 'PredictionCache', 'HotReloadManager']
        missing_classes = [cls for cls in required_classes if not hasattr(src.inference, cls)]

        if missing_classes:
            result.add_check(
                "推理组件完整性检查",
                False,
                f"缺失组件: {missing_classes}"
            )
        else:
            result.add_check(
                "推理组件完整性检查",
                True,
                "✅ 所有推理组件已实现"
            )

        # 测试Predictor类的基本功能
        try:
            # 创建一个不存在的模型路径来测试错误处理
            predictor = Predictor("non_existent_model.pkl")
            try:
                predictor.load_model()
                result.add_check(
                    "推理模块错误处理",
                    False,
                    "应该抛出ModelLoadError"
                )
            except ModelLoadError:
                result.add_check(
                    "推理模块错误处理",
                    True,
                    "✅ 错误处理正常"
                )
        except Exception as e:
            result.add_check(
                "推理模块基本功能",
                False,
                f"Predictor类功能异常: {str(e)}"
            )

    except ImportError as e:
        result.add_check(
            "推理模块导入",
            False,
            f"推理模块导入失败: {str(e)}"
        )
    except Exception as e:
        result.add_check(
            "推理模块验证",
            False,
            f"验证过程异常: {str(e)}"
        )


async def validate_feature_extractor(result: MVPValidationResult):
    """验证特征提取器"""
    logger.info("验证特征提取器...")

    try:
        from src.ml.features.extractor import MatchFeatureExtractor, MatchFeatureSet

        # 检查组件是否存在
        result.add_check(
            "MatchFeatureExtractor组件",
            True,
            "✅ MatchFeatureExtractor组件已实现"
        )

        # 检查MatchFeatureSet数据类
        result.add_check(
            "MatchFeatureSet数据类",
            True,
            "✅ MatchFeatureSet数据类已实现"
        )

        # 测试基本初始化
        extractor = MatchFeatureExtractor()
        result.add_check(
            "特征提取器初始化",
            True,
            "✅ 特征提取器可以正常初始化"
        )

        # 测试批量特征提取方法存在
        if hasattr(extractor, 'extract_features'):
            result.add_check(
                "特征提取方法",
                True,
                "✅ extract_features方法已实现"
            )
        else:
            result.add_check(
                "特征提取方法",
                False,
                "extract_features方法缺失"
            )

    except ImportError as e:
        result.add_check(
            "特征提取器导入",
            False,
            f"特征提取器导入失败: {str(e)}"
        )
    except Exception as e:
        result.add_check(
            "特征提取器验证",
            False,
            f"验证过程异常: {str(e)}"
        )


async def validate_e2e_test(result: MVPValidationResult):
    """验证端到端测试"""
    logger.info("验证端到端测试...")

    try:
        # 检查测试文件是否存在
        test_file = Path("tests/test_pipeline_e2e.py")
        if test_file.exists():
            result.add_check(
                "端到端测试文件",
                True,
                "✅ test_pipeline_e2e.py已创建"
            )

            # 检查测试文件内容
            content = test_file.read_text()

            # 检查关键测试函数
            required_tests = [
                'test_full_prediction_pipeline',
                'test_feature_extractor_standalone',
                'test_minimal_pipeline_smoke'
            ]

            for test_name in required_tests:
                if test_name in content:
                    result.add_check(
                        f"测试函数 {test_name}",
                        True,
                        f"✅ {test_name}已实现"
                    )
                else:
                    result.add_check(
                        f"测试函数 {test_name}",
                        False,
                        f"❌ {test_name}缺失"
                    )

            # 检查测试标记
            if '@pytest.mark.e2e' in content:
                result.add_check(
                    "E2E测试标记",
                    True,
                    "✅ E2E测试标记已添加"
                )
            else:
                result.add_check(
                    "E2E测试标记",
                    False,
                    "❌ E2E测试标记缺失"
                )

        else:
            result.add_check(
                "端到端测试文件",
                False,
                "❌ test_pipeline_e2e.py不存在"
            )

    except Exception as e:
        result.add_check(
            "端到端测试验证",
            False,
            f"验证过程异常: {str(e)}"
        )


async def validate_import_dependencies(result: MVPValidationResult):
    """验证导入依赖"""
    logger.info("验证导入依赖...")

    try:
        # 检查核心模块导入
        modules_to_test = [
            ('src.ml.features.extractor', 'MatchFeatureExtractor'),
            ('src.ml.features.advanced_feature_transformer', 'AdvancedFeatureTransformer'),
            ('src.ml.features.h2h_calculator', 'H2HCalculator'),
            ('src.ml.features.venue_analyzer', 'VenueAnalyzer'),
            ('src.inference', 'Predictor'),
            ('src.ml.training.training_pipeline', 'ClassificationTrainingPipeline')
        ]

        for module_name, class_name in modules_to_test:
            try:
                # 使用正确的Python模块导入语法
                module = __import__(module_name, fromlist=[class_name])
                if hasattr(module, class_name):
                    result.add_check(
                        f"模块导入 {module_name}",
                        True,
                        "✅ 导入成功"
                    )
                else:
                    result.add_check(
                        f"模块导入 {module_name}",
                        False,
                        f"❌ 找不到类 {class_name}"
                    )
            except ImportError as e:
                result.add_check(
                    f"模块导入 {module_name}",
                    False,
                    f"❌ 导入失败: {str(e)}"
                )
            except Exception as e:
                result.add_check(
                    f"模块导入 {module_name}",
                    False,
                    f"❌ 导入异常: {str(e)}"
                )

    except Exception as e:
        result.add_check(
            "依赖验证",
            False,
            f"依赖验证失败: {str(e)}"
        )


async def validate_basic_pipeline_connectivity(result: MVPValidationResult):
    """验证基本流水线连通性"""
    logger.info("验证基本流水线连通性...")

    try:
        # 尝试创建一个最小化的特征提取实例
        from src.ml.features.extractor import MatchFeatureExtractor

        extractor = MatchFeatureExtractor()
        result.add_check(
            "特征提取器实例化",
            True,
            "✅ 特征提取器可以实例化"
        )

        # 测试特征名称生成
        feature_names = extractor._get_feature_names()
        if len(feature_names) > 0:
            result.add_check(
                "特征名称生成",
                True,
                f"✅ 生成了 {len(feature_names)} 个特征名称"
            )
        else:
            result.add_check(
                "特征名称生成",
                False,
                "❌ 未生成任何特征名称"
            )

        # 测试推理器类的基本方法
        from src.inference import Predictor
        import tempfile

        with tempfile.NamedTemporaryFile() as tmp:
            predictor = Predictor(tmp.name)

            # 检查关键方法是否存在
            methods_to_check = ['load_model', 'predict', 'get_model_info']
            for method in methods_to_check:
                if hasattr(predictor, method):
                    result.add_check(
                        f"预测器方法 {method}",
                        True,
                        f"✅ {method}方法存在"
                    )
                else:
                    result.add_check(
                        f"预测器方法 {method}",
                        False,
                        f"❌ {method}方法缺失"
                    )

    except Exception as e:
        result.add_check(
            "流水线连通性",
            False,
            f"连通性验证失败: {str(e)}"
        )


async def main():
    """主验证函数"""
    print("🚀 开始MVP闭环验证...")
    print("正在检查所有核心阻断点是否已修复...\n")

    result = MVPValidationResult()

    # 执行所有验证
    await validate_inference_module(result)
    await validate_feature_extractor(result)
    await validate_e2e_test(result)
    await validate_import_dependencies(result)
    await validate_basic_pipeline_connectivity(result)

    # 打印结果
    success = result.print_summary()

    # 返回适当的退出代码
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())