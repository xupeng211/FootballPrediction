#!/usr/bin/env node
'use strict';

const { assertDbWriteAllowed } = require('./helpers/db_write_guard');

const PHASE = 'PHASE5_21L2A_RAW_MATCH_DATA_COMPLETENESS_SOURCE_FIDELITY_AUDIT';
const FOTMOB_DATA_VERSION = 'fotmob_html_hyd_v1';
const SYNTHETIC_DATA_VERSION = 'PHASE4.43_SYNTHETIC';
const EXPECTED_RAW_COUNT = 10;
const EXPECTED_SEEDED_RAW_COUNT = 8;
const SEEDED_LIGUE1_MATCH_ID_PREFIX = '53_20252026_';

const REQUIRED_TOP_LEVEL_KEYS = Object.freeze(['_meta', 'content', 'general', 'header', 'matchId']);
const REQUIRED_MODULES = Object.freeze([
    '_meta',
    'content',
    'general',
    'header',
    'matchId',
    'content.matchFacts',
    'content.lineup',
    'content.liveticker',
    'content.playerStats',
    'content.shotmap',
    'content.stats',
    'content.teamForm',
    'content.h2h',
    'content.table',
    'content.momentum',
    'content.topPlayers',
    'content.insights',
    'content.highlights',
]);

function normalizeText(value) {
    return String(value ?? '').trim();
}

function toKebabKey(key) {
    return normalizeText(key)
        .replace(/[A-Z]/g, char => `-${char.toLowerCase()}`)
        .replace(/^--+/, '');
}

function parseArgs(argv = []) {
    const args = {};
    for (let index = 0; index < argv.length; index += 1) {
        const token = argv[index];
        if (!token.startsWith('--')) continue;
        const raw = token.slice(2);
        const eqIndex = raw.indexOf('=');
        if (eqIndex >= 0) {
            args[toKebabKey(raw.slice(0, eqIndex))] = raw.slice(eqIndex + 1);
            continue;
        }
        const next = argv[index + 1];
        if (next && !next.startsWith('--')) {
            args[toKebabKey(raw)] = next;
            index += 1;
        } else {
            args[toKebabKey(raw)] = 'yes';
        }
    }
    return args;
}

function normalizeBooleanFlag(value) {
    const normalized = normalizeText(value).toLowerCase();
    if (['yes', 'true', '1', 'y'].includes(normalized)) return true;
    if (['no', 'false', '0', 'n'].includes(normalized)) return false;
    return null;
}

function parseExpectedInteger(value) {
    const normalized = normalizeText(value);
    if (!/^\d+$/.test(normalized)) return null;
    return Number.parseInt(normalized, 10);
}

function validateRequiredNoFlag(input, flagName, errors) {
    const value = normalizeBooleanFlag(input[flagName]);
    if (value !== false) {
        errors.push(`${flagName}=no is required`);
    }
    return value;
}

function validateBlockedYesFlag(input, flagName, errors) {
    const value = normalizeBooleanFlag(input[flagName]);
    if (value === true) {
        errors.push(`${flagName}=yes is blocked in Phase 5.21L2A`);
    }
    return value;
}

function validateAuditInput(input = {}) {
    const errors = [];
    const source = normalizeText(input.source).toLowerCase();
    const expectedRawCount = parseExpectedInteger(input['expected-raw-count']);
    const expectedSeededRawCount = parseExpectedInteger(input['expected-seeded-raw-count']);

    if (!source) {
        errors.push('source=fotmob is required');
    } else if (source !== 'fotmob') {
        errors.push('source must be fotmob');
    }

    if (expectedRawCount === null) {
        errors.push('expected-raw-count=10 is required');
    } else if (expectedRawCount !== EXPECTED_RAW_COUNT) {
        errors.push('expected-raw-count must be 10');
    }

    if (expectedSeededRawCount === null) {
        errors.push('expected-seeded-raw-count=8 is required');
    } else if (expectedSeededRawCount !== EXPECTED_SEEDED_RAW_COUNT) {
        errors.push('expected-seeded-raw-count must be 8');
    }

    const allowNetwork = validateRequiredNoFlag(input, 'allow-network', errors);
    const allowDbWrite = validateRequiredNoFlag(input, 'allow-db-write', errors);
    const printFullRawData = validateRequiredNoFlag(input, 'print-full-raw-data', errors);
    const saveFullRawData = validateRequiredNoFlag(input, 'save-full-raw-data', errors);

    for (const blockedFlag of ['write-report-json', 'parser-features', 'train', 'predict', 'execute', 'commit']) {
        validateBlockedYesFlag(input, blockedFlag, errors);
    }

    return {
        ok: errors.length === 0,
        errors,
        value: {
            source,
            expectedRawCount,
            expectedSeededRawCount,
            allowNetwork,
            allowDbWrite,
            printFullRawData,
            saveFullRawData,
        },
    };
}

function classifyProvenance(dataVersion) {
    if (dataVersion === FOTMOB_DATA_VERSION) return 'fotmob_html_hydration';
    if (dataVersion === SYNTHETIC_DATA_VERSION) return 'legacy_synthetic';
    return 'unknown';
}

function isPlainObject(value) {
    return value !== null && typeof value === 'object' && !Array.isArray(value);
}

function pathJoin(base, key) {
    return base ? `${base}.${key}` : key;
}

function listJsonPaths(value, options = {}) {
    const includeContainers = options.includeContainers === true;
    const paths = new Set();

    function walk(node, currentPath) {
        if (Array.isArray(node)) {
            if (currentPath && includeContainers) paths.add(currentPath);
            const arrayPath = currentPath ? `${currentPath}[]` : '[]';
            paths.add(arrayPath);
            for (const item of node) {
                walk(item, arrayPath);
            }
            return;
        }

        if (isPlainObject(node)) {
            if (currentPath && includeContainers) paths.add(currentPath);
            const keys = Object.keys(node);
            if (keys.length === 0 && currentPath) paths.add(currentPath);
            for (const key of keys) {
                walk(node[key], pathJoin(currentPath, key));
            }
            return;
        }

        paths.add(currentPath || '$');
    }

    walk(value, '');
    return [...paths].sort();
}

function summarizeJsonShape(value) {
    const leafPaths = new Set();
    const allPaths = new Set();
    const arrayPaths = new Set();
    const counters = {
        node_count: 0,
        object_count: 0,
        array_count: 0,
        scalar_count: 0,
        leaf_path_count: 0,
        distinct_path_count: 0,
        max_depth: 0,
        array_path_count: 0,
    };

    function walk(node, currentPath, depth) {
        counters.node_count += 1;
        counters.max_depth = Math.max(counters.max_depth, depth);
        if (currentPath) allPaths.add(currentPath);

        if (Array.isArray(node)) {
            counters.array_count += 1;
            if (currentPath) arrayPaths.add(currentPath);
            if (node.length === 0 && currentPath) leafPaths.add(`${currentPath}[]`);
            for (const item of node) {
                walk(item, currentPath ? `${currentPath}[]` : '[]', depth + 1);
            }
            return;
        }

        if (isPlainObject(node)) {
            counters.object_count += 1;
            const keys = Object.keys(node);
            if (keys.length === 0 && currentPath) leafPaths.add(currentPath);
            for (const key of keys) {
                walk(node[key], pathJoin(currentPath, key), depth + 1);
            }
            return;
        }

        counters.scalar_count += 1;
        leafPaths.add(currentPath || '$');
    }

    walk(value, '', 0);
    counters.leaf_path_count = leafPaths.size;
    counters.distinct_path_count = allPaths.size;
    counters.array_path_count = arrayPaths.size;
    return counters;
}

function summarizeTopLevelKeys(rawData) {
    if (!isPlainObject(rawData)) return [];
    return Object.keys(rawData).sort();
}

function hasPath(value, dottedPath) {
    const parts = dottedPath.split('.');
    let cursor = value;
    for (const part of parts) {
        if (!isPlainObject(cursor) || !Object.prototype.hasOwnProperty.call(cursor, part)) {
            return false;
        }
        cursor = cursor[part];
    }
    return true;
}

function summarizeModulePresence(rawData) {
    const presence = {};
    for (const modulePath of REQUIRED_MODULES) {
        presence[modulePath] = hasPath(rawData, modulePath);
    }
    return presence;
}

function median(values) {
    const sorted = values.filter(value => Number.isFinite(value)).sort((a, b) => a - b);
    if (sorted.length === 0) return null;
    const middle = Math.floor(sorted.length / 2);
    if (sorted.length % 2 === 1) return sorted[middle];
    return (sorted[middle - 1] + sorted[middle]) / 2;
}

function distribution(values) {
    const safe = values.filter(value => Number.isFinite(value));
    if (safe.length === 0) return { min: null, max: null, median: null };
    return {
        min: Math.min(...safe),
        max: Math.max(...safe),
        median: median(safe),
    };
}

function summarizePathCoverage(rowSummaries = []) {
    const rowPathSets = rowSummaries.map(row => new Set(row.paths || []));
    const allPaths = new Set();
    for (const pathSet of rowPathSets) {
        for (const path of pathSet) allPaths.add(path);
    }

    const commonPaths = [];
    const partialPaths = [];
    for (const path of allPaths) {
        const presentCount = rowPathSets.filter(pathSet => pathSet.has(path)).length;
        if (presentCount === rowPathSets.length) {
            commonPaths.push(path);
        } else {
            partialPaths.push(path);
        }
    }

    return {
        common_paths_count: commonPaths.length,
        partial_paths_count: partialPaths.length,
        common_paths_sample: commonPaths.sort().slice(0, 25),
        partial_paths_sample: partialPaths.sort().slice(0, 25),
    };
}

function summarizeProvenanceGroups(rowSummaries = []) {
    const groups = {};
    for (const row of rowSummaries) {
        const key = row.data_version || 'UNKNOWN';
        if (!groups[key]) {
            groups[key] = {
                provenance: row.provenance,
                row_count: 0,
                has_meta_count: 0,
                has_content_count: 0,
                has_general_count: 0,
                has_header_count: 0,
                has_match_id_count: 0,
                external_ids: [],
            };
        }
        groups[key].row_count += 1;
        groups[key].has_meta_count += row.module_presence._meta ? 1 : 0;
        groups[key].has_content_count += row.module_presence.content ? 1 : 0;
        groups[key].has_general_count += row.module_presence.general ? 1 : 0;
        groups[key].has_header_count += row.module_presence.header ? 1 : 0;
        groups[key].has_match_id_count += row.module_presence.matchId ? 1 : 0;
        groups[key].external_ids.push(row.external_id);
    }

    const provenanceGroupCounts = {};
    for (const row of rowSummaries) {
        provenanceGroupCounts[row.provenance] = (provenanceGroupCounts[row.provenance] || 0) + 1;
    }

    return {
        by_data_version: groups,
        provenance_group_counts: provenanceGroupCounts,
    };
}

function flattenSearchEntries(value) {
    const entries = [];

    function walk(node, key = '') {
        if (Array.isArray(node)) {
            for (const item of node) walk(item, key);
            return;
        }
        if (isPlainObject(node)) {
            for (const [childKey, childValue] of Object.entries(node)) {
                entries.push({ key: childKey.toLowerCase(), value: '' });
                walk(childValue, childKey);
            }
            return;
        }
        entries.push({ key: key.toLowerCase(), value: normalizeText(node).toLowerCase() });
    }

    walk(value);
    return entries;
}

function detectBlockOrErrorMarkers(rawData) {
    const entries = flattenSearchEntries(rawData);
    const hasErrorKey = entries.some(entry => ['error', 'errors', 'errorcode', 'errormessage'].includes(entry.key));
    const hasCaptchaMarker = entries.some(
        entry => entry.key.includes('captcha') || entry.value.includes('captcha') || entry.value.includes('turnstile')
    );
    const hasBlockMarker = entries.some(entry =>
        [
            'forbidden',
            'access denied',
            'cloudflare',
            'rate limit',
            'too many requests',
            'unusual traffic',
            'http_403',
            'http_429',
            'status 403',
            'status 429',
            '403 forbidden',
            '429 too many',
        ].some(marker => entry.key.includes(marker) || entry.value.includes(marker))
    );
    const topLevelKeys = summarizeTopLevelKeys(rawData);
    const hasPlaceholderOnlyShape =
        !isPlainObject(rawData) ||
        topLevelKeys.length <= 2 ||
        (hasPath(rawData, 'content') && isPlainObject(rawData.content) && Object.keys(rawData.content).length === 0);

    return {
        has_error_key: hasErrorKey,
        has_captcha_marker: hasCaptchaMarker,
        has_block_marker: hasBlockMarker,
        has_placeholder_only_shape: hasPlaceholderOnlyShape,
    };
}

function detectLikelyTransformedPayload(rawData) {
    if (!isPlainObject(rawData)) return 'unknown';
    if (hasPath(rawData, 'props.pageProps') || hasPath(rawData, 'pageProps')) {
        return 'possible_full_next_data';
    }

    const topLevelKeys = summarizeTopLevelKeys(rawData);
    const onlyCanonicalKeys = topLevelKeys.every(key => REQUIRED_TOP_LEVEL_KEYS.includes(key));
    if (onlyCanonicalKeys && hasPath(rawData, 'content') && hasPath(rawData, 'general') && hasPath(rawData, 'header')) {
        return 'transformed_hydration_payload';
    }

    if (hasPath(rawData, 'content') && hasPath(rawData, 'general') && hasPath(rawData, 'header')) {
        return 'transformed_hydration_payload';
    }

    return 'unknown';
}

function detectPotentialSourceFidelityRisk(rawData, context = {}) {
    const risks = [];
    const likelyShape = detectLikelyTransformedPayload(rawData);
    const provenance = context.provenance || classifyProvenance(context.data_version);

    if (provenance !== 'fotmob_html_hydration') {
        return risks;
    }
    if (likelyShape === 'transformed_hydration_payload') {
        risks.push('raw_data_is_transformed_payload');
        risks.push('full_hydration_source_not_stored');
        risks.push('props_pageProps_not_stored');
    }
    if (!hasPath(rawData, 'props.pageProps')) {
        risks.push('pageProps_absent');
    }
    if (!hasPath(rawData, 'props.pageProps.content')) {
        risks.push('full_pageProps_content_path_absent');
    }
    return [...new Set(risks)].sort();
}

function normalizeRowId(row = {}) {
    return row.id === undefined || row.id === null ? null : String(row.id);
}

function normalizeCollectedAt(row = {}) {
    if (row.collected_at instanceof Date) return row.collected_at.toISOString();
    return normalizeText(row.collected_at || row.collectedAt);
}

function detectRawDataType(rawData) {
    if (isPlainObject(rawData)) return 'object';
    if (Array.isArray(rawData)) return 'array';
    return typeof rawData;
}

function buildRowAnomalies({ provenance, modulePresence }) {
    const strictAnomalies = [];
    const schemaAnomalies = [];

    if (provenance === 'fotmob_html_hydration') {
        for (const key of REQUIRED_TOP_LEVEL_KEYS) {
            if (!modulePresence[key]) strictAnomalies.push(`missing_${key}`);
        }
    }
    if (provenance === 'legacy_synthetic' && !modulePresence._meta) {
        schemaAnomalies.push('synthetic_missing__meta');
    }
    if (provenance === 'unknown') {
        schemaAnomalies.push('unknown_provenance');
    }

    return { strictAnomalies, schemaAnomalies };
}

function summarizeRow(row = {}) {
    const rawData = row.raw_data || row.rawData || {};
    const dataVersion = normalizeText(row.data_version || row.dataVersion);
    const provenance = classifyProvenance(dataVersion);
    const topLevelKeys = summarizeTopLevelKeys(rawData);
    const shape = summarizeJsonShape(rawData);
    const paths = listJsonPaths(rawData, { includeContainers: true });
    const modulePresence = summarizeModulePresence(rawData);
    const blockOrErrorMarkers = detectBlockOrErrorMarkers(rawData);
    const likelyShape = detectLikelyTransformedPayload(rawData);
    const potentialFidelityRisks = detectPotentialSourceFidelityRisk(rawData, {
        data_version: dataVersion,
        provenance,
    });
    const isFotMob = provenance === 'fotmob_html_hydration';
    const { strictAnomalies, schemaAnomalies } = buildRowAnomalies({ provenance, modulePresence });

    const jsonString = JSON.stringify(rawData);
    return {
        id: normalizeRowId(row),
        match_id: normalizeText(row.match_id || row.matchId),
        external_id: normalizeText(row.external_id || row.externalId),
        data_version: dataVersion,
        provenance,
        excluded_from_fotmob_source_fidelity: !isFotMob,
        data_hash: normalizeText(row.data_hash || row.dataHash),
        collected_at: normalizeCollectedAt(row),
        raw_data_type: detectRawDataType(rawData),
        json_byte_length: Buffer.byteLength(jsonString, 'utf8'),
        top_level_keys: topLevelKeys,
        ...shape,
        module_presence: modulePresence,
        block_or_error_markers: blockOrErrorMarkers,
        likely_shape: likelyShape,
        potential_fidelity_risks: potentialFidelityRisks,
        strict_anomalies: strictAnomalies,
        schema_anomalies: schemaAnomalies,
        paths,
    };
}

function buildModuleCoverage(rowSummaries = []) {
    const counts = {};
    const missingExternalIds = {};
    for (const modulePath of REQUIRED_MODULES) {
        counts[modulePath] = 0;
        missingExternalIds[modulePath] = [];
    }

    for (const row of rowSummaries) {
        for (const modulePath of REQUIRED_MODULES) {
            if (row.module_presence[modulePath]) {
                counts[modulePath] += 1;
            } else {
                missingExternalIds[modulePath].push(row.external_id);
            }
        }
    }

    return {
        per_module_presence_counts: counts,
        per_module_missing_external_ids: missingExternalIds,
    };
}

function findSuspiciousSmallPayloads(rowSummaries = []) {
    const sizes = rowSummaries.map(row => row.json_byte_length).filter(Number.isFinite);
    const medianSize = median(sizes);
    if (!Number.isFinite(medianSize) || medianSize === 0) return [];
    return rowSummaries
        .filter(row => row.json_byte_length < Math.max(1000, medianSize * 0.25))
        .map(row => ({
            match_id: row.match_id,
            external_id: row.external_id,
            json_byte_length: row.json_byte_length,
            median_reference: medianSize,
        }));
}

function findCompletenessOutliers(rowSummaries = []) {
    const leafCounts = rowSummaries.map(row => row.leaf_path_count).filter(Number.isFinite);
    const medianLeafCount = median(leafCounts);
    if (!Number.isFinite(medianLeafCount) || medianLeafCount === 0) return [];
    return rowSummaries
        .filter(row => row.leaf_path_count < medianLeafCount * 0.5)
        .map(row => ({
            match_id: row.match_id,
            external_id: row.external_id,
            leaf_path_count: row.leaf_path_count,
            median_reference: medianLeafCount,
        }));
}

function buildSeededLigue1Coverage(matchRows = [], rowSummaryByMatchId = new Map()) {
    return matchRows
        .filter(row => normalizeText(row.match_id).startsWith(SEEDED_LIGUE1_MATCH_ID_PREFIX))
        .map(row => {
            const summary = rowSummaryByMatchId.get(normalizeText(row.match_id));
            return {
                match_id: normalizeText(row.match_id),
                external_id: normalizeText(row.external_id),
                home_team: normalizeText(row.home_team),
                away_team: normalizeText(row.away_team),
                status: normalizeText(row.status),
                has_raw_data: Boolean(summary),
                data_version: summary?.data_version || normalizeText(row.data_version),
                provenance: summary?.provenance || classifyProvenance(row.data_version),
                key_module_presence: summary?.module_presence || {},
                excluded_from_fotmob_source_fidelity: summary?.excluded_from_fotmob_source_fidelity ?? true,
            };
        });
}

function buildSourceFidelityAssessment({ rowSummaries, fotmobRows, provenanceSummary }) {
    const mixedProvenance = Object.keys(provenanceSummary.provenance_group_counts).length > 1;
    const hasFotMobRows = fotmobRows.length > 0;
    const allFotMobTransformed =
        hasFotMobRows && fotmobRows.every(row => row.likely_shape === 'transformed_hydration_payload');
    const anyFullNextData = fotmobRows.some(row => row.likely_shape === 'possible_full_next_data');
    const hasSynthetic = rowSummaries.some(row => row.provenance === 'legacy_synthetic');

    if (!hasFotMobRows) {
        return {
            table_has_mixed_provenance: mixedProvenance,
            fotmob_rows_current_raw_data_is_full_next_data: 'unknown',
            fotmob_rows_current_raw_data_is_transformed_payload: 'unknown',
            transform_may_drop_fields: 'unknown',
            full_hydration_source_not_stored: 'unknown',
            legacy_synthetic_rows_excluded_from_fotmob_conclusion: hasSynthetic,
            requires_live_source_compare: true,
            recommended_storage_strategy_review: true,
            summary: 'No fotmob_html_hyd_v1 rows were available, so source fidelity cannot be concluded locally.',
        };
    }

    return {
        table_has_mixed_provenance: mixedProvenance,
        fotmob_rows_current_raw_data_is_full_next_data: anyFullNextData,
        fotmob_rows_current_raw_data_is_transformed_payload: allFotMobTransformed,
        transform_may_drop_fields: true,
        full_hydration_source_not_stored: !anyFullNextData,
        legacy_synthetic_rows_excluded_from_fotmob_conclusion: hasSynthetic,
        requires_live_source_compare: true,
        recommended_storage_strategy_review: true,
        summary:
            'Local evidence shows fotmob_html_hyd_v1 rows store transformed _meta/content/general/header/matchId payloads, not full __NEXT_DATA__.props.pageProps. A no-write live source fidelity compare is required before parser/features/training.',
    };
}

function buildRawMatchDataCompletenessAudit({ rawRows = [], matchRows = [], input = {} } = {}) {
    const rowSummaries = rawRows.map(summarizeRow);
    const provenanceSummary = summarizeProvenanceGroups(rowSummaries);
    const rowSummaryByMatchId = new Map(rowSummaries.map(row => [row.match_id, row]));
    const fotmobRows = rowSummaries.filter(row => row.provenance === 'fotmob_html_hydration');
    const syntheticRows = rowSummaries.filter(row => row.provenance === 'legacy_synthetic');
    const unknownRows = rowSummaries.filter(row => row.provenance === 'unknown');
    const seededCoverage = buildSeededLigue1Coverage(matchRows, rowSummaryByMatchId);
    const fotmobPathCoverage = summarizePathCoverage(fotmobRows);
    const fotmobModuleCoverage = buildModuleCoverage(fotmobRows);
    const topLevelKeyUnion = [...new Set(rowSummaries.flatMap(row => row.top_level_keys))].sort();
    const fotmobTopLevelKeyUnion = [...new Set(fotmobRows.flatMap(row => row.top_level_keys))].sort();
    const syntheticSchemaAnomalies = syntheticRows
        .filter(row => row.schema_anomalies.length > 0)
        .map(row => ({
            match_id: row.match_id,
            external_id: row.external_id,
            data_version: row.data_version,
            schema_anomalies: row.schema_anomalies,
        }));
    const suspiciousMissingModules = Object.entries(fotmobModuleCoverage.per_module_missing_external_ids)
        .filter(([, externalIds]) => externalIds.length > 0)
        .map(([modulePath, externalIds]) => ({ module: modulePath, missing_external_ids: externalIds }));
    const blockOrErrorRows = rowSummaries
        .filter(row => Object.values(row.block_or_error_markers).some(Boolean))
        .map(row => ({
            match_id: row.match_id,
            external_id: row.external_id,
            block_or_error_markers: row.block_or_error_markers,
        }));

    return {
        phase: PHASE,
        source: input.source || 'fotmob',
        audit_only: true,
        network_used: false,
        db_write_executed: false,
        parser_features_executed: false,
        training_executed: false,
        prediction_executed: false,
        full_raw_data_printed: false,
        full_raw_data_saved: false,
        total_raw_rows: rowSummaries.length,
        expected_raw_count: input.expectedRawCount ?? EXPECTED_RAW_COUNT,
        expected_seeded_raw_count: input.expectedSeededRawCount ?? EXPECTED_SEEDED_RAW_COUNT,
        provenance_summary: provenanceSummary,
        provenance_group_counts: provenanceSummary.provenance_group_counts,
        fotmob_html_hyd_v1_rows: fotmobRows.length,
        legacy_synthetic_rows: syntheticRows.length,
        unknown_provenance_rows: unknownRows.length,
        seeded_ligue1_raw_rows: seededCoverage.filter(row => row.has_raw_data).length,
        top_level_key_union: topLevelKeyUnion,
        fotmob_top_level_key_union: fotmobTopLevelKeyUnion,
        common_paths_count: fotmobPathCoverage.common_paths_count,
        partial_paths_count: fotmobPathCoverage.partial_paths_count,
        path_coverage: fotmobPathCoverage,
        module_coverage: fotmobModuleCoverage,
        json_byte_length_distribution: distribution(fotmobRows.map(row => row.json_byte_length)),
        leaf_path_count_distribution: distribution(fotmobRows.map(row => row.leaf_path_count)),
        max_depth_distribution: distribution(fotmobRows.map(row => row.max_depth)),
        completeness_outliers: findCompletenessOutliers(fotmobRows),
        suspicious_small_payloads: findSuspiciousSmallPayloads(fotmobRows),
        suspicious_missing_modules: suspiciousMissingModules,
        synthetic_schema_anomalies: syntheticSchemaAnomalies,
        unknown_provenance_rows_detail: unknownRows.map(row => ({
            match_id: row.match_id,
            external_id: row.external_id,
            data_version: row.data_version,
        })),
        block_or_error_marker_rows: blockOrErrorRows,
        seeded_ligue1_coverage: seededCoverage,
        rows: rowSummaries.map(row => {
            const { paths, ...summary } = row;
            return summary;
        }),
        source_fidelity_assessment: buildSourceFidelityAssessment({
            rowSummaries,
            fotmobRows,
            provenanceSummary,
        }),
        next_recommended_phase:
            'Phase 5.21L2B HTML hydration source fidelity live compare: single target, no DB write, no full body save/print.',
    };
}

async function queryReadOnly(client, sql, params = []) {
    const normalizedSql = normalizeText(sql).replace(/\s+/g, ' ').toLowerCase();
    if (!normalizedSql.startsWith('select ')) {
        throw new Error('NON_SELECT_SQL_BLOCKED');
    }
    if (/\b(insert|update|delete|truncate|alter|drop|create|grant|revoke|copy|for update)\b/i.test(normalizedSql)) {
        throw new Error('SQL_WRITE_OR_LOCK_BLOCKED');
    }
    return client.query(sql, params);
}

async function loadAuditRows(client) {
    const rawResult = await queryReadOnly(
        client,
        `
        SELECT id, match_id, external_id, data_version, data_hash, collected_at, raw_data
        FROM raw_match_data
        ORDER BY external_id
        `
    );
    const matchResult = await queryReadOnly(
        client,
        `
        SELECT
            m.match_id,
            m.external_id,
            m.home_team,
            m.away_team,
            m.match_date,
            m.status,
            r.id AS raw_id,
            r.data_version,
            r.data_hash,
            r.collected_at
        FROM matches m
        LEFT JOIN raw_match_data r ON r.match_id = m.match_id
        ORDER BY m.match_id
        `
    );

    return {
        rawRows: rawResult.rows || [],
        matchRows: matchResult.rows || [],
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
        output({
            phase: PHASE,
            ok: false,
            blocked: true,
            errors: validation.errors,
            network_used: false,
            db_write_executed: false,
        });
        return { status: 1, payload: null };
    }

    if (validation.value.execute || validation.value.commit) {
        assertDbWriteAllowed({
            script: 'raw_match_data_completeness_fidelity_audit.js',
            tables: ['raw_match_data', 'matches'],
            operations: ['INSERT', 'UPDATE'],
        });
    }

    const pool = dependencies.client ? null : createDefaultPool();
    const client = dependencies.client || pool;
    try {
        const { rawRows, matchRows } = dependencies.rows || (await loadAuditRows(client));
        const audit = buildRawMatchDataCompletenessAudit({
            rawRows,
            matchRows,
            input: validation.value,
        });
        output(audit);
        return { status: 0, payload: audit };
    } finally {
        if (pool && typeof pool.end === 'function') {
            await pool.end();
        }
    }
}

module.exports = {
    PHASE,
    FOTMOB_DATA_VERSION,
    SYNTHETIC_DATA_VERSION,
    REQUIRED_MODULES,
    parseArgs,
    normalizeBooleanFlag,
    validateAuditInput,
    classifyProvenance,
    listJsonPaths,
    summarizeJsonShape,
    summarizeTopLevelKeys,
    summarizeModulePresence,
    summarizePathCoverage,
    summarizeProvenanceGroups,
    detectBlockOrErrorMarkers,
    detectLikelyTransformedPayload,
    detectPotentialSourceFidelityRisk,
    buildRawMatchDataCompletenessAudit,
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
