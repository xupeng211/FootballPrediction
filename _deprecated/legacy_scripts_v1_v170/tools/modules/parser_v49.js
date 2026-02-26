/**
 * V49.000 Full-Spectrum Parser Module
 * ===================================
 *
 * 核心升级：从"端点提取"升级为"全量三维时间序列提取"
 *
 * New Features:
 *   - DOM List Mapping Algorithm (废弃正则表达式)
 *   - Full 1X2 Dimension Support (Home/Draw/Away)
 *   - Payout Calculation (返还率计算)
 *   - Temporal Sequence Sorting
 *
 * @module parser_v49
 * @author Senior DevOps & Systems Engineer
 * @version V49.000
 * @since 2026-01-24
 */

'use strict';

const logger = require('./logger');
const log = logger.createLogger('parser_v49');

// ============================================================================
// CONFIGURATION
// ============================================================================

const PARSER_V49_CONFIG = {
    // Structural anchors (stable)
    anchorHeader: "h3:text('Odds movement')",

    // Row extraction patterns
    // V64.100: 阈值放行 - 允许接受仅包含 2 条记录的合法 UI 状态
    minRowsExpected: 2,
    maxRowsExpected: 30,

    // Value validation ranges
    minOddValue: 1.01,
    maxOddValue: 50.0,
    minPayout: 0.85,
    maxPayout: 0.99,

    // Time calibration
    currentYear: new Date().getFullYear()
};

// ============================================================================
// ERROR CLASS
// ============================================================================

class ParserV49Error extends Error {
    constructor(type, message, context = {}) {
        super(message);
        this.name = 'ParserV49Error';
        this.errorType = type;
        this.timestamp = new Date().toISOString();
        this.context = context;
    }

    toString() {
        return `[${this.errorType}] [${this.timestamp}] ${this.message}`;
    }
}

// ============================================================================
// TIME CALIBRATION (Inherited from V43.200)
// ============================================================================

/**
 * Convert local date format to ISO UTC timestamp
 * @param {string} dateStr - Date string in various formats
 * @returns {string|null} - ISO 8601 timestamp in UTC
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
                const date = new Date(Date.UTC(PARSER_V49_CONFIG.currentYear, month, day, hour, minute));
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
                const date = new Date(Date.UTC(PARSER_V49_CONFIG.currentYear, month, day, hour, minute));
                return date.toISOString();
            }
        }

        // Format 3: "10:00" (time only, assume today)
        const pattern3 = /^(\d{1,2}):(\d{2})$/;
        const match3 = dateStr.trim().match(pattern3);
        if (match3) {
            const hour = parseInt(match3[1]);
            const minute = parseInt(match3[2]);
            const now = new Date();
            const date = new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate(), hour, minute));
            return date.toISOString();
        }

        // Format 4: ISO 8601 attempt
        const isoAttempt = new Date(dateStr);
        if (!isNaN(isoAttempt.getTime())) {
            return isoAttempt.toISOString();
        }

    } catch (error) {
        // Parse failed
    }

    return null;
}

// ============================================================================
// PAYOUT CALCULATION (NEW)
// ============================================================================

/**
 * Calculate payout (返还率) from 1X2 odds
 * Formula: Payout = 1 / (1/Home + 1/Draw + 1/Away)
 *
 * @param {number} home - Home win odd
 * @param {number} draw - Draw odd
 * @param {number} away - Away win odd
 * @returns {number} - Payout percentage (0-1)
 *
 * @example
 * calculatePayout(2.50, 3.20, 2.80) // Returns: ~0.94
 */
function calculatePayout(home, draw, away) {
    if (!home || !draw || !away) return null;
    if (home < 1 || draw < 1 || away < 1) return null;

    const sum = (1 / home) + (1 / draw) + (1 / away);

    if (sum === 0) return null;

    const payout = 1 / sum;

    // Validate payout range
    if (payout < PARSER_V49_CONFIG.minPayout || payout > PARSER_V49_CONFIG.maxPayout) {
        return null;
    }

    return Math.round(payout * 10000) / 10000; // 4 decimal places
}

// ============================================================================
// FULL-SPECTRUM EXTRACTION (CORE ALGORITHM)
// ============================================================================

/**
 * V49.000: Extract all temporal rows from tooltip HTML
 *
 * Key Change: Use DOM-based extraction instead of regex
 *
 * @param {string} rawHTML - Raw HTML from tooltip
 * @returns {Array<string>} - Array of row HTML strings
 */
function extractAllTemporalRows(rawHTML) {
    const rows = [];

    try {
        // Strategy: Split by div and reconstruct rows based on time pattern
        // Time pattern is the anchor: XX Jan, XX:XX

        // Split HTML by div tags
        const divPattern = /<div[^>]*>(.*?)<\/div>/gis;
        const divContents = [];
        let match;

        while ((match = divPattern.exec(rawHTML)) !== null) {
            divContents.push(match[1]);
        }

        // Group consecutive divs into rows
        let currentRow = [];
        let inDataRow = false;

        for (const content of divContents) {
            // Check if this div contains time pattern
            const hasTime = /\d{1,2}\s+\w+\.?\s*,?\s+\d{1,2}:\d{2}/.test(content);

            if (hasTime) {
                // Start of new row - save previous row if exists
                if (currentRow.length > 0) {
                    rows.push(currentRow.join(''));
                }
                currentRow = [`<div>${content}</div>`];
                inDataRow = true;
            } else if (inDataRow) {
                // Continue current row
                currentRow.push(`<div>${content}</div>`);

                // Check if row has numeric values (completion signal)
                const valueCount = (content.match(/\d+\.\d+/g) || []).length;

                if (valueCount >= 3) {
                    // Row complete
                    rows.push(currentRow.join(''));
                    currentRow = [];
                    inDataRow = false;
                }
            }

            // Safety: prevent infinite row growth
            if (currentRow.length > 10) {
                currentRow = [];
                inDataRow = false;
            }
        }

        // Add last row if exists
        if (currentRow.length > 0) {
            rows.push(currentRow.join(''));
        }

        log.debug(`Extracted ${rows.length} temporal rows from HTML`);

    } catch (error) {
        throw new ParserV49Error('ROW_EXTRACTION_FAILED', `Failed to extract rows: ${error.message}`);
    }

    return rows;
}

/**
 * V49.000: Parse a single row with full 1X2 dimensions
 *
 * @param {string} rowHTML - Row HTML
 * @param {string} providerName - Provider name
 * @param {number} sequence - Sequence number
 * @returns {Object|null} - Parsed record or null
 */
function parseFullRow(rowHTML, providerName, sequence) {
    // Extract timestamp
    const timeMatch = rowHTML.match(/(\d{1,2}\s+\w+\.?\s*,?\s+\d{1,2}:\d{2})/);
    if (!timeMatch) {
        return null;
    }

    const timestamp = calibrateTimestamp(timeMatch[1]);
    if (!timestamp) {
        return null;
    }

    // Extract all numeric values (potential odds)
    const oddPattern = /(\d+\.\d+)/g;
    const oddMatches = [...rowHTML.matchAll(oddPattern)];

    if (oddMatches.length < 3) {
        log.debug(`Insufficient odds values: found ${oddMatches.length}, expected >= 3`);
        return null;
    }

    // Take first 3 as home/draw/away (this is standard layout)
    const homeOdd = parseFloat(oddMatches[0][1]);
    const drawOdd = parseFloat(oddMatches[1][1]);
    const awayOdd = parseFloat(oddMatches[2][1]);

    // Validate odds ranges
    if (homeOdd < PARSER_V49_CONFIG.minOddValue || homeOdd > PARSER_V49_CONFIG.maxOddValue) {
        return null;
    }
    if (drawOdd < PARSER_V49_CONFIG.minOddValue || drawOdd > PARSER_V49_CONFIG.maxOddValue) {
        return null;
    }
    if (awayOdd < PARSER_V49_CONFIG.minOddValue || awayOdd > PARSER_V49_CONFIG.maxOddValue) {
        return null;
    }

    // Calculate payout
    const payout = calculatePayout(homeOdd, drawOdd, awayOdd);

    return {
        provider_name: providerName,
        timestamp: timestamp,
        home_odd: homeOdd,
        draw_odd: drawOdd,
        away_odd: awayOdd,
        payout: payout,
        sequence: sequence,
        metric_type: 'temporal_odds_1x2_full',
        raw_data: {
            source: 'v49.000_parser',
            full_spectrum: true,
            dimensions: ['home', 'draw', 'away']
        }
    };
}

/**
 * V49.000: Main parsing function - Full spectrum extraction
 *
 * @param {string} rawHTML - Raw HTML from tooltip
 * @param {string} [providerName='unknown'] - Provider name
 * @returns {Array} - Array of full temporal records
 */
function parseFullTooltipHTML(rawHTML, providerName = 'unknown') {
    const allRecords = [];

    try {
        // Validate input
        if (!rawHTML || typeof rawHTML !== 'string') {
            throw new ParserV49Error('INVALID_INPUT', 'Raw HTML is empty or invalid');
        }

        // Check for anchor
        if (!rawHTML.includes('Odds movement')) {
            throw new ParserV49Error('ANCHOR_NOT_FOUND', 'Required anchor "Odds movement" not found');
        }

        // Extract all rows
        const rowHTMLs = extractAllTemporalRows(rawHTML);

        if (rowHTMLs.length < PARSER_V49_CONFIG.minRowsExpected) {
            log.warn(`Only ${rowHTMLs.length} rows extracted, expected at least ${PARSER_V49_CONFIG.minRowsExpected}`);
        }

        // Parse each row
        let sequence = 0;
        for (const rowHTML of rowHTMLs) {
            try {
                const record = parseFullRow(rowHTML, providerName, sequence);
                if (record) {
                    allRecords.push(record);
                    sequence++;
                }
            } catch (e) {
                log.debug(`Skipping malformed row: ${e.message}`);
            }
        }

        // Sort by timestamp to ensure correct ordering
        allRecords.sort((a, b) => {
            return new Date(a.timestamp) - new Date(b.timestamp);
        });

        // Re-assign sequence numbers after sorting
        allRecords.forEach((record, idx) => {
            record.sequence = idx;
        });

        log.info(`Parsed ${allRecords.length} full temporal records for ${providerName}`);

        return allRecords;

    } catch (error) {
        if (error instanceof ParserV49Error) {
            throw error;
        }
        throw new ParserV49Error('PARSE_FAILURE', error.message, { originalError: error.message });
    }
}

// ============================================================================
// V50.200 RAW JSON PARSER (API-First Strategy)
// ============================================================================

/**
 * V50.200: Parse raw JSON response from API interception
 *
 * Converts intercepted API JSON data to temporal record format.
 * Handles various JSON structures from OddsPortal API endpoints.
 *
 * @param {Object} rawJson - Raw JSON data from intercepted API response
 * @param {string} [providerName='unknown'] - Provider name (e.g., Entity_P)
 * @returns {Array} - Array of temporal records
 *
 * @example
 * const rawJson = {
 *     odds: [
 *         { timestamp: '2026-01-24T10:00:00Z', home: 1.5, draw: 4.0, away: 6.0 }
 *     ]
 * };
 * const records = parseRawJsonResponse(rawJson, 'Entity_P');
 */
function parseRawJsonResponse(rawJson, providerName = 'unknown') {
    const allRecords = [];

    try {
        // Validate input
        if (!rawJson || typeof rawJson !== 'object') {
            throw new ParserV49Error('INVALID_JSON', 'Raw JSON must be an object');
        }

        // Strategy 1: Handle odds array format
        if (rawJson.odds && Array.isArray(rawJson.odds)) {
            for (const oddRecord of rawJson.odds) {
                try {
                    const record = parseApiOddsRecord(oddRecord, providerName);
                    if (record) {
                        allRecords.push(record);
                    }
                } catch (e) {
                    log.debug(`Skipping malformed odds record: ${e.message}`);
                }
            }
        }

        // Strategy 2: Handle results array format
        else if (rawJson.results && Array.isArray(rawJson.results)) {
            for (const resultRecord of rawJson.results) {
                try {
                    const record = parseApiOddsRecord(resultRecord, providerName);
                    if (record) {
                        allRecords.push(record);
                    }
                } catch (e) {
                    log.debug(`Skipping malformed result record: ${e.message}`);
                }
            }
        }

        // Strategy 3: Handle data array format
        else if (rawJson.data && Array.isArray(rawJson.data)) {
            for (const dataRecord of rawJson.data) {
                try {
                    const record = parseApiOddsRecord(dataRecord, providerName);
                    if (record) {
                        allRecords.push(record);
                    }
                } catch (e) {
                    log.debug(`Skipping malformed data record: ${e.message}`);
                }
            }
        }

        // Strategy 4: Handle single record format
        else if (rawJson.home || rawJson.draw || rawJson.away) {
            const record = parseApiOddsRecord(rawJson, providerName);
            if (record) {
                allRecords.push(record);
            }
        }

        // Strategy 5: Handle nested structures
        else {
            // Try to find arrays in nested properties
            for (const key of Object.keys(rawJson)) {
                const value = rawJson[key];
                if (Array.isArray(value) && value.length > 0) {
                    for (const item of value) {
                        if (typeof item === 'object' && item !== null) {
                            try {
                                const record = parseApiOddsRecord(item, providerName);
                                if (record) {
                                    allRecords.push(record);
                                }
                            } catch (e) {
                                // Continue
                            }
                        }
                    }
                }
            }
        }

        // Sort by timestamp
        allRecords.sort((a, b) => {
            return new Date(a.timestamp) - new Date(b.timestamp);
        });

        // Re-assign sequence numbers
        allRecords.forEach((record, idx) => {
            record.sequence = idx;
        });

        log.info(`V50.200: Parsed ${allRecords.length} records from raw JSON for ${providerName}`);

        return allRecords;

    } catch (error) {
        if (error instanceof ParserV49Error) {
            throw error;
        }
        throw new ParserV49Error('JSON_PARSE_FAILED', error.message, { originalError: error.message });
    }
}

/**
 * V50.200: Parse a single API odds record
 *
 * @param {Object} record - Single odds record from API
 * @param {string} providerName - Provider name
 * @returns {Object|null} - Parsed temporal record or null
 */
function parseApiOddsRecord(record, providerName) {
    // Extract timestamp
    let timestamp = record.timestamp || record.time || record.date || record.occurred_at;

    // Handle different timestamp formats
    if (timestamp) {
        // If already ISO format, use as-is
        if (typeof timestamp === 'string' && timestamp.includes('T') && timestamp.includes(':')) {
            // Already ISO format
        } else if (typeof timestamp === 'string') {
            // Try to convert
            timestamp = calibrateTimestamp(timestamp);
        } else if (typeof timestamp === 'number') {
            // Unix timestamp
            timestamp = new Date(timestamp * 1000).toISOString();
        }
    } else {
        // No timestamp available, use current time
        timestamp = new Date().toISOString();
    }

    // Extract odds values (try different field names)
    const homeOdd = parseFloat(record.home || record.home_odd || record.h || record['1']);
    const drawOdd = parseFloat(record.draw || record.draw_odd || record.d || record['X']);
    const awayOdd = parseFloat(record.away || record.away_odd || record.a || record['2']);

    // Validate odds
    if (isNaN(homeOdd) || isNaN(drawOdd) || isNaN(awayOdd)) {
        return null;
    }

    if (homeOdd < PARSER_V49_CONFIG.minOddValue || homeOdd > PARSER_V49_CONFIG.maxOddValue) {
        return null;
    }
    if (drawOdd < PARSER_V49_CONFIG.minOddValue || drawOdd > PARSER_V49_CONFIG.maxOddValue) {
        return null;
    }
    if (awayOdd < PARSER_V49_CONFIG.minOddValue || awayOdd > PARSER_V49_CONFIG.maxOddValue) {
        return null;
    }

    // Calculate payout
    const payout = calculatePayout(homeOdd, drawOdd, awayOdd);

    return {
        provider_name: providerName,
        timestamp: timestamp,
        home_odd: homeOdd,
        draw_odd: drawOdd,
        away_odd: awayOdd,
        payout: payout,
        sequence: 0,  // Will be reassigned after sorting
        metric_type: 'temporal_odds_1x2_full',
        raw_data: {
            source: 'v50.200_api_interceptor',
            api_first: true,
            dimensions: ['home', 'draw', 'away']
        }
    };
}

// ============================================================================
// LEGACY COMPATIBILITY (V43.200 API)
// ============================================================================

/**
 * Legacy function for backward compatibility
 * Returns single-dimension records (first odd only)
 */
function parseTooltipHTML(rawHTML, providerName = 'unknown') {
    const fullRecords = parseFullTooltipHTML(rawHTML, providerName);

    // Convert to legacy format (single value)
    return fullRecords.map(record => ({
        provider_name: record.provider_name,
        metric_type: 'temporal_odds_1x2',
        value: record.home_odd, // Use home odd as primary value
        occurred_at: record.timestamp,
        raw_data: record.raw_data
    }));
}

// ============================================================================
// EXPORTS
// ============================================================================

module.exports = {
    // V49.000 New API
    parseFullTooltipHTML,
    extractAllTemporalRows,
    parseFullRow,
    calculatePayout,

    // V50.200 API Interceptor Support
    parseRawJsonResponse,
    parseApiOddsRecord,

    // Legacy API (backward compatible)
    parseTooltipHTML,
    calibrateTimestamp,
    ParserV49Error,
    PARSER_V49_CONFIG
};
