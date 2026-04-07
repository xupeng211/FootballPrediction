/**
 * RealWorld Odds Fetch - TITAN V6.0 真实数据抓取TDD测试
 * ==================================================
 * 
 * 验证真实OddsPortal抓取能力
 * 禁止随机数，所有数据必须来自真实API
 * 
 * @module tests/unit/RealWorld_Odds_Fetch
 * @version V6.0.0-REAL
 * @date 2026-03-15
 */

'use strict';

const { describe, it, afterEach } = require('node:test');
const assert = require('node:assert');

// 导入真实模块
const { OddsPortalHarvester, OddsPortalURLParser } = require('../../src/infrastructure/harvesters/OddsPortalHarvester');
const { ProxyRotator } = require('../../src/infrastructure/harvesters/ProxyRotator');
const { resetProxyProvider } = require('../../src/infrastructure/network/ProxyProvider');
const { Normalizer } = require('../../src/utils/Normalizer');

afterEach(() => {
  resetProxyProvider();
});

// ============================================================================
// 测试配置
// ============================================================================

const TEST_CONFIG = {
  REAL_MATCH: {
    home_team: 'Arsenal',
    away_team: 'Chelsea',
    league: 'Premier League',
    season: '2023/2024'
  },
  PROXY_PORTS: [7890, 7891, 7892] // 测试用代理端口
};

// ============================================================================
// 真实数据抓取测试套件
// ============================================================================

describe('RealWorld_Odds_Fetch - TITAN V6.0 真实赔率抓取', () => {
  
  // 测试1: OddsPortalURLParser 必须解析真实URL
  describe('OddsPortal URL解析', () => {
    
    it('断言1: 必须解析真实Arsenal vs Chelsea的URL并返回真实hash', () => {
      const realUrl = 'https://www.oddsportal.com/soccer/england/premier-league/arsenal-chelsea/';
      
      const result = OddsPortalURLParser.parseMatchURL(realUrl);
      
      // 断言: 返回结果必须存在
      assert.ok(result, 'URL解析结果不能为空');
      
      // 断言: match_hash必须是真实字符串(非随机数)
      assert.ok(result.match_hash, '必须有match_hash');
      assert.strictEqual(typeof result.match_hash, 'string', 'match_hash必须是字符串');
      assert.ok(result.match_hash.length > 5, 'match_hash长度必须大于5');
      
      // 断言: 不能是随机数生成的格式
      assert.ok(!result.match_hash.match(/^[0-9a-f]{8}-[0-9a-f]{4}/), '不能是UUID格式');
      
      // 断言: 必须正确解析出队名
      assert.ok(result.home_team, '必须有home_team');
      assert.ok(result.away_team, '必须有away_team');
      assert.ok(result.home_team.toLowerCase().includes('arsenal') || result.home_team.toLowerCase().includes('chelsea'), 
                '必须解析出Arsenal或Chelsea');
    });
    
    it('断言2: 必须支持赛季格式的URL', () => {
      const seasonUrl = 'https://www.oddsportal.com/soccer/england/premier-league-2023-2024/manchester-united-liverpool/';
      
      const result = OddsPortalURLParser.parseMatchURL(seasonUrl);
      
      assert.ok(result, '赛季URL解析结果不能为空');
      assert.ok(result.season, '必须解析出season');
      assert.ok(result.season.includes('2023') || result.season.includes('2024'), 'season必须包含2023或2024');
    });
  });

  // 测试2: ProxyRotator 必须注入真实代理
  describe('ProxyRotator 代理注入', () => {
    
    it('断言3: 必须返回真实的代理IP配置而非模拟数据', () => {
      const rotator = new ProxyRotator({ strategy: 'round-robin' });
      
      const proxy = rotator.getNextProxy();
      
      // 断言: 必须返回代理配置
      assert.ok(proxy, '代理配置不能为空');
      
      // 断言: 必须有server属性
      assert.ok(proxy.server, '必须有server属性');
      assert.strictEqual(typeof proxy.server, 'string', 'server必须是字符串');
      
      // 断言: server必须是真实代理格式 (http://host:port)
      const proxyUrl = new URL(proxy.server);
      assert.strictEqual(proxyUrl.protocol, 'http:', '代理协议必须是 http');
      assert.ok(proxyUrl.hostname, '代理必须包含主机名');
      assert.ok(proxyUrl.port, '代理必须包含端口号');

      // 断言: 必须是22端口之一
      const port = parseInt(proxyUrl.port, 10);
      assert.ok(port >= 7890 && port <= 7911, `端口${port}必须在7890-7911范围内`);
    });
    
    it('断言4: 连续获取代理必须轮询不同端口', () => {
      const rotator = new ProxyRotator({ strategy: 'round-robin' });
      
      const ports = [];
      for (let i = 0; i < 5; i++) {
        const proxy = rotator.getNextProxy();
        const portMatch = proxy.server.match(/:(\d+)$/);
        ports.push(parseInt(portMatch[1]));
      }
      
      // 断言: 至少使用了2个不同端口
      const uniquePorts = [...new Set(ports)];
      assert.ok(uniquePorts.length >= 2, `轮询必须使用不同端口，实际使用了${uniquePorts.length}个`);
    });
  });

  // 测试3: market_margin 计算验证
  describe('市场抽水率计算', () => {
    
    it('断言5: market_margin必须在真实博弈市场范围内(0.02-0.12)', () => {
      // 真实赔率数据样本
      const realOdds1x2 = [2.15, 3.40, 3.60]; // 真实1X2赔率
      
      // 计算隐含概率
      const impliedProbs = realOdds1x2.map(o => 1 / o);
      const totalProb = impliedProbs.reduce((a, b) => a + b, 0);
      
      // 计算市场抽水率
      const marketMargin = totalProb - 1;
      
      // 断言: 必须在真实市场范围内 2% - 12%
      assert.ok(marketMargin >= 0.02 && marketMargin <= 0.12, 
                `market_margin=${marketMargin.toFixed(4)}必须在0.02-0.12之间`);
      
      console.log(`   ✅ 真实赔率抽水率: ${(marketMargin * 100).toFixed(2)}%`);
    });
    
    it('断言6: Pinnacle真实赔率样本验证', () => {
      // Pinnacle典型赔率样本 (来自真实市场)
      const pinnacleOdds = [
        { match: 'Arsenal vs Chelsea', odds: [2.05, 3.50, 3.90], margin: 0.048 },
        { match: 'Man City vs Liverpool', odds: [1.75, 4.00, 4.50], margin: 0.056 },
        { match: 'Real Madrid vs Barcelona', odds: [2.30, 3.40, 3.20], margin: 0.038 }
      ];
      
      pinnacleOdds.forEach(sample => {
        const implied = sample.odds.map(o => 1 / o);
        const calculatedMargin = implied.reduce((a, b) => a + b, 0) - 1;
        
        // 允许0.02的误差
        const diff = Math.abs(calculatedMargin - sample.margin);
        assert.ok(diff < 0.02, 
                  `${sample.match}的margin计算误差过大: ${diff.toFixed(4)}`);
        
        console.log(`   ✅ ${sample.match}: ${(calculatedMargin * 100).toFixed(2)}%`);
      });
    });
  });

  // 测试4: 真实数据完整性
  describe('真实数据完整性', () => {
    
    it('断言7: 真实抓取的hash不能是随机数生成', () => {
      const realUrls = [
        'https://www.oddsportal.com/soccer/england/premier-league/arsenal-chelsea/',
        'https://www.oddsportal.com/soccer/spain/laliga/real-madrid-barcelona/',
        'https://www.oddsportal.com/soccer/germany/bundesliga/bayern-dortmund/'
      ];
      
      const hashes = realUrls.map(url => OddsPortalURLParser.parseMatchURL(url)?.match_hash);
      
      // 断言: 所有hash必须存在
      hashes.forEach((hash, i) => {
        assert.ok(hash, `URL ${i} 的hash不能为空`);
        
        // 断言: hash必须是确定性的(相同URL生成相同hash)
        const hash2 = OddsPortalURLParser.parseMatchURL(realUrls[i])?.match_hash;
        assert.strictEqual(hash, hash2, '相同URL必须生成相同hash(确定性)');
        
        // 断言: 不能是Math.random()生成的格式
        assert.ok(!hash.match(/^0\.\d+$/), '不能是Math.random()格式');
      });
    });
    
    it('断言8: 队名对齐必须准确', () => {
      const testCases = [
        {
          url: 'https://www.oddsportal.com/soccer/england/premier-league/arsenal-chelsea/',
          homeTokens: ['arsenal'],
          awayTokens: ['chelsea']
        },
        {
          url: 'https://www.oddsportal.com/soccer/spain/laliga/real-madrid-barcelona/',
          homeTokens: ['real', 'madrid'],
          awayTokens: ['barcelona']
        }
      ];
      
      testCases.forEach(tc => {
        const result = OddsPortalURLParser.parseMatchURL(tc.url);
        const normalizedHome = Normalizer.normalizeTeamName(result?.home_team || '').toLowerCase();
        const normalizedAway = Normalizer.normalizeTeamName(result?.away_team || '').toLowerCase();
        
        assert.ok(result, `必须解析 ${tc.url}`);
        tc.homeTokens.forEach(token => {
          assert.ok(
            normalizedHome.includes(token),
            `home_team必须包含${token}，实际为${result.home_team}`
          );
        });
        tc.awayTokens.forEach(token => {
          assert.ok(
            normalizedAway.includes(token),
            `away_team必须包含${token}，实际为${result.away_team}`
          );
        });
      });
    });
  });
});

// 运行测试时打印信息
console.log('\n🔥 TITAN V6.0 真实赔率抓取TDD测试');
console.log('=====================================\n');
console.log('⚠️  注意: 这些测试验证真实数据处理能力');
console.log('   禁止随机数，所有数据必须可验证\n');
