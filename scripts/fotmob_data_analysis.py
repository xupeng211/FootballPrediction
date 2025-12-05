#!/usr/bin/env python3
"""FotMob真实数据深度分析
Real FotMob Data Deep Analysis.

基于现有的FotMob比赛数据文件进行深度分析，生成数据字典报告。
"""

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))


class FotMobRealDataAnalyzer:
    """FotMob真实数据分析器."""

    def __init__(self):
        """初始化分析器."""
        self.data_dir = Path("data/fotmob/historical")
        self.analysis_results = {}

    def load_fotmob_data(self) -> list[dict[str, Any]]:
        """加载FotMob数据文件."""
        data_files = list(self.data_dir.glob("fotmob_matches_*.json"))
        all_matches = []

        for file_path in sorted(data_files):
            print(f"📁 加载文件: {file_path.name}")
            try:
                with open(file_path, encoding='utf-8') as f:
                    data = json.load(f)

                if 'matches' in data:
                    matches = data['matches']
                    print(f"  ✅ 包含 {len(matches)} 场比赛")
                    all_matches.extend(matches)

            except Exception as e:
                print(f"  ❌ 加载失败: {e}")

        return all_matches

    def analyze_match_structure(self, matches: list[dict[str, Any]]) -> dict[str, Any]:
        """分析比赛数据结构."""
        if not matches:
            return {}

        # 分析单个比赛的结构
        sample_match = matches[0]

        structure = {
            "basic_fields": {},
            "numeric_fields": {},
            "categorical_fields": {},
            "data_completeness": {},
            "sample_values": {}
        }

        # 分析每个字段
        for field_name, field_value in sample_match.items():
            field_type = type(field_value).__name__

            structure["basic_fields"][field_name] = {
                "type": field_type,
                "description": self._get_field_description(field_name)
            }

            # 检查数值字段
            if isinstance(field_value, (int, float)):
                structure["numeric_fields"][field_name] = field_type
            elif isinstance(field_value, str):
                # 尝试判断是否为类别字段
                unique_values = set()
                for match in matches[:100]:  # 检查前100个比赛
                    val = match.get(field_name)
                    if val is not None:
                        unique_values.add(str(val))
                    if len(unique_values) > 20:  # 如果唯一值太多，认为是文本字段
                        break

                if len(unique_values) <= 20:
                    structure["categorical_fields"][field_name] = {
                        "unique_values": len(unique_values),
                        "values": sorted(list(unique_values))[:10]  # 只显示前10个值
                    }

            # 检查数据完整性
            non_null_count = sum(1 for match in matches if match.get(field_name) is not None)
            structure["data_completeness"][field_name] = {
                "available": non_null_count,
                "total": len(matches),
                "percentage": (non_null_count / len(matches)) * 100
            }

            # 保存样本值
            structure["sample_values"][field_name] = str(field_value)[:100]

        return structure

    def _get_field_description(self, field_name: str) -> str:
        """获取字段描述."""
        descriptions = {
            "match_id": "比赛唯一标识符",
            "league_id": "联赛唯一标识符",
            "league_name": "联赛名称",
            "home_team_id": "主队唯一标识符",
            "home_team_name": "主队名称",
            "away_team_id": "客队唯一标识符",
            "away_team_name": "客队名称",
            "home_score": "主队得分",
            "away_score": "客队得分",
            "status_id": "比赛状态ID",
            "status": "比赛状态（如FT-全场结束）",
            "finished": "比赛是否已结束",
            "started": "比赛是否已开始",
            "kickoff_time": "开球时间（本地时间）",
            "utc_time": "开球时间（UTC时间）",
        }

        return descriptions.get(field_name, "未知字段")

    def analyze_advanced_features(self, matches: list[dict[str, Any]]) -> dict[str, Any]:
        """分析高级特征的可能性."""
        features = {
            "basic_features": [],
            "derived_features": [],
            "team_strength_features": [],
            "time_features": [],
            "league_features": []
        }

        # 基础特征
        basic_fields = [
            "home_team_name", "away_team_name", "home_score", "away_score",
            "status", "finished", "started", "kickoff_time", "utc_time",
            "league_name"
        ]

        for field in basic_fields:
            if any(match.get(field) is not None for match in matches):
                features["basic_features"].append(field)

        # 可派生特征
        features["derived_features"] = [
            "goal_difference",  # 比分差
            "total_goals",      # 总进球数
            "match_duration",    # 比赛时长
            "is_draw",         # 是否平局
            "home_win",         # 主队是否获胜
            "away_win",         # 客队是否获胜
            "scoring_match",    # 是否有进球
        ]

        # 球队实力特征（需要历史数据）
        features["team_strength_features"] = [
            "team_form_recent",      # 最近状态
            "head_to_head",         # 历史交锋
            "home_advantage",       # 主场优势
            "team_ranking",         # 球队排名
            "points_per_game",      # 场均积分
        ]

        # 时间特征
        features["time_features"] = [
            "day_of_week",          # 星期几
            "month",                # 月份
            "season_stage",         # 赛季阶段
            "time_slot",            # 时间段
            "is_weekend",           # 是否周末
        ]

        # 联赛特征
        features["league_features"] = [
            "league_importance",    # 联赛重要性
            "derby_match",          # 德比战
            "cup_match",            # 杯赛
            "international_match",  # 国际比赛
        ]

        return features

    def generate_comprehensive_report(self, matches: list[dict[str, Any]], structure: dict[str, Any], features: dict[str, Any]) -> str:
        """生成综合报告."""
        report = []

        # 标题
        report.append("# 🔍 FotMob 数据源深度分析报告")
        report.append(f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"**分析比赛数**: {len(matches)}")
        report.append("")

        if not matches:
            report.append("❌ 未找到任何比赛数据")
            return "\n".join(report)

        # 1. 数据概览
        report.append("## 📊 1. 数据概览")
        report.append("")

        # 统计各联赛比赛数量
        league_stats = {}
        for match in matches:
            league = match.get("league_name", "Unknown")
            league_stats[league] = league_stats.get(league, 0) + 1

        report.append("### 联赛分布:")
        for league, count in sorted(league_stats.items(), key=lambda x: x[1], reverse=True):
            report.append(f"- **{league}**: {count} 场比赛")
        report.append("")

        # 统计比赛状态
        status_stats = {}
        for match in matches:
            status = match.get("status", "Unknown")
            status_stats[status] = status_stats.get(status, 0) + 1

        report.append("### 比赛状态分布:")
        for status, count in status_stats.items():
            report.append(f"- **{status}**: {count} 场比赛")
        report.append("")

        # 2. 基础信息字段分析
        report.append("## 📋 2. 基础信息字段分析")
        report.append("")

        basic_info_fields = [
            ("比赛ID", "match_id"),
            ("主队信息", "home_team_name", "home_team_id"),
            ("客队信息", "away_team_name", "away_team_id"),
            ("比分信息", "home_score", "away_score"),
            ("比赛状态", "status", "status_id", "finished", "started"),
            ("时间信息", "kickoff_time", "utc_time"),
            ("联赛信息", "league_name", "league_id"),
        ]

        for category, *fields in basic_info_fields:
            report.append(f"### {category}:")

            available_fields = []
            for field in fields:
                if field in structure.get("basic_fields", {}):
                    available_fields.append(field)

            if available_fields:
                for field in available_fields:
                    field_info = structure["basic_fields"][field]
                    completeness = structure["data_completeness"].get(field, {})
                    percentage = completeness.get("percentage", 0)
                    status = "✅" if percentage > 90 else "⚠️" if percentage > 50 else "❌"
                    sample = structure["sample_values"].get(field, "N/A")

                    report.append(f"- {status} **{field_info.get('description', field)}** (`{field}`)")
                    report.append(f"  - 数据完整性: {percentage:.1f}% ({completeness.get('available', 0)}/{len(matches)})")
                    report.append(f"  - 数据类型: {field_info.get('type', 'Unknown')}")
                    if sample and sample != "N/A":
                        report.append(f"  - 样例: `{sample}`")
            else:
                report.append("- ❌ 未找到相关字段")

            report.append("")

        # 3. 数据可用性评估
        report.append("## ✅ 3. 数据可用性评估")
        report.append("")

        # 基础信息
        basic_completeness = []
        basic_required = ["match_id", "home_team_name", "away_team_name", "home_score", "away_score", "status"]
        for field in basic_required:
            if field in structure.get("data_completeness", {}):
                basic_completeness.append(structure["data_completeness"][field].get("percentage", 0))

        avg_basic = sum(basic_completeness) / len(basic_completeness) if basic_completeness else 0
        report.append(f"- **基础信息**: {avg_basic:.1f}% 平均完整度")

        # 核心数据
        core_completeness = []
        core_required = ["home_score", "away_score", "status", "finished", "kickoff_time"]
        for field in core_required:
            if field in structure.get("data_completeness", {}):
                core_completeness.append(structure["data_completeness"][field].get("percentage", 0))

        avg_core = sum(core_completeness) / len(core_completeness) if core_completeness else 0
        report.append(f"- **核心数据**: {avg_core:.1f}% 平均完整度")

        # 时间数据
        time_completeness = []
        time_required = ["kickoff_time", "utc_time"]
        for field in time_required:
            if field in structure.get("data_completeness", {}):
                time_completeness.append(structure["data_completeness"][field].get("percentage", 0))

        avg_time = sum(time_completeness) / len(time_completeness) if time_completeness else 0
        report.append(f"- **时间数据**: {avg_time:.1f}% 平均完整度")
        report.append("")

        # 4. 特征工程适用性
        report.append("## 🚀 4. 特征工程适用性")
        report.append("")

        report.append("### ✅ 可直接使用的特征:")
        for feature in features.get("basic_features", []):
            desc = structure.get("basic_fields", {}).get(feature, {}).get("description", feature)
            report.append(f"- **{desc}** (`{feature}`)")

        report.append("")
        report.append("### 🔧 可派生的特征:")
        for feature in features.get("derived_features", []):
            report.append(f"- **{feature}**")

        report.append("")
        report.append("### 📈 需要额外数据的特征:")
        for feature in features.get("team_strength_features", []):
            report.append(f"- **{feature}** (需要历史数据)")

        report.append("")
        report.append("### ⏰ 时间相关特征:")
        for feature in features.get("time_features", []):
            report.append(f"- **{feature}**")

        report.append("")
        report.append("### 🏆 联赛相关特征:")
        for feature in features.get("league_features", []):
            report.append(f"- **{feature}**")

        # 5. 当前数据结构示例
        report.append("")
        report.append("## 📝 5. 当前数据结构示例")
        report.append("")

        if matches:
            sample_match = matches[0]
            report.append("```json")
            # 显示部分字段作为示例
            sample_data = {}
            important_fields = ["match_id", "league_name", "home_team_name", "away_team_name",
                               "home_score", "away_score", "status", "kickoff_time"]

            for field in important_fields:
                if field in sample_match:
                    sample_data[field] = sample_match[field]

            import json as json_module
            report.append(json_module.dumps(sample_data, indent=2, ensure_ascii=False)[:1000] + "...")
            report.append("```")
            report.append("")

        # 6. 建议和结论
        report.append("")
        report.append("## 💡 6. 建议和结论")
        report.append("")

        # 数据质量评估
        overall_quality = (avg_basic + avg_core + avg_time) / 3
        if overall_quality > 90:
            quality_level = "优秀"
        elif overall_quality > 75:
            quality_level = "良好"
        elif overall_quality > 50:
            quality_level = "一般"
        else:
            quality_level = "需要改进"

        report.append(f"### 数据质量评估: **{quality_level}** ({overall_quality:.1f}%)")
        report.append("")

        # 特征工程建议
        report.append("### 特征工程建议:")

        if avg_basic > 80:
            report.append("- ✅ **基础特征完整**: 可以直接提取球队、比分、时间等基础特征")
        else:
            report.append("- ⚠️ **基础特征不完整**: 需要补齐基础信息字段")

        if avg_core > 80:
            report.append("- ✅ **核心数据可靠**: 比赛结果和状态数据完整，适合监督学习")
        else:
            report.append("- ⚠️ **核心数据缺失**: 需要完善比赛结果数据")

        if avg_time > 80:
            report.append("- ✅ **时间特征可用**: 可提取时间序列特征和周期性模式")
        else:
            report.append("- ⚠️ **时间特征缺失**: 需要改进时间数据收集")

        # 数据增强建议
        report.append("")
        report.append("### 数据增强建议:")
        report.append("- 🔗 **增强数据采集**: 集成更多详细统计数据（xG、射门、控球率等）")
        report.append("- 📊 **历史数据**: 建立球队历史表现数据库")
        report.append("- 🔍 **实时数据**: 考虑实时赔率和技术统计数据")
        report.append("- 🏆 **标签数据**: 建立更丰富的预测目标（如半场比分、大小球等）")
        report.append("- 📍 **地理数据**: 添加地理距离、主场优势等信息")

        report.append("")
        report.append("### 技术实现建议:")
        report.append("- **数据清洗**: 建立统一的数据清洗和验证流程")
        report.append("- **特征存储**: 设计高效的特征存储和检索系统")
        report.append("- **实时更新**: 实现数据的实时更新和增量处理")
        report.append("- **质量监控**: 建立数据质量监控和报警机制")

        return "\n".join(report)


def main():
    """主函数."""
    print("🚀 启动FotMob真实数据深度分析")
    print("="*60)

    analyzer = FotMobRealDataAnalyzer()

    # 加载数据
    print("📁 加载FotMob数据文件...")
    matches = analyzer.load_fotmob_data()

    if not matches:
        print("❌ 未加载到任何比赛数据")
        return

    print(f"✅ 成功加载 {len(matches)} 场比赛数据")
    print("🔍 开始深度分析...")
    print("")

    # 分析数据结构
    print("📊 分析数据结构...")
    structure = analyzer.analyze_match_structure(matches)

    # 分析特征可能性
    print("🚀 分析特征工程可能性...")
    features = analyzer.analyze_advanced_features(matches)

    # 生成报告
    print("📋 生成分析报告...")
    report = analyzer.generate_comprehensive_report(matches, structure, features)

    # 输出报告
    print("\n" + "="*60)
    print(report)

    # 保存报告
    report_path = Path("fotmob_real_data_analysis.md")
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report)

    print(f"\n💾 详细报告已保存到: {report_path}")

    # 保存分析结果
    analysis_path = Path("fotmob_analysis_results.json")
    with open(analysis_path, 'w', encoding='utf-8') as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "total_matches": len(matches),
            "structure": structure,
            "features": features,
            "sample_matches": matches[:5]  # 保存前5个样本
        }, f, indent=2, ensure_ascii=False, default=str)

    print(f"💾 分析结果已保存到: {analysis_path}")
    print("\n🎉 FotMob真实数据深度分析完成!")


if __name__ == "__main__":
    main()
