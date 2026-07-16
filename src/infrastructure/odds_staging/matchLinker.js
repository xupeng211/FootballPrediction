'use strict';

// lifecycle: permanent；仅基于本地 candidate JSON 的确定性比赛关联决策。

const { stableCanonicalize } = require('./contracts');

function normalizeIdentityText(value) {
    return String(value ?? '')
        .normalize('NFKD')
        .replace(/[\u0300-\u036f]/g, '')
        .toLowerCase()
        .replace(/\s+/g, ' ')
        .trim();
}

function candidateId(candidate, index) {
    return String(candidate?.id ?? candidate?.match_id ?? `candidate-${index}`);
}

function candidateSourceMatchId(candidate) {
    return String(candidate?.source_match_id ?? candidate?.sourceMatchId ?? '').trim();
}

function sameKickoff(left, right) {
    if (!left || !right) {
        return false;
    }
    const leftMs = Date.parse(left);
    const rightMs = Date.parse(right);
    return Number.isFinite(leftMs) && Number.isFinite(rightMs) && leftMs === rightMs;
}

function sameRequiredField(observationValue, candidateValue) {
    const expected = normalizeIdentityText(observationValue);
    if (!expected) {
        return true;
    }
    return expected === normalizeIdentityText(candidateValue);
}

function matchesOrientation(observation, candidate, reversed) {
    const home = reversed
        ? (candidate?.away_team ?? candidate?.awayTeam)
        : (candidate?.home_team ?? candidate?.homeTeam);
    const away = reversed
        ? (candidate?.home_team ?? candidate?.homeTeam)
        : (candidate?.away_team ?? candidate?.awayTeam);
    return (
        normalizeIdentityText(observation.home_team) === normalizeIdentityText(home) &&
        normalizeIdentityText(observation.away_team) === normalizeIdentityText(away) &&
        sameKickoff(observation.kickoff_at, candidate?.kickoff_at ?? candidate?.kickoffAt) &&
        sameRequiredField(observation.competition, candidate?.competition) &&
        sameRequiredField(observation.season, candidate?.season)
    );
}

function buildDecision(status, method, candidates, evidence = {}) {
    const candidateIds = candidates.map((candidate, index) => candidateId(candidate, index)).sort();
    return {
        status,
        method,
        candidate_ids: candidateIds,
        matched_id: status === 'matched' ? candidateIds[0] : null,
        evidence: stableCanonicalize(evidence),
    };
}

function decideMatchLink(observation, candidates = []) {
    const localCandidates = Array.isArray(candidates) ? candidates.filter(Boolean) : [];
    const sourceMatchId = String(observation?.source_match_id || '').trim();
    if (sourceMatchId) {
        const directMatches = localCandidates.filter(candidate => candidateSourceMatchId(candidate) === sourceMatchId);
        if (directMatches.length === 1) {
            return buildDecision('matched', 'source_match_id', directMatches, { source_match_id: sourceMatchId });
        }
        if (directMatches.length > 1) {
            return buildDecision('ambiguous', 'source_match_id_multiple_candidates', directMatches, {
                source_match_id: sourceMatchId,
            });
        }
    }

    const exactMatches = localCandidates.filter(candidate => matchesOrientation(observation, candidate, false));
    const reversedMatches = localCandidates.filter(candidate => matchesOrientation(observation, candidate, true));
    if (exactMatches.length === 1 && reversedMatches.length === 0) {
        return buildDecision('matched', 'exact_home_away_kickoff', exactMatches, {
            source_match_id: sourceMatchId || null,
        });
    }
    if (exactMatches.length > 0 || reversedMatches.length > 0) {
        return buildDecision('ambiguous', 'candidate_identity_conflict', [...exactMatches, ...reversedMatches], {
            exact_candidate_count: exactMatches.length,
            reversed_candidate_count: reversedMatches.length,
        });
    }
    return buildDecision('unmatched', 'no_local_candidate', [], {
        source_match_id: sourceMatchId || null,
    });
}

module.exports = {
    decideMatchLink,
    normalizeIdentityText,
};
