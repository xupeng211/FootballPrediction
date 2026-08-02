#!/usr/bin/env node
'use strict';

// lifecycle: permanent
// CLI entry point for the bounded, auditable FotMob detail capture
// pipeline (PLAN / CAPTURE / REPLAY).
//
// Default behavior is always safe:
//   - `help` or no subcommand prints usage and exits 0;
//   - PLAN is fully offline and requires explicit selection
//     (--season / --match-id / --limit);
//   - CAPTURE is off by default: every authorization gate must be passed
//     (--execute, CONFIRM_REAL_FOTMOB_DETAIL_CAPTURE=1, authorization id,
//     expected plan sha256, max-requests, CONFIRM_MAX_FOTMOB_REQUESTS);
//   - REPLAY is fully offline;
//   - nothing ever writes to the database.

const path = require('node:path');
const fs = require('node:fs');

const {
    buildDeterministicCapturePlan,
    writePlanDocument,
    verifyRepositoryExternalPath,
} = require('../../src/infrastructure/fotmob/FotMobDetailCapturePlan');

const {
    executeCaptureRun,
    validateAuthorizationBinding,
} = require('../../src/infrastructure/fotmob/FotMobDetailCapturePipeline');

const {
    replayCapturePair,
    writeDetailArtifact,
    readRunState,
    writeRunSummary,
    buildRunSummary,
} = require('../../src/infrastructure/fotmob/FotMobDetailCaptureRetention');

const NextDataParser = require('../../src/parsers/fotmob/NextDataParser');
const FotMobRawParser = require('../../src/parsers/fotmob/FotMobRawParser');

const USAGE = [
    'Usage:',
    '  node scripts/ops/fotmob_detail_capture.js plan \\',
    '    --candidate-artifact=/absolute/external/path/candidate-match-identity.v1.json \\',
    '    --season=2024/2025 \\',
    '    [--season=2023/2024 ...] [--match-id=<numeric> ...] \\',
    '    [--limit=<positive integer>] \\',
    '    --output=/absolute/external/path/plan.json',
    '',
    '  # CAPTURE — help/example only; never runs without every gate:',
    '  CONFIRM_REAL_FOTMOB_DETAIL_CAPTURE=1 \\',
    '  CONFIRM_MAX_FOTMOB_REQUESTS=3 \\',
    '  node scripts/ops/fotmob_detail_capture.js capture \\',
    '    --plan=/absolute/path/plan.json \\',
    '    --expected-plan-sha256=<64hex> \\',
    '    --authorization-id=<id> \\',
    '    --max-requests=3 \\',
    '    --delay-ms=60000 \\',
    '    --output-root=/absolute/external/path \\',
    '    --run-id=<plain-identifier, no slashes or dots-at-start> \\',
    '    --execute',
    '',
    '  node scripts/ops/fotmob_detail_capture.js replay \\',
    '    --run-dir=/absolute/external/path/runs/<run-id> \\',
    '    [--plan=/absolute/path/plan.json]',
    '',
    'Selection rules:',
    '  PLAN requires at least one of --season, --match-id, or --limit;',
    '  it never silently selects the full candidate population.',
    '  CAPTURE requires --execute plus the documented environment gates.',
    '  All outputs are written to repository-external absolute paths.',
].join('\n');

function parseArgs(argv) {
    const args = {};
    const positionals = [];
    for (let i = 0; i < argv.length; i += 1) {
        const token = argv[i];
        if (token === '--help' || token === '-h') {
            args.help = true;
            continue;
        }
        if (token.startsWith('--')) {
            const eq = token.indexOf('=');
            const rawKey = eq === -1 ? token.slice(2) : token.slice(2, eq);
            let value;
            if (eq !== -1) {
                value = token.slice(eq + 1);
            } else {
                // Space-separated value form: consume the next token when it
                // is not itself a flag.
                const next = argv[i + 1];
                if (next !== undefined && !next.startsWith('--')) {
                    value = next;
                    i += 1;
                } else {
                    value = true; // boolean flag
                }
            }
            if (rawKey === 'season' || rawKey === 'match-id') {
                if (!Array.isArray(args[rawKey])) args[rawKey] = [];
                args[rawKey].push(value);
            } else {
                args[rawKey] = value;
            }
        } else {
            positionals.push(token);
        }
    }
    return { args, positionals };
}

function fail(message) {
    process.stderr.write(`ERROR: ${message}\n`);
    process.exit(2);
}

/* eslint-disable-next-line complexity */
function runPlan(args, deps = {}) {
    const artifactPath = String(args['candidate-artifact'] || '').trim();
    const output = String(args.output || '').trim();
    const seasons = Array.isArray(args.season) ? args.season : (args.season ? [args.season] : []);
    const matchIds = Array.isArray(args['match-id']) ? args['match-id'] : (args['match-id'] ? [args['match-id']] : []);
    const limit = args.limit === undefined || args.limit === true ? null : Number(args.limit);

    if (!artifactPath) fail('--candidate-artifact is required');
    if (!output) fail('--output is required');
    if (args.limit === true || (limit !== null && (!Number.isInteger(limit) || limit < 1))) {
        fail('--limit must be a positive integer');
    }

    const fsImpl = deps.fsImpl || fs;
    const planResult = buildDeterministicCapturePlan({
        artifactPath,
        seasons,
        matchIds,
        limit,
        generatedAt: deps.now ? deps.now() : new Date().toISOString(),
        collectorCodeRevision: deps.collectorCodeRevision || '',
        fsImpl,
    });

    const written = writePlanDocument(planResult.plan, output, { fsImpl });
    const out = {
        mode: 'plan',
        selected_candidate_count: planResult.selectedCount,
        plan_business_sha256: planResult.planBusinessSha256,
        output_path: written.outputPath,
        written_sha256: written.writtenSha256,
    };
    (deps.stdout || process.stdout).write(JSON.stringify(out, null, 2) + '\n');
    return out;
}

/* eslint-disable-next-line complexity */
async function runCapture(args, deps = {}) {
    const planPath = String(args.plan || '').trim();
    const outputRoot = String(args['output-root'] || '').trim();
    const expectedPlanSha256 = String(args['expected-plan-sha256'] || '').trim();
    const authorizationId = String(args['authorization-id'] || '').trim();
    const maxRequests = Number(args['max-requests'] || 0);
    const delayMs = args['delay-ms'] === undefined ? undefined : Number(args['delay-ms']);
    const runId = String(args['run-id'] || '').trim();
    const execute = args.execute === true;

    if (!planPath) fail('--plan is required');
    if (!outputRoot) fail('--output-root is required');

    const fsImpl = deps.fsImpl || fs;
    if (!fsImpl.existsSync(planPath)) fail('--plan file does not exist');

    const plan = JSON.parse(fsImpl.readFileSync(planPath, 'utf8'));

    // The full authorization binding is validated before any network call.
    // When --execute is absent this throws SAFETY_ERROR → zero fetches.
    const binding = validateAuthorizationBinding({
        plan,
        planPath,
        expectedPlanSha256,
        authorizationId,
        maxRequests,
        outputRoot,
        runId,
        execute,
        networkAuthorization: execute === true,
        env: deps.env || process.env,
        repositoryRoot: deps.repositoryRoot,
        execSync: deps.execSync,
        fsImpl,
    });

    const result = await executeCaptureRun({
        plan,
        planPath,
        expectedPlanSha256,
        authorizationId,
        maxRequests,
        outputRoot,
        runId: binding.runId,
        execute,
        networkAuthorization: execute === true,
        delayMs,
        fetchImpl: deps.fetchImpl,
        parser: deps.parser || {
            extractFromHtml: NextDataParser.extractFromHtml,
            transformToApiFormat: NextDataParser.transformToApiFormat,
        },
        now: deps.now,
        env: deps.env || process.env,
        repositoryRoot: deps.repositoryRoot,
        execSync: deps.execSync,
        fsImpl,
    });

    const out = {
        mode: 'capture',
        run_id: result.runId,
        status: result.status,
        plan_sha256: result.planSha256,
        completed_count: result.completedCount,
        total_count: result.totalCount,
        stopped_at_ordinal: result.stoppedAtOrdinal,
        stop_reason: result.stopReason,
        network_requests_made: result.networkRequestsMade,
        run_dir: result.runDir,
    };
    (deps.stdout || process.stdout).write(JSON.stringify(out, null, 2) + '\n');
    return out;
}

/* eslint-disable-next-line complexity */
function runReplay(args, deps = {}) {
    const runDir = String(args['run-dir'] || '').trim();
    if (!runDir) fail('--run-dir is required');

    const fsImpl = deps.fsImpl || fs;
    const runState = readRunState(runDir, fsImpl);
    if (!runState) fail('run-state.json not found in --run-dir');

    const planPath = String(args.plan || '').trim();
    let plan = null;
    if (planPath) {
        if (!fsImpl.existsSync(planPath)) fail('--plan file does not exist');
        plan = JSON.parse(fsImpl.readFileSync(planPath, 'utf8'));
    }

    const capturesDir = path.join(runDir, 'captures');
    const replayDir = path.join(runDir, 'replay');
    if (!fsImpl.existsSync(capturesDir)) fail('captures directory not found');
    fsImpl.mkdirSync(replayDir, { recursive: true });

    const parser = deps.parser || {
        extractFromHtml: NextDataParser.extractFromHtml,
        transformToApiFormat: NextDataParser.transformToApiFormat,
        parseFotMobRaw: FotMobRawParser.parseFotMobRaw,
    };

    const ordinals = (Array.isArray(runState.completed_ordinals) ? runState.completed_ordinals : [])
        .map(Number)
        .sort((a, b) => a - b);
    const replayed = [];

    for (const ordinal of ordinals) {
        const files = fsImpl.readdirSync(capturesDir);
        const manifestFiles = files.filter(f => f.startsWith(`${ordinal}-`) && f.endsWith('.manifest.json'));
        if (manifestFiles.length !== 1) {
            throw Object.assign(
                new Error(`replay failed: expected exactly one manifest for ordinal ${ordinal}`),
                { code: 'SAFETY_ERROR' }
            );
        }
        const sourceMatchId = manifestFiles[0]
            .slice(`${ordinal}-`.length, -'.manifest.json'.length);

        const result = replayCapturePair({
            runDir,
            ordinal,
            sourceMatchId,
            plan,
            parser,
            parsedAt: deps.now ? deps.now() : new Date().toISOString(),
            parserCodeRevision: deps.parserCodeRevision || '',
            fsImpl,
        });
        const written = writeDetailArtifact({
            artifact: result.artifact,
            replayDir,
            ordinal,
            sourceMatchId,
            fsImpl,
        });
        replayed.push({
            ordinal,
            source_match_id: sourceMatchId,
            artifact_path: written.artifactPath,
            artifact_sha256: written.artifactSha256,
            structured_payload_sha256: result.artifact.structured_payload_sha256,
        });
    }

    const summary = buildRunSummary(
        runState,
        { selected_candidate_count: runState.completed_ordinals.length },
        ordinals
    );
    writeRunSummary(runDir, summary, fsImpl);

    const out = {
        mode: 'replay',
        run_id: runState.run_id,
        replayed_count: replayed.length,
        replayed,
        replay_dir: replayDir,
    };
    (deps.stdout || process.stdout).write(JSON.stringify(out, null, 2) + '\n');
    return out;
}

async function main(argv = process.argv.slice(2), deps = {}) {
    const { args, positionals } = parseArgs(argv);
    if (args.help || positionals.length === 0) {
        (deps.stdout || process.stdout).write(USAGE + '\n');
        return { mode: 'help' };
    }
    const subcommand = positionals[0];
    if (subcommand === 'plan') return runPlan(args, deps);
    if (subcommand === 'capture') return runCapture(args, deps);
    if (subcommand === 'replay') return runReplay(args, deps);
    fail(`unknown subcommand: ${subcommand}`);
    return null;
}

module.exports = { main, parseArgs, runPlan, runCapture, runReplay, USAGE };

if (require.main === module) {
    main().catch((err) => {
        process.stderr.write(`ERROR: ${err && err.message ? err.message : String(err)}\n`);
        const code = err && (err.code === 'INPUT_ERROR' || err.code === 'SAFETY_ERROR') ? 2 : 1;
        process.exit(code);
    });
}
