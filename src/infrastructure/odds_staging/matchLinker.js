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

/**
 * Match ordered home/away + competition + season, IGNORING kickoff.
 * Used only for diagnostic classification of derived kickoff conflicts
 * when kickoff_time_interpretation is enabled.
 */
function matchesIdentityIgnoreKickoff(observation, candidate, reversed) {
    const home = candidateValue(candidate, reversed ? 'away_team' : 'home_team', reversed ? 'awayTeam' : 'homeTeam');
    const away = candidateValue(candidate, reversed ? 'home_team' : 'away_team', reversed ? 'homeTeam' : 'awayTeam');
    if (!text(observation.home_team) || !text(observation.away_team) || !text(home) || !text(away)) {
        return false;
    }
    return [
        [observation.home_team, home],
        [observation.away_team, away],
        [observation.competition, candidate.competition],
        [observation.season, candidate.season],
    ].every(
        ([left, right]) => text(left) && text(right) && normalizeIdentityText(left) === normalizeIdentityText(right)
    );
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

function decideDirectSourceId(sourceProvider, sourceMatchId, candidates, observation) {
    if (!sourceProvider || !sourceMatchId) return null;
    const matches = candidates.filter(
        candidate =>
            candidateSourceProvider(candidate) === sourceProvider && candidateSourceMatchId(candidate) === sourceMatchId
    );
    if (matches.length === 0) return null;
    if (matches.length > 1) {
        return buildDecision('ambiguous', 'source_match_id_multiple_candidates', matches, {
            source_provider: sourceProvider,
            source_match_id: sourceMatchId,
            candidates: matches.map(candidateSummary),
        });
    }
    const identity = inspectIdentityConsistency(observation, matches[0]);
    if (identity.conflicts.length > 0) {
        return buildDecision('ambiguous', 'source_match_id_identity_conflict', matches, {
            source_provider: sourceProvider,
            source_match_id: sourceMatchId,
            identity,
        });
    }
    if (!candidateStableId(matches[0])) {
        return stableIdMissingDecision('source_match_id', matches, {
            source_provider: sourceProvider,
            source_match_id: sourceMatchId,
            identity,
        });
    }
    return buildDecision('matched', 'source_match_id', matches, {
        source_provider: sourceProvider,
        source_match_id: sourceMatchId,
        identity,
    });
}

function decideExactIdentity(observation, candidates, sourceMatchId) {
    const exact = candidates.filter(candidate => matchesOrientation(observation, candidate, false));
    const reversed = candidates.filter(candidate => matchesOrientation(observation, candidate, true));
    if (exact.length !== 1 || reversed.length !== 0) return { decision: null, exact, reversed };
    if (!candidateStableId(exact[0])) {
        return {
            decision: stableIdMissingDecision('exact_home_away_kickoff', exact, { source_match_id: sourceMatchId }),
            exact,
            reversed,
        };
    }
    return {
        decision: buildDecision('matched', 'exact_home_away_kickoff', exact, { source_match_id: sourceMatchId }),
        exact,
        reversed,
    };
}

function derivedConflictMethod(observation, candidate) {
    const left = text(observation.kickoff_at);
    const right = text(candidateValue(candidate, 'kickoff_at', 'kickoffAt'));
    if (!left || !right || !isStrictAbsoluteTimestamp(left) || !isStrictAbsoluteTimestamp(right)) {
        return { method: 'derived_kickoff_conflict', delta: null };
    }
    const delta = Math.round((Date.parse(left) - Date.parse(right)) / 60000);
    const method =
        Math.abs(delta) === 15
            ? 'derived_kickoff_conflict_15m'
            : Math.abs(delta) === 30
              ? 'derived_kickoff_conflict_30m'
              : Math.abs(delta) > 0
                ? 'derived_kickoff_conflict_other'
                : 'derived_kickoff_conflict';
    return { method, delta };
}

function decideDerivedConflict(observation, candidates, reversed, sourceMatchId) {
    if (!observation.kickoff_time_interpretation_evidence || observation.source_provider !== 'football-data-csv') {
        return null;
    }
    const matches = candidates.filter(candidate => matchesIdentityIgnoreKickoff(observation, candidate, false));
    if (matches.length !== 1 || reversed.length !== 0) return null;
    if (!candidateStableId(matches[0])) {
        return stableIdMissingDecision('derived_kickoff_conflict', matches, { source_match_id: sourceMatchId });
    }
    const details = derivedConflictMethod(observation, matches[0]);
    return buildDecision('unmatched', details.method, matches, {
        source_match_id: sourceMatchId,
        candidate_kickoff: text(candidateValue(matches[0], 'kickoff_at', 'kickoffAt')),
        derived_kickoff: text(observation.kickoff_at),
        delta_minutes: details.delta,
        identity_consistent_except_kickoff: true,
    });
}

function decideMatchLink(observation, candidates = []) {
    const localCandidates = Array.isArray(candidates) ? candidates.filter(Boolean) : [];
    const sourceProvider = text(observation?.source_provider);
    const sourceMatchId = text(observation?.source_match_id);
    const direct = decideDirectSourceId(sourceProvider, sourceMatchId, localCandidates, observation);
    if (direct) return direct;
    const exact = decideExactIdentity(observation, localCandidates, sourceMatchId);
    if (exact.decision) return exact.decision;
    const derived = decideDerivedConflict(observation, localCandidates, exact.reversed, sourceMatchId);
    if (derived) return derived;
    if (exact.exact.length > 0 || exact.reversed.length > 0) {
        return buildDecision('ambiguous', 'candidate_identity_conflict', [...exact.exact, ...exact.reversed], {
            exact_candidate_count: exact.exact.length,
            reversed_candidate_count: exact.reversed.length,
            candidates: [...exact.exact, ...exact.reversed].map(candidateSummary),
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
