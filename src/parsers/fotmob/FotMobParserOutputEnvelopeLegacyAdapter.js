/**
 * FotMobParserOutputEnvelopeLegacyAdapter — Dry-Run Legacy Adapter
 * ===============================================================
 *
 * 将 NextDataParser.transformToApiFormat 输出包装为 FotMobParserOutputEnvelope。
 *
 * 纯函数模块：无网络、无 DB、无文件 I/O、无副作用。
 * 不 import NextDataParser，不运行 transformToApiFormat。
 * 只接受已生成好的 transformToApiFormat output object。
 *
 * Boundary: NextDataParser.transformToApiFormat output (Boundary A from DATA-L1F-2B)
 *
 * Parent docs:
 *   - DATA-L1E: FotMob parser output envelope implementation plan
 *   - DATA-L1E-1: FotMobParserOutputEnvelope schema (PR #1699)
 *   - DATA-L1F-2B: NextDataParser + thin parsers output shape audit (PR #1703)
 *
 * lifecycle: permanent
 * @module parsers/fotmob/FotMobParserOutputEnvelopeLegacyAdapter
 */

'use strict';

const {
    FIELD_CONTRACT_CLASSES,
    TIMING_CLASSES,
    MODEL_ELIGIBILITY,
    PAYLOAD_TYPES,
    createEmptyEnvelope,
    createFieldEntry,
} = require('./FotMobParserOutputEnvelope');

// ===========================================================================
// 字段路径分类规则
// ===========================================================================

const POSTMATCH_PATH_PREFIXES = Object.freeze([
    'content.stats',
    'content.shotmap',
    'content.events',
    'content.playerStats',
    'content.momentum',
    'content.matchFacts',
    'header.teams.score',
    'header.status.scoreStr',
    'header.status.winner',
    'header.status.result',
    'general.score',
    'general.result',
    'general.winner',
]);

const UNKNOWN_TIMING_PATH_PREFIXES = Object.freeze([
    'content.lineup',
    'content.injury',
    'content.injuries',
    'content.odds',
    'content.table',
    'content.form',
    'content.standings',
    'general.leagueTable',
    'general.standings',
    'general.form',
]);

const RAW_ONLY_PATH_PREFIXES = Object.freeze([
    'content',
    'content.',
    'general',
    'general.',
    'header',
    'header.',
    '_meta',
    '_meta.',
    '__NEXT_DATA__',
    'pageProps',
    'raw',
]);

// ===========================================================================
// 字段分类辅助函数
// ===========================================================================

function _matchPath(prefixes, fieldPath) {
    for (const prefix of prefixes) {
        if (fieldPath === prefix || fieldPath.startsWith(prefix + '.') || fieldPath.startsWith(prefix + '[')) {
            return true;
        }
    }
    return false;
}

function _matchPathPrefixOnly(prefixes, fieldPath) {
    for (const prefix of prefixes) {
        if (fieldPath === prefix || fieldPath.startsWith(prefix)) {
            return true;
        }
    }
    return false;
}

/**
 * 根据字段路径和值，保守分类字段的 timing 和 eligibility。
 * 分类优先级：postmatch → unknown_timing → raw_only → default(unknown)
 */
function classifyField(fieldPath, value, context = {}) {
    if (_matchPath(POSTMATCH_PATH_PREFIXES, fieldPath)) {
        return {
            timingClass: TIMING_CLASSES.POSTMATCH,
            modelEligibility: MODEL_ELIGIBILITY.FORBIDDEN_POSTMATCH,
            contractClass: FIELD_CONTRACT_CLASSES.UNSAFE_POSTMATCH,
        };
    }
    if (_matchPath(UNKNOWN_TIMING_PATH_PREFIXES, fieldPath)) {
        return {
            timingClass: TIMING_CLASSES.UNKNOWN_TIMING,
            modelEligibility: MODEL_ELIGIBILITY.FORBIDDEN_UNKNOWN_TIMING,
            contractClass: FIELD_CONTRACT_CLASSES.UNKNOWN_TIMING,
        };
    }
    if (_matchPathPrefixOnly(RAW_ONLY_PATH_PREFIXES, fieldPath)) {
        return {
            timingClass: TIMING_CLASSES.RAW_ONLY,
            modelEligibility: MODEL_ELIGIBILITY.FORBIDDEN_RAW_ONLY,
            contractClass: FIELD_CONTRACT_CLASSES.DEBUG_OR_RAW_ONLY,
        };
    }
    return {
        timingClass: TIMING_CLASSES.UNKNOWN_TIMING,
        modelEligibility: MODEL_ELIGIBILITY.FORBIDDEN_UNKNOWN_TIMING,
        contractClass: FIELD_CONTRACT_CLASSES.UNKNOWN_TIMING,
    };
}

// ===========================================================================
// field entry 构建辅助
// ===========================================================================

function _addMatchIdField(fields, transformOutput) {
    if (transformOutput.matchId !== undefined && transformOutput.matchId !== null) {
        fields.push(createFieldEntry({
            name: 'matchId',
            value: String(transformOutput.matchId),
            field_path: 'matchId',
            field_contract_class: FIELD_CONTRACT_CLASSES.METADATA_ONLY,
            timing_class: TIMING_CLASSES.FIXTURE_METADATA,
            model_eligibility: MODEL_ELIGIBILITY.AUDIT_ONLY,
            warnings: ['matchId is metadata_only — allowed for join/filter, forbidden as feature'],
        }));
    }
}

function _addRawBlockField(fields, blockName, value, warning) {
    if (value !== undefined && value !== null) {
        fields.push(createFieldEntry({
            name: blockName,
            value,
            field_path: blockName,
            field_contract_class: FIELD_CONTRACT_CLASSES.DEBUG_OR_RAW_ONLY,
            timing_class: TIMING_CLASSES.RAW_ONLY,
            model_eligibility: MODEL_ELIGIBILITY.FORBIDDEN_RAW_ONLY,
            warnings: [warning],
        }));
    }
}

function _addClassifiedContentField(fields, fieldPath, value, warnings) {
    const classification = classifyField(fieldPath, value);
    fields.push(createFieldEntry({
        name: fieldPath,
        value,
        field_path: fieldPath,
        field_contract_class: classification.contractClass,
        timing_class: classification.timingClass,
        model_eligibility: classification.modelEligibility,
        warnings,
    }));
}

function _addMetaFields(fields, _meta) {
    const metaSubFields = ['source', 'hasStats', 'hasLineup', 'hasShotmap'];
    for (const key of metaSubFields) {
        if (_meta[key] !== undefined && _meta[key] !== null) {
            fields.push(createFieldEntry({
                name: `_meta.${key}`,
                value: _meta[key],
                field_path: `_meta.${key}`,
                field_contract_class: FIELD_CONTRACT_CLASSES.DEBUG_OR_RAW_ONLY,
                timing_class: TIMING_CLASSES.RAW_ONLY,
                model_eligibility: MODEL_ELIGIBILITY.AUDIT_ONLY,
                warnings: ['_meta field — audit/evidence only, not a model feature'],
            }));
        }
    }
}

// ===========================================================================
// 字段 flatten
// ===========================================================================

function _addContentSubFields(fields, content, _meta) {
    const subFields = [
        { key: 'hasStats', path: 'content.stats',
            warnings: ['postmatch match statistics (xG, shots, possession, corners, fouls, etc.)', 'forbidden from entering prematch model'] },
        { key: 'hasShotmap', path: 'content.shotmap',
            warnings: ['postmatch shotmap data — forbidden from entering prematch model'] },
        { key: 'hasLineup', path: 'content.lineup',
            warnings: ['lineup timing unknown — may be prematch or postmatch', 'forbidden without observed_at and cutoff evidence'] },
    ];

    // extra sub-fields not gated by _meta flags
    const extraSubFields = [
        { condition: content && content.events, path: 'content.events',
            warnings: ['match events/timeline — postmatch data'] },
    ];

    for (const sf of subFields) {
        if (_meta[sf.key] || (content && content[sf.path.split('.')[1]])) {
            const value = (content && content[sf.path.split('.')[1]]) || null;
            _addClassifiedContentField(fields, sf.path, value, sf.warnings);
        }
    }
    for (const sf of extraSubFields) {
        if (sf.condition) {
            const fieldKey = sf.path.split('.')[1];
            _addClassifiedContentField(fields, sf.path, content[fieldKey], sf.warnings);
        }
    }
}

function flattenTransformOutputFields(transformOutput) {
    const fields = [];
    const _meta = transformOutput._meta || {};
    const content = transformOutput.content;

    _addMatchIdField(fields, transformOutput);
    _addRawBlockField(fields, 'content', content, 'content is raw pageProps content — use as evidence only, not as model feature');
    _addContentSubFields(fields, content, _meta);
    _addRawBlockField(fields, 'general', transformOutput.general, 'general is raw pageProps data — use as evidence only');
    _addRawBlockField(fields, 'header', transformOutput.header, 'header is raw pageProps data — use as evidence only');
    _addMetaFields(fields, _meta);

    return fields;
}

// ===========================================================================
// envelope metadata 构建辅助
// ===========================================================================

function _validateInput(transformOutput) {
    if (!transformOutput || typeof transformOutput !== 'object') {
        throw new Error(
            'adaptTransformToApiFormatOutputToEnvelope: transformOutput must be a non-null object, ' +
            `received ${transformOutput === null ? 'null' : typeof transformOutput}`
        );
    }
    if (transformOutput.matchId === undefined || transformOutput.matchId === null) {
        throw new Error(
            'adaptTransformToApiFormatOutputToEnvelope: transformOutput.matchId is required, ' +
            `received ${JSON.stringify(transformOutput.matchId)}`
        );
    }
}

function _buildPayloadMeta(safeOpts) {
    return {
        payload_type: PAYLOAD_TYPES.PARSER_INPUT,
        payload_hash: safeOpts.payloadHash !== undefined ? safeOpts.payloadHash : null,
        captured_at: safeOpts.capturedAt !== undefined ? safeOpts.capturedAt : null,
        data_version: safeOpts.dataVersion !== undefined
            ? (safeOpts.dataVersion === null ? null : String(safeOpts.dataVersion))
            : 'unknown',
        storage_path: safeOpts.storagePath !== undefined ? safeOpts.storagePath : null,
        source_url: safeOpts.sourceUrl !== undefined ? safeOpts.sourceUrl : null,
        final_url: safeOpts.finalUrl !== undefined ? safeOpts.finalUrl : null,
        fetched_at: safeOpts.fetchedAt !== undefined ? safeOpts.fetchedAt : null,
    };
}

function _buildEnvelopeWarnings(dataVersion, payloadHash, capturedAt, fetchedAt) {
    const warnings = [];
    if (dataVersion === 'unknown') {
        warnings.push('payload.data_version is unknown — canonical version not confirmed in this payload');
    }
    if (payloadHash === null) {
        warnings.push('payload.payload_hash is null — hash not computed at adapter level');
    }
    if (capturedAt === null && fetchedAt === null) {
        warnings.push(
            'payload.captured_at and fetched_at are both null — ' +
            'transformOutput._meta.extractedAt exists but is not equivalent to captured_at/fetched_at'
        );
    }
    return warnings;
}

function _addExtractedAtField(envelope, legacyExtractedAt, capturedAt, fetchedAt) {
    if (!legacyExtractedAt) return;
    const extractedWarnings = [
        'legacy extractedAt from NextDataParser._meta — this is parser execution time, not data capture time',
    ];
    if (capturedAt !== null || fetchedAt !== null) {
        extractedWarnings.push('captured_at or fetched_at is present — extractedAt is retained as supplementary audit evidence only');
    } else {
        extractedWarnings.push('null is acceptable for missing capture metadata — do not use extractedAt as captured_at');
    }
    envelope.fields.push(createFieldEntry({
        name: '_meta.extractedAt',
        value: legacyExtractedAt,
        field_path: '_meta.extractedAt',
        field_contract_class: FIELD_CONTRACT_CLASSES.DEBUG_OR_RAW_ONLY,
        timing_class: TIMING_CLASSES.RAW_ONLY,
        model_eligibility: MODEL_ELIGIBILITY.AUDIT_ONLY,
        warnings: extractedWarnings,
    }));
}

// ===========================================================================
// 主入口
// ===========================================================================

function adaptTransformToApiFormatOutputToEnvelope(transformOutput, options = {}) {
    _validateInput(transformOutput);

    const safeOpts = options && typeof options === 'object' ? options : {};
    const payloadMeta = _buildPayloadMeta(safeOpts);
    const envelopeWarnings = _buildEnvelopeWarnings(
        payloadMeta.data_version, payloadMeta.payload_hash, payloadMeta.captured_at,
        safeOpts.fetchedAt !== undefined ? safeOpts.fetchedAt : null
    );

    const legacyExtractedAt = transformOutput._meta && transformOutput._meta.extractedAt
        ? String(transformOutput._meta.extractedAt)
        : null;

    const envelope = createEmptyEnvelope({
        match_id: String(transformOutput.matchId),
        source: safeOpts.source || 'fotmob',
        payload: payloadMeta,
        parser: {
            parser_name: safeOpts.parserName || 'NextDataParser.transformToApiFormat',
            parser_version: safeOpts.parserVersion || 'legacy-static',
            parsed_at: safeOpts.parsedAt !== undefined ? safeOpts.parsedAt : null,
        },
        warnings: envelopeWarnings,
    });

    envelope.fields = flattenTransformOutputFields(transformOutput);
    _addExtractedAtField(envelope, legacyExtractedAt, payloadMeta.captured_at,
        safeOpts.fetchedAt !== undefined ? safeOpts.fetchedAt : null);

    return envelope;
}

// ===========================================================================
// 导出
// ===========================================================================

module.exports = {
    adaptTransformToApiFormatOutputToEnvelope,
    classifyField,
    flattenTransformOutputFields,
};
