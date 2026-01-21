#!/usr/bin/env python3
"""
英超24/25赛季L1级数据采集器 - 创世纪级版本
专门用于构建英超量化母库的完整赛季数据采集
"""

import csv
from datetime import UTC, datetime
import logging
import os

import requests

logger = logging.getLogger(__name__)


class PremierLeagueL1Harvester:
    """
    英超24/25赛季L1数据采集器

    核心功能:
    1. 抓取英超24/25赛季所有比赛清单 (目标380场)
    2. 提取基础比赛信息 (ID、日期、对阵、比分)
    3. 构建创世纪级的量化母库清单
    """

    def __init__(self):
        """初始化L1采集器"""
        self.base_url = "https://www.fotmob.com/api"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-US,en;q=0.9,en-GB;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)

        # 英超24/25赛季配置
        self.premier_league_id = 47  # FotMob中英超的ID
        self.season_id = 23032  # 24/25赛季ID
        self.output_file = "data/production/genesis_manifest_PL2425.csv"

        logger.info("🏆 初始化英超24/25赛季L1采集器")

    def get_season_matches(self) -> list[dict]:
        """
        获取英超24/25赛季所有比赛

        Returns:
            比赛信息列表
        """
        logger.info(f"🏆 开始获取英超24/25赛季 (League ID: {self.premier_league_id})")

        # 构建请求URL
        url = f"{self.base_url}/leagues?id={self.premier_league_id}&season={self.season_id}"
        logger.info(f"🌍 请求URL: {url}")

        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()

            data = response.json()

            # 解析赛季数据
            matches = self._parse_season_data(data)

            logger.info(f"✅ 成功获取 {len(matches)} 场比赛信息")
            return matches

        except requests.exceptions.RequestException as e:
            logger.exception(f"❌ 请求英超数据失败: {e}")
            return []
        except Exception as e:
            logger.exception(f"❌ 解析英超数据异常: {e}")
            return []

    def _parse_season_data(self, data: dict) -> list[dict]:
        """
        解析赛季数据中的比赛信息

        Args:
            data: API响应数据

        Returns:
            比赛信息列表
        """
        matches = []

        try:
            # 数据在 fixtures.allMatches 中
            if "fixtures" in data and "allMatches" in data["fixtures"]:
                all_matches = data["fixtures"]["allMatches"]
                logger.info(f"📊 找到 {len(all_matches)} 场比赛数据")

                for match in all_matches:
                    match_info = self._extract_match_info(match)
                    if match_info:
                        matches.append(match_info)
            else:
                logger.warning("⚠️ 未找到比赛数据字段")

            logger.info(f"📊 从API数据中解析出 {len(matches)} 场有效比赛")
            return matches

        except Exception as e:
            logger.exception(f"❌ 解析比赛数据失败: {e}")
            return []

    def _extract_match_info(self, match: dict) -> dict | None:
        """
        提取单场比赛的基础信息

        Args:
            match: 比赛数据

        Returns:
            比赛信息字典
        """
        try:
            # 提取基础信息 - 处理可能的字符串类型
            home_data = match.get("home")
            if isinstance(home_data, str):
                home_team = home_data
            else:
                home_team = home_data.get("name", "Unknown Home") if home_data else "Unknown Home"

            away_data = match.get("away")
            if isinstance(away_data, str):
                away_team = away_data
            else:
                away_team = away_data.get("name", "Unknown Away") if away_data else "Unknown Away"

            # 提取时间信息
            status = match.get("status", {})
            match_time_str = status.get("utcTime", "")

            # 提取比分信息
            home_score = None
            away_score = None
            actual_result = None

            if status.get("finished"):
                score_str = status.get("scoreStr", "")
                if score_str and "-" in score_str:
                    try:
                        home_score, away_score = map(int, score_str.split("-"))
                        # 确定比赛结果
                        if home_score > away_score:
                            actual_result = "H"
                        elif home_score < away_score:
                            actual_result = "A"
                        else:
                            actual_result = "D"
                    except ValueError:
                        logger.warning(f"⚠️ 无法解析比分: {score_str}")

            # 提取比赛ID - 处理字符串类型
            match_id = match.get("id")

            # 提取其他有用信息 - round字段是字符串
            round_info = match.get("round", "")
            round_name = str(round_info) if round_info else ""

            # 尝试从 venue 字段获取场地信息
            venue_data = match.get("venue")
            if isinstance(venue_data, str):
                venue_name = venue_data
            else:
                venue_name = venue_data.get("name", "") if venue_data else ""

            return {
                "match_id": match_id,
                "external_id": str(match_id) if match_id else "",
                "home_team": home_team,
                "away_team": away_team,
                "match_date": match_time_str,
                "home_score": home_score,
                "away_score": away_score,
                "actual_result": actual_result,
                "round_name": round_name,
                "stage_name": "Premier League",  # 英超没有stage信息，使用固定值
                "status": status.get("statusStr", ""),
                "venue": venue_name,
                "league_name": "Premier League",
                "season_id": self.season_id,
                "is_finished": status.get("finished", False),
                "collection_date": datetime.now(UTC).isoformat(),
            }

        except Exception as e:
            logger.exception(f"❌ 提取比赛信息失败 {match.get('id', 'unknown')}: {e}")
            return None

    def save_manifest_csv(self, matches: list[dict]) -> bool:
        """
        保存创世纪级清单到CSV文件

        Args:
            matches: 比赛信息列表

        Returns:
            保存是否成功
        """
        if not matches:
            logger.error("❌ 没有比赛数据可保存")
            return False

        try:
            # 确保目录存在
            os.makedirs(os.path.dirname(self.output_file), exist_ok=True)

            # 定义CSV字段
            fieldnames = [
                "match_id",
                "external_id",
                "home_team",
                "away_team",
                "match_date",
                "home_score",
                "away_score",
                "actual_result",
                "round_name",
                "stage_name",
                "status",
                "venue",
                "league_name",
                "season_id",
                "is_finished",
                "collection_date",
            ]

            # 写入CSV文件
            with open(self.output_file, "w", newline="", encoding="utf-8") as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()

                # 按日期排序
                sorted_matches = sorted(matches, key=lambda x: x["match_date"] or "")

                for match in sorted_matches:
                    writer.writerow(match)

            logger.info(f"💾 创世纪清单已保存: {self.output_file}")
            logger.info(f"📊 包含 {len(matches)} 场英超比赛")

            return True

        except Exception as e:
            logger.exception(f"❌ 保存清单文件失败: {e}")
            return False

    def harvest_premier_league_season(self) -> bool:
        """
        完整的英超24/25赛季采集流程

        Returns:
            采集是否成功
        """
        logger.info("🚀 开始英超24/25赛季创世纪级数据采集")
        logger.info("=" * 60)

        try:
            # Step 1: 获取赛季比赛数据
            matches = self.get_season_matches()

            if not matches:
                logger.error("❌ 未能获取到任何比赛数据")
                return False

            # Step 2: 验证数据质量
            finished_matches = [m for m in matches if m.get("is_finished", False)]
            unfinished_matches = [m for m in matches if not m.get("is_finished", False)]

            logger.info("📊 数据质量统计:")
            logger.info(f"   总比赛数: {len(matches)}")
            logger.info(f"   已完成比赛: {len(finished_matches)}")
            logger.info(f"   未完成比赛: {len(unfinished_matches)}")

            if len(matches) < 300:  # 英超通常有380场左右
                logger.warning(f"⚠️ 比赛数量偏少: {len(matches)} 场 (预期约380场)")

            # Step 3: 保存到创世纪清单文件
            success = self.save_manifest_csv(matches)

            if success:
                logger.info("🎉 英超24/25赛季数据采集完成!")
                logger.info(f"🎯 创世纪清单已生成: {self.output_file}")
                logger.info("=" * 60)
                return True
            logger.error("❌ 保存创世纪清单失败")
            return False

        except Exception as e:
            logger.exception(f"❌ 数据采集流程异常: {e}")
            return False

    def validate_manifest_quality(self) -> dict:
        """
        验证创世纪清单数据质量

        Returns:
            质量报告
        """
        if not os.path.exists(self.output_file):
            return {"status": "error", "message": "创世纪清单文件不存在"}

        try:
            with open(self.output_file, encoding="utf-8") as csvfile:
                reader = csv.DictReader(csvfile)
                matches = list(reader)

            total_matches = len(matches)
            finished_matches = len([m for m in matches if m.get("is_finished") == "True"])

            # 统计结果分布
            results = {}
            for match in matches:
                result = match.get("actual_result", "N/A")
                results[result] = results.get(result, 0) + 1

            report = {
                "status": "success",
                "total_matches": total_matches,
                "finished_matches": finished_matches,
                "completion_rate": round(finished_matches / total_matches * 100, 2)
                if total_matches > 0
                else 0,
                "result_distribution": results,
                "file_size_mb": round(os.path.getsize(self.output_file) / 1024 / 1024, 2),
            }

            logger.info("📊 创世纪清单质量报告:")
            logger.info(f"   总比赛数: {report['total_matches']}")
            logger.info(f"   已完成比赛: {report['finished_matches']}")
            logger.info(f"   完成率: {report['completion_rate']}%")
            logger.info(f"   文件大小: {report['file_size_mb']}MB")
            logger.info(f"   结果分布: {report['result_distribution']}")

            return report

        except Exception as e:
            return {"status": "error", "message": f"验证失败: {e}"}


def main():
    """主函数"""
    harvester = PremierLeagueL1Harvester()

    # 执行创世纪级数据采集
    success = harvester.harvest_premier_league_season()

    # 验证数据质量
    if success:
        report = harvester.validate_manifest_quality()
        logger.info(f"\n🎯 最终状态: {report['status']}")

    return 0 if success else 1


if __name__ == "__main__":
    main()
