"""
V38.0 "特种渗透版" Odds API 客户端
==================================
基于 StealthClient 的重构实现，补齐 TLS/JA3 指纹伪装。

核心改进:
1. 使用 curl_cffi (AsyncSession) 替代 aiohttp
2. 强制启用 impersonate="chrome131"
3. 完整的 sec-ch-ua 请求头序列
4. 集成 TeamAliasResolver 进行队名对齐
5. 代理池默认从统一配置系统加载
"""

from __future__ import annotations

from datetime import UTC, datetime
import logging
from typing import TYPE_CHECKING, Any, cast

import psycopg2

from src.config_unified import get_settings
from src.core.matching.team_alias_resolver import TeamAliasResolver, get_resolver
from src.infrastructure.network.stealth_client import StealthClient, get_stealth_client

if TYPE_CHECKING:
    from types import TracebackType

logger = logging.getLogger(__name__)

HTTP_OK = 200
ODDSPORTAL_MATCH_URL_TEMPLATE = "https://www.oddsportal.com/soccer/match/{match_id}/"
ODDSPORTAL_REFERER = "https://www.oddsportal.com/soccer/"
MATCH_LIST_URL_TEMPLATE = "https://api.example.com/matches?league={league}&date={date}"
TLS_FINGERPRINT_URL = "https://tls.browserleaks.com/json"
HTTPBIN_GET_URL = "https://httpbin.org/get"
PREMIUM_DATA_QUALITY = "PREMIUM-GOLD"
STANDARD_DATA_QUALITY = "STANDARD"
SOURCE_CHANNEL_API = "api"


def _utc_now_iso() -> str:
    """返回 UTC ISO 时间戳。"""
    return datetime.now(UTC).isoformat()


def _build_default_proxy_pool() -> list[str]:
    """从统一配置系统构造代理池。"""
    settings = get_settings()
    ports = [int(port.strip()) for port in settings.proxy_ports.split(",") if port.strip()]
    template = settings.proxy_server_template
    return [template.format(port=port) for port in ports]


def _safe_response_json(response: Any) -> dict[str, Any]:
    """尽量把响应转换为 JSON 字典。"""
    payload = response.json()
    if isinstance(payload, dict):
        return cast("dict[str, Any]", payload)
    return {}


class OddsAPIClientV38:
    """V38.0 特种渗透版 Odds API 客户端。"""

    def __init__(self, proxy_pool: list[str] | None = None) -> None:
        self.stealth_client: StealthClient | None = None
        self.team_resolver: TeamAliasResolver | None = None
        self.proxy_pool = proxy_pool or _build_default_proxy_pool()
        self.proxy_index = 0

    async def __aenter__(self) -> OddsAPIClientV38:
        self.stealth_client = await get_stealth_client()
        self.team_resolver = get_resolver()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        if self.stealth_client is not None:
            await self.stealth_client.close()

    def _require_client(self) -> StealthClient:
        if self.stealth_client is None:
            raise RuntimeError("StealthClient 尚未初始化，请使用 async with 上下文。")
        return self.stealth_client

    def _require_resolver(self) -> TeamAliasResolver:
        if self.team_resolver is None:
            raise RuntimeError("TeamAliasResolver 尚未初始化，请使用 async with 上下文。")
        return self.team_resolver

    def _get_next_proxy(self) -> str | None:
        if not self.proxy_pool:
            return None
        proxy = self.proxy_pool[self.proxy_index]
        self.proxy_index = (self.proxy_index + 1) % len(self.proxy_pool)
        return proxy

    async def fetch_odds(self, match_id: str, source: str = "oddsportal") -> dict[str, Any] | None:
        """获取比赛赔率数据。"""
        client = self._require_client()
        proxy = self._get_next_proxy()
        url = ODDSPORTAL_MATCH_URL_TEMPLATE.format(match_id=match_id)

        try:
            response = await client.fetch(
                url,
                proxy=proxy,
                headers={
                    "referer": ODDSPORTAL_REFERER,
                    "accept": "application/json, text/plain, */*",
                },
            )

            if response.status_code != HTTP_OK:
                logger.warning(
                    "获取赔率失败: match_id=%s status=%s", match_id, response.status_code
                )
                return None

            content_type = str(response.headers.get("content-type", ""))
            data = _safe_response_json(response) if "json" in content_type else {}

            return {
                "match_id": match_id,
                "source": source,
                "data": data,
                "fetched_at": _utc_now_iso(),
                "proxy_used": proxy,
            }
        except Exception:
            logger.exception("获取赔率异常: match_id=%s source=%s", match_id, source)
            return None

    async def fetch_match_list(self, league: str, date: str) -> list[dict[str, Any]]:
        """获取比赛列表。"""
        client = self._require_client()
        resolver = self._require_resolver()
        standard_league = resolver.resolve(league) or league
        url = MATCH_LIST_URL_TEMPLATE.format(league=standard_league, date=date)

        try:
            response = await client.fetch(url, proxy=self._get_next_proxy())
            if response.status_code != HTTP_OK:
                logger.warning(
                    "获取比赛列表失败: league=%s date=%s status=%s",
                    standard_league,
                    date,
                    response.status_code,
                )
                return []

            payload = _safe_response_json(response)
            raw_matches = payload.get("matches")
            matches = (
                cast("list[dict[str, Any]]", raw_matches) if isinstance(raw_matches, list) else []
            )

            for match in matches:
                home_team = str(match.get("home_team", ""))
                away_team = str(match.get("away_team", ""))
                match["home_team_std"] = resolver.resolve(home_team)
                match["away_team_std"] = resolver.resolve(away_team)

        except Exception:
            logger.exception("获取比赛列表异常: league=%s date=%s", standard_league, date)
            return []
        else:
            return matches

    async def validate_tls_fingerprint(self) -> dict[str, Any]:
        """验证当前 TLS 指纹是否与 Chrome 131 一致。"""
        result = await self._require_client().verify_fingerprint()
        expected_ja3 = StealthClient.CHROME_131_JA3_HASH
        actual_ja3 = str(result.get("ja3n_hash", "unknown"))

        return {
            "valid": actual_ja3 == expected_ja3,
            "expected_ja3": expected_ja3,
            "actual_ja3": actual_ja3,
            "tls_version": result.get("tls_version"),
            "user_agent": result.get("user_agent"),
            "timestamp": _utc_now_iso(),
        }

    async def stealth_health_check(self) -> dict[str, Any]:
        """执行全面的隐身健康检查。"""
        client = self._require_client()
        resolver = self._require_resolver()
        tls_check = await self.validate_tls_fingerprint()

        try:
            response = await client.fetch(HTTPBIN_GET_URL, proxy=self._get_next_proxy())
            latency_raw = getattr(response, "elapsed", 0)
            latency_ms = int(latency_raw) if isinstance(latency_raw, (int, float)) else 0
            http_check = {
                "status": "ok",
                "status_code": response.status_code,
                "latency_ms": latency_ms,
            }
        except Exception as exc:
            logger.exception("隐身健康检查 HTTP 连通性异常")
            http_check = {"status": "error", "error": str(exc)}

        resolver_check = {
            "teams_count": len(resolver.get_all_teams()),
            "test_match": resolver.resolve("Man Utd"),
        }
        proxy_check = {"pool_size": len(self.proxy_pool), "current_index": self.proxy_index}

        logger.info(
            "V38 健康检查: tls=%s http=%s proxy_pool=%s",
            tls_check["valid"],
            http_check["status"],
            proxy_check["pool_size"],
        )

        return {
            "tls_fingerprint": tls_check,
            "http_connectivity": http_check,
            "resolver": resolver_check,
            "proxy_pool": proxy_check,
            "overall_status": "healthy"
            if tls_check["valid"] and http_check["status"] == "ok"
            else "degraded",
        }

    async def save_odds_to_db(
        self, match_id: str, provider: str, odds_data: dict[str, Any]
    ) -> bool:
        """保存赔率数据到数据库。"""
        settings = get_settings()
        db_config = {
            "host": settings.db_host,
            "port": settings.db_port,
            "database": settings.db_name,
            "user": settings.db_user,
            "password": settings.db_password.get_secret_value(),
        }

        try:
            conn = psycopg2.connect(**db_config)
            cursor = conn.cursor()

            opening = odds_data.get("opening", {})
            closing = odds_data.get("closing", {})
            current = odds_data.get("current", closing)

            odds_home_open = opening.get("home") if isinstance(opening, dict) else None
            odds_draw_open = opening.get("draw") if isinstance(opening, dict) else None
            odds_away_open = opening.get("away") if isinstance(opening, dict) else None
            opening_at = opening.get("timestamp") if isinstance(opening, dict) else None

            odds_home_close = closing.get("home") if isinstance(closing, dict) else None
            odds_draw_close = closing.get("draw") if isinstance(closing, dict) else None
            odds_away_close = closing.get("away") if isinstance(closing, dict) else None
            closing_at = closing.get("timestamp") if isinstance(closing, dict) else None

            odds_home_current = current.get("home") if isinstance(current, dict) else None
            odds_draw_current = current.get("draw") if isinstance(current, dict) else None
            odds_away_current = current.get("away") if isinstance(current, dict) else None
            current_at = current.get("timestamp") if isinstance(current, dict) else None

            odds_drop_home = None
            odds_drop_draw = None
            odds_drop_away = None
            market_margin = None

            if odds_home_open and odds_home_close:
                odds_drop_home = round((odds_home_open - odds_home_close) / odds_home_open, 4)
            if odds_draw_open and odds_draw_close:
                odds_drop_draw = round((odds_draw_open - odds_draw_close) / odds_draw_open, 4)
            if odds_away_open and odds_away_close:
                odds_drop_away = round((odds_away_open - odds_away_close) / odds_away_open, 4)
            if odds_home_close and odds_draw_close and odds_away_close:
                market_margin = round(
                    (1 / odds_home_close + 1 / odds_draw_close + 1 / odds_away_close) - 1,
                    4,
                )

            sql = """
            INSERT INTO match_odds (
                match_id, provider,
                odds_home_open, odds_draw_open, odds_away_open, opening_at,
                odds_home_close, odds_draw_close, odds_away_close, closing_at,
                odds_home_current, odds_draw_current, odds_away_current, current_at,
                odds_drop_home, odds_drop_draw, odds_drop_away, market_margin,
                source_channel, data_quality, collected_at
            ) VALUES (
                %s, %s,
                %s, %s, %s, %s,
                %s, %s, %s, %s,
                %s, %s, %s, %s,
                %s, %s, %s, %s,
                %s, %s, NOW()
            )
            ON CONFLICT (match_id, provider) DO UPDATE SET
                odds_home_open = EXCLUDED.odds_home_open,
                odds_draw_open = EXCLUDED.odds_draw_open,
                odds_away_open = EXCLUDED.odds_away_open,
                opening_at = EXCLUDED.opening_at,
                odds_home_close = EXCLUDED.odds_home_close,
                odds_draw_close = EXCLUDED.odds_draw_close,
                odds_away_close = EXCLUDED.odds_away_close,
                closing_at = EXCLUDED.closing_at,
                odds_home_current = EXCLUDED.odds_home_current,
                odds_draw_current = EXCLUDED.odds_draw_current,
                odds_away_current = EXCLUDED.odds_away_current,
                current_at = EXCLUDED.current_at,
                odds_drop_home = EXCLUDED.odds_drop_home,
                odds_drop_draw = EXCLUDED.odds_drop_draw,
                odds_drop_away = EXCLUDED.odds_drop_away,
                market_margin = EXCLUDED.market_margin,
                source_channel = EXCLUDED.source_channel,
                data_quality = EXCLUDED.data_quality,
                collected_at = NOW()
            """

            cursor.execute(
                sql,
                (
                    match_id,
                    provider,
                    odds_home_open,
                    odds_draw_open,
                    odds_away_open,
                    opening_at,
                    odds_home_close,
                    odds_draw_close,
                    odds_away_close,
                    closing_at,
                    odds_home_current,
                    odds_draw_current,
                    odds_away_current,
                    current_at,
                    odds_drop_home,
                    odds_drop_draw,
                    odds_drop_away,
                    market_margin,
                    SOURCE_CHANNEL_API,
                    PREMIUM_DATA_QUALITY
                    if odds_home_open is not None and odds_home_close is not None
                    else STANDARD_DATA_QUALITY,
                ),
            )

            conn.commit()
            logger.info(
                "赔率已落库: match_id=%s provider=%s current=(%s,%s,%s)",
                match_id,
                provider,
                odds_home_current,
                odds_draw_current,
                odds_away_current,
            )
        except Exception:
            logger.exception("数据库保存失败: match_id=%s provider=%s", match_id, provider)
            return False
        else:
            return True
        finally:
            if "cursor" in locals():
                cursor.close()
            if "conn" in locals():
                conn.close()


async def fetch_odds_v38(match_id: str, proxy: str | None = None) -> dict[str, Any] | None:
    """快捷函数：使用 V38 客户端获取赔率。"""
    async with OddsAPIClientV38(proxy_pool=[proxy] if proxy else None) as client:
        return await client.fetch_odds(match_id)


async def health_check_v38() -> dict[str, Any]:
    """快捷函数：执行 V38 健康检查。"""
    async with OddsAPIClientV38() as client:
        return await client.stealth_health_check()


class OddsAPIClient:
    """向后兼容包装器，将旧接口转发到 V38 实现。"""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self._v38: OddsAPIClientV38 | None = None
        self._args = args
        self._kwargs = kwargs

    async def __aenter__(self) -> OddsAPIClient:
        self._v38 = OddsAPIClientV38(*self._args, **self._kwargs)
        await self._v38.__aenter__()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        if self._v38 is not None:
            await self._v38.__aexit__(exc_type, exc_val, exc_tb)

    async def fetch_odds(self, *args: Any, **kwargs: Any) -> dict[str, Any] | None:
        if self._v38 is None:
            raise RuntimeError("OddsAPIClient 尚未初始化，请使用 async with 上下文。")
        return await self._v38.fetch_odds(*args, **kwargs)

    async def fetch_match_list(self, *args: Any, **kwargs: Any) -> list[dict[str, Any]]:
        if self._v38 is None:
            raise RuntimeError("OddsAPIClient 尚未初始化，请使用 async with 上下文。")
        return await self._v38.fetch_match_list(*args, **kwargs)
