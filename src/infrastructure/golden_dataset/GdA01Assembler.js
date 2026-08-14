'use strict';

// lifecycle: permanent
// GD-A01 file-first assembler。输入必须由调用者显式绑定；本模块只读取冻结文件，
// 通过调用者注入的现有 M3 verifier 与 matchLinker 复核后，在用户指定的仓库外路径写出结果。

const fs = require('node:fs');
const path = require('node:path');

const {
    ASSEMBLY_SCHEMA_VERSION,
    GdA01ContractError,
    RECEIPT_SCHEMA_VERSION,
    STAGE,
    TEMPORAL_CAPABILITY,
    admittedIdSetHash,
    computeArtifactBusinessHash,
    linkageDecisionSetHash,
    observationProjection,
    observationSortKey,
    sha256Bytes,
    stableStringify,
    validateAssemblyArtifact,
    validateCanonicalCandidateDocument,
    validateFotMobFreezeDocument,
    validateFotMobManifestRows,
    validateOddsObservation,
    validateOutputFiles,
    validateProviderContractBinding,
    validateReceiptDocument,
} = require('./GdA01AssemblyContract');
const { decideMatchLink } = require('../odds_staging/matchLinker');

const SAFE_SOURCE_ID = /^[A-Za-z0-9][A-Za-z0-9._-]*$/;
const GIT_REVISION = /^[0-9a-f]{40}$/;

function fail(message, code = 'GD_A01_INPUT_INVALID') {
    throw new GdA01ContractError(message, code);
}

function resolvedPath(value, label) {
    if (typeof value !== 'string' || !path.isAbsolute(value)) fail(`${label} must be an absolute path`, 'PATH_INVALID');
    return path.resolve(value);
}

function assertOrdinaryFile(filePath, label, repositoryRoot, fileSystem) {
    const absolute = resolvedPath(filePath, label);
    let stat;
    let realPath;
    try {
        stat = fileSystem.lstatSync(absolute);
        realPath = fileSystem.realpathSync(absolute);
    } catch {
        fail(`${label} is unavailable`, 'INPUT_MISSING');
    }
    if (!stat.isFile() || stat.isSymbolicLink()) fail(`${label} must be an ordinary file`, 'PATH_INVALID');
    const realRepository = fileSystem.realpathSync(repositoryRoot);
    const relative = path.relative(realRepository, realPath);
    if (relative === '' || (!relative.startsWith(`..${path.sep}`) && relative !== '..' && !path.isAbsolute(relative))) {
        fail(`${label} must be repository-external`, 'SAFETY_BOUNDARY');
    }
    const before = fileSystem.lstatSync(realPath);
    const bytes = fileSystem.readFileSync(realPath);
    const after = fileSystem.lstatSync(realPath);
    if (
        before.dev !== after.dev ||
        before.ino !== after.ino ||
        before.size !== after.size ||
        before.mtimeMs !== after.mtimeMs
    ) {
        fail(`${label} changed while being read`, 'INPUT_MUTATED');
    }
    return { path: realPath, bytes, sha256: sha256Bytes(bytes), byteSize: bytes.length };
}

function assertOrdinaryDirectory(directoryPath, label, repositoryRoot, fileSystem) {
    const absolute = resolvedPath(directoryPath, label);
    let stat;
    let realPath;
    try {
        stat = fileSystem.lstatSync(absolute);
        realPath = fileSystem.realpathSync(absolute);
    } catch {
        fail(`${label} is unavailable`, 'INPUT_MISSING');
    }
    if (!stat.isDirectory() || stat.isSymbolicLink()) fail(`${label} must be an ordinary directory`, 'PATH_INVALID');
    const realRepository = fileSystem.realpathSync(repositoryRoot);
    const relative = path.relative(realRepository, realPath);
    if (relative === '' || (!relative.startsWith(`..${path.sep}`) && relative !== '..' && !path.isAbsolute(relative))) {
        fail(`${label} must be repository-external`, 'SAFETY_BOUNDARY');
    }
    return realPath;
}

function parseJson(binding, label) {
    try {
        return JSON.parse(binding.bytes.toString('utf8'));
    } catch {
        fail(`${label} is not valid JSON`, 'SCHEMA_MISMATCH');
    }
}

function parseJsonLines(binding, label) {
    const text = binding.bytes.toString('utf8');
    const lines = text.split('\n');
    if (lines.length > 0 && lines[lines.length - 1] === '') lines.pop();
    const rows = [];
    lines.forEach((line, index) => {
        if (line.trim() === '') fail(`${label} contains a blank line`, 'SCHEMA_MISMATCH');
        try {
            rows.push(JSON.parse(line));
        } catch {
            fail(`${label} contains invalid JSON at line ${index + 1}`, 'SCHEMA_MISMATCH');
        }
    });
    return rows;
}

function readFotMobInput(options, repositoryRoot, fileSystem) {
    const candidateBinding = assertOrdinaryFile(options.spinePath, 'canonical spine', repositoryRoot, fileSystem);
    const candidateDocument = parseJson(candidateBinding, 'canonical spine');
    const candidateContract = validateCanonicalCandidateDocument(candidateDocument);

    const freezeBinding = assertOrdinaryFile(options.fotmobFreezePath, 'FotMob freeze', repositoryRoot, fileSystem);
    const freezeDocument = validateFotMobFreezeDocument(parseJson(freezeBinding, 'FotMob freeze'));

    const manifestBinding = assertOrdinaryFile(
        options.fotmobManifestPath,
        'FotMob asset manifest',
        repositoryRoot,
        fileSystem
    );
    if (manifestBinding.sha256 !== freezeDocument.manifest_sha256) {
        fail('FotMob asset manifest SHA-256 differs from frozen identity', 'MANIFEST_HASH_MISMATCH');
    }
    const manifestRows = validateFotMobManifestRows(
        parseJsonLines(manifestBinding, 'FotMob asset manifest'),
        freezeDocument,
        candidateContract.byId
    );
    const frozenIds = new Set(manifestRows.map(row => row.canonical_match_id));
    if (frozenIds.size !== freezeDocument.raw_payload_count) {
        fail('FotMob frozen ID set is not unique', 'POPULATION_MISMATCH');
    }
    return {
        candidateBinding,
        candidateContract,
        freezeBinding,
        freezeDocument,
        manifestBinding,
        manifestRows,
        manifestById: new Map(manifestRows.map(row => [row.canonical_match_id, row])),
        frozenIds,
    };
}

function classificationCount(classification, prefix) {
    return Object.entries(classification || {})
        .filter(([key]) => key.startsWith(prefix))
        .reduce((total, [, count]) => total + Number(count || 0), 0);
}

function sourceBindingFromReceipt(source) {
    const provenance = source.repository_provenance || {};
    return {
        id: source.id,
        raw_sha256: source.raw_sha256,
        raw_size_bytes: source.raw_size_bytes,
        accepted_count: source.accepted_count,
        quarantine_count: source.quarantine_count,
        emitted_digest: source.emitted_digest,
        repository_provenance: {
            repository: provenance.repository || null,
            commit_sha: provenance.commit_sha || null,
            blob_sha: provenance.blob_sha || null,
            path: provenance.path || null,
        },
    };
}

function validateSourceDirectoryLayout(root, receipt, fileSystem) {
    const expected = new Set(['receipt.json', ...(receipt.sources || []).map(source => source.id)]);
    const entries = fileSystem.readdirSync(root);
    for (const entry of entries) {
        if (!expected.has(entry)) {
            fail('historical odds emit root contains an unexpected source identity', 'UNEXPECTED_SOURCE');
        }
    }
    if (entries.length !== expected.size) {
        fail('historical odds emit root is missing a source identity', 'UNEXPECTED_SOURCE');
    }
    for (const source of receipt.sources || []) {
        if (typeof source.id !== 'string' || !SAFE_SOURCE_ID.test(source.id)) {
            fail('historical odds receipt source ID is unsafe', 'UNEXPECTED_SOURCE');
        }
        const sourcePath = path.join(root, source.id);
        let stat;
        try {
            stat = fileSystem.lstatSync(sourcePath);
        } catch {
            fail('historical odds source directory is missing', 'UNEXPECTED_SOURCE');
        }
        if (!stat.isDirectory() || stat.isSymbolicLink()) {
            fail('historical odds source directory must be ordinary', 'PATH_INVALID');
        }
    }
}

function readOddsInput(options, repositoryRoot, fileSystem, candidateContract, historicalOddsVerifier) {
    if (
        !historicalOddsVerifier ||
        typeof historicalOddsVerifier.validateRebuildReceipt !== 'function' ||
        typeof historicalOddsVerifier.verifyRebuildReceiptAgainstOutput !== 'function'
    ) {
        fail('GD-A01 requires the existing M3 historical odds verifier', 'DEPENDENCY_INVALID');
    }
    const { validateRebuildReceipt, verifyRebuildReceiptAgainstOutput } = historicalOddsVerifier;
    const oddsRoot = assertOrdinaryDirectory(
        options.oddsRootPath,
        'historical odds emit root',
        repositoryRoot,
        fileSystem
    );
    const receiptBinding = assertOrdinaryFile(
        path.join(oddsRoot, 'receipt.json'),
        'historical odds receipt',
        repositoryRoot,
        fileSystem
    );
    const receipt = parseJson(receiptBinding, 'historical odds receipt');
    const receiptShape = validateRebuildReceipt(receipt);
    if (!receiptShape.valid) fail('historical odds receipt shape validation failed', 'ODDS_RECEIPT_INVALID');
    const verifier = verifyRebuildReceiptAgainstOutput(oddsRoot, fileSystem, {
        repositoryRoot,
        validateReceipt: validateRebuildReceipt,
    });
    if (!verifier.valid) fail('historical odds receipt/output verification failed', 'ODDS_RECEIPT_INVALID');
    const providerBinding = validateProviderContractBinding(receipt);
    validateSourceDirectoryLayout(oddsRoot, receipt, fileSystem);

    const observations = [];
    const observationKeys = new Set();
    for (const source of receipt.sources) {
        const acceptedBinding = assertOrdinaryFile(
            path.join(oddsRoot, source.id, 'accepted-observations.jsonl'),
            `historical odds accepted observations ${source.id}`,
            repositoryRoot,
            fileSystem
        );
        const sourceRows = parseJsonLines(acceptedBinding, `historical odds accepted observations ${source.id}`);
        if (sourceRows.length !== source.accepted_count) {
            fail(`historical odds accepted count mismatch for ${source.id}`, 'POPULATION_MISMATCH');
        }
        sourceRows.forEach((rawObservation, index) => {
            const observation = validateOddsObservation(rawObservation, `${source.id} observation ${index}`);
            if (observation.raw_sha256 !== source.raw_sha256) {
                fail(`historical odds raw hash mismatch for ${source.id}`, 'INPUT_HASH_MISMATCH');
            }
            const key = `${source.id}|${observation.raw_record_locator}|${observation.idempotency_key}`;
            if (observationKeys.has(key)) {
                fail('historical odds contain duplicate source observation identity', 'DUPLICATE_SOURCE_IDENTITY');
            }
            observationKeys.add(key);
            observations.push({ ...observation, source_id: source.id });
        });
    }
    if (observations.length !== receipt.evaluation_readiness.observation_facts.accepted_count) {
        fail('historical odds accepted observations disagree with receipt facts', 'POPULATION_MISMATCH');
    }
    return {
        root: oddsRoot,
        receiptBinding,
        receipt,
        providerBinding,
        sources: receipt.sources.map(sourceBindingFromReceipt).sort((left, right) => left.id.localeCompare(right.id)),
        observations,
        businessHash: receipt.source_population.business_content_sha256,
    };
}

function observationGroupKey(observation) {
    return [observation.season, observation.kickoff_at, observation.home_team, observation.away_team].join('\u0000');
}

function assertEmbeddedLink(observation, decision) {
    if (
        observation.match_link.status !== decision.status ||
        observation.match_link.method !== decision.method ||
        observation.match_link.matched_id !== decision.matched_id ||
        stableStringify(observation.match_link.candidate_ids) !== stableStringify(decision.candidate_ids)
    ) {
        fail('historical odds embedded link differs from the existing matchLinker decision', 'LINKAGE_CONFLICT');
    }
}

function linkAcceptedObservations(observations, candidates) {
    const groups = new Map();
    for (const observation of observations) {
        const key = observationGroupKey(observation);
        const group = groups.get(key) || [];
        group.push(observation);
        groups.set(key, group);
    }
    const byCanonicalId = new Map();
    for (const group of groups.values()) {
        const decision = decideMatchLink(group[0], candidates);
        if (decision.status !== 'matched' || decision.method !== 'exact_home_away_kickoff' || !decision.matched_id) {
            fail('historical odds group did not receive an exact unique canonical link', 'LINKAGE_NOT_EXACT');
        }
        for (const observation of group) assertEmbeddedLink(observation, decision);
        const existing = byCanonicalId.get(decision.matched_id);
        if (existing) {
            if (existing.decision.matched_id !== decision.matched_id) {
                fail('canonical linkage has conflicting decisions', 'LINKAGE_CONFLICT');
            }
            existing.observations.push(...group);
        } else {
            byCanonicalId.set(decision.matched_id, { decision, observations: [...group] });
        }
    }
    return byCanonicalId;
}

function buildRow(candidate, frozen, linked) {
    const observations = linked.observations
        .map(observation => observationProjection(observation, observation.source_id))
        .sort((left, right) => observationSortKey(left).localeCompare(observationSortKey(right)));
    const sourceIds = [...new Set(observations.map(observation => observation.source_id))].sort();
    const sourceRawHashes = [...new Set(observations.map(observation => observation.raw_sha256))].sort();
    return {
        canonical_match_id: candidate.id,
        competition: candidate.competition,
        season: candidate.season,
        kickoff_at: candidate.kickoff_at,
        home_team: candidate.home_team,
        away_team: candidate.away_team,
        source_linkage: {
            authority: 'src/infrastructure/odds_staging/matchLinker.js',
            status: linked.decision.status,
            method: linked.decision.method,
            candidate_ids: linked.decision.candidate_ids,
            matched_id: linked.decision.matched_id,
        },
        fotmob_frozen_source: {
            snapshot_id: frozen.snapshot_id,
            target_population_hash: frozen.target_population_hash,
            manifest_sha256: frozen.manifest_sha256,
            canonical_match_id: frozen.canonical_match_id,
            fotmob_match_id: frozen.fotmob_match_id,
            raw_payload_sha256: frozen.raw_payload_sha256,
            capture_semantics: 'POSTMATCH_ONLY',
            capture_timestamp: 'UNPROVEN',
        },
        football_data: {
            source_ids: sourceIds,
            source_raw_sha256: sourceRawHashes,
            observation_count: observations.length,
            observations,
        },
        admission: {
            status: 'ADMITTED',
            rejection_reason: null,
        },
    };
}

function buildRejectedRows(candidates, frozenIds) {
    return candidates
        .filter(candidate => !frozenIds.has(candidate.id))
        .map(candidate => ({
            canonical_match_id: candidate.id,
            source_provider: candidate.source_provider,
            source_match_id: candidate.source_match_id,
            competition: candidate.competition,
            season: candidate.season,
            kickoff_at: candidate.kickoff_at,
            home_team: candidate.home_team,
            away_team: candidate.away_team,
            admission: {
                status: 'REJECTED',
                rejection_reason: 'NOT_IN_FROZEN_FOTMOB_POPULATION',
            },
        }))
        .sort((left, right) => left.canonical_match_id.localeCompare(right.canonical_match_id));
}

function buildSourceBindings(input, odds, rows, codeRevision) {
    const admittedIds = rows.map(row => row.canonical_match_id);
    const linkageHash = linkageDecisionSetHash(rows);
    const classification = odds.receipt.linkage.classification || {};
    const sourceCandidateUnmatched = classificationCount(classification, 'unmatched/');
    const sourceCandidateAmbiguous = classificationCount(classification, 'ambiguous/');
    return {
        canonical_candidate_artifact: {
            schema_version: 'candidate-match-identity/v1',
            sha256: input.candidateBinding.sha256,
            byte_size: input.candidateBinding.byteSize,
            candidate_count: input.candidateContract.candidates.length,
            business_hash: input.candidateContract.businessHash,
            admitted_id_set_sha256: admittedIdSetHash(admittedIds),
        },
        fotmob_frozen_asset: {
            schema_version: input.freezeDocument.schema,
            freeze_sha256: input.freezeBinding.sha256,
            snapshot_id: input.freezeDocument.snapshot_id,
            target_population_hash: input.freezeDocument.target_population_hash,
            manifest_sha256: input.manifestBinding.sha256,
            raw_payload_count: input.freezeDocument.raw_payload_count,
            admitted_id_set_sha256: admittedIdSetHash(admittedIds),
        },
        football_data_historical_odds: {
            receipt_schema_version: odds.receipt.schema_version,
            receipt_sha256: odds.receiptBinding.sha256,
            business_hash: odds.businessHash,
            source_candidate_population: odds.receipt.source_population.unique_candidates,
            accepted_observation_count: odds.receipt.evaluation_readiness.observation_facts.accepted_count,
            quarantine_observation_count: odds.receipt.evaluation_readiness.observation_facts.quarantine_count,
            source_candidate_exact_link_count: odds.receipt.linkage.distinct_matched_fotmob_ids,
            source_candidate_unmatched_count: sourceCandidateUnmatched,
            source_candidate_ambiguous_count: sourceCandidateAmbiguous,
            admitted_exact_link_count: rows.length,
            admitted_unmatched_count: 0,
            admitted_ambiguous_count: 0,
            sources: odds.sources,
        },
        canonical_linkage: {
            authority: 'src/infrastructure/odds_staging/matchLinker.js',
            decision_set_sha256: linkageHash,
            admitted_link_status: 'EXACT_UNIQUE_HOME_AWAY_KICKOFF',
        },
        provider_semantic_contract: {
            contract_id: odds.providerBinding.contract_id,
            provider_id: odds.providerBinding.provider_id,
            evidence_type: odds.providerBinding.evidence_type,
            effective_from_season: odds.providerBinding.effective_from_season,
            first_collection_semantics: odds.providerBinding.first_collection_semantics,
            closing_series_semantics: odds.providerBinding.closing_series_semantics,
            exact_observation_timestamp: 'UNPROVEN',
            exact_capture_timestamp: 'UNPROVEN',
        },
    };
}

function buildArtifact(input, odds, codeRevision) {
    const linkedByCanonicalId = linkAcceptedObservations(odds.observations, input.candidateContract.candidates);
    for (const canonicalId of linkedByCanonicalId.keys()) {
        if (!input.frozenIds.has(canonicalId)) {
            fail(
                'accepted odds contain a canonical identity outside the frozen FotMob population',
                'UNEXPECTED_SOURCE'
            );
        }
    }
    const rows = input.manifestRows.map(frozen => {
        const candidate = input.candidateContract.byId.get(frozen.canonical_match_id);
        const linked = linkedByCanonicalId.get(frozen.canonical_match_id);
        if (!linked) fail('frozen FotMob population has no exact admitted odds link', 'POPULATION_MISMATCH');
        return buildRow(candidate, frozen, linked);
    });
    const sourceBindings = buildSourceBindings(input, odds, rows, codeRevision);
    const artifactWithoutHash = {
        schema_version: ASSEMBLY_SCHEMA_VERSION,
        stage: STAGE,
        artifact_kind: 'spine_odds_assembly',
        source_bindings: sourceBindings,
        temporal_capability: TEMPORAL_CAPABILITY,
        rows,
        rejected_rows: buildRejectedRows(input.candidateContract.candidates, input.frozenIds),
    };
    const artifact = {
        ...artifactWithoutHash,
        business_content_sha256: computeArtifactBusinessHash({
            ...artifactWithoutHash,
            business_content_sha256: null,
        }),
    };
    validateAssemblyArtifact(artifact);
    return artifact;
}

function buildReceipt(artifact, codeRevision, expectedAdmittedRows) {
    const artifactBytes = Buffer.from(`${stableStringify(artifact)}\n`, 'utf8');
    const receipt = {
        schema_version: RECEIPT_SCHEMA_VERSION,
        stage: STAGE,
        build_mode: 'file_first',
        code_revision: codeRevision,
        source_bindings: artifact.source_bindings,
        admitted_row_count: artifact.rows.length,
        rejected_row_count: artifact.rejected_rows.length,
        admitted_id_set_sha256: admittedIdSetHash(artifact.rows.map(row => row.canonical_match_id)),
        linkage_decision_set_sha256: linkageDecisionSetHash(artifact.rows),
        output_business_sha256: artifact.business_content_sha256,
        artifact_sha256: sha256Bytes(artifactBytes),
        temporal_capability: artifact.temporal_capability,
        ...(expectedAdmittedRows === undefined
            ? {}
            : {
                  population_profile: {
                      expected_admitted_rows: Number(expectedAdmittedRows),
                      expected_admitted_unmatched: 0,
                      expected_admitted_ambiguous: 0,
                  },
              }),
    };
    validateReceiptDocument(receipt, artifactBytes, artifact);
    return { artifactBytes, receiptBytes: Buffer.from(`${stableStringify(receipt)}\n`, 'utf8'), artifact, receipt };
}

function assertCodeRevision(codeRevision) {
    if (typeof codeRevision !== 'string' || !GIT_REVISION.test(codeRevision)) {
        fail('code_revision must be a full Git SHA', 'INPUT_INVALID');
    }
    return codeRevision;
}

function buildAssembly(options = {}, dependencies = {}) {
    const fileSystem = dependencies.fileSystem || fs;
    const repositoryRoot = dependencies.repositoryRoot || path.resolve(__dirname, '../../..');
    const codeRevision = assertCodeRevision(options.codeRevision);
    const historicalOddsVerifier = dependencies.historicalOddsVerifier;
    const input = readFotMobInput(options, repositoryRoot, fileSystem);
    const odds = readOddsInput(options, repositoryRoot, fileSystem, input.candidateContract, historicalOddsVerifier);
    const artifact = buildArtifact(input, odds, codeRevision);
    if (options.expectedAdmittedRows !== undefined && artifact.rows.length !== Number(options.expectedAdmittedRows)) {
        fail('GD-A01 frozen validation population does not match the explicit expected count', 'POPULATION_MISMATCH');
    }
    return buildReceipt(artifact, codeRevision, options.expectedAdmittedRows);
}

function assertOutputPath(outputPath, label, repositoryRoot, fileSystem) {
    const absolute = resolvedPath(outputPath, label);
    const parent = path.dirname(absolute);
    let parentStat;
    try {
        parentStat = fileSystem.statSync(parent);
    } catch {
        fail(`${label} parent directory is unavailable`, 'PATH_INVALID');
    }
    if (!parentStat.isDirectory()) fail(`${label} parent is not a directory`, 'PATH_INVALID');
    const realRepository = fileSystem.realpathSync(repositoryRoot);
    const realParent = fileSystem.realpathSync(parent);
    const relative = path.relative(realRepository, realParent);
    if (relative === '' || (!relative.startsWith(`..${path.sep}`) && relative !== '..' && !path.isAbsolute(relative))) {
        fail(`${label} must be repository-external`, 'SAFETY_BOUNDARY');
    }
    if (fileSystem.existsSync(absolute)) fail(`${label} already exists`, 'OUTPUT_EXISTS');
    return absolute;
}

function writeAssemblyOutputs(result, options = {}, dependencies = {}) {
    const fileSystem = dependencies.fileSystem || fs;
    const repositoryRoot = dependencies.repositoryRoot || path.resolve(__dirname, '../../..');
    const outputPath = assertOutputPath(options.outputPath, 'GD-A01 artifact output', repositoryRoot, fileSystem);
    const receiptPath = assertOutputPath(options.receiptPath, 'GD-A01 receipt output', repositoryRoot, fileSystem);
    if (outputPath === receiptPath) fail('GD-A01 artifact and receipt outputs must differ', 'PATH_INVALID');
    fileSystem.writeFileSync(outputPath, result.artifactBytes, { flag: 'wx' });
    fileSystem.writeFileSync(receiptPath, result.receiptBytes, { flag: 'wx' });
    return { outputPath, receiptPath };
}

function validateAssemblyFiles(artifactPath, receiptPath, dependencies = {}) {
    const fileSystem = dependencies.fileSystem || fs;
    const repositoryRoot = dependencies.repositoryRoot || path.resolve(__dirname, '../../..');
    const artifactBinding = assertOrdinaryFile(artifactPath, 'GD-A01 artifact', repositoryRoot, fileSystem);
    const receiptBinding = assertOrdinaryFile(receiptPath, 'GD-A01 receipt', repositoryRoot, fileSystem);
    return validateOutputFiles(artifactBinding.bytes, receiptBinding.bytes);
}

module.exports = {
    buildAssembly,
    validateAssemblyFiles,
    writeAssemblyOutputs,
};
