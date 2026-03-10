#!/usr/bin/env python3
"""
FootballPrediction - 全系统健康检查脚本 (工业加固版)
==========================================

V4.46.8 工业化加固:
- 环境变量安全: 强制要求 DB_PASSWORD，无默认值回退
- 双重日志: 控制台 + 文件 (/app/logs/)
- 结构化退出码: 0=成功, 1=失败, 2=配置错误
- CLI 标准化: 使用 argparse

执行方式:
    python scripts/maintenance/check_system_health.py
    python scripts/maintenance/check_system_health.py --verbose
    python scripts/maintenance/check_system_health.py --json

作者: FootballPrediction Ops Team
版本: V4.46.8-INDUSTRIAL
"""

import argparse
import json
import logging
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# 路径配置
PROJECT_ROOT = Path(__file__).parent.parent.parent
LOG_DIR = PROJECT_ROOT / "logs"
LOG_DIR.mkdir(exist_ok=True)

# ============================================================================
# 日志配置 - 双重输出 (控制台 + 文件)
# ============================================================================

def setup_logging(verbose: bool = False) -> logging.Logger:
    """配置双重日志输出"""
    log_level = logging.DEBUG if verbose else logging.INFO

    # 创建 logger
    logger = logging.getLogger("check_system_health")
    logger.setLevel(log_level)

    # 清除现有 handlers
    logger.handlers.clear()

    # 日志格式
    formatter = logging.Formatter(
        fmt="[%(asctime)s] [%(levelname)s] [check_system_health] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # 控制台输出
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # 文件输出
    log_file = LOG_DIR / "check_system_health.log"
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(log_level)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger


# ============================================================================
# 可选依赖检查
# ============================================================================

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


# ============================================================================
# 配置类 - 安全加载环境变量
# ============================================================================

class ConfigError(Exception):
    """配置错误异常"""
    pass


def get_required_env(key: str) -> str:
    """获取必需的环境变量，缺失时报错"""
    value = os.getenv(key)
    if not value:
        raise ConfigError(f"缺少必需的环境变量: {key}")
    return value


def get_optional_env(key: str, default: Optional[str] = None) -> Optional[str]:
    """获取可选的环境变量"""
    return os.getenv(key, default)


# ============================================================================
# ANSI 颜色代码
# ============================================================================

class Colors:
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    BLUE = "\033[94m"
    BOLD = "\033[1m"
    END = "\033[0m"


def print_status(name: str, status: str, details: str = "", logger: Optional[logging.Logger] = None):
    """打印状态行"""
    if status == "OK":
        color = Colors.GREEN
        symbol = "✓"
        log_func = logger.info if logger else print
    elif status == "WARNING":
        color = Colors.YELLOW
        symbol = "⚠"
        log_func = logger.warning if logger else print
    else:
        color = Colors.RED
        symbol = "✗"
        log_func = logger.error if logger else print

    print(f"{color}{symbol} {name:<30}{Colors.END} {status}")
    if details:
        print(f"  └─ {details}")

    if logger:
        log_func(f"{name}: {status} - {details}" if details else f"{name}: {status}")


# ============================================================================
# 系统健康检查器
# ============================================================================

class SystemHealthChecker:
    """系统健康检查器"""

    def __init__(self, verbose: bool = False, logger: Optional[logging.Logger] = None):
        self.verbose = verbose
        self.logger = logger or logging.getLogger("check_system_health")
        self.results: List[Dict[str, str]] = []
        self.project_root = PROJECT_ROOT

        # 安全加载配置 - 无默认密码回退
        try:
            self.db_host = get_optional_env("DB_HOST", "localhost") or "localhost"
            self.db_port = int(get_optional_env("DB_PORT", "5432") or "5432")
            self.db_name = get_optional_env("DB_NAME", "football_db") or "football_db"
            self.db_user = get_optional_env("DB_USER", "football_user") or "football_user"
            # 安全关键: 必须从环境变量获取密码
            self.db_password = get_required_env("DB_PASSWORD")

            self.redis_host = get_optional_env("REDIS_HOST", "localhost") or "localhost"
            self.redis_port = int(get_optional_env("REDIS_PORT", "6379") or "6379")

        except ConfigError as e:
            self.logger.error(f"配置错误: {e}")
            self.logger.error("请确保已设置 DB_PASSWORD 环境变量")
            raise

    def add_result(self, name: str, status: str, details: str = ""):
        """记录检查结果"""
        self.results.append({"name": name, "status": status, "details": details})
        print_status(name, status, details, self.logger)

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
            model_dir = self.project_root / "models"

            if not model_dir.exists():
                self.add_result("Model Files", "FAILED", "models directory not found")
                return False

            # 检查 .joblib 模型
            joblib_models = list(model_dir.glob("*.joblib"))
            model_count = len(joblib_models)

            if model_count >= 1:
                details = f"Found {model_count} model files"
                self.add_result("Model Files", "OK", details)
                return True
            else:
                details = f"No model files found in {model_dir}"
                self.add_result("Model Files", "WARNING", details)
                return False

        except Exception as e:
            self.add_result("Model Files", "FAILED", str(e))
            return False

    def generate_report(self, json_output: bool = False) -> str:
        """生成系统准备就绪报告"""
        if json_output:
            return json.dumps({
                "timestamp": datetime.now().isoformat(),
                "results": self.results,
                "summary": {
                    "ok_count": sum(1 for r in self.results if r["status"] == "OK"),
                    "warning_count": sum(1 for r in self.results if r["status"] == "WARNING"),
                    "failed_count": sum(1 for r in self.results if r["status"] == "FAILED"),
                }
            }, indent=2, ensure_ascii=False)

        report_lines = []
        report_lines.append("=" * 60)
        report_lines.append("FootballPrediction - 系统准备就绪报告")
        report_lines.append("=" * 60)
        report_lines.append(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report_lines.append("")

        # 统计结果
        ok_count = sum(1 for r in self.results if r["status"] == "OK")
        warning_count = sum(1 for r in self.results if r["status"] == "WARNING")
        failed_count = sum(1 for r in self.results if r["status"] == "FAILED")

        report_lines.append("【检查结果统计】")
        report_lines.append(f"  ✓ 正常: {ok_count}")
        report_lines.append(f"  ⚠ 警告: {warning_count}")
        report_lines.append(f"  ✗ 失败: {failed_count}")
        report_lines.append("")

        # 详细结果
        report_lines.append("【详细检查结果】")
        for r in self.results:
            symbol = "✓" if r["status"] == "OK" else ("⚠" if r["status"] == "WARNING" else "✗")
            report_lines.append(f"  {symbol} {r['name']}: {r['status']}")
            if r.get("details"):
                report_lines.append(f"     {r['details']}")

        report_lines.append("")

        # 系统状态评估
        report_lines.append("【系统状态评估】")
        if failed_count > 0:
            status = "❌ 系统未就绪"
            recommendation = "请先修复失败的检查项，然后再部署到生产环境。"
            exit_code = 1
        elif warning_count > 0:
            status = "⚠ 系统基本就绪"
            recommendation = "系统可以运行，但建议解决警告项以获得最佳性能。"
            exit_code = 0
        else:
            status = "✅ 系统完全就绪"
            recommendation = "所有核心组件运行正常，可以开始预测！"
            exit_code = 0

        report_lines.append(f"  状态: {status}")
        report_lines.append(f"  建议: {recommendation}")

        return "\n".join(report_lines), exit_code

    def run(self, json_output: bool = False) -> Tuple[str, int]:
        """执行所有检查"""
        print(f"\n{Colors.BLUE}{Colors.BOLD}{'=' * 60}{Colors.END}")
        print(f"{Colors.BLUE}{Colors.BOLD}FootballPrediction - 系统健康检查 (工业加固版){Colors.END}")
        print(f"{Colors.BLUE}{Colors.BOLD}{'=' * 60}{Colors.END}\n")

        self.logger.info("开始系统健康检查")

        # 执行各项检查
        self.check_postgresql()
        self.check_redis()
        self.check_docker_services()
        self.check_data_quality()
        self.check_model_files()

        # 生成报告
        print(f"\n{Colors.BLUE}{Colors.BOLD}{'=' * 60}{Colors.END}")
        print(f"{Colors.BLUE}{Colors.BOLD}系统准备就绪报告{Colors.END}")
        print(f"{Colors.BLUE}{Colors.BOLD}{'=' * 60}{Colors.END}\n")

        if json_output:
            report = self.generate_report(json_output=True)
            print(report)
            exit_code = 1 if any(r["status"] == "FAILED" for r in self.results) else 0
        else:
            report, exit_code = self.generate_report(json_output=False)
            print(report)

        # 保存报告到文件
        report_path = LOG_DIR / "system_readiness_report.txt"
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(report)

        self.logger.info(f"报告已保存到: {report_path}")

        return report, exit_code


# ============================================================================
# CLI 入口
# ============================================================================

def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description="FootballPrediction 系统健康检查 - 工业加固版",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python scripts/maintenance/check_system_health.py
  python scripts/maintenance/check_system_health.py --verbose
  python scripts/maintenance/check_system_health.py --json

环境变量:
  DB_PASSWORD    数据库密码 (必需)
  DB_HOST        数据库主机 (默认: localhost)
  DB_PORT        数据库端口 (默认: 5432)
  DB_NAME        数据库名称 (默认: football_db)
  REDIS_HOST     Redis 主机 (默认: localhost)
  REDIS_PORT     Redis 端口 (默认: 6379)
        """
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="详细输出模式")
    parser.add_argument("--json", action="store_true", help="JSON 格式输出")
    return parser.parse_args()


def main():
    """主入口 - 带全局异常捕获"""
    args = parse_args()

    # 配置日志
    logger = setup_logging(args.verbose)

    try:
        checker = SystemHealthChecker(verbose=args.verbose, logger=logger)
        report, exit_code = checker.run(json_output=args.json)
        sys.exit(exit_code)

    except ConfigError as e:
        logger.error(f"配置错误: {e}")
        logger.error("请检查环境变量配置")
        sys.exit(2)  # 配置错误专用退出码

    except Exception as e:
        logger.exception(f"未预期的错误: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
