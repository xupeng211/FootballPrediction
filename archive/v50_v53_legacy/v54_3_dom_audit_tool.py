#!/usr/bin/env python3
"""
V54.3.1 DOM 审计工具 - 无声结构发现版本
==========================================

功能:
1. 深度解剖已完赛历史页面 DOM 结构
2. 定位数值容器的 CSS 选择器路径
3. 对比历史与即时页面的选择器差异
4. 【强制脱敏】所有数值和机构名称均被占位符替换

脱敏规则:
- 数值格式 [0-9].[0-9]{2} → [VALUE]
- 机构名称 → [PROVIDER_X]
- href/title → 仅显示正则模式

Author: Senior DOM Audit Expert
Version: V54.3.1
Date: 2026-01-01
"""

import asyncio
import re
import sys
from pathlib import Path
from typing import Any

from playwright.async_api import async_playwright

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# ============================================================
# 脱敏模块 (Redaction Module)
# ============================================================

BOOKMAKER_PATTERNS = [
    r'pinnacle', r'bet365', r'william\s+hill', r'unibet',
    r'betway', r'ladbrokes', r'coral', r'bwin', r'10bet',
    r'1xbet', r'188bet', r'sportingbet', r'interwetten',
    r'sbobet', r'18bet', r'betvictor', r'energybet',
    r'marathon', r'betsson', r'nordicbet', r'comeon'
]

PROVIDER_KEYWORDS = [re.compile(pat, re.IGNORECASE) for pat in BOOKMAKER_PATTERNS]


def sanitize_text(text: str) -> str:
    """对文本进行脱敏处理"""
    if not text:
        return '[EMPTY]'

    # 第一步：替换数值格式
    sanitized = re.sub(r'\b\d+\.\d{2}\b', '[VALUE]', text)

    # 第二步：替换机构名称
    for pattern in PROVIDER_KEYWORDS:
        sanitized = pattern.sub('[PROVIDER_X]', sanitized)

    # 第三步：限制长度
    if len(sanitized) > 50:
        sanitized = sanitized[:47] + '...'

    return sanitized


def sanitize_url(url: str) -> str:
    """对 URL 进行脱敏，仅保留模式"""
    if not url:
        return '[EMPTY]'

    # 提取路径模式，隐藏具体值
    pattern_match = re.search(r'/([a-z]{2}-[0-9]+)/', url)
    if pattern_match:
        return f'[URL_PATTERN: /XX-XX/.../]'
    return '[URL_PATTERN]'


def sanitize_attribute_value(value: str) -> str:
    """对属性值进行脱敏"""
    if not value:
        return '[EMPTY]'

    # 检测是否包含数值
    if re.search(r'\d+\.\d{2}', value):
        return '[CONTAINS_VALUE]'

    # 检测是否包含机构名
    for pattern in PROVIDER_KEYWORDS:
        if pattern.search(value):
            return '[CONTAINS_PROVIDER]'

    # 截断并标记
    if len(value) > 30:
        return f'[TEXT: {len(value)} chars]'

    return sanitize_text(value)


def format_selector_path(element: dict[str, Any]) -> str:
    """格式化 CSS 选择器路径"""
    parts = []

    if element.get('tagName'):
        parts.append(element['tagName'].lower())

    if element.get('id'):
        parts.append(f"#{element['id']}")

    if element.get('className'):
        # 只取第一个 class
        classes = element['className'].split()
        if classes:
            parts.append(f".{classes[0]}")

    return ' > '.join(parts) if parts else '[UNKNOWN_PATH]'


# ============================================================
# 审计核心逻辑
# ============================================================

async def silent_audit_historical_page():
    """无声审计：仅输出结构，不暴露数据"""

    # 2023-2024 赛季已完赛比赛
    test_url = "https://www.oddsportal.com/football/england/premier-league-2023-2024/sheffield-utd-tottenham-t0DBiZhl/"

    print("=" * 70)
    print("【V54.3.1 无声结构审计】")
    print("=" * 70)
    print(f"目标: [HISTORICAL_MATCH_URL]")
    print(f"脱敏模式: 启用 (数值→[VALUE], 机构→[PROVIDER_X])")
    print()

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=False)
        page = await browser.new_page()

        print("[1/5] 加载页面...")
        await page.goto(test_url, wait_until="networkidle", timeout=30000)
        await asyncio.sleep(5)

        print("[2/5] 页面渲染完成，开始结构提取...")
        print()

        # ============================================================
        # 第一阶段：数值容器定位
        # ============================================================

        print("=" * 70)
        print("【第一阶段：数值容器定位】")
        print("=" * 70)
        print()

        # 审计 1: 定位所有包含数值的元素
        print("[Audit-1.1] 数值容器结构探测:")
        value_containers = await page.evaluate("""
            () => {
                const results = [];
                const elements = document.querySelectorAll('*');

                elements.forEach(el => {
                    const text = el.textContent?.trim();
                    // 匹配赔率格式
                    if (text && /^\\d+\\.\\d{2}$/.test(text)) {
                        // 构建 DOM 路径
                        const path = [];
                        let current = el;
                        while (current && current !== document.body) {
                            const tag = current.tagName.toLowerCase();
                            const id = current.id ? `#${current.id}` : '';
                            const cls = current.className ? `.${current.className.split(' ')[0]}` : '';
                            path.unshift(`${tag}${id}${cls}`);
                            if (path.length > 5) break; // 限制路径深度
                            current = current.parentElement;
                        }
                        results.push({
                            tagName: el.tagName,
                            className: el.className,
                            id: el.id,
                            domPath: path.join(' > '),
                            depth: path.length
                        });
                    }
                });
                return results.slice(0, 30);
            }
        """)

        print(f"  发现 {len(value_containers)} 个数值容器:")
        print()

        # 按路径分组
        path_groups: dict[str, list[dict]] = {}
        for container in value_containers:
            path = container['domPath']
            if path not in path_groups:
                path_groups[path] = []
            path_groups[path].append(container)

        print(f"  唯一选择器路径: {len(path_groups)} 个")
        print()

        for i, (path, containers) in enumerate(list(path_groups.items())[:10], 1):
            print(f"    [{i}] 路径: {path[:70]}")
            sample = containers[0]
            print(f"        tagName: {sample['tagName']}")
            print(f"        className: {sanitize_text(sample['className'])[:60]}")
            print(f"        id: {sample['id'] or '[NONE]'}")
            print(f"        出现次数: {len(containers)}")
            print()

        # ============================================================
        # 第二阶段：机构名称定位
        # ============================================================

        print("=" * 70)
        print("【第二阶段：机构名称定位】")
        print("=" * 70)
        print()

        print("[Audit-2.1] 机构标签容器探测:")
        provider_containers = await page.evaluate("""
            () => {
                const results = [];
                const keywords = ['Pinnacle', 'bet365', 'William Hill', 'Unibet',
                                  'betway', 'Ladbrokes', 'Coral', 'bwin'];

                const elements = document.querySelectorAll('*');
                elements.forEach(el => {
                    const text = el.textContent?.trim() || '';
                    for (const keyword of keywords) {
                        if (text.includes(keyword)) {
                            results.push({
                                tagName: el.tagName,
                                className: el.className,
                                id: el.id,
                                textLength: text.length,
                                hasLink: el.querySelector('a') !== null
                            });
                            break;
                        }
                    }
                });
                return results.slice(0, 15);
            }
        """)

        print(f"  发现 {len(provider_containers)} 个机构标签:")
        for i, container in enumerate(provider_containers[:10], 1):
            print(f"    [{i}] <{container['tagName']}>")
            print(f"        className: {sanitize_text(container['className'])[:60]}")
            print(f"        id: {container['id'] or '[NONE]'}")
            print(f"        包含链接: {container['hasLink']}")
            print()

        # ============================================================
        # 第三阶段：链接结构审计
        # ============================================================

        print("=" * 70)
        print("【第三阶段：链接结构审计】")
        print("=" * 70)
        print()

        print("[Audit-3.1] odds-link 链接结构:")
        link_structure = await page.evaluate("""
            () => {
                const links = document.querySelectorAll('a[class*="odds"]');
                return Array.from(links).slice(0, 10).map(link => ({
                    tagName: link.tagName,
                    className: link.className,
                    href: link.getAttribute('href') || '',
                    title: link.getAttribute('title') || '',
                    hrefLength: (link.getAttribute('href') || '').length,
                    titleLength: (link.getAttribute('title') || '').length,
                    parentTag: link.parentElement?.tagName || '',
                    parentClass: link.parentElement?.className || ''
                }));
            }
        """)

        if link_structure:
            print(f"  发现 {len(link_structure)} 个链接:")
            for i, link in enumerate(link_structure, 1):
                print(f"    [{i}] 选择器: {link['tagName']}.{link['className'].split()[0] if link['className'] else ''}")
                print(f"        href: [LENGTH:{link['hrefLength']} chars]")
                print(f"        title: [LENGTH:{link['titleLength']} chars]")
                print(f"        父级: <{link['parentTag']}> .{link['parentClass'].split()[0] if link['parentClass'] else ''}")
                print()
        else:
            print("  未发现 odds-link 结构")
            print()

        # ============================================================
        # 第四阶段：属性值模式探测
        # ============================================================

        print("=" * 70)
        print("【第四阶段：属性值模式探测】")
        print("=" * 70)
        print()

        print("[Audit-4.1] title 属性模式分析:")
        title_patterns = await page.evaluate("""
            () => {
                const results = [];
                const elements = document.querySelectorAll('[title]');

                elements.forEach(el => {
                    const title = el.getAttribute('title');
                    if (title && title.length > 0) {
                        results.push({
                            tagName: el.tagName,
                            className: el.className,
                            titleLength: title.length,
                            hasDigits: /\\d/.test(title),
                            hasOpening: /opening|initial|开盘/i.test(title),
                            hasOddsFormat: /\\d+\\.\\d{2}/.test(title)
                        });
                    }
                });
                return results.slice(0, 20);
            }
        """)

        # 分类统计
        opening_count = sum(1 for t in title_patterns if t['hasOpening'])
        odds_count = sum(1 for t in title_patterns if t['hasOddsFormat'])

        print(f"  扫描 {len(title_patterns)} 个带 title 属性的元素:")
        print(f"    包含 'opening/initial' 关键词: {opening_count}")
        print(f"    包含数值格式: {odds_count}")
        print()

        # 显示包含 opening 的元素
        opening_elements = [t for t in title_patterns if t['hasOpening']]
        if opening_elements:
            print("  [FOCUS] 包含 'opening/initial' 的元素:")
            for i, el in enumerate(opening_elements[:5], 1):
                print(f"    [{i}] <{el['tagName']}>")
                print(f"        className: {el['className'][:50]}")
                print(f"        title长度: {el['titleLength']} chars")
                print()

        # ============================================================
        # 第五阶段：隐藏元素探测
        # ============================================================

        print("=" * 70)
        print("【第五阶段：隐藏元素探测】")
        print("=" * 70)
        print()

        print("[Audit-5.1] 隐藏数值容器:")
        hidden_containers = await page.evaluate("""
            () => {
                const results = [];
                const elements = document.querySelectorAll('*');

                elements.forEach(el => {
                    const style = getComputedStyle(el);
                    if ((style.display === 'none' || style.visibility === 'hidden')) {
                        const text = el.textContent?.trim();
                        if (text && /^\\d+\\.\\d{2}$/.test(text)) {
                            results.push({
                                tagName: el.tagName,
                                className: el.className,
                                id: el.id,
                                display: style.display,
                                visibility: style.visibility
                            });
                        }
                    }
                });
                return results.slice(0, 10);
            }
        """)

        if hidden_containers:
            print(f"  发现 {len(hidden_containers)} 个隐藏数值元素:")
            for i, el in enumerate(hidden_containers, 1):
                print(f"    [{i}] <{el['tagName']}>")
                print(f"        className: {el['className'][:50]}")
                print(f"        display={el['display']}, visibility={el['visibility']}")
                print()
        else:
            print("  未发现隐藏数值元素")
            print()

        # ============================================================
        # 第六阶段：Vue.js data-v 属性探测
        # ============================================================

        print("=" * 70)
        print("【第六阶段：Vue.js data-v 属性探测】")
        print("=" * 70)
        print()

        print("[Audit-6.1] Vue 组件边界探测:")
        vue_elements = await page.evaluate("""
            () => {
                const results = [];
                const elements = document.querySelectorAll('[class*="data-v-"]');

                const uniqueClasses = new Set();
                elements.forEach(el => {
                    Array.from(el.classList).forEach(cls => {
                        if (cls.startsWith('data-v-')) {
                            uniqueClasses.add(cls);
                        }
                    });
                });
                return Array.from(uniqueClasses).slice(0, 10);
            }
        """)

        if vue_elements:
            print(f"  发现 {len(vue_elements)} 个唯一的 data-v-* 类名:")
            for i, cls in enumerate(vue_elements, 1):
                print(f"    [{i}] {cls}")
            print()
        else:
            print("  未发现 Vue.js data-v 属性")
            print()

        await asyncio.sleep(2)
        await browser.close()

    # ============================================================
    # 结构对比总结
    # ============================================================

    print()
    print("=" * 70)
    print("【V54.3.1 无声审计总结】")
    print("=" * 70)
    print()

    print("历史页面结构特征:")
    print(f"  [A] 数值容器选择器路径: 已提取 (见上方 Audit-1.1)")
    print(f"  [B] 机构标签容器: {len(provider_containers)} 个唯一结构")
    print(f"  [C] odds-link 链接: {'存在' if link_structure else '不存在'}")
    print(f"  [D] Opening/title 标记: {opening_count} 个")
    print(f"  [E] 隐藏数值元素: {len(hidden_containers)} 个")
    print(f"  [F] Vue data-v 属性: {len(vue_elements)} 个")
    print()

    print("下一步行动:")
    print("  [1] 与即时页面选择器对比 → 生成差异化报告")
    print("  [2] 构建 V54.4 历史页面专用采集器")
    print("  [3] 实现初盘/终赔的分离提取逻辑")
    print()

    print("=" * 70)
    print("【V54.3.1 无声审计完成】")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(silent_audit_historical_page())
