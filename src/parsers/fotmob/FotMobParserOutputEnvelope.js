/**
 * FotMobParserOutputEnvelope — FotMob Parser Output Envelope Schema
 * ================================================================
 *
 * 定义 FotMob parser 未来输出 envelope 的数据结构、常量枚举和轻量校验辅助函数。
 *
 * 本文件是 DATA-L1E-1 的 schema-only 产物。它只定义结构，不接入任何 parser runtime。
 * 纯定义：无网络、无 DB、无文件 I/O、无副作用。
 *
 * 父文档:
 *   - DATA-L1A: FotMob prematch data boundary audit
 *   - DATA-L1B: FotMob prematch field contract
 *   - DATA-L1C: FotMob raw payload retention replay policy
 *   - DATA-L1D: FotMob parser field provenance timing labels design
 *   - DATA-L1E: FotMob parser output envelope implementation plan
 *
 * lifecycle: permanent
 * @module parsers/fotmob/FotMobParserOutputEnvelope
 */

'use strict';

// ===========================================================================
// 1. 字段合同分类 — 来自 DATA-L1B
// ===========================================================================

/**
 * 字段合同分类（field contract class）。
 *
 * 直接映射 DATA-L1B 的 5 类字段合同。这是所有标签的"根分类"——
 * 决定一个字段是否属于赛前安全字段、赛后字段、未知时间字段等。
 *
 * @readonly
 * @enum {string}
 */
const FIELD_CONTRACT_CLASSES = Object.freeze({
    /** 经审计确认在赛前即可用的字段。需要经过 cutoff 检查才能放行进入模型。 */
    SAFE_PREMATCH_CANDIDATE: 'safe_prematch_candidate',

    /** 经审计确认仅在赛后存在的字段。绝对禁止进入赛前模型。 */
    UNSAFE_POSTMATCH: 'unsafe_postmatch',

    /** 无法确定时间归属的字段。默认禁止进入模型，除非后续 audit 提供 observed_at 证据并升级。 */
    UNKNOWN_TIMING: 'unknown_timing',

    /** 仅作为元数据的字段（如 matchId、leagueId）。作为特征时禁止；用于 join/filter 时允许。 */
    METADATA_ONLY: 'metadata_only',

    /** 仅用于调试或原始数据追踪的字段。永远不进模型。 */
    DEBUG_OR_RAW_ONLY: 'debug_or_raw_only',
});

// ===========================================================================
// 2. 时间分类 — 来自 DATA-L1D §7.2
// ===========================================================================

/**
 * 字段时间分类（timing class）。
 *
 * 描述字段在比赛时间线中的位置——比赛开始前多久存在、赛中产生还是赛后产生。
 * 没有 timing label 的字段，默认不能信任。
 *
 * @readonly
 * @enum {string}
 */
const TIMING_CLASSES = Object.freeze({
    /** 赛程元数据（联赛、轮次、开球时间、队名）。赛前确定，不随比赛进行而变化。 */
    FIXTURE_METADATA: 'fixture_metadata',

    /** 赛前快照（如初盘赔率、赛前阵容公告）。早于开球一定时间存在。 */
    PREMATCH_SNAPSHOT: 'prematch_snapshot',

    /** 接近开球的快照（如临场阵容、最新赔率）。接近 kickoff 时间点。 */
    NEAR_KICKOFF_SNAPSHOT: 'near_kickoff_snapshot',

    /** 赛中实时数据（如实时比分、实时控球率）。仅比赛进行中产生。 */
    LIVE_MATCH: 'live_match',

    /** 赛后数据（如 xG、shots、最终比分、球员评分）。比赛结束后才能确定。绝对禁止进入赛前模型。 */
    POSTMATCH: 'postmatch',

    /** 无法确定时间归属。没有证据证明字段在 cutoff 前存在。默认禁止进入模型。 */
    UNKNOWN_TIMING: 'unknown_timing',

    /** 从历史数据衍生而来（如历史交锋记录、近期战绩）。时间维度不是"某场比赛的时刻"而是"历史窗口"。 */
    DERIVED_FROM_HISTORY: 'derived_from_history',

    /** 原始 payload 或原始数据块（pageProps / __NEXT_DATA__ / HTML hydration）。只能作为来源证据，禁止直接进入模型。 */
    RAW_ONLY: 'raw_only',
});

// ===========================================================================
// 3. 模型准入标签 — 来自 DATA-L1D §8
// ===========================================================================

/**
 * 模型准入标签（model eligibility）。
 *
 * parser 根据 DATA-L1B 字段合同 + payload metadata 给出字段级的初步准入判定。
 * 最终 enforcement 由 feature engine / training / backtest 执行。
 *
 * @readonly
 * @enum {string}
 */
const MODEL_ELIGIBILITY = Object.freeze({
    /** 显式允许进入模型。字段已通过所有检查（合同 + timing + cutoff）。 */
    ALLOWED_CANDIDATE: 'allowed_candidate',

    /** 有条件允许——需要 feature engine 侧做 cutoff 交叉检查后才能放行。 */
    CANDIDATE_IF_CUTOFF_VALID: 'candidate_if_cutoff_valid',

    /** 禁止——字段属于赛后数据，绝对禁止进入赛前模型。 */
    FORBIDDEN_POSTMATCH: 'forbidden_postmatch',

    /** 禁止——字段时间归属未知，默认不可信。 */
    FORBIDDEN_UNKNOWN_TIMING: 'forbidden_unknown_timing',

    /** 禁止——字段来自原始 payload，不能作为模型特征。 */
    FORBIDDEN_RAW_ONLY: 'forbidden_raw_only',

    /** 禁止——字段是 metadata_only 类型但被当作特征使用。 */
    FORBIDDEN_METADATA_ONLY: 'forbidden_metadata_only',

    /** 禁止——字段违反了 DATA-L1B 合同约定（被明确禁止但仍试图进入模型）。 */
    FORBIDDEN_CONTRACT_VIOLATION: 'forbidden_contract_violation',

    /** 仅供审计——字段进入 envelope 但仅用于审计追踪，不参与任何模型计算。 */
    AUDIT_ONLY: 'audit_only',
});

// ===========================================================================
// 4. payload 类型 — 来自 DATA-L1C
// ===========================================================================

/**
 * payload 类型（payload type）。
 *
 * 标记 parser 输入的原始数据格式。不同类型对应不同的 parser 入口和处理逻辑。
 *
 * @readonly
 * @enum {string}
 */
const PAYLOAD_TYPES = Object.freeze({
    /** FotMob 原始 API JSON 响应。 */
    RAW_JSON: 'raw_json',

    /** Next.js pageProps（SSR 序列化后的页面数据）。 */
    PAGE_PROPS: 'pageProps',

    /** Next.js __NEXT_DATA__ 内联脚本。 */
    NEXT_DATA: 'next_data',

    /** HTML 中的 hydration 数据块。 */
    HTML_HYDRATION: 'html_hydration',

    /** 已经过初步解析、可以直接送入 parser 的结构。 */
    PARSER_INPUT: 'parser_input',

    /** 未知来源。payload 类型未确认或无法确定。 */
    UNKNOWN: 'unknown',
});

// ===========================================================================
// 5. envelope shape 定义
// ===========================================================================

/**
 * 创建最小合法 envelope。
 *
 * 返回一个完整的 envelope 骨架，所有必选字段都有保守默认值。
 * 不读取任何外部数据，不访问网络、文件或 DB。
 *
 * @param {Object} [overrides={}] — 覆盖默认值的字段
 * @returns {Object} 最小 envelope 结构
 *
 * @example
 *   const env = createEmptyEnvelope({ match_id: '4830507' });
 *   // env.payload.payload_type === 'unknown'
 *   // env.fields === []
 */
function createEmptyEnvelope(overrides = {}) {
    const base = {
        /** 比赛 ID（FotMob matchId）。 */
        match_id: null,

        /** 数据来源标识。 */
        source: 'fotmob',

        /** payload 层面的元数据。来自 DATA-L1C。 */
        payload: {
            payload_type: PAYLOAD_TYPES.UNKNOWN,
            payload_hash: null,
            captured_at: null,
            data_version: null,
            storage_path: null,
            source_url: null,
            final_url: null,
        },

        /** parser 层面的元数据。 */
        parser: {
            parser_name: null,
            parser_version: null,
            parsed_at: null,
        },

        /** 字段数组。每个元素是一个 field entry。 */
        fields: [],

        /** 顶层 warnings。记录 envelope 级别的问题（如 payload metadata 缺失）。 */
        warnings: [],
    };

    // 浅合并 overrides：只允许覆盖顶层 key
    if (overrides && typeof overrides === 'object') {
        for (const key of Object.keys(overrides)) {
            if (key in base) {
                base[key] = overrides[key];
            }
        }
    }

    return base;
}

/**
 * 创建单个字段 entry。
 *
 * 返回一个字段 entry 的完整骨架，所有标签默认保守（unknown_timing / forbidden_unknown_timing）。
 * 纯函数，不判断真实 FotMob 字段。
 *
 * @param {Object} [overrides={}] — 覆盖默认值的字段
 * @returns {Object} 字段 entry 结构
 *
 * @example
 *   const entry = createFieldEntry({ name: 'home_team', value: 'PSG' });
 *   // entry.field_contract_class === 'unknown_timing'
 *   // entry.model_eligibility === 'forbidden_unknown_timing'
 */
function createFieldEntry(overrides = {}) {
    const base = {
        /** 字段名（人类可读）。 */
        name: null,

        /** 字段值（任意类型）。 */
        value: null,

        /** 字段在 raw payload 中的 JSONPath 式路径。 */
        field_path: null,

        /** 字段合同分类（来自 DATA-L1B）。默认 unknown_timing——没有证据就不能假设安全。 */
        field_contract_class: FIELD_CONTRACT_CLASSES.UNKNOWN_TIMING,

        /** 字段时间分类（来自 DATA-L1D §7.2）。默认 unknown_timing。 */
        timing_class: TIMING_CLASSES.UNKNOWN_TIMING,

        /** 字段被观察到的时间点（ISO 8601）。null 表示未记录。 */
        observed_at: null,

        /** 模型准入标签（初步判定）。默认 forbidden_unknown_timing——保守策略。 */
        model_eligibility: MODEL_ELIGIBILITY.FORBIDDEN_UNKNOWN_TIMING,

        /** 字段级别的 warnings（如 field_path 不确定、timing_class 可能过时）。 */
        warnings: [],
    };

    if (overrides && typeof overrides === 'object') {
        for (const key of Object.keys(overrides)) {
            if (key in base) {
                base[key] = overrides[key];
            }
        }
    }

    return base;
}

/**
 * 轻量 envelope shape 校验。
 *
 * 只检查 envelope 是否具有最小结构（payload/parser/fields 存在且类型正确）。
 * 不做业务阻断，不访问文件、网络、DB。
 *
 * @param {Object} envelope — 待校验的 envelope 对象
 * @returns {{ valid: boolean, errors: string[] }} 校验结果
 *
 * @example
 *   const result = validateEnvelopeShape(createEmptyEnvelope());
 *   // result.valid === true
 *   // result.errors === []
 */
function validateEnvelopeShape(envelope) {
    const errors = [];

    if (!envelope || typeof envelope !== 'object') {
        errors.push('envelope must be a non-null object');
        return { valid: false, errors };
    }

    // payload 块
    if (!envelope.payload || typeof envelope.payload !== 'object') {
        errors.push('envelope.payload must be a non-null object');
    } else {
        if (envelope.payload.payload_type === undefined) {
            errors.push('envelope.payload.payload_type is missing');
        }
    }

    // parser 块
    if (!envelope.parser || typeof envelope.parser !== 'object') {
        errors.push('envelope.parser must be a non-null object');
    }

    // fields 数组
    if (!Array.isArray(envelope.fields)) {
        errors.push('envelope.fields must be an array');
    }

    return { valid: errors.length === 0, errors };
}

/**
 * 检查 field entry 是否被标记为 forbidden。
 *
 * 纯工具函数，供未来 feature engine / dry-run checker 使用。
 *
 * @param {Object} fieldEntry — 单个字段 entry
 * @returns {boolean} 如果 model_eligibility 以 'forbidden_' 开头则返回 true
 */
function isForbidden(fieldEntry) {
    if (!fieldEntry || typeof fieldEntry.model_eligibility !== 'string') {
        return true; // 没有 eligibility 标签 → 保守拒绝
    }
    return fieldEntry.model_eligibility.startsWith('forbidden_');
}

/**
 * 检查 field entry 是否有条件允许（candidate_if_cutoff_valid）。
 *
 * @param {Object} fieldEntry — 单个字段 entry
 * @returns {boolean} 如果需要 cutoff 交叉检查则返回 true
 */
function isCandidateIfCutoffValid(fieldEntry) {
    if (!fieldEntry || typeof fieldEntry.model_eligibility !== 'string') {
        return false;
    }
    return fieldEntry.model_eligibility === MODEL_ELIGIBILITY.CANDIDATE_IF_CUTOFF_VALID;
}

/**
 * 检查 field entry 是否显式允许。
 *
 * @param {Object} fieldEntry — 单个字段 entry
 * @returns {boolean} 如果 model_eligibility 为 allowed_candidate 则返回 true
 */
function isAllowed(fieldEntry) {
    if (!fieldEntry || typeof fieldEntry.model_eligibility !== 'string') {
        return false;
    }
    return fieldEntry.model_eligibility === MODEL_ELIGIBILITY.ALLOWED_CANDIDATE;
}

// ===========================================================================
// 导出
// ===========================================================================

module.exports = {
    // 常量枚举
    FIELD_CONTRACT_CLASSES,
    TIMING_CLASSES,
    MODEL_ELIGIBILITY,
    PAYLOAD_TYPES,

    // 工厂 / 辅助函数
    createEmptyEnvelope,
    createFieldEntry,
    validateEnvelopeShape,
    isForbidden,
    isCandidateIfCutoffValid,
    isAllowed,
};
