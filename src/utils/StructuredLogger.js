/**
 * StructuredLogger - V4.0 结构化日志器
 * ======================================
 *
 * 独立模块：输出 JSON 格式日志，便于 ELK 采集
 * 从 FeatureSmelter.js 剥离，支持独立测试
 *
 * @module utils/StructuredLogger
 * @version V4.0.0-MODULAR
 * @since 2026-03-13
 */

'use strict';

const fs = require('fs');
const path = require('path');

// 日志级别常量
const LOG_LEVELS = {
    ERROR: 'error',
    WARN: 'warn',
    INFO: 'info',
    DEBUG: 'debug'
};

// ============================================================================
// StructuredLogger 类
// ============================================================================

/**
 * 结构化日志器
 * 输出 JSON 格式，便于 ELK 采集和分析
 */
class StructuredLogger {
    /**
     * @param {object} options - 日志选项
     * @param {string} options.component - 组件名称
     * @param {string} options.logDir - 日志目录
     * @param {boolean} options.enableStructured - 是否启用结构化输出
     */
    constructor(options = {}) {
        this.component = options.component || 'FeatureSmelter';
        this.logDir = options.logDir || '/app/logs/pipeline';
        this.enableStructured = options.enableStructured !== false;
        this.logStream = null;

        this._ensureLogDirectory();
        this._initLogStream();
    }

    /**
     * 确保日志目录存在
     * @private
     */
    _ensureLogDirectory() {
        if (!fs.existsSync(this.logDir)) {
            try {
                fs.mkdirSync(this.logDir, { recursive: true });
            } catch (error) {
                console.warn(`[WARN] 无法创建日志目录: ${error.message}`);
            }
        }
    }

    /**
     * 初始化日志文件流
     * @private
     */
    _initLogStream() {
        const logFileName = `smelter_${new Date().toISOString().slice(0, 10)}.jsonl`;
        const logFilePath = path.join(this.logDir, logFileName);

        try {
            this.logStream = fs.createWriteStream(logFilePath, { flags: 'a' });
        } catch (error) {
            console.warn(`[WARN] 无法创建日志文件: ${error.message}`);
        }
    }

    /**
     * 输出结构化日志
     * @param {string} level - 日志级别 (error, warn, info, debug)
     * @param {string} message - 日志消息
     * @param {object} [context] - 附加上下文
     */
    log(level, message, context = {}) {
        const logEntry = {
            timestamp: new Date().toISOString(),
            level,
            component: this.component,
            message,
            ...context
        };

        // 控制台输出
        const consoleMethod = level === 'error' ? 'error' : level === 'warn' ? 'warn' : 'log';
        if (this.enableStructured) {
            console[consoleMethod](JSON.stringify(logEntry));
        } else {
            const prefix = `[${logEntry.timestamp}] [${level.toUpperCase()}]`;
            console[consoleMethod](`${prefix} ${message}`, Object.keys(context).length > 0 ? context : '');
        }

        // 文件输出（JSONL 格式）
        if (this.logStream && this.logStream.writable) {
            try {
                this.logStream.write(JSON.stringify(logEntry) + '\n');
            } catch (writeError) {
                // 忽略写入错误
            }
        }
    }

    /**
     * 记录信息级别日志
     * @param {string} message - 日志消息
     * @param {object} [context] - 附加上下文
     */
    info(message, context = {}) {
        this.log(LOG_LEVELS.INFO, message, context);
    }

    /**
     * 记录警告级别日志
     * @param {string} message - 日志消息
     * @param {object} [context] - 附加上下文
     */
    warn(message, context = {}) {
        this.log(LOG_LEVELS.WARN, message, context);
    }

    /**
     * 记录错误级别日志
     * @param {string} message - 日志消息
     * @param {object} [context] - 附加上下文
     */
    error(message, context = {}) {
        this.log(LOG_LEVELS.ERROR, message, context);
    }

    /**
     * 记录调试级别日志
     * @param {string} message - 日志消息
     * @param {object} [context] - 附加上下文
     */
    debug(message, context = {}) {
        if (process.env.LOG_LEVEL === 'debug') {
            this.log(LOG_LEVELS.DEBUG, message, context);
        }
    }

    /**
     * 关闭日志流
     */
    close() {
        if (this.logStream) {
            try {
                this.logStream.end();
            } catch (error) {
                // 忽略关闭错误
            }
            this.logStream = null;
        }
    }
}

// ============================================================================
// 导出
// ============================================================================

module.exports = {
    StructuredLogger,
    LOG_LEVELS
};