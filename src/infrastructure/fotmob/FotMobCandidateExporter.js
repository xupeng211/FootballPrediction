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
    return new Promise(resolve => setTimeout(resolve, ms));
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
 * Extract all fixtures from pageProps.
 * Returns { fixtures, audit } where audit records exclusion counts.
 * Excludes abandoned matches (status.reason.short === 'Ab').
 * Postponed, rescheduled, and cancelled matches are NOT excluded.
 */
function extractFixtures(nd) {
    const pp = nd?.props?.pageProps;
    if (!pp)
        return {
            fixtures: [],
            audit: {
                raw_fixture_count: 0,
                excluded_fixture_count: 0,
                excluded_by_reason: {},
                excluded_fixture_samples: [],
                accepted_fixture_count: 0,
            },
        };

    const raw = pp.fixtures?.allMatches;
    if (!Array.isArray(raw))
        return {
            fixtures: [],
            audit: {
                raw_fixture_count: 0,
                excluded_fixture_count: 0,
                excluded_by_reason: {},
                excluded_fixture_samples: [],
                accepted_fixture_count: 0,
            },
        };

    const MAX_EXCLUDED_SAMPLES = 10;
    const audit = {
        raw_fixture_count: raw.length,
        excluded_fixture_count: 0,
        excluded_by_reason: {},
        excluded_fixture_samples: [],
        accepted_fixture_count: 0,
    };

    const fixtures = [];
    for (const f of raw) {
        const reasonShort = f?.status?.reason?.short;

        // Only explicit 'Ab' is excluded
        if (reasonShort === 'Ab') {
            audit.excluded_fixture_count += 1;
            audit.excluded_by_reason['Ab'] = (audit.excluded_by_reason['Ab'] || 0) + 1;
            if (audit.excluded_fixture_samples.length < MAX_EXCLUDED_SAMPLES) {
                const id = f?.id ? String(f.id).trim() : null;
                if (id && isNumericExternalId(id)) {
                    audit.excluded_fixture_samples.push({ source_match_id: id, reason_code: 'Ab' });
                }
            }
            continue;
        }

        const id = f?.id ? String(f.id).trim() : '';
        if (!isNumericExternalId(id)) continue;

        const home = f?.home?.name || null;
        const away = f?.away?.name || null;
        const kickoff = f?.status?.utcTime || null;

        if (!home || !away || !kickoff) continue;

        fixtures.push({ id, home, away, kickoff });
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
        if (!c.kickoff_at || !isStrictAbsoluteTimestamp(c.kickoff_at))
            errors.push(`bad_kickoff:${c.id}:${c.kickoff_at}`);
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
    const seasons = Array.isArray(options.seasons) ? options.seasons : [];
    const leagueSlug = options.leagueSlug || competition.toLowerCase().replace(/\s+/g, '-');
    const deps = options.deps || {};
    const _fetchPage = deps.fetchPage || fetchPage;
    const _delay = deps.delay || delay;
    const _clock = deps.clock || (() => new Date().toISOString());

    if (seasons.length === 0) {
        throw Object.assign(new Error('At least one season is required'), { code: 'INPUT_ERROR' });
    }
    const maxRequests = Math.min(seasons.length * 2, MAX_TOTAL_REQUESTS);

    const allCandidates = [];
    const seasonResults = [];
    let requestCount = 0;

    for (let i = 0; i < seasons.length; i += 1) {
        const season = seasons[i];
        const seasonParam = encodeURIComponent(season);
        const url = `${FOTMOB_BASE_URL}${FIXTURES_URL_PATTERN.replace('{leagueId}', leagueId).replace('{slug}', leagueSlug)}?season=${seasonParam}`;
        const seasonCandidates = [];
        let pageOk = false;

        // Try primary URL
        if (requestCount >= maxRequests) {
            seasonResults.push({ season, result: 'request_budget_exhausted', candidates: 0, identity: null });
            continue;
        }

        requestCount += 1;
        let resp;
        try {
            resp = await _fetchPage(url, { userAgent: options.userAgent });
        } catch (err) {
            seasonResults.push({ season, result: `fetch_error:${err.message}`, candidates: 0, identity: null });
            continue;
        }

        if (resp.status === 403 || resp.status === 429) {
            seasonResults.push({ season, result: `blocked_http_${resp.status}`, candidates: 0, identity: null });
            break;
        }

        if (resp.status !== 200) {
            seasonResults.push({ season, result: `http_${resp.status}`, candidates: 0, identity: null });
            continue;
        }

        const nd = extractNextData(resp.body);
        if (!nd) {
            seasonResults.push({ season, result: 'no_next_data', candidates: 0, identity: null });
            continue;
        }

        const identity = extractPageIdentity(nd);
        const requestedSeasonCanonical = normaliseSeason(season);
        const identityOk =
            identity &&
            identity.league_name &&
            /premier\s*league/i.test(String(identity.league_name).trim()) &&
            String(identity.league_id) === leagueId &&
            identity.season_canonical !== null &&
            identity.season_canonical === requestedSeasonCanonical;

        if (!identityOk) {
            const reason = !identity
                ? 'identity_extraction_failed'
                : !identity.league_name || !/premier\s*league/i.test(String(identity.league_name).trim())
                  ? 'competition_identity_mismatch'
                  : String(identity.league_id) !== leagueId
                    ? 'league_id_mismatch'
                    : identity.season_canonical === null
                      ? 'season_identity_missing'
                      : 'season_identity_mismatch';
            seasonResults.push({
                season,
                result: reason,
                candidates: 0,
                identity: identity
                    ? {
                          league_name: identity.league_name,
                          league_id: identity.league_id,
                          season_raw: identity.season_raw,
                          season_canonical: identity.season_canonical,
                      }
                    : null,
            });
            continue;
        }

        pageOk = true;
        const extraction = extractFixtures(nd);
        const fixtures = extraction.fixtures;
        for (const f of fixtures) {
            seasonCandidates.push(buildCandidate(f, leagueId, competition, season));
        }
        allCandidates.push(...seasonCandidates);

        const validation = validateSeasonCandidates(seasonCandidates, {
            competition,
            season,
            expectedFixtures: EPL_FIXTURES_PER_SEASON,
        });

        seasonResults.push({
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
        });

        // Delay between seasons
        if (i < seasons.length - 1) {
            await _delay(options.requestDelayMs || DEFAULT_DELAY_MS);
        }
    }

    const businessHash = computeBusinessContentHash(allCandidates);
    const extractedAt = _clock();

    const allValidated = seasonResults.every(r => r.result === 'complete');
    const totalExpected = seasons.length * EPL_FIXTURES_PER_SEASON;

    return {
        candidates: allCandidates,
        snapshot: {
            source_provider: 'FotMob',
            league_id: leagueId,
            competition,
            seasons,
            candidate_count: allCandidates.length,
            business_content_sha256: businessHash,
        },
        validation: {
            all_seasons_complete: allValidated && allCandidates.length === totalExpected,
            season_results: seasonResults,
            total_candidates: allCandidates.length,
            total_expected: totalExpected,
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
        try {
            fileSystem.unlinkSync(tempCandidate);
        } catch {}
        try {
            fileSystem.unlinkSync(tempSummary);
        } catch {}
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

    // Identity helpers
    generateCandidateId,
    isStrictAbsoluteTimestamp,
    isNumericExternalId,

    // Extraction
    extractNextData,
    extractPageIdentity,
    extractFixtures,

    // Building and validation
    buildCandidate,
    validateSeasonCandidates,
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
