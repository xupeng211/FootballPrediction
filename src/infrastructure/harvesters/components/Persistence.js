/**
 * Persistence - 数据持久化器
 * ==========================
 *
 * 负责数据的双保险持久化：
 * - 数据库存储（主存储，失败即抛错）
 * - 文件存储（辅助存储，失败不阻塞）
 *
 * @module infrastructure/harvesters/components/Persistence
 * @version V1.0.0
 */

'use strict';

const fs = require('fs').promises;
const path = require('path');

/**
 * 数据持久化器类
 */
class Persistence {
    /**
     * 创建 Persistence 实例
     * @param {object} config - 配置选项
     * @param {string} config.dataPath - 数据文件保存路径
     */
    constructor(config = {}) {
        this.dataPath = config.dataPath || 'data/matches';
        this._writePromises = [];
    }

    /**
     * 保存数据到数据库
     * @param {object} client - 数据库连接客户端
     * @param {string} matchId - 比赛 ID
     * @param {object} rawData - 原始数据对象
     * @returns {Promise<void>}
     * @throws {Error} 数据库保存失败时抛出
     */
    async saveToDatabase(client, matchId, rawData) {
        const query = `
            INSERT INTO raw_match_data (match_id, raw_data, collected_at)
            VALUES ($1, $2, NOW())
            ON CONFLICT (match_id)
            DO UPDATE SET raw_data = EXCLUDED.raw_data, collected_at = NOW()
        `;

        try {
            await client.query(query, [matchId, JSON.stringify(rawData)]);
        } catch (dbErr) {
            const errType = this._classifyDatabaseError(dbErr);
            throw new Error(`${errType} 数据库保存失败 [${matchId}]: ${dbErr.message}`);
        }
    }

    /**
     * 异步保存数据到文件（双保险模式）
     * @param {string} matchId - 比赛 ID
     * @param {object} rawData - 原始数据对象
     * @param {object} metadata - 额外元数据
     * @returns {Promise<string>} 保存的文件路径
     */
    async saveToFile(matchId, rawData, metadata = {}) {
        const dataDir = path.resolve(process.cwd(), this.dataPath);
        const filePath = path.join(dataDir, `${matchId}.json`);

        // 确保目录存在
        await fs.mkdir(dataDir, { recursive: true });

        // 构建保存数据结构
        const dataToSave = {
            match_id: matchId,
            raw_data: rawData,
            saved_at: new Date().toISOString(),
            source: metadata.source || 'ProductionHarvester',
            worker_id: metadata.workerId || 'unknown',
            ...metadata
        };

        await fs.writeFile(filePath, JSON.stringify(dataToSave, null, 2));

        return filePath;
    }

    /**
     * 执行双保险保存（数据库 + 文件）
     * @param {object} pool - 数据库连接池
     * @param {string} matchId - 比赛 ID
     * @param {object} rawData - 原始数据
     * @param {object} metadata - 元数据
     * @returns {Promise<{dbSuccess: boolean, filePath: string|null}>}
     */
    async dualSave(pool, matchId, rawData, metadata = {}) {
        const result = {
            dbSuccess: false,
            filePath: null
        };

        // 1. 数据库保存（主存储，失败即抛错）
        const client = await pool.connect();
        try {
            await this.saveToDatabase(client, matchId, rawData);
            result.dbSuccess = true;
        } finally {
            client.release();
        }

        // 2. 文件保存（辅助存储，失败不阻塞）
        this.saveToFile(matchId, rawData, metadata).then(
            filePath => {
                result.filePath = filePath;
                console.log(`[SAVE-FILE] ✓ ${matchId}.json 已保存`);
            },
            err => {
                const errorType = this._classifyFileError(err);
                console.error(`[SAVE-FILE] ${errorType} ${matchId} 保存失败: ${err.message}`);
            }
        );

        return result;
    }

    /**
     * 检查文件是否已存在
     * @param {string} matchId - 比赛 ID
     * @returns {Promise<boolean>}
     */
    async fileExists(matchId) {
        const filePath = path.join(path.resolve(process.cwd(), this.dataPath), `${matchId}.json`);
        try {
            await fs.access(filePath);
            return true;
        } catch {
            return false;
        }
    }

    /**
     * 从文件加载数据
     * @param {string} matchId - 比赛 ID
     * @returns {Promise<object|null>}
     */
    async loadFromFile(matchId) {
        const filePath = path.join(path.resolve(process.cwd(), this.dataPath), `${matchId}.json`);
        try {
            const content = await fs.readFile(filePath, 'utf8');
            return JSON.parse(content);
        } catch {
            return null;
        }
    }

    /**
     * 删除文件
     * @param {string} matchId - 比赛 ID
     * @returns {Promise<boolean>}
     */
    async deleteFile(matchId) {
        const filePath = path.join(path.resolve(process.cwd(), this.dataPath), `${matchId}.json`);
        try {
            await fs.unlink(filePath);
            return true;
        } catch {
            return false;
        }
    }

    /**
     * 数据库错误分类器
     * @private
     * @param {Error} error - 数据库错误对象
     * @returns {string} 错误类型标记
     */
    _classifyDatabaseError(error) {
        const code = error.code;
        const message = error.message.toLowerCase();

        if (code === 'ECONNREFUSED' || code === 'ETIMEDOUT' || message.includes('connect')) {
            return '[DB-NETWORK]';
        }
        if (code === '28P01' || message.includes('authentication') || message.includes('password')) {
            return '[DB-AUTH]';
        }
        if (code === '23505') {
            return '[DB-DUPLICATE]';
        }
        if (code === '42P01') {
            return '[DB-TABLE-NOT-FOUND]';
        }
        return '[DB-ERROR]';
    }

    /**
     * 文件错误分类器
     * @private
     * @param {Error} error - 错误对象
     * @returns {string} 错误类型标记
     */
    _classifyFileError(error) {
        const message = error.message.toLowerCase();
        if (message.includes('enoent')) return '[FILE-NOT-FOUND]';
        if (message.includes('eacces') || message.includes('permission')) return '[PERMISSION]';
        if (message.includes('enospc')) return '[DISK-FULL]';
        return '[FILE-ERROR]';
    }

    /**
     * 获取存储统计
     * @returns {object}
     */
    getStats() {
        return {
            dataPath: this.dataPath,
            pendingWrites: this._writePromises.length
        };
    }
}

module.exports = { Persistence };
