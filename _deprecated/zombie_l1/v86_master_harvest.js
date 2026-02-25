/**
 * V86.000 Production Environment Full-Stack UI Matrix Harvest Pipeline (Final Master)
 * =============================================================================
 *
 * Core Mission:
 *   - Backfill 10,000+ PENDING L3 temporal records from database
 *   - Multi-worker proxy mode for high-throughput harvesting
 *   - Integration with V85.980+ interaction engine (Six Tigers positioning + Force Click)
 *
 * Architecture:
 *   - Task Sharding: Extract PENDING hashes + oddsportal_url from matches_mapping
 *   - Parallel Strategy: CONCURRENT_WORKERS = 6 (configurable)
 *   - Proxy Rotation: Round-robin proxy assignment per worker context
 *   - Breakpoint Resume: Skip completed (temporal_count > 0) records
 *   - Auto-Escape: Mark FAILED_SKIPPED after 3 consecutive failures
 *   - Silent Storage: [Hash: OK] or [Hash: Error] only in logs
 *
 * @usage: node scripts/ops/v86_master_harvest.js
 * @env: CONCURRENT_WORKERS=6 PROXY_LIST=http://proxy1:port,http://proxy2:port
 * @author Senior Infrastructure & Automation Architect
 * @version V86.000
 * @since 2026-01-26
 */

'use strict';

const { chromium } = require('playwright');
const { Client } = require('pg');
const path = require('path');
const interactionV51 = require('./modules/interaction_v51');
const parserV51 = require('./modules/parser_v51');
const storage = require('./modules/storage');
const logger = require('./modules/logger');
const log = logger.createLogger('v86_master');

// ============================================================================
// CONFIGURATION
// ============================================================================

const CONFIG = {
    // 并发配置 (可环境变量覆盖)
    concurrentWorkers: parseInt(process.env.CONCURRENT_WORKERS) || 6,

    // 代理配置 (支持环境变量)
    proxyList: parseProxyList(process.env.PROXY_LIST),

    // 数据库查询配置
    query: {
        batchSize: 500,  // 每批查询数量
        maxTotal: null,   // null = 无限制
        skipCompleted: true,  // 断点续传：跳过已完成记录
        minHashLength: 8
    },

    // 失败逃逸配置
    failureThreshold: 3,  // 连续 3 次失败后标记为 FAILED_SKIPPED
    failureBackoffMs: 5000,  // 失败后退避时间

    // 浏览器配置 (headless 生产模式)
    browserConfig: {
        headless: true,
        timeout: 60000
    },

    // Ghost Protocol 反爬检测
    ghostProtocol: {
        userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
        viewport: { width: 1920, height: 1080 },
        locale: 'en-US',
        timezoneId: 'America/New_York'
    },

    // 导航配置
    navigation: {
        waitUntil: 'networkidle',
        timeout: 30000
    },

    // 视觉取证配置 (V85.980+)
    visual: {
        maxProviders: 6,  // Six Tigers - 完整覆盖
        expandCollapsed: true,
        enableRetry: true,
        maxRetries: 2
    },

    // 性能监控配置
    monitoring: {
        progressInterval: 100,  // 每 100 场输出进度
        reportInterval: 1000,   // 每 1000 场输出详细报告
        startTime: Date.now()
    }
};

/**
 * 解析代理列表环境变量
 * @param {string} proxyEnv - 逗号分隔的代理列表
 * @returns {Array<string>} - 代理 URL 数组
 */
function parseProxyList(proxyEnv) {
    if (!proxyEnv) return [];
    return proxyEnv.split(',').map(p => p.trim()).filter(p => p.length > 0);
}

// ============================================================================
// V86.000: DATABASE QUERY & TASK SHARDING
// ============================================================================

/**
 * Query PENDING matches from matches_mapping table
 *
 * SQL Logic:
 *   - SELECT: fotmob_id, oddsportal_hash, oddsportal_url
 *   - WHERE: oddsportal_hash IS NOT NULL
 *   - LEFT JOIN: Check temporal_metric_records count for resume
 *   - ORDER BY: Random distribution for parallel processing
 *
 * @param {number} limit - Query limit
 * @param {boolean} skipCompleted - Skip records with temporal_count > 0
 * @returns {Promise<Array>} - Array of task records
 */
async function queryPendingTasks(limit, skipCompleted = true) {
    const client = await storage.createConnection();
    const tasks = [];

    try {
        log.info('[V86.000] Querying PENDING tasks from matches_mapping...');

        let query = `
            SELECT
                mm.fotmob_id,
                mm.oddsportal_hash,
                mm.oddsportal_url,
                COALESCE(COUNT(tmr.entity_id), 0) as temporal_count
            FROM matches_mapping mm
            LEFT JOIN entities_mapping em ON em.source_id = mm.oddsportal_hash
                AND em.source_system = 'oddsportal'
            LEFT JOIN temporal_metric_records tmr ON tmr.entity_id = em.entity_id
            WHERE mm.oddsportal_hash IS NOT NULL
                AND mm.oddsportal_hash != ''
                AND LENGTH(mm.oddsportal_hash) >= $1
        `;

        const params = [CONFIG.query.minHashLength];

        // 断点续传：跳过已完成记录
        if (skipCompleted) {
            query += ` AND (tmr.entity_id IS NULL OR COUNT(tmr.entity_id) = 0)`;
        }

        query += `
            GROUP BY mm.fotmob_id, mm.oddsportal_hash, mm.oddsportal_url
            ORDER BY RANDOM()
            LIMIT $2
        `;

        params.push(limit);

        const result = await client.query(query, params);

        for (const row of result.rows) {
            const task = {
                fotmobId: row.fotmob_id,
                hash: row.oddsportal_hash,
                url: null,
                urlType: 'none',
                failureCount: 0,
                status: 'PENDING',
                temporalCount: parseInt(row.temporal_count)
            };

            // 优先使用全路径 URL
            if (row.oddsportal_url && row.oddsportal_url.length > 20) {
                task.url = row.oddsportal_url;
                task.urlType = 'full-path';
            } else if (row.oddsportal_hash) {
                task.url = `https://www.oddsportal.com/match/${row.oddsportal_hash}/`;
                task.urlType = 'hash-constructed';
            }

            tasks.push(task);
        }

        log.info(`[V86.000] Retrieved ${tasks.length} PENDING tasks`);
        log.info(`  - Full-path URLs: ${tasks.filter(t => t.urlType === 'full-path').length}`);
        log.info(`  - Hash-constructed: ${tasks.filter(t => t.urlType === 'hash-constructed').length}`);

        return tasks;

    } catch (error) {
        log.error(`[V86.000] Database query failed: ${error.message}`);
        throw error;
    } finally {
        await client.end().catch(() => {});
    }
}

/**
 * Update task status in database
 *
 * @param {string} fotmobId - FotMob match ID
 * @param {string} status - Task status (SUCCESS, FAILED_SKIPPED)
 * @param {number} temporalCount - Number of temporal records stored
 */
async function updateTaskStatus(fotmobId, status, temporalCount = 0) {
    const client = await storage.createConnection();

    try {
        // Update matches_mapping harvest_status
        await client.query(
            `UPDATE matches_mapping
             SET harvest_status = $1,
                 last_harvested_at = NOW(),
                 temporal_count = $2
             WHERE fotmob_id = $3`,
            [status, temporalCount, fotmobId]
        );

    } catch (error) {
        log.debug(`[V86.000] Status update failed for ${fotmobId}: ${error.message}`);
    } finally {
        await client.end().catch(() => {});
    }
}

// ============================================================================
// V86.000: SINGLE WORKER EXECUTION ENGINE
// ============================================================================

/**
 * Process a single task (one match)
 *
 * @param {Object} task - Task record
 * @param {string|null} proxy - Optional proxy URL
 * @returns {Promise<Object>} - Processing result
 */
async function processSingleTask(task, proxy = null) {
    const result = {
        hash: task.hash,
        success: false,
        temporalCount: 0,
        providersCaptured: 0,
        error: null,
        status: task.status
    };

    let browser = null;
    let context = null;
    let page = null;

    try {
        // =======================================================================
        // Step 1: Launch browser with proxy (if provided)
        // =======================================================================
        const browserOptions = {
            headless: CONFIG.browserConfig.headless
        };

        // Add proxy configuration if available
        const contextOptions = {
            ...CONFIG.ghostProtocol
        };

        if (proxy) {
            contextOptions.proxy = { server: proxy };
        }

        browser = await chromium.launch(browserOptions);
        context = await browser.newContext(contextOptions);
        page = await context.newPage();
        page.setDefaultTimeout(CONFIG.browserConfig.timeout);

        // =======================================================================
        // Step 2: Navigate to target URL (V85.990 Full-Path Adapter)
        // =======================================================================
        await page.goto(task.url, CONFIG.navigation);

        // =======================================================================
        // Step 3: V85.980 Patch A - Expand collapsed content
        // =======================================================================
        await interactionV51.expandAllCollapsedContent(page);

        // =======================================================================
        // Step 4: V85.980+ Visual Extraction - Six Tigers Capture
        // =======================================================================
        const visualResult = await interactionV51.captureOddsMovementVisually(page, {
            maxProviders: CONFIG.visual.maxProviders,
            expandCollapsed: false,  // Already done
            enableRetry: CONFIG.visual.enableRetry,
            maxRetries: CONFIG.visual.maxRetries
        });

        if (!visualResult.success || visualResult.results.length === 0) {
            throw new Error('Visual extraction failed - no providers captured');
        }

        // =======================================================================
        // Step 5: Parse modal HTML using parser_v51
        // =======================================================================
        const allMovementData = [];

        for (const visualItem of visualResult.results) {
            const movementData = parserV51.parseModalHtml(
                visualItem.html,
                visualItem.providerName
            );
            allMovementData.push(...movementData);
        }

        if (allMovementData.length === 0) {
            throw new Error('No temporal data extracted from HTML');
        }

        // =======================================================================
        // Step 6: Store to database using storage.js
        // =======================================================================
        const dbClient = await storage.createConnection();

        try {
            // Get or create entity
            const entityId = await storage.getOrCreateEntity(
                dbClient,
                task.hash,
                task.url,
                'match'
            );

            // Store temporal records (V49.000 full-spectrum)
            const storeResult = await storage.upsertFullTemporalRecords(
                dbClient,
                entityId,
                allMovementData
            );

            result.temporalCount = storeResult.total_records || allMovementData.length;
            result.providersCaptured = visualResult.results.length;
            result.success = true;

        } finally {
            await dbClient.end().catch(() => {});
        }

    } catch (error) {
        result.error = error.message.substring(0, 100);
        result.success = false;
    } finally {
        if (page) await page.close().catch(() => {});
        if (context) await context.close().catch(() => {});
        if (browser) await browser.close().catch(() => {});
    }

    return result;
}

// ============================================================================
// V86.000: PARALLEL WORKER POOL
// ============================================================================

/**
 * Process a batch of tasks with concurrent workers
 *
 * @param {Array} tasks - Array of task records
 * @returns {Promise<Object>} - Batch processing results
 */
async function processBatchWithWorkers(tasks) {
    const results = {
        total: tasks.length,
        success: 0,
        failed: 0,
        skipped: 0,
        temporalRecords: 0,
        providersCaptured: 0,
        failedTasks: []
    };

    // Process in chunks based on CONCURRENT_WORKERS
    const chunkSize = CONFIG.concurrentWorkers;

    for (let i = 0; i < tasks.length; i += chunkSize) {
        const chunk = tasks.slice(i, i + chunkSize);

        // Get proxy for this worker (round-robin)
        const workerResults = await Promise.allSettled(
            chunk.map((task, idx) => {
                const proxy = CONFIG.proxyList.length > 0
                    ? CONFIG.proxyList[(i + idx) % CONFIG.proxyList.length]
                    : null;

                return processSingleTask(task, proxy);
            })
        );

        // Process results
        for (let j = 0; j < workerResults.length; j++) {
            const task = chunk[j];
            const settledResult = workerResults[j];

            if (settledResult.status === 'fulfilled' && settledResult.value.success) {
                const r = settledResult.value;

                results.success++;
                results.temporalRecords += r.temporalCount;
                results.providersCaptured += r.providersCaptured;

                // Update task status
                await updateTaskStatus(task.fotmobId, 'SUCCESS', r.temporalCount);

                // Silent log: [Hash: OK]
                log.info(`[${task.hash.substring(0, 6)}]: OK (${r.temporalCount} records, ${r.providersCaptured} providers)`);

            } else {
                // Failure handling
                const errorMsg = settledResult.status === 'rejected'
                    ? settledResult.reason.message
                    : settledResult.value.error;

                task.failureCount++;

                // Auto-escape: Mark as FAILED_SKIPPED after threshold
                if (task.failureCount >= CONFIG.failureThreshold) {
                    results.skipped++;
                    task.status = 'FAILED_SKIPPED';
                    await updateTaskStatus(task.fotmobId, 'FAILED_SKIPPED', 0);
                    results.failedTasks.push({ hash: task.hash, reason: 'Max retries exceeded' });
                } else {
                    results.failed++;
                }

                // Silent log: [Hash: Error]
                log.warn(`[${task.hash.substring(0, 6)}]: Error (${task.failureCount}/${CONFIG.failureThreshold})`);
            }
        }

        // Progress monitoring
        const processed = i + chunkSize;
        if (processed % CONFIG.monitoring.progressInterval === 0 || processed >= tasks.length) {
            const elapsedMs = Date.now() - CONFIG.monitoring.startTime;
            const elapsedMin = elapsedMs / 60000;
            const speed = elapsedMin > 0 ? (processed / elapsedMin).toFixed(1) : 0;

            log.info(`[Progress] Processed: ${processed}/${results.total} | Success: ${results.success} | Speed: ${speed} matches/min`);
        }
    }

    return results;
}

// ============================================================================
// V86.000: MAIN EXECUTION
// ============================================================================

/**
 * V86.000 Main execution
 */
async function runV86_MasterPipeline() {
    log.info('=== V86.000 Master Pipeline - Production Harvest ===');
    log.info(`Configuration:`);
    log.info(`  - Concurrent Workers: ${CONFIG.concurrentWorkers}`);
    log.info(`  - Proxy List: ${CONFIG.proxyList.length} proxies`);
    log.info(`  - Failure Threshold: ${CONFIG.failureThreshold} attempts`);
    log.info(`  - Visual Extraction: V85.980+ Six Tigers`);
    log.info(`  - Skip Completed: ${CONFIG.query.skipCompleted}`);

    try {
        // =======================================================================
        // Phase 1: Task Sharding - Query PENDING tasks
        // =======================================================================
        log.info('[Phase 1] Task Sharding...');
        const tasks = await queryPendingTasks(
            CONFIG.query.batchSize,
            CONFIG.query.skipCompleted
        );

        if (tasks.length === 0) {
            log.info('[Phase 1] No PENDING tasks found. Pipeline complete.');
            return { success: true, message: 'No tasks to process' };
        }

        // =======================================================================
        // Phase 2: Batch Processing with Workers
        // =======================================================================
        log.info('[Phase 2] Batch Processing...');
        const batchResults = await processBatchWithWorkers(tasks);

        // =======================================================================
        // Phase 3: Final Report
        // =======================================================================
        const elapsedMs = Date.now() - CONFIG.monitoring.startTime;
        const elapsedMin = elapsedMs / 60000;
        const avgSpeed = elapsedMin > 0 ? (batchResults.total / elapsedMin).toFixed(1) : 0;

        console.log('\n' + '='.repeat(70));
        console.log('[V86.000] Master Pipeline - Final Report');
        console.log('='.repeat(70));
        console.log(`Total Tasks: ${batchResults.total}`);
        console.log(`Success: ${batchResults.success} (${(batchResults.success / batchResults.total * 100).toFixed(1)}%)`);
        console.log(`Failed: ${batchResults.failed}`);
        console.log(`Skipped: ${batchResults.skipped}`);
        console.log(`Temporal Records: ${batchResults.temporalRecords}`);
        console.log(`Providers Captured: ${batchResults.providersCaptured}`);
        console.log(`Elapsed Time: ${elapsedMin.toFixed(2)} min`);
        console.log(`Average Speed: ${avgSpeed} matches/min`);

        if (batchResults.failedTasks.length > 0) {
            console.log(`\nFailed Tasks (${batchResults.failedTasks.length}):`);
            batchResults.failedTasks.slice(0, 10).forEach(t => {
                console.log(`  - ${t.hash}: ${t.reason}`);
            });
            if (batchResults.failedTasks.length > 10) {
                console.log(`  ... and ${batchResults.failedTasks.length - 10} more`);
            }
        }

        console.log('='.repeat(70) + '\n');

        return {
            version: 'V86.000',
            timestamp: new Date().toISOString(),
            config: {
                concurrentWorkers: CONFIG.concurrentWorkers,
                proxyCount: CONFIG.proxyList.length,
                failureThreshold: CONFIG.failureThreshold
            },
            results: batchResults,
            performance: {
                elapsedMs,
                elapsedMin,
                avgSpeed
            }
        };

    } catch (error) {
        log.error(`[V86.000] Fatal error: ${error.message}`);
        throw error;
    }
}

// ============================================================================
// MAIN ENTRY
// ============================================================================

(async () => {
    try {
        const report = await runV86_MasterPipeline();

        if (report.results && report.results.success > 0) {
            log.success('[V86.000] Pipeline completed successfully');
            process.exit(0);
        } else {
            log.warn('[V86.000] Pipeline completed with no successes');
            process.exit(1);
        }
    } catch (error) {
        log.error(error.stack);
        process.exit(1);
    }
})();
