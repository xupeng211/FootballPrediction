'use strict';

const ALLOWED_MAPPING_METHODS = [
  'exact',
  'fuzzy',
  'manual',
  'unknown',
  'exact_kickoff_tolerance',
  'home_date_fill',
  'hash_lock',
  'sequential_hash_rollover',
  'set_closure',
  'set_reconciliation',
  'recon_matrix',
  'protocol_extract',
  'dictionary',
  'season_mirror',
  'semantic',
  'V5.5_HARVESTER',
  'v41_186_auto'
];

function assertFunctionDependency(name, value) {
  if (typeof value !== 'function') {
    throw new TypeError(`[ReconSchemaJanitor] 缺少必需依赖: ${name}`);
  }
}

function assertObjectDependency(name, value) {
  if (!value || typeof value !== 'object') {
    throw new TypeError(`[ReconSchemaJanitor] 缺少必需依赖: ${name}`);
  }
}

class ReconSchemaJanitor {
  constructor(options = {}) {
    assertFunctionDependency('getDbPool', options.getDbPool);
    assertFunctionDependency('executeWithRetry', options.executeWithRetry);
    assertObjectDependency('mappingMigration', options.mappingMigration);
    assertFunctionDependency('mappingMigration.findDuplicateSeasonHashGroups', options.mappingMigration.findDuplicateSeasonHashGroups);
    assertFunctionDependency('mappingMigration.dedupeMappings', options.mappingMigration.dedupeMappings);
    assertFunctionDependency('mappingMigration.repairLinkedStatusesWithoutMapping', options.mappingMigration.repairLinkedStatusesWithoutMapping);
    assertFunctionDependency('RepositoryError', options.RepositoryError);

    this.getDbPool = options.getDbPool;
    this.executeWithRetry = options.executeWithRetry;
    this.mappingMigration = options.mappingMigration;
    this.logger = options.logger || { warn() {} };
    this.RepositoryError = options.RepositoryError;
    this.mappingSchemaEnsured = false;
    this.mappingHashUniquenessEnsured = false;
    this.leagueDictionarySchemaEnsured = false;
  }

  async ensureOddsPortalMappingSchema(options = {}) {
    const repairOrphanedLinkedStatuses = options.repairOrphanedLinkedStatuses !== false;

    if (this.mappingSchemaEnsured) {
      return;
    }

    await this.executeWithRetry(async () => {
      await this.getDbPool().query(`
        ALTER TABLE matches_oddsportal_mapping
        ADD COLUMN IF NOT EXISTS is_reversed BOOLEAN DEFAULT FALSE
      `);
      await this.getDbPool().query(`
        ALTER TABLE matches_oddsportal_mapping
        ADD COLUMN IF NOT EXISTS candidate_name VARCHAR(255)
      `);
      await this.getDbPool().query(`
        ALTER TABLE matches_oddsportal_mapping
        ADD COLUMN IF NOT EXISTS is_evidence_only BOOLEAN DEFAULT FALSE
      `);
      await this.getDbPool().query(`
        ALTER TABLE matches_oddsportal_mapping
        DROP CONSTRAINT IF EXISTS valid_method
      `);
      await this.getDbPool().query(`
        ALTER TABLE matches_oddsportal_mapping
        ADD CONSTRAINT valid_method CHECK (
          mapping_method::text = ANY (ARRAY[${ALLOWED_MAPPING_METHODS.map((method) => `'${method}'::text`).join(', ')}])
        )
      `);
    }, 'ensureOddsPortalMappingSchema');

    if (!this.leagueDictionarySchemaEnsured) {
      await this.ensureLeagueDictionarySchema();
    }

    if (!this.mappingHashUniquenessEnsured) {
      await this.ensureMappingHashUniquenessIndex();
    }

    if (repairOrphanedLinkedStatuses) {
      await this.repairOrphanedLinkedStatuses();
    }

    this.mappingSchemaEnsured = true;
  }

  async ensureLeagueDictionarySchema() {
    await this.executeWithRetry(async () => {
      await this.getDbPool().query(`
        CREATE TABLE IF NOT EXISTS recon_league_dictionary (
          id SERIAL PRIMARY KEY,
          league_id INTEGER NOT NULL,
          season VARCHAR(16) NOT NULL DEFAULT '',
          remote_name VARCHAR(255) NOT NULL,
          local_team_id VARCHAR(64) NOT NULL,
          created_at TIMESTAMP DEFAULT NOW(),
          updated_at TIMESTAMP DEFAULT NOW()
        )
      `);
      await this.getDbPool().query(`
        ALTER TABLE recon_league_dictionary
        ADD COLUMN IF NOT EXISTS season VARCHAR(16) NOT NULL DEFAULT ''
      `);
      await this.getDbPool().query(`
        DROP INDEX IF EXISTS idx_recon_league_dictionary_unique
      `);
      await this.getDbPool().query(`
        CREATE UNIQUE INDEX IF NOT EXISTS idx_recon_league_dictionary_unique
        ON recon_league_dictionary(league_id, season, remote_name)
      `);
      await this.getDbPool().query(`
        DROP INDEX IF EXISTS idx_recon_league_dictionary_team
      `);
      await this.getDbPool().query(`
        CREATE INDEX IF NOT EXISTS idx_recon_league_dictionary_team
        ON recon_league_dictionary(league_id, season, local_team_id)
      `);
    }, 'ensureLeagueDictionarySchema');

    this.leagueDictionarySchemaEnsured = true;
  }

  async ensureMappingHashUniquenessIndex() {
    const duplicateGroups = await this.executeWithRetry(
      () => this.mappingMigration.findDuplicateSeasonHashGroups(this.getDbPool()),
      'precheckMappingHashDuplicates'
    );

    if (duplicateGroups.length > 0) {
      await this.healMappingHashUniquenessConflicts('precheck', duplicateGroups);
    }

    try {
      await this.createMappingHashUniquenessIndex();
    } catch (error) {
      if (!(error instanceof this.RepositoryError) || error.code !== 'HASH_INDEX_DUPLICATES') {
        throw error;
      }

      const healResult = await this.healMappingHashUniquenessConflicts('create_index_conflict');
      if (healResult.deletedCount <= 0) {
        throw error;
      }

      await this.createMappingHashUniquenessIndex();
    }

    this.mappingHashUniquenessEnsured = true;
  }

  async createMappingHashUniquenessIndex() {
    await this.executeWithRetry(async () => {
      try {
        await this.getDbPool().query(`
          CREATE UNIQUE INDEX IF NOT EXISTS idx_mapping_season_hash_unique
          ON matches_oddsportal_mapping(season, oddsportal_hash)
        `);
      } catch (error) {
        if (this.isCreateIndexDuplicateConflict(error)) {
          throw new this.RepositoryError(
            '历史 season/hash 重复数据阻止唯一索引创建',
            'HASH_INDEX_DUPLICATES',
            error
          );
        }
        throw error;
      }
    }, 'ensureOddsPortalHashUniquenessIndex');
  }

  async healMappingHashUniquenessConflicts(reason, duplicateGroups = null) {
    const healResult = await this.executeWithRetry(
      () => this.mappingMigration.dedupeMappings({
        queryable: this.getDbPool(),
        logger: this.logger,
        groups: duplicateGroups
      }),
      'healMappingHashDuplicates'
    );

    if (healResult.deletedCount > 0) {
      this.logger.warn(
        `[HEAL] 检测到历史 Hash 冲突，自动清理了 ${healResult.deletedCount} 条脏数据以固化唯一索引`,
        {
          reason,
          duplicate_groups: healResult.groupCount,
          repaired_linked_count: healResult.repairedCount || 0,
          sample_groups: (healResult.groups || []).slice(0, 3)
        }
      );
    }

    return healResult;
  }

  async repairOrphanedLinkedStatuses() {
    const repairResult = await this.executeWithRetry(
      () => this.mappingMigration.repairLinkedStatusesWithoutMapping(this.getDbPool()),
      'repairLinkedStatusesWithoutMapping'
    );

    if (repairResult.repairedCount > 0) {
      this.logger.warn(
        `[HEAL] 检测到 ${repairResult.repairedCount} 场 RECON_LINKED 残留，已自动回退为 harvested`,
        {
          repaired_count: repairResult.repairedCount,
          sample_match_ids: (repairResult.matchIds || []).slice(0, 10)
        }
      );
    }

    return repairResult;
  }

  isCreateIndexDuplicateConflict(error) {
    if (!error || error.code !== '23505') {
      return false;
    }

    const message = String(error.message || '');
    const detail = String(error.detail || '');
    return message.includes('idx_mapping_season_hash_unique')
      || message.includes('could not create unique index')
      || detail.includes('(season, oddsportal_hash)');
  }
}

module.exports = { ReconSchemaJanitor };
