/**
 * Dashboard - 终端仪表盘
 * ==============================================
 *
 * 负责:
 * - 渲染 Worker 状态
 * - 进度条显示
 * - 统计报告
 *
 * 纯 UI 逻辑，不包含任何业务逻辑
 *
 * @module core/ui/Dashboard
 * @version V174.0.0
 */

'use strict';

/**
 * Dashboard - 终端仪表盘
 */
class Dashboard {
    /**
     * @param {Object} options - 配置选项
     * @param {number} options.total - 总任务数
     * @param {string} options.title - 标题
     * @param {boolean} options.enabled - 是否启用
     */
    constructor(options = {}) {
        this.total = options.total ?? 0;
        this.title = options.title ?? 'V174-REFRESH 装甲群收割器';
        this.enabled = options.enabled ?? true;

        // 计数器
        this.processed = 0;
        this.success = 0;
        this.failed = 0;
        this.retried = 0;
        this.skipped = 0;

        // 时间
        this.startTime = Date.now();

        // Worker 状态
        this.workers = new Map();
    }

    /**
     * 更新 Worker 状态
     * @param {number} workerId - Worker ID
     * @param {string} status - 状态
     * @param {Object} data - 附加数据
     */
    updateWorker(workerId, status, data = {}) {
        const existing = this.workers.get(workerId) || {};

        this.workers.set(workerId, {
            status,
            success: data.success ?? existing.success ?? 0,
            failed: data.failed ?? existing.failed ?? 0,
            currentMatch: data.currentMatch || null,
            port: data.port ?? existing.port,
            lastUpdate: Date.now()
        });

        if (this.enabled) {
            this.render();
        }
    }

    /**
     * 记录结果
     * @param {boolean} success - 是否成功
     * @param {boolean} isRetry - 是否重试
     */
    recordResult(success, isRetry = false) {
        this.processed++;
        if (success) this.success++;
        else this.failed++;
        if (isRetry) this.retried++;
    }

    /**
     * 获取状态图标
     * @private
     */
    _getStatusIcon(status) {
        const icons = {
            'RUNNING': '🔥',
            'SUCCESS': '✅',
            'WAITING': '⏳',
            'ERROR': '❌',
            'COOLING': '❄️',
            'STOPPED': '🛑',
            'RETRYING': '🔄',
            'READY': '🟢',
            'RECOVERING': '🔧',
            'STARTING': '🚀'
        };
        return icons[status] || '❓';
    }

    /**
     * 格式化持续时间
     * @private
     */
    _formatDuration(ms) {
        if (!ms || ms < 0) return '--';
        const hours = Math.floor(ms / 3600000);
        const minutes = Math.floor((ms % 3600000) / 60000);
        if (hours > 0) {
            return `${hours}h ${minutes}m`;
        }
        return `${minutes}m`;
    }

    /**
     * 渲染仪表盘
     */
    render() {
        if (!this.enabled) return;

        console.clear();
        console.log('');
        console.log('═'.repeat(80));
        console.log(`  ${this.title}`);
        console.log('═'.repeat(80));
        console.log('');

        // Worker 状态
        console.log('┌' + '─'.repeat(78) + '┐');

        for (const [workerId, info] of this.workers) {
            const statusIcon = this._getStatusIcon(info.status);
            const portStr = `[Port ${info.port}]`.padEnd(12);
            const statusStr = `[${info.status}]`.padEnd(14);
            const successStr = `✅ ${info.success}`.padEnd(10);
            const failedStr = `❌ ${info.failed}`;
            const matchStr = info.currentMatch
                ? ` | ${info.currentMatch.substring(0, 30)}`
                : '';

            console.log(
                `│ Worker ${workerId}: ${portStr} ${statusIcon} ${statusStr} ${successStr} ${failedStr}${matchStr}`
            );
        }

        console.log('└' + '─'.repeat(78) + '┘');
        console.log('');

        // 总进度
        const pct = this.processed > 0
            ? ((this.processed / this.total) * 100).toFixed(1)
            : '0.0';
        const bar = '█'.repeat(Math.floor(parseFloat(pct) / 5)) +
            '░'.repeat(20 - Math.floor(parseFloat(pct) / 5));

        const elapsed = Date.now() - this.startTime;
        const avgTime = this.processed > 0 ? elapsed / this.processed : 0;
        const remaining = avgTime * (this.total - this.processed);

        console.log('─'.repeat(80));
        console.log(`  总进度: [${bar}] ${pct}% | ${this.processed}/${this.total}`);
        console.log(`  成功: ${this.success} | 失败: ${this.failed} | 重试: ${this.retried} | 跳过: ${this.skipped}`);
        console.log(`  已用: ${this._formatDuration(elapsed)} | 预估剩余: ${this._formatDuration(remaining)}`);
        console.log('─'.repeat(80));
    }

    /**
     * 打印最终报告
     */
    summary() {
        const elapsed = Date.now() - this.startTime;
        const successRate = this.processed > 0
            ? ((this.success / this.processed) * 100).toFixed(1)
            : '0.0';

        console.log('');
        console.log('═'.repeat(80));
        console.log('  收割完成报告');
        console.log('═'.repeat(80));
        console.log(`  总计: ${this.total} 场`);
        console.log(`  成功: ${this.success}`);
        console.log(`  失败: ${this.failed}`);
        console.log(`  重试: ${this.retried}`);
        console.log(`  成功率: ${successRate}%`);
        console.log(`  总耗时: ${this._formatDuration(elapsed)}`);
        console.log('═'.repeat(80));
    }

    /**
     * 获取状态快照 (用于 JSON 序列化)
     * @returns {Object}
     */
    getSnapshot() {
        return {
            total: this.total,
            processed: this.processed,
            success: this.success,
            failed: this.failed,
            retried: this.retried,
            skipped: this.skipped,
            progressPct: this.total > 0
                ? ((this.processed / this.total) * 100).toFixed(1)
                : '0.0',
            elapsedMs: Date.now() - this.startTime,
            startTime: new Date(this.startTime).toISOString(),
            workers: this._getWorkerSnapshot()
        };
    }

    /**
     * 获取 Worker 快照
     * @private
     */
    _getWorkerSnapshot() {
        const snapshot = {};
        for (const [workerId, info] of this.workers) {
            snapshot[workerId] = {
                status: info.status,
                success: info.success,
                failed: info.failed,
                port: info.port,
                currentMatch: info.currentMatch
            };
        }
        return snapshot;
    }

    /**
     * 重置仪表盘
     */
    reset() {
        this.processed = 0;
        this.success = 0;
        this.failed = 0;
        this.retried = 0;
        this.skipped = 0;
        this.startTime = Date.now();
        this.workers.clear();
    }
}

module.exports = {
    Dashboard
};
