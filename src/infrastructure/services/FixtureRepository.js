'use strict';

const { Normalizer } = require('../../utils/Normalizer');
const { loadReconConfig } = require('../recon/services/ReconServiceConfig');
const mappingMigration = require('./migrations/dedupeMappings');
const { ReconConflictArbiter } = require('./recon/ReconConflictArbiter');
const { MatchIdentityResolver } = require('./recon/MatchIdentityResolver');
const { MatchCanonicalJanitor } = require('./recon/MatchCanonicalJanitor');
const { ReconSchemaJanitor } = require('./recon/ReconSchemaJanitor');
const { ReconMappingStore } = require('./recon/ReconMappingStore');

function loadRepositoryConfig() {
  try { return loadReconConfig(process.env.RECON_CONFIG_PATH); } catch (error) {
    console.error('[FixtureRepository] 警告: 无法加载 recon 配置', error.message);
    throw error;
  }
}

const RECON_CONFIG = loadRepositoryConfig();
const SQL_TEMPLATES = RECON_CONFIG.sql_templates || {};
const REPOSITORY_CONFIG = RECON_CONFIG.repository || {};
const RETRY_CONFIG = REPOSITORY_CONFIG.retry || {};
const POOL_CONFIG = REPOSITORY_CONFIG.pool || {};
const CONFLICT_ARBITER_CONFIG = REPOSITORY_CONFIG.conflict_arbiter || {};
const IDENTITY_INACTIVE_STATUSES = REPOSITORY_CONFIG.identity_inactive_statuses || [];

class RepositoryError extends Error {
  constructor(message, code, originalError = null, details = null) {
    super(message);
    this.name = 'RepositoryError';
    this.code = code;
    this.originalError = originalError;
    this.details = details || null;
    this.timestamp = new Date().toISOString();
  }
}

class FixtureRepository {
  constructor(options = {}) {
    this.dbPool = options.dbPool;
    this.logger = options.logger || { info() {}, warn() {}, error() {} };
    this.batchSize = options.batchSize ?? REPOSITORY_CONFIG.batch_size ?? 50;
    this.maxRetries = options.maxRetries ?? RETRY_CONFIG.max_retries;
    this.retryDelayMs = options.retryDelayMs ?? RETRY_CONFIG.retry_delay_ms;
    this.maxRetryWindowMs = options.maxRetryWindowMs ?? RETRY_CONFIG.max_retry_window_ms;
    this.retryBackoffMultiplier = options.retryBackoffMultiplier ?? RETRY_CONFIG.backoff_multiplier;
    this.traceId = options.traceId || null;
    this.mappingMigration = options.mappingMigration || mappingMigration;
    this.sleep = options.sleep || ((ms) => new Promise((resolve) => setTimeout(resolve, ms)));
    this.now = options.now || (() => Date.now());

    this.conflictArbiter = new ReconConflictArbiter({
      sameFixtureThreshold: options.conflictArbiterOptions?.sameFixtureThreshold
        ?? CONFLICT_ARBITER_CONFIG.same_fixture_threshold,
      sameFixtureWindowMs: options.conflictArbiterOptions?.sameFixtureWindowMs
        ?? CONFLICT_ARBITER_CONFIG.same_fixture_window_ms
    });
    this.schemaJanitor = new ReconSchemaJanitor({
      getDbPool: () => this.dbPool,
      executeWithRetry: this._executeWithRetry.bind(this),
      mappingMigration: this.mappingMigration,
      logger: this.logger,
      RepositoryError
    });
    this.matchIdentityResolver = options.matchIdentityResolver || new MatchIdentityResolver({
      getDbPool: () => this.dbPool,
      executeWithRetry: this._executeWithRetry.bind(this),
      logger: this.logger,
      RepositoryError
    });
    this.matchCanonicalJanitor = options.matchCanonicalJanitor || new MatchCanonicalJanitor({
      getDbPool: () => this.dbPool,
      executeWithRetry: this._executeWithRetry.bind(this),
      logger: this.logger,
      RepositoryError,
      identityInactiveStatuses: options.identityInactiveStatuses || IDENTITY_INACTIVE_STATUSES
    });
    this.mappingStore = new ReconMappingStore({
      getDbPool: () => this.dbPool,
      logger: this.logger,
      traceId: this.traceId,
      executeWithRetry: this._executeWithRetry.bind(this),
      ensureSchema: () => this.ensureOddsPortalMappingSchema(),
      updateMatchPipelineStatusWithClient: this._updateMatchPipelineStatusWithClient.bind(this),
      RepositoryError,
      arbiter: this.conflictArbiter,
      sqlTemplates: SQL_TEMPLATES,
      reconConfig: RECON_CONFIG
    });
    Object.defineProperties(this, {
      _mappingSchemaEnsured: {
        get: () => this.schemaJanitor.mappingSchemaEnsured,
        set: (value) => { this.schemaJanitor.mappingSchemaEnsured = Boolean(value); }
      },
      _mappingHashUniquenessEnsured: {
        get: () => this.schemaJanitor.mappingHashUniquenessEnsured,
        set: (value) => { this.schemaJanitor.mappingHashUniquenessEnsured = Boolean(value); }
      }
    });
  }
  async init() {
    if (!this.dbPool) {
      const { Pool } = require('pg');
      this.dbPool = new Pool({
        host: process.env.DB_HOST || 'localhost',
        port: Number.parseInt(process.env.DB_PORT || '5432', 10),
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
  async ensureOddsPortalMappingSchema() { return this.schemaJanitor.ensureOddsPortalMappingSchema(); }
  async auditCanonicalIdentityDuplicates(options = {}) { return this.matchCanonicalJanitor.auditDuplicateGroups(options); }
  async repairCanonicalIdentity(options = {}) { return this.matchCanonicalJanitor.consolidateDuplicateGroups(options); }
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
          const plannedDelayMs = Math.round(
            this.retryDelayMs * Math.max(1, attempt) ** this.retryBackoffMultiplier
          );
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
  async saveOddsPortalMapping(mappingData, options = {}) { return this.mappingStore.saveOddsPortalMapping(mappingData, options); }
  async batchSaveOddsPortalMappings(mappings, options = {}) { return this.mappingStore.batchSaveOddsPortalMappings(mappings, options); }
  async resolveHashConflict(conflict, options = {}) { return this.mappingStore.resolveHashConflict(conflict, options); }
  async batchUpdateMatchPipelineStatus(matchIds, status, options = {}) {
    if (!Array.isArray(matchIds) || matchIds.length === 0) {
      return { success: true, updated: 0 };
    }
    const orderedMatchIds = [...new Set(matchIds.map((id) => String(id)))]
      .sort((left, right) => left.localeCompare(right));
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
  async _updateMatchPipelineStatusWithClient(client, matchIds, status, options = {}) {
    if (!Array.isArray(matchIds) || matchIds.length === 0) {
      return 0;
    }
    const season = options.season ? String(options.season) : null;
    const expectedCurrentStatuses = Array.isArray(options.expectedCurrentStatus)
      ? options.expectedCurrentStatus
        .map((value) => String(value || '').trim())
        .filter(Boolean)
      : options.expectedCurrentStatus
        ? [String(options.expectedCurrentStatus).trim()]
        : [];
    let query = `
      UPDATE matches m
      SET pipeline_status = $2,
          updated_at = NOW()
      WHERE m.match_id = ANY($1::text[])
    `;
    const params = [matchIds, status];
    if (status === 'RECON_MISMATCH') {
      const allowedStatuses = expectedCurrentStatuses.length > 0 ? expectedCurrentStatuses : ['harvested'];
      params.push(allowedStatuses);
      query += `
        AND m.pipeline_status = ANY($3::text[])
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
  async persist(fixtures) {
    if (!Array.isArray(fixtures) || fixtures.length === 0) {
      return { total: 0, inserted: 0, updated: 0, failed: 0, errors: [] };
    }
    await this.init();
    const normalizedFixtures = fixtures.map((fixture) => ({
      ...fixture,
      home_team: Normalizer.normalizeTeamName(fixture.home_team),
      away_team: Normalizer.normalizeTeamName(fixture.away_team)
    }));
    const canonicalFixtures = await this.matchIdentityResolver.resolveCanonicalFixtures(normalizedFixtures);
    const results = { total: fixtures.length, inserted: 0, updated: 0, failed: 0, errors: [] };
    for (let index = 0; index < canonicalFixtures.length; index += this.batchSize) {
      const batch = canonicalFixtures
        .slice(index, index + this.batchSize)
        .map((fixture) => ({
          ...this._sanitizeFixtureForPersistence(fixture),
          season: Normalizer.normalizeSeason(fixture.season),
          home_team: this._truncate(Normalizer.normalizeTeamName(fixture.home_team), 200),
          away_team: this._truncate(Normalizer.normalizeTeamName(fixture.away_team), 200),
          status: this._truncate(Normalizer.normalizeStatus(fixture.status), 50),
          is_finished: fixture.is_finished ?? Normalizer.normalizeStatus(fixture.status) === 'finished',
          data_source: this._requireNonEmptyString(fixture, 'data_source', 50)
        }))
        .sort((left, right) => String(left.match_id).localeCompare(String(right.match_id)));
      try {
        const batchResult = await this._persistBatch(batch);
        results.inserted += batchResult.inserted;
        results.updated += batchResult.updated;
      } catch (error) {
        results.failed += batch.length;
        results.errors.push({
          batchStart: index,
          batchSize: batch.length,
          error: error.message
        });
      }
    }
    return results;
  }
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
        const result = await client.query(`
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
        `, values);

        const inserted = result.rows.filter((row) => row.inserted).length;
        return { inserted, updated: result.rows.length - inserted };
      } finally {
        client.release();
      }
    }, 'persistFixtures');
  }
  _sanitizeFixtureForPersistence(fixture) {
    return { ...fixture, match_id: this._requireNonEmptyString(fixture, 'match_id', 50), external_id: this._requireNonEmptyString(fixture, 'external_id', 100), league_name: this._truncate(String(fixture.league_name || ''), 100), match_date: this._safeDate(fixture.match_date) };
  }
  _requireNonEmptyString(fixture, fieldName, maxLength = 100) {
    const value = String(fixture?.[fieldName] || '').trim();
    if (!value) {
      throw new RepositoryError(
        `比赛缺少必填 identity 字段: ${fieldName}`,
        'CANONICAL_IDENTITY_INVALID',
        null,
        { field: fieldName, match_id: fixture?.match_id ? String(fixture.match_id) : null }
      );
    }
    return this._truncate(value, maxLength);
  }
  _truncate(value, maxLength) { return String(value || '').slice(0, maxLength); }
  _safeDate(value) { const date = value ? (value instanceof Date ? value : new Date(value)) : null; return !date || Number.isNaN(date.getTime()) ? null : date; }
  async findMatchByTeams(homeTeam, awayTeam, season) {
    return this._executeWithRetry(async () => {
      const client = await this.dbPool.connect();
      try {
        const result = await client.query(
          SQL_TEMPLATES.find_match_by_teams || `
            SELECT match_id, home_team, away_team, match_date
            FROM matches
            WHERE season = $1
              AND (
                (LOWER(home_team) = LOWER($2) AND LOWER(away_team) = LOWER($3))
                OR (LOWER(home_team) = LOWER($3) AND LOWER(away_team) = LOWER($2))
              )
            LIMIT 1;
          `,
          [season, homeTeam, awayTeam]
        );

        if (result.rows.length === 0) {
          return null;
        }

        return {
          matchId: result.rows[0].match_id,
          confidence: 1,
          method: 'exact',
          dbHome: result.rows[0].home_team,
          dbAway: result.rows[0].away_team
        };
      } finally {
        client.release();
      }
    }, 'findMatchByTeams');
  }
  async findMatchesBySeason(season) {
    return this._executeWithRetry(async () => {
      const client = await this.dbPool.connect();
      try {
        const result = await client.query(
          SQL_TEMPLATES.find_matches_by_season || `
            SELECT match_id, home_team, away_team, match_date
            FROM matches
            WHERE season = $1
            ORDER BY match_date;
          `,
          [season]
        );
        return result.rows;
      } finally {
        client.release();
      }
    }, 'findMatchesBySeason');
  }
  async getUnstitchedMatches(season, leagueName) {
    return this._executeWithRetry(async () => {
      const client = await this.dbPool.connect();
      try {
        const result = await client.query(
          SQL_TEMPLATES.get_unstitched_matches || `
            SELECT m.match_id, m.home_team, m.away_team, m.match_date
            FROM matches m
            LEFT JOIN matches_oddsportal_mapping map
              ON m.match_id = map.match_id AND map.season = $2
            WHERE m.league_name = $1
              AND m.season = $2
              AND map.match_id IS NULL
            ORDER BY m.match_date;
          `,
          [leagueName, season]
        );
        return result.rows;
      } finally {
        client.release();
      }
    }, 'getUnstitchedMatches');
  }
  async getReconEligibleMatches(season, leagueName, limitOrOptions = null) {
    return this._executeWithRetry(async () => {
      const client = await this.dbPool.connect();
      try {
        const normalizedOptions = (
          Number.isInteger(limitOrOptions) || limitOrOptions === null
            ? { limit: limitOrOptions }
            : (limitOrOptions || {})
        );
        const limit = Number.isInteger(normalizedOptions.limit) ? normalizedOptions.limit : null;
        const allowMismatchRetry = normalizedOptions.allowMismatchRetry === true;
        const eligibleStatuses = allowMismatchRetry
          ? ['harvested', 'RECON_MISMATCH']
          : ['harvested'];
        const params = [leagueName, season];
        let query = `
          SELECT m.match_id, m.home_team, m.away_team, m.match_date, m.league_name, m.season, m.pipeline_status
          FROM matches m
          WHERE m.league_name = $1
            AND m.season = $2
            AND m.pipeline_status = ANY($3::text[])
            AND NOT EXISTS (
              SELECT 1
              FROM matches_oddsportal_mapping map
              WHERE map.match_id = m.match_id
                AND map.season = $2
            )
          ORDER BY m.match_date DESC, m.match_id DESC
        `;
        params.push(eligibleStatuses);
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
  async getMappingStats(season) {
    return this._executeWithRetry(async () => {
      const client = await this.dbPool.connect();
      try {
        const result = await client.query(
          SQL_TEMPLATES.get_mapping_stats || `
            SELECT
              COUNT(*) as total,
              COUNT(*) FILTER (WHERE status = 'pending') as pending,
              COUNT(*) FILTER (WHERE status = 'harvested') as harvested
            FROM matches_oddsportal_mapping
            WHERE season = $1
          `,
          [season]
        );
        return result.rows[0] || { total: 0, pending: 0, harvested: 0 };
      } finally {
        client.release();
      }
    }, 'getMappingStats');
  }
  async close() { if (this.dbPool && typeof this.dbPool.end === 'function') { await this.dbPool.end(); this.logger.info('[Repository] 数据库连接池已关闭'); } }
}

module.exports = { FixtureRepository, RepositoryError };
