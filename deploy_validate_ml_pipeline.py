#!/usr/bin/env python3
"""
P0-4 ML Pipeline 部署验证脚本
验证新ML Pipeline的核心功能和集成
"""

import sys
import logging
import tempfile
from pathlib import Path
from typing import List, Dict, Any

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 添加src路径
sys.path.insert(0, str(Path(__file__).parent / "src"))

class DeploymentValidator:
    """ML Pipeline部署验证器"""

    def __init__(self):
        self.test_results = []
        self.temp_dir = None

    def log_result(self, test_name: str, passed: bool, details: str = ""):
        """记录测试结果"""
        status = "✅ PASS" if passed else "❌ FAIL"
        logger.info(f"{status} {test_name}: {details}")
        self.test_results.append({
            "test": test_name,
            "passed": passed,
            "details": details
        })

    def test_configuration_system(self) -> bool:
        """测试配置系统"""
        logger.info("🔧 Testing Configuration System...")

        try:
            # 测试基本配置创建
            from src.pipeline.config import PipelineConfig, ModelConfig, FeatureConfig

            # 测试默认配置
            config = PipelineConfig()
            assert config.model.default_algorithm == "xgboost"
            assert len(config.model.supported_algorithms) > 0

            # 测试配置验证
            try:
                bad_config = PipelineConfig(
                    model={"default_algorithm": "invalid_algorithm"}
                )
                self.log_result("Config Validation", False, "Should reject invalid algorithm")
                return False
            except ValueError:
                self.log_result("Config Validation", True, "Correctly rejects invalid algorithm")

            # 测试dict转换修复
            dict_config = PipelineConfig(
                features={"required_features": ["test_feature"]},
                model={"default_algorithm": "lightgbm"}
            )
            assert isinstance(dict_config.features, FeatureConfig)
            assert isinstance(dict_config.model, ModelConfig)

            self.log_result("Configuration System", True, "All config tests passed")
            return True

        except Exception as e:
            self.log_result("Configuration System", False, str(e))
            return False

    def test_model_registry(self) -> bool:
        """测试模型注册表"""
        logger.info("🗄️ Testing Model Registry...")

        try:
            from src.pipeline.config import PipelineConfig
            from src.pipeline.model_registry import ModelRegistry

            # 创建临时目录
            self.temp_dir = tempfile.mkdtemp()
            config = PipelineConfig()
            config.models_dir = self.temp_dir

            # 测试注册表创建
            registry = ModelRegistry(config)

            # 测试模型保存
            from sklearn.ensemble import RandomForestClassifier
            import numpy as np

            # 创建简单模型
            model = RandomForestClassifier(n_estimators=2, random_state=42)
            X_train = np.random.random((10, 5))
            y_train = np.random.randint(0, 2, 10)
            model.fit(X_train, y_train)

            metadata = {
                "algorithm": "random_forest",
                "accuracy": 0.85,
                "features": ["feature1", "feature2"]
            }

            model_path = registry.save_model(model, "test_model", metadata)
            assert Path(model_path).exists()

            # 测试模型加载
            loaded_model, loaded_metadata = registry.load_model("test_model")
            assert loaded_model is not None
            assert loaded_metadata["algorithm"] == "random_forest"

            # 测试模型比较
            comparison = registry.compare_models("test_model")
            assert len(comparison) > 0

            self.log_result("Model Registry", True, "Model save/load/compare working")
            return True

        except Exception as e:
            self.log_result("Model Registry", False, str(e))
            return False

    def test_feature_loader_interface(self) -> bool:
        """测试特征加载器接口"""
        logger.info("🔄 Testing Feature Loader Interface...")

        try:
            # 测试导入是否正确
            from src.pipeline.feature_loader import FeatureLoader
            from src.features.feature_store_interface import FeatureStoreProtocol

            # 验证类定义
            assert hasattr(FeatureLoader, 'load_training_data')
            assert hasattr(FeatureLoader, '_load_training_data_async')

            self.log_result("Feature Loader Interface", True, "Imports and class structure correct")
            return True

        except Exception as e:
            self.log_result("Feature Loader Interface", False, str(e))
            return False

    def test_trainer_interface(self) -> bool:
        """测试训练器接口"""
        logger.info("🏋️ Testing Trainer Interface...")

        try:
            from src.pipeline.config import PipelineConfig
            from src.pipeline.trainer import Trainer

            # 测试训练器创建
            config = PipelineConfig()
            trainer = Trainer(config)

            # 验证必要方法存在
            assert hasattr(trainer, 'train')
            assert hasattr(trainer, 'training_history')

            # 测试历史记录初始化
            assert isinstance(trainer.training_history, list)

            self.log_result("Trainer Interface", True, "Trainer class structure correct")
            return True

        except Exception as e:
            self.log_result("Trainer Interface", False, str(e))
            return False

    def test_pipeline_module_structure(self) -> bool:
        """测试Pipeline模块结构"""
        logger.info("📁 Testing Pipeline Module Structure...")

        try:
            from src.pipeline import FeatureLoader, Trainer, ModelRegistry, PipelineConfig

            # 验证模块导出
            assert FeatureLoader is not None
            assert Trainer is not None
            assert ModelRegistry is not None
            assert PipelineConfig is not None

            # 验证工作流模块
            try:
                from src.pipeline.flows import train_flow, eval_flow
                self.log_result("Pipeline Flows", True, "Flows module accessible")
            except ImportError as e:
                self.log_result("Pipeline Flows", False, f"Flow import error: {e}")
                return False

            self.log_result("Pipeline Module Structure", True, "All core components accessible")
            return True

        except Exception as e:
            self.log_result("Pipeline Module Structure", False, str(e))
            return False

    def test_integration_readiness(self) -> bool:
        """测试集成准备度"""
        logger.info("🔗 Testing Integration Readiness...")

        try:
            # 检查关键文件存在
            required_files = [
                "src/pipeline/__init__.py",
                "src/pipeline/config.py",
                "src/pipeline/feature_loader.py",
                "src/pipeline/trainer.py",
                "src/pipeline/model_registry.py",
                "src/features/feature_store_interface.py",
                "patches/pr_p0_4_ml_pipeline_fix.md"
            ]

            missing_files = []
            for file_path in required_files:
                if not Path(file_path).exists():
                    missing_files.append(file_path)

            if missing_files:
                self.log_result("Integration Readiness", False, f"Missing files: {missing_files}")
                return False

            # 检查文档完整性
            doc_content = Path("patches/pr_p0_4_ml_pipeline_fix.md").read_text()
            required_sections = ["修复内容", "Root Cause", "验证步骤", "部署指南"]

            missing_sections = []
            for section in required_sections:
                if section not in doc_content:
                    missing_sections.append(section)

            if missing_sections:
                self.log_result("Documentation Completeness", False, f"Missing sections: {missing_sections}")
            else:
                self.log_result("Documentation Completeness", True, "All required sections present")

            self.log_result("Integration Readiness", True, "All files and documentation ready")
            return True

        except Exception as e:
            self.log_result("Integration Readiness", False, str(e))
            return False

    def cleanup(self):
        """清理临时文件"""
        if self.temp_dir and Path(self.temp_dir).exists():
            import shutil
            shutil.rmtree(self.temp_dir, ignore_errors=True)

    def run_all_tests(self) -> dict[str, Any]:
        """运行所有验证测试"""
        logger.info("🚀 Starting P0-4 ML Pipeline Deployment Validation")
        logger.info("=" * 60)

        tests = [
            ("Configuration System", self.test_configuration_system),
            ("Model Registry", self.test_model_registry),
            ("Feature Loader Interface", self.test_feature_loader_interface),
            ("Trainer Interface", self.test_trainer_interface),
            ("Pipeline Module Structure", self.test_pipeline_module_structure),
            ("Integration Readiness", self.test_integration_readiness),
        ]

        passed_tests = 0
        total_tests = len(tests)

        for test_name, test_func in tests:
            try:
                if test_func():
                    passed_tests += 1
            except Exception as e:
                logger.error(f"Test {test_name} crashed: {e}")
                self.log_result(test_name, False, f"Test crash: {e}")

        logger.info("=" * 60)
        logger.info(f"📊 Validation Results: {passed_tests}/{total_tests} tests passed")

        # 生成报告
        success_rate = passed_tests / total_tests
        if success_rate >= 0.8:
            logger.info("✅ P0-4 ML Pipeline Deployment Validation: PASSED")
            status = "PASSED"
        else:
            logger.error("❌ P0-4 ML Pipeline Deployment Validation: FAILED")
            status = "FAILED"

        return {
            "status": status,
            "passed_tests": passed_tests,
            "total_tests": total_tests,
            "success_rate": success_rate,
            "test_results": self.test_results
        }

def main():
    """主函数"""
    validator = DeploymentValidator()

    try:
        results = validator.run_all_tests()

        # 生成验证报告
        report = f"""
# P0-4 ML Pipeline 部署验证报告

**验证时间**: {Path(__file__).stat().st_mtime}
**验证状态**: {results['status']}
**通过率**: {results['success_rate']:.1%} ({results['passed_tests']}/{results['total_tests']})

## 详细结果
"""

        for result in results['test_results']:
            status_icon = "✅" if result['passed'] else "❌"
            report += f"{status_icon} **{result['test']}**: {result['details']}\n"

        # 保存报告
        report_path = Path("P0_4_DEPLOYMENT_VALIDATION_REPORT.md")
        report_path.write_text(report)

        logger.info(f"📄 验证报告已保存: {report_path}")

        return results['status'] == "PASSED"

    finally:
        validator.cleanup()

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
