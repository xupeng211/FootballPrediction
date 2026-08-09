#!/usr/bin/env node
'use strict';

// lifecycle: permanent；M3-R1 有界重建入口：把多个 historical_git_recovery 来源
// 一次性确定性重建为 repo-external 发射输出 + 重建收据。
//
// 设计边界（与现有 odds_staging 模块一致）：
// - 只复用 runOfflineStaging / emitDeterministicResult，不重实现任何 staging 逻辑。
// - 输入 bundle 与输出 emit-dir 都必须在 Git 仓库之外；bundle 内相对路径不得逃逸。
// - 无网络、无数据库、无仓库写入；默认模式 dry_run_no_write（只写 --emit-dir）。
// - 来源通过 manifest.repository_provenance（git blob SHA）绑定到不可变 Git 对象；
//   本脚本不执行 git、不重新恢复 raw，只核验 raw_size_bytes / raw_sha256。
// - 收据不含任何期望计数常量（如 38,616 / 216 / 892 / 888 / 4 均不出现）；
//   只记录实际结果，基线对照属于审计证据而非流水线。
// - 业务哈希为 M3-R1 定义组合（见 computeSourcePopulationBusinessHash）：
//   D4F 文档遗留的 07e579ed… 组合从未保留在仓库中，无法从 current main 复算，
//   因此本脚本定义并记录自己的确定性组合（计数层面与历史基线完全一致）。

const crypto = require('node:crypto');
const fs = require('node:fs');
const path = require('node:path');
const { OfflineStagingError } = require('../../../src/infrastructure/odds_staging/sourceManifest');
const {
    buildSemanticMatchIdentity,
    isStrictAbsoluteTimestamp,
    stableCanonicalize,
    stableStringify,
} = require('../../../src/infrastructure/odds_staging/contracts');
const { emitDeterministicResult, loadCandidatesForRun, runOfflineStaging } = require('../../../src/infrastructure/odds_staging/pipeline');

const BUNDLE_SCHEMA_VERSION = 'm3-historical-odds-rebuild-bundle/v1';
const RECEIPT_SCHEMA_VERSION = 'm3-historical-odds-rebuild-receipt/v1';

const EXIT_CODES = Object.freeze({
    success: 0,
    input_error: 2,
    safety_boundary_error: 3,
    unexpected_error: 5,
});

function usage() {
    return [
        'Usage:',
        '  npm run odds:staging:rebuild -- --bundle <repo-external-bundle-dir> --emit-dir <repo-external-existing-empty-dir> --ingested-at <ISO-8601> [--candidates <local-candidates.json>]',
        '',
        'Required:',
        '  --bundle <directory>      repo-external dir containing sources.json (m3-historical-odds-rebuild-bundle/v1)',
        '  --emit-dir <directory>    repo-external, existing, empty; per-source outputs + receipt.json are written here',
        '  --ingested-at <ISO-8601>  fixed ingestion timestamp for deterministic output',
        '',
        'Optional:',
        '  --candidates <file>       candidate artifact (e.g. m3-d2b candidate-match-identity.v1.json) for linkage classification',
        '',
        'Safety:',
        '  Bundle, candidates and emit dir must all be outside the Git repository.',
        '  Bundle-relative csv/manifest paths must stay inside the bundle directory.',
        '  No network, no database, no repository writes. Receipt contains actuals only, never hard-coded baselines.',
        '',
        'Exit codes:',
        '  0 completed; 2 manifest/input error; 3 safety boundary error; 5 unexpected error.',
    ].join('\n');
}

function readOption(argv, index, option) {
    const value = argv[index + 1];
    if (!value || String(value).startsWith('--')) {
        throw new OfflineStagingError('INPUT_ERROR', `${option} requires a value`);
    }
    return String(value);
}

function parseArgs(argv = []) {
    const args = { bundle: '', candidates: '', emitDir: '', ingestedAt: '', help: false };
    const mapping = { '--bundle': 'bundle', '--candidates': 'candidates', '--emit-dir': 'emitDir', '--ingested-at': 'ingestedAt' };
    for (let index = 0; index < argv.length; index += 1) {
        const token = String(argv[index]);
        if (token === '--help' || token === '-h') {
            args.help = true;
            continue;
        }
        const equalsOption = Object.keys(mapping).find(option => token.startsWith(`${option}=`));
        if (equalsOption) {
            args[mapping[equalsOption]] = token.slice(equalsOption.length + 1);
            continue;
        }
        if (mapping[token]) {
            args[mapping[token]] = readOption(argv, index, token);
            index += 1;
            continue;
        }
        throw new OfflineStagingError('INPUT_ERROR', `unknown argument: ${token}`);
    }
    if (!args.help) {
        for (const field of ['bundle', 'emitDir', 'ingestedAt']) {
            if (!args[field]) {
                throw new OfflineStagingError('INPUT_ERROR', `--${field} is required`);
            }
        }
        if (!isStrictAbsoluteTimestamp(args.ingestedAt)) {
            throw new OfflineStagingError('INPUT_ERROR', 'ingested_at must be an ISO-8601 timestamp with Z or an explicit numeric offset');
        }
    }
    return args;
}

function isInsidePath(rootPath, targetPath) {
    const relative = path.relative(rootPath, targetPath);
    return relative === '' || (!relative.startsWith(`..${path.sep}`) && relative !== '..' && !path.isAbsolute(relative));
}

function assertOutsideRepository(directory, fileSystem) {
    let realDirectory;
    try {
        realDirectory = fileSystem.realpathSync(directory);
    } catch {
        throw new OfflineStagingError('INPUT_ERROR', 'input or emit directory does not exist');
    }
    const repositoryRoot = fileSystem.realpathSync(path.resolve(__dirname, '../../..'));
    if (isInsidePath(repositoryRoot, realDirectory)) {
        throw new OfflineStagingError('SAFETY_ERROR', 'input and emit directories must be outside the Git repository');
    }
    return realDirectory;
}

function assertInsideRoot(rootPath, targetPath) {
    const relative = path.relative(rootPath, targetPath);
    if (relative === '' || relative.startsWith('..') || path.isAbsolute(relative)) {
        throw new OfflineStagingError('SAFETY_ERROR', 'bundle-relative input path must stay inside the bundle directory');
    }
}

function sha256Buffer(buffer) {
    return crypto.createHash('sha256').update(buffer).digest('hex');
}

function parseBundleIndex(bundleDirectory, fileSystem) {
    const indexPath = path.join(bundleDirectory, 'sources.json');
    if (!fileSystem.existsSync(indexPath)) {
        throw new OfflineStagingError('INPUT_ERROR', 'bundle directory must contain sources.json');
    }
    let payload;
    try {
        payload = JSON.parse(fileSystem.readFileSync(indexPath, 'utf8'));
    } catch (error) {
        throw new OfflineStagingError('INPUT_ERROR', `unable to parse bundle sources.json: ${error.message}`);
    }
    if (!payload || typeof payload !== 'object' || payload.schema_version !== BUNDLE_SCHEMA_VERSION) {
        throw new OfflineStagingError('INPUT_ERROR', `unsupported bundle schema_version: expected ${BUNDLE_SCHEMA_VERSION}`);
    }
    if (!Array.isArray(payload.sources) || payload.sources.length === 0) {
        throw new OfflineStagingError('INPUT_ERROR', 'bundle sources must be a non-empty array');
    }
    return payload.sources;
}

function resolveBundleSourcePath(bundleDirectory, value, field, id, fileSystem) {
    const resolved = path.resolve(bundleDirectory, value);
    assertInsideRoot(bundleDirectory, resolved);
    if (!fileSystem.existsSync(resolved)) {
        throw new OfflineStagingError('INPUT_ERROR', `bundle source ${id} ${field} does not exist: ${value}`);
    }
    return resolved;
}

function buildBundleSourceEntry(entry, seenIds, bundleDirectory, fileSystem) {
    const id = String(entry?.id || '').trim();
    if (!id) {
        throw new OfflineStagingError('INPUT_ERROR', 'bundle source missing required field: id');
    }
    // id 会成为 emit 目录下的子目录名：必须是安全路径段，防止 ../ 逃逸
    // （逃逸会允许写入并在失败回滚时递归删除 emit-dir 之外的位置）。
    if (!/^[A-Za-z0-9][A-Za-z0-9._-]*$/.test(id) || id === '.' || id === '..') {
        throw new OfflineStagingError('SAFETY_ERROR', `bundle source id must be a safe path segment: ${id}`);
    }
    if (seenIds.has(id)) {
        throw new OfflineStagingError('INPUT_ERROR', `duplicate bundle source id: ${id}`);
    }
    seenIds.add(id);
    const source = { id };
    for (const field of ['csv', 'manifest']) {
        const value = String(entry?.[field] || '').trim();
        if (!value) {
            throw new OfflineStagingError('INPUT_ERROR', `bundle source ${id} missing required field: ${field}`);
        }
        source[field] = resolveBundleSourcePath(bundleDirectory, value, field, id, fileSystem);
    }
    return source;
}

function loadBundle(bundleDirectory, fileSystem) {
    const sources = [];
    const seenIds = new Set();
    for (const entry of parseBundleIndex(bundleDirectory, fileSystem)) {
        sources.push(buildBundleSourceEntry(entry, seenIds, bundleDirectory, fileSystem));
    }
    return sources;
}

function readCandidatesArtifact(candidatePath, fileSystem) {
    const absolutePath = path.resolve(candidatePath);
    if (!fileSystem.existsSync(absolutePath)) {
        throw new OfflineStagingError('INPUT_ERROR', 'candidates file does not exist');
    }
    const buffer = fileSystem.readFileSync(absolutePath);
    let payload;
    try {
        payload = JSON.parse(buffer.toString('utf8'));
    } catch (error) {
        throw new OfflineStagingError('INPUT_ERROR', `unable to parse candidates JSON: ${error.message}`);
    }
    return {
        basename: path.basename(absolutePath),
        raw_sha256: sha256Buffer(buffer),
        declared_business_content_sha256: String(payload?.snapshot?.business_content_sha256 || '').trim() || null,
    };
}

/**
 * M3-R1 defined deterministic composition for the source population business hash:
 * sha256 over JSON.stringify of the sorted projection of canonical match identities
 * (sort key season|kickoff_at|home_team|away_team; fields source_provider, competition,
 * season, kickoff_at, home_team, away_team). The legacy D4F hash 07e579ed… was
 * documented without its composition and is not recomputable from retained artifacts;
 * this composition is the canonical M3-R1 replacement and is recorded in the receipt.
 * The sort is code-unit comparison (locale-independent): localeCompare without a
 * pinned locale would change collation order — and therefore the hash — across
 * differently-localed runtimes.
 */
function compareIdentitySortKey(left, right) {
    const leftKey = `${left.season}|${left.kickoff_at}|${left.home_team}|${left.away_team}`;
    const rightKey = `${right.season}|${right.kickoff_at}|${right.home_team}|${right.away_team}`;
    return leftKey < rightKey ? -1 : leftKey > rightKey ? 1 : 0;
}

function computeSourcePopulationBusinessHash(identities) {
    const sorted = [...identities].sort(compareIdentitySortKey);
    const content = sorted.map(identity => ({
        source_provider: identity.source_provider,
        competition: identity.competition,
        season: identity.season,
        kickoff_at: identity.kickoff_at,
        home_team: identity.home_team,
        away_team: identity.away_team,
    }));
    return crypto.createHash('sha256').update(JSON.stringify(content)).digest('hex');
}

/**
 * Quarantine entries use the quarantine schema, not the full observation schema;
 * reconstruct the identity-relevant observation view (same fields my audit analysis
 * used to reproduce the 892-candidate population from current main).
 */
function quarantineToObservation(entry) {
    const sourceFields = entry.evidence?.source_fields || {};
    return {
        source_provider: entry.source_provider,
        source_match_id: entry.source_match_id,
        competition: sourceFields.competition,
        season: sourceFields.season,
        kickoff_at: sourceFields.kickoff_at,
        home_team: sourceFields.home_team,
        away_team: sourceFields.away_team,
        match_link: entry.evidence?.match_link,
    };
}

function buildPopulationEntries(allObservations) {
    const byIdentity = new Map();
    for (const observation of allObservations) {
        const identity = buildSemanticMatchIdentity(observation);
        // D4F population contract: unique source candidates are exactly the
        // canonical_match_identity outputs. Adapter-quarantine entries carry no
        // row identity (unresolved_raw_identity) and must not inflate the count.
        if (identity.identity_mode !== 'canonical_match_identity') {
            continue;
        }
        const key = stableStringify(identity);
        if (!byIdentity.has(key)) {
            byIdentity.set(key, { identity, observations: [] });
        }
        byIdentity.get(key).observations.push(observation);
    }
    return [...byIdentity.values()];
}

function buildSourcePopulation(entries) {
    const identities = entries.map(entry => entry.identity);
    const perSeason = {};
    for (const identity of identities) {
        perSeason[identity.season] = (perSeason[identity.season] || 0) + 1;
    }
    return {
        unique_candidates: identities.length,
        per_season: stableCanonicalize(perSeason),
        identity_mode: identities[0] ? identities[0].identity_mode : null,
        business_content_sha256: computeSourcePopulationBusinessHash(identities),
    };
}

function classifyLinkage(entries) {
    const classification = {};
    const matchedFotmobIds = new Set();
    const conflictSamples = [];
    for (const entry of entries) {
        const link = entry.observations[0].match_link || {};
        const key = `${link.status || 'unmatched'}/${link.method || 'not_evaluated'}`;
        classification[key] = (classification[key] || 0) + 1;
        if (link.status === 'matched') {
            matchedFotmobIds.add(link.matched_id);
        }
        if ((link.status || '') === 'unmatched' && String(link.method || '').startsWith('derived_kickoff_conflict')) {
            conflictSamples.push({
                season: entry.identity.season,
                home_team: entry.identity.home_team,
                away_team: entry.identity.away_team,
                kickoff_at: entry.identity.kickoff_at,
                method: link.method,
                delta_minutes: link.evidence?.delta_minutes ?? null,
                candidate_ids: [...new Set(link.candidate_ids || [])].sort(),
            });
        }
    }
    conflictSamples.sort((left, right) => left.kickoff_at.localeCompare(right.kickoff_at));
    return {
        classification: stableCanonicalize(classification),
        distinct_matched_fotmob_ids: matchedFotmobIds.size,
        conflict_samples: stableCanonicalize(conflictSamples),
    };
}

function assertEmptyEmitDirectory(emitDirectory, fileSystem) {
    if (!fileSystem.existsSync(emitDirectory)) {
        throw new OfflineStagingError('SAFETY_ERROR', 'emit directory must already exist; it will not be created automatically');
    }
    if (!fileSystem.statSync(emitDirectory).isDirectory()) {
        throw new OfflineStagingError('SAFETY_ERROR', 'emit directory must be a directory');
    }
    if (fileSystem.readdirSync(emitDirectory).length > 0) {
        throw new OfflineStagingError('SAFETY_ERROR', 'emit directory must be empty before a rebuild');
    }
}

function loadManifestJson(manifestPath, sourceId, fileSystem) {
    try {
        return JSON.parse(fileSystem.readFileSync(manifestPath, 'utf8'));
    } catch (error) {
        throw new OfflineStagingError('INPUT_ERROR', `unable to parse manifest ${sourceId}: ${error.message}`);
    }
}

function emitSourceResult(result, emitDirectory, source, repositoryRoot, createdDirectories, fileSystem) {
    const subdirectory = path.join(emitDirectory, source.id);
    if (fileSystem.existsSync(subdirectory)) {
        throw new OfflineStagingError('SAFETY_ERROR', `emit subdirectory already exists: ${source.id}`);
    }
    fileSystem.mkdirSync(subdirectory);
    createdDirectories.push(subdirectory);
    emitDeterministicResult(result, subdirectory, { repositoryRoot }, fileSystem);
    return subdirectory;
}

function countQuarantineReasons(quarantine) {
    const reasonCounts = {};
    for (const quarantineEntry of quarantine) {
        for (const reason of quarantineEntry.reasons || []) {
            reasonCounts[reason] = (reasonCounts[reason] || 0) + 1;
        }
    }
    return reasonCounts;
}

function buildReceiptSource(result, source) {
    const manifest = result.normalized_manifest;
    return stableCanonicalize({
        id: source.id,
        raw_sha256: result.summary.raw_sha256,
        raw_size_bytes: result.summary.raw_size_bytes,
        repository_provenance: manifest.repository_provenance,
        total_observations: result.summary.total_observations,
        accepted_count: result.summary.accepted_count,
        quarantine_count: result.summary.quarantine_count,
        quarantine_reasons: stableCanonicalize(countQuarantineReasons(result.quarantine)),
    });
}

function rollbackCreatedDirectories(createdDirectories, fileSystem) {
    for (const directory of createdDirectories) {
        try {
            fileSystem.rmSync(directory, { recursive: true, force: true });
        } catch {
            // 只保留原始失败；清理失败不得隐藏主错误或触碰任务前既有文件。
        }
    }
}

function runRebuild(options = {}, dependencies = {}) {
    const fileSystem = dependencies.fileSystem || fs;
    const bundleDirectory = assertOutsideRepository(path.resolve(options.bundle), fileSystem);
    const emitDirectory = assertOutsideRepository(path.resolve(options.emitDir), fileSystem);
    assertEmptyEmitDirectory(emitDirectory, fileSystem);

    const sources = loadBundle(bundleDirectory, fileSystem);
    const candidatesPath = options.candidates ? assertOutsideRepository(path.resolve(options.candidates), fileSystem) : null;
    const candidatesArtifact = candidatesPath ? readCandidatesArtifact(candidatesPath, fileSystem) : null;
    const candidates = candidatesPath ? loadCandidatesForRun(candidatesPath, { fileSystem }) : [];

    const repositoryRoot = fileSystem.realpathSync(path.resolve(__dirname, '../../..'));
    const allObservations = [];
    const createdDirectories = [];
    const receiptSources = [];
    try {
        for (const source of sources) {
            const manifest = loadManifestJson(source.manifest, source.id, fileSystem);
            const result = runOfflineStaging(
                {
                    sourcePath: source.csv,
                    manifestPath: source.manifest,
                    adapter: String(manifest.adapter || ''),
                    candidates,
                    ingestedAt: options.ingestedAt,
                },
                { fileSystem }
            );
            emitSourceResult(result, emitDirectory, source, repositoryRoot, createdDirectories, fileSystem);
            allObservations.push(
                ...result.accepted_observations,
                ...result.quarantine.map(quarantineToObservation)
            );
            receiptSources.push(buildReceiptSource(result, source));
        }

        const entries = buildPopulationEntries(allObservations);
        const receipt = stableCanonicalize({
            schema_version: RECEIPT_SCHEMA_VERSION,
            ingested_at: options.ingestedAt,
            candidates_artifact: candidatesArtifact
                ? {
                      basename: candidatesArtifact.basename,
                      raw_sha256: candidatesArtifact.raw_sha256,
                      declared_business_content_sha256: candidatesArtifact.declared_business_content_sha256,
                  }
                : null,
            sources: receiptSources,
            source_population: buildSourcePopulation(entries),
            linkage: candidatesArtifact ? classifyLinkage(entries) : null,
            boundary: {
                network: false,
                database: false,
                repository_write: false,
                default_mode: 'dry_run_no_write',
            },
        });
        fileSystem.writeFileSync(path.join(emitDirectory, 'receipt.json'), `${stableStringify(receipt)}\n`, 'utf8');
        return receipt;
    } catch (error) {
        rollbackCreatedDirectories(createdDirectories, fileSystem);
        if (error instanceof OfflineStagingError) {
            throw error;
        }
        throw new OfflineStagingError('SAFETY_ERROR', `rebuild failed and staged output was rolled back: ${error.message}`);
    }
}

function collectReceiptSourceFieldErrors(source, index) {
    const errors = [];
    for (const field of ['id', 'raw_sha256', 'repository_provenance']) {
        if (!source[field]) {
            errors.push(`receipt.sources[${index}] missing required field: ${field}`);
        }
    }
    for (const field of ['total_observations', 'accepted_count', 'quarantine_count']) {
        if (!Number.isSafeInteger(source[field]) || source[field] < 0) {
            errors.push(`receipt.sources[${index}].${field} must be a non-negative safe integer`);
        }
    }
    if (!source.quarantine_reasons || typeof source.quarantine_reasons !== 'object') {
        errors.push(`receipt.sources[${index}].quarantine_reasons must be an object`);
    }
    return errors;
}

function validateReceiptSources(sources) {
    const errors = [];
    if (!Array.isArray(sources) || sources.length === 0) {
        errors.push('receipt.sources must be a non-empty array');
        return errors;
    }
    sources.forEach((source, index) => {
        if (!source || typeof source !== 'object') {
            errors.push(`receipt.sources[${index}] must be a plain object`);
            return;
        }
        errors.push(...collectReceiptSourceFieldErrors(source, index));
    });
    return errors;
}

function validateReceiptPopulation(population) {
    const errors = [];
    if (!population || typeof population !== 'object') {
        errors.push('receipt.source_population must be a plain object');
        return errors;
    }
    if (!Number.isSafeInteger(population.unique_candidates) || population.unique_candidates < 0) {
        errors.push('receipt.source_population.unique_candidates must be a non-negative safe integer');
    }
    if (!/^[a-f0-9]{64}$/i.test(String(population.business_content_sha256 || ''))) {
        errors.push('receipt.source_population.business_content_sha256 must be a 64-character SHA-256 hex string');
    }
    return errors;
}

function validateReceiptBoundary(boundary) {
    const errors = [];
    if (!boundary || typeof boundary !== 'object') {
        errors.push('receipt.boundary must be a plain object');
        return errors;
    }
    for (const field of ['network', 'database', 'repository_write']) {
        if (boundary[field] !== false) {
            errors.push(`receipt.boundary.${field} must be false`);
        }
    }
    if (boundary.default_mode !== 'dry_run_no_write') {
        errors.push('receipt.boundary.default_mode must be dry_run_no_write');
    }
    return errors;
}

function validateRebuildReceipt(receipt) {
    if (!receipt || typeof receipt !== 'object' || Array.isArray(receipt)) {
        return { valid: false, errors: ['receipt must be a plain object'] };
    }
    const errors = [];
    if (receipt.schema_version !== RECEIPT_SCHEMA_VERSION) {
        errors.push(`unsupported receipt schema_version: ${receipt.schema_version || ''}`);
    }
    if (!isStrictAbsoluteTimestamp(receipt.ingested_at)) {
        errors.push('receipt.ingested_at must be a strict ISO-8601 timestamp');
    }
    errors.push(...validateReceiptSources(receipt.sources));
    errors.push(...validateReceiptPopulation(receipt.source_population));
    errors.push(...validateReceiptBoundary(receipt.boundary));
    return { valid: errors.length === 0, errors };
}

function main(argv = process.argv.slice(2), dependencies = {}) {
    const stdout = dependencies.stdout || (text => process.stdout.write(text));
    const stderr = dependencies.stderr || (text => process.stderr.write(text));
    try {
        const args = parseArgs(argv);
        if (args.help) {
            stdout(`${usage()}\n`);
            return EXIT_CODES.success;
        }
        const receipt = runRebuild(
            {
                bundle: args.bundle,
                candidates: args.candidates || undefined,
                emitDir: args.emitDir,
                ingestedAt: args.ingestedAt,
            },
            dependencies
        );
        stdout(`${JSON.stringify({ schema_version: receipt.schema_version, ingested_at: receipt.ingested_at, sources: receipt.sources.map(source => ({ id: source.id, total_observations: source.total_observations, accepted_count: source.accepted_count, quarantine_count: source.quarantine_count })), source_population: receipt.source_population, linkage: receipt.linkage })}\n`);
        return EXIT_CODES.success;
    } catch (error) {
        const code = error instanceof OfflineStagingError ? error.code : 'UNEXPECTED_ERROR';
        stderr(`historical odds rebuild failed: ${error.message}\n`);
        if (code === 'SAFETY_ERROR') {
            return EXIT_CODES.safety_boundary_error;
        }
        if (code === 'INPUT_ERROR') {
            return EXIT_CODES.input_error;
        }
        return EXIT_CODES.unexpected_error;
    }
}

if (require.main === module) {
    process.exitCode = main();
}

module.exports = {
    BUNDLE_SCHEMA_VERSION,
    EXIT_CODES,
    RECEIPT_SCHEMA_VERSION,
    buildPopulationEntries,
    buildSourcePopulation,
    classifyLinkage,
    compareIdentitySortKey,
    computeSourcePopulationBusinessHash,
    loadBundle,
    main,
    parseArgs,
    quarantineToObservation,
    runRebuild,
    usage,
    validateRebuildReceipt,
};
