#!/usr/bin/env node
'use strict';

// lifecycle: permanent；package.json 引用的唯一离线赔率 staging CLI，默认不写文件。

const { OfflineStagingError } = require('../../src/infrastructure/odds_staging/sourceManifest');
const { isStrictAbsoluteTimestamp } = require('../../src/infrastructure/odds_staging/contracts');
const {
    emitDeterministicResult,
    loadCandidatesForRun,
    runOfflineStaging,
} = require('../../src/infrastructure/odds_staging/pipeline');

const EXIT_CODES = Object.freeze({
    success: 0,
    input_error: 2,
    safety_boundary_error: 3,
    strict_quarantine: 4,
    unexpected_error: 5,
});

function usage() {
    return [
        'Usage:',
        '  npm run odds:staging:dry-run -- --source <absolute-local-file> --manifest <absolute-local-manifest.json> --adapter <football-data-csv|oddsportal-explicit-envelope-html> --candidates <absolute-local-candidates.json>',
        '',
        'Required:',
        '  --candidates <absolute-local-candidates.json>',
        '',
        'Optional:',
        '  --emit-dir <existing-absolute-directory-outside-repository>',
        '  --ingested-at <ISO-8601 with Z or numeric offset>',
        '  --strict',
        '',
        'Safety:',
        '  Default mode writes nothing and prints a summary only.',
        '  --emit-dir requires --ingested-at so emitted observation files are deterministic.',
        '  The HTML adapter accepts only a data-odds-staging="explicit" JSON envelope; it does not parse ordinary OddsPortal DOM.',
        '  Network URLs, browser execution, database access, and repository-local emit directories are rejected.',
        '',
        'Exit codes:',
        '  0 completed; inspect accepted_count and quarantine_count because completion does not mean every record was accepted.',
        '  2 manifest/input error; 3 safety boundary error; 4 strict mode found quarantine; 5 unexpected error.',
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
    const args = {
        source: '',
        manifest: '',
        adapter: '',
        candidates: '',
        emitDir: '',
        ingestedAt: '',
        strict: false,
        help: false,
    };
    const mapping = {
        '--source': 'source',
        '--manifest': 'manifest',
        '--adapter': 'adapter',
        '--candidates': 'candidates',
        '--emit-dir': 'emitDir',
        '--ingested-at': 'ingestedAt',
    };

    for (let index = 0; index < argv.length; index += 1) {
        const token = String(argv[index]);
        if (token === '--strict') {
            args.strict = true;
            continue;
        }
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
        for (const field of ['source', 'manifest', 'adapter', 'candidates']) {
            if (!args[field]) {
                throw new OfflineStagingError('INPUT_ERROR', `--${field} is required`);
            }
        }
        if (args.emitDir && !args.ingestedAt) {
            throw new OfflineStagingError(
                'INPUT_ERROR',
                '--ingested-at is required with --emit-dir for deterministic output'
            );
        }
        if (args.ingestedAt && !isStrictAbsoluteTimestamp(args.ingestedAt)) {
            throw new OfflineStagingError(
                'INPUT_ERROR',
                'ingested_at must be an ISO-8601 timestamp with Z or an explicit numeric offset'
            );
        }
    }
    return args;
}

function writeSummary(output, summary) {
    output(`${JSON.stringify(summary)}\n`);
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

        const candidates = loadCandidatesForRun(args.candidates, dependencies);
        const result = runOfflineStaging(
            {
                sourcePath: args.source,
                manifestPath: args.manifest,
                adapter: args.adapter,
                candidates,
                ingestedAt: args.ingestedAt || undefined,
            },
            dependencies
        );
        const emittedFiles = args.emitDir
            ? emitDeterministicResult(result, args.emitDir, { repositoryRoot: dependencies.repositoryRoot })
            : [];
        writeSummary(stdout, {
            ...result.summary,
            emitted_files: emittedFiles,
            strict: args.strict,
        });
        return args.strict && result.quarantine.length > 0 ? EXIT_CODES.strict_quarantine : EXIT_CODES.success;
    } catch (error) {
        const code = error instanceof OfflineStagingError ? error.code : 'UNEXPECTED_ERROR';
        stderr(`odds staging dry-run failed: ${error.message}\n`);
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
    EXIT_CODES,
    main,
    parseArgs,
    usage,
};
