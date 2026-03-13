/**
 * 确定性 ID 生成器
 * ==================
 *
 * V4.46.5 HARDENING: 替换所有 Math.random() ID 生成
 * 遵循"零模拟铁律"：不使用 Math.random() 伪造数据
 *
 * 生成算法：基于时间戳 + 进程 ID + 计数器的确定性组合
 * @module core/id_generator
 * @version V4.46.5
 */

'use strict';

// ============================================================================
// 内部状态
// ============================================================================

/** 进程 ID（用于多进程区分） */
const PROCESS_ID = process.pid.toString(36);

/** 机器标识（取主机名哈希前 4 位） */
const MACHINE_ID = (() => {
    try {
        const hostname = require('os').hostname();
        let hash = 0;
        for (let i = 0; i < hostname.length; i++) {
            hash = ((hash << 5) - hash) + hostname.charCodeAt(i);
            hash = hash & hash; // 转换为 32 位整数
        }
        return Math.abs(hash).toString(36).substring(0, 4).padStart(4, '0');
    } catch {
        return 'xxxx';
    }
})();

/** 全局计数器（单进程内递增） */
let globalCounter = 0;

/** 上次时间戳（用于检测时间回拨） */
let lastTimestamp = 0;

// ============================================================================
// ID 生成函数
// ============================================================================

/**
 * 生成确定性 Trace ID
 * 格式: trace_{timestamp}_{machine}_{pid}_{counter}
 * @param {string} [prefix] - ID 前缀
 * @returns {string} 确定性唯一 ID
 */
function generateDeterministicId(prefix = 'trace') {
    const now = Date.now();

    // 检测时间回拨，防止 ID 重复
    if (now <= lastTimestamp) {
        globalCounter++;
    } else {
        lastTimestamp = now;
    }

    // 递增计数器（36 进制，更紧凑）
    const counter = (globalCounter++).toString(36);

    // 组合：前缀_时间戳_机器_PID_计数器
    return `${prefix}_${now}_${MACHINE_ID}_${PROCESS_ID}_${counter}`;
}

/**
 * 生成 Session ID
 * 格式: SESSION-{type}-{timestamp}-{counter}
 * @param {string} type - Session 类型（如 WORKER, SWARM, LOCK）
 * @param {number} [identifier] - 可选标识符（如 Worker ID）
 * @returns {string} Session ID
 */
function generateSessionId(type, identifier) {
    const now = Date.now();
    const counter = (globalCounter++).toString(36);

    if (identifier !== undefined) {
        return `${type}-${identifier}-${now}-${counter}`;
    }
    return `${type}-${now}-${counter}`;
}

/**
 * 生成 Lock ID
 * 格式: LOCK-{resource}-{timestamp}-{counter}
 * @param {string|number} resource - 资源标识（如端口号）
 * @returns {string} Lock ID
 */
function generateLockId(resource) {
    const now = Date.now();
    const counter = (globalCounter++).toString(36);
    return `LOCK-${resource}-${now}-${counter}`;
}

/**
 * 生成 Request ID
 * 格式: REQ-{timestamp}-{machine}-{counter}
 * @returns {string} Request ID
 */
function generateRequestId() {
    return generateDeterministicId('REQ');
}

/**
 * 生成短 ID（用于日志、追踪等）
 * 格式: {timestamp后6位}{counter 36进制}
 * @returns {string} 短 ID
 */
function generateShortId() {
    const now = Date.now();
    const timestampSuffix = now.toString().slice(-6);
    const counter = (globalCounter++).toString(36).padStart(4, '0');
    return `${timestampSuffix}${counter}`;
}

// ============================================================================
// 向后兼容：generateTraceId 别名
// ============================================================================

/**
 * 生成 Trace ID（向后兼容）
 * @returns {string}
 */
function generateTraceId() {
    return generateDeterministicId('trace');
}

// ============================================================================
// 导出
// ============================================================================

module.exports = {
    generateDeterministicId,
    generateSessionId,
    generateLockId,
    generateRequestId,
    generateShortId,
    generateTraceId,  // 向后兼容
    // 内部状态导出（用于测试）
    _getProcessId: () => PROCESS_ID,
    _getMachineId: () => MACHINE_ID,
    _getCounter: () => globalCounter,
};
