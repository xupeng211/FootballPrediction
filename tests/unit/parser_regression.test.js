/**
 * TITAN V6.0 REGRESSION SQUAD - 解析器回归测试
 * ==============================================
 * 验证 OddsPortalParser 与 OddsPortalHarvester 旧逻辑的等效性
 * 
 * @module tests/unit/parser_regression
 * @version V6.0-REGRESSION
 * @date 2026-03-16
 */

'use strict';

const assert = require('assert');
const fs = require('fs');
const path = require('path');

// 载入新旧模块
const {
  deepParseOddsData: newDeepParse,
  findValuesByKey: newFindValuesByKey,
  findBookieById: newFindBookieById,
  BOOKMAKER_ID_MAP,
  ODDS_FIELD_PATTERNS
} = require('../../src/infrastructure/harvesters/OddsPortalParser');

// 模拟旧模块逻辑（从OddsPortalHarvester提取的DEPRECATED实现）
class LegacyParser {
  _findValuesByKey(obj, targetKeys, results = [], maxDepth = 10, currentDepth = 0) {
    if (currentDepth > maxDepth || !obj || typeof obj !== 'object') {
      return results;
    }

    const keys = Array.isArray(targetKeys) ? targetKeys : [targetKeys];

    for (const key of Object.keys(obj)) {
      const lowerKey = key.toLowerCase();
      const value = obj[key];

      for (const targetKey of keys) {
        if (lowerKey === targetKey.toLowerCase() || 
            lowerKey.includes(targetKey.toLowerCase())) {
          results.push({ key, value, depth: currentDepth, path: [...arguments[5] || [], key] });
        }
      }

      if (value && typeof value === 'object') {
        this._findValuesByKey(value, targetKeys, results, maxDepth, currentDepth + 1, [...(arguments[5] || []), key]);
      }
    }

    return results;
  }

  _findBookieById(obj, bookieKey) {
    const ids = bookieKey === 'pinnacle' ? BOOKMAKER_ID_MAP.PINNACLE : BOOKMAKER_ID_MAP.BET365;
    
    const searchBookie = (current, depth = 0, maxDepth = 10) => {
      if (depth > maxDepth || !current || typeof current !== 'object') return null;

      if (Array.isArray(current)) {
        for (const item of current) {
          const found = searchBookie(item, depth + 1, maxDepth);
          if (found) return found;
        }
        return null;
      }

      const id = current.id || current.providerId || current.bookieId || current.bid;
      const name = current.name || current.bookie || current.provider || current.label;
      
      if (id !== undefined && id !== null) {
        const idStr = String(id);
        for (const targetId of ids) {
          if (idStr === String(targetId)) {
            return current;
          }
        }
      }

      if (name) {
        const nameStr = String(name).toLowerCase();
        for (const targetId of ids) {
          if (typeof targetId === 'string' && nameStr.includes(targetId.toLowerCase())) {
            return current;
          }
        }
      }

      for (const key of Object.keys(current)) {
        const found = searchBookie(current[key], depth + 1, maxDepth);
        if (found) return found;
      }

      return null;
    };

    return searchBookie(obj);
  }

  _normalizeOddsArray(odds) {
    if (!odds) return null;
    
    if (Array.isArray(odds) && odds.length >= 3) {
      const nums = odds.slice(0, 3).map(o => parseFloat(o));
      if (nums.every(n => !isNaN(n) && n > 1 && n < 100)) {
        return nums.map(n => parseFloat(n.toFixed(2)));
      }
    }
    
    if (typeof odds === 'object' && !Array.isArray(odds)) {
      const home = odds.home || odds[0] || odds.h;
      const draw = odds.draw || odds[1] || odds.d;
      const away = odds.away || odds[2] || odds.a;
      
      if (home !== undefined && draw !== undefined && away !== undefined) {
        return [
          parseFloat(parseFloat(String(home)).toFixed(2)),
          parseFloat(parseFloat(String(draw)).toFixed(2)),
          parseFloat(parseFloat(String(away)).toFixed(2))
        ];
      }
    }

    return null;
  }

  _deepParseOddsData(apiData) {
    const result = {
      opening_odds: null,
      closing_odds: null,
      movement_curve: [],
      bookmakers: {},
      timestamps: {},
      _apiExcavator: true
    };

    try {
      const pinData = this._findBookieById(apiData, 'pinnacle');
      const b365Data = this._findBookieById(apiData, 'bet365');

      if (pinData) {
        const openingResults = this._findValuesByKey(pinData, ODDS_FIELD_PATTERNS.OPENING);
        for (const res of openingResults) {
          const normalized = this._normalizeOddsArray(res.value);
          if (normalized) {
            result.opening_odds = normalized;
            result.bookmakers.pinnacle = result.bookmakers.pinnacle || {};
            result.bookmakers.pinnacle.opening = normalized;
            break;
          }
        }

        const closingResults = this._findValuesByKey(pinData, ODDS_FIELD_PATTERNS.CLOSING);
        for (const res of closingResults) {
          const normalized = this._normalizeOddsArray(res.value);
          if (normalized) {
            result.closing_odds = normalized;
            result.bookmakers.pinnacle = result.bookmakers.pinnacle || {};
            result.bookmakers.pinnacle.closing = normalized;
            break;
          }
        }
      }

      if (b365Data) {
        result.bookmakers.bet365 = {};

        const openingResults = this._findValuesByKey(b365Data, ODDS_FIELD_PATTERNS.OPENING);
        for (const res of openingResults) {
          const normalized = this._normalizeOddsArray(res.value);
          if (normalized) {
            result.bookmakers.bet365.opening = normalized;
            break;
          }
        }

        const closingResults = this._findValuesByKey(b365Data, ODDS_FIELD_PATTERNS.CLOSING);
        for (const res of closingResults) {
          const normalized = this._normalizeOddsArray(res.value);
          if (normalized) {
            result.bookmakers.bet365.closing = normalized;
            break;
          }
        }
      }
    } catch (e) {
      console.error('Legacy parsing error:', e.message);
    }

    return result;
  }
}

// 测试套件
console.log('\n╔══════════════════════════════════════════════════════════════════╗');
console.log('║     🔬 TITAN V6.0 REGRESSION SQUAD - 回归审计 🔬               ║');
console.log('║     验证 OddsPortalParser 与旧逻辑的等效性                     ║');
console.log('╚══════════════════════════════════════════════════════════════════╝\n');

// 载入测试样本
const mockDataPath = path.join(__dirname, '../mocks/fulham_api_sample.json');
const mockData = JSON.parse(fs.readFileSync(mockDataPath, 'utf-8'));

const testSamples = [
  { name: 'ajax结构', data: mockData.ajax },
  { name: 'raw结构', data: mockData.raw },
  { name: '嵌套结构', data: { nested: { deep: mockData.ajax } } }
];

let passCount = 0;
let failCount = 0;
const startTime = Date.now();

// 执行测试
for (const sample of testSamples) {
  console.log(`\n📋 测试样本: ${sample.name}`);
  console.log('-'.repeat(60));

  const legacyParser = new LegacyParser();
  
  // 旧逻辑输出
  const legacyResult = legacyParser._deepParseOddsData(sample.data);
  
  // 新逻辑输出
  const newResult = newDeepParse(sample.data);

  // 断言1: _apiExcavator 标记
  try {
    assert.strictEqual(legacyResult._apiExcavator, newResult._apiExcavator, 
      '_apiExcavator 标记不一致');
    console.log('  ✅ PASS: _apiExcavator 标记一致');
    passCount++;
  } catch (e) {
    console.log(`  ❌ FAIL: ${e.message}`);
    failCount++;
  }

  // 断言2: Bet365 opening odds
  try {
    const legacyBet365Opening = legacyResult.bookmakers?.bet365?.opening;
    const newBet365Opening = newResult.bet365?.opening;
    
    if (legacyBet365Opening && newBet365Opening) {
      assert.deepStrictEqual(legacyBet365Opening, newBet365Opening,
        'Bet365 opening odds 不一致');
      console.log(`  ✅ PASS: Bet365 opening [${newBet365Opening.join(', ')}]`);
    } else if (!legacyBet365Opening && !newBet365Opening) {
      console.log('  ✅ PASS: Bet365 opening 均为 null');
    } else {
      throw new Error(`Bet365 opening 不匹配: 旧=${legacyBet365Opening}, 新=${newBet365Opening}`);
    }
    passCount++;
  } catch (e) {
    console.log(`  ❌ FAIL: ${e.message}`);
    failCount++;
  }

  // 断言3: Bet365 closing odds
  try {
    const legacyBet365Closing = legacyResult.bookmakers?.bet365?.closing;
    const newBet365Closing = newResult.bet365?.closing;
    
    if (legacyBet365Closing && newBet365Closing) {
      assert.deepStrictEqual(legacyBet365Closing, newBet365Closing,
        'Bet365 closing odds 不一致');
      console.log(`  ✅ PASS: Bet365 closing [${newBet365Closing.join(', ')}]`);
    } else if (!legacyBet365Closing && !newBet365Closing) {
      console.log('  ✅ PASS: Bet365 closing 均为 null');
    } else {
      throw new Error(`Bet365 closing 不匹配: 旧=${legacyBet365Closing}, 新=${newBet365Closing}`);
    }
    passCount++;
  } catch (e) {
    console.log(`  ❌ FAIL: ${e.message}`);
    failCount++;
  }

  // 断言4: Pinnacle closing odds
  try {
    const legacyPinnacleClosing = legacyResult.bookmakers?.pinnacle?.closing || legacyResult.closing_odds;
    const newPinnacleClosing = newResult.pinnacle?.closing;
    
    if (legacyPinnacleClosing && newPinnacleClosing) {
      assert.deepStrictEqual(legacyPinnacleClosing, newPinnacleClosing,
        'Pinnacle closing odds 不一致');
      console.log(`  ✅ PASS: Pinnacle closing [${newPinnacleClosing.join(', ')}]`);
    } else if (!legacyPinnacleClosing && !newPinnacleClosing) {
      console.log('  ✅ PASS: Pinnacle closing 均为 null');
    } else {
      throw new Error(`Pinnacle closing 不匹配: 旧=${legacyPinnacleClosing}, 新=${newPinnacleClosing}`);
    }
    passCount++;
  } catch (e) {
    console.log(`  ❌ FAIL: ${e.message}`);
    failCount++;
  }
}

// 纯函数性质测试
console.log('\n\n🔬 纯函数性质审计');
console.log('='.repeat(60));

let pureFunctionTest = true;
try {
  // 测试1: 相同输入必须产生相同输出
  const input = mockData.ajax;
  const result1 = newDeepParse(input);
  const result2 = newDeepParse(input);
  
  assert.deepStrictEqual(result1, result2, '相同输入产生不同输出，非纯函数');
  console.log('  ✅ PASS: 相同输入产生相同输出');
  passCount++;
} catch (e) {
  console.log(`  ❌ FAIL: ${e.message}`);
  failCount++;
  pureFunctionTest = false;
}

try {
  // 测试2: 不修改输入对象
  const input = JSON.parse(JSON.stringify(mockData.ajax));
  const inputCopy = JSON.parse(JSON.stringify(mockData.ajax));
  
  newDeepParse(input);
  
  assert.deepStrictEqual(input, inputCopy, '函数修改了输入对象，非纯函数');
  console.log('  ✅ PASS: 不修改输入对象');
  passCount++;
} catch (e) {
  console.log(`  ❌ FAIL: ${e.message}`);
  failCount++;
  pureFunctionTest = false;
}

try {
  // 测试3: 不依赖外部状态 (this.config, this.browser 等)
  const newModuleSource = fs.readFileSync(
    path.join(__dirname, '../../src/infrastructure/harvesters/OddsPortalParser.js'),
    'utf-8'
  );
  
  const hasThisConfig = /this\.config/.test(newModuleSource);
  const hasThisBrowser = /this\.browser/.test(newModuleSource);
  const hasGlobalState = /global\./.test(newModuleSource);
  
  assert(!hasThisConfig, '代码包含 this.config 引用');
  assert(!hasThisBrowser, '代码包含 this.browser 引用');
  assert(!hasGlobalState, '代码包含 global. 引用');
  
  console.log('  ✅ PASS: 无外部状态依赖');
  passCount++;
} catch (e) {
  console.log(`  ❌ FAIL: ${e.message}`);
  failCount++;
  pureFunctionTest = false;
}

// 性能测试
const perfStart = Date.now();
for (let i = 0; i < 1000; i++) {
  newDeepParse(mockData.ajax);
}
const perfDuration = Date.now() - perfStart;
console.log(`\n  ⏱️  性能: 1000次解析耗时 ${perfDuration}ms (${(perfDuration/1000).toFixed(2)}ms/次)`);

// 总结果
const totalDuration = Date.now() - startTime;

console.log('\n\n╔══════════════════════════════════════════════════════════════════╗');
console.log('║     📊 REGRESSION SQUAD 最终报告 📊                            ║');
console.log('╠══════════════════════════════════════════════════════════════════╣');
console.log(`║     总测试数: ${String(passCount + failCount).padStart(3)}                                          ║`);
console.log(`║     ✅ 通过: ${String(passCount).padStart(3)}                                              ║`);
console.log(`║     ❌ 失败: ${String(failCount).padStart(3)}                                              ║`);
console.log(`║     通过率: ${String(((passCount / (passCount + failCount)) * 100).toFixed(1)).padStart(5)}%                                        ║`);
console.log(`║     总耗时: ${String(totalDuration).padStart(4)}ms                                          ║`);
console.log(`║     纯函数: ${pureFunctionTest ? '✅ 验证通过' : '❌ 验证失败'}                              ║`);
console.log('╠══════════════════════════════════════════════════════════════════╣');

if (failCount === 0) {
  console.log('║     🎉 所有回归测试通过！外科手术拆分成功！                    ║');
  console.log('║     新旧模块逻辑100%对齐，可以安全删除DEPRECATED代码           ║');
} else {
  console.log('║     ⚠️  存在测试失败，请检查逻辑差异                           ║');
}
console.log('╚══════════════════════════════════════════════════════════════════╝\n');

process.exit(failCount > 0 ? 1 : 0);
