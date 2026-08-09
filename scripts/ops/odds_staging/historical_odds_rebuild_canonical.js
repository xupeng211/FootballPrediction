'use strict';

// lifecycle: permanent；M3-R1 canonical 恢复 + temporal contract 辅助模块
// （historical_odds_rebuild.js 的 sibling 模块：把 canonical git 恢复、观察级
// temporal facts、fail-closed readiness classifier 与 output-aware 收据验证
// 拆出，使主入口保持在 CI eslint max-lines 800 / complexity 15 约束内）。
//
// 边界与主入口一致：
// - 只经有界只读 git 子进程访问对象库（固定命令形态，shell=false，限时/限量，
//   剥离 GIT_* 环境变量）；绝不执行用户命令、不写仓库。
// - canonical 来源身份（CANONICAL_SOURCES）是不可变 Git 对象绑定（commit+path →
//   blob SHA → SHA-256/字节数/行数），允许固定；业务结果计数从不硬编码。
// - 物化只发生在 repo 外确定性 staging 目录；reuse-if-identical，不一致 fail closed。
// - 验证器从实际发射输出重算每个收据事实（确定性一致性，非密码学真实性）。

const crypto = require('node:crypto');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { execFileSync } = require('node:child_process');
const { OfflineStagingError } = require('../../../src/infrastructure/odds_staging/sourceManifest');
const {
    buildSemanticMatchIdentity,
    isStrictAbsoluteTimestamp,
    stableCanonicalize,
    stableStringify,
} = require('../../../src/infrastructure/odds_staging/contracts');

// M3-R1 canonical source identities（来自 current main 的不可变 Git 对象，已逐一核验：
// rev-parse commit:path == expectedBlobSha，字节数与行数与历史审计证据一致）。
// 这些是来源身份不变量 —— 允许固定（mandate §8）；业务结果计数（38,832 / 892 / 888 …）
// 仍必须从实际发射数据计算，禁止硬编码。
const CANONICAL_GIT_REPOSITORY = 'xupeng211/FootballPrediction';
const CANONICAL_SOURCES = Object.freeze([
    {
        id: 'raw_odds_2223',
        historicalPath: 'data/external/odds/raw_odds_2223.csv',
        sourceCommit: '2fef3821532970654a9ad4f515de20cd479d358e',
        expectedBlobSha: 'd938f7b58fd92aafefa63effe3548afb27b17188',
        expectedSha256: 'e51361323bcdcdcec2faf8f58e7bcfc4f5b193ed6017b284c71538ed70d98ea2',
        expectedBytes: 175799,
        expectedRows: 380,
    },
    {
        id: 'raw_odds_2324',
        historicalPath: 'data/external/odds/raw_odds_2324.csv',
        sourceCommit: '2fef3821532970654a9ad4f515de20cd479d358e',
        expectedBlobSha: '5bc9399ba12ef3ca732477dc207b52ca09edd00e',
        expectedSha256: '0b669038e94bf305603d841f02006c7d35ebd41c8722c76e479f2393079b995f',
        expectedBytes: 171815,
        expectedRows: 380,
    },
    {
        id: 'real_odds_raw',
        historicalPath: 'data/real_odds_raw.csv',
        sourceCommit: 'fead3b97c669aad03449c4eed340b4a82eb0122e',
        expectedBlobSha: '97a199ffc44a030a632b06ca33f31c3b3904aa6a',
        expectedSha256: '045cb84f6a75dc947e5aa5c4170c844237c1dcd489ae3264a795f39a20114361',
        expectedBytes: 219137,
        expectedRows: 420,
    },
]);

// M3 冻结 FotMob candidate artifact 基线（canonical 模式 fail closed 绑定；generic 模式不绑定）。
const CANONICAL_CANDIDATE_BASELINE = Object.freeze({
    candidate_count: 1140,
    business_content_sha256: 'eff881728429260012b4de9f93764a08096407e06b9dffd9c9f9e2b4e0bc9d3f',
});

const TEMPORAL_READINESS_NOT_READY = 'NOT_READY_FOR_TEMPORAL_VALUE_EVALUATION';
const TEMPORAL_READINESS_READY = 'READY_FOR_TEMPORAL_VALUE_EVALUATION';

function assertFixedGitIdentity(commit, pathName) {
    if (!/^[a-f0-9]{40}$/i.test(String(commit || ''))) {
        throw new OfflineStagingError('SAFETY_ERROR', 'canonical source commit must be a 40-character hex SHA');
    }
    if (pathName && (String(pathName).startsWith('/') || String(pathName).includes('..'))) {
        throw new OfflineStagingError('SAFETY_ERROR', 'canonical source path must be a repository-relative path without ..');
    }
}

/**
 * 有界只读 git 子进程访问器。只暴露三个固定命令形态：
 * - git rev-parse <commit>:<path>       （commit+path → blob SHA 绑定）
 * - git cat-file blob <sha>             （读取不可变对象字节）
 * - git show -s --format=%cI <commit>   （提交者时间，严格 ISO-8601）
 * 所有 argv 都由本文件固定调用点构造，绝不接受用户命令；shell=false；
 * timeout / maxBuffer 有界；环境剥离全部 GIT_* 变量（GIT_DIR / GIT_WORK_TREE /
 * GIT_INDEX_FILE / GIT_OBJECT_DIRECTORY / GIT_ALTERNATE_OBJECT_DIRECTORIES /
 * GIT_CONFIG_* …），阻止环境劫持仓库解析；固定 GIT_TERMINAL_PROMPT=0 /
 * GIT_CONFIG_NOSYSTEM=1。
 */
function createBoundedGitReader(repositoryRoot, options = {}) {
    const timeoutMs = Number.isSafeInteger(options.timeoutMs) ? options.timeoutMs : 30000;
    const maxBufferBytes = Number.isSafeInteger(options.maxBufferBytes) ? options.maxBufferBytes : 32 * 1024 * 1024;
    const baseEnv = options.env || process.env;
    const env = {};
    for (const [key, value] of Object.entries(baseEnv)) {
        if (/^GIT_/i.test(key)) {
            continue;
        }
        env[key] = value;
    }
    env.GIT_TERMINAL_PROMPT = '0';
    env.GIT_CONFIG_NOSYSTEM = '1';
    env.GIT_PAGER = 'cat';
    env.LC_ALL = 'C';
    // Fail-closed no-network hardening: never lazy-fetch missing objects from a
    // promisor/partial clone and never allow any transport, even for file:// remotes.
    env.GIT_NO_LAZY_FETCH = '1';
    env.GIT_ALLOW_PROTOCOL = 'none';

    function execGit(argv, binary = false) {
        try {
            return execFileSync('git', ['-C', repositoryRoot, ...argv], {
                encoding: binary ? null : 'utf8',
                shell: false,
                timeout: timeoutMs,
                maxBuffer: maxBufferBytes,
                env,
            });
        } catch (error) {
            throw new OfflineStagingError('SAFETY_ERROR', `bounded git object access failed for ${argv[0]} ${argv[1]}: ${error.message}`);
        }
    }

    return {
        resolveBlobSha(commit, pathName) {
            assertFixedGitIdentity(commit, pathName);
            const output = String(execGit(['rev-parse', `${commit}:${pathName}`])).trim();
            if (!/^[a-f0-9]{40}$/i.test(output)) {
                throw new OfflineStagingError('SAFETY_ERROR', `git rev-parse did not resolve a blob SHA for ${commit}:${pathName}`);
            }
            return output;
        },
        readBlob(blobSha) {
            if (!/^[a-f0-9]{40}$/i.test(String(blobSha || ''))) {
                throw new OfflineStagingError('SAFETY_ERROR', 'readBlob requires a 40-character hex blob SHA');
            }
            return execGit(['cat-file', 'blob', blobSha], true);
        },
        readCommitTimestamp(commit) {
            assertFixedGitIdentity(commit, '');
            const output = String(execGit(['show', '-s', '--format=%cI', commit])).trim();
            if (!isStrictAbsoluteTimestamp(output)) {
                throw new OfflineStagingError('SAFETY_ERROR', `git show -s did not return a strict ISO-8601 commit timestamp for ${commit}`);
            }
            return output;
        },
    };
}

function canonicalStagingDirectory(ingestedAt, sourceSpecs) {
    const specFingerprint = crypto.createHash('sha256').update(stableStringify(sourceSpecs)).digest('hex').slice(0, 16);
    const seed = crypto.createHash('sha256').update(`m3-r1-canonical:${ingestedAt}:${specFingerprint}`).digest('hex').slice(0, 16);
    return path.join(os.tmpdir(), `footballprediction-m3-r1-canonical-${seed}`);
}

function assertNotInsideRepositoryPath(directory, fileSystem, repositoryRoot) {
    // The staging directory may not exist yet; containment is decided on the
    // resolved path (the repository root is realpath'd so a symlinked checkout
    // root cannot be tricked).
    const target = path.resolve(directory);
    const root = fileSystem.realpathSync(path.resolve(repositoryRoot));
    if (isInsidePath(root, target)) {
        throw new OfflineStagingError('SAFETY_ERROR', 'canonical staging directory must be outside the Git repository');
    }
}

function isInsidePath(rootPath, targetPath) {
    const relative = path.relative(rootPath, targetPath);
    return relative === '' || (!relative.startsWith(`..${path.sep}`) && relative !== '..' && !path.isAbsolute(relative));
}

function writeFileIfChanged(filePath, content, fileSystem) {
    if (fileSystem.existsSync(filePath)) {
        const existing = fileSystem.readFileSync(filePath);
        if (existing.equals(content)) {
            return;
        }
        throw new OfflineStagingError('SAFETY_ERROR', `canonical staging file already exists with different content: ${path.basename(filePath)}`);
    }
    fileSystem.writeFileSync(filePath, content);
}

function countCsvDataRows(buffer) {
    const lines = buffer.toString('utf8').split('\n');
    if (lines.length > 0 && lines[lines.length - 1] === '') {
        lines.pop();
    }
    return Math.max(0, lines.filter(line => line.trim() !== '').length - 1);
}

function buildCanonicalSourceManifest(spec, rawPath, ingestedAt, commitTimestamp, rawSizeBytes, rawSha256) {
    return {
        schema_version: 'odds-source-manifest/v1',
        source_provider: 'football-data-csv',
        acquisition_mode: 'historical_git_recovery',
        source_url: `git+repository://${CANONICAL_GIT_REPOSITORY}@${spec.sourceCommit}/${spec.historicalPath}`,
        declared_upstream_url: null,
        source_match_id: null,
        captured_at: null,
        capture_time_status: 'unknown',
        recovered_at: ingestedAt,
        source_timezone: 'unknown',
        raw_path: rawPath,
        raw_media_type: 'text/csv',
        raw_size_bytes: rawSizeBytes,
        raw_sha256: rawSha256,
        adapter: 'football-data-csv',
        adapter_version: '1.2.0',
        provenance_status: 'declared',
        upstream_provenance_status: 'unverified',
        license_status: 'unverified',
        repository_provenance: {
            repository: CANONICAL_GIT_REPOSITORY,
            commit_sha: spec.sourceCommit,
            blob_sha: spec.expectedBlobSha,
            path: spec.historicalPath,
            commit_timestamp: commitTimestamp,
        },
        kickoff_time_interpretation: {
            status: 'derived',
            timezone: 'Europe/London',
            method: 'source_local_calendar_time',
            evidence_level: 'empirical_cross_source',
            official_source_declaration: false,
            evidence_reference: 'M3-D3A-R calibration; M3_D4F_READINESS_REVIEW.md section 9A/9B Europe/London interpretation',
            allowed_competitions: ['Premier League'],
            allowed_seasons: ['2022/2023', '2023/2024', '2024/2025'],
        },
    };
}

/**
 * canonical 模式来源自恢复：CANONICAL_SOURCES（或测试注入的 fixture spec）中的
 * commit+path → blob SHA → 字节核验（SHA-256 / 字节数 / 行数）→ 物化到 repo 外
 * 确定性 staging 目录（reuse-if-identical，内容不一致则 fail closed）→ 构造与审计
 * 证据形状一致的 manifest（raw_path = 物化路径，满足 sourceManifest.js 的 realpath
 * 契约）→ 返回与 loadBundle 相同形状的 source 列表。
 * recovered_at = ingestedAt（确定性：两次独立 canonical 运行生成字节一致的输出）。
 */
function recoverCanonicalSources(ingestedAt, gitReader, fileSystem, sourceSpecs, repositoryRoot) {
    const stagingDirectory = canonicalStagingDirectory(ingestedAt, sourceSpecs);
    assertNotInsideRepositoryPath(stagingDirectory, fileSystem, repositoryRoot);
    if (!fileSystem.existsSync(stagingDirectory)) {
        fileSystem.mkdirSync(stagingDirectory, { recursive: true });
    }
    const sources = [];
    for (const spec of sourceSpecs) {
        const resolvedBlobSha = gitReader.resolveBlobSha(spec.sourceCommit, spec.historicalPath);
        if (resolvedBlobSha !== spec.expectedBlobSha) {
            throw new OfflineStagingError('SAFETY_ERROR', `canonical source ${spec.id}: resolved git blob ${resolvedBlobSha} != pinned blob ${spec.expectedBlobSha} (commit+path+blob binding violated)`);
        }
        const bytes = gitReader.readBlob(resolvedBlobSha);
        if (bytes.length !== spec.expectedBytes) {
            throw new OfflineStagingError('SAFETY_ERROR', `canonical source ${spec.id}: raw size ${bytes.length} != pinned ${spec.expectedBytes}`);
        }
        const rawSha256 = sha256Buffer(bytes);
        if (rawSha256 !== spec.expectedSha256) {
            throw new OfflineStagingError('SAFETY_ERROR', `canonical source ${spec.id}: raw SHA-256 ${rawSha256} != pinned ${spec.expectedSha256}`);
        }
        const rowCount = countCsvDataRows(bytes);
        if (rowCount !== spec.expectedRows) {
            throw new OfflineStagingError('SAFETY_ERROR', `canonical source ${spec.id}: data rows ${rowCount} != pinned ${spec.expectedRows}`);
        }
        const commitTimestamp = gitReader.readCommitTimestamp(spec.sourceCommit);
        const csvPath = path.join(stagingDirectory, `${spec.id}.csv`);
        const manifestPath = path.join(stagingDirectory, `${spec.id}.manifest.json`);
        writeFileIfChanged(csvPath, bytes, fileSystem);
        writeFileIfChanged(
            manifestPath,
            Buffer.from(`${JSON.stringify(buildCanonicalSourceManifest(spec, csvPath, ingestedAt, commitTimestamp, bytes.length, rawSha256))}\n`, 'utf8'),
            fileSystem
        );
        sources.push({ id: spec.id, csv: csvPath, manifest: manifestPath });
    }
    return sources;
}

function sha256Buffer(buffer) {
    return crypto.createHash('sha256').update(buffer).digest('hex');
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
 * reconstruct the identity-relevant observation view (same fields the audit analysis
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
    // Code-unit ordering (never localeCompare): determinism must not depend on
    // the host locale or the input order, and the receipt carries these samples.
    conflictSamples.sort((left, right) => {
        const leftKey = `${left.season}|${left.home_team}|${left.away_team}|${left.kickoff_at}|${left.method}|${left.delta_minutes}|${(left.candidate_ids || []).join('|')}`;
        const rightKey = `${right.season}|${right.home_team}|${right.away_team}|${right.kickoff_at}|${right.method}|${right.delta_minutes}|${(right.candidate_ids || []).join('|')}`;
        if (leftKey < rightKey) {
            return -1;
        }
        if (leftKey > rightKey) {
            return 1;
        }
        return 0;
    });
    return {
        classification: stableCanonicalize(classification),
        distinct_matched_fotmob_ids: matchedFotmobIds.size,
        conflict_samples: stableCanonicalize(conflictSamples),
    };
}

/**
 * Observation-level temporal facts，从 ACTUAL 发射的 observations 计算（绝非常量）。
 * Accepted observations 携带完整 observation schema；quarantine records 携带
 * quarantine schema —— 其 capture 证据位于 evidence.parsed_fields，且顶层没有
 * observation-schema 的 snapshot 字段。Fail-closed 约定：quarantine record 没有
 * 已证实的 snapshot 语义，按 snapshot_type unknown 计数（除非其 parsed fields
 * 另有陈述）。真实数据下该组合给出 38,832 / 0 / 0（全部 unknown）。
 */
function computeObservationFacts(acceptedObservations, quarantineRecords) {
    let snapshotTypeUnknownCount = 0;
    let knownSnapshotTypeCount = 0;
    let knownSourceObservedAtCount = 0;
    let knownCapturedAtCount = 0;
    let captureTimeStatusUnknownCount = 0;
    for (const observation of acceptedObservations) {
        // Fail-closed: a missing/null snapshot_type counts as unknown — it must
        // never be counted as neither known nor unknown (which would under-count
        // unknowns and let the readiness classifier be bypassed).
        if (observation.snapshot_type && observation.snapshot_type !== 'unknown') {
            knownSnapshotTypeCount += 1;
        } else {
            snapshotTypeUnknownCount += 1;
        }
        if (observation.source_observed_at) {
            knownSourceObservedAtCount += 1;
        }
        if (observation.captured_at) {
            knownCapturedAtCount += 1;
        }
        if (observation.capture_time_status === 'unknown') {
            captureTimeStatusUnknownCount += 1;
        }
    }
    for (const record of quarantineRecords) {
        const parsedFields = record.evidence?.parsed_fields || {};
        // Fail-closed: only a genuinely proven snapshot statement in the parsed
        // fields counts as known; absent or 'unknown' stays unknown.
        const parsedSnapshotType = parsedFields.snapshot_type;
        if (parsedSnapshotType && parsedSnapshotType !== 'unknown') {
            knownSnapshotTypeCount += 1;
        } else {
            snapshotTypeUnknownCount += 1;
        }
        if (parsedFields.source_observed_at) {
            knownSourceObservedAtCount += 1;
        }
        if (parsedFields.captured_at) {
            knownCapturedAtCount += 1;
        }
        if (parsedFields.capture_time_status === 'unknown') {
            captureTimeStatusUnknownCount += 1;
        }
    }
    return stableCanonicalize({
        observation_count: acceptedObservations.length + quarantineRecords.length,
        accepted_count: acceptedObservations.length,
        quarantine_count: quarantineRecords.length,
        snapshot_type_unknown_count: snapshotTypeUnknownCount,
        known_snapshot_type_count: knownSnapshotTypeCount,
        known_source_observed_at_count: knownSourceObservedAtCount,
        known_captured_at_count: knownCapturedAtCount,
        capture_time_status_unknown_count: captureTimeStatusUnknownCount,
    });
}

/**
 * 从 observation facts 推导 machine-readable temporal semantics。三个时序字段
 * 都是 facts 的纯函数：全部 unknown → 'unknown'；全部 known → 'known'；
 * 部分 known → 'mixed'。plain/C 的 opening/closing 状态是 provenance 证据的
 * 结论（当前无任何捕获契约证据，一律 not_proven），不是 facts 的函数。
 */
function buildTemporalSemantics(observationFacts) {
    return stableCanonicalize({
        snapshot_type: temporalFieldSemantics(observationFacts.known_snapshot_type_count, observationFacts.observation_count),
        source_observed_at: temporalFieldSemantics(observationFacts.known_source_observed_at_count, observationFacts.observation_count),
        capture_time: temporalFieldSemantics(observationFacts.known_captured_at_count, observationFacts.observation_count),
        plain_series_opening_status: 'not_proven',
        c_series_closing_status: 'not_proven',
    });
}

function temporalFieldSemantics(knownCount, totalCount) {
    if (knownCount === 0) {
        return 'unknown';
    }
    return knownCount === totalCount ? 'known' : 'mixed';
}

/**
 * 最小 deterministic temporal-readiness classifier（fail closed）：
 * 只有全部必要条件都满足时才可能给出 READY —— 可靠 observation 时间戳、
 * 已证实的 temporal snapshot 语义、有效的 prematch decision-time 解释
 * （plain opening / C closing 必须 proven）。当前契约任何一项都不满足，
 * 因此必然 NOT_READY；手改收据值为 READY 会被 --validate 拒绝。
 */
function classifyTemporalEvaluationReadiness(facts, semantics) {
    const reasons = [];
    if (facts.known_source_observed_at_count === 0) {
        reasons.push('reliable observation timestamp missing: no observation has a known source_observed_at');
    }
    if (facts.known_captured_at_count === 0) {
        reasons.push('capture time missing: no observation has a known captured_at');
    }
    if (facts.snapshot_type_unknown_count === facts.observation_count) {
        reasons.push('proven temporal snapshot semantics missing: snapshot_type is unknown on every observation');
    }
    if (semantics.plain_series_opening_status !== 'proven') {
        reasons.push('plain series opening status is not proven');
    }
    if (semantics.c_series_closing_status !== 'proven') {
        reasons.push('C series closing status is not proven');
    }
    return stableCanonicalize({
        temporal_value_evaluation: reasons.length === 0 ? TEMPORAL_READINESS_READY : TEMPORAL_READINESS_NOT_READY,
        reasons,
    });
}

// ---- GAP-02: output-aware receipt self-verification -------------------------

function deepStableEqual(left, right) {
    return stableStringify(left) === stableStringify(right);
}

// Fixed order of the emitted files covered by the per-source emitted_digest.
const EMITTED_DIGEST_FILES = Object.freeze([
    'accepted-observations.jsonl',
    'quarantine.jsonl',
    'summary.json',
    'source-manifest.normalized.json',
]);

/**
 * sha256 over the concatenated bytes of the four emitted files (fixed order).
 * Rebuild writes it into receipt.sources[i].emitted_digest; verification
 * recomputes it from the emit directory so ANY byte-level tamper of the emitted
 * output (counts, content, manifest, summary) fails the digest comparison.
 */
function computeEmittedDigest(sourceDirectory, fileSystem) {
    const hash = crypto.createHash('sha256');
    for (const name of EMITTED_DIGEST_FILES) {
        const filePath = path.join(sourceDirectory, name);
        if (!fileSystem.existsSync(filePath)) {
            throw new OfflineStagingError('SAFETY_ERROR', `emitted file missing for digest: ${filePath}`);
        }
        hash.update(fileSystem.readFileSync(filePath));
    }
    return hash.digest('hex');
}

function readJsonlRecords(filePath, fileSystem) {
    if (!fileSystem.existsSync(filePath)) {
        return null;
    }
    try {
        return String(fileSystem.readFileSync(filePath, 'utf8'))
            .trim()
            .split('\n')
            .filter(Boolean)
            .map(line => JSON.parse(line));
    } catch {
        return null;
    }
}

function collectSourceOutputErrors(source, emitDirectory, fileSystem) {
    const errors = [];
    const sourceDirectory = path.join(emitDirectory, source.id);
    const accepted = readJsonlRecords(path.join(sourceDirectory, 'accepted-observations.jsonl'), fileSystem);
    const quarantine = readJsonlRecords(path.join(sourceDirectory, 'quarantine.jsonl'), fileSystem);
    if (accepted === null) {
        errors.push(`source ${source.id}: missing or unparseable accepted-observations.jsonl`);
    }
    if (quarantine === null) {
        errors.push(`source ${source.id}: missing or unparseable quarantine.jsonl`);
    }
    if (accepted !== null && accepted.length !== source.accepted_count) {
        errors.push(`source ${source.id}: emitted accepted rows ${accepted.length} != receipt accepted_count ${source.accepted_count}`);
    }
    if (quarantine !== null && quarantine.length !== source.quarantine_count) {
        errors.push(`source ${source.id}: emitted quarantine rows ${quarantine.length} != receipt quarantine_count ${source.quarantine_count}`);
    }
    if (accepted !== null && quarantine !== null && accepted.length + quarantine.length !== source.total_observations) {
        errors.push(`source ${source.id}: emitted rows ${accepted.length + quarantine.length} != receipt total_observations ${source.total_observations}`);
    }
    let emittedDigest = null;
    try {
        emittedDigest = computeEmittedDigest(sourceDirectory, fileSystem);
    } catch (error) {
        errors.push(`source ${source.id}: ${error.message}`);
    }
    if (emittedDigest !== null && emittedDigest !== source.emitted_digest) {
        errors.push(`source ${source.id}: emitted output digest recomputed from the emit directory does not match the receipt`);
    }
    errors.push(...collectManifestDerivedFieldErrors(source, sourceDirectory, fileSystem, quarantine));
    return { errors, accepted, quarantine };
}

function collectManifestDerivedFieldErrors(source, sourceDirectory, fileSystem, quarantine) {
    const errors = [];
    // The receipt's manifest-derived fields (raw sha/size, provenance) and
    // quarantine reasons are pure functions of the emitted files: recompute them
    // so hand-edited receipt fields fail even when every emitted byte matches.
    const manifestPath = path.join(sourceDirectory, 'source-manifest.normalized.json');
    let emittedManifest = null;
    try {
        emittedManifest = JSON.parse(fileSystem.readFileSync(manifestPath, 'utf8'));
    } catch {
        errors.push(`source ${source.id}: missing or unparseable emitted normalized manifest`);
    }
    if (emittedManifest) {
        if (String(emittedManifest.raw_sha256 || '') !== source.raw_sha256) {
            errors.push(`source ${source.id}: receipt raw_sha256 does not match the emitted normalized manifest`);
        }
        if (emittedManifest.raw_size_bytes !== source.raw_size_bytes) {
            errors.push(`source ${source.id}: receipt raw_size_bytes does not match the emitted normalized manifest`);
        }
        if (!deepStableEqual(emittedManifest.repository_provenance, source.repository_provenance)) {
            errors.push(`source ${source.id}: receipt repository_provenance does not match the emitted normalized manifest`);
        }
    }
    const quarantineReasons = {};
    for (const record of quarantine || []) {
        for (const reason of record.reasons || []) {
            quarantineReasons[reason] = (quarantineReasons[reason] || 0) + 1;
        }
    }
    if (!deepStableEqual(stableCanonicalize(quarantineReasons), source.quarantine_reasons)) {
        errors.push(`source ${source.id}: quarantine reasons recomputed from emitted output do not match the receipt`);
    }
    return errors;
}

function collectEmitDirectoryReconciliationErrors(emitDirectory, receipt, fileSystem) {
    const errors = [];
    const declaredIds = new Set();
    for (const source of receipt.sources) {
        if (declaredIds.has(source.id)) {
            errors.push(`receipt declares source ${source.id} more than once`);
        }
        declaredIds.add(source.id);
    }
    let entries;
    try {
        entries = fileSystem.readdirSync(emitDirectory);
    } catch (error) {
        return [`unable to list the emit directory: ${error.message}`];
    }
    for (const name of entries) {
        // receipt.json is the receipt itself; every other entry must be a
        // declared per-source output directory.
        if (name !== 'receipt.json' && !declaredIds.has(name)) {
            errors.push(`emit directory contains output not declared by the receipt: ${name}`);
        }
    }
    return errors;
}

function collectPopulationAndLinkageErrors(entries, receipt) {
    const errors = [];
    const population = buildSourcePopulation(entries);
    if (population.unique_candidates !== receipt.source_population.unique_candidates) {
        errors.push(`source population candidates ${population.unique_candidates} != receipt ${receipt.source_population.unique_candidates}`);
    }
    if (population.business_content_sha256 !== receipt.source_population.business_content_sha256) {
        errors.push('source population business hash recomputed from emitted output does not match the receipt');
    }
    if (!deepStableEqual(population.per_season, receipt.source_population.per_season)) {
        errors.push('source population per-season distribution does not match the receipt');
    }
    if (population.identity_mode !== receipt.source_population.identity_mode) {
        errors.push('source population identity mode recomputed from emitted output does not match the receipt');
    }
    // Linkage presence is a derived invariant: linkage is computed exactly when a
    // candidates artifact was bound, so a receipt may not drop or invent it.
    const linkageMissing = receipt.linkage === null || receipt.linkage === undefined;
    const artifactMissing = receipt.candidates_artifact === null || receipt.candidates_artifact === undefined;
    if (linkageMissing !== artifactMissing) {
        errors.push('receipt.linkage presence must match receipt.candidates_artifact presence');
    }
    if (receipt.linkage) {
        const linkage = classifyLinkage(entries);
        if (!deepStableEqual(linkage.classification, receipt.linkage.classification)) {
            errors.push('linkage classification recomputed from emitted output does not match the receipt');
        }
        if (linkage.distinct_matched_fotmob_ids !== receipt.linkage.distinct_matched_fotmob_ids) {
            errors.push('linkage distinct matched FotMob ids do not match the receipt');
        }
        if (!deepStableEqual(linkage.conflict_samples, receipt.linkage.conflict_samples)) {
            errors.push('linkage conflict samples recomputed from emitted output do not match the receipt');
        }
    }
    return errors;
}

function collectTemporalConsistencyErrors(facts, receipt) {
    const errors = [];
    if (!deepStableEqual(facts, receipt.evaluation_readiness.observation_facts)) {
        errors.push('observation facts recomputed from emitted output do not match the receipt');
    }
    // The three timestamp/snapshot semantics fields are pure functions of the
    // facts: recompute them so hand-edited semantics (e.g. flipping snapshot_type
    // to 'known' while facts stay unknown) fail closed. plain/C opening/closing
    // statuses are provenance conclusions and are checked for fact contradictions
    // below instead.
    const derived = buildTemporalSemantics(facts);
    for (const field of ['snapshot_type', 'source_observed_at', 'capture_time']) {
        if (receipt.temporal_semantics[field] !== derived[field]) {
            errors.push(`temporal_semantics.${field} ${receipt.temporal_semantics[field]} contradicts the observation facts (recomputed ${derived[field]})`);
        }
    }
    const readiness = classifyTemporalEvaluationReadiness(facts, receipt.temporal_semantics);
    // Compare the full classifier output (value AND reasons): hand-edited reasons
    // must fail even when the declared value happens to match the classifier.
    const declaredReadiness = stableCanonicalize({
        temporal_value_evaluation: receipt.evaluation_readiness.temporal_value_evaluation,
        reasons: receipt.evaluation_readiness.reasons,
    });
    if (!deepStableEqual(readiness, declaredReadiness)) {
        errors.push('temporal evaluation readiness classifier rejects the receipt-declared readiness (fail closed)');
    }
    if (receipt.temporal_semantics.plain_series_opening_status === 'proven' && facts.known_snapshot_type_count === 0) {
        errors.push('temporal_semantics claims plain series opening proven while no observation has proven snapshot semantics (contradiction)');
    }
    if (receipt.temporal_semantics.c_series_closing_status === 'proven' && facts.known_snapshot_type_count === 0) {
        errors.push('temporal_semantics claims C series closing proven while no observation has proven snapshot semantics (contradiction)');
    }
    return errors;
}

function collectPinnedIdentityErrors(entry, pinned) {
    const errors = [];
    if (entry.commit_sha !== pinned.sourceCommit) {
        errors.push(`canonical contract source ${entry.id}: commit_sha ${entry.commit_sha} does not match the pinned identity`);
    }
    if (entry.blob_sha !== pinned.expectedBlobSha) {
        errors.push(`canonical contract source ${entry.id}: blob_sha does not match the pinned identity`);
    }
    if (entry.path !== pinned.historicalPath) {
        errors.push(`canonical contract source ${entry.id}: path does not match the pinned identity`);
    }
    if (entry.raw_sha256 !== pinned.expectedSha256) {
        errors.push(`canonical contract source ${entry.id}: raw_sha256 does not match the pinned identity`);
    }
    if (entry.raw_size_bytes !== pinned.expectedBytes) {
        errors.push(`canonical contract source ${entry.id}: raw_size_bytes does not match the pinned identity`);
    }
    if (entry.raw_row_count !== pinned.expectedRows) {
        errors.push(`canonical contract source ${entry.id}: raw_row_count does not match the pinned identity`);
    }
    return errors;
}

function collectCanonicalContractErrors(receipt, gitReader, sourceSpecs) {
    const errors = [];
    // The contract must reference exactly the pinned canonical identities
    // (commit + path + blob + hashes) — never a substituted or dropped source.
    const pinnedById = new Map(sourceSpecs.map(spec => [spec.id, spec]));
    if (receipt.canonical_source_contract.sources.length !== sourceSpecs.length) {
        errors.push(`canonical contract declares ${receipt.canonical_source_contract.sources.length} sources but ${sourceSpecs.length} are pinned`);
    }
    const seenIds = new Set();
    for (const entry of receipt.canonical_source_contract.sources) {
        const pinned = pinnedById.get(entry.id);
        if (seenIds.has(entry.id)) {
            errors.push(`canonical contract declares source ${entry.id} more than once`);
            continue;
        }
        seenIds.add(entry.id);
        if (!pinned) {
            errors.push(`canonical contract declares source ${entry.id} which is not a pinned canonical source`);
            continue;
        }
        errors.push(...collectPinnedIdentityErrors(entry, pinned));
    }
    for (const entry of receipt.canonical_source_contract.sources) {
        let resolved;
        try {
            resolved = gitReader.resolveBlobSha(entry.commit_sha, entry.path);
        } catch (error) {
            errors.push(`canonical contract source ${entry.id}: git resolution failed: ${error.message}`);
            continue;
        }
        if (resolved !== entry.blob_sha) {
            errors.push(`canonical contract source ${entry.id}: resolved git blob ${resolved} != receipt blob_sha ${entry.blob_sha}`);
            continue;
        }
        try {
            const bytes = gitReader.readBlob(resolved);
            if (sha256Buffer(bytes) !== entry.raw_sha256) {
                errors.push(`canonical contract source ${entry.id}: git object SHA-256 does not match the receipt`);
            }
            if (bytes.length !== entry.raw_size_bytes) {
                errors.push(`canonical contract source ${entry.id}: git object size ${bytes.length} != receipt raw_size_bytes ${entry.raw_size_bytes}`);
            }
            if (countCsvDataRows(bytes) !== entry.raw_row_count) {
                errors.push(`canonical contract source ${entry.id}: git object data rows do not match the receipt`);
            }
        } catch (error) {
            errors.push(`canonical contract source ${entry.id}: git object read failed: ${error.message}`);
        }
    }
    return errors;
}

/**
 * GAP-02：收据 output-aware 自验证。dependencies.validateReceipt 必须由调用方注入
 * （主入口的 validateRebuildReceipt；避免本模块与主入口循环依赖）。
 * 重算：per-source 发射计数、population、linkage、observation facts、temporal
 * readiness（fail closed）、canonical git contract（commit+path→blob→哈希/字节/行数）。
 */
function verifyRebuildReceiptAgainstOutput(emitDirectory, fileSystem, dependencies = {}) {
    const validateReceipt = dependencies.validateReceipt;
    if (typeof validateReceipt !== 'function') {
        return { valid: false, errors: ['verifyRebuildReceiptAgainstOutput requires dependencies.validateReceipt'] };
    }
    const receiptPath = path.join(emitDirectory, 'receipt.json');
    if (!fileSystem.existsSync(receiptPath)) {
        return { valid: false, errors: [`emit directory missing receipt.json: ${receiptPath}`] };
    }
    let receipt;
    try {
        receipt = JSON.parse(fileSystem.readFileSync(receiptPath, 'utf8'));
    } catch (error) {
        return { valid: false, errors: [`unable to parse receipt.json: ${error.message}`] };
    }
    const shape = validateReceipt(receipt);
    if (!shape.valid) {
        return { valid: false, errors: shape.errors };
    }

    const errors = [];
    errors.push(...collectEmitDirectoryReconciliationErrors(emitDirectory, receipt, fileSystem));
    const acceptedAll = [];
    const quarantineAll = [];
    for (const source of receipt.sources) {
        const collected = collectSourceOutputErrors(source, emitDirectory, fileSystem);
        errors.push(...collected.errors);
        if (collected.accepted !== null) {
            acceptedAll.push(...collected.accepted);
        }
        if (collected.quarantine !== null) {
            quarantineAll.push(...collected.quarantine);
        }
    }

    const entries = buildPopulationEntries([...acceptedAll, ...quarantineAll.map(quarantineToObservation)]);
    errors.push(...collectPopulationAndLinkageErrors(entries, receipt));
    const facts = computeObservationFacts(acceptedAll, quarantineAll);
    errors.push(...collectTemporalConsistencyErrors(facts, receipt));
    if (receipt.rebuild_mode === 'canonical_git_history') {
        try {
            const repositoryRoot = dependencies.repositoryRoot || path.resolve(__dirname, '../../..');
            const gitReader = dependencies.gitReader || createBoundedGitReader(repositoryRoot, dependencies);
            const sourceSpecs = dependencies.canonicalSources || CANONICAL_SOURCES;
            errors.push(...collectCanonicalContractErrors(receipt, gitReader, sourceSpecs));
        } catch (error) {
            errors.push(`canonical contract re-verification failed: ${error.message}`);
        }
    }
    return { valid: errors.length === 0, errors };
}

module.exports = {
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
    countCsvDataRows,
    createBoundedGitReader,
    quarantineToObservation,
    recoverCanonicalSources,
    verifyRebuildReceiptAgainstOutput,
};
