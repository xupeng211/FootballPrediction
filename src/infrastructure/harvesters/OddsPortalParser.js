/**
 * TITAN V6.0 OddsPortalParser - API深度破译与时序历史重构
 * ===========================================================
 * 从拦截的API报文中提取完整的赔率变动曲线与原始时间戳
 * 
 * @module infrastructure/harvesters/OddsPortalParser
 * @version V6.0-API-DECRYPT
 * @date 2026-03-16
 */

'use strict';

// V6.0 SCHEMA-DESIGN: 博彩公司ID映射表 (P0必抓 + P1主流)
const BOOKMAKER_ID_MAP = {
  // P0 级 (必抓) - 核心数据源
  PINNACLE: [18, 27, 'pinnacle', 'Pinnacle', 'PINNACLE'],
  BET365: [16, 'bet365', 'Bet365', 'BET365', '365'],
  
  // P1 级 (主流) - 市场参考
  BWIN: [1, 'bwin', 'Bwin', 'BWIN', 'bwin.com'],
  WILLIAM_HILL: [2, 'williamhill', 'William Hill', 'WilliamHill', 'WH', 'wh'],
  INTERTOPS: [3, 'interwetten', 'Interwetten', 'Intertops', 'intertops'],
  
  // 名称到键的映射
  NAME_TO_KEY: {
    // P0
    'pinnacle': 'pinnacle', 'Pinnacle': 'pinnacle', 'PINNACLE': 'pinnacle',
    '18': 'pinnacle', '27': 'pinnacle',
    'bet365': 'bet365', 'Bet365': 'bet365', 'BET365': 'bet365', '365': 'bet365',
    '16': 'bet365',
    // P1
    'bwin': 'bwin', 'Bwin': 'bwin', 'BWIN': 'bwin', 'bwin.com': 'bwin', '1': 'bwin',
    'williamhill': 'william_hill', 'William Hill': 'william_hill', 'WilliamHill': 'william_hill',
    'WH': 'william_hill', 'wh': 'william_hill', '2': 'william_hill',
    'interwetten': 'intertops', 'Interwetten': 'intertops', 'intertops': 'intertops',
    'Intertops': 'intertops', '3': 'intertops'
  },
  
  // 公司元数据
  METADATA: {
    pinnacle: { id: 18, name: 'Pinnacle', tier: 'P0', priority: 1 },
    bet365: { id: 16, name: 'Bet365', tier: 'P0', priority: 2 },
    bwin: { id: 1, name: 'Bwin', tier: 'P1', priority: 3 },
    william_hill: { id: 2, name: 'William Hill', tier: 'P1', priority: 4 },
    intertops: { id: 3, name: 'Interwetten', tier: 'P1', priority: 5 }
  }
};

// V6.0 API-DECRYPT: 赔率字段关键词映射
const ODDS_FIELD_PATTERNS = {
  OPENING: ['opening', 'initial', 'start', 'open', 'first', 'orig', 'original'],
  CLOSING: ['closing', 'current', 'last', 'final', 'end', 'now', 'latest'],
  HISTORY: ['history', 'movement', 'timeline', 'changes', 'trend', 'oddsHistory', 'priceHistory'],
  TIMESTAMP: ['timestamp', 'time', 'dat_h', 'date', 't', 'updated', 'created', 'ts']
};

/**
 * V6.0 API-DECRYPT: 递归历史矿工算法
 * 扫描API响应中的时序赔率数据点 { ts: timestamp, o: [odds] }
 * 
 * @param {Object} obj - API响应对象
 * @param {Array} results - 结果收集数组
 * @param {number} maxDepth - 最大递归深度
 * @param {number} currentDepth - 当前深度
 * @param {string} path - 当前路径
 * @returns {Array} 历史记录点数组 [{ ts, o, path }]
 */
function recursiveHistoryScanner(obj, results = [], maxDepth = 15, currentDepth = 0, path = '') {
  if (currentDepth > maxDepth || !obj || typeof obj !== 'object') {
    return results;
  }

  // 检查当前对象是否包含时序赔率结构
  const hasOddsArray = Array.isArray(obj) && 
    obj.length === 3 && 
    obj.every(v => {
      const num = parseFloat(v);
      return !isNaN(num) && num > 1 && num < 100;
    });

  // 如果是纯数组，检查兄弟节点是否有时间戳
  if (hasOddsArray && path) {
    // 尝试从路径或上下文推断时间戳
    const parentPath = path.substring(0, path.lastIndexOf('.'));
    results.push({
      o: obj.map(v => parseFloat(v)),
      path: path,
      _type: 'raw_odds_array'
    });
  }

  // 遍历对象属性
  for (const [key, value] of Object.entries(obj)) {
    const currentPath = path ? `${path}.${key}` : key;
    const lowerKey = key.toLowerCase();

    // 情况1: 值为数组且是赔率格式 [x.xx, x.xx, x.xx]
    if (Array.isArray(value) && value.length === 3) {
      const odds = value.map(v => parseFloat(v));
      const areValidOdds = odds.every(n => !isNaN(n) && n > 1 && n < 100);
      
      if (areValidOdds) {
        // 查找兄弟节点中的时间戳
        let timestamp = null;
        const siblingKeys = Object.keys(obj);
        
        for (const sKey of siblingKeys) {
          const sLower = sKey.toLowerCase();
          if (ODDS_FIELD_PATTERNS.TIMESTAMP.some(ts => sLower.includes(ts.toLowerCase()))) {
            const tsValue = obj[sKey];
            if (typeof tsValue === 'number' && tsValue > 1000000000) {
              timestamp = tsValue; // Unix时间戳
              break;
            } else if (typeof tsValue === 'string') {
              const parsed = Date.parse(tsValue) / 1000;
              if (!isNaN(parsed) && parsed > 1000000000) {
                timestamp = parsed;
                break;
              }
            }
          }
        }

        // 如果找到时间戳，记录完整数据点
        if (timestamp) {
          results.push({
            ts: timestamp,
            o: odds,
            path: currentPath,
            _type: 'timestamped_odds'
          });
        } else {
          // 无时间戳的赔率记录
          results.push({
            o: odds,
            path: currentPath,
            _type: 'odds_only'
          });
        }
      }
    }

    // 情况2: 值为对象，包含 o/odds 和 t/ts 字段
    if (typeof value === 'object' && value !== null && !Array.isArray(value)) {
      const oddsValue = value.o || value.odds || value.price;
      const tsValue = value.t || value.ts || value.timestamp || value.time || value.dat_h;

      if (Array.isArray(oddsValue) && oddsValue.length === 3) {
        const odds = oddsValue.map(v => parseFloat(v));
        const areValidOdds = odds.every(n => !isNaN(n) && n > 1 && n < 100);

        if (areValidOdds) {
          let timestamp = null;
          if (typeof tsValue === 'number' && tsValue > 1000000000) {
            timestamp = tsValue;
          } else if (typeof tsValue === 'string') {
            const parsed = parseInt(tsValue);
            if (!isNaN(parsed) && parsed > 1000000000) {
              timestamp = parsed;
            }
          }

          if (timestamp) {
            results.push({
              ts: timestamp,
              o: odds,
              path: currentPath,
              _type: 'structured_odds'
            });
          }
        }
      }

      // 递归扫描
      recursiveHistoryScanner(value, results, maxDepth, currentDepth + 1, currentPath);
    }

    // 情况3: 历史数组包含多个时间点
    if (Array.isArray(value) && value.length > 0) {
      // 检查是否是历史记录数组
      const isHistoryArray = value.every(item => {
        if (typeof item !== 'object') return false;
        const hasOdds = Array.isArray(item.o || item.odds) || 
          (Array.isArray(item) && item.length === 3);
        const hasTs = item.t !== undefined || item.ts !== undefined || 
          item.timestamp !== undefined || item.time !== undefined;
        return hasOdds || hasTs;
      });

      if (isHistoryArray) {
        for (let i = 0; i < value.length; i++) {
          const item = value[i];
          const itemPath = `${currentPath}[${i}]`;

          if (typeof item === 'object') {
            const odds = item.o || item.odds || (Array.isArray(item) ? item : null);
            const ts = item.t || item.ts || item.timestamp || item.time || item.dat_h;

            if (Array.isArray(odds) && odds.length === 3) {
              const oddsNums = odds.map(v => parseFloat(v));
              const areValid = oddsNums.every(n => !isNaN(n) && n > 1 && n < 100);

              if (areValid) {
                let timestamp = null;
                if (typeof ts === 'number' && ts > 1000000000) {
                  timestamp = ts;
                } else if (typeof ts === 'string') {
                  const parsed = parseInt(ts);
                  if (!isNaN(parsed) && parsed > 1000000000) {
                    timestamp = parsed;
                  }
                }

                if (timestamp) {
                  results.push({
                    ts: timestamp,
                    o: oddsNums,
                    path: itemPath,
                    _type: 'history_array_item'
                  });
                }
              }
            }
          }
        }
      }
    }
  }

  return results;
}

/**
 * V6.0 API-DECRYPT: 处理并排序历史数据
 * 自动锚定初盘/终盘，计算波动指数
 * 
 * @param {Array} historyPoints - recursiveHistoryScanner返回的原始点
 * @returns {Object} { opening, closing, history, volatility_index, last_changed_at }
 */
function processOddsTimeline(historyPoints) {
  if (!historyPoints || historyPoints.length === 0) {
    return null;
  }

  // 过滤出带时间戳的点
  const timestampedPoints = historyPoints.filter(p => p.ts !== undefined);
  
  // 按时间戳升序排序
  timestampedPoints.sort((a, b) => a.ts - b.ts);

  // 去重：同一秒内的记录只保留第一个
  const uniquePoints = [];
  let lastTs = 0;
  for (const point of timestampedPoints) {
    if (point.ts !== lastTs) {
      uniquePoints.push(point);
      lastTs = point.ts;
    }
  }

  if (uniquePoints.length === 0) {
    // 没有时间戳，尝试从原始点提取
    const oddsOnly = historyPoints.filter(p => p.o !== undefined);
    if (oddsOnly.length === 0) return null;
    
    return {
      opening: oddsOnly[0].o,
      closing: oddsOnly[oddsOnly.length - 1].o,
      history: oddsOnly.map(p => ({ o: p.o })),
      volatility_index: 0,
      last_changed_at: null,
      _point_count: oddsOnly.length,
      _is_premium: oddsOnly.length >= 3
    };
  }

  // 初盘（最早）
  const opening = uniquePoints[0].o;
  const openingTs = uniquePoints[0].ts;

  // 终盘（最晚）
  const closing = uniquePoints[uniquePoints.length - 1].o;
  const closingTs = uniquePoints[uniquePoints.length - 1].ts;

  // 计算波动指数（各位置赔率变化幅度的平均值）
  let volatilitySum = 0;
  for (let i = 1; i < uniquePoints.length; i++) {
    const prev = uniquePoints[i - 1].o;
    const curr = uniquePoints[i].o;
    const change = (
      Math.abs(curr[0] - prev[0]) / prev[0] +
      Math.abs(curr[1] - prev[1]) / prev[1] +
      Math.abs(curr[2] - prev[2]) / prev[2]
    ) / 3;
    volatilitySum += change;
  }
  const volatilityIndex = uniquePoints.length > 1 
    ? (volatilitySum / (uniquePoints.length - 1)) * 100 
    : 0;

  return {
    opening,
    closing,
    history: uniquePoints.map(p => ({ ts: p.ts, o: p.o })),
    volatility_index: parseFloat(volatilityIndex.toFixed(4)),
    last_changed_at: closingTs,
    opening_at: openingTs,
    _point_count: uniquePoints.length,
    _is_premium: uniquePoints.length >= 3
  };
}

/**
 * 递归深度搜索对象中的所有值
 * @param {Object} obj - 要搜索的对象
 * @param {string|Array} targetKeys - 目标键名或键名列表
 * @param {Array} results - 结果收集数组
 * @param {number} maxDepth - 最大递归深度
 * @param {number} currentDepth - 当前深度
 * @param {Array} path - 当前路径
 * @returns {Array} 找到的所有值
 */
function findValuesByKey(obj, targetKeys, results = [], maxDepth = 10, currentDepth = 0, path = []) {
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
        results.push({ key, value, depth: currentDepth, path: [...path, key] });
      }
    }

    if (value && typeof value === 'object') {
      findValuesByKey(value, targetKeys, results, maxDepth, currentDepth + 1, [...path, key]);
    }
  }

  return results;
}

/**
 * 递归查找博彩公司数据
 * @param {Object} obj - API返回的对象
 * @param {string} bookieKey - 'pinnacle' 或 'bet365'
 * @returns {Object|null} 博彩公司数据
 */
function findBookieById(obj, bookieKey) {
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

/**
 * V6.0 SCHEMA-DESIGN: 纯度校验函数
 * 验证赔率数组是否符合入库标准
 * 
 * @param {Array} odds - 赔率数组 [H, D, A]
 * @param {Object} options - 校验选项
 * @returns {Object} { valid: boolean, errors: string[], purity_score: number }
 */
function validatePurity(odds, options = {}) {
  const errors = [];
  const { 
    minOdds = 1.01, 
    maxOdds = 99.99, 
    requireLength = 3,
    strictMode = true 
  } = options;
  
  // 1. 检查是否为数组
  if (!Array.isArray(odds)) {
    errors.push('赔率数据必须是数组');
    return { valid: false, errors, purity_score: 0 };
  }
  
  // 2. 检查数组长度
  if (odds.length !== requireLength) {
    errors.push(`赔率数组长度必须为${requireLength}，当前为${odds.length}`);
    return { valid: false, errors, purity_score: 0 };
  }
  
  // 3. 检查每个元素
  let validCount = 0;
  for (let i = 0; i < odds.length; i++) {
    const val = odds[i];
    const num = parseFloat(val);
    
    // 检查是否为有效数字
    if (isNaN(num)) {
      errors.push(`位置${i}的值不是有效数字: ${val}`);
      continue;
    }
    
    // 检查数值范围
    if (num < minOdds || num > maxOdds) {
      errors.push(`位置${i}的数值越界: ${num} (允许范围: ${minOdds}-${maxOdds})`);
      continue;
    }
    
    validCount++;
  }
  
  // 4. 计算纯度分数
  const purity_score = Math.round((validCount / requireLength) * 100);
  
  // 5. 严格模式检查
  if (strictMode && errors.length > 0) {
    return { 
      valid: false, 
      errors, 
      purity_score,
      _rejected: true,
      _rejection_reason: errors.join('; ')
    };
  }
  
  return { 
    valid: errors.length === 0, 
    errors, 
    purity_score,
    normalized_odds: odds.map(v => parseFloat(v))
  };
}

/**
 * V6.0 SCHEMA-DESIGN: 计算波动指数
 * @param {Array} history - 历史记录数组 [{ t, o }]
 * @returns {Object} 波动指数和统计数据
 */
function calculateVolatilityMetrics(history) {
  if (!history || history.length < 2) {
    return {
      volatility_index: 0,
      max_home_movement: 0,
      max_draw_movement: 0,
      max_away_movement: 0,
      total_movement_count: history ? history.length : 0
    };
  }
  
  let volatilitySum = 0;
  let maxHomeMove = 0;
  let maxDrawMove = 0;
  let maxAwayMove = 0;
  
  for (let i = 1; i < history.length; i++) {
    const prev = history[i - 1].o;
    const curr = history[i].o;
    
    // 计算各位置的变化幅度
    const homeChange = Math.abs(curr[0] - prev[0]);
    const drawChange = Math.abs(curr[1] - prev[1]);
    const awayChange = Math.abs(curr[2] - prev[2]);
    
    // 更新最大变化
    maxHomeMove = Math.max(maxHomeMove, homeChange);
    maxDrawMove = Math.max(maxDrawMove, drawChange);
    maxAwayMove = Math.max(maxAwayMove, awayChange);
    
    // 计算相对变化率
    const change = (
      (homeChange / prev[0]) +
      (drawChange / prev[1]) +
      (awayChange / prev[2])
    ) / 3;
    volatilitySum += change;
  }
  
  const volatility_index = history.length > 1 
    ? (volatilitySum / (history.length - 1)) * 100 
    : 0;
  
  return {
    volatility_index: parseFloat(volatility_index.toFixed(4)),
    max_home_movement: parseFloat(maxHomeMove.toFixed(4)),
    max_draw_movement: parseFloat(maxDrawMove.toFixed(4)),
    max_away_movement: parseFloat(maxAwayMove.toFixed(4)),
    total_movement_count: history.length
  };
}

/**
 * V6.0 API-DECRYPT: 深度解析赔率数据（含时序历史）
 * @param {Object} apiData - API返回的原始数据
 * @returns {Object} 解析后的赔率数据 { pinnacle: {}, bet365: {} }
 */
function deepParseOddsData(apiData) {
  const result = {
    pinnacle: null,
    bet365: null,
    raw: apiData,
    _apiDecrypt: true,
    _version: 'V6.0-DECRYPT'
  };

  if (!apiData || typeof apiData !== 'object') {
    return result;
  }

  // 查找Pinnacle数据
  const pinData = findBookieById(apiData, 'pinnacle');
  if (pinData) {
    // 使用时序历史扫描器
    const historyPoints = recursiveHistoryScanner(pinData);
    const timeline = processOddsTimeline(historyPoints);

    result.pinnacle = {
      detected: true,
      bookmaker_id: 18,
      _is_premium: timeline?._is_premium || false,
      ...timeline
    };
  }

  // 查找Bet365数据
  const b365Data = findBookieById(apiData, 'bet365');
  if (b365Data) {
    const historyPoints = recursiveHistoryScanner(b365Data);
    const timeline = processOddsTimeline(historyPoints);

    result.bet365 = {
      detected: true,
      bookmaker_id: 16,
      _is_premium: timeline?._is_premium || false,
      ...timeline
    };
  }

  return result;
}

/**
 * 从搜索结果中提取赔率数组
 * @param {Array} results - findValuesByKey返回的结果
 * @returns {Array|null} 赔率数组 [home, draw, away]
 */
function extractOddsArray(results) {
  if (!results || results.length === 0) return null;
  
  for (const result of results) {
    const value = result.value;
    
    // 处理数组格式: [1.5, 4.0, 6.5]
    if (Array.isArray(value) && value.length >= 3) {
      const nums = value.slice(0, 3).map(v => parseFloat(v));
      if (nums.every(n => !isNaN(n) && n > 1 && n < 100)) {
        return nums;
      }
    }
    
    // 处理对象格式: {home: 1.5, draw: 4.0, away: 6.5}
    if (typeof value === 'object' && !Array.isArray(value)) {
      const home = value.home !== undefined ? parseFloat(value.home) : 
                   value.h !== undefined ? parseFloat(value.h) : null;
      const draw = value.draw !== undefined ? parseFloat(value.draw) : 
                   value.d !== undefined ? parseFloat(value.d) : null;
      const away = value.away !== undefined ? parseFloat(value.away) : 
                   value.a !== undefined ? parseFloat(value.a) : null;
      
      if (home !== null && draw !== null && away !== null &&
          !isNaN(home) && !isNaN(draw) && !isNaN(away) &&
          home > 1 && home < 100 && draw > 1 && draw < 100 && away > 1 && away < 100) {
        return [home, draw, away];
      }
    }
  }
  return null;
}

/**
 * DOM Sniper: 从页面DOM提取赔率数据
 * @param {Object} page - Playwright页面对象
 * @returns {Object} { pinnacleOdds, bet365Odds, allBookmakers }
 */
async function extractOddsFromDOM(page) {
  return await page.evaluate(() => {
    const results = { 
      pinnacleOdds: null, 
      bet365Odds: null, 
      allBookmakers: [],
      debug: {
        bodyLength: document.body.innerText.length,
        hasPinnacle: /Pinnacle/i.test(document.body.innerText),
        hasBet365: /Bet365|bet365/i.test(document.body.innerText)
      }
    };

    // 尝试多种选择器
    const selectors = [
      'table tbody tr',
      'div[role="row"]',
      '[class*="bookmaker"]',
      '[class*="odds"]',
      '.odds-table tr'
    ];

    for (const selector of selectors) {
      const rows = document.querySelectorAll(selector);
      
      rows.forEach((row) => {
        const text = row.textContent || '';
        const isPinnacle = /Pinnacle/i.test(text);
        const isBet365 = /Bet365|bet365/i.test(text);

        const oddsPattern = /(\d+\.\d{2})/g;
        const odds = text.match(oddsPattern);

        if (odds && odds.length >= 3) {
          const oddsValues = odds.slice(0, 3).map(o => parseFloat(o));

          if (isPinnacle && !results.pinnacleOdds) {
            results.pinnacleOdds = oddsValues;
          }
          if (isBet365 && !results.bet365Odds) {
            results.bet365Odds = oddsValues;
          }

          const bookieName = text.substring(0, 30).trim();
          results.allBookmakers.push({ name: bookieName, odds: oddsValues });
        }
      });

      if (results.allBookmakers.length > 0) break;
    }

    // 从完整文本匹配（备用）
    if (!results.pinnacleOdds || !results.bet365Odds) {
      const allText = document.body.innerText || '';

      if (!results.pinnacleOdds) {
        const pinnacleMatch = allText.match(/Pinnacle\D{0,100}(\d+\.\d{2})\s+(\d+\.\d{2})\s+(\d+\.\d{2})/i);
        if (pinnacleMatch) {
          results.pinnacleOdds = [
            parseFloat(pinnacleMatch[1]),
            parseFloat(pinnacleMatch[2]),
            parseFloat(pinnacleMatch[3])
          ];
          results.debug.pinnacleSource = 'text_regex';
        }
      }

      if (!results.bet365Odds) {
        const bet365Match = allText.match(/Bet365\D{0,100}(\d+\.\d{2})\s+(\d+\.\d{2})\s+(\d+\.\d{2})/i);
        if (bet365Match) {
          results.bet365Odds = [
            parseFloat(bet365Match[1]),
            parseFloat(bet365Match[2]),
            parseFloat(bet365Match[3])
          ];
          results.debug.bet365Source = 'text_regex';
        }
      }
    }

    return results;
  });
}

/**
 * 从API响应中提取所有数值数组（赔率候选）
 * @param {Object} obj - API响应对象
 * @param {Object} result - 结果收集器
 * @param {number} depth - 当前深度
 * @param {string} path - 当前路径
 */
function extractOddsArrays(obj, result = { rawArrays: [] }, depth = 0, path = '') {
  if (depth > 15 || !obj || typeof obj !== 'object') return result;

  for (const [key, value] of Object.entries(obj)) {
    const currentPath = path ? `${path}.${key}` : key;

    if (Array.isArray(value) && value.length === 3) {
      const areNumbers = value.every(v => {
        const num = parseFloat(v);
        return !isNaN(num) && num > 1 && num < 100;
      });
      if (areNumbers) {
        result.rawArrays.push({
          path: currentPath,
          values: value.map(v => parseFloat(v)),
          depth
        });
      }
    }

    if (typeof value === 'object' && value !== null) {
      extractOddsArrays(value, result, depth + 1, currentPath);
    }
  }

  return result;
}

/**
 * V6.0 SCHEMA-DESIGN: 构建标准化的市场情感数据对象
 * 符合回测级精度标准，包含胜平负全时序赔率
 * 
 * @param {Object} apiResult - API解析结果
 * @param {Object} domResult - DOM提取结果
 * @param {Object} options - 配置选项
 * @returns {Object} 标准化的市场情感数据
 */
function buildMarketSentiment(apiResult, domResult, options = {}) {
  const extractionTimestamp = new Date().toISOString();
  const { sourceChannel = 'unknown', strictValidation = true } = options;
  
  const ms = {
    _schema_version: 'V6.0-ULTIMATE',
    _extract_timestamp: extractionTimestamp,
    extract_method: 'ODDS_PORTAL_API_DECRYPT_V6.0',
    source: 'oddsportal_api_decrypt',
    _apiDecrypt: true
  };
  
  let premiumCount = 0;
  let validBookmakerCount = 0;

  /**
   * 内部函数：构建单一博彩公司的标准结构
   * @param {Object} bookieData - 解析后的博彩公司数据
   * @param {string} bookieKey - 公司键名
   * @param {Object} fallbackData - DOM回退数据
   * @returns {Object|null} 标准化的公司数据
   */
  const buildBookieStructure = (bookieData, bookieKey, fallbackData) => {
    if (!bookieData && !fallbackData) return null;
    
    const meta = BOOKMAKER_ID_MAP.METADATA[bookieKey];
    if (!meta) return null;
    
    // 使用纯度校验
    let opening = null;
    let closing = null;
    let history = [];
    let sourceChannel = 'api';
    let isComplete = true;
    let dataQuality = 'STANDARD';
    
    if (bookieData) {
      // API数据 - 完整时序
      if (bookieData.opening) {
        const validation = validatePurity(bookieData.opening, { strictMode: strictValidation });
        if (validation.valid) opening = { o: validation.normalized_odds, t: bookieData.opening_at };
      }
      
      if (bookieData.closing) {
        const validation = validatePurity(bookieData.closing, { strictMode: strictValidation });
        if (validation.valid) closing = { o: validation.normalized_odds, t: bookieData.last_changed_at };
      }
      
      if (bookieData.history && bookieData.history.length > 0) {
        history = bookieData.history
          .filter(h => validatePurity(h.o, { strictMode: false }).valid)
          .map((h, index) => ({
            t: h.ts,
            o: h.o,
            type: index === 0 ? 'OPEN' : (index === bookieData.history.length - 1 ? 'CLOSE' : 'MOVE')
          }));
      }
      
      sourceChannel = bookieData._detected_channel || 'api';
      isComplete = bookieData._is_premium || false;
      dataQuality = bookieData._is_premium ? 'PREMIUM-GOLD' : 'STANDARD';
    } else if (fallbackData) {
      // DOM回退数据 - 仅终盘
      const validation = validatePurity(fallbackData, { strictMode: strictValidation });
      if (!validation.valid) return null;
      
      closing = { o: validation.normalized_odds, t: Math.floor(Date.now() / 1000) };
      history = [{ t: closing.t, o: closing.o, type: 'CLOSE' }];
      sourceChannel = 'dom_fallback';
      isComplete = false;
      dataQuality = 'PARTIAL';
    }
    
    // 必须有closing数据才能入库
    if (!closing) return null;
    
    // 如果没有opening，使用最早的history
    if (!opening && history.length > 0) {
      const first = history[0];
      opening = { o: first.o, t: first.t };
    }
    
    // 计算波动指标
    const volatility = calculateVolatilityMetrics(history);
    
    // 计算纯度分数
    let purityScore = 100;
    if (!isComplete) purityScore -= 20;
    if (history.length < 3) purityScore -= 10;
    if (dataQuality === 'PARTIAL') purityScore -= 15;
    
    validBookmakerCount++;
    if (bookieData && bookieData._is_premium) premiumCount++;
    
    return {
      bookmaker_id: meta.id,
      bookmaker_name: meta.name,
      tier: meta.tier,
      
      opening: opening || closing, // 保底使用closing
      closing: closing,
      
      movement: {
        history: history,
        point_count: history.length,
        ...volatility
      },
      
      metadata: {
        purity_score: Math.max(0, purityScore),
        source_channel: sourceChannel,
        extraction_timestamp: extractionTimestamp,
        data_quality: dataQuality,
        is_complete: isComplete
      }
    };
  };

  // P0 级: Pinnacle
  const pinData = apiResult?.pinnacle;
  const pinFallback = domResult?.pinnacleOdds;
  const pinStructured = buildBookieStructure(pinData, 'pinnacle', pinFallback);
  if (pinStructured) ms.pinnacle = pinStructured;

  // P0 级: Bet365
  const b365Data = apiResult?.bet365;
  const b365Fallback = domResult?.bet365Odds;
  const b365Structured = buildBookieStructure(b365Data, 'bet365', b365Fallback);
  if (b365Structured) ms.bet365 = b365Structured;

  // P1 级: Bwin (如果API中有数据)
  if (apiResult?.bwin) {
    const bwinStructured = buildBookieStructure(apiResult.bwin, 'bwin', null);
    if (bwinStructured) ms.bwin = bwinStructured;
  }

  // P1 级: William Hill (如果API中有数据)
  if (apiResult?.william_hill) {
    const whStructured = buildBookieStructure(apiResult.william_hill, 'william_hill', null);
    if (whStructured) ms.william_hill = whStructured;
  }

  // 添加汇总信息
  ms._summary = {
    total_bookmakers: validBookmakerCount,
    premium_gold_count: premiumCount,
    has_p0_data: !!(ms.pinnacle || ms.bet365),
    overall_purity: validBookmakerCount > 0 
      ? Math.round(
          (Object.values(ms)
            .filter(v => v && v.metadata)
            .reduce((sum, v) => sum + v.metadata.purity_score, 0) / validBookmakerCount)
        )
      : 0,
    data_completeness: validBookmakerCount > 0 ? 'high' : 'none'
  };

  return ms;
}

module.exports = {
  // V6.0 API-DECRYPT核心函数
  recursiveHistoryScanner,
  processOddsTimeline,
  deepParseOddsData,
  
  // V6.0 SCHEMA-DESIGN核心函数
  validatePurity,
  calculateVolatilityMetrics,
  
  // DOM提取函数
  extractOddsFromDOM,
  buildMarketSentiment,
  extractOddsArrays,
  
  // 工具函数
  findValuesByKey,
  findBookieById,
  
  // 常量
  BOOKMAKER_ID_MAP,
  ODDS_FIELD_PATTERNS
};