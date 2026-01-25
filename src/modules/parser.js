/**
 * V66.000 - Data Parser Module
 * =============================
 *
 * Unified parsing logic for HTML tooltips and JSON API responses.
 * Refactored from V49.000 parser with improved error handling.
 *
 * @module modules/parser
 * @author Principal Software Architect
 * @version V66.000
 * @since 2026-01-25
 */

'use strict';

const { generateTraceId } = require('../core/retry');

// ============================================================================
// CONFIGURATION
// ============================================================================

const PARSER_CONFIG = {
    // Validation ranges
    minOddValue: 1.01,
    maxOddValue: 50.0,
    minPayout: 0.85,
    maxPayout: 0.99,

    // Structural requirements
    minRowsExpected: 2,
    maxRowsExpected: 30,
    anchorHeader: "Odds movement",

    // Time settings
    currentYear: new Date().getFullYear()
};

// ============================================================================
// ERROR CLASS
// ============================================================================

class ParserError extends Error {
    constructor(code, message, traceId = null, context = {}) {
        super(message);
        this.name = 'ParserError';
        this.errorCode = code;
        this.traceId = traceId || generateTraceId();
        this.timestamp = new Date().toISOString();
        this.context = context;
    }

    toJSON() {
        return {
            error_code: this.errorCode,
            trace_id: this.traceId,
            timestamp: this.timestamp,
            message: this.message,
            context: this.context
        };
    }
}

// ============================================================================
// TIME CALIBRATION
// ============================================================================>

/**
 * Convert various date formats to ISO 8601 timestamp
 * @param {string} dateStr - Date string
 * @returns {string|null} - ISO 8601 timestamp or null
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

        // Format: "24 Jan, 10:00"
        const pattern1 = /^(\d{1,2})\s+(\w+\.?)\s*,?\s+(\d{1,2}):(\d{2})$/i;
        const match1 = dateStr.trim().match(pattern1);
        if (match1) {
            const day = parseInt(match1[1]);
            const monthStr = match1[2].toLowerCase();
            const hour = parseInt(match1[3]);
            const minute = parseInt(match1[4]);

            if (monthMap[monthStr] !== undefined) {
                const month = monthMap[monthStr];
                const date = new Date(Date.UTC(PARSER_CONFIG.currentYear, month, day, hour, minute));
                return date.toISOString();
            }
        }

        // Format: "Jan 24, 10:00"
        const pattern2 = /^(\w+\.?)\s+(\d{1,2})\s*,?\s+(\d{1,2}):(\d{2})$/i;
        const match2 = dateStr.trim().match(pattern2);
        if (match2) {
            const monthStr = match2[1].toLowerCase();
            const day = parseInt(match2[2]);
            const hour = parseInt(match2[3]);
            const minute = parseInt(match2[4]);

            if (monthMap[monthStr] !== undefined) {
                const month = monthMap[monthStr];
                const date = new Date(Date.UTC(PARSER_CONFIG.currentYear, month, day, hour, minute));
                return date.toISOString();
            }
        }

        // Format: "10:00" (time only)
        const pattern3 = /^(\d{1,2}):(\d{2})$/;
        const match3 = dateStr.trim().match(pattern3);
        if (match3) {
            const hour = parseInt(match3[1]);
            const minute = parseInt(match3[2]);
            const now = new Date();
            const date = new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate(), hour, minute));
            return date.toISOString();
        }

        // ISO 8601 format
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
// PAYOUT CALCULATION
// ============================================================================

/**
 * Calculate payout from 1X2 odds
 * Formula: Payout = 1 / (1/Home + 1/Draw + 1/Away)
 * @param {number} home - Home win odd
 * @param {number} draw - Draw odd
 * @param {number} away - Away win odd
 * @returns {number|null} - Payout (0-1) or null
 */
function calculatePayout(home, draw, away) {
    if (!home || !draw || !away) return null;
    if (home < 1 || draw < 1 || away < 1) return null;

    const sum = (1 / home) + (1 / draw) + (1 / away);
    if (sum === 0) return null;

    const payout = 1 / sum;

    if (payout < PARSER_CONFIG.minPayout || payout > PARSER_CONFIG.maxPayout) {
        return null;
    }

    return Math.round(payout * 10000) / 10000;
}

// ============================================================================
// HTML PARSING
// ============================================================================

/**
 * Extract temporal rows from tooltip HTML
 * @param {string} rawHTML - Raw HTML content
 * @returns {Array<string>} - Array of row HTML strings
 */
function extractTemporalRows(rawHTML) {
    const rows = [];

    try {
        const divPattern = /<div[^>]*>(.*?)<\/div>/gis;
        const divContents = [];
        let match;

        while ((match = divPattern.exec(rawHTML)) !== null) {
            divContents.push(match[1]);
        }

        let currentRow = [];
        let inDataRow = false;

        for (const content of divContents) {
            const hasTime = /\d{1,2}\s+\w+\.?\s*,?\s+\d{1,2}:\d{2}/.test(content);

            if (hasTime) {
                if (currentRow.length > 0) {
                    rows.push(currentRow.join(''));
                }
                currentRow = [`<div>${content}</div>`];
                inDataRow = true;
            } else if (inDataRow) {
                currentRow.push(`<div>${content}</div>`);

                const valueCount = (content.match(/\d+\.\d+/g) || []).length;

                if (valueCount >= 3) {
                    rows.push(currentRow.join(''));
                    currentRow = [];
                    inDataRow = false;
                }
            }

            if (currentRow.length > 10) {
                currentRow = [];
                inDataRow = false;
            }
        }

        if (currentRow.length > 0) {
            rows.push(currentRow.join(''));
        }

    } catch (error) {
        throw new ParserError(
            'ROW_EXTRACTION_FAILED',
            `Failed to extract rows: ${error.message}`
        );
    }

    return rows;
}

/**
 * Parse a single temporal row
 * @param {string} rowHTML - Row HTML
 * @param {string} providerName - Provider identifier
 * @param {number} sequence - Sequence number
 * @returns {Object|null} - Parsed record or null
 */
function parseRow(rowHTML, providerName, sequence) {
    // Extract timestamp
    const timeMatch = rowHTML.match(/(\d{1,2}\s+\w+\.?\s*,?\s+\d{1,2}:\d{2})/);
    if (!timeMatch) return null;

    const timestamp = calibrateTimestamp(timeMatch[1]);
    if (!timestamp) return null;

    // Extract odds values
    const oddPattern = /(\d+\.\d+)/g;
    const oddMatches = [...rowHTML.matchAll(oddPattern)];

    if (oddMatches.length < 3) {
        return null;
    }

    const homeOdd = parseFloat(oddMatches[0][1]);
    const drawOdd = parseFloat(oddMatches[1][1]);
    const awayOdd = parseFloat(oddMatches[2][1]);

    // Validate ranges
    if (homeOdd < PARSER_CONFIG.minOddValue || homeOdd > PARSER_CONFIG.maxOddValue) {
        return null;
    }
    if (drawOdd < PARSER_CONFIG.minOddValue || drawOdd > PARSER_CONFIG.maxOddValue) {
        return null;
    }
    if (awayOdd < PARSER_CONFIG.minOddValue || awayOdd > PARSER_CONFIG.maxOddValue) {
        return null;
    }

    const payout = calculatePayout(homeOdd, drawOdd, awayOdd);

    return {
        provider_name: providerName,
        timestamp,
        home_odd: homeOdd,
        draw_odd: drawOdd,
        away_odd: awayOdd,
        payout,
        sequence,
        metric_type: 'temporal_odds_1x2_full',
        raw_data: {
            source: 'v66.000_parser',
            full_spectrum: true,
            dimensions: ['home', 'draw', 'away']
        }
    };
}

/**
 * Parse full tooltip HTML
 * @param {string} rawHTML - Raw HTML content
 * @param {string} [providerName='unknown'] - Provider identifier
 * @returns {Array} - Array of temporal records
 */
function parseTooltipHTML(rawHTML, providerName = 'unknown') {
    const allRecords = [];
    const traceId = generateTraceId();

    try {
        // Validate input
        if (!rawHTML || typeof rawHTML !== 'string') {
            throw new ParserError(
                'INVALID_INPUT',
                'Raw HTML is empty or invalid',
                traceId
            );
        }

        // Check for anchor
        if (!rawHTML.includes(PARSER_CONFIG.anchorHeader)) {
            throw new ParserError(
                'ANCHOR_NOT_FOUND',
                `Required anchor "${PARSER_CONFIG.anchorHeader}" not found`,
                traceId
            );
        }

        // Extract rows
        const rowHTMLs = extractTemporalRows(rawHTML);

        if (rowHTMLs.length < PARSER_CONFIG.minRowsExpected) {
            // Log warning but continue
            console.warn(JSON.stringify({
                level: 'warn',
                trace_id: traceId,
                module: 'modules/parser',
                message: `Only ${rowHTMLs.length} rows extracted, expected at least ${PARSER_CONFIG.minRowsExpected}`
            }));
        }

        // Parse each row
        let sequence = 0;
        for (const rowHTML of rowHTMLs) {
            try {
                const record = parseRow(rowHTML, providerName, sequence);
                if (record) {
                    allRecords.push(record);
                    sequence++;
                }
            } catch (e) {
                // Skip malformed rows
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

        console.info(JSON.stringify({
            level: 'info',
            trace_id: traceId,
            module: 'modules/parser',
            message: `Parsed ${allRecords.length} temporal records for ${providerName}`
        }));

        return allRecords;

    } catch (error) {
        if (error instanceof ParserError) {
            throw error;
        }
        throw new ParserError(
            'PARSE_FAILURE',
            error.message,
            traceId,
            { originalError: error.message }
        );
    }
}

// ============================================================================
// JSON API PARSING
// ============================================================================

/**
 * Parse JSON API response
 * @param {Object} rawJson - Raw JSON data
 * @param {string} [providerName='unknown'] - Provider identifier
 * @returns {Array} - Array of temporal records
 */
function parseJsonResponse(rawJson, providerName = 'unknown') {
    const allRecords = [];
    const traceId = generateTraceId();

    try {
        // Validate input
        if (!rawJson || typeof rawJson !== 'object') {
            throw new ParserError(
                'INVALID_JSON',
                'Raw JSON must be an object',
                traceId
            );
        }

        // Strategy 1: Handle odds array
        if (rawJson.odds && Array.isArray(rawJson.odds)) {
            for (const oddRecord of rawJson.odds) {
                const record = parseApiRecord(oddRecord, providerName);
                if (record) allRecords.push(record);
            }
        }
        // Strategy 2: Handle results array
        else if (rawJson.results && Array.isArray(rawJson.results)) {
            for (const resultRecord of rawJson.results) {
                const record = parseApiRecord(resultRecord, providerName);
                if (record) allRecords.push(record);
            }
        }
        // Strategy 3: Handle data array
        else if (rawJson.data && Array.isArray(rawJson.data)) {
            for (const dataRecord of rawJson.data) {
                const record = parseApiRecord(dataRecord, providerName);
                if (record) allRecords.push(record);
            }
        }
        // Strategy 4: Handle single record
        else if (rawJson.home || rawJson.draw || rawJson.away) {
            const record = parseApiRecord(rawJson, providerName);
            if (record) allRecords.push(record);
        }
        // Strategy 5: Search nested structures
        else {
            for (const key of Object.keys(rawJson)) {
                const value = rawJson[key];
                if (Array.isArray(value) && value.length > 0) {
                    for (const item of value) {
                        if (typeof item === 'object' && item !== null) {
                            const record = parseApiRecord(item, providerName);
                            if (record) allRecords.push(record);
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

        console.info(JSON.stringify({
            level: 'info',
            trace_id: traceId,
            module: 'modules/parser',
            message: `Parsed ${allRecords.length} records from JSON for ${providerName}`
        }));

        return allRecords;

    } catch (error) {
        if (error instanceof ParserError) {
            throw error;
        }
        throw new ParserError(
            'JSON_PARSE_FAILED',
            error.message,
            traceId,
            { originalError: error.message }
        );
    }
}

/**
 * Parse a single API record
 * @param {Object} record - Single odds record
 * @param {string} providerName - Provider identifier
 * @returns {Object|null} - Parsed record or null
 */
function parseApiRecord(record, providerName) {
    // Extract timestamp
    let timestamp = record.timestamp || record.time || record.date || record.occurred_at;

    if (timestamp) {
        if (typeof timestamp === 'string' && timestamp.includes('T') && timestamp.includes(':')) {
            // Already ISO format
        } else if (typeof timestamp === 'string') {
            timestamp = calibrateTimestamp(timestamp);
        } else if (typeof timestamp === 'number') {
            timestamp = new Date(timestamp * 1000).toISOString();
        }
    } else {
        timestamp = new Date().toISOString();
    }

    // Extract odds
    const homeOdd = parseFloat(record.home || record.home_odd || record.h || record['1']);
    const drawOdd = parseFloat(record.draw || record.draw_odd || record.d || record['X']);
    const awayOdd = parseFloat(record.away || record.away_odd || record.a || record['2']);

    // Validate
    if (isNaN(homeOdd) || isNaN(drawOdd) || isNaN(awayOdd)) {
        return null;
    }

    if (homeOdd < PARSER_CONFIG.minOddValue || homeOdd > PARSER_CONFIG.maxOddValue) {
        return null;
    }
    if (drawOdd < PARSER_CONFIG.minOddValue || drawOdd > PARSER_CONFIG.maxOddValue) {
        return null;
    }
    if (awayOdd < PARSER_CONFIG.minOddValue || awayOdd > PARSER_CONFIG.maxOddValue) {
        return null;
    }

    const payout = calculatePayout(homeOdd, drawOdd, awayOdd);

    return {
        provider_name: providerName,
        timestamp,
        home_odd: homeOdd,
        draw_odd: drawOdd,
        away_odd: awayOdd,
        payout,
        sequence: 0,
        metric_type: 'temporal_odds_1x2_full',
        raw_data: {
            source: 'v66.000_api_parser',
            api_first: true,
            dimensions: ['home', 'draw', 'away']
        }
    };
}

// ============================================================================
// EXPORTS
// ============================================================================

module.exports = {
    // HTML parsing
    parseTooltipHTML,
    extractTemporalRows,
    parseRow,

    // JSON parsing
    parseJsonResponse,
    parseApiRecord,

    // Utilities
    calibrateTimestamp,
    calculatePayout,

    // Error class
    ParserError,

    // Config
    PARSER_CONFIG
};
