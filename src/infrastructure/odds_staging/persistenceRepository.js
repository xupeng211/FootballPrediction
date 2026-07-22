'use strict';

// lifecycle: permanent；Historical odds staging 的显式 DI persistence port，默认拒绝任何写入。

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

function createAuthorizedWriteAdapter(adapter, authorizeWrite) {
    if (!adapter || typeof adapter.runInTransaction !== 'function') {
        throw new PersistenceContractError('write adapter must implement runInTransaction');
    }
    if (typeof authorizeWrite !== 'function') {
        throw new PersistenceWriteDisabledError('write adapter requires an explicit authorizeWrite dependency');
    }
    return {
        ...adapter,
        async runInTransaction(callback) {
            await authorizeWrite({ tables: TARGET_TABLES, operations: ['INSERT', 'UPDATE'] });
            return adapter.runInTransaction(callback);
        },
    };
}

class HistoricalOddsStagingPersistenceRepository {
    constructor({ adapter = null, authorizeWrite = null } = {}) {
        this.adapter = adapter && authorizeWrite ? createAuthorizedWriteAdapter(adapter, authorizeWrite) : null;
        this.hasAdapter = Boolean(adapter);
        this.hasAuthorizer = typeof authorizeWrite === 'function';
    }

    plan(result, context = {}) {
        return buildPersistencePlan(result, context);
    }

    async execute(plan, { authorization = 'not_authorized' } = {}) {
        if (plan?.run?.mode === 'dry_run' && authorization === 'not_authorized') {
            return { status: 'not_persisted', reason: 'dry_run', run_key: plan.run.run_key };
        }
        if (plan?.run?.mode !== 'controlled_write' || authorization !== 'write_authorized') {
            throw new PersistenceWriteDisabledError(
                'persistence requires a controlled_write plan and explicit write_authorized execution'
            );
        }
        if (!this.hasAdapter || !this.hasAuthorizer || !this.adapter) {
            throw new PersistenceWriteDisabledError('controlled_write requires an explicit adapter and authorizeWrite dependency');
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
            // No out-of-band failure write: D4C must prove atomic failure-state handling inside the authorized transaction.
            throw error;
        }
    }
}

module.exports = {
    HistoricalOddsStagingPersistenceRepository,
    PersistenceConflictError,
    PersistenceWriteDisabledError,
    TARGET_TABLES,
    createAuthorizedWriteAdapter,
};
