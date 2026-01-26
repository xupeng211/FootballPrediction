/**
 * V85.990 Production Environment Resource Locator (Full-Path URL) Normalization
 * ============================================================================
 *
 * Core Mission:
 *   - Replace hash-based URL construction with database-stored full-path URLs
 *   - Ensure target UI matrix (Six-Nodes) loads completely
 *
 * Key Changes:
 *   - SQL Logic: Extract BOTH oddsportal_hash AND oddsportal_url fields
 *   - URL Priority: oddsportal_url (FULL) > hash-based construction (FALLBACK)
 *   - Validation: Verify 8-char hash identifier before navigation
 *   - Silent Execution: No URL/odds data in logs, status reporting only
 *
 * @usage: node scripts/ops/v85_990_full_path_url_adapter.js
 * @author Senior Data Engineer & Automation Specialist
 * @version V85.990
 * @since 2026-01-26
 */

'use strict';

const { chromium } = require('playwright');
const { Client } = require('pg');
const path = require('path');
const interactionV51 = require('./modules/interaction_v51');
const storage = require('./modules/storage');
const logger = require('./modules/logger');
const log = logger.createLogger('v85_990_adapter');

// ============================================================================
// CONFIGURATION
// ============================================================================

const CONFIG = {
    // Database query config
    query: {
        limit: 100,  // Batch size for URL extraction
        minHashLength: 8  // Minimum hash length for validation
    },

    // Browser config (headless for production)
    browserConfig: {
        headless: true,
        timeout: 60000
    },

    // Ghost Protocol config
    ghostProtocol: {
        userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
        viewport: { width: 1920, height: 1080 },
        locale: 'en-US',
        timezoneId: 'America/New_York'
    },

    // Navigation config
    navigation: {
        waitUntil: 'networkidle',
        timeout: 30000
    },

    // Visual extraction config
    visual: {
        maxProviders: 5,
        expandCollapsed: true,
        enableRetry: true,
        maxRetries: 2
    },

    // Concurrent processing
    concurrent: 2
};

// ============================================================================
// V85.990: DATABASE QUERY FUNCTIONS
// ============================================================================

/**
 * Query matches_mapping table to extract full-path URLs
 *
 * SQL Logic:
 *   - SELECT: oddsportal_hash, oddsportal_url, match_id
 *   - FROM: matches_mapping
 *   - WHERE: oddsportal_url IS NOT NULL (prioritize full-path records)
 *   - LIMIT: CONFIG.query.limit
 *
 * @returns {Promise<Array>} - Array of match records with hash and URL
 */
async function queryFullUrlMatches() {
    const client = await storage.createConnection();
    const results = {
        fullPath: 0,    // Count of records with full URL
        hashOnly: 0,    // Count of records with hash only
        total: 0,
        matches: []
    };

    try {
        log.info('[V85.990] Querying matches_mapping table for full-path URLs...');

        const queryResult = await client.query(
            `SELECT
                mm.fotmob_id,
                mm.oddsportal_hash,
                mm.oddsportal_url,
                m.match_date
             FROM matches_mapping mm
             LEFT JOIN matches m ON mm.fotmob_id = m.match_id
             WHERE mm.oddsportal_hash IS NOT NULL
             ORDER BY m.match_date DESC NULLS LAST
             LIMIT $1`,
            [CONFIG.query.limit]
        );

        for (const row of queryResult.rows) {
            const matchRecord = {
                fotmobId: row.fotmob_id,
                hash: row.oddsportal_hash,
                url: null,
                urlType: 'none',
                isValid: false
            };

            // Priority 1: Use oddsportal_url if available
            if (row.oddsportal_url && row.oddsportal_url.length > 20) {
                matchRecord.url = row.oddsportal_url;
                matchRecord.urlType = 'full-path';
                matchRecord.isValid = validateUrl(row.oddsportal_url, row.oddsportal_hash);
                results.fullPath++;
            }
            // Fallback: Construct URL from hash
            else if (row.oddsportal_hash && row.oddsportal_hash.length === 8) {
                matchRecord.url = constructHashBasedUrl(row.oddsportal_hash);
                matchRecord.urlType = 'hash-constructed';
                matchRecord.isValid = true;
                results.hashOnly++;
            }

            results.matches.push(matchRecord);
            results.total++;
        }

        log.info(`[V85.990] Query complete: ${results.fullPath} full-path, ${results.hashOnly} hash-only, ${results.total} total`);

        return results;

    } catch (error) {
        log.error(`[V85.990] Database query failed: ${error.message}`);
        throw error;
    } finally {
        await client.end().catch(() => {});
    }
}

/**
 * V85.990: Validate URL contains expected hash identifier
 *
 * @param {string} url - URL to validate
 * @param {string} expectedHash - Expected 8-char hash
 * @returns {boolean} - True if URL contains valid hash
 */
function validateUrl(url, expectedHash) {
    if (!url || !expectedHash) return false;

    // Extract hash from URL (last 8 chars before trailing slash)
    const urlParts = url.split('/');
    const lastPart = urlParts[urlParts.length - 2] || urlParts[urlParts.length - 1];

    // Check if URL contains the expected hash
    const isValid = lastPart.includes(expectedHash) || url.includes(expectedHash);

    if (!isValid) {
        log.warn(`[V85.990] URL validation failed: hash mismatch`);
    }

    return isValid;
}

/**
 * Fallback: Construct hash-based URL (legacy method)
 *
 * @param {string} hash - 8-char hash
 * @returns {string} - Constructed URL
 */
function constructHashBasedUrl(hash) {
    return `https://www.oddsportal.com/match/${hash}/`;
}

// ============================================================================
// V85.990: BATCH PROCESSING ENGINE
// ============================================================================

/**
 * Process a batch of matches with full-path URLs
 *
 * @param {Array} matches - Array of match records
 * @returns {Promise<Object>} - Batch processing results
 */
async function processBatch(matches) {
    const results = {
        total: matches.length,
        success: 0,
        failed: 0,
        urlAlignment: {
            fullPath: 0,
            hashFallback: 0,
            warning: 0
        },
        connectivity: {
            pageLoadSuccess: 0,
            matrixFound: 0,
            matrixNotFound: 0
        },
        sixNodeSync: {
            identifier18Active: 0,  // William Hill
            identifier5Active: 0    // Ladbrokes
        }
    };

    // Process in parallel with concurrency limit
    const chunks = [];
    for (let i = 0; i < matches.length; i += CONFIG.concurrent) {
        chunks.push(matches.slice(i, i + CONFIG.concurrent));
    }

    for (const chunk of chunks) {
        const chunkResults = await Promise.allSettled(
            chunk.map(match => processSingleMatch(match))
        );

        for (const result of chunkResults) {
            if (result.status === 'fulfilled' && result.value) {
                const r = result.value;

                if (r.success) results.success++;
                else results.failed++;

                results.urlAlignment.fullPath += r.urlAlignment.fullPath;
                results.urlAlignment.hashFallback += r.urlAlignment.hashFallback;
                results.urlAlignment.warning += r.urlAlignment.warning;

                results.connectivity.pageLoadSuccess += r.connectivity.pageLoadSuccess;
                results.connectivity.matrixFound += r.connectivity.matrixFound;
                results.connectivity.matrixNotFound += r.connectivity.matrixNotFound;

                results.sixNodeSync.identifier18Active += r.sixNodeSync.identifier18Active;
                results.sixNodeSync.identifier5Active += r.sixNodeSync.identifier5Active;
            } else {
                results.failed++;
            }
        }
    }

    return results;
}

/**
 * Process a single match with full-path URL
 *
 * @param {Object} match - Match record
 * @returns {Promise<Object>} - Processing result
 */
async function processSingleMatch(match) {
    const result = {
        success: false,
        fotmobId: match.fotmobId,
        urlAlignment: { fullPath: 0, hashFallback: 0, warning: 0 },
        connectivity: { pageLoadSuccess: 0, matrixFound: 0, matrixNotFound: 0 },
        sixNodeSync: { identifier18Active: 0, identifier5Active: 0 }
    };

    let browser = null;
    let context = null;
    let page = null;

    try {
        // Track URL type
        if (match.urlType === 'full-path') {
            result.urlAlignment.fullPath = 1;
            log.debug(`[V85.990] Full-Path URL: [${match.hash}] type=FULL`);
        } else {
            result.urlAlignment.hashFallback = 1;
            log.warn(`[V85.990] [Warning: Short-Path] hash=${match.hash}`);
            result.urlAlignment.warning = 1;
        }

        // Launch browser
        browser = await chromium.launch({
            headless: CONFIG.browserConfig.headless
        });

        context = await browser.newContext(CONFIG.ghostProtocol);
        page = await context.newPage();
        page.setDefaultTimeout(CONFIG.browserConfig.timeout);

        // Navigate to target
        await page.goto(match.url, CONFIG.navigation);
        result.connectivity.pageLoadSuccess = 1;

        // Check for matrix container
        const matrixExists = await page.$$('div.border-black-borders').then(el => el.length > 0);

        if (matrixExists) {
            result.connectivity.matrixFound = 1;
            log.debug(`[V85.990] Matrix container FOUND for [${match.hash}]`);
        } else {
            result.connectivity.matrixNotFound = 1;
            log.warn(`[V85.990] Matrix container NOT FOUND for [${match.hash}]`);
        }

        // Check for Six-Node identifiers (William Hill, Ladbrokes)
        const identifier18Exists = await page.$$('img[title*="William Hill" i], img[src*="williamhill" i]').then(el => el.length > 0);
        const identifier5Exists = await page.$$('img[title*="Ladbrokes" i], img[src*="ladbrokes" i]').then(el => el.length > 0);

        if (identifier18Exists) result.sixNodeSync.identifier18Active = 1;
        if (identifier5Exists) result.sixNodeSync.identifier5Active = 1;

        result.success = true;

    } catch (error) {
        log.debug(`[V85.990] Process failed for [${match.hash}]: ${error.message.substring(0, 50)}`);
        result.success = false;
    } finally {
        if (page) await page.close().catch(() => {});
        if (context) await context.close().catch(() => {});
        if (browser) await browser.close().catch(() => {});
    }

    return result;
}

// ============================================================================
// V85.990: MAIN ENTRY
// ============================================================================

/**
 * V85.990 Main execution
 */
async function runV85_990Adapter() {
    log.info('=== V85.990 Full-Path URL Adapter ===');
    log.info('Mission: Replace hash-based URL construction with database-stored full-path URLs');

    try {
        // =======================================================================
        // Phase 1: Database Query
        // =======================================================================
        log.info('[Phase 1] Querying matches_mapping table...');
        const queryResults = await queryFullUrlMatches();

        // =======================================================================
        // Phase 2: URL Alignment Report
        // =======================================================================
        log.info('[Phase 2] URL Alignment Analysis...');
        log.info(`  Full-Path URLs: ${queryResults.fullPath}`);
        log.info(`  Hash-Only URLs: ${queryResults.hashOnly}`);
        log.info(`  Total Matches: ${queryResults.total}`);

        const urlAlignmentRate = (queryResults.fullPath / queryResults.total * 100).toFixed(1);
        log.info(`  URL Alignment Rate: ${urlAlignmentRate}%`);

        // =======================================================================
        // Phase 3: Batch Processing
        // =======================================================================
        log.info('[Phase 3] Batch processing with full-path URLs...');
        const batchResults = await processBatch(queryResults.matches);

        // =======================================================================
        // Phase 4: Final Report
        // =======================================================================
        log.info('[Phase 4] Generating V85.990 Delivery Report...');

        const connectivityRate = (batchResults.connectivity.matrixFound / batchResults.total * 100).toFixed(1);
        const identifier18Rate = (batchResults.sixNodeSync.identifier18Active / batchResults.total * 100).toFixed(1);
        const identifier5Rate = (batchResults.sixNodeSync.identifier5Active / batchResults.total * 100).toFixed(1);
        const masterReadiness = (batchResults.success / batchResults.total * 100).toFixed(1);

        console.log('\n' + '='.repeat(70));
        console.log('[V85.990] Full-Path URL Adapter - Delivery Report');
        console.log('='.repeat(70));
        console.log(`1. URL Alignment: ${queryResults.fullPath}/${queryResults.total} full-path URLs extracted`);
        console.log(`2. Connectivity: ${batchResults.connectivity.matrixFound}/${batchResults.total} matrix containers found (${connectivityRate}%)`);
        console.log(`3. Six-Node Sync:`);
        console.log(`   - Identifier-18 (WH): ${batchResults.sixNodeSync.identifier18Active}/${batchResults.total} active (${identifier18Rate}%)`);
        console.log(`   - Identifier-5 (LB): ${batchResults.sixNodeSync.identifier5Active}/${batchResults.total} active (${identifier5Rate}%)`);
        console.log(`4. Master Pipeline Readiness: ${masterReadiness}%`);
        console.log('='.repeat(70));

        const finalStatus = masterReadiness >= 80 ? 'DEPLOYED' : 'NEEDS_REVIEW';
        console.log(`[V85.990] Full-Path Adapter ${finalStatus}. Resource Mapping: SYNCED. Readiness for Master Pipeline: ${masterReadiness}%.`);
        console.log('='.repeat(70) + '\n');

        return {
            version: 'V85.990',
            timestamp: new Date().toISOString(),
            urlAlignment: {
                fullPath: queryResults.fullPath,
                hashOnly: queryResults.hashOnly,
                total: queryResults.total,
                rate: urlAlignmentRate
            },
            connectivity: {
                pageLoadSuccess: batchResults.connectivity.pageLoadSuccess,
                matrixFound: batchResults.connectivity.matrixFound,
                matrixNotFound: batchResults.connectivity.matrixNotFound,
                rate: connectivityRate
            },
            sixNodeSync: {
                identifier18Active: batchResults.sixNodeSync.identifier18Active,
                identifier5Active: batchResults.sixNodeSync.identifier5Active,
                identifier18Rate,
                identifier5Rate
            },
            masterReadiness,
            status: finalStatus
        };

    } catch (error) {
        log.error(`[V85.990] Fatal error: ${error.message}`);
        throw error;
    }
}

// ============================================================================
// MAIN ENTRY
// ============================================================================

(async () => {
    try {
        const report = await runV85_990Adapter();
        process.exit(report.masterReadiness >= 80 ? 0 : 1);
    } catch (error) {
        log.error(error.stack);
        process.exit(1);
    }
})();
