#!/usr/bin/env node
'use strict';

// lifecycle: permanent
// CLI entry point for the deterministic FotMob candidate exporter.
// Default mode prints summary only; --output writes validated candidates
// to a directory outside the Git repository.

const path = require('node:path');
const fs = require('node:fs');
const {
    exportCandidates,
    writeOutputFiles,
    buildOutputDocument,
    buildSummaryDocument,
    buildV2OutputDocument,
    buildV2SummaryDocument,
    verifyOutputPathSafety,
    canonicalizeRequestedSeasons,
    canonicalizeCompetition,
    canonicalizeLeagueId,
    canonicalizeLeagueSlug,
} = require('../../src/infrastructure/fotmob/FotMobCandidateExporter');

const CANONICAL_MAKE_TARGET = 'make data-fotmob-candidates-network-export';
const TRUE_LIKE_NETWORK_VALUES = new Set(['yes', 'true', '1', 'on']);
const FALSE_LIKE_NETWORK_VALUES = new Set(['no', 'false', '0', 'off']);

const USAGE = [
    'Usage:',
    '  npm run fotmob:candidates:export -- \\',
    '    --league-id 47 \\',
    '    --competition "Premier League" \\',
    '    --season 2022/2023 \\',
    '    --season 2023/2024 \\',
    '    --season 2024/2025 \\',
    '    --network-preview=true \\',
    '    --network-authorization=yes \\',
    '    [--slug premier-league] \\',
    '    [--output-schema=identity-v1|canonical-v2] \\',
    '    [--retain-raw-responses=/absolute/path/outside/repo/] \\',
    '    [--output /absolute/path/outside/repository/]',
    '',
    'Required:',
    '  --league-id     FotMob league id; must be a positive integer (e.g. 47 for Premier League)',
    '  --competition   Canonical competition name (e.g. "Premier League")',
    '  --season        Season string; repeat for each season.',
    '                  Accepted: YYYY/YYYY, YYYY-YYYY, YYYY/YY, YY/YY, YY-YY.',
    '                  Must represent a consecutive season (e.g. 2022/2023).',
    '                  Seasons must be consecutive and non-duplicate across repeats.',
    '  --network-preview=true',
    '                  Explicitly acknowledges that this command can make live network requests.',
    '  --network-authorization=yes',
    '                  Fresh explicit authorization for the live network request.',
    '',
    'Output schema:',
    '  --output-schema=identity-v1    Default. Produce candidate-match-identity/v1 artifact.',
    '  --output-schema=canonical-v2   Produce canonical-inventory-artifact/v2 artifact with',
    '                                 provider_status, status_mapping_version, and dual hashes.',
    '                                 REQUIRES --retain-raw-responses.',
    '',
    'Raw provenance retention:',
    '  --retain-raw-responses=<dir>   Absolute directory OUTSIDE the repository.',
    '                                 Saves the raw FotMob HTML response bytes per season',
    '                                 with a capture manifest. Required for canonical-v2.',
    '                                 Files are written atomically; existing identical files',
    '                                 are idempotent.',
    '',
    'Optional:',
    '  --slug          URL slug override; must be safe ASCII kebab-case (default: derived from competition name)',
    '  --output        Absolute output directory OUTSIDE the Git repository for the candidate artifact',
    '',
    'Safety:',
    `  Ordinary invocations are blocked. Use ${CANONICAL_MAKE_TARGET}.`,
    '  Both explicit network flags are required before any FotMob request.',
    '  This command does not write to the database.',
    '  --output requires an existing absolute directory outside the repository.',
    '  Network access is limited to FotMob league fixtures pages only.',
    '  Maximum 6 requests per invocation.',
    '',
    'Output files (--output-schema=identity-v1, when --output is used):',
    '  candidate-match-identity.v1.json          Full candidate document',
    '  candidate-match-identity.v1.summary.json  Counts, hashes, season stats',
    '',
    'Output files (--output-schema=canonical-v2, when --output is used):',
    '  canonical-inventory-artifact.v2.json          Full v2 artifact document',
    '  canonical-inventory-artifact.v2.summary.json  Dual hashes, counts, status coverage',
].join('\n');

/* eslint-disable-next-line complexity */
function parseArgs(argv) {
    const args = {
        leagueId: '',
        competition: '',
        seasons: [],
        slug: '',
        output: '',
        outputSchema: '',
        retainRawResponses: '',
        networkPreview: '',
        networkAuthorization: '',
        help: false,
    };

    for (let i = 0; i < argv.length; i += 1) {
        const token = argv[i];
        if (token === '--help' || token === '-h') {
            args.help = true;
            return args;
        }
        if (token === '--league-id') {
            args.leagueId = argv[i + 1];
            i += 1;
            continue;
        }
        if (token === '--competition') {
            args.competition = argv[i + 1];
            i += 1;
            continue;
        }
        if (token === '--season') {
            args.seasons.push(argv[i + 1]);
            i += 1;
            continue;
        }
        if (token === '--slug') {
            args.slug = argv[i + 1];
            i += 1;
            continue;
        }
        if (token === '--output') {
            args.output = argv[i + 1];
            i += 1;
            continue;
        }
        if (token === '--output-schema') {
            args.outputSchema = argv[i + 1];
            i += 1;
            continue;
        }
        if (typeof token === 'string' && token.startsWith('--output-schema=')) {
            args.outputSchema = token.slice('--output-schema='.length);
            continue;
        }
        if (token === '--retain-raw-responses') {
            args.retainRawResponses = argv[i + 1];
            i += 1;
            continue;
        }
        if (typeof token === 'string' && token.startsWith('--retain-raw-responses=')) {
            args.retainRawResponses = token.slice('--retain-raw-responses='.length);
            continue;
        }
        if (token === '--network-preview') {
            args.networkPreview = argv[i + 1];
            i += 1;
            continue;
        }
        if (typeof token === 'string' && token.startsWith('--network-preview=')) {
            args.networkPreview = token.slice('--network-preview='.length);
            continue;
        }
        if (token === '--network-authorization') {
            args.networkAuthorization = argv[i + 1];
            i += 1;
            continue;
        }
        if (typeof token === 'string' && token.startsWith('--network-authorization=')) {
            args.networkAuthorization = token.slice('--network-authorization='.length);
        }
    }

    return args;
}

function validateArgs(args) {
    const errors = [];
    if (!args.leagueId) errors.push('--league-id is required');
    if (args.leagueId) {
        try {
            canonicalizeLeagueId(args.leagueId);
        } catch (err) {
            errors.push(err.message);
        }
    }
    if (!args.competition) errors.push('--competition is required');
    if (args.competition) {
        try {
            canonicalizeCompetition(args.competition);
        } catch (err) {
            errors.push(err.message);
        }
    }

    // Validate a custom slug when one is provided (absent slug uses the
    // canonical competition-derived default and is not an error).
    if (args.slug) {
        try {
            canonicalizeLeagueSlug(args.slug);
        } catch (err) {
            errors.push(err.message);
        }
    }

    // Validate seasons via the core canonicaliser (no network access)
    try {
        const rawSeasons = args.seasons.length === 0 ? [] : args.seasons;
        canonicalizeRequestedSeasons(rawSeasons);
    } catch (err) {
        errors.push(err.message);
    }

    if (args.output) {
        if (!path.isAbsolute(args.output)) {
            errors.push('--output must be an absolute path');
        } else {
            try {
                verifyOutputPathSafety(args.output);
                if (!fs.existsSync(path.resolve(args.output))) {
                    errors.push('--output directory must already exist');
                }
            } catch (err) {
                errors.push(err.message);
            }
        }
    }
    return errors;
}

function normaliseNetworkAuthorizationValue(value) {
    if (typeof value !== 'string') return null;
    const normalized = value.trim().toLowerCase();
    if (TRUE_LIKE_NETWORK_VALUES.has(normalized)) return true;
    if (FALSE_LIKE_NETWORK_VALUES.has(normalized)) return false;
    return null;
}

function validateNetworkAuthorization(args) {
    const preview = normaliseNetworkAuthorizationValue(args.networkPreview);
    const authorization = normaliseNetworkAuthorizationValue(args.networkAuthorization);
    const errors = [];

    if (preview !== true) {
        errors.push('--network-preview=true is required for live FotMob requests');
    }
    if (authorization !== true) {
        errors.push('--network-authorization=yes is required for live FotMob requests');
    }
    if (errors.length > 0) {
        errors.push(`Use ${CANONICAL_MAKE_TARGET} for the canonical authorized entrypoint`);
    }

    return errors;
}

function writeInputErrors(stderr, errors) {
    for (const error of errors) stderr.write(`Error: ${error}\n`);
    stderr.write('\nUse --help for usage.\n');
}

function createExportOptions(args, deps) {
    const competition = canonicalizeCompetition(args.competition);
    const options = {
        leagueId: canonicalizeLeagueId(args.leagueId),
        competition,
        seasons: args.seasons,
        leagueSlug: canonicalizeLeagueSlug(args.slug || competition.toLowerCase().replace(/\s+/g, '-')),
        networkAuthorization: true,
        deps: deps.exporterDeps,
    };

    // Output schema
    if (args.outputSchema && args.outputSchema !== 'identity-v1') {
        options.outputSchema = args.outputSchema;
    }

    // Raw response retention
    if (args.retainRawResponses) {
        options.retainRawResponses = {
            outputDir: args.retainRawResponses,
            collectorComponent: 'FotMobCandidateExporter',
            collectorCodeRevision: deps.collectorCodeRevision || 'unknown',
        };
    }

    return options;
}

function hasIncompleteSeasons(result, stderr) {
    if (result.validation.all_seasons_complete) return false;

    stderr.write('\nWARNING: Not all seasons produced the expected fixture count.\n');
    for (const seasonResult of result.validation.season_results) {
        if (seasonResult.result !== 'complete') {
            stderr.write(`  ${seasonResult.season}: ${seasonResult.result} (${seasonResult.candidates} fixtures)\n`);
        }
    }
    return true;
}

function writeRequestedOutput(args, result, deps, stderr) {
    if (!args.output) return null;

    const isV2 = result.meta.schema_version === 'canonical-inventory-artifact/v2';

    try {
        if (isV2) {
            const candidatePath = path.join(args.output, 'canonical-inventory-artifact.v2.json');
            const summaryPath = path.join(args.output, 'canonical-inventory-artifact.v2.summary.json');
            const candidateDoc = buildV2OutputDocument(
                result.candidates,
                result.snapshot,
                result.meta,
                result.v2Snapshot
            );
            const summaryDoc = buildV2SummaryDocument(
                result.candidates,
                result.snapshot,
                result.meta,
                result.v2Snapshot
            );
            // Write atomically
            writeV2OutputFiles(args.output, candidateDoc, summaryDoc, deps);
            stderr.write(`Wrote ${candidatePath}\n`);
            stderr.write(`Wrote ${summaryPath}\n`);
        } else {
            const paths = writeOutputFiles(args.output, result.candidates, result.snapshot, result.meta, {
                repositoryRoot: deps.repositoryRoot,
            });
            stderr.write(`Wrote ${paths.candidatePath}\n`);
            stderr.write(`Wrote ${paths.summaryPath}\n`);
        }

        // Report raw retentions
        if (result.rawRetentions && result.rawRetentions.length > 0) {
            for (const retention of result.rawRetentions) {
                stderr.write(
                    `Retained raw: ${retention.rawFilePath} (SHA-256: ${retention.bodySha256}, ${retention.byteSize} bytes)\n`
                );
            }
        }

        return null;
    } catch (err) {
        stderr.write(`Output error: ${err.message}\n`);
        return 3;
    }
}

/**
 * Atomic write for v2 output files.
 */
function writeV2OutputFiles(outputDir, candidateDoc, summaryDoc, deps) {
    const fs = require('node:fs');
    verifyOutputPathSafety(outputDir, { repositoryRoot: deps.repositoryRoot });

    const candidatePath = path.join(outputDir, 'canonical-inventory-artifact.v2.json');
    const summaryPath = path.join(outputDir, 'canonical-inventory-artifact.v2.summary.json');

    const tempCandidate = candidatePath + '.tmp.' + Date.now();
    const tempSummary = summaryPath + '.tmp.' + Date.now();

    try {
        fs.writeFileSync(tempCandidate, JSON.stringify(candidateDoc, null, 2) + '\n', {
            encoding: 'utf8',
            flag: 'wx',
        });
        fs.writeFileSync(tempSummary, JSON.stringify(summaryDoc, null, 2) + '\n', {
            encoding: 'utf8',
            flag: 'wx',
        });
        fs.renameSync(tempCandidate, candidatePath);
        fs.renameSync(tempSummary, summaryPath);
    } catch (err) {
        try {
            fs.unlinkSync(tempCandidate);
        } catch (cleanupErr) {
            void cleanupErr;
        }
        try {
            fs.unlinkSync(tempSummary);
        } catch (cleanupErr) {
            void cleanupErr;
        }
        throw err;
    }
}

function exitCodeForError(err) {
    if (err.code === 'SAFETY_ERROR') return 3;
    if (err.code === 'INPUT_ERROR') return 2;
    return 5;
}

async function main(argv = process.argv.slice(2), deps = {}) {
    const stdout = deps.stdout || process.stdout;
    const stderr = deps.stderr || process.stderr;

    try {
        const args = parseArgs(argv);
        if (args.help) {
            stdout.write(USAGE + '\n');
            return 0;
        }

        const inputErrors = [...validateArgs(args), ...validateNetworkAuthorization(args)];
        if (inputErrors.length > 0) {
            writeInputErrors(stderr, inputErrors);
            return 2;
        }

        const runExporter = deps.exportCandidates || exportCandidates;
        const result = await runExporter(createExportOptions(args, deps));

        // Print summary
        const summaryDoc = buildSummaryDocument(result.candidates, result.snapshot, result.meta);
        stdout.write(JSON.stringify(summaryDoc, null, 2) + '\n');

        // Validate
        if (hasIncompleteSeasons(result, stderr)) return 3;

        // Output if requested
        const outputExitCode = writeRequestedOutput(args, result, deps, stderr);
        if (outputExitCode) return outputExitCode;

        stderr.write(
            `Total: ${result.validation.total_candidates} candidates, ` +
                `${result.validation.total_expected} expected, ` +
                `${result.meta.total_requests} requests\n`
        );
        stderr.write(`Business SHA-256: ${result.snapshot.business_content_sha256}\n`);
        if (result.v2Snapshot) {
            stderr.write(`V2 business hash: ${result.v2Snapshot.business_hash}\n`);
            stderr.write(`Identity projection hash: ${result.v2Snapshot.identity_projection_hash}\n`);
        }

        return 0;
    } catch (err) {
        stderr.write(`fotmob:candidates:export failed: ${err.message}\n`);
        return exitCodeForError(err);
    }
}

if (require.main === module) {
    main()
        .then(code => {
            process.exitCode = code;
        })
        .catch(() => {
            process.exitCode = 5;
        });
}

module.exports = {
    main,
    parseArgs,
    validateArgs,
    validateNetworkAuthorization,
    normaliseNetworkAuthorizationValue,
    createExportOptions,
    USAGE,
};
