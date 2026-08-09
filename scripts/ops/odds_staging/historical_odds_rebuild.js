#!/usr/bin/env node
'use strict';

/* eslint-disable max-lines -- 有界重建 CLI（usage/解析/发射/收据 v3 schema 验证器/出口代码）
   是单一 audit gate：全部验证路径保留在同文件以便一位评审者端到端追踪 fail-closed 行为。 */
// lifecycle: permanent；M3-R1 有界重建入口：把多个 historical_git_recovery 来源
// 一次性确定性重建为 repo-external 发射输出 + 重建收据。
//
// 两种运行模式（互斥）：
// - generic_external_bundle：从 repo-external bundle（m3-historical-odds-rebuild-bundle/v1）
//   读取 CSV + manifest（既有模式，保留；收据记录 rebuild_mode=generic_external_bundle）。
// - canonical_git_history：不要求任何预先准备的 CSV bundle —— 直接从本仓库不可变
//   Git 对象恢复三个固定来源（CANONICAL_SOURCES 的 commit+path → blob SHA →
//   核验 SHA-256/字节数/行数 → 物化到 repo 外确定性 staging 目录 → 构造 manifest →
//   复用 runOfflineStaging）。只经有界只读 git 子进程访问对象库（仅
//   rev-parse / cat-file blob / show -s；shell=false；限时/限量；剥离 GIT_* 环境变量）。
//   canonical 恢复与 output-aware 验证实现位于 sibling 模块
//   historical_odds_rebuild_canonical.js（保持本文件在 CI eslint 复杂度/行数约束内）。
//
// 设计边界（与现有 odds_staging 模块一致）：
// - 只复用 runOfflineStaging / emitDeterministicResult，不重实现任何 staging 逻辑。
// - 输入 bundle / emit-dir / candidates 都必须在 Git 仓库之外；bundle 内相对路径不得逃逸。
// - 无网络、无数据库、无仓库写入；默认模式 dry_run_no_write（只写 --emit-dir / staging）。
// - 收据（m3-historical-odds-rebuild-receipt/v2）只记录实际结果，不含任何期望计数常量
//   （38,616 / 216 / 892 / 888 / 4 均不出现）；基线对照属于审计证据而非流水线；
//   canonical 模式下 candidates artifact 绑定到 M3 冻结基线（数量 + 声明业务哈希，fail closed）。
// - 收据自带 machine-readable temporal contract（evaluation_readiness /
//   temporal_semantics），且验证器（--validate）基于实际发射输出重算每个事实：
//   任何手改收据 / 发射文件 / 变更哈希都会被拒绝（确定性一致性，非密码学真实性）。
// - 业务哈希为 M3-R1 定义组合（见 computeSourcePopulationBusinessHash）：
//   D4F 文档遗留的 07e579ed… 组合从未保留在仓库中，无法从 current main 复算，
//   因此本脚本定义并记录自己的确定性组合（计数层面与历史基线完全一致）。

const crypto = require('node:crypto');
const fs = require('node:fs');
const path = require('node:path');
const { OfflineStagingError } = require('../../../src/infrastructure/odds_staging/sourceManifest');
const {
    isStrictAbsoluteTimestamp,
    stableCanonicalize,
    stableStringify,
} = require('../../../src/infrastructure/odds_staging/contracts');
const { emitDeterministicResult, loadCandidatesForRun, runOfflineStaging } = require('../../../src/infrastructure/odds_staging/pipeline');
const { resolveProviderContractApplicable } = require('../../../src/infrastructure/odds_staging/adapters');
const { FOOTBALL_DATA_PROVIDER_CONTRACT } = require('../../../src/infrastructure/odds_staging/footballDataProviderContract');
const {
    CANONICAL_CANDIDATE_BASELINE,
    CANONICAL_GIT_REPOSITORY,
    CANONICAL_SOURCES,
    TEMPORAL_READINESS_NOT_READY,
    TEMPORAL_READINESS_READY,
    buildCanonicalSourceManifest,
    buildPopulationEntries,
    buildSourcePopulation,
    buildTemporalSemantics,
    canonicalStagingDirectory,
    classifyLinkage,
    classifyTemporalEvaluationReadiness,
    compareIdentitySortKey,
    computeEmittedDigest,
    computeObservationFacts,
    computeSourcePopulationBusinessHash,
    createBoundedGitReader,
    quarantineToObservation,
    recoverCanonicalSources,
    verifyRebuildReceiptAgainstOutput,
} = require('./historical_odds_rebuild_canonical');

const BUNDLE_SCHEMA_VERSION = 'm3-historical-odds-rebuild-bundle/v1';
// v3 (M3-R2): provider_semantic_contract、series_semantics_distribution、
// 多维度 readiness（closing_odds_semantics_ready / exact timestamp / strict
// decision-time / closing_market_benchmark_semantics_ready）加入收据 —— 结构变化，
// 因此 bump，不沿用 v2。
const RECEIPT_SCHEMA_VERSION = 'm3-historical-odds-rebuild-receipt/v3';

const EXIT_CODES = Object.freeze({
    success: 0,
    input_error: 2,
    safety_boundary_error: 3,
    unexpected_error: 5,
    validation_error: 6,
});

function usage() {
    return [
        'Usage (generic external bundle):',
        '  npm run odds:staging:rebuild -- --bundle <repo-external-bundle-dir> --emit-dir <repo-external-existing-empty-dir> --ingested-at <ISO-8601> [--candidates <local-candidates.json>]',
        '',
        'Usage (canonical git history — M3-R1 self-recovering mode):',
        '  npm run odds:staging:rebuild -- --canonical-history --emit-dir <repo-external-existing-empty-dir> --ingested-at <ISO-8601> [--candidates <frozen-m3-candidate-artifact.json>]',
        '',
        'Usage (receipt self-verification):',
        '  npm run odds:staging:rebuild -- --validate <emit-dir>',
        '',
        'Required (generic bundle mode):',
        '  --bundle <directory>      repo-external dir containing sources.json (m3-historical-odds-rebuild-bundle/v1)',
        '  --emit-dir <directory>    repo-external, existing, empty; per-source outputs + receipt.json are written here',
        '  --ingested-at <ISO-8601>  fixed ingestion timestamp for deterministic output',
        '',
        'Required (canonical mode):',
        '  --canonical-history       recover the three pinned M3-R1 sources from immutable Git objects; mutually exclusive with --bundle',
        '  --emit-dir <directory>    repo-external, existing, empty; per-source outputs + receipt.json are written here',
        '  --ingested-at <ISO-8601>  fixed ingestion timestamp for deterministic output',
        '',
        'Optional:',
        '  --candidates <file>       candidate artifact for linkage classification; in canonical mode must match the frozen M3 baseline (fail closed)',
        '  --validate <emit-dir>     re-verify an emitted rebuild: recompute every receipt fact from the emitted files (counts, population, linkage, temporal facts, canonical git contract) and reject tampered receipts (exit 6)',
        '',
        'Safety:',
        '  Bundle, candidates and emit dir must all be outside the Git repository.',
        '  Bundle-relative csv/manifest paths must stay inside the bundle directory.',
        '  Canonical mode reads the repository object store through a bounded read-only git child process',
        '  (fixed commands only: rev-parse, cat-file blob, show -s; no shell; no checkout/fetch/pull/push;',
        '  bounded timeout and output buffer; GIT_* environment variables are stripped).',
        '  No network, no database, no repository writes. Receipt contains actuals only, never hard-coded baselines.',
        '',
        'Exit codes:',
        '  0 completed; 2 manifest/input error; 3 safety boundary error; 5 unexpected error; 6 receipt verification failed.',
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
    const args = { bundle: '', candidates: '', emitDir: '', ingestedAt: '', validate: '', canonical: false, help: false };
    const mapping = { '--bundle': 'bundle', '--candidates': 'candidates', '--emit-dir': 'emitDir', '--ingested-at': 'ingestedAt', '--validate': 'validate' };
    for (let index = 0; index < argv.length; index += 1) {
        const token = String(argv[index]);
        if (token === '--help' || token === '-h') {
            args.help = true;
            continue;
        }
        if (token === '--canonical-history') {
            args.canonical = true;
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
        if (args.validate) {
            rejectValidateModeConflicts(args);
            return args;
        }
        if (args.canonical) {
            for (const field of ['emitDir', 'ingestedAt']) {
                if (!args[field]) {
                    throw new OfflineStagingError('INPUT_ERROR', `--${field} is required for --canonical-history`);
                }
            }
        } else {
            for (const field of ['bundle', 'emitDir', 'ingestedAt']) {
                if (!args[field]) {
                    throw new OfflineStagingError('INPUT_ERROR', `--${field} is required`);
                }
            }
        }
        if (!isStrictAbsoluteTimestamp(args.ingestedAt)) {
            throw new OfflineStagingError('INPUT_ERROR', 'ingested_at must be an ISO-8601 timestamp with Z or an explicit numeric offset');
        }
    }
    return args;
}

function rejectValidateModeConflicts(args) {
    if (args.canonical || args.bundle) {
        throw new OfflineStagingError('INPUT_ERROR', '--validate cannot be combined with --canonical-history or --bundle');
    }
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
    const declaredCandidateCount = Number(payload?.snapshot?.candidate_count);
    return {
        basename: path.basename(absolutePath),
        raw_sha256: sha256Buffer(buffer),
        declared_business_content_sha256: String(payload?.snapshot?.business_content_sha256 || '').trim() || null,
        declared_candidate_count: Number.isSafeInteger(declaredCandidateCount) && declaredCandidateCount >= 0 ? declaredCandidateCount : null,
        actual_candidate_count: Array.isArray(payload?.candidates) ? payload.candidates.length : null,
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

function buildReceiptSource(result, source, emitDirectory, fileSystem) {
    const manifest = result.normalized_manifest;
    return stableCanonicalize({
        id: source.id,
        raw_sha256: result.summary.raw_sha256,
        raw_size_bytes: result.summary.raw_size_bytes,
        repository_provenance: manifest.repository_provenance,
        // Emitted-consistent arithmetic: summary.total_observations counts pre-dedup
        // rows (4-row fixture -> 24) while the emitted JSONL holds accepted + quarantine
        // (18). The receipt must match what --validate recomputes from the emitted
        // files. On the real M3 data both definitions agree (38,616 + 216 = 38,832).
        total_observations: result.summary.accepted_count + result.summary.quarantine_count,
        accepted_count: result.summary.accepted_count,
        quarantine_count: result.summary.quarantine_count,
        quarantine_reasons: stableCanonicalize(countQuarantineReasons(result.quarantine)),
        // Digest over the emitted files (accepted/quarantine/summary/manifest) so
        // verification recomputes it from the emit directory: any byte-level tamper
        // of the emitted output fails the digest comparison.
        emitted_digest: computeEmittedDigest(path.join(emitDirectory, source.id), fileSystem),
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

function resolveRebuildSources(options, fileSystem, repositoryRoot, dependencies) {
    if (options.canonical) {
        const sourceSpecs = dependencies.canonicalSources || CANONICAL_SOURCES;
        const gitReader = dependencies.gitReader || createBoundedGitReader(repositoryRoot, dependencies);
        const sources = recoverCanonicalSources(options.ingestedAt, gitReader, fileSystem, sourceSpecs, repositoryRoot);
        return {
            canonical: true,
            sources,
            canonicalContract: {
                satisfied: true,
                sources: sourceSpecs.map(spec => ({
                    id: spec.id,
                    commit_sha: spec.sourceCommit,
                    blob_sha: spec.expectedBlobSha,
                    path: spec.historicalPath,
                    raw_sha256: spec.expectedSha256,
                    raw_size_bytes: spec.expectedBytes,
                    raw_row_count: spec.expectedRows,
                })),
            },
        };
    }
    const bundleDirectory = assertOutsideRepository(path.resolve(options.bundle), fileSystem);
    return { canonical: false, sources: loadBundle(bundleDirectory, fileSystem), canonicalContract: null };
}

function bindFrozenCandidatesWhenCanonical(resolved, candidatesArtifact) {
    if (resolved.canonical && candidatesArtifact) {
        bindFrozenCandidates(candidatesArtifact);
    }
}

function bindFrozenCandidates(candidatesArtifact) {
    // M3 冻结 candidate artifact 绑定：数量与声明业务哈希都必须匹配，fail closed。
    // 声明数量还必须与 artifact 内 candidates 数组的实际数量一致 —— 否则一个声明
    // 被篡改为 1140、实际数组只有少量候选的 artifact 会通过绑定而让 linkage 漂移。
    if (candidatesArtifact.declared_candidate_count !== CANONICAL_CANDIDATE_BASELINE.candidate_count) {
        throw new OfflineStagingError('INPUT_ERROR', 'canonical mode requires the frozen M3 candidate artifact: candidate count mismatch');
    }
    if (candidatesArtifact.declared_business_content_sha256 !== CANONICAL_CANDIDATE_BASELINE.business_content_sha256) {
        throw new OfflineStagingError('INPUT_ERROR', 'canonical mode requires the frozen M3 candidate artifact: business content SHA-256 mismatch');
    }
    if (candidatesArtifact.actual_candidate_count !== candidatesArtifact.declared_candidate_count) {
        throw new OfflineStagingError('INPUT_ERROR', 'canonical mode requires the frozen M3 candidate artifact: declared candidate count does not match the artifact candidates array');
    }
}

function appendContractApplicableSource(source, manifest, applicableSources) {
    if (resolveProviderContractApplicable(manifest)) {
        applicableSources.push(source.id);
    }
}

function buildCandidatesArtifactRecord(candidatesArtifact) {
    if (!candidatesArtifact) {
        return null;
    }
    return {
        basename: candidatesArtifact.basename,
        raw_sha256: candidatesArtifact.raw_sha256,
        declared_business_content_sha256: candidatesArtifact.declared_business_content_sha256,
    };
}

// dependencies.repositoryRoot lets tests point the canonical git reader at a
// fixture repository; the CLI default remains this checkout.
function resolveRepositoryRoot(dependencies, fileSystem) {
    return dependencies.repositoryRoot
        ? fileSystem.realpathSync(path.resolve(dependencies.repositoryRoot))
        : fileSystem.realpathSync(path.resolve(__dirname, '../../..'));
}

function runRebuild(options = {}, dependencies = {}) {
    const fileSystem = dependencies.fileSystem || fs;
    const canonical = Boolean(options.canonical);
    if (canonical && options.bundle) {
        throw new OfflineStagingError('INPUT_ERROR', '--canonical-history cannot be combined with --bundle');
    }
    const emitDirectory = assertOutsideRepository(path.resolve(options.emitDir), fileSystem);
    assertEmptyEmitDirectory(emitDirectory, fileSystem);

    const repositoryRoot = resolveRepositoryRoot(dependencies, fileSystem);
    const resolved = resolveRebuildSources(options, fileSystem, repositoryRoot, dependencies);
    const candidatesPath = options.candidates ? assertOutsideRepository(path.resolve(options.candidates), fileSystem) : null;
    const candidatesArtifact = candidatesPath ? readCandidatesArtifact(candidatesPath, fileSystem) : null;
    bindFrozenCandidatesWhenCanonical(resolved, candidatesArtifact);
    const candidates = candidatesPath ? loadCandidatesForRun(candidatesPath, { fileSystem }) : [];

    const allAcceptedObservations = [];
    const allQuarantineRecords = [];
    const createdDirectories = [];
    const receiptSources = [];
    // M3-R2 (Codex F-02): applicable_sources 由 ACTUAL 源 manifest 计算 —— canonical
    // 模式恒为 pinned 三源；generic 模式只有声明 provider_contract 的源才进入列表
    // （无声明 → []），绝不从发射观测倒推，也绝不无条件使用官方契约。
    const providerContractApplicableSources = [];
    try {
        for (const source of resolved.sources) {
            const manifest = loadManifestJson(source.manifest, source.id, fileSystem);
            appendContractApplicableSource(source, manifest, providerContractApplicableSources);
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
            allAcceptedObservations.push(...result.accepted_observations);
            allQuarantineRecords.push(...result.quarantine);
            receiptSources.push(buildReceiptSource(result, source, emitDirectory, fileSystem));
        }

        const entries = buildPopulationEntries([
            ...allAcceptedObservations,
            ...allQuarantineRecords.map(quarantineToObservation),
        ]);
        const observationFacts = computeObservationFacts(allAcceptedObservations, allQuarantineRecords);
        const temporalSemantics = buildTemporalSemantics(observationFacts);
        const readiness = classifyTemporalEvaluationReadiness(observationFacts, temporalSemantics);
        const rebuildMode = resolved.canonical ? 'canonical_git_history' : 'generic_external_bundle';
        const seriesSemanticsDistribution = stableCanonicalize({
            closing_observation_count: observationFacts.closing_observation_count,
            first_collection_observation_count: observationFacts.first_collection_observation_count,
            unknown_temporal_semantics_observation_count: observationFacts.unknown_temporal_semantics_observation_count,
        });
        const receipt = stableCanonicalize({
            schema_version: RECEIPT_SCHEMA_VERSION,
            rebuild_mode: rebuildMode,
            ingested_at: options.ingestedAt,
            rebuild_status: {
                source_rebuild: 'SUCCESS',
                linkage_rebuild: candidatesArtifact ? 'EXECUTED' : 'NOT_EXECUTED',
            },
            candidates_artifact: buildCandidatesArtifactRecord(candidatesArtifact),
            sources: receiptSources,
            source_population: buildSourcePopulation(entries),
            linkage: candidatesArtifact ? classifyLinkage(entries) : null,
            boundary: {
                network: false,
                database: false,
                repository_write: false,
                default_mode: 'dry_run_no_write',
            },
            canonical_source_contract: resolved.canonicalContract,
            // M3-R2: 机器可读 provider semantic contract 追溯（runtime 不联网；
            // official_source_urls 只作为 provenance metadata 存在于 committed contract）。
            provider_semantic_contract: {
                contract_id: FOOTBALL_DATA_PROVIDER_CONTRACT.contract_id,
                provider_id: FOOTBALL_DATA_PROVIDER_CONTRACT.provider_id,
                evidence_type: FOOTBALL_DATA_PROVIDER_CONTRACT.evidence_type,
                evidence_checked_at: FOOTBALL_DATA_PROVIDER_CONTRACT.evidence_checked_at,
                effective_from_season: FOOTBALL_DATA_PROVIDER_CONTRACT.effective_from_season,
                exact_observation_timestamp_available: FOOTBALL_DATA_PROVIDER_CONTRACT.exact_observation_timestamp_available,
                exact_capture_timestamp_available: FOOTBALL_DATA_PROVIDER_CONTRACT.exact_capture_timestamp_available,
                applicable_sources: resolved.canonical
                    ? resolved.canonicalContract.sources.map(source => source.id).sort()
                    : providerContractApplicableSources.sort(),
            },
            series_semantics_distribution: seriesSemanticsDistribution,
            evaluation_readiness: {
                temporal_value_evaluation: readiness.temporal_value_evaluation,
                closing_odds_semantics_ready: readiness.closing_odds_semantics_ready,
                first_collection_semantics_ready: readiness.first_collection_semantics_ready,
                exact_observation_timestamp_ready: readiness.exact_observation_timestamp_ready,
                exact_capture_timestamp_ready: readiness.exact_capture_timestamp_ready,
                strict_decision_time_value_evaluation_ready: readiness.strict_decision_time_value_evaluation_ready,
                closing_market_benchmark_semantics_ready: readiness.closing_market_benchmark_semantics_ready,
                reasons: readiness.reasons,
                observation_facts: observationFacts,
            },
            temporal_semantics: temporalSemantics,
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
    // The source id is joined into the emit directory during verification: only a
    // safe path segment may be accepted (a crafted '../x' must never escape it).
    if (!/^[A-Za-z0-9][A-Za-z0-9._-]*$/.test(String(source.id || ''))) {
        errors.push(`receipt.sources[${index}].id must be a safe path segment`);
    }
    for (const field of ['raw_sha256', 'repository_provenance']) {
        if (!source[field]) {
            errors.push(`receipt.sources[${index}] missing required field: ${field}`);
        }
    }
    for (const field of ['total_observations', 'accepted_count', 'quarantine_count']) {
        if (!Number.isSafeInteger(source[field]) || source[field] < 0) {
            errors.push(`receipt.sources[${index}].${field} must be a non-negative safe integer`);
        }
    }
    if (!/^[a-f0-9]{64}$/i.test(String(source.emitted_digest || ''))) {
        errors.push(`receipt.sources[${index}].emitted_digest must be a 64-character SHA-256 hex string`);
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

function validateReceiptObservationFacts(facts) {
    const errors = [];
    for (const field of ['observation_count', 'accepted_count', 'quarantine_count', 'snapshot_type_unknown_count', 'known_snapshot_type_count', 'known_source_observed_at_count', 'known_captured_at_count', 'capture_time_status_unknown_count', 'closing_observation_count', 'first_collection_observation_count', 'unknown_temporal_semantics_observation_count']) {
        if (!Number.isSafeInteger(facts[field]) || facts[field] < 0) {
            errors.push(`receipt.evaluation_readiness.observation_facts.${field} must be a non-negative safe integer`);
        }
    }
    if (Number.isSafeInteger(facts.accepted_count) && Number.isSafeInteger(facts.quarantine_count) && Number.isSafeInteger(facts.observation_count) && facts.accepted_count + facts.quarantine_count !== facts.observation_count) {
        errors.push('receipt.evaluation_readiness.observation_facts: observation_count must equal accepted_count + quarantine_count');
    }
    if (Number.isSafeInteger(facts.closing_observation_count) && Number.isSafeInteger(facts.first_collection_observation_count) && Number.isSafeInteger(facts.unknown_temporal_semantics_observation_count) && Number.isSafeInteger(facts.observation_count) && facts.closing_observation_count + facts.first_collection_observation_count + facts.unknown_temporal_semantics_observation_count !== facts.observation_count) {
        errors.push('receipt.evaluation_readiness.observation_facts: closing + first_collection + unknown_temporal_semantics must equal observation_count');
    }
    return errors;
}

function validateReceiptProviderSemanticContract(contract) {
    const errors = [];
    if (!contract || typeof contract !== 'object') {
        return ['receipt.provider_semantic_contract must be a plain object'];
    }
    for (const field of ['contract_id', 'provider_id', 'evidence_type', 'evidence_checked_at', 'effective_from_season']) {
        if (typeof contract[field] !== 'string' || contract[field] === '') {
            errors.push(`receipt.provider_semantic_contract.${field} must be a non-empty string`);
        }
    }
    for (const field of ['exact_observation_timestamp_available', 'exact_capture_timestamp_available']) {
        if (contract[field] !== false) {
            errors.push(`receipt.provider_semantic_contract.${field} must be false`);
        }
    }
    if (!Array.isArray(contract.applicable_sources)) {
        errors.push('receipt.provider_semantic_contract.applicable_sources must be an array');
    } else if (contract.applicable_sources.some(source => typeof source !== 'string' || source === '')) {
        errors.push('receipt.provider_semantic_contract.applicable_sources must contain non-empty strings');
    }
    return errors;
}

function validateReceiptSeriesSemanticsDistribution(distribution) {
    const errors = [];
    if (!distribution || typeof distribution !== 'object' || Array.isArray(distribution)) {
        return ['receipt.series_semantics_distribution must be a plain object'];
    }
    for (const field of ['closing_observation_count', 'first_collection_observation_count', 'unknown_temporal_semantics_observation_count']) {
        if (!Number.isSafeInteger(distribution[field]) || distribution[field] < 0) {
            errors.push(`receipt.series_semantics_distribution.${field} must be a non-negative safe integer`);
        }
    }
    return errors;
}

const TEMPORAL_READINESS_DIMENSIONS = Object.freeze([
    'closing_odds_semantics_ready',
    'first_collection_semantics_ready',
    'exact_observation_timestamp_ready',
    'exact_capture_timestamp_ready',
    'strict_decision_time_value_evaluation_ready',
    'closing_market_benchmark_semantics_ready',
]);

function validateReceiptReadiness(evaluationReadiness) {
    const errors = [];
    if (!evaluationReadiness || typeof evaluationReadiness !== 'object') {
        return ['receipt.evaluation_readiness must be a plain object'];
    }
    const value = evaluationReadiness.temporal_value_evaluation;
    if (value !== TEMPORAL_READINESS_NOT_READY && value !== TEMPORAL_READINESS_READY) {
        errors.push(`receipt.evaluation_readiness.temporal_value_evaluation must be one of ${TEMPORAL_READINESS_NOT_READY}, ${TEMPORAL_READINESS_READY}`);
    }
    for (const field of TEMPORAL_READINESS_DIMENSIONS) {
        const dimensionValue = evaluationReadiness[field];
        if (dimensionValue !== 'YES' && dimensionValue !== 'NO') {
            errors.push(`receipt.evaluation_readiness.${field} must be one of YES, NO`);
        }
    }
    if (!Array.isArray(evaluationReadiness.reasons) || evaluationReadiness.reasons.some(reason => typeof reason !== 'string' || reason === '')) {
        errors.push('receipt.evaluation_readiness.reasons must be an array of non-empty strings');
    } else if (evaluationReadiness.reasons.length === 0 && value !== TEMPORAL_READINESS_READY) {
        errors.push('receipt.evaluation_readiness.reasons must be non-empty unless temporal_value_evaluation is READY');
    }
    const facts = evaluationReadiness.observation_facts;
    if (!facts || typeof facts !== 'object') {
        errors.push('receipt.evaluation_readiness.observation_facts must be a plain object');
        return errors;
    }
    errors.push(...validateReceiptObservationFacts(facts));
    return errors;
}

function validateReceiptSemantics(semantics) {
    const errors = [];
    if (!semantics || typeof semantics !== 'object') {
        return ['receipt.temporal_semantics must be a plain object'];
    }
    for (const field of ['snapshot_type', 'source_observed_at', 'capture_time']) {
        if (!['unknown', 'known', 'mixed'].includes(semantics[field])) {
            errors.push(`receipt.temporal_semantics.${field} must be one of unknown, known, mixed`);
        }
    }
    for (const field of ['plain_series_opening_status', 'c_series_closing_status', 'plain_series_first_collection_status']) {
        if (!['not_proven', 'proven'].includes(semantics[field])) {
            errors.push(`receipt.temporal_semantics.${field} must be one of not_proven, proven`);
        }
    }
    if (typeof semantics.provider_contract_id !== 'string' || semantics.provider_contract_id === '') {
        errors.push('receipt.temporal_semantics.provider_contract_id must be a non-empty string');
    }
    return errors;
}

function validateContractHexField(entry, index, field, pattern, label) {
    if (!pattern.test(String(entry[field] || ''))) {
        return [`receipt.canonical_source_contract.sources[${index}].${field} must be ${label}`];
    }
    return [];
}

function collectCanonicalContractEntryErrors(entry, index) {
    const errors = [];
    if (!entry || typeof entry !== 'object') {
        errors.push(`receipt.canonical_source_contract.sources[${index}] must be a plain object`);
        return errors;
    }
    if (!/^[A-Za-z0-9][A-Za-z0-9._-]*$/.test(String(entry.id || ''))) {
        errors.push(`receipt.canonical_source_contract.sources[${index}].id must be a safe path segment`);
    }
    errors.push(...validateContractHexField(entry, index, 'commit_sha', /^[a-f0-9]{40}$/i, 'a 40-character hex SHA'));
    errors.push(...validateContractHexField(entry, index, 'blob_sha', /^[a-f0-9]{40}$/i, 'a 40-character hex SHA'));
    const contractPath = String(entry.path || '');
    if (!contractPath || contractPath.startsWith('/') || contractPath.includes('..')) {
        errors.push(`receipt.canonical_source_contract.sources[${index}].path must be a repository-relative path`);
    }
    errors.push(...validateContractHexField(entry, index, 'raw_sha256', /^[a-f0-9]{64}$/i, 'a 64-character hex SHA-256'));
    for (const field of ['raw_size_bytes', 'raw_row_count']) {
        if (!Number.isSafeInteger(entry[field]) || entry[field] < 0) {
            errors.push(`receipt.canonical_source_contract.sources[${index}].${field} must be a non-negative safe integer`);
        }
    }
    return errors;
}

function validateReceiptRebuildStatus(rebuildStatus, receipt) {
    const errors = [];
    if (!rebuildStatus || typeof rebuildStatus !== 'object') {
        return ['receipt.rebuild_status must be a plain object'];
    }
    if (rebuildStatus.source_rebuild !== 'SUCCESS') {
        errors.push('receipt.rebuild_status.source_rebuild must be SUCCESS');
    }
    if (rebuildStatus.linkage_rebuild !== 'EXECUTED' && rebuildStatus.linkage_rebuild !== 'NOT_EXECUTED') {
        errors.push('receipt.rebuild_status.linkage_rebuild must be EXECUTED or NOT_EXECUTED');
    }
    // Machine-readable contract: linkage_rebuild state must match both linkage and
    // candidates_artifact presence (a receipt may not claim NOT_EXECUTED while
    // carrying linkage or a bound artifact, or vice versa).
    const linkageMissing = receipt.linkage === null || receipt.linkage === undefined;
    const artifactMissing = receipt.candidates_artifact === null || receipt.candidates_artifact === undefined;
    errors.push(...validateLinkageRebuildState(rebuildStatus.linkage_rebuild, linkageMissing, artifactMissing));
    return errors;
}

function validateLinkageRebuildState(linkageRebuild, linkageMissing, artifactMissing) {
    const errors = [];
    if (linkageRebuild === 'EXECUTED') {
        if (linkageMissing) {
            errors.push('receipt.rebuild_status.linkage_rebuild EXECUTED requires receipt.linkage');
        }
        if (artifactMissing) {
            errors.push('receipt.rebuild_status.linkage_rebuild EXECUTED requires receipt.candidates_artifact');
        }
    } else {
        if (!linkageMissing) {
            errors.push('receipt.rebuild_status.linkage_rebuild NOT_EXECUTED requires receipt.linkage to be null');
        }
        if (!artifactMissing) {
            errors.push('receipt.rebuild_status.linkage_rebuild NOT_EXECUTED requires receipt.candidates_artifact to be null');
        }
    }
    return errors;
}

function validateReceiptCanonicalContract(contract, rebuildMode) {
    const errors = [];
    if (rebuildMode !== 'canonical_git_history') {
        if (contract !== null && contract !== undefined) {
            errors.push('generic_external_bundle receipts must not carry a canonical_source_contract');
        }
        return errors;
    }
    if (!contract || typeof contract !== 'object' || contract.satisfied !== true || !Array.isArray(contract.sources) || contract.sources.length === 0) {
        errors.push('canonical_git_history receipts require a satisfied canonical_source_contract');
        return errors;
    }
    contract.sources.forEach((entry, index) => {
        errors.push(...collectCanonicalContractEntryErrors(entry, index));
    });
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
    if (receipt.rebuild_mode !== 'canonical_git_history' && receipt.rebuild_mode !== 'generic_external_bundle') {
        errors.push('receipt.rebuild_mode must be canonical_git_history or generic_external_bundle');
    }
    if (!isStrictAbsoluteTimestamp(receipt.ingested_at)) {
        errors.push('receipt.ingested_at must be a strict ISO-8601 timestamp');
    }
    errors.push(...validateReceiptSources(receipt.sources));
    errors.push(...validateReceiptPopulation(receipt.source_population));
    errors.push(...validateReceiptBoundary(receipt.boundary));
    errors.push(...validateReceiptRebuildStatus(receipt.rebuild_status, receipt));
    errors.push(...validateReceiptReadiness(receipt.evaluation_readiness));
    errors.push(...validateReceiptProviderSemanticContract(receipt.provider_semantic_contract));
    errors.push(...validateReceiptSeriesSemanticsDistribution(receipt.series_semantics_distribution));
    errors.push(...validateReceiptSemantics(receipt.temporal_semantics));
    errors.push(...validateReceiptCanonicalContract(receipt.canonical_source_contract, receipt.rebuild_mode));
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
        if (args.validate) {
            const fileSystem = dependencies.fileSystem || fs;
            const emitDirectory = assertOutsideRepository(path.resolve(args.validate), fileSystem);
            const result = verifyRebuildReceiptAgainstOutput(emitDirectory, fileSystem, {
                validateReceipt: validateRebuildReceipt,
                ...dependencies,
            });
            stdout(`${JSON.stringify(result)}\n`);
            return result.valid ? EXIT_CODES.success : EXIT_CODES.validation_error;
        }
        const receipt = runRebuild(
            {
                bundle: args.bundle || undefined,
                candidates: args.candidates || undefined,
                emitDir: args.emitDir,
                ingestedAt: args.ingestedAt,
                canonical: args.canonical,
            },
            dependencies
        );
        stdout(`${JSON.stringify({ schema_version: receipt.schema_version, rebuild_mode: receipt.rebuild_mode, ingested_at: receipt.ingested_at, sources: receipt.sources.map(source => ({ id: source.id, total_observations: source.total_observations, accepted_count: source.accepted_count, quarantine_count: source.quarantine_count })), source_population: receipt.source_population, linkage: receipt.linkage, evaluation_readiness: receipt.evaluation_readiness })}\n`);
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
    CANONICAL_CANDIDATE_BASELINE,
    CANONICAL_GIT_REPOSITORY,
    CANONICAL_SOURCES,
    EXIT_CODES,
    RECEIPT_SCHEMA_VERSION,
    TEMPORAL_READINESS_NOT_READY,
    TEMPORAL_READINESS_READY,
    buildCanonicalSourceManifest,
    buildPopulationEntries,
    buildSourcePopulation,
    canonicalStagingDirectory,
    classifyLinkage,
    classifyTemporalEvaluationReadiness,
    compareIdentitySortKey,
    computeObservationFacts,
    computeSourcePopulationBusinessHash,
    createBoundedGitReader,
    loadBundle,
    main,
    parseArgs,
    quarantineToObservation,
    recoverCanonicalSources,
    runRebuild,
    usage,
    validateRebuildReceipt,
    verifyRebuildReceiptAgainstOutput,
};
