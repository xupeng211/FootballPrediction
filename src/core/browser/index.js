/**
 * 浏览器管理模块入口
 * @module core/browser
 * @version V4.46.5 - 硬化：使用确定性 ID 生成器
 */

'use strict';

const { BrowserManager } = require('./BrowserManager');
const { StealthInjector, getDefaultStealthScript } = require('./StealthInjector');

// V4.46.5 HARDENING: 使用确定性 ID 生成器（零模拟铁律）
const { generateTraceId } = require('../id_generator');

// ============================================================================
// V4.20: 向后兼容 - 从已删除的 browser-pool.js 迁移
// ============================================================================

// generateTraceId 已移至 src/core/id_generator.js

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
