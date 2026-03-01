/**
 * MessageTypes - IPC 消息类型常量定义
 * ==============================================
 *
 * 定义 Worker 与 Master 之间通信的所有消息类型
 *
 * @module core/ipc/MessageTypes
 * @version V174.0.0
 */

'use strict';

/**
 * IPC 消息类型枚举
 */
const MessageTypes = {
    // ========================================================================
    // Worker -> Master 消息
    // ========================================================================

    /** Worker 已就绪，可以接收任务 */
    READY: 'READY',

    /** 任务开始执行 */
    TASK_START: 'TASK_START',

    /** 任务执行成功 */
    TASK_SUCCESS: 'TASK_SUCCESS',

    /** 任务执行失败 */
    TASK_FAILED: 'TASK_FAILED',

    /** 任务需要重试 */
    TASK_RETRY: 'TASK_RETRY',

    /** Worker 触发熔断 */
    WORKER_CIRCUIT_BREAK: 'WORKER_CIRCUIT_BREAK',

    /** Worker 进入冷却模式 */
    WORKER_COOL_DOWN: 'WORKER_COOL_DOWN',

    /** Worker 心跳 */
    HEARTBEAT: 'HEARTBEAT',

    // ========================================================================
    // Master -> Worker 消息
    // ========================================================================

    /** 分配新任务 */
    TASK: 'TASK',

    /** Master 重新分配的重试任务 */
    TASK_RETRY_FROM_MASTER: 'TASK_RETRY_FROM_MASTER',

    /** 关闭 Worker */
    SHUTDOWN: 'SHUTDOWN',

    /** 心跳响应 */
    HEARTBEAT_ACK: 'HEARTBEAT_ACK'
};

/**
 * 创建标准化的消息对象
 * @param {string} type - 消息类型
 * @param {Object} payload - 消息负载
 * @returns {Object} 标准化消息对象
 */
function createMessage(type, payload = {}) {
    return {
        type,
        timestamp: Date.now(),
        ...payload
    };
}

/**
 * 创建任务开始消息
 * @param {string} matchId - 比赛 ID
 * @returns {Object}
 */
function taskStartMessage(matchId) {
    return createMessage(MessageTypes.TASK_START, { matchId });
}

/**
 * 创建任务成功消息
 * @param {string} matchId - 比赛 ID
 * @param {number} responseTime - 响应时间 (ms)
 * @param {number} rawSize - 数据大小 (bytes)
 * @returns {Object}
 */
function taskSuccessMessage(matchId, responseTime, rawSize) {
    return createMessage(MessageTypes.TASK_SUCCESS, { matchId, responseTime, rawSize });
}

/**
 * 创建任务失败消息
 * @param {string} matchId - 比赛 ID
 * @param {string} error - 错误信息
 * @returns {Object}
 */
function taskFailedMessage(matchId, error) {
    return createMessage(MessageTypes.TASK_FAILED, { matchId, error });
}

/**
 * 创建任务重试消息
 * @param {string} matchId - 比赛 ID
 * @param {string} error - 错误信息
 * @param {number} retryCount - 重试次数
 * @param {number} backoffDelay - 退避延时 (ms)
 * @returns {Object}
 */
function taskRetryMessage(matchId, error, retryCount, backoffDelay) {
    return createMessage(MessageTypes.TASK_RETRY, { matchId, error, retryCount, backoffDelay });
}

module.exports = {
    MessageTypes,
    createMessage,
    taskStartMessage,
    taskSuccessMessage,
    taskFailedMessage,
    taskRetryMessage
};
