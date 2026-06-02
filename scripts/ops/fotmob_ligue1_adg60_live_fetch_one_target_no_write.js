#!/usr/bin/env node
// lifecycle: one-shot-helper
// cleanup: archive/remove after ADG60 one-target live fetch no-write is merged
//
// WARNING: This helper is capable of performing a live network fetch to FotMob.
// The fetch is GUARDED: it requires the explicit CLI flag --execute-one-target-live-fetch.
// Without the flag, only preflight validation runs.
// Exactly ONE target, ONE request. No body persistence. No DB write. No browser automation.
'use strict';

const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');

const ROOT = path.resolve(__dirname, '../..');
const PHASE = 'ADG60-PAYLOAD-ACQUISITION-LIVE-FETCH-ONE-TARGET-NO-WRITE';
const NEXT_PHASE = 'ADG60-PAYLOAD-ACQUISITION-LIVE-FETCH-ONE-TARGET-NO-WRITE-REVIEW';
const OUT_MANIFEST = 'docs/_manifests/fotmob_ligue1_adg60_payload_acquisition_live_fetch_one_target_no_write.json';
const OUT_REPORT = 'docs/_reports/FOTMOB_LIGUE1_ADG60_PAYLOAD_ACQUISITION_LIVE_FETCH_ONE_TARGET_NO_WRITE.md';

const SOURCE_INPUTS = [
    'docs/_reports/FOTMOB_LIGUE1_ADG60_PREFLIGHT_NO_WRITE.md',
    'docs/_manifests/fotmob_ligue1_adg60_preflight_no_write.json',
    'docs/_reports/FOTMOB_LIGUE1_ADG60_RAW_PAYLOAD_SOURCE_INVENTORY.md',
    'docs/_manifests/fotmob_ligue1_adg60_raw_payload_source_inventory.json',
    'docs/_reports/FOTMOB_LIGUE1_ADG60_PAYLOAD_ACQUISITION_PLAN.md',
    'docs/_manifests/fotmob_ligue1_adg60_payload_acquisition_plan.json',
    'docs/_reports/FOTMOB_LIGUE1_ADG60_PAYLOAD_ACQUISITION_AUTHORIZATION_GATE.md',
    'docs/_manifests/fotmob_ligue1_adg60_payload_acquisition_authorization_gate.json',
    'docs/_reports/FOTMOB_LIGUE1_ADG60_PAYLOAD_ACQUISITION_DRY_RUN_NO_WRITE.md',
    'docs/_manifests/fotmob_ligue1_adg60_payload_acquisition_dry_run_no_write.json',
    'docs/_reports/FOTMOB_LIGUE1_ADG60_PAYLOAD_ACQUISITION_LIVE_FETCH_AUTHORIZATION.md',
    'docs/_manifests/fotmob_ligue1_adg60_payload_acquisition_live_fetch_authorization.json',
    'docs/_manifests/fotmob_ligue1_adg59b_source_controlled_acceptance_suspension_state.json',
    'docs/data/FOTMOB_CURRENT_STATE.md',
];

const FOTMOB_BASE = 'https://www.fotmob.com';
const REQUEST_TIMEOUT_MS = 20000;
const MAX_NETWORK_REQUESTS = 1;
const MAX_SELECTED_TARGETS = 1;

const STOP_CONDITIONS = [
    'target identity mismatch',
    'home/away orientation mismatch',
    'expected date mismatch',
    'competition mismatch',
    'missing corrected_hash_id',
    'missing route hash',
    'selected target count exceeded 1',
    'network request count would exceed 1',
    'output directory not clean',
    'body would be persisted',
    'DB write attempted',
    'raw_match_data insert attempted',
    'browser automation attempted in this PR',
    '403 / 429 / captcha / anti-bot / blocked response',
    'unexpected redirect',
    'unexpected schema / payload structure',
    'payload too large (> 5 MB)',
    'more targets than authorized batch',
    'any retry loop',
];

function absolutePath(relativePath) {
    return path.join(ROOT, relativePath);
}

function readText(relativePath) {
    return fs.readFileSync(absolutePath(relativePath), 'utf8');
}

function readJson(relativePath) {
    return JSON.parse(readText(relativePath));
}

function writeText(relativePath, value) {
    fs.writeFileSync(absolutePath(relativePath), value, 'utf8');
}

function writeJson(relativePath, value) {
    writeText(relativePath, `${JSON.stringify(value, null, 4)}\n`);
}

function sha256(buffer) {
    return crypto.createHash('sha256').update(buffer).digest('hex');
}

function parseArgs() {
    const args = process.argv.slice(2);
    const result = {
        executeLiveFetch: false,
        targetIndex: 1,
        unknown: [],
    };
    for (let i = 0; i < args.length; i++) {
        if (args[i] === '--execute-one-target-live-fetch') {
            result.executeLiveFetch = true;
        } else if (args[i] === '--target-index') {
            const val = parseInt(args[++i], 10);
            if (!isNaN(val) && val >= 1 && val <= 32) {
                result.targetIndex = val;
            } else {
                throw new Error(`Invalid --target-index: ${args[i]}. Must be 1-32.`);
            }
        } else {
            result.unknown.push(args[i]);
        }
    }
    return result;
}

function selectTarget(dryRunManifest, targetIndex) {
    const targets = dryRunManifest.dry_run_matrix;
    if (!targets || targets.length !== 32) {
        throw new Error('Dry-run matrix must have exactly 32 targets');
    }
    const target = targets.find(t => t.target_index === targetIndex);
    if (!target) {
        throw new Error(`Target index ${targetIndex} not found in dry-run matrix`);
    }
    if (target.identity_status !== 'accepted_suspension_resolved') {
        throw new Error(`Target ${targetIndex} not in accepted_suspension_resolved state`);
    }
    return target;
}

function buildUrl(target) {
    const routeHashPair = target.corrected_route_hash_pair;
    if (!routeHashPair) {
        throw new Error(`Target ${target.target_index} missing corrected_route_hash_pair`);
    }
    const parts = routeHashPair.split('#');
    if (parts.length !== 2) {
        throw new Error(`Invalid route_hash_pair format: ${routeHashPair}`);
    }
    const routeHash = parts[0];
    const matchId = parts[1];
    return {
        url: `${FOTMOB_BASE}/matches/${routeHash}/${matchId}`,
        routeHash,
        matchId,
        routeHashPair,
    };
}

function runPreflight({ target, urlInfo, args }) {
    const checks = [];
    const failures = [];

    // Scope checks
    checks.push({ name: 'exactly_one_target_selected', pass: true });
    checks.push({ name: 'target_count_total_32', pass: true });

    // Identity checks
    checks.push({ name: 'expected_home_exists', pass: Boolean(target.expected_home) });
    checks.push({ name: 'expected_away_exists', pass: Boolean(target.expected_away) });
    checks.push({ name: 'expected_date_exists', pass: Boolean(target.expected_date) });
    checks.push({ name: 'competition_exists', pass: Boolean(target.competition) });
    checks.push({ name: 'corrected_hash_id_exists', pass: Boolean(target.corrected_hash_id) });
    checks.push({ name: 'corrected_route_hash_pair_exists', pass: Boolean(target.corrected_route_hash_pair) });
    checks.push({ name: 'url_constructed', pass: Boolean(urlInfo.url) });

    // Safety checks
    checks.push({ name: 'browser_automation_allowed', pass: false, note: 'browser automation not allowed in this PR' });
    checks.push({ name: 'payload_body_persistence_allowed', pass: false, note: 'body persistence not allowed in this PR' });
    checks.push({ name: 'db_write_allowed', pass: false, note: 'DB write not allowed' });
    checks.push({ name: 'raw_write_allowed', pass: false, note: 'raw write not allowed' });
    checks.push({ name: 'raw_match_data_insert_allowed', pass: false, note: 'raw_match_data insert not allowed' });
    checks.push({ name: 'adg60_write_allowed', pass: false, note: 'ADG60 write not allowed' });

    const identityFailures = checks.filter(c => {
        if (c.name.startsWith('browser_') || c.name.startsWith('payload_') ||
            c.name.startsWith('db_') || c.name.startsWith('raw_') || c.name.startsWith('adg60_')) {
            return c.pass === true; // these should be false
        }
        return !c.pass;
    }).map(c => c.name);

    if (identityFailures.length > 0) {
        for (const name of identityFailures) {
            failures.push(`preflight identity/safety failure: ${name}`);
        }
    }

    return {
        passed: failures.length === 0,
        checks,
        failures,
        selected_target_count: 1,
        target_count_total: 32,
        execute_live_fetch_requested: args.executeLiveFetch,
    };
}

function buildStopResult(httpStatus, finalUrl, contentType, stopReason, extra) {
    return {
        requestPerformed: true, requestCount: 1, httpStatus,
        redirected: extra.redirected || false,
        redirectLocation: extra.redirectLocation || undefined,
        finalUrl, contentType, stopped: true, stopReason,
        bodyPersisted: false, bodyLogged: false, bodyCommitted: false,
        error: extra.error || undefined,
    };
}

function detectSchemaFlags(buffer) {
    const bodyText = buffer.toString('utf8');
    const hasNextData = bodyText.includes('__NEXT_DATA__');
    const hasPageProps = bodyText.includes('"pageProps"');
    const hasProps = bodyText.includes('"props"');
    const looksLikeJson = bodyText.trim().startsWith('{') || bodyText.trim().startsWith('[');
    const looksLikeHtml = /<(!doctype|html|head|body|script)/i.test(bodyText.substring(0, 500));
    const hasMatchDetails = bodyText.includes('"matchDetails"') || bodyText.includes('"match"');
    const hasGeneral = bodyText.includes('"general"');
    const hasContent = bodyText.includes('"content"');
    const hasTeamColorsPageProps = bodyText.includes('"teamColors"');
    const payloadLike = hasNextData || hasPageProps || (looksLikeJson && hasMatchDetails);
    return {
        payloadLike,
        minimalSchemaFlags: {
            hasNextDataMarker: hasNextData, hasPagePropsMarker: hasPageProps,
            hasPropsMarker: hasProps, looksLikeJson, looksLikeHtml,
            hasMatchDetails, hasGeneral, hasContent, hasTeamColorsPageProps,
        },
    };
}

async function executeLiveFetch(urlInfo) {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);

    let response;
    let error = null;

    try {
        response = await fetch(urlInfo.url, {
            method: 'GET',
            redirect: 'manual',
            signal: controller.signal,
            headers: {
                'User-Agent': 'FootballPrediction/4.51.2 (data-pipeline; ADG60-one-target-no-write)',
                'Accept': 'text/html,application/json,*/*',
            },
        });
    } catch (e) {
        error = { type: e.name, message: e.message };
    } finally {
        clearTimeout(timeoutId);
    }

    if (error) {
        return buildStopResult(null, urlInfo.url, 'unknown',
            `Network error: ${error.type} - ${error.message}`, { error });
    }

    const httpStatus = response.status;
    const redirected = httpStatus >= 300 && httpStatus < 400;
    const finalUrl = response.url;
    const contentType = response.headers.get('content-type') || 'unknown';

    if (httpStatus === 403 || httpStatus === 429 || httpStatus >= 500) {
        return buildStopResult(httpStatus, finalUrl, contentType,
            `HTTP ${httpStatus} - blocked or error response`, { redirected });
    }

    if (redirected) {
        const location = response.headers.get('location') || 'unknown';
        return buildStopResult(httpStatus, finalUrl, contentType,
            `HTTP ${httpStatus} redirect to: ${location}. Redirect not followed per policy.`,
            { redirected: true, redirectLocation: location });
    }

    // Read body into memory transiently — compute metadata only, never persist
    try {
        const arrayBuffer = await response.arrayBuffer();
        const buffer = Buffer.from(arrayBuffer);
        const byteSize = buffer.length;

        if (byteSize > 5 * 1024 * 1024) {
            return {
                requestPerformed: true, requestCount: 1, httpStatus,
                redirected: false, finalUrl, contentType, byteSize,
                bodySha256: 'not-computed-body-too-large',
                payloadLike: false,
                minimalSchemaFlags: { bodyTooLarge: true },
                stopped: true, stopReason: 'Payload too large (> 5 MB)',
                bodyPersisted: false, bodyLogged: false, bodyCommitted: false,
            };
        }

        const bodySha256 = sha256(buffer);
        const { payloadLike, minimalSchemaFlags } = detectSchemaFlags(buffer);

        // IMMEDIATELY discard body — never persist
        return {
            requestPerformed: true, requestCount: 1, httpStatus,
            redirected: false, finalUrl, contentType, byteSize,
            bodySha256, payloadLike, minimalSchemaFlags,
            stopped: false, stopReason: null,
            bodyPersisted: false, bodyLogged: false, bodyCommitted: false,
        };
    } catch (e) {
        return buildStopResult(httpStatus, finalUrl, contentType,
            `Body read error: ${e.message}`, { error: { type: 'body_read_error', message: e.message } });
    }
}

function buildManifest({ generatedAt, target, urlInfo, preflight, executionResult, args }) {
    const requestPerformed = executionResult ? executionResult.requestPerformed : false;
    const networkPerformed = requestPerformed;

    return {
        schema_version: 'adg60_payload_acquisition_live_fetch_one_target_no_write_v1',
        lifecycle: 'phase-artifact',
        phase: PHASE,
        generated_at: generatedAt,
        source_inputs: SOURCE_INPUTS,
        selected_target: {
            target_index: target.target_index,
            target_match_id: target.target_match_id,
            expected_home: target.expected_home,
            expected_away: target.expected_away,
            expected_date: target.expected_date,
            competition: target.competition,
            corrected_hash_id: target.corrected_hash_id,
            corrected_route_hash_pair: target.corrected_route_hash_pair,
            selected_reason: `Default first target (smallest target_index=${target.target_index}) from dry-run matrix`,
            preflight_identity_status: target.identity_status,
            preflight_route_status: target.corrected_route_hash_pair ? 'route_hash_pair_available' : 'missing',
        },
        request_policy: {
            method: 'GET',
            url: urlInfo.url,
            route_hash: urlInfo.routeHash,
            match_id: urlInfo.matchId,
            max_network_requests: MAX_NETWORK_REQUESTS,
            max_selected_targets: MAX_SELECTED_TARGETS,
            timeout_ms: REQUEST_TIMEOUT_MS,
            redirect: 'manual',
            browser_automation: false,
            retry: false,
            parallelism: false,
            body_persistence: false,
            execute_flag_required: '--execute-one-target-live-fetch',
        },
        preflight_checks: {
            passed: preflight.passed,
            checks: preflight.checks,
            selected_target_count: preflight.selected_target_count,
            target_count_total: preflight.target_count_total,
            execute_live_fetch_requested: args.executeLiveFetch,
        },
        execution_result: executionResult || {
            requestPerformed: false,
            requestCount: 0,
            stopReason: 'Live fetch not requested. Use --execute-one-target-live-fetch to perform the fetch.',
            bodyPersisted: false,
            bodyLogged: false,
            bodyCommitted: false,
        },
        safety: {
            live_fetch_performed: requestPerformed,
            network_fetch_performed: networkPerformed,
            browser_automation_performed: false,
            payload_saved: false,
            response_body_saved: false,
            acquisition_execution_performed: requestPerformed,
            db_write_performed: false,
            raw_write_performed: false,
            raw_match_data_insert_performed: false,
            schema_migration_performed: false,
            adg60_write_performed: false,
            raw_write_ready_marked: false,
        },
        live_fetch_performed: requestPerformed,
        network_fetch_performed: networkPerformed,
        browser_automation_performed: false,
        payload_saved: false,
        response_body_saved: false,
        acquisition_execution_performed: requestPerformed,
        db_write_performed: false,
        raw_write_performed: false,
        raw_match_data_insert_performed: false,
        schema_migration_performed: false,
        adg60_write_performed: false,
        raw_write_ready_marked: false,
        recommended_next_phase: NEXT_PHASE,
        next_phase_boundary: 'Review the one-target live fetch result before any further target. No automatic progression to next target. DB/raw/raw_match_data writes remain prohibited.',
        stop_conditions: STOP_CONDITIONS,
    };
}

function fmtHeader(manifest) {
    const pc = manifest.preflight_checks;
    return [
        '<!-- markdownlint-disable MD013 -->',
        '',
        '# FotMob Ligue 1 ADG60 Payload Acquisition Live Fetch One Target No Write',
        '',
        '- lifecycle: phase-artifact',
        `- phase: ${manifest.phase}`,
        '- scope: one target live fetch, no write',
        '- based_on: ADG60 preflight no-write; ADG60 raw payload source inventory; ADG60 payload acquisition plan; ADG60 authorization gate; ADG60 dry-run no-write; ADG60 live-fetch authorization',
        `- target_count: ${pc.target_count_total}`,
        `- selected_target_count: ${pc.selected_target_count}`,
        '- no response body persisted',
        '- no DB write', '- no raw write', '- no raw_match_data insert',
        '- no schema migration', '- no ADG60 write',
    ];
}

function fmtTarget(t) {
    return [
        '', '## Selected Target', '',
        `- target_index: ${t.target_index}`,
        `- target_match_id: ${t.target_match_id}`,
        `- expected_home: ${t.expected_home}`,
        `- expected_away: ${t.expected_away}`,
        `- expected_date: ${t.expected_date}`,
        `- competition: ${t.competition}`,
        `- corrected_hash_id: ${t.corrected_hash_id}`,
        `- corrected_route_hash_pair: ${t.corrected_route_hash_pair}`,
        `- selected_reason: ${t.selected_reason}`,
        `- preflight_identity_status: ${t.preflight_identity_status}`,
        `- preflight_route_status: ${t.preflight_route_status}`,
    ];
}

function fmtPreflight(pc) {
    const lines = [
        '', '## Preflight Result', '',
        `- preflight_passed: ${pc.passed}`,
        `- execute_live_fetch_requested: ${pc.execute_live_fetch_requested}`,
    ];
    if (pc.checks && pc.checks.length > 0) {
        lines.push('');
        lines.push('| Check | Pass | Note |');
        lines.push('| --- | --- | --- |');
        for (const c of pc.checks) {
            lines.push(`| ${c.name} | ${c.pass} | ${c.note || ''} |`);
        }
    }
    return lines;
}

function fmtRequestPolicy(rp) {
    return [
        '', '## Request Policy', '',
        `- method: ${rp.method}`,
        `- url: <${rp.url}>`,
        `- route_hash: ${rp.route_hash}`,
        `- match_id: ${rp.matchId}`,
        `- max_network_requests: ${rp.max_network_requests}`,
        `- timeout_ms: ${rp.timeout_ms}`,
        `- redirect: ${rp.redirect}`,
        `- browser_automation: ${rp.browser_automation}`,
        `- retry: ${rp.retry}`,
        `- parallelism: ${rp.parallelism}`,
        `- body_persistence: ${rp.body_persistence}`,
        '',
    ];
}

function fmtSchemaFlags(flags) {
    if (!flags || Object.keys(flags).length === 0) return [];
    const lines = ['', '### Minimal Schema Flags', ''];
    for (const [flag, value] of Object.entries(flags)) {
        lines.push(`- ${flag}: ${value}`);
    }
    return lines;
}

function fmtExecPerformed(er) {
    const lines = [
        `- http_status: ${er.httpStatus}`,
        `- final_url: <${er.finalUrl || 'N/A'}>`,
        `- redirected: ${er.redirected || false}`,
    ];
    if (er.redirectLocation) lines.push(`- redirect_location: <${er.redirectLocation}>`);
    lines.push(`- content_type: ${er.contentType || 'N/A'}`);
    lines.push(`- byte_size: ${er.byteSize !== undefined ? er.byteSize : 'N/A'}`);
    lines.push(`- sha256: ${er.bodySha256 || 'N/A'}`);
    lines.push(`- payload_like: ${er.payloadLike !== undefined ? er.payloadLike : 'N/A'}`);
    lines.push(...fmtSchemaFlags(er.minimalSchemaFlags));
    if (er.stopped) {
        lines.push(`- stopped: ${er.stopped}`, `- stop_reason: ${er.stopReason}`);
    }
    if (er.error) lines.push(`- error: ${JSON.stringify(er.error)}`);
    lines.push(`- body_persisted: ${er.bodyPersisted !== undefined ? er.bodyPersisted : false}`);
    lines.push(`- body_logged: ${er.bodyLogged !== undefined ? er.bodyLogged : false}`);
    lines.push(`- body_committed: ${er.bodyCommitted !== undefined ? er.bodyCommitted : false}`);
    return lines;
}

function fmtExecNotPerformed(er) {
    return [`- stop_reason: ${er.stopReason || 'Live fetch not requested'}`];
}

function fmtExecution(er) {
    const lines = ['## Execution Result', '', `- request_performed: ${er.requestPerformed || false}`, `- request_count: ${er.requestCount || 0}`];
    if (er.requestPerformed) {
        lines.push(...fmtExecPerformed(er));
    } else {
        lines.push(...fmtExecNotPerformed(er));
    }
    return lines;
}

function fmtSafety(m) {
    return [
        '', '## Safety', '',
        `- live_fetch_performed: ${m.live_fetch_performed}`,
        `- network_fetch_performed: ${m.network_fetch_performed}`,
        `- browser_automation_performed: ${m.browser_automation_performed}`,
        `- payload_saved: ${m.payload_saved}`,
        `- response_body_saved: ${m.response_body_saved}`,
        `- acquisition_execution_performed: ${m.acquisition_execution_performed}`,
        `- db_write_performed: ${m.db_write_performed}`,
        `- raw_write_performed: ${m.raw_write_performed}`,
        `- raw_match_data_insert_performed: ${m.raw_match_data_insert_performed}`,
        `- schema_migration_performed: ${m.schema_migration_performed}`,
        `- adg60_write_performed: ${m.adg60_write_performed}`,
        `- raw_write_ready_marked: ${m.raw_write_ready_marked}`,
    ];
}

function fmtStopConditions(sc) {
    const lines = ['', '## Stop Conditions', ''];
    for (const cond of sc) lines.push(`- ${cond}`);
    return lines;
}

function fmtNextPhase(m) {
    return [
        '', '## Recommended Next Phase', '',
        `- recommended next phase: ${m.recommended_next_phase}`,
        '- Review the one-target live fetch result before any further target.',
        '- No automatic progression to next target.',
        '- DB/raw/raw_match_data writes remain prohibited.',
        '- If body was not persisted, next phase still requires separate body persistence authorization.',
    ];
}

function formatReport(manifest) {
    const lines = [].concat(
        fmtHeader(manifest),
        fmtTarget(manifest.selected_target),
        fmtPreflight(manifest.preflight_checks),
        fmtRequestPolicy(manifest.request_policy),
        fmtExecution(manifest.execution_result),
        fmtSafety(manifest),
        fmtStopConditions(manifest.stop_conditions),
        fmtNextPhase(manifest),
    );
    return `${lines.join('\n')}\n`;
}

async function main() {
    const args = parseArgs();
    const generatedAt = new Date().toISOString();

    // Read inputs
    const dryRunManifest = readJson('docs/_manifests/fotmob_ligue1_adg60_payload_acquisition_dry_run_no_write.json');
    const authManifest = readJson('docs/_manifests/fotmob_ligue1_adg60_payload_acquisition_live_fetch_authorization.json');

    // Validate authorization boundary
    if (authManifest.batch_policy.initial_batch_size !== 1) {
        throw new Error('Authorization contract requires initial_batch_size=1');
    }
    if (authManifest.batch_policy.max_batch_size_before_review > 3) {
        throw new Error('Authorization contract max batch size exceeded');
    }

    // Select target
    const target = selectTarget(dryRunManifest, args.targetIndex);

    // Build URL
    const urlInfo = buildUrl(target);

    // Preflight
    const preflight = runPreflight({ target, urlInfo, args });
    if (!preflight.passed) {
        const manifest = buildManifest({ generatedAt, target, urlInfo, preflight, executionResult: null, args });
        writeJson(OUT_MANIFEST, manifest);
        writeText(OUT_REPORT, formatReport(manifest));
        console.log(JSON.stringify({
            phase: manifest.phase,
            selected_target: `${target.target_match_id} (${target.expected_home} vs ${target.expected_away})`,
            preflight_passed: false,
            preflight_failures: preflight.failures,
            live_fetch_performed: false,
            network_fetch_performed: false,
            recommended_next_phase: manifest.recommended_next_phase,
        }, null, 2));
        process.exit(1);
    }

    // Execute or skip
    let executionResult = null;

    if (args.executeLiveFetch) {
        console.error(`[LIVE-FETCH] Executing live fetch for target_index=${target.target_index}: ${target.expected_home} vs ${target.expected_away}`);
        console.error(`[LIVE-FETCH] URL: ${urlInfo.url}`);
        console.error(`[LIVE-FETCH] This will perform exactly 1 network request. No body will be persisted.`);

        executionResult = await executeLiveFetch(urlInfo);

        if (executionResult.requestPerformed) {
            console.error(`[LIVE-FETCH] Request performed. HTTP ${executionResult.httpStatus}, size=${executionResult.byteSize}, sha256=${executionResult.bodySha256 ? executionResult.bodySha256.substring(0, 16) + '...' : 'N/A'}`);
            if (executionResult.stopped) {
                console.error(`[LIVE-FETCH] STOPPED: ${executionResult.stopReason}`);
            }
        }
    } else {
        console.error('[PREFLIGHT-ONLY] Live fetch not requested. Use --execute-one-target-live-fetch to execute.');
        console.error(`[PREFLIGHT-ONLY] Would fetch URL: ${urlInfo.url}`);
    }

    // Build and write output
    const manifest = buildManifest({ generatedAt, target, urlInfo, preflight, executionResult, args });
    writeJson(OUT_MANIFEST, manifest);
    writeText(OUT_REPORT, formatReport(manifest));

    console.log(JSON.stringify({
        phase: manifest.phase,
        selected_target: `${target.target_match_id} (${target.expected_home} vs ${target.expected_away})`,
        preflight_passed: preflight.passed,
        request_performed: manifest.live_fetch_performed,
        request_count: executionResult ? executionResult.requestCount : 0,
        http_status: executionResult ? executionResult.httpStatus : null,
        byte_size: executionResult ? executionResult.byteSize : null,
        payload_like: executionResult ? executionResult.payloadLike : null,
        body_persisted: executionResult ? executionResult.bodyPersisted : false,
        db_write_performed: false,
        raw_write_ready_marked: false,
        recommended_next_phase: manifest.recommended_next_phase,
    }, null, 2));
}

if (require.main === module) {
    main().catch(err => {
        console.error(`FATAL: ${err.message}`);
        process.exit(1);
    });
}

module.exports = {
    NEXT_PHASE,
    selectTarget,
    buildUrl,
    runPreflight,
    buildManifest,
    formatReport,
    executeLiveFetch,
    parseArgs,
};
