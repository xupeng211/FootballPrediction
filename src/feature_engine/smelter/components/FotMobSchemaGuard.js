'use strict';

const DEFAULT_MAX_DEPTH = 4;

const DEFAULT_EXPECTED_KEYS = [
  'content',
  'general',
  'header',
  'nav',
  'stats',
  'lineup',
  'matchId',
  'details',
  'teams',
  'home',
  'away'
];

function isPlainObject(value) {
  return value !== null && typeof value === 'object' && !Array.isArray(value);
}

function flattenKeyShape(value, options = {}) {
  const maxDepth = Number.isInteger(options.maxDepth) ? options.maxDepth : DEFAULT_MAX_DEPTH;
  const keys = new Set();

  function visit(node, prefix, depth) {
    if (depth > maxDepth || node === null || node === undefined) {
      return;
    }

    if (Array.isArray(node)) {
      if (prefix) {
        keys.add(`${prefix}[]`);
      }
      const firstObject = node.find(item => item && typeof item === 'object');
      if (firstObject) {
        visit(firstObject, prefix ? `${prefix}[]` : '[]', depth + 1);
      }
      return;
    }

    if (!isPlainObject(node)) {
      return;
    }

    for (const key of Object.keys(node).sort()) {
      const path = prefix ? `${prefix}.${key}` : key;
      keys.add(path);
      visit(node[key], path, depth + 1);
    }
  }

  visit(value, '', 0);
  return [...keys].sort();
}

function normalizeExpectedKeys(expectedSchema) {
  if (Array.isArray(expectedSchema)) {
    return [...new Set(expectedSchema.map(item => String(item).trim()).filter(Boolean))].sort();
  }

  return flattenKeyShape(expectedSchema || {}, { maxDepth: DEFAULT_MAX_DEPTH });
}

class FotMobSchemaGuard {
  constructor(options = {}) {
    this.expectedKeys = normalizeExpectedKeys(options.expectedKeys || options.expectedSchema || DEFAULT_EXPECTED_KEYS);
    this.maxDepth = Number.isInteger(options.maxDepth) ? options.maxDepth : DEFAULT_MAX_DEPTH;
    this.alerts = [];
    this.logger = options.logger || console;
    this.alertLimit = Number.isInteger(options.alertLimit) ? options.alertLimit : 100;
  }

  inspect(rawData, metadata = {}) {
    const currentKeys = flattenKeyShape(rawData, { maxDepth: this.maxDepth });
    const expected = new Set(this.expectedKeys);
    const current = new Set(currentKeys);

    const added = currentKeys.filter(key => !expected.has(key));
    const removed = this.expectedKeys.filter(key => !current.has(key));
    const ok = added.length === 0 && removed.length === 0;
    const result = {
      ok,
      matchId: metadata.matchId || metadata.match_id || null,
      inspectedAt: new Date().toISOString(),
      added,
      removed,
      currentKeys,
      expectedKeys: this.expectedKeys
    };

    if (!ok) {
      this._recordAlert(result);
    }

    return result;
  }

  getAlerts() {
    return this.alerts.map(alert => ({ ...alert }));
  }

  summarize(results = this.alerts) {
    const summary = {
      inspected: results.length,
      changed: 0,
      added: {},
      removed: {}
    };

    for (const result of results) {
      if (!result.ok) {
        summary.changed++;
      }
      for (const key of result.added || []) {
        summary.added[key] = (summary.added[key] || 0) + 1;
      }
      for (const key of result.removed || []) {
        summary.removed[key] = (summary.removed[key] || 0) + 1;
      }
    }

    return summary;
  }

  _recordAlert(result) {
    const alert = {
      type: 'FOTMOB_SCHEMA_DIFF',
      severity: 'warning',
      matchId: result.matchId,
      inspectedAt: result.inspectedAt,
      added: result.added,
      removed: result.removed
    };

    this.alerts.push(alert);
    if (this.alerts.length > this.alertLimit) {
      this.alerts.shift();
    }

    if (typeof this.logger.warn === 'function') {
      this.logger.warn('[FotMobSchemaGuard] schema diff detected', alert);
    }
  }
}

module.exports = {
  DEFAULT_EXPECTED_KEYS,
  FotMobSchemaGuard,
  flattenKeyShape
};
