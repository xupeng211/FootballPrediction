'use strict';

/* eslint-disable max-lines */

// lifecycle: permanent
// Deterministic, read-only FotMob league schedule candidate exporter.
// No writes to repository, database, or project directories.
// Real output must go to an absolute path outside the Git worktree.

const crypto = require('node:crypto');
const path = require('node:path');
const fs = require('node:fs');
const child_process = require('node:child_process');

const FOTMOB_BASE_URL = 'https://www.fotmob.com';
const DEFAULT_UA = 'FootballPrediction-FotMobCandidateExporter/1.0';
const DEFAULT_TIMEOUT_MS = 60_000;
const DEFAULT_DELAY_MS = 5_000;
const MAX_TOTAL_REQUESTS = 6;
const FIXTURES_URL_PATTERN = '/leagues/{leagueId}/fixtures/{slug}';
const EPL_FIXTURES_PER_SEASON = 380;
const CANONICAL_COMPETITION = 'Premier League';

// ----------------------------------------------------------------
// Provider status contract
// ----------------------------------------------------------------

const {
    ALLOWED_PROVIDER_STATUSES,
    FOTMOB_STATUS_TO_APPLICATION_STATUS,
    STATUS_MAPPING_VERSION,
} = require('./FotMobStatusContract');

/**
 * Derive a deterministic provider_status from a FotMob fixtures-page
 * `fixture.status` object.
 *
 * Only explicitly confirmed terminal states are accepted. Every other
 * combination is treated as unknown and fails closed so callers can
 * reject the fixture and block the season export.
 *
 * Allowed terminal states:
 *   cancelled === true  && finished !== true  →  cancelled
 *   finished  === true  && cancelled !== true →  finished
 *   reason.short ∈ {Postponed, Postp}          →  postponed
 *   (see scheduled rules below)                →  scheduled
 *
 * scheduled is ONLY returned when ALL of the following hold:
 *   - started  === false or absent (must NOT be true)
 *   - finished === false or absent (must NOT be true)
 *   - cancelled === false or absent (must NOT be true)
 *   - reason is absent, or reason.short is null/empty,
 *     or reason.short is one of the known pre-match reason codes
 *     that do NOT indicate postponement/cancellation/interruption
 *   - no unknown extra boolean flags on the status object
 *
 * Fail-closed (status=null) for:
 *   - started === true (match is in progress — not a terminal state)
 *   - any non-boolean value for started/finished/cancelled
 *   - contradictory flags (finished + cancelled)
 *   - unknown reason.short values (including 'Suspended', 'Live',
 *     'Interrupted', 'Cancelled' as reason short)
 *   - missing / non-object fixtureStatus
 *
 * @param {object}  fixtureStatus  fixture.status from FotMob pageProps
 * @returns {{ status: string|null, error: string|null }}
 */
/* eslint-disable-next-line complexity */
function deriveProviderStatus(fixtureStatus) {
    if (!fixtureStatus || typeof fixtureStatus !== 'object') {
        return { status: null, error: 'missing_status_object' };
    }

    // Every boolean flag MUST be a strict boolean if present.
    for (const flag of ['started', 'finished', 'cancelled']) {
        if (Object.prototype.hasOwnProperty.call(fixtureStatus, flag)) {
            const value = fixtureStatus[flag];
            if (typeof value !== 'boolean') {
                return { status: null, error: `non_boolean_flag:${flag}=${typeof value}` };
            }
        }
    }

    const started = fixtureStatus.started === true;
    const finished = fixtureStatus.finished === true;
    const cancelled = fixtureStatus.cancelled === true;
    const reasonShort =
        fixtureStatus.reason && typeof fixtureStatus.reason.short === 'string'
            ? fixtureStatus.reason.short
            : null;

    // Contradictory terminal states.
    if (finished && cancelled) {
        return { status: null, error: 'contradictory_status_flags:finished_and_cancelled' };
    }

    // Explicit terminal states.
    if (cancelled) {
        return { status: 'cancelled', error: null };
    }
    if (finished) {
        return { status: 'finished', error: null };
    }

    // Postponement — only when terminal flags are not set.
    if (reasonShort === 'Postponed' || reasonShort === 'Postp') {
        return { status: 'postponed', error: null };
    }

    // A match that has started but is not finished/cancelled/postponed
    // is in an unknown intermediate state (e.g. live, suspended,
    // interrupted, half-time). Fail closed — the exporter cannot
    // determine the final status.
    if (started) {
        const detail = reasonShort ? `started_with_reason:${reasonShort}` : 'started_no_reason';
        return { status: null, error: detail };
    }

    // Unknown / unexpected reason codes when the match has not started.
    // Known benign reasons that appear for future scheduled fixtures:
    //   - (empty / null / absent)  — no status annotation yet
    //   - 'FT' is only expected on finished matches but can appear
    //     briefly before boolean flags are updated; treat as
    //     scheduled only when finished===false explicitly.
    // Everything else (Suspended, Live, Interrupted, Cancelled as
    // reason short, etc.) is unknown territory → fail closed.
    if (reasonShort !== null && reasonShort !== '') {
        // 'FT' with finished===false is ambiguous but can occur in
        // edge cases; treat conservatively as scheduled since the
        // boolean flag overrides the reason code.
        if (reasonShort !== 'FT') {
            return { status: null, error: `unknown_reason:${reasonShort}` };
        }
    }

    // All checks passed — this is a future scheduled fixture.
    return { status: 'scheduled', error: null };
}

// ----------------------------------------------------------------
// Candidate identity
// ----------------------------------------------------------------

/**
 * Generate a canonical L1 match_id per the L1 Data Contract.
 *   leagueId + "_" + seasonWithoutSlash + "_" + externalId
 * Example: 47_20222023_3900932
 */
function generateCandidateId(leagueId, season, sourceMatchId) {
    const seasonTag = String(season).replace(/\//g, '');
    return `${leagueId}_${seasonTag}_${sourceMatchId}`;
}

/**
 * Verify a value is a strict ISO-8601 timestamp with Z or numeric offset.
 * Accepts optional fractional seconds of 1 to 9 digits (e.g. `.000Z`).
 */
function isStrictAbsoluteTimestamp(value) {
    return (
        typeof value === 'string' &&
        /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,9})?(Z|[+-]\d{2}:\d{2})$/.test(value)
    );
}

/**
 * Verify a value is a purely numeric FotMob match id.
 */
function isNumericExternalId(value) {
    return typeof value === 'string' && value.length > 0 && /^\d+$/.test(value);
}

// ----------------------------------------------------------------
// Request season canonicalisation
// ----------------------------------------------------------------

/**
 * Canonicalise a list of requested season strings before any network access.
 * Returns the deduplicated canonical `YYYY/YYYY` array, preserving order.
 * Throws INPUT_ERROR for invalid, non-consecutive, or duplicate inputs.
 */
function canonicalizeRequestedSeasons(values) {
    if (!Array.isArray(values) || values.length === 0) {
        throw Object.assign(new Error('At least one season is required'), { code: 'INPUT_ERROR' });
    }

    // Normalise every value
    const canonical = [];
    for (let index = 0; index < values.length; index += 1) {
        const raw = values[index];
        if (typeof raw !== 'string') {
            throw Object.assign(new Error(`Season at index ${index} must be a string`), { code: 'INPUT_ERROR' });
        }
        const c = normaliseSeason(raw);
        if (c === null) {
            throw Object.assign(
                new Error(
                    `Invalid season format: "${raw.trim()}" (expected YYYY/YYYY, YYYY-YYYY, YYYY/YY, YY/YY, or YY-YY)`
                ),
                { code: 'INPUT_ERROR' }
            );
        }
        canonical.push(c);
    }

    // Duplicate detection (post-normalisation, before consecutive check so
    // the user sees "Duplicate" rather than "Non-consecutive" for repeats.)
    const seen = new Set();
    const dupes = [];
    for (const c of canonical) {
        if (seen.has(c)) {
            dupes.push(c);
        } else {
            seen.add(c);
        }
    }
    if (dupes.length > 0) {
        throw Object.assign(new Error(`Duplicate canonical seasons not allowed: ${dupes.join(', ')}`), {
            code: 'INPUT_ERROR',
        });
    }

    // Consecutive check for multi-season requests (only after dedup)
    for (let i = 1; i < canonical.length; i += 1) {
        const prevStart = Number(canonical[i - 1].split('/')[0]);
        const currStart = Number(canonical[i].split('/')[0]);
        if (currStart !== prevStart + 1) {
            throw Object.assign(
                new Error(
                    `Non-consecutive seasons: ${canonical[i - 1]} then ${canonical[i]} (expected consecutive starting years)`
                ),
                { code: 'INPUT_ERROR' }
            );
        }
    }

    return canonical;
}

// ----------------------------------------------------------------
// HTTP helpers
// ----------------------------------------------------------------

/**
 * Fetch a URL and return { status, contentType, body, bodyBytes }.
 * Hard budget — callers must track request count externally.
 */
async function fetchPage(url, options = {}) {
    const userAgent = options.userAgent || DEFAULT_UA;
    const timeoutMs = options.timeoutMs || DEFAULT_TIMEOUT_MS;

    const ctrl = new AbortController();
    const timer = setTimeout(() => ctrl.abort(), timeoutMs);

    try {
        const res = await fetch(url, { signal: ctrl.signal, headers: { 'User-Agent': userAgent } });
        // Read as ArrayBuffer first so we can retain the raw bytes for
        // provenance capture, then decode to text for __NEXT_DATA__ parsing.
        const bodyArrayBuffer = await res.arrayBuffer();
        const bodyBytes = Buffer.from(bodyArrayBuffer);
        const body = new TextDecoder().decode(bodyArrayBuffer);
        return {
            status: res.status,
            contentType: String(res.headers.get('content-type') || ''),
            body,
            bodyBytes,
        };
    } finally {
        clearTimeout(timer);
    }
}

/**
 * Sleep for `ms` milliseconds.
 */
function delay(ms) {
    return new Promise(resolve => {
        setTimeout(resolve, ms);
    });
}

// ----------------------------------------------------------------
// Season identity
// ----------------------------------------------------------------

/**
 * Build a canonical YYYY/YYYY string from two years.
 * Returns null when the range is not a single consecutive season.
 */
function canonicalSeasonFromYears(start, end) {
    if (end !== start + 1) return null;
    return `${start}/${end}`;
}

/**
 * Normalise an observed season string into canonical YYYY/YYYY.
 * All accepted formats MUST represent a single consecutive season
 * (endYear === startYear + 1).
 *
 * Accepted: 2022/2023, 2022-2023, 22/23, 2022/23, 22-23
 * Rejected: 2022/2024, 2022-2024, 22/24, 22-24, 2022/2022, reverse, etc.
 * Returns null for unrecognised or non-consecutive formats.
 */
function normaliseSeason(value) {
    if (typeof value !== 'string') return null;

    const raw = value.trim();
    if (!raw) return null;

    // Full canonical: YYYY/YYYY
    let match = raw.match(/^(\d{4})\/(\d{4})$/);
    if (match) return canonicalSeasonFromYears(Number(match[1]), Number(match[2]));

    // Full dash: YYYY-YYYY
    match = raw.match(/^(\d{4})-(\d{4})$/);
    if (match) return canonicalSeasonFromYears(Number(match[1]), Number(match[2]));

    // Mixed abbreviated: YYYY/YY
    match = raw.match(/^(\d{4})\/(\d{2})$/);
    if (match) {
        const start = Number(match[1]);
        const end = 2000 + Number(match[2]);
        return canonicalSeasonFromYears(start, end);
    }

    // Abbreviated slash: YY/YY
    match = raw.match(/^(\d{2})\/(\d{2})$/);
    if (match) {
        const start = 2000 + Number(match[1]);
        const end = 2000 + Number(match[2]);
        return canonicalSeasonFromYears(start, end);
    }

    // Abbreviated dash: YY-YY
    match = raw.match(/^(\d{2})-(\d{2})$/);
    if (match) {
        const start = 2000 + Number(match[1]);
        const end = 2000 + Number(match[2]);
        return canonicalSeasonFromYears(start, end);
    }

    return null;
}

/**
 * Canonicalise the only competition supported by this EPL-specific exporter.
 * Rejects aliases and non-primitive values before they can reach network code.
 */
function canonicalizeCompetition(value) {
    if (typeof value !== 'string') {
        throw Object.assign(new Error('Competition must be a string'), { code: 'INPUT_ERROR' });
    }

    const normalized = value.trim().replace(/\s+/g, ' ');
    if (normalized.toLowerCase() !== CANONICAL_COMPETITION.toLowerCase()) {
        throw Object.assign(new Error('Competition must be Premier League'), { code: 'INPUT_ERROR' });
    }

    return CANONICAL_COMPETITION;
}

/**
 * Canonicalise a FotMob league id into its decimal string identity.
 * Accepts a positive safe-integer number or a decimal positive-integer
 * string (surrounding whitespace tolerated). Rejects every other value —
 * including path separators, query/fragment markers, encoded separators,
 * signed/decimal/exponential forms, zero, and all coercible non-primitive
 * values — before any network access and without invoking custom
 * toString/valueOf coercion.
 */
function canonicalizeLeagueId(value) {
    if (typeof value === 'number') {
        if (!Number.isSafeInteger(value) || value <= 0) {
            throw Object.assign(new Error('League id must be a positive safe integer'), { code: 'INPUT_ERROR' });
        }
        return String(value);
    }
    if (typeof value === 'string') {
        const normalized = value.trim();
        if (!/^[1-9]\d*$/.test(normalized)) {
            throw Object.assign(new Error('League id must be a decimal positive integer string'), {
                code: 'INPUT_ERROR',
            });
        }
        return normalized;
    }
    throw Object.assign(new Error('League id must be a number or string primitive'), { code: 'INPUT_ERROR' });
}

/**
 * Canonicalise a FotMob league slug into safe lowercase ASCII kebab-case.
 * Only primitive strings matching `^[a-z0-9]+(?:-[a-z0-9]+)*$` (after
 * trimming and lowercasing) are accepted, so no path separator, query,
 * fragment, encoded separator, whitespace, underscore, or Unicode path
 * variant can reach the request URL. Non-primitive values are rejected
 * without coercion.
 */
function canonicalizeLeagueSlug(value) {
    if (typeof value !== 'string') {
        throw Object.assign(new Error('League slug must be a string primitive'), { code: 'INPUT_ERROR' });
    }
    const normalized = value.trim().toLowerCase();
    if (!/^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(normalized)) {
        throw Object.assign(new Error('League slug must be safe ASCII kebab-case'), { code: 'INPUT_ERROR' });
    }
    return normalized;
}

// ----------------------------------------------------------------
// FotMob page extraction
// ----------------------------------------------------------------

/**
 * Parse `__NEXT_DATA__` from a FotMob HTML page.
 */
function extractNextData(html) {
    const match = html.match(/<script\s+id="__NEXT_DATA__"[^>]*>(.*?)<\/script>/s);
    if (!match) return null;
    try {
        return JSON.parse(match[1]);
    } catch {
        return null;
    }
}

/**
 * Extract league-level identity from __NEXT_DATA__.
 */
function extractPageIdentity(nd) {
    const pp = nd?.props?.pageProps;
    if (!pp) return null;

    const details = pp.details || {};
    const query = nd.query || {};

    const rawSeason = query.season ?? pp.selectedSeason ?? pp.currentSeason ?? null;

    return {
        league_name: details.name || details.longName || details.primaryName || null,
        league_id: details.id ? String(details.id) : null,
        season_raw: rawSeason,
        season_canonical: rawSeason ? normaliseSeason(rawSeason) : null,
        tabs: Array.isArray(pp.tabs) ? pp.tabs : [],
    };
}

/**
 * Maximum number of excluded or rejected fixture samples retained in the audit.
 */
const MAX_EXCLUDED_SAMPLES = 10;

/**
 * Create an empty fixture extraction audit.
 */
function createEmptyFixtureAudit() {
    return {
        raw_fixture_count: 0,
        excluded_fixture_count: 0,
        excluded_by_reason: {},
        excluded_fixture_samples: [],
        rejected_fixture_count: 0,
        rejected_by_reason: {},
        rejected_fixture_samples: [],
        accepted_fixture_count: 0,
        status_unknown_fixture_count: 0,
        status_unknown_by_reason: {},
        status_unknown_fixture_samples: [],
    };
}

/**
 * Record one excluded fixture in the audit.
 * Samples are bounded and store only the source match id, never the
 * full fixture payload.
 */
function recordExcludedFixture(audit, fixture) {
    audit.excluded_fixture_count += 1;
    audit.excluded_by_reason['Ab'] = (audit.excluded_by_reason['Ab'] || 0) + 1;
    if (audit.excluded_fixture_samples.length >= MAX_EXCLUDED_SAMPLES) {
        return;
    }
    const id = fixture?.id ? String(fixture.id).trim() : null;
    if (id && isNumericExternalId(id)) {
        audit.excluded_fixture_samples.push({ source_match_id: id, reason_code: 'Ab' });
    }
}

/**
 * Classify why a fixture fails the candidate contract.
 * Returns null for valid fixtures, or a deterministic reason code.
 * Priority order: bad source id, then missing home, missing away, missing kickoff.
 */
function classifyFixtureRejection(fixture) {
    const id = fixture?.id ? String(fixture.id).trim() : '';
    if (!isNumericExternalId(id)) return 'bad_source_match_id';
    if (!fixture?.home?.name) return 'missing_home_team';
    if (!fixture?.away?.name) return 'missing_away_team';
    if (!fixture?.status?.utcTime) return 'missing_kickoff';
    return null;
}

/**
 * Record one rejected (contract-invalid) fixture in the audit.
 * Samples are bounded and store at most source_match_id + reason_code.
 * When no valid source_match_id is available, only reason_code is recorded.
 */
function recordRejectedFixture(audit, fixture) {
    const reason = classifyFixtureRejection(fixture);
    if (!reason) return;

    audit.rejected_fixture_count += 1;
    audit.rejected_by_reason[reason] = (audit.rejected_by_reason[reason] || 0) + 1;
    if (audit.rejected_fixture_samples.length >= MAX_EXCLUDED_SAMPLES) {
        return;
    }
    const id = fixture?.id ? String(fixture.id).trim() : null;
    const sample = { reason_code: reason };
    if (id && isNumericExternalId(id)) {
        sample.source_match_id = id;
    }
    audit.rejected_fixture_samples.push(sample);
}

/**
 * Build an accepted fixture record, or null when the fixture does not
 * satisfy the candidate contract (numeric id, both teams, kickoff).
 * Includes the derived provider_status for v2 output.
 */
function extractAcceptedFixture(fixture) {
    if (classifyFixtureRejection(fixture) !== null) {
        return null;
    }
    const id = String(fixture.id).trim();
    const home = fixture.home.name;
    const away = fixture.away.name;
    const kickoff = fixture.status.utcTime;
    const statusResult = deriveProviderStatus(fixture.status);
    return { id, home, away, kickoff, provider_status: statusResult.status, status_error: statusResult.error };
}

/**
 * Extract all fixtures from pageProps.
 * Returns { fixtures, audit } where audit records exclusion counts.
 * Excludes abandoned matches (status.reason.short === 'Ab').
 * Postponed, rescheduled, and cancelled matches are NOT excluded.
 * Fixtures with unknown/unresolvable provider status are rejected and
 * counted separately so the season can fail closed.
 */
function extractFixtures(nd) {
    const pp = nd?.props?.pageProps;
    const raw = pp ? pp.fixtures?.allMatches : null;
    if (!Array.isArray(raw)) {
        return { fixtures: [], audit: createEmptyFixtureAudit() };
    }

    const audit = createEmptyFixtureAudit();
    audit.raw_fixture_count = raw.length;

    const fixtures = [];
    for (const f of raw) {
        // Only explicit 'Ab' is excluded
        if (f?.status?.reason?.short === 'Ab') {
            recordExcludedFixture(audit, f);
            continue;
        }
        const accepted = extractAcceptedFixture(f);
        if (accepted) {
            // Fail closed: every accepted fixture MUST have a valid provider_status.
            if (!accepted.provider_status || !ALLOWED_PROVIDER_STATUSES.has(accepted.provider_status)) {
                audit.status_unknown_fixture_count += 1;
                const reasonKey = accepted.status_error || 'unknown';
                audit.status_unknown_by_reason[reasonKey] =
                    (audit.status_unknown_by_reason[reasonKey] || 0) + 1;
                if (audit.status_unknown_fixture_samples.length < MAX_EXCLUDED_SAMPLES) {
                    const sample = { reason_code: reasonKey };
                    const id = f?.id ? String(f.id).trim() : null;
                    if (id && isNumericExternalId(id)) {
                        sample.source_match_id = id;
                    }
                    audit.status_unknown_fixture_samples.push(sample);
                }
                // Do NOT include this fixture in the accepted set.
                continue;
            }
            fixtures.push(accepted);
        } else {
            recordRejectedFixture(audit, f);
        }
    }

    audit.accepted_fixture_count = fixtures.length;
    return { fixtures, audit };
}

// ----------------------------------------------------------------
// Candidate building
// ----------------------------------------------------------------

/**
 * Build a single candidate record from extracted fixture data.
 */
function buildCandidate(fixture, leagueId, competition, season) {
    return {
        id: generateCandidateId(leagueId, season, fixture.id),
        source_provider: 'FotMob',
        source_match_id: fixture.id,
        competition,
        season,
        home_team: fixture.home,
        away_team: fixture.away,
        kickoff_at: fixture.kickoff,
        provider_status: fixture.provider_status,
        status_mapping_version: STATUS_MAPPING_VERSION,
    };
}

/**
 * Validate a set of candidates for one season.
 */
function validateSeasonCandidates(candidates, { competition, season, expectedFixtures }) {
    const errors = [];
    const ids = new Set();
    const sourceIds = new Set();
    const homeAwayKickoff = new Set();

    for (const c of candidates) {
        if (!c.id) errors.push(`missing_id`);
        if (!c.source_match_id || !isNumericExternalId(c.source_match_id)) errors.push(`bad_source_match_id:${c.id}`);
        if (!c.home_team) errors.push(`missing_home:${c.id}`);
        if (!c.away_team) errors.push(`missing_away:${c.id}`);
        if (c.home_team === c.away_team) errors.push(`same_teams:${c.id}`);
        if (!c.kickoff_at || !isStrictAbsoluteTimestamp(c.kickoff_at)) {
            errors.push(`bad_kickoff:${c.id}:${c.kickoff_at}`);
        }
        if (c.competition !== competition) errors.push(`wrong_competition:${c.id}:${c.competition}`);
        if (c.season !== season) errors.push(`wrong_season:${c.id}:${c.season}`);

        if (ids.has(c.id)) errors.push(`duplicate_id:${c.id}`);
        if (sourceIds.has(c.source_match_id)) errors.push(`duplicate_source_match_id:${c.source_match_id}`);

        ids.add(c.id);
        sourceIds.add(c.source_match_id);
        homeAwayKickoff.add(`${c.home_team}|${c.away_team}|${c.kickoff_at}`);
    }

    const fixtureCountOk = candidates.length === expectedFixtures;
    if (!fixtureCountOk) {
        errors.push(`fixture_count_mismatch:${candidates.length} vs expected ${expectedFixtures}`);
    }

    return {
        valid: errors.length === 0,
        errors,
        fixture_count: candidates.length,
        unique_ids: ids.size,
        unique_source_ids: sourceIds.size,
        unique_teams: new Set([...candidates.flatMap(c => [c.home_team, c.away_team])]).size,
    };
}

// ----------------------------------------------------------------
// Aggregate candidate validation
// ----------------------------------------------------------------

/**
 * Validate aggregate integrity across all candidates for all seasons.
 * Checks global ID uniqueness, source-match-id uniqueness, season
 * membership, per-season counts, and total count.
 */
function validateAggregateCandidates(candidates, canonicalSeasons, expectedPerSeason) {
    const errors = [];
    const idSet = new Set();
    const sourceIdSet = new Set();
    const perSeason = {};
    const expectedSeasonSet = new Set(canonicalSeasons);

    for (const c of candidates) {
        if (idSet.has(c.id)) {
            errors.push(`aggregate_duplicate_id:${c.id}`);
        }
        idSet.add(c.id);

        if (sourceIdSet.has(c.source_match_id)) {
            errors.push(`aggregate_duplicate_source_match_id:${c.source_match_id}`);
        }
        sourceIdSet.add(c.source_match_id);

        if (!expectedSeasonSet.has(c.season)) {
            errors.push(`unexpected_season:${c.season}:${c.id}`);
        }

        perSeason[c.season] = (perSeason[c.season] || 0) + 1;
    }

    for (const s of canonicalSeasons) {
        const count = perSeason[s] || 0;
        if (count !== expectedPerSeason) {
            errors.push(`season_count_mismatch:${s}:${count}`);
        }
    }

    const expectedTotal = canonicalSeasons.length * expectedPerSeason;
    if (candidates.length !== expectedTotal) {
        errors.push(`aggregate_total_mismatch:${candidates.length} vs expected ${expectedTotal}`);
    }

    return {
        valid: errors.length === 0,
        errors,
        unique_ids: idSet.size,
        unique_source_ids: sourceIdSet.size,
        per_season_counts: perSeason,
    };
}

// ----------------------------------------------------------------
// Business content hash
// ----------------------------------------------------------------

/**
 * Compute a stable SHA-256 over the business-relevant fields only.
 * Does NOT include extracted_at, local paths, or request metadata.
 */
function computeBusinessContentHash(candidates) {
    const sorted = [...candidates].sort((a, b) => {
        const keyA = `${a.season}|${a.kickoff_at}|${a.home_team}|${a.away_team}|${a.source_match_id}`;
        const keyB = `${b.season}|${b.kickoff_at}|${b.home_team}|${b.away_team}|${b.source_match_id}`;
        return keyA.localeCompare(keyB);
    });
    const content = sorted.map(c => ({
        id: c.id,
        source_provider: c.source_provider,
        source_match_id: c.source_match_id,
        competition: c.competition,
        season: c.season,
        home_team: c.home_team,
        away_team: c.away_team,
        kickoff_at: c.kickoff_at,
    }));
    return crypto.createHash('sha256').update(JSON.stringify(content)).digest('hex');
}

// ----------------------------------------------------------------
// V2 hashes
// ----------------------------------------------------------------

/**
 * Compute the v1 identity projection hash over the 8 identity fields only.
 * This MUST match the existing approved hash for real 3-season master data.
 * provider_status, status_mapping_version, and all metadata are excluded.
 *
 * Unchanged from the historical computeBusinessContentHash logic — kept as
 * a separately named entrypoint so v2 callers never accidentally call the
 * old name and conflate it with the full v2 business hash.
 */
function computeV1IdentityProjectionHash(candidates) {
    return computeBusinessContentHash(candidates);
}

/**
 * Compute a full v2 business hash over the complete candidate fields
 * including provider status and status mapping version.
 * Deterministic: sorted, projected to canonical fields, SHA-256.
 */
function computeV2BusinessHash(candidates) {
    const sorted = [...candidates].sort((a, b) => {
        const keyA = `${a.season}|${a.kickoff_at}|${a.home_team}|${a.away_team}|${a.source_match_id}`;
        const keyB = `${b.season}|${b.kickoff_at}|${b.home_team}|${b.away_team}|${b.source_match_id}`;
        return keyA.localeCompare(keyB);
    });
    const content = sorted.map(c => ({
        id: c.id,
        source_provider: c.source_provider,
        source_match_id: c.source_match_id,
        competition: c.competition,
        season: c.season,
        home_team: c.home_team,
        away_team: c.away_team,
        kickoff_at: c.kickoff_at,
        provider_status: c.provider_status,
        status_mapping_version: c.status_mapping_version,
    }));
    return crypto.createHash('sha256').update(JSON.stringify(content)).digest('hex');
}

// ----------------------------------------------------------------
// Main export pipeline
// ----------------------------------------------------------------

/**
 * Build the FotMob fixtures page URL for one season.
 * Only canonical league ids (decimal positive integer strings) and
 * canonical league slugs (safe ASCII kebab-case) may reach this builder;
 * `exportCandidates` canonicalises both before any call.
 */
function buildSeasonFixturesUrl(leagueId, leagueSlug, season) {
    const seasonParam = encodeURIComponent(season);
    const pathPart = FIXTURES_URL_PATTERN.replace('{leagueId}', leagueId).replace('{slug}', leagueSlug);
    return `${FOTMOB_BASE_URL}${pathPart}?season=${seasonParam}`;
}

/**
 * Classify the observed page identity against the requested league/season.
 * Returns { ok, reason } where reason is null when ok.
 */
function classifySeasonIdentity(identity, leagueId, requestedSeasonCanonical, requestedCompetition) {
    if (!identity) {
        return { ok: false, reason: 'identity_extraction_failed' };
    }
    let observedCompetition;
    try {
        observedCompetition = canonicalizeCompetition(identity.league_name);
    } catch {
        return { ok: false, reason: 'competition_identity_mismatch' };
    }
    if (observedCompetition !== requestedCompetition) {
        return { ok: false, reason: 'competition_identity_mismatch' };
    }
    if (String(identity.league_id) !== leagueId) {
        return { ok: false, reason: 'league_id_mismatch' };
    }
    if (identity.season_canonical === null) {
        return { ok: false, reason: 'season_identity_missing' };
    }
    if (identity.season_canonical !== requestedSeasonCanonical) {
        return { ok: false, reason: 'season_identity_mismatch' };
    }
    return { ok: true, reason: null };
}

/**
 * Safe identity summary for audit output (never full page data).
 */
function buildSafeIdentitySummary(identity) {
    if (!identity) {
        return null;
    }
    return {
        league_name: identity.league_name,
        league_id: identity.league_id,
        season_raw: identity.season_raw,
        season_canonical: identity.season_canonical,
    };
}

/**
 * Process a single season: budget check, one fixtures request, identity
 * verification, fixture extraction, candidate building, and per-season
 * validation.
 * Returns { seasonResult, candidates, requestsUsed, stop, succeeded }.
 * `stop` is set only for blocking statuses (403/429); `succeeded` marks a
 * fully processed season and drives inter-season delay placement.
 */
/* eslint-disable-next-line complexity */
async function processSeason(season, context) {
    const { leagueId, competition, leagueSlug, deps, userAgent, requestCount, maxRequests } = context;

    if (requestCount >= maxRequests) {
        return {
            seasonResult: { season, result: 'request_budget_exhausted', candidates: 0, identity: null },
            candidates: [],
            requestsUsed: 0,
            stop: false,
            succeeded: false,
        };
    }

    const url = buildSeasonFixturesUrl(leagueId, leagueSlug, season);
    const _fetchPage = deps.fetchPage || fetchPage;

    let resp;
    try {
        resp = await _fetchPage(url, { userAgent });
    } catch (err) {
        return {
            seasonResult: { season, result: `fetch_error:${err.message}`, candidates: 0, identity: null },
            candidates: [],
            requestsUsed: 1,
            stop: false,
            succeeded: false,
        };
    }

    // Capture data for provenance retention — always included when
    // we received bytes, regardless of parse/validation outcome.
    const _capture = resp.bodyBytes
        ? {
              url,
              bodyBytes: resp.bodyBytes,
              httpStatus: resp.status,
              contentType: resp.contentType,
          }
        : null;

    if (resp.status === 403 || resp.status === 429) {
        return {
            seasonResult: {
                season,
                result: `blocked_http_${resp.status}`,
                candidates: 0,
                identity: null,
                _capture,
            },
            candidates: [],
            requestsUsed: 1,
            stop: true,
            succeeded: false,
        };
    }

    if (resp.status !== 200) {
        return {
            seasonResult: {
                season,
                result: `http_${resp.status}`,
                candidates: 0,
                identity: null,
                _capture,
            },
            candidates: [],
            requestsUsed: 1,
            stop: false,
            succeeded: false,
        };
    }

    const nd = extractNextData(resp.body);
    if (!nd) {
        return {
            seasonResult: {
                season,
                result: 'no_next_data',
                candidates: 0,
                identity: null,
                _capture,
            },
            candidates: [],
            requestsUsed: 1,
            stop: false,
            succeeded: false,
        };
    }

    const identity = extractPageIdentity(nd);
    const verdict = classifySeasonIdentity(identity, leagueId, normaliseSeason(season), competition);
    if (!verdict.ok) {
        return {
            seasonResult: {
                season,
                result: verdict.reason,
                candidates: 0,
                identity: buildSafeIdentitySummary(identity),
                _capture,
            },
            candidates: [],
            requestsUsed: 1,
            stop: false,
            succeeded: false,
        };
    }

    const extraction = extractFixtures(nd);
    const seasonCandidates = extraction.fixtures.map(f => buildCandidate(f, leagueId, competition, season));
    const validation = validateSeasonCandidates(seasonCandidates, {
        competition,
        season,
        expectedFixtures: EPL_FIXTURES_PER_SEASON,
    });

    // Audit closure invariant: every fixture must be classified exactly once.
    // Accepted + Excluded + Rejected + StatusUnknown = Raw.
    const classifiedSum =
        extraction.audit.accepted_fixture_count +
        extraction.audit.excluded_fixture_count +
        extraction.audit.rejected_fixture_count +
        extraction.audit.status_unknown_fixture_count;
    const auditCloses = extraction.audit.raw_fixture_count === classifiedSum;

    if (!auditCloses || extraction.audit.rejected_fixture_count > 0 || extraction.audit.status_unknown_fixture_count > 0) {
        const errs = [...validation.errors];
        if (!auditCloses) {
            errs.push(
                `audit_not_closed:raw=${extraction.audit.raw_fixture_count},` +
                    `accepted=${extraction.audit.accepted_fixture_count},` +
                    `excluded=${extraction.audit.excluded_fixture_count},` +
                    `rejected=${extraction.audit.rejected_fixture_count},` +
                    `status_unknown=${extraction.audit.status_unknown_fixture_count}`
            );
        }
        if (extraction.audit.rejected_fixture_count > 0) {
            errs.push(`unexpected_rejected_fixtures:${extraction.audit.rejected_fixture_count}`);
        }
        if (extraction.audit.status_unknown_fixture_count > 0) {
            errs.push(`unknown_provider_status:${extraction.audit.status_unknown_fixture_count}`);
        }
        Object.assign(validation, { valid: false, errors: errs });
    }

    return {
        seasonResult: {
            season,
            result: validation.valid ? 'complete' : 'validation_failed',
            candidates: seasonCandidates.length,
            identity: {
                league_name: identity.league_name,
                league_id: identity.league_id,
                season: identity.season_canonical,
            },
            audit: extraction.audit,
            validation,
            _capture,
        },
        candidates: seasonCandidates,
        requestsUsed: 1,
        stop: false,
        succeeded: true,
    };
}

/**
 * Resolve the trusted 40-hex git revision from HEAD.
 * Fails closed when the worktree is dirty, the repository cannot be
 * identified, or the revision is not a plausible full-length SHA.
 *
 * @param {object} [options]
 * @param {string} [options.repositoryRoot] — absolute path to the Git repo
 * @param {object} [options.deps] — { execSync } for testability
 * @returns {{ revision: string, dirty: false }}
 */
function resolveGitState(options = {}) {
    const repositoryRoot = options.repositoryRoot
        ? path.resolve(options.repositoryRoot)
        : path.resolve(__dirname, '..', '..', '..');
    const execSync = (options.deps && options.deps.execSync) || child_process.execSync;
    const execOptions = { cwd: repositoryRoot, encoding: 'utf8', timeout: 10_000 };

    // Detect uncommitted change or untracked file — fail closed.
    let statusOutput;
    try {
        statusOutput = execSync('git status --porcelain', execOptions);
    } catch (err) {
        throw Object.assign(
            new Error(`git status failed: ${err.message}`),
            { code: 'SAFETY_ERROR' }
        );
    }
    if (statusOutput.trim().length > 0) {
        throw Object.assign(
            new Error('git worktree is dirty — commit or stash changes before exporting'),
            { code: 'SAFETY_ERROR' }
        );
    }

    // Resolve the full 40-hex revision.
    let revision;
    try {
        revision = execSync('git rev-parse HEAD', execOptions).trim();
    } catch (err) {
        throw Object.assign(
            new Error(`git rev-parse failed: ${err.message}`),
            { code: 'SAFETY_ERROR' }
        );
    }
    if (!/^[0-9a-f]{40}$/.test(revision)) {
        throw Object.assign(
            new Error(`git revision is not a valid 40-hex SHA: ${revision}`),
            { code: 'SAFETY_ERROR' }
        );
    }

    return { revision, dirty: false };
}

/**
 * Export FotMob league schedule candidates for one or more seasons.
 *
 * @param {Object} options
 * @param {number|string} options.leagueId        — FotMob league id (positive integer, e.g. 47)
 * @param {string}        options.competition     — Premier League formatting variant
 * @param {string[]}      options.seasons         — season strings (e.g. ["2022/2023"])
 * @param {string}        [options.leagueSlug]    — safe ASCII kebab-case URL slug (default: derived from competition)
 * @param {boolean}       options.networkAuthorization — explicit live-network authorization
 * @param {string}        [options.outputSchema]  — 'identity-v1' (default) or 'canonical-v2'
 * @param {Object}        [options.retainRawResponses] — { outputDir, collectorComponent, gitRevision }
 * @param {Object}        [options.deps]          — dependency injection
 * @returns {Promise<Object>} { candidates, snapshot, validation, meta, rawRetentions (if enabled) }
 */
/* eslint-disable-next-line complexity */
async function exportCandidates(options = {}) {
    const rawSeasons = Array.isArray(options.seasons) ? options.seasons : [];
    const deps = options.deps || {};
    const _delay = deps.delay || delay;
    const _clock = deps.clock || (() => new Date().toISOString());

    // Validate every user-controlled identity before any network access.
    const canonicalSeasons = canonicalizeRequestedSeasons(rawSeasons);
    const competition = canonicalizeCompetition(options.competition);
    const leagueId = canonicalizeLeagueId(options.leagueId);
    const leagueSlug =
        options.leagueSlug === undefined || options.leagueSlug === null || options.leagueSlug === ''
            ? canonicalizeLeagueSlug(competition.toLowerCase().replace(/\s+/g, '-'))
            : canonicalizeLeagueSlug(options.leagueSlug);
    if (options.networkAuthorization !== true) {
        throw Object.assign(new Error('Explicit network authorization is required'), { code: 'SAFETY_ERROR' });
    }
    const maxRequests = Math.min(canonicalSeasons.length * 2, MAX_TOTAL_REQUESTS);

    // Output schema
    const outputSchema = options.outputSchema || 'identity-v1';
    if (!['identity-v1', 'canonical-v2'].includes(outputSchema)) {
        throw Object.assign(new Error(`Unknown output schema: ${outputSchema}`), { code: 'INPUT_ERROR' });
    }

    // Raw retention gate: v2 canoncial mode requires retention
    const retainRaw = options.retainRawResponses || null;
    if (outputSchema === 'canonical-v2' && !retainRaw) {
        throw Object.assign(
            new Error('canonical-v2 output requires --retain-raw-responses with a repository-external output directory'),
            { code: 'SAFETY_ERROR' }
        );
    }

    const allCandidates = [];
    const seasonResults = [];
    const rawRetentions = [];
    let requestCount = 0;

    for (let i = 0; i < canonicalSeasons.length; i += 1) {
        const captureStartedAt = _clock();
        const outcome = await processSeason(canonicalSeasons[i], {
            leagueId,
            competition,
            leagueSlug,
            deps,
            userAgent: options.userAgent,
            requestCount,
            maxRequests,
        });
        const captureCompletedAt = _clock();

        requestCount += outcome.requestsUsed;
        allCandidates.push(...outcome.candidates);

        // Raw response retention — capture evidence BEFORE parsing,
        // so failed parses and identity mismatches still leave raw.
        // In v2 mode, every HTTP response with bytes must be retained.
        const cap = outcome.seasonResult._capture;
        if (cap && cap.bodyBytes && cap.bodyBytes.length > 0) {
            if (retainRaw) {
                try {
                    const retention = writeRawRetention(
                        retainRaw.outputDir,
                        cap.bodyBytes,
                        {
                            url: cap.url,
                            leagueId,
                            competition,
                            requestedSeason: canonicalSeasons[i],
                            canonicalSeason: canonicalSeasons[i],
                            httpStatus: cap.httpStatus,
                            contentType: cap.contentType,
                            captureStartedAt,
                            captureCompletedAt,
                            collectorComponent: retainRaw.collectorComponent || 'FotMobCandidateExporter',
                            collectorCodeRevision: retainRaw.collectorCodeRevision || 'unknown',
                            networkAuthorizationMode: 'explicit_network_authorization',
                        },
                        {
                            fileSystem: deps.fileSystem || fs,
                            repositoryRoot: deps.repositoryRoot,
                        }
                    );
                    rawRetentions.push(retention);
                } catch (retentionErr) {
                    // Raw retention failure blocks the entire export in v2 mode.
                    throw Object.assign(
                        new Error(`raw retention failed for season ${canonicalSeasons[i]}: ${retentionErr.message}`),
                        { code: 'SAFETY_ERROR' }
                    );
                }
            } else if (outputSchema === 'canonical-v2') {
                throw Object.assign(
                    new Error(`raw retention failed: no retention config for season ${canonicalSeasons[i]}`),
                    { code: 'SAFETY_ERROR' }
                );
            }
        } else if (outputSchema === 'canonical-v2' && outcome.succeeded) {
            // Succeeded seasons must always have capture data in v2 mode.
            throw Object.assign(
                new Error(`raw retention failed: no response bytes for season ${canonicalSeasons[i]}`),
                { code: 'SAFETY_ERROR' }
            );
        }

        // Strip internal capture data from season results before returning
        delete outcome.seasonResult._capture;
        seasonResults.push(outcome.seasonResult);

        if (outcome.stop) {
            break;
        }

        // Delay only after a fully processed season, and never after the last one
        if (outcome.succeeded && i < canonicalSeasons.length - 1) {
            await _delay(options.requestDelayMs || DEFAULT_DELAY_MS);
        }
    }

    const extractedAt = _clock();
    const aggregateV = validateAggregateCandidates(allCandidates, canonicalSeasons, EPL_FIXTURES_PER_SEASON);
    const allSeasonsComplete = seasonResults.every(r => r.result === 'complete') && aggregateV.valid;

    // Compute hashes
    const identityProjectionHash = computeV1IdentityProjectionHash(allCandidates);
    const v2BusinessHash =
        outputSchema === 'canonical-v2' ? computeV2BusinessHash(allCandidates) : null;
    const v1BusinessHash = computeBusinessContentHash(allCandidates);

    // Per-season counts
    const perSeasonCounts = {};
    for (const c of allCandidates) {
        perSeasonCounts[c.season] = (perSeasonCounts[c.season] || 0) + 1;
    }

    // Schema version for meta
    const schemaVersion =
        outputSchema === 'canonical-v2' ? 'canonical-inventory-artifact/v2' : 'candidate-match-identity/v1';

    return {
        candidates: allCandidates,
        snapshot: {
            source_provider: 'FotMob',
            league_id: leagueId,
            competition,
            seasons: canonicalSeasons,
            candidate_count: allCandidates.length,
            business_content_sha256: v1BusinessHash,
        },
        v2Snapshot:
            outputSchema === 'canonical-v2'
                ? {
                      identity_projection_hash: identityProjectionHash,
                      business_hash: v2BusinessHash,
                      per_season_counts: perSeasonCounts,
                  }
                : undefined,
        validation: {
            all_seasons_complete: allSeasonsComplete,
            season_results: seasonResults,
            total_candidates: allCandidates.length,
            total_expected: canonicalSeasons.length * EPL_FIXTURES_PER_SEASON,
            aggregate_validation: aggregateV,
        },
        meta: {
            extracted_at: extractedAt,
            total_requests: requestCount,
            schema_version: schemaVersion,
        },
        rawRetentions: rawRetentions.length > 0 ? rawRetentions : undefined,
    };
}

// ----------------------------------------------------------------
// Output safety
// ----------------------------------------------------------------

/**
 * Verify that `outputPath` is an absolute path outside the Git repository.
 * Uses realpath to prevent symlink-based repository containment bypass.
 * Throws on failure.
 */
function verifyOutputPathSafety(outputPath, options = {}) {
    const repositoryRoot = options.repositoryRoot
        ? path.resolve(options.repositoryRoot)
        : path.resolve(__dirname, '..', '..', '..');

    if (!path.isAbsolute(outputPath)) {
        throw Object.assign(new Error('Output path must be absolute'), { code: 'SAFETY_ERROR' });
    }

    const fileSystem = options.fileSystem || fs;

    // Output directory must exist and be a directory
    let outputStat;
    try {
        outputStat = fileSystem.lstatSync(outputPath);
    } catch {
        throw Object.assign(new Error('Output directory must already exist'), { code: 'SAFETY_ERROR' });
    }

    if (!outputStat.isDirectory()) {
        throw Object.assign(new Error('Output path must be a directory'), { code: 'SAFETY_ERROR' });
    }

    // Reject symbolic links pointing into the repository
    if (outputStat.isSymbolicLink()) {
        throw Object.assign(new Error('Output path must not be a symbolic link'), { code: 'SAFETY_ERROR' });
    }

    // Resolve both paths to their real locations
    const repoReal = (() => {
        try {
            return fileSystem.realpathSync(repositoryRoot);
        } catch {
            return repositoryRoot;
        }
    })();
    const outputReal = (() => {
        try {
            return fileSystem.realpathSync(outputPath);
        } catch {
            return outputPath;
        }
    })();

    // Must not be inside the repository (check by real path)
    const isInside = outputReal === repoReal || outputReal.startsWith(repoReal + path.sep);
    if (isInside) {
        throw Object.assign(new Error('Output path must be outside the Git repository'), {
            code: 'SAFETY_ERROR',
            repositoryRoot: repoReal,
            requestedPath: outputPath,
            realPath: outputReal,
        });
    }

    // Must not be inside any .git directory (check by real path)
    if (outputReal.includes(path.sep + '.git' + path.sep) || outputReal.endsWith(path.sep + '.git')) {
        throw Object.assign(new Error('Output path must not be inside a .git directory'), {
            code: 'SAFETY_ERROR',
        });
    }

    return outputReal;
}

// ----------------------------------------------------------------
// Serialisation helpers
// ----------------------------------------------------------------

/**
 * Build a complete candidate-match-identity/v1 output document.
 */
function buildOutputDocument(candidates, snapshot, meta) {
    return {
        schema_version: meta.schema_version,
        extracted_at: meta.extracted_at,
        snapshot: {
            source_provider: snapshot.source_provider,
            league_id: snapshot.league_id,
            competition: snapshot.competition,
            seasons: snapshot.seasons,
            candidate_count: snapshot.candidate_count,
            business_content_sha256: snapshot.business_content_sha256,
        },
        candidates: candidates.sort((a, b) => {
            const keyA = `${a.season}|${a.kickoff_at}|${a.home_team}|${a.away_team}|${a.source_match_id}`;
            const keyB = `${b.season}|${b.kickoff_at}|${b.home_team}|${b.away_team}|${b.source_match_id}`;
            return keyA.localeCompare(keyB);
        }),
    };
}

/**
 * Build a canonical-inventory-artifact/v2 output document.
 *
 * Contract requirements (from CanonicalInventoryContract.js):
 *   schema_version  = 'canonical-inventory-artifact/v2'
 *   artifact.kind   = 'master'  (this exporter always produces master)
 *   artifact.competition, seasons, candidate_count, per_season_counts
 *   artifact.business_hash, artifact.identity_projection_hash
 *   artifact.status_mapping_version
 *   artifact.synthetic_test_only
 *   candidates       — sorted deterministic array
 *
 * The artifact field 'source_provider' is accepted by the formal
 * unknown-field policy (the contract does not reject it).
 */
function buildV2OutputDocument(candidates, snapshot, meta, v2Snapshot) {
    const sorted = [...candidates].sort((a, b) => {
        const keyA = `${a.season}|${a.kickoff_at}|${a.home_team}|${a.away_team}|${a.source_match_id}`;
        const keyB = `${b.season}|${b.kickoff_at}|${b.home_team}|${b.away_team}|${b.source_match_id}`;
        return keyA.localeCompare(keyB);
    });
    return {
        schema_version: meta.schema_version,
        extracted_at: meta.extracted_at,
        artifact: {
            kind: 'master',
            source_provider: snapshot.source_provider,
            competition: snapshot.competition,
            seasons: snapshot.seasons,
            candidate_count: snapshot.candidate_count,
            per_season_counts: v2Snapshot.per_season_counts,
            identity_projection_hash: v2Snapshot.identity_projection_hash,
            business_hash: v2Snapshot.business_hash,
            status_mapping_version: STATUS_MAPPING_VERSION,
            synthetic_test_only: false,
        },
        candidates: sorted,
    };
}

/**
 * Build a v2 summary document.
 */
function buildV2SummaryDocument(candidates, snapshot, meta, v2Snapshot) {
    const bySeason = {};
    for (const c of candidates) {
        bySeason[c.season] = (bySeason[c.season] || 0) + 1;
    }
    return {
        schema_version: meta.schema_version,
        extracted_at: meta.extracted_at,
        summary: {
            total_candidates: candidates.length,
            per_season: bySeason,
            source_provider: snapshot.source_provider,
            competition: snapshot.competition,
            identity_projection_hash: v2Snapshot.identity_projection_hash,
            business_hash: v2Snapshot.business_hash,
            status_mapping_version: STATUS_MAPPING_VERSION,
        },
    };
}

/**
 * Validate that a v2 summary document is consistent with the corresponding
 * v2 artifact document that has already passed formal contract validation.
 *
 * Checks schema_version, candidate counts, per-season distribution,
 * hashes, and status_mapping_version. Throws SAFETY_ERROR on any mismatch.
 *
 * This is a pure function — no filesystem or network access.
 *
 * @param {object} candidateDoc  the v2 artifact document (already validated)
 * @param {object} summaryDoc    the v2 summary document to validate
 */
/* eslint-disable-next-line complexity */
function validateV2SummaryAgainstArtifact(candidateDoc, summaryDoc) {
    if (!candidateDoc || !summaryDoc) {
        throw Object.assign(new Error('summary validation requires both artifact and summary documents'), {
            code: 'SAFETY_ERROR',
        });
    }

    const artifact = candidateDoc.artifact;
    const summary = summaryDoc.summary;
    if (!artifact || !summary) {
        throw Object.assign(new Error('summary validation: missing artifact or summary block'), {
            code: 'SAFETY_ERROR',
        });
    }

    // Schema version must match.
    if (candidateDoc.schema_version !== summaryDoc.schema_version) {
        throw Object.assign(
            new Error('summary schema_version does not match artifact'),
            { code: 'SAFETY_ERROR' }
        );
    }

    // Candidate count must match.
    const artifactCount = candidateDoc.candidates ? candidateDoc.candidates.length : 0;
    if (artifactCount !== summary.total_candidates) {
        throw Object.assign(
            new Error(`summary total_candidates ${summary.total_candidates} does not match artifact ${artifactCount}`),
            { code: 'SAFETY_ERROR' }
        );
    }

    // Per-season counts must match.
    if (!summary.per_season || typeof summary.per_season !== 'object') {
        throw Object.assign(new Error('summary is missing per_season counts'), { code: 'SAFETY_ERROR' });
    }
    const artifactPerSeason = artifact.per_season_counts || {};
    const seasons = Object.keys(summary.per_season);
    if (seasons.length !== Object.keys(artifactPerSeason).length) {
        throw Object.assign(
            new Error('summary per_season season count does not match artifact'),
            { code: 'SAFETY_ERROR' }
        );
    }
    for (const season of seasons) {
        if (summary.per_season[season] !== artifactPerSeason[season]) {
            throw Object.assign(
                new Error(
                    `summary per_season["${season}"]=${summary.per_season[season]} ` +
                    `does not match artifact ${artifactPerSeason[season]}`
                ),
                { code: 'SAFETY_ERROR' }
            );
        }
    }

    // Source provider and competition must match.
    if (summary.source_provider !== artifact.source_provider) {
        throw Object.assign(
            new Error('summary source_provider does not match artifact'),
            { code: 'SAFETY_ERROR' }
        );
    }
    if (summary.competition !== artifact.competition) {
        throw Object.assign(
            new Error('summary competition does not match artifact'),
            { code: 'SAFETY_ERROR' }
        );
    }

    // Hashes must match.
    if (summary.identity_projection_hash !== artifact.identity_projection_hash) {
        throw Object.assign(
            new Error('summary identity_projection_hash does not match artifact'),
            { code: 'SAFETY_ERROR' }
        );
    }
    if (summary.business_hash !== artifact.business_hash) {
        throw Object.assign(
            new Error('summary business_hash does not match artifact'),
            { code: 'SAFETY_ERROR' }
        );
    }

    // Status mapping version must match.
    if (summary.status_mapping_version !== artifact.status_mapping_version) {
        throw Object.assign(
            new Error('summary status_mapping_version does not match artifact'),
            { code: 'SAFETY_ERROR' }
        );
    }
}

/**
 * Build a summary document (counts, hashes, season stats only — no full candidate data).
 */
function buildSummaryDocument(candidates, snapshot, meta) {
    const bySeason = {};
    for (const c of candidates) {
        bySeason[c.season] = (bySeason[c.season] || 0) + 1;
    }
    return {
        schema_version: meta.schema_version,
        extracted_at: meta.extracted_at,
        summary: {
            total_candidates: candidates.length,
            per_season: bySeason,
            source_provider: snapshot.source_provider,
            competition: snapshot.competition,
            business_content_sha256: snapshot.business_content_sha256,
        },
    };
}

/**
 * Best-effort unlink used during atomic-write cleanup.
 * Cleanup failures are intentionally swallowed so the original write
 * or rename error is never masked.
 */
function bestEffortUnlink(fileSystem, filePath) {
    try {
        fileSystem.unlinkSync(filePath);
    } catch (cleanupError) {
        // Cleanup is best-effort; preserve the original write failure.
        void cleanupError;
    }
}

/**
 * Write the full candidate JSON and summary JSON to the output directory.
 */
function writeOutputFiles(outputDir, candidates, snapshot, meta, options = {}) {
    const fileSystem = options.fileSystem || fs;
    const safeDir = verifyOutputPathSafety(outputDir, options);

    const candidatePath = path.join(safeDir, 'candidate-match-identity.v1.json');
    const summaryPath = path.join(safeDir, 'candidate-match-identity.v1.summary.json');

    const candidateDoc = buildOutputDocument(candidates, snapshot, meta);
    const summaryDoc = buildSummaryDocument(candidates, snapshot, meta);

    // Write atomically: temp file → rename
    const tempCandidate = candidatePath + '.tmp.' + Date.now();
    const tempSummary = summaryPath + '.tmp.' + Date.now();

    try {
        fileSystem.writeFileSync(tempCandidate, JSON.stringify(candidateDoc, null, 2) + '\n', {
            encoding: 'utf8',
            flag: 'wx',
        });
        fileSystem.writeFileSync(tempSummary, JSON.stringify(summaryDoc, null, 2) + '\n', {
            encoding: 'utf8',
            flag: 'wx',
        });
        fileSystem.renameSync(tempCandidate, candidatePath);
        fileSystem.renameSync(tempSummary, summaryPath);
    } catch (err) {
        bestEffortUnlink(fileSystem, tempCandidate);
        bestEffortUnlink(fileSystem, tempSummary);
        throw err;
    }

    return { candidatePath, summaryPath };
}

// ----------------------------------------------------------------
// Raw response retention
// ----------------------------------------------------------------

/**
 * Write raw response bytes to a repository-external directory atomically.
 * Computes SHA-256, records byte_size, and produces a capture manifest.
 *
 * @param {string} outputDir   absolute directory outside the repository
 * @param {Buffer} bodyBytes   raw HTTP response body bytes
 * @param {object} context     { url, season, httpStatus, contentType, captureStartedAt, captureCompletedAt, collectorComponent, gitRevision }
 * @param {object} options     { fileSystem, repositoryRoot }
 * @returns {{ manifest: object, rawFilePath: string, bodySha256: string, byteSize: number }}
 */
/* eslint-disable-next-line complexity */
function writeRawRetention(outputDir, bodyBytes, context, options = {}) {
    const fileSystem = options.fileSystem || fs;
    const safeDir = verifyOutputPathSafety(outputDir, options);

    const bodySha256 = crypto.createHash('sha256').update(bodyBytes).digest('hex');
    const byteSize = bodyBytes.length;

    // Sanitised season for filename
    const seasonSafe = context.canonicalSeason.replace(/[^a-zA-Z0-9_-]/g, '_');
    const rawFileName = `fotmob-fixtures-${context.leagueId}-${seasonSafe}-${bodySha256.slice(0, 12)}.html`;
    const rawFilePath = path.join(safeDir, rawFileName);

    // Paired manifest file written alongside the raw HTML as evidence unit.
    const manifestFileName = `fotmob-fixtures-${context.leagueId}-${seasonSafe}-${bodySha256.slice(0, 12)}.manifest.json`;
    const manifestFilePath = path.join(safeDir, manifestFileName);
    const manifest = buildCaptureManifest(context, bodySha256, byteSize, rawFileName);
    const manifestBytes = Buffer.from(JSON.stringify(manifest, null, 2) + '\n', 'utf8');
    const expectedManifestSha = crypto.createHash('sha256').update(manifestBytes).digest('hex');

    // 4.1 — Only two allowed states: both absent or both present as regular files.
    let existingRawStat;
    try { existingRawStat = fileSystem.lstatSync(rawFilePath); } catch { existingRawStat = null; }
    let existingManifestStat;
    try { existingManifestStat = fileSystem.lstatSync(manifestFilePath); } catch { existingManifestStat = null; }

    const rawExists = existingRawStat !== null;
    const manifestExists = existingManifestStat !== null;

    // Partial state — only one file exists.
    if (rawExists !== manifestExists) {
        throw Object.assign(
            new Error(
                `raw retention pair integrity violated: ` +
                `raw=${rawExists ? 'present' : 'absent'}, ` +
                `manifest=${manifestExists ? 'present' : 'absent'}`
            ),
            { code: 'SAFETY_ERROR' }
        );
    }

    // Symlinks are rejected for both files.
    if (rawExists && (!existingRawStat.isFile() || existingRawStat.isSymbolicLink())) {
        throw Object.assign(
            new Error(`raw retention refused: raw file is not a regular file: ${rawFileName}`),
            { code: 'SAFETY_ERROR' }
        );
    }
    if (manifestExists && (!existingManifestStat.isFile() || existingManifestStat.isSymbolicLink())) {
        throw Object.assign(
            new Error(`raw retention refused: manifest is not a regular file: ${manifestFileName}`),
            { code: 'SAFETY_ERROR' }
        );
    }

    // Both files exist — verify paired integrity.
    if (rawExists) {
        const existingRawBytes = fileSystem.readFileSync(rawFilePath);
        const existingRawSha = crypto.createHash('sha256').update(existingRawBytes).digest('hex');

        if (existingRawSha !== bodySha256) {
            throw Object.assign(
                new Error(`raw retention refused: target ${rawFileName} exists with different content`),
                { code: 'SAFETY_ERROR' }
            );
        }

        // Verify manifest file is valid JSON and content matches.
        let existingManifest;
        try {
            existingManifest = JSON.parse(fileSystem.readFileSync(manifestFilePath, 'utf8'));
        } catch (parseErr) {
            throw Object.assign(
                new Error(`raw retention refused: manifest is not valid JSON: ${manifestFileName}`),
                { code: 'SAFETY_ERROR' }
            );
        }

        // Verify manifest fields match the raw file and expected values.
        if (existingManifest.body_sha256 !== bodySha256) {
            throw Object.assign(
                new Error(`raw retention refused: manifest body_sha256 does not match raw: ${manifestFileName}`),
                { code: 'SAFETY_ERROR' }
            );
        }
        if (existingManifest.body_byte_size !== byteSize) {
            throw Object.assign(
                new Error(`raw retention refused: manifest body_byte_size does not match raw: ${manifestFileName}`),
                { code: 'SAFETY_ERROR' }
            );
        }
        if (existingManifest.raw_file_relative_path !== rawFileName) {
            throw Object.assign(
                new Error(`raw retention refused: manifest raw_file_relative_path mismatch: ${manifestFileName}`),
                { code: 'SAFETY_ERROR' }
            );
        }

        // Full manifest content must match (after stable serialization of the expected one).
        // Compare the serialized bytes so timestamp/revision differences are caught.
        const existingManifestBytes = fileSystem.readFileSync(manifestFilePath);
        const existingManifestSha = crypto.createHash('sha256').update(existingManifestBytes).digest('hex');
        if (existingManifestSha !== expectedManifestSha) {
            throw Object.assign(
                new Error(`raw retention refused: manifest content differs (capture time or revision changed): ${manifestFileName}`),
                { code: 'SAFETY_ERROR' }
            );
        }

        // Both files match — idempotent success.
        return {
            manifest,
            manifestFilePath,
            rawFilePath,
            bodySha256,
            byteSize,
        };
    }

    // Neither file exists — write both atomically.
    // 4.3: Write temp files → verify → rename raw → rename manifest → verify final → rollback on partial.
    const tempHtmlPath = rawFilePath + '.tmp.' + Date.now();
    const tempManifestPath = manifestFilePath + '.tmp.' + Date.now();

    try {
        fileSystem.writeFileSync(tempHtmlPath, bodyBytes, { flag: 'wx' });
        fileSystem.writeFileSync(tempManifestPath, manifestBytes, { flag: 'wx' });

        // Verify temp file contents before rename.
        const tempHtmlBytes = fileSystem.readFileSync(tempHtmlPath);
        if (crypto.createHash('sha256').update(tempHtmlBytes).digest('hex') !== bodySha256) {
            throw Object.assign(
                new Error('raw retention failed: temp HTML verification failed'),
                { code: 'SAFETY_ERROR' }
            );
        }
        const tempManifestBytes = fileSystem.readFileSync(tempManifestPath);
        if (crypto.createHash('sha256').update(tempManifestBytes).digest('hex') !== expectedManifestSha) {
            throw Object.assign(
                new Error('raw retention failed: temp manifest verification failed'),
                { code: 'SAFETY_ERROR' }
            );
        }

        // Rename raw first, then manifest.
        fileSystem.renameSync(tempHtmlPath, rawFilePath);

        try {
            fileSystem.renameSync(tempManifestPath, manifestFilePath);
        } catch (manifestRenameErr) {
            // 4.3: Manifest rename failed — rollback the just-created final raw.
            bestEffortUnlink(fileSystem, rawFilePath);
            bestEffortUnlink(fileSystem, tempManifestPath);
            throw Object.assign(
                new Error(`raw retention failed: manifest rename error: ${manifestRenameErr.message}`),
                { code: 'SAFETY_ERROR' }
            );
        }

        // Final verification: re-read both files and confirm pairing.
        let finalRawBytes;
        try { finalRawBytes = fileSystem.readFileSync(rawFilePath); } catch {
            throw Object.assign(
                new Error('raw retention failed: final raw read failed'),
                { code: 'SAFETY_ERROR' }
            );
        }
        const finalRawSha = crypto.createHash('sha256').update(finalRawBytes).digest('hex');
        if (finalRawSha !== bodySha256) {
            bestEffortUnlink(fileSystem, rawFilePath);
            bestEffortUnlink(fileSystem, manifestFilePath);
            throw Object.assign(
                new Error('raw retention failed: final raw verification failed'),
                { code: 'SAFETY_ERROR' }
            );
        }

        let finalManifestParsed;
        try {
            finalManifestParsed = JSON.parse(fileSystem.readFileSync(manifestFilePath, 'utf8'));
        } catch {
            bestEffortUnlink(fileSystem, rawFilePath);
            bestEffortUnlink(fileSystem, manifestFilePath);
            throw Object.assign(
                new Error('raw retention failed: final manifest parse failed'),
                { code: 'SAFETY_ERROR' }
            );
        }

        if (finalManifestParsed.body_sha256 !== bodySha256 ||
            finalManifestParsed.body_byte_size !== byteSize ||
            finalManifestParsed.raw_file_relative_path !== rawFileName) {
            bestEffortUnlink(fileSystem, rawFilePath);
            bestEffortUnlink(fileSystem, manifestFilePath);
            throw Object.assign(
                new Error('raw retention failed: final manifest field mismatch'),
                { code: 'SAFETY_ERROR' }
            );
        }
    } catch (err) {
        // Clean up any temp files — best-effort, do not mask the original error.
        bestEffortUnlink(fileSystem, tempHtmlPath);
        bestEffortUnlink(fileSystem, tempManifestPath);
        throw err;
    }

    return {
        manifest,
        manifestFilePath,
        rawFilePath,
        bodySha256,
        byteSize,
    };
}

/**
 * Build a capture manifest for a single raw response.
 */
function buildCaptureManifest(context, bodySha256, byteSize, rawFileName) {
    return {
        schema_version: 'fotmob-raw-capture-manifest/v1',
        source_provider: 'FotMob',
        source_kind: 'league_fixtures_page',
        request_method: 'GET',
        request_url: context.url,
        league_id: context.leagueId,
        competition: context.competition,
        requested_season: context.requestedSeason,
        canonical_season: context.canonicalSeason,
        capture_started_at: context.captureStartedAt,
        capture_completed_at: context.captureCompletedAt,
        http_status: context.httpStatus,
        content_type: context.contentType,
        body_byte_size: byteSize,
        body_sha256: bodySha256,
        collector_component: context.collectorComponent,
        collector_code_revision: context.collectorCodeRevision,
        network_authorization_mode: context.networkAuthorizationMode,
        raw_file_relative_path: rawFileName,
    };
}

module.exports = {
    // Constants
    FOTMOB_BASE_URL,
    EPL_FIXTURES_PER_SEASON,
    MAX_TOTAL_REQUESTS,
    STATUS_MAPPING_VERSION,
    ALLOWED_PROVIDER_STATUSES,

    // Season identity
    normaliseSeason,
    canonicalizeRequestedSeasons,
    canonicalizeCompetition,
    canonicalizeLeagueId,
    canonicalizeLeagueSlug,

    // Identity helpers
    generateCandidateId,
    isStrictAbsoluteTimestamp,
    isNumericExternalId,

    // Extraction
    extractNextData,
    extractPageIdentity,
    classifySeasonIdentity,
    extractFixtures,
    classifyFixtureRejection,
    deriveProviderStatus,

    // Building and validation
    buildCandidate,
    validateSeasonCandidates,
    validateAggregateCandidates,
    computeBusinessContentHash,
    computeV1IdentityProjectionHash,
    computeV2BusinessHash,

    // Pipeline
    exportCandidates,
    buildOutputDocument,
    buildSummaryDocument,
    buildV2OutputDocument,
    buildV2SummaryDocument,
    validateV2SummaryAgainstArtifact,
    verifyOutputPathSafety,
    writeOutputFiles,

    // Git state
    resolveGitState,

    // Raw retention
    writeRawRetention,
    buildCaptureManifest,

    // Network (for test injection)
    fetchPage,
    delay,

    // URL pattern
    FIXTURES_URL_PATTERN,
};
