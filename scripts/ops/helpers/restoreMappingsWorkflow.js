'use strict';

const {
  buildPerLeagueCounter,
  incrementPerLeague,
  serializePerLeagueCounter
} = require('./restoreMappingsShared');
const {
  dedupeCandidates,
  extractHashFromUrl,
  looksLikeRealHash,
  isCanonicalEventUrl,
  extractRawOddsPortalCandidates,
  buildEvidenceCandidate,
  buildBrazilCanonicalCandidate,
  candidateHitsDictionary,
  chooseCanonicalOverride
} = require('./restoreMappingsCandidates');

async function ensureDictionaryEntries(repository, evaluator, cache, row, leagueId) {
  const dictionaryKey = `${leagueId}::${row.season}`;
  if (!cache.has(dictionaryKey)) {
    const entries = Number.isInteger(leagueId) && leagueId > 0
      ? await repository.getLeagueDictionaryEntries(leagueId, { season: row.season })
      : [];
    cache.set(dictionaryKey, entries);
  }

  const dictionaryEntries = cache.get(dictionaryKey) || [];
  evaluator.setLeagueDictionaryEntries(leagueId, dictionaryEntries);
  return dictionaryEntries;
}

function buildRestoreCandidates(row, sourceUrl) {
  const evidenceCandidate = buildEvidenceCandidate(row);
  const rawCandidates = extractRawOddsPortalCandidates(row.raw_data, sourceUrl);
  return {
    rawCandidates,
    candidates: dedupeCandidates([evidenceCandidate, ...rawCandidates])
  };
}

function buildPromotionMappingData(row, appliedCandidate, best) {
  const finalUrl = String(appliedCandidate?.url || '').trim();
  const finalHash = extractHashFromUrl(finalUrl, appliedCandidate?.hash);
  if (!looksLikeRealHash(finalHash) || !finalUrl) {
    return null;
  }

  return {
    match_id: String(row.match_id),
    oddsportal_hash: finalHash,
    full_url: finalUrl,
    season: String(row.season),
    league_name: String(row.league_name || ''),
    home_team: String(appliedCandidate.homeTeam || row.evidence_home_team || row.home_team || ''),
    away_team: String(appliedCandidate.awayTeam || row.evidence_away_team || row.away_team || ''),
    status: 'pending',
    match_confidence: Number(best.confidence || 0),
    mapping_method: best.method,
    is_reversed: Boolean(best.isReversed)
  };
}

function recordRestoreFailure(summary, row, leagueId, error, verbose) {
  summary.failed++;
  summary.errors.push({
    match_id: String(row.match_id),
    league_id: leagueId,
    error: error.message
  });

  if (verbose) {
    console.error(`[restore] failed match_id=${row.match_id}: ${error.message}`);
  }
}

function shouldSkipRestoreRow(summary, row, dictionaryEntries, candidates) {
  if (!row.evidence_hash && !row.evidence_url) {
    summary.skipped_missing_evidence++;
    return true;
  }

  summary.evidence_rows++;
  if (!Array.isArray(dictionaryEntries) || dictionaryEntries.length === 0) {
    summary.skipped_missing_dictionary++;
    return true;
  }

  if (candidates.length === 0) {
    summary.skipped_missing_identity++;
    return true;
  }

  return false;
}

function resolveBestRestoreCandidate(summary, evaluator, row, candidates, threshold) {
  const best = evaluator.findBestCandidate({
    home_team: row.home_team,
    away_team: row.away_team,
    match_date: row.match_date
  }, candidates);
  if (!best) {
    summary.skipped_low_score++;
    return null;
  }

  if (!candidateHitsDictionary(evaluator, best.candidate, row)) {
    summary.skipped_not_dictionary++;
    return null;
  }

  summary.dictionary_hits++;
  if (Number(best.confidence || 0) <= Number(threshold)) {
    summary.skipped_low_score++;
    return null;
  }

  return best;
}

async function persistRestorePromotion(summary, promotedByLeague, repository, row, leagueId, best, mappingData, dryRun, verbose, canonicalOverride) {
  if (!dryRun) {
    await repository.saveOddsPortalMapping(mappingData, {
      pipelineStatus: 'RECON_LINKED'
    });
  }

  summary.promoted++;
  incrementPerLeague(promotedByLeague, leagueId, 1);
  if (canonicalOverride) {
    summary.promoted_with_canonical_override++;
  }
  if (verbose) {
    console.log(
      `[restore] promote match_id=${row.match_id} league_id=${leagueId} confidence=${Number(best.confidence).toFixed(3)} url=${mappingData.full_url}`
    );
  }
}

async function restoreEvidenceMappings({
  repository,
  rows,
  evaluator,
  getResultsUrl,
  threshold,
  dryRun = false,
  verbose = false
}) {
  const summary = {
    scanned: rows.length,
    evidence_rows: 0,
    raw_signal_candidates: 0,
    dictionary_hits: 0,
    promoted: 0,
    promoted_with_canonical_override: 0,
    skipped_missing_evidence: 0,
    skipped_missing_dictionary: 0,
    skipped_missing_identity: 0,
    skipped_low_score: 0,
    skipped_not_dictionary: 0,
    failed: 0,
    errors: [],
    promoted_by_league: serializePerLeagueCounter(buildPerLeagueCounter())
  };
  const promotedByLeague = buildPerLeagueCounter();
  const dictionaryCache = new Map();

  for (const row of rows) {
    const leagueId = Number(row.league_id || 0);
    const dictionaryEntries = await ensureDictionaryEntries(repository, evaluator, dictionaryCache, row, leagueId);
    const sourceUrl = getResultsUrl(leagueId, row.season);
    const { rawCandidates, candidates } = buildRestoreCandidates(row, sourceUrl);
    summary.raw_signal_candidates += rawCandidates.length;

    if (shouldSkipRestoreRow(summary, row, dictionaryEntries, candidates)) {
      continue;
    }

    const best = resolveBestRestoreCandidate(summary, evaluator, row, candidates, threshold);
    if (!best) {
      continue;
    }

    const canonicalOverride = chooseCanonicalOverride(row, best.candidate, rawCandidates, sourceUrl);
    const mappingData = buildPromotionMappingData(row, canonicalOverride || best.candidate, best);
    if (!mappingData) {
      summary.skipped_missing_identity++;
      continue;
    }

    try {
      await persistRestorePromotion(
        summary,
        promotedByLeague,
        repository,
        row,
        leagueId,
        best,
        mappingData,
        dryRun,
        verbose,
        canonicalOverride
      );
    } catch (error) {
      recordRestoreFailure(summary, row, leagueId, error, verbose);
    }
  }

  summary.promoted_by_league = serializePerLeagueCounter(promotedByLeague);
  return summary;
}

function buildCanonicalMappingData(row, canonicalCandidate, currentHash) {
  return {
    match_id: String(row.match_id),
    oddsportal_hash: currentHash,
    full_url: canonicalCandidate.url,
    season: String(row.season),
    league_name: String(row.league_name || ''),
    home_team: String(canonicalCandidate.homeTeam || row.remote_home_team || row.home_team || ''),
    away_team: String(canonicalCandidate.awayTeam || row.remote_away_team || row.away_team || ''),
    status: String(row.mapping_status || 'pending'),
    match_confidence: Number(row.match_confidence || 0),
    mapping_method: String(row.mapping_method || 'protocol_extract')
  };
}

function recordCanonicalFailure(summary, row, leagueId, error, verbose) {
  summary.failed++;
  summary.errors.push({
    match_id: String(row.match_id),
    league_id: leagueId,
    error: error.message
  });

  if (verbose) {
    console.error(`[canonical] failed match_id=${row.match_id}: ${error.message}`);
  }
}

function resolveCanonicalCandidate(row, sourceUrl) {
  const leagueId = Number(row.league_id || 0);
  const currentUrl = String(row.full_url || '').trim();
  const currentHash = extractHashFromUrl(currentUrl, row.oddsportal_hash);
  if (!looksLikeRealHash(currentHash)) {
    return { state: 'missing_hash', currentHash: '' };
  }

  const rawCandidates = extractRawOddsPortalCandidates(row.raw_data, sourceUrl);
  let canonicalCandidate = rawCandidates.find((candidate) => (
    extractHashFromUrl(candidate?.url, candidate?.hash) === currentHash
    && isCanonicalEventUrl(candidate?.url)
  )) || null;

  if (!canonicalCandidate && leagueId === 268) {
    canonicalCandidate = buildBrazilCanonicalCandidate(row, sourceUrl);
  }

  if (!canonicalCandidate) {
    return { state: 'missing_signal', currentHash };
  }

  const canonicalHash = extractHashFromUrl(canonicalCandidate.url, canonicalCandidate.hash);
  if (canonicalHash !== currentHash) {
    return { state: 'hash_mismatch', currentHash };
  }

  if (canonicalCandidate.url === currentUrl || isCanonicalEventUrl(currentUrl)) {
    return { state: 'already_canonical', currentHash };
  }

  return {
    state: 'ready',
    currentHash,
    canonicalCandidate
  };
}

async function resyncCanonicalUrls({
  repository,
  rows,
  getResultsUrl,
  dryRun = false,
  verbose = false
}) {
  const summary = {
    scanned: rows.length,
    updated: 0,
    already_canonical: 0,
    skipped_missing_hash: 0,
    skipped_missing_signal: 0,
    skipped_hash_mismatch: 0,
    failed: 0,
    updated_by_league: serializePerLeagueCounter(buildPerLeagueCounter()),
    errors: []
  };
  const updatedByLeague = buildPerLeagueCounter();

  for (const row of rows) {
    const leagueId = Number(row.league_id || 0);
    const resolution = resolveCanonicalCandidate(row, getResultsUrl(leagueId, row.season));

    if (resolution.state === 'missing_hash') {
      summary.skipped_missing_hash++;
      continue;
    }
    if (resolution.state === 'missing_signal') {
      summary.skipped_missing_signal++;
      continue;
    }
    if (resolution.state === 'hash_mismatch') {
      summary.skipped_hash_mismatch++;
      continue;
    }
    if (resolution.state === 'already_canonical') {
      summary.already_canonical++;
      continue;
    }

    try {
      if (!dryRun) {
        await repository.saveOddsPortalMapping(
          buildCanonicalMappingData(row, resolution.canonicalCandidate, resolution.currentHash),
          { preserveLinkedStatus: true }
        );
      }

      summary.updated++;
      incrementPerLeague(updatedByLeague, leagueId, 1);
      if (verbose) {
        console.log(`[canonical] update match_id=${row.match_id} league_id=${leagueId} url=${resolution.canonicalCandidate.url}`);
      }
    } catch (error) {
      recordCanonicalFailure(summary, row, leagueId, error, verbose);
    }
  }

  summary.updated_by_league = serializePerLeagueCounter(updatedByLeague);
  return summary;
}

module.exports = {
  restoreEvidenceMappings,
  resyncCanonicalUrls
};
