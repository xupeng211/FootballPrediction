#!/usr/bin/env python3
"""
V74.0 Deep Probe - Vue.js 动态列表深度探测

核心策略：
1. 扫描 Vue 组件的 __vue__ 属性
2. 提取隐藏的 dataset 和路由参数
3. 查找 match-link 类似属性
4. 逆向构造比赛 URL
"""

import asyncio
import json
import logging
import re
from datetime import datetime
from pathlib import Path

from playwright.async_api import async_playwright

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('logs/v74_deep_probe.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


# ============================================================================
# JavaScript 探测脚本
# ============================================================================

DEEP_PROBE_JS = """
() => {
    const results = [];

    // 策略 1: 扫描所有带 href 的 <a> 标签
    const allLinks = document.querySelectorAll('a[href]');
    for (const link of allLinks) {
        const href = link.getAttribute('href');
        // 匹配比赛页面格式: /football/.../...-xxxxxx/
        const matchIdMatch = href.match(/\\/\\/([a-z0-9]{7,8})\\//);
        if (matchIdMatch) {
            results.push({
                strategy: 'href_match',
                href: href,
                match_id: matchIdMatch[1],
                text: link.textContent?.trim().substring(0, 100)
            });
        }
    }

    // 策略 2: 扫描 Vue 组件的 data 属性
    const allElements = document.querySelectorAll('*');
    for (const elem of allElements) {
        // 检查 dataset
        if (elem.dataset) {
            for (const [key, value] of Object.entries(elem.dataset)) {
                // 查找包含 ID 的 data 属性
                if (typeof value === 'string' && value.length >= 7 && value.length <= 10) {
                    const idMatch = value.match(/([a-z0-9]{7,8})/i);
                    if (idMatch && /^[a-z0-9]{7,8}$/.test(idMatch[1])) {
                        results.push({
                            strategy: 'dataset',
                            dataset_key: key,
                            dataset_value: value,
                            match_id: idMatch[1],
                            tag: elem.tagName,
                            class: elem.className
                        });
                    }
                }
            }
        }

        // 检查 Vue 组件
        if (elem.__vue__) {
            const vueData = elem.__vue__;
            // 深度扫描 Vue 组件属性
            const scanObject = (obj, path = 'vue') => {
                if (!obj || typeof obj !== 'object') return;

                for (const [key, value] of Object.entries(obj)) {
                    const currentPath = `${path}.${key}`;

                    // 查找可能的 ID
                    if (typeof value === 'string' && value.length >= 7 && value.length <= 10) {
                        const idMatch = value.match(/([a-z0-9]{7,8})/i);
                        if (idMatch && /^[a-z0-9]{7,8}$/.test(idMatch[1])) {
                            results.push({
                                strategy: 'vue_property',
                                path: currentPath,
                                value: value,
                                match_id: idMatch[1]
                            });
                        }
                    }

                    // 递归扫描（限制深度）
                    if (typeof value === 'object' && path.split('.').length < 5) {
                        scanObject(value, currentPath);
                    }
                }
            };

            scanObject(vueData, 'vue');
        }

        // 检查 Vue Router 属性
        if (elem.__vueParentComponent) {
            const router = elem.__vueParentComponent.$router;
            if (router && router.currentRoute && router.currentRoute.value) {
                const params = router.currentRoute.value.params;
                if (params) {
                    for (const [key, value] of Object.entries(params)) {
                        const idMatch = String(value).match(/([a-z0-9]{7,8})/i);
                        if (idMatch && /^[a-z0-9]{7,8}$/.test(idMatch[1])) {
                            results.push({
                                strategy: 'vue_router',
                                param_key: key,
                                param_value: value,
                                match_id: idMatch[1]
                            });
                        }
                    }
                }
            }
        }
    }

    // 策略 3: 扫描所有 script 标签中的 JSON 数据
    const scripts = document.querySelectorAll('script[type="application/json"]');
    for (const script of scripts) {
        try {
            const data = JSON.parse(script.textContent);
            const jsonString = JSON.stringify(data);
            const idMatches = jsonString.match(/"([a-z0-9]{7,8})"/gi);
            if (idMatches) {
                for (const match of idMatches) {
                    const id = match.replace(/"/g, '');
                    if (/^[a-z0-9]{7,8}$/.test(id)) {
                        results.push({
                            strategy: 'json_ld',
                            match_id: id
                        });
                    }
                }
            }
        } catch (e) {
            // 忽略解析错误
        }
    }

    // 策略 4: 从 window.__INITIAL_STATE__ 或类似全局变量提取
    if (window.__INITIAL_STATE__) {
        const stateString = JSON.stringify(window.__INITIAL_STATE__);
        const idMatches = stateString.match(/"([a-z0-9]{7,8})"/gi);
        if (idMatches) {
            for (const match of idMatches) {
                const id = match.replace(/"/g, '');
                if (/^[a-z0-9]{7,8}$/.test(id)) {
                    results.push({
                        strategy: 'initial_state',
                        match_id: id
                    });
                }
            }
        }
    }

    // 去重
    const uniqueIds = new Set();
    const uniqueResults = [];
    for (const result of results) {
        if (!uniqueIds.has(result.match_id)) {
            uniqueIds.add(result.match_id);
            uniqueResults.push(result);
        }
    }

    return {
        total_found: uniqueResults.length,
        strategies: {
            href_match: uniqueResults.filter(r => r.strategy === 'href_match').length,
            dataset: uniqueResults.filter(r => r.strategy === 'dataset').length,
            vue_property: uniqueResults.filter(r => r.strategy === 'vue_property').length,
            vue_router: uniqueResults.filter(r => r.strategy === 'vue_router').length,
            json_ld: uniqueResults.filter(r => r.strategy === 'json_ld').length,
            initial_state: uniqueResults.filter(r => r.strategy === 'initial_state').length
        },
        results: uniqueResults.slice(0, 100)  // 返回前 100 个
    };
}
"""


async def deep_probe_page(url: str, league: str, season: str):
    """对单个页面进行深度探测"""
    logger.info(f"=" * 60)
    logger.info(f"V74.0 Deep Probe - {league} {season}")
    logger.info(f"URL: {url}")
    logger.info(f"=" * 60)

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,  # 非无头模式便于调试
            slow_mo=100
        )

        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )

        page = await context.new_page()

        try:
            # 访问页面
            logger.info("正在加载页面...")
            await page.goto(url, wait_until='networkidle', timeout=60000)

            # 等待 Vue 渲染
            logger.info("等待 Vue.js 渲染（5 秒）...")
            await asyncio.sleep(5)

            # 滚动触发懒加载
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight / 2)")
            await asyncio.sleep(2)

            # 执行深度探测
            logger.info("执行深度 JavaScript 探测...")
            probe_result = await page.evaluate(DEEP_PROBE_JS)

            # 输出结果
            logger.info(f"探测完成！")
            logger.info(f"  总计发现: {probe_result['total_found']} 个唯一 ID")
            logger.info(f"  策略分布:")
            for strategy, count in probe_result['strategies'].items():
                if count > 0:
                    logger.info(f"    - {strategy}: {count}")

            # 保存详细结果
            output_file = Path('audit_temp/v74_probe_results.json')
            output_file.parent.mkdir(exist_ok=True)
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'league': league,
                    'season': season,
                    'url': url,
                    'timestamp': datetime.now().isoformat(),
                    'probe_result': probe_result
                }, f, indent=2, ensure_ascii=False)

            logger.info(f"详细结果已保存: {output_file}")

            # 打印前 20 个发现的 ID
            logger.info(f"\\n前 20 个发现的比赛 ID:")
            for i, result in enumerate(probe_result['results'][:20], 1):
                logger.info(f"  [{i}] {result['match_id']} (策略: {result['strategy']})")

            return probe_result

        finally:
            await browser.close()


async def main():
    """主函数"""
    # 测试页面
    test_urls = [
        ("Bundesliga", "24/25", "https://www.oddsportal.com/football/germany/bundesliga-2024-2025/results/"),
        ("Premier League", "24/25", "https://www.oddsportal.com/football/england/premier-league-2024-2025/results/"),
    ]

    all_results = {}

    for league, season, url in test_urls:
        result = await deep_probe_page(url, league, season)
        all_results[f"{league}_{season}"] = result
        await asyncio.sleep(3)  # 间隔避免过载

    # 汇总报告
    logger.info("\\n" + "=" * 60)
    logger.info("V74.0 Deep Probe - 汇总报告")
    logger.info("=" * 60)

    total_ids = sum(r['total_found'] for r in all_results.values())
    logger.info(f"总探测页面: {len(all_results)}")
    logger.info(f"总发现 ID: {total_ids}")

    for key, result in all_results.items():
        logger.info(f"  {key}: {result['total_found']} 个 ID")


if __name__ == "__main__":
    asyncio.run(main())
