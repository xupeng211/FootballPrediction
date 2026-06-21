#!/usr/bin/env node
'use strict';

// lifecycle: permanent
// scope: read-only authoritative workflow enforcement audit; static scan only, no network, no DB, no scanned-script execution

const fs = require('node:fs');
const path = require('node:path');

const PHASE = 'AUTHORITATIVE_WORKFLOW_ENFORCEMENT_DRY_RUN';
const REPO_ROOT = path.resolve(__dirname, '..', '..');
const REPORT_BACKLINK_TARGETS = [
    'docs/PROJECT_STATUS.md',
    'docs/DOCUMENTATION_GOVERNANCE.md',
    'docs/CODEX_WORKFLOW.md',
    'docs/AGENT_WORKFLOW.md',
    'docs/DATA_SOURCE_STRATEGY.md',
    'docs/data/FOTMOB_CURRENT_STATE.md',
];

const AUTHORITATIVE_CANDIDATES = [
    { path: 'docs/PROJECT_STATUS.md', role: 'current project status ledger', recommended: true },
    { path: 'docs/DOCUMENTATION_GOVERNANCE.md', role: 'documentation governance rules', recommended: true },
    { path: 'docs/CODEX_WORKFLOW.md', role: 'Codex agent workflow rules', recommended: true },
    { path: 'docs/AGENT_WORKFLOW.md', role: 'agent workflow hardening rules', recommended: true },
    { path: '.github/pull_request_template.md', role: 'active PR template', recommended: true },
    { path: 'AGENTS.md', role: 'agent entrypoint', recommended: true },
    { path: 'CLAUDE.md', role: 'Claude agent entrypoint', recommended: true },
    { path: 'docs/DATA_SOURCE_STRATEGY.md', role: 'data source strategy', recommended: true },
    { path: 'docs/data/FOTMOB_CURRENT_STATE.md', role: 'FotMob current state', recommended: true },
    { path: 'docs/CHANGELOG.md', role: 'historical changelog', recommended: false },
    { path: 'README.md', role: 'public project overview', recommended: false },
    { path: '.github/PULL_REQUEST_TEMPLATE.md', role: 'legacy uppercase PR template', recommended: false },
];

const REQUIRED_AUTH_DOCS = [
    'docs/PROJECT_STATUS.md',
    'docs/DOCUMENTATION_GOVERNANCE.md',
    'docs/CODEX_WORKFLOW.md',
    '.github/pull_request_template.md',
    'AGENTS.md',
];

const PLANNED_DOCS_FROM_GOVERNANCE = [
    'docs/FOTMOB_CURRENT_STATE.md',
    'docs/CANONICAL_MATCH_SCHEMA.md',
    'docs/DEVELOPMENT_WORKFLOW.md',
    'docs/README.md',
];

const RECENT_REPORTS = [
    {
        task: 'formal_training_cohort_inventory_dry_run',
        path: 'docs/_reports/formal_training_cohort_inventory_dry_run_20260620.md',
        terms: ['formal_training_cohort_inventory', 'formal cohort', '58 rows', 'multi-league'],
        projectStatusDelta:
            'Formal training remains blocked: 58 smoke/integration candidates, 0 formal candidates with odds, no model training authorization.',
    },
    {
        task: 'technical_debt_workflow_audit_dry_run',
        path: 'docs/_reports/technical_debt_workflow_audit_dry_run_20260620.md',
        terms: ['technical_debt_workflow_audit', 'EXTREMELY_HIGH', 'SC-002', 'cutoff time'],
        projectStatusDelta:
            'Technical debt audit blocks data expansion and formal training until P0 debt is handled.',
    },
    {
        task: 'p0_db_write_safety_gate_dry_run',
        path: 'docs/_reports/p0_db_write_safety_gate_dry_run_20260620.md',
        terms: ['p0_db_write_safety_gate', '122', 'ALLOW_DB_WRITE', 'SC-002'],
        projectStatusDelta:
            'P0 DB write gate is audit-only: 122 production DB-write scripts detected, 66 P0, 110 with no gate.',
    },
];

function readText(repoRoot, relPath) {
    const absPath = path.join(repoRoot, relPath);
    if (!fs.existsSync(absPath)) return null;
    return fs.readFileSync(absPath, 'utf8');
}

function exists(repoRoot, relPath) {
    return fs.existsSync(path.join(repoRoot, relPath));
}

function listFiles(repoRoot, relDir, predicate = () => true) {
    const dir = path.join(repoRoot, relDir);
    if (!fs.existsSync(dir)) return [];
    return fs.readdirSync(dir, { withFileTypes: true })
        .filter(entry => entry.isFile())
        .map(entry => path.join(relDir, entry.name).replace(/\\/g, '/'))
        .filter(predicate)
        .sort();
}

function countLines(text) {
    if (!text) return 0;
    return text.split('\n').length;
}

function extractLifecycle(text) {
    if (!text) return null;
    const match = text.match(/lifecycle:\s*([^\n]+)/i);
    return match ? match[1].trim() : null;
}

function extractLastUpdated(text) {
    if (!text) return null;
    const match = text.match(/Last updated:\s*(\d{4}-\d{2}-\d{2})/i);
    return match ? match[1] : null;
}

function dateFromReportPath(reportPath) {
    const match = reportPath.match(/(?:_|-)(20\d{6})(?:\.|_|-)/);
    if (!match) return null;
    const raw = match[1];
    return `${raw.slice(0, 4)}-${raw.slice(4, 6)}-${raw.slice(6, 8)}`;
}

function containsAny(text, terms) {
    const lower = String(text || '').toLowerCase();
    return terms.some(term => lower.includes(String(term).toLowerCase()));
}

function buildAuthoritativeDocs(repoRoot) {
    return AUTHORITATIVE_CANDIDATES
        .filter(doc => exists(repoRoot, doc.path))
        .map(doc => {
            const text = readText(repoRoot, doc.path) || '';
            return {
                path: doc.path,
                role: doc.role,
                recommended_authoritative_entrypoint: doc.recommended,
                lifecycle: extractLifecycle(text),
                line_count: countLines(text),
                last_updated: extractLastUpdated(text),
            };
        });
}

function buildMissingAuthoritativeDocs(repoRoot) {
    const missingRequired = REQUIRED_AUTH_DOCS
        .filter(relPath => !exists(repoRoot, relPath))
        .map(relPath => ({ path: relPath, severity: 'P0', reason: 'required authoritative workflow doc missing' }));
    const missingPlanned = PLANNED_DOCS_FROM_GOVERNANCE
        .filter(relPath => !exists(repoRoot, relPath))
        .map(relPath => ({ path: relPath, severity: 'P2', reason: 'planned/mentioned source-of-truth doc is absent' }));
    return [...missingRequired, ...missingPlanned];
}

function buildReportsInventory(repoRoot) {
    const reportFiles = listFiles(repoRoot, 'docs/_reports', file => file.endsWith('.md'));
    const manifestFiles = listFiles(repoRoot, 'docs/_manifests', file => file.endsWith('.json'));
    const totalReportLines = reportFiles.reduce((sum, file) => {
        const text = readText(repoRoot, file) || '';
        return sum + countLines(text);
    }, 0);
    return {
        reports_count: reportFiles.length,
        manifests_count: manifestFiles.length,
        reports_total_lines: totalReportLines,
        overgrown: reportFiles.length > 120 || totalReportLines > 12000,
        overgrown_reason: reportFiles.length > 120
            ? 'docs/_reports exceeds 120-file governance budget signal'
            : null,
        report_files: reportFiles,
        manifest_files: manifestFiles,
    };
}

function buildReportsWithoutBacklink(repoRoot, reportFiles) {
    return reportFiles.filter(file => {
        const text = readText(repoRoot, file) || '';
        return !REPORT_BACKLINK_TARGETS.some(target => text.includes(target));
    });
}

function parseClaimedCount(text, label) {
    const regex = new RegExp(`${label}[^\\n]*contains\\s+(\\d+)`, 'i');
    const match = String(text || '').match(regex);
    return match ? Number.parseInt(match[1], 10) : null;
}

function latestRecentReportDate() {
    return RECENT_REPORTS
        .map(report => dateFromReportPath(report.path))
        .filter(Boolean)
        .sort()
        .pop();
}

function addProjectStatusStaleness(stale, projectStatus, inventory) {
    const newestRecentDate = latestRecentReportDate();
    const projectLastUpdated = extractLastUpdated(projectStatus);
    if (projectLastUpdated && newestRecentDate && projectLastUpdated < newestRecentDate) {
        stale.push({
            path: 'docs/PROJECT_STATUS.md',
            severity: 'P0',
            reason: `last updated ${projectLastUpdated}, but recent governance/data dry-runs exist on ${newestRecentDate}`,
        });
    }

    const claimedReports = parseClaimedCount(projectStatus, 'docs/_reports/');
    if (claimedReports !== null && claimedReports !== inventory.reports_count) {
        stale.push({
            path: 'docs/PROJECT_STATUS.md',
            severity: 'P2',
            reason: `reports count claims ${claimedReports}, actual ${inventory.reports_count}`,
        });
    }

    const claimedManifests = parseClaimedCount(projectStatus, 'docs/_manifests/');
    if (claimedManifests !== null && claimedManifests !== inventory.manifests_count) {
        stale.push({
            path: 'docs/PROJECT_STATUS.md',
            severity: 'P2',
            reason: `manifests count claims ${claimedManifests}, actual ${inventory.manifests_count}`,
        });
    }
}

function addPlannedStatusDrift(stale, repoRoot, file, text) {
    for (const existingDoc of ['docs/PROJECT_STATUS.md', 'docs/DATA_SOURCE_STRATEGY.md']) {
        if (exists(repoRoot, existingDoc) && text.includes(`${existingDoc} | planned`)) {
            stale.push({
                path: file,
                severity: 'P1',
                reason: `${existingDoc} exists but is still listed as planned`,
            });
        }
    }
}

function addOverviewDocDrift(stale, changelog, readme) {
    if (!containsAny(changelog, ['2026-06-20', 'workflow', 'governance', 'P0 DB write'])) {
        stale.push({
            path: 'docs/CHANGELOG.md',
            severity: 'P2',
            reason: 'changelog does not reflect June 2026 workflow/governance dry-run conclusions',
        });
    }

    if (readme.includes('Production-Ready') && !readme.includes('docs/PROJECT_STATUS.md')) {
        stale.push({
            path: 'README.md',
            severity: 'P2',
            reason: 'README still signals Production-Ready but does not point readers to PROJECT_STATUS current blockers',
        });
    }
}

function buildStaleAuthoritativeDocs(repoRoot, inventory) {
    const stale = [];
    const projectStatus = readText(repoRoot, 'docs/PROJECT_STATUS.md') || '';
    const docGov = readText(repoRoot, 'docs/DOCUMENTATION_GOVERNANCE.md') || '';
    const codexWorkflow = readText(repoRoot, 'docs/CODEX_WORKFLOW.md') || '';
    const changelog = readText(repoRoot, 'docs/CHANGELOG.md') || '';
    const readme = readText(repoRoot, 'README.md') || '';

    addProjectStatusStaleness(stale, projectStatus, inventory);
    addPlannedStatusDrift(stale, repoRoot, 'docs/DOCUMENTATION_GOVERNANCE.md', docGov);
    addPlannedStatusDrift(stale, repoRoot, 'docs/CODEX_WORKFLOW.md', codexWorkflow);
    addOverviewDocDrift(stale, changelog, readme);

    return stale;
}

function buildRecentReportReflection(repoRoot) {
    const projectStatus = readText(repoRoot, 'docs/PROJECT_STATUS.md') || '';
    return RECENT_REPORTS.map(report => {
        const reportText = readText(repoRoot, report.path) || '';
        const existsFlag = Boolean(reportText);
        const reflected = existsFlag && containsAny(projectStatus, report.terms);
        return {
            task: report.task,
            report_path: report.path,
            report_exists: existsFlag,
            reflected_in_project_status: reflected,
            needs_project_status_delta: existsFlag && !reflected,
            required_project_status_summary: report.projectStatusDelta,
        };
    });
}

function hasPrTemplateDocChecklist(templateText) {
    return /Source-of-truth docs updated/i.test(templateText) ||
        /authoritative docs updated/i.test(templateText) ||
        /权威文档/.test(templateText);
}

function buildAiWorkflowRuleGaps(repoRoot) {
    const gaps = [];
    const codex = readText(repoRoot, 'docs/CODEX_WORKFLOW.md') || '';
    const docGov = readText(repoRoot, 'docs/DOCUMENTATION_GOVERNANCE.md') || '';
    const agents = readText(repoRoot, 'AGENTS.md') || '';
    const claude = readText(repoRoot, 'CLAUDE.md') || '';
    const combined = [codex, docGov, agents, claude].join('\n');

    if (!containsAny(combined, ['Read current source-of-truth docs', '权威文档', 'source-of-truth docs first'])) {
        gaps.push({ severity: 'P0', gap: 'AI agents are not clearly required to read source-of-truth docs first' });
    }
    if (!containsAny(combined, ['Never develop directly on `main`', '不在 `main` 分支直接开发'])) {
        gaps.push({ severity: 'P0', gap: 'main branch direct-work prohibition is missing' });
    }
    if (!containsAny(combined, ['DB write', 'DB writes', '写库', 'raw write', 'training'])) {
        gaps.push({ severity: 'P0', gap: 'high-risk no-write/no-training rules are missing' });
    }
    if (!containsAny(codex, ['skip source-of-truth updates while adding more reports']) ||
        !containsAny(docGov, ['First update main docs'])) {
        gaps.push({ severity: 'P0', gap: 'workflow docs do not prohibit reports without source-of-truth update' });
    }
    if (!/completion|完成标准|Final Report/i.test(codex) ||
        !/source-of-truth docs updated|Current-state doc updated|权威文档更新/.test(codex)) {
        gaps.push({
            severity: 'P1',
            gap: 'CODEX_WORKFLOW has final report guidance but no explicit completion standard requiring source-of-truth update or justified no-update',
        });
    }
    if (!containsAny(combined, ['报告结论回流', 'source-of-truth summary', 'summarized or linked from a source-of-truth doc'])) {
        gaps.push({ severity: 'P1', gap: 'report conclusions are not hard-required to flow back into authoritative docs before completion' });
    }

    return gaps;
}

function buildPrTemplateGaps(repoRoot) {
    const template = readText(repoRoot, '.github/pull_request_template.md') || '';
    const uppercaseTemplateExists = exists(repoRoot, '.github/PULL_REQUEST_TEMPLATE.md');
    const gaps = [];

    if (!template.includes('## Files Changed')) {
        gaps.push({ severity: 'P1', gap: 'active PR template does not require changed files declaration' });
    }
    if (!hasPrTemplateDocChecklist(template)) {
        gaps.push({ severity: 'P0', gap: 'active PR template does not require explicit authoritative/source-of-truth doc update status' });
    }
    if (!/Reports added/.test(template)) {
        gaps.push({ severity: 'P1', gap: 'active PR template does not require reports-added declaration' });
    }
    if (!/Current-state doc updated/.test(template)) {
        gaps.push({ severity: 'P1', gap: 'active PR template only asks current-state doc update in debt section, not Documentation Impact gate' });
    }
    if (!/Reason for new docs|reason.*report|why.*report/i.test(template)) {
        gaps.push({ severity: 'P1', gap: 'active PR template does not require justification when docs/_reports is added without source-of-truth update' });
    }
    if (uppercaseTemplateExists) {
        gaps.push({ severity: 'P2', gap: 'legacy .github/PULL_REQUEST_TEMPLATE.md exists and can confuse reviewers despite lowercase template being active' });
    }

    return gaps;
}

function buildGatekeeperGaps(repoRoot) {
    const aiGate = readText(repoRoot, 'scripts/ops/ai_workflow_gate.py') || '';
    const gatekeeper = readText(repoRoot, 'scripts/devops/gatekeeper.sh') || '';
    const workflow = readText(repoRoot, '.github/workflows/production-gate.yml') || '';
    const docGovChecker = readText(repoRoot, 'scripts/ops/documentation_governance_check.py') || '';
    const gaps = [];

    if (!aiGate.includes('check_doc_sprawl')) {
        gaps.push({ severity: 'P0', gap: 'AI Workflow Gate lacks docs/_reports/doc-sprawl check' });
    }
    if (!/Source-of-truth docs updated|authoritative.*updated|PROJECT_STATUS/.test(aiGate)) {
        gaps.push({ severity: 'P0', gap: 'AI Workflow Gate does not block report-only PRs that skip PROJECT_STATUS or other authoritative docs' });
    }
    if (!/documentation_governance_check/.test(workflow) && !/documentation_governance_check/.test(gatekeeper)) {
        gaps.push({ severity: 'P1', gap: 'documentation_governance_check.py exists but is not wired into Production Gate/gatekeeper as a general PR check' });
    }
    if (docGovChecker.includes('ALLOWED_ADDED') && !docGovChecker.includes('source-of-truth')) {
        gaps.push({ severity: 'P1', gap: 'documentation_governance_check focuses on allowlists/budgets, not report conclusion backflow' });
    }
    if (aiGate.includes('MAX_DOC_SPRAWL_NEW_FILES = 5')) {
        gaps.push({ severity: 'P1', gap: 'doc sprawl gate allows up to 5 report/manifest files and does not require authoritative-doc linkage' });
    }
    if (workflow.includes('--skip-body-checks')) {
        gaps.push({ severity: 'P1', gap: 'push events skip PR body governance checks; branch protection must compensate' });
    }

    return gaps;
}

function groupBySeverity(items) {
    return {
        P0: items.filter(item => item.severity === 'P0'),
        P1: items.filter(item => item.severity === 'P1'),
        P2: items.filter(item => item.severity === 'P2'),
    };
}

function buildRecommendedSteps(context) {
    return {
        P0: [
            'Modify PR template to require authoritative/source-of-truth doc update status and report-backflow justification.',
            'Add AI Workflow Gate check: if docs/_reports/*.md is added, require PROJECT_STATUS/DOCUMENTATION_GOVERNANCE/CODEX_WORKFLOW/DATA_SOURCE_STRATEGY/FOTMOB_CURRENT_STATE update or an explicit no-update justification.',
            'Backfill recent dry-run conclusions into PROJECT_STATUS.md after user-approved fix phase.',
        ],
        P1: [
            'Update DOCUMENTATION_GOVERNANCE.md to make report conclusion backflow a hard PR completion rule.',
            'Update CODEX_WORKFLOW.md final completion criteria: no new report without authoritative-doc update or explicit reviewer-visible reason.',
            'Wire documentation_governance_check.py or a new focused source-of-truth backflow check into Production Gate.',
        ],
        P2: [
            'Clarify active PR template by deprecating the uppercase legacy template in a later cleanup phase.',
            'Add report backlink cleanup policy for historical reports without changing history in this dry run.',
            'Align README and CHANGELOG with current status docs in separate scoped documentation cleanup.',
        ],
        fix_phase1_minimal_scope: [
            '.github/pull_request_template.md',
            'scripts/ops/ai_workflow_gate.py',
            'tests/unit/test_ai_workflow_gate.py',
            'docs/DOCUMENTATION_GOVERNANCE.md',
            'docs/CODEX_WORKFLOW.md',
            'docs/PROJECT_STATUS.md',
        ],
        should_enter_fix_phase1: context.p0Count > 0,
    };
}

function buildAnswers(context) {
    return {
        project_has_authoritative_docs: true,
        current_authoritative_entrypoints: [
            'docs/PROJECT_STATUS.md',
            'docs/DOCUMENTATION_GOVERNANCE.md',
            'docs/CODEX_WORKFLOW.md',
            'docs/AGENT_WORKFLOW.md',
            '.github/pull_request_template.md',
            'AGENTS.md',
            'CLAUDE.md',
            'docs/DATA_SOURCE_STRATEGY.md',
            'docs/data/FOTMOB_CURRENT_STATE.md',
        ],
        stale_or_unmaintained_docs: context.staleDocs.map(item => item.path),
        reports_overgrown: context.inventory.overgrown,
        recent_three_reports_reflected: context.recentReflection.every(item => item.reflected_in_project_status),
        ai_agent_required_to_maintain_authoritative_docs: context.aiGaps.length === 0,
        pr_template_forces_authoritative_doc_update_status: context.prGaps.every(item => item.severity !== 'P0'),
        gatekeeper_blocks_report_without_authoritative_update: context.gatekeeperGaps.every(item => item.severity !== 'P0'),
        should_add_ci_check: true,
        should_modify_pr_template: true,
        should_modify_codex_workflow: true,
        should_modify_documentation_governance: true,
        should_enter_authoritative_workflow_enforcement_fix_phase1: context.p0Count > 0,
    };
}

function buildAudit(repoRoot = REPO_ROOT) {
    const inventory = buildReportsInventory(repoRoot);
    const authoritativeDocs = buildAuthoritativeDocs(repoRoot);
    const staleDocs = buildStaleAuthoritativeDocs(repoRoot, inventory);
    const reportsWithoutBacklink = buildReportsWithoutBacklink(repoRoot, inventory.report_files);
    const recentReflection = buildRecentReportReflection(repoRoot);
    const aiGaps = buildAiWorkflowRuleGaps(repoRoot);
    const prGaps = buildPrTemplateGaps(repoRoot);
    const gatekeeperGaps = buildGatekeeperGaps(repoRoot);
    const severityItems = [
        ...staleDocs,
        ...aiGaps,
        ...prGaps,
        ...gatekeeperGaps,
        ...recentReflection
            .filter(item => item.needs_project_status_delta)
            .map(item => ({ severity: 'P0', gap: `${item.task} conclusion not reflected in PROJECT_STATUS.md` })),
    ];
    const grouped = groupBySeverity(severityItems);
    const context = {
        inventory,
        staleDocs,
        recentReflection,
        aiGaps,
        prGaps,
        gatekeeperGaps,
        p0Count: grouped.P0.length,
    };

    return {
        phase: PHASE,
        generated_at: new Date().toISOString(),
        safety: {
            static_scan_only: true,
            network_used: false,
            db_connected: false,
            scanned_scripts_executed: false,
            writes_performed: false,
            training_performed: false,
            model_files_generated: false,
        },
        authoritative_docs_found: authoritativeDocs,
        missing_authoritative_docs: buildMissingAuthoritativeDocs(repoRoot),
        stale_authoritative_docs: staleDocs,
        reports_inventory: {
            reports_count: inventory.reports_count,
            manifests_count: inventory.manifests_count,
            reports_total_lines: inventory.reports_total_lines,
            overgrown: inventory.overgrown,
            overgrown_reason: inventory.overgrown_reason,
        },
        reports_without_status_backlink: {
            count: reportsWithoutBacklink.length,
            paths: reportsWithoutBacklink,
        },
        reports_not_reflected_in_project_status: recentReflection.filter(item => item.needs_project_status_delta),
        recent_task_reflection: recentReflection,
        ai_workflow_rule_gaps: aiGaps,
        pr_template_gaps: prGaps,
        gatekeeper_gaps: gatekeeperGaps,
        severity_summary: {
            P0: grouped.P0.length,
            P1: grouped.P1.length,
            P2: grouped.P2.length,
        },
        recommended_authoritative_entrypoints: authoritativeDocs
            .filter(doc => doc.recommended_authoritative_entrypoint)
            .map(doc => doc.path),
        docs_not_recommended_to_create: [
            'PROJECT_STATUS_V2.md',
            'NEW_WORKFLOW.md',
            'NEW_RULES.md',
            'docs/AUTHORITATIVE_WORKFLOW_V2.md',
        ],
        recommended_enforcement_steps: buildRecommendedSteps(context),
        required_backflow: {
            project_status: recentReflection
                .filter(item => item.needs_project_status_delta)
                .map(item => item.required_project_status_summary),
            documentation_governance: [
                'A report that changes active project state must update or explicitly justify not updating a source-of-truth doc in the same PR.',
                'docs/_reports entries are evidence, not durable current truth.',
            ],
            codex_workflow: [
                'Task completion requires source-of-truth update status in the PR body.',
                'Adding docs/_reports without PROJECT_STATUS/DOCUMENTATION_GOVERNANCE/CODEX_WORKFLOW backflow is a No-Go unless explicitly justified.',
            ],
            ci_gatekeeper: [
                'Detect added docs/_reports/*.md.',
                'Require touched authoritative docs or explicit PR body justification.',
                'Fail hollow Documentation Impact answers.',
            ],
        },
        answers: buildAnswers(context),
    };
}

function formatSummary(audit) {
    const lines = [
        `Phase: ${audit.phase}`,
        `Safety: static_scan_only=${audit.safety.static_scan_only} network=${audit.safety.network_used} db=${audit.safety.db_connected} writes=${audit.safety.writes_performed}`,
        '',
        'Authoritative docs found:',
        ...audit.authoritative_docs_found.map(doc => `- ${doc.path} (${doc.role})`),
        '',
        `docs/_reports: ${audit.reports_inventory.reports_count} files, ${audit.reports_inventory.reports_total_lines} lines, overgrown=${audit.reports_inventory.overgrown}`,
        `reports_without_status_backlink: ${audit.reports_without_status_backlink.count}`,
        '',
        'Recent report reflection in PROJECT_STATUS.md:',
        ...audit.recent_task_reflection.map(item => `- ${item.task}: reflected=${item.reflected_in_project_status}`),
        '',
        `Severity summary: P0=${audit.severity_summary.P0} P1=${audit.severity_summary.P1} P2=${audit.severity_summary.P2}`,
        `Recommend fix_phase1: ${audit.answers.should_enter_authoritative_workflow_enforcement_fix_phase1 ? 'yes' : 'no'}`,
        '',
        'P0 enforcement steps:',
        ...audit.recommended_enforcement_steps.P0.map(step => `- ${step}`),
    ];
    return `${lines.join('\n')}\n`;
}

function parseArgs(argv = process.argv.slice(2)) {
    const options = { json: false, help: false };
    for (const arg of argv) {
        if (arg === '--json') options.json = true;
        else if (arg === '--help' || arg === '-h') options.help = true;
        else throw new Error(`Unknown argument: ${arg}`);
    }
    return options;
}

function usage() {
    return [
        'Usage:',
        '  node scripts/ops/authoritative_workflow_enforcement_dry_run.js',
        '  node scripts/ops/authoritative_workflow_enforcement_dry_run.js --json',
        '',
        'Safety:',
        '  Static file scan only. No network, no DB connection, no script execution, no training, no writes.',
    ].join('\n');
}

function main(argv = process.argv.slice(2)) {
    const options = parseArgs(argv);
    if (options.help) {
        process.stdout.write(`${usage()}\n`);
        return 0;
    }
    const audit = buildAudit();
    process.stdout.write(options.json ? `${JSON.stringify(audit, null, 2)}\n` : formatSummary(audit));
    return 0;
}

module.exports = {
    PHASE,
    AUTHORITATIVE_CANDIDATES,
    REQUIRED_AUTH_DOCS,
    RECENT_REPORTS,
    REPORT_BACKLINK_TARGETS,
    buildAudit,
    buildAuthoritativeDocs,
    buildMissingAuthoritativeDocs,
    buildReportsInventory,
    buildReportsWithoutBacklink,
    buildRecentReportReflection,
    buildStaleAuthoritativeDocs,
    buildAiWorkflowRuleGaps,
    buildPrTemplateGaps,
    buildGatekeeperGaps,
    hasPrTemplateDocChecklist,
    formatSummary,
    parseArgs,
    usage,
    main,
};

if (require.main === module) {
    try {
        process.exitCode = main();
    } catch (error) {
        process.stderr.write(`${error.message}\n`);
        process.exitCode = 1;
    }
}
