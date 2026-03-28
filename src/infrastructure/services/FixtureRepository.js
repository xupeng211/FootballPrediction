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

const { Normalizer } = require('../../utils/Normalizer');
const { loadReconConfig } = require('../recon/services/ReconServiceConfig');

function loadRepositoryConfig() {
  try {
    return loadReconConfig(process.env.RECON_CONFIG_PATH);
  } catch (e) {
    console.error('[FixtureRepository] 警告: 无法加载 recon 配置', e.message);
    throw e;
  }
}

const RECON_CONFIG = loadRepositoryConfig();
const SQL_TEMPLATES = RECON_CONFIG.sql_templates || {};
const REPOSITORY_CONFIG = RECON_CONFIG.repository || {};
const RETRY_CONFIG = REPOSITORY_CONFIG.retry || {};
const POOL_CONFIG = REPOSITORY_CONFIG.pool || {};

/**
 * Repository 错误类
 */
class RepositoryError extends Error {
  /**
   * @param {string} message - 错误消息
   * @param {string} code - 错误代码
   * @param {Error} [originalError] - 原始错误对象
   */
  constructor(message, code, originalError = null, details = null) {
    super(message);
    this.name = 'RepositoryError';
    this.code = code;
    this.originalError = originalError;
    this.details = details || null;
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
    this.batchSize = options.batchSize ?? REPOSITORY_CONFIG.batch_size ?? 50;
    this.maxRetries = options.maxRetries ?? RETRY_CONFIG.max_retries;
    this.retryDelayMs = options.retryDelayMs ?? RETRY_CONFIG.retry_delay_ms;
    this.maxRetryWindowMs = options.maxRetryWindowMs ?? RETRY_CONFIG.max_retry_window_ms;
    this.retryBackoffMultiplier = options.retryBackoffMultiplier ?? RETRY_CONFIG.backoff_multiplier;
    this.traceId = options.traceId || null;
    this._mappingSchemaEnsured = false;
    this._mappingHashUniquenessEnsured = false;
    this.sleep = options.sleep || ((ms) => new Promise((resolve) => setTimeout(resolve, ms)));
    this.now = options.now || (() => Date.now());
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
        max: POOL_CONFIG.max,
        idleTimeoutMillis: POOL_CONFIG.idle_timeout_ms
      });
      this.logger.info('[Repository] 数据库连接池已创建');
    }

    await this.ensureOddsPortalMappingSchema();
  }

  /**
   * 确保映射表具备方向一致性字段
   * @returns {Promise<void>}
   */
  async ensureOddsPortalMappingSchema() {
    if (this._mappingSchemaEnsured) {
      return;
    }

    await this._executeWithRetry(async () => {
      await this.dbPool.query(`
        ALTER TABLE matches_oddsportal_mapping
        ADD COLUMN IF NOT EXISTS is_reversed BOOLEAN DEFAULT FALSE
      `);
    }, 'ensureOddsPortalMappingSchema');

    if (!this._mappingHashUniquenessEnsured) {
      await this._executeWithRetry(async () => {
        await this.dbPool.query(`
          CREATE UNIQUE INDEX IF NOT EXISTS idx_mapping_season_hash_unique
          ON matches_oddsportal_mapping(season, oddsportal_hash)
        `);
      }, 'ensureOddsPortalHashUniquenessIndex');

      this._mappingHashUniquenessEnsured = true;
    }

    this._mappingSchemaEnsured = true;
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
    const startedAt = this.now();

    for (let attempt = 1; attempt <= this.maxRetries; attempt++) {
      try {
        return await operation();
      } catch (error) {
        if (error instanceof RepositoryError && error.code !== 'DATABASE_ERROR') {
          throw error;
        }

        lastError = error;
        const elapsedMs = Math.max(0, this.now() - startedAt);
        this.logger.warn(`[Repository] ${operationName} 失败 (尝试 ${attempt}/${this.maxRetries})`, {
          error: error.message,
          code: error.code,
          elapsedMs
        });

        const remainingBudgetMs = Math.max(0, this.maxRetryWindowMs - elapsedMs);
        if (attempt < this.maxRetries && remainingBudgetMs > 0) {
          const plannedDelayMs = Math.round(this.retryDelayMs * Math.max(1, attempt) ** this.retryBackoffMultiplier);
          const sleepMs = Math.min(remainingBudgetMs, plannedDelayMs);
          if (sleepMs > 0) {
            await this.sleep(sleepMs);
          }
          continue;
        }

        break;
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
  async saveOddsPortalMapping(mappingData, options = {}) {
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
    await this.ensureOddsPortalMappingSchema();

    const optionalFields = ['match_confidence', 'mapping_method', 'is_reversed'];
    const hasOptionalFields = await this._checkOptionalFields('matches_oddsportal_mapping', optionalFields);

    return this._executeWithRetry(async () => {
      const client = await this.dbPool.connect();
      const pipelineStatus = options.pipelineStatus || null;
      
      try {
        await client.query('BEGIN');
        await this._auditSeasonHashConflictsWithClient(client, [mappingData]);
        const result = await this._saveOddsPortalMappingWithClient(client, mappingData, hasOptionalFields);
        let updated = 0;

        if (pipelineStatus) {
          updated = await this._updateMatchPipelineStatusWithClient(
            client,
            [String(mappingData.match_id)],
            pipelineStatus
          );
        }

        await client.query('COMMIT');

        this.logger.info('[Repository] 映射保存成功', { 
          matchId: mappingData.match_id,
          hash: mappingData.oddsportal_hash,
          traceId: this.traceId
        });

        return {
          success: true,
          matchId: result.matchId,
          wasInsert: result.wasInsert,
          updated
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
        if (this._isSeasonHashUniqueViolation(error, mappingData)) {
          throw new RepositoryError(
            `赛季 hash 冲突: season=${mappingData.season}, hash=${mappingData.oddsportal_hash}, match_id=${mappingData.match_id}`,
            'HASH_CONFLICT',
            error,
            {
              season: mappingData.season,
              oddsportal_hash: mappingData.oddsportal_hash,
              match_id: mappingData.match_id
            }
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
      params.push(mappingData.match_confidence ?? (RECON_CONFIG.matching || {}).confidence_threshold);
    }

    if (hasOptionalFields.mapping_method) {
      columns.push('mapping_method');
      values.push(`$${params.length + 1}`);
      params.push(mappingData.mapping_method || 'protocol_extract');
    }

    if (hasOptionalFields.is_reversed) {
      columns.push('is_reversed');
      values.push(`$${params.length + 1}`);
      params.push(Boolean(mappingData.is_reversed));
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
      hasOptionalFields.mapping_method ? ', mapping_method = EXCLUDED.mapping_method' : '',
      hasOptionalFields.is_reversed ? ', is_reversed = EXCLUDED.is_reversed' : ''
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

      return fields.reduce((accumulator, fieldName) => {
        accumulator[fieldName] = existingFields.includes(fieldName);
        return accumulator;
      }, {});
    }, 'checkOptionalFields');
  }

  /**
   * 批量保存映射 (事务保护)
   * @param {Array} mappings - 映射列表
   * @returns {Promise<Object>} 批量保存结果
   * @throws {RepositoryError}
   */
  async batchSaveOddsPortalMappings(mappings, options = {}) {
    if (!Array.isArray(mappings) || mappings.length === 0) {
      return { success: true, inserted: 0, failed: 0, errors: [], updated: 0 };
    }

    const orderedMappings = [...mappings].sort((a, b) =>
      String(a.match_id).localeCompare(String(b.match_id))
    );

    const requiredFields = ['match_id', 'oddsportal_hash', 'full_url', 'season', 'league_name', 'home_team', 'away_team'];
    for (const mapping of orderedMappings) {
      const missing = requiredFields.filter(f => !mapping[f]);
      if (missing.length > 0) {
        throw new RepositoryError(
          `缺少必填字段: ${missing.join(', ')}`,
          'MISSING_REQUIRED_FIELDS'
        );
      }
    }

    await this.ensureOddsPortalMappingSchema();

    const optionalFields = ['match_confidence', 'mapping_method', 'is_reversed'];
    const hasOptionalFields = await this._checkOptionalFields('matches_oddsportal_mapping', optionalFields);

    return this._executeWithRetry(async () => {
      const client = await this.dbPool.connect();
      const results = { inserted: 0, failed: 0, errors: [], updated: 0 };
      const pipelineStatus = options.pipelineStatus || null;
      
      try {
        await client.query('BEGIN');
        await this._auditSeasonHashConflictsWithClient(client, orderedMappings);
        
        for (const mapping of orderedMappings) {
          try {
            await this._saveOddsPortalMappingWithClient(client, mapping, hasOptionalFields);
            results.inserted++;
          } catch (error) {
            results.failed++;
            results.errors.push({ matchId: mapping.match_id, error: error.message });
            throw error;
          }
        }

        if (pipelineStatus) {
          results.updated = await this._updateMatchPipelineStatusWithClient(
            client,
            orderedMappings.map((mapping) => String(mapping.match_id)),
            pipelineStatus
          );
        }
        
        await client.query('COMMIT');
        return { success: true, ...results };
      } catch (error) {
        await client.query('ROLLBACK');

        if (error instanceof RepositoryError) {
          throw error;
        }

        if (orderedMappings.some((mapping) => this._isSeasonHashUniqueViolation(error, mapping))) {
          throw new RepositoryError(
            `批量保存映射失败: 检测到赛季 hash 冲突`,
            'HASH_CONFLICT',
            error,
            {
              match_ids: orderedMappings.map((mapping) => String(mapping.match_id)),
              season: orderedMappings[0]?.season || null
            }
          );
        }

        if (error.code === '23505') {
          throw new RepositoryError(
            `批量保存映射失败: 唯一约束冲突 - ${error.message}`,
            'UNIQUE_VIOLATION',
            error
          );
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
   * 批量更新比赛流水线状态
   * @param {Array<string>} matchIds - 比赛 ID 列表
   * @param {string} status - 新状态
   * @returns {Promise<{success: boolean, updated: number}>}
   */
  async batchUpdateMatchPipelineStatus(matchIds, status, options = {}) {
    if (!Array.isArray(matchIds) || matchIds.length === 0) {
      return { success: true, updated: 0 };
    }

    const orderedMatchIds = [...new Set(matchIds.map((id) => String(id)))]
      .sort((a, b) => a.localeCompare(b));

    return this._executeWithRetry(async () => {
      const client = await this.dbPool.connect();

      try {
        await client.query('BEGIN');
        const updated = await this._updateMatchPipelineStatusWithClient(client, orderedMatchIds, status, options);
        await client.query('COMMIT');
        return { success: true, updated };
      } catch (error) {
        await client.query('ROLLBACK');
        throw new RepositoryError(
          `批量更新比赛流水线状态失败: ${error.message}`,
          'BATCH_STATUS_UPDATE_FAILED',
          error
        );
      } finally {
        client.release();
      }
    }, 'batchUpdateMatchPipelineStatus');
  }

  /**
   * 使用共享 client 批量更新比赛流水线状态
   * @private
   * @param {Object} client - PostgreSQL client
   * @param {Array<string>} matchIds - 比赛 ID 列表
   * @param {string} status - 新状态
   * @returns {Promise<number>}
   */
  async _updateMatchPipelineStatusWithClient(client, matchIds, status, options = {}) {
    if (!Array.isArray(matchIds) || matchIds.length === 0) {
      return 0;
    }

    const season = options.season ? String(options.season) : null;
    const expectedCurrentStatus = options.expectedCurrentStatus || null;
    let query = `
      UPDATE matches m
      SET pipeline_status = $2,
          updated_at = NOW()
      WHERE m.match_id = ANY($1::text[])
    `;
    const params = [matchIds, status];

    if (status === 'RECON_MISMATCH') {
      params.push(expectedCurrentStatus || 'harvested');
      query += `
        AND m.pipeline_status = $3
        AND NOT EXISTS (
          SELECT 1
          FROM matches_oddsportal_mapping map
          WHERE map.match_id = m.match_id
      `;

      if (season) {
        params.push(season);
        query += `
            AND map.season = $4
        `;
      }

      query += `
        )
      `;
    }

    const result = await client.query(query, params);
    return result.rowCount || 0;
  }

  _isSeasonHashUniqueViolation(error, mappingData = null) {
    if (!error || error.code !== '23505') {
      return false;
    }

    const constraint = String(error.constraint || '');
    const detail = String(error.detail || error.message || '');
    if (constraint === 'idx_mapping_season_hash_unique') {
      return true;
    }

    if (detail.includes('(season, oddsportal_hash)')) {
      return true;
    }

    if (!mappingData) {
      return false;
    }

    return detail.includes(String(mappingData.season || ''))
      && detail.includes(String(mappingData.oddsportal_hash || ''));
  }

  async _auditSeasonHashConflictsWithClient(client, mappings = []) {
    if (!Array.isArray(mappings) || mappings.length === 0) {
      return;
    }

    const uniqueMappings = new Map();
    for (const mapping of mappings) {
      const key = `${mapping.season}::${mapping.oddsportal_hash}`;
      if (!uniqueMappings.has(key)) {
        uniqueMappings.set(key, new Set());
      }
      uniqueMappings.get(key).add(String(mapping.match_id));
    }

    for (const [key, matchIds] of uniqueMappings.entries()) {
      if (matchIds.size > 1) {
        const [season, oddsportalHash] = key.split('::');
        const conflict = {
          season,
          oddsportal_hash: oddsportalHash,
          incoming_match_ids: [...matchIds].sort()
        };
        this.logger.error('[Repository] 检测到批内 hash 冲突', conflict);
        throw new RepositoryError(
          `批内出现重复 season/hash 组合: season=${season}, hash=${oddsportalHash}`,
          'HASH_CONFLICT',
          null,
          conflict
        );
      }
    }

    const seasons = [...new Set(mappings.map((mapping) => String(mapping.season)))];
    const hashes = [...new Set(mappings.map((mapping) => String(mapping.oddsportal_hash)))];
    const result = await client.query(`
      SELECT season, oddsportal_hash, match_id, full_url
      FROM matches_oddsportal_mapping
      WHERE season = ANY($1::text[])
        AND oddsportal_hash = ANY($2::text[])
    `, [seasons, hashes]);

    for (const row of result.rows || []) {
      const key = `${row.season}::${row.oddsportal_hash}`;
      const incomingMatchIds = uniqueMappings.get(key);
      if (!incomingMatchIds || incomingMatchIds.has(String(row.match_id))) {
        continue;
      }

      const conflict = {
        season: row.season,
        oddsportal_hash: row.oddsportal_hash,
        existing_match_id: String(row.match_id),
        incoming_match_ids: [...incomingMatchIds].sort(),
        existing_full_url: row.full_url || null
      };

      this.logger.error('[Repository] 检测到赛季 hash 冲突', conflict);
      throw new RepositoryError(
        `赛季 hash 冲突: season=${row.season}, hash=${row.oddsportal_hash}, existing_match_id=${row.match_id}`,
        'HASH_CONFLICT',
        null,
        conflict
      );
    }
  }

  /**
   * 持久化 L1 赛程
   * @param {Array<Object>} fixtures - 赛程列表
   * @returns {Promise<Object>} 入库结果
   */
  async persist(fixtures) {
    if (!Array.isArray(fixtures) || fixtures.length === 0) {
      return { total: 0, inserted: 0, updated: 0, failed: 0, errors: [] };
    }

    await this.init();

    const results = {
      total: fixtures.length,
      inserted: 0,
      updated: 0,
      failed: 0,
      errors: []
    };

    for (let i = 0; i < fixtures.length; i += this.batchSize) {
      const batch = fixtures
        .slice(i, i + this.batchSize)
        .map((fixture) => ({
          ...this._sanitizeFixtureForPersistence(fixture),
          season: Normalizer.normalizeSeason(fixture.season),
          home_team: this._truncate(Normalizer.normalizeTeamName(fixture.home_team), 200),
          away_team: this._truncate(Normalizer.normalizeTeamName(fixture.away_team), 200),
          status: this._truncate(Normalizer.normalizeStatus(fixture.status), 50),
          is_finished: fixture.is_finished ?? Normalizer.normalizeStatus(fixture.status) === 'finished',
          data_source: this._truncate(fixture.data_source || 'FotMob', 50)
        }))
        .sort((a, b) => String(a.match_id).localeCompare(String(b.match_id)));

      try {
        const batchResult = await this._persistBatch(batch);
        results.inserted += batchResult.inserted;
        results.updated += batchResult.updated;
      } catch (error) {
        results.failed += batch.length;
        results.errors.push({
          batchStart: i,
          batchSize: batch.length,
          error: error.message
        });
      }
    }

    return results;
  }

  /**
   * 批量持久化单批赛程
   * @private
   * @param {Array<Object>} batch - 单批赛程
   * @returns {Promise<{inserted: number, updated: number}>}
   */
  async _persistBatch(batch) {
    return this._executeWithRetry(async () => {
      const client = await this.dbPool.connect();
      try {
        const values = [];
        const rows = batch.map((fixture, index) => {
          const offset = index * 12;
          values.push(
            fixture.match_id,
            fixture.external_id,
            fixture.league_name,
            fixture.season,
            fixture.home_team,
            fixture.away_team,
            fixture.match_date,
            fixture.home_score ?? null,
            fixture.away_score ?? null,
            fixture.status,
            fixture.is_finished,
            fixture.data_source
          );
          return `($${offset + 1}, $${offset + 2}, $${offset + 3}, $${offset + 4}, $${offset + 5}, $${offset + 6}, $${offset + 7}, $${offset + 8}, $${offset + 9}, $${offset + 10}, $${offset + 11}, $${offset + 12})`;
        });

        const query = `
          INSERT INTO matches (
            match_id, external_id, league_name, season, home_team, away_team,
            match_date, home_score, away_score, status, is_finished, data_source
          )
          VALUES ${rows.join(', ')}
          ON CONFLICT (match_id) DO UPDATE SET
            external_id = EXCLUDED.external_id,
            league_name = EXCLUDED.league_name,
            season = EXCLUDED.season,
            home_team = EXCLUDED.home_team,
            away_team = EXCLUDED.away_team,
            match_date = EXCLUDED.match_date,
            home_score = COALESCE(matches.home_score, EXCLUDED.home_score),
            away_score = COALESCE(matches.away_score, EXCLUDED.away_score),
            status = EXCLUDED.status,
            is_finished = EXCLUDED.is_finished,
            data_source = EXCLUDED.data_source,
            updated_at = NOW()
          RETURNING (xmax = 0) AS inserted;
        `;

        const result = await client.query(query, values);
        const inserted = result.rows.filter((row) => row.inserted).length;
        const updated = result.rows.length - inserted;
        return { inserted, updated };
      } finally {
        client.release();
      }
    }, 'persistFixtures');
  }

  _sanitizeFixtureForPersistence(fixture) {
    return {
      ...fixture,
      match_id: this._truncate(String(fixture.match_id || ''), 50),
      external_id: this._truncate(String(fixture.external_id || ''), 100),
      league_name: this._truncate(String(fixture.league_name || ''), 100),
      match_date: this._safeDate(fixture.match_date)
    };
  }

  _truncate(value, maxLength) {
    return String(value || '').slice(0, maxLength);
  }

  _safeDate(value) {
    if (!value) {
      return null;
    }

    const date = value instanceof Date ? value : new Date(value);
    return Number.isNaN(date.getTime()) ? null : date;
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
   * 获取可执行 Recon 的比赛（已完成 Harvest 且尚未建立映射）
   * @param {string} season - 赛季
   * @param {string} leagueName - 联赛名称
   * @param {number|null} limit - 条数上限
   * @returns {Promise<Array>}
   */
  async getReconEligibleMatches(season, leagueName, limit = null) {
    return this._executeWithRetry(async () => {
      const client = await this.dbPool.connect();
      try {
        const params = [leagueName, season];
        let query = `
          SELECT m.match_id, m.home_team, m.away_team, m.match_date, m.league_name, m.season
          FROM matches m
          WHERE m.league_name = $1
            AND m.season = $2
            AND m.pipeline_status = 'harvested'
            AND NOT EXISTS (
              SELECT 1
              FROM matches_oddsportal_mapping map
              WHERE map.match_id = m.match_id
                AND map.season = $2
            )
          ORDER BY m.match_date DESC, m.match_id DESC
        `;

        if (Number.isInteger(limit) && limit > 0) {
          params.push(limit);
          query += ` LIMIT $${params.length}`;
        }

        const result = await client.query(query, params);
        return result.rows;
      } finally {
        client.release();
      }
    }, 'getReconEligibleMatches');
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
