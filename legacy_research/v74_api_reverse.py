#!/usr/bin/env python3
"""
V74.2 API Reverse - 网络请求监听与 API 逆向

终极策略：
1. 监听所有网络请求
2. 找到返回比赛数据的 API
3. 解析 API 响应中的比赛 ID 和 URL
4. 直接构造完整的比赛 URL
"""

import asyncio
import json
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any

from playwright.async_api import async_playwright, Page, Request

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('logs/v74_api_reverse.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class APIInterceptor:
    """API 请求拦截器"""

    def __init__(self):
        self.captured_requests: List[Dict[str, Any]] = []
        self.api_endpoints: Dict[str, List[Dict]] = {}

    async def on_request(self, request: Request):
        """监听所有请求"""
        url = request.url
        method = request.method
        resource_type = request.resource_type

        # 记录 API 请求
        if resource_type in ['xhr', 'fetch']:
            logger.info(f"[API] {method} {url}")

            self.captured_requests.append({
                'url': url,
                'method': method,
                'resource_type': resource_type,
                'timestamp': datetime.now().isoformat()
            })

            # 按端点分类
            endpoint = url.split('?')[0].split('/')[-1]
            if endpoint not in self.api_endpoints:
                self.api_endpoints[endpoint] = []
            self.api_endpoints[endpoint].append({
                'url': url,
                'method': method
            })

    async def on_response(self, response):
        """监听响应"""
        try:
            url = response.url
            status = response.status

            # 只记录成功的 API 响应
            if status == 200 and response.request.resource_type in ['xhr', 'fetch']:
                try:
                    body = await response.text()

                    # 检查是否包含比赛数据
                    if any(keyword in body.lower() for keyword in ['match', 'team', 'odds', 'home', 'away']):
                        # 尝试解析 JSON
                        try:
                            data = json.loads(body)
                            logger.info(f"[Response] URL: {url[:80]}...")
                            logger.info(f"[Response] Size: {len(body)} bytes")

                            # 检查是否包含 7-8 位 ID
                            body_str = json.dumps(data) if isinstance(data, (dict, list)) else body
                            ids = re.findall(r'["/]([a-z0-9]{7,8})["/]', body_str, re.IGNORECASE)

                            if ids:
                                logger.info(f"[Response] Found {len(set(ids))} potential IDs")

                        except json.JSONDecodeError:
                            pass

                except Exception as e:
                    pass

        except Exception as e:
            pass


async def monitor_network_traffic(url: str, league: str, season: str):
    """监听网络流量"""
    logger.info(f"=" * 60)
    logger.info(f"V74.2 API Reverse - {league} {season}")
    logger.info(f"URL: {url}")
    logger.info(f"=" * 60)

    interceptor = APIInterceptor()

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            slow_mo=100
        )

        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )

        page = await context.new_page()

        # 注册监听器
        page.on('request', interceptor.on_request)
        page.on('response', interceptor.on_response)

        try:
            # 访问页面
            logger.info("正在加载页面并监听网络请求...")
            await page.goto(url, wait_until='networkidle', timeout=60000)

            # 等待并滚动触发更多请求
            logger.info("等待 API 请求（10 秒）...")
            await asyncio.sleep(10)

            # 滚动页面触发懒加载
            logger.info("滚动页面触发懒加载...")
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await asyncio.sleep(5)

            # 点击一些元素触发数据加载
            logger.info("尝试触发数据加载...")
            try:
                # 尝试点击可能的触发器
                await page.click('[class*="show"]', timeout=3000)
                await asyncio.sleep(3)
            except:
                pass

            # 最终等待
            await asyncio.sleep(5)

            # 输出报告
            logger.info(f"\\n" + "=" * 60)
            logger.info(f"网络监听报告")
            logger.info(f"=" * 60)

            logger.info(f"捕获的 API 请求数: {len(interceptor.captured_requests)}")
            logger.info(f"发现的 API 端点: {len(interceptor.api_endpoints)}")

            for endpoint, requests in interceptor.api_endpoints.items():
                logger.info(f"  - {endpoint}: {len(requests)} 个请求")

            # 保存详细结果
            output_file = Path('audit_temp/v74_api_monitor.json')
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'league': league,
                    'season': season,
                    'url': url,
                    'timestamp': datetime.now().isoformat(),
                    'total_requests': len(interceptor.captured_requests),
                    'endpoints': interceptor.api_endpoints,
                    'requests': interceptor.captured_requests
                }, f, indent=2, ensure_ascii=False)

            logger.info(f"详细结果已保存: {output_file}")

            # 打印前 10 个 API 请求
            logger.info(f"\\n前 10 个 API 请求:")
            for req in interceptor.captured_requests[:10]:
                logger.info(f"  [{req['method']}] {req['url'][:80]}...")

            return interceptor

        finally:
            await browser.close()


async def main():
    """主函数"""
    test_url = "https://www.oddsportal.com/football/germany/bundesliga-2024-2025/results/"

    interceptor = await monitor_network_traffic(test_url, "Bundesliga", "24/25")

    logger.info(f"\\n任务完成！")


if __name__ == "__main__":
    asyncio.run(main())
