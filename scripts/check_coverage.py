#!/usr/bin/env python3
"""
检查API模块的测试覆盖率
"""

import subprocess
import sys
import json
from pathlib import Path

def run_command(cmd):
    """运行命令并返回结果"""
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=120
        )
        return result.returncode == 0, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return False, "", "Command timed out"
    except Exception as e:
        return False, "", str(e)

def check_coverage():
    """检查当前覆盖率"""
    print("🔍 检查API模块测试覆盖率...")
    print("=" * 60)

    # 运行所有API测试
    success, stdout, stderr = run_command(
        "python -m pytest tests/unit/api/test_*.py -v --cov=src.api --cov-report=json --tb=no 2>/dev/null"
    )

    if success and Path("coverage.json").exists():
        try:
            with open("coverage.json", "r") as f:
                coverage_data = json.load(f)

            print("📊 覆盖率结果:")
            print("-" * 40)

            if 'files' in coverage_data:
                for file_path, file_data in coverage_data['files'].items():
                    if 'src/api/' in file_path:
                        module_name = file_path.replace('src/api/', '').replace('.py', '')
                        percent = file_data['summary']['percent_covered']
                        covered = file_data['summary']['covered_lines']
                        total = file_data['summary']['num_statements']
                        missing = file_data['summary']['missing_lines']

                        # 根据覆盖率显示不同的图标
                        if percent >= 50:
                            icon = "🟢"
                        elif percent >= 20:
                            icon = "🟡"
                        else:
                            icon = "🔴"

                        print(f"{icon} {module_name:<20} {percent:>5.1f}% ({covered}/{total} 行)")

                        if missing and len(missing) <= 10:
                            print(f"    缺失行: {missing[:5]}{'...' if len(missing) > 5 else ''}")

            print("-" * 40)
            total_percent = coverage_data['totals']['percent_covered']
            print(f"📈 总覆盖率: {total_percent:.1f}%")

            return total_percent
        except Exception as e:
            print(f"❌ 解析覆盖率数据失败: {e}")
            return 0
    else:
        print("⚠️ 无法生成覆盖率报告")
        print("可能的原因:")
        print("  - 缺少pytest-cov插件")
        print("  - 测试导入失败")
        print("  - 依赖问题")
        return 0

def main():
    """主函数"""
    print("🚀 API模块覆盖率检查工具")
    print("=" * 60)

    # 检查环境
    print("检查环境...")
    success, _, _ = run_command("python -m pytest --version")
    if not success:
        print("❌ pytest未安装或不可用")
        return 1

    # 检查覆盖率
    coverage = check_coverage()

    print("\n" + "=" * 60)
    print("📋 总结:")
    if coverage >= 50:
        print("✅ 覆盖率良好!")
        print("   - 当前覆盖率已达到50%+的目标")
        print("   - 可以专注于提升测试质量")
    elif coverage >= 30:
        print("⚠️ 覆盖率中等")
        print("   - 当前覆盖率:", f"{coverage:.1f}%")
        print("   - 建议继续提升到50%+")
    else:
        print("❌ 覆盖率偏低")
        print("   - 当前覆盖率:", f"{coverage:.1f}%")
        print("   - 需要大幅提升测试覆盖率")

    return 0 if coverage >= 30 else 1

if __name__ == "__main__":
    sys.exit(main())