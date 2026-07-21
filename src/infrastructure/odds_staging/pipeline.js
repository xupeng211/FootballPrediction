'use strict';

// lifecycle: permanent；默认无写入的本地 raw → canonical observation → quarantine 薄流水线。

const fs = require('node:fs');
const path = require('node:path');
const {
    QUARANTINE_SCHEMA_VERSION,
    appendObservationSignals,
    createCanonicalObservation,
    isStrictAbsoluteTimestamp,
    stableCanonicalize,
    stableStringify,
} = require('./contracts');
const { ADAPTER_VERSIONS, getAdapter } = require('./adapters');
const { deduplicateObservations } = require('./deduplication');
const { detectFakeOdds } = require('./fakeOddsDetector');
const { decideMatchLink } = require('./matchLinker');
const { OfflineStagingError, assertAbsoluteLocalPath, loadCandidates, loadSourceBundle } = require('./sourceManifest');
const { validateObservation } = require('./validators');

const ADAPTER_MEDIA_TYPES = Object.freeze({
    'football-data-csv': 'text/csv',
    'oddsportal-explicit-envelope-html': 'text/html',
});

function resolveIngestedAt(value, clock) {
    const candidate = value || clock();
    if (!isStrictAbsoluteTimestamp(candidate)) {
        throw new OfflineStagingError(
            'INPUT_ERROR',
            'ingested_at must be an ISO-8601 timestamp with Z or an explicit numeric offset'
        );
    }
    return String(candidate);
}

function ensureAdapterCompatibility(manifest, adapterName) {
    const adapter = getAdapter(adapterName);
    if (!adapter) {
        throw new OfflineStagingError('INPUT_ERROR', `unsupported adapter: ${adapterName || ''}`);
    }
    if (manifest.adapter !== adapterName) {
        throw new OfflineStagingError('INPUT_ERROR', 'manifest.adapter does not match the requested adapter');
    }
    if (manifest.adapter_version !== ADAPTER_VERSIONS[adapterName]) {
        throw new OfflineStagingError(
            'INPUT_ERROR',
            `manifest.adapter_version ${manifest.adapter_version || ''} is not supported; this build only accepts ${adapterName}@${ADAPTER_VERSIONS[adapterName]}`
        );
    }
    if (manifest.raw_media_type !== ADAPTER_MEDIA_TYPES[adapterName]) {
        throw new OfflineStagingError('INPUT_ERROR', 'manifest.raw_media_type does not match the requested adapter');
    }
    return adapter;
}

function buildObservation(manifest, draft, ingestedAt) {
    const { adapter_quarantine_reasons: adapterReasons = [], kickoff_time_interpretation_evidence, ...fields } = draft;
    const observation = createCanonicalObservation({
        ...fields,
        source_provider: manifest.source_provider,
        source_url: manifest.source_url,
        captured_at: manifest.captured_at,
        capture_time_status: manifest.capture_time_status,
        source_timezone: manifest.source_timezone,
        raw_sha256: manifest.raw_sha256,
        adapter: manifest.adapter,
        adapter_version: manifest.adapter_version,
        provenance_status: manifest.provenance_status,
        quarantine_reasons: adapterReasons,
        ingested_at: ingestedAt,
    });
    // Attach kickoff_time_interpretation_evidence if present (audit trail)
    if (kickoff_time_interpretation_evidence) {
        observation.kickoff_time_interpretation_evidence = kickoff_time_interpretation_evidence;
    }
    return observation;
}

function applyMatchLink(observation, candidates) {
    const matchLink = decideMatchLink(observation, candidates);
    const linked = { ...observation, match_link: matchLink };
    if (matchLink.status === 'matched') {
        return linked;
    }
    // Specific conflict reasons from derived kickoff diagnostics
    if (/^derived_kickoff_conflict/.test(matchLink.method)) {
        return appendObservationSignals(linked, [matchLink.method], [matchLink.method]);
    }
    const reason = matchLink.status === 'ambiguous' ? 'match_link_ambiguous' : 'match_link_unmatched';
    return appendObservationSignals(linked, [reason], [reason]);
}

function createAdapterQuarantine(manifest, adapterEntry) {
    return stableCanonicalize({
        schema_version: QUARANTINE_SCHEMA_VERSION,
        source_provider: manifest.source_provider,
        source_match_id: manifest.source_match_id || null,
        raw_sha256: manifest.raw_sha256,
        raw_record_locator: adapterEntry.raw_record_locator || 'raw:document',
        adapter: manifest.adapter,
        adapter_version: manifest.adapter_version,
        reasons: [...new Set(adapterEntry.reasons || [])].sort(),
        evidence: {
            parsing_evidence: adapterEntry.evidence || {},
            source_fields: {
                competition: manifest.competition || null,
                source_match_id: manifest.source_match_id || null,
                source_url: manifest.source_url,
            },
        },
    });
}

function createObservationQuarantine(observation) {
    return stableCanonicalize({
        schema_version: QUARANTINE_SCHEMA_VERSION,
        source_provider: observation.source_provider,
        source_match_id: observation.source_match_id,
        raw_sha256: observation.raw_sha256,
        raw_record_locator: observation.raw_record_locator,
        adapter: observation.adapter,
        adapter_version: observation.adapter_version,
        reasons: [...new Set(observation.quarantine_reasons || [])].sort(),
        evidence: {
            extraction_method: observation.extraction_method,
            match_link: observation.match_link,
            quality_flags: observation.quality_flags,
            duplicate_evidence: observation.duplicate_evidence,
            parsed_fields: {
                bookmaker: observation.bookmaker,
                bookmaker_source_id: observation.bookmaker_source_id,
                market: observation.market,
                selection: observation.selection,
                line: observation.line,
                decimal_odds: observation.decimal_odds,
                snapshot_type: observation.snapshot_type,
                source_observed_at: observation.source_observed_at,
                captured_at: observation.captured_at,
                source_timezone: observation.source_timezone,
                idempotency_key: observation.idempotency_key,
                provenance_status: observation.provenance_status,
                // 可选合同字段只在真实存在时进入证据，保持旧 quarantine 输出不变。
                ...(observation.source_quote_series ? { source_quote_series: observation.source_quote_series } : {}),
                ...(observation.capture_time_status ? { capture_time_status: observation.capture_time_status } : {}),
            },
            source_fields: {
                away_team: observation.away_team,
                competition: observation.competition,
                home_team: observation.home_team,
                kickoff_at: observation.kickoff_at,
                season: observation.season,
            },
        },
    });
}

function sortByKey(records) {
    return [...records].sort((left, right) => stableStringify(left).localeCompare(stableStringify(right)));
}

function runOfflineStaging(options = {}, dependencies = {}) {
    const clock = dependencies.clock || (() => new Date().toISOString());
    const bundle = (dependencies.loadSourceBundle || loadSourceBundle)(
        {
            manifestPath: options.manifestPath,
            sourcePath: options.sourcePath,
        },
        dependencies
    );
    const adapter = ensureAdapterCompatibility(bundle.manifest, options.adapter);
    const ingestedAt = resolveIngestedAt(options.ingestedAt, clock);
    const adapterResult = adapter(bundle.rawText, { manifest: bundle.manifest });
    const candidates = Array.isArray(options.candidates) ? options.candidates : [];

    let observations = (adapterResult.observations || [])
        .map(draft => buildObservation(bundle.manifest, draft, ingestedAt))
        .map(validateObservation);
    observations = detectFakeOdds(observations, options.fakeOddsConfig);
    observations = observations.map(observation => applyMatchLink(observation, candidates));

    const deduplication = deduplicateObservations(observations);
    const acceptedObservations = deduplication.observations.filter(
        observation => observation.quarantine_reasons.length === 0
    );
    const quarantinedObservations = deduplication.observations
        .filter(observation => observation.quarantine_reasons.length > 0)
        .map(createObservationQuarantine);
    const adapterQuarantine = (adapterResult.quarantine || []).map(entry =>
        createAdapterQuarantine(bundle.manifest, entry)
    );
    const quarantine = sortByKey([...adapterQuarantine, ...quarantinedObservations]);

    return {
        normalized_manifest: bundle.manifest,
        accepted_observations: sortByKey(acceptedObservations),
        quarantine,
        summary: stableCanonicalize({
            schema_version: 'odds-staging-summary/v1',
            adapter: bundle.manifest.adapter,
            adapter_version: bundle.manifest.adapter_version,
            source_provider: bundle.manifest.source_provider,
            raw_sha256: bundle.manifest.raw_sha256,
            raw_size_bytes: bundle.manifest.raw_size_bytes,
            total_observations: observations.length,
            accepted_count: acceptedObservations.length,
            quarantine_count: quarantine.length,
            exact_duplicate_count: deduplication.exact_duplicate_count,
            semantic_duplicate_count: deduplication.semantic_duplicate_count,
            semantic_conflict_count: deduplication.semantic_conflict_count,
            default_mode: 'dry_run_no_write',
        }),
    };
}

function isInsidePath(rootPath, targetPath) {
    const relative = path.relative(rootPath, targetPath);
    return (
        relative === '' || (!relative.startsWith(`..${path.sep}`) && relative !== '..' && !path.isAbsolute(relative))
    );
}

function resolveExternalEmitDirectory(rawDirectory, options = {}, fileSystem = fs) {
    const repositoryRoot = fileSystem.realpathSync(options.repositoryRoot || path.resolve(__dirname, '../../..'));
    const requestedDirectory = assertAbsoluteLocalPath(rawDirectory, 'emit directory');
    if (!fileSystem.existsSync(requestedDirectory)) {
        throw new OfflineStagingError(
            'SAFETY_ERROR',
            'emit directory must already exist; it will not be created automatically'
        );
    }
    const emitDirectory = fileSystem.realpathSync(requestedDirectory);
    if (!fileSystem.statSync(emitDirectory).isDirectory()) {
        throw new OfflineStagingError('SAFETY_ERROR', 'emit directory must be a directory');
    }
    if (isInsidePath(repositoryRoot, emitDirectory)) {
        throw new OfflineStagingError('SAFETY_ERROR', 'emit directory must be outside the Git repository');
    }
    return emitDirectory;
}

function emitDeterministicResult(result, emitDirectory, options = {}, fileSystem = fs) {
    const outputDirectory = resolveExternalEmitDirectory(emitDirectory, options, fileSystem);
    const files = {
        'source-manifest.normalized.json': `${stableStringify(result.normalized_manifest)}\n`,
        'accepted-observations.jsonl':
            result.accepted_observations.map(stableStringify).join('\n') +
            (result.accepted_observations.length > 0 ? '\n' : ''),
        'quarantine.jsonl':
            result.quarantine.map(stableStringify).join('\n') + (result.quarantine.length > 0 ? '\n' : ''),
        'summary.json': `${stableStringify(result.summary)}\n`,
    };
    for (const filename of Object.keys(files)) {
        if (fileSystem.existsSync(path.join(outputDirectory, filename))) {
            throw new OfflineStagingError('SAFETY_ERROR', `emit output already exists: ${filename}`);
        }
    }
    const temporaryPaths = [];
    const renamedFinalPaths = [];
    const temporaryToken = options.temporaryToken || String(process.pid) + '-' + String(Date.now());
    try {
        for (const [index, [filename, content]] of Object.entries(files).entries()) {
            const temporaryPath = path.join(
                outputDirectory,
                '.' + filename + '.' + temporaryToken + '.' + String(index) + '.tmp'
            );
            if (fileSystem.existsSync(temporaryPath)) {
                throw new OfflineStagingError('SAFETY_ERROR', 'temporary emit output already exists: ' + filename);
            }
            temporaryPaths.push(temporaryPath);
            fileSystem.writeFileSync(temporaryPath, content, { encoding: 'utf8', flag: 'wx' });
        }
        for (const [index, filename] of Object.keys(files).entries()) {
            const finalPath = path.join(outputDirectory, filename);
            fileSystem.renameSync(temporaryPaths[index], finalPath);
            renamedFinalPaths.push(finalPath);
        }
    } catch (error) {
        for (const outputPath of [...temporaryPaths, ...renamedFinalPaths]) {
            try {
                if (fileSystem.existsSync(outputPath)) {
                    fileSystem.unlinkSync(outputPath);
                }
            } catch {
                // 只保留原始失败；清理失败不得隐藏主错误或触碰任务前既有文件。
            }
        }
        if (error instanceof OfflineStagingError) {
            throw error;
        }
        throw new OfflineStagingError(
            'SAFETY_ERROR',
            'emit failed and staged output was rolled back: ' + error.message
        );
    }
    return Object.keys(files).sort();
}

function loadCandidatesForRun(candidatePath, dependencies = {}) {
    return candidatePath ? (dependencies.loadCandidates || loadCandidates)(candidatePath, dependencies) : [];
}

module.exports = {
    ADAPTER_MEDIA_TYPES,
    emitDeterministicResult,
    loadCandidatesForRun,
    resolveExternalEmitDirectory,
    runOfflineStaging,
};
