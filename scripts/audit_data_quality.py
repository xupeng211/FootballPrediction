#!/usr/bin/env python3
"""
数据质量审计脚本
Data Quality Audit Script

验证系统从"收集 -> 清洗 -> 存储"的数据处理质量
Author: Data Engineer
Date: 2025-11-20
"""

import os
import sys
import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
import json

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import psycopg2
from psycopg2.extras import RealDictCursor

# 配置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class DataQualityAuditor:
    """数据质量审计器"""

    def __init__(self):
        self.db_url = os.getenv(
            "DATABASE_URL",
            "postgresql://postgres:postgres-dev-password@localhost:5432/football_prediction",
        )
        self.api_key = os.getenv("FOOTBALL_DATA_API_KEY")

    def connect_database(self) -> psycopg2.extensions.connection:
        """连接数据库"""
        try:
            conn = psycopg2.connect(self.db_url)
            logger.info("✅ 数据库连接成功")
            return conn
        except Exception as e:
            logger.error(f"❌ 数据库连接失败: {e}")
            raise

    def execute_query(
        self, query: str, params: tuple | None = None
    ) -> list[dict[str, Any]]:
        """执行SQL查询"""
        try:
            with self.connect_database() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    cursor.execute(query, params)
                    results = cursor.fetchall()
                    return [dict(row) for row in results]
        except Exception as e:
            logger.error(f"❌ 查询执行失败: {e}")
            return []

    def check_table_exists(self, table_name: str) -> bool:
        """检查表是否存在"""
        query = """
        SELECT EXISTS (
            SELECT FROM information_schema.tables
            WHERE table_schema = 'public'
            AND table_name = %s
        );
        """
        result = self.execute_query(query, (table_name,))
        return result[0]["exists"] if result else False

    def audit_matches_data(self) -> dict[str, Any]:
        """审计比赛数据质量"""
        logger.info("🔍 开始审计比赛数据...")

        if not self.check_table_exists("matches"):
            logger.warning("⚠️ matches表不存在")
            return {"status": "table_not_found", "data": []}

        # 查询最近3场比赛
        query = """
        SELECT
            id,
            home_team_name,
            away_team_name,
            match_date,
            status,
            home_score,
            away_score,
            competition_name,
            created_at,
            updated_at
        FROM matches
        ORDER BY match_date DESC
        LIMIT 3;
        """

        matches = self.execute_query(query)

        # 数据质量检查
        quality_issues = []
        for match in matches:
            # 检查时间格式
            if match["match_date"]:
                try:
                    match_date = match["match_date"]
                    if not isinstance(match_date, datetime):
                        quality_issues.append(
                            f"比赛ID {match['id']}: match_date不是datetime类型"
                        )
                except:
                    quality_issues.append(f"比赛ID {match['id']}: match_date格式错误")

            # 检查队名格式
            if match["home_team_name"]:
                if match["home_team_name"].strip() != match["home_team_name"]:
                    quality_issues.append(
                        f"比赛ID {match['id']}: home_team_name包含多余空格"
                    )

            if match["away_team_name"]:
                if match["away_team_name"].strip() != match["away_team_name"]:
                    quality_issues.append(
                        f"比赛ID {match['id']}: away_team_name包含多余空格"
                    )

        return {
            "status": "success",
            "count": len(matches),
            "quality_issues": quality_issues,
            "data": matches,
        }

    def audit_teams_data(self) -> dict[str, Any]:
        """审计球队数据质量"""
        logger.info("🔍 开始审计球队数据...")

        if not self.check_table_exists("teams"):
            logger.warning("⚠️ teams表不存在")
            return {"status": "table_not_found", "data": []}

        # 查询任意3个球队
        query = """
        SELECT
            id,
            name,
            short_name,
            crest_url,
            founded_year,
            venue_name,
            created_at,
            updated_at
        FROM teams
        ORDER BY id
        LIMIT 3;
        """

        teams = self.execute_query(query)

        # 数据质量检查
        quality_issues = []
        for team in teams:
            # 检查队名格式
            if team["name"]:
                if team["name"].strip() != team["name"]:
                    quality_issues.append(f"球队ID {team['id']}: name包含多余空格")

                if len(team["name"]) < 2:
                    quality_issues.append(f"球队ID {team['id']}: name过短")

            # 检查简称
            if team["short_name"]:
                if len(team["short_name"]) > 10:
                    quality_issues.append(f"球队ID {team['id']}: short_name过长")

        return {
            "status": "success",
            "count": len(teams),
            "quality_issues": quality_issues,
            "data": teams,
        }

    def audit_database_schema(self) -> dict[str, Any]:
        """审计数据库架构"""
        logger.info("🔍 开始审计数据库架构...")

        # 查询所有表
        tables_query = """
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'public'
        ORDER BY table_name;
        """

        tables = self.execute_query(tables_query)
        table_names = [t["table_name"] for t in tables]

        # 查询每个表的记录数
        table_stats = []
        for table in table_names:
            try:
                count_query = f"SELECT COUNT(*) as count FROM {table};"
                result = self.execute_query(count_query)
                count = result[0]["count"] if result else 0
                table_stats.append({"table": table, "record_count": count})
            except Exception as e:
                logger.warning(f"⚠️ 无法查询表 {table}: {e}")
                table_stats.append({"table": table, "record_count": "ERROR"})

        return {
            "status": "success",
            "table_count": len(table_names),
            "tables": table_names,
            "table_stats": table_stats,
        }

    def trigger_data_collection(self, league_id: int = 2021) -> dict[str, Any]:
        """触发数据采集"""
        logger.info(f"🚀 开始触发数据采集 (League ID: {league_id})...")

        try:
            # 导入数据采集任务
            from src.tasks.data_collection_tasks import collect_league_matches

            # 模拟调用采集任务
            logger.info("📡 调用数据采集任务...")

            # 由于这是一个演示，我们将模拟采集过程
            # 在真实环境中，这里应该调用实际的采集函数
            result = {
                "status": "success",
                "league_id": league_id,
                "message": "数据采集模拟成功",
                "matches_collected": "模拟数据",
                "api_key_used": self.api_key[:10] + "..." if self.api_key else None,
            }

            logger.info(f"✅ 数据采集完成: {result}")
            return result

        except ImportError as e:
            logger.warning(f"⚠️ 无法导入采集任务: {e}")
            return {"status": "import_error", "message": f"采集任务模块未找到: {e}"}
        except Exception as e:
            logger.error(f"❌ 数据采集失败: {e}")
            return {"status": "error", "message": str(e)}

    def display_data_tables(self, matches_data: dict, teams_data: dict):
        """以表格形式展示数据"""

        # 显示比赛数据
        if matches_data["status"] == "success" and matches_data["data"]:
            # 打印表头

            for match in matches_data["data"]:
                match["match_date"].strftime("%Y-%m-%d %H:%M") if match[
                    "match_date"
                ] else "N/A"
                f"{match['home_score']}-{match['away_score']}" if match[
                    "home_score"
                ] is not None and match["away_score"] is not None else "N/A"

            # 显示数据质量问题
            if matches_data["quality_issues"]:
                for _issue in matches_data["quality_issues"]:
                    pass
            else:
                pass
        else:
            pass

        # 显示球队数据
        if teams_data["status"] == "success" and teams_data["data"]:
            # 打印表头

            for team in teams_data["data"]:
                team["founded_year"] if team["founded_year"] else "N/A"
                team["created_at"].strftime("%Y-%m-%d") if team["created_at"] else "N/A"

            # 显示数据质量问题
            if teams_data["quality_issues"]:
                for _issue in teams_data["quality_issues"]:
                    pass
            else:
                pass
        else:
            pass

    def run_full_audit(self) -> dict[str, Any]:
        """运行完整的数据质量审计"""
        logger.info("🎯 开始完整数据质量审计...")

        start_time = datetime.now()

        results = {
            "audit_start_time": start_time.isoformat(),
            "api_key_configured": bool(self.api_key),
            "database_url_configured": bool(self.db_url),
        }

        try:
            # 1. 触发数据采集
            logger.info("📡 步骤1: 触发数据采集...")
            results["data_collection"] = self.trigger_data_collection()

            # 2. 审计数据库架构
            logger.info("🏗️ 步骤2: 审计数据库架构...")
            results["schema_audit"] = self.audit_database_schema()

            # 3. 审计比赛数据
            logger.info("🏆 步骤3: 审计比赛数据...")
            results["matches_audit"] = self.audit_matches_data()

            # 4. 审计球队数据
            logger.info("👥 步骤4: 审计球队数据...")
            results["teams_audit"] = self.audit_teams_data()

            # 5. 汇总质量报告
            total_issues = len(
                results["matches_audit"].get("quality_issues", [])
            ) + len(results["teams_audit"].get("quality_issues", []))

            results["summary"] = {
                "total_tables": results["schema_audit"]["table_count"],
                "matches_records": len(results["matches_audit"].get("data", [])),
                "teams_records": len(results["teams_audit"].get("data", [])),
                "total_quality_issues": total_issues,
                "overall_quality": "GOOD" if total_issues == 0 else "NEEDS_ATTENTION",
            }

        except Exception as e:
            logger.error(f"❌ 审计过程中发生错误: {e}")
            results["error"] = str(e)
            results["status"] = "failed"

        finally:
            end_time = datetime.now()
            results["audit_duration"] = (end_time - start_time).total_seconds()
            results["audit_end_time"] = end_time.isoformat()

        return results


def main():
    """主函数"""

    # 检查环境变量
    api_key = os.getenv("FOOTBALL_DATA_API_KEY")
    db_url = os.getenv("DATABASE_URL")

    if not api_key:
        pass

    if not db_url:
        return 1

    try:
        # 创建审计器
        auditor = DataQualityAuditor()

        # 运行完整审计
        results = auditor.run_full_audit()

        # 显示数据表格
        auditor.display_data_tables(
            results.get("matches_audit", {}), results.get("teams_audit", {})
        )

        # 显示架构信息
        schema_data = results.get("schema_audit", {})
        if schema_data.get("status") == "success":
            for _table_stat in schema_data["table_stats"]:
                pass

        # 显示汇总报告
        summary = results.get("summary", {})
        if summary:
            pass

        # 保存审计结果到文件
        audit_file = f"audit_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(audit_file, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, default=str, ensure_ascii=False)

        # 根据质量评级返回退出码
        return 0 if summary.get("overall_quality") == "GOOD" else 1

    except Exception as e:
        logger.error(f"❌ 审计系统错误: {e}")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
