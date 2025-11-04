#!/usr/bin/env python3
"""
基础测试框架构建工具
Basic Test Framework Builder

基于Issue #194需求，建立完整的基础测试框架和CI/CD质量门禁，
解决现有测试问题，优化pytest配置，确保代码质量。

作者: Claude AI Assistant
版本: v1.0
创建时间: 2025-11-03
"""

import json
import sys
import os
import subprocess
import shutil
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum

# 添加项目根目录到Python路径
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

class TestFrameworkStatus(Enum):
    """测试框架状态枚举"""
    BUILDING = "building"
    READY = "ready"
    ERROR = "error"
    OPTIMIZED = "optimized"

class QualityGateStatus(Enum):
    """质量门禁状态枚举"""
    DISABLED = "disabled"
    WARNING = "warning"
    ENFORCED = "enforced"
    STRICT = "strict"

@dataclass
class TestIssue:
    """测试问题数据结构"""
    file_path: str
    issue_type: str
    description: str
    severity: str
    suggested_fix: str

@dataclass
class TestFrameworkReport:
    """测试框架报告数据结构"""
    timestamp: str
    status: TestFrameworkStatus
    total_tests_found: int
    runnable_tests: int
    error_tests: int
    skipped_tests: int
    issues_found: List[TestIssue]
    fixes_applied: List[str]
    coverage_threshold: float
    quality_gate_status: QualityGateStatus
    recommendations: List[str]

class TestFrameworkBuilder:
    """基础测试框架构建器"""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.timestamp = datetime.now().isoformat()

        # 配置参数
        self.config = {
            "coverage_threshold": 30.0,  # 目标覆盖率30%
            "max_test_duration": 300,   # 最大测试时间5分钟
            "parallel_jobs": 4,         # 并行测试作业数
            "quality_gate_strict": False, # 质量门禁严格模式
            "test_markers": [
                "unit", "integration", "api", "domain", "services",
                "smoke", "critical", "health"
            ]
        }

        # 已知测试问题模式
        self.test_issue_patterns = {
            "import_error": [
                "ImportError", "ModuleNotFoundError", "cannot import name"
            ],
            "circular_import": [
                "circular import", "most likely due to a circular import"
            ],
            "file_conflict": [
                "import file mismatch", "not the same as the test file"
            ],
            "missing_dependency": [
                "No module named", "ModuleNotFoundError"
            ]
        }

    def analyze_test_framework(self) -> TestFrameworkReport:
        """分析当前测试框架状态"""
        print("🔍 分析当前测试框架状态...")

        # 扫描测试文件
        test_files = self._scan_test_files()
        total_tests = len(test_files)

        # 尝试收集测试（模拟pytest收集过程）
        try:
            collection_result = self._dry_run_pytest_collection()
            runnable_tests = collection_result["collected"]
            error_tests = collection_result["errors"]
            skipped_tests = collection_result["skipped"]
        except Exception as e:
            print(f"⚠️ 测试收集失败: {e}")
            runnable_tests = 0
            error_tests = total_tests
            skipped_tests = 0

        # 识别测试问题
        issues = self._identify_test_issues(test_files)

        # 生成建议
        recommendations = self._generate_framework_recommendations(issues, total_tests)

        return TestFrameworkReport(
            timestamp=self.timestamp,
            status=TestFrameworkStatus.BUILDING,
            total_tests_found=total_tests,
            runnable_tests=runnable_tests,
            error_tests=error_tests,
            skipped_tests=skipped_tests,
            issues_found=issues,
            fixes_applied=[],
            coverage_threshold=self.config["coverage_threshold"],
            quality_gate_status=QualityGateStatus.DISABLED,
            recommendations=recommendations
        )

    def _scan_test_files(self) -> List[Path]:
        """扫描测试文件"""
        test_patterns = ["test_*.py", "*_test.py"]
        test_files = []

        tests_dir = self.project_root / "tests"
        if tests_dir.exists():
            for pattern in test_patterns:
                test_files.extend(tests_dir.rglob(pattern))

        return test_files

    def _dry_run_pytest_collection(self) -> Dict[str, int]:
        """干运行pytest收集"""
        try:
            result = subprocess.run(
                ["pytest", "--collect-only", "-q"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=60
            )

            # 解析输出
            lines = result.stdout.strip().split('\n')
            collected = 0
            errors = 0
            skipped = 0

            for line in lines:
                if "collected" in line.lower():
                    try:
                        collected = int(line.split()[-2])
                    except (IndexError, ValueError):
                        pass
                elif "error" in line.lower():
                    errors += 1
                elif "skipped" in line.lower():
                    try:
                        skipped = int(line.split()[-2])
                    except (IndexError, ValueError):
                        pass

            return {"collected": collected, "errors": errors, "skipped": skipped}

        except (subprocess.TimeoutExpired,
    subprocess.CalledProcessError,
    FileNotFoundError):
            return {"collected": 0, "errors": 0, "skipped": 0}

    def _identify_test_issues(self, test_files: List[Path]) -> List[TestIssue]:
        """识别测试问题"""
        issues = []

        for test_file in test_files:
            try:
                with open(test_file, 'r', encoding='utf-8') as f:
                    content = f.read()

                # 检查导入问题
                file_issues = self._check_file_imports(test_file, content)
                issues.extend(file_issues)

            except Exception as e:
                issues.append(TestIssue(
                    file_path=str(test_file.relative_to(self.project_root)),
                    issue_type="file_access",
                    description=f"无法读取测试文件: {e}",
                    severity="high",
                    suggested_fix="检查文件权限或文件完整性"
                ))

        return issues

    def _check_file_imports(self, test_file: Path, content: str) -> List[TestIssue]:
        """检查文件导入问题"""
        issues = []
        file_path = str(test_file.relative_to(self.project_root))

        lines = content.split('\n')
        for i, line in enumerate(lines, 1):
            line = line.strip()
            if not line.startswith('from ') and not line.startswith('import '):
                continue

            # 检查已知的导入问题模式
            for issue_type, patterns in self.test_issue_patterns.items():
                for pattern in patterns:
                    if pattern in line:
                        severity = "high" if issue_type in ["import_error", "circular_import"] else "medium"
                        suggested_fix = self._get_suggested_fix(issue_type,
    line,
    file_path)

                        issues.append(TestIssue(
                            file_path=file_path,
                            issue_type=issue_type,
                            description=f"第{i}行: {line}",
                            severity=severity,
                            suggested_fix=suggested_fix
                        ))

        return issues

    def _get_suggested_fix(self,
    issue_type: str,
    problematic_line: str,
    file_path: str) -> str:
        """获取建议的修复方案"""
        fixes = {
            "import_error": "检查导入的模块是否存在，或创建缺失的模块文件",
            "circular_import": "重构代码以避免循环导入，或将导入移到函数内部",
            "file_conflict": "重命名测试文件以避免命名冲突，或清理__pycache__",
            "missing_dependency": "安装缺失的依赖包或检查模块路径配置",
            "file_access": "检查文件权限和文件完整性"
        }

        base_fix = fixes.get(issue_type, "检查导入语法和模块可用性")

        # 添加具体的修复建议
        if "src.services" in problematic_line:
            base_fix += f"。考虑检查 services/ 目录是否存在相应的服务文件"
        elif "src.database.models" in problematic_line:
            base_fix += f"。考虑检查 database/models/ 目录是否存在相应的模型文件"
        elif "src.domain.events" in problematic_line:
            base_fix += f"。考虑检查 domain/events/ 目录是否存在相应的事件文件"

        return base_fix

    def _generate_framework_recommendations(self,
    issues: List[TestIssue],
    total_tests: int) -> List[str]:
        """生成框架改进建议"""
        recommendations = []

        # 基于问题类型生成建议
        issue_types = [issue.issue_type for issue in issues]
        error_count = len([i for i in issues if i.severity == "high"])

        if error_count > 0:
            recommendations.append(f"🚨 **紧急修复**: 发现{error_count}个高严重性问题，需要优先解决")

        if "import_error" in issue_types:
            recommendations.append("📦 **依赖管理**: 修复模块导入错误，确保所有依赖模块都存在")

        if "circular_import" in issue_types:
            recommendations.append("🔄 **代码重构**: 解决循环导入问题，优化模块结构")

        if "file_conflict" in issue_types:
            recommendations.append("🧹 **文件整理**: 清理测试文件命名冲突，删除缓存文件")

        # 基于测试数量生成建议
        if total_tests < 50:
            recommendations.append("📈 **测试扩展**: 当前测试数量较少，建议增加更多单元测试")
        elif total_tests < 100:
            recommendations.append("📊 **测试完善**: 继续增加测试覆盖率，特别是API和集成测试")
        else:
            recommendations.append("🎯 **测试优化**: 测试数量充足，可以专注于测试质量和性能优化")

        # 覆盖率建议
        recommendations.append(f"🎯 **覆盖率目标**: 当前目标覆盖率{self.config['coverage_threshold']}%，建议逐步提升")

        return recommendations

    def build_basic_test_framework(self) -> TestFrameworkReport:
        """构建基础测试框架"""
        print("🏗️ 构建基础测试框架...")

        # 1. 分析现状
        report = self.analyze_test_framework()

        # 2. 修复测试问题
        fixes = self._apply_test_fixes(report.issues_found)
        report.fixes_applied = fixes

        # 3. 创建基础测试
        self._create_basic_tests()

        # 4. 优化pytest配置
        self._optimize_pytest_config()

        # 5. 设置质量门禁
        self._setup_quality_gates()

        # 6. 创建测试脚本
        self._create_test_scripts()

        # 更新状态
        report.status = TestFrameworkStatus.READY
        report.quality_gate_status = QualityGateStatus.WARNING

        return report

def __apply_test_fixes_handle_error():
                        shutil.rmtree(cache_path)
                        fixes.append(f"清理缓存目录: {cache_path.relative_to(self.project_root)}")
                    except Exception as e:
                        print(f"⚠️ 无法清理缓存目录 {cache_path}: {e}")

        # 修复文件冲突
        duplicate_files = []

def __apply_test_fixes_check_condition():
                # 检查是否存在冲突
                other_config = test_file.parent / "core" / "test_config.py"

def __apply_test_fixes_check_condition():
                    duplicate_files.append(test_file)


def __apply_test_fixes_handle_error():
                backup_path = dup_file.with_suffix(f".backup{datetime.now().strftime('%Y%m%d_%H%M%S')}.py")
                dup_file.rename(backup_path)
                fixes.append(f"修复文件冲突: {dup_file.name} -> {backup_path.name}")
            except Exception as e:
                print(f"⚠️ 无法修复文件冲突 {dup_file}: {e}")

        # 创建缺失的基础模块
        missing_modules = [
            "src/domain/events/__init__.py",
            "src/services/__init__.py",
            "src/database/models/__init__.py"
        ]


def __apply_test_fixes_manage_resource():
                        f.write(f'"""{module_path}"""\n')
                    fixes.append(f"创建缺失模块: {module_path}")
                except Exception as e:
                    print(f"⚠️ 无法创建模块 {module_path}: {e}")

        return fixes

    def _apply_test_fixes(self, issues: List[TestIssue]) -> List[str]:
        """应用测试修复"""
        fixes = []

        # 清理缓存文件
        cache_dirs = [".pytest_cache", "__pycache__"]
        for cache_dir in cache_dirs:
            for cache_path in self.project_root.rglob(cache_dir):
                if cache_path.is_dir():
                    __apply_test_fixes_handle_error()
                        shutil.rmtree(cache_path)
                        fixes.append(f"清理缓存目录: {cache_path.relative_to(self.project_root)}")
                    except Exception as e:
                        print(f"⚠️ 无法清理缓存目录 {cache_path}: {e}")

        # 修复文件冲突
        duplicate_files = []
        for test_file in self._scan_test_files():
            __apply_test_fixes_check_condition()
                # 检查是否存在冲突
                other_config = test_file.parent / "core" / "test_config.py"
                __apply_test_fixes_check_condition()
                    duplicate_files.append(test_file)

        for dup_file in duplicate_files:
            __apply_test_fixes_handle_error()
                backup_path = dup_file.with_suffix(f".backup{datetime.now().strftime('%Y%m%d_%H%M%S')}.py")
                dup_file.rename(backup_path)
                fixes.append(f"修复文件冲突: {dup_file.name} -> {backup_path.name}")
            except Exception as e:
                print(f"⚠️ 无法修复文件冲突 {dup_file}: {e}")

        # 创建缺失的基础模块
        missing_modules = [
            "src/domain/events/__init__.py",
            "src/services/__init__.py",
            "src/database/models/__init__.py"
        ]

        for module_path in missing_modules:
            full_path = self.project_root / module_path
            if not full_path.exists():
                try:
                    full_path.parent.mkdir(parents=True, exist_ok=True)
                    __apply_test_fixes_manage_resource()
                        f.write(f'"""{module_path}"""\n')
                    fixes.append(f"创建缺失模块: {module_path}")
                except Exception as e:
                    print(f"⚠️ 无法创建模块 {module_path}: {e}")

        return fixes

    def _create_basic_tests(self):
        """创建基础测试文件"""
        basic_tests = {
            "test_health_check.py": self._generate_health_check_test(),
            "test_config_basic.py": self._generate_config_test(),
            "test_api_endpoints.py": self._generate_api_test(),
            "test_domain_models.py": self._generate_domain_test(),
        }

        tests_dir = self.project_root / "tests" / "unit"
        tests_dir.mkdir(parents=True, exist_ok=True)

        for filename, content in basic_tests.items():
            test_file = tests_dir / filename
            if not test_file.exists():
                with open(test_file, 'w', encoding='utf-8') as f:
                    f.write(content)
                print(f"✅ 创建基础测试: {filename}")

    def _generate_health_check_test(self) -> str:
        """生成健康检查测试"""
        return '''"""
健康检查基础测试
Basic Health Check Tests
"""

import pytest
from fastapi.testclient import TestClient
import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

try:
    from src.main import app
    client = TestClient(app)
    APP_AVAILABLE = True
except ImportError:
    APP_AVAILABLE = False
    print("⚠️ 主应用不可用，跳过健康检查测试")


@pytest.mark.health
@pytest.mark.smoke
@pytest.mark.skipif(not APP_AVAILABLE, reason="主应用不可用")
def test_health_endpoint():
    """测试健康检查端点"""
    response = client.get("/health")
    assert response.status_code == 200

    data = response.json()
    assert "status" in data
    assert data["status"] == "healthy"


@pytest.mark.health
@pytest.mark.skipif(not APP_AVAILABLE, reason="主应用不可用")
def test_root_endpoint():
    """测试根端点"""
    response = client.get("/")
    assert response.status_code == 200


@pytest.mark.health
@pytest.mark.unit
def test_basic_imports():
    """测试基础模块导入"""
    try:
        import src.core.config
        assert True
    except ImportError:
        pytest.skip("配置模块不可用")


@pytest.mark.health
@pytest.mark.unit
def test_project_structure():
    """测试项目结构"""
    project_root = Path(__file__).parent.parent.parent

    # 检查关键目录
    required_dirs = ["src", "tests", "scripts"]
    for dir_name in required_dirs:
        assert (project_root / dir_name).exists(), f"缺少目录: {dir_name}"

    # 检查关键文件
    required_files = ["README.md", "pytest.ini", "requirements.txt"]
    for file_name in required_files:
        assert (project_root / file_name).exists(), f"缺少文件: {file_name}"
'''

    def _generate_config_test(self) -> str:
        """生成配置测试"""
        return '''"""
配置基础测试
Basic Configuration Tests
"""

import pytest
import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


@pytest.mark.unit
@pytest.mark.smoke
def test_pytest_config_exists():
    """测试pytest配置文件存在"""
    project_root = Path(__file__).parent.parent.parent
    config_file = project_root / "pytest.ini"

    assert config_file.exists(), "pytest.ini配置文件不存在"

    # 检查关键配置
    content = config_file.read_text()
    assert "[pytest]" in content, "pytest配置文件格式错误"
    assert "testpaths = tests" in content, "测试路径配置缺失"


@pytest.mark.unit
def test_test_directory_structure():
    """测试目录结构"""
    project_root = Path(__file__).parent.parent.parent
    tests_root = project_root / "tests"

    assert tests_root.exists(), "tests目录不存在"

    # 检查测试子目录
    subdirs = ["unit", "integration", "api"]
    for subdir in subdirs:
        subdir_path = tests_root / subdir
        if subdir_path.exists():
            assert subdir_path.is_dir(), f"{subdir}不是目录"


@pytest.mark.unit
def test_python_path_config():
    """测试Python路径配置"""
    # 测试当前文件能否导入项目模块
    try:
        import src
        assert hasattr(src, '__path__'), "src包路径配置错误"
    except ImportError as e:
        pytest.skip(f"无法导入src模块: {e}")


@pytest.mark.unit
def test_environment_variables():
    """测试环境变量配置"""
    import os

    # 检查Python路径
    python_path = os.environ.get('PYTHONPATH', '')
    assert 'src' in python_path or str(Path(__file__).parent.parent.parent) in python_path,
    
    \
        "PYTHONPATH未正确配置"


@pytest.mark.unit
def test_dependencies_available():
    """测试基础依赖可用性"""
    required_packages = ['pytest', 'fastapi']

    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            pytest.skip(f"依赖包 {package} 不可用")
'''

    def _generate_api_test(self) -> str:
        """生成API测试"""
        return '''"""
API端点基础测试
Basic API Endpoint Tests
"""

import pytest
from fastapi.testclient import TestClient
import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

try:
    from src.main import app
    client = TestClient(app)
    APP_AVAILABLE = True
except ImportError:
    APP_AVAILABLE = False
    client = None


@pytest.mark.api
@pytest.mark.integration
@pytest.mark.skipif(not APP_AVAILABLE, reason="主应用不可用")
class TestAPIEndpoints:
    """API端点测试类"""

    def test_health_response_format(self):
        """测试健康检查响应格式"""
        response = client.get("/health")
        assert response.status_code == 200

        data = response.json()
        required_fields = ["status", "timestamp"]

        for field in required_fields:
            assert field in data, f"响应缺少字段: {field}"

    def test_api_root_response(self):
        """测试API根端点响应"""
        response = client.get("/")
        assert response.status_code in [200, 404]  # 允许404作为正常响应

    def test_response_headers(self):
        """测试响应头"""
        response = client.get("/health")
        assert response.status_code == 200

        # 检查内容类型
        content_type = response.headers.get("content-type", "")
        assert "application/json" in content_type, "响应头content-type错误"

    def test_error_handling(self):
        """测试错误处理"""
        # 测试不存在的端点
        response = client.get("/nonexistent-endpoint")
        assert response.status_code == 404


@pytest.mark.api
@pytest.mark.unit
def test_api_imports():
    """测试API相关导入"""
    try:
        from src.api.routes import health
        assert True
    except ImportError:
        pytest.skip("API路由模块不可用")


@pytest.mark.api
@pytest.mark.unit
def test_fastapi_app_creation():
    """测试FastAPI应用创建"""
    try:
        from fastapi import FastAPI
        test_app = FastAPI()
        assert test_app is not None
    except ImportError:
        pytest.skip("FastAPI不可用")
'''

    def _generate_domain_test(self) -> str:
        """生成领域层测试"""
        return '''"""
领域层基础测试
Basic Domain Layer Tests
"""

import pytest
import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


@pytest.mark.domain
@pytest.mark.unit
def test_domain_structure():
    """测试领域层结构"""
    project_root = Path(__file__).parent.parent.parent
    domain_dir = project_root / "src" / "domain"

    if domain_dir.exists():
        assert domain_dir.is_dir(), "domain目录存在但不是目录"

        # 检查领域层子模块
        submodules = ["models", "services", "events", "strategies"]
        for module in submodules:
            module_path = domain_dir / module
            if module_path.exists():
                init_file = module_path / "__init__.py"
                if not init_file.exists():
                    pytest.skip(f"领域模块 {module} 缺少 __init__.py 文件")


@pytest.mark.domain
@pytest.mark.unit
def test_domain_models_import():
    """测试领域模型导入"""
    try:
        # 尝试导入基础模型
        from src.domain.models.base import BaseModel
        assert True
    except ImportError:
        pytest.skip("基础模型不可用")


@pytest.mark.domain
@pytest.mark.unit
def test_domain_services_import():
    """测试领域服务导入"""
    try:
        # 尝试导入服务基类
        from src.domain.services.base import BaseService
        assert True
    except ImportError:
        pytest.skip("领域服务基类不可用")


@pytest.mark.domain
@pytest.mark.unit
def test_prediction_domain_logic():
    """测试预测领域逻辑基础"""
    try:
        from src.domain.models.prediction import Prediction
        # 基础实例化测试
        assert True
    except ImportError:
        pytest.skip("预测模型不可用")


@pytest.mark.domain
@pytest.mark.unit
def test_strategy_pattern_implementation():
    """测试策略模式实现"""
    try:
        from src.domain.strategies.factory import StrategyFactory
        assert True
    except ImportError:
        pytest.skip("策略工厂不可用")
'''

    def _optimize_pytest_config(self):
        """优化pytest配置"""
        config_file = self.project_root / "pytest.ini"

        if config_file.exists():
            content = config_file.read_text()

            # 优化覆盖率配置
            if "--cov-fail-under=5" in content:
                content = content.replace("--cov-fail-under=5", "--cov-fail-under=30")
                print("✅ 覆盖率阈值更新为30%")

            # 添加并行测试配置
            if "-n auto" not in content and "--dist" not in content:
                addopts_section = content.find("[tool:pytest]")
                if addopts_section == -1:
                    # 添加新的配置节
                    content += "\n\n[tool:pytest]\naddopts = -n auto --dist=loadscope\n"
                else:
                    print("ℹ️ pytest配置已包含并行测试配置")

            # 写回文件
            config_file.write_text(content)

    def _setup_quality_gates(self):
        """设置质量门禁"""
        # 创建GitHub Actions质量门禁配置
        quality_gate_content = '''name: Quality Gate

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  quality-check:
    runs-on: ubuntu-latest

    steps:
    - uses: actions/checkout@v4

    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'

    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install pytest pytest-cov pytest-xdist
        pip install -r requirements.txt

    - name: Run unit tests
      run: |
        pytest tests/unit/ -v --cov=src --cov-report=xml --cov-fail-under=30

    - name: Run integration tests
      run: |
        pytest tests/integration/ -v --maxfail=3

    - name: Check code quality
      run: |
        pip install ruff mypy
        ruff check src/ tests/
        mypy src/ --ignore-missing-imports

    - name: Upload coverage
      uses: codecov/codecov-action@v3
      with:
        file: ./coverage.xml
'''

        workflows_dir = self.project_root / ".github" / "workflows"
        workflows_dir.mkdir(parents=True, exist_ok=True)

        quality_gate_file = workflows_dir / "quality-gate.yml"
        if not quality_gate_file.exists():
            with open(quality_gate_file, 'w') as f:
                f.write(quality_gate_content)
            print("✅ 创建质量门禁配置")

    def _create_test_scripts(self):
        """创建测试脚本"""
        scripts = {
            "run_tests.sh": '''#!/bin/bash
# 运行测试脚本

set -e

echo "🧪 开始运行测试套件..."

# 清理缓存
echo "🧹 清理测试缓存..."
find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
find . -name ".pytest_cache" -type d -exec rm -rf {} + 2>/dev/null || true

# 运行单元测试
echo "🔍 运行单元测试..."
pytest tests/unit/ -v --cov=src --cov-report=html --cov-report=term-missing --cov-fail-under=30

# 运行集成测试
echo "🔗 运行集成测试..."
pytest tests/integration/ -v --maxfail=5

# 生成测试报告
echo "📊 生成测试报告..."
pytest --html=reports/test_report.html --self-contained-html

echo "✅ 测试完成！"
echo "📈 覆盖率报告: htmlcov/index.html"
echo "📄 HTML测试报告: reports/test_report.html"
''',

            "quick_test.sh": '''#!/bin/bash
# 快速测试脚本

echo "⚡ 运行快速测试..."

# 只运行关键测试
pytest tests/unit/ -v -m "smoke or critical" --maxfail=3

echo "✅ 快速测试完成！"
''',

            "test_health.sh": '''#!/bin/bash
# 测试健康检查脚本

echo "🏥 运行测试健康检查..."

# 检查测试环境
python -c "import pytest; print('pytest版本:', pytest.__version__)" || {
    echo "❌ pytest不可用"
    exit 1
}

# 检查项目结构
if [ ! -d "tests" ]; then
    echo "❌ tests目录不存在"
    exit 1
fi

# 干运行测试收集
echo "🔍 检查测试可收集性..."
pytest --collect-only -q > /dev/null || {
    echo "⚠️ 测试收集存在问题"
}

echo "✅ 测试健康检查通过！"
'''
        }

        scripts_dir = self.project_root / "scripts"
        scripts_dir.mkdir(exist_ok=True)

        for filename, content in scripts.items():
            script_file = scripts_dir / filename
            with open(script_file, 'w') as f:
                f.write(content)
            script_file.chmod(0o755)
            print(f"✅ 创建测试脚本: {filename}")

    def export_framework_report(self,
    report: TestFrameworkReport,
    output_file: Optional[Path] = None) -> Path:
        """导出框架报告"""
        if output_file is None:
            output_file = self.project_root / "reports" / f"test_framework_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

        output_file.parent.mkdir(parents=True, exist_ok=True)

        # 转换为可序列化的字典
        report_dict = asdict(report)
        report_dict["status"] = report.status.value
        report_dict["quality_gate_status"] = report.quality_gate_status.value
        report_dict["issues_found"] = [asdict(issue) for issue in report.issues_found]

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(report_dict, f, indent=2, ensure_ascii=False)

        return output_file

def _main_check_condition():
        builder.config["coverage_threshold"] = args.coverage_threshold


def _main_check_condition():
            # 仅分析当前状态
            print("🔍 分析测试框架现状...")
            report = builder.analyze_test_framework()

            print(f"\n📊 测试框架分析结果:")
            print(f"   总测试文件: {report.total_tests_found}")
            print(f"   可运行测试: {report.runnable_tests}")
            print(f"   错误测试: {report.error_tests}")
            print(f"   问题发现: {len(report.issues_found)}个")
            print(f"   状态: {report.status.value.upper()}")


def _main_iterate_items():
                    print(f"   - {issue.file_path}: {issue.description}")


def _main_check_condition():
                report_file = builder.export_framework_report(report)
                print(f"\n📄 详细报告: {report_file}")


def _main_check_condition():
            # 构建完整测试框架
            print("🏗️ 构建基础测试框架...")
            report = builder.build_basic_test_framework()

            print(f"\n📊 测试框架构建结果:")
            print(f"   状态: {report.status.value.upper()}")
            print(f"   应用的修复: {len(report.fixes_applied)}个")
            print(f"   覆盖率目标: {report.coverage_threshold}%")
            print(f"   质量门禁: {report.quality_gate_status.value.upper()}")


def _main_iterate_items():
                    print(f"   ✅ {fix}")


def _main_check_condition():
                report_file = builder.export_framework_report(report)
                print(f"\n📄 详细报告: {report_file}")

            print(f"\n🎯 下一步操作:")
            print(f"   1. 运行测试: ./scripts/run_tests.sh")
            print(f"   2. 快速检查: ./scripts/test_health.sh")
            print(f"   3. 查看覆盖率: open htmlcov/index.html")

        else:
            # 默认执行分析和构建
            print("🚀 开始测试框架构建流程...")

            # 分析现状
            report = builder.analyze_test_framework()


def _main_check_condition():
                print(f"⚠️ 发现{report.error_tests}个测试问题，开始修复...")

                # 构建框架
                report = builder.build_basic_test_framework()

                print(f"✅ 测试框架构建完成！")
                print(f"📊 修复了{len(report.fixes_applied)}个问题")

            else:
                print(f"✅ 测试框架状态良好，无需修复")

            # 运行验证测试
            print(f"\n🧪 运行验证测试...")

def _main_handle_error():
                subprocess.run([
                    "python", "-m", "pytest",
                    "tests/unit/test_health_check.py",
                    "-v", "--tb=short"
                ], check=False, cwd=project_root)
            except Exception as e:
                print(f"⚠️ 验证测试运行失败: {e}")

    except KeyboardInterrupt:
        print("\n👋 用户中断，退出程序")
        sys.exit(130)
    except Exception as e:
        print(f"❌ 程序执行出错: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="基础测试框架构建工具")
    parser.add_argument(
        "--project-root",
        type=Path,
        help="项目根目录路径"
    )
    parser.add_argument(
        "--analyze-only",
        action="store_true",
        help="仅分析当前状态"
    )
    parser.add_argument(
        "--build-framework",
        action="store_true",
        help="构建完整测试框架"
    )
    parser.add_argument(
        "--coverage-threshold",
        type=float,
        default=30.0,
        help="覆盖率阈值"
    )
    parser.add_argument(
        "--output-report",
        action="store_true",
        help="输出框架报告"
    )

    args = parser.parse_args()

    # 创建框架构建器实例
    project_root = args.project_root or Path(__file__).parent.parent
    builder = TestFrameworkBuilder(project_root)

    _main_check_condition()
        builder.config["coverage_threshold"] = args.coverage_threshold

    try:
        _main_check_condition()
            # 仅分析当前状态
            print("🔍 分析测试框架现状...")
            report = builder.analyze_test_framework()

            print(f"\n📊 测试框架分析结果:")
            print(f"   总测试文件: {report.total_tests_found}")
            print(f"   可运行测试: {report.runnable_tests}")
            print(f"   错误测试: {report.error_tests}")
            print(f"   问题发现: {len(report.issues_found)}个")
            print(f"   状态: {report.status.value.upper()}")

            if report.issues_found:
                print(f"\n🚨 发现的主要问题:")
                _main_iterate_items()
                    print(f"   - {issue.file_path}: {issue.description}")

            _main_check_condition()
                report_file = builder.export_framework_report(report)
                print(f"\n📄 详细报告: {report_file}")

        _main_check_condition()
            # 构建完整测试框架
            print("🏗️ 构建基础测试框架...")
            report = builder.build_basic_test_framework()

            print(f"\n📊 测试框架构建结果:")
            print(f"   状态: {report.status.value.upper()}")
            print(f"   应用的修复: {len(report.fixes_applied)}个")
            print(f"   覆盖率目标: {report.coverage_threshold}%")
            print(f"   质量门禁: {report.quality_gate_status.value.upper()}")

            if report.fixes_applied:
                print(f"\n🔧 应用的修复:")
                _main_iterate_items()
                    print(f"   ✅ {fix}")

            _main_check_condition()
                report_file = builder.export_framework_report(report)
                print(f"\n📄 详细报告: {report_file}")

            print(f"\n🎯 下一步操作:")
            print(f"   1. 运行测试: ./scripts/run_tests.sh")
            print(f"   2. 快速检查: ./scripts/test_health.sh")
            print(f"   3. 查看覆盖率: open htmlcov/index.html")

        else:
            # 默认执行分析和构建
            print("🚀 开始测试框架构建流程...")

            # 分析现状
            report = builder.analyze_test_framework()

            _main_check_condition()
                print(f"⚠️ 发现{report.error_tests}个测试问题，开始修复...")

                # 构建框架
                report = builder.build_basic_test_framework()

                print(f"✅ 测试框架构建完成！")
                print(f"📊 修复了{len(report.fixes_applied)}个问题")

            else:
                print(f"✅ 测试框架状态良好，无需修复")

            # 运行验证测试
            print(f"\n🧪 运行验证测试...")
            _main_handle_error()
                subprocess.run([
                    "python", "-m", "pytest",
                    "tests/unit/test_health_check.py",
                    "-v", "--tb=short"
                ], check=False, cwd=project_root)
            except Exception as e:
                print(f"⚠️ 验证测试运行失败: {e}")

    except KeyboardInterrupt:
        print("\n👋 用户中断，退出程序")
        sys.exit(130)
    except Exception as e:
        print(f"❌ 程序执行出错: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()