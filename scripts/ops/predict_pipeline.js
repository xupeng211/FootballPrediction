/**
 * PredictionPipeline - V200 棰勬祴娴佹按绾? * =====================================
 *
 * 鍦?L1/L2/L3 瀹屾垚鍚庤嚜鍔ㄧ敓鎴愰娴嬫姤鍛? * 璋冪敤 Python 棰勬祴鑴氭湰骞朵繚瀛樼粨鏋滃埌鏁版嵁搴? *
 * @module scripts/ops/predict_pipeline
 * @version V200.0.0
 */

'use strict';

const { spawn } = require('child_process');
const { Pool } = require('pg');

// ============================================================================
// 閰嶇疆甯搁噺
// ============================================================================

const PREDICT_CONFIG = {
    /** Python 鑴氭湰璺緞 */
    SCRIPT_PATH: path.join(process.cwd(), 'scripts/ops/predict_weekend.py',

    /** 棰勬祴澶╂暟 */
    PREDICT_DAYS: parseInt(process.env.PREDICT_DAYS || '4'),

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
        console.log(`[${timestamp()}] [SUCCESS] [PredictionPipeline] 鉁?${msg}${metaStr}`);
    }
};

// ============================================================================
// PredictionPipeline 绫?// ============================================================================

class PredictionPipeline {
    /**
     * 鍒涘缓 PredictionPipeline 瀹炰緥
     * @param {Object} options - 閰嶇疆閫夐」
     */
    constructor(options = {}) {
        this.config = { ...PREDICT_CONFIG, ...options };
        this.pool = null;
    }

    /**
     * 鍒濆鍖?     */
    async init() {
        log.info('馃殌 鍒濆鍖?PredictionPipeline V200...');

        this.pool = new Pool({
            ...this.config.db,
            max: 5,
            idleTimeoutMillis: 30000
        });

        // 娴嬭瘯杩炴帴
        const client = await this.pool.connect();
        await client.query('SELECT 1');
        client.release();
        log.info('鉁?鏁版嵁搴撹繛鎺ユ睜宸插氨缁?);
    }

    /**
     * 杩愯棰勬祴
     * @param {Object} options - 鎵ц閫夐」
     * @returns {Promise<Object>} 棰勬祴缁撴灉
     */
    async run(options = {}) {
        const { save = true, league = null } = options;

        log.info('鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺?);
        log.info('  V200 棰勬祴娴佹按绾?- 鎵ц棰勬祴');
        log.info('鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺?);

        const startTime = Date.now();

        try {
            // 璋冪敤 Python 棰勬祴鑴氭湰
            const result = await this._runPythonPredictor(save, league);

            // 瑙ｆ瀽棰勬祴缁撴灉
            const predictions = await this._parsePredictions(result);

            const elapsed = ((Date.now() - startTime) / 1000).toFixed(1);
            log.success(`棰勬祴瀹屾垚锛岃€楁椂 ${elapsed}s锛屽叡 ${predictions.length} 鍦烘瘮璧沗);

            // 鐢熸垚鎽樿鎶ュ憡
            const summary = this._generateSummary(predictions);
            this._printSummary(summary);

            return {
                success: true,
                predictions,
                summary,
                elapsed
            };

        } catch (error) {
            log.error('棰勬祴鎵ц澶辫触', error);
            return {
                success: false,
                error: error.message,
                predictions: []
            };
        }
    }

    /**
     * 璋冪敤 Python 棰勬祴鑴氭湰
     * @param {boolean} save - 鏄惁淇濆瓨鍒版暟鎹簱
     * @param {string|null} league - 鎸囧畾鑱旇禌
     * @returns {Promise<string>} 鑴氭湰杈撳嚭
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

            log.info(`鎵ц: python ${args.join(' ')}`);

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
                    reject(new Error(`Python 鑴氭湰閫€鍑虹爜 ${code}: ${stderr}`));
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
     * 瑙ｆ瀽棰勬祴杈撳嚭
     * @param {string} output - Python 鑴氭湰杈撳嚭
     * @returns {Promise<Array>} 棰勬祴鍒楄〃
     */
    async _parsePredictions(output) {
        // 浠庢暟鎹簱鑾峰彇鏈€鏂伴娴?        const query = `
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
     * 鐢熸垚鎽樿
     * @param {Array} predictions - 棰勬祴鍒楄〃
     * @returns {Object} 鎽樿
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
     * 鎵撳嵃鎽樿鎶ュ憡
     * @param {Object} summary - 鎽樿
     */
    _printSummary(summary) {
        log.info('鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺?);
        log.info('  馃搳 棰勬祴鎽樿鎶ュ憡');
        log.info('鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺?);
        log.info(`  鎬婚娴嬫暟: ${summary.total}`);
        log.info(`  楂樹环鍊兼姇娉?(EV > 5%): ${summary.highValue}`);

        if (summary.topPicks.length > 0) {
            log.info('\n  馃敟 Top 5 楂樹环鍊兼姇娉?');
            summary.topPicks.forEach((p, i) => {
                const ev = p.ev_home || 0;
                log.info(`    ${i + 1}. ${p.home_team} vs ${p.away_team} | ${p.recommended_bet || p.predicted_result} | EV: ${ev > 0 ? '+' : ''}${(ev * 100).toFixed(1)}%`);
            });
        }

        log.info('鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺?);
    }

    /**
     * 鍏抽棴杩炴帴
     */
    async close() {
        if (this.pool) {
            await this.pool.end();
            log.info('鉁?鏁版嵁搴撹繛鎺ユ睜宸插叧闂?);
        }
    }
}

// ============================================================================
// 瀵煎嚭
// ============================================================================

module.exports = {
    PredictionPipeline,
    PREDICT_CONFIG
};

