#!/usr/bin/env python3
"""
V54.7 API 拦截器 - 网络请求监听与数据提取
===========================================

功能:
1. 拦截所有 XHR/Fetch 请求
2. 过滤包含 ajax/results/next-games 的响应
3. 解析 JSON 提取比赛详情 URL
4. 保存完整响应数据用于分析

Author: Senior Network Protocol & API Reverse Engineer
Version: V54.7
Date: 2026-01-01
"""

import asyncio
import json
import logging
import re
from datetime import datetime
from pathlib import Path

from playwright.async_api import async_playwright, Response
from playwright_stealth import Stealth

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

# 输出目录
OUTPUT_DIR = Path("logs/debug_v54_7")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

USER_DATA_DIR = Path(".playwright_stealth_profile")

# 存储拦截的响应
intercepted_responses = []


class APIInterceptor:
    """API 拦截器"""

    def __init__(self):
        self.captured_count = 0
        self.target_keywords = ["ajax", "results", "next-games", "get-data", "matches"]
        self.football_pattern = re.compile(r'/football/[a-z/-]+-\w{3,}/')

    async def on_response(self, response: Response):
        """响应处理回调"""
        try:
            url = response.url
            request = response.request
            resource_type = request.resource_type

            # 过滤目标请求
            is_target = (
                resource_type in ["xhr", "fetch"] or
                any(keyword in url.lower() for keyword in self.target_keywords)
            )

            if not is_target:
                return

            # 尝试获取响应内容
            try:
                content_type = response.headers.get("content-type", "")

                if "application/json" in content_type:
                    data = await response.json()
                    text_data = json.dumps(data)
                else:
                    text_data = await response.text()
                    data = None

                # 检查是否包含足球相关内容
                has_football = (
                    "/football/" in url or
                    "/football/" in text_data or
                    self.football_pattern.search(text_data)
                )

                if has_football:
                    self.captured_count += 1

                    captured = {
                        "id": self.captured_count,
                        "url": url,
                        "method": request.method,
                        "status": response.status,
                        "type": resource_type,
                        "content_type": content_type,
                        "has_json": data is not None,
                        "data_size": len(text_data),
                        "text": text_data,
                        "json": data,
                    }

                    intercepted_responses.append(captured)

                    logger.info(f"✓ 拦截 #{self.captured_count}: {url[:80]}")
                    logger.info(f"  状态: {response.status}, 大小: {len(text_data):,} 字节")

                    # 如果包含比赛链接，立即保存
                    if self._extract_match_urls(text_data):
                        logger.info(f"  >> 发现比赛链接！")

            except Exception as e:
                # 解析失败，只记录基本信息
                logger.debug(f"解析响应失败: {url[:60]}, 错误: {e}")

        except Exception as e:
            logger.debug(f"响应处理异常: {e}")

    def _extract_match_urls(self, text: str) -> list[str]:
        """从文本中提取比赛详情 URL"""
        # 匹配 /football/.../team1-team2-xxxxx/ 格式
        pattern = r'(/football/[a-z/-]+-[a-zA-Z0-9]{3,}/)'
        matches = re.findall(pattern, text)
        return matches


async def intercept_and_extract():
    """执行拦截并提取数据"""

    logger.info("")
    logger.info("=" * 60)
    logger.info("V54.7 API 拦截器启动")
    logger.info("=" * 60)
    logger.info("")

    # 初始化拦截器
    interceptor = APIInterceptor()

    playwright = await async_playwright().start()

    browser_context = await playwright.chromium.launch_persistent_context(
        user_data_dir=str(USER_DATA_DIR),
        headless=True,
        args=[
            "--disable-blink-features=AutomationControlled",
            "--disable-dev-shm-usage",
        ],
        viewport={"width": 1920, "height": 1080},
        locale="en-US",
    )

    stealth = Stealth()
    page = browser_context.pages[0] if browser_context.pages else await browser_context.new_page()
    await stealth.apply_stealth_async(page)

    # 注册响应监听器
    page.on("response", interceptor.on_response)

    logger.info("✓ 网络监听器已部署")
    logger.info("✓ 过滤关键词: " + ", ".join(interceptor.target_keywords))
    logger.info("")

    try:
        # 步骤 1: 访问主页建立会话
        logger.info("步骤 1: 访问主页建立会话...")
        await page.goto("https://www.oddsportal.com", wait_until="domcontentloaded", timeout=30000)
        await asyncio.sleep(3)

        # 步骤 2: 访问目标 Results 页面
        target_url = "https://www.oddsportal.com/football/england/premier-league-2023-2024/results/"
        logger.info(f"步骤 2: 访问目标页面...")
        logger.info(f"  URL: {target_url}")

        await page.goto(target_url, wait_until="domcontentloaded", timeout=60000)
        await asyncio.sleep(5)

        # 步骤 3: 触发式加载（强制滚动）
        logger.info("")
        logger.info("步骤 3: 触发式加载（强制滚动）...")

        for i in range(30):
            await page.evaluate("window.scrollBy(0, 400)")
            await asyncio.sleep(0.3)

            # 每 10 次滚动报告一次
            if (i + 1) % 10 == 0:
                logger.info(f"  滚动进度: {i + 1}/30, 已拦截: {interceptor.captured_count} 个")

        # 步骤 4: 等待网络空闲
        logger.info("")
        logger.info("步骤 4: 等待网络请求完成...")
        try:
            await page.wait_for_load_state("networkidle", timeout=10000)
        except:
            pass  # 继续执行

        await asyncio.sleep(5)

        # 步骤 5: 分析拦截结果
        logger.info("")
        logger.info("=" * 60)
        logger.info("【拦截结果分析】")
        logger.info("=" * 60)
        logger.info(f"总拦截响应: {len(intercepted_responses)}")
        logger.info("")

        if intercepted_responses:
            # 分类统计
            by_type = {}
            total_size = 0
            all_match_urls = set()

            for resp in intercepted_responses:
                rtype = resp["type"]
                by_type[rtype] = by_type.get(rtype, 0) + 1
                total_size += resp["data_size"]

                # 提取比赛 URL
                urls = interceptor._extract_match_urls(resp["text"])
                all_match_urls.update(urls)

            logger.info("按类型统计:")
            for rtype, count in sorted(by_type.items()):
                logger.info(f"  {rtype:15s}: {count} 个")

            logger.info("")
            logger.info(f"数据总量: {total_size:,} 字节")
            logger.info(f"提取的比赛链接: {len(all_match_urls)} 个")

            if all_match_urls:
                logger.info("")
                logger.info("比赛链接样例:")
                for i, url in enumerate(list(all_match_urls)[:10]):
                    logger.info(f"  {i+1}. {url}")

            # 保存完整拦截数据
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = OUTPUT_DIR / f"intercepted_{timestamp}.json"

            # 只保存关键数据，减少文件大小
            save_data = []
            for resp in intercepted_responses:
                save_data.append({
                    "id": resp["id"],
                    "url": resp["url"],
                    "method": resp["method"],
                    "status": resp["status"],
                    "type": resp["type"],
                    "data_size": resp["data_size"],
                    # 只保存前 2000 字符
                    "text_preview": resp["text"][:2000] if len(resp["text"]) > 2000 else resp["text"],
                })

            with open(output_file, "w", encoding="utf-8") as f:
                json.dump({
                    "timestamp": timestamp,
                    "total_responses": len(intercepted_responses),
                    "total_size": total_size,
                    "match_urls_count": len(all_match_urls),
                    "match_urls": list(all_match_urls),
                    "responses": save_data,
                }, f, indent=2, ensure_ascii=False)

            logger.info("")
            logger.info("=" * 60)
            logger.info("【审计报告】")
            logger.info("=" * 60)
            logger.info(f"✓ 成功截获 API 响应: 是 ({len(intercepted_responses)} 个)")
            logger.info(f"✓ 截获数据包大小: {total_size:,} 字节")
            logger.info(f"✓ 提取真实链接: {len(all_match_urls)} 个")

            if all_match_urls:
                logger.info("")
                logger.info("提取的真实链接样例:")
                for url in list(all_match_urls)[:3]:
                    logger.info(f"  - {url}")
            else:
                logger.info("")
                logger.warning("  (未从 API 响应中提取到比赛链接)")

            logger.info("")
            logger.info(f"完整数据已保存: {output_file}")
            logger.info("=" * 60)

        else:
            logger.warning("未拦截到任何目标响应")
            logger.warning("")
            logger.warning("可能原因:")
            logger.warning("  1. 页面使用静态渲染（JavaScript 动态生成内容）")
            logger.warning("  2. API 端点已改变")
            logger.warning("  3. 需要用户登录才能访问")

    except Exception as e:
        logger.error(f"拦截过程出错: {e}")
        import traceback
        traceback.print_exc()

    finally:
        await browser_context.close()
        await playwright.stop()
        logger.info("")
        logger.info("拦截器已关闭")


if __name__ == "__main__":
    asyncio.run(intercept_and_extract())
