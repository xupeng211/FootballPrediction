/**
 * DbClient - 统一数据库连接管理器
 * ==============================================
 *
 * 提供单例模式的数据库连接管理，避免重复初始化。
 *
 * @module core/utils/DbClient
 * @version V175.0.0
 */

'use strict';

const { Client } = require('pg');

/**
 * 数据库配置
 */
const DB_CONFIG = {
    host: process.env.DB_HOST || 'host.docker.internal',
    port: parseInt(process.env.DB_PORT) || 5432,
    database: process.env.DB_NAME || 'football_db',
    user: process.env.DB_USER || 'football_user',
    password: process.env.DB_PASSWORD || 'football_pass',
    connectionTimeoutMillis: parseInt(process.env.DB_CONNECT_TIMEOUT) || 10000,
    query_timeout: parseInt(process.env.DB_QUERY_TIMEOUT) || 30000
};

/** @type {Client|null} */
let _instance = null;

/**
 * 获取数据库客户端单例
 * @returns {Promise<Client>}
 */
async function getDbClient() {
    if (_instance) {
        return _instance;
    }

    _instance = new Client(DB_CONFIG);
    await _instance.connect();
    return _instance;
}

/**
 * 关闭数据库连接
 * @returns {Promise<void>}
 */
async function closeDbClient() {
    if (_instance) {
        await _instance.end();
        _instance = null;
    }
}

/**
 * 获取数据库配置（只读）
 * @returns {Readonly<typeof DB_CONFIG>}
 */
function getDbConfig() {
    return { ...DB_CONFIG };
}

module.exports = {
    getDbClient,
    closeDbClient,
    getDbConfig,
    DB_CONFIG
};
