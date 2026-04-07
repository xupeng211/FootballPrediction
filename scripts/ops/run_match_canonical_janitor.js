#!/usr/bin/env node
'use strict';

const { Pool } = require('pg');

const { buildDbPoolConfig } = require('./ReconCLIHandler');
const { FixtureRepository } = require('../../src/infrastructure/services/FixtureRepository');

function parseArgs(argv = process.argv.slice(2)) {
  const args = Array.isArray(argv) ? [...argv] : [];
  const result = {
    season: null,
    sourceProvider: null,
    limit: null,
    auditOnly: true
  };

  for (let index = 0; index < args.length; index++) {
    switch (args[index]) {
      case '--season':
        result.season = args[++index];
        break;
      case '--source-provider':
        result.sourceProvider = args[++index];
        break;
      case '--limit':
        result.limit = parseInt(args[++index], 10);
        break;
      case '--audit-only':
        result.auditOnly = true;
        break;
      case '--repair':
        result.auditOnly = false;
        break;
      default:
        break;
    }
  }

  if (!result.season) {
    throw new Error('--season 参数是必需的');
  }

  return result;
}

async function main(argv = process.argv.slice(2)) {
  const args = parseArgs(argv);
  const dbPool = new Pool(buildDbPoolConfig());
  const repository = new FixtureRepository({ dbPool });

  try {
    await repository.init({ repairOrphanedLinkedStatuses: false });

    const options = {
      season: String(args.season),
      sourceProvider: args.sourceProvider || undefined,
      limit: Number.isInteger(args.limit) && args.limit > 0 ? args.limit : undefined
    };

    const summary = args.auditOnly
      ? await repository.auditCanonicalIdentityDuplicates(options)
      : await repository.repairCanonicalIdentity(options);

    console.log(JSON.stringify({
      success: true,
      mode: args.auditOnly ? 'audit_only' : 'repair',
      season: args.season,
      sourceProvider: args.sourceProvider || null,
      summary
    }, null, 2));

    return 0;
  } finally {
    await repository.close().catch(async () => {
      await dbPool.end();
    });
  }
}

if (require.main === module) {
  main().then(
    (exitCode) => process.exit(exitCode),
    (error) => {
      console.error('[janitor] 执行失败:', error.message);
      process.exit(1);
    }
  );
}

module.exports = {
  parseArgs,
  main
};
