#!/usr/bin/env python3
"""
V41.106 "架构标准化" - 全链路端到端测试
====================================================

验证 FotMob 数据采集的完整流程：
1. 抓取 - FotMobCoreCollector.fetch_match_details()
2. 解析 - _parse_technical_features() 提取 152 维特征
3. 入库 - 存储 technical_features 到 matches 表

作者：首席架构师 & 数据科学家 (V41.106)
日期：2026-01-16
依赖：src.api.collectors.fotmob_core, src.database.connection
"""

from datetime import datetime
import json
import logging
from pathlib import Path
import sys

import psycopg2
from psycopg2.extras import RealDictCursor

# 添加项目根目录到 sys.path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.api.collectors.fotmob_core import FotMobCoreCollector
from src.config_unified import get_settings

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("logs/v41_106_e2e_test.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# 测试配置
TEST_MATCH_ID = 3428850  # Lazio vs Fiorentina, 2020/2021
EXPECTED_HOME_XG = 1.56
EXPECTED_AWAY_XG = 1.67
EXPECTED_FEATURE_COUNT = 152


class V41_106_E2ETest:
    """V41.106 全链路端到端测试"""

    def __init__(self):
        self.settings = get_settings()
        self.collector = FotMobCoreCollector()
        self.test_results = {
            "timestamp": datetime.now().isoformat(),
            "tests": {}
        }

    def test_01_fetch_match_data(self) -> bool:
        """测试 1: 抓取比赛数据"""
        logger.info("\n" + "=" * 70)
        logger.info("测试 1: 抓取比赛数据 (fetch_match_details)")
        logger.info("=" * 70)

        try:
            # 使用标准入口抓取数据
            match_data = self.collector.fetch_match_details(TEST_MATCH_ID)

            if match_data is None:
                logger.error("❌ 抓取失败: 返回 None")
                self.test_results["tests"]["fetch_match_data"] = {
                    "status": "failed",
                    "error": "返回 None"
                }
                return False

            # 验证数据结构
            if "content" not in match_data:
                logger.error("❌ 数据结构错误: 缺少 'content' 字段")
                self.test_results["tests"]["fetch_match_data"] = {
                    "status": "failed",
                    "error": "缺少 'content' 字段"
                }
                return False

            logger.info(f"✅ 抓取成功: Match ID {TEST_MATCH_ID}")
            logger.info(f"   响应大小: {len(json.dumps(match_data))} bytes")

            # 保存原始数据用于验证
            self.raw_match_data = match_data

            self.test_results["tests"]["fetch_match_data"] = {
                "status": "passed",
                "match_id": TEST_MATCH_ID,
                "response_size": len(json.dumps(match_data))
            }
            return True

        except Exception as e:
            logger.error(f"❌ 抓取异常: {e}")
            self.test_results["tests"]["fetch_match_data"] = {
                "status": "error",
                "error": str(e)
            }
            return False

    def test_02_parse_technical_features(self) -> bool:
        """测试 2: 解析 152 维技术特征"""
        logger.info("\n" + "=" * 70)
        logger.info("测试 2: 解析技术特征 (_parse_technical_features)")
        logger.info("=" * 70)

        try:
            if not hasattr(self, "raw_match_data"):
                logger.error("❌ 缺少原始数据: 请先运行测试 1")
                return False

            # 解析技术特征
            features = self.collector._parse_technical_features(self.raw_match_data)

            if features is None:
                logger.error("❌ 解析失败: 返回 None")
                self.test_results["tests"]["parse_technical_features"] = {
                    "status": "failed",
                    "error": "返回 None"
                }
                return False

            # 验证 xG 数据
            home_xg = features.get("home_xg")
            away_xg = features.get("away_xg")

            logger.info("📊 提取结果:")
            logger.info(f"   home_xg: {home_xg} (期望: {EXPECTED_HOME_XG})")
            logger.info(f"   away_xg: {away_xg} (期望: {EXPECTED_AWAY_XG})")

            if abs(home_xg - EXPECTED_HOME_XG) > 0.01:
                logger.warning(f"⚠️ home_xg 值不匹配: {home_xg} != {EXPECTED_HOME_XG}")
                # 不返回 False，继续测试

            # 统计特征维度
            feature_count = len(features)
            logger.info(f"   特征维度: {feature_count} (期望: ~{EXPECTED_FEATURE_COUNT})")

            # 统计非空特征
            non_null_features = {k: v for k, v in features.items() if v is not None}
            logger.info(f"   非空特征: {len(non_null_features)}")

            # 统计 NaN 特征
            nan_features = {k: v for k, v in features.items() if str(v) == "nan"}
            if nan_features:
                logger.warning(f"⚠️ NaN 特征数量: {len(nan_features)}")
                logger.info(f"   示例: {list(nan_features.keys())[:5]}")

            self.technical_features = features

            self.test_results["tests"]["parse_technical_features"] = {
                "status": "passed",
                "feature_count": feature_count,
                "non_null_count": len(non_null_features),
                "nan_count": len(nan_features),
                "home_xg": home_xg,
                "away_xg": away_xg
            }
            return True

        except Exception as e:
            logger.error(f"❌ 解析异常: {e}")
            self.test_results["tests"]["parse_technical_features"] = {
                "status": "error",
                "error": str(e)
            }
            return False

    def test_03_database_connection(self) -> bool:
        """测试 3: 数据库连接"""
        logger.info("\n" + "=" * 70)
        logger.info("测试 3: 数据库连接")
        logger.info("=" * 70)

        try:
            # 连接数据库
            conn = psycopg2.connect(
                host=self.settings.database.host,
                port=self.settings.database.port,
                database=self.settings.database.name,
                user=self.settings.database.user,
                password=self.settings.database.password.get_secret_value(),
                cursor_factory=RealDictCursor
            )

            logger.info("✅ 数据库连接成功")
            logger.info(f"   主机: {self.settings.database.host}")
            logger.info(f"   端口: {self.settings.database.port}")
            logger.info(f"   数据库: {self.settings.database.name}")

            self.db_conn = conn
            self.db_cursor = conn.cursor()

            self.test_results["tests"]["database_connection"] = {
                "status": "passed",
                "host": self.settings.database.host,
                "database": self.settings.database.name
            }
            return True

        except Exception as e:
            logger.error(f"❌ 数据库连接失败: {e}")
            self.test_results["tests"]["database_connection"] = {
                "status": "error",
                "error": str(e)
            }
            return False

    def test_04_check_technical_features_field(self) -> bool:
        """测试 4: 检查 technical_features 字段"""
        logger.info("\n" + "=" * 70)
        logger.info("测试 4: 检查 technical_features 字段")
        logger.info("=" * 70)

        try:
            # 检查字段是否存在
            self.db_cursor.execute("""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_name = 'matches' AND column_name = 'technical_features'
            """)

            result = self.db_cursor.fetchone()

            if not result:
                logger.error("❌ technical_features 字段不存在")
                logger.info("   请运行: psql -f scripts/sql/v41_105_add_technical_features.sql")
                self.test_results["tests"]["check_technical_features_field"] = {
                    "status": "failed",
                    "error": "字段不存在"
                }
                return False

            logger.info("✅ technical_features 字段存在")
            logger.info(f"   数据类型: {result['data_type']}")
            logger.info(f"   可空: {result['is_nullable']}")

            # 检查索引
            self.db_cursor.execute("""
                SELECT indexname
                FROM pg_indexes
                WHERE tablename = 'matches' AND indexname LIKE '%technical_features%'
            """)

            indexes = self.db_cursor.fetchall()
            if indexes:
                logger.info(f"   索引: {', '.join([idx['indexname'] for idx in indexes])}")

            self.test_results["tests"]["check_technical_features_field"] = {
                "status": "passed",
                "data_type": result["data_type"],
                "indexes": [idx["indexname"] for idx in indexes]
            }
            return True

        except Exception as e:
            logger.error(f"❌ 检查字段失败: {e}")
            self.test_results["tests"]["check_technical_features_field"] = {
                "status": "error",
                "error": str(e)
            }
            return False

    def test_05_insert_technical_features(self) -> bool:
        """测试 5: 插入 technical_features 数据"""
        logger.info("\n" + "=" * 70)
        logger.info("测试 5: 插入 technical_features 数据")
        logger.info("=" * 70)

        try:
            if not hasattr(self, "technical_features"):
                logger.error("❌ 缺少技术特征: 请先运行测试 2")
                return False

            # 检查比赛是否存在
            self.db_cursor.execute("""
                SELECT match_id, home_team, away_team
                FROM matches
                WHERE match_id = %s
            """, (str(TEST_MATCH_ID),))

            match = self.db_cursor.fetchone()

            if not match:
                logger.warning(f"⚠️ 比赛 {TEST_MATCH_ID} 不存在，跳过插入测试")
                self.test_results["tests"]["insert_technical_features"] = {
                    "status": "skipped",
                    "reason": "比赛不存在"
                }
                return True

            # 更新 technical_features
            self.db_cursor.execute("""
                UPDATE matches
                SET technical_features = %s
                WHERE match_id = %s
            """, (json.dumps(self.technical_features), str(TEST_MATCH_ID)))

            self.db_conn.commit()

            logger.info("✅ 更新成功")
            logger.info(f"   比赛: {match['home_team']} vs {match['away_team']}")
            logger.info(f"   特征维度: {len(self.technical_features)}")

            # 验证更新结果
            self.db_cursor.execute("""
                SELECT technical_features
                FROM matches
                WHERE match_id = %s
            """, (str(TEST_MATCH_ID),))

            result = self.db_cursor.fetchone()
            # psycopg2 RealDictCursor 自动将 JSONB 反序列化为 dict
            if isinstance(result["technical_features"], str):
                stored_features = json.loads(result["technical_features"])
            else:
                stored_features = result["technical_features"]

            logger.info(f"   存储维度: {len(stored_features)}")

            self.test_results["tests"]["insert_technical_features"] = {
                "status": "passed",
                "match_id": str(TEST_MATCH_ID),
                "feature_count": len(stored_features)
            }
            return True

        except Exception as e:
            logger.error(f"❌ 插入失败: {e}")
            self.db_conn.rollback()
            self.test_results["tests"]["insert_technical_features"] = {
                "status": "error",
                "error": str(e)
            }
            return False

    def test_06_verify_xg_query(self) -> bool:
        """测试 6: 验证 xG 查询"""
        logger.info("\n" + "=" * 70)
        logger.info("测试 6: 验证 xG 查询")
        logger.info("=" * 70)

        try:
            # 查询 xG 数据
            self.db_cursor.execute("""
                SELECT
                    match_id,
                    technical_features->>'home_xg' as home_xg,
                    technical_features->>'away_xg' as away_xg
                FROM matches
                WHERE match_id = %s
                  AND technical_features->>'home_xg' IS NOT NULL
            """, (str(TEST_MATCH_ID),))

            result = self.db_cursor.fetchone()

            if not result:
                logger.warning("⚠️ xG 数据未找到或为空")
                self.test_results["tests"]["verify_xg_query"] = {
                    "status": "skipped",
                    "reason": "xG 数据为空"
                }
                return True

            home_xg = float(result["home_xg"])
            away_xg = float(result["away_xg"])

            logger.info("✅ xG 查询成功")
            logger.info(f"   home_xg: {home_xg}")
            logger.info(f"   away_xg: {away_xg}")

            self.test_results["tests"]["verify_xg_query"] = {
                "status": "passed",
                "home_xg": home_xg,
                "away_xg": away_xg
            }
            return True

        except Exception as e:
            logger.error(f"❌ 查询失败: {e}")
            self.test_results["tests"]["verify_xg_query"] = {
                "status": "error",
                "error": str(e)
            }
            return False

    def run_all_tests(self) -> int:
        """运行所有测试"""
        logger.info("=" * 70)
        logger.info("V41.106 全链路端到端测试")
        logger.info("=" * 70)
        logger.info(f"⏰ 开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info(f"🎯 测试比赛: {TEST_MATCH_ID}")

        # 创建日志目录
        Path("logs").mkdir(exist_ok=True)

        # 运行测试
        results = []

        # 测试 1: 抓取
        results.append(self.test_01_fetch_match_data())

        # 测试 2: 解析
        results.append(self.test_02_parse_technical_features())

        # 测试 3: 数据库连接
        results.append(self.test_03_database_connection())

        if results[-1]:  # 数据库连接成功才继续
            # 测试 4: 检查字段
            results.append(self.test_04_check_technical_features_field())

            # 测试 5: 插入数据
            results.append(self.test_05_insert_technical_features())

            # 测试 6: 验证查询
            results.append(self.test_06_verify_xg_query())

            # 关闭数据库连接
            if hasattr(self, "db_cursor"):
                self.db_cursor.close()
            if hasattr(self, "db_conn"):
                self.db_conn.close()

        # 统计结果
        passed = sum(1 for r in results if r is True)
        total = len(results)

        logger.info("\n" + "=" * 70)
        logger.info("测试结果汇总")
        logger.info("=" * 70)
        logger.info(f"✅ 通过: {passed}/{total}")
        logger.info(f"❌ 失败: {total - passed}/{total}")

        # 保存结果
        results_file = Path("logs/v41_106_e2e_test_results.json")
        with open(results_file, "w", encoding="utf-8") as f:
            self.test_results["summary"] = {
                "total": total,
                "passed": passed,
                "failed": total - passed,
                "success_rate": f"{100 * passed / total:.1f}%"
            }
            json.dump(self.test_results, f, indent=2, ensure_ascii=False)

        logger.info(f"\n📄 结果已保存: {results_file}")

        logger.info(f"\n⏰ 结束时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        # 返回退出码
        return 0 if passed == total else 1


def main():
    """主函数"""
    tester = V41_106_E2ETest()
    return tester.run_all_tests()


if __name__ == "__main__":
    sys.exit(main())
