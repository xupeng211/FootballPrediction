'use strict';

const TRUE_VALUES = new Set(['1', 'true', 'yes', 'y', 'on']);

function normalizeBoolean(value) {
  if (typeof value === 'boolean') {
    return value;
  }

  if (value === null || value === undefined) {
    return false;
  }

  return TRUE_VALUES.has(String(value).trim().toLowerCase());
}

function isFotMobComplianceModeEnabled(value = process.env.FOTMOB_COMPLIANCE_MODE) {
  return normalizeBoolean(value);
}

function resolveFotMobComplianceMode(config = {}) {
  if (isFotMobComplianceModeEnabled(process.env.FOTMOB_COMPLIANCE_MODE)) {
    return true;
  }

  if (Object.prototype.hasOwnProperty.call(config, 'fotmobComplianceMode')) {
    return normalizeBoolean(config.fotmobComplianceMode);
  }

  if (Object.prototype.hasOwnProperty.call(config, 'complianceMode')) {
    return normalizeBoolean(config.complianceMode);
  }

  return false;
}

module.exports = {
  isFotMobComplianceModeEnabled,
  resolveFotMobComplianceMode
};
