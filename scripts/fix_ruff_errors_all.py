#!/usr/bin/env python3
"""
一键修复所有 Ruff 错误的主脚本
按顺序执行所有修复阶段
"""

import subprocess
import sys
import os

def run_script(script_name, description):
    """运行修复脚本"""
    print(f"\n{'='*80}")
    print(f"🚀 执行: {description}")
    print(f"📄 脚本: {script_name}")
    print('='*80)

    try:
        # 使脚本可执行
        os.chmod(script_name, 0o755)

        # 运行脚本
        result = subprocess.run([sys.executable, script_name],
                              capture_output=True, text=True, check=False)

        if result.returncode == 0:
            print(f"✅ {description} - 成功")
            if result.stdout:
                print(result.stdout[-1000:])  # 显示最后1000字符
        else:
            print(f"⚠️ {description} - 部分成功但有警告")
            if result.stderr:
                print(result.stderr[-500:])  # 显示最后500字符

    except Exception as e:
        print(f"❌ 执行 {script_name} 时出错: {e}")

def check_ruff_errors():
    """检查剩余的 ruff 错误"""
    print(f"\n{'='*80}")
    print("🔍 检查剩余的 Ruff 错误")
    print('='*80)

    try:
        # 统计错误
        cmd = ["ruff", "check", "--output-format=json", "src/", "tests/"]
        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode == 0:
            print("✅ 没有剩余的 Ruff 错误！")
            return True
        else:
            # 统计错误类型
            try:
                import json
                errors = json.loads(result.stdout)
                error_counts = {}
                for error in errors:
                    code = error.get('code', 'UNKNOWN')
                    error_counts[code] = error_counts.get(code, 0) + 1

                print(f"❌ 仍有 {len(errors)} 个错误:")
                for code, count in sorted(error_counts.items(), key=lambda x: x[1], reverse=True):
                    print(f"  - {code}: {count} 个")

            except:
                print("❌ 无法解析错误输出")

            return False

    except Exception as e:
        print(f"❌ 检查错误时出错: {e}")
        return False

def run_make_lint():
    """运行 make lint 验证"""
    print(f"\n{'='*80}")
    print("🧪 运行 make lint 验证")
    print('='*80)

    try:
        result = subprocess.run(["make", "lint"], capture_output=True, text=True)

        if result.returncode == 0:
            print("✅ make lint 通过！所有代码质量检查都通过了！")
            return True
        else:
            print("❌ make lint 失败:")
            print(result.stdout[-2000:])
            print(result.stderr[-2000:])
            return False

    except Exception as e:
        print(f"❌ 运行 make lint 时出错: {e}")
        return False

def main():
    """主函数"""
    print("🔧 Ruff 错误修复 - 一键解决方案")
    print("="*80)
    print("\n本脚本将按顺序执行以下修复步骤：")
    print("1. Phase 1: 修复简单错误（F541, E712 等）")
    print("2. Phase 2: 修复复杂错误（E731, E714, E722 等）")
    print("3. 生成未使用变量修复脚本")
    print("4. 运行 ruff 自动修复")
    print("5. 验证修复结果")

    # 确认继续
    response = input("\n是否继续？(y/N): ")
    if response.lower() not in ['y', 'yes']:
        print("已取消")
        return

    # Phase 1: 修复简单错误
    run_script("scripts/fix_ruff_errors_phase1.py", "Phase 1 - 修复简单错误")

    # Phase 2: 修复复杂错误
    run_script("scripts/fix_ruff_errors_phase2.py", "Phase 2 - 修复复杂错误")

    # 运行生成的未使用变量修复脚本
    if os.path.exists("fix_unused_vars.py"):
        run_script("fix_unused_vars.py", "修复未使用变量")

        # 清理临时脚本
        try:
            os.remove("fix_unused_vars.py")
            print("🗑️ 已清理临时脚本: fix_unused_vars.py")
        except:
            pass

    # 运行 ruff 自动修复
    print(f"\n{'='*80}")
    print("🔧 运行 ruff 自动修复剩余错误")
    print('='*80)

    try:
        result = subprocess.run(["ruff", "check", "--fix", "src/", "tests/"],
                              capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ ruff 自动修复完成")
        else:
            print("⚠️ 部分错误需要手动处理")
    except Exception as e:
        print(f"❌ ruff 自动修复出错: {e}")

    # 检查剩余错误
    has_errors = not check_ruff_errors()

    # 运行 make lint
    lint_passed = run_make_lint()

    # 总结
    print(f"\n{'='*80}")
    print("📊 修复总结")
    print('='*80)

    if not has_errors and lint_passed:
        print("🎉 恭喜！所有 Ruff 错误已修复，make lint 通过！")
        print("\n✅ 代码现在符合所有质量标准！")
    else:
        print("⚠️ 还有部分错误需要手动处理：")
        print("\n1. 查看上述错误列表")
        print("2. 手动修复剩余错误")
        print("3. 再次运行 'make lint' 验证")

        # 提供手动修复建议
        print("\n💡 手动修复建议：")
        print("- 未使用变量：添加下划线前缀（如：teams -> _teams）")
        print("- 裸露 except：改为 except Exception:")
        print("- lambda 赋值：改为 def 函数定义")
        print("- 类型比较：使用 is/isnot 或 isinstance()")

if __name__ == "__main__":
    main()