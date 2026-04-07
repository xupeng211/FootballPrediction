/**
 * CircuitBreaker - V1.1.0 [Genesis.Standardization] Production-Grade Circuit Breaker
 * ============================================================================
 *
 * 自愈熔断器 - 连续失败 2 次，强制进入 15 分钟冷却期。
 *
 * V1.1.0 改进:
 * - 错误码标准化：使用 NetworkShieldError
 * - JSDoc 完整类型标注
 * - 日志级别规范化（RadarLogger 兼容）
 * - 状态转换事件系统增强
 * - 半开状态可配置
 *
 * States:
 * - CLOSED: 正常状态，允许请求通过
 * - OPEN: 熔断状态，拒绝请求
 * - HALF_OPEN: 半开状态，允许测试请求
 * @module network/core/CircuitBreaker
 * @version V1.1.0
 * @since 2026-02-03
 * @author [Genesis.Standardization]
 */

'use strict';

const { circuitOpen, NetworkShieldError } = require('./NetworkShieldError');

// ============================================================================
// CIRCUIT BREAKER CONFIG
// ============================================================================

/**
 * @typedef {object} CircuitBreakerConfig
 * @property {number} [failureThreshold=2] - 失败阈值
 * @property {number} [cooldownMinutes=15] - 冷却时间（分钟）
 * @property {number} [halfOpenMaxCalls=1] - 半开状态最大测试请求数
 * @property {number} [successThreshold=1] - 成功阈值（恢复到 CLOSED）
 * @property {number} [halfOpenTimeoutMs=30000] - 半开状态超时时间（毫秒）
 */

/**
 * @constant {CircuitBreakerConfig} DEFAULT_CONFIG
 */
const DEFAULT_CONFIG = Object.freeze({
    failureThreshold: 2,
    cooldownMinutes: 15,
    halfOpenMaxCalls: 1,
    successThreshold: 1,
    halfOpenTimeoutMs: 30000
});

// ============================================================================
// CIRCUIT BREAKER STATE ENUM
// ============================================================================

/**
 * @enum {string}
 */
const CircuitState = Object.freeze({
    CLOSED: 'CLOSED',       // 正常状态
    OPEN: 'OPEN',           // 熔断状态
    HALF_OPEN: 'HALF_OPEN'  // 半开状态（测试中）
});

/**
 * 获取熔断器状态列表
 * @returns {string[]}
 */
function getCircuitStates() {
    return Object.values(CircuitState);
}

// ============================================================================
// CIRCUIT BREAKER CLASS
// ============================================================================

/**
 * CircuitBreaker - 熔断器类
 * @class
 * @example
 * const samplePort = DEFAULT_PROXY_PORT;
 * const breaker = new CircuitBreaker(samplePort, {
 *   failureThreshold: 2,
 *   cooldownMinutes: 15
 * }, logger);
 *
 * try {
 *   await breaker.execute(async () => {
 *     return await fetchData();
 *   });
 * } catch (error) {
 *   if (error.name === 'NS_CIRCUIT_OPEN') {
 *     // 熔断器已打开
 *   }
 * }
 */
class CircuitBreaker {
    /**
     * 创建熔断器实例
     * @param {number} port - 代理端口
     * @param {CircuitBreakerConfig} [config] - 配置选项
     * @param {object} [logger] - 日志记录器（RadarLogger 兼容）
     */
    constructor(port, config = {}, logger = null) {
        /**
         * @type {number}
         * @readonly
         */
        this.port = port;

        /**
         * @type {CircuitBreakerConfig}
         * @readonly
         * @private
         */
        this._config = { ...DEFAULT_CONFIG, ...config };

        /**
         * @type {string}
         * @private
         */
        this._state = CircuitState.CLOSED;

        /**
         * @type {number}
         * @private
         */
        this._consecutiveFailures = 0;

        /**
         * @type {number}
         * @private
         */
        this._consecutiveSuccesses = 0;

        /**
         * @type {Date|null}
         * @private
         */
        this._lastFailureTime = null;

        /**
         * @type {Date|null}
         * @private
         */
        this._lastStateChange = null;

        /**
         * @type {Date|null}
         * @private
         */
        this._cooldownUntil = null;

        /**
         * @type {number}
         * @private
         */
        this._halfOpenCallCount = 0;

        /**
         * @type {object | null}
         * @private
         */
        this._logger = logger || null;

        /**
         * @type {Map<string, Function[]>}
         * @private
         */
        this._eventListeners = new Map();

        /**
         * @type {object}
         * @private
         */
        this._stats = {
            totalExecutions: 0,
            successfulExecutions: 0,
            failedExecutions: 0,
            rejectedExecutions: 0,
            stateTransitions: 0
        };

        this._logStateChange('INITIALIZED', CircuitState.CLOSED);
    }

    // ========================================================================
    // PUBLIC METHODS
    // ========================================================================

    /**
     * 执行请求（带熔断保护）
     * @param {Function} requestFn - 请求函数，返回 Promise
     * @returns {Promise<*>} 请求结果
     * @throws {NetworkShieldError} 熔断器已打开、请求失败
     * @example
     * const result = await breaker.execute(async () => {
     *   return await fetch(url);
     * });
     */
    async execute(requestFn) {
        // 检查是否需要转换状态
        this._evaluateStateTransition();

        // 如果熔断器打开，拒绝请求
        if (this._state === CircuitState.OPEN) {
            this._stats.rejectedExecutions++;
            throw circuitOpen(this.port, new Date(this._cooldownUntil));
        }

        this._stats.totalExecutions++;

        try {
            // 执行请求
            const result = await requestFn();

            // 记录成功
            this.recordSuccess();

            this._stats.successfulExecutions++;

            return result;
        } catch (error) {
            // 记录失败
            this.recordFailure(error);

            this._stats.failedExecutions++;

            throw error;
        }
    }

    /**
     * 记录成功
     * @public
     */
    recordSuccess() {
        this._consecutiveFailures = 0;
        this._consecutiveSuccesses++;

        // 如果在半开状态，成功次数达到阈值则恢复到关闭状态
        if (this._state === CircuitState.HALF_OPEN) {
            if (this._consecutiveSuccesses >= this._config.successThreshold) {
                this._transitionTo(CircuitState.CLOSED);
                this._emit('recovered', { port: this.port });
            }
        }

        this._log('info', `Consecutive successes: ${this._consecutiveSuccesses}`);
    }

    /**
     * 记录失败
     * @param {Error} [error] - 错误对象
     * @public
     */
    recordFailure(error) {
        this._consecutiveFailures++;
        this._consecutiveSuccesses = 0;
        this._lastFailureTime = new Date();

        // 检查是否需要熔断
        if (this._consecutiveFailures >= this._config.failureThreshold) {
            this._transitionTo(CircuitState.OPEN);
            this._emit('tripped', {
                port: this.port,
                failures: this._consecutiveFailures,
                error: error?.message || 'Unknown error'
            });
        }

        this._log('warn', `Consecutive failures: ${this._consecutiveFailures}`);
    }

    /**
     * 手动重置熔断器
     * @public
     */
    reset() {
        this._transitionTo(CircuitState.CLOSED);
        this._consecutiveFailures = 0;
        this._consecutiveSuccesses = 0;
        this._cooldownUntil = null;
        this._halfOpenCallCount = 0;

        this._log('info', 'Circuit breaker manually reset');
    }

    /**
     * 获取当前状态
     * @returns {CircuitBreakerState} 状态信息
     * @typedef {object} CircuitBreakerState
     * @property {number} port - 代理端口
     * @property {string} state - 熔断器状态
     * @property {number} consecutiveFailures - 连续失败次数
     * @property {number} consecutiveSuccesses - 连续成功次数
     * @property {Date|null} lastFailureTime - 最后失败时间
     * @property {Date|null} cooldownUntil - 冷却结束时间
     * @property {boolean} canExecute - 是否可执行请求
     * @property {object} stats - 统计信息
     */
    getState() {
        return {
            port: this.port,
            state: this._state,
            consecutiveFailures: this._consecutiveFailures,
            consecutiveSuccesses: this._consecutiveSuccesses,
            lastFailureTime: this._lastFailureTime,
            cooldownUntil: this._cooldownUntil,
            canExecute: this._state !== CircuitState.OPEN,
            stats: { ...this._stats }
        };
    }

    /**
     * 检查熔断器是否打开
     * @returns {boolean}
     */
    isOpen() {
        return this._state === CircuitState.OPEN;
    }

    /**
     * 检查熔断器是否关闭
     * @returns {boolean}
     */
    isClosed() {
        return this._state === CircuitState.CLOSED;
    }

    /**
     * 检查熔断器是否半开
     * @returns {boolean}
     */
    isHalfOpen() {
        return this._state === CircuitState.HALF_OPEN;
    }

    /**
     * 添加事件监听器
     * @param {string} event - 事件名称 ('tripped', 'recovered', 'halfOpen')
     * @param {Function} listener - 监听器函数
     * @example
     * breaker.on('tripped', (data) => {
     *   console.log(`Breaker tripped for port ${data.port}`);
     * });
     */
    on(event, listener) {
        if (!this._eventListeners.has(event)) {
            this._eventListeners.set(event, []);
        }
        this._eventListeners.get(event).push(listener);
    }

    /**
     * 移除事件监听器
     * @param {string} event - 事件名称
     * @param {Function} listener - 监听器函数
     */
    off(event, listener) {
        if (!this._eventListeners.has(event)) return;
        const listeners = this._eventListeners.get(event);
        const index = listeners.indexOf(listener);
        if (index > -1) {
            listeners.splice(index, 1);
        }
    }

    /**
     * 获取统计信息
     * @returns {object}
     */
    getStats() {
        return {
            ...this._stats,
            successRate: this._stats.totalExecutions > 0
                ? this._stats.successfulExecutions / this._stats.totalExecutions
                : 0,
            failureRate: this._stats.totalExecutions > 0
                ? this._stats.failedExecutions / this._stats.totalExecutions
                : 0
        };
    }

    // ========================================================================
    // PRIVATE METHODS
    // ========================================================================

    /**
     * 评估状态转换
     * @private
     */
    _evaluateStateTransition() {
        const now = new Date();

        // 如果熔断器打开，检查冷却期是否结束
        if (this._state === CircuitState.OPEN && this._cooldownUntil) {
            if (now >= this._cooldownUntil) {
                this._transitionTo(CircuitState.HALF_OPEN);
                this._emit('halfOpen', { port: this.port });
            }
        }

        // 如果半开状态超时，回到打开状态
        if (this._state === CircuitState.HALF_OPEN) {
            const halfOpenElapsed = now - new Date(this._lastStateChange);
            if (halfOpenElapsed > this._config.halfOpenTimeoutMs) {
                this._transitionTo(CircuitState.OPEN);
                this._emit('halfOpenTimeout', { port: this.port });
            }
        }
    }

    /**
     * 转换到新状态
     * @private
     * @param {string} newState - 新状态
     */
    _transitionTo(newState) {
        const oldState = this._state;
        this._state = newState;
        this._lastStateChange = new Date();

        // 如果转换到打开状态，设置冷却时间
        if (newState === CircuitState.OPEN) {
            const cooldownUntil = new Date();
            cooldownUntil.setMinutes(cooldownUntil.getMinutes() + this._config.cooldownMinutes);
            this._cooldownUntil = cooldownUntil;
        } else if (newState === CircuitState.CLOSED) {
            this._cooldownUntil = null;
            this._halfOpenCallCount = 0;
        }

        this._stats.stateTransitions++;
        this._logStateChange(oldState, newState);
    }

    /**
     * 记录状态变化
     * @private
     * @param {string} oldState - 旧状态
     * @param {string} newState - 新状态
     */
    _logStateChange(oldState, newState) {
        this._log('info', `State transition: ${oldState} -> ${newState}`);
    }

    /**
     * 触发事件
     * @private
     * @param {string} event - 事件名称
     * @param {object} data - 事件数据
     */
    _emit(event, data) {
        if (!this._eventListeners.has(event)) return;

        this._eventListeners.get(event).forEach(listener => {
            try {
                listener(data);
            } catch (error) {
                this._log('error', `Event listener error: ${error.message}`);
            }
        });
    }

    /**
     * 记录日志
     * @private
     * @param {string} level - 日志级别
     * @param {string} message - 日志消息
     */
    _log(level, message) {
        const logMessage = `[CircuitBreaker:${this.port}] ${message}`;

        if (!this._logger) {
            // 回退到 console
            switch (level) {
                case 'debug':
                    console.debug(logMessage);
                    break;
                case 'info':
                    console.info(logMessage);
                    break;
                case 'warn':
                    console.warn(logMessage);
                    break;
                case 'error':
                    console.error(logMessage);
                    break;
                default:
                    console.log(logMessage);
            }
            return;
        }

        // 使用 RadarLogger 兼容接口
        switch (level) {
            case 'debug':
                if (typeof this._logger.debug === 'function') {
                    this._logger.debug(logMessage);
                }
                break;
            case 'info':
                if (typeof this._logger.info === 'function') {
                    this._logger.info(logMessage);
                } else if (typeof this._logger.log === 'function') {
                    this._logger.log(logMessage);
                }
                break;
            case 'warn':
                if (typeof this._logger.warn === 'function') {
                    this._logger.warn(logMessage);
                }
                break;
            case 'error':
                if (typeof this._logger.error === 'function') {
                    this._logger.error(logMessage);
                }
                break;
        }
    }
}

// ============================================================================
// CIRCUIT BREAKER REGISTRY
// ============================================================================

/**
 * CircuitBreakerRegistry - 熔断器注册表
 * @class
 * @example
 * const registry = new CircuitBreakerRegistry(
 *   { failureThreshold: 2 },
 *   logger
 * );
 *
 * const breaker = registry.getBreaker(samplePort);
 * await breaker.execute(async () => { ... });
 */
class CircuitBreakerRegistry {
    /**
     * 创建熔断器注册表
     * @param {CircuitBreakerConfig} [config] - 全局配置
     * @param {object} [logger] - 日志记录器
     */
    constructor(config = {}, logger = null) {
        /**
         * @type {Map<number, CircuitBreaker>}
         * @private
         */
        this._breakers = new Map();

        /**
         * @type {CircuitBreakerConfig}
         * @private
         */
        this._config = config;

        /**
         * @type {object}
         * @private
         */
        this._logger = logger;
    }

    /**
     * 获取或创建熔断器
     * @param {number} port - 代理端口
     * @returns {CircuitBreaker} 熔断器实例
     */
    getBreaker(port) {
        if (!this._breakers.has(port)) {
            const breaker = new CircuitBreaker(port, this._config, this._logger);
            this._breakers.set(port, breaker);
        }
        return this._breakers.get(port);
    }

    /**
     * 移除熔断器
     * @param {number} port - 代理端口
     * @returns {boolean} 是否成功移除
     */
    removeBreaker(port) {
        return this._breakers.delete(port);
    }

    /**
     * 获取所有熔断器状态
     * @returns {CircuitBreakerState[]} 状态列表
     */
    getAllStates() {
        return Array.from(this._breakers.values()).map(b => b.getState());
    }

    /**
     * 获取统计摘要
     * @returns {object}
     */
    getSummary() {
        const states = this.getAllStates();

        const summary = {
            totalBreakers: states.length,
            open: 0,
            closed: 0,
            halfOpen: 0,
            totalExecutions: 0,
            successfulExecutions: 0,
            failedExecutions: 0,
            rejectedExecutions: 0
        };

        for (const state of states) {
            switch (state.state) {
                case CircuitState.OPEN:
                    summary.open++;
                    break;
                case CircuitState.CLOSED:
                    summary.closed++;
                    break;
                case CircuitState.HALF_OPEN:
                    summary.halfOpen++;
                    break;
            }

            summary.totalExecutions += state.stats.totalExecutions;
            summary.successfulExecutions += state.stats.successfulExecutions;
            summary.failedExecutions += state.stats.failedExecutions;
            summary.rejectedExecutions += state.stats.rejectedExecutions;
        }

        return summary;
    }

    /**
     * 重置所有熔断器
     */
    resetAll() {
        for (const breaker of this._breakers.values()) {
            breaker.reset();
        }
    }

    /**
     * 关闭所有熔断器（清理）
     */
    shutdown() {
        this._breakers.clear();
    }

    /**
     * 获取熔断器数量
     * @returns {number}
     */
    get size() {
        return this._breakers.size;
    }

    /**
     * 获取所有端口
     * @returns {number[]}
     */
    getPorts() {
        return Array.from(this._breakers.keys());
    }
}

module.exports = {
    CircuitBreaker,
    CircuitBreakerRegistry,
    CircuitState,
    getCircuitStates,
    DEFAULT_CONFIG
};
