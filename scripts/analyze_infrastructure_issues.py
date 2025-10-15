#!/usr/bin/env python3
"""
深度分析基础设施问题
"""

import ast
import os
import re
from pathlib import Path
from collections import defaultdict, Counter
import subprocess
import json

def analyze_syntax_errors():
    """分析语法错误"""
    print("\n=== 1. 语法错误分析 ===")

    # 使用Python AST解析器检查语法错误
    syntax_errors = []
    python_files = list(Path('src').rglob('*.py'))

    for file_path in python_files[:50]:  # 检查前50个文件
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            ast.parse(content)
        except SyntaxError as e:
            syntax_errors.append({
                'file': str(file_path),
                'line': e.lineno,
                'error': str(e),
                'type': 'SyntaxError'
            })
        except Exception as e:
            syntax_errors.append({
                'file': str(file_path),
                'error': str(e),
                'type': 'OtherError'
            })

    print(f"发现 {len(syntax_errors)} 个语法错误")

    # 统计错误类型
    error_types = Counter([err['type'] for err in syntax_errors])
    print(f"错误类型分布: {dict(error_types)}")

    # 显示前10个错误
    for i, err in enumerate(syntax_errors[:10]):
        print(f"{i+1}. {err['file']}: {err['error']}")

    return syntax_errors

def analyze_import_issues():
    """分析导入问题"""
    print("\n=== 2. 导入问题分析 ===")

    import_issues = []
    missing_modules = set()

    # 检查测试收集错误
    try:
        result = subprocess.run(
            ["python", "-m", "pytest", "--collect-only", "tests/", "-q"],
            capture_output=True,
            text=True,
            timeout=30
        )

        error_output = result.stderr
        # 提取ImportError
        import_errors = re.findall(r'ImportError: (.+)', error_output)
        for error in import_errors:
            if "cannot import name" in error:
                import_issues.append(error)
                # 提取缺失的模块/函数名
                match = re.search(r'cannot import name \'(.+?)\'', error)
                if match:
                    missing_modules.add(match.group(1))

    except subprocess.TimeoutExpired:
        print("测试收集超时")
    except Exception as e:
        print(f"运行测试收集时出错: {e}")

    print(f"发现 {len(import_issues)} 个导入问题")
    print(f"缺失的模块/函数: {list(missing_modules)[:10]}...")

    # 检查src目录中的导入问题
    src_files = list(Path('src').rglob('*.py'))
    for file_path in src_files[:20]:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # 查找循环导入
            if 'from .' in content or 'import .' in content:
                import_issues.append(f"{file_path}: 可能的循环导入")

        except Exception:
            pass

    return import_issues

def analyze_type_annotation_issues():
    """分析类型注解问题"""
    print("\n=== 3. 类型注解问题分析 ===")

    type_issues = []

    # 检查mypy错误
    try:
        result = subprocess.run(
            ["python", "-m", "mypy", "src/utils", "--ignore-missing-imports", "--no-error-summary"],
            capture_output=True,
            text=True,
            timeout=30
        )

        mypy_output = result.stdout
        # 提取类型错误
        type_errors = re.findall(r'error:(.+)', mypy_output)

        for error in type_errors[:20]:
            type_issues.append(error)

    except subprocess.TimeoutExpired:
        print("MyPy检查超时")
    except Exception as e:
        print(f"运行MyPy时出错: {e}")

    print(f"发现 {len(type_issues)} 个类型注解问题")

    # 统计常见问题
    common_issues = Counter()
    for issue in type_issues:
        if "Name" in issue:
            common_issues["未定义名称"] += 1
        elif "attr" in issue:
            common_issues["属性错误"] += 1
        elif "arg" in issue:
            common_issues["参数错误"] += 1
        elif "return" in issue:
            common_issues["返回值错误"] += 1

    print(f"常见类型问题: {dict(common_issues)}")

    return type_issues

def analyze_dependency_issues():
    """分析依赖问题"""
    print("\n=== 4. 依赖问题分析 ===")

    dependency_issues = []

    # 检查requirements文件
    req_files = [
        'requirements.txt',
        'requirements/requirements.txt',
        'requirements/requirements.lock',
        'pyproject.toml'
    ]

    missing_deps = []
    for req_file in req_files:
        if Path(req_file).exists():
            print(f"找到依赖文件: {req_file}")
        else:
            missing_deps.append(req_file)

    if missing_deps:
        print(f"缺失的依赖文件: {missing_deps}")

    # 检查常见依赖
    common_deps = [
        'fastapi', 'sqlalchemy', 'redis', 'celery',
        'pydantic', 'pytest', 'mypy', 'ruff'
    ]

    installed_deps = []
    try:
        import pkg_resources
        installed = {pkg.key for pkg in pkg_resources.working_set}
        for dep in common_deps:
            if dep in installed:
                installed_deps.append(dep)
            else:
                dependency_issues.append(f"缺失依赖: {dep}")
    except:
        pass

    print(f"已安装的常见依赖: {installed_deps}")
    print(f"依赖问题: {len(dependency_issues)} 个")

    return dependency_issues

def analyze_configuration_issues():
    """分析配置问题"""
    print("\n=== 5. 配置问题分析 ===")

    config_issues = []

    # 检查关键配置文件
    config_files = [
        '.env.example',
        '.env',
        'pytest.ini',
        'mypy.ini',
        '.ruff.toml',
        'pyproject.toml',
        '.gitignore',
        'Dockerfile',
        'docker-compose.yml'
    ]

    existing_configs = []
    for config_file in config_files:
        if Path(config_file).exists():
            existing_configs.append(config_file)
        else:
            config_issues.append(f"缺失配置文件: {config_file}")

    print(f"存在的配置文件: {existing_configs}")

    # 检查pytest配置
    if Path('pytest.ini').exists():
        with open('pytest.ini', 'r') as f:
            pytest_config = f.read()
            if 'python_files' not in pytest_config:
                config_issues.append("pytest.ini缺少python_files配置")

    # 检查mypy配置
    if Path('mypy.ini').exists():
        with open('mypy.ini', 'r') as f:
            mypy_config = f.read()
            if '[mypy]' not in mypy_config:
                config_issues.append("mypy.ini缺少[mypy]配置")

    print(f"配置问题: {len(config_issues)} 个")

    return config_issues

def analyze_project_structure():
    """分析项目结构问题"""
    print("\n=== 6. 项目结构问题分析 ===")

    structure_issues = []

    # 检查目录结构
    src_structure = {
        'api': Path('src/api'),
        'core': Path('src/core'),
        'domain': Path('src/domain'),
        'database': Path('src/database'),
        'services': Path('src/services'),
        'utils': Path('src/utils'),
        'tests': Path('tests'),
        'scripts': Path('scripts'),
    }

    for name, path in src_structure.items():
        if path.exists():
            file_count = len(list(path.rglob('*.py')))
            print(f"{name}/: {file_count} 个Python文件")
        else:
            structure_issues.append(f"缺失目录: {name}/")

    # 检查__init__.py文件
    missing_inits = []
    for dir_path in Path('src').rglob('*/'):
        if not (dir_path / '__init__.py').exists() and dir_path != Path('src'):
            missing_inits.append(str(dir_path))

    if missing_inits[:5]:
        print(f"缺失__init__.py的目录: {missing_inits[:5]}...")
        structure_issues.extend(missing_inits[:5])

    # 检查重复文件
    backup_dirs = list(Path('.').glob('src_backup_*'))
    if backup_dirs:
        print(f"发现 {len(backup_dirs)} 个备份目录")
        structure_issues.append(f"存在备份目录: {backup_dirs}")

    print(f"结构问题: {len(structure_issues)} 个")

    return structure_issues

def generate_report():
    """生成完整的问题报告"""

    print("=" * 80)
    print("           足球预测系统基础设施问题深度分析报告")
    print("=" * 80)

    issues = {
        'syntax_errors': analyze_syntax_errors(),
        'import_issues': analyze_import_issues(),
        'type_issues': analyze_type_annotation_issues(),
        'dependency_issues': analyze_dependency_issues(),
        'configuration_issues': analyze_configuration_issues(),
        'structure_issues': analyze_project_structure()
    }

    print("\n" + "=" * 80)
    print("                         问题汇总")
    print("=" * 80)

    total_issues = sum(len(issues[key]) for key in issues)
    print(f"\n总问题数: {total_issues}")
    print("\n各类问题分布:")
    for category, issue_list in issues.items():
        print(f"  - {category}: {len(issue_list)} 个")

    # 优先级建议
    print("\n" + "=" * 80)
    print("                     修复优先级建议")
    print("=" * 80)

    print("\n🔥 高优先级（阻塞性问题）:")
    print("  1. 修复语法错误 - 影响代码解析和测试运行")
    print("  2. 修复导入错误 - 影响模块加载和依赖关系")
    print("  3. 补充缺失的__init__.py文件 - 影响Python包结构")

    print("\n⚡ 中优先级（功能性问题）:")
    print("  1. 修复类型注解错误 - 影响代码质量和IDE支持")
    print("  2. 清理备份目录 - 影响项目整洁度")
    print("  3. 完善配置文件 - 影响开发工具集成")

    print("\n📈 低优先级（优化性问题）:")
    print("  1. 优化项目结构 - 提升可维护性")
    print("  2. 完善依赖管理 - 提升部署稳定性")
    print("  3. 添加更多测试 - 提升代码质量保障")

    # 保存详细报告
    with open('infrastructure_issues_report.json', 'w', encoding='utf-8') as f:
        json.dump(issues, f, ensure_ascii=False, indent=2, default=str)

    print(f"\n详细报告已保存到: infrastructure_issues_report.json")

    return issues

if __name__ == "__main__":
    generate_report()