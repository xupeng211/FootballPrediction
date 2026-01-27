/**
 * TrajectoryParser Module - V133.000 Ultimate Visual Breakthrough
 * ================================================================
 *
 * Time alignment and trajectory extraction utilities.
 * Extracted from QuantHarvester.js for modular architecture.
 *
 * @module parsers/TrajectoryParser
 * @version V133.000
 * @since 2026-01-27
 * @author Senior Lead Systems Architect
 *
 * @example
 * const { TrajectoryParser, SyncTimestamp, alignTimestamp } = require('./parsers/TrajectoryParser');
 */

'use strict';

const { JSDOM } = require('jsdom');

// ============================================================================
// SYNC TIMESTAMP MODULE (2026 Calibration)
// ============================================================================

/**
 * SyncTimestamp - Time alignment utilities
 * Handles parsing of various timestamp formats into ISO 8601
 */
class SyncTimestamp {
    /**
     * @param {number} currentYear - Current year for timestamp calibration
     */
    constructor(currentYear = new Date().getFullYear()) {
        this.currentYear = currentYear;
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
     * Parse date string to ISO 8601 format
     * @param {string} dateStr - Date string in various formats
     * @returns {string|null} ISO 8601 timestamp or null
     */
    parse(dateStr) {
        if (!dateStr || typeof dateStr !== 'string') {
            return null;
        }

        try {
            // Format: "24 Jan, 10:00" or "Jan 24, 10:00"
            const pattern1 = /^(\d{1,2})\s+(\w+\.?)\s*,?\s*(\d{1,2}):(\d{2})$/i;
            const match1 = dateStr.trim().match(pattern1);
            if (match1) {
                const day = parseInt(match1[1]);
                const monthStr = match1[2].toLowerCase();
                const hour = parseInt(match1[3]);
                const minute = parseInt(match1[4]);

                if (this.monthMap[monthStr] !== undefined) {
                    const date = new Date(Date.UTC(this.currentYear, this.monthMap[monthStr], day, hour, minute));
                    return date.toISOString();
                }
            }

            const pattern2 = /^(\w+\.?)\s+(\d{1,2})\s*,?\s*(\d{1,2}):(\d{2})$/i;
            const match2 = dateStr.trim().match(pattern2);
            if (match2) {
                const monthStr = match2[1].toLowerCase();
                const day = parseInt(match2[2]);
                const hour = parseInt(match2[3]);
                const minute = parseInt(match2[4]);

                if (this.monthMap[monthStr] !== undefined) {
                    const date = new Date(Date.UTC(this.currentYear, this.monthMap[monthStr], day, hour, minute));
                    return date.toISOString();
                }
            }

        } catch (error) {
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

            // Step 3: Sort by time
            trajectory.sort((a, b) => new Date(a.time) - new Date(b.time));

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

        // V133.000: Data quality threshold check
        const recordCount = trajectory.length;
        if (recordCount > 0 && recordCount < 3) {
            console.warn(`[V133.000 TrajectoryParser] LOW DATA QUALITY: ${recordCount} records < 3 threshold`);
            return {
                trajectory,
                valid: false,  // Not enough data points for reliable trajectory
                warning: `Insufficient data points: ${recordCount} < 3. May trigger retry.`,
                recordCount,
                quality: 'POOR'
            };
        }

        return {
            trajectory,
            valid: recordCount >= 2,  // At least 2 points for trajectory
            recordCount,
            quality: recordCount >= 5 ? 'EXCELLENT' : recordCount >= 3 ? 'GOOD' : 'POOR'
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
