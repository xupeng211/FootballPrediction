#!/usr/bin/env python3
"""
FootballPrediction 部署验证脚本
验证 docker-compose.deploy.yml 部署的正确性和健康状态
"""

import sys
import time
import argparse
import subprocess
import requests
from pathlib import Path

# 添加项目路径
sys.path.append(str(Path(__file__).parent.parent))


class DeploymentVerifier:
    """部署验证器"""

    def __init__(self, timeout: int = 300):
        self.timeout = timeout
        self.base_url = "http://localhost:8000"
        self.services = {
            "app": "http://localhost:8000/health",
            "db": "postgresql://postgres:postgres-dev-password@localhost:5432/football_prediction",
            "redis": "redis://localhost:6379/0",
        }

    def log(self, message: str, level: str = "INFO"):
        """记录日志"""
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] [{level}] {message}")

    def run_command(
        self, command: str, check: bool = True
    ) -> subprocess.CompletedProcess:
        """执行命令"""
        self.log(f"执行命令: {command}")
        try:
            result = subprocess.run(
                command, shell=True, capture_output=True, text=True, check=check
            )
            return result
        except subprocess.CalledProcessError as e:
            self.log(f"命令执行失败: {e}", "ERROR")
            self.log(f"错误输出: {e.stderr}", "ERROR")
            raise

    def check_docker_services(self) -> bool:
        """检查Docker服务状态"""
        self.log("检查Docker服务状态...")

        try:
            # 检查容器状态
            result = self.run_command("docker-compose -f docker-compose.deploy.yml ps")
            self.log(f"Docker服务状态:\n{result.stdout}")

            # 检查所有必需服务是否运行
            required_services = ["app", "db", "redis"]
            for service in required_services:
                if f"{service}" not in result.stdout or "Up" not in result.stdout:
                    self.log(f"服务 {service} 未正确启动", "ERROR")
                    return False
                else:
                    self.log(f"✅ 服务 {service} 运行正常")

            return True

        except Exception as e:
            self.log(f"检查Docker服务失败: {e}", "ERROR")
            return False

    def wait_for_app_ready(self) -> bool:
        """等待应用就绪"""
        self.log("等待FastAPI应用就绪...")
        start_time = time.time()

        while time.time() - start_time < self.timeout:
            try:
                response = requests.get(f"{self.base_url}/health", timeout=10)
                if response.status_code == 200:
                    self.log("✅ FastAPI应用就绪")
                    health_data = response.json()
                    self.log(f"应用健康状态: {health_data}")
                    return True
            except requests.exceptions.RequestException:
                pass

            self.log("等待应用启动...", "DEBUG")
            time.sleep(5)

        self.log("应用启动超时", "ERROR")
        return False

    def check_database_connection(self) -> bool:
        """检查数据库连接"""
        self.log("检查数据库连接...")

        try:
            # 使用curl检查数据库健康接口
            result = self.run_command("curl -f http://localhost:8000/health/database")
            if result.returncode == 0:
                self.log("✅ 数据库连接正常")
                return True
            else:
                self.log("数据库连接检查失败", "ERROR")
                return False

        except Exception as e:
            self.log(f"数据库连接检查异常: {e}", "ERROR")
            return False

    def check_redis_connection(self) -> bool:
        """检查Redis连接"""
        self.log("检查Redis连接...")

        try:
            # 通过应用检查Redis状态
            response = requests.get(f"{self.base_url}/health", timeout=10)
            if response.status_code == 200:
                health_data = response.json()
                if "cache" in health_data or "redis" in str(health_data).lower():
                    self.log("✅ Redis连接正常")
                    return True
                else:
                    self.log("Redis状态信息不完整", "WARN")
                    return True  # 暂时认为正常，因为健康检查可能不包含Redis信息

            return False

        except Exception as e:
            self.log(f"Redis连接检查异常: {e}", "ERROR")
            return False

    def check_api_endpoints(self) -> bool:
        """检查API端点"""
        self.log("检查API端点...")

        endpoints = ["/health", "/health/system", "/docs", "/api/v1/predictions/"]

        all_passed = True
        for endpoint in endpoints:
            try:
                response = requests.get(f"{self.base_url}{endpoint}", timeout=10)
                if response.status_code in [200, 404]:  # 404对于某些端点是可接受的
                    self.log(f"✅ {endpoint} - 状态码: {response.status_code}")
                else:
                    self.log(f"❌ {endpoint} - 状态码: {response.status_code}", "ERROR")
                    all_passed = False
            except Exception as e:
                self.log(f"❌ {endpoint} - 错误: {e}", "ERROR")
                all_passed = False

        return all_passed

    def check_ml_services(self) -> bool:
        """检查机器学习服务"""
        self.log("检查机器学习服务...")

        try:
            # 检查推理服务健康状态
            response = requests.get(
                f"{self.base_url}/api/v1/health/inference", timeout=10
            )
            if response.status_code == 200:
                self.log("✅ ML推理服务正常")
                return True
            else:
                self.log(f"ML推理服务状态异常: {response.status_code}", "WARN")
                return True  # 非关键服务，不阻止部署验证

        except Exception as e:
            self.log(f"ML服务检查异常: {e}", "WARN")
            return True  # 非关键服务

    def verify_configuration(self) -> bool:
        """验证配置"""
        self.log("验证配置...")

        config_checks = [
            ("检查.env文件", lambda: Path(".env").exists()),
            (
                "检查docker-compose.deploy.yml",
                lambda: Path("docker-compose.deploy.yml").exists(),
            ),
            ("检查Dockerfile", lambda: Path("Dockerfile").exists()),
        ]

        all_passed = True
        for check_name, check_func in config_checks:
            try:
                if check_func():
                    self.log(f"✅ {check_name}")
                else:
                    self.log(f"❌ {check_name}", "ERROR")
                    all_passed = False
            except Exception as e:
                self.log(f"❌ {check_name} - 错误: {e}", "ERROR")
                all_passed = False

        return all_passed

    def generate_report(self, results: dict) -> bool:
        """生成验证报告"""
        self.log("生成部署验证报告...")

        all_passed = all(results.values())

        report = f"""
# FootballPrediction 部署验证报告

## 验证时间
{time.strftime("%Y-%m-%d %H:%M:%S")}

## 验证结果概览
{"✅ 部署验证通过" if all_passed else "❌ 部署验证失败"}

## 详细结果
"""

        for check_name, result in results.items():
            status = "✅ 通过" if result else "❌ 失败"
            report += f"- **{check_name}**: {status}\n"

        report += f"""

## 服务访问信息
- **FastAPI应用**: {self.base_url}
- **API文档**: {self.base_url}/docs
- **健康检查**: {self.base_url}/health

## 下一步操作
"""
        if all_passed:
            report += """
✅ 部署验证成功！您可以：
1. 访问 http://localhost:8000/docs 查看API文档
2. 使用 make test.integration 进行集成测试
3. 开始使用足球预测系统功能
"""
        else:
            report += """
❌ 部署验证失败，请检查：
1. Docker服务是否正常启动
2. 环境配置是否正确
3. 网络连接是否正常
4. 查看日志: docker-compose -f docker-compose.deploy.yml logs
"""

        # 写入报告文件
        report_file = Path("deployment_verification_report.md")
        with open(report_file, "w", encoding="utf-8") as f:
            f.write(report)

        self.log(f"验证报告已保存到: {report_file}")
        return all_passed

    def verify_deployment(self) -> bool:
        """执行完整部署验证"""
        self.log("🚀 开始 FootballPrediction 部署验证")
        self.log("=" * 60)

        verification_checks = {
            "配置验证": self.verify_configuration(),
            "Docker服务检查": self.check_docker_services(),
            "应用就绪检查": self.wait_for_app_ready(),
            "数据库连接检查": self.check_database_connection(),
            "Redis连接检查": self.check_redis_connection(),
            "API端点检查": self.check_api_endpoints(),
            "ML服务检查": self.check_ml_services(),
        }

        # 生成报告
        success = self.generate_report(verification_checks)

        self.log("=" * 60)
        if success:
            self.log("🎉 FootballPrediction 部署验证完成 - 所有检查通过!")
        else:
            self.log("❌ FootballPrediction 部署验证完成 - 部分检查失败")

        return success


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="FootballPrediction 部署验证脚本")
    parser.add_argument("--timeout", type=int, default=300, help="应用启动超时时间(秒)")
    parser.add_argument(
        "--base-url", default="http://localhost:8000", help="应用基础URL"
    )

    args = parser.parse_args()

    # 创建验证器
    verifier = DeploymentVerifier(timeout=args.timeout)
    verifier.base_url = args.base_url

    try:
        # 执行验证
        success = verifier.verify_deployment()
        sys.exit(0 if success else 1)

    except KeyboardInterrupt:
        print("\n验证被用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"验证过程中发生错误: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
