/**
 * TaskPool - 任务池管理器
 * ==============================================
 *
 * 负责:
 * - 从 PostgreSQL 提取任务
 * - 任务状态流转 (PENDING -> RUNNING -> COMPLETED)
 * - 重试队列管理
 * - 坏账清理
 *
 * @module core/scheduler/TaskPool
 * @version V174.0.0
 */

'use strict';

/**
 * TaskPool - 任务池管理器
 */
class TaskPool {
    /**
     * @param {import('pg').Client} dbClient - PostgreSQL 客户端
     * @param {Object} config - 配置选项
     */
    constructor(dbClient, config = {}) {
        this.client = dbClient;
        this.config = {
            minSizeBytes: config.minSizeBytes ?? 5000,
            maxRetries: config.maxRetries ?? 3,
            batchSize: config.batchSize ?? 1000,
            ...config
        };

        // 任务队列
        this.pendingQueue = [];
        this.retryQueue = [];
        this.completedSet = new Set();

        // 统计
        this.stats = {
            loaded: 0,
            completed: 0,
            failed: 0,
            retried: 0
        };
    }

    /**
     * 加载待处理任务
     * @param {Object} options - 加载选项
     * @returns {Promise<Array>} 任务列表
     */
    async loadTasks(options = {}) {
        const limit = options.limit ?? this.config.batchSize;

        const query = `
            SELECT
                m.match_id,
                m.external_id as fotmob_id,
                m.home_team,
                m.away_team,
                m.league_name,
                m.match_date,
                m.status
            FROM matches m
            LEFT JOIN raw_match_data r ON m.match_id = r.match_id
            WHERE m.external_id IS NOT NULL
              AND m.external_id <> ''
              AND m.external_id SIMILAR TO '[0-9]+'
              AND (r.raw_data IS NULL OR r.raw_data::text = '{}')
              AND (m.status = 'finished' OR m.status = 'completed' OR m.match_date < NOW())
            ORDER BY m.match_date DESC
            LIMIT $1
        `;

        try {
            const result = await this.client.query(query, [limit]);
            this.pendingQueue = result.rows;
            this.stats.loaded = this.pendingQueue.length;
            return this.pendingQueue;
        } catch (e) {
            throw new Error(`LOAD_TASKS_ERROR:${e.message}`);
        }
    }

    /**
     * 加载需要修复的任务 (数据质量不达标)
     * @returns {Promise<Array>}
     */
    async loadRepairTasks() {
        const query = `
            SELECT
                m.match_id,
                m.external_id as fotmob_id,
                m.home_team,
                m.away_team,
                m.league_name,
                m.match_date,
                m.status,
                LENGTH(r.raw_data::text) as current_size
            FROM matches m
            JOIN raw_match_data r ON m.match_id = r.match_id
            WHERE m.external_id IS NOT NULL
              AND m.external_id <> ''
              AND m.external_id ~ '^[0-9]+'
              AND LENGTH(r.raw_data::text) < $1
            ORDER BY m.match_date DESC
            LIMIT 100
        `;

        try {
            const result = await this.client.query(query, [this.config.minSizeBytes]);
            return result.rows;
        } catch (e) {
            throw new Error(`LOAD_REPAIR_ERROR:${e.message}`);
        }
    }

    /**
     * 清理坏账记录
     * @returns {Promise<number>} 删除的记录数
     */
    async cleanBadRecords() {
        const query = `
            DELETE FROM raw_match_data
            WHERE LENGTH(raw_data::text) < $1
            RETURNING match_id
        `;

        try {
            const result = await this.client.query(query, [this.config.minSizeBytes]);
            return result.rowCount;
        } catch (e) {
            throw new Error(`CLEAN_BAD_RECORDS_ERROR:${e.message}`);
        }
    }

    /**
     * 获取下一个任务
     * @returns {Object|null}
     */
    getNext() {
        // 优先从重试队列获取
        if (this.retryQueue.length > 0) {
            return this.retryQueue.shift();
        }

        // 从主队列获取
        if (this.pendingQueue.length > 0) {
            return this.pendingQueue.shift();
        }

        return null;
    }

    /**
     * 将任务放回队列 (重试)
     * @param {Object} task - 任务对象
     * @param {number} delay - 延迟时间 (ms)
     */
    requeue(task, delay = 0) {
        if (delay > 0) {
            setTimeout(() => {
                this.retryQueue.push(task);
                this.stats.retried++;
            }, delay);
        } else {
            this.retryQueue.unshift(task);  // 放到队首
            this.stats.retried++;
        }
    }

    /**
     * 标记任务完成
     * @param {string} matchId - 比赛 ID
     */
    markCompleted(matchId) {
        this.completedSet.add(matchId);
        this.stats.completed++;
    }

    /**
     * 标记任务失败
     * @param {string} matchId - 比赛 ID
     */
    markFailed(matchId) {
        this.stats.failed++;
    }

    /**
     * 检查是否还有任务
     * @returns {boolean}
     */
    hasMore() {
        return this.pendingQueue.length > 0 || this.retryQueue.length > 0;
    }

    /**
     * 获取剩余任务数
     * @returns {number}
     */
    getRemaining() {
        return this.pendingQueue.length + this.retryQueue.length;
    }

    /**
     * 获取统计信息
     * @returns {Object}
     */
    getStats() {
        return {
            ...this.stats,
            pending: this.pendingQueue.length,
            retry: this.retryQueue.length,
            completed: this.completedSet.size,
            remaining: this.getRemaining()
        };
    }

    /**
     * 重置统计
     */
    reset() {
        this.pendingQueue = [];
        this.retryQueue = [];
        this.completedSet.clear();
        this.stats = { loaded: 0, completed: 0, failed: 0, retried: 0 };
    }
}

module.exports = {
    TaskPool
};
