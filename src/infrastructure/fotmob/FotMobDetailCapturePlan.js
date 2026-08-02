'use strict';

// lifecycle: permanent
//
// FotMob bounded detail capture — PLAN stage.
//
// Builds a deterministic, offline capture plan from a validated candidate
// artifact. Explicit selection is required: without at least one of
// `--season`, `--match-id`, or `--limit`, plan building fails — the plan
// never silently selects the full 1,140-candidate population.
//
// Output schema: fotmob-detail-capture-plan/v1 (see FotMobDetailCaptureContract).
// The plan document is written to a repository-external absolute path only.

const path = require('node:path');
const fs = require('node:fs');

const {
    PLAN_SCHEMA_VERSION,
    GENERATOR_COMPONENT,
    REQUIRED_COMPETITION,
    REQUIRED_LEAGUE_ID,
    canonicalJsonHash,
    isPlainObject,
    readAndValidateCandidateArtifact,
    sha256Text,
    assertNoSymlinkAncestors,
} = require('./FotMobDetailCaptureContract');

const VALID_SEASON_PATTERN = /^(\d{4})\/(\d{4})$/;

/**
 * Verify a path is repository-external and not a symlink.
 * Fails closed on relative paths, paths inside the repo, and symlinks.
 *
 * @param {string} outputPath - absolute path outside the repository
 * @param {object} options - { repositoryRoot, fsImpl }
 */
function verifyRepositoryExternalPath(outputPath, options = {}) {
    const repositoryRoot = options.repositoryRoot
        ? path.resolve(options.repositoryRoot)
        : path.resolve(__dirname, '..', '..', '..');
    const fileSystem = options.fsImpl || fs;

    if (!path.isAbsolute(String(outputPath || ''))) {
        throw Object.assign(new Error('output path must be absolute'), { code: 'INPUT_ERROR' });
    }
    const abs = path.resolve(String(outputPath || ''));
    const repoResolved = path.resolve(repositoryRoot);
    const rel = path.relative(repoResolved, abs);
    if (rel === '' || (!rel.startsWith('..') && !path.isAbsolute(rel))) {
        throw Object.assign(
            new Error(`output path must be outside the repository: ${abs}`),
            { code: 'SAFETY_ERROR' }
        );
    }

    // Reject symlinks along the way: lstat on the final path, the immediate
    // parent, and every ancestor component (an intermediate symlink could
    // redirect the write back into the repository).
    let stat = null;
    try {
        stat = fileSystem.lstatSync(abs);
    } catch {
        // parent existence check below
        stat = null;
    }
    if (stat && (stat.isSymbolicLink() || !stat.isFile())) {
        throw Object.assign(
            new Error(`output path must be a regular file, not a symlink: ${abs}`),
            { code: 'SAFETY_ERROR' }
        );
    }
    const parent = path.dirname(abs);
    let parentStat = null;
    try {
        parentStat = fileSystem.lstatSync(parent);
    } catch {
        throw Object.assign(
            new Error(`output parent directory does not exist: ${parent}`),
            { code: 'INPUT_ERROR' }
        );
    }
    if (parentStat.isSymbolicLink()) {
        throw Object.assign(
            new Error(`output parent directory must not be a symlink: ${parent}`),
            { code: 'SAFETY_ERROR' }
        );
    }
    assertNoSymlinkAncestors(parent, fileSystem);
    return abs;
}

/**
 * Build a deterministic capture plan from a validated candidate artifact.
 *
 * @param {object} options - {
 *   artifactPath (absolute, external),
 *   artifactSha256 (optional — must match when provided),
 *   seasons: string[] (canonical YYYY/YYYY, repeatable),
 *   matchIds: string[] (numeric, repeatable),
 *   limit: number|null,
 *   generatedAt (ISO string),
 *   collectorCodeRevision (40-hex),
 *   fsImpl?
 * }
 * @returns {{ plan: object, selectedCount: number, planBusinessSha256: string }}
 */
/* eslint-disable-next-line complexity */
function buildDeterministicCapturePlan(options = {}) {
    const artifactPath = String(options.artifactPath || '').trim();
    if (!artifactPath) {
        throw Object.assign(new Error('artifactPath is required'), { code: 'INPUT_ERROR' });
    }

    const seasons = Array.isArray(options.seasons) ? options.seasons : [];
    const matchIds = Array.isArray(options.matchIds) ? options.matchIds : [];
    const limit = options.limit === undefined || options.limit === null ? null : Number(options.limit);
    if (limit !== null && (!Number.isInteger(limit) || limit < 1)) {
        throw Object.assign(new Error('limit must be a positive integer'), { code: 'INPUT_ERROR' });
    }

    // Explicit selection required — never default to the full population.
    const hasSeasonFilter = seasons.length > 0;
    const hasMatchIdFilter = matchIds.length > 0;
    if (!hasSeasonFilter && !hasMatchIdFilter && limit === null) {
        throw Object.assign(
            new Error('explicit selection required: provide --season, --match-id, or --limit'),
            { code: 'INPUT_ERROR' }
        );
    }

    for (const s of seasons) {
        if (typeof s !== 'string' || !VALID_SEASON_PATTERN.test(s)) {
            throw Object.assign(new Error(`invalid season: ${JSON.stringify(s)}`), { code: 'INPUT_ERROR' });
        }
    }
    for (const id of matchIds) {
        if (!/^\d+$/.test(String(id))) {
            throw Object.assign(new Error(`invalid match id: ${JSON.stringify(id)}`), { code: 'INPUT_ERROR' });
        }
    }

    const loaded = readAndValidateCandidateArtifact(artifactPath, options.fsImpl);
    if (!loaded.ok) {
        throw Object.assign(
            new Error(`candidate artifact validation failed: ${loaded.errors.join('; ')}`),
            { code: 'INPUT_ERROR' }
        );
    }
    if (options.artifactSha256 && String(options.artifactSha256) !== loaded.artifact_sha256) {
        throw Object.assign(
            new Error('artifact SHA-256 mismatch'),
            { code: 'SAFETY_ERROR' }
        );
    }

    const seasonSet = new Set(seasons);
    const matchIdSet = new Set(matchIds.map(String));

    // Deterministic ordering: season → kickoff_at → source_match_id.
    const ordered = loaded.candidates
        .map((c, index) => ({
            ordinal: index + 1,
            candidate_id: String(c.candidate_id ?? c.id ?? ''),
            source_match_id: String(c.source_match_id ?? c.external_id ?? c.id ?? ''),
            competition: String(c.competition ?? REQUIRED_COMPETITION),
            season: String(c.season ?? ''),
            home_team: String(c.home_team ?? c.homeTeam ?? ''),
            away_team: String(c.away_team ?? c.awayTeam ?? ''),
            kickoff_at: String(c.kickoff_at ?? c.kickoffAt ?? c.kickoff_time ?? ''),
        }))
        .filter(c => {
            if (seasonSet.size > 0 && !seasonSet.has(c.season)) return false;
            if (matchIdSet.size > 0 && !matchIdSet.has(c.source_match_id)) return false;
            return true;
        })
        .sort((a, b) => {
            if (a.season !== b.season) return a.season < b.season ? -1 : 1;
            if (a.kickoff_at !== b.kickoff_at) return a.kickoff_at < b.kickoff_at ? -1 : 1;
            if (a.source_match_id !== b.source_match_id) return a.source_match_id < b.source_match_id ? -1 : 1;
            return 0;
        });

    const selected = limit === null ? ordered : ordered.slice(0, limit);

    const candidates = selected.map((c, index) => {
        const candidateIdentity = {
            source_match_id: c.source_match_id,
            competition: c.competition,
            season: c.season,
            home_team: c.home_team,
            away_team: c.away_team,
            kickoff_at: c.kickoff_at,
        };
        return {
            ordinal: index + 1,
            candidate_id: c.candidate_id,
            source_match_id: c.source_match_id,
            competition: c.competition,
            season: c.season,
            home_team: c.home_team,
            away_team: c.away_team,
            kickoff_at: c.kickoff_at,
            expected_request_path: `/match/${c.source_match_id}`,
            candidate_identity_sha256: canonicalJsonHash(candidateIdentity),
        };
    });

    const selectedSeasons = [...new Set(candidates.map(c => c.season))].sort();
    const planBusiness = {
        source_provider: 'FotMob',
        source_artifact_schema: loaded.schema,
        source_artifact_sha256: loaded.artifact_sha256,
        source_artifact_business_hash: loaded.business_hash,
        competition: REQUIRED_COMPETITION,
        league_id: REQUIRED_LEAGUE_ID,
        selected_seasons: selectedSeasons,
        selected_candidate_count: candidates.length,
        candidates,
    };
    const planBusinessSha256 = canonicalJsonHash(planBusiness);

    const plan = {
        schema_version: PLAN_SCHEMA_VERSION,
        ...planBusiness,
        plan_business_sha256: planBusinessSha256,
        generated_at: String(options.generatedAt || ''),
        generator_component: GENERATOR_COMPONENT,
        generator_code_revision: String(options.collectorCodeRevision || ''),
    };

    return {
        plan,
        selectedCount: candidates.length,
        planBusinessSha256,
    };
}

/**
 * Write a plan document to a repository-external absolute path.
 * Atomic write via temp file + rename; readback verified.
 *
 * @param {object} plan - plan document
 * @param {string} outputPath - absolute external path
 * @param {object} options - { repositoryRoot, fsImpl }
 * @returns {{ outputPath: string, writtenSha256: string }}
 */
function writePlanDocument(plan, outputPath, options = {}) {
    const fileSystem = options.fsImpl || fs;
    const abs = verifyRepositoryExternalPath(outputPath, options);
    const bytes = Buffer.from(JSON.stringify(plan, null, 2) + '\n', 'utf8');
    const writtenSha256 = sha256Text(bytes.toString('utf8'));

    const tmpPath = `${abs}.tmp-${process.pid}-${Date.now()}`;
    try {
        fileSystem.writeFileSync(tmpPath, bytes, { encoding: 'utf8', flag: 'wx' });
        fileSystem.renameSync(tmpPath, abs);
    } catch (err) {
        try { fileSystem.unlinkSync(tmpPath); } catch { /* ignore */ }
        throw Object.assign(
            new Error(`failed to write plan document: ${err.message}`),
            { code: 'SAFETY_ERROR' }
        );
    }

    // Readback verification.
    let readback;
    try {
        readback = fileSystem.readFileSync(abs, 'utf8');
    } catch (err) {
        throw Object.assign(
            new Error(`plan readback failed: ${err.message}`),
            { code: 'SAFETY_ERROR' }
        );
    }
    if (sha256Text(readback) !== writtenSha256) {
        throw Object.assign(
            new Error('plan readback hash mismatch'),
            { code: 'SAFETY_ERROR' }
        );
    }
    return { outputPath: abs, writtenSha256 };
}

module.exports = {
    VALID_SEASON_PATTERN,
    verifyRepositoryExternalPath,
    buildDeterministicCapturePlan,
    writePlanDocument,
};
