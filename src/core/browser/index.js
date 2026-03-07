/**
 * 浏览器管理模块入口
 * @module core/browser
 * @version V4.20 - 合并 browser-pool 功能
 */

'use strict';

const { BrowserManager } = require('./BrowserManager');
const { StealthInjector, getDefaultStealthScript } = require('./StealthInjector');

// ============================================================================
// V4.20: 向后兼容 - 从已删除的 browser-pool.js 迁移
// ============================================================================

/**
 * 生成追踪 ID
 * @returns {string}
 */
function generateTraceId() {
    return `trace_${Date.now()}_${Math.random().toString(36).substring(2, 11)}`;
}

/**
 * 全局浏览器池实例 (单例)
 * @type {BrowserManager|null}
 */
let globalPool = null;

/**
 * 获取全局浏览器池
 * @param {Object} [config] - 配置选项
 * @returns {BrowserManager}
 */
function getGlobalPool(config) {
    if (!globalPool) {
        globalPool = new BrowserManager(config);
    }
    return globalPool;
}

/**
 * 清理全局浏览器池
 * @returns {Promise<void>}
 */
async function cleanupGlobalPool() {
    if (globalPool) {
        await globalPool.safeClose();
        globalPool = null;
    }
}

module.exports = {
    // 核心类
    BrowserManager,
    StealthInjector,
    getDefaultStealthScript,
    // V4.20: 向后兼容导出
    generateTraceId,
    getGlobalPool,
    cleanupGlobalPool
};
