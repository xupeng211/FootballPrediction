#!/usr/bin/env node
/* eslint-disable complexity, max-lines, max-statements */
'use strict';

const {
    listJsonPaths,
    summarizeJsonShape,
    detectBlockOrErrorMarkers,
} = require('./raw_match_data_completeness_fidelity_audit');

const PHASE = 'PHASE5_21L2O_PAGEPROPS_V2_RAW_COMPLETENESS_AUDIT';
const SOURCE = 'fotmob';
const TABLE = 'raw_match_data';
const DATA_VERSION = 'fotmob_pageprops_v2';
const SEEDED_TARGETS = Object.freeze([
    { externalId: '4830746', matchId: '53_20252026_4830746' },
    { externalId: '4830747', matchId: '53_20252026_4830747' },
    { externalId: '4830748', matchId: '53_20252026_4830748' },
    { externalId: '4830750', matchId: '53_20252026_4830750' },
    { externalId: '4830751', matchId: '53_20252026_4830751' },
    { externalId: '4830752', matchId: '53_20252026_4830752' },
    { externalId: '4830753', matchId: '53_20252026_4830753' },
    { externalId: '4830754', matchId: '53_20252026_4830754' },
]);
const EXPECTED_TARGET_EXTERNAL_IDS = Object.freeze(SEEDED_TARGETS.map(target => target.externalId));
const EXPECTED_MATCH_IDS = Object.freeze(SEEDED_TARGETS.map(target => target.matchId));
const EXPECTED_ROW_COUNTS = Object.freeze({
    matches: 10,
    raw_match_data: 18,
    bookmaker_odds_history: 2,
    l3_features: 2,
    match_features_training: 2,
    predictions: 2,
});
const EXPECTED_DISTRIBUTION = Object.freeze({
    'PHASE4.23': 1,
    'PHASE4.43_SYNTHETIC': 1,
    fotmob_html_hyd_v1: 8,
    fotmob_pageprops_v2: 8,
});
const MODULE_PATHS = Object.freeze([
    'content',
    'content.lineup',
    'content.matchFacts',
    'content.playerStats',
    'content.shotmap',
    'content.stats',
    'content.h2h',
    'content.table',
    'content.momentum',
    'seo',
    'seo.eventJSONLD',
    'seo.breadcrumbJSONLD',
    'fallback',
    'translations',
    'header',
    'general',
    'nav',
    'ongoing',
    'ssr',
    'fetchingLeagueData',
    'hasPendingVAR',
]);
const CORE_MODULE_PATHS = Object.freeze([
    'content',
    'content.lineup',
    'content.matchFacts',
    'content.playerStats',
    'content.shotmap',
    'content.stats',
    'content.h2h',
    'content.table',
    'content.momentum',
    'seo',
    'fallback',
    'translations',
    'header',
    'general',
    'nav',
]);
const OPTIONAL_MODULE_PATHS = Object.freeze(MODULE_PATHS.filter(modulePath => !CORE_MODULE_PATHS.includes(modulePath)));
const REQUIRED_NO_FLAGS = Object.freeze([
    'allowDbWrite',
    'allowNetwork',
    'allowParserFeatures',
    'allowTraining',
    'allowPrediction',
    'printFullRawData',
    'saveFullRawData',
]);
const BLOCKED_TRUE_FLAGS = Object.freeze([
    'execute',
    'commit',
    'touchFotmob',
    'liveRequest',
    'allowRawMatchDataWrite',
    'allowSchemaMigration',
    'allowMatchesWrite',
    'printFullJson',
    'saveFullJson',
]);
const PARTIAL_PATH_SAMPLE_LIMIT = 25;
const COMMON_PATH_SAMPLE_LIMIT = 25;
const MISSING_PATH_SAMPLE_LIMIT = 25;
const MARKER_SAMPLE_LIMIT = 25;

function normalizeText(value) {
    return String(value ?? '').trim();
}

function isPlainObject(value) {
    return value !== null && typeof value === 'object' && !Array.isArray(value);
}

function objectOrEmpty(value) {
    return isPlainObject(value) ? value : {};
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
        table: null,
        targetExternalIds: null,
        dataVersion: null,
        allowDbWrite: null,
        allowNetwork: null,
        allowParserFeatures: null,
        allowTraining: null,
        allowPrediction: null,
        printFullRawData: null,
        saveFullRawData: null,
        execute: false,
        commit: false,
        touchFotmob: false,
        liveRequest: false,
        allowRawMatchDataWrite: false,
        allowSchemaMigration: false,
        allowMatchesWrite: false,
        printFullJson: false,
        saveFullJson: false,
        help: false,
        unknown: [],
    };
    const keyMap = {
        source: 'source',
        table: 'table',
        'target-external-ids': 'targetExternalIds',
        target_external_ids: 'targetExternalIds',
        'data-version': 'dataVersion',
        data_version: 'dataVersion',
        'allow-db-write': 'allowDbWrite',
        allow_db_write: 'allowDbWrite',
        'allow-network': 'allowNetwork',
        allow_network: 'allowNetwork',
        'allow-parser-features': 'allowParserFeatures',
        allow_parser_features: 'allowParserFeatures',
        'allow-training': 'allowTraining',
        allow_training: 'allowTraining',
        'allow-prediction': 'allowPrediction',
        allow_prediction: 'allowPrediction',
        'print-full-raw-data': 'printFullRawData',
        print_full_raw_data: 'printFullRawData',
        'save-full-raw-data': 'saveFullRawData',
        save_full_raw_data: 'saveFullRawData',
        execute: 'execute',
        commit: 'commit',
        'touch-fotmob': 'touchFotmob',
        touch_fotmob: 'touchFotmob',
        'live-request': 'liveRequest',
        live_request: 'liveRequest',
        'allow-raw-match-data-write': 'allowRawMatchDataWrite',
        allow_raw_match_data_write: 'allowRawMatchDataWrite',
        'allow-schema-migration': 'allowSchemaMigration',
        allow_schema_migration: 'allowSchemaMigration',
        'allow-matches-write': 'allowMatchesWrite',
        allow_matches_write: 'allowMatchesWrite',
        'print-full-json': 'printFullJson',
        print_full_json: 'printFullJson',
        'save-full-json': 'saveFullJson',
        save_full_json: 'saveFullJson',
        help: 'help',
        h: 'help',
    };
    const booleanKeys = new Set([
        'allowDbWrite',
        'allowNetwork',
        'allowParserFeatures',
        'allowTraining',
        'allowPrediction',
        'printFullRawData',
        'saveFullRawData',
        'execute',
        'commit',
        'touchFotmob',
        'liveRequest',
        'allowRawMatchDataWrite',
        'allowSchemaMigration',
        'allowMatchesWrite',
        'printFullJson',
        'saveFullJson',
        'help',
    ]);

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

function arraysEqual(left = [], right = []) {
    if (left.length !== right.length) return false;
    return left.every((value, index) => value === right[index]);
}

function parseTargetExternalIds(rawValue) {
    const rawText = normalizeText(rawValue);
    if (!rawText) {
        return {
            ok: false,
            errors: ['missing target-external-ids'],
            ids: [],
        };
    }
    const ids = rawText
        .split(',')
        .map(item => normalizeText(item))
        .filter(Boolean);
    const errors = [];
    if (!arraysEqual(ids, EXPECTED_TARGET_EXTERNAL_IDS)) {
        errors.push(`target-external-ids must be exactly ${EXPECTED_TARGET_EXTERNAL_IDS.join(',')}`);
    }
    return {
        ok: errors.length === 0,
        errors,
        ids,
    };
}

function validateAuditInput(input = {}) {
    const errors = [];
    const source = normalizeText(input.source).toLowerCase();
    const table = normalizeText(input.table);
    const dataVersion = normalizeText(input.dataVersion);
    const parsedTargetIds = parseTargetExternalIds(input.targetExternalIds);

    if (Array.isArray(input.unknown) && input.unknown.length > 0) {
        errors.push(`unknown arguments: ${input.unknown.join(', ')}`);
    }

    if (!source) {
        errors.push('missing source=fotmob');
    } else if (source !== SOURCE) {
        errors.push('source must be fotmob');
    }
    if (!table) {
        errors.push('missing table=raw_match_data');
    } else if (table !== TABLE) {
        errors.push('table must be raw_match_data');
    }
    if (!dataVersion) {
        errors.push('missing data-version=fotmob_pageprops_v2');
    } else if (dataVersion !== DATA_VERSION) {
        errors.push('data-version must be fotmob_pageprops_v2');
    }

    errors.push(...parsedTargetIds.errors);

    for (const flagName of REQUIRED_NO_FLAGS) {
        const normalizedValue = normalizeBooleanFlag(input[flagName]);
        const cliName = flagName.replace(/[A-Z]/g, match => `-${match.toLowerCase()}`);
        if (normalizedValue === true) {
            errors.push(`${cliName}=yes is blocked`);
            continue;
        }
        if (normalizedValue !== false) {
            errors.push(`${cliName}=no is required`);
        }
    }

    for (const flagName of BLOCKED_TRUE_FLAGS) {
        if (normalizeBooleanFlag(input[flagName]) === true) {
            const cliName = flagName.replace(/[A-Z]/g, match => `-${match.toLowerCase()}`);
            errors.push(`${cliName}=yes is blocked`);
        }
    }

    return {
        ok: errors.length === 0,
        errors,
        value: {
            source,
            table,
            dataVersion,
            targetExternalIds: parsedTargetIds.ids,
        },
    };
}

function readPath(value, dottedPath) {
    const parts = normalizeText(dottedPath).split('.').filter(Boolean);
    let cursor = value;
    for (const part of parts) {
        if (!isPlainObject(cursor) || !Object.prototype.hasOwnProperty.call(cursor, part)) return undefined;
        cursor = cursor[part];
    }
    return cursor;
}

function hasPath(value, dottedPath) {
    return readPath(value, dottedPath) !== undefined;
}

function countNulls(value) {
    let nullCount = 0;

    function walk(node) {
        if (node === null) {
            nullCount += 1;
            return;
        }
        if (Array.isArray(node)) {
            for (const item of node) walk(item);
            return;
        }
        if (isPlainObject(node)) {
            for (const child of Object.values(node)) walk(child);
        }
    }

    walk(value);
    return nullCount;
}

function summarizeTopLevelKeys(value) {
    if (!isPlainObject(value)) return [];
    return Object.keys(value).sort();
}

function summarizePagePropsShape(pageProps) {
    const base = summarizeJsonShape(pageProps);
    return {
        path_count: base.distinct_path_count,
        leaf_path_count: base.leaf_path_count,
        max_depth: base.max_depth,
        scalar_count: base.scalar_count,
        object_count: base.object_count,
        array_count: base.array_count,
        null_count: countNulls(pageProps),
    };
}

function flattenTextEntries(value, currentPath = '') {
    const entries = [];
    if (Array.isArray(value)) {
        value.forEach((item, index) => {
            entries.push(...flattenTextEntries(item, currentPath ? `${currentPath}[${index}]` : `[${index}]`));
        });
        return entries;
    }
    if (isPlainObject(value)) {
        for (const [key, child] of Object.entries(value)) {
            entries.push({ path: currentPath, key: key.toLowerCase(), value: '' });
            entries.push(...flattenTextEntries(child, currentPath ? `${currentPath}.${key}` : key));
        }
        return entries;
    }
    entries.push({
        path: currentPath,
        key: '',
        value: normalizeText(value).toLowerCase(),
    });
    return entries;
}

function detectSuspiciousMarkers(pageProps) {
    const baseMarkers = detectBlockOrErrorMarkers(pageProps);
    const entries = flattenTextEntries(pageProps);
    const markerNames = new Set();

    if (baseMarkers.has_error_key) markerNames.add('error_key');
    if (baseMarkers.has_captcha_marker) markerNames.add('captcha');
    if (baseMarkers.has_block_marker) markerNames.add('blocked_or_forbidden');
    if (baseMarkers.has_placeholder_only_shape) markerNames.add('placeholder_only_shape');

    for (const entry of entries) {
        const value = entry.value;
        if (!value) continue;
        if (value.includes('cloudflare')) markerNames.add('cloudflare');
        if (value.includes('access denied')) markerNames.add('access_denied');
        if (value.includes('forbidden') || value.includes('http_403')) markerNames.add('forbidden');
        if (value.includes('turnstile') || value.includes('captcha')) markerNames.add('captcha');
        if (value.includes('not found') || value === '404' || value.includes('http_404')) markerNames.add('not_found');
        if (value.includes('placeholder')) markerNames.add('placeholder');
        if (
            value.includes('you have been blocked') ||
            value.includes('request blocked') ||
            value.includes('temporarily blocked')
        ) {
            markerNames.add('blocked');
        }
    }

    return {
        ...baseMarkers,
        marker_names: [...markerNames].sort(),
    };
}

function extractTeamName(teamValue) {
    if (typeof teamValue === 'string') return normalizeText(teamValue);
    if (isPlainObject(teamValue)) return normalizeText(teamValue.name || teamValue.shortName || teamValue.id);
    return '';
}

function buildModulePresence(pageProps) {
    const presence = {};
    for (const modulePath of MODULE_PATHS) {
        presence[modulePath] = hasPath(pageProps, modulePath);
    }
    return presence;
}

function resolveCoverageTier(modulePresence) {
    const missingCoreModules = CORE_MODULE_PATHS.filter(modulePath => modulePresence[modulePath] !== true);
    if (missingCoreModules.length > 0) return 'seeded_pageprops_v2_incomplete';
    const missingOptionalModules = OPTIONAL_MODULE_PATHS.filter(modulePath => modulePresence[modulePath] !== true);
    if (missingOptionalModules.length > 0) return 'seeded_pageprops_v2_partial_coverage';
    return 'seeded_pageprops_v2_high_coverage';
}

function distribution(values = []) {
    const safe = values.filter(Number.isFinite).sort((left, right) => left - right);
    if (safe.length === 0) return { min: null, max: null, median: null };
    const middle = Math.floor(safe.length / 2);
    const median = safe.length % 2 === 1 ? safe[middle] : (safe[middle - 1] + safe[middle]) / 2;
    return {
        min: safe[0],
        max: safe[safe.length - 1],
        median,
    };
}

function detectSchema(constraints = []) {
    const definitions = (Array.isArray(constraints) ? constraints : []).map(row => normalizeText(row.definition));
    return {
        raw_match_data_match_id_data_version_key_present: (constraints || []).some(
            row => normalizeText(row.conname) === 'raw_match_data_match_id_data_version_key'
        ),
        raw_match_data_match_id_key_absent: !(constraints || []).some(
            row => normalizeText(row.conname) === 'raw_match_data_match_id_key'
        ),
        unique_match_id_data_version: definitions.includes('UNIQUE (match_id, data_version)'),
        unique_match_id_only: definitions.includes('UNIQUE (match_id)'),
    };
}

function buildRowCountsSummary(rows = []) {
    const counts = {};
    for (const row of rows) {
        counts[normalizeText(row.table_name)] = Number(row.rows);
    }
    return counts;
}

function buildDistributionSummary(rows = []) {
    const summary = {};
    for (const row of rows) {
        summary[normalizeText(row.data_version)] = Number(row.rows);
    }
    return summary;
}

function formatCoverageCount(count, total) {
    return `${count}/${total}`;
}

function buildModuleCoverage(perTarget = []) {
    const coverage = {};
    const missingExternalIds = {};
    const total = perTarget.length;
    for (const modulePath of MODULE_PATHS) {
        const count = perTarget.filter(
            target => target.row_found && target.module_presence[modulePath] === true
        ).length;
        coverage[modulePath] = formatCoverageCount(count, total);
        missingExternalIds[modulePath] = perTarget
            .filter(target => !target.row_found || target.module_presence[modulePath] !== true)
            .map(target => target.external_id);
    }
    return {
        coverage,
        missingExternalIds,
    };
}

function buildPathCoverage(perTarget = []) {
    const pathSets = perTarget.map(target => new Set(target.pageprops_paths || []));
    const unionPaths = new Set();
    for (const pathSet of pathSets) {
        for (const path of pathSet) unionPaths.add(path);
    }

    const commonPaths = [];
    const partialPaths = [];
    for (const path of unionPaths) {
        const presentInExternalIds = perTarget
            .filter((target, index) => pathSets[index].has(path))
            .map(target => target.external_id);
        const missingExternalIds = perTarget
            .filter((target, index) => !pathSets[index].has(path))
            .map(target => target.external_id);
        if (presentInExternalIds.length === perTarget.length) {
            commonPaths.push(path);
        } else {
            partialPaths.push({
                path,
                present_in_count: presentInExternalIds.length,
                present_in_external_ids: presentInExternalIds,
                missing_in_external_ids: missingExternalIds,
            });
        }
    }

    const missingByTargetSamples = perTarget.map((target, index) => {
        const missingPaths = [...unionPaths].filter(path => !pathSets[index].has(path)).sort();
        return {
            external_id: target.external_id,
            match_id: target.match_id,
            missing_path_count: missingPaths.length,
            missing_paths_sample: missingPaths.slice(0, MISSING_PATH_SAMPLE_LIMIT),
        };
    });

    return {
        common_paths_count: commonPaths.length,
        partial_paths_count: partialPaths.length,
        unique_paths_count: unionPaths.size,
        common_path_samples: commonPaths.sort().slice(0, COMMON_PATH_SAMPLE_LIMIT),
        partial_path_samples: partialPaths
            .sort((left, right) => left.path.localeCompare(right.path))
            .slice(0, PARTIAL_PATH_SAMPLE_LIMIT),
        missing_by_target_samples: missingByTargetSamples,
    };
}

function buildSuspiciousPayloads(perTarget = []) {
    const validTargets = perTarget.filter(target => target.row_found && target.pageprops_found);
    const sizeStats = distribution(validTargets.map(target => target.json_byte_length));
    const pathStats = distribution(validTargets.map(target => target.path_count));
    const sizeMedian = Number(sizeStats.median);
    const pathMedian = Number(pathStats.median);
    const smallPayloads = [];
    const payloadSizeOutliers = [];
    const missingCoreModules = [];
    const blockOrErrorMarkers = [];

    for (const target of validTargets) {
        const reasons = [];
        if (Number.isFinite(sizeMedian) && sizeMedian > 0 && target.json_byte_length < sizeMedian * 0.5) {
            reasons.push('json_byte_length_below_half_median');
            payloadSizeOutliers.push({
                external_id: target.external_id,
                match_id: target.match_id,
                json_byte_length: target.json_byte_length,
                json_byte_length_median: sizeMedian,
            });
        }
        if (Number.isFinite(pathMedian) && pathMedian > 0 && target.path_count < pathMedian * 0.5) {
            reasons.push('path_count_below_half_median');
        }
        if (target.module_presence.content !== true) {
            reasons.push('missing_core_content');
        }
        if (reasons.length > 0) {
            smallPayloads.push({
                external_id: target.external_id,
                match_id: target.match_id,
                reasons,
                json_byte_length: target.json_byte_length,
                path_count: target.path_count,
            });
        }

        const missingCore = CORE_MODULE_PATHS.filter(modulePath => target.module_presence[modulePath] !== true);
        if (missingCore.length > 0) {
            missingCoreModules.push({
                external_id: target.external_id,
                match_id: target.match_id,
                missing_core_modules: missingCore,
            });
        }

        if (target.marker_names.length > 0) {
            blockOrErrorMarkers.push({
                external_id: target.external_id,
                match_id: target.match_id,
                marker_names: target.marker_names.slice(0, MARKER_SAMPLE_LIMIT),
            });
        }
    }

    return {
        small_payloads: smallPayloads,
        block_or_error_markers: blockOrErrorMarkers,
        missing_core_modules: missingCoreModules,
        payload_size_outliers: payloadSizeOutliers,
    };
}

function buildCompletenessAssessment({ perTarget = [], moduleCoverageCounts = {}, coverageTier, suspicious = {} }) {
    const parserCandidateModules = CORE_MODULE_PATHS.filter(
        modulePath => moduleCoverageCounts[modulePath] === perTarget.length
    );
    const optionalHandlingModules = MODULE_PATHS.filter(
        modulePath => OPTIONAL_MODULE_PATHS.includes(modulePath) || moduleCoverageCounts[modulePath] < perTarget.length
    );
    const fieldsNotSafeToAssume = MODULE_PATHS.filter(
        modulePath => moduleCoverageCounts[modulePath] < perTarget.length
    );
    const canEnterParserPlanning = coverageTier !== 'seeded_pageprops_v2_incomplete';

    return {
        can_enter_parser_planning: canEnterParserPlanning,
        parser_candidate_modules: parserCandidateModules,
        optional_handling_modules: optionalHandlingModules,
        fields_not_safe_to_assume_all_leagues: fieldsNotSafeToAssume,
        lower_tier_league_risk:
            'Seeded Ligue 1 pageProps v2 rows can inform parser planning, but future lower-tier or colder leagues may miss optional page-level siblings or content submodules. Parser design must branch by data_version/source/coverage tier and keep optional handling explicit.',
        planning_only_recommendation:
            'Proceed to parser planning only. Do not implement parser/features/training until leakage-safe module mapping is explicitly designed.',
        suspicious_small_payload_count: suspicious.small_payloads?.length || 0,
        missing_core_module_target_count: suspicious.missing_core_modules?.length || 0,
    };
}

function summarizeTargetRow(target, row) {
    const safeRow = row || {};
    const rawData = objectOrEmpty(safeRow.raw_data);
    const hasMeta = Object.prototype.hasOwnProperty.call(rawData, '_meta');
    const hasMatchId = Object.prototype.hasOwnProperty.call(rawData, 'matchId');
    const pageProps = objectOrEmpty(rawData.pageProps);
    const pagePropsFound = isPlainObject(rawData.pageProps);
    const rawDataTopLevelKeys = summarizeTopLevelKeys(rawData);
    const pagePropsTopLevelKeys = summarizeTopLevelKeys(pageProps);
    const pagePropsPaths = pagePropsFound ? listJsonPaths(pageProps, { includeContainers: true }) : [];
    const pagePropsShape = pagePropsFound
        ? summarizePagePropsShape(pageProps)
        : {
              path_count: 0,
              leaf_path_count: 0,
              max_depth: 0,
              scalar_count: 0,
              object_count: 0,
              array_count: 0,
              null_count: 0,
          };
    const modulePresence = buildModulePresence(pageProps);
    const coverageTier = resolveCoverageTier(modulePresence);
    const markers = pagePropsFound ? detectSuspiciousMarkers(pageProps) : detectSuspiciousMarkers(rawData);

    return {
        row_found: Boolean(row),
        external_id: target.externalId,
        match_id: target.matchId,
        data_hash: normalizeText(safeRow.data_hash),
        home_team: extractTeamName(readPath(pageProps, 'general.homeTeam')),
        away_team: extractTeamName(readPath(pageProps, 'general.awayTeam')),
        raw_data_type: isPlainObject(safeRow.raw_data) ? 'object' : typeof safeRow.raw_data,
        has_meta: hasMeta,
        has_matchId: hasMatchId,
        has_pageProps: pagePropsFound,
        json_byte_length: pagePropsFound ? Buffer.byteLength(JSON.stringify(pageProps), 'utf8') : 0,
        raw_data_top_level_keys: rawDataTopLevelKeys,
        pageprops_top_level_keys: pagePropsTopLevelKeys,
        pageProps_top_level_keys: pagePropsTopLevelKeys,
        path_count: pagePropsShape.path_count,
        leaf_path_count: pagePropsShape.leaf_path_count,
        max_depth: pagePropsShape.max_depth,
        scalar_count: pagePropsShape.scalar_count,
        object_count: pagePropsShape.object_count,
        array_count: pagePropsShape.array_count,
        null_count: pagePropsShape.null_count,
        pageprops_found: pagePropsFound,
        pageprops_paths: pagePropsPaths,
        module_presence: modulePresence,
        coverage_tier: coverageTier,
        marker_names: markers.marker_names,
        block_or_error_markers: markers,
    };
}

function buildExcludedProvenanceSummary(rows = []) {
    const byDataVersion = {};
    for (const row of rows) {
        const version = normalizeText(row.data_version);
        byDataVersion[version] = (byDataVersion[version] || 0) + 1;
    }
    return {
        total_rows: rows.length,
        by_data_version: byDataVersion,
        rows: rows.map(row => ({
            external_id: normalizeText(row.external_id),
            match_id: normalizeText(row.match_id),
            data_version: normalizeText(row.data_version),
            data_hash: normalizeText(row.data_hash),
        })),
    };
}

function buildAuditSummary({
    rowCountRows = [],
    constraintRows = [],
    targetRows = [],
    distributionRows = [],
    duplicateRows = [],
    excludedRows = [],
    input = {},
} = {}) {
    const errors = [];
    const rowCounts = buildRowCountsSummary(rowCountRows);
    const dataVersionDistribution = buildDistributionSummary(distributionRows);
    const schema = detectSchema(constraintRows);
    const targetRowByExternalId = new Map(targetRows.map(row => [normalizeText(row.external_id), row]));

    for (const [tableName, expectedRows] of Object.entries(EXPECTED_ROW_COUNTS)) {
        if (Number(rowCounts[tableName]) !== expectedRows) {
            errors.push(`row count mismatch for ${tableName}: expected ${expectedRows}, got ${rowCounts[tableName]}`);
        }
    }

    for (const [dataVersion, expectedRows] of Object.entries(EXPECTED_DISTRIBUTION)) {
        if (Number(dataVersionDistribution[dataVersion]) !== expectedRows) {
            errors.push(
                `data_version distribution mismatch for ${dataVersion}: expected ${expectedRows}, got ${dataVersionDistribution[dataVersion]}`
            );
        }
    }

    if (!schema.unique_match_id_data_version) {
        errors.push('missing UNIQUE (match_id, data_version)');
    }
    if (schema.unique_match_id_only) {
        errors.push('legacy UNIQUE (match_id) must be absent');
    }
    if (!schema.raw_match_data_match_id_data_version_key_present) {
        errors.push('raw_match_data_match_id_data_version_key must be present');
    }
    if (!schema.raw_match_data_match_id_key_absent) {
        errors.push('raw_match_data_match_id_key must be absent');
    }
    if ((duplicateRows || []).length > 0) {
        errors.push(`duplicate (match_id,data_version) rows found: ${(duplicateRows || []).length}`);
    }
    if ((targetRows || []).length !== EXPECTED_TARGET_EXTERNAL_IDS.length) {
        errors.push(`expected ${EXPECTED_TARGET_EXTERNAL_IDS.length} target rows, got ${(targetRows || []).length}`);
    }

    const perTarget = SEEDED_TARGETS.map(target => {
        const row = targetRowByExternalId.get(target.externalId) || null;
        if (!row) {
            errors.push(`missing v2 row for external_id=${target.externalId}`);
        }
        const summary = summarizeTargetRow(target, row);
        if (summary.row_found && normalizeText(row.data_version) !== DATA_VERSION) {
            errors.push(`${target.externalId} data_version must be ${DATA_VERSION}`);
        }
        if (summary.row_found && summary.has_pageProps !== true) {
            errors.push(`${target.externalId} raw_data missing pageProps`);
        }
        if (summary.row_found && summary.has_meta !== true) {
            errors.push(`${target.externalId} raw_data missing _meta`);
        }
        if (summary.row_found && summary.has_matchId !== true) {
            errors.push(`${target.externalId} raw_data missing matchId`);
        }
        return summary;
    });

    const allTargetRowsFound = perTarget.every(target => target.row_found === true);
    const moduleCoverageDetail = buildModuleCoverage(perTarget);
    const moduleCoverageCounts = Object.fromEntries(
        Object.entries(moduleCoverageDetail.coverage).map(([modulePath, formatted]) => [
            modulePath,
            Number.parseInt(formatted.split('/')[0], 10),
        ])
    );
    const pathCoverage = buildPathCoverage(perTarget);
    const suspicious = buildSuspiciousPayloads(perTarget);
    const coverageTier = (() => {
        if (perTarget.some(target => target.coverage_tier === 'seeded_pageprops_v2_incomplete')) {
            return 'seeded_pageprops_v2_incomplete';
        }
        if (perTarget.some(target => target.coverage_tier === 'seeded_pageprops_v2_partial_coverage')) {
            return 'seeded_pageprops_v2_partial_coverage';
        }
        return 'seeded_pageprops_v2_high_coverage';
    })();
    const completenessAssessment = buildCompletenessAssessment({
        perTarget,
        moduleCoverageCounts,
        coverageTier,
        suspicious,
    });
    const foundTargets = perTarget.filter(target => target.row_found && target.pageprops_found);
    const sizeStats = {
        json_byte_length_min: distribution(foundTargets.map(target => target.json_byte_length)).min,
        json_byte_length_max: distribution(foundTargets.map(target => target.json_byte_length)).max,
        json_byte_length_median: distribution(foundTargets.map(target => target.json_byte_length)).median,
        path_count_min: distribution(foundTargets.map(target => target.path_count)).min,
        path_count_max: distribution(foundTargets.map(target => target.path_count)).max,
        path_count_median: distribution(foundTargets.map(target => target.path_count)).median,
    };

    return {
        phase: PHASE,
        audit_only: true,
        ok: errors.length === 0,
        source: input.source || SOURCE,
        table: input.table || TABLE,
        data_version: input.dataVersion || DATA_VERSION,
        target_count: EXPECTED_TARGET_EXTERNAL_IDS.length,
        all_target_rows_found: allTargetRowsFound,
        schema,
        row_counts: rowCounts,
        data_version_distribution: dataVersionDistribution,
        size_stats: sizeStats,
        module_coverage: moduleCoverageDetail.coverage,
        module_coverage_missing_external_ids: moduleCoverageDetail.missingExternalIds,
        path_coverage: pathCoverage,
        suspicious,
        coverage_tier: coverageTier,
        completeness_assessment: completenessAssessment,
        excluded_provenance: buildExcludedProvenanceSummary(excludedRows),
        per_target: perTarget.map(target => {
            const { pageprops_paths, module_presence, block_or_error_markers, ...summary } = target;
            return {
                ...summary,
                module_presence,
                block_or_error_markers,
            };
        }),
        duplicates: {
            duplicate_match_id_data_version_count: (duplicateRows || []).length,
            rows: duplicateRows || [],
        },
        errors,
        controlled_error: errors.length > 0 ? errors[0] : null,
        db_write_executed: false,
        raw_match_data_write_executed: false,
        network_executed: false,
        parser_features_executed: false,
        training_executed: false,
        prediction_executed: false,
        print_full_raw_data: false,
        save_full_raw_data: false,
    };
}

function assertSelectOnly(sql) {
    const normalizedSql = normalizeText(sql).replace(/\s+/g, ' ').toLowerCase();
    if (!normalizedSql.startsWith('select ')) {
        throw new Error(`NON_SELECT_SQL_BLOCKED: ${sql}`);
    }
    if (
        /\b(insert|update|delete|truncate|alter|drop|create|grant|revoke|copy|for update|begin|commit|rollback)\b/i.test(
            normalizedSql
        )
    ) {
        throw new Error(`SQL_WRITE_OR_LOCK_BLOCKED: ${sql}`);
    }
}

async function safeSelect(client, sql, params = []) {
    assertSelectOnly(sql);
    return client.query(sql, params);
}

async function loadAuditRows(client, input) {
    const rowCountResult = await safeSelect(
        client,
        `
        SELECT 'matches' AS table_name, COUNT(*) AS rows FROM matches
        UNION ALL
        SELECT 'bookmaker_odds_history', COUNT(*) FROM bookmaker_odds_history
        UNION ALL
        SELECT 'raw_match_data', COUNT(*) FROM raw_match_data
        UNION ALL
        SELECT 'l3_features', COUNT(*) FROM l3_features
        UNION ALL
        SELECT 'match_features_training', COUNT(*) FROM match_features_training
        UNION ALL
        SELECT 'predictions', COUNT(*) FROM predictions
        `
    );
    const constraintResult = await safeSelect(
        client,
        `
        SELECT
            conname,
            contype,
            pg_get_constraintdef(c.oid) AS definition
        FROM pg_constraint c
        JOIN pg_class t ON c.conrelid = t.oid
        WHERE t.relname = 'raw_match_data'
        ORDER BY conname
        `
    );
    const targetResult = await safeSelect(
        client,
        `
        SELECT external_id, match_id, data_version, data_hash, collected_at, raw_data
        FROM raw_match_data
        WHERE external_id = ANY($1)
          AND data_version = $2
        ORDER BY external_id
        `,
        [input.targetExternalIds, input.dataVersion]
    );
    const distributionResult = await safeSelect(
        client,
        `
        SELECT data_version, COUNT(*) AS rows
        FROM raw_match_data
        GROUP BY data_version
        ORDER BY data_version
        `
    );
    const duplicateResult = await safeSelect(
        client,
        `
        SELECT match_id, data_version, COUNT(*) AS rows
        FROM raw_match_data
        GROUP BY match_id, data_version
        HAVING COUNT(*) > 1
        ORDER BY match_id, data_version
        `
    );
    const excludedRowsResult = await safeSelect(
        client,
        `
        SELECT external_id, match_id, data_version, data_hash
        FROM raw_match_data
        WHERE data_version <> ALL($1)
        ORDER BY data_version, external_id
        `,
        [[DATA_VERSION, 'fotmob_html_hyd_v1']]
    );

    return {
        rowCountRows: rowCountResult.rows || [],
        constraintRows: constraintResult.rows || [],
        targetRows: targetResult.rows || [],
        distributionRows: distributionResult.rows || [],
        duplicateRows: duplicateResult.rows || [],
        excludedRows: excludedRowsResult.rows || [],
    };
}

function createDefaultPool() {
    const { Pool } = require('pg');
    const { buildDbConnectionConfig } = require('./helpers/dbBlueprint');
    return new Pool(buildDbConnectionConfig());
}

async function runCli(argv = process.argv.slice(2), dependencies = {}) {
    const parsedArgs = Array.isArray(argv) ? parseArgs(argv) : argv;
    const validation = validateAuditInput(parsedArgs);
    const output = dependencies.output || (payload => process.stdout.write(`${JSON.stringify(payload, null, 2)}\n`));

    if (!validation.ok) {
        const blockedPayload = {
            phase: PHASE,
            ok: false,
            blocked: true,
            errors: validation.errors,
            db_write_executed: false,
            raw_match_data_write_executed: false,
            network_executed: false,
            parser_features_executed: false,
            training_executed: false,
            prediction_executed: false,
        };
        output(blockedPayload);
        return { status: 1, payload: blockedPayload };
    }

    const pool = dependencies.client ? null : createDefaultPool();
    const client = dependencies.client || pool;

    try {
        const rows =
            dependencies.rows ||
            (await loadAuditRows(client, {
                source: validation.value.source,
                table: validation.value.table,
                dataVersion: validation.value.dataVersion,
                targetExternalIds: validation.value.targetExternalIds,
            }));
        const summary = buildAuditSummary({
            ...rows,
            input: validation.value,
        });
        output(summary);
        return { status: summary.ok ? 0 : 1, payload: summary };
    } finally {
        if (pool && typeof pool.end === 'function') {
            await pool.end();
        }
    }
}

module.exports = {
    PHASE,
    SOURCE,
    TABLE,
    DATA_VERSION,
    SEEDED_TARGETS,
    EXPECTED_TARGET_EXTERNAL_IDS,
    EXPECTED_MATCH_IDS,
    EXPECTED_ROW_COUNTS,
    EXPECTED_DISTRIBUTION,
    MODULE_PATHS,
    CORE_MODULE_PATHS,
    OPTIONAL_MODULE_PATHS,
    parseArgs,
    validateAuditInput,
    summarizePagePropsShape,
    detectSuspiciousMarkers,
    buildModulePresence,
    resolveCoverageTier,
    buildPathCoverage,
    buildSuspiciousPayloads,
    buildCompletenessAssessment,
    buildAuditSummary,
    runCli,
};

if (require.main === module) {
    runCli()
        .then(result => {
            process.exitCode = result.status;
        })
        .catch(error => {
            process.stderr.write(`${error.stack || error.message}\n`);
            process.exitCode = 1;
        });
}
