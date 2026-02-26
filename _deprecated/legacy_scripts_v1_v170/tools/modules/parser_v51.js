/**
 * V51.000 Parser Module - Enhanced Stability
 * ============================================
 *
 * 核心攻坚逻辑：
 *   - 动作 B (契约校验): 双点采样 (Initial + Current) 强制执行
 *   - 输出协议: [JSON_RESULT]{...}[JSON_RESULT]
 *   - 回退机制: 采样密度 < 2 时触发 fallback 重新解析
 *
 * @module parser_v51
 * @author Senior Node.js & Playwright Engineer
 * @version V51.000
 * @since 2026-01-25
 */

'use strict';

const logger = require('./logger');
const log = logger.createLogger('parser_v51');

// ============================================================================
// CONFIGURATION
// ============================================================================

const PARSER_V51_CONFIG = {
    // 契约校验配置
    contractValidation: {
        requiredSamples: 2,        // 必须获取 Initial + Current
        minSampleDensity: 2,       // 最小采样密度
        maxFallbackAttempts: 2     // 最大回退重试次数
    },

    // 数值验证范围
    valueValidation: {
        minOddValue: 1.01,
        maxOddValue: 50.0,
        minPayout: 0.85,
        maxPayout: 0.99
    },

    // 时间校准
    currentYear: new Date().getFullYear(),

    // JSON_RESULT 协议配置
    outputProtocol: {
        enabled: true,
        format: 'JSON_RESULT',
        version: 'V51.000'
    }
};

// ============================================================================
// ERROR CLASS
// ============================================================================

class ParserV51Error extends Error {
    constructor(type, message, context = {}) {
        super(message);
        this.name = 'ParserV51Error';
        this.errorType = type;
        this.timestamp = new Date().toISOString();
        this.context = context;
    }

    toString() {
        return `[${this.errorType}] [${this.timestamp}] ${this.message}`;
    }
}

// ============================================================================
// TIME CALIBRATION (继承自 V49.000)
// ============================================================================

/**
 * 将本地日期格式转换为 ISO UTC 时间戳
 * @param {string} dateStr - 日期字符串
 * @returns {string|null} - ISO 8601 时间戳
 */
function calibrateTimestamp(dateStr) {
    if (!dateStr || typeof dateStr !== 'string') {
        return null;
    }

    try {
        const monthMap = {
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
        };

        // Format 1: "24 Jan, 10:00"
        const pattern1 = /^(\d{1,2})\s+(\w+\.?)\s*,?\s+(\d{1,2}):(\d{2})$/i;
        const match1 = dateStr.trim().match(pattern1);
        if (match1) {
            const day = parseInt(match1[1]);
            const monthStr = match1[2].toLowerCase();
            const hour = parseInt(match1[3]);
            const minute = parseInt(match1[4]);

            if (monthMap[monthStr] !== undefined) {
                const month = monthMap[monthStr];
                const date = new Date(Date.UTC(PARSER_V51_CONFIG.currentYear, month, day, hour, minute));
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

            if (monthMap[monthStr] !== undefined) {
                const month = monthMap[monthStr];
                const date = new Date(Date.UTC(PARSER_V51_CONFIG.currentYear, month, day, hour, minute));
                return date.toISOString();
            }
        }

        // Format 3: "10:00" (时间仅)
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
        // 解析失败
    }

    return null;
}

// ============================================================================
// 动作 B: 契约校验 (Dual-Point Sampling)
// ============================================================================

/**
 * V51.000: 契约校验器 - 验证双点采样
 *
 * @param {Array} samples - 采样数组
 * @returns {{valid: boolean, error?: string}}
 */
function validateContract(samples) {
    const config = PARSER_V51_CONFIG.contractValidation;

    if (!Array.isArray(samples)) {
        return { valid: false, error: '采样数据格式无效' };
    }

    // 先检查完整性 (Initial + Current)，再检查密度
    const hasInitial = samples.some(s => s.type === 'Initial');
    const hasCurrent = samples.some(s => s.type === 'Current');

    if (!hasInitial || !hasCurrent) {
        const missing = [];
        if (!hasInitial) missing.push('Initial');
        if (!hasCurrent) missing.push('Current');
        return {
            valid: false,
            error: `双点采样不完整: 缺少 ${missing.join(', ')}`
        };
    }

    if (samples.length < config.minSampleDensity) {
        return {
            valid: false,
            error: `采样密度不足: 需要 ${config.minSampleDensity} 个样本，实际获得 ${samples.length} 个`
        };
    }

    return { valid: true };
}

/**
 * V51.000: 从单行提取双点采样数据
 *
 * @param {string} rowHTML - 行 HTML
 * @returns {{initial: number|null, current: number|null, delta: number|null}}
 */
function extractDualPointFromRow(rowHTML) {
    // 提取所有数值
    const oddPattern = /(\d+\.\d+)/g;
    const matches = [...rowHTML.matchAll(oddPattern)];

    if (matches.length < 1) {
        return { initial: null, current: null, delta: null };
    }

    // 策略 1: 查找 "Opening odds:" 标签
    const openingMatch = rowHTML.match(/Opening odds:\s*(\d+\.\d+)/);
    let initial = null;
    let current = null;
    let delta = null;

    if (openingMatch) {
        initial = parseFloat(openingMatch[1]);
        // 第一个普通赔率值通常是当前值
        if (matches.length > 0) {
            current = parseFloat(matches[0][1]);
        }
        // 查找 delta (通常带 + 号)
        const deltaMatch = rowHTML.match(/\+(\d+\.\d+)/);
        if (deltaMatch) {
            delta = parseFloat(deltaMatch[1]);
        }
    } else {
        // 策略 2: 假设第一个是 Initial，第二个是 Current
        if (matches.length >= 2) {
            initial = parseFloat(matches[0][1]);
            current = parseFloat(matches[1][1]);
            delta = current - initial;
        } else if (matches.length === 1) {
            current = parseFloat(matches[0][1]);
            // 无法获取 initial，返回 null
        }
    }

    return { initial, current, delta };
}

// ============================================================================
// FULL-SPECTRUM EXTRACTION
// ============================================================================

/**
 * V51.000: 从 tooltip HTML 提取所有时序行
 *
 * @param {string} rawHTML - 原始 HTML
 * @returns {Array<string>} - 行 HTML 数组
 */
function extractAllTemporalRows(rawHTML) {
    const rows = [];

    try {
        // 策略：直接在原始 HTML 中查找时间模式，然后提取周围的上下文
        const timePattern = /\d{1,2}\s+\w+\.?\s*,?\s*\d{1,2}:\d{2}/g;
        const timeMatches = [];
        let match;

        while ((match = timePattern.exec(rawHTML)) !== null) {
            timeMatches.push({
                timestamp: match[0],
                index: match.index,
                endIndex: match.index + match[0].length
            });
        }

        // 为每个时间匹配提取上下文
        for (const timeMatch of timeMatches) {
            // 提取时间前后的一段内容（最多 800 字符，确保包含 Opening odds）
            const start = Math.max(0, timeMatch.index - 300);
            const end = Math.min(rawHTML.length, timeMatch.endIndex + 500);
            const context = rawHTML.substring(start, end);

            // 验证上下文包含赔率值
            const oddPattern = /\d+\.\d+/g;
            const oddMatches = context.match(oddPattern);

            if (oddMatches && oddMatches.length >= 1) {
                rows.push(context);
            }
        }

        log.debug(`提取 ${rows.length} 个时序行`);

    } catch (error) {
        throw new ParserV51Error('ROW_EXTRACTION_FAILED', `行提取失败: ${error.message}`);
    }

    return rows;
}

/**
 * V51.000: 解析单行 - 带契约校验
 *
 * @param {string} rowHTML - 行 HTML
 * @param {string} providerName - 提供商名称
 * @param {number} sequence - 序列号
 * @returns {Object|null} - 解析记录或 null
 */
function parseFullRowWithContract(rowHTML, providerName, sequence) {
    // 提取时间戳
    const timeMatch = rowHTML.match(/(\d{1,2}\s+\w+\.?\s*,?\s*\d{1,2}:\d{2})/);
    if (!timeMatch) {
        return null;
    }

    const timestamp = calibrateTimestamp(timeMatch[1]);
    if (!timestamp) {
        return null;
    }

    // 提取双点采样
    const dualPoint = extractDualPointFromRow(rowHTML);

    // 提取所有赔率值
    const oddPattern = /(\d+\.\d+)/g;
    const oddMatches = [...rowHTML.matchAll(oddPattern)];

    if (oddMatches.length < 1) {
        log.debug(`赔率值不足: 找到 ${oddMatches.length} 个`);
        return null;
    }

    // 过滤掉小数值 (delta 值通常很小，如 0.05)
    const validOdds = oddMatches
        .map(m => parseFloat(m[1]))
        .filter(v => v >= PARSER_V51_CONFIG.valueValidation.minOddValue);

    if (validOdds.length < 1) {
        log.debug(`有效赔率值不足: 找到 ${oddMatches.length} 个，过滤后 ${validOdds.length} 个`);
        return null;
    }

    const config = PARSER_V51_CONFIG.valueValidation;

    // 判断是单值还是 1X2 格式 (基于过滤后的有效赔率)
    const isSingleValue = validOdds.length < 3;

    let homeOdd, drawOdd, awayOdd, payout;

    if (isSingleValue) {
        // 单值格式
        homeOdd = parseFloat(oddMatches[0][1]);
        drawOdd = null;
        awayOdd = null;
        payout = null;

        // 验证单值范围
        if (homeOdd < config.minOddValue || homeOdd > config.maxOddValue) return null;
    } else {
        // 1X2 格式
        homeOdd = parseFloat(oddMatches[0][1]);
        drawOdd = parseFloat(oddMatches[1][1]);
        awayOdd = parseFloat(oddMatches[2][1]);

        // 验证赔率范围
        if (homeOdd < config.minOddValue || homeOdd > config.maxOddValue) return null;
        if (drawOdd < config.minOddValue || drawOdd > config.maxOddValue) return null;
        if (awayOdd < config.minOddValue || awayOdd > config.maxOddValue) return null;

        // 计算返还率
        payout = calculatePayout(homeOdd, drawOdd, awayOdd);
    }

    return {
        provider_name: providerName,
        timestamp: timestamp,
        home_odd: homeOdd,
        draw_odd: drawOdd,
        away_odd: awayOdd,
        payout: payout,
        sequence: sequence,
        metric_type: isSingleValue ? 'temporal_odds_single' : 'temporal_odds_1x2_full',

        // V51.000: 双点采样数据
        dual_point_sampling: {
            initial: dualPoint.initial,
            current: dualPoint.current,
            delta: dualPoint.delta,
            valid: dualPoint.initial !== null && dualPoint.current !== null
        },

        raw_data: {
            source: 'v51.000_parser',
            full_spectrum: !isSingleValue,
            dimensions: isSingleValue ? ['single'] : ['home', 'draw', 'away'],
            contract_validated: true
        }
    };
}

/**
 * V51.000: 计算返还率
 */
function calculatePayout(home, draw, away) {
    if (!home || !draw || !away) return null;
    if (home < 1 || draw < 1 || away < 1) return null;

    const sum = (1 / home) + (1 / draw) + (1 / away);
    if (sum === 0) return null;

    const payout = 1 / sum;
    const config = PARSER_V51_CONFIG.valueValidation;

    if (payout < config.minPayout || payout > config.maxPayout) {
        return null;
    }

    return Math.round(payout * 10000) / 10000;
}

/**
 * V51.000: 主解析函数 - 带契约校验和回退机制
 *
 * @param {string} rawHTML - 原始 HTML
 * @param {string} [providerName='unknown'] - 提供商名称
 * @returns {Array} - 时序记录数组
 */
function parseFullTooltipHTMLWithContract(rawHTML, providerName = 'unknown') {
    const allRecords = [];

    try {
        // 验证输入
        if (!rawHTML || typeof rawHTML !== 'string') {
            throw new ParserV51Error('INVALID_INPUT', '原始 HTML 为空或无效');
        }

        // 检查锚点
        if (!rawHTML.includes('Odds movement')) {
            throw new ParserV51Error('ANCHOR_NOT_FOUND', '必需锚点 "Odds movement" 未找到');
        }

        // 提取所有行
        const rowHTMLs = extractAllTemporalRows(rawHTML);

        if (rowHTMLs.length < 1) {
            log.warn(`未提取到任何时序行`);
        } else if (rowHTMLs.length === 1) {
            log.debug(`仅提取 1 行，可能为单点采样数据`);
        }

        // 解析每一行
        let sequence = 0;
        let contractFailures = 0;

        for (const rowHTML of rowHTMLs) {
            try {
                const record = parseFullRowWithContract(rowHTML, providerName, sequence);

                if (record) {
                    // V51.000: 契约校验
                    if (record.dual_point_sampling.valid) {
                        allRecords.push(record);
                        sequence++;
                    } else {
                        contractFailures++;
                        log.debug(`契约校验失败: 序列 ${sequence}，双点采样不完整`);
                    }
                }
            } catch (e) {
                log.debug(`跳过格式错误的行: ${e.message}`);
            }
        }

        // 如果契约失败过多，触发回退机制
        // V51.000: 降低阈值，对于单行或少量行更积极地使用回退
        const fallbackThreshold = Math.max(1, Math.floor(rowHTMLs.length * 0.5));
        if (contractFailures >= fallbackThreshold) {
            log.warn(`契约失败过多 (${contractFailures}/${rowHTMLs.length})，触发回退解析...`);
            const fallbackRecords = parseWithFallback(rawHTML, providerName);
            allRecords.push(...fallbackRecords);
        }

        // 按时间戳排序
        allRecords.sort((a, b) => {
            return new Date(a.timestamp) - new Date(b.timestamp);
        });

        // 重新分配序列号
        allRecords.forEach((record, idx) => {
            record.sequence = idx;
        });

        log.info(`解析 ${allRecords.length} 个完整时序记录 (${providerName})`);

        return allRecords;

    } catch (error) {
        if (error instanceof ParserV51Error) {
            throw error;
        }
        throw new ParserV51Error('PARSE_FAILURE', error.message, { originalError: error.message });
    }
}

/**
 * V51.000: 回退解析 - 放宽契约要求
 *
 * @param {string} rawHTML - 原始 HTML
 * @param {string} providerName - 提供商名称
 * @returns {Array} - 时序记录数组
 */
function parseWithFallback(rawHTML, providerName) {
    log.info('执行回退解析策略...');

    const rowHTMLs = extractAllTemporalRows(rawHTML);
    const records = [];
    let sequence = 0;

    for (const rowHTML of rowHTMLs) {
        try {
            const timeMatch = rowHTML.match(/(\d{1,2}\s+\w+\.?\s*,?\s+\d{1,2}:\d{2})/);
            if (!timeMatch) continue;

            const timestamp = calibrateTimestamp(timeMatch[1]);
            if (!timestamp) continue;

            // 提取所有数值并过滤
            const oddMatches = [...rowHTML.matchAll(/(\d+\.\d+)/g)];
            if (oddMatches.length < 1) continue;

            // 过滤有效赔率值
            const validOdds = oddMatches
                .map(m => parseFloat(m[1]))
                .filter(v => v >= PARSER_V51_CONFIG.valueValidation.minOddValue &&
                            v <= PARSER_V51_CONFIG.valueValidation.maxOddValue);

            if (validOdds.length < 1) continue;

            // 判断是单值还是 1X2 格式
            const isSingleValue = validOdds.length < 3;

            let homeOdd, drawOdd, awayOdd, payout;

            if (isSingleValue) {
                // 单值格式
                homeOdd = validOdds[0];
                drawOdd = null;
                awayOdd = null;
                payout = null;
            } else {
                // 1X2 格式
                homeOdd = validOdds[0];
                drawOdd = validOdds[1];
                awayOdd = validOdds[2];
                payout = calculatePayout(homeOdd, drawOdd, awayOdd);
            }

            records.push({
                provider_name: providerName,
                timestamp: timestamp,
                home_odd: homeOdd,
                draw_odd: drawOdd,
                away_odd: awayOdd,
                payout: payout,
                sequence: sequence,
                metric_type: isSingleValue ? 'temporal_odds_single' : 'temporal_odds_1x2_full',
                dual_point_sampling: {
                    initial: null,
                    current: homeOdd,
                    delta: null,
                    valid: false,
                    fallback: true
                },
                raw_data: {
                    source: 'v51.000_parser_fallback',
                    full_spectrum: !isSingleValue,
                    dimensions: isSingleValue ? ['single'] : ['home', 'draw', 'away'],
                    contract_validated: false
                }
            });

            sequence++;
        } catch (e) {
            // 跳过
        }
    }

    log.info(`回退解析完成: ${records.length} 个记录`);
    return records;
}

// ============================================================================
// [JSON_RESULT] 输出协议
// ============================================================================

/**
 * V51.000: 封装为 JSON_RESULT 协议
 *
 * 输出格式: [JSON_RESULT]{...}[JSON_RESULT]
 *
 * @param {Array} records - 时序记录数组
 * @param {Object} metadata - 元数据
 * @returns {string} - JSON_RESULT 格式字符串
 */
function formatJsonResult(records, metadata = {}) {
    const result = {
        version: PARSER_V51_CONFIG.outputProtocol.version,
        timestamp: new Date().toISOString(),
        metadata: metadata,
        data: records,
        stats: {
            totalRecords: records.length,
            contractValidated: records.filter(r => r.dual_point_sampling.valid).length,
            fallbackUsed: records.filter(r => r.dual_point_sampling.fallback).length
        }
    };

    const jsonStr = JSON.stringify(result, null, 2);
    return `[JSON_RESULT]${jsonStr}[JSON_RESULT]`;
}

/**
 * V51.000: 解析 JSON_RESULT 协议
 *
 * @param {string} jsonResultStr - JSON_RESULT 格式字符串
 * @returns {Object|null} - 解析结果
 */
function parseJsonResult(jsonResultStr) {
    try {
        // 提取 JSON 部分
        const match = jsonResultStr.match(/\[JSON_RESULT\](.*)\[JSON_RESULT\]/s);
        if (!match) {
            throw new Error('无效的 JSON_RESULT 格式');
        }

        const jsonStr = match[1];
        const result = JSON.parse(jsonStr);

        return result;
    } catch (error) {
        log.error(`JSON_RESULT 解析失败: ${error.message}`);
        return null;
    }
}

/**
 * V51.000: 解析 HTML 并直接输出 JSON_RESULT 格式
 *
 * @param {string} rawHTML - 原始 HTML
 * @param {string} [providerName='unknown'] - 提供商名称
 * @returns {string} - JSON_RESULT 格式字符串
 */
function parseAndFormat(rawHTML, providerName = 'unknown') {
    const records = parseFullTooltipHTMLWithContract(rawHTML, providerName);
    return formatJsonResult(records, { provider: providerName });
}

// ============================================================================
// LEGACY COMPATIBILITY
// ============================================================================

/**
 * 向后兼容的解析函数
 */
function parseTooltipHTML(rawHTML, providerName = 'unknown') {
    const fullRecords = parseFullTooltipHTMLWithContract(rawHTML, providerName);

    return fullRecords.map(record => ({
        provider_name: record.provider_name,
        metric_type: 'temporal_odds_1x2',
        value: record.home_odd,
        occurred_at: record.timestamp,
        raw_data: record.raw_data
    }));
}

// ============================================================================
// V85.000: Modal HTML Parser (视觉取证专用)
// ============================================================================

/**
 * V85.000: 解析从视觉取证获取的 Modal HTML 碎片
 *
 * 这个函数专门用于处理通过 captureOddsMovementVisually() 获取的 HTML，
 * 从中提取时间戳和赔率数值，并返回标准化的时序记录数组。
 *
 * @param {string} html - 从视觉取证获取的 Modal HTML
 * @param {string} providerLabel - 提供商标签 (如 'Pinnacle', 'bet365')
 * @returns {Array<Object>} - 时序记录数组
 */
function parseModalHtml(html, providerLabel) {
    // V85.801: 先进行输入验证，防止访问 null.length 导致崩溃
    if (!html || typeof html !== 'string') {
        throw new ParserV51Error('INVALID_HTML_INPUT', 'HTML 参数为空或无效');
    }

    log.info(`[V85.000] 解析 Modal HTML (${html.length} chars) - Provider: ${providerLabel}`);

    const records = [];

    try {
        // 锚点验证：检查必需的关键词
        if (!html.includes('Odds movement') && !html.includes('Opening odds')) {
            log.warn('[V85.000] HTML 缺少关键锚点，可能不是有效的 Odds Movement 弹窗');
        }

        // 提取所有时序行（复用现有逻辑）
        const rowHTMLs = extractAllTemporalRows(html);

        if (rowHTMLs.length === 0) {
            log.warn('[V85.000] 未提取到任何时序行');
            return records;
        }

        log.debug(`[V85.000] 提取到 ${rowHTMLs.length} 个时序行`);

        // 解析每一行
        let sequence = 0;

        for (const rowHTML of rowHTMLs) {
            try {
                const record = parseFullRowWithContract(rowHTML, providerLabel, sequence);

                if (record) {
                    // V51.000: 契约校验（放宽要求，接受单点采样）
                    if (record.dual_point_sampling.valid || record.dual_point_sampling.fallback) {
                        records.push(record);
                        sequence++;
                    } else {
                        log.debug(`[V85.000] 跳过未通过校验的记录: 序列 ${sequence}`);
                    }
                }
            } catch (e) {
                log.debug(`[V85.000] 跳过格式错误的行: ${e.message}`);
            }
        }

        // 按时间戳排序
        records.sort((a, b) => {
            return new Date(a.timestamp) - new Date(b.timestamp);
        });

        // 重新分配序列号
        records.forEach((record, idx) => {
            record.sequence = idx;
        });

        log.info(`[V85.000] 解析完成: ${records.length} 个时序记录`);

        // 统计信息
        const stats = {
            total: records.length,
            withOpeningOdds: records.filter(r => r.dual_point_sampling.initial !== null).length,
            singleValue: records.filter(r => r.metric_type === 'temporal_odds_single').length,
            full1X2: records.filter(r => r.metric_type === 'temporal_odds_1x2_full').length
        };

        log.debug(`[V85.000] 统计: 总计=${stats.total}, 开盘=${stats.withOpeningOdds}, 单值=${stats.singleValue}, 1X2=${stats.full1X2}`);

        return records;

    } catch (error) {
        if (error instanceof ParserV51Error) {
            throw error;
        }
        throw new ParserV51Error('PARSE_MODAL_HTML_FAILED', `Modal HTML 解析失败: ${error.message}`, {
            provider: providerLabel,
            htmlLength: html ? html.length : 0
        });
    }
}

/**
 * V85.000: 快速提取 - 从 Modal HTML 提取关键数据（用于调试）
 *
 * @param {string} html - Modal HTML
 * @param {string} providerLabel - 提供商标签
 * @returns {Object} - 包含原始时间戳、赔率数组等关键信息
 */
function extractQuickDataFromModal(html, providerLabel) {
    const result = {
        provider: providerLabel,
        timestamps: [],
        odds: [],
        openingOdds: null,
        hasMovement: false
    };

    try {
        // 提取时间戳
        const timePattern = /\\d{1,2}\\s+\\w+\\.?\\s*,?\\s*\\d{1,2}:\\d{2}/g;
        const timeMatches = [...html.matchAll(timePattern)];
        result.timestamps = timeMatches.map(m => m[0]);

        // 提取开盘赔率
        const openingMatch = html.match(/Opening odds:\\s*(\\d+\\.\\d+)/);
        if (openingMatch) {
            result.openingOdds = parseFloat(openingMatch[1]);
        }

        // 提取所有赔率值
        const oddMatches = [...html.matchAll(/(\\d+\\.\\d+)/g)];
        result.odds = oddMatches.map(m => parseFloat(m[1]));

        // 判断是否有变动（至少 2 个不同的赔率值）
        const uniqueOdds = new Set(result.odds);
        result.hasMovement = uniqueOdds.size > 1;

    } catch (error) {
        log.debug(`[V85.000] 快速提取失败: ${error.message}`);
    }

    return result;
}

// ============================================================================
// EXPORTS
// ============================================================================

module.exports = {
    // V85.000 新增视觉取证解析 API
    parseModalHtml,
    extractQuickDataFromModal,
    // V51.000 新 API
    parseFullTooltipHTMLWithContract,
    parseAndFormat,
    formatJsonResult,
    parseJsonResult,
    validateContract,
    extractDualPointFromRow,
    extractAllTemporalRows,

    // Legacy API
    parseTooltipHTML,
    calibrateTimestamp,
    calculatePayout,

    // 配置
    PARSER_V51_CONFIG,
    ParserV51Error
};
