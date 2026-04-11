'use strict';

function getConfidenceThreshold(reconConfig = {}) {
  return (reconConfig.matching || {}).confidence_threshold;
}

function buildMismatchInsertPayload(evidenceData, hasOptionalFields = {}, buildEvidenceOnlyHash) {
  const columns = ['match_id', 'oddsportal_hash', 'full_url', 'season', 'league_name', 'home_team', 'away_team', 'status', 'created_at', 'updated_at'];
  const values = ['$1', '$2', '$3', '$4', '$5', '$6', '$7', '$8', 'NOW()', 'NOW()'];
  const params = [
    String(evidenceData.match_id),
    buildEvidenceOnlyHash(evidenceData.match_id),
    evidenceData.full_url || `evidence://recon/${encodeURIComponent(String(evidenceData.match_id))}`,
    String(evidenceData.season),
    String(evidenceData.league_name),
    String(evidenceData.home_team),
    String(evidenceData.away_team),
    'pending'
  ];

  if (hasOptionalFields.match_confidence) {
    columns.push('match_confidence');
    values.push(`$${params.length + 1}`);
    params.push(Number(evidenceData.match_confidence || 0));
  }

  if (hasOptionalFields.mapping_method) {
    columns.push('mapping_method');
    values.push(`$${params.length + 1}`);
    params.push(String(evidenceData.mapping_method || 'unknown'));
  }

  if (hasOptionalFields.is_reversed) {
    columns.push('is_reversed');
    values.push(`$${params.length + 1}`);
    params.push(Boolean(evidenceData.is_reversed));
  }

  if (hasOptionalFields.candidate_name) {
    columns.push('candidate_name');
    values.push(`$${params.length + 1}`);
    params.push(evidenceData.candidate_name ? String(evidenceData.candidate_name) : null);
  }

  if (hasOptionalFields.is_evidence_only) {
    columns.push('is_evidence_only');
    values.push(`$${params.length + 1}`);
    params.push(true);
  }

  return { columns, params, values };
}

function buildMismatchInsertQuery(columns, values, hasOptionalFields = {}) {
  return `
    INSERT INTO matches_oddsportal_mapping (${columns.join(', ')})
    VALUES (${values.join(', ')})
    ON CONFLICT (match_id, season) DO UPDATE SET
      oddsportal_hash = EXCLUDED.oddsportal_hash,
      full_url = EXCLUDED.full_url,
      home_team = EXCLUDED.home_team,
      away_team = EXCLUDED.away_team,
      status = EXCLUDED.status,
      updated_at = NOW()
      ${hasOptionalFields.match_confidence ? ', match_confidence = EXCLUDED.match_confidence' : ''}
      ${hasOptionalFields.mapping_method ? ', mapping_method = EXCLUDED.mapping_method' : ''}
      ${hasOptionalFields.is_reversed ? ', is_reversed = EXCLUDED.is_reversed' : ''}
      ${hasOptionalFields.candidate_name ? ', candidate_name = EXCLUDED.candidate_name' : ''}
      ${hasOptionalFields.is_evidence_only ? ', is_evidence_only = TRUE' : ''}
    WHERE COALESCE(matches_oddsportal_mapping.is_evidence_only, FALSE) = TRUE
    RETURNING match_id;
  `;
}

function buildStatusUpdateStatement(matchId, status, options = {}) {
  const expectedCurrentStatus = options.expectedCurrentStatus || null;
  const requireNoMapping = Boolean(options.requireNoMapping);
  let query = `
    UPDATE matches m
    SET pipeline_status = $2,
        updated_at = NOW()
    WHERE m.match_id = $1
  `;
  const params = [String(matchId), status];

  if (expectedCurrentStatus) {
    params.push(expectedCurrentStatus);
    query += `
      AND m.pipeline_status = $3
    `;
  }

  if (requireNoMapping) {
    query += `
      AND NOT EXISTS (
        SELECT 1
        FROM matches_oddsportal_mapping map
        WHERE map.match_id = m.match_id
          AND COALESCE(map.is_evidence_only, FALSE) = FALSE
      )
    `;
  }

  return { params, query };
}

function buildOrderedMappings(mappings = []) {
  return [...mappings].sort((left, right) =>
    String(left.match_id).localeCompare(String(right.match_id))
  );
}

function buildMappingInsertPayload(mappingData, hasOptionalFields = {}, reconConfig = {}) {
  const columns = ['match_id', 'oddsportal_hash', 'full_url', 'season', 'league_name', 'home_team', 'away_team', 'status', 'created_at', 'updated_at'];
  const values = ['$1', '$2', '$3', '$4', '$5', '$6', '$7', '$8', 'NOW()', 'NOW()'];
  const params = [
    mappingData.match_id,
    mappingData.oddsportal_hash,
    mappingData.full_url,
    mappingData.season,
    mappingData.league_name,
    mappingData.home_team,
    mappingData.away_team,
    mappingData.status || 'pending'
  ];

  if (hasOptionalFields.match_confidence) {
    columns.push('match_confidence');
    values.push(`$${params.length + 1}`);
    params.push(mappingData.match_confidence ?? getConfidenceThreshold(reconConfig));
  }

  if (hasOptionalFields.mapping_method) {
    columns.push('mapping_method');
    values.push(`$${params.length + 1}`);
    params.push(mappingData.mapping_method || 'protocol_extract');
  }

  if (hasOptionalFields.is_reversed) {
    columns.push('is_reversed');
    values.push(`$${params.length + 1}`);
    params.push(Boolean(mappingData.is_reversed));
  }

  if (hasOptionalFields.is_evidence_only) {
    columns.push('is_evidence_only');
    values.push(`$${params.length + 1}`);
    params.push(false);
  }

  return { columns, params, values };
}

function buildMappingInsertQuery(sqlTemplates = {}, payload, hasOptionalFields = {}) {
  return (sqlTemplates.save_mapping || `
    INSERT INTO matches_oddsportal_mapping ({columns})
    VALUES ({values})
    ON CONFLICT (match_id, season) DO UPDATE SET
      oddsportal_hash = EXCLUDED.oddsportal_hash,
      full_url = EXCLUDED.full_url,
      home_team = EXCLUDED.home_team,
      away_team = EXCLUDED.away_team,
      status = EXCLUDED.status,
      updated_at = NOW()
      {optional_updates}
    RETURNING match_id;
  `)
    .replace('{columns}', payload.columns.join(', '))
    .replace('{values}', payload.values.join(', '))
    .replace('{optional_updates}', [
      hasOptionalFields.match_confidence ? ', match_confidence = EXCLUDED.match_confidence' : '',
      hasOptionalFields.mapping_method ? ', mapping_method = EXCLUDED.mapping_method' : '',
      hasOptionalFields.is_reversed ? ', is_reversed = EXCLUDED.is_reversed' : '',
      hasOptionalFields.candidate_name ? ', candidate_name = NULL' : '',
      hasOptionalFields.is_evidence_only ? ', is_evidence_only = FALSE' : ''
    ].join(''));
}

function buildForceOverwriteParams(existingMappingRow, incomingMapping, hasOptionalFields = {}, reconConfig = {}) {
  return [
    String(incomingMapping.match_id),
    incomingMapping.full_url,
    incomingMapping.league_name,
    incomingMapping.home_team,
    incomingMapping.away_team,
    incomingMapping.status || 'pending',
    hasOptionalFields.match_confidence
      ? (incomingMapping.match_confidence ?? getConfidenceThreshold(reconConfig))
      : null,
    hasOptionalFields.mapping_method
      ? String(incomingMapping.mapping_method || 'protocol_extract')
      : null,
    hasOptionalFields.is_reversed
      ? Boolean(incomingMapping.is_reversed)
      : null,
    String(incomingMapping.season),
    String(incomingMapping.oddsportal_hash),
    String(existingMappingRow.match_id)
  ];
}

module.exports = {
  buildForceOverwriteParams,
  buildMappingInsertPayload,
  buildMappingInsertQuery,
  buildMismatchInsertPayload,
  buildMismatchInsertQuery,
  buildOrderedMappings,
  buildStatusUpdateStatement,
  getConfidenceThreshold
};
