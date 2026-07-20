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
    verifyOutputPathSafety,
    canonicalizeRequestedSeasons,
} = require('../../src/infrastructure/fotmob/FotMobCandidateExporter');

const USAGE = [
    'Usage:',
    '  npm run fotmob:candidates:export -- \\',
    '    --league-id 47 \\',
    '    --competition "Premier League" \\',
    '    --season 2022/2023 \\',
    '    --season 2023/2024 \\',
    '    --season 2024/2025 \\',
    '    [--slug premier-league] \\',
    '    [--output /absolute/path/outside/repository/]',
    '',
    'Required:',
    '  --league-id     FotMob league id (e.g. 47 for Premier League)',
    '  --competition   Canonical competition name (e.g. "Premier League")',
    '  --season        Season string; repeat for each season.',
    '                  Accepted: YYYY/YYYY, YYYY-YYYY, YYYY/YY, YY/YY, YY-YY.',
    '                  Must represent a consecutive season (e.g. 2022/2023).',
    '                  Seasons must be consecutive and non-duplicate across repeats.',
    '',
    'Optional:',
    '  --slug          URL slug override (default: derived from competition name)',
    '  --output        Absolute output directory OUTSIDE the Git repository',
    '',
    'Safety:',
    '  Default mode writes nothing to disk and prints a summary only.',
    '  --output requires an existing absolute directory outside the repository.',
    '  Network access is limited to FotMob league fixtures pages only.',
    '  Maximum 6 requests per invocation.',
    '',
    'Output files (when --output is used):',
    '  candidate-match-identity.v1.json          Full candidate document',
    '  candidate-match-identity.v1.summary.json  Counts, hashes, season stats',
].join('\n');

function parseArgs(argv) {
    const args = {
        leagueId: '',
        competition: '',
        seasons: [],
        slug: '',
        output: '',
        help: false,
    };

    for (let i = 0; i < argv.length; i += 1) {
        const token = String(argv[i]);
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
    }

    return args;
}

function validateArgs(args) {
    const errors = [];
    if (!args.leagueId) errors.push('--league-id is required');
    if (!args.competition) errors.push('--competition is required');

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

async function main(argv = process.argv.slice(2), deps = {}) {
    const stdout = deps.stdout || process.stdout;
    const stderr = deps.stderr || process.stderr;

    try {
        const args = parseArgs(argv);
        if (args.help) {
            stdout.write(USAGE + '\n');
            return 0;
        }

        const argErrors = validateArgs(args);
        if (argErrors.length > 0) {
            for (const e of argErrors) stderr.write(`Error: ${e}\n`);
            stderr.write('\nUse --help for usage.\n');
            return 2;
        }

        const opts = {
            leagueId: args.leagueId,
            competition: args.competition,
            seasons: args.seasons,
            leagueSlug: args.slug || args.competition.toLowerCase().replace(/\s+/g, '-'),
        };

        const result = await exportCandidates(opts);

        // Print summary
        const summaryDoc = buildSummaryDocument(result.candidates, result.snapshot, result.meta);
        stdout.write(JSON.stringify(summaryDoc, null, 2) + '\n');

        // Validate
        if (!result.validation.all_seasons_complete) {
            stderr.write('\nWARNING: Not all seasons produced the expected fixture count.\n');
            for (const sr of result.validation.season_results) {
                if (sr.result !== 'complete') {
                    stderr.write(`  ${sr.season}: ${sr.result} (${sr.candidates} fixtures)\n`);
                }
            }
            return 3;
        }

        // Output if requested
        if (args.output) {
            try {
                const paths = writeOutputFiles(args.output, result.candidates, result.snapshot, result.meta, {
                    repositoryRoot: deps.repositoryRoot,
                });
                stderr.write(`Wrote ${paths.candidatePath}\n`);
                stderr.write(`Wrote ${paths.summaryPath}\n`);
            } catch (err) {
                stderr.write(`Output error: ${err.message}\n`);
                return 3;
            }
        }

        stderr.write(
            `Total: ${result.validation.total_candidates} candidates, ` +
                `${result.validation.total_expected} expected, ` +
                `${result.meta.total_requests} requests\n`
        );
        stderr.write(`Business SHA-256: ${result.snapshot.business_content_sha256}\n`);

        return 0;
    } catch (err) {
        stderr.write(`fotmob:candidates:export failed: ${err.message}\n`);
        if (err.code === 'SAFETY_ERROR') return 3;
        if (err.code === 'INPUT_ERROR') return 2;
        return 5;
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

module.exports = { main, parseArgs, validateArgs, USAGE };
