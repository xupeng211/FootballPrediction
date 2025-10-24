"""
测试调度任务模块结构
Test scheduler tasks module structure
"""

import os
import pytest
import ast


@pytest.mark.unit

def test_module_files_exist():
    """测试所有模块文件都存在"""
    base_path = "src/scheduler/tasks"

    required_files = [
        "__init__.py",
        "base.py",
        "collection.py",
        "features.py",
        "maintenance.py",
        "quality.py",
        "predictions.py",
        "processing.py",
    ]

    for file_name in required_files:
        file_path = os.path.join(base_path, file_name)
        assert os.path.exists(file_path), f"文件 {file_path} 不存在"


def test_module_has_correct_imports():
    """测试模块有正确的导入"""
    base_path = "src/scheduler/tasks"

    # 检查 __init__.py 的导入
    init_file = os.path.join(base_path, "__init__.py")
    with open(init_file, "r", encoding="utf-8") as f:
        content = f.read()

    # 验证关键导入存在
    expected_imports = [
        "from .base import BaseDataTask",
        "from .collection import",
        "from .features import calculate_features_batch",
        "from .maintenance import cleanup_data",
        "from .quality import run_quality_checks",
        "from .predictions import generate_predictions",
        "from .processing import process_bronze_to_silver",
    ]

    for import_stmt in expected_imports:
        assert import_stmt in content, f"导入语句 '{import_stmt}' 不在 __init__.py 中"


def test_base_module_structure():
    """测试基础模块结构"""
    base_path = "src/scheduler/tasks/base.py"
    with open(base_path, "r", encoding="utf-8") as f:
        tree = ast.parse(f.read())

    # 检查是否有 BaseDataTask 类
    classes = [node.name for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]
    assert "BaseDataTask" in classes, "BaseDataTask 类不在 base.py 中"

    # 检查方法
    methods = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == "BaseDataTask":
            methods = [n.name for n in node.body if isinstance(n, ast.FunctionDef)]
            break

    expected_methods = ["on_failure", "on_success", "get_retry_config"]
    for method in expected_methods:
        assert method in methods, f"方法 {method} 不在 BaseDataTask 类中"


def test_collection_module_structure():
    """测试数据采集模块结构"""
    base_path = "src/scheduler/tasks/collection.py"
    with open(base_path, "r", encoding="utf-8") as f:
        content = f.read()

    # 验证任务函数存在
    expected_functions = [
        "def collect_fixtures(",
        "def collect_odds(",
        "def collect_live_scores_conditional(",
    ]

    for func in expected_functions:
        assert func in content, f"函数 '{func}' 不在 collection.py 中"


def test_features_module_structure():
    """测试特征计算模块结构"""
    base_path = "src/scheduler/tasks/features.py"
    with open(base_path, "r", encoding="utf-8") as f:
        content = f.read()

    # 验证任务函数存在
    assert "def calculate_features_batch(" in content, (
        "calculate_features_batch 函数不在 features.py 中"
    )


def test_maintenance_module_structure():
    """测试维护模块结构"""
    base_path = "src/scheduler/tasks/maintenance.py"
    with open(base_path, "r", encoding="utf-8") as f:
        content = f.read()

    # 验证任务函数存在
    expected_functions = [
        "def cleanup_data(",
        "def backup_database(",
    ]

    for func in expected_functions:
        assert func in content, f"函数 '{func}' 不在 maintenance.py 中"


def test_quality_module_structure():
    """测试质量检查模块结构"""
    base_path = "src/scheduler/tasks/quality.py"
    with open(base_path, "r", encoding="utf-8") as f:
        content = f.read()

    # 验证任务函数存在
    assert "def run_quality_checks(" in content, (
        "run_quality_checks 函数不在 quality.py 中"
    )


def test_predictions_module_structure():
    """测试预测模块结构"""
    base_path = "src/scheduler/tasks/predictions.py"
    with open(base_path, "r", encoding="utf-8") as f:
        content = f.read()

    # 验证任务函数存在
    assert "def generate_predictions(" in content, (
        "generate_predictions 函数不在 predictions.py 中"
    )


def test_processing_module_structure():
    """测试数据处理模块结构"""
    base_path = "src/scheduler/tasks/processing.py"
    with open(base_path, "r", encoding="utf-8") as f:
        content = f.read()

    # 验证任务函数存在
    assert "def process_bronze_to_silver(" in content, (
        "process_bronze_to_silver 函数不在 processing.py 中"
    )


def test_original_file_updated():
    """测试原始文件已更新为向后兼容"""
    original_file = "src/scheduler/tasks.py"
    with open(original_file, "r", encoding="utf-8") as f:
        content = f.read()

    # 验证文件包含向后兼容性说明
    assert "已重构为模块化结构" in content, "原始文件没有重构说明"

    # 验证从新模块导入
    assert "from .tasks import (" in content, "原始文件没有从新模块导入"


def test_module_sizes():
    """测试模块大小合理"""
    base_path = "src/scheduler/tasks"

    file_sizes = {}
    for file_name in os.listdir(base_path):
        if file_name.endswith(".py") and file_name != "__pycache__":
            file_path = os.path.join(base_path, file_name)
            with open(file_path, "r", encoding="utf-8") as f:
                lines = len(f.readlines())
                file_sizes[file_name] = lines

    # 验证没有文件过大（比如超过500行）
    for file_name, line_count in file_sizes.items():
        assert line_count < 500, f"文件 {file_name} 过大，有 {line_count} 行"

    # 打印文件大小信息
    print("\n模块文件行数统计:")
    for file_name, line_count in sorted(file_sizes.items()):
        print(f"  {file_name}: {line_count} 行")
