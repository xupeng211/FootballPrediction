/**
 * MasterGate - Master IPC 消息网关
 * ==============================================
 *
 * 负责:
 * - 监听 Worker 消息
 * - 消息路由与分发
 * - 自愈逻辑触发
 *
 * @module core/ipc/MasterGate
 * @version V174.0.0
 */

'use strict';

const { MessageTypes } = require('./MessageTypes');

/**
 * MasterGate - Master IPC 消息网关
 */
class MasterGate {
    /**
     * @param {Object} options - 配置选项
     * @param {Object} options.handlers - 消息处理器映射
     * @param {number} options.circuitBreakerThreshold - 熔断阈值
     */
    constructor(options = {}) {
        this.handlers = options.handlers || {};
        this.circuitBreakerThreshold = options.circuitBreakerThreshold ?? 5;

        // Worker 状态跟踪
        this.workerStates = new Map();  // workerId -> { consecutiveErrors, status, ... }

        // 统计
        this.stats = {
            messagesReceived: 0,
            readySignals: 0,
            taskSuccesses: 0,
            taskFailures: 0,
            retryRequests: 0,
            circuitBreaks: 0
        };
    }

    /**
     * 注册消息处理器
     * @param {string} type - 消息类型
     * @param {Function} handler - 处理函数 (workerId, msg) => void
     */
    on(type, handler) {
        this.handlers[type] = handler;
    }

    /**
     * 处理来自 Worker 的消息
     * @param {number} workerId - Worker ID
     * @param {Object} msg - 消息对象
     */
    handle(workerId, msg) {
        this.stats.messagesReceived++;

        // 初始化 Worker 状态
        if (!this.workerStates.has(workerId)) {
            this.workerStates.set(workerId, {
                consecutiveErrors: 0,
                status: 'UNKNOWN',
                lastMessage: null
            });
        }

        const state = this.workerStates.get(workerId);
        state.lastMessage = msg;

        // 路由到对应处理器
        switch (msg.type) {
            case MessageTypes.READY:
                this._handleReady(workerId, msg);
                break;

            case MessageTypes.TASK_START:
                this._handleTaskStart(workerId, msg);
                break;

            case MessageTypes.TASK_SUCCESS:
                this._handleTaskSuccess(workerId, msg);
                break;

            case MessageTypes.TASK_FAILED:
                this._handleTaskFailed(workerId, msg);
                break;

            case MessageTypes.TASK_RETRY:
                this._handleTaskRetry(workerId, msg);
                break;

            case MessageTypes.WORKER_CIRCUIT_BREAK:
                this._handleCircuitBreak(workerId, msg);
                break;

            case MessageTypes.WORKER_COOL_DOWN:
                this._handleCoolDown(workerId, msg);
                break;

            default:
                // 未知消息类型，调用通用处理器
                if (this.handlers['*']) {
                    this.handlers['*'](workerId, msg);
                }
        }
    }

    /**
     * 处理 READY 信号
     * @private
     */
    _handleReady(workerId, msg) {
        this.stats.readySignals++;
        const state = this.workerStates.get(workerId);
        state.status = 'READY';
        state.consecutiveErrors = 0;

        if (this.handlers[MessageTypes.READY]) {
            this.handlers[MessageTypes.READY](workerId, msg);
        }
    }

    /**
     * 处理任务开始
     * @private
     */
    _handleTaskStart(workerId, msg) {
        const state = this.workerStates.get(workerId);
        state.status = 'RUNNING';
        state.currentMatch = msg.matchId;

        if (this.handlers[MessageTypes.TASK_START]) {
            this.handlers[MessageTypes.TASK_START](workerId, msg);
        }
    }

    /**
     * 处理任务成功
     * @private
     */
    _handleTaskSuccess(workerId, msg) {
        this.stats.taskSuccesses++;
        const state = this.workerStates.get(workerId);
        state.status = 'SUCCESS';
        state.consecutiveErrors = 0;
        state.currentMatch = null;

        if (this.handlers[MessageTypes.TASK_SUCCESS]) {
            this.handlers[MessageTypes.TASK_SUCCESS](workerId, msg);
        }
    }

    /**
     * 处理任务失败
     * @private
     */
    _handleTaskFailed(workerId, msg) {
        this.stats.taskFailures++;
        const state = this.workerStates.get(workerId);
        state.status = 'ERROR';
        state.consecutiveErrors++;

        // 检查是否需要熔断
        if (state.consecutiveErrors >= this.circuitBreakerThreshold) {
            this._triggerCircuitBreak(workerId);
        }

        if (this.handlers[MessageTypes.TASK_FAILED]) {
            this.handlers[MessageTypes.TASK_FAILED](workerId, msg);
        }
    }

    /**
     * 处理重试请求
     * @private
     */
    _handleTaskRetry(workerId, msg) {
        this.stats.retryRequests++;
        const state = this.workerStates.get(workerId);
        state.status = 'RETRYING';

        if (this.handlers[MessageTypes.TASK_RETRY]) {
            this.handlers[MessageTypes.TASK_RETRY](workerId, msg);
        }
    }

    /**
     * 处理熔断信号
     * @private
     */
    _handleCircuitBreak(workerId, msg) {
        this.stats.circuitBreaks++;
        const state = this.workerStates.get(workerId);
        state.status = 'RECOVERING';

        if (this.handlers[MessageTypes.WORKER_CIRCUIT_BREAK]) {
            this.handlers[MessageTypes.WORKER_CIRCUIT_BREAK](workerId, msg);
        }
    }

    /**
     * 处理冷却信号
     * @private
     */
    _handleCoolDown(workerId, msg) {
        const state = this.workerStates.get(workerId);
        state.status = 'COOLING';

        if (this.handlers[MessageTypes.WORKER_COOL_DOWN]) {
            this.handlers[MessageTypes.WORKER_COOL_DOWN](workerId, msg);
        }
    }

    /**
     * 触发熔断
     * @private
     */
    _triggerCircuitBreak(workerId) {
        this.stats.circuitBreaks++;
        const state = this.workerStates.get(workerId);
        state.status = 'RECOVERING';

        console.log(`🛑 [MasterGate] Worker ${workerId} 触发熔断 (连续失败 ${state.consecutiveErrors} 次)`);

        if (this.handlers['circuitBreak']) {
            this.handlers['circuitBreak'](workerId);
        }
    }

    /**
     * 重置 Worker 的连续错误计数
     * @param {number} workerId - Worker ID
     */
    resetErrors(workerId) {
        const state = this.workerStates.get(workerId);
        if (state) {
            state.consecutiveErrors = 0;
        }
    }

    /**
     * 获取 Worker 状态
     * @param {number} workerId - Worker ID
     * @returns {Object|null}
     */
    getWorkerState(workerId) {
        return this.workerStates.get(workerId) || null;
    }

    /**
     * 获取统计信息
     * @returns {Object}
     */
    getStats() {
        return {
            ...this.stats,
            activeWorkers: this.workerStates.size
        };
    }

    /**
     * 获取所有 Worker 状态快照
     * @returns {Object}
     */
    getWorkerSnapshot() {
        const snapshot = {};
        for (const [workerId, state] of this.workerStates) {
            snapshot[workerId] = { ...state };
        }
        return snapshot;
    }
}

module.exports = {
    MasterGate
};
