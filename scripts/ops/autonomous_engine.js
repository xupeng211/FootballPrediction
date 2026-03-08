#!/usr/bin/env node
/**
 * AutonomousOrchestrator - V201.1 鍏ㄨ嚜鍔ㄩ棴鐜祦姘寸嚎
 * ================================================
 *
 * 涓ぎ缂栨帓鍣細L1 鈫?L2 鈫?L3 鈫?RECALCULATE_ELO 鈫?PREDICT 浜斿眰娴佹按绾胯嚜鍔ㄧ紪鎺? * 瀹炵幇鐘舵€佽疆璇€佽嚜鍔ㄨЕ鍙戙€侀敊璇殧绂汇€佽嚜鎰堥噸璇? *
 * @module scripts/ops/autonomous_engine
 * @version V201.1.0
 */

'use strict';

const { Pool } = require('pg');
const { spawn } = require('child_process');

// 瀵煎叆涓夊眰妯″潡
const { FixtureSeeder } = require('../../src/infrastructure/FixtureSeeder');
const { ProductionHarvester } = require('../../src/infrastructure/harvesters/ProductionHarvester');
const { FeatureSmelter } = require('../../src/feature_engine/smelter/FeatureSmelter');

// 瀵煎叆缁熶竴娉ㄥ唽涓績
const Registry = require('../../config/registry');

// ============================================================================
// 閰嶇疆甯搁噺
// ============================================================================

const ORCHESTRATOR_CONFIG = {
    /** 寰幆闂撮殧 (ms) - 榛樿 6 灏忔椂 */
    LOOP_INTERVAL_MS: parseInt(process.env.LOOP_INTERVAL_MS) || 6 * 60 * 60 * 1000,

    /** L2 鏈€澶ч噸璇曟鏁?*/
    L2_MAX_RETRIES: parseInt(process.env.L2_MAX_RETRIES) || 3,

    /** L2 閲嶈瘯闂撮殧 (ms) */
    L2_RETRY_DELAY_MS: parseInt(process.env.L2_RETRY_DELAY_MS) || 60000,

    /** L3 鏈€澶ч噸璇曟鏁?*/
    L3_MAX_RETRIES: parseInt(process.env.L3_MAX_RETRIES) || 2,

    /** L3 閲嶈瘯闂撮殧 (ms) */
    L3_RETRY_DELAY_MS: parseInt(process.env.L3_RETRY_DELAY_MS) || 30000,

    /** 棰勬祴澶╂暟 */
    PREDICT_DAYS: parseInt(process.env.PREDICT_DAYS) || 4,

    /** 鏁版嵁搴撻厤缃?*/
    db: {
        host: process.env.DB_HOST || 'localhost',
        port: parseInt(process.env.DB_PORT || '5432'),
        database: process.env.DB_NAME || 'football_db',
        user: process.env.DB_USER || 'football_user',
        password: process.env.DB_PASSWORD || ''
    }
};

// ============================================================================
// 鏃ュ織绯荤粺
// ============================================================================

function timestamp() {
    return new Date().toISOString();
}

const log = {
    info: (msg, meta = null) => {
        const metaStr = meta ? ` | ${JSON.stringify(meta)}` : '';
        console.log(`[${timestamp()}] [INFO] [Orchestrator] ${msg}${metaStr}`);
    },
    warn: (msg, meta = null) => {
        const metaStr = meta ? ` | ${JSON.stringify(meta)}` : '';
        console.warn(`[${timestamp()}] [WARN] [Orchestrator] ${msg}${metaStr}`);
    },
    error: (msg, error = null) => {
        const meta = error ? { error: error.message, stack: error.stack } : {};
        console.error(`[${timestamp()}] [ERROR] [Orchestrator] ${msg}`, meta);
    },
    success: (msg, meta = null) => {
        const metaStr = meta ? ` | ${JSON.stringify(meta)}` : '';
        console.log(`[${timestamp()}] [SUCCESS] [Orchestrator] 鉁?${msg}${metaStr}`);
    },
    section: (title) => {
        console.log('\n' + '鈺?.repeat(70));
        console.log(`  ${title}`);
        console.log('鈺?.repeat(70));
    }
};

// ============================================================================
// AutonomousOrchestrator 绫?// ============================================================================

class AutonomousOrchestrator {
    constructor(config = {}) {
        this.config = { ...ORCHESTRATOR_CONFIG, ...config };
        this.pool = null;
        this.dryRun = false;
        this.onlyStages = null;
    }

    /**
     * 鍒濆鍖?     */
    async init() {
        log.info('馃殌 鍒濆鍖?AutonomousOrchestrator V201.1...');

        this.pool = new Pool({
            ...this.config.db,
            max: 5,
            idleTimeoutMillis: 30000
        });

        // 娴嬭瘯杩炴帴
        const client = await this.pool.connect();
        await client.query('SELECT 1');
        client.release();

        log.success('鏁版嵁搴撹繛鎺ユ睜宸插氨缁?);
    }

    /**
     * 鍏抽棴杩炴帴
     */
    async close() {
        if (this.pool) {
            await this.pool.end();
            log.info('鏁版嵁搴撹繛鎺ユ睜宸插叧闂?);
        }
    }

    // ========================================================================
    // 闃舵 1: L1 Discovery (璧涚▼鎾)
    // ========================================================================

    async runL1Discovery() {
        log.section('闃舵 1/5: L1 Discovery (璧涚▼鎾)');

        if (this.dryRun) {
            log.info('[DRY-RUN] 璺宠繃 L1 Discovery');
            return { success: true, skipped: true };
        }

        try {
            // 浠庨厤缃姞杞芥椿璺冭仈璧?            const leagueConfig = require('../../config/leagues.json');
            const activeLeagues = leagueConfig.active_leagues || [];
            const activeSeasons = leagueConfig.active_seasons || ['2024/2025'];

            log.info(`娲昏穬鑱旇禌: ${activeLeagues.map(l => l.name).join(', ')}`);
            log.info(`娲昏穬璧涘: ${activeSeasons.join(', ')}`);

            // 鍒涘缓 Seeder 瀹炰緥
            const seeder = new FixtureSeeder({
                leagues: activeLeagues,
                seasons: activeSeasons
            });

            await seeder.init();
            const stats = await seeder.seedAll();
            await seeder.close();

            const totalSeeded = stats?.total || 0;
            log.success(`L1 Discovery 瀹屾垚锛屽叡鎾 ${totalSeeded} 鍦烘瘮璧沗);
            return { success: true, seeded: totalSeeded, stats };

        } catch (error) {
            log.error(`L1 Discovery 澶辫触: ${error.message}`);
            return { success: false, error: error.message };
        }
    }

    // ========================================================================
    // 闃舵 2: L2 Harvest (璧旂巼鏀跺壊)
    // ========================================================================

    async runL2Harvest() {
        log.section('闃舵 2/5: L2 Harvest (璧旂巼鏀跺壊)');

        if (this.dryRun) {
            log.info('[DRY-RUN] 璺宠繃 L2 Harvest');
            return { success: true, skipped: true };
        }

        try {
            // 妫€鏌ュ緟鏀跺壊鏁伴噺
            const pending = await this._getPendingL2Count();
            log.info(`寰呮敹鍓?L2 鏁版嵁: ${pending} 鍦篳);

            if (pending === 0) {
                log.success('L2 鏁版嵁宸插叏閮ㄦ敹鍓插畬鎴?);
                return { success: true, harvested: 0 };
            }

            // 鎵ц鏀跺壊
            const harvester = new ProductionHarvester({
                batchSize: Math.min(pending, 500),
                maxWorkers: 1
            });

            await harvester.init();
            const result = await harvester.run();
            await harvester.close();

            log.success(`L2 Harvest 瀹屾垚锛屾敹鍓?${result.success || 0} 鍦篳);
            return { success: true, ...result };

        } catch (error) {
            log.error(`L2 Harvest 澶辫触: ${error.message}`);
            return { success: false, error: error.message };
        }
    }

    // ========================================================================
    // 闃舵 3: L3 Smelt (鐗瑰緛鐔旂偧)
    // ========================================================================

    async runL3Smelt() {
        log.section('闃舵 3/5: L3 Smelt (鐗瑰緛鐔旂偧)');

        if (this.dryRun) {
            log.info('[DRY-RUN] 璺宠繃 L3 Smelt');
            return { success: true, skipped: true };
        }

        try {
            // 妫€鏌ュ緟鐔旂偧鏁伴噺
            const pending = await this._getPendingL3Count();
            log.info(`寰呯啍鐐?L3 鐗瑰緛: ${pending} 鍦篳);

            if (pending === 0) {
                log.success('L3 鐗瑰緛宸插叏閮ㄧ啍鐐煎畬鎴?);
                return { success: true, smelted: 0 };
            }

            // 鎵ц鐔旂偧
            const smelter = new FeatureSmelter({
                batchSize: Math.min(pending, 500)
            });

            await smelter.init();
            const result = await smelter.run();
            await smelter.close();

            log.success(`L3 Smelt 瀹屾垚锛岀啍鐐?${result.success || 0} 鍦篳);
            return { success: true, ...result };

        } catch (error) {
            log.error(`L3 Smelt 澶辫触: ${error.message}`);
            return { success: false, error: error.message };
        }
    }

    // ========================================================================
    // 闃舵 4: Recalculate Elo (鎴樺姏閲嶇畻) - 鍏抽敭闂幆锛?    // ========================================================================

    async runRecalculateElo() {
        log.section('闃舵 4/5: Recalculate Elo (鎴樺姏閲嶇畻)');

        if (this.dryRun) {
            log.info('[DRY-RUN] 璺宠繃 Elo 閲嶇畻');
            return { success: true, skipped: true };
        }

        try {
            // 妫€鏌ユ湁姣斿垎鐨勬瘮璧涙暟閲?            const pendingScores = await this._getMatchesWithScoresCount();
            log.info(`鏈夋瘮鍒嗙殑姣旇禌: ${pendingScores} 鍦篳);

            // 璋冪敤 Node 鑴氭湰閲嶇畻 Elo
            const result = await this._runEloRecalculation();

            log.success('Elo 閲嶇畻瀹屾垚');
            return { success: true, ...result };

        } catch (error) {
            log.error(`Elo 閲嶇畻澶辫触: ${error.message}`);
            return { success: false, error: error.message };
        }
    }

    /**
     * 鎵ц Elo 閲嶇畻鑴氭湰
     */
    async _runEloRecalculation() {
        return new Promise((resolve, reject) => {
            const args = [path.join(process.cwd(), 'scripts/maintenance/recalculate_elo.js'];

            log.info(`鎵ц: node ${args.join(' ')}`);

            const child = spawn('node', args, {
                env: process.env,
                cwd: '/app',
                stdio: 'inherit'
            });

            child.on('close', (code) => {
                if (code === 0) {
                    resolve({ exitCode: 0 });
                } else {
                    reject(new Error(`Elo 閲嶇畻鑴氭湰閫€鍑虹爜 ${code}`));
                }
            });

            child.on('error', (err) => {
                reject(err);
            });
        });
    }

    // ========================================================================
    // 闃舵 5: Predict (棰勬祴鐢熸垚)
    // ========================================================================

    async runPredict() {
        log.section('闃舵 5/5: Predict (棰勬祴鐢熸垚)');

        if (this.dryRun) {
            log.info('[DRY-RUN] 璺宠繃棰勬祴');
            return { success: true, skipped: true };
        }

        try {
            // 璋冪敤 Python 棰勬祴鑴氭湰
            const result = await this._runPythonPredictor();

            log.success('棰勬祴鐢熸垚瀹屾垚');
            return { success: true, ...result };

        } catch (error) {
            log.error(`棰勬祴鐢熸垚澶辫触: ${error.message}`);
            return { success: false, error: error.message };
        }
    }

    /**
     * 鎵ц Python 棰勬祴鑴氭湰
     */
    async _runPythonPredictor() {
        return new Promise((resolve, reject) => {
            const args = [
                path.join(process.cwd(), 'scripts/ops/predict_weekend.py',
                '--days', String(this.config.PREDICT_DAYS),
                '--save'
            ];

            log.info(`鎵ц: python ${args.join(' ')}`);

            const python = spawn('python', args, {
                env: process.env,
                cwd: '/app',
                stdio: 'inherit'
            });

            python.on('close', (code) => {
                if (code === 0) {
                    resolve({ exitCode: 0 });
                } else {
                    reject(new Error(`棰勬祴鑴氭湰閫€鍑虹爜 ${code}`));
                }
            });

            python.on('error', (err) => {
                reject(err);
            });
        });
    }

    // ========================================================================
    // 杈呭姪鏂规硶
    // ========================================================================

    async _getActiveLeagues() {
        const result = await this.pool.query(`
            SELECT DISTINCT
                SPLIT_PART(match_id, '_', 1) as id,
                league_name as name
            FROM matches
            WHERE match_date >= NOW() - INTERVAL '30 days'
        `);
        return result.rows;
    }

    async _getPendingL2Count() {
        const result = await this.pool.query(`
            SELECT COUNT(*) as count
            FROM matches m
            LEFT JOIN raw_match_data r ON m.match_id = r.match_id
            WHERE r.match_id IS NULL
              AND m.match_date < NOW()
        `);
        return parseInt(result.rows[0].count) || 0;
    }

    async _getPendingL3Count() {
        const result = await this.pool.query(`
            SELECT COUNT(*) as count
            FROM matches m
            JOIN raw_match_data r ON m.match_id = r.match_id
            LEFT JOIN l3_features f ON m.match_id = f.match_id
            WHERE r.raw_data IS NOT NULL
              AND f.match_id IS NULL
        `);
        return parseInt(result.rows[0].count) || 0;
    }

    async _getMatchesWithScoresCount() {
        const result = await this.pool.query(`
            SELECT COUNT(*) as count
            FROM matches
            WHERE home_score IS NOT NULL
              AND away_score IS NOT NULL
        `);
        return parseInt(result.rows[0].count) || 0;
    }

    _shouldRun(stage) {
        if (!this.onlyStages) return true;
        return this.onlyStages.includes(stage);
    }

    // ========================================================================
    // 涓昏繍琛屾柟娉?    // ========================================================================

    /**
     * 鎵ц瀹屾暣娴佹按绾?     * @param {Object} options - 鎵ц閫夐」
     */
    async run(options = {}) {
        const { loop = false, dryRun = false, only = null } = options;

        this.dryRun = dryRun;
        this.onlyStages = only ? only.split(',').map(s => s.trim().toLowerCase()) : null;

        const results = {};

        do {
            const startTime = Date.now();

            log.section('馃殌 V201.1 鍏ㄨ嚜鍔ㄦ祦姘寸嚎鍚姩');
            log.info(`寰幆妯″紡: ${loop}`);
            log.info(`棰勮妯″紡: ${dryRun}`);
            log.info(`鎸囧畾闃舵: ${only || '鍏ㄩ儴'}`);

            // 闃舵 1: L1 Discovery
            if (this._shouldRun('l1') || this._shouldRun('discovery')) {
                results.l1 = await this.runL1Discovery();
            }

            // 闃舵 2: L2 Harvest
            if (this._shouldRun('l2') || this._shouldRun('harvest')) {
                results.l2 = await this.runL2Harvest();
            }

            // 闃舵 3: L3 Smelt
            if (this._shouldRun('l3') || this._shouldRun('smelt')) {
                results.l3 = await this.runL3Smelt();
            }

            // 闃舵 4: Recalculate Elo - 鍏抽敭闂幆锛?            if (this._shouldRun('elo') || this._shouldRun('recalculate')) {
                results.elo = await this.runRecalculateElo();
            }

            // 闃舵 5: Predict
            if (this._shouldRun('predict')) {
                results.predict = await this.runPredict();
            }

            const elapsed = ((Date.now() - startTime) / 1000).toFixed(1);

            log.section('馃搳 娴佹按绾挎墽琛屽畬鎴?);
            log.success(`鎬昏€楁椂: ${elapsed}s`);
            log.info(`鎵ц缁撴灉: ${JSON.stringify(results, null, 2)}`);

            if (loop) {
                log.info(`绛夊緟 ${this.config.LOOP_INTERVAL_MS / 1000 / 60} 鍒嗛挓鍚庢墽琛屼笅涓€杞?..`);
                await new Promise(r => setTimeout(r, this.config.LOOP_INTERVAL_MS));
            }

        } while (loop);

        return results;
    }
}

// ============================================================================
// CLI 鍏ュ彛
// ============================================================================

async function main() {
    const args = process.argv.slice(2);

    const options = {
        loop: args.includes('--loop'),
        dryRun: args.includes('--dry-run'),
        only: null
    };

    // 瑙ｆ瀽 --only 鍙傛暟
    const onlyIdx = args.indexOf('--only');
    if (onlyIdx !== -1 && args[onlyIdx + 1]) {
        options.only = args[onlyIdx + 1];
    }

    // 瑙ｆ瀽 --interval 鍙傛暟
    const intervalIdx = args.indexOf('--interval');
    if (intervalIdx !== -1 && args[intervalIdx + 1]) {
        ORCHESTRATOR_CONFIG.LOOP_INTERVAL_MS = parseInt(args[intervalIdx + 1]);
    }

    const orchestrator = new AutonomousOrchestrator();

    try {
        await orchestrator.init();
        const results = await orchestrator.run(options);
        await orchestrator.close();

        // 妫€鏌ユ槸鍚︽湁澶辫触
        const hasFailure = Object.values(results).some(r => r && !r.success);
        process.exit(hasFailure ? 1 : 0);

    } catch (error) {
        log.error('娴佹按绾挎墽琛屽け璐?, error);
        await orchestrator.close();
        process.exit(1);
    }
}

// 杩愯
main();

