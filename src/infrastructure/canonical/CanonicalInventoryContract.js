'use strict';

// lifecycle: permanent
// M3 canonical inventory 的版本化、离线、fail-closed 输入合同。它不连接数据库，
// 也不产生或伪造真实 FotMob 候选产物。

const crypto = require('node:crypto');
const fs = require('node:fs');
const path = require('node:path');
const {
    computeBusinessContentHash,
    isNumericExternalId,
    isStrictAbsoluteTimestamp,
} = require('../fotmob/FotMobCandidateExporter');

const SCHEMA_VERSION = 'canonical-inventory-artifact/v2';
const SOURCE_PROVIDER = 'FotMob';
const CANONICAL_PROVIDER = 'fotmob';
const COMPETITION = 'Premier League';
const SEASONS = Object.freeze(['2022/2023', '2023/2024', '2024/2025']);
const FIXTURES_PER_SEASON = 380;
const MASTER_COUNT = SEASONS.length * FIXTURES_PER_SEASON;
const APPROVED_CANARY_COUNTS = new Set([1, 10]);
const APPROVED_REAL_MASTER_V1_IDENTITY_PROJECTION_HASH =
    'eff881728429260012b4de9f93764a08096407e06b9dffd9c9f9e2b4e0bc9d3f';
// `abandoned` fixtures are excluded by the approved full-inventory preflight.
// They must not become durable canonical rows merely because status is outside
// the v1 identity projection.
const STATUS_MAPPING_VERSION = 'fotmob-status-to-matches-status/v1';
const FOTMOB_STATUS_TO_APPLICATION_STATUS = Object.freeze({
    scheduled: 'scheduled',
    finished: 'finished',
    postponed: 'postponed',
    cancelled: 'cancelled',
});
const ALLOWED_STATUSES = new Set(Object.keys(FOTMOB_STATUS_TO_APPLICATION_STATUS));
const CANDIDATE_FIELDS = new Set([
    'id',
    'source_provider',
    'source_match_id',
    'competition',
    'season',
    'home_team',
    'away_team',
    'kickoff_at',
    'provider_status',
    'status_mapping_version',
]);
const SHA256 = /^[0-9a-f]{64}$/;
const REPOSITORY_ROOT = path.resolve(__dirname, '../../..');

class CanonicalInventoryContractError extends Error {
    constructor(message, code = 'CANONICAL_INPUT_INVALID') {
        super(message);
        this.name = 'CanonicalInventoryContractError';
        this.code = code;
    }
}

function sha256Text(value) {
    return crypto.createHash('sha256').update(String(value), 'utf8').digest('hex');
}

function stableCanonicalize(value) {
    if (Array.isArray(value)) return value.map(stableCanonicalize);
    if (value && typeof value === 'object') {
        return Object.keys(value)
            .sort()
            .reduce((out, key) => {
                out[key] = stableCanonicalize(value[key]);
                return out;
            }, {});
    }
    return value;
}

function stableStringify(value) {
    return JSON.stringify(stableCanonicalize(value));
}

function canonicalOrder(left, right) {
    const leftKey = `${left.season}|${left.kickoff_at}|${left.home_team}|${left.away_team}|${left.source_match_id}`;
    const rightKey = `${right.season}|${right.kickoff_at}|${right.home_team}|${right.away_team}|${right.source_match_id}`;
    return leftKey.localeCompare(rightKey);
}

function assertText(value, field, candidateId) {
    if (typeof value !== 'string' || value.length === 0) {
        throw new CanonicalInventoryContractError(`candidate ${candidateId || '<unknown>'} requires ${field}`);
    }
    return value;
}

function canonicalCandidateProjection(candidate) {
    return {
        id: candidate.id,
        source_provider: candidate.source_provider,
        source_match_id: candidate.source_match_id,
        competition: candidate.competition,
        season: candidate.season,
        home_team: candidate.home_team,
        away_team: candidate.away_team,
        kickoff_at: candidate.kickoff_at,
        provider_status: candidate.provider_status,
        status_mapping_version: candidate.status_mapping_version,
    };
}

function immutableFingerprint(candidate) {
    return sha256Text(stableStringify(canonicalCandidateProjection(candidate)));
}

function computeV1IdentityProjectionHash(candidates) {
    return computeBusinessContentHash(
        candidates.map(candidate => ({
            id: candidate.id,
            source_provider: candidate.source_provider,
            source_match_id: candidate.source_match_id,
            competition: candidate.competition,
            season: candidate.season,
            home_team: candidate.home_team,
            away_team: candidate.away_team,
            kickoff_at: candidate.kickoff_at,
        }))
    );
}

function computeBusinessHash(candidates) {
    const rows = [...candidates].sort(canonicalOrder).map(canonicalCandidateProjection);
    return sha256Text(JSON.stringify(rows));
}

function countBySeason(candidates) {
    return candidates.reduce((counts, candidate) => {
        counts[candidate.season] = (counts[candidate.season] || 0) + 1;
        return counts;
    }, {});
}

function sameSeasonCounts(left, right) {
    return (
        SEASONS.every(season => Number(left?.[season] || 0) === Number(right?.[season] || 0)) &&
        Object.keys(left || {}).length === Object.keys(right || {}).length
    );
}

function isWithinDirectory(directory, candidatePath) {
    const relative = path.relative(directory, candidatePath);
    return (
        relative === '' || (!relative.startsWith(`..${path.sep}`) && relative !== '..' && !path.isAbsolute(relative))
    );
}

function validateCandidate(candidate) {
    if (!candidate || typeof candidate !== 'object' || Array.isArray(candidate)) {
        throw new CanonicalInventoryContractError('candidate must be an object');
    }
    for (const field of Object.keys(candidate)) {
        if (!CANDIDATE_FIELDS.has(field)) {
            throw new CanonicalInventoryContractError(`candidate has unknown semantic field ${field}`);
        }
    }
    const id = assertText(candidate.id, 'id');
    assertText(candidate.source_provider, 'source_provider', id);
    assertText(candidate.source_match_id, 'source_match_id', id);
    assertText(candidate.competition, 'competition', id);
    assertText(candidate.season, 'season', id);
    assertText(candidate.home_team, 'home_team', id);
    assertText(candidate.away_team, 'away_team', id);
    assertText(candidate.kickoff_at, 'kickoff_at', id);
    const providerStatus = assertText(candidate.provider_status, 'provider_status', id);
    const mappingVersion = assertText(candidate.status_mapping_version, 'status_mapping_version', id);
    if (candidate.source_provider !== SOURCE_PROVIDER) {
        throw new CanonicalInventoryContractError(`candidate ${id} source_provider must be ${SOURCE_PROVIDER}`);
    }
    if (!isNumericExternalId(candidate.source_match_id)) {
        throw new CanonicalInventoryContractError(`candidate ${id} source_match_id must be numeric`);
    }
    if (candidate.competition !== COMPETITION) {
        throw new CanonicalInventoryContractError(`candidate ${id} competition is out of scope`);
    }
    if (!SEASONS.includes(candidate.season)) {
        throw new CanonicalInventoryContractError(`candidate ${id} season is out of scope`);
    }
    if (candidate.home_team === candidate.away_team) {
        throw new CanonicalInventoryContractError(`candidate ${id} has identical home and away teams`);
    }
    if (!isStrictAbsoluteTimestamp(candidate.kickoff_at)) {
        throw new CanonicalInventoryContractError(`candidate ${id} kickoff_at must be absolute ISO-8601`);
    }
    if (mappingVersion !== STATUS_MAPPING_VERSION) {
        throw new CanonicalInventoryContractError(`candidate ${id} has unknown status mapping version`);
    }
    const applicationStatus = FOTMOB_STATUS_TO_APPLICATION_STATUS[providerStatus];
    if (!applicationStatus) {
        throw new CanonicalInventoryContractError(`candidate ${id} has unknown provider status`);
    }
    return {
        id,
        source_provider: candidate.source_provider,
        source_match_id: candidate.source_match_id,
        competition: candidate.competition,
        season: candidate.season,
        home_team: candidate.home_team,
        away_team: candidate.away_team,
        kickoff_at: candidate.kickoff_at,
        provider_status: providerStatus,
        status_mapping_version: mappingVersion,
        application_status: applicationStatus,
    };
}

function assertSha(value, label) {
    if (typeof value !== 'string' || !SHA256.test(value)) {
        throw new CanonicalInventoryContractError(`${label} must be a lowercase SHA-256`);
    }
}

// eslint-disable-next-line complexity -- artifact metadata is one atomic fail-closed contract.
function assertMetadata(document, candidates, options = {}) {
    const artifact = document?.artifact;
    if (!artifact || typeof artifact !== 'object' || Array.isArray(artifact)) {
        throw new CanonicalInventoryContractError('artifact metadata is required');
    }
    if (document.schema_version !== SCHEMA_VERSION) {
        throw new CanonicalInventoryContractError('unsupported artifact schema version');
    }
    if (!['master', 'canary'].includes(artifact.kind)) {
        throw new CanonicalInventoryContractError('artifact kind must be master or canary');
    }
    if (artifact.competition !== COMPETITION) {
        throw new CanonicalInventoryContractError('artifact competition is out of scope');
    }
    if (
        !Array.isArray(artifact.seasons) ||
        artifact.seasons.length !== SEASONS.length ||
        !SEASONS.every((season, index) => artifact.seasons[index] === season)
    ) {
        throw new CanonicalInventoryContractError('artifact seasons must be the approved ordered EPL scope');
    }
    if (!Number.isInteger(artifact.candidate_count) || artifact.candidate_count !== candidates.length) {
        throw new CanonicalInventoryContractError('artifact candidate_count does not match candidates');
    }
    assertSha(artifact.business_hash, 'artifact business_hash');
    assertSha(artifact.identity_projection_hash, 'artifact identity_projection_hash');
    if (artifact.status_mapping_version !== STATUS_MAPPING_VERSION) {
        throw new CanonicalInventoryContractError('artifact status_mapping_version is not approved');
    }
    if (!sameSeasonCounts(artifact.per_season_counts, countBySeason(candidates))) {
        throw new CanonicalInventoryContractError('artifact per_season_counts does not match candidates');
    }
    if (artifact.business_hash !== computeBusinessHash(candidates)) {
        throw new CanonicalInventoryContractError('artifact business_hash mismatch');
    }
    if (artifact.identity_projection_hash !== computeV1IdentityProjectionHash(candidates)) {
        throw new CanonicalInventoryContractError(
            'artifact identity projection mismatch',
            'V1_IDENTITY_PROJECTION_MISMATCH'
        );
    }
    if (artifact.synthetic_test_only === true) {
        if (options.allowSyntheticTestOnly !== true) {
            throw new CanonicalInventoryContractError('synthetic artifacts are disposable-test-only');
        }
    } else if (
        artifact.kind === 'master' &&
        artifact.identity_projection_hash !== APPROVED_REAL_MASTER_V1_IDENTITY_PROJECTION_HASH
    ) {
        throw new CanonicalInventoryContractError(
            'real master does not match the approved v1 identity projection',
            'V1_IDENTITY_PROJECTION_MISMATCH'
        );
    }
    return artifact;
}

function assertMasterPopulation(artifact, candidates) {
    if (artifact.kind !== 'master') return;
    if (artifact.parent_master !== undefined && artifact.parent_master !== null) {
        throw new CanonicalInventoryContractError('master artifact must not have parent_master');
    }
    if (candidates.length !== MASTER_COUNT) {
        throw new CanonicalInventoryContractError(`master artifact count must be ${MASTER_COUNT}`);
    }
    const counts = countBySeason(candidates);
    for (const season of SEASONS) {
        if (counts[season] !== FIXTURES_PER_SEASON) {
            throw new CanonicalInventoryContractError(
                `master artifact season ${season} must contain ${FIXTURES_PER_SEASON} candidates`
            );
        }
    }
}

// eslint-disable-next-line complexity -- all parent/allowlist assertions form one atomic contract.
function assertCanaryPopulation(artifact, candidates, options = {}) {
    if (artifact.kind !== 'canary') return;
    if (!APPROVED_CANARY_COUNTS.has(candidates.length)) {
        throw new CanonicalInventoryContractError('canary artifact count must be an approved bounded size (1 or 10)');
    }
    const declared = artifact.parent_master;
    if (!declared || typeof declared !== 'object') {
        throw new CanonicalInventoryContractError('canary parent_master metadata is required');
    }
    assertSha(declared.sha256, 'canary parent sha256');
    for (const field of ['business_hash', 'identity_projection_hash']) {
        assertSha(declared[field], `canary parent ${field}`);
    }
    if (!Number.isInteger(declared.byte_size) || declared.byte_size <= 0) {
        throw new CanonicalInventoryContractError('canary parent byte_size is required');
    }
    if (!options.parentArtifactPath) {
        throw new CanonicalInventoryContractError('canary artifact requires its physical parent master path');
    }
    // Do not accept an in-memory parent document or caller-supplied binding as
    // evidence. The canary declaration binds its parent by bytes, so re-read the
    // ordinary external parent file and make that physical binding the only
    // source of lineage metadata.
    const parent = readOrdinaryArtifact(options.parentArtifactPath, {
        sha256: declared.sha256,
        byte_size: declared.byte_size,
        allowSyntheticTestOnly: options.allowSyntheticTestOnly === true,
    });
    if (parent.artifact.kind !== 'master') {
        throw new CanonicalInventoryContractError('canary parent must be a master artifact');
    }
    if (Boolean(parent.artifact.synthetic_test_only) !== Boolean(artifact.synthetic_test_only)) {
        throw new CanonicalInventoryContractError('canary and parent synthetic classification must match');
    }
    for (const field of ['business_hash', 'identity_projection_hash']) {
        if (declared[field] !== parent.artifact[field]) {
            throw new CanonicalInventoryContractError(`canary parent ${field} mismatch`);
        }
    }
    if (declared.status_mapping_version !== parent.artifact.status_mapping_version) {
        throw new CanonicalInventoryContractError('canary parent status mapping version mismatch');
    }
    if (
        declared.candidate_count !== MASTER_COUNT ||
        !sameSeasonCounts(declared.per_season_counts, parent.artifact.per_season_counts)
    ) {
        throw new CanonicalInventoryContractError('canary parent population metadata mismatch');
    }
    if (
        !Array.isArray(artifact.allowlist) ||
        artifact.allowlist.length !== candidates.length ||
        artifact.allowlist.length === 0
    ) {
        throw new CanonicalInventoryContractError('canary allowlist must exactly cover candidates');
    }
    const parentById = new Map(parent.candidates.map(candidate => [candidate.id, candidate]));
    const candidateIds = candidates.map(candidate => candidate.id);
    if (
        new Set(artifact.allowlist).size !== artifact.allowlist.length ||
        new Set(candidateIds).size !== candidateIds.length
    ) {
        throw new CanonicalInventoryContractError('canary allowlist and candidate IDs must be unique');
    }
    if (!artifact.allowlist.every((id, index) => id === candidateIds[index])) {
        throw new CanonicalInventoryContractError('canary candidates must follow its explicit allowlist order');
    }
    const parentOrder = parent.candidates.filter(candidate => artifact.allowlist.includes(candidate.id));
    if (!parentOrder.every((candidate, index) => candidate.id === candidateIds[index])) {
        throw new CanonicalInventoryContractError('canary candidates must follow parent deterministic order');
    }
    for (const candidate of candidates) {
        const parentCandidate = parentById.get(candidate.id);
        if (
            !parentCandidate ||
            stableStringify(canonicalCandidateProjection(parentCandidate)) !==
                stableStringify(canonicalCandidateProjection(candidate))
        ) {
            throw new CanonicalInventoryContractError(
                `canary candidate ${candidate.id} is not the exact parent projection`
            );
        }
    }
    return {
        document: parent.document,
        binding: {
            path: parent.path,
            sha256: parent.sha256,
            byte_size: parent.byte_size,
        },
    };
}

function validateArtifactDocument(document, options = {}) {
    if (!document || typeof document !== 'object' || Array.isArray(document) || !Array.isArray(document.candidates)) {
        throw new CanonicalInventoryContractError('artifact document with candidates array is required');
    }
    const candidates = document.candidates.map(validateCandidate);
    const ids = new Set();
    const providerIds = new Set();
    const fixtureIdentities = new Set();
    for (const candidate of candidates) {
        if (ids.has(candidate.id)) throw new CanonicalInventoryContractError(`duplicate candidate ID ${candidate.id}`);
        if (providerIds.has(candidate.source_match_id)) {
            throw new CanonicalInventoryContractError(`duplicate provider match ID ${candidate.source_match_id}`);
        }
        const fixtureIdentity = [
            candidate.competition,
            candidate.season,
            candidate.home_team,
            candidate.away_team,
        ].join('\u0000');
        if (fixtureIdentities.has(fixtureIdentity)) {
            throw new CanonicalInventoryContractError(`duplicate ordered fixture identity ${candidate.id}`);
        }
        ids.add(candidate.id);
        providerIds.add(candidate.source_match_id);
        fixtureIdentities.add(fixtureIdentity);
    }
    const artifact = assertMetadata(document, candidates, options);
    assertMasterPopulation(artifact, candidates);
    const parent = assertCanaryPopulation(artifact, candidates, options);
    return {
        document: { ...document, candidates },
        artifact,
        candidates,
        parent_document: parent?.document,
        parent_binding: parent?.binding,
        parent_artifact_path: parent?.binding.path,
    };
}

// eslint-disable-next-line complexity -- file identity checks must remain adjacent to parsing.
function readOrdinaryArtifact(filePath, expected = {}, fileSystem = fs) {
    if (!path.isAbsolute(filePath)) throw new CanonicalInventoryContractError('artifact path must be absolute');
    const supplied = fileSystem.lstatSync(filePath);
    if (!supplied.isFile() || supplied.isSymbolicLink()) {
        throw new CanonicalInventoryContractError('artifact must be an ordinary non-symlink file');
    }
    // `path.resolve()` is lexical and does not reveal an intermediate symlink.
    // Bind the read to the physical ordinary file, then compare physical roots so
    // `/tmp/link-to-repository/artifact.json` cannot bypass the external-artifact
    // boundary.
    const repositoryPath = fileSystem.realpathSync(REPOSITORY_ROOT);
    const resolvedArtifactPath = fileSystem.realpathSync(filePath);
    if (isWithinDirectory(repositoryPath, resolvedArtifactPath)) {
        throw new CanonicalInventoryContractError('artifact must be repository-external');
    }
    const before = fileSystem.lstatSync(resolvedArtifactPath);
    if (!before.isFile() || before.isSymbolicLink()) {
        throw new CanonicalInventoryContractError('artifact must be an ordinary non-symlink file');
    }
    const bytes = fileSystem.readFileSync(resolvedArtifactPath);
    const after = fileSystem.lstatSync(resolvedArtifactPath);
    if (
        before.dev !== after.dev ||
        before.ino !== after.ino ||
        before.size !== after.size ||
        before.mtimeMs !== after.mtimeMs
    ) {
        throw new CanonicalInventoryContractError('artifact changed while being read', 'ARTIFACT_MUTATED');
    }
    const sha256 = crypto.createHash('sha256').update(bytes).digest('hex');
    if (expected.sha256 && sha256 !== expected.sha256) {
        throw new CanonicalInventoryContractError('artifact SHA-256 mismatch');
    }
    if (expected.byte_size !== undefined && before.size !== expected.byte_size) {
        throw new CanonicalInventoryContractError('artifact byte size mismatch');
    }
    let document;
    try {
        document = JSON.parse(bytes.toString('utf8'));
    } catch {
        throw new CanonicalInventoryContractError('artifact is not valid UTF-8 JSON');
    }
    return {
        ...validateArtifactDocument(document, {
            parentArtifactPath: expected.parentArtifactPath,
            allowSyntheticTestOnly: expected.allowSyntheticTestOnly === true,
        }),
        sha256,
        byte_size: before.size,
        path: resolvedArtifactPath,
    };
}

module.exports = {
    APPROVED_CANARY_COUNTS,
    APPROVED_REAL_MASTER_V1_IDENTITY_PROJECTION_HASH,
    ALLOWED_STATUSES,
    CANONICAL_PROVIDER,
    COMPETITION,
    CanonicalInventoryContractError,
    FOTMOB_STATUS_TO_APPLICATION_STATUS,
    FIXTURES_PER_SEASON,
    MASTER_COUNT,
    SCHEMA_VERSION,
    SEASONS,
    SOURCE_PROVIDER,
    STATUS_MAPPING_VERSION,
    canonicalCandidateProjection,
    canonicalOrder,
    computeBusinessHash,
    computeV1IdentityProjectionHash,
    immutableFingerprint,
    readOrdinaryArtifact,
    sha256Text,
    stableStringify,
    validateArtifactDocument,
};
