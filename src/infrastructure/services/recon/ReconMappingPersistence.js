'use strict';

const {
  assertRequiredFields,
  assertSuccessfulRebind,
  buildForceOverwriteAssignments,
  classifyWriteError,
  getPreserveLinkedStatusFlag,
  isSeasonHashUniqueViolation
} = require('../../shared/helpers/reconMappingStoreShared');
const {
  buildForceOverwriteParams,
  buildMappingInsertPayload,
  buildMappingInsertQuery,
  buildOrderedMappings,
  getConfidenceThreshold
} = require('../../shared/helpers/reconMappingSqlBuilders');

class ReconMappingPersistence {
  constructor(options = {}) {
    this.getDbPool = options.getDbPool;
    this.logger = options.logger || { info() {}, warn() {}, error() {} };
    this.traceId = options.traceId || null;
    this.executeWithRetry = options.executeWithRetry;
    this.ensureSchema = options.ensureSchema;
    this.updateMatchPipelineStatusWithClient = options.updateMatchPipelineStatusWithClient;
    this.RepositoryError = options.RepositoryError;
    this.sqlTemplates = options.sqlTemplates || {};
    this.reconConfig = options.reconConfig || {};
    this.queries = options.queries;
    this.mismatchManager = options.mismatchManager;
  }

  async saveOddsPortalMapping(mappingData, options = {}) {
    assertRequiredFields(this.RepositoryError, mappingData);
    await this.ensureSchema();

    const hasOptionalFields = await this.queries.checkOptionalFields('matches_oddsportal_mapping', [
      'match_confidence',
      'mapping_method',
      'is_reversed',
      'candidate_name',
      'is_evidence_only'
    ]);

    return this.executeWithRetry(async () => {
      const client = await this.getDbPool().connect();
      const pipelineStatus = options.pipelineStatus || null;
      const preserveLinkedStatus = getPreserveLinkedStatusFlag(options);

      try {
        await client.query('BEGIN');
        const audit = await this.mismatchManager.auditSeasonHashConflictsWithClient(client, [mappingData], {
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
            updated: linkedStatusUpdated,
            applied: Number(audit.appliedMappings || 0)
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
          updated,
          applied: Number(audit.appliedMappings || 0) + Number(result?.applied || 0)
        };
      } catch (error) {
        await client.query('ROLLBACK');
        throw classifyWriteError(error, {
          RepositoryError: this.RepositoryError,
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
      return { success: true, inserted: 0, failed: 0, errors: [], updated: 0, applied: 0 };
    }

    const orderedMappings = buildOrderedMappings(mappings);
    orderedMappings.forEach((mapping) => assertRequiredFields(this.RepositoryError, mapping));

    await this.ensureSchema();
    const hasOptionalFields = await this.queries.checkOptionalFields('matches_oddsportal_mapping', [
      'match_confidence',
      'mapping_method',
      'is_reversed',
      'candidate_name',
      'is_evidence_only'
    ]);

    return this.executeWithRetry(async () => {
      const client = await this.getDbPool().connect();
      const pipelineStatus = options.pipelineStatus || null;
      const preserveLinkedStatus = getPreserveLinkedStatusFlag(options);
      const results = { inserted: 0, failed: 0, errors: [], updated: 0, applied: 0 };

      try {
        await client.query('BEGIN');
        const audit = await this.mismatchManager.auditSeasonHashConflictsWithClient(client, orderedMappings, {
          pipelineStatus,
          preserveLinkedStatus,
          hasOptionalFields
        });
        const remainingMappings = audit.remainingMappings || orderedMappings;
        results.updated += Number(audit.linkedStatusUpdated || 0);
        results.applied += Number(audit.appliedMappings || 0);

        for (const mapping of remainingMappings) {
          try {
            const saveResult = await this.saveOddsPortalMappingWithClient(
              client,
              mapping,
              hasOptionalFields,
              {
                pipelineStatus,
                preserveLinkedStatus
              }
            );
            results.inserted++;
            results.applied += Number(saveResult?.applied || 0);
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
        if (orderedMappings.some((mapping) => isSeasonHashUniqueViolation(error, mapping))) {
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

  async saveOddsPortalMappingWithClient(client, mappingData, hasOptionalFields, runtimeOptions = {}) {
    const payload = buildMappingInsertPayload(mappingData, hasOptionalFields, this.reconConfig);
    const query = buildMappingInsertQuery(this.sqlTemplates, payload, hasOptionalFields);

    try {
      const result = await client.query(query, payload.params);
      return {
        matchId: result.rows[0]?.match_id,
        wasInsert: result.rows.length > 0,
        applied: (result.rowCount || 0) > 0 ? 1 : 0
      };
    } catch (error) {
      return this.handleUniqueViolationWithOverwrite(
        client,
        error,
        mappingData,
        hasOptionalFields,
        runtimeOptions
      );
    }
  }

  async handleUniqueViolationWithOverwrite(client, error, mappingData, hasOptionalFields, runtimeOptions = {}) {
    if (!isSeasonHashUniqueViolation(error, mappingData)) {
      throw error;
    }

    const existingMapping = await this.queries.fetchMappingBySeasonHashWithClient(
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

    if (!forced?.resolved) {
      throw error;
    }

    return {
      matchId: forced.matchId || String(mappingData.match_id),
      wasInsert: false,
      forcedOverwrite: true,
      previousMatchId: forced.previousMatchId || null,
      applied: Number(forced.mappingApplied || 0)
    };
  }

  async rebindMappingToMatchWithClient(client, existingMappingRow, incomingMapping, hasOptionalFields = {}) {
    if (String(existingMappingRow?.match_id || '') !== String(incomingMapping?.match_id || '')) {
      await this.deleteExistingMappingForMatchWithClient(client, incomingMapping);
    }

    const assignments = [
      'match_id = $1',
      'full_url = $2',
      'league_name = $3',
      'home_team = $4',
      'away_team = $5',
      'status = $6',
      'updated_at = NOW()'
    ];
    const params = [
      String(incomingMapping.match_id),
      incomingMapping.full_url,
      incomingMapping.league_name,
      incomingMapping.home_team,
      incomingMapping.away_team,
      incomingMapping.status || 'pending'
    ];
    let nextParamIndex = params.length + 1;

    if (hasOptionalFields.match_confidence) {
      assignments.push(`match_confidence = $${nextParamIndex}`);
      params.push(incomingMapping.match_confidence ?? getConfidenceThreshold(this.reconConfig));
      nextParamIndex += 1;
    }

    if (hasOptionalFields.mapping_method) {
      assignments.push(`mapping_method = $${nextParamIndex}`);
      params.push(String(incomingMapping.mapping_method || 'protocol_extract'));
      nextParamIndex += 1;
    }

    if (hasOptionalFields.is_reversed) {
      assignments.push(`is_reversed = $${nextParamIndex}`);
      params.push(Boolean(incomingMapping.is_reversed));
      nextParamIndex += 1;
    }

    if (hasOptionalFields.candidate_name) {
      assignments.push('candidate_name = NULL');
    }

    if (hasOptionalFields.is_evidence_only) {
      assignments.push('is_evidence_only = FALSE');
    }

    const seasonParamIndex = nextParamIndex;
    params.push(incomingMapping.season);
    nextParamIndex += 1;
    const hashParamIndex = nextParamIndex;
    params.push(incomingMapping.oddsportal_hash);
    nextParamIndex += 1;
    const matchIdParamIndex = nextParamIndex;
    params.push(String(existingMappingRow.match_id));

    const result = await client.query(`
      UPDATE matches_oddsportal_mapping
      SET ${assignments.join(',\n          ')}
      WHERE season = $${seasonParamIndex}
        AND oddsportal_hash = $${hashParamIndex}
        AND match_id = $${matchIdParamIndex}
    `, params);

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

    const matchRows = await this.queries.fetchMatchesByIdsWithClient(client, [
      existingMappingRow.match_id,
      incomingMapping.match_id
    ]);
    const existingMatch = matchRows.get(String(existingMappingRow.match_id));
    const incomingMatch = matchRows.get(String(incomingMapping.match_id));
    if (!existingMatch || !incomingMatch) {
      return { resolved: false };
    }

    await this.deleteExistingMappingForMatchWithClient(client, incomingMapping);

    const result = await client.query(`
      UPDATE matches_oddsportal_mapping
      SET ${buildForceOverwriteAssignments(hasOptionalFields).join(',\n          ')}
      WHERE season = $10
        AND oddsportal_hash = $11
        AND match_id = $12
      RETURNING match_id
    `, buildForceOverwriteParams(existingMappingRow, incomingMapping, hasOptionalFields, this.reconConfig));

    assertSuccessfulRebind(this.RepositoryError, result.rowCount || 0, {
      season: incomingMapping.season,
      oddsportal_hash: incomingMapping.oddsportal_hash,
      previous_match_id: String(existingMappingRow.match_id),
      rebound_match_id: String(incomingMapping.match_id),
      resolution: 'force_overwrite_hash_conflict'
    });

    const linkedStatusUpdated = await this.updateOverwritePipelineStatuses(
      client,
      existingMappingRow,
      incomingMapping,
      existingMatch,
      incomingMatch,
      options
    );

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
      mappingApplied: 1,
      linkedStatusUpdated,
      matchId: String(incomingMapping.match_id),
      previousMatchId: String(existingMappingRow.match_id)
    };
  }

  async updateOverwritePipelineStatuses(client, existingMappingRow, incomingMapping, existingMatch, incomingMatch, options = {}) {
    let linkedStatusUpdated = 0;

    if (String(existingMappingRow.match_id) !== String(incomingMapping.match_id)) {
      await this.mismatchManager.setSingleMatchPipelineStatusWithClient(client, existingMatch.match_id, 'harvested', {
        expectedCurrentStatus: 'RECON_LINKED',
        requireNoMapping: true
      });
    }

    if (!options.pipelineStatus) {
      return linkedStatusUpdated;
    }

    linkedStatusUpdated += await this.mismatchManager.setSingleMatchPipelineStatusWithClient(
      client,
      incomingMatch.match_id,
      options.pipelineStatus,
      {
        expectedCurrentStatus: incomingMatch.pipeline_status || 'harvested'
      }
    );

    return linkedStatusUpdated;
  }
}

module.exports = { ReconMappingPersistence };
