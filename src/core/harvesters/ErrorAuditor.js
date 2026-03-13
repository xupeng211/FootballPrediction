/**
 * ErrorAuditor - 错误审计员
 * ==========================
 *
 * 统一管理错误分类和重试判断逻辑。
 * 从 AbstractHarvester 剥离的工业级组件。
 * @module core/harvesters/ErrorAuditor
 * @version V1.0.0
 */

'use strict';

// ============================================================================
// 错误类型常量
// ============================================================================

const ErrorType = {
    BLOCKED: 'BLOCKED',           // Turnstile/Captcha/熔断
    RATE_LIMITED: 'RATE_LIMITED', // 403 限流
    TIMEOUT: 'TIMEOUT',           // 超时
    NO_DATA: 'NO_DATA',           // 无数据
    NETWORK_ERROR: 'NETWORK_ERROR', // 网络错误
    UNKNOWN: 'UNKNOWN'            // 未知错误
};

// ============================================================================
// 可重试错误模式
// ============================================================================

const RETRYABLE_PATTERNS = [
    'ERR_CONNECTION_CLOSED',
    'ERR_CONNECTION_RESET',
    'ERR_CONNECTION_TIMED_OUT',
    'ERR_TIMED_OUT',
    'ETIMEDOUT',
    'ECONNRESET',
    'ECONNREFUSED',
    'ENOTFOUND',
    'net::ERR_',
    'TIMEOUT',
    'Timeout',          // V4.51.1: 添加首字母大写版本
    'timeout',           // V4.51.1: 添加小写版本
    'Navigation timeout',
    'NETWORK_ERROR',
    'NO_NEXT_DATA',
    'DATA_TRANSFORM_FAILED',
    // V4.51.1: CF_BLOCK 已移至 NON_RETRYABLE_PATTERNS
    'reset by peer',  // 新增: 匹配 "Connection reset by peer"
    'socket'          // V4.51.1: 新增 socket hang up 支持
];

// ============================================================================
// 不可重试错误模式
// ============================================================================

const NON_RETRYABLE_PATTERNS = [
    '403',
    'ERR_BLOCKED',
    'Access denied',
    'Forbidden',
    'Turnstile',
    'CF_BLOCK',           // V4.51.1: Cloudflare 阻止需要办证
    'captcha'             // V4.51.1: 验证码需要人工介入
    // 注意: "Connection reset" 不应在这里，因为 "reset by peer" 是可重试的
];

// ============================================================================
// ErrorAuditor - 错误审计类
// ============================================================================

/**
 *
 */
class ErrorAuditor {
    /**
     * 创建 ErrorAuditor 实例
     * @param {object} [config] - 配置选项
     */
    constructor(config = {}) {
        this.config = {
            ...config
        };

        // 统计数据
        this.stats = {
            totalErrors: 0,
            byType: {}
        };
    }

    // ========================================================================
    // 核心方法
    // ========================================================================

    /**
     * 分类错误类型
     * @param {string} errorMessage - 错误消息
     * @returns {string} 错误类型 (ErrorType 枚举)
     */
    classifyError(errorMessage) {
        const msg = (errorMessage || '').toLowerCase();

        // V4.46.1: 全局熔断错误识别
        if (msg.includes('circuit_breaker_open') ||
            msg.includes('全局熔断') ||
            msg.includes('所有代理节点不可用')) {
            return ErrorType.BLOCKED;
        }

        if (msg.includes('403') || msg.includes('forbidden')) {
            return ErrorType.RATE_LIMITED;
        }

        // V4.51.1: 增强超时识别，包括 ETIMEDOUT
        if (msg.includes('timeout') ||
            msg.includes('timed out') ||
            msg.includes('etimedout')) {
            return ErrorType.TIMEOUT;
        }

        if (msg.includes('no_data') || msg.includes('size_too_small')) {
            return ErrorType.NO_DATA;
        }

        // V4.51.1: 增强网络错误识别，包括 socket hang up
        if (msg.includes('connection') ||
            msg.includes('network') ||
            msg.includes('econnreset') ||
            msg.includes('reset by peer') ||
            msg.includes('econnrefused') ||
            msg.includes('enotfound') ||
            msg.includes('socket')) {
            return ErrorType.NETWORK_ERROR;
        }

        // V4.51.1: CF_BLOCK 和 Access denied 必须识别为 BLOCKED
        if (msg.includes('turnstile') ||
            msg.includes('captcha') ||
            msg.includes('cf_block') ||
            msg.includes('access denied')) {
            return ErrorType.BLOCKED;
        }

        return ErrorType.UNKNOWN;
    }

    /**
     * 判断是否为可重试的错误
     * @param {Error|string} error - 错误对象或消息
     * @returns {boolean} 是否可重试
     */
    isRetryableError(error) {
        const msg = (typeof error === 'string' ? error : (error.message || '')).toLowerCase();

        // 先检查不可重试模式
        for (const pattern of NON_RETRYABLE_PATTERNS) {
            if (msg.includes(pattern.toLowerCase())) {
                return false;
            }
        }

        // 再检查可重试模式
        for (const pattern of RETRYABLE_PATTERNS) {
            if (msg.includes(pattern.toLowerCase())) {
                return true;
            }
        }

        // V4.51.2: NO_DATA 改为可重试（冷门赛事可能需要多次尝试+端口切换）
        if (msg.includes('NO_DATA')) {
            return true;  // 改为可重试，触发重试+端口切换+Cookie刷新
        }

        // V4.46.3: SIZE_TOO_SMALL 可重试（可能是 403 逃逸）
        if (msg.includes('SIZE_TOO_SMALL')) {
            return true;
        }

        return false;
    }

    /**
     * 记录错误（用于统计分析）
     * @param {string} errorMessage - 错误消息
     * @param {object} [metadata] - 额外元数据
     */
    recordError(errorMessage, metadata = {}) {
        const errorType = this.classifyError(errorMessage);

        this.stats.totalErrors++;

        if (!this.stats.byType[errorType]) {
            this.stats.byType[errorType] = 0;
        }
        this.stats.byType[errorType]++;

        return {
            type: errorType,
            retryable: this.isRetryableError(errorMessage),
            ...metadata
        };
    }

    /**
     * 获取错误统计
     * @returns {object} 统计数据
     */
    getStats() {
        return { ...this.stats };
    }

    /**
     * 重置统计
     */
    resetStats() {
        this.stats = {
            totalErrors: 0,
            byType: {}
        };
    }

    // ========================================================================
    // 辅助方法
    // ========================================================================

    /**
     * 判断是否为阻塞性错误（需要刷新身份）
     * @param {string} errorType - 错误类型
     * @returns {boolean}
     */
    isBlockingError(errorType) {
        return errorType === ErrorType.BLOCKED;
    }

    /**
     * 判断是否为限流错误
     * @param {string} errorType - 错误类型
     * @returns {boolean}
     */
    isRateLimitedError(errorType) {
        return errorType === ErrorType.RATE_LIMITED;
    }

    /**
     * 获取推荐的退避时间（毫秒）
     * @param {string} errorType - 错误类型
     * @param {number} attempt - 当前尝试次数
     * @returns {number} 退避时间（毫秒）
     */
    getRecommendedBackoff(errorType, attempt = 1) {
        const baseBackoff = {
            [ErrorType.BLOCKED]: 60000,      // 60 秒
            [ErrorType.RATE_LIMITED]: 30000, // 30 秒
            [ErrorType.TIMEOUT]: 10000,      // 10 秒
            [ErrorType.NETWORK_ERROR]: 5000, // 5 秒
            [ErrorType.NO_DATA]: 0,          // 不重试
            [ErrorType.UNKNOWN]: 5000        // 5 秒
        };

        const base = baseBackoff[errorType] || 5000;
        // 指数退避，最大 60 秒
        return Math.min(base * Math.pow(1.5, attempt - 1), 60000);
    }

    /**
     * 格式化错误信息用于日志
     * @param {string} errorMessage - 错误消息
     * @returns {string} 格式化后的错误信息
     */
    formatErrorForLog(errorMessage) {
        const errorType = this.classifyError(errorMessage);
        const retryable = this.isRetryableError(errorMessage);
        return `[${errorType}]${retryable ? ' (可重试)' : ''} ${errorMessage}`;
    }
}

// ============================================================================
// 单例模式
// ============================================================================

let _instance = null;

/**
 * 获取 ErrorAuditor 单例
 * @param {object} [config] - 配置选项
 * @returns {ErrorAuditor}
 */
function getErrorAuditor(config = {}) {
    if (!_instance) {
        _instance = new ErrorAuditor(config);
    }
    return _instance;
}

/**
 * 重置单例（用于测试）
 */
function resetErrorAuditor() {
    _instance = null;
}

module.exports = {
    ErrorAuditor,
    ErrorType,
    RETRYABLE_PATTERNS,
    NON_RETRYABLE_PATTERNS,
    getErrorAuditor,
    resetErrorAuditor
};
