/**
 * FeatureSmelter - V176 特征熔炼调度器
 * ========================================
 *
 * 批量处理 raw_match_data，调用 4 个 Extractor 生成结构化特征
 *
 * @module feature_engine/smelter/FeatureSmelter
 * @version V176.0.0
 */

'use strict';

const { Pool } = require('pg');

// 导入 4 个提取器
const { extractGoldenFeatures } = require('../extractors/GoldenFeatureExtractor');
const { extractTacticalFeatures } = require('../extractors/TacticalMomentumExtractor');
const { calculateEloFeatures } = require('../extractors/EloRatingExtractor');
const { extractOddsMovementFeatures } = require('../extractors/OddsMovementExtractor');

// ============================================================================
// 配置
// ============================================================================

const DEFAULT_CONFIG = {
    db: {
        host: process.env.DB_HOST || 'localhost',
        port: parseInt(process.env.DB_PORT || '5432'),
        database: process.env.DB_NAME || 'football_db',
        user: process.env.DB_USER || 'football_user',
        password: process.env.DB_PASSWORD || ''
    },
    batchSize: 100,
    delayMs: 10
};

// ============================================================================
// FeatureSmelter 类
// ============================================================================

class FeatureSmelter {
    constructor(config = {}) {
        this.config = { ...DEFAULT_CONFIG, ...config };
        this.pool = null;
        this.stats = {
            total: 0,
            success: 0,
            failed: 0,
            skipped: 0
        };
    }

    /**
     * 初始化数据库连接
     */
    async init() {
        this.pool = new Pool({
            ...this.config.db,
            max: 10,
            idleTimeoutMillis: 30000
        });

        // 测试连接
        const client = await this.pool.connect();
        await client.query('SELECT 1');
        client.release();

        console.log('✅ FeatureSmelter 数据库连接就绪');
        return this;
    }

    /**
     * 获取待处理的比赛列表
     * @param {boolean} fullRecalculate - 是否全量重算
     * @param {number} limit - 批量大小
     */
    async getPendingMatches(fullRecalculate = false, limit = 1000) {
        const query = fullRecalculate
            ? `SELECT m.match_id, m.external_id, m.home_team, m.away_team, m.match_date, r.raw_data
               FROM matches m
               JOIN raw_match_data r ON m.match_id = r.match_id
               WHERE m.external_id IS NOT NULL AND r.raw_data IS NOT NULL
               ORDER BY m.match_date ASC
               LIMIT $1`
            : `SELECT m.match_id, m.external_id, m.home_team, m.away_team, m.match_date, r.raw_data
               FROM matches m
               JOIN raw_match_data r ON m.match_id = r.match_id
               LEFT JOIN l3_features f ON m.match_id = f.match_id
               WHERE m.external_id IS NOT NULL
                 AND r.raw_data IS NOT NULL
                 AND f.match_id IS NULL
               ORDER BY m.match_date ASC
               LIMIT $1`;

        const result = await this.pool.query(query, [limit]);
        return result.rows;
    }

    /**
     * 提取单场比赛的所有特征
     * @param {Object} rawData - 原始 JSON 数据
     * @param {Object} matchInfo - 比赛基本信息
     * @returns {Object} 结构化特征
     */
    extractAllFeatures(rawData, matchInfo) {
        const features = {
            match_id: matchInfo.match_id,
            external_id: matchInfo.external_id
        };

        try {
            // 1. 黄金特征 (身价/伤病/评分)
            features.golden_features = extractGoldenFeatures(rawData);

            // 2. 战术动量特征 (xG/控球/射门/momentum)
            features.tactical_features = extractTacticalFeatures(rawData);

            // 3. 赔率变动特征 (隐含概率/Steam信号)
            features.odds_features = extractOddsMovementFeatures(rawData, features.tactical_features);

            // 4. Elo 特征 (简化版，需要历史数据时使用 calculateEloFeatures)
            features.elo_features = {
                home_elo_pre: 1500,
                away_elo_pre: 1500,
                elo_diff: 0,
                expected_home_win: 0.5,
                _version: 'V176.0.0',
                _note: 'Elo 需要历史比赛数据，请使用 EloRatingExtractor 批量计算'
            };

            // 元数据
            features._extractedAt = new Date().toISOString();
            features._version = 'V176.0.0';

            return features;

        } catch (error) {
            console.error(`特征提取失败 [${matchInfo.match_id}]: ${error.message}`);
            return {
                match_id: matchInfo.match_id,
                external_id: matchInfo.external_id,
                _error: error.message
            };
        }
    }

    /**
     * 将特征写入数据库
     * @param {Object} features - 结构化特征
     */
    async upsertFeatures(features) {
        const query = `
            INSERT INTO l3_features (
                match_id,
                golden_features,
                tactical_features,
                elo_features,
                odds_features,
                created_at,
                updated_at
            )
            VALUES ($1, $2, $3, $4, $5, NOW(), NOW())
            ON CONFLICT (match_id)
            DO UPDATE SET
                golden_features = EXCLUDED.golden_features,
                tactical_features = EXCLUDED.tactical_features,
                elo_features = EXCLUDED.elo_features,
                odds_features = EXCLUDED.odds_features,
                updated_at = NOW()
        `;

        await this.pool.query(query, [
            features.match_id,
            JSON.stringify(features.golden_features || {}),
            JSON.stringify(features.tactical_features || {}),
            JSON.stringify(features.elo_features || {}),
            JSON.stringify(features.odds_features || {})
        ]);
    }

    /**
     * 执行熔炼
     * @param {Object} options - 配置选项
     */
    async run(options = {}) {
        const { fullRecalculate = false, dryRun = false, limit = 1000 } = options;

        console.log('═══════════════════════════════════════════════════════════════');
        console.log('  V176 FeatureSmelter - 特征熔炼');
        console.log('═══════════════════════════════════════════════════════════════');
        console.log(`  fullRecalculate: ${fullRecalculate}`);
        console.log(`  dryRun: ${dryRun}`);
        console.log('═══════════════════════════════════════════════════════════════');

        // 获取待处理比赛
        const matches = await this.getPendingMatches(fullRecalculate, limit);
        this.stats.total = matches.length;

        console.log(`📋 待处理比赛: ${matches.length} 场`);

        if (matches.length === 0) {
            console.log('🎉 没有待处理的比赛');
            return this.stats;
        }

        // 处理每场比赛
        for (let i = 0; i < matches.length; i++) {
            const match = matches[i];

            try {
                // 解析原始数据
                let rawData = match.raw_data;
                if (typeof rawData === 'string') {
                    rawData = JSON.parse(rawData);
                }

                if (!rawData) {
                    this.stats.skipped++;
                    continue;
                }

                // 提取特征
                const features = this.extractAllFeatures(rawData, match);

                // 写入数据库
                if (!dryRun) {
                    await this.upsertFeatures(features);
                }

                this.stats.success++;

                // 进度报告
                if ((i + 1) % 50 === 0 || i === matches.length - 1) {
                    console.log(`✅ 进度: ${i + 1}/${matches.length} | 成功: ${this.stats.success}`);
                }

                // 延迟
                if (this.config.delayMs > 0) {
                    await new Promise(r => setTimeout(r, this.config.delayMs));
                }

            } catch (error) {
                this.stats.failed++;
                console.error(`❌ [${match.match_id}]: ${error.message}`);
            }
        }

        // 报告
        this.printReport();

        return this.stats;
    }

    /**
     * 打印熔炼报告
     */
    printReport() {
        console.log('═══════════════════════════════════════════════════════════════');
        console.log('  📊 熔炼完成报告');
        console.log('═══════════════════════════════════════════════════════════════');
        console.log(`  总计: ${this.stats.total}`);
        console.log(`  成功: ${this.stats.success}`);
        console.log(`  失败: ${this.stats.failed}`);
        console.log(`  跳过: ${this.stats.skipped}`);
        console.log('═══════════════════════════════════════════════════════════════');
    }

    /**
     * 关闭数据库连接
     */
    async close() {
        if (this.pool) {
            await this.pool.end();
            console.log('🛹 FeatureSmelter 连接已关闭');
        }
    }
}

// ============================================================================
// 导出
// ============================================================================

module.exports = { FeatureSmelter, DEFAULT_CONFIG };
