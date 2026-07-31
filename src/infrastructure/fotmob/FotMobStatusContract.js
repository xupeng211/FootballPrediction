'use strict';

// lifecycle: permanent
// Shared, dependency-free status contract for the FotMob-to-application
// status mapping. This is the single source of truth for both the
// exporter (FotMobCandidateExporter) and the canonical inventory
// contract (CanonicalInventoryContract).
//
// This module MUST NOT import from either consumer — it is a leaf.

const STATUS_MAPPING_VERSION = 'fotmob-status-to-matches-status/v1';

/**
 * Allowed canonical provider_status values.
 * Every exported candidate MUST carry exactly one of these.
 */
const ALLOWED_PROVIDER_STATUSES = new Set([
    'scheduled',
    'finished',
    'postponed',
    'cancelled',
]);

/**
 * Mapping from FotMob-derived provider_status to application-level
 * status label. Every allowed key maps to itself; this contract
 * exists so the canonical inventory contract can validate the
 * mapping without importing exporter internals.
 */
const FOTMOB_STATUS_TO_APPLICATION_STATUS = Object.freeze({
    scheduled: 'scheduled',
    finished: 'finished',
    postponed: 'postponed',
    cancelled: 'cancelled',
});

module.exports = {
    ALLOWED_PROVIDER_STATUSES,
    FOTMOB_STATUS_TO_APPLICATION_STATUS,
    STATUS_MAPPING_VERSION,
};
