/**
 * @file Normalizer.test.js - Normalizer 工具类单元测试
 * @module tests/unit/Normalizer
 * @version V6.6.0
 * @description
 * 测试 Normalizer 类的方法:
 * - normalizeSeason: 赛季格式标准化
 * - buildMatchId: match_id 构建
 * - isValidMatchId: match_id 格式验证
 * - normalizeTeamName: 队名归一化
 */

'use strict';

const { describe, it, before } = require('node:test');
const assert = require('node:assert');
const { Normalizer } = require('../../src/utils/Normalizer');

describe('Normalizer - V6.6 标准化工具类', () => {
  
  describe('normalizeSeason()', () => {
    it('应正确处理标准格式 YYYY/YYYY', () => {
      const result = Normalizer.normalizeSeason('2023/2024');
      assert.strictEqual(result, '2023/2024');
    });

    it('应正确处理 4位简写格式 YYMM', () => {
      const result = Normalizer.normalizeSeason('2324');
      assert.strictEqual(result, '2023/2024');
    });

    it('应正确处理 8位完整格式 YYYYMMMM', () => {
      const result = Normalizer.normalizeSeason('20232024');
      assert.strictEqual(result, '2023/2024');
    });

    it('应正确处理带横线格式 YYYY-YYYY', () => {
      const result = Normalizer.normalizeSeason('2023-2024');
      assert.strictEqual(result, '2023/2024');
    });

    it('应正确处理带下划线格式 YYYY_YYYY', () => {
      const result = Normalizer.normalizeSeason('2023_2024');
      assert.strictEqual(result, '2023/2024');
    });

    it('应正确处理空格分隔格式', () => {
      const result = Normalizer.normalizeSeason('2023 2024');
      assert.strictEqual(result, '2023/2024');
    });

    it('应对空值抛出错误', () => {
      assert.throws(() => {
        Normalizer.normalizeSeason(null);
      }, /Invalid season/);
    });

    it('应对 undefined 抛出错误', () => {
      assert.throws(() => {
        Normalizer.normalizeSeason(undefined);
      }, /Invalid season/);
    });

    it('应对空字符串抛出错误', () => {
      assert.throws(() => {
        Normalizer.normalizeSeason('');
      }, /Invalid season/);
    });

    it('应对非字符串类型抛出错误', () => {
      assert.throws(() => {
        Normalizer.normalizeSeason(2024);
      }, /Invalid season/);
    });

    it('应对非法格式抛出错误', () => {
      assert.throws(() => {
        Normalizer.normalizeSeason('abc');
      }, /Unrecognized season format/);
    });

    it('应对世纪边界情况正确处理', () => {
      const result = Normalizer.normalizeSeason('9900');
      assert.strictEqual(result, '2099/2100');
    });
  });

  describe('buildMatchId()', () => {
    it('应正确构建标准 match_id', () => {
      const result = Normalizer.buildMatchId(47, '2023/2024', '3609929');
      assert.strictEqual(result, '47_20232024_3609929');
    });

    it('应自动标准化赛季格式', () => {
      const result = Normalizer.buildMatchId(47, '2324', '3609929');
      assert.strictEqual(result, '47_20232024_3609929');
    });

    it('应处理不同联赛ID', () => {
      const result = Normalizer.buildMatchId(87, '2024/2025', '3700001');
      assert.strictEqual(result, '87_20242025_3700001');
    });

    it('应对无效联赛ID抛出错误', () => {
      assert.throws(() => {
        Normalizer.buildMatchId(null, '2023/2024', '3609929');
      });
    });

    it('应对无效 externalId 抛出错误', () => {
      assert.throws(() => {
        Normalizer.buildMatchId(47, '2023/2024', null);
      });
    });
  });

  describe('isValidMatchId()', () => {
    it('应验证标准格式为有效', () => {
      const result = Normalizer.isValidMatchId('47_20232024_3609929');
      assert.strictEqual(result, true);
    });

    it('应验证不同联赛ID为有效', () => {
      const result = Normalizer.isValidMatchId('87_20242025_3700001');
      assert.strictEqual(result, true);
    });

    it('应验证缺失下划线为无效', () => {
      const result = Normalizer.isValidMatchId('47202320243609929');
      assert.strictEqual(result, false);
    });

    it('应验证赛季格式错误为无效', () => {
      const result = Normalizer.isValidMatchId('47_2023_3609929');
      assert.strictEqual(result, false);
    });

    it('应验证空字符串为无效', () => {
      const result = Normalizer.isValidMatchId('');
      assert.strictEqual(result, false);
    });

    it('应验证 null 为无效', () => {
      const result = Normalizer.isValidMatchId(null);
      assert.strictEqual(result, false);
    });

    it('应验证 undefined 为无效', () => {
      const result = Normalizer.isValidMatchId(undefined);
      assert.strictEqual(result, false);
    });

    it('应验证特殊字符为无效', () => {
      const result = Normalizer.isValidMatchId('47_2023-2024_3609929');
      assert.strictEqual(result, false);
    });

    it('应验证多段格式为无效', () => {
      const result = Normalizer.isValidMatchId('47_20232024_3609929_extra');
      assert.strictEqual(result, false);
    });
  });

  describe('normalizeTeamName()', () => {
    it('应将中超别名统一到 OddsPortal 对账口径', () => {
      assert.strictEqual(
        Normalizer.normalizeTeamName('Henan FC'),
        'Henan Songshan Longmen'
      );
      assert.strictEqual(
        Normalizer.normalizeTeamName('Henan Fc'),
        'Henan Songshan Longmen'
      );
      assert.strictEqual(
        Normalizer.normalizeTeamName('Shenzhen Peng City'),
        'Shenzhen Xinpengcheng'
      );
      assert.strictEqual(
        Normalizer.normalizeTeamName('Chengdu Rongcheng Fc'),
        'Chengdu Rongcheng'
      );
    });

    it('无显式别名时应保留常见俱乐部缩写大写格式', () => {
      assert.strictEqual(
        Normalizer.normalizeTeamName('New York City Fc'),
        'New York City FC'
      );
      assert.strictEqual(
        Normalizer.normalizeTeamName('Inter Miami Cf'),
        'Inter Miami CF'
      );
    });
  });

  describe('鲁棒性边界测试', () => {
    it('应处理极长赛季字符串', () => {
      assert.throws(() => {
        Normalizer.normalizeSeason('202320242025');
      }, /Unrecognized season format/);
    });

    it('应处理非数字赛季', () => {
      assert.throws(() => {
        Normalizer.normalizeSeason('abcd/efgh');
      }, /Unrecognized season format/);
    });

    it('应处理负数联赛ID', () => {
      const result = Normalizer.buildMatchId(-1, '2023/2024', '3609929');
      assert.strictEqual(result, '-1_20232024_3609929');
    });

    it('应处理超大联赛ID', () => {
      const result = Normalizer.buildMatchId(999999, '2023/2024', '3609929');
      assert.strictEqual(result, '999999_20232024_3609929');
      assert.strictEqual(Normalizer.isValidMatchId(result), true);
    });
  });
});
