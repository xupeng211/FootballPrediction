/**
 * V107.000 Hover + Modal Engine
 * ==============================
 *
 * V107.000: 回归 OddsHarvester 物理交互模式
 * - 终止 API 解码尝试 (V106.004-V106.015 已证明 API 响应采用非标加密)
 * - 基于 OddsHarvester 的 odds_history_extractor.py 逻辑重构
 *
 * V108.000: 多维坐标悬停逻辑优化
 * - 三轴数据提取: Home/Draw/Away 每个轴独立悬停
 * - 数据封装: { provider, axis_1/2/3: {init, history} }
 * - Promise.race 竞速模型优化响应时间
 *
 * 核心策略:
 * 1. 目标识别: div.border-black-borders.flex.h-9 (庄家行)
 * 2. 三轴物理交互: 对每个 odds cell 执行 hover() 触发弹窗
 * 3. 关键等待: Promise.race 监测弹窗文本出现
 * 4. DOM 提取: 明文 HTML → 初盘数值 + 变盘历史
 *
 * @version V108.000
 * @since 2026-01-27
 */

'use strict';

const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const TARGET_URL = 'https://www.oddsportal.com/football/england/premier-league/brighton-everton-vPKFVEM6/';
const OUTPUT_DIR = path.join(__dirname, '../../logs/v107_hover');

// Ensure output directory exists
if (!fs.existsSync(OUTPUT_DIR)) {
    fs.mkdirSync(OUTPUT_DIR, { recursive: true });
}

const CONFIG = {
    userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
    viewport: { width: 1920, height: 1080 },
    timeout: 60000,
    hover: {
        waitMin: 1500,
        waitMax: 2500,
        modalTimeout: 5000,
        // V108.000: Promise.race 竞速优化 - 检测文本出现而非完整 DOM
        raceOptimization: true,
        textDetectionTimeout: 3000
    },
    maxBookmakers: 10,
    // V108.000: 三轴配置
    axes: ['home', 'draw', 'away'],
    axisNames: {
        home: 'axis_1',
        draw: 'axis_2',
        away: 'axis_3'
    }
};

const REALISTIC_HEADERS = {
    'Accept-Language': 'en-US,en;q=0.9',
    'Sec-Fetch-Dest': 'document',
    'Sec-Fetch-Mode': 'navigate',
    'Sec-Fetch-Site': 'none',
    'Referer': 'https://www.oddsportal.com/football/england/premier-league/'
};

const log = {
    info: (msg) => console.log(`[V108.000] [INFO] ${msg}`),
    success: (msg) => console.log(`[V108.000] [✓] ${msg}`),
    warn: (msg) => console.warn(`[V108.000] [!] ${msg}`),
    error: (msg) => console.error(`[V108.000] [✗] ${msg}`),
    section: (title) => {
        console.log('\n' + '='.repeat(70));
        console.log(`[V108.000] ${title}`);
        console.log('='.repeat(70));
    }
};

/**
 * Random delay to simulate human behavior
 */
function randomDelay(min, max) {
    return Math.floor(Math.random() * (max - min + 1)) + min;
}

/**
 * Simulate mouse trajectory before hover
 */
async function simulateMouseTrajectory(page) {
    const x = Math.floor(Math.random() * 500) + 100;
    const y = Math.floor(Math.random() * 300) + 100;
    await page.mouse.move(x, y);
    await page.waitForTimeout(randomDelay(100, 300));
}

/**
 * Parse opening odds from modal HTML
 * V107.003: Fixed parsing for actual modal structure
 */
function parseOpeningOdds(modalHtml) {
    // Look for "Opening odds:" section and extract everything until the next div
    const openingMatch = modalHtml.match(/Opening odds:<\/div>([\s\S]*?)<div class="flex border-t/);

    if (openingMatch) {
        const content = openingMatch[1];
        // Extract date: pattern like "24 Jan, 23:03"
        const dateMatch = content.match(/(\d{2}\s[A-Za-z]{3},\s\d{2}:\d{2})/);
        // Extract odds value: pattern like "1.89"
        const oddsMatch = content.match(/(\d+\.\d+)/);

        if (dateMatch && oddsMatch) {
            return {
                time: dateMatch[0],
                home: parseFloat(oddsMatch[0]) || null
            };
        }
    }

    return null;
}

/**
 * Parse history movement list from modal HTML
 * V107.003: Fixed parsing - use greedy match to capture nested structure
 */
function parseHistoryMovement(modalHtml) {
    const movements = [];

    // First, add the opening odds as a historical point
    const openingOdds = parseOpeningOdds(modalHtml);
    if (openingOdds && openingOdds.home) {
        movements.push({
            time: openingOdds.time,
            home: openingOdds.home,
            type: 'opening'
        });
    }

    // Then, extract the current/last odds from the top section
    // V107.003: Use greedy match to capture complete nested structure
    const currentMatch = modalHtml.match(/<div class="flex flex-row gap-3">([\s\S]*?)<\/div>\s*<div class="mt-2/);

    if (currentMatch) {
        const content = currentMatch[1];
        // Extract date and odds value using simple patterns
        const dateMatch = content.match(/(\d{2}\s[A-Za-z]{3},\s\d{2}:\d{2})/);
        const oddsMatch = content.match(/(\d+\.\d+)/);

        if (dateMatch && oddsMatch) {
            const currentOdds = parseFloat(oddsMatch[0]) || null;

            // Only add if different from opening
            if (movements.length === 0 || currentOdds !== movements[0].home) {
                movements.push({
                    time: dateMatch[0],
                    home: currentOdds,
                    type: 'current'
                });
            }
        }
    }

    return movements;
}

/**
 * V108.000: Promise.race 竞速模型 - 检测弹窗文本出现
 * 优化响应时间，不再等待完整 DOM 渲染
 */
async function waitForModalWithRace(page, timeout = CONFIG.hover.textDetectionTimeout) {
    const modalSelector = 'h3:has-text("Odds movement")';

    // Promise.race: 文本检测 vs 超时
    const textDetectionPromise = page.waitForSelector(modalSelector, {
        state: 'visible',
        timeout: timeout
    });

    const timeoutPromise = new Promise((_, reject) =>
        setTimeout(() => reject(new Error('Text detection timeout')), timeout)
    );

    try {
        await Promise.race([textDetectionPromise, timeoutPromise]);
        return true;
    } catch (e) {
        return false;
    }
}

/**
 * V108.000: 从单个轴 (Home/Draw/Away) 提取数据
 */
async function extractFromSingleAxis(page, axisCell, axisName, axisIndex) {
    const axisResult = {
        axis: axisName,
        axisIndex: axisIndex,
        init: null,
        history: [],
        success: false,
        modalHtml: null
    };

    try {
        log.info(`    Processing axis ${axisIndex + 1}/3 (${axisName})...`);

        // Step 1: Simulate mouse trajectory
        await simulateMouseTrajectory(page);

        // Step 2: Physical hover on axis cell
        log.info(`    Hovering over ${axisName} cell...`);
        await axisCell.hover();

        // Random wait after hover
        await page.waitForTimeout(randomDelay(CONFIG.hover.waitMin, CONFIG.hover.waitMax));

        // Step 3: Wait for modal (V108.000: 使用 Promise.race 优化)
        log.info(`    Waiting for modal...`);
        const modalAppeared = await waitForModalWithRace(page);

        if (!modalAppeared) {
            log.warn(`    Modal timeout for ${axisName}`);
            return axisResult;
        }

        log.success(`    Modal appeared for ${axisName}!`);

        // Step 4: Get modal HTML
        const modalSelector = 'h3:has-text("Odds movement")';
        const modalElement = await page.$(modalSelector);

        if (!modalElement) {
            log.warn(`    Modal element not found for ${axisName}`);
            return axisResult;
        }

        let modalHtml = null;
        try {
            modalHtml = await modalElement.evaluate((el) => {
                let container = el;
                let depth = 0;
                const maxDepth = 10;

                while (container && depth < maxDepth) {
                    const classes = container.className || '';
                    const hasModalClass = /modal|popup|dialog|tooltip|dropdown/i.test(classes);
                    const hasRole = container.getAttribute('role') === 'dialog';
                    const isFixedOrAbsolute = /fixed|absolute/.test(window.getComputedStyle(container).position);

                    if (hasModalClass || hasRole || (isFixedOrAbsolute && classes.length > 10)) {
                        return container.outerHTML;
                    }

                    container = container.parentElement;
                    depth++;
                }

                return el.parentElement?.outerHTML || el.outerHTML;
            });
        } catch (e) {
            log.warn(`    Failed to get modal HTML: ${e.message}`);
        }

        axisResult.modalHtml = modalHtml;

        if (!modalHtml) {
            return axisResult;
        }

        // Step 5: Parse opening odds (init value)
        const openingOdds = parseOpeningOdds(modalHtml);
        if (openingOdds && openingOdds.home) {
            axisResult.init = openingOdds.home;
            log.success(`    Init value for ${axisName}: ${axisResult.init}`);
        }

        // Step 6: Parse history movements
        const movements = parseHistoryMovement(modalHtml);
        axisResult.history = movements;
        log.success(`    Captured ${movements.length} history points for ${axisName}`);

        axisResult.success = movements.length > 0 || axisResult.init !== null;

        // Move mouse away to close modal before next axis
        await page.mouse.move(0, 0);
        await page.waitForTimeout(500);

    } catch (error) {
        log.error(`    Error extracting ${axisName}: ${error.message}`);
    }

    return axisResult;
}

/**
 * V108.000: 从庄家行提取三轴数据 (Home/Draw/Away)
 * 返回格式: { provider, axis_1/2/3: {init, history} }
 */
async function extractMultiAxisFromRow(page, rowElement, bookmakerIndex) {
    log.info(`\nProcessing bookmaker #${bookmakerIndex + 1} (Multi-Axis Mode)...`);

    const result = {
        provider: null,
        axis_1: { init: null, history: [] },
        axis_2: { init: null, history: [] },
        axis_3: { init: null, history: [] },
        success: false,
        error: null
    };

    try {
        // Step 1: 识别行类型并获取庄家名称
        const elementType = await rowElement.evaluate(el => {
            if (el.classList.contains('odds-cell')) return 'odds-cell';
            if (el.classList.contains('h-9')) return 'row';
            return 'unknown';
        });

        log.info(`  Element type: ${elementType}`);

        // 获取庄家名称
        const nameElement = await rowElement.$('img[alt], span, div[class*="name"]');
        if (nameElement) {
            result.provider = await nameElement.evaluate(el =>
                el.getAttribute('alt') || el.textContent?.trim() || `Bookmaker_${bookmakerIndex}`
            );
            log.info(`  Provider: ${result.provider}`);
        } else {
            result.provider = `Bookmaker_${bookmakerIndex}`;
        }

        // Step 2: 找到所有 odds cells (Home/Draw/Away)
        let oddsCells = [];

        if (elementType === 'row') {
            // 对于行元素，获取所有 odds cells
            oddsCells = await rowElement.$$('div.odds-cell, div[class*="odd"], span[class*="odd"]');
            log.info(`  Found ${oddsCells.length} odds cells in row`);
        } else if (elementType === 'odds-cell') {
            // 对于单个 cell，获取兄弟 cells
            const parent = await rowElement.evaluateHandle(el => el.parentElement);
            if (parent) {
                oddsCells = await parent.$$('div.odds-cell, div[class*="odd"], span[class*="odd"]');
            }
            oddsCells = oddsCells.length > 0 ? oddsCells : [rowElement];
            log.info(`  Found ${oddsCells.length} odds cells (including current)`);
        }

        if (oddsCells.length === 0) {
            result.error = 'No odds cells found';
            return result;
        }

        // Step 3: 只处理前 3 个 odds cells (Home/Draw/Away)
        const targetCells = oddsCells.slice(0, 3);
        log.info(`  Processing ${targetCells.length} axes (max 3)...`);

        // Step 4: 对每个轴执行悬停和数据提取
        for (let i = 0; i < targetCells.length; i++) {
            const axisName = CONFIG.axes[i]; // home, draw, away
            const axisKey = CONFIG.axisNames[axisName]; // axis_1, axis_2, axis_3

            log.info(`  === Axis ${i + 1}/${targetCells.length} (${axisName}) ===`);

            const axisResult = await extractFromSingleAxis(page, targetCells[i], axisName, i);

            // 将结果存储到对应轴
            result[axisKey] = {
                init: axisResult.init,
                history: axisResult.history
            };

            if (axisResult.success) {
                log.success(`  Axis ${axisName} extraction SUCCESS`);
            } else {
                log.warn(`  Axis ${axisName} extraction FAILED`);
            }

            // 轴之间短暂等待
            if (i < targetCells.length - 1) {
                await page.waitForTimeout(randomDelay(800, 1200));
            }
        }

        // Step 5: 判断整体成功
        const axesWithData = CONFIG.axes.filter((axis, i) => {
            const axisKey = CONFIG.axisNames[axis];
            return result[axisKey].init !== null || result[axisKey].history.length > 0;
        });

        result.success = axesWithData.length >= 2; // 至少 2 个轴有数据

        log.success(`  Multi-axis extraction complete: ${axesWithData.length}/3 axes with data`);

        // Step 6: 保存调试信息
        const debugData = {
            provider: result.provider,
            timestamp: new Date().toISOString(),
            axesData: {
                axis_1: result.axis_1,
                axis_2: result.axis_2,
                axis_3: result.axis_3
            }
        };

        const filename = `multi_axis_${bookmakerIndex}_${Date.now()}.json`;
        const filepath = path.join(OUTPUT_DIR, filename);
        fs.writeFileSync(filepath, JSON.stringify(debugData, null, 2), 'utf-8');
        log.info(`  Saved multi-axis data to: ${filepath}`);

    } catch (error) {
        result.error = error.message;
        log.error(`  Error: ${error.message}`);
    } finally {
        // Always move mouse away
        await page.mouse.move(0, 0);
        await page.waitForTimeout(randomDelay(500, 1000));
    }

    return result;
}

/**
 * V108.000: 兼容性包装器 - 保持向后兼容
 */
async function extractFromBookmakerRow(page, rowElement, bookmakerIndex) {
    // V108.000: 调用新的多轴提取函数
    return await extractMultiAxisFromRow(page, rowElement, bookmakerIndex);
}

/**
 * Main extraction function
 */
async function runHoverModalExtraction() {
    log.section('V108.000 HOVER + MODAL ENGINE (Multi-Axis)');
    log.info('Target URL:', TARGET_URL);
    log.info('[V108.000] Multi-Axis Mode: ENABLED (Home/Draw/Away)');
    log.info('[V108.000] Promise.race Optimization: ENABLED');
    log.info('');

    const browser = await chromium.launch({
        headless: false, // Use headed mode to see hover interactions
        args: ['--disable-blink-features=AutomationControlled'],
        ignoreDefaultArgs: ['--enable-automation']
    });

    const context = await browser.newContext({
        userAgent: CONFIG.userAgent,
        viewport: CONFIG.viewport
    });

    await context.addInitScript(() => {
        Object.defineProperty(navigator, 'webdriver', { get: () => false });
    });

    const page = await context.newPage();
    await page.setExtraHTTPHeaders(REALISTIC_HEADERS);

    try {
        log.section('STEP 1: PAGE LOAD');
        log.info(`Navigating to: ${TARGET_URL}`);
        await page.goto(TARGET_URL, {
            timeout: CONFIG.timeout,
            waitUntil: 'networkidle'
        });
        log.success(`Page loaded successfully`);
        log.info(`Waiting for dynamic content to render (this may take a while)...`);

        // V107.002: Wait for dynamic content to load
        // The page uses client-side rendering, so we need to wait for odds cells to appear
        let waitAttempts = 0;
        const maxWaitAttempts = 30; // 30 seconds max

        log.info('Waiting for odds cells to appear...');
        while (waitAttempts < maxWaitAttempts) {
            const oddsCellCount = await page.$$eval('div.odds-cell, .odds-cell, div[class*="odds-cell"]', els => els.length);
            if (oddsCellCount > 0) {
                log.success(`Found ${oddsCellCount} odds cells after ${waitAttempts} seconds`);
                break;
            }
            await page.waitForTimeout(1000);
            waitAttempts++;

            if (waitAttempts % 5 === 0) {
                log.info(`Still waiting... (${waitAttempts}s)`);
            }
        }

        if (waitAttempts >= maxWaitAttempts) {
            log.warn('No odds cells found after max wait time');
            log.info('Page might be geo-blocked or content not available');
        }

        await page.waitForTimeout(randomDelay(2000, 3000));

        log.section('STEP 2: FIND BOOKMAKER ROWS');

        // V107.001: Use correct selectors discovered through DOM analysis
        const possibleSelectors = [
            'div.flex.h-9.border-b.border-l.border-r.border-black-borders.text-xs', // V107.001 discovered
            'div.odds-cell', // Direct odds cell selector
            'div[class*="border"][class*="flex"][class*="h-9"]', // Fallback
        ];

        let bookmakerRows = [];
        let usedSelector = null;

        for (const selector of possibleSelectors) {
            const rows = await page.$$(selector);
            log.info(`Testing selector: ${selector}`);
            log.info(`  Found ${rows.length} elements`);
            if (rows.length > 0) {
                // For odds-cell selector, we need to get parent rows
                if (selector.includes('odds-cell')) {
                    log.info(`  Getting parent rows for odds cells...`);
                    // Get unique parent rows
                    const parentRows = new Set();
                    for (const cell of rows) {
                        const parent = await cell.evaluateHandle(el => {
                            let p = el.parentElement;
                            while (p) {
                                if (p.classList.contains('h-9') && p.classList.contains('border-black-borders')) {
                                    return p;
                                }
                                p = p.parentElement;
                            }
                            return null;
                        });
                        if (parent) {
                            const parentId = await parent.evaluate(el => el.className);
                            parentRows.add(parentId);
                        }
                    }
                    log.info(`  Found ${parentRows.size} unique parent rows`);
                    if (parentRows.size > 0) {
                        bookmakerRows = rows; // Use odds cells directly
                        usedSelector = selector;
                        break;
                    }
                } else {
                    bookmakerRows = rows;
                    usedSelector = selector;
                    break;
                }
            }
        }

        if (bookmakerRows.length === 0) {
            log.error('No bookmaker rows found!');
            log.info('Dumping page HTML for analysis...');
            const bodyHtml = await page.evaluate(() => document.body.innerHTML);
            const dumpPath = path.join(OUTPUT_DIR, 'page_dump.html');
            fs.writeFileSync(dumpPath, bodyHtml, 'utf-8');
            log.info(`Page HTML saved to: ${dumpPath}`);
            return;
        }

        log.success(`Found ${bookmakerRows.length} bookmaker rows`);
        log.info(`Using selector: ${usedSelector}`);

        // Limit to max bookmakers
        const targetRows = bookmakerRows.slice(0, CONFIG.maxBookmakers);
        log.info(`Processing ${targetRows.length} rows (max: ${CONFIG.maxBookmakers})`);

        log.section('STEP 3: HOVER + EXTRACTION');

        const results = [];
        let successCount = 0;

        for (let i = 0; i < targetRows.length; i++) {
            log.info(`\n--- Bookmaker ${i + 1}/${targetRows.length} ---`);

            const result = await extractFromBookmakerRow(page, targetRows[i], i);
            results.push(result);

            if (result.success) {
                successCount++;
            }

            // Wait between extractions
            if (i < targetRows.length - 1) {
                await page.waitForTimeout(randomDelay(1500, 2500));
            }
        }

        log.section('STEP 4: RESULTS SUMMARY (V108.000 Multi-Axis)');
        log.info(`Total processed: ${results.length}`);
        log.success(`Successful extractions: ${successCount}`);
        log.info(`Multi-Axis Capture Rate: ${((successCount / results.length) * 100).toFixed(1)}%`);

        // V108.000: Calculate multi-axis statistics
        let withCompleteAxisCount = 0;
        let totalAxesCaptured = 0;
        let totalInitValues = 0;
        let totalHistoryPoints = 0;

        for (const result of results) {
            if (result.success) {
                // Count how many axes have data
                const axesWithData = CONFIG.axes.filter((axis, i) => {
                    const axisKey = CONFIG.axisNames[axis];
                    return result[axisKey].init !== null || result[axisKey].history.length > 0;
                });
                totalAxesCaptured += axesWithData.length;

                // Count init values
                for (const axis of CONFIG.axes) {
                    const axisKey = CONFIG.axisNames[axis];
                    if (result[axisKey].init !== null) {
                        totalInitValues++;
                    }
                    totalHistoryPoints += result[axisKey].history.length;
                }

                if (axesWithData.length >= 2) {
                    withCompleteAxisCount++;
                }
            }
        }

        const avgAxesPerResult = results.length > 0 ? (totalAxesCaptured / results.length).toFixed(1) : 0;
        log.success(`Providers with 2+ axes: ${withCompleteAxisCount}`);
        log.success(`Average axes per result: ${avgAxesPerResult}`);
        log.success(`Total init values captured: ${totalInitValues}`);
        log.success(`Total history points: ${totalHistoryPoints}`);

        // Check success criteria (V108.000 updated)
        const successCriteria = successCount >= 2 && withCompleteAxisCount >= 2 && totalInitValues >= 4;
        log.info('');
        log.info('V108.000 Success Criteria Check:');
        log.info(`  ✓ 2+ providers with data: ${successCount >= 2}`);
        log.info(`  ✓ 2+ providers with 2+ axes: ${withCompleteAxisCount >= 2}`);
        log.info(`  ✓ 4+ init values captured: ${totalInitValues >= 4}`);
        log.info(`  ✓ Multi-Axis Capture Rate > 0%: ${successCount > 0}`);

        log.section('STEP 5: SAMPLE DATA OUTPUT (V108.000 Format)');

        // Output first successful multi-axis result
        const firstSuccess = results.find(r => r.success);
        if (firstSuccess) {
            log.success(`First successful multi-axis extraction:`);
            console.log(JSON.stringify({
                provider: firstSuccess.provider || 'Unknown',
                axis_1: {
                    init: firstSuccess.axis_1.init,
                    history_count: firstSuccess.axis_1.history.length
                },
                axis_2: {
                    init: firstSuccess.axis_2.init,
                    history_count: firstSuccess.axis_2.history.length
                },
                axis_3: {
                    init: firstSuccess.axis_3.init,
                    history_count: firstSuccess.axis_3.history.length
                }
            }, null, 2));
            console.log('');
            console.log('Full history for axis_1 (Home):');
            console.log(JSON.stringify(firstSuccess.axis_1.history.slice(0, 5), null, 2));
        }

        // Save full results
        const resultsPath = path.join(OUTPUT_DIR, `v108_extraction_results_${Date.now()}.json`);
        fs.writeFileSync(resultsPath, JSON.stringify(results, null, 2), 'utf-8');
        log.success(`Full V108.000 results saved to: ${resultsPath}`);

        log.section('FINAL STATUS');
        if (successCriteria) {
            log.success('[V108.000] Multi-Axis Sync: ACTIVE. 3-axis data captured successfully.');
            console.log('');
            console.log('V108.000 三轴时序 JSON (第一个提供商):');
            console.log(JSON.stringify(firstSuccess, null, 2));
        } else {
            log.warn('[V108.000] Partial success - some axes captured but below threshold');
        }

    } catch (error) {
        log.error(`Extraction failed: ${error.message}`);
        console.error(error.stack);
    } finally {
        log.info('Closing browser...');
        await page.close();
        await context.close();
        await browser.close();
    }
}

if (require.main === module) {
    runHoverModalExtraction().catch(error => {
        console.error('[V108.000] Fatal error:', error);
        process.exit(1);
    });
}

// V108.000: Export multi-axis functions for integration
module.exports = {
    runHoverModalExtraction,
    extractMultiAxisFromRow,
    extractFromSingleAxis,
    waitForModalWithRace
};
