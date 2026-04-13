'use strict';

function assertFunctionDependency(name, value) {
  if (typeof value !== 'function') {
    throw new TypeError(`[MatchIdentityResolver] 缺少必需依赖: ${name}`);
  }
}

function toComparableTime(value) {
  const timestamp = new Date(value || 0).getTime();
  return Number.isFinite(timestamp) ? timestamp : Number.POSITIVE_INFINITY;
}

function normalizeRawString(value) {
  const normalized = String(value || '').trim();
  return normalized || null;
}

function requireIdentityValue(value, fieldName, RepositoryError, details = null) {
  const normalized = normalizeRawString(value);
  if (!normalized) {
    throw new RepositoryError(
      `Canonical identity 缺少必填字段: ${fieldName}`,
      'CANONICAL_IDENTITY_INVALID',
      null,
      details ? { field: fieldName, ...details } : { field: fieldName }
    );
  }
  return normalized;
}

function normalizeProvider(value, RepositoryError, { required = true, fieldName = 'data_source', details = null } = {}) {
  if (!required && (value === undefined || value === null || String(value).trim() === '')) {
    return null;
  }
  return requireIdentityValue(value, fieldName, RepositoryError, details);
}

function buildIdentityKey({ season, sourceProvider, rawMatchId }, RepositoryError, details = null) {
  return `${requireIdentityValue(season, 'season', RepositoryError, details)}::${normalizeProvider(
    sourceProvider,
    RepositoryError,
    { fieldName: 'data_source', details }
  )}::${requireIdentityValue(rawMatchId, 'external_id', RepositoryError, details)}`;
}

function comparePriority(left, right) {
  return right - left;
}

function compareWinnerCandidates(left, right, rawMatchId = null) {
  const comparisons = [
    comparePriority(left?.pipeline_status === 'RECON_LINKED' ? 1 : 0, right?.pipeline_status === 'RECON_LINKED' ? 1 : 0),
    comparePriority(String(left?.external_id || '') === String(rawMatchId || '') ? 1 : 0, String(right?.external_id || '') === String(rawMatchId || '') ? 1 : 0),
    comparePriority(left?.pipeline_status !== 'failed' ? 1 : 0, right?.pipeline_status !== 'failed' ? 1 : 0),
    toComparableTime(left?.created_at) - toComparableTime(right?.created_at),
    String(left?.match_id || '').localeCompare(String(right?.match_id || ''))
  ];

  return comparisons.find((value) => value !== 0) || 0;
}

function determineDecisionReason(rows, winner, rawMatchId = null) {
  const linkedCandidates = rows.filter((row) => row?.pipeline_status === 'RECON_LINKED');
  if (winner?.pipeline_status === 'RECON_LINKED' && linkedCandidates.length === 1) {
    return 'Winner has RECON_LINKED status';
  }

  const exactCandidates = rows.filter((row) => String(row?.external_id || '') === String(rawMatchId || ''));
  if (String(winner?.external_id || '') === String(rawMatchId || '') && exactCandidates.length === 1) {
    return 'Winner external_id matches raw_match_id';
  }

  const activeCandidates = rows.filter((row) => row?.pipeline_status !== 'failed');
  if (winner?.pipeline_status !== 'failed' && activeCandidates.length === 1) {
    return 'Winner remains active while duplicate is failed';
  }

  const earliestCreatedAt = [...rows]
    .sort((left, right) => toComparableTime(left?.created_at) - toComparableTime(right?.created_at))[0];
  if (earliestCreatedAt && String(earliestCreatedAt.match_id) === String(winner?.match_id)) {
    return 'Winner is earliest created_at canonical candidate';
  }

  return 'Winner selected by stable match_id tie-breaker';
}

function selectWinnerDecision(rows = [], options = {}) {
  if (!Array.isArray(rows) || rows.length === 0) {
    return { winner: null, decisionReason: 'No canonical candidates' };
  }

  const ordered = [...rows].sort((left, right) =>
    compareWinnerCandidates(left, right, options.rawMatchId)
  );
  const winner = ordered[0] || null;

  return {
    winner,
    decisionReason: determineDecisionReason(rows, winner, options.rawMatchId)
  };
}

function selectWinner(rows = [], options = {}) {
  return selectWinnerDecision(rows, options).winner;
}

class MatchIdentityResolver {
  constructor(options = {}) {
    assertFunctionDependency('getDbPool', options.getDbPool);
    assertFunctionDependency('executeWithRetry', options.executeWithRetry);
    assertFunctionDependency('RepositoryError', options.RepositoryError);

    this.getDbPool = options.getDbPool;
    this.executeWithRetry = options.executeWithRetry;
    this.logger = options.logger || { info() {}, warn() {}, error() {} };
    this.RepositoryError = options.RepositoryError;
  }

  assertFixtureIdentity(fixture, index = null) {
    const details = {
      fixture_index: index,
      match_id: fixture?.match_id ? String(fixture.match_id) : null
    };

    return {
      season: requireIdentityValue(fixture?.season, 'season', this.RepositoryError, details),
      sourceProvider: normalizeProvider(fixture?.data_source, this.RepositoryError, {
        fieldName: 'data_source',
        details
      }),
      rawMatchId: requireIdentityValue(fixture?.external_id, 'external_id', this.RepositoryError, details)
    };
  }

  async resolveCanonicalFixtures(fixtures = []) {
    if (!Array.isArray(fixtures) || fixtures.length === 0) {
      return fixtures;
    }

    const identities = fixtures.map((fixture, index) => this.assertFixtureIdentity(fixture, index));

    return this.executeWithRetry(async () => {
      const client = await this.getDbPool().connect();
      try {
        const seasons = [...new Set(identities.map((item) => item.season))];
        const providers = [...new Set(identities.map((item) => item.sourceProvider))];
        const rawMatchIds = [...new Set(identities.map((item) => item.rawMatchId))];

        const result = await client.query(`
          SELECT match_id, season, data_source, external_id, pipeline_status, created_at
          FROM matches
          WHERE season = ANY($1::text[])
            AND data_source = ANY($2::text[])
            AND external_id = ANY($3::text[])
        `, [seasons, providers, rawMatchIds]);

        const rowsByKey = new Map();
        for (const row of result.rows || []) {
          const key = buildIdentityKey({
            season: row.season,
            sourceProvider: row.data_source,
            rawMatchId: row.external_id
          }, this.RepositoryError, { match_id: row.match_id });

          if (!rowsByKey.has(key)) {
            rowsByKey.set(key, []);
          }
          rowsByKey.get(key).push(row);
        }

        return fixtures.map((fixture, index) => {
          const identity = identities[index];
          const key = buildIdentityKey(identity, this.RepositoryError, {
            fixture_index: index,
            match_id: fixture?.match_id ? String(fixture.match_id) : null
          });
          const existingRows = rowsByKey.get(key) || [];
          if (existingRows.length === 0) {
            return fixture;
          }

          const winner = selectWinner(existingRows, { rawMatchId: identity.rawMatchId });
          if (!winner) {
            return fixture;
          }

          return {
            ...fixture,
            match_id: String(winner.match_id),
            external_id: identity.rawMatchId,
            data_source: identity.sourceProvider
          };
        });
      } finally {
        client.release();
      }
    }, 'resolveCanonicalFixtures');
  }
}

module.exports = {
  MatchIdentityResolver,
  buildIdentityKey,
  normalizeProvider,
  normalizeRawString,
  requireIdentityValue,
  selectWinner,
  selectWinnerDecision,
  toComparableTime
};
