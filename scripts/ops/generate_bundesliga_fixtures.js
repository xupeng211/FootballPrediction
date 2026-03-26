/**
 * Bundesliga Fixture Generator - 程序化生成完整赛程
 * ================================================
 * 基于德甲 18 队双循环赛制生成 306 场标准赛程
 * 18 teams × 34 rounds = 306 matches
 *
 * @version V11.0-GENERATOR
 * @date 2026-03-26
 */

'use strict';

const { Pool } = require('pg');

// 德甲 2025/26 赛季 18 支标准球队
const TEAMS = [
  'Bayern München',
  'Borussia Dortmund',
  'Bayer Leverkusen',
  'RB Leipzig',
  'Eintracht Frankfurt',
  'Wolfsburg',
  'Freiburg',
  'VfB Stuttgart',
  'Mainz 05',
  'Werder Bremen',
  'Hoffenheim',
  'Augsburg',
  'Borussia Mönchengladbach',
  'Union Berlin',
  'Heidenheim',
  'St. Pauli',
  'Holstein Kiel',
  'Bochum'
];

// 2025/26 赛季德甲赛程日期 (第一轮 2025-08-22 至 第34轮 2026-05-16)
const ROUND_DATES = [
  '2025-08-22', '2025-08-29', '2025-09-12', '2025-09-19', '2025-09-26',
  '2025-10-03', '2025-10-17', '2025-10-24', '2025-10-31', '2025-11-07',
  '2025-11-21', '2025-11-28', '2025-12-05', '2025-12-12', '2025-12-19',
  '2026-01-09', '2026-01-16', '2026-01-23', '2026-01-30', '2026-02-06',
  '2026-02-13', '2026-02-20', '2026-02-27', '2026-03-06', '2026-03-13',
  '2026-03-20', '2026-03-27', '2026-04-03', '2026-04-10', '2026-04-17',
  '2026-04-24', '2026-05-01', '2026-05-08', '2026-05-16'
];

const DB_CONFIG = {
  host: process.env.DB_HOST || 'db',
  port: parseInt(process.env.DB_PORT || '5432'),
  database: process.env.DB_NAME || 'football_db',
  user: process.env.DB_USER || 'football_user',
  password: process.env.DB_PASSWORD || 'football_pass',
  max: 10,
  idleTimeoutMillis: 30000,
  connectionTimeoutMillis: 10000,
};

/**
 * 生成标准 round-robin 赛程 (circle method)
 */
function generateRoundRobinSchedule(teams) {
  const n = teams.length;
  const rounds = n - 1;
  const schedule = [];

  // 创建副本
  let rotation = [...teams];
  const fixed = rotation[0];
  const rotating = rotation.slice(1);

  for (let round = 0; round < rounds; round++) {
    const roundMatches = [];

    // 固定第一个球队
    roundMatches.push({
      home: rotating.length % 2 === 0 ? fixed : rotating[rotating.length - 1],
      away: rotating.length % 2 === 0 ? rotating[rotating.length - 1] : fixed
    });

    // 其他球队配对
    for (let i = 0; i < Math.floor(rotating.length / 2); i++) {
      const homeIdx = i;
      const awayIdx = rotating.length - 1 - i;

      if (homeIdx !== awayIdx) {
        roundMatches.push({
          home: rotating[homeIdx],
          away: rotating[awayIdx]
        });
      }
    }

    schedule.push(roundMatches);

    // 旋转球队 (保持第一个固定)
    rotating.unshift(rotating.pop());
  }

  return schedule;
}

/**
 * 生成完整双循环赛程 (主场 + 客场)
 */
function generateFullSchedule(teams) {
  const firstHalf = generateRoundRobinSchedule(teams);
  const secondHalf = firstHalf.map(round =>
    round.map(match => ({ home: match.away, away: match.home }))
  );
  return [...firstHalf, ...secondHalf];
}

/**
 * 生成 match_id
 */
function generateMatchId(homeTeam, awayTeam, round, isSecondHalf) {
  const homeCode = homeTeam.substring(0, 3).toUpperCase().replace(/[^A-Z]/g, '');
  const awayCode = awayTeam.substring(0, 3).toUpperCase().replace(/[^A-Z]/g, '');
  const roundStr = String(round + 1).padStart(2, '0');
  const halfCode = isSecondHalf ? 'B' : 'A';
  return `54_20252026_${roundStr}${halfCode}${homeCode}${awayCode}`;
}

/**
 * 将赛程写入数据库
 */
async function persistSchedule(pool, schedule) {
  console.log(`[入库] 开始写入 ${schedule.length} 轮赛程...`);

  let totalMatches = 0;
  let inserted = 0;
  let updated = 0;

  const client = await pool.connect();

  try {
    await client.query('BEGIN');

    for (let roundIdx = 0; roundIdx < schedule.length; roundIdx++) {
      const round = schedule[roundIdx];
      const roundDate = ROUND_DATES[roundIdx] || ROUND_DATES[ROUND_DATES.length - 1];
      const isSecondHalf = roundIdx >= schedule.length / 2;

      for (const match of round) {
        const matchId = generateMatchId(match.home, match.away, roundIdx, isSecondHalf);

        try {
          const upsertQuery = `
            INSERT INTO matches (
              match_id,
              league_name,
              season,
              home_team,
              away_team,
              match_date,
              status,
              is_finished,
              data_source,
              created_at,
              updated_at
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, NOW(), NOW())
            ON CONFLICT (match_id)
            DO UPDATE SET
              home_team = EXCLUDED.home_team,
              away_team = EXCLUDED.away_team,
              match_date = EXCLUDED.match_date,
              updated_at = NOW()
            RETURNING xmax::text::int = 0 as is_insert
          `;

          const result = await client.query(upsertQuery, [
            matchId,
            'Bundesliga',
            '2025/2026',
            match.home,
            match.away,
            roundDate,
            'scheduled',
            false,
            'V11.0-Generator'
          ]);

          if (result.rows[0]?.is_insert) {
            inserted++;
          } else {
            updated++;
          }
          totalMatches++;

        } catch (err) {
          console.error(`  ✗ ${match.home} vs ${match.away} 失败:`, err.message);
        }
      }

      if ((roundIdx + 1) % 5 === 0) {
        console.log(`  进度: ${roundIdx + 1}/${schedule.length} 轮`);
      }
    }

    await client.query('COMMIT');

  } catch (err) {
    await client.query('ROLLBACK');
    console.error('[入库] 事务失败:', err.message);
  } finally {
    client.release();
  }

  console.log(`\n[结果] 总计: ${totalMatches} 场, 新增: ${inserted}, 更新: ${updated}`);
  return { totalMatches, inserted, updated };
}

/**
 * 主函数
 */
async function main() {
  console.log('\n' + '='.repeat(70));
  console.log('  Bundesliga Fixture Generator V11.0');
  console.log('  基于 Round-Robin 算法生成 306 场标准赛程');
  console.log('='.repeat(70) + '\n');

  const pool = new Pool(DB_CONFIG);

  try {
    console.log(`[配置] 球队数: ${TEAMS.length}, 预期场次: ${TEAMS.length * (TEAMS.length - 1)}`);

    // 生成赛程
    console.log('[生成] 构建双循环赛程表...');
    const schedule = generateFullSchedule(TEAMS);
    console.log(`  ✓ 生成 ${schedule.length} 轮, ${schedule.reduce((sum, r) => sum + r.length, 0)} 场比赛`);

    // 检查当前数据
    console.log('\n[审计] 检查当前 L1 数据...');
    const beforeResult = await pool.query(`
      SELECT
        COUNT(*) as total,
        COUNT(*) FILTER (WHERE match_id LIKE '%20252026%') as valid_season
      FROM matches
      WHERE season = '2025/2026' AND league_name = 'Bundesliga'
    `);
    console.log(`  当前: ${beforeResult.rows[0].total} 场, 有效25/26: ${beforeResult.rows[0].valid_season} 场`);

    // 写入数据库
    console.log('\n[入库] 写入数据库...');
    const result = await persistSchedule(pool, schedule);

    // 最终审计
    console.log('\n[审计] 执行最终核对...');
    const afterResult = await pool.query(`
      SELECT
        COUNT(*) as total,
        COUNT(*) FILTER (WHERE match_id LIKE '%20252026%') as valid_season,
        COUNT(*) FILTER (WHERE is_finished = true) as finished
      FROM matches
      WHERE season = '2025/2026' AND league_name = 'Bundesliga'
    `);

    const { total, valid_season, finished } = afterResult.rows[0];

    console.log('\n' + '='.repeat(70));
    console.log('  【L1 赛程生成报告】');
    console.log('='.repeat(70));
    console.log(`  总记录数: ${total}`);
    console.log(`  有效25/26: ${valid_season}`);
    console.log(`  已完成: ${finished}`);
    console.log(`  目标: 306 场`);
    console.log(`  达成率: ${Math.round((parseInt(valid_season) / 306) * 100)}%`);
    console.log('='.repeat(70));

    if (parseInt(valid_season) >= 306) {
      console.log('\n  🎉 L1 种子补齐完成！306 场全部到位！');
      console.log('  ✅ 现在可以执行 V11.0 二次收割填充 L2 映射表\n');
    } else {
      console.log(`\n  ⚠️  还需补充 ${306 - parseInt(valid_season)} 场\n`);
    }

  } catch (err) {
    console.error('[致命错误]', err);
    process.exit(1);
  } finally {
    await pool.end();
  }
}

main().catch(console.error);
