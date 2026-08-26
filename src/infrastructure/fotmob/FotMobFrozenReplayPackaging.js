'use strict';

// Immutable offline evidence bridge. All authority/input validation precedes
// creation of a private temporary output tree; a directory rename publishes it.
const crypto = require('node:crypto');
const fs = require('node:fs');
const path = require('node:path');
const zlib = require('node:zlib');
const { validateSourceIndex, validateObservation } = require('./FotMobDetailStagingContract');
const { assertNoSymlinkAncestors, ensureRealDirectoryTree, readFileSafeNoFollow, verifyRepositoryExternalPath, writeJsonAtomically } = require('./FotMobDetailStagingRetention');
const { verifyRepositoryExternalRegularFile, verifyArchive, inspectArchive, buildPackageReceipt } = require('./FotMobDetailStagingSourceVerification');
const { validateFotMobFreezeDocument, validateFotMobManifestRows } = require('../golden_dataset/GdA01AssemblyContract');

const sha256 = bytes => crypto.createHash('sha256').update(bytes).digest('hex');
const GENERATED_HISTORICAL_REUSE_PACKAGE_ID = 'historical-reuse-replay';
function fail(message, code = 'INPUT_ERROR') { throw Object.assign(new Error(message), { code }); }
function safeId(value, label) { const v = String(value || ''); if (!/^[A-Za-z0-9._-]+$/.test(v)) fail(`${label} must be a plain identifier`); return v; }
function safeNumericId(value, label) { const v = String(value || ''); if (!/^\d+$/.test(v)) fail(`${label} must be numeric`); return v; }
function readJson(abs, repositoryRoot, label) {
    verifyRepositoryExternalRegularFile(abs, { repositoryRoot });
    const binding = readFileSafeNoFollow(abs);
    try { return { path: path.resolve(abs), bytes: binding.bytes, value: JSON.parse(binding.bytes.toString('utf8')) }; }
    catch { fail(`invalid JSON ${label}: ${abs}`); }
}
function readJsonl(abs, repositoryRoot) {
    verifyRepositoryExternalRegularFile(abs, { repositoryRoot });
    const binding = readFileSafeNoFollow(abs); const lines = binding.bytes.toString('utf8').split('\n');
    if (lines.at(-1) === '') lines.pop(); if (!lines.length) fail('asset manifest must not be empty');
    const rows = lines.map((line, index) => { if (!line.trim()) fail(`asset manifest blank line ${index + 1}`); try { return JSON.parse(line); } catch { fail(`invalid JSONL at ${abs}:${index + 1}`); } });
    return { path: path.resolve(abs), bytes: binding.bytes, rows };
}
function tarHeader(name, size) {
    if (Buffer.byteLength(name) > 100) fail(`replay package member name too long: ${name}`);
    const h = Buffer.alloc(512); h.write(name); h.write('0000644\0', 100); h.write('0000000\0', 108); h.write('0000000\0', 116); h.write(Number(size).toString(8).padStart(11, '0') + '\0', 124); h.write('00000000000\0', 136); h.write('0', 156); h.write('ustar\0', 257); h.write('00', 263);
    let sum = 0; for (let i = 0; i < 512; i += 1) sum += i >= 148 && i < 156 ? 32 : h[i]; h.write(sum.toString(8).padStart(6, '0') + '\0 ', 148); return h;
}
function deterministicTarGz(members) { const blocks = []; for (const m of members) { blocks.push(tarHeader(m.name, m.bytes.length), m.bytes); const rest = m.bytes.length % 512; if (rest) blocks.push(Buffer.alloc(512 - rest)); } blocks.push(Buffer.alloc(1024)); return zlib.gzipSync(Buffer.concat(blocks), { mtime: 0 }); }
function writeExclusive(abs, bytes, repositoryRoot) { verifyRepositoryExternalPath(abs, { repositoryRoot }); const dir = path.dirname(abs); ensureRealDirectoryTree(dir); assertNoSymlinkAncestors(dir); let fd; try { fd = fs.openSync(abs, 'wx', 0o600); fs.writeFileSync(fd, bytes); fs.fsyncSync(fd); } catch (e) { if (e.code === 'EEXIST') fail(`refusing to overwrite output: ${abs}`, 'OUTPUT_CONFLICT'); throw e; } finally { if (fd !== undefined) fs.closeSync(fd); } return sha256(bytes); }
function within(child, root) { const r = path.relative(root, child); return r === '' || (!r.startsWith('..') && !path.isAbsolute(r)); }
function canonicalPath(abs) {
    let candidate = path.resolve(abs);
    const suffix = [];
    let resolved = false;
    while (!resolved) {
        try {
            const real = fs.realpathSync.native(candidate);
            candidate = path.join(real, ...suffix.reverse());
            resolved = true;
        } catch (error) {
            if (error.code !== 'ENOENT' && error.code !== 'ENOTDIR') throw error;
            const parent = path.dirname(candidate);
            if (parent === candidate) return candidate;
            suffix.push(path.basename(candidate));
            candidate = parent;
        }
    }
    return candidate;
}
function assertOutputIsolation(outputRoot, protectedFiles, repositoryRoot) {
    const out = verifyRepositoryExternalPath(outputRoot, { repositoryRoot });
    const canonicalOut = canonicalPath(out);
    for (const file of protectedFiles) {
        const evidenceRoot = canonicalPath(path.dirname(path.resolve(file)));
        if (within(canonicalOut, evidenceRoot) || within(evidenceRoot, canonicalOut)) {
            fail(`output root overlaps immutable evidence tree: ${out} <-> ${evidenceRoot}`, 'SAFETY_ERROR');
        }
    }
    return out;
}
// eslint-disable-next-line complexity
function inputRows(input, repositoryRoot) {
    if (!input || input.schema_version !== 'fotmob-frozen-replay-package-input/v1') fail('input schema_version must be fotmob-frozen-replay-package-input/v1'); if (!Array.isArray(input.entries) || !input.entries.length) fail('input entries must be non-empty');
    const byId = new Map();
    for (const entry of input.entries) { const id = safeNumericId(entry.fotmob_match_id, 'fotmob_match_id'); if (byId.has(id)) fail(`duplicate input fotmob_match_id ${id}`); const kind = String(entry.kind || ''); if (!['EXISTING_PACKAGE', 'HISTORICAL_REUSE_LOOSE'].includes(kind)) fail(`unsupported input kind for ${id}`); if (kind === 'HISTORICAL_REUSE_LOOSE' && entry.source_provenance !== 'HISTORICAL_REUSE') fail(`loose historical entry ${id} must preserve source_provenance=HISTORICAL_REUSE`); for (const f of ['payload_path', 'manifest_path']) verifyRepositoryExternalRegularFile(entry[f], { repositoryRoot }); if (kind === 'EXISTING_PACKAGE') { safeId(entry.package_id, 'package_id'); if (!/^[a-f0-9]{64}$/i.test(String(entry.archive_sha256 || ''))) fail(`existing package ${id} archive_sha256 invalid`); verifyRepositoryExternalRegularFile(entry.archive_path, { repositoryRoot }); if (!entry.payload_member || !entry.manifest_member) fail(`existing package ${id} archive member binding missing`); } byId.set(id, { ...entry, fotmob_match_id: id, kind }); }
    return byId;
}
function archiveGroups(rows, repositoryRoot) {
    const groups = new Map(); const packageByCanonicalArchivePath = new Map();
    for (const row of rows.values()) {
        if (row.kind !== 'EXISTING_PACKAGE') continue;
        const id = safeId(row.package_id, 'package_id');
        if (id === GENERATED_HISTORICAL_REUSE_PACKAGE_ID) fail(`existing package_id reserves generated package namespace: ${id}`, 'SAFETY_ERROR');
        const archivePath = verifyRepositoryExternalRegularFile(row.archive_path, { repositoryRoot });
        const canonicalArchivePath = fs.realpathSync.native(archivePath);
        const priorPackageId = packageByCanonicalArchivePath.get(canonicalArchivePath);
        if (priorPackageId && priorPackageId !== id) fail(`canonical archive path is already bound to package_id ${priorPackageId}: ${canonicalArchivePath}`, 'SAFETY_ERROR');
        packageByCanonicalArchivePath.set(canonicalArchivePath, id);
        const b = { path: archivePath, canonicalPath: canonicalArchivePath, sha256: row.archive_sha256.toLowerCase() };
        const old = groups.get(id);
        if (old && (old.canonicalPath !== b.canonicalPath || old.sha256 !== b.sha256)) fail(`conflicting archive binding for package_id ${id}`, 'SAFETY_ERROR');
        groups.set(id, b);
    }
    return groups;
}
function registerArchiveBinding(archives, packageId, archive) {
    const existing = archives.get(packageId);
    if (!existing) { archives.set(packageId, archive); return; }
    if (existing.path !== archive.path || existing.sha256 !== archive.sha256) {
        fail(`duplicate archive binding for package_id ${packageId}`, 'SAFETY_ERROR');
    }
}
function candidate(payload) { return { id: String(payload.candidate_id || ''), source_match_id: String(payload.source_match_id || ''), source_provider: String(payload.source_provider || ''), competition: String(payload.competition || ''), season: String(payload.season || ''), home_team: String(payload.expected_identity?.home_team || ''), away_team: String(payload.expected_identity?.away_team || ''), kickoff_at: String(payload.expected_identity?.kickoff_at || '') }; }
function ownedCleanup(tempRoot, parent) { if (!tempRoot || path.dirname(tempRoot) !== parent || !path.basename(tempRoot).startsWith('.')) return; try { fs.rmSync(tempRoot, { recursive: true, force: true, maxRetries: 1 }); } catch { /* only our mkdtemp root */ } }

// eslint-disable-next-line complexity
function buildReplaySourceIndex(args = {}) {
    const repositoryRoot = path.resolve(args.repositoryRoot || path.resolve(__dirname, '..', '..', '..'));
    for (const f of ['freezePath', 'assetManifestPath', 'inputPath', 'outputRoot']) if (!args[f]) fail(`missing ${f}`);
    const freezeBinding = readJson(args.freezePath, repositoryRoot, 'freeze'); let freeze; try { freeze = validateFotMobFreezeDocument(freezeBinding.value); } catch (e) { fail(`invalid authoritative freeze: ${e.message}`, e.code || 'SAFETY_ERROR'); }
    const assets = readJsonl(args.assetManifestPath, repositoryRoot); if (sha256(assets.bytes) !== freeze.manifest_sha256) fail('asset manifest SHA-256 differs from authoritative freeze', 'SAFETY_ERROR');
    const inputBinding = readJson(args.inputPath, repositoryRoot, 'input'); const supplied = inputRows(inputBinding.value, repositoryRoot);
    if (assets.rows.length !== freeze.raw_payload_count || supplied.size !== freeze.raw_payload_count) fail(`population mismatch: freeze=${freeze.raw_payload_count} assets=${assets.rows.length} supplied=${supplied.size}`);
    const groupedArchives = archiveGroups(supplied, repositoryRoot); const protectedFiles = [freezeBinding.path, assets.path, inputBinding.path]; for (const row of supplied.values()) { protectedFiles.push(row.payload_path, row.manifest_path); if (row.kind === 'EXISTING_PACKAGE') protectedFiles.push(row.archive_path); }
    const outputRoot = assertOutputIsolation(path.resolve(args.outputRoot), protectedFiles, repositoryRoot); if (fs.existsSync(outputRoot)) fail(`output root already exists: ${outputRoot}`, 'OUTPUT_CONFLICT');
    const rows = [...assets.rows].sort((a, b) => String(a.fotmob_match_id).localeCompare(String(b.fotmob_match_id), 'en')); const seen = new Set(); const prepared = []; const candidateById = new Map();
    for (const expected of rows) { const id = safeNumericId(expected.fotmob_match_id, 'asset fotmob_match_id'); if (seen.has(id)) fail(`duplicate asset fotmob_match_id ${id}`); seen.add(id); const row = supplied.get(id); if (!row) fail(`missing expected input ${id}`); if (String(row.canonical_match_id) !== expected.canonical_match_id) fail(`input canonical ID mismatch for ${id}`); const payload = readJson(row.payload_path, repositoryRoot, `payload ${id}`); const manifest = readJson(row.manifest_path, repositoryRoot, `manifest ${id}`); const observation = validateObservation({ payload: payload.value, manifest: manifest.value, payloadBytes: payload.bytes }); if (!observation.ok) fail(`staging observation contract rejected ${id}: ${observation.errors.map(e => e.message).join('; ')}`, 'SAFETY_ERROR'); if (sha256(payload.bytes) !== expected.raw_payload_sha256) fail(`payload SHA mismatch for ${id}`, 'SAFETY_ERROR'); if (String(payload.value.source_match_id) !== id || String(manifest.value.source_match_id) !== id) fail(`payload/manifest source identity mismatch for ${id}`, 'SAFETY_ERROR'); if (String(payload.value.candidate_id) !== expected.canonical_match_id || String(manifest.value.candidate_id) !== expected.canonical_match_id) fail(`canonical identity mismatch for ${id}`, 'SAFETY_ERROR'); const c = candidate(payload.value); if (candidateById.has(c.id)) fail(`duplicate candidate identity ${c.id}`, 'SAFETY_ERROR'); candidateById.set(c.id, c); prepared.push({ expected, row, packageId: row.kind === 'HISTORICAL_REUSE_LOOSE' ? GENERATED_HISTORICAL_REUSE_PACKAGE_ID : safeId(row.package_id, 'package_id'), payloadBytes: payload.bytes, manifestBytes: manifest.bytes }); }
    if (seen.size !== supplied.size) fail('extra input entry not present in authoritative asset manifest', 'SAFETY_ERROR'); try { validateFotMobManifestRows(assets.rows, freeze, candidateById); } catch (e) { fail(`authoritative asset manifest contract rejected: ${e.message}`, e.code || 'SAFETY_ERROR'); }
    const parent = path.dirname(outputRoot); ensureRealDirectoryTree(parent); let tempRoot;
    try {
        tempRoot = fs.mkdtempSync(path.join(parent, `.${path.basename(outputRoot)}.tmp-`)); ensureRealDirectoryTree(tempRoot);
        const loose = prepared.filter(x => x.row.kind === 'HISTORICAL_REUSE_LOOSE'); const archives = new Map();
        if (loose.length) { const members = loose.flatMap(x => { x.payloadMember = `pairs/${x.row.fotmob_match_id}.payload.json`; x.manifestMember = `pairs/${x.row.fotmob_match_id}.manifest.json`; return [{ name: x.payloadMember, bytes: x.payloadBytes }, { name: x.manifestMember, bytes: x.manifestBytes }]; }); const rel = `packages/${GENERATED_HISTORICAL_REUSE_PACKAGE_ID}.tar.gz`; const tempArchive = path.join(tempRoot, rel); const bytes = deterministicTarGz(members); writeExclusive(tempArchive, bytes, repositoryRoot); const hash = sha256(bytes); verifyArchive(tempArchive, hash, { repositoryRoot }); registerArchiveBinding(archives, GENERATED_HISTORICAL_REUSE_PACKAGE_ID, { path: path.join(outputRoot, rel), sha256: hash, members: inspectArchive(tempArchive, { repositoryRoot }).members, first: loose[0] }); }
        for (const [id, binding] of groupedArchives) { verifyArchive(binding.path, binding.sha256, { repositoryRoot }); registerArchiveBinding(archives, id, { ...binding, members: inspectArchive(binding.path, { repositoryRoot }).members, first: null }); }
        for (const item of prepared.filter(x => x.row.kind === 'EXISTING_PACKAGE')) { item.payloadMember = String(item.row.payload_member); item.manifestMember = String(item.row.manifest_member); const names = new Map(archives.get(item.packageId).members.map(m => [m.name, m.sha256])); if (names.get(item.payloadMember) !== sha256(item.payloadBytes) || names.get(item.manifestMember) !== sha256(item.manifestBytes)) fail(`archive member binding mismatch for ${item.row.fotmob_match_id}`, 'SAFETY_ERROR'); if (!archives.get(item.packageId).first) archives.get(item.packageId).first = item; }
        const archiveBindings = {}; for (const [id, archive] of [...archives].sort(([a], [b]) => a.localeCompare(b, 'en'))) { const receipt = buildPackageReceipt({ packageId: id, archivePath: archive.path, archiveSha256: archive.sha256, members: archive.members, payloadMember: archive.first.payloadMember, manifestMember: archive.first.manifestMember }); const rel = `receipts/${id}.verified-package-receipt.json`; writeJsonAtomically(path.join(tempRoot, rel), receipt, { repositoryRoot }); archiveBindings[id] = { sha256: archive.sha256, path: archive.path, receipt: path.join(outputRoot, rel) }; }
        const entries = prepared.map(item => { const pr = `materialized/${item.row.fotmob_match_id}.payload.json`; const mr = `materialized/${item.row.fotmob_match_id}.manifest.json`; writeExclusive(path.join(tempRoot, pr), item.payloadBytes, repositoryRoot); writeExclusive(path.join(tempRoot, mr), item.manifestBytes, repositoryRoot); return { source_match_id: item.row.fotmob_match_id, payload_file: path.join(outputRoot, pr), manifest_file: path.join(outputRoot, mr), payload_file_sha256: sha256(item.payloadBytes), manifest_file_sha256: sha256(item.manifestBytes), package: item.packageId, payload_member: item.payloadMember, manifest_member: item.manifestMember }; });
        const sourceIndex = { schema_version: 'fotmob-detail-source-index/v1', source_provider: 'FotMob', archive_bindings: archiveBindings, entries }; const indexValidation = validateSourceIndex(sourceIndex); if (!indexValidation.ok) fail(`generated source index violates staging contract: ${indexValidation.errors.join('; ')}`, 'INTERNAL_ERROR'); const indexRel = 'fotmob-detail-source-index.json'; const tempIndex = path.join(tempRoot, indexRel); writeJsonAtomically(tempIndex, sourceIndex, { repositoryRoot }); const summary = { schema_version: 'fotmob-frozen-replay-package-receipt/v1', source_provenance: 'HISTORICAL_REUSE', packaging_provenance: 'CURRENT_OFFLINE_REPLAY_PACKAGING', target_count: rows.length, existing_packaged_count: prepared.length - loose.length, newly_packaged_historical_reuse_count: loose.length, source_index_sha256: sha256(readFileSafeNoFollow(tempIndex).bytes), source_index_path: path.join(outputRoot, indexRel), source_ids_sha256: sha256(Buffer.from(JSON.stringify(entries.map(x => x.source_match_id)), 'utf8')), offline_only: true, zero_network: true, zero_database: true }; writeJsonAtomically(path.join(tempRoot, 'replay-packaging-receipt.json'), summary, { repositoryRoot }); if (fs.existsSync(outputRoot)) fail(`output root already exists: ${outputRoot}`, 'OUTPUT_CONFLICT'); fs.renameSync(tempRoot, outputRoot); tempRoot = null; return { sourceIndexPath: path.join(outputRoot, indexRel), summary, sourceIndex };
    } finally { ownedCleanup(tempRoot, parent); }
}
module.exports = { buildReplaySourceIndex, deterministicTarGz, sha256, assertOutputIsolation };
