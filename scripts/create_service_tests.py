#!/usr/bin/env python3
"""
服务测试生成器
自动为业务服务生成完整的单元测试和集成测试
"""

import os
import sys
import ast
import json
import inspect
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple, Set
from dataclasses import dataclass
from collections import defaultdict
import re
from datetime import datetime

@dataclass
class TestConfig:
    """测试配置"""
    target_module: str
    output_file: str
    test_types: List[str]
    include_mocks: bool = True
    include_fixtures: bool = True
    include_parametrized: bool = True

class ServiceAnalyzer:
    """服务分析器"""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.src_dir = project_root / "src"

    def analyze_service_module(self, module_path: str) -> Dict[str, Any]:
        """分析服务模块"""
        print(f"🔍 分析服务模块: {module_path}")

        try:
            # 导入模块
            sys.path.insert(0, str(self.src_dir))
            module = __import__(module_path, fromlist=['*'])

            analysis = {
                'module_name': module_path,
                'classes': [],
                'functions': [],
                'imports': [],
                'dependencies': set()
            }

            # 分析AST结构
            module_file = self.src_dir / f"{module_path.replace('.', '/')}.py"
            if module_file.exists():
                with open(module_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                tree = ast.parse(content)

                for node in ast.walk(tree):
                    if isinstance(node, ast.ClassDef):
                        class_info = self._analyze_class(node, module)
                        analysis['classes'].append(class_info)
                    elif isinstance(node, ast.FunctionDef):
                        if not node.name.startswith('_'):
                            func_info = self._analyze_function(node)
                            analysis['functions'].append(func_info)
                    elif isinstance(node, ast.Import):
                        for alias in node.names:
                            analysis['imports'].append(alias.name)
                    elif isinstance(node, ast.ImportFrom):
                        if node.module:
                            analysis['imports'].append(node.module)

            # 分析运行时信息
            for name, obj in module.__dict__.items():
                if inspect.isclass(obj) and not name.startswith('_'):
                    if name not in [c['name'] for c in analysis['classes']]:
                        class_info = self._analyze_runtime_class(obj)
                        analysis['classes'].append(class_info)
                elif inspect.isfunction(obj) and not name.startswith('_'):
                    if name not in [f['name'] for f in analysis['functions']]:
                        func_info = self._analyze_runtime_function(obj)
                        analysis['functions'].append(func_info)

            print(f"✅ 发现 {len(analysis['classes'])} 个类,
    {len(analysis['functions'])} 个函数")
            return analysis

        except Exception as e:
            print(f"❌ 分析模块失败: {e}")
            return {}

    def _analyze_class(self, node: ast.ClassDef, module) -> Dict[str, Any]:
        """分析类定义"""
        methods = []
        properties = []
        dependencies = set()

        for item in node.body:
            if isinstance(item, ast.FunctionDef):
                method_info = self._analyze_function(item)
                methods.append(method_info)
                # 分析方法依赖
                for decorator in item.decorator_list:
                    if isinstance(decorator, ast.Name):
                        dependencies.add(decorator.id)

        return {
            'name': node.name,
            'type': 'class',
            'methods': methods,
            'properties': properties,
            'dependencies': list(dependencies),
            'base_classes': [base.id if isinstance(base,
    ast.Name) else str(base) for base in node.bases]
        }

    def _analyze_function(self, node: ast.FunctionDef) -> Dict[str, Any]:
        """分析函数定义"""
        args = []
        returns = None
        dependencies = set()

        # 分析参数
        for arg in node.args.args:
            args.append({
                'name': arg.arg,
                'type': None,  # 可以进一步分析类型注解
                'default': None
            })

        # 分析返回类型
        if node.returns:
            if isinstance(node.returns, ast.Name):
                returns = node.returns.id
            else:
                returns = 'complex_type'

        # 分析函数体中的依赖
        for sub_node in ast.walk(node):
            if isinstance(sub_node, ast.Call):
                if isinstance(sub_node.func, ast.Name):
                    dependencies.add(sub_node.func.id)
                elif isinstance(sub_node.func, ast.Attribute):
                    dependencies.add(sub_node.func.attr)

        return {
            'name': node.name,
            'type': 'function',
            'args': args,
            'returns': returns,
            'dependencies': list(dependencies),
            'is_async': isinstance(node, ast.AsyncFunctionDef),
            'decorators': [d.id if isinstance(d,
    ast.Name) else str(d) for d in node.decorator_list if isinstance(d,
    ast.Name)]
        }

    def _analyze_runtime_class(self, cls) -> Dict[str, Any]:
        """分析运行时类"""
        methods = []
        dependencies = set()

        for name, method in inspect.getmembers(cls, predicate=inspect.isfunction):
            if not name.startswith('_'):
                method_info = self._analyze_runtime_function(method)
                method_info['name'] = name
                methods.append(method_info)

        return {
            'name': cls.__name__,
            'type': 'class',
            'methods': methods,
            'properties': [],
            'dependencies': list(dependencies),
            'base_classes': [base.__name__ for base in cls.__bases__]
        }

    def _analyze_runtime_function(self, func) -> Dict[str, Any]:
        """分析运行时函数"""
        try:
            sig = inspect.signature(func)
            args = []

            for param_name, param in sig.parameters.items():
                args.append({
                    'name': param_name,
                    'type': param.annotation if param.annotation != inspect.Parameter.empty else None,
                    'default': param.default if param.default != inspect.Parameter.empty else None
                })

            return {
                'name': func.__name__,
                'type': 'function',
                'args': args,
                'returns': sig.return_annotation if sig.return_annotation != inspect.Signature.empty else None,
                'dependencies': [],
                'is_async': inspect.iscoroutinefunction(func),
                'decorators': []
            }
        except Exception as e:
            print(f"⚠️  分析函数失败: {func.__name__} - {e}")
            return {
                'name': func.__name__,
                'type': 'function',
                'args': [],
                'returns': None,
                'dependencies': [],
                'is_async': False,
                'decorators': []
            }

class ServiceTestGenerator:
    """服务测试生成器"""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.src_dir = project_root / "src"
        self.test_dir = project_root / "tests"

    def generate_tests_for_service(self,
    analysis: Dict[str,
    Any],
    config: TestConfig) -> str:
        """为服务生成测试"""
        print(f"🧪 为服务 {analysis['module_name']} 生成测试...")

        test_content = f'''"""
自动生成的服务测试
模块: {analysis['module_name']}
生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

注意: 这是一个自动生成的测试文件，请根据实际业务逻辑进行调整和完善
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock, MagicMock
import asyncio
from datetime import datetime, timedelta
from typing import Any, Dict, List

# 导入目标模块
'''

        # 添加导入语句
        test_content += f"from {analysis['module_name']} import (\n"

        # 导入类
        for cls in analysis['classes']:
            test_content += f"    {cls['name']},\n"

        # 导入独立函数
        for func in analysis['functions']:
            test_content += f"    {func['name']},\n"

        test_content += ")\n\n"

        # 添加fixtures
        if config.include_fixtures:
            test_content += self._generate_fixtures(analysis)

        # 为每个类生成测试
        for cls in analysis['classes']:
            test_content += self._generate_class_tests(cls, config)

        # 为每个函数生成测试
        for func in analysis['functions']:
            test_content += self._generate_function_tests(func, config)

        return test_content

    def _generate_fixtures(self, analysis: Dict[str, Any]) -> str:
        """生成测试fixtures"""
        fixtures = '''
@pytest.fixture
def sample_data():
    """示例数据fixture"""
    return {
        "id": 1,
        "name": "test",
        "created_at": datetime.now(),
        "updated_at": datetime.now()
    }

@pytest.fixture
def mock_repository():
    """模拟仓库fixture"""
    repo = Mock()
    repo.get_by_id.return_value = Mock()
    repo.get_all.return_value = []
    repo.save.return_value = Mock()
    repo.delete.return_value = True
    return repo

@pytest.fixture
def mock_service():
    """模拟服务fixture"""
    service = Mock()
    service.process.return_value = {"status": "success"}
    service.validate.return_value = True
    return service

'''
        return fixtures

    def _generate_class_tests(self, cls: Dict[str, Any], config: TestConfig) -> str:
        """为类生成测试"""
        class_name = cls['name']
        tests = f"""
class Test{class_name}:
    \"\"\"{class_name} 测试类\"\"\"

    def setup_method(self):
        \"\"\"每个测试方法前的设置\"\"\"
        self.instance = {class_name}()

    def teardown_method(self):
        \"\"\"每个测试方法后的清理\"\"\"
        pass

    def test_init(self):
        \"\"\"测试初始化\"\"\"
        assert self.instance is not None
        assert isinstance(self.instance, {class_name})

"""

        # 为每个方法生成测试
        for method in cls['methods']:
            tests += self._generate_method_tests(class_name, method, config)

        return tests

    def _generate_method_tests(self,
    class_name: str,
    method: Dict[str,
    Any],
    config: TestConfig) -> str:
        """为方法生成测试"""
        method_name = method['name']
        tests = f"""
    def test_{method_name}_basic(self):
        \"\"\"测试 {method_name} 基本功能\"\"\"
        # TODO: 实现具体的测试逻辑
        result = self.instance.{method_name}()
        assert result is not None

"""

        # 如果方法有参数，生成参数化测试
        if method['args'] and len(method['args']) > 1:  # 排除self
            tests += f"""
    @pytest.mark.parametrize("test_input, expected", [
        # TODO: 添加测试参数组合
        (None, None),
    ])
    def test_{method_name}_parametrized(self, test_input, expected):
        \"\"\"测试 {method_name} 参数化\"\"\"
        # TODO: 实现参数化测试
        if test_input is not None:
            result = self.instance.{method_name}(test_input)
            assert result == expected

"""

        # 如果是异步方法，生成异步测试
        if method['is_async']:
            tests = tests.replace("def test_", "async def test_")
            tests = tests.replace("assert result is not None", "result = await result")

        # 如果需要mock，生成mock测试
        if config.include_mocks and method['dependencies']:
            tests += f"""
    @patch('object_to_mock')
    def test_{method_name}_with_mock(self, mock_obj):
        \"\"\"测试 {method_name} 使用mock\"\"\"
        # TODO: 配置mock对象
        mock_obj.return_value = "mocked_result"

        result = self.instance.{method_name}()
        assert result is not None
        mock_obj.assert_called_once()

"""

        return tests

    def _generate_function_tests(self, func: Dict[str, Any], config: TestConfig) -> str:
        """为函数生成测试"""
        func_name = func['name']
        tests = f"""

def test_{func_name}_basic():
    \"\"\"测试 {func_name} 基本功能\"\"\"
    # TODO: 实现具体的测试逻辑
    from {func.get('module', 'src')} import {func_name}

    result = {func_name}()
    assert result is not None

"""

        # 如果函数有参数，生成参数化测试
        if func['args'] and config.include_parametrized:
            tests += f"""
@pytest.mark.parametrize("test_input, expected", [
    # TODO: 添加测试参数组合
    (None, None),
    ({{"key": "value"}}, {{"processed": True}}),
])
def test_{func_name}_parametrized(test_input, expected):
    \"\"\"测试 {func_name} 参数化\"\"\"
    from {func.get('module', 'src')} import {func_name}

    result = {func_name}(test_input)
    assert result == expected

"""

        # 如果是异步函数，生成异步测试
        if func['is_async']:
            tests = tests.replace("def test_", "async def test_")
            tests = tests.replace("result = ", "result = await ")

        # 如果需要mock，生成mock测试
        if config.include_mocks and func['dependencies']:
            tests += f"""
@patch('dependency_to_mock')
def test_{func_name}_with_mock(mock_obj):
    \"\"\"测试 {func_name} 使用mock\"\"\"
    from {func.get('module', 'src')} import {func_name}

    # TODO: 配置mock对象
    mock_obj.return_value = "mocked_value"

    result = {func_name}()
    assert result is not None
    mock_obj.assert_called_once()

"""

        return tests

class ServiceTestExecutor:
    """服务测试执行器"""

    def __init__(self, project_root: Path = None):
        self.project_root = project_root or Path.cwd()
        self.analyzer = ServiceAnalyzer(self.project_root)
        self.generator = ServiceTestGenerator(self.project_root)

    def discover_services(self) -> List[str]:
        """发现服务模块"""
        print("🔍 发现服务模块...")

        services = []
        src_dir = self.project_root / "src"

        # 查找服务目录
        service_dirs = [
            "services",
            "domain/services",
            "business",
            "core"
        ]

        for service_dir in service_dirs:
            service_path = src_dir / service_dir
            if service_path.exists():
                for file_path in service_path.glob("*.py"):
                    if file_path.name != "__init__.py":
                        # 构建模块路径
                        rel_path = file_path.relative_to(src_dir)
                        module_name = str(rel_path.with_suffix("")).replace("/", ".")
                        services.append(module_name)

        # 查找其他可能的服务文件
        for pattern in ["*_service.py", "*_service_impl.py", "service_*.py"]:
            for file_path in src_dir.rglob(pattern):
                rel_path = file_path.relative_to(src_dir)
                module_name = str(rel_path.with_suffix("")).replace("/", ".")
                if module_name not in services:
                    services.append(module_name)

        print(f"✅ 发现 {len(services)} 个服务模块")
        return sorted(services)

    def generate_tests_for_service(self, service_module: str) -> bool:
        """为指定服务生成测试"""
        print(f"🎯 为服务 {service_module} 生成测试...")

        # 分析服务模块
        analysis = self.analyzer.analyze_service_module(service_module)
        if not analysis:
            print(f"❌ 无法分析服务模块: {service_module}")
            return False

        # 创建测试配置
        config = TestConfig(
            target_module=service_module,
            output_file=f"tests/unit/test_{service_module.replace('.', '_')}.py",
            test_types=["unit", "integration"],
            include_mocks=True,
            include_fixtures=True,
            include_parametrized=True
        )

        # 生成测试代码
        test_content = self.generator.generate_tests_for_service(analysis, config)

        # 保存测试文件
        test_file = self.project_root / config.output_file
        test_file.parent.mkdir(parents=True, exist_ok=True)

        try:
            with open(test_file, 'w', encoding='utf-8') as f:
                f.write(test_content)
            print(f"✅ 测试文件已生成: {test_file}")
            return True
        except Exception as e:
            print(f"❌ 保存测试文件失败: {e}")
            return False

    def generate_all_service_tests(self) -> Dict[str, bool]:
        """为所有服务生成测试"""
        print("🚀 开始为所有服务生成测试")
        print("=" * 50)

        services = self.discover_services()
        results = {}

        for service in services:
            print(f"\n📋 处理服务: {service}")
            success = self.generate_tests_for_service(service)
            results[service] = success

        # 生成报告
        self._generate_generation_report(results)

        return results

    def _generate_generation_report(self, results: Dict[str, bool]):
        """生成测试生成报告"""
        total_services = len(results)
        successful_services = sum(1 for success in results.values() if success)
        failed_services = total_services - successful_services

        report = f"""# 服务测试生成报告

**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**总服务数**: {total_services}
**成功生成**: {successful_services}
**生成失败**: {failed_services}
**成功率**: {(successful_services / total_services * 100):.1f}%

## 📊 详细结果

### ✅ 成功生成的服务
"""

        for service, success in results.items():
            if success:
                report += f"- {service}\n"

        if failed_services > 0:
            report += "\n### ❌ 生成失败的服务\n"
            for service, success in results.items():
                if not success:
                    report += f"- {service}\n"

        report += f"""
## 🚀 下一步行动

1. **检查生成的测试**: 查看生成的测试文件，根据实际业务逻辑调整
2. **完善测试逻辑**: 补充TODO标记的测试实现
3. **运行测试验证**: 执行生成的测试确保可正常运行
4. **集成到CI/CD**: 将测试集成到持续集成流程

## 📁 生成的测试文件

"""

        for service, success in results.items():
            if success:
                test_file = f"tests/unit/test_{service.replace('.', '_')}.py"
                report += f"- `{test_file}`\n"

        # 保存报告
        report_dir = self.project_root / "reports"
        report_dir.mkdir(exist_ok=True)
        report_file = report_dir / f"service_test_generation_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"

        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report)

        print(f"\n📄 生成报告已保存: {report_file}")

def create_prediction_service_test():
    """创建预测服务测试"""
    content = '''"""预测服务测试"""
import pytest
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from datetime import datetime
from src.models.prediction_service import PredictionService
from src.database.models.match import Match
from src.database.models.team import Team
from src.database.models.prediction import Prediction

class TestPredictionService:
    """预测服务测试"""

    @pytest.fixture
    def mock_repository(self):
        """模拟预测仓库"""
        return Mock()

    @pytest.fixture
    def mock_model(self):
        """模拟ML模型"""
        mock_model = Mock()
        mock_model.predict.return_value = {
            "home_win": 0.65,
            "draw": 0.20,
            "away_win": 0.15
        }
        return mock_model

    @pytest.fixture
    def service(self, mock_repository, mock_model):
        """创建预测服务"""
        return PredictionService(
            repository=mock_repository,
            model=mock_model
        )

    def test_predict_match(self, service, mock_repository, mock_model):
        """测试比赛预测"""
        # 准备测试数据
        home_team = Team(id=1, name="Team A")
        away_team = Team(id=2, name="Team B")
        match = Match(
            id=1,
            home_team=home_team,
            away_team=away_team,
            date=datetime(2024, 1, 1, 15, 0)
        )

        # 设置模拟返回
        mock_repository.get_match_features.return_value = {
            "home_form": [1, 1, 0],
            "away_form": [0, 0, 1],
            "head_to_head": {"home_wins": 2, "away_wins": 1}
        }

        # 调用方法
        result = service.predict_match(match.id)

        # 验证
        assert result["predicted_winner"] in ["home", "draw", "away"]
        assert "confidence" in result
        assert "probabilities" in result
        mock_model.predict.assert_called_once()

    def test_batch_predict(self, service, mock_repository, mock_model):
        """测试批量预测"""
        # 准备测试数据
        match_ids = [1, 2, 3]

        # 设置模拟返回
        mock_repository.get_matches_by_ids.return_value = [
            Mock(id=1), Mock(id=2), Mock(id=3)
        ]

        # 调用方法
        results = service.batch_predict(match_ids)

        # 验证
        assert len(results) == 3
        assert all("predicted_winner" in r for r in results)

    def test_get_prediction_accuracy(self, service, mock_repository):
        """测试获取预测准确率"""
        # 设置模拟返回
        mock_repository.get_completed_predictions.return_value = [
            Mock(is_correct=True),
            Mock(is_correct=True),
            Mock(is_correct=False),
            Mock(is_correct=True)
        ]

        # 调用方法
        accuracy = service.get_accuracy(30)  # 最近30天

        # 验证
        assert accuracy == 0.75  # 3/4 正确

    def test_update_prediction(self, service, mock_repository):
        """测试更新预测"""
        prediction_id = 1
        update_data = {
            "confidence": 0.90,
            "notes": "Updated prediction"
        }

        # 设置模拟返回
        mock_prediction = Mock(spec=Prediction)
        mock_repository.get_by_id.return_value = mock_prediction

        # 调用方法
        result = service.update_prediction(prediction_id, update_data)

        # 验证
        assert result == mock_prediction
        mock_repository.save.assert_called_once()

    def test_validate_prediction_input(self, service):
        """测试预测输入验证"""
        # 有效输入
        valid_input = {
            "match_id": 1,
            "features": {
                "home_form": [1, 1, 0],
                "away_form": [0, 1, 1]
            }
        }
        assert service.validate_input(valid_input) is True

        # 无效输入（缺少必要字段）
        invalid_input = {
            "features": {}
        }
        assert service.validate_input(invalid_input) is False

    def test_get_feature_importance(self, service, mock_model):
        """测试获取特征重要性"""
        # 设置模拟返回
        mock_model.get_feature_importance.return_value = {
            "home_form": 0.30,
            "away_form": 0.25,
            "head_to_head": 0.20,
            "goals_average": 0.15,
            "injuries": 0.10
        }

        # 调用方法
        importance = service.get_feature_importance()

        # 验证
        assert "home_form" in importance
        assert importance["home_form"] == 0.30

    def test_calculate_confidence(self, service):
        """测试计算置信度"""
        probabilities = {
            "home_win": 0.65,
            "draw": 0.20,
            "away_win": 0.15
        }

        # 计算置信度（最高概率）
        confidence = service.calculate_confidence(probabilities)
        assert confidence == 0.65

    def test_predict_with_outcome(self, service, mock_repository):
        """测试带结果的预测"""
        # 准备测试数据
        match_id = 1
        actual_result = "home"

        # 设置模拟返回
        mock_prediction = Mock(
            predicted_winner="home",
            confidence=0.70,
            is_correct=True
        )
        mock_repository.get_prediction_by_match.return_value = mock_prediction

        # 调用方法
        result = service.predict_with_outcome(match_id, actual_result)

        # 验证
        assert result["correct"] is True
        assert result["predicted"] == actual_result

    def test_get_model_performance(self, service, mock_repository):
        """测试获取模型性能"""
        # 设置模拟返回
        mock_repository.get_performance_metrics.return_value = {
            "accuracy": 0.75,
            "precision": 0.80,
            "recall": 0.70,
            "f1_score": 0.75
        }

        # 调用方法
        performance = service.get_model_performance()

        # 验证
        assert performance["accuracy"] == 0.75
        assert "precision" in performance
        assert "recall" in performance
        assert "f1_score" in performance
'''

    file_path = Path("tests/unit/services/test_prediction_service.py")
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(content)
    print(f"✅ 创建文件: {file_path}")


def create_data_processing_service_test():
    """创建数据处理服务测试"""
    content = '''"""数据处理服务测试"""
import pytest
from unittest.mock import Mock, patch, MagicMock, AsyncMock
import pandas as pd
from datetime import datetime
from src.services.data_processing import DataProcessingService

class TestDataProcessingService:
    """数据处理服务测试"""

    @pytest.fixture
    def mock_repository(self):
        """模拟数据仓库"""
        return Mock()

    @pytest.fixture
    def mock_cache(self):
        """模拟缓存"""
        return Mock()

    @pytest.fixture
    def service(self, mock_repository, mock_cache):
        """创建数据处理服务"""
        return DataProcessingService(
            repository=mock_repository,
            cache=mock_cache
        )

    def test_process_match_data(self, service, mock_repository):
        """测试处理比赛数据"""
        # 准备测试数据
        raw_data = {
            "match_id": 1,
            "home_team": "Team A",
            "away_team": "Team B",
            "date": "2024-01-01",
            "score": "2-1"
        }

        # 设置模拟返回
        mock_repository.save_processed_data.return_value = True

        # 调用方法
        result = service.process_match(raw_data)

        # 验证
        assert result is True
        mock_repository.save_processed_data.assert_called_once()

    def test_clean_player_data(self, service):
        """测试清理球员数据"""
        # 准备脏数据
        dirty_data = {
            "name": "John Doe ",
            "age": " 25",
            "position": "  MIDFIELDER  ",
            "salary": "50000.00"
        }

        # 调用方法
        cleaned_data = service.clean_player_data(dirty_data)

        # 验证
        assert cleaned_data["name"] == "John Doe"
        assert cleaned_data["age"] == 25
        assert cleaned_data["position"] == "MIDFIELDER"
        assert cleaned_data["salary"] == 50000.0

    def test_validate_match_data(self, service):
        """测试验证比赛数据"""
        # 有效数据
        valid_data = {
            "match_id": 1,
            "home_team_id": 1,
            "away_team_id": 2,
            "date": datetime(2024, 1, 1),
            "league": "Premier League"
        }
        assert service.validate_match_data(valid_data) is True

        # 无效数据（缺少字段）
        invalid_data = {
            "match_id": 1,
            "home_team_id": 1
        }
        assert service.validate_match_data(invalid_data) is False

    def test_aggregate_team_stats(self, service, mock_repository):
        """测试聚合球队统计"""
        # 设置模拟返回
        mock_repository.get_team_matches.return_value = [
            {"team_id": 1, "goals_scored": 2, "goals_conceded": 1},
            {"team_id": 1, "goals_scored": 3, "goals_conceded": 2},
            {"team_id": 1, "goals_scored": 1, "goals_conceded": 1}
        ]

        # 调用方法
        stats = service.aggregate_team_stats(1)

        # 验证
        assert stats["total_goals_scored"] == 6
        assert stats["total_goals_conceded"] == 4
        assert stats["matches_played"] == 3
        assert stats["average_goals_scored"] == 2.0

    def test_transform_data_format(self, service):
        """测试转换数据格式"""
        # 准备测试数据
        data_list = [
            {"match_id": 1, "team": "A", "score": 2},
            {"match_id": 1, "team": "B", "score": 1}
        ]

        # 调用方法
        transformed = service.transform_to_match_format(data_list)

        # 验证
        assert transformed["match_id"] == 1
        assert transformed["home_score"] == 2
        assert transformed["away_score"] == 1

    def test_handle_missing_data(self, service):
        """测试处理缺失数据"""
        # 准备带缺失值的数据
        data = pd.DataFrame({
            "id": [1, 2, 3],
            "name": ["Team A", None, "Team C"],
            "score": [2, None, 1]
        })

        # 调用方法
        cleaned_data = service.handle_missing_data(data)

        # 验证
        assert None not in cleaned_data["name"].values
        assert None not in cleaned_data["score"].values

    def test_calculate_derived_features(self, service):
        """测试计算衍生特征"""
        # 准备基础数据
        base_data = {
            "home_goals": 2,
            "away_goals": 1,
            "home_shots": 10,
            "away_shots": 5
        }

        # 调用方法
        features = service.calculate_features(base_data)

        # 验证
        assert features["goal_difference"] == 1
        assert features["total_goals"] == 3
        assert features["home_shot_accuracy"] == 0.2  # 2/10
        assert features["away_shot_accuracy"] == 0.2  # 1/5

    def test_batch_process_matches(self, service, mock_repository):
        """测试批量处理比赛"""
        # 准备测试数据
        matches = [
            {"id": 1, "home": "A", "away": "B"},
            {"id": 2, "home": "C", "away": "D"}
        ]

        # 设置模拟返回
        mock_repository.batch_save.return_value = True

        # 调用方法
        result = service.batch_process_matches(matches)

        # 验证
        assert result is True
        mock_repository.batch_save.assert_called_once()

    def test_data_quality_check(self, service):
        """测试数据质量检查"""
        # 准备测试数据
        data = {
            "total_records": 1000,
            "null_values": 50,
            "duplicates": 10,
            "invalid_dates": 5
        }

        # 调用方法
        quality_score = service.calculate_quality_score(data)

        # 验证
        assert 0 <= quality_score <= 1
        assert quality_score > 0.9  # 期望较高的质量分数

    def test_cache_processed_data(self, service, mock_cache):
        """测试缓存处理后的数据"""
        # 准备测试数据
        data = {"match_id": 1, "processed": True}
        cache_key = "match_1"

        # 调用方法
        service.cache_data(cache_key, data, ttl=3600)

        # 验证
        mock_cache.set.assert_called_once_with(cache_key, data, ex=3600)

    def test_get_cached_data(self, service, mock_cache):
        """测试获取缓存数据"""
        # 设置模拟返回
        cached_data = {"match_id": 1, "processed": True}
        mock_cache.get.return_value = cached_data

        # 调用方法
        result = service.get_cached_data("match_1")

        # 验证
        assert result == cached_data
        mock_cache.get.assert_called_once_with("match_1")
'''

    file_path = Path("tests/unit/services/test_data_processing_service.py")
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(content)
    print(f"✅ 创建文件: {file_path}")


def create_monitoring_service_test():
    """创建监控服务测试"""
    content = '''"""监控服务测试"""
import pytest
from unittest.mock import Mock, patch, MagicMock, AsyncMock
import time
from datetime import datetime, timedelta
from src.monitoring.system_monitor import SystemMonitor
from src.monitoring.metrics_collector import MetricsCollector

class TestSystemMonitor:
    """系统监控测试"""

    @pytest.fixture
    def mock_metrics_collector(self):
        """模拟指标收集器"""
        collector = Mock(spec=MetricsCollector)
        collector.collect_cpu_usage.return_value = 45.5
        collector.collect_memory_usage.return_value = 68.2
        collector.collect_disk_usage.return_value = 32.1
        return collector

    @pytest.fixture
    def monitor(self, mock_metrics_collector):
        """创建系统监控器"""
        return SystemMonitor(metrics_collector=mock_metrics_collector)

    def test_get_system_metrics(self, monitor, mock_metrics_collector):
        """测试获取系统指标"""
        # 调用方法
        metrics = monitor.get_system_metrics()

        # 验证
        assert "cpu_usage" in metrics
        assert "memory_usage" in metrics
        assert "disk_usage" in metrics
        assert metrics["cpu_usage"] == 45.5

    def test_health_check(self, monitor):
        """测试健康检查"""
        # 设置模拟返回
        with patch('monitor.database_check') as mock_db,
    patch('monitor.redis_check') as mock_redis:
            mock_db.return_value = {"status": "healthy", "response_time": 10}
            mock_redis.return_value = {"status": "healthy", "response_time": 5}

            # 调用方法
            health = monitor.check_health()

            # 验证
            assert health["overall_status"] == "healthy"
            assert "checks" in health
            assert len(health["checks"]) == 2

    def test_performance_monitoring(self, monitor):
        """测试性能监控"""
        # 准备测试数据
        start_time = time.time()
        time.sleep(0.01)  # 模拟操作
        end_time = time.time()

        # 调用方法
        performance = monitor.measure_performance(start_time, end_time)

        # 验证
        assert "duration_ms" in performance
        assert performance["duration_ms"] > 0

    def test_alert_threshold_check(self, monitor):
        """测试告警阈值检查"""
        # 设置高CPU使用率
        monitor.metrics_collector.collect_cpu_usage.return_value = 95.0

        # 调用方法
        alerts = monitor.check_alerts()

        # 验证
        assert len(alerts) > 0
        assert any(alert["type"] == "high_cpu" for alert in alerts)

    def test_log_anomaly_detection(self, monitor):
        """测试日志异常检测"""
        # 准备异常日志
        logs = [
            {"level": "ERROR", "message": "Database connection failed"},
            {"level": "ERROR", "message": "Database connection failed"},
            {"level": "ERROR", "message": "Database connection failed"}
        ]

        # 调用方法
        anomalies = monitor.detect_log_anomalies(logs)

        # 验证
        assert len(anomalies) > 0
        assert anomalies[0]["type"] == "repeated_errors"

    def test_api_endpoint_monitoring(self, monitor):
        """测试API端点监控"""
        # 准备API指标
        api_metrics = {
            "/api/predictions": {
                "requests": 1000,
                "errors": 10,
                "avg_response_time": 120
            },
            "/api/matches": {
                "requests": 500,
                "errors": 5,
                "avg_response_time": 80
            }
        }

        # 调用方法
        health = monitor.check_api_health(api_metrics)

        # 验证
        assert "/api/predictions" in health
        assert health["/api/predictions"]["status"] in ["healthy", "degraded", "unhealthy"]

    def test_resource_usage_trend(self, monitor):
        """测试资源使用趋势"""
        # 准备历史数据
        historical_data = [
            {"timestamp": datetime.now() - timedelta(hours=1), "cpu": 30},
            {"timestamp": datetime.now() - timedelta(minutes=30), "cpu": 45},
            {"timestamp": datetime.now(), "cpu": 60}
        ]

        # 调用方法
        trend = monitor.analyze_resource_trend(historical_data)

        # 验证
        assert "direction" in trend  # up/down/stable
        assert "rate" in trend
        assert trend["direction"] == "up"

    def test_generate_monitoring_report(self, monitor):
        """测试生成监控报告"""
        # 设置模拟数据
        with patch.object(monitor,
    'get_system_metrics') as mock_metrics,
    patch.object(monitor,
    'check_health') as mock_health:
            mock_metrics.return_value = {"cpu": 50, "memory": 60}
            mock_health.return_value = {"status": "healthy"}

            # 调用方法
            report = monitor.generate_report()

            # 验证
            assert "system_metrics" in report
            assert "health_status" in report
            assert "timestamp" in report
            assert report["health_status"]["status"] == "healthy"


class TestMetricsCollector:
    """指标收集器测试"""

    @pytest.fixture
    def collector(self):
        """创建指标收集器"""
        return MetricsCollector()

    def test_collect_cpu_usage(self, collector):
        """测试收集CPU使用率"""
        with patch('psutil.cpu_percent') as mock_cpu:
            mock_cpu.return_value = 45.5

            # 调用方法
            cpu_usage = collector.collect_cpu_usage()

            # 验证
            assert isinstance(cpu_usage, (int, float))
            assert 0 <= cpu_usage <= 100

    def test_collect_memory_usage(self, collector):
        """测试收集内存使用率"""
        with patch('psutil.virtual_memory') as mock_memory:
            mock_memory_obj = Mock()
            mock_memory_obj.percent = 68.2
            mock_memory.return_value = mock_memory_obj

            # 调用方法
            memory_usage = collector.collect_memory_usage()

            # 验证
            assert isinstance(memory_usage, (int, float))
            assert 0 <= memory_usage <= 100

    def test_collect_disk_usage(self, collector):
        """测试收集磁盘使用率"""
        with patch('psutil.disk_usage') as mock_disk:
            mock_disk_obj = Mock()
            mock_disk_obj.percent = 32.1
            mock_disk.return_value = mock_disk_obj

            # 调用方法
            disk_usage = collector.collect_disk_usage()

            # 验证
            assert isinstance(disk_usage, (int, float))
            assert 0 <= disk_usage <= 100

    def test_collect_network_stats(self, collector):
        """测试收集网络统计"""
        with patch('psutil.net_io_counters') as mock_net:
            mock_net_obj = Mock()
            mock_net_obj.bytes_sent = 1000000
            mock_net_obj.bytes_recv = 2000000
            mock_net.return_value = mock_net_obj

            # 调用方法
            net_stats = collector.collect_network_stats()

            # 验证
            assert "bytes_sent" in net_stats
            assert "bytes_recv" in net_stats
            assert net_stats["bytes_sent"] == 1000000

    def test_collect_process_count(self, collector):
        """测试收集进程数量"""
        with patch('psutil.pids') as mock_pids:
            mock_pids.return_value = [1, 2, 3, 4, 5]

            # 调用方法
            process_count = collector.collect_process_count()

            # 验证
            assert process_count == 5

    def test_collect_active_connections(self, collector):
        """测试收集活动连接数"""
        with patch('psutil.net_connections') as mock_connections:
            mock_connections.return_value = [Mock() for _ in range(10)]

            # 调用方法
            connections = collector.collect_active_connections()

            # 验证
            assert connections == 10

    def test_collect_system_load(self, collector):
        """测试收集系统负载"""
        with patch('os.getloadavg') as mock_loadavg:
            mock_loadavg.return_value = (1.0, 1.5, 2.0)

            # 调用方法
            load = collector.collect_system_load()

            # 验证
            assert "1min" in load
            assert "5min" in load
            assert "15min" in load
            assert load["1min"] == 1.0

    def test_collect_all_metrics(self, collector):
        """测试收集所有指标"""
        with patch.object(collector,
    'collect_cpu_usage',
    return_value=50),
    patch.object(collector,
    'collect_memory_usage',
    return_value=60),
    patch.object(collector,
    'collect_disk_usage',
    return_value=30):

            # 调用方法
            metrics = collector.collect_all()

            # 验证
            assert "cpu" in metrics
            assert "memory" in metrics
            assert "disk" in metrics
            assert "timestamp" in metrics
'''

    file_path = Path("tests/unit/services/test_monitoring_service.py")
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(content)
    print(f"✅ 创建文件: {file_path}")


def main():
    """主函数"""
    print("🚀 开始创建服务层测试文件...")

    # 创建服务测试目录
    service_test_dir = Path("tests/unit/services")
    service_test_dir.mkdir(parents=True, exist_ok=True)

    # 创建各个测试文件
    create_prediction_service_test()
    create_data_processing_service_test()
    create_monitoring_service_test()

    # 使用自动化生成器
    executor = ServiceTestExecutor()
    results = executor.generate_all_service_tests()

    print(f"\n✅ 已创建服务测试文件!")
    print(f"\n📝 自动生成结果: {sum(1 for success in results.values() if success)}/{len(results)}")

    print("\n🏃 运行测试:")
    print("   make test.unit")


if __name__ == "__main__":
    main()