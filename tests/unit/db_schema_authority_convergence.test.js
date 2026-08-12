/**
 * PR-A4 DB schema authority convergence static contract tests.
 *
 * lifecycle: permanent
 * scope: machine-readable authority, startup contracts, and no-DB regression proof
 * These tests never import a DB client, connect to a DB, or execute SQL/migrations.
 */

'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const { execFileSync } = require('node:child_process');
const fs = require('node:fs');
const path = require('node:path');

const REPO_ROOT = path.resolve(__dirname, '../..');

function read(relativePath) {
    return fs.readFileSync(path.join(REPO_ROOT, relativePath), 'utf8');
}

function readJson(relativePath) {
    return JSON.parse(read(relativePath));
}

function surfaceByPath(policy, pathValue) {
    return policy.runtime_schema_mutation_policy.surfaces.find(surface => surface.path === pathValue);
}

function listFiles(relativePath) {
    const absolutePath = path.join(REPO_ROOT, relativePath);
    return fs.readdirSync(absolutePath, { withFileTypes: true }).flatMap(entry => {
        const childPath = path.join(relativePath, entry.name);
        return entry.isDirectory() ? listFiles(childPath) : [childPath];
    });
}

function changedPaths() {
    const outputs = [];
    for (const args of [
        ['diff', '--name-only', 'origin/main...HEAD'],
        ['diff', '--name-only'],
        ['diff', '--cached', '--name-only'],
    ]) {
        try {
            outputs.push(
                execFileSync('git', ['-c', `safe.directory=${REPO_ROOT}`, ...args], {
                    cwd: REPO_ROOT,
                    encoding: 'utf8',
                })
            );
        } catch {
            // A shallow/local checkout may not have origin/main; other views still prove the guard.
        }
    }

    try {
        const status = execFileSync('git', ['-c', `safe.directory=${REPO_ROOT}`, 'status', '--porcelain=v1', '-uall'], {
            cwd: REPO_ROOT,
            encoding: 'utf8',
        });
        outputs.push(
            status
                .split('\n')
                .filter(Boolean)
                .map(line => line.slice(3))
                .join('\n')
        );
    } catch {
        // The test still retains the committed-diff checks if status is unavailable.
    }

    return [...new Set(outputs.flatMap(output => output.split('\n').filter(Boolean)))];
}

test('A4 policy names exactly one forward schema evolution authority', () => {
    const policy = readJson('config/db_schema_authority.json');

    assert.deepEqual(policy.forward_schema_evolution_authorities, ['database/migrations/']);
    assert.equal(policy.schema_definition_authority.path, 'database/migrations/');
    assert.equal(policy.schema_definition_authority.lifecycle, 'CANONICAL');
    assert.equal(policy.future_schema_change_location, 'database/migrations/');
    assert.equal(policy.execution_requires_explicit_authorization, true);
    assert.equal(policy.automatic_application_on_default_startup, false);
});

test('A4 policy classifies both migration trees and freezes Alembic future revisions', () => {
    const policy = readJson('config/db_schema_authority.json');
    const trees = Object.fromEntries(policy.migration_trees.map(tree => [tree.path, tree]));

    assert.equal(trees['database/migrations/'].lifecycle, 'CANONICAL');
    assert.equal(trees['database/migrations/'].future_schema_changes_allowed, true);
    assert.equal(trees['src/database/migrations/'].lifecycle, 'LEGACY');
    assert.equal(trees['src/database/migrations/'].future_schema_changes_allowed, false);
    assert.equal(trees['src/database/migrations/'].automatic_execution, false);
    assert.equal(trees['src/database/migrations/'].freeze_policy, 'frozen; no future Alembic revisions');
    assert.equal(policy.migration_content_policy.future_alembic_revisions_allowed, false);
});

test('A4 changes no migration content or Docker bootstrap SQL', () => {
    const protectedChanges = changedPaths().filter(
        filePath =>
            filePath.startsWith('database/migrations/') ||
            filePath.startsWith('src/database/migrations/versions/') ||
            filePath === 'deploy/docker/init_db.sql'
    );

    assert.deepEqual(protectedChanges, []);
});

test('A4 authority decision matches the current contract chronology', () => {
    const rawMigrationFiles = listFiles('database/migrations').filter(file => file.endsWith('.sql'));
    const alembicRevisionFiles = listFiles('src/database/migrations/versions').filter(file => file.endsWith('.py'));

    assert.ok(rawMigrationFiles.includes('database/migrations/V26.10__create_m3_canonical_inventory_contract.sql'));
    assert.equal(rawMigrationFiles.length, 16);
    assert.equal(alembicRevisionFiles.length, 3);
    assert.ok(alembicRevisionFiles.includes('src/database/migrations/versions/003_v145_l2_data_version.py'));
});

test('A4 startup helpers cannot run legacy Alembic or fail open after migration failure', () => {
    const policy = readJson('config/db_schema_authority.json');

    for (const helper of policy.startup_helpers) {
        const source = read(helper.path);
        assert.doesNotMatch(source, /alembic\s+(upgrade|downgrade)/i, helper.path);
        assert.doesNotMatch(source, /python\s+-m\s+alembic/i, helper.path);
        assert.equal(helper.implicit_migration, false, helper.path);
    }

    assert.doesNotMatch(read('docker/entrypoint.sh'), /run_database_migrations/);
    assert.doesNotMatch(read('docker/simple_entrypoint.sh'), /run_database_migrations/);
    assert.match(read('docker/entrypoint_production.sh'), /information_schema\.tables/);
    assert.doesNotMatch(read('docker/entrypoint_production.sh'), /CREATE\s+TABLE|ALTER\s+TABLE/i);
});

test('A4 disables SchemaManager mutation entrypoints while retaining the module', () => {
    const policy = readJson('config/db_schema_authority.json');
    const source = read('src/database/schema_manager.py');
    const schemaManager = surfaceByPath(policy, 'src/database/schema_manager.py');

    assert.equal(schemaManager.lifecycle, 'LEGACY_NON_CANONICAL_RUNTIME_DDL');
    assert.equal(schemaManager.mutation_entrypoints_disabled, true);
    assert.equal(schemaManager.read_only_methods_retained, true);

    const initializeStart = source.indexOf('def initialize_schema');
    const productionStart = source.indexOf('def initialize_production_schema');
    const firstConnection = source.indexOf('self.get_connection()', initializeStart);
    assert.ok(initializeStart >= 0);
    assert.ok(productionStart > initializeStart);
    assert.ok(source.indexOf('raise RuntimeError', initializeStart) < firstConnection);
    assert.match(source.slice(productionStart, productionStart + 500), /raise RuntimeError/);
    const supportedSourceFiles = [...listFiles('src'), ...listFiles('scripts/ops'), ...listFiles('docker')].filter(
        file => /\.(js|py|sh)$/.test(file) && file !== 'src/database/schema_manager.py'
    );
    for (const file of supportedSourceFiles) {
        assert.doesNotMatch(read(file), /\b(?:initialize_schema|initialize_production_schema)\s*\(/, file);
    }
});

test('A4 turns L3 schema setup into a read-only precondition', () => {
    const policy = readJson('config/db_schema_authority.json');
    const source = read('scripts/ops/l3_stitch_pipeline.js');
    const l3 = surfaceByPath(policy, 'scripts/ops/l3_stitch_pipeline.js');

    assert.equal(l3.schema_mutation_entrypoint, 'disabled');
    assert.doesNotMatch(source, /CREATE\s+TABLE|CREATE\s+INDEX/i);
    assert.match(source, /to_regclass\('public\.l3_features'\)/);
    assert.match(source, /database\/migrations\/V26\.4__create_l3_features_table\.sql/);
    assert.match(source, /operations:\s*\['UPDATE'\]/);
});

test('A4 keeps init_db.sql dev-only and out of unified/production-like Compose', () => {
    const policy = readJson('config/db_schema_authority.json');
    const initSurface = policy.bootstrap_surfaces.find(surface => surface.path === 'deploy/docker/init_db.sql');

    assert.equal(initSurface.lifecycle, 'DEV_BOOTSTRAP_NON_AUTHORITATIVE');
    assert.equal(initSurface.production_migration_authority, false);
    assert.equal(initSurface.staging_migration_authority, false);
    assert.match(read('deploy/docker/init_db.sql'), /DEV-ONLY/i);
    assert.match(read('deploy/docker/init_db.sql'), /Not for production/);
    assert.match(read('docker-compose.dev.yml'), /init_db\.sql:\/docker-entrypoint-initdb/);
    assert.doesNotMatch(read('docker-compose.yml'), /init_db\.sql:\/docker-entrypoint-initdb/);
});

test('A4 preserves separate execution authorization and SC-002 status', () => {
    const policy = readJson('config/db_schema_authority.json');
    const sqlPolicy = readJson('config/sql_migration_policy_allowlist.json');

    assert.equal(policy.sc002.sql_migration_allowlist_preserved, true);
    assert.equal(policy.sc002.python_db_write_guard_preserved, true);
    assert.equal(policy.sc002.alembic_runtime_guard_preserved, true);
    assert.equal(policy.sc002.execution_authorization_is_not_inferred_from_location, true);
    assert.equal(sqlPolicy._sql_execution_authorized, false);
    assert.match(sqlPolicy._sc002_status, /partial mitigation only/);
    assert.match(read('scripts/ops/helpers/python_db_write_guard.py'), /def assert_db_write_allowed/);
    assert.match(read('src/database/migrations/env.py'), /_check_alembic_migration_guard/);
});

test('A4 current-state docs answer the next-schema-change question deterministically', () => {
    const policy = readJson('config/db_schema_authority.json');
    const currentStateDocs = [
        'README.md',
        'docs/PROJECT_MAP.md',
        'docs/CAPABILITY_INDEX.md',
        'docs/ARCHITECTURE.md',
        'docs/operations/LOCAL_STAGING_SCHEMA_MIGRATION_PLAN.md',
    ];

    assert.equal(policy.future_schema_change_location, 'database/migrations/');
    for (const docPath of currentStateDocs) {
        const doc = read(docPath);
        assert.match(doc, /database\/migrations\//, docPath);
        assert.doesNotMatch(doc, /migration.*UNCLEAR|UNCLEAR.*migration/i, docPath);
    }
});
