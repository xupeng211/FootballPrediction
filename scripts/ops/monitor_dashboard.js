/**
 * V173 中央监控大屏 (The Persistent Dashboard)
 * =============================================
 *
 * 轻量级实时监控工具，读取 Master 心跳状态并可视化展示
 * 设计原则：极其轻量，不影响主收割进程
 *
 * 使用方式：
 *   npm run watch
 *   node scripts/ops/monitor_dashboard.js
 *
 * @module scripts/ops/monitor_dashboard
 * @version V173.0.0
 */

'use strict';

const fs = require('fs');
const path = require('path');
const { Client } = require('pg');

// ============================================================================
// 配置
// ============================================================================

const STATUS_FILE = process.env.STATUS_FILE || '/app/logs/live_status.json';
const REFRESH_INTERVAL = parseInt(process.env.REFRESH_INTERVAL) || 5000;  // 5秒刷新

const DB_CONFIG = {
    host: process.env.DB_HOST || 'db',
    port: parseInt(process.env.DB_PORT || '5432'),
    database: process.env.DB_NAME || 'football_db',
    user: process.env.DB_USER || 'football_user',
    password: process.env.DB_PASSWORD || 'your_secure_password_here'
};

// ============================================================================
// 颜色
// ============================================================================

const colors = {
    reset: '\x1b[0m',
    bright: '\x1b[1m',
    dim: '\x1b[2m',
    green: '\x1b[32m',
    yellow: '\x1b[33m',
    red: '\x1b[31m',
    cyan: '\x1b[36m',
    blue: '\x1b[34m',
    magenta: '\x1b[35m',
    bgBlue: '\x1b[44m',
    bgGreen: '\x1b[42m'
};

const c = (text, color) => `${colors[color]}${text}${colors.reset}`;

// ============================================================================
// 监控仪表盘
// ============================================================================

class MonitorDashboard {
    constructor() {
        this.client = null;
        this.lastStatus = null;
        this.running = true;
    }

    async start() {
        console.log('');
        console.log(c('═'.repeat(80), 'bright'));
        console.log(c('  V173 中央监控大屏 - The Persistent Dashboard', 'bright'));
        console.log(c('═'.repeat(80), 'bright'));
        console.log('');
        console.log(`  📡 状态文件: ${STATUS_FILE}`);
        console.log(`  🔄 刷新间隔: ${REFRESH_INTERVAL / 1000}s`);
        console.log(`  ⌨️  按 Ctrl+C 退出`);
        console.log('');

        // 连接数据库
        await this.connectDB();

        // 启动监控循环
        this._startMonitorLoop();

        // 处理退出
        process.on('SIGINT', () => this.stop());
        process.on('SIGTERM', () => this.stop());
    }

    async connectDB() {
        try {
            this.client = new Client({
                ...DB_CONFIG,
                connectionTimeoutMillis: 5000
            });
            await this.client.connect();
        } catch (e) {
            // 数据库可选
            this.client = null;
        }
    }

    async disconnectDB() {
        if (this.client) {
            await this.client.end();
            this.client = null;
        }
    }

    _startMonitorLoop() {
        // 立即渲染一次
        this._render();

        // 定时刷新
        this._interval = setInterval(() => {
            this._render();
        }, REFRESH_INTERVAL);
    }

    _render() {
        // 读取心跳状态
        const status = this._readHeartbeat();

        // 清屏
        console.clear();

        // 标题
        this._renderHeader(status);

        if (!status) {
            console.log('');
            console.log(c('  ⏳ 等待收割器启动...', 'yellow'));
            console.log(c('  提示: 运行 npm run harvest 启动收割任务', 'dim'));
            return;
        }

        // 进度条
        this._renderProgress(status);

        // 计数器
        this._renderCounters(status);

        // 时间统计
        this._renderTiming(status);

        // 代理状态矩阵 (22 端口)
        this._renderProxyMatrix(status);

        // 数据库统计
        this._renderDBStats();

        // 最近活动
        this._renderRecentActivity(status);
    }

    _readHeartbeat() {
        try {
            if (!fs.existsSync(STATUS_FILE)) {
                return null;
            }
            const content = fs.readFileSync(STATUS_FILE, 'utf8');
            return JSON.parse(content);
        } catch (e) {
            return null;
        }
    }

    _renderHeader(status) {
        const now = new Date().toISOString().slice(0, 19).replace('T', ' ');
        const startTime = status?.startTime
            ? new Date(status.startTime).toISOString().slice(0, 19).replace('T', ' ')
            : '--';

        console.log('');
        console.log(c('═'.repeat(80), 'bright'));
        console.log(c('  V173 中央监控大屏', 'bright') + c(' | ', 'dim') + c('实时状态', 'cyan'));
        console.log(c('═'.repeat(80), 'bright'));
        console.log('');
        console.log(`  📅 当前时间: ${c(now, 'cyan')}`);
        console.log(`  🚀 启动时间: ${c(startTime, 'dim')}`);
        console.log(`  📦 版本: ${c(status?.version || 'N/A', 'magenta')}`);
        console.log('');
    }

    _renderProgress(status) {
        const total = status.total || 0;
        const processed = status.processed || 0;
        const pct = parseFloat(status.progressPct) || 0;

        const barWidth = 40;
        const filled = Math.floor((pct / 100) * barWidth);
        const empty = barWidth - filled;

        const bar = c('█'.repeat(filled), 'green') + c('░'.repeat(empty), 'dim');

        console.log(c('─'.repeat(80), 'dim'));
        console.log(`  📊 总进度: [${bar}] ${c(pct + '%', 'bright')}`);
        console.log(`           ${c(processed, 'cyan')} / ${c(total, 'dim')} 场比赛`);
        console.log('');
    }

    _renderCounters(status) {
        const s = status;

        console.log('  📈 实时统计:');
        console.log(`     ✅ 成功: ${c(s.success || 0, 'green')}    ` +
                    `❌ 失败: ${c(s.failed || 0, 'red')}    ` +
                    `🔄 重试: ${c(s.retried || 0, 'yellow')}    ` +
                    `⏭️  跳过: ${c(s.skipped || 0, 'dim')}`);
        console.log('');
    }

    _renderTiming(status) {
        const elapsed = status.elapsedMs || 0;
        const remaining = status.estimatedRemainingMs;

        const elapsedStr = this._formatDuration(elapsed);
        const remainingStr = remaining ? this._formatDuration(remaining) : '--';

        // 计算收割速率
        const rate = elapsed > 0 && status.processed > 0
            ? (status.processed / (elapsed / 3600000)).toFixed(1)
            : '0.0';

        console.log('  ⏱️  时间统计:');
        console.log(`     已用时间: ${c(elapsedStr, 'cyan')}    ` +
                    `预估剩余: ${c(remainingStr, 'yellow')}    ` +
                    `收割速率: ${c(rate + ' 场/h', 'green')}`);
        console.log('');
    }

    _renderProxyMatrix(status) {
        const proxyStatus = status.proxyStatus || {};

        console.log(c('─'.repeat(80), 'dim'));
        console.log('  🔌 代理端口状态矩阵 (22 IP):');
        console.log('');

        // 按 6 列显示
        const ports = Object.keys(proxyStatus).sort((a, b) => parseInt(a) - parseInt(b));
        const rows = [];

        for (let i = 0; i < ports.length; i += 6) {
            const rowPorts = ports.slice(i, i + 6);
            const row = rowPorts.map(port => {
                const info = proxyStatus[port];
                const statusIcon = this._getStatusIcon(info?.status);
                const color = this._getStatusColor(info?.status);
                return ` ${port}:${c(statusIcon, color)}`;
            }).join(' ');
            rows.push('     ' + row);
        }

        rows.forEach(row => console.log(row));

        // 图例
        console.log('');
        console.log('  图例: ' +
            c('🔥 运行中 ', 'green') +
            c('✅ 成功 ', 'cyan') +
            c('⏳ 等待 ', 'yellow') +
            c('❌ 错误 ', 'red') +
            c('💤 空闲 ', 'dim'));
        console.log('');
    }

    _renderDBStats() {
        if (!this.client) return;

        // 异步查询，不阻塞渲染
        this._fetchDBStats().then(stats => {
            if (stats) {
                console.log(c('─'.repeat(80), 'dim'));
                console.log('  🗄️  数据库资产:');
                console.log(`     总比赛: ${c(stats.totalMatches, 'cyan')}    ` +
                            `已完成: ${c(stats.finishedMatches, 'green')}    ` +
                            `黄金数据: ${c(stats.goldData, 'yellow')}    ` +
                            `成功率: ${c(stats.successRate + '%', 'bright')}`);
                console.log('');
            }
        }).catch(() => {});
    }

    async _fetchDBStats() {
        if (!this.client) return null;

        try {
            const query = `
                SELECT
                    COUNT(DISTINCT m.match_id) as total_matches,
                    COUNT(CASE WHEN m.is_finished = true THEN 1 END) as finished_matches,
                    COUNT(CASE WHEN r.match_id IS NOT NULL AND LENGTH(r.l2_raw_json::text) > 5000 THEN 1 END) as gold_data
                FROM matches m
                LEFT JOIN raw_match_data r ON m.match_id = r.match_id
            `;
            const result = await this.client.query(query);
            const row = result.rows[0];

            const total = parseInt(row.finished_matches) || 0;
            const gold = parseInt(row.gold_data) || 0;
            const successRate = total > 0 ? ((gold / total) * 100).toFixed(1) : '0.0';

            return {
                totalMatches: row.total_matches,
                finishedMatches: row.finished_matches,
                goldData: gold,
                successRate
            };
        } catch (e) {
            return null;
        }
    }

    _renderRecentActivity(status) {
        const workers = status.workers || {};
        const activities = [];

        for (const [workerId, info] of Object.entries(workers)) {
            if (info.currentMatch) {
                activities.push({
                    workerId,
                    port: info.port,
                    match: info.currentMatch,
                    status: info.status
                });
            }
        }

        if (activities.length > 0) {
            console.log(c('─'.repeat(80), 'dim'));
            console.log('  🔥 正在处理:');
            activities.slice(0, 3).forEach(a => {
                const statusIcon = this._getStatusIcon(a.status);
                const color = this._getStatusColor(a.status);
                console.log(`     W${a.workerId} [${a.port}]: ${c(statusIcon, color)} ${a.match.substring(0, 40)}`);
            });
            console.log('');
        }

        // 最近完成的比赛
        if (status.lastMatchId) {
            console.log(`  📝 最近完成: ${c(status.lastMatchId, 'dim')}`);
            console.log('');
        }

        // 页脚
        console.log(c('─'.repeat(80), 'dim'));
        console.log(c(`  刷新于 ${new Date().toISOString().slice(11, 19)} | 按 Ctrl+C 退出`, 'dim'));
    }

    _getStatusIcon(status) {
        switch (status) {
            case 'RUNNING': return '🔥';
            case 'SUCCESS': return '✅';
            case 'WAITING': return '⏳';
            case 'ERROR': return '❌';
            case 'COOLING': return '❄️';
            case 'STOPPED': return '🛑';
            case 'RETRYING': return '🔄';
            case 'IDLE': return '💤';
            default: return '❓';
        }
    }

    _getStatusColor(status) {
        switch (status) {
            case 'RUNNING': return 'green';
            case 'SUCCESS': return 'cyan';
            case 'WAITING': return 'yellow';
            case 'ERROR': return 'red';
            case 'COOLING': return 'blue';
            case 'IDLE': return 'dim';
            default: return 'dim';
        }
    }

    _formatDuration(ms) {
        if (!ms || ms < 0) return '--';
        const hours = Math.floor(ms / 3600000);
        const minutes = Math.floor((ms % 3600000) / 60000);
        const seconds = Math.floor((ms % 60000) / 1000);

        if (hours > 0) {
            return `${hours}h ${minutes}m`;
        } else if (minutes > 0) {
            return `${minutes}m ${seconds}s`;
        } else {
            return `${seconds}s`;
        }
    }

    stop() {
        this.running = false;
        if (this._interval) {
            clearInterval(this._interval);
        }
        this.disconnectDB().then(() => {
            console.log('');
            console.log(c('  监控已停止', 'yellow'));
            process.exit(0);
        });
    }
}

// ============================================================================
// 主函数
// ============================================================================

async function main() {
    const dashboard = new MonitorDashboard();
    await dashboard.start();
}

main().catch(console.error);
