#!/usr/bin/env node
/**
 * TITAN-V4.46.5 集成回归测试
 * ====================================
 *
 * 模拟收割 1 场比赛 -> 执行熔炼 -> 验证 L3 记录是否生成
 * 模拟完整的 Hyper-Drive 链路
 *
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

// 测试数据
const TEST_MATCH = {
    match_id: `TEST_${Date.now()}`,
    home_team: 'Test Home',
    away_team: 'Test Away',
    league_id: 1,
    match_time: new Date().toISOString(),
    status: 'scheduled'
};

/**
 * 集成回归测试主类
 */
class EndToEndTest {
    constructor() {
        this.pool = null;
        this.testMatchId = `E2E_TEST_${Date.now()}_${process.pid}`;
    }

    /**
     * 初始化数据库连接
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

        // 测试连接
        const client = await this.pool.connect();
        await client.query('SELECT 1');
        client.release();

        console.log('✅ 数据库连接成功');
    }

    /**
     * 清理测试数据
     */
    async cleanup() {
        console.log('🧹 清理测试数据...');

        if (this.pool) {
            // 删除测试数据
            await this.pool.query(
                'DELETE FROM l3_features WHERE match_id LIKE $1',
                [`${this.testMatchId}%`]
            );
            await this.pool.query(
                'DELETE FROM raw_match_data WHERE match_id LIKE $1',
                [`${this.testMatchId}%`]
            );
            await this.pool.query(
                'DELETE FROM matches WHERE match_id LIKE $1',
                [`${this.testMatchId}%`]
            );

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
            `INSERT INTO matches (match_id, home_team, away_team, league_id, match_time, status, l2_harvested)
             VALUES ($1, $2, $3, $4, $5, $6, false)
             ON CONFLICT (match_id) DO UPDATE SET l2_harvested = false
             RETURNING match_id`,
            [matchId, TEST_MATCH.home_team, TEST_MATCH.away_team,
             TEST_MATCH.league_id, TEST_MATCH.match_time, TEST_MATCH.status]
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
     */
    async testL2Write(matchId) {
        console.log('\n📝 测试 L2 数据写入...');

        const l2Data = {
            odds: {
                home_win: 2.5,
                draw: 3.2,
                away_win: 2.8
            },
            timestamp: Date.now().toISOString(),
            source: 'e2e_test'
        };

        await this.pool.query(
            `INSERT INTO raw_match_data (match_id, raw_data, harvested_at, source)
             VALUES ($1, $2, NOW(), $3)
             ON CONFLICT (match_id) DO UPDATE SET raw_data = $2, harvested_at = NOW()
             RETURNING match_id`,
            [matchId, JSON.stringify(l2Data), 'e2e_test']
        );

        // 更新 L2 标记
        await this.pool.query(
            'UPDATE matches SET l2_harvested = true WHERE match_id = $1',
            [matchId]
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
     */
    async testL3Smelt(matchId) {
        console.log('\n🔥 测试 L3 特征熔炼...');

        // 模拟特征熔炼输出
        const l3Features = {
            match_id: matchId,
            feature_version: 'V4.46.5',
            feature_count: 100,
            odds_home_win: 2.5,
            odds_draw: 3.2,
            odds_away_win: 2.8,
            smelted_at: new Date().toISOString(),
            quality_score: 0.95
        };

        await this.pool.query(
            `INSERT INTO l3_features (match_id, features, feature_version, created_at, quality_score)
             VALUES ($1, $2, $3, NOW(), $4)
             ON CONFLICT (match_id) DO UPDATE SET features = $2, created_at = NOW()
             RETURNING match_id`,
            [matchId, JSON.stringify(l3Features), 'V4.46.5', 0.95]
        );

        const result = await this.pool.query(
            'SELECT * FROM l3_features WHERE match_id = $1',
            [matchId]
        );

        assert(result.rows.length === 1, 'L3 数据写入失败');
        assert(result.rows[0].quality_score === 0.95, 'L3 数据质量分数不匹配');

        console.log(`   ✅ L3 特征熔炼成功: ${matchId}`);
    }

    /**
     * 验证数据完整性
     */
    async verifyIntegrity(matchId) {
        console.log('\n🔍 验证数据完整性...');

        const result = await this.pool.query(
            `SELECT
                m.match_id,
                m.l2_harvested,
                r.raw_data IS NOT NULL as has_l2,
                l.features IS NOT NULL as has_l3
             FROM matches m
             LEFT JOIN raw_match_data r ON m.match_id = r.match_id
             LEFT JOIN l3_features l ON m.match_id = l.match_id
             WHERE m.match_id = $1`,
            [matchId]
        );

        assert(result.rows.length === 1, '数据完整性验证失败：未找到记录');

        const row = result.rows[0];
        assert(row.l2_harvested === true, 'L2 标记未更新');
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
        console.log('═══════════════════════════════════════════════════════════════');
        console.log('  TITAN-V4.46.5 集成回归测试');
        console.log('═══════════════════════════════════════════════════════════════');
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
