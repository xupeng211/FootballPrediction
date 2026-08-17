'use strict';

// lifecycle: permanent
// Premier League v1 standings 的合同绑定层。它只验证现有
// config/model_feature_contracts.json 的已解析对象，不创建第二份合同。

const { sha256Text, stableStringify } = require('../canonical/StableValue');

const STANDINGS_CONTRACT_ID = 'standings/premier-league-point-in-time/v1';
const STANDINGS_CONTRACT_VERSION = 'v1';
const STANDINGS_COMPETITION = 'Premier League';
const STANDINGS_LEAGUE_ID = 47;
const STANDINGS_SEASONS = Object.freeze(['2022/2023', '2023/2024', '2024/2025']);
const STANDINGS_TEAM_COUNT = 20;

const STANDINGS_REASON_CODES = Object.freeze([
    'MISSING_PRIOR_RESULT_EVIDENCE',
    'RESULT_IDENTITY_CONFLICT',
    'RESULT_SCORE_CONFLICT',
    'EVENT_TIME_CONFLICT',
    'FIXTURE_STATUS_CONFLICT',
    'ADMIN_ADJUSTMENT_CONFLICT',
    'ADMIN_ADJUSTMENT_EFFECTIVE_TIME_AMBIGUOUS',
    'POSTPONED_EVENT_TIME_UNPROVEN',
    'EXCEPTION_STATUS_UNPROVEN',
    'RULE_VERSION_UNPROVEN',
    'SAME_KICKOFF_NOT_ELIGIBLE',
    'STANDINGS_POSITION_UNAVAILABLE',
    'DEPENDENCY_UNAVAILABLE',
]);

const STANDINGS_CONTRACT_FIELDS = new Set([
    'contract_id',
    'version',
    'feature_bindings',
    'competition_scope',
    'season_rule_bindings',
    'points_rule',
    'ordering_rules',
    'tie_representation',
    'table_position_diff_rule',
    'strict_cutoff_rule',
    'same_kickoff_rule',
    'postponed_rule',
    'exception_rule',
    'administrative_adjustment_rule',
    'season_boundary_rule',
    'result_state_requirements',
    'missing_history_policy',
    'source_authority',
    'lineage_requirements',
    'source_conflict_policy',
    'fail_closed_reason_codes',
    'evidence_provenance',
]);

const STANDINGS_BOUNDARY_FIELDS = new Set([
    'retained_in_v_next',
    'semantic_direction',
    'cutoff',
    'same_kickoff_fixtures',
    'training_eligible',
    'runtime_eligible',
    'rule_history_closure_required',
    'semantic_contract_status',
    'historical_evidence_status',
    'contract',
    'unresolved_evidence',
]);

const BINDING_BRAND = Symbol('standings-contract-binding');

class StandingsContractError extends Error {
    constructor(message, code = 'STANDINGS_CONTRACT_INVALID') {
        super(message);
        this.name = 'StandingsContractError';
        this.code = code;
    }
}

function isPlainObject(value) {
    return value !== null && typeof value === 'object' && !Array.isArray(value);
}

function fail(message, code = 'STANDINGS_CONTRACT_INVALID') {
    throw new StandingsContractError(message, code);
}

function requireObject(value, label) {
    if (!isPlainObject(value)) fail(`${label} must be an object`, 'SCHEMA_MISMATCH');
    return value;
}

function requireText(value, label, expected) {
    if (typeof value !== 'string' || value.trim() === '' || (expected !== undefined && value !== expected)) {
        fail(`${label} is malformed`, 'SCHEMA_MISMATCH');
    }
    return value;
}

function requireInteger(value, label, expected) {
    if (!Number.isSafeInteger(value) || (expected !== undefined && value !== expected)) {
        fail(`${label} is malformed`, 'SCHEMA_MISMATCH');
    }
    return value;
}

function requireExactKeys(value, expected, label) {
    const actual = new Set(Object.keys(value));
    if (actual.size !== expected.size || [...expected].some(key => !actual.has(key))) {
        fail(`${label} fields are malformed`, 'SCHEMA_MISMATCH');
    }
}

function requireTextArray(value, label, expected) {
    if (!Array.isArray(value) || value.some(item => typeof item !== 'string' || item.trim() === '')) {
        fail(`${label} is malformed`, 'SCHEMA_MISMATCH');
    }
    if (expected !== undefined && stableStringify(value) !== stableStringify(expected)) {
        fail(`${label} differs from the frozen contract`, 'SCHEMA_MISMATCH');
    }
    return value;
}

function requireExactObject(value, expected, label) {
    requireObject(value, label);
    requireExactKeys(value, new Set(Object.keys(expected)), label);
    for (const [key, expectedValue] of Object.entries(expected)) {
        if (stableStringify(value[key]) !== stableStringify(expectedValue)) {
            fail(`${label}.${key} differs from the frozen contract`, 'SCHEMA_MISMATCH');
        }
    }
    return value;
}

function freezeDeep(value) {
    if (value && typeof value === 'object' && !Object.isFrozen(value)) {
        for (const child of Object.values(value)) freezeDeep(child);
        Object.freeze(value);
    }
    return value;
}

function validateSeasonRuleBindings(bindings) {
    if (!Array.isArray(bindings) || bindings.length !== STANDINGS_SEASONS.length) {
        fail('standings season rule bindings are incomplete', 'RULE_VERSION_UNPROVEN');
    }
    for (const [index, season] of STANDINGS_SEASONS.entries()) {
        const binding = requireObject(bindings[index], `standings season rule binding[${index}]`);
        requireText(binding.season, `standings season rule binding[${index}].season`, season);
        requireText(binding.document_title, `standings season rule binding[${index}].document_title`);
        requireText(binding.source_url, `standings season rule binding[${index}].source_url`);
        requireText(
            binding.rule_identifier,
            `standings season rule binding[${index}].rule_identifier`,
            'C.1-C.7,C.17,C.18,C.25-C.30'
        );
    }
}

function validateConflictPolicy(value) {
    requireExactKeys(
        value,
        new Set(['action', 'reason_codes', 'majority_vote', 'provider_priority']),
        'source conflict policy'
    );
    requireText(value.action, 'source conflict policy.action', 'FAIL_CLOSED');
    requireTextArray(value.reason_codes, 'source conflict policy.reason_codes', [
        'RESULT_IDENTITY_CONFLICT',
        'RESULT_SCORE_CONFLICT',
        'EVENT_TIME_CONFLICT',
        'FIXTURE_STATUS_CONFLICT',
        'ADMIN_ADJUSTMENT_CONFLICT',
    ]);
    requireText(value.majority_vote, 'source conflict policy.majority_vote', 'FORBIDDEN');
    requireText(
        value.provider_priority,
        'source conflict policy.provider_priority',
        'FORBIDDEN_WITHOUT_EXPLICIT_AUTHORITY'
    );
}

function validateStandingsBoundary(registry) {
    requireObject(registry, 'feature contract registry');
    requireText(
        registry.schema_version,
        'feature contract registry.schema_version',
        'model-feature-contract-registry/v2'
    );
    requireText(registry.lifecycle, 'feature contract registry.lifecycle', 'permanent');
    requireObject(registry.decision_boundaries, 'feature contract decision boundaries');
    const standings = requireObject(registry.decision_boundaries.standings, 'standings decision boundary');
    requireExactKeys(standings, STANDINGS_BOUNDARY_FIELDS, 'standings decision boundary');
    for (const [field, expected] of Object.entries({
        retained_in_v_next: 'YES',
        semantic_direction: 'OFFICIAL_POINT_IN_TIME_STANDINGS',
        cutoff: 'source_kickoff < target_kickoff',
        same_kickoff_fixtures: 'EXCLUDED',
        training_eligible: 'NO',
        runtime_eligible: 'NO',
        rule_history_closure_required: 'NO',
        semantic_contract_status: 'FROZEN',
        historical_evidence_status: 'EVIDENCE_CLOSED_FOR_FROZEN_SCOPE',
    })) {
        requireText(standings[field], `standings decision boundary.${field}`, expected);
    }
    requireTextArray(standings.unresolved_evidence, 'standings unresolved evidence', []);

    const contract = requireObject(standings.contract, 'standings semantic contract');
    requireExactKeys(contract, STANDINGS_CONTRACT_FIELDS, 'standings semantic contract');
    requireText(contract.contract_id, 'standings contract id', STANDINGS_CONTRACT_ID);
    requireText(contract.version, 'standings contract version', STANDINGS_CONTRACT_VERSION);
    requireTextArray(contract.feature_bindings, 'standings feature bindings', [
        'home_table_position',
        'away_table_position',
        'table_position_diff',
    ]);

    const scope = requireExactObject(
        contract.competition_scope,
        {
            competition: STANDINGS_COMPETITION,
            league_id: STANDINGS_LEAGUE_ID,
            frozen_seasons: STANDINGS_SEASONS,
            target_population: 888,
        },
        'standings competition scope'
    );
    validateSeasonRuleBindings(contract.season_rule_bindings);
    requireExactObject(contract.points_rule, { win: 3, draw: 1, loss: 0 }, 'standings points rule');
    requireTextArray(contract.ordering_rules, 'standings ordering rules', [
        'points',
        'goal_difference',
        'goals_scored',
    ]);
    requireExactObject(
        contract.tie_representation,
        {
            mode: 'COMPETITION_RANKING_SHARED_POSITION_WITH_GAPS',
            definition: '1 + number of clubs strictly ahead under the applicable ordinary ranking criteria.',
            examples: ['1,1,3', '4,5,5,7'],
            forbidden_tie_breakers: [
                'alphabetical club name',
                'team ID',
                'provider order',
                'match ID',
                'database order',
                'filesystem order',
                'ingestion order',
            ],
        },
        'standings tie representation'
    );
    requireExactObject(
        contract.table_position_diff_rule,
        {
            orientation: 'HOME_POSITION_MINUS_AWAY_POSITION',
            formula: 'home_table_position - away_table_position',
            requires_both_positions: 'YES',
            unavailable_if_either_missing: 'YES',
        },
        'standings table position diff rule'
    );
    requireText(contract.strict_cutoff_rule, 'standings strict cutoff rule', 'SOURCE_EVENT_TIME_LT_TARGET_KICKOFF');
    requireText(contract.same_kickoff_rule, 'standings same kickoff rule', 'EXCLUDED');
    requireText(contract.postponed_rule, 'standings postponed rule', 'ACTUAL_PLAYED_EVENT_TIME_ONLY');
    requireExactObject(
        contract.exception_rule,
        {
            abandoned: 'NOT_TABLE_ELIGIBLE',
            awarded: 'OFFICIAL_TABLE_ELIGIBILITY_REQUIRED',
            replayed: 'OFFICIAL_DISPOSITION_WITHOUT_DOUBLE_COUNT',
            void: 'NOT_TABLE_ELIGIBLE',
            unknown_status: 'FAIL_CLOSED',
        },
        'standings exception rule'
    );
    requireExactObject(
        contract.administrative_adjustment_rule,
        {
            point_layer: 'MATCH_EARNED_POINTS_PLUS_EFFECTIVE_ADMINISTRATIVE_ADJUSTMENTS',
            retroactive_allowed: 'NO',
            exact_timestamp: 'USE_EXACT_TIMESTAMP',
            date_only: 'UNCERTAIN_DAY_INTERVAL',
            before_interval: 'NOT_EFFECTIVE',
            after_interval: 'EFFECTIVE',
            overlap: 'UNAVAILABLE',
            overlap_reason_code: 'ADMIN_ADJUSTMENT_EFFECTIVE_TIME_AMBIGUOUS',
        },
        'standings administrative adjustment rule'
    );
    requireText(
        contract.season_boundary_rule,
        'standings season boundary rule',
        'EXACT_COMPETITION_SEASON_CLUB_UNIVERSE_ONLY'
    );
    requireTextArray(contract.result_state_requirements, 'standings result state requirements', [
        'canonical_match_identity',
        'canonical_team_identity',
        'proven_eligible_result_status',
        'actual_eligible_event_time',
        'final_score',
        'source_lineage',
    ]);
    requireExactObject(
        contract.missing_history_policy,
        {
            action: 'UNAVAILABLE',
            reason_code: 'MISSING_PRIOR_RESULT_EVIDENCE',
            fallbacks_forbidden: [
                'skip match',
                'forward fill',
                'final table',
                'later standings',
                'provider current table',
                'fabricated score',
            ],
        },
        'standings missing history policy'
    );
    requireTextArray(contract.source_authority, 'standings source authority');
    requireTextArray(contract.lineage_requirements, 'standings lineage requirements');
    validateConflictPolicy(contract.source_conflict_policy);
    requireTextArray(contract.fail_closed_reason_codes, 'standings fail-closed reason codes', STANDINGS_REASON_CODES);

    const provenance = requireObject(contract.evidence_provenance, 'standings evidence provenance');
    requireText(
        provenance.task_id,
        'standings evidence provenance.task_id',
        'STANDINGS-HISTORY-EVIDENCE-REMEDIATION-V1'
    );
    requireText(
        provenance.memo_sha256,
        'standings evidence provenance.memo_sha256',
        'e09a80735f26d3fe3f949fcc115c853354c3f449dcf1ca6e9da7954846dbb357'
    );
    requireInteger(provenance.target_population, 'standings evidence provenance.target_population', 888);
    requireText(
        provenance.target_row_evidence_coverage,
        'standings evidence provenance.target_row_evidence_coverage',
        '887/888'
    );
    requireInteger(
        provenance.expected_fail_closed_target_rows,
        'standings evidence provenance.expected_fail_closed_target_rows',
        1
    );
    const expectedUnavailableTargets = requireTextArray(
        provenance.expected_unavailable_targets,
        'standings evidence provenance.expected_unavailable_targets'
    );
    if (expectedUnavailableTargets.length !== 1) {
        fail('standings evidence provenance expected unavailable target scope is malformed', 'SCHEMA_MISMATCH');
    }
    requireText(
        provenance.evidence_status,
        'standings evidence provenance.evidence_status',
        'SEMANTIC_CONTRACT_EVIDENCE_READY'
    );

    return { standings, contract, scope };
}

function bindFrozenStandingsContract(registry) {
    const { standings, contract, scope } = validateStandingsBoundary(registry);
    const binding = {
        binding_type: 'FROZEN_PREMIER_LEAGUE_STANDINGS_CONTRACT',
        contract_id: contract.contract_id,
        version: contract.version,
        registry_schema_version: registry.schema_version,
        registry_sha256: sha256Text(stableStringify(registry)),
        semantic_contract_status: standings.semantic_contract_status,
        historical_evidence_status: standings.historical_evidence_status,
        competition: scope.competition,
        league_id: scope.league_id,
        frozen_seasons: [...scope.frozen_seasons],
        target_population: scope.target_population,
        team_count: STANDINGS_TEAM_COUNT,
        points_rule: { ...contract.points_rule },
        ordering_rules: [...contract.ordering_rules],
        tie_mode: contract.tie_representation.mode,
        diff_orientation: contract.table_position_diff_rule.orientation,
        strict_cutoff_rule: contract.strict_cutoff_rule,
        same_kickoff_rule: contract.same_kickoff_rule,
        postponed_rule: contract.postponed_rule,
        exception_rule: { ...contract.exception_rule },
        administrative_adjustment_rule: { ...contract.administrative_adjustment_rule },
        reason_codes: [...contract.fail_closed_reason_codes],
    };
    Object.defineProperty(binding, BINDING_BRAND, { value: true, enumerable: false });
    return freezeDeep(binding);
}

function assertStandingsContractBinding(binding) {
    if (!isPlainObject(binding) || binding[BINDING_BRAND] !== true) {
        fail('standings engine requires a binding produced by bindFrozenStandingsContract', 'CONTRACT_BINDING_INVALID');
    }
    if (
        binding.binding_type !== 'FROZEN_PREMIER_LEAGUE_STANDINGS_CONTRACT' ||
        binding.contract_id !== STANDINGS_CONTRACT_ID ||
        binding.version !== STANDINGS_CONTRACT_VERSION ||
        binding.competition !== STANDINGS_COMPETITION ||
        binding.league_id !== STANDINGS_LEAGUE_ID ||
        stableStringify(binding.frozen_seasons) !== stableStringify(STANDINGS_SEASONS) ||
        binding.team_count !== STANDINGS_TEAM_COUNT ||
        binding.strict_cutoff_rule !== 'SOURCE_EVENT_TIME_LT_TARGET_KICKOFF' ||
        binding.same_kickoff_rule !== 'EXCLUDED' ||
        binding.tie_mode !== 'COMPETITION_RANKING_SHARED_POSITION_WITH_GAPS' ||
        binding.diff_orientation !== 'HOME_POSITION_MINUS_AWAY_POSITION'
    ) {
        fail('standings contract binding is incompatible with the frozen v1 contract', 'CONTRACT_BINDING_INVALID');
    }
    return binding;
}

module.exports = {
    STANDINGS_COMPETITION,
    STANDINGS_CONTRACT_ID,
    STANDINGS_CONTRACT_VERSION,
    STANDINGS_LEAGUE_ID,
    STANDINGS_REASON_CODES,
    STANDINGS_SEASONS,
    STANDINGS_TEAM_COUNT,
    StandingsContractError,
    assertStandingsContractBinding,
    bindFrozenStandingsContract,
};
