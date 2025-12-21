"""FotMob API 采集器 - 资深后端工程师重构版
Senior Backend Engineer Refactored Version

使用正确的鉴权头直接访问 FotMob API，无需浏览器自动化。
"""

import asyncio
import json
from typing import Any, Optional
import aiohttp
import logging

logger = logging.getLogger(__name__)


class FotMobCollector:
    """FotMob API 采集器 - 正确鉴权版本."""

    def __init__(
        self,
        max_retries: int = 3,
        timeout: int = 30,
    ):
        self.max_retries = max_retries
        self.timeout = timeout
        self.client: Optional[aiohttp.ClientSession] = None

        # 统计信息
        self.stats = {
            "requests_made": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "matches_collected": 0,
        }

        logger.info("🔐 FotMob API采集器初始化完成 - 资深后端工程师版本")

    async def initialize(self):
        """初始化HTTP客户端 - 包含关键鉴权头."""
        # 🎯 这就是钥匙！FotMob API的正确鉴权头
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Referer": "https://www.fotmob.com/",
            "Origin": "https://www.fotmob.com",
            # 🔑 关键鉴权头 - 必须硬编码！
            "x-mas": "eyJib2R5Ijp7InVybCI6Ii9hcGkvZGF0YS9hdWRpby1tYXRjaGVzIiwiY29kZSI6MTc2NDA1NTcxMjgyOCwiZm9vIjoicHJvZHVjdGlvbjoyMDhhOGY4N2MyY2MxMzM0M2YxZGQ4NjcxNDcxY2Y1YTAzOWRjZWQzIn0sInNpZ25hdHVyZSI6IkMyMkI0MUQ5Njk2NUJBREM1NjMyNzcwRDgyNzVFRTQ4In0=",
            "x-foo": "production:208a8f87c2cc13343f1dd8671471cf5a039dced3",
        }

        # 创建HTTP客户端
        timeout = aiohttp.ClientTimeout(total=self.timeout)
        self.client = aiohttp.ClientSession(
            headers=headers,
            timeout=timeout,
        )

        logger.info("🔐 HTTP客户端初始化完成 - 已加载FotMob关键鉴权头")

    async def collect_match_data(self, match_id: str) -> Optional[dict[str, Any]]:
        """采集单场比赛详情数据 - L2详情采集."""
        try:
            if not self.client:
                await self.initialize()

            # 🎯 正确的L2 API端点
            url = "https://www.fotmob.com/api/matchDetails"
            params = {"matchId": match_id}

            full_url = f"{url}?matchId={match_id}"
            logger.info(f"🎯 L2请求: {full_url}")

            async with self.client.get(url, params=params) as response:
                self.stats["requests_made"] += 1

                logger.info(f"🔍 L2响应状态码: {response.status}, URL: {full_url}")

                if response.status == 200:
                    data = await response.json()
                    self.stats["successful_requests"] += 1
                    self.stats["matches_collected"] += 1

                    # 📊 数据湖模式：立即保存原始数据
                    raw_save_success = await self._save_raw_data(match_id, data)
                    if not raw_save_success:
                        logger.warning(f"⚠️ 原始数据保存失败，但继续处理: {match_id}")

                    # 🎯 关键验证：检查是否包含xG数据
                    if self._validate_data_quality(data, match_id):
                        logger.info(f"✅ L2采集成功: {match_id} (数据已保存到数据湖)")
                        return data
                    else:
                        logger.warning(f"⚠️ L2数据质量不足: {match_id} (原始数据已保存)")
                        return None
                else:
                    response_text = await response.text()
                    logger.error(f"❌ L2请求失败，状态码: {response.status}, URL: {full_url}")
                    logger.error(f"🔍 响应内容: {response_text[:200]}...")
                    self.stats["failed_requests"] += 1
                    return None

        except Exception as e:
            logger.error(f"❌ L2采集异常 {match_id}: {e}")
            import traceback

            logger.error(f"🔍 详细错误: {traceback.format_exc()}")
            self.stats["failed_requests"] += 1
            return None

    async def _save_raw_data(self, match_id: str, data: dict[str, Any]) -> bool:
        """
        保存原始数据到raw_match_data表 - 数据湖模式

        Args:
            match_id: 比赛ID
            data: 原始JSON数据

        Returns:
            bool: 保存是否成功
        """
        try:
            # 使用asyncpg直接连接，避免ORM开销
            import asyncpg
            import urllib.parse
            import os

            # 从环境变量获取数据库URL
            db_url = os.getenv(
                "DB_URL",
                "postgresql+asyncpg://postgres:postgres@localhost:5432/football_prediction",
            )

            # 解析数据库URL
            parsed = urllib.parse.urlparse(db_url.replace("postgresql+asyncpg://", "postgresql://"))

            conn = await asyncpg.connect(
                host=parsed.hostname or "localhost",
                port=parsed.port or 5432,
                user=parsed.username or "postgres",
                password=parsed.password or "postgres",
                database=parsed.path.lstrip("/") or "football_prediction",
            )

            try:
                # 构建UPSERT SQL语句 - 数据湖模式
                query = """
                    INSERT INTO raw_match_data
                    (external_id, source, raw_data, collected_at, created_at, updated_at)
                    VALUES ($1, $2, $3, NOW(), NOW(), NOW())
                    ON CONFLICT (external_id)
                    DO UPDATE SET
                        raw_data = EXCLUDED.raw_data,
                        updated_at = NOW()
                """

                # 执行保存
                await conn.execute(query, match_id, "fotmob", json.dumps(data, ensure_ascii=False))

                data_size = len(json.dumps(data, ensure_ascii=False))
                logger.info(f"📊 原始数据已保存: {match_id} (大小: {data_size} 字节)")
                return True

            finally:
                await conn.close()

        except Exception as e:
            logger.error(f"❌ 原始数据保存失败 {match_id}: {e}")
            import traceback

            logger.error(f"🔍 详细错误: {traceback.format_exc()}")
            return False

    def _extract_odds(self, content: dict[str, Any]) -> dict[str, Any]:
        """提取赔率数据 - 支持多种赔率数据源"""
        odds_data = {
            "pre_match_home_odds": None,
            "pre_match_draw_odds": None,
            "pre_match_away_odds": None,
            "home_win_probability": None,
            "draw_probability": None,
            "away_win_probability": None,
        }

        try:
            # 1. 检查superlive中的赔率数据
            if "superlive" in content:
                superlive = content["superlive"]
                if "odds" in superlive:
                    odds = superlive["odds"]
                    if isinstance(odds, dict) and "home" in odds:
                        odds_data["pre_match_home_odds"] = odds.get("home")
                        odds_data["pre_match_draw_odds"] = odds.get("draw")
                        odds_data["pre_match_away_odds"] = odds.get("away")

            # 2. 检查betting模块
            if "betting" in content:
                betting = content["betting"]

                # 检查preMatchOdds
                if "preMatchOdds" in betting:
                    pre_odds = betting["preMatchOdds"]
                    if isinstance(pre_odds, dict):
                        odds_data["pre_match_home_odds"] = pre_odds.get("home") or odds_data["pre_match_home_odds"]
                        odds_data["pre_match_draw_odds"] = pre_odds.get("draw") or odds_data["pre_match_draw_odds"]
                        odds_data["pre_match_away_odds"] = pre_odds.get("away") or odds_data["pre_match_away_odds"]

                # 检查matchOdds
                if "matchOdds" in betting and not odds_data["pre_match_home_odds"]:
                    match_odds = betting["matchOdds"]
                    if isinstance(match_odds, dict):
                        odds_data["pre_match_home_odds"] = match_odds.get("home")
                        odds_data["pre_match_draw_odds"] = match_odds.get("draw")
                        odds_data["pre_match_away_odds"] = match_odds.get("away")

            # 3. 检查general.bettingOdds
            if "general" in content and isinstance(content["general"], dict):
                general = content["general"]
                if "bettingOdds" in general and not odds_data["pre_match_home_odds"]:
                    betting_odds = general["bettingOdds"]
                    if isinstance(betting_odds, dict):
                        # 尝试多个可能的字段名
                        home_odds = betting_odds.get("homeWin") or betting_odds.get("home") or betting_odds.get("1")
                        draw_odds = betting_odds.get("draw") or betting_odds.get("X")
                        away_odds = betting_odds.get("awayWin") or betting_odds.get("away") or betting_odds.get("2")

                        odds_data["pre_match_home_odds"] = home_odds or odds_data["pre_match_home_odds"]
                        odds_data["pre_match_draw_odds"] = draw_odds or odds_data["pre_match_draw_odds"]
                        odds_data["pre_match_away_odds"] = away_odds or odds_data["pre_match_away_odds"]

            # 4. 计算隐含概率 (如果有赔率数据)
            if odds_data["pre_match_home_odds"]:
                try:
                    home_odds = float(odds_data["pre_match_home_odds"])
                    draw_odds = float(odds_data["pre_match_draw_odds"]) if odds_data["pre_match_draw_odds"] else None
                    away_odds = float(odds_data["pre_match_away_odds"])

                    # 转换为隐含概率 (考虑bookmaker margin)
                    if home_odds > 0 and away_odds > 0:
                        odds_data["home_win_probability"] = round(1.0 / home_odds * 100, 2)
                        odds_data["away_win_probability"] = round(1.0 / away_odds * 100, 2)
                        if draw_odds and draw_odds > 0:
                            odds_data["draw_probability"] = round(1.0 / draw_odds * 100, 2)
                except (ValueError, TypeError) as e:
                    logger.warning(f"赔率数据转换失败: {e}")

            # 5. 数据质量验证
            valid_odds_count = sum(
                [
                    1
                    for v in [
                        odds_data["pre_match_home_odds"],
                        odds_data["pre_match_draw_odds"],
                        odds_data["pre_match_away_odds"],
                    ]
                    if v is not None and isinstance(v, (int, float)) and v > 1.0
                ]
            )

            if valid_odds_count > 0:
                logger.info(f"✅ 成功提取 {valid_odds_count}/3 项赔率数据")
                return odds_data
            else:
                logger.debug("⚠️ 未找到有效赔率数据")
                return odds_data

        except Exception as e:
            logger.error(f"❌ 赔率数据提取失败: {e}")
            return odds_data

    def _extract_player_ratings(self, content: dict[str, Any]) -> dict[str, Any]:
        """提取球员评分数据 - 从playerStats中提取FotMob评分"""
        ratings_data = {
            "home_team_ratings": [],
            "away_team_ratings": [],
            "avg_home_rating": None,
            "avg_away_rating": None,
            "best_home_player": None,
            "best_away_player": None,
            "total_players_rated": 0,
            "team_ratings": {},  # 按teamId分组
        }

        try:
            # 检查playerStats数据
            if "playerStats" not in content:
                logger.debug("⚠️ 未找到playerStats数据")
                return ratings_data

            player_stats = content["playerStats"]
            if not isinstance(player_stats, dict):
                logger.debug("⚠️ playerStats不是对象格式")
                return ratings_data

            # 遍历球员统计，提取评分
            for player_id, player_info in player_stats.items():
                if not isinstance(player_info, dict):
                    continue

                team_id = player_info.get("teamId")
                player_name = player_info.get("name", "Unknown")

                # 检查stats数组
                stats = player_info.get("stats", [])
                if not isinstance(stats, list) or len(stats) == 0:
                    continue

                player_rating = None

                # 遍历stats数组，查找评分
                for stat_group in stats:
                    if not isinstance(stat_group, dict) or "stats" not in stat_group:
                        continue

                    stat_details = stat_group["stats"]
                    if isinstance(stat_details, dict):
                        # 查找FotMob评分
                        if "FotMob rating" in stat_details:
                            rating_info = stat_details["FotMob rating"]
                            if isinstance(rating_info, dict) and "stat" in rating_info:
                                stat_value = rating_info["stat"]
                                if isinstance(stat_value, dict) and "value" in stat_value:
                                    player_rating = float(stat_value["value"])
                                    break

                if player_rating and player_rating > 0:
                    player_data = {
                        "player_id": int(player_id),
                        "player_name": player_name,
                        "team_id": team_id,
                        "rating": player_rating,
                    }

                    # 按球队分组
                    if team_id not in ratings_data["team_ratings"]:
                        ratings_data["team_ratings"][team_id] = []
                    ratings_data["team_ratings"][team_id].append(player_data)

            # 处理球队评分数据
            team_ids = list(ratings_data["team_ratings"].keys())

            if len(team_ids) >= 2:
                # 取前两个球队作为主客队
                home_team_id = team_ids[0]
                away_team_id = team_ids[1]

                ratings_data["home_team_ratings"] = ratings_data["team_ratings"][home_team_id]
                ratings_data["away_team_ratings"] = ratings_data["team_ratings"][away_team_id]

                # 计算主队统计
                home_ratings = [p["rating"] for p in ratings_data["home_team_ratings"]]
                if home_ratings:
                    ratings_data["avg_home_rating"] = round(sum(home_ratings) / len(home_ratings), 2)
                    best_home = max(ratings_data["home_team_ratings"], key=lambda x: x["rating"])
                    ratings_data["best_home_player"] = {
                        "name": best_home["player_name"],
                        "rating": best_home["rating"],
                    }

                # 计算客队统计
                away_ratings = [p["rating"] for p in ratings_data["away_team_ratings"]]
                if away_ratings:
                    ratings_data["avg_away_rating"] = round(sum(away_ratings) / len(away_ratings), 2)
                    best_away = max(ratings_data["away_team_ratings"], key=lambda x: x["rating"])
                    ratings_data["best_away_player"] = {
                        "name": best_away["player_name"],
                        "rating": best_away["rating"],
                    }

            # 计算总评分球员数
            ratings_data["total_players_rated"] = len(ratings_data["home_team_ratings"]) + len(
                ratings_data["away_team_ratings"]
            )

            if ratings_data["total_players_rated"] > 0:
                logger.info(f"✅ 成功提取 {ratings_data['total_players_rated']} 名球员评分")
                logger.debug(f"   主队平均评分: {ratings_data['avg_home_rating']}")
                logger.debug(f"   客队平均评分: {ratings_data['avg_away_rating']}")

                # 显示评分前3名的球员
                all_players = ratings_data["home_team_ratings"] + ratings_data["away_team_ratings"]
                top_players = sorted(all_players, key=lambda x: x["rating"], reverse=True)[:3]
                logger.debug("   评分前3名球员:")
                for i, player in enumerate(top_players, 1):
                    logger.debug(f"     {i}. {player['player_name']}: {player['rating']}")
            else:
                logger.debug("⚠️ 未找到有效球员评分数据")

            return ratings_data

        except Exception as e:
            logger.error(f"❌ 球员评分提取失败: {e}")
            return ratings_data

    def _extract_match_events(self, content: dict[str, Any]) -> dict[str, Any]:
        """提取比赛事件数据 - 红黄牌、进球、时间线等"""
        events_data = {
            "home_red_cards": 0,
            "away_red_cards": 0,
            "home_yellow_cards": 0,
            "away_yellow_cards": 0,
            "total_events": 0,
            "goals": [],
            "cards": [],
            "substitutions": [],
            "match_events": [],  # 完整事件时间线
        }

        try:
            # 获取主客队ID以便区分事件
            home_team_id = None
            away_team_id = None

            if "general" in content:
                general = content["general"]
                home_team_id = general.get("homeTeam", {}).get("id")
                away_team_id = general.get("awayTeam", {}).get("id")

            # 检查events数据 - 主要事件来源
            if "events" in content:
                events = content["events"]
                if isinstance(events, dict) and "events" in events:
                    event_list = events["events"]

                    if isinstance(event_list, list):
                        events_data["total_events"] = len(event_list)

                        # 处理每个事件
                        for event in event_list:
                            if not isinstance(event, dict):
                                continue

                            event_type = event.get("type")
                            event_time = event.get("time", 0)
                            is_home = event.get("isHome", False)

                            # 构建标准化事件对象
                            standardized_event = {
                                "type": event_type,
                                "time": event_time,
                                "timeStr": event.get("timeStr", ""),
                                "isHome": is_home,
                                "player": event.get("player", {}),
                                "team": "home" if is_home else "away",
                            }

                            # 添加特定事件的详细信息
                            if event_type == "Goal":
                                goal_info = {
                                    "player": event.get("nameStr", ""),
                                    "player_id": event.get("playerId"),
                                    "score": event.get("newScore", []),
                                    "isPenalty": event.get("goalDescription") == "Penalty",
                                    "ownGoal": event.get("ownGoal", False),
                                }
                                standardized_event.update(goal_info)
                                events_data["goals"].append(standardized_event)

                            elif event_type == "Card":
                                card_type = event.get("card", "")
                                card_info = {
                                    "player": event.get("nameStr", ""),
                                    "player_id": event.get("playerId"),
                                    "cardType": card_type,  # "Yellow" 或 "Red"
                                }
                                standardized_event.update(card_info)
                                events_data["cards"].append(standardized_event)

                                # 统计红黄牌数量
                                if card_type == "Red":
                                    if is_home:
                                        events_data["home_red_cards"] += 1
                                    else:
                                        events_data["away_red_cards"] += 1
                                elif card_type == "Yellow":
                                    if is_home:
                                        events_data["home_yellow_cards"] += 1
                                    else:
                                        events_data["away_yellow_cards"] += 1

                            elif event_type == "Substitution":
                                sub_info = {"swap": event.get("swap", [])}
                                standardized_event.update(sub_info)
                                events_data["substitutions"].append(standardized_event)

                            # 添加到完整事件时间线
                            events_data["match_events"].append(standardized_event)

            # 检查header中的红牌统计（备用数据源）
            if "header" in content:
                header = content["header"]
                if "status" in header:
                    status = header["status"]
                    # 使用header中的红牌数量作为验证或补充
                    header_home_reds = status.get("numberOfHomeRedCards", 0)
                    header_away_reds = status.get("numberOfAwayRedCards", 0)

                    # 如果events中没有找到红牌，使用header数据
                    if events_data["home_red_cards"] == 0 and header_home_reds > 0:
                        events_data["home_red_cards"] = header_home_reds
                    if events_data["away_red_cards"] == 0 and header_away_reds > 0:
                        events_data["away_red_cards"] = header_away_reds

            logger.info(f"✅ 成功提取比赛事件: {events_data['total_events']} 个事件")
            logger.info(
                f"   进球: {len(events_data['goals'])}, 黄牌: {events_data['home_yellow_cards'] + events_data['away_yellow_cards']}, 红牌: {events_data['home_red_cards'] + events_data['away_red_cards']}"
            )

            return events_data

        except Exception as e:
            logger.error(f"❌ 比赛事件提取失败: {e}")
            return events_data

    def _validate_data_quality(self, data: dict[str, Any], match_id: str) -> bool:
        """验证数据质量 - 确保包含关键ML特征"""
        try:
            # 检查基础结构
            if not data or "content" not in data:
                logger.warning(f"⚠️ 数据结构异常 {match_id}: 缺少content字段")
                return False

            content = data.get("content", {})

            # 检查xG数据（关键ML特征）
            has_xg = False
            if "stats" in content:
                stats = content.get("stats", {})
                # 检查各种可能的xG字段
                xg_fields = ["xg", "expectedGoals", "xG", "expected_goals"]
                for field in xg_fields:
                    if field in str(stats):
                        has_xg = True
                        break

            # 检查阵容数据
            has_lineups = "lineups" in content and content.get("lineups")

            # 检查赔率数据 - 使用新的提取方法
            odds_data = self._extract_odds(content)
            has_odds = any(odds_data.values())

            # 检查球员评分数据 - 使用新的提取方法
            ratings_data = self._extract_player_ratings(content)
            has_ratings = ratings_data["total_players_rated"] > 0

            # 检查比赛事件数据 - 使用新的提取方法
            events_data = self._extract_match_events(content)
            has_events = events_data["total_events"] > 0

            # 至少需要一个关键特征
            quality_score = sum([has_xg, has_lineups, has_odds, has_ratings, has_events])

            logger.info(
                f"📊 数据质量评估 {match_id}: xG={has_xg}, lineups={has_lineups}, odds={has_odds}, ratings={has_ratings}, events={has_events}, score={quality_score}/5"
            )

            return quality_score >= 1  # 至少有一个特征

        except Exception as e:
            logger.error(f"❌ 数据质量验证失败 {match_id}: {e}")
            return False

    async def collect_matches_by_date(self, date_str: str) -> list[dict[str, Any]]:
        """按日期采集比赛列表 - L1列表采集."""
        try:
            if not self.client:
                await self.initialize()

            # 🎯 正确的L1 API端点 - 修正日期格式
            formatted_date = date_str.replace("-", "")  # 2024-12-04 -> 20241204
            url = "https://www.fotmob.com/api/matches"
            params = {
                "date": formatted_date,
                "timezone": "Asia/Shanghai",
                "ccode3": "CHN",
            }

            full_url = f"{url}?date={formatted_date}&timezone=Asia/Shanghai&ccode3=CHN"
            logger.info(f"🎯 L1请求: {full_url}")

            async with self.client.get(url, params=params) as response:
                self.stats["requests_made"] += 1

                logger.info(f"🔍 L1响应状态码: {response.status}, URL: {full_url}")

                if response.status == 200:
                    data = await response.json()
                    logger.info(f"✅ L1采集成功: {formatted_date}")

                    # 解析比赛数据
                    matches = []
                    if "matches" in data:
                        matches = data["matches"]
                    elif "leagues" in data:
                        for league in data["leagues"]:
                            if "matches" in league:
                                matches.extend(league["matches"])
                    else:
                        logger.info(f"🔍 L1数据结构: {list(data.keys())}")
                        for _key, value in data.items():
                            if isinstance(value, list) and value and isinstance(value[0], dict):
                                matches.extend(value)
                                break

                    logger.info(f"✅ 解析到 {len(matches)} 场比赛")
                    return matches
                else:
                    response_text = await response.text()
                    logger.error(f"❌ L1请求失败，状态码: {response.status}, URL: {full_url}")
                    logger.error(f"🔍 响应内容: {response_text[:200]}...")
                    return []

        except Exception as e:
            logger.error(f"❌ L1采集异常 {date_str}: {e}")
            import traceback

            logger.error(f"🔍 详细错误: {traceback.format_exc()}")
            return []

    async def batch_collect_matches(
        self, match_ids: list[str], delay_between_requests: float = 2.0
    ) -> list[dict[str, Any]]:
        """批量采集比赛数据."""
        results = []
        total_matches = len(match_ids)

        logger.info(f"🚀 开始批量采集 {total_matches} 场比赛数据")

        for i, match_id in enumerate(match_ids, 1):
            try:
                logger.info(f"🔄 采集进度: {i}/{total_matches} - 比赛 {match_id}")

                data = await self.collect_match_data(match_id)
                if data:
                    results.append(data)
                    logger.info(f"✅ 成功采集: {match_id}")
                else:
                    logger.warning(f"⚠️ 采集失败: {match_id}")

                # 智能延迟，避免触发反爬
                if i < total_matches:
                    delay = delay_between_requests + (i % 2) * 0.5  # 2.0-2.5秒变化延迟
                    await asyncio.sleep(delay)

            except Exception as e:
                logger.error(f"❌ 采集比赛 {match_id} 时发生错误: {e}")
                continue

        logger.info(f"🎉 批量采集完成，成功: {len(results)}/{total_matches}")
        return results

    def get_stats(self) -> dict[str, Any]:
        """获取采集器统计信息."""
        stats = self.stats.copy()

        # 添加成功率
        if stats["requests_made"] > 0:
            stats["success_rate"] = stats["successful_requests"] / stats["requests_made"]
        else:
            stats["success_rate"] = 0.0

        return stats

    def _extract_deep_stats(self, content: dict[str, Any]) -> dict[str, Any]:
        """提取深度统计数据 - 射图谱、势头、教练、板凳评分等"""
        deep_stats = {
            "match_shotmap": [],  # 射图谱数据
            "match_momentum": [],  # 比赛势头数据
            "home_coach": None,  # 主队教练
            "away_coach": None,  # 客队教练
            "home_bench_rating": None,  # 主队板凳评分
            "away_bench_rating": None,  # 客队板凳评分
            "match_detailed_stats": {},  # 🆕 抓取所有详细统计数据 (Catch-All)
        }

        try:
            # 1. 提取射图谱数据
            if "shotmap" in content:
                shotmap_data = content["shotmap"]
                if isinstance(shotmap_data, dict) and "shots" in shotmap_data:
                    shots = shotmap_data["shots"]
                    if isinstance(shots, list):
                        deep_stats["match_shotmap"] = shots
                        logger.info(f"🎯 提取到 {len(shots)} 个射门数据")

            # 2. 提取比赛势头数据
            if "momentum" in content:
                momentum_data = content["momentum"]
                if isinstance(momentum_data, dict) and "data" in momentum_data:
                    momentum = momentum_data["data"]
                    if isinstance(momentum, list):
                        deep_stats["match_momentum"] = momentum
                        logger.info(f"📈 提取到 {len(momentum)} 个势头数据点")

            # 3. 提取教练信息
            if "content" in content and isinstance(content["content"], dict):
                content_data = content["content"]

                # 从general信息中查找教练数据
                if "general" in content_data:
                    general = content_data["general"]

                    # 检查主队教练
                    if "homeTeam" in general and isinstance(general["homeTeam"], dict):
                        home_team = general["homeTeam"]
                        if "coachName" in home_team:
                            deep_stats["home_coach"] = home_team["coachName"]
                        elif "managerName" in home_team:
                            deep_stats["home_coach"] = home_team["managerName"]

                    # 检查客队教练
                    if "awayTeam" in general and isinstance(general["awayTeam"], dict):
                        away_team = general["awayTeam"]
                        if "coachName" in away_team:
                            deep_stats["away_coach"] = away_team["coachName"]
                        elif "managerName" in away_team:
                            deep_stats["away_coach"] = away_team["managerName"]

                # 从lineups中查找教练信息（备用数据源）
                if (not deep_stats["home_coach"] or not deep_stats["away_coach"]) and "lineups" in content_data:
                    lineups = content_data["lineups"]
                    if isinstance(lineups, dict):
                        # 主队教练
                        if "home" in lineups and isinstance(lineups["home"], dict):
                            home_lineup = lineups["home"]
                            if "coach" in home_lineup and not deep_stats["home_coach"]:
                                deep_stats["home_coach"] = home_lineup["coach"]

                        # 客队教练
                        if "away" in lineups and isinstance(lineups["away"], dict):
                            away_lineup = lineups["away"]
                            if "coach" in away_lineup and not deep_stats["away_coach"]:
                                deep_stats["away_coach"] = away_lineup["coach"]

            # 4. 提取板凳评分（从球员评分中计算板凳球员平均分）
            if "content" in content and isinstance(content["content"], dict):
                content_data = content["content"]

                # 查找球员评分数据
                player_ratings = []

                # 可能的球员评分数据源位置
                rating_sources = [
                    ("players", "players"),
                    ("ratings", "ratings"),
                    ("playerStats", "playerStats"),
                    ("stats", "stats"),
                ]

                for source_key, nested_key in rating_sources:
                    if source_key in content_data:
                        source_data = content_data[source_key]
                        if isinstance(source_data, dict) and nested_key in source_data:
                            ratings = source_data[nested_key]
                            if isinstance(ratings, list):
                                player_ratings.extend(ratings)
                                break

                # 计算主客队板凳评分（假设板凳球员有特定标识）
                if player_ratings:
                    home_bench_ratings = []
                    away_bench_ratings = []

                    for player in player_ratings:
                        if isinstance(player, dict):
                            rating = player.get("rating") or player.get("averageRating") or player.get("score")
                            is_home = player.get("isHome") or player.get("team") == "home"
                            is_bench = player.get("position") == "bench" or player.get("substitute") is True

                            if rating and is_bench:
                                try:
                                    rating_value = float(rating)
                                    if is_home:
                                        home_bench_ratings.append(rating_value)
                                    else:
                                        away_bench_ratings.append(rating_value)
                                except (ValueError, TypeError):
                                    continue

                    # 计算平均板凳评分
                    if home_bench_ratings:
                        deep_stats["home_bench_rating"] = sum(home_bench_ratings) / len(home_bench_ratings)
                        logger.info(f"🏠 主队板凳评分: {deep_stats['home_bench_rating']:.2f}")

                    if away_bench_ratings:
                        deep_stats["away_bench_rating"] = sum(away_bench_ratings) / len(away_bench_ratings)
                        logger.info(f"✈️ 客队板凳评分: {deep_stats['away_bench_rating']:.2f}")

            # 记录提取结果摘要
            extracted_count = sum([1 for v in deep_stats.values() if v is not None and v != [] and v != ""])

            logger.info(f"📊 深度统计提取完成: {extracted_count}/6 项数据成功提取")

            # 🆕 6. 提取完整统计数据 (Catch-All Statistics)
            # 尝试从多个位置提取统计数据
            detailed_stats = {}
            stats_sources = [
                "stats",  # 主要统计数据
                "matchStats",  # 比赛统计数据
                "content",  # 根内容结构中的统计
                "matchFacts",  # 比赛详情中的统计
                "statistics",  # 备用统计字段
            ]

            for source_key in stats_sources:
                if source_key in content:
                    stats_data = content[source_key]
                    if isinstance(stats_data, dict) and stats_data:
                        # 检查是否包含关键足球统计数据指标
                        has_football_stats = any(
                            key.lower()
                            in [
                                "big chances",
                                "big chances created",
                                "goals",
                                "shots",
                                "passes",
                                "pass accuracy",
                                "tackles",
                                "dribbles",
                                "corners",
                                "fouls",
                                "offsides",
                                "possession",
                                "expected goals",
                                "xg",
                                "saves",
                                " interceptions",
                                "clearances",
                                "aerial duels",
                            ]
                            for key in stats_data.keys()
                        )

                        if has_football_stats or len(stats_data) > 10:
                            detailed_stats = stats_data
                            logger.info(f"📊 从 '{source_key}' 提取到完整统计数据: {len(stats_data)} 个字段")

                            # 检查包含的关键指标
                            key_stats = []
                            if "big chances" in str(stats_data).lower():
                                key_stats.append("Big Chances")
                            if "passes" in str(stats_data).lower():
                                key_stats.append("Passes")
                            if "tackles" in str(stats_data).lower():
                                key_stats.append("Tackles")
                            if "xg" in str(stats_data).lower() or "expected goals" in str(stats_data).lower():
                                key_stats.append("xG")

                            if key_stats:
                                logger.info(f"   🔍 关键指标: {', '.join(key_stats)}")
                            break

            deep_stats["match_detailed_stats"] = detailed_stats

            # 详细日志
            if deep_stats["home_coach"]:
                logger.info(f"👨‍💼 主队教练: {deep_stats['home_coach']}")
            if deep_stats["away_coach"]:
                logger.info(f"👨‍💼 客队教练: {deep_stats['away_coach']}")
            if deep_stats["match_shotmap"]:
                logger.info(f"🎯 射图谱数据: {len(deep_stats['match_shotmap'])} 个射门")
            if deep_stats["match_momentum"]:
                logger.info(f"📈 势头数据: {len(deep_stats['match_momentum'])} 个数据点")
            if detailed_stats:
                logger.info(f"📊 详细统计: {len(detailed_stats)} 个字段")

            return deep_stats

        except Exception as e:
            logger.error(f"❌ 深度统计提取失败: {e}")
            import traceback

            traceback.print_exc()
            return deep_stats

    async def close(self):
        """关闭采集器."""
        if self.client:
            await self.client.close()
            logger.info("🔐 HTTP客户端已关闭")

    async def __aenter__(self):
        """异步上下文管理器入口."""
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口."""
        await self.close()


# 便捷函数
async def create_fotmob_collector(**kwargs) -> FotMobCollector:
    """创建FotMob采集器."""
    return FotMobCollector(**kwargs)
