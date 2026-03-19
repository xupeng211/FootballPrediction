#!/usr/bin/env node
/**
 * TITAN MONITOR - 实时健康监控与熔断触发器
 * ==========================================
 *
 * 监控维度:
 * - 数据质量 (0.2KB 空壳检测)
 * - Timeout 率 (连续失败熔断)
 * - 数据增长速率
 * - IO 性能
 *
 * @version V6.6-MONITOR
 */

'use strict';

const { Pool } = require('pg');
const { exec } = require('child_process');
const { promisify } = require('util');
const execAsync = promisify(exec);

class TitanMonitor {
  constructor() {
    this.dbPool = new Pool({
      host: process.env.DB_HOST || 'localhost',
      port: process.env.DB_PORT || 5432,
      database: process.env.DB_NAME || 'football_db',
      user: process.env.DB_USER || 'football_user',
      password: process.env.DB_PASSWORD || 'football_pass',
      max: 5
    });
    
    this.stats = {
      checkCount: 0,
      lastTotalSize: 0,
      lastCheckTime: Date.now(),
      consecutiveLowQuality: 0,
      consecutiveTimeouts: 0
    };
    
    this.circuitBreaker = {
      isOpen: false,
      lastOpenTime: null
    };
  }

  /**
   * 执行健康检查
   */
  async healthCheck() {
    this.stats.checkCount++;
    const now = Date.now();
    
    try {
      // 1. 检查最新数据质量
      const qualityCheck = await this._checkDataQuality();
      
      // 2. 检查增长速率
      const growthRate = await this._checkGrowthRate();
      
      // 3. 检查 IO 性能
      const ioStats = await this._checkIOStats();
      
      // 4. 熔断逻辑判断
      const shouldTrigger = this._evaluateCircuitBreaker(qualityCheck, growthRate);
      
      // 输出报告
      this._printReport(qualityCheck, growthRate, ioStats, shouldTrigger);
      
      if (shouldTrigger.trigger) {
        await this._triggerCircuitBreaker(shouldTrigger.reason);
      }
      
      return { qualityCheck, growthRate, ioStats, shouldTrigger };
      
    } catch (error) {
      console.error(`[MONITOR] 健康检查失败: ${error.message}`);
      return null;
    }
  }

  /**
   * 数据质量检查
   * @private
   */
  async _checkDataQuality() {
    const client = await this.dbPool.connect();
    
    try {
      // 最新 10 条数据的质量
      const latestQuery = `
        SELECT match_id, LENGTH(raw_data::text) as size, collected_at
        FROM raw_match_data
        ORDER BY collected_at DESC
        LIMIT 10
      `;
      const latest = await client.query(latestQuery);
      
      // 检测 0.2KB 级别的空壳数据 (< 1KB)
      const shellData = latest.rows.filter(r => r.size < 1024);
      
      // 检测低于 100KB 的低质量数据
      const lowQuality = latest.rows.filter(r => r.size < 102400);
      
      // 平均大小
      const avgSize = latest.rows.reduce((sum, r) => sum + parseInt(r.size), 0) / latest.rows.length;
      
      return {
        latestSamples: latest.rows,
        shellCount: shellData.length,
        lowQualityCount: lowQuality.length,
        avgSize: Math.round(avgSize),
        status: shellData.length > 0 ? 'CRITICAL' : lowQuality.length > 5 ? 'WARNING' : 'OK'
      };
      
    } finally {
      client.release();
    }
  }

  /**
   * 增长速率检查
   * @private
   */
  async _checkGrowthRate() {
    const client = await this.dbPool.connect();
    
    try {
      const now = Date.now();
      const timeDelta = (now - this.stats.lastCheckTime) / 1000; // seconds
      
      // 总数据量
      const countQuery = `SELECT COUNT(*) as total, SUM(LENGTH(raw_data::text)) as total_size FROM raw_match_data`;
      const result = await client.query(countQuery);
      const currentCount = parseInt(result.rows[0].total);
      const currentSize = parseInt(result.rows[0].total_size) || 0;
      
      // 计算速率
      const countRate = timeDelta > 0 ? (currentCount / timeDelta) * 60 : 0; // 场/min
      const sizeDelta = currentSize - this.stats.lastTotalSize;
      const dataRate = timeDelta > 0 ? (sizeDelta / timeDelta / 1024) : 0; // KB/s
      
      // 更新状态
      this.stats.lastTotalSize = currentSize;
      this.stats.lastCheckTime = now;
      
      return {
        totalMatches: currentCount,
        totalSizeMB: (currentSize / 1024 / 1024).toFixed(2),
        matchRatePerMin: countRate.toFixed(1),
        dataRateKBps: dataRate.toFixed(1),
        status: countRate < 10 ? 'SLOW' : countRate > 200 ? 'FAST' : 'NORMAL'
      };
      
    } finally {
      client.release();
    }
  }

  /**
   * IO 性能检查
   * @private
   */
  async _checkIOStats() {
    try {
      const client = await this.dbPool.connect();
      
      try {
        // PostgreSQL 统计
        const statsQuery = `
          SELECT 
            SUM(heap_blks_hit) as cache_hits,
            SUM(heap_blks_read) as disk_reads
          FROM pg_statio_user_tables
          WHERE relname = 'raw_match_data'
        `;
        const stats = await client.query(statsQuery);
        
        const hits = parseInt(stats.rows[0]?.cache_hits) || 0;
        const reads = parseInt(stats.rows[0]?.disk_reads) || 0;
        const total = hits + reads;
        const cacheHitRatio = total > 0 ? (hits / total * 100).toFixed(1) : 'N/A';
        
        return {
          cacheHitRatio: cacheHitRatio === 'N/A' ? 'N/A' : `${cacheHitRatio}%`,
          diskReads: reads,
          status: cacheHitRatio === 'N/A' ? 'UNKNOWN' : parseFloat(cacheHitRatio) > 95 ? 'EXCELLENT' : 'GOOD'
        };
        
      } finally {
        client.release();
      }
      
    } catch (error) {
      return { cacheHitRatio: 'N/A', diskReads: 0, status: 'UNKNOWN' };
    }
  }

  /**
   * 熔断判断
   * @private
   */
  _evaluateCircuitBreaker(quality, growth) {
    const reasons = [];
    
    // 1. 空壳数据熔断
    if (quality.shellCount > 0) {
      this.stats.consecutiveLowQuality++;
      if (this.stats.consecutiveLowQuality >= 3) {
        reasons.push(`连续 ${this.stats.consecutiveLowQuality} 次检测到空壳数据 (${quality.shellCount} 场)`);
      }
    } else {
      this.stats.consecutiveLowQuality = 0;
    }
    
    // 2. 低质量数据过多
    if (quality.lowQualityCount >= 8) {
      reasons.push(`低质量数据占比过高 (${quality.lowQualityCount}/10)`);
    }
    
    // 3. 增长停滞
    if (parseFloat(growth.matchRatePerMin) < 1) {
      this.stats.consecutiveTimeouts++;
      if (this.stats.consecutiveTimeouts >= 5) {
        reasons.push(`连续 ${this.stats.consecutiveTimeouts} 次检测增长停滞 (< 1场/min)`);
      }
    } else {
      this.stats.consecutiveTimeouts = 0;
    }
    
    return {
      trigger: reasons.length > 0,
      reason: reasons.join('; ')
    };
  }

  /**
   * 触发熔断
   * @private
   */
  async _triggerCircuitBreaker(reason) {
    if (this.circuitBreaker.isOpen) return;
    
    this.circuitBreaker.isOpen = true;
    this.circuitBreaker.lastOpenTime = Date.now();
    
    console.log('');
    console.log('╔══════════════════════════════════════════════════════════════╗');
    console.log('║  🚨 CIRCUIT BREAKER TRIGGERED 🚨                             ║');
    console.log('╠══════════════════════════════════════════════════════════════╣');
    console.log(`║  触发原因: ${reason.substring(0, 50).padEnd(50)} ║`);
    console.log(`║  熔断时间: ${new Date().toISOString()}                 ║`);
    console.log('║                                                              ║');
    console.log('║  建议操作:                                                   ║');
    console.log('║  1. 检查代理池健康状态                                       ║');
    console.log('║  2. 验证 FotMob 页面结构是否变更                            ║');
    console.log('║  3. 考虑降低并发数后重新启动                                ║');
    console.log('╚══════════════════════════════════════════════════════════════╝');
    console.log('');
    
    // 可选: 发送系统信号终止马拉松进程
    try {
      await execAsync('pkill -f "titan_marathon.js"');
      console.log('[MONITOR] 已发送终止信号给 titan_marathon.js');
    } catch (e) {
      // 忽略错误
    }
  }

  /**
   * 打印监控报告
   * @private
   */
  _printReport(quality, growth, io, trigger) {
    const timestamp = new Date().toISOString().split('T')[1].split('.')[0];
    
    console.log('');
    console.log(`╔══════════════════════════════════════════════════════════════╗`);
    console.log(`║  📊 TITAN MONITOR @ ${timestamp}                          ║`);
    console.log(`╠══════════════════════════════════════════════════════════════╣`);
    
    // 数据质量
    const qStatus = quality.status === 'OK' ? '✅' : quality.status === 'WARNING' ? '⚠️' : '❌';
    console.log(`║  ${qStatus} 数据质量: ${quality.avgSize.toString().padStart(6)}KB 平均 | 空壳: ${quality.shellCount} | 低质: ${quality.lowQualityCount}        ║`);
    
    // 增长速率
    const gStatus = growth.status === 'NORMAL' ? '✅' : growth.status === 'FAST' ? '⚡' : '⚠️';
    console.log(`║  ${gStatus} 增长速率: ${growth.matchRatePerMin.padStart(5)}场/min | 数据: ${growth.dataRateKBps.padStart(5)}KB/s | 总量: ${growth.totalMatches.toString().padStart(5)} ║`);
    
    // IO
    const ioStatus = io.status === 'EXCELLENT' ? '✅' : io.status === 'GOOD' ? '✓' : '?';
    console.log(`║  ${ioStatus} IO 性能: 缓存命中率 ${io.cacheHitRatio.padStart(6)} | 磁盘读: ${io.diskReads.toString().padStart(6)}                  ║`);
    
    if (trigger.trigger) {
      console.log(`╠══════════════════════════════════════════════════════════════╣`);
      console.log(`║  🔥 熔断预警: ${trigger.reason.substring(0, 45).padEnd(45)} ║`);
    }
    
    console.log(`╚══════════════════════════════════════════════════════════════╝`);
  }

  /**
   * 清理资源
   */
  async cleanup() {
    if (this.dbPool) {
      await this.dbPool.end();
    }
  }
}

/**
 * 主函数 - 持续监控模式
 */
async function main() {
  const monitor = new TitanMonitor();
  const interval = parseInt(process.argv[2]) || 30; // 默认 30 秒检查一次
  
  console.log('');
  console.log('╔══════════════════════════════════════════════════════════════╗');
  console.log('║  📡 TITAN MONITOR 启动                                       ║');
  console.log('║                                                              ║');
  console.log(`║  检查间隔: ${interval}秒 | 熔断阈值: 3次空壳/5次停滞          ║`);
  console.log('║                                                              ║');
  console.log('║  检测指标:                                                   ║');
  console.log('║  - 空壳数据 (< 1KB)                                          ║');
  console.log('║  - 低质量数据 (< 100KB)                                      ║');
  console.log('║  - 增长速率 (< 1场/min 视为停滞)                             ║');
  console.log('║  - IO 缓存命中率                                             ║');
  console.log('╚══════════════════════════════════════════════════════════════╝');
  console.log('');
  
  // 立即执行一次检查
  await monitor.healthCheck();
  
  // 定时检查
  const timer = setInterval(async () => {
    await monitor.healthCheck();
  }, interval * 1000);
  
  // 优雅退出
  process.on('SIGINT', async () => {
    console.log('\n🛑 监控停止...');
    clearInterval(timer);
    await monitor.cleanup();
    process.exit(0);
  });
}

// 单次检查模式
async function singleCheck() {
  const monitor = new TitanMonitor();
  const result = await monitor.healthCheck();
  await monitor.cleanup();
  return result;
}

// 导出供其他模块使用
module.exports = { TitanMonitor, singleCheck };

// 如果直接运行
if (require.main === module) {
  main().catch(err => {
    console.error('监控错误:', err);
    process.exit(1);
  });
}