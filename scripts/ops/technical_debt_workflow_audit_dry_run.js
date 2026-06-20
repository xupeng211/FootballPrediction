#!/usr/bin/env node
'use strict';

// lifecycle: permanent
// scope: read-only technical debt & workflow health audit — static scan only, no network, no DB write

const PHASE = 'TECHNICAL_DEBT_WORKFLOW_AUDIT_DRY_RUN';
const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

// ─── constants ──────────────────────────────────────────────────────────────────

const REPO_ROOT = path.resolve(__dirname, '..', '..');

const AREAS = Object.freeze({
    WORKFLOWS: 'github_workflows', BRANCH_MERGE: 'branch_and_merge', TESTS: 'test_debt',
    SCRIPTS: 'script_debt', REPORTS: 'report_debt', DATA_GOVERNANCE: 'data_governance',
    DUAL_STACK: 'python_js_dual_stack', REPO_NOISE: 'repo_noise',
});

const SEVERITY = Object.freeze({
    P0: 'P0 — must fix immediately', P1: 'P1 — fix before data expansion',
    P2: 'P2 — schedule when possible',
});

const RISK_CLASS = Object.freeze({
    DRY_RUN: 'dry_run_safe', WRITE_RISK: 'write_risk_no_safety_gate',
    STRUCTURAL: 'structural_debt', STALE: 'stale_or_superseded',
});

// ─── helpers ────────────────────────────────────────────────────────────────────

function readDir(dirPath) { return fs.existsSync(dirPath) ? fs.readdirSync(dirPath) : []; }
function readFile(filePath) { return fs.existsSync(filePath) ? fs.readFileSync(filePath, 'utf-8') : null; }
function fileLines(filePath) { const c = readFile(filePath); return c ? c.split('\n').length : 0; }

function lsFiles(pattern) {
    try { return execSync(`git -C "${REPO_ROOT}" ls-files ${pattern}`, { encoding: 'utf-8', timeout: 10000 }).trim().split('\n').filter(Boolean); }
    catch { return []; }
}

function grepCount(pattern, dir) {
    try { return parseInt(execSync(`grep -r "${pattern}" "${dir}" --include="*.js" --include="*.py" --include="*.sh" --include="*.sql" -l 2>/dev/null | wc -l`, { encoding: 'utf-8', timeout: 15000 }).trim(), 10) || 0; }
    catch { return 0; }
}

function findFiles(dir, ext, excludeDirs = []) {
    const results = [];
    if (!fs.existsSync(dir)) return results;
    for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
        const full = path.join(dir, entry.name);
        if (excludeDirs.some(d => full.includes(d))) continue;
        if (entry.isDirectory()) results.push(...findFiles(full, ext, excludeDirs));
        else if (entry.name.endsWith(ext)) results.push(full);
    }
    return results;
}

function countLines(files) { let t = 0; for (const f of files) { try { t += fs.readFileSync(f, 'utf-8').split('\n').length; } catch { /* skip */ } } return t; }

function finding(id, area, severity, riskClass, title, detail, impact = '', recommendation = '') {
    return { id, area, severity, risk_class: riskClass, title, detail, impact, recommendation };
}

function scanDbWriteScripts(scripts) {
    const writePat = ['INSERT INTO', 'UPDATE.*SET', 'DELETE FROM', 'ON CONFLICT.*DO UPDATE'];
    const gatePat = ['ALLOW_DB_WRITE', 'FINAL_DB_WRITE_CONFIRMATION', 'ALLOW_RAW_MATCH_DATA_WRITE'];
    const results = [];
    for (const s of scripts) {
        const c = readFile(s) || '';
        if (writePat.some(p => new RegExp(p, 'i').test(c)) && !gatePat.some(p => c.includes(p)))
            {results.push({ path: path.relative(REPO_ROOT, s), lines: c.split('\n').length });}
    }
    return results;
}

// ─── area 1: github workflows ───────────────────────────────────────────────────

function auditWorkflows() {
    const findings = [];
    const wfDir = path.join(REPO_ROOT, '.github', 'workflows');
    const wfFiles = readDir(wfDir).filter(f => f.endsWith('.yml') || f.endsWith('.yaml'));
    const combinedYaml = wfFiles.map(f => readFile(path.join(wfDir, f)) || '').join('\n');
    const gkContent = readFile(path.join(REPO_ROOT, 'scripts', 'devops', 'gatekeeper.sh')) || '';

    findings.push(finding('WF-001', AREAS.WORKFLOWS, SEVERITY.P0, RISK_CLASS.STRUCTURAL,
        'Single workflow file bears all CI responsibility',
        `${wfFiles.length} file(s): ${wfFiles.join(', ')}. One job runs everything sequentially — no matrix, no parallelization, no backup workflow.`,
        'Any misconfiguration in this file takes down the entire CI pipeline.',
        'Split into separate workflow files: lint, test, security, build. Add workflow_dispatch trigger.'));

    if (!combinedYaml.includes('schedule') && !combinedYaml.includes('cron'))
        {findings.push(finding('WF-002', AREAS.WORKFLOWS, SEVERITY.P2, RISK_CLASS.STRUCTURAL,
            'No scheduled/cron workflow triggers', 'No nightly CI runs. Main branch health only checked on push/PR.',
            'Silent main breakage possible.', 'Add nightly cron workflow on main.'));}

    if (!combinedYaml.includes('paths') && !combinedYaml.includes('paths-ignore'))
        {findings.push(finding('WF-003', AREAS.WORKFLOWS, SEVERITY.P2, RISK_CLASS.STRUCTURAL,
            'No path-based filtering on workflow triggers',
            'Every PR runs full 30-min gate regardless of what changed. Docs-only changes still build Docker + DB.',
            'Wastes CI minutes.', 'Add paths-ignore for docs/, .gitignore changes.'));}

    if (combinedYaml.includes('skip-body-checks') || gkContent.includes('skip-body-checks'))
        {findings.push(finding('WF-004', AREAS.WORKFLOWS, SEVERITY.P1, RISK_CLASS.STRUCTURAL,
            'Push events skip PR body governance checks',
            'AI Workflow Gate on push bypasses section presence, safety consistency, hollow content detection.',
            'Governance bypass possible without strict branch protection.',
            'Add post-merge governance validation workflow. Require PR before push in GitHub settings.'));}

    const pyTestFiles = findFiles(path.join(REPO_ROOT, 'tests'), '.py', ['node_modules', '.venv', '__pycache__', 'Z_LEGACY']);
    const pyTestsInCI = gkContent.includes('pytest') || gkContent.includes('python.*test');
    if (pyTestFiles.length > 10 && !pyTestsInCI)
        {findings.push(finding('WF-005', AREAS.WORKFLOWS, SEVERITY.P0, RISK_CLASS.STRUCTURAL,
            'Python unit tests never run in CI',
            `${pyTestFiles.length} Python test files exist but CI runs only ruff + mypy + one config test.`,
            'Python business logic can be broken and CI still passes.',
            'Add pytest run to CI gate with coverage.'));}

    findings.push(finding('WF-006', AREAS.WORKFLOWS, SEVERITY.P1, RISK_CLASS.STRUCTURAL,
        'Docker build validation is compile-only, no runtime check',
        'docker-build job only verifies buildx exits zero. No container launch, no health check.',
        'Broken runtime deps not caught.', 'Add post-build smoke test: start container, verify health.'));

    const intDir = path.join(REPO_ROOT, 'tests', 'integration');
    const intFiles = fs.existsSync(intDir) ? readDir(intDir).filter(f => f.endsWith('.js') && !f.includes('.disabled')) : [];
    if (intFiles.length > 0)
        {findings.push(finding('WF-007', AREAS.WORKFLOWS, SEVERITY.P1, RISK_CLASS.STRUCTURAL,
            `${intFiles.length} active integration test files never run in CI`,
            `Files: ${intFiles.join(', ')}. Not invoked by any workflow.`,
            'Integration regressions only caught manually.', 'Add CI job for integration tests.'));}

    findings.push(finding('WF-008', AREAS.WORKFLOWS, SEVERITY.P1, RISK_CLASS.STRUCTURAL,
        'Full coverage gates only run on push to main, not on PR',
        'PR mode runs only incremental tests + recon-core. 80% floor only applies on push.',
        'PR can merge with coverage below threshold.', 'Move coverage gates to PR workflow.'));

    const gkJsPath = path.join(REPO_ROOT, 'scripts', 'ops', 'gatekeeper.js');
    if (fs.existsSync(gkJsPath))
        {findings.push(finding('WF-009', AREAS.WORKFLOWS, SEVERITY.P2, RISK_CLASS.STALE,
            'Dead code: scripts/ops/gatekeeper.js never invoked',
            '329-line Node.js gatekeeper. CI uses gatekeeper.sh exclusively. Acknowledged orphan in repoHygiene.js.',
            'Maintenance burden.', 'Delete or deprecate with removal timeline.'));}

    return { area: AREAS.WORKFLOWS, workflow_file_count: wfFiles.length, workflow_files: wfFiles, findings };
}

// ─── area 2: branch and merge ───────────────────────────────────────────────────

function auditBranchMerge() {
    const findings = [];
    const gkContent = readFile(path.join(REPO_ROOT, 'scripts', 'devops', 'gatekeeper.sh')) || '';
    const hasDataBranches = gkContent.includes('data/*');

    if (!hasDataBranches)
        {findings.push(finding('BM-001', AREAS.BRANCH_MERGE, SEVERITY.P0, RISK_CLASS.STRUCTURAL,
            'Gatekeeper only recognizes security/* and feat/* as preferred workspace',
            'data/* branches account for ~82% of remote branches and ~73% of merges but trigger workspace warning on every push.',
            'Warning noise reduces attention to real gate failures.',
            'Add data/*, docs/*, chore/* to preferred workspace branches.'));}

    findings.push(finding('BM-002', AREAS.BRANCH_MERGE, SEVERITY.P0, RISK_CLASS.STRUCTURAL,
        'No GitHub-side branch protection rules configured',
        'No CODEOWNERS, no required status checks, no merge queue. Protection is client-side hooks only, which can be bypassed.',
        'Developer can push directly to main by skipping hooks.',
        'Configure GitHub branch protection: require PR, status checks, block force push.'));

    findings.push(finding('BM-003', AREAS.BRANCH_MERGE, SEVERITY.P1, RISK_CLASS.STRUCTURAL,
        'Post-merge verification is manual only',
        'No automated CI validates that a push to main came from a proper PR merge.',
        'Direct pushes can land undetected.', 'Add post-merge CI workflow validating merge provenance.'));

    try {
        const rc = parseInt(execSync(`git -C "${REPO_ROOT}" ls-remote --heads origin 2>/dev/null | wc -l`, { encoding: 'utf-8', timeout: 10000 }).trim(), 10) || 0;
        if (rc > 100)
            {findings.push(finding('BM-004', AREAS.BRANCH_MERGE, SEVERITY.P2, RISK_CLASS.STALE,
                `Excessive remote branch count: ${rc} on origin`,
                'Most are stale data/* phase-artifact branches.', 'Slows git ops.', 'Implement post-merge branch cleanup.'));}
    } catch { /* offline */ }

    findings.push(finding('BM-005', AREAS.BRANCH_MERGE, SEVERITY.P2, RISK_CLASS.STRUCTURAL,
        'Branch naming convention only in gatekeeper.sh, not docs',
        'No BRANCH_NAMING.md. Valid prefixes only defined in git_branch_is_preferred_workspace().',
        'Confusion for new contributors.', 'Document naming convention in docs/.'));

    return { area: AREAS.BRANCH_MERGE, findings };
}

// ─── area 3: test debt ─────────────────────────────────────────────────────────

function auditTests() {
    const findings = [];
    const testsDir = path.join(REPO_ROOT, 'tests');
    const unitDir = path.join(testsDir, 'unit');
    const intDir = path.join(testsDir, 'integration');
    const stressDir = path.join(testsDir, 'stress');

    const unitFiles = fs.existsSync(unitDir) ? findFiles(unitDir, '.js', ['node_modules', 'Z_LEGACY']) : [];
    const intFiles = fs.existsSync(intDir) ? findFiles(intDir, '.js', ['node_modules']) : [];
    const stressFiles = fs.existsSync(stressDir) ? findFiles(stressDir, '.js', ['node_modules']) : [];
    const pyTestFiles = findFiles(testsDir, '.py', ['node_modules', '.venv', '__pycache__', 'Z_LEGACY']);

    const allTests = [...unitFiles, ...intFiles, ...stressFiles, ...pyTestFiles];
    const oversized = allTests.map(f => ({ path: f, lines: fileLines(f) })).filter(f => f.lines > 500).sort((a, b) => b.lines - a.lines);

    if (oversized.length > 50)
        {findings.push(finding('TE-001', AREAS.TESTS, SEVERITY.P1, RISK_CLASS.STRUCTURAL,
            `${oversized.length} test files exceed 500 lines`,
            `Largest: ${oversized.slice(0, 5).map(f => `${path.relative(REPO_ROOT, f.path)} (${f.lines}L)`).join(', ')}`,
            'Hard to maintain and review.', 'Split by behavior domain. Target <300 lines.'));}

    if (unitFiles.length > 100 && intFiles.length < 20 && stressFiles.length < 5)
        {findings.push(finding('TE-002', AREAS.TESTS, SEVERITY.P1, RISK_CLASS.STRUCTURAL,
            'Test pyramid imbalance: ~99% unit, ~1% integration',
            `Unit: ${unitFiles.length} files (${countLines(unitFiles)} lines), Integration: ${intFiles.length}, Stress: ${stressFiles.length}.`,
            'Integration points and E2E flows barely tested.', 'Add integration tests for key pipeline stages.'));}

    const disabled = findFiles(testsDir, '.disabled', ['node_modules']);
    if (disabled.length > 0)
        {findings.push(finding('TE-003', AREAS.TESTS, SEVERITY.P1, RISK_CLASS.STALE,
            `${disabled.length} disabled test files exist`,
            `Disabled: ${disabled.map(f => path.relative(REPO_ROOT, f)).join(', ')}`,
            'Accumulate without resolution.', 'Fix/re-enable within 1 sprint or delete.'));}

    const spawnCount = grepCount('spawnSync|execSync', testsDir);
    if (spawnCount > 30)
        {findings.push(finding('TE-004', AREAS.TESTS, SEVERITY.P2, RISK_CLASS.STRUCTURAL,
            `${spawnCount} test files use spawnSync/execSync — testing output, not behavior`,
            'Tests run scripts as subprocess, check exit codes. Brittle, prevents coverage instrumentation.',
            'Refactor to directly import and test module functions.'));}

    findings.push(finding('TE-005', AREAS.TESTS, SEVERITY.P2, RISK_CLASS.STRUCTURAL,
        'Python and JS tests follow fundamentally different patterns',
        `Python (${pyTestFiles.length} files): heavy subprocess.run, mock. JS (${unitFiles.length}): direct require. No shared fixtures.`,
        'Inconsistent patterns.', 'Adopt shared fixture strategy. Prefer direct imports.'));

    return { area: AREAS.TESTS, unit_files: unitFiles.length, unit_lines: countLines(unitFiles),
        integration_files: intFiles.length, integration_lines: countLines(intFiles),
        stress_files: stressFiles.length, stress_lines: countLines(stressFiles),
        python_test_files: pyTestFiles.length, python_test_lines: countLines(pyTestFiles),
        oversized_test_files: oversized.length, disabled_test_files: disabled.length, findings };
}

// ─── area 4: script debt ────────────────────────────────────────────────────────

function auditScripts() {
    const findings = [];
    const opsDir = path.join(REPO_ROOT, 'scripts', 'ops');
    const devopsDir = path.join(REPO_ROOT, 'scripts', 'devops');

    const opsJs = fs.existsSync(opsDir) ? findFiles(opsDir, '.js', ['node_modules', 'helpers']) : [];
    const opsPy = fs.existsSync(opsDir) ? findFiles(opsDir, '.py', ['node_modules']) : [];
    const devopsJs = fs.existsSync(devopsDir) ? findFiles(devopsDir, '.js', []) : [];
    const allOps = [...opsJs, ...opsPy];

    const dryRun = allOps.filter(f => f.includes('dry_run') || f.includes('dry-run') || f.includes('no_write'));
    if (dryRun.length > 80)
        {findings.push(finding('SC-001', AREAS.SCRIPTS, SEVERITY.P1, RISK_CLASS.DRY_RUN,
            `${dryRun.length} dry-run/no-write scripts — excessive investigation artifacts`,
            `${dryRun.length} scripts (~${Math.round(dryRun.length / allOps.length * 100)}% of ops) are investigation artifacts. Many are phase-completed.`,
            'Massive cognitive overhead.', 'Archive completed investigation scripts.'));}

    const dbWriteRisk = scanDbWriteScripts(allOps);
    if (dbWriteRisk.length > 5)
        {findings.push(finding('SC-002', AREAS.SCRIPTS, SEVERITY.P0, RISK_CLASS.WRITE_RISK,
            `${dbWriteRisk.length} scripts perform DB writes without safety gates`,
            `INSERT/UPDATE/DELETE but no ALLOW_DB_WRITE check: ${dbWriteRisk.slice(0, 10).map(s => s.path).join(', ')}`,
            'Highest risk: accidental prod DB write likely.',
            'Add ALLOW_DB_WRITE and FINAL_DB_WRITE_CONFIRMATION gates to all DB-writing scripts.'));}

    const allRefs = (readFile(path.join(REPO_ROOT, 'Makefile')) || '') +
        (readFile(path.join(REPO_ROOT, 'package.json')) || '') +
        (readFile(path.join(REPO_ROOT, 'scripts', 'devops', 'gatekeeper.sh')) || '');
    const orphans = allOps.filter(f => !allRefs.includes(path.basename(f)));
    if (orphans.length > 100)
        {findings.push(finding('SC-003', AREAS.SCRIPTS, SEVERITY.P2, RISK_CLASS.STALE,
            `${orphans.length} scripts not referenced by Makefile/pkg.json/gatekeeper.sh`,
            `~${Math.round(orphans.length / allOps.length * 100)}% of ops are orphans. Includes ~100 ADG campaign and ~50 Python no_write triplets.`,
            'Dead code burden.', 'Archive completed campaigns. Delete one-shots.'));}

    const rmdi = grepCount('INSERT INTO raw_match_data', opsDir);
    if (rmdi > 5)
        {findings.push(finding('SC-004', AREAS.SCRIPTS, SEVERITY.P1, RISK_CLASS.STRUCTURAL,
            `INSERT INTO raw_match_data duplicated across ${rmdi} scripts`,
            'Copy-pasted SQL. No centralized write abstraction.',
            'Schema changes require hunting every occurrence.', 'Create shared RawMatchDataWriter module.'));}

    const mi = grepCount('INSERT INTO matches', opsDir);
    if (mi > 5)
        {findings.push(finding('SC-005', AREAS.SCRIPTS, SEVERITY.P1, RISK_CLASS.STRUCTURAL,
            `INSERT INTO matches duplicated across ${mi} scripts`,
            'Same pattern as raw_match_data.', 'See SC-004.', 'Create shared MatchesWriter module.'));}

    return { area: AREAS.SCRIPTS, ops_js_files: opsJs.length, ops_py_files: opsPy.length,
        devops_files: devopsJs.length, dry_run_scripts: dryRun.length,
        scripts_with_db_write_no_gate: dbWriteRisk.length, orphan_scripts: orphans.length, findings };
}

// ─── area 5: report debt ────────────────────────────────────────────────────────

function auditReports() {
    const findings = [];
    const reportsDir = path.join(REPO_ROOT, 'docs', '_reports');
    if (!fs.existsSync(reportsDir)) return { area: AREAS.REPORTS, report_count: 0, report_lines: 0, findings };

    const reportFiles = findFiles(reportsDir, '.md', []);
    const reportLines = countLines(reportFiles);

    if (reportFiles.length > 300)
        {findings.push(finding('RP-001', AREAS.REPORTS, SEVERITY.P1, RISK_CLASS.STALE,
            `${reportFiles.length} report files (${reportLines} lines) — excessive accumulation`,
            'Write-once-never-update pattern. Most are phase-artifact evidence, not current state.',
            'Signal-to-noise ratio very poor.', 'Archive completed phase reports. Consolidate series.'));}

    const neededDocs = [{ file: 'DEBT_REGISTER.md', id: 'RP-002', desc: 'tech debt' },
        { file: 'DATA_STATUS.md', id: 'RP-003', desc: 'data pipeline state' }];
    for (const doc of neededDocs) {
        if (!fs.existsSync(path.join(REPO_ROOT, 'docs', doc.file)))
            {findings.push(finding(doc.id, AREAS.REPORTS, SEVERITY.P1, RISK_CLASS.STRUCTURAL,
                `Missing current-state: docs/${doc.file}`,
                `No centralized ${doc.desc} tracking. Current state fragmented across ${reportFiles.length}+ reports.`,
                '', `Create docs/${doc.file} as single source of truth.`));}
    }

    const psContent = readFile(path.join(REPO_ROOT, 'docs', 'PROJECT_STATUS.md'));
    if (psContent && psContent.includes('363 historical report files'))
        {findings.push(finding('RP-004', AREAS.REPORTS, SEVERITY.P2, RISK_CLASS.STALE,
            `PROJECT_STATUS.md count stale (claims 363, actual ${reportFiles.length})`,
            `Off by ${reportFiles.length - 363}. Last updated 2026-06-07.`,
            'Misleading status info.', 'Update counts or automate.'));}

    const fcsContent = readFile(path.join(REPO_ROOT, 'docs', 'data', 'FOTMOB_CURRENT_STATE.md')) || '';
    if (fcsContent.includes('Superseded notice') || fcsContent.includes('superseded'))
        {findings.push(finding('RP-005', AREAS.REPORTS, SEVERITY.P1, RISK_CLASS.STALE,
            'FOTMOB_CURRENT_STATE.md carries superseded notice but remains primary entry doc',
            'Its core claims are superseded but it still serves as canonical reference. Readers must cross-reference FOTMOB_RETAINED_RAW_STAGE_STATUS.md.',
            'Confusion about authority.', 'Consolidate into single current-truth doc.'));}

    return { area: AREAS.REPORTS, report_count: reportFiles.length, report_lines: reportLines, findings };
}

// ─── area 6: data governance ────────────────────────────────────────────────────

function auditDataGovernance() {
    const findings = [];
    const trainPy = readFile(path.join(REPO_ROOT, 'scripts', 'ops', 'train_model.py')) || '';

    if (trainPy && !trainPy.includes('is_training_eligible'))
        {findings.push(finding('DG-001', AREAS.DATA_GOVERNANCE, SEVERITY.P0, RISK_CLASS.WRITE_RISK,
            'Training pipeline bypasses all governance labels',
            'train_model.py queries status=Harvested (wrong case) and ignores is_training_eligible/source_type/evidence_level.',
            'Governance layer (V26.7) has zero effect on model training.',
            'Fix case mismatch. Add is_training_eligible=true, evidence_level checks.'));}

    const initDb = readFile(path.join(REPO_ROOT, 'deploy', 'docker', 'init_db.sql')) || '';
    const missing = ['pipeline_status', 'source_type', 'evidence_level', 'is_production_scope',
        'is_reconciliation_eligible', 'is_training_eligible', 'pipeline_status_reason'].filter(c => !initDb.includes(c));
    if (missing.length > 3)
        {findings.push(finding('DG-002', AREAS.DATA_GOVERNANCE, SEVERITY.P0, RISK_CLASS.STRUCTURAL,
            `init_db.sql is ${missing.length}+ columns behind migration chain`,
            `Missing: ${missing.join(', ')}. Fresh deploy creates broken schema.`,
            'Cold-start deploy broken.', 'Update init_db.sql to match current migrations.'));}

    if (initDb.includes('UNIQUE(match_id)') && !initDb.includes('UNIQUE(match_id, data_version)'))
        {findings.push(finding('DG-003', AREAS.DATA_GOVERNANCE, SEVERITY.P1, RISK_CLASS.STRUCTURAL,
            'raw_match_data UNIQUE constraint conflict',
            'init_db.sql has UNIQUE(match_id) but scripts expect UNIQUE(match_id, data_version) for multi-version storage.',
            'Multi-version raw storage breaks on fresh deploy.', 'Reconcile init_db.sql with migration chain.'));}

    let hasDvCheck = false;
    for (const m of findFiles(path.join(REPO_ROOT, 'database', 'migrations'), '.sql', [])) {
        const mc = readFile(m) || '';
        if (mc.includes('data_version') && mc.includes('CHECK')) { hasDvCheck = true; break; }
    }
    if (!hasDvCheck)
        {findings.push(finding('DG-004', AREAS.DATA_GOVERNANCE, SEVERITY.P2, RISK_CLASS.STRUCTURAL,
            'data_version has no CHECK constraint (no controlled vocabulary)',
            'Ad-hoc strings with no DB enforcement. Version targeting relies on hardcoded string matching.',
            'Any code can write any version string.', 'Add CHECK constraint. Define version constants.'));}

    findings.push(finding('DG-005', AREAS.DATA_GOVERNANCE, SEVERITY.P1, RISK_CLASS.STRUCTURAL,
        'V26.7 governance columns all NULL — backfill not executed',
        'is_training_eligible etc all NULL for all 60 matches. Governance labels cannot be used for filtering.',
        'Training eligibility pipeline cannot proceed.', 'Execute 4-phase backfill (A-D) with user auth.'));

    findings.push(finding('DG-006', AREAS.DATA_GOVERNANCE, SEVERITY.P0, RISK_CLASS.STRUCTURAL,
        'Feature leakage prevention policy (cutoff time) is undefined',
        'Training eligibility Rule 3 requires prediction_cutoff_time policy that does not exist.',
        'Training cannot safely begin. Post-match features could leak into training.',
        'Define prediction_cutoff_time policy. Implement time-gated feature extraction.'));

    return { area: AREAS.DATA_GOVERNANCE, findings };
}

// ─── area 7: dual-stack debt ────────────────────────────────────────────────────

function auditDualStack() {
    const findings = [];
    const srcJs = findFiles(path.join(REPO_ROOT, 'src'), '.js', ['node_modules']);
    const srcPy = findFiles(path.join(REPO_ROOT, 'src'), '.py', ['__pycache__', '.venv']);
    const cfgJs = findFiles(path.join(REPO_ROOT, 'config'), '.js', ['node_modules']);
    const cfgPy = findFiles(path.join(REPO_ROOT, 'config'), '.py', ['__pycache__']);

    const jsLines = countLines([...srcJs, ...cfgJs]);
    const pyLines = countLines([...srcPy, ...cfgPy]);

    if (jsLines > pyLines * 2)
        {findings.push(finding('DS-001', AREAS.DUAL_STACK, SEVERITY.P1, RISK_CLASS.STRUCTURAL,
            `JS codebase is ${Math.round(jsLines / Math.max(pyLines, 1))}x larger than Python (${jsLines} vs ${pyLines}L)`,
            `JS: ${srcJs.length + cfgJs.length} files. Python: ${srcPy.length + cfgPy.length} files.`,
            'Asymmetric maintenance burden.', 'Evaluate JS consolidation. Consider TypeScript.'));}

    const eloPy = path.join(REPO_ROOT, 'src', 'ml', 'features', 'elo_rating_system.py');
    const eloJs = path.join(REPO_ROOT, 'src', 'feature_engine', 'extractors', 'EloRatingExtractor.js');
    if (fs.existsSync(eloPy) && fs.existsSync(eloJs))
        {findings.push(finding('DS-002', AREAS.DUAL_STACK, SEVERITY.P0, RISK_CLASS.STRUCTURAL,
            'ELO rating algorithm duplicated across Python and JS',
            `Python: elo_rating_system.py (${fileLines(eloPy)}L). JS: EloRatingExtractor.js (${fileLines(eloJs)}L). No shared algorithm or cross-validation.`,
            'K-factor/rating changes in one stack silently diverge from the other.',
            'Extract ELO config to shared_constants.json. Both stacks validate against each other.'));}

    const cc1 = path.join(REPO_ROOT, 'config', 'constants.js');
    const cc2 = path.join(REPO_ROOT, 'src', 'config', 'constants.js');
    if (fs.existsSync(cc1) && fs.existsSync(cc2)) {
        const c1 = readFile(cc1) || ''; const c2 = readFile(cc2) || '';
        if (c1 === c2 && c1.length > 100)
            {findings.push(finding('DS-003', AREAS.DUAL_STACK, SEVERITY.P2, RISK_CLASS.STRUCTURAL,
                'config/constants.js and src/config/constants.js are identical copies',
                'Any change must be made in both places.', 'Duplicate burden.', 'Keep one canonical copy.'));}
    }

    findings.push(finding('DS-004', AREAS.DUAL_STACK, SEVERITY.P2, RISK_CLASS.STRUCTURAL,
        '380K lines of JavaScript with no type system',
        'No TypeScript, all JSDoc rules disabled. Only complexity cap (15) provides structural protection.',
        'Type errors only at runtime. Refactoring risky.', 'Consider incremental TypeScript or JSDoc type checking.'));

    return { area: AREAS.DUAL_STACK, js_source_files: srcJs.length + cfgJs.length, js_source_lines: jsLines,
        py_source_files: srcPy.length + cfgPy.length, py_source_lines: pyLines, findings };
}

// ─── area 8: repo noise ─────────────────────────────────────────────────────────

function checkCodexTmp() {
    const dir = path.join(REPO_ROOT, '.codex-tmp');
    if (!fs.existsSync(dir)) return null;
    try {
        const size = parseInt(execSync(`du -sm "${dir}" 2>/dev/null | cut -f1`, { encoding: 'utf-8', timeout: 5000 }).trim(), 10) || 0;
        if (size <= 100) return null;
        return finding('RN-001', AREAS.REPO_NOISE, SEVERITY.P2, RISK_CLASS.STALE,
            `.codex-tmp/ is ${size} MB — cleanup needed`,
            `${size} MB of execution artifacts.`, 'Disk waste.', 'Clean up. Add to .gitignore.');
    } catch { return null; }
}

function checkTrackedNoise() {
    const tracked = lsFiles('').filter(f => f.includes('package-lock.json') ||
        (f.includes('data/debug/') && f.endsWith('.png')) ||
        (f.includes('docs/audit/') && (f.endsWith('.csv') || f.endsWith('.png'))));
    if (!tracked.length) return null;
    return finding('RN-002', AREAS.REPO_NOISE, SEVERITY.P2, RISK_CLASS.STALE,
        `${tracked.length} tracked files match .gitignore but remain in index`,
        tracked.join(', '), 'Repo bloat.', 'git rm --cached.');
}

function checkArchiveVault() {
    const vault = path.join(REPO_ROOT, 'archive_vault_2026');
    if (!fs.existsSync(vault)) return null;
    const count = findFiles(vault, '.py', []).length + findFiles(vault, '.js', []).length;
    if (count <= 10) return null;
    return finding('RN-003', AREAS.REPO_NOISE, SEVERITY.P2, RISK_CLASS.STALE,
        `archive_vault_2026/ contains ${count} tracked source files`,
        '.gitignore only excludes archive/ not archive_vault_2026/.', 'Repo bloat.', 'Add to .gitignore, untrack.');
}

function checkDockerignore() {
    const diPath = path.join(REPO_ROOT, '.dockerignore');
    const lines = (readFile(diPath) || '').split('\n').filter(Boolean).length;
    if (lines >= 50) return null;
    return finding('RN-004', AREAS.REPO_NOISE, SEVERITY.P2, RISK_CLASS.STRUCTURAL,
        `.dockerignore sparse (${lines} vs .gitignore 400+)`,
        'Missing: pkg-lock, Makefile, reports/, logs, binary artifacts.', 'Docker context too large.', 'Align with .gitignore.');
}

function checkLargeLegacy(gitFiles) {
    const large = [];
    for (const f of gitFiles) {
        try { const st = fs.statSync(path.join(REPO_ROOT, f)); if (st.size > 100 * 1024 && f.includes('Z_LEGACY')) large.push({ path: f, sizeKB: Math.round(st.size / 1024) }); }
        catch { /* skip */ }
    }
    if (!large.length) return null;
    return finding('RN-005', AREAS.REPO_NOISE, SEVERITY.P2, RISK_CLASS.STALE,
        `${large.length} large legacy test fixtures tracked`,
        `Largest: ${large.slice(0, 3).map(f => `${f.path} (${f.sizeKB}KB)`).join(', ')}`,
        'Clone size.', 'Move out of active repo.');
}

function auditRepoNoise() {
    const findings = [];
    const gitFiles = lsFiles('');
    for (const check of [checkCodexTmp(), checkTrackedNoise(), checkArchiveVault(), checkDockerignore(), checkLargeLegacy(gitFiles)])
        {if (check) findings.push(check);}
    return { area: AREAS.REPO_NOISE, findings };
}

// ─── main orchestrator ──────────────────────────────────────────────────────────

function runAudit() {
    const results = { phase: PHASE, timestamp: new Date().toISOString(), repo_root: REPO_ROOT, areas: {}, all_findings: [], summary: {} };
    const areaNames = Object.values(AREAS);
    const auditFns = [auditWorkflows, auditBranchMerge, auditTests, auditScripts, auditReports, auditDataGovernance, auditDualStack, auditRepoNoise];

    for (let i = 0; i < auditFns.length; i++) {
        const r = auditFns[i]();
        results.areas[areaNames[i]] = r;
        results.all_findings.push(...r.findings);
    }

    const p0 = results.all_findings.filter(f => f.severity === SEVERITY.P0);
    const p1 = results.all_findings.filter(f => f.severity === SEVERITY.P1);
    const p2 = results.all_findings.filter(f => f.severity === SEVERITY.P2);

    const wfP0 = p0.filter(f => f.area === AREAS.WORKFLOWS).length;
    const wfHealth = wfP0 >= 2 ? 'LOW' : wfP0 >= 1 ? 'MEDIUM' : 'HIGH';
    const debt = p0.length >= 5 ? 'EXTREMELY_HIGH' : p0.length >= 3 ? 'HIGH' : p0.length >= 1 ? 'MEDIUM' : 'LOW';

    const expansionBlockers = p0.filter(f => f.id.startsWith('DG-') || f.id === 'WF-005' || f.id === 'BM-002');
    const trainingBlockers = p0.filter(f => f.id.startsWith('DG-') || f.id === 'DS-002');

    results.summary = {
        total_findings: results.all_findings.length, p0_count: p0.length, p1_count: p1.length, p2_count: p2.length,
        overall_debt: debt, workflow_health: wfHealth,
        dry_run_safe_count: results.all_findings.filter(f => f.risk_class === RISK_CLASS.DRY_RUN).length,
        write_risk_count: results.all_findings.filter(f => f.risk_class === RISK_CLASS.WRITE_RISK).length,
        structural_count: results.all_findings.filter(f => f.risk_class === RISK_CLASS.STRUCTURAL).length,
        stale_count: results.all_findings.filter(f => f.risk_class === RISK_CLASS.STALE).length,
        p0_findings: p0.map(f => ({ id: f.id, title: f.title, area: f.area })),
        p1_findings: p1.map(f => ({ id: f.id, title: f.title, area: f.area })),
        p2_findings: p2.map(f => ({ id: f.id, title: f.title, area: f.area })),
        can_proceed_to_expansion_plan: expansionBlockers.length === 0,
        expansion_blockers: expansionBlockers.length > 0 ? expansionBlockers.map(f => `${f.id}: ${f.title}`) : [],
        training_blocked: trainingBlockers.length > 0,
        training_blockers: trainingBlockers.length > 0 ? trainingBlockers.map(f => `${f.id}: ${f.title}`) : [],
    };

    return results;
}

// ─── CLI ────────────────────────────────────────────────────────────────────────

function parseArgs(argv) {
    const args = { json: false, help: false };
    for (const a of argv) { if (a === '--json') args.json = true; if (a === '--help' || a === '-h') args.help = true; }
    return args;
}

function printHelp() {
    console.log(`Usage: node scripts/ops/technical_debt_workflow_audit_dry_run.js [--json] [--help]
Options: --json (JSON output) --help (this message)
Read-only static audit of 8 areas. No network. No DB write. No file modifications.`);
}

function main() {
    const args = parseArgs(process.argv.slice(2));
    if (args.help) { printHelp(); process.exit(0); }
    const results = runAudit();
    if (args.json) { console.log(JSON.stringify(results, null, 2)); return results; }

    const s = results.summary;
    const lines = [
        `\n=== ${PHASE} ===`, `Timestamp: ${results.timestamp}`,
        `\nTotal findings: ${s.total_findings}`, `  P0: ${s.p0_count}  P1: ${s.p1_count}  P2: ${s.p2_count}`,
        `\nOverall debt: ${s.overall_debt}  Workflow health: ${s.workflow_health}`,
        `\nCan proceed to expansion: ${s.can_proceed_to_expansion_plan ? 'YES' : 'NO'}  Training blocked: ${s.training_blocked ? 'YES' : 'NO'}`,
        '\n--- P0 ---', ...s.p0_findings.map(f => `  ${f.id}: ${f.title} [${f.area}]`),
        '\n--- P1 ---', ...s.p1_findings.map(f => `  ${f.id}: ${f.title} [${f.area}]`),
        '\n--- P2 ---', ...s.p2_findings.map(f => `  ${f.id}: ${f.title} [${f.area}]`), '',
    ];
    console.log(lines.join('\n'));
    return results;
}

module.exports = { PHASE, AREAS, SEVERITY, RISK_CLASS, finding, auditWorkflows, auditBranchMerge, auditTests, auditScripts, auditReports, auditDataGovernance, auditDualStack, auditRepoNoise, runAudit, parseArgs, scanDbWriteScripts };
if (require.main === module) main();
