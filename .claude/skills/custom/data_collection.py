#!/usr/bin/env python3
"""
数据采集 Claude Skill
Professional Web Scraping and Data Collection Skill for Football Prediction

功能:
- 智能API认证头获取和更新
- 多数据源采集策略
- 反爬虫检测和绕过
- 数据质量验证
- 采集性能优化

作者: FootballPrediction Team
版本: v1.0.0
"""

import asyncio
import json
import logging
import os
import random
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Any

# 添加项目路径
sys.path.insert(0, "/home/user/projects/FootballPrediction")

import aiohttp
import asyncpg

from src.config_unified import get_settings

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class AuthHeader:
    """API认证头数据结构"""

    x_mas: str
    x_foo: str
    user_agent: str
    source: str
    created_at: datetime
    last_success: datetime | None = None
    success_count: int = 0
    failure_count: int = 0


@dataclass
class CollectionResult:
    """采集结果数据结构"""

    success: bool
    data_size: int
    matches_found: int
    pl_matches: int
    duration_seconds: float
    error_message: str | None = None
    response_headers: dict[str, str] | None = None


class DataCollectionSkill:
    """
    专业数据采集技能

    核心能力:
    1. 智能API认证管理
    2. 多策略反爬虫绕过
    3. 数据质量验证
    4. 性能监控和优化
    5. 自动重试和错误恢复
    """

    def __init__(self):
        """初始化数据采集技能"""
        self.settings = get_settings()
        self.current_headers: AuthHeader | None = None
        self.session: aiohttp.ClientSession | None = None
        self.db_pool: asyncpg.Pool | None = None

        # 采集配置
        self.max_retries = 3
        self.base_delay = 1.0
        self.max_delay = 5.0
        self.timeout = 30

        # 用户代理池
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:109.0) Gecko/20100101 Firefox/121.0",
        ]

        logger.info("🔧 数据采集Claude Skill初始化完成")

    async def initialize(self):
        """初始化连接"""
        # HTTP客户端
        if not self.session or self.session.closed:
            self.session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self.timeout),
                connector=aiohttp.TCPConnector(limit=10, limit_per_host=5),
            )

        # 数据库连接
        if not self.db_pool:
            self.db_pool = await asyncpg.create_pool(
                self.settings.database.get_connection_string(), min_size=2, max_size=10
            )

        # 加载当前认证头
        await self.load_current_headers()

        logger.info("✅ 数据采集技能连接初始化完成")

    async def close(self):
        """关闭资源"""
        if self.session and not self.session.closed:
            await self.session.close()
        if self.db_pool:
            await self.db_pool.close()
        logger.info("🔐 数据采集技能资源已关闭")

    async def __aenter__(self):
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def load_current_headers(self):
        """从环境变量加载当前认证头"""
        x_mas = os.getenv("FOTMOB_X_MAS_HEADER")
        x_foo = os.getenv("FOTMOB_X_FOO_HEADER")

        if x_mas and x_foo:
            self.current_headers = AuthHeader(
                x_mas=x_mas,
                x_foo=x_foo,
                user_agent=random.choice(self.user_agents),
                source="environment",
                created_at=datetime.now(),
            )
            logger.info("📥 已从环境变量加载认证头")
        else:
            logger.warning("⚠️ 环境变量中未找到认证头")

    async def validate_headers(self) -> tuple[bool, str]:
        """
        验证当前认证头是否有效

        Returns:
            (is_valid, message)
        """
        if not self.current_headers:
            return False, "没有可用的认证头"

        try:
            headers = self._build_headers()

            # 测试API连接
            test_url = "https://www.fotmob.com/api/matches"
            test_date = datetime.now().strftime("%Y%m%d")
            params = {"date": test_date}

            async with self.session.get(test_url, headers=headers, params=params) as response:
                if response.status == 200:
                    # 尝试解析JSON
                    data = await response.json()
                    self.current_headers.last_success = datetime.now()
                    self.current_headers.success_count += 1

                    # 更新环境变量
                    os.environ["FOTMOB_X_MAS_HEADER"] = self.current_headers.x_mas
                    os.environ["FOTMOB_X_FOO_HEADER"] = self.current_headers.x_foo

                    return True, f"认证头有效 (成功次数: {self.current_headers.success_count})"
                else:
                    self.current_headers.failure_count += 1
                    return False, f"认证头无效 (状态码: {response.status})"

        except Exception as e:
            self.current_headers.failure_count += 1
            return False, f"认证头验证异常: {str(e)}"

    async def update_headers_from_browser(self, headers_dict: dict[str, str]) -> bool:
        """
        从浏览器捕获的请求头更新认证信息

        Args:
            headers_dict: 浏览器开发者工具捕获的headers

        Returns:
            是否更新成功
        """
        try:
            x_mas = headers_dict.get("x-mas")
            x_foo = headers_dict.get("x-foo")
            user_agent = headers_dict.get("user-agent", "")

            if not x_mas or not x_foo:
                logger.error("❌ 缺少必要的认证头 (x-mas 或 x-foo)")
                return False

            # 创建新的认证头
            new_headers = AuthHeader(
                x_mas=x_mas, x_foo=x_foo, user_agent=user_agent, source="browser_captured", created_at=datetime.now()
            )

            # 验证新头
            old_headers = self.current_headers
            self.current_headers = new_headers

            is_valid, message = await self.validate_headers()

            if is_valid:
                # 保存到环境变量
                await self._save_headers_to_env()

                # 保存到数据库记录
                await self._save_headers_to_db()

                logger.info(f"✅ 认证头更新成功: {message}")
                return True
            else:
                # 恢复旧头
                self.current_headers = old_headers
                logger.error(f"❌ 新认证头验证失败: {message}")
                return False

        except Exception as e:
            logger.error(f"❌ 更新认证头失败: {e}")
            return False

    def _build_headers(self) -> dict[str, str]:
        """构建完整的请求头"""
        if not self.current_headers:
            raise ValueError("没有可用的认证头")

        return {
            "User-Agent": self.current_headers.user_agent,
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Referer": "https://www.fotmob.com/",
            "Origin": "https://www.fotmob.com",
            "x-mas": self.current_headers.x_mas,
            "x-foo": self.current_headers.x_foo,
        }

    async def _save_headers_to_env(self):
        """保存认证头到环境变量"""
        if self.current_headers:
            os.environ["FOTMOB_X_MAS_HEADER"] = self.current_headers.x_mas
            os.environ["FOTMOB_X_FOO_HEADER"] = self.current_headers.x_foo
            logger.info("💾 认证头已保存到环境变量")

    async def _save_headers_to_db(self):
        """保存认证头到数据库记录"""
        try:
            async with self.db_pool.acquire() as conn:
                # 创建认证头记录表（如果不存在）
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS api_auth_headers (
                        id SERIAL PRIMARY KEY,
                        source VARCHAR(50),
                        x_mas TEXT NOT NULL,
                        x_foo TEXT NOT NULL,
                        user_agent TEXT,
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                        last_success TIMESTAMP WITH TIME ZONE,
                        success_count INTEGER DEFAULT 0,
                        failure_count INTEGER DEFAULT 0,
                        is_active BOOLEAN DEFAULT TRUE
                    )
                """)

                # 插入新记录
                await conn.execute(
                    """
                    INSERT INTO api_auth_headers
                    (source, x_mas, x_foo, user_agent, last_success, success_count)
                    VALUES ($1, $2, $3, $4, $5, $6)
                """,
                    self.current_headers.source,
                    self.current_headers.x_mas,
                    self.current_headers.x_foo,
                    self.current_headers.user_agent,
                    self.current_headers.last_success,
                    self.current_headers.success_count,
                )

                logger.info("💾 认证头已保存到数据库")

        except Exception as e:
            logger.error(f"❌ 保存认证头到数据库失败: {e}")

    async def collect_with_retry(self, url: str, params: dict | None = None) -> CollectionResult:
        """
        带重试机制的数据采集

        Args:
            url: API URL
            params: 请求参数

        Returns:
            CollectionResult
        """
        start_time = time.time()

        for attempt in range(self.max_retries):
            try:
                headers = self._build_headers()

                # 智能延迟
                if attempt > 0:
                    delay = self.base_delay * (2**attempt) + random.uniform(0, 1)
                    delay = min(delay, self.max_delay)
                    logger.info(f"⏱️ 第{attempt + 1}次重试，延迟 {delay:.1f}秒")
                    await asyncio.sleep(delay)

                async with self.session.get(url, headers=headers, params=params) as response:
                    duration = time.time() - start_time

                    if response.status == 200:
                        data = await response.json()
                        data_size = len(json.dumps(data))

                        # 分析数据
                        matches_found = self._count_matches(data)
                        pl_matches = self._count_pl_matches(data)

                        # 更新成功统计
                        if self.current_headers:
                            self.current_headers.last_success = datetime.now()
                            self.current_headers.success_count += 1

                        return CollectionResult(
                            success=True,
                            data_size=data_size,
                            matches_found=matches_found,
                            pl_matches=pl_matches,
                            duration_seconds=duration,
                            response_headers=dict(response.headers),
                        )

                    elif response.status == 404:
                        logger.warning("⚠️ API返回404 - 可能认证头失效")
                        if attempt == self.max_retries - 1:
                            return CollectionResult(
                                success=False,
                                data_size=0,
                                matches_found=0,
                                pl_matches=0,
                                duration_seconds=duration,
                                error_message="API返回404，认证头可能已失效",
                            )

                    else:
                        logger.warning(f"⚠️ API返回状态码: {response.status}")

            except Exception as e:
                logger.error(f"❌ 采集异常 (尝试{attempt + 1}): {e}")
                if attempt == self.max_retries - 1:
                    duration = time.time() - start_time
                    return CollectionResult(
                        success=False,
                        data_size=0,
                        matches_found=0,
                        pl_matches=0,
                        duration_seconds=duration,
                        error_message=str(e),
                    )

        duration = time.time() - start_time
        return CollectionResult(
            success=False,
            data_size=0,
            matches_found=0,
            pl_matches=0,
            duration_seconds=duration,
            error_message="达到最大重试次数",
        )

    def _count_matches(self, data: dict) -> int:
        """统计比赛数量"""
        if "matches" in data:
            return len(data["matches"])
        elif "leagues" in data:
            total = 0
            for league in data["leagues"]:
                if "matches" in league:
                    total += len(league["matches"])
            return total
        return 0

    def _count_pl_matches(self, data: dict) -> int:
        """统计英超比赛数量"""
        if "leagues" in data:
            for league in data["leagues"]:
                league_name = league.get("name", "").lower()
                if "premier league" in league_name or "english premier" in league_name or league.get("id") == 47:
                    return len(league.get("matches", []))
        return 0

    async def get_collection_status(self) -> dict[str, Any]:
        """获取采集状态汇总"""
        try:
            async with self.db_pool.acquire() as conn:
                # 获取matches表统计
                query = """
                    SELECT
                        COUNT(*) as total_matches,
                        COUNT(CASE WHEN collection_status = 'completed' THEN 1 END) as completed,
                        COUNT(CASE WHEN collection_status = 'pending' THEN 1 END) as pending,
                        COUNT(CASE WHEN collection_status = 'failed' THEN 1 END) as failed
                    FROM matches
                    WHERE league_name ILIKE '%premier%' OR league_id = 47
                """
                stats = await conn.fetchrow(query)

                # 获取L2数据统计
                l2_query = """
                    SELECT COUNT(*) as total_l2_data
                    FROM raw_match_data rmd
                    JOIN matches m ON rmd.external_id = m.external_id
                    WHERE m.league_name ILIKE '%premier%' OR m.league_id = 47
                """
                l2_stats = await conn.fetchrow(l2_query)

                return {
                    "headers_status": {
                        "current_source": self.current_headers.source if self.current_headers else "none",
                        "success_count": self.current_headers.success_count if self.current_headers else 0,
                        "failure_count": self.current_headers.failure_count if self.current_headers else 0,
                        "last_success": self.current_headers.last_success.isoformat()
                        if self.current_headers and self.current_headers.last_success
                        else None,
                    },
                    "collection_stats": {
                        "total_matches": stats["total_matches"],
                        "completed": stats["completed"],
                        "pending": stats["pending"],
                        "failed": stats["failed"],
                        "l2_data_count": l2_stats["total_l2_data"],
                        "completion_rate": round(stats["completed"] / max(stats["total_matches"], 1) * 100, 2),
                    },
                }

        except Exception as e:
            logger.error(f"❌ 获取采集状态失败: {e}")
            return {"error": str(e)}

    async def smart_detect_headers(self) -> bool:
        """
        智能检测有效认证头

        Returns:
            是否检测到有效头
        """
        logger.info("🔍 启动智能认证头检测...")

        # 这里可以实现更复杂的检测逻辑
        # 例如：从多个数据源获取，使用机器学习等

        # 目前只验证现有头
        is_valid, message = await self.validate_headers()

        if is_valid:
            logger.info(f"✅ 当前认证头有效: {message}")
            return True
        else:
            logger.warning(f"❌ 当前认证头无效: {message}")
            logger.info("📋 请手动从浏览器开发者工具获取新的认证头:")
            logger.info("   1. 访问 https://www.fotmob.com")
            logger.info("   2. 打开开发者工具 (F12)")
            logger.info("   3. 切换到 Network 标签")
            logger.info("   4. 浏览页面，找到 /api/matches 请求")
            logger.info("   5. 复制 Request Headers 中的 x-mas 和 x-foo")
            return False


# 便捷接口函数
async def create_data_collection_skill() -> DataCollectionSkill:
    """创建数据采集技能实例"""
    skill = DataCollectionSkill()
    await skill.initialize()
    return skill


# Claude Skill接口
async def test_api_headers() -> dict[str, Any]:
    """
    测试API认证头 (Claude Skill接口)

    Returns:
        测试结果
    """
    async with DataCollectionSkill() as skill:
        is_valid, message = await skill.validate_headers()
        return {
            "valid": is_valid,
            "message": message,
            "headers_source": skill.current_headers.source if skill.current_headers else "none",
        }


async def update_api_headers(headers_dict: dict[str, str]) -> dict[str, Any]:
    """
    更新API认证头 (Claude Skill接口)

    Args:
        headers_dict: 浏览器捕获的headers

    Returns:
        更新结果
    """
    async with DataCollectionSkill() as skill:
        success = await skill.update_headers_from_browser(headers_dict)
        return {"success": success, "message": "认证头更新成功" if success else "认证头更新失败"}


async def collect_matches(date: str) -> dict[str, Any]:
    """
    采集指定日期的比赛数据 (Claude Skill接口)

    Args:
        date: 日期字符串 (YYYY-MM-DD 或 YYYYMMDD)

    Returns:
        采集结果
    """
    async with DataCollectionSkill() as skill:
        url = "https://www.fotmob.com/api/matches"
        params = {"date": date.replace("-", "")}

        result = await skill.collect_with_retry(url, params)

        return {
            "success": result.success,
            "data_size": result.data_size,
            "matches_found": result.matches_found,
            "pl_matches": result.pl_matches,
            "duration": result.duration_seconds,
            "error_message": result.error_message,
        }


async def get_collection_status() -> dict[str, Any]:
    """
    获取采集状态 (Claude Skill接口)

    Returns:
        状态汇总
    """
    async with DataCollectionSkill() as skill:
        return await skill.get_collection_status()


if __name__ == "__main__":
    # 测试代码
    async def main():
        async with DataCollectionSkill() as skill:
            # 测试认证头
            print("🔍 测试认证头...")
            is_valid, message = await skill.validate_headers()
            print(f"结果: {is_valid} - {message}")

            # 获取状态
            status = await skill.get_collection_status()
            print(f"状态: {json.dumps(status, indent=2, default=str)}")

    asyncio.run(main())
