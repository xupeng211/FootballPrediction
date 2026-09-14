'use strict';

// Filesystem-backed transport, for offline proof only.
//
// This transport exists so the snapshot and restore machinery can be built and
// proven with no network and no credentials.  It is NOT a production backup
// target: the whole point of Blocker #3 is that no local path shares a failure
// domain with the source.  It is used to stage a generation and to hand a
// restored root back to the canonical readers.
//
// It has no default root, no environment fallback and no production path.  A
// root must be supplied explicitly by the caller.

const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');

const { ObjectAlreadyExistsError, SnapshotIntegrityError } = require('./transport');

const KEY_PATTERN = /^[A-Za-z0-9](?:[A-Za-z0-9._-]*[A-Za-z0-9_-])?(?:\/[A-Za-z0-9](?:[A-Za-z0-9._-]*[A-Za-z0-9_-])?)*$/;

// Path fragments that mark the governed production area.  A local transport
// must never be aimed at it: staging writes onto the source would corrupt the
// very authority the snapshot is meant to protect.
const PRODUCTION_MARKERS = Object.freeze([
    path.join('data', 'market_evidence', 'live'),
]);

function canonicalizeKey(key) {
    if (typeof key !== 'string' || key.length === 0) throw new SnapshotIntegrityError('object key is required');
    // The null byte is written as an escape sequence, never as a raw byte.
    // A raw NUL makes Git classify this whole file as binary, which hides it
    // from text diff, from the incremental static scanners and from patch
    // review -- the exact auditability a security-sensitive check must keep.
    if (key.includes('\0')) throw new SnapshotIntegrityError('object key must not contain a null byte');
    if (key.includes('\\')) throw new SnapshotIntegrityError(`object key must use forward slashes: ${key}`);
    if (key.startsWith('/')) throw new SnapshotIntegrityError(`object key must be relative: ${key}`);
    if (key.endsWith('/')) throw new SnapshotIntegrityError(`object key must not end with a slash: ${key}`);
    if (key.includes('//')) throw new SnapshotIntegrityError(`object key must not contain an empty segment: ${key}`);
    if (key.length > 900) throw new SnapshotIntegrityError('object key is too long');
    for (const segment of key.split('/')) {
        if (segment === '.' || segment === '..') throw new SnapshotIntegrityError(`object key must not contain traversal segments: ${key}`);
    }
    if (!KEY_PATTERN.test(key)) throw new SnapshotIntegrityError(`object key contains unsupported characters: ${key}`);
    return key;
}

// The match is on whole path segments, not on a substring.  A substring test
// would also condemn `.../live-2`, and a denylist that refuses directories it
// does not mean is a denylist nobody can reason about.  Every form that denotes
// the governed area itself, or anything below it, is refused.
function isGovernedProductionPath(target) {
    if (typeof target !== 'string' || !target.trim()) return false;
    const resolved = path.resolve(target);
    return PRODUCTION_MARKERS.some(marker => {
        const rooted = path.resolve('/', marker);
        return resolved === rooted
            || resolved.startsWith(`${rooted}${path.sep}`)
            || resolved.endsWith(`${path.sep}${marker}`)
            || resolved.includes(`${path.sep}${marker}${path.sep}`);
    });
}

// `path.resolve` is lexical: it never asks the filesystem, so a path reached
// through a symlinked ancestor resolves to something that names none of the
// governed area while every read and write through it lands inside it.  A root
// such as `<scratch>/link/nested`, where `link` points at the governed area, is
// refused by neither the literal check above -- its text contains no
// `data/market_evidence/live` -- nor by the callers' own `lstat` of the final
// component, which sees an ordinary directory because the link is higher up.
// The real location therefore has to be checked as well, and it is the only
// thing that can answer the question the check is actually asking.
//
// Only the longest *existing* prefix can be resolved: a path that does not
// exist yet has no real location, and a non-existent tail names nothing on
// disk.  Resolving the prefix and appending the tail unchanged gives the path
// the target will have once those directories are created, so a destination
// that is safe to create is still accepted and one that would land in the
// governed area is refused before anything is created.
//
// A path that cannot be resolved for any reason other than a missing prefix --
// a component that is not a directory, or a permission refusal -- yields null
// and only the lexical arm applies.  That is not a way in: the callers' own
// existence and type checks refuse those paths, and so does the operating
// system, so the unresolvable set is disjoint from the set that can be read.
function realLocationOf(target) {
    let prefix = path.resolve(target);
    const tail = [];
    for (;;) {
        try {
            const real = fs.realpathSync(prefix);
            return tail.length === 0 ? real : path.join(real, ...tail);
        } catch (error) {
            if (error.code !== 'ENOENT') return null;
            const parent = path.dirname(prefix);
            if (parent === prefix) return null;
            tail.unshift(path.basename(prefix));
            prefix = parent;
        }
    }
}

function assertNotGovernedProductionPath(target, label, ErrorType = SnapshotIntegrityError) {
    if (isGovernedProductionPath(target)) {
        throw new ErrorType(`${label} must never be the governed production area: ${path.resolve(target)}`);
    }
    const real = realLocationOf(target);
    if (real !== null && isGovernedProductionPath(real)) {
        throw new ErrorType(`${label} must never resolve into the governed production area: ${real}`);
    }
    return path.resolve(target);
}

function assertUsableRoot(root) {
    if (typeof root !== 'string' || !root.trim()) throw new SnapshotIntegrityError('an explicit root is required; local transport has no default root');
    return assertNotGovernedProductionPath(root, 'local transport root');
}

function assertNoSymlinkAncestors(root, absolutePath) {
    const relative = path.relative(root, absolutePath);
    if (relative === '' || relative.startsWith('..') || path.isAbsolute(relative)) throw new SnapshotIntegrityError(`resolved path escapes the transport root: ${absolutePath}`);
    let current = root;
    for (const segment of relative.split(path.sep)) {
        current = path.join(current, segment);
        let stat;
        try {
            stat = fs.lstatSync(current);
        } catch (error) {
            if (error.code === 'ENOENT') continue;
            throw error;
        }
        if (stat.isSymbolicLink()) throw new SnapshotIntegrityError(`symbolic links are not permitted in the transport root: ${current}`);
    }
}

function resolveKey(root, key) {
    const canonical = canonicalizeKey(key);
    const absolute = path.resolve(root, canonical);
    const relative = path.relative(root, absolute);
    if (relative === '' || relative.startsWith('..') || path.isAbsolute(relative)) throw new SnapshotIntegrityError(`object key escapes the transport root: ${key}`);
    assertNoSymlinkAncestors(root, absolute);
    return { canonical, absolute };
}

// A pathname is re-resolved by the kernel at open time, so a component that was
// validated a moment ago and used a moment later can be a different object by
// then.  Checking the parent chain and afterwards opening the full pathname
// therefore leaves a window, and O_EXCL does not close it: the exclusive flag
// speaks about the final component only, while every intermediate component is
// resolved again -- through whatever symlink now sits there.  The create path
// below stops naming the directory part at all.  Each level is opened with
// O_NOFOLLOW|O_DIRECTORY, and every lookup after that is made *relative to the
// descriptor* of the level above it, because a descriptor pins an inode and no
// later change to any pathname can steer it.
//
// Node's public fs API has no openat(2) binding, so an already-open descriptor
// is named through /proc/self/fd.  That entry resolves to the inode the
// descriptor holds rather than to a path, so appending a name to it looks that
// name up in exactly that directory.  Without that mount the traversal cannot
// be expressed at all, and quietly falling back to opening by pathname would
// restore precisely the race this replaced, so the transport refuses to be
// constructed rather than degrading.
const DIRECTORY_DESCRIPTOR_ROOT = '/proc/self/fd';
const DIRECTORY_OPEN_FLAGS = fs.constants.O_RDONLY | fs.constants.O_DIRECTORY | fs.constants.O_NOFOLLOW;
const CREATE_ONLY_OPEN_FLAGS = fs.constants.O_WRONLY | fs.constants.O_CREAT | fs.constants.O_EXCL | fs.constants.O_NOFOLLOW;

function descriptorRelativePath(descriptor, name) {
    return `${DIRECTORY_DESCRIPTOR_ROOT}/${descriptor}/${name}`;
}

function assertDirectoryDescriptorTraversalAvailable() {
    let probe;
    try {
        probe = fs.openSync(DIRECTORY_DESCRIPTOR_ROOT, fs.constants.O_RDONLY | fs.constants.O_DIRECTORY);
    } catch (error) {
        throw new SnapshotIntegrityError(`local transport requires directory-descriptor traversal, which needs a readable ${DIRECTORY_DESCRIPTOR_ROOT}: ${error.message}`);
    }
    fs.closeSync(probe);
}

// One level down, relative to an already-open descriptor.  A name that is a
// symlink, a plain file or anything else that is not a directory is refused by
// the flags themselves, so there is no window between deciding and acting, and
// only a genuinely absent name is created.  `label` is the pathname the caller
// asked for: it is used for the message, never for the lookup.
function descendDirectory(descriptor, name, label) {
    const target = descriptorRelativePath(descriptor, name);
    try {
        return fs.openSync(target, DIRECTORY_OPEN_FLAGS);
    } catch (error) {
        if (error.code === 'ENOENT') {
            fs.mkdirSync(target, { mode: 0o755 });
            return fs.openSync(target, DIRECTORY_OPEN_FLAGS);
        }
        if (error.code === 'ENOTDIR' || error.code === 'ELOOP') throw new SnapshotIntegrityError(`object key parent is not a plain directory: ${label}`);
        throw error;
    }
}

// The parent directory of `absolute`, held open, with the levels that do not
// exist yet created.  The caller owns the returned descriptor.
function openParentDirectoryDescriptor(root, absolute) {
    const relative = path.relative(root, path.dirname(absolute));
    if (relative.startsWith('..') || path.isAbsolute(relative)) throw new SnapshotIntegrityError(`object key escapes the transport root: ${absolute}`);
    let descriptor = fs.openSync(root, DIRECTORY_OPEN_FLAGS);
    if (relative === '' || relative === '.') return descriptor;
    let current = root;
    try {
        for (const segment of relative.split(path.sep)) {
            current = path.join(current, segment);
            const next = descendDirectory(descriptor, segment, current);
            fs.closeSync(descriptor);
            descriptor = next;
        }
        return descriptor;
    } catch (error) {
        fs.closeSync(descriptor);
        throw error;
    }
}

function sha256OfBytes(bytes) {
    return crypto.createHash('sha256').update(bytes).digest('hex');
}

function createLocalTransport({ root } = {}) {
    assertDirectoryDescriptorTraversalAvailable();
    const resolvedRoot = assertUsableRoot(root);
    if (!fs.existsSync(resolvedRoot)) throw new SnapshotIntegrityError(`local transport root does not exist: ${resolvedRoot}`);
    const rootStat = fs.lstatSync(resolvedRoot);
    if (rootStat.isSymbolicLink() || !rootStat.isDirectory()) throw new SnapshotIntegrityError(`local transport root must be a plain directory: ${resolvedRoot}`);

    return {
        // Create-only.  fs.openSync with 'wx' is the atomic primitive: the
        // create and the existence check are the same syscall, so two writers
        // racing on one generation cannot both win.
        //
        // The directory is named by descriptor, not by pathname, so O_EXCL now
        // claims the final name inside the directory the walk actually opened
        // rather than inside whatever the final path resolution would have made
        // of the intermediate components.  That is the guarantee O_EXCL never
        // had on its own, and it is the one this transport's contract states.
        putObjectCreateOnly({ key, bytes } = {}) {
            if (!Buffer.isBuffer(bytes)) throw new SnapshotIntegrityError('putObjectCreateOnly requires a Buffer');
            const { canonical, absolute } = resolveKey(resolvedRoot, key);
            const parent = openParentDirectoryDescriptor(resolvedRoot, absolute);
            let fd;
            try {
                fd = fs.openSync(descriptorRelativePath(parent, path.basename(absolute)), CREATE_ONLY_OPEN_FLAGS, 0o644);
            } catch (error) {
                if (error.code === 'EEXIST') throw new ObjectAlreadyExistsError(canonical);
                // The walk above either found or created every level, so a
                // missing one here means the parent directory was removed
                // between the walk and the create.  Naming it keeps the
                // transport's failures in one family instead of leaking a bare
                // errno that a caller's `SnapshotIntegrityError` handling would
                // not catch.
                if (error.code === 'ENOENT') throw new SnapshotIntegrityError(`object key parent disappeared during the create: ${canonical}`);
                throw error;
            } finally {
                fs.closeSync(parent);
            }
            try {
                fs.writeFileSync(fd, bytes);
                fs.fsyncSync(fd);
            } finally {
                fs.closeSync(fd);
            }
            return Object.freeze({ key: canonical, size: bytes.length, sha256: sha256OfBytes(bytes) });
        },

        getObject({ key } = {}) {
            const { absolute } = resolveKey(resolvedRoot, key);
            let stat;
            try {
                stat = fs.lstatSync(absolute);
            } catch (error) {
                if (error.code === 'ENOENT') return null;
                throw error;
            }
            if (stat.isSymbolicLink() || !stat.isFile()) throw new SnapshotIntegrityError(`object is not a plain file: ${key}`);
            return fs.readFileSync(absolute);
        },

        headObject({ key } = {}) {
            const { canonical, absolute } = resolveKey(resolvedRoot, key);
            let stat;
            try {
                stat = fs.lstatSync(absolute);
            } catch (error) {
                if (error.code === 'ENOENT') return null;
                throw error;
            }
            if (stat.isSymbolicLink() || !stat.isFile()) throw new SnapshotIntegrityError(`object is not a plain file: ${key}`);
            return Object.freeze({ key: canonical, size: stat.size });
        },

        listObjects({ prefix = '' } = {}) {
            const results = [];
            const walk = (directory, relativeDirectory) => {
                const names = fs.readdirSync(directory).sort();
                for (const name of names) {
                    const absolute = path.join(directory, name);
                    const stat = fs.lstatSync(absolute);
                    if (stat.isSymbolicLink()) throw new SnapshotIntegrityError(`symbolic links are not permitted in the transport root: ${absolute}`);
                    const relative = relativeDirectory ? `${relativeDirectory}/${name}` : name;
                    if (stat.isDirectory()) walk(absolute, relative);
                    else if (stat.isFile()) results.push(Object.freeze({ key: relative, size: stat.size }));
                }
            };
            walk(resolvedRoot, '');
            return Object.freeze(results.filter(entry => entry.key.startsWith(prefix)));
        },

        describe() {
            return Object.freeze({ kind: 'local', create_only: true, delete_exposed: false, root: resolvedRoot });
        },
    };
}

module.exports = {
    createLocalTransport,
    canonicalizeKey,
    sha256OfBytes,
    isGovernedProductionPath,
    assertNotGovernedProductionPath,
    realLocationOf,
    PRODUCTION_MARKERS,
    KEY_PATTERN,
};
