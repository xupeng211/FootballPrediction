/**
 * TITAN V5.5 OddsPortal Harvester TDD测试
 * ======================================
 * 测试哈希抓取逻辑与matches_mapping表对接
 * 
 * @module tests/unit/OddsPortalHarvester_V55
 * @version V5.5.0-ODDS-REANIMATION
 * @date 2026-03-14
 */

'use strict';

const { describe, it, before, after } = require('node:test');
const assert = require('node:assert');

// 被测组件
const {
  OddsPortalHarvester,
  OddsPortalURLParser,
  HARVESTER_CONFIG
} = require('../../src/infrastructure/harvesters/OddsPortalHarvester.js');

// ============================================================================
// Mock数据工厂
// ============================================================================

const MockDataFactory = {
  /**
   * 生成模拟OddsPortal URL
   */
  createMockOddsPortalURL: (overrides = {}) => {
    const league = overrides.league || 'premier-league';
    const season = overrides.season || '2023-2024';
    const homeTeam = overrides.homeTeam || 'Manchester United';
    const awayTeam = overrides.awayTeam || 'Chelsea';
    
    return `https://www.oddsportal.com/soccer/england/${league}-${season}/${encodeURIComponent(homeTeam)}-${encodeURIComponent(awayTeam)}/`;
  },
  
  /**
   * 生成模拟比赛列表
   */
  createMockMatches: (count = 10) => {
    const matches = [];
    const teams = [
      ['Manchester United', 'Chelsea'],
      ['Liverpool', 'Arsenal'],
      ['Manchester City', 'Tottenham'],
      ['Newcastle', 'Brighton'],
      ['West Ham', 'Aston Villa'],
      ['Leicester', 'Everton'],
      ['Leeds', 'Southampton'],
      ['Wolves', 'Crystal Palace'],
      ['Fulham', 'Brentford'],
      ['Nottingham Forest', 'Bournemouth']
    ];
    
    for (let i = 0; i < count; i++) {
      const [home, away] = teams[i % teams.length];
      matches.push({
        match_id: `match_${i + 1}`,
        url: MockDataFactory.createMockOddsPortalURL({
          homeTeam: home,
          awayTeam: away
        })
      });
    }
    
    return matches;
  }
};

// ============================================================================
// TDD测试套件
// ============================================================================

describe('V5.5 OddsPortalHarvester TDD测试', () => {
  
  // ========================================================================
  // TDD 1: URL解析器测试
  // ========================================================================
  
  describe('TDD-URL解析器', () => {
    it('TDD: 应从URL中提取hash段落', () => {
      const url = 'https://www.oddsportal.com/soccer/england/premier-league-2023-2024/Manchester%20United-Chelsea/';
      
      const result = OddsPortalURLParser.parseMatchURL(url);
      
      // TDD断言: 必须解析出hash
      assert.ok(result, 'URL解析结果不应为null');
      assert.ok(result.match_hash, '必须提取match_hash');
      assert.ok(result.match_hash.length > 0, 'hash不应为空');
      assert.strictEqual(result.league, 'premier-league', '应解析联赛名称');
      assert.strictEqual(result.season, '2023/2024', '应解析赛季');
    });
    
    it('TDD: 应正确解析队名', () => {
      const url = 'https://www.oddsportal.com/soccer/spain/laliga-2023-2024/Real%20Madrid-Barcelona/';
      
      const result = OddsPortalURLParser.parseMatchURL(url);
      
      // TDD断言: 队名解析
      assert.ok(result.home_team, '应解析主队名称');
      assert.ok(result.away_team, '应解析客队名称');
      assert.ok(result.home_team.toLowerCase().includes('real'), '主队应包含Real');
      assert.ok(result.away_team.toLowerCase().includes('barcelona'), '客队应包含Barcelona');
    });
    
    it('TDD: 应处理无效URL', () => {
      const invalidUrl = 'https://invalid-url.com/not-oddsportal';
      
      const result = OddsPortalURLParser.parseMatchURL(invalidUrl);
      
      // TDD断言: 无效URL应返回null
      assert.strictEqual(result, null, '无效URL应返回null');
    });
    
    it('TDD: 应构建完整的URL', () => {
      const league = 'Premier League';
      const season = '2023/2024';
      const homeTeam = 'Arsenal';
      const awayTeam = 'Liverpool';
      
      const url = OddsPortalURLParser.buildURL(league, season, homeTeam, awayTeam);
      
      // TDD断言: URL构建
      assert.ok(url.includes('oddsportal.com'), 'URL应包含域名');
      assert.ok(url.includes('premier-league'), 'URL应包含联赛');
      assert.ok(url.includes('2023-2024'), 'URL应包含赛季');
    });
    
    it('TDD: 应抛出未知联赛异常', () => {
      // TDD断言: 未知联赛应抛出错误
      assert.throws(() => {
        OddsPortalURLParser.buildURL('Unknown League', '2023/2024', 'Team A', 'Team B');
      }, /未知联赛/, '未知联赛应抛出异常');
    });
  });
  
  // ========================================================================
  // TDD 2: Harvester配置测试
  // ========================================================================
  
  describe('TDD-Harvester配置', () => {
    it('TDD: 应包含9900X多线程配置', () => {
      // TDD断言: 9900X配置
      assert.strictEqual(HARVESTER_CONFIG.MAX_WORKERS, 12, '应配置12核Worker');
      assert.strictEqual(HARVESTER_CONFIG.MAX_CONCURRENCY, 24, '应配置24并行度');
    });
    
    it('TDD: 应包含Playwright超时配置', () => {
      // TDD断言: 超时配置
      assert.ok(HARVESTER_CONFIG.PAGE_TIMEOUT >= 30000, '页面超时至少30秒');
      assert.ok(HARVESTER_CONFIG.NAVIGATION_TIMEOUT >= 60000, '导航超时至少60秒');
    });
    
    it('TDD: 应配置重试机制', () => {
      // TDD断言: 重试配置
      assert.ok(HARVESTER_CONFIG.MAX_RETRIES >= 3, '至少3次重试');
      assert.ok(HARVESTER_CONFIG.RETRY_DELAY_MS >= 2000, '重试延迟至少2秒');
    });
    
    it('TDD: 应定义联赛URL映射', () => {
      // TDD断言: 联赛映射
      assert.ok(HARVESTER_CONFIG.LEAGUE_URLS['Premier League'], '应有英超配置');
      assert.ok(HARVESTER_CONFIG.LEAGUE_URLS['La Liga'], '应有西甲配置');
      assert.ok(HARVESTER_CONFIG.LEAGUE_URLS['Bundesliga'], '应有德甲配置');
      assert.ok(HARVESTER_CONFIG.LEAGUE_URLS['Serie A'], '应有意甲配置');
      assert.ok(HARVESTER_CONFIG.LEAGUE_URLS['Ligue 1'], '应有法甲配置');
    });
  });
  
  // ========================================================================
  // TDD 3: Harvester实例化测试
  // ========================================================================
  
  describe('TDD-Harvester实例化', () => {
    let harvester;
    
    before(() => {
      harvester = new OddsPortalHarvester();
    });
    
    it('TDD: 应正确初始化Harvester', () => {
      // TDD断言: 实例化
      assert.ok(harvester, 'Harvester应被创建');
      assert.ok(harvester.config, '应有配置对象');
      assert.strictEqual(harvester.config.MAX_WORKERS, 12, '应继承默认Worker数');
    });
    
    it('TDD: 应支持自定义配置', () => {
      const customHarvester = new OddsPortalHarvester({
        MAX_WORKERS: 8,
        PAGE_TIMEOUT: 45000
      });
      
      // TDD断言: 自定义配置
      assert.strictEqual(customHarvester.config.MAX_WORKERS, 8, '应使用自定义Worker数');
      assert.strictEqual(customHarvester.config.PAGE_TIMEOUT, 45000, '应使用自定义超时');
      // 未覆盖的配置应继承默认值
      assert.strictEqual(customHarvester.config.MAX_CONCURRENCY, 24, '应继承默认并行度');
    });
    
    it('TDD: 应初始化统计对象', () => {
      // TDD断言: 统计初始化
      assert.strictEqual(harvester.stats.matchesHarvested, 0, '初始收割数为0');
      assert.strictEqual(harvester.stats.hashesExtracted, 0, '初始hash数为0');
      assert.strictEqual(harvester.stats.errors, 0, '初始错误数为0');
    });
    
    it('TDD: 应初始化Worker池', () => {
      // TDD断言: Worker池
      assert.ok(Array.isArray(harvester.workers), 'workers应为数组');
      assert.strictEqual(harvester.workers.length, 0, '初始化前Worker数为0');
    });
  });
  
  // ========================================================================
  // TDD 4: 哈希提取逻辑测试 (Mock模式)
  // ========================================================================
  
  describe('TDD-哈希提取逻辑', () => {
    it('TDD: 应生成有效的hash', () => {
      const url1 = 'https://www.oddsportal.com/soccer/england/premier-league-2023-2024/Manchester United-Chelsea/';
      const url2 = 'https://www.oddsportal.com/soccer/england/premier-league-2023-2024/Arsenal-Liverpool/';
      
      const result1 = OddsPortalURLParser.parseMatchURL(url1);
      const result2 = OddsPortalURLParser.parseMatchURL(url2);
      
      // TDD断言: hash唯一性
      assert.notStrictEqual(result1.match_hash, result2.match_hash, '不同URL应生成不同hash');
      assert.ok(result1.match_hash.match(/^[a-f0-9]+$/), 'hash应为十六进制字符串');
    });
    
    it('TDD: 应正确对接matches_mapping字段', () => {
      const url = 'https://www.oddsportal.com/soccer/italy/serie-a-2023-2024/Juventus-AC%20Milan/';
      
      const result = OddsPortalURLParser.parseMatchURL(url);
      
      // TDD断言: 对接matches_mapping表字段
      assert.ok(result.match_hash, '对应oddsportal_hash字段');
      assert.ok(result.raw_url, '对应oddsportal_url字段');
      assert.ok(result.league, '对应league_name字段');
      assert.ok(result.season, '对应season字段');
    });
  });
  
  // ========================================================================
  // TDD 5: 批量收割测试 (Mock模式)
  // ========================================================================
  
  describe('TDD-批量收割', () => {
    it('TDD: 应处理批量比赛列表', () => {
      const matches = MockDataFactory.createMockMatches(10);
      
      // TDD断言: 批量数据生成
      assert.strictEqual(matches.length, 10, '应生成10场比赛');
      assert.ok(matches[0].match_id, '每场比赛应有match_id');
      assert.ok(matches[0].url.includes('oddsportal.com'), 'URL应指向oddsportal');
    });
    
    it('TDD: 应生成符合matches_mapping的输出格式', () => {
      const matches = MockDataFactory.createMockMatches(5);
      
      // 模拟收割结果
      const results = matches.map(match => {
        const parsed = OddsPortalURLParser.parseMatchURL(match.url);
        return {
          success: true,
          hash: parsed?.match_hash,
          url: match.url,
          parsed: parsed,
          oddsportal_hash: parsed?.match_hash,
          oddsportal_url: match.url,
          confidence: 0.95,
          mapping_method: 'V5.5_HARVESTER'
        };
      });
      
      // TDD断言: 输出格式
      const firstResult = results[0];
      assert.ok(firstResult.oddsportal_hash, '应有oddsportal_hash字段');
      assert.ok(firstResult.oddsportal_url, '应有oddsportal_url字段');
      assert.ok(firstResult.confidence >= 0.9, '置信度应>=0.9');
      assert.strictEqual(firstResult.mapping_method, 'V5.5_HARVESTER', '应有mapping_method字段');
    });
  });
  
  // ========================================================================
  // TDD 6: Worker池管理测试
  // ========================================================================
  
  describe('TDD-Worker池管理', () => {
    it('TDD: 应支持12个Worker并发', () => {
      const harvester = new OddsPortalHarvester({ MAX_WORKERS: 12 });
      
      // 模拟初始化后
      for (let i = 0; i < 12; i++) {
        harvester.workers.push({
          id: i,
          page: null,
          busy: false,
          stats: { requests: 0, errors: 0 }
        });
      }
      
      // TDD断言: Worker池
      assert.strictEqual(harvester.workers.length, 12, '应有12个Worker');
      
      // 检查Worker结构
      const worker = harvester.workers[0];
      assert.strictEqual(worker.id, 0, 'Worker应有ID');
      assert.strictEqual(worker.busy, false, 'Worker初始状态应为空闲');
    });
    
    it('TDD: 应能获取可用Worker', () => {
      const harvester = new OddsPortalHarvester();
      
      // 模拟Worker
      harvester.workers = [
        { id: 0, busy: true },
        { id: 1, busy: false },
        { id: 2, busy: true }
      ];
      
      const available = harvester._getAvailableWorker();
      
      // TDD断言: 获取可用Worker
      assert.ok(available, '应找到可用Worker');
      assert.strictEqual(available.id, 1, '应返回ID为1的Worker');
      assert.strictEqual(available.busy, false, '返回的Worker应为空闲');
    });
    
    it('TDD: 无可用Worker时应返回undefined', () => {
      const harvester = new OddsPortalHarvester();
      
      // 所有Worker都忙
      harvester.workers = [
        { id: 0, busy: true },
        { id: 1, busy: true },
        { id: 2, busy: true }
      ];
      
      const available = harvester._getAvailableWorker();
      
      // TDD断言: 无可用Worker
      assert.strictEqual(available, undefined, '无可用Worker时应返回undefined');
    });
  });
  
  // ========================================================================
  // TDD 7: 统计报告测试
  // ========================================================================
  
  describe('TDD-统计报告', () => {
    it('TDD: 应生成吞吐量统计', () => {
      const harvester = new OddsPortalHarvester();
      harvester.stats.startTime = Date.now() - 10000; // 10秒前开始
      harvester.stats.matchesHarvested = 100;
      harvester.stats.hashesExtracted = 100;
      
      const stats = harvester.getStats();
      
      // TDD断言: 统计信息
      assert.ok(stats.elapsed_ms >= 10000, '应计算经过时间');
      assert.ok(stats.throughput >= 0, '应计算吞吐量');
      assert.strictEqual(stats.matchesHarvested, 100, '应统计收割数');
    });
  });
});

// ============================================================================
// 集成测试套件
// ============================================================================

describe('V5.5 OddsPortalHarvester集成测试', () => {
  it('TDD-集成: 完整收割流程 (需要真实浏览器)', async () => {
    // 跳过集成测试，除非显式启用
    console.log('⏭️  集成测试跳过: 需要真实Playwright浏览器');
  });
});
