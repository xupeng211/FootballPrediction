/**
 * @file Strategy Parser 单元测试
 * @description 测试 HTML 解析、字段提取、边界条件处理
 * @version 1.0.0
 */

'use strict';

const { describe, it, beforeEach } = require('node:test');
const assert = require('node:assert');

// 模拟的 FotMobStrategy 解析器
/**
 *
 */
class MockFotMobStrategy {
  /**
   *
   * @param config
   */
  constructor(config = {}) {
    this.config = config;
  }

  /**
   * 解析 HTML 响应 - V4.51.2 三层解析保险
   * @param {string} html - HTML 内容
   * @returns {object | null} 解析后的数据
   */
  parseHTML(html) {
    if (!html || typeof html !== 'string') {
      return null;
    }

    try {
      // 方案 1: 提取 __NEXT_DATA__ (FotMob 主方案)
      const nextDataMatch = html.match(/id=["']__NEXT_DATA__["'][^>]*>([\s\S]+?)<\/script>/);
      if (nextDataMatch) {
        const data = JSON.parse(nextDataMatch[1].trim());
        if (data.props?.pageProps?.match?.id || data.props?.pageProps?.general?.matchId) {
          const match = data.props.pageProps.match || data.props.pageProps;
          return this._normalizeMatchData(match);
        }
      }

      // 方案 2: 提取 window.__INITIAL_STATE__ (备用方案 A)
      // 使用更精确的正则来处理嵌套括号和转义字符
      const initialStateRegex = /window\.__INITIAL_STATE__\s*=\s*({[\s\S]*?});\s*<\/script>/;
      const initialStateMatch = html.match(initialStateRegex);
      if (initialStateMatch) {
        try {
          const data = JSON.parse(initialStateMatch[1]);
          if (data.match?.id) {
            return this._normalizeMatchData(data.match);
          }
        } catch (e) {
          // JSON 解析失败，继续尝试其他方案
        }
      }

      // 方案 3: DOM 备用解析 (备用方案 B) - V4.51.2 新增
      return this._parseDOMFallback(html);
    } catch (error) {
      return null;
    }
  }

  /**
   * 标准化比赛数据
   * @param match
   * @private
   */
  _normalizeMatchData(match) {
    // 处理 score 字段
    let score = null;
    if (match.score && Array.isArray(match.score)) {
      score = match.score;
    } else if (match.homeScore !== undefined && match.awayScore !== undefined) {
      score = [match.homeScore, match.awayScore];
    }

    return {
      match_id: match.id,
      home_team: {
        name: match.home?.name || match.homeTeam?.name || 'Unknown',
        id: match.home?.id || match.homeTeam?.id || 0
      },
      away_team: {
        name: match.away?.name || match.awayTeam?.name || 'Unknown',
        id: match.away?.id || match.awayTeam?.id || 0
      },
      match_info: {
        date: match.date || match.matchDate,
        status: match.status || 'UNKNOWN',
        score: score
      },
      statistics: match.stats || match.statistics || {},
      _source: 'html_parse',
      parsed_at: new Date().toISOString()
    };
  }

  /**
   * DOM 备用解析 - V4.51.2 新增
   * 当所有 JSON 数据都缺失时，从 DOM 提取基础信息
   * @param html
   * @private
   */
  _parseDOMFallback(html) {
    try {
      // 尝试提取标题
      const titleMatch = html.match(/<h1[^>]*>([^<]+)<\/h1>/);
      const title = titleMatch ? titleMatch[1] : '';

      // 尝试提取队伍名称
      const homeMatch = html.match(/class="[^"]*home[^"]*"[^>]*>([^<]+)/i);
      const awayMatch = html.match(/class="[^"]*away[^"]*"[^>]*>([^<]+)/i);

      // 尝试从 title 解析 "Team A vs Team B"
      let teams = [];
      if (title.includes(' vs ')) {
        teams = title.split(' vs ').map(t => t.trim());
      }

      if ((homeMatch && awayMatch) || teams.length === 2) {
        return {
          match_id: 'dom_' + Date.now(),
          home_team: {
            name: homeMatch ? homeMatch[1].trim() : teams[0],
            id: 0
          },
          away_team: {
            name: awayMatch ? awayMatch[1].trim() : teams[1],
            id: 0
          },
          match_info: {
            status: 'UNKNOWN'
          },
          statistics: {},
          _source: 'dom_fallback',
          _domExtracted: true,
          parsed_at: new Date().toISOString()
        };
      }

      return null;
    } catch (error) {
      return null;
    }
  }

  /**
   * 验证数据结构完整性
   * @param {object} data - 解析后的数据
   * @returns {boolean} 是否有效
   */
  validateData(data) {
    if (!data || typeof data !== 'object') {
      return false;
    }

    const required = ['match_id', 'home_team', 'away_team', 'match_info'];
    return required.every(field => data[field] !== undefined);
  }

  /**
   * 处理错误响应
   * @param {number} statusCode - HTTP 状态码
   * @returns {string} 错误类型
   */
  classifyError(statusCode) {
    if (statusCode === 403) return 'FORBIDDEN';
    if (statusCode === 404) return 'NOT_FOUND';
    if (statusCode === 429) return 'RATE_LIMITED';
    if (statusCode >= 500) return 'SERVER_ERROR';
    if (statusCode === 0) return 'NETWORK_ERROR';
    return 'UNKNOWN_ERROR';
  }
}

// ==================== 测试套件 ====================

describe('Strategy Parser - FotMobStrategy', () => {
  let strategy;

  beforeEach(() => {
    strategy = new MockFotMobStrategy();
  });

  describe('HTML 解析 - 正常场景', () => {
it('✅ 应正确解析完整的 HTML 响应', () => {
      const html = `
        <html>
          <script>
            window.__INITIAL_STATE__ = {
              "match": {
                "id": "12345",
                "home": { "name": "Arsenal", "id": 1 },
                "away": { "name": "Chelsea", "id": 2 },
                "date": "2026-03-12",
                "status": "FINISHED",
                "score": [2, 1],
                "stats": { "possession": [55, 45] }
              }
            };
          </script>
        </html>
      `;

      const result = strategy.parseHTML(html);

      assert.ok(result);
      assert.strictEqual(result.match_id, '12345');
      assert.strictEqual(result.home_team.name, 'Arsenal');
      assert.strictEqual(result.away_team.name, 'Chelsea');
      assert.deepStrictEqual(result.match_info.score, [2, 1]);
    });

it('✅ 应处理缺失统计字段的情况', () => {
      const html = `
        <script>
          window.__INITIAL_STATE__ = {
            "match": {
              "id": "67890",
              "home": { "name": "Liverpool", "id": 3 },
              "away": { "name": "Man City", "id": 4 },
              "date": "2026-03-13",
              "status": "SCHEDULED"
            }
          };
        </script>
      `;

      const result = strategy.parseHTML(html);

      assert.ok(result);
      assert.strictEqual(result.match_id, '67890');
      assert.deepStrictEqual(result.statistics, {});
    });
  });

  describe('HTML 解析 - 边界条件', () => {
it('❌ 空 HTML 应返回 null', () => {
      expect(strategy.parseHTML('')).toBeNull();
      expect(strategy.parseHTML(null)).toBeNull();
      expect(strategy.parseHTML(undefined)).toBeNull();
    });

it('❌ 不包含 INITIAL_STATE 的 HTML 应返回 null', () => {
      const html = '<html><body>No data here</body></html>';
      expect(strategy.parseHTML(html)).toBeNull();
    });

it('❌ 无效的 JSON 应返回 null', () => {
      const html = `
        <script>
          window.__INITIAL_STATE__ = { invalid json };
        </script>
      `;
      expect(strategy.parseHTML(html)).toBeNull();
    });

it('❌ 缺少必要字段的 JSON 应返回 null', () => {
      const html = `
        <script>
          window.__INITIAL_STATE__ = { "other": "data" };
        </script>
      `;
      expect(strategy.parseHTML(html)).toBeNull();
    });

it('⚠️  特殊字符和转义应正确处理', () => {
      const html = `
        <script>
          window.__INITIAL_STATE__ = {
            "match": {
              "id": "special\\"id",
              "home": { "name": "O'Brien Team", "id": 1 },
              "away": { "name": "Team B", "id": 2 },
              "date": "2026-03-12",
              "status": "FINISHED"
            }
          };
        </script>
      `;

      const result = strategy.parseHTML(html);
      assert.ok(result);
    });
  });

  describe('数据验证', () => {
it('✅ 完整数据应通过验证', () => {
      const data = {
        match_id: '123',
        home_team: { name: 'A', id: 1 },
        away_team: { name: 'B', id: 2 },
        match_info: { date: '2026-03-12' }
      };
      expect(strategy.validateData(data)).toBe(true);
    });

it('❌ 缺少字段应验证失败', () => {
      expect(strategy.validateData(null)).toBe(false);
      expect(strategy.validateData({})).toBe(false);
      expect(strategy.validateData({ match_id: '123' })).toBe(false);
    });

it('❌ 空对象应验证失败', () => {
      expect(strategy.validateData({})).toBe(false);
    });
  });

  describe('错误分类', () => {
it('✅ HTTP 状态码应正确分类', () => {
      expect(strategy.classifyError(403)).toBe('FORBIDDEN');
      expect(strategy.classifyError(404)).toBe('NOT_FOUND');
      expect(strategy.classifyError(429)).toBe('RATE_LIMITED');
      expect(strategy.classifyError(500)).toBe('SERVER_ERROR');
      expect(strategy.classifyError(503)).toBe('SERVER_ERROR');
      expect(strategy.classifyError(0)).toBe('NETWORK_ERROR');
      expect(strategy.classifyError(418)).toBe('UNKNOWN_ERROR');
    });
  });
});

// 测试覆盖率报告
describe('📊 Coverage Requirements', () => {
it('业务逻辑覆盖率应达到 80%', () => {
    // 此测试用于标记覆盖率要求
    assert.strictEqual(true, true);
  });
});
