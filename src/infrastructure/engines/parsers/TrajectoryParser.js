/**
 * TrajectoryParser Module - V150.002 Opening Odds Priority Fix
 * =============================================================
 *
 * Time alignment and trajectory extraction utilities.
 * Extracted from QuantHarvester.js for modular architecture.
 *
 * @module parsers/TrajectoryParser
 * @version V150.002
 * @since 2026-01-28
 * @author Principal Data Engineer (Data Purity Specialist)
 *
 * V150.002 Features:
 * - Opening odds extraction priority (skip current odds)
 * - Split by "Opening odds:" to avoid false matches
 * - Fixed documentElement handling for JSDOM wrapper
 * - V140.000 Features preserved:
 *   - 强制初盘打标: 排序后最早点自动标记为 Initial
 *   - 时区硬化: 强制 UTC，消除本地时区干扰
 *   - 年份校准: 跨年检测 + 未来日期自动回滚
 *   - "苍蝇腿也是肉"原则: recordCount >= 1 即 SUCCESS
 *   - quality_score 元数据: snapshot/partial/complete
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
        // V151.000: 默认使用 2024 作为基准年份（适配 Golden Zone 数据）
        this.baseYear = parseInt(options.baseYear || env.BASE_YEAR || 2024);
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
     * V151.000: 跨年检测与年份校准
     * 修复逻辑：对于历史数据，优先尝试回滚到正确年份
     * 判定规则：若 parsedDate > (now + 48h)，则执行 year = year - 1
     * 支持 BASE_YEAR 环境变量（默认 2024，适配 Golden Zone 数据）
     * @param {Date} parsedDate - 解析出的日期
     * @returns {Date} 校准后的日期
     */
    _calibrateYear(parsedDate) {
        const now = new Date();
        const futureThreshold = new Date(now.getTime() + this.maxFutureToleranceHours * 60 * 60 * 1000);

        // V151.000: 首先检查是否在有效范围内（无需校准）
        if (parsedDate <= futureThreshold) {
            return parsedDate;
        }

        // V151.000: 日期超出容差，执行年份校准
        // 使用 baseYear 作为参考点（默认 2024，适配 Golden Zone 数据）
        const targetYear = this.baseYear;
        const calibratedDate = new Date(Date.UTC(
            targetYear,
            parsedDate.getUTCMonth(),
            parsedDate.getUTCDate(),
            parsedDate.getUTCHours(),
            parsedDate.getUTCMinutes()
        ));

        // 验证校准后的日期是否合理（不应在未来）
        if (calibratedDate > futureThreshold) {
            // 即使使用 baseYear 仍然在未来，回退到 baseYear - 1
            console.log(`[V151.000 SyncTimestamp] Cross-year detection: ${parsedDate.toISOString()} > threshold, rolling back to ${targetYear - 1}`);
            return new Date(Date.UTC(
                targetYear - 1,
                parsedDate.getUTCMonth(),
                parsedDate.getUTCDate(),
                parsedDate.getUTCHours(),
                parsedDate.getUTCMinutes()
            ));
        }

        console.log(`[V151.000 SyncTimestamp] Year calibrated: ${parsedDate.getUTCFullYear()} -> ${targetYear}`);
        return calibratedDate;
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

                // V160.Repair: [年份锁定] 修复日期解析逻辑
                // 如果解析出的年份小于 2024，必须强制通过 BASE_YEAR=2024 进行偏移校准
                // 禁止出现 2001 年的数据（历史污染）
                const parsedYear = date.getUTCFullYear();
                if (parsedYear < 2024) {
                    console.log(`[V160.Repair SyncTimestamp] 🚨 Detected historical year: ${parsedYear} < 2024, forcing BASE_YEAR=${this.baseYear}`);
                    date = new Date(Date.UTC(this.baseYear, month, day, hour, minute));
                }

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

            // [V164.FullTrajectory] Flexbox Columnar Extraction (OddsPortal 2026)
            // Structure: Container(flex-row) -> [TimeCol(flex-col), OddsCol(flex-col)]
            const historyContainers = document.querySelectorAll('div.flex.flex-row.gap-3');
            
            for (const container of historyContainers) {
                // We expect at least 2 columns: Time and Odds
                // Sometimes there is a 3rd column for Volume/Bookmakers count
                const columns = Array.from(container.children).filter(c => c.tagName === 'DIV');
                
                if (columns.length >= 2) {
                    const timeCol = columns[0];
                    const oddsCol = columns[1];
                    
                    // Get all entries in the columns
                    // Selector: direct children divs or divs with specific text classes
                    const timeEntries = timeCol.querySelectorAll('div.text-\\[10px\\]');
                    const oddsEntries = oddsCol.querySelectorAll('div.text-\\[10px\\]');
                    
                    // Match by index
                    const count = Math.min(timeEntries.length, oddsEntries.length);
                    
                    for (let i = 0; i < count; i++) {
                        const timeText = timeEntries[i].textContent.trim();
                        const oddsText = oddsEntries[i].textContent.trim();
                        
                        if (!timeText || !oddsText) continue;
                        
                        const sync = new SyncTimestamp();
                        const timestamp = sync.parse(timeText);
                        const value = parseFloat(oddsText);
                        
                        if (timestamp && !isNaN(value) && value > 1.0) {
                            // Deduplicate
                            const exists = trajectory.some(p => p.time === timestamp && p.value === value);
                            if (!exists) {
                                trajectory.push({
                                    time: timestamp,
                                    value: value,
                                    type: 'Historical'
                                });
                            }
                        }
                    }
                }
            }

            // [V164.FullTrajectory] Opening Odds Extraction (Separate Section)
            // Structure: div.mt-2.gap-1 -> div.flex.gap-1 -> [Time, Odds]
            const openingSection = document.querySelector('div.mt-2.gap-1, div.gap-1.mt-2');
            if (openingSection && openingSection.textContent.includes('Opening')) {
                const flexRow = openingSection.querySelector('div.flex.gap-1');
                if (flexRow) {
                    const divs = flexRow.querySelectorAll('div');
                    if (divs.length >= 2) {
                        const timeText = divs[0].textContent.trim();
                        const oddsText = divs[1].textContent.trim();
                        
                        const sync = new SyncTimestamp();
                        const timestamp = sync.parse(timeText);
                        const value = parseFloat(oddsText);
                        
                        if (timestamp && !isNaN(value)) {
                            trajectory.push({
                                time: timestamp,
                                value: value,
                                type: 'Initial'
                            });
                        }
                    }
                }
            }

            // [V164.DeepSlam] Fallback: Table Extraction (Legacy)
            if (trajectory.length === 0) {
                const tableRows = document.querySelectorAll('tr');
                tableRows.forEach((row) => {
                    try {
                        const cells = row.querySelectorAll('td');
                        if (cells.length >= 2) {
                            const firstCell = cells[0].textContent.trim();
                            const secondCell = cells[1].textContent.trim();
                            if (!firstCell || !secondCell || isNaN(parseFloat(secondCell))) return;
                            
                            const sync = new SyncTimestamp();
                            const timestamp = sync.parse(firstCell);
                            const value = parseFloat(secondCell);

                            if (timestamp && !isNaN(value) && value > 1.0) {
                                const exists = trajectory.some(p => p.time === timestamp && p.value === value);
                                if (!exists) {
                                    trajectory.push({ time: timestamp, value: value, type: 'Historical' });
                                }
                            }
                        }
                    } catch (e) {}
                });
            }

            // [V164.FullTrajectory] Sequence Generation & Time Alignment
            // Sort by time ascending (Oldest -> Newest)
            trajectory.sort((a, b) => new Date(a.time) - new Date(b.time));

            // Mark the first point (oldest) as Initial/Opening if not already
            if (trajectory.length > 0) {
                // Ensure earliest is Initial
                trajectory[0].type = 'Initial';
                
                // If we have explicit "Opening" data (from separate section), it might be duplicated
                // if the time matches exactly. But Set/Dedupe logic above might not catch it if times strictly differ.
                // Generally, earliest is best.
            }

        } catch (error) {
            // Log error but don't fail
            console.error('[V164.FullTrajectory TrajectoryParser] Extraction error:', error.message);
            return {
                trajectory: [],
                valid: false,
                error: error.message,
                recordCount: 0
            };
        } finally {
            if (dom) {
                try {
                    dom.window.close();
                } catch (e) {
                    // Ignore cleanup errors
                }
            }
        }

        // [V164.TitanSlayer] Skeleton Enforcement
        // "苍蝇腿也是肉" -> "Initial odds are Gold". Accept 1+ points.
        const recordCount = trajectory.length;
        let qualityScore;
        if (recordCount >= 5) {
            qualityScore = 'complete';
        } else if (recordCount >= 3) {
            qualityScore = 'partial';
        } else {
            qualityScore = 'skeleton'; // [V164.TitanSlayer] Mandate: Initial odds secured
        }

        return {
            trajectory,
            valid: recordCount >= 1, 
            recordCount,
            quality: recordCount >= 5 ? 'EXCELLENT' : recordCount >= 3 ? 'GOOD' : 'POOR',
            quality_score: qualityScore
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
