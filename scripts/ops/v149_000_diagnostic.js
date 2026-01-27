/**
 * V149.000 Diagnostic - TrajectoryParser Investigation
 * ===================================================
 *
 * Diagnostic task to investigate why TrajectoryParser returns 0 points
 * despite successful modal detection in V148.000.
 *
 * @module ops/v149_000_diagnostic
 * @version V149.000
 * @since 2026-01-28
 * @author Principal Frontend Reverse Engineer
 *
 * V149.000 Objectives:
 * 1. Capture actual modal HTML after successful detection
 * 2. Analyze TrajectoryParser input/output
 * 3. Verify CSS selectors match current DOM structure
 * 4. Generate diagnostic report with findings
 */

'use strict';

const { Pool } = require('pg');
const { performance } = require('perf_hooks');
const fs = require('fs');
const path = require('path');
const { QuantHarvester } = require('../../src/engines/QuantHarvester');
const { TrajectoryParser } = require('../../src/engines/parsers/TrajectoryParser');

// ============================================================================
// CONFIGURATION
// ============================================================================

function loadEnvVar(key) {
    try {
        const envContent = fs.readFileSync(path.join(__dirname, '../../.env'), 'utf8');
        const match = envContent.match(new RegExp(`^${key}=(.+)`, 'm'));
        return match ? match[1].trim() : null;
    } catch (e) {
        return null;
    }
}

const CONFIG = {
    // Database
    dbHost: process.env.DB_HOST || 'localhost',
    dbPort: parseInt(process.env.DB_PORT) || 5432,
    dbName: process.env.DB_NAME || 'football_db',
    dbUser: process.env.DB_USER || 'football_user',
    dbPassword: loadEnvVar('DB_PASSWORD') || process.env.DB_PASSWORD || '',

    // Test scope
    sampleSize: 2,
    targetYearStart: 2025,
    targetYearEnd: 2026,

    // Output
    htmlCaptureDir: '/home/user/projects/FootballPrediction/logs/forensic/v149_modal_html/',
    reportPath: '/home/user/projects/FootballPrediction/logs/forensic/V149_DIAGNOSTIC_REPORT.md',
};

// ============================================================================
// PHASE 1: Sample Targets
// ============================================================================

async function sampleTargets() {
    const pool = new Pool({
        host: CONFIG.dbHost,
        port: CONFIG.dbPort,
        database: CONFIG.dbName,
        user: CONFIG.dbUser,
        password: CONFIG.dbPassword,
    });

    try {
        console.log('[V149.000] 🎯 Sampling targets for diagnostic...');

        const query = `
            SELECT
                m.match_id,
                m.league_name,
                m.season,
                m.match_date,
                m.home_team,
                m.away_team,
                mm.oddsportal_url
            FROM matches m
            INNER JOIN matches_mapping mm
                ON m.match_id = mm.fotmob_id
            WHERE mm.oddsportal_url IS NOT NULL
                AND EXTRACT(YEAR FROM m.match_date) BETWEEN $1 AND $2
                AND (m.l3_extraction_status = 'PENDING' OR m.l3_extraction_status IS NULL)
            ORDER BY RANDOM()
            LIMIT $3
        `;

        const result = await pool.query(query, [
            CONFIG.targetYearStart,
            CONFIG.targetYearEnd,
            CONFIG.sampleSize
        ]);

        console.log(`[V149.000] ✅ Sampled ${result.rows.length} targets`);
        return result.rows;

    } finally {
        await pool.end();
    }
}

// ============================================================================
// PHASE 2: Capture Modal HTML
// ============================================================================

async function captureModalHtml(matches) {
    const results = [];
    const harvester = new QuantHarvester({
        logLevel: 'info',
        forceRemoveOverlays: true,  // V149.000: Enable overlay removal
        scrollIntoViewBeforeHover: true
    });

    // Ensure output directory exists
    if (!fs.existsSync(CONFIG.htmlCaptureDir)) {
        fs.mkdirSync(CONFIG.htmlCaptureDir, { recursive: true });
    }

    try {
        for (let i = 0; i < matches.length; i++) {
            const match = matches[i];
            console.log(`[V149.000] 📸 Capture ${i + 1}/${matches.length}: ${match.home_team} vs ${match.away_team}`);

            // Use internal method to capture modal HTML
            const modalHtml = await harvester._captureModalForDiagnostic(match.oddsportal_url);

            // Save HTML to file
            const filename = `modal_${match.match_id}_${Date.now()}.html`;
            const filepath = path.join(CONFIG.htmlCaptureDir, filename);
            fs.writeFileSync(filepath, modalHtml || '', 'utf8');

            // Analyze with TrajectoryParser
            const parser = new TrajectoryParser();
            const parseResult = parser.extractFullTrajectoryDOM(modalHtml || '');

            results.push({
                match_id: match.match_id,
                home_team: match.home_team,
                away_team: match.away_team,
                modalHtmlLength: modalHtml ? modalHtml.length : 0,
                modalHtmlFile: filename,
                parseResult: {
                    trajectory: parseResult.trajectory || [],
                    valid: parseResult.valid,
                    recordCount: parseResult.recordCount,
                    quality: parseResult.quality,
                    quality_score: parseResult.quality_score,
                    warning: parseResult.warning,
                    error: parseResult.error
                }
            });

            console.log(`[V149.000]   HTML Length: ${modalHtml ? modalHtml.length : 0} chars`);
            console.log(`[V149.000]   Trajectory Points: ${parseResult.recordCount}`);
            console.log(`[V149.000]   Valid: ${parseResult.valid}`);
            console.log('');
        }

    } finally {
        await harvester.shutdown();
    }

    return results;
}

// ============================================================================
// PHASE 3: Analysis
// ============================================================================

async function analyzeResults(captureResults) {
    const analysis = {
        totalTargets: captureResults.length,
        successfulCapture: 0,
        failedCapture: 0,
        successfulParse: 0,
        failedParse: 0,
        avgHtmlLength: 0,
        avgTrajectoryPoints: 0,
        issues: []
    };

    for (const result of captureResults) {
        if (result.modalHtmlLength > 0) {
            analysis.successfulCapture++;
        } else {
            analysis.failedCapture++;
            analysis.issues.push({
                match_id: result.match_id,
                issue: 'No HTML captured'
            });
        }

        if (result.parseResult.valid && result.parseResult.recordCount > 0) {
            analysis.successfulParse++;
        } else {
            analysis.failedParse++;
            if (result.parseResult.error) {
                analysis.issues.push({
                    match_id: result.match_id,
                    issue: 'Parse error: ' + result.parseResult.error
                });
            } else if (result.parseResult.warning) {
                analysis.issues.push({
                    match_id: result.match_id,
                    issue: 'Parse warning: ' + result.parseResult.warning
                });
            } else {
                analysis.issues.push({
                    match_id: result.match_id,
                    issue: `Valid=${result.parseResult.valid}, Points=${result.parseResult.recordCount}`
                });
            }
        }

        analysis.avgHtmlLength += result.modalHtmlLength;
        analysis.avgTrajectoryPoints += result.parseResult.recordCount;
    }

    if (captureResults.length > 0) {
        analysis.avgHtmlLength = Math.round(analysis.avgHtmlLength / captureResults.length);
        analysis.avgTrajectoryPoints = (analysis.avgTrajectoryPoints / captureResults.length).toFixed(2);
    }

    return analysis;
}

// ============================================================================
// PHASE 4: Generate Report
// ============================================================================

function generateDiagnosticReport(captureResults, analysis) {
    const lines = [];

    lines.push('# V149.000 TrajectoryParser Diagnostic Report');
    lines.push('');
    lines.push('**Diagnostic Date**: ' + new Date().toISOString());
    lines.push('**Scope**: ' + captureResults.length + ' Targets (2025-2026)');
    lines.push('**Objective**: Investigate why TrajectoryParser returns 0 points');
    lines.push('');
    lines.push('---');
    lines.push('');
    lines.push('## Executive Summary');
    lines.push('');
    lines.push('| Metric | Value |');
    lines.push('|--------|-------|');
    lines.push('| **Total Targets** | ' + analysis.totalTargets + ' |');
    lines.push('| **Successful HTML Capture** | ' + analysis.successfulCapture + ' |');
    lines.push('| **Failed HTML Capture** | ' + analysis.failedCapture + ' |');
    lines.push('| **Successful Parse** | ' + analysis.successfulParse + ' |');
    lines.push('| **Failed Parse** | ' + analysis.failedParse + ' |');
    lines.push('| **Avg HTML Length** | ' + analysis.avgHtmlLength + ' chars |');
    lines.push('| **Avg Trajectory Points** | ' + analysis.avgTrajectoryPoints + ' |');
    lines.push('');
    lines.push('---');
    lines.push('');
    lines.push('## Detailed Results');
    lines.push('');

    for (const result of captureResults) {
        lines.push('### Match: ' + result.home_team + ' vs ' + result.away_team);
        lines.push('');
        lines.push('- **Match ID**: `' + result.match_id + '`');
        lines.push('- **HTML Captured**: ' + result.modalHtmlLength + ' chars');
        lines.push('- **HTML File**: `' + result.modalHtmlFile + '`');
        lines.push('- **Trajectory Points**: ' + result.parseResult.recordCount);
        lines.push('- **Valid**: ' + (result.parseResult.valid ? 'Yes' : 'No'));
        lines.push('- **Quality**: ' + (result.parseResult.quality || 'N/A'));
        lines.push('- **Quality Score**: ' + (result.parseResult.quality_score || 'N/A'));

        if (result.parseResult.warning) {
            lines.push('- **Warning**: ' + result.parseResult.warning);
        }
        if (result.parseResult.error) {
            lines.push('- **Error**: ' + result.parseResult.error);
        }

        if (result.parseResult.trajectory && result.parseResult.trajectory.length > 0) {
            lines.push('');
            lines.push('**Trajectory Preview** (first 3 points):');
            lines.push('```');
            result.parseResult.trajectory.slice(0, 3).forEach((point, idx) => {
                lines.push((idx + 1) + '. ' + point.time + ' -> ' + point.value + ' (' + point.type + ')');
            });
            lines.push('```');
        }

        lines.push('');
    }

    lines.push('---');
    lines.push('');
    lines.push('## Issues Detected');
    lines.push('');

    if (analysis.issues.length === 0) {
        lines.push('✅ No issues detected. All targets processed successfully.');
    } else {
        analysis.issues.forEach((issue, idx) => {
            lines.push((idx + 1) + '. **Match `' + issue.match_id + '`**: ' + issue.issue);
        });
    }

    lines.push('');
    lines.push('---');
    lines.push('');
    lines.push('## Conclusions');
    lines.push('');

    if (analysis.successfulParse === analysis.totalTargets) {
        lines.push('## ✅ ALL SUCCESSFUL');
        lines.push('- TrajectoryParser working correctly');
        lines.push('- All targets captured and parsed successfully');
    } else if (analysis.successfulParse === 0) {
        lines.push('## ❌ COMPLETE FAILURE');
        lines.push('- TrajectoryParser failed on all targets');
        lines.push('- HTML capture: ' + (analysis.successfulCapture > 0 ? 'Working' : 'FAILED'));
        lines.push('- **RECOMMENDATION**: Review captured HTML files for DOM structure mismatch');
    } else {
        lines.push('## ⚠️ PARTIAL SUCCESS');
        lines.push('- Some targets successful, others failed');
        lines.push('- Success Rate: ' + ((analysis.successfulParse / analysis.totalTargets) * 100).toFixed(0) + '%');
        lines.push('- **RECOMMENDATION**: Compare successful vs failed HTML structures');
    }

    lines.push('');
    lines.push('**Next Steps**:');
    lines.push('1. Review captured HTML files in: `' + CONFIG.htmlCaptureDir + '`');
    lines.push('2. Compare with TrajectoryParser selectors in `src/engines/parsers/TrajectoryParser.js`');
    lines.push('3. Update selectors if DOM structure has changed');
    lines.push('');
    lines.push('---');
    lines.push('');
    lines.push('*Generated by V149.000 Diagnostic Task*');
    lines.push('*Principal Frontend Reverse Engineer*');
    lines.push('*Date: ' + new Date().toISOString() + '*');

    const report = lines.join('\n');
    fs.writeFileSync(CONFIG.reportPath, report, 'utf8');
    console.log('[V149.000] 📄 Report saved to: ' + CONFIG.reportPath);

    return CONFIG.reportPath;
}

// ============================================================================
// PHASE 5: Main Entry Point
// ============================================================================

async function main() {
    console.log('╔══════════════════════════════════════════════════════════════╗');
    console.log('║            V149.000 TRAJECTORY PARSER DIAGNOSTIC                 ║');
    console.log('╠══════════════════════════════════════════════════════════════╣');
    console.log('║  Scope: ' + CONFIG.sampleSize + ' Targets (2025-2026)                                   ║');
    console.log('║  Objective: Investigate 0-point extraction issue                    ║');
    console.log('╚══════════════════════════════════════════════════════════════╝');
    console.log('');

    try {
        // Phase 1: Sample targets
        const matches = await sampleTargets();
        if (matches.length === 0) {
            console.log('[V149.000] ⚠️  No targets found. Exiting.');
            return;
        }

        // Phase 2: Capture modal HTML
        const captureResults = await captureModalHtml(matches);

        // Phase 3: Analyze results
        const analysis = await analyzeResults(captureResults);

        // Phase 4: Generate report
        const reportPath = generateDiagnosticReport(captureResults, analysis);

        console.log('');
        console.log('╔══════════════════════════════════════════════════════════════╗');
        console.log('║                  V149.000 DIAGNOSTIC COMPLETE                    ║');
        console.log('╠══════════════════════════════════════════════════════════════╣');
        console.log('║  Successful Capture: ' + analysis.successfulCapture + '/' + analysis.totalTargets + '                              ║');
        console.log('║  Successful Parse: ' + analysis.successfulParse + '/' + analysis.totalTargets + '                                ║');
        console.log('║  Avg Trajectory Points: ' + analysis.avgTrajectoryPoints + '                              ║');
        console.log('║  Report: ' + reportPath + '                              ║');
        console.log('╚══════════════════════════════════════════════════════════════╝');
        console.log('');
        console.log('[V149.000] 📊 HTML files saved to: ' + CONFIG.htmlCaptureDir);

    } catch (error) {
        console.error('[V149.000] ❌ Fatal error:', error);
        process.exit(1);
    }
}

// Run diagnostic
if (require.main === module) {
    main().catch(error => {
        console.error('[V149.000] Fatal error:', error);
        process.exit(1);
    });
}

module.exports = { sampleTargets, captureModalHtml, analyzeResults, generateDiagnosticReport };
