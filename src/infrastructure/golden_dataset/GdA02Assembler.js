'use strict';

// lifecycle: permanent
// GD-A02 is a pure in-memory projection from the already authoritative GD-A01
// artifact + FotMob capture/staging contracts.  File I/O is kept at the CLI
// boundary; this module never fetches, connects to a DB, writes raw data or
// re-parses a raw/pageProps document.

const { validateObservation, validateStagingArtifact } = require('../fotmob/FotMobDetailStagingContract');
const {
    validateAssemblyArtifact,
    validateOutputFiles: validateGdA01OutputFiles,
    validateFotMobFreezeDocument,
    validateFotMobManifestRows,
    admittedIdSetHash,
    computeArtifactBusinessHash: computeGdA01BusinessHash,
    sha256Bytes,
    stableStringify,
} = require('./GdA01AssemblyContract');
const {
    ARTIFACT_KIND,
    FACTS_ASSEMBLY_SCHEMA_VERSION,
    FACTS_RECEIPT_SCHEMA_VERSION,
    FACT_TIMING,
    GdA02ContractError,
    PARSED_OUTPUT_CONTRACT_VERSION,
    SCOPE,
    SECTIONS,
    computeArtifactBusinessHash,
    computeFactsSetHash,
    computeSchemaFingerprint,
    emptyShotsOnTargetProjection,
    resultFromScores,
    validateFactsArtifact,
    validateFactsSourceIndex,
    validateTemporal,
} = require('./GdA02FactsContract');

function fail(message, code = 'GD_A02_INPUT_INVALID') {
    throw new GdA02ContractError(message, code);
}

function requireBuffer(value, label) {
    if (!Buffer.isBuffer(value)) fail(`${label} bytes are required`, 'PROVENANCE_INVALID');
}

function parseCandidateMap(upstreamArtifact) {
    return new Map(
        upstreamArtifact.rows.map(row => [
            row.canonical_match_id,
            {
                id: row.canonical_match_id,
                source_provider: 'FotMob',
                source_match_id: row.fotmob_frozen_source.fotmob_match_id,
                competition: row.competition,
                season: row.season,
                home_team: row.home_team,
                away_team: row.away_team,
                kickoff_at: row.kickoff_at,
            },
        ])
    );
}

function validateUpstream(options) {
    requireBuffer(options.gdA01ArtifactBytes, 'GD-A01 artifact');
    requireBuffer(options.gdA01ReceiptBytes, 'GD-A01 receipt');
    const upstream = validateGdA01OutputFiles(options.gdA01ArtifactBytes, options.gdA01ReceiptBytes);
    const artifact = upstream.artifact;
    const receipt = upstream.receipt;
    if (artifact.rows.length !== receipt.admitted_row_count) {
        fail('GD-A01 receipt/admitted row mismatch', 'POPULATION_MISMATCH');
    }
    if (artifact.rows.some(row => row.admission.status !== 'ADMITTED')) {
        fail('GD-A01 contains a non-admitted row in rows', 'POPULATION_MISMATCH');
    }
    if (computeGdA01BusinessHash({ ...artifact, business_content_sha256: null }) !== artifact.business_content_sha256) {
        fail('GD-A01 business identity cannot be reverified', 'BUSINESS_HASH_MISMATCH');
    }
    return upstream;
}

function validateFrozenInputs(options, upstreamArtifact) {
    if (!options.fotmobFreezeDocument || !options.fotmobManifestRows) {
        fail('frozen FotMob document and manifest rows are required', 'PROVENANCE_INVALID');
    }
    const freeze = validateFotMobFreezeDocument(options.fotmobFreezeDocument);
    requireBuffer(options.fotmobFreezeBytes, 'FotMob freeze');
    if (sha256Bytes(options.fotmobFreezeBytes) !== options.fotmobFreezeSha256) {
        fail('FotMob freeze byte hash differs from input binding', 'HASH_MISMATCH');
    }
    requireBuffer(options.fotmobManifestBytes, 'FotMob manifest');
    if (sha256Bytes(options.fotmobManifestBytes) !== freeze.manifest_sha256) {
        fail('FotMob manifest byte hash differs from frozen identity', 'HASH_MISMATCH');
    }
    const normalizedRows = validateFotMobManifestRows(
        options.fotmobManifestRows,
        freeze,
        parseCandidateMap(upstreamArtifact)
    );
    if (normalizedRows.length !== upstreamArtifact.rows.length) {
        fail('frozen manifest population differs from GD-A01 admitted population', 'POPULATION_MISMATCH');
    }
    return {
        freeze,
        manifestRows: normalizedRows,
        manifestById: new Map(normalizedRows.map(row => [row.canonical_match_id, row])),
    };
}

function validateFactInputIndex(sourceIndex, expectedIds) {
    const entries = validateFactsSourceIndex(sourceIndex);
    const expected = new Set(expectedIds);
    const seen = new Set();
    for (const entry of entries) {
        if (!expected.has(entry.canonical_match_id)) {
            fail(
                `facts source index contains an extra canonical ID ${entry.canonical_match_id}`,
                'POPULATION_MISMATCH'
            );
        }
        if (seen.has(entry.canonical_match_id)) {
            fail(`duplicate facts source index ID ${entry.canonical_match_id}`, 'POPULATION_MISMATCH');
        }
        seen.add(entry.canonical_match_id);
    }
    if (seen.size !== expected.size) {
        fail('facts source index does not conserve the GD-A01 admitted ID set', 'POPULATION_MISMATCH');
    }
    return new Map(entries.map(entry => [entry.canonical_match_id, entry]));
}

function compareExact(actual, expected, label) {
    if (actual !== expected) fail(`${label} mismatch`, 'IDENTITY_CONFLICT');
}

// eslint-disable-next-line complexity
function validateSourcePair(entry, expectedRow, frozenRow) {
    requireBuffer(entry.stagingArtifactBytes, `${expectedRow.canonical_match_id} staging artifact`);
    requireBuffer(entry.capturePayloadBytes, `${expectedRow.canonical_match_id} capture payload`);
    requireBuffer(entry.captureManifestBytes, `${expectedRow.canonical_match_id} capture manifest`);
    if (sha256Bytes(entry.stagingArtifactBytes) !== entry.index.staging_artifact_sha256) {
        fail(`${expectedRow.canonical_match_id} staging artifact file hash mismatch`, 'HASH_MISMATCH');
    }
    if (sha256Bytes(entry.capturePayloadBytes) !== entry.index.capture_payload_sha256) {
        fail(`${expectedRow.canonical_match_id} capture payload file hash mismatch`, 'HASH_MISMATCH');
    }
    if (sha256Bytes(entry.captureManifestBytes) !== entry.index.capture_manifest_file_sha256) {
        fail(`${expectedRow.canonical_match_id} capture manifest file hash mismatch`, 'HASH_MISMATCH');
    }
    const stagingValidation = validateStagingArtifact(entry.stagingArtifact);
    if (!stagingValidation.ok) {
        fail(
            `${expectedRow.canonical_match_id} staging artifact invalid: ${stagingValidation.errors.join('; ')}`,
            'STAGING_ARTIFACT_INVALID'
        );
    }
    if (
        entry.stagingArtifact.canonical_match_id !== null ||
        entry.stagingArtifact.canonical_link_status !== 'UNLINKED_NOT_ATTEMPTED'
    ) {
        fail(
            `${expectedRow.canonical_match_id} staging artifact has an unexpected canonical link`,
            'IDENTITY_CONFLICT'
        );
    }
    if (
        !['ACCEPTED_NEW', 'ACCEPTED_REPEAT_EXACT', 'ACCEPTED_REPEAT_EQUIVALENT'].includes(
            entry.stagingArtifact.import_terminal_state
        )
    ) {
        fail(`${expectedRow.canonical_match_id} staging artifact is not accepted`, 'STAGING_ARTIFACT_INVALID');
    }
    const observationValidation = validateObservation({
        payload: entry.capturePayload,
        manifest: entry.captureManifest,
        payloadBytes: entry.capturePayloadBytes,
    });
    if (!observationValidation.ok) {
        fail(
            `${expectedRow.canonical_match_id} capture pair invalid: ${observationValidation.errors.map(error => error.message || error).join('; ')}`,
            'CAPTURE_CONTRACT_INVALID'
        );
    }
    compareExact(
        entry.stagingArtifact.source_match_id,
        frozenRow.fotmob_match_id,
        `${expectedRow.canonical_match_id} staging source ID`
    );
    compareExact(
        String(entry.capturePayload.source_match_id),
        frozenRow.fotmob_match_id,
        `${expectedRow.canonical_match_id} capture source ID`
    );
    compareExact(
        String(entry.captureManifest.source_match_id),
        frozenRow.fotmob_match_id,
        `${expectedRow.canonical_match_id} capture manifest source ID`
    );
    compareExact(
        entry.stagingArtifact.stable_payload_sha256,
        entry.capturePayload.stable_payload_sha256,
        `${expectedRow.canonical_match_id} stable payload hash`
    );
    compareExact(
        entry.stagingArtifact.payload_file_sha256,
        entry.captureManifest.payload_file_sha256,
        `${expectedRow.canonical_match_id} payload provenance hash`
    );
    compareExact(
        entry.stagingArtifact.capture_manifest_sha256,
        entry.captureManifest.capture_manifest_sha256,
        `${expectedRow.canonical_match_id} capture manifest hash`
    );
    compareExact(
        entry.stagingArtifact.parser_output_contract_version,
        PARSED_OUTPUT_CONTRACT_VERSION,
        `${expectedRow.canonical_match_id} parsed output contract`
    );
    compareExact(
        entry.capturePayload.parser_output_contract_version,
        PARSED_OUTPUT_CONTRACT_VERSION,
        `${expectedRow.canonical_match_id} capture parsed output contract`
    );
    for (const [label, actual, expected] of [
        ['expected home team', entry.stagingArtifact.expected_identity.home_team, expectedRow.home_team],
        ['expected away team', entry.stagingArtifact.expected_identity.away_team, expectedRow.away_team],
        ['expected kickoff', entry.stagingArtifact.expected_identity.kickoff_at, expectedRow.kickoff_at],
        ['capture expected home team', entry.capturePayload.expected_identity.home_team, expectedRow.home_team],
        ['capture expected away team', entry.capturePayload.expected_identity.away_team, expectedRow.away_team],
        ['capture expected kickoff', entry.capturePayload.expected_identity.kickoff_at, expectedRow.kickoff_at],
        ['frozen source hash', frozenRow.raw_payload_sha256, expectedRow.fotmob_frozen_source.raw_payload_sha256],
    ]) {
        compareExact(actual, expected, `${expectedRow.canonical_match_id} ${label}`);
    }
    compareExact(
        entry.capturePayload.normalized.match_external_id,
        frozenRow.fotmob_match_id,
        `${expectedRow.canonical_match_id} normalized external ID`
    );
    if (entry.capturePayload.observed_identity.observed_match_id_conflict === true) {
        fail(`${expectedRow.canonical_match_id} capture identity conflict`, 'IDENTITY_CONFLICT');
    }
    for (const section of SECTIONS) {
        const staged = entry.stagingArtifact.sections[section] || {};
        const normalizedValue = entry.capturePayload.normalized[section] ?? null;
        if (staged.version !== (normalizedValue === null ? null : PARSED_OUTPUT_CONTRACT_VERSION)) {
            fail(`${expectedRow.canonical_match_id} ${section} version mismatch`, 'SCHEMA_MISMATCH');
        }
        if (stableStringify(staged.json) !== stableStringify(normalizedValue)) {
            fail(
                `${expectedRow.canonical_match_id} ${section} staging/capture projection mismatch`,
                'PROVENANCE_INVALID'
            );
        }
    }
    return observationValidation;
}

// eslint-disable-next-line complexity
function buildXgProjection(payload) {
    const normalized = payload.normalized || {};
    const shotmap = normalized.shotmap;
    if (!shotmap || !Array.isArray(shotmap.shots)) {
        return require('./GdA02FactsContract').emptyXgProjection();
    }
    const toTeamId = value => {
        if (Number.isSafeInteger(value) && value > 0) return value;
        if (typeof value === 'string' && /^\d+$/.test(value)) {
            const parsed = Number(value);
            if (Number.isSafeInteger(parsed) && parsed > 0) return parsed;
        }
        return null;
    };
    const homeTeamId = toTeamId(normalized.home_team && normalized.home_team.id);
    const awayTeamId = toTeamId(normalized.away_team && normalized.away_team.id);
    const sides = {
        home: { value: 0, known_shots: 0, missing_shots: 0, invalid_team: false },
        away: { value: 0, known_shots: 0, missing_shots: 0, invalid_team: false },
    };
    let shotsWithXg = 0;
    let shotsWithoutXg = 0;
    let nonOwnGoalShots = 0;
    let nonOwnGoalShotsWithXg = 0;
    for (const shot of shotmap.shots) {
        const ownGoal = shot && shot.isOwnGoal === true;
        const hasXg =
            shot &&
            typeof shot.expectedGoals === 'number' &&
            Number.isFinite(shot.expectedGoals) &&
            shot.expectedGoals >= 0 &&
            shot.expectedGoals <= 1;
        if (hasXg) shotsWithXg += 1;
        else shotsWithoutXg += 1;
        if (!ownGoal) {
            nonOwnGoalShots += 1;
            if (hasXg) nonOwnGoalShotsWithXg += 1;
        }
        const teamId = toTeamId(shot && shot.teamId);
        const side =
            teamId !== null && teamId === homeTeamId
                ? 'home'
                : teamId !== null && teamId === awayTeamId
                  ? 'away'
                  : null;
        if (!side) {
            sides.home.invalid_team = true;
            sides.away.invalid_team = true;
            continue;
        }
        if (hasXg) {
            sides[side].value += shot.expectedGoals;
            sides[side].known_shots += 1;
        } else if (!ownGoal) {
            sides[side].missing_shots += 1;
        }
    }
    const buildSide = side => {
        if (sides[side].invalid_team || (sides[side].known_shots === 0 && sides[side].missing_shots === 0)) {
            return {
                value: null,
                status: 'UNAVAILABLE',
                known_shots: sides[side].known_shots,
                missing_shots: sides[side].missing_shots,
            };
        }
        const status = sides[side].missing_shots > 0 ? 'PARTIAL' : 'COMPLETE';
        return {
            value: status === 'PARTIAL' ? null : sides[side].value,
            status,
            known_shots: sides[side].known_shots,
            missing_shots: sides[side].missing_shots,
        };
    };
    const home = buildSide('home');
    const away = buildSide('away');
    const status =
        home.status === 'COMPLETE' && away.status === 'COMPLETE' && nonOwnGoalShots === nonOwnGoalShotsWithXg
            ? 'VALID'
            : 'PARTIAL';
    return {
        status,
        source_path: 'normalized.shotmap.shots[*].expectedGoals',
        aggregation: 'sum_known_expectedGoals_by_team_id',
        total_shots: shotmap.shots.length,
        shots_with_xg: shotsWithXg,
        shots_without_xg: shotsWithoutXg,
        non_own_goal_shots: nonOwnGoalShots,
        non_own_goal_shots_with_xg: nonOwnGoalShotsWithXg,
        home,
        away,
    };
}

// The existing FotMob parser/staging authority retains the normalized shotmap.
// This projection promotes only the source's explicit boolean observation; it
// never estimates shots on target from goals or from the summary stats section.
// eslint-disable-next-line complexity -- source identity and boolean observation checks stay together.
function buildShotsOnTargetProjection(payload) {
    const normalized = payload.normalized || {};
    const shotmap = normalized.shotmap;
    if (!shotmap || !Array.isArray(shotmap.shots) || shotmap.shots.length === 0) {
        return emptyShotsOnTargetProjection();
    }
    const toTeamId = value => {
        if (Number.isSafeInteger(value) && value > 0) return value;
        if (typeof value === 'string' && /^\d+$/.test(value)) {
            const parsed = Number(value);
            if (Number.isSafeInteger(parsed) && parsed > 0) return parsed;
        }
        return null;
    };
    const homeTeamId = toTeamId(normalized.home_team && normalized.home_team.id);
    const awayTeamId = toTeamId(normalized.away_team && normalized.away_team.id);
    if (homeTeamId === null || awayTeamId === null || homeTeamId === awayTeamId) {
        return emptyShotsOnTargetProjection();
    }
    const sides = {
        home: { value: 0, known_shots: 0, missing_shots: 0 },
        away: { value: 0, known_shots: 0, missing_shots: 0 },
    };
    let shotsWithOnTarget = 0;
    let shotsWithoutOnTarget = 0;
    let invalidIdentity = false;
    for (const shot of shotmap.shots) {
        const teamId = toTeamId(shot && shot.teamId);
        const side =
            teamId !== null && teamId === homeTeamId
                ? 'home'
                : teamId !== null && teamId === awayTeamId
                  ? 'away'
                  : null;
        if (!side) {
            invalidIdentity = true;
            shotsWithoutOnTarget += 1;
            continue;
        }
        if (typeof (shot && shot.isOnTarget) !== 'boolean') {
            sides[side].missing_shots += 1;
            shotsWithoutOnTarget += 1;
            continue;
        }
        sides[side].known_shots += 1;
        shotsWithOnTarget += shot.isOnTarget ? 1 : 0;
        if (shot.isOnTarget === true) sides[side].value += 1;
    }
    const buildSide = side => {
        if (invalidIdentity || sides[side].missing_shots > 0) {
            return {
                value: null,
                status: 'PARTIAL',
                known_shots: sides[side].known_shots,
                missing_shots: sides[side].missing_shots,
            };
        }
        return {
            value: sides[side].value,
            status: 'COMPLETE',
            known_shots: sides[side].known_shots,
            missing_shots: 0,
        };
    };
    const home = buildSide('home');
    const away = buildSide('away');
    return {
        status: home.status === 'COMPLETE' && away.status === 'COMPLETE' ? 'VALID' : 'PARTIAL',
        source_path: 'normalized.shotmap.shots[*].isOnTarget',
        aggregation: 'count_true_isOnTarget_by_team_id',
        total_shots: shotmap.shots.length,
        shots_with_on_target: shotsWithOnTarget,
        shots_without_on_target: shotsWithoutOnTarget,
        home,
        away,
    };
}

function buildSectionProjection(stagingArtifact, section) {
    const source = stagingArtifact.sections[section];
    return {
        present: source.json !== null,
        version: source.version,
        coverage: stagingArtifact.coverage_record[section],
        schema_fingerprint: source.json === null ? null : computeSchemaFingerprint(source.json),
    };
}

function buildFactsRow(expectedRow, frozenRow, entry) {
    const result = resultFromScores(
        entry.capturePayload.normalized.home_team && entry.capturePayload.normalized.home_team.score,
        entry.capturePayload.normalized.away_team && entry.capturePayload.normalized.away_team.score
    );
    return {
        canonical_match_id: expectedRow.canonical_match_id,
        competition: expectedRow.competition,
        season: expectedRow.season,
        kickoff_at: expectedRow.kickoff_at,
        home_team: expectedRow.home_team,
        away_team: expectedRow.away_team,
        source_linkage: expectedRow.source_linkage,
        provenance: {
            frozen: {
                snapshot_id: frozenRow.snapshot_id,
                target_population_hash: frozenRow.target_population_hash,
                manifest_sha256: entry.freezeManifestSha256,
                fotmob_match_id: frozenRow.fotmob_match_id,
                raw_payload_sha256: frozenRow.raw_payload_sha256,
                source_artifact_class: frozenRow.source_artifact_class,
                capture_origin: frozenRow.capture_origin,
            },
            staging: {
                artifact_schema_version: entry.stagingArtifact.schema_version,
                observation_id: entry.stagingArtifact.observation_id,
                business_hash: entry.stagingArtifact.business_hash,
                artifact_integrity_sha256: entry.stagingArtifact.artifact_integrity_sha256,
                stable_payload_sha256: entry.stagingArtifact.stable_payload_sha256,
                payload_file_sha256: entry.stagingArtifact.payload_file_sha256,
                capture_manifest_sha256: entry.stagingArtifact.capture_manifest_sha256,
            },
            capture: {
                source_provider: entry.capturePayload.source_provider,
                parser_component: entry.capturePayload.parser_component,
                parser_version: entry.capturePayload.parser_version,
                parser_output_contract_version: entry.capturePayload.parser_output_contract_version,
                payload_file_sha256: entry.index.capture_payload_sha256,
                manifest_file_sha256: entry.index.capture_manifest_file_sha256,
                stable_payload_sha256: entry.capturePayload.stable_payload_sha256,
                capture_manifest_sha256: entry.captureManifest.capture_manifest_sha256,
            },
        },
        temporal_semantics: FACT_TIMING,
        facts: {
            sections: Object.fromEntries(
                SECTIONS.map(section => [section, buildSectionProjection(entry.stagingArtifact, section)])
            ),
            match_result: result,
            xg: buildXgProjection(entry.capturePayload),
            shots_on_target: buildShotsOnTargetProjection(entry.capturePayload),
        },
        admission: { status: 'ADMITTED', rejection_reason: null },
    };
}

function buildRejectedRow(expectedRow, frozenRow, error) {
    return {
        canonical_match_id: expectedRow.canonical_match_id,
        source_match_id: frozenRow.fotmob_match_id,
        admission: { status: 'REJECTED', rejection_reason: 'GD_A02_FACT_INPUT_REJECTED' },
        error_code: error.code || 'GD_A02_INPUT_INVALID',
        reason: String(error.message || error),
    };
}

function buildSourceBinding(options, upstream, frozen, sourceIndex, sourceEntries, rows) {
    return {
        gd_a01_artifact: {
            sha256: sha256Bytes(options.gdA01ArtifactBytes),
            business_hash: upstream.artifact.business_content_sha256,
        },
        gd_a01_receipt: {
            sha256: sha256Bytes(options.gdA01ReceiptBytes),
            output_business_hash: upstream.receipt.output_business_sha256,
        },
        fotmob_freeze: {
            sha256: options.fotmobFreezeSha256,
            snapshot_id: frozen.freeze.snapshot_id,
            target_population_hash: frozen.freeze.target_population_hash,
            manifest_sha256: frozen.freeze.manifest_sha256,
            raw_payload_count: frozen.freeze.raw_payload_count,
        },
        fotmob_manifest: {
            sha256: frozen.freeze.manifest_sha256,
            row_count: frozen.manifestRows.length,
        },
        fotmob_facts_source_index: {
            sha256: options.factsSourceIndexSha256,
            entry_count: sourceIndex.entries.length,
            artifact_set_sha256: computeFactsSetHash(sourceEntries, 'staging_artifact_sha256'),
            payload_set_sha256: computeFactsSetHash(sourceEntries, 'capture_payload_sha256'),
            manifest_set_sha256: computeFactsSetHash(sourceEntries, 'capture_manifest_file_sha256'),
            admitted_fact_count: rows.length,
        },
    };
}

function buildFactsAssembly(options = {}) {
    const upstream = validateUpstream(options);
    const frozen = validateFrozenInputs(options, upstream.artifact);
    const sourceIndex = options.factsSourceIndex;
    if (!sourceIndex) fail('GD-A02 facts source index is required', 'PROVENANCE_INVALID');
    requireBuffer(options.factsSourceIndexBytes, 'GD-A02 facts source index');
    if (typeof options.fotmobFreezeSha256 !== 'string' || typeof options.factsSourceIndexSha256 !== 'string') {
        fail('GD-A02 input binding hashes are required', 'PROVENANCE_INVALID');
    }
    const sourceIndexMap = validateFactInputIndex(
        sourceIndex,
        upstream.artifact.rows.map(row => row.canonical_match_id)
    );
    if (sha256Bytes(options.factsSourceIndexBytes) !== options.factsSourceIndexSha256) {
        fail('GD-A02 facts source index byte hash differs from input binding', 'HASH_MISMATCH');
    }
    const sourceEntries = [];
    const rows = [];
    const rejectedRows = [];
    const sortedUpstreamRows = [...upstream.artifact.rows].sort((a, b) =>
        a.canonical_match_id.localeCompare(b.canonical_match_id)
    );
    for (const expectedRow of sortedUpstreamRows) {
        const frozenRow = frozen.manifestById.get(expectedRow.canonical_match_id);
        const indexed = sourceIndexMap.get(expectedRow.canonical_match_id);
        if (!frozenRow || !indexed) {
            fail(`${expectedRow.canonical_match_id} lacks frozen/source evidence`, 'POPULATION_MISMATCH');
        }
        if (indexed.canonical_match_id !== expectedRow.canonical_match_id) {
            fail(`${expectedRow.canonical_match_id} source index identity mismatch`, 'IDENTITY_CONFLICT');
        }
        const entry = {
            ...indexed,
            ...options.loadedFactsByCanonicalId?.get(expectedRow.canonical_match_id),
            index: indexed,
            freezeManifestSha256: frozen.freeze.manifest_sha256,
        };
        sourceEntries.push(indexed);
        try {
            validateSourcePair(entry, expectedRow, frozenRow);
            rows.push(buildFactsRow(expectedRow, frozenRow, entry));
        } catch (error) {
            if (!(error instanceof GdA02ContractError)) throw error;
            rejectedRows.push(buildRejectedRow(expectedRow, frozenRow, error));
        }
    }
    const sourceBindings = buildSourceBinding(options, upstream, frozen, sourceIndex, sourceEntries, rows);
    const artifactWithoutHash = {
        schema_version: FACTS_ASSEMBLY_SCHEMA_VERSION,
        stage: 'GD-A02',
        artifact_kind: ARTIFACT_KIND,
        source_bindings: sourceBindings,
        temporal_semantics: FACT_TIMING,
        scope: SCOPE,
        population_accounting: {
            input_match_count: upstream.artifact.rows.length,
            admitted_count: rows.length,
            rejected_or_quarantined_count: rejectedRows.length,
            unaccounted_count: upstream.artifact.rows.length - rows.length - rejectedRows.length,
            duplicate_id_count: 0,
            extra_id_count: 0,
        },
        rows: rows.sort((a, b) => a.canonical_match_id.localeCompare(b.canonical_match_id)),
        rejected_rows: rejectedRows.sort((a, b) => a.canonical_match_id.localeCompare(b.canonical_match_id)),
    };
    const artifact = {
        ...artifactWithoutHash,
        business_content_sha256: computeArtifactBusinessHash({ ...artifactWithoutHash, business_content_sha256: null }),
    };
    validateFactsArtifact(artifact);
    const artifactBytes = Buffer.from(`${JSON.stringify(artifact)}\n`, 'utf8');
    const receiptWithoutSelfHash = {
        schema_version: FACTS_RECEIPT_SCHEMA_VERSION,
        stage: 'GD-A02',
        build_mode: 'file_first',
        code_revision: options.codeRevision,
        source_bindings: artifact.source_bindings,
        input_match_count: artifact.population_accounting.input_match_count,
        admitted_row_count: artifact.rows.length,
        rejected_row_count: artifact.rejected_rows.length,
        unaccounted_row_count: artifact.population_accounting.unaccounted_count,
        admitted_id_set_sha256: admittedIdSetHash(artifact.rows.map(row => row.canonical_match_id)),
        accounted_id_set_sha256: admittedIdSetHash(
            [...artifact.rows, ...artifact.rejected_rows].map(row => row.canonical_match_id)
        ),
        output_business_sha256: artifact.business_content_sha256,
        artifact_sha256: sha256Bytes(artifactBytes),
        temporal_semantics: FACT_TIMING,
        scope: SCOPE,
        status:
            artifact.rejected_rows.length === 0 && artifact.population_accounting.unaccounted_count === 0
                ? 'COMPLETE'
                : 'INCOMPLETE_REJECTED',
    };
    const receipt = receiptWithoutSelfHash;
    const receiptBytes = Buffer.from(`${JSON.stringify(receipt)}\n`, 'utf8');
    require('./GdA02FactsContract').validateReceiptDocument(receipt, artifactBytes, artifact);
    return { artifact, receipt, artifactBytes, receiptBytes, upstream, frozen, sourceEntries };
}

function validateFactsFiles(artifactBytes, receiptBytes, options = {}) {
    return require('./GdA02FactsContract').validateOutputFiles(artifactBytes, receiptBytes, options);
}

module.exports = {
    buildFactsAssembly,
    validateFactsFiles,
};
