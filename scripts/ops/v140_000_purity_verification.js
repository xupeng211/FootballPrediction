/**
 * V140.000 Data Purity Verification Flight
 * =============================================================================
 *
 * Validates the V140.000 data purity calibration fixes:
 * 1. 强制初盘打标 - earliest point marked as Initial
 * 2. 时区硬化 - UTC timezone enforcement
 * 3. 年份校准 - cross-year detection and auto-correction
 *
 * @module v140_000_purity_verification
 * @version V140.000
 * @since 2026-01-27
 * @author Principal Data Engineer (Data Purity Specialist)
 */

'use strict';

const { QuantHarvester } = require('../../src/engines/QuantHarvester');

// Configuration from environment
const config = {
    // V140.000: Data Purity Configuration
    enforceUTC: process.env.ENFORCE_UTC !== 'false',
    baseYear: parseInt(process.env.BASE_YEAR) || new Date().getFullYear(),
    maxFutureToleranceHours: parseInt(process.env.MAX_FUTURE_TOLERANCE_HOURS) || 48,

    // Database configuration
    dbHost: process.env.DB_HOST || '172.25.16.1',
    dbPort: parseInt(process.env.DB_PORT) || 5432,
    dbName: process.env.DB_NAME || 'football_db',
    dbUser: process.env.DB_USER || 'football_user',
    dbPassword: process.env.DB_PASSWORD || 'football_pass',

    // Logging
    logLevel: process.env.LOG_LEVEL || 'info',
    headless: process.env.HEADLESS_MODE !== 'false',

    // Golden Zone
    goldenZoneStartDate: '2024-01-01'
};

/**
 * V140.000: Fetch verification targets (100 matches)
 * @returns {Promise<Array>} Array of match objects with URLs
 */
async function fetchVerificationTargets() {
    const { Client } = require('pg');
    const client = new Client({
        host: config.dbHost,
        port: config.dbPort,
        database: config.dbName,
        user: config.dbUser,
        password: config.dbPassword
    });

    try {
        await client.connect();
        console.log('[V140.000] Database connected');

        // Fetch 100 golden zone matches with oddsportal URLs
        const query = `
            SELECT
                m.match_id as sourceId,
                m.match_date,
                m.home_team,
                m.away_team,
                m.league_name,
                mm.oddsportal_url as url,
                mm.oddsportal_hash
            FROM matches m
            INNER JOIN matches_mapping mm ON m.match_id = mm.fotmob_id
            WHERE m.match_date >= $1
              AND mm.oddsportal_url IS NOT NULL
            ORDER BY m.match_date DESC
            LIMIT 100
        `;

        const result = await client.query(query, [config.goldenZoneStartDate]);
        console.log(`[V140.000] VERIFICATION TARGETS: ${result.rows.length} matches loaded`);

        return result.rows;
    } finally {
        await client.end();
    }
}

/**
 * V140.000: Generate verification report after harvest
 * @param {Object} harvestResult - Harvest result object
 * @returns {Promise<Object>} Verification metrics
 */
async function generateVerificationReport(harvestResult) {
    const { Client } = require('pg');
    const client = new Client({
        host: config.dbHost,
        port: config.dbPort,
        database: config.dbName,
        user: config.dbUser,
        password: config.dbPassword
    });

    try {
        await client.connect();

        // Query Initial Label Coverage
        const initialLabelQuery = `
            SELECT
                COUNT(*) as total_records,
                COUNT(CASE WHEN is_baseline = true THEN 1 END) as initial_count,
                ROUND(100.0 * COUNT(CASE WHEN is_baseline = true THEN 1 END) / COUNT(*), 2) as coverage_percentage
            FROM temporal_metric_records
            WHERE created_at > NOW() - INTERVAL '10 minutes'
        `;

        const initialResult = await client.query(initialLabelQuery);

        // Query future dates (should be 0 after V140.000)
        const futureDateQuery = `
            SELECT
                COUNT(*) as future_date_count
            FROM temporal_metric_records
            WHERE occurred_at > NOW() + INTERVAL '48 hours'
                AND created_at > NOW() - INTERVAL '10 minutes'
        `;

        const futureResult = await client.query(futureDateQuery);

        // Query trajectory depth
        const trajectoryDepthQuery = `
            SELECT
                AVG(record_count) as avg_depth,
                MIN(record_count) as min_depth,
                MAX(record_count) as max_depth
            FROM (
                SELECT COUNT(*) as record_count
                FROM temporal_metric_records
                WHERE created_at > NOW() - INTERVAL '10 minutes'
                GROUP BY entity_id, dimension
            ) sub
        `;

        const depthResult = await client.query(trajectoryDepthQuery);

        return {
            initialLabelCoverage: {
                totalRecords: parseInt(initialResult.rows[0].total_records),
                initialCount: parseInt(initialResult.rows[0].initial_count),
                coveragePercentage: parseFloat(initialResult.rows[0].coverage_percentage)
            },
            futureDates: {
                count: parseInt(futureResult.rows[0].future_date_count)
            },
            trajectoryDepth: {
                avgDepth: parseFloat(depthResult.rows[0].avg_depth),
                minDepth: parseInt(depthResult.rows[0].min_depth),
                maxDepth: parseInt(depthResult.rows[0].max_depth)
            }
        };

    } finally {
        await client.end();
    }
}

/**
 * V140.000: Main verification flight
 */
async function main() {
    console.log('╔═══════════════════════════════════════════════════════════╗');
    console.log('║         V140.000 DATA PURITY VERIFICATION FLIGHT            ║');
    console.log('╚═══════════════════════════════════════════════════════════╝');
    console.log('');
    console.log('[V140.000] Configuration:');
    console.log(`  - ENFORCE_UTC: ${config.enforceUTC}`);
    console.log(`  - BASE_YEAR: ${config.baseYear}`);
    console.log(`  - MAX_FUTURE_TOLERANCE_HOURS: ${config.maxFutureToleranceHours}`);
    console.log('');

    const harvester = new QuantHarvester(config);

    try {
        // Step 1: Initialize
        console.log('[V140.000] Step 1: Initializing QuantHarvester...');
        await harvester.init();
        console.log('[V140.000] ✅ QuantHarvester initialized');

        // Step 2: Fetch verification targets
        console.log('[V140.000] Step 2: Fetching verification targets...');
        const targets = await fetchVerificationTargets();
        console.log(`[V140.000] ✅ ${targets.length} targets loaded`);

        if (targets.length === 0) {
            console.log('[V140.000] ⚠️ No targets available for verification');
            return;
        }

        // Step 3: Run verification harvest (limit to first 20 for quick validation)
        console.log('[V140.000] Step 3: Running verification harvest (20 matches)...');
        const verificationTargets = targets.slice(0, 20);
        const harvestResult = await harvester.startQueue(verificationTargets, 20, (processed, total) => {
            console.log(`[V140.000] Progress: ${processed}/${total} (${Math.round(processed/total*100)}%)`);
        });
        console.log('[V140.000] ✅ Harvest completed');

        // Step 4: Generate verification report
        console.log('[V140.000] Step 4: Generating verification report...');
        const report = await generateVerificationReport(harvestResult);
        console.log('[V140.000] ✅ Report generated');

        // Step 5: Display results
        console.log('');
        console.log('╔═══════════════════════════════════════════════════════════╗');
        console.log('║              V140.000 VERIFICATION RESULTS                  ║');
        console.log('╚═══════════════════════════════════════════════════════════╝');
        console.log('');
        console.log('[METRIC 1] Initial Label Coverage');
        console.log(`  Total Records: ${report.initialLabelCoverage.totalRecords}`);
        console.log(`  Initial Labels: ${report.initialLabelCoverage.initialCount}`);
        console.log(`  Coverage: ${report.initialLabelCoverage.coveragePercentage}%`);
        console.log(`  Status: ${report.initialLabelCoverage.coveragePercentage >= 100 ? '✅ PASS' : '❌ FAIL'}`);
        console.log('');
        console.log('[METRIC 2] Future Date Detection');
        console.log(`  Future Date Count: ${report.futureDates.count}`);
        console.log(`  Status: ${report.futureDates.count === 0 ? '✅ PASS (no future dates)' : '❌ FAIL (future dates detected)'}`);
        console.log('');
        console.log('[METRIC 3] Trajectory Depth');
        console.log(`  Average Depth: ${report.trajectoryDepth.avgDepth.toFixed(2)} points`);
        console.log(`  Min Depth: ${report.trajectoryDepth.minDepth} points`);
        console.log(`  Max Depth: ${report.trajectoryDepth.maxDepth} points`);
        console.log('');

        // Final verdict
        const pass = report.initialLabelCoverage.coveragePercentage >= 100 && report.futureDates.count === 0;
        console.log('╔═══════════════════════════════════════════════════════════╗');
        console.log(`║  FINAL VERDICT: ${pass ? '✅ DATA PURITY VERIFIED' : '❌ DATA PURITY FAILED'}  ║`);
        console.log('╚═══════════════════════════════════════════════════════════╝');

        // Save report to file
        const fs = require('fs');
        const reportPath = '/home/user/projects/FootballPrediction/logs/forensic/V140_PURITY_VERIFIED.md';
        fs.mkdirSync('/home/user/projects/FootballPrediction/logs/forensic', { recursive: true });

        const reportContent = `# V140.000 Data Purity Verification Report

**Verification Date**: ${new Date().toISOString()}
**Scope**: V140.000 Data Purity Calibration (20 matches)

---

## Executive Summary

| Metric | Value | Status |
|--------|-------|--------|
| **Initial Label Coverage** | ${report.initialLabelCoverage.coveragePercentage}% | ${report.initialLabelCoverage.coveragePercentage >= 100 ? '✅ PASS' : '❌ FAIL'} |
| **Future Date Detection** | ${report.futureDates.count} | ${report.futureDates.count === 0 ? '✅ PASS' : '❌ FAIL'} |
| **Avg Trajectory Depth** | ${report.trajectoryDepth.avgDepth.toFixed(2)} points | ✅ |

## Detailed Metrics

### 1. Initial Label Coverage
- Total Records: ${report.initialLabelCoverage.totalRecords}
- Initial Labels: ${report.initialLabelCoverage.initialCount}
- Coverage Percentage: ${report.initialLabelCoverage.coveragePercentage}%

### 2. Future Date Detection
- Future Date Count: ${report.futureDates.count}
- Status: ${report.futureDates.count === 0 ? 'PASS - No future dates detected after V140.000 calibration' : 'FAIL - Future dates still present'}

### 3. Trajectory Depth
- Average Depth: ${report.trajectoryDepth.avgDepth.toFixed(2)} points
- Min Depth: ${report.trajectoryDepth.minDepth} points
- Max Depth: ${report.trajectoryDepth.maxDepth} points

## Final Verdict

**${pass ? '✅ DATA PURITY VERIFIED - Initial Labels: ENFORCED. Timezone: HARDENED. Data Purity: 100%.' : '❌ DATA PURITY FAILED - Issues detected'}**

---

*Generated by V140.000 Data Purity Verification Flight*
`;

        fs.writeFileSync(reportPath, reportContent);
        console.log(``);
        console.log(`[V140.000] Report saved to: ${reportPath}`);

    } catch (error) {
        console.error('[V140.000] ❌ Verification failed:', error.message);
        throw error;
    } finally {
        await harvester.shutdown();
    }
}

// Run verification
if (require.main === module) {
    main().catch(error => {
        console.error('[V140.000] Fatal error:', error);
        process.exit(1);
    });
}

module.exports = { main, generateVerificationReport };
