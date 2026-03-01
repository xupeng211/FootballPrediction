/**
 * WorkerMessenger - IPC 消息收发器
 * ==============================================
 *
 * 负责 Worker 与 Master 进程之间的安全通信
 * - 消息发送重试机制
 * - IPC 就绪检测
 * - 标准化消息格式
 *
 * @module core/ipc/WorkerMessenger
 * @version V174.0.0
 */

'use strict';

const {
    MessageTypes,
    createMessage,
    taskStartMessage,
    taskSuccessMessage,
    taskFailedMessage,
    taskRetryMessage
} = require('./MessageTypes');

/**
 * WorkerMessenger - IPC 通信管理器
 */
class WorkerMessenger {
    /**
     * @param {number} workerId - Worker 标识符
     * @param {Object} options - 配置选项
     * @param {number} options.maxRetries - 最大重试次数
     * @param {number} options.retryDelayBase - 重试延时基数 (ms)
     * @param {boolean} options.silent - 静默模式（不打印日志）
     */
    constructor(workerId, options = {}) {
        this.workerId = workerId;
        this.maxRetries = options.maxRetries ?? 3;
        this.retryDelayBase = options.retryDelayBase ?? 100;
        this.silent = options.silent ?? false;
        this._ready = false;
    }

    /**
     * 日志输出
     * @private
     */
    _log(level, msg) {
        if (this.silent) return;
        const timestamp = new Date().toISOString().slice(0, 19).replace('T', ' ');
        const prefix = `[W${this.workerId}] [IPC]`;
        console.log(`${timestamp} ${prefix} [${level.toUpperCase()}] ${msg}`);
    }

    /**
     * 安全发送消息给 Master 进程
     * - 如果 process.send 不存在（非 fork 模式），则静默忽略
     * - 增加重试机制，防止瞬时通信失败
     *
     * @param {Object} message - 消息对象
     * @returns {boolean} 发送是否成功
     */
    safeSend(message) {
        for (let attempt = 1; attempt <= this.maxRetries; attempt++) {
            try {
                if (typeof process.send === 'function') {
                    process.send(message);
                    this._log('debug', `消息已发送: ${message.type}`);
                    return true;
                }
                this._log('warn', 'process.send 不可用（非 fork 模式）');
                return false;
            } catch (e) {
                if (attempt < this.maxRetries) {
                    // 短暂等待后重试
                    const delay = this.retryDelayBase * attempt;
                    this._log('warn', `发送失败 (尝试 ${attempt}/${this.maxRetries})，${delay}ms 后重试`);
                    this._syncSleep(delay);
                }
            }
        }
        this._log('error', `消息发送失败，已重试 ${this.maxRetries} 次`);
        return false;
    }

    /**
     * 同步睡眠（用于重试间隔）
     * @private
     * @param {number} ms - 毫秒数
     */
    _syncSleep(ms) {
        const { execSync } = require('child_process');
        try {
            execSync(`sleep ${ms}ms 2>/dev/null || true`, { timeout: ms + 1000 });
        } catch (e) {
            // 忽略 sleep 失败
        }
    }

    /**
     * 等待 IPC 就绪
     * 循环检查 process.send 是否可用
     *
     * @param {number} timeoutMs - 超时时间 (ms)
     * @returns {Promise<boolean>} 是否就绪
     */
    async waitForReady(timeoutMs = 5000) {
        const startTime = Date.now();
        while (Date.now() - startTime < timeoutMs) {
            if (typeof process.send === 'function') {
                this._ready = true;
                this._log('info', 'IPC 通道已就绪');
                return true;
            }
            await new Promise(r => setTimeout(r, 100));
        }
        this._log('warn', `IPC 通道未就绪 (超时 ${timeoutMs}ms)`);
        return typeof process.send === 'function';
    }

    /**
     * 发送 READY 信号
     */
    notifyReady() {
        this.safeSend(createMessage(MessageTypes.READY));
        this._log('info', 'READY 信号已发送');
    }

    /**
     * 通知任务开始
     * @param {string} matchId - 比赛 ID
     */
    notifyTaskStart(matchId) {
        this.safeSend(taskStartMessage(matchId));
    }

    /**
     * 通知任务成功
     * @param {string} matchId - 比赛 ID
     * @param {Object} metrics - 性能指标
     * @param {number} metrics.responseTime - 响应时间 (ms)
     * @param {number} metrics.rawSize - 数据大小 (bytes)
     */
    notifyTaskSuccess(matchId, metrics = {}) {
        const { responseTime = 0, rawSize = 0 } = metrics;
        this.safeSend(taskSuccessMessage(matchId, responseTime, rawSize));
    }

    /**
     * 通知任务失败
     * @param {string} matchId - 比赛 ID
     * @param {string} error - 错误信息
     */
    notifyTaskFailed(matchId, error) {
        this.safeSend(taskFailedMessage(matchId, error));
    }

    /**
     * 通知任务需要重试
     * @param {string} matchId - 比赛 ID
     * @param {string} error - 错误信息
     * @param {number} retryCount - 重试次数
     * @param {number} backoffDelay - 退避延时 (ms)
     */
    notifyTaskRetry(matchId, error, retryCount, backoffDelay) {
        this.safeSend(taskRetryMessage(matchId, error, retryCount, backoffDelay));
    }

    /**
     * 通知 Worker 熔断
     * @param {Object} payload - 熔断信息
     */
    notifyCircuitBreak(payload) {
        this.safeSend({
            type: MessageTypes.WORKER_CIRCUIT_BREAK,
            workerId: this.workerId,
            ...payload
        });
    }

    /**
     * 通知 Worker 进入冷却
     * @param {Object} payload - 冷却信息
     */
    notifyCoolDown(payload) {
        this.safeSend({
            type: MessageTypes.WORKER_COOL_DOWN,
            workerId: this.workerId,
            ...payload
        });
    }

    /**
     * 检查 IPC 是否可用
     * @returns {boolean}
     */
    isAvailable() {
        return typeof process.send === 'function';
    }

    /**
     * 检查是否已就绪
     * @returns {boolean}
     */
    isReady() {
        return this._ready || this.isAvailable();
    }
}

module.exports = {
    WorkerMessenger,
    MessageTypes,
    createMessage
};
