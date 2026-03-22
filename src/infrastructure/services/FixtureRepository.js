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
            if (upsertResult === 'inserted') result.inserted++;
            else if (upsertResult === 'updated') result.updated++;
            else result.failed++;
          }
        } finally {
          client.release();
        }
      } catch (error) {
        this.logger.error(`[Repository] 批量持久化失败: ${error.message}`);
        result.failed += batch.length;
      }
    }

    return result;
  }

  /**
   * 单条 Upsert
   * @private
   */
  async _upsertMatch(client, match) {
    try {
      const query = `
        INSERT INTO matches (match_id, league_id, season, home_team, away_team, match_date, match_time, status, external_id, created_at, updated_at)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, NOW(), NOW())
        ON CONFLICT (match_id) DO UPDATE SET
          home_team = EXCLUDED.home_team,
          away_team = EXCLUDED.away_team,
          match_date = EXCLUDED.match_date,
          match_time = EXCLUDED.match_time,
          status = EXCLUDED.status,
          external_id = EXCLUDED.external_id,
          updated_at = NOW()
        RETURNING (xmax = 0) AS was_insert
      `;

      const values = [
        match.match_id,
        match.league_id,
        match.season,
        match.home_team,
        match.away_team,
        match.match_date,
        match.match_time,
        match.status,
        match.external_id
      ];

      const result = await client.query(query, values);
      return result.rows[0]?.was_insert ? 'inserted' : 'updated';
    } catch (error) {
      this.logger.error(`[Repository] Upsert 失败 ${match.match_id}: ${error.message}`);
      return 'failed';
    }
  }

  /**
   * 查询已存在的比赛
   * @param {Array} matchIds - 比赛 ID 数组
   * @returns {Promise<Set>} 已存在的 match_id 集合
   */
  async findExistingMatches(matchIds) {
    try {
      const client = await this.dbPool.connect();
      try {
        const query = `
          SELECT match_id FROM matches
          WHERE match_id = ANY($1)
        `;
        const result = await client.query(query, [matchIds]);
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
        const pattern = `${leagueId}_${season.replace(/[\/-_]/g, '')}_%`;
        const result = await client.query(
          'DELETE FROM matches WHERE match_id LIKE $1',
          [pattern]
        );
        this.logger.info(`[Repository] 删除 ${result.rowCount} 条记录`);
        return result.rowCount;
      } finally {
        client.release();
      }
    } catch (error) {
      this.logger.error(`[Repository] 删除失败: ${error.message}`);
      return 0;
    }
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
   * V6.7: 根据队名查找比赛 (用于 Recon Scanner)
   * @param {string} homeTeam - 主队名
   * @param {string} awayTeam - 客队名
   * @param {string} season - 赛季 (如 '2023/2024')
   * @returns {Promise<Object|null>} { matchId, confidence, method, dbHome, dbAway }
   */
  async findMatchByTeams(homeTeam, awayTeam, season) {
    try {
      const client = await this.dbPool.connect();
      try {
        // 1. 首先尝试精确匹配
        const exactQuery = `
          SELECT match_id, home_team, away_team, match_date
          FROM matches
          WHERE season = $1
            AND (
              (LOWER(home_team) = LOWER($2) AND LOWER(away_team) = LOWER($3))
              OR (LOWER(home_team) = LOWER($3) AND LOWER(away_team) = LOWER($2))
            )
          LIMIT 1;
        `;

        const exactResult = await client.query(exactQuery, [
          season, homeTeam, awayTeam
        ]);

        if (exactResult.rows.length > 0) {
          const row = exactResult.rows[0];
          return {
            matchId: row.match_id,
            confidence: 1.0,
            method: 'exact',
            dbHome: row.home_team,
            dbAway: row.away_team
          };
        }

        // 2. 精确匹配失败，返回 null (模糊匹配在 recon_scanner 中处理)
        return null;

      } finally {
        client.release();
      }
    } catch (error) {
      this.logger.error(`[Repository] 队名查找失败: ${error.message}`);
      return null;
    }
  }

  /**
   * V6.7: 保存 OddsPortal 映射
   * @param {Object} mappingData - 映射数据
   * @returns {Promise<Object>} { success, matchId }
   */
  async saveOddsPortalMapping(mappingData) {
    try {
      const client = await this.dbPool.connect();
      try {
        const query = `
          INSERT INTO matches_oddsportal_mapping
            (match_id, oddsportal_hash, full_url, season, league_name, home_team, away_team,
             match_confidence, mapping_method, status, created_at, updated_at)
          VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, NOW(), NOW())
          ON CONFLICT (match_id, season) DO UPDATE SET
            oddsportal_hash = EXCLUDED.oddsportal_hash,
            full_url = EXCLUDED.full_url,
            match_confidence = EXCLUDED.match_confidence,
            mapping_method = EXCLUDED.mapping_method,
            updated_at = NOW()
          RETURNING match_id;
        `;

        const result = await client.query(query, [
          mappingData.match_id,
          mappingData.oddsportal_hash,
          mappingData.full_url,
          mappingData.season,
          mappingData.league_name,
          mappingData.home_team,
          mappingData.away_team,
          mappingData.match_confidence,
          mappingData.mapping_method,
          mappingData.status || 'pending'
        ]);

        return {
          success: result.rows.length > 0,
          matchId: result.rows[0]?.match_id
        };

      } finally {
        client.release();
      }
    } catch (error) {
      this.logger.error(`[Repository] 保存映射失败: ${error.message}`);
      return { success: false, error: error.message };
    }
  }

  /**
   * V6.7: 获取映射统计
   * @param {string} season - 赛季
   * @returns {Promise<Object>} { total, pending, harvested }
   */
  async getMappingStats(season) {
    try {
      const client = await this.dbPool.connect();
      try {
        const query = `
          SELECT
            COUNT(*) as total,
            COUNT(*) FILTER (WHERE status = 'pending') as pending,
            COUNT(*) FILTER (WHERE status = 'harvested') as harvested
          FROM matches_oddsportal_mapping
          WHERE season = $1
        `;

        const result = await client.query(query, [season]);
        return result.rows[0] || { total: 0, pending: 0, harvested: 0 };

      } finally {
        client.release();
      }
    } catch (error) {
      this.logger.error(`[Repository] 获取统计失败: ${error.message}`);
      return { total: 0, pending: 0, harvested: 0 };
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