/**
 * RawDataQueries - 原始数据查询封装
 * ==============================================
 *
 * 封装所有与 raw_match_data 表相关的数据库操作
 * - 存储原始 JSON 数据
 * - 查询历史数据
 * - 数据清理
 *
 * @module models/RawDataQueries
 * @version V174.0.0
 */

'use strict';

/**
 * RawDataQueries - 原始数据查询类
 */
class RawDataQueries {
    /**
     * @param {import('pg').Client} client - PostgreSQL 客户端
     */
    constructor(client) {
        this.client = client;
    }

    /**
     * 存储原始 JSON 数据
     *
     * @param {string} matchId - 比赛 ID
     * @param {object} rawData - 原始数据对象
     * @param {string} column - 目标列名 (默认 raw_data)
     * @returns {Promise<boolean>}
     */
    async storeRawJson(matchId, rawData, column = 'raw_data') {
        const query = `
            INSERT INTO raw_match_data (match_id, ${column}, collected_at)
            VALUES ($1, $2::jsonb, NOW())
            ON CONFLICT (match_id) DO UPDATE SET
                ${column} = EXCLUDED.${column},
                collected_at = NOW()
        `;

        try {
            await this.client.query(query, [matchId, JSON.stringify(rawData)]);
            return true;
        } catch (e) {
            throw new Error(`STORE_RAW_ERROR:${e.message}`);
        }
    }

    /**
     * 获取原始 JSON 数据
     *
     * @param {string} matchId - 比赛 ID
     * @param {string} column - 目标列名
     * @returns {Promise<object|null>}
     */
    async getRawJson(matchId, column = 'raw_data') {
        const query = `
            SELECT ${column}, collected_at FROM raw_match_data WHERE match_id = $1
        `;

        try {
            const result = await this.client.query(query, [matchId]);
            if (result.rows[0]) {
                return {
                    data: result.rows[0][column],
                    collectedAt: result.rows[0].collected_at
                };
            }
            return null;
        } catch (e) {
            throw new Error(`GET_RAW_ERROR:${e.message}`);
        }
    }

    /**
     * 检查原始数据是否存在
     *
     * @param {string} matchId - 比赛 ID
     * @returns {Promise<boolean>}
     */
    async exists(matchId) {
        const query = `SELECT 1 FROM raw_match_data WHERE match_id = $1`;
        try {
            const result = await this.client.query(query, [matchId]);
            return result.rows.length > 0;
        } catch (e) {
            return false;
        }
    }

    /**
     * 删除原始数据
     *
     * @param {string} matchId - 比赛 ID
     * @returns {Promise<boolean>}
     */
    async delete(matchId) {
        const query = `DELETE FROM raw_match_data WHERE match_id = $1`;
        try {
            await this.client.query(query, [matchId]);
            return true;
        } catch (e) {
            throw new Error(`DELETE_RAW_ERROR:${e.message}`);
        }
    }

    /**
     * 获取过期的原始数据列表
     *
     * @param {number} daysOld - 过期天数
     * @param {number} limit - 限制数量
     * @returns {Promise<Array>}
     */
    async getExpired(daysOld = 30, limit = 100) {
        const query = `
            SELECT match_id, collected_at FROM raw_match_data
            WHERE collected_at < NOW() - INTERVAL '${daysOld} days'
            ORDER BY collected_at ASC
            LIMIT $1
        `;

        try {
            const result = await this.client.query(query, [limit]);
            return result.rows;
        } catch (e) {
            throw new Error(`GET_EXPIRED_ERROR:${e.message}`);
        }
    }

    /**
     * 清理过期的原始数据
     *
     * @param {number} daysOld - 过期天数
     * @returns {Promise<number>} 删除的记录数
     */
    async cleanupExpired(daysOld = 30) {
        const query = `
            DELETE FROM raw_match_data
            WHERE collected_at < NOW() - INTERVAL '${daysOld} days'
            RETURNING match_id
        `;

        try {
            const result = await this.client.query(query);
            return result.rows.length;
        } catch (e) {
            throw new Error(`CLEANUP_ERROR:${e.message}`);
        }
    }

    /**
     * 获取存储统计信息
     *
     * @returns {Promise<Object>}
     */
    async getStats() {
        const query = `
            SELECT
                COUNT(*) as total_records,
                COUNT(raw_data) as raw_records,
                MIN(collected_at) as oldest_record,
                MAX(collected_at) as newest_record
            FROM raw_match_data
        `;

        try {
            const result = await this.client.query(query);
            return result.rows[0];
        } catch (e) {
            throw new Error(`GET_STATS_ERROR:${e.message}`);
        }
    }

    /**
     * 批量存储原始数据
     *
     * @param {Array<{matchId: string, data: object}>} items - 数据列表
     * @returns {Promise<number>} 成功数量
     */
    async batchStore(items) {
        let successCount = 0;

        for (const item of items) {
            try {
                await this.storeRawJson(item.matchId, item.data);
                successCount++;
            } catch (e) {
                // 继续处理下一个
            }
        }

        return successCount;
    }
}

module.exports = {
    RawDataQueries
};
