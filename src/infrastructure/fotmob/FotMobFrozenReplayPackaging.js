'use strict';

// lifecycle: permanent
// Offline-only packaging bridge for immutable FotMob frozen evidence.  This
// deliberately reuses the existing staging package receipt and source-index
// contracts; it does not introduce another replay format.

const crypto = require('node:crypto');
const fs = require('node:fs');
const path = require('node:path');
const zlib = require('node:zlib');

const { validateSourceIndex } = require('./FotMobDetailStagingContract');
const {
    assertNoSymlinkAncestors,
    ensureRealDirectoryTree,
    readFileSafeNoFollow,
    verifyRepositoryExternalPath,
    writeJsonAtomically,
} = require('./FotMobDetailStagingRetention');
const {
    verifyRepositoryExternalRegularFile,
    verifyArchive,
    inspectArchive,
    buildPackageReceipt,
} = require('./FotMobDetailStagingSourceVerification');

function sha256(bytes) {
    return crypto.createHash('sha256').update(bytes).digest('hex');
}

function fail(message, code = 'INPUT_ERROR') {
    throw Object.assign(new Error(message), { code });
}

function canonical(value) {
    return JSON.stringify(value, Object.keys(value).sort());
}

function safeId(value, label) {
    const result = String(value || '');
    if (!/^[A-Za-z0-9._-]+$/.test(result)) fail(`${label} must be a plain identifier`);
    return result;
}

function safeNumericId(value, label) {
    const result = String(value || '');
    if (!/^\d+$/.test(result)) fail(`${label} must be numeric`);
    return result;
}

function readJson(abs, repositoryRoot) {
    verifyRepositoryExternalRegularFile(abs, { repositoryRoot });
    const bytes = readFileSafeNoFollow(abs).bytes;
    try {
        return JSON.parse(bytes.toString('utf8'));
    } catch {
        fail(`invalid JSON input: ${abs}`);
    }
}

function readJsonl(abs, repositoryRoot) {
    verifyRepositoryExternalRegularFile(abs, { repositoryRoot });
    return readFileSafeNoFollow(abs).bytes
        .toString('utf8')
        .trim()
        .split('\n')
        .filter(Boolean)
        .map((line, index) => {
            try { return JSON.parse(line); } catch { fail(`invalid JSONL at ${abs}:${index + 1}`); }
        });
}

function tarHeader(name, size) {
    if (Buffer.byteLength(name, 'utf8') > 100) fail(`replay package member name too long: ${name}`);
    const header = Buffer.alloc(512);
    header.write(name, 0, 'utf8');
    header.write('0000644\0', 100, 'utf8');
    header.write('0000000\0', 108, 'utf8');
    header.write('0000000\0', 116, 'utf8');
    header.write(Number(size).toString(8).padStart(11, '0') + '\0', 124, 'utf8');
    header.write('00000000000\0', 136, 'utf8');
    header.write('0', 156, 'utf8');
    header.write('ustar\0', 257, 'utf8');
    header.write('00', 263, 'utf8');
    let sum = 0;
    for (let i = 0; i < 512; i += 1) sum += i >= 148 && i < 156 ? 32 : header[i];
    header.write(sum.toString(8).padStart(6, '0') + '\0 ', 148, 'utf8');
    return header;
}

function deterministicTarGz(members) {
    const blocks = [];
    for (const member of members) {
        blocks.push(tarHeader(member.name, member.bytes.length), member.bytes);
        const rest = member.bytes.length % 512;
        if (rest) blocks.push(Buffer.alloc(512 - rest));
    }
    blocks.push(Buffer.alloc(1024));
    return zlib.gzipSync(Buffer.concat(blocks), { mtime: 0 });
}

function writeExclusive(abs, bytes, repositoryRoot) {
    verifyRepositoryExternalPath(abs, { repositoryRoot });
    const dir = path.dirname(abs);
    ensureRealDirectoryTree(dir);
    assertNoSymlinkAncestors(dir);
    let fd;
    try {
        fd = fs.openSync(abs, 'wx', 0o600);
        fs.writeFileSync(fd, bytes);
        fs.fsyncSync(fd);
    } catch (error) {
        if (error && error.code === 'EEXIST') fail(`refusing to overwrite output: ${abs}`, 'OUTPUT_CONFLICT');
        throw error;
    } finally {
        if (fd !== undefined) fs.closeSync(fd);
    }
    return sha256(bytes);
}

function inputRows(input, repositoryRoot) {
    if (!input || input.schema_version !== 'fotmob-frozen-replay-package-input/v1') {
        fail('input schema_version must be fotmob-frozen-replay-package-input/v1');
    }
    if (!Array.isArray(input.entries) || input.entries.length === 0) fail('input entries must be non-empty');
    const byId = new Map();
    for (const entry of input.entries) {
        const sourceId = safeNumericId(entry.fotmob_match_id, 'fotmob_match_id');
        if (byId.has(sourceId)) fail(`duplicate input fotmob_match_id ${sourceId}`);
        const kind = String(entry.kind || '');
        if (!['EXISTING_PACKAGE', 'HISTORICAL_REUSE_LOOSE'].includes(kind)) fail(`unsupported input kind for ${sourceId}`);
        if (kind === 'HISTORICAL_REUSE_LOOSE' && entry.source_provenance !== 'HISTORICAL_REUSE') {
            fail(`loose historical entry ${sourceId} must preserve source_provenance=HISTORICAL_REUSE`);
        }
        for (const field of ['payload_path', 'manifest_path']) {
            verifyRepositoryExternalRegularFile(entry[field], { repositoryRoot });
        }
        byId.set(sourceId, { ...entry, fotmob_match_id: sourceId, kind });
    }
    return byId;
}

function assertDocumentBinding(row, payloadBytes, payload, manifest, expected) {
    if (sha256(payloadBytes) !== expected.raw_payload_sha256) fail(`payload SHA mismatch for ${row.fotmob_match_id}`, 'SAFETY_ERROR');
    if (String(payload.source_match_id) !== row.fotmob_match_id || String(manifest.source_match_id) !== row.fotmob_match_id) {
        fail(`payload/manifest source identity mismatch for ${row.fotmob_match_id}`, 'SAFETY_ERROR');
    }
    if (String(payload.candidate_id) !== expected.canonical_match_id || String(manifest.candidate_id) !== expected.canonical_match_id) {
        fail(`canonical identity mismatch for ${row.fotmob_match_id}`, 'SAFETY_ERROR');
    }
}

// The coordinator intentionally owns the complete fail-closed population
// ledger (input, identity, archive, receipt, materialization, output).  Keep
// those checks in one auditable transaction boundary rather than splitting
// them into helpers that could accidentally omit an accounting gate.
// eslint-disable-next-line complexity
function buildReplaySourceIndex(args = {}) {
    const repositoryRoot = path.resolve(args.repositoryRoot || path.resolve(__dirname, '..', '..', '..'));
    for (const field of ['freezePath', 'assetManifestPath', 'inputPath', 'outputRoot']) {
        if (!args[field]) fail(`missing ${field}`);
        verifyRepositoryExternalPath(args[field], { repositoryRoot });
    }
    const outputRoot = path.resolve(args.outputRoot);
    if (fs.existsSync(outputRoot)) fail(`output root already exists: ${outputRoot}`, 'OUTPUT_CONFLICT');
    const freeze = readJson(args.freezePath, repositoryRoot);
    const assets = readJsonl(args.assetManifestPath, repositoryRoot);
    const input = readJson(args.inputPath, repositoryRoot);
    const supplied = inputRows(input, repositoryRoot);
    if (Number(freeze.raw_payload_count) !== assets.length || assets.length !== supplied.size) {
        fail(`population mismatch: freeze=${freeze.raw_payload_count} assets=${assets.length} supplied=${supplied.size}`);
    }
    const rows = [...assets].sort((a, b) => String(a.fotmob_match_id).localeCompare(String(b.fotmob_match_id), 'en'));
    const seenCanonical = new Set();
    const archives = new Map();
    const loose = [];
    const prepared = [];
    for (const expected of rows) {
        const sourceId = safeNumericId(expected.fotmob_match_id, 'asset fotmob_match_id');
        if (seenCanonical.has(expected.canonical_match_id)) fail(`duplicate canonical_match_id ${expected.canonical_match_id}`);
        seenCanonical.add(expected.canonical_match_id);
        const row = supplied.get(sourceId);
        if (!row) fail(`missing expected input ${sourceId}`);
        if (String(row.canonical_match_id) !== expected.canonical_match_id) fail(`input canonical ID mismatch for ${sourceId}`);
        const payload = readFileSafeNoFollow(row.payload_path).bytes;
        const manifestBytes = readFileSafeNoFollow(row.manifest_path).bytes;
        let manifest;
        try { manifest = JSON.parse(manifestBytes.toString('utf8')); } catch { fail(`invalid manifest JSON for ${sourceId}`); }
        let payloadDoc;
        try { payloadDoc = JSON.parse(payload.toString('utf8')); } catch { fail(`invalid payload JSON for ${sourceId}`); }
        assertDocumentBinding(row, payload, payloadDoc, manifest, expected);
        // Reassign raw bytes after semantic binding; all source-index hashes bind physical files.
        const packageId = row.kind === 'HISTORICAL_REUSE_LOOSE' ? 'historical-reuse-replay' : safeId(row.package_id, 'package_id');
        prepared.push({ expected, row, packageId, payloadBytes: payload, manifestBytes, payloadDoc, manifest });
        if (row.kind === 'HISTORICAL_REUSE_LOOSE') loose.push(prepared[prepared.length - 1]);
    }
    for (const sourceId of supplied.keys()) {
        if (!rows.some(row => String(row.fotmob_match_id) === sourceId)) fail(`extra input entry ${sourceId}`);
    }
    ensureRealDirectoryTree(outputRoot);
    const looseMembers = [];
    for (const item of loose) {
        item.payloadMember = `pairs/${item.row.fotmob_match_id}.payload.json`;
        item.manifestMember = `pairs/${item.row.fotmob_match_id}.manifest.json`;
        looseMembers.push({ name: item.payloadMember, bytes: item.payloadBytes }, { name: item.manifestMember, bytes: item.manifestBytes });
    }
    if (loose.length) {
        const archivePath = path.join(outputRoot, 'packages', 'historical-reuse-replay.tar.gz');
        writeExclusive(archivePath, deterministicTarGz(looseMembers), repositoryRoot);
        const archiveSha = sha256(readFileSafeNoFollow(archivePath).bytes);
        const inspected = inspectArchive(archivePath, { repositoryRoot });
        verifyArchive(archivePath, archiveSha, { repositoryRoot });
        archives.set('historical-reuse-replay', { path: archivePath, sha256: archiveSha, members: inspected.members, first: loose[0] });
    }
    for (const item of prepared.filter(value => value.row.kind === 'EXISTING_PACKAGE')) {
        const id = item.packageId;
        if (!archives.has(id)) {
            const archivePath = item.row.archive_path;
            verifyRepositoryExternalRegularFile(archivePath, { repositoryRoot });
            const archiveSha = String(item.row.archive_sha256 || '');
            verifyArchive(archivePath, archiveSha, { repositoryRoot });
            archives.set(id, { path: archivePath, sha256: archiveSha, members: inspectArchive(archivePath, { repositoryRoot }).members, first: item });
        }
        item.payloadMember = String(item.row.payload_member || '');
        item.manifestMember = String(item.row.manifest_member || '');
        const names = new Map(archives.get(id).members.map(member => [member.name, member.sha256]));
        if (names.get(item.payloadMember) !== sha256(item.payloadBytes) || names.get(item.manifestMember) !== sha256(item.manifestBytes)) {
            fail(`archive member binding mismatch for ${item.row.fotmob_match_id}`, 'SAFETY_ERROR');
        }
    }
    const archiveBindings = {};
    for (const [id, archive] of [...archives.entries()].sort(([a], [b]) => a.localeCompare(b, 'en'))) {
        const receipt = buildPackageReceipt({
            packageId: id,
            archivePath: archive.path,
            archiveSha256: archive.sha256,
            members: archive.members,
            payloadMember: archive.first.payloadMember,
            manifestMember: archive.first.manifestMember,
        });
        const receiptPath = path.join(outputRoot, 'receipts', `${id}.verified-package-receipt.json`);
        writeJsonAtomically(receiptPath, receipt, { repositoryRoot });
        archiveBindings[id] = { sha256: archive.sha256, path: archive.path, receipt: receiptPath };
    }
    const entries = [];
    for (const item of prepared) {
        const payloadPath = path.join(outputRoot, 'materialized', `${item.row.fotmob_match_id}.payload.json`);
        const manifestPath = path.join(outputRoot, 'materialized', `${item.row.fotmob_match_id}.manifest.json`);
        writeExclusive(payloadPath, item.payloadBytes, repositoryRoot);
        writeExclusive(manifestPath, item.manifestBytes, repositoryRoot);
        entries.push({
            source_match_id: item.row.fotmob_match_id,
            payload_file: payloadPath,
            manifest_file: manifestPath,
            payload_file_sha256: sha256(item.payloadBytes),
            manifest_file_sha256: sha256(item.manifestBytes),
            package: item.packageId,
            payload_member: item.payloadMember,
            manifest_member: item.manifestMember,
        });
    }
    const sourceIndex = { schema_version: 'fotmob-detail-source-index/v1', source_provider: 'FotMob', archive_bindings: archiveBindings, entries };
    const validation = validateSourceIndex(sourceIndex);
    if (!validation.ok) fail(`generated source index violates staging contract: ${validation.errors.join('; ')}`, 'INTERNAL_ERROR');
    const sourceIndexPath = path.join(outputRoot, 'fotmob-detail-source-index.json');
    writeJsonAtomically(sourceIndexPath, sourceIndex, { repositoryRoot });
    const summary = {
        schema_version: 'fotmob-frozen-replay-package-receipt/v1',
        source_provenance: 'HISTORICAL_REUSE',
        packaging_provenance: 'CURRENT_OFFLINE_REPLAY_PACKAGING',
        target_count: rows.length,
        existing_packaged_count: prepared.length - loose.length,
        newly_packaged_historical_reuse_count: loose.length,
        source_index_sha256: sha256(readFileSafeNoFollow(sourceIndexPath).bytes),
        source_index_path: sourceIndexPath,
        source_ids_sha256: sha256(Buffer.from(canonical(entries.map(entry => entry.source_match_id)), 'utf8')),
        offline_only: true,
        zero_network: true,
        zero_database: true,
    };
    writeJsonAtomically(path.join(outputRoot, 'replay-packaging-receipt.json'), summary, { repositoryRoot });
    return { sourceIndexPath, summary, sourceIndex };
}

module.exports = { buildReplaySourceIndex, deterministicTarGz, sha256 };
