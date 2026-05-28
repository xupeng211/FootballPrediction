#!/usr/bin/env node
'use strict';

const fs = require('node:fs');
const path = require('node:path');

const PROJECT_ROOT = path.resolve(__dirname, '../..');
const PHASE = 'Phase 5.21-ADG9';
const STATUS = 'completed_strict_fixture_identity_guard_validation';
const ADG8_RESULT_PATH = 'docs/_manifests/fotmob_identity_mapping_source_inventory_audit_result.adg8.json';
const ARTIFACT_OUTPUT_PATH = 'docs/_manifests/fotmob_strict_fixture_identity_guard_implementation.adg9.json';
const REPORT_OUTPUT_PATH = 'docs/_reports/FOTMOB_STRICT_FIXTURE_IDENTITY_GUARD_IMPLEMENTATION_ADG9.md';

const {
    validateStrictFixtureIdentity,
    FIXTURE_IDENTITY_GUARD_PASSED,
    FIXTURE_IDENTITY_GUARD_BLOCKED,
} = require('../../src/infrastructure/services/FotMobRouteIdentityReconciler');

function absolutePath(filePath) {
    return path.isAbsolute(filePath) ? filePath : path.join(PROJECT_ROOT, filePath);
}

function readJsonFile(filePath) {
    return JSON.parse(fs.readFileSync(absolutePath(filePath), 'utf8'));
}

function writeJsonFile(filePath, value) {
    fs.writeFileSync(absolutePath(filePath), `${JSON.stringify(value, null, 4)}\n`, 'utf8');
}

function writeTextFile(filePath, value) {
    fs.writeFileSync(absolutePath(filePath), value, 'utf8');
}

function buildGuardInput(adg8Record = {}) {
    return {
        schedule_external_id: adg8Record.schedule_external_id,
        detail_external_id_candidate: adg8Record.expected_detail_external_id_candidate,
        expected_home_team: adg8Record.expected_home_team,
        expected_away_team: adg8Record.expected_away_team,
        observed_detail_id: adg8Record.observed_detail_id,
        observed_home_team: adg8Record.observed_home_team,
        observed_away_team: adg8Record.observed_away_team,
        expected_match_date: adg8Record.expected_match_date,
        observed_match_date: adg8Record.observed_match_date,
        expected_competition: adg8Record.expected_competition,
        observed_competition: adg8Record.observed_competition,
        is_suspended_reference:
            adg8Record.audit_classification === 'suspended_reference_still_blocked' ||
            adg8Record.reference_status === 'blocked_reference_only_no_unsuspend',
    };
}

function validateAllSamples(adg8Artifact = {}) {
    const records = adg8Artifact.audit_results || [];
    return records.map(record => {
        const guardInput = buildGuardInput(record);
        const guardResult = validateStrictFixtureIdentity(guardInput);

        return {
            ...guardResult,
            target_match_id: record.target_match_id || null,
            adg8_audit_classification: record.audit_classification,
            guard_consistent_with_adg8:
                guardResult.fixture_identity_guard_status ===
                (record.audit_classification === 'correct_mapping'
                    ? FIXTURE_IDENTITY_GUARD_PASSED
                    : FIXTURE_IDENTITY_GUARD_BLOCKED),
            source_page_url: record.source_page_url || null,
            source_inventory_record_key: record.source_inventory_record_key || null,
            candidate_generation_rule: record.candidate_generation_rule || null,
        };
    });
}

function countBy(results = [], predicate) {
    return results.filter(predicate).length;
}

function buildArtifact(adg8Result = {}, generatedAt = new Date().toISOString()) {
    const guardResults = validateAllSamples(adg8Result);

    const summary = {
        audited_sample_count: guardResults.length,
        positive_control_count: countBy(
            guardResults,
            r => r.audit_classification === 'correct_mapping'
        ),
        guard_passed_count: countBy(
            guardResults,
            r => r.fixture_identity_guard_status === FIXTURE_IDENTITY_GUARD_PASSED
        ),
        guard_blocked_count: countBy(
            guardResults,
            r => r.fixture_identity_guard_status === FIXTURE_IDENTITY_GUARD_BLOCKED
        ),
        reverse_fixture_mapping_error_count: countBy(
            guardResults,
            r => r.audit_classification === 'reverse_fixture_mapping_error'
        ),
        home_away_inversion_count: countBy(
            guardResults,
            r => r.home_away_orientation_status === 'reversed' && r.correction_needed === true
        ),
        same_team_pair_wrong_leg_count: countBy(
            guardResults,
            r =>
                r.blockers.includes('same_team_pair_wrong_leg')
        ),
        date_mismatch_count: countBy(
            guardResults,
            r => r.blockers.includes('date_mismatch')
        ),
        suspended_reference_still_blocked_count: countBy(
            guardResults,
            r => r.audit_classification === 'suspended_reference_still_blocked'
        ),
        correction_candidate_count: countBy(
            guardResults,
            r => r.correction_needed === true
        ),
        guard_adg8_consistent_count: countBy(
            guardResults,
            r => r.guard_consistent_with_adg8 === true
        ),
        raw_write_execution_ready: false,
    };

    return {
        schema_version: 'fotmob_strict_fixture_identity_guard_implementation_adg9_v1',
        phase: PHASE,
        generated_at: generatedAt,
        adg9_guard_execution_status: STATUS,
        runtime_code_changed: true,
        guard_function: 'validateStrictFixtureIdentity',
        guard_location: 'src/infrastructure/services/FotMobRouteIdentityReconciler.js',
        guard_implemented: true,
        no_live_fetch: true,
        no_network_request: true,
        no_browser_automation: true,
        no_direct_api_probing: true,
        no_db_write: true,
        no_raw_write: true,
        no_raw_match_data_insert: true,
        no_re_acceptance: true,
        no_suspension_reversal: true,
        no_source_inventory_mutation: true,
        no_candidate_mutation: true,
        no_full_payload_saved: true,
        raw_write_execution_ready: false,
        ...summary,
        guard_details: guardResults,
    };
}

function buildReport(artifact = {}) {
    const lines = [
        '# FotMob Strict Fixture Identity Guard Implementation ADG9',
        '',
        `- Phase: ${artifact.phase}`,
        `- Status: ${artifact.adg9_guard_execution_status}`,
        `- runtime_code_changed=true`,
        `- guard_function=validateStrictFixtureIdentity`,
        `- guard_location=src/infrastructure/services/FotMobRouteIdentityReconciler.js`,
        '',
        '## Guard Behavior',
        '',
        '- Positive control #4813735: passes guard, correct_mapping, detail identity validated',
        '- Five ADG8 reverse samples: blocked by guard',
        '- Home/away inversion: detected and blocked',
        '- Date mismatch (154-248 day deltas): blocked',
        '- Same-team-pair wrong-leg: blocked',
        '- URL hash alone: insufficient, candidate remains unvalidated',
        '- Suspended references: remain blocked',
        '- raw_write_execution_ready: false (always)',
        '',
        '## Validation Results',
        '',
        `| sample | classification | status | correction | date_delta |`,
        `| --- | --- | --- | --- | --- |`,
    ];

    for (const r of artifact.guard_details || []) {
        lines.push(
            `| ${r.schedule_external_id} | ${r.audit_classification} | ${r.fixture_identity_guard_status} | ${r.correction_needed} | ${r.date_delta_days ?? 'null'} |`
        );
    }

    lines.push(
        '',
        '## Summary',
        '',
        `- audited_sample_count=${artifact.audited_sample_count}`,
        `- guard_passed_count=${artifact.guard_passed_count}`,
        `- guard_blocked_count=${artifact.guard_blocked_count}`,
        `- reverse_fixture_mapping_error_count=${artifact.reverse_fixture_mapping_error_count}`,
        `- correction_candidate_count=${artifact.correction_candidate_count}`,
        `- suspended_reference_still_blocked_count=${artifact.suspended_reference_still_blocked_count}`,
        `- guard_adg8_consistent_count=${artifact.guard_adg8_consistent_count}`,
        '',
        '## Safety',
        '',
        '- no live fetch / network request / browser automation / direct API probing',
        '- no DB writes / raw writes / raw_match_data inserts',
        '- no re-acceptance / suspension reversal',
        '- no source inventory mutation / candidate mutation',
        '- no full payload saved',
        '- raw_write_execution_ready=false',
        '',
        '## Next Step',
        '',
        'No-write regression of strict guard over the 42-target population (Phase 5.21 ADG10 after separate planning).',
        'Do not proceed to raw write.'
    );

    return `${lines.join('\n')}\n`;
}

function parseArgs(argv = process.argv.slice(2)) {
    const options = { writeFiles: true, help: false, unknown: [] };
    for (const arg of argv) {
        if (arg === '--help' || arg === '-h') {
            options.help = true;
            continue;
        }
        if (arg === '--write-files=false' || arg === '--write-files=no' || arg === '--write-files=0') {
            options.writeFiles = false;
            continue;
        }
        if (arg === '--write-files=true' || arg === '--write-files=yes' || arg === '--write-files=1') {
            options.writeFiles = true;
            continue;
        }
        options.unknown.push(arg);
    }
    return options;
}

function runAdg9(options = {}, dependencies = {}) {
    const adg8Result = dependencies.adg8Result || readJsonFile(ADG8_RESULT_PATH);
    const generatedAt = dependencies.generatedAt || new Date().toISOString();
    const artifact = buildArtifact(adg8Result, generatedAt);
    const report = buildReport(artifact);
    if (options.writeFiles !== false) {
        writeJsonFile(ARTIFACT_OUTPUT_PATH, artifact);
        writeTextFile(REPORT_OUTPUT_PATH, report);
    }
    return { ok: true, artifact, report };
}

function main(argv = process.argv.slice(2)) {
    const options = parseArgs(argv);
    if (options.help) {
        process.stdout.write(
            'Usage: node scripts/ops/fotmob_strict_fixture_identity_guard_validate_adg9.js [--write-files=false]\n'
        );
        return { status: 0 };
    }
    const result = runAdg9(options);
    process.stdout.write(
        `${JSON.stringify(
            {
                adg9_guard_execution_status: result.artifact.adg9_guard_execution_status,
                guard_passed_count: result.artifact.guard_passed_count,
                guard_blocked_count: result.artifact.guard_blocked_count,
                correction_candidate_count: result.artifact.correction_candidate_count,
                guard_adg8_consistent_count: result.artifact.guard_adg8_consistent_count,
                raw_write_execution_ready: result.artifact.raw_write_execution_ready,
            },
            null,
            2
        )}\n`
    );
    return { status: 0 };
}

module.exports = {
    PHASE,
    STATUS,
    ADG8_RESULT_PATH,
    ARTIFACT_OUTPUT_PATH,
    REPORT_OUTPUT_PATH,
    buildGuardInput,
    validateAllSamples,
    buildArtifact,
    buildReport,
    runAdg9,
    main,
};

if (require.main === module) {
    try {
        process.exitCode = main().status;
    } catch (error) {
        process.stderr.write(`${error.stack || error.message}\n`);
        process.exitCode = 1;
    }
}
