#!/usr/bin/env node
'use strict';

// lifecycle: permanent
// CLI entry point for the bounded, auditable FotMob detail capture
// pipeline (PLAN / PREFLIGHT / CAPTURE / REPLAY).
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
    resolveGitRevision,
} = require('../../src/infrastructure/fotmob/FotMobDetailCapturePipeline');

const {
    replayCapturePair,
    writeDetailArtifact,
    readRunState,
    readPlanSnapshot,
    writeRunSummary,
    buildRunSummary,
} = require('../../src/infrastructure/fotmob/FotMobDetailCaptureRetention');

const {
    validateAndRecomputeCapturePlan,
    readAndValidateCandidateArtifact,
} = require('../../src/infrastructure/fotmob/FotMobDetailCaptureContract');

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
    '  node scripts/ops/fotmob_detail_capture.js preflight \\',
    '    --plan=/absolute/path/plan.json \\',
    '    --expected-plan-sha256=<64hex> \\',
    '    --authorization-id=<id> \\',
    '    --max-requests=3 \\',
    '    --output-root=/absolute/external/path \\',
    '    --run-id=<plain-identifier, no slashes or dots-at-start>',
    '    # fully offline: validates plan + authorization gates, prints the',
    '    # candidate count and URL summary; creates nothing, fetches nothing.',
    '',
    '  # CAPTURE — canonical entrypoint is make data-fotmob-detail-capture-execute;',
    '  # the direct Node CLI below is the internal engine and never runs without',
    '  # every gate:',
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
    '    [--plan=/absolute/path/plan.json]   # optional; must match run snapshot',
    '',
    'Selection rules:',
    '  PLAN requires at least one of --season, --match-id, or --limit;',
    '  it never silently selects the full candidate population.',
    '  CAPTURE requires --execute plus the documented environment gates.',
    '  REPLAY is fully offline and binds identity to the run plan snapshot.',
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

    // Input errors surface BEFORE any git interaction: explicit selection
    // and artifact schema are validated exactly like the plan builder does,
    // so a missing selection or an unknown artifact schema is reported as
    // such even when the worktree is dirty (the git revision binding only
    // applies to plans that would otherwise build successfully).
    const hasSeasonFilter = seasons.length > 0;
    const hasMatchIdFilter = matchIds.length > 0;
    if (!hasSeasonFilter && !hasMatchIdFilter && limit === null) {
        fail('explicit selection required: provide --season, --match-id, or --limit');
    }
    const artifactCheck = readAndValidateCandidateArtifact(artifactPath, fsImpl);
    if (!artifactCheck.ok) {
        fail(`candidate artifact validation failed: ${artifactCheck.errors.join('; ')}`);
    }

    // The plan is bound to the generating git revision (clean worktree,
    // full 40-hex HEAD) so the generator revision inside the plan is always
    // a verified repository state.
    const collectorCodeRevision = resolveGitRevision({
        repositoryRoot: deps.repositoryRoot,
        execSync: deps.execSync,
    });
    const planResult = buildDeterministicCapturePlan({
        artifactPath,
        seasons,
        matchIds,
        limit,
        generatedAt: deps.now ? deps.now() : new Date().toISOString(),
        collectorCodeRevision,
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

/**
 * PREFLIGHT — fully offline gate validation.
 * Re-validates the plan (schema + recomputed business hash), every
 * authorization gate that does not require --execute (git revision,
 * output root, run id, budget, authorization variables), and prints the
 * candidate count and URL-path summary. Creates NO run directory, writes
 * NO capture payload, and calls NO fetch.
 */
function runPreflight(args, deps = {}) {
    const planPath = String(args.plan || '').trim();
    const outputRoot = String(args['output-root'] || '').trim();
    const expectedPlanSha256 = String(args['expected-plan-sha256'] || '').trim();
    const authorizationId = String(args['authorization-id'] || '').trim();
    const maxRequests = Number(args['max-requests'] || 0);
    const runId = String(args['run-id'] || '').trim();

    if (!planPath) fail('--plan is required');
    if (!outputRoot) fail('--output-root is required');

    const fsImpl = deps.fsImpl || fs;
    if (!fsImpl.existsSync(planPath)) fail('--plan file does not exist');

    const plan = JSON.parse(fsImpl.readFileSync(planPath, 'utf8'));

    // The full plan re-validation + recomputation runs first (P1-2): a
    // tampered plan is rejected with zero side effects.
    const planCheck = validateAndRecomputeCapturePlan(plan);
    if (!planCheck.ok) {
        fail(`plan validation failed: ${planCheck.errors.join('; ')}`);
    }
    if (planCheck.recomputed_sha256 !== expectedPlanSha256) {
        fail('recomputed plan SHA-256 does not match --expected-plan-sha256');
    }

    // Authorization gate validation WITHOUT --execute: git revision,
    // paths, run id, budget and authorization variables must all be ready
    // before the operator can proceed to the execute target. The
    // execute-only confirmations (--execute, networkAuthorization,
    // CONFIRM_* env vars) are skipped by requireExecute: false.
    validateAuthorizationBinding({
        plan,
        planPath,
        expectedPlanSha256,
        authorizationId,
        maxRequests,
        outputRoot,
        runId,
        execute: false,
        networkAuthorization: false,
        requireExecute: false,
        env: deps.env || process.env,
        repositoryRoot: deps.repositoryRoot,
        execSync: deps.execSync,
        fsImpl,
    });

    const summary = {
        mode: 'preflight',
        plan_sha256: planCheck.recomputed_sha256,
        selected_candidate_count: plan.candidates.length,
        request_urls: plan.candidates.map(c => `/match/${c.source_match_id}`),
        execution_ready: true,
    };
    (deps.stdout || process.stdout).write(JSON.stringify(summary, null, 2) + '\n');
    return summary;
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
            parseFotMobRaw: FotMobRawParser.parseFotMobRaw,
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
    if (!runDir) {
        throw Object.assign(new Error('--run-dir is required'), { code: 'SAFETY_ERROR' });
    }

    const fsImpl = deps.fsImpl || fs;
    const runState = readRunState(runDir, fsImpl);
    if (!runState) {
        throw Object.assign(new Error('run-state.json not found in --run-dir'), { code: 'SAFETY_ERROR' });
    }

    // The run-bound plan snapshot is REQUIRED for replay identity (P2-6):
    // replay never guesses identity from file names and never emits empty
    // candidate identity.
    const runPlan = readPlanSnapshot(runDir, fsImpl);
    if (!runPlan) {
        throw Object.assign(
            new Error('run plan snapshot (run-dir/plan.json) not found in --run-dir'),
            { code: 'SAFETY_ERROR' }
        );
    }
    // The run state must be bound to the SAME plan as the snapshot (Codex
    // re-review P2): a snapshot from another valid plan mixed into this run
    // directory must fail closed before any artifact is materialized.
    if (String(runState.plan_sha256 || '') !== String(runPlan.plan_business_sha256 || '')) {
        throw Object.assign(
            new Error('run state plan SHA does not match the run plan snapshot'),
            { code: 'SAFETY_ERROR' }
        );
    }

    const planPath = String(args.plan || '').trim();
    if (planPath) {
        if (!fsImpl.existsSync(planPath)) {
            throw Object.assign(new Error('--plan file does not exist'), { code: 'SAFETY_ERROR' });
        }
        const externalPlan = JSON.parse(fsImpl.readFileSync(planPath, 'utf8'));
        // An external --plan may only serve as an additional comparison: it
        // must match the run snapshot's plan SHA exactly.
        if (String(externalPlan.plan_business_sha256 || '') !== runPlan.plan_business_sha256) {
            throw Object.assign(
                new Error('--plan does not match the run plan snapshot'),
                { code: 'SAFETY_ERROR' }
            );
        }
    }

    const capturesDir = path.join(runDir, 'captures');
    const replayDir = path.join(runDir, 'replay');
    if (!fsImpl.existsSync(capturesDir)) {
        throw Object.assign(new Error('captures directory not found'), { code: 'SAFETY_ERROR' });
    }

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

        // Fully offline and deterministic: identity from the run snapshot,
        // parsed_at derived from the capture record — no wall clock.
        // The parser code revision comes from the BOUND collector revision
        // chain (R3-P2-3): the run plan snapshot's generator_code_revision
        // and the run state's collector_code_revision must agree (the
        // capture gate requires both to equal the HEAD that ran the
        // capture). A chain mismatch fails closed — replay never writes an
        // empty or unverifiable revision (Codex re-review P2).
        const planRevision = String(runPlan.generator_code_revision || '');
        const runStateRevision = String(runState.collector_code_revision || '');
        const parserCodeRevision = planRevision || runStateRevision || String(deps.parserCodeRevision || '');
        if (!/^[0-9a-f]{40}$/.test(parserCodeRevision)) {
            throw Object.assign(
                new Error('replay failed: parser code revision must be 40-hex from the run plan snapshot'),
                { code: 'SAFETY_ERROR' }
            );
        }
        if (planRevision && runStateRevision && planRevision !== runStateRevision) {
            throw Object.assign(
                new Error(
                    'replay failed: collector revision chain mismatch — ' +
                    `plan snapshot generator_code_revision ${planRevision} vs run state collector_code_revision ${runStateRevision}`
                ),
                { code: 'SAFETY_ERROR' }
            );
        }
        // R3-P2-2: every replayed pair must be bound to THIS run state —
        // a pair captured under another run id / authorization id is
        // REPLAY_PAIR_CONTEXT_MISMATCH and fails closed before any artifact
        // or summary write.
        const result = replayCapturePair({
            runDir,
            ordinal,
            sourceMatchId,
            runPlan,
            parserCodeRevision,
            expectedRunId: String(runState.run_id || ''),
            expectedAuthorizationId: String(runState.authorization_id || ''),
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
    if (subcommand === 'preflight') return runPreflight(args, deps);
    if (subcommand === 'capture') return runCapture(args, deps);
    if (subcommand === 'replay') return runReplay(args, deps);
    fail(`unknown subcommand: ${subcommand}`);
    return null;
}

module.exports = { main, parseArgs, runPlan, runPreflight, runCapture, runReplay, USAGE };

if (require.main === module) {
    main().catch((err) => {
        process.stderr.write(`ERROR: ${err && err.message ? err.message : String(err)}\n`);
        const code = err && (err.code === 'INPUT_ERROR' || err.code === 'SAFETY_ERROR') ? 2 : 1;
        process.exit(code);
    });
}
