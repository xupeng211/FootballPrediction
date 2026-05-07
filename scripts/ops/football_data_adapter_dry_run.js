#!/usr/bin/env node
'use strict';

const crypto = require('crypto');
const fs = require('fs');
const path = require('path');
const { parseFootballDataCsv } = require('../lib/football_data_local_csv_parser');

const DRY_RUN_VERSION = 'PHASE4.63C_FOOTBALL_DATA_ADAPTER_DRY_RUN';
const REQUIRED_MANIFEST_FIELDS = ['source_name', 'approval_status', 'sha256', 'row_count', 'mapping_version'];
const ALLOWED_APPROVAL_STATUSES = new Set(['dry_run_only', 'approved_for_dry_run']);

function usage() {
    return [
        'Usage:',
        '  node scripts/ops/football_data_adapter_dry_run.js --source-manifest <path> --local-csv <path> [--json]',
        '  node scripts/ops/football_data_adapter_dry_run.js --source-manifest <path> --local-csv <path> --commit',
        '',
        'Safety:',
        '  Phase 4.63C is local dry-run only. No network, no DB, no adapted CSV, no staging writes.',
    ].join('\n');
}

function parseArgs(argv) {
    const args = {
        sourceManifest: '',
        localCsv: '',
        commit: false,
        json: false,
        help: false,
    };

    for (let index = 0; index < argv.length; index += 1) {
        const token = argv[index];
        if (token.startsWith('--source-manifest=')) {
            args.sourceManifest = token.slice('--source-manifest='.length);
        } else if (token === '--source-manifest') {
            args.sourceManifest = String(argv[index + 1] || '');
            index += 1;
        } else if (token.startsWith('--local-csv=')) {
            args.localCsv = token.slice('--local-csv='.length);
        } else if (token === '--local-csv') {
            args.localCsv = String(argv[index + 1] || '');
            index += 1;
        } else if (token === '--commit') {
            args.commit = true;
        } else if (token === '--json') {
            args.json = true;
        } else if (token === '--help' || token === '-h') {
            args.help = true;
        } else {
            throw new Error(`Unknown argument: ${token}`);
        }
    }

    return args;
}

function resolveLocalPath(rawPath, cwd = process.cwd()) {
    if (!rawPath) {
        return '';
    }
    return path.isAbsolute(rawPath) ? path.resolve(rawPath) : path.resolve(cwd, rawPath);
}

function toRelativePath(absolutePath, cwd = process.cwd()) {
    if (!absolutePath) {
        return '';
    }
    return path.relative(cwd, absolutePath) || '.';
}

function buildNonExecutionConfirmations() {
    return [
        'no_external_network',
        'no_db_reads',
        'no_db_writes',
        'no_file_writes',
        'no_legacy_runtime',
        'no_training',
        'no_prediction_execution',
        'no_model_artifact_load',
        'no_adapted_csv_writes',
        'no_staging_writes',
    ];
}

function buildSafetyFlags() {
    return {
        would_insert_matches: false,
        would_insert_odds: false,
        would_write_db: false,
        would_access_network: false,
        would_write_files: false,
        would_execute_legacy_runtime: false,
        would_train_model: false,
        would_execute_prediction: false,
    };
}

function countCsvDataRows(csvText) {
    const lines = String(csvText || '')
        .replace(/^\uFEFF/, '')
        .replace(/\r\n/g, '\n')
        .replace(/\r/g, '\n')
        .split('\n')
        .map(line => line.trim())
        .filter(Boolean);

    return Math.max(0, lines.length - 1);
}

function sha256Text(text) {
    return crypto.createHash('sha256').update(text).digest('hex');
}

function readJsonFile(filePath) {
    return JSON.parse(fs.readFileSync(filePath, 'utf8'));
}

function validateManifest(manifest) {
    const errors = [];
    const missingFields = REQUIRED_MANIFEST_FIELDS.filter(
        field => manifest[field] === undefined || manifest[field] === null || manifest[field] === ''
    );
    const hasLocalCsvPath = typeof manifest.local_csv_path === 'string' && manifest.local_csv_path.trim() !== '';

    if (missingFields.length > 0) {
        errors.push(`manifest missing required fields: ${missingFields.join(',')}`);
    }
    if (!hasLocalCsvPath) {
        errors.push('manifest missing required field: local_csv_path');
    }
    if (!ALLOWED_APPROVAL_STATUSES.has(String(manifest.approval_status || ''))) {
        errors.push(`approval_status is not allowed for dry-run: ${manifest.approval_status || ''}`);
    }
    if (!Number.isInteger(manifest.row_count) || manifest.row_count < 0) {
        errors.push('manifest row_count must be a non-negative integer');
    }

    return {
        manifest_valid: errors.length === 0,
        manifest_required_fields_present: missingFields.length === 0 && hasLocalCsvPath,
        manifest_missing_fields: hasLocalCsvPath ? missingFields : [...missingFields, 'local_csv_path'],
        approval_status_allowed: ALLOWED_APPROVAL_STATUSES.has(String(manifest.approval_status || '')),
        errors,
    };
}

function buildFailurePayload(args, fields = {}) {
    return {
        dry_run_version: DRY_RUN_VERSION,
        mode: fields.mode || 'football-data-csv-dry-run',
        ok: false,
        source_manifest: args.sourceManifest || null,
        local_csv: args.localCsv || null,
        source_manifest_found: false,
        local_csv_found: false,
        sha256_match: false,
        row_count_match: false,
        ...buildSafetyFlags(),
        non_execution_confirmations: buildNonExecutionConfirmations(),
        errors: [],
        warnings: [],
        ...fields,
    };
}

function buildBlockedCommitPayload(args) {
    return buildFailurePayload(args, {
        mode: 'blocked-commit',
        blocked: true,
        blocked_reason: 'BLOCKED: football-data CSV commit is not wired in Phase 4.63C.',
        errors: ['BLOCKED: football-data CSV commit is not wired in Phase 4.63C.'],
    });
}

function buildPathContext(args, cwd, existsSync) {
    const sourceManifestPath = resolveLocalPath(args.sourceManifest, cwd);
    const localCsvPath = resolveLocalPath(args.localCsv, cwd);
    return {
        sourceManifestPath,
        localCsvPath,
        sourceManifestFound: existsSync(sourceManifestPath),
        localCsvFound: existsSync(localCsvPath),
    };
}

function validateDryRunInputs(args, cwd, pathContext) {
    if (!args.sourceManifest || !args.localCsv) {
        return buildFailurePayload(args, {
            mode: 'argument-error',
            errors: ['ERROR: provide --source-manifest=<path> and --local-csv=<path>'],
        });
    }

    if (!pathContext.sourceManifestFound) {
        return buildFailurePayload(args, {
            mode: 'manifest-error',
            source_manifest_found: false,
            local_csv_found: pathContext.localCsvFound,
            errors: [`source manifest not found: ${toRelativePath(pathContext.sourceManifestPath, cwd)}`],
        });
    }

    if (!pathContext.localCsvFound) {
        return buildFailurePayload(args, {
            mode: 'csv-error',
            source_manifest_found: true,
            local_csv_found: false,
            errors: [`local CSV not found: ${toRelativePath(pathContext.localCsvPath, cwd)}`],
        });
    }

    return null;
}

function loadManifestPayload(args, pathContext, readManifest) {
    try {
        return {
            manifest: readManifest(pathContext.sourceManifestPath),
            errorPayload: null,
        };
    } catch (error) {
        return {
            manifest: null,
            errorPayload: buildFailurePayload(args, {
                mode: 'manifest-error',
                source_manifest_found: true,
                local_csv_found: true,
                errors: [`unable to parse source manifest: ${error.message}`],
            }),
        };
    }
}

function buildManifestValidationPayload(args, manifestValidation) {
    if (manifestValidation.manifest_valid) {
        return null;
    }

    return buildFailurePayload(args, {
        mode: 'manifest-error',
        source_manifest_found: true,
        local_csv_found: true,
        manifest_valid: false,
        manifest_required_fields_present: manifestValidation.manifest_required_fields_present,
        manifest_missing_fields: manifestValidation.manifest_missing_fields,
        approval_status_allowed: manifestValidation.approval_status_allowed,
        errors: manifestValidation.errors,
    });
}

function buildIntegrityFields(manifest, csvText) {
    const actualSha256 = sha256Text(csvText);
    const actualRowCount = countCsvDataRows(csvText);
    return {
        source_manifest_found: true,
        local_csv_found: true,
        manifest_valid: true,
        manifest_required_fields_present: true,
        approval_status_allowed: true,
        expected_sha256: manifest.sha256,
        actual_sha256: actualSha256,
        sha256_match: actualSha256 === manifest.sha256,
        expected_row_count: manifest.row_count,
        actual_row_count: actualRowCount,
        row_count_match: actualRowCount === manifest.row_count,
    };
}

function buildIntegrityFailurePayload(args, integrityFields) {
    if (!integrityFields.sha256_match) {
        return buildFailurePayload(args, {
            mode: 'integrity-error',
            ...integrityFields,
            errors: ['sha256 mismatch; parser was not executed'],
        });
    }

    if (!integrityFields.row_count_match) {
        return buildFailurePayload(args, {
            mode: 'integrity-error',
            ...integrityFields,
            errors: ['row_count mismatch; parser was not executed'],
        });
    }

    return null;
}

function buildParserOptions(manifest) {
    return {
        sourceName: manifest.source_name,
        dataVersion: manifest.mapping_version,
        defaultSeason: manifest.default_season || manifest.season || '2024/2025',
        timezone: manifest.timezone || 'UTC',
    };
}

function buildSuccessPayload(args, manifest, parserResult, integrityFields) {
    const classification = parserResult.row_classification || {};
    return {
        dry_run_version: DRY_RUN_VERSION,
        mode: 'football-data-csv-dry-run',
        ok: true,
        source_manifest: args.sourceManifest,
        local_csv: args.localCsv,
        source_name: manifest.source_name,
        source_type: manifest.source_type || null,
        approval_status: manifest.approval_status,
        mapping_version: manifest.mapping_version,
        parser_version: parserResult.parser_version,
        ...integrityFields,
        total_rows: parserResult.total_rows,
        parsed_rows: parserResult.parsed_rows,
        candidate_rows: parserResult.candidate_rows,
        candidate_preview: parserResult.candidate_rows.slice(0, 5),
        row_classification: classification,
        trainable_label_rows: classification.trainable_label_rows || 0,
        skipped_rows: classification.skipped_rows || 0,
        invalid_date_rows: classification.invalid_date_rows || 0,
        missing_team_rows: classification.missing_team_rows || 0,
        missing_score_rows: classification.missing_score_rows || 0,
        invalid_result_rows: classification.invalid_result_rows || 0,
        odds_preview_rows: classification.odds_preview_rows || 0,
        warnings: parserResult.warnings,
        errors: parserResult.errors,
        ...buildSafetyFlags(),
        non_execution_confirmations: buildNonExecutionConfirmations(),
        parser_non_execution_confirmations: parserResult.non_execution_confirmations,
    };
}

function runDryRun(args, dependencies = {}) {
    const cwd = dependencies.cwd || process.cwd();
    const readFileSync = dependencies.readFileSync || fs.readFileSync;
    const existsSync = dependencies.existsSync || fs.existsSync;
    const readManifest = dependencies.readManifest || readJsonFile;
    const parseCsv = dependencies.parseFootballDataCsv || parseFootballDataCsv;
    const pathContext = buildPathContext(args, cwd, existsSync);
    const inputFailure = validateDryRunInputs(args, cwd, pathContext);
    if (inputFailure) {
        return inputFailure;
    }

    const manifestPayload = loadManifestPayload(args, pathContext, readManifest);
    if (manifestPayload.errorPayload) {
        return manifestPayload.errorPayload;
    }

    const manifest = manifestPayload.manifest;
    const manifestValidation = validateManifest(manifest);
    const manifestFailure = buildManifestValidationPayload(args, manifestValidation);
    if (manifestFailure) {
        return manifestFailure;
    }

    const csvText = readFileSync(pathContext.localCsvPath, 'utf8');
    const integrityFields = buildIntegrityFields(manifest, csvText);
    const integrityFailure = buildIntegrityFailurePayload(args, integrityFields);
    if (integrityFailure) {
        return integrityFailure;
    }

    const parserResult = parseCsv(csvText, buildParserOptions(manifest));
    return buildSuccessPayload(args, manifest, parserResult, integrityFields);
}

function payloadToText(payload) {
    const lines = [
        `mode=${payload.mode}`,
        `ok=${payload.ok}`,
        `source_manifest_found=${payload.source_manifest_found}`,
        `local_csv_found=${payload.local_csv_found}`,
        `sha256_match=${payload.sha256_match}`,
        `row_count_match=${payload.row_count_match}`,
        `would_insert_matches=${payload.would_insert_matches}`,
        `would_insert_odds=${payload.would_insert_odds}`,
        `would_write_db=${payload.would_write_db}`,
        `would_access_network=${payload.would_access_network}`,
        `would_write_files=${payload.would_write_files}`,
    ];

    if (payload.blocked_reason) {
        lines.push(`blocked_reason=${payload.blocked_reason}`);
    }
    if (payload.parser_version) {
        lines.push(`parser_version=${payload.parser_version}`);
    }
    if (payload.total_rows !== undefined) {
        lines.push(`total_rows=${payload.total_rows}`);
        lines.push(`trainable_label_rows=${payload.trainable_label_rows}`);
        lines.push(`skipped_rows=${payload.skipped_rows}`);
        lines.push(`invalid_date_rows=${payload.invalid_date_rows}`);
        lines.push(`missing_score_rows=${payload.missing_score_rows}`);
        lines.push(`odds_preview_rows=${payload.odds_preview_rows}`);
    }
    if (payload.row_classification) {
        lines.push(`row_classification=${JSON.stringify(payload.row_classification)}`);
    }
    if (payload.candidate_preview) {
        lines.push(`candidate_preview=${JSON.stringify(payload.candidate_preview)}`);
    }
    if (Array.isArray(payload.errors) && payload.errors.length > 0) {
        lines.push(`errors=${payload.errors.join('; ')}`);
    }
    if (Array.isArray(payload.warnings) && payload.warnings.length > 0) {
        lines.push(`warnings=${JSON.stringify(payload.warnings)}`);
    }
    lines.push('non_execution_confirmations=');
    for (const confirmation of payload.non_execution_confirmations || []) {
        lines.push(`  ${confirmation}`);
    }

    return lines.join('\n');
}

function writePayload(payload, json, io) {
    const output = json ? `${JSON.stringify(payload, null, 2)}\n` : `${payloadToText(payload)}\n`;
    io.stdout(output);
}

function main(argv = process.argv.slice(2), io = {}) {
    const output = {
        stdout: io.stdout || (text => process.stdout.write(text)),
        stderr: io.stderr || (text => process.stderr.write(text)),
    };

    try {
        const args = parseArgs(argv);
        if (args.help) {
            output.stdout(`${usage()}\n`);
            return 0;
        }
        if (args.commit) {
            const payload = buildBlockedCommitPayload(args);
            writePayload(payload, args.json, output);
            return 1;
        }

        const payload = runDryRun(args);
        writePayload(payload, args.json, output);
        return payload.ok ? 0 : 1;
    } catch (error) {
        const payload = buildFailurePayload(
            {
                sourceManifest: '',
                localCsv: '',
            },
            {
                mode: 'argument-error',
                errors: [error.message],
            }
        );
        writePayload(payload, argv.includes('--json'), output);
        return 1;
    }
}

if (require.main === module) {
    process.exitCode = main();
}

module.exports = {
    DRY_RUN_VERSION,
    parseArgs,
    runDryRun,
    validateManifest,
    countCsvDataRows,
    sha256Text,
    buildNonExecutionConfirmations,
    main,
};
