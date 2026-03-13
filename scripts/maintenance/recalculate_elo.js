#!/usr/bin/env node
/**
 * V199.0 Elo 战力重算脚本 - 自适应全联赛版
 * ============================================
 *
 * 【重构】废除硬编码联赛映射，实现动态发现
 * - 自动从数据库发现所有联赛
 * - 支持任意新联赛自动接入（中超、J联赛等）
 * - 按联赛分别统计和展示
 *
 * 用法:
 *   node scripts/maintenance/recalculate_elo.js                    # 全量重算（所有联赛）
 *   node scripts/maintenance/recalculate_elo.js --dry-run          # 预览模式
 *   node scripts/maintenance/recalculate_elo.js --incremental      # 增量更新（只处理无 Elo 的比赛）
 * @module scripts/maintenance/recalculate_elo
 * @version V199.0.0 - 自适应全联赛版
 * @updated 2026-03-11
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
// 动态联赛发现
// ============================================================================

/**
 * 从数据库动态发现所有联赛
 * @param {object} client - PostgreSQL 客户端
 * @returns {Promise<Array>} 联赛列表 [{ league_id, league_name, match_count }]
 */
async function discoverLeagues(client) {
    const query = `
        SELECT
            split_part(match_id, '_', 1) as league_id,
            league_name,
            COUNT(*) as match_count
        FROM matches
        GROUP BY split_part(match_id, '_', 1), league_name
        ORDER BY match_count DESC
    `;

    const result = await client.query(query);
    return result.rows.map(row => ({
        leagueId: row.league_id,
        leagueName: row.league_name,
        matchCount: parseInt(row.match_count, 10)
    }));
}

/**
 * 获取联赛的已完赛比赛统计
 * @param {object} client - PostgreSQL 客户端
 * @param {string} leagueId - 联赛 ID
 * @returns {Promise<object>} 统计数据
 */
async function getLeagueStats(client, leagueId) {
    const query = `
        SELECT
            COUNT(*) as total_matches,
            COUNT(CASE WHEN m.status = 'finished' THEN 1 END) as finished_matches,
            COUNT(CASE WHEN m.status = 'finished'
                       AND l.elo_features IS NOT NULL
                       AND l.elo_features != '{}'::jsonb THEN 1 END) as has_elo
        FROM matches m
        LEFT JOIN l3_features l ON m.match_id = l.match_id
        WHERE split_part(m.match_id, '_', 1) = $1
    `;

    const result = await client.query(query, [leagueId]);
    return {
        total: parseInt(result.rows[0].total_matches, 10),
        finished: parseInt(result.rows[0].finished_matches, 10),
        hasElo: parseInt(result.rows[0].has_elo, 10)
    };
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
    const incremental = args.includes('--incremental');

    console.log('\n' + '═'.repeat(70));
    console.log('  V199.0 Elo 战力重算系统 - 自适应全联赛版');
    console.log('═'.repeat(70));
    console.log(`  模式: ${dryRun ? '预览' : (incremental ? '增量更新' : '全量重算')}`);
    console.log(`  联赛: 动态发现（自动识别所有联赛）`);
    console.log('═'.repeat(70) + '\n');

    // 连接数据库
    const pool = new Pool({ ...CONFIG.db, max: 10 });
    const client = await pool.connect();

    try {
        // ============================================
        // Step 1: 动态发现所有联赛
        // ============================================
        console.log('🔍 Step 1: 动态发现联赛...');
        const leagues = await discoverLeagues(client);

        console.log('\n  发现联赛列表:');
        console.log('  ─'.repeat(50));

        const leagueStatsList = [];
        for (const league of leagues) {
            const stats = await getLeagueStats(client, league.leagueId);
            leagueStatsList.push({ ...league, ...stats });

            const fillRate = stats.finished > 0
                ? ((stats.hasElo / stats.finished) * 100).toFixed(1)
                : '0.0';
            const status = stats.hasElo === stats.finished ? '✅' :
                          stats.hasElo === 0 ? '❌' : '⚠️';

            console.log(`  ${status} [${league.leagueId.padEnd(3)}] ${league.leagueName.padEnd(20)} ` +
                       `| ${stats.finished}场已完赛 | Elo填充: ${fillRate}%`);
        }

        const totalFinished = leagueStatsList.reduce((sum, l) => sum + l.finished, 0);
        const totalHasElo = leagueStatsList.reduce((sum, l) => sum + l.hasElo, 0);
        const missingElo = totalFinished - totalHasElo;

        console.log('  ─'.repeat(50));
        console.log(`  📊 总计: ${totalFinished} 场已完赛, ${totalHasElo} 场有 Elo, ` +
                   `${missingElo} 场缺失\n`);

        if (missingElo === 0 && incremental) {
            console.log('✅ 所有已完赛比赛都已有 Elo 数据，无需更新！');
            return;
        }

        // ============================================
        // Step 2: 获取比赛数据
        // ============================================
        console.log('📋 Step 2: 获取比赛数据...');

        let query = `
            SELECT
                m.match_id,
                m.home_team,
                m.away_team,
                m.home_score,
                m.away_score,
                m.match_date,
                m.league_name,
                split_part(m.match_id, '_', 1) as league_id
            FROM matches m
            LEFT JOIN l3_features l ON m.match_id = l.match_id
            WHERE m.status = 'finished'
              AND m.home_score IS NOT NULL
              AND m.away_score IS NOT NULL
              AND m.home_score::text ~ '^[0-9]+$'
              AND m.away_score::text ~ '^[0-9]+$'
        `;

        // 增量模式：只处理缺失 Elo 的比赛
        if (incremental) {
            query += `
              AND (l.elo_features IS NULL OR l.elo_features = '{}'::jsonb)
            `;
        }

        query += ` ORDER BY m.match_date ASC`;

        const result = await client.query(query);
        const matches = result.rows;

        // 按联赛分组统计
        const matchesByLeague = {};
        for (const match of matches) {
            const lid = match.league_id;
            if (!matchesByLeague[lid]) {
                matchesByLeague[lid] = [];
            }
            matchesByLeague[lid].push(match);
        }

        console.log(`\n  获取到 ${matches.length} 场比赛需要处理:`);
        for (const [lid, leagueMatches] of Object.entries(matchesByLeague)) {
            const league = leagues.find(l => l.leagueId === lid);
            console.log(`    - [${lid}] ${league?.leagueName || 'Unknown'}: ${leagueMatches.length} 场`);
        }
        console.log('');

        if (matches.length === 0) {
            console.log('⚠️  没有可处理的比赛');
            return;
        }

        // ============================================
        // Step 3: 初始化 Elo 提取器并计算
        // ============================================
        console.log('🔄 Step 3: 计算 Elo 评分...\n');

        // 【关键】如果非增量模式，需要加载已有的 Elo 历史
        // 这样可以保留已计算球队的评分
        const eloExtractor = new EloRatingExtractor(CONFIG.elo);

        // 如果是全量模式，从数据库加载已有评分（可选，保持连续性）
        if (!incremental) {
            console.log('  📥 加载已有 Elo 评分以保持连续性...');
            const existingRatings = await client.query(`
                SELECT team_name, elo_rating, matches_played
                FROM team_elo_ratings
            `);

            for (const row of existingRatings.rows) {
                eloExtractor.setTeamRating(row.team_name, parseFloat(row.elo_rating));
                // 恢复历史记录数量（简化处理）
                for (let i = 0; i < (row.matches_played || 0); i++) {
                    if (!eloExtractor.ratingHistory.has(row.team_name)) {
                        eloExtractor.ratingHistory.set(row.team_name, []);
                    }
                    eloExtractor.ratingHistory.get(row.team_name).push({
                        rating: parseFloat(row.elo_rating),
                        timestamp: Date.now()
                    });
                }
            }
            console.log(`  ✅ 加载了 ${existingRatings.rows.length} 支球队的已有评分\n`);
        }

        const eloResults = new Map();
        let processed = 0;
        const startTime = Date.now();

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
                league_id: match.league_id,
                league_name: match.league_name
            });

            processed++;
            if (processed % 200 === 0) {
                const elapsed = ((Date.now() - startTime) / 1000).toFixed(1);
                const rate = (processed / (Date.now() - startTime) * 1000).toFixed(1);
                console.log(`  进度: ${processed}/${matches.length} (${rate} 场/秒, 已用时 ${elapsed}s)`);
            }
        }

        const totalTime = ((Date.now() - startTime) / 1000).toFixed(1);
        console.log(`\n  ✅ 计算完成: ${processed} 场比赛, 耗时 ${totalTime}s\n`);

        // ============================================
        // Step 4: 显示统计信息
        // ============================================
        const stats = eloExtractor.getStats();
        console.log('─'.repeat(70));
        console.log('  📊 Elo 评分统计');
        console.log('─'.repeat(70));
        console.log(`  球队总数: ${stats.teamCount}`);
        console.log(`  平均评分: ${stats.avgRating.toFixed(1)}`);
        console.log(`  最高评分: ${stats.maxRating.toFixed(1)}`);
        console.log(`  最低评分: ${stats.minRating.toFixed(1)}`);

        // 显示 TOP 15 球队
        const allRatings = eloExtractor.exportAllRatings();
        const sortedTeams = Object.entries(allRatings)
            .sort((a, b) => b[1] - a[1])
            .slice(0, 15);

        console.log('\n  🏆 TOP 15 球队 Elo 评分:');
        console.log('─'.repeat(70));
        sortedTeams.forEach(([team, rating], index) => {
            const medal = index === 0 ? '🥇' : index === 1 ? '🥈' : index === 2 ? '🥉' : '  ';
            console.log(`  ${medal} ${(index + 1).toString().padStart(2)}. ${team.padEnd(25)} ${rating.toFixed(1)}`);
        });

        // 按联赛显示球队数量
        console.log('\n  📈 按联赛统计:');
        console.log('─'.repeat(70));

        const leagueTeamCounts = {};
        for (const [matchId, features] of eloResults) {
            const lid = features.league_id;
            leagueTeamCounts[lid] = (leagueTeamCounts[lid] || 0) + 1;
        }

        for (const [lid, count] of Object.entries(leagueTeamCounts).sort((a, b) => b[1] - a[1])) {
            const league = leagues.find(l => l.leagueId === lid);
            console.log(`  [${lid}] ${league?.leagueName?.padEnd(20) || 'Unknown'.padEnd(20)} | ${count} 场更新`);
        }

        // ============================================
        // Step 5: 更新数据库
        // ============================================
        if (!dryRun) {
            console.log('\n' + '─'.repeat(70));
            console.log('  💾 Step 5: 更新数据库...');
            console.log('─'.repeat(70));

            // 5.1 更新 L3 特征表
            console.log('\n  📝 更新 L3 特征表...');
            let updated = 0;
            let skipped = 0;
            const batchSize = 100;
            const matchIds = Array.from(eloResults.keys());

            for (let i = 0; i < matchIds.length; i += batchSize) {
                const batch = matchIds.slice(i, i + batchSize);

                for (const matchId of batch) {
                    try {
                        const eloFeatures = eloResults.get(matchId);
                        const updateResult = await client.query(`
                            UPDATE l3_features
                            SET elo_features = $1, updated_at = NOW()
                            WHERE match_id = $2
                        `, [JSON.stringify(eloFeatures), matchId]);

                        if (updateResult.rowCount > 0) {
                            updated++;
                        } else {
                            skipped++;
                        }
                    } catch (err) {
                        console.error(`  ❌ 更新失败 [${matchId}]: ${err.message}`);
                    }
                }

                if ((i + batchSize) % 500 === 0 || i + batchSize >= matchIds.length) {
                    console.log(`    进度: ${Math.min(i + batchSize, matchIds.length)}/${matchIds.length}`);
                }
            }

            console.log(`\n  ✅ L3 更新: ${updated} 场`);
            console.log(`  ⏭️  跳过: ${skipped} 场（无 L3 记录）`);

            // 5.2 保存球队 Elo 评分
            console.log('\n  💾 保存球队 Elo 评分...');

            await client.query(`
                CREATE TABLE IF NOT EXISTS team_elo_ratings (
                    team_name VARCHAR(255) PRIMARY KEY,
                    elo_rating DECIMAL(10, 2) NOT NULL,
                    matches_played INTEGER DEFAULT 0,
                    last_updated TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                )
            `);

            let teamsSaved = 0;
            const teamEntries = Object.entries(allRatings);

            for (const [teamName, rating] of teamEntries) {
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

        } else {
            console.log('\n  📋 预览模式 - 未更新数据库');
        }

        // ============================================
        // Step 6: 验证更新结果
        // ============================================
        if (!dryRun) {
            console.log('\n' + '─'.repeat(70));
            console.log('  🔍 Step 6: 验证更新结果...');
            console.log('─'.repeat(70));

            const updatedLeagues = await discoverLeagues(client);
            let allFilled = true;

            for (const league of updatedLeagues) {
                const stats = await getLeagueStats(client, league.leagueId);
                const fillRate = stats.finished > 0
                    ? ((stats.hasElo / stats.finished) * 100).toFixed(1)
                    : '100.0';
                const status = stats.hasElo === stats.finished ? '✅' :
                              stats.hasElo === 0 ? '❌' : '⚠️';

                console.log(`  ${status} [${league.leagueId.padEnd(3)}] ${league.leagueName.padEnd(20)} ` +
                           `| Elo填充: ${fillRate}% (${stats.hasElo}/${stats.finished})`);

                if (stats.hasElo < stats.finished) {
                    allFilled = false;
                }
            }

            // 统计球队数量
            const teamCountResult = await client.query(`SELECT COUNT(*) as count FROM team_elo_ratings`);
            const teamCount = parseInt(teamCountResult.rows[0].count, 10);
            console.log(`\n  📊 球队总数: ${teamCount} 支`);

            if (allFilled) {
                console.log('\n  🎉 所有联赛 Elo 数据已完整填充！');
            }
        }

        console.log('\n' + '═'.repeat(70));
        console.log('  ✅ V199.0 Elo 重算完成！');
        console.log('═'.repeat(70) + '\n');

    } finally {
        client.release();
        await pool.end();
    }
}

// ============================================================================
// CLI 入口
// ============================================================================

main().catch(err => {
    console.error('❌ 致命错误:', err.message);
    console.error(err.stack);
    process.exit(1);
});
