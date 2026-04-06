'use strict';

const {
  normalizeProvider,
  normalizeRawString,
  requireIdentityValue,
  selectWinnerDecision,
  toComparableTime
} = require('./MatchIdentityResolver');

function assertFunctionDependency(name, value) {
  if (typeof value !== 'function') {
    throw new TypeError(`[MatchCanonicalJanitor] 缺少必需依赖: ${name}`);
  }
}

const PIPELINE_STATUS_PRIORITY = new Map([
  ['RECON_LINKED', 6],
  ['RECON_MISMATCH', 5],
  ['harvested', 4],
  ['processing', 3],
  ['pending', 2],
  ['skipped', 1],
  ['failed', 0]
]);

class MatchCanonicalJanitor {
  constructor(options = {}) {
    assertFunctionDependency('getDbPool', options.getDbPool);
    assertFunctionDependency('executeWithRetry', options.executeWithRetry);
    assertFunctionDependency('RepositoryError', options.RepositoryError);

    this.getDbPool = options.getDbPool;
    this.executeWithRetry = options.executeWithRetry;
    this.logger = options.logger || { info() {}, warn() {}, error() {} };
    this.RepositoryError = options.RepositoryError;
    this.identityInactiveStatuses = [...new Set((options.identityInactiveStatuses || []).map((status) =>
      requireIdentityValue(status, 'identity_inactive_statuses[]', this.RepositoryError)
    ))];
    if (this.identityInactiveStatuses.length === 0) {
      throw new TypeError('[MatchCanonicalJanitor] 缺少必需依赖: identityInactiveStatuses');
    }
  }

  selectInheritedPipelineStatus(rows = []) {
    return [...rows]
      .sort((left, right) => this.statusPriority(right?.pipeline_status) - this.statusPriority(left?.pipeline_status))[0]
      ?.pipeline_status || 'pending';
  }

  statusPriority(status) {
    return PIPELINE_STATUS_PRIORITY.get(String(status || '')) ?? -1;
  }

  normalizeSourceProvider(value, fieldName = 'data_source', details = null) {
    return normalizeProvider(value, this.RepositoryError, {
      fieldName,
      details,
      required: true
    });
  }

  normalizeOptionalSourceProvider(value, fieldName = 'data_source') {
    return normalizeProvider(value, this.RepositoryError, {
      fieldName,
      required: false
    });
  }

  appendIdentityActiveFilter(conditions, params, alias = 'm') {
    params.push(this.identityInactiveStatuses);
    conditions.push(`NOT (${alias}.pipeline_status = ANY($${params.length}::text[]))`);
  }

  buildIdentityIndexPredicate() {
    const quotedStatuses = this.identityInactiveStatuses
      .map((status) => `'${String(status).replace(/'/g, "''")}'`)
      .join(', ');
    return `external_id IS NOT NULL AND NOT (pipeline_status = ANY(ARRAY[${quotedStatuses}]::text[]))`;
  }

  buildSnapshot(rows = [], winner, loserRows = []) {
    const serializeRow = (row) => ({
      match_id: String(row?.match_id || ''),
      external_id: row?.external_id ?? null,
      league_name: row?.league_name ?? null,
      home_team: row?.home_team ?? null,
      away_team: row?.away_team ?? null,
      match_date: row?.match_date ?? null,
      pipeline_status: row?.pipeline_status ?? null
    });

    return {
      winner_before: serializeRow(winner),
      losers_before: loserRows.map(serializeRow),
      duplicate_count: rows.length
    };
  }

  async auditDuplicateGroups(options = {}) {
    return this.executeWithRetry(async () => {
      const client = await this.getDbPool().connect();
      try {
        return await this.auditDuplicateGroupsWithClient(client, options);
      } finally {
        client.release();
      }
    }, 'auditMatchCanonicalDuplicates');
  }

  async auditDuplicateGroupsWithClient(client, options = {}) {
    const params = [];
    const conditions = [
      `r.raw_data#>>'{general,matchId}' IS NOT NULL`
    ];
    this.appendIdentityActiveFilter(conditions, params);

    if (options.season) {
      params.push(String(options.season));
      conditions.push(`m.season = $${params.length}`);
    }

    if (options.sourceProvider !== undefined) {
      params.push(this.normalizeSourceProvider(options.sourceProvider, 'sourceProvider'));
      conditions.push(`m.data_source = $${params.length}`);
    }

    let limitClause = '';
    if (Number.isInteger(options.limit) && options.limit > 0) {
      params.push(options.limit);
      limitClause = ` LIMIT $${params.length}`;
    }

    const result = await client.query(`
      WITH grouped AS (
        SELECT
          m.season,
          m.data_source AS source_provider,
          r.raw_data#>>'{general,matchId}' AS raw_match_id,
          COUNT(DISTINCT m.match_id) AS duplicate_count,
          ARRAY_AGG(DISTINCT m.match_id ORDER BY m.match_id) AS match_ids,
          ARRAY_AGG(DISTINCT m.league_name ORDER BY m.league_name) AS league_names
        FROM matches m
        JOIN raw_match_data r
          ON r.match_id = m.match_id
        WHERE ${conditions.join(' AND ')}
        GROUP BY m.season, m.data_source, r.raw_data#>>'{general,matchId}'
        HAVING COUNT(DISTINCT m.match_id) > 1
      )
      SELECT *
      FROM grouped
      ORDER BY duplicate_count DESC, season, raw_match_id
      ${limitClause}
    `, params);

    return result.rows || [];
  }
  async consolidateDuplicateGroups(options = {}) {
    return this.executeWithRetry(async () => {
      const client = await this.getDbPool().connect();
      const summary = {
        season: options.season || null,
        source_provider: this.normalizeOptionalSourceProvider(options.sourceProvider, 'sourceProvider'),
        duplicate_groups: 0,
        raw_duplicate_groups: 0,
        external_identity_groups: 0,
        winners_updated: 0,
        losers_failed: 0,
        mappings_rebound: 0,
        mappings_retired: 0,
        groups: []
      };

      try {
        const rawGroups = await this.auditDuplicateGroupsWithClient(client, options);
        const rawSummary = await this.consolidateGroupsWithClient(client, rawGroups, (groupClient, group) =>
          this.consolidateDuplicateGroupWithClient(groupClient, group)
        );

        summary.raw_duplicate_groups = rawSummary.groupCount;
        summary.duplicate_groups += rawSummary.groupCount;
        summary.winners_updated += rawSummary.winnersUpdated;
        summary.losers_failed += rawSummary.losersFailed;
        summary.mappings_rebound += rawSummary.mappingsRebound;
        summary.mappings_retired += rawSummary.mappingsRetired;
        summary.groups.push(...rawSummary.groups);

        const externalGroups = await this.auditExternalIdentityDuplicatesWithClient(client, options);
        const externalSummary = await this.consolidateGroupsWithClient(client, externalGroups, (groupClient, group) =>
          this.consolidateExternalIdentityGroupWithClient(groupClient, group)
        );

        summary.external_identity_groups = externalSummary.groupCount;
        summary.duplicate_groups += externalSummary.groupCount;
        summary.winners_updated += externalSummary.winnersUpdated;
        summary.losers_failed += externalSummary.losersFailed;
        summary.mappings_rebound += externalSummary.mappingsRebound;
        summary.mappings_retired += externalSummary.mappingsRetired;
        summary.groups.push(...externalSummary.groups);

        await this.ensureSourceIdentityUniquenessIndexWithClient(client);
        return summary;
      } finally {
        client.release();
      }
    }, 'consolidateCanonicalDuplicates');
  }

  async ensureSourceIdentityUniquenessIndex() {
    return this.executeWithRetry(async () => {
      const client = await this.getDbPool().connect();
      try {
        const externalGroups = await this.auditExternalIdentityDuplicatesWithClient(client, {});
        await this.consolidateGroupsWithClient(client, externalGroups, (groupClient, group) =>
          this.consolidateExternalIdentityGroupWithClient(groupClient, group)
        );
        await this.ensureSourceIdentityUniquenessIndexWithClient(client);
      } finally {
        client.release();
      }
    }, 'ensureSourceIdentityUniquenessIndex');
  }

  async consolidateGroupsWithClient(client, groups = [], handler) {
    const summary = {
      groupCount: 0,
      winnersUpdated: 0,
      losersFailed: 0,
      mappingsRebound: 0,
      mappingsRetired: 0,
      groups: []
    };

    for (const group of groups) {
      let healed;
      await client.query('BEGIN');
      try {
        healed = await handler(client, group);
        await client.query('COMMIT');
        summary.groupCount += 1;
        summary.winnersUpdated += Number(healed.winners_updated || 0);
        summary.losersFailed += Number(healed.losers_failed || 0);
        summary.mappingsRebound += Number(healed.mappings_rebound || 0);
        summary.mappingsRetired += Number(healed.mappings_retired || 0);
        summary.groups.push(healed.group);
        if (healed.logEntry?.message) {
          const level = healed.logEntry.level || 'warn';
          const loggerMethod = typeof this.logger[level] === 'function' ? this.logger[level] : this.logger.warn;
          loggerMethod.call(this.logger, healed.logEntry.message, healed.logEntry.data);
        }
      } catch (error) {
        await client.query('ROLLBACK');
        throw error;
      }
    }

    return summary;
  }

  async ensureSourceIdentityUniquenessIndexWithClient(client) {
    try {
      await client.query(`
        CREATE UNIQUE INDEX IF NOT EXISTS idx_matches_season_source_external_active_unique
        ON matches(season, data_source, external_id)
        WHERE ${this.buildIdentityIndexPredicate()}
      `);
    } catch (error) {
      throw new this.RepositoryError(
        `Canonical identity 唯一索引固化失败: ${error.message}`,
        'CANONICAL_INDEX_BUILD_FAILED',
        error,
        { inactive_statuses: this.identityInactiveStatuses }
      );
    }
  }

  async consolidateDuplicateGroupWithClient(client, group) {
    const rows = await this.fetchDuplicateMembersWithClient(client, group.match_ids || []);
    const rawMatchId = rows[0]?.raw_match_id || group.raw_match_id || null;
    const { winner, decisionReason } = selectWinnerDecision(rows, { rawMatchId });
    if (!winner) {
      throw new this.RepositoryError(
        `无法为 raw_match_id=${group.raw_match_id} 选择 canonical winner`,
        'CANONICAL_WINNER_MISSING',
        null,
        group
      );
    }

    const loserRows = rows.filter((row) => String(row.match_id) !== String(winner.match_id));
    const inheritedStatus = this.selectInheritedPipelineStatus(rows);
    const canonicalMatchTime = normalizeRawString(winner.raw_match_time);
    const canonicalHomeTeam = normalizeRawString(winner.raw_home_team) || winner.home_team;
    const canonicalAwayTeam = normalizeRawString(winner.raw_away_team) || winner.away_team;
    const snapshot = this.buildSnapshot(rows, winner, loserRows);

    const mappings = await this.fetchMappingsForMatchIdsWithClient(client, rows.map((row) => row.match_id));
    const mappingResult = await this.rebindMappingsToWinnerWithClient(client, winner, loserRows, mappings);

    const loserIds = loserRows.map((row) => String(row.match_id));
    let losersFailed = 0;
    if (loserIds.length > 0) {
      const loserUpdate = await client.query(`
        UPDATE matches
        SET pipeline_status = 'failed',
            updated_at = NOW()
        WHERE match_id = ANY($1::text[])
      `, [loserIds]);
      losersFailed = loserUpdate.rowCount || 0;
    }

    const winnerUpdate = await client.query(`
      UPDATE matches
      SET external_id = $2,
          home_team = $3,
          away_team = $4,
          match_date = COALESCE($5::timestamptz, match_date),
          pipeline_status = $6,
          updated_at = NOW()
      WHERE match_id = $1
    `, [
      String(winner.match_id),
      String(rawMatchId || winner.external_id || ''),
      canonicalHomeTeam,
      canonicalAwayTeam,
      canonicalMatchTime,
      inheritedStatus
    ]);

    const auditGroup = {
      season: winner.season,
      source_provider: this.normalizeSourceProvider(winner.data_source, 'winner.data_source', { winner_match_id: winner.match_id }),
      raw_match_id: rawMatchId,
      winner_match_id: String(winner.match_id),
      loser_match_ids: loserIds,
      inherited_pipeline_status: inheritedStatus,
      canonical_match_time: canonicalMatchTime,
      mappings_rebound: mappingResult.reboundCount,
      mappings_retired: mappingResult.retiredCount,
      decision_reason: decisionReason,
      snapshot
    };

    return {
      winners_updated: winnerUpdate.rowCount || 0,
      losers_failed: losersFailed,
      mappings_rebound: mappingResult.reboundCount,
      mappings_retired: mappingResult.retiredCount,
      group: auditGroup,
      logEntry: {
        level: 'warn',
        message: '[HEAL] Canonical identity 已收敛重复实体',
        data: auditGroup
      }
    };
  }

  async fetchDuplicateMembersWithClient(client, matchIds = []) {
    const result = await client.query(`
      SELECT
        m.match_id,
        m.external_id,
        m.league_name,
        m.season,
        m.home_team,
        m.away_team,
        m.match_date,
        m.status,
        m.data_source,
        m.pipeline_status,
        m.created_at,
        m.updated_at,
        r.collected_at,
        r.external_id AS raw_table_external_id,
        r.raw_data#>>'{general,matchId}' AS raw_match_id,
        COALESCE(r.raw_data#>>'{general,matchTimeUTCDate}', r.raw_data#>>'{header,status,utcTime}') AS raw_match_time,
        COALESCE(r.raw_data#>>'{general,homeTeam,name}', r.raw_data#>>'{header,teams,0,name}') AS raw_home_team,
        COALESCE(r.raw_data#>>'{general,awayTeam,name}', r.raw_data#>>'{header,teams,1,name}') AS raw_away_team
      FROM matches m
      JOIN raw_match_data r
        ON r.match_id = m.match_id
      WHERE m.match_id = ANY($1::text[])
      ORDER BY m.created_at, m.match_id
    `, [[...new Set(matchIds.map((matchId) => String(matchId)))]]); 

    return result.rows || [];
  }

  async auditExternalIdentityDuplicatesWithClient(client, options = {}) {
    const params = [];
    const conditions = [
      `m.external_id IS NOT NULL`
    ];
    this.appendIdentityActiveFilter(conditions, params);

    if (options.season) {
      params.push(String(options.season));
      conditions.push(`m.season = $${params.length}`);
    }

    if (options.sourceProvider !== undefined) {
      params.push(this.normalizeSourceProvider(options.sourceProvider, 'sourceProvider'));
      conditions.push(`m.data_source = $${params.length}`);
    }

    let limitClause = '';
    if (Number.isInteger(options.limit) && options.limit > 0) {
      params.push(options.limit);
      limitClause = ` LIMIT $${params.length}`;
    }

    const result = await client.query(`
      SELECT
        m.season,
        m.data_source AS source_provider,
        m.external_id,
        COUNT(*) AS duplicate_count,
        ARRAY_AGG(m.match_id ORDER BY m.created_at, m.match_id) AS match_ids
      FROM matches m
      WHERE ${conditions.join(' AND ')}
      GROUP BY m.season, m.data_source, m.external_id
      HAVING COUNT(*) > 1
      ORDER BY duplicate_count DESC, m.external_id
      ${limitClause}
    `, params);

    return result.rows || [];
  }

  async fetchMatchRowsByIdsOnlyWithClient(client, matchIds = []) {
    if (!Array.isArray(matchIds) || matchIds.length === 0) {
      return [];
    }

    const result = await client.query(`
      SELECT
        match_id,
        external_id,
        league_name,
        season,
        home_team,
        away_team,
        match_date,
        status,
        data_source,
        pipeline_status,
        created_at,
        updated_at
      FROM matches
      WHERE match_id = ANY($1::text[])
      ORDER BY created_at, match_id
    `, [[...new Set(matchIds.map((matchId) => String(matchId)))]]); 

    return result.rows || [];
  }

  async fetchMappingsForMatchIdsWithClient(client, matchIds = []) {
    if (!Array.isArray(matchIds) || matchIds.length === 0) {
      return [];
    }

    const result = await client.query(`
      SELECT match_id, season, oddsportal_hash, full_url, home_team, away_team, status, created_at, updated_at
      FROM matches_oddsportal_mapping
      WHERE match_id = ANY($1::text[])
        AND COALESCE(is_evidence_only, FALSE) = FALSE
      ORDER BY updated_at DESC NULLS LAST, created_at DESC NULLS LAST, match_id
    `, [[...new Set(matchIds.map((matchId) => String(matchId)))]]); 

    return result.rows || [];
  }

  chooseMappingToKeep(winner, mappings = []) {
    if (!Array.isArray(mappings) || mappings.length === 0) {
      return null;
    }

    const winnerMapping = mappings.find((mapping) => String(mapping.match_id) === String(winner.match_id));
    if (winnerMapping) {
      return winnerMapping;
    }

    return [...mappings].sort((left, right) => {
      const updatedDiff = toComparableTime(right.updated_at || right.created_at) - toComparableTime(left.updated_at || left.created_at);
      if (updatedDiff !== 0) {
        return updatedDiff;
      }
      return String(left.match_id).localeCompare(String(right.match_id));
    })[0] || null;
  }

  async rebindMappingsToWinnerWithClient(client, winner, loserRows = [], mappings = []) {
    if (!Array.isArray(mappings) || mappings.length === 0) {
      return { reboundCount: 0, retiredCount: 0 };
    }

    const loserIds = loserRows.map((row) => String(row.match_id));
    const keepMapping = this.chooseMappingToKeep(winner, mappings);
    let reboundCount = 0;
    let retiredCount = 0;

    if (keepMapping && String(keepMapping.match_id) !== String(winner.match_id)) {
      const updateResult = await client.query(`
        UPDATE matches_oddsportal_mapping
        SET match_id = $1,
            updated_at = NOW()
        WHERE season = $2
          AND oddsportal_hash = $3
          AND match_id = $4
      `, [
        String(winner.match_id),
        keepMapping.season,
        keepMapping.oddsportal_hash,
        String(keepMapping.match_id)
      ]);
      reboundCount += updateResult.rowCount || 0;
    }

    if (loserIds.length > 0) {
      const deleteResult = await client.query(`
        DELETE FROM matches_oddsportal_mapping
        WHERE match_id = ANY($1::text[])
      `, [loserIds]);
      retiredCount += deleteResult.rowCount || 0;
    }

    return { reboundCount, retiredCount };
  }

  async consolidateExternalIdentityGroupWithClient(client, group) {
    const rows = await this.fetchMatchRowsByIdsOnlyWithClient(client, group.match_ids || []);
    const { winner, decisionReason } = selectWinnerDecision(rows, { rawMatchId: group.external_id });
    if (!winner) {
      throw new this.RepositoryError(
        `无法为 external_id=${group.external_id} 选择 canonical winner`,
        'CANONICAL_WINNER_MISSING',
        null,
        group
      );
    }

    const loserRows = rows.filter((row) => String(row.match_id) !== String(winner.match_id));
    const inheritedStatus = this.selectInheritedPipelineStatus(rows);
    const snapshot = this.buildSnapshot(rows, winner, loserRows);
    const mappings = await this.fetchMappingsForMatchIdsWithClient(client, rows.map((row) => row.match_id));
    const mappingResult = await this.rebindMappingsToWinnerWithClient(client, winner, loserRows, mappings);

    const winnerUpdate = await client.query(`
      UPDATE matches
      SET pipeline_status = $2,
          updated_at = NOW()
      WHERE match_id = $1
    `, [
      String(winner.match_id),
      inheritedStatus
    ]);

    const loserIds = loserRows.map((row) => String(row.match_id));
    let losersFailed = 0;
    if (loserIds.length > 0) {
      const loserUpdate = await client.query(`
        UPDATE matches
        SET pipeline_status = 'failed',
            updated_at = NOW()
        WHERE match_id = ANY($1::text[])
      `, [loserIds]);
      losersFailed = loserUpdate.rowCount || 0;
    }

    const auditGroup = {
      season: winner.season,
      source_provider: this.normalizeSourceProvider(winner.data_source, 'winner.data_source', { winner_match_id: winner.match_id }),
      external_id: group.external_id,
      winner_match_id: String(winner.match_id),
      loser_match_ids: loserIds,
      inherited_pipeline_status: inheritedStatus,
      mappings_rebound: mappingResult.reboundCount,
      mappings_retired: mappingResult.retiredCount,
      decision_reason: decisionReason,
      snapshot
    };

    return {
      winners_updated: winnerUpdate.rowCount || 0,
      losers_failed: losersFailed,
      mappings_rebound: mappingResult.reboundCount,
      mappings_retired: mappingResult.retiredCount,
      group: auditGroup,
      logEntry: {
        level: 'warn',
        message: '[HEAL] External identity 已收敛重复实体',
        data: auditGroup
      }
    };
  }
}

module.exports = { MatchCanonicalJanitor };
