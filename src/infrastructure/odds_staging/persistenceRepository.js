'use strict';

// lifecycle: permanent；Historical odds staging 的显式 DI persistence port，默认拒绝任何写入。

const { assertDbWriteAllowed } = require('../../../scripts/ops/helpers/db_write_guard');
const { buildPersistencePlan, PersistenceContractError } = require('./persistenceContracts');

const TARGET_TABLES = Object.freeze([
    'odds_historical_import_runs',
    'odds_historical_source_files',
    'odds_historical_staging_observations',
    'odds_historical_quarantine',
]);

class PersistenceWriteDisabledError extends Error {
    constructor(message) {
        super(message);
        this.name = 'PersistenceWriteDisabledError';
        this.code = 'PERSISTENCE_WRITE_DISABLED';
    }
}

class PersistenceConflictError extends Error {
    constructor(message) {
        super(message);
        this.name = 'PersistenceConflictError';
        this.code = 'PERSISTENCE_CONFLICT';
    }
}

function createGuardedWriteAdapter(adapter, guard = assertDbWriteAllowed) {
    if (!adapter || typeof adapter.runInTransaction !== 'function') {
        throw new PersistenceContractError('write adapter must implement runInTransaction');
    }
    return {
        ...adapter,
        async runInTransaction(callback) {
            guard({
                script: 'odds_historical_staging_persistence',
                tables: TARGET_TABLES,
                operations: ['INSERT', 'UPDATE'],
            });
            return adapter.runInTransaction(callback);
        },
    };
}

class HistoricalOddsStagingPersistenceRepository {
    constructor({ adapter = null, guard = assertDbWriteAllowed } = {}) {
        this.adapter = adapter ? createGuardedWriteAdapter(adapter, guard) : null;
    }

    plan(result, context = {}) {
        return buildPersistencePlan(result, context);
    }

    async execute(plan, { mode = 'dry_run' } = {}) {
        if (mode === 'dry_run') {
            return { status: 'not_persisted', reason: 'dry_run', run_key: plan.run.run_key };
        }
        if (mode !== 'write_authorized' || !this.adapter) {
            throw new PersistenceWriteDisabledError(
                'historical odds persistence is disabled without an explicit guarded adapter and write_authorized mode'
            );
        }
        try {
            return await this.adapter.runInTransaction(async operations => {
                const existing = await operations.findAcceptedByIdempotencyKey(plan.accepted.map(row => row.idempotency_key));
                const known = new Map((existing || []).map(row => [row.idempotency_key, row]));
                const newAccepted = [];
                let duplicateCount = 0;
                for (const row of plan.accepted) {
                    const prior = known.get(row.idempotency_key);
                    if (!prior) newAccepted.push(row);
                    else if (prior.business_fingerprint === row.business_fingerprint) duplicateCount += 1;
                    else throw new PersistenceConflictError(`divergent idempotency conflict: ${row.idempotency_key}`);
                }
                await operations.createImportRun(plan.run);
                await operations.registerSourceFile(plan.source_file);
                if (newAccepted.length) await operations.insertAcceptedObservations(newAccepted);
                if (plan.quarantine.length) await operations.insertQuarantineRecords(plan.quarantine);
                const result = {
                    status: 'persisted',
                    accepted_count: newAccepted.length,
                    quarantine_count: plan.quarantine.length,
                    duplicate_count: duplicateCount,
                };
                await operations.markRunCompleted(plan.run.run_key, result);
                return result;
            });
        } catch (error) {
            // Adapter may record failure in an independent, explicitly guarded audit transaction; never hide the original error.
            if (typeof this.adapter.recordRunFailure === 'function') {
                try {
                    await this.adapter.recordRunFailure(plan.run.run_key, error.message);
                } catch {
                    // The original transaction error remains authoritative.
                }
            }
            throw error;
        }
    }
}

module.exports = {
    HistoricalOddsStagingPersistenceRepository,
    PersistenceConflictError,
    PersistenceWriteDisabledError,
    TARGET_TABLES,
    createGuardedWriteAdapter,
};
