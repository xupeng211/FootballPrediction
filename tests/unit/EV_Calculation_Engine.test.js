/**
 * TITAN V5.5 Realtime Valuation - EV 计算引擎 TDD 测试
 * 任务: TITAN-V5.5-REALTIME-VALUATION
 * 
 * 核心公式: EV = (Model_Probability × Market_Odds) - 1
 * 分级标签:
 *   - [ELITE VALUE]: EV > 0.15 (15% 利润溢价)
 *   - [FAIR PRICE]: 0 < EV <= 0.15
 *   - [NEGATIVE EV]: EV < 0 (不建议入场)
 */

const assert = require('node:assert');
const { describe, it } = require('node:test');

// ============================================================================
// EV 计算引擎 (待实现)
// ============================================================================

class EVCalculationEngine {
  /**
   * 计算期望值 (Expected Value)
   * @param {number} modelProbability - 模型预测胜率 (0-1)
   * @param {number} marketOdds - 市场赔率 (decimal odds)
   * @returns {object} EV 计算结果
   */
  static calculate(modelProbability, marketOdds) {
    // 参数校验
    if (marketOdds < 1.0) {
      throw new Error('赔率必须 >= 1.0');
    }
    if (modelProbability <= 0 || modelProbability > 1) {
      throw new Error('胜率必须在 (0, 1] 范围内');
    }

    // 核心公式: EV = (P × Odds) - 1
    const ev = (modelProbability * marketOdds) - 1;
    
    // 分级标签
    let grade;
    if (ev > 0.15) {
      grade = 'ELITE_VALUE';
    } else if (ev > 0) {
      grade = 'FAIR_PRICE';
    } else {
      grade = 'NEGATIVE_EV';
    }

    return {
      ev: Number(ev.toFixed(3)),
      evPercentage: Number((ev * 100).toFixed(1)),
      grade,
      modelProbability: Number(modelProbability.toFixed(4)),
      marketOdds,
      recommendation: this._getRecommendation(grade)
    };
  }

  /**
   * 批量计算并排序
   * @param {Array} matches - 比赛数组 [{home, away, probability, odds}]
   * @returns {Array} 按 EV 降序排列的结果
   */
  static calculateBatch(matches) {
    return matches
      .map(m => ({
        ...m,
        ...this.calculate(m.probability, m.odds)
      }))
      .sort((a, b) => b.ev - a.ev);
  }

  static _getRecommendation(grade) {
    const recommendations = {
      'ELITE_VALUE': '🔥 强烈推荐 - 重大价值洼地',
      'FAIR_PRICE': '✅ 合理价格 - 可考虑入场',
      'NEGATIVE_EV': '❌ 不建议 - 价格高于概率'
    };
    return recommendations[grade];
  }
}

// ============================================================================
// TDD 测试套件
// ============================================================================

describe('EV 计算引擎 - TITAN V5.5 Realtime Valuation', () => {
  
  describe('核心公式计算', () => {
    it('应该正确计算标准案例: 72.95% × 1.85 - 1 = 0.35', () => {
      const result = EVCalculationEngine.calculate(0.7295, 1.85);
      assert.strictEqual(result.ev, 0.35, 'EV 必须精确等于 0.35');
      assert.ok(result.evPercentage >= 34.9, 'EV 百分比应 >= +34.9%');
    });

    it('应该正确计算高胜率高赔率案例', () => {
      const result = EVCalculationEngine.calculate(0.65, 2.10);
      assert.strictEqual(result.ev, 0.365, 'EV 应为 0.365');
      assert.strictEqual(result.grade, 'ELITE_VALUE', '应标记为 ELITE_VALUE');
    });

    it('应该正确计算边缘价值案例', () => {
      const result = EVCalculationEngine.calculate(0.55, 1.90);
      assert.strictEqual(result.ev, 0.045, 'EV 应为 0.045');
      assert.strictEqual(result.grade, 'FAIR_PRICE', '应标记为 FAIR_PRICE');
    });

    it('应该正确识别负 EV 案例', () => {
      const result = EVCalculationEngine.calculate(0.45, 2.0);
      assert.strictEqual(result.ev, -0.10, 'EV 应为 -0.10');
      assert.strictEqual(result.grade, 'NEGATIVE_EV', '应标记为 NEGATIVE_EV');
    });
  });

  describe('分级标签系统', () => {
    it('[ELITE_VALUE] EV > 0.15 应标记为精英价值', () => {
      const result = EVCalculationEngine.calculate(0.70, 1.70);
      assert.strictEqual(result.grade, 'ELITE_VALUE');
      assert.ok(result.ev > 0.15);
      assert.ok(result.recommendation.includes('强烈推荐'));
    });

    it('[FAIR_PRICE] 0 < EV <= 0.15 应标记为合理价格', () => {
      const result = EVCalculationEngine.calculate(0.60, 1.80);
      assert.strictEqual(result.grade, 'FAIR_PRICE');
      assert.ok(result.ev > 0 && result.ev <= 0.15);
      assert.ok(result.recommendation.includes('合理价格'));
    });

    it('[NEGATIVE_EV] EV < 0 应标记为负期望', () => {
      const result = EVCalculationEngine.calculate(0.40, 2.20);
      assert.strictEqual(result.grade, 'NEGATIVE_EV');
      assert.ok(result.ev < 0);
      assert.ok(result.recommendation.includes('不建议'));
    });
  });

  describe('边界测试与异常处理', () => {
    it('赔率 < 1.0 时应抛出异常', () => {
      assert.throws(
        () => EVCalculationEngine.calculate(0.70, 0.95),
        /赔率必须 >= 1.0/
      );
    });

    it('赔率 = 1.0 时应正常计算 (无利润空间)', () => {
      const result = EVCalculationEngine.calculate(0.70, 1.0);
      assert.strictEqual(result.ev, -0.30, 'EV 应为 -0.30');
    });

    it('胜率 = 0 时应抛出异常', () => {
      assert.throws(
        () => EVCalculationEngine.calculate(0, 2.0),
        /胜率必须在/
      );
    });

    it('胜率 < 0 时应抛出异常', () => {
      assert.throws(
        () => EVCalculationEngine.calculate(-0.10, 2.0),
        /胜率必须在/
      );
    });

    it('胜率 > 1 时应抛出异常', () => {
      assert.throws(
        () => EVCalculationEngine.calculate(1.10, 2.0),
        /胜率必须在/
      );
    });
  });

  describe('批量计算与排序', () => {
    it('应该按 EV 降序排列多场比赛', () => {
      const matches = [
        { home: 'Team A', away: 'Team B', probability: 0.55, odds: 1.90 },
        { home: 'Team C', away: 'Team D', probability: 0.70, odds: 1.85 },
        { home: 'Team E', away: 'Team F', probability: 0.45, odds: 2.10 },
      ];
      
      const results = EVCalculationEngine.calculateBatch(matches);
      
      // 验证按 EV 降序排列
      assert.ok(results[0].ev > results[1].ev, '第一场 EV 应高于第二场');
      assert.ok(results[1].ev > results[2].ev, '第二场 EV 应高于第三场');
      
      // 验证最高 EV 是 Team C vs Team D
      assert.strictEqual(results[0].home, 'Team C');
      assert.strictEqual(results[0].ev, 0.295);
    });

    it('应该识别 Top 3 精英信号', () => {
      const matches = [
        { home: 'A', away: 'B', probability: 0.75, odds: 1.80 }, // EV = 0.35
        { home: 'C', away: 'D', probability: 0.68, odds: 1.75 }, // EV = 0.19
        { home: 'E', away: 'F', probability: 0.72, odds: 1.60 }, // EV = 0.152
        { home: 'G', away: 'H', probability: 0.55, odds: 1.90 }, // EV = 0.045
        { home: 'I', away: 'J', probability: 0.40, odds: 2.20 }, // EV = -0.12
      ];
      
      const results = EVCalculationEngine.calculateBatch(matches);
      const eliteSignals = results.filter(r => r.grade === 'ELITE_VALUE');
      
      assert.strictEqual(eliteSignals.length, 3, '应有3个 ELITE_VALUE 信号');
      assert.strictEqual(eliteSignals[0].home, 'A');
      assert.strictEqual(eliteSignals[1].home, 'C');
      assert.strictEqual(eliteSignals[2].home, 'E');
    });
  });

  describe('实时估值链路与数据完整性', () => {
    it('应该包含完整的返回字段', () => {
      const result = EVCalculationEngine.calculate(0.65, 2.0);
      
      assert.ok('ev' in result, '应包含 ev 字段');
      assert.ok('evPercentage' in result, '应包含 evPercentage 字段');
      assert.ok('grade' in result, '应包含 grade 字段');
      assert.ok('modelProbability' in result, '应包含 modelProbability 字段');
      assert.ok('marketOdds' in result, '应包含 marketOdds 字段');
      assert.ok('recommendation' in result, '应包含 recommendation 字段');
    });

    it('EV 百分比应该正确转换为百分数', () => {
      const result = EVCalculationEngine.calculate(0.7295, 1.85);
      // 允许 35 或 34.9 的舍入差异
      assert.ok(result.evPercentage === 34.9 || result.evPercentage === 35, 
                `EV 百分比应为 34.9 或 35，实际是 ${result.evPercentage}`);
      assert.ok(result.grade === 'ELITE_VALUE', '应为 ELITE_VALUE');
    });
  });
});

// 导出供其他模块使用
module.exports = { EVCalculationEngine };
