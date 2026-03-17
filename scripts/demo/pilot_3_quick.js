/**
 * TITAN V6.0 - 3 Match Quick Pilot (Demo)
 */

'use strict';

const { Pool } = require('pg');
const { OddsPortalHarvester } = require('../../src/infrastructure/harvesters/OddsPortalHarvester');

const CONFIG = {
  DB_CONFIG: {
    host: process.env.DB_HOST || 'host.docker.internal',
    port: parseInt(process.env.DB_PORT || '5432'),
    database: process.env.DB_NAME || 'football_db',
    user: process.env.DB_USER || 'football_user',
    password: process.env.DB_PASSWORD || 'football_password',
  }
};

const PILOT_3_MATCHES = [
  { match_id: 'PILOT_20_001', url: 'https://www.oddsportal.com/football/england/premier-league/arsenal-bournemouth-jcHwYvNG/' },
  { match_id: 'PILOT_20_002', url: 'https://www.oddsportal.com/football/england/premier-league/liverpool-tottenham-dtZvdoAa/' },
  { match_id: 'PILOT_20_003', url: 'https://www.oddsportal.com/football/england/premier-league/chelsea-manchester-city-bLP5yET8/' }
];

async function pilot3() {
  console.log('\n🔥 TITAN V6.0 - 3 Match Quick Pilot\n');
  
  const pool = new Pool(CONFIG.DB_CONFIG);
  const harvester = new OddsPortalHarvester({ headless: true });
  
  const results = [];
  
  for (const match of PILOT_3_MATCHES) {
    console.log(`\n🎯 ${match.match_id}`);
    console.log(`   🔗 ${match.url}`);
    
    try {
      const result = await harvester.harvest(match.url);
      
      // 验证
      const bodyTextLength = result.odds?._diagnostic?.bodyTextLength || 0;
      const odds1x2 = result.odds?.['1x2'];
      
      if (bodyTextLength < 5000) {
        console.log(`   ❌ bodyTextLength ${bodyTextLength} < 5000`);
        results.push({ match_id: match.match_id, status: 'failed', reason: 'bodyTextLength' });
        continue;
      }
      
      if (!odds1x2 || odds1x2.length !== 3) {
        console.log(`   ❌ Missing 1x2 odds`);
        results.push({ match_id: match.match_id, status: 'failed', reason: 'no_odds' });
        continue;
      }
      
      const impliedProbs = odds1x2.map(o => 1 / parseFloat(o));
      const margin = impliedProbs.reduce((a, b) => a + b, 0) - 1;
      
      if (margin < 0.02 || margin > 0.08) {
        console.log(`   ❌ Margin ${(margin * 100).toFixed(2)}% out of range`);
        results.push({ match_id: match.match_id, status: 'failed', reason: 'margin_out_of_range' });
        continue;
      }
      
      console.log(`   ✅ Success`);
      console.log(`   💰 Odds: ${odds1x2.join(' | ')}`);
      console.log(`   📊 Margin: ${(margin * 100).toFixed(2)}%`);
      console.log(`   📝 Body: ${bodyTextLength} chars`);
      
      // 写入数据库
      const marketSentiment = result.market_sentiment || {
        match_id: match.match_id,
        oddsportal_url: result.url,
        extract_method: 'V6.0-DEEP-PARSE',
        extracted_at: new Date().toISOString(),
        odds_1x2: odds1x2,
        opening_odds: result.odds?.opening,
        closing_odds: result.odds?.closing || odds1x2,
        movement_curve: result.odds?.curve || [],
        bookmakers: result.odds?.bookmakers || {},
        _source: result.odds?._source
      };
      
      await pool.query(`
        INSERT INTO l3_features (match_id, market_sentiment, updated_at)
        VALUES ($1, $2, NOW())
        ON CONFLICT (match_id) DO UPDATE SET 
          market_sentiment = EXCLUDED.market_sentiment,
          updated_at = NOW()
      `, [match.match_id, JSON.stringify(marketSentiment)]);
      
      console.log(`   💾 Written to l3_features`);
      results.push({ match_id: match.match_id, status: 'success', odds: odds1x2, margin: (margin * 100).toFixed(2) });
      
    } catch (error) {
      console.log(`   ❌ Error: ${error.message}`);
      results.push({ match_id: match.match_id, status: 'error', reason: error.message });
    }
  }
  
  await harvester.close();
  await pool.end();
  
  console.log('\n🏁 Results:');
  results.forEach(r => {
    console.log(`   ${r.match_id}: ${r.status} ${r.odds ? '[' + r.odds.join('/') + ']' : ''}`);
  });
  
  return results;
}

pilot3().catch(console.error);
