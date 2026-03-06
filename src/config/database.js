/**
 * 数据库配置中心 - V3.0-PRO
 * ==========================================
 *
 * 提供数据库连接池管理，包括：
 * 1. 环境变量读取
 * 2. 连接池配置
 * 3. 指数退避重试逻辑
 * 4. 健康检查
 *
 * @module config/database
 * @version V3.0.0-PRO
 * @since 2026-03-06
 */

'use strict';

const { Pool } = require('pg');
const {
    DB_MAX_RETRIES,
    DB_RETRY_DELAY_MS,
    DB_RETRY_BACKOFF_MULTIPLIER,
    DB_CONNECTION_TIMEOUT_MS
} = require('./constants');

// ============================================================================
// 数据库配置
// ============================================================================

/**
 * 数据库连接配置
 * 从环境变量读取，提供默认值
 *
 * @constant {Object}
 */
const DB_CONFIG = Object.freeze({
    host: process.env.DB_HOST || 'db',
    port: parseInt(process.env.DB_PORT || '5432', 10),
    database: process.env.DB_NAME || 'football_db',
    user: process.env.DB_USER || 'football_user',
    password: process.env.DB_PASSWORD || '',

    // 连接池配置
    pool: {
        max: parseInt(process.env.DB_POOL_MAX || '10', 10),
        min: parseInt(process.env.DB_POOL_MIN || '2', 10),
        idle: parseInt(process.env.DB_POOL_IDLE_MS || '10000', 10),
        acquire: parseInt(process.env.DB_POOL_ACQUIRE_MS || '30000', 10)
    },

    // 超时配置
    connectionTimeoutMillis: parseInt(process.env.DB_CONNECTION_TIMEOUT_MS || String(DB_CONNECTION_TIMEOUT_MS), 10),
    queryTimeout: parseInt(process.env.DB_QUERY_TIMEOUT_MS || '60000', 10),

    // SSL 配置
    ssl: process.env.DB_SSL === 'true' ? { rejectUnauthorized: false } : false
});

// ============================================================================
// 连接池单例
// ============================================================================

/** @type {Pool|null} */
let poolInstance = null;

/**
 * 获取数据库连接池单例
 *
 * @returns {Pool} PostgreSQL 连接池实例
 * @throws {Error} 如果无法建立连接
 */
function getPool() {
    if (poolInstance) {
        return poolInstance;
    }

    poolInstance = new Pool({
        host: DB_CONFIG.host,
        port: DB_CONFIG.port,
        database: DB_CONFIG.database,
        user: DB_CONFIG.user,
        password: DB_CONFIG.password,
        max: DB_CONFIG.pool.max,
        min: DB_CONFIG.pool.min,
        idleTimeoutMillis: DB_CONFIG.pool.idle,
        connectionTimeoutMillis: DB_CONFIG.connectionTimeoutMillis
    });

    // 错误处理
    poolInstance.on('error', (err) => {
        console.error({
            timestamp: new Date().toISOString(),
            level: 'error',
            component: 'DatabasePool',
            message: 'Unexpected database pool error',
            error: err.message,
            stack: err.stack
        });
    });

    return poolInstance;
}

// ============================================================================
// 重试逻辑
// ============================================================================

/**
 * 使用指数退避策略执行数据库操作
 *
 * @template T
 * @param {Function} operation - 要执行的异步操作函数
 * @param {string} operationName - 操作名称（用于日志）
 * @param {Object} [options] - 重试选项
 * @param {number} [options.maxRetries] - 最大重试次数
 * @param {number} [options.initialDelayMs] - 初始延迟（毫秒）
 * @param {number} [options.backoffMultiplier] - 退避乘数
 * @returns {Promise<T>} 操作结果
 * @throws {Error} 如果所有重试都失败
 *
 * @example
 * const result = await withRetry(
 *     async (client) => client.query('SELECT * FROM matches'),
 *     'fetchMatches'
 * );
 */
async function withRetry(operation, operationName, options = {}) {
    const {
        maxRetries = DB_MAX_RETRIES,
        initialDelayMs = DB_RETRY_DELAY_MS,
        backoffMultiplier = DB_RETRY_BACKOFF_MULTIPLIER
    } = options;

    let lastError = null;
    let delayMs = initialDelayMs;

    for (let attempt = 1; attempt <= maxRetries; attempt++) {
        try {
            const pool = getPool();
            const result = await operation(pool);
            return result;
        } catch (error) {
            lastError = error;

            // 判断是否为可重试错误
            const isRetryable = isRetryableError(error);
            if (!isRetryable || attempt === maxRetries) {
                break;
            }

            console.warn({
                timestamp: new Date().toISOString(),
                level: 'warn',
                component: 'DatabaseRetry',
                operation: operationName,
                attempt: `${attempt}/${maxRetries}`,
                error: error.message,
                nextRetryIn: `${delayMs}ms`
            });

            // 等待后重试
            await sleep(delayMs);
            delayMs = Math.min(delayMs * backoffMultiplier, 30000); // 最大 30 秒
        }
    }

    // 所有重试都失败
    const finalError = new Error(
        `Database operation "${operationName}" failed after ${maxRetries} attempts: ${lastError?.message}`
    );
    finalError.cause = lastError;
    throw finalError;
}

/**
 * 判断错误是否可重试
 *
 * @param {Error} error - 错误对象
 * @returns {boolean} 是否可重试
 */
function isRetryableError(error) {
    const retryableCodes = [
        '08006', // Connection failure
        '08001', // Unable to connect
        '08004', // Server rejected the connection
        '53000', // Insufficient resources
        '53200', // Out of memory
        '54000', // Program limit exceeded
        '55006', // Object in use
        '55P03', // Lock not available
        '57P03', // Cannot connect now
        'ECONNRESET', // Connection reset
        'ETIMEDOUT', // Connection timed out
        'ECONNREFUSED' // Connection refused
    ];

    const errorCode = error?.code || '';
    return retryableCodes.includes(errorCode) ||
           retryableCodes.includes(error?.errno?.toString()) ||
           error?.message?.includes('Connection') ||
           error?.message?.includes('timeout') ||
           error?.message?.includes('ECONNREFUSED');
}

/**
 * 异步睡眠
 *
 * @param {number} ms - 睡眠时间（毫秒）
 * @returns {Promise<void>}
 */
function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

// ============================================================================
// 健康检查
// ============================================================================

/**
 * 检查数据库连接健康状态
 *
 * @returns {Promise<{healthy: boolean, latency: number, error?: string}>}
 */
async function checkHealth() {
    const startTime = Date.now();

    try {
        const pool = getPool();
        const result = await pool.query('SELECT 1 as health_check');
        const latency = Date.now() - startTime;

        return {
            healthy: result.rows?.[0]?.health_check === 1,
            latency,
            timestamp: new Date().toISOString()
        };
    } catch (error) {
        const latency = Date.now() - startTime;
        return {
            healthy: false,
            latency,
            error: error.message,
            timestamp: new Date().toISOString()
        };
    }
}

// ============================================================================
// 查询辅助函数
// ============================================================================

/**
 * 执行参数化查询（带重试）
 *
 * @param {string} sql - SQL 查询语句
 * @param {Array} [params] - 查询参数
 * @param {string} [queryName] - 查询名称（用于日志）
 * @returns {Promise<import('pg').QueryResult>}
 */
async function query(sql, params = [], queryName = 'unnamed_query') {
    return withRetry(
        async (pool) => pool.query(sql, params),
        queryName
    );
}

/**
 * 执行事务
 *
 * @param {Function} transactionFn - 事务函数，接收 client 参数
 * @param {string} [transactionName] - 事务名称
 * @returns {Promise<any>} 事务结果
 */
async function transaction(transactionFn, transactionName = 'unnamed_transaction') {
    return withRetry(async (pool) => {
        const client = await pool.connect();
        try {
            await client.query('BEGIN');
            const result = await transactionFn(client);
            await client.query('COMMIT');
            return result;
        } catch (error) {
            await client.query('ROLLBACK');
            throw error;
        } finally {
            client.release();
        }
    }, transactionName);
}

// ============================================================================
// 关闭连接池
// ============================================================================

/**
 * 优雅关闭数据库连接池
 *
 * @returns {Promise<void>}
 */
async function closePool() {
    if (poolInstance) {
        console.info({
            timestamp: new Date().toISOString(),
            level: 'info',
            component: 'DatabasePool',
            message: 'Closing database connection pool'
        });

        await poolInstance.end();
        poolInstance = null;

        console.info({
            timestamp: new Date().toISOString(),
            level: 'info',
            component: 'DatabasePool',
            message: 'Database connection pool closed'
        });
    }
}

// ============================================================================
// 导出
// ============================================================================

module.exports = {
    DB_CONFIG,
    getPool,
    withRetry,
    query,
    transaction,
    checkHealth,
    closePool,
    isRetryableError,
    sleep
};
