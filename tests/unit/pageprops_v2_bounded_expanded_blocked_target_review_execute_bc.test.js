const test = require('node:test');
const assert = require('node:assert');
const fs = require('fs');
const path = require('path');

const PROJECT_ROOT = path.resolve(__dirname, '../../');
const RESULT_PATH = path.join(PROJECT_ROOT, 'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.bounded_expanded_blocked_target_review_result.phase521l2v3bc.json');
const PROPOSAL_PATH = path.join(PROJECT_ROOT, 'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.proposal.json');
const REPORT_PATH = path.join(PROJECT_ROOT, 'docs/_reports/DATA_ENTRYPOINT_GOVERNANCE_PHASE5_21_L2V3BC.md');

function readJson(filePath) {
    return JSON.parse(fs.readFileSync(filePath, 'utf8'));
}

test('L2V3BC execution result exists and adheres to safety constraints', () => {
    const result = readJson(RESULT_PATH);
    
    assert.equal(result._meta.phase, '5.21L2V3BC');
    assert.equal(result.review_execution_performed, true);
    assert.equal(result.safety_status.raw_write_execution_ready, false);
    assert.equal(result.safety_status.live_fetch_performed, false);
    assert.equal(result.safety_status.detail_fetch_performed, false);
    assert.equal(result.safety_status.network_request_performed, false);
    assert.equal(result.safety_status.db_write_performed, false);
    assert.equal(result.safety_status.raw_match_data_insert_performed, false);
    assert.equal(result.safety_status.raw_write_execution_performed, false);
    assert.equal(result.safety_status.re_acceptance_execution_performed, false);
    assert.equal(result.safety_status.suspension_reversal_performed, false);
});

test('L2V3BC executes exactly 42 targets', () => {
    const result = readJson(RESULT_PATH);
    
    assert.equal(result.bounded_review_scope_count, 42);
    assert.equal(result.executed_review_target_count, 42);
    assert.equal(result.reviewed_targets.length, 42);
});

test('L2V3BC target classifications comply with convergence gate and trigger architecture decision', () => {
    const result = readJson(RESULT_PATH);
    const summary = result.classification_summary;
    
    const totalProgress = summary.clean_candidate_count + 
                          summary.rejected_mapping_count + 
                          summary.superseded_mapping_count + 
                          summary.eligible_for_re_acceptance_review_count;
                          
    assert.equal(totalProgress, 0);
    assert.equal(summary.needs_new_evidence_count, 42);
    
    assert.equal(result.architecture_decision_gate_required, true);
    assert.equal(result.no_progress_stop_rule_triggered, true);
    assert.equal(result.recommended_next_step, 'Architecture Decision Gate');
});

test('L2V3BC artifacts avoid full payload markers', () => {
    const result = readJson(RESULT_PATH);
    const proposal = readJson(PROPOSAL_PATH);
    const reportText = fs.readFileSync(REPORT_PATH, 'utf8');
    
    const texts = [JSON.stringify(result), JSON.stringify(proposal), reportText];

    for (const text of texts) {
        assert.equal(text.includes('"raw_data":'), false);
        assert.equal(text.includes('"pageProps":'), false);
        assert.equal(text.includes('__NEXT_DATA__'), false);
        assert.equal(text.includes('<!DOCTYPE'), false);
        assert.equal(text.includes('"body":'), false);
        assert.equal(text.includes('"source_body":'), false);
    }
});
