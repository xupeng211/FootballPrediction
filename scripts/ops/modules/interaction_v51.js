/**
 * V85.951 Interaction Module - Enhanced Stability
 * ================================================
 *
 * 核心攻坚逻辑：
 *   - 动作 A (穿透加载): scrollIntoViewIfNeeded + waitForSelector
 *   - 动作 C (DOM 审计): aria-label + data-testid 优先策略
 *   - 针对源节点 ID [16, 18, 22, 25, 30] 的特殊处理
 *
 * V85.951 增强：
 *   - 三级联合定位器 (属性/合约/结构匹配)
 *   - 坐标偏移重试机制 (Hover Calibration)
 *   - Identifier-417 精度增强
 *
 * @module interaction_v51
 * @author Senior Node.js & Playwright Engineer
 * @version V85.951
 * @since 2026-01-25
 */

'use strict';

const path = require('path');
const fs = require('fs');
const logger = require('./logger');
const log = logger.createLogger('interaction_v51');

// ============================================================================
// V85.000: Visual Provider Mapping (替代 ID 依赖方案)
// ============================================================================

const VISUAL_PROVIDERS = {
    PINNACLE: {
        id: '417',
        name: 'Pinnacle',
        title: 'Pinnacle',
        aliases: ['pinnacle', 'ps3838'],
        // V85.980 补丁 C: Logo 路径比 Title 更稳定
        logoSelector: 'img[title*="Pinnacle" i], img[src*="pinnacle" i], img[alt*="Pinnacle" i]',
        rowSelector: 'div.border-black-borders:has(img[title*="Pinnacle" i]), div.border-black-borders:has(img[src*="pinnacle" i])',
        fallbackSelector: 'div[class*="provider"]:has-text("Pinnacle"), div:has(img[src*="pinnacle" i])'
    },
    BET365: {
        id: '16',
        name: 'bet365',
        title: 'bet365',
        aliases: ['bet365', '365'],
        logoSelector: 'img[title*="bet365" i]',
        rowSelector: 'div.border-black-borders:has(img[title*="bet365" i])',
        fallbackSelector: 'div[class*="provider"]:has-text("bet365")'
    },
    LADBROKES: {
        id: '5',
        name: 'Ladbrokes',
        title: 'Ladbrokes',
        aliases: ['ladbrokes', 'lad brokes'],
        logoSelector: 'img[title*="Ladbrokes" i]',
        rowSelector: 'div.border-black-borders:has(img[title*="Ladbrokes" i])',
        fallbackSelector: 'div[class*="provider"]:has-text("Ladbrokes")'
    },
    BWIN: {
        id: '22',
        name: 'Bwin',
        title: 'Bwin',
        aliases: ['bwin'],
        logoSelector: 'img[title*="Bwin" i]',
        rowSelector: 'div.border-black-borders:has(img[title*="Bwin" i])',
        fallbackSelector: 'div[class*="provider"]:has-text("Bwin")'
    },
    WILLIAM_HILL: {
        id: '18',
        name: 'William Hill',
        title: 'William Hill',
        aliases: ['william hill', 'will hill', 'wh'],
        logoSelector: 'img[title*="William Hill" i]',
        rowSelector: 'div.border-black-borders:has(img[title*="William Hill" i])',
        fallbackSelector: 'div[class*="provider"]:has-text("William Hill")'
    },
    ONEXBET: {
        id: '211',
        name: '1xBet',
        title: '1xBet',
        aliases: ['1xbet', '1 xbet'],
        logoSelector: 'img[title*="1xBet" i]',
        rowSelector: 'div.border-black-borders:has(img[title*="1xBet" i])',
        fallbackSelector: 'div[class*="provider"]:has-text("1xBet")'
    }
};

const PROVIDER_IDS = Object.fromEntries(
    Object.entries(VISUAL_PROVIDERS).map(([key, val]) => [key, val.id])
);

// ============================================================================
// V85.980: 补丁动作 A - 激活折叠内容 (Expand All)
// ============================================================================

/**
 * V85.980: 激活所有折叠内容 - 展开 "Show more" 等隐藏行
 *
 * 目的: 确保 Pinnacle 等被隐藏的提供商行进入 DOM 树
 *
 * @param {import('@playwright/test').Page} page - Playwright 页面对象
 * @returns {Promise<{success: boolean, expandedCount: number, errors: string[]}>}
 */
async function expandAllCollapsedContent(page) {
    log.info('[V85.980] 补丁动作 A: 激活折叠内容...');

    const errors = [];
    let expandedCount = 0;

    // 展开按钮选择器列表 (按优先级排序)
    const expandSelectors = [
        // 文本匹配按钮
        'button:has-text("Show more")',
        'button:has-text("Show all")',
        'button:has-text("Show")',
        'button:has-text("More")',
        'button:has-text("Expand")',
        // 链接形式
        'a:has-text("Show more")',
        'a:has-text("Show all")',
        'a:has-text("more")',
        'a:has-text("expand")',
        // 图标按钮 (data-testid)
        'button[data-testid="expand-button"]',
        'button[data-testid="show-more"]',
        'button[aria-label*="expand" i]',
        'button[aria-label*="show more" i]',
        // 通用类名
        'button[class*="expand"]',
        'button[class*="show-more"]',
        'div[class*="expand"]:not([class*="expanded"])'
    ];

    for (const selector of expandSelectors) {
        try {
            const elements = await page.$$(selector);

            for (const element of elements) {
                try {
                    // 检查元素是否可见
                    const isVisible = await element.isVisible().catch(() => false);
                    if (!isVisible) continue;

                    // 检查按钮文本，避免重复点击已展开的内容
                    const textContent = await element.textContent().catch(() => '');
                    if (textContent && (
                        textContent.toLowerCase().includes('hide') ||
                        textContent.toLowerCase().includes('collapse') ||
                        textContent.toLowerCase().includes('less')
                    )) {
                        log.debug(`[V85.980] 跳过已展开按钮: "${textContent.trim()}"`);
                        continue;
                    }

                    // 滚动到视图
                    await element.scrollIntoViewIfNeeded({ block: 'center' });
                    await page.waitForTimeout(200);

                    // 点击展开
                    await element.click({ force: true });
                    expandedCount++;

                    log.debug(`[V85.980] 点击展开: ${selector}`);

                    // 等待内容展开
                    await page.waitForTimeout(500);

                } catch (e) {
                    // 单个元素失败不影响其他元素
                }
            }

        } catch (e) {
            errors.push(`选择器 ${selector} 失败: ${e.message}`);
        }
    }

    // 特殊处理: 查找并点击 "X more bookmakers" 类型的提示
    try {
        const moreBookmakersSelectors = [
            'div:has-text("more bookmakers")',
            'div:has-text("more providers")',
            'span:has-text("more")',
            'div[class*="more"]'
        ];

        for (const selector of moreBookmakersSelectors) {
            const elements = await page.$$(selector);
            for (const element of elements) {
                const text = await element.textContent().catch(() => '');
                if (text && /\d+\s+more/i.test(text)) {
                    await element.click({ force: true });
                    expandedCount++;
                    log.debug(`[V85.980] 点击 "${text.trim()}"`);
                    await page.waitForTimeout(500);
                }
            }
        }
    } catch (e) {
        errors.push(`more bookmakers 查找失败: ${e.message}`);
    }

    // 最终等待: 让所有动态内容加载完成
    await page.waitForTimeout(1000);

    log.info(`[V85.980] 补丁动作 A 完成: 展开了 ${expandedCount} 个折叠区域`);

    return {
        success: expandedCount > 0 || errors.length === 0,
        expandedCount: expandedCount,
        errors: errors
    };
}

// ============================================================================
// V85.951: 三级联合定位器 (Identifier-417 精度增强)
// ============================================================================

/**
 * V85.951: 针对特定动态组件的三级联合定位器
 *
 * 三级定位策略 (按权重执行):
 *   权重 1 (属性匹配): 模糊匹配 img 标签的 title 属性 (忽略大小写)
 *   权重 2 (合约匹配): 检索 data-bookmaker-id="417" 或自定义数据属性
 *   权重 3 (结构匹配): 寻找包含特定文本标识的父级容器行 (Row Locator)
 *
 * @param {import('@playwright/test').Page} page - Playwright 页面对象
 * @param {string} providerKey - VISUAL_PROVIDERS 中的键 (如 'PINNACLE')
 * @returns {Promise<{element: ElementHandle|null, method: string, selector: string}>}
 */
async function locateProviderWithTripleLocator(page, providerKey) {
    const providerConfig = VISUAL_PROVIDERS[providerKey];
    if (!providerConfig) {
        return { element: null, method: 'none', selector: '' };
    }

    log.debug(`[V85.951] 三级联合定位器启动: ${providerKey}`);

    // ========================================================================
    // 权重 1: 属性匹配 (Attribute Matching)
    // V85.980 补丁 C: 增加 Logo 路径支持 (src 属性比 title 更稳定)
    // ========================================================================
    try {
        // 策略 A: 多重属性选择器 (按优先级)
        const titleSelectors = [
            `img[title*="${providerConfig.title}" i]`,
            `img[alt*="${providerConfig.title}" i]`,
            // V85.980: Logo 路径优先 (src 比 title 更稳定)
            `img[src*="${providerConfig.title.toLowerCase()}" i]`,
            // 多重别名匹配
            ...providerConfig.aliases.map(alias => `img[title*="${alias}" i]`),
            ...providerConfig.aliases.map(alias => `img[src*="${alias.toLowerCase()}" i]`)
        ];

        for (const selector of titleSelectors) {
            const elements = await page.$$(selector);
            for (const el of elements) {
                // 验证元素可见且在赔率行中
                const isVisible = await el.isVisible().catch(() => false);
                if (isVisible) {
                    // 向上查找父级行元素
                    const row = await findParentRow(el);
                    if (row) {
                        log.debug(`[V85.980] 权重 1 成功: ${selector}`);
                        return {
                            element: row,
                            method: 'attribute_matching',
                            selector: selector
                        };
                    }
                }
            }
        }
    } catch (e) {
        log.debug(`[V85.980] 权重 1 失败: ${e.message}`);
    }

    // ========================================================================
    // 权重 2: 合约匹配 (Contract Matching)
    // ========================================================================
    try {
        // V85.960: 获取提供商 ID
        const providerId = PROVIDER_IDS[providerKey];

        // 策略 B: 查找 data-bookmaker-id 或类似自定义属性
        const contractSelectors = [];

        if (providerId) {
            // 使用提供商专属 ID
            contractSelectors.push(
                `[data-bookmaker-id="${providerId}"]`,
                `[data-entity-id="${providerId}"]`,
                `[data-provider-id="${providerId}"]`,
                `[data-source="${providerId}"]`
            );
        }

        // 更广泛的合约属性 (回退策略)
        contractSelectors.push(
            `[data-bookmaker*="${providerConfig.title.toLowerCase()}"]`,
            `[data-provider*="${providerConfig.title.toLowerCase()}"]`
        );

        for (const selector of contractSelectors) {
            const elements = await page.$$(selector);
            if (elements.length > 0) {
                // 选择第一个可见元素
                for (const el of elements) {
                    const row = await findParentRow(el);
                    if (row) {
                        log.debug(`[V85.951] 权重 2 成功: ${selector}`);
                        return {
                            element: row,
                            method: 'contract_matching',
                            selector: selector
                        };
                    }
                }
            }
        }
    } catch (e) {
        log.debug(`[V85.951] 权重 2 失败: ${e.message}`);
    }

    // ========================================================================
    // 权重 3: 结构匹配 (Structural Matching)
    // ========================================================================
    try {
        // 策略 C: 寻找包含特定文本标识的父级容器
        const textSelectors = [
            `div:has-text("${providerConfig.name}")`,
            `div:has-text("${providerConfig.title}")`,
            // 更宽松的文本匹配
            `div:has(img[alt*="${providerConfig.title}" i])`,
            // 原始回退选择器
            providerConfig.fallbackSelector
        ];

        for (const selector of textSelectors) {
            try {
                const elements = await page.$$(selector);
                for (const el of elements) {
                    const textContent = await el.textContent();
                    // 验证包含提供商相关文本
                    if (textContent && (
                        textContent.includes(providerConfig.name) ||
                        textContent.includes(providerConfig.title) ||
                        providerConfig.aliases.some(alias =>
                            textContent.toLowerCase().includes(alias.toLowerCase())
                        )
                    )) {
                        // 确保是赔率行结构
                        const hasOddContent = /\d+\.\d+/.test(textContent);
                        if (hasOddContent) {
                            log.debug(`[V85.951] 权重 3 成功: ${selector}`);
                            return {
                                element: el,
                                method: 'structural_matching',
                                selector: selector
                            };
                        }
                    }
                }
            } catch (e2) {
                // 继续尝试下一个选择器
            }
        }
    } catch (e) {
        log.debug(`[V85.951] 权重 3 失败: ${e.message}`);
    }

    // 所有权重均失败
    log.warn(`[V85.951] 三级联合定位器失败: ${providerKey}`);
    return {
        element: null,
        method: 'none',
        selector: ''
    };
}

/**
 * V85.951: 向上查找父级赔率行元素
 *
 * @param {ElementHandle} element - 起始元素
 * @returns {Promise<ElementHandle|null>}
 */
async function findParentRow(element) {
    try {
        // 向上遍历最多 5 级
        for (let i = 0; i < 5; i++) {
            const tagName = await element.evaluate(el => el.tagName);
            const className = await element.evaluate(el => el.className).catch(() => '');

            // 检查是否为赔率行
            if (tagName === 'DIV' && (
                className.includes('border') ||
                className.includes('row') ||
                className.includes('provider')
            )) {
                return element;
            }

            // 获取父元素
            const parent = await element.evaluateHandle(el => el.parentElement);
            if (parent === element) break; // 已到达顶部
            element = parent;
        }
    } catch (e) {
        // 忽略错误
    }
    return null;
}

/**
 * V85.980: 交互降维 - 悬停与点击混合触发机制
 *
 * 改进点 (补丁 B):
 *   - 如果执行 hover() 后 3 秒内未探测到弹窗，立即改用 element.click() 触发
 *   - 强制等待: 增加 page.waitForLoadState('networkidle')
 *   - 防止异步弹窗加载过慢
 *
 * @param {ElementHandle} element - 目标元素
 * @param {import('@playwright/test').Page} page - Playwright 页面对象
 * @param {Object} [options={}] - 配置选项
 * @returns {Promise<{success: boolean, attempts: number, finalMethod: string, triggerType: string}>}
 */
async function calibratedHover(element, page, options = {}) {
    const config = {
        hoverTimeout: 3000,           // 悬停等待时间 (V85.980: 3秒)
        clickFallback: true,          // V85.980: 启用点击回退
        networkIdleTimeout: 10000,    // V85.980: networkidle 等待时间
        anchorSelector: 'h3:text("Odds movement"), h3:has-text("Odds movement"), div[class*="bottom-"]:has(h3)',
        ...options
    };

    let attempt = 0;
    const offsets = [
        { x: 0, y: 0 },      // 中心点
        { x: 5, y: 5 },      // 右下微调
        { x: -5, y: 5 },     // 左下微调
        { x: 5, y: -5 },     // 右上微调
        { x: -5, y: -5 }     // 左上微调
    ];

    // ===========================================================================
    // 阶段 1: 悬偏移重试 (保留原逻辑)
    // ===========================================================================
    for (const offset of offsets) {
        attempt++;
        try {
            log.debug(`[V85.980] Hover 尝试 ${attempt}/5, offset: (${offset.x}, ${offset.y})`);

            // 执行带偏移的 hover
            await element.hover({
                position: offset,
                force: true  // 强制触发，即使元素被遮挡
            });

            // 等待锚点出现
            try {
                const anchor = await page.waitForSelector(config.anchorSelector, {
                    timeout: config.hoverTimeout
                });
                if (anchor) {
                    log.success(`[V85.980] Hover 成功 (尝试 ${attempt}, offset: ${offset.x},${offset.y})`);
                    return {
                        success: true,
                        attempts: attempt,
                        finalMethod: `hover_offset_${offset.x}_${offset.y}`,
                        triggerType: 'hover'
                    };
                }
            } catch (e) {
                // 锚点未出现，继续尝试下一个偏移
                log.debug(`[V85.980] 悬停后 ${config.hoverTimeout}ms 内未探测到弹窗`);
            }

        } catch (e) {
            log.debug(`[V85.980] Hover 失败: ${e.message}`);
        }
    }

    // ===========================================================================
    // 阶段 2: V85.980 补丁 B - Click Fallback (交互降维)
    // ===========================================================================
    if (config.clickFallback) {
        log.info('[V85.980] 补丁动作 B: 悬停均失败，切换到 Click 触发模式...');

        try {
            // 滚动到视图中心
            await element.scrollIntoViewIfNeeded({ block: 'center' });
            await page.waitForTimeout(300);

            // 点击元素
            log.debug('[V85.980] 执行 element.click()...');
            await element.click({ force: true, timeout: 5000 });

            // V85.980: 强制等待 networkidle (防止异步弹窗加载过慢)
            log.debug('[V85.980] 等待 networkidle...');
            try {
                await page.waitForLoadState('networkidle', { timeout: config.networkIdleTimeout });
            } catch (e) {
                // networkidle 超时不是致命错误，继续执行
                log.debug('[V85.980] networkidle 超时，继续检查弹窗...');
            }

            // 额外等待，确保弹窗有时间渲染
            await page.waitForTimeout(1000);

            // 检查弹窗是否出现
            try {
                const anchor = await page.waitForSelector(config.anchorSelector, {
                    timeout: 3000
                });
                if (anchor) {
                    log.success('[V85.980] Click 触发成功! 弹窗已激活');
                    return {
                        success: true,
                        attempts: attempt + 1,
                        finalMethod: 'click_fallback',
                        triggerType: 'click'
                    };
                }
            } catch (e) {
                log.warn('[V85.980] Click 后仍未探测到弹窗');
            }

        } catch (e) {
            log.warn(`[V85.980] Click 触发失败: ${e.message}`);
        }
    }

    log.warn('[V85.980] 悬停与点击均失败');
    return {
        success: false,
        attempts: attempt + (config.clickFallback ? 1 : 0),
        finalMethod: 'none',
        triggerType: 'failed'
    };
}

// ============================================================================
// V85.000: 视觉锁定函数 - 通过视觉属性定位并取证赔率变动数据
// ============================================================================

/**
 * V85.951: 增强版视觉取证函数 - 集成三级联合定位器
 *
 * 核心逻辑：
 * 1. 遍历 VISUAL_PROVIDERS 映射表
 * 2. 使用 V85.951 三级联合定位器锁定赔率行
 * 3. 执行 calibratedHover() 坐标偏移重试
 * 4. 等待 h3:text('Odds movement') 出现
 * 5. 提取并解析弹窗 HTML
 *
 * @param {import('@playwright/test').Page} page - Playwright 页面对象
 * @param {Object} [options={}] - 配置选项
 * @returns {Promise<{success: boolean, results: Object[], errors: string[]}>}
 */
async function captureOddsMovementVisually(page, options = {}) {
    const finalOptions = {
        hoverWaitMin: 2000,
        hoverWaitMax: 5000,
        maxProviders: 5,
        enableRetry: true,
        maxRetries: 2,
        useTripleLocator: true,  // V85.951: 启用三级联合定位器
        useCalibratedHover: true, // V85.951: 启用坐标偏移重试
        expandCollapsed: true,    // V85.980: 启用折叠内容展开
        ...options
    };

    log.info('=== V85.980 视觉取证启动 (Matrix Force-Unlock Edition) ===');
    log.info(`目标提供商: ${Object.keys(VISUAL_PROVIDERS).join(', ')}`);

    const results = [];
    const errors = [];
    let processedCount = 0;

    // ===========================================================================
    // V85.980 补丁动作 A: 激活折叠内容 (在任何定位之前执行)
    // ===========================================================================
    if (finalOptions.expandCollapsed) {
        log.info('[前置步骤] V85.980 补丁动作 A: 激活折叠内容...');
        const expandResult = await expandAllCollapsedContent(page);
        if (expandResult.success) {
            log.success(`[前置步骤] 展开了 ${expandResult.expandedCount} 个折叠区域`);
        } else {
            log.warn('[前置步骤] 未找到可展开的内容 (可能已全部展开)');
        }
    }

    // 遍历视觉提供商标量表
    for (const [providerKey, providerConfig] of Object.entries(VISUAL_PROVIDERS)) {
        if (processedCount >= finalOptions.maxProviders) {
            log.info(`已处理 ${processedCount} 个提供商，达到上限`);
            break;
        }

        let attempt = 0;
        let success = false;

        while (attempt < finalOptions.maxRetries && !success) {
            attempt++;
            try {
                log.debug(`[${providerKey}] 尝试 ${attempt}/${finalOptions.maxRetries}`);

                // ========================================================================
                // Step 1: V85.951 三级联合定位器
                // ========================================================================
                let rowElement = null;
                let locatorResult = null;

                if (finalOptions.useTripleLocator) {
                    // 使用 V85.951 三级联合定位器
                    locatorResult = await locateProviderWithTripleLocator(page, providerKey);
                    rowElement = locatorResult.element;

                    if (rowElement) {
                        log.debug(`[${providerKey}] 三级联合定位器成功: ${locatorResult.method} (${locatorResult.selector})`);
                    }
                }

                // 回退到原始选择器逻辑
                if (!rowElement) {
                    const selectors = [
                        providerConfig.rowSelector,
                        providerConfig.fallbackSelector,
                        providerConfig.logoSelector
                    ];

                    for (const selector of selectors) {
                        try {
                            const elements = await page.$$(selector);
                            if (elements.length > 0) {
                                for (const el of elements) {
                                    const textContent = await el.textContent();
                                    if (textContent && textContent.trim().length > 0) {
                                        rowElement = el;
                                        log.debug(`[${providerKey}] 找到行元素: ${selector}`);
                                        break;
                                    }
                                }
                                if (rowElement) break;
                            }
                        } catch (e) {
                            // 继续尝试下一个选择器
                        }
                    }
                }

                if (!rowElement) {
                    log.debug(`[${providerKey}] 未找到行元素，跳过`);
                    break;
                }

                // Step 2: 定位赔率单元格（交互触发器）
                const oddCellSelector = 'div.flex-center.flex-col.font-bold, div[class*="odd"], div[class*="price"]';
                const triggerElement = await rowElement.$(oddCellSelector);
                const targetToHover = triggerElement || rowElement;

                // ========================================================================
                // Step 3: V85.951 坐标偏移重试机制
                // ========================================================================
                // 模拟人类行为：滚动到视图中心
                await targetToHover.scrollIntoViewIfNeeded({ block: 'center' });
                await page.waitForTimeout(300);

                let hoverResult = null;
                if (finalOptions.useCalibratedHover) {
                    // 使用 V85.951 坐标偏移重试
                    hoverResult = await calibratedHover(targetToHover, page, {
                        initialTimeout: 3000,
                        anchorSelector: 'h3:text("Odds movement"), h3:has-text("Odds movement")'
                    });

                    if (!hoverResult.success) {
                        if (attempt < finalOptions.maxRetries && finalOptions.enableRetry) {
                            log.debug(`[${providerKey}] 坐标偏移重试失败，准备全局重试...`);
                            await page.waitForTimeout(1000);
                            continue;
                        }
                        throw new Error('坐标偏移重试均失败');
                    }

                    log.debug(`[${providerKey}] Hover 成功: ${hoverResult.finalMethod} (${hoverResult.attempts} 次尝试)`);
                } else {
                    // 原始简单 hover
                    await targetToHover.hover();
                    log.debug(`[${providerKey}] Hover 触发完成`);
                }

                // Step 4: 等待 "Odds movement" 弹窗出现
                const movementSelector = 'h3:text("Odds movement"), h3:has-text("Odds movement"), div[class*="bottom-"]:has(h3)';

                // 使用更长的等待时间，并使用 waitFor 的 OR 逻辑
                let movementElement = null;
                try {
                    movementElement = await page.waitForSelector(movementSelector, {
                        timeout: finalOptions.hoverWaitMax
                    });
                } catch (e) {
                    log.debug(`[${providerKey}] 弹窗未在 ${finalOptions.hoverWaitMax}ms 内出现`);
                }

                if (!movementElement) {
                    // 尝试备用选择器
                    const fallbackMovementSelectors = [
                        'h3:has-text("movement")',
                        'div[role="tooltip"]',
                        'div[class*="tooltip"]'
                    ];

                    for (const fallbackSelector of fallbackMovementSelectors) {
                        try {
                            movementElement = await page.$(fallbackSelector);
                            if (movementElement) {
                                log.debug(`[${providerKey}] 使用备用选择器找到弹窗: ${fallbackSelector}`);
                                break;
                            }
                        } catch (e2) {
                            // 继续
                        }
                    }
                }

                if (!movementElement) {
                    if (attempt < finalOptions.maxRetries && finalOptions.enableRetry) {
                        log.debug(`[${providerKey}] 弹窗未出现，重试中...`);
                        await page.waitForTimeout(1000);
                        continue;
                    }
                    throw new Error('弹窗未出现，可能选择器已失效');
                }

                // Step 5: 提取证物 HTML
                // 策略：获取弹窗容器的 innerHTML
                let modalHTML = null;
                try {
                    // 查找弹窗容器（通常包含多行时序数据）
                    const containerSelectors = [
                        'div[class*="bottom-"]',
                        'div[role="tooltip"]',
                        movementSelector
                    ];

                    for (const containerSel of containerSelectors) {
                        const container = await page.$(containerSel);
                        if (container) {
                            modalHTML = await container.evaluate(el => el.innerHTML);
                            if (modalHTML && modalHTML.includes('Odds movement')) {
                                log.debug(`[${providerKey}] 成功取证 HTML (${modalHTML.length} chars)`);
                                break;
                            }
                        }
                    }

                    if (!modalHTML) {
                        // 最后回退：直接使用 page.evaluate 从 DOM 获取
                        modalHTML = await page.evaluate(() => {
                            const h3 = document.querySelector('h3:text("Odds movement"), h3:has-text("Odds movement")');
                            if (h3 && h3.parentElement) {
                                return h3.parentElement.innerHTML;
                            }
                            return null;
                        });
                    }

                } catch (e) {
                    throw new Error(`HTML 提取失败: ${e.message}`);
                }

                if (!modalHTML) {
                    throw new Error('无法获取弹窗 HTML');
                }

                // Step 6: 验证取证数据完整性
                if (!modalHTML.includes('Opening odds') &&
                    !modalHTML.match(/\d{1,2}\s+\w+\.?\s*,?\s*\d{1,2}:\d{2}/)) {
                    throw new Error('取证数据不完整');
                }

                // 成功取证
                results.push({
                    provider: providerKey,
                    providerName: providerConfig.name,
                    html: modalHTML,
                    htmlLength: modalHTML.length,
                    timestamp: new Date().toISOString(),
                    attempt: attempt
                });

                log.success(`[${providerKey}] ✓ 取证成功 (尝试 ${attempt}, ${modalHTML.length} chars)`);
                success = true;
                processedCount++;

                // 清理：移开鼠标，关闭弹窗
                await page.mouse.click(0, 0);
                await page.waitForTimeout(500);

            } catch (error) {
                const errorMsg = `[${providerKey}] ${error.message}`;
                errors.push(errorMsg);
                log.warn(errorMsg);

                if (attempt < finalOptions.maxRetries && finalOptions.enableRetry) {
                    log.debug(`[${providerKey}] 准备重试...`);
                    await page.waitForTimeout(1000);
                }

                // 失败后也要清理
                try {
                    await page.mouse.click(0, 0);
                    await page.waitForTimeout(300);
                } catch (e) {
                    // 忽略清理错误
                }
            }
        }
    }

    // 生成最终报告
    const overallSuccess = results.length > 0;

    log.info('=== V85.000 视觉取证完成 ===');
    log.info(`结果: ${overallSuccess ? '成功' : '失败'}`);
    log.info(`成功取证: ${results.length} 个提供商`);
    log.info(`失败: ${errors.length} 个提供商`);

    if (errors.length > 0) {
        log.info('错误列表:');
        errors.forEach(err => log.info(`  - ${err}`));
    }

    return {
        success: overallSuccess,
        results: results,
        errors: errors,
        processedCount: processedCount,
        summary: {
            total: Object.keys(VISUAL_PROVIDERS).length,
            successful: results.length,
            failed: errors.length
        }
    };
}

/**
 * V85.000: 单个提供商视觉取证（可用于针对性采集）
 *
 * @param {import('@playwright/test').Page} page - Playwright 页面对象
 * @param {string} providerKey - VISUAL_PROVIDERS 中的键 (如 'PINNACLE')
 * @returns {Promise<{success: boolean, html?: string, error?: string}>}
 */
async function captureSingleProviderVisually(page, providerKey) {
    if (!VISUAL_PROVIDERS[providerKey]) {
        return {
            success: false,
            error: `未知提供商: ${providerKey}`
        };
    }

    const result = await captureOddsMovementVisually(page, {
        maxProviders: 1
    });

    if (result.success && result.results.length > 0) {
        return {
            success: true,
            html: result.results[0].html,
            provider: result.results[0].providerName
        };
    }

    return {
        success: false,
        error: result.errors[0] || '取证失败'
    };
}

// ============================================================================
// ERROR CLASS
// ============================================================================

class InteractionV51Error extends Error {
    constructor(type, message, context = {}) {
        super(message);
        this.name = 'InteractionV51Error';
        this.errorType = type;
        this.timestamp = new Date().toISOString();
        this.context = context;
    }

    toString() {
        return `[${this.errorType}] [${this.timestamp}] ${this.message}`;
    }
}

// ============================================================================
// CONFIGURATION
// ============================================================================

/**
 * V51.000: 加载配置 - 针对特定源节点的穿透加载
 */
const V51_CONFIG = {
    // 目标源节点 ID (需要特殊处理的节点)
    targetSourceIds: [16, 18, 22, 25, 30],

    // 穿透加载配置
    penetrationLoad: {
        enabled: true,
        maxRetries: 3,
        scrollTimeout: 5000,
        contentTimeout: 10000,
        minContentLength: 1
    },

    // DOM 审计配置
    domAudit: {
        // 优先级选择器策略 (从高到低)
        selectorPriority: [
            { type: 'data-testid', weight: 100 },
            { type: 'aria-label', weight: 90 },
            { type: 'role', weight: 80 },
            { type: 'stable-class', weight: 50 },  // 非随机类名
            { type: 'fallback-class', weight: 10 } // Tailwind 等构建时类名
        ],

        // 稳定属性白名单
        stableAttributes: [
            'data-testid',
            'data-provider',
            'data-entity-id',
            'aria-label',
            'role'
        ],

        // 随机类名模式 (需要避免的)
        randomClassPatterns: [
            /data-v-[a-f0-9]{6,}/,      // Vue scoped CSS
            /_\d+[a-f0-9]{4,}/,         // CSS Modules
            /css-[a-z0-9]{8,}/          // Styled Components
        ]
    },

    // 双点采样配置
    dualPointSampling: {
        enabled: true,
        requiredSamples: 2,  // Initial + Current
        sampleInterval: 500, // 采样间隔 (ms)
        maxWaitTime: 5000    // 最大等待时间
    }
};

// ============================================================================
// 动作 A: 穿透加载 (Penetration Load)
// ============================================================================

/**
 * V51.000: 穿透加载 - 确保动态内容完全加载
 *
 * 核心逻辑：
 * 1. 使用 scrollIntoViewIfNeeded() 将节点滚动到可视区域
 * 2. 使用 waitForSelector() 等待内容加载
 * 3. 验证 textContent 不为空
 *
 * @param {ElementHandle} element - 目标节点元素
 * @param {import('@playwright/test').Page} page - Playwright 页面对象
 * @param {Object} [config={}] - 配置选项
 * @returns {Promise<{success: boolean, contentLength: number, error?: string}>}
 */
async function penetrationLoad(element, page, config = {}) {
    const finalConfig = { ...V51_CONFIG.penetrationLoad, ...config };
    let attempt = 0;

    log.debug('[动作A] 启动穿透加载...');

    while (attempt < finalConfig.maxRetries) {
        attempt++;
        try {
            // Step 1: 滚动到可视区域
            await element.evaluate(el => {
                if (el.scrollIntoViewIfNeeded) {
                    el.scrollIntoViewIfNeeded({ block: 'center' });
                } else {
                    el.scrollIntoView({ block: 'center', behavior: 'smooth' });
                }
            });

            // 等待滚动完成
            await page.waitForTimeout(300);

            // Step 2: 等待内容加载
            const textContent = await element.textContent();

            if (textContent && textContent.trim().length >= finalConfig.minContentLength) {
                log.debug(`[动作A] 穿透加载成功 (尝试 ${attempt}/${finalConfig.maxRetries})`);
                return {
                    success: true,
                    contentLength: textContent.trim().length,
                    attempts: attempt
                };
            }

            // Step 3: 内容仍为空，等待后重试
            if (attempt < finalConfig.maxRetries) {
                log.debug(`[动作A] 内容为空，等待 ${finalConfig.scrollTimeout}ms 后重试...`);
                await page.waitForTimeout(finalConfig.scrollTimeout);
            }

        } catch (error) {
            if (attempt < finalConfig.maxRetries) {
                log.warn(`[动作A] 尝试 ${attempt}/${finalConfig.maxRetries} 失败: ${error.message}`);
                await page.waitForTimeout(finalConfig.scrollTimeout);
            } else {
                return {
                    success: false,
                    contentLength: 0,
                    error: `穿透加载失败: ${error.message}`
                };
            }
        }
    }

    return {
        success: false,
        contentLength: 0,
        error: '穿透加载超时'
    };
}

/**
 * V51.000: 针对特定源节点的穿透加载
 *
 * @param {import('@playwright/test').Page} page - Playwright 页面对象
 * @param {number[]} sourceIds - 目标源节点 ID 数组 (默认 [16, 18, 22, 25, 30])
 * @returns {Promise<{success: boolean, loaded: number[], failed: number[]}>}
 */
async function penetrationLoadForSourceIds(page, sourceIds = V51_CONFIG.targetSourceIds) {
    log.info(`[动作A] 针对源节点 [${sourceIds.join(', ')}] 启动穿透加载...`);

    const results = {
        success: true,
        loaded: [],
        failed: []
    };

    for (const sourceId of sourceIds) {
        try {
            // 尝试多种选择器策略
            const selectors = [
                `[data-entity-id="${sourceId}"]`,
                `[data-provider-id="${sourceId}"]`,
                `[data-source-id="${sourceId}"]`,
                `[aria-label*="${sourceId}"]`,
                // 回退到索引选择 (最后手段)
                `*:nth-child(${sourceId})`
            ];

            let element = null;
            for (const selector of selectors) {
                try {
                    element = await page.$(selector);
                    if (element) break;
                } catch (e) {
                    // 继续尝试下一个选择器
                }
            }

            if (element) {
                const loadResult = await penetrationLoad(element, page);
                if (loadResult.success) {
                    results.loaded.push(sourceId);
                    log.debug(`[动作A] 源节点 ${sourceId} 加载成功`);
                } else {
                    results.failed.push(sourceId);
                    log.warn(`[动作A] 源节点 ${sourceId} 加载失败: ${loadResult.error}`);
                }
            } else {
                results.failed.push(sourceId);
                log.warn(`[动作A] 源节点 ${sourceId} 未找到`);
            }

        } catch (error) {
            results.failed.push(sourceId);
            log.error(`[动作A] 源节点 ${sourceId} 处理异常: ${error.message}`);
        }
    }

    results.success = results.failed.length === 0;
    return results;
}

// ============================================================================
// 动作 C: DOM 审计 (DOM Audit)
// ============================================================================

/**
 * V51.000: DOM 审计 - 分析元素的选择器稳定性
 *
 * 返回稳定的、不依赖随机类名的选择器
 *
 * @param {ElementHandle} element - 目标元素
 * @param {import('@playwright/test').Page} page - Playwright 页面对象
 * @returns {Promise<{stableSelector: string, auditScore: number, details: Object[]}>}
 */
async function auditDom(element, page) {
    const auditDetails = [];
    let totalScore = 0;

    try {
        // 检查稳定属性
        for (const attr of V51_CONFIG.domAudit.stableAttributes) {
            const attrValue = await element.getAttribute(attr);
            if (attrValue) {
                const priority = V51_CONFIG.domAudit.selectorPriority.find(p => p.type === attr);
                const score = priority ? priority.weight : 50;
                totalScore += score;

                auditDetails.push({
                    attribute: attr,
                    value: attrValue,
                    score: score,
                    stable: true
                });

                log.debug(`[DOM审计] 发现稳定属性: ${attr}="${attrValue}" (评分: ${score})`);
            }
        }

        // 检查类名稳定性
        const classNames = await element.evaluate(el => {
            return Array.from(el.classList || []);
        });

        for (const className of classNames) {
            let isRandom = false;

            for (const pattern of V51_CONFIG.domAudit.randomClassPatterns) {
                if (pattern.test(className)) {
                    isRandom = true;
                    auditDetails.push({
                        type: 'class',
                        value: className,
                        score: 0,
                        stable: false,
                        reason: '匹配随机类名模式'
                    });
                    break;
                }
            }

            if (!isRandom && className.length > 2) {
                // 非随机类名，给予部分评分
                totalScore += 20;
                auditDetails.push({
                    type: 'class',
                    value: className,
                    score: 20,
                    stable: true
                });
            }
        }

        // 构建稳定选择器
        const stableSelector = buildStableSelector(element, auditDetails);

        log.debug(`[DOM审计] 审计完成 (总分: ${totalScore})`);

        return {
            stableSelector: stableSelector,
            auditScore: totalScore,
            details: auditDetails
        };

    } catch (error) {
        log.error(`[DOM审计] 审计失败: ${error.message}`);
        return {
            stableSelector: null,
            auditScore: 0,
            details: [],
            error: error.message
        };
    }
}

/**
 * V51.000: 构建稳定选择器
 *
 * @param {ElementHandle} element - 目标元素
 * @param {Array} auditDetails - 审计详情
 * @returns {string} - 稳定的 CSS 选择器
 */
function buildStableSelector(element, auditDetails) {
    // 按评分排序，使用最稳定的属性
    const stableAttrs = auditDetails
        .filter(d => d.stable && d.attribute)
        .sort((a, b) => b.score - a.score);

    if (stableAttrs.length > 0) {
        const bestAttr = stableAttrs[0];
        return `[${bestAttr.attribute}="${bestAttr.value}"]`;
    }

    // 回退到索引 (最不稳定)
    return null;
}

/**
 * V51.000: 通过 DOM 审计识别节点
 *
 * @param {import('@playwright/test').Page} page - Playwright 页面对象
 * @returns {Promise<Array<{element: ElementHandle, index: number, selector: string, score: number}>>}
 */
async function identifyNodesByDomAudit(page) {
    const nodes = [];

    log.info('[动作C] 启动 DOM 审计识别...');

    try {
        // V84.700: 更新为实际存在的 data-testid 值
        // 策略 1: 使用 data-testid (最高优先级)
        let providerRows = await page.$$('[data-testid="betting-exchanges-table-row"], [data-testid="bookmaker-table-header-line"], [data-testid="dropping-odds"]');

        // 策略 2: 回退到 aria-label
        if (providerRows.length === 0) {
            providerRows = await page.$$('[aria-label*="provider"], [aria-label*="odds"], [aria-label*="bookmaker"]');
        }

        // 策略 3: 回退到稳定类名
        if (providerRows.length === 0) {
            providerRows = await page.$$('div[class*="provider"], div[class*="bookmaker"]');
        }

        log.debug(`[动作C] 找到 ${providerRows.length} 个候选节点`);

        for (let i = 0; i < providerRows.length; i++) {
            const row = providerRows[i];
            const auditResult = await auditDom(row, page);

            nodes.push({
                element: row,
                index: i,
                selector: auditResult.stableSelector || `nth-child(${i})`,
                score: auditResult.auditScore,
                details: auditResult.details
            });
        }

        // 按评分排序 (高到低)
        nodes.sort((a, b) => b.score - a.score);

        log.info(`[动作C] DOM 审计完成，识别 ${nodes.length} 个节点`);

    } catch (error) {
        log.error(`[动作C] DOM 审计识别失败: ${error.message}`);
    }

    return nodes;
}

/**
 * V51.000: 定位交互触发器 (增强版 - DOM 审计)
 *
 * @param {ElementHandle} nodeElement - 节点元素
 * @returns {Promise<ElementHandle|null>}
 */
async function locateTriggerByDomAudit(nodeElement) {
    try {
        // V84.700: 更新为实际存在的 data-testid 触发器
        // 策略 1: data-testid 优先
        const testIdSelectors = [
            '[data-testid="bookie-logo"]',
            '[data-testid="bookmaker-name"]',
            '[data-testid="interaction-trigger"]',
            '[data-testid="hover-trigger"]',
            '[data-testid*="trigger"]'
        ];

        for (const selector of testIdSelectors) {
            const trigger = await nodeElement.$(selector);
            if (trigger) {
                log.debug(`[动作C] 触发器找到 (data-testid): ${selector}`);
                return trigger;
            }
        }

        // 策略 2: aria-label
        const ariaSelectors = [
            '[aria-label="Show odds movement"]',
            '[aria-label*="odds"]',
            '[aria-label*="chart"]',
            '[aria-label*="bookmaker"]'
        ];

        for (const selector of ariaSelectors) {
            const trigger = await nodeElement.$(selector);
            if (trigger) {
                log.debug(`[动作C] 触发器找到 (aria-label): ${selector}`);
                return trigger;
            }
        }

        // 策略 3: 稳定类名
        const stableSelectors = [
            'div[class*="trigger"]',
            'div[class*="hover"]',
            'span[class*="odd"]'
        ];

        for (const selector of stableSelectors) {
            const triggers = await nodeElement.$$(selector);
            if (triggers.length > 0) {
                log.debug(`[动作C] 触发器找到 (stable class): ${selector}`);
                return triggers[0];
            }
        }

        // 策略 4: 使用节点本身
        log.debug('[动作C] 使用节点本身作为触发器');
        return nodeElement;

    } catch (error) {
        log.warn(`[动作C] 触发器定位失败: ${error.message}`);
        return null;
    }
}

// ============================================================================
// 动作 B: 契约校验 (Dual-Point Sampling)
// ============================================================================

/**
 * V51.000: 契约校验 - 双点采样 (Initial + Current)
 *
 * 强制获取两个数值：
 * - Initial: 开盘赔率
 * - Current: 当前赔率
 *
 * @param {ElementHandle} element - 目标元素
 * @param {import('@playwright/test').Page} page - Playwright 页面对象
 * @returns {Promise<{valid: boolean, samples: Object[], error?: string}>}
 */
async function dualPointSampling(element, page) {
    log.debug('[动作B] 启动双点采样...');

    const samples = [];
    const config = V51_CONFIG.dualPointSampling;

    try {
        // 第一次采样 (Initial)
        await page.waitForTimeout(config.sampleInterval);
        const sample1 = await extractOddValue(element, page);
        if (sample1 !== null) {
            samples.push({ type: 'Initial', value: sample1, timestamp: Date.now() });
            log.debug(`[动作B] Initial 采样: ${sample1}`);
        }

        // 第二次采样 (Current)
        await page.waitForTimeout(config.sampleInterval);
        const sample2 = await extractOddValue(element, page);
        if (sample2 !== null) {
            samples.push({ type: 'Current', value: sample2, timestamp: Date.now() });
            log.debug(`[动作B] Current 采样: ${sample2}`);
        }

        // 契约校验
        const valid = samples.length >= config.requiredSamples;

        if (!valid) {
            return {
                valid: false,
                samples: samples,
                error: `采样密度不足: 需要 ${config.requiredSamples} 个样本，实际获得 ${samples.length} 个`
            };
        }

        log.debug(`[动作B] 双点采样成功 (${samples.length} 个样本)`);
        return { valid: true, samples: samples };

    } catch (error) {
        return {
            valid: false,
            samples: samples,
            error: `双点采样失败: ${error.message}`
        };
    }
}

/**
 * V51.000: 提取赔率数值
 *
 * @param {ElementHandle} element - 目标元素
 * @param {import('@playwright/test').Page} page - Playwright 页面对象
 * @returns {Promise<number|null>}
 */
async function extractOddValue(element, page) {
    try {
        const textContent = await element.textContent();
        if (!textContent) return null;

        // 提取数值 (支持格式: 1.95, +0.05, 等)
        const match = textContent.match(/(\d+\.\d+|\d+)/);
        if (match) {
            return parseFloat(match[1]);
        }

        return null;
    } catch (error) {
        return null;
    }
}

// ============================================================================
// 综合攻坚流程
// ============================================================================

/**
 * V51.000: 综合攻坚流程 - 完整的三动作执行
 *
 * @param {import('@playwright/test').Page} page - Playwright 页面对象
 * @param {Object} [options={}] - 配置选项
 * @returns {Promise<{success: boolean, results: Object, errors: string[]}>}
 */
async function executeHardeningProcess(page, options = {}) {
    log.info('=== V51.000 综合攻坚流程启动 ===');

    const errors = [];
    const results = {
        penetrationLoad: null,
        domAudit: null,
        dualPointSampling: null
    };

    // 动作 A: 穿透加载
    log.info('[步骤 1/3] 动作 A: 穿透加载...');
    const sourceIds = options.sourceIds || V51_CONFIG.targetSourceIds;
    results.penetrationLoad = await penetrationLoadForSourceIds(page, sourceIds);

    if (!results.penetrationLoad.success) {
        errors.push(`穿透加载部分失败: ${results.penetrationLoad.failed.join(', ')}`);
    }

    // 动作 C: DOM 审计
    log.info('[步骤 2/3] 动作 C: DOM 审计...');
    const nodes = await identifyNodesByDomAudit(page);
    results.domAudit = {
        totalNodes: nodes.length,
        highScoreNodes: nodes.filter(n => n.score >= 80).length
    };

    if (nodes.length === 0) {
        errors.push('DOM 审计未找到任何节点');
    }

    // 动作 B: 契约校验 (仅对高分节点)
    log.info('[步骤 3/3] 动作 B: 契约校验...');
    const highScoreNodes = nodes.filter(n => n.score >= 80).slice(0, 5);

    for (const node of highScoreNodes) {
        const samplingResult = await dualPointSampling(node.element, page);
        if (!samplingResult.valid) {
            errors.push(`节点 ${node.index} 契约校验失败: ${samplingResult.error}`);
        }
    }

    results.dualPointSampling = {
        tested: highScoreNodes.length,
        passed: highScoreNodes.length - errors.filter(e => e.includes('契约校验')).length
    };

    const success = errors.length === 0;

    log.info('=== V51.000 综合攻坚流程完成 ===');
    log.info(`结果: ${success ? '成功' : '部分失败'}`);
    log.info(`穿透加载: ${results.penetrationLoad.loaded.length} 成功, ${results.penetrationLoad.failed.length} 失败`);
    log.info(`DOM 审计: ${results.domAudit.totalNodes} 节点, ${results.domAudit.highScoreNodes} 高分`);
    log.info(`契约校验: ${results.dualPointSampling.passed}/${results.dualPointSampling.tested} 通过`);

    return {
        success: success,
        results: results,
        errors: errors,
        nodes: highScoreNodes.map(n => ({
            index: n.index,
            selector: n.selector,
            score: n.score
        }))
    };
}

// ============================================================================
// EXPORTS
// ============================================================================

module.exports = {
    // V85.980 新增视觉取证 API (Matrix Force-Unlock Edition)
    VISUAL_PROVIDERS,
    PROVIDER_IDS,  // V85.960: 提供商 ID 映射表
    captureOddsMovementVisually,
    captureSingleProviderVisually,

    // V85.980 补丁动作
    expandAllCollapsedContent,  // 补丁 A: 激活折叠内容

    // V85.951/V85.980 三级联合定位器
    locateProviderWithTripleLocator,
    findParentRow,
    calibratedHover,  // V85.980: 集成 Click Fallback

    // 核心攻坚动作
    penetrationLoad,
    penetrationLoadForSourceIds,
    auditDom,
    identifyNodesByDomAudit,
    locateTriggerByDomAudit,
    dualPointSampling,

    // 综合流程
    executeHardeningProcess,

    // 配置
    V51_CONFIG,

    // 错误类
    InteractionV51Error
};
