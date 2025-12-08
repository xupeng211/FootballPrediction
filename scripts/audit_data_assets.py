#!/usr/bin/env python3
"""
数据资产盘点审计脚本 - 非干扰式只读检查
Non-Destructive Data Assets Audit Script

执行4个关键的只读检查，验证数据库中新数据和架构的完整性
"""

import asyncio
import logging
import sys
import os
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("data_audit.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# 设置环境变量
os.environ.setdefault('DATABASE_URL', 'postgresql://postgres:postgres@db:5432/football_prediction')

@dataclass
class AuditResult:
    """审计结果数据类"""
    check_name: str
    status: str  # "PASS", "FAIL", "WARNING"
    details: Dict[str, Any]
    execution_time: float
    error_message: Optional[str] = None

class DataAssetAuditor:
    """数据资产审计器 - 专门执行非干扰式只读检查"""

    def __init__(self):
        self.db_manager = None
        self.results: List[AuditResult] = []

    async def initialize(self):
        """初始化审计器"""
        try:
            from src.database.async_manager import initialize_database, get_db_session

            logger.info("🔧 初始化数据库连接...")
            initialize_database()
            logger.info("✅ 数据库连接初始化成功")

            # 验证连接
            from sqlalchemy import text
            async with get_db_session() as session:
                result = await session.execute(text("SELECT 1 as test"))
                test_value = result.scalar()
                if test_value != 1:
                    raise RuntimeError("数据库连接验证失败")
                logger.info("✅ 数据库连接验证通过")

            return True

        except Exception as e:
            logger.error(f"❌ 数据库初始化失败: {e}")
            return False

    async def _execute_query_with_timing(self, query: str, query_name: str) -> tuple:
        """执行查询并记录执行时间"""
        from src.database.async_manager import get_db_session
        from sqlalchemy import text
        import time

        start_time = time.time()

        try:
            async with get_db_session() as session:
                result = await session.execute(text(query))
                execution_time = time.time() - start_time

                logger.debug(f"🕒 查询 '{query_name}' 执行时间: {execution_time:.3f}s")
                return result, execution_time

        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"❌ 查询 '{query_name}' 执行失败: {e}")
            raise e

    async def check_schema_integrity(self) -> AuditResult:
        """检查1: Schema完整性检查 - 验证JSON字段数据类型"""
        logger.info("🔍 执行Schema完整性检查...")

        query = """
        SELECT
            column_name,
            data_type,
            udt_name
        FROM information_schema.columns
        WHERE table_name = 'matches'
            AND table_schema = 'public'
            AND (column_name LIKE '%json%' OR column_name LIKE '%stats%' OR column_name LIKE '%environment%')
        ORDER BY column_name;
        """

        try:
            result, execution_time = await self._execute_query_with_timing(query, "Schema Integrity")
            rows = result.fetchall()

            # 验证结果
            expected_json_columns = [
                'stats_json', 'lineups_json', 'odds_snapshot_json',
                'match_info', 'environment_json', 'lineups',
                'stats', 'events', 'odds', 'match_metadata'
            ]

            found_columns = [row[0] for row in rows]
            json_columns = []
            jsonb_columns = []

            for row in rows:
                column_name, data_type, udt_name = row
                if 'json' in data_type.lower() or 'json' in udt_name.lower():
                    json_columns.append((column_name, data_type, udt_name))
                    if data_type.lower() == 'jsonb':
                        jsonb_columns.append(column_name)

            details = {
                "total_columns_found": len(rows),
                "expected_json_columns": len(expected_json_columns),
                "found_columns": found_columns,
                "json_columns": [(col, dtype) for col, dtype, udt in json_columns],
                "jsonb_columns": jsonb_columns,
                "query_result_count": len(rows)
            }

            # 判断检查状态
            status = "PASS"
            if len(json_columns) == 0:
                status = "FAIL"
            elif len(json_columns) < len(expected_json_columns) * 0.8:
                status = "WARNING"

            return AuditResult(
                check_name="Schema Integrity Check",
                status=status,
                details=details,
                execution_time=execution_time
            )

        except Exception as e:
            return AuditResult(
                check_name="Schema Integrity Check",
                status="FAIL",
                details={},
                execution_time=0,
                error_message=str(e)
            )

    async def check_data_volume(self) -> AuditResult:
        """检查2: 数据总量检查 - 统计比赛总数"""
        logger.info("🔍 执行数据总量检查...")

        query = "SELECT COUNT(*) as total_matches FROM matches;"

        try:
            result, execution_time = await self._execute_query_with_timing(query, "Data Volume")
            total_matches = result.scalar()

            # 获取有数据的记录数统计
            detailed_stats_query = """
            SELECT
                COUNT(*) as total_matches,
                COUNT(CASE WHEN stats_json IS NOT NULL THEN 1 END) as matches_with_stats,
                COUNT(CASE WHEN environment_json IS NOT NULL THEN 1 END) as matches_with_environment,
                COUNT(CASE WHEN home_xg IS NOT NULL THEN 1 END) as matches_with_xg,
                MAX(created_at) as latest_record,
                MIN(created_at) as earliest_record
            FROM matches;
            """

            detailed_result, _ = await self._execute_query_with_timing(detailed_stats_query, "Detailed Volume Stats")
            detailed_row = detailed_result.first()

            details = {
                "total_matches": total_matches,
                "matches_with_stats": detailed_row.matches_with_stats,
                "matches_with_environment": detailed_row.matches_with_environment,
                "matches_with_xg": detailed_row.matches_with_xg,
                "data_completeness_pct": round((detailed_row.matches_with_stats / total_matches * 100) if total_matches > 0 else 0, 2),
                "environment_completeness_pct": round((detailed_row.matches_with_environment / total_matches * 100) if total_matches > 0 else 0, 2),
                "xg_completeness_pct": round((detailed_row.matches_with_xg / total_matches * 100) if total_matches > 0 else 0, 2),
                "latest_record": str(detailed_row.latest_record) if detailed_row.latest_record else None,
                "earliest_record": str(detailed_row.earliest_record) if detailed_row.earliest_record else None
            }

            # 判断检查状态
            status = "PASS"
            if total_matches == 0:
                status = "FAIL"
            elif total_matches < 100:
                status = "WARNING"

            return AuditResult(
                check_name="Data Volume Check",
                status=status,
                details=details,
                execution_time=execution_time
            )

        except Exception as e:
            return AuditResult(
                check_name="Data Volume Check",
                status="FAIL",
                details={},
                execution_time=0,
                error_message=str(e)
            )

    async def check_data_quality_xg(self) -> AuditResult:
        """检查3: 数据质量抽样 - 验证xG数据完整性"""
        logger.info("🔍 执行数据质量抽样检查 (xG数据)...")

        # 随机抽取一条有stats_json的记录
        query = """
        SELECT
            id,
            fotmob_id,
            home_team_name,
            away_team_name,
            home_xg,
            away_xg,
            stats_json,
            collection_time
        FROM matches
        WHERE stats_json IS NOT NULL
        ORDER BY RANDOM()
        LIMIT 1;
        """

        try:
            result, execution_time = await self._execute_query_with_timing(query, "Data Quality xG")
            row = result.first()

            if not row:
                return AuditResult(
                    check_name="Data Quality Check (xG)",
                    status="WARNING",
                    details={"message": "No records with stats_json found"},
                    execution_time=execution_time
                )

            # 解析和验证JSON数据
            stats_json = row.stats_json
            home_xg = row.home_xg
            away_xg = row.away_xg

            xg_validation = {
                "has_stats_json": stats_json is not None,
                "stats_json_type": type(stats_json).__name__,
                "home_xg_numeric": home_xg is not None,
                "away_xg_numeric": away_xg is not None,
                "home_xg_value": float(home_xg) if home_xg is not None else None,
                "away_xg_value": float(away_xg) if away_xg is not None else None,
            }

            # 如果stats_json是字符串，尝试解析
            if isinstance(stats_json, str):
                try:
                    parsed_stats = json.loads(stats_json)
                    xg_validation["stats_json_parsed"] = True
                    xg_validation["stats_json_keys"] = list(parsed_stats.keys()) if isinstance(parsed_stats, dict) else "Not a dict"
                except:
                    xg_validation["stats_json_parsed"] = False
            elif isinstance(stats_json, dict):
                xg_validation["stats_json_parsed"] = True
                xg_validation["stats_json_keys"] = list(stats_json.keys())
            else:
                xg_validation["stats_json_parsed"] = False

            details = {
                "sample_match_id": row.id,
                "sample_fotmob_id": row.fotmob_id,
                "sample_match": f"{row.home_team_name} vs {row.away_team_name}",
                "collection_time": str(row.collection_time) if row.collection_time else None,
                "xg_validation": xg_validation
            }

            # 判断检查状态
            status = "PASS"
            if not xg_validation["has_stats_json"]:
                status = "FAIL"
            elif not (xg_validation["home_xg_numeric"] or xg_validation["away_xg_numeric"]):
                status = "WARNING"

            return AuditResult(
                check_name="Data Quality Check (xG)",
                status=status,
                details=details,
                execution_time=execution_time
            )

        except Exception as e:
            return AuditResult(
                check_name="Data Quality Check (xG)",
                status="FAIL",
                details={},
                execution_time=0,
                error_message=str(e)
            )

    async def check_environment_context(self) -> AuditResult:
        """检查4: 环境暗物质抽样 - 验证裁判和场地数据"""
        logger.info("🔍 执行环境暗物质抽样检查 (裁判和场地数据)...")

        query = """
        SELECT
            id,
            fotmob_id,
            home_team_name,
            away_team_name,
            environment_json,
            venue,
            match_time
        FROM matches
        WHERE environment_json IS NOT NULL
        ORDER BY RANDOM()
        LIMIT 1;
        """

        try:
            result, execution_time = await self._execute_query_with_timing(query, "Environment Context")
            row = result.first()

            if not row:
                return AuditResult(
                    check_name="Environment Context Check",
                    status="WARNING",
                    details={"message": "No records with environment_json found"},
                    execution_time=execution_time
                )

            # 解析和验证环境数据
            environment_json = row.environment_json
            venue = row.venue

            env_validation = {
                "has_environment_json": environment_json is not None,
                "environment_json_type": type(environment_json).__name__,
                "has_venue": venue is not None,
                "venue_value": venue
            }

            # 解析environment_json内容
            referee_info = {}
            venue_info = {}

            if isinstance(environment_json, str):
                try:
                    parsed_env = json.loads(environment_json)
                    env_validation["environment_json_parsed"] = True

                    # 检查裁判信息
                    if isinstance(parsed_env, dict) and "referee" in parsed_env:
                        referee_data = parsed_env["referee"]
                        if isinstance(referee_data, dict):
                            referee_info = {
                                "has_referee": True,
                                "has_id": "id" in referee_data,
                                "has_name": "name" in referee_data,
                                "referee_keys": list(referee_data.keys())
                            }
                        else:
                            referee_info = {"has_referee": False, "referee_type": type(referee_data).__name__}
                    else:
                        referee_info = {"has_referee": False}

                    # 检查场地信息
                    if isinstance(parsed_env, dict) and "venue" in parsed_env:
                        venue_data = parsed_env["venue"]
                        if isinstance(venue_data, dict):
                            venue_info = {
                                "has_venue_info": True,
                                "has_coordinates": "coordinates" in venue_data,
                                "has_name": "name" in venue_data,
                                "venue_keys": list(venue_data.keys())
                            }
                        else:
                            venue_info = {"has_venue_info": False, "venue_type": type(venue_data).__name__}
                    else:
                        venue_info = {"has_venue_info": False}

                except Exception as parse_error:
                    env_validation["environment_json_parsed"] = False
                    env_validation["parse_error"] = str(parse_error)
                    referee_info = {"has_referee": False, "error": "Parse failed"}
                    venue_info = {"has_venue_info": False, "error": "Parse failed"}

            elif isinstance(environment_json, dict):
                env_validation["environment_json_parsed"] = True
                # 类似的字典解析逻辑...
            else:
                env_validation["environment_json_parsed"] = False

            details = {
                "sample_match_id": row.id,
                "sample_fotmob_id": row.fotmob_id,
                "sample_match": f"{row.home_team_name} vs {row.away_team_name}",
                "match_time": str(row.match_time) if row.match_time else None,
                "env_validation": env_validation,
                "referee_info": referee_info,
                "venue_info": venue_info
            }

            # 判断检查状态
            status = "PASS"
            if not env_validation["has_environment_json"]:
                status = "FAIL"
            elif not referee_info.get("has_referee") and not venue_info.get("has_venue_info"):
                status = "WARNING"

            return AuditResult(
                check_name="Environment Context Check",
                status=status,
                details=details,
                execution_time=execution_time
            )

        except Exception as e:
            return AuditResult(
                check_name="Environment Context Check",
                status="FAIL",
                details={},
                execution_time=0,
                error_message=str(e)
            )

    async def run_full_audit(self) -> Dict[str, Any]:
        """执行完整的数据资产审计"""
        logger.info("🚀 开始执行完整的数据资产审计...")

        start_time = datetime.now()

        # 执行所有检查
        checks = [
            self.check_schema_integrity(),
            self.check_data_volume(),
            self.check_data_quality_xg(),
            self.check_environment_context()
        ]

        self.results = await asyncio.gather(*checks, return_exceptions=True)

        # 处理异常结果
        processed_results = []
        for result in self.results:
            if isinstance(result, Exception):
                processed_results.append(AuditResult(
                    check_name="Unknown Check",
                    status="FAIL",
                    details={},
                    execution_time=0,
                    error_message=str(result)
                ))
            else:
                processed_results.append(result)

        self.results = processed_results

        end_time = datetime.now()
        total_time = (end_time - start_time).total_seconds()

        # 汇总结果
        summary = {
            "audit_timestamp": start_time.isoformat(),
            "total_execution_time": total_time,
            "total_checks": len(self.results),
            "passed_checks": len([r for r in self.results if r.status == "PASS"]),
            "failed_checks": len([r for r in self.results if r.status == "FAIL"]),
            "warning_checks": len([r for r in self.results if r.status == "WARNING"]),
            "overall_status": "PASS" if all(r.status in ["PASS", "WARNING"] for r in self.results) else "FAIL",
            "results": self.results
        }

        logger.info(f"✅ 审计完成 - 总用时: {total_time:.2f}s")
        logger.info(f"📊 结果: 通过 {summary['passed_checks']}, 失败 {summary['failed_checks']}, 警告 {summary['warning_checks']}")

        return summary

    def generate_markdown_report(self, audit_summary: Dict[str, Any]) -> str:
        """生成Markdown格式的可视化报告"""
        report = []
        report.append("# 📊 数据资产盘点审计报告")
        report.append("")
        report.append("## 📋 审计概览")
        report.append("")
        report.append(f"- **审计时间**: {audit_summary['audit_timestamp']}")
        report.append(f"- **总执行时间**: {audit_summary['total_execution_time']:.3f} 秒")
        report.append(f"- **检查项目**: {audit_summary['total_checks']} 项")
        report.append(f"- **通过检查**: {audit_summary['passed_checks']} 项")
        report.append(f"- **失败检查**: {audit_summary['failed_checks']} 项")
        report.append(f"- **警告检查**: {audit_summary['warning_checks']} 项")
        report.append(f"- **整体状态**: {self._get_status_emoji(audit_summary['overall_status'])} {audit_summary['overall_status']}")
        report.append("")

        # 详细检查结果表格
        report.append("## 🔍 详细检查结果")
        report.append("")
        report.append("| 检查项目 | 状态 | 执行时间 | 关键指标 | 备注 |")
        report.append("|---------|------|----------|----------|------|")

        for result in audit_summary["results"]:
            status_emoji = self._get_status_emoji(result.status)
            key_metrics = self._extract_key_metrics(result.check_name, result.details)
            notes = result.error_message or "正常"

            report.append(f"| {result.check_name} | {status_emoji} {result.status} | {result.execution_time:.3f}s | {key_metrics} | {notes} |")

        report.append("")

        # 详细数据质量信息
        report.append("## 📈 数据质量详情")
        report.append("")

        for result in audit_summary["results"]:
            if result.status == "FAIL" or result.details:
                report.append(f"### {result.check_name}")
                report.append("")
                report.append(f"**状态**: {self._get_status_emoji(result.status)} {result.status}")
                report.append(f"**执行时间**: {result.execution_time:.3f}s")
                report.append("")

                if "total_matches" in result.details:
                    report.append(f"- **比赛总数**: {result.details['total_matches']:,}")
                    report.append(f"- **数据完整度**: {result.details.get('data_completeness_pct', 0):.1f}%")
                    report.append(f"- **环境数据完整度**: {result.details.get('environment_completeness_pct', 0):.1f}%")
                    report.append(f"- **xG数据完整度**: {result.details.get('xg_completeness_pct', 0):.1f}%")

                if "sample_match" in result.details:
                    report.append(f"- **采样比赛**: {result.details['sample_match']}")
                    report.append(f"- **比赛ID**: {result.details.get('sample_match_id')}")

                if "json_columns" in result.details:
                    report.append(f"- **JSON字段数**: {len(result.details['json_columns'])}")
                    report.append(f"- **JSONB字段数**: {len(result.details.get('jsonb_columns', []))}")

                report.append("")

        # 审计结论
        report.append("## 📝 审计结论")
        report.append("")

        if audit_summary['overall_status'] == 'PASS':
            report.append("✅ **审计通过** - 数据资产状态良好，所有关键检查项目均正常")
        elif audit_summary['failed_checks'] == 0:
            report.append("⚠️ **审计通过（含警告）** - 数据资产基本正常，存在部分需要关注的项")
        else:
            report.append("❌ **审计失败** - 发现关键问题，需要立即处理")

        report.append("")
        report.append("---")
        report.append(f"*报告生成时间: {datetime.now().isoformat()}*")

        return "\n".join(report)

    def _get_status_emoji(self, status: str) -> str:
        """获取状态emoji"""
        return {
            "PASS": "✅",
            "FAIL": "❌",
            "WARNING": "⚠️"
        }.get(status, "❓")

    def _extract_key_metrics(self, check_name: str, details: Dict[str, Any]) -> str:
        """提取关键指标用于表格显示"""
        if check_name == "Schema Integrity Check":
            json_cols = len(details.get("json_columns", []))
            return f"{json_cols} JSON字段"

        elif check_name == "Data Volume Check":
            total = details.get("total_matches", 0)
            completeness = details.get("data_completeness_pct", 0)
            return f"{total:,} 场比赛 ({completeness:.1f}%)"

        elif check_name == "Data Quality Check (xG)":
            has_stats = details.get("xg_validation", {}).get("has_stats_json", False)
            has_xg = details.get("xg_validation", {}).get("home_xg_numeric", False) or details.get("xg_validation", {}).get("away_xg_numeric", False)
            return f"Stats: {'✓' if has_stats else '✗'}, xG: {'✓' if has_xg else '✗'}"

        elif check_name == "Environment Context Check":
            has_env = details.get("env_validation", {}).get("has_environment_json", False)
            has_referee = details.get("referee_info", {}).get("has_referee", False)
            return f"Env: {'✓' if has_env else '✗'}, Referee: {'✓' if has_referee else '✗'}"

        return "无关键指标"

async def main():
    """主函数"""
    logger.info("🚀 启动数据资产盘点审计...")

    auditor = DataAssetAuditor()

    # 初始化
    if not await auditor.initialize():
        logger.error("❌ 审计器初始化失败")
        return False

    # 执行审计
    try:
        audit_summary = await auditor.run_full_audit()

        # 生成并保存报告
        markdown_report = auditor.generate_markdown_report(audit_summary)

        # 保存到文件
        report_file = Path("data_audit_report.md")
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(markdown_report)

        logger.info(f"📄 审计报告已保存到: {report_file}")

        # 输出报告到控制台
        print("\n" + "="*60)
        print("📊 数据资产盘点审计报告")
        print("="*60)
        print(markdown_report)

        return audit_summary['overall_status'] == 'PASS'

    except Exception as e:
        logger.error(f"❌ 审计执行失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)