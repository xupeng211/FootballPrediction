#!/usr/bin/env node
/**
 * [Genesis.StressTest] 20 Match Stress Test Runner
 * ===============================================
 *
 * Run apex_engine.js stress test on selected matches
 */

const { execSync } = require('child_process');
const fs = require('fs');
const path = require('path');

// Test configuration
const TEST_URLS = [
    'https://www.oddsportal.com/football/spain/laliga-2024-2025/real-madrid-real-sociedad-jVjHFI03/',
    'https://www.oddsportal.com/football/spain/laliga-2024-2025/alaves-osasuna-befPDdVF/',
    'https://www.oddsportal.com/football/spain/laliga-2024-2025/leganes-valladolid-hdCcelFl/',
    'https://www.oddsportal.com/football/spain/laliga-2024-2025/espanyol-las-palmas-nuc2SQDs/',
    'https://www.oddsportal.com/football/spain/laliga/girona-atl-madrid-dhsK6cBj/',
    'https://www.oddsportal.com/football/spain/laliga-2024-2025/villarreal-sevilla-djfP9mUs/',
    'https://www.oddsportal.com/football/italy/serie-a-2024-2025/atalanta-parma-r9FABj4C/',
    'https://www.oddsportal.com/football/italy/serie-a-2024-2025/empoli-verona-2DnySBlg/',
    'https://www.oddsportal.com/football/italy/serie-a-2024-2025/lazio-lecce-MF2xQkJ5/',
    'https://www.oddsportal.com/football/italy/serie-a-2024-2025/torino-as-roma-tKZ2tB3n/',
    'https://www.oddsportal.com/football/italy/serie-a-2024-2025/udinese-fiorentina-MTsBvkYb/',
    'https://www.oddsportal.com/football/italy/serie-a-2024-2025/venezia-juventus-fstJxT2B/'
];

const ENGINE_PATH = 'scripts/ops/apex_engine.js';
const DELAY_MS = 3000;  // 3s delay between matches
const LOG_FILE = 'logs/ops/stress_test_13.log';

// Ensure log directory exists
const logDir = path.dirname(LOG_FILE);
if (!fs.existsSync(logDir)) {
    fs.mkdirSync(logDir, { recursive: true });
}

console.log('='.repeat(70));
console.log('[Genesis.StressTest] Starting 13 Match Stress Test');
console.log('='.repeat(70));
console.log(`Engine: ${ENGINE_PATH}`);
console.log(`Matches: ${TEST_URLS.length}`);
console.log(`Delay: ${DELAY_MS}ms`);
console.log(`Log: ${LOG_FILE}`);
console.log('='.repeat(70));

const results = {
    total: TEST_URLS.length,
    success: 0,
    failed: 0,
    errors: []
};

let startTime = Date.now();

for (let i = 0; i < TEST_URLS.length; i++) {
    const url = TEST_URLS[i];
    const matchId = url.split('/').filter(Boolean).pop(); // Extract match ID from URL

    console.log(`\n[${i + 1}/${TEST_URLS.length}] Testing: ${matchId}`);
    console.log(`URL: ${url.substring(0, 70)}...`);

    try {
        const cmd = `node ${ENGINE_PATH} "${url}" "${matchId}"`;

        const start = Date.now();
        const result = execSync(cmd, {
            encoding: 'utf8',
            stdio: 'pipe',
            timeout: 120000  // 2 min timeout
        });

        const elapsed = Date.now() - start;

        // Check if apex_engine succeeded (exit code 0)
        if (result.status === 0) {
            results.success++;
            console.log(`✅ SUCCESS in ${elapsed}ms`);
        } else {
            results.failed++;
            results.errors.push({ matchId, url, error: result.stderr });
            console.log(`❌ FAILED in ${elapsed}ms`);
            console.log(`Error: ${result.stderr.substring(0, 200)}...`);
        }

    } catch (error) {
        results.failed++;
        results.errors.push({ matchId, url, error: error.message });
        console.log(`❌ EXCEPTION: ${error.message}`);
    }

    // Delay between matches
    if (i < TEST_URLS.length - 1) {
        console.log(`Waiting ${DELAY_MS}ms before next match...`);
        const delay = Math.floor(DELAY_MS * (0.8 + Math.random() * 0.4));  // ±20% jitter
        const ms = Math.floor(delay);
        const seconds = (ms / 1000).toFixed(1);
        console.log(`Next test in ${seconds}s...`);

        // Synchronous sleep for Node.js
        Atomics.wait(new Int32Array(new SharedArrayBuffer(4)), 0, ms);
    }
}

const totalTime = Date.now() - startTime;
const avgTime = (totalTime / TEST_URLS.length / 1000).toFixed(2);

console.log('\n' + '='.repeat(70));
console.log('[Genesis.StressTest] Final Report');
console.log('='.repeat(70));
console.log(`Total: ${results.total}`);
console.log(`Success: ${results.success}`);
console.log(`Failed: ${results.failed}`);
console.log(`Success Rate: ${(100 * results.success / results.total).toFixed(1)}%`);
console.log(`Total Time: ${(totalTime / 1000).toFixed(1)}s`);
console.log(`Avg Time: ${avgTime}s per match`);
console.log('='.repeat(70));

// Save summary to file
const summary = {
    timestamp: new Date().toISOString(),
    total: results.total,
    success: results.success,
    failed: results.failed,
    successRate: (100 * results.success / results.total).toFixed(1) + '%',
    totalTimeSec: (totalTime / 1000).toFixed(1),
    avgTimeSec: avgTime,
    errors: results.errors.map(e => ({ matchId: e.matchId, error: e.error?.substring(0, 100) }))
};

fs.appendFileSync(LOG_FILE, '\n\n' + JSON.stringify(summary, null, 2) + '\n');

console.log(`\nSummary saved to: ${LOG_FILE}`);
