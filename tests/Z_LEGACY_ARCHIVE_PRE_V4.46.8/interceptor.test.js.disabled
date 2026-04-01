/**
 * V66.000 - Mock Interceptor Tests
 * ===================================
 *
 * Unit tests for XHR interceptor functionality without real network.
 * Uses mocking to test response handling logic.
 *
 * @file interceptor.test.js
 * @version V66.000
 */

'use strict';

const { describe, it } = require('node:test');
const assert = require('assert');

const { parseJsonResponse } = require('../src/modules/parser');

// ============================================================================
// TEST DATA
// ============================================================================

const MOCK_API_RESPONSES = {
    standardFormat: {
        odds: [
            {
                timestamp: '2026-01-24T10:00:00Z',
                home: 2.50,
                draw: 3.20,
                away: 2.80
            },
            {
                timestamp: '2026-01-24T11:00:00Z',
                home: 2.45,
                draw: 3.25,
                away: 2.85
            }
        ]
    },

    resultsFormat: {
        results: [
            {
                timestamp: '2026-01-24T10:00:00Z',
                home_odd: 2.50,
                draw_odd: 3.20,
                away_odd: 2.80
            }
        ]
    },

    dataFormat: {
        data: [
            {
                time: '2026-01-24T10:00:00Z',
                h: 2.50,
                d: 3.20,
                a: 2.80
            }
        ]
    },

    singleRecord: {
        timestamp: '2026-01-24T10:00:00Z',
        home: 2.50,
        draw: 3.20,
        away: 2.80
    },

    alternativeFields: {
        odds: [
            {
                occurred_at: '2026-01-24T10:00:00Z',
                '1': 2.50,
                X: 3.20,
                '2': 2.80
            }
        ]
    },

    unixTimestamp: {
        odds: [
            {
                timestamp: 1706102400,
                home: 2.50,
                draw: 3.20,
                away: 2.80
            }
        ]
    },

    invalidResponse: {
        odds: [
            {
                timestamp: '2026-01-24T10:00:00Z'
            }
        ]
    },

    emptyArray: {
        odds: []
    },

    nullValues: {
        odds: [
            {
                timestamp: '2026-01-24T10:00:00Z',
                home: null,
                draw: 3.20,
                away: 2.80
            }
        ]
    },

    outOfRange: {
        odds: [
            {
                timestamp: '2026-01-24T10:00:00Z',
                home: 0.50,
                draw: 3.20,
                away: 2.80
            }
        ]
    }
};

// ============================================================================
// MOCK INTERCEPTOR CLASS
// ============================================================================

class MockApiInterceptor {
    constructor() {
        this.capturedResponses = [];
    }

    captureResponse(url, jsonData) {
        this.capturedResponses.push({
            url,
            json: jsonData,
            timestamp: Date.now()
        });
    }

    getCapturedResponses() {
        return this.capturedResponses;
    }

    hasData() {
        return this.capturedResponses.length > 0;
    }

    getByUrlPattern(pattern) {
        return this.capturedResponses.filter(r => r.url.includes(pattern));
    }

    clear() {
        this.capturedResponses = [];
    }
}

// ============================================================================
// TEST SUITE
// ============================================================================

describe('Mock Interceptor Tests', () => {

    describe('MockApiInterceptor', () => {

        it('should capture API responses', () => {
            const interceptor = new MockApiInterceptor();

            interceptor.captureResponse('/api/odds/123', MOCK_API_RESPONSES.standardFormat);

            assert.strictEqual(interceptor.capturedResponses.length, 1);
            assert.strictEqual(interceptor.hasData(), true);
        });

        it('should clear captured responses', () => {
            const interceptor = new MockApiInterceptor();

            interceptor.captureResponse('/api/odds/123', MOCK_API_RESPONSES.standardFormat);
            assert.strictEqual(interceptor.capturedResponses.length, 1);

            interceptor.clear();
            assert.strictEqual(interceptor.capturedResponses.length, 0);
        });

        it('should filter responses by URL pattern', () => {
            const interceptor = new MockApiInterceptor();

            interceptor.captureResponse('/api/odds/123', MOCK_API_RESPONSES.standardFormat);
            interceptor.captureResponse('/api/results/456', MOCK_API_RESPONSES.resultsFormat);
            interceptor.captureResponse('/ajax-match-odds/789', MOCK_API_RESPONSES.dataFormat);

            const oddsResponses = interceptor.getByUrlPattern('/api/odds');
            assert.strictEqual(oddsResponses.length, 1);

            const apiResponses = interceptor.getByUrlPattern('/api');
            assert.strictEqual(apiResponses.length, 2);
        });
    });

    describe('Response format handling', () => {

        it('should parse standard odds array format', () => {
            const records = parseJsonResponse(MOCK_API_RESPONSES.standardFormat, 'Provider_A');

            assert.ok(Array.isArray(records));
            assert.ok(records.length >= 1);
            assert.strictEqual(records[0].home_odd, 2.50);
        });

        it('should parse results array format', () => {
            const records = parseJsonResponse(MOCK_API_RESPONSES.resultsFormat, 'Provider_B');

            assert.ok(Array.isArray(records));
            assert.ok(records.length >= 1);
            assert.strictEqual(records[0].home_odd, 2.50);
        });

        it('should parse data array format', () => {
            const records = parseJsonResponse(MOCK_API_RESPONSES.dataFormat, 'Provider_C');

            assert.ok(Array.isArray(records));
            assert.ok(records.length >= 1);
            assert.strictEqual(records[0].home_odd, 2.50);
        });

        it('should parse single record format', () => {
            const records = parseJsonResponse(MOCK_API_RESPONSES.singleRecord, 'Provider_D');

            assert.ok(Array.isArray(records));
            assert.ok(records.length >= 1);
        });

        it('should parse alternative field names', () => {
            const records = parseJsonResponse(MOCK_API_RESPONSES.alternativeFields, 'Provider_E');

            assert.ok(records.length >= 1);
            assert.strictEqual(records[0].home_odd, 2.50);
            assert.strictEqual(records[0].draw_odd, 3.20);
            assert.strictEqual(records[0].away_odd, 2.80);
        });

        it('should handle Unix timestamp format', () => {
            const records = parseJsonResponse(MOCK_API_RESPONSES.unixTimestamp, 'Provider_A');

            assert.ok(records.length >= 1);
            assert.ok(records[0].timestamp.includes('T'));
        });
    });

    describe('Error handling', () => {

        it('should handle empty array gracefully', () => {
            const records = parseJsonResponse(MOCK_API_RESPONSES.emptyArray, 'Provider_A');

            assert.ok(Array.isArray(records));
            assert.strictEqual(records.length, 0);
        });

        it('should skip records with null values', () => {
            const records = parseJsonResponse(MOCK_API_RESPONSES.nullValues, 'Provider_A');

            assert.ok(Array.isArray(records));
        });

        it('should skip records with out of range odds', () => {
            const records = parseJsonResponse(MOCK_API_RESPONSES.outOfRange, 'Provider_A');

            assert.ok(Array.isArray(records));
            assert.strictEqual(records.length, 0);
        });

        it('should skip records with missing fields', () => {
            const records = parseJsonResponse(MOCK_API_RESPONSES.invalidResponse, 'Provider_A');

            assert.ok(Array.isArray(records));
            assert.strictEqual(records.length, 0);
        });

        it('should throw ParserError for non-object input', () => {
            assert.throws(() => {
                parseJsonResponse(null, 'Provider_A');
            });

            assert.throws(() => {
                parseJsonResponse('string', 'Provider_A');
            });

            assert.throws(() => {
                parseJsonResponse(undefined, 'Provider_A');
            });
        });
    });

    describe('Data integrity', () => {

        it('should sort records by timestamp', () => {
            const records = parseJsonResponse(MOCK_API_RESPONSES.standardFormat, 'Provider_A');

            for (let i = 1; i < records.length; i++) {
                const prevTime = new Date(records[i - 1].timestamp).getTime();
                const currTime = new Date(records[i].timestamp).getTime();
                assert.ok(currTime >= prevTime);
            }
        });

        it('should assign sequential sequence numbers', () => {
            const records = parseJsonResponse(MOCK_API_RESPONSES.standardFormat, 'Provider_A');

            records.forEach((record, index) => {
                assert.strictEqual(record.sequence, index);
            });
        });

        it('should include provider name in all records', () => {
            const records = parseJsonResponse(MOCK_API_RESPONSES.standardFormat, 'TestProvider');

            records.forEach(record => {
                assert.strictEqual(record.provider_name, 'TestProvider');
            });
        });

        it('should calculate payout for valid records', () => {
            const records = parseJsonResponse(MOCK_API_RESPONSES.standardFormat, 'Provider_A');

            records.forEach(record => {
                assert.ok(record.payout !== null);
                assert.ok(record.payout >= 0.85 && record.payout <= 0.99);
            });
        });

        it('should include raw_data metadata', () => {
            const records = parseJsonResponse(MOCK_API_RESPONSES.standardFormat, 'Provider_A');

            records.forEach(record => {
                assert.ok(record.raw_data);
                assert.strictEqual(record.raw_data.source, 'v66.000_api_parser');
                assert.ok(Array.isArray(record.raw_data.dimensions));
            });
        });
    });

    describe('Provider tracking', () => {

        it('should associate correct provider with records', () => {
            const providers = ['Provider_A', 'Provider_B', 'Provider_C'];

            providers.forEach(provider => {
                const records = parseJsonResponse(MOCK_API_RESPONSES.standardFormat, provider);

                records.forEach(record => {
                    assert.strictEqual(record.provider_name, provider);
                });
            });
        });

        it('should handle different providers independently', () => {
            const recordsA = parseJsonResponse(MOCK_API_RESPONSES.standardFormat, 'Provider_A');
            const recordsB = parseJsonResponse(MOCK_API_RESPONSES.resultsFormat, 'Provider_B');

            assert.strictEqual(recordsA[0].provider_name, 'Provider_A');
            assert.strictEqual(recordsB[0].provider_name, 'Provider_B');
        });
    });
});

// ============================================================================
// EXPORTS
// ============================================================================

module.exports = {
    MockApiInterceptor,
    MOCK_API_RESPONSES
};
