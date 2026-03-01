/**
 * Core Utils - 核心工具模块索引
 * ==============================================
 *
 * 统一导出所有工具函数，提供简洁的导入路径。
 *
 * @module core/utils
 * @version V175.0.0
 *
 * @example
 * const { getDbClient, safeGet, is } = require('./core/utils');
 */

'use strict';

const DbClient = require('./DbClient');
const SafeAccess = require('./SafeAccess');

module.exports = {
    // 数据库工具
    getDbClient: DbClient.getDbClient,
    closeDbClient: DbClient.closeDbClient,
    getDbConfig: DbClient.getDbConfig,
    DB_CONFIG: DbClient.DB_CONFIG,

    // 安全访问工具
    safeGet: SafeAccess.safeGet,
    hasPath: SafeAccess.hasPath,
    safeArrayGet: SafeAccess.safeArrayGet,
    is: SafeAccess.is
};
