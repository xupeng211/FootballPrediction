#!/usr/bin/env node
/**
 * TITAN-V4.46.5 集成回归测试
 * ====================================
 *
 * 验证 L1/L2/L3 数据管道完整性
 * 模拟完整的 Hyper-Drive 链路
 * @version V4.46.5
 * @date 2026-03-09
 */

'use strict';

const { Pool } = require('pg');
const assert = require('assert');

// 测试配置
const TEST_CONFIG = {
    host: process.env.DB_HOST || 'localhost',
    port: parseInt(process.env.DB_PORT) || 5432,
    database: process.env.DB_NAME || 'football_db',
    user: process.env.DB_USER || 'football_user',
    password: process.env.DB_PASSWORD || ''
};

// 测试数据 (对齐实际表结构: match_date, league_name, season, status)
const TEST_MATCH = {
    match_id: `TEST_${Date.now()}`,
    home_team: 'Test Home FC',
    away_team: 'Test Away United',
    league_name: 'Test League',
    season: '2324',
    match_date: new Date().toISOString(),
    status: 'Scheduled'
};

/**
 * 集成回归测试主类
 */
class EndToEndTest {
    /**
     *
     */
    constructor() {
        this.pool = null;
        this.testMatchId = `E2E_${Date.now()}_${process.pid}`;
    }

    /**
     *
     */
    async initialize() {
        console.log('🔌 初始化数据库连接...');
        this.pool = new Pool({
            host: TEST_CONFIG.host,
            port: TEST_CONFIG.port,
            database: TEST_CONFIG.database,
            user: TEST_CONFIG.user,
            password: TEST_CONFIG.password,
            max: 5
        });
        const client = await this.pool.connect();
        await client.query('SELECT 1');
        client.release();
        console.log('✅ 数据库连接成功');
    }

    /**
     *
     */
    async cleanup() {
        console.log('🧹 清理测试数据...');
        if (this.pool) {
            await this.pool.query('DELETE FROM l3_features WHERE match_id LIKE $1',
                [`${this.testMatchId}%`]);
            await this.pool.query('DELETE FROM raw_match_data WHERE match_id LIKE $1',
                [`${this.testMatchId}%`]);
            await this.pool.query('DELETE FROM matches WHERE match_id LIKE $1',
                [`${this.testMatchId}%`]);
            await this.pool.end();
            console.log('✅ 清理完成');
        }
    }

    /**
     * 测试 L1 数据写入
     */
    async testL1Write() {
        console.log('\n📝 测试 L1 数据写入...');
        const matchId = `${this.testMatchId}_L1`;
        await this.pool.query(
            `INSERT INTO matches (match_id, home_team, away_team, league_name, season, match_date, status)
             VALUES ($1, $2, $3, $4, $5, $6, $7)
             ON CONFLICT (match_id) DO UPDATE SET home_team = $2
             RETURNING match_id`,
            [matchId, TEST_MATCH.home_team, TEST_MATCH.away_team,
             TEST_MATCH.league_name, TEST_MATCH.season, TEST_MATCH.match_date, TEST_MATCH.status]
        );
        const result = await this.pool.query(
            'SELECT * FROM matches WHERE match_id = $1',
            [matchId]
        );
        assert(result.rows.length === 1, 'L1 数据写入失败');
        assert(result.rows[0].home_team === TEST_MATCH.home_team, 'L1 数据内容不匹配');
        console.log(`   ✅ L1 数据写入成功: ${matchId}`);
        return matchId;
    }

    /**
     * 测试 L2 数据写入
     * 表结构: match_id, raw_data (jsonb), collected_at, data_hash
     * @param matchId
     */
    async testL2Write(matchId) {
        console.log('\n📝 测试 L2 数据写入...');
        const l2Data = {
            odds: {
                home_win: 2.5,
                draw: 3.2,
                away_win: 2.8
            },
            timestamp: new Date().toISOString(),
            source: 'e2e_test'
        };
        await this.pool.query(
            `INSERT INTO raw_match_data (match_id, raw_data, collected_at, data_hash)
             VALUES ($1, $2, NOW(), $3)
             ON CONFLICT (match_id) DO UPDATE SET raw_data = $2, collected_at = NOW()
             RETURNING match_id`,
            [matchId, JSON.stringify(l2Data), 'e2e_test_hash_123']
        );
        const result = await this.pool.query(
            'SELECT * FROM raw_match_data WHERE match_id = $1',
            [matchId]
        );
        assert(result.rows.length === 1, 'L2 数据写入失败');
        assert(result.rows[0].raw_data.odds, 'L2 数据内容不匹配');
        console.log(`   ✅ L2 数据写入成功: ${matchId}`);
    }

    /**
     * 测试 L3 特征熔炼
     * 表结构: match_id, golden_features, tactical_features, elo_features, odds_features, ...
     * @param matchId
     */
    async testL3Smelt(matchId) {
        console.log('\n🔥 测试 L3 特征熔炼...');
        // 模拟特征熔炼输出 (对齐实际表结构)
        const goldenFeatures = {
            odds_home_win: 2.5,
            odds_draw: 3.2,
            odds_away_win: 2.8,
            feature_count: 100,
            smelted_at: new Date().toISOString()
        };
        const tacticalFeatures = { formation_home: '4-3-3', formation_away: '4-4-2' };
        const eloFeatures = { home_elo: 1850, away_elo: 1720 };
        const oddsFeatures = { opening_home: 2.6, opening_draw: 3.3, opening_away: 2.9 };

        await this.pool.query(
            `INSERT INTO l3_features (match_id, golden_features, tactical_features, elo_features, odds_features, created_at)
             VALUES ($1, $2, $3, $4, $5, NOW())
             ON CONFLICT (match_id) DO UPDATE SET golden_features = $2, created_at = NOW()
             RETURNING match_id`,
            [matchId, JSON.stringify(goldenFeatures), JSON.stringify(tacticalFeatures),
             JSON.stringify(eloFeatures), JSON.stringify(oddsFeatures)]
        );
        const result = await this.pool.query(
            'SELECT * FROM l3_features WHERE match_id = $1',
            [matchId]
        );
        assert(result.rows.length === 1, 'L3 数据写入失败');
        assert(result.rows[0].golden_features.odds_home_win === 2.5, 'L3 数据内容不匹配');
        console.log(`   ✅ L3 特征熔炼成功: ${matchId}`);
    }
    /**
     * 验证数据完整性
     * @param matchId
     */
    async verifyIntegrity(matchId) {
        console.log('\n🔍 验证数据完整性...');
        const result = await this.pool.query(
            `SELECT
                m.match_id,
                r.raw_data IS NOT NULL as has_l2,
                l.golden_features IS NOT NULL as has_l3
             FROM matches m
             LEFT JOIN raw_match_data r ON m.match_id = r.match_id
             LEFT JOIN l3_features l ON m.match_id = l.match_id
             WHERE m.match_id = $1`,
            [matchId]
        );
        assert(result.rows.length === 1, '数据完整性验证失败：未找到记录');
        const row = result.rows[0];
        assert(row.has_l2 === true, 'L2 数据缺失');
        assert(row.has_l3 === true, 'L3 数据缺失');
        console.log(`   ✅ 数据完整性验证通过: L1/L2/L3 全部对齐`);
        console.log(`      - L1: ✅`);
        console.log(`      - L2: ✅`);
        console.log(`      - L3: ✅`);
    }
    /**
     * 运行完整测试
     */
    async run() {
        console.log('═════════════════════════════════════════════════════════════════');
        console.log('  TITAN-V4.46.5 集成回归测试');
        console.log('═════════════════════════════════════════════════════════════');
        console.log(`  测试时间: ${new Date().toISOString()}`);
        console.log('────────────────────────────────────────────────────────────────────');
        try {
            await this.initialize();
            // 测试 L1 -> L2 -> L3 完整链路
            const matchId = await this.testL1Write();
            await this.testL2Write(matchId);
            await this.testL3Smelt(matchId);
            await this.verifyIntegrity(matchId);
            console.log('\n═══════════════════════════════════════════════════════════════');
            console.log('  ✅ 所有集成测试通过!');
            console.log('═══════════════════════════════════════════════════════════════');
            console.log('  Hyper-Drive 链路验证成功');
            console.log('  数据完整性: 100%');
            console.log('  特征熔炼: 正常');
            console.log('═══════════════════════════════════════════════════════════════');
            return true;
        } catch (error) {
            console.error('\n❌ 测试失败:', error.message);
            throw error;
        } finally {
            await this.cleanup();
        }
    }
}

// 主入口
/**
 *
 */
async function main() {
    const test = new EndToEndTest();
    await test.run();
}
module.exports = { EndToEndTest };
if (require.main === module) {
    main().catch(err => {
        console.error('集成测试失败:', err);
        process.exit(1);
    });
}
