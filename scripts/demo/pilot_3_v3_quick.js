/**
 * TITAN V6.0 PRECISION-LOCK - 3 Match Quick Test
 * ==============================================
 * 
 * 快速验证V3 PRECISION-LOCK: Pinnacle和Bet365强制提取
 * 
 * @module scripts/ops/pilot_3_v3_quick
 * @version V6.0-PRECISION-LOCK
 * @date 2026-03-16
 */

'use strict';

const { OddsPortalHarvester } = require('../../src/infrastructure/harvesters/OddsPortalHarvester');
const { ProxyRotator } = require('../../src/infrastructure/harvesters/ProxyRotator');

const THREE_MATCHES = [
  { match_id: 'V3_TEST_001', home: 'Arsenal', away: 'Bournemouth', url: 'https://www.oddsportal.com/football/england/premier-league/arsenal-bournemouth-jcHwYvNG/' },
  { match_id: 'V3_TEST_002', home: 'Liverpool', away: 'Tottenham', url: 'https://www.oddsportal.com/football/england/premier-league/liverpool-tottenham-dtZvdoAa/' },
  { match_id: 'V3_TEST_003', home: 'Chelsea', away: 'Man City', url: 'https://www.oddsportal.com/football/england/premier-league/chelsea-manchester-city-bLP5yET8/' }
];

async function pilot3V3() {
  console.log('\n🔒 TITAN V6.0 PRECISION-LOCK - 3 Match Quick Test\n');

  const proxyRotator = new ProxyRotator({ strategy: 'round-robin' });
  const harvester = new OddsPortalHarvester({ headless: true });
  
  const results = [];

  for (let i = 0; i < THREE_MATCHES.length; i++) {
    const match = THREE_MATCHES[i];
    const proxy = proxyRotator.getNextProxy();

    console.log(`\n[${i + 1}/3] 🔒 ${match.home} vs ${match.away}`);
    console.log(`       🔌 Proxy: ${proxy.port}`);

    try {
      const result = await harvester.harvest(match.url);
      const ms = result.market_sentiment;

      // V3 PRECISION-LOCK验证
      console.log(`       🔒 _v3Lock: ${ms?._v3Lock ? '✅' : '❌'}`);
      console.log(`       🔒 _averageDisabled: ${ms?._averageDisabled ? '✅' : '❌'}`);
      console.log(`       🔒 _whitelist: [${ms?._whitelist?.join(', ') || 'N/A'}]`);
      
      // Pinnacle验证
      const hasPinnacle = ms?.pinnacle_odds?.closing?.length === 3;
      console.log(`       🔒 Pinnacle: ${hasPinnacle ? '✅' : '❌'}`);
      if (hasPinnacle) {
        console.log(`       💰 Pinnacle Closing: ${ms.pinnacle_odds.closing.join(' | ')}`);
        if (ms.pinnacle_odds.opening) {
          console.log(`       📈 Pinnacle Opening: ${ms.pinnacle_odds.opening.join(' | ')}`);
        }
      }

      // Bet365验证
      const hasBet365 = ms?.bet365_odds?.closing?.length === 3;
      console.log(`       🔒 Bet365: ${hasBet365 ? '✅' : '❌'}`);
      if (hasBet365) {
        console.log(`       💰 Bet365 Closing: ${ms.bet365_odds.closing.join(' | ')}`);
        if (ms.bet365_odds.opening) {
          console.log(`       📈 Bet365 Opening: ${ms.bet365_odds.opening.join(' | ')}`);
        }
      }

      // 价差计算
      if (hasPinnacle && hasBet365) {
        const pin = ms.pinnacle_odds.closing.map(o => parseFloat(o));
        const b365 = ms.bet365_odds.closing.map(o => parseFloat(o));
        const spread = [
          Math.abs(pin[0] - b365[0]).toFixed(3),
          Math.abs(pin[1] - b365[1]).toFixed(3),
          Math.abs(pin[2] - b365[2]).toFixed(3)
        ];
        console.log(`       📊 Spread (Pinnacle vs Bet365): ${spread.join(' | ')}`);
      }

      results.push({
        match: `${match.home} vs ${match.away}`,
        hasPinnacle,
        hasBet365,
        v3Lock: ms?._v3Lock,
        averageDisabled: ms?._averageDisabled,
        status: hasPinnacle || hasBet365 ? 'success' : 'failed'
      });

    } catch (error) {
      console.log(`       ❌ Error: ${error.message}`);
      results.push({
        match: `${match.home} vs ${match.away}`,
        error: error.message,
        status: 'failed'
      });
    }

    if (i < THREE_MATCHES.length - 1) {
      await new Promise(r => setTimeout(r, 3000));
    }
  }

  await harvester.close();

  // 汇总
  console.log('\n' + '='.repeat(80));
  console.log('📊 V3 PRECISION-LOCK 汇总');
  console.log('='.repeat(80));
  
  const successCount = results.filter(r => r.status === 'success').length;
  const pinCount = results.filter(r => r.hasPinnacle).length;
  const b365Count = results.filter(r => r.hasBet365).length;

  console.log(`总场次: ${results.length}`);
  console.log(`成功: ${successCount}/${results.length}`);
  console.log(`Pinnacle找到: ${pinCount}/${results.length} (${(pinCount/results.length*100).toFixed(0)}%)`);
  console.log(`Bet365找到: ${b365Count}/${results.length} (${(b365Count/results.length*100).toFixed(0)}%)`);
  console.log(`V3 Lock: ${results.filter(r => r.v3Lock).length}/${results.length}`);
  console.log(`Average禁用: ${results.filter(r => r.averageDisabled).length}/${results.length}`);
  console.log('='.repeat(80));

  return results;
}

// 运行
if (require.main === module) {
  pilot3V3().catch(console.error);
}

module.exports = { pilot3V3 };