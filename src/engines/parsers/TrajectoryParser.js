/**
 * TrajectoryParser Module - V140.000 Data Purity Calibration
 * ================================================================
 *
 * Time alignment and trajectory extraction utilities.
 * Extracted from QuantHarvester.js for modular architecture.
 *
 * @module parsers/TrajectoryParser
 * @version V140.000
 * @since 2026-01-27
 * @author Principal Data Engineer (Data Purity Specialist)
 *
 * V140.000 Features:
 * - 强制初盘打标: 排序后最早点自动标记为 Initial
 * - 时区硬化: 强制 UTC，消除本地时区干扰
 * - 年份校准: 跨年检测 + 未来日期自动回滚
 * - "苍蝇腿也是肉"原则: recordCount >= 1 即 SUCCESS
 * - quality_score 元数据: snapshot/partial/complete
 * - Flexbox-first extraction with table fallback
 *
 * @example
 * const { TrajectoryParser, SyncTimestamp, alignTimestamp } = require('./parsers/TrajectoryParser');
 */

'use strict';

const { JSDOM } = require('jsdom');

// ============================================================================
// SYNC TIMESTAMP MODULE (V140.000 Data Purity Calibration)
// ============================================================================

/**
 * SyncTimestamp - V140.000 Time alignment utilities with hardened timezone/year
 * Handles parsing of various timestamp formats into ISO 8601 UTC
 *
 * V140.000 Enhancements:
 * - 强制 UTC 输出，消除本地时区干扰
 * - 跨年检测: 解析日期 > (now + 48h) 自动回滚一年
 * - 支持环境配置: ENFORCE_UTC, BASE_YEAR, MAX_FUTURE_TOLERANCE_HOURS
 */
class SyncTimestamp {
    /**
     * @param {Object} options - Configuration options
     * @param {number} options.baseYear - Base year for calibration (default: current year)
     * @param {boolean} options.enforceUTC - Force UTC timezone (default: true)
     * @param {number} options.maxFutureToleranceHours - Max future date tolerance (default: 48)
     */
    constructor(options = {}) {
        // V140.000: 支持环境配置或默认值
        const env = process.env || {};
        this.baseYear = parseInt(options.baseYear || env.BASE_YEAR || new Date().getFullYear());
        this.enforceUTC = options.enforceUTC !== undefined ? options.enforceUTC : (env.ENFORCE_UTC !== 'false');
        this.maxFutureToleranceHours = parseInt(options.maxFutureToleranceHours || env.MAX_FUTURE_TOLERANCE_HOURS || 48);

        this.monthMap = {
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
    }

    /**
     * V140.000: 跨年检测与年份校准
     * 如果解析出的日期 > (当前时间 + 容差)，则判定为跨年错误，回滚一年
     * @param {Date} parsedDate - 解析出的日期
     * @returns {Date} 校准后的日期
     */
    _calibrateYear(parsedDate) {
        const now = new Date();
        const futureThreshold = new Date(now.getTime() + this.maxFutureToleranceHours * 60 * 60 * 1000);

        if (parsedDate > futureThreshold) {
            // 日期太远，可能是跨年解析错误，回滚一年
            console.log(`[V140.000 SyncTimestamp] Cross-year detection: ${parsedDate.toISOString()} > threshold, rolling back 1 year`);
            return new Date(Date.UTC(parsedDate.getUTCFullYear() - 1, parsedDate.getUTCMonth(), parsedDate.getUTCDate(), parsedDate.getUTCHours(), parsedDate.getUTCMinutes()));
        }

        return parsedDate;
    }

    /**
     * Parse date string to ISO 8601 UTC format
     * V140.000: 强制 UTC 输出，支持跨年检测
     * @param {string} dateStr - Date string in various formats
     * @returns {string|null} ISO 8601 UTC timestamp or null
     */
    parse(dateStr) {
        if (!dateStr || typeof dateStr !== 'string') {
            return null;
        }

        try {
            let year = this.baseYear;
            let month = null;
            let day = null;
            let hour = null;
            let minute = null;

            // Format: "24 Jan, 10:00" or "Jan 24, 10:00"
            const pattern1 = /^(\d{1,2})\s+(\w+\.?)\s*,?\s*(\d{1,2}):(\d{2})$/i;
            const match1 = dateStr.trim().match(pattern1);
            if (match1) {
                day = parseInt(match1[1]);
                const monthStr = match1[2].toLowerCase();
                hour = parseInt(match1[3]);
                minute = parseInt(match1[4]);
                month = this.monthMap[monthStr];
            }

            const pattern2 = /^(\w+\.?)\s+(\d{1,2})\s*,?\s*(\d{1,2}):(\d{2})$/i;
            const match2 = dateStr.trim().match(pattern2);
            if (match2) {
                const monthStr = match2[1].toLowerCase();
                day = parseInt(match2[2]);
                hour = parseInt(match2[3]);
                minute = parseInt(match2[4]);
                month = this.monthMap[monthStr];
            }

            if (month !== null && !isNaN(month)) {
                // V140.000: 强制使用 Date.UTC 构造，确保 UTC 时区
                let date = new Date(Date.UTC(year, month, day, hour, minute));

                // V140.000: 跨年检测与年份校准
                date = this._calibrateYear(date);

                // V140.000: 强制返回 UTC ISO-8601 格式
                return date.toISOString();
            }

        } catch (error) {
            console.error(`[V140.000 SyncTimestamp] Parse error for "${dateStr}":`, error.message);
            return null;
        }

        return null;
    }
}

/**
 * Standalone alignTimestamp function for test compatibility
 * @param {string} dateStr - Date string to align
 * @returns {string|null} ISO 8601 timestamp
 */
function alignTimestamp(dateStr) {
    const sync = new SyncTimestamp();
    return sync.parse(dateStr);
}

// ============================================================================
// DOM-FIRST TRAJECTORY PARSER
// ============================================================================

/**
 * TrajectoryParser - DOM-based trajectory extraction
 * V133.000: Enhanced with fuzzy matching and data quality threshold
 * Extracts quantitative data trajectories from modal HTML
 */
class TrajectoryParser {
    /**
     * Extract full trajectory from modal HTML using DOM traversal
     * V122.000: Memory leak fixed with explicit JSDOM cleanup
     * V133.000: Added fuzzy matching selectors and data quality threshold
     *
     * @param {string} modalHtml - Modal HTML content
     * @returns {Object} Result object with trajectory and metadata
     */
    extractFullTrajectoryDOM(modalHtml) {
        const trajectory = [];
        let dom = null;

        try {
            if (!modalHtml || typeof modalHtml !== 'string') {
                return {
                    trajectory: [],
                    valid: false,
                    warning: 'Invalid input: modalHtml is not a string',
                    recordCount: 0
                };
            }

            dom = new JSDOM(modalHtml);
            const document = dom.window.document;

            // V134.000: Try NEW flexbox structure first (OddsPortal 2026 redesign)
            const timeDivs = document.querySelectorAll('div[class*="text-[10px]"], div.text-\\[10px\\]');
            const dataPoints = [];

            // Group consecutive divs that form time-odds-change triplets
            for (let i = 0; i < timeDivs.length; i++) {
                const div = timeDivs[i];
                const text = div.textContent.trim();

                // Check if this looks like a timestamp (e.g., "15 May, 18:52")
                const timeMatch = text.match(/^(\d{1,2}\s+\w+\.?\s*,?\s*\d{1,2}:\d{2})/);
                if (timeMatch) {
                    // Look ahead for odds value in nearby divs
                    const sync = new SyncTimestamp();
                    const timestamp = sync.parse(timeMatch[1]);

                    if (timestamp) {
                        // Search forward for odds value
                        let oddsValue = null;
                        let parent = div.parentElement;
                        let attempts = 0;

                        while (parent && attempts < 5) {
                            const siblings = parent.querySelectorAll('div[class*="text-\\[10px\\]"], div[class*="font-bold"]');
                            for (const sibling of siblings) {
                                const sibText = sibling.textContent.trim();
                                const oddsMatch = sibText.match(/^(\d+\.\d+)$/);
                                if (oddsMatch && !oddsValue) {
                                    oddsValue = parseFloat(oddsMatch[1]);
                                    break;
                                }
                            }
                            if (oddsValue) break;
                            parent = parent.parentElement;
                            attempts++;
                        }

                        if (oddsValue && oddsValue > 1.0) {
                            dataPoints.push({ time: timestamp, value: oddsValue, type: 'Flexbox' });
                        }
                    }
                }
            }

            // Add flexbox-extracted data to trajectory
            if (dataPoints.length > 0) {
                trajectory.push(...dataPoints);
            }

            // V134.000: Fallback to OLD table structure (compatibility)
            if (trajectory.length === 0) {
                // Step 1: Extract Opening odds
                const openingElements = document.querySelectorAll('*');
                for (const el of openingElements) {
                    if (el.textContent && el.textContent.includes('Opening odds')) {
                        const parent = el.parentElement;
                        if (parent) {
                            const textContent = parent.textContent;
                            const timeMatch = textContent.match(/(\d{1,2}\s+\w+\.?\s*,?\s*\d{1,2}:\d{2})/);
                            const oddsMatch = textContent.match(/(\d+\.\d+)/);

                            if (timeMatch && oddsMatch) {
                                const sync = new SyncTimestamp();
                                const timestamp = sync.parse(timeMatch[1]);
                                if (timestamp) {
                                    trajectory.push({
                                        time: timestamp,
                                        value: parseFloat(oddsMatch[1]),
                                        type: 'Initial'
                                    });
                                }
                            }
                        }
                        break;
                    }
                }

                // Step 2: Extract Historical data
                const tableRows = document.querySelectorAll('tr');
                tableRows.forEach((row) => {
                    try {
                        const cells = row.querySelectorAll('td');
                        if (cells.length >= 2) {
                            const firstCell = cells[0].textContent.trim();
                            const secondCell = cells[1].textContent.trim();

                            const sync = new SyncTimestamp();
                            const timestamp = sync.parse(firstCell);
                            const value = parseFloat(secondCell);

                            if (timestamp && !isNaN(value) && value > 1.0) {
                                // Check for duplicates
                                const exists = trajectory.some(p =>
                                    p.time === timestamp && p.value === value
                                );
                                if (!exists) {
                                    trajectory.push({
                                        time: timestamp,
                                        value: value,
                                        type: 'Historical'
                                    });
                                }
                            }
                        }
                    } catch (e) {
                        // Ignore row errors
                    }
                });
            }

            // V140.000: Step 3 - Sort by time and ENFORCE INITIAL LABEL
            trajectory.sort((a, b) => new Date(a.time) - new Date(b.time));

            // V140.000: 强制初盘打标 - 最早的点必须标记为 Initial
            // 这解决了 V139.200 审计发现的 Initial Label Coverage = 0% 问题
            if (trajectory.length > 0) {
                const earliestPoint = trajectory[0];
                if (earliestPoint.type !== 'Initial') {
                    console.log(`[V140.000 TrajectoryParser] ENFORCING INITIAL LABEL on earliest point: ${earliestPoint.time}`);
                    earliestPoint.type = 'Initial';
                }
            }

        } catch (error) {
            // Log error but don't fail
            console.error('[V133.000 TrajectoryParser] Extraction error:', error.message);
            return {
                trajectory: [],
                valid: false,
                error: error.message,
                recordCount: 0
            };
        } finally {
            // V122.000: CRITICAL - Fix memory leak by explicitly closing JSDOM
            if (dom) {
                try {
                    dom.window.close();
                } catch (e) {
                    // Ignore cleanup errors
                }
            }
        }

        // V136.000: "苍蝇腿也是肉"原则 - 只要 recordCount >= 1，即标记为 SUCCESS
        const recordCount = trajectory.length;

        // V136.000: Add quality_score metadata
        // Snapshot: 1-2 points (opening odds only)
        // Partial: 3-4 points (some historical data)
        // Complete: 5+ points (full trajectory)
        let qualityScore;
        if (recordCount >= 5) {
            qualityScore = 'complete';
        } else if (recordCount >= 3) {
            qualityScore = 'partial';
        } else {
            qualityScore = 'snapshot';
        }

        if (recordCount > 0 && recordCount < 3) {
            console.log(`[V136.000 TrajectoryParser] SNAPSHOT DATA: ${recordCount} point(s) - Opening odds captured`);
            return {
                trajectory,
                valid: true,  // V136.000: Accept POOR quality data (1+ points is valuable)
                warning: null,  // V136.000: No warning for valid data
                recordCount,
                quality: 'POOR',
                quality_score: qualityScore  // V136.000: New metadata
            };
        }

        return {
            trajectory,
            valid: recordCount >= 1,  // V136.000: Changed from >= 2 to >= 1
            recordCount,
            quality: recordCount >= 5 ? 'EXCELLENT' : recordCount >= 3 ? 'GOOD' : 'POOR',
            quality_score: qualityScore  // V136.000: New metadata
        };
    }

    /**
     * Validate trajectory state
     * V133.000: Enhanced with quality metrics
     * @param {Array} trajectory - Trajectory array
     * @returns {Object} Validation result
     */
    validateTrajectory(trajectory) {
        // Handle new V133.000 return format
        const trajectoryArray = Array.isArray(trajectory) ? trajectory : trajectory?.trajectory || [];

        if (!Array.isArray(trajectoryArray) || trajectoryArray.length === 0) {
            return {
                valid: false,
                initial: null,
                current: null,
                hasDrift: false,
                error: 'Trajectory is empty'
            };
        }

        if (trajectoryArray.length < 2) {
            return {
                valid: false,
                initial: trajectoryArray[0]?.value || null,
                current: trajectoryArray[trajectoryArray.length - 1]?.value || null,
                hasDrift: false,
                error: `Insufficient points: ${trajectoryArray.length} < 2`
            };
        }

        const initial = trajectoryArray[0].value;
        const current = trajectoryArray[trajectoryArray.length - 1].value;
        const hasDrift = Math.abs(current - initial) > 0.001;

        return {
            valid: true,
            initial,
            current,
            hasDrift,
            trajectoryLength: trajectoryArray.length
        };
    }
}

// ============================================================================
// EXPORTS
// ============================================================================

module.exports = {
    TrajectoryParser,
    SyncTimestamp,
    alignTimestamp
};
