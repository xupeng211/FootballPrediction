/**
 * ErrorHandler - 高级错误审计器
 * ==============================
 *
 * 负责错误的分类、审计和重试决策：
 * - 错误类型分类
 * - 可重试性判断
 * - 错误统计与报告
 *
 * @module infrastructure/harvesters/components/ErrorHandler
 * @version V1.0.0
 */

'use strict';

/**
 * 错误类型枚举
 */
const ErrorType = {
    RETRYABLE: 'RETRYABLE',
    FATAL: 'FATAL',
    IGNORE: 'IGNORE',
    NETWORK: 'NETWORK',
    AUTH: 'AUTH',
    TIMEOUT: 'TIMEOUT',
    DATA: 'DATA',
    UNKNOWN: 'UNKNOWN'
};

/**
 * 高级错误审计器类
 */
class ErrorHandler {
    /**
     * 创建 ErrorHandler 实例
     * @param {object} config - 配置选项
     */
    constructor(config = {}) {
        this.config = {
            maxRetries: config.maxRetries || 3,
            enableDetailedLogging: config.enableDetailedLogging || false
        };
        this.stats = {
            total: 0,
            byType: {},
            retryable: 0,
            fatal: 0
        };
        this.errorPatterns = {
            retryable: [
                /timeout/i,
                /ECONNRESET/i,
                /ETIMEDOUT/i,
                /ECONNREFUSED/i,
                /network/i,
                /temporarily unavailable/i,
                /rate limit/i,
                /too many requests/i,
                /socket hang up/i,
                /connection closed/i
            ],
            fatal: [
                /authentication failed/i,
                /access denied/i,
                /permission denied/i,
                /not found/i,
                /invalid/i,
                /parse error/i,
                /syntax error/i
            ],
            ignore: [
                /aborted/i,
                /cancelled/i,
                /closed/i
            ]
        };
    }

    /**
     * 分类错误
     * @param {Error} error - 错误对象
     * @returns {ErrorType} 错误类型
     */
    classify(error) {
        if (!error) return ErrorType.UNKNOWN;

        const message = error.message || '';
        const code = error.code || '';
        const combined = `${message} ${code}`;

        // 检查可重试错误模式
        for (const pattern of this.errorPatterns.retryable) {
            if (pattern.test(combined)) {
                return ErrorType.RETRYABLE;
            }
        }

        // 检查致命错误模式
        for (const pattern of this.errorPatterns.fatal) {
            if (pattern.test(combined)) {
                return ErrorType.FATAL;
            }
        }

        // 检查可忽略错误模式
        for (const pattern of this.errorPatterns.ignore) {
            if (pattern.test(combined)) {
                return ErrorType.IGNORE;
            }
        }

        // 根据错误代码判断
        if (this._isNetworkError(code, message)) {
            return ErrorType.NETWORK;
        }
        if (this._isAuthError(code, message)) {
            return ErrorType.AUTH;
        }
        if (this._isTimeoutError(code, message)) {
            return ErrorType.TIMEOUT;
        }
        if (this._isDataError(code, message)) {
            return ErrorType.DATA;
        }

        return ErrorType.UNKNOWN;
    }

    /**
     * 判断错误是否可重试
     * @param {Error} error - 错误对象
     * @param {number} attempt - 当前尝试次数
     * @returns {boolean}
     */
    isRetryable(error, attempt = 1) {
        if (attempt >= this.config.maxRetries) {
            return false;
        }

        const type = this.classify(error);
        return type === ErrorType.RETRYABLE ||
               type === ErrorType.NETWORK ||
               type === ErrorType.TIMEOUT;
    }

    /**
     * 审计错误
     * @param {Error} error - 错误对象
     * @param {object} context - 错误上下文
     */
    audit(error, context = {}) {
        this.stats.total++;
        const type = this.classify(error);
        const code = error.code || '';
        const message = error.message || '';

        // V6.6: 增强断网保护 - 检测网络断开错误
        const isNetworkDisconnected = ['ENOTFOUND', 'ETIMEDOUT', 'ECONNREFUSED', 'EAI_AGAIN'].includes(code) ||
                                      /getaddrinfo|dns|network is unreachable/i.test(message);

        if (isNetworkDisconnected) {
            console.warn(`[WAITING] 网络连接中断 (${code})，系统进入等待状态，将在重试后恢复...`);
            // 网络错误标记为可重试，避免崩溃
            this.stats.retryable++;
            this.stats.byType[ErrorType.NETWORK] = (this.stats.byType[ErrorType.NETWORK] || 0) + 1;
            return ErrorType.NETWORK;
        }

        // 按类型统计
        this.stats.byType[type] = (this.stats.byType[type] || 0) + 1;

        // 可重试性统计
        if (this.isRetryable(error)) {
            this.stats.retryable++;
        } else {
            this.stats.fatal++;
        }

        // 详细日志
        if (this.config.enableDetailedLogging) {
            console.log(`[ErrorHandler] ${type}: ${error.message}`, context);
        }

        return type;
    }

    /**
     * 生成错误报告
     * @returns {object}
     */
    generateReport() {
        return {
            total: this.stats.total,
            byType: { ...this.stats.byType },
            retryable: this.stats.retryable,
            fatal: this.stats.fatal,
            retryRate: this.stats.total > 0
                ? ((this.stats.retryable / this.stats.total) * 100).toFixed(1)
                : '0.0'
        };
    }

    /**
     * 添加自定义错误模式
     * @param {string} category - 类别 ('retryable' | 'fatal' | 'ignore')
     * @param {RegExp} pattern - 正则表达式模式
     */
    addPattern(category, pattern) {
        if (this.errorPatterns[category]) {
            this.errorPatterns[category].push(pattern);
        }
    }

    /**
     * 重置统计
     */
    resetStats() {
        this.stats = {
            total: 0,
            byType: {},
            retryable: 0,
            fatal: 0
        };
    }

    /**
     * 检查是否为网络错误
     * @private
     */
    _isNetworkError(code, message) {
        const networkCodes = ['ECONNRESET', 'ECONNREFUSED', 'ETIMEDOUT', 'ENOTFOUND', 'EAI_AGAIN'];
        return networkCodes.includes(code) ||
               /network|connection|socket/i.test(message);
    }

    /**
     * 检查是否为认证错误
     * @private
     */
    _isAuthError(code, message) {
        const authCodes = ['28P01', 'EACCES'];
        return authCodes.includes(code) ||
               /authentication|unauthorized|forbidden/i.test(message);
    }

    /**
     * 检查是否为超时错误
     * @private
     */
    _isTimeoutError(code, message) {
        return code === 'ETIMEDOUT' ||
               code === 'TIMEOUT' ||
               /timeout|timed out/i.test(message);
    }

    /**
     * 检查是否为数据错误
     * @private
     */
    _isDataError(code, message) {
        return code === '23505' || // 唯一约束冲突
               /duplicate|constraint|validation/i.test(message);
    }

    /**
     * 数据库错误分类器（兼容旧版）
     * @param {Error} error - 数据库错误对象
     * @returns {string} 错误类型标记
     */
    classifyDatabaseError(error) {
        const code = error.code;
        const message = error.message.toLowerCase();

        if (code === 'ECONNREFUSED' || code === 'ETIMEDOUT' || message.includes('connect')) {
            return '[DB-NETWORK]';
        }
        if (code === '28P01' || message.includes('authentication') || message.includes('password')) {
            return '[DB-AUTH]';
        }
        if (code === '23505') {
            return '[DB-DUPLICATE]';
        }
        if (code === '42P01') {
            return '[DB-TABLE-NOT-FOUND]';
        }
        return '[DB-ERROR]';
    }

    /**
     * 文件错误分类器（兼容旧版）
     * @param {Error} error - 错误对象
     * @returns {string} 错误类型标记
     */
    classifyFileError(error) {
        const message = error.message.toLowerCase();
        if (message.includes('enoent')) return '[FILE-NOT-FOUND]';
        if (message.includes('eacces') || message.includes('permission')) return '[PERMISSION]';
        if (message.includes('enospc')) return '[DISK-FULL]';
        return '[FILE-ERROR]';
    }
}

module.exports = { ErrorHandler, ErrorType };
