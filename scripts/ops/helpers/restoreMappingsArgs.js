'use strict';

const { DEFAULT_SEASON, DEFAULT_THRESHOLD } = require('./restoreMappingsShared');

const VALUE_HANDLERS = new Map([
  ['--season', (result, value) => {
    result.season = String(value || '').trim() || DEFAULT_SEASON;
  }],
  ['--threshold', (result, value) => {
    result.threshold = Number(value);
  }],
  ['--limit', (result, value) => {
    result.limit = Number.parseInt(value, 10);
  }]
]);

const FLAG_HANDLERS = new Map([
  ['--dry-run', (result) => {
    result.dryRun = true;
  }],
  ['--verbose', (result) => {
    result.verbose = true;
  }]
]);

function validateArgs(result) {
  if (!Number.isFinite(result.threshold) || result.threshold <= 0 || result.threshold > 1) {
    throw new Error(`非法 --threshold: ${result.threshold}`);
  }

  if (result.limit !== null && (!Number.isInteger(result.limit) || result.limit <= 0)) {
    throw new Error(`非法 --limit: ${result.limit}`);
  }
}

function parseArgs(argv = process.argv.slice(2)) {
  const args = Array.isArray(argv) ? [...argv] : [];
  const result = {
    season: DEFAULT_SEASON,
    threshold: DEFAULT_THRESHOLD,
    limit: null,
    dryRun: false,
    verbose: false
  };

  for (let index = 0; index < args.length; index++) {
    const token = args[index];
    const valueHandler = VALUE_HANDLERS.get(token);
    if (valueHandler) {
      valueHandler(result, args[++index]);
      continue;
    }

    const flagHandler = FLAG_HANDLERS.get(token);
    if (flagHandler) {
      flagHandler(result);
    }
  }

  validateArgs(result);
  return result;
}

module.exports = {
  parseArgs
};
