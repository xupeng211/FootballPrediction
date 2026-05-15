#!/usr/bin/env node
'use strict';

const {
    HASH_STRATEGY_STABLE_RAW_PAYLOAD_V1,
    buildStableRawPayload,
    buildRawDataFromStablePayload,
    buildFetchMetadata,
    normalizeMatchId,
    sha256StableRawPayload,
    computeRawDetailHashes,
} = require('../../src/infrastructure/services/FotMobRawDetailFetcher');

function normalizeText(value) {
    return String(value || '').trim();
}

function normalizeBooleanFlag(value, fallback = undefined) {
    if (typeof value === 'boolean') return value;
    if (value === null || value === undefined || value === '') return fallback;
    const normalized = String(value).trim().toLowerCase();
    if (['1', 'true', 'yes', 'y', 'on'].includes(normalized)) return true;
    if (['0', 'false', 'no', 'n', 'off'].includes(normalized)) return false;
    return fallback;
}

function parseOptionValue(arg, argv, index) {
    if (arg.includes('=')) return { value: arg.slice(arg.indexOf('=') + 1), consumedNext: false };
    const nextArg = argv[index + 1];
    if (typeof nextArg === 'string' && !nextArg.startsWith('--')) return { value: nextArg, consumedNext: true };
    return { value: true, consumedNext: false };
}

function parseArgs(argv = process.argv.slice(2)) {
    const options = {
        source: null,
        externalId: null,
        homeTeam: null,
        awayTeam: null,
        allowNetwork: null,
        allowDbWrite: null,
        help: false,
        unknown: [],
    };
    const keyMap = {
        source: 'source',
        'external-id': 'externalId',
        external_id: 'externalId',
        'home-team': 'homeTeam',
        home_team: 'homeTeam',
        'away-team': 'awayTeam',
        away_team: 'awayTeam',
        'allow-network': 'allowNetwork',
        allow_network: 'allowNetwork',
        'allow-db-write': 'allowDbWrite',
        allow_db_write: 'allowDbWrite',
        help: 'help',
        h: 'help',
    };
    const booleanKeys = new Set(['allowNetwork', 'allowDbWrite', 'help']);

    for (let index = 0; index < argv.length; index += 1) {
        const arg = String(argv[index]);
        if (!arg.startsWith('--')) {
            options.unknown.push(arg);
            continue;
        }
        const rawKey = arg.replace(/^--/, '').split('=')[0];
        const optionKey = keyMap[rawKey];
        const { value, consumedNext } = parseOptionValue(arg, argv, index);
        if (consumedNext) index += 1;
        if (!optionKey) {
            options.unknown.push(rawKey);
            continue;
        }
        options[optionKey] = booleanKeys.has(optionKey) ? normalizeBooleanFlag(value, true) : value;
    }

    return options;
}

function validateArgs(input = {}) {
    const errors = [];
    const value = {
        source: normalizeText(input.source).toLowerCase(),
        externalId: normalizeText(input.externalId),
        homeTeam: normalizeText(input.homeTeam),
        awayTeam: normalizeText(input.awayTeam),
        allowNetwork: normalizeBooleanFlag(input.allowNetwork, false),
        allowDbWrite: normalizeBooleanFlag(input.allowDbWrite, false),
        unknown: Array.isArray(input.unknown) ? input.unknown : [],
    };

    if (value.unknown.length > 0) errors.push(`unknown arguments: ${value.unknown.join(', ')}`);
    if (value.source !== 'fotmob') errors.push('source must be fotmob');
    if (!/^\d+$/.test(value.externalId)) errors.push('external-id must be numeric');
    if (!value.homeTeam) errors.push('home-team is required');
    if (!value.awayTeam) errors.push('away-team is required');
    if (value.allowNetwork === true) errors.push('allow-network=yes is blocked in Phase 5.20L2D audit');
    if (value.allowDbWrite === true) errors.push('allow-db-write=yes is blocked in Phase 5.20L2D audit');

    return { ok: errors.length === 0, errors, value };
}

function buildAuditPayload(input = {}) {
    return {
        content: {
            stats: [{ title: 'Top stats', stats: [{ key: 'shotsOnTarget', home: 3, away: 5 }] }],
            lineup: {
                homeTeam: input.homeTeam,
                awayTeam: input.awayTeam,
            },
        },
        general: {
            homeTeam: { name: input.homeTeam },
            awayTeam: { name: input.awayTeam },
        },
        header: {
            teams: [{ name: input.homeTeam }, { name: input.awayTeam }],
        },
    };
}

function buildAuditMetadata(overrides = {}) {
    return buildFetchMetadata({
        requestedRoute: 'html_hydration',
        requestUrl: overrides.requestUrl || 'https://www.fotmob.com/match/4830747',
        finalUrl: overrides.finalUrl || 'https://www.fotmob.com/matches/auxerre-vs-nice/2sy6tc',
        httpStatus: overrides.httpStatus ?? 200,
        contentType: overrides.contentType || 'text/html; charset=utf-8',
        bodyByteLength: overrides.bodyByteLength ?? 123456,
        bodySha256: overrides.bodySha256 || 'body-sha-1',
        dataVersion: 'fotmob_html_hyd_v1',
        fetchedAt: overrides.fetchedAt || '2026-05-15T10:00:00.000Z',
        hasStats: true,
        hasLineup: true,
        hasShotmap: false,
        dataHash: overrides.dataHash || null,
        matchIdSource: overrides.matchIdSource || 'input_external_id_fallback',
    });
}

function runAudit(input = {}) {
    const validation = validateArgs(input);
    if (!validation.ok) {
        return {
            phase: 'PHASE5_20L2D_FOTMOB_RAW_DETAIL_HASH_STABILITY_AUDIT',
            ok: false,
            hash_strategy: HASH_STRATEGY_STABLE_RAW_PAYLOAD_V1,
            controlled_error: `INVALID_AUDIT_INPUT:${validation.errors.join('; ')}`,
        };
    }

    const value = validation.value;
    const payload = buildAuditPayload(value);
    const matchResolution = normalizeMatchId(payload, value, {
        requestUrl: 'https://www.fotmob.com/match/4830747',
        finalUrl: 'https://www.fotmob.com/matches/auxerre-vs-nice/2sy6tc',
    });
    const stableRawPayload = buildStableRawPayload(payload, value, {
        requestUrl: 'https://www.fotmob.com/match/4830747',
        finalUrl: 'https://www.fotmob.com/matches/auxerre-vs-nice/2sy6tc',
    });
    const stableHash = sha256StableRawPayload(stableRawPayload);

    const rawDataA = buildRawDataFromStablePayload(
        stableRawPayload,
        buildAuditMetadata({
            dataHash: stableHash,
            fetchedAt: '2026-05-15T10:00:00.000Z',
            bodySha256: 'body-sha-a',
            requestUrl: 'https://www.fotmob.com/match/4830747',
            finalUrl: 'https://www.fotmob.com/matches/auxerre-vs-nice/2sy6tc',
            matchIdSource: matchResolution.matchIdSource,
        })
    );
    const rawDataB = buildRawDataFromStablePayload(
        stableRawPayload,
        buildAuditMetadata({
            dataHash: stableHash,
            fetchedAt: '2026-05-15T10:05:00.000Z',
            bodySha256: 'body-sha-b',
            requestUrl: 'https://www.fotmob.com/match/4830747?ref=drift',
            finalUrl: 'https://www.fotmob.com/matches/auxerre-vs-nice/2sy6tc?tab=stats',
            httpStatus: 206,
            contentType: 'text/html; charset=iso-8859-1',
            bodyByteLength: 654321,
            matchIdSource: matchResolution.matchIdSource,
        })
    );
    const driftedStablePayload = JSON.parse(JSON.stringify(stableRawPayload));
    driftedStablePayload.content.stats[0].stats[0].home = 4;
    const rawDataDrift = buildRawDataFromStablePayload(
        driftedStablePayload,
        buildAuditMetadata({
            dataHash: sha256StableRawPayload(driftedStablePayload),
            matchIdSource: matchResolution.matchIdSource,
        })
    );

    const hashA = computeRawDetailHashes(stableRawPayload, rawDataA);
    const hashB = computeRawDetailHashes(stableRawPayload, rawDataB);
    const hashDrift = computeRawDetailHashes(driftedStablePayload, rawDataDrift);

    return {
        phase: 'PHASE5_20L2D_FOTMOB_RAW_DETAIL_HASH_STABILITY_AUDIT',
        ok: true,
        source: value.source,
        external_id: value.externalId,
        home_team: value.homeTeam,
        away_team: value.awayTeam,
        hash_strategy: HASH_STRATEGY_STABLE_RAW_PAYLOAD_V1,
        stable_raw_payload_hash_a: hashA.stable_raw_payload_hash,
        stable_raw_payload_hash_b: hashB.stable_raw_payload_hash,
        raw_data_with_meta_hash_a: hashA.raw_data_with_meta_hash,
        raw_data_with_meta_hash_b: hashB.raw_data_with_meta_hash,
        stable_hash_unchanged_when_meta_changes: hashA.stable_raw_payload_hash === hashB.stable_raw_payload_hash,
        raw_data_with_meta_hash_changes_when_meta_changes:
            hashA.raw_data_with_meta_hash !== hashB.raw_data_with_meta_hash,
        stable_hash_changes_when_payload_changes: hashA.stable_raw_payload_hash !== hashDrift.stable_raw_payload_hash,
        match_id_source: matchResolution.matchIdSource,
        match_id: stableRawPayload.matchId,
        metadata_hash_excluded_fields: hashA.metadata_hash_excluded_fields,
        full_html_body_stored: false,
        db_write_executed: false,
        network_used: false,
    };
}

function usage() {
    return [
        'Usage:',
        '  node scripts/ops/fotmob_raw_detail_hash_stability_audit.js \\',
        '    --source=fotmob --external-id=4830747 --home-team=Auxerre --away-team=Nice \\',
        '    --allow-network=no --allow-db-write=no',
        '',
        'Safety:',
        '  Phase 5.20L2D audit is local-only. No network. No DB write. No body save/print.',
    ].join('\n');
}

async function runCli(argv = process.argv.slice(2), io = {}) {
    const stdout = io.stdout || process.stdout.write.bind(process.stdout);
    const args = parseArgs(argv);
    if (args.help) {
        stdout(`${usage()}\n`);
        return 0;
    }
    const result = runAudit(args);
    stdout(`${JSON.stringify(result, null, 2)}\n`);
    return result.ok ? 0 : 1;
}

if (require.main === module) {
    runCli()
        .then(status => {
            process.exitCode = status;
        })
        .catch(error => {
            process.stdout.write(
                `${JSON.stringify(
                    {
                        phase: 'PHASE5_20L2D_FOTMOB_RAW_DETAIL_HASH_STABILITY_AUDIT',
                        ok: false,
                        controlled_error: String(error.message || error),
                    },
                    null,
                    2
                )}\n`
            );
            process.exitCode = 1;
        });
}

module.exports = {
    parseArgs,
    validateArgs,
    buildAuditPayload,
    buildAuditMetadata,
    runAudit,
    runCli,
};
