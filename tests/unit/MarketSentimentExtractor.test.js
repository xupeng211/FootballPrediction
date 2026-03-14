/**
 * TITAN V6.0 Data Convergence - MarketSentimentExtractor TDD Tests
 * 任务: TITAN-V6.0-DATA-CONVERGENCE
 * 
 * 市场情绪提取器测试套件
 * - 对齐验证: BridgeRadarEngine C++ 必须在 < 10ms 内返回正确关联
 * - 降幅逻辑: odds_drop 特征计算
 * - 抽水率计算: market_margin 计算
 */

const assert = require('node:assert');
const { describe, it, beforeEach } = require('node:test');

// ============================================================================
// MarketSentimentExtractor (待实现)
// ============================================================================

class MarketSentimentExtractor {
  constructor(config = {}) {
    this.config = {
      alignmentTimeoutMs: config.alignmentTimeoutMs || 10,
      defaultOdds: config.defaultOdds || [2.0, 3.2, 3.5],
      ...config
    };
    this.bridgeRadar = null; // C++ 引擎实例
  }

  /**
   * 初始化 BridgeRadar C++ 引擎
   */
  initializeBridgeRadar() {
    // 实际生产环境将调用 rapidfuzz
    this.bridgeRadar = {
      findBestMatch: (teamName, candidates, threshold = 70) => {
        // 模拟 C++ 快速对齐
        const start = Date.now();
        
        // 简单的字符串相似度匹配
        let bestMatch = null;
        let bestScore = 0;
        
        for (const candidate of candidates) {
          const score = this._calculateSimilarity(teamName, candidate);
          if (score > bestScore) {
            bestScore = score;
            bestMatch = candidate;
          }
        }
        
        const elapsed = Date.now() - start;
        
        if (bestScore >= threshold) {
          return { match: bestMatch, score: bestScore, elapsedMs: elapsed };
        }
        return { match: null, score: bestScore, elapsedMs: elapsed };
      }
    };
    
    return this;
  }

  /**
   * 计算字符串相似度 (简化版，实际使用 rapidfuzz.WRatio)
   */
  _calculateSimilarity(str1, str2) {
    const s1 = str1.toLowerCase().replace(/[^a-z0-9]/g, '');
    const s2 = str2.toLowerCase().replace(/[^a-z0-9]/g, '');
    
    if (s1 === s2) return 100;
    
    // 包含关系
    if (s1.includes(s2) || s2.includes(s1)) return 85;
    
    // 计算共同子串长度
    let common = 0;
    const minLen = Math.min(s1.length, s2.length);
    for (let i = 0; i < minLen; i++) {
      if (s1[i] === s2[i]) common++;
    }
    
    return Math.round((common / Math.max(s1.length, s2.length)) * 100);
  }

  /**
   * 对齐验证: 给定 FotMob 队名与 OddsPortal 哈希，返回正确关联
   * @param {string} fotmobTeamName - FotMob 队名
   * @param {Array} oddsPortalCandidates - OddsPortal 候选列表
   * @returns {object} 对齐结果
   */
  alignTeams(fotmobTeamName, oddsPortalCandidates) {
    if (!this.bridgeRadar) {
      this.initializeBridgeRadar();
    }

    const startTime = Date.now();
    const result = this.bridgeRadar.findBestMatch(fotmobTeamName, oddsPortalCandidates);
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
   * @returns {number} odds_drop 特征值 (+表示降幅)
   */
  calculateOddsDrop(openingOdds, closingOdds) {
    if (openingOdds <= 0 || closingOdds <= 0) {
      throw new Error('赔率必须大于0');
    }
    
    // 降幅逻辑: (opening - closing) / opening
    // 若 2.0 -> 1.8, 降幅为 +10%
    const drop = (openingOdds - closingOdds) / openingOdds;
    return Number(drop.toFixed(4));
  }

  /**
   * 计算市场抽水率 (Margin)
   * @param {Array} odds - 1X2 赔率 [home, draw, away]
   * @returns {number} market_margin 值
   */
  calculateMarketMargin(odds) {
    if (!Array.isArray(odds) || odds.length !== 3) {
      throw new Error('1X2 赔率必须是长度为3的数组');
    }
    
    if (odds.some(o => o <= 0)) {
      throw new Error('赔率必须大于0');
    }
    
    // 计算隐含概率总和
    const impliedProbabilities = odds.map(o => 1 / o);
    const totalProbability = impliedProbabilities.reduce((a, b) => a + b, 0);
    
    // 抽水率 = 概率总和 - 1
    const margin = totalProbability - 1;
    
    return Number(margin.toFixed(4));
  }

  /**
   * 提取完整市场情绪特征 (8维度)
   * @param {object} oddsData - 赔率数据
   * @returns {object} 市场情绪特征
   */
  extractMarketSentiment(oddsData) {
    const {
      openingOdds = this.config.defaultOdds,
      closingOdds = this.config.defaultOdds,
      homeTeam,
      awayTeam,
      matchId
    } = oddsData;

    // 计算各项特征
    const oddsDrop = this.calculateOddsDrop(openingOdds[0], closingOdds[0]);
    const marketMargin = this.calculateMarketMargin(closingOdds);
    
    // 赔率效率分: 反映赔率对真实概率的拟合度
    const oddsEfficiencyScore = this._calculateEfficiencyScore(openingOdds, closingOdds);
    
    // 市场隐含偏见
    const marketImpliedBias = this._calculateImpliedBias(closingOdds);
    
    // 庄家共识指数 (模拟基于多庄家数据)
    const bookieConsensusIndex = this._calculateConsensusIndex(oddsData);
    
    // 市场波动性
    const marketVolatility = this._calculateVolatility(openingOdds, closingOdds);
    
    // 资金流向指标 (模拟)
    const moneyFlowIndex = this._calculateMoneyFlow(oddsData);
    
    // 逆向信号强度
    const contrarianSignal = this._calculateContrarianSignal(oddsData);

    return {
      odds_drop: oddsDrop,
      market_margin: marketMargin,
      odds_efficiency_score: oddsEfficiencyScore,
      market_implied_bias: marketImpliedBias,
      bookie_consensus_index: bookieConsensusIndex,
      market_volatility: marketVolatility,
      money_flow_index: moneyFlowIndex,
      contrarian_signal: contrarianSignal,
      extracted_at: new Date().toISOString(),
      version: 'V6.0.0'
    };
  }

  // 内部计算方法
  _calculateEfficiencyScore(opening, closing) {
    const drops = opening.map((o, i) => Math.abs(o - closing[i]) / o);
    const avgDrop = drops.reduce((a, b) => a + b, 0) / drops.length;
    return Number((1 - avgDrop).toFixed(4)); // 效率越高，降幅越小
  }

  _calculateImpliedBias(odds) {
    const probs = odds.map(o => 1 / o);
    const homeBias = probs[0] - probs[2]; // 主队偏见
    return Number(homeBias.toFixed(4));
  }

  _calculateConsensusIndex(oddsData) {
    // 模拟: 基于多庄家数据的一致性
    return Number((0.7 + Math.random() * 0.25).toFixed(4));
  }

  _calculateVolatility(opening, closing) {
    const drops = opening.map((o, i) => Math.abs(o - closing[i]) / o);
    const avgVolatility = drops.reduce((a, b) => a + b, 0) / drops.length;
    return Number(avgVolatility.toFixed(4));
  }

  _calculateMoneyFlow(oddsData) {
    // 模拟资金流向指标 (-1 到 1)
    return Number((Math.random() * 2 - 1).toFixed(4));
  }

  _calculateContrarianSignal(oddsData) {
    // 逆向信号强度 (0 到 1)
    return Number(Math.random().toFixed(4));
  }
}

// ============================================================================
// TDD 测试套件
// ============================================================================

describe('MarketSentimentExtractor - TITAN V6.0 Data Convergence', () => {
  
  let extractor;
  
  beforeEach(() => {
    extractor = new MarketSentimentExtractor();
  });

  describe('对齐验证 - BridgeRadar C++ 引擎', () => {
    it('应该在 < 10ms 内完成队名对齐', () => {
      const candidates = ['Manchester United', 'Man Utd', 'Man City', 'Liverpool'];
      const result = extractor.alignTeams('Manchester United', candidates);
      
      assert.ok(result.elapsedMs < 10, 
        `对齐耗时 ${result.elapsedMs}ms 应 < 10ms`);
      assert.strictEqual(result.matchedName, 'Manchester United');
      assert.ok(result.confidence >= 70);
    });

    it('应该正确匹配缩写队名', () => {
      const candidates = ['Manchester United', 'Man Utd', 'Man City', 'Liverpool'];
      const result = extractor.alignTeams('Man Utd', candidates);
      
      assert.ok(result.elapsedMs < 10);
      assert.ok(result.success, '对齐应该成功');
      assert.ok(result.confidence >= 70);
    });

    it('应该在无法匹配时返回失败', () => {
      const candidates = ['Real Madrid', 'Barcelona'];
      const result = extractor.alignTeams('Unknown Team', candidates);
      
      assert.strictEqual(result.matchedName, null);
      assert.ok(result.confidence < 70);
    });
  });

  describe('降幅逻辑 - odds_drop 计算', () => {
    it('应该正确计算赔率降幅: 2.0 -> 1.8 = +0.10 (10%)', () => {
      const drop = extractor.calculateOddsDrop(2.0, 1.8);
      assert.strictEqual(drop, 0.1, '降幅应为 0.10 (+10%)');
    });

    it('应该正确计算赔率升幅: 1.8 -> 2.0 = -0.1111 (-11.11%)', () => {
      const drop = extractor.calculateOddsDrop(1.8, 2.0);
      assert.strictEqual(drop, -0.1111, '升幅应为 -0.1111 (-11.11%)');
    });

    it('相同赔率时降幅应为 0', () => {
      const drop = extractor.calculateOddsDrop(2.0, 2.0);
      assert.strictEqual(drop, 0);
    });

    it('赔率 <= 0 时应抛出异常', () => {
      assert.throws(() => extractor.calculateOddsDrop(0, 1.5), /赔率必须大于0/);
      assert.throws(() => extractor.calculateOddsDrop(1.5, 0), /赔率必须大于0/);
      assert.throws(() => extractor.calculateOddsDrop(-1, 1.5), /赔率必须大于0/);
    });
  });

  describe('抽水率计算 - market_margin', () => {
    it('应该正确计算 [2.0, 3.4, 3.6] 的抽水率', () => {
      const odds = [2.0, 3.4, 3.6];
      const margin = extractor.calculateMarketMargin(odds);
      
      // 1/2.0 + 1/3.4 + 1/3.6 = 0.5 + 0.2941 + 0.2778 = 1.0719
      // margin = 1.0719 - 1 = 0.0719
      const expected = 0.0719;
      assert.strictEqual(margin, expected);
    });

    it('公平赔率时抽水率应接近 0', () => {
      // 公平赔率: 1/3 + 1/3 + 1/3 = 1
      const odds = [3.0, 3.0, 3.0];
      const margin = extractor.calculateMarketMargin(odds);
      assert.strictEqual(margin, 0);
    });

    it('数组长度不为 3 时应抛出异常', () => {
      assert.throws(() => extractor.calculateMarketMargin([2.0, 3.0]), /长度为3/);
      assert.throws(() => extractor.calculateMarketMargin([2.0]), /长度为3/);
      assert.throws(() => extractor.calculateMarketMargin([]), /长度为3/);
    });

    it('赔率 <= 0 时应抛出异常', () => {
      assert.throws(() => extractor.calculateMarketMargin([0, 3.0, 3.0]), /赔率必须大于0/);
      assert.throws(() => extractor.calculateMarketMargin([2.0, -1, 3.0]), /赔率必须大于0/);
    });
  });

  describe('完整市场情绪特征提取 (8维度)', () => {
    it('应该返回包含 8 个维度的特征对象', () => {
      const oddsData = {
        openingOdds: [2.0, 3.4, 3.6],
        closingOdds: [1.8, 3.6, 4.0],
        homeTeam: 'Team A',
        awayTeam: 'Team B',
        matchId: 'M001'
      };
      
      const sentiment = extractor.extractMarketSentiment(oddsData);
      
      assert.ok('odds_drop' in sentiment, '应包含 odds_drop');
      assert.ok('market_margin' in sentiment, '应包含 market_margin');
      assert.ok('odds_efficiency_score' in sentiment, '应包含 odds_efficiency_score');
      assert.ok('market_implied_bias' in sentiment, '应包含 market_implied_bias');
      assert.ok('bookie_consensus_index' in sentiment, '应包含 bookie_consensus_index');
      assert.ok('market_volatility' in sentiment, '应包含 market_volatility');
      assert.ok('money_flow_index' in sentiment, '应包含 money_flow_index');
      assert.ok('contrarian_signal' in sentiment, '应包含 contrarian_signal');
    });

    it('应该包含版本和时间戳信息', () => {
      const oddsData = {
        openingOdds: [2.0, 3.4, 3.6],
        closingOdds: [1.8, 3.6, 4.0]
      };
      
      const sentiment = extractor.extractMarketSentiment(oddsData);
      
      assert.strictEqual(sentiment.version, 'V6.0.0');
      assert.ok(sentiment.extracted_at, '应包含 extracted_at 时间戳');
    });

    it('应该使用默认赔率当输入缺失时', () => {
      const oddsData = {};
      const sentiment = extractor.extractMarketSentiment(oddsData);
      
      assert.ok(sentiment.odds_drop !== undefined);
      assert.ok(sentiment.market_margin !== undefined);
    });
  });
});

// 导出供其他模块使用
module.exports = { MarketSentimentExtractor };
