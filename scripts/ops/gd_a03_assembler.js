#!/usr/bin/env node
'use strict';

/* eslint-disable max-lines -- GD-A03 keeps the registry boundary validator with its file-first entrypoint. */

// lifecycle: permanent；GD-A03 file-first prior-state feature-view entrypoint。
// 所有 Golden Dataset 输入/输出均显式绑定到仓库外普通文件；不联网、不连 DB、
// 不写 raw/L3、不训练、不做 backtest。feature name/order 从仓库 config 读取。

const fs = require('node:fs');
const path = require('node:path');
const { resolveGitState } = require('../../src/infrastructure/fotmob/FotMobCandidateExporter');

const {
    validateCanonicalCandidateDocument,
    sha256Bytes,
    stableStringify,
    validateOutputFiles: validateGdA01OutputFiles,
} = require('../../src/infrastructure/golden_dataset/GdA01AssemblyContract');
const {
    validateOutputFiles: validateGdA02OutputFiles,
} = require('../../src/infrastructure/golden_dataset/GdA02FactsContract');
const { assertNoSymlinkAncestors } = require('../../src/infrastructure/fotmob/FotMobDetailCaptureContract');
const {
    FIXTURES_PER_SEASON,
    MASTER_COUNT,
    SEASONS,
} = require('../../src/infrastructure/canonical/CanonicalInventoryContract');
const {
    GdA03ContractError,
    PRIOR_STATE_ARTIFACT_SCHEMA_VERSION,
    SCHEDULE_AWAY_FIXTURES_PER_TEAM,
    SCHEDULE_FIXTURES_PER_TEAM,
    SCHEDULE_HOME_FIXTURES_PER_TEAM,
    SCHEDULE_TEAM_CLOSURE_SCHEMA_VERSION,
    SCHEDULE_TEAMS_PER_SEASON,
    computeFactRejectionBinding,
    computeFactRejectionBindingsHash,
    computeFactResultBinding,
    computeFactResultBindingsHash,
} = require('../../src/infrastructure/golden_dataset/GdA03PriorStateContract');
const { admittedIdSetHash } = require('../../src/infrastructure/golden_dataset/GdA01AssemblyContract');
const {
    buildPriorStateFeatureView,
    validatePriorStateOutputFiles,
} = require('../../src/infrastructure/golden_dataset/GdA03PriorStateAssembler');

const EXIT_CODES = Object.freeze({
    OK: 0,
    INPUT: 2,
    VALIDATION: 6,
    UNEXPECTED: 5,
});
const GIT_REVISION = /^[0-9a-f]{40}$/;

function usage() {
    return [
        'GD-A03 file-first point-in-time prior-state feature view assembler',
        '',
        'Build:',
        '  npm run gd:a03 -- build --gd-a01-artifact <abs.json> --gd-a01-receipt <abs.json>',
        '    --gd-a02-artifact <abs.json> --gd-a02-receipt <abs.json>',
        '    --schedule-artifact <abs.json> --output <abs-artifact.json>',
        '    --receipt <abs-receipt.json> --code-revision <40-hex-git-sha>',
        '    [--expected-targets <count>]',
        '',
        'Validate:',
        '  npm run gd:a03 -- validate --artifact <abs-artifact.json> --receipt <abs-receipt.json>',
        '    [--expected-targets <count>]',
        '',
        'The command is deterministic, offline, file-first, and writes only the two explicit output files.',
    ].join('\n');
}

function fail(message, code = 'GD_A03_INPUT_INVALID') {
    throw new GdA03ContractError(message, code);
}

function readValue(argv, index, option) {
    const value = argv[index + 1];
    if (!value || value.startsWith('--')) fail(`${option} requires a value`, 'INPUT_INVALID');
    return value;
}

// eslint-disable-next-line complexity -- the CLI has one explicit, auditable option parser.
function parseArgs(argv = []) {
    const command = argv[0] || 'help';
    if (command === '--help' || command === '-h' || command === 'help') return { command: 'help' };
    if (!['build', 'validate'].includes(command)) fail(`unsupported command ${command}`, 'INPUT_INVALID');
    const values = {};
    const options = new Map([
        ['--gd-a01-artifact', 'gdA01ArtifactPath'],
        ['--gd-a01-receipt', 'gdA01ReceiptPath'],
        ['--gd-a02-artifact', 'gdA02ArtifactPath'],
        ['--gd-a02-receipt', 'gdA02ReceiptPath'],
        ['--schedule-artifact', 'scheduleArtifactPath'],
        ['--output', 'outputPath'],
        ['--receipt', 'receiptPath'],
        ['--artifact', 'artifactPath'],
        ['--code-revision', 'codeRevision'],
        ['--expected-targets', 'expectedTargets'],
    ]);
    for (let index = 1; index < argv.length; index += 1) {
        const token = argv[index];
        const equalOption = [...options.keys()].find(option => token.startsWith(`${option}=`));
        if (equalOption) {
            values[options.get(equalOption)] = token.slice(equalOption.length + 1);
            continue;
        }
        const key = options.get(token);
        if (!key) fail(`unknown argument ${token}`, 'INPUT_INVALID');
        values[key] = readValue(argv, index, token);
        index += 1;
    }
    const required =
        command === 'build'
            ? [
                  'gdA01ArtifactPath',
                  'gdA01ReceiptPath',
                  'gdA02ArtifactPath',
                  'gdA02ReceiptPath',
                  'scheduleArtifactPath',
                  'outputPath',
                  'receiptPath',
                  'codeRevision',
              ]
            : ['artifactPath', 'receiptPath'];
    for (const field of required) if (!values[field]) fail(`${field} is required for ${command}`, 'INPUT_INVALID');
    if (command === 'build' && !GIT_REVISION.test(values.codeRevision)) {
        fail('--code-revision must be a full Git SHA', 'INPUT_INVALID');
    }
    if (values.expectedTargets !== undefined) {
        values.expectedTargets = Number(values.expectedTargets);
        if (!Number.isSafeInteger(values.expectedTargets) || values.expectedTargets < 1) {
            fail('--expected-targets must be a positive integer', 'INPUT_INVALID');
        }
    }
    return { command, ...values };
}

function resolvedPath(value, label) {
    if (typeof value !== 'string' || !path.isAbsolute(value)) fail(`${label} must be absolute`, 'PATH_INVALID');
    return path.resolve(value);
}

function assertExternalRegularFile(filePath, label, repositoryRoot) {
    const absolute = resolvedPath(filePath, label);
    try {
        assertNoSymlinkAncestors(absolute);
    } catch (error) {
        fail(`${label} path contains a symlink: ${error.message}`, 'PATH_INVALID');
    }
    let stat;
    let realPath;
    try {
        stat = fs.lstatSync(absolute);
        realPath = fs.realpathSync(absolute);
    } catch {
        fail(`${label} is unavailable`, 'INPUT_MISSING');
    }
    if (!stat.isFile() || stat.isSymbolicLink()) fail(`${label} must be an ordinary file`, 'PATH_INVALID');
    const repository = fs.realpathSync(repositoryRoot);
    const relative = path.relative(repository, realPath);
    if (relative === '' || (!relative.startsWith(`..${path.sep}`) && relative !== '..' && !path.isAbsolute(relative))) {
        fail(`${label} must be repository-external`, 'SAFETY_BOUNDARY');
    }
    const before = fs.lstatSync(realPath);
    const bytes = fs.readFileSync(realPath);
    const after = fs.lstatSync(realPath);
    if (
        before.dev !== after.dev ||
        before.ino !== after.ino ||
        before.size !== after.size ||
        before.mtimeMs !== after.mtimeMs
    ) {
        fail(`${label} changed while being read`, 'INPUT_MUTATED');
    }
    return { path: realPath, bytes, sha256: sha256Bytes(bytes) };
}

function assertRepositoryConfigFile(filePath, label, repositoryRoot) {
    const absolute = resolvedPath(filePath, label);
    const repository = fs.realpathSync(repositoryRoot);
    const realPath = fs.realpathSync(absolute);
    const relative = path.relative(repository, realPath);
    if (relative === '' || relative.startsWith(`..${path.sep}`) || relative === '..' || path.isAbsolute(relative)) {
        fail(`${label} must be inside the repository`, 'SAFETY_BOUNDARY');
    }
    const bytes = fs.readFileSync(realPath);
    return { path: realPath, bytes, sha256: sha256Bytes(bytes) };
}

function assertCodeRevisionMatchesHead(codeRevision, repositoryRoot) {
    let gitState;
    try {
        gitState = resolveGitState({ repositoryRoot });
    } catch (error) {
        fail(`cannot verify --code-revision against Git HEAD: ${error.message}`, 'CODE_REVISION_UNVERIFIED');
    }
    if (gitState.revision !== codeRevision) {
        fail(`--code-revision ${codeRevision} does not match Git HEAD ${gitState.revision}`, 'CODE_REVISION_MISMATCH');
    }
}

function loadRuntimeFeatureIdentity(repositoryRoot) {
    const binding = assertRepositoryConfigFile(
        path.join(repositoryRoot, 'src/ml/feature_adapters/prematch.py'),
        'V26_6_PreMatchAdapter source',
        repositoryRoot
    );
    const source = binding.bytes.toString('utf8');
    const listMatch = source.match(/V26_6_FEATURES\s*=\s*\[(?<body>[\s\S]*?)\n\s*\]/);
    if (!listMatch) fail('V26_6_PreMatchAdapter.V26_6_FEATURES declaration is missing', 'SCHEMA_MISMATCH');
    const orderedFeatures = [...listMatch.groups.body.matchAll(/['"]([^'"]+)['"]/g)].map(match => match[1]);
    if (orderedFeatures.length !== 20) {
        fail('V26_6_PreMatchAdapter.V26_6_FEATURES must contain exactly 20 names', 'SCHEMA_MISMATCH');
    }
    return { ...binding, symbol: 'V26_6_PreMatchAdapter.V26_6_FEATURES', orderedFeatures };
}

function assertOutputPath(filePath, label, repositoryRoot) {
    const absolute = resolvedPath(filePath, label);
    try {
        assertNoSymlinkAncestors(absolute);
    } catch (error) {
        fail(`${label} path contains a symlink: ${error.message}`, 'PATH_INVALID');
    }
    const parent = path.dirname(absolute);
    let parentStat;
    try {
        parentStat = fs.lstatSync(parent);
    } catch {
        fail(`${label} parent is unavailable`, 'PATH_INVALID');
    }
    if (!parentStat.isDirectory() || parentStat.isSymbolicLink()) {
        fail(`${label} parent is not an ordinary directory`, 'PATH_INVALID');
    }
    const repository = fs.realpathSync(repositoryRoot);
    const realParent = fs.realpathSync(parent);
    const relative = path.relative(repository, realParent);
    if (relative === '' || (!relative.startsWith(`..${path.sep}`) && relative !== '..' && !path.isAbsolute(relative))) {
        fail(`${label} must be repository-external`, 'SAFETY_BOUNDARY');
    }
    try {
        fs.lstatSync(absolute);
        fail(`${label} already exists`, 'OUTPUT_EXISTS');
    } catch (error) {
        if (error instanceof GdA03ContractError) throw error;
        if (error.code !== 'ENOENT') fail(`${label} cannot be checked`, 'PATH_INVALID');
    }
    return absolute;
}

function parseJson(binding, label) {
    try {
        return JSON.parse(binding.bytes.toString('utf8'));
    } catch (error) {
        fail(`${label} is not valid JSON: ${error.message}`, 'SCHEMA_MISMATCH');
    }
}

const FEATURE_CONTRACT_REGISTRY_SCHEMA_VERSION = 'model-feature-contract-registry/v2';
const V1_FEATURE_CONTRACT_ID = 'v26_7_aligned/v1';
const V_NEXT_FEATURE_CONTRACT_ID = 'canonical_prematch/vnext-v1';
const V_NEXT_REMOVED_FEATURES = new Set(['rolling_team_rating_home', 'rolling_team_rating_away', 'adjusted_elo_gap']);
const MIGRATION_CLASSIFICATIONS = new Set([
    'UNCHANGED',
    'REMOVED',
    'SEMANTICS_PENDING',
    'SOURCE_PENDING',
    'CONTRACT_PENDING',
]);
const REGISTRY_ROOT_FIELDS = new Set([
    'schema_version',
    'lifecycle',
    'contracts',
    'migration_map',
    'decision_boundaries',
]);
const REGISTRY_CONTRACT_FIELDS = new Set([
    'contract_id',
    'artifact_name',
    'model_type',
    'feature_contract_version',
    'feature_count',
    'ordered_features',
    'contract_role',
    'activation_status',
    'feature_statuses',
]);
const REQUIRED_CONTRACT_FIELDS = new Set([
    'contract_id',
    'artifact_name',
    'model_type',
    'feature_contract_version',
    'feature_count',
    'ordered_features',
]);
const FEATURE_STATUS_FIELDS = new Set([
    'feature_name',
    'v_next_status',
    'semantic_definition_status',
    'historical_source_status',
    'runtime_source_status',
    'training_eligibility',
    'reason_code',
]);
const EXPECTED_VNEXT_FEATURE_STATUS_VALUES = Object.freeze({
    rolling_xg_home: [
        'RETAINED_PROVEN',
        'PROVEN_DERIVED',
        'PROVEN_DERIVED',
        'NOT_PROVEN',
        'NOT_READY_RUNTIME_PARITY',
        'RUNTIME_NUMERIC_SEMANTICS_NOT_PROVEN',
    ],
    rolling_xg_away: [
        'RETAINED_PROVEN',
        'PROVEN_DERIVED',
        'PROVEN_DERIVED',
        'NOT_PROVEN',
        'NOT_READY_RUNTIME_PARITY',
        'RUNTIME_NUMERIC_SEMANTICS_NOT_PROVEN',
    ],
    rolling_shots_on_target_home: [
        'RETAINED_PENDING',
        'SEMANTICS_PENDING',
        'SOURCE_PENDING',
        'SOURCE_PENDING',
        'NOT_ELIGIBLE_SOURCE_CLOSURE',
        'SOT_SOURCE_IDENTITY_AND_OWN_GOAL_PENDING',
    ],
    rolling_shots_on_target_away: [
        'RETAINED_PENDING',
        'SEMANTICS_PENDING',
        'SOURCE_PENDING',
        'SOURCE_PENDING',
        'NOT_ELIGIBLE_SOURCE_CLOSURE',
        'SOT_SOURCE_IDENTITY_AND_OWN_GOAL_PENDING',
    ],
    rolling_possession_home: [
        'RETAINED_UNAVAILABLE',
        'SEMANTICS_DEFINED',
        'UNAVAILABLE',
        'UNAVAILABLE',
        'NOT_ELIGIBLE_SOURCE_UNAVAILABLE',
        'NO_PROVEN_POSSESSION_SOURCE_FACT',
    ],
    rolling_possession_away: [
        'RETAINED_UNAVAILABLE',
        'SEMANTICS_DEFINED',
        'UNAVAILABLE',
        'UNAVAILABLE',
        'NOT_ELIGIBLE_SOURCE_UNAVAILABLE',
        'NO_PROVEN_POSSESSION_SOURCE_FACT',
    ],
    home_table_position: [
        'RETAINED_PROVEN',
        'SEMANTICS_FROZEN',
        'PROVEN_FOR_FROZEN_SCOPE',
        'NOT_PROVEN',
        'NOT_READY_RUNTIME_PARITY',
        'RUNTIME_NUMERIC_SEMANTICS_NOT_PROVEN',
    ],
    away_table_position: [
        'RETAINED_PROVEN',
        'SEMANTICS_FROZEN',
        'PROVEN_FOR_FROZEN_SCOPE',
        'NOT_PROVEN',
        'NOT_READY_RUNTIME_PARITY',
        'RUNTIME_NUMERIC_SEMANTICS_NOT_PROVEN',
    ],
    table_position_diff: [
        'RETAINED_PROVEN',
        'SEMANTICS_FROZEN',
        'PROVEN_FOR_FROZEN_SCOPE',
        'NOT_PROVEN',
        'NOT_READY_RUNTIME_PARITY',
        'RUNTIME_NUMERIC_SEMANTICS_NOT_PROVEN',
    ],
    home_points: [
        'RETAINED_PROVEN',
        'PROVEN_DERIVED',
        'PROVEN_DERIVED',
        'NOT_PROVEN',
        'NOT_READY_RUNTIME_PARITY',
        'RUNTIME_NUMERIC_SEMANTICS_NOT_PROVEN',
    ],
    away_points: [
        'RETAINED_PROVEN',
        'PROVEN_DERIVED',
        'PROVEN_DERIVED',
        'NOT_PROVEN',
        'NOT_READY_RUNTIME_PARITY',
        'RUNTIME_NUMERIC_SEMANTICS_NOT_PROVEN',
    ],
    points_diff: [
        'RETAINED_PROVEN',
        'PROVEN_DERIVED',
        'PROVEN_DERIVED',
        'NOT_PROVEN',
        'NOT_READY_RUNTIME_PARITY',
        'RUNTIME_NUMERIC_SEMANTICS_NOT_PROVEN',
    ],
    home_recent_form_points: [
        'RETAINED_PROVEN',
        'PROVEN_DERIVED',
        'PROVEN_DERIVED',
        'NOT_PROVEN',
        'NOT_READY_RUNTIME_PARITY',
        'RUNTIME_NUMERIC_SEMANTICS_NOT_PROVEN',
    ],
    raw_elo_gap: [
        'RETAINED_PENDING',
        'OWNER_PARAMETER_DECISION_REQUIRED',
        'CONTRACT_PENDING',
        'CONTRACT_PENDING',
        'NOT_ELIGIBLE_OWNER_PARAMETER_CONTRACT',
        'ELO_OWNER_PARAMETER_DECISION_REQUIRED',
    ],
    home_fatigue_index: [
        'RETAINED_PROVEN',
        'PROVEN_DERIVED',
        'PROVEN_DERIVED',
        'NOT_PROVEN',
        'NOT_READY_RUNTIME_PARITY',
        'RUNTIME_NUMERIC_SEMANTICS_NOT_PROVEN',
    ],
    away_fatigue_index: [
        'RETAINED_PROVEN',
        'PROVEN_DERIVED',
        'PROVEN_DERIVED',
        'NOT_PROVEN',
        'NOT_READY_RUNTIME_PARITY',
        'RUNTIME_NUMERIC_SEMANTICS_NOT_PROVEN',
    ],
    fatigue_diff: [
        'RETAINED_PROVEN',
        'PROVEN_DERIVED',
        'PROVEN_DERIVED',
        'NOT_PROVEN',
        'NOT_READY_RUNTIME_PARITY',
        'RUNTIME_NUMERIC_SEMANTICS_NOT_PROVEN',
    ],
});

function isPlainObject(value) {
    return value !== null && typeof value === 'object' && !Array.isArray(value);
}

function hasExactKeys(value, expected) {
    return isPlainObject(value) && stableStringify(Object.keys(value).sort()) === stableStringify([...expected].sort());
}

function assertRegistryText(value, label) {
    if (typeof value !== 'string' || !value.trim()) fail(`${label} is malformed`, 'SCHEMA_MISMATCH');
}

function assertRegistryIdentifier(value, label) {
    assertRegistryText(value, label);
    if (!/^[A-Za-z0-9][A-Za-z0-9_.\-/]*$/.test(value)) fail(`${label} is malformed`, 'SCHEMA_MISMATCH');
}

function validateRegistryFeatureStatuses(contract) {
    if (contract.feature_statuses === undefined) return;
    if (!Array.isArray(contract.feature_statuses) || contract.feature_statuses.length === 0) {
        fail(`feature contract ${contract.contract_id} feature status matrix is malformed`, 'SCHEMA_MISMATCH');
    }
    const seen = new Set();
    for (const status of contract.feature_statuses) {
        if (!hasExactKeys(status, FEATURE_STATUS_FIELDS)) {
            fail(`feature contract ${contract.contract_id} feature status is malformed`, 'SCHEMA_MISMATCH');
        }
        for (const field of FEATURE_STATUS_FIELDS) assertRegistryText(status[field], `feature status ${field}`);
        if (!/^[A-Za-z0-9][A-Za-z0-9_]*$/.test(status.feature_name) || seen.has(status.feature_name)) {
            fail(`feature contract ${contract.contract_id} feature status name is malformed`, 'SCHEMA_MISMATCH');
        }
        seen.add(status.feature_name);
    }
}

function validateVNextFeatureStatusValues(contract) {
    const expectedFeatures = Object.keys(EXPECTED_VNEXT_FEATURE_STATUS_VALUES);
    if (stableStringify(expectedFeatures) !== stableStringify(contract.ordered_features)) {
        fail('V-next feature status authority is incomplete', 'SCHEMA_MISMATCH');
    }
    const fields = [
        'v_next_status',
        'semantic_definition_status',
        'historical_source_status',
        'runtime_source_status',
        'training_eligibility',
        'reason_code',
    ];
    for (const status of contract.feature_statuses) {
        const actual = fields.map(field => status[field]);
        if (stableStringify(actual) !== stableStringify(EXPECTED_VNEXT_FEATURE_STATUS_VALUES[status.feature_name])) {
            fail(`V-next feature status values are malformed for ${status.feature_name}`, 'SCHEMA_MISMATCH');
        }
    }
}

// eslint-disable-next-line complexity -- registry validation enumerates each fail-closed schema boundary.
function validateRegistryContractShape(contract, index) {
    if (!isPlainObject(contract)) {
        fail(`feature contract entry #${index} is malformed`, 'SCHEMA_MISMATCH');
    }
    if (![...REQUIRED_CONTRACT_FIELDS].every(field => field in contract)) {
        fail(`feature contract entry #${index} is malformed`, 'SCHEMA_MISMATCH');
    }
    for (const field of Object.keys(contract)) {
        if (!REGISTRY_CONTRACT_FIELDS.has(field)) {
            fail(`feature contract entry #${index} is malformed`, 'SCHEMA_MISMATCH');
        }
    }
    for (const field of ['contract_id', 'artifact_name', 'model_type', 'feature_contract_version']) {
        assertRegistryIdentifier(contract[field], `feature contract entry #${index}.${field}`);
    }
    if (!Number.isSafeInteger(contract.feature_count) || contract.feature_count <= 0) {
        fail(`feature contract entry #${index}.feature_count is malformed`, 'SCHEMA_MISMATCH');
    }
    if (!Array.isArray(contract.ordered_features) || contract.ordered_features.length !== contract.feature_count) {
        fail(`feature contract entry #${index}.ordered_features is malformed`, 'SCHEMA_MISMATCH');
    }
    const seenFeatures = new Set();
    for (const feature of contract.ordered_features) {
        if (typeof feature !== 'string' || !/^[A-Za-z0-9][A-Za-z0-9_]*$/.test(feature) || seenFeatures.has(feature)) {
            fail(`feature contract entry #${index}.ordered_features contains an invalid feature`, 'SCHEMA_MISMATCH');
        }
        seenFeatures.add(feature);
    }
    for (const field of ['contract_role', 'activation_status']) {
        if (contract[field] !== undefined) {
            assertRegistryText(contract[field], `feature contract entry #${index}.${field}`);
        }
    }
    validateRegistryFeatureStatuses(contract);
}

function validateRegistryMigrationMap(registry, v1Contract, vNextContract) {
    const migrationMap = registry.migration_map;
    const requiredFields = new Set(['from_contract_id', 'to_contract_id', 'entries']);
    if (!hasExactKeys(migrationMap, requiredFields)) {
        fail('feature contract migration map is malformed', 'SCHEMA_MISMATCH');
    }
    if (
        migrationMap.from_contract_id !== V1_FEATURE_CONTRACT_ID ||
        migrationMap.to_contract_id !== V_NEXT_FEATURE_CONTRACT_ID ||
        !Array.isArray(migrationMap.entries) ||
        migrationMap.entries.length !== v1Contract.feature_count
    ) {
        fail('feature contract migration map is incomplete', 'SCHEMA_MISMATCH');
    }
    const seen = new Set();
    const expectedEntries = v1Contract.ordered_features;
    migrationMap.entries.forEach((entry, index) => {
        const fields = new Set(['from_feature', 'to_feature', 'classification', 'reason']);
        if (!hasExactKeys(entry, fields)) fail(`migration entry #${index + 1} is malformed`, 'SCHEMA_MISMATCH');
        if (
            typeof entry.from_feature !== 'string' ||
            !expectedEntries.includes(entry.from_feature) ||
            seen.has(entry.from_feature)
        ) {
            fail(`migration entry #${index + 1} source feature is malformed`, 'SCHEMA_MISMATCH');
        }
        if (
            entry.to_feature !== null &&
            (!isPlainObject(vNextContract) || !vNextContract.ordered_features.includes(entry.to_feature))
        ) {
            fail(`migration entry #${index + 1} target feature is malformed`, 'SCHEMA_MISMATCH');
        }
        if (
            !MIGRATION_CLASSIFICATIONS.has(entry.classification) ||
            typeof entry.reason !== 'string' ||
            !entry.reason.trim()
        ) {
            fail(`migration entry #${index + 1} decision is malformed`, 'SCHEMA_MISMATCH');
        }
        if (entry.classification === 'REMOVED' ? entry.to_feature !== null : entry.to_feature === null) {
            fail(`migration entry #${index + 1} target/classification is inconsistent`, 'SCHEMA_MISMATCH');
        }
        seen.add(entry.from_feature);
    });
    if (stableStringify([...seen].sort()) !== stableStringify([...expectedEntries].sort())) {
        fail('feature contract migration source coverage is malformed', 'SCHEMA_MISMATCH');
    }
    const targets = migrationMap.entries.filter(entry => entry.to_feature !== null).map(entry => entry.to_feature);
    if (
        new Set(targets).size !== targets.length ||
        stableStringify([...new Set(targets)].sort()) !== stableStringify([...vNextContract.ordered_features].sort())
    ) {
        fail('feature contract migration target coverage is malformed', 'SCHEMA_MISMATCH');
    }
}

function requireBoundaryObject(value, fields, label) {
    if (!hasExactKeys(value, new Set(fields))) {
        fail(`${label} is malformed`, 'SCHEMA_MISMATCH');
    }
    return value;
}

function requireBoundaryText(value, label, expected = undefined) {
    assertRegistryText(value, label);
    if (expected !== undefined && value !== expected) {
        fail(`${label} is malformed`, 'SCHEMA_MISMATCH');
    }
}

function requireBoundaryTextFields(value, fields, label) {
    for (const field of fields) requireBoundaryText(value[field], `${label}.${field}`);
}

function requireBoundaryList(value, expected, label) {
    if (stableStringify(value) !== stableStringify(expected)) {
        fail(`${label} is malformed`, 'SCHEMA_MISMATCH');
    }
}

// eslint-disable-next-line complexity -- decision-boundary values are frozen as one auditable contract.
function validateDecisionBoundaryValues(boundaries) {
    const rawElo = requireBoundaryObject(
        boundaries.raw_elo,
        [
            'direction',
            'retained_in_v_next',
            'semantic_status',
            'training_eligible',
            'runtime_eligible',
            'parameter_sheet',
        ],
        'raw ELO decision boundary'
    );
    for (const [field, expected] of Object.entries({
        direction: 'BOUNDED_START',
        retained_in_v_next: 'YES',
        semantic_status: 'OWNER_PARAMETER_DECISION_REQUIRED',
        training_eligible: 'NO',
        runtime_eligible: 'NO',
    })) {
        requireBoundaryText(rawElo[field], `raw ELO decision boundary.${field}`, expected);
    }
    if (!Array.isArray(rawElo.parameter_sheet) || rawElo.parameter_sheet.length !== 11) {
        fail('raw ELO parameter sheet is malformed', 'SCHEMA_MISMATCH');
    }
    rawElo.parameter_sheet.forEach((parameter, index) => {
        const id = `E${index + 1}`;
        requireBoundaryObject(
            parameter,
            ['id', 'parameter', 'candidate_contract', 'owner_decision_required'],
            `raw ELO parameter ${id}`
        );
        requireBoundaryText(parameter.id, `raw ELO parameter ${id}.id`, id);
        requireBoundaryTextFields(parameter, ['parameter', 'candidate_contract'], `raw ELO parameter ${id}`);
        requireBoundaryText(
            parameter.owner_decision_required,
            `raw ELO parameter ${id}.owner_decision_required`,
            'YES'
        );
    });

    const standings = requireBoundaryObject(
        boundaries.standings,
        [
            'retained_in_v_next',
            'semantic_direction',
            'cutoff',
            'same_kickoff_fixtures',
            'training_eligible',
            'runtime_eligible',
            'rule_history_closure_required',
            'semantic_contract_status',
            'historical_evidence_status',
            'contract',
            'unresolved_evidence',
        ],
        'standings decision boundary'
    );
    for (const [field, expected] of Object.entries({
        retained_in_v_next: 'YES',
        semantic_direction: 'OFFICIAL_POINT_IN_TIME_STANDINGS',
        cutoff: 'source_kickoff < target_kickoff',
        same_kickoff_fixtures: 'EXCLUDED',
        training_eligible: 'NO',
        runtime_eligible: 'NO',
        rule_history_closure_required: 'YES',
        semantic_contract_status: 'FROZEN',
        historical_evidence_status: 'EVIDENCE_CLOSED_FOR_FROZEN_SCOPE',
    })) {
        requireBoundaryText(standings[field], `standings decision boundary.${field}`, expected);
    }
    if (!Array.isArray(standings.unresolved_evidence) || standings.unresolved_evidence.length !== 0) {
        fail('standings unresolved evidence is malformed', 'SCHEMA_MISMATCH');
    }
    if (!isPlainObject(standings.contract)) {
        fail('standings semantic contract is malformed', 'SCHEMA_MISMATCH');
    }

    const sot = requireBoundaryObject(
        boundaries.sot,
        [
            'retained_in_v_next',
            'inventory_mode',
            'existing_source_repair_feasible',
            'new_acquisition_required',
            'training_eligible',
            'runtime_eligible',
            'evidence',
            'evidence_provenance',
            'bounded_next_scope',
        ],
        'SOT decision boundary'
    );
    for (const [field, expected] of Object.entries({
        retained_in_v_next: 'YES',
        inventory_mode: 'READ_ONLY_EXISTING_FROZEN_SOURCES',
        existing_source_repair_feasible: 'NO',
        new_acquisition_required: 'YES',
        training_eligible: 'NO',
        runtime_eligible: 'NO',
    })) {
        requireBoundaryText(sot[field], `SOT decision boundary.${field}`, expected);
    }
    const evidence = requireBoundaryObject(
        sot.evidence,
        [
            'formal_payloads',
            'shotmap_payloads',
            'payloads_with_is_on_target',
            'payloads_with_is_own_goal',
            'payloads_with_own_goal_true',
            'normalized_team_identity_pairs',
            'independent_observed_home_away_team_pairs',
            'blocker',
        ],
        'SOT evidence'
    );
    const expectedEvidenceCounts = {
        formal_payloads: 812,
        shotmap_payloads: 812,
        payloads_with_is_on_target: 812,
        payloads_with_is_own_goal: 812,
        payloads_with_own_goal_true: 90,
        normalized_team_identity_pairs: 812,
        independent_observed_home_away_team_pairs: 0,
    };
    for (const [field, expected] of Object.entries(expectedEvidenceCounts)) {
        if (!Number.isSafeInteger(evidence[field]) || evidence[field] !== expected) {
            fail(`SOT evidence.${field} is malformed`, 'SCHEMA_MISMATCH');
        }
    }
    requireBoundaryText(
        evidence.blocker,
        'SOT evidence.blocker',
        'Frozen captures do not prove independent home/away shot-team binding.'
    );
    const evidenceProvenance = requireBoundaryObject(
        sot.evidence_provenance,
        ['authority', 'memo_sha256', 'inventory_scope', 'reproducibility'],
        'SOT evidence provenance'
    );
    requireBoundaryText(
        evidenceProvenance.authority,
        'SOT evidence provenance.authority',
        'OSD-V1 final decision memo'
    );
    requireBoundaryText(
        evidenceProvenance.memo_sha256,
        'SOT evidence provenance.memo_sha256',
        '21eab8eedb31688488850d47833b2f86a2b765abadc49562050a81ebeaf78e2f'
    );
    requireBoundaryTextFields(evidenceProvenance, ['inventory_scope', 'reproducibility'], 'SOT evidence provenance');
    if (
        !Array.isArray(sot.bounded_next_scope) ||
        sot.bounded_next_scope.length !== 5 ||
        sot.bounded_next_scope.some(item => typeof item !== 'string' || !item.trim())
    ) {
        fail('SOT bounded next scope is malformed', 'SCHEMA_MISMATCH');
    }

    const possession = requireBoundaryObject(
        boundaries.possession,
        [
            'retained_in_v_next',
            'historical_source_status',
            'runtime_source_status',
            'training_eligible',
            'runtime_eligible',
            'fallbacks_forbidden',
        ],
        'possession decision boundary'
    );
    for (const [field, expected] of Object.entries({
        retained_in_v_next: 'YES',
        historical_source_status: 'UNAVAILABLE',
        runtime_source_status: 'UNAVAILABLE',
        training_eligible: 'NO',
        runtime_eligible: 'NO',
    })) {
        requireBoundaryText(possession[field], `possession decision boundary.${field}`, expected);
    }
    requireBoundaryList(
        possession.fallbacks_forbidden,
        ['50/50', '55/45', 'team average', 'league average', 'forward fill', 'interpolation', 'estimated possession'],
        'possession forbidden fallback policy'
    );

    const sharedEngine = requireBoundaryObject(
        boundaries.shared_engine,
        [
            'architecture_approved',
            'implementation_started',
            'canonical_semantic_engine',
            'historical_source_adapter',
            'runtime_source_adapter',
        ],
        'shared semantic engine boundary'
    );
    requireBoundaryText(sharedEngine.architecture_approved, 'shared semantic engine architecture_approved', 'YES');
    requireBoundaryText(sharedEngine.implementation_started, 'shared semantic engine implementation_started', 'NO');
    const canonicalEngine = requireBoundaryObject(
        sharedEngine.canonical_semantic_engine,
        ['input', 'output', 'prohibitions'],
        'canonical semantic engine boundary'
    );
    requireBoundaryTextFields(canonicalEngine, ['input', 'output'], 'canonical semantic engine boundary');
    requireBoundaryList(
        canonicalEngine.prohibitions,
        [
            'network fetch',
            'provider query',
            'database query',
            'database write',
            'historical/runtime path branching',
            'compatibility proxy defaults',
            'silent unavailable-field defaults',
        ],
        'canonical semantic engine prohibitions'
    );
    requireBoundaryTextFields(
        sharedEngine,
        ['historical_source_adapter', 'runtime_source_adapter'],
        'shared semantic engine boundary'
    );

    const activation = requireBoundaryObject(
        boundaries.activation,
        [
            'v_next_defined',
            'v_next_default_activated',
            'training_default_switched',
            'runtime_default_switched',
            'model_schema_switched',
            'feature_frame_readiness',
            'real_training_readiness',
            'train_inference_numeric_parity',
            'golden_dataset_complete',
        ],
        'activation boundary'
    );
    for (const [field, expected] of Object.entries({
        v_next_defined: 'YES',
        v_next_default_activated: 'NO',
        training_default_switched: 'NO',
        runtime_default_switched: 'NO',
        model_schema_switched: 'NO',
        feature_frame_readiness: 'NOT_READY',
        real_training_readiness: 'NOT_READY',
        train_inference_numeric_parity: 'NOT_PROVEN',
        golden_dataset_complete: 'NO',
    })) {
        requireBoundaryText(activation[field], `activation boundary.${field}`, expected);
    }

    const legacy = requireBoundaryObject(
        boundaries.legacy_proxy_policy,
        ['canonical_v_next_reachability', 'proxies_rejected', 'compatibility_behavior'],
        'legacy proxy policy'
    );
    requireBoundaryText(
        legacy.canonical_v_next_reachability,
        'legacy proxy policy.canonical_v_next_reachability',
        'NO'
    );
    requireBoundaryList(
        legacy.proxies_rejected,
        [
            'goals proxy for xG',
            'goals*3+2 SOT',
            '55/45 possession',
            'estimated standings',
            'default or implicit cold-start ELO',
            'fatigue 0.5 fallback',
            'compatibility team rating',
            'raw_elo_gap * 0.1 adjusted ELO',
        ],
        'legacy proxy rejection policy'
    );
    requireBoundaryTextFields(legacy, ['compatibility_behavior'], 'legacy proxy policy');
}

// eslint-disable-next-line complexity -- registry validation enumerates the version lifecycle and migration gates.
function validateFeatureContractRegistry(registry) {
    if (!isPlainObject(registry) || !hasExactKeys(registry, REGISTRY_ROOT_FIELDS)) {
        fail('feature contract registry v2 fields are malformed', 'SCHEMA_MISMATCH');
    }
    if (registry.schema_version !== FEATURE_CONTRACT_REGISTRY_SCHEMA_VERSION || registry.lifecycle !== 'permanent') {
        fail('feature contract registry schema or lifecycle is unsupported', 'SCHEMA_MISMATCH');
    }
    if (!Array.isArray(registry.contracts) || registry.contracts.length !== 2) {
        fail('feature contract registry must contain exactly V1 and V-next contracts', 'SCHEMA_MISMATCH');
    }
    const contractIds = new Set();
    const modelBindings = new Set();
    registry.contracts.forEach((contract, index) => {
        validateRegistryContractShape(contract, index + 1);
        if (contractIds.has(contract.contract_id)) fail('duplicate feature contract id', 'SCHEMA_MISMATCH');
        const binding = `${contract.artifact_name}\u0000${contract.model_type}`;
        if (modelBindings.has(binding)) fail('duplicate feature contract model binding', 'SCHEMA_MISMATCH');
        contractIds.add(contract.contract_id);
        modelBindings.add(binding);
    });
    const v1Contract = registry.contracts.find(contract => contract.contract_id === V1_FEATURE_CONTRACT_ID);
    const vNextContract = registry.contracts.find(contract => contract.contract_id === V_NEXT_FEATURE_CONTRACT_ID);
    if (!v1Contract || !vNextContract || registry.contracts[0] !== v1Contract) {
        fail('versioned registry must contain frozen V1 first and V-next contracts', 'SCHEMA_MISMATCH');
    }
    if (v1Contract.contract_role !== 'HISTORICAL_DEFAULT' || v1Contract.activation_status !== 'ACTIVE_DEFAULT') {
        fail('frozen V1 contract default binding is malformed', 'SCHEMA_MISMATCH');
    }
    if (
        vNextContract.contract_role !== 'VERSIONED_NEXT' ||
        vNextContract.activation_status !== 'DEFINED_NOT_ACTIVATED'
    ) {
        fail('V-next contract activation boundary is malformed', 'SCHEMA_MISMATCH');
    }
    if (
        vNextContract.feature_count !== 17 ||
        !Array.isArray(vNextContract.feature_statuses) ||
        vNextContract.feature_statuses.length !== vNextContract.feature_count ||
        stableStringify(vNextContract.feature_statuses.map(status => status.feature_name)) !==
            stableStringify(vNextContract.ordered_features) ||
        vNextContract.ordered_features.some(feature => V_NEXT_REMOVED_FEATURES.has(feature))
    ) {
        fail('V-next feature status/order boundary is malformed', 'SCHEMA_MISMATCH');
    }
    validateVNextFeatureStatusValues(vNextContract);
    validateRegistryMigrationMap(registry, v1Contract, vNextContract);
    const boundaryNames = new Set([
        'raw_elo',
        'standings',
        'sot',
        'possession',
        'shared_engine',
        'activation',
        'legacy_proxy_policy',
    ]);
    if (
        !hasExactKeys(registry.decision_boundaries, boundaryNames) ||
        [...boundaryNames].some(name => !isPlainObject(registry.decision_boundaries[name]))
    ) {
        fail('feature contract decision boundaries are incomplete', 'SCHEMA_MISMATCH');
    }
    validateDecisionBoundaryValues(registry.decision_boundaries);
    return { v1Contract, vNextContract };
}

function loadFeatureContract(repositoryRoot) {
    const binding = assertRepositoryConfigFile(
        path.join(repositoryRoot, 'config/model_feature_contracts.json'),
        'feature contract registry',
        repositoryRoot
    );
    const registry = parseJson(binding, 'feature contract registry');
    const { v1Contract: contract } = validateFeatureContractRegistry(registry);
    const runtimeFeatureAdapter = loadRuntimeFeatureIdentity(repositoryRoot);
    if (stableStringify(contract.ordered_features) !== stableStringify(runtimeFeatureAdapter.orderedFeatures)) {
        fail('config feature order differs from V26_6_PreMatchAdapter.V26_6_FEATURES', 'SCHEMA_MISMATCH');
    }
    return {
        contract,
        bytes: binding.bytes,
        sha256: binding.sha256,
        registrySchemaVersion: registry.schema_version,
        runtimeFeatureAdapter,
    };
}

function buildSourceBindings(inputs, featureContractBinding, scheduleValidation) {
    const factRows = inputs.gdA02.artifact.rows;
    const factRejections = inputs.gdA02.artifact.rejected_rows;
    const factResultBindings = factRows.map(row => ({
        canonical_match_id: row.canonical_match_id,
        fact_result_binding: computeFactResultBinding({
            canonicalMatchId: row.canonical_match_id,
            result: row.facts.match_result,
            sourceProvenance: row.provenance,
        }),
    }));
    const factRejectionBindings = factRejections.map(row => ({
        canonical_match_id: row.canonical_match_id,
        fact_rejection_binding: computeFactRejectionBinding({
            canonicalMatchId: row.canonical_match_id,
            sourceMatchId: row.source_match_id,
            rejectionReason: row.admission.rejection_reason,
            errorCode: row.error_code,
            reason: row.reason,
        }),
    }));
    return {
        gd_a01_artifact: {
            sha256: inputs.gdA01Artifact.sha256,
            business_hash: inputs.gdA01.artifact.business_content_sha256,
            schema_version: inputs.gdA01.artifact.schema_version,
        },
        gd_a01_receipt: {
            sha256: inputs.gdA01Receipt.sha256,
            business_hash: inputs.gdA01.receipt.output_business_sha256,
            schema_version: inputs.gdA01.receipt.schema_version,
            admitted_id_set_sha256: inputs.gdA01.receipt.admitted_id_set_sha256,
            admitted_row_count: inputs.gdA01.receipt.admitted_row_count,
        },
        gd_a02_artifact: {
            sha256: inputs.gdA02Artifact.sha256,
            business_hash: inputs.gdA02.artifact.business_content_sha256,
            schema_version: inputs.gdA02.artifact.schema_version,
            fact_result_bindings_sha256: computeFactResultBindingsHash(factResultBindings),
            fact_result_binding_count: factResultBindings.length,
            fact_rejection_bindings_sha256: computeFactRejectionBindingsHash(factRejectionBindings),
            fact_rejection_binding_count: factRejectionBindings.length,
            fact_admitted_id_set_sha256: admittedIdSetHash(factRows.map(row => row.canonical_match_id)),
            fact_admitted_row_count: factRows.length,
            fact_rejected_id_set_sha256: admittedIdSetHash(factRejections.map(row => row.canonical_match_id)),
            fact_rejected_row_count: factRejections.length,
            fact_accounted_id_set_sha256: admittedIdSetHash([
                ...factRows.map(row => row.canonical_match_id),
                ...factRejections.map(row => row.canonical_match_id),
            ]),
            fact_accounted_row_count: factRows.length + factRejections.length,
        },
        gd_a02_receipt: {
            sha256: inputs.gdA02Receipt.sha256,
            business_hash: inputs.gdA02.receipt.output_business_sha256,
            schema_version: inputs.gdA02.receipt.schema_version,
        },
        canonical_schedule: {
            sha256: inputs.schedule.sha256,
            business_hash: scheduleValidation.businessHash,
            schema_version: 'candidate-match-identity/v1',
        },
        feature_contract: {
            sha256: featureContractBinding.sha256,
            schema_version: featureContractBinding.registrySchemaVersion,
        },
        runtime_feature_adapter: {
            sha256: featureContractBinding.runtimeFeatureAdapter.sha256,
            schema_version: featureContractBinding.runtimeFeatureAdapter.symbol,
            ordered_features: featureContractBinding.runtimeFeatureAdapter.orderedFeatures,
        },
    };
}

function loadBuildInputs(args, repositoryRoot) {
    const gdA01Artifact = assertExternalRegularFile(args.gdA01ArtifactPath, 'GD-A01 artifact', repositoryRoot);
    const gdA01Receipt = assertExternalRegularFile(args.gdA01ReceiptPath, 'GD-A01 receipt', repositoryRoot);
    const gdA02Artifact = assertExternalRegularFile(args.gdA02ArtifactPath, 'GD-A02 artifact', repositoryRoot);
    const gdA02Receipt = assertExternalRegularFile(args.gdA02ReceiptPath, 'GD-A02 receipt', repositoryRoot);
    const schedule = assertExternalRegularFile(
        args.scheduleArtifactPath,
        'canonical schedule artifact',
        repositoryRoot
    );
    const gdA01 = validateGdA01OutputFiles(gdA01Artifact.bytes, gdA01Receipt.bytes);
    // GD-A02 may legitimately contain rejected rows. GD-A03 binds admitted ∪ rejected
    // coverage to GD-A01, so an expected target count must not be misread as an
    // admitted-fact count here.
    const gdA02 = validateGdA02OutputFiles(gdA02Artifact.bytes, gdA02Receipt.bytes);
    const scheduleDocument = parseJson(schedule, 'canonical schedule artifact');
    let scheduleValidation;
    try {
        scheduleValidation = validateCanonicalCandidateDocument(scheduleDocument);
    } catch (error) {
        fail(`canonical schedule artifact is invalid: ${error.message}`, error.code || 'SCHEMA_MISMATCH');
    }
    const expectedCandidateBinding = gdA01.artifact.source_bindings.canonical_candidate_artifact;
    if (
        !expectedCandidateBinding ||
        schedule.sha256 !== expectedCandidateBinding.sha256 ||
        scheduleValidation.businessHash !== expectedCandidateBinding.business_hash
    ) {
        fail('canonical schedule artifact does not match GD-A01 identity binding', 'HASH_MISMATCH');
    }
    if (scheduleValidation.candidates.length !== MASTER_COUNT) {
        fail(`canonical schedule must contain ${MASTER_COUNT} candidates`, 'HISTORY_CLOSURE_INVALID');
    }
    for (const season of SEASONS) {
        const count = scheduleValidation.candidates.filter(candidate => candidate.season === season).length;
        if (count !== FIXTURES_PER_SEASON) {
            fail(
                `canonical schedule season ${season} must contain ${FIXTURES_PER_SEASON} candidates`,
                'HISTORY_CLOSURE_INVALID'
            );
        }
    }
    const featureContractBinding = loadFeatureContract(repositoryRoot);
    const perSeasonCounts = scheduleValidation.candidates.reduce((counts, candidate) => {
        counts[candidate.season] = (counts[candidate.season] || 0) + 1;
        return counts;
    }, {});
    const perTeamCounts = {};
    for (const candidate of scheduleValidation.candidates) {
        const seasonTeams = perTeamCounts[candidate.season] || {};
        const home = seasonTeams[candidate.home_team] || { total: 0, home: 0, away: 0 };
        const away = seasonTeams[candidate.away_team] || { total: 0, home: 0, away: 0 };
        home.total += 1;
        home.home += 1;
        away.total += 1;
        away.away += 1;
        seasonTeams[candidate.home_team] = home;
        seasonTeams[candidate.away_team] = away;
        perTeamCounts[candidate.season] = seasonTeams;
    }
    const scheduleClosure = {
        schema_version: 'canonical-schedule-history/v1',
        status: 'PROVEN',
        authority:
            'canonical-inventory-contract + candidate-match-identity/v1; schedule completeness only, not result completeness',
        per_season_expected_counts: perSeasonCounts,
        team_closure: {
            schema_version: SCHEDULE_TEAM_CLOSURE_SCHEMA_VERSION,
            status: 'PROVEN',
            teams_per_season: SCHEDULE_TEAMS_PER_SEASON,
            fixtures_per_team: SCHEDULE_FIXTURES_PER_TEAM,
            home_fixtures_per_team: SCHEDULE_HOME_FIXTURES_PER_TEAM,
            away_fixtures_per_team: SCHEDULE_AWAY_FIXTURES_PER_TEAM,
            per_team_counts: perTeamCounts,
        },
    };
    return {
        targetRows: gdA01.artifact.rows,
        factRows: gdA02.artifact.rows,
        factRejections: gdA02.artifact.rejected_rows,
        scheduleCandidates: scheduleValidation.candidates,
        scheduleClosure,
        featureContract: featureContractBinding.contract,
        sourceBindings: buildSourceBindings(
            { gdA01Artifact, gdA01Receipt, gdA02Artifact, gdA02Receipt, schedule, gdA01, gdA02 },
            featureContractBinding,
            scheduleValidation
        ),
        codeRevision: args.codeRevision,
    };
}

function writeOutputs(result, args, repositoryRoot) {
    const outputPath = assertOutputPath(args.outputPath, 'GD-A03 artifact output', repositoryRoot);
    const receiptPath = assertOutputPath(args.receiptPath, 'GD-A03 receipt output', repositoryRoot);
    if (outputPath === receiptPath) fail('GD-A03 artifact and receipt outputs must differ', 'PATH_INVALID');
    fs.writeFileSync(outputPath, result.artifactBytes, { flag: 'wx' });
    fs.writeFileSync(receiptPath, result.receiptBytes, { flag: 'wx' });
    return { outputPath, receiptPath };
}

function summary(result, output = null) {
    const artifact = result.artifact;
    return {
        schema_version: PRIOR_STATE_ARTIFACT_SCHEMA_VERSION,
        target_population: artifact.population_accounting.target_population_count,
        rows_accounted: artifact.population_accounting.rows_accounted,
        feature_eligible: artifact.population_accounting.feature_eligible_count,
        feature_unavailable: artifact.population_accounting.feature_unavailable_count,
        unaccounted: artifact.population_accounting.unaccounted_count,
        duplicate: artifact.population_accounting.duplicate_id_count,
        extra: artifact.population_accounting.extra_id_count,
        validation_counters: artifact.validation_counters,
        numeric_parity: artifact.numeric_parity,
        business_hash: artifact.business_content_sha256,
        output,
        receipt: output ? output.receipt : undefined,
        validation: 'PASS',
    };
}

function main(argv = process.argv.slice(2), dependencies = {}) {
    const stdout = dependencies.stdout || (text => process.stdout.write(text));
    const stderr = dependencies.stderr || (text => process.stderr.write(text));
    const repositoryRoot = dependencies.repositoryRoot || path.resolve(__dirname, '../..');
    try {
        const args = parseArgs(argv);
        if (args.command === 'help') {
            stdout(`${usage()}\n`);
            return EXIT_CODES.OK;
        }
        if (args.command === 'validate') {
            const artifact = assertExternalRegularFile(args.artifactPath, 'GD-A03 artifact', repositoryRoot);
            const receipt = assertExternalRegularFile(args.receiptPath, 'GD-A03 receipt', repositoryRoot);
            const result = validatePriorStateOutputFiles(artifact.bytes, receipt.bytes);
            if (
                args.expectedTargets !== undefined &&
                result.artifact.population_accounting.target_population_count !== args.expectedTargets
            ) {
                fail(`GD-A03 target population is not ${args.expectedTargets}`, 'POPULATION_MISMATCH');
            }
            stdout(`${JSON.stringify(summary(result))}\n`);
            return EXIT_CODES.OK;
        }
        assertCodeRevisionMatchesHead(args.codeRevision, repositoryRoot);
        const result = buildPriorStateFeatureView(loadBuildInputs(args, repositoryRoot));
        validatePriorStateOutputFiles(result.artifactBytes, result.receiptBytes);
        if (
            args.expectedTargets !== undefined &&
            result.artifact.population_accounting.target_population_count !== args.expectedTargets
        ) {
            fail(`GD-A03 target population is not ${args.expectedTargets}`, 'POPULATION_MISMATCH');
        }
        const written = writeOutputs(result, args, repositoryRoot);
        stdout(`${JSON.stringify(summary(result, written))}\n`);
        return EXIT_CODES.OK;
    } catch (error) {
        const code =
            error instanceof GdA03ContractError || typeof error?.code === 'string' ? error.code : 'UNEXPECTED_ERROR';
        stderr(`gd-a03 assembler failed: ${error.message}\n`);
        if (code === 'UNEXPECTED_ERROR') return EXIT_CODES.UNEXPECTED;
        if (
            [
                'ARTIFACT_HASH_MISMATCH',
                'BUSINESS_HASH_MISMATCH',
                'SCHEMA_MISMATCH',
                'POPULATION_MISMATCH',
                'CUTOFF_VIOLATION',
                'TARGET_MATCH_LEAK',
                'HISTORY_CLOSURE_INVALID',
                'PROVENANCE_INVALID',
                'FACT_VALUE_INVALID',
                'RECEIPT_HASH_MISMATCH',
            ].includes(code)
        ) {
            return EXIT_CODES.VALIDATION;
        }
        return EXIT_CODES.INPUT;
    }
}

if (require.main === module) process.exitCode = main();

module.exports = {
    EXIT_CODES,
    loadBuildInputs,
    loadFeatureContract,
    loadRuntimeFeatureIdentity,
    main,
    parseArgs,
    summary,
    usage,
};
