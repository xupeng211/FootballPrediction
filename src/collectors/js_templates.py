#!/usr/bin/env python3
"""V41.570 JavaScript Templates - JavaScript 代码模板库

This module contains all JavaScript code templates used for browser automation.
Separated from odds_production_extractor.py as part of the Great Decoupling.

Templates:
    - DOM_CLEANUP_SCRIPT: Removes UI obstacles (cookie banners, ads, overlays)
    - GHOST_HOVER_SCRIPT: Triggers hover events via event dispatching
    - EXTRACT_BOOKMAKER_ODDS_SCRIPT: Extracts odds for a specific bookmaker
    - EXTRACT_ALL_BOOKMAKERS_SCRIPT: Extracts odds for all bookmakers in one call
    - TOOLTIP_DATA_EXTRACTOR_SCRIPT: Extracts data from hover tooltips

Author: V41.570 Refactoring Team
Date: 2026-01-21
"""

from __future__ import annotations

# ============================================================================
# V89.0 Shield Breaker: DOM Cleanup Script
# ============================================================================

DOM_CLEANUP_SCRIPT = """
() => {
    const removed = [];
    const hidden = [];

    // 1. 移除 OneTrust Cookie Banner
    const onetrustSelectors = [
        '[id^="onetrust"]',
        '[id*="onetrust"]',
        '[class*="ot-sdk-container"]',
        '[class*="onetrust"]',
        '.ot-bnr-w',
        '#onetrust-consent-sdk',
        '.ot-consent-sdk'
    ];

    onetrustSelectors.forEach(selector => {
        try {
            const elements = document.querySelectorAll(selector);
            elements.forEach(el => {
                removed.push({tag: el.tagName, id: el.id, cls: el.className});
                el.remove();
            });
        } catch (e) {
            // 忽略选择器错误
        }
    });

    // 2. 移除 Bonus 广告
    const bonusSelectors = [
        '[class*="bonus"]',
        '[class*="Bonus"]',
        '[id*="bonus"]',
        '[id*="Bonus"]',
        '.banner',
        '.promo',
        '.advertisement'
    ];

    bonusSelectors.forEach(selector => {
        try {
            const elements = document.querySelectorAll(selector);
            elements.forEach(el => {
                // 检查是否是广告元素（避免误删内容）
                const text = el.textContent?.toLowerCase() || '';
                if (text.includes('bonus') || text.includes('promo') ||
                    el.className?.toLowerCase().includes('bonus')) {
                    removed.push({tag: el.tagName, id: el.id, cls: el.className});
                    el.remove();
                }
            });
        } catch (e) {
            // 忽略选择器错误
        }
    });

    // 3. 移除 Google iframe 和其他外部 iframe
    const iframes = document.querySelectorAll('iframe');
    iframes.forEach(iframe => {
        const src = iframe.src || '';
        if (src.includes('google') || src.includes('doubleclick') ||
            src.includes('facebook') || src.includes('analytics')) {
            removed.push({tag: 'iframe', src: src});
            iframe.remove();
        }
    });

    // 4. 隐藏高 z-index 遮罩层（保留 Tooltip）
    const allElements = document.querySelectorAll('*');
    allElements.forEach(el => {
        try {
            const style = window.getComputedStyle(el);
            const zIndex = parseInt(style.zIndex) || 0;

            // z-index > 100 且不是 tooltip 相关元素
            if (zIndex > 100) {
                const classes = el.className?.toLowerCase() || '';
                const id = el.id?.toLowerCase() || '';
                const isTooltip = classes.includes('tooltip') ||
                                  classes.includes('popover') ||
                                  id.includes('tooltip') ||
                                  id.includes('popover') ||
                                  el.getAttribute('role') === 'tooltip';

                if (!isTooltip && el.tagName !== 'BODY' && el.tagName !== 'HTML') {
                    el.style.setProperty('display', 'none', 'important');
                    hidden.push({
                        tag: el.tagName,
                        zIndex: zIndex,
                        cls: el.className,
                        id: el.id
                    });
                }
            }
        } catch (e) {
            // 忽略计算样式错误
        }
    });

    // 5. 强制启用页面滚动
    document.body.style.setProperty('overflow', 'auto', 'important');
    document.documentElement.style.setProperty('overflow', 'auto', 'important');

    // 6. 移除滚动锁定
    document.body.classList.remove('scroll-locked');
    document.body.classList.remove('modal-open');

    return {
        removedCount: removed.length,
        hiddenCount: hidden.length,
        removed: removed.slice(0, 10),  // 只返回前 10 个用于日志
        hidden: hidden.slice(0, 10)
    };
}
"""


# ============================================================================
# V90.0 Ghost Protocol: Event Dispatch Script
# ============================================================================


def get_ghost_hover_script(element_selector: str) -> str:
    """Returns the Ghost Protocol hover script for a specific selector.

    Args:
        element_selector: CSS selector for the target element

    Returns:
        JavaScript code as a string
    """
    return f"""
() => {{
    const results = {{}};
    const containers = document.querySelectorAll("{element_selector}");

    if (containers.length === 0) {{
        results.error = "No containers found";
        return results;
    }}

    // 尝试触发第一个容器的事件
    const target = containers[0];

    // V90.0: 隔山打牛 - 直接触发事件，完全绕过物理层
    try {{
        // 1. mouseover 事件
        const mouseoverEvent = new MouseEvent('mouseover', {{
            bubbles: true,
            cancelable: true,
            view: window
        }});
        target.dispatchEvent(mouseoverEvent);

        // 2. mouseenter 事件
        const mouseenterEvent = new MouseEvent('mouseenter', {{
            bubbles: true,
            cancelable: true,
            view: window
        }});
        target.dispatchEvent(mouseenterEvent);

        // 3. click 事件 (某些网站需要点击才能触发)
        const clickEvent = new MouseEvent('click', {{
            bubbles: true,
            cancelable: true,
            view: window
        }});
        target.dispatchEvent(clickEvent);

        results.success = true;
        results.triggered = ['mouseover', 'mouseenter', 'click'];
        results.element_tag = target.tagName;
        results.element_class = target.className;

    }} catch (e) {{
        results.error = e.toString();
    }}

    // 等待 100ms 让 tooltip 渲染
    return new Promise(resolve => {{
        setTimeout(() => {{
            // 检查是否出现 tooltip
            const tooltip = document.querySelector('[class*="tooltip"]') ||
                           document.querySelector('[role="tooltip"]') ||
                           document.querySelector('[data-tooltip]');
            results.tooltip_found = !!tooltip;
            if (tooltip) {{
                results.tooltip_text = tooltip.textContent?.substring(0, 200);
            }}
            resolve(results);
        }}, 100);
    }});
}}
"""


# ============================================================================
# V41.541 Quad Engine: Multi-Source Odds Extraction Script
# ============================================================================

EXTRACT_BOOKMAKER_ODDS_SCRIPT = """
(entityName) => {
    // Step 1: Find the bookmaker container by name
    let targetContainer = null;
    const allElements = document.querySelectorAll('*');

    for (let el of allElements) {
        const text = el.textContent || '';
        // V41.541: Entity-agnostic matching (no hard-coded exclusions)
        // Match exact bookmaker name with minimal context
        const lowerText = text.toLowerCase();
        const lowerEntityName = entityName.toLowerCase();

        // Check if this element contains our target bookmaker name
        // Use word boundary matching to avoid false positives
        const entityPattern = new RegExp('\\\\b' + lowerEntityName + '\\\\b', 'i');
        if (entityPattern.test(lowerText)) {
            // Search upward for container with odds elements
            let parent = el;
            for (let i = 0; i < 15; i++) {
                if (parent && parent.parentElement) {
                    parent = parent.parentElement;
                    // Look for odds container with multiple odds
                    const oddsElements = parent.querySelectorAll('.odds-text');
                    if (oddsElements.length >= 3) {
                        // Verify this container is primarily for this bookmaker
                        const containerText = parent.textContent || '';
                        if (containerText.toLowerCase().includes(lowerEntityName)) {
                            targetContainer = parent;
                            break;
                        }
                    }
                }
            }
            if (targetContainer) break;
        }
    }

    if (!targetContainer) {
        return { found: false, error: 'Bookmaker container not found' };
    }

    // Step 2: Extract odds using fallback selector chain
    const selectorChain = [
        '.odds-text',
        '.odds-cell .odd',
        'td[data-odd]',
        '.odd',
        '[data-odd]'
    ];

    let extractedOdds = [];
    let usedSelector = null;

    for (const selector of selectorChain) {
        const oddsElements = targetContainer.querySelectorAll(selector);
        extractedOdds = [];

        for (let elem of oddsElements) {
            let text = null;

            if (selector === 'td[data-odd]' || selector === '[data-odd]') {
                text = elem.getAttribute('data-odd');
            } else {
                text = elem.textContent?.trim();
            }

            if (text) {
                const oddsMatch = text.match(/^[\\d\\.]+$/);
                if (oddsMatch) {
                    const numVal = parseFloat(text);
                    if (numVal >= 1.01 && numVal <= 20.0) {
                        extractedOdds.push(numVal);
                    }
                }
            }
        }

        if (extractedOdds.length >= 3) {
            usedSelector = selector;
            break;
        }
    }

    if (extractedOdds.length >= 3) {
        return {
            found: true,
            odds: [extractedOdds[0], extractedOdds[1], extractedOdds[2]],
            selector: usedSelector
        };
    } else {
        return {
            found: false,
            error: `Found ${extractedOdds.length} odds, need at least 3`
        };
    }
}
"""


def get_extract_all_bookmakers_script(entity_list: list[dict]) -> str:
    """Returns a script to extract all bookmakers in a single call.

    Args:
        entity_list: List of {code, name} dicts for each bookmaker

    Returns:
        JavaScript code as a string
    """
    # This is used directly in extract_all_entities_final_odds_concurrent
    # The function template is inline in that method
    return f"""
(entityList) => {{
        const results = [];
        const selectorChain = [
            '.odds-text',
            '.odds-cell .odd',
            'td[data-odd]',
            '.odd',
            '[data-odd]'
        ];

        for (const entity of entityList) {{
            const entityName = entity.name;
            const entityCode = entity.code;
            let targetContainer = null;
            const allElements = document.querySelectorAll('*');

            // Step 1: Find bookmaker container
            for (let el of allElements) {{
                const text = el.textContent || '';
                const lowerText = text.toLowerCase();
                const lowerEntityName = entityName.toLowerCase();
                const entityPattern = new RegExp('\\\\b' + lowerEntityName + '\\\\b', 'i');

                if (entityPattern.test(lowerText)) {{
                    let parent = el;
                    for (let i = 0; i < 15; i++) {{
                        if (parent && parent.parentElement) {{
                            parent = parent.parentElement;
                            const oddsElements = parent.querySelectorAll('.odds-text');
                            if (oddsElements.length >= 3) {{
                                const containerText = parent.textContent || '';
                                if (containerText.toLowerCase().includes(lowerEntityName)) {{
                                    targetContainer = parent;
                                    break;
                                }}
                            }}
                        }}
                    }}
                    if (targetContainer) break;
                }}
            }}

            if (!targetContainer) {{
                results.push({{ code: entityCode, found: false, error: 'Bookmaker container not found' }});
                continue;
            }}

            // Step 2: Extract odds using selector chain
            let extractedOdds = [];
            for (const selector of selectorChain) {{
                const oddsElements = targetContainer.querySelectorAll(selector);
                extractedOdds = [];

                for (let elem of oddsElements) {{
                    let text = null;
                    if (selector === 'td[data-odd]' || selector === '[data-odd]') {{
                        text = elem.getAttribute('data-odd');
                    }} else {{
                        text = elem.textContent?.trim();
                    }}

                    if (text) {{
                        const oddsMatch = text.match(/^[\\d\\.]+$/);
                        if (oddsMatch) {{
                            const numVal = parseFloat(text);
                            if (numVal >= 1.01 && numVal <= 20.0) {{
                                extractedOdds.push(numVal);
                            }}
                        }}
                    }}
                }}

                if (extractedOdds.length >= 3) {{
                    break;
                }}
            }}

            if (extractedOdds.length >= 3) {{
                results.push({{
                    code: entityCode,
                    found: true,
                    odds: [extractedOdds[0], extractedOdds[1], extractedOdds[2]]
                }});
            }} else {{
                results.push({{
                    code: entityCode,
                    found: false,
                    error: `Found ${{extractedOdds.length}} odds, need at least 3`
                }});
            }}
        }}

        return results;
    }}
"""
