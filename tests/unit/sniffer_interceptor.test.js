/**
 * TITAN V6.0 SNIFFER INTERCEPTOR - TDD Test Suite
 * ================================================
 * 测试驱动开发：验证内存级JSON拦截器
 * 
 * Red Phase: 编写测试，期望Sniffer能100%捕获解析后的明文数据
 * 
 * @module tests/unit/sniffer_interceptor
 * @version V6.0-TDD
 * @date 2026-03-16
 */

'use strict';

const assert = require('assert');
const { describe, it, beforeEach } = require('node:test');

// 模拟OddsPortal解密后的明文JSON结构
const MOCK_DECRYPTED_DATA = {
  "userData": {
    "oddsformat": 1,
    "myBookmakers": [16, 27, 44, 500],
    "oddsformatTitle": "Decimal Odds"
  },
  "bookiehash": "X134283264X24576X0X0X0X0X0X0X0X0X0X0X0",
  "oddsdata": {
    "bet365": {
      "id": 16,
      "name": "Bet365",
      "history": [
        { "t": 1710594000, "o": [1.55, 4.00, 6.00] },
        { "t": 1710604800, "o": [1.52, 3.95, 6.20] },
        { "t": 1710615600, "o": [1.50, 3.90, 6.50] }
      ]
    },
    "pinnacle": {
      "id": 27,
      "name": "Pinnacle",
      "history": [
        { "t": 1710594000, "o": [1.58, 4.05, 5.90] },
        { "t": 1710604800, "o": [1.54, 3.98, 6.15] }
      ]
    }
  },
  "timestamp": 1710637200
};

// 模拟非目标数据（应该被忽略）
const MOCK_NON_TARGET_DATA = {
  "someOtherData": "should be ignored",
  "random": [1, 2, 3]
};

/**
 * 模拟浏览器环境的JSON.parse拦截器
 */
class MockJsonSniffer {
  constructor() {
    this.capturedData = [];
    this.originalParse = null;
    this.isInjected = false;
    this._isParsing = false; // 防止递归标志
  }

  /**
   * 注入Sniffer钩子
   */
  inject() {
    if (this.isInjected) return;
    
    const self = this;
    this.originalParse = JSON.parse;
    
    // 模拟浏览器全局JSON.parse重写
    JSON.parse = function(text, reviver) {
      // 防止递归
      if (self._isParsing) {
        return self.originalParse.call(JSON, text, reviver);
      }
      
      self._isParsing = true;
      let parsed;
      try {
        parsed = self.originalParse.call(JSON, text, reviver);
      } finally {
        self._isParsing = false;
      }
      
      // 特征识别：检查是否包含目标Key
      if (self.isTargetData(parsed)) {
        // 克隆数据并捕获
        let cloned;
        try {
          cloned = self.originalParse.call(JSON, JSON.stringify(parsed));
        } catch (e) {
          cloned = parsed;
        }
        
        self.capturedData.push({
          timestamp: Date.now(),
          data: cloned,
          keys: Object.keys(parsed)
        });
      }
      
      return parsed;
    };
    
    this.isInjected = true;
  }

  /**
   * 恢复原始JSON.parse
   */
  restore() {
    JSON.parse = this.originalParse;
    this.isInjected = false;
  }

  /**
   * 特征识别：判断是否为赔率数据
   */
  isTargetData(obj) {
    if (!obj || typeof obj !== 'object') return false;
    
    const targetKeys = ['userData', 'bookiehash', 'oddsdata', 'myBookmakers'];
    const objKeys = Object.keys(obj);
    
    return targetKeys.some(key => objKeys.includes(key));
  }

  /**
   * 获取捕获的数据
   */
  getCapturedData() {
    return this.capturedData;
  }

  /**
   * 清空捕获数据
   */
  clear() {
    this.capturedData = [];
  }
}

describe('TITAN V6.0 JSON SNIFFER INTERCEPTOR', () => {
  let sniffer;

  beforeEach(() => {
    sniffer = new MockJsonSniffer();
    sniffer.clear();
  });

  describe('RED PHASE: 基础功能测试', () => {
    it('应该成功注入Sniffer钩子', () => {
      sniffer.inject();
      assert.strictEqual(sniffer.isInjected, true, 'Sniffer应该成功注入');
      sniffer.restore();
    });

    it('应该恢复原始JSON.parse', () => {
      sniffer.inject();
      sniffer.restore();
      assert.strictEqual(sniffer.isInjected, false, 'Sniffer应该成功恢复');
    });
  });

  describe('RED PHASE: 数据捕获测试', () => {
    it('应该100%捕获包含userData的JSON', () => {
      sniffer.inject();
      
      // 模拟解析目标数据
      const data = JSON.stringify(MOCK_DECRYPTED_DATA);
      JSON.parse(data);
      
      const captured = sniffer.getCapturedData();
      assert.strictEqual(captured.length, 1, '应该捕获1条数据');
      assert.deepStrictEqual(captured[0].data, MOCK_DECRYPTED_DATA, '数据应该完全匹配');
      
      sniffer.restore();
    });

    it('应该100%捕获包含bookiehash的JSON', () => {
      sniffer.inject();
      
      const testData = { bookiehash: "X123", odds: [1.5, 3.5, 6.5] };
      JSON.stringify(testData);
      JSON.parse(JSON.stringify(testData));
      
      const captured = sniffer.getCapturedData();
      assert.strictEqual(captured.length, 1, '应该捕获包含bookiehash的数据');
      
      sniffer.restore();
    });

    it('应该100%捕获包含oddsdata的JSON', () => {
      sniffer.inject();
      
      const testData = { oddsdata: { bet365: { o: [1.5, 4.0, 6.5] } } };
      JSON.parse(JSON.stringify(testData));
      
      const captured = sniffer.getCapturedData();
      assert.strictEqual(captured.length, 1, '应该捕获包含oddsdata的数据');
      
      sniffer.restore();
    });

    it('应该忽略不包含特征Key的非目标数据', () => {
      sniffer.inject();
      
      JSON.parse(JSON.stringify(MOCK_NON_TARGET_DATA));
      
      const captured = sniffer.getCapturedData();
      assert.strictEqual(captured.length, 0, '不应该捕获非目标数据');
      
      sniffer.restore();
    });
  });

  describe('RED PHASE: Bet365赔率识别测试', () => {
    it('应该准确识别Bet365赔率数组', () => {
      sniffer.inject();
      
      JSON.parse(JSON.stringify(MOCK_DECRYPTED_DATA));
      
      const captured = sniffer.getCapturedData();
      assert.strictEqual(captured.length, 1);
      
      const data = captured[0].data;
      assert.ok(data.oddsdata, '应该包含oddsdata字段');
      assert.ok(data.oddsdata.bet365, '应该包含bet365字段');
      assert.ok(Array.isArray(data.oddsdata.bet365.history), 'history应该是数组');
      assert.strictEqual(data.oddsdata.bet365.history.length, 3, '应该有3个历史节点');
      
      // 验证赔率数值
      const firstNode = data.oddsdata.bet365.history[0];
      assert.ok(Array.isArray(firstNode.o), '赔率应该是数组');
      assert.strictEqual(firstNode.o.length, 3, '应该有3个赔率值');
      assert.strictEqual(firstNode.o[0], 1.55, '主胜赔率应该是1.55');
      
      sniffer.restore();
    });

    it('应该捕获完整变盘历史', () => {
      sniffer.inject();
      
      JSON.parse(JSON.stringify(MOCK_DECRYPTED_DATA));
      
      const captured = sniffer.getCapturedData();
      const bet365History = captured[0].data.oddsdata.bet365.history;
      
      // 验证时间戳连续性
      for (let i = 1; i < bet365History.length; i++) {
        assert.ok(
          bet365History[i].t > bet365History[i-1].t,
          `时间戳应该递增: ${bet365History[i-1].t} -> ${bet365History[i].t}`
        );
      }
      
      sniffer.restore();
    });

    it('应该识别赔率字段为o而不是v', () => {
      sniffer.inject();
      
      JSON.parse(JSON.stringify(MOCK_DECRYPTED_DATA));
      
      const captured = sniffer.getCapturedData();
      const firstNode = captured[0].data.oddsdata.bet365.history[0];
      
      assert.ok(firstNode.hasOwnProperty('o'), '应该使用o字段存储赔率');
      assert.ok(!firstNode.hasOwnProperty('v'), '不应该使用v字段');
      
      sniffer.restore();
    });
  });

  describe('RED PHASE: 数据完整性测试', () => {
    it('应该克隆数据而不是引用原始对象', () => {
      sniffer.inject();
      
      const original = JSON.parse(JSON.stringify(MOCK_DECRYPTED_DATA));
      const captured = sniffer.getCapturedData()[0].data;
      
      // 修改原始数据
      original.oddsdata.bet365.history[0].o[0] = 999;
      
      // 验证捕获的数据未被修改
      assert.strictEqual(captured.oddsdata.bet365.history[0].o[0], 1.55, '数据应该被克隆');
      
      sniffer.restore();
    });

    it('应该记录捕获时间戳', () => {
      sniffer.inject();
      
      const before = Date.now();
      JSON.parse(JSON.stringify(MOCK_DECRYPTED_DATA));
      const after = Date.now();
      
      const captured = sniffer.getCapturedData();
      assert.ok(captured[0].timestamp >= before, '时间戳应该>=before');
      assert.ok(captured[0].timestamp <= after, '时间戳应该<=after');
      
      sniffer.restore();
    });
  });
});

// 测试报告输出
console.log('\n╔══════════════════════════════════════════════════════════════════════════════╗');
console.log('║     TITAN V6.0 JSON SNIFFER - TDD TEST SUITE                                 ║');
console.log('╚══════════════════════════════════════════════════════════════════════════════╝\n');

// 如果直接运行此文件，显示测试完成信息
if (require.main === module) {
  console.log('📋 测试场景:');
  console.log('   1. 注入Sniffer钩子');
  console.log('   2. 解析包含userData/bookiehash/oddsdata的JSON');
  console.log('   3. 验证100%捕获Bet365赔率数组');
  console.log('   4. 验证赔率字段为o而不是v');
  console.log('   5. 验证完整变盘历史（3+节点）');
  console.log('\n✅ 运行: npm test -- tests/unit/sniffer_interceptor.test.js\n');
}

module.exports = {
  MockJsonSniffer,
  MOCK_DECRYPTED_DATA,
  MOCK_NON_TARGET_DATA
};