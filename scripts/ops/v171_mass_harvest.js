/**
 * V171.001 Mass Harvest - 全自动流水线总闸
 * ============================================
 *
 * 从数据库 pending 池自动取件，完成：
 * 1. 自动取件：读取 status='pending' 的即将到来的比赛
 * 2. 自动寻址：C++ BridgeRadarEngine 补全 OddsPortal URL
 * 3. 全息收割：L2(FotMob) + L3(OddsPortal) 双源采集
 * 4. 大脑预测：MultiModelValidator 3 模型共识
 * 5. 任务闭环：更新 status='completed'
 *
 * Usage:
 *   node scripts/ops/v171_mass_harvest.js --limit 50
 *   node scripts/ops/v171_mass_harvest.js --limit 10 --dry-run
 *
 * @module scripts/ops/v171_mass_harvest
 * @version V171.001
 */

'use strict';

const path = require('path');
const { Client } = require('pg');
const { spawn } = require('child_process');

const PROJECT_ROOT = path.resolve(__dirname, '../..');

// ============================================================================
// CONFIGURATION
// ============================================================================

const CONFIG = {
    // 数据库配置
    database: {
        host: process.env.DB_HOST || 'db',
        port: parseInt(process.env.DB_PORT) || 5432,
        database: process.env.DB_NAME || 'football_db',
        user: process.env.DB_USER || 'football_user',
        password: process.env.DB_PASSWORD || 'football_pass'
    },

    // 收割配置
    harvest: {
        limit: 50,                    // 默认处理 50 场
        lookAheadHours: 168,          // 查找未来 7 天的比赛
        maxConcurrent: 3,             // 最大并发数
        retryAttempts: 2,             // 重试次数
        retryDelayMs: 5000            // 重试延迟
    },

    // C++ 模糊匹配配置
    fuzzyBridge: {
        enabled: true,
        minThreshold: 65.0,           // 最低相似度阈值
        highThreshold: 85.0           // 高置信度阈值
    },

    // 日志级别
    logLevel: process.env.LOG_LEVEL || 'info'
};

// ============================================================================
// LOGGER
// ============================================================================

class Logger {
    constructor(level = 'info') {
        this.level = level;
        this.levels = { debug: 0, info: 1, warn: 2, error: 3 };
    }

    _log(level, emoji, ...args) {
        if (this.levels[level] >= this.levels[this.level]) {
            const timestamp = new Date().toISOString().slice(11, 19);
            console.log(`[${timestamp}] ${emoji} ${level.toUpperCase()}`, ...args);
        }
    }

    debug(...args) { this._log('debug', '🔍', ...args); }
    info(...args) { this._log('info', 'ℹ️', ...args); }
    warn(...args) { this._log('warn', '⚠️', ...args); }
    error(...args) { this._log('error', '❌', ...args); }
    success(...args) { this._log('info', '✅', ...args); }
    alert(...args) { this._log('info', '🚨', ...args); }

    banner(title) {
        console.log('');
        console.log('═'.repeat(65));
        console.log(`  ${title}`);
        console.log('═'.repeat(65));
        console.log('');
    }

    section(title) {
        console.log('');
        console.log('─'.repeat(65));
        console.log(`  ${title}`);
        console.log('─'.repeat(65));
    }
}

// ============================================================================
// DATABASE MANAGER
// ============================================================================

class DatabaseManager {
    constructor(config, logger) {
        this.config = config;
        this.logger = logger;
        this.client = null;
    }

    async connect() {
        this.client = new Client(this.config);
        await this.client.connect();
        this.logger.info('数据库连接成功');
    }

    async disconnect() {
        if (this.client) {
            await this.client.end();
            this.client = null;
        }
    }

    /**
     * 获取待收割的比赛列表
     */
    async getPendingMatches(limit, lookAheadHours) {
        const result = await this.client.query(`
            SELECT
                match_id,
                home_team,
                away_team,
                league_name,
                match_date,
                EXTRACT(EPOCH FROM (match_date - NOW())) / 3600 as hours_until_kickoff,
                external_id as oddsportal_url
            FROM matches
            WHERE status = 'pending'
              AND is_finished = false
              AND match_date >= NOW()
              AND match_date <= NOW() + INTERVAL '1 hour' * $2
            ORDER BY match_date ASC
            LIMIT $1
        `, [limit, lookAheadHours]);

        return result.rows;
    }

    /**
     * 更新比赛的 OddsPortal URL (存储到 external_id)
     */
    async updateOddsPortalUrl(matchId, url, confidence) {
        await this.client.query(`
            UPDATE matches
            SET external_id = $2,
                updated_at = NOW()
            WHERE match_id = $1
        `, [matchId, url]);
    }

    /**
     * 标记比赛为已完成
     */
    async markCompleted(matchId, homeScore = null, awayScore = null) {
        await this.client.query(`
            UPDATE matches
            SET status = 'completed',
                is_finished = true,
                home_score = $2,
                away_score = $3,
                updated_at = NOW()
            WHERE match_id = $1
        `, [matchId, homeScore, awayScore]);
    }

    /**
     * 插入预测结果
     */
    async insertPrediction(prediction) {
        await this.client.query(`
            INSERT INTO predictions (
                match_id, predicted_result, final_confidence,
                model_version, home_win_prob, draw_prob, away_win_prob
            ) VALUES ($1, $2, $3, $4, $5, $6, $7)
            ON CONFLICT (match_id, model_version) DO UPDATE SET
                predicted_result = EXCLUDED.predicted_result,
                final_confidence = EXCLUDED.final_confidence,
                home_win_prob = EXCLUDED.home_win_prob,
                draw_prob = EXCLUDED.draw_prob,
                away_win_prob = EXCLUDED.away_win_prob,
                prediction_date = NOW()
        `, [
            prediction.match_id,
            prediction.predicted_result,
            prediction.final_confidence,
            prediction.model_version || 'V171.001',
            prediction.home_win_prob,
            prediction.draw_prob,
            prediction.away_win_prob
        ]);
    }

    /**
     * 插入基本面数据
     */
    async insertFundamentals(fundamentals) {
        await this.client.query(`
            INSERT INTO match_fundamentals (
                match_id, home_formation, away_formation,
                home_starters, away_starters,
                home_missing, away_missing,
                injuries, suspensions, market_value_gap
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
            ON CONFLICT (match_id) DO UPDATE SET
                home_formation = EXCLUDED.home_formation,
                away_formation = EXCLUDED.away_formation,
                home_starters = EXCLUDED.home_starters,
                away_starters = EXCLUDED.away_starters,
                home_missing = EXCLUDED.home_missing,
                away_missing = EXCLUDED.away_missing,
                injuries = EXCLUDED.injuries,
                suspensions = EXCLUDED.suspensions,
                market_value_gap = EXCLUDED.market_value_gap,
                updated_at = NOW()
        `, [
            fundamentals.match_id,
            fundamentals.home_formation,
            fundamentals.away_formation,
            JSON.stringify(fundamentals.home_starters || []),
            JSON.stringify(fundamentals.away_starters || []),
            JSON.stringify(fundamentals.home_missing || []),
            JSON.stringify(fundamentals.away_missing || []),
            JSON.stringify(fundamentals.injuries || []),
            JSON.stringify(fundamentals.suspensions || []),
            fundamentals.market_value_gap
        ]);
    }

    /**
     * 获取统计信息
     */
    async getStats() {
        const result = await this.client.query(`
            SELECT
                (SELECT COUNT(*) FROM matches WHERE status = 'pending') as pending,
                (SELECT COUNT(*) FROM matches WHERE status = 'completed') as completed,
                (SELECT COUNT(*) FROM predictions) as predictions,
                (SELECT COUNT(*) FROM match_fundamentals) as fundamentals
        `);
        return result.rows[0];
    }
}

// ============================================================================
// C++ FUZZY BRIDGE (Python Bridge 调用)
// ============================================================================

class CppFuzzyBridge {
    constructor(config, logger) {
        this.config = config;
        this.logger = logger;
        this.enabled = config.enabled;
    }

    /**
     * 调用 Python BridgeRadarEngine 进行动态 URL 寻址
     */
    async findOddsPortalUrl(match) {
        if (!this.enabled) {
            return { success: false, error: 'Fuzzy bridge disabled' };
        }

        this.logger.debug(`[C++ Bridge] 寻找 OddsPortal URL: ${match.home_team} vs ${match.away_team}`);

        // 转义单引号
        const homeTeam = match.home_team.replace(/'/g, "\\'");
        const awayTeam = match.away_team.replace(/'/g, "\\'");
        const leagueName = match.league_name.replace(/'/g, "\\'");

        const pythonScript = `
import sys
import json
sys.path.insert(0, '${PROJECT_ROOT}')

try:
    from src.utils.cpp_bridge_radar import BridgeRadarEngine, RadarQuery
    from datetime import datetime

    engine = BridgeRadarEngine()

    query = RadarQuery(
        match_id='${match.match_id}',
        home_team='${homeTeam}',
        away_team='${awayTeam}',
        league_name='${leagueName}',
        match_date=datetime.now(),
        min_threshold=${this.config.minThreshold}
    )

    # 尝试动态桥接
    url = engine.dynamic_bridge(query, verbose=False)

    if url:
        result = {
            'success': True,
            'url': url,
            'confidence': 85.0
        }
    else:
        result = {
            'success': False,
            'error': 'No matching URL found'
        }

    print(json.dumps(result))

except Exception as e:
    print(json.dumps({'success': False, 'error': str(e)}))
`;

        try {
            const result = await this._runPython(pythonScript);
            return result;
        } catch (error) {
            return { success: false, error: error.message };
        }
    }

    /**
     * 运行 Python 脚本
     */
    async _runPython(script) {
        return new Promise((resolve, reject) => {
            const proc = spawn('python3', ['-c', script], {
                cwd: PROJECT_ROOT,
                env: { ...process.env, PYTHONIOENCODING: 'utf-8' }
            });

            let stdout = '';
            let stderr = '';

            proc.stdout.on('data', (data) => { stdout += data.toString(); });
            proc.stderr.on('data', (data) => { stderr += data.toString(); });

            proc.on('close', (code) => {
                if (code !== 0) {
                    reject(new Error(`Python error: ${stderr || stdout}`));
                    return;
                }

                try {
                    const output = stdout.trim().split('\n').pop();
                    const result = JSON.parse(output);
                    resolve(result);
                } catch (e) {
                    reject(new Error(`Parse error: ${e.message}`));
                }
            });

            proc.on('error', reject);
        });
    }
}

// ============================================================================
// HARVEST ORCHESTRATOR
// ============================================================================

class HarvestOrchestrator {
    constructor(config, logger) {
        this.config = config;
        this.logger = logger;
        this.db = null;
        this.fuzzyBridge = null;
        this.quantHarvester = null;

        this.stats = {
            processed: 0,
            success: 0,
            failed: 0,
            predictions: 0,
            ssrAlerts: 0
        };
    }

    async initialize() {
        this.logger.banner('V171.001 全自动流水线总闸');
        this.logger.info('初始化组件...');

        // 初始化数据库
        this.db = new DatabaseManager(CONFIG.database, this.logger);
        await this.db.connect();

        // 初始化 C++ 模糊匹配桥接
        this.fuzzyBridge = new CppFuzzyBridge(CONFIG.fuzzyBridge, this.logger);
        this.logger.info(`C++ 模糊匹配: ${CONFIG.fuzzyBridge.enabled ? '启用' : '禁用'}`);

        // 初始化 QuantHarvester
        const { QuantHarvester } = require(path.join(PROJECT_ROOT, 'src/infrastructure/engines/QuantHarvester'));
        this.quantHarvester = new QuantHarvester({
            enableProxy: true,
            enablePythonBridge: true,
            logLevel: 'error'
        });

        await this.quantHarvester.init();
        this.logger.info('QuantHarvester 初始化完成');

        // 显示配置
        this.logger.section('收割配置');
        this.logger.info(`  处理上限: ${CONFIG.harvest.limit} 场`);
        this.logger.info(`  时间窗口: 未来 ${CONFIG.harvest.lookAheadHours} 小时`);
        this.logger.info(`  并发数: ${CONFIG.harvest.maxConcurrent}`);
        this.logger.info(`  重试次数: ${CONFIG.harvest.retryAttempts}`);
    }

    async shutdown() {
        this.logger.info('关闭组件...');

        if (this.quantHarvester) {
            await this.quantHarvester.shutdown();
        }

        if (this.db) {
            await this.db.disconnect();
        }

        this.logger.success('所有组件已关闭');
    }

    /**
     * 执行完整的收割流程
     */
    async run(limit, dryRun = false) {
        this.logger.section(`Step 1: 获取待收割任务 (limit=${limit})`);

        // 获取 pending 比赛
        const matches = await this.db.getPendingMatches(limit, CONFIG.harvest.lookAheadHours);

        if (matches.length === 0) {
            this.logger.warn('没有找到待收割的比赛');
            return;
        }

        this.logger.info(`找到 ${matches.length} 场待收割比赛:`);
        matches.forEach((m, i) => {
            const hours = parseFloat(m.hours_until_kickoff).toFixed(1);
            const urlStatus = m.oddsportal_url ? '✅' : '❓';
            this.logger.info(`  ${i + 1}. ${m.home_team} vs ${m.away_team} (${hours}h后) [URL: ${urlStatus}]`);
        });

        if (dryRun) {
            this.logger.warn('🔍 DRY RUN 模式 - 不执行实际收割');
            return;
        }

        // 批量处理
        this.logger.section('Step 2-5: 全息收割流水线');

        for (const match of matches) {
            await this._processMatch(match);
        }

        // 显示统计
        this._printStats();
    }

    /**
     * 处理单场比赛
     */
    async _processMatch(match) {
        const matchId = match.match_id;
        const matchLabel = `${match.home_team} vs ${match.away_team}`;

        this.logger.info('');
        this.logger.info(`🎯 处理: ${matchLabel} (${matchId})`);

        try {
            // Step 2: 自动寻址 (C++ Bridge)
            let oddsportalUrl = match.oddsportal_url;

            if (!oddsportalUrl) {
                this.logger.info('  [Step 2] C++ 自动寻址...');
                const bridgeResult = await this.fuzzyBridge.findOddsPortalUrl(match);

                if (bridgeResult.success) {
                    oddsportalUrl = bridgeResult.url;
                    await this.db.updateOddsPortalUrl(matchId, oddsportalUrl, bridgeResult.confidence || 0);
                    this.logger.success(`  ✅ 找到 URL: ${oddsportalUrl}`);
                } else {
                    this.logger.warn(`  ⚠️ 未找到 URL: ${bridgeResult.error}`);
                }
            } else {
                this.logger.info(`  [Step 2] URL 已存在: ${oddsportalUrl}`);
            }

            // Step 3: 全息收割 (L2 + L3)
            this.logger.info('  [Step 3] 全息收割...');

            const harvestResult = await this._harvestMatch(match, oddsportalUrl);

            if (!harvestResult.success) {
                throw new Error(`Harvest failed: ${harvestResult.error}`);
            }

            this.logger.success(`  ✅ 收割完成: ${harvestResult.dataPoints || 0} 数据点`);

            // Step 4: 大脑预测 (MultiModelValidator)
            this.logger.info('  [Step 4] 多模型预测...');

            const prediction = await this._runPrediction(match);

            if (prediction) {
                await this.db.insertPrediction(prediction);
                this.stats.predictions++;

                const confidence = (prediction.final_confidence * 100).toFixed(1);
                this.logger.success(`  ✅ 预测: ${prediction.predicted_result} (${confidence}%)`);

                // 检测 SSR 级预测
                if (prediction.is_ssr) {
                    this.stats.ssrAlerts++;
                    this.logger.alert(`  🚨 SSR 级预测! ${matchLabel}`);
                }
            }

            // Step 5: 任务闭环
            this.logger.info('  [Step 5] 任务闭环...');
            await this.db.markCompleted(matchId);
            this.logger.success(`  ✅ 状态更新: pending → completed`);

            this.stats.success++;

        } catch (error) {
            this.logger.error(`  ❌ 处理失败: ${error.message}`);
            this.stats.failed++;
        }

        this.stats.processed++;
    }

    /**
     * 执行收割
     */
    async _harvestMatch(match, oddsportalUrl) {
        if (!oddsportalUrl) {
            return { success: false, error: 'No OddsPortal URL available' };
        }

        try {
            const result = await this.quantHarvester.harvestMatch(oddsportalUrl, match.match_id);
            return result;
        } catch (error) {
            return { success: false, error: error.message };
        }
    }

    /**
     * 执行多模型预测
     */
    async _runPrediction(match) {
        // 转义单引号
        const leagueName = match.league_name.replace(/'/g, "\\'");

        const pythonScript = `
import sys
import json
sys.path.insert(0, '${PROJECT_ROOT}')

try:
    from src.ml.inference.multi_model_validator import MultiModelValidator

    validator = MultiModelValidator()
    validation = validator.validate_match(
        match_id='${match.match_id}',
        league_name='${leagueName}'
    )
    validator.close()

    result = {
        'match_id': '${match.match_id}',
        'predicted_result': validation.final_prediction,
        'final_confidence': float(validation.final_confidence),
        'home_win_prob': float(validation.home_win_prob) if hasattr(validation, 'home_win_prob') else 0.33,
        'draw_prob': float(validation.draw_prob) if hasattr(validation, 'draw_prob') else 0.33,
        'away_win_prob': float(validation.away_win_prob) if hasattr(validation, 'away_win_prob') else 0.33,
        'consensus_level': validation.consensus_level.value,
        'is_ssr': float(validation.final_confidence) >= 0.75 and validation.consensus_level.value == 'UNANIMOUS'
    }

    print(json.dumps(result))

except Exception as e:
    print(json.dumps({'success': False, 'error': str(e)}))
`;

        try {
            const result = await this._runPython(pythonScript);
            return result.success === false ? null : result;
        } catch (error) {
            this.logger.debug(`Prediction failed: ${error.message}`);
            return null;
        }
    }

    /**
     * 运行 Python 脚本
     */
    async _runPython(script) {
        return new Promise((resolve, reject) => {
            const proc = spawn('python3', ['-c', script], {
                cwd: PROJECT_ROOT,
                env: { ...process.env, PYTHONIOENCODING: 'utf-8' }
            });

            let stdout = '';
            proc.stdout.on('data', (data) => { stdout += data.toString(); });

            proc.on('close', (code) => {
                try {
                    const output = stdout.trim().split('\n').pop();
                    resolve(JSON.parse(output));
                } catch (e) {
                    reject(new Error(`Parse error: ${e.message}`));
                }
            });

            proc.on('error', reject);
        });
    }

    /**
     * 打印统计信息
     */
    async _printStats() {
        this.logger.section('收割统计');

        const dbStats = await this.db.getStats();

        this.logger.info(`  处理: ${this.stats.processed} 场`);
        this.logger.info(`  成功: ${this.stats.success} 场`);
        this.logger.info(`  失败: ${this.stats.failed} 场`);
        this.logger.info(`  预测: ${this.stats.predictions} 条`);
        this.logger.info(`  SSR 告警: ${this.stats.ssrAlerts} 次`);

        this.logger.info('');
        this.logger.info('数据库状态:');
        this.logger.info(`  Pending: ${dbStats.pending}`);
        this.logger.info(`  Completed: ${dbStats.completed}`);
        this.logger.info(`  Predictions: ${dbStats.predictions}`);
        this.logger.info(`  Fundamentals: ${dbStats.fundamentals}`);
    }
}

// ============================================================================
// MAIN
// ============================================================================

async function main() {
    // 解析命令行参数
    const args = process.argv.slice(2);
    const limitIndex = args.indexOf('--limit');
    const limit = limitIndex > -1 ? parseInt(args[limitIndex + 1]) || CONFIG.harvest.limit : CONFIG.harvest.limit;
    const dryRun = args.includes('--dry-run');

    const logger = new Logger(CONFIG.logLevel);
    const orchestrator = new HarvestOrchestrator(CONFIG, logger);

    // 优雅关闭
    process.on('SIGINT', async () => {
        logger.info('\n收到 SIGINT 信号...');
        await orchestrator.shutdown();
        process.exit(0);
    });

    process.on('SIGTERM', async () => {
        logger.info('\n收到 SIGTERM 信号...');
        await orchestrator.shutdown();
        process.exit(0);
    });

    try {
        await orchestrator.initialize();
        await orchestrator.run(limit, dryRun);
        await orchestrator.shutdown();

        logger.banner('V171.001 全自动流水线完成');
        process.exit(0);

    } catch (error) {
        logger.error(`Fatal error: ${error.message}`);
        await orchestrator.shutdown();
        process.exit(1);
    }
}

// 导出
module.exports = { HarvestOrchestrator, CONFIG };

// 运行
if (require.main === module) {
    main();
}
