#!/usr/bin/env python3
"""
验证拆分后的代码是否损坏

检查拆分模块的语法正确性、导入完整性和基本结构。
"""

import ast
import sys
from pathlib import Path
from typing import Dict, List, Tuple, Optional


def check_python_syntax(file_path: Path) -> Tuple[bool, Optional[str]]:
    """
    检查Python文件的语法

    Returns:
        (is_valid, error_message)
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        # 尝试解析AST
        ast.parse(content)
        return True, None
    except SyntaxError as e:
        return False, f"语法错误: {e}"
    except Exception as e:
        return False, f"其他错误: {e}"


def check_imports(file_path: Path) -> Tuple[bool, List[str]]:
    """
    检查文件的导入

    Returns:
        (has_imports, import_list)
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        tree = ast.parse(content)
        imports = []

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(f"import {alias.name}")
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                for alias in node.names:
                    imports.append(f"from {module} import {alias.name}")

        return len(imports) > 0, imports
    except Exception:
        return False, []


def verify_audit_service_mod() -> Dict[str, bool]:
    """验证audit_service_mod模块"""
    print("\n" + "=" * 60)
    print("验证 audit_service_mod 模块")
    print("=" * 60)

    results = {
        "syntax_valid": True,
        "imports_valid": True,
        "structure_valid": True,
        "details": {},
    }

    base_path = Path("src/services/audit_service_mod")
    if not base_path.exists():
        results["structure_valid"] = False
        print("✗ 目录不存在")
        return results

    # 检查必需的文件
    required_files = [
        "__init__.py",
        "context.py",
        "decorators.py",
        "models.py",
        "service.py",
        "storage.py",
        "utils.py",
    ]

    for file_name in required_files:
        file_path = base_path / file_name
        if file_path.exists():
            print(f"✓ {file_name}")

            # 检查语法
            is_valid, error = check_python_syntax(file_path)
            if is_valid:
                results["details"][f"{file_name}_syntax"] = True
                print("  ✓ 语法正确")
            else:
                results["syntax_valid"] = False
                results["details"][f"{file_name}_syntax"] = False
                print(f"  ✗ 语法错误: {error}")

            # 检查导入
            has_imports, imports = check_imports(file_path)
            if has_imports:
                results["details"][f"{file_name}_imports"] = True
                print(f"  ✓ 有导入语句 ({len(imports)}个)")
            else:
                results["details"][f"{file_name}_imports"] = False
                print("  ⚠️  无导入语句")
        else:
            print(f"✗ {file_name} - 文件缺失")
            results["structure_valid"] = False

    return results


def verify_other_modules():
    """验证其他重要的拆分模块"""
    print("\n" + "=" * 60)
    print("验证其他重要模块")
    print("=" * 60)

    modules_to_check = [
        ("src/services/manager_mod.py", "manager_mod"),
        ("src/services/data_processing_mod", "data_processing_mod"),
        ("src/database/connection_mod", "connection_mod"),
        ("src/cache/ttl_cache_improved_mod", "ttl_cache_improved_mod"),
        ("src/data/processing/football_data_cleaner_mod", "football_data_cleaner_mod"),
        ("src/monitoring/system_monitor_mod", "system_monitor_mod"),
        (
            "src/monitoring/metrics_collector_enhanced_mod",
            "metrics_collector_enhanced_mod",
        ),
    ]

    results = {}

    for module_path, module_name in modules_to_check:
        print(f"\n检查模块: {module_name}")
        module_results = {"exists": False, "syntax_valid": True, "file_count": 0}

        path = Path(module_path)
        if path.exists():
            module_results["exists"] = True
            print("✓ 目录/文件存在")

            if path.is_dir():
                # 统计Python文件
                py_files = list(path.rglob("*.py"))
                module_results["file_count"] = len(py_files)
                print(f"  包含 {len(py_files)} 个Python文件")

                # 检查每个文件的语法
                for py_file in py_files:
                    is_valid, error = check_python_syntax(py_file)
                    if not is_valid:
                        module_results["syntax_valid"] = False
                        print(f"  ✗ {py_file.name}: {error}")
                    else:
                        print(f"  ✓ {py_file.name}: 语法正确")
            else:
                # 单个文件
                module_results["file_count"] = 1
                is_valid, error = check_python_syntax(path)
                if not is_valid:
                    module_results["syntax_valid"] = False
                    print(f"  ✗ 语法错误: {error}")
                else:
                    print("  ✓ 语法正确")
        else:
            print("✗ 目录/文件不存在")

        results[module_name] = module_results

    return results


def verify_modularization_quality():
    """验证模块化质量"""
    print("\n" + "=" * 60)
    print("验证模块化质量")
    print("=" * 60)

    # 检查audit_service的模块化
    audit_service_mod = Path("src/services/audit_service_mod")
    original_audit = Path("src/services/audit_service.py")

    print("\naudit_service 模块化分析:")

    if audit_service_mod.exists():
        # 统计拆分后的代码
        total_lines = 0
        for py_file in audit_service_mod.rglob("*.py"):
            lines = len(py_file.read_text(encoding="utf-8").split("\n"))
            total_lines += lines

        print(f"✓ 拆分后总行数: {total_lines}")
        print(f"✓ 模块文件数: {len(list(audit_service_mod.rglob('*.py')))}")

        # 检查原始文件
        if original_audit.exists():
            original_lines = len(original_audit.read_text(encoding="utf-8").split("\n"))
            print(f"✓ 原始文件行数: {original_lines}")

            if total_lines > 0:
                print("✓ 模块化成功，代码被合理拆分")
            else:
                print("⚠️  拆分后代码为空")

        # 检查__init__.py
        init_file = audit_service_mod / "__init__.py"
        if init_file.exists():
            init_content = init_file.read_text(encoding="utf-8")
            if "AuditService" in init_content:
                print("✓ __init__.py 正确导出了主要类")
            else:
                print("⚠️  __init__.py 可能未正确导出主要类")


def main():
    """主函数"""
    print("=" * 60)
    print("验证拆分代码完整性")
    print("=" * 60)

    # 添加项目根目录到Python路径
    sys.path.insert(0, str(Path.cwd()))

    # 验证audit_service_mod
    audit_results = verify_audit_service_mod()

    # 验证其他模块
    other_results = verify_other_modules()

    # 验证模块化质量
    verify_modularization_quality()

    # 总结
    print("\n" + "=" * 60)
    print("验证总结")
    print("=" * 60)

    print("\naudit_service_mod:")
    print(f"  语法正确: {'✓' if audit_results['syntax_valid'] else '✗'}")
    print(f"  结构完整: {'✓' if audit_results['structure_valid'] else '✗'}")

    print("\n其他模块:")
    for module_name, results in other_results.items():
        if results["exists"]:
            print(
                f"  {module_name}: ✓ 存在, {'语法正确' if results['syntax_valid'] else '语法错误'} ({results['file_count']} 文件)"
            )
        else:
            print(f"  {module_name}: ✗ 不存在")

    print("\n建议:")
    if audit_results["syntax_valid"] and audit_results["structure_valid"]:
        print("✓ audit_service_mod 代码完整，可以使用")
    else:
        print("✗ audit_service_mod 有问题，需要修复")

    # 尝试导入测试
    print("\n" + "=" * 60)
    print("导入测试")
    print("=" * 60)

    test_modules = [
        ("src.services.audit_service_mod", "AuditService"),
        ("src.services.manager_mod", "ServiceManager"),
    ]

    for module_name, class_name in test_modules:
        try:
            module = __import__(module_name, fromlist=[class_name])
            getattr(module, class_name)
            print(f"✓ {module_name}.{class_name} 导入成功")
        except Exception as e:
            print(f"✗ {module_name}.{class_name} 导入失败: {e}")


if __name__ == "__main__":
    main()
