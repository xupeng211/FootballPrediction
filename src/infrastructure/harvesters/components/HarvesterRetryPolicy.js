'use strict';

const { getErrorAuditor, ErrorType } = require('../../../core/harvesters/ErrorAuditor');
const { getAutoAuthManager } = require('../../auth/AutoAuthManager');

/**
 * HarvesterRetryPolicy - 收割器重试策略
 * ====================================
 *
 * 统一管理：
 * - 错误分类
 * - 可重试判断
 * - 数据库/文件错误归类
 * - 指数退避
 * - 重试过程中的端口切换与 Session 清理
 */
class HarvesterRetryPolicy {
    /**
     * @param {object} [config]
     * @param {object} [config.errorAuditor]
     * @param {number} [config.baseBackoffMs=1000]
     * @param {number} [config.maxBackoffMs=8000]
     * @param {number} [config.cooldownThreshold=3]
     * @param {number} [config.cooldownMs=30000]
     */
    constructor(config = {}) {
        this.errorAuditor = config.errorAuditor || getErrorAuditor();
        this.baseBackoffMs = config.baseBackoffMs || 1000;
        this.maxBackoffMs = config.maxBackoffMs || 8000;
        this.cooldownThreshold = config.cooldownThreshold || 3;
        this.cooldownMs = config.cooldownMs || 30000;
    }

    /**
     * @param {object} errorAuditor
     */
    setErrorAuditor(errorAuditor) {
        this.errorAuditor = errorAuditor || getErrorAuditor();
    }

    /**
     * @param {Error|string} error
     * @returns {boolean}
     */
    isRetryableError(error) {
        return this.errorAuditor.isRetryableError(error);
    }

    /**
     * @param {string} errorMessage
     * @returns {string}
     */
    classifyError(errorMessage) {
        return this.errorAuditor.classifyError(errorMessage);
    }

    /**
     * @param {Error} error
     * @returns {string}
     */
    classifyDatabaseError(error) {
        const message = (error?.message || '').toLowerCase();

        if (message.includes('duplicate key') || error?.code === '23505') {
            return 'DUPLICATE_KEY';
        }
        if (
            message.includes('syntax error') ||
            message.includes('sql injection') ||
            message.includes('unterminated quoted string') ||
            error?.code === '42601'
        ) {
            return 'SQL_SYNTAX_ERROR';
        }
        if (
            message.includes('econnrefused') ||
            message.includes('connection') ||
            error?.code === 'ECONNREFUSED'
        ) {
            return 'CONNECTION_ERROR';
        }
        if (
            message.includes('timeout') ||
            message.includes('timed out') ||
            error?.code === 'ETIMEDOUT'
        ) {
            return 'TIMEOUT';
        }

        return 'UNKNOWN';
    }

    /**
     * @param {Error} error
     * @returns {string}
     */
    classifyFileError(error) {
        const message = (error?.message || '').toLowerCase();

        if (message.includes('eacces') || message.includes('permission denied')) {
            return 'PERMISSION_DENIED';
        }
        if (message.includes('enospc') || message.includes('no space left on device')) {
            return 'NO_SPACE';
        }

        return 'UNKNOWN';
    }

    /**
     * 指数退避：第 1 次重试为 2s，随后 4s、8s，最高封顶。
     * @param {number} attempt
     * @returns {number}
     */
    getRecommendedBackoff(attempt) {
        const normalizedAttempt = Math.max(1, Number.isFinite(attempt) ? attempt : 1);
        return Math.min(this.baseBackoffMs * Math.pow(2, normalizedAttempt), this.maxBackoffMs);
    }

    /**
     * 获取冷却秒数，避免日志文案与配置脱节。
     * @returns {number}
     */
    getCooldownSeconds() {
        return Math.max(1, Math.round(this.cooldownMs / 1000));
    }

    /**
     * 执行带重试的收割
     * @param {object} harvester
     * @param {object} match
     * @param {number} index
     * @param {number} maxRetries
     * @returns {Promise<object>}
     */
    async executeWithRetry(harvester, match, index, maxRetries = 3) {
        const { match_id, home_team, away_team } = match;
        const workerId = (index % harvester.config.maxWorkers) + 1;

        console.log(`[DEBUG] harvestWithRetry called: Match ${match_id}, Worker ${workerId}`);

        let lastError = null;
        let consecutiveSizeTooSmall = 0;

        for (let attempt = 1; attempt <= maxRetries; attempt++) {
            try {
                console.log(`[DEBUG] Attempt ${attempt} for match ${match_id}`);
                const result = await this._executeWithWatchdog(
                    () => harvester._harvestSingleMatch(match, index, attempt),
                    {
                        timeoutMs: harvester.config.harvestTimeoutMs,
                        matchId: match_id,
                        workerId,
                        onTimeout: async () => {
                            await harvester._closeWorkerContext?.(workerId, 'WATCHDOG_TIMEOUT');
                        }
                    }
                );

                if (result.success) {
                    if (attempt > 1) {
                        console.log(`✅ [RETRY-${attempt}] ${home_team} vs ${away_team} 重试成功`);
                        harvester._recordRetry();
                    }
                    harvester._recordSuccess();
                    return result;
                }

                if (result.error && result.error.includes('SIZE_TOO_SMALL')) {
                    consecutiveSizeTooSmall++;
                    if (consecutiveSizeTooSmall >= this.cooldownThreshold) {
                        console.log(
                            `⏸️  [COOLDOWN] Worker 休息 ${this.getCooldownSeconds()} 秒 (连续 ${consecutiveSizeTooSmall} 次 SIZE_TOO_SMALL)...`
                        );
                        await harvester._delay(this.cooldownMs);
                        consecutiveSizeTooSmall = 0;
                    }
                }

                if (!this.isRetryableError(new Error(result.error))) {
                    const errorType = this.classifyError(result.error);
                    if (errorType === ErrorType.BLOCKED) {
                        await harvester._triggerAutoAuth(index, result.error);
                    }
                    harvester._recordFailure();
                    return result;
                }

                lastError = result.error;
            } catch (error) {
                lastError = error.message;

                if (!this.isRetryableError(error)) {
                    harvester._recordFailure();
                    return {
                        success: false,
                        match_id,
                        error: error.message,
                        attempts: attempt,
                    };
                }
            }

            if (attempt < maxRetries) {
                await this._prepareNextAttempt(harvester, {
                    attempt,
                    index,
                    homeTeam: home_team,
                    awayTeam: away_team
                });
            }
        }

        harvester._recordFailure();
        return {
            success: false,
            match_id,
            error: `重试 ${maxRetries} 次后仍失败: ${lastError}`,
            attempts: maxRetries,
        };
    }

    /**
     * @private
     * @param {object} harvester
     * @param {object} context
     * @param {number} context.attempt
     * @param {number} context.index
     * @param {string} context.homeTeam
     * @param {string} context.awayTeam
     */
    async _prepareNextAttempt(harvester, context) {
        const { attempt, index, homeTeam, awayTeam } = context;
        const workerId = (index % harvester.config.maxWorkers) + 1;
        const backoffMs = this.getRecommendedBackoff(attempt);
        const currentIdentity = harvester.networkManager?.getWorkerIdentity(workerId);

        if (currentIdentity) {
            const newIdentity = await harvester.networkManager.forceReassignPort(workerId, currentIdentity.proxy.port);
            const newPort = newIdentity?.proxy?.port || newIdentity?.port || newIdentity;

            if (harvester.networkManager.sessionManager) {
                await harvester.networkManager.sessionManager.clearSession(currentIdentity.proxy.port);
                console.log(`🧹 [RETRY-${attempt + 1}] 清理旧 Cookie...`);
            }

            console.log(
                `🔄 [RETRY-${attempt + 1}] ${homeTeam} vs ${awayTeam} 切换端口 ${currentIdentity.proxy.port} → ${newPort}...`
            );
        }

        await harvester._delay(backoffMs);
    }

    /**
     * BLOCKED 错误恢复：清 Session、切端口、热刷新身份、清 Context。
     * @param {object} harvester
     * @param {number} index
     * @param {string} errorMessage
     * @returns {Promise<void>}
     */
    async handleBlockedRecovery(harvester, index, errorMessage) {
        const workerId = (index % harvester.config.maxWorkers) + 1;

        console.log('\n');
        console.log('═══════════════════════════════════════════════════════════════');
        console.log('  \x1b[33m[AUTO-AUTH]\x1b[0m 检测到 BLOCKED 错误，触发自动身份刷新...');
        console.log(`  错误详情: ${errorMessage}`);
        console.log('═══════════════════════════════════════════════════════════════');

        try {
            let currentPort = null;
            let newPort = null;

            if (harvester.networkManager?.sessionManager) {
                const identity = harvester.networkManager.getWorkerIdentity(workerId);
                if (identity?.proxy?.port) {
                    currentPort = identity.proxy.port;
                    await harvester.networkManager.sessionManager.clearSession(currentPort);
                    console.log(`  🧹 [AUTO-AUTH] 已清理 Worker ${workerId} 的旧 Session (Port ${currentPort})`);
                }
            }

            if (harvester.networkManager) {
                const currentIdentity = harvester.networkManager.getWorkerIdentity(workerId);
                if (currentIdentity?.proxy?.port) {
                    const newIdentity = await harvester.networkManager.forceReassignPort(workerId, currentIdentity.proxy.port);
                    const newPortValue = newIdentity?.proxy?.port || newIdentity?.port || newIdentity;
                    console.log(`  🔄 [AUTO-AUTH] 端口切换: ${currentIdentity.proxy.port} → ${newPortValue}`);
                    newPort = newPortValue;
                }
            }

            if (newPort) {
                const autoAuthManager = harvester.autoAuthManager || getAutoAuthManager();
                const refreshResult = await autoAuthManager.refreshSession(workerId, newPort);

                if (refreshResult.success) {
                    console.log(`  🔑 [AUTO-AUTH] Session 热刷新成功 (${refreshResult.cookieCount} cookies)`);
                } else {
                    console.log(`  ⚠️ [AUTO-AUTH] Session 刷新失败: ${refreshResult.error}`);
                    console.log(`  💡 提示: 请在宿主机运行 'node scripts/capture_auth.js --port ${newPort}' 手动捕获身份`);
                }
            }

            if (typeof harvester._closeWorkerContext === 'function') {
                const closed = await harvester._closeWorkerContext(workerId, 'AUTO-AUTH');
                if (closed) {
                    console.log(`  🧹 [AUTO-AUTH] 已清理 Worker ${workerId} 的旧 Context`);
                }
            }

            console.log('  ✅ [AUTO-AUTH] 身份刷新完成，下次请求将使用新身份\n');
        } catch (error) {
            console.error(`  ❌ [AUTO-AUTH] 身份刷新失败: ${error.message}`);
            console.log('  ⚠️  将在下次收割时重试...\n');
        }
    }

    async _executeWithWatchdog(task, options = {}) {
        const timeoutMs = Number.isFinite(options.timeoutMs) && options.timeoutMs > 0
            ? options.timeoutMs
            : 120000;

        let timeoutId = null;

        try {
            return await Promise.race([
                Promise.resolve().then(task),
                new Promise((_, reject) => {
                    timeoutId = setTimeout(async () => {
                        try {
                            await options.onTimeout?.();
                        } catch (timeoutCleanupError) {
                            // 看门狗清理失败不应吞掉主超时错误
                        }

                        const timeoutError = new Error(
                            `WATCHDOG_TIMEOUT: ${options.matchId || 'unknown_match'} 超过 ${timeoutMs}ms`
                        );
                        timeoutError.code = 'WATCHDOG_TIMEOUT';
                        timeoutError.workerId = options.workerId;
                        reject(timeoutError);
                    }, timeoutMs);
                })
            ]);
        } finally {
            if (timeoutId) {
                clearTimeout(timeoutId);
            }
        }
    }
}

module.exports = {
    HarvesterRetryPolicy,
};
