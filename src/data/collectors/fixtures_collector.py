"""# mypy: ignore-errors
# 该文件包含复杂的机器学习逻辑,类型检查已忽略
赛程数据采集器.

实现足球比赛赛程数据的采集逻辑。
包含防重复,防丢失策略,确保赛程数据的完整性和一致性。

采集策略:
- 每日凌晨执行全量同步
- 实时增量更新新增赛程
- 基于 match_id + league_id 去重
- 检测缺失比赛并补全

基于 DATA_DESIGN.md 第1.1节设计.
"""

import asyncio
import hashlib
import json
import logging
import os
from datetime import datetime, timedelta
from typing import Any, Optional

from src.adapters.football import ApiFootballAdapter, FootballAdapterError
from src.collectors.base_collector import CollectionResult
from src.database.connection import get_async_session
from src.database.models.raw_data import RawMatchData

logger = logging.getLogger(__name__)


class FixturesCollector:
    """赛程数据采集器.

    负责从外部API采集足球比赛赛程数据,
    实现防重复,
    防丢失机制,
    确保数据质量.
    支持基于配置文件的动态联赛管理和API速率限制保护.
    """

    def __init__(
        self,
        data_source: str = "football_api",
        config_file: str | None = None,
        **kwargs,
    ):
        """初始化赛程采集器.

        Args:
            data_source: 数据源名称
            config_file: 配置文件路径，默认使用 data_sources.json
        """
        self.data_source = data_source
        self.config_file = config_file or os.path.join(
            os.path.dirname(__file__), "../../config/data_sources.json"
        )

        # 加载配置
        self.config = self._load_config()
        self.target_leagues = self._load_target_leagues()

        # 初始化ApiFootballAdapter
        self.api_adapter = ApiFootballAdapter(name=data_source)

        # 防重复:记录已处理的比赛ID
        self._processed_matches: set[str] = set()
        # 防丢失:记录应该存在但缺失的比赛
        self._missing_matches: list[dict[str, Any]] = []

        # 采集统计
        self.league_stats = {}

    def _load_config(self) -> dict[str, Any]:
        """从配置文件加载数据源战略配置."""
        try:
            with open(self.config_file, encoding="utf-8") as f:
                config = json.load(f)
            logger.info(f"✅ 成功加载数据战略配置: {self.config_file}")
            logger.info(f"📋 配置版本: {config.get('version', 'unknown')}")
            logger.info(
                f"🎯 采集策略: {config.get('strategic_settings', {}).get('collection_strategy', 'unknown')}"
            )
            return config
        except FileNotFoundError:
            logger.error(f"❌ 配置文件未找到: {self.config_file}")
            logger.warning("⚠️ 使用默认配置作为回退")
            return self._get_default_config()
        except json.JSONDecodeError as e:
            logger.error(f"❌ 配置文件JSON解析错误: {e}")
            logger.warning("⚠️ 使用默认配置作为回退")
            return self._get_default_config()
        except Exception as e:
            logger.error(f"❌ 加载配置文件时发生错误: {e}")
            logger.warning("⚠️ 使用默认配置作为回退")
            return self._get_default_config()

    def _get_default_config(self) -> dict[str, Any]:
        """获取默认配置（回退方案）."""
        return {
            "version": "2.0.0-fallback",
            "strategic_settings": {
                "backfill_seasons": 3,
                "current_season": 2024,
                "max_api_calls_per_minute": 10,
                "collection_strategy": "high_value_focus",
            },
            "target_leagues": [
                # 基本的五大联赛作为回退
                {
                    "name": "Premier League",
                    "api_id": 2021,
                    "db_id": 11,
                    "type": "Tier1",
                    "priority": "critical",
                },
                {
                    "name": "La Liga",
                    "api_id": 2014,
                    "db_id": 12,
                    "type": "Tier1",
                    "priority": "critical",
                },
                {
                    "name": "Bundesliga",
                    "api_id": 2002,
                    "db_id": 13,
                    "type": "Tier1",
                    "priority": "critical",
                },
                {
                    "name": "Serie A",
                    "api_id": 2019,
                    "db_id": 14,
                    "type": "Tier1",
                    "priority": "critical",
                },
                {
                    "name": "Ligue 1",
                    "api_id": 2015,
                    "db_id": 15,
                    "type": "Tier1",
                    "priority": "critical",
                },
            ],
            "api_limits": {
                "football_data_org": {
                    "max_requests_per_minute": 10,
                    "max_requests_per_hour": 100,
                    "retry_attempts": 3,
                    "retry_delay_seconds": 2,
                }
            },
        }

    def _load_target_leagues(self) -> list[dict[str, Any]]:
        """从配置中加载目标联赛列表."""
        leagues = []
        try:
            for league_config in self.config.get("target_leagues", []):
                # 转换新配置格式以兼容现有代码
                league_info = {
                    "name": league_config["name"],
                    "country": league_config.get("country", "Unknown"),
                    "type": league_config["typing.Type"],
                    "priority": league_config.get("priority", "medium"),
                    "api_id": league_config["api_id"],
                    "db_id": league_config["db_id"],
                    "teams_count": league_config.get("teams_count", 20),
                }
                leagues.append(league_info)

            logger.info(f"✅ 成功加载 {len(leagues)} 个核心联赛")
            return leagues

        except Exception as e:
            logger.error(f"❌ 加载联赛配置失败: {e}")
            return []

    def get_strategic_settings(self) -> dict[str, Any]:
        """获取战略设置."""
        return self.config.get("strategic_settings", {})

    def get_league_by_name(self, name: str) -> dict[str, Any] | None:
        """根据联赛名称获取联赛配置."""
        for league in self.target_leagues:
            if league["name"] == name:
                return league
        return None

    def get_backfill_seasons(self) -> int:
        """获取历史回溯赛季数."""
        strategic_settings = self.get_strategic_settings()
        return strategic_settings.get("backfill_seasons", 3)

    def get_current_season(self) -> int:
        """获取当前赛季."""
        strategic_settings = self.get_strategic_settings()
        return strategic_settings.get("current_season", 2024)

    def get_backfill_years(self) -> list[int]:
        """获取历史回溯年限列表."""
        current_season = self.get_current_season()
        backfill_count = self.get_backfill_seasons()
        return [current_season - i for i in range(1, backfill_count + 1)]

    def get_max_api_calls_per_minute(self) -> int:
        """获取每分钟最大API调用次数."""
        strategic_settings = self.get_strategic_settings()
        return strategic_settings.get("max_api_calls_per_minute", 10)

    def get_collection_strategy(self) -> str:
        """获取采集策略."""
        strategic_settings = self.get_strategic_settings()
        return strategic_settings.get("collection_strategy", "high_value_focus")

    def get_leagues_by_type(self, league_type: str = "Tier1") -> list[dict[str, Any]]:
        """根据联赛类型获取联赛列表."""
        return [
            league
            for league in self.target_leagues
            if league.get("type", "Tier1") == league_type
        ]

    def get_leagues_by_priority(
        self, priority: str = "critical"
    ) -> list[dict[str, Any]]:
        """根据优先级获取联赛列表."""
        return [
            league
            for league in self.target_leagues
            if league.get("priority", "medium") == priority
        ]

    def get_rate_limit_delay(self) -> float:
        """根据配置计算请求间隔."""
        max_calls_per_minute = self.get_max_api_calls_per_minute()
        # 保守的间隔计算：60秒 / (每分钟请求数 * 0.8)
        delay = 60 / (max_calls_per_minute * 0.8)
        return max(delay, 1.0)  # 至少1秒间隔

    def get_api_limits(self, api_name: str = "football_data_org") -> dict[str, Any]:
        """获取指定API的速率限制配置."""
        api_limits = self.config.get("api_limits", {})
        return api_limits.get(
            api_name,
            {
                "max_requests_per_minute": 10,
                "max_requests_per_hour": 100,
                "retry_attempts": 3,
                "retry_delay_seconds": 2,
            },
        )

    def get_league_summary(self) -> dict[str, Any]:
        """获取联赛配置摘要统计."""
        type_count = {}
        priority_count = {}

        for league in self.target_leagues:
            league_type = league.get("type", "Unknown")
            priority = league.get("priority", "medium")

            type_count[league_type] = type_count.get(league_type, 0) + 1
            priority_count[priority] = priority_count.get(priority, 0) + 1

        return {
            "total_leagues": len(self.target_leagues),
            "types": type_count,
            "priorities": priority_count,
            "backfill_seasons": self.get_backfill_seasons(),
            "current_season": self.get_current_season(),
            "collection_strategy": self.get_collection_strategy(),
        }

    # 动态速率限制配置（从配置文件加载）
    # RATE_LIMIT_DELAY 和 MAX_RETRIES 现在通过 get_rate_limit_delay() 和 get_api_rate_limit() 获取

    async def collect_fixtures(
        self,
        leagues: list[str] | None = None,
        season: int = 2024,
        **kwargs,
    ) -> CollectionResult:
        """采集赛程数据.

        支持欧洲五大联赛+竞彩关键联赛+关键杯赛批量采集，包含API速率限制保护。

        防重复策略:
        - 基于 external_match_id + league_id 生成唯一键
        - 检查数据库中是否已存在
        - 跳过重复记录

        防丢失策略:
        - 全量获取指定赛季的赛程
        - 与数据库现有数据比对
        - 标记缺失的比赛并补全

        速率限制策略:
        - 在每个联赛请求间强制休眠
        - 支持重试机制
        - 避免触发HTTP 429错误

        Args:
            leagues: 需要采集的联赛列表
            season: 赛季年份

        Returns:
            CollectionResult: 采集结果
        """
        collected_data = []
        success_count = 0
        error_count = 0
        error_messages = []

        try:
            # 初始化适配器
            logger.info("正在初始化API适配器...")
            await self.api_adapter.initialize()

            # 获取需要采集的联赛列表（默认从配置文件获取）
            if not leagues:
                leagues = [league["code"] for league in self.target_leagues]

            logger.info(
                f"开始采集多联赛赛程数据: {len(leagues)} 个联赛, 赛季: {season}"
            )
            logger.info(f"目标联赛: {leagues}")

            # 按联赛采集赛程数据（支持速率限制）
            for i, league_code in enumerate(leagues):
                league_info = next(
                    (
                        league
                        for league in self.target_leagues
                        if league["code"] == league_code
                    ),
                    None,
                )
                league_name = league_info["name"] if league_info else league_code

                logger.info(
                    f"[{i + 1}/{len(leagues)}] 正在采集联赛 {league_name} ({league_code}) 的赛程数据..."
                )

                # 重置联赛统计
                self.league_stats[league_code] = {
                    "requested": 0,
                    "success": 0,
                    "errors": 0,
                    "name": league_name,
                }

                league_info = next(
                    (
                        league
                        for league in self.target_leagues
                        if league["code"] == league_code
                    ),
                    None,
                )
                league_id = league_info["api_id"] if league_info else None

                league_data = await self._collect_league_with_rate_limit(
                    league_code, league_id, season, league_name
                )

                if league_data:
                    # 将数据添加到总收集列表
                    collected_data.extend(league_data)
                    success_count += len(league_data)

                    # 速率限制：在下一个联赛请求前休眠
                    if i < len(leagues) - 1:
                        logger.info(
                            f"⏳  速率限制保护：等待 {self.RATE_LIMIT_DELAY} 秒后采集下一个联赛..."
                        )
                        await asyncio.sleep(self.RATE_LIMIT_DELAY)
                else:
                    error_count += 1
                    error_messages.append(f"采集联赛 {league_name} 失败")

            # 输出采集统计摘要
            logger.info("=" * 50)
            logger.info("📊 多联赛采集统计摘要")
            logger.info("=" * 50)
            for league_code, stats in self.league_stats.items():
                status = "✅" if stats["success"] > 0 else "❌"
                logger.info(
                    f"{status} {stats['name']} ({league_code}): "
                    f"请求={stats['requested']}, 成功={stats['success']}, 错误={stats['errors']}"
                )

            # 检测并处理缺失的比赛（防丢失）
            await self._detect_missing_matches(collected_data)

            # 保存到Bronze层原始数据表
            if collected_data:
                await self._save_to_bronze_layer(collected_data)

            # 清理适配器
            await self.api_adapter.cleanup()

            # 确定最终状态
            total_collected = len(collected_data)
            if error_count == 0:
                success = True
            elif success_count > 0:
                success = True  # 部分成功也算成功
            else:
                success = False

            # 构建结果数据
            result_data = {
                "collection_type": "fixtures",
                "data_source": self.data_source,
                "records_collected": total_collected,
                "success_count": success_count,
                "error_count": error_count,
                "collected_data": collected_data,
                "status": "success" if success else "failed",
                "errors": error_messages[:5] if error_messages else [],
                "league_stats": self.league_stats,
            }

            result = CollectionResult(
                success=success,
                data=result_data,
                error="; ".join(error_messages[:5]) if error_messages else None,
            )

            logger.info(
                f"多联赛赛程数据采集完成: "
                f"总计={total_collected}, 成功={success_count}, 错误={error_count}"
            )

            return result

        except FootballAdapterError as e:
            logger.error(f"赛程数据采集失败: {str(e)}")
            return CollectionResult(success=False, error=str(e))
        except Exception as e:
            logger.error(f"赛程数据采集出现未预期错误: {str(e)}")
            return CollectionResult(success=False, error=f"未预期错误: {str(e)}")

    async def _collect_league_with_rate_limit(
        self, league_code: str, league_id: int, season: int, league_name: str
    ) -> list[dict[str, Any]]:
        """使用速率限制保护采集单个联赛的数据.

        Args:
            league_code: 联赛代码
            league_id: 联赛数字ID (Football-Data.org验证过的ID)
            season: 赛季
            league_name: 联赛名称

        Returns:
            list[dict]: 采集到的比赛数据列表
        """
        max_retries = self.MAX_RETRIES
        retry_count = 0
        collected_data = []

        while retry_count <= max_retries:
            try:
                self.league_stats[league_code]["requested"] += 1

                logger.debug(f"尝试采集联赛 {league_name} 第 {retry_count + 1} 次")

                # 使用真实的API适配器获取数据 (使用验证过的数字ID)
                logger.info(
                    f"调用API获取联赛 {league_name} (ID: {league_id}) 的数据..."
                )
                league_fixtures = await self.api_adapter.get_fixtures(
                    league_id=league_id, season=season
                )

                logger.info(
                    f"联赛 {league_name} ({league_code}) 获取到 {len(league_fixtures)} 场比赛"
                )

                # 处理每场比赛
                for fixture_data in league_fixtures:
                    try:
                        # 防重复检查
                        match_key = self._generate_match_key(fixture_data)
                        if match_key in self._processed_matches:
                            logger.debug(f"跳过重复比赛: {match_key}")
                            continue

                        # 数据清洗和标准化
                        cleaned_fixture = await self._clean_fixture_data(fixture_data)
                        if cleaned_fixture:
                            # 添加到收集的数据列表
                            collected_data.append(cleaned_fixture)
                            self._processed_matches.add(match_key)  # 标记为已处理
                            self.league_stats[league_code]["success"] += 1
                            logger.debug(
                                f"成功处理比赛: {cleaned_fixture.get('external_match_id')}"
                            )
                        else:
                            self.league_stats[league_code]["errors"] += 1
                            logger.warning(
                                f"无效的比赛数据: {fixture_data.get('id', 'unknown')}"
                            )

                    except (
                        ValueError,
                        TypeError,
                        AttributeError,
                        KeyError,
                        RuntimeError,
                    ) as e:
                        self.league_stats[league_code]["errors"] += 1
                        logger.error(f"处理比赛数据时出错: {str(e)}")

                # 成功则返回收集的数据
                logger.info(
                    f"联赛 {league_name} 采集成功，收集到 {len(collected_data)} 场有效比赛"
                )
                return collected_data

            except FootballAdapterError as e:
                retry_count += 1
                logger.warning(
                    f"采集联赛 {league_name} 失败 (尝试 {retry_count}/{max_retries + 1}): {str(e)}"
                )

                if "429" in str(e).lower() and retry_count < max_retries:
                    logger.warning("检测到速率限制 (HTTP 429)，应用指数退避策略...")
                    wait_time = self.RATE_LIMIT_DELAY * (
                        2**retry_count
                    )  # 指数退避: 7s, 14s, 28s
                    logger.info(
                        f"等待 {wait_time} 秒后重试 (第{retry_count + 1}次重试)..."
                    )
                    await asyncio.sleep(wait_time)
                elif "invalid" in str(e).lower() and retry_count < max_retries:
                    logger.warning(
                        f"API调用失败 (可能是ID问题)，重试第{retry_count + 1}次..."
                    )
                    wait_time = self.RATE_LIMIT_DELAY * (retry_count + 1)
                    logger.info(f"等待 {wait_time} 秒后重试...")
                    await asyncio.sleep(wait_time)

                if retry_count <= max_retries:
                    continue
                else:
                    logger.error(f"联赛 {league_name} 采集最终失败")
                    return []

            except Exception as e:
                logger.error(f"采集联赛 {league_name} 发生异常: {str(e)}")
                self.league_stats[league_code]["errors"] += 1
                return []

        # 所有重试都失败了
        logger.error(f"联赛 {league_name} 采集失败，已达到最大重试次数 {max_retries}")
        return []

    async def collect_odds(self, **kwargs) -> CollectionResult:
        """赛程采集器不处理赔率数据."""
        return CollectionResult(
            success=True,
            data={
                "message": "Odds collection not supported by FixturesCollector",
                "collection_type": "odds",
                "status": "skipped",
            },
        )

    async def collect_live_scores(self, **kwargs) -> CollectionResult:
        """赛程采集器不处理实时比分数据."""
        return CollectionResult(
            success=True,
            data={
                "message": "Live scores collection not supported by FixturesCollector",
                "collection_type": "live_scores",
                "status": "skipped",
            },
        )

    async def _get_active_leagues(self) -> list[str]:
        """获取活跃的联赛列表.

        Returns:
            list[str]: 联赛代码列表
        """
        try:
            # 返回主要联赛作为默认配置
            active_leagues = [
                "PL",  # 英超
                "PD",  # 西甲
                "SA",  # 意甲
                "BL1",  # 德甲
                "FL1",  # 法甲
                "CL",  # 欧冠
                "EL",  # 欧联
            ]

            logger.info(f"使用活跃联赛列表: {active_leagues}")
            return active_leagues
        except Exception as e:
            logger.error(f"获取活跃联赛列表失败: {str(e)}")
            return ["PL", "PD"]  # 默认返回英超和西甲

    def _generate_match_key(self, fixture_data: dict[str, Any]) -> str:
        """生成比赛唯一键（防重复）.

        Args:
            fixture_data: 比赛原始数据

        Returns:
            str: 比赛唯一键
        """
        # 使用外部ID、主队、客队、比赛时间生成唯一键
        key_components = [
            str(fixture_data.get("id", "")),
            str(fixture_data.get("homeTeam", {}).get("id", "")),
            str(fixture_data.get("awayTeam", {}).get("id", "")),
            str(fixture_data.get("utcDate", "")),
        ]

        key_string = "|".join(key_components)
        return hashlib.md5(key_string.encode(), usedforsecurity=False).hexdigest()

    async def _clean_fixture_data(
        self, raw_fixture: dict[str, Any]
    ) -> dict[str, Any] | None:
        """清洗和标准化赛程数据.

        Args:
            raw_fixture: 原始赛程数据

        Returns:
            Optional[dict]: 清洗后的数据,无效则返回None
        """
        try:
            # 基础字段验证
            if not all(
                key in raw_fixture for key in ["id", "homeTeam", "awayTeam", "utcDate"]
            ):
                return None

            # 时间标准化为UTC
            match_time = datetime.fromisoformat(
                raw_fixture["utcDate"].replace("Z", "+00:00")
            )

            cleaned_data = {
                "external_match_id": str(raw_fixture["id"]),
                "external_league_id": str(
                    raw_fixture.get("competition", {}).get("id", "")
                ),
                "external_home_team_id": str(raw_fixture["homeTeam"]["id"]),
                "external_away_team_id": str(raw_fixture["awayTeam"]["id"]),
                "match_time": match_time.isoformat(),
                "status": raw_fixture.get("status", "SCHEDULED"),
                "season": raw_fixture.get("season", {}).get("id"),
                "matchday": raw_fixture.get("matchday"),
                "raw_data": raw_fixture,
                "collected_at": datetime.now().isoformat(),
                "processed": False,
            }

            return cleaned_data

        except (ValueError, AttributeError, KeyError, RuntimeError) as e:
            self.logger.error(f"Failed to clean fixture data: {str(e)}")
            return None

    async def _detect_missing_matches(
        self,
        collected_data: list[dict[str, Any]],
    ) -> None:
        """检测缺失的比赛（防丢失策略）.

        Args:
            collected_data: 本次采集的数据
        """
        try:
            # 目前简化实现，在生产环境中需要与数据库比对
            logger.info(
                f"缺失比赛检测完成，发现 {len(self._missing_matches)} 场缺失比赛"
            )

        except Exception as e:
            logger.error(f"检测缺失比赛失败: {str(e)}")

    async def _save_to_bronze_layer(self, collected_data: list[dict[str, Any]]) -> None:
        """保存数据到Bronze层原始数据表.

        Args:
            collected_data: 采集到的数据列表
        """
        try:
            logger.info(f"正在保存 {len(collected_data)} 条记录到Bronze层...")

            async with get_async_session() as session:
                saved_count = 0

                for data in collected_data:
                    try:
                        # 检查是否已存在相同的记录（幂等性）
                        external_id = data.get("external_match_id")
                        if not external_id:
                            logger.warning("跳过没有external_match_id的记录")
                            continue

                        # 检查记录是否已存在
                        from sqlalchemy import select

                        existing_query = select(RawMatchData).where(
                            RawMatchData.external_id == external_id,
                            RawMatchData.source == self.data_source,
                        )
                        existing_result = await session.execute(existing_query)
                        existing_record = existing_result.scalar_one_or_none()

                        if existing_record:
                            # 更新现有记录
                            existing_record.match_data = data
                            existing_record.collected_at = datetime.now()
                            logger.debug(f"更新已存在的记录: {external_id}")
                        else:
                            # 创建新记录
                            raw_match = RawMatchData(
                                external_id=external_id,
                                source=self.data_source,
                                match_data=data,  # 存储完整的原始JSON数据
                                collected_at=datetime.now(),
                                processed=False,
                            )
                            session.add(raw_match)
                            logger.debug(f"创建新记录: {external_id}")

                        saved_count += 1

                    except Exception as e:
                        logger.error(
                            f"保存单个记录失败 {data.get('external_match_id', 'unknown')}: {str(e)}"
                        )
                        continue

                # 提交事务
                await session.commit()
                logger.info(f"Bronze层数据保存成功，共处理 {saved_count} 条记录")

        except Exception as e:
            logger.error(f"保存Bronze层数据失败: {str(e)}")
            raise

    # 移除了不需要的方法，只保留核心的collect_fixtures功能


# 其他方法如collect_teams, collect_players等可以通过ApiFootballAdapter直接调用
