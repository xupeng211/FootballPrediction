/**
 * SafeAccess - 安全数据访问工具
 * =============================
 *
 * 提供安全的对象属性访问函数
 *
 * @module core/utils/SafeAccess
 */

'use strict';

/**
 * 安全获取对象属性
 * @param {Object} obj - 源对象
 * @param {string} path - 属性路径 (如 'a.b.c')
 * @param {*} defaultValue - 默认值
 * @returns {*}
 */
function safeGet(obj, path, defaultValue = undefined) {
    if (!obj || typeof obj !== 'object') {
        return defaultValue;
    }

    const keys = path.split('.');
    let current = obj;

    for (const key of keys) {
        if (current === null || current === undefined || typeof current !== 'object') {
            return defaultValue;
        }
        current = current[key];
    }

    return current !== undefined ? current : defaultValue;
}

/**
 * 检查路径是否存在
 * @param {Object} obj - 源对象
 * @param {string} path - 属性路径
 * @returns {boolean}
 */
function hasPath(obj, path) {
    if (!obj || typeof obj !== 'object') {
        return false;
    }

    const keys = path.split('.');
    let current = obj;

    for (const key of keys) {
        if (current === null || current === undefined || typeof current !== 'object') {
            return false;
        }
        if (!(key in current)) {
            return false;
        }
        current = current[key];
    }

    return true;
}

/**
 * 检查值是否为有效对象
 * @param {*} value
 * @returns {boolean}
 */
function is(value) {
    return value !== null && typeof value === 'object';
}

module.exports = { safeGet, hasPath, is };
