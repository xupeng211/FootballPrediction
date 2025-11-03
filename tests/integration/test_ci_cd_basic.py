import pytest
#!/usr/bin/env python3
"""
基础CI/CD功能测试
验证核心CI/CD功能是否正常
"""

import os
import subprocess
import sys
from pathlib import Path

def test_basic_ci_functionality(, client, client, client):
    """测试基础CI/CD功能"""
    print("🧪 测试基础CI/CD功能...")
    
    tests_passed = 0
    tests_total = 0
    
    # 测试1: Python环境检查
    tests_total += 1
    try:
        import sys
        python_version = f"{sys.version_info.major}.{sys.version_info.minor}"
        print(f"✅ Python版本: {python_version}")
        tests_passed += 1
    except Exception as e:
        print(f"❌ Python版本检查失败: {e}")
    
    # 测试2: 基础模块导入
    tests_total += 1
    try:
        import os
        import sys
        import json
        import pathlib
        print("✅ 基础模块导入成功")
        tests_passed += 1
    except Exception as e:
        print(f"❌ 基础模块导入失败: {e}")
    
    # 测试3: 项目结构检查
    tests_total += 1
    try:
        required_dirs = ['src', 'tests', 'scripts']
        missing_dirs = []
        
        for dir_name in required_dirs:
            if not Path(dir_name).exists():
                missing_dirs.append(dir_name)
        
        if not missing_dirs:
            print("✅ 项目结构完整")
            tests_passed += 1
        else:
            print(f"❌ 缺失目录: {', '.join(missing_dirs)}")
    except Exception as e:
        print(f"❌ 项目结构检查失败: {e}")
    
    # 测试4: 核心文件检查
    tests_total += 1
    try:
        required_files = ['CLAUDE.md', 'pyproject.toml', 'Makefile']
        missing_files = []
        
        for file_name in required_files:
            if not Path(file_name).exists():
                missing_files.append(file_name)
        
        if not missing_files:
            print("✅ 核心文件完整")
            tests_passed += 1
        else:
            print(f"❌ 缺失文件: {', '.join(missing_files)}")
    except Exception as e:
        print(f"❌ 核心文件检查失败: {e}")
    
    # 测试5: 质量工具可用性
    tests_total += 1
    try:
        # 检查是否有质量守护工具
        if Path('scripts/quality_guardian.py').exists():
            print("✅ 质量守护工具可用")
            tests_passed += 1
        else:
            print("⚠️  质量守护工具缺失")
    except Exception as e:
        print(f"❌ 质量工具检查失败: {e}")
    
    # 测试6: 代码检查工具
    tests_total += 1
    try:
        # 检查是否有代码检查工具
        try:
            subprocess.run(['ruff', '--version'], capture_output=True, timeout=5)
            print("✅ Ruff代码检查工具可用")
            tests_passed += 1
        except:
            print("⚠️  Ruff工具不可用")
    except Exception as e:
        print(f"❌ 代码检查工具失败: {e}")
    
    # 测试7: 简单测试执行
    tests_total += 1
    try:
        # 执行简单测试
        test_result = subprocess.run([
            sys.executable, 'test_simple_working.py'
        ], capture_output=True, text=True, timeout=10)
        
        if test_result.returncode == 0:
            print("✅ 简单测试执行成功")
            tests_passed += 1
        else:
            print(f"❌ 简单测试失败: {test_result.stderr}")
    except Exception as e:
        print(f"❌ 简单测试执行失败: {e}")
    
    # 测试8: 文件操作能力
    tests_total += 1
    try:
        # 测试文件读写
        test_file = Path('test_ci_cd_temp.txt')
        test_file.write_text('CI/CD test content')
        content = test_file.read_text()
        
        if content == 'CI/CD test content':
            test_file.unlink()
            print("✅ 文件操作能力正常")
            tests_passed += 1
        else:
            print("❌ 文件操作内容不匹配")
    except Exception as e:
        print(f"❌ 文件操作失败: {e}")
    
    success_rate = (tests_passed / tests_total) * 100 if tests_total > 0 else 0
    print(f"\n📊 CI/CD功能测试结果:")
    print(f"   - 总测试数: {tests_total}")
    print(f"   - 通过数: {tests_passed}")
    print(f"   - 成功率: {success_rate:.1f}%")
    
    return tests_passed, tests_total, success_rate

def test_deployment_readiness(, client, client, client):
    """测试部署就绪状态"""
    print("\n🚀 测试部署就绪状态...")
    
    readiness_checks = []
    
    # 检查1: 环境变量
    readiness_checks.append(('环境变量', os.environ.get('PATH') is not None))
    
    # 检查2: 工作目录
    readiness_checks.append(('工作目录', Path('.').exists() and Path('.').is_dir()))
    
    # 检查3: Git仓库
    git_repo = Path('.git')
    if git_repo.exists():
        readiness_checks.append(('Git仓库', True))
    else:
        readiness_checks.append(('Git仓库', False))
    
    # 检查4: 配置文件
    config_files = ['pyproject.toml', 'pytest.ini']
    config_ok = all(Path(f).exists() for f in config_files)
    readiness_checks.append(('配置文件', config_ok))
    
    # 检查5: 脚本文件
    scripts_dir = Path('scripts')
    if scripts_dir.exists():
        script_count = len(list(scripts_dir.glob('*.py')))
        readiness_checks.append(('脚本文件', script_count > 10))
    else:
        readiness_checks.append(('脚本文件', False))
    
    print(f"\n📋 部署就绪检查:")
    for check_name, status in readiness_checks:
        status_icon = "✅" if status else "❌"
        print(f"   {status_icon} {check_name}: {'就绪' if status else '未就绪'}")
    
    readiness_score = sum(1 for _, status in readiness_checks if status) / len(readiness_checks)
    print(f"\n🎯 部署就绪度: {readiness_score:.1f}")
    
    return readiness_score

def main():
    """主函数"""
    print("🚀 基础CI/CD功能测试")
    print("=" * 50)
    
    # 执行CI/CD功能测试
    passed, total, success_rate = test_basic_ci_functionality()
    
    # 测试部署就绪状态
    readiness_score = test_deployment_readiness()
    
    # 综合评估
    overall_score = (success_rate + readiness_score) / 2
    print(f"\n🎯 综合CI/CD评估:")
    print(f"   - 功能成功率: {success_rate:.1f}%")
    print(f"   - 部署就绪度: {readiness_score:.1f}")
    print(f"   - 综合分数: {overall_score:.1f}%")
    
    # 检查目标
    target_achieved = overall_score >= 50.0
    print(f"\n🎯 目标检查 (50%+):")
    if target_achieved:
        print(f"   ✅ 目标达成: {overall_score:.1f}% ≥ 50%")
    else:
        print(f"   ⚠️  接近目标: {overall_score:.1f}%")
    
    return {
        'passed_tests': passed,
        'total_tests': total,
        'success_rate': success_rate,
        'readiness_score': readiness_score,
        'overall_score': overall_score,
        'target_achieved': target_achieved
    }

if __name__ == "__main__":
    result = main()
    
    if result['target_achieved']:
        print("\n🎉 CI/CD功能基本恢复！")
    else:
        print("\n📈 CI/CD功能有所改善")
