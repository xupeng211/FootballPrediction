#!/usr/bin/env python3
"""
Docker 容器内连通性验证脚本
验证 app 容器与 db、redis 的连接状态
"""

import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

# 配置日志
log_dir = Path(__file__).parent.parent.parent / "logs"
log_dir.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler(log_dir / "docker_connectivity.log"), logging.StreamHandler()],
)
logger = logging.getLogger(__name__)


class ConnectivityChecker:
    """容器内连通性检查器"""

    def __init__(self):
        self.results = {"timestamp": datetime.now().isoformat(), "checks": {}}

    def check_database(self) -> dict:
        """检查数据库连通性"""
        logger.info("🔍 检查数据库连通性...")
        start_time = time.time()

        try:
            import psycopg2

            from src.config_unified import get_settings

            settings = get_settings()
            db = settings.database

            logger.info(f"📍 连接目标: {db.host}:{db.port}/{db.name}")

            # 测试连接
            conn = psycopg2.connect(
                host=db.host,
                port=db.port,
                database=db.name,
                user=db.user,
                password=db.password.get_secret_value(),
                connect_timeout=10,
            )

            cursor = conn.cursor()

            # 查询数据量
            cursor.execute("SELECT COUNT(*) FROM matches")
            match_count = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM match_features_training")
            feature_count = cursor.fetchone()[0]

            cursor.close()
            conn.close()

            elapsed = (time.time() - start_time) * 1000

            result = {
                "status": "OK",
                "host": db.host,
                "port": db.port,
                "database": db.name,
                "match_count": match_count,
                "feature_count": feature_count,
                "response_time_ms": round(elapsed, 2),
            }

            logger.info(f"✅ 数据库连接成功: {match_count} 场比赛, {feature_count} 条特征")
            return result

        except Exception as e:
            elapsed = (time.time() - start_time) * 1000
            logger.error(f"❌ 数据库连接失败: {e}")
            return {"status": "Fail", "error": str(e), "response_time_ms": round(elapsed, 2)}

    def check_redis(self) -> dict:
        """检查 Redis 连通性"""
        logger.info("🔍 检查 Redis 连通性...")
        start_time = time.time()

        try:
            import redis

            from src.config_unified import get_settings

            settings = get_settings()
            redis_config = settings.redis

            logger.info(f"📍 连接目标: {redis_config.host}:{redis_config.port}")

            # 测试连接
            r = redis.Redis(
                host=redis_config.host,
                port=redis_config.port,
                db=redis_config.db,
                password=redis_config.password.get_secret_value()
                if redis_config.password
                else None,
                socket_timeout=5,
            )

            # 写入测试
            test_key = "connectivity_test"
            test_value = f"test_{datetime.now().isoformat()}"
            r.set(test_key, test_value)
            write_time = (time.time() - start_time) * 1000

            # 读取测试
            start_read = time.time()
            retrieved = r.get(test_key)
            read_time = (time.time() - start_read) * 1000

            # 清理
            r.delete(test_key)
            r.close()

            total_elapsed = (time.time() - start_time) * 1000

            result = {
                "status": "OK",
                "host": redis_config.host,
                "port": redis_config.port,
                "db": redis_config.db,
                "write_latency_ms": round(write_time, 2),
                "read_latency_ms": round(read_time, 2),
                "total_time_ms": round(total_elapsed, 2),
                "data_matched": (retrieved.decode() == test_value),
            }

            logger.info(f"✅ Redis 连接成功: 写入 {write_time:.2f}ms, 读取 {read_time:.2f}ms")
            return result

        except Exception as e:
            elapsed = (time.time() - start_time) * 1000
            logger.error(f"❌ Redis 连接失败: {e}")
            return {"status": "Fail", "error": str(e), "response_time_ms": round(elapsed, 2)}

    def check_model_files(self) -> dict:
        """检查模型文件是否存在"""
        logger.info("🔍 检查模型文件...")
        start_time = time.time()

        try:
            from pathlib import Path

            from src.config_unified import get_settings

            get_settings()

            # 检查模型目录
            models_dir = Path("data/models")
            models_dir.mkdir(parents=True, exist_ok=True)

            # 查找所有模型文件
            model_files = list(models_dir.glob("**/*.pkl")) + list(models_dir.glob("**/*.joblib"))

            result = {
                "status": "OK",
                "models_dir": str(models_dir),
                "model_count": len(model_files),
                "model_files": [str(f) for f in model_files[:5]],  # 只显示前5个
            }

            if len(model_files) > 5:
                result["model_files"].append(f"... and {len(model_files) - 5} more")

            elapsed = (time.time() - start_time) * 1000
            result["scan_time_ms"] = round(elapsed, 2)

            logger.info(f"✅ 找到 {len(model_files)} 个模型文件")
            return result

        except Exception as e:
            elapsed = (time.time() - start_time) * 1000
            logger.error(f"❌ 模型文件检查失败: {e}")
            return {"status": "Fail", "error": str(e), "response_time_ms": round(elapsed, 2)}

    def check_filesystem(self) -> dict:
        """检查文件系统权限"""
        logger.info("🔍 检查文件系统权限...")
        start_time = time.time()

        try:
            from pathlib import Path

            # 检查关键目录
            directories = {
                "logs": Path("logs"),
                "data": Path("data"),
                "data/models": Path("data/models"),
                "data/external": Path("data/external"),
            }

            results = {}
            for name, path in directories.items():
                path.mkdir(parents=True, exist_ok=True)

                # 测试写入
                test_file = path / f".write_test_{os.getpid()}"
                try:
                    test_file.write_text("test")
                    test_file.unlink()
                    results[name] = "OK"
                except Exception as e:
                    results[name] = f"Fail: {str(e)}"

            elapsed = (time.time() - start_time) * 1000

            all_ok = all(v == "OK" for v in results.values())

            result = {
                "status": "OK" if all_ok else "Partial",
                "directories": results,
                "check_time_ms": round(elapsed, 2),
            }

            logger.info(f"✅ 文件系统检查完成: {results}")
            return result

        except Exception as e:
            elapsed = (time.time() - start_time) * 1000
            logger.error(f"❌ 文件系统检查失败: {e}")
            return {"status": "Fail", "error": str(e), "response_time_ms": round(elapsed, 2)}

    def run_all_checks(self) -> dict:
        """运行所有检查"""
        logger.info("=" * 60)
        logger.info("🚀 开始 Docker 容器连通性检查")
        logger.info("=" * 60)

        self.results["checks"]["database"] = self.check_database()
        self.results["checks"]["redis"] = self.check_redis()
        self.results["checks"]["model_files"] = self.check_model_files()
        self.results["checks"]["filesystem"] = self.check_filesystem()

        # 计算总体状态
        all_ok = all(
            check.get("status") in ["OK", "Partial"] for check in self.results["checks"].values()
        )
        self.results["overall_status"] = "OK" if all_ok else "Fail"

        logger.info("=" * 60)
        logger.info(f"📊 连通性检查完成: {self.results['overall_status']}")
        logger.info("=" * 60)

        return self.results

    def print_summary(self):
        """打印检查摘要"""
        print("\n" + "=" * 60)
        print("📋 Docker 容器连通性检查报告")
        print("=" * 60)

        for name, check in self.results["checks"].items():
            status = check.get("status", "Unknown")
            status_icon = "✅" if status in ["OK", "Partial"] else "❌"
            print(f"\n{status_icon} {name.upper()}: {status}")

            if status == "OK" or status == "Partial":
                for key, value in check.items():
                    if key != "status":
                        print(f"   • {key}: {value}")
            else:
                print(f"   • Error: {check.get('error', 'Unknown error')}")

        print("\n" + "=" * 60)
        print(f"总体状态: {self.results['overall_status']}")
        print("=" * 60 + "\n")


def main():
    """主函数"""
    checker = ConnectivityChecker()
    results = checker.run_all_checks()
    checker.print_summary()

    # 返回退出码
    return 0 if results["overall_status"] == "OK" else 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
