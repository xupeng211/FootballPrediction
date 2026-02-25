/**
 * FundamentalHarvester - V171.000
 * ================================
 *
 * 基本面数据收割器 - 整合多源数据采集
 *
 * Data Sources:
 * - FotMob API: 首发阵容、伤停名单、球队身价
 * - Transfermarkt: 球员身价、转会信息
 * - 内部缓存: 已采集数据
 *
 * Output Schema:
 * {
 *   match_id: string,
 *   home_squad: { formation, starters, missing_players, market_value },
 *   away_squad: { formation, starters, missing_players, market_value },
 *   injuries: [{ player, team, reason, expected_return }],
 *   suspensions: [{ player, team, reason, matches_missed }],
 *   market_value_gap: number (home_mv - away_mv in EUR)
 * }
 *
 * @module engines/FundamentalHarvester
 * @version V171.000
 */

'use strict';

const path = require('path');
const { Client } = require('pg');

// V172: 使用统一数据库配置
const { DatabaseConfig } = require(path.resolve(__dirname, '../../../config/database'));

const PROJECT_ROOT = path.resolve(__dirname, '../..');

// ============================================================================
// CONFIGURATION
// ============================================================================

const CONFIG = {
    fotmob: {
        baseUrl: 'https://www.fotmob.com/api',
        endpoints: {
            matchDetails: '/matchDetails',
            teamSquad: '/teams',
            playerStats: '/player'
        },
        timeout: 30000
    },
    cache: {
        ttl: 3600000, // 1 hour
        maxSize: 1000
    }
};

// ============================================================================
// FUNDAMENTAL HARVESTER
// ============================================================================

class FundamentalHarvester {
    /**
     * 创建基本面收割器
     * @param {Object} options - 配置选项
     */
    constructor(options = {}) {
        this.options = {
            enableCache: options.enableCache !== false,
            logLevel: options.logLevel || 'info'
        };

        this._cache = new Map();
        this._conn = null;

        this.logger = {
            info: (msg) => console.log(`[FundamentalHarvester] ${msg}`),
            warn: (msg) => console.warn(`[FundamentalHarvester] ⚠️ ${msg}`),
            error: (msg) => console.error(`[FundamentalHarvester] ❌ ${msg}`)
        };
    }

    // ========================================================================
    // DATABASE
    // ========================================================================

    async _getConnection() {
        if (!this._conn || this._conn.closed) {
            this._conn = new Client({
                host: DatabaseConfig.host,
                port: DatabaseConfig.port,
                database: DatabaseConfig.database,
                user: DatabaseConfig.user,
                password: DatabaseConfig.password
            });
            await this._conn.connect();
        }
        return this._conn;
    }

    async close() {
        if (this._conn && !this._conn.closed) {
            await this._conn.end();
            this._conn = null;
        }
    }

    // ========================================================================
    // FOTMOB API
    // ========================================================================

    /**
     * 从 FotMob 获取比赛详情（包含阵容、伤停）
     * @param {string} matchId - FotMob match ID
     * @returns {Promise<Object>} 比赛详情
     */
    async fetchFotMobMatchDetails(matchId) {
        const httpx = require('httpx');
        const url = `${CONFIG.fotmob.baseUrl}${CONFIG.fotmob.endpoints.matchDetails}?matchId=${matchId}`;

        try {
            const response = await httpx.request(url, {
                timeout: CONFIG.fotmob.timeout,
                headers: {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                    'Accept': 'application/json',
                    'Origin': 'https://www.fotmob.com',
                    'Referer': 'https://www.fotmob.com/'
                }
            });

            if (response.statusCode !== 200) {
                throw new Error(`FotMob API error: ${response.statusCode}`);
            }

            const data = JSON.parse(response.data.toString());
            return this._parseFotMobData(data, matchId);

        } catch (error) {
            this.logger.error(`FotMob fetch failed: ${error.message}`);
            throw error;
        }
    }

    /**
     * 解析 FotMob 数据
     * @private
     */
    _parseFotMobData(data, matchId) {
        const result = {
            match_id: matchId,
            home_squad: null,
            away_squad: null,
            injuries: [],
            suspensions: [],
            market_value_gap: null
        };

        try {
            // 提取阵容数据
            const content = data.content || {};

            // 查找 lineup 数据
            const lineupData = this._findLineupData(content);

            if (lineupData) {
                result.home_squad = {
                    formation: lineupData.home?.formation || null,
                    starters: this._extractPlayers(lineupData.home?.lineup || []),
                    missing_players: this._extractPlayers(lineupData.home?.missingPlayers || [])
                };

                result.away_squad = {
                    formation: lineupData.away?.formation || null,
                    starters: this._extractPlayers(lineupData.away?.lineup || []),
                    missing_players: this._extractPlayers(lineupData.away?.missingPlayers || [])
                };
            }

            // 提取伤停数据
            result.injuries = this._extractInjuries(content);
            result.suspensions = this._extractSuspensions(content);

            // 计算身价差距
            const homeValue = this._extractMarketValue(content, 'home');
            const awayValue = this._extractMarketValue(content, 'away');
            if (homeValue && awayValue) {
                result.market_value_gap = homeValue - awayValue;
            }

        } catch (error) {
            this.logger.warn(`Failed to parse FotMob data: ${error.message}`);
        }

        return result;
    }

    /**
     * 查找阵容数据
     * @private
     */
    _findLineupData(content, depth = 0) {
        if (depth > 8 || !content || typeof content !== 'object') {
            return null;
        }

        // 检查当前层级
        if (content.home && content.away &&
            (content.home.lineup || content.away.lineup)) {
            return content;
        }

        // 递归搜索
        for (const key of Object.keys(content)) {
            if (typeof content[key] === 'object') {
                const found = this._findLineupData(content[key], depth + 1);
                if (found) return found;
            }
        }

        return null;
    }

    /**
     * 提取球员列表
     * @private
     */
    _extractPlayers(lineup) {
        if (!Array.isArray(lineup)) return [];

        return lineup.map(p => ({
            player_id: p.id || p.playerId || null,
            name: p.name || p.playerName || 'Unknown',
            position: p.position || p.role || null,
            shirt_number: p.shirtNumber || p.number || null,
            rating: p.rating || null
        })).filter(p => p.name && p.name !== 'Unknown');
    }

    /**
     * 提取伤病数据
     * @private
     */
    _extractInjuries(content) {
        const injuries = [];

        // 递归查找 missingPlayers 和 injury 数据
        const search = (obj, depth = 0) => {
            if (depth > 10 || !obj || typeof obj !== 'object') return;

            if (Array.isArray(obj.missingPlayers)) {
                for (const p of obj.missingPlayers) {
                    if (p.reason && p.reason.toLowerCase().includes('injur')) {
                        injuries.push({
                            player: p.name || 'Unknown',
                            team: p.teamName || null,
                            reason: p.reason || 'Injury',
                            expected_return: p.expectedReturn || null
                        });
                    }
                }
            }

            for (const key of Object.keys(obj)) {
                if (typeof obj[key] === 'object') {
                    search(obj[key], depth + 1);
                }
            }
        };

        search(content);
        return injuries;
    }

    /**
     * 提取停赛数据
     * @private
     */
    _extractSuspensions(content) {
        const suspensions = [];

        const search = (obj, depth = 0) => {
            if (depth > 10 || !obj || typeof obj !== 'object') return;

            if (Array.isArray(obj.missingPlayers)) {
                for (const p of obj.missingPlayers) {
                    const reason = (p.reason || '').toLowerCase();
                    if (reason.includes('susp') || reason.includes('red card') || reason.includes('ban')) {
                        suspensions.push({
                            player: p.name || 'Unknown',
                            team: p.teamName || null,
                            reason: p.reason || 'Suspension',
                            matches_missed: p.matchesMissed || null
                        });
                    }
                }
            }

            for (const key of Object.keys(obj)) {
                if (typeof obj[key] === 'object') {
                    search(obj[key], depth + 1);
                }
            }
        };

        search(content);
        return suspensions;
    }

    /**
     * 提取市场价值
     * @private
     */
    _extractMarketValue(content, side) {
        const search = (obj, depth = 0) => {
            if (depth > 10 || !obj || typeof obj !== 'object') return null;

            // 查找 squadMarketValue 或 marketValue
            if (obj.squadMarketValue) {
                return this._parseMarketValue(obj.squadMarketValue);
            }
            if (obj.marketValue) {
                return this._parseMarketValue(obj.marketValue);
            }

            for (const key of Object.keys(obj)) {
                if (typeof obj[key] === 'object') {
                    const found = search(obj[key], depth + 1);
                    if (found) return found;
                }
            }

            return null;
        };

        // 查找主队/客队数据
        const sideData = content[side] || {};
        return search(sideData) || search(content);
    }

    /**
     * 解析市值字符串
     * @private
     */
    _parseMarketValue(valueStr) {
        if (typeof valueStr === 'number') return valueStr;
        if (typeof valueStr !== 'string') return null;

        // 解析 "€123.4M" 格式
        const match = valueStr.match(/€?([\d.]+)\s*([MBK]?)/i);
        if (!match) return null;

        const num = parseFloat(match[1]);
        const unit = (match[2] || '').toUpperCase();

        switch (unit) {
            case 'B': return num * 1e9;
            case 'M': return num * 1e6;
            case 'K': return num * 1e3;
            default: return num;
        }
    }

    // ========================================================================
    // PYTHON LINEUP COLLECTOR
    // ========================================================================

    /**
     * 调用 Python LineupCollector
     * @param {string} matchId - 比赛 ID
     * @returns {Promise<Object>} 阵容数据
     */
    async callPythonLineupCollector(matchId) {
        const { spawn } = require('child_process');

        return new Promise((resolve, reject) => {
            const script = `
import sys
import json
sys.path.insert(0, '${PROJECT_ROOT.replace(/\\/g, '/')}')

try:
    from src.collectors.lineup_collector import LineupCollector

    collector = LineupCollector()
    result = collector.collect_lineup('${matchId}')

    if result:
        output = {
            'success': True,
            'data': result.to_dict() if hasattr(result, 'to_dict') else result
        }
    else:
        output = {'success': False, 'error': 'No data returned'}

    print(json.dumps(output))

except Exception as e:
    print(json.dumps({'success': False, 'error': str(e)}))
    sys.exit(1)
`;

            const python = spawn('python3', ['-c', script], {
                cwd: PROJECT_ROOT,
                env: { ...process.env, PYTHONIOENCODING: 'utf-8' }
            });

            let stdout = '';
            let stderr = '';

            python.stdout.on('data', (data) => { stdout += data.toString(); });
            python.stderr.on('data', (data) => { stderr += data.toString(); });

            python.on('close', (code) => {
                if (code !== 0) {
                    reject(new Error(`Python error: ${stderr}`));
                    return;
                }

                try {
                    const result = JSON.parse(stdout.trim().split('\n').pop());
                    if (result.success) {
                        resolve(result.data);
                    } else {
                        reject(new Error(result.error || 'Unknown error'));
                    }
                } catch (e) {
                    reject(new Error(`Parse error: ${e.message}`));
                }
            });

            python.on('error', reject);
        });
    }

    // ========================================================================
    // DATABASE STORAGE
    // ========================================================================

    /**
     * 存储基本面数据到数据库
     * @param {Object} data - 基本面数据
     */
    async saveToDatabase(data) {
        const conn = await this._getConnection();

        try {
            // 存储到 match_fundamentals 表
            await conn.query(`
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
                data.match_id,
                data.home_squad?.formation || null,
                data.away_squad?.formation || null,
                JSON.stringify(data.home_squad?.starters || []),
                JSON.stringify(data.away_squad?.starters || []),
                JSON.stringify(data.home_squad?.missing_players || []),
                JSON.stringify(data.away_squad?.missing_players || []),
                JSON.stringify(data.injuries || []),
                JSON.stringify(data.suspensions || []),
                data.market_value_gap
            ]);

            this.logger.info(`Saved fundamentals for match: ${data.match_id}`);

        } catch (error) {
            // 如果表不存在，创建表
            if (error.code === '42P01') {
                await this._createFundamentalsTable(conn);
                await this.saveToDatabase(data);
            } else {
                throw error;
            }
        }
    }

    /**
     * 创建基本面数据表
     * @private
     */
    async _createFundamentalsTable(conn) {
        await conn.query(`
            CREATE TABLE IF NOT EXISTS match_fundamentals (
                match_id VARCHAR(50) PRIMARY KEY,
                home_formation VARCHAR(10),
                away_formation VARCHAR(10),
                home_starters JSONB,
                away_starters JSONB,
                home_missing JSONB,
                away_missing JSONB,
                injuries JSONB,
                suspensions JSONB,
                market_value_gap NUMERIC,
                created_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP DEFAULT NOW()
            )
        `);
        this.logger.info('Created match_fundamentals table');
    }

    // ========================================================================
    // MAIN HARVEST METHOD
    // ========================================================================

    /**
     * 采集比赛基本面数据
     * @param {string} matchId - 比赛 ID
     * @param {Object} options - 选项
     * @returns {Promise<Object>} 基本面数据
     */
    async harvest(matchId, options = {}) {
        this.logger.info(`Harvesting fundamentals for: ${matchId}`);

        let data = null;

        // 优先使用 Python LineupCollector（更成熟）
        try {
            data = await this.callPythonLineupCollector(matchId);
            this.logger.info(`Got data from Python LineupCollector`);
        } catch (error) {
            this.logger.warn(`Python collector failed: ${error.message}`);

            // 回退到 FotMob API
            try {
                data = await this.fetchFotMobMatchDetails(matchId);
                this.logger.info(`Got data from FotMob API`);
            } catch (error2) {
                this.logger.error(`FotMob API also failed: ${error2.message}`);
                throw new Error(`All data sources failed for ${matchId}`);
            }
        }

        // 存储到数据库
        if (data && options.saveToDb !== false) {
            await this.saveToDatabase(data);
        }

        return data;
    }

    /**
     * 批量采集
     * @param {string[]} matchIds - 比赛 ID 列表
     * @returns {Promise<Object[]>} 基本面数据列表
     */
    async harvestBatch(matchIds) {
        const results = [];

        for (const matchId of matchIds) {
            try {
                const data = await this.harvest(matchId);
                results.push({ matchId, success: true, data });
            } catch (error) {
                results.push({ matchId, success: false, error: error.message });
            }
        }

        return results;
    }
}

// ============================================================================
// EXPORTS
// ============================================================================

module.exports = { FundamentalHarvester };
