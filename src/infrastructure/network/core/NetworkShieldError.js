/**
 * NetworkShieldError - V1.1.0 [Genesis.Standardization] Error Code System
 * ===========================================================================
 *
 * 标准化错误码系统 - 所有 NetworkShield 组件统一使用此错误类型。
 *
 * Error Codes:
 * - NS_AUTH_FAIL (4001): 代理认证失败
 * - NS_PROXY_DEAD (4002): 代理节点不可用
 * - NS_REGISTRY_LOCKED (4003): 注册表锁定
 * - NS_REGISTRY_CORRUPT (4004): 注册表数据损坏
 * - NS_SESSION_EXPIRED (4005): 会话已过期
 * - NS_NO_PROXY_AVAILABLE (4006): 无可用代理节点
 * - NS_CIRCUIT_OPEN (4007): 熔断器已打开
 * - NS_INVALID_CONFIG (4008): 配置无效
 * - NS_FILESYSTEM_ERROR (4009): 文件系统错误
 *
 * @module network/core/NetworkShieldError
 * @version V1.1.0
 * @since 2026-02-03
 * @author [Genesis.Standardization]
 */

'use strict';

// ============================================================================
// ERROR CODE ENUMERATION
// ============================================================================

const ErrorCode = {
    // Authentication & Authorization (4001-4099)
    NS_AUTH_FAIL: {
        code: 4001,
        name: 'NS_AUTH_FAIL',
        message: 'Proxy authentication failed',
        severity: 'ERROR',
        retryable: false
    },

    // Proxy Availability (4100-4199)
    NS_PROXY_DEAD: {
        code: 4100,
        name: 'NS_PROXY_DEAD',
        message: 'Proxy node is not responding',
        severity: 'WARN',
        retryable: true
    },
    NS_NO_PROXY_AVAILABLE: {
        code: 4101,
        name: 'NS_NO_PROXY_AVAILABLE',
        message: 'No available proxy nodes in pool',
        severity: 'ERROR',
        retryable: true
    },

    // Registry Operations (4200-4299)
    NS_REGISTRY_LOCKED: {
        code: 4200,
        name: 'NS_REGISTRY_LOCKED',
        message: 'Registry is locked by another process',
        severity: 'WARN',
        retryable: true
    },
    NS_REGISTRY_CORRUPT: {
        code: 4201,
        name: 'NS_REGISTRY_CORRUPT',
        message: 'Registry data is corrupted or invalid',
        severity: 'ERROR',
        retryable: false
    },

    // Session Management (4300-4399)
    NS_SESSION_EXPIRED: {
        code: 4300,
        name: 'NS_SESSION_EXPIRED',
        message: 'Session has expired',
        severity: 'WARN',
        retryable: false
    },
    NS_SESSION_NOT_FOUND: {
        code: 4301,
        name: 'NS_SESSION_NOT_FOUND',
        message: 'Session does not exist',
        severity: 'WARN',
        retryable: false
    },

    // Circuit Breaker (4400-4499)
    NS_CIRCUIT_OPEN: {
        code: 4400,
        name: 'NS_CIRCUIT_OPEN',
        message: 'Circuit breaker is OPEN for this proxy',
        severity: 'WARN',
        retryable: false
    },

    // Configuration (4500-4599)
    NS_INVALID_CONFIG: {
        code: 4500,
        name: 'NS_INVALID_CONFIG',
        message: 'Invalid configuration parameter',
        severity: 'ERROR',
        retryable: false
    },

    // Filesystem (4600-4699)
    NS_FILESYSTEM_ERROR: {
        code: 4600,
        name: 'NS_FILESYSTEM_ERROR',
        message: 'Filesystem operation failed',
        severity: 'ERROR',
        retryable: true
    },

    // Health Check (4700-4799)
    NS_HEALTH_CHECK_FAILED: {
        code: 4700,
        name: 'NS_HEALTH_CHECK_FAILED',
        message: 'Health check operation failed',
        severity: 'WARN',
        retryable: true
    }
};

// ============================================================================
// NETWORK SHIELD ERROR CLASS
// ============================================================================

class NetworkShieldError extends Error {
    /**
     * 创建 NetworkShield 标准错误
     *
     * @param {string|Object} errorCode - 错误码名称（如 'NS_PROXY_DEAD'）或错误配置对象
     * @param {string} [customMessage] - 自定义消息（可选）
     * @param {Object} [context] - 上下文信息（可选）
     * @param {Error} [cause] - 原始错误（可选）
     */
    constructor(errorCode, customMessage = null, context = {}, cause = null) {
        // 支持传入错误码名称或配置对象
        let errorConfig;
        if (typeof errorCode === 'string') {
            errorConfig = ErrorCode[errorCode];
            if (!errorConfig) {
                // 未定义的错误码，使用通用配置
                errorConfig = {
                    code: 5000,
                    name: 'NS_UNKNOWN',
                    message: `Unknown error: ${errorCode}`,
                    severity: 'ERROR',
                    retryable: false
                };
            }
        } else {
            errorConfig = errorCode;
        }

        // 构建错误消息
        const message = customMessage || errorConfig.message;

        super(message);

        /**
         * @type {string} 错误码名称
         */
        this.name = errorConfig.name;

        /**
         * @type {number} 数字错误码
         */
        this.code = errorConfig.code;

        /**
         * @type {string} 错误严重级别：DEBUG, INFO, WARN, ERROR
         */
        this.severity = errorConfig.severity;

        /**
         * @type {boolean} 是否可重试
         */
        this.retryable = errorConfig.retryable;

        /**
         * @type {Object} 上下文信息
         */
        this.context = context;

        /**
         * @type {Error} 原始错误（用于错误链）
         */
        this.cause = cause;

        /**
         * @type {string} 时间戳
         */
        this.timestamp = new Date().toISOString();

        // 维护正确的堆栈跟踪
        if (Error.captureStackTrace) {
            Error.captureStackTrace(this, NetworkShieldError);
        }
    }

    /**
     * 转换为可序列化的对象
     *
     * @returns {Object} 序列化后的错误对象
     */
    toJSON() {
        return {
            name: this.name,
            code: this.code,
            message: this.message,
            severity: this.severity,
            retryable: this.retryable,
            context: this.context,
            cause: this.cause ? {
                name: this.cause.name,
                message: this.cause.message,
                stack: this.cause.stack
            } : null,
            timestamp: this.timestamp,
            stack: this.stack
        };
    }

    /**
     * 转换为日志字符串
     *
     * @returns {string} 日志格式字符串
     */
    toLogString() {
        const contextStr = Object.keys(this.context).length > 0
            ? ` | Context: ${JSON.stringify(this.context)}`
            : '';
        return `[${this.name}] (${this.code}) ${this.message}${contextStr}`;
    }

    /**
     * 检查错误是否可重试
     *
     * @returns {boolean} 是否可重试
     */
    isRetryable() {
        return this.retryable;
    }

    /**
     * 检查错误严重级别
     *
     * @param {string} level - 要比较的级别
     * @returns {boolean} 是否达到或超过指定级别
     */
    isSeverityAtLeast(level) {
        const severityOrder = { DEBUG: 0, INFO: 1, WARN: 2, ERROR: 3 };
        return severityOrder[this.severity] >= (severityOrder[level] || 0);
    }
}

// ============================================================================
// ERROR FACTORY FUNCTIONS
// ============================================================================

/**
 * 创建代理认证失败错误
 *
 * @param {string} proxyUrl - 代理 URL
 * @param {Error} [cause] - 原始错误
 * @returns {NetworkShieldError}
 */
function authFail(proxyUrl, cause = null) {
    return new NetworkShieldError(
        ErrorCode.NS_AUTH_FAIL,
        `Authentication failed for proxy: ${proxyUrl}`,
        { proxyUrl },
        cause
    );
}

/**
 * 创建代理不可用错误
 *
 * @param {number} port - 代理端口
 * @param {string} reason - 失败原因
 * @returns {NetworkShieldError}
 */
function proxyDead(port, reason) {
    return new NetworkShieldError(
        ErrorCode.NS_PROXY_DEAD,
        `Proxy port ${port} is not responding: ${reason}`,
        { port, reason }
    );
}

/**
 * 创建注册表锁定错误
 *
 * @param {string} lockPath - 锁文件路径
 * @param {number} timeoutMs - 超时时间
 * @returns {NetworkShieldError}
 */
function registryLocked(lockPath, timeoutMs) {
    return new NetworkShieldError(
        ErrorCode.NS_REGISTRY_LOCKED,
        `Registry lock timeout after ${timeoutMs}ms`,
        { lockPath, timeoutMs }
    );
}

/**
 * 创建无可用代理错误
 *
 * @param {number} totalNodes - 总节点数
 * @param {number} activeNodes - 活跃节点数
 * @returns {NetworkShieldError}
 */
function noProxyAvailable(totalNodes, activeNodes) {
    return new NetworkShieldError(
        ErrorCode.NS_NO_PROXY_AVAILABLE,
        `No available proxy nodes (${activeNodes}/${totalNodes} active)`,
        { totalNodes, activeNodes }
    );
}

/**
 * 创建会话过期错误
 *
 * @param {string} sessionId - 会话 ID
 * @returns {NetworkShieldError}
 */
function sessionExpired(sessionId) {
    return new NetworkShieldError(
        ErrorCode.NS_SESSION_EXPIRED,
        `Session ${sessionId} has expired`,
        { sessionId }
    );
}

/**
 * 创建熔断器打开错误
 *
 * @param {number} port - 代理端口
 * @param {Date} cooldownUntil - 冷却结束时间
 * @returns {NetworkShieldError}
 */
function circuitOpen(port, cooldownUntil) {
    return new NetworkShieldError(
        ErrorCode.NS_CIRCUIT_OPEN,
        `Circuit breaker OPEN for port ${port}, cooldown until ${cooldownUntil.toISOString()}`,
        { port, cooldownUntil: cooldownUntil.toISOString() }
    );
}

/**
 * 创建配置无效错误
 *
 * @param {string} param - 参数名
 * @param {string} reason - 原因
 * @returns {NetworkShieldError}
 */
function invalidConfig(param, reason) {
    return new NetworkShieldError(
        ErrorCode.NS_INVALID_CONFIG,
        `Invalid configuration for '${param}': ${reason}`,
        { param, reason }
    );
}

/**
 * 创建文件系统错误
 *
 * @param {string} operation - 操作类型
 * @param {string} filePath - 文件路径
 * @param {Error} [cause] - 原始错误
 * @returns {NetworkShieldError}
 */
function filesystemError(operation, filePath, cause = null) {
    return new NetworkShieldError(
        ErrorCode.NS_FILESYSTEM_ERROR,
        `Filesystem ${operation} failed for ${filePath}`,
        { operation, filePath },
        cause
    );
}

/**
 * 从标准 Error 创建 NetworkShieldError
 *
 * @param {Error} error - 原始错误
 * @param {string} defaultCode - 默认错误码
 * @returns {NetworkShieldError}
 */
function fromError(error, defaultCode = 'NS_FILESYSTEM_ERROR') {
    if (error instanceof NetworkShieldError) {
        return error;
    }

    return new NetworkShieldError(
        defaultCode,
        error.message,
        {},
        error
    );
}

/**
 * 检查错误是否为特定类型
 *
 * @param {Error} error - 错误对象
 * @param {string} errorCode - 错误码名称
 * @returns {boolean}
 */
function isErrorType(error, errorCode) {
    return error instanceof NetworkShieldError && error.name === errorCode;
}

// ============================================================================
// ERROR HANDLER UTILITIES
// ============================================================================

/**
 * 安全执行函数并转换错误
 *
 * @param {Function} fn - 要执行的函数
 * @param {string} [errorCode] - 默认错误码
 * @returns {Promise<*>} 函数结果
 * @throws {NetworkShieldError}
 */
async function safeExecute(fn, errorCode = 'NS_FILESYSTEM_ERROR') {
    try {
        return await fn();
    } catch (error) {
        throw fromError(error, errorCode);
    }
}

/**
 * 安全执行同步函数并转换错误
 *
 * @param {Function} fn - 要执行的函数
 * @param {string} [errorCode] - 默认错误码
 * @returns {*} 函数结果
 * @throws {NetworkShieldError}
 */
function safeExecuteSync(fn, errorCode = 'NS_FILESYSTEM_ERROR') {
    try {
        return fn();
    } catch (error) {
        throw fromError(error, errorCode);
    }
}

module.exports = {
    // Error Code Enumeration
    ErrorCode,

    // Main Error Class
    NetworkShieldError,

    // Factory Functions
    authFail,
    proxyDead,
    registryLocked,
    noProxyAvailable,
    sessionExpired,
    circuitOpen,
    invalidConfig,
    filesystemError,
    fromError,
    isErrorType,

    // Utilities
    safeExecute,
    safeExecuteSync
};
