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

const {
    verifyRepositoryExternalPath,
    assertNoSymlinkAncestors,
    readFileSafeNoFollow,
} = require('./FotMobDetailStagingRetention');
const { canonicalJsonHash, sha256Hex } = require('./FotMobDetailCaptureContract');

const PACKAGE_RECEIPT_SCHEMA = 'fotmob-detail-staging-package-receipt/v1';

const TAR_BLOCK = 512;

// R1-P0-1 / R2-P0-1 (Codex rounds 1-2): a live inspection result may be
// reused ONLY if it came from this module's own live verification in this
// run. R1's enumerable Symbol property was forgeable by object spread
// (`{ ...live, members: [...] }` copied the symbol), so round 2 hardened
// this to unforgeable OBJECT IDENTITY: the registry is a module-private
// WeakSet, and every registered inspection is deep-frozen (top object +
// members array + each member row), so a spread copy is a different object
// (not in the set -> rejected) and in-place member replacement is
// impossible. A fabricated {members:[...]} table can never satisfy either.
const liveVerifyRegistry = new WeakSet();

function deepFreezeInspection(inspected) {
    for (const member of inspected.members) Object.freeze(member);
    Object.freeze(inspected.members);
    Object.freeze(inspected);
    return inspected;
}

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
    let sawDigit = false;
    for (let i = offset; i < offset + length; i += 1) {
        const ch = bytes[i];
        if (ch === 0 || ch === 32) continue; // NUL or space padding
        if (ch < 48 || ch > 55) return null; // not octal digit
        sawDigit = true;
        value = value * 8 + (ch - 48);
    }
    // R1-P2-1 (Codex round 1): an all-NUL/space field is NOT "size 0" — a
    // numeric field must contain at least one octal digit. Returning null
    // lets the size consumer fail closed (invalid octal) instead of
    // accepting an empty size field as a zero-byte member.
    return sawDigit ? value : null;
}

/**
 * Strict PAX record parser (P2-1, Codex review 4863122944): every record is
 * `<len> <key>=<value>\n` where len counts the ENTIRE record including its
 * own digits. Any malformed record — non-integer length, length out of the
 * data bounds, missing trailing newline — is a FAIL-CLOSED rejection, never
 * a silent skip (a skipped record could smuggle a path override).
 */
function parsePaxRecords(data) {
    // R11-P3-3 (Codex round 11): PAX lengths are defined in BYTES, but the
    // previous implementation decoded the whole block to a UTF-8 string and
    // measured with string.length (UTF-16 code units) — a legal non-ASCII
    // path (e.g. `16 path=é.json\n`: 16 bytes, 15 UTF-16 units) was wrongly
    // rejected as out of bounds. Records are now split at BYTE boundaries on
    // the Buffer (data is a Buffer, not a string) and each record is decoded
    // separately, so the length math is byte-accurate.
    // A string input (direct unit tests) is converted to bytes; the
    // production call site passes a Buffer slice.
    const bytes = typeof data === 'string' ? Buffer.from(data, 'utf8') : data;
    const records = {};
    let idx = 0;
    while (idx < bytes.length) {
        const space = bytes.indexOf(0x20, idx); // ' '
        if (space === -1) {
            throw Object.assign(new Error('PAX record missing length separator'), { code: 'SAFETY_ERROR' });
        }
        const digits = bytes.subarray(idx, space).toString('utf8');
        if (!/^[0-9]+$/.test(digits)) {
            throw Object.assign(new Error('PAX record length is not a positive integer'), { code: 'SAFETY_ERROR' });
        }
        const len = Number(digits);
        if (len <= 0 || len > bytes.length - idx) {
            throw Object.assign(new Error('PAX record length out of bounds'), { code: 'SAFETY_ERROR' });
        }
        if (bytes[idx + len - 1] !== 0x0a) {
            throw Object.assign(new Error('PAX record must end with a newline'), { code: 'SAFETY_ERROR' });
        }
        const record = bytes.subarray(space + 1, idx + len - 1).toString('utf8');
        const eq = record.indexOf('=');
        if (eq !== -1) {
            records[record.slice(0, eq)] = record.slice(eq + 1);
        }
        // The length field counts the whole record INCLUDING its own digits
        // and the space, so the next record starts exactly at idx + len.
        idx = idx + len;
    }
    return records;
}

function ustarName(header) {
    const name = header.subarray(0, 100).toString('utf8').replace(/\0.*$/, '');
    // P1-1 (Codex review 4863122944): the ustar magic at 257..262 is SIX
    // bytes — standard ustar is `ustar\0`, GNU tar writes `ustar ` (space).
    // Comparing against the five-byte string 'ustar' never matched, which
    // silently DISABLED the prefix check (a prefix=../ traversal could be
    // smuggled through the 155-byte prefix field). Both magic variants now
    // enable prefix processing, and the COMBINED name is validated.
    const magic = header.subarray(257, 263).toString('utf8');
    if (magic !== 'ustar\0' && magic !== 'ustar ') return name;
    const prefix = header.subarray(345, 500).toString('utf8').replace(/\0.*$/, '');
    return prefix ? `${prefix}/${name}` : name;
}

/**
 * Two-level member-name safety (P1-1):
 *   1. RAW semantics — every original path segment (including the ustar
 *      prefix and the GNU/PAX override) must be free of `..` segments, NUL
 *      bytes, backslashes and absolute-path escapes;
 *   2. COMBINED normalized path — after prefix+name (or PAX/GNU override)
 *      composition, the normalized POSIX path must stay inside the archive
 *      root (no `..`, no leading `/`) and must not be empty.
 *
 * @param {string} name - final combined member path
 * @param {Array<string>} rawParts - original uncombined path strings
 * @returns {boolean} true when safe
 */
function isSafeMemberName(name, rawParts = []) {
    if (typeof name !== 'string' || name === '') return false;
    const parts = rawParts.length > 0 ? rawParts : [name];
    for (const raw of parts) {
        if (typeof raw !== 'string' || raw === '') return false;
        if (raw.includes('\0')) return false;
        if (raw.includes('\\')) return false;
        if (raw.startsWith('/')) return false;
        const segments = raw.split('/');
        if (segments.some(seg => seg === '..')) return false;
    }
    const normalized = path.posix.normalize(name);
    if (normalized === '' || normalized === '..' || normalized.startsWith('../') || normalized.startsWith('/')) {
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
    // P1-4: read through a no-follow fd with dev/inode identity check — the
    // archive bytes hashed here are the same inode that was validated.
    const bytes = readFileSafeNoFollow(abs, { fsImpl: fileSystem }).bytes;
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
        // P2-1: the size field is REQUIRED to be valid octal — a corrupt
        // size silently defaulting to 0 would accept a truncated member as
        // empty. `|| 0` is a security bug, never a fallback here.
        const size = parseOctal(header, 124, 12);
        if (size === null) {
            throw Object.assign(new Error(`tar member size field is not valid octal: ${abs}`), {
                code: 'SAFETY_ERROR',
            });
        }
        const paddedSize = Math.ceil(size / TAR_BLOCK) * TAR_BLOCK;
        const contentStart = offset + TAR_BLOCK;
        // P2-1: explicit bounds — both the declared content and its padding
        // must physically exist in the buffer. subarray() would silently
        // clamp, so every length must be verified BEFORE any slice.
        if (contentStart + size > tar.length) {
            throw Object.assign(new Error(`tar member content extends beyond the archive (truncated): ${abs}`), {
                code: 'SAFETY_ERROR',
            });
        }
        if (contentStart + paddedSize > tar.length) {
            throw Object.assign(new Error(`tar member padding is incomplete (truncated): ${abs}`), {
                code: 'SAFETY_ERROR',
            });
        }

        if (typeflag === 'L') {
            // GNU long name: the next data block holds the real name, stored
            // NUL-terminated and NUL-padded to the block boundary (real GNU
            // tar emits `path\0` + padding). R4-P3-2: strip the trailing NUL
            // padding so the resolved name is the actual path — the safety
            // validator must NOT see the padding as part of the name;
            // embedded NULs inside the name remain a fail-closed rejection
            // (isSafeMemberName).
            const rawLongName = tar.subarray(contentStart, contentStart + size).toString('utf8');
            pendingLongName = rawLongName.replace(/\0+$/, '');
            offset = contentStart + paddedSize;
            continue;
        }
        if (typeflag === 'x') {
            // PAX extended headers: path= may override the name; linkpath= means
            // a link target is being recorded — links are forbidden, fail closed.
            // R11-P3-3 (Codex round 11): parse at BYTE boundaries — PAX
            // lengths count bytes, and a pre-decoded UTF-8 string would
            // measure non-ASCII paths in UTF-16 code units instead.
            const pax = parsePaxRecords(tar.subarray(contentStart, contentStart + size));
            if (pax.linkpath !== undefined) {
                throw Object.assign(new Error(`tar member declares a link target (not allowed): ${abs}`), {
                    code: 'SAFETY_ERROR',
                });
            }
            if (pax.path !== undefined) pendingPaxPath = pax.path;
            offset = contentStart + paddedSize;
            continue;
        }
        if (typeflag === 'g') {
            // P2-1: GLOBAL PAX headers are not implemented — they apply to
            // every subsequent member (e.g. a global path prefix), so
            // ignoring them could silently miss a name override. Fail closed.
            throw Object.assign(new Error(`tar declares a GLOBAL PAX header (not supported): ${abs}`), {
                code: 'SAFETY_ERROR',
            });
        }
        if (typeflag === 'K') {
            throw Object.assign(new Error(`tar member declares a GNU long link (not allowed): ${abs}`), {
                code: 'SAFETY_ERROR',
            });
        }

        // P1-1: compose the member name from the RAW path fields (ustar
        // name+prefix, GNU long name, PAX path override) and validate BOTH
        // the raw segments AND the combined normalized path.
        let name;
        let rawParts;
        if (pendingPaxPath !== null) {
            name = pendingPaxPath;
            rawParts = [pendingPaxPath];
        } else if (pendingLongName !== null) {
            name = pendingLongName;
            rawParts = [pendingLongName];
        } else {
            const rawName = header.subarray(0, 100).toString('utf8').replace(/\0.*$/, '');
            const magic = header.subarray(257, 263).toString('utf8');
            const hasUstar = magic === 'ustar\0' || magic === 'ustar ';
            const rawPrefix = hasUstar ? header.subarray(345, 500).toString('utf8').replace(/\0.*$/, '') : '';
            name = rawPrefix ? `${rawPrefix}/${rawName}` : rawName;
            rawParts = rawPrefix ? [rawPrefix, rawName] : [rawName];
        }
        pendingLongName = null;
        pendingPaxPath = null;
        if (!isSafeMemberName(name, rawParts)) {
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
        // P1-1: duplicate detection on the NORMALIZED path — 'a/./b.json'
        // and 'a/b.json' are the same member and must be rejected as one.
        const normalizedName = path.posix.normalize(name);
        if (seen.has(normalizedName)) {
            throw Object.assign(new Error(`duplicate tar member path: ${name} (normalized ${normalizedName})`), {
                code: 'SAFETY_ERROR',
            });
        }
        seen.add(normalizedName);
        const content = tar.subarray(contentStart, contentStart + size);
        members.push({
            name,
            type: 'file',
            size,
            sha256: crypto.createHash('sha256').update(content).digest('hex'),
        });
        offset = contentStart + paddedSize;
    }

    // R10-P3-2 (Codex round 10): a dangling GNU long-name (L) or PAX path
    // override (x) at end-of-archive — metadata record followed directly by
    // the zero end blocks, with no data member to consume it — must fail
    // closed. Without this, the parser accepts an archive that ends in an
    // unconsumed name override.
    if (pendingLongName !== null || pendingPaxPath !== null) {
        throw Object.assign(
            new Error(`tar ends with a dangling GNU/PAX name override (no member follows): ${abs}`),
            { code: 'SAFETY_ERROR' }
        );
    }

    // Canonical end-of-archive: the loop exits EITHER on the first zero block
    // or by running out of buffer. The tar spec requires TWO consecutive
    // 512-byte zero blocks (1024 zero bytes) as the end marker; everything
    // after them must be zero padding only. If the buffer runs out without
    // the end blocks, or the marker has only one zero block, the archive is
    // truncated and must be rejected (P2-1; R1-P2-2 for the two-block rule).
    if (offset + TAR_BLOCK <= tar.length) {
        if (offset + 2 * TAR_BLOCK > tar.length) {
            throw Object.assign(
                new Error(`tar end-of-archive marker is truncated (two zero blocks required): ${abs}`),
                { code: 'SAFETY_ERROR' }
            );
        }
        const tail = tar.subarray(offset);
        if (!tail.every(b => b === 0)) {
            throw Object.assign(new Error(`tar has non-canonical end (trailing data after end blocks): ${abs}`), {
                code: 'SAFETY_ERROR',
            });
        }
    } else {
        throw Object.assign(new Error(`tar has no canonical end-of-archive blocks (truncated): ${abs}`), {
            code: 'SAFETY_ERROR',
        });
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
    const actual = sha256Hex(readFileSafeNoFollow(abs, { fsImpl: fileSystem }).bytes);
    if (actual !== String(expectedSha256).toLowerCase()) {
        throw Object.assign(new Error(`archive sha256 mismatch: declared ${expectedSha256}, actual ${actual}`), {
            code: 'SAFETY_ERROR',
        });
    }
    return { archive_path: abs, archive_sha256: actual };
}

/**
 * PR1817 remediation (P0-1): deterministic inventory hash over the FULL
 * managed member list — stable-sorted rows of {member_path, member_type,
 * member_size, member_sha256}. The inventory is bound into the package
 * receipt and RE-COMPUTED from the live archive on every build run, so a
 * receipt whose member table does not exactly match the archive's real
 * members can never pass (a receipt hash alone proves nothing).
 *
 * @param {Array<{name,type,size,sha256}>} members - inspected archive members
 * @returns {string} 64-hex inventory hash
 */
function computeArchiveInventory(members) {
    const rows = members
        .map(m => ({
            member_path: String(m.name),
            member_type: String(m.type || 'file'),
            member_size: Number(m.size),
            member_sha256: String(m.sha256),
        }))
        .sort((a, b) => (a.member_path < b.member_path ? -1 : 1));
    return canonicalJsonHash(rows);
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
        // P0-1: inventory over the COMPLETE managed member set; any member
        // drift between the receipt and the live archive fails closed.
        archive_inventory_sha256: computeArchiveInventory(members),
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
    // P0-1: the archive inventory hash is REQUIRED — a receipt without it
    // cannot bind the live archive's member table and is rejected.
    if (!/^[0-9a-f]{64}$/.test(String(receipt.archive_inventory_sha256 || ''))) {
        errors.push('receipt archive_inventory_sha256 must be 64 lowercase hex');
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
 * PR1817 remediation (P0-1): re-verify a package's LIVE archive against its
 * receipt. Called once per package per build run (the result may be shared
 * across entries of the same package WITHIN one run, never across runs):
 *
 *   1. safe re-inspection of the live archive (no cache of past runs);
 *   2. live archive SHA-256 must equal the receipt's AND the binding's;
 *   3. live member inventory must equal the receipt's
 *      archive_inventory_sha256 (binds the full member table);
 *   4. per-member comparison: the receipt's member name set must equal the
 *      live archive's member name set (no extras, no missing managed
 *      members), and every shared member must have the same sha256.
 *
 * @param {object} args - { binding, receipt, options }
 * @returns {object} inspected - { archive_sha256, members: [{name,type,size,sha256}] }
 */
function verifyLiveArchiveAgainstReceipt(args = {}) {
    const binding = args.binding || {};
    const receipt = args.receipt || {};
    const options = args.options || {};

    const inspected = inspectArchive(String(binding.path || ''), options);
    if (inspected.archive_sha256 !== String(receipt.archive_sha256 || '')) {
        throw Object.assign(
            new Error(
                `live archive sha256 ${inspected.archive_sha256} does not match receipt archive sha256 ${receipt.archive_sha256}`
            ),
            { code: 'SAFETY_ERROR' }
        );
    }
    if (String(receipt.archive_sha256 || '') !== String(binding.sha256 || '')) {
        throw Object.assign(
            new Error(`receipt archive sha ${receipt.archive_sha256} does not match binding ${binding.sha256}`),
            { code: 'SAFETY_ERROR' }
        );
    }
    const liveInventory = computeArchiveInventory(inspected.members);
    if (liveInventory !== String(receipt.archive_inventory_sha256 || '')) {
        throw Object.assign(
            new Error(
                `live archive member inventory does not match receipt archive_inventory_sha256 (receipt members disagree with the real archive)`
            ),
            { code: 'SAFETY_ERROR' }
        );
    }
    const liveByName = new Map(inspected.members.map(m => [m.name, m]));
    const receiptNames = Object.keys(receipt.members || {}).sort();
    const liveNames = [...liveByName.keys()].sort();
    if (receiptNames.length !== liveNames.length || receiptNames.some((n, i) => n !== liveNames[i])) {
        const missing = liveNames.filter(n => !receipt.members[n]);
        const extra = receiptNames.filter(n => !liveByName.has(n));
        throw Object.assign(
            new Error(
                `receipt member set disagrees with live archive (missing from receipt: ${missing.join(', ') || 'none'}; not in archive: ${extra.join(', ') || 'none'})`
            ),
            { code: 'SAFETY_ERROR' }
        );
    }
    for (const name of liveNames) {
        const live = liveByName.get(name);
        if (String(receipt.members[name]) !== String(live.sha256)) {
            throw Object.assign(
                new Error(`receipt member hash disagrees with live archive for member: ${name}`),
                { code: 'SAFETY_ERROR' }
            );
        }
    }
    // R1-P0-1 / R2-P0-1: register the inspected object BY IDENTITY and deep
    // freeze it before handing it out — the registry membership is the
    // unforgeable capability; a spread copy is a different object and is
    // rejected, and the frozen members table cannot be replaced in place.
    liveVerifyRegistry.add(inspected);
    return deepFreezeInspection(inspected);
}

/**
 * Bind ONE source-index entry to its package: the entry uses exactly ONE
 * package (single-package rule); the receipt must be valid; the receipt's
 * archive SHA must equal the binding's declared SHA; the LIVE archive must be
 * re-inspected and its SHA + full member table (inventory + per-member
 * hashes) must equal the receipt (P0-1 — the receipt can never be the sole
 * trusted source); and the extracted payload/manifest files must be safe
 * inputs whose live SHA equals BOTH the receipt's member hashes AND the live
 * archive member hashes.
 *
 * @param {object} args - { entry, binding, receipt, inspected, payloadFile,
 *                          manifestFile, outputRoot, options }
 * @returns {{ payload, manifest, payloadBytes, payloadFileSha256, manifestFileSha256 }}
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

    // P0-1: bind the receipt to the LIVE archive. `inspected` is accepted
    // ONLY when it is the module-private live-verification capability
    // (R1-P0-1, hardened in R2-P0-1): it must be the exact object registered
    // by THIS module's own verifyLiveArchiveAgainstReceipt in this run
    // (WeakSet identity — a spread copy or fabricated object is rejected),
    // and its archive SHA must be the receipt's archive SHA. If no inspected
    // is supplied (direct API use), the live archive is re-verified here —
    // fail closed either way.
    if (args.inspected !== undefined) {
        if (!liveVerifyRegistry.has(args.inspected)) {
            throw Object.assign(
                new Error('inspected must be a live-verification capability registered by this module (object identity; spreads and fabricated objects are rejected)'),
                { code: 'SAFETY_ERROR' }
            );
        }
        if (String(args.inspected.archive_sha256 || '') !== String(receipt.archive_sha256 || '')) {
            throw Object.assign(
                new Error('inspected archive sha256 does not match the receipt archive sha256'),
                { code: 'SAFETY_ERROR' }
            );
        }
    }
    const inspected =
        args.inspected || verifyLiveArchiveAgainstReceipt({ binding, receipt, options });

    // Extracted input files: safe + live SHA equals the receipt member SHA
    // AND the live archive member hash (both directions).
    const payloadAbs = verifyRepositoryExternalRegularFile(args.payloadFile, options);
    const manifestAbs = verifyRepositoryExternalRegularFile(args.manifestFile, options);
    if (outputRoot) {
        assertInputOutputNonOverlap(payloadAbs, outputRoot);
        assertInputOutputNonOverlap(manifestAbs, outputRoot);
    }
    const fileSystem = options.fsImpl || fs;
    // P1-4: payload/manifest bytes come from no-follow fds with dev/inode
    // identity checks — the bytes hashed are the same inodes that were
    // verified, and a mid-run swap of either file fails closed.
    const payloadBytes = readFileSafeNoFollow(payloadAbs, { fsImpl: fileSystem }).bytes;
    const manifestBytes = readFileSafeNoFollow(manifestAbs, { fsImpl: fileSystem }).bytes;
    const payloadSha = sha256Hex(payloadBytes);
    const manifestSha = sha256Hex(manifestBytes);
    // R4-P1-1: a receipt declares ONE payload_member / manifest_member, but a
    // single archive/package can hold MANY pairs. The source-index ENTRY may
    // carry its own payload_member / manifest_member selectors — use them
    // when present so each entry of the same package compares against ITS
    // archive member (both in the receipt hash map and in the live archive);
    // entries without selectors fall back to the receipt's global selectors
    // (single-pair receipts keep working; a second pair without selectors
    // still fails closed on the member-hash mismatch below).
    const payloadMember = String(entry.payload_member || receipt.payload_member || '');
    const manifestMember = String(entry.manifest_member || receipt.manifest_member || '');
    const liveByName = new Map(inspected.members.map(m => [m.name, m]));
    const livePayload = liveByName.get(payloadMember);
    const liveManifest = liveByName.get(manifestMember);
    if (payloadSha !== receipt.members[payloadMember] || (livePayload && payloadSha !== livePayload.sha256)) {
        throw Object.assign(
            new Error(
                `payload file sha256 ${payloadSha} does not match archive member ${payloadMember} (receipt ${receipt.members[payloadMember]}, live ${livePayload ? livePayload.sha256 : 'missing'})`
            ),
            { code: 'SAFETY_ERROR' }
        );
    }
    if (manifestSha !== receipt.members[manifestMember] || (liveManifest && manifestSha !== liveManifest.sha256)) {
        throw Object.assign(
            new Error(
                `manifest file sha256 ${manifestSha} does not match archive member ${manifestMember} (receipt ${receipt.members[manifestMember]}, live ${liveManifest ? liveManifest.sha256 : 'missing'})`
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
        manifestFileSha256: manifestSha,
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
    computeArchiveInventory,
    verifyLiveArchiveAgainstReceipt,
    verifyEntryAgainstReceipt,
};
