'use strict';

const {
  assertFunctionDependency,
  assertObjectDependency
} = require('../../shared/helpers/reconMappingStoreShared');
const { ReconMappingQueries } = require('./ReconMappingQueries');
const { ReconMappingPersistence } = require('./ReconMappingPersistence');
const { ReconMismatchManager } = require('./ReconMismatchManager');

class ReconMappingStore {
  constructor(options = {}) {
    assertFunctionDependency('getDbPool', options.getDbPool);
    assertFunctionDependency('executeWithRetry', options.executeWithRetry);
    assertFunctionDependency('ensureSchema', options.ensureSchema);
    assertFunctionDependency('updateMatchPipelineStatusWithClient', options.updateMatchPipelineStatusWithClient);
    assertFunctionDependency('RepositoryError', options.RepositoryError);
    assertObjectDependency('arbiter', options.arbiter);
    assertFunctionDependency('arbiter.analyzeConflict', options.arbiter.analyzeConflict);

    const sharedOptions = {
      ...options,
      logger: options.logger || { info() {}, warn() {}, error() {} },
      reconConfig: options.reconConfig || {},
      sqlTemplates: options.sqlTemplates || {},
      traceId: options.traceId || null
    };

    this.queries = new ReconMappingQueries(sharedOptions);
    this.mismatchManager = new ReconMismatchManager({
      ...sharedOptions,
      queries: this.queries
    });
    this.persistence = new ReconMappingPersistence({
      ...sharedOptions,
      mismatchManager: this.mismatchManager,
      queries: this.queries
    });

    this.mismatchManager.attachPersistence(this.persistence);
  }

  async saveOddsPortalMapping(mappingData, options = {}) {
    return this.persistence.saveOddsPortalMapping(mappingData, options);
  }

  async batchSaveOddsPortalMappings(mappings, options = {}) {
    return this.persistence.batchSaveOddsPortalMappings(mappings, options);
  }

  async batchSaveMismatchEvidence(mismatchRecords, options = {}) {
    return this.mismatchManager.batchSaveMismatchEvidence(mismatchRecords, options);
  }

  async resolveHashConflict(conflict, options = {}) {
    return this.mismatchManager.resolveHashConflict(conflict, options);
  }
}

module.exports = { ReconMappingStore };
