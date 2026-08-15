#!/usr/bin/env node
'use strict';

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
} = require('../../src/infrastructure/golden_dataset/GdA03PriorStateContract');
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
        fail(
            `--code-revision ${codeRevision} does not match Git HEAD ${gitState.revision}`,
            'CODE_REVISION_MISMATCH'
        );
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

function loadFeatureContract(repositoryRoot) {
    const binding = assertRepositoryConfigFile(
        path.join(repositoryRoot, 'config/model_feature_contracts.json'),
        'feature contract registry',
        repositoryRoot
    );
    const registry = parseJson(binding, 'feature contract registry');
    if (!Array.isArray(registry.contracts) || registry.contracts.length !== 1) {
        fail('feature contract registry must have one canonical contract', 'SCHEMA_MISMATCH');
    }
    const contract = registry.contracts[0];
    const runtimeFeatureAdapter = loadRuntimeFeatureIdentity(repositoryRoot);
    if (stableStringify(contract.ordered_features) !== stableStringify(runtimeFeatureAdapter.orderedFeatures)) {
        fail('config feature order differs from V26_6_PreMatchAdapter.V26_6_FEATURES', 'SCHEMA_MISMATCH');
    }
    return {
        contract,
        bytes: binding.bytes,
        sha256: binding.sha256,
        runtimeFeatureAdapter,
    };
}

function buildSourceBindings(inputs, featureContractBinding, scheduleValidation) {
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
        },
        gd_a02_artifact: {
            sha256: inputs.gdA02Artifact.sha256,
            business_hash: inputs.gdA02.artifact.business_content_sha256,
            schema_version: inputs.gdA02.artifact.schema_version,
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
            schema_version: 'model-feature-contract-registry/v1',
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
    const gdA02 = validateGdA02OutputFiles(gdA02Artifact.bytes, gdA02Receipt.bytes, {
        expectedAdmittedRows: args.expectedTargets,
    });
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
