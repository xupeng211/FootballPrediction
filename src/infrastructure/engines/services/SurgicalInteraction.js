/**
 * SurgicalInteraction - V165.000 Genesis.HeartBypass
 * =====================================================
 *
 * [Genesis.V164.Surgical_Upgrade] Event-Driven Facade
 *
 * Refactored into 3 modules:
 * - DOMNavigator: Modal detection & provider extraction
 * - EventSimulator: Event-driven state detection (V165.000 upgraded)
 * - AntiFingerprint: Overlay removal & detection avoidance
 *
 * This file serves as a facade, delegating to specialized modules.
 *
 * @module services/SurgicalInteraction
 * @version V165.000 (Heart Bypass Upgrade)
 * @since 2026-02-01
 * @author [Genesis.V164.Surgical_Upgrade]
 */

'use strict';

const { DOMNavigator } = require('./modules/dom_navigator');
const { EventSimulator } = require('./modules/event_simulator');
const { AntiFingerprint } = require('./modules/anti_fingerprint');

/**
 * SurgicalInteraction - Facade for browser interactions
 *
 * Delegates to specialized modules for modularity and maintainability.
 */
class SurgicalInteraction {
    /**
     * @param {Object} page - Playwright page object
     * @param {Object} config - Configuration object
     */
    constructor(page, config = {}) {
        this.page = page;
        this.config = config;

        // Initialize specialized modules
        this.domNavigator = new DOMNavigator(page, config);
        this.eventSimulator = new EventSimulator(page, config);
        this.antiFingerprint = new AntiFingerprint(page, config);
    }

    /**
     * Internal logging methods
     */
    info(...args) { console.log(`[SurgicalInteraction] INFO`, ...args); }
    warn(...args) { console.log(`[SurgicalInteraction] WARN`, ...args); }
    error(...args) { console.error(`[SurgicalInteraction] ERROR`, ...args); }

    // ========================================================================
    // DOM Navigation Methods (delegated to DOMNavigator)
    // ========================================================================

    /**
     * V148.000: Detect modal by "Odds movement" title
     * @returns {Promise<boolean>} True if modal is detected
     */
    async detectModalWithTitle() {
        return this.domNavigator.detectModalWithTitle();
    }

    /**
     * V160.000: Extract Provider Name from Parent Row
     * @param {ElementHandle} cell - The odds cell element
     * @returns {Promise<string|null>} Provider name or null
     */
    async extractProviderNameFromCell(cell) {
        return this.domNavigator.extractProviderNameFromCell(cell);
    }

    // ========================================================================
    // Event Simulation Methods (delegated to EventSimulator)
    // ========================================================================

    /**
     * V145.000: Random stabilization
     * @param {number} customMin - Optional custom minimum (ms)
     * @param {number} customMax - Optional custom maximum (ms)
     * @returns {Promise<number>} Actual delay time (ms)
     */
    async randomStabilize(customMin, customMax) {
        return this.eventSimulator.randomStabilize(customMin, customMax);
    }

    /**
     * V150.000: Random render wait
     * @returns {Promise<number>} Actual wait time (ms)
     */
    async randomRenderWait() {
        return this.eventSimulator.randomRenderWait();
    }

    /**
     * V145.000: Generate pixel jitter
     * @param {number} range - Pixel range
     * @returns {Object} X and Y offset values
     */
    generatePixelJitter(range) {
        return this.eventSimulator.generatePixelJitter(range);
    }

    /**
     * V145.000: Humanized Reliable Hover
     * @param {ElementHandle} cell - The odds cell to hover
     * @param {number} cellIndex - Cell index for logging
     * @param {string} axisName - Axis name (home/draw/away)
     * @param {number} totalCells - Total cells for logging
     * @returns {Promise<Object>} Result object
     */
    async performReliableHover(cell, cellIndex, axisName, totalCells) {
        return this.eventSimulator.performReliableHover(
            cell,
            () => this.randomRenderWait(),
            cellIndex,
            axisName,
            totalCells
        );
    }

    // ========================================================================
    // Anti-Fingerprint Methods (delegated to AntiFingerprint)
    // ========================================================================

    /**
     * V145.000: Scroll settle
     * @returns {Promise<void>}
     */
    async scrollSettle() {
        return this.antiFingerprint.scrollSettle();
    }

    /**
     * V146.000: Wait for React async rendering
     * @param {number} timeout - Maximum wait time (ms)
     * @returns {Promise<boolean>} True if rendered successfully
     */
    async waitForReactRender(timeout) {
        return this.antiFingerprint.waitForReactRender(timeout);
    }

    /**
     * V145.000: Handle overlays
     * @returns {Promise<boolean>} True if overlays were removed
     */
    async handleOverlays() {
        return this.antiFingerprint.handleOverlays();
    }

    // ========================================================================
    // V165.000 Event-Driven Methods (delegated to EventSimulator)
    // ========================================================================

    /**
     * V165.000: Wait for memory data to be ready
     * Event-driven replacement for randomStabilize()
     *
     * @returns {Promise<boolean>} True if memory data is ready
     */
    async waitForMemoryData() {
        return this.eventSimulator.waitForMemoryData();
    }

    /**
     * V165.000: Quick state check
     * Non-blocking check if memory data is ready
     *
     * @returns {Promise<boolean>} True if data is ready
     */
    async isMemoryDataReady() {
        return this.eventSimulator.isMemoryDataReady();
    }

    /**
     * V165.000: Wait for any state (memory OR modal OR odds cells)
     * Unified state detection with minimal latency
     *
     * @param {number} timeout - Max timeout (ms)
     * @returns {Promise<Object>} Result with state and method
     */
    async waitForAnyState(timeout = 2000) {
        return this.eventSimulator.waitForAnyState(timeout);
    }

    // ========================================================================
    // V166.000: [Genesis.FinalWall] Semantic Harvesting Methods
    // ========================================================================

    /**
     * V166.2: DOM Force Read (Ghost Fallback)
     * Scrapes visible odds directly from the DOM when network intercept fails.
     */
    async scrapeVisibleOddsFallback() {
        this.info('[V166.2] [Ghost] 👻 Engaging DOM Force Read (Fallback)...');
        
        try {
            const result = await this.page.evaluate(() => {
                const providers = [];
                const rows = document.querySelectorAll('div[data-v-037756ac].flex-col, tr'); // Adjust selector based on observation
                
                // Generic Row Scanner
                // We look for rows that contain a Provider Name and exactly 3 Odds-like numbers
                
                const allElements = document.querySelectorAll('*');
                const processed = new Set();
                
                // Target Keywords
                const targets = ['Pinnacle', 'bet365', 'William Hill', 'Ladbrokes', 'Bwin', 'Average'];
                
                // Helper: Find parent row
                const findRow = (el) => {
                    let p = el.parentElement;
                    while(p && p !== document.body) {
                        // A row usually has display: flex or is a TR, and has significant width
                        const style = window.getComputedStyle(p);
                        if (p.tagName === 'TR' || (style.display === 'flex' && p.innerText.includes('\n'))) {
                            return p;
                        }
                        p = p.parentElement;
                    }
                    return null;
                };

                // Scan for Provider Names
                for (const el of allElements) {
                    // Check if text is exactly a provider name or contains it strongly
                    const text = el.innerText?.trim();
                    if (!text) continue;
                    
                    const provider = targets.find(t => text.includes(t));
                    if (provider && !processed.has(provider)) {
                        const row = findRow(el);
                        if (row) {
                            // Scan row for odds
                            const rowText = row.innerText;
                            // Regex for odds: 1.01 - 100.00
                            const oddsMatches = rowText.match(/(\d+\.\d{2})/g);
                            
                            // We expect at least 3 odds (1x2) or maybe Payout
                            if (oddsMatches && oddsMatches.length >= 3) {
                                // Filter sanity
                                const validOdds = oddsMatches.map(parseFloat).filter(v => v > 1.0 && v < 50);
                                
                                if (validOdds.length >= 3) {
                                    // Payout calculation (approx)
                                    const [h, d, a] = validOdds.slice(0, 3);
                                    const margin = (1/h + 1/d + 1/a);
                                    const payout = margin > 0 ? (1 / margin) * 100 : 0;

                                    providers.push({
                                        provider: provider,
                                        instant_h: h,
                                        instant_d: d,
                                        instant_a: a,
                                        payout: parseFloat(payout.toFixed(2)),
                                        source: 'dom_fallback'
                                    });
                                    processed.add(provider);
                                }
                            }
                        }
                    }
                }
                return providers;
            });
            
            this.info(`[V166.2] [Ghost] Found ${result.length} providers via DOM.`);
            return result;
            
        } catch (e) {
            this.warn('[V166.2] [Ghost] DOM Scrape failed:', e.message);
            return [];
        }
    }

    /**
     * V166.1: Expand UI to show all bookmakers
     * Finds "Show all", "Show more" buttons and clicks them.
     * Robust to navigation and DOM updates.
     */
    async expandAllBookmakers() {
        this.info('[V166.1] 🔓 Expanding UI (Show all bookmakers)...');
        // Removed 'bookmakers' to avoid clicking nav links
        const expandKeywords = ['show all', 'show more', 'compare odds'];
        
        try {
            // Retry loop to handle DOM updates/navigation
            for (let i = 0; i < 3; i++) {
                // Wait for stability before querying
                await this.page.waitForLoadState('domcontentloaded').catch(() => {});
                
                // Find visible buttons from Node context
                // Filter out 'a' tags with real hrefs to prevent navigation
                const handles = await this.page.$$('button, div[role="button"], a');
                let clicked = false;

                for (const handle of handles) {
                    try {
                        const text = (await handle.innerText().catch(() => '')) || '';
                        
                        // Check keywords
                        if (expandKeywords.some(kw => text.toLowerCase().includes(kw))) {
                            
                            // Safety Check: Is it a navigation link?
                            const href = await handle.getAttribute('href').catch(() => null);
                            if (href && href.length > 1 && !href.startsWith('#') && !href.startsWith('javascript')) {
                                // It's a link, skip it
                                continue;
                            }

                            const isVisible = await handle.isVisible().catch(() => false);
                            if (isVisible) {
                                this.info(`[V166.1] Clicking expand button: "${text.substring(0, 20)}..."`);
                                
                                try {
                                    // Click with navigation race
                                    await Promise.all([
                                        handle.click({ timeout: 3000 }),
                                        this.page.waitForNavigation({ timeout: 2000 }).catch(() => {})
                                    ]);
                                } catch (e) {
                                    if (e.message.includes('destroyed') || e.message.includes('detached')) {
                                        this.info('[V166.1] Context updated during click, re-anchoring...');
                                    }
                                }
                                
                                // Wait for potential reaction
                                await this.page.waitForTimeout(2000);
                                clicked = true;
                                break; // DOM likely changed, break inner loop and re-query
                            }
                        }
                    } catch (e) {
                        // Ignore stale element errors
                    }
                }
                
                if (!clicked) break; // No more buttons found
            }
        } catch (e) {
            this.warn('[V166.1] ⚠️ Expand UI minor error:', e.message);
        }
        
        // Final stabilization
        await this.page.waitForLoadState('networkidle').catch(() => {});
    }

    /**
     * V166.5: Force activate lazy-loaded data via chunked scrolling
     */
    async activeAllData() {
        this.info('[V166.5] 🔄 Triggering Deep Chunked Scroll...');
        await this.page.evaluate(async () => {
            const totalHeight = document.body.scrollHeight;
            let current = 0;
            while (current < totalHeight) {
                window.scrollBy(0, 800);
                current += 800;
                await new Promise(r => setTimeout(r, 200));
            }
            await new Promise(r => setTimeout(r, 1000));
            window.scrollTo(0, 0);
        });
        await this.page.waitForTimeout(3000);
    }

    /**
     * V166.4: [Genesis.FinalOverwrite] Harvest by Semantic Patterns (Clean Scope)
     * =====================================================================
     * Fixed scope issues by explicitly defining configuration inside evaluate block.
     */
    async harvestBySemanticPatterns(options = {}) {
        this.info('[V166.4] [FinalOverwrite] 🔨 Overwriting logic to purge scope bugs...');
        // 1. 显式构建配置对象
        const runConfig = {
            titanIdSignatures: ['18', '32', '25', '16', '2'],
            semanticKeywords: ['Average', 'Highest', 'Opening', 'Pinnacle', 'bet365', 'William Hill', 'Ladbrokes', 'Bwin'],
            ...options
        };

        try {
            // Step 0: 展开 UI 并确保网络空闲
            await this.expandAllBookmakers();
            
            // Step 0.5: 深度滚动激活
            await this.activeAllData();
            
            // [V168.000] Genesis.Solidify: Fast Fail Mechanism
            // Check if key providers are present before proceeding with expensive operations
            const hasCrucialData = await this.page.evaluate(() => {
                const text = document.body.innerText;
                return text.includes('bet365') || text.includes('Pinnacle');
            });

            if (!hasCrucialData) {
                // Give a small grace period (5s) just in case
                try {
                    await this.page.waitForFunction(() => {
                        const t = document.body.innerText;
                        return t.includes('bet365') || t.includes('Pinnacle');
                    }, { timeout: 5000 });
                } catch (e) {
                    throw new Error('SOURCE_MISSING: Critical providers (bet365/Pinnacle) not found in DOM');
                }
            }
            
            await this.page.waitForLoadState('networkidle', { timeout: 5000 }).catch(() => {});

            // Step 1: 在浏览器沙盒内执行，显式传递 runConfig
            const semanticData = await this.page.evaluate((conf) => {
                const results = { candidates: [] };
                const rows = document.querySelectorAll('tr, div.flex-row, div.border-b');
                
                rows.forEach(row => {
                    const rowText = row.innerText || "";
                    let provider = null;
                    
                    // 基于 ID 指纹和关键字的精准识别
                    if (rowText.includes('Pinnacle')) provider = 'Pinnacle';
                    else if (rowText.includes('bet365')) provider = 'bet365';
                    else if (rowText.includes('William Hill')) provider = 'William Hill';
                    else if (rowText.includes('Ladbrokes')) provider = 'Ladbrokes';
                    else if (rowText.includes('Bwin')) provider = 'Bwin';
                    else if (rowText.includes('Average')) provider = 'Average';

                    if (provider) {
                        // 在行内寻找赔率格 (包含数字.数字数字 格式)
                        const oddsCells = Array.from(row.querySelectorAll('td, div')).filter(c => 
                            /^\s*\d+\.\d{2}\s*$/.test(c.innerText)
                        );
                        
                        if (oddsCells.length >= 3) {
                            const targetCell = oddsCells[0]; // 选取第一个有效格进行 Hover
                            const uniqueId = `genesis-${provider.replace(/\s+/g, '')}`;
                            targetCell.setAttribute('data-genesis-target', uniqueId);
                            
                            // Calc instant payout for fallback
                            const [h, d, a] = oddsCells.slice(0, 3).map(c => parseFloat(c.innerText));
                            const margin = (1/h + 1/d + 1/a);
                            const calcPayout = margin > 0 ? (1 / margin) * 100 : null;

                            results.candidates.push({
                                provider: provider,
                                selector: `[data-genesis-target="${uniqueId}"]`,
                                instantValue: h, // Use Home for now
                                calculatedPayout: calcPayout
                            });
                        }
                    }
                });
                return results;
            }, runConfig); // <--- 关键：确保此处传递的是 runConfig

            // Step 3: Deep Dive Trajectory Capture
            const config = runConfig; // Map back for consistent usage below
            if (config.enableTrajectoryCapture && semanticData.candidates.length > 0) {
                this.info(`[V166.4] 🎯 Identified targets: ${semanticData.candidates.map(t => t.provider).join(', ')}`);
                const trajectoryData = await this._captureTrajectories(semanticData.candidates);
                
                // Inject calculated payout if missing
                trajectoryData.forEach(td => {
                    const candidate = semanticData.candidates.find(c => c.provider === td.provider);
                    if (candidate && candidate.calculatedPayout && !td.market_payout) {
                        td.market_payout = parseFloat(candidate.calculatedPayout.toFixed(2));
                    }
                });

                return {
                    success: trajectoryData.length > 0,
                    data: trajectoryData,
                    providerCount: semanticData.candidates.length,
                    trajectoryCount: trajectoryData.length,
                    method: 'SEMANTIC_OVERWRITE'
                };
            } else {
                return {
                    success: false,
                    data: [],
                    providerCount: 0,
                    trajectoryCount: 0,
                    method: 'SEMANTIC_OVERWRITE'
                };
            }

        } catch (e) {
            this.error('[V166.4] ❌ Overwrite Execution Failed:', e.message);
            return { success: false, data: [], errors: [e.message] };
        }
    }

    /**
     * V169.000: [Genesis.DeepForensic] Humanized Hover Movement
     * =======================================================
     * 模拟人类鼠标移动轨迹，使用平滑曲线而非直线跳跃
     *
     * @param {number} startX - 起始 X 坐标
     * @param {number} startY - 起始 Y 坐标
     * @param {number} targetX - 目标 X 坐标
     * @param {number} targetY - 目标 Y 坐标
     * @param {number} steps - 移动步数 (默认 10)
     * @param {number} delayPerStep - 每步延迟 (ms, 默认 10)
     */
    async _humanizedHover(startX, startY, targetX, targetY, steps = 10, delayPerStep = 10) {
        const deltaX = (targetX - startX) / steps;
        const deltaY = (targetY - startY) / steps;

        for (let i = 0; i <= steps; i++) {
            const x = startX + deltaX * i;
            const y = startY + deltaY * i;

            // 添加轻微随机抖动，模拟人类手部微颤
            const jitter = this.generatePixelJitter(1);
            await this.page.mouse.move(x + jitter.x, y + jitter.y);
            await this.page.waitForTimeout(delayPerStep);
        }
    }

    /**
     * V169.000: [Genesis.DeepForensic] Ensure Tooltip Visible
     * ======================================================
     * 确保气泡弹出，如果 3 秒内未出现则尝试"刷新"动作
     *
     * @param {number} timeoutMs - 超时时间 (ms)
     * @returns {Promise<boolean>} 气泡是否可见
     */
    async _ensureTooltipVisible(timeoutMs = 3000) {
        const startTime = Date.now();
        const checkInterval = 200;

        while (Date.now() - startTime < timeoutMs) {
            const hasTooltip = await this.page.evaluate(() => {
                const allDivs = Array.from(document.querySelectorAll('div, ul, span'));
                return allDivs.some(el => {
                    const style = window.getComputedStyle(el);
                    const isVisible = style.display !== 'none' && style.visibility !== 'hidden' && parseFloat(style.opacity) > 0;
                    const isFloating = style.position === 'absolute' || style.position === 'fixed';
                    const text = el.innerText || '';
                    const hasTime = /\d{2}:\d{2}/.test(text);
                    const hasOdds = /\d+\.\d{2}/.test(text);
                    return isVisible && isFloating && hasTime && hasOdds;
                });
            });

            if (hasTooltip) {
                return true;
            }

            // 如果超过一半时间仍未出现，尝试"刷新"动作
            if (Date.now() - startTime > timeoutMs / 2) {
                this.info('[V169.000] 🔄 Tooltip not appearing, trying refresh...');
                // 移开鼠标
                await this.page.mouse.move(0, 0);
                await this.page.waitForTimeout(300);
                // 重新移入 (由外层调用处理)
                return false; // 返回 false 让外层重试
            }

            await this.page.waitForTimeout(checkInterval);
        }

        return false;
    }

    /**
     * V169.100: [Genesis.VisualAudit] Force Trigger Tooltip
     * Bypass physical mouse blocks by dispatching events directly
     * @param {string} selector - Target element selector
     */
    async _forceTriggerTooltip(selector) {
        this.info(`[V169.100] ⚡ Applying ForceTrigger on ${selector}...`);
        try {
            await this.page.dispatchEvent(selector, 'mouseover');
            await this.page.dispatchEvent(selector, 'mouseenter');
        } catch (e) {
            this.warn(`[V169.100] ForceTrigger failed: ${e.message}`);
        }
    }

    /**
     * V169.000: [Genesis.DeepForensic] Deep Trajectory Capture with Humanized Interaction
     * ==================================================================================
     * Deep sampling: Humanized Hover -> Raw Text Dump -> Line-by-Line Regex -> L3 Data
     *
     * 增强:
     * - 人类化鼠标移动轨迹
     * - 坐标校准 (scrollIntoView + 1s 等待)
     * - 多点尝试 (center, topLeft)
     * - 气泡死亡等待 (3秒超时 + 刷新动作)
     */
    async _captureTrajectories(targets) {
        const results = [];

        for (const target of targets) {
            const hoverPoints = [
                { name: 'center', offset: { x: 0.5, y: 0.5 } },
                { name: 'topLeft', offset: { x: 0.2, y: 0.2 } }
            ];

            let captured = false;

            for (const point of hoverPoints) {
                if (captured) break;

                try {
                    this.info(`[V169.000] 🖱️  Hovering ${target.provider} (${point.name})...`);

                    const element = await this.page.$(target.selector);
                    if (!element) continue;

                    // V169.000: 坐标校准 - 滚动到视野 + 强制等待 1 秒
                    await element.evaluate(el => {
                        el.scrollIntoView({ block: 'center', inline: 'center' });
                    });
                    await this.page.waitForTimeout(1000);

                    const box = await element.boundingBox();
                    if (!box) continue;

                    // 计算目标点坐标
                    const targetX = box.x + box.width * point.offset.x;
                    const targetY = box.y + box.height * point.offset.y;

                    // V169.000: 获取当前鼠标位置 (假设在页面左上角)
                    const currentPos = { x: 0, y: 0 };

                    // V169.000: 人类化悬停 - 平滑移动
                    await this._humanizedHover(
                        currentPos.x,
                        currentPos.y,
                        targetX,
                        targetY,
                        10,  // steps
                        15   // delayPerStep (ms)
                    );

                    // V169.000: 停留时长 - 随机 500-1000ms，模拟人类阅读
                    const dwellTime = 500 + Math.random() * 500;
                    await this.page.waitForTimeout(dwellTime);

                    // V169.000: 气泡死亡等待 - 初始检查
                    let tooltipAppeared = await this._ensureTooltipVisible(2000);

                    // [V169.100] Force Trigger Fallback
                    if (!tooltipAppeared) {
                        this.info('[V169.100] 🛡️ Physical hover blocked. Attempting ForceTrigger...');
                        await this._forceTriggerTooltip(target.selector);
                        await this.page.waitForTimeout(1000);
                        tooltipAppeared = await this._ensureTooltipVisible(2000);
                    }

                    if (!tooltipAppeared && point.name === 'center') {
                        this.info(`[V169.000] ⚠️  Tooltip not appeared at ${point.name}, trying next point...`);
                        // 移开鼠标，准备尝试下一个点
                        await this.page.mouse.move(0, 0);
                        await this.page.waitForTimeout(300);
                        continue;
                    }

                    // 提取 tooltip 文本
                    const tooltipText = await this.page.evaluate(() => {
                        const allDivs = Array.from(document.querySelectorAll('div, ul, span, table'));
                        // Filter candidates: visible, floating, contains time + odds pattern
                        const candidates = allDivs.filter(el => {
                            const style = window.getComputedStyle(el);
                            const isVisible = style.display !== 'none' && style.visibility !== 'hidden' && parseFloat(style.opacity) > 0;
                            const isFloating = style.position === 'absolute' || style.position === 'fixed';
                            const text = el.innerText || '';
                            // Must contain at least one time pattern AND one odds-like pattern
                            const hasTime = /\d{2}:\d{2}/.test(text);
                            const hasOdds = /\d+\.\d{2}/.test(text);
                            return isVisible && isFloating && hasTime && hasOdds;
                        });

                        // Sort by z-index descending
                        candidates.sort((a, b) => {
                             return (parseInt(window.getComputedStyle(b).zIndex) || 0) - (parseInt(window.getComputedStyle(a).zIndex) || 0);
                        });

                        return candidates.length > 0 ? candidates[0].innerText : null;
                    });

                    if (tooltipText) {
                    this.info('[[RAW TOOLTIP]]:', tooltipText.replace(/\n/g, ' | ').substring(0, 150));
                    
                    // 2. LINE-BY-LINE PARSING (State Machine)
                    const lines = tooltipText.split('\n');
                    const curve = [];
                    let lastTime = null;
                    let linesSinceTime = 0;
                    
                    lines.forEach(line => {
                        const cleanLine = line.trim().replace(/\s+/g, ' ');
                        if (!cleanLine) return;

                        // Time Match: "24 May, 22:10", "10:00", "Today, 10:00"
                        const timeMatch = cleanLine.match(/^(\d{2}\s\w{3},?\s\d{2}:\d{2}|\d{2}\/\d{2}\s\d{2}:\d{2}|\d{2}:\d{2}|Today,?\s\d{2}:\d{2}|Yesterday,?\s\d{2}:\d{2})/i);
                        
                        if (timeMatch) {
                            lastTime = timeMatch[0];
                            linesSinceTime = 0;
                            // Check if this line ALSO has odds (same line case)
                            const inlineOdds = cleanLine.match(/(\d+\.\d{2})/);
                            if (inlineOdds) {
                                // Fallthrough to odds processing with this line
                            } else {
                                return; // Just a time line, wait for next lines
                            }
                        }

                        // Odds Match: Look for odds if we have a recent time anchor (within 3 lines)
                        if (lastTime && linesSinceTime <= 2) {
                             const allNumbers = cleanLine.match(/(\d+\.\d{2}|\d+\.\d{1}|\d{2,3}%)/g);
                             if (allNumbers) {
                                let oddsVal = null;
                                let payoutVal = null;

                                allNumbers.forEach(numStr => {
                                    const val = parseFloat(numStr.replace('%', ''));
                                    if (isNaN(val)) return;

                                    if (val >= 1.01 && val <= 50.0) {
                                        oddsVal = val;
                                    } else if (val > 50.0 && val <= 100.0) {
                                        payoutVal = val;
                                    }
                                });

                                if (oddsVal !== null) {
                                    const point = {
                                        raw_time: lastTime,
                                        v: oddsVal
                                    };
                                if (payoutVal !== null) {
                                    point.payout = payoutVal;
                                    // DEBUG: Log payout capture
                                    // console.log(`[Payout] ${target.provider} @ ${lastTime}: ${payoutVal}%`);
                                }
                                
                                // Deduplicate: Don't add if identical to last point (timestamp & value)
                                    // Actually, we might have multiple updates at same time?
                                    // Let's just push.
                                    curve.push(point);
                                    
                                    // Reset time anchor to avoid reusing it for unrelated numbers further down?
                                    // Usually 1 Time -> 1 Odds row.
                                    lastTime = null; 
                                }
                             }
                        }
                        
                        if (lastTime) linesSinceTime++;
                    });

                    if (curve.length > 0) {
                        results.push({
                            provider: target.provider,
                            dimension: '1x2',
                            instant: target.instantValue,
                            curve: curve,
                            _meta: { source: 'brute_force_text' }
                        });
                        this.info(`[V169.000] ✅ Extracted ${curve.length} points for ${target.provider}`);
                        captured = true;
                    } else {
                        this.warn(`[V169.000] ⚠️ Tooltip text found but no valid lines parsed.`);
                    }
                } else {
                    this.warn(`[V169.000] ⚠️ No valid tooltip found for ${target.provider}`);
                }

                // 移开鼠标，准备处理下一个目标
                await this.page.mouse.move(0, 0);
                await this.page.waitForTimeout(300);

                } catch (e) {
                    this.warn(`[V169.000] ⚠️ Failed ${target.provider} (${point.name}): ${e.message}`);
                    // 移开鼠标，准备重试
                    await this.page.mouse.move(0, 0);
                    await this.page.waitForTimeout(300);
                }
            }
        }

        return results;
    }

    /**
     * V166.000: [Genesis.FinalWall] Pixel Jitter Generator
     * =============================================
     * 生成像素级抖动，模拟真实用户鼠标移动
     *
     * @param {number} range - 抖动范围（像素）
     * @returns {Object} {x, y} 抖动偏移量
     */
    generatePixelJitter(range = 3) {
        const jitter = (Math.random() - 0.5) * 2 * range;
        const jitterInt = Math.round(jitter);

        // Random jitter between -range and +range
        const x = Math.floor(Math.random() * (range * 2 + 1)) - range;
        const y = Math.floor(Math.random() * (range * 2 + 1)) - range;

        return { x, y };
    }

    // ========================================================================
    // Deprecated Methods (for backward compatibility)
    // ========================================================================

    /**
     * V127.000: Randomized jitter wait (DEPRECATED)
     * @param {number} min - Minimum wait time (ms)
     * @param {number} jitter - Jitter range (ms)
     * @returns {Promise<void>}
     */
    async jitterWait(min = 2000, jitter = 1500) {
        console.warn('[V165.000] ⚠️  jitterWait() is DEPRECATED, use waitForMemoryData() instead');
        const delay = Math.floor(Math.random() * jitter) + min;
        await this.page.waitForTimeout(delay);
    }
}

module.exports = { SurgicalInteraction };
