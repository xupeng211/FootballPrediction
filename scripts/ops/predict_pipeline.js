/**
 * PredictionPipeline - V200 预测流水线
 * =====================================
 *
 * 在 L1/L2/L3 完成后自动生成预测报告
 * 调用 Python 预测脚本并保存结果到数据库
 *
 * @module scripts/ops/predict_pipeline
 * @version V200.0.0
 */

'use strict';

const { spawn } = require('child_process');
const { Pool } = require('pg');

// ============================================================================
// 配置常量
// ============================================================================

const PREDICT_CONFIG = {
    /** Python 脚本路径 */
    SCRIPT_PATH: '/app/scripts/ops/predict_weekend.py',

    /** 预测天数 */
    PREDICT_DAYS: parseInt(process.env.PREDICT_DAYS || '4'),

    /** 数据库配置 */
    db: {
        host: process.env.DB_HOST || 'localhost',
        port: parseInt(process.env.DB_PORT || '5432'),
        database: process.env.DB_NAME || 'football_db',
        user: process.env.DB_USER || 'football_user',
        password: process.env.DB_PASSWORD || ''
    }
};

// ============================================================================
// 日志系统
// ============================================================================

function timestamp() {
    return new Date().toISOString();
}

const log = {
    info: (msg, meta = null) => {
        const metaStr = meta ? ` | ${JSON.stringify(meta)}` : '';
        console.log(`[${timestamp()}] [INFO] [PredictionPipeline] ${msg}${metaStr}`);
    },
    warn: (msg, meta = null) => {
        const metaStr = meta ? ` | ${JSON.stringify(meta)}` : '';
        console.warn(`[${timestamp()}] [WARN] [PredictionPipeline] ${msg}${metaStr}`);
    },
    error: (msg, error = null) => {
        const meta = error ? { error: error.message, stack: error.stack } : {};
        console.error(`[${timestamp()}] [ERROR] [PredictionPipeline] ${msg}`, meta);
    },
    success: (msg, meta = null) => {
        const metaStr = meta ? ` | ${JSON.stringify(meta)}` : '';
        console.log(`[${timestamp()}] [SUCCESS] [PredictionPipeline] ✅ ${msg}${metaStr}`);
    }
};

// ============================================================================
// PredictionPipeline 类
// ============================================================================

class PredictionPipeline {
    /**
     * 创建 PredictionPipeline 实例
     * @param {Object} options - 配置选项
     */
    constructor(options = {}) {
        this.config = { ...PREDICT_CONFIG, ...options };
        this.pool = null;
    }

    /**
     * 初始化
     */
    async init() {
        log.info('🚀 初始化 PredictionPipeline V200...');

        this.pool = new Pool({
            ...this.config.db,
            max: 5,
            idleTimeoutMillis: 30000
        });

        // 测试连接
        const client = await this.pool.connect();
        await client.query('SELECT 1');
        client.release();
        log.info('✅ 数据库连接池已就绪');
    }

    /**
     * 运行预测
     * @param {Object} options - 执行选项
     * @returns {Promise<Object>} 预测结果
     */
    async run(options = {}) {
        const { save = true, league = null } = options;

        log.info('═══════════════════════════════════════════════════════════════');
        log.info('  V200 预测流水线 - 执行预测');
        log.info('═══════════════════════════════════════════════════════════════');

        const startTime = Date.now();

        try {
            // 调用 Python 预测脚本
            const result = await this._runPythonPredictor(save, league);

            // 解析预测结果
            const predictions = await this._parsePredictions(result);

            const elapsed = ((Date.now() - startTime) / 1000).toFixed(1);
            log.success(`预测完成，耗时 ${elapsed}s，共 ${predictions.length} 场比赛`);

            // 生成摘要报告
            const summary = this._generateSummary(predictions);
            this._printSummary(summary);

            return {
                success: true,
                predictions,
                summary,
                elapsed
            };

        } catch (error) {
            log.error('预测执行失败', error);
            return {
                success: false,
                error: error.message,
                predictions: []
            };
        }
    }

    /**
     * 调用 Python 预测脚本
     * @param {boolean} save - 是否保存到数据库
     * @param {string|null} league - 指定联赛
     * @returns {Promise<string>} 脚本输出
     */
    async _runPythonPredictor(save, league) {
        return new Promise((resolve, reject) => {
            const args = [
                this.config.SCRIPT_PATH,
                '--days', String(this.config.PREDICT_DAYS)
            ];

            if (save) {
                args.push('--save');
            }

            if (league) {
                args.push('--league', league);
            }

            log.info(`执行: python ${args.join(' ')}`);

            const python = spawn('python', args, {
                env: process.env,
                cwd: '/app'
            });

            let stdout = '';
            let stderr = '';

            python.stdout.on('data', (data) => {
                stdout += data.toString();
            });

            python.stderr.on('data', (data) => {
                stderr += data.toString();
            });

            python.on('close', (code) => {
                if (code !== 0) {
                    reject(new Error(`Python 脚本退出码 ${code}: ${stderr}`));
                } else {
                    resolve(stdout);
                }
            });

            python.on('error', (err) => {
                reject(err);
            });
        });
    }

    /**
     * 解析预测输出
     * @param {string} output - Python 脚本输出
     * @returns {Promise<Array>} 预测列表
     */
    async _parsePredictions(output) {
        // 从数据库获取最新预测
        const query = `
            SELECT
                p.match_id,
                m.home_team,
                m.away_team,
                m.league_name,
                m.match_date,
                p.predicted_result,
                p.final_confidence as confidence,
                p.confidence_home as prob_home,
                p.confidence_draw as prob_draw,
                p.confidence_away as prob_away,
                p.edge as ev_home,
                p.edge as ev_draw,
                p.edge as ev_away,
                p.model_version,
                p.recommended_bet
            FROM predictions p
            JOIN matches m ON p.match_id = m.match_id
            WHERE p.prediction_date > NOW() - INTERVAL '1 hour'
            ORDER BY p.edge DESC
        `;

        const result = await this.pool.query(query);
        return result.rows;
    }

    /**
     * 生成摘要
     * @param {Array} predictions - 预测列表
     * @returns {Object} 摘要
     */
    _generateSummary(predictions) {
        const highValue = predictions.filter(p => (p.ev_home || 0) > 0.05);

        const byLeague = {};
        predictions.forEach(p => {
            if (!byLeague[p.league_name]) {
                byLeague[p.league_name] = [];
            }
            byLeague[p.league_name].push(p);
        });

        return {
            total: predictions.length,
            highValue: highValue.length,
            byLeague,
            topPicks: highValue.slice(0, 5)
        };
    }

    /**
     * 打印摘要报告
     * @param {Object} summary - 摘要
     */
    _printSummary(summary) {
        log.info('═══════════════════════════════════════════════════════════════');
        log.info('  📊 预测摘要报告');
        log.info('═══════════════════════════════════════════════════════════════');
        log.info(`  总预测数: ${summary.total}`);
        log.info(`  高价值投注 (EV > 5%): ${summary.highValue}`);

        if (summary.topPicks.length > 0) {
            log.info('\n  🔥 Top 5 高价值投注:');
            summary.topPicks.forEach((p, i) => {
                const ev = p.ev_home || 0;
                log.info(`    ${i + 1}. ${p.home_team} vs ${p.away_team} | ${p.recommended_bet || p.predicted_result} | EV: ${ev > 0 ? '+' : ''}${(ev * 100).toFixed(1)}%`);
            });
        }

        log.info('═══════════════════════════════════════════════════════════════');
    }

    /**
     * 关闭连接
     */
    async close() {
        if (this.pool) {
            await this.pool.end();
            log.info('✅ 数据库连接池已关闭');
        }
    }
}

// ============================================================================
// 导出
// ============================================================================

module.exports = {
    PredictionPipeline,
    PREDICT_CONFIG
};
