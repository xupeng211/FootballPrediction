'use strict';

// lifecycle: permanent

const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const test = require('node:test');
const {
    CanonicalInventoryContractError,
    MASTER_COUNT,
    computeV1IdentityProjectionHash,
    readOrdinaryArtifact,
    validateArtifactDocument,
} = require('../../src/infrastructure/canonical/CanonicalInventoryContract');
const {
    buildDocument,
    parentMetadata,
    syntheticCandidates,
    writeDocument,
} = require('../helpers/canonicalInventoryFixtures');

function tempDir() {
    return fs.mkdtempSync(path.join(os.tmpdir(), 'fp-canonical-contract-'));
}

test('synthetic v2 master preserves its deterministic v1 identity projection and rejects status defects', () => {
    const master = buildDocument(syntheticCandidates());
    assert.equal(master.candidates.length, MASTER_COUNT);
    assert.equal(master.artifact.identity_projection_hash, computeV1IdentityProjectionHash(master.candidates));
    assert.equal(validateArtifactDocument(master, { allowSyntheticTestOnly: true }).candidates.length, MASTER_COUNT);
    const nonSynthetic = structuredClone(master);
    delete nonSynthetic.artifact.synthetic_test_only;
    assert.throws(
        () => validateArtifactDocument(nonSynthetic),
        error => error.code === 'V1_IDENTITY_PROJECTION_MISMATCH'
    );
    const missingStatus = structuredClone(master);
    delete missingStatus.candidates[0].status;
    assert.throws(() => validateArtifactDocument(missingStatus), CanonicalInventoryContractError);
    const unknownStatus = structuredClone(master);
    unknownStatus.candidates[0].status = 'invented';
    assert.throws(() => validateArtifactDocument(unknownStatus), CanonicalInventoryContractError);
    const abandonedStatus = structuredClone(master);
    abandonedStatus.candidates[0].status = 'abandoned';
    assert.throws(() => validateArtifactDocument(abandonedStatus), CanonicalInventoryContractError);
});

test('population, duplicate, scope and identity mismatches fail closed', () => {
    const master = buildDocument(syntheticCandidates());
    for (const mutate of [
        document => {
            document.candidates.pop();
            document.artifact.candidate_count -= 1;
            document.artifact.per_season_counts['2024/2025'] -= 1;
        },
        document => {
            document.candidates[1].id = document.candidates[0].id;
        },
        document => {
            document.candidates[0].season = '2025/2026';
        },
        document => {
            document.candidates[0].competition = 'Other League';
        },
        document => {
            document.artifact.identity_projection_hash = '0'.repeat(64);
        },
    ]) {
        const broken = structuredClone(master);
        mutate(broken);
        assert.throws(
            () => validateArtifactDocument(broken, { allowSyntheticTestOnly: true }),
            CanonicalInventoryContractError
        );
    }
});

test('canary requires exact parent allowlist order and immutable projection', () => {
    const directory = tempDir();
    try {
        const master = buildDocument(syntheticCandidates());
        const binding = writeDocument(directory, 'master.json', master);
        const canary = buildDocument(master.candidates.slice(0, 10), {
            kind: 'canary',
            parentMaster: parentMetadata(master, binding),
        });
        assert.equal(
            validateArtifactDocument(canary, {
                parentDocument: master,
                parentBinding: binding,
                allowSyntheticTestOnly: true,
            }).candidates.length,
            10
        );
        const reordered = structuredClone(canary);
        reordered.candidates.reverse();
        reordered.artifact.allowlist.reverse();
        assert.throws(
            () =>
                validateArtifactDocument(reordered, {
                    parentDocument: master,
                    parentBinding: binding,
                    allowSyntheticTestOnly: true,
                }),
            CanonicalInventoryContractError
        );
        const mutated = structuredClone(canary);
        mutated.candidates[0].home_team = 'Synthetic mutation';
        assert.throws(
            () =>
                validateArtifactDocument(mutated, {
                    parentDocument: master,
                    parentBinding: binding,
                    allowSyntheticTestOnly: true,
                }),
            CanonicalInventoryContractError
        );
    } finally {
        fs.rmSync(directory, { recursive: true, force: true });
    }
});

test('ordinary-file hash and symlink checks reject swapped inputs', { skip: process.platform === 'win32' }, () => {
    const directory = tempDir();
    try {
        const master = buildDocument(syntheticCandidates());
        const binding = writeDocument(directory, 'master.json', master);
        assert.equal(
            readOrdinaryArtifact(binding.path, { sha256: binding.sha256, allowSyntheticTestOnly: true }).sha256,
            binding.sha256
        );
        assert.throws(
            () => readOrdinaryArtifact(binding.path, { sha256: '0'.repeat(64), allowSyntheticTestOnly: true }),
            CanonicalInventoryContractError
        );
        const symlink = path.join(directory, 'link.json');
        fs.symlinkSync(binding.path, symlink);
        assert.throws(
            () => readOrdinaryArtifact(symlink, { sha256: binding.sha256, allowSyntheticTestOnly: true }),
            CanonicalInventoryContractError
        );
        let lstatCalls = 0;
        const mutatedFileSystem = {
            readFileSync: fs.readFileSync.bind(fs),
            realpathSync: fs.realpathSync.bind(fs),
            lstatSync(filePath) {
                lstatCalls += 1;
                const stat = fs.lstatSync(filePath);
                return lstatCalls === 3 ? { ...stat, size: stat.size + 1 } : stat;
            },
        };
        assert.throws(
            () =>
                readOrdinaryArtifact(
                    binding.path,
                    { sha256: binding.sha256, allowSyntheticTestOnly: true },
                    mutatedFileSystem
                ),
            error => error.code === 'ARTIFACT_MUTATED'
        );
    } finally {
        fs.rmSync(directory, { recursive: true, force: true });
    }
});

test(
    'repository-external artifact boundary resolves intermediate symlinks',
    { skip: process.platform === 'win32' },
    () => {
        const directory = tempDir();
        const repositoryRoot = path.resolve(__dirname, '../..');
        const repositoryTemp = fs.mkdtempSync(path.join(repositoryRoot, '.canonical-contract-test-'));
        try {
            const master = buildDocument(syntheticCandidates());
            const binding = writeDocument(repositoryTemp, 'artifact.json', master);
            const repositoryLink = path.join(directory, 'repository-link');
            fs.symlinkSync(repositoryRoot, repositoryLink, 'dir');
            const linkedArtifact = path.join(repositoryLink, path.basename(repositoryTemp), 'artifact.json');
            assert.throws(
                () => readOrdinaryArtifact(linkedArtifact, { sha256: binding.sha256, allowSyntheticTestOnly: true }),
                error => error instanceof CanonicalInventoryContractError && /repository-external/.test(error.message)
            );
        } finally {
            fs.rmSync(repositoryTemp, { recursive: true, force: true });
            fs.rmSync(directory, { recursive: true, force: true });
        }
    }
);
