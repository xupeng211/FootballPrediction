'use strict';

// lifecycle: permanent
// Deterministic, read-only FotMob league schedule candidate exporter.
// No writes to repository, database, or project directories.
// Real output must go to an absolute path outside the Git worktree.

const crypto = require('node:crypto');
const path = require('node:path');
const fs = require('node:fs');

const FOTMOB_BASE_URL = 'https://www.fotmob.com';
const DEFAULT_UA = 'FootballPrediction-FotMobCandidateExporter/1.0';
const DEFAULT_TIMEOUT_MS = 60_000;
const DEFAULT_DELAY_MS = 5_000;
const MAX_TOTAL_REQUESTS = 6;
const FIXTURES_URL_PATTERN = '/leagues/{leagueId}/fixtures/{slug}';
const EPL_FIXTURES_PER_SEASON = 380;

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
 */
function isStrictAbsoluteTimestamp(value) {
    return typeof value === 'string' && /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(Z|[+-]\d{2}:\d{2})$/.test(value);
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
    for (const raw of values) {
        if (raw === undefined || raw === null) {
            throw Object.assign(new Error('Season value must be a non-empty string'), { code: 'INPUT_ERROR' });
        }
        const c = normaliseSeason(String(raw).trim());
        if (c === null) {
            throw Object.assign(
                new Error(
                    `Invalid season format: "${String(raw).trim()}" (expected YYYY/YYYY, YYYY-YYYY, YY/YY, or YY-YY)`
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
 * Fetch a URL and return { status, body }. Does NOT save full response.
 * Hard budget — callers must track request count externally.
 */
async function fetchPage(url, options = {}) {
    const userAgent = options.userAgent || DEFAULT_UA;
    const timeoutMs = options.timeoutMs || DEFAULT_TIMEOUT_MS;

    const ctrl = new AbortController();
    const timer = setTimeout(() => ctrl.abort(), timeoutMs);

    try {
        const res = await fetch(url, { signal: ctrl.signal, headers: { 'User-Agent': userAgent } });
        const body = await res.text();
        return {
            status: res.status,
            contentType: String(res.headers.get('content-type') || ''),
            body,
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
 * Normalise an observed season string into canonical YYYY/YYYY.
 * Accepts: 2022/2023, 2022-2023, 22/23, 2022/23, 22-23
 * Returns null for unrecognised formats.
 */
function normaliseSeason(value) {
    const raw = String(value ?? '').trim();
    if (!raw) return null;

    // Already canonical: YYYY/YYYY
    let match = raw.match(/^(\d{4})\/(\d{4})$/);
    if (match) return `${match[1]}/${match[2]}`;

    // Dash-separated: YYYY-YYYY
    match = raw.match(/^(\d{4})-(\d{4})$/);
    if (match) return `${match[1]}/${match[2]}`;

    // Abbreviated slash: YY/YY
    match = raw.match(/^(\d{2})\/(\d{2})$/);
    if (match) {
        const start = 2000 + Number(match[1]);
        const end = 2000 + Number(match[2]);
        if (end === start + 1) return `${start}/${end}`;
        return null;
    }

    return null;
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

    const rawSeason = query.season || pp.selectedSeason || pp.currentSeason || null;

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
 */
function extractAcceptedFixture(fixture) {
    if (classifyFixtureRejection(fixture) !== null) {
        return null;
    }
    const id = String(fixture.id).trim();
    const home = fixture.home.name;
    const away = fixture.away.name;
    const kickoff = fixture.status.utcTime;
    return { id, home, away, kickoff };
}

/**
 * Extract all fixtures from pageProps.
 * Returns { fixtures, audit } where audit records exclusion counts.
 * Excludes abandoned matches (status.reason.short === 'Ab').
 * Postponed, rescheduled, and cancelled matches are NOT excluded.
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
// Main export pipeline
// ----------------------------------------------------------------

/**
 * Build the FotMob fixtures page URL for one season.
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
function classifySeasonIdentity(identity, leagueId, requestedSeasonCanonical) {
    if (!identity) {
        return { ok: false, reason: 'identity_extraction_failed' };
    }
    const nameOk = Boolean(identity.league_name) && /premier\s*league/i.test(String(identity.league_name).trim());
    if (!nameOk) {
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

    if (resp.status === 403 || resp.status === 429) {
        return {
            seasonResult: { season, result: `blocked_http_${resp.status}`, candidates: 0, identity: null },
            candidates: [],
            requestsUsed: 1,
            stop: true,
            succeeded: false,
        };
    }

    if (resp.status !== 200) {
        return {
            seasonResult: { season, result: `http_${resp.status}`, candidates: 0, identity: null },
            candidates: [],
            requestsUsed: 1,
            stop: false,
            succeeded: false,
        };
    }

    const nd = extractNextData(resp.body);
    if (!nd) {
        return {
            seasonResult: { season, result: 'no_next_data', candidates: 0, identity: null },
            candidates: [],
            requestsUsed: 1,
            stop: false,
            succeeded: false,
        };
    }

    const identity = extractPageIdentity(nd);
    const verdict = classifySeasonIdentity(identity, leagueId, normaliseSeason(season));
    if (!verdict.ok) {
        return {
            seasonResult: {
                season,
                result: verdict.reason,
                candidates: 0,
                identity: buildSafeIdentitySummary(identity),
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
    // Rejected (contract-invalid) fixtures block season completion.
    const auditCloses =
        extraction.audit.raw_fixture_count ===
        extraction.audit.accepted_fixture_count +
            extraction.audit.excluded_fixture_count +
            extraction.audit.rejected_fixture_count;

    if (!auditCloses || extraction.audit.rejected_fixture_count > 0) {
        const errs = [...validation.errors];
        if (extraction.audit.rejected_fixture_count > 0) {
            errs.push(`unexpected_rejected_fixtures:${extraction.audit.rejected_fixture_count}`);
        }
        if (!auditCloses) {
            errs.push(
                `audit_not_closed:raw=${extraction.audit.raw_fixture_count},sum=${extraction.audit.accepted_fixture_count + extraction.audit.excluded_fixture_count + extraction.audit.rejected_fixture_count}`
            );
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
        },
        candidates: seasonCandidates,
        requestsUsed: 1,
        stop: false,
        succeeded: true,
    };
}

/**
 * Export FotMob league schedule candidates for one or more seasons.
 *
 * @param {Object} options
 * @param {number|string} options.leagueId        — FotMob league id (e.g. 47)
 * @param {string}        options.competition     — canonical competition name
 * @param {string[]}      options.seasons         — season strings (e.g. ["2022/2023"])
 * @param {string}        [options.leagueSlug]    — URL slug (default: derived from competition)
 * @param {Object}        [options.deps]          — dependency injection
 * @returns {Promise<Object>} { candidates, snapshot, validation }
 */
async function exportCandidates(options = {}) {
    const leagueId = String(options.leagueId);
    const competition = String(options.competition);
    const rawSeasons = Array.isArray(options.seasons) ? options.seasons : [];
    const leagueSlug = options.leagueSlug || competition.toLowerCase().replace(/\s+/g, '-');
    const deps = options.deps || {};
    const _delay = deps.delay || delay;
    const _clock = deps.clock || (() => new Date().toISOString());

    // Canonicalise before any network access
    const canonicalSeasons = canonicalizeRequestedSeasons(rawSeasons);
    const maxRequests = Math.min(canonicalSeasons.length * 2, MAX_TOTAL_REQUESTS);

    const allCandidates = [];
    const seasonResults = [];
    let requestCount = 0;

    for (let i = 0; i < canonicalSeasons.length; i += 1) {
        const outcome = await processSeason(canonicalSeasons[i], {
            leagueId,
            competition,
            leagueSlug,
            deps,
            userAgent: options.userAgent,
            requestCount,
            maxRequests,
        });

        requestCount += outcome.requestsUsed;
        seasonResults.push(outcome.seasonResult);
        allCandidates.push(...outcome.candidates);

        if (outcome.stop) {
            break;
        }

        // Delay only after a fully processed season, and never after the last one
        if (outcome.succeeded && i < canonicalSeasons.length - 1) {
            await _delay(options.requestDelayMs || DEFAULT_DELAY_MS);
        }
    }

    const businessHash = computeBusinessContentHash(allCandidates);
    const extractedAt = _clock();

    const aggregateV = validateAggregateCandidates(allCandidates, canonicalSeasons, EPL_FIXTURES_PER_SEASON);

    const allSeasonsComplete = seasonResults.every(r => r.result === 'complete') && aggregateV.valid;

    return {
        candidates: allCandidates,
        snapshot: {
            source_provider: 'FotMob',
            league_id: leagueId,
            competition,
            seasons: canonicalSeasons,
            candidate_count: allCandidates.length,
            business_content_sha256: businessHash,
        },
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
            schema_version: 'candidate-match-identity/v1',
        },
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

module.exports = {
    // Constants
    FOTMOB_BASE_URL,
    EPL_FIXTURES_PER_SEASON,
    MAX_TOTAL_REQUESTS,

    // Season identity
    normaliseSeason,
    canonicalizeRequestedSeasons,

    // Identity helpers
    generateCandidateId,
    isStrictAbsoluteTimestamp,
    isNumericExternalId,

    // Extraction
    extractNextData,
    extractPageIdentity,
    extractFixtures,
    classifyFixtureRejection,

    // Building and validation
    buildCandidate,
    validateSeasonCandidates,
    validateAggregateCandidates,
    computeBusinessContentHash,

    // Pipeline
    exportCandidates,
    buildOutputDocument,
    buildSummaryDocument,
    verifyOutputPathSafety,
    writeOutputFiles,

    // Network (for test injection)
    fetchPage,
    delay,

    // URL pattern
    FIXTURES_URL_PATTERN,
};
