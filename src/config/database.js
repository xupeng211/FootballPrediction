/**
 * V4.46.2 数据库配置与连接池管理 (src/config)
 * =============================================
 *
 * 提供数据库连接池和重试逻辑
 *
 * @module config/database
 * @version V4.46.2
 */

'use strict';

const { Pool } = require('pg');

// ============================================================================
// 数据库配置
// ============================================================================

const DB_CONFIG = {
    host: process.env.DB_HOST || 'localhost',
    port: parseInt(process.env.DB_PORT) || 5432,
    database: process.env.DB_NAME || 'football_db',
    user: process.env.DB_USER || 'football_user',
    password: process.env.DB_PASSWORD,
    max: 20,
    idleTimeoutMillis: 30000,
    connectionTimeoutMillis: 5000
};

// ============================================================================
// 连接池单例
// ============================================================================

let pool = null;

/**
 * 获取数据库连接池
 * @returns {Pool}
 */
function getPool() {
    if (!pool) {
        pool = new Pool(DB_CONFIG);

        pool.on('error', (err) => {
            console.error('[DB] 连接池错误:', err.message);
        });
    }
    return pool;
}

/**
 * 带重试的数据库操作
 * @param {Function} operation - 要执行的数据库操作
 * @param {number} maxRetries - 最大重试次数
 * @param {number} delayMs - 初始延迟毫秒
 * @returns {Promise<any>}
 */
async function withRetry(operation, maxRetries = 3, delayMs = 1000) {
    let lastError;

    for (let attempt = 1; attempt <= maxRetries; attempt++) {
        try {
            return await operation();
        } catch (error) {
            lastError = error;

            if (!isRetryableError(error)) {
                throw error;
            }

            if (attempt < maxRetries) {
                const backoffDelay = delayMs * Math.pow(2, attempt - 1);
                console.log(`[DB] 重试 ${attempt}/${maxRetries}，等待 ${backoffDelay}ms...`);
                await new Promise(resolve => setTimeout(resolve, backoffDelay));
            }
        }
    }

    throw lastError;
}

/**
 * 检查错误是否可重试
 * @param {Error} error
 * @returns {boolean}
 */
function isRetryableError(error) {
    const retryableCodes = [
        'ECONNRESET',
        'ECONNREFUSED',
        'ETIMEDOUT',
        '57P01', // admin_shutdown
        '57P02', // crash_shutdown
        '57P03', // cannot_connect_now
        '08006', // connection_failure
        '08001', // sqlclient_unable_to_establish_sqlconnection
    ];

    return retryableCodes.some(code =>
        error.code === code ||
        (error.message && error.message.includes(code))
    );
}

/**
 * 检查数据库健康状态
 * @returns {Promise<{healthy: boolean, latency?: number, error?: string}>}
 */
async function checkHealth() {
    const startTime = Date.now();

    try {
        const client = await getPool().connect();
        await client.query('SELECT 1');
        client.release();

        return {
            healthy: true,
            latency: Date.now() - startTime
        };
    } catch (error) {
        return {
            healthy: false,
            error: error.message
        };
    }
}

/**
 * 关闭连接池
 */
async function closePool() {
    if (pool) {
        await pool.end();
        pool = null;
        console.log('[DB] 连接池已关闭');
    }
}

// ============================================================================
// 导出
// ============================================================================

module.exports = {
    getPool,
    withRetry,
    isRetryableError,
    checkHealth,
    closePool,
    DB_CONFIG
};
