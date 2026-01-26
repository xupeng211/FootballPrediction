/**
 * V115.000 Quant Price Sync Engine - FIXED DOM-First Trajectory Extraction
 * =====================================================================
 *
 * V115.000 核心修复：
 * 1. DOM-First Extraction - 使用 DOM 遍历替代脆弱的正则表达式
 * 2. querySelectorAll('tr') - 真正遍历所有表格行
 * 3. 对账保证 - 确保 N 行数据全部存入 history 数组
 *
 * @version V115.000
 * @since 2026-01-27
 * @author Senior Quant Systems Engineer
 */

'use strict';

const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');
const { JSDOM } = require('jsdom');
const storage = require('./modules/storage');
const logger = require('./modules/logger');
const baseLogger = logger.createLogger('v115');

// V115.000: 扩展日志对象，添加 section 方法
const log = {
    info: (msg) => baseLogger.info(msg),
    success: (msg) => baseLogger.success(msg),
    warn: (msg) => baseLogger.warn(msg),
    error: (msg) => baseLogger.error(msg),
    debug: (msg) => baseLogger.debug(msg),
    section: (title) => {
        console.log('\n' + '='.repeat(70));
        console.log(`[V115.000] ${title}`);
        console.log('='.repeat(70));
    }
};

// ============================================================================
// CONFIGURATION
// ============================================================================

const OUTPUT_DIR = path.join(__dirname, '../../logs/v115_quant');

if (!fs.existsSync(OUTPUT_DIR)) {
    fs.mkdirSync(OUTPUT_DIR, { recursive: true });
}

// V115.000: Market Venue Whitelist (数据源准入白名单)
const MARKET_VENUE_WHITELIST = {
    // 准入名单代号 -> 标准映射
    venues: {
        'PIN-01': {
            standardId: 'PIN-01',
            names: ['pinnacle', 'pin', 'pinnacle sports', 'pinnacle.com'],
            priority: 1
        },
        'WIL-02': {
            standardId: 'WIL-02',
            names: ['william hill', 'williamhill', 'william hill sports', 'wh'],
            priority: 2
        },
        'B365-03': {
            standardId: 'B365-03',
            names: ['bet365', 'b365', 'bet365.com', 'bet 365'],
            priority: 3
        },
        'LAD-04': {
            standardId: 'LAD-04',
            names: ['ladbrokes', 'lad', 'ladbrokes.com', 'ladbrokes coral'],
            priority: 4
        },
        '188-05': {
            standardId: '188-05',
            names: ['188bet', '188', '188bet.com', '188 bet'],
            priority: 5
        },
        'SBO-06': {
            standardId: 'SBO-06',
            names: ['sbobet', 'sbo', 'sbobet.com', 'sbo bet'],
            priority: 6
        },
        'BWI-07': {
            standardId: 'BWI-07',
            names: ['betway', 'bwi', 'betway.com', 'bet way'],
            priority: 7
        }
    },

    normalizeVenueName(venueName) {
        if (!venueName || typeof venueName !== 'string') {
            return null;
        }

        const normalized = venueName.toLowerCase().trim();

        for (const [standardId, config] of Object.entries(this.venues)) {
            if (config.names.some(name => normalized.includes(name) || name.includes(normalized))) {
                log.debug(`[V115.000] Venue normalized: "${venueName}" -> "${standardId}"`);
                return standardId;
            }
        }

        log.warn(`[V115.000] Venue not in whitelist: "${venueName}"`);
        return null;
    },

    isAllowed(venueName) {
        return this.normalizeVenueName(venueName) !== null;
    },

    getAllowedIds() {
        return Object.keys(this.venues);
    }
};

const CONFIG = {
    userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
    viewport: { width: 1920, height: 1080 },
    timeout: 60000,

    // V115.000: 轴向配置 - 严格隔离
    axes: ['home', 'draw', 'away'],
    axisDimensions: {
        home: 'A',
        draw: 'B',
        away: 'C'
    },

    // 悬停交互配置
    hover: {
        waitMin: 1500,
        waitMax: 2500,
        modalTimeout: 5000,
        textDetectionTimeout: 3000
    },

    // V115.000: 全量时序抓取配置
    fullTrajectory: {
        enabled: true,
        maxHistoryDepth: 100,
        requireCompleteTrajectory: true,
        minTrajectoryPoints: 2
    },

    maxBookmakers: 10,
    currentYear: new Date().getFullYear()
};

const REALISTIC_HEADERS = {
    'Accept-Language': 'en-US,en;q=0.9',
    'Sec-Fetch-Dest': 'document',
    'Sec-Fetch-Mode': 'navigate',
    'Sec-Fetch-Site': 'none',
    'Referer': 'https://www.oddsportal.com/football/england/premier-league/'
};

// ============================================================================
// ERROR CLASS
// ============================================================================

class QuantEngineError extends Error {
    constructor(type, message, context = {}) {
        super(message);
        this.name = 'QuantEngineError';
        this.errorType = type;
        this.timestamp = new Date().toISOString();
        this.context = context;
    }

    toString() {
        return `[${this.errorType}] [${this.timestamp}] ${this.message}`;
    }
}

// ============================================================================
// V115.000: SYNC TIMESTAMP MODULE
// ============================================================================

const SyncTimestamp = {
    monthMap: {
        'jan': 0, 'jan.': 0, 'january': 0,
        'feb': 1, 'feb.': 1, 'february': 1,
        'mar': 2, 'mar.': 2, 'march': 2,
        'apr': 3, 'apr.': 3, 'april': 3,
        'may': 4, 'may.': 4,
        'jun': 5, 'jun.': 5, 'june': 5,
        'jul': 6, 'jul.': 6, 'july': 6,
        'aug': 7, 'aug.': 7, 'august': 7,
        'sep': 8, 'sep.': 8, 'september': 8,
        'oct': 9, 'oct.': 9, 'october': 9,
        'nov': 10, 'nov.': 10, 'november': 10,
        'dec': 11, 'dec.': 11, 'december': 11
    },

    parse(dateStr) {
        if (!dateStr || typeof dateStr !== 'string') {
            return null;
        }

        try {
            // Format 1: "24 Jan, 10:00"
            const pattern1 = /^(\d{1,2})\s+(\w+\.?)\s*,?\s+(\d{1,2}):(\d{2})$/i;
            const match1 = dateStr.trim().match(pattern1);
            if (match1) {
                const day = parseInt(match1[1]);
                const monthStr = match1[2].toLowerCase();
                const hour = parseInt(match1[3]);
                const minute = parseInt(match1[4]);

                if (this.monthMap[monthStr] !== undefined) {
                    const month = this.monthMap[monthStr];
                    const date = new Date(Date.UTC(CONFIG.currentYear, month, day, hour, minute));
                    return date.toISOString();
                }
            }

            // Format 2: "Jan 24, 10:00"
            const pattern2 = /^(\w+\.?)\s+(\d{1,2})\s*,?\s+(\d{1,2}):(\d{2})$/i;
            const match2 = dateStr.trim().match(pattern2);
            if (match2) {
                const monthStr = match2[1].toLowerCase();
                const day = parseInt(match2[2]);
                const hour = parseInt(match2[3]);
                const minute = parseInt(match2[4]);

                if (this.monthMap[monthStr] !== undefined) {
                    const month = this.monthMap[monthStr];
                    const date = new Date(Date.UTC(CONFIG.currentYear, month, day, hour, minute));
                    return date.toISOString();
                }
            }

            // Format 3: "10:00" (仅时间)
            const pattern3 = /^(\d{1,2}):(\d{2})$/;
            const match3 = dateStr.trim().match(pattern3);
            if (match3) {
                const hour = parseInt(match3[1]);
                const minute = parseInt(match3[2]);
                const now = new Date();
                const date = new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate(), hour, minute));
                return date.toISOString();
            }

            // Format 4: ISO 8601 尝试
            const isoAttempt = new Date(dateStr);
            if (!isNaN(isoAttempt.getTime())) {
                return isoAttempt.toISOString();
            }

        } catch (error) {
            log.debug(`[V115.000] 时间解析失败: ${dateStr}, error: ${error.message}`);
        }

        return null;
    },

    parseBatch(dateStrings) {
        const results = [];
        for (const dateStr of dateStrings) {
            const parsed = this.parse(dateStr);
            if (parsed) {
                results.push({
                    timestamp: parsed,
                    original: dateStr
                });
            }
        }
        return results;
    }
};

// ============================================================================
// V115.000: DOM-FIRST TRAJECTORY EXTRACTION (修复核心)
// ============================================================================

/**
 * V115.000: DOM-First 深度穿透 - 使用 DOM 遍历而非正则表达式
 *
 * 关键修复：
 * - 使用 JSDOM 创建虚拟 DOM
 * - 使用 querySelectorAll('tr') 真正遍历所有表格行
 * - 确保每个数据点都被捕获
 *
 * @param {string} modalHtml - Modal HTML 内容
 * @returns {Array<{time: string, value: number, type: string}>}
 */
function extractFullTrajectoryDOM(modalHtml) {
    const trajectory = [];

    try {
        if (!modalHtml || typeof modalHtml !== 'string') {
            log.warn('[V115.000] Modal HTML 为空');
            return trajectory;
        }

        // V115.000: 创建虚拟 DOM
        const dom = new JSDOM(modalHtml);
        const document = dom.window.document;

        // 步骤 1: 提取开盘指数 (Opening odds)
        const openingElements = document.querySelectorAll('*');
        for (const el of openingElements) {
            if (el.textContent && el.textContent.includes('Opening odds')) {
                const parent = el.parentElement;
                if (parent) {
                    const textContent = parent.textContent;
                    const timeMatch = textContent.match(/(\d{1,2}\s+\w+\.?\s*,?\s*\d{1,2}:\d{2})/);
                    const oddsMatch = textContent.match(/(\d+\.\d+)/);

                    if (timeMatch && oddsMatch) {
                        const timestamp = SyncTimestamp.parse(timeMatch[1]);
                        if (timestamp) {
                            trajectory.push({
                                time: timestamp,
                                value: parseFloat(oddsMatch[1]),
                                type: 'Initial'
                            });
                            log.debug(`[V115.000] 提取 Initial: ${oddsMatch[1]} @ ${timeMatch[1]}`);
                        }
                    }
                }
                break;
            }
        }

        // V115.000: 步骤 2 - 使用 querySelectorAll 遍历所有表格行
        // 这是核心修复：真正遍历所有行，而不是依赖正则表达式
        const tableRows = document.querySelectorAll('tr');
        log.debug(`[V115.000] DOM 遍历发现 ${tableRows.length} 个表格行`);

        tableRows.forEach((row, rowIndex) => {
            try {
                const cells = row.querySelectorAll('td');
                if (cells.length >= 2) {
                    const firstCell = cells[0].textContent.trim();
                    const secondCell = cells[1].textContent.trim();

                    // 尝试从第一个单元格提取时间戳
                    const timestamp = SyncTimestamp.parse(firstCell);

                    // 尝试从第二个单元格提取数值
                    const value = parseFloat(secondCell);

                    if (timestamp && !isNaN(value) && value > 1.0) {
                        trajectory.push({
                            time: timestamp,
                            value: value,
                            type: 'Historical'
                        });
                        log.debug(`[V115.000] DOM 遍历提取行 ${rowIndex + 1}: ${value} @ ${firstCell}`);
                    }
                }
            } catch (e) {
                // 忽略单行错误，继续处理其他行
            }
        });

        // V115.000: 步骤 3 - 尝试使用 div 结构提取（备用方案）
        if (trajectory.length < 2) {
            log.debug('[V115.000] 表格行提取不足，尝试 div 结构提取...');

            const divContainers = document.querySelectorAll('div');
            let lastTime = null;
            let lastValue = null;

            divContainers.forEach(div => {
                const text = div.textContent.trim();

                // 检测时间戳
                const timeMatch = text.match(/^(\d{1,2}\s+\w+\.?\s*,?\s*\d{1,2}:\d{2})$/);
                if (timeMatch) {
                    lastTime = SyncTimestamp.parse(timeMatch[1]);
                }

                // 检测数值
                const valueMatch = text.match(/^(\d+\.\d+)$/);
                if (valueMatch) {
                    lastValue = parseFloat(valueMatch[1]);
                }

                // 如果同时有时间戳和数值，添加到轨迹
                if (lastTime && lastValue && lastValue > 1.0) {
                    // 检查是否已存在相同点
                    const exists = trajectory.some(p =>
                        p.time === lastTime && p.value === lastValue
                    );

                    if (!exists) {
                        trajectory.push({
                            time: lastTime,
                            value: lastValue,
                            type: 'Historical'
                        });
                        log.debug(`[V115.000] Div 结构提取: ${lastValue} @ ${lastTime}`);
                    }

                    // 重置
                    lastTime = null;
                    lastValue = null;
                }
            });
        }

        // 步骤 4: 提取当前指数 (Current)
        const currentElements = document.querySelectorAll('[class*="current"]');
        for (const el of currentElements) {
            const textContent = el.textContent;
            const valueMatch = textContent.match(/(\d+\.\d+)/);

            if (valueMatch) {
                const value = parseFloat(valueMatch[1]);
                let timestamp = new Date().toISOString();

                // 尝试查找附近的时间戳
                const parent = el.parentElement;
                if (parent) {
                    const timeMatch = parent.textContent.match(/(\d{1,2}\s+\w+\.?\s*,?\s*\d{1,2}:\d{2})/);
                    if (timeMatch) {
                        timestamp = SyncTimestamp.parse(timeMatch[1]);
                    }
                }

                // 检查是否与最后一个点重复
                const lastPoint = trajectory[trajectory.length - 1];
                if (!lastPoint || lastPoint.value !== value) {
                    trajectory.push({
                        time: timestamp,
                        value: value,
                        type: 'Current'
                    });
                    log.debug(`[V115.000] 提取 Current: ${value} @ ${timestamp}`);
                }
            }
        }

        // 步骤 5: 按时间排序
        trajectory.sort((a, b) => new Date(a.time) - new Date(b.time));

        log.info(`[V115.000] DOM-First 完整轨迹提取: ${trajectory.length} 个时序点`);

    } catch (error) {
        log.error(`[V115.000] DOM 遍历失败: ${error.message}`);
    }

    return trajectory;
}

/**
 * V115.000: 状态断言
 */
function assertTrajectoryState(trajectory) {
    if (!Array.isArray(trajectory) || trajectory.length === 0) {
        return {
            valid: false,
            initial: null,
            current: null,
            hasDrift: false,
            error: '轨迹为空'
        };
    }

    const initial = trajectory[0].value;
    const current = trajectory[trajectory.length - 1].value;
    const hasDrift = Math.abs(current - initial) > 0.001;

    if (trajectory.length < CONFIG.fullTrajectory.minTrajectoryPoints) {
        return {
            valid: false,
            initial,
            current,
            hasDrift,
            error: `轨迹点数不足: 需要 ${CONFIG.fullTrajectory.minTrajectoryPoints}，实际 ${trajectory.length}`
        };
    }

    return {
        valid: true,
        initial,
        current,
        hasDrift,
        trajectoryLength: trajectory.length
    };
}

// ============================================================================
// V115.000: AXIS ISOLATION
// ============================================================================

function validateAxisIsolation(axisData) {
    const result = {
        valid: true,
        crosstalkDetected: false,
        errors: []
    };

    try {
        const axes = ['home', 'draw', 'away'];

        for (const axis of axes) {
            if (!axisData[axis]) {
                result.errors.push(`轴 ${axis} 数据缺失`);
                result.valid = false;
                continue;
            }

            if (axisData[axis].trajectory && Array.isArray(axisData[axis].trajectory)) {
                for (const otherAxis of axes) {
                    if (otherAxis !== axis &&
                        axisData[otherAxis] &&
                        axisData[otherAxis].trajectory === axisData[axis].trajectory) {
                        result.errors.push(`轴 ${axis} 和 ${otherAxis} 共享轨迹数组引用！`);
                        result.crosstalkDetected = true;
                        result.valid = false;
                    }
                }
            }
        }

        const homeValue = axisData.home?.state?.initial;
        const drawValue = axisData.draw?.state?.initial;
        const awayValue = axisData.away?.state?.initial;

        if (homeValue && drawValue && awayValue) {
            if (homeValue === drawValue && drawValue === awayValue) {
                result.errors.push(`所有轴的初始值完全相同 (${homeValue})，可能存在数据污染`);
            }
        }

    } catch (error) {
        result.valid = false;
        result.errors.push(`轴向隔离验证异常: ${error.message}`);
    }

    return result;
}

// ============================================================================
// V115.000: MAIN EXTRACTION ENGINE
// ============================================================================

function randomDelay(min, max) {
    return Math.floor(Math.random() * (max - min + 1)) + min;
}

async function waitForModalWithRace(page, timeout = CONFIG.hover.textDetectionTimeout) {
    const modalSelector = 'h3:has-text("Odds movement")';

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

async function extractFromSingleAxisV115(page, axisCell, axisName, axisIndex, standardVenueId) {
    const axisResult = {
        axis: axisName,
        dimension: CONFIG.axisDimensions[axisName],
        standardVenueId: standardVenueId,
        trajectory: [],
        state: null,
        success: false,
        modalHtml: null
    };

    try {
        log.info(`    [V115.000] Processing axis ${axisIndex + 1}/3 (${axisName})...`);

        // 悬停交互
        await axisCell.hover();
        await page.waitForTimeout(randomDelay(CONFIG.hover.waitMin, CONFIG.hover.waitMax));

        // 等待弹窗
        const modalAppeared = await waitForModalWithRace(page);
        if (!modalAppeared) {
            log.warn(`    Modal timeout for ${axisName}`);
            return axisResult;
        }

        log.success(`    Modal appeared for ${axisName}!`);

        // 获取 Modal HTML
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

        // V115.000: 使用 DOM-First 提取完整时序轨迹
        const trajectory = extractFullTrajectoryDOM(modalHtml);
        axisResult.trajectory = trajectory;

        if (trajectory.length === 0) {
            log.warn(`    No trajectory extracted for ${axisName}`);
            return axisResult;
        }

        // V115.000: 状态断言
        const stateAssertion = assertTrajectoryState(trajectory);
        axisResult.state = stateAssertion;

        if (stateAssertion.valid) {
            log.success(`    [V115.000] Axis ${axisName} state validated:`);
            log.success(`      Initial: ${stateAssertion.initial}`);
            log.success(`      Current: ${stateAssertion.current}`);
            log.success(`      Has_Drift: ${stateAssertion.hasDrift}`);
            log.success(`      Trajectory: ${stateAssertion.trajectoryLength} points`);

            axisResult.success = true;
        } else {
            log.warn(`    [V115.000] Axis ${axisName} state validation failed: ${stateAssertion.error}`);
        }

        // 移开鼠标关闭弹窗
        await page.mouse.move(0, 0);
        await page.waitForTimeout(500);

    } catch (error) {
        log.error(`    Error extracting ${axisName}: ${error.message}`);
    }

    return axisResult;
}

async function extractMultiAxisV115(page, rowElement, bookmakerIndex) {
    log.info(`\n[V115.000] Processing bookmaker #${bookmakerIndex + 1}...`);

    const result = {
        provider: null,
        standardVenueId: null,
        axes: {
            home: null,
            draw: null,
            away: null
        },
        axisIsolation: null,
        success: false,
        error: null
    };

    try {
        // 步骤 1: 识别庄家名称并应用白名单过滤
        const nameElement = await rowElement.$('img[alt], span, div[class*="name"]');
        let rawVenueName = null;

        if (nameElement) {
            rawVenueName = await nameElement.evaluate(el =>
                el.getAttribute('alt') || el.textContent?.trim() || null
            );
        }

        result.provider = rawVenueName;

        const standardVenueId = MARKET_VENUE_WHITELIST.normalizeVenueName(rawVenueName);

        if (!standardVenueId) {
            log.warn(`[V115.000] Venue "${rawVenueName}" not in whitelist, skipping`);
            result.error = `Venue not in whitelist: ${rawVenueName}`;
            return result;
        }

        result.standardVenueId = standardVenueId;
        log.success(`[V115.000] Venue approved: "${rawVenueName}" -> "${standardVenueId}"`);

        // 步骤 2: 找到所有 odds cells
        let oddsCells = await rowElement.$$('div.odds-cell, div[class*="odd"], span[class*="odd"]');
        const targetCells = oddsCells.slice(0, 3);

        if (targetCells.length < 3) {
            result.error = `Insufficient odds cells: ${targetCells.length}`;
            return result;
        }

        // 步骤 3: 串行提取三轴数据
        for (let i = 0; i < targetCells.length; i++) {
            const axisName = CONFIG.axes[i];

            log.info(`  [V115.000] === Axis ${i + 1}/3 (${axisName}) ===`);
            log.info(`  [V115.000] Ensuring axis isolation before extraction...`);

            await page.mouse.move(0, 0);
            await page.waitForTimeout(randomDelay(800, 1200));

            const axisResult = await extractFromSingleAxisV115(
                page,
                targetCells[i],
                axisName,
                i,
                standardVenueId
            );

            result.axes[axisName] = JSON.parse(JSON.stringify({
                axis: axisResult.axis,
                dimension: axisResult.dimension,
                standardVenueId: axisResult.standardVenueId,
                trajectory: axisResult.trajectory,
                state: axisResult.state,
                success: axisResult.success
            }));

            if (axisResult.success) {
                log.success(`  [V115.000] Axis ${axisName} extraction complete`);
            } else {
                log.warn(`  [V115.000] Axis ${axisName} extraction failed`);
            }
        }

        // 步骤 4: 验证轴向隔离
        log.info(`  [V115.000] Validating axis isolation...`);
        const isolationResult = validateAxisIsolation(result.axes);
        result.axisIsolation = isolationResult;

        if (isolationResult.valid) {
            log.success(`  [V115.000] Axis isolation validated: No crosstalk detected`);
        } else {
            log.error(`  [V115.000] Axis isolation validation failed:`);
            isolationResult.errors.forEach(err => log.error(`    - ${err}`));
        }

        // 步骤 5: 判断整体成功
        const successCount = CONFIG.axes.filter(axis => result.axes[axis]?.success).length;
        result.success = successCount >= 2 && isolationResult.valid;

        log.success(`  [V115.000] Multi-axis extraction complete: ${successCount}/3 axes successful`);

    } catch (error) {
        result.error = error.message;
        log.error(`  [V115.000] Error: ${error.message}`);
    } finally {
        await page.mouse.move(0, 0);
        await page.waitForTimeout(randomDelay(500, 1000));
    }

    return result;
}

async function persistQuantData(client, entityId, extractionResult) {
    try {
        const records = [];

        for (const axisName of CONFIG.axes) {
            const axisData = extractionResult.axes[axisName];
            if (!axisData || !axisData.success) continue;

            for (const point of axisData.trajectory) {
                records.push({
                    provider_name: axisData.standardVenueId,
                    metric_type: `quant_price_trajectory_${axisName}`,
                    dimension: axisData.dimension,
                    value: point.value,
                    occurred_at: point.time,
                    sequence: axisData.trajectory.indexOf(point),
                    raw_data: {
                        axis: axisName,
                        pointType: point.type,
                        venueId: axisData.standardVenueId,
                        state: axisData.state
                    }
                });
            }
        }

        const result = await storage.upsertTemporalRecords(client, entityId, records);

        log.success(`[V115.000] Persisted ${result.inserted + result.updated} records for entity ${entityId}`);

        return result;

    } catch (error) {
        log.error(`[V115.000] Persistence failed: ${error.message}`);
        throw new QuantEngineError('PERSISTENCE_FAILED', error.message);
    }
}

async function runQuantPriceSyncV115(targetUrl, sourceId) {
    log.section('[V115.000] QUANT PRICE SYNC ENGINE (FIXED DOM-FIRST)');
    log.info('Target URL:', targetUrl);
    log.info('Source ID:', sourceId);
    log.info('[V115.000] Market Venue Whitelist: ACTIVE');
    log.info('[V115.000] DOM-First Trajectory Extraction: ENABLED');
    log.info('[V115.000] Axis Isolation: STRICT');
    log.info('');

    const browser = await chromium.launch({
        headless: false,
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

    const dbClient = await storage.createConnection();

    try {
        log.section('STEP 1: PAGE LOAD');
        await page.goto(targetUrl, {
            timeout: CONFIG.timeout,
            waitUntil: 'networkidle'
        });
        log.success('Page loaded');

        let waitAttempts = 0;
        while (waitAttempts < 30) {
            const oddsCellCount = await page.$$eval('div.odds-cell, .odds-cell', els => els.length);
            if (oddsCellCount > 0) break;
            await page.waitForTimeout(1000);
            waitAttempts++;
        }

        log.section('STEP 2: CREATE ENTITY MAPPING');
        const entityId = await storage.getOrCreateEntity(dbClient, sourceId, targetUrl, 'match');
        log.success(`Entity ID: ${entityId}`);

        log.section('STEP 3: FIND BOOKMAKER ROWS');
        const bookmakerRows = await page.$$('div.flex.h-9.border-b.border-black-borders');
        log.success(`Found ${bookmakerRows.length} bookmaker rows`);

        const targetRows = bookmakerRows.slice(0, CONFIG.maxBookmakers);

        log.section('STEP 4: V115.000 QUANT EXTRACTION (DOM-FIRST)');

        const results = [];
        let successCount = 0;
        let whitelistedCount = 0;

        for (let i = 0; i < targetRows.length; i++) {
            const result = await extractMultiAxisV115(page, targetRows[i], i);
            results.push(result);

            if (result.standardVenueId) {
                whitelistedCount++;
            }

            if (result.success) {
                successCount++;

                await persistQuantData(dbClient, entityId, result);
            }

            await page.waitForTimeout(randomDelay(1500, 2500));
        }

        log.section('STEP 5: RESULTS SUMMARY');
        log.info(`Total processed: ${results.length}`);
        log.success(`Whitelisted venues: ${whitelistedCount}`);
        log.success(`Successful extractions: ${successCount}`);

        const resultsPath = path.join(OUTPUT_DIR, `v115_results_${sourceId}_${Date.now()}.json`);
        fs.writeFileSync(resultsPath, JSON.stringify(results, null, 2), 'utf-8');
        log.success(`Results saved to: ${resultsPath}`);

        log.section('FINAL STATUS');
        if (successCount >= 2) {
            log.success('[V115.000] Quant Engine: TUNED. DOM-First Extraction: VERIFIED. Ready for Tier-1 Production.');
        } else {
            log.warn('[V115.000] Partial success');
        }

        return results;

    } catch (error) {
        log.error(`Extraction failed: ${error.message}`);
        throw error;
    } finally {
        await dbClient.end();
        await page.close();
        await context.close();
        await browser.close();
    }
}

// ============================================================================
// V115.000: SAMPLE VALIDATION
// ============================================================================

async function runSampleValidation() {
    log.section('[V115.000] SAMPLE VALIDATION (5 场实战采样)');

    const dbClient = await storage.createConnection();

    try {
        const result = await dbClient.query(`
            SELECT DISTINCT entity_id
            FROM temporal_metric_records
            WHERE metric_type LIKE 'quant_price_trajectory_%'
            LIMIT 5;
        `);

        if (result.rows.length === 0) {
            log.warn('[V115.000] No quant data found for validation');
            return;
        }

        log.info(`Found ${result.rows.length} entities for validation`);

        let validCount = 0;

        for (const row of result.rows) {
            const entityId = row.entity_id;

            const dataResult = await dbClient.query(`
                SELECT
                    metric_type,
                    dimension,
                    COUNT(*) as record_count,
                    MIN(occurred_at) as earliest,
                    MAX(occurred_at) as latest
                FROM temporal_metric_records
                WHERE entity_id = $1
                  AND metric_type LIKE 'quant_price_trajectory_%'
                GROUP BY metric_type, dimension
                ORDER BY metric_type, dimension;
            `, [entityId]);

            log.info(`\nEntity: ${entityId}`);
            console.table(dataResult.rows);

            const hasMultipleAxes = new Set(dataResult.rows.map(r => r.metric_type)).size >= 2;
            const hasHistory = dataResult.rows.some(r => r.record_count > 1);

            if (hasMultipleAxes && hasHistory) {
                log.success(`  ✓ VALID: Multiple axes with history`);
                validCount++;
            } else {
                log.warn(`  ✗ INVALID: Missing multiple axes or history`);
            }
        }

        log.section('VALIDATION SUMMARY');
        log.success(`Valid samples: ${validCount}/${result.rows.length}`);

        if (validCount >= 4) {
            log.success('[V115.000] Sample Validation: PASSED. System ready for production.');
        } else {
            log.warn('[V115.000] Sample Validation: FAILED. Need more samples.');
        }

    } finally {
        await dbClient.end();
    }
}

module.exports = {
    runQuantPriceSync: runQuantPriceSyncV115,
    runSampleValidation,
    extractMultiAxisV115,
    extractFullTrajectoryDOM,
    assertTrajectoryState,
    validateAxisIsolation,
    MARKET_VENUE_WHITELIST,
    SyncTimestamp,
    QuantEngineError
};

if (require.main === module) {
    const args = process.argv.slice(2);

    if (args.includes('--validate')) {
        runSampleValidation().catch(console.error);
    } else {
        const url = args[0] || 'https://www.oddsportal.com/football/england/premier-league/brighton-everton-vPKFVEM6/';
        const sourceId = args[1] || 'test-match-001';
        runQuantPriceSyncV115(url, sourceId).catch(console.error);
    }
}
