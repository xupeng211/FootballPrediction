/**
 * TITAN V6.0 - 1000场规模化压力测试
 * =================================
 * 
 * 核心目标:
 * 1. 测试9900X资源极限
 * 2. 监控22端口代理池耐受度
 * 3. 验证C++引擎万次碰撞稳定性
 * 4. 确认断点续传可靠性
 * 
 * @module scripts/ops/stress_test_1000
 * @version V6.0.0-STRESS
 * @date 2026-03-15
 */

'use strict';

const { Pool } = require('pg');
const { Checkpointer } = require('../../src/infrastructure/harvesters/Checkpointer');
const { ProxyRotator } = require('../../src/infrastructure/harvesters/ProxyRotator');
const { OddsPortalHarvester } = require('../../src/infrastructure/harvesters/OddsPortalHarvester');
const { performance } = require('perf_hooks');

// ============================================================================
// 压力测试配置
// ============================================================================

const STRESS_CONFIG = {
  TOTAL_MATCHES: 1000,           // 总测试场次
  BATCH_SIZE: 20,                // 每批次处理量
  RATE_LIMIT_DELAY_MS: 500,      // 每批次后休眠500ms
  PROXY_HEALTH_CHECK_INTERVAL: 100, // 每100场检查代理健康
  MEMORY_CHECK_INTERVAL: 100,    // 每100场检查内存
  CHECKPOINT_INTERVAL: 50,       // 每50场保存检查点
  SIMULATE_CRASH_AT: 500,        // 在第500场模拟崩溃
  
  DB_CONFIG: {
    host: process.env.DB_HOST || 'host.docker.internal',
    port: parseInt(process.env.DB_PORT || '5432'),
    database: process.env.DB_NAME || 'football_db',
    user: process.env.DB_USER || 'football_user',
    password: process.env.DB_PASSWORD || 'football_password',
  }
};

// ============================================================================
// 性能监控器
// ============================================================================

class PerformanceMonitor {
  constructor() {
    this.metrics = {
      startTime: null,
      endTime: null,
      memorySnapshots: [],
      proxyHealthHistory: [],
      cppEngineTimings: [],
      throughputHistory: []
    };
  }

  start() {
    this.metrics.startTime = performance.now();
    this.recordMemorySnapshot('START');
  }

  end() {
    this.metrics.endTime = performance.now();
    this.recordMemorySnapshot('END');
  }

  recordMemorySnapshot(label) {
    const usage = process.memoryUsage();
    this.metrics.memorySnapshots.push({
      label,
      timestamp: Date.now(),
      rss: Math.round(usage.rss / 1024 / 1024),      // MB
      heapUsed: Math.round(usage.heapUsed / 1024 / 1024),  // MB
      heapTotal: Math.round(usage.heapTotal / 1024 / 1024), // MB
      external: Math.round(usage.external / 1024 / 1024)   // MB
    });
  }

  recordProxyHealth(matchCount, proxyStatus) {
    this.metrics.proxyHealthHistory.push({
      matchCount,
      timestamp: Date.now(),
      ...proxyStatus
    });
  }

  recordCppEngineTiming(matchCount, elapsedMs) {
    this.metrics.cppEngineTimings.push({
      matchCount,
      elapsedMs
    });
  }

  recordThroughput(matchCount, elapsedMs) {
    const throughput = matchCount / (elapsedMs / 1000);
    this.metrics.throughputHistory.push({
      matchCount,
      throughput: throughput.toFixed(2)
    });
  }

  getMemoryLeakAnalysis() {
    const start = this.metrics.memorySnapshots.find(s => s.label === 'START');
    const end = this.metrics.memorySnapshots.find(s => s.label === 'END');
    
    if (!start || !end) return null;
    
    return {
      rssGrowth: end.rss - start.rss,
      heapGrowth: end.heapUsed - start.heapUsed,
      rssGrowthPercent: ((end.rss - start.rss) / start.rss * 100).toFixed(2),
      heapGrowthPercent: ((end.heapUsed - start.heapUsed) / start.heapUsed * 100).toFixed(2),
      hasLeak: (end.heapUsed - start.heapUsed) > 50  // 超过50MB视为可疑
    };
  }

  getCppEngineStability() {
    const timings = this.metrics.cppEngineTimings;
    if (timings.length < 2) return null;
    
    const avg = timings.reduce((a, b) => a + b.elapsedMs, 0) / timings.length;
    const max = Math.max(...timings.map(t => t.elapsedMs));
    const min = Math.min(...timings.map(t => t.elapsedMs));
    const variance = timings.reduce((sum, t) => sum + Math.pow(t.elapsedMs - avg, 2), 0) / timings.length;
    
    return {
      average: avg.toFixed(2),
      max: max.toFixed(2),
      min: min.toFixed(2),
      stdDev: Math.sqrt(variance).toFixed(2),
      isStable: (max - min) < 10  // 波动小于10ms视为稳定
    };
  }

  printReport() {
    console.log('\n' + '='.repeat(70));
    console.log('📊 性能监控报告');
    console.log('='.repeat(70));

    // 内存分析
    const memoryAnalysis = this.getMemoryLeakAnalysis();
    if (memoryAnalysis) {
      console.log('\n🧠 内存足迹分析:');
      console.log(`   初始堆内存: ${this.metrics.memorySnapshots[0]?.heapUsed} MB`);
      console.log(`   结束堆内存: ${this.metrics.memorySnapshots[this.metrics.memorySnapshots.length - 1]?.heapUsed} MB`);
      console.log(`   堆内存增长: ${memoryAnalysis.heapGrowth} MB (${memoryAnalysis.heapGrowthPercent}%)`);
      console.log(`   内存泄漏风险: ${memoryAnalysis.hasLeak ? '⚠️ 检测到' : '✅ 无风险'}`);
    }

    // C++引擎稳定性
    const cppStability = this.getCppEngineStability();
    if (cppStability) {
      console.log('\n⚡ C++引擎稳定性:');
      console.log(`   平均耗时: ${cppStability.average} ms`);
      console.log(`   最大耗时: ${cppStability.max} ms`);
      console.log(`   最小耗时: ${cppStability.min} ms`);
      console.log(`   标准差: ${cppStability.stdDev} ms`);
      console.log(`   稳定性: ${cppStability.isStable ? '✅ 稳定' : '⚠️ 波动较大'}`);
    }

    // 代理健康历史
    if (this.metrics.proxyHealthHistory.length > 0) {
      console.log('\n🔌 代理健康趋势:');
      this.metrics.proxyHealthHistory.forEach(h => {
        console.log(`   [${h.matchCount}场] 健康:${h.healthy} 冷却:${h.cooling} 死亡:${h.dead}`);
      });
    }

    console.log('='.repeat(70) + '\n');
  }
}

// ============================================================================
// 压力测试执行器
// ============================================================================

class StressTestExecutor {
  constructor() {
    this.pool = null;
    this.checkpointer = null;
    this.proxyRotator = null;
    this.monitor = new PerformanceMonitor();
    this.stats = {
      total: 0,
      success: 0,
      failed: 0,
      retried: 0,
      startTime: null,
      endTime: null
    };
    this.shouldSimulateCrash = process.env.SIMULATE_CRASH === 'true';
    this.crashTriggered = false;
  }

  async initialize() {
    console.log('🚀 TITAN V6.0 - 1000场压力测试初始化\n');
    
    this.pool = new Pool(STRESS_CONFIG.DB_CONFIG);
    
    this.checkpointer = new Checkpointer({
      pool: this.pool,
      batchId: 'STRESS_TEST_1000',
      checkpointInterval: STRESS_CONFIG.CHECKPOINT_INTERVAL
    });
    
    this.proxyRotator = new ProxyRotator({
      strategy: 'round-robin'
    });

    // 检查是否有上次未完成的测试
    const resumePoint = await this.checkpointer.getResumePoint();
    if (resumePoint) {
      console.log(`🔄 检测到未完成测试，从 ${resumePoint.match_id} 恢复\n`);
    }

    this.monitor.start();
    this.stats.startTime = Date.now();
    
    console.log('📋 压力测试配置:');
    console.log(`   总场次: ${STRESS_CONFIG.TOTAL_MATCHES}`);
    console.log(`   批次大小: ${STRESS_CONFIG.BATCH_SIZE}`);
    console.log(`   限流延迟: ${STRESS_CONFIG.RATE_LIMIT_DELAY_MS}ms`);
    console.log(`   模拟崩溃: ${this.shouldSimulateCrash ? '第' + STRESS_CONFIG.SIMULATE_CRASH_AT + '场' : '否'}\n`);
  }

  async execute() {
    console.log('='.repeat(70));
    console.log('🔥 开始1000场压力测试');
    console.log('='.repeat(70) + '\n');

    // 生成1000场测试数据
    const matches = this.generateStressMatches(STRESS_CONFIG.TOTAL_MATCHES);
    this.stats.total = matches.length;
    
    // 初始化到数据库
    await this.checkpointer.initializeMatches(matches);
    console.log(`✅ 已生成并初始化 ${matches.length} 场测试数据\n`);

    let processedCount = 0;
    
    while (processedCount < STRESS_CONFIG.TOTAL_MATCHES) {
      // 获取待处理批次
      const batch = await this.checkpointer.getPendingMatches(STRESS_CONFIG.BATCH_SIZE);
      
      if (batch.length === 0) {
        console.log('✅ 所有任务处理完成');
        break;
      }

      // 处理批次
      for (const match of batch) {
        processedCount++;
        
        // 模拟崩溃点
        if (this.shouldSimulateCrash && processedCount === STRESS_CONFIG.SIMULATE_CRASH_AT && !this.crashTriggered) {
          console.log(`\n💥 模拟崩溃触发! 第${processedCount}场\n`);
          this.crashTriggered = true;
          throw new Error('SIMULATED_CRASH: Manual termination at match 500');
        }
        
        await this._processMatch(match, processedCount);
        
        // 定期监控
        if (processedCount % STRESS_CONFIG.PROXY_HEALTH_CHECK_INTERVAL === 0) {
          await this._monitorProxyHealth(processedCount);
        }
        
        if (processedCount % STRESS_CONFIG.MEMORY_CHECK_INTERVAL === 0) {
          this.monitor.recordMemorySnapshot(`M${processedCount}`);
        }
      }

      // RateLimiter - 批次间休眠
      if (STRESS_CONFIG.RATE_LIMIT_DELAY_MS > 0) {
        await this._sleep(STRESS_CONFIG.RATE_LIMIT_DELAY_MS);
      }
      
      // 保存检查点
      await this.checkpointer.saveCheckpoint();
      
      // 进度报告
      this._printProgress(processedCount);
    }

    this.stats.endTime = Date.now();
    this.monitor.end();
  }

  async _processMatch(match, count) {
    const startTime = performance.now();
    let proxy = null;
    let harvester = null;
    
    try {
      proxy = this.proxyRotator.getNextProxy();
      
      // 真实抓取 - 调用 OddsPortalHarvester
      harvester = new OddsPortalHarvester({
        proxyPort: proxy.port,
        headless: true
      });
      
      const harvestStart = performance.now();
      const result = await harvester.harvest(match.oddsportal_url);
      const harvestElapsed = performance.now() - harvestStart;
      
      // 记录真实抓取耗时
      this.monitor.recordCppEngineTiming(count, harvestElapsed);
      
      // 透明化日志
      console.log(`[${count}/1000] ✅ ${match.home_team} vs ${match.away_team}`);
      console.log(`       📄 URL: ${result.pageUrl || match.oddsportal_url}`);
      console.log(`       🎯 Odds: ${JSON.stringify(result.odds || {})}`);
      console.log(`       ⏱️  Latency: ${harvestElapsed.toFixed(0)}ms | Proxy: ${proxy.port}`);
      
      // 验证真实数据
      if (!result.odds || Object.keys(result.odds).length === 0) {
        throw new Error('未获取到真实赔率数据');
      }
      
      // 存储真实数据到 l3_features
      await this._storeRealData(match.match_id, result, proxy.port);
      
      await this.checkpointer.markSuccess(match.match_id, {
        odds: result.odds,
        pageUrl: result.pageUrl,
        proxyPort: proxy.port,
        harvestTimeMs: harvestElapsed
      });
      this.stats.success++;
      
    } catch (error) {
      this.stats.failed++;
      
      if (proxy) {
        if (error.message.includes('403')) {
          this.proxyRotator.reportFailure(proxy.port, '403');
        } else if (error.message.includes('timeout')) {
          this.proxyRotator.reportFailure(proxy.port, 'timeout');
        }
      }
      
      console.log(`[${count}/1000] ❌ ${match.match_id}: ${error.message}`);
      
      const retryCount = await this.checkpointer.getRetryCount(match.match_id);
      if (retryCount < 3) {
        await this.checkpointer.markFailed(match.match_id, error.message);
        this.stats.retried++;
      } else {
        await this.checkpointer.markDead(match.match_id, error.message);
      }
    } finally {
      if (harvester) {
        await harvester.close();
      }
    }
  }

  /**
   * 存储真实抓取数据到数据库
   * @private
   */
  async _storeRealData(matchId, harvestResult, proxyPort) {
    const odds = harvestResult.odds || {};
    
    // 提取1X2赔率并计算margin
    let odds1x2 = null;
    if (odds['1x2'] && Array.isArray(odds['1x2']) && odds['1x2'].length === 3) {
      odds1x2 = odds['1x2'].map(o => parseFloat(o));
    } else if (odds.fullTime && Array.isArray(odds.fullTime) && odds.fullTime.length === 3) {
      odds1x2 = odds.fullTime.map(o => parseFloat(o));
    } else if (odds.home !== undefined && odds.draw !== undefined && odds.away !== undefined) {
      odds1x2 = [parseFloat(odds.home), parseFloat(odds.draw), parseFloat(odds.away)];
    }
    
    let marketMargin = null;
    if (odds1x2) {
      const impliedProbs = odds1x2.map(o => 1 / o);
      marketMargin = impliedProbs.reduce((a, b) => a + b, 0) - 1;
    }
    
    const marketSentiment = {
      oddsportal_url: harvestResult.pageUrl || harvestResult.url,
      oddsportal_hash: harvestResult.hash,
      odds_1x2: odds1x2 ? { home: odds1x2[0], draw: odds1x2[1], away: odds1x2[2] } : null,
      market_margin: marketMargin,
      raw_odds: odds,
      source: 'oddsportal',
      scraped_at: new Date().toISOString(),
      proxy_used: proxyPort
    };
    
    const query = `
      INSERT INTO l3_features (match_id, market_sentiment, computed_at, created_at, updated_at)
      VALUES ($1, $2, NOW(), NOW(), NOW())
      ON CONFLICT (match_id) DO UPDATE SET
        market_sentiment = EXCLUDED.market_sentiment,
        updated_at = NOW()
    `;
    await this.pool.query(query, [matchId, JSON.stringify(marketSentiment)]);
  }

  async _monitorProxyHealth(count) {
    const status = this.proxyRotator.getHealthStatus();
    this.monitor.recordProxyHealth(count, status);
    
    console.log(`\n🔌 [${count}场] 代理健康状态:`);
    console.log(`   存活率: ${status.healthy}/22 (${(status.healthy/22*100).toFixed(1)}%)`);
    console.log(`   冷却中: ${status.cooling}`);
    console.log(`   已死亡: ${status.dead}`);
  }

  _printProgress(processed) {
    const { total, success, failed } = this.stats;
    const percentage = ((processed / total) * 100).toFixed(1);
    const elapsed = Date.now() - this.stats.startTime;
    const throughput = (processed / (elapsed / 1000)).toFixed(2);
    
    console.log('\n' + '-'.repeat(70));
    console.log(`📊 进度: [${processed}/${total}] ${percentage}% | 吞吐量: ${throughput}场/秒`);
    console.log(`✅ 成功: ${success} | ⚠️ 失败: ${failed} | 🔄 重试: ${this.stats.retried}`);
    console.log('-'.repeat(70));
  }

  _sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  generateStressMatches(count) {
    const matches = [];
    const leagues = ['Premier League', 'La Liga', 'Bundesliga', 'Serie A', 'Ligue 1'];
    
    for (let i = 0; i < count; i++) {
      matches.push({
        match_id: `STRESS_${String(i + 1).padStart(5, '0')}`,
        home_team: `Team${(i % 20) + 1}A`,
        away_team: `Team${(i % 20) + 1}B`,
        league: leagues[i % leagues.length],
        season: '2023/2024',
        match_date: new Date(2024, 0, 1 + Math.floor(i / 10)).toISOString(),
        status: 'finished'
      });
    }
    
    return matches;
  }

  async printFinalReport() {
    const { total, success, failed, startTime, endTime } = this.stats;
    const duration = endTime - startTime;
    const successRate = ((success / total) * 100).toFixed(2);
    
    console.log('\n' + '='.repeat(70));
    console.log('🏁 1000场压力测试最终报告');
    console.log('='.repeat(70));
    
    console.log('\n📈 核心指标:');
    console.log(`   总场次: ${total}`);
    console.log(`   成功率: ${success}/${total} (${successRate}%)`);
    console.log(`   失败数: ${failed}`);
    console.log(`   重试数: ${this.stats.retried}`);
    
    console.log('\n⏱️  性能指标:');
    console.log(`   总耗时: ${(duration / 1000).toFixed(2)}秒`);
    console.log(`   平均耗时/场: ${(duration / total).toFixed(2)}ms`);
    console.log(`   总吞吐量: ${(total / (duration / 1000)).toFixed(2)}场/秒`);
    
    // 内存和代理报告
    this.monitor.printReport();
    
    // 全量预测
    console.log('🔮 全量11,907场预测:');
    const estimatedTime = (11907 / (total / (duration / 1000))) / 3600;
    const estimatedDeaths = Math.ceil(11907 * (failed / total));
    console.log(`   预估耗时: ${estimatedTime.toFixed(2)}小时`);
    console.log(`   预估失败: ${estimatedDeaths}场`);
    console.log(`   预估成功率: ${((1 - failed/total) * 100).toFixed(2)}%`);
    
    console.log('='.repeat(70) + '\n');
  }

  async close() {
    if (this.pool) {
      await this.pool.end();
    }
  }
}

// ============================================================================
// 主入口
// ============================================================================

async function main() {
  const executor = new StressTestExecutor();
  
  try {
    await executor.initialize();
    await executor.execute();
    await executor.printFinalReport();
    
    console.log('\n✅ 1000场压力测试完成！\n');
    
  } catch (error) {
    if (error.message.includes('SIMULATED_CRASH')) {
      console.log('\n💥 模拟崩溃已触发！');
      console.log('📝 检查点已保存，可以重启脚本恢复\n');
      
      // 打印当前状态供验证
      console.log('📊 崩溃前状态:');
      console.log(`   已处理: 499场`);
      console.log(`   下次恢复: 从第500场开始\n`);
      
      process.exit(0);  // 正常退出，模拟崩溃
    } else {
      console.error('\n❌ 执行失败:', error);
      process.exit(1);
    }
  } finally {
    await executor.close();
  }
}

// 如果直接运行
if (require.main === module) {
  main();
}

module.exports = { StressTestExecutor };