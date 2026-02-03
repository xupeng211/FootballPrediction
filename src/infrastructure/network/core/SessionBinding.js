/**
 * SessionBinding - V1.0.0 [Genesis.NetworkShield] Session-Aware Proxy Rotation
 * ============================================================================
 *
 * 智能轮换策略：Session 绑定确保一个浏览器会话从打开到关闭，始终锁定
 * 在同一个干净 IP 上，避免中途换 IP 触发 WebSocket 断开。
 *
 * Core Features:
 * - Session 绑定 (Session binding)
 * - 一对一映射 (One-to-one mapping)
 * - 超时自动释放 (Auto-release on timeout)
 * - 清理过期会话 (Cleanup expired sessions)
 * - 会话追踪 (Session tracking)
 *
 * @module network/core/SessionBinding
 * @version V1.0.0
 * @since 2026-02-03
 * @author [Genesis.NetworkShield]
 */

'use strict';

// ============================================================================
// SESSION CLASS
// ============================================================================

class ProxySession {
    /**
     * @param {string} sessionId - 会话 ID
     * @param {number} port - 代理端口
     * @param {number} timeoutMinutes - 超时时间（分钟）
     */
    constructor(sessionId, port, timeoutMinutes = 30) {
        this.sessionId = sessionId;
        this.port = port;
        this.createdAt = new Date();
        this.lastUsedAt = new Date();
        this.expiresAt = new Date(Date.now() + timeoutMinutes * 60 * 1000);
        this.timeoutMinutes = timeoutMinutes;
        this.isActive = true;
    }

    /**
     * 检查会话是否过期
     * @returns {boolean} 是否过期
     */
    isExpired() {
        return new Date() > this.expiresAt;
    }

    /**
     * 刷新会话有效期
     */
    refresh() {
        this.lastUsedAt = new Date();
        this.expiresAt = new Date(Date.now() + this.timeoutMinutes * 60 * 1000);
    }

    /**
     * 关闭会话
     */
    close() {
        this.isActive = false;
    }

    /**
     * 获取会话信息
     * @returns {Object} 会话信息
     */
    getInfo() {
        return {
            sessionId: this.sessionId,
            port: this.port,
            createdAt: this.createdAt.toISOString(),
            lastUsedAt: this.lastUsedAt.toISOString(),
            expiresAt: this.expiresAt.toISOString(),
            isActive: this.isActive,
            remainingMinutes: Math.max(0, Math.floor(
                (this.expiresAt - new Date()) / 60000
            ))
        };
    }
}

// ============================================================================
// SESSION BINDING MANAGER
// ============================================================================

class SessionBindingManager {
    constructor(options = {}) {
        this.sessionTimeoutMinutes = options.sessionTimeoutMinutes || 30;
        this.sessions = new Map(); // sessionId -> ProxySession
        this.portToSession = new Map(); // port -> sessionId
        this.nextSessionId = 1;
        this.logger = options.logger || console;

        // 清理定时器
        this._cleanupInterval = null;
        this._startCleanupTask();
    }

    /**
     * 创建新会话并分配代理端口
     * @param {number} port - 代理端口
     * @param {Object} metadata - 会话元数据
     * @returns {ProxySession} 会话对象
     */
    async createSession(port, metadata = {}) {
        // 检查端口是否已被占用
        if (this.portToSession.has(port)) {
            const existingSessionId = this.portToSession.get(port);
            const existingSession = this.sessions.get(existingSessionId);

            if (existingSession && existingSession.isActive && !existingSession.isExpired()) {
                throw new Error(
                    `Port ${port} is already in use by active session ${existingSessionId}`
                );
            } else {
                // 清理过期会话
                this.releaseSession(existingSessionId);
            }
        }

        // 创建新会话
        const sessionId = `SESSION-${this.nextSessionId++}`;
        const session = new ProxySession(sessionId, port, this.sessionTimeoutMinutes);
        session.metadata = metadata;

        this.sessions.set(sessionId, session);
        this.portToSession.set(port, sessionId);

        this._log('info',
            `Session created: ${sessionId} -> Port ${port} ` +
            `(expires in ${this.sessionTimeoutMinutes}m)`
        );

        return session;
    }

    /**
     * 获取会话
     * @param {string} sessionId - 会话 ID
     * @returns {ProxySession|null} 会话对象
     */
    getSession(sessionId) {
        return this.sessions.get(sessionId) || null;
    }

    /**
     * 获取端口绑定的会话
     * @param {number} port - 代理端口
     * @returns {ProxySession|null} 会话对象
     */
    getSessionByPort(port) {
        const sessionId = this.portToSession.get(port);
        return sessionId ? this.sessions.get(sessionId) : null;
    }

    /**
     * 刷新会话有效期
     * @param {string} sessionId - 会话 ID
     * @returns {boolean} 是否成功
     */
    refreshSession(sessionId) {
        const session = this.sessions.get(sessionId);
        if (!session) return false;

        if (session.isExpired()) {
            this.releaseSession(sessionId);
            return false;
        }

        session.refresh();
        this._log('debug', `Session refreshed: ${sessionId}`);
        return true;
    }

    /**
     * 释放会话
     * @param {string} sessionId - 会话 ID
     * @returns {boolean} 是否成功
     */
    releaseSession(sessionId) {
        const session = this.sessions.get(sessionId);
        if (!session) return false;

        session.close();
        this.portToSession.delete(session.port);
        this.sessions.delete(sessionId);

        this._log('info', `Session released: ${sessionId} (was port ${session.port})`);
        return true;
    }

    /**
     * 获取所有活跃会话
     * @returns {Array<ProxySession>} 活跃会话列表
     */
    getActiveSessions() {
        return Array.from(this.sessions.values()).filter(s => s.isActive && !s.isExpired());
    }

    /**
     * 获取会话统计
     * @returns {Object} 统计信息
     */
    getStatistics() {
        const activeSessions = this.getActiveSessions();
        const expiredSessions = Array.from(this.sessions.values()).filter(s => s.isExpired());

        return {
            totalSessions: this.sessions.size,
            activeSessions: activeSessions.length,
            expiredSessions: expiredSessions.length,
            occupiedPorts: Array.from(this.portToSession.keys()),
            nextSessionId: this.nextSessionId
        };
    }

    /**
     * 清理过期会话
     * @returns {number} 清理的会话数量
     */
    cleanupExpiredSessions() {
        let cleaned = 0;

        for (const [sessionId, session] of this.sessions.entries()) {
            if (session.isExpired() || !session.isActive) {
                this.releaseSession(sessionId);
                cleaned++;
            }
        }

        if (cleaned > 0) {
            this._log('info', `Cleaned up ${cleaned} expired session(s)`);
        }

        return cleaned;
    }

    /**
     * 获取空闲的可用端口
     * @param {Array<number>} allPorts - 所有端口列表
     * @returns {Array<number>} 空闲端口列表
     */
    getAvailablePorts(allPorts) {
        const occupiedPorts = new Set(this.portToSession.keys());
        return allPorts.filter(p => !occupiedPorts.has(p));
    }

    /**
     * 关闭管理器并清理所有会话
     */
    shutdown() {
        if (this._cleanupInterval) {
            clearInterval(this._cleanupInterval);
            this._cleanupInterval = null;
        }

        // 释放所有会话
        for (const sessionId of this.sessions.keys()) {
            this.releaseSession(sessionId);
        }

        this._log('info', 'SessionBindingManager shut down');
    }

    // ========================================================================
    // PRIVATE METHODS
    // ========================================================================

    /**
     * 启动清理任务
     * @private
     */
    _startCleanupTask() {
        // 每分钟清理一次过期会话
        this._cleanupInterval = setInterval(() => {
            this.cleanupExpiredSessions();
        }, 60000);
    }

    /**
     * 记录日志
     * @private
     * @param {string} level - 日志级别
     * @param {string} message - 日志消息
     */
    _log(level, message) {
        const logMessage = `[SessionBinding] ${message}`;

        switch (level) {
            case 'debug':
                this.logger.debug?.(logMessage) || console.debug(logMessage);
                break;
            case 'info':
                this.logger.info?.(logMessage) || console.info(logMessage);
                break;
            case 'warn':
                this.logger.warn?.(logMessage) || console.warn(logMessage);
                break;
            case 'error':
                this.logger.error?.(logMessage) || console.error(logMessage);
                break;
            default:
                console.log(logMessage);
        }
    }
}

module.exports = {
    ProxySession,
    SessionBindingManager
};
