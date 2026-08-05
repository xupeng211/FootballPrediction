/* eslint-disable complexity, max-lines */
'use strict';

// lifecycle: permanent
//
// FotMob detail staging — offline source verification.
//
// Owns the VERIFIED_PACKAGE_RECEIPT binding model (PR1817 remediation,
// FINDING_3 / FINDING_4):
//
//   1. verifyArchive()          — live SHA-256 over the physical archive bytes,
//                                 compared against the source-index declared
//                                 value (never just "looks like 64 hex").
//   2. inspectArchive()         — minimal SAFE tar reader: no extraction,
//                                 no child_process; rejects absolute member
//                                 paths, ".." traversal, symlinks/hardlinks,
//                                 special files and corrupted headers;
//                                 returns per-member content SHA-256.
//   3. buildPackageReceipt()    — deterministic receipt binding archive SHA,
//                                 member checksums root, payload/manifest
//                                 member names and member hashes.
//   4. verifyPackageReceipt()   — receipt business-hash recomputation and
//                                 schema/binding validation (tamper closed).
//   5. verifyEntryAgainstReceipt() — one source-index entry is bound to ONE
//                                 package; the extracted payload/manifest
//                                 files' live SHA must equal the receipt's
//                                 member hashes; single-package rule.
//   6. Generic input path gates — verifyRepositoryExternalRegularFile /
//                                 verifyRepositoryExternalDirectory /
//                                 assertInputOutputNonOverlap (FINDING_4):
//                                 every input path is absolute, repository-
//                                 external, a regular file/dir, leaf and ALL
//                                 ancestors free of symlinks, and never
//                                 overlapping the output root.
//
// Zero network, zero database, zero capture, zero wall clock in business
// outputs. All reads are repository-external absolute paths only.

const path = require('node:path');
const fs = require('node:fs');
const crypto = require('node:crypto');
const zlib = require('node:zlib');

const { verifyRepositoryExternalPath, assertNoSymlinkAncestors } = require('./FotMobDetailStagingRetention');
const { canonicalJsonHash, sha256Hex } = require('./FotMobDetailCaptureContract');

const PACKAGE_RECEIPT_SCHEMA = 'fotmob-detail-staging-package-receipt/v1';

const TAR_BLOCK = 512;

// ─────────────────────────────────────────────────────────────
// Generic input path gates (FINDING_4)
// ─────────────────────────────────────────────────────────────

/**
 * Verify an INPUT path is absolute, outside the repository, exists, is a
 * regular file, is not a symlink, and has NO symlink ancestor. Leaf-only
 * checks are never enough: an intermediate symlinked directory could
 * redirect the read (or a later write) anywhere.
 *
 * @param {string} filePath - input file path
 * @param {object} options - { repositoryRoot, fsImpl }
 * @returns {string} resolved absolute path
 */
function verifyRepositoryExternalRegularFile(filePath, options = {}) {
    const fileSystem = options.fsImpl || fs;
    const abs = verifyRepositoryExternalPath(filePath, options);
    let stat = null;
    try {
        stat = fileSystem.lstatSync(abs);
    } catch {
        /* absent */
    }
    if (!stat) {
        throw Object.assign(new Error(`input file does not exist: ${abs}`), { code: 'SAFETY_ERROR' });
    }
    if (stat.isSymbolicLink() || !stat.isFile()) {
        throw Object.assign(new Error(`input must be a regular file (no symlinks): ${abs}`), { code: 'SAFETY_ERROR' });
    }
    return abs;
}

/**
 * Verify an input DIRECTORY is absolute, outside the repository, exists, is a
 * real directory (leaf + all ancestors free of symlinks).
 *
 * @param {string} dirPath - input directory path
 * @param {object} options - { repositoryRoot, fsImpl }
 * @returns {string} resolved absolute path
 */
function verifyRepositoryExternalDirectory(dirPath, options = {}) {
    const fileSystem = options.fsImpl || fs;
    const abs = verifyRepositoryExternalPath(dirPath, options);
    let stat = null;
    try {
        stat = fileSystem.lstatSync(abs);
    } catch {
        /* absent */
    }
    if (!stat || stat.isSymbolicLink() || !stat.isDirectory()) {
        throw Object.assign(new Error(`input must be a real directory (no symlinks): ${abs}`), {
            code: 'SAFETY_ERROR',
        });
    }
    return abs;
}

/**
 * Reject overlapping input/output relationships (FINDING_4):
 *   - the input must not be inside (or equal to) the output root — the
 *     output tree must never contain an input ("store contains input");
 *   - the output root must not EQUAL the input's own directory ("output
 *     equals input directory" / "input directory contains output") — a
 *     commit would write its store ledger next to the input, and the
 *     marker-based residue scan would classify the input as residue.
 *
 * A subdirectory of the input's directory is allowed (e.g. work/out next
 * to work/source-index.json): writes stay inside the subdirectory and
 * never touch the input.
 *
 * @param {string} inputFile - absolute input file path
 * @param {string} outputRoot - absolute output root path
 */
function assertInputOutputNonOverlap(inputFile, outputRoot) {
    const inputAbs = path.resolve(String(inputFile || ''));
    const outAbs = path.resolve(String(outputRoot || ''));
    const relInput = path.relative(outAbs, inputAbs);
    if (relInput === '' || (!relInput.startsWith('..') && !path.isAbsolute(relInput))) {
        throw Object.assign(new Error(`input must not be inside the output root: ${inputAbs}`), {
            code: 'SAFETY_ERROR',
        });
    }
    const relOut = path.relative(path.dirname(inputAbs), outAbs);
    if (relOut === '') {
        throw Object.assign(new Error(`output root must not equal the input's directory: ${inputAbs}`), {
            code: 'SAFETY_ERROR',
        });
    }
    return true;
}

// ─────────────────────────────────────────────────────────────
// Safe tar inspection (no extraction, no child_process)
// ─────────────────────────────────────────────────────────────

function parseOctal(bytes, offset, length) {
    let value = 0;
    for (let i = offset; i < offset + length; i += 1) {
        const ch = bytes[i];
        if (ch === 0 || ch === 32) continue; // NUL or space padding
        if (ch < 48 || ch > 55) return null; // not octal digit
        value = value * 8 + (ch - 48);
    }
    return value;
}

function parsePaxRecords(data) {
    const records = {};
    let idx = 0;
    while (idx < data.length) {
        const space = data.indexOf(' ', idx);
        if (space === -1) break;
        const len = Number(data.slice(idx, space));
        if (!Number.isFinite(len) || len <= 0) break;
        const record = data.slice(space + 1, idx + len - 1); // strip trailing newline
        const eq = record.indexOf('=');
        if (eq !== -1) {
            records[record.slice(0, eq)] = record.slice(eq + 1);
        }
        // The length field counts the whole record INCLUDING its own digits
        // and the space, so the next record starts exactly at idx + len
        // (idx = space + 1 + len would land past the first digit of the
        // following record and silently drop every later record).
        idx = idx + len;
    }
    return records;
}

function ustarName(header) {
    const name = header.subarray(0, 100).toString('utf8').replace(/\0.*$/, '');
    // ustar magic at 257..262 — if absent, prefix is not valid.
    const magic = header.subarray(257, 263).toString('utf8');
    if (magic !== 'ustar') return name;
    const prefix = header.subarray(345, 500).toString('utf8').replace(/\0.*$/, '');
    return prefix ? `${prefix}/${name}` : name;
}

function isSafeMemberName(name) {
    if (typeof name !== 'string' || name === '') return false;
    if (name.startsWith('/') || name.startsWith('\\')) return false;
    if (name.includes('\\')) return false;
    const normalized = path.posix.normalize(name);
    if (normalized === '..' || normalized.startsWith('../') || normalized.startsWith('/')) {
        return false;
    }
    return true;
}

/**
 * Safely inspect a gzipped tar archive: recompute member hashes from member
 * CONTENT without writing anything to disk. Rejects absolute paths, ".."
 * traversal, symlink/hardlink/special members, duplicate member names and
 * corrupted headers (checksum mismatch = tampered archive, fail closed).
 *
 * @param {string} archivePath - absolute repository-external archive path
 * @param {object} options - { repositoryRoot, fsImpl }
 * @returns {{ archive_sha256: string, members: Array<{name,size,sha256}> }}
 */
function inspectArchive(archivePath, options = {}) {
    const fileSystem = options.fsImpl || fs;
    const abs = verifyRepositoryExternalRegularFile(archivePath, options);
    const bytes = fileSystem.readFileSync(abs);
    const archiveSha256 = sha256Hex(bytes);

    let tar;
    try {
        tar = zlib.gunzipSync(bytes);
    } catch {
        throw Object.assign(new Error(`archive is not a valid gzip stream: ${abs}`), { code: 'INPUT_ERROR' });
    }

    const members = [];
    const seen = new Set();
    let offset = 0;
    let pendingLongName = null;
    let pendingPaxPath = null;

    while (offset + TAR_BLOCK <= tar.length) {
        const header = tar.subarray(offset, offset + TAR_BLOCK);
        if (header.every(b => b === 0)) break; // end-of-archive marker
        const storedChecksum = parseOctal(header, 148, 8);
        let sum = 0;
        for (let i = 0; i < TAR_BLOCK; i += 1) {
            sum += i >= 148 && i < 156 ? 32 : header[i];
        }
        if (storedChecksum === null || storedChecksum !== sum) {
            throw Object.assign(new Error(`tar header checksum mismatch (tampered archive): ${abs}`), {
                code: 'SAFETY_ERROR',
            });
        }
        const typeflag = String.fromCharCode(header[156]);
        const size = parseOctal(header, 124, 12) || 0;
        const paddedSize = Math.ceil(size / TAR_BLOCK) * TAR_BLOCK;
        const contentStart = offset + TAR_BLOCK;

        if (typeflag === 'L') {
            // GNU long name: the next data block holds the real name.
            pendingLongName = tar.subarray(contentStart, contentStart + size).toString('utf8');
            offset = contentStart + paddedSize;
            continue;
        }
        if (typeflag === 'x' || typeflag === 'g') {
            // PAX extended headers: path= may override the name; linkpath= means
            // a link target is being recorded — links are forbidden, fail closed.
            const pax = parsePaxRecords(tar.subarray(contentStart, contentStart + size).toString('utf8'));
            if (pax.linkpath !== undefined) {
                throw Object.assign(new Error(`tar member declares a link target (not allowed): ${abs}`), {
                    code: 'SAFETY_ERROR',
                });
            }
            if (pax.path !== undefined) pendingPaxPath = pax.path;
            offset = contentStart + paddedSize;
            continue;
        }
        if (typeflag === 'K') {
            throw Object.assign(new Error(`tar member declares a GNU long link (not allowed): ${abs}`), {
                code: 'SAFETY_ERROR',
            });
        }

        let name = pendingPaxPath || pendingLongName || ustarName(header);
        pendingLongName = null;
        pendingPaxPath = null;
        if (!isSafeMemberName(name)) {
            throw Object.assign(new Error(`unsafe tar member name: ${name}`), { code: 'SAFETY_ERROR' });
        }

        if (typeflag === '1' || typeflag === '2') {
            throw Object.assign(new Error(`tar member is a link (hardlink/symlink not allowed): ${name}`), {
                code: 'SAFETY_ERROR',
            });
        }
        if (['3', '4', '6', '7'].includes(typeflag)) {
            throw Object.assign(new Error(`tar member is a special file: ${name}`), { code: 'SAFETY_ERROR' });
        }
        if (typeflag === '5') {
            offset = contentStart + paddedSize; // directory entry — no content hash
            continue;
        }
        if (typeflag !== '0' && typeflag !== '\0') {
            throw Object.assign(new Error(`unsupported tar typeflag '${typeflag}': ${name}`), { code: 'SAFETY_ERROR' });
        }
        if (seen.has(name)) {
            throw Object.assign(new Error(`duplicate tar member name: ${name}`), { code: 'SAFETY_ERROR' });
        }
        seen.add(name);
        const content = tar.subarray(contentStart, contentStart + size);
        members.push({
            name,
            size,
            sha256: crypto.createHash('sha256').update(content).digest('hex'),
        });
        offset = contentStart + paddedSize;
    }

    return { archive_sha256: archiveSha256, members };
}

// ─────────────────────────────────────────────────────────────
// Verified package receipts
// ─────────────────────────────────────────────────────────────

/**
 * Live-verify an archive: regular file, repository-external, no symlink
 * ancestors, and its ACTUAL SHA-256 equals the declared value.
 *
 * @param {string} archivePath - absolute archive path
 * @param {string} expectedSha256 - declared 64-hex SHA-256
 * @param {object} options - { repositoryRoot, fsImpl }
 * @returns {{ archive_path, archive_sha256 }}
 */
function verifyArchive(archivePath, expectedSha256, options = {}) {
    const fileSystem = options.fsImpl || fs;
    const abs = verifyRepositoryExternalRegularFile(archivePath, options);
    if (!/^[0-9a-f]{64}$/.test(String(expectedSha256 || ''))) {
        throw Object.assign(new Error('expected archive sha256 must be 64 lowercase hex'), { code: 'INPUT_ERROR' });
    }
    const actual = sha256Hex(fileSystem.readFileSync(abs));
    if (actual !== String(expectedSha256).toLowerCase()) {
        throw Object.assign(new Error(`archive sha256 mismatch: declared ${expectedSha256}, actual ${actual}`), {
            code: 'SAFETY_ERROR',
        });
    }
    return { archive_path: abs, archive_sha256: actual };
}

/**
 * Build a deterministic package receipt from an inspected archive.
 *
 * @param {object} args - { packageId, archivePath, archiveSha256, members,
 *                          payloadMember, manifestMember }
 * @returns {object} receipt document with receipt_sha256 (business hash over
 *                   every field except receipt_sha256 itself)
 */
function buildPackageReceipt(args = {}) {
    const packageId = String(args.packageId || '');
    if (!/^[A-Za-z0-9._-]+$/.test(packageId)) {
        throw Object.assign(new Error('package id must be a plain identifier'), { code: 'INPUT_ERROR' });
    }
    const members = Array.isArray(args.members) ? args.members : [];
    const memberHashes = {};
    for (const member of members) {
        if (!member || typeof member.name !== 'string' || !isSafeMemberName(member.name)) {
            throw Object.assign(new Error(`invalid member name: ${member && member.name}`), { code: 'INPUT_ERROR' });
        }
        if (!/^[0-9a-f]{64}$/.test(String(member.sha256 || ''))) {
            throw Object.assign(new Error(`invalid member hash: ${member && member.name}`), { code: 'INPUT_ERROR' });
        }
        memberHashes[member.name] = member.sha256;
    }
    const payloadMember = String(args.payloadMember || '');
    const manifestMember = String(args.manifestMember || '');
    if (!memberHashes[payloadMember]) {
        throw Object.assign(new Error(`payload member not found in archive: ${payloadMember}`), {
            code: 'INPUT_ERROR',
        });
    }
    if (!memberHashes[manifestMember]) {
        throw Object.assign(new Error(`manifest member not found in archive: ${manifestMember}`), {
            code: 'INPUT_ERROR',
        });
    }
    if (!/^[0-9a-f]{64}$/.test(String(args.archiveSha256 || ''))) {
        throw Object.assign(new Error('archive sha256 must be 64 lowercase hex'), { code: 'INPUT_ERROR' });
    }
    const receipt = {
        schema_version: PACKAGE_RECEIPT_SCHEMA,
        package_id: packageId,
        archive_sha256: String(args.archiveSha256).toLowerCase(),
        archive_file: path.basename(String(args.archivePath || '')),
        payload_member: payloadMember,
        manifest_member: manifestMember,
        members: memberHashes,
    };
    // Business hash over everything except itself (same discipline as the
    // staging artifact business projection).
    receipt.receipt_sha256 = canonicalJsonHash(receipt);
    return receipt;
}

/**
 * Validate a package receipt document: schema, field formats, member binding,
 * and the receipt business hash recomputation (any tampering fails closed).
 *
 * @param {object} receipt - receipt document
 * @returns {{ ok: boolean, errors: string[], recomputed_receipt_sha256: string }}
 */
function verifyPackageReceipt(receipt) {
    const errors = [];
    if (!receipt || typeof receipt !== 'object') {
        return { ok: false, errors: ['receipt is not an object'], recomputed_receipt_sha256: '' };
    }
    if (receipt.schema_version !== PACKAGE_RECEIPT_SCHEMA) {
        errors.push(`receipt schema_version must be ${PACKAGE_RECEIPT_SCHEMA}`);
    }
    if (!/^[A-Za-z0-9._-]+$/.test(String(receipt.package_id || ''))) {
        errors.push('receipt package_id must be a plain identifier');
    }
    if (!/^[0-9a-f]{64}$/.test(String(receipt.archive_sha256 || ''))) {
        errors.push('receipt archive_sha256 must be 64 lowercase hex');
    }
    if (!receipt.members || typeof receipt.members !== 'object') {
        errors.push('receipt members must be an object');
    } else {
        for (const [name, hash] of Object.entries(receipt.members)) {
            if (!isSafeMemberName(name)) errors.push(`unsafe member name: ${name}`);
            if (!/^[0-9a-f]{64}$/.test(String(hash || ''))) {
                errors.push(`member hash must be 64 lowercase hex: ${name}`);
            }
        }
        for (const memberField of ['payload_member', 'manifest_member']) {
            if (!receipt.members[receipt[memberField]]) {
                errors.push(`receipt ${memberField} must reference an existing member`);
            }
        }
    }
    const recomputed = canonicalJsonHash(
        (() => {
            const copy = { ...receipt };
            delete copy.receipt_sha256;
            return copy;
        })()
    );
    if (recomputed !== String(receipt.receipt_sha256 || '')) {
        errors.push('receipt_sha256 does not match recomputed receipt business hash');
    }
    return { ok: errors.length === 0, errors, recomputed_receipt_sha256: recomputed };
}

/**
 * Bind ONE source-index entry to its package: the entry uses exactly ONE
 * package (single-package rule); the receipt must be valid; the receipt's
 * archive SHA must equal the binding's declared SHA; the archive must be
 * live-verified against that SHA; and the extracted payload/manifest files
 * must be safe inputs whose live SHA equals the receipt's member hashes.
 *
 * @param {object} args - { entry, binding, receipt, payloadFile, manifestFile,
 *                          outputRoot, options }
 * @returns {{ payload, manifest, payloadBytes, payloadFileSha256 }}
 */
function verifyEntryAgainstReceipt(args = {}) {
    const entry = args.entry || {};
    const binding = args.binding || {};
    const receipt = args.receipt || {};
    const outputRoot = args.outputRoot;
    const options = args.options || {};

    const packageId = String(entry.package || '');
    if (packageId === '') {
        throw Object.assign(new Error('entry has no package binding'), {
            code: 'SAFETY_ERROR',
        });
    }
    // NOTE: receipt.package_id is NOT required to equal the index binding key.
    // The receipt is built before the index that references it, so its
    // package_id is an independently chosen operator identifier; the binding
    // chain is the receipt FILE referenced by the binding, receipt archive SHA
    // == binding SHA, live archive verification, and live member hashes.
    // Requiring identifier equality would add no security (index and binding
    // live in the same document) and would reject legitimate workflows.
    // Receipt must be valid, and its archive SHA must equal the declared one.
    const receiptValidation = verifyPackageReceipt(receipt);
    if (!receiptValidation.ok) {
        throw Object.assign(new Error(`package receipt invalid: ${receiptValidation.errors.join('; ')}`), {
            code: 'SAFETY_ERROR',
        });
    }
    if (String(receipt.archive_sha256 || '') !== String(binding.sha256 || '')) {
        throw Object.assign(
            new Error(`receipt archive sha ${receipt.archive_sha256} does not match binding ${binding.sha256}`),
            { code: 'SAFETY_ERROR' }
        );
    }
    // Live-verify the archive itself against the declared SHA.
    verifyArchive(String(binding.path || ''), String(binding.sha256 || ''), options);

    // Extracted input files: safe + live SHA equals the receipt member SHA.
    const payloadAbs = verifyRepositoryExternalRegularFile(args.payloadFile, options);
    const manifestAbs = verifyRepositoryExternalRegularFile(args.manifestFile, options);
    if (outputRoot) {
        assertInputOutputNonOverlap(payloadAbs, outputRoot);
        assertInputOutputNonOverlap(manifestAbs, outputRoot);
    }
    const fileSystem = options.fsImpl || fs;
    const payloadBytes = fileSystem.readFileSync(payloadAbs);
    const manifestBytes = fileSystem.readFileSync(manifestAbs);
    const payloadSha = sha256Hex(payloadBytes);
    const manifestSha = sha256Hex(manifestBytes);
    if (payloadSha !== receipt.members[receipt.payload_member]) {
        throw Object.assign(
            new Error(
                `payload file sha256 ${payloadSha} does not match archive member ${receipt.payload_member} (${receipt.members[receipt.payload_member]})`
            ),
            { code: 'SAFETY_ERROR' }
        );
    }
    if (manifestSha !== receipt.members[receipt.manifest_member]) {
        throw Object.assign(
            new Error(
                `manifest file sha256 ${manifestSha} does not match archive member ${receipt.manifest_member} (${receipt.members[receipt.manifest_member]})`
            ),
            { code: 'SAFETY_ERROR' }
        );
    }
    const manifest = JSON.parse(manifestBytes.toString('utf8'));
    return {
        payload: JSON.parse(payloadBytes.toString('utf8')),
        manifest,
        payloadBytes,
        payloadFileSha256: payloadSha,
    };
}

module.exports = {
    PACKAGE_RECEIPT_SCHEMA,
    assertNoSymlinkAncestors,
    verifyRepositoryExternalRegularFile,
    verifyRepositoryExternalDirectory,
    assertInputOutputNonOverlap,
    parseOctal,
    parsePaxRecords,
    ustarName,
    isSafeMemberName,
    inspectArchive,
    verifyArchive,
    buildPackageReceipt,
    verifyPackageReceipt,
    verifyEntryAgainstReceipt,
};
