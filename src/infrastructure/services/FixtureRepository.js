/**
 * @file FixtureRepository - 赛程数据持久化层 (V11.0 Clean Sweep)
 * @module infrastructure/services/FixtureRepository
 * @version V11.0-REPOSITORY-HARDENED
 * @description
 * 职责: 负责赛程数据的 PostgreSQL 持久化操作
 * V11.0 变更:
 * - 添加缺失的 match_confidence 和 mapping_method 字段处理
 * - saveOddsPortalMapping 改为抛出错误而非静默失败
 * - 添加事务支持和自动重试机制
 */

'use strict';

const path = require('path');
const fs = require('fs');

/**
 * 加载 SQL 模板配置
 * @private
 * @returns {Object} SQL 模板
 */
function loadSqlTemplates() {
  try {
    const configPath = path.join(process.cwd(), 'config/recon_config.json');
    if (fs.existsSync(configPath)) {
      const config = JSON.parse(fs.readFileSync(configPath, 'utf8'));
      return config.sql_templates || {};
    }
  } catch (e) {
    console.error('[FixtureRepository] 警告: 无法加载 sql_templates 配置', e.message);
  }
  return {};
}

const SQL_TEMPLATES = loadSqlTemplates();

/**
 * Repository 错误类
 */
class RepositoryError extends Error {
  /**
   * @param {string} message - 错误消息
   * @param {string} code - 错误代码
   * @param {Error} [originalError] - 原始错误对象
   */
  constructor(message, code, originalError = null) {
    super(message);
    this.name = 'RepositoryError';
    this.code = code;
    this.originalError = originalError;
    this.timestamp = new Date().toISOString();
  }
}

/**
 * 赛程数据仓储 (V11.0 Clean Sweep)
 * @class FixtureRepository
 */
class FixtureRepository {
  /**
   * @param {Object} [options] - 配置选项
   * @param {Object} [options.dbPool] - 数据库连接池
   * @param {Object} [options.logger] - 日志记录器
   * @param {number} [options.batchSize] - 批量处理大小
   * @param {number} [options.maxRetries] - 最大重试次数
   * @param {number} [options.retryDelayMs] - 重试延迟（毫秒）
   * @param {string} [options.traceId] - 追踪 ID
   */
  constructor(options = {}) {
    this.dbPool = options.dbPool;
    this.logger = options.logger || { info: () => {}, warn: () => {}, error: () => {} };
    this.batchSize = options.batchSize || 50;
    this.maxRetries = options.maxRetries || 3;
    this.retryDelayMs = options.retryDelayMs || 1000;
    this.traceId = options.traceId || null;
  }

  /**
   * 初始化连接池
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
      this.logger.info('[Repository] 数据库连接池已创建');
    }
  }

  /**
   * 带重试的数据库操作
   * @private
   * @param {Function} operation - 数据库操作函数
   * @param {string} operationName - 操作名称（用于日志）
   * @returns {Promise<any>} 操作结果
   * @throws {RepositoryError} 当重试耗尽时抛出
   */
  async _executeWithRetry(operation, operationName) {
    let lastError;
    
    for (let attempt = 1; attempt <= this.maxRetries; attempt++) {
      try {
        return await operation();
      } catch (error) {
        lastError = error;
        this.logger.warn(`[Repository] ${operationName} 失败 (尝试 ${attempt}/${this.maxRetries})`, {
          error: error.message,
          code: error.code
        });
        
        if (attempt < this.maxRetries) {
          await new Promise(r => setTimeout(r, this.retryDelayMs * attempt));
        }
      }
    }
    
    throw new RepositoryError(
      `${operationName} 在 ${this.maxRetries} 次尝试后仍然失败: ${lastError.message}`,
      'MAX_RETRIES_EXCEEDED',
      lastError
    );
  }

  /**
   * 保存 OddsPortal 映射 (V11.0 硬化版)
   * @param {Object} mappingData - 映射数据
   * @returns {Promise<Object>} 保存结果
   * @throws {RepositoryError}
   */
  async saveOddsPortalMapping(mappingData) {
    const requiredFields = ['match_id', 'oddsportal_hash', 'full_url', 'season', 'league_name', 'home_team', 'away_team'];
    
    // 验证必填字段
    const missing = requiredFields.filter(f => !mappingData[f]);
    if (missing.length > 0) {
      throw new RepositoryError(
        `缺少必填字段: ${missing.join(', ')}`,
        'MISSING_REQUIRED_FIELDS'
      );
    }

    // V11.0: 如果表没有这些字段，从数据中移除
    const optionalFields = ['match_confidence', 'mapping_method'];
    const hasOptionalFields = await this._checkOptionalFields('matches_oddsportal_mapping', optionalFields);

    return this._executeWithRetry(async () => {
      const client = await this.dbPool.connect();
      
      try {
        await client.query('BEGIN');
        const result = await this._saveOddsPortalMappingWithClient(client, mappingData, hasOptionalFields);
        await client.query('COMMIT');

        this.logger.info('[Repository] 映射保存成功', { 
          matchId: mappingData.match_id,
          hash: mappingData.oddsportal_hash,
          traceId: this.traceId
        });

        return {
          success: true,
          matchId: result.matchId,
          wasInsert: result.wasInsert
        };

      } catch (error) {
        await client.query('ROLLBACK');
        
        // 分类错误
        if (error.code === '23503') { // 外键约束
          throw new RepositoryError(
            `外键约束失败: ${error.message}`,
            'FOREIGN_KEY_VIOLATION',
            error
          );
        }
        if (error.code === '23505') { // 唯一约束
          throw new RepositoryError(
            `唯一约束冲突: ${error.message}`,
            'UNIQUE_VIOLATION',
            error
          );
        }
        if (error.code === '23502') { // 非空约束
          throw new RepositoryError(
            `非空约束失败: ${error.message}`,
            'NOT_NULL_VIOLATION',
            error
          );
        }
        
        throw new RepositoryError(
          `数据库操作失败: ${error.message}`,
          'DATABASE_ERROR',
          error
        );
      } finally {
        client.release();
      }
    }, 'saveOddsPortalMapping');
  }

  /**
   * 使用共享 client 保存映射
   * @private
   * @param {Object} client - PostgreSQL client
   * @param {Object} mappingData - 映射数据
   * @param {Object} hasOptionalFields - 可选字段存在状态
   * @returns {Promise<{matchId: string|undefined, wasInsert: boolean}>}
   */
  async _saveOddsPortalMappingWithClient(client, mappingData, hasOptionalFields) {
    let columns = ['match_id', 'oddsportal_hash', 'full_url', 'season', 'league_name', 'home_team', 'away_team', 'status', 'created_at', 'updated_at'];
    let values = ['$1', '$2', '$3', '$4', '$5', '$6', '$7', '$8', 'NOW()', 'NOW()'];
    let params = [
      mappingData.match_id,
      mappingData.oddsportal_hash,
      mappingData.full_url,
      mappingData.season,
      mappingData.league_name,
      mappingData.home_team,
      mappingData.away_team,
      mappingData.status || 'pending'
    ];

    if (hasOptionalFields.match_confidence) {
      columns.push('match_confidence');
      values.push(`$${params.length + 1}`);
      params.push(mappingData.match_confidence || 0.75);
    }

    if (hasOptionalFields.mapping_method) {
      columns.push('mapping_method');
      values.push(`$${params.length + 1}`);
      params.push(mappingData.mapping_method || 'protocol_extract');
    }

    // 使用 SQL 模板
    const template = SQL_TEMPLATES.save_mapping || `
      INSERT INTO matches_oddsportal_mapping ({columns})
      VALUES ({values})
      ON CONFLICT (match_id, season) DO UPDATE SET
        oddsportal_hash = EXCLUDED.oddsportal_hash,
        full_url = EXCLUDED.full_url,
        home_team = EXCLUDED.home_team,
        away_team = EXCLUDED.away_team,
        status = EXCLUDED.status,
        updated_at = NOW()
        {optional_updates}
      RETURNING match_id;
    `;

    const optionalUpdates = [
      hasOptionalFields.match_confidence ? ', match_confidence = EXCLUDED.match_confidence' : '',
      hasOptionalFields.mapping_method ? ', mapping_method = EXCLUDED.mapping_method' : ''
    ].join('');

    const query = template
      .replace('{columns}', columns.join(', '))
      .replace('{values}', values.join(', '))
      .replace('{optional_updates}', optionalUpdates);

    const result = await client.query(query, params);
    return {
      matchId: result.rows[0]?.match_id,
      wasInsert: result.rows.length > 0
    };
  }

  /**
   * 检查表是否存在可选字段
   * @private
   * @param {string} tableName - 表名
   * @param {Array<string>} fields - 字段列表
   * @returns {Promise<Object>} 字段存在状态
   */
  async _checkOptionalFields(tableName, fields) {
    return this._executeWithRetry(async () => {
      const template = SQL_TEMPLATES.check_optional_fields || `
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = $1 AND column_name = ANY($2)
      `;
      
      const result = await this.dbPool.query(template, [tableName, fields]);
      const existingFields = result.rows.map(r => r.column_name);
      
      return {
        match_confidence: existingFields.includes('match_confidence'),
        mapping_method: existingFields.includes('mapping_method')
      };
    }, 'checkOptionalFields');
  }

  /**
   * 批量保存映射 (事务保护)
   * @param {Array} mappings - 映射列表
   * @returns {Promise<Object>} 批量保存结果
   * @throws {RepositoryError}
   */
  async batchSaveOddsPortalMappings(mappings) {
    if (!Array.isArray(mappings) || mappings.length === 0) {
      return { success: true, inserted: 0, failed: 0, errors: [] };
    }

    const requiredFields = ['match_id', 'oddsportal_hash', 'full_url', 'season', 'league_name', 'home_team', 'away_team'];
    for (const mapping of mappings) {
      const missing = requiredFields.filter(f => !mapping[f]);
      if (missing.length > 0) {
        throw new RepositoryError(
          `缺少必填字段: ${missing.join(', ')}`,
          'MISSING_REQUIRED_FIELDS'
        );
      }
    }

    const optionalFields = ['match_confidence', 'mapping_method'];
    const hasOptionalFields = await this._checkOptionalFields('matches_oddsportal_mapping', optionalFields);

    return this._executeWithRetry(async () => {
      const client = await this.dbPool.connect();
      const results = { inserted: 0, failed: 0, errors: [] };
      
      try {
        await client.query('BEGIN');
        
        for (const mapping of mappings) {
          try {
            await this._saveOddsPortalMappingWithClient(client, mapping, hasOptionalFields);
            results.inserted++;
          } catch (error) {
            results.failed++;
            results.errors.push({ matchId: mapping.match_id, error: error.message });
            throw error;
          }
        }
        
        await client.query('COMMIT');
        return { success: true, ...results };
      } catch (error) {
        await client.query('ROLLBACK');

        if (error instanceof RepositoryError) {
          throw error;
        }

        throw new RepositoryError(
          `批量保存映射失败: ${error.message}`,
          'BATCH_SAVE_FAILED',
          error
        );
      } finally {
        client.release();
      }
    }, 'batchSaveOddsPortalMappings');
  }

  /**
   * 根据队名查找比赛
   * @param {string} homeTeam - 主队名称
   * @param {string} awayTeam - 客队名称
   * @param {string} season - 赛季
   * @returns {Promise<Object|null>} 匹配的比赛结果
   */
  async findMatchByTeams(homeTeam, awayTeam, season) {
    return this._executeWithRetry(async () => {
      const client = await this.dbPool.connect();
      try {
        const query = SQL_TEMPLATES.find_match_by_teams || `
          SELECT match_id, home_team, away_team, match_date
          FROM matches
          WHERE season = $1
            AND (
              (LOWER(home_team) = LOWER($2) AND LOWER(away_team) = LOWER($3))
              OR (LOWER(home_team) = LOWER($3) AND LOWER(away_team) = LOWER($2))
            )
          LIMIT 1;
        `;
        const result = await client.query(query, [season, homeTeam, awayTeam]);
        
        if (result.rows.length > 0) {
          return {
            matchId: result.rows[0].match_id,
            confidence: 1.0,
            method: 'exact',
            dbHome: result.rows[0].home_team,
            dbAway: result.rows[0].away_team
          };
        }
        return null;
      } finally {
        client.release();
      }
    }, 'findMatchByTeams');
  }

  /**
   * 获取赛季所有比赛
   * @param {string} season - 赛季
   * @returns {Promise<Array>} 比赛列表
   */
  async findMatchesBySeason(season) {
    return this._executeWithRetry(async () => {
      const client = await this.dbPool.connect();
      try {
        const query = SQL_TEMPLATES.find_matches_by_season || `
          SELECT match_id, home_team, away_team, match_date
          FROM matches
          WHERE season = $1
          ORDER BY match_date;
        `;
        const result = await client.query(query, [season]);
        return result.rows;
      } finally {
        client.release();
      }
    }, 'findMatchesBySeason');
  }

  /**
   * 获取未缝合的比赛
   * @param {string} season - 赛季
   * @param {string} leagueName - 联赛名称
   * @returns {Promise<Array>} 未缝合的比赛列表
   */
  async getUnstitchedMatches(season, leagueName) {
    return this._executeWithRetry(async () => {
      const client = await this.dbPool.connect();
      try {
        const query = SQL_TEMPLATES.get_unstitched_matches || `
          SELECT m.match_id, m.home_team, m.away_team, m.match_date
          FROM matches m
          LEFT JOIN matches_oddsportal_mapping map
            ON m.match_id = map.match_id AND map.season = $2
          WHERE m.league_name = $1
            AND m.season = $2
            AND map.match_id IS NULL
          ORDER BY m.match_date;
        `;
        const result = await client.query(query, [leagueName, season]);
        return result.rows;
      } finally {
        client.release();
      }
    }, 'getUnstitchedMatches');
  }

  /**
   * 获取映射统计
   * @param {string} season - 赛季
   * @returns {Promise<Object>} 统计结果
   */
  async getMappingStats(season) {
    return this._executeWithRetry(async () => {
      const client = await this.dbPool.connect();
      try {
        const query = SQL_TEMPLATES.get_mapping_stats || `
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
    }, 'getMappingStats');
  }

  /**
   * 关闭连接池
   */
  async close() {
    if (this.dbPool) {
      await this.dbPool.end();
      this.logger.info('[Repository] 数据库连接池已关闭');
    }
  }
}

module.exports = { FixtureRepository, RepositoryError };
