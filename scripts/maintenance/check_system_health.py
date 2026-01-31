#!/usr/bin/env python3
"""
FootballPrediction - 全系统健康检查脚本
==========================================

检查所有核心组件状态，确保 2026 赛季开始前系统准备就绪。

执行方式:
    python scripts/maintenance/check_system_health.py
    python scripts/maintenance/check_system_health.py --verbose

作者: FootballPrediction Ops Team
版本: V1.0 (2025-12-31)
"""

import sys
import os
import subprocess
from pathlib import Path
from datetime import datetime
from typing import List, Tuple

# 尝试导入可选依赖
try:
    import psycopg2
    HAS_POSTGRES = True
except ImportError:
    HAS_POSTGRES = False

try:
    import redis
    HAS_REDIS = True
except ImportError:
    HAS_REDIS = False

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

# 加载环境变量
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# ANSI 颜色代码
class Colors:
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    BLUE = "\033[94m"
    BOLD = "\033[1m"
    END = "\033[0m"


def print_header(text: str):
    """打印标题"""
    print(f"\n{Colors.BLUE}{Colors.BOLD}{'=' * 60}{Colors.END}")
    print(f"{Colors.BLUE}{Colors.BOLD}{text:^60}{Colors.END}")
    print(f"{Colors.BLUE}{Colors.BOLD}{'=' * 60}{Colors.END}\n")


def print_status(name: str, status: str, details: str = ""):
    """打印状态行"""
    if status == "OK":
        color = Colors.GREEN
        symbol = "✓"
    elif status == "WARNING":
        color = Colors.YELLOW
        symbol = "⚠"
    else:
        color = Colors.RED
        symbol = "✗"

    print(f"{color}{symbol} {name:<30}{Colors.END} {status}")
    if details:
        print(f"  └─ {details}")


class SystemHealthChecker:
    """系统健康检查器"""

    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.results: List[Tuple[str, str, str]] = []
        self.project_root = Path(__file__).parent.parent.parent

        # 从环境变量获取配置
        self.db_host = os.getenv("DB_HOST", "localhost")
        self.db_port = int(os.getenv("DB_PORT", "5432"))
        self.db_name = os.getenv("DB_NAME", "football_prediction_dev")
        self.db_user = os.getenv("DB_USER", "football_user")
        self.db_password = os.getenv("DB_PASSWORD", "football_password_change_in_production")

        self.redis_host = os.getenv("REDIS_HOST", "localhost")
        self.redis_port = int(os.getenv("REDIS_PORT", "6379"))

    def add_result(self, name: str, status: str, details: str = ""):
        """记录检查结果"""
        self.results.append((name, status, details))
        print_status(name, status, details)

    def check_postgresql(self) -> bool:
        """检查 PostgreSQL 数据库连接"""
        if not HAS_POSTGRES:
            self.add_result("PostgreSQL Database", "FAILED", "psycopg2 not installed")
            return False

        try:
            conn = psycopg2.connect(
                host=self.db_host,
                port=self.db_port,
                database=self.db_name,
                user=self.db_user,
                password=self.db_password,
                connect_timeout=5
            )

            cursor = conn.cursor()

            # 检查连接
            cursor.execute("SELECT version();")
            version = cursor.fetchone()[0]

            # 检查数据库大小
            cursor.execute("SELECT pg_size_pretty(pg_database_size(%s));", (self.db_name,))
            db_size = cursor.fetchone()[0]

            # 检查表数量
            cursor.execute("""
                SELECT COUNT(*) FROM information_schema.tables
                WHERE table_schema = 'public';
            """)
            table_count = cursor.fetchone()[0]

            # 检查 matches 表记录数
            cursor.execute("SELECT COUNT(*) FROM matches;")
            match_count = cursor.fetchone()[0]

            # 检查 predictions 表记录数
            cursor.execute("SELECT COUNT(*) FROM predictions;")
            pred_count = cursor.fetchone()[0]

            cursor.close()
            conn.close()

            details = (
                f"PostgreSQL {version.split()[1]} | "
                f"Size: {db_size} | "
                f"Tables: {table_count} | "
                f"Matches: {match_count:,} | "
                f"Predictions: {pred_count:,}"
            )
            self.add_result("PostgreSQL Database", "OK", details)
            return True

        except Exception as e:
            self.add_result("PostgreSQL Database", "FAILED", str(e))
            return False

    def check_redis(self) -> bool:
        """检查 Redis 缓存"""
        if not HAS_REDIS:
            self.add_result("Redis Cache", "FAILED", "redis not installed")
            return False

        try:
            r = redis.Redis(
                host=self.redis_host,
                port=self.redis_port,
                decode_responses=True,
                socket_connect_timeout=5
            )

            # Ping 测试
            r.ping()

            # 获取信息
            info = r.info()

            # 获取 key 数量
            key_count = r.dbsize()

            details = (
                f"Redis {info['redis_version']} | "
                f"Memory: {info['used_memory_human']} | "
                f"Keys: {key_count:,} | "
                f"Uptime: {info['uptime_in_days']} days"
            )
            self.add_result("Redis Cache", "OK", details)
            return True

        except Exception as e:
            self.add_result("Redis Cache", "FAILED", str(e))
            return False

    def check_football_watcher(self) -> bool:
        """检查 football-watcher systemd 服务"""
        try:
            # 获取当前用户名
            username = os.getenv("USER", os.getenv("USERNAME", "user"))
            service_name = f"football-watcher@{username}.service"

            # 检查服务状态
            result = subprocess.run(
                ["systemctl", "is-active", service_name],
                capture_output=True,
                text=True,
                timeout=5
            )

            status = result.stdout.strip()

            if status == "active":
                # 获取详细状态
                result = subprocess.run(
                    ["systemctl", "status", service_name],
                    capture_output=True,
                    text=True,
                    timeout=5
                )

                # 解析运行时间
                for line in result.stdout.split('\n'):
                    if 'active (running)' in line:
                        uptime = line.split(';')[1].strip() if ';' in line else "Unknown"
                        break
                else:
                    uptime = "Unknown"

                self.add_result("Football-Watcher Service", "OK", f"Running | {uptime}")
                return True
            else:
                self.add_result("Football-Watcher Service", "WARNING", f"Status: {status}")
                return False

        except FileNotFoundError:
            self.add_result("Football-Watcher Service", "WARNING", "Not installed (systemctl not found)")
            return False
        except Exception as e:
            self.add_result("Football-Watcher Service", "WARNING", str(e))
            return False

    def check_dashboard(self) -> bool:
        """检查 Streamlit Dashboard"""
        if not HAS_REQUESTS:
            self.add_result("Streamlit Dashboard", "WARNING", "requests not installed, skipping check")
            return False

        try:
            # 尝试连接 localhost:8501
            response = requests.get(
                "http://localhost:8501",
                timeout=5
            )

            if response.status_code == 200:
                self.add_result("Streamlit Dashboard", "OK", "Accessible on port 8501")
                return True
            else:
                self.add_result("Streamlit Dashboard", "WARNING", f"Status: {response.status_code}")
                return False

        except requests.exceptions.ConnectionError:
            self.add_result("Streamlit Dashboard", "WARNING", "Not running (port 8501 not accessible)")
            return False
        except Exception as e:
            self.add_result("Streamlit Dashboard", "WARNING", str(e))
            return False

    def check_data_quality(self) -> bool:
        """检查数据质量"""
        if not HAS_POSTGRES:
            self.add_result("Data Quality", "FAILED", "psycopg2 not installed")
            return False

        try:
            conn = psycopg2.connect(
                host=self.db_host,
                port=self.db_port,
                database=self.db_name,
                user=self.db_user,
                password=self.db_password,
            )

            cursor = conn.cursor()

            # 检查 scheduled 比赛（未来赛程）
            cursor.execute("""
                SELECT COUNT(*) FROM matches
                WHERE status = 'scheduled' AND match_date >= CURRENT_TIMESTAMP;
            """)
            scheduled_count = cursor.fetchone()[0]

            # 检查僵尸比赛
            cursor.execute("""
                SELECT COUNT(*) FROM matches
                WHERE status = 'scheduled' AND match_date < '2025-01-01';
            """)
            zombie_count = cursor.fetchone()[0]

            cursor.close()
            conn.close()

            if zombie_count > 0:
                details = f"Zombie matches detected: {zombie_count:,} | Scheduled: {scheduled_count:,}"
                self.add_result("Data Quality", "WARNING", details)
                return False
            else:
                details = f"Clean database | Scheduled: {scheduled_count:,}"
                self.add_result("Data Quality", "OK", details)
                return True

        except Exception as e:
            self.add_result("Data Quality", "FAILED", str(e))
            return False

    def check_model_files(self) -> bool:
        """检查模型文件"""
        try:
            model_zoo = self.project_root / "model_zoo"

            if not model_zoo.exists():
                self.add_result("Model Files", "FAILED", "model_zoo directory not found")
                return False

            # 检查 V26.8 模型
            v26_models = list(model_zoo.glob("v26.8_*.pkl"))
            v26_count = len(v26_models)

            # 检查 V26.7 模型
            v27_models = list(model_zoo.glob("v26.7_*.pkl"))
            v27_count = len(v27_models)

            if v26_count >= 4:
                details = f"V26.8: {v26_count} models | V26.7: {v27_count} models"
                self.add_result("Model Files", "OK", details)
                return True
            else:
                details = f"V26.8: {v26_count} models (expected 4+) | V26.7: {v27_count} models"
                self.add_result("Model Files", "WARNING", details)
                return False

        except Exception as e:
            self.add_result("Model Files", "FAILED", str(e))
            return False

    def check_prediction_files(self) -> Tuple[int, int]:
        """检查并统计预测文件"""
        try:
            predictions_dir = self.project_root / "predictions"

            if not predictions_dir.exists():
                return 0, 0

            # 统计 CSV 文件
            csv_files = list(predictions_dir.glob("*.csv"))
            test_csvs = [f for f in csv_files if "test" in f.name.lower() or "temp" in f.name.lower()]
            production_csvs = [f for f in csv_files if f not in test_csvs]

            return len(production_csvs), len(test_csvs)

        except Exception:
            return 0, 0

    def check_docker_services(self) -> bool:
        """检查 Docker 服务状态"""
        try:
            result = subprocess.run(
                ["docker-compose", "ps", "-q"],
                capture_output=True,
                text=True,
                timeout=10,
                cwd=self.project_root
            )

            running_count = len([line for line in result.stdout.strip().split('\n') if line])

            if running_count >= 2:
                self.add_result("Docker Services", "OK", f"{running_count} containers running")
                return True
            else:
                self.add_result("Docker Services", "WARNING", f"Only {running_count} containers running (expected 2+)")
                return False

        except FileNotFoundError:
            self.add_result("Docker Services", "WARNING", "docker-compose not found")
            return False
        except Exception as e:
            self.add_result("Docker Services", "WARNING", str(e))
            return False

    def generate_report(self) -> str:
        """生成系统准备就绪报告"""
        report_lines = []

        report_lines.append("=" * 60)
        report_lines.append("FootballPrediction - 系统准备就绪报告")
        report_lines.append("=" * 60)
        report_lines.append(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report_lines.append("")

        # 统计结果
        ok_count = sum(1 for _, status, _ in self.results if status == "OK")
        warning_count = sum(1 for _, status, _ in self.results if status == "WARNING")
        failed_count = sum(1 for _, status, _ in self.results if status == "FAILED")

        report_lines.append("【检查结果统计】")
        report_lines.append(f"  ✓ 正常: {ok_count}")
        report_lines.append(f"  ⚠ 警告: {warning_count}")
        report_lines.append(f"  ✗ 失败: {failed_count}")
        report_lines.append("")

        # 详细结果
        report_lines.append("【详细检查结果】")
        for name, status, details in self.results:
            symbol = "✓" if status == "OK" else ("⚠" if status == "WARNING" else "✗")
            report_lines.append(f"  {symbol} {name}: {status}")
            if details:
                report_lines.append(f"     {details}")

        report_lines.append("")

        # 系统状态评估
        report_lines.append("【系统状态评估】")
        if failed_count > 0:
            status = "❌ 系统未就绪"
            recommendation = "请先修复失败的检查项，然后再部署到生产环境。"
        elif warning_count > 0:
            status = "⚠ 系统基本就绪"
            recommendation = "系统可以运行，但建议解决警告项以获得最佳性能。"
        else:
            status = "✅ 系统完全就绪"
            recommendation = "所有核心组件运行正常，可以开始 2026 赛季预测！"

        report_lines.append(f"  状态: {status}")
        report_lines.append(f"  建议: {recommendation}")
        report_lines.append("")

        # 下一步操作
        report_lines.append("【下一步操作】")

        if failed_count == 0 and warning_count == 0:
            report_lines.append("  1. 启动 Streamlit Dashboard:")
            report_lines.append("     streamlit run dashboards/live_dashboard_2026.py")
            report_lines.append("")
            report_lines.append("  2. 确保 football-watcher 服务运行:")
            report_lines.append("     sudo systemctl start football-watcher@$(whoami).service")
            report_lines.append("")
            report_lines.append("  3. 等待 2026 赛程数据可用（自动监听）")
            report_lines.append("")
            report_lines.append("  4. 查看实时预测结果:")
            report_lines.append("     http://localhost:8501")
        else:
            report_lines.append("  1. 启动 Docker 服务:")
            report_lines.append("     make up")
            report_lines.append("")
            report_lines.append("  2. 查看应用日志:")
            report_lines.append("     tail -f logs/app.log")
            report_lines.append("")
            report_lines.append("  3. 重新运行健康检查:")
            report_lines.append("     python scripts/maintenance/check_system_health.py --verbose")

        report_lines.append("")
        report_lines.append("=" * 60)

        return "\n".join(report_lines)

    def run(self) -> int:
        """执行所有检查"""
        print_header("FootballPrediction - 系统健康检查")

        print(f"{Colors.BOLD}检查时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{Colors.END}")
        print()

        # 执行各项检查
        self.check_postgresql()
        self.check_redis()
        self.check_docker_services()
        self.check_football_watcher()
        self.check_dashboard()
        self.check_data_quality()
        self.check_model_files()

        # 检查预测文件
        prod_count, test_count = self.check_prediction_files()
        if test_count > 0:
            self.add_result(
                "Prediction Files",
                "WARNING",
                f"Production: {prod_count}, Test files to clean: {test_count}"
            )
        else:
            self.add_result(
                "Prediction Files",
                "OK",
                f"Production: {prod_count}, Test files: {test_count}"
            )

        # 生成报告
        print_header("系统准备就绪报告")

        report = self.generate_report()
        print(report)

        # 保存报告到文件
        report_path = self.project_root / "logs" / "system_readiness_report.txt"
        report_path.parent.mkdir(exist_ok=True)
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(report)

        print(f"\n{Colors.BLUE}报告已保存到: {report_path}{Colors.END}\n")

        # 返回退出码
        failed_count = sum(1 for _, status, _ in self.results if status == "FAILED")
        return 1 if failed_count > 0 else 0


def main():
    """主入口"""
    verbose = "--verbose" in sys.argv or "-v" in sys.argv

    checker = SystemHealthChecker(verbose=verbose)
    exit_code = checker.run()

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
