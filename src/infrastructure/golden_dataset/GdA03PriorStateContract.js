'use strict';

// lifecycle: permanent
// GD-A03 的 feature identity / numeric-lineage contract。特征名称与顺序仍由
// config/model_feature_contracts.json 传入并校验；本文件只声明每个名称的
// 语义边界、可用性规则与 provenance 要求，不把历史 SchemaManager proxy
// 提升为数值权威。

const { GdA01ContractError, sha256Text, stableStringify } = require('./GdA01AssemblyContract');
const {
    AWAY_FIXTURES_PER_TEAM,
    FIXTURES_PER_TEAM,
    HOME_FIXTURES_PER_TEAM,
    TEAMS_PER_SEASON,
} = require('../canonical/CanonicalInventoryContract');

const PRIOR_STATE_ARTIFACT_SCHEMA_VERSION = 'golden-dataset-v1-gd-a03-prior-state-features-artifact/v1';
const PRIOR_STATE_RECEIPT_SCHEMA_VERSION = 'gd-a03-prior-state-feature-view-receipt/v2';
const PRIOR_STATE_LINEAGE_CONTRACT_VERSION = 'gd-a03-numeric-lineage/v2';
const SCHEDULE_TEAM_CLOSURE_SCHEMA_VERSION = 'canonical-schedule-team-closure/v1';
const GD_A03_SOURCE_BINDING_NAMES = Object.freeze([
    'canonical_schedule',
    'feature_contract',
    'gd_a01_artifact',
    'gd_a01_receipt',
    'gd_a02_artifact',
    'gd_a02_receipt',
    'runtime_feature_adapter',
]);
const SCHEDULE_TEAMS_PER_SEASON = TEAMS_PER_SEASON;
const SCHEDULE_FIXTURES_PER_TEAM = FIXTURES_PER_TEAM;
const SCHEDULE_HOME_FIXTURES_PER_TEAM = HOME_FIXTURES_PER_TEAM;
const SCHEDULE_AWAY_FIXTURES_PER_TEAM = AWAY_FIXTURES_PER_TEAM;
const PRIOR_STATE_STAGE = 'GD-A03';
const FEATURE_CUTOFF_POLICY = 'TARGET_KICKOFF_EXCLUSIVE';
const FEATURE_CUTOFF_RELATION = 'source_match_kickoff < target_match_kickoff';
const REQUIRED_ROLLING_HISTORY_COUNT = 5;
const FATIGUE_LOOKBACK_DAYS = 7;
const FEATURE_CONTRACT_ID = 'v26_7_aligned/v1';
const FEATURE_CONTRACT_VERSION = 'v26_6_pre_match/v1';
const FEATURE_COUNT = 20;

const FEATURE_AVAILABILITY = Object.freeze({
    AVAILABLE: 'AVAILABLE',
    UNAVAILABLE: 'UNAVAILABLE',
});

const SEMANTICS_STATUS = Object.freeze({
    PROVEN: 'PROVEN',
    PROVEN_DERIVED: 'PROVEN_DERIVED',
    UNAVAILABLE: 'UNAVAILABLE',
    SEMANTICS_UNPROVEN: 'SEMANTICS_UNPROVEN',
    BLOCKED_BY_HISTORY_CLOSURE: 'BLOCKED_BY_HISTORY_CLOSURE',
});

const FEATURE_FAMILIES = Object.freeze({
    rolling: 'rolling',
    standings: 'standings',
    advanced: 'advanced',
});

const REASON_CODES = Object.freeze({
    DEPENDENCY_UNAVAILABLE: 'DEPENDENCY_UNAVAILABLE',
    ELO_HISTORY_GAP: 'ELO_HISTORY_GAP',
    ELO_INITIAL_STATE_UNPROVEN: 'ELO_INITIAL_STATE_UNPROVEN',
    HISTORY_GAP: 'HISTORY_GAP',
    INSUFFICIENT_HISTORY: 'INSUFFICIENT_HISTORY',
    NO_PROVEN_SOURCE_FACT: 'NO_PROVEN_SOURCE_FACT',
    SEMANTICS_UNPROVEN: 'SEMANTICS_UNPROVEN',
    SOT_OWN_GOAL_FLAG_UNAVAILABLE: 'SOT_OWN_GOAL_FLAG_UNAVAILABLE',
    SOT_OWN_GOAL_SEMANTICS_UNPROVEN: 'SOT_OWN_GOAL_SEMANTICS_UNPROVEN',
    SOT_TEAM_IDENTITY_BINDING_UNPROVEN: 'SOT_TEAM_IDENTITY_BINDING_UNPROVEN',
    STANDINGS_HISTORY_GAP: 'STANDINGS_HISTORY_GAP',
    STANDINGS_TIEBREAK_UNPROVEN: 'STANDINGS_TIEBREAK_UNPROVEN',
});

const FEATURE_SEMANTICS = [
    {
        feature_name: 'rolling_xg_home',
        family: FEATURE_FAMILIES.rolling,
        intended_semantics: 'Target home team mean xG over its five actual prior official matches.',
        source_authority: 'GD-A02 facts artifact linked to canonical schedule identity.',
        source_fields: ['facts.xg.home.value', 'facts.xg.home.status=COMPLETE'],
        history_scope: 'Premier League, same season, target home team.',
        lookback_rule: 'Exactly five actual prior matches; source kickoff is strictly before cutoff.',
        derivation: 'Arithmetic mean of the five proven team-side xG values.',
        cutoff_rule: FEATURE_CUTOFF_RELATION,
        missing_history_policy: 'Null with HISTORY_GAP/INSUFFICIENT_HISTORY; never reach farther back.',
        cold_start_policy: 'Fewer than five prior matches is unavailable.',
        provenance_requirements: 'Every source canonical ID, kickoff, GD-A02 staging/business hash and xG path.',
        semantics_status: SEMANTICS_STATUS.PROVEN_DERIVED,
    },
    {
        feature_name: 'rolling_xg_away',
        family: FEATURE_FAMILIES.rolling,
        intended_semantics: 'Target away team mean xG over its five actual prior official matches.',
        source_authority: 'GD-A02 facts artifact linked to canonical schedule identity.',
        source_fields: ['facts.xg.home.value or facts.xg.away.value by team side', 'facts.xg.<side>.status=COMPLETE'],
        history_scope: 'Premier League, same season, target away team.',
        lookback_rule: 'Exactly five actual prior matches; source kickoff is strictly before cutoff.',
        derivation: 'Arithmetic mean of the five proven team-side xG values.',
        cutoff_rule: FEATURE_CUTOFF_RELATION,
        missing_history_policy: 'Null with HISTORY_GAP/INSUFFICIENT_HISTORY; never reach farther back.',
        cold_start_policy: 'Fewer than five prior matches is unavailable.',
        provenance_requirements: 'Every source canonical ID, kickoff, GD-A02 staging/business hash and xG path.',
        semantics_status: SEMANTICS_STATUS.PROVEN_DERIVED,
    },
    {
        feature_name: 'rolling_shots_on_target_home',
        family: FEATURE_FAMILIES.rolling,
        intended_semantics: 'Target home team mean shots on target over five actual prior matches.',
        source_authority: 'GD-A02 v2 facts projection from the existing validated FotMob normalized shotmap.',
        source_fields: [
            'facts.shots_on_target.home.value',
            'facts.shots_on_target.home.status=COMPLETE',
            'facts.shots_on_target source path=normalized.shotmap.shots[*].isOnTarget',
        ],
        history_scope: 'Premier League, same season, target home team.',
        lookback_rule: 'Exactly five actual prior matches would be required.',
        derivation: 'Arithmetic mean of the five proven team-side on-target shot counts.',
        cutoff_rule: FEATURE_CUTOFF_RELATION,
        missing_history_policy: 'Null with NO_PROVEN_SOURCE_FACT; no goals or shot proxy.',
        cold_start_policy: 'Unavailable.',
        provenance_requirements: 'Every source canonical ID, kickoff, GD-A02 staging/business hash and shotmap path.',
        semantics_status: SEMANTICS_STATUS.SEMANTICS_UNPROVEN,
    },
    {
        feature_name: 'rolling_shots_on_target_away',
        family: FEATURE_FAMILIES.rolling,
        intended_semantics: 'Target away team mean shots on target over five actual prior matches.',
        source_authority: 'GD-A02 v2 facts projection from the existing validated FotMob normalized shotmap.',
        source_fields: [
            'facts.shots_on_target.away.value',
            'facts.shots_on_target.away.status=COMPLETE',
            'facts.shots_on_target source path=normalized.shotmap.shots[*].isOnTarget',
        ],
        history_scope: 'Premier League, same season, target away team.',
        lookback_rule: 'Exactly five actual prior matches would be required.',
        derivation: 'Arithmetic mean of the five proven team-side on-target shot counts.',
        cutoff_rule: FEATURE_CUTOFF_RELATION,
        missing_history_policy: 'Null with NO_PROVEN_SOURCE_FACT; no goals or shot proxy.',
        cold_start_policy: 'Unavailable.',
        provenance_requirements: 'Every source canonical ID, kickoff, GD-A02 staging/business hash and shotmap path.',
        semantics_status: SEMANTICS_STATUS.SEMANTICS_UNPROVEN,
    },
    {
        feature_name: 'rolling_possession_home',
        family: FEATURE_FAMILIES.rolling,
        intended_semantics: 'Target home team mean possession over five actual prior matches.',
        source_authority: 'No accepted numeric field in the GD-A02 factual projection.',
        source_fields: ['GD-A02 sections.stats is fingerprint-only; no numeric possession value'],
        history_scope: 'Premier League, same season, target home team.',
        lookback_rule: 'Exactly five actual prior matches would be required.',
        derivation: 'No derivation is permitted until a numeric source field is contractually projected.',
        cutoff_rule: FEATURE_CUTOFF_RELATION,
        missing_history_policy: 'Null with NO_PROVEN_SOURCE_FACT; no 50/55/45 proxy.',
        cold_start_policy: 'Unavailable.',
        provenance_requirements: 'A future source must bind field path, source hash and source match ID.',
        semantics_status: SEMANTICS_STATUS.UNAVAILABLE,
    },
    {
        feature_name: 'rolling_possession_away',
        family: FEATURE_FAMILIES.rolling,
        intended_semantics: 'Target away team mean possession over five actual prior matches.',
        source_authority: 'No accepted numeric field in the GD-A02 factual projection.',
        source_fields: ['GD-A02 sections.stats is fingerprint-only; no numeric possession value'],
        history_scope: 'Premier League, same season, target away team.',
        lookback_rule: 'Exactly five actual prior matches would be required.',
        derivation: 'No derivation is permitted until a numeric source field is contractually projected.',
        cutoff_rule: FEATURE_CUTOFF_RELATION,
        missing_history_policy: 'Null with NO_PROVEN_SOURCE_FACT; no 50/55/45 proxy.',
        cold_start_policy: 'Unavailable.',
        provenance_requirements: 'A future source must bind field path, source hash and source match ID.',
        semantics_status: SEMANTICS_STATUS.UNAVAILABLE,
    },
    {
        feature_name: 'rolling_team_rating_home',
        family: FEATURE_FAMILIES.rolling,
        intended_semantics: 'Target home team rolling rating under a proven, versioned rating algorithm.',
        source_authority: 'No authoritative rating formula is established for GD-A03 V1.',
        source_fields: ['No accepted rating observation or frozen rating algorithm.'],
        history_scope: 'Would require the same five prior matches plus a proven rating contract.',
        lookback_rule: 'Exactly five actual prior matches would be required by the canonical adapter.',
        derivation: 'No value; current xG/possession/shots weighted proxy is compatibility behavior only.',
        cutoff_rule: FEATURE_CUTOFF_RELATION,
        missing_history_policy: 'Null with SEMANTICS_UNPROVEN.',
        cold_start_policy: 'Unavailable.',
        provenance_requirements: 'Versioned rating formula, inputs, source IDs and cutoff proof.',
        semantics_status: SEMANTICS_STATUS.SEMANTICS_UNPROVEN,
    },
    {
        feature_name: 'rolling_team_rating_away',
        family: FEATURE_FAMILIES.rolling,
        intended_semantics: 'Target away team rolling rating under a proven, versioned rating algorithm.',
        source_authority: 'No authoritative rating formula is established for GD-A03 V1.',
        source_fields: ['No accepted rating observation or frozen rating algorithm.'],
        history_scope: 'Would require the same five prior matches plus a proven rating contract.',
        lookback_rule: 'Exactly five actual prior matches would be required by the canonical adapter.',
        derivation: 'No value; current xG/possession/shots weighted proxy is compatibility behavior only.',
        cutoff_rule: FEATURE_CUTOFF_RELATION,
        missing_history_policy: 'Null with SEMANTICS_UNPROVEN.',
        cold_start_policy: 'Unavailable.',
        provenance_requirements: 'Versioned rating formula, inputs, source IDs and cutoff proof.',
        semantics_status: SEMANTICS_STATUS.SEMANTICS_UNPROVEN,
    },
    {
        feature_name: 'home_table_position',
        family: FEATURE_FAMILIES.standings,
        intended_semantics: 'Exact league table position immediately before target kickoff.',
        source_authority:
            'Canonical schedule plus complete prior competition results; no exact tie-break authority is frozen.',
        source_fields: [
            'prior fixture result.home_score',
            'prior fixture result.away_score',
            'official tie-break rules',
        ],
        history_scope: 'All Premier League fixtures in the target season strictly before cutoff.',
        lookback_rule: 'Unbounded prior-season competition history; no target result.',
        derivation: 'No V1 value until full result closure and exact tie-break reproduction are proven.',
        cutoff_rule: FEATURE_CUTOFF_RELATION,
        missing_history_policy: 'Null with STANDINGS_HISTORY_GAP or STANDINGS_TIEBREAK_UNPROVEN.',
        cold_start_policy: 'Zero points does not identify an exact position; unavailable.',
        provenance_requirements: 'Complete league result ID set, goal data, tie-break contract and source hashes.',
        semantics_status: SEMANTICS_STATUS.SEMANTICS_UNPROVEN,
    },
    {
        feature_name: 'away_table_position',
        family: FEATURE_FAMILIES.standings,
        intended_semantics: 'Exact league table position immediately before target kickoff.',
        source_authority:
            'Canonical schedule plus complete prior competition results; no exact tie-break authority is frozen.',
        source_fields: [
            'prior fixture result.home_score',
            'prior fixture result.away_score',
            'official tie-break rules',
        ],
        history_scope: 'All Premier League fixtures in the target season strictly before cutoff.',
        lookback_rule: 'Unbounded prior-season competition history; no target result.',
        derivation: 'No V1 value until full result closure and exact tie-break reproduction are proven.',
        cutoff_rule: FEATURE_CUTOFF_RELATION,
        missing_history_policy: 'Null with STANDINGS_HISTORY_GAP or STANDINGS_TIEBREAK_UNPROVEN.',
        cold_start_policy: 'Zero points does not identify an exact position; unavailable.',
        provenance_requirements: 'Complete league result ID set, goal data, tie-break contract and source hashes.',
        semantics_status: SEMANTICS_STATUS.SEMANTICS_UNPROVEN,
    },
    {
        feature_name: 'table_position_diff',
        family: FEATURE_FAMILIES.standings,
        intended_semantics: 'Home exact prior table position minus away exact prior table position.',
        source_authority: 'Depends on both exact prior table positions.',
        source_fields: ['home_table_position', 'away_table_position'],
        history_scope: 'Same target-season prior competition table.',
        lookback_rule: 'Inherits both position lineages and strict cutoff.',
        derivation: 'home_table_position - away_table_position only when both are proven.',
        cutoff_rule: FEATURE_CUTOFF_RELATION,
        missing_history_policy: 'Null with DEPENDENCY_UNAVAILABLE.',
        cold_start_policy: 'Unavailable when either position is unavailable.',
        provenance_requirements: 'Both upstream position lineages and their source ID sets.',
        semantics_status: SEMANTICS_STATUS.SEMANTICS_UNPROVEN,
    },
    {
        feature_name: 'home_points',
        family: FEATURE_FAMILIES.standings,
        intended_semantics: 'Target home team competition points from all prior actual fixtures.',
        source_authority: 'GD-A02 match_result plus canonical schedule identity.',
        source_fields: ['facts.match_result.outcome', 'canonical schedule prior fixture IDs'],
        history_scope: 'Premier League, same season, target home team, all prior fixtures.',
        lookback_rule: 'All actual prior team fixtures; source kickoff is strictly before cutoff.',
        derivation: '3 for win, 1 for draw, 0 for loss, summed over the closed team history.',
        cutoff_rule: FEATURE_CUTOFF_RELATION,
        missing_history_policy: 'Null with HISTORY_GAP/STANDINGS_HISTORY_GAP if any scheduled prior result is absent.',
        cold_start_policy: 'Zero is proven when the canonical team history has no prior fixture.',
        provenance_requirements: 'Exact team prior ID set, every result fact provenance, schedule hash.',
        semantics_status: SEMANTICS_STATUS.PROVEN_DERIVED,
    },
    {
        feature_name: 'away_points',
        family: FEATURE_FAMILIES.standings,
        intended_semantics: 'Target away team competition points from all prior actual fixtures.',
        source_authority: 'GD-A02 match_result plus canonical schedule identity.',
        source_fields: ['facts.match_result.outcome', 'canonical schedule prior fixture IDs'],
        history_scope: 'Premier League, same season, target away team, all prior fixtures.',
        lookback_rule: 'All actual prior team fixtures; source kickoff is strictly before cutoff.',
        derivation: '3 for win, 1 for draw, 0 for loss, summed over the closed team history.',
        cutoff_rule: FEATURE_CUTOFF_RELATION,
        missing_history_policy: 'Null with HISTORY_GAP/STANDINGS_HISTORY_GAP if any scheduled prior result is absent.',
        cold_start_policy: 'Zero is proven when the canonical team history has no prior fixture.',
        provenance_requirements: 'Exact team prior ID set, every result fact provenance, schedule hash.',
        semantics_status: SEMANTICS_STATUS.PROVEN_DERIVED,
    },
    {
        feature_name: 'points_diff',
        family: FEATURE_FAMILIES.standings,
        intended_semantics: 'Home prior points minus away prior points.',
        source_authority: 'Depends on proven home_points and away_points.',
        source_fields: ['home_points', 'away_points'],
        history_scope: 'Same target-season prior team histories.',
        lookback_rule: 'Inherits both point lineages and strict cutoff.',
        derivation: 'home_points - away_points only when both are proven.',
        cutoff_rule: FEATURE_CUTOFF_RELATION,
        missing_history_policy: 'Null with DEPENDENCY_UNAVAILABLE.',
        cold_start_policy: 'Zero is allowed only when both team histories are proven empty.',
        provenance_requirements: 'Both upstream point lineages and source ID sets.',
        semantics_status: SEMANTICS_STATUS.PROVEN_DERIVED,
    },
    {
        feature_name: 'home_recent_form_points',
        family: FEATURE_FAMILIES.standings,
        intended_semantics: 'Target home team points over its five actual prior fixtures.',
        source_authority: 'GD-A02 match_result plus canonical schedule identity.',
        source_fields: ['facts.match_result.outcome', 'canonical schedule exact previous-five IDs'],
        history_scope: 'Premier League, same season, target home team.',
        lookback_rule: 'Exactly five actual prior fixtures; no shrinking or skipping.',
        derivation: 'Sum of 3/1/0 result points for the exact previous-five sequence.',
        cutoff_rule: FEATURE_CUTOFF_RELATION,
        missing_history_policy: 'Null with INSUFFICIENT_HISTORY or HISTORY_GAP.',
        cold_start_policy: 'Fewer than five actual prior fixtures is unavailable.',
        provenance_requirements: 'Exact five source IDs, result provenance for every source, schedule hash.',
        semantics_status: SEMANTICS_STATUS.PROVEN_DERIVED,
    },
    {
        feature_name: 'raw_elo_gap',
        family: FEATURE_FAMILIES.advanced,
        intended_semantics: 'Home minus away prior ELO under an authoritative frozen algorithm.',
        source_authority: 'No authoritative historical ELO universe/initialization contract is proven in V1.',
        source_fields: ['prior result universe', 'initial rating', 'K factor', 'home treatment', 'season boundary'],
        history_scope: 'Would require complete ordered competition history and pre-dataset initialization policy.',
        lookback_rule: 'All algorithm inputs strictly before cutoff.',
        derivation: 'No value; 1500 cold-start is not silently treated as observed history.',
        cutoff_rule: FEATURE_CUTOFF_RELATION,
        missing_history_policy: 'Null with ELO_INITIAL_STATE_UNPROVEN/ELO_HISTORY_GAP.',
        cold_start_policy: 'Dataset-initialized 1500 is not accepted as authoritative V1 ELO.',
        provenance_requirements: 'Frozen algorithm version and complete ordered result source IDs.',
        semantics_status: SEMANTICS_STATUS.SEMANTICS_UNPROVEN,
    },
    {
        feature_name: 'adjusted_elo_gap',
        family: FEATURE_FAMILIES.advanced,
        intended_semantics: 'Versioned transformation of proven raw_elo_gap.',
        source_authority: 'Depends on raw_elo_gap and a frozen transformation contract.',
        source_fields: ['raw_elo_gap', 'adjustment formula/version'],
        history_scope: 'Inherits raw ELO prior-state scope.',
        lookback_rule: 'Inherits raw ELO strict cutoff.',
        derivation: 'No value while raw_elo_gap is unproven; current *0.1 compatibility rule is not promoted.',
        cutoff_rule: FEATURE_CUTOFF_RELATION,
        missing_history_policy: 'Null with DEPENDENCY_UNAVAILABLE/SEMANTICS_UNPROVEN.',
        cold_start_policy: 'Unavailable.',
        provenance_requirements: 'Raw ELO lineage plus frozen adjustment formula/version.',
        semantics_status: SEMANTICS_STATUS.SEMANTICS_UNPROVEN,
    },
    {
        feature_name: 'home_fatigue_index',
        family: FEATURE_FAMILIES.advanced,
        intended_semantics:
            'Target home team scheduled-match count in the prior seven-day interval divided by seven, capped at one.',
        source_authority: 'Canonical complete schedule/inventory identity authority.',
        source_fields: ['canonical schedule prior fixture kickoff_at and team identity'],
        history_scope: 'Premier League, same season, target home team.',
        lookback_rule: 'Kickoff in [target cutoff - 7 days, target cutoff).',
        derivation: 'min(1, count(prior scheduled matches) / 7).',
        cutoff_rule: FEATURE_CUTOFF_RELATION,
        missing_history_policy: 'Null if schedule closure is not proven; never use 0.5 default.',
        cold_start_policy: 'Zero is proven when the closed interval contains no prior scheduled fixture.',
        provenance_requirements: 'Complete schedule closure, exact window source IDs and schedule hash.',
        semantics_status: SEMANTICS_STATUS.PROVEN_DERIVED,
    },
    {
        feature_name: 'away_fatigue_index',
        family: FEATURE_FAMILIES.advanced,
        intended_semantics:
            'Target away team scheduled-match count in the prior seven-day interval divided by seven, capped at one.',
        source_authority: 'Canonical complete schedule/inventory identity authority.',
        source_fields: ['canonical schedule prior fixture kickoff_at and team identity'],
        history_scope: 'Premier League, same season, target away team.',
        lookback_rule: 'Kickoff in [target cutoff - 7 days, target cutoff).',
        derivation: 'min(1, count(prior scheduled matches) / 7).',
        cutoff_rule: FEATURE_CUTOFF_RELATION,
        missing_history_policy: 'Null if schedule closure is not proven; never use 0.5 default.',
        cold_start_policy: 'Zero is proven when the closed interval contains no prior scheduled fixture.',
        provenance_requirements: 'Complete schedule closure, exact window source IDs and schedule hash.',
        semantics_status: SEMANTICS_STATUS.PROVEN_DERIVED,
    },
    {
        feature_name: 'fatigue_diff',
        family: FEATURE_FAMILIES.advanced,
        intended_semantics: 'Home prior-seven-day fatigue index minus away prior-seven-day fatigue index.',
        source_authority: 'Depends on both canonical schedule-derived fatigue values.',
        source_fields: ['home_fatigue_index', 'away_fatigue_index'],
        history_scope: 'Same target-season prior schedule windows.',
        lookback_rule: 'Inherits both strict seven-day windows.',
        derivation: 'home_fatigue_index - away_fatigue_index only when both are proven.',
        cutoff_rule: FEATURE_CUTOFF_RELATION,
        missing_history_policy: 'Null with DEPENDENCY_UNAVAILABLE.',
        cold_start_policy: 'Zero is allowed only when both empty windows are proven.',
        provenance_requirements: 'Both upstream fatigue lineages and exact schedule IDs.',
        semantics_status: SEMANTICS_STATUS.PROVEN_DERIVED,
    },
];

const FEATURE_SEMANTICS_BY_NAME = new Map(FEATURE_SEMANTICS.map(item => [item.feature_name, item]));

class GdA03ContractError extends GdA01ContractError {
    constructor(message, code = 'GD_A03_CONTRACT_INVALID') {
        super(message, code);
        this.name = 'GdA03ContractError';
    }
}

function fail(message, code = 'GD_A03_CONTRACT_INVALID') {
    throw new GdA03ContractError(message, code);
}

function assertObject(value, label) {
    if (!value || typeof value !== 'object' || Array.isArray(value)) fail(`${label} must be an object`);
    return value;
}

function assertText(value, label) {
    if (typeof value !== 'string' || value.trim() === '') fail(`${label} must be non-empty text`);
    return value;
}

function assertSha(value, label) {
    if (typeof value !== 'string' || !/^[0-9a-f]{64}$/.test(value)) {
        fail(`${label} must be a lowercase SHA-256`, 'HASH_MISMATCH');
    }
    return value;
}

function assertFiniteNumber(value, label) {
    if (typeof value !== 'number' || !Number.isFinite(value)) fail(`${label} must be finite`, 'FACT_VALUE_INVALID');
    return value;
}

function deepFreeze(value) {
    if (!value || typeof value !== 'object' || Object.isFrozen(value)) return value;
    Object.freeze(value);
    for (const child of Object.values(value)) deepFreeze(child);
    return value;
}

function validateFeatureContract(contract) {
    assertObject(contract, 'feature contract');
    if (contract.contract_id !== FEATURE_CONTRACT_ID) fail('feature contract ID is not canonical', 'SCHEMA_MISMATCH');
    if (contract.feature_contract_version !== FEATURE_CONTRACT_VERSION) {
        fail('feature contract version is unsupported', 'SCHEMA_MISMATCH');
    }
    if (contract.feature_count !== FEATURE_COUNT) fail('feature contract count is not 20', 'SCHEMA_MISMATCH');
    if (!Array.isArray(contract.ordered_features) || contract.ordered_features.length !== FEATURE_COUNT) {
        fail('feature contract ordered_features must contain exactly 20 names', 'SCHEMA_MISMATCH');
    }
    const names = new Set(contract.ordered_features);
    if (names.size !== FEATURE_COUNT || [...names].some(name => !FEATURE_SEMANTICS_BY_NAME.has(name))) {
        fail('feature contract contains unsupported or duplicate feature names', 'SCHEMA_MISMATCH');
    }
    return {
        contract_id: contract.contract_id,
        artifact_name: contract.artifact_name,
        model_type: contract.model_type,
        feature_contract_version: contract.feature_contract_version,
        feature_count: contract.feature_count,
        ordered_features: [...contract.ordered_features],
    };
}

function featureSemanticsInOrder(orderedFeatures) {
    return orderedFeatures.map(featureName => {
        const definition = FEATURE_SEMANTICS_BY_NAME.get(featureName);
        if (!definition) fail(`no GD-A03 semantic definition for ${featureName}`, 'SCHEMA_MISMATCH');
        return { ...definition };
    });
}

function isSemanticsProven(status) {
    return status === SEMANTICS_STATUS.PROVEN || status === SEMANTICS_STATUS.PROVEN_DERIVED;
}

function computeBusinessHash(artifact) {
    const { business_content_sha256: ignored, ...projection } = artifact;
    return sha256Text(stableStringify(projection));
}

function computeReceiptHash(receipt) {
    const { receipt_content_sha256: ignored, ...projection } = receipt;
    return sha256Text(stableStringify(projection));
}

function computeProvenanceDigest(projection) {
    return sha256Text(stableStringify(projection));
}

module.exports = {
    FATIGUE_LOOKBACK_DAYS,
    FEATURE_AVAILABILITY,
    FEATURE_CONTRACT_ID,
    FEATURE_CONTRACT_VERSION,
    FEATURE_COUNT,
    FEATURE_CUTOFF_POLICY,
    FEATURE_CUTOFF_RELATION,
    FEATURE_FAMILIES,
    FEATURE_SEMANTICS,
    FEATURE_SEMANTICS_BY_NAME,
    GdA03ContractError,
    PRIOR_STATE_ARTIFACT_SCHEMA_VERSION,
    PRIOR_STATE_LINEAGE_CONTRACT_VERSION,
    PRIOR_STATE_RECEIPT_SCHEMA_VERSION,
    PRIOR_STATE_STAGE,
    REASON_CODES,
    REQUIRED_ROLLING_HISTORY_COUNT,
    SCHEDULE_AWAY_FIXTURES_PER_TEAM,
    SCHEDULE_FIXTURES_PER_TEAM,
    SCHEDULE_HOME_FIXTURES_PER_TEAM,
    SCHEDULE_TEAM_CLOSURE_SCHEMA_VERSION,
    GD_A03_SOURCE_BINDING_NAMES,
    SCHEDULE_TEAMS_PER_SEASON,
    SEMANTICS_STATUS,
    assertFiniteNumber,
    assertObject,
    assertSha,
    assertText,
    computeBusinessHash,
    computeReceiptHash,
    computeProvenanceDigest,
    featureSemanticsInOrder,
    isSemanticsProven,
    stableStringify,
    validateFeatureContract,
};
