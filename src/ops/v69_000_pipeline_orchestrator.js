/**
 * V69.000 - The Master Switch
 * ===========================
 *
 * Full-Stack Pipeline Orchestrator - Automated Data Flow Trigger System
 *
 * This module eliminates the three manual breakpoints identified in V68.300 audit:
 * 1. L2 Enrichment Trigger: Auto-fill empty L2 data boxes
 * 2. Bridge Trigger: Auto-discover and align hashes
 * 3. Odds Harvest Trigger: Auto-collect temporal odds
 *
 * @file v69_000_pipeline_orchestrator.js
 * @author Principal Systems Integration Engineer
 * @version V69.000
 * @since 2026-01-25
 *
 * ============================================================================
 * FLOW DIAGRAM:
 * ============================================================================
 *
 *  matches.l2_raw_json IS NULL
 *       │
 *       ▼ [Step A: L2 Enrichment Trigger]
 *  ┌──────────────────────────────────────────────────────────────┐
 *  │  Python: FotMobCoreCollector.harvest_match_with_league()       │
 *  │  → 填补 xG, 阵容, rating 等详情                                   │
 *  └──────────────────────────────────────────────────────────────┘
 *       │
 *       ▼ status: 'DISCOVERED' → 'ENRICHED'
 *  matches NOT IN matches_mapping
 *       │
 *       ▼ [Step B: Bridge Trigger (V73.200 BridgeEngine)]
 *  ┌──────────────────────────────────────────────────────────────┐
 *  │  V73.200 BridgeEngine (队名模糊匹配 - SOE)                    │
 *  │  → 发现 oddsportal_url, 更新 matches_mapping                 │
 *  │  → 120+ 队名标准化, 英超优先策略, 70% 阈值                    │
 *  └──────────────────────────────────────────────────────────────┘
 *       │
 *       ▼ status: 'ENRICHED' → 'MAPPED'
 *  temporal_metric_records EMPTY OR stale
 *       │
 *       ▼ [Step C: Odds Harvest Trigger]
 *  ┌──────────────────────────────────────────────────────────────┐
 *  │  V66.000 Application.run(url, sourceId)                       │
 *  │  → 悬停收割, 收集 5 家 Provider 时间序列赔率                     │
 *  └──────────────────────────────────────────────────────────────┘
 *       │
 *       ▼ status: 'MAPPED' → 'HARVESTED'
 *
 * ============================================================================
 */

'use strict';

// ============================================================================
// IMPORTS
// ============================================================================

const path = require('path');
const { Pool } = require('pg');
const { spawn } = require('child_process');

// V73.200: Import unified BridgeEngine (Single Source of Excellence)
const { BridgeEngine } = require('../modules/bridge_engine');

// V72.100: Fixed spawnAsync wrapper for proper error handling
/**
 * Spawn a process asynchronously and return the result
 * @param {string} command - Command to execute
 * @param {Array<string>} args - Arguments array
 * @param {Object} options - Options object
 * @returns {Promise<{stdout: string, stderr: string}>}
 */
function spawnAsync(command, args, options = {}) {
    return new Promise((resolve, reject) => {
        const child = spawn(command, args, options);

        let stdout = '';
        let stderr = '';

        child.stdout.on('data', (data) => {
            stdout += data.toString();
        });

        child.stderr.on('data', (data) => {
            stderr += data.toString();
        });

        child.on('close', (code) => {
            if (code === 0) {
                resolve({ stdout, stderr });
            } else {
                reject(new Error(`Process exited with code ${code}: ${stderr}`));
            }
        });

        child.on('error', (error) => {
            reject(error);
        });
    });
}

// Database modules
const { getGlobalPool, cleanupGlobalPool } = require('../core/browser');

// V70.200 Data Sentinel
const { DataSentinel } = require('./v70_200_data_sentinel');

// Configuration
const ORCHESTRATOR_CONFIG = {
    version: 'V82.500',
    name: 'The Master Switch (V82.500 Turbo Mode)',

    // ============================================================================
    // V82.500: Turbo Concurrency Configuration
    // ============================================================================
    // Global rate limiting to prevent API熔断 (circuit breaker tripping)
    // Throughput Formula: Throughput = 1 / (T_process + T_delay)
    // Target: ~3,600 matches/day with 3s delay + increased concurrency
    MATCH_PROCESSING_INTERVAL: 3000,  // V82.500: Reduced from 5s to 3s

    // ============================================================================
    // V71.100: League Filtering Configuration
    // ============================================================================
    // Supported leagues for L2 enrichment (have valid stats data from FotMob API)
    // Filtered out: league_id=55 (Serie A - missing 'content.stats' field)
    supportedLeagueIds: [
        47,  // Premier League
        87,  // La Liga
        54,  // Bundesliga
        53   // Ligue 1
        // Note: 55 (Serie A) excluded due to missing L2 stats structure
    ],

    // Step A: L2 Enrichment settings
    l2Enrichment: {
        batchSize: 50,
        maxConcurrent: 6,  // V82.500: Increased from 3 to 6
        cooldownSeconds: 10,
        pythonPath: 'python3',
        scriptPath: path.join(__dirname, '../../scripts/ops/v69_010_l2_trigger.py'),
        // V71.100: Apply league filtering to scan query
        filterUnsupportedLeagues: true  // Enable automatic filtering
    },

    // Step B: Bridge settings (V73.200: Using BridgeEngine)
    bridge: {
        batchSize: 100,
        fuzzyThreshold: 70.0,  // V73.200 optimized threshold (was 85%)
        maxConcurrent: 4  // V82.500: Increased from 2 to 4
        // V73.200: Removed scriptPath - now using BridgeEngine directly
    },

    // Step C: Odds Harvest settings
    oddsHarvest: {
        batchSize: 20,
        maxConcurrent: 4,  // V82.500: Increased from 2 to 4
        highPriorityLeagues: [
            'Premier League',
            'La Liga',
            'Bundesliga',
            'Ligue 1'  // V71.100: Removed Serie A (no L2 data)
        ],
        harvestWindowHours: 48,  // 赛前 48 小时内收割
        scriptPath: path.join(__dirname, '../main.js')
    },

    // Circuit breaker
    circuitBreaker: {
        maxConcurrentBrowsers: 6,  // V82.500: Increased from 3 to 6
        maxRetryAttempts: 3,
        backoffMultiplier: 2,
        baseDelayMs: 5000,
        // V82.500: 403 detection and auto-rollback
        error403Threshold: 0.05,  // 5% 403 error rate triggers rollback
        rollbackConcurrency: 2,  // Rollback to safe concurrency level
        cooldownMinutes: 30
    },

    // State persistence
    state: {
        table: 'match_pipeline_state',
        statuses: ['DISCOVERED', 'ENRICHED', 'MAPPED', 'HARVESTED', 'FAILED'],
        batchSize: 100
    },

    // V70.200 Data Sentinel
    sentinel: {
        enabled: true,
        runEveryNCycles: 1,  // Run sentinel after every N cycles
        showDashboard: true
    }
};

// ============================================================================
// STRUCTURED LOGGER
// ============================================================================

/**
 * Create structured log entry
 * @param {string} level - Log level
 * @param {string} message - Log message
 * @param {Object} [data] - Additional data
 * @returns {Object} - Structured log entry
 */
function createLogEntry(level, message, data = {}) {
    return {
        level,
        timestamp: new Date().toISOString(),
        module: 'v69_000_orchestrator',
        version: ORCHESTRATOR_CONFIG.version,
        message,
        trace_id: generateTraceId(),
        ...data
    };
}

/**
 * Log structured message
 * @param {string} level - Log level
 * @param {string} message - Log message
 * @param {Object} [data] - Additional data
 */
function log(level, message, data = {}) {
    const entry = createLogEntry(level, message, data);
    console.log(JSON.stringify(entry));
}

/**
 * Generate unique trace ID
 * @returns {string} - Trace ID
 */
function generateTraceId() {
    return `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
}

// ============================================================================
// ERROR CLASS
// ============================================================================

/**
 * Orchestrator Error
 * @extends Error
 */
class OrchestratorError extends Error {
    /**
     * @param {string} code - Error code
     * @param {string} message - Error message
     * @param {string} [traceId] - Trace ID
     * @param {Object} [context] - Error context
     */
    constructor(code, message, traceId = null, context = {}) {
        super(message);
        this.name = 'OrchestratorError';
        this.errorCode = code;
        this.traceId = traceId || generateTraceId();
        this.timestamp = new Date().toISOString();
        this.context = context;
    }

    /**
     * Convert to JSON
     * @returns {Object} - JSON representation
     */
    toJSON() {
        return {
            error_code: this.errorCode,
            trace_id: this.traceId,
            timestamp: this.timestamp,
            message: this.message,
            context: this.context
        };
    }
}

// ============================================================================
// DATABASE CONNECTION
// ============================================================================

/**
 * Create orchestrator database pool
 * @param {Object} [config={}] - Configuration overrides
 * @returns {Pool} - PostgreSQL connection pool
 */
function createOrchestratorPool(config = {}) {
    const poolConfig = {
        host: process.env.DB_HOST || '172.25.16.1',
        port: parseInt(process.env.DB_PORT) || 5432,
        database: process.env.DB_NAME || 'football_db',
        user: process.env.DB_USER || 'football_user',
        password: process.env.DB_PASSWORD || 'football_pass',
        max: config.max || 20,
        min: config.min || 2,
        idleTimeoutMillis: config.idleTimeout || 30000
    };

    const pool = new Pool(poolConfig);

    pool.on('error', (err) => {
        log('error', 'Database pool error', { error: err.message });
    });

    return pool;
}

// ============================================================================
// STEP A: L2 ENRICHMENT TRIGGER
// ============================================================================

/**
 * V69.010 - L2 Enrichment Trigger
 *
 * Monitors matches with NULL l2_raw_json and triggers FotMob data collection.
 */
class L2EnrichmentTrigger {
    /**
     * @param {Pool} db - Database pool
     */
    constructor(db) {
        this.db = db;
        this.config = ORCHESTRATOR_CONFIG.l2Enrichment;
    }

    /**
     * Scan for matches needing L2 enrichment
     * @param {number} [limit=50] - Maximum matches to process
     * @returns {Promise<Array>} - Matches needing enrichment
     */
    async scan(limit = 50) {
        const client = await this.db.connect();
        try {
            // V71.100: Build league filter condition
            let leagueFilterCondition = '';
            const queryParams = [limit];

            if (this.config.filterUnsupportedLeagues && ORCHESTRATOR_CONFIG.supportedLeagueIds.length > 0) {
                const supportedIds = ORCHESTRATOR_CONFIG.supportedLeagueIds.join(',');
                leagueFilterCondition = `AND league_id IN (${supportedIds})`;
                log('info', '[V71.100] League filtering active', {
                    supported_league_ids: ORCHESTRATOR_CONFIG.supportedLeagueIds,
                    excluded_league_id: 55  // Serie A excluded
                });
            }

            const query = `
                SELECT match_id, league_name, season, home_team, away_team, match_date, league_id
                FROM matches
                WHERE l2_raw_json IS NULL
                  AND match_date < NOW()  -- V72.100: Only past matches (not future fixtures)
                  AND match_date >= NOW() - INTERVAL '7 days'  -- V72.100: Recent matches only
                  ${leagueFilterCondition}
                ORDER BY match_date DESC
                LIMIT $1
            `;

            const result = await client.query(query, queryParams);

            log('info', `[Step A] Found matches needing L2 enrichment`, {
                count: result.rows.length,
                limit,
                filtered: this.config.filterUnsupportedLeagues
            });

            return result.rows;

        } finally {
            client.release();
        }
    }

    /**
     * Trigger L2 enrichment via Python script
     * @param {Array} matches - Matches to enrich
     * @returns {Promise<Object>} - Processing result
     */
    async triggerEnrichment(matches) {
        const matchIds = matches.map(m => m.match_id).join(',');

        log('info', '[Step A] Triggering L2 enrichment', {
            count: matches.length,
            sample_match_ids: matchIds.split(',').slice(0, 5).join(',')
        });

        try {
            // V72.100: Fixed spawnAsync call with proper command/args separation
            const { stdout, stderr } = await spawnAsync(
                this.config.pythonPath,  // command (string)
                [  // args (array)
                    this.config.scriptPath,
                    '--match-ids', matchIds,
                    '--batch-size', this.config.batchSize.toString()
                ],
                {
                    cwd: path.join(__dirname, '../..')
                }
            );

            if (stderr && stderr.includes('ERROR')) {
                throw new Error(`Python script error: ${stderr}`);
            }

            const lines = stdout.trim().split('\n');
            const resultLine = lines[lines.length - 1]; // Last line should have JSON result
            const result = JSON.parse(resultLine);

            log('info', '[Step A] L2 enrichment completed', result);

            return result;

        } catch (error) {
            log('error', '[Step A] L2 enrichment failed', {
                error: error.message,
                match_count: matches.length
            });
            throw new OrchestratorError(
                'L2_ENRICHMENT_FAILED',
                `Failed to enrich L2 data: ${error.message}`,
                null,
                { match_count: matches.length }
            );
        }
    }

    /**
     * Update pipeline state after enrichment
     * @param {Array} matchIds - Match IDs that were enriched
     * @returns {Promise<number>} - Number of updated records
     */
    async updateState(matchIds) {
        const client = await this.db.connect();
        try {
            const query = `
                INSERT INTO match_pipeline_state (match_id, status, updated_at)
                VALUES ($1, 'ENRICHED', NOW())
                ON CONFLICT (match_id)
                DO UPDATE SET status = 'ENRICHED', updated_at = NOW()
            `;

            let updated = 0;
            for (const matchId of matchIds) {
                const result = await client.query(query, [matchId]);
                if (result.rowCount > 0) updated++;
            }

            log('info', '[Step A] Pipeline state updated', {
                updated_count: updated,
                new_status: 'ENRICHED'
            });

            return updated;

        } finally {
            client.release();
        }
    }

    /**
     * Execute Step A: Full L2 enrichment flow
     * @param {number} [limit=50] - Maximum matches to process
     * @returns {Promise<Object>} - Execution result
     */
    async execute(limit = 50) {
        log('info', '[Step A] Starting L2 enrichment trigger', { limit });

        const matches = await this.scan(limit);

        if (matches.length === 0) {
            log('info', '[Step A] No matches need L2 enrichment');
            return { processed: 0, enriched: 0 };
        }

        // V71.100: Log league distribution before processing
        const leagueDistribution = {};
        matches.forEach(m => {
            leagueDistribution[m.league_name] = (leagueDistribution[m.league_name] || 0) + 1;
        });
        log('info', '[V71.100] Processing matches by league', leagueDistribution);

        const result = await this.triggerEnrichment(matches);

        // Update pipeline state
        const matchIds = matches.map(m => m.match_id);
        await this.updateState(matchIds);

        // V71.100: Apply rate limiting delay after batch enrichment
        if (ORCHESTRATOR_CONFIG.MATCH_PROCESSING_INTERVAL > 0) {
            const delayMs = ORCHESTRATOR_CONFIG.MATCH_PROCESSING_INTERVAL;
            log('info', `[V71.100] Rate limiting: Waiting ${delayMs}ms after batch enrichment`, {
                batch_size: matches.length,
                delay_ms: delayMs
            });

            await new Promise(resolve => setTimeout(resolve, delayMs));
        }

        return {
            processed: matches.length,
            enriched: result.enriched || matches.length,
            failed: result.failed || 0
        };
    }
}

// ============================================================================
// STEP B: BRIDGE TRIGGER
// ============================================================================

/**
 * V73.200 - Bridge Trigger (Unified with BridgeEngine)
 *
 * Uses BridgeEngine as the Single Source of Excellence for all bridge/mapping logic.
 * Replaces V69.020 implementation with proven V73.000 algorithm (18.40% success rate).
 *
 * Key improvements:
 *   - Fixed Levenshtein algorithm (no more 3D indexing bug)
 *   - 120+ team name normalizations (5 leagues)
 *   - Premier League priority strategy (2020-2022 seasons)
 *   - Direct matches_mapping→matches_mapping matching (bypasses insufficient entities_mapping)
 *   - 70% fuzzy threshold (optimized from 85%)
 */
class BridgeTrigger {
    /**
     * @param {Pool} db - Database pool
     */
    constructor(db) {
        this.db = db;
        this.config = ORCHESTRATOR_CONFIG.bridge;
        // V73.200: Use BridgeEngine as Single Source of Excellence
        this.bridgeEngine = new BridgeEngine(db);
    }

    /**
     * Execute Step B: Full bridge trigger flow
     * Delegates to BridgeEngine.execute()
     * @param {number} [limit=100] - Maximum matches to process
     * @returns {Promise<Object>} - Execution result
     */
    async execute(limit = 100) {
        log('info', '[Step B] Starting bridge trigger (V73.200 BridgeEngine)', { limit });

        // V73.200: Delegate to unified BridgeEngine
        const result = await this.bridgeEngine.execute(limit);

        log('info', '[Step B] Bridge mapping completed (V73.200)', {
            mapped: result.mapped,
            failed: result.failed,
            success_rate: result.success_rate
        });

        return result;
    }
}

// ============================================================================
// STEP C: ODDS HARVEST TRIGGER
// ============================================================================

/**
 * V69.030 - Odds Harvest Trigger
 *
 * Triggers V66.000 engine for harvesting temporal odds from high-priority matches.
 */
class OddsHarvestTrigger {
    /**
     * @param {Pool} db - Database pool
     */
    constructor(db) {
        this.db = db;
        this.config = ORCHESTRATOR_CONFIG.oddsHarvest;
    }

    /**
     * Scan for matches needing odds harvest
     * @param {number} [limit=20] - Maximum matches to process
     * @returns {Promise<Array>} - Matches needing harvest
     */
    async scan(limit = 20) {
        const client = await this.db.connect();
        try {
            // V72.200: Fixed JOIN chain for correct schema alignment
            // matches_mapping.fotmob_id -> entities_mapping.source_id -> temporal_metric_records.entity_id
            const query = `
                SELECT mm.fotmob_id, mm.oddsportal_url,
                       m.league_name, m.home_team, m.away_team, m.match_date,
                       COUNT(tmr.id) as existing_records
                FROM matches_mapping mm
                JOIN matches m ON mm.fotmob_id = m.match_id
                LEFT JOIN entities_mapping em ON em.source_system = 'fotmob' AND em.source_id = mm.fotmob_id
                LEFT JOIN temporal_metric_records tmr ON tmr.entity_id = em.entity_id
                WHERE mm.review_status = 'approved'
                  AND mm.oddsportal_url IS NOT NULL
                  AND (tmr.id IS NULL
                       OR tmr.occurred_at < NOW() - INTERVAL '24 hours')
                  AND m.match_date >= NOW() + INTERVAL '48 hours'
                  AND m.match_date <= NOW() + INTERVAL '7 days'
                GROUP BY mm.fotmob_id, mm.oddsportal_url, m.league_name, m.home_team, m.away_team, m.match_date
                ORDER BY
                    CASE WHEN m.league_name = ANY($1) THEN 0 ELSE 1 END,
                    m.match_date ASC
                LIMIT $2
            `;

            const result = await client.query(query, [
                this.config.highPriorityLeagues,
                limit
            ]);

            log('info', '[Step C] Found matches needing odds harvest', {
                count: result.rows.length,
                limit,
                high_priority_filter: true
            });

            return result.rows;

        } finally {
            client.release();
        }
    }

    /**
     * Trigger odds harvest via V66.000 engine
     * @param {Array} matches - Matches to harvest
     * @returns {Promise<Object>} - Processing result
     */
    async triggerHarvest(matches) {
        log('info', '[Step C] Triggering odds harvest', {
            count: matches.length,
            sample_urls: matches.slice(0, 3).map(m => m.oddsportal_url)
        });

        let harvested = 0;
        let failed = 0;

        for (const match of matches) {
            try {
                const url = `https://www.oddsportal.com${match.oddsportal_url}`;
                const sourceId = match.fotmob_id;

                // Call V66.000 Application
                const Application = require('../main');
                const app = new Application();

                await app.initialize();

                const result = await app.run(url, sourceId);

                if (result.success) {
                    harvested++;
                    await this.updateState(match.fotmob_id, 'HARVESTED');
                } else {
                    failed++;
                    await this.updateState(match.fotmob_id, 'FAILED');
                }

                await app.shutdown();

                // Cooldown between harvests
                await this.cooldown();

            } catch (error) {
                log('error', '[Step C] Harvest failed for match', {
                    match_id: match.fotmob_id,
                    error: error.message
                });
                failed++;
                await this.updateState(match.fotmob_id, 'FAILED');
            }
        }

        log('info', '[Step C] Odds harvest completed', {
            harvested,
            failed,
            success_rate: (harvested / matches.length * 100).toFixed(2) + '%'
        });

        return { harvested, failed, processed: matches.length };
    }

    /**
     * Update pipeline state after harvest
     * @param {string} matchId - Match ID
     * @param {string} status - New status
     * @returns {Promise<void>}
     */
    async updateState(matchId, status) {
        const client = await this.db.connect();
        try {
            await client.query(
                `INSERT INTO match_pipeline_state (match_id, status, updated_at)
                 VALUES ($1, $2, NOW())
                 ON CONFLICT (match_id)
                 DO UPDATE SET status = $2, updated_at = NOW()`,
                [matchId, status]
            );
        } finally {
            client.release();
        }
    }

    /**
     * Cooldown between harvest operations
     * @returns {Promise<void>}
     */
    async cooldown() {
        const delay = Math.random() * 5000 + 5000; // 5-10 seconds
        log('debug', '[Step C] Harvest cooldown', { delay_ms: Math.round(delay) });
        await new Promise(resolve => setTimeout(resolve, delay));
    }

    /**
     * Execute Step C: Full odds harvest flow
     * @param {number} [limit=20] - Maximum matches to process
     * @returns {Promise<Object>} - Execution result
     */
    async execute(limit = 20) {
        log('info', '[Step C] Starting odds harvest trigger', { limit });

        const matches = await this.scan(limit);

        if (matches.length === 0) {
            log('info', '[Step C] No matches need odds harvest');
            return { processed: 0, harvested: 0, failed: 0 };
        }

        return await this.triggerHarvest(matches);
    }
}

// ============================================================================
// MASTER ORCHESTRATOR
// ============================================================================

/**
 * V69.000 - The Master Switch
 *
 * Orchestrates the full pipeline: L2 Enrichment → Bridge → Odds Harvest
 */
class PipelineOrchestrator {
    /**
     * @param {Object} [options={}] - Configuration options
     */
    constructor(options = {}) {
        this.db = createOrchestratorPool(options.db);
        this.l2Trigger = new L2EnrichmentTrigger(this.db);
        this.bridgeTrigger = new BridgeTrigger(this.db);
        this.oddsTrigger = new OddsHarvestTrigger(this.db);

        this.running = false;
        this.stats = {
            cycle: 0,
            l2_enriched: 0,
            bridged: 0,
            harvested: 0,
            failed: 0
        };

        // Register shutdown handlers
        this._registerSignalHandlers();
    }

    /**
     * Register signal handlers for graceful shutdown
     * @private
     */
    _registerSignalHandlers() {
        const shutdownHandler = async () => {
            log('info', 'Received shutdown signal, cleaning up...');
            this.running = false;
            await this.shutdown();
            process.exit(0);
        };

        process.on('SIGINT', shutdownHandler);
        process.on('SIGTERM', shutdownHandler);
    }

    /**
     * Execute full pipeline cycle
     * @param {Object} [limits={}] - Step-specific limits
     * @returns {Promise<Object>} - Overall result
     */
    async executeCycle(limits = {}) {
        const {
            l2Limit = 50,
            bridgeLimit = 100,
            oddsLimit = 20
        } = limits;

        this.stats.cycle++;

        log('info', '='.repeat(80));
        log('info', `[V69.000] Starting Pipeline Cycle #${this.stats.cycle}`);
        log('info', '='.repeat(80));

        const cycleStart = Date.now();

        // Step A: L2 Enrichment
        log('info', '');
        log('info', '┌─ Step A: L2 Enrichment Trigger ─────────────────────────────────┐');
        const l2Result = await this.l2Trigger.execute(l2Limit);
        this.stats.l2_enriched += l2Result.enriched || 0;
        this.stats.failed += l2Result.failed || 0;
        log('info', '└────────────────────────────────────────────────────────────────┘');
        log('info', `  Result: ${l2Result.processed} processed, ${l2Result.enriched} enriched, ${l2Result.failed} failed`);

        // Step B: Bridge Mapping
        log('info', '');
        log('info', '┌─ Step B: Bridge Trigger ─────────────────────────────────────────┐');
        const bridgeResult = await this.bridgeTrigger.execute(bridgeLimit);
        this.stats.bridged += bridgeResult.mapped || 0;
        this.stats.failed += bridgeResult.failed || 0;
        log('info', '└────────────────────────────────────────────────────────────────┘');
        log('info', `  Result: ${bridgeResult.processed} processed, ${bridgeResult.mapped} mapped, ${bridgeResult.failed} failed`);

        // Step C: Odds Harvest
        log('info', '');
        log('info', '┌─ Step C: Odds Harvest Trigger ────────────────────────────────────┐');
        const oddsResult = await this.oddsTrigger.execute(oddsLimit);
        this.stats.harvested += oddsResult.harvested || 0;
        this.stats.failed += oddsResult.failed || 0;
        log('info', '└────────────────────────────────────────────────────────────────┘');
        log('info', `  Result: ${oddsResult.processed} processed, ${oddsResult.harvested} harvested, ${oddsResult.failed} failed`);

        const cycleTime = (Date.now() - cycleStart) / 1000;

        log('info', '');
        log('info', '='.repeat(80));
        log('info', `[V69.000] Pipeline Cycle #${this.stats.cycle} Complete`);
        log('info', '='.repeat(80));
        log('info', `  L2 Enriched: ${this.stats.l2_enriched} total`);
        log('info', `  Bridge Mapped: ${this.stats.bridged} total`);
        log('info', `  Odds Harvested: ${this.stats.harvested} total`);
        log('info', `  Failed: ${this.stats.failed} total`);
        log('info', `  Cycle Time: ${cycleTime.toFixed(1)}s`);
        log('info', '='.repeat(80));

        // V70.200: Run Data Sentinel after cycle
        if (ORCHESTRATOR_CONFIG.sentinel.enabled &&
            this.stats.cycle % ORCHESTRATOR_CONFIG.sentinel.runEveryNCycles === 0) {
            log('info', '');
            log('info', '[V69.000] Running V70.200 Data Sentinel...');
            try {
                const sentinel = new DataSentinel();
                const sentinelResult = ORCHESTRATOR_CONFIG.sentinel.showDashboard ?
                    await sentinel.run() :
                    await sentinel.executeScan();

                await sentinel.cleanup();

                // Add sentinel health check warning if score is low
                if (sentinelResult.healthScore < 7) {
                    log('warning', `[V69.000] ⚠️ Data health score is ${sentinelResult.healthScore}/10 - review quality gate results`);
                }

            } catch (sentinelError) {
                log('error', '[V69.000] Sentinel scan failed', {
                    error: sentinelError.message
                });
            }
        }

        return {
            cycle: this.stats.cycle,
            l2: l2Result,
            bridge: bridgeResult,
            odds: oddsResult,
            cycle_time_seconds: cycleTime
        };
    }

    /**
     * Run continuous pipeline loop
     * @param {Object} [options={}] - Run options
     * @returns {Promise<void>}
     */
    async run(options = {}) {
        const {
            cycles = 1,
            intervalSeconds = 300,  // 5 minutes between cycles
            limits = {}
        } = options;

        this.running = true;
        log('info', `[V69.000] Starting continuous pipeline mode`, {
            cycles,
            interval_minutes: intervalSeconds / 60
        });

        for (let i = 0; i < cycles && this.running; i++) {
            await this.executeCycle(limits);

            if (i < cycles - 1 && this.running) {
                log('info', `[V69.000] Waiting ${intervalSeconds}s before next cycle...`);
                await this._sleep(intervalSeconds * 1000);
            }
        }

        log('info', '[V69.000] Pipeline execution completed');
    }

    /**
     * Graceful shutdown
     * @returns {Promise<void>}
     */
    async shutdown() {
        log('info', '[V69.000] Shutting down orchestrator...');

        try {
            await this.db.end();
            log('info', '[V69.000] Database pool closed');
        } catch (error) {
            log('error', '[V69.000] Error during shutdown', { error: error.message });
        }
    }

    /**
     * Sleep utility
     * @param {number} ms - Milliseconds to sleep
     * @returns {Promise<void>}
     * @private
     */
    async _sleep(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }

    /**
     * Get pipeline statistics
     * @returns {Object} - Current stats
     */
    getStats() {
        return {
            ...this.stats,
            running: this.running
        };
    }
}

// ============================================================================
// CLI INTERFACE
// ============================================================================

/**
 * Main CLI entry point
 * @param {Array} args - Command line arguments
 * @returns {Promise<number>} - Exit code
 */
async function main(args) {
    const orchestrator = new PipelineOrchestrator();

    try {
        // Parse command line arguments
        const mode = args[0] || 'single';

        // V72.100: Support generic --limit parameter for pilot testing
        const genericLimit = parseInt(args['--limit']);

        const options = {
            cycles: parseInt(args['--cycles']) || 1,
            intervalSeconds: parseInt(args['--interval']) || 300,
            limits: {
                l2Limit: genericLimit || parseInt(args['--l2-limit']) || 50,
                bridgeLimit: genericLimit || parseInt(args['--bridge-limit']) || 100,
                oddsLimit: genericLimit || parseInt(args['--odds-limit']) || 20
            }
        };

        if (mode === 'continuous') {
            await orchestrator.run(options);
        } else {
            await orchestrator.executeCycle(options.limits);
        }

        const stats = orchestrator.getStats();
        log('info', '[V69.000] Final statistics', stats);

        await orchestrator.shutdown();

        return 0;

    } catch (error) {
        log('error', '[V69.000] Fatal error', {
            error: error.message,
            stack: error.stack
        });

        await orchestrator.shutdown();

        return 1;
    }
}

// ============================================================================
// EXPORTS
// ============================================================================

module.exports = {
    PipelineOrchestrator,
    L2EnrichmentTrigger,
    BridgeTrigger,
    OddsHarvestTrigger,
    ORCHESTRATOR_CONFIG,
    main,
    generateTraceId
};

// ============================================================================
// CLI EXECUTION
// ============================================================================

if (require.main === module) {
    const args = process.argv.slice(2);

    // Parse arguments
    const options = {};
    for (let i = 0; i < args.length; i++) {
        if (args[i] === '--cycles' && args[i + 1]) {
            options['--cycles'] = args[++i];
        } else if (args[i] === '--interval' && args[i + 1]) {
            options['--interval'] = args[++i];
        } else if (args[i] === '--limit' && args[i + 1]) {
            // V72.100: Generic limit for pilot testing
            options['--limit'] = args[++i];
        } else if (args[i] === '--l2-limit' && args[i + 1]) {
            options['--l2-limit'] = args[++i];
        } else if (args[i] === '--bridge-limit' && args[i + 1]) {
            options['--bridge-limit'] = args[++i];
        } else if (args[i] === '--odds-limit' && args[i + 1]) {
            options['--odds-limit'] = args[++i];
        }
    }

    // V72.100: Assign options as properties to args for main() to access
    Object.assign(args, options);
    main(args).then(exitCode => {
        process.exit(exitCode);
    });
}
