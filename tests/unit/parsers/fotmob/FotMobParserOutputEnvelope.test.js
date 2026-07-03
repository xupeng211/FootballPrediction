/**
 * FotMobParserOutputEnvelope 单元测试
 * ===================================
 *
 * 测试 envelope schema 常量、工厂函数和轻量校验辅助函数。
 * 纯静态测试：不访问网络、文件、DB、FotMob parser runtime。
 *
 * lifecycle: permanent
 */

'use strict';

const { describe, test } = require('node:test');
const assert = require('node:assert/strict');

const {
    FIELD_CONTRACT_CLASSES,
    TIMING_CLASSES,
    MODEL_ELIGIBILITY,
    PAYLOAD_TYPES,
    createEmptyEnvelope,
    createFieldEntry,
    validateEnvelopeShape,
    isForbidden,
    isCandidateIfCutoffValid,
    isAllowed,
} = require('../../../../src/parsers/fotmob/FotMobParserOutputEnvelope');

// ===========================================================================
// 常量存在性
// ===========================================================================

describe('FIELD_CONTRACT_CLASSES', () => {
    test('应包含 DATA-L1B 定义的 5 类字段合同', () => {
        const values = Object.values(FIELD_CONTRACT_CLASSES);
        assert.ok(values.includes('safe_prematch_candidate'));
        assert.ok(values.includes('unsafe_postmatch'));
        assert.ok(values.includes('unknown_timing'));
        assert.ok(values.includes('metadata_only'));
        assert.ok(values.includes('debug_or_raw_only'));
        assert.equal(values.length, 5);
    });

    test('应是冻结对象（immutable）', () => {
        assert.throws(
            () => { FIELD_CONTRACT_CLASSES.NEW_KEY = 'should_fail'; },
            /object is not extensible|Cannot add property/
        );
    });
});

describe('TIMING_CLASSES', () => {
    test('应包含 DATA-L1D 定义的 8 类 timing class', () => {
        const values = Object.values(TIMING_CLASSES);
        assert.ok(values.includes('fixture_metadata'));
        assert.ok(values.includes('prematch_snapshot'));
        assert.ok(values.includes('near_kickoff_snapshot'));
        assert.ok(values.includes('live_match'));
        assert.ok(values.includes('postmatch'));
        assert.ok(values.includes('unknown_timing'));
        assert.ok(values.includes('derived_from_history'));
        assert.ok(values.includes('raw_only'));
        assert.equal(values.length, 8);
    });
});

describe('MODEL_ELIGIBILITY', () => {
    test('应包含 8 类 model eligibility', () => {
        const values = Object.values(MODEL_ELIGIBILITY);
        assert.ok(values.includes('allowed_candidate'));
        assert.ok(values.includes('candidate_if_cutoff_valid'));
        assert.ok(values.includes('forbidden_postmatch'));
        assert.ok(values.includes('forbidden_unknown_timing'));
        assert.ok(values.includes('forbidden_raw_only'));
        assert.ok(values.includes('forbidden_metadata_only'));
        assert.ok(values.includes('forbidden_contract_violation'));
        assert.ok(values.includes('audit_only'));
        assert.equal(values.length, 8);
    });
});

describe('PAYLOAD_TYPES', () => {
    test('应包含 DATA-L1C 定义的 payload 类型', () => {
        const values = Object.values(PAYLOAD_TYPES);
        assert.ok(values.includes('raw_json'));
        assert.ok(values.includes('pageProps'));
        assert.ok(values.includes('next_data'));
        assert.ok(values.includes('html_hydration'));
        assert.ok(values.includes('parser_input'));
        assert.ok(values.includes('unknown'));
        assert.equal(values.length, 6);
    });
});

// ===========================================================================
// createEmptyEnvelope
// ===========================================================================

describe('createEmptyEnvelope', () => {
    test('应返回包含 payload/parser/fields/warnings 的最小结构', () => {
        const env = createEmptyEnvelope();
        assert.equal(typeof env, 'object');
        assert.notEqual(env, null);
        assert.equal(env.source, 'fotmob');
        assert.equal(typeof env.payload, 'object');
        assert.equal(typeof env.parser, 'object');
        assert.ok(Array.isArray(env.fields));
        assert.ok(Array.isArray(env.warnings));
        assert.equal(env.fields.length, 0);
    });

    test('payload 块应有保守默认值', () => {
        const env = createEmptyEnvelope();
        assert.equal(env.payload.payload_type, 'unknown');
        assert.equal(env.payload.payload_hash, null);
        assert.equal(env.payload.captured_at, null);
        assert.equal(env.payload.data_version, null);
        assert.equal(env.payload.storage_path, null);
        assert.equal(env.payload.source_url, null);
        assert.equal(env.payload.final_url, null);
    });

    test('parser 块应有保守默认值', () => {
        const env = createEmptyEnvelope();
        assert.equal(env.parser.parser_name, null);
        assert.equal(env.parser.parser_version, null);
        assert.equal(env.parser.parsed_at, null);
    });

    test('match_id 默认为 null', () => {
        const env = createEmptyEnvelope();
        assert.equal(env.match_id, null);
    });

    test('应接受 overrides 覆盖 match_id', () => {
        const env = createEmptyEnvelope({ match_id: '4830507' });
        assert.equal(env.match_id, '4830507');
    });

    test('应忽略 overrides 中的未知 key', () => {
        const env = createEmptyEnvelope({ not_a_real_key: 'oops' });
        assert.equal(env.not_a_real_key, undefined);
    });

    test('overrides 为 null/undefined 时应返回默认结构', () => {
        const envNull = createEmptyEnvelope(null);
        const envUndef = createEmptyEnvelope(undefined);
        assert.equal(envNull.source, 'fotmob');
        assert.equal(envUndef.source, 'fotmob');
    });
});

// ===========================================================================
// createFieldEntry
// ===========================================================================

describe('createFieldEntry', () => {
    test('应返回包含必选字段的 entry 骨架', () => {
        const entry = createFieldEntry();
        assert.equal(typeof entry, 'object');
        assert.equal(entry.name, null);
        assert.equal(entry.value, null);
        assert.equal(entry.field_path, null);
        assert.equal(entry.observed_at, null);
        assert.ok(Array.isArray(entry.warnings));
    });

    test('默认 field_contract_class 应为 unknown_timing（保守）', () => {
        const entry = createFieldEntry();
        assert.equal(entry.field_contract_class, 'unknown_timing');
    });

    test('默认 timing_class 应为 unknown_timing（保守）', () => {
        const entry = createFieldEntry();
        assert.equal(entry.timing_class, 'unknown_timing');
    });

    test('默认 model_eligibility 应为 forbidden_unknown_timing（保守）', () => {
        const entry = createFieldEntry();
        assert.equal(entry.model_eligibility, 'forbidden_unknown_timing');
    });

    test('应接受 overrides 覆盖字段值', () => {
        const entry = createFieldEntry({
            name: 'home_team',
            value: 'Paris SG',
            field_path: '$.general.homeTeam.name',
            field_contract_class: FIELD_CONTRACT_CLASSES.SAFE_PREMATCH_CANDIDATE,
            timing_class: TIMING_CLASSES.FIXTURE_METADATA,
            model_eligibility: MODEL_ELIGIBILITY.CANDIDATE_IF_CUTOFF_VALID,
        });
        assert.equal(entry.name, 'home_team');
        assert.equal(entry.value, 'Paris SG');
        assert.equal(entry.field_path, '$.general.homeTeam.name');
        assert.equal(entry.field_contract_class, 'safe_prematch_candidate');
        assert.equal(entry.timing_class, 'fixture_metadata');
        assert.equal(entry.model_eligibility, 'candidate_if_cutoff_valid');
    });

    test('应忽略 overrides 中的未知 key', () => {
        const entry = createFieldEntry({ not_real: true });
        assert.equal(entry.not_real, undefined);
    });
});

// ===========================================================================
// validateEnvelopeShape
// ===========================================================================

describe('validateEnvelopeShape', () => {
    test('合法最小 envelope 应返回 valid: true', () => {
        const env = createEmptyEnvelope();
        const result = validateEnvelopeShape(env);
        assert.equal(result.valid, true);
        assert.equal(result.errors.length, 0);
    });

    test('null 输入应返回 valid: false', () => {
        const result = validateEnvelopeShape(null);
        assert.equal(result.valid, false);
        assert.ok(result.errors.length > 0);
    });

    test('非对象输入应返回 valid: false', () => {
        const result = validateEnvelopeShape('not an object');
        assert.equal(result.valid, false);
    });

    test('缺少 payload 应返回 valid: false', () => {
        const result = validateEnvelopeShape({ parser: {}, fields: [] });
        assert.equal(result.valid, false);
        assert.ok(result.errors.some(e => e.includes('payload')));
    });

    test('缺少 parser 应返回 valid: false', () => {
        const result = validateEnvelopeShape({ payload: {}, fields: [] });
        assert.equal(result.valid, false);
        assert.ok(result.errors.some(e => e.includes('parser')));
    });

    test('fields 不是数组应返回 valid: false', () => {
        const result = validateEnvelopeShape({ payload: {}, parser: {}, fields: 'not_array' });
        assert.equal(result.valid, false);
        assert.ok(result.errors.some(e => e.includes('fields')));
    });

    test('带合法 field entry 的 envelope 应返回 valid: true', () => {
        const env = createEmptyEnvelope();
        env.fields.push(createFieldEntry({ name: 'home_team' }));
        const result = validateEnvelopeShape(env);
        assert.equal(result.valid, true);
    });
});

// ===========================================================================
// isForbidden / isCandidateIfCutoffValid / isAllowed
// ===========================================================================

describe('isForbidden', () => {
    test('forbidden_postmatch → true', () => {
        const entry = createFieldEntry({ model_eligibility: MODEL_ELIGIBILITY.FORBIDDEN_POSTMATCH });
        assert.equal(isForbidden(entry), true);
    });

    test('forbidden_unknown_timing → true', () => {
        const entry = createFieldEntry();
        assert.equal(isForbidden(entry), true);
    });

    test('candidate_if_cutoff_valid → false', () => {
        const entry = createFieldEntry({ model_eligibility: MODEL_ELIGIBILITY.CANDIDATE_IF_CUTOFF_VALID });
        assert.equal(isForbidden(entry), false);
    });

    test('allowed_candidate → false', () => {
        const entry = createFieldEntry({ model_eligibility: MODEL_ELIGIBILITY.ALLOWED_CANDIDATE });
        assert.equal(isForbidden(entry), false);
    });

    test('null/undefined entry → true（保守拒绝）', () => {
        assert.equal(isForbidden(null), true);
        assert.equal(isForbidden(undefined), true);
    });

    test('没有 model_eligibility 的 entry → true（保守拒绝）', () => {
        assert.equal(isForbidden({ name: 'x' }), true);
    });
});

describe('isCandidateIfCutoffValid', () => {
    test('candidate_if_cutoff_valid → true', () => {
        const entry = createFieldEntry({ model_eligibility: MODEL_ELIGIBILITY.CANDIDATE_IF_CUTOFF_VALID });
        assert.equal(isCandidateIfCutoffValid(entry), true);
    });

    test('forbidden_postmatch → false', () => {
        const entry = createFieldEntry({ model_eligibility: MODEL_ELIGIBILITY.FORBIDDEN_POSTMATCH });
        assert.equal(isCandidateIfCutoffValid(entry), false);
    });

    test('null entry → false', () => {
        assert.equal(isCandidateIfCutoffValid(null), false);
    });
});

describe('isAllowed', () => {
    test('allowed_candidate → true', () => {
        const entry = createFieldEntry({ model_eligibility: MODEL_ELIGIBILITY.ALLOWED_CANDIDATE });
        assert.equal(isAllowed(entry), true);
    });

    test('candidate_if_cutoff_valid → false', () => {
        const entry = createFieldEntry({ model_eligibility: MODEL_ELIGIBILITY.CANDIDATE_IF_CUTOFF_VALID });
        assert.equal(isAllowed(entry), false);
    });

    test('null entry → false', () => {
        assert.equal(isAllowed(null), false);
    });
});
