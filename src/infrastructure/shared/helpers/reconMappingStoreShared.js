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

function getPreserveLinkedStatusFlag(options = {}) {
  return options?.preserveLinkedStatus === true || options?.preserve_linked_status === true;
}

function decodeUrlSlugName(slug) {
  return String(slug || '')
    .replace(/-[A-Za-z0-9]{8}$/u, '')
    .split('-')
    .filter(Boolean)
    .join(' ')
    .trim();
}

function isH2HUrl(url) {
  return /\/football\/h2h\//iu.test(String(url || ''));
}

function safeUrlPathname(url) {
  try {
    return new URL(String(url)).pathname;
  } catch {
    return '';
  }
}

function buildTeamPairScores(arbiter, matchRow, leftTeam, rightTeam) {
  const directScore = (
    arbiter.teamSimilarity(matchRow.home_team, leftTeam)
    + arbiter.teamSimilarity(matchRow.away_team, rightTeam)
  );
  const reverseScore = (
    arbiter.teamSimilarity(matchRow.home_team, rightTeam)
    + arbiter.teamSimilarity(matchRow.away_team, leftTeam)
  );

  return {
    directScore,
    reverseScore
  };
}

function scoreUrlAgainstMatch(arbiter, url, matchRow) {
  if (!url || !matchRow) {
    return 0;
  }

  const pathname = safeUrlPathname(url);
  if (!pathname) {
    return 0;
  }

  const h2hMatch = pathname.match(/\/football\/h2h\/([^/]+)\/([^/]+)\/?$/iu);
  if (h2hMatch) {
    const scores = buildTeamPairScores(
      arbiter,
      matchRow,
      decodeUrlSlugName(h2hMatch[1]),
      decodeUrlSlugName(h2hMatch[2])
    );
    return Math.max(scores.directScore, scores.reverseScore);
  }

  const lastSegment = pathname.split('/').filter(Boolean).pop() || '';
  const standardMatch = lastSegment.match(/^(.*)-([A-Za-z0-9]{8})$/u);
  if (!standardMatch) {
    return 0;
  }

  const slugParts = String(standardMatch[1] || '').split('-').filter(Boolean);
  if (slugParts.length < 2) {
    return 0;
  }

  let bestScore = 0;
  for (let index = 1; index < slugParts.length; index++) {
    const scores = buildTeamPairScores(
      arbiter,
      matchRow,
      slugParts.slice(0, index).join(' '),
      slugParts.slice(index).join(' ')
    );
    bestScore = Math.max(bestScore, scores.directScore, scores.reverseScore);
  }

  return bestScore;
}

function scoreFixturePair(arbiter, matchRow, candidateMatch) {
  if (!matchRow || !candidateMatch) {
    return {
      directScore: 0,
      reverseScore: 0,
      bestScore: 0,
      isReversed: false
    };
  }

  const directScore = (
    arbiter.teamSimilarity(matchRow.home_team, candidateMatch.home_team)
    + arbiter.teamSimilarity(matchRow.away_team, candidateMatch.away_team)
  );
  const reverseScore = (
    arbiter.teamSimilarity(matchRow.home_team, candidateMatch.away_team)
    + arbiter.teamSimilarity(matchRow.away_team, candidateMatch.home_team)
  );

  return {
    directScore,
    reverseScore,
    bestScore: Math.max(directScore, reverseScore),
    isReversed: reverseScore > directScore
  };
}

function shouldForceOverwriteEvidenceOnlyConflict(existingMapping, incomingMapping) {
  return existingMapping?.is_evidence_only === true
    && incomingMapping?.is_evidence_only !== true;
}

function extractMatchTimestamp(matchRow) {
  const timestamp = new Date(matchRow?.match_date || '').getTime();
  return Number.isFinite(timestamp) ? timestamp : null;
}

function hasValidSequentialUrls(existingMapping, incomingMapping) {
  const existingUrl = String(existingMapping?.full_url || '').trim();
  const incomingUrl = String(incomingMapping?.full_url || '').trim();
  return Boolean(existingUrl && incomingUrl && !isH2HUrl(existingUrl) && !isH2HUrl(incomingUrl));
}

function hasSufficientIncomingConfidence(existingMapping, incomingMapping) {
  const incomingConfidence = Number(incomingMapping?.match_confidence || 0);
  const existingConfidence = Number(existingMapping?.match_confidence || 0);
  return incomingConfidence >= Math.max(existingConfidence, 0.75);
}

function shouldPreferIncomingSequentialHashOverwrite({
  arbiter,
  existingMatch,
  incomingMatch,
  existingMapping,
  incomingMapping,
  decision = {}
}) {
  const existingTimestamp = extractMatchTimestamp(existingMatch);
  const incomingTimestamp = extractMatchTimestamp(incomingMatch);
  if (existingTimestamp === null || incomingTimestamp === null || incomingTimestamp <= existingTimestamp) {
    return false;
  }

  if (!hasValidSequentialUrls(existingMapping, incomingMapping)) {
    return false;
  }

  if (!hasSufficientIncomingConfidence(existingMapping, incomingMapping)) {
    return false;
  }

  const pairScore = scoreFixturePair(arbiter, existingMatch, incomingMatch);
  return decision.sameFixture !== true
    && Number.isFinite(decision?.dateDistanceMs)
    && decision.dateDistanceMs > arbiter.sameFixtureWindowMs
    && pairScore.bestScore >= arbiter.sameFixtureThreshold;
}

function looksLikeProtocolOverwrite(incomingMapping) {
  const incomingMethod = String(incomingMapping?.mapping_method || '').trim().toLowerCase();
  const incomingUrl = String(incomingMapping?.full_url || '').trim();
  return incomingMethod === 'protocol_extract'
    || Boolean(incomingUrl && !isH2HUrl(incomingUrl));
}

function shouldPreferIncomingProtocolOverwrite({
  arbiter,
  existingMatch,
  incomingMatch,
  existingMapping,
  incomingMapping,
  decision = {}
}) {
  const existingUrl = String(existingMapping?.full_url || '').trim();
  const incomingUrl = String(incomingMapping?.full_url || '').trim();
  if (!existingUrl || !isH2HUrl(existingUrl) || !looksLikeProtocolOverwrite(incomingMapping)) {
    return false;
  }

  const existingUrlScore = scoreUrlAgainstMatch(arbiter, existingUrl, existingMatch);
  const incomingUrlScore = scoreUrlAgainstMatch(arbiter, incomingUrl, incomingMatch);
  const incomingScore = Number(decision?.incomingScore || 0);
  const existingScore = Number(decision?.existingScore || 0);
  const incomingEvidenceScore = Math.max(incomingScore, incomingUrlScore);

  return existingUrlScore < arbiter.sameFixtureThreshold
    && incomingScore >= arbiter.sameFixtureThreshold
    && incomingScore > existingScore
    && incomingEvidenceScore > existingUrlScore;
}

function assertFields(RepositoryError, payload, requiredFields, errorCode, messagePrefix) {
  const missingFields = requiredFields.filter((field) => !payload[field]);
  if (missingFields.length === 0) {
    return;
  }

  throw new RepositoryError(
    `${messagePrefix}: ${missingFields.join(', ')}`,
    errorCode
  );
}

function assertRequiredFields(RepositoryError, mappingData) {
  assertFields(
    RepositoryError,
    mappingData,
    ['match_id', 'oddsportal_hash', 'full_url', 'season', 'league_name', 'home_team', 'away_team'],
    'MISSING_REQUIRED_FIELDS',
    '缺少必填字段'
  );
}

function assertMismatchEvidenceFields(RepositoryError, evidenceData) {
  assertFields(
    RepositoryError,
    evidenceData,
    ['match_id', 'season', 'league_name', 'home_team', 'away_team'],
    'MISMATCH_EVIDENCE_REQUIRED_FIELDS',
    '失配证据缺少必填字段'
  );
}

function buildEvidenceOnlyHash(matchId) {
  const digest = crypto.createHash('sha1').update(String(matchId || '')).digest('hex').slice(0, 7);
  return `~${digest}`;
}

function buildForceOverwriteAssignments(hasOptionalFields = {}) {
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

function assertSuccessfulRebind(RepositoryError, rowCount, details) {
  if (Number(rowCount) === 1) {
    return;
  }

  throw new RepositoryError(
    'HASH_CONFLICT 重绑确认失败: 目标映射未命中唯一行',
    'HASH_CONFLICT_REBIND_FAILED',
    null,
    details
  );
}

function isSeasonHashUniqueViolation(error, mappingData = null) {
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

function classifyWriteError(error, { RepositoryError, mappingData, defaultCode, defaultMessage }) {
  if (error instanceof RepositoryError) {
    return error;
  }

  if (error.code === '23503') {
    return new RepositoryError(`外键约束失败: ${error.message}`, 'FOREIGN_KEY_VIOLATION', error);
  }

  if (isSeasonHashUniqueViolation(error, mappingData)) {
    return new RepositoryError(
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
    return new RepositoryError(`唯一约束冲突: ${error.message}`, 'UNIQUE_VIOLATION', error);
  }

  if (error.code === '23502') {
    return new RepositoryError(`非空约束失败: ${error.message}`, 'NOT_NULL_VIOLATION', error);
  }

  return new RepositoryError(`${defaultMessage}: ${error.message}`, defaultCode, error);
}

module.exports = {
  assertFunctionDependency,
  assertMismatchEvidenceFields,
  assertObjectDependency,
  assertRequiredFields,
  assertSuccessfulRebind,
  buildEvidenceOnlyHash,
  buildForceOverwriteAssignments,
  classifyWriteError,
  getPreserveLinkedStatusFlag,
  isSeasonHashUniqueViolation,
  scoreFixturePair,
  scoreUrlAgainstMatch,
  shouldForceOverwriteEvidenceOnlyConflict,
  shouldPreferIncomingProtocolOverwrite,
  shouldPreferIncomingSequentialHashOverwrite
};
