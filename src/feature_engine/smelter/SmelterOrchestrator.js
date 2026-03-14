/**
 * SmelterOrchestrator - V5.2 特征熔炼编排器
 * ==========================================
 *
 * V5.2 模块化重构后的新入口。
 * 职责：调用 DataFetcher 拿数据 -> 调用 Extractors 算特征 -> 调用 L3Writer 存结果。
 *
 * @module feature_engine/smelter/SmelterOrchestrator
 * @version V5.2.0-MODULAR
 * @since 2026-03-14
 */

'use strict';

const { DataFetcher } = require('./components/DataFetcher');
const { L3Writer } = require('./components/L3Writer');
const { GoldenExtractor } = require('./components/GoldenExtractor');
const { TacticalExtractor } = require('./components/TacticalExtractor');
const { RollingFeatureExtractor } = require('./components/RollingFeatureExtractor');
const { EfficiencyFeatureExtractor } = require('./components/EfficiencyFeatureExtractor');
const { DrawPropensityExtractor } = require('./components/DrawPropensityExtractor');
const { StructuredLogger } = require('../../utils/StructuredLogger');

// 导入旧的提取器（赔率）直到迁移完成
const { extractOddsMovementFeatures } = require('../extractors/OddsMovementExtractor');

// ============================================================================
// 配置常量
// ============================================================================

const DEFAULT_CONFIG = {
    batchSize: 500,
    delayMs: 5,
    enableStreaming: false,
    logDir: '/app/logs/pipeline',
    defaultEloRating: 1500
};

// ============================================================================
// SmelterOrchestrator 类
// ============================================================================

/**
 * 特征熔炼编排器
 */
class SmelterOrchestrator {
    /**
     * @param {object} options - 配置选项
     * @param {object} options.pool - 数据库连接池（必填）
     * @param {object} options.config - 额外配置
     */
    constructor(options = {}) {
        if (!options.pool) {
            throw new Error('SmelterOrchestrator 需要数据库连接池');
        }

        this.config = { ...DEFAULT_CONFIG, ...(options.config || {}) };
        this.pool = options.pool;

        // 初始化日志器
        this.logger = new StructuredLogger({
            component: 'SmelterOrchestrator',
            logDir: this.config.logDir,
            enableStructured: true
        });

        // 初始化组件
        this.dataFetcher = new DataFetcher({ pool: this.pool });
        this.l3Writer = new L3Writer({ pool: this.pool });
        this.goldenExtractor = new GoldenExtractor();
        this.tacticalExtractor = new TacticalExtractor();

        // V5.2 新增：38维特征提取器
        this.rollingExtractor = new RollingFeatureExtractor({
            dbPool: this.pool,
            config: { rollingWindow: 5, minSamples: 3 }
        });
        this.efficiencyExtractor = new EfficiencyFeatureExtractor({
            dbPool: this.pool,
            config: { rollingWindow: 5, minSamples: 3 }
        });
        this.drawExtractor = new DrawPropensityExtractor({
            dbPool: this.pool,
            config: { rollingWindow: 10, minSamples: 5 }
        });

        // 状态
        this.isInitialized = false;
        this.stats = {
            total: 0,
            success: 0,
            failed: 0,
            skipped: 0,
            startTime: null,
            endTime: null
        };
    }

    /**
     * 初始化编排器
     * @returns {Promise<SmelterOrchestrator>}
     */
    async init() {
        try {
            // 加载 Elo 缓存
            await this.dataFetcher.loadEloCache();

            this.isInitialized = true;
            this.logger.info('SmelterOrchestrator V5.2 初始化完成', {
                eloTeams: this.dataFetcher.eloCache?.size || 0
            });

            return this;
        } catch (error) {
            this.logger.error('初始化失败', { error: error.message });
            throw error;
        }
    }

    /**
     * 执行特征熔炼
     * @param {object} options - 执行选项
     * @param {boolean} options.fullRecalculate - 是否全量重算
     * @param {number} options.limit - 处理数量限制
     * @returns {Promise<object>} 处理统计
     */
    async run(options = {}) {
        if (!this.isInitialized) {
            await this.init();
        }

        const fullRecalculate = options.fullRecalculate || false;
        const limit = options.limit || null;

        this.stats.startTime = Date.now();
        this.logger.info('开始特征熔炼', { fullRecalculate, limit });

        try {
            if (this.config.enableStreaming) {
                // 流式处理
                await this._runStreaming(fullRecalculate, limit);
            } else {
                // 批处理
                await this._runBatch(fullRecalculate, limit);
            }

            this.stats.endTime = Date.now();
            const duration = this.stats.endTime - this.stats.startTime;

            this.logger.info('特征熔炼完成', {
                total: this.stats.total,
                success: this.stats.success,
                failed: this.stats.failed,
                duration: `${duration}ms`,
                rate: this.stats.total > 0 ? (this.stats.success / this.stats.total * 100).toFixed(2) + '%' : 'N/A'
            });

            return { ...this.stats, duration };

        } catch (error) {
            this.stats.endTime = Date.now();
            this.logger.error('特征熔炼失败', { error: error.message });
            throw error;
        }
    }

    /**
     * 批处理模式
     * @private
     */
    async _runBatch(fullRecalculate, limit) {
        let processed = 0;
        let hasMore = true;

        while (hasMore) {
            const batchSize = limit
                ? Math.min(this.config.batchSize, limit - processed)
                : this.config.batchSize;

            if (batchSize <= 0) break;

            // 获取数据
            const matches = await this.dataFetcher.getPendingMatches(fullRecalculate, batchSize);

            if (matches.length === 0) {
                hasMore = false;
                break;
            }

            // 处理批次
            const features = [];
            for (const match of matches) {
                const feature = await this._processMatch(match);
                if (feature) {
                    features.push(feature);
                    this.stats.success++;
                }
                this.stats.total++;
                processed++;
            }

            // 保存批次
            if (features.length > 0) {
                await this.l3Writer.saveFeatures(features);
            }

            // 延迟
            if (this.config.delayMs > 0) {
                await this._sleep(this.config.delayMs);
            }

            hasMore = matches.length === batchSize;

            if (limit && processed >= limit) {
                break;
            }
        }
    }

    /**
     * 流式处理模式
     * @private
     */
    async _runStreaming(fullRecalculate, limit) {
        const features = [];
        let count = 0;

        for await (const match of this.dataFetcher.streamPendingMatches(fullRecalculate)) {
            if (limit && count >= limit) break;

            const feature = await this._processMatch(match);
            if (feature) {
                features.push(feature);
                this.stats.success++;

                // 批量写入
                if (features.length >= this.config.batchSize) {
                    await this.l3Writer.saveFeatures([...features]);
                    features.length = 0;
                }
            }

            this.stats.total++;
            count++;
        }

        // 写入剩余
        if (features.length > 0) {
            await this.l3Writer.saveFeatures(features);
        }
    }

    /**
     * 处理单场比赛
     * @private
     * @param {object} match - 比赛数据
     * @returns {object|null} 特征对象或 null
     */
    async _processMatch(match) {
        const { match_id, home_team, away_team, raw_data } = match;

        if (!raw_data) {
            this.logger.debug('跳过：无原始数据', { match_id });
            this.stats.skipped++;
            return null;
        }

        try {
            // 提取所有特征（5个提取器）
            const allFeatures = await this._extractAllFeatures({
                match_id,
                home_team,
                away_team,
                ...raw_data
            });

            // 获取 Elo 特征
            const eloFeatures = this.dataFetcher.getEloFeatures(home_team, away_team);

            // 分离各维度特征
            const goldenFeatures = this.goldenExtractor.extract(raw_data);
            const tacticalFeatures = this.tacticalExtractor.extract(raw_data);
            const oddsMovementFeatures = extractOddsMovementFeatures(raw_data);

            return {
                match_id,
                external_id: match.external_id || match_id,
                golden_features: goldenFeatures,
                tactical_features: tacticalFeatures,
                odds_movement_features: oddsMovementFeatures,
                rolling_features: allFeatures.rolling || {},
                efficiency_features: allFeatures.efficiency || {},
                draw_features: allFeatures.draw || {},
                elo_features: eloFeatures,
                computed_at: new Date().toISOString()
            };

        } catch (error) {
            this.logger.error('特征提取失败', {
                match_id,
                error: error.message
            });
            this.stats.failed++;
            return null;
        }
    }

    /**
     * 提取全部特征（V5.2 38维）
     * @private
     * @param {object} matchData - 比赛数据
     * @returns {object} 完整特征集
     */
    async _extractAllFeatures(matchData) {
        const { match_id, home_team, away_team, match_date } = matchData;

        // 基础特征提取（同步）
        const goldenFeatures = this.goldenExtractor.extract(matchData);
        const tacticalFeatures = this.tacticalExtractor.extract(matchData);

        // 构建基础上下文
        const baseFeatures = {
            ...goldenFeatures,
            ...tacticalFeatures,
            match_id,
            home_team,
            away_team,
            match_date: match_date || new Date().toISOString()
        };

        // 获取ELO和H2H特征
        const eloFeatures = this.dataFetcher.getEloFeatures(home_team, away_team);
        Object.assign(baseFeatures, eloFeatures);

        // V5.2 新增：异步提取历史依赖特征
        let rollingFeatures = {};
        let efficiencyFeatures = {};
        let drawFeatures = {};

        try {
            // 并行提取新特征
            const [rolling, efficiency, draw] = await Promise.allSettled([
                this.rollingExtractor.extract(baseFeatures),
                this.efficiencyExtractor.extract(baseFeatures),
                this.drawExtractor.extract(baseFeatures)
            ]);

            if (rolling.status === 'fulfilled') {
                rollingFeatures = rolling.value || {};
            } else {
                this.logger.warn('Rolling特征提取失败', { match_id, error: rolling.reason?.message });
            }

            if (efficiency.status === 'fulfilled') {
                efficiencyFeatures = efficiency.value || {};
            } else {
                this.logger.warn('Efficiency特征提取失败', { match_id, error: efficiency.reason?.message });
            }

            if (draw.status === 'fulfilled') {
                drawFeatures = draw.value || {};
            } else {
                this.logger.warn('Draw特征提取失败', { match_id, error: draw.reason?.message });
            }
        } catch (error) {
            this.logger.error('新特征提取异常', { match_id, error: error.message });
        }

        // 合并所有特征（38维）
        return {
            ...baseFeatures,
            ...rollingFeatures,
            ...efficiencyFeatures,
            ...drawFeatures,
            rolling: rollingFeatures,
            efficiency: efficiencyFeatures,
            draw: drawFeatures,
            _version: 'V5.2.0',
            _extractedAt: new Date().toISOString()
        };
    }

    /**
     * 获取统计信息
     * @returns {object}
     */
    getStats() {
        return {
            ...this.stats,
            dataFetcher: this.dataFetcher.getStats(),
            l3Writer: this.l3Writer.getStats(),
            goldenExtractor: this.goldenExtractor.getStats(),
            tacticalExtractor: this.tacticalExtractor.getStats()
        };
    }

    /**
     * 关闭资源
     */
    async close() {
        this.logger.info('SmelterOrchestrator 关闭');
    }

    /**
     * 睡眠
     * @private
     */
    _sleep(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }
}

// ============================================================================
// 导出
// ============================================================================
module.exports = {
    SmelterOrchestrator,
    DEFAULT_CONFIG
};
