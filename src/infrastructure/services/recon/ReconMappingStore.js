'use strict';

const crypto = require('crypto');

function assertFunctionDependency(name, value) {
  if (typeof value !== 'function') {
    throw new TypeError(`[ReconMappingStore] 缺少必需依赖: ${name}`);
  }
}

function assertObjectDependency(name, value) {
  if (!value || typeof value !== 'object') {
    throw new TypeError(`[ReconMappingStore] 缺少必需依赖: ${name}`);
  }
}

class ReconMappingStore {
  constructor(options = {}) {
    assertFunctionDependency('getDbPool', options.getDbPool);
    assertFunctionDependency('executeWithRetry', options.executeWithRetry);
    assertFunctionDependency('ensureSchema', options.ensureSchema);
    assertFunctionDependency('updateMatchPipelineStatusWithClient', options.updateMatchPipelineStatusWithClient);
    assertFunctionDependency('RepositoryError', options.RepositoryError);
    assertObjectDependency('arbiter', options.arbiter);
    assertFunctionDependency('arbiter.analyzeConflict', options.arbiter.analyzeConflict);

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

  getPreserveLinkedStatusFlag(options = {}) {
    return options?.preserveLinkedStatus === true || options?.preserve_linked_status === true;
  }

  async saveOddsPortalMapping(mappingData, options = {}) {
    this.assertRequiredFields(mappingData);
    await this.ensureSchema();

    const hasOptionalFields = await this.checkOptionalFields('matches_oddsportal_mapping', [
      'match_confidence',
      'mapping_method',
      'is_reversed',
      'candidate_name',
      'is_evidence_only'
    ]);

    return this.executeWithRetry(async () => {
      const client = await this.getDbPool().connect();
      const pipelineStatus = options.pipelineStatus || null;
      const preserveLinkedStatus = this.getPreserveLinkedStatusFlag(options);

      try {
        await client.query('BEGIN');
        const audit = await this.auditSeasonHashConflictsWithClient(client, [mappingData], {
          pipelineStatus,
          preserveLinkedStatus,
          hasOptionalFields
        });
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

        const result = await this.saveOddsPortalMappingWithClient(
          client,
          targetMapping,
          hasOptionalFields,
          {
            pipelineStatus,
            preserveLinkedStatus
          }
        );
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
      'is_reversed',
      'candidate_name',
      'is_evidence_only'
    ]);

    return this.executeWithRetry(async () => {
      const client = await this.getDbPool().connect();
      const pipelineStatus = options.pipelineStatus || null;
      const preserveLinkedStatus = this.getPreserveLinkedStatusFlag(options);
      const results = { inserted: 0, failed: 0, errors: [], updated: 0 };

      try {
        await client.query('BEGIN');
        const audit = await this.auditSeasonHashConflictsWithClient(client, orderedMappings, {
          pipelineStatus,
          preserveLinkedStatus,
          hasOptionalFields
        });
        const remainingMappings = audit.remainingMappings || orderedMappings;
        results.updated += Number(audit.linkedStatusUpdated || 0);

        for (const mapping of remainingMappings) {
          try {
            await this.saveOddsPortalMappingWithClient(
              client,
              mapping,
              hasOptionalFields,
              {
                pipelineStatus,
                preserveLinkedStatus
              }
            );
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
          pipelineStatus: options.pipelineStatus || null,
          preserveLinkedStatus: this.getPreserveLinkedStatusFlag(options)
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

  assertMismatchEvidenceFields(evidenceData) {
    const requiredFields = ['match_id', 'season', 'league_name', 'home_team', 'away_team'];
    const missing = requiredFields.filter((field) => !evidenceData[field]);
    if (missing.length > 0) {
      throw new this.RepositoryError(
        `失配证据缺少必填字段: ${missing.join(', ')}`,
        'MISMATCH_EVIDENCE_REQUIRED_FIELDS'
      );
    }
  }

  buildEvidenceOnlyHash(matchId) {
    const digest = crypto.createHash('sha1').update(String(matchId || '')).digest('hex').slice(0, 7);
    return `~${digest}`;
  }

  async batchSaveMismatchEvidence(mismatchRecords, options = {}) {
    if (!Array.isArray(mismatchRecords) || mismatchRecords.length === 0) {
      return { success: true, saved: 0, skipped: 0 };
    }

    await this.ensureSchema();
    const hasOptionalFields = await this.checkOptionalFields('matches_oddsportal_mapping', [
      'match_confidence',
      'mapping_method',
      'is_reversed',
      'candidate_name',
      'is_evidence_only'
    ]);

    const orderedRecords = [...mismatchRecords]
      .filter(Boolean)
      .map((record) => ({ ...record, match_id: String(record.match_id) }))
      .sort((left, right) => String(left.match_id).localeCompare(String(right.match_id)));

    orderedRecords.forEach((record) => this.assertMismatchEvidenceFields(record));

    return this.executeWithRetry(async () => {
      const client = await this.getDbPool().connect();
      let saved = 0;
      let skipped = 0;

      try {
        await client.query('BEGIN');

        for (const record of orderedRecords) {
          const result = await this.saveMismatchEvidenceWithClient(client, record, hasOptionalFields);
          if (result.saved) {
            saved++;
          } else {
            skipped++;
          }
        }

        await client.query('COMMIT');
        return { success: true, saved, skipped };
      } catch (error) {
        await client.query('ROLLBACK');
        throw this.classifyWriteError(error, {
          mappingData: {
            match_ids: orderedRecords.map((record) => record.match_id),
            season: orderedRecords[0]?.season || null
          },
          defaultCode: 'DATABASE_ERROR',
          defaultMessage: '失配证据写入失败'
        });
      } finally {
        client.release();
      }
    }, 'batchSaveMismatchEvidence');
  }

  async saveMismatchEvidenceWithClient(client, evidenceData, hasOptionalFields) {
    const columns = ['match_id', 'oddsportal_hash', 'full_url', 'season', 'league_name', 'home_team', 'away_team', 'status', 'created_at', 'updated_at'];
    const values = ['$1', '$2', '$3', '$4', '$5', '$6', '$7', '$8', 'NOW()', 'NOW()'];
    const params = [
      String(evidenceData.match_id),
      this.buildEvidenceOnlyHash(evidenceData.match_id),
      evidenceData.full_url || `evidence://recon/${encodeURIComponent(String(evidenceData.match_id))}`,
      String(evidenceData.season),
      String(evidenceData.league_name),
      String(evidenceData.home_team),
      String(evidenceData.away_team),
      'pending'
    ];

    if (hasOptionalFields.match_confidence) {
      columns.push('match_confidence');
      values.push(`$${params.length + 1}`);
      params.push(Number(evidenceData.match_confidence || 0));
    }

    if (hasOptionalFields.mapping_method) {
      columns.push('mapping_method');
      values.push(`$${params.length + 1}`);
      params.push(String(evidenceData.mapping_method || 'unknown'));
    }

    if (hasOptionalFields.is_reversed) {
      columns.push('is_reversed');
      values.push(`$${params.length + 1}`);
      params.push(Boolean(evidenceData.is_reversed));
    }

    if (hasOptionalFields.candidate_name) {
      columns.push('candidate_name');
      values.push(`$${params.length + 1}`);
      params.push(evidenceData.candidate_name ? String(evidenceData.candidate_name) : null);
    }

    if (hasOptionalFields.is_evidence_only) {
      columns.push('is_evidence_only');
      values.push(`$${params.length + 1}`);
      params.push(true);
    }

    const query = `
      INSERT INTO matches_oddsportal_mapping (${columns.join(', ')})
      VALUES (${values.join(', ')})
      ON CONFLICT (match_id, season) DO UPDATE SET
        oddsportal_hash = EXCLUDED.oddsportal_hash,
        full_url = EXCLUDED.full_url,
        home_team = EXCLUDED.home_team,
        away_team = EXCLUDED.away_team,
        status = EXCLUDED.status,
        updated_at = NOW()
        ${hasOptionalFields.match_confidence ? ', match_confidence = EXCLUDED.match_confidence' : ''}
        ${hasOptionalFields.mapping_method ? ', mapping_method = EXCLUDED.mapping_method' : ''}
        ${hasOptionalFields.is_reversed ? ', is_reversed = EXCLUDED.is_reversed' : ''}
        ${hasOptionalFields.candidate_name ? ', candidate_name = EXCLUDED.candidate_name' : ''}
        ${hasOptionalFields.is_evidence_only ? ', is_evidence_only = TRUE' : ''}
      WHERE COALESCE(matches_oddsportal_mapping.is_evidence_only, FALSE) = TRUE
      RETURNING match_id;
    `;

    const result = await client.query(query, params);
    return {
      matchId: result.rows[0]?.match_id || null,
      saved: (result.rowCount || 0) > 0
    };
  }

  async saveOddsPortalMappingWithClient(client, mappingData, hasOptionalFields, runtimeOptions = {}) {
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

    if (hasOptionalFields.is_evidence_only) {
      columns.push('is_evidence_only');
      values.push(`$${params.length + 1}`);
      params.push(false);
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
        hasOptionalFields.is_reversed ? ', is_reversed = EXCLUDED.is_reversed' : '',
        hasOptionalFields.candidate_name ? ', candidate_name = NULL' : '',
        hasOptionalFields.is_evidence_only ? ', is_evidence_only = FALSE' : ''
      ].join(''));

    try {
      const result = await client.query(query, params);
      return {
        matchId: result.rows[0]?.match_id,
        wasInsert: result.rows.length > 0
      };
    } catch (error) {
      if (!this.isSeasonHashUniqueViolation(error, mappingData)) {
        throw error;
      }

      const existingMapping = await this.fetchMappingBySeasonHashWithClient(
        client,
        mappingData.season,
        mappingData.oddsportal_hash
      );
      if (!existingMapping) {
        throw error;
      }

      const forced = await this.forceOverwriteSeasonHashConflictWithClient(
        client,
        existingMapping,
        mappingData,
        hasOptionalFields,
        {
          pipelineStatus: runtimeOptions.pipelineStatus || null,
          preserveLinkedStatus: Boolean(runtimeOptions.preserveLinkedStatus),
          reason: 'unique_violation_fallback'
        }
      );

      if (forced?.resolved) {
        return {
          matchId: forced.matchId || String(mappingData.match_id),
          wasInsert: false,
          forcedOverwrite: true,
          previousMatchId: forced.previousMatchId || null
        };
      }

      throw error;
    }
  }

  async fetchMappingBySeasonHashWithClient(client, season, oddsportalHash) {
    const result = await client.query(`
      SELECT season, oddsportal_hash, match_id, full_url, league_name, home_team, away_team,
             status, match_confidence, mapping_method, is_reversed, candidate_name,
             is_evidence_only, updated_at
      FROM matches_oddsportal_mapping
      WHERE season = $1
        AND oddsportal_hash = $2
      LIMIT 1
    `, [
      String(season),
      String(oddsportalHash)
    ]);

    return result.rows[0] || null;
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
      SELECT season, oddsportal_hash, match_id, full_url, home_team, away_team, match_confidence, updated_at
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
            pipelineStatus: options.pipelineStatus || null,
            preserveLinkedStatus: Boolean(options.preserveLinkedStatus),
            hasOptionalFields: options.hasOptionalFields || {}
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
            AND COALESCE(map.is_evidence_only, FALSE) = FALSE
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

  async deleteExistingMappingForMatchWithClient(client, incomingMapping) {
    const result = await client.query(`
      DELETE FROM matches_oddsportal_mapping
      WHERE match_id = $1
        AND season = $2
        AND oddsportal_hash <> $3
    `, [
      String(incomingMapping.match_id),
      String(incomingMapping.season),
      String(incomingMapping.oddsportal_hash)
    ]);

    return result.rowCount || 0;
  }

  buildForceOverwriteAssignments(hasOptionalFields = {}) {
    return [
      'match_id = $1',
      'full_url = $2',
      'league_name = $3',
      'home_team = $4',
      'away_team = $5',
      'status = $6',
      'updated_at = NOW()',
      hasOptionalFields.match_confidence ? 'match_confidence = $7' : null,
      hasOptionalFields.mapping_method ? 'mapping_method = $8' : null,
      hasOptionalFields.is_reversed ? 'is_reversed = $9' : null,
      hasOptionalFields.candidate_name ? 'candidate_name = NULL' : null,
      hasOptionalFields.is_evidence_only ? 'is_evidence_only = FALSE' : null
    ].filter(Boolean);
  }

  async forceOverwriteSeasonHashConflictWithClient(
    client,
    existingMappingRow,
    incomingMapping,
    hasOptionalFields = {},
    options = {}
  ) {
    if (!existingMappingRow || !incomingMapping) {
      return { resolved: false };
    }

    const matchRows = await this.fetchMatchesByIdsWithClient(client, [
      existingMappingRow.match_id,
      incomingMapping.match_id
    ]);
    const existingMatch = matchRows.get(String(existingMappingRow.match_id));
    const incomingMatch = matchRows.get(String(incomingMapping.match_id));
    if (!existingMatch || !incomingMatch) {
      return { resolved: false };
    }

    await this.deleteExistingMappingForMatchWithClient(client, incomingMapping);

    const assignments = this.buildForceOverwriteAssignments(hasOptionalFields);
    const params = [
      String(incomingMapping.match_id),
      incomingMapping.full_url,
      incomingMapping.league_name,
      incomingMapping.home_team,
      incomingMapping.away_team,
      incomingMapping.status || 'pending',
      hasOptionalFields.match_confidence
        ? (incomingMapping.match_confidence ?? (this.reconConfig.matching || {}).confidence_threshold)
        : null,
      hasOptionalFields.mapping_method
        ? String(incomingMapping.mapping_method || 'protocol_extract')
        : null,
      hasOptionalFields.is_reversed
        ? Boolean(incomingMapping.is_reversed)
        : null,
      String(incomingMapping.season),
      String(incomingMapping.oddsportal_hash),
      String(existingMappingRow.match_id)
    ];

    const result = await client.query(`
      UPDATE matches_oddsportal_mapping
      SET ${assignments.join(',\n          ')}
      WHERE season = $10
        AND oddsportal_hash = $11
        AND match_id = $12
      RETURNING match_id
    `, params);

    this.assertSuccessfulRebind(result.rowCount || 0, {
      season: incomingMapping.season,
      oddsportal_hash: incomingMapping.oddsportal_hash,
      previous_match_id: String(existingMappingRow.match_id),
      rebound_match_id: String(incomingMapping.match_id),
      resolution: 'force_overwrite_hash_conflict'
    });

    let linkedStatusUpdated = 0;

    if (String(existingMappingRow.match_id) !== String(incomingMapping.match_id)) {
      await this.setSingleMatchPipelineStatusWithClient(client, existingMatch.match_id, 'harvested', {
        expectedCurrentStatus: 'RECON_LINKED',
        requireNoMapping: true
      });
    }

    if (options.pipelineStatus) {
      linkedStatusUpdated += await this.setSingleMatchPipelineStatusWithClient(
        client,
        incomingMatch.match_id,
        options.pipelineStatus,
        {
          expectedCurrentStatus: incomingMatch.pipeline_status || 'harvested'
        }
      );
    }

    this.logger.warn('[HEAL] season/hash 冲突触发 SQL 强制覆盖，已用新 match_id 覆盖旧映射', {
      season: incomingMapping.season,
      oddsportal_hash: incomingMapping.oddsportal_hash,
      previous_match_id: String(existingMappingRow.match_id),
      rebound_match_id: String(incomingMapping.match_id),
      previous_home_team: existingMappingRow.home_team || null,
      previous_away_team: existingMappingRow.away_team || null,
      incoming_home_team: incomingMapping.home_team,
      incoming_away_team: incomingMapping.away_team,
      reason: options.reason || 'force_overwrite'
    });

    return {
      resolved: true,
      action: 'force_overwrite_hash_conflict',
      linkedStatusUpdated,
      matchId: String(incomingMapping.match_id),
      previousMatchId: String(existingMappingRow.match_id)
    };
  }

  assertSuccessfulRebind(rowCount, details) {
    if (Number(rowCount) === 1) {
      return;
    }

    throw new this.RepositoryError(
      'HASH_CONFLICT 重绑确认失败: 目标映射未命中唯一行',
      'HASH_CONFLICT_REBIND_FAILED',
      null,
      details
    );
  }

  async resolveHashConflictWithClient(client, conflict = {}) {
    const existingMapping = conflict.existingMapping || null;
    const incomingMapping = conflict.incomingMapping || null;
    const pipelineStatus = conflict.pipelineStatus || null;
    const preserveLinkedStatus = Boolean(conflict.preserveLinkedStatus);

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
    const existingLinked = existingMatch.pipeline_status === 'RECON_LINKED';

    if (decision.sameFixture) {
      const winner = decision.preferredWinner;
      const winnerMatch = winner === 'existing' ? existingMatch : incomingMatch;
      const loserMatch = winner === 'existing' ? incomingMatch : existingMatch;

      if (winner === 'incoming') {
        const rebindRowCount = await this.rebindMappingToMatchWithClient(client, existingMapping, incomingMapping);
        this.assertSuccessfulRebind(rebindRowCount, {
          season: incomingMapping.season,
          oddsportal_hash: incomingMapping.oddsportal_hash,
          previous_match_id: String(existingMatch.match_id),
          rebound_match_id: String(incomingMatch.match_id),
          resolution: 'rebind_duplicate'
        });
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

    if (existingLinked && preserveLinkedStatus && !decision.incomingHasStrongerEvidence) {
      this.logger.warn('[HEAL] 检测到 season/hash 冲突，但新证据不足以推翻既有 RECON_LINKED，已保留原绑定', {
        season: incomingMapping.season,
        oddsportal_hash: incomingMapping.oddsportal_hash,
        existing_match_id: String(existingMatch.match_id),
        incoming_match_id: String(incomingMatch.match_id),
        preserve_linked_status: preserveLinkedStatus,
        existing_match_date: existingMatch.match_date,
        incoming_match_date: incomingMatch.match_date,
        evidence: {
          date_distance_ms: Number.isFinite(decision.dateDistanceMs)
            ? decision.dateDistanceMs
            : null,
          existing_confidence: Number(decision.existingConfidence.toFixed(3)),
          incoming_confidence: Number(decision.incomingConfidence.toFixed(3)),
          confidence_delta: Number(decision.confidenceDelta.toFixed(3)),
          score_delta: Number(decision.scoreDelta.toFixed(3)),
          existing_score: Number(decision.existingScore.toFixed(3)),
          incoming_score: Number(decision.incomingScore.toFixed(3))
        }
      });

      return {
        resolved: true,
        action: 'preserve_existing_link',
        linkedStatusUpdated: 0
      };
    }

    if (decision.incomingScore >= this.arbiter.sameFixtureThreshold && decision.incomingScore > decision.existingScore) {
      if (existingLinked && !decision.incomingHasStrongerEvidence) {
        return { resolved: false };
      }

      const rebindRowCount = await this.rebindMappingToMatchWithClient(client, existingMapping, incomingMapping);
      this.assertSuccessfulRebind(rebindRowCount, {
        season: incomingMapping.season,
        oddsportal_hash: incomingMapping.oddsportal_hash,
        previous_match_id: String(existingMatch.match_id),
        rebound_match_id: String(incomingMatch.match_id),
        resolution: 'rebind_wrong_fixture'
      });
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
        },
        evidence: {
          date_distance_ms: Number.isFinite(decision.dateDistanceMs)
            ? decision.dateDistanceMs
            : null,
          existing_confidence: Number(decision.existingConfidence.toFixed(3)),
          incoming_confidence: Number(decision.incomingConfidence.toFixed(3)),
          confidence_delta: Number(decision.confidenceDelta.toFixed(3)),
          score_delta: Number(decision.scoreDelta.toFixed(3))
        }
      });

      return {
        resolved: true,
        action: 'rebind_wrong_fixture',
        linkedStatusUpdated: pipelineStatus ? 1 : 0
      };
    }

    const forcedResolution = await this.forceOverwriteSeasonHashConflictWithClient(
      client,
      existingMapping,
      incomingMapping,
      conflict.hasOptionalFields || {},
      {
        pipelineStatus,
        preserveLinkedStatus,
        reason: 'arbiter_force_overwrite'
      }
    );

    if (forcedResolution?.resolved) {
      return forcedResolution;
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
