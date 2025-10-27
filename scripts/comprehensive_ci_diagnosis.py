#!/usr/bin/env python3
"""
全面的CI/CD诊断工具
分析所有失败的工作流并提供修复建议
"""

import subprocess
import re
from pathlib import Path

def analyze_local_issues():
    """分析本地可能存在的问题"""
    print("🔍 分析本地潜在问题...")

    issues = []

    # 1. 检查Python语法
    print("  🔧 检查Python语法...")
    try:
        result = subprocess.run(['python', '-m', 'py_compile', 'src/main.py'],
                              capture_output=True, text=True)
        if result.returncode != 0:
            issues.append(("语法错误", "main.py", result.stderr))
            print(f"    ❌ main.py语法错误: {result.stderr}")
        else:
            print("    ✅ main.py语法正确")
    except Exception as e:
        print(f"    ⚠️ 检查main.py时出错: {e}")

    # 2. 检查依赖问题
    print("  🔧 检查依赖...")
    try:
        result = subprocess.run(['python', '-c', 'import fastapi'],
                              capture_output=True, text=True)
        if result.returncode != 0:
            issues.append(("依赖缺失", "fastapi", result.stderr))
            print(f"    ❌ FastAPI导入失败: {result.stderr}")
        else:
            print("    ✅ FastAPI可用")
    except Exception as e:
        print(f"    ⚠️ 检查FastAPI时出错: {e}")

    # 3. 检查配置文件
    print("  🔧 检查配置文件...")
    config_files = ['requirements.txt', 'pyproject.toml', '.env.example']
    for config_file in config_files:
        if Path(config_file).exists():
            print(f"    ✅ {config_file} 存在")
        else:
            issues.append(("配置缺失", config_file, "文件不存在"))
            print(f"    ❌ {config_file} 不存在")

    return issues

def check_docker_issues():
    """检查Docker相关问题"""
    print("🐳 检查Docker相关问题...")

    docker_issues = []

    # 检查Dockerfile
    if Path('Dockerfile').exists():
        try:
            with open('Dockerfile', 'r') as f:
                content = f.read()

            # 检查常见问题
            if 'COPY requirements.txt' in content and not Path('requirements.txt').exists():
                docker_issues.append(("Docker配置", "requirements.txt缺失",
                                   "Dockerfile引用requirements.txt但文件不存在"))

            if 'python:' not in content:
                docker_issues.append(("Docker配置", "Python基础镜像",
                                   "Dockerfile可能缺少Python基础镜像"))

            print("    ✅ Dockerfile存在且基本配置正确")

        except Exception as e:
            docker_issues.append(("Docker配置", "Dockerfile读取错误", str(e)))
            print(f"    ❌ 读取Dockerfile时出错: {e}")
    else:
        docker_issues.append(("Docker配置", "Dockerfile缺失", "Dockerfile不存在"))
        print("    ❌ Dockerfile不存在")

    # 检查docker-compose.yml
    if Path('docker-compose.yml').exists():
        print("    ✅ docker-compose.yml存在")
    else:
        docker_issues.append(("Docker配置", "docker-compose.yml缺失",
                           "docker-compose.yml不存在"))
        print("    ❌ docker-compose.yml不存在")

    return docker_issues

def check_python_environment():
    """检查Python环境问题"""
    print("🐍 检查Python环境...")

    env_issues = []

    # 检查Python版本
    try:
        result = subprocess.run(['python', '--version'],
                              capture_output=True, text=True)
        version = result.stdout.strip()
        print(f"    ✅ Python版本: {version}")

        if '3.11' not in version and '3.12' not in version:
            env_issues.append(("Python版本", "版本不匹配",
                            f"当前版本 {version}，建议使用3.11+"))

    except Exception as e:
        env_issues.append(("Python版本", "检查失败", str(e)))
        print(f"    ❌ 检查Python版本时出错: {e}")

    # 检查关键模块
    critical_modules = ['fastapi', 'uvicorn', 'sqlalchemy', 'pydantic']
    for module in critical_modules:
        try:
            result = subprocess.run(['python', '-c', f'import {module}'],
                                  capture_output=True, text=True)
            if result.returncode == 0:
                print(f"    ✅ {module} 可用")
            else:
                env_issues.append(("模块缺失", module, result.stderr))
                print(f"    ❌ {module} 导入失败")
        except Exception as e:
            env_issues.append(("模块检查", module, str(e)))
            print(f"    ⚠️ 检查{module}时出错: {e}")

    return env_issues

def check_import_issues():
    """检查导入问题"""
    print("📦 检查导入问题...")

    import_issues = []

    # 检查main.py的导入
    try:
        with open('src/main.py', 'r') as f:
            main_content = f.read()

        # 提取所有import语句
        import_lines = re.findall(r'^\s*(?:from\s+\S+\s+)?import\s+\S+', main_content, re.MULTILINE)

        for import_line in import_lines:
            try:
                # 简单的导入测试
                module_name = re.search(r'import\s+(\w+)', import_line)
                if module_name:
                    module = module_name.group(1)
                    result = subprocess.run(['python', '-c', f'import {module}'],
                                          capture_output=True, text=True)
                    if result.returncode != 0:
                        import_issues.append(("导入错误", module, result.stderr))
                        print(f"    ❌ {module} 导入失败")
                    else:
                        print(f"    ✅ {module} 导入成功")
            except Exception as e:
                print(f"    ⚠️ 检查 {import_line} 时出错: {e}")

    except Exception as e:
        import_issues.append(("src/main.py", "文件读取", str(e)))
        print(f"    ❌ 读取src/main.py时出错: {e}")

    return import_issues

def generate_fix_recommendations(issues):
    """生成修复建议"""
    print("\n🔧 生成修复建议...")

    recommendations = []

    for category, item, details in issues:
        if category == "语法错误":
            recommendations.append(f"修复 {item} 中的语法错误: {details}")
        elif category == "依赖缺失":
            recommendations.append(f"安装缺失的依赖: pip install {item}")
        elif category == "配置缺失":
            recommendations.append(f"创建缺失的配置文件: {item}")
        elif category == "Docker配置":
            recommendations.append(f"修复Docker配置: {details}")
        elif category == "导入错误":
            recommendations.append(f"修复导入问题: {item} - {details}")
        elif category == "Python版本":
            recommendations.append(f"更新Python版本: {details}")

    return recommendations

def run_comprehensive_diagnosis():
    """运行全面诊断"""
    print("🚀 开始全面的CI/CD诊断...")

    all_issues = []

    # 1. 本地问题分析
    local_issues = analyze_local_issues()
    all_issues.extend(local_issues)

    # 2. Docker问题检查
    docker_issues = check_docker_issues()
    all_issues.extend(docker_issues)

    # 3. Python环境检查
    env_issues = check_python_environment()
    all_issues.extend(env_issues)

    # 4. 导入问题检查
    import_issues = check_import_issues()
    all_issues.extend(import_issues)

    # 5. 生成修复建议
    recommendations = generate_fix_recommendations(all_issues)

    # 6. 输出报告
    print("\n📊 诊断总结:")
    print(f"  - 发现问题数: {len(all_issues)}")
    print(f"  - 修复建议数: {len(recommendations)}")

    if all_issues:
        print("\n🔍 问题分类:")
        categories = {}
        for category, item, details in all_issues:
            categories[category] = categories.get(category, 0) + 1

        for category, count in categories.items():
            print(f"  - {category}: {count} 个问题")

    if recommendations:
        print("\n🔧 修复建议:")
        for i, rec in enumerate(recommendations, 1):
            print(f"  {i}. {rec}")

    # 7. 保存报告
    report_content = f"""# CI/CD 诊断报告

## 问题统计
- 总问题数: {len(all_issues)}
- 修复建议数: {len(recommendations)}

## 详细问题
"""
    for category, item, details in all_issues:
        report_content += f"### {category}: {item}\n```\n{details}\n```\n\n"

    report_content += "## 修复建议\n"
    for i, rec in enumerate(recommendations, 1):
        report_content += f"{i}. {rec}\n"

    with open("CI_DIAGNOSIS_REPORT.md", "w", encoding="utf-8") as f:
        f.write(report_content)

    print("\n📄 详细报告已保存到: CI_DIAGNOSIS_REPORT.md")

    return all_issues, recommendations

if __name__ == "__main__":
    run_comprehensive_diagnosis()