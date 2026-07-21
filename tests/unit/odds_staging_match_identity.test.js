'use strict';

// lifecycle: permanent；Football-Data 确定性比赛身份测试：alias、时间解释、manifest 验证

const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const assert = require('node:assert/strict');
const { randomUUID } = require('node:crypto');

const PROJECT_ROOT = path.resolve(__dirname, '../..');
const {
    FOOTBALL_DATA_TEAM_ALIASES,
    resolveFootballDataTeamName,
    resolveCompetition,
    parseAndValidateDate,
    deriveSeason,
    isAllowedSeason,
    deriveKickoffAt,
    validateKickoffTimeInterpretation,
    isInterpretationApplicable,
    buildKickoffInterpretationEvidence,
    ALLOWED_SEASONS,
    ALLOWED_COMPETITIONS,
} = require('../../src/infrastructure/odds_staging/footballDataIdentity');
const { adaptFootballDataCsv } = require('../../src/infrastructure/odds_staging/adapters');

// ── Alias Tests ───────────────────────────────────────────────────

test('12 条别名字面量精确且不可变', () => {
    assert.equal(Object.keys(FOOTBALL_DATA_TEAM_ALIASES).length, 12);
    assert.ok(Object.isFrozen(FOOTBALL_DATA_TEAM_ALIASES));
});

test('resolveFootballDataTeamName 逐条精确映射', () => {
    const cases = [
        ['Luton', 'Luton Town'],
        ['Bournemouth', 'AFC Bournemouth'],
        ['Brighton', 'Brighton & Hove Albion'],
        ['Leeds', 'Leeds United'],
        ['Leicester', 'Leicester City'],
        ['Man City', 'Manchester City'],
        ['Man United', 'Manchester United'],
        ['Newcastle', 'Newcastle United'],
        ["Nott'm Forest", 'Nottingham Forest'],
        ['Tottenham', 'Tottenham Hotspur'],
        ['West Ham', 'West Ham United'],
        ['Wolves', 'Wolverhampton Wanderers'],
    ];
    for (const [src, expected] of cases) {
        assert.equal(resolveFootballDataTeamName(src), expected, `${src} → ${expected}`);
    }
});

test('大小写和 NFKC 空白规范化', () => {
    assert.equal(resolveFootballDataTeamName('  MAN city  '), 'Manchester City');
    assert.equal(resolveFootballDataTeamName('Man City'), 'Manchester City'); // NBSP → space
    assert.equal(resolveFootballDataTeamName('WEST HAM'), 'West Ham United');
});

test('未知球队不转换', () => {
    assert.equal(resolveFootballDataTeamName('Liverpool'), 'Liverpool');
    assert.equal(resolveFootballDataTeamName('Chelsea'), 'Chelsea');
    assert.equal(resolveFootballDataTeamName('Arsenal'), 'Arsenal');
    assert.equal(resolveFootballDataTeamName('Unknown FC'), 'Unknown FC');
});

test('不做模糊或语音匹配', () => {
    assert.equal(resolveFootballDataTeamName('Man U'), 'Man U'); // not in alias table
    assert.equal(resolveFootballDataTeamName('Mancity'), 'Mancity');
    assert.equal(resolveFootballDataTeamName('Tottneham'), 'Tottneham'); // typo
});

// ── Competition/Season Tests ─────────────────────────────────────

test('E0 → Premier League 映射', () => {
    assert.equal(resolveCompetition('E0'), 'Premier League');
    assert.equal(resolveCompetition('E0 '), 'Premier League');
});

test('Premier League 保持 canonical', () => {
    assert.equal(resolveCompetition('Premier League'), 'Premier League');
});

test('其他 division 不映射', () => {
    assert.equal(resolveCompetition('E1'), 'E1');
    assert.equal(resolveCompetition('SP1'), 'SP1');
});

test('parseAndValidateDate DD/MM/YYYY', () => {
    assert.deepEqual(parseAndValidateDate('05/08/2022'), { year: 2022, month: 8, day: 5 });
    assert.deepEqual(parseAndValidateDate('31/12/2023'), { year: 2023, month: 12, day: 31 });
});

test('parseAndValidateDate YYYY-MM-DD', () => {
    assert.deepEqual(parseAndValidateDate('2022-08-05'), { year: 2022, month: 8, day: 5 });
});

test('parseAndValidateDate 拒绝非法日期', () => {
    assert.equal(parseAndValidateDate('29/02/2023'), null); // not a leap year
    assert.equal(parseAndValidateDate('31/04/2023'), null); // April has 30 days
    assert.equal(parseAndValidateDate(''), null);
    assert.equal(parseAndValidateDate('not-a-date'), null);
});

test('deriveSeason 正确推导赛季', () => {
    assert.equal(deriveSeason(2022, 8), '2022/2023'); // Aug → new season
    assert.equal(deriveSeason(2023, 1), '2022/2023'); // Jan → previous season
    assert.equal(deriveSeason(2023, 5), '2022/2023'); // May → previous season
    assert.equal(deriveSeason(2023, 7), '2023/2024'); // July → new season
    assert.equal(deriveSeason(2024, 3), '2023/2024');
    assert.equal(deriveSeason(2024, 8), '2024/2025');
});

test('isAllowedSeason 只接受授权赛季', () => {
    assert.ok(isAllowedSeason('2022/2023'));
    assert.ok(isAllowedSeason('2023/2024'));
    assert.ok(isAllowedSeason('2024/2025'));
    assert.ok(!isAllowedSeason('2021/2022'));
    assert.ok(!isAllowedSeason('2025/2026'));
});

// ── Timezone Tests ────────────────────────────────────────────────

test('deriveKickoffAt GMT 日期正确转换', () => {
    const interp = validInterpretation();
    // Jan 2023 is GMT (UTC+0). Source 20:00 London = 20:00 UTC
    const result = deriveKickoffAt('23/01/2023', '20:00', interp);
    assert.equal(result.error, null);
    assert.equal(result.kickoff_at, '2023-01-23T20:00:00Z');
});

test('deriveKickoffAt BST 日期正确转换', () => {
    const interp = validInterpretation();
    // Aug 2022 is BST (UTC+1). Source 20:00 London = 19:00 UTC
    const result = deriveKickoffAt('05/08/2022', '20:00', interp);
    assert.equal(result.error, null);
    assert.equal(result.kickoff_at, '2022-08-05T19:00:00Z');
});

test('deriveKickoffAt 对 London DST 不存在和歧义本地时间 fail closed', () => {
    const interp = validInterpretation();
    assert.equal(deriveKickoffAt('26/03/2023', '00:30', interp).kickoff_at, '2023-03-26T00:30:00Z');
    assert.equal(deriveKickoffAt('26/03/2023', '01:30', interp).error, 'kickoff_local_time_nonexistent');
    assert.equal(deriveKickoffAt('26/03/2023', '02:30', interp).kickoff_at, '2023-03-26T01:30:00Z');
    assert.equal(deriveKickoffAt('29/10/2023', '00:30', interp).kickoff_at, '2023-10-28T23:30:00Z');
    assert.equal(deriveKickoffAt('29/10/2023', '01:30', interp).error, 'kickoff_local_time_ambiguous');
    assert.equal(deriveKickoffAt('29/10/2023', '02:30', interp).kickoff_at, '2023-10-29T02:30:00Z');
    assert.equal(deriveKickoffAt('31/03/2024', '01:30', interp).error, 'kickoff_local_time_nonexistent');
});

test('deriveKickoffAt 拒绝无效时间', () => {
    const interp = validInterpretation();
    assert.equal(deriveKickoffAt('05/08/2022', '', interp).error, 'kickoff_missing');
    assert.equal(deriveKickoffAt('', '20:00', interp).error, 'kickoff_invalid');
    assert.equal(deriveKickoffAt('05/08/2022', '25:00', interp).error, 'kickoff_invalid');
    assert.equal(deriveKickoffAt('05/08/2022', '12:60', interp).error, 'kickoff_invalid');
});

test('deriveKickoffAt 无 interpretation 返回 unresolved', () => {
    const result = deriveKickoffAt('05/08/2022', '20:00', null);
    assert.equal(result.kickoff_at, null);
    assert.equal(result.error, 'kickoff_timezone_unresolved');
});

test('deriveKickoffAt 非法 interpretation 返回 invalid', () => {
    assert.equal(
        deriveKickoffAt('05/08/2022', '20:00', { status: 'derived', timezone: 'Asia/Tokyo' }).error,
        'kickoff_interpretation_invalid'
    );
    assert.equal(
        deriveKickoffAt('05/08/2022', '20:00', { status: 'official', timezone: 'Europe/London' }).error,
        'kickoff_interpretation_invalid'
    );
});

// ── Manifest Interpretation Validation ───────────────────────────

function validInterpretation(overrides = {}) {
    return {
        status: 'derived',
        timezone: 'Europe/London',
        method: 'source_local_calendar_time',
        evidence_level: 'empirical_cross_source',
        official_source_declaration: false,
        evidence_reference: 'm3-d3a-result-freeze/test-ref',
        allowed_competitions: ['Premier League'],
        allowed_seasons: ['2022/2023', '2023/2024', '2024/2025'],
        ...overrides,
    };
}

test('合法 interpretation 对象通过验证', () => {
    const result = validateKickoffTimeInterpretation(validInterpretation());
    assert.equal(result.valid, true);
    assert.deepEqual(result.errors, []);
});

test('interpretation 可选 — 缺失时不报错', () => {
    const result = validateKickoffTimeInterpretation(null);
    assert.equal(result.valid, true);
});

test('status 不是 derived 拒绝', () => {
    const result = validateKickoffTimeInterpretation(validInterpretation({ status: 'official' }));
    assert.ok(result.errors.some(e => /status must be "derived"/.test(e)));
});

test('timezone 不是 Europe/London 拒绝', () => {
    const result = validateKickoffTimeInterpretation(validInterpretation({ timezone: 'UTC' }));
    assert.ok(result.errors.some(e => /timezone must be "Europe\/London"/.test(e)));
});

test('method 错误拒绝', () => {
    const result = validateKickoffTimeInterpretation(validInterpretation({ method: 'manual' }));
    assert.ok(result.errors.some(e => /method/.test(e)));
});

test('evidence_level 错误拒绝', () => {
    const result = validateKickoffTimeInterpretation(validInterpretation({ evidence_level: 'official' }));
    assert.ok(result.errors.some(e => /evidence_level/.test(e)));
});

test('official_source_declaration=true 拒绝', () => {
    const result = validateKickoffTimeInterpretation(validInterpretation({ official_source_declaration: true }));
    assert.ok(result.errors.some(e => /official_source_declaration/.test(e)));
});

test('evidence_reference 缺失拒绝', () => {
    const result = validateKickoffTimeInterpretation(validInterpretation({ evidence_reference: '' }));
    assert.ok(result.errors.some(e => /evidence_reference/.test(e)));
});

test('competition 扩大拒绝', () => {
    const result = validateKickoffTimeInterpretation(
        validInterpretation({ allowed_competitions: ['Premier League', 'Championship'] })
    );
    assert.ok(result.errors.some(e => /unauthorized competition/.test(e)));
});

test('season 扩大拒绝', () => {
    const result = validateKickoffTimeInterpretation(
        validInterpretation({ allowed_seasons: ['2022/2023', '2025/2026'] })
    );
    assert.ok(result.errors.some(e => /unauthorized season/.test(e)));
});

test('未知字段拒绝', () => {
    const result = validateKickoffTimeInterpretation(validInterpretation({ extra_field: true }));
    assert.ok(result.errors.some(e => /unknown field/.test(e)));
});

test('interpretation 数组、重复 scope 和空 scope 均被拒绝', () => {
    assert.equal(validateKickoffTimeInterpretation([]).valid, false);
    assert.equal(
        validateKickoffTimeInterpretation(
            validInterpretation({ allowed_competitions: ['Premier League', 'Premier League'] })
        ).valid,
        false
    );
    assert.equal(validateKickoffTimeInterpretation(validInterpretation({ allowed_seasons: [] })).valid, false);
});

test('isInterpretationApplicable 仅对正确上下文返回 true', () => {
    assert.ok(
        isInterpretationApplicable({
            kickoff_time_interpretation: { status: 'derived' },
            acquisition_mode: 'historical_git_recovery',
            adapter: 'football-data-csv',
            adapter_version: '1.2.0',
            source_timezone: 'unknown',
        })
    );

    // 缺少 interpretation
    assert.ok(
        !isInterpretationApplicable({
            acquisition_mode: 'historical_git_recovery',
            adapter: 'football-data-csv',
            adapter_version: '1.2.0',
            source_timezone: 'unknown',
        })
    );
    // 错误的 source_timezone
    assert.ok(
        !isInterpretationApplicable({
            kickoff_time_interpretation: {},
            acquisition_mode: 'historical_git_recovery',
            adapter: 'football-data-csv',
            adapter_version: '1.2.0',
            source_timezone: 'UTC',
        })
    );
    // 非历史恢复
    assert.ok(
        !isInterpretationApplicable({
            kickoff_time_interpretation: {},
            acquisition_mode: 'live',
            adapter: 'football-data-csv',
            adapter_version: '1.2.0',
            source_timezone: 'unknown',
        })
    );
    // 错误 adapter
    assert.ok(
        !isInterpretationApplicable({
            kickoff_time_interpretation: {},
            acquisition_mode: 'historical_git_recovery',
            adapter: 'oddsportal-explicit-envelope-html',
            adapter_version: '1.2.0',
            source_timezone: 'unknown',
        })
    );
});

test('buildKickoffInterpretationEvidence 生成正确证据', () => {
    const interp = validInterpretation();
    const evidence = buildKickoffInterpretationEvidence(interp, '05/08/2022', '20:00');
    assert.equal(evidence.status, 'derived');
    assert.equal(evidence.timezone, 'Europe/London');
    assert.equal(evidence.official_source_declaration, false);
    assert.equal(evidence.source_local_date, '05/08/2022');
    assert.equal(evidence.source_local_time, '20:00');
});

test('manifest 实际 scope 在 alias 前逐行生效', () => {
    const manifest = {
        acquisition_mode: 'historical_git_recovery',
        adapter: 'football-data-csv',
        adapter_version: '1.2.0',
        source_timezone: 'unknown',
        kickoff_time_interpretation: validInterpretation({ allowed_seasons: ['2022/2023'] }),
    };
    const unauthorizedSeason = adaptFootballDataCsv(
        'Div,Date,Time,HomeTeam,AwayTeam,B365H,B365D,B365A\nE0,05/08/2023,15:00,Man City,Wolves,2,3,4',
        { manifest }
    );
    assert.equal(unauthorizedSeason.observations[0].identity_reason, 'season_not_authorized');
    assert.equal(unauthorizedSeason.observations[0].home_team, null);
    const unauthorizedCompetition = adaptFootballDataCsv(
        'Div,Date,Time,HomeTeam,AwayTeam,B365H,B365D,B365A\nE1,05/08/2022,15:00,Man City,Wolves,2,3,4',
        { manifest }
    );
    assert.equal(unauthorizedCompetition.observations[0].identity_reason, 'competition_not_authorized');
    assert.equal(unauthorizedCompetition.observations[0].home_team, null);
});
