/**
 * V173-SENTINEL 资产报告生成器
 * =============================
 *
 * 运行该脚本能输出一个包含所有联赛的"数据净值表"
 * 列出总场次、黄金 JSON 数和成功率
 *
 * @module scripts/ops/asset_report
 * @version V173.0.0
 */

'use strict';

const path = require('path');
const { Client } = require('pg');

// ============================================================================
// 配置
// ============================================================================

const PROJECT_ROOT = process.env.PROJECT_ROOT || '/app';

// 数据库配置 - 支持容器环境
const DB_CONFIG = {
    host: process.env.DB_HOST || 'db',  // 容器内使用服务名 'db'
    port: parseInt(process.env.DB_PORT || '5432'),
    database: process.env.DB_NAME || 'football_db',
    user: process.env.DB_USER || 'football_user',
    password: process.env.DB_PASSWORD || 'your_secure_password_here'
};

// ============================================================================
// 颜色输出
// ============================================================================

const colors = {
    reset: '\x1b[0m',
    bright: '\x1b[1m',
    green: '\x1b[32m',
    yellow: '\x1b[33m',
    red: '\x1b[31m',
    cyan: '\x1b[36m',
    blue: '\x1b[34m',
    magenta: '\x1b[35m'
};

function colorize(text, color) {
    return `${colors[color]}${text}${colors.reset}`;
}

// ============================================================================
// 资产报告生成器
// ============================================================================

class AssetReporter {
    constructor() {
        this.client = null;
    }

    async connect() {
        this.client = new Client({
            host: DB_CONFIG.host,
            port: DB_CONFIG.port,
            database: DB_CONFIG.database,
            user: DB_CONFIG.user,
            password: DB_CONFIG.password,
            connectionTimeoutMillis: 10000
        });
        await this.client.connect();
    }

    async disconnect() {
        if (this.client) {
            await this.client.end();
            this.client = null;
        }
    }

    /**
     * 生成完整资产报告
     */
    async generateReport() {
        console.log('');
        console.log('═'.repeat(80));
        console.log(colorize('  V173 资产净值表 - 数据盘点报告', 'bright'));
        console.log(colorize('  (含网页渗透模式统计)', 'cyan'));
        console.log('═'.repeat(80));
        console.log('');

        // 1. 总体统计
        await this._printOverallStats();

        // 2. 按联赛统计
        await this._printLeagueStats();

        // 3. 数据质量分析
        await this._printQualityAnalysis();

        // 4. 网页渗透模式统计
        await this._printInfiltrationStats();

        // 5. 待收割队列
        await this._printPendingQueue();

        console.log('');
        console.log('═'.repeat(80));
        console.log(colorize(`  报告生成时间: ${new Date().toISOString()}`, 'cyan'));
        console.log('═'.repeat(80));
    }

    /**
     * 总体统计
     */
    async _printOverallStats() {
        const query = `
            SELECT
                COUNT(DISTINCT m.match_id) as total_matches,
                COUNT(CASE WHEN m.is_finished = true THEN 1 END) as finished_matches,
                COUNT(CASE WHEN m.match_date > NOW() THEN 1 END) as upcoming_matches,
                COUNT(DISTINCT m.league_name) as total_leagues
            FROM matches m
        `;

        const result = await this.client.query(query);
        const stats = result.rows[0];

        console.log(colorize('📊 总体统计', 'bright'));
        console.log('─'.repeat(60));
        console.log(`   总比赛数:     ${colorize(stats.total_matches, 'cyan')}`);
        console.log(`   已完成比赛:   ${colorize(stats.finished_matches, 'green')}`);
        console.log(`   未开始比赛:   ${colorize(stats.upcoming_matches, 'yellow')}`);
        console.log(`   覆盖联赛数:   ${colorize(stats.total_leagues, 'magenta')}`);
        console.log('');
    }

    /**
     * 按联赛统计
     */
    async _printLeagueStats() {
        const query = `
            SELECT
                m.league_name,
                COUNT(*) as total_matches,
                COUNT(CASE WHEN m.is_finished = true THEN 1 END) as finished,
                COUNT(CASE WHEN r.match_id IS NOT NULL AND LENGTH(r.l2_raw_json::text) > 5000 THEN 1 END) as gold_data,
                COUNT(CASE WHEN r.match_id IS NOT NULL AND LENGTH(r.l2_raw_json::text) > 0 AND LENGTH(r.l2_raw_json::text) <= 5000 THEN 1 END) as small_data,
                COUNT(CASE WHEN r.match_id IS NULL THEN 1 END) as no_data
            FROM matches m
            LEFT JOIN raw_match_data r ON m.match_id = r.match_id
            GROUP BY m.league_name
            ORDER BY total_matches DESC
        `;

        const result = await this.client.query(query);

        console.log(colorize('🏆 联赛数据净值表', 'bright'));
        console.log('─'.repeat(80));
        console.log(
            '   联赛名称'.padEnd(25) +
            '总场次'.padStart(8) +
            '已完成'.padStart(8) +
            '黄金数据'.padStart(10) +
            '成功率'.padStart(10) +
            '状态'.padStart(10)
        );
        console.log('─'.repeat(80));

        let totalGold = 0;
        let totalFinished = 0;

        for (const row of result.rows) {
            const successRate = row.finished > 0
                ? ((row.gold_data / row.finished) * 100).toFixed(1)
                : '0.0';

            let statusIcon = '✅';
            let statusColor = 'green';
            if (parseFloat(successRate) >= 90) {
                statusIcon = '🟢';
            } else if (parseFloat(successRate) >= 70) {
                statusIcon = '🟡';
                statusColor = 'yellow';
            } else {
                statusIcon = '🔴';
                statusColor = 'red';
            }

            const leagueName = row.league_name.length > 22
                ? row.league_name.substring(0, 22) + '...'
                : row.league_name;

            console.log(
                `   ${leagueName.padEnd(22)}` +
                `${String(row.total_matches).padStart(8)}` +
                `${String(row.finished).padStart(8)}` +
                `${colorize(String(row.gold_data), 'cyan').padStart(10)}` +
                `${colorize(successRate + '%', 'bright').padStart(10)}` +
                `${colorize(statusIcon, statusColor).padStart(10)}`
            );

            totalGold += parseInt(row.gold_data);
            totalFinished += parseInt(row.finished);
        }

        console.log('─'.repeat(80));
        const overallRate = totalFinished > 0
            ? ((totalGold / totalFinished) * 100).toFixed(1)
            : '0.0';
        console.log(
            `   ${'总计'.padEnd(22)}` +
            `${''.padStart(8)}` +
            `${String(totalFinished).padStart(8)}` +
            `${colorize(String(totalGold), 'green').padStart(10)}` +
            `${colorize(overallRate + '%', 'bright').padStart(10)}`
        );
        console.log('');
    }

    /**
     * 数据质量分析
     */
    async _printQualityAnalysis() {
        const query = `
            SELECT
                COUNT(CASE WHEN LENGTH(l2_raw_json::text) > 50000 THEN 1 END) as large_data,
                COUNT(CASE WHEN LENGTH(l2_raw_json::text) BETWEEN 10000 AND 50000 THEN 1 END) as medium_data,
                COUNT(CASE WHEN LENGTH(l2_raw_json::text) BETWEEN 5000 AND 10000 THEN 1 END) as small_valid,
                COUNT(CASE WHEN LENGTH(l2_raw_json::text) > 0 AND LENGTH(l2_raw_json::text) < 5000 THEN 1 END) as invalid_data,
                AVG(LENGTH(l2_raw_json::text))::int as avg_size
            FROM raw_match_data
            WHERE l2_raw_json IS NOT NULL
        `;

        const result = await this.client.query(query);
        const stats = result.rows[0];

        console.log(colorize('📈 数据质量分析', 'bright'));
        console.log('─'.repeat(60));
        console.log(`   大型数据 (>50KB):  ${colorize(stats.large_data, 'green')}`);
        console.log(`   中型数据 (10-50KB): ${colorize(stats.medium_data, 'cyan')}`);
        console.log(`   小型数据 (5-10KB):  ${colorize(stats.small_valid, 'yellow')}`);
        console.log(`   无效数据 (<5KB):    ${colorize(stats.invalid_data, 'red')}`);
        console.log(`   平均大小:           ${colorize((stats.avg_size / 1024).toFixed(1) + ' KB', 'magenta')}`);
        console.log('');
    }

    /**
     * V173: 网页渗透模式统计
     */
    async _printInfiltrationStats() {
        // 检查是否有 _meta.source 字段（网页渗透模式标记）
        const query = `
            SELECT
                COUNT(CASE WHEN l2_raw_json::text LIKE '%web_infiltration%' THEN 1 END) as infiltration_count,
                COUNT(CASE WHEN l2_raw_json::text LIKE '%"hasStats":true%' THEN 1 END) as has_stats,
                COUNT(CASE WHEN l2_raw_json::text LIKE '%"hasLineup":true%' THEN 1 END) as has_lineup,
                COUNT(CASE WHEN l2_raw_json::text LIKE '%"hasShotmap":true%' THEN 1 END) as has_shotmap,
                AVG(CASE WHEN l2_raw_json::text LIKE '%web_infiltration%' THEN LENGTH(l2_raw_json::text) END)::int as avg_infiltration_size
            FROM raw_match_data
            WHERE l2_raw_json IS NOT NULL
        `;

        const result = await this.client.query(query);
        const stats = result.rows[0];

        const infiltrationCount = parseInt(stats.infiltration_count) || 0;
        const avgSize = stats.avg_infiltration_size ? (stats.avg_infiltration_size / 1024).toFixed(1) : '0.0';

        console.log(colorize('🎭 网页渗透模式统计 (V173)', 'bright'));
        console.log('─'.repeat(60));

        if (infiltrationCount > 0) {
            console.log(`   渗透采集成功:   ${colorize(infiltrationCount, 'green')} 场`);
            console.log(`   平均数据大小:   ${colorize(avgSize + ' KB', 'cyan')}`);
            console.log(`   含 Stats 数据:  ${colorize(stats.has_stats || 0, 'yellow')}`);
            console.log(`   含 Lineup 数据: ${colorize(stats.has_lineup || 0, 'magenta')}`);
            console.log(`   含 Shotmap 数据: ${colorize(stats.has_shotmap || 0, 'blue')}`);
        } else {
            console.log(colorize('   暂无网页渗透模式采集的数据', 'yellow'));
        }
        console.log('');
    }

    /**
     * 待收割队列
     */
    async _printPendingQueue() {
        const query = `
            SELECT
                m.league_name,
                COUNT(*) as pending_count
            FROM matches m
            LEFT JOIN raw_match_data r ON m.match_id = r.match_id
            WHERE m.is_finished = true
              AND (r.l2_raw_json IS NULL OR LENGTH(r.l2_raw_json::text) < 5000)
            GROUP BY m.league_name
            ORDER BY pending_count DESC
            LIMIT 10
        `;

        const result = await this.client.query(query);

        console.log(colorize('⏳ 待收割队列 (Top 10)', 'bright'));
        console.log('─'.repeat(40));

        if (result.rows.length === 0) {
            console.log(colorize('   ✅ 所有比赛已完成收割！', 'green'));
        } else {
            for (const row of result.rows) {
                const leagueName = row.league_name.length > 25
                    ? row.league_name.substring(0, 25) + '...'
                    : row.league_name;
                console.log(`   ${leagueName.padEnd(28)} ${colorize(row.pending_count, 'yellow')}`);
            }
        }
        console.log('');
    }
}

// ============================================================================
// 主函数
// ============================================================================

async function main() {
    const reporter = new AssetReporter();

    try {
        await reporter.connect();
        await reporter.generateReport();
    } catch (error) {
        console.error(colorize(`❌ 报告生成失败: ${error.message}`, 'red'));
        process.exit(1);
    } finally {
        await reporter.disconnect();
    }
}

// 导出
module.exports = { AssetReporter };

// 直接运行时执行
if (require.main === module) {
    main().catch(console.error);
}
