/**
 * TITAN V6.0 SCHEMA-DESIGN 测试套件
 * ================================
 * 验证 market_sentiment 终极 JSON 结构的完整性
 * 
 * @module tests/unit/schema_design_validator
 * @version V6.0-ULTIMATE
 * @date 2026-03-16
 */

'use strict';

const { describe, it, before } = require('node:test');
const assert = require('node:assert');
const {
  validatePurity,
  calculateVolatilityMetrics,
  buildMarketSentiment,
  BOOKMAKER_ID_MAP
} = require('../../src/infrastructure/harvesters/OddsPortalParser');

describe('V6.0 SCHEMA-DESIGN: 纯度校验系统', () => {
  
  describe('validatePurity() - 核心校验逻辑', () => {
    
    it('应通过有效的标准赔率 [2.15, 3.40, 3.60]', () => {
      const odds = [2.15, 3.40, 3.60];
      const result = validatePurity(odds);
      
      assert.strictEqual(result.valid, true, '有效赔率应通过校验');
      assert.strictEqual(result.purity_score, 100, '纯度分数应为100');
      assert.deepStrictEqual(result.normalized_odds, [2.15, 3.40, 3.60]);
      assert.strictEqual(result.errors.length, 0, '不应有错误');
    });
    
    it('应拒绝长度不为3的数组', () => {
      const odds = [2.15, 3.40];
      const result = validatePurity(odds);
      
      assert.strictEqual(result.valid, false, '长度不为3应被拒绝');
      assert.strictEqual(result.purity_score, 0, '纯度分数应为0');
      assert.ok(result.errors.some(e => e.includes('长度')), '应报告长度错误');
    });
    
    it('应拒绝包含1.00的越界值 (低于1.01)', () => {
      const odds = [1.00, 3.40, 3.60];
      const result = validatePurity(odds);
      
      assert.strictEqual(result.valid, false, '1.00应被拒绝');
      assert.ok(result._rejected, '应标记为拒绝');
      assert.ok(result._rejection_reason.includes('越界'), '应报告越界错误');
    });
    
    it('应拒绝包含101.00的越界值 (高于99.99)', () => {
      const odds = [2.15, 101.00, 3.60];
      const result = validatePurity(odds);
      
      assert.strictEqual(result.valid, false, '101.00应被拒绝');
      assert.ok(result.errors.some(e => e.includes('越界')), '应报告越界错误');
    });
    
    it('应拒绝包含非数字值的数组', () => {
      const odds = [2.15, 'invalid', 3.60];
      const result = validatePurity(odds);
      
      assert.strictEqual(result.valid, false, '非数字值应被拒绝');
      assert.ok(result.errors.some(e => e.includes('不是有效数字')), '应报告类型错误');
    });
    
    it('应正确计算部分有效的纯度分数', () => {
      const odds = [2.15, 'invalid', 3.60];
      const result = validatePurity(odds, { strictMode: false });
      
      assert.strictEqual(result.purity_score, 67, '2/3有效应为67分');
    });
    
    it('应接受边界值 1.01 和 99.99', () => {
      const odds1 = [1.01, 50.00, 99.99];
      const result1 = validatePurity(odds1);
      
      assert.strictEqual(result1.valid, true, '边界值1.01-99.99应被接受');
      assert.strictEqual(result1.purity_score, 100);
    });
    
    it('应拒绝 CookieLaw 污染数据 [445.32]', () => {
      const odds = [14.58, 445.32, 1.80];
      const result = validatePurity(odds);
      
      assert.strictEqual(result.valid, false, '445.32应被拒绝');
      assert.ok(result._rejection_reason.includes('99.99'), '应报告上限越界');
    });
  });
  
  describe('calculateVolatilityMetrics() - 波动指数计算', () => {
    
    it('应正确计算简单的波动指数', () => {
      const history = [
        { t: 1000, o: [2.00, 3.00, 4.00] },
        { t: 2000, o: [1.90, 3.10, 4.20] }
      ];
      const result = calculateVolatilityMetrics(history);
      
      assert.ok(result.volatility_index > 0, '应有正波动指数');
      assert.strictEqual(result.total_movement_count, 2);
      assert.ok(result.max_home_movement > 0);
    });
    
    it('单点历史应返回零波动', () => {
      const history = [{ t: 1000, o: [2.00, 3.00, 4.00] }];
      const result = calculateVolatilityMetrics(history);
      
      assert.strictEqual(result.volatility_index, 0, '单点应无波动');
      assert.strictEqual(result.total_movement_count, 1);
    });
    
    it('空历史应返回零值', () => {
      const result = calculateVolatilityMetrics([]);
      
      assert.strictEqual(result.volatility_index, 0);
      assert.strictEqual(result.total_movement_count, 0);
    });
    
    it('应计算最大变动幅度', () => {
      const history = [
        { t: 1000, o: [2.00, 3.00, 4.00] },
        { t: 2000, o: [1.50, 3.50, 5.00] },
        { t: 3000, o: [1.80, 3.20, 4.50] }
      ];
      const result = calculateVolatilityMetrics(history);
      
      assert.strictEqual(result.max_home_movement, 0.50, '主胜最大变动应为0.50');
      assert.strictEqual(result.max_draw_movement, 0.50, '平局最大变动应为0.50');
      assert.strictEqual(result.max_away_movement, 1.00, '客胜最大变动应为1.00');
    });
  });
});

describe('V6.0 SCHEMA-DESIGN: 数据结构构建', () => {
  
  describe('buildMarketSentiment() - 标准结构生成', () => {
    
    it('应生成符合规范的 P0 级数据结构', () => {
      const apiResult = {
        pinnacle: {
          detected: true,
          bookmaker_id: 18,
          opening: [2.15, 3.40, 3.60],
          closing: [1.95, 3.65, 4.20],
          opening_at: 1710576000,
          last_changed_at: 1710662400,
          history: [
            { ts: 1710576000, o: [2.15, 3.40, 3.60] },
            { ts: 1710604800, o: [2.10, 3.45, 3.70] },
            { ts: 1710662400, o: [1.95, 3.65, 4.20] }
          ],
          volatility_index: 2.34,
          _is_premium: true,
          _point_count: 3
        }
      };
      
      const ms = buildMarketSentiment(apiResult, null);
      
      // 验证顶层结构
      assert.strictEqual(ms._schema_version, 'V6.0-ULTIMATE');
      assert.ok(ms._extract_timestamp);
      assert.ok(ms.pinnacle, '应包含pinnacle数据');
      
      // 验证公司结构
      const pin = ms.pinnacle;
      assert.strictEqual(pin.bookmaker_id, 18);
      assert.strictEqual(pin.bookmaker_name, 'Pinnacle');
      assert.strictEqual(pin.tier, 'P0');
      
      // 验证四个维度
      assert.ok(pin.opening, '应有opening');
      assert.ok(pin.opening.o, 'opening应有o字段');
      assert.ok(pin.opening.t, 'opening应有t字段');
      assert.deepStrictEqual(pin.opening.o, [2.15, 3.40, 3.60]);
      
      assert.ok(pin.closing, '应有closing');
      assert.deepStrictEqual(pin.closing.o, [1.95, 3.65, 4.20]);
      
      assert.ok(pin.movement, '应有movement');
      assert.ok(pin.movement.history, 'movement应有history');
      assert.strictEqual(pin.movement.point_count, 3);
      assert.ok(pin.movement.volatility_index >= 0);
      
      assert.ok(pin.metadata, '应有metadata');
      assert.ok(pin.metadata.purity_score >= 0);
      assert.ok(pin.metadata.source_channel);
      assert.ok(pin.metadata.extraction_timestamp);
      assert.ok(['PREMIUM-GOLD', 'STANDARD', 'PARTIAL'].includes(pin.metadata.data_quality));
    });
    
    it('应正确标记 PREMIUM-GOLD 数据 (3+变盘点)', () => {
      const apiResult = {
        bet365: {
          detected: true,
          bookmaker_id: 16,
          opening: [2.10, 3.50, 3.50],
          closing: [1.90, 3.75, 4.10],
          opening_at: 1710576000,
          last_changed_at: 1710662400,
          history: [
            { ts: 1710576000, o: [2.10, 3.50, 3.50] },
            { ts: 1710615600, o: [2.05, 3.55, 3.60] },
            { ts: 1710637200, o: [2.00, 3.60, 3.75] },
            { ts: 1710662400, o: [1.90, 3.75, 4.10] }
          ],
          _is_premium: true,
          _point_count: 4
        }
      };
      
      const ms = buildMarketSentiment(apiResult, null);
      
      assert.strictEqual(ms.bet365.metadata.data_quality, 'PREMIUM-GOLD');
      assert.strictEqual(ms.bet365.metadata.is_complete, true);
      assert.strictEqual(ms._summary.premium_gold_count, 1);
    });
    
    it('DOM回退数据应标记为 PARTIAL', () => {
      const domResult = {
        pinnacleOdds: [1.95, 3.65, 4.20]
      };
      
      const ms = buildMarketSentiment(null, domResult);
      
      assert.ok(ms.pinnacle, '应包含pinnacle数据');
      assert.strictEqual(ms.pinnacle.metadata.data_quality, 'PARTIAL');
      assert.strictEqual(ms.pinnacle.metadata.is_complete, false);
      assert.strictEqual(ms.pinnacle.metadata.source_channel, 'dom_fallback');
    });
    
    it('应生成包含汇总信息的 _summary', () => {
      const apiResult = {
        pinnacle: {
          detected: true,
          bookmaker_id: 18,
          opening: [2.15, 3.40, 3.60],
          closing: [1.95, 3.65, 4.20],
          history: [{ ts: 1000, o: [2.15, 3.40, 3.60] }, { ts: 2000, o: [1.95, 3.65, 4.20] }],
          _is_premium: true
        },
        bet365: {
          detected: true,
          bookmaker_id: 16,
          opening: [2.10, 3.50, 3.50],
          closing: [1.90, 3.75, 4.10],
          history: [{ ts: 1000, o: [2.10, 3.50, 3.50] }],
          _is_premium: false
        }
      };
      
      const ms = buildMarketSentiment(apiResult, null);
      
      assert.ok(ms._summary, '应有_summary');
      assert.strictEqual(ms._summary.total_bookmakers, 2);
      assert.strictEqual(ms._summary.premium_gold_count, 1);
      assert.strictEqual(ms._summary.has_p0_data, true);
      assert.ok(ms._summary.overall_purity >= 0 && ms._summary.overall_purity <= 100);
      assert.ok(['high', 'medium', 'low', 'none'].includes(ms._summary.data_completeness));
    });
    
    it('污染数据应被拒绝入库', () => {
      const apiResult = {
        pinnacle: {
          detected: true,
          bookmaker_id: 18,
          opening: [14.58, 445.32, 1.80], // CookieLaw污染
          closing: [1.95, 3.65, 4.20],
          history: []
        }
      };
      
      const ms = buildMarketSentiment(apiResult, null);
      
      // opening应为null因为校验失败，但closing应该存在
      assert.ok(ms.pinnacle.closing, 'closing应存在');
      // opening被污染，应使用closing作为保底
      assert.deepStrictEqual(ms.pinnacle.opening.o, ms.pinnacle.closing.o);
    });
    
    it('history中的每个点应有正确的type标记', () => {
      const apiResult = {
        pinnacle: {
          detected: true,
          bookmaker_id: 18,
          opening: [2.15, 3.40, 3.60],
          closing: [1.95, 3.65, 4.20],
          history: [
            { ts: 1710576000, o: [2.15, 3.40, 3.60] },
            { ts: 1710604800, o: [2.10, 3.45, 3.70] },
            { ts: 1710626400, o: [2.05, 3.50, 3.80] },
            { ts: 1710662400, o: [1.95, 3.65, 4.20] }
          ],
          _is_premium: true
        }
      };
      
      const ms = buildMarketSentiment(apiResult, null);
      const history = ms.pinnacle.movement.history;
      
      assert.strictEqual(history[0].type, 'OPEN', '第一个点应为OPEN');
      assert.strictEqual(history[1].type, 'MOVE', '中间点应为MOVE');
      assert.strictEqual(history[2].type, 'MOVE', '中间点应为MOVE');
      assert.strictEqual(history[3].type, 'CLOSE', '最后一个点应为CLOSE');
    });
  });
});

describe('V6.0 SCHEMA-DESIGN: 博彩公司ID映射', () => {
  
  it('应包含所有P0级公司', () => {
    assert.ok(BOOKMAKER_ID_MAP.METADATA.pinnacle, '应有Pinnacle');
    assert.ok(BOOKMAKER_ID_MAP.METADATA.bet365, '应有Bet365');
    assert.strictEqual(BOOKMAKER_ID_MAP.METADATA.pinnacle.tier, 'P0');
    assert.strictEqual(BOOKMAKER_ID_MAP.METADATA.bet365.tier, 'P0');
  });
  
  it('应包含所有P1级公司', () => {
    assert.ok(BOOKMAKER_ID_MAP.METADATA.bwin, '应有Bwin');
    assert.ok(BOOKMAKER_ID_MAP.METADATA.william_hill, '应有William Hill');
    assert.ok(BOOKMAKER_ID_MAP.METADATA.intertops, '应有Interwetten');
    assert.strictEqual(BOOKMAKER_ID_MAP.METADATA.bwin.tier, 'P1');
  });
  
  it('P0公司应有正确的ID映射', () => {
    assert.ok(BOOKMAKER_ID_MAP.PINNACLE.includes(18));
    assert.ok(BOOKMAKER_ID_MAP.PINNACLE.includes(27));
    assert.ok(BOOKMAKER_ID_MAP.BET365.includes(16));
  });
  
  it('P1公司应有正确的ID映射', () => {
    assert.ok(BOOKMAKER_ID_MAP.BWIN.includes(1));
    assert.ok(BOOKMAKER_ID_MAP.WILLIAM_HILL.includes(2));
    assert.ok(BOOKMAKER_ID_MAP.INTERTOPS.includes(3));
  });
});

// 运行测试报告
console.log('\n╔══════════════════════════════════════════════════════════════════════════════╗');
console.log('║     🔱 TITAN V6.0 SCHEMA-DESIGN 测试套件                                     ║');
console.log('║     验证 market_sentiment 终极 JSON 结构完整性                              ║');
console.log('╚══════════════════════════════════════════════════════════════════════════════╝\n');