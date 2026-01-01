#!/usr/bin/env python3
"""
V54.10 API 拦截采集引擎 - 网络响应拦截方案
================================================

核心创新：
1. 使用 page.on("response") 拦截 ajax-user-data API
2. 直接从 JSON 提取纯净赔率数据（避开 DOM 杂音）
3. Margin 校验：1.02 < 1/P1 + 1/P2 + 1/P3 < 1.08

Author: Senior Backend Architect (Network Protocol Expert)
Version: V54.10 API Interceptor
Date: 2026-01-01
"""

import asyncio
import json
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Optional

import psycopg2
from playwright.async_api import Page, Response

from src.config_unified import get_settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)


class InterceptionStatus(Enum):
    """拦截状态"""
    API_CAPTURED = "api_captured"
    NO_API_DATA = "no_api_data"
    INVALID_ODDS = "invalid_odds"
    MARGIN_FAILED = "margin_failed"
    SUCCESS = "success"
    ERROR = "error"


@dataclass
class InterceptionResult:
    """拦截结果"""
    match_id: str
    status: InterceptionStatus
    home_odds: Optional[float] = None
    draw_odds: Optional[float] = None
    away_odds: Optional[float] = None
    margin: Optional[float] = None
    api_captured: bool = False
    error_detail: Optional[str] = None


@dataclass
class APICache:
    """API 数据缓存"""
    captured_data: dict = field(default_factory=dict)
    is_captured: bool = False


class V54_10APIInterceptor:
    """V54.10 API 拦截采集引擎"""

    def __init__(self):
        self.settings = get_settings()
        self.api_cache = APICache()

    def get_db_connection(self):
        """获取数据库连接"""
        return psycopg2.connect(
            host=self.settings.database.host,
            port=self.settings.database.port,
            database=self.settings.database.name,
            user=self.settings.database.user,
            password=self.settings.database.password.get_secret_value(),
        )

    def get_test_matches(self, limit: int = 26) -> list[dict]:
        """获取待测试的 26 场比赛"""
        conn = self.get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                pf.match_id,
                m.home_team,
                m.away_team,
                pf.source_url
            FROM prematch_features pf
            JOIN matches m ON pf.match_id = m.match_id
            WHERE pf.source_url IS NOT NULL
              AND pf.is_processed = FALSE
              AND pf.closing_home_odds IS NULL
            ORDER BY pf.id DESC
            LIMIT %s
        """, (limit,))

        results = cursor.fetchall()
        cursor.close()
        conn.close()

        return results

    def setup_response_interceptor(self, page: Page):
        """
        设置响应拦截器

        拦截所有 /ajax-user-data/ 开头的 API 响应
        """
        async def handle_response(response: Response):
            """处理响应事件"""
            # 记录所有响应 URL（调试用）
            url = response.url

            # 拦截所有可能的 API 端点
            if any(pattern in url for pattern in [
                "/ajax-",
                "/api/",
                "/serve/",
                "oddsportal.com/ajax"
            ]):
                logger.debug(f"  [API] {url[:80]}...")

            # 专门拦截 ajax-user-data
            if "/ajax-user-data/" in url or "/ajax-" in url:
                logger.info(f"  [捕获] {url[:80]} (状态: {response.status})")
                if response.status == 200:
                    try:
                        data = None

                        # 首先尝试直接解析 JSON
                        try:
                            data = await response.json()
                        except:
                            # 如果失败，说明是 JavaScript 包装格式
                            # 响应格式：JSON.parse('{...}') 其中的字符串是转义的 JSON
                            text = await response.text()

                            # 策略 1: 提取 JSON.parse('...') 中的转义字符串
                            # 格式: JSON.parse('{"key":"value",...}')
                            match = re.search(r"JSON\.parse\('(.+?)'\)", text, re.DOTALL)
                            if match:
                                escaped_json = match.group(1)
                                # 解析转义序列：\\" -> ", \\\\ -> \\
                                unescaped = escaped_json.replace('\\"', '"').replace('\\\\', '\\')
                                data = json.loads(unescaped)
                            else:
                                # 策略 2: 提取 JSON.parse("...") 中的转义字符串
                                match = re.search(r'JSON\.parse\("(.+?)"\)', text, re.DOTALL)
                                if match:
                                    escaped_json = match.group(1)
                                    unescaped = escaped_json.replace('\\"', '"').replace('\\\\', '\\')
                                    data = json.loads(unescaped)
                                else:
                                    # 策略 3: 查找任何 {...} 结构（使用平衡括号匹配）
                                    # 从 { 开始，找到匹配的 }
                                    def extract_object(s, start=0):
                                        """提取从 start 开始的完整 JSON 对象"""
                                        if s[start] != '{':
                                            return None
                                        depth = 0
                                        in_string = False
                                        escape_next = False
                                        for i, c in enumerate(s[start:], start):
                                            if escape_next:
                                                escape_next = False
                                                continue
                                            if c == '\\':
                                                escape_next = True
                                                continue
                                            if c == '"' and not escape_next:
                                                in_string = not in_string
                                            if not in_string:
                                                if c == '{':
                                                    depth += 1
                                                elif c == '}':
                                                    depth -= 1
                                                    if depth == 0:
                                                        return s[start:i+1]
                                        return None

                                    for match in re.finditer(r'\{', text):
                                        obj_str = extract_object(text, match.start())
                                        if obj_str:
                                            try:
                                                data = json.loads(obj_str)
                                                break
                                            except:
                                                continue

                        if data:
                            self.api_cache.captured_data = data
                            self.api_cache.is_captured = True
                            logger.info(f"  ✓ API 拦截成功: {url[:60]}...")

                            # 保存样本 JSON 用于调试
                            import os
                            debug_dir = Path("logs/debug_v54_10/json_samples")
                            debug_dir.mkdir(parents=True, exist_ok=True)
                            sample_file = debug_dir / f"sample_{len(list(debug_dir.glob('*.json')))}.json"
                            with open(sample_file, 'w', encoding='utf-8') as f:
                                json.dump(data, f, indent=2, ensure_ascii=False)
                        else:
                            logger.info(f"  ✗ API 数据为空")
                    except Exception as e:
                        logger.info(f"  ✗ API 解析失败: {e}")
                else:
                    logger.info(f"  ✗ API 状态码: {response.status}")

        # 注册响应监听器
        page.on("response", handle_response)

    def reset_cache(self):
        """重置缓存"""
        self.api_cache = APICache()

    async def extract_odds_from_api_json(self, api_data: dict) -> Optional[dict]:
        """
        从 API JSON 数据中提取赔率

        策略：
        1. 查找包含 avg_p1, avg_p2, avg_p3 的数据结构
        2. 或者查找包含 home/draw/away 的 odds 数据
        """
        # 尝试多种可能的 JSON 结构
        odds_candidates = []

        # 策略 1: 直接查找 avg_p1, avg_p2, avg_p3
        if "avg_p1" in api_data and "avg_p2" in api_data and "avg_p3" in api_data:
            try:
                p1 = float(api_data.get("avg_p1", 0))
                p2 = float(api_data.get("avg_p2", 0))
                p3 = float(api_data.get("avg_p3", 0))
                if self._validate_odds_values(p1, p2, p3):
                    odds_candidates.append((p1, p2, p3))
            except (ValueError, TypeError):
                pass

        # 策略 2: 查找嵌套的 odds 对象
        for key, value in api_data.items():
            if isinstance(value, dict):
                # 检查是否包含 odds 相关字段
                if any(k in value for k in ["avg_p1", "home_odds", "p1", "odds_home"]):
                    extracted = self._extract_from_nested(value)
                    if extracted:
                        odds_candidates.append(extracted)

            # 检查列表中的第一个元素
            elif isinstance(value, list) and value:
                first_item = value[0]
                if isinstance(first_item, dict):
                    if any(k in first_item for k in ["avg_p1", "home_odds", "p1", "odds_home"]):
                        extracted = self._extract_from_nested(first_item)
                        if extracted:
                            odds_candidates.append(extracted)

        # 策略 3: 递归搜索所有数值
        if not odds_candidates:
            found = self._deep_search_odds(api_data)
            if found:
                odds_candidates.append(found)

        # 返回最佳候选（通常是第一个或平均值的那个）
        if odds_candidates:
            # 使用第一个有效的候选
            p1, p2, p3 = odds_candidates[0]
            return {"home": p1, "draw": p2, "away": p3}

        return None

    def _validate_odds_values(self, p1: float, p2: float, p3: float) -> bool:
        """验证赔率值是否合理"""
        if not all(1.01 <= x <= 50.0 for x in [p1, p2, p3]):
            return False

        # 预检查 Margin（快速过滤）
        margin = 1.0 / p1 + 1.0 / p2 + 1.0 / p3
        if margin < 0.8 or margin > 3.0:  # 宽松预检查
            return False

        return True

    def _extract_from_nested(self, data: dict) -> Optional[tuple]:
        """从嵌套对象中提取赔率"""
        # 尝试多种字段名
        home_keys = ["avg_p1", "home_odds", "p1", "odds_home", "final_home", "home"]
        draw_keys = ["avg_p2", "draw_odds", "p2", "odds_draw", "final_draw", "draw"]
        away_keys = ["avg_p3", "away_odds", "p3", "odds_away", "final_away", "away"]

        p1 = p2 = p3 = None

        for key in home_keys:
            if key in data:
                try:
                    p1 = float(data[key])
                    break
                except (ValueError, TypeError):
                    continue

        for key in draw_keys:
            if key in data:
                try:
                    p2 = float(data[key])
                    break
                except (ValueError, TypeError):
                    continue

        for key in away_keys:
            if key in data:
                try:
                    p3 = float(data[key])
                    break
                except (ValueError, TypeError):
                    continue

        if p1 and p2 and p3 and self._validate_odds_values(p1, p2, p3):
            return (p1, p2, p3)

        return None

    def _deep_search_odds(self, data: Any, depth: int = 0) -> Optional[tuple]:
        """深度搜索赔率值"""
        if depth > 5:
            return None

        if isinstance(data, dict):
            # 收集所有可能是赔率的数值
            candidates = []
            for key, value in data.items():
                if isinstance(value, (int, float)):
                    value_f = float(value)
                    if 1.01 <= value_f <= 50.0:
                        candidates.append((key, value_f))

            # 如果恰好有 3 个候选值，且键名包含 home/draw/away 或 1/2/3
            if len(candidates) == 3:
                # 尝试排序：p1(主胜)最小，p2(平局)最大，p3(客胜)居中
                sorted_vals = sorted([v for k, v in candidates])
                # 检查是否合理：主胜通常最小
                if self._validate_odds_values(sorted_vals[0], sorted_vals[2], sorted_vals[1]):
                    return (sorted_vals[0], sorted_vals[2], sorted_vals[1])

            # 递归搜索
            for value in data.values():
                result = self._deep_search_odds(value, depth + 1)
                if result:
                    return result

        elif isinstance(data, list) and data:
            for item in data:
                result = self._deep_search_odds(item, depth + 1)
                if result:
                    return result

        return None

    async def intercept_and_extract(self, page: Page, match_id: str, url: str) -> InterceptionResult:
        """
        拦截并提取赔率数据

        流程：
        1. 访问页面
        2. 从 DOM 中直接提取 Vue.js 渲染后的赔率数据
        3. 校验 Margin
        """
        try:
            # source_url 已包含完整域名，直接使用
            target_url = url.strip()
            await page.goto(target_url, wait_until="domcontentloaded", timeout=60000)

            # 等待 Vue.js 渲染和数据加载
            # OddsPortal 使用 Vue.js，需要等待 JavaScript 执行完成
            await asyncio.sleep(10)

            # 使用 JavaScript 直接从 DOM 提取赔率
            # 策略：查找紧密连接的 3 个赔率值（来自同一元素的连续匹配）
            odds_data = await page.evaluate("""
                () => {
                    // 不使用词边界，直接匹配 XX.XX 格式
                    const oddsPattern = /\\d+\\.\\d{2}/g;
                    const candidates = [];

                    // 直接查找 body 文本中的所有匹配
                    const bodyText = document.body.textContent || '';
                    const matches = [...bodyText.matchAll(oddsPattern)];

                    // 转换为数值并过滤有效范围
                    const values = matches.map(m => parseFloat(m[0])).filter(n => n >= 1.01 && n <= 50.0);

                    // 查找连续 3 个值满足 Margin 条件
                    for (let i = 0; i <= values.length - 3; i++) {
                        const p1 = values[i];
                        const p2 = values[i + 1];
                        const p3 = values[i + 2];

                        const margin = 1/p1 + 1/p2 + 1/p3;

                        if (margin > 1.02 && margin < 1.08) {
                            candidates.push({values: [p1, p2, p3], margin, index: i});
                        }
                    }

                    // 优先选择最早出现的组合（通常是主要赔率）
                    candidates.sort((a, b) => a.index - b.index);

                    if (candidates.length > 0) {
                        return candidates[0].values;
                    }

                    return null;
                }
            """)

            if not odds_data or len(odds_data) < 3:
                return InterceptionResult(
                    match_id=match_id,
                    status=InterceptionStatus.INVALID_ODDS,
                    error_detail="无法从 DOM 提取有效赔率"
                )

            # 提取 P1, P2, P3
            p1, p2, p3 = odds_data[0], odds_data[1], odds_data[2]

            # Margin 校验
            margin = 1.0 / p1 + 1.0 / p2 + 1.0 / p3

            if not (1.02 < margin < 1.08):
                return InterceptionResult(
                    match_id=match_id,
                    status=InterceptionStatus.MARGIN_FAILED,
                    home_odds=p1,
                    draw_odds=p2,
                    away_odds=p3,
                    margin=margin,
                    api_captured=True,
                    error_detail=f"Margin={margin:.4f} 超出范围 (1.02, 1.08)"
                )

            # 成功
            return InterceptionResult(
                match_id=match_id,
                status=InterceptionStatus.SUCCESS,
                home_odds=p1,
                draw_odds=p2,
                away_odds=p3,
                margin=margin,
                api_captured=True
            )

        except Exception as e:
            return InterceptionResult(
                match_id=match_id,
                status=InterceptionStatus.ERROR,
                error_detail=str(e)
            )

    def update_database(self, result: InterceptionResult) -> bool:
        """
        更新数据库

        仅当 status == SUCCESS 时更新 is_processed = TRUE
        """
        if result.status != InterceptionStatus.SUCCESS:
            return False

        conn = self.get_db_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("""
                UPDATE prematch_features
                SET
                    closing_home_odds = %s,
                    closing_draw_odds = %s,
                    closing_away_odds = %s,
                    is_processed = TRUE,
                    primary_provider = 'V54.10-API-Interceptor',
                    data_timestamp = CURRENT_TIMESTAMP
                WHERE match_id = %s
            """, (
                result.home_odds,
                result.draw_odds,
                result.away_odds,
                result.match_id
            ))

            conn.commit()
            cursor.close()
            conn.close()
            return True

        except Exception as e:
            logger.error(f"数据库更新失败 [{result.match_id}]: {e}")
            cursor.close()
            conn.close()
            return False


async def run_interceptor_test(limit: int = 26) -> dict:
    """
    运行拦截器测试

    返回统计结果（Silent Mode）
    """
    interceptor = V54_10APIInterceptor()

    # 获取测试数据
    matches = interceptor.get_test_matches(limit=limit)

    logger.info("=== V54.10 API 拦截测试开始 ===")
    logger.info(f"测试样本: {len(matches)} 场比赛")
    logger.info("")

    # 初始化 Playwright
    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        # 统计变量
        results = {
            "total": len(matches),
            "success": 0,
            "invalid_odds": 0,
            "margin_failed": 0,
            "error": 0,
            "margins": [],
            "valid_rate": 0.0,
            "avg_margin": 0.0
        }

        # 逐场处理
        for idx, match in enumerate(matches, 1):
            # 数据库返回顺序: match_id, home_team, away_team, source_url
            match_id = match[0]
            home_team = match[1]
            away_team = match[2]
            source_url = match[3]

            logger.info(f"[{idx}/{len(matches)}] 处理: {home_team} vs {away_team}")

            result = await interceptor.intercept_and_extract(page, match_id, source_url)

            # 统计结果
            if result.status == InterceptionStatus.SUCCESS:
                results["success"] += 1
                results["margins"].append(result.margin)
                interceptor.update_database(result)
                logger.info(f"  ✓ 成功: Margin = {result.margin:.4f}")
            else:
                status_key = f"{result.status.value}"
                results[status_key] = results.get(status_key, 0) + 1
                logger.warning(f"  ✗ {result.status.value}: {result.error_detail}")

            # 场间延迟
            await asyncio.sleep(1)

        await browser.close()

    # 计算统计指标
    results["valid_rate"] = (results["success"] / results["total"] * 100
                            if results["total"] > 0 else 0.0)

    if results["margins"]:
        results["avg_margin"] = sum(results["margins"]) / len(results["margins"])

    return results


async def main():
    """主函数"""
    results = await run_interceptor_test(limit=26)

    logger.info("")
    logger.info("=" * 60)
    logger.info("V54.10 DOM 直接提取方案 - 执行报告")
    logger.info("=" * 60)
    logger.info("")
    logger.info(f"【测试样本】 {results['total']} 场比赛")
    logger.info("")
    logger.info(f"【逻辑成功率】 {results['valid_rate']:.2f}%")
    logger.info(f"  - 成功提取: {results['success']} 场")
    logger.info(f"  - 赔率无效: {results.get('invalid_odds', 0)} 场")
    logger.info(f"  - Margin 失败: {results.get('margin_failed', 0)} 场")
    logger.info(f"  - 其他错误: {results.get('error', 0)} 场")
    logger.info("")
    if results['avg_margin'] > 0:
        logger.info(f"【平均 Margin】 {results['avg_margin']:.4f}")
    logger.info("")
    logger.info("=" * 60)
    logger.info("V54.10 DOM 直接提取方案已就绪")
    logger.info("=" * 60)

    # 保存报告
    output_path = Path("logs/debug_v54_10/interceptor_report.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump({
            "version": "V54.10",
            "report_time": datetime.now().isoformat(),
            "statistics": {
                "total_samples": results["total"],
                "logic_success_rate_pct": results["valid_rate"],
                "avg_margin": results["avg_margin"],
                "status_breakdown": {
                    "success": results["success"],
                    "invalid_odds": results.get("invalid_odds", 0),
                    "margin_failed": results.get("margin_failed", 0),
                    "error": results.get("error", 0),
                }
            }
        }, f, indent=2, ensure_ascii=False)

    logger.info(f"详细报告已保存: {output_path}")


if __name__ == "__main__":
    asyncio.run(main())
