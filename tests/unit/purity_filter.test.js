/**
 * TITAN V6.0 PURITY FILTER - 信号提纯与精度校准测试
 * ==================================================
 * TDD Red Phase: 验证域名白名单和数值围栏逻辑
 * 
 * @module tests/unit/purity_filter
 * @version V6.0-PURITY-TDD
 * @date 2026-03-16
 */

'use strict';

const { test, describe } = require('node:test');
const assert = require('node:assert');

// 信号提纯过滤器 (待测试实现)
class PurityFilter {
  constructor() {
    // 域名白名单 - 只允许OddsPortal核心API
    this.ALLOWED_DOMAINS = [
      'oddsportal.com',
      'oddsportal.com/ajax-user-data/',
      'oddsportal.com/ajax/',
      'oddsportal.com/feed/'
    ];
    
    // 第三方噪音域名黑名单
    this.BLOCKED_DOMAINS = [
      'cookielaw.org',
      'cdn.cookielaw.org',
      'onetrust.com',
      'googletagmanager.com',
      'google-analytics.com',
      'facebook.com',
      'doubleclick.net'
    ];
    
    // 赔率数值围栏
    this.ODDS_MIN = 1.01;
    this.ODDS_MAX = 99.99;
    
    // 统计
    this.stats = {
      totalChecked: 0,
      passed: 0,
      blockedByDomain: 0,
      blockedByValue: 0,
      goldenStreams: 0
    };
  }

  /**
   * 验证URL是否在白名单中
   * @param {string} url 
   * @returns {boolean}
   */
  isAllowedDomain(url) {
    if (!url || typeof url !== 'string') return false;
    
    // 首先检查是否在黑名单
    for (const blocked of this.BLOCKED_DOMAINS) {
      if (url.includes(blocked)) return false;
    }
    
    // 然后检查是否在白名单
    for (const allowed of this.ALLOWED_DOMAINS) {
      if (url.includes(allowed)) return true;
    }
    
    // 默认拒绝不在白名单的URL
    return false;
  }

  /**
   * 验证赔率数值是否在有效围栏内
   * @param {Array<number>} odds - 赔率数组 [home, draw, away]
   * @returns {boolean}
   */
  isValidOddsRange(odds) {
    if (!Array.isArray(odds) || odds.length < 3) return false;
    
    const firstThree = odds.slice(0, 3);
    return firstThree.every(n => {
      const num = parseFloat(n);
      return !isNaN(num) && num >= this.ODDS_MIN && num <= this.ODDS_MAX;
    });
  }

  /**
   * 从文本中提取赔率数组
   * @param {string} text 
   * @returns {Array<number>|null}
   */
  extractOddsFromText(text) {
    if (!text || typeof text !== 'string') return null;
    
    // 改进的正则: 匹配三个连续的浮点数
    const pattern = /(\d+\.\d{2})[^\d.]{0,20}(\d+\.\d{2})[^\d.]{0,20}(\d+\.\d{2})/;
    const match = text.match(pattern);
    
    if (match) {
      return [
        parseFloat(match[1]),
        parseFloat(match[2]),
        parseFloat(match[3])
      ];
    }
    
    return null;
  }

  /**
   * 主过滤函数
   * @param {Object} stream - 数据流对象 { url, text, channel }
   * @returns {Object} { isGolden: boolean, reason: string, odds: Array|null }
   */
  filter(stream) {
    this.stats.totalChecked++;
    
    // Step 1: 域名白名单检查
    if (!this.isAllowedDomain(stream.url)) {
      this.stats.blockedByDomain++;
      return { isGolden: false, reason: 'BLOCKED_DOMAIN', odds: null };
    }
    
    // Step 2: 提取赔率
    const odds = this.extractOddsFromText(stream.text);
    if (!odds) {
      return { isGolden: false, reason: 'NO_ODDS_PATTERN', odds: null };
    }
    
    // Step 3: 数值围栏检查
    if (!this.isValidOddsRange(odds)) {
      this.stats.blockedByValue++;
      return { isGolden: false, reason: 'INVALID_ODDS_RANGE', odds };
    }
    
    // 通过所有检查 - GOLDEN STREAM
    this.stats.passed++;
    this.stats.goldenStreams++;
    return { isGolden: true, reason: 'PASSED', odds };
  }

  /**
   * 计算纯度分数
   * @returns {number} 0-100
   */
  getPurityScore() {
    if (this.stats.totalChecked === 0) return 100;
    
    const errorRate = (this.stats.blockedByDomain + this.stats.blockedByValue) / this.stats.totalChecked;
    return Math.max(0, Math.round(100 - (errorRate * 100)));
  }

  reset() {
    this.stats = {
      totalChecked: 0,
      passed: 0,
      blockedByDomain: 0,
      blockedByValue: 0,
      goldenStreams: 0
    };
  }
}

// ============================================================================
// TDD TEST SUITE
// ============================================================================

describe('TITAN V6.0 PURITY FILTER - 信号提纯测试', () => {
  let filter;

  test('Setup: 初始化过滤器', () => {
    filter = new PurityFilter();
    assert.ok(filter, '过滤器应成功创建');
    assert.strictEqual(filter.ODDS_MIN, 1.01, '最小赔率应为1.01');
    assert.strictEqual(filter.ODDS_MAX, 99.99, '最大赔率应为99.99');
  });

  // ============================================================================
  // 场景 A: 真金数据 (必须 PASS)
  // ============================================================================
  describe('场景 A: 真金数据 (必须 PASS)', () => {
    test('A1: 标准赔率 [1.50, 3.90, 6.50] 来自核心API', () => {
      const stream = {
        url: 'https://www.oddsportal.com/ajax-user-data/e/8EamNN8b/1/',
        text: '{"t":1710594000,"o":[1.50,3.90,6.50]}',
        channel: 'fetch'
      };
      
      const result = filter.filter(stream);
      
      assert.strictEqual(result.isGolden, true, '应为GOLDEN STREAM');
      assert.strictEqual(result.reason, 'PASSED', '通过原因应为PASSED');
      assert.deepStrictEqual(result.odds, [1.50, 3.90, 6.50], '赔率应匹配');
    });

    test('A2: 高赔率 [15.00, 8.50, 1.25] 来自ajax接口', () => {
      const stream = {
        url: 'https://www.oddsportal.com/ajax/odds/12345',
        text: '{"odds":[15.00,8.50,1.25]}',
        channel: 'xhr'
      };
      
      const result = filter.filter(stream);
      
      assert.strictEqual(result.isGolden, true, '应为GOLDEN STREAM');
      assert.strictEqual(filter.isValidOddsRange(result.odds), true, '赔率应在有效范围内');
    });

    test('A3: 边界值 [1.01, 50.00, 99.99]', () => {
      const stream = {
        url: 'https://oddsportal.com/feed/match-odds',
        text: '[1.01, 50.00, 99.99]',
        channel: 'ws'
      };
      
      const result = filter.filter(stream);
      
      assert.strictEqual(result.isGolden, true, '边界值应通过');
      assert.deepStrictEqual(result.odds, [1.01, 50.00, 99.99]);
    });
  });

  // ============================================================================
  // 场景 B: 泥沙数据 (必须 FAIL)
  // ============================================================================
  describe('场景 B: 泥沙数据 (必须 FAIL)', () => {
    test('B1: CookieLaw数据 [14.58, 445.32, 1.80] 必须被拦截', () => {
      const stream = {
        url: 'https://cdn.cookielaw.org/consent/xxx/data.json',
        text: '{"values":[14.58,445.32,1.80]}',
        channel: 'fetch'
      };
      
      const result = filter.filter(stream);
      
      assert.strictEqual(result.isGolden, false, '应为非GOLDEN');
      assert.strictEqual(result.reason, 'BLOCKED_DOMAIN', '应因域名被拦截');
    });

    test('B2: OneTrust埋点数据必须被拦截', () => {
      const stream = {
        url: 'https://geolocation.onetrust.com/',
        text: '{"lat":51.50,"lon":-0.12}',
        channel: 'xhr'
      };
      
      const result = filter.filter(stream);
      
      assert.strictEqual(result.isGolden, false);
      assert.strictEqual(result.reason, 'BLOCKED_DOMAIN');
    });

    test('B3: Google Analytics必须被拦截', () => {
      const stream = {
        url: 'https://www.google-analytics.com/collect',
        text: 'v=1&tid=UA-12345&cid=abc',
        channel: 'xhr'
      };
      
      const result = filter.filter(stream);
      
      assert.strictEqual(result.isGolden, false);
      assert.strictEqual(result.reason, 'BLOCKED_DOMAIN');
    });

    test('B4: 虽然数值有效但域名不在白名单', () => {
      const stream = {
        url: 'https://example.com/api/data',
        text: '{"o":[2.50,3.40,2.80]}',
        channel: 'fetch'
      };
      
      const result = filter.filter(stream);
      
      assert.strictEqual(result.isGolden, false);
      assert.strictEqual(result.reason, 'BLOCKED_DOMAIN');
    });
  });

  // ============================================================================
  // 场景 C: 边界值测试 (数值围栏)
  // ============================================================================
  describe('场景 C: 边界值测试 (数值围栏)', () => {
    test('C1: [1.00, 50.00, 2.50] - 低于最小值必须FAIL', () => {
      const stream = {
        url: 'https://oddsportal.com/ajax/odds',
        text: '[1.00, 50.00, 2.50]',
        channel: 'fetch'
      };
      
      const result = filter.filter(stream);
      
      assert.strictEqual(result.isGolden, false, '应因数值越界被拦截');
      assert.strictEqual(result.reason, 'INVALID_ODDS_RANGE');
    });

    test('C2: [1.01, 101.00, 2.50] - 高于最大值必须FAIL', () => {
      const stream = {
        url: 'https://oddsportal.com/ajax/odds',
        text: '[1.01, 101.00, 2.50]',
        channel: 'fetch'
      };
      
      const result = filter.filter(stream);
      
      assert.strictEqual(result.isGolden, false);
      assert.strictEqual(result.reason, 'INVALID_ODDS_RANGE');
    });

    test('C3: [0.50, 3.00, 5.00] - 包含小于1的值必须FAIL', () => {
      const stream = {
        url: 'https://oddsportal.com/ajax/odds',
        text: '[0.50, 3.00, 5.00]',
        channel: 'fetch'
      };
      
      const result = filter.filter(stream);
      
      assert.strictEqual(result.isGolden, false);
      assert.strictEqual(result.reason, 'INVALID_ODDS_RANGE');
    });

    test('C4: [500.00, 3.00, 5.00] - 包含过大值必须FAIL', () => {
      const stream = {
        url: 'https://oddsportal.com/ajax/odds',
        text: '[500.00, 3.00, 5.00]',
        channel: 'fetch'
      };
      
      const result = filter.filter(stream);
      
      assert.strictEqual(result.isGolden, false);
      assert.strictEqual(result.reason, 'INVALID_ODDS_RANGE');
    });
  });

  // ============================================================================
  // 场景 D: 纯度分数计算
  // ============================================================================
  describe('场景 D: 纯度分数计算', () => {
    test('D1: 100%纯度 - 无错误尝试', () => {
      filter.reset();
      
      // 5个有效数据
      for (let i = 0; i < 5; i++) {
        filter.filter({
          url: 'https://oddsportal.com/ajax/odds',
          text: '[1.50, 3.90, 6.50]'
        });
      }
      
      assert.strictEqual(filter.getPurityScore(), 100, '应返回100分');
    });

    test('D2: 计算purity_score - 有错误尝试', () => {
      filter.reset();
      
      // 5个有效 + 5个无效 = 50%错误率 = 50分
      for (let i = 0; i < 5; i++) {
        filter.filter({ url: 'https://oddsportal.com/ajax/odds', text: '[1.50, 3.90, 6.50]' });
      }
      for (let i = 0; i < 5; i++) {
        filter.filter({ url: 'https://cdn.cookielaw.org/data', text: '[14.58, 445.32, 1.80]' });
      }
      
      const score = filter.getPurityScore();
      assert.strictEqual(score, 50, '应返回50分 (50%错误率)');
    });

    test('D3: purity_score最低为0', () => {
      filter.reset();
      
      // 10个全无效
      for (let i = 0; i < 10; i++) {
        filter.filter({ url: 'https://example.com', text: 'invalid' });
      }
      
      assert.strictEqual(filter.getPurityScore(), 0, '应返回0分');
    });
  });

  // ============================================================================
  // 场景 E: 统计信息验证
  // ============================================================================
  describe('场景 E: 统计信息验证', () => {
    test('E1: 正确统计各类拦截', () => {
      filter.reset();
      
      // 域名拦截
      filter.filter({ url: 'https://cdn.cookielaw.org/data', text: '[1.50, 3.90, 6.50]' });
      
      // 数值拦截
      filter.filter({ url: 'https://oddsportal.com/ajax/odds', text: '[500.00, 3.00, 5.00]' });
      
      // 成功
      filter.filter({ url: 'https://oddsportal.com/ajax/odds', text: '[1.50, 3.90, 6.50]' });
      
      assert.strictEqual(filter.stats.totalChecked, 3, '应检查3次');
      assert.strictEqual(filter.stats.blockedByDomain, 1, '应拦截1个域名');
      assert.strictEqual(filter.stats.blockedByValue, 1, '应拦截1个数值');
      assert.strictEqual(filter.stats.goldenStreams, 1, '应有1个Golden Stream');
    });
  });
});

// ============================================================================
// TEST SUMMARY
// ============================================================================

console.log('\n╔══════════════════════════════════════════════════════════════════════════════╗');
console.log('║     🔬 TITAN V6.0 PURITY FILTER - TDD 精度校准测试                             ║');
console.log('║     宁可漏掉，绝不抓错                                                         ║');
console.log('╚══════════════════════════════════════════════════════════════════════════════╝\n');
console.log('📋 测试场景:');
console.log('   A. 真金数据 - [1.50, 3.90, 6.50] 必须 PASS');
console.log('   B. 泥沙数据 - CookieLaw等噪音必须 FAIL');
console.log('   C. 边界值   - [1.00, 101.00] 等越界值必须 FAIL');
console.log('   D. 纯度分数 - purity_score 计算验证');
console.log('   E. 统计信息 - 拦截分类统计');
console.log('\n✅ 运行: npm test -- tests/unit/purity_filter.test.js\n');
