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
const { Normalizer } = require('../../../utils/Normalizer');

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
        this._writePromises = new Set();
        this.logger = config.logger || console;
        this.autoSchemaSync = config.autoSchemaSync !== false;
        this._matchesColumns = null;
        this._pipelineStatusColumn = null;
    }

    /**
     * 保存数据到数据库 (V6.6 硬化版本)
     * @param {object} client - 数据库连接客户端
     * @param {string} leagueId - 联赛 ID
     * @param {string} season - 赛季 (如 '2023/2024' 或 '2324')
     * @param {string} externalId - 外部数据源 ID
     * @param {object} rawData - 原始数据对象
     * @returns {Promise<string>} 标准化的 match_id
     * @throws {Error} 数据库保存失败或数据验证失败时抛出
     */
    async saveToDatabase(client, leagueId, season, externalId, rawData) {
        // V6.6: 使用 Normalizer 构建标准化 match_id
        const normalizedSeason = Normalizer.normalizeSeason(season);
        const matchId = Normalizer.buildMatchId(leagueId, normalizedSeason, externalId);

        // V6.6: 预检 match_id 格式
        if (!Normalizer.isValidMatchId(matchId)) {
            throw new Error(`[VALIDATION] match_id 格式非法: ${matchId}`);
        }

        // V6.6: 预检 raw_data 非空
        if (!rawData || Object.keys(rawData).length === 0) {
            throw new Error(`[VALIDATION] raw_data 不能为空: ${matchId}`);
        }

        const query = `
            INSERT INTO raw_match_data (match_id, raw_data, collected_at, data_version, external_id)
            VALUES ($1, $2, NOW(), $3, $4)
            ON CONFLICT (match_id)
            DO UPDATE SET 
                raw_data = EXCLUDED.raw_data, 
                collected_at = NOW(),
                data_version = EXCLUDED.data_version
        `;

        try {
            await client.query(query, [
                matchId, 
                JSON.stringify(rawData), 
                'V26.1',  // V6.6: 固定数据版本
                externalId
            ]);
            return matchId;
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

        // 构建保存数据结构 (V6.6: 包含 data_version)
        const dataToSave = {
            match_id: matchId,
            raw_data: rawData,
            saved_at: new Date().toISOString(),
            data_version: 'V26.1',  // V6.6: 固定数据版本
            source: metadata.source || 'ProductionHarvester',
            worker_id: metadata.workerId || 'unknown',
            ...metadata
        };

        await fs.writeFile(filePath, JSON.stringify(dataToSave, null, 2));

        return filePath;
    }

    /**
     * 执行双保险保存（数据库 + 文件）V6.6 硬化版本
     * @param {object} pool - 数据库连接池
     * @param {string} leagueId - 联赛 ID
     * @param {string} season - 赛季
     * @param {string} externalId - 外部数据源 ID
     * @param {object} rawData - 原始数据
     * @param {object} metadata - 元数据
     * @returns {Promise<{dbSuccess: boolean, filePath: string|null, matchId: string}>}
     */
    async dualSave(pool, leagueId, season, externalId, rawData, metadata = {}) {
        const result = {
            dbSuccess: false,
            filePath: null,
            matchId: null
        };

        // 1. 数据库保存（主存储，失败即抛错）
        const client = await pool.connect();
        try {
            await client.query('BEGIN');
            const matchId = await this.saveToDatabase(client, leagueId, season, externalId, rawData);
            await this._syncMatchPipelineState(client, matchId, rawData);
            await client.query('COMMIT');
            result.dbSuccess = true;
            result.matchId = matchId;
        } catch (error) {
            try {
                await client.query('ROLLBACK');
            } catch (rollbackError) {
                this.logger.warn?.(`[Persistence] ROLLBACK 失败: ${rollbackError.message}`);
            }
            throw error;
        } finally {
            this._safeReleaseClient(client);
        }

        // 2. 文件保存（辅助存储，失败不阻塞）
        const writePromise = this.saveToFile(result.matchId, rawData, metadata).then(
            filePath => {
                result.filePath = filePath;
                console.log(`[SAVE-FILE] ✓ ${result.matchId}.json 已保存`);
            },
            err => {
                const errorType = this._classifyFileError(err);
                console.error(`[SAVE-FILE] ${errorType} ${result.matchId} 保存失败: ${err.message}`);
            }
        ).finally(() => {
            this._writePromises.delete(writePromise);
        });
        this._writePromises.add(writePromise);

        return result;
    }

    async flushPendingWrites() {
        if (this._writePromises.size === 0) {
            return { pending: 0, settled: 0 };
        }

        const pendingWrites = Array.from(this._writePromises);
        await Promise.allSettled(pendingWrites);

        return {
            pending: pendingWrites.length,
            settled: pendingWrites.length
        };
    }

    /**
     * 确保 matches 表具备 pipeline_status 列；若无法添加则回退到 status。
     * @param {object} dbHandle - 数据库 client 或 pool
     * @returns {Promise<'pipeline_status'|'status'>}
     */
    async ensurePipelineStatusSchema(dbHandle) {
        const { client, release } = await this._acquireClient(dbHandle);
        try {
            return await this._ensurePipelineStatusSchemaWithClient(client);
        } finally {
            release();
        }
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
            pendingWrites: this._writePromises.size
        };
    }

    async _syncMatchPipelineState(client, matchId, rawData) {
        const statusColumn = await this._ensurePipelineStatusSchemaWithClient(client);
        const columns = await this._getMatchesColumns(client);

        const assignments = [`${statusColumn} = $2`, 'updated_at = NOW()'];
        const values = [matchId, 'harvested'];

        if (columns.has('l2_collected_at')) {
            assignments.push('l2_collected_at = NOW()');
        }

        if (columns.has('l2_data_version')) {
            values.push('V26.1');
            assignments.push(`l2_data_version = $${values.length}`);
        }

        if (columns.has('l2_raw_json')) {
            values.push(JSON.stringify(rawData));
            assignments.push(`l2_raw_json = $${values.length}::jsonb`);
        }

        await client.query(
            `UPDATE matches SET ${assignments.join(', ')} WHERE match_id = $1`,
            values
        );
    }

    async _ensurePipelineStatusSchemaWithClient(client) {
        if (this._pipelineStatusColumn) {
            return this._pipelineStatusColumn;
        }

        let columns = await this._getMatchesColumns(client);
        if (columns.has('pipeline_status')) {
            this._pipelineStatusColumn = 'pipeline_status';
            return this._pipelineStatusColumn;
        }

        if (this.autoSchemaSync) {
            try {
                await client.query(`
                    ALTER TABLE matches
                    ADD COLUMN IF NOT EXISTS pipeline_status VARCHAR(20) DEFAULT 'pending'
                `);
                await client.query(`
                    CREATE INDEX IF NOT EXISTS idx_matches_pipeline_status
                    ON matches(pipeline_status)
                `);
                await client.query(`
                    UPDATE matches m
                    SET pipeline_status = CASE
                        WHEN r.match_id IS NOT NULL THEN 'harvested'
                        ELSE COALESCE(m.pipeline_status, 'pending')
                    END,
                    updated_at = NOW()
                    FROM (
                        SELECT match_id
                        FROM raw_match_data
                    ) r
                    WHERE m.match_id = r.match_id
                       OR m.pipeline_status IS NULL
                `);
                this._matchesColumns = null;
                columns = await this._getMatchesColumns(client, { force: true });
                if (columns.has('pipeline_status')) {
                    this._pipelineStatusColumn = 'pipeline_status';
                    return this._pipelineStatusColumn;
                }
            } catch (error) {
                this.logger.warn?.(`[Persistence] 自动补齐 pipeline_status 失败，回退 status: ${error.message}`);
            }
        }

        this._pipelineStatusColumn = 'status';
        return this._pipelineStatusColumn;
    }

    async _getMatchesColumns(client, options = {}) {
        if (this._matchesColumns && !options.force) {
            return this._matchesColumns;
        }

        const result = await client.query(
            `
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = $1
                  AND column_name = ANY($2)
                ORDER BY column_name
            `,
            ['matches', [
                'status',
                'pipeline_status',
                'updated_at',
                'l2_collected_at',
                'l2_data_version',
                'l2_raw_json'
            ]]
        );

        this._matchesColumns = new Set(result.rows.map(row => row.column_name));
        return this._matchesColumns;
    }

    async _acquireClient(dbHandle) {
        if (dbHandle && typeof dbHandle.connect === 'function') {
            const client = await dbHandle.connect();
            return {
                client,
                release: () => this._safeReleaseClient(client)
            };
        }

        if (dbHandle && typeof dbHandle.query === 'function') {
            return {
                client: dbHandle,
                release: () => {}
            };
        }

        throw new Error('[Persistence] 无法获取数据库连接');
    }

    _safeReleaseClient(client) {
        if (!client || typeof client.release !== 'function') {
            return;
        }

        try {
            client.release();
        } catch (releaseError) {
            this.logger.warn?.(`[Persistence] 释放数据库连接失败: ${releaseError.message}`);
        }
    }
}

module.exports = { Persistence };
