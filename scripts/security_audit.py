#!/usr/bin/env python3
"""
安全审计脚本
Security Audit Script

对项目进行全面的安全审计，包括：
- 依赖安全漏洞检查
- 配置安全检查
- 代码安全检查
- 权限和安全设置验证
"""

import os
import sys
import subprocess
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any


class SecurityAuditor:
    """安全审计器"""

    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "project_root": str(project_root),
            "findings": [],
            "score": 100,
            "max_score": 100,
            "recommendations": [],
        }

    def run_full_audit(self) -> Dict[str, Any]:
        """运行完整的安全审计"""
        print("🔍 开始安全审计...")

        # 1. 依赖安全检查
        self.audit_dependencies()

        # 2. 配置安全检查
        self.audit_configuration()

        # 3. 代码安全检查
        self.audit_code_security()

        # 4. 文件权限检查
        self.audit_file_permissions()

        # 5. 环境变量安全检查
        self.audit_environment_variables()

        # 6. API安全检查
        self.audit_api_security()

        # 7. 数据库安全检查
        self.audit_database_security()

        # 8. 生成审计报告
        self.generate_report()

        return self.results

    def audit_dependencies(self):
        """审计依赖安全性"""
        print("  📦 检查依赖安全...")

        # 运行safety检查
        try:
            result = subprocess.run(
                ["python", "-m", "safety", "check", "--json"],
                capture_output=True,
                text=True,
                cwd=self.project_root,
            )

            if result.returncode == 0:
                safety_data = json.loads(result.stdout)
                vulnerabilities = safety_data.get("vulnerabilities", [])

                if vulnerabilities:
                    self.results["findings"].append(
                        {
                            "category": "dependencies",
                            "severity": "high",
                            "description": f"发现 {len(vulnerabilities)} 个依赖漏洞",
                            "details": vulnerabilities[:5],  # 只记录前5个
                        }
                    )
                    self.results["score"] -= min(len(vulnerabilities) * 5, 30)
                else:
                    self.results["findings"].append(
                        {
                            "category": "dependencies",
                            "severity": "info",
                            "description": "未发现依赖漏洞",
                        }
                    )
            else:
                self.results["findings"].append(
                    {
                        "category": "dependencies",
                        "severity": "warning",
                        "description": "无法运行依赖安全检查",
                    }
                )

        except Exception as e:
            self.results["findings"].append(
                {
                    "category": "dependencies",
                    "severity": "error",
                    "description": f"依赖安全检查失败: {str(e)}",
                }
            )

    def audit_configuration(self):
        """审计配置安全性"""
        print("  ⚙️ 检查配置安全...")

        # 检查环境变量
        env_files = [".env", ".env.production", ".env.staging"]
        for env_file in env_files:
            env_path = self.project_root / env_file
            if env_path.exists():
                self._check_env_file_security(env_path)

        # 检查配置文件中的敏感信息
        config_files = list(self.project_root.glob("**/*.config")) + list(
            self.project_root.glob("**/config/*.py")
        )

        for config_file in config_files:
            self._check_config_file_secrets(config_file)

    def _check_env_file_security(self, env_file: Path):
        """检查环境变量文件安全性"""
        try:
            with open(env_file, "r") as f:
                content = f.read()

            # 检查敏感信息
            sensitive_patterns = [
                (r"password\s*=.*[\'\"].*[\'\"]", "明文密码"),
                (r"secret_key\s*=.*[\'\"].*[\'\"]", "明文密钥"),
                (r"jwt_secret\s*=.*[\'\"].*[\'\"]", "JWT密钥"),
                (r"database_url\s*=.*[\'\"].*://.*", "数据库连接字符串"),
                (r"api_key\s*=.*[\'\"].*[\'\"]", "API密钥"),
            ]

            issues = []
            for pattern, description in sensitive_patterns:
                if re.search(pattern, content, re.IGNORECASE):
                    issues.append(description)

            if issues:
                self.results["findings"].append(
                    {
                        "category": "configuration",
                        "severity": "high",
                        "description": f"环境变量文件 {env_file.name} 包含敏感信息",
                        "details": issues,
                        "file": str(env_file),
                    }
                )
                self.results["score"] -= len(issues) * 3

            # 检查文件权限
            stat = env_file.stat()
            if stat.st_mode & 0o077:  # 检查是否有组/其他权限
                self.results["findings"].append(
                    {
                        "category": "configuration",
                        "severity": "medium",
                        "description": f"环境变量文件 {env_file.name} 权限过于开放",
                        "file": str(env_file),
                    }
                )
                self.results["score"] -= 5

        except Exception as e:
            self.results["findings"].append(
                {
                    "category": "configuration",
                    "severity": "warning",
                    "description": f"无法检查环境变量文件 {env_file.name}: {str(e)}",
                }
            )

    def _check_config_file_secrets(self, config_file: Path):
        """检查配置文件中的敏感信息"""
        try:
            with open(config_file, "r", encoding="utf-8") as f:
                content = f.read()

            # 检查硬编码的密钥和密码
            secret_patterns = [
                r"(password|secret|key)\s*=\s*[\'\"][^\'\"]+[\'\"]",
                r"(token|auth)\s*=\s*[\'\"][^\'\"]+[\'\"]",
                r"(credential|cred)\s*=\s*[\'\"][^\'\"]+[\'\"]",
            ]

            for pattern in secret_patterns:
                if re.search(pattern, content, re.IGNORECASE):
                    self.results["findings"].append(
                        {
                            "category": "configuration",
                            "severity": "high",
                            "description": "配置文件可能包含硬编码的敏感信息",
                            "file": str(config_file),
                        }
                    )
                    self.results["score"] -= 10
                    break

        except Exception as e:
            self.results["findings"].append(
                {
                    "category": "configuration",
                    "severity": "warning",
                    "description": f"无法检查配置文件 {config_file}: {str(e)}",
                }
            )

    def audit_code_security(self):
        """审计代码安全性"""
        print("  🔒 检查代码安全...")

        # 检查Python源代码
        python_files = list(self.project_root.glob("src/**/*.py"))

        security_issues = {
            "sql_injection": [],
            "hardcoded_secrets": [],
            "weak_crypto": [],
            "insecure_deserialization": [],
            "path_traversal": [],
        }

        for py_file in python_files:
            self._analyze_python_file(py_file, security_issues)

        # 报告发现的问题
        for issue_type, issues in security_issues.items():
            if issues:
                self.results["findings"].append(
                    {
                        "category": "code_security",
                        "severity": "high",
                        "description": f"发现 {len(issues)} 个{issue_type}问题",
                        "details": issues[:3],  # 只记录前3个
                    }
                )
                self.results["score"] -= len(issues) * 5

    def _analyze_python_file(self, file_path: Path, issues: Dict[str, List[str]]):
        """分析Python文件的安全问题"""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            # SQL注入检查
            if re.search(r"(execute|executemany)\s*\(\s*[\"\'].*?\s*\+\s*", content, re.IGNORECASE):
                issues["sql_injection"].append(str(file_path))

            # 硬编码密钥检查
            if re.search(
                r"(password|secret|key|token)\s*=\s*[\"\'\'][^\"\'\'][8,][\"\'\']",
                content,
                re.IGNORECASE,
            ):
                issues["hardcoded_secrets"].append(str(file_path))

            # 弱加密算法检查 (检查不安全的用法)
            # MD5用于文件校验和且设置了usedforsecurity=False是安全的
            if re.search(r"\bmd5\b(?!\s*\(.*usedforsecurity\s*=\s*False)", content, re.IGNORECASE):
                # 检查是否为不安全的MD5用法
                if not re.search(r"md5.*usedforsecurity\s*=\s*False", content, re.IGNORECASE):
                    issues["weak_crypto"].append(f"{file_path}: 使用了不安全的MD5算法")

            # SHA1和DES检查
            if re.search(r"\bsha1\b", content, re.IGNORECASE):
                issues["weak_crypto"].append(f"{file_path}: 使用了弱加密算法 sha1")

            if re.search(r"\bdes\b(?!\w)", content, re.IGNORECASE):
                issues["weak_crypto"].append(f"{file_path}: 使用了弱加密算法 des")

            if re.search(r"\brc4\b", content, re.IGNORECASE):
                issues["weak_crypto"].append(f"{file_path}: 使用了弱加密算法 rc4")

            # 不安全反序列化检查
            if "pickle.load" in content or "pickle.loads" in content:
                issues["insecure_deserialization"].append(str(file_path))

            # 路径遍历检查 (检查可能的恶意路径遍历)
            dangerous_patterns = [
                r"\.\.\/\.\.\/.*\/",  # 多级向上遍历后访问文件
                r"\.\.\\\.\..*\\",  # Windows风格的路径遍历
                r"read.*\.\.",  # 读取操作中的路径遍历
                r"open.*\.\.",  # 文件打开中的路径遍历
            ]
            for pattern in dangerous_patterns:
                if re.search(pattern, content):
                    issues["path_traversal"].append(f"{file_path}: 检测到潜在路径遍历模式")
                    break

        except Exception as e:
            self.results["findings"].append(
                {
                    "category": "code_security",
                    "severity": "warning",
                    "description": f"无法分析文件 {file_path}: {str(e)}",
                }
            )

    def audit_file_permissions(self):
        """审计文件权限"""
        print("  📂 检查文件权限...")

        # 检查关键文件的权限
        critical_files = [
            ".env",
            ".env.production",
            "requirements/requirements.lock",
            "docker-compose.yml",
            "Dockerfile",
        ]

        for file_name in critical_files:
            file_path = self.project_root / file_name
            if file_path.exists():
                stat = file_path.stat()
                mode = oct(stat.st_mode)[-3:]

                # 检查是否过于开放
                if mode in ["777", "666"]:
                    self.results["findings"].append(
                        {
                            "category": "file_permissions",
                            "severity": "medium",
                            "description": f"文件 {file_name} 权限过于开放 ({mode})",
                            "file": str(file_path),
                        }
                    )
                    self.results["score"] -= 3

    def audit_environment_variables(self):
        """审计环境变量安全性"""
        print("  🌍 检查环境变量安全...")

        # 检查是否在代码中硬编码了敏感信息
        env_var_patterns = [
            (
                r"os\.getenv\([\"\'\'](?:PASSWORD|SECRET|KEY|TOKEN|DATABASE_URL)[\"\'\']",
                "硬编码敏感环境变量",
            ),
            (r"os\.environ\[\"\'\'][^\"\'\'][\"\'\']", "使用os.environ访问敏感变量"),
        ]

        python_files = list(self.project_root.glob("src/**/*.py"))

        for py_file in python_files:
            try:
                with open(py_file, "r", encoding="utf-8") as f:
                    content = f.read()

                for pattern, description in env_var_patterns:
                    if re.search(pattern, content):
                        self.results["findings"].append(
                            {
                                "category": "environment_variables",
                                "severity": "medium",
                                "description": description,
                                "file": str(py_file),
                            }
                        )
                        self.results["score"] -= 2
                        break

            except Exception:
                continue

    def audit_api_security(self):
        """审计API安全性"""
        print("  🌐 检查API安全...")

        # 检查API路由文件
        api_files = list(self.project_root.glob("src/api/**/*.py"))

        api_issues = {"no_auth": [], "no_rate_limit": [], "no_cors": [], "exposed_endpoints": []}

        for api_file in api_files:
            self._analyze_api_file(api_file, api_issues)

        # 报告API安全问题
        for issue_type, files in api_issues.items():
            if files:
                self.results["findings"].append(
                    {
                        "category": "api_security",
                        "severity": "medium",
                        "description": f"API安全检查: {issue_type}",
                        "details": files[:3],
                    }
                )
                self.results["score"] -= len(files) * 3

    def _analyze_api_file(self, file_path: Path, issues: Dict[str, List[str]]):
        """分析API文件的安全性"""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            # 检查认证装饰器
            if "@router.get" in content and "@router.post" in content:
                if "Depends" not in content and "auth" not in content.lower():
                    issues["no_auth"].append(str(file_path))

            # 检查速率限制
            if "rate_limit" not in content.lower():
                issues["no_rate_limit"].append(str(file_path))

            # 检查CORS
            if "cors" not in content.lower():
                issues["no_cors"].append(str(file_path))

            except Exception:
            pass

    def audit_database_security(self):
        """审计数据库安全性"""
        print("  🗄️ 检查数据库安全...")

        # 检查数据库迁移文件
        migration_files = list(self.project_root.glob("**/migrations/**/*.py"))

        db_issues = []
        for migration_file in migration_files:
            try:
                with open(migration_file, "r", encoding="utf-8") as f:
                    content = f.read()

                # 检查是否有未加密的敏感数据
                if "password" in content.lower() and "hash" not in content.lower():
                    db_issues.append(f"{migration_file}: 可能包含未加密的密码")

            except Exception:
                pass

        if db_issues:
            self.results["findings"].append(
                {
                    "category": "database_security",
                    "severity": "medium",
                    "description": "数据库安全问题",
                    "details": db_issues[:3],
                }
            )
            self.results["score"] -= len(db_issues) * 4

    def generate_report(self):
        """生成审计报告"""
        # 计算最终分数
        self.results["score"] = max(0, self.results["score"])

        # 生成建议
        self._generate_recommendations()

        # 保存报告
        report_file = self.project_root / "security_audit_report.json"
        with open(report_file, "w", encoding="utf-8") as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False)

        # 打印摘要
        self._print_summary()

    def _generate_recommendations(self):
        """生成安全建议"""
        recommendations = []

        # 基于发现的问题生成建议
        categories = set(f["category"] for f in self.results["findings"])

        if "dependencies" in categories:
            recommendations.append("定期更新依赖包以修复安全漏洞")

        if "configuration" in categories:
            recommendations.append("移除代码中的硬编码敏感信息")
            recommendations.append("使用环境变量管理配置")
            recommendations.append("确保敏感文件的权限设置正确")

        if "code_security" in categories:
            recommendations.append("使用参数化查询避免SQL注入")
            recommendations.append("避免硬编码密钥和密码")
            recommendations.append("使用强加密算法")

        if "api_security" in categories:
            recommendations.append("为API端点添加认证")
            recommendations.append("实施速率限制")
            recommendations.append("配置CORS策略")

        if "file_permissions" in categories:
            recommendations.append("限制敏感文件的权限")

        self.results["recommendations"] = recommendations

    def _print_summary(self):
        """打印审计摘要"""
        print("\n" + "=" * 60)
        print("🔒 安全审计报告")
        print("=" * 60)
        print(f"审计时间: {self.results['timestamp']}")
        print(f"项目路径: {self.results['project_root']}")
        print(f"安全评分: {self.results['score']}/100")
        print(f"发现问题: {len(self.results['findings'])}")

        if self.results["findings"]:
            print("\n🚨 发现的主要问题:")
            for finding in self.results["findings"][:10]:  # 显示前10个问题
                print(f"  • [{finding['severity'].upper()}] {finding['description']}")

        if self.results["recommendations"]:
            print("\n💡 安全建议:")
            for i, rec in enumerate(self.results["recommendations"], 1):
                print(f"  {i}. {rec}")

        print("\n📄 详细报告已保存到: security_audit_report.json")
        print("=" * 60)


def main():
    """主函数"""
    if len(sys.argv) > 1:
        project_root = sys.argv[1]
    else:
        project_root = os.getcwd()

    auditor = SecurityAuditor(project_root)
    results = auditor.run_full_audit()

    # 根据评分设置退出码
    if results["score"] < 70:
        print("\n❌ 安全评分过低，请及时修复安全问题")
        sys.exit(1)
    else:
        print("\n✅ 安全检查通过")
        sys.exit(0)


if __name__ == "__main__":
    main()
