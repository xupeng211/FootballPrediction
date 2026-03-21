/**
 * @file FixtureRepository - 赛程数据持久化层
 * @module infrastructure/services/FixtureRepository
 * @version V6.7.5-REPOSITORY
 * @description
 * 职责: 负责赛程数据的 PostgreSQL 持久化操作
 * 包含: 批量插入、冲突处理、Upsert 逻辑
 * 从 DiscoveryService 解耦，专注数据持久化
 */

'use strict';

/**
 * 赛程数据仓储
 * @class FixtureRepository
 */
class FixtureRepository {
  /**
   * 创建仓储实例
   * @param {Object} options - 配置选项
   * @param {Object} options.dbPool - PostgreSQL 连接池
   * @param {Object} options.logger - 日志对象
   * @param {number} options.batchSize - 批量大小 (默认: 50)
   */
  constructor(options = {}) {
    this.dbPool = options.dbPool;
    this.logger = options.logger || {
      info: () => {},
      warn: () => {},
      error: () => {}
    };
    this.batchSize = options.batchSize || 50;
  }

  /**
   * 持久化赛程数据 (批量 Upsert)
   * @param {Array} fixtures - 比赛数据数组
   * @returns {Promise<Object>} { total, inserted, updated, failed }
   */
  async persist(fixtures) {
    const result = { total: fixtures.length, inserted: 0, updated: 0, failed: 0 };

    for (let i = 0; i < fixtures.length; i += this.batchSize) {
      const batch = fixtures.slice(i, i + this.batchSize);

      try {
        const client = await this.dbPool.connect();
        try {
          for (const match of batch) {
            const upsertResult = await this._upsertMatch(client, match);
            if (upsertResult.inserted) {
              result.inserted++;
            } else {
              result.updated++;
            }
          }
        } finally {
          client.release();
        }
      } catch (error) {
        this.logger.error(`[Repository] 批量写入失败: ${error.message}`);
        result.failed += batch.length;
      }
    }

    return result;
  }

  /**
   * 单条数据 Upsert
   * @private
   */
  async _upsertMatch(client, match) {
    const upsertQuery = `
      INSERT INTO matches (
        match_id, external_id, league_name, season,
        home_team, away_team, match_date, status,
        is_finished, created_at, updated_at
      ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
      ON CONFLICT (match_id) DO UPDATE SET
        external_id = EXCLUDED.external_id,
        status = EXCLUDED.status,
        is_finished = EXCLUDED.is_finished,
        updated_at = EXCLUDED.updated_at
      RETURNING (xmax = 0) AS inserted
    `;

    const values = [
      match.match_id,
      match.external_id,
      match.league_name,
      match.season,
      match.home_team,
      match.away_team,
      match.match_date,
      match.status,
      match.is_finished,
      match.created_at,
      match.updated_at
    ];

    const result = await client.query(upsertQuery, values);
    return { inserted: result.rows[0]?.inserted || false };
  }

  /**
   * 根据 match_id 查询单条记录
   * @param {string} matchId - 比赛 ID
   * @returns {Promise<Object|null>}
   */
  async findById(matchId) {
    try {
      const client = await this.dbPool.connect();
      try {
        const result = await client.query(
          'SELECT * FROM matches WHERE match_id = $1',
          [matchId]
        );
        return result.rows[0] || null;
      } finally {
        client.release();
      }
    } catch (error) {
      this.logger.error(`[Repository] 查询失败: ${error.message}`);
      return null;
    }
  }

  /**
   * 批量查询是否存在
   * @param {Array<string>} matchIds - 比赛 ID 数组
   * @returns {Promise<Set<string>>} 已存在的 ID 集合
   */
  async findExistingIds(matchIds) {
    try {
      const client = await this.dbPool.connect();
      try {
        const result = await client.query(
          'SELECT match_id FROM matches WHERE match_id = ANY($1)',
          [matchIds]
        );
        return new Set(result.rows.map(r => r.match_id));
      } finally {
        client.release();
      }
    } catch (error) {
      this.logger.error(`[Repository] 批量查询失败: ${error.message}`);
      return new Set();
    }
  }

  /**
   * 删除指定联赛赛季的数据
   * @param {number} leagueId - 联赛 ID
   * @param {string} season - 赛季
   * @returns {Promise<number>} 删除的行数
   */
  async deleteByLeagueAndSeason(leagueId, season) {
    try {
      const client = await this.dbPool.connect();
      try {
        // 使用 match_id 前缀匹配: leagueId_season_*
        const pattern = `${leagueId}_${season.replace(/[\/\-_]/g, '')}_%`;
        const result = await client.query(
          'DELETE FROM matches WHERE match_id LIKE $1',
          [pattern]
        );
        this.logger.info(`[Repository] 删除 ${result.rowCount} 条记录`);
        return result.rowCount;
      } finally {
        client.release();
      }

  /**
   * 获取 raw_match_data 表记录总数 (V6.7: 供审计使用)
   * @returns {Promise<number>}
   */
  async getRawMatchDataCount() {
    try {
      const client = await this.dbPool.connect();
      try {
        const result = await client.query('SELECT COUNT(*) as count FROM raw_match_data');
        return parseInt(result.rows[0].count, 10);
      } finally {
        client.release();
      }
    } catch (error) {
      this.logger.error(`[Repository] 获取记录数失败: ${error.message}`);
      return 0;
    }
  }

  /**
   * 获取最近记录 (V6.7: 供审计使用)
   * @param {number} limit - 返回条数
   * @returns {Promise<Array>}
   */
  async getRecentRecords(limit = 5) {
    try {
      const client = await this.dbPool.connect();
      try {
        const result = await client.query(
          'SELECT match_id, collected_at FROM raw_match_data ORDER BY collected_at DESC LIMIT $1',
          [limit]
        );
        return result.rows;
      } finally {
        client.release();
      }
    } catch (error) {
      this.logger.error(`[Repository] 获取最近记录失败: ${error.message}`);
      return [];
    }
  }

  /**
   * 初始化 (V6.7: 如果未提供 dbPool，自动创建)
   */
  async init() {
    if (!this.dbPool) {
      const { Pool } = require('pg');
      this.dbPool = new Pool({
        host: process.env.DB_HOST || 'localhost',
        port: parseInt(process.env.DB_PORT || '5432'),
        database: process.env.DB_NAME || 'football_db',
        user: process.env.DB_USER || 'football_user',
        password: process.env.DB_PASSWORD || 'football_pass',
        max: 10,
        idleTimeoutMillis: 30000
      });
      this.logger.info('[Repository] 已自动创建数据库连接池');
    }
  }

  /**
   * 关闭连接 (V6.7: 资源释放)
   */
  async close() {
    if (this.dbPool) {
      await this.dbPool.end();
      this.logger.info('[Repository] 数据库连接池已关闭');
    }
  }
}

module.exports = { FixtureRepository };
