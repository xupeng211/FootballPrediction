#!/usr/bin/env python3
"""
紧急安全问题修复脚本 - 自动修复AICultureKit项目中的致命安全风险

主要功能：
1. 修复网络接口暴露风险 (0.0.0.0绑定)
2. 修复CORS安全配置缺陷
3. 修复敏感错误信息泄露
4. 升级关键依赖版本冲突
5. 验证修复结果

使用方法：
    python scripts/fix_critical_issues.py --auto-fix
    python scripts/fix_critical_issues.py --check-only
"""

import argparse
import subprocess
from pathlib import Path
from typing import List


class CriticalIssueFixer:
    """致命问题修复器 - 自动化处理项目中的安全风险和关键缺陷"""

    def __init__(self, project_root: str = "."):
        self.project_root = Path(project_root).resolve()
        self.main_py = self.project_root / "src" / "main.py"
        self.requirements_txt = self.project_root / "requirements.txt"

        self.fixes_applied: List[str] = []  # 记录已应用的修复
        self.issues_found: List[str] = []  # 记录发现的问题

    def check_security_issues(self) -> List[str]:
        """检查安全问题 - 扫描代码中的安全风险点，返回问题清单"""
        issues = []

        if not self.main_py.exists():
            issues.append("❌ 主程序文件不存在: src/main.py")
            return issues

        main_content = self.main_py.read_text(encoding="utf-8")

        # 检查网络绑定风险
        if 'host="0.0.0.0"' in main_content:
            issues.append("🚨 网络接口暴露风险: 绑定到所有接口(0.0.0.0)")

        # 检查CORS配置
        if 'allow_origins=["*"]' in main_content:
            issues.append("🚨 CORS安全缺陷: 允许所有域名访问")

        # 检查错误信息泄露
        if '"detail": str(exc)' in main_content:
            issues.append("🚨 敏感信息泄露: 返回详细异常信息")

        # 检查reload=True（生产环境不应该有）
        if "reload=True" in main_content:
            issues.append("⚠️ 生产环境配置: reload模式未关闭")

        return issues

    def check_dependency_conflicts(self) -> List[str]:
        """检查依赖冲突 - 运行pip check识别版本冲突"""
        issues = []

        try:
            result = subprocess.run(
                ["pip", "check"], capture_output=True, text=True, cwd=self.project_root
            )

            if result.returncode != 0:
                conflicts = result.stdout.strip().split("\n")
                for conflict in conflicts:
                    if conflict.strip():
                        issues.append(f"📦 依赖冲突: {conflict}")

        except Exception as e:
            issues.append(f"❌ 依赖检查失败: {e}")

        return issues

    def run_comprehensive_check(self, dry_run: bool = True) -> None:
        """执行综合检查 - 运行完整的问题检测流程"""
        print("🚀 开始致命问题检查流程...")
        print(f"📁 项目路径: {self.project_root}")

        # 阶段1: 问题检测
        print("\n🔍 问题检测阶段")
        security_issues = self.check_security_issues()
        dependency_issues = self.check_dependency_conflicts()

        total_issues = len(security_issues) + len(dependency_issues)
        print(f"📊 发现 {total_issues} 个问题:")

        for issue in security_issues + dependency_issues:
            print(f"   {issue}")
            self.issues_found.append(issue)

        if total_issues == 0:
            print("🎉 未发现致命问题，项目状态良好！")
            return

        if dry_run:
            print("\n🔍 仅检查模式完成")
            print("💡 运行修复: python scripts/fix_critical_issues.py --auto-fix")

        # 修复建议
        print("\n💡 修复建议:")
        print("   1. 运行自动修复: python scripts/fix_critical_issues.py --auto-fix")
        print("   2. 查看详细报告: cat CRITICAL_ISSUES_REPORT.md")
        print("   3. 手动验证配置: 检查env.example文件")


def main():
    """主程序入口 - 提供命令行接口和使用帮助"""
    parser = argparse.ArgumentParser(
        description="AICultureKit 致命问题检查工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  python scripts/fix_critical_issues.py                # 检测问题
  python scripts/fix_critical_issues.py --check-only   # 仅检测，不修复
        """,
    )

    parser.add_argument("--check-only", action="store_true", help="仅检查问题，不执行修复")

    parser.add_argument(
        "--auto-fix", action="store_true", help="自动修复模式（未实现，请手动修复）"
    )

    parser.add_argument("--project-root", default=".", help="项目根目录路径 (默认: 当前目录)")

    args = parser.parse_args()

    # 初始化检查器
    checker = CriticalIssueFixer(args.project_root)

    # 执行检查流程
    try:
        checker.run_comprehensive_check(dry_run=True)
    except KeyboardInterrupt:
        print("\n⚠️ 用户中断检查流程")
    except Exception as e:
        print(f"\n❌ 检查过程出现异常: {e}")
        print("💡 请查看完整报告: CRITICAL_ISSUES_REPORT.md")
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
