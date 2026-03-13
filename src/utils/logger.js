/**
 * V172 结构化日志系统
 * ====================
 *
 * 特性:
 * - 支持 DEBUG/INFO/WARN/ERROR 等级
 * - 性能埋点 (耗时统计)
 * - 模块化前缀
 * - 可配置输出级别
 * @module src/utils/logger
 * @version V172.100
 */

'use strict';

// ============================================================================
// 日志级别定义
// ============================================================================

const LOG_LEVELS = {
    DEBUG: 0,
    INFO: 1,
    WARN: 2,
    ERROR: 3,
    SILENT: 4
};

// 当前日志级别 (可通过环境变量配置)
const CURRENT_LEVEL = LOG_LEVELS[process.env.LOG_LEVEL?.toUpperCase()] ?? LOG_LEVELS.INFO;

// ============================================================================
// 性能计时器
// ============================================================================

const timers = new Map();

/**
 * 开始计时
 * @param {string} label - 计时器标签
 */
function timeStart(label) {
    timers.set(label, {
        start: process.hrtime.bigint(),
        label
    });
}

/**
 * 结束计时并返回耗时
 * @param {string} label - 计时器标签
 * @returns {number} 耗时 (毫秒)
 */
function timeEnd(label) {
    const timer = timers.get(label);
    if (!timer) {
        return -1;
    }

    const elapsed = Number(process.hrtime.bigint() - timer.start) / 1_000_000; // ns -> ms
    timers.delete(label);
    return elapsed;
}

// ============================================================================
// Logger 类
// ============================================================================

/**
 *
 */
class Logger {
    /**
     * @param {string} module - 模块名称
     */
    constructor(module) {
        this.module = module;
        this.prefix = `[${module}]`;
    }

    /**
     * 格式化时间戳
     * @returns {string}
     */
    _timestamp() {
        return new Date().toISOString().slice(11, 19);
    }

    /**
     * 格式化输出
     * @param {string} level - 日志级别
     * @param {string} icon - 图标
     * @param {string} message - 消息
     * @param {any[]} args - 额外参数
     */
    _log(level, icon, message, args) {
        const levelNum = LOG_LEVELS[level];
        if (levelNum < CURRENT_LEVEL) return;

        const timestamp = this._timestamp();
        const prefix = `${timestamp} ${icon} ${this.prefix}`;

        switch (level) {
            case 'DEBUG':
                console.log(`${prefix}`, message, ...args);
                break;
            case 'INFO':
                console.log(`${prefix} ✅ ${message}`, ...args);
                break;
            case 'WARN':
                console.log(`${prefix} ⚠️  ${message}`, ...args);
                break;
            case 'ERROR':
                console.error(`${prefix} ❌ ${message}`, ...args);
                break;
        }
    }

    /**
     * 调试日志
     * @param {string} message - 消息
     * @param  {...any} args - 额外参数
     */
    debug(message, ...args) {
        this._log('DEBUG', '🔍', message, args);
    }

    /**
     * 信息日志
     * @param {string} message - 消息
     * @param  {...any} args - 额外参数
     */
    info(message, ...args) {
        this._log('INFO', 'ℹ️', message, args);
    }

    /**
     * 警告日志
     * @param {string} message - 消息
     * @param  {...any} args - 额外参数
     */
    warn(message, ...args) {
        this._log('WARN', '⚠️', message, args);
    }

    /**
     * 错误日志
     * @param {string} message - 消息
     * @param  {...any} args - 额外参数
     */
    error(message, ...args) {
        this._log('ERROR', '❌', message, args);
    }

    /**
     * 成功日志 (INFO 别名)
     * @param {string} message - 消息
     * @param  {...any} args - 额外参数
     */
    success(message, ...args) {
        this._log('INFO', '✅', message, args);
    }

    /**
     * Stealth 日志 (DEBUG 别名)
     * @param {string} message - 消息
     * @param  {...any} args - 额外参数
     */
    stealth(message, ...args) {
        this._log('DEBUG', '🕵️', message, args);
    }

    // ========================================================================
    // 性能埋点
    // ========================================================================

    /**
     * 开始性能计时
     * @param {string} operation - 操作名称
     */
    time(operation) {
        timeStart(`${this.module}:${operation}`);
    }

    /**
     * 结束性能计时并记录
     * @param {string} operation - 操作名称
     * @returns {number} 耗时 (毫秒)
     */
    timeEnd(operation) {
        const label = `${this.module}:${operation}`;
        const elapsed = timeEnd(label);

        if (elapsed >= 0) {
            this.debug(`${operation} 耗时: ${elapsed.toFixed(2)}ms`);
        }

        return elapsed;
    }

    /**
     * 包装异步函数，自动记录耗时
     * @param {string} operation - 操作名称
     * @param {Function} fn - 异步函数
     * @returns {Promise<any>}
     */
    async measure(operation, fn) {
        this.time(operation);
        try {
            const result = await fn();
            this.timeEnd(operation);
            return result;
        } catch (error) {
            this.timeEnd(operation);
            throw error;
        }
    }
}

// ============================================================================
// 工厂函数
// ============================================================================

/**
 * 创建 Logger 实例
 * @param {string} module - 模块名称
 * @returns {Logger}
 */
function createLogger(module) {
    return new Logger(module);
}

// ============================================================================
// 全局性能监控
// ============================================================================

const PerformanceMonitor = {
    metrics: new Map(),

    /**
     * 记录指标
     * @param {string} name - 指标名称
     * @param {number} value - 指标值
     */
    record(name, value) {
        if (!this.metrics.has(name)) {
            this.metrics.set(name, []);
        }
        this.metrics.get(name).push({
            value,
            timestamp: Date.now()
        });
    },

    /**
     * 获取指标统计
     * @param {string} name - 指标名称
     * @returns {object} 统计信息
     */
    getStats(name) {
        const values = this.metrics.get(name) || [];
        if (values.length === 0) {
            return { count: 0, avg: 0, min: 0, max: 0 };
        }

        const nums = values.map(v => v.value);
        return {
            count: nums.length,
            avg: nums.reduce((a, b) => a + b, 0) / nums.length,
            min: Math.min(...nums),
            max: Math.max(...nums)
        };
    },

    /**
     * 清除所有指标
     */
    clear() {
        this.metrics.clear();
    },

    /**
     * 打印所有指标统计
     */
    printReport() {
        console.log('\n📊 性能监控报告');
        console.log('='.repeat(50));

        for (const [name, values] of this.metrics) {
            const stats = this.getStats(name);
            console.log(`  ${name}:`);
            console.log(`    次数: ${stats.count}`);
            console.log(`    平均: ${stats.avg.toFixed(2)}ms`);
            console.log(`    最小: ${stats.min.toFixed(2)}ms`);
            console.log(`    最大: ${stats.max.toFixed(2)}ms`);
        }

        console.log('='.repeat(50));
    }
};

// ============================================================================
// 导出
// ============================================================================

module.exports = {
    Logger,
    createLogger,
    LOG_LEVELS,
    PerformanceMonitor,
    timeStart,
    timeEnd
};
