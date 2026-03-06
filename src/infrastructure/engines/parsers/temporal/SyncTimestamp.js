/**
 * SyncTimestamp - V140.000 Data Purity Calibration
 * ================================================
 *
 * [Genesis.Reconstruction] 时间对齐工具 - 独立模块
 *
 * 时间戳解析与对齐功能，支持多时区和年份校准。
 *
 * @module parsers/temporal/SyncTimestamp
 * @version V140.000
 * @since 2026-02-02
 * @author [Genesis.Reconstruction]
 */

'use strict';

/**
 * SyncTimestamp - V140.000 Time alignment utilities with hardened timezone/year
 */
class SyncTimestamp {
    constructor(options = {}) {
        const env = process.env || {};
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
     * V140.000: 校准年份 - 处理跨年情况
     * @param {Date} parsedDate - 解析后的日期
     * @returns {Date} 校准后的日期
     * @private
     */
    _calibrateYear(parsedDate) {
        const now = new Date();
        const futureThreshold = new Date(now.getTime() + this.maxFutureToleranceHours * 60 * 60 * 1000);

        if (parsedDate <= futureThreshold) {
            return parsedDate;
        }

        const targetYear = this.baseYear;
        const calibratedDate = new Date(Date.UTC(
            targetYear,
            parsedDate.getUTCMonth(),
            parsedDate.getUTCDate(),
            parsedDate.getUTCHours(),
            parsedDate.getUTCMinutes()
        ));

        if (calibratedDate > futureThreshold) {
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
     * V140.000: 解析时间戳字符串
     * @param {string} dateStr - 时间戳字符串 (如 "24 Jan, 10:00")
     * @returns {string|null} ISO 格式时间戳，解析失败返回 null
     */
    parse(dateStr) {
        if (!dateStr || typeof dateStr !== 'string') {
            return null;
        }

        try {
            const year = this.baseYear;
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
                let date = new Date(Date.UTC(year, month, day, hour, minute));

                const parsedYear = date.getUTCFullYear();
                if (parsedYear < 2024) {
                    console.log(`[V160.Repair SyncTimestamp] 🚨 Detected historical year: ${parsedYear} < 2024, forcing BASE_YEAR=${this.baseYear}`);
                    date = new Date(Date.UTC(this.baseYear, month, day, hour, minute));
                }

                date = this._calibrateYear(date);
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
 * @param {string} dateStr - 时间戳字符串
 * @returns {string|null} ISO 格式时间戳
 */
function alignTimestamp(dateStr) {
    const sync = new SyncTimestamp();
    return sync.parse(dateStr);
}

module.exports = { SyncTimestamp, alignTimestamp };
