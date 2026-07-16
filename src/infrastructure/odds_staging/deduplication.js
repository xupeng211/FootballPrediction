'use strict';

// lifecycle: permanent；不依赖数据库的 exact duplicate 与 semantic conflict 处理。

const {
    appendObservationSignals,
    buildExactDuplicateKey,
    buildSemanticDuplicateKey,
    stableCanonicalize,
} = require('./contracts');

function sourceReference(observation) {
    return {
        idempotency_key: observation.idempotency_key,
        raw_record_locator: observation.raw_record_locator,
        raw_sha256: observation.raw_sha256,
    };
}

function mergeDuplicateEvidence(primary, duplicate, field) {
    const current = primary.duplicate_evidence || {};
    const evidence = Array.isArray(current[field]) ? current[field] : [];
    const nextEvidence = [...evidence, sourceReference(duplicate)].sort((left, right) =>
        left.idempotency_key.localeCompare(right.idempotency_key)
    );
    return {
        ...primary,
        duplicate_evidence: stableCanonicalize({
            ...current,
            [field]: nextEvidence,
        }),
    };
}

function sortByIdempotency(observations) {
    return [...observations].sort((left, right) =>
        String(left.idempotency_key).localeCompare(String(right.idempotency_key))
    );
}

function deduplicateObservations(observations = []) {
    const exactUnique = new Map();
    let exactDuplicateCount = 0;
    for (const observation of sortByIdempotency(observations)) {
        const key = buildExactDuplicateKey(observation);
        if (!exactUnique.has(key)) {
            exactUnique.set(key, observation);
            continue;
        }
        exactDuplicateCount += 1;
        exactUnique.set(key, mergeDuplicateEvidence(exactUnique.get(key), observation, 'exact_duplicates'));
    }

    const semanticGroups = new Map();
    for (const observation of exactUnique.values()) {
        const key = buildSemanticDuplicateKey(observation);
        if (!semanticGroups.has(key)) {
            semanticGroups.set(key, []);
        }
        semanticGroups.get(key).push(observation);
    }

    const resolved = [];
    let semanticDuplicateCount = 0;
    let semanticConflictCount = 0;
    for (const [semanticKey, group] of semanticGroups.entries()) {
        const ordered = sortByIdempotency(group);
        const oddsValues = [...new Set(ordered.map(observation => String(observation.decimal_odds)))].sort();
        if (oddsValues.length === 1) {
            let primary = ordered[0];
            for (const duplicate of ordered.slice(1)) {
                semanticDuplicateCount += 1;
                primary = mergeDuplicateEvidence(primary, duplicate, 'semantic_duplicates');
            }
            resolved.push(primary);
            continue;
        }

        semanticConflictCount += 1;
        for (const observation of ordered) {
            const currentEvidence = observation.duplicate_evidence || {};
            resolved.push(
                appendObservationSignals(
                    {
                        ...observation,
                        duplicate_evidence: stableCanonicalize({
                            ...currentEvidence,
                            semantic_conflict: {
                                decimal_odds_values: oddsValues,
                                semantic_key: semanticKey,
                            },
                        }),
                    },
                    ['semantic_duplicate_conflict'],
                    ['semantic_duplicate_conflict']
                )
            );
        }
    }

    return {
        observations: sortByIdempotency(resolved),
        exact_duplicate_count: exactDuplicateCount,
        semantic_duplicate_count: semanticDuplicateCount,
        semantic_conflict_count: semanticConflictCount,
    };
}

module.exports = {
    deduplicateObservations,
};
