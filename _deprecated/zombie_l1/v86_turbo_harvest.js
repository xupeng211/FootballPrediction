/**
 * V86.120 Turbo Harvest Pipeline - Matrix Port Mapping Edition
 * ============================================================
 *
 * Core Mission:
 *   - Utilize Ryzen 9900X (24GB RAM) with 20 concurrent workers
 *   - Matrix Port Mapping: Worker i → Port 7891+i (1:1 binding)
 *   - Lifecycle restart: Reclaim memory every 50 tasks
 *   - Resource Guard: Intercept all non-essential resources
 *
 * V86.120 Changes:
 *   - [FIXED] SQL aggregate function error in queryPendingTasks
 *   - Replaced COUNT() in WHERE clause with NOT EXISTS pattern
 *   - Improved query performance and stability
 *
 * Architecture:
 *   - Port Range: 7891-7910 (20 independent public IPs via WSL2 gateway)
 *   - Worker Assignment: Worker[0]→7891, Worker[1]→7992, ..., Worker[19]→7910
 *   - Resource Blocking: image/font/media/stylesheet (minimal UI only)
 *   - Lifecycle: MAX_TASKS_PER_WORKER=50, then browser restart
 *   - Zombie Guard: on('close') monitoring + process cleanup
 *
 * @usage: node scripts/ops/v86_turbo_harvest.js
 * @author High-Performance Systems Architect
 * @version V86.120
 * @since 2026-01-26
 */

'use strict';

const { chromium } = require('playwright');
const { Client } = require('pg');
const fs = require('fs');
const path = require('path');
const { EventEmitter } = require('events');

const interactionV51 = require('./modules/interaction_v51');
const parserV51 = require('./modules/parser_v51');
const storage = require('./modules/storage');
const logger = require('./modules/logger');
const log = logger.createLogger('v86_turbo');

// ============================================================================
// CONFIGURATION - V86.120 MATRIX EDITION
// ============================================================================

const CONFIG = {
    // Turbo并发配置 (固定20工兵)
    concurrentWorkers: 20,

    // 金丝雀测试配置 (V86.120)
    canaryTest: {
        enabled: true,           // 启用金丝雀测试
        testTasks: 1,            // 测试任务数
        timeoutMs: 120000,       // 单场测试超时 (2分钟)
        requireSuccess: true     // 要求测试成功才继续
    },

    // 矩阵端口映射 (WSL2 Gateway → 22 Public IPs)
    matrixPortMapping: {
        gatewayHost: '172.25.16.1',
        startPort: 7891,
        endPort: 7910,
        totalPorts: 20
    },

    // 生命周期管理
    lifecycle: {
        maxTasksPerWorker: 50,  // 每处理50个任务重启浏览器
        workerRestartDelayMs: 2000,  // 重启延迟
        forceRestartMemoryMB: 1024,  // 内存超过1GB强制重启
        memoryCheckIntervalMs: 30000  // 每30秒检查一次
    },

    // 数据库查询配置
    query: {
        batchSize: 1000,
        maxTotal: null,
        skipCompleted: true,
        minHashLength: 8
    },

    // 资源拦截 (Ghost Mode)
    resourceGuard: {
        enabled: true,
        blockImages: true,
        blockFonts: true,
        blockMedia: true,
        blockStylesheets: true,  // 激进模式：拦截所有样式表
        allowedDomains: [
            'oddsportal.com'
        ],
        // 必需的资源模式
        allowedPatterns: [
            /oddsportal\.com.*\.css/i,  // 只允许目标站点CSS
            /oddsportal\.com.*\.js/i     // 必需的JS
        ]
    },

    // 僵尸进程监控
    zombieGuard: {
        enabled: true,
        timeoutMs: 120000,
        checkIntervalMs: 10000,
        maxRestarts: 3,
        enableCleanup: true
    },

    // 断点记录配置
    checkpoint: {
        filePath: path.join(__dirname, 'harvest_checkpoint.json'),
        syncIntervalMs: 5000,
        autoSave: true
    },

    // 浏览器配置 (极限优化)
    browserConfig: {
        headless: true,
        timeout: 90000
    },

    // Ghost Protocol 反爬检测
    ghostProtocol: {
        userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
        viewport: { width: 1920, height: 1080 },
        locale: 'en-US',
        timezoneId: 'America/New_York',
        ignoreDefaultArgs: ['--enable-automation'],
        args: [
            '--disable-dev-shm-usage',
            '--disable-gpu',
            '--disable-setuid-sandbox',
            '--no-sandbox',
            '--disable-web-security',
            '--disable-features=IsolateOrigins,site-per-process',
            '--disable-blink-features=AutomationControlled',
            '--disable-infobars',
            '--disable-extensions',
            '--disable-default-apps',
            '--no-first-run',
            '--disable-sync',
            '--metrics-recording-only',
            '--mute-audio',
            '--no-default-browser-check'
        ]
    },

    // 导航配置
    navigation: {
        waitUntil: 'domcontentloaded',
        timeout: 30000
    },

    // 视觉取证配置
    visual: {
        maxProviders: 6,
        expandCollapsed: true,
        enableRetry: true,
        maxRetries: 2
    },

    // 性能监控配置
    monitoring: {
        progressInterval: 50,
        reportInterval: 500,
        startTime: Date.now()
    }
};

// ============================================================================
// V86.120: MATRIX PORT MANAGER
// ============================================================================

/**
 * Get proxy server URL for worker index
 * @param {number} workerIndex - Worker index (0-19)
 * @returns {string} - Proxy server URL
 */
function getProxyServerForWorker(workerIndex) {
    const port = CONFIG.matrixPortMapping.startPort + workerIndex;
    return `http://${CONFIG.matrixPortMapping.gatewayHost}:${port}`;
}

/**
 * Generate matrix port mapping table
 * @returns {Array} - Array of worker configurations
 */
function generateMatrixMapping() {
    const mapping = [];

    for (let i = 0; i < CONFIG.concurrentWorkers; i++) {
        const port = CONFIG.matrixPortMapping.startPort + i;
        const proxyServer = getProxyServerForWorker(i);

        mapping.push({
            workerId: i,
            workerName: `W-${i.toString().padStart(2, '0')}`,
            port: port,
            proxyServer: proxyServer,
            gatewayHost: CONFIG.matrixPortMapping.gatewayHost,
            status: 'idle',
            currentTask: null,
            tasksProcessed: 0,
            tasksUntilRestart: CONFIG.lifecycle.maxTasksPerWorker,
            lastActivity: Date.now(),
            restartCount: 0,
            browser: null,
            context: null,
            page: null,
            memoryUsage: 0,
            isAlive: true
        });
    }

    return mapping;
}

// ============================================================================
// V86.120: RESOURCE GUARD (GHOST MODE)
// ============================================================================

/**
 * Setup resource interception for memory optimization
 * @param {import('@playwright/test').Page} page - Playwright page
 * @param {number} workerId - Worker ID for logging
 */
async function setupResourceGuard(page, workerId) {
    if (!CONFIG.resourceGuard.enabled) return;

    const workerName = `W-${workerId.toString().padStart(2, '0')}`;

    await page.route('**/*', (route) => {
        const request = route.request();
        const resourceType = request.resourceType();
        const url = request.url();

        // Check if resource is allowed
        let isAllowed = false;

        // Allow documents (HTML)
        if (resourceType === 'document') {
            isAllowed = true;
        }

        // Allow XHR/fetch (API calls)
        if (resourceType === 'websocket' || resourceType === 'xhr' || resourceType === 'fetch') {
            isAllowed = true;
        }

        // Check allowed patterns
        for (const pattern of CONFIG.resourceGuard.allowedPatterns) {
            if (pattern.test(url)) {
                isAllowed = true;
                break;
            }
        }

        // Block by resource type
        if (!isAllowed) {
            if (resourceType === 'image' && CONFIG.resourceGuard.blockImages) {
                route.abort();
                return;
            }
            if (resourceType === 'font' && CONFIG.resourceGuard.blockFonts) {
                route.abort();
                return;
            }
            if (resourceType === 'media' && CONFIG.resourceGuard.blockMedia) {
                route.abort();
                return;
            }
            if (resourceType === 'stylesheet' && CONFIG.resourceGuard.blockStylesheets) {
                // 只允许必需的CSS，其他全部拦截
                if (!CONFIG.resourceGuard.allowedPatterns.some(p => p.test(url))) {
                    route.abort();
                    return;
                }
            }
        }

        route.continue();
    });

    log.debug(`[${workerName}] Resource Guard: Image/Font/Media/Stylesheet blocking enabled`);
}

// ============================================================================
// V86.120: WORKER LIFECYCLE MANAGER
// ============================================================================

/**
 * Worker lifecycle manager class
 */
class WorkerLifecycleManager extends EventEmitter {
    constructor(workerConfig) {
        super();
        this.config = workerConfig;
        this.isRestarting = false;
        this.memoryCheckInterval = null;
    }

    /**
     * Create browser instance for worker
     */
    async createBrowser() {
        const { workerId, proxyServer } = this.config;
        const workerName = this.config.workerName;

        try {
            const browser = await chromium.launch({
                headless: CONFIG.browserConfig.headless,
                args: CONFIG.ghostProtocol.args
            });

            const contextOptions = {
                ...CONFIG.ghostProtocol,
                proxy: {
                    server: proxyServer
                }
            };

            const context = await browser.newContext(contextOptions);
            const page = await context.newPage();
            page.setDefaultTimeout(CONFIG.browserConfig.timeout);

            // Setup resource guard
            await setupResourceGuard(page, workerId);

            // Setup close handler for zombie detection
            browser.on('disconnected', () => {
                log.warn(`[${workerName}] Browser disconnected unexpectedly`);
                this.emit('disconnected');
            });

            context.on('close', () => {
                log.debug(`[${workerName}] Context closed`);
            });

            page.on('close', () => {
                log.debug(`[${workerName}] Page closed`);
            });

            // Start memory monitoring
            this.startMemoryMonitoring();

            this.config.browser = browser;
            this.config.context = context;
            this.config.page = page;
            this.config.isAlive = true;

            log.info(`[${workerName}] Browser launched on port ${this.config.port}`);

            return { browser, context, page };

        } catch (error) {
            log.error(`[${workerName}] Failed to create browser: ${error.message}`);
            this.config.isAlive = false;
            throw error;
        }
    }

    /**
     * Destroy browser instance
     */
    async destroyBrowser() {
        const workerName = this.config.workerName;

        try {
            this.stopMemoryMonitoring();

            if (this.config.page) {
                await this.config.page.close().catch(() => {});
                this.config.page = null;
            }

            if (this.config.context) {
                await this.config.context.close().catch(() => {});
                this.config.context = null;
            }

            if (this.config.browser) {
                await this.config.browser.close().catch(() => {});
                this.config.browser = null;
            }

            this.config.isAlive = false;

            log.debug(`[${workerName}] Browser destroyed, memory released`);

        } catch (error) {
            log.warn(`[${workerName}] Error during browser cleanup: ${error.message}`);
        }
    }

    /**
     * Restart browser (lifecycle management)
     */
    async restartBrowser() {
        const workerName = this.config.workerName;

        if (this.isRestarting) {
            log.warn(`[${workerName}] Already restarting, skipping`);
            return;
        }

        this.isRestarting = true;
        log.info(`[${workerName}] Restarting browser (tasks processed: ${this.config.tasksProcessed})`);

        await this.destroyBrowser();

        // Wait before restart
        await new Promise(resolve => setTimeout(resolve, CONFIG.lifecycle.workerRestartDelayMs));

        await this.createBrowser();

        this.config.tasksUntilRestart = CONFIG.lifecycle.maxTasksPerWorker;
        this.config.restartCount++;
        this.isRestarting = false;

        log.info(`[${workerName}] Browser restarted successfully`);
    }

    /**
     * Check if restart is needed
     */
    shouldRestart() {
        return this.config.tasksUntilRestart <= 0 ||
               this.config.memoryUsage > CONFIG.lifecycle.forceRestartMemoryMB;
    }

    /**
     * Record task completion
     */
    recordTask() {
        this.config.tasksProcessed++;
        this.config.tasksUntilRestart--;
        this.config.lastActivity = Date.now();
    }

    /**
     * Start memory monitoring
     */
    startMemoryMonitoring() {
        this.memoryCheckInterval = setInterval(() => {
            if (this.config.browser && this.config.browser.isConnected()) {
                // Estimate memory usage (cannot get actual in Playwright)
                // Use task count as proxy
                this.config.memoryUsage = Math.floor(
                    this.config.tasksProcessed * 0.5  // ~0.5MB per task estimate
                );

                if (this.config.memoryUsage > CONFIG.lifecycle.forceRestartMemoryMB) {
                    log.warn(`[${this.config.workerName}] Memory threshold exceeded: ${this.config.memoryUsage}MB`);
                    this.emit('memory-exceeded');
                }
            }
        }, CONFIG.lifecycle.memoryCheckIntervalMs);
    }

    /**
     * Stop memory monitoring
     */
    stopMemoryMonitoring() {
        if (this.memoryCheckInterval) {
            clearInterval(this.memoryCheckInterval);
            this.memoryCheckInterval = null;
        }
    }

    /**
     * Cleanup
     */
    async cleanup() {
        this.stopMemoryMonitoring();
        await this.destroyBrowser();
    }
}

// ============================================================================
// V86.120: CHECKPOINT SYSTEM
// ============================================================================

/**
 * Load checkpoint from file
 */
function loadCheckpoint() {
    try {
        if (fs.existsSync(CONFIG.checkpoint.filePath)) {
            const data = fs.readFileSync(CONFIG.checkpoint.filePath, 'utf-8');
            return JSON.parse(data);
        }
        return {
            version: 'V86.120',
            startTime: new Date().toISOString(),
            processed: {},
            skipped: [],
            failed: [],
            stats: {
                total: 0,
                success: 0,
                failed: 0,
                skipped: 0
            }
        };
    } catch (error) {
        log.warn(`[V86.120] Failed to load checkpoint: ${error.message}`);
        return null;
    }
}

/**
 * Save checkpoint to file
 */
function saveCheckpoint(checkpoint) {
    try {
        checkpoint.lastUpdate = new Date().toISOString();
        fs.writeFileSync(
            CONFIG.checkpoint.filePath,
            JSON.stringify(checkpoint, null, 2)
        );
    } catch (error) {
        log.warn(`[V86.120] Failed to save checkpoint: ${error.message}`);
    }
}

/**
 * Update checkpoint with task result
 */
function updateCheckpoint(checkpoint, hash, status, result = null) {
    checkpoint.processed[hash] = {
        status: status,
        timestamp: new Date().toISOString(),
        result: result
    };

    checkpoint.stats.total++;

    if (status === 'SUCCESS') {
        checkpoint.stats.success++;
    } else if (status === 'FAILED_SKIPPED') {
        checkpoint.stats.skipped++;
    } else {
        checkpoint.stats.failed++;
    }

    if (CONFIG.checkpoint.autoSave && checkpoint.stats.total % 20 === 0) {
        saveCheckpoint(checkpoint);
    }
}

// ============================================================================
// V86.120: TASK PROCESSING ENGINE
// ============================================================================

/**
 * Query PENDING tasks from database
 */
async function queryPendingTasks(limit, skipCompleted = true) {
    const client = await storage.createConnection();
    const tasks = [];

    try {
        let query = `
            SELECT
                mm.fotmob_id,
                mm.oddsportal_hash,
                mm.oddsportal_url
            FROM matches_mapping mm
        `;

        const params = [CONFIG.query.minHashLength];

        if (skipCompleted) {
            // V86.120: 使用 NOT EXISTS 替代聚合函数，避免 WHERE 子句错误
            query += `
            WHERE mm.oddsportal_hash IS NOT NULL
                AND mm.oddsportal_hash != ''
                AND LENGTH(mm.oddsportal_hash) >= $1
                AND NOT EXISTS (
                    SELECT 1
                    FROM entities_mapping em
                    INNER JOIN temporal_metric_records tmr ON tmr.entity_id = em.entity_id
                    WHERE em.source_id = mm.oddsportal_hash
                        AND em.source_system = 'oddsportal'
                    LIMIT 1
                )
            `;
        } else {
            query += `
            WHERE mm.oddsportal_hash IS NOT NULL
                AND mm.oddsportal_hash != ''
                AND LENGTH(mm.oddsportal_hash) >= $1
            `;
        }

        query += `
            ORDER BY RANDOM()
            LIMIT $2
        `;

        params.push(limit);

        const result = await client.query(query, params);

        for (const row of result.rows) {
            tasks.push({
                fotmobId: row.fotmob_id,
                hash: row.oddsportal_hash,
                url: row.oddsportal_url && row.oddsportal_url.length > 20
                    ? row.oddsportal_url
                    : `https://www.oddsportal.com/match/${row.oddsportal_hash}/`,
                urlType: row.oddsportal_url && row.oddsportal_url.length > 20 ? 'full-path' : 'hash-constructed',
                failureCount: 0,
                status: 'PENDING',
                temporalCount: 0
            });
        }

        log.info(`[V86.120] Retrieved ${tasks.length} PENDING tasks`);

        return tasks;

    } finally {
        await client.end().catch(() => {});
    }
}

/**
 * Process a single task with worker
 * @param {Object} task - Task record
 * @param {WorkerLifecycleManager} workerManager - Worker lifecycle manager
 * @param {Object} checkpoint - Checkpoint data
 */
async function processTaskWithWorker(task, workerManager, checkpoint) {
    const workerName = workerManager.config.workerName;
    const hashPrefix = task.hash.substring(0, 6);

    const result = {
        hash: task.hash,
        success: false,
        temporalCount: 0,
        providersCaptured: 0,
        error: null
    };

    workerManager.config.status = 'busy';
    workerManager.config.currentTask = task;
    workerManager.config.lastActivity = Date.now();

    try {
        // Ensure browser is alive
        if (!workerManager.config.browser || !workerManager.config.isAlive) {
            await workerManager.createBrowser();
        }

        const { page } = workerManager.config;

        // Navigate to target
        await page.goto(task.url, CONFIG.navigation);

        // Expand collapsed content
        await interactionV51.expandAllCollapsedContent(page);

        // Visual extraction
        const visualResult = await interactionV51.captureOddsMovementVisually(page, {
            maxProviders: CONFIG.visual.maxProviders,
            expandCollapsed: false,
            enableRetry: CONFIG.visual.enableRetry,
            maxRetries: CONFIG.visual.maxRetries
        });

        if (!visualResult.success || visualResult.results.length === 0) {
            throw new Error('Visual extraction failed');
        }

        // Parse HTML
        const allMovementData = [];
        for (const visualItem of visualResult.results) {
            const movementData = parserV51.parseModalHtml(
                visualItem.html,
                visualItem.providerName
            );
            allMovementData.push(...movementData);
        }

        if (allMovementData.length === 0) {
            throw new Error('No temporal data extracted');
        }

        // Store to database
        const dbClient = await storage.createConnection();
        try {
            const entityId = await storage.getOrCreateEntity(
                dbClient,
                task.hash,
                task.url,
                'match'
            );

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

        workerManager.config.status = 'idle';
        workerManager.config.currentTask = null;
        workerManager.recordTask();

    } catch (error) {
        result.error = error.message;
        result.success = false;

        workerManager.config.status = 'idle';
        workerManager.config.currentTask = null;
        workerManager.recordTask();
    }

    // Update checkpoint
    const status = result.success ? 'SUCCESS' : 'FAILED';
    updateCheckpoint(checkpoint, task.hash, status, result);

    // Output format: [W-i] Processing Hash [X] | Port [789x] | Status [OK/FAIL]
    const statusStr = result.success ? 'OK' : 'FAIL';
    console.log(`[${workerName}] Processing Hash [${hashPrefix}] | Port [${workerManager.config.port}] | Status [${statusStr}]`);

    return result;
}

// ============================================================================
// V86.120: CANARY TEST (金丝雀测试)
// ============================================================================

/**
 * Run canary test before full deployment
 * @param {WorkerLifecycleManager} canaryWorker - Worker-00 for testing
 * @param {Array} tasks - Available tasks
 * @param {Object} checkpoint - Checkpoint data
 * @returns {Promise<boolean>} - True if canary passed
 */
async function runCanaryTest(canaryWorker, tasks, checkpoint) {
    if (!CONFIG.canaryTest.enabled || tasks.length === 0) {
        log.info('[V86.120] Canary test: DISABLED or no tasks available');
        return true;
    }

    const workerName = canaryWorker.config.workerName;
    const testTask = tasks[0];

    log.info('='.repeat(70));
    log.info('[V86.120] CANARY TEST - Starting Pre-Flight Check');
    log.info('='.repeat(70));
    log.info(`Worker: ${workerName} (Port ${canaryWorker.config.port})`);
    log.info(`Target: ${testTask.hash.substring(0, 6)}... | URL: ${testTask.urlType}`);
    log.info('='.repeat(70));

    const startTime = Date.now();

    try {
        // Create timeout promise
        const timeoutPromise = new Promise((_, reject) => {
            setTimeout(() => reject(new Error('Canary test timeout')), CONFIG.canaryTest.timeoutMs);
        });

        // Run canary task
        const resultPromise = processTaskWithWorker(testTask, canaryWorker, checkpoint);
        const result = await Promise.race([resultPromise, timeoutPromise]);

        const elapsedMs = Date.now() - startTime;

        if (result.success) {
            log.info('='.repeat(70));
            log.info(`[V86.120] CANARY TEST - PASSED ✓`);
            log.info(`  Status: OK`);
            log.info(`  Temporal Records: ${result.temporalCount}`);
            log.info(`  Providers Captured: ${result.providersCaptured}`);
            log.info(`  Elapsed: ${(elapsedMs / 1000).toFixed(2)}s`);
            log.info('='.repeat(70));
            log.info('[V86.120] Deploying remaining 19 workers...');
            return true;
        } else {
            log.error('='.repeat(70));
            log.error(`[V86.120] CANARY TEST - FAILED ✗`);
            log.error(`  Error: ${result.error}`);
            log.error(`  Elapsed: ${(elapsedMs / 1000).toFixed(2)}s`);
            log.error('='.repeat(70));

            if (CONFIG.canaryTest.requireSuccess) {
                throw new Error('Canary test failed - aborting deployment');
            }
            return false;
        }

    } catch (error) {
        const elapsedMs = Date.now() - startTime;
        log.error('='.repeat(70));
        log.error(`[V86.120] CANARY TEST - FATAL ERROR ✗`);
        log.error(`  Error: ${error.message}`);
        log.error(`  Elapsed: ${(elapsedMs / 1000).toFixed(2)}s`);
        log.error('='.repeat(70));
        throw error;
    }
}

// ============================================================================
// V86.120: TURBO MAIN EXECUTION
// ============================================================================

/**
 * V86.120 Main execution
 */
async function runV86_TurboPipeline() {
    log.info('=== V86.120 Turbo Pipeline - Matrix Port Mapping Edition ===');
    log.info(`System Configuration:`);
    log.info(`  - Concurrent Workers: ${CONFIG.concurrentWorkers} (Fixed)`);
    log.info(`  - Gateway: ${CONFIG.matrixPortMapping.gatewayHost}`);
    log.info(`  - Port Range: ${CONFIG.matrixPortMapping.startPort}-${CONFIG.matrixPortMapping.endPort}`);
    log.info(`  - Resource Guard: ${CONFIG.resourceGuard.enabled ? 'ENABLED' : 'DISABLED'}`);
    log.info(`  - Lifecycle Restart: ${CONFIG.lifecycle.maxTasksPerWorker} tasks/worker`);
    log.info(`  - Zombie Guard: ${CONFIG.zombieGuard.enabled ? 'ENABLED' : 'DISABLED'}`);
    log.info(`  - Canary Test: ${CONFIG.canaryTest.enabled ? 'ENABLED' : 'DISABLED'}`);

    // Generate matrix mapping
    const matrixMapping = generateMatrixMapping();
    log.info(`[V86.120] Matrix Mapping Generated:`);
    for (const w of matrixMapping) {
        log.info(`  ${w.workerName} → Port ${w.port} (${w.proxyServer})`);
    }

    // Create worker lifecycle managers
    const workerManagers = matrixMapping.map(
        config => new WorkerLifecycleManager(config)
    );

    // Load checkpoint
    const checkpoint = loadCheckpoint();

    // Start zombie monitor
    let zombieMonitorInterval = null;
    if (CONFIG.zombieGuard.enabled) {
        zombieMonitorInterval = setInterval(() => {
            const now = Date.now();
            for (const wm of workerManagers) {
                if (wm.config.status === 'busy') {
                    const idleTime = now - wm.config.lastActivity;
                    if (idleTime > CONFIG.zombieGuard.timeoutMs) {
                        log.warn(`[${wm.config.workerName}] Zombie detected, restarting...`);
                        wm.restartBrowser().catch(err => {
                            log.error(`[${wm.config.workerName}] Restart failed: ${err.message}`);
                        });
                    }
                }
            }
        }, CONFIG.zombieGuard.checkIntervalMs);
    }

    try {
        // Query tasks
        log.info('[V86.120] Loading tasks...');
        const tasks = await queryPendingTasks(
            CONFIG.query.batchSize,
            CONFIG.query.skipCompleted
        );

        if (tasks.length === 0) {
            log.info('[V86.120] No PENDING tasks found');
            return { success: true, message: 'No tasks' };
        }

        // Filter out already processed tasks
        let pendingTasks = tasks.filter(t => !checkpoint.processed[t.hash]);
        log.info(`[V86.120] ${pendingTasks.length} tasks to process (${tasks.length - pendingTasks.length} in checkpoint)`);

        const results = {
            total: pendingTasks.length,
            success: 0,
            failed: 0,
            skipped: 0,
            temporalRecords: 0,
            providersCaptured: 0
        };

        // V86.120: Canary Test - Initialize Worker-00 first
        if (CONFIG.canaryTest.enabled && pendingTasks.length > 0) {
            const canaryWorker = workerManagers[0];

            log.info('[V86.120] Initializing Worker-00 for canary test...');
            await canaryWorker.createBrowser();

            // Log proxy connection establishment
            log.info(`[W-00] Proxy Link Established: ${canaryWorker.config.proxyServer}`);

            // Run canary test
            const canaryPassed = await runCanaryTest(canaryWorker, pendingTasks, checkpoint);

            if (canaryPassed) {
                // Remove canary task from pending list
                const canaryTask = pendingTasks.shift();
                if (canaryTask) {
                    if (checkpoint.processed[canaryTask.hash]?.status === 'SUCCESS') {
                        results.total = pendingTasks.length;
                        results.success = 1;
                        const canaryResult = checkpoint.processed[canaryTask.hash].result;
                        if (canaryResult) {
                            results.temporalRecords += canaryResult.temporalCount || 0;
                            results.providersCaptured += canaryResult.providersCaptured || 0;
                        }
                    }
                }
            }

            // Initialize remaining workers
            log.info('[V86.120] Initializing remaining 19 workers...');
            await Promise.all(
                workerManagers.slice(1).map(wm => wm.createBrowser().catch(err => {
                    log.error(`[${wm.config.workerName}] Init failed: ${err.message}`);
                }))
            );

            // Log proxy connections for all workers
            for (const wm of workerManagers) {
                if (wm.config.isAlive) {
                    log.info(`[${wm.config.workerName}] Proxy Link Established: ${wm.config.proxyServer}`);
                }
            }
        } else {
            // Initialize all workers (no canary test)
            log.info('[V86.120] Initializing all workers...');
            await Promise.all(
                workerManagers.map(wm => wm.createBrowser().catch(err => {
                    log.error(`[${wm.config.workerName}] Init failed: ${err.message}`);
                }))
            );
        }

        // Process tasks with matrix workers
        let taskIndex = 0;

        while (taskIndex < pendingTasks.length) {
            const availableWorkers = workerManagers.filter(
                wm => wm.config.status === 'idle' &&
                     wm.config.isAlive &&
                     wm.config.restartCount < CONFIG.zombieGuard.maxRestarts
            );

            if (availableWorkers.length === 0) {
                await new Promise(resolve => setTimeout(resolve, 500));
                continue;
            }

            // Assign tasks to available workers
            const batchPromises = availableWorkers.map(async (workerManager) => {
                if (taskIndex >= pendingTasks.length) return null;

                const task = pendingTasks[taskIndex++];

                if (checkpoint.processed[task.hash]) {
                    return { hash: task.hash, skipped: true };
                }

                // Check if worker needs restart
                if (workerManager.shouldRestart()) {
                    await workerManager.restartBrowser();
                }

                return processTaskWithWorker(task, workerManager, checkpoint);
            });

            const batchResults = await Promise.allSettled(batchPromises);

            // Process results
            for (const settledResult of batchResults) {
                if (!settledResult.value) continue;
                const r = settledResult.value;
                if (r.skipped) continue;

                if (r.success) {
                    results.success++;
                    results.temporalRecords += r.temporalCount;
                    results.providersCaptured += r.providersCaptured;
                } else {
                    results.failed++;
                }
            }

            // Progress monitoring
            if (taskIndex % CONFIG.monitoring.progressInterval === 0) {
                const elapsedMs = Date.now() - CONFIG.monitoring.startTime;
                const elapsedMin = elapsedMs / 60000;
                const speed = elapsedMin > 0 ? (taskIndex / elapsedMin).toFixed(1) : 0;

                log.info(`[Progress] Processed: ${taskIndex}/${results.total} | Success: ${results.success} | Speed: ${speed} matches/min`);
            }
        }

        // Final checkpoint save
        saveCheckpoint(checkpoint);

        // Cleanup all workers
        log.info('[V86.120] Cleaning up workers...');
        await Promise.all(
            workerManagers.map(wm => wm.cleanup())
        );

        // Stop zombie monitor
        if (zombieMonitorInterval) {
            clearInterval(zombieMonitorInterval);
        }

        // Generate report
        const elapsedMs = Date.now() - CONFIG.monitoring.startTime;
        const elapsedMin = elapsedMs / 60000;
        const avgSpeed = elapsedMin > 0 ? (results.total / elapsedMin).toFixed(1) : 0;

        console.log('\n' + '='.repeat(70));
        console.log('[V86.120] Turbo Pipeline - Final Report');
        console.log('='.repeat(70));
        console.log(`Total Tasks: ${results.total}`);
        console.log(`Success: ${results.success} (${(results.success / results.total * 100).toFixed(1)}%)`);
        console.log(`Failed: ${results.failed}`);
        console.log(`Temporal Records: ${results.temporalRecords}`);
        console.log(`Providers Captured: ${results.providersCaptured}`);
        console.log(`Elapsed Time: ${elapsedMin.toFixed(2)} min`);
        console.log(`Average Speed: ${avgSpeed} matches/min`);
        console.log('='.repeat(70) + '\n');

        return {
            version: 'V86.120',
            timestamp: new Date().toISOString(),
            config: {
                concurrentWorkers: CONFIG.concurrentWorkers,
                gatewayHost: CONFIG.matrixPortMapping.gatewayHost,
                portRange: `${CONFIG.matrixPortMapping.startPort}-${CONFIG.matrixPortMapping.endPort}`
            },
            results: results,
            performance: {
                elapsedMs,
                elapsedMin,
                avgSpeed
            }
        };

    } catch (error) {
        log.error(`[V86.120] Fatal error: ${error.message}`);
        throw error;
    } finally {
        // Cleanup
        if (zombieMonitorInterval) {
            clearInterval(zombieMonitorInterval);
        }

        await Promise.all(
            workerManagers.map(wm => wm.cleanup())
        );
    }
}

// ============================================================================
// MAIN ENTRY
// ============================================================================

(async () => {
    try {
        const report = await runV86_TurboPipeline();

        if (report.results && report.results.success > 0) {
            log.success('[V86.120] Turbo Pipeline completed successfully');
            process.exit(0);
        } else {
            log.warn('[V86.120] Pipeline completed with no successes');
            process.exit(1);
        }
    } catch (error) {
        log.error(error.stack);
        process.exit(1);
    }
})();
