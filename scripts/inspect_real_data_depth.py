#!/usr/bin/env python3
"""
Data Forensics Expert - Real Data Depth Inspection
数据取证专家 - V2采集器数据深度检查

Principal Data Forensics Expert: 首席数据取证专家
Purpose: 验证V2采集器实际捕获的关键数据字段
Target: xG, 赔率, 球员评分, 跑动距离等用户关注的核心数据
"""

import asyncio
import json
import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)8s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


class DataForensicsExpert:
    """数据取证专家"""

    def __init__(self):
        """初始化取证专家"""
        self.captured_data = {}
        self.inspection_results = {}

    async def capture_target_match(self) -> Optional[str]:
        """
        定点狙击：捕获昨天的五大联赛焦点战

        Returns:
            比赛数据JSON字符串
        """
        logger.info("🎯 开始定点狙击：获取昨天的五大联赛焦点战")

        try:
            from src.data.collectors.fotmob_browser import FotmobBrowserScraper

            # 计算昨天的日期
            yesterday = datetime.now() - timedelta(days=1)
            date_str = yesterday.strftime("%Y-%m-%d")
            logger.info(f"📅 目标日期: {date_str}")

            async with FotmobBrowserScraper() as scraper:
                # 1. 获取昨天的比赛列表
                logger.info("📋 获取比赛列表...")
                matches_data = await scraper.scrape_matches(date_str)

                if not matches_data or "matches" not in matches_data:
                    logger.error("❌ 未找到比赛数据")
                    return None

                matches = matches_data["matches"]
                logger.info(f"✅ 找到 {len(matches)} 场比赛")

                # 2. 寻找五大联赛的焦点战
                target_match = None
                premier_league_matches = []

                for match in matches:
                    # 寻找英超比赛
                    if match.get("league", {}).get("name") == "Premier League":
                        premier_league_matches.append(match)
                        logger.info(
                            f"🏴󐁧󐁢󐁥󐁮󐁧󐁿 找到英超比赛: {match.get('home', {}).get('name')} vs {match.get('away', {}).get('name')}"
                        )

                    # 寻找其他五大联赛
                    if match.get("league", {}).get("name") in [
                        "Premier League",
                        "La Liga",
                        "Bundesliga",
                        "Serie A",
                        "Ligue 1",
                    ]:
                        # 优先选择知名球队的比赛
                        home_name = match.get("home", {}).get("name", "").lower()
                        away_name = match.get("away", {}).get("name", "").lower()

                        top_teams = [
                            "liverpool",
                            "manchester",
                            "chelsea",
                            "arsenal",
                            "real madrid",
                            "barcelona",
                            "bayern munich",
                            "juventus",
                            "psg",
                            "milan",
                            "inter",
                        ]

                        if any(
                            team in home_name or team in away_name for team in top_teams
                        ):
                            target_match = match
                            logger.info(f"🎯 发现焦点战: {home_name} vs {away_name}")
                            break

                # 如果没找到焦点战，选择第一场英超比赛
                if not target_match and premier_league_matches:
                    target_match = premier_league_matches[0]
                    logger.info("🎯 选择首场英超比赛")

                if not target_match:
                    logger.error("❌ 未找到合适的比赛")
                    return None

                # 3. 获取比赛的详细信息
                match_id = target_match.get("id")
                match_name = f"{target_match.get('home', {}).get('name')} vs {target_match.get('away', {}).get('name')}"

                logger.info(f"🎬 开始捕获比赛详情: {match_name} (ID: {match_id})")

                # 这里我们需要重新创建一个专门的详情页采集器
                detailed_data = await self._capture_match_details(match_id, match_name)

                return detailed_data

        except Exception as e:
            logger.error(f"❌ 捕获比赛数据失败: {e}")
            return None

    async def _capture_match_details(
        self, match_id: int, match_name: str
    ) -> Optional[str]:
        """捕获比赛详情数据"""
        logger.info(f"🔍 深度取证: {match_name}")

        try:
            from src.data.collectors.fotmob_browser_v2 import FotmobBrowserScraperV2

            async with FotmobBrowserScraperV2() as scraper:
                # 捕获比赛详情页的所有数据
                logger.info("🌐 启动浏览器，拦截API调用...")

                # 导航到比赛详情页
                detail_url = f"https://www.fotmob.com/match/{match_id}"
                detailed_data = await scraper.scrape_match_details(match_id)

                if detailed_data:
                    logger.info(f"✅ 成功捕获比赛详情: {len(str(detailed_data))} 字符")
                    self.captured_data = detailed_data
                    return json.dumps(detailed_data, indent=2, ensure_ascii=False)
                else:
                    logger.error("❌ 捕获详情失败")
                    return None

        except ImportError:
            logger.warning("⚠️ FotmobBrowserScraperV2 不可用，尝试使用基础版本")
            return await self._fallback_capture(match_id, match_name)
        except Exception as e:
            logger.error(f"❌ 详情捕获异常: {e}")
            return None

    async def _fallback_capture(self, match_id: int, match_name: str) -> Optional[str]:
        """备用捕获方案"""
        logger.info("🔄 使用备用捕获方案")

        try:
            from src.data.collectors.fotmob_browser import FotmobBrowserScraper

            async with FotmobBrowserScraper() as scraper:
                # 尝试从匹配列表获取更详细信息
                yesterday = datetime.now() - timedelta(days=1)
                date_str = yesterday.strftime("%Y-%m-%d")

                matches_data = await scraper.scrape_matches(date_str)

                if matches_data and "matches" in matches_data:
                    for match in matches_data["matches"]:
                        if match.get("id") == match_id:
                            logger.info("✅ 从比赛列表找到详细信息")
                            return json.dumps(match, indent=2, ensure_ascii=False)

                return None

        except Exception as e:
            logger.error(f"❌ 备用方案也失败: {e}")
            return None

    def inspect_data_depth(self, data_str: str) -> dict[str, Any]:
        """
        深度检查数据字段

        Args:
            data_str: JSON字符串格式的比赛数据

        Returns:
            检查结果字典
        """
        if not data_str:
            return {"error": "没有数据可检查"}

        logger.info("🔍 开始深度数据取证...")

        try:
            data = json.loads(data_str)
        except json.JSONDecodeError as e:
            return {"error": f"JSON解析失败: {e}"}

        results = {
            "data_size_bytes": len(data_str.encode("utf-8")),
            "has_xG": False,
            "has_lineups": False,
            "has_ratings": False,
            "has_odds": False,
            "has_running_distance": False,
            "has_momentum": False,
            "detailed_findings": {},
            "sample_structure": {},
        }

        # 1. 检查xG数据
        logger.info("📊 检查xG数据...")
        xg_results = self._check_xg_data(data)
        results.update(xg_results)

        # 2. 检查阵容数据
        logger.info("👥 检查阵容数据...")
        lineup_results = self._check_lineup_data(data)
        results.update(lineup_results)

        # 3. 检查球员评分
        logger.info("⭐ 检查球员评分...")
        rating_results = self._check_rating_data(data)
        results.update(rating_results)

        # 4. 检查赔率数据
        logger.info("💰 检查赔率数据...")
        odds_results = self._check_odds_data(data)
        results.update(odds_results)

        # 5. 检查跑动距离
        logger.info("🏃 检查跑动距离...")
        distance_results = self._check_running_distance(data)
        results.update(distance_results)

        # 6. 检查势头图
        logger.info("📈 检查势头图...")
        momentum_results = self._check_momentum_data(data)
        results.update(momentum_results)

        # 7. 生成样本结构
        logger.info("🗺️ 生成数据结构样本...")
        results["sample_structure"] = self._generate_structure_sample(data)

        return results

    def _check_xg_data(self, data: dict[str, Any]) -> dict[str, Any]:
        """检查xG数据"""
        results = {"has_xG": False, "xg_details": {}}

        xg_keywords = ["xg", "expected goals", "xg", "expectedgoals"]
        xg_found = self._deep_search(data, xg_keywords)

        if xg_found:
            results["has_xG"] = True
            results["xg_details"] = {
                "locations": xg_found,
                "sample_values": self._extract_sample_values(data, xg_found[:2]),
            }
            logger.info("✅ 发现xG数据")
        else:
            logger.info("❌ 未发现xG数据")

        return results

    def _check_lineup_data(self, data: dict[str, Any]) -> dict[str, Any]:
        """检查阵容数据"""
        results = {"has_lineups": False, "lineup_details": {}}

        lineup_keywords = ["lineup", "lineups", "starting xi", "players", "team"]
        lineup_found = self._deep_search(data, lineup_keywords)

        if lineup_found:
            results["has_lineups"] = True
            results["lineup_details"] = {
                "locations": lineup_found,
                "forward_names": self._extract_forward_names(data),
            }
            logger.info("✅ 发现阵容数据")
        else:
            logger.info("❌ 未发现阵容数据")

        return results

    def _check_rating_data(self, data: dict[str, Any]) -> dict[str, Any]:
        """检查球员评分"""
        results = {"has_ratings": False, "rating_details": {}}

        rating_keywords = ["rating", "fotmob rating", "player rating", "score"]
        rating_found = self._deep_search(data, rating_keywords)

        if rating_found:
            results["has_ratings"] = True
            results["rating_details"] = {
                "locations": rating_found,
                "sample_ratings": self._extract_sample_values(data, rating_found[:3]),
            }
            logger.info("✅ 发现球员评分数据")
        else:
            logger.info("❌ 未发现球员评分数据")

        return results

    def _check_odds_data(self, data: dict[str, Any]) -> dict[str, Any]:
        """检查赔率数据"""
        results = {"has_odds": False, "odds_details": {}}

        odds_keywords = ["odds", "betting", "bookmaker", "price", "win", "draw"]
        odds_found = self._deep_search(data, odds_keywords)

        if odds_found:
            results["has_odds"] = True
            results["odds_details"] = {
                "locations": odds_found,
                "bookmakers": self._extract_bookmakers(data),
                "odds_type": self._determine_odds_type(data),
            }
            logger.info("✅ 发现赔率数据")
        else:
            logger.info("❌ 未发现赔率数据")

        return results

    def _check_running_distance(self, data: dict[str, Any]) -> dict[str, Any]:
        """检查跑动距离"""
        results = {"has_running_distance": False, "distance_details": {}}

        distance_keywords = ["distance", "km", "running", "cover", "meter", "miles"]
        distance_found = self._deep_search(data, distance_keywords)

        if distance_found:
            results["has_running_distance"] = True
            results["distance_details"] = {
                "locations": distance_found,
                "sample_distances": self._extract_sample_values(
                    data, distance_found[:3]
                ),
            }
            logger.info("✅ 发现跑动距离数据")
        else:
            logger.info("❌ 未发现跑动距离数据")

        return results

    def _check_momentum_data(self, data: dict[str, Any]) -> dict[str, Any]:
        """检查势头图数据"""
        results = {"has_momentum": False, "momentum_details": {}}

        momentum_keywords = ["momentum", "graph", "timeline", "pressure", "attack"]
        momentum_found = self._deep_search(data, momentum_keywords)

        if momentum_found:
            results["has_momentum"] = True
            results["momentum_details"] = {
                "locations": momentum_found,
                "sample_data": self._extract_sample_values(data, momentum_found[:2]),
            }
            logger.info("✅ 发现势头图数据")
        else:
            logger.info("❌ 未发现势头图数据")

        return results

    def _deep_search(self, data: Any, keywords: list[str], path: str = "") -> list[str]:
        """深度搜索关键词"""
        found_paths = []

        if isinstance(data, dict):
            for key, value in data.items():
                current_path = f"{path}.{key}" if path else key

                # 检查key是否匹配关键词
                if any(keyword in key.lower() for keyword in keywords):
                    found_paths.append(current_path)

                # 递归搜索值
                found_paths.extend(self._deep_search(value, keywords, current_path))

        elif isinstance(data, list):
            for i, item in enumerate(data):
                current_path = f"{path}[{i}]" if path else f"[{i}]"
                found_paths.extend(self._deep_search(item, keywords, current_path))

        return found_paths

    def _extract_forward_names(self, data: dict[str, Any]) -> list[str]:
        """提取前锋名字"""
        forwards = []

        def extract_names_recursive(d, depth=0):
            if depth > 10:  # 防止无限递归
                return

            if isinstance(d, dict):
                # 查找前锋相关信息
                for key, value in d.items():
                    if any(
                        word in key.lower()
                        for word in ["forward", "striker", "attacker"]
                    ):
                        if isinstance(value, str):
                            forwards.append(value)
                        elif isinstance(value, dict) and "name" in value:
                            forwards.append(value["name"])

                    extract_names_recursive(value, depth + 1)

            elif isinstance(d, list):
                for item in d:
                    extract_names_recursive(item, depth + 1)

        extract_names_recursive(data)
        return forwards[:5]  # 返回前5个前锋名字

    def _extract_bookmakers(self, data: dict[str, Any]) -> list[str]:
        """提取博彩公司名称"""
        bookmakers = set()

        common_bookmakers = [
            "bet365",
            "william hill",
            "pinnacle",
            "betfair",
            "ladbrokes",
            "coral",
            "sky bet",
            "betway",
            "10bet",
            "marathonbet",
        ]

        def find_bookmakers_recursive(d, depth=0):
            if depth > 10:
                return

            if isinstance(d, str):
                lower_str = d.lower()
                for bookmaker in common_bookmakers:
                    if bookmaker in lower_str:
                        bookmakers.add(bookmaker)

            elif isinstance(d, dict):
                for key, value in d.items():
                    find_bookmakers_recursive(key, depth + 1)
                    find_bookmakers_recursive(value, depth + 1)

            elif isinstance(d, list):
                for item in d:
                    find_bookmakers_recursive(item, depth + 1)

        find_bookmakers_recursive(data)
        return list(bookmakers)

    def _determine_odds_type(self, data: dict[str, Any]) -> str:
        """判断赔率类型"""
        # 简单判断：如果有opening或initial关键字，可能是初盘
        if self._deep_search(data, ["opening", "initial", "first"]):
            return "可能包含初盘"
        # 如果有closing或final关键字，可能是终盘
        elif self._deep_search(data, ["closing", "final", "last"]):
            return "可能包含终盘"
        else:
            return "无法确定类型"

    def _extract_sample_values(
        self, data: dict[str, Any], paths: list[str]
    ) -> dict[str, Any]:
        """提取指定路径的样本值"""
        samples = {}

        for path in paths:
            try:
                value = self._get_value_by_path(data, path)
                if value is not None:
                    samples[path] = value
            except Exception:
                continue

        return samples

    def _get_value_by_path(self, data: dict[str, Any], path: str) -> Any:
        """根据路径获取值"""
        current = data
        parts = path.split(".")

        for part in parts:
            if "[" in part and "]" in part:
                # 处理数组索引
                key, index_str = part.split("[")
                index = int(index_str.rstrip("]"))
                current = current[key][index]
            else:
                current = current[part]

        return current

    def _generate_structure_sample(
        self, data: dict[str, Any], max_depth: int = 2
    ) -> dict[str, Any]:
        """生成数据结构样本"""

        def get_structure(d, depth=0):
            if depth >= max_depth:
                return str(type(d).__name__)

            if isinstance(d, dict):
                return {k: get_structure(v, depth + 1) for k, v in list(d.items())[:5]}
            elif isinstance(d, list):
                return [get_structure(d[0], depth + 1)] if d else []
            else:
                return str(type(d).__name__)

        return get_structure(data)

    def generate_forensics_report(self, results: dict[str, Any]) -> str:
        """生成取证报告"""
        report = f"""
# 🔍 数据取证专家报告

## 📊 基础信息
- **数据大小**: {results.get('data_size_bytes', 0):,} 字节
- **检查时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## 🎯 关键数据检查结果

### 1. xG (预期进球) 数据
- **状态**: {'✅ 存在' if results.get('has_xG') else '❌ 缺失'}
{self._format_details(results.get('xg_details', {}), 'xG')}

### 2. 阵容数据
- **状态**: {'✅ 存在' if results.get('has_lineups') else '❌ 缺失'}
{self._format_details(results.get('lineup_details', {}), '阵容')}

### 3. 球员评分
- **状态**: {'✅ 存在' if results.get('has_ratings') else '❌ 缺失'}
{self._format_details(results.get('rating_details', {}), '评分')}

### 4. 赔率数据
- **状态**: {'✅ 存在' if results.get('has_odds') else '❌ 缺失'}
{self._format_details(results.get('odds_details', {}), '赔率')}

### 5. 跑动距离
- **状态**: {'✅ 存在' if results.get('has_running_distance') else '❌ 缺失'}
{self._format_details(results.get('distance_details', {}), '跑动距离')}

### 6. 势头图
- **状态**: {'✅ 存在' if results.get('has_momentum') else '❌ 缺失'}
{self._format_details(results.get('momentum_details', {}), '势头图')}

## 🗺️ 数据结构样本
```json
{json.dumps(results.get('sample_structure', {}), indent=2, ensure_ascii=False)}
```

## 🎯 取证结论
{self._generate_conclusion(results)}
"""
        return report

    def _format_details(self, details: dict[str, Any], category: str) -> str:
        """格式化详情信息"""
        if not details:
            return "   - 无详细信息"

        formatted = []

        if "locations" in details:
            formatted.append(f"   - 位置: {', '.join(details['locations'][:3])}")

        if "sample_values" in details:
            formatted.append(f"   - 样本值: {details['sample_values']}")

        if "forward_names" in details and details["forward_names"]:
            formatted.append(
                f"   - 前锋名字: {', '.join(details['forward_names'][:3])}"
            )

        if "bookmakers" in details and details["bookmakers"]:
            formatted.append(f"   - 博彩公司: {', '.join(details['bookmakers'])}")

        if "odds_type" in details:
            formatted.append(f"   - 赔率类型: {details['odds_type']}")

        return "\n".join(formatted)

    def _generate_conclusion(self, results: dict[str, Any]) -> str:
        """生成结论"""
        positive_count = sum(
            [
                results.get("has_xG", False),
                results.get("has_lineups", False),
                results.get("has_ratings", False),
                results.get("has_odds", False),
                results.get("has_running_distance", False),
                results.get("has_momentum", False),
            ]
        )

        total_count = 6
        percentage = (positive_count / total_count) * 100

        if percentage >= 80:
            return f"🎉 **优秀**: {positive_count}/{total_count} 项核心数据存在 ({percentage:.0f}%)，V2采集器表现优异！"
        elif percentage >= 60:
            return f"✅ **良好**: {positive_count}/{total_count} 项核心数据存在 ({percentage:.0f}%)，V2采集器基本满足需求。"
        elif percentage >= 40:
            return f"⚠️ **一般**: {positive_count}/{total_count} 项核心数据存在 ({percentage:.0f}%)，V2采集器需要改进。"
        else:
            return f"❌ **不足**: {positive_count}/{total_count} 项核心数据存在 ({percentage:.0f}%)，V2采集器存在严重缺陷。"


async def main():
    """主函数"""
    logger.info("🕵️ 数据取证专家开始工作...")

    expert = DataForensicsExpert()

    try:
        # Step 1: 定点狙击 - 捕获目标比赛数据
        logger.info("=" * 60)
        logger.info("Step 1: 定点狙击 - 捕获目标比赛数据")
        logger.info("=" * 60)

        captured_data = await expert.capture_target_match()

        if not captured_data:
            logger.error("❌ 数据捕获失败，无法进行取证分析")
            sys.exit(1)

        # Step 2: 深度取证 - 分析数据内容
        logger.info("\n" + "=" * 60)
        logger.info("Step 2: 深度取证 - 分析数据内容")
        logger.info("=" * 60)

        results = expert.inspect_data_depth(captured_data)

        # Step 3: 生成报告
        logger.info("\n" + "=" * 60)
        logger.info("Step 3: 生成取证报告")
        logger.info("=" * 60)

        report = expert.generate_forensics_report(results)

        # 打印报告
        print(report)

        # 保存报告到文件
        report_path = "data_forensics_report.md"
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(report)

        logger.info(f"📄 详细取证报告已保存到: {report_path}")

        # 保存原始数据
        raw_data_path = "captured_match_data.json"
        with open(raw_data_path, "w", encoding="utf-8") as f:
            f.write(captured_data)

        logger.info(f"📄 原始捕获数据已保存到: {raw_data_path}")

        # 返回适当的退出码
        if results.get("has_lineups") and results.get("has_ratings"):
            logger.info("🎉 取证成功：发现关键数据字段")
            sys.exit(0)
        else:
            logger.warning("⚠️ 取证完成：但缺少关键数据字段")
            sys.exit(1)

    except Exception as e:
        logger.error(f"❌ 取证过程失败: {e}")
        sys.exit(2)


if __name__ == "__main__":
    asyncio.run(main())
