#!/usr/bin/env python3
"""
FBref数据质检脚本
Data QA Specialist: 数据深度验证专家

Purpose: 检查FBref数据采集深度，确保Match Report链接完整性
"""

import asyncio
import sys
import json
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

logging.basicConfig(
    level=logging.INFO,
    format="🔍 %(asctime)s [%(levelname)8s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


class FBrefDataQA:
    """FBref数据质检员"""

    def __init__(self):
        self.database_url = "postgresql://postgres:postgres-dev-password@localhost:5432/football_prediction"
        self.engine = None
        self.conn = None

    def connect_database(self):
        """连接数据库"""
        try:
            from sqlalchemy import create_engine, text

            self.engine = create_engine(self.database_url)
            self.conn = self.engine.connect()
            self.text = text  # 保存text函数
            logger.info("✅ 数据库连接成功")
            return True
        except Exception as e:
            logger.error(f"❌ 数据库连接失败: {e}")
            return False

    def get_latest_fbref_match(self) -> Optional[dict[str, Any]]:
        """获取最新入库的FBref比赛数据"""
        try:
            query = self.text(
                """
                SELECT m.id, m.match_date, m.home_score, m.away_score,
                       m.stats, m.match_metadata, m.data_source, m.season,
                       m.created_at,
                       ht.name as home_team, at.name as away_team
                FROM matches m
                LEFT JOIN teams ht ON m.home_team_id = ht.id
                LEFT JOIN teams at ON m.away_team_id = at.id
                WHERE m.data_source = 'fbref'
                ORDER BY m.created_at DESC
                LIMIT 1
            """
            )

            result = self.conn.execute(query)
            row = result.fetchone()

            if row:
                return {
                    "id": row[0],
                    "match_date": row[1],
                    "home_score": row[2],
                    "away_score": row[3],
                    "stats": row[4],
                    "match_metadata": row[5],
                    "data_source": row[6],
                    "season": row[7],
                    "created_at": row[8],
                    "home_team": row[9],
                    "away_team": row[10],
                }
            return None

        except Exception as e:
            logger.error(f"❌ 查询最新比赛失败: {e}")
            return None

    def analyze_xg_data(self, stats_data: dict) -> dict[str, Any]:
        """分析xG数据质量"""
        if not stats_data:
            return {"status": "missing", "details": "stats字段为空"}

        xg_analysis = {
            "status": "available",
            "has_xg_field": "xg" in stats_data,
            "xg_keys": [],
            "xg_content": {},
        }

        # 检查xg字段
        if "xg" in stats_data:
            xg_data = stats_data["xg"]
            xg_analysis["xg_content"] = xg_data
            xg_analysis["xg_keys"] = (
                list(xg_data.keys()) if isinstance(xg_data, dict) else []
            )

            # 检查是否有主客队xG
            has_home_xg = any(
                "home_xg" in str(key).lower() for key in xg_analysis["xg_keys"]
            )
            has_away_xg = any(
                "away_xg" in str(key).lower() for key in xg_analysis["xg_keys"]
            )
            xg_analysis["has_home_away_xg"] = has_home_xg and has_away_xg

            # 验证xG数据类型
            xg_analysis["xg_types"] = {}
            for key, value in xg_data.items():
                xg_analysis["xg_types"][key] = type(value).__name__

        # 检查是否有其他xG相关字段
        other_xg_keys = [key for key in stats_data.keys() if "xg" in key.lower()]
        xg_analysis["all_xg_keys"] = other_xg_keys

        return xg_analysis

    def analyze_raw_data_depth(self, raw_data: dict) -> dict[str, Any]:
        """分析原始数据深度，特别关注Match Report链接"""
        if not raw_data:
            return {"status": "missing", "details": "raw_data字段为空"}

        depth_analysis = {
            "status": "available",
            "total_fields": len(raw_data),
            "field_names": list(raw_data.keys()),
            "has_url_fields": [],
            "url_content": {},
            "potential_match_report_urls": [],
        }

        # 检查URL相关字段
        url_keywords = ["url", "link", "report", "match", "detail", "stats"]
        for field_name, field_value in raw_data.items():
            if any(keyword in field_name.lower() for keyword in url_keywords):
                depth_analysis["has_url_fields"].append(field_name)
                depth_analysis["url_content"][field_name] = str(field_value)

                # 特别检查是否是Match Report链接
                if "match" in field_name.lower() or "report" in field_name.lower():
                    depth_analysis["potential_match_report_urls"].append(
                        {
                            "field": field_name,
                            "value": str(field_value),
                            "contains_fbref": "fbref" in str(field_value).lower(),
                        }
                    )

        # 检查是否有列名包含相关链接信息
        link_column_names = [
            col
            for col in depth_analysis["field_names"]
            if any(
                keyword in col.lower() for keyword in url_keywords + ["href", "link"]
            )
        ]
        depth_analysis["link_column_names"] = link_column_names

        return depth_analysis

    def analyze_metadata_depth(self, metadata: dict) -> dict[str, Any]:
        """分析metadata深度"""
        if not metadata:
            return {"status": "missing", "details": "metadata字段为空"}

        meta_analysis = {
            "status": "available",
            "total_fields": len(metadata),
            "field_names": list(metadata.keys()),
            "has_urls": False,
            "url_fields": {},
            "potential_match_report_urls": [],
        }

        # 检查metadata中的URL
        for field_name, field_value in metadata.items():
            if isinstance(field_value, str) and (
                "http" in field_value or "fbref" in field_value
            ):
                meta_analysis["has_urls"] = True
                meta_analysis["url_fields"][field_name] = field_value

                if "match" in field_name.lower() or "report" in field_name.lower():
                    meta_analysis["potential_match_report_urls"].append(
                        {"field": field_name, "value": field_value}
                    )

        return meta_analysis

    def generate_qa_report(self, match_data: dict) -> str:
        """生成数据质检报告"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        report = f"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                       FBref数据质量质检报告                              ║
║                     Data QA Specialist: 数据深度验证                      ║
╚════════════════════════════════════════════════════════════════════════════╝

🕐 质检时间: {timestamp}
🎯 检查对象: 最新入库的FBref比赛数据

┌─ 📊 基础比赛信息 ───────────────────────────────────────────────────────────────┐"""

        # 基础信息展示
        report += f"""
│ 比赛ID: {match_data['id']}
│ 主队: {match_data['home_team']}
│ 客队: {match_data['away_team']}"""

        if (
            match_data["home_score"] is not None
            and match_data["away_score"] is not None
        ):
            report += f"""
│ 比分: {match_data['home_score']}-{match_data['away_score']}"""
        else:
            report += """
│ 比分: 未开始"""

        report += f"""
│ 比赛日期: {match_data['match_date']}
│ 赛季: {match_data['season']}
│ 数据来源: {match_data['data_source']}
│ 入库时间: {match_data['created_at']}"""

        # xG数据分析
        xg_analysis = self.analyze_xg_data(match_data["stats"])
        report += """
└────────────────────────────────────────────────────────────────────────────────────┘

┌─ 📈 xG数据深度分析 ───────────────────────────────────────────────────────────────┐"""

        if xg_analysis["status"] == "available":
            report += f"""
│ xG数据状态: ✅ 存在
│ xG主字段: {'存在' if xg_analysis['has_xg_field'] else '缺失'}
│ xG完整度: {'完整' if xg_analysis.get('has_home_away_xg') else '部分'}"""

            if xg_analysis["xg_keys"]:
                report += f"""
│ xG数据字段: {', '.join(xg_analysis['xg_keys'][:5])}"""

                # 显示xG数据类型
                for key, value in xg_analysis["xg_types"].items():
                    report += f"""
│   {key}: {value}"""

            if "all_xg_keys" in xg_analysis and xg_analysis["all_xg_keys"]:
                report += f"""
│ 所有xG相关字段: {', '.join(xg_analysis['all_xg_keys'])}"""

        else:
            report += f"""
│ xG数据状态: ❌ 缺失
│ 详情: {xg_analysis.get('details', '未知错误')}"""

        # 原始数据深度分析
        stats_data = match_data.get("stats", {})
        raw_data = (
            stats_data.get("raw_data", {}) if isinstance(stats_data, dict) else {}
        )
        metadata = match_data.get("match_metadata", {})

        raw_analysis = self.analyze_raw_data_depth(raw_data)
        report += """
└──────────────────────────────────────────────────────────────────────────────────────┘

┌─ 🔗 链接深度分析 ───────────────────────────────────────────────────────────────┐"""

        if raw_analysis["status"] == "available":
            report += f"""
│ 原始数据字段数: {raw_analysis['total_fields']}
│ URL相关字段数: {len(raw_analysis['has_url_fields'])}"""

            if raw_analysis["has_url_fields"]:
                report += f"""
│ URL字段列表: {', '.join(raw_analysis['has_url_fields'])}"""

                for field, value in raw_analysis["url_content"].items():
                    preview = value[:100] + "..." if len(value) > 100 else value
                    report += f"""
│   {field}: {preview}"""

            if raw_analysis["potential_match_report_urls"]:
                report += f"""
│ ⚠️  发现可能的Match Report URL: {len(raw_analysis['potential_match_report_urls'])} 个"""

                for url_info in raw_analysis["potential_match_report_urls"][:3]:
                    fbref_marker = "✅" if url_info["contains_fbref"] else "❌"
                    report += f"""
│   {fbref_marker} {url_info['field']}: {url_info['value'][:80]}..."""

            if raw_analysis["link_column_names"]:
                report += f"""
│ 可能的链接列名: {', '.join(raw_analysis['link_column_names'])}"""

            if (
                not raw_analysis["has_url_fields"]
                and not raw_analysis["link_column_names"]
            ):
                report += """
│ 🔍 建议检查字段: date, score, home, away 之外的其他列"""
        else:
            report += f"""
│ 原始数据状态: ❌ 缺失
│ 详情: {raw_analysis.get('details', '未知错误')}"""

        # metadata深度分析
        meta_analysis = self.analyze_metadata_depth(metadata)
        report += """
└──────────────────────────────────────────────────────────────────────────────────────┘

┌─ 📋 Metadata深度分析 ────────────────────────────────────────────────────────────┐"""

        if meta_analysis["status"] == "available":
            report += f"""
│ Metadata字段数: {meta_analysis['total_fields']}
│ 包含URL: {'是' if meta_analysis['has_urls'] else '否'}"""

            if meta_analysis["has_urls"]:
                report += f"""
│ URL字段数: {len(meta_analysis['url_fields'])}"""

                for field, value in meta_analysis["url_fields"].items():
                    preview = value[:80] + "..." if len(value) > 80 else value
                    report += f"""
│   {field}: {preview}"""

            if meta_analysis["potential_match_report_urls"]:
                report += f"""
│ ⚠️  发现可能的Match Report URL: {len(meta_analysis['potential_match_report_urls'])} 个"""

        else:
            report += f"""
│ Metadata状态: ❌ 缺失
│ 详情: {meta_analysis.get('details', '未知错误')}"""

        # 生成建议
        report += """
└──────────────────────────────────────────────────────────────────────────────────────┘

┌─ 🎯 质检结论与建议 ────────────────────────────────────────────────────────────────┐"""

        conclusions = []
        recommendations = []

        # xG数据评估
        if xg_analysis["status"] == "available":
            if xg_analysis.get("has_home_away_xg"):
                conclusions.append("✅ xG数据完整性高")
            else:
                conclusions.append("⚠️ xG数据部分完整")
                recommendations.append("🔧 建议补充xG数据提取逻辑")
        else:
            conclusions.append("❌ xG数据缺失")
            recommendations.append("🚨 立即修复xG数据采集")

        # 深度链接评估
        has_match_report_urls = (
            len(raw_analysis.get("potential_match_report_urls", [])) > 0
            or len(meta_analysis.get("potential_match_report_urls", [])) > 0
        )

        if has_match_report_urls:
            conclusions.append("✅ 发现Match Report链接")
            recommendations.append("🎉 可基于这些链接进行深度采集")
        else:
            conclusions.append("❌ 未发现Match Report链接")
            recommendations.append("⚠️ **重大风险**: 需要立即修复采集器")
            recommendations.append("🔧 建议添加Match Report字段提取和存储")
            recommendations.append("🔗 热修复方案: 修改_clean_schedule_data方法")

        # 数据完整性评估
        if raw_analysis["total_fields"] >= 10:
            conclusions.append("✅ 原始数据维度丰富")
        else:
            conclusions.append("⚠️ 原始数据维度有限")
            recommendations.append("📊 建议增加更多字段采集")

        report += f"│ 质检结论: {'; '.join(conclusions)}\n│"

        for rec in recommendations:
            report += f"│ {rec}\n"

        report += f"""└──────────────────────────────────────────────────────────────────────────────────────┘

📊质检完成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
🔄建议下次质检: {(datetime.now() + timedelta(hours=6)).strftime('%Y-%m-%d %H:%M:%S')}
"""

        return report

    def run_quality_check(self) -> bool:
        """运行完整的数据质检"""
        logger.info("🔍 开始FBref数据质量质检")

        if not self.connect_database():
            logger.error("💥 无法连接数据库，质检失败")
            return False

        # 获取最新FBref比赛数据
        match_data = self.get_latest_fbref_match()

        if not match_data:
            logger.error("💥 数据库中无FBref比赛数据")
            return False

        logger.info(
            f"📊 检查比赛: {match_data['home_team']} vs {match_data['away_team']}"
        )

        # 生成质检报告
        report = self.generate_qa_report(match_data)
        print(report)

        # 保存报告
        report_file = (
            Path(__file__).parent
            / "logs"
            / f'fbref_qa_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.txt'
        )
        with open(report_file, "w", encoding="utf-8") as f:
            f.write(report)

        logger.info(f"📋 质检报告已保存: {report_file}")

        # 简单的健康评分
        stats_data = match_data.get("stats", {})
        raw_data = (
            stats_data.get("raw_data", {}) if isinstance(stats_data, dict) else {}
        )

        has_xg = "xg" in stats_data
        has_urls = any(
            "url" in str(key).lower() or "link" in str(key).lower()
            for key in raw_data.keys()
        )

        if has_xg and has_urls:
            logger.info("🎉 数据质量评估: 优秀 (A+)")
            return True
        elif has_xg or has_urls:
            logger.info("📈 数据质量评估: 良好 (B)")
            return True
        else:
            logger.warning("⚠️ 数据质量评估: 需要改进 (C)")
            return False

    def close_connection(self):
        """关闭数据库连接"""
        if self.conn:
            self.conn.close()
            logger.info("✅ 数据库连接已关闭")
        if self.engine:
            self.engine.dispose()
            logger.info("✅ 数据库引擎已关闭")


async def main():
    """主函数"""
    qa = FBrefDataQA()

    try:
        success = qa.run_quality_check()

        logger.info(f"🎯 质检完成: {'成功' if success else '需要改进'}")
        return 0 if success else 1

    except Exception as e:
        logger.error(f"💥 质检过程异常: {e}")
        import traceback

        traceback.print_exc()
        return 1
    finally:
        qa.close_connection()


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
