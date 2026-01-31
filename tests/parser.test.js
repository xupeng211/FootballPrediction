/**
 * V66.000 - Parser Unit Tests
 * =============================
 *
 * Unit tests for the parser module using Node.js built-in test runner.
 *
 * @file parser.test.js
 * @version V66.000
 */

'use strict';

const { describe, it } = require('node:test');
const assert = require('assert');

const {
    parseTooltipHTML,
    parseJsonResponse,
    calibrateTimestamp,
    calculatePayout,
    ParserError
} = require('../src/modules/parser');

// ============================================================================
// TEST DATA
// ============================================================================

const MOCK_TOOLTIP_HTML = `
    <div>
        <h3>Odds movement</h3>
        <div class="temporal-row">
            <span class="time">24 Jan, 10:00</span>
            <span class="odds">2.50</span>
            <span class="odds">3.20</span>
            <span class="odds">2.80</span>
        </div>
        <div class="temporal-row">
            <span class="time">24 Jan, 11:30</span>
            <span class="odds">2.45</span>
            <span class="odds">3.25</span>
            <span class="odds">2.85</span>
        </div>
    </div>
`;

const MOCK_API_JSON = {
    odds: [
        {
            timestamp: '2026-01-24T10:00:00Z',
            home: 2.50,
            draw: 3.20,
            away: 2.80
        },
        {
            timestamp: '2026-01-24T11:30:00Z',
            home: 2.45,
            draw: 3.25,
            away: 2.85
        }
    ]
};

// ============================================================================
// TEST SUITE
// ============================================================================

describe('Parser Module Unit Tests', () => {

    // ========================================================================
    // Timestamp Calibration Tests
    // ========================================================================

    describe('calibrateTimestamp', () => {

        it('should parse "DD Mon, HH:MM" format', () => {
            const result = calibrateTimestamp('24 Jan, 10:00');
            assert.ok(result);
            assert.ok(result.includes('T'));
            assert.ok(result.includes('10:00:00'));
        });

        it('should parse "Mon DD, HH:MM" format', () => {
            const result = calibrateTimestamp('Jan 24, 14:30');
            assert.ok(result);
            assert.ok(result.includes('T'));
            assert.ok(result.includes('14:30:00'));
        });

        it('should parse "HH:MM" format (time only)', () => {
            const result = calibrateTimestamp('10:00');
            assert.ok(result);
            assert.ok(result.includes('T'));
        });

        it('should return null for invalid input', () => {
            assert.strictEqual(calibrateTimestamp(null), null);
            assert.strictEqual(calibrateTimestamp(''), null);
            assert.strictEqual(calibrateTimestamp('invalid'), null);
        });
    });

    // ========================================================================
    // Payout Calculation Tests
    // ========================================================================

    describe('calculatePayout', () => {

        it('should calculate correct payout', () => {
            const result = calculatePayout(2.50, 3.20, 2.80);
            assert.ok(result !== null);
            assert.ok(result >= 0.85 && result <= 0.99);
        });

        it('should return null for invalid odds', () => {
            assert.strictEqual(calculatePayout(0, 3.20, 2.80), null);
            assert.strictEqual(calculatePayout(2.50, null, 2.80), null);
            assert.strictEqual(calculatePayout(2.50, 3.20, null), null);
        });

        it('should return null for out-of-range payout', () => {
            const result = calculatePayout(1.01, 1.01, 1.01);
            assert.strictEqual(result, null);
        });
    });

    // ========================================================================
    // HTML Parsing Tests
    // ========================================================================

    describe('parseTooltipHTML', () => {

        it('should parse valid tooltip HTML', () => {
            const records = parseTooltipHTML(MOCK_TOOLTIP_HTML, 'Provider_A');
            assert.ok(Array.isArray(records));
            assert.ok(records.length > 0);
        });

        it('should extract all temporal points', () => {
            const records = parseTooltipHTML(MOCK_TOOLTIP_HTML, 'Provider_A');
            assert.ok(records.length >= 2);
        });

        it('should include all required fields', () => {
            const records = parseTooltipHTML(MOCK_TOOLTIP_HTML, 'Provider_A');
            const record = records[0];

            assert.ok(record.provider_name);
            assert.ok(record.timestamp);
            assert.ok(typeof record.home_odd === 'number');
            assert.ok(typeof record.draw_odd === 'number');
            assert.ok(typeof record.away_odd === 'number');
            assert.ok(record.sequence !== undefined);
        });

        it('should sort records by timestamp', () => {
            const records = parseTooltipHTML(MOCK_TOOLTIP_HTML, 'Provider_A');
            for (let i = 1; i < records.length; i++) {
                const prevTime = new Date(records[i - 1].timestamp).getTime();
                const currTime = new Date(records[i].timestamp).getTime();
                assert.ok(currTime >= prevTime);
            }
        });

        it('should assign sequential sequence numbers', () => {
            const records = parseTooltipHTML(MOCK_TOOLTIP_HTML, 'Provider_A');
            records.forEach((record, index) => {
                assert.strictEqual(record.sequence, index);
            });
        });

        it('should throw ParserError for empty input', () => {
            assert.throws(
                () => parseTooltipHTML('', 'Provider_A'),
                ParserError
            );
        });

        it('should throw ParserError for missing anchor', () => {
            assert.throws(
                () => parseTooltipHTML('<div>No anchor here</div>', 'Provider_A'),
                ParserError
            );
        });

        it('should return empty array for HTML with no valid rows', () => {
            const records = parseTooltipHTML(
                '<h3>Odds movement</h3><div>No valid rows here</div>',
                'Provider_A'
            );
            assert.ok(Array.isArray(records));
        });
    });

    // ========================================================================
    // JSON Parsing Tests
    // ========================================================================

    describe('parseJsonResponse', () => {

        it('should parse API JSON with odds array', () => {
            const records = parseJsonResponse(MOCK_API_JSON, 'Provider_A');
            assert.ok(Array.isArray(records));
            assert.ok(records.length > 0);
        });

        it('should extract all required fields from JSON', () => {
            const records = parseJsonResponse(MOCK_API_JSON, 'Provider_A');
            const record = records[0];

            assert.strictEqual(record.provider_name, 'Provider_A');
            assert.ok(record.timestamp);
            assert.strictEqual(record.home_odd, 2.50);
            assert.strictEqual(record.draw_odd, 3.20);
            assert.strictEqual(record.away_odd, 2.80);
        });

        it('should handle different field name variants', () => {
            const variantJson = {
                data: [{
                    time: '2026-01-24T10:00:00Z',
                    h: 1.5,
                    X: 4.0,
                    '2': 6.0
                }]
            };

            const records = parseJsonResponse(variantJson, 'Provider_B');
            assert.ok(records.length > 0);
            assert.strictEqual(records[0].home_odd, 1.5);
            assert.strictEqual(records[0].draw_odd, 4.0);
            assert.strictEqual(records[0].away_odd, 6.0);
        });

        it('should return empty array for invalid JSON structure', () => {
            const records = parseJsonResponse({ invalid: 'structure' }, 'Provider_A');
            assert.ok(Array.isArray(records));
            assert.strictEqual(records.length, 0);
        });

        it('should throw ParserError for non-object input', () => {
            assert.throws(
                () => parseJsonResponse(null, 'Provider_A'),
                ParserError
            );
            assert.throws(
                () => parseJsonResponse('string', 'Provider_A'),
                ParserError
            );
        });
    });

    // ========================================================================
    // Data Validation Tests
    // ========================================================================

    describe('Data validation', () => {

        it('should reject odds below minimum', () => {
            const invalidHtml = `
                <h3>Odds movement</h3>
                <div><span>24 Jan, 10:00</span><span>0.50</span><span>3.20</span><span>2.80</span></div>
            `;
            const records = parseTooltipHTML(invalidHtml, 'Provider_A');
            assert.strictEqual(records.length, 0);
        });

        it('should reject odds above maximum', () => {
            const invalidHtml = `
                <h3>Odds movement</h3>
                <div><span>24 Jan, 10:00</span><span>100.50</span><span>3.20</span><span>2.80</span></div>
            `;
            const records = parseTooltipHTML(invalidHtml, 'Provider_A');
            assert.strictEqual(records.length, 0);
        });

        it('should handle provider name parameter correctly', () => {
            const records = parseTooltipHTML(MOCK_TOOLTIP_HTML, 'TestProvider');
            if (records.length > 0) {
                assert.strictEqual(records[0].provider_name, 'TestProvider');
            }
        });
    });
});

// ============================================================================
// EXPORTS
// ============================================================================

module.exports = {
    MOCK_TOOLTIP_HTML,
    MOCK_API_JSON
};
