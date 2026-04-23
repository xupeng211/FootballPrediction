#!/usr/bin/env node
/* eslint-disable complexity, max-lines */
/**
 * V198.1 滚动特征重算脚本
 * ========================
 *
 * 基于历史比赛计算各队的滚动平均特征（Last N Games）
 *
 * 计算特征:
 * - home_xg_rolling (近 5 场平均 xG)
 * - away_xg_rolling
 * - home_goals_rolling (近 5 场平均进球)
 * - away_goals_rolling
 * - home_conceded_rolling (近 5 场平均失球)
 * - away_conceded_rolling
 *
 * 用法:
 *   node scripts/maintenance/recalculate_rolling.js                    # 全量重算
 *   node scripts/maintenance/recalculate_rolling.js --league-id 87     # 只算西甲
 *   node scripts/maintenance/recalculate_rolling.js --dry-run          # 预览模式
 * @module scripts/maintenance/recalculate_rolling
 * @version V198.1.0
 */

'use strict';

const { Pool } = require('pg');

// ============================================================================
// 配置
// ============================================================================

const CONFIG = {
    db: {
        host: process.env.DB_HOST || '127.0.0.1',
        port: parseInt(process.env.DB_PORT || '5432'),
        database: process.env.DB_NAME || 'football_db',
        user: process.env.DB_USER || 'football_user',
        password: process.env.DB_PASSWORD || ''
    },
    rolling: {
        windowSize: 5,  // 近 5 场
        minMatches: 1   // 最少 1 场才计算
    }
};

// ============================================================================
// 滚动计算器
// ============================================================================

/**
 *
 */
class RollingFeatureCalculator {
    /**
     *
     * @param config
     */
    constructor(config = {}) {
        this.config = { ...CONFIG.rolling, ...config };
        // 球队历史数据: teamName -> [{ matchDate, xg, goals, conceded, isHome }, ...]
        this.teamHistory = new Map();
    }

    /**
     * 添加比赛数据
     * @param match
     */
    addMatch(match) {
        const { home_team, away_team, home_score, away_score, match_date, home_xg, away_xg } = match;

        // 主队记录
        if (!this.teamHistory.has(home_team)) {
            this.teamHistory.set(home_team, []);
        }
        this.teamHistory.get(home_team).push({
            matchDate: new Date(match_date),
            xg: parseFloat(home_xg) || 0,
            goals: parseInt(home_score, 10) || 0,
            conceded: parseInt(away_score, 10) || 0,
            isHome: true
        });

        // 客队记录
        if (!this.teamHistory.has(away_team)) {
            this.teamHistory.set(away_team, []);
        }
        this.teamHistory.get(away_team).push({
            matchDate: new Date(match_date),
            xg: parseFloat(away_xg) || 0,
            goals: parseInt(away_score, 10) || 0,
            conceded: parseInt(home_score, 10) || 0,
            isHome: false
        });
    }

    /**
     * 按日期排序历史数据
     */
    sortHistory() {
        for (const [team, history] of this.teamHistory) {
            history.sort((a, b) => a.matchDate - b.matchDate);
        }
    }

    /**
     * 计算某队在指定日期前的滚动特征
     * @param teamName
     * @param beforeDate
     * @param isHome
     */
    getRollingFeatures(teamName, beforeDate, isHome) {
        const history = this.teamHistory.get(teamName) || [];
        const targetDate = new Date(beforeDate);

        // 过滤目标日期之前的比赛
        const priorMatches = history.filter(h => h.matchDate < targetDate);

        // 取最近 N 场
        const recentMatches = priorMatches.slice(-this.config.windowSize);

        if (recentMatches.length < this.config.minMatches) {
            return {
                xg_rolling: 0,
                goals_rolling: 0,
                conceded_rolling: 0,
                matches_count: recentMatches.length
            };
        }

        // 计算平均值
        const avgXg = recentMatches.reduce((sum, m) => sum + m.xg, 0) / recentMatches.length;
        const avgGoals = recentMatches.reduce((sum, m) => sum + m.goals, 0) / recentMatches.length;
        const avgConceded = recentMatches.reduce((sum, m) => sum + m.conceded, 0) / recentMatches.length;

        // 计算状态分 (综合评分: xG + 进球 - 失球)
        const formScore = (avgXg * 0.4 + avgGoals * 0.4 - avgConceded * 0.2) * 10;

        return {
            xg_rolling: Math.round(avgXg * 100) / 100,
            goals_rolling: Math.round(avgGoals * 100) / 100,
            conceded_rolling: Math.round(avgConceded * 100) / 100,
            form_score: Math.round(formScore * 100) / 100,
            matches_count: recentMatches.length
        };
    }

    /**
     * 获取统计信息
     */
    getStats() {
        const teamCounts = Array.from(this.teamHistory.values()).map(h => h.length);
        return {
            teamCount: this.teamHistory.size,
            totalMatches: teamCounts.reduce((a, b) => a + b, 0) / 2, // 每场比赛记录两次
            avgMatchesPerTeam: teamCounts.length > 0
                ? teamCounts.reduce((a, b) => a + b, 0) / teamCounts.length
                : 0
        };
    }
}

// ============================================================================
// 主逻辑
// ============================================================================

/**
 *
 */
async function main() {
    const args = process.argv.slice(2);
    const dryRun = args.includes('--dry-run');
    const leagueId = args.find(a => a.startsWith('--league-id'))?.split('=')[1] ||
                     args[args.indexOf('--league-id') + 1];

    // 联赛 ID 到名称映射
    const leagueNames = {
        '87': ['La Liga', '西班牙甲组联赛', '西甲'],
        '47': ['Premier League', '英格兰超级联赛', '英超'],
        '135': ['Serie A', '意大利甲组联赛', '意甲'],
        '54': ['Bundesliga', '德国甲组联赛', '德甲'],
        '61': ['Ligue 1', '法国甲组联赛', '法甲']
    };

    const targetLeagueNames = leagueId ? leagueNames[leagueId] || [leagueId] : null;

    console.log('\n' + '═'.repeat(70));
    console.log('  V198.1 滚动特征重算系统');
    console.log('═'.repeat(70));
    console.log(`  联赛过滤: ${targetLeagueNames ? targetLeagueNames.join('/') : '全部'}`);
    console.log(`  预览模式: ${dryRun}`);
    console.log(`  窗口大小: ${CONFIG.rolling.windowSize} 场`);
    console.log('═'.repeat(70) + '\n');

    // 连接数据库
    const pool = new Pool({ ...CONFIG.db, max: 10 });
    const client = await pool.connect();

    try {
        // 1. 获取所有有比分的已完成比赛
        let query = `
            SELECT
                m.match_id,
                m.home_team,
                m.away_team,
                m.home_score,
                m.away_score,
                m.match_date,
                m.league_name,
                COALESCE(l3.tactical_features->>'home_xg', '0')::numeric as home_xg,
                COALESCE(l3.tactical_features->>'away_xg', '0')::numeric as away_xg
            FROM matches m
            LEFT JOIN l3_features l3 ON m.match_id = l3.match_id
            WHERE m.home_score IS NOT NULL
              AND m.away_score IS NOT NULL
              AND m.home_score::text ~ '^[0-9]+$'
              AND m.away_score::text ~ '^[0-9]+$'
        `;

        const params = [];
        if (targetLeagueNames) {
            const conditions = targetLeagueNames.map((_, i) => `m.league_name LIKE $${i + 1}`);
            query += ` AND (${conditions.join(' OR ')})`;
            targetLeagueNames.forEach(name => params.push(`%${name}%`));
        }

        query += ` ORDER BY m.match_date ASC`;

        const result = await client.query(query, params);
        const matches = result.rows;

        console.log(`📋 获取到 ${matches.length} 场有比分的比赛\n`);

        if (matches.length === 0) {
            console.log('⚠️  没有可处理的比赛');
            return;
        }

        // 2. 初始化滚动计算器
        const calculator = new RollingFeatureCalculator(CONFIG.rolling);

        // 3. 添加所有比赛数据
        console.log('🔄 构建球队历史数据...');
        for (const match of matches) {
            calculator.addMatch(match);
        }
        calculator.sortHistory();

        const stats = calculator.getStats();
        console.log(`  球队数量: ${stats.teamCount}`);
        console.log(`  总比赛数: ${stats.totalMatches.toFixed(0)}`);
        console.log(`  平均每队: ${stats.avgMatchesPerTeam.toFixed(1)} 场\n`);

        // 4. 计算每场比赛的滚动特征
        console.log('🔄 计算滚动特征...');

        const rollingResults = new Map();

        for (const match of matches) {
            const homeRolling = calculator.getRollingFeatures(
                match.home_team,
                match.match_date,
                true
            );
            const awayRolling = calculator.getRollingFeatures(
                match.away_team,
                match.match_date,
                false
            );

            rollingResults.set(match.match_id, {
                home_xg_rolling: homeRolling.xg_rolling,
                away_xg_rolling: awayRolling.xg_rolling,
                home_goals_rolling: homeRolling.goals_rolling,
                away_goals_rolling: awayRolling.goals_rolling,
                home_conceded_rolling: homeRolling.conceded_rolling,
                away_conceded_rolling: awayRolling.conceded_rolling,
                home_form_score: homeRolling.form_score || 0,
                away_form_score: awayRolling.form_score || 0,
                home_matches_count: homeRolling.matches_count,
                away_matches_count: awayRolling.matches_count
            });
        }

        console.log(`  ✅ 计算完成: ${rollingResults.size} 场\n`);

        // 5. 显示样本
        console.log('─'.repeat(70));
        console.log('  📊 滚动特征样本（最近 10 场）');
        console.log('─'.repeat(70));

        const sampleMatches = matches.slice(-10);
        for (const match of sampleMatches) {
            const rolling = rollingResults.get(match.match_id);
            console.log(`\n  ${match.home_team} vs ${match.away_team}`);
            console.log(`    比分: ${match.home_score} - ${match.away_score}`);
            console.log(`    主队 xG_rolling: ${rolling.home_xg_rolling.toFixed(2)} (近 ${rolling.home_matches_count} 场)`);
            console.log(`    客队 xG_rolling: ${rolling.away_xg_rolling.toFixed(2)} (近 ${rolling.away_matches_count} 场)`);
            console.log(`    主队状态分: ${rolling.home_form_score.toFixed(2)}`);
            console.log(`    客队状态分: ${rolling.away_form_score.toFixed(2)}`);
        }

        // 6. 更新数据库
        if (!dryRun) {
            console.log('\n' + '─'.repeat(70));
            console.log('  💾 更新 L3 特征表...');
            console.log('─'.repeat(70));

            let updated = 0;
            let skipped = 0;

            for (const [matchId, rolling] of rollingResults) {
                try {
                    // 获取现有的 tactical_features
                    const existingResult = await client.query(
                        'SELECT tactical_features FROM l3_features WHERE match_id = $1',
                        [matchId]
                    );

                    if (existingResult.rows.length > 0) {
                        const existingTactical = existingResult.rows[0].tactical_features || {};

                        // 合并滚动特征
                        const updatedTactical = {
                            ...existingTactical,
                            home_xg_rolling: rolling.home_xg_rolling,
                            away_xg_rolling: rolling.away_xg_rolling,
                            home_goals_rolling: rolling.home_goals_rolling,
                            away_goals_rolling: rolling.away_goals_rolling,
                            home_conceded_rolling: rolling.home_conceded_rolling,
                            away_conceded_rolling: rolling.away_conceded_rolling,
                            home_form_score: rolling.home_form_score,
                            away_form_score: rolling.away_form_score,
                            home_matches_count: rolling.home_matches_count,
                            away_matches_count: rolling.away_matches_count,
                            _rollingVersion: 'V198.1.0',
                            _rollingCalculatedAt: new Date().toISOString()
                        };

                        await client.query(`
                            UPDATE l3_features
                            SET tactical_features = $1, updated_at = NOW()
                            WHERE match_id = $2
                        `, [JSON.stringify(updatedTactical), matchId]);

                        updated++;
                    } else {
                        skipped++;
                    }
                } catch (err) {
                    console.error(`  ❌ 更新失败 [${matchId}]: ${err.message}`);
                }
            }

            console.log(`\n  ✅ 更新: ${updated} 场`);
            console.log(`  ⏭️  跳过: ${skipped} 场（无 L3 记录）`);
        } else {
            console.log('\n  📋 预览模式 - 未更新数据库');
        }

        console.log('\n' + '═'.repeat(70));
        console.log('  🎉 滚动特征重算完成！');
        console.log('═'.repeat(70) + '\n');

    } finally {
        client.release();
        await pool.end();
    }
}

main().catch(err => {
    console.error('❌ 致命错误:', err.message);
    process.exit(1);
});
