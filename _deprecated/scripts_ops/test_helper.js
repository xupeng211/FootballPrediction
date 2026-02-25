/**
 * V43.000 Test Helper Module
 * ===========================
 *
 * Unit testing utilities for offline parser validation
 *
 * Core Features:
 *   - HTML sample file management
 *   - Batch testing with detailed reporting
 *   - Golden sample validation
 *
 * Author: Software Architect & QA Lead
 * Version: V43.000
 * Date: 2026-01-24
 */

'use strict';

const fs = require('fs');
const path = require('path');
const parser = require('./parser');

// ============================================================================
// TEST CONFIGURATION
// ============================================================================

const TEST_CONFIG = {
    samplesDir: path.join(__dirname, '../tests'),
    logsDir: path.join(__dirname, '../logs'),
    goldenSample: 'v42_910_tooltip_sample.html',
    expectedRecordsPerSample: 1
};

// ============================================================================
// SAMPLE GENERATION
// ============================================================================

/**
 * Create a test HTML sample file from V42.910 forensic results
 * @param {string} outputPath - Output file path
 * @returns {boolean} - Success status
 */
function createGoldenSample(outputPath) {
    // Sample HTML based on V42.910 forensic findings (sanitized)
    const goldenHTML = `<div data-v-037756ac="" class="flex flex-col gap-2">
    <div data-v-037756ac="" class="height-content absolute bottom-[30px] z-10 flex w-max flex-col gap-2 bg-gray-med_light pb-2 pl-2 pr-2 pt-2 text-[10px] text-black-main shadow-xl">
        <h3 class="text-sm font-semibold uppercase leading-4 text-[#2F2F2F]">Odds movement</h3>
        <div class="flex flex-row gap-3">
            <div class="flex flex-col gap-1">
                <div class="flex gap-3">
                    <div class="text-[10px] font-normal">24 Jan, 10:00</div>
                </div>
            </div>
            <div class="flex flex-col gap-1">
                <div class="text-[10px] font-bold">1.95</div>
            </div>
            <div class="flex flex-col gap-1">
                <div class="text-[10px] font-bold text-green-dark">+0.05</div>
            </div>
        </div>
        <div class="mt-2 gap-1">
            <div class="text-[10px] font-bold">Opening odds: 1.90</div>
        </div>
    </div>
</div>`;

    try {
        const fullPath = path.resolve(outputPath);
        fs.writeFileSync(fullPath, goldenHTML, 'utf-8');
        console.log(`[Test Helper] Golden sample created: ${fullPath}`);
        return true;
    } catch (error) {
        console.error(`[Test Helper] Failed to create golden sample: ${error.message}`);
        return false;
    }
}

// ============================================================================
// BATCH TESTING
// ============================================================================

/**
 * Run batch unit tests on all HTML samples in directory
 * @param {string} testDir - Directory containing test HTML files
 * @returns {Object} - Test results
 */
function runBatchTests(testDir = TEST_CONFIG.samplesDir) {
    console.log('[Test Helper] === BATCH UNIT TESTS ===');
    console.log(`[Test Helper] Test directory: ${testDir}`);
    console.log('');

    const results = {
        total: 0,
        passed: 0,
        failed: 0,
        skipped: 0,
        details: []
    };

    try {
        // Check if directory exists
        if (!fs.existsSync(testDir)) {
            console.log(`[Test Helper] Test directory not found, creating...`);
            fs.mkdirSync(testDir, { recursive: true });

            // Create golden sample
            const goldenPath = path.join(testDir, TEST_CONFIG.goldenSample);
            createGoldenSample(goldenPath);
        }

        // Get all HTML files
        const files = fs.readdirSync(testDir).filter(f =>
            f.endsWith('.html') || f.endsWith('.htm')
        );

        if (files.length === 0) {
            console.log('[Test Helper] No test files found');
            return results;
        }

        results.total = files.length;

        // Test each file
        for (const file of files) {
            const filePath = path.join(testDir, file);
            const fileResult = {
                file: file,
                path: filePath,
                success: false,
                records: 0,
                error: null
            };

            try {
                const parseResult = parser.parseFromFile(filePath, 'test_provider');

                if (parseResult.success) {
                    fileResult.success = true;
                    fileResult.records = parseResult.recordCount;
                    results.passed++;
                    console.log(`[Test Helper] [PASS] ${file}: [${parseResult.recordCount}] records`);
                } else {
                    fileResult.error = parseResult.error;
                    results.failed++;
                    console.log(`[Test Helper] [FAIL] ${file}: ${parseResult.error}`);
                }

            } catch (error) {
                fileResult.error = error.message;
                results.failed++;
                console.log(`[Test Helper] [ERROR] ${file}: ${error.message}`);
            }

            results.details.push(fileResult);
        }

    } catch (error) {
        console.error(`[Test Helper] Batch test error: ${error.message}`);
    }

    console.log('');
    console.log('[Test Helper] === TEST SUMMARY ===');
    console.log(`[Test Helper] Total: ${results.total}`);
    console.log(`[Test Helper] Passed: ${results.passed}`);
    console.log(`[Test Helper] Failed: ${results.failed}`);
    console.log('[Test Helper] ====================');
    console.log('');

    return results;
}

/**
 * Validate parser against golden sample
 * @returns {Object} - Validation result
 */
function validateGoldenSample() {
    console.log('[Test Helper] === GOLDEN SAMPLE VALIDATION ===');
    console.log('');

    const goldenPath = path.join(TEST_CONFIG.samplesDir, TEST_CONFIG.goldenSample);

    // Ensure golden sample exists
    if (!fs.existsSync(goldenPath)) {
        console.log('[Test Helper] Creating golden sample...');
        createGoldenSample(goldenPath);
    }

    const parseResult = parser.parseFromFile(goldenPath, 'golden_test_provider');

    if (parseResult.success) {
        console.log(`[Test Helper] Golden sample validation: [PASS]`);
        console.log(`[Test Helper] Records extracted: [${parseResult.recordCount}]`);

        // Validate record structure
        if (parseResult.records.length > 0) {
            const record = parseResult.records[0];
            console.log('[Test Helper] Record structure:');
            console.log(`[Test Helper]   - provider_name: ${record.provider_name}`);
            console.log(`[Test Helper]   - metric_type: ${record.metric_type}`);
            console.log(`[Test Helper]   - value: [REDACTED]`);
            console.log(`[Test Helper]   - occurred_at: ${record.occurred_at}`);
        }

        console.log('');
        console.log('[Test Helper] Golden sample validation: PASSED');
        console.log('');

        return {
            success: true,
            recordCount: parseResult.recordCount,
            records: parseResult.records
        };
    } else {
        console.log(`[Test Helper] Golden sample validation: [FAILED]`);
        console.log(`[Test Helper] Error: ${parseResult.error}`);
        console.log('');

        return {
            success: false,
            error: parseResult.error
        };
    }
}

// ============================================================================
// COVERAGE REPORTING
// ============================================================================

/**
 * Generate test coverage report
 * @param {Object} testResults - Test results from runBatchTests
 * @returns {string} - Formatted coverage report
 */
function generateCoverageReport(testResults) {
    const coverage = testResults.total > 0
        ? ((testResults.passed / testResults.total) * 100).toFixed(2)
        : '0.00';

    let report = '';
    report += '========================================\n';
    report += '[Test Helper] COVERAGE REPORT\n';
    report += '========================================\n';
    report += `Total Tests:     ${testResults.total}\n`;
    report += `Passed:          ${testResults.passed}\n`;
    report += `Failed:          ${testResults.failed}\n`;
    report += `Skipped:         ${testResults.skipped}\n`;
    report += `Coverage:        ${coverage}%\n`;
    report += '========================================\n';
    report += '\n';

    if (testResults.failed > 0) {
        report += 'Failed Tests:\n';
        for (const detail of testResults.details) {
            if (!detail.success) {
                report += `  - ${detail.file}: ${detail.error}\n`;
            }
        }
        report += '\n';
    }

    return report;
}

// ============================================================================
// EXPORTS
// ============================================================================

module.exports = {
    createGoldenSample,
    runBatchTests,
    validateGoldenSample,
    generateCoverageReport,
    TEST_CONFIG
};
