/**
 * MarketSentimentExtractor - V6.0 市场情绪提取器
 * ================================================
 *
 * 从 OddsPortal 赔率数据中提取市场情绪特征
 * 集成 BridgeRadar C++ 引擎实现队名对齐
 *
 * @module feature_engine/smelter/components/MarketSentimentExtractor
 * @version V6.0.0
 * @since 2026-03-14
 */

'use strict';

const { BaseExtractor, ExtractorError } = require('./BaseExtractor');

// ============================================================================
// 配置常量
// ============================================================================

const DEFAULT_CONFIG = {
  alignmentTimeoutMs: 10,   // C++ 对齐超时 10ms
  defaultOdds: [2.0, 3.2, 3.5],
  enableRapidFuzz: false,   // 是否启用真实 RapidFuzz
  rapidFuzzThreshold: 70    // 匹配阈值
};

// ============================================================================
// MarketSentimentExtractor 类
// ============================================================================

class MarketSentimentExtractor extends BaseExtractor {
  /**
   * 创建市场情绪提取器实例
   * @param {Object} config - 配置对象
   */
  constructor(config = {}) {
    super({
      name: 'MarketSentimentExtractor',
      version: 'V6.0.0',
      config: { ...DEFAULT_CONFIG, ...config }
    });
    this.rapidfuzz = null;
    this._initializeEngine();
  }

  getDefaultConfig() {
    return { ...DEFAULT_CONFIG };
  }

  getFeatureNames() {
    return [
      'market_sentiment',
      'odds_drop',
      'market_margin',
      'odds_efficiency_score',
      'market_implied_bias',
      'bookie_consensus_index',
      'market_volatility',
      'money_flow_index',
      'contrarian_signal'
    ];
  }

  /**
   * 初始化 C++ 引擎
   * @private
   */
  _initializeEngine() {
    if (this.config.enableRapidFuzz) {
      try {
        this.rapidfuzz = require('rapidfuzz');
        this.logger.info('✅ RapidFuzz C++ 引擎加载成功');
      } catch (err) {
        this.logger.warn('⚠️  RapidFuzz 未安装，使用纯 JavaScript 回退');
      }
    }
  }

  /**
   * 提取市场情绪特征 (主入口)
   * @param {Object} context - 上下文对象
   * @param {string} context.matchId - 比赛ID
   * @param {Object} context.oddsData - 赔率数据
   * @returns {Promise<Object>} 市场情绪特征
   */
  async extract(context) {
    const { matchId, oddsData = {} } = context;

    this.logger.debug(`开始提取市场情绪特征: ${matchId}`);

    try {
      const sentiment = this._extractMarketSentiment(oddsData);
      
      this.logger.info(`✅ 市场情绪特征提取完成: ${matchId}`);
      
      return {
        market_sentiment: sentiment,
        metadata: {
          extracted_at: new Date().toISOString(),
          version: 'V6.0.0',
          extractor: this.name
        }
      };
    } catch (error) {
      this.logger.error(`❌ 市场情绪特征提取失败: ${matchId}`, error);
      
      // 返回默认值 (Mean Imputation)
      return {
        market_sentiment: this._getDefaultSentiment(),
        metadata: {
          extracted_at: new Date().toISOString(),
          version: 'V6.0.0-FALLBACK',
          extractor: this.name,
          error: error.message
        }
      };
    }
  }

  /**
   * 对齐队名 - 使用 C++ 引擎
   * @param {string} fotmobTeamName - FotMob 队名
   * @param {Array<string>} oddsPortalCandidates - OddsPortal 候选列表
   * @returns {Object} 对齐结果
   */
  alignTeams(fotmobTeamName, oddsPortalCandidates) {
    const startTime = Date.now();
    
    let result;
    if (this.rapidfuzz) {
      result = this._alignWithRapidFuzz(fotmobTeamName, oddsPortalCandidates);
    } else {
      result = this._alignWithJS(fotmobTeamName, oddsPortalCandidates);
    }
    
    const elapsedMs = Date.now() - startTime;
    
    return {
      fotmobName: fotmobTeamName,
      matchedName: result.match,
      confidence: result.score,
      elapsedMs,
      success: result.match !== null && elapsedMs < this.config.alignmentTimeoutMs
    };
  }

  /**
   * 计算赔率降幅
   * @param {number} openingOdds - 初始赔率
   * @param {number} closingOdds - 终盘赔率
   * @returns {number} odds_drop 特征值
   */
  calculateOddsDrop(openingOdds, closingOdds) {
    if (openingOdds <= 0 || closingOdds <= 0) {
      throw new Error('赔率必须大于0');
    }
    
    const drop = (openingOdds - closingOdds) / openingOdds;
    return Number(drop.toFixed(4));
  }

  /**
   * 计算市场抽水率 (Margin)
   * @param {Array<number>} odds - 1X2 赔率 [home, draw, away]
   * @returns {number} market_margin 值
   */
  calculateMarketMargin(odds) {
    if (!Array.isArray(odds) || odds.length !== 3) {
      throw new Error('1X2 赔率必须是长度为3的数组');
    }
    
    if (odds.some(o => o <= 0)) {
      throw new Error('赔率必须大于0');
    }
    
    const impliedProbabilities = odds.map(o => 1 / o);
    const totalProbability = impliedProbabilities.reduce((a, b) => a + b, 0);
    const margin = totalProbability - 1;
    
    return Number(margin.toFixed(4));
  }

  // ============================================================================
  // 私有方法
  // ============================================================================

  /**
   * 使用 RapidFuzz 对齐
   * @private
   */
  _alignWithRapidFuzz(teamName, candidates) {
    let bestMatch = null;
    let bestScore = 0;
    
    for (const candidate of candidates) {
      const score = this.rapidfuzz.fuzz.WRatio(teamName, candidate);
      if (score > bestScore) {
        bestScore = score;
        bestMatch = candidate;
      }
    }
    
    if (bestScore >= this.config.rapidFuzzThreshold) {
      return { match: bestMatch, score: bestScore };
    }
    return { match: null, score: bestScore };
  }

  /**
   * 使用纯 JS 对齐 (回退)
   * @private
   */
  _alignWithJS(teamName, candidates) {
    let bestMatch = null;
    let bestScore = 0;
    
    for (const candidate of candidates) {
      const score = this._calculateSimilarity(teamName, candidate);
      if (score > bestScore) {
        bestScore = score;
        bestMatch = candidate;
      }
    }
    
    if (bestScore >= this.config.rapidFuzzThreshold) {
      return { match: bestMatch, score: bestScore };
    }
    return { match: null, score: bestScore };
  }

  /**
   * 计算字符串相似度
   * @private
   */
  _calculateSimilarity(str1, str2) {
    const s1 = str1.toLowerCase().replace(/[^a-z0-9]/g, '');
    const s2 = str2.toLowerCase().replace(/[^a-z0-9]/g, '');
    
    if (s1 === s2) return 100;
    if (s1.includes(s2) || s2.includes(s1)) return 85;
    
    let common = 0;
    const minLen = Math.min(s1.length, s2.length);
    for (let i = 0; i < minLen; i++) {
      if (s1[i] === s2[i]) common++;
    }
    
    return Math.round((common / Math.max(s1.length, s2.length)) * 100);
  }

  /**
   * 提取完整市场情绪特征
   * @private
   */
  _extractMarketSentiment(oddsData) {
    const {
      openingOdds = this.config.defaultOdds,
      closingOdds = this.config.defaultOdds
    } = oddsData;

    const oddsDrop = this.calculateOddsDrop(openingOdds[0], closingOdds[0]);
    const marketMargin = this.calculateMarketMargin(closingOdds);
    
    return {
      odds_drop: oddsDrop,
      market_margin: marketMargin,
      odds_efficiency_score: this._calculateEfficiencyScore(openingOdds, closingOdds),
      market_implied_bias: this._calculateImpliedBias(closingOdds),
      bookie_consensus_index: this._calculateConsensusIndex(oddsData),
      market_volatility: this._calculateVolatility(openingOdds, closingOdds),
      money_flow_index: this._calculateMoneyFlow(oddsData),
      contrarian_signal: this._calculateContrarianSignal(oddsData),
      extracted_at: new Date().toISOString(),
      version: 'V6.0.0'
    };
  }

  /**
   * 计算赔率效率分
   * @private
   */
  _calculateEfficiencyScore(opening, closing) {
    const drops = opening.map((o, i) => Math.abs(o - closing[i]) / o);
    const avgDrop = drops.reduce((a, b) => a + b, 0) / drops.length;
    return Number((1 - avgDrop).toFixed(4));
  }

  /**
   * 计算市场隐含偏见
   * @private
   */
  _calculateImpliedBias(odds) {
    const probs = odds.map(o => 1 / o);
    const homeBias = probs[0] - probs[2];
    return Number(homeBias.toFixed(4));
  }

  /**
   * 计算庄家共识指数
   * @private
   */
  _calculateConsensusIndex(oddsData) {
    const { openingOdds = this.config.defaultOdds, closingOdds = this.config.defaultOdds } = oddsData;
    const relativeMoves = openingOdds.map((opening, index) => {
      const closing = closingOdds[index] || opening;
      return Math.abs(closing - opening) / opening;
    });
    const avgMove = relativeMoves.reduce((sum, value) => sum + value, 0) / relativeMoves.length;
    return Number(Math.max(0, Math.min(1, 1 - avgMove * 2)).toFixed(4));
  }

  /**
   * 计算市场波动性
   * @private
   */
  _calculateVolatility(opening, closing) {
    const drops = opening.map((o, i) => Math.abs(o - closing[i]) / o);
    const avgVolatility = drops.reduce((a, b) => a + b, 0) / drops.length;
    return Number(avgVolatility.toFixed(4));
  }

  /**
   * 计算资金流向指标
   * @private
   */
  _calculateMoneyFlow(oddsData) {
    const { openingOdds = this.config.defaultOdds, closingOdds = this.config.defaultOdds } = oddsData;
    const homeFlow = (1 / closingOdds[0]) - (1 / openingOdds[0]);
    const awayFlow = (1 / closingOdds[2]) - (1 / openingOdds[2]);
    return Number(Math.max(-1, Math.min(1, homeFlow - awayFlow)).toFixed(4));
  }

  /**
   * 计算逆向信号强度
   * @private
   */
  _calculateContrarianSignal(oddsData) {
    const consensus = this._calculateConsensusIndex(oddsData);
    const moneyFlow = Math.abs(this._calculateMoneyFlow(oddsData));
    return Number(Math.max(0, Math.min(1, moneyFlow * (1 - consensus))).toFixed(4));
  }

  /**
   * 获取默认市场情绪特征 (Mean Imputation)
   * @private
   */
  _getDefaultSentiment() {
    return {
      odds_drop: 0,
      market_margin: 0.05,
      odds_efficiency_score: 0.85,
      market_implied_bias: 0,
      bookie_consensus_index: 0.825,
      market_volatility: 0.05,
      money_flow_index: 0,
      contrarian_signal: 0.5,
      extracted_at: new Date().toISOString(),
      version: 'V6.0.0-DEFAULT',
      is_default: true
    };
  }
}

// ============================================================================
// 导出
// ============================================================================

module.exports = { MarketSentimentExtractor };
