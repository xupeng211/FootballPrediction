'use strict';

// lifecycle: permanent；仅基于本地 candidate JSON 的确定性比赛关联决策。

const { isStrictAbsoluteTimestamp, stableCanonicalize } = require('./contracts');

function normalizeIdentityText(value) {
    return String(value ?? '')
        .normalize('NFKD')
        .replace(/[\u0300-\u036f]/g, '')
        .toLowerCase()
        .replace(/\s+/g, ' ')
        .trim();
}

function text(value) {
    const normalized = String(value ?? '').trim();
    return normalized || null;
}

function candidateValue(candidate, snakeCase, camelCase) {
    return candidate?.[snakeCase] ?? candidate?.[camelCase];
}

function candidateStableId(candidate) {
    return text(candidate?.id) || text(candidateValue(candidate, 'match_id', 'matchId'));
}

function candidateSourceProvider(candidate) {
    return text(candidateValue(candidate, 'source_provider', 'sourceProvider'));
}

function candidateSourceMatchId(candidate) {
    return text(candidateValue(candidate, 'source_match_id', 'sourceMatchId'));
}

function candidateSummary(candidate) {
    return {
        candidate_id: candidateStableId(candidate),
        source_provider: candidateSourceProvider(candidate),
        source_match_id: candidateSourceMatchId(candidate),
    };
}

function candidateIds(candidates) {
    return [...new Set(candidates.map(candidateStableId).filter(Boolean))].sort();
}

function sameKickoff(left, right) {
    return (
        isStrictAbsoluteTimestamp(left) && isStrictAbsoluteTimestamp(right) && Date.parse(left) === Date.parse(right)
    );
}

function compareIdentityField(field, observationValue, candidateValue) {
    const observationText = text(observationValue);
    const candidateText = text(candidateValue);
    if (!observationText || !candidateText) {
        return {
            conflict: null,
            missing:
                observationText || candidateText
                    ? { field, missing_on: observationText ? 'candidate' : 'observation' }
                    : null,
        };
    }
    return normalizeIdentityText(observationText) === normalizeIdentityText(candidateText)
        ? { conflict: null, missing: null }
        : {
              conflict: {
                  field,
                  observation_value: observationText,
                  candidate_value: candidateText,
              },
              missing: null,
          };
}

function compareKickoff(observationValue, candidateValue) {
    const observationText = text(observationValue);
    const candidateText = text(candidateValue);
    if (!observationText || !candidateText) {
        return {
            conflict: null,
            missing:
                observationText || candidateText
                    ? { field: 'kickoff_at', missing_on: observationText ? 'candidate' : 'observation' }
                    : null,
        };
    }
    if (!isStrictAbsoluteTimestamp(observationText) || !isStrictAbsoluteTimestamp(candidateText)) {
        return {
            conflict: {
                field: 'kickoff_at',
                observation_value: observationText,
                candidate_value: candidateText,
                reason: 'absolute_timestamp_required',
            },
            missing: null,
        };
    }
    return Date.parse(observationText) === Date.parse(candidateText)
        ? { conflict: null, missing: null }
        : {
              conflict: {
                  field: 'kickoff_at',
                  observation_value: observationText,
                  candidate_value: candidateText,
              },
              missing: null,
          };
}

function inspectIdentityConsistency(observation, candidate) {
    const comparisons = [
        compareIdentityField('home_team', observation.home_team, candidateValue(candidate, 'home_team', 'homeTeam')),
        compareIdentityField('away_team', observation.away_team, candidateValue(candidate, 'away_team', 'awayTeam')),
        compareKickoff(observation.kickoff_at, candidateValue(candidate, 'kickoff_at', 'kickoffAt')),
        compareIdentityField('competition', observation.competition, candidate?.competition),
        compareIdentityField('season', observation.season, candidate?.season),
    ];
    return {
        conflicts: comparisons.map(comparison => comparison.conflict).filter(Boolean),
        missing_evidence: comparisons.map(comparison => comparison.missing).filter(Boolean),
    };
}

function matchesOrientation(observation, candidate, reversed) {
    const home = candidateValue(candidate, reversed ? 'away_team' : 'home_team', reversed ? 'awayTeam' : 'homeTeam');
    const away = candidateValue(candidate, reversed ? 'home_team' : 'away_team', reversed ? 'homeTeam' : 'awayTeam');
    if (
        !text(observation.home_team) ||
        !text(observation.away_team) ||
        !text(home) ||
        !text(away) ||
        !sameKickoff(observation.kickoff_at, candidateValue(candidate, 'kickoff_at', 'kickoffAt'))
    ) {
        return false;
    }
    const homeMatches = normalizeIdentityText(observation.home_team) === normalizeIdentityText(home);
    const awayMatches = normalizeIdentityText(observation.away_team) === normalizeIdentityText(away);
    const consistency = inspectIdentityConsistency(
        { ...observation, home_team: observation.home_team, away_team: observation.away_team },
        {
            ...candidate,
            home_team: home,
            away_team: away,
        }
    );
    return homeMatches && awayMatches && consistency.conflicts.length === 0;
}

function buildDecision(status, method, candidates, evidence = {}) {
    const stableIds = candidateIds(candidates);
    return {
        status,
        method,
        candidate_ids: stableIds,
        matched_id: status === 'matched' ? stableIds[0] || null : null,
        evidence: stableCanonicalize(evidence),
    };
}

function stableIdMissingDecision(method, candidates, evidence = {}) {
    return buildDecision('ambiguous', 'candidate_stable_id_missing', candidates, {
        ...evidence,
        attempted_method: method,
        candidates_missing_stable_id: candidates
            .filter(candidate => !candidateStableId(candidate))
            .map(candidateSummary),
    });
}

function decideMatchLink(observation, candidates = []) {
    const localCandidates = Array.isArray(candidates) ? candidates.filter(Boolean) : [];
    const sourceProvider = text(observation?.source_provider);
    const sourceMatchId = text(observation?.source_match_id);
    if (sourceProvider && sourceMatchId) {
        const directMatches = localCandidates.filter(
            candidate =>
                candidateSourceProvider(candidate) === sourceProvider &&
                candidateSourceMatchId(candidate) === sourceMatchId
        );
        if (directMatches.length === 1) {
            const candidate = directMatches[0];
            const identity = inspectIdentityConsistency(observation, candidate);
            if (identity.conflicts.length > 0) {
                return buildDecision('ambiguous', 'source_match_id_identity_conflict', directMatches, {
                    source_provider: sourceProvider,
                    source_match_id: sourceMatchId,
                    identity,
                });
            }
            if (!candidateStableId(candidate)) {
                return stableIdMissingDecision('source_match_id', directMatches, {
                    source_provider: sourceProvider,
                    source_match_id: sourceMatchId,
                    identity,
                });
            }
            return buildDecision('matched', 'source_match_id', directMatches, {
                source_provider: sourceProvider,
                source_match_id: sourceMatchId,
                identity,
            });
        }
        if (directMatches.length > 1) {
            return buildDecision('ambiguous', 'source_match_id_multiple_candidates', directMatches, {
                source_provider: sourceProvider,
                source_match_id: sourceMatchId,
                candidates: directMatches.map(candidateSummary),
            });
        }
    }

    const exactMatches = localCandidates.filter(candidate => matchesOrientation(observation, candidate, false));
    const reversedMatches = localCandidates.filter(candidate => matchesOrientation(observation, candidate, true));
    if (exactMatches.length === 1 && reversedMatches.length === 0) {
        const candidate = exactMatches[0];
        if (!candidateStableId(candidate)) {
            return stableIdMissingDecision('exact_home_away_kickoff', exactMatches, {
                source_match_id: sourceMatchId,
            });
        }
        return buildDecision('matched', 'exact_home_away_kickoff', exactMatches, {
            source_match_id: sourceMatchId,
        });
    }
    if (exactMatches.length > 0 || reversedMatches.length > 0) {
        return buildDecision('ambiguous', 'candidate_identity_conflict', [...exactMatches, ...reversedMatches], {
            exact_candidate_count: exactMatches.length,
            reversed_candidate_count: reversedMatches.length,
            candidates: [...exactMatches, ...reversedMatches].map(candidateSummary),
        });
    }
    return buildDecision('unmatched', 'no_local_candidate', [], {
        source_provider: sourceProvider,
        source_match_id: sourceMatchId,
    });
}

module.exports = {
    decideMatchLink,
    normalizeIdentityText,
};
