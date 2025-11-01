#!/usr/bin/env python3
"""
依赖包验证脚本
Dependency Verification Script

验证项目依赖包的安装状态和版本兼容性
"""

import sys
import importlib
import subprocess
import os
from pathlib import Path
from typing import Dict, List, Tuple, Any
import json


class DependencyVerifier:
    """依赖包验证器"""

    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.results = {
            "python_version": sys.version,
            "environment": {},
            "dependencies": {},
            "missing_packages": [],
            "version_conflicts": [],
            "summary": {}
        }

    def verify_dependencies(self) -> Dict[str, Any]:
        """执行完整依赖验证"""
        print("🔍 开始依赖包验证...")
        print("=" * 60)

        # 1. 检查Python环境
        self._check_python_environment()

        # 2. 检查关键依赖包
        self._check_critical_dependencies()

        # 3. 检查可选依赖包
        self._check_optional_dependencies()

        # 4. 检查版本兼容性
        self._check_version_compatibility()

        # 5. 生成验证报告
        self._generate_summary()

        return self.results

    def _check_python_environment(self):
        """检查Python环境"""
        print("🐍 检查Python环境...")

        env_info = {
            "version": sys.version,
            "executable": sys.executable,
            "platform": sys.platform,
            "implementation": sys.implementation,
            "paths": sys.path[:5]  # 只显示前5个路径
        }

        self.results["environment"] = env_info

        print(f"  Python版本: {sys.version.split()[0]}")
        print(f"  执行路径: {sys.executable}")
        print(f"  平台: {sys.platform}")
        print()

    def _check_critical_dependencies(self):
        """检查关键依赖包"""
        print("📦 检查关键依赖包...")

        # 关键依赖包列表
        critical_packages = {
            "requests": {"min_version": "2.25.0", "description": "HTTP请求库"},
            "aiohttp": {"min_version": "3.8.0", "description": "异步HTTP客户端"},
            "pyyaml": {"import_name": "yaml", "min_version": "6.0", "description": "YAML配置解析"},
            "psutil": {"min_version": "5.8.0", "description": "系统监控"},
            "pandas": {"min_version": "1.3.0", "description": "数据处理"},
            "numpy": {"min_version": "1.20.0", "description": "数值计算"},
            "redis": {"min_version": "4.0.0", "description": "Redis客户端"},
            "prometheus_client": {"description": "Prometheus监控"},
            "fastapi": {"min_version": "0.68.0", "description": "Web框架"},
            "sqlalchemy": {"min_version": "1.4.0", "description": "ORM框架"},
            "asyncpg": {"min_version": "0.24.0", "description": "PostgreSQL异步驱动"},
            "uvicorn": {"min_version": "0.15.0", "description": "ASGI服务器"}
        }

        for package_name, config in critical_packages.items():
            result = self._check_single_package(package_name, config)
            self.results["dependencies"][package_name] = result

        print()

    def _check_optional_dependencies(self):
        """检查可选依赖包"""
        print("🔧 检查可选依赖包...")

        optional_packages = {
            "matplotlib": {"description": "数据可视化"},
            "scikit-learn": {"description": "机器学习库"},
            "jupyter": {"description": "Jupyter笔记本"},
            "pytest": {"description": "测试框架"},
            "black": {"description": "代码格式化"},
            "mypy": {"description": "类型检查"},
            "bandit": {"description": "安全扫描"},
            "pip-audit": {"description": "依赖安全审计"}
        }

        for package_name, config in optional_packages.items():
            result = self._check_single_package(package_name, config)
            self.results["dependencies"][package_name] = result

        print()

    def _check_single_package(self, package_name: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """检查单个包的状态"""
        import_name = config.get("import_name", package_name)
        min_version = config.get("min_version")
        description = config.get("description", "")

        result = {
            "name": package_name,
            "import_name": import_name,
            "description": description,
            "installed": False,
            "version": None,
            "version_ok": None,
            "error": None
        }

        try:
            # 尝试导入包
            module = importlib.import_module(import_name)
            result["installed"] = True

            # 获取版本信息
            if hasattr(module, "__version__"):
                result["version"] = module.__version__
            elif hasattr(module, "version"):
                result["version"] = module.version
            else:
                # 尝试通过pip获取版本
                version = self._get_package_version(package_name)
                result["version"] = version

            # 检查版本兼容性
            if min_version and result["version"]:
                result["version_ok"] = self._compare_versions(result["version"], min_version)
                if not result["version_ok"]:
                    self.results["version_conflicts"].append({
                        "package": package_name,
                        "current": result["version"],
                        "required": f">={min_version}"
                    })

            status = "✅"
            if min_version and result["version_ok"] is False:
                status = "⚠️"
            elif result["installed"]:
                status = "✅"

            version_info = f" (v{result['version']})" if result["version"] else ""
            version_status = ""
            if min_version and result["version_ok"] is not None:
                version_status = f" [要求: >={min_version}]"

            print(f"  {status} {package_name}{version_info}{version_status}")

        except ImportError as e:
            result["error"] = str(e)
            self.results["missing_packages"].append(package_name)
            print(f"  ❌ {package_name}: 未安装")

        except Exception as e:
            result["error"] = str(e)
            print(f"  ⚠️ {package_name}: 检查失败 - {e}")

        return result

    def _get_package_version(self, package_name: str) -> str:
        """通过pip获取包版本"""
        try:
            result = subprocess.run(
                [sys.executable, "-m", "pip", "show", package_name],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                for line in result.stdout.split("\n"):
                    if line.startswith("Version:"):
                        return line.split(":")[1].strip()
            pass
        return None

    def _compare_versions(self, current: str, required: str) -> bool:
        """比较版本号"""
        try:
            from packaging import version
            return version.parse(current) >= version.parse(required)
        except ImportError:
            # 简单版本比较（如果packaging不可用）
            try:
                current_parts = [int(x) for x in current.split(".")]
                required_parts = [int(x) for x in required.split(".")]

                # 填充较短的版本号
                max_len = max(len(current_parts), len(required_parts))
                current_parts.extend([0] * (max_len - len(current_parts)))
                required_parts.extend([0] * (max_len - len(required_parts)))

                return current_parts >= required_parts
    def _check_version_compatibility(self):
        """检查版本兼容性"""
        print("🔍 检查版本兼容性...")

        if self.results["version_conflicts"]:
            print("  ⚠️ 发现版本冲突:")
            for conflict in self.results["version_conflicts"]:
                print(f"    - {conflict['package']}: {conflict['current']} (要求: {conflict['required']})")
        else:
            print("  ✅ 未发现版本冲突")

        print()

    def _generate_summary(self):
        """生成验证摘要"""
        print("📊 生成验证摘要...")

        total_packages = len(self.results["dependencies"])
        installed_packages = sum(1 for dep in self.results["dependencies"].values() if dep["installed"])
        missing_packages = len(self.results["missing_packages"])
        version_conflicts = len(self.results["version_conflicts"])

        self.results["summary"] = {
            "total_packages": total_packages,
            "installed_packages": installed_packages,
            "missing_packages": missing_packages,
            "version_conflicts": version_conflicts,
            "installation_rate": (installed_packages / total_packages * 100) if total_packages > 0 else 0,
            "status": "OK" if missing_packages == 0 and version_conflicts == 0 else "WARNING"
        }

        summary = self.results["summary"]
        print(f"  总包数: {summary['total_packages']}")
        print(f"  已安装: {summary['installed_packages']}")
        print(f"  缺失: {summary['missing_packages']}")
        print(f"  版本冲突: {summary['version_conflicts']}")
        print(f"  安装率: {summary['installation_rate']:.1f}%")
        print(f"  状态: {summary['status']}")

    def save_report(self, output_file: str = None):
        """保存验证报告"""
        if output_file is None:
            output_file = self.project_root / "dependency_verification_report.json"

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False, default=str)

        print(f"\n📄 验证报告已保存到: {output_file}")

    def print_recommendations(self):
        """打印修复建议"""
        print("\n💡 修复建议:")

        if self.results["missing_packages"]:
            print("  📦 安装缺失的包:")
            missing_str = " ".join(self.results["missing_packages"])
            print(f"    pip install {missing_str}")

        if self.results["version_conflicts"]:
            print("  🔄 更新版本冲突的包:")
            for conflict in self.results["version_conflicts"]:
                print(f"    pip install '{conflict['package']}={conflict['required']}'")

        if not self.results["missing_packages"] and not self.results["version_conflicts"]:
            print("  ✅ 所有依赖包状态良好，无需修复")


def main():
    """主函数"""
    verifier = DependencyVerifier()

    try:
        # 执行验证
        results = verifier.verify_dependencies()

        # 打印建议
        verifier.print_recommendations()

        # 保存报告
        verifier.save_report()

        # 根据结果设置退出码
        summary = results["summary"]
        if summary["status"] == "OK":
            print(f"\n🎉 依赖验证通过! 安装率: {summary['installation_rate']:.1f}%")
            sys.exit(0)
        else:
            print(f"\n⚠️ 依赖验证发现问题，请查看上述建议。安装率: {summary['installation_rate']:.1f}%")
            sys.exit(1)

    except KeyboardInterrupt:
        print("\n\n⏹️ 验证被用户中断")
        sys.exit(130)
    except Exception as e:
        print(f"\n❌ 验证过程中出现错误: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()