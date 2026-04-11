'use strict';

const {
  assertMismatchEvidenceFields,
  buildEvidenceOnlyHash,
  classifyWriteError,
  getPreserveLinkedStatusFlag
} = require('../../shared/helpers/reconMappingStoreShared');
const {
  buildMismatchInsertPayload,
  buildMismatchInsertQuery,
  buildStatusUpdateStatement
} = require('../../shared/helpers/reconMappingSqlBuilders');
const { ReconHashConflictResolver } = require('./ReconHashConflictResolver');

function normalizeMismatchRecords(records = []) {
  return [...records]
    .filter(Boolean)
    .map((record) => ({ ...record, match_id: String(record.match_id) }))
    .sort((left, right) => String(left.match_id).localeCompare(String(right.match_id)));
}

function buildSeasonHashIndex(mappings = []) {
  const uniqueMappings = new Map();

  for (const mapping of mappings) {
    const key = `${mapping.season}::${mapping.oddsportal_hash}`;
    if (!uniqueMappings.has(key)) {
      uniqueMappings.set(key, new Set());
    }
    uniqueMappings.get(key).add(String(mapping.match_id));
  }

  return uniqueMappings;
}

function buildMappingLookup(mappings = []) {
  return new Map(mappings.map((mapping) => [String(mapping.match_id), mapping]));
}

function buildConflictPayload(row, incomingMatchIds) {
  return {
    season: row.season,
    oddsportal_hash: row.oddsportal_hash,
    existing_match_id: String(row.match_id),
    incoming_match_ids: [...incomingMatchIds].sort(),
    existing_full_url: row.full_url || null
  };
}

class ReconMismatchManager {
  constructor(options = {}) {
    this.getDbPool = options.getDbPool;
    this.logger = options.logger || { info() {}, warn() {}, error() {} };
    this.executeWithRetry = options.executeWithRetry;
    this.ensureSchema = options.ensureSchema;
    this.RepositoryError = options.RepositoryError;
    this.queries = options.queries;
    this.conflictResolver = new ReconHashConflictResolver({
      arbiter: options.arbiter,
      logger: this.logger,
      RepositoryError: this.RepositoryError,
      queries: this.queries,
      statusUpdater: this
    });
  }

  attachPersistence(persistence) {
    this.conflictResolver.attachPersistence(persistence);
  }

  async batchSaveMismatchEvidence(mismatchRecords, _options = {}) {
    if (!Array.isArray(mismatchRecords) || mismatchRecords.length === 0) {
      return { success: true, saved: 0, skipped: 0 };
    }

    await this.ensureSchema();
    const hasOptionalFields = await this.queries.checkOptionalFields('matches_oddsportal_mapping', [
      'match_confidence',
      'mapping_method',
      'is_reversed',
      'candidate_name',
      'is_evidence_only'
    ]);
    const orderedRecords = normalizeMismatchRecords(mismatchRecords);
    orderedRecords.forEach((record) => assertMismatchEvidenceFields(this.RepositoryError, record));

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
        throw classifyWriteError(error, {
          RepositoryError: this.RepositoryError,
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
    const payload = buildMismatchInsertPayload(evidenceData, hasOptionalFields, buildEvidenceOnlyHash);
    const result = await client.query(
      buildMismatchInsertQuery(payload.columns, payload.values, hasOptionalFields),
      payload.params
    );

    return {
      matchId: result.rows[0]?.match_id || null,
      saved: (result.rowCount || 0) > 0
    };
  }

  async setSingleMatchPipelineStatusWithClient(client, matchId, status, options = {}) {
    const statement = buildStatusUpdateStatement(matchId, status, options);
    const result = await client.query(statement.query, statement.params);
    return result.rowCount || 0;
  }

  async resolveHashConflict(conflict, options = {}) {
    return this.executeWithRetry(async () => {
      const client = await this.getDbPool().connect();

      try {
        await client.query('BEGIN');
        const result = await this.conflictResolver.resolveHashConflictWithClient(client, {
          ...conflict,
          pipelineStatus: options.pipelineStatus || null,
          preserveLinkedStatus: getPreserveLinkedStatusFlag(options)
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

  async auditSeasonHashConflictsWithClient(client, mappings = [], options = {}) {
    if (!Array.isArray(mappings) || mappings.length === 0) {
      return { remainingMappings: [], linkedStatusUpdated: 0, appliedMappings: 0 };
    }

    const uniqueMappings = buildSeasonHashIndex(mappings);
    this.assertNoBatchConflicts(uniqueMappings);

    const existingRows = await this.queries.fetchMappingsBySeasonHashesWithClient(client, mappings);
    return this.processSeasonHashRows(client, existingRows, mappings, uniqueMappings, options);
  }

  assertNoBatchConflicts(uniqueMappings) {
    for (const [key, matchIds] of uniqueMappings.entries()) {
      if (matchIds.size <= 1) {
        continue;
      }

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

  async processSeasonHashRows(client, existingRows, mappings, uniqueMappings, options) {
    const mappingByMatchId = buildMappingLookup(mappings);
    const handledMatchIds = new Set();
    let linkedStatusUpdated = 0;
    let appliedMappings = 0;

    for (const row of existingRows) {
      const resolution = await this.resolveSeasonHashRow(
        client,
        row,
        uniqueMappings,
        mappingByMatchId,
        options
      );

      if (resolution.skip) {
        continue;
      }

      if (resolution.resolved) {
        handledMatchIds.add(String(resolution.incomingMatchId));
        linkedStatusUpdated += Number(resolution.linkedStatusUpdated || 0);
        appliedMappings += Number(resolution.mappingApplied || 0);
        continue;
      }

      const conflict = buildConflictPayload(row, resolution.incomingMatchIds);
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
      linkedStatusUpdated,
      appliedMappings
    };
  }

  async resolveSeasonHashRow(client, row, uniqueMappings, mappingByMatchId, options) {
    const key = `${row.season}::${row.oddsportal_hash}`;
    const incomingMatchIds = uniqueMappings.get(key);
    if (!incomingMatchIds || incomingMatchIds.has(String(row.match_id))) {
      return { skip: true };
    }

    if (incomingMatchIds.size !== 1) {
      return { incomingMatchIds, resolved: false, skip: false };
    }

    const incomingMatchId = [...incomingMatchIds][0];
    const resolution = await this.conflictResolver.resolveHashConflictWithClient(client, {
      existingMapping: row,
      incomingMapping: mappingByMatchId.get(incomingMatchId),
      pipelineStatus: options.pipelineStatus || null,
      preserveLinkedStatus: Boolean(options.preserveLinkedStatus),
      hasOptionalFields: options.hasOptionalFields || {}
    });

    return {
      incomingMatchId,
      incomingMatchIds,
      linkedStatusUpdated: Number(resolution?.linkedStatusUpdated || 0),
      mappingApplied: Number(resolution?.mappingApplied || 0),
      resolved: Boolean(resolution?.resolved),
      skip: false
    };
  }
}

module.exports = { ReconMismatchManager };
