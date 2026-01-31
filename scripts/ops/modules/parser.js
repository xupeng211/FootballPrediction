/**
 * V43.200 Parser Module
 * =====================
 *
 * Encapsulates DOM parsing logic with structural anchoring strategy
 *
 * Core Features:
 *   - Structural Anchors: Uses h3:text('Odds movement') as anchor
 *   - Relative Path Navigation: nth-child based positioning
 *   - Decoupled Design: Accepts rawHTML, returns standard JSON
 *   - Defensive Programming: Graceful fallback on parse failures
 *
 * @module parser
 * @author Senior DevOps & Systems Engineer
 * @version V43.200
 * @since 2026-01-24
 */

'use strict';

const fs = require('fs');
const path = require('path');
const logger = require('./logger');
const log = logger.createLogger('parser');

/**
 * @typedef {Object} TemporalRecord
 * @property {string} provider_name - Name of the data provider
 * @property {string} metric_type - Type of metric (e.g., 'temporal_odds_1x2')
 * @property {number} value - Numerical value of the metric
 * @property {string} occurred_at - ISO 8601 timestamp in UTC
 * @property {Object} raw_data - Additional metadata
 */

/**
 * @typedef {Object} ParseResult
 * @property {boolean} success - Whether parsing succeeded
 * @property {string} [filePath] - Path to parsed file (for file parsing)
 * @property {TemporalRecord[]} [records] - Extracted temporal records
 * @property {number} [recordCount] - Number of records extracted
 * @property {string} [timestamp] - Parse timestamp
 * @property {string} [error] - Error message if failed
 */

// ============================================================================
// CONFIGURATION
// ============================================================================

const PARSER_CONFIG = {
    // Structural anchors (stable)
    anchorHeader: "h3:text('Odds movement')",

    // Relative navigation (using nth-child, not Tailwind classes)
    rowContainerPath: './../../..',  // Navigate up from header to tooltip container
    rowSelector: 'div',               // Generic container selector

    // Time calibration
    currentYear: new Date().getFullYear()
};

// ============================================================================
// ERROR CLASS
// ============================================================================

class ParserError extends Error {
    constructor(type, message, context = {}) {
        super(message);
        this.name = 'ParserError';
        this.errorType = type;
        this.timestamp = new Date().toISOString();
        this.context = context;
    }

    toString() {
        return `[${this.errorType}] [${this.timestamp}] ${this.message}`;
    }
}

// ============================================================================
// TIME CALIBRATION (Standalone utility)
// ============================================================================

/**
 * Convert local date format to ISO UTC timestamp
 *
 * @param {string} dateStr - Date string in various formats
 * @returns {string|null} - ISO 8601 timestamp in UTC or null if parse fails
 *
 * @example
 * calibrateTimestamp("24 Jan, 10:00") // Returns: "2026-01-24T10:00:00.000Z"
 * calibrateTimestamp("Jan 24, 10:00") // Returns: "2026-01-24T10:00:00.000Z"
 * calibrateTimestamp("10:00")       // Returns: ISO timestamp for today at 10:00
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
                const date = new Date(Date.UTC(PARSER_CONFIG.currentYear, month, day, hour, minute));
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
                const date = new Date(Date.UTC(PARSER_CONFIG.currentYear, month, day, hour, minute));
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
// STRUCTURAL ANCHOR PARSER (Main Logic)
// ============================================================================

/**
 * Parse tooltip HTML using structural anchor strategy
 *
 * @param {string} rawHTML - Raw HTML content to parse
 * @param {string} [providerName='unknown'] - Provider name for records
 * @returns {TemporalRecord[]} - Array of extracted temporal records
 * @throws {ParserError} When anchor not found or parsing fails
 *
 * @example
 * const html = '<div>...Odds movement...24 Jan, 10:00...1.95...</div>';
 * const records = parseTooltipHTML(html, 'pinnacle');
 * // Returns: [{ provider_name: 'pinnacle', value: 1.95, occurred_at: '2026-01-24T10:00:00.000Z', ... }]
 */
function parseTooltipHTML(rawHTML, providerName = 'unknown') {
    const records = [];

    try {
        // Validate input
        if (!rawHTML || typeof rawHTML !== 'string') {
            throw new ParserError('INVALID_INPUT', 'Raw HTML is empty or invalid');
        }

        // Check for anchor header
        if (!rawHTML.includes('Odds movement')) {
            throw new ParserError('ANCHOR_NOT_FOUND', 'Required anchor "Odds movement" not found in HTML');
        }

        // Parse HTML structure (structural positioning)
        const structureAnalysis = analyzeHTMLStructure(rawHTML);

        // Extract data rows using relative positioning
        const dataRows = extractDataRows(rawHTML, structureAnalysis);

        // Parse each row for time-value pairs
        for (const row of dataRows) {
            try {
                const timeValue = extractTimeFromRow(row);
                const numValue = extractValueFromRow(row);

                if (timeValue && numValue) {
                    const occurredAt = calibrateTimestamp(timeValue);
                    const value = parseFloat(numValue);

                    if (occurredAt && !isNaN(value) && value > 1 && value < 100) {
                        records.push({
                            provider_name: providerName,
                            metric_type: 'temporal_odds_1x2',
                            value: value,
                            occurred_at: occurredAt,
                            raw_data: { source: 'v43.000_parser', structural_anchor: true }
                        });
                    }
                }
            } catch (e) {
                // Skip malformed row
            }
        }

        return records;

    } catch (error) {
        if (error instanceof ParserError) {
            throw error;
        }
        throw new ParserError('PARSE_FAILURE', error.message, { originalError: error.message });
    }
}

/**
 * Analyze HTML structure for structural positioning
 * @param {string} html - Raw HTML
 * @returns {Object} - Structure analysis
 */
function analyzeHTMLStructure(html) {
    return {
        hasAnchor: html.includes('Odds movement'),
        divCount: (html.match(/<div/g) || []).length,
        spanCount: (html.match(/<span/g) || []).length,
        hasFlexLayout: html.includes('flex'),
        hasGapClass: html.includes('gap-')
    };
}

/**
 * Extract data rows from HTML using structural patterns
 * @param {string} html - Raw HTML
 * @param {Object} structure - Structure analysis
 * @returns {Array} - Array of row HTML strings
 */
function extractDataRows(html, structure) {
    const rows = [];

    // Pattern: Look for div containers that contain both time and value patterns
    // Time pattern: XX Jan, XX:XX
    // Value pattern: X.XX

    // Split by div tags and reassemble rows
    const divPattern = /<div[^>]*>(.*?)<\/div>/gis;
    const divMatches = [];
    let match;

    while ((match = divPattern.exec(html)) !== null) {
        divMatches.push(match[1]);
    }

    // Group divs into rows (heuristic: consecutive divs form a row)
    let currentRow = '';
    let rowDepth = 0;

    for (const divContent of divMatches) {
        // Check if this div contains time pattern
        const hasTime = /\d{1,2}\s+\w+\.?\s*,?\s+\d{1,2}:\d{2}/.test(divContent);

        if (hasTime) {
            // Start of new row
            if (currentRow) {
                rows.push(currentRow);
            }
            currentRow = `<div>${divContent}</div>`;
            rowDepth = 1;
        } else if (rowDepth > 0 && rowDepth < 5) {
            // Continue current row
            currentRow += `<div>${divContent}</div>`;
            rowDepth++;

            // Check if row has numeric value
            if (/>\s*\d+\.\d+\s*</.test(divContent)) {
                // Row complete
                rows.push(currentRow);
                currentRow = '';
                rowDepth = 0;
            }
        }
    }

    // Add last row if exists
    if (currentRow) {
        rows.push(currentRow);
    }

    return rows;
}

/**
 * Extract time text from row HTML
 * @param {string} rowHTML - Row HTML
 * @returns {string|null} - Time text or null
 */
function extractTimeFromRow(rowHTML) {
    // Pattern: "24 Jan, 10:00" or "Jan 24, 10:00"
    const timePattern = /(\d{1,2}\s+\w+\.?\s*,?\s+\d{1,2}:\d{2})|(\w+\.?\s+\d{1,2}\s*,?\s+\d{1,2}:\d{2})/i;
    const match = rowHTML.match(timePattern);
    return match ? match[0] : null;
}

/**
 * Extract value text from row HTML
 * @param {string} rowHTML - Row HTML
 * @returns {string|null} - Value text or null
 */
function extractValueFromRow(rowHTML) {
    // Pattern: numeric value X.XX
    const valuePattern = /(\d+\.\d+)/;
    const match = rowHTML.match(valuePattern);
    return match ? match[0] : null;
}

// ============================================================================
// OFFLINE PARSER (for Unit Testing)
// ============================================================================

/**
 * Parse HTML from file (for unit testing)
 * @param {string} filePath - Path to HTML file
 * @param {string} providerName - Provider name
 * @returns {Object} - Parse result with records and metadata
 */
function parseFromFile(filePath, providerName = 'test_provider') {
    try {
        const fullPath = path.resolve(filePath);

        if (!fs.existsSync(fullPath)) {
            throw new ParserError('FILE_NOT_FOUND', `HTML file not found: ${filePath}`);
        }

        const rawHTML = fs.readFileSync(fullPath, 'utf-8');
        const records = parseTooltipHTML(rawHTML, providerName);

        return {
            success: true,
            filePath: fullPath,
            records: records,
            recordCount: records.length,
            timestamp: new Date().toISOString()
        };

    } catch (error) {
        if (error instanceof ParserError) {
            return {
                success: false,
                error: error.toString(),
                filePath: filePath
            };
        }
        return {
            success: false,
            error: `[UNKNOWN_ERROR] ${error.message}`,
            filePath: filePath
        };
    }
}

/**
 * Batch parse multiple HTML files from directory
 * @param {string} directoryPath - Path to directory containing HTML files
 * @param {string} providerName - Provider name
 * @returns {Array} - Array of parse results
 */
function parseBatchFromDirectory(directoryPath, providerName = 'test_provider') {
    const results = [];

    try {
        const fullPath = path.resolve(directoryPath);

        if (!fs.existsSync(fullPath)) {
            throw new ParserError('DIR_NOT_FOUND', `Directory not found: ${directoryPath}`);
        }

        const files = fs.readdirSync(fullPath).filter(f => f.endsWith('.html') || f.endsWith('.htm'));

        for (const file of files) {
            const filePath = path.join(fullPath, file);
            const result = parseFromFile(filePath, providerName);
            results.push(result);
        }

        return {
            success: true,
            directory: fullPath,
            totalFiles: files.length,
            results: results
        };

    } catch (error) {
        if (error instanceof ParserError) {
            return {
                success: false,
                error: error.toString()
            };
        }
        return {
            success: false,
            error: `[UNKNOWN_ERROR] ${error.message}`
        };
    }
}

// ============================================================================
// EXPORTS
// ============================================================================

module.exports = {
    parseTooltipHTML,
    parseFromFile,
    parseBatchFromDirectory,
    calibrateTimestamp,
    ParserError,
    PARSER_CONFIG
};
