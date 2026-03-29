'use strict';

class ReconMappingStore {
  constructor(options = {}) {
    this.getDbPool = options.getDbPool;
    this.logger = options.logger || { info() {}, warn() {}, error() {} };
    this.traceId = options.traceId || null;
    this.executeWithRetry = options.executeWithRetry;
    this.ensureSchema = options.ensureSchema;
    this.updateMatchPipelineStatusWithClient = options.updateMatchPipelineStatusWithClient;
    this.RepositoryError = options.RepositoryError;
    this.arbiter = options.arbiter;
    this.sqlTemplates = options.sqlTemplates || {};
    this.reconConfig = options.reconConfig || {};
  }

  async saveOddsPortalMapping(mappingData, options = {}) {
    this.assertRequiredFields(mappingData);
    await this.ensureSchema();

    const hasOptionalFields = await this.checkOptionalFields('matches_oddsportal_mapping', [
      'match_confidence',
      'mapping_method',
      'is_reversed'
    ]);

    return this.executeWithRetry(async () => {
      const client = await this.getDbPool().connect();
      const pipelineStatus = options.pipelineStatus || null;

      try {
        await client.query('BEGIN');
        const audit = await this.auditSeasonHashConflictsWithClient(client, [mappingData], { pipelineStatus });
        const targetMapping = (audit.remainingMappings || [])[0] || null;
        const linkedStatusUpdated = Number(audit.linkedStatusUpdated || 0);

        if (!targetMapping) {
          await client.query('COMMIT');
          return {
            success: true,
            matchId: String(mappingData.match_id),
            wasInsert: false,
            updated: linkedStatusUpdated
          };
        }

        const result = await this.saveOddsPortalMappingWithClient(client, targetMapping, hasOptionalFields);
        let updated = linkedStatusUpdated;

        if (pipelineStatus) {
          updated += await this.updateMatchPipelineStatusWithClient(
            client,
            [String(targetMapping.match_id)],
            pipelineStatus
          );
        }

        await client.query('COMMIT');
        this.logger.info('[Repository] 映射保存成功', {
          matchId: targetMapping.match_id,
          hash: targetMapping.oddsportal_hash,
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
        throw this.classifyWriteError(error, {
          mappingData,
          defaultCode: 'DATABASE_ERROR',
          defaultMessage: '数据库操作失败'
        });
      } finally {
        client.release();
      }
    }, 'saveOddsPortalMapping');
  }

  async batchSaveOddsPortalMappings(mappings, options = {}) {
    if (!Array.isArray(mappings) || mappings.length === 0) {
      return { success: true, inserted: 0, failed: 0, errors: [], updated: 0 };
    }

    const orderedMappings = [...mappings].sort((left, right) =>
      String(left.match_id).localeCompare(String(right.match_id))
    );
    orderedMappings.forEach((mapping) => this.assertRequiredFields(mapping));

    await this.ensureSchema();
    const hasOptionalFields = await this.checkOptionalFields('matches_oddsportal_mapping', [
      'match_confidence',
      'mapping_method',
      'is_reversed'
    ]);

    return this.executeWithRetry(async () => {
      const client = await this.getDbPool().connect();
      const pipelineStatus = options.pipelineStatus || null;
      const results = { inserted: 0, failed: 0, errors: [], updated: 0 };

      try {
        await client.query('BEGIN');
        const audit = await this.auditSeasonHashConflictsWithClient(client, orderedMappings, { pipelineStatus });
        const remainingMappings = audit.remainingMappings || orderedMappings;
        results.updated += Number(audit.linkedStatusUpdated || 0);

        for (const mapping of remainingMappings) {
          try {
            await this.saveOddsPortalMappingWithClient(client, mapping, hasOptionalFields);
            results.inserted++;
          } catch (error) {
            results.failed++;
            results.errors.push({ matchId: mapping.match_id, error: error.message });
            throw error;
          }
        }

        if (pipelineStatus && remainingMappings.length > 0) {
          results.updated += await this.updateMatchPipelineStatusWithClient(
            client,
            remainingMappings.map((mapping) => String(mapping.match_id)),
            pipelineStatus
          );
        }

        await client.query('COMMIT');
        return { success: true, ...results };
      } catch (error) {
        await client.query('ROLLBACK');
        if (error instanceof this.RepositoryError) {
          throw error;
        }
        if (orderedMappings.some((mapping) => this.isSeasonHashUniqueViolation(error, mapping))) {
          throw new this.RepositoryError(
            '批量保存映射失败: 检测到赛季 hash 冲突',
            'HASH_CONFLICT',
            error,
            {
              match_ids: orderedMappings.map((mapping) => String(mapping.match_id)),
              season: orderedMappings[0]?.season || null
            }
          );
        }
        if (error.code === '23505') {
          throw new this.RepositoryError(
            `批量保存映射失败: 唯一约束冲突 - ${error.message}`,
            'UNIQUE_VIOLATION',
            error
          );
        }
        throw new this.RepositoryError(
          `批量保存映射失败: ${error.message}`,
          'BATCH_SAVE_FAILED',
          error
        );
      } finally {
        client.release();
      }
    }, 'batchSaveOddsPortalMappings');
  }

  async resolveHashConflict(conflict, options = {}) {
    return this.executeWithRetry(async () => {
      const client = await this.getDbPool().connect();

      try {
        await client.query('BEGIN');
        const result = await this.resolveHashConflictWithClient(client, {
          ...conflict,
          pipelineStatus: options.pipelineStatus || null
        });

        if (!result?.resolved) {
          throw new this.RepositoryError(
            'HASH_CONFLICT 无法自动自愈，需人工审计',
            'HASH_CONFLICT',
            null,
            conflict || null
          );
        }

        await client.query('COMMIT');
        return result;
      } catch (error) {
        await client.query('ROLLBACK');
        throw error;
      } finally {
        client.release();
      }
    }, 'resolveHashConflict');
  }

  assertRequiredFields(mappingData) {
    const requiredFields = ['match_id', 'oddsportal_hash', 'full_url', 'season', 'league_name', 'home_team', 'away_team'];
    const missing = requiredFields.filter((field) => !mappingData[field]);
    if (missing.length > 0) {
      throw new this.RepositoryError(
        `缺少必填字段: ${missing.join(', ')}`,
        'MISSING_REQUIRED_FIELDS'
      );
    }
  }

  async saveOddsPortalMappingWithClient(client, mappingData, hasOptionalFields) {
    const columns = ['match_id', 'oddsportal_hash', 'full_url', 'season', 'league_name', 'home_team', 'away_team', 'status', 'created_at', 'updated_at'];
    const values = ['$1', '$2', '$3', '$4', '$5', '$6', '$7', '$8', 'NOW()', 'NOW()'];
    const params = [
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
      params.push(mappingData.match_confidence ?? (this.reconConfig.matching || {}).confidence_threshold);
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

    const query = (this.sqlTemplates.save_mapping || `
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
    `)
      .replace('{columns}', columns.join(', '))
      .replace('{values}', values.join(', '))
      .replace('{optional_updates}', [
        hasOptionalFields.match_confidence ? ', match_confidence = EXCLUDED.match_confidence' : '',
        hasOptionalFields.mapping_method ? ', mapping_method = EXCLUDED.mapping_method' : '',
        hasOptionalFields.is_reversed ? ', is_reversed = EXCLUDED.is_reversed' : ''
      ].join(''));

    const result = await client.query(query, params);
    return {
      matchId: result.rows[0]?.match_id,
      wasInsert: result.rows.length > 0
    };
  }

  async checkOptionalFields(tableName, fields) {
    return this.executeWithRetry(async () => {
      const result = await this.getDbPool().query(
        this.sqlTemplates.check_optional_fields || `
          SELECT column_name
          FROM information_schema.columns
          WHERE table_name = $1 AND column_name = ANY($2)
        `,
        [tableName, fields]
      );
      const existingFields = result.rows.map((row) => row.column_name);
      return fields.reduce((accumulator, fieldName) => ({
        ...accumulator,
        [fieldName]: existingFields.includes(fieldName)
      }), {});
    }, 'checkOptionalFields');
  }

  async auditSeasonHashConflictsWithClient(client, mappings = [], options = {}) {
    if (!Array.isArray(mappings) || mappings.length === 0) {
      return { remainingMappings: [], linkedStatusUpdated: 0 };
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
        throw new this.RepositoryError(
          `批内出现重复 season/hash 组合: season=${season}, hash=${oddsportalHash}`,
          'HASH_CONFLICT',
          null,
          conflict
        );
      }
    }

    const seasons = [...new Set(mappings.map((mapping) => String(mapping.season)))];
    const hashes = [...new Set(mappings.map((mapping) => String(mapping.oddsportal_hash)))];
    const mappingByMatchId = new Map(mappings.map((mapping) => [String(mapping.match_id), mapping]));
    const handledMatchIds = new Set();
    let linkedStatusUpdated = 0;

    const result = await client.query(`
      SELECT season, oddsportal_hash, match_id, full_url, home_team, away_team, updated_at
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

      if (incomingMatchIds.size === 1) {
        const incomingMatchId = [...incomingMatchIds][0];
        const resolution = await this.resolveHashConflictWithClient(client, {
          existingMapping: row,
          incomingMapping: mappingByMatchId.get(incomingMatchId),
          pipelineStatus: options.pipelineStatus || null
        });

        if (resolution?.resolved) {
          handledMatchIds.add(String(incomingMatchId));
          linkedStatusUpdated += Number(resolution.linkedStatusUpdated || 0);
          continue;
        }
      }

      const conflict = {
        season: row.season,
        oddsportal_hash: row.oddsportal_hash,
        existing_match_id: String(row.match_id),
        incoming_match_ids: [...incomingMatchIds].sort(),
        existing_full_url: row.full_url || null
      };
      this.logger.error('[Repository] 检测到赛季 hash 冲突', conflict);
      throw new this.RepositoryError(
        `赛季 hash 冲突: season=${row.season}, hash=${row.oddsportal_hash}, existing_match_id=${row.match_id}`,
        'HASH_CONFLICT',
        null,
        conflict
      );
    }

    return {
      remainingMappings: mappings.filter((mapping) => !handledMatchIds.has(String(mapping.match_id))),
      linkedStatusUpdated
    };
  }

  async fetchMatchesByIdsWithClient(client, matchIds = []) {
    if (!Array.isArray(matchIds) || matchIds.length === 0) {
      return new Map();
    }

    const result = await client.query(`
      SELECT match_id, season, match_date, home_team, away_team, pipeline_status
      FROM matches
      WHERE match_id = ANY($1::text[])
    `, [[...new Set(matchIds.map((matchId) => String(matchId)))]]);

    return new Map((result.rows || []).map((row) => [String(row.match_id), row]));
  }

  async setSingleMatchPipelineStatusWithClient(client, matchId, status, options = {}) {
    const expectedCurrentStatus = options.expectedCurrentStatus || null;
    const requireNoMapping = Boolean(options.requireNoMapping);
    let query = `
      UPDATE matches m
      SET pipeline_status = $2,
          updated_at = NOW()
      WHERE m.match_id = $1
    `;
    const params = [String(matchId), status];

    if (expectedCurrentStatus) {
      params.push(expectedCurrentStatus);
      query += `
        AND m.pipeline_status = $3
      `;
    }

    if (requireNoMapping) {
      query += `
        AND NOT EXISTS (
          SELECT 1
          FROM matches_oddsportal_mapping map
          WHERE map.match_id = m.match_id
        )
      `;
    }

    const result = await client.query(query, params);
    return result.rowCount || 0;
  }

  async rebindMappingToMatchWithClient(client, existingMappingRow, incomingMapping) {
    const result = await client.query(`
      UPDATE matches_oddsportal_mapping
      SET match_id = $1,
          full_url = $2,
          league_name = $3,
          home_team = $4,
          away_team = $5,
          status = $6,
          updated_at = NOW()
      WHERE season = $7
        AND oddsportal_hash = $8
        AND match_id = $9
    `, [
      String(incomingMapping.match_id),
      incomingMapping.full_url,
      incomingMapping.league_name,
      incomingMapping.home_team,
      incomingMapping.away_team,
      incomingMapping.status || 'pending',
      incomingMapping.season,
      incomingMapping.oddsportal_hash,
      String(existingMappingRow.match_id)
    ]);

    return result.rowCount || 0;
  }

  async resolveHashConflictWithClient(client, conflict = {}) {
    const existingMapping = conflict.existingMapping || null;
    const incomingMapping = conflict.incomingMapping || null;
    const pipelineStatus = conflict.pipelineStatus || null;

    if (!existingMapping || !incomingMapping) {
      return { resolved: false };
    }

    const matchRows = await this.fetchMatchesByIdsWithClient(client, [
      existingMapping.match_id,
      incomingMapping.match_id
    ]);
    const existingMatch = matchRows.get(String(existingMapping.match_id));
    const incomingMatch = matchRows.get(String(incomingMapping.match_id));

    if (!existingMatch || !incomingMatch) {
      return { resolved: false };
    }

    const decision = this.arbiter.analyzeConflict({
      existingMatch,
      incomingMatch,
      existingMapping,
      incomingMapping
    });

    if (decision.sameFixture) {
      const winner = decision.preferredWinner;
      const winnerMatch = winner === 'existing' ? existingMatch : incomingMatch;
      const loserMatch = winner === 'existing' ? incomingMatch : existingMatch;

      if (winner === 'incoming') {
        await this.rebindMappingToMatchWithClient(client, existingMapping, incomingMapping);
        await this.setSingleMatchPipelineStatusWithClient(client, loserMatch.match_id, 'failed', {
          requireNoMapping: true
        });
        if (pipelineStatus) {
          await this.setSingleMatchPipelineStatusWithClient(client, incomingMatch.match_id, pipelineStatus, {
            expectedCurrentStatus: incomingMatch.pipeline_status || 'harvested'
          });
        }
      } else {
        await this.setSingleMatchPipelineStatusWithClient(client, incomingMatch.match_id, 'failed', {
          expectedCurrentStatus: incomingMatch.pipeline_status || 'harvested'
        });
      }

      this.logger.warn('[HEAL] 检测到同场重复 ID，已自动收敛 season/hash 冲突', {
        season: incomingMapping.season,
        oddsportal_hash: incomingMapping.oddsportal_hash,
        winner_match_id: String(winnerMatch.match_id),
        loser_match_id: String(loserMatch.match_id),
        resolution: winner === 'existing' ? 'keep_existing_mark_incoming_failed' : 'rebind_to_incoming_mark_existing_failed'
      });

      return {
        resolved: true,
        action: winner === 'existing' ? 'keep_existing_duplicate' : 'rebind_duplicate',
        linkedStatusUpdated: winner === 'incoming' && pipelineStatus ? 1 : 0
      };
    }

    if (decision.incomingScore >= this.arbiter.sameFixtureThreshold && decision.incomingScore > decision.existingScore) {
      await this.rebindMappingToMatchWithClient(client, existingMapping, incomingMapping);
      await this.setSingleMatchPipelineStatusWithClient(client, existingMatch.match_id, 'harvested', {
        expectedCurrentStatus: 'RECON_LINKED',
        requireNoMapping: true
      });
      if (pipelineStatus) {
        await this.setSingleMatchPipelineStatusWithClient(client, incomingMatch.match_id, pipelineStatus, {
          expectedCurrentStatus: incomingMatch.pipeline_status || 'harvested'
        });
      }

      this.logger.warn('[HEAL] 检测到 season/hash 映射误绑，已自动重绑到更匹配的 match_id', {
        season: incomingMapping.season,
        oddsportal_hash: incomingMapping.oddsportal_hash,
        previous_match_id: String(existingMatch.match_id),
        rebound_match_id: String(incomingMatch.match_id),
        previous_match: {
          home_team: existingMatch.home_team,
          away_team: existingMatch.away_team,
          match_date: existingMatch.match_date
        },
        rebound_match: {
          home_team: incomingMatch.home_team,
          away_team: incomingMatch.away_team,
          match_date: incomingMatch.match_date
        },
        mapping_target: {
          home_team: incomingMapping.home_team,
          away_team: incomingMapping.away_team,
          full_url: incomingMapping.full_url
        },
        scores: {
          existing: Number(decision.existingScore.toFixed(3)),
          incoming: Number(decision.incomingScore.toFixed(3))
        }
      });

      return {
        resolved: true,
        action: 'rebind_wrong_fixture',
        linkedStatusUpdated: pipelineStatus ? 1 : 0
      };
    }

    return { resolved: false };
  }

  isSeasonHashUniqueViolation(error, mappingData = null) {
    if (!error || error.code !== '23505') {
      return false;
    }

    const constraint = String(error.constraint || '');
    const detail = String(error.detail || error.message || '');
    if (constraint === 'idx_mapping_season_hash_unique' || detail.includes('(season, oddsportal_hash)')) {
      return true;
    }

    return Boolean(mappingData)
      && detail.includes(String(mappingData.season || ''))
      && detail.includes(String(mappingData.oddsportal_hash || ''));
  }

  classifyWriteError(error, { mappingData, defaultCode, defaultMessage }) {
    if (error instanceof this.RepositoryError) {
      return error;
    }
    if (error.code === '23503') {
      return new this.RepositoryError(`外键约束失败: ${error.message}`, 'FOREIGN_KEY_VIOLATION', error);
    }
    if (this.isSeasonHashUniqueViolation(error, mappingData)) {
      return new this.RepositoryError(
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
    if (error.code === '23505') {
      return new this.RepositoryError(`唯一约束冲突: ${error.message}`, 'UNIQUE_VIOLATION', error);
    }
    if (error.code === '23502') {
      return new this.RepositoryError(`非空约束失败: ${error.message}`, 'NOT_NULL_VIOLATION', error);
    }
    return new this.RepositoryError(`${defaultMessage}: ${error.message}`, defaultCode, error);
  }
}

module.exports = { ReconMappingStore };
