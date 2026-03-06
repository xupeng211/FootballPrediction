#!/usr/bin/env node
/**
 * V198.1 Elo 战力重算脚本
 * ========================
 *
 * 基于历史比赛结果计算各队真实 Elo 评分
 *
 * 用法:
 *   node scripts/maintenance/recalculate_elo.js                    # 全量重算
 *   node scripts/maintenance/recalculate_elo.js --league-id 87     # 只算西甲
 *   node scripts/maintenance/recalculate_elo.js --dry-run          # 预览模式
 *
 * @module scripts/maintenance/recalculate_elo
 * @version V198.1.0
 */

'use strict';

const { Pool } = require('pg');
const { EloRatingExtractor } = require('../../src/feature_engine/extractors/EloRatingExtractor');

// ============================================================================
// 配置
// ============================================================================

const CONFIG = {
    db: {
        host: process.env.DB_HOST || 'host.docker.internal',
        port: parseInt(process.env.DB_PORT || '5432'),
        database: process.env.DB_NAME || 'football_db',
        user: process.env.DB_USER || 'football_user',
        password: process.env.DB_PASSWORD || ''
    },
    // Elo 参数（针对足球优化）
    elo: {
        initialRating: 1500,
        kFactor: 20,              // 足球标准 K 值
        homeFieldAdvantage: 50    // 主场优势 50 分
    }
};

// ============================================================================
// 主逻辑
// ============================================================================

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
    console.log('  V198.1 Elo 战力重算系统');
    console.log('═'.repeat(70));
    console.log(`  联赛过滤: ${targetLeagueNames ? targetLeagueNames.join('/') : '全部'}`);
    console.log(`  预览模式: ${dryRun}`);
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
                m.league_name
            FROM matches m
            WHERE m.home_score IS NOT NULL
              AND m.away_score IS NOT NULL
              AND m.home_score::text ~ '^[0-9]+$'
              AND m.away_score::text ~ '^[0-9]+$'
        `;

        const params = [];
        if (targetLeagueNames) {
            // 构建多条件 OR 查询
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

        // 2. 初始化 Elo 提取器
        const eloExtractor = new EloRatingExtractor(CONFIG.elo);

        // 3. 按时间顺序计算 Elo
        console.log('🔄 开始计算 Elo 评分...\n');

        const eloResults = new Map();
        let processed = 0;

        for (const match of matches) {
            // 转换数据格式
            const matchData = {
                matchId: match.match_id,
                homeTeamId: match.home_team,
                awayTeamId: match.away_team,
                homeScore: parseInt(match.home_score, 10),
                awayScore: parseInt(match.away_score, 10),
                matchDate: match.match_date
            };

            // 计算 Elo
            const eloFeatures = eloExtractor.updateMatchElo(matchData);
            eloResults.set(match.match_id, {
                ...eloFeatures,
                league_name: match.league_name
            });

            processed++;
            if (processed % 100 === 0) {
                console.log(`  进度: ${processed}/${matches.length}`);
            }
        }

        // 4. 显示球队最终 Elo 评分
        const stats = eloExtractor.getStats();
        console.log('\n' + '─'.repeat(70));
        console.log('  📊 Elo 评分统计');
        console.log('─'.repeat(70));
        console.log(`  球队数量: ${stats.teamCount}`);
        console.log(`  平均评分: ${stats.avgRating.toFixed(1)}`);
        console.log(`  最高评分: ${stats.maxRating.toFixed(1)}`);
        console.log(`  最低评分: ${stats.minRating.toFixed(1)}`);

        // 显示西甲 TOP 10
        const allRatings = eloExtractor.exportAllRatings();
        const sortedTeams = Object.entries(allRatings)
            .sort((a, b) => b[1] - a[1])
            .slice(0, 15);

        console.log('\n  🏆 TOP 15 球队 Elo 评分:');
        console.log('─'.repeat(70));
        sortedTeams.forEach(([team, rating], index) => {
            const medal = index === 0 ? '🥇' : index === 1 ? '🥈' : index === 2 ? '🥉' : '  ';
            console.log(`  ${medal} ${index + 1}. ${team.padEnd(25)} ${rating.toFixed(1)}`);
        });

        // 5. 更新数据库（非预览模式）
        if (!dryRun) {
            console.log('\n' + '─'.repeat(70));
            console.log('  💾 更新 L3 特征表...');
            console.log('─'.repeat(70));

            let updated = 0;
            let skipped = 0;

            for (const [matchId, eloFeatures] of eloResults) {
                try {
                    // 检查 L3 记录是否存在
                    const checkResult = await client.query(
                        'SELECT match_id FROM l3_features WHERE match_id = $1',
                        [matchId]
                    );

                    if (checkResult.rows.length > 0) {
                        // 更新 elo_features
                        await client.query(`
                            UPDATE l3_features
                            SET elo_features = $1, updated_at = NOW()
                            WHERE match_id = $2
                        `, [JSON.stringify(eloFeatures), matchId]);
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

        // 6. 保存球队最终 Elo 到数据库（可选）
        if (!dryRun) {
            console.log('\n' + '─'.repeat(70));
            console.log('  💾 保存球队 Elo 评分...');
            console.log('─'.repeat(70));

            // 创建或更新 team_elo_ratings 表
            await client.query(`
                CREATE TABLE IF NOT EXISTS team_elo_ratings (
                    team_name VARCHAR(255) PRIMARY KEY,
                    elo_rating DECIMAL(10, 2) NOT NULL,
                    matches_played INTEGER DEFAULT 0,
                    last_updated TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                )
            `);

            let teamsSaved = 0;
            for (const [teamName, rating] of Object.entries(allRatings)) {
                const matchCount = eloExtractor.ratingHistory.get(teamName)?.length || 0;

                await client.query(`
                    INSERT INTO team_elo_ratings (team_name, elo_rating, matches_played, last_updated)
                    VALUES ($1, $2, $3, NOW())
                    ON CONFLICT (team_name)
                    DO UPDATE SET
                        elo_rating = EXCLUDED.elo_rating,
                        matches_played = EXCLUDED.matches_played,
                        last_updated = NOW()
                `, [teamName, rating, matchCount]);

                teamsSaved++;
            }

            console.log(`  ✅ 保存 ${teamsSaved} 支球队的 Elo 评分`);
        }

        console.log('\n' + '═'.repeat(70));
        console.log('  🎉 Elo 重算完成！');
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
