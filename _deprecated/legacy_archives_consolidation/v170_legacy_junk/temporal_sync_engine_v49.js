#!/usr/bin/env node
/**
 * V49.520 Full-Spectrum Temporal Sync Engine (TestID-Based Recognition)
 * =====================================================================
 *
 * 核心升级：
 *   - V49.520: 基于 data-testid 的节点识别（React/Vue 架构支持）
 *   - 全量三维时间序列提取 (Home/Draw/Away)
 *   - 返还率 (Payout) 自动计算
 *   - 人类行为模拟集成 (随机延迟)
 *   - 批量事务存储优化
 *   - 5 节点并行处理与 applyHumanDelay 完美衔接
 *
 * Usage:
 *   node temporal_sync_engine_v49.js "<TARGET_URL>" "<SOURCE_ID>"
 *
 * @module temporal_sync_engine_v49
 * @author Senior DevOps & Systems Engineer
 * @version V49.520
 * @since 2026-01-24
 */

'use strict';

const { chromium } = require('playwright');
const path = require('path');

// Import modules
const interaction = require('./modules/interaction');
const parserV49 = require('./modules/parser_v49');
// V51.000: 可选使用新模块
let parserV51 = null;
let interactionV51 = null;
try {
    parserV51 = require('./modules/parser_v51');
    interactionV51 = require('./modules/interaction_v51');
} catch (e) {
    // V51 模块不可用，使用 V49
}
const storage = require('./modules/storage');
const logger = require('./modules/logger');
const log = logger.createLogger('temporal_sync_v49');

// ============================================================================
// CONFIGURATION
// ============================================================================

function loadConfig() {
    const configPath = path.join(__dirname, 'config/schema_map.json');

    try {
        const fs = require('fs');
        const configData = fs.readFileSync(configPath, 'utf-8');
        const schemaConfig = JSON.parse(configData);

        return {
            headless: true,
            // V82.500: Timeout increased 66% for better tolerance (180s -> 300s)
            timeout: 300000,

            // Target keys from config
            TARGET_KEYS: schemaConfig.target_providers.primary,

            // Selectors from config
            rowSelector: schemaConfig.selectors.row_identification.formula_a.selector,
            triggerSelector: schemaConfig.selectors.interaction_trigger.formula_b.selector,
            tooltipContainer: schemaConfig.selectors.tooltip_detection.container.selector,

            // V82.500: Enhanced rate limiting (reduced delays for faster processing)
            maxProviders: 5,
            rateLimit: {
                concurrency: 1,
                delay: 3000  // V82.500: Reduced from 5s to 3s
            },

            // V82.500: Human behavior settings (optimized for speed)
            humanBehavior: {
                hoverWaitMin: 1500,  // V82.500: Reduced from 2500ms
                hoverWaitMax: 3500,  // V82.500: Reduced from 5000ms
                interProviderDelayMin: 2500,  // V82.500: Reduced from 4000ms
                interProviderDelayMax: 5000  // V82.500: Reduced from 8000ms
            },

            // V82.500: Degradation strategy - allow partial success
            degradation: {
                enablePartialStorage: true,  // Store available data even if incomplete
                minRequiredRecords: 1,  // At least 1 record required for success
                missingTemporalLabel: 'MISSING_TEMPORAL'  // Tag for degraded data
            }
        };
    } catch (error) {
        log.error(`Failed to load schema_map.json: ${error.message}`);
        throw new Error(`Configuration file not found: ${configPath}`);
    }
}

const CONFIG = loadConfig();

// ============================================================================
// STATE MANAGEMENT
// ============================================================================

let currentBrowser = null;
let currentDbClient = null;

let extractionStats = {
    url: '',
    sourceId: '',
    timestamp: '',
    rowsScanned: 0,
    rowsMatched: 0,
    nodesAttempted: 0,  // V49.211: Number of target key nodes attempted
    rowsProcessed: 0,
    tooltipsDetected: 0,
    temporalPointsExtracted: 0,
    databasePersisted: 0,
    errors: []
};

// ============================================================================
// LOGGING
// ============================================================================

function logError(error) {
    const errorLog = {
        timestamp: new Date().toISOString(),
        type: error.name || 'UnknownError',
        message: error.message || 'Unknown error',
        context: error.context || {}
    };

    extractionStats.errors.push(errorLog);
    console.error(`[V49.000] [${errorLog.type}] [${errorLog.timestamp}] ${errorLog.message}`);
}

function logInfo(msg) {
    console.log(`[V49.000] ${msg}`);
}

// ============================================================================
// GRACEFUL SHUTDOWN
// ============================================================================

async function gracefulShutdown(signal) {
    logInfo(`Received ${signal}, initiating graceful shutdown...`);

    const cleanupTasks = [];

    if (currentBrowser) {
        cleanupTasks.push(
            (async () => {
                try {
                    await currentBrowser.close();
                    logInfo('Browser closed successfully');
                } catch (error) {
                    logInfo(`Error closing browser: ${error.message}`);
                }
            })()
        );
    }

    if (currentDbClient) {
        cleanupTasks.push(
            (async () => {
                try {
                    await currentDbClient.end();
                    logInfo('Database connection closed successfully');
                } catch (error) {
                    logInfo(`Error closing database: ${error.message}`);
                }
            })()
        );
    }

    await Promise.all(cleanupTasks);
    process.exit(0);
}

process.on('SIGINT', () => gracefulShutdown('SIGINT'));
process.on('SIGTERM', () => gracefulShutdown('SIGTERM'));

// ============================================================================
// MAIN EXTRACTION ORCHESTRATOR
// ============================================================================

/**
 * V50.200: Main extraction with API-first + UI-fallback hybrid strategy
 */
async function runFullSpectrumExtraction(url, sourceId) {
    extractionStats.url = url;
    extractionStats.sourceId = sourceId;
    extractionStats.timestamp = new Date().toISOString();

    try {
        logInfo('=== V50.200 Hybrid Temporal Sync Engine (API-First + UI-Fallback) ===');
        logInfo(`Target: ${sourceId}`);
        logInfo('');

        // Step 1: Database connection
        logInfo('[1/7] Establishing database connection...');
        currentDbClient = await storage.createConnection();
        const entityId = await storage.getOrCreateEntity(currentDbClient, sourceId, url);
        logInfo('Entity ID resolved');
        logInfo('');

        // Step 2: Launch browser
        logInfo('[2/7] Launching browser...');
        currentBrowser = await chromium.launch({
            headless: CONFIG.headless,
            args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-gpu'],
        });

        const context = await currentBrowser.newContext({
            viewport: { width: 1920, height: 1080 },
            userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        });

        const page = await context.newPage();
        page.setDefaultTimeout(CONFIG.timeout);

        // Step 3: V50.200 Setup API interceptor (BEFORE page load)
        logInfo('[3/7] === V50.200 API INTERCEPTOR SETUP ===');
        const capturedApiResponses = await interaction.setupApiInterceptor(page);
        logInfo('API interceptor registered');
        logInfo('');

        // Step 4: Navigate to page
        logInfo('[4/7] Loading target page...');
        await page.goto(url, { waitUntil: 'networkidle', timeout: CONFIG.timeout });
        await page.waitForTimeout(3000);  // Wait for API responses
        logInfo('Page loaded');
        logInfo('');

        // Step 5: V50.200 Try API-first extraction
        logInfo('[5/7] === V50.200 API-FIRST EXTRACTION ===');

        let apiDataExtracted = false;
        let allMovementData = [];

        if (interaction.hasApiData(capturedApiResponses)) {
            logInfo(`API responses captured: ${capturedApiResponses.length}`);

            // Process all captured API responses
            for (const apiResponse of capturedApiResponses) {
                try {
                    logInfo(`  Processing API response from ${apiResponse.url.substring(0, 60)}...`);

                    const parsedRecords = parserV51
                        ? parserV51.parseRawJsonResponse(apiResponse.json, sourceId)
                        : parserV49.parseRawJsonResponse(apiResponse.json, sourceId);

                    if (parsedRecords.length > 0) {
                        allMovementData.push(...parsedRecords);
                        extractionStats.temporalPointsExtracted += parsedRecords.length;
                        logInfo(`  Extracted: ${parsedRecords.length} temporal points (API)`);
                        apiDataExtracted = true;
                    }
                } catch (error) {
                    logInfo(`  API parsing failed: ${error.message}`);
                }
            }

            if (apiDataExtracted) {
                logInfo('API-FIRST: Data successfully extracted from API responses');
            }
        } else {
            logInfo('API-FIRST: No API responses captured, will use UI fallback');
        }

        logInfo('');

        // Step 6: V50.200 UI-Fallback (only if API extraction failed)
        if (!apiDataExtracted) {
            logInfo('[6/7] === UI-FALLBACK EXTRACTION ===');
            logInfo('Falling back to UI hover extraction...');

            // Node identification (V49.520 TestID-based)
            const matchedNodes = await interaction.identifyNodesByTestId(page);

            extractionStats.rowsScanned = matchedNodes.length;
            extractionStats.rowsMatched = matchedNodes.filter(n => n.matched).length;

            logInfo(`Nodes scanned: ${matchedNodes.length}`);
            logInfo(`Nodes matched: ${extractionStats.rowsMatched}`);

            if (matchedNodes.length === 0) {
                logInfo('No matching nodes found for UI extraction.');
            } else {
                // Process matched nodes (V49.520 Index-Based Selection)
                let processedCount = 0;

                // V49.520: Process first 5 nodes by index (stable selection strategy)
                const maxNodesToProcess = Math.min(CONFIG.maxProviders, matchedNodes.length);

                for (let i = 0; i < maxNodesToProcess; i++) {
                    extractionStats.nodesAttempted = i + 1;

                    try {
                        const node = matchedNodes[i];
                        const nodeLabel = `Node_${node.index}`;

                        logInfo(`Processing [${extractionStats.nodesAttempted}/${maxNodesToProcess}]: ${nodeLabel}`);
                        logInfo(`  Metric containers: ${node.metricCount}`);

                        // V49.520: Locate trigger using TestID priority strategy
                        const trigger = await interaction.locateTriggerByTestId(
                            node.element,
                            CONFIG.triggerSelector  // Fallback selector
                        );

                        if (!trigger) {
                            logInfo('  SKIP: Trigger not found');
                            continue;
                        }

                        // V49.000: Use enhanced hover with human behavior
                        const hoverResult = await interaction.smartHoverWithBehavior(trigger, page, {
                            nodeIndex: node.index,
                            maxRetries: 3
                        });

                        if (!hoverResult.success) {
                            logInfo(`  SKIP: ${hoverResult.error || 'Hover failed'}`);
                            continue;
                        }

                        extractionStats.tooltipsDetected++;
                        logInfo('  SUCCESS: Tooltip detected');

                        // Capture tooltip HTML (V53.000: use outerHTML to include wrapper)
                        const tooltipContainer = await page.$(CONFIG.tooltipContainer);
                        if (!tooltipContainer) {
                            logInfo('  SKIP: Tooltip container not found');
                            continue;
                        }

                        // V53.000: Use outerHTML to ensure we capture the full tooltip structure
                        const rawHTML = await tooltipContainer.evaluate(el => el.outerHTML);

                        // V51.000: Use enhanced parser with contract validation (if available)
                        const movementData = parserV51
                            ? parserV51.parseFullTooltipHTMLWithContract(rawHTML, nodeLabel)
                            : parserV49.parseFullTooltipHTML(rawHTML, nodeLabel);

                        if (movementData.length > 0) {
                            extractionStats.temporalPointsExtracted += movementData.length;

                            logInfo(`  Extracted: ${movementData.length} temporal points (UI)`);
                            logInfo(`  Dimensions: Home/Draw/Away + Payout`);

                            // Aggregate data for batch storage
                            allMovementData.push(...movementData);
                        }

                        extractionStats.rowsProcessed++;
                        processedCount++;

                        // V49.520: Apply human delay between nodes (for nodes with index >= 2)
                        if (processedCount >= 2 && processedCount < maxNodesToProcess) {
                            await interaction.applyHumanDelay(
                                page,
                                CONFIG.humanBehavior.interProviderDelayMin,
                                CONFIG.humanBehavior.interProviderDelayMax
                            );
                        }

                    } catch (error) {
                        logError({ ...error, context: { nodeIndex: extractionStats.nodesAttempted } });
                        console.warn(`[V50.200] Node [${extractionStats.nodesAttempted}] SKIP: ${error.message}`);
                    }
                }

                // V50.200: Log UI fallback summary
                logInfo(`UI-Fallback Summary: ${extractionStats.nodesAttempted} nodes attempted, ${processedCount} successfully processed`);
            }
        } else {
            logInfo('[6/7] === UI-FALLBACK SKIPPED ===');
            logInfo('API extraction succeeded, UI fallback not needed');
        }

        // Step 7: Batch storage (V50.200 optimized)
        logInfo('');
        logInfo('[7/7] === BATCH STORAGE ===');

        if (allMovementData.length > 0) {
            const dbResult = await storage.upsertFullTemporalRecords(
                currentDbClient,
                entityId,
                allMovementData
            );

            extractionStats.databasePersisted = dbResult.total_records;

            logInfo(`Database: [${dbResult.total_records}] records persisted`);
            logInfo(`  Breakdown: ${dbResult.inserted} inserted, ${dbResult.updated} updated`);
            logInfo(`  Temporal points: ${dbResult.temporal_points}`);
        }

        // Cleanup
        await currentBrowser.close();
        currentBrowser = null;

        await currentDbClient.end();
        currentDbClient = null;

        // Final summary
        logInfo('');
        logInfo('=== V50.200 EXTRACTION COMPLETE ===');
        logInfo(`Extraction mode: ${apiDataExtracted ? 'API-FIRST' : 'UI-FALLBACK'}`);
        logInfo(`Temporal points extracted: ${extractionStats.temporalPointsExtracted}`);
        logInfo(`Database persisted: ${extractionStats.databasePersisted}`);
        logInfo(`Errors: ${extractionStats.errors.length}`);

        return {
            success: true,
            stats: extractionStats,
            mode: apiDataExtracted ? 'API-FIRST' : 'UI-FALLBACK'
        };

    } catch (error) {
        logError(error);

        // Cleanup on error
        if (currentBrowser) {
            try { await currentBrowser.close(); } catch (e) {}
        }
        if (currentDbClient) {
            try { await currentDbClient.end(); } catch (e) {}
        }

        return {
            success: false,
            error: error.message,
            stats: extractionStats
        };
    }
}

// ============================================================================
// CLI ENTRY POINT
// ============================================================================

if (require.main === module) {
    const args = process.argv.slice(2);

    const url = args[0];
    const sourceId = args[1] || 'unknown';

    if (!url) {
        console.error('Usage:');
        console.error('  node temporal_sync_engine_v49.js "<TARGET_URL>" "<SOURCE_ID>"');
        console.error('');
        console.error('Example:');
        console.error('  node temporal_sync_engine_v49.js "https://www.oddsportal.com/..." "4507128"');
        process.exit(1);
    }

    runFullSpectrumExtraction(url, sourceId)
        .then(result => {
            if (result.success) {
                console.log('');
                console.log('============================================================');
                console.log('[V50.200] FINAL AUDIT');
                console.log('============================================================');
                console.log(`[V50.200] Extraction Mode: ${result.mode || 'UNKNOWN'}`);
                console.log(`[V50.200] Temporal points extracted: ${result.stats.temporalPointsExtracted}`);
                console.log(`[V50.200] Database persisted: ${result.stats.databasePersisted}`);
                console.log(`[V50.200] Errors: ${result.stats.errors.length}`);
                console.log('============================================================');
                console.log('');
                console.log('[V50.200] Hybrid Harvesting Complete (API-First + UI-Fallback).');
                console.log('');
                process.exit(0);
            } else {
                console.error('[V50.200] Extraction failed:', result.error);
                process.exit(1);
            }
        })
        .catch(error => {
            console.error('[V50.200] Fatal error:', error.message);
            process.exit(1);
        });
}

module.exports = { runFullSpectrumExtraction };
