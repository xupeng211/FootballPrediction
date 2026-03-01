/**
 * MatchQueries - 比赛数据查询封装
 * ==============================================
 *
 * 封装所有与 matches 表相关的数据库操作
 * - 更新 xG 数据
 * - 查询比赛信息
 * - 批量操作
 *
 * @module models/MatchQueries
 * @version V174.0.0
 */

'use strict';

/**
 * MatchQueries - 比赛数据查询类
 */
class MatchQueries {
    /**
     * @param {import('pg').Client} client - PostgreSQL 客户端
     */
    constructor(client) {
        this.client = client;
    }

    /**
     * 更新比赛的 xG 数据
     *
     * @param {string} matchId - 比赛 ID
     * @param {number|null} xgHome - 主队 xG
     * @param {number|null} xgAway - 客队 xG
     * @returns {Promise<boolean>} 是否更新成功
     */
    async updateXG(matchId, xgHome, xgAway) {
        const query = `
            UPDATE matches SET
                xg_home = $2,
                xg_away = $3,
                updated_at = NOW()
            WHERE match_id = $1
        `;

        try {
            await this.client.query(query, [matchId, xgHome, xgAway]);
            return true;
        } catch (e) {
            throw new Error(`UPDATE_XG_ERROR:${e.message}`);
        }
    }

    /**
     * 更新比赛的完整统计数据
     *
     * @param {string} matchId - 比赛 ID
     * @param {Object} stats - 统计数据
     * @param {number|null} stats.xg_home - 主队 xG
     * @param {number|null} stats.xg_away - 客队 xG
     * @param {number|null} stats.possession_home - 主队控球率
     * @param {number|null} stats.possession_away - 客队控球率
     * @returns {Promise<boolean>}
     */
    async updateStats(matchId, stats) {
        const query = `
            UPDATE matches SET
                xg_home = $2,
                xg_away = $3,
                possession_home = $4,
                possession_away = $5,
                updated_at = NOW()
            WHERE match_id = $1
        `;

        try {
            await this.client.query(query, [
                matchId,
                stats.xg_home ?? null,
                stats.xg_away ?? null,
                stats.possession_home ?? null,
                stats.possession_away ?? null
            ]);
            return true;
        } catch (e) {
            throw new Error(`UPDATE_STATS_ERROR:${e.message}`);
        }
    }

    /**
     * 根据 ID 查询比赛
     *
     * @param {string} matchId - 比赛 ID
     * @returns {Promise<Object|null>} 比赛记录或 null
     */
    async findById(matchId) {
        const query = `
            SELECT * FROM matches WHERE match_id = $1
        `;

        try {
            const result = await this.client.query(query, [matchId]);
            return result.rows[0] || null;
        } catch (e) {
            throw new Error(`FIND_MATCH_ERROR:${e.message}`);
        }
    }

    /**
     * 根据 external_id 查询比赛
     *
     * @param {string} externalId - 外部 ID
     * @returns {Promise<Object|null>}
     */
    async findByExternalId(externalId) {
        const query = `
            SELECT * FROM matches WHERE external_id = $1
        `;

        try {
            const result = await this.client.query(query, [externalId]);
            return result.rows[0] || null;
        } catch (e) {
            throw new Error(`FIND_BY_EXTERNAL_ERROR:${e.message}`);
        }
    }

    /**
     * 获取待收割的比赛列表
     *
     * @param {Object} options - 查询选项
     * @param {number} options.limit - 限制数量
     * @param {string[]} options.statuses - 比赛状态列表
     * @returns {Promise<Array>} 比赛列表
     */
    async getPendingHarvest(options = {}) {
        const limit = options.limit ?? 50;
        const statuses = options.statuses ?? ['completed', 'finished'];

        const query = `
            SELECT * FROM matches
            WHERE status = ANY($1)
            AND xg_home IS NULL
            ORDER BY match_time DESC
            LIMIT $2
        `;

        try {
            const result = await this.client.query(query, [statuses, limit]);
            return result.rows;
        } catch (e) {
            throw new Error(`GET_PENDING_ERROR:${e.message}`);
        }
    }

    /**
     * 批量更新 xG 数据
     *
     * @param {Array<{matchId: string, xgHome: number|null, xgAway: number|null}>} updates - 更新列表
     * @returns {Promise<number>} 成功更新的数量
     */
    async batchUpdateXG(updates) {
        let successCount = 0;

        for (const update of updates) {
            try {
                await this.updateXG(update.matchId, update.xgHome, update.xgAway);
                successCount++;
            } catch (e) {
                // 继续处理下一个
            }
        }

        return successCount;
    }

    /**
     * 检查比赛是否存在
     *
     * @param {string} matchId - 比赛 ID
     * @returns {Promise<boolean>}
     */
    async exists(matchId) {
        const query = `SELECT 1 FROM matches WHERE match_id = $1`;
        try {
            const result = await this.client.query(query, [matchId]);
            return result.rows.length > 0;
        } catch (e) {
            return false;
        }
    }

    /**
     * 获取比赛的收割状态
     *
     * @param {string} matchId - 比赛 ID
     * @returns {Promise<Object|null>} 收割状态信息
     */
    async getHarvestStatus(matchId) {
        const query = `
            SELECT
                match_id,
                xg_home,
                xg_away,
                updated_at,
                CASE
                    WHEN xg_home IS NOT NULL THEN 'harvested'
                    ELSE 'pending'
                END as status
            FROM matches
            WHERE match_id = $1
        `;

        try {
            const result = await this.client.query(query, [matchId]);
            return result.rows[0] || null;
        } catch (e) {
            throw new Error(`GET_HARVEST_STATUS_ERROR:${e.message}`);
        }
    }
}

module.exports = {
    MatchQueries
};
