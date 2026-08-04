"use strict";

// lifecycle: permanent
//
// FotMob detail staging — pure offline converter.
//
// Converts one repository-external (payload, manifest, source-index) input
// into a `fotmob-detail-staging-artifact/v1` document.
//
// Hard offline guarantees:
//   - zero network: no fetcher import, no fetch/http module, no URL handling;
//   - zero database: no pg/ioredis/DB client import, no env DB variables;
//   - zero capture: never invokes capture or PLAN/PREFLIGHT/CAPTURE/REPLAY;
//   - inputs are never mutated (payload/manifest objects are read only);
//   - no wall-clock time enters business fields (generated_at comes from the
//     manifest's response_received_at; observation_id is a deterministic
//     UUID v5 over the observation key);
//   - no local absolute path enters the business projection or the artifact
//     (paths exist only in the source index document, which is not a
//     business output);
//   - canonical_match_id is never guessed: null + UNLINKED_NOT_ATTEMPTED.
//
// The converter is a pure function of its inputs: shuffling the source index
// entry order does not change the artifact bytes (per-observation artifacts
// are independent documents; the aggregate ordering is the retention layer's
// responsibility, sorted by observation key).

const {
  validateSourceIndex,
  validateObservation,
  buildStagingArtifact,
  TERMINAL_STATES,
  ERROR_CODES,
} = require("./FotMobDetailStagingContract");

/**
 * Convert one observation pair into a staging artifact document (pure).
 *
 * @param {object} args - {
 *   payload: parsed payload document,
 *   manifest: parsed manifest document,
 *   payloadBytes: Buffer of the physical payload file,
 *   payloadFileSha256: SHA-256 of the payload file bytes (optional; verified
 *                       against manifest in L4 when provided)
 * }
 * @returns {object} {
 *   ok, terminal_state, error_code, quarantine_status,
 *   artifact: object|null, validation: object, errors: [{code,message}]
 * }
 */
function convertPair(args = {}) {
  const payload = args.payload;
  const manifest = args.manifest;
  const payloadBytes = args.payloadBytes;
  const payloadFileSha256 = args.payloadFileSha256;

  const validation = validateObservation({
    payload,
    manifest,
    payloadBytes: payloadBytes || Buffer.alloc(0),
  });

  if (!validation.ok) {
    return {
      ok: false,
      source_match_id:
        payload &&
        payload.source_match_id !== null &&
        payload.source_match_id !== undefined
          ? String(payload.source_match_id)
          : "",
      terminal_state: validation.terminal_state,
      error_code: validation.error_code,
      quarantine_status: validation.quarantine_status,
      artifact: null,
      validation,
      errors: validation.errors,
    };
  }

  // L1–L8 green: the terminal state defaults to ACCEPTED_NEW; the
  // retention store re-classifies to ACCEPTED_REPEAT_EXACT / _EQUIVALENT
  // against previously staged snapshots. Quarantined observations never
  // reach here (validateObservation reports them as not ok).
  const artifact = buildStagingArtifact({
    payload,
    manifest,
    validation,
    payloadFileSha256,
    terminalState: TERMINAL_STATES.ACCEPTED_NEW,
  });

  return {
    ok: true,
    terminal_state: TERMINAL_STATES.ACCEPTED_NEW,
    error_code: null,
    quarantine_status: "not_quarantined",
    artifact,
    validation,
    errors: [],
  };
}

/**
 * Convert every entry in a validated source index (pure, order-independent
 * per observation).
 *
 * @param {object} args - { sourceIndex, loader: async (entry) =>
 *   { payload, manifest, payloadBytes } }
 * @returns {Promise<Array>} results in source-index order; each item as in
 *   convertPair plus { source_match_id }
 */
async function convertAll(args = {}) {
  const sourceIndex = args.sourceIndex;
  const loader = args.loader;

  const indexValidation = validateSourceIndex(sourceIndex);
  if (!indexValidation.ok) {
    return {
      ok: false,
      errors: indexValidation.errors.map((message) => ({
        code: ERROR_CODES.E001,
        message,
      })),
      results: [],
      source_index_validation: indexValidation,
    };
  }

  const results = [];
  for (const entry of indexValidation.entries) {
    let loaded;
    try {
      loaded = await loader(entry);
    } catch (error) {
      results.push({
        ok: false,
        source_match_id: String(entry.source_match_id ?? ""),
        terminal_state: TERMINAL_STATES.REJECTED_PROVENANCE_BROKEN,
        error_code: ERROR_CODES.E008,
        quarantine_status: "not_quarantined",
        artifact: null,
        errors: [
          {
            code: ERROR_CODES.E008,
            message: `input load failed: ${error.message}`,
          },
        ],
      });
      continue;
    }
    const converted = convertPair({
      payload: loaded.payload,
      manifest: loaded.manifest,
      payloadBytes: loaded.payloadBytes,
      payloadFileSha256: loaded.payloadFileSha256,
    });
    results.push({
      ...converted,
      source_match_id: String(entry.source_match_id ?? ""),
    });
  }

  return {
    ok: results.every((r) => r.ok),
    errors: results.flatMap((r) => (r.ok ? [] : r.errors)),
    results,
    source_index_validation: indexValidation,
  };
}

module.exports = { convertPair, convertAll };
