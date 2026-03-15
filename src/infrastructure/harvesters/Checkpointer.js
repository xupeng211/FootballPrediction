/**
 * Checkpointer - V6.0 P0 断点续传核心模块
 * =========================================
 *
 * 为 OddsPortalHarvester 提供持久化进度追踪能力
 * 确保 11,907 场回填任务可以断点续传、失败重试
 *
 * @module infrastructure/harvesters/Checkpointer
 * @version V6.0.0-FORTIFY
 * @since 2026-03-15
 */

'use strict';

const { StructuredLogger } = require('../../utils/StructuredLogger');

// SQL 语句
const SQL = {
  // 初始化比赛记录
  initMatch: `
    INSERT INTO backfill_progress (match_id, status, match_info, batch_id, oddsportal_hash)
    VALUES ($1, 'pending', $2, $3, $4)
    ON CONFLICT (match_id) DO NOTHING
  `,

  // 获取待处理任务 (断点续传核心)
  getPending: `
    SELECT match_id, retry_count, match_info, oddsportal_hash
    FROM backfill_progress
    WHERE status IN ('pending', 'failed')
      AND retry_count < 3
    ORDER BY retry_count ASC, updated_at ASC
    LIMIT $1
  `,

  // 标记为处理中
  markProcessing: `
    UPDATE backfill_progress
    SET status = 'processing', updated_at = NOW()
    WHERE match_id = $1 AND status NOT IN ('success', 'processing')
  `,

  // 标记成功
  markSuccess: `
    UPDATE backfill_progress
    SET status = 'success',
        completed_at = NOW(),
        processing_time_ms = $2,
        proxy_port = $3
    WHERE match_id = $1
  `,

  // 标记失败
  markFailed: `
    UPDATE backfill_progress
    SET status = 'failed',
        retry_count = retry_count + 1,
        last_error = $2,
        proxy_port = $3
    WHERE match_id = $1
  `,

  // 标记跳过
  markSkipped: `
    UPDATE backfill_progress
    SET status = 'skipped', updated_at = NOW()
    WHERE match_id = $1
  `,

  // 获取统计信息
  getStats: `
    SELECT
      COUNT(*) FILTER (WHERE status = 'pending') as pending_count,
      COUNT(*) FILTER (WHERE status = 'processing') as processing_count,
      COUNT(*) FILTER (WHERE status = 'success') as success_count,
      COUNT(*) FILTER (WHERE status = 'failed' AND retry_count < 3) as retryable_count,
      COUNT(*) FILTER (WHERE status = 'failed' AND retry_count >= 3) as dead_count,
      COUNT(*) FILTER (WHERE status = 'skipped') as skipped_count,
      COUNT(*) as total_count
    FROM backfill_progress
    WHERE ($1::varchar IS NULL OR batch_id = $1)
  `,

  // 获取已成功的ID列表 (用于断点续传时排除)
  getCompletedIds: `
    SELECT match_id
    FROM backfill_progress
    WHERE status IN ('success', 'skipped')
  `,

  // 重置失败但可重试的任务
  resetRetryable: `
    UPDATE backfill_progress
    SET status = 'pending', updated_at = NOW()
    WHERE status = 'failed' AND retry_count < 3
  `,

  // 清理旧数据
  cleanup: `
    DELETE FROM backfill_progress
    WHERE status = 'success'
      AND completed_at < NOW() - INTERVAL '7 days'
  `
};

/**
 * Checkpointer 类
 */
class Checkpointer {
  /**
   * @param {object} options - 配置选项
   * @param {object} options.pool - PostgreSQL连接池
   * @param {string} options.batchId - 批次ID
   */
  constructor(options = {}) {
    if (!options.pool) {
      throw new Error('Checkpointer 需要数据库连接池');
    }

    this.pool = options.pool;
    this.batchId = options.batchId || `batch_${Date.now()}`;

    this.logger = new StructuredLogger({
      component: 'Checkpointer',
      logDir: '/app/logs/pipeline',
      enableStructured: true
    });

    this.stats = {
      initialized: 0,
      succeeded: 0,
      failed: 0,
      skipped: 0
    };
  }

  /**
   * 批量初始化比赛记录
   * @param {Array} matches - 比赛列表 [{match_id, home_team, away_team, ...}]
   * @returns {Promise<number>} 初始化数量
   */
  async initializeMatches(matches) {
    const client = await this.pool.connect();
    let count = 0;

    try {
      await client.query('BEGIN');

      for (const match of matches) {
        try {
          await client.query(SQL.initMatch, [
            match.match_id,
            JSON.stringify({
              home_team: match.home_team,
              away_team: match.away_team,
              league: match.league,
              match_date: match.match_date
            }),
            this.batchId,
            match.oddsportal_hash || null
          ]);
          count++;
        } catch (err) {
          // 忽略重复键错误
          if (!err.message.includes('duplicate key')) {
            throw err;
          }
        }
      }

      await client.query('COMMIT');
      this.stats.initialized += count;

      this.logger.info('✅ 比赛记录初始化完成', {
        batchId: this.batchId,
        count,
        total: matches.length
      });

      return count;
    } catch (error) {
      await client.query('ROLLBACK');
      this.logger.error('❌ 初始化失败', { error: error.message });
      throw error;
    } finally {
      client.release();
    }
  }

  /**
   * 获取待处理任务 (断点续传核心)
   * @param {number} limit - 获取数量限制
   * @returns {Promise<Array>} 待处理任务列表
   */
  async getPendingMatches(limit = 100) {
    const result = await this.pool.query(SQL.getPending, [limit]);

    this.logger.debug('获取待处理任务', {
      count: result.rows.length,
      limit
    });

    return result.rows;
  }

  /**
   * 获取已完成的ID集合 (用于快速排除)
   * @returns {Promise<Set>} 已完成ID集合
   */
  async getCompletedIdsSet() {
    const result = await this.pool.query(SQL.getCompletedIds);
    const ids = new Set(result.rows.map(r => r.match_id));

    this.logger.debug('获取已完成ID', { count: ids.size });

    return ids;
  }

  /**
   * 标记比赛为处理中
   * @param {string} matchId - 比赛ID
   */
  async markProcessing(matchId) {
    await this.pool.query(SQL.markProcessing, [matchId]);
  }

  /**
   * 标记比赛处理成功
   * @param {string} matchId - 比赛ID
   * @param {object} metadata - 元数据 {processingTimeMs, proxyPort}
   */
  async markSuccess(matchId, metadata = {}) {
    await this.pool.query(SQL.markSuccess, [
      matchId,
      metadata.processingTimeMs || 0,
      metadata.proxyPort || null
    ]);

    this.stats.succeeded++;

    this.logger.debug('✅ 标记成功', {
      matchId,
      proxyPort: metadata.proxyPort
    });
  }

  /**
   * 标记比赛处理失败
   * @param {string} matchId - 比赛ID
   * @param {string} error - 错误信息
   * @param {number} proxyPort - 使用的代理端口
   */
  async markFailed(matchId, error, proxyPort = null) {
    await this.pool.query(SQL.markFailed, [
      matchId,
      error?.substring(0, 500) || 'Unknown error', // 限制长度
      proxyPort
    ]);

    this.stats.failed++;

    this.logger.warn('❌ 标记失败', {
      matchId,
      error: error?.substring(0, 100),
      proxyPort
    });
  }

  /**
   * 标记比赛跳过
   * @param {string} matchId - 比赛ID
   */
  async markSkipped(matchId) {
    await this.pool.query(SQL.markSkipped, [matchId]);
    this.stats.skipped++;
  }

  /**
   * 获取进度统计
   * @returns {Promise<object>} 统计信息
   */
  async getStats() {
    const result = await this.pool.query(SQL.getStats, [this.batchId]);
    const stats = result.rows[0];

    // 计算进度百分比
    const completed = parseInt(stats.success_count) + parseInt(stats.skipped_count);
    const total = parseInt(stats.total_count);
    const progress = total > 0 ? (completed / total * 100).toFixed(2) : '0.00';

    return {
      ...stats,
      progress_percentage: progress,
      batchId: this.batchId,
      memoryStats: this.stats
    };
  }

  /**
   * 重置可重试的失败任务
   * @returns {Promise<number>} 重置数量
   */
  async resetRetryable() {
    const result = await this.pool.query(SQL.resetRetryable);

    this.logger.info('🔄 重置可重试任务', {
      count: result.rowCount
    });

    return result.rowCount;
  }

  /**
   * 清理旧的成功记录
   * @param {number} days - 保留天数
   */
  async cleanup(days = 7) {
    const result = await this.pool.query(SQL.cleanup);

    this.logger.info('🧹 清理旧数据', {
      deleted: result.rowCount,
      olderThan: `${days} days`
    });

    return result.rowCount;
  }

  /**
   * 打印进度报告
   */
  async printProgressReport() {
    const stats = await this.getStats();

    console.log('\n' + '='.repeat(60));
    console.log('📊 回填进度报告');
    console.log('='.repeat(60));
    console.log(`批次ID: ${stats.batchId}`);
    console.log(`总任务: ${stats.total_count}`);
    console.log(`已完成: ${stats.success_count} ✅`);
    console.log(`处理中: ${stats.processing_count} 🔄`);
    console.log(`待处理: ${stats.pending_count} ⏳`);
    console.log(`可重试: ${stats.retryable_count} ⚠️`);
    console.log(`已死亡: ${stats.dead_count} 💀`);
    console.log(`已跳过: ${stats.skipped_count} ⏭️`);
    console.log(`进度: ${stats.progress_percentage}%`);
    console.log('='.repeat(60));

    return stats;
  }
}

module.exports = { Checkpointer, SQL };