#!/usr/bin/env node
/**
 * V50.200 API Interceptor Unit Tests (TDD)
 * ===========================================
 *
 * Test-Driven Development for API interceptor module
 *
 * Test Coverage:
 *   - setupApiInterceptor() creates response handler
 *   - Captures /ajax-match-odds/ responses
 *   - Captures /api/ responses
 *   - Stores data in global._api_buffer
 *   - Returns captured responses array
 *   - Non-JSON responses are ignored
 *   - Non-matching URLs are ignored
 *
 * @module v50_200_api_interceptor.test
 * @version V50.200
 * @since 2026-01-24
 */

'use strict';

const assert = require('assert');

// ============================================================================
// MOCK CLASSES
// ============================================================================

/**
 * Mock Page for API interception testing
 */
class MockPageForApiInterceptor {
    constructor() {
        this.responseHandlers = [];
        this.globalBuffer = [];
        this.capturedResponses = [];
    }

    /**
     * Register response handler (simulates page.on('response'))
     */
    on(event, handler) {
        if (event === 'response') {
            this.responseHandlers.push(handler);
        }
    }

    /**
     * Simulate incoming response
     */
    async _simulateResponse(url, contentType, jsonData) {
        const mockResponse = {
            url: () => url,
            headerValue: (name) => {
                if (name === 'content-type') {
                    return contentType;
                }
                return null;
            },
            json: async () => jsonData,
            status: () => 200
        };

        // Trigger all registered handlers
        for (const handler of this.responseHandlers) {
            await handler(mockResponse);
        }

        return mockResponse;
    }

    /**
     * Simulate page.evaluate for global buffer storage
     */
    async evaluate(func, data) {
        // Simulate browser global._api_buffer storage
        this.globalBuffer.push(data);
    }
}

// ============================================================================
// TEST SUITE 1: API INTERCEPTOR SETUP
// ============================================================================

async function test_suite_1_api_interceptor_setup() {
    console.log('\n=== TEST SUITE 1: API Interceptor Setup ===\n');

    let testsPassed = 0;
    let testsFailed = 0;

    // Test 1.1: Verify setupApiInterceptor returns capture array
    async function test_1_1() {
        console.log('Test 1.1: setupApiInterceptor returns capture array');
        try {
            // Import the interaction module (will implement later)
            const interaction = require('../../scripts/ops/modules/interaction');

            const mockPage = new MockPageForApiInterceptor();
            const capturedResponses = await interaction.setupApiInterceptor(mockPage);

            assert(Array.isArray(capturedResponses), 'Should return array');
            assert.strictEqual(capturedResponses.length, 0, 'Initial array should be empty');

            console.log('  ✓ PASS: Returns empty capture array');
            return true;
        } catch (error) {
            console.log(`  𐄄 FAIL: ${error.message}`);
            return false;
        }
    }

    // Test 1.2: Verify response handler is registered
    async function test_1_2() {
        console.log('Test 1.2: Response handler registered on page');
        try {
            const interaction = require('../../scripts/ops/modules/interaction');

            const mockPage = new MockPageForApiInterceptor();
            const handlerCountBefore = mockPage.responseHandlers.length;

            await interaction.setupApiInterceptor(mockPage);

            const handlerCountAfter = mockPage.responseHandlers.length;
            assert.strictEqual(handlerCountAfter, handlerCountBefore + 1, 'Should register one handler');

            console.log('  ✓ PASS: Handler registered');
            return true;
        } catch (error) {
            console.log(`  𐄄 FAIL: ${error.message}`);
            return false;
        }
    }

    // Test 1.3: Captures /ajax-match-odds/ responses
    async function test_1_3() {
        console.log('Test 1.3: Captures /ajax-match-odds/ responses');
        try {
            const interaction = require('../../scripts/ops/modules/interaction');

            const mockPage = new MockPageForApiInterceptor();
            const capturedResponses = await interaction.setupApiInterceptor(mockPage);

            // Simulate API response
            const testUrl = 'https://www.oddsportal.com/ajax-match-odds/12345678/';
            const testData = { odds: [{ home: 1.5, draw: 4.0, away: 6.0 }] };

            await mockPage._simulateResponse(testUrl, 'application/json', testData);

            assert.strictEqual(capturedResponses.length, 1, 'Should capture one response');
            assert.deepStrictEqual(capturedResponses[0].json, testData, 'Should capture JSON data');

            console.log('  ✓ PASS: /ajax-match-odds/ response captured');
            return true;
        } catch (error) {
            console.log(`  𐄄 FAIL: ${error.message}`);
            return false;
        }
    }

    // Test 1.4: Captures /api/ responses
    async function test_1_4() {
        console.log('Test 1.4: Captures /api/ responses');
        try {
            const interaction = require('../../scripts/ops/modules/interaction');

            const mockPage = new MockPageForApiInterceptor();
            const capturedResponses = await interaction.setupApiInterceptor(mockPage);

            // Simulate API response
            const testUrl = 'https://www.oddsportal.com/api/matches/12345678/odds/';
            const testData = { results: [{ timestamp: '2026-01-24T10:00:00Z', value: 1.5 }] };

            await mockPage._simulateResponse(testUrl, 'application/json', testData);

            assert.strictEqual(capturedResponses.length, 1, 'Should capture one response');
            assert.deepStrictEqual(capturedResponses[0].json, testData, 'Should capture JSON data');

            console.log('  ✓ PASS: /api/ response captured');
            return true;
        } catch (error) {
            console.log(`  𐄄 FAIL: ${error.message}`);
            return false;
        }
    }

    // Test 1.5: Ignores non-matching URLs
    async function test_1_5() {
        console.log('Test 1.5: Ignores non-matching URLs');
        try {
            const interaction = require('../../scripts/ops/modules/interaction');

            const mockPage = new MockPageForApiInterceptor();
            const capturedResponses = await interaction.setupApiInterceptor(mockPage);

            // Simulate non-matching URL
            const testUrl = 'https://www.oddsportal.com/football/england/premier-league/';
            const testData = { html: '<div>page content</div>' };

            await mockPage._simulateResponse(testUrl, 'text/html', testData);

            assert.strictEqual(capturedResponses.length, 0, 'Should ignore non-matching URLs');

            console.log('  ✓ PASS: Non-matching URLs ignored');
            return true;
        } catch (error) {
            console.log(`  𐄄 FAIL: ${error.message}`);
            return false;
        }
    }

    // Test 1.6: Stores data in global._api_buffer
    async function test_1_6() {
        console.log('Test 1.6: Stores data in global._api_buffer');
        try {
            const interaction = require('../../scripts/ops/modules/interaction');

            const mockPage = new MockPageForApiInterceptor();
            await interaction.setupApiInterceptor(mockPage);

            // Simulate API response
            const testUrl = 'https://www.oddsportal.com/ajax-match-odds/12345678/';
            const testData = { odds: [{ home: 1.5 }] };

            await mockPage._simulateResponse(testUrl, 'application/json', testData);

            assert.strictEqual(mockPage.globalBuffer.length, 1, 'Should store in global buffer');
            assert.deepStrictEqual(mockPage.globalBuffer[0], testData, 'Should store correct data');

            console.log('  ✓ PASS: Data stored in global._api_buffer');
            return true;
        } catch (error) {
            console.log(`  𐄄 FAIL: ${error.message}`);
            return false;
        }
    }

    // Run all tests in suite 1
    const tests = [
        test_1_1,
        test_1_2,
        test_1_3,
        test_1_4,
        test_1_5,
        test_1_6
    ];

    for (const test of tests) {
        const result = await test();
        if (result) {
            testsPassed++;
        } else {
            testsFailed++;
        }
    }

    console.log(`\nSuite 1 Results: ${testsPassed} passed, ${testsFailed} failed\n`);
    return { passed: testsPassed, failed: testsFailed };
}

// ============================================================================
// TEST SUITE 2: RAW JSON PARSER
// ============================================================================

async function test_suite_2_raw_json_parser() {
    console.log('\n=== TEST SUITE 2: Raw JSON Parser ===\n');

    let testsPassed = 0;
    let testsFailed = 0;

    // Test 2.1: Parse basic odds structure
    async function test_2_1() {
        console.log('Test 2.1: Parse basic odds structure');
        try {
            const parserV49 = require('../../scripts/ops/modules/parser_v49');

            const rawJson = {
                odds: [
                    { timestamp: '2026-01-24T10:00:00Z', home: 1.5, draw: 4.0, away: 6.0 },
                    { timestamp: '2026-01-24T11:00:00Z', home: 1.45, draw: 4.2, away: 6.5 }
                ]
            };

            const records = parserV49.parseRawJsonResponse(rawJson, 'Entity_P');

            assert(Array.isArray(records), 'Should return array');
            assert.strictEqual(records.length, 2, 'Should parse 2 records');
            assert.strictEqual(records[0].provider_name, 'Entity_P', 'Should set provider name');

            console.log('  ✓ PASS: Basic odds structure parsed');
            return true;
        } catch (error) {
            console.log(`  𐄄 FAIL: ${error.message}`);
            return false;
        }
    }

    // Test 2.2: Calculate payout from raw JSON
    async function test_2_2() {
        console.log('Test 2.2: Calculate payout from raw JSON');
        try {
            const parserV49 = require('../../scripts/ops/modules/parser_v49');

            const rawJson = {
                odds: [
                    { timestamp: '2026-01-24T10:00:00Z', home: 2.0, draw: 3.0, away: 4.0 }
                ]
            };

            const records = parserV49.parseRawJsonResponse(rawJson, 'Entity_P');

            // Payout = 1 / (1/2 + 1/3 + 1/4) = 1 / (0.5 + 0.333 + 0.25) = 1 / 1.083 = 0.9231
            // Implementation uses 4 decimal places
            const expectedPayout = 0.9231;
            assert.strictEqual(records[0].payout, expectedPayout, 'Should calculate correct payout');

            console.log('  ✓ PASS: Payout calculated correctly');
            return true;
        } catch (error) {
            console.log(`  𐄄 FAIL: ${error.message}`);
            return false;
        }
    }

    // Test 2.3: Handle missing timestamp
    async function test_2_3() {
        console.log('Test 2.3: Handle missing timestamp gracefully');
        try {
            const parserV49 = require('../../scripts/ops/modules/parser_v49');

            const rawJson = {
                odds: [
                    { home: 1.5, draw: 4.0, away: 6.0 }  // No timestamp
                ]
            };

            const records = parserV49.parseRawJsonResponse(rawJson, 'Entity_P');

            // Should return empty or handle gracefully
            assert(Array.isArray(records), 'Should return array');
            console.log('  ✓ PASS: Missing timestamp handled gracefully');
            return true;
        } catch (error) {
            console.log(`  𐄄 FAIL: ${error.message}`);
            return false;
        }
    }

    // Run all tests in suite 2
    const tests = [
        test_2_1,
        test_2_2,
        test_2_3
    ];

    for (const test of tests) {
        const result = await test();
        if (result) {
            testsPassed++;
        } else {
            testsFailed++;
        }
    }

    console.log(`\nSuite 2 Results: ${testsPassed} passed, ${testsFailed} failed\n`);
    return { passed: testsPassed, failed: testsFailed };
}

// ============================================================================
// MAIN TEST RUNNER
// ============================================================================

async function runAllTests() {
    console.log('\n============================================================');
    console.log('V50.200 API Interceptor Unit Tests (TDD)');
    console.log('============================================================');

    const suite1Results = await test_suite_1_api_interceptor_setup();
    const suite2Results = await test_suite_2_raw_json_parser();

    const totalPassed = suite1Results.passed + suite2Results.passed;
    const totalFailed = suite1Results.failed + suite2Results.failed;
    const totalTests = totalPassed + totalFailed;

    console.log('\n============================================================');
    console.log('FINAL RESULTS');
    console.log('============================================================');
    console.log(`Total Tests: ${totalTests}`);
    console.log(`Passed: ${totalPassed}`);
    console.log(`Failed: ${totalFailed}`);
    console.log(`Success Rate: ${Math.round((totalPassed / totalTests) * 100)}%`);
    console.log('============================================================\n');

    if (totalFailed > 0) {
        process.exit(1);
    }

    process.exit(0);
}

// Run tests if executed directly
if (require.main === module) {
    runAllTests().catch(error => {
        console.error('Fatal error running tests:', error);
        process.exit(1);
    });
}

module.exports = {
    test_suite_1_api_interceptor_setup,
    test_suite_2_raw_json_parser,
    MockPageForApiInterceptor
};
