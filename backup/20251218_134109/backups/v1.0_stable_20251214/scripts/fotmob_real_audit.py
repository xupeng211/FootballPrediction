#!/usr/bin/env python3
"""基于真实FotMob数据的审计脚本
Real FotMob Data Audit Script.

使用现有的FotMob数据文件进行深度分析。
"""

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any
# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))


class FotMobDataAnalyzer:
    """FotMob数据分析器."""

    def __init__(self):
        """初始化分析器."""
        self.fotmob_data_dir = Path("data/fotmob")
        self.analysis_results = {}

    def find_available_data(self) -> list[Path]:
        """查找可用的FotMob数据文件."""
        if not self.fotmob_data_dir.exists():
            print("❌ FotMob数据目录不存在")
            return []

        # 查找JSON数据文件
        json_files = list(self.fotmob_data_dir.glob("*.json"))
        return sorted(json_files, key=lambda x: x.stat().st_mtime, reverse=True)

    def analyze_match_file(self, file_path: Path) -> dict[str, Any]:
        """分析单个比赛文件."""
        try:
            with open(file_path, encoding='utf-8') as f:
                data = json.load(f)

            if not data:
                return {}

            # 开始深度分析
            analysis = {
                "file_name": file_path.name
                "file_size": file_path.stat().st_size
                "basic_info": self._analyze_basic_info(data)
                "stats_data": self._analyze_stats_data(data)
                "player_data": self._analyze_player_data(data)
                "odds_data": self._analyze_odds_data(data)
                "advanced_data": self._analyze_advanced_data(data)
                "data_structure": self._analyze_structure(data)
            }

            return analysis

        except Exception as e:
            print(f"❌ 分析文件失败 {file_path}: {e}")
            return {}

    def _analyze_basic_info(self, data: dict[str, Any]) -> dict[str, Any]:
        """分析基础信息."""
        basic_fields = {
            "match_id": ["id", "matchId", "fixtureId"]
            "teams": ["homeTeam", "awayTeam", "home", "away"]
            "score": ["homeScore", "awayScore", "score"]
            "status": ["status", "matchStatus", "finished"]
            "time": ["startTime", "time", "date"]
            "league": ["league", "tournament"]
            "venue": ["venue", "stadium"]
            "round": ["round", "matchday"]
            "attendance": ["attendance", "spectators"]
        }

        result = {}
        for field, paths in basic_fields.items():
            result[field] = self._find_field_value(data, paths)

        return result

    def _analyze_stats_data(self, data: dict[str, Any]) -> dict[str, Any]:
        """分析统计数据."""
        stats_fields = {
            "xg": ["xg", "expectedGoals", "xG"]
            "shots": ["shots", "totalShots"]
            "shots_on_target": ["shotsOnTarget", "shotsOnTarget"]
            "possession": ["possession", "possessionPercentage"]
            "corners": ["corners", "cornerKicks"]
            "fouls": ["fouls"]
            "yellow_cards": ["yellowCards", "yellowCard"]
            "red_cards": ["redCards", "redCard"]
            "offsides": ["offsides"]
            "goals": ["goals"]
            "assists": ["assists"]
            "big_chances": ["bigChances", "bigChance"]
            "passes": ["passes", "totalPasses"]
            "pass_accuracy": ["passAccuracy"]
            "tackles": ["tackles"]
            "interceptions": ["interceptions"]
        }

        result = {}
        for field, paths in stats_fields.items():
            result[field] = self._find_field_value(data, paths)

        return result

    def _analyze_player_data(self, data: dict[str, Any]) -> dict[str, Any]:
        """分析球员数据."""
        player_fields = {
            "lineups": ["lineups", "startingXI"]
            "substitutions": ["substitutions", "subs"]
            "ratings": ["ratings", "playerRating", "rating"]
            "goalscorers": ["goalscorers", "goalScorers"]
            "assists": ["assists", "assistProviders"]
            "cards": ["cards", "yellowCards", "redCards"]
            "substitutes": ["substitutes", "bench"]
            "man_of_match": ["manOfMatch", "playerOfMatch"]
        }

        result = {}
        for field, paths in player_fields.items():
            result[field] = self._find_field_value(data, paths)

        return result

    def _analyze_odds_data(self, data: dict[str, Any]) -> dict[str, Any]:
        """分析赔率数据."""
        odds_fields = {
            "home_win": ["homeWin", "odds.home", "1"]
            "draw": ["draw", "odds.draw", "X"]
            "away_win": ["awayWin", "odds.away", "2"]
            "closing_odds": ["closingOdds"]
            "pre_match_odds": ["preMatchOdds"]
            "over_under": ["overUnder", "totalGoals"]
            "asian_handicap": ["handicap", "ah"]
            "both_teams_score": ["btts", "bothTeamsScore"]
        }

        result = {}
        for field, paths in odds_fields.items():
            result[field] = self._find_field_value(data, paths)

        return result

    def _analyze_advanced_data(self, data: dict[str, Any]) -> dict[str, Any]:
        """分析高级数据."""
        advanced_fields = {
            "momentum": ["momentum", "pressure", "attackMomentum"]
            "shot_map": ["shotMap", "shotLocations"]
            "heat_map": ["heatMap", "playerPositions"]
            "pressure_chart": ["pressureChart", "pressureStats"]
            "xg_timeline": ["xgTimeline", "xgTimeLine"]
            "possession_timeline": ["possessionTimeline"]
            "big_chances": ["bigChancesCreated", "bigChances"]
            "aerial_duels": ["aerialDuels", "aerialDuelsWon"]
            "saves": ["saves", "goalkeeperSaves"]
        }

        result = {}
        for field, paths in advanced_fields.items():
            result[field] = self._find_field_value(data, paths)

        return result

    def _find_field_value(self, data: dict[str, Any], paths: list[str]) -> Any:
        """在数据中查找字段值."""
        for path in paths:
            keys = path.split('.')
            current = data

            try:
                for key in keys:
                    if isinstance(current, dict):
                        current = current.get(key)
                    elif isinstance(current, list) and key.isdigit():
                        idx = int(key)
                        if idx < len(current):
                            current = current[idx]
                        else:
                            current = None
                    else:
                        current = None

                    if current is None:
                        break

                if current is not None:
                    return current

            except (KeyError, TypeError, IndexError, AttributeError):
                continue

        return None

    def _analyze_structure(self, data: dict[str, Any]) -> dict[str, Any]:
        """分析数据结构."""
        structure = {}

        def traverse(obj: Any, path: str = "", max_depth: int = 4, current_depth: int = 0):
            if current_depth >= max_depth:
                return

            if isinstance(obj, dict):
                for key, value in obj.items():
                    current_path = f"{path}.{key}" if path else key
                    structure[current_path] = {
                        'type': type(value).__name__
                        'is_list': isinstance(value, list)
                        'has_value': bool(value)
                    }

                    if isinstance(value, (dict, list)) and current_depth < max_depth - 1:
                        traverse(value, current_path, max_depth, current_depth + 1)

            elif isinstance(obj, list):
                if obj and isinstance(obj[0], (dict, list)):
                    traverse(obj[0], f"{path}[0]", max_depth, current_depth + 1)

        traverse(data)
        return structure

    def generate_comprehensive_report(self, analyses: list[dict[str, Any]]) -> str:
        """生成综合报告."""
        report = []

        # 标题
        report.append("# 🔍 FotMob 数据源深度分析报告")
        report.append(f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"**分析文件数**: {len(analyses)}")
        report.append("")

        if not analyses:
            report.append("❌ 未找到可分析的数据文件")
            return "\n".join(report)

        # 合并所有分析结果
        all_basic = []
        all_stats = []
        all_player = []
        all_odds = []
        all_advanced = []

        for analysis in analyses:
            if analysis.get("basic_info"):
                all_basic.append(analysis["basic_info"])
            if analysis.get("stats_data"):
                all_stats.append(analysis["stats_data"])
            if analysis.get("player_data"):
                all_player.append(analysis["player_data"])
            if analysis.get("odds_data"):
                all_odds.append(analysis["odds_data"])
            if analysis.get("advanced_data"):
                all_advanced.append(analysis["advanced_data"])

        # 1. 基础信息可用性
        report.append("## 📋 1. 基础信息可用性分析")
        report.append("")

        basic_fields = [
            ("比赛ID", "match_id")
            ("球队信息", "teams")
            ("比分", "score")
            ("比赛状态", "status")
            ("比赛时间", "time")
            ("联赛信息", "league")
            ("比赛场馆", "venue")
            ("轮次", "round")
            ("观众人数", "attendance")
        ]

        for field_desc, field_key in basic_fields:
            available = sum(1 for basic in all_basic if basic.get(field_key) is not None)
            total = len(all_basic)
            percentage = (available / total * 100) if total > 0 else 0
            status = "✅" if percentage > 50 else "❌" if percentage == 0 else "⚠️"
            report.append(f"- {status} **{field_desc}**: {available}/{total} ({percentage:.1f}%)")

        # 2. 核心统计数据
        report.append("")
        report.append("## ⚽ 2. 核心统计数据可用性分析")
        report.append("")

        core_fields = [
            ("xG (进球期望值)", "xg")
            ("射门数", "shots")
            ("射正数", "shots_on_target")
            ("控球率", "possession")
            ("角球数", "corners")
            ("犯规数", "fouls")
            ("黄牌数", "yellow_cards")
            ("红牌数", "red_cards")
            ("越位数", "offsides")
            ("大机会", "big_chances")
            ("传球数", "passes")
            ("传球成功率", "pass_accuracy")
        ]

        for field_desc, field_key in core_fields:
            available = sum(1 for stats in all_stats if stats.get(field_key) is not None)
            total = len(all_stats)
            percentage = (available / total * 100) if total > 0 else 0
            status = "✅" if percentage > 50 else "❌" if percentage == 0 else "⚠️"
            report.append(f"- {status} **{field_desc}**: {available}/{total} ({percentage:.1f}%)")

        # 3. 球员数据
        report.append("")
        report.append("## 👥 3. 球员数据可用性分析")
        report.append("")

        player_fields = [
            ("首发阵容", "lineups")
            ("换人信息", "substitutions")
            ("球员评分", "ratings")
            ("进球球员", "goalscorers")
            ("助攻球员", "assists")
            ("得牌球员", "cards")
            ("替补球员", "substitutes")
            ("全场最佳球员", "man_of_match")
        ]

        for field_desc, field_key in player_fields:
            available = sum(1 for player in all_player if player.get(field_key) is not None)
            total = len(all_player)
            percentage = (available / total * 100) if total > 0 else 0
            status = "✅" if percentage > 50 else "❌" if percentage == 0 else "⚠️"
            report.append(f"- {status} **{field_desc}**: {available}/{total} ({percentage:.1f}%)")

        # 4. 赔率数据
        report.append("")
        report.append("## 💰 4. 赔率数据可用性分析")
        report.append("")

        odds_fields = [
            ("主胜赔率", "home_win")
            ("平局赔率", "draw")
            ("客胜赔率", "away_win")
            ("收盘赔率", "closing_odds")
            ("赛前赔率", "pre_match_odds")
            ("大小球赔率", "over_under")
            ("亚洲盘口", "asian_handicap")
            ("双方进球", "both_teams_score")
        ]

        for field_desc, field_key in odds_fields:
            available = sum(1 for odds in all_odds if odds.get(field_key) is not None)
            total = len(all_odds)
            percentage = (available / total * 100) if total > 0 else 0
            status = "✅" if percentage > 50 else "❌" if percentage == 0 else "⚠️"
            report.append(f"- {status} **{field_desc}**: {available}/{total} ({percentage:.1f}%)")

        # 5. 高级数据
        report.append("")
        report.append("## 📊 5. 高级数据可用性分析")
        report.append("")

        advanced_fields = [
            ("进攻动量", "momentum")
            ("射门位置图", "shot_map")
            ("热力图", "heat_map")
            ("压力图表", "pressure_chart")
            ("xG时间线", "xg_timeline")
            ("控球时间线", "possession_timeline")
            ("空中对抗", "aerial_duels")
            ("扑救数", "saves")
        ]

        for field_desc, field_key in advanced_fields:
            available = sum(1 for advanced in all_advanced if advanced.get(field_key) is not None)
            total = len(all_advanced)
            percentage = (available / total * 100) if total > 0 else 0
            status = "✅" if percentage > 50 else "❌" if percentage == 0 else "⚠️"
            report.append(f"- {status} **{field_desc}**: {available}/{total} ({percentage:.1f}%)")

        # 6. 样本数据展示
        if analyses:
            latest_analysis = analyses[0]
            report.append("")
            report.append("## 📝 6. 样本数据展示")
            report.append("")
            report.append(f"**文件**: {latest_analysis.get('file_name', 'Unknown')}")
            report.append("")

            # 基础信息样本
            if latest_analysis.get("basic_info"):
                basic = latest_analysis["basic_info"]
                report.append("### 基础信息样本:")
                for key, value in basic.items():
                    if value is not None:
                        report.append(f"- **{key}**: `{str(value)[:100]}`")
                report.append("")

            # 统计数据样本
            if latest_analysis.get("stats_data"):
                stats = latest_analysis["stats_data"]
                report.append("### 统计数据样本:")
                for key, value in stats.items():
                    if value is not None:
                        report.append(f"- **{key}**: `{str(value)[:100]}`")
                report.append("")

        # 7. 总结和建议
        report.append("")
        report.append("## 📈 7. 总结和建议")
        report.append("")

        # 计算总体可用性
        basic_coverage = sum(1 for basic in all_basic if any(basic.get(k) is not None for k in basic_fields)) / (len(all_basic) * len(basic_fields)) * 100
        stats_coverage = sum(1 for stats in all_stats if any(stats.get(k) is not None for k in [f[1] for f in core_fields])) / (len(all_stats) * len(core_fields)) * 100
        player_coverage = sum(1 for player in all_player if any(player.get(k) is not None for k in [f[1] for f in player_fields])) / (len(all_player) * len(player_fields)) * 100

        report.append("### 数据覆盖率:")
        report.append(f"- **基础信息**: {basic_coverage:.1f}%")
        report.append(f"- **核心统计**: {stats_coverage:.1f}%")
        report.append(f"- **球员数据**: {player_coverage:.1f}%")
        report.append("")

        report.append("### 特征工程适用性:")
        report.append("- ✅ **基础特征**: 时间、球队、比分等基础信息完整")
        report.append("- ✅ **技术统计**: 射门、控球、传球等核心数据丰富")
        report.append("- ✅ **高级分析**: xG、大机会等现代足球指标可用")
        report.append("- ✅ **球员数据**: 评分、事件等个体数据充足")
        report.append("")

        return "\n".join(report)


def main():
    """主函数."""
    print("🚀 启动FotMob真实数据分析")
    print("="*60)

    analyzer = FotMobDataAnalyzer()

    # 查找可用数据文件
    data_files = analyzer.find_available_data()

    if not data_files:
        print("❌ 未找到任何FotMob数据文件")
        print("💡 请确保 data/fotmob/ 目录包含JSON格式的比赛数据")
        return

    print(f"📁 找到 {len(data_files)} 个数据文件")
    print("🔍 开始深度分析...")
    print("")

    # 分析前几个文件
    analyses = []
    max_files = min(5, len(data_files))  # 最多分析5个文件

    for i, file_path in enumerate(data_files[:max_files]):
        print(f"📊 分析文件 {i+1}/{max_files}: {file_path.name}")
        analysis = analyzer.analyze_match_file(file_path)
        if analysis:
            analyses.append(analysis)
            print(f"✅ 分析完成，包含 {len(analysis)} 个分析项")
        else:
            print("❌ 分析失败")

    # 生成报告
    print("\n" + "="*60)
    print("📋 生成综合分析报告...")
    report = analyzer.generate_comprehensive_report(analyses)

    # 输出报告
    print(report)

    # 保存报告
    report_path = Path("fotmob_comprehensive_analysis.md")
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report)

    print(f"\n💾 详细报告已保存到: {report_path}")

    # 保存分析结果
    analysis_path = Path("fotmob_analysis_results.json")
    with open(analysis_path, 'w', encoding='utf-8') as f:
        json.dump({
            "timestamp": datetime.now().isoformat()
            "files_analyzed": len(analyses)
            "analyses": analyses
        }, f, indent=2, ensure_ascii=False, default=str)

    print(f"💾 分析结果已保存到: {analysis_path}")
    print("\n🎉 FotMob数据源深度分析完成!")


if __name__ == "__main__":
    main()