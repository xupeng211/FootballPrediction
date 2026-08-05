/* eslint-disable complexity, max-lines */
// The retention layer is a commit protocol + full consistency validator: the
// marker chain, ledger monotonicity checks, the residue scan and the summary
// arithmetic are intentionally branchy. File-level disable matches project
// precedent (FotMobDetailStagingContract, GoldenFeatureExtractor).
'use strict';

// lifecycle: permanent
//
// FotMob detail staging — retention layer: LOGICAL_COMMIT_MARKER atomic
// commit protocol (PR1817 remediation, FINDING_1) over an append-only
// repository-external file store.
//
// The staging layer has NO database by design (this task): the "store" is
// the output directory itself. Files are written with per-file atomicity
// (tmp + fsync + rename); the SET is committed by a final commit marker
// written via atomic rename. The marker is the ONLY commit point:
//
//   - commit-<seq>.json  — binds {name, sha256} of every file in the commit
//                          (artifacts, quarantine evidence, summary,
//                          store-state ledger version) + the previous
//                          marker's file hash (tamper-evident chain);
//   - store-state-<seq>.json — immutable ledger VERSION per commit (the
//                          CURRENT ledger = the one bound by the latest
//                          valid marker), so the validator can prove old
//                          records are never deleted;
//   - summary-<seq>.json  — one immutable per-run summary per commit;
//   - observation-*.artifact.json / quarantine-*.json — immutable snapshots;
//
// P1-4 TOCTOU posture (honest threat model): inputs are read through
// O_NOFOLLOW fds with dev/inode verified before and after the read; outputs
// go to a controlled private directory (owner-checked, group/world-writable
// rejected) via O_EXCL tmp + same-filesystem rename with a pre/post write
// directory identity check; every commit runs under an exclusive per-store
// lock. These mitigations shrink the check-to-use windows to the width of a
// single syscall and make a mid-write swap detectable. They are NOT a
// defense against a same-uid adversary who can sustain a race across
// ancestor walks, or against a hostile mount point — that requires a trusted
// kernel/FUSE layer and is explicitly out of scope for this offline
// operator tool. The commit-marker protocol guarantees that any tampering
// that does slip through leaves detectable residue / chain breaks.
//
// Failures:
//   - a failed commit removes the files it wrote and leaves NO marker —
//     the old committed state stays valid and byte-identical;
//   - files present but NOT bound by any valid marker are UNCOMMITTED
//     RESIDUE: commit refuses to start on residue and the validator reports
//     it — residue is never treated as committed (no false success);
//   - divergent existing files fail closed (never overwritten);
//   - existing file with identical bytes = idempotent (never rewritten).
//
// This is LOGICAL atomicity (commit-marker visibility), NOT a physical
// single-rename generation swap: a mid-commit crash may leave uncommitted
// files on disk, but they are provably not part of any committed state and
// are either cleaned up or reported as residue. The PR claims exactly this:
// COMMIT_MARKER_ATOMIC_VISIBILITY.
//
// Terminal states (names MUST match the contract package):
//   - ACCEPTED_NEW             → new immutable artifact snapshot written
//   - ACCEPTED_REPEAT_EXACT    → identical key already staged; nothing written
//   - ACCEPTED_REPEAT_EQUIVALENT → same source_match_id, new payload version;
//                                the artifact is REBUILT with this final
//                                terminal state (FINDING_2: artifact, summary
//                                and ledger must agree), new snapshot written,
//                                prior untouched
//   - REJECTED_*               → nothing written
//   - QUARANTINED_*            → lightweight quarantine evidence record
//                                (identity + error code; never full payload)

const path = require('node:path');
const fs = require('node:fs');
const crypto = require('node:crypto');
const util = require('node:util');

const {
    TERMINAL_STATES,
    ERROR_CODES,
    MAX_SOURCE_MATCH_ID_LENGTH,
    isPlainJsonData,
    snapshotStrictPlainData,
    isStrictAbsoluteTimestamp,
    validateStagingArtifact,
    buildStagingArtifact,
    canonicalJsonHash,
} = require('./FotMobDetailStagingContract');

const STORE_STATE_SCHEMA = 'fotmob-detail-staging-store-state/v1';
const COMMIT_MARKER_SCHEMA = 'fotmob-detail-staging-commit-marker/v1';

// ─────────────────────────────────────────────────────────────
// Path safety
// ─────────────────────────────────────────────────────────────

/**
 * Reject any symlink component in an absolute path (walking every ancestor —
 * an intermediate symlinked directory could redirect a write back into the
 * repository). Same discipline as the capture pipeline's path guards.
 */
function assertNoSymlinkAncestors(absPath, fsImpl = fs) {
    const abs = path.resolve(String(absPath));
    const segments = abs.split(path.sep).filter(Boolean);
    let current = path.parse(abs).root;
    for (const segment of segments) {
        current = path.join(current, segment);
        let stat = null;
        try {
            stat = fsImpl.lstatSync(current);
        } catch {
            /* component absent is fine */
        }
        if (stat && stat.isSymbolicLink()) {
            throw Object.assign(new Error(`path component must not be a symlink: ${current}`), {
                code: 'SAFETY_ERROR',
            });
        }
    }
    return abs;
}

function ensureRealDirectoryTree(absDirPath, fsImpl = fs) {
    const abs = assertNoSymlinkAncestors(absDirPath, fsImpl);
    const segments = abs.split(path.sep).filter(Boolean);
    let current = path.parse(abs).root;
    for (const segment of segments) {
        current = path.join(current, segment);
        let stat = null;
        try {
            stat = fsImpl.lstatSync(current);
        } catch {
            /* absent */
        }
        if (stat) {
            if (stat.isSymbolicLink()) {
                throw Object.assign(new Error(`path component must not be a symlink: ${current}`), {
                    code: 'SAFETY_ERROR',
                });
            }
            if (!stat.isDirectory()) {
                throw Object.assign(new Error(`path component must be a directory: ${current}`), {
                    code: 'SAFETY_ERROR',
                });
            }
        } else {
            // P1-4: directories the tool creates are PRIVATE (0700) so the
            // controlled-private-directory check can never be defeated by a
            // permissive umask. Operator-created directories must pass the
            // owner + not-group/world-writable checks themselves.
            fsImpl.mkdirSync(current, { mode: 0o700 });
            let created = null;
            try {
                created = fsImpl.lstatSync(current);
            } catch {
                /* treat as missing */
            }
            if (!created || created.isSymbolicLink() || !created.isDirectory()) {
                throw Object.assign(new Error(`failed to create real directory: ${current}`), { code: 'SAFETY_ERROR' });
            }
        }
    }
    const finalStat = fsImpl.lstatSync(abs);
    if (!finalStat || finalStat.isSymbolicLink() || !finalStat.isDirectory()) {
        throw Object.assign(new Error(`target must be a real directory: ${abs}`), {
            code: 'SAFETY_ERROR',
        });
    }
    // P1-4: the write target must be a controlled private directory — owned
    // by the current uid and not group/world writable. A group- or world-
    // writable store directory would let a less-privileged peer plant files
    // the commit protocol would then bind or report as residue.
    assertControlledPrivateDirectory(finalStat, abs);
    return abs;
}

/**
 * P1-4: a controlled store/output directory must be owned by the current
 * process and must NOT be group- or world-writable. Honest limitation (see
 * module header): this and the fd-based read + dev/inode checks shrink the
 * race windows; they do not defend against a same-uid attacker who can race
 * a rename at any point — that requires a trusted mount point / FUSE layer
 * and is explicitly out of scope for an offline operator tool.
 */
function assertControlledPrivateDirectory(stat, abs) {
    if (typeof stat.uid === 'number' && typeof process.getuid === 'function' && stat.uid !== process.getuid()) {
        throw Object.assign(
            new Error(`output directory must be owned by the current user: ${abs}`),
            { code: 'SAFETY_ERROR' }
        );
    }
    if ((stat.mode & 0o022) !== 0) {
        throw Object.assign(
            new Error(`output directory must not be group/world writable: ${abs}`),
            { code: 'SAFETY_ERROR' }
        );
    }
}

/**
 * Verify a path is absolute, outside the repository, and has no symlink
 * component (leaf included — assertNoSymlinkAncestors walks every segment).
 * Mirrors FotMobDetailCapturePlan.verifyRepositoryExternalPath.
 */
function verifyRepositoryExternalPath(outputPath, options = {}) {
    const repositoryRoot = options.repositoryRoot
        ? path.resolve(options.repositoryRoot)
        : path.resolve(__dirname, '..', '..', '..');
    if (!path.isAbsolute(String(outputPath || ''))) {
        throw Object.assign(new Error('output path must be absolute'), {
            code: 'INPUT_ERROR',
        });
    }
    const abs = path.resolve(String(outputPath || ''));
    const repoResolved = path.resolve(repositoryRoot);
    const rel = path.relative(repoResolved, abs);
    if (rel === '' || (!rel.startsWith('..') && !path.isAbsolute(rel))) {
        throw Object.assign(new Error(`output path must be outside the repository: ${abs}`), { code: 'SAFETY_ERROR' });
    }
    assertNoSymlinkAncestors(abs);
    return abs;
}

// ─────────────────────────────────────────────────────────────
// Atomic write / read
// ─────────────────────────────────────────────────────────────

/**
 * Write a JSON document atomically: tmp file in the same directory (same
 * filesystem), write → fsync → close → rename. Existing files are never
 * overwritten unless identical (idempotency) — divergent content fails
 * closed. The returned sha256 is over the EXACT final bytes.
 *
 * @param {string} filePath - final absolute path
 * @param {object} doc - JSON-serializable document
 * @param {object} options - { fsImpl, repositoryRoot }
 * @returns {{ written: boolean, reason: string, sha256: string }}
 */
function writeJsonAtomically(filePath, doc, options = {}) {
    const fileSystem = options.fsImpl || fs;
    const abs = verifyRepositoryExternalPath(filePath, options);
    const dir = path.dirname(abs);
    ensureRealDirectoryTree(dir, fileSystem);

    // P1-4: root dev/inode is captured BEFORE the write and re-verified AFTER
    // the rename — if the output directory itself was swapped (bind mount or
    // rename-over of the directory) while we wrote, the run fails closed
    // instead of committing into a directory we never validated.
    let dirBefore = null;
    try {
        dirBefore = fileSystem.lstatSync(dir);
    } catch {
        /* reported by ensureRealDirectoryTree above */
    }

    let finalStat = null;
    try {
        finalStat = fileSystem.lstatSync(abs);
    } catch {
        /* absent */
    }
    if (finalStat && finalStat.isSymbolicLink()) {
        throw Object.assign(new Error(`refusing to write through a symlink: ${abs}`), { code: 'SAFETY_ERROR' });
    }

    const bytes = Buffer.from(JSON.stringify(doc, null, 2) + '\n', 'utf8');
    const fileSha = crypto.createHash('sha256').update(bytes).digest('hex');

    if (finalStat && finalStat.isFile()) {
        const existing = fileSystem.readFileSync(abs);
        if (existing.equals(bytes)) {
            return { written: false, reason: 'existing_identical', sha256: fileSha };
        }
        throw Object.assign(new Error(`refusing to overwrite divergent existing file: ${abs}`), {
            code: 'OUTPUT_CONFLICT',
        });
    }

    const tmp = `${abs}.tmp-${process.pid}`;
    // A stale tmp from a previous failed write must not block this one.
    try {
        fileSystem.unlinkSync(tmp);
    } catch {
        /* absent */
    }
    let fd;
    try {
        // P1-4: 'wx' = O_CREAT|O_EXCL — the tmp is created fresh, never
        // follows or reuses an existing inode; same-directory tmp + rename
        // keeps the publish on one filesystem (no cross-device copy window).
        fd = fileSystem.openSync(tmp, 'wx');
        try {
            // R18-P2-1 (Codex round 18): fs.writeSync may legally return a
            // SHORT write — fewer bytes than requested. The return count was
            // previously ignored, so a truncated tmp could be fsynced,
            // renamed and reported written:true while the artifact or the
            // commit marker carried partial content (validate would only
            // discover the mismatch later, leaving an un-committable store).
            // Loop until the whole buffer is written; a non-integer, zero or
            // negative return (no progress) or an overshoot is an immediate
            // failure through the existing cleanup (unlink tmp, rethrow) —
            // the marker stays the single commit point, never written on a
            // failed persistence.
            let written = 0;
            while (written < bytes.length) {
                const n = fileSystem.writeSync(fd, bytes, written, bytes.length - written);
                if (typeof n !== 'number' || !Number.isInteger(n) || n <= 0 || n > bytes.length - written) {
                    throw Object.assign(
                        new Error(`short write made no progress while writing: ${abs}`),
                        { code: 'SAFETY_ERROR' }
                    );
                }
                written += n;
            }
            fileSystem.fsyncSync(fd);
        } finally {
            fileSystem.closeSync(fd);
        }
        fileSystem.renameSync(tmp, abs);
    } catch (error) {
        try {
            fileSystem.unlinkSync(tmp);
        } catch {
            /* best effort */
        }
        throw error;
    }
    // P1-4: root dev/inode AFTER the write must equal the pre-write identity.
    if (dirBefore) {
        let dirAfter = null;
        try {
            dirAfter = fileSystem.lstatSync(dir);
        } catch {
            /* fail closed below */
        }
        if (!dirAfter || dirAfter.dev !== dirBefore.dev || dirAfter.ino !== dirBefore.ino) {
            throw Object.assign(
                new Error(`output directory identity changed during write: ${dir}`),
                { code: 'SAFETY_ERROR' }
            );
        }
    }
    return { written: true, reason: 'written', sha256: fileSha };
}

/**
 * P1-4: read a file with no-follow + identity-checked semantics. The read
 * goes through an fd opened with O_NOFOLLOW (a leaf symlink can never be
 * followed at open time), the fd is fstat'd (regular-file check on the SAME
 * inode we read), the bytes are read THROUGH the fd (a rename-over of the
 * directory entry after open cannot redirect the read), and the dev/inode
 * captured before the read must equal the dev/inode after the read — a
 * swapped or replaced file fails closed.
 *
 * Honest limitation: this mitigates the leaf-swap window (the check-to-use
 * race on the file itself). A same-uid attacker who can race the ancestor
 * walk or rename the DIRECTORY between validation and open remains able to
 * swap targets — the ancestor walk is realpath-verified, and the
 * write-path directory identity check below detects directory swaps at
 * commit time, but a sustained same-uid adversary is NOT a defense target
 * of this tool (see the module header).
 *
 * @param {string} filePath - absolute repository-external file path
 * @param {object} options - { fsImpl }
 * @returns {{ bytes: Buffer, abs: string, dev: number, ino: number }}
 */
function readFileSafeNoFollow(filePath, options = {}) {
    const fileSystem = options.fsImpl || fs;
    const abs = assertNoSymlinkAncestors(String(filePath), fileSystem);
    const noFollow = fileSystem.constants && fileSystem.constants.O_NOFOLLOW ? fileSystem.constants.O_NOFOLLOW : 0;
    let fd;
    try {
        fd = fileSystem.openSync(abs, fileSystem.constants.O_RDONLY | noFollow);
    } catch (error) {
        throw Object.assign(new Error(`file not readable (no-follow open failed): ${abs}`), {
            code: 'INPUT_ERROR',
        });
    }
    let before = null;
    let bytes;
    try {
        before = fileSystem.fstatSync(fd);
        if (!before || before.isSymbolicLink() || !before.isFile()) {
            throw Object.assign(new Error(`input must be a regular file, not a symlink: ${abs}`), {
                code: 'SAFETY_ERROR',
            });
        }
        // R12-P2-2 (Codex round 12): an optional size bound enforced via the
        // PRE-READ fstat — the file is never read into memory if it exceeds
        // the limit (a compression-bomb archive must fail before any
        // allocation, not after).
        if (options.maxBytes !== undefined && before.size > options.maxBytes) {
            throw Object.assign(
                new Error(
                    `input file exceeds the size limit (${before.size} > ${options.maxBytes} bytes): ${abs}`
                ),
                { code: 'SAFETY_ERROR' }
            );
        }
        bytes = fileSystem.readFileSync(fd);
        const after = fileSystem.fstatSync(fd);
        if (!after || after.dev !== before.dev || after.ino !== before.ino) {
            throw Object.assign(new Error(`input file identity changed during read: ${abs}`), {
                code: 'SAFETY_ERROR',
            });
        }
    } finally {
        try {
            fileSystem.closeSync(fd);
        } catch {
            /* best effort */
        }
    }
    return { bytes, abs, dev: before.dev, ino: before.ino };
}

/**
 * Read a JSON file with FULL input safety (PR1817 FINDING_4): absolute path,
 * regular file, leaf not a symlink, ALL ancestors free of symlinks, and the
 * bytes read through a no-follow fd whose dev/inode is verified before and
 * after the read (P1-4).
 */
function readJsonFile(filePath, options = {}) {
    const { bytes } = readFileSafeNoFollow(filePath, options);
    let parsed;
    try {
        parsed = JSON.parse(bytes.toString('utf8'));
    } catch (error) {
        throw Object.assign(new Error(`file is not valid JSON: ${filePath}`), {
            code: 'INPUT_ERROR',
        });
    }
    return {
        parsed,
        bytes,
        sha256: crypto.createHash('sha256').update(bytes).digest('hex'),
    };
}

/**
 * P1-4: exclusive per-store lock. The lock file is created with O_EXCL
 * inside the (already validated, controlled, private) output root; a live
 * holder is refused (fail closed), a dead holder's stale lock is removed and
 * retried ONCE. The lock is held for the DURATION of the whole commit
 * (residue scan → writes → marker), not per file, so two concurrent commits
 * into the same store cannot interleave their multi-file transactions.
 * Honest limitation: this serializes OUR writer protocol; it does not stop a
 * same-uid attacker from writing into the store by other means (their files
 * are then detected as residue / unbound files by the next commit and the
 * validator).
 */
// P1-4: the exclusive store lock file name. An OPERATIONAL control file —
// created only while a commit holds the lock, never bound by any commit
// marker, excluded from the residue scan (collectCommittedState), removed on
// release, stale copies recovered on next acquisition.
const STAGING_LOCK_FILE_NAME = '.staging-write.lock';

function withStoreLock(outputRoot, fsImpl, work) {
    const lockPath = path.join(outputRoot, STAGING_LOCK_FILE_NAME);
    let lockFd = null;
    const acquire = () => {
        // R19-P2-1 (Codex round 19): lockCreated gates EVERY cleanup — the
        // lock path is only ever touched when openSync('wx') actually
        // created it. A non-EEXIST openSync failure (I/O, permissions,
        // fault injection) happens BEFORE creation: the path may belong to
        // ANOTHER live holder, and unlinking it would break the per-store
        // exclusivity.
        let lockCreated = false;
        try {
            lockFd = fsImpl.openSync(lockPath, 'wx');
            lockCreated = true;
            // R18-P2-1 (Codex round 18): same short-write discipline as
            // writeJsonAtomically — a truncated PID in the lock file could
            // make isHolderAlive() misjudge a LIVE holder as dead and clear
            // its lock. Loop until the full PID is written; no-progress
            // fails the acquisition.
            const pidBytes = Buffer.from(String(process.pid));
            let pidWritten = 0;
            while (pidWritten < pidBytes.length) {
                const n = fsImpl.writeSync(lockFd, pidBytes, pidWritten, pidBytes.length - pidWritten);
                if (typeof n !== 'number' || !Number.isInteger(n) || n <= 0 || n > pidBytes.length - pidWritten) {
                    throw Object.assign(
                        new Error(`short write made no progress while writing the store lock: ${lockPath}`),
                        { code: 'SAFETY_ERROR' }
                    );
                }
                pidWritten += n;
            }
        } catch (error) {
            if (error && error.code === 'EEXIST') {
                // The lock already existed when openSync failed — we did
                // NOT create it; report contention for the holder check.
                return false;
            }
            if (!lockCreated) {
                // openSync failed before creating the lock: the path is not
                // ours — never close/unlink it.
                throw error;
            }
            // The lock was CREATED by us ('wx') — a failed write leaves an
            // EMPTY or partial lock that parseInt cannot resolve, which
            // isHolderAlive() then treats as held forever (permanent
            // fail-closed, no auto-recovery). Since no other process can
            // hold it (EEXIST would have returned above), remove our own
            // lock before propagating the failure.
            try {
                fsImpl.closeSync(lockFd);
            } catch {
                /* best effort */
            }
            try {
                fsImpl.unlinkSync(lockPath);
            } catch {
                /* best effort — a stale lock is recovered on the next commit */
            }
            throw error;
        }
        return true;
    };
    const isHolderAlive = () => {
        let pid = null;
        try {
            pid = parseInt(fsImpl.readFileSync(lockPath, 'utf8'), 10);
        } catch {
            return true; // unreadable lock → assume held (fail closed)
        }
        if (!Number.isFinite(pid)) {
            return true;
        }
        try {
            process.kill(pid, 0);
            return true;
        } catch (error) {
            return error.code === 'EPERM'; // EPERM = exists, ESRCH = dead
        }
    };
    if (!acquire()) {
        if (isHolderAlive()) {
            throw Object.assign(
                new Error(`another process holds the store lock: ${lockPath}`),
                { code: 'SAFETY_ERROR' }
            );
        }
        try {
            fsImpl.unlinkSync(lockPath);
        } catch {
            /* raced away — the retry decides */
        }
        if (!acquire()) {
            throw Object.assign(
                new Error(`store lock is contended and could not be acquired: ${lockPath}`),
                { code: 'SAFETY_ERROR' }
            );
        }
    }
    try {
        return work();
    } finally {
        try {
            fsImpl.closeSync(lockFd);
        } catch {
            /* best effort */
        }
        try {
            fsImpl.unlinkSync(lockPath);
        } catch {
            /* best effort — a stale lock is recovered on the next commit */
        }
    }
}

// ─────────────────────────────────────────────────────────────
// File naming (commit protocol)
// ─────────────────────────────────────────────────────────────

function observationKey(sourceMatchId, stablePayloadSha256) {
    return `${String(sourceMatchId)}:${String(stablePayloadSha256)}`;
}

function artifactFileName(sourceMatchId, stablePayloadSha256) {
    return `observation-${String(sourceMatchId)}-${String(stablePayloadSha256)}.artifact.json`;
}

function quarantineFileName(sourceMatchId, errorCode) {
    return `quarantine-${String(sourceMatchId)}-${String(errorCode)}.json`;
}

function summaryFileNameForSeq(seq) {
    return `summary-${Number(seq)}.json`;
}

function ledgerFileNameForSeq(seq) {
    return `store-state-${Number(seq)}.json`;
}

function markerFileNameForSeq(seq) {
    return `commit-${Number(seq)}.json`;
}

function isArtifactFileName(name) {
    return /^observation-\d+-[0-9a-f]{64}\.artifact\.json$/.test(String(name || ''));
}

function isQuarantineFileName(name) {
    return /^quarantine-\d+-E\d{3}\.json$/.test(String(name || ''));
}

function isSummaryFileName(name) {
    return /^summary-\d+\.json$/.test(String(name || ''));
}

function isLedgerFileName(name) {
    return /^store-state-\d+\.json$/.test(String(name || ''));
}

function isMarkerFileName(name) {
    return /^commit-\d+\.json$/.test(String(name || ''));
}

const COMMIT_FILE_PATTERNS = [isArtifactFileName, isQuarantineFileName, isSummaryFileName, isLedgerFileName];

function isCommitFilePattern(name) {
    return COMMIT_FILE_PATTERNS.some(predicate => predicate(name));
}

function emptyStoreState() {
    return {
        schema_version: STORE_STATE_SCHEMA,
        observations: {},
        quarantines: {},
    };
}

// ─────────────────────────────────────────────────────────────
// Commit marker chain + committed-state loading
// ─────────────────────────────────────────────────────────────

function validateMarkerDoc(marker) {
    const errors = [];
    if (!marker || typeof marker !== 'object') {
        return { ok: false, errors: ['marker is not an object'] };
    }
    if (marker.schema_version !== COMMIT_MARKER_SCHEMA) {
        errors.push(`marker schema_version must be ${COMMIT_MARKER_SCHEMA}`);
    }
    if (!Number.isInteger(marker.commit_seq) || marker.commit_seq < 1) {
        errors.push('marker commit_seq must be a positive integer');
    }
    if (marker.previous_commit_seq !== null && !Number.isInteger(marker.previous_commit_seq)) {
        errors.push('marker previous_commit_seq must be an integer or null');
    }
    if (marker.previous_marker_sha256 !== null && !/^[0-9a-f]{64}$/.test(String(marker.previous_marker_sha256 || ''))) {
        errors.push('marker previous_marker_sha256 must be 64-hex or null');
    }
    if (!Array.isArray(marker.files) || marker.files.length === 0) {
        errors.push('marker files must be a non-empty array');
    } else {
        const seen = new Set();
        for (const fileEntry of marker.files) {
            if (
                !fileEntry ||
                typeof fileEntry.name !== 'string' ||
                fileEntry.name === '' ||
                path.basename(fileEntry.name) !== fileEntry.name
            ) {
                errors.push('marker file name must be a plain basename');
                continue;
            }
            if (!isCommitFilePattern(fileEntry.name)) {
                errors.push(`marker file has an unrecognized name: ${fileEntry.name}`);
            }
            if (!/^[0-9a-f]{64}$/.test(String(fileEntry.sha256 || ''))) {
                errors.push(`marker file sha256 must be 64-hex: ${fileEntry.name}`);
            }
            if (seen.has(fileEntry.name)) {
                errors.push(`marker lists duplicate file: ${fileEntry.name}`);
            }
            seen.add(fileEntry.name);
        }
    }
    return { ok: errors.length === 0, errors };
}

/**
 * Collect the committed state of a store root WITHOUT throwing: validates
 * the commit marker chain, verifies every marker-bound file against its
 * listed SHA-256, loads every ledger version, and scans for uncommitted
 * residue (files in the root not bound by any valid marker).
 *
 * @param {string} root - repository-external store root
 * @param {object} options - { repositoryRoot, fsImpl }
 * @returns {object} { ok, errors: [{code,message}], markers: [doc...],
 *   latestSeq: number, latestLedger: object|null, ledgerVersions: [doc...],
 *   residue: [names], markerBoundFiles: {name: sha256} }
 */
/* eslint-disable-next-line complexity */
function collectCommittedState(root, options = {}) {
    const fileSystem = options.fsImpl || fs;
    const errors = [];
    let entries = [];
    try {
        entries = fileSystem.readdirSync(root).sort();
    } catch {
        errors.push({ code: 'PARTIAL_OUTPUT', message: 'store root not readable' });
        return {
            ok: false,
            errors,
            markers: [],
            latestSeq: 0,
            latestLedger: null,
            ledgerVersions: [],
            residue: [],
            markerBoundFiles: {},
        };
    }

    const markerNames = entries.filter(isMarkerFileName);
    const markers = [];
    for (const name of markerNames) {
        const seqFromName = Number(name.match(/^commit-(\d+)\.json$/)[1]);
        let doc = null;
        try {
            doc = readJsonFile(path.join(root, name), options).parsed;
        } catch (error) {
            errors.push({
                code: 'MARKER_INVALID',
                message: `commit marker unreadable: ${name} (${error.message})`,
            });
            continue;
        }
        const markerValidation = validateMarkerDoc(doc);
        if (!markerValidation.ok) {
            errors.push({
                code: 'MARKER_INVALID',
                message: `commit marker invalid: ${name} (${markerValidation.errors.join('; ')})`,
            });
            continue;
        }
        if (doc.commit_seq !== seqFromName) {
            errors.push({
                code: 'MARKER_INVALID',
                message: `commit marker seq mismatch: ${name} says ${doc.commit_seq}`,
            });
            continue;
        }
        markers.push({ seq: doc.commit_seq, doc, fileName: name });
    }

    markers.sort((a, b) => a.seq - b.seq);

    // Chain validation: seqs must be strictly consecutive from 1 and each
    // marker must bind the previous marker's exact file bytes.
    const markerBySeq = new Map();
    let prevBytesSha = null;
    let expectedSeq = 1;
    for (const marker of markers) {
        if (marker.seq !== expectedSeq) {
            errors.push({
                code: 'MARKER_CHAIN_BROKEN',
                message: `commit marker seq gap: expected ${expectedSeq}, found ${marker.seq}`,
            });
            break;
        }
        const read = readJsonFile(path.join(root, marker.fileName), options);
        if (marker.doc.previous_commit_seq !== (expectedSeq === 1 ? null : expectedSeq - 1)) {
            errors.push({
                code: 'MARKER_CHAIN_BROKEN',
                message: `commit marker ${marker.seq}: previous_commit_seq does not match chain`,
            });
            break;
        }
        if (marker.doc.previous_marker_sha256 !== prevBytesSha) {
            errors.push({
                code: 'MARKER_CHAIN_BROKEN',
                message: `commit marker ${marker.seq}: previous_marker_sha256 does not match the previous marker's bytes`,
            });
            break;
        }
        marker.fileSha = read.sha256;
        markerBySeq.set(marker.seq, marker);
        prevBytesSha = read.sha256;
        expectedSeq += 1;
    }

    const validMarkers = [...markerBySeq.values()];

    // Marker-bound file hash verification: every listed file must exist with
    // exactly the listed bytes.
    const markerBoundFiles = {};
    for (const marker of validMarkers) {
        for (const fileEntry of marker.doc.files) {
            markerBoundFiles[fileEntry.name] = fileEntry.sha256;
            let read = null;
            try {
                read = readJsonFile(path.join(root, fileEntry.name), options);
            } catch (error) {
                errors.push({
                    code: 'MARKER_FILE_MISMATCH',
                    message: `commit marker ${marker.seq} file missing: ${fileEntry.name} (${error.message})`,
                });
                continue;
            }
            if (read.sha256 !== fileEntry.sha256) {
                errors.push({
                    code: 'MARKER_FILE_MISMATCH',
                    message: `commit marker ${marker.seq} file sha mismatch: ${fileEntry.name}`,
                });
            }
        }
    }

    // Ledger versions: every store-state-<seq>.json bound by a valid marker.
    const ledgerVersions = [];
    for (const marker of validMarkers) {
        const ledgerName = ledgerFileNameForSeq(marker.seq);
        const ledgerFile = marker.doc.files.find(f => f.name === ledgerName);
        if (!ledgerFile) {
            errors.push({
                code: 'MARKER_INVALID',
                message: `commit marker ${marker.seq} does not bind a store-state ledger`,
            });
            continue;
        }
        try {
            ledgerVersions.push(readJsonFile(path.join(root, ledgerName), options).parsed);
        } catch (error) {
            errors.push({
                code: 'LEDGER_INVALID',
                message: `ledger unreadable: ${ledgerName} (${error.message})`,
            });
        }
    }

    // Residue scan: any non-marker file not bound by a valid marker.
    // P1-4: the exclusive store lock (`.staging-write.lock`) is an
    // OPERATIONAL control file, not store data: it exists only while a
    // commit holds the lock, is never bound by a marker, and is removed on
    // release (a stale lock left by a crash is recovered by the next
    // acquisition). Every OTHER unbound file — including a straggler tmp
    // from a failed write — is residue.
    const residue = [];
    for (const name of entries) {
        if (isMarkerFileName(name)) continue;
        if (name === STAGING_LOCK_FILE_NAME) continue;
        if (!Object.prototype.hasOwnProperty.call(markerBoundFiles, name)) {
            residue.push(name);
        }
    }
    if (residue.length > 0) {
        errors.push({
            code: 'UNCOMMITTED_RESIDUE',
            message: `uncommitted residue files present (not bound by any valid commit marker): ${residue.join(', ')}`,
        });
    }

    const latestSeq = validMarkers.length > 0 ? validMarkers[validMarkers.length - 1].seq : 0;
    const latestLedger = ledgerVersions.length > 0 ? ledgerVersions[ledgerVersions.length - 1] : emptyStoreState();

    return {
        ok: errors.length === 0,
        errors,
        markers: validMarkers,
        latestSeq,
        latestLedger,
        ledgerVersions,
        residue,
        markerBoundFiles,
    };
}

/**
 * Throwing variant for commit-time use: any problem with the existing
 * committed state (invalid markers, broken chain, residue) fails closed.
 */
function loadCommittedState(root, options = {}) {
    const collected = collectCommittedState(root, options);
    if (!collected.ok) {
        throw Object.assign(new Error(`store not in a valid committed state: ${collected.errors[0].message}`), {
            code: 'OUTPUT_CONFLICT',
            details: collected.errors,
        });
    }
    return collected;
}

// ─────────────────────────────────────────────────────────────
// Classification
// ─────────────────────────────────────────────────────────────

/**
 * Classify the terminal state of one observation against the current ledger
 * (pure). The converter artifact always carries ACCEPTED_NEW; the FINAL
 * artifact is rebuilt by commitObservations with the classified state
 * (FINDING_2 — artifact / summary / ledger three-way consistency).
 *
 * @param {object} args - { result: convertPair result, storeState }
 * @returns {{ terminal_state: string, reason: string, artifact: object|null }}
 */
function classifyAgainstStore(args = {}) {
    const result = args.result;
    const storeState = args.storeState || emptyStoreState();
    const sourceMatchId = String(result.source_match_id ?? (result.artifact && result.artifact.source_match_id) ?? '');
    const stable = String((result.artifact && result.artifact.stable_payload_sha256) || '');

    if (!result.ok) {
        return {
            terminal_state: result.terminal_state,
            reason: result.quarantine_status === 'quarantined' ? 'quarantined' : 'rejected',
            artifact: null,
        };
    }

    const key = observationKey(sourceMatchId, stable);
    if (storeState.observations[key]) {
        return {
            terminal_state: TERMINAL_STATES.ACCEPTED_REPEAT_EXACT,
            reason: 'exact_duplicate',
            artifact: null,
        };
    }

    // Same source_match_id with a different payload version: identity must
    // agree with the previously staged observation, else fail closed.
    const prior = Object.values(storeState.observations).filter(o => String(o.source_match_id) === sourceMatchId);
    if (prior.length > 0) {
        const artifact = result.artifact;
        const newIdentity = artifact.expected_identity || {};
        for (const p of prior) {
            if (canonicalJsonHash(p.expected_identity || {}) !== canonicalJsonHash(newIdentity)) {
                return {
                    terminal_state: TERMINAL_STATES.REJECTED_IDENTITY_INCONSISTENT,
                    reason: 'identity_conflict_with_staged_observation',
                    artifact: null,
                };
            }
        }
        return {
            terminal_state: TERMINAL_STATES.ACCEPTED_REPEAT_EQUIVALENT,
            reason: 'new_payload_version',
            artifact: result.artifact,
        };
    }

    return {
        terminal_state: TERMINAL_STATES.ACCEPTED_NEW,
        reason: 'first_observation',
        artifact: result.artifact,
    };
}

// ─────────────────────────────────────────────────────────────
// Build orchestration (commit protocol)
// ─────────────────────────────────────────────────────────────

function compareSummaryObservations(a, b) {
    if (a.source_match_id !== b.source_match_id) {
        return a.source_match_id < b.source_match_id ? -1 : 1;
    }
    const hashA = a.stable_payload_sha256 || '';
    const hashB = b.stable_payload_sha256 || '';
    if (hashA !== hashB) return hashA < hashB ? -1 : 1;
    return 0;
}

// R7-P2-2 (Codex round 7): a quarantine terminal state carries EXACTLY the
// error code that defines it. E013 (INTERNAL_CONTRACT_VIOLATION) is a
// "should never happen" sentinel — NOT a legal quarantine code — and a
// fallback that stringifies it into evidence files would commit records the
// D-group validator then rejects. The map is the single source of truth for
// the writer pre-loop and the D-group validator.
const QUARANTINE_STATE_ERROR_CODES = Object.freeze({
    [TERMINAL_STATES.QUARANTINED_VALIDATION_FAIL]: Object.freeze([ERROR_CODES.E011]),
    [TERMINAL_STATES.QUARANTINED_PROVENANCE_MISMATCH]: Object.freeze([ERROR_CODES.E008]),
});

// R10-P2-1 (Codex round 10): quarantine evidence NEVER persists caller-
// supplied error text. The pre-loop has already validated that the code is
// the EXACT code defining the declared terminal state (QUARANTINE_STATE_
// ERROR_CODES), so the reason derives deterministically from the validated
// code — a direct API caller injecting `errors:[{message:'<html>…'}]` can
// no longer write raw content into the evidence file, ledger or marker.
// The fallback is deterministic too (unreachable with the current map).
const QUARANTINE_REASON_BY_CODE = Object.freeze({
    [ERROR_CODES.E011]: 'value sanity fail (E011)',
    [ERROR_CODES.E008]: 'provenance hash mismatch (E008)',
});

/**
 * Stage converted observations into a single output root with the
 * LOGICAL_COMMIT_MARKER protocol. storeDir (if given) must equal outputRoot:
 * the store is the output root itself.
 *
 * @param {object} args - { results, outputRoot, storeDir, repositoryRoot,
 *                          runId, builtAt, fsImpl }
 * @returns {object} summary document
 */
/* eslint-disable-next-line complexity */
function commitObservations(args = {}) {
    const fileSystem = args.fsImpl || fs;
    const repositoryRoot = args.repositoryRoot || path.resolve(__dirname, '..', '..', '..');
    const outputRoot = verifyRepositoryExternalPath(args.outputRoot, {
        repositoryRoot,
        fsImpl: fileSystem,
    });
    if (args.storeDir !== undefined && args.storeDir !== null && args.storeDir !== '') {
        const storeDirResolved = verifyRepositoryExternalPath(args.storeDir, {
            repositoryRoot,
            fsImpl: fileSystem,
        });
        if (storeDirResolved !== outputRoot) {
            throw Object.assign(new Error('store-dir must equal output-root (single-root commit-marker store)'), {
                code: 'INPUT_ERROR',
            });
        }
    }
    const runId = String(args.runId || 'offline-staging-run');
    // R11-P2-1 (Codex round 11): runId is persisted into
    // summary.operations.converter_run_id — the CLI help already documents
    // `--run-id=<plain-identifier>`, so the exported API enforces the same
    // contract: a finite plain identifier, never arbitrary text.
    if (!/^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$/.test(runId)) {
        throw Object.assign(new Error(`runId must be a plain identifier (got '${runId}')`), {
            code: 'INPUT_ERROR',
        });
    }
    const results = Array.isArray(args.results) ? args.results : [];
    const builtAt = String(args.builtAt || '');
    // R10-P2-1 (Codex round 10): builtAt is persisted as `recorded_at` on
    // quarantine evidence — a direct caller could otherwise inject arbitrary
    // bytes into committed files through this free string. A non-empty
    // builtAt must be a strict ISO-8601 absolute timestamp (the CLI always
    // passes one); empty stays allowed for callers that omit it.
    if (builtAt !== '' && !isStrictAbsoluteTimestamp(builtAt)) {
        throw Object.assign(
            new Error(`builtAt must be a strict ISO-8601 absolute timestamp (got '${builtAt}')`),
            { code: 'INPUT_ERROR' }
        );
    }

    ensureRealDirectoryTree(outputRoot, fileSystem);

    // P1-4: the whole commit — residue scan, artifact/summary/ledger writes
    // AND the commit marker — runs under the exclusive per-store lock, so two
    // concurrent commits into the same store can never interleave their
    // multi-file transactions (one is refused via the lock or the
    // same-seq marker conflict).
    return withStoreLock(outputRoot, fileSystem, () => {
    // Fail closed on an invalid or residue-laden existing state.
    const committed = loadCommittedState(outputRoot, {
        fsImpl: fileSystem,
        repositoryRoot,
    });
    const storeState = committed.latestLedger;
    const seq = committed.latestSeq + 1;

    // R9-P2-1 (Codex round 9): the RAW result contract is enforced BEFORE
    // classification — classifyAgainstStore branches on result.ok TRUTHINESS
    // (a string 'false' or 1 is truthy success) and DISCARDS the raw
    // terminal_state for ok:true results (deriving it against the store), so
    // type-mismatched or self-contradictory results would otherwise be
    // silently upgraded to committed accepted snapshots. The exported API
    // must speak the exact converter contract:
    //   - ok is a REAL boolean;
    //   - ok:true declares ACCEPTED_NEW — retention then derives
    //     EXACT/EQUIVALENT/identity-conflict from the store state;
    //   - ok:false must not claim an accepted state — a "failed" result can
    //     never commit an artifact (LINKED_*/unknown states still fall
    //     through to the retainable-state whitelist below).
    // R11-P2-1 (Codex round 11): SNAPSHOT every result — one materialized
    // read of every field. An accessor/proxy-backed envelope could otherwise
    // return a legal `error_code` at gate time and injected text at write
    // time. Accessor-backed envelope scalars are refused upfront via a
    // descriptor scan (never invoking the getter); the remaining scalars are
    // then materialized by a JSON round-trip. `artifactInputs` keeps its
    // ORIGINAL reference — everything derived from it is re-validated and
    // re-hashed by the REPEAT_EQUIVALENT rebuild into a fresh plain object
    // before any byte is written.
    // R12-P2-1 (Codex round 12): the artifact is DEEP-SNAPSHOTTED here too,
    // not kept as the caller's reference — a transparent Proxy artifact
    // could otherwise return legal bytes to every descriptor read and then
    // inject raw content through a toJSON trap at the moment JSON.stringify
    // serializes the artifact file (validation, hashing and the marker
    // would all agree on bytes that differ from the written artifact).
    // snapshotStrictPlainData builds a deep copy from own-property
    // descriptors ONLY (JSON.stringify is never invoked on the caller's
    // object), and refuses accessors, proxies, non-plain prototypes,
    // non-finite numbers, cyclic references and excessive nesting — so the
    // artifact gate + validator + content scan + hashing + serialization
    // all read the SAME materialized bytes, and a cycle is a structured
    // INPUT_ERROR (R12-P3-1), never a RangeError. Every gate and every
    // write-phase read below uses the snapshot only — the caller's object is
    // never read again. A non-JSON-serializable envelope (cyclic, function
    // values) fails closed as INPUT_ERROR.
    let snapshots;
    try {
        snapshots = results.map(result => {
            // R13-P3-1 (Codex round 13): the RESULT ENVELOPE itself must not
            // be a Proxy — a transparent proxy passes Object.keys, descriptor
            // reads, destructuring and the JSON round-trip below and commits
            // today, contradicting the R11/R12 contract promise ("envelope
            // proxy → INPUT_ERROR"). Rejected before ANY field of the
            // caller's object is read — the snapshot below is the only read.
            if (util.types.isProxy(result)) {
                throw new TypeError('result envelope is a proxy');
            }
            for (const key of Object.keys(result)) {
                if (key === 'artifact' || key === 'artifactInputs') continue;
                const descriptor = Object.getOwnPropertyDescriptor(result, key);
                if (!descriptor || !('value' in descriptor)) {
                    throw new TypeError('accessor envelope field');
                }
            }
            const { artifact, artifactInputs, ...scalars } = result;
            return {
                ...JSON.parse(JSON.stringify(scalars)),
                artifact: snapshotStrictPlainData(artifact ?? null, 'artifact'),
                artifactInputs,
            };
        });
    } catch (error) {
        if (error instanceof TypeError && String(error.message || '').startsWith('artifact')) {
            throw Object.assign(
                new Error(`artifact must be strict plain JSON data (${error.message})`),
                { code: 'INPUT_ERROR' }
            );
        }
        throw Object.assign(
            new Error(
                'result envelope must be strict plain JSON data (no accessors, no inherited props, no proxies)'
            ),
            { code: 'INPUT_ERROR' }
        );
    }
    for (const snapshot of snapshots) {
        const result = snapshot;
        if (typeof result.ok !== 'boolean') {
            throw Object.assign(
                new Error(
                    `result.ok must be a boolean (got '${String(result.ok)}' of type ${typeof result.ok})`
                ),
                { code: 'INPUT_ERROR' }
            );
        }
        if (result.ok) {
            if (result.terminal_state !== TERMINAL_STATES.ACCEPTED_NEW) {
                throw Object.assign(
                    new Error(
                        `ok:true result must declare terminal_state ACCEPTED_NEW (got '${String(
                            result.terminal_state
                        )}') — final states are derived against the store`
                    ),
                    { code: 'INPUT_ERROR' }
                );
            }
            // R11-P2-1 (Codex round 11): an accepted raw result must not
            // carry a non-null error_code — buildSummary persists
            // `error_code: result.error_code || null` into the committed
            // summary, so a free-text error_code on an accepted result would
            // write arbitrary bytes into the marker-bound summary. The
            // converter emits null here; null/absent is the only legal value.
            if (result.error_code !== undefined && result.error_code !== null) {
                throw Object.assign(
                    new Error(
                        `ok:true result must not carry an error_code (got '${String(result.error_code)}')`
                    ),
                    { code: 'INPUT_ERROR' }
                );
            }
        } else if (
            result.terminal_state === TERMINAL_STATES.ACCEPTED_NEW ||
            result.terminal_state === TERMINAL_STATES.ACCEPTED_REPEAT_EXACT ||
            result.terminal_state === TERMINAL_STATES.ACCEPTED_REPEAT_EQUIVALENT
        ) {
            throw Object.assign(
                new Error(
                    `ok:false result must declare a rejected or quarantine terminal_state (got '${String(
                        result.terminal_state
                    )}')`
                ),
                { code: 'INPUT_ERROR' }
            );
        }
    }

    // ── 1. classify every result against the ledger (pure, no writes) ──
    // The snapshots are the ONLY objects downstream code ever reads — the
    // classification, summary rows, quarantine evidence, ledger merge and
    // write plan all derive from these materialized values.
    const classified = snapshots.map(result => ({
        result,
        classification: classifyAgainstStore({ result, storeState }),
    }));

    // ── 2. collect the writes to make (final artifacts, quarantine,
    //      ledger merge, summary) ──
    const artifactWrites = [];
    const quarantineWrites = [];
    const newObservations = {};
    const quarantineEntries = [];
    const newObservationKeys = new Set();
    // R3-P2-1: quarantine evidence is keyed by (source_match_id, error_code)
    // and its content carries a per-run recorded_at — re-running the same
    // quarantined input would otherwise collide with the committed evidence
    // file (divergent bytes → OUTPUT_CONFLICT) and rewrite the ledger key.
    // The FIRST recording is immutable evidence: committed or in-batch keys
    // are reused (no duplicate write, no ledger churn), exactly like
    // byte-identical artifact EXACT replay.
    const committedQuarantines = storeState.quarantines || {};
    const inBatchQuarantineKeys = new Set();

    // R5-P2-1 (Codex round 5): commitObservations is an EXPORTED runtime API —
    // results are not only produced by the converter, so every result must be
    // validated BEFORE any filename is derived from it. A direct caller
    // passing an illegal source_match_id (e.g. `x/../../escaped`) could
    // otherwise escape outputRoot via path.join. Fail closed:
    //   - the effective source id (result, falling back to the artifact) must
    //     be numeric — filenames embed it raw;
    //   - result.source_match_id and artifact.source_match_id must agree.
    // R6-P2-1 (Codex round 6): the input contract must close COMPLETELY —
    // no conditional/truthy checks that a non-string or falsy value can slip
    // through (a numeric `stable_payload_sha256` or a falsy `error_code`
    // previously skipped validation and was stringified into file names):
    //   - accepted-classified results must carry a PLAIN artifact whose
    //     stable_payload_sha256 is a string of 64 lowercase hex, and the
    //     artifact must pass the FULL artifact validator (the same one the
    //     store validator applies to committed artifacts);
    //   - quarantine-classified results must carry a REGISTRY error_code
    //     (string `E###` in ERROR_CODES — no silent E013 fallback), a
    //     quarantine terminal state, and `quarantine_status === 'quarantined'`.
    for (const item of classified) {
        const result = item.result;
        const cls = item.classification;
        const artifact = result.artifact;
        const resultId =
            result.source_match_id === undefined || result.source_match_id === null
                ? ''
                : String(result.source_match_id);
        const artifactId =
            artifact && artifact.source_match_id !== undefined && artifact.source_match_id !== null
                ? String(artifact.source_match_id)
                : '';
        const effectiveId = String(result.source_match_id ?? (artifact && artifact.source_match_id) ?? '');
        if (!/^\d+$/.test(effectiveId)) {
            throw Object.assign(
                new Error(`result source_match_id must be numeric (got '${effectiveId}')`),
                { code: 'INPUT_ERROR' }
            );
        }
        // R7-P3-2 (Codex round 7): bound the id BEFORE any filename or ledger
        // key derives from it — an arbitrarily long digit id must fail here
        // with a structured error, not at the filesystem (ENAMETOOLONG).
        if (effectiveId.length > MAX_SOURCE_MATCH_ID_LENGTH) {
            throw Object.assign(
                new Error(
                    `result source_match_id exceeds ${MAX_SOURCE_MATCH_ID_LENGTH} digits (got ${effectiveId.length})`
                ),
                { code: 'INPUT_ERROR' }
            );
        }
        if (resultId !== '' && artifactId !== '' && resultId !== artifactId) {
            throw Object.assign(
                new Error(
                    `result.source_match_id ${resultId} disagrees with artifact.source_match_id ${artifactId}`
                ),
                { code: 'INPUT_ERROR' }
            );
        }
        const isAccepted =
            cls.terminal_state === TERMINAL_STATES.ACCEPTED_NEW ||
            cls.terminal_state === TERMINAL_STATES.ACCEPTED_REPEAT_EQUIVALENT ||
            cls.terminal_state === TERMINAL_STATES.ACCEPTED_REPEAT_EXACT;
        const isQuarantine =
            cls.terminal_state === TERMINAL_STATES.QUARANTINED_VALIDATION_FAIL ||
            cls.terminal_state === TERMINAL_STATES.QUARANTINED_PROVENANCE_MISMATCH;
        const isRejected =
            cls.terminal_state === TERMINAL_STATES.REJECTED_IDENTITY_INCONSISTENT ||
            cls.terminal_state === TERMINAL_STATES.REJECTED_PROVENANCE_BROKEN ||
            cls.terminal_state === TERMINAL_STATES.REJECTED_SCHEMA_UNKNOWN;
        // R8-P2-2 (Codex round 8): this store retains EXACTLY the
        // accepted/rejected/quarantine terminal states — LINKED_*/LINK_*
        // are downstream canonical-link states the validator's count
        // arithmetic does not recognize, so a commit that wrote one would
        // succeed while producing a store its own validator rejects
        // (processed_count=1 but every bucket 0). classifyAgainstStore
        // passes the result's terminal_state through VERBATIM for ok:false
        // results, so this gate is the only place the exported API's
        // unretainable states (LINKED_CANONICAL, LINK_PENDING, LINK_BLOCKED,
        // or any typo) can be refused BEFORE any summary/ledger/marker byte
        // is written.
        if (!isAccepted && !isRejected && !isQuarantine) {
            throw Object.assign(
                new Error(
                    `result terminal_state '${String(cls.terminal_state)}' is not retainable by the staging store (accepted/rejected/quarantined only)`
                ),
                { code: 'INPUT_ERROR' }
            );
        }
        // R8-P2-2 (Codex round 8): `ok` and the classified state must agree.
        // classifyAgainstStore derives accepted states (and
        // REJECTED_IDENTITY_INCONSISTENT, the identity-conflict-with-staged-
        // observation path) ONLY from ok:true results and passes
        // rejected/quarantine states through ONLY from ok:false results —
        // any other pairing is an exported-API caller lying about the result
        // (e.g. ok:false with a valid accepted artifact would otherwise
        // commit an artifact from a "failed" result).
        if (result.ok) {
            if (!isAccepted && cls.terminal_state !== TERMINAL_STATES.REJECTED_IDENTITY_INCONSISTENT) {
                throw Object.assign(
                    new Error(
                        `ok:true result cannot classify as '${String(cls.terminal_state)}' (accepted or REJECTED_IDENTITY_INCONSISTENT only)`
                    ),
                    { code: 'INPUT_ERROR' }
                );
            }
        } else if (isAccepted) {
            throw Object.assign(
                new Error(
                    `ok:false result cannot classify as accepted state '${String(cls.terminal_state)}'`
                ),
                { code: 'INPUT_ERROR' }
            );
        }
        if (isAccepted) {
            if (!artifact || typeof artifact !== 'object' || Array.isArray(artifact)) {
                throw Object.assign(
                    new Error('accepted result must carry a plain artifact object'),
                    { code: 'INPUT_ERROR' }
                );
            }
            // R7-P2-1 (Codex round 7): "plain object" is not enough —
            // Object.create(validArtifact) inherits every field, and getters
            // can return valid values at validation time and different ones
            // at write time. Only strict plain JSON data passes.
            if (!isPlainJsonData(artifact)) {
                throw Object.assign(
                    new Error(
                        'accepted result artifact must be plain JSON data (no inherited props, no accessors)'
                    ),
                    { code: 'INPUT_ERROR' }
                );
            }
            if (
                typeof artifact.stable_payload_sha256 !== 'string' ||
                !/^[0-9a-f]{64}$/.test(artifact.stable_payload_sha256)
            ) {
                throw Object.assign(
                    new Error('artifact stable_payload_sha256 must be a 64-lowercase-hex string'),
                    { code: 'INPUT_ERROR' }
                );
            }
            // R6-P2-1: full artifact validation — a direct caller's tampered
            // artifact (bad hashes, bad identity, broken integrity) is
            // rejected before any filename is derived or any byte is written.
            const artifactValidation = validateStagingArtifact(artifact);
            if (!artifactValidation.ok) {
                throw Object.assign(
                    new Error(`artifact invalid: ${artifactValidation.errors.join('; ')}`),
                    { code: 'INPUT_ERROR' }
                );
            }
        }
        if (isQuarantine) {
            const errorCode = result.error_code;
            if (
                typeof errorCode !== 'string' ||
                !/^E\d{3}$/.test(errorCode) ||
                !Object.values(ERROR_CODES).includes(errorCode)
            ) {
                throw Object.assign(
                    new Error(
                        `quarantined result must carry a registry error_code (got '${String(errorCode)}')`
                    ),
                    { code: 'INPUT_ERROR' }
                );
            }
            if (
                result.terminal_state !== TERMINAL_STATES.QUARANTINED_VALIDATION_FAIL &&
                result.terminal_state !== TERMINAL_STATES.QUARANTINED_PROVENANCE_MISMATCH
            ) {
                throw Object.assign(
                    new Error(
                        `quarantined result terminal_state must be a quarantine state (got '${String(
                            result.terminal_state
                        )}')`
                    ),
                    { code: 'INPUT_ERROR' }
                );
            }
            if (result.quarantine_status !== 'quarantined') {
                throw Object.assign(
                    new Error(`quarantined result quarantine_status must be 'quarantined'`),
                    { code: 'INPUT_ERROR' }
                );
            }
            // R7-P2-2 (Codex round 7): the code must be the EXACT code that
            // defines the declared terminal state — a registry-valid but
            // mismatched code (E013 on QUARANTINED_VALIDATION_FAIL) would
            // otherwise be written as evidence the D-group validator then
            // rejects. No fallback can mask a mismatched pair.
            const allowedCodes = QUARANTINE_STATE_ERROR_CODES[result.terminal_state] || [];
            if (!allowedCodes.includes(errorCode)) {
                throw Object.assign(
                    new Error(
                        `quarantined result error_code ${errorCode} does not match terminal_state ${result.terminal_state} (allowed: ${allowedCodes.join(
                            '/'
                        )})`
                    ),
                    { code: 'INPUT_ERROR' }
                );
            }
        }
        // R10-P2-1 (Codex round 10): the REJECTED envelope is tightened too —
        // the summary records `error_code` for rejected observations, so a
        // direct caller could otherwise inject arbitrary text into the
        // committed summary the same way quarantine_reason allowed. Only
        // ok:false raw-declared rejections are gated (ok:true-derived
        // REJECTED_IDENTITY_INCONSISTENT carries the incoming version's
        // null error_code by design).
        if (isRejected && !result.ok) {
            const errorCode = result.error_code;
            if (
                typeof errorCode !== 'string' ||
                !/^E\d{3}$/.test(errorCode) ||
                !Object.values(ERROR_CODES).includes(errorCode)
            ) {
                throw Object.assign(
                    new Error(
                        `rejected result must carry a registry error_code (got '${String(errorCode)}')`
                    ),
                    { code: 'INPUT_ERROR' }
                );
            }
        }
    }

    for (const item of classified) {
        const result = item.result;
        const cls = item.classification;
        const sourceMatchId = String(
            result.source_match_id ?? (result.artifact && result.artifact.source_match_id) ?? ''
        );
        if (
            cls.terminal_state === TERMINAL_STATES.ACCEPTED_NEW ||
            cls.terminal_state === TERMINAL_STATES.ACCEPTED_REPEAT_EQUIVALENT
        ) {
            let artifact = cls.artifact;
            if (cls.terminal_state === TERMINAL_STATES.ACCEPTED_REPEAT_EQUIVALENT) {
                // FINDING_2: rebuild with the FINAL terminal state — the business
                // hash and the integrity hash are recomputed over the final state.
                const inputs = result.artifactInputs || {};
                artifact = buildStagingArtifact({
                    payload: inputs.payload,
                    manifest: inputs.manifest,
                    validation: result.validation,
                    payloadFileSha256: inputs.payloadFileSha256,
                    terminalState: TERMINAL_STATES.ACCEPTED_REPEAT_EQUIVALENT,
                });
                // R7-P1-2 (Codex round 7): the FINAL artifact — the exact
                // snapshot that will be written, ledgered and markered — must
                // pass the same contract as the pre-checked input. The rebuild
                // derives from `artifactInputs`, which an exported-API caller
                // fully controls: a rebuild missing its stable hash, identity,
                // terminal state or required fields is refused BEFORE any byte
                // is written. Summary, ledger and writer all keep referencing
                // this same snapshot (P0-2 write-back below).
                if (!isPlainJsonData(artifact)) {
                    throw Object.assign(
                        new Error('rebuilt REPEAT_EQUIVALENT artifact is not plain JSON data'),
                        { code: 'INPUT_ERROR' }
                    );
                }
                if (
                    typeof artifact.stable_payload_sha256 !== 'string' ||
                    !/^[0-9a-f]{64}$/.test(artifact.stable_payload_sha256)
                ) {
                    throw Object.assign(
                        new Error(
                            'rebuilt REPEAT_EQUIVALENT artifact stable_payload_sha256 must be a 64-lowercase-hex string'
                        ),
                        { code: 'INPUT_ERROR' }
                    );
                }
                if (String(artifact.source_match_id ?? '') !== sourceMatchId) {
                    throw Object.assign(
                        new Error(
                            `rebuilt REPEAT_EQUIVALENT artifact source_match_id ${String(
                                artifact.source_match_id
                            )} disagrees with ${sourceMatchId}`
                        ),
                        { code: 'INPUT_ERROR' }
                    );
                }
                if (artifact.import_terminal_state !== TERMINAL_STATES.ACCEPTED_REPEAT_EQUIVALENT) {
                    throw Object.assign(
                        new Error(
                            `rebuilt REPEAT_EQUIVALENT artifact import_terminal_state must be ACCEPTED_REPEAT_EQUIVALENT`
                        ),
                        { code: 'INPUT_ERROR' }
                    );
                }
                const rebuiltValidation = validateStagingArtifact(artifact);
                if (!rebuiltValidation.ok) {
                    throw Object.assign(
                        new Error(
                            `rebuilt REPEAT_EQUIVALENT artifact invalid: ${rebuiltValidation.errors.join('; ')}`
                        ),
                        { code: 'INPUT_ERROR' }
                    );
                }
                // P0-2: write the FINAL artifact back into the classification so
                // the summary (buildSummary reads cls.artifact) and everything
                // downstream derive from the SAME artifact the ledger records
                // and the artifact file stores. Without this write-back the
                // summary business hash would keep referencing the rebuilt-
                // before (ACCEPTED_NEW) artifact and the three records would
                // silently disagree.
                item.classification = { ...cls, artifact };
            }
            const key = observationKey(sourceMatchId, artifact.stable_payload_sha256);
            if (newObservationKeys.has(key)) {
                item.classification = {
                    terminal_state: TERMINAL_STATES.ACCEPTED_REPEAT_EXACT,
                    reason: 'in_batch_duplicate',
                    artifact: null,
                };
                continue;
            }
            newObservationKeys.add(key);
            const fileName = artifactFileName(sourceMatchId, artifact.stable_payload_sha256);
            artifactWrites.push({ name: fileName, doc: artifact, key });
            newObservations[key] = {
                source_match_id: sourceMatchId,
                stable_payload_sha256: artifact.stable_payload_sha256,
                artifact_file: fileName,
                expected_identity: artifact.expected_identity,
                first_imported_at: String(artifact.generated_at),
                terminal_state: cls.terminal_state,
                business_hash: artifact.business_hash,
            };
        } else if (
            cls.terminal_state === TERMINAL_STATES.QUARANTINED_VALIDATION_FAIL ||
            cls.terminal_state === TERMINAL_STATES.QUARANTINED_PROVENANCE_MISMATCH
        ) {
            // R7-P2-2 (Codex round 7): the pre-loop gate has already verified
            // this code matches the declared quarantine terminal state — no
            // E013 fallback can substitute for a mismatched or missing code.
            const errorCode = result.error_code;
            const fileName = quarantineFileName(sourceMatchId, errorCode);
            const quarantineKey = `${sourceMatchId}:${errorCode}`;
            if (
                !Object.prototype.hasOwnProperty.call(committedQuarantines, quarantineKey) &&
                !inBatchQuarantineKeys.has(quarantineKey)
            ) {
                // R3-P2-1: first recording of this (source_match_id,
                // error_code) — write the evidence file + ledger entry. A
                // re-run of the same quarantined input reuses the immutable
                // first recording instead of colliding on the file.
                inBatchQuarantineKeys.add(quarantineKey);
                const quarantineDoc = {
                    schema_version: 'fotmob-detail-staging-quarantine/v1',
                    source_match_id: sourceMatchId,
                    terminal_state: cls.terminal_state,
                    error_code: errorCode,
                    quarantine_status: 'quarantined',
                    // R10-P2-1: the reason derives from the VALIDATED error
                    // code — the caller-supplied errors[0].message is never
                    // persisted (a direct caller could otherwise inject raw
                    // HTML/payload bytes into the committed evidence).
                    quarantine_reason:
                        QUARANTINE_REASON_BY_CODE[errorCode] || `quarantined (${errorCode})`,
                    recorded_at: builtAt,
                    // Evidence is the identity + error, never the full payload.
                };
                quarantineWrites.push({ name: fileName, doc: quarantineDoc });
                // R3-P2-1: [key, entry] pairs — Object.fromEntries requires
                // array pairs, not {key, entry} objects (the old shape
                // silently produced {undefined: undefined}, which
                // JSON.stringify drops, so the ledger never recorded
                // quarantine evidence at all).
                quarantineEntries.push([
                    quarantineKey,
                    {
                        ...quarantineDoc,
                        quarantine_file: fileName,
                    },
                ]);
            }
        }
    }

    // Ledger merge: existing entries are preserved byte-for-byte by
    // construction (new keys only) — the immutable ledger VERSIONS make this
    // verifiable by the validator (no record is ever deleted).
    const nextStoreState = {
        schema_version: STORE_STATE_SCHEMA,
        observations: { ...storeState.observations, ...newObservations },
        quarantines: {
            ...(storeState.quarantines || {}),
            ...Object.fromEntries(quarantineEntries),
        },
    };

    const summary = buildSummary({
        classified,
        outputRoot,
        runId,
        builtAt,
        storeState: nextStoreState,
    });

    // R8-P2-2 (Codex round 8): the summary is the document the store
    // validator re-checks (A-group) — validate it HERE, before any byte is
    // written, so a commit can never succeed while producing a summary its
    // own validator rejects. Defense in depth behind the pre-loop
    // terminal-state gate: any future state/arithmetic drift between
    // buildSummary and validateSummaryDoc fails closed at commit time
    // instead of being committed as an invalid store.
    const summaryErrors = [];
    validateSummaryDoc(summary, summaryErrors);
    if (summaryErrors.length > 0) {
        throw Object.assign(
            new Error(`summary failed self-validation: ${summaryErrors.map(e => e.message).join('; ')}`),
            { code: 'INPUT_ERROR' }
        );
    }

    // ── 3. write everything (per-file atomic), marker LAST ──
    const writePlan = [
        ...artifactWrites
            .slice()
            .sort((a, b) => (a.name < b.name ? -1 : 1))
            .map(w => ({ name: w.name, doc: w.doc })),
        ...quarantineWrites
            .slice()
            .sort((a, b) => (a.name < b.name ? -1 : 1))
            .map(w => ({ name: w.name, doc: w.doc })),
        { name: summaryFileNameForSeq(seq), doc: summary },
        { name: ledgerFileNameForSeq(seq), doc: nextStoreState },
    ];

    // R5-P2-1: final containment gate on EVERY file this commit writes — the
    // name must be a plain basename (no separators) and its resolved path
    // must stay inside outputRoot. Defense in depth: even if a future code
    // path derived a name from unvalidated input, the write cannot escape
    // the store.
    const resolvedRoot = path.resolve(outputRoot);
    for (const write of writePlan) {
        const name = String(write.name || '');
        if (name !== path.basename(name) || !path.resolve(resolvedRoot, name).startsWith(resolvedRoot + path.sep)) {
            throw Object.assign(new Error(`commit file name escapes the output root: ${name}`), {
                code: 'INPUT_ERROR',
            });
        }
        // R10-P2-1 (Codex round 10): every document this commit persists —
        // artifact, quarantine evidence, summary AND ledger — must be strict
        // plain JSON data before any byte is written. The per-class gates
        // already check artifacts; this covers the remaining documents so a
        // direct caller cannot smuggle raw payload bytes into a committed
        // file through a document the per-class gates never inspected.
        if (!isPlainJsonData(write.doc)) {
            throw Object.assign(
                new Error(`commit document is not plain JSON data: ${write.name}`),
                { code: 'INPUT_ERROR' }
            );
        }
    }

    const writtenFiles = [];
    try {
        for (const write of writePlan) {
            const result = writeJsonAtomically(path.join(outputRoot, write.name), write.doc, {
                fsImpl: fileSystem,
                repositoryRoot,
            });
            if (result.written) {
                writtenFiles.push({ name: write.name, sha256: result.sha256 });
            }
        }
        // The commit marker is the ONLY commit point: it binds every file of
        // this commit (including its own predecessor's bytes via
        // previous_marker_sha256 — the previous marker's exact file hash, so a
        // tampered or missing old marker breaks the chain).
        const previousMarkerSha = seq === 1 ? null : committed.markers[committed.markers.length - 1].fileSha;
        const allFiles = writePlan.map(w => ({
            name: w.name,
            sha256: crypto
                .createHash('sha256')
                .update(JSON.stringify(w.doc, null, 2) + '\n', 'utf8')
                .digest('hex'),
        }));
        allFiles.sort((a, b) => (a.name < b.name ? -1 : 1));
        const marker = {
            schema_version: COMMIT_MARKER_SCHEMA,
            commit_seq: seq,
            previous_commit_seq: seq === 1 ? null : seq - 1,
            previous_marker_sha256: previousMarkerSha,
            files: allFiles,
        };
        writeJsonAtomically(path.join(outputRoot, markerFileNameForSeq(seq)), marker, {
            fsImpl: fileSystem,
            repositoryRoot,
        });
    } catch (error) {
        // Rollback: remove ONLY the files this attempt actually wrote. Files
        // that pre-existed (existing_identical skips) are never touched. Old
        // committed state stays intact; if any file survives, the next commit's
        // residue check and the validator will report it.
        for (const written of writtenFiles.reverse()) {
            try {
                fileSystem.unlinkSync(path.join(outputRoot, written.name));
            } catch {
                /* best effort */
            }
        }
        throw error;
    }

    return summary;
    });
}

/**
 * Build the deterministic summary document. Business projection (counts +
 * per-observation hashes) is byte-deterministic across identical inputs;
 * operations fields (runId, builtAt, output root, store counts) are excluded
 * from any business hash. The stable payload hash is recorded for EVERY
 * accepted observation (including ACCEPTED_REPEAT_EXACT folds) so the
 * validator can re-derive the ledger key.
 */
/* eslint-disable-next-line complexity */
function buildSummary(args = {}) {
    const classified = args.classified || [];
    const outputRoot = args.outputRoot;
    const runId = String(args.runId || '');
    const builtAt = String(args.builtAt || '');
    const storeState = args.storeState || emptyStoreState();

    const terminalCounts = {};
    const observations = [];
    for (const item of classified) {
        const result = item.result;
        const cls = item.classification;
        const sourceMatchId = String(
            result.source_match_id ?? (result.artifact && result.artifact.source_match_id) ?? ''
        );
        const state = cls.terminal_state;
        terminalCounts[state] = (terminalCounts[state] || 0) + 1;
        const observation = {
            source_match_id: sourceMatchId,
            terminal_state: state,
            reason: cls.reason,
            error_code: result.error_code || null,
        };
        if (
            state === TERMINAL_STATES.QUARANTINED_VALIDATION_FAIL ||
            state === TERMINAL_STATES.QUARANTINED_PROVENANCE_MISMATCH
        ) {
            // R6-P2-2 (Codex round 6): the summary quarantine row binds to the
            // ledger by the SAME derived key/file name the ledger uses — the
            // validator cross-checks `source_match_id:error_code` key and the
            // quarantine file against the ledger + marker.
            // R7-P2-2 (Codex round 7): no E013 fallback — the commit pre-loop
            // has already validated the exact code for this terminal state.
            const errorCode = result.error_code;
            observation.quarantine_file = quarantineFileName(sourceMatchId, errorCode);
        }
        if (cls.artifact) {
            observation.stable_payload_sha256 = cls.artifact.stable_payload_sha256;
            observation.business_hash = cls.artifact.business_hash;
            observation.artifact_file = artifactFileName(sourceMatchId, cls.artifact.stable_payload_sha256);
        } else if (result.ok) {
            // ACCEPTED_REPEAT_EXACT fold: no new artifact, but the key's stable
            // hash is still recorded so the validator can find the original key.
            observation.stable_payload_sha256 = result.artifact.stable_payload_sha256;
            observation.business_hash = null;
            observation.artifact_file = null;
        }
        observations.push(observation);
    }
    observations.sort(compareSummaryObservations);

    // ERRATA_3: the business projection must be byte-deterministic across
    // identical inputs — run-scoped values (paths, run ids, timestamps) live
    // in `operations` and never enter the projection or its hash.
    const businessProjection = {
        schema_version: 'fotmob-detail-staging-summary/v1',
        processed_count: observations.length,
        accepted_new_count: terminalCounts[TERMINAL_STATES.ACCEPTED_NEW] || 0,
        accepted_repeat_exact_count: terminalCounts[TERMINAL_STATES.ACCEPTED_REPEAT_EXACT] || 0,
        accepted_repeat_equivalent_count: terminalCounts[TERMINAL_STATES.ACCEPTED_REPEAT_EQUIVALENT] || 0,
        rejected_count:
            (terminalCounts[TERMINAL_STATES.REJECTED_IDENTITY_INCONSISTENT] || 0) +
            (terminalCounts[TERMINAL_STATES.REJECTED_PROVENANCE_BROKEN] || 0) +
            (terminalCounts[TERMINAL_STATES.REJECTED_SCHEMA_UNKNOWN] || 0),
        quarantined_count:
            (terminalCounts[TERMINAL_STATES.QUARANTINED_VALIDATION_FAIL] || 0) +
            (terminalCounts[TERMINAL_STATES.QUARANTINED_PROVENANCE_MISMATCH] || 0),
        observations,
    };
    businessProjection.business_projection_sha256 = canonicalJsonHash(businessProjection);

    return {
        schema_version: 'fotmob-detail-staging-summary/v1',
        business_projection: businessProjection,
        operations: {
            converter_run_id: runId,
            built_at: builtAt,
            output_root: String(outputRoot),
            store_observation_count: Object.keys(storeState.observations || {}).length,
        },
    };
}

// ─────────────────────────────────────────────────────────────
// Validate — full consistency validator (FINDING_5)
// ─────────────────────────────────────────────────────────────

function validateSummaryDoc(summary, errors) {
    if (!summary || typeof summary !== 'object' || summary.schema_version !== 'fotmob-detail-staging-summary/v1') {
        errors.push({ code: 'SUMMARY_INVALID', message: 'summary schema_version invalid' });
        return;
    }
    const bp = summary.business_projection;
    if (!bp || typeof bp !== 'object' || !Array.isArray(bp.observations)) {
        errors.push({ code: 'SUMMARY_INVALID', message: 'summary business_projection.observations missing' });
        return;
    }
    // R13-P2-4 (Codex round 13): every observation must be a non-array
    // object BEFORE any field read — a raw/null row previously threw at
    // observation.terminal_state instead of yielding a structured
    // SUMMARY_INVALID, so a tampered store crashed programmatic callers.
    // Each malformed index is reported, then this summary's remaining field
    // reads are short-circuited (the hash recomputation, counts, sort and
    // duplicate checks below all assume well-formed rows).
    let malformedObservation = false;
    for (let i = 0; i < bp.observations.length; i += 1) {
        const observation = bp.observations[i];
        if (!observation || typeof observation !== 'object' || Array.isArray(observation)) {
            malformedObservation = true;
            errors.push({
                code: 'SUMMARY_INVALID',
                message: `summary observation at index ${i} must be an object`,
            });
        }
    }
    if (malformedObservation) {
        return;
    }
    // 2. business projection hash recomputation.
    const projectionCopy = { ...bp };
    delete projectionCopy.business_projection_sha256;
    if (canonicalJsonHash(projectionCopy) !== String(bp.business_projection_sha256 || '')) {
        errors.push({
            code: 'SUMMARY_INVALID',
            message: 'business_projection_sha256 does not match recomputed projection',
        });
    }
    // 3./4. counts.
    if (bp.processed_count !== bp.observations.length) {
        errors.push({ code: 'SUMMARY_INVALID', message: 'processed_count does not match observations length' });
    }
    const counts = {};
    const stateValues = Object.values(TERMINAL_STATES);
    for (const observation of bp.observations) {
        const state = String(observation.terminal_state || '');
        if (!stateValues.includes(state)) {
            errors.push({ code: 'SUMMARY_INVALID', message: `unknown terminal state in summary: ${state}` });
        }
        counts[state] = (counts[state] || 0) + 1;
    }
    if (
        bp.accepted_new_count !== (counts[TERMINAL_STATES.ACCEPTED_NEW] || 0) ||
        bp.accepted_repeat_exact_count !== (counts[TERMINAL_STATES.ACCEPTED_REPEAT_EXACT] || 0) ||
        bp.accepted_repeat_equivalent_count !== (counts[TERMINAL_STATES.ACCEPTED_REPEAT_EQUIVALENT] || 0)
    ) {
        errors.push({
            code: 'SUMMARY_INVALID',
            message: 'summary accepted counts do not match re-counted observations',
        });
    }
    const expectedRejected =
        (counts[TERMINAL_STATES.REJECTED_IDENTITY_INCONSISTENT] || 0) +
        (counts[TERMINAL_STATES.REJECTED_PROVENANCE_BROKEN] || 0) +
        (counts[TERMINAL_STATES.REJECTED_SCHEMA_UNKNOWN] || 0);
    const expectedQuarantined =
        (counts[TERMINAL_STATES.QUARANTINED_VALIDATION_FAIL] || 0) +
        (counts[TERMINAL_STATES.QUARANTINED_PROVENANCE_MISMATCH] || 0);
    if (bp.rejected_count !== expectedRejected) {
        errors.push({
            code: 'SUMMARY_INVALID',
            message: 'rejected_count does not match re-counted rejected observations',
        });
    }
    if (bp.quarantined_count !== expectedQuarantined) {
        errors.push({
            code: 'SUMMARY_INVALID',
            message: 'quarantined_count does not match re-counted quarantined observations',
        });
    }
    // 5. arithmetic.
    const arithmetic =
        bp.accepted_new_count +
        bp.accepted_repeat_exact_count +
        bp.accepted_repeat_equivalent_count +
        bp.rejected_count +
        bp.quarantined_count;
    if (arithmetic !== bp.processed_count) {
        errors.push({ code: 'SUMMARY_INVALID', message: 'terminal state counts do not sum to processed_count' });
    }
    // 6. deterministic sort order.
    for (let i = 1; i < bp.observations.length; i += 1) {
        if (compareSummaryObservations(bp.observations[i - 1], bp.observations[i]) > 0) {
            errors.push({ code: 'SUMMARY_INVALID', message: 'summary observations are not deterministically sorted' });
            break;
        }
    }
    // 7. no duplicate observation entries.
    const seenRows = new Set();
    for (const observation of bp.observations) {
        const rowKey = JSON.stringify({
            source_match_id: observation.source_match_id,
            stable_payload_sha256: observation.stable_payload_sha256 || null,
            terminal_state: observation.terminal_state,
            artifact_file: observation.artifact_file || null,
        });
        if (seenRows.has(rowKey)) {
            errors.push({ code: 'SUMMARY_INVALID', message: 'duplicate observation entry in summary' });
        }
        seenRows.add(rowKey);
    }
    // 9. artifact file name legality.
    for (const observation of bp.observations) {
        const artifactFile = observation.artifact_file;
        if (artifactFile !== undefined && artifactFile !== null && artifactFile !== '') {
            if (
                !isArtifactFileName(String(artifactFile)) ||
                path.basename(String(artifactFile)) !== String(artifactFile)
            ) {
                errors.push({
                    code: 'SUMMARY_INVALID',
                    message: `summary references an illegal artifact file name: ${artifactFile}`,
                });
            }
        }
        if (
            observation.stable_payload_sha256 !== undefined &&
            observation.stable_payload_sha256 !== null &&
            observation.stable_payload_sha256 !== '' &&
            !/^[0-9a-f]{64}$/.test(String(observation.stable_payload_sha256))
        ) {
            errors.push({
                code: 'SUMMARY_INVALID',
                message: 'summary observation stable_payload_sha256 must be 64-hex',
            });
        }
    }
    // 10. operations fields must never enter the business projection.
    if (summary.operations && typeof summary.operations === 'object') {
        for (const operationKey of Object.keys(summary.operations)) {
            if (Object.prototype.hasOwnProperty.call(bp, operationKey)) {
                errors.push({
                    code: 'SUMMARY_INVALID',
                    message: `operations field leaked into business projection: ${operationKey}`,
                });
            }
        }
    }
}

/**
 * Full output-root consistency validator (PR1817 remediation, FINDING_5):
 * commit markers, ledger versions (monotonic), summaries (recomputed),
 * artifacts (validated + orphan detection), quarantine records
 * (bidirectional), and residue reporting.
 */
/* eslint-disable-next-line complexity */
function validateOutputRoot(outputRoot, options = {}) {
    const fileSystem = options.fsImpl || fs;
    const repositoryRoot = options.repositoryRoot || path.resolve(__dirname, '..', '..', '..');
    const abs = verifyRepositoryExternalPath(outputRoot, {
        repositoryRoot,
        fsImpl: fileSystem,
    });
    if (options.storeDir !== undefined && options.storeDir !== null && options.storeDir !== '') {
        const storeDirResolved = verifyRepositoryExternalPath(options.storeDir, {
            repositoryRoot,
            fsImpl: fileSystem,
        });
        if (storeDirResolved !== abs) {
            throw Object.assign(new Error('store-dir must equal output-root (single-root commit-marker store)'), {
                code: 'INPUT_ERROR',
            });
        }
    }

    const errors = [];
    const committed = collectCommittedState(abs, { fsImpl: fileSystem, repositoryRoot });
    errors.push(...committed.errors);
    if (committed.markers.length === 0) {
        errors.push({
            code: 'PARTIAL_OUTPUT',
            message: 'no valid commit marker present — partial/incomplete run',
        });
    }

    let summaryFiles = [];
    let summaries = [];
    let ledgerVersions = [];
    const ledgerEntriesByKey = new Map();
    const ledgerEntryByArtifact = new Map();
    const quarantineLedger = new Map();

    // The deep checks run UNCONDITIONALLY: a state-level failure (residue,
    // broken marker chain) must not hide the remaining A–E checks — the
    // validator reports every problem it can, not just the first one.
    // ── A. summaries (one per committed marker) ──
    summaryFiles = committed.markers.map(marker => {
        const summaryName = summaryFileNameForSeq(marker.seq);
        return marker.doc.files.find(f => f.name === summaryName) ? summaryName : null;
    });
    for (const marker of committed.markers) {
        const summaryName = summaryFileNameForSeq(marker.seq);
        const bound = marker.doc.files.find(f => f.name === summaryName);
        if (!bound) {
            errors.push({
                code: 'SUMMARY_INVALID',
                message: `commit marker ${marker.seq} does not bind a summary`,
            });
            continue;
        }
        try {
            summaries.push(readJsonFile(path.join(abs, summaryName), { fsImpl: fileSystem }).parsed);
        } catch (error) {
            errors.push({
                code: 'SUMMARY_INVALID',
                message: `summary unreadable: ${summaryName} (${error.message})`,
            });
        }
    }
    for (const summary of summaries) {
        validateSummaryDoc(summary, errors);
    }

    // ── B. store ledger versions ──
    ledgerVersions = committed.ledgerVersions;
    let previousLedger = null;
    for (const ledger of ledgerVersions) {
        if (!ledger || ledger.schema_version !== STORE_STATE_SCHEMA) {
            errors.push({ code: 'LEDGER_INVALID', message: 'ledger schema_version invalid' });
            continue;
        }
        // R10-P2-2 (Codex round 10): observations must be a non-array plain
        // object — `typeof [] === 'object'` lets an array silently pass the
        // empty Object.entries() path and validate as an empty store.
        if (
            !ledger.observations ||
            typeof ledger.observations !== 'object' ||
            Array.isArray(ledger.observations)
        ) {
            errors.push({ code: 'LEDGER_INVALID', message: 'ledger observations must be a plain object' });
            continue;
        }
        // R5-P3-1 (Codex round 5): quarantines must be a PLAIN OBJECT on every
        // ledger version — an array (`quarantines: []`) would silently pass
        // the empty Object.entries() path. Keys are `id:E###` and each entry
        // must carry the evidence-file reference and terminal-state fields the
        // D-group cross-checks rely on.
        const quarantinesDoc = ledger.quarantines;
        if (
            quarantinesDoc === undefined ||
            quarantinesDoc === null ||
            typeof quarantinesDoc !== 'object' ||
            Array.isArray(quarantinesDoc)
        ) {
            errors.push({ code: 'LEDGER_INVALID', message: 'ledger quarantines must be a plain object' });
        } else {
            for (const [key, entry] of Object.entries(quarantinesDoc)) {
                if (!/^\d+:E\d{3}$/.test(String(key))) {
                    errors.push({ code: 'LEDGER_INVALID', message: `ledger quarantine key has invalid format: ${key}` });
                    continue;
                }
                if (!entry || typeof entry !== 'object' || Array.isArray(entry)) {
                    errors.push({ code: 'LEDGER_INVALID', message: `ledger quarantine entry ${key} is not an object` });
                    continue;
                }
                if (!isQuarantineFileName(String(entry.quarantine_file || ''))) {
                    errors.push({
                        code: 'LEDGER_INVALID',
                        message: `ledger quarantine entry ${key} references illegal file: ${entry.quarantine_file}`,
                    });
                }
                if (typeof entry.terminal_state !== 'string' || entry.terminal_state === '') {
                    errors.push({
                        code: 'LEDGER_INVALID',
                        message: `ledger quarantine entry ${key} has no terminal_state`,
                    });
                }
                if (!/^E\d{3}$/.test(String(entry.error_code || ''))) {
                    errors.push({
                        code: 'LEDGER_INVALID',
                        message: `ledger quarantine entry ${key} has no valid error_code`,
                    });
                }
                // R6-P2-2 (Codex round 6): SEMANTIC binding — the key must
                // derive from the entry, and the file name must derive from
                // the key. Format-legal but self-contradictory records
                // (key `123:E001` with entry source_match_id `456`,
                // error_code `E002`, quarantine_file for `789:E003`) are
                // tamper and must fail closed.
                const keyParts = String(key).split(':');
                const keyId = keyParts[0];
                const keyCode = keyParts[1];
                if (String(entry.source_match_id ?? '') !== keyId) {
                    errors.push({
                        code: 'LEDGER_INVALID',
                        message: `ledger quarantine key ${key} source_match_id disagrees with its entry`,
                    });
                }
                if (String(entry.error_code ?? '') !== keyCode) {
                    errors.push({
                        code: 'LEDGER_INVALID',
                        message: `ledger quarantine key ${key} error_code disagrees with its entry`,
                    });
                }
                const derivedQuarantineFile = quarantineFileName(keyId, keyCode);
                if (String(entry.quarantine_file ?? '') !== derivedQuarantineFile) {
                    errors.push({
                        code: 'LEDGER_INVALID',
                        message: `ledger quarantine entry ${key} quarantine_file must be ${derivedQuarantineFile}`,
                    });
                }
                if (
                    entry.terminal_state !== TERMINAL_STATES.QUARANTINED_VALIDATION_FAIL &&
                    entry.terminal_state !== TERMINAL_STATES.QUARANTINED_PROVENANCE_MISMATCH
                ) {
                    errors.push({
                        code: 'LEDGER_INVALID',
                        message: `ledger quarantine entry ${key} terminal_state must be a quarantine state`,
                    });
                }
                if (!Object.values(ERROR_CODES).includes(String(entry.error_code ?? ''))) {
                    errors.push({
                        code: 'LEDGER_INVALID',
                        message: `ledger quarantine entry ${key} error_code must be a registry error code`,
                    });
                }
                // R10-P2-1 (Codex round 10): recorded_at is committed into
                // both the ledger entry and the evidence file — a direct
                // caller could inject arbitrary bytes through it. Non-empty
                // recorded_at must be a strict ISO-8601 absolute timestamp
                // (the commit path already enforces this on builtAt).
                const ledgerRecordedAt = String(entry.recorded_at ?? '');
                if (ledgerRecordedAt !== '' && !isStrictAbsoluteTimestamp(ledgerRecordedAt)) {
                    errors.push({
                        code: 'LEDGER_INVALID',
                        message: `ledger quarantine entry ${key} recorded_at must be a strict ISO-8601 timestamp`,
                    });
                }
            }
        }
        for (const [key, entry] of Object.entries(ledger.observations)) {
            // R10-P2-2 (Codex round 10): a null / non-object / array entry
            // is reported as LEDGER_INVALID, never a validator crash — a
            // marker-consistent but semantically illegal ledger must fail
            // closed with a structured error, not throw a TypeError.
            if (!entry || typeof entry !== 'object' || Array.isArray(entry)) {
                errors.push({
                    code: 'LEDGER_INVALID',
                    message: `ledger observation entry ${key} is not an object`,
                });
                continue;
            }
            // 12./13. key format and derivation.
            const expectedKey = observationKey(
                String(entry.source_match_id ?? ''),
                String(entry.stable_payload_sha256 ?? '')
            );
            const keyParts = String(key).split(':');
            if (keyParts.length !== 2 || !/^\d+$/.test(keyParts[0]) || !/^[0-9a-f]{64}$/.test(keyParts[1])) {
                errors.push({ code: 'LEDGER_INVALID', message: `ledger key has invalid format: ${key}` });
                continue;
            }
            if (key !== expectedKey) {
                errors.push({
                    code: 'LEDGER_INVALID',
                    message: `ledger key ${key} does not match its entry (${expectedKey})`,
                });
            }
            // 14./15./16./17. artifact binding.
            const artifactFile = String(entry.artifact_file || '');
            if (!isArtifactFileName(artifactFile)) {
                errors.push({
                    code: 'LEDGER_INVALID',
                    message: `ledger entry references illegal artifact file: ${artifactFile}`,
                });
                continue;
            }
            if (!Object.prototype.hasOwnProperty.call(committed.markerBoundFiles, artifactFile)) {
                errors.push({
                    code: 'LEDGER_INVALID',
                    message: `ledger entry references uncommitted artifact: ${artifactFile}`,
                });
                continue;
            }
            let artifact = null;
            try {
                artifact = readJsonFile(path.join(abs, artifactFile), { fsImpl: fileSystem }).parsed;
            } catch (error) {
                errors.push({
                    code: 'LEDGER_INVALID',
                    message: `ledger artifact unreadable: ${artifactFile} (${error.message})`,
                });
            }
            if (artifact) {
                if (
                    String(artifact.source_match_id ?? '') !== String(entry.source_match_id ?? '') ||
                    String(artifact.stable_payload_sha256 ?? '') !== String(entry.stable_payload_sha256 ?? '')
                ) {
                    errors.push({
                        code: 'LEDGER_INVALID',
                        message: `ledger entry ${key} source id / stable hash disagree with its artifact`,
                    });
                }
                if (String(artifact.business_hash ?? '') !== String(entry.business_hash ?? '')) {
                    errors.push({
                        code: 'LEDGER_INVALID',
                        message: `ledger entry ${key} business hash disagrees with its artifact`,
                    });
                }
                if (
                    canonicalJsonHash(artifact.expected_identity || {}) !==
                    canonicalJsonHash(entry.expected_identity || {})
                ) {
                    errors.push({
                        code: 'LEDGER_INVALID',
                        message: `ledger entry ${key} expected identity disagrees with its artifact`,
                    });
                }
                if (artifact.import_terminal_state !== entry.terminal_state) {
                    errors.push({
                        code: 'LEDGER_INVALID',
                        message: `ledger entry ${key} terminal state disagrees with its artifact`,
                    });
                }
            }
            if (ledgerEntryByArtifact.has(artifactFile) && ledgerEntryByArtifact.get(artifactFile) !== key) {
                errors.push({
                    code: 'LEDGER_INVALID',
                    message: `artifact ${artifactFile} referenced by multiple ledger keys`,
                });
            }
            ledgerEntryByArtifact.set(artifactFile, key);
            ledgerEntriesByKey.set(key, entry);
        }
        // 18./19. monotonicity: no record deleted, no same-key content change.
        if (previousLedger) {
            for (const [key, prevEntry] of Object.entries(previousLedger.observations || {})) {
                const currentEntry = (ledger.observations || {})[key];
                if (currentEntry === undefined) {
                    errors.push({
                        code: 'LEDGER_INVALID',
                        message: `ledger deleted a previously committed observation: ${key}`,
                    });
                } else if (JSON.stringify(currentEntry) !== JSON.stringify(prevEntry)) {
                    errors.push({
                        code: 'LEDGER_INVALID',
                        message: `ledger changed previously committed observation content: ${key}`,
                    });
                }
            }
            for (const [key, prevEntry] of Object.entries(previousLedger.quarantines || {})) {
                const currentEntry = (ledger.quarantines || {})[key];
                if (currentEntry === undefined) {
                    errors.push({
                        code: 'LEDGER_INVALID',
                        message: `ledger deleted a previously committed quarantine: ${key}`,
                    });
                } else if (JSON.stringify(currentEntry) !== JSON.stringify(prevEntry)) {
                    errors.push({
                        code: 'LEDGER_INVALID',
                        message: `ledger changed previously committed quarantine content: ${key}`,
                    });
                }
            }
        }
        previousLedger = ledger;
    }
    const latestLedger = ledgerVersions.length > 0 ? ledgerVersions[ledgerVersions.length - 1] : null;

    // ── D. quarantine ledger (bidirectional) ──
    for (const [key, entry] of Object.entries(
        latestLedger && latestLedger.quarantines ? latestLedger.quarantines : {}
    )) {
        // R6-P2-2 hardening: a null/non-object entry is already reported as
        // LEDGER_INVALID by the B-group — the D-group must fail closed
        // gracefully instead of crashing on `entry.quarantine_file`, and
        // must not publish the malformed entry into the ledger map the
        // summary cross-check reads.
        if (!entry || typeof entry !== 'object' || Array.isArray(entry)) {
            continue;
        }
        quarantineLedger.set(key, entry);
        const quarantineFile = String(entry.quarantine_file || '');
        if (!isQuarantineFileName(quarantineFile)) {
            errors.push({
                code: 'QUARANTINE_INVALID',
                message: `quarantine ledger entry references illegal file: ${quarantineFile}`,
            });
            continue;
        }
        if (!Object.prototype.hasOwnProperty.call(committed.markerBoundFiles, quarantineFile)) {
            errors.push({
                code: 'QUARANTINE_INVALID',
                message: `quarantine ledger references uncommitted file: ${quarantineFile}`,
            });
            continue;
        }
        let quarantine = null;
        try {
            quarantine = readJsonFile(path.join(abs, quarantineFile), { fsImpl: fileSystem }).parsed;
        } catch (error) {
            errors.push({
                code: 'QUARANTINE_INVALID',
                message: `quarantine file unreadable: ${quarantineFile} (${error.message})`,
            });
        }
        // R6-P2-2 (Codex round 6): the physical file name must be exactly the
        // name derived from the ledger entry's id + error code — a renamed or
        // mismatched quarantine file is tamper even when every field reads
        // format-legal.
        const derivedQuarantineName = quarantineFileName(
            String(entry.source_match_id ?? ''),
            String(entry.error_code ?? '')
        );
        if (quarantineFile !== derivedQuarantineName) {
            errors.push({
                code: 'QUARANTINE_INVALID',
                message: `quarantine ${quarantineFile} filename must derive from ledger entry (${derivedQuarantineName})`,
            });
        }
        if (quarantine) {
            if (String(quarantine.quarantine_status ?? '') !== 'quarantined') {
                errors.push({
                    code: 'QUARANTINE_INVALID',
                    message: `quarantine ${quarantineFile} quarantine_status must be 'quarantined'`,
                });
            }
            if (String(quarantine.terminal_state ?? '') !== String(entry.terminal_state ?? '')) {
                errors.push({
                    code: 'QUARANTINE_INVALID',
                    message: `quarantine ${quarantineFile} terminal state disagrees with ledger`,
                });
            }
            if (String(quarantine.error_code ?? '') !== String(entry.error_code ?? '')) {
                errors.push({
                    code: 'QUARANTINE_INVALID',
                    message: `quarantine ${quarantineFile} error code disagrees with ledger`,
                });
            }
            if (String(quarantine.source_match_id ?? '') !== String(entry.source_match_id ?? '')) {
                errors.push({
                    code: 'QUARANTINE_INVALID',
                    message: `quarantine ${quarantineFile} source match id disagrees with ledger`,
                });
            }
            // R10-P2-1 (Codex round 10): the evidence file's recorded_at must
            // be a strict ISO-8601 absolute timestamp and agree with the
            // ledger entry — the commit path derives both from builtAt, so a
            // disagreement means tamper.
            const fileRecordedAt = String(quarantine.recorded_at ?? '');
            if (fileRecordedAt !== '' && !isStrictAbsoluteTimestamp(fileRecordedAt)) {
                errors.push({
                    code: 'QUARANTINE_INVALID',
                    message: `quarantine ${quarantineFile} recorded_at must be a strict ISO-8601 timestamp`,
                });
            }
            if (fileRecordedAt !== String(entry.recorded_at ?? '')) {
                errors.push({
                    code: 'QUARANTINE_INVALID',
                    message: `quarantine ${quarantineFile} recorded_at disagrees with ledger`,
                });
            }
            // R11-P3-1 (Codex round 11): the reason is a DETERMINISTIC
            // function of the validated error code — a free-text
            // quarantine_reason is tamper even when every other field is
            // legal, so the D-group enforces the fixed mapping on the
            // evidence file AND its agreement with the ledger entry.
            const expectedReason = QUARANTINE_REASON_BY_CODE[String(quarantine.error_code ?? '')];
            if (expectedReason !== undefined && String(quarantine.quarantine_reason ?? '') !== expectedReason) {
                errors.push({
                    code: 'QUARANTINE_INVALID',
                    message: `quarantine ${quarantineFile} quarantine_reason does not derive from error code ${quarantine.error_code}`,
                });
            }
            if (String(quarantine.quarantine_reason ?? '') !== String(entry.quarantine_reason ?? '')) {
                errors.push({
                    code: 'QUARANTINE_INVALID',
                    message: `quarantine ${quarantineFile} quarantine_reason disagrees with ledger`,
                });
            }
            // 30. quarantine evidence never contains the full payload.
            const serialized = JSON.stringify(quarantine);
            if (serialized.includes('"normalized"') || serialized.includes('"sections"')) {
                errors.push({
                    code: 'QUARANTINE_INVALID',
                    message: `quarantine file contains payload content: ${quarantineFile}`,
                });
            }
            // 31. error code / terminal state coherence — the SAME map the
            // commit pre-loop enforces (R7-P2-2), so a quarantine record whose
            // code does not define its state can never be committed OR
            // accepted by the validator.
            const state = String(quarantine.terminal_state ?? '');
            const code = String(quarantine.error_code ?? '');
            const allowedCodes = QUARANTINE_STATE_ERROR_CODES[state] || [];
            if (state === TERMINAL_STATES.QUARANTINED_VALIDATION_FAIL || state === TERMINAL_STATES.QUARANTINED_PROVENANCE_MISMATCH) {
                if (!allowedCodes.includes(code)) {
                    errors.push({
                        code: 'QUARANTINE_INVALID',
                        message: `quarantine ${quarantineFile}: ${state} must carry ${allowedCodes.join('/')}`,
                    });
                }
            } else {
                errors.push({
                    code: 'QUARANTINE_INVALID',
                    message: `quarantine ${quarantineFile}: unknown quarantine terminal state ${state}`,
                });
            }
        }
    }
    // orphan quarantine files.
    let quarantineFiles = [];
    try {
        quarantineFiles = fileSystem.readdirSync(abs).filter(isQuarantineFileName);
    } catch {
        /* reported above */
    }
    for (const quarantineFile of quarantineFiles) {
        const referenced = [...quarantineLedger.values()].some(
            entry => String(entry.quarantine_file || '') === quarantineFile
        );
        if (!referenced) {
            errors.push({
                code: 'ORPHAN_QUARANTINE',
                message: `orphan quarantine file not in the ledger: ${quarantineFile}`,
            });
        }
    }

    // ── C. artifacts: every ledger-referenced artifact validated; orphans
    //      detected; exact-repeat keys must exist in the ledger ──
    for (const [key, entry] of ledgerEntriesByKey) {
        const artifactFile = String(entry.artifact_file || '');
        try {
            const { parsed: artifact } = readJsonFile(path.join(abs, artifactFile), {
                fsImpl: fileSystem,
            });
            const validation = validateStagingArtifact(artifact);
            if (!validation.ok) {
                errors.push({
                    code: 'ARTIFACT_INVALID',
                    message: `artifact invalid: ${artifactFile} (${validation.errors.join('; ')})`,
                });
            }
        } catch (error) {
            errors.push({
                code: 'ARTIFACT_INVALID',
                message: `artifact unreadable: ${artifactFile} (${error.message})`,
            });
        }
    }
    let artifactFiles = [];
    try {
        artifactFiles = fileSystem.readdirSync(abs).filter(isArtifactFileName);
    } catch {
        /* reported above */
    }
    for (const artifactFile of artifactFiles) {
        if (!ledgerEntryByArtifact.has(artifactFile)) {
            errors.push({
                code: 'ORPHAN_ARTIFACT',
                message: `orphan artifact not referenced by the ledger: ${artifactFile}`,
            });
        }
    }

    // ── summary ↔ artifact / ledger consistency (25./26./27./28.) ──
    for (const summary of summaries) {
        // R13-P2-4 (Codex round 13): a summary whose business_projection is
        // missing or whose observations is not an array was already reported
        // as SUMMARY_INVALID by validateSummaryDoc — never let the field
        // reads below crash on it (for...of over null/undefined throws).
        const summaryObservations =
            summary && summary.business_projection && Array.isArray(summary.business_projection.observations)
                ? summary.business_projection.observations
                : [];
        for (const observation of summaryObservations) {
            // R13-P2-4: a malformed row is already reported as SUMMARY_INVALID
            // above — skip it here instead of throwing at the field reads.
            if (!observation || typeof observation !== 'object' || Array.isArray(observation)) {
                continue;
            }
            const state = String(observation.terminal_state || '');
            const artifactFile = observation.artifact_file;
            if (
                state === TERMINAL_STATES.QUARANTINED_VALIDATION_FAIL ||
                state === TERMINAL_STATES.QUARANTINED_PROVENANCE_MISMATCH
            ) {
                // R6-P2-2 (Codex round 6): a summary quarantine row must bind
                // to the ledger by the derived `source_match_id:error_code`
                // key, carry the SAME quarantine file the ledger records, and
                // that file must be marker-committed.
                const quarantineKey = `${observation.source_match_id}:${observation.error_code}`;
                const quarantineEntry = quarantineLedger.get(quarantineKey);
                if (!quarantineEntry) {
                    errors.push({
                        code: 'STATE_MISMATCH',
                        message: `summary quarantine observation ${observation.source_match_id} has no ledger quarantine entry (${quarantineKey})`,
                    });
                } else if (
                    String(quarantineEntry.quarantine_file ?? '') !==
                    String(observation.quarantine_file ?? '')
                ) {
                    errors.push({
                        code: 'STATE_MISMATCH',
                        message: `summary quarantine observation ${observation.source_match_id} quarantine_file disagrees with the ledger`,
                    });
                } else if (
                    !Object.prototype.hasOwnProperty.call(
                        committed.markerBoundFiles,
                        String(observation.quarantine_file ?? '')
                    )
                ) {
                    errors.push({
                        code: 'STATE_MISMATCH',
                        message: `summary quarantine observation ${observation.source_match_id} references an uncommitted quarantine file`,
                    });
                }
            }
            if (
                (state === TERMINAL_STATES.ACCEPTED_NEW || state === TERMINAL_STATES.ACCEPTED_REPEAT_EQUIVALENT) &&
                (artifactFile === undefined || artifactFile === null || artifactFile === '')
            ) {
                errors.push({
                    code: 'STATE_MISMATCH',
                    message: `summary observation ${observation.source_match_id} in state ${state} claims no artifact file`,
                });
            }
            if (state === TERMINAL_STATES.ACCEPTED_REPEAT_EXACT) {
                if (artifactFile !== undefined && artifactFile !== null && artifactFile !== '') {
                    errors.push({
                        code: 'STATE_MISMATCH',
                        message: `summary observation ${observation.source_match_id} ACCEPTED_REPEAT_EXACT claims a new artifact file`,
                    });
                }
                const key = observationKey(
                    String(observation.source_match_id ?? ''),
                    String(observation.stable_payload_sha256 ?? '')
                );
                if (!ledgerEntriesByKey.has(key)) {
                    errors.push({
                        code: 'STATE_MISMATCH',
                        message: `summary observation ${observation.source_match_id} ACCEPTED_REPEAT_EXACT has no staged snapshot in the ledger`,
                    });
                }
            }
            if (artifactFile && artifactFile !== '') {
                let artifact = null;
                try {
                    artifact = readJsonFile(path.join(abs, artifactFile), { fsImpl: fileSystem }).parsed;
                } catch {
                    /* already reported */
                }
                if (artifact) {
                    // P0-2: full three-way cross-comparison — summary ↔
                    // artifact ↔ ledger. The summary must reference the SAME
                    // final artifact (source id, stable hash, business hash,
                    // terminal state) that the ledger records, and the ledger
                    // entry must reference the same artifact file.
                    if (artifact.import_terminal_state !== state) {
                        errors.push({
                            code: 'STATE_MISMATCH',
                            message: `summary observation ${observation.source_match_id} terminal state disagrees with its artifact`,
                        });
                    }
                    if (String(artifact.source_match_id ?? '') !== String(observation.source_match_id ?? '')) {
                        errors.push({
                            code: 'STATE_MISMATCH',
                            message: `summary observation ${observation.source_match_id} source_match_id disagrees with its artifact`,
                        });
                    }
                    if (
                        String(artifact.stable_payload_sha256 ?? '') !==
                        String(observation.stable_payload_sha256 ?? '')
                    ) {
                        errors.push({
                            code: 'STATE_MISMATCH',
                            message: `summary observation ${observation.source_match_id} stable_payload_sha256 disagrees with its artifact`,
                        });
                    }
                    if (String(artifact.business_hash ?? '') !== String(observation.business_hash ?? '')) {
                        errors.push({
                            code: 'STATE_MISMATCH',
                            message: `summary observation ${observation.source_match_id} business_hash disagrees with its artifact`,
                        });
                    }
                }
                // Ledger side: the artifact file must be referenced by exactly
                // one ledger entry whose recorded fields agree with the
                // summary observation.
                let ledgerEntry = null;
                for (const [, entry] of ledgerEntriesByKey) {
                    if (String(entry.artifact_file || '') === artifactFile) {
                        ledgerEntry = entry;
                        break;
                    }
                }
                if (!ledgerEntry) {
                    errors.push({
                        code: 'STATE_MISMATCH',
                        message: `summary observation ${observation.source_match_id} artifact ${artifactFile} has no ledger entry`,
                    });
                } else {
                    if (String(ledgerEntry.business_hash ?? '') !== String(observation.business_hash ?? '')) {
                        errors.push({
                            code: 'STATE_MISMATCH',
                            message: `summary observation ${observation.source_match_id} business_hash disagrees with the ledger`,
                        });
                    }
                    if (String(ledgerEntry.source_match_id ?? '') !== String(observation.source_match_id ?? '')) {
                        errors.push({
                            code: 'STATE_MISMATCH',
                            message: `summary observation ${observation.source_match_id} source_match_id disagrees with the ledger`,
                        });
                    }
                    if (
                        String(ledgerEntry.stable_payload_sha256 ?? '') !==
                        String(observation.stable_payload_sha256 ?? '')
                    ) {
                        errors.push({
                            code: 'STATE_MISMATCH',
                            message: `summary observation ${observation.source_match_id} stable_payload_sha256 disagrees with the ledger`,
                        });
                    }
                    if (String(ledgerEntry.terminal_state ?? '') !== state) {
                        errors.push({
                            code: 'STATE_MISMATCH',
                            message: `summary observation ${observation.source_match_id} terminal state disagrees with the ledger`,
                        });
                    }
                }
            }
        }
    }

    const latestMarker = committed.markers.length > 0 ? committed.markers[committed.markers.length - 1] : null;
    return {
        ok: errors.length === 0,
        errors,
        summary_present: summaries.length > 0,
        store_state_present: ledgerVersions.length > 0,
        marker_count: committed.markers.length,
        ledger_version_count: ledgerVersions.length,
        summary_count: summaries.length,
        artifact_check_count: ledgerEntriesByKey.size,
        quarantine_check_count: quarantineLedger.size,
        residue_files: committed.residue,
        // P1-5: the EXACT file SHA-256 of the latest valid commit marker —
        // the value an externally anchored validator compares its
        // --expected-latest-marker-sha256 against. Computed here from the
        // store's committed state (and independently re-hashed by the CLI
        // via readFileSafeNoFollow before comparison — never trusted from
        // the store alone).
        latest_marker_sha256: latestMarker ? latestMarker.fileSha : null,
    };
}

module.exports = {
    STORE_STATE_SCHEMA,
    COMMIT_MARKER_SCHEMA,
    assertNoSymlinkAncestors,
    ensureRealDirectoryTree,
    verifyRepositoryExternalPath,
    writeJsonAtomically,
    readJsonFile,
    readFileSafeNoFollow,
    withStoreLock,
    observationKey,
    artifactFileName,
    quarantineFileName,
    summaryFileNameForSeq,
    ledgerFileNameForSeq,
    markerFileNameForSeq,
    isArtifactFileName,
    isQuarantineFileName,
    isSummaryFileName,
    isLedgerFileName,
    isMarkerFileName,
    emptyStoreState,
    collectCommittedState,
    loadCommittedState,
    classifyAgainstStore,
    commitObservations,
    buildSummary,
    compareSummaryObservations,
    validateOutputRoot,
};
