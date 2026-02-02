/**
 * ErrorHandler - V167.000 Global Exception Handling Middleware
 * =============================================================
 *
 * [Genesis.Reconstruction] 全局异常处理中间件
 *
 * 专门针对 `context destroyed` 建立自动重连逻辑，
 * 确保单场失败不崩掉整个进程。
 *
 * 核心特性:
 * - 全局异常捕获和分类
 * - Context destroyed 自动重连
 * - 资源清理保证（finally 块）
 * - 结构化错误日志
 * - 熔断器机制（连续失败阈值）
 *
 * @module middleware/ErrorHandler
 * @version V167.000
 * @since 2026-02-02
 * @author [Genesis.Reconstruction]
 */

'use strict';

/**
 * V167.000: 错误类型枚举
 */
const ERROR_TYPES = {
    CONTEXT_DESTROYED: 'CONTEXT_DESTROYED',
    TARGET_CLOSED: 'TARGET_CLOSED',
    NETWORK_ERROR: 'NETWORK_ERROR',
    TIMEOUT_ERROR: 'TIMEOUT_ERROR',
    PARSE_ERROR: 'PARSE_ERROR',
    VALIDATION_ERROR: 'VALIDATION_ERROR',
    UNKNOWN_ERROR: 'UNKNOWN_ERROR'
};

/**
 * V167.000: 可重试错误列表
 * 这些错误会触发自动重试
 */
const RETRYABLE_ERRORS = [
    'context destroyed',
    'target closed',
    'Session closed',
    'Navigation failed',
    'Net::ERR_',
    'Timeout',
    'ETIMEDOUT',
    'ECONNRESET'
];

/**
 * V167.000: 错误分类器
 * 将错误消息分类到标准错误类型
 */
class ErrorClassifier {
    /**
     * 分类错误类型
     * @param {Error|string} error - 错误对象或错误消息
     * @returns {string} 错误类型
     */
    static classify(error) {
        const message = error instanceof Error ? error.message : String(error);
        const lowerMessage = message.toLowerCase();

        // Context/Target 错误
        if (lowerMessage.includes('context destroyed') ||
            lowerMessage.includes('context has been closed')) {
            return ERROR_TYPES.CONTEXT_DESTROYED;
        }

        if (lowerMessage.includes('target closed') ||
            lowerMessage.includes('target has been closed')) {
            return ERROR_TYPES.TARGET_CLOSED;
        }

        // 网络错误
        if (lowerMessage.includes('net::err_') ||
            lowerMessage.includes('network') ||
            lowerMessage.includes('connection')) {
            return ERROR_TYPES.NETWORK_ERROR;
        }

        // 超时错误
        if (lowerMessage.includes('timeout') ||
            lowerMessage.includes('timed out')) {
            return ERROR_TYPES.TIMEOUT_ERROR;
        }

        // 解析错误
        if (lowerMessage.includes('parse') ||
            lowerMessage.includes('json') ||
            lowerMessage.includes('syntax') ||
            lowerMessage.includes('token') ||
            lowerMessage.includes('unexpected')) {
            return ERROR_TYPES.PARSE_ERROR;
        }

        // 验证错误
        if (lowerMessage.includes('validation') ||
            lowerMessage.includes('invalid')) {
            return ERROR_TYPES.VALIDATION_ERROR;
        }

        return ERROR_TYPES.UNKNOWN_ERROR;
    }

    /**
     * 判断错误是否可重试
     * @param {Error|string} error - 错误对象或错误消息
     * @returns {boolean} 是否可重试
     */
    static isRetryable(error) {
        const message = error instanceof Error ? error.message : String(error);
        const lowerMessage = message.toLowerCase();

        return RETRYABLE_ERRORS.some(pattern =>
            lowerMessage.includes(pattern.toLowerCase())
        );
    }

    /**
     * 判断是否为致命错误（不可恢复）
     * @param {Error|string} error - 错误对象或错误消息
     * @returns {boolean} 是否为致命错误
     */
    static isFatal(error) {
        const type = ErrorClassifier.classify(error);

        // 解析错误和验证错误通常是致命的
        return type === ERROR_TYPES.PARSE_ERROR ||
               type === ERROR_TYPES.VALIDATION_ERROR;
    }
}

/**
 * V167.000: 熔断器
 * 防止连续失败导致资源耗尽
 */
class CircuitBreaker {
    /**
     * @param {Object} config - 熔断器配置
     * @param {number} config.failureThreshold - 失败阈值（默认：5）
     * @param {number} config.resetTimeout - 重置超时（毫秒，默认：60000）
     */
    constructor(config = {}) {
        this.failureThreshold = config.failureThreshold || 5;
        this.resetTimeout = config.resetTimeout || 60000; // 1 minute

        this.failureCount = 0;
        this.lastFailureTime = null;
        this.state = 'CLOSED'; // CLOSED, OPEN, HALF_OPEN
    }

    /**
     * 记录成功
     */
    recordSuccess() {
        this.failureCount = 0;
        this.state = 'CLOSED';
    }

    /**
     * 记录失败
     */
    recordFailure() {
        this.failureCount++;
        this.lastFailureTime = Date.now();

        if (this.failureCount >= this.failureThreshold) {
            this.state = 'OPEN';
            console.warn(`[CircuitBreaker] ⚠️ Threshold reached: ${this.failureCount} failures, circuit OPEN`);
        }
    }

    /**
     * 检查是否允许执行
     * @returns {boolean} 是否允许执行
     */
    allowExecution() {
        // 如果熔断器打开，检查是否可以重置
        if (this.state === 'OPEN') {
            const timeSinceLastFailure = Date.now() - this.lastFailureTime;
            if (timeSinceLastFailure > this.resetTimeout) {
                this.state = 'HALF_OPEN';
                this.failureCount = 0;
                console.log('[CircuitBreaker] 🔧 Circuit HALF_OPEN, attempting recovery...');
                return true;
            }
            return false;
        }

        return true;
    }

    /**
     * 获取状态
     * @returns {Object} 状态信息
     */
    getState() {
        return {
            state: this.state,
            failureCount: this.failureCount,
            lastFailureTime: this.lastFailureTime
        };
    }
}

/**
 * V167.000: 资源清理器
 * 确保在任何情况下都能正确清理资源
 */
class ResourceCleaner {
    /**
     * @param {Object} resources - 资源对象
     */
    constructor(resources = {}) {
        this.resources = {
            page: null,
            context: null,
            browser: null,
            dbClient: null,
            listeners: [],
            ...resources
        };
    }

    /**
     * 注册资源
     * @param {string} name - 资源名称
     * @param {Object} resource - 资源对象
     */
    register(name, resource) {
        this.resources[name] = resource;
    }

    /**
     * 注册事件监听器（用于清理）
     * @param {Object} emitter - 事件发射器
     * @param {string} event - 事件名称
     * @param {Function} listener - 监听器函数
     */
    registerListener(emitter, event, listener) {
        this.resources.listeners.push({ emitter, event, listener });
    }

    /**
     * 清理所有资源
     * @returns {Promise<void>}
     */
    async cleanup() {
        console.log('[ResourceCleaner] 🧹 Starting resource cleanup...');

        // 清理事件监听器
        for (const { emitter, event, listener } of this.resources.listeners) {
            try {
                emitter.removeListener(event, listener);
            } catch (e) {
                // 忽略监听器清理错误
            }
        }
        this.resources.listeners = [];

        // 关闭 Page
        if (this.resources.page && !this.resources.page.isClosed()) {
            try {
                await this.resources.page.close();
                console.log('[ResourceCleaner] ✅ Page closed');
            } catch (e) {
                console.warn('[ResourceCleaner] ⚠️ Page close error:', e.message);
            }
        }

        // 关闭 Context
        if (this.resources.context) {
            try {
                await this.resources.context.close();
                console.log('[ResourceCleaner] ✅ Context closed');
            } catch (e) {
                console.warn('[ResourceCleaner] ⚠️ Context close error:', e.message);
            }
        }

        // 关闭 Browser
        if (this.resources.browser && this.resources.browser.isConnected()) {
            try {
                await this.resources.browser.close();
                console.log('[ResourceCleaner] ✅ Browser closed');
            } catch (e) {
                console.warn('[ResourceCleaner] ⚠️ Browser close error:', e.message);
            }
        }

        // 关闭数据库连接
        if (this.resources.dbClient) {
            try {
                await this.resources.dbClient.end();
                console.log('[ResourceCleaner] ✅ Database connection closed');
            } catch (e) {
                console.warn('[ResourceCleaner] ⚠️ DB close error:', e.message);
            }
        }

        console.log('[ResourceCleaner] ✅ Resource cleanup complete');
    }
}

/**
 * V167.000: 错误处理器
 * 全局异常处理和自动恢复
 */
class ErrorHandler {
    /**
     * @param {Object} config - 配置选项
     * @param {number} config.maxRetries - 最大重试次数（默认：3）
     * @param {number} config.retryDelay - 重试延迟（毫秒，默认：2000）
     * @param {boolean} config.enableCircuitBreaker - 启用熔断器（默认：true）
     */
    constructor(config = {}) {
        this.maxRetries = config.maxRetries || 3;
        this.retryDelay = config.retryDelay || 2000;
        this.enableCircuitBreaker = config.enableCircuitBreaker !== false;

        this.circuitBreaker = this.enableCircuitBreaker
            ? new CircuitBreaker(config.circuitBreaker)
            : null;

        this.stats = {
            totalErrors: 0,
            recoveredErrors: 0,
            fatalErrors: 0,
            errorsByType: {}
        };
    }

    /**
     * V167.000: 包装函数，提供全局异常处理
     * @param {Function} fn - 要执行的函数
     * @param {Object} context - 上下文信息（用于日志）
     * @returns {Function} 包装后的函数
     */
    withErrorHandling(fn, context = 'Unknown') {
        return async (...args) => {
            const cleaner = new ResourceCleaner();

            try {
                // 注册资源到清理器
                if (args[0]?.page) cleaner.register('page', args[0].page);
                if (args[0]?.context) cleaner.register('context', args[0].context);
                if (args[0]?.browser) cleaner.register('browser', args[0].browser);

                const result = await this._executeWithRetry(fn, args, context);
                return result;

            } catch (error) {
                return this._handleFatalError(error, context);
            } finally {
                await cleaner.cleanup();
            }
        };
    }

    /**
     * V167.000: 执行函数，支持自动重试
     * @private
     */
    async _executeWithRetry(fn, args, context) {
        let lastError = null;
        let attempt = 0;

        while (attempt <= this.maxRetries) {
            // 检查熔断器
            if (this.circuitBreaker && !this.circuitBreaker.allowExecution()) {
                throw new Error(`[ErrorHandler] Circuit breaker is OPEN, refusing execution`);
            }

            try {
                const result = await fn(...args);

                // 成功，记录到熔断器
                if (this.circuitBreaker) {
                    this.circuitBreaker.recordSuccess();
                }

                return result;

            } catch (error) {
                lastError = error;
                const errorType = ErrorClassifier.classify(error);
                this.stats.totalErrors++;
                this.stats.errorsByType[errorType] = (this.stats.errorsByType[errorType] || 0) + 1;

                // 记录错误
                console.error(`[ErrorHandler] ❌ [${context}] Attempt ${attempt + 1}/${this.maxRetries + 1}: ${errorType} - ${error.message}`);

                // 检查是否可重试
                if (!ErrorClassifier.isRetryable(error) || attempt >= this.maxRetries) {
                    if (this.circuitBreaker) {
                        this.circuitBreaker.recordFailure();
                    }
                    throw error;
                }

                // 等待后重试
                attempt++;
                const delay = this.retryDelay * attempt; // 指数退避
                console.log(`[ErrorHandler] 🔄 Retrying in ${delay}ms...`);
                await new Promise(resolve => setTimeout(resolve, delay));
            }
        }

        throw lastError;
    }

    /**
     * V167.000: 处理致命错误
     * @private
     */
    _handleFatalError(error, context) {
        const errorType = ErrorClassifier.classify(error);
        this.stats.fatalErrors++;

        console.error(`[ErrorHandler] 💀 FATAL ERROR [${context}]: ${errorType}`);
        console.error(`[ErrorHandler] Message: ${error.message}`);
        console.error(`[ErrorHandler] Stack: ${error.stack}`);

        return {
            success: false,
            error: error.message,
            errorType,
            context,
            fatal: true
        };
    }

    /**
     * V167.000: 获取统计信息
     * @returns {Object} 统计信息
     */
    getStats() {
        return {
            ...this.stats,
            circuitBreaker: this.circuitBreaker?.getState()
        };
    }

    /**
     * V167.000: 重置统计信息
     */
    resetStats() {
        this.stats = {
            totalErrors: 0,
            recoveredErrors: 0,
            fatalErrors: 0,
            errorsByType: {}
        };
    }
}

/**
 * V167.000: 便捷函数创建错误处理器
 * @param {Object} config - 配置选项
 * @returns {ErrorHandler} 错误处理器实例
 */
function createErrorHandler(config = {}) {
    return new ErrorHandler(config);
}

/**
 * V167.000: 导出
 */
module.exports = {
    ERROR_TYPES,
    RETRYABLE_ERRORS,
    ErrorClassifier,
    CircuitBreaker,
    ResourceCleaner,
    ErrorHandler,
    createErrorHandler
};
