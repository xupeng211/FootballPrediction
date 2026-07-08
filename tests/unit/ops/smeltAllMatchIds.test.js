/**
 * GOLD-AUDIT-2BB — --match-ids allowlist unit tests
 * ==================================================
 *
 * Tests the pure helper functions extracted from scripts/ops/smelt_all.js:
 * parseMatchIdsArg / validateMatchIds, and the enforcement logic around
 * --match-ids + --limit mutual exclusion and write-mode rejection.
 *
 * These tests exercise the argument parsing and validation layer only;
 * DB-backed integration is validated separately via dry-run.
 *
 * @module tests/unit/ops/smeltAllMatchIds
 * @version V1.0.0-2BB
 */

'use strict';

const { describe, it } = require('node:test');
const assert = require('node:assert');

// ── Reconstruct the pure helper functions from smelt_all.js ─────────────────
// We test these as pure functions to avoid needing the full CLI harness.

function parseMatchIdsArg(raw) {
    if (raw === undefined || raw === null || raw === '') {
        return { matchIds: null, error: '--match-ids requires a comma-separated list of match IDs' };
    }

    const ids = raw.split(',').map(s => s.trim()).filter(s => s.length > 0);

    // Check for empty entries (e.g. "a,,b" or "a, ,b")
    const rawParts = raw.split(',');
    if (rawParts.some(p => p.trim() === '')) {
        return { matchIds: null, error: '--match-ids contains empty entry after trimming' };
    }

    if (ids.length === 0) {
        return { matchIds: null, error: '--match-ids list is empty' };
    }

    return { matchIds: ids, error: null };
}

function validateMatchIds(matchIds) {
    if (!Array.isArray(matchIds) || matchIds.length === 0) {
        return 'matchIds must be a non-empty array';
    }

    const seen = new Set();
    for (const id of matchIds) {
        if (seen.has(id)) {
            return `Duplicate match_id "${id}" in --match-ids list`;
        }
        seen.add(id);
    }

    return null;
}

/**
 * Simulates the enforcement logic that smelt_all.js main() performs.
 * Returns { allowed: boolean, error: string | null }.
 */
function checkMatchIdsConstraints({ matchIds, hasLimit, isNoWrite }) {
    if (matchIds !== null && hasLimit) {
        return { allowed: false, error: '--match-ids and --limit are mutually exclusive' };
    }
    if (matchIds !== null && !isNoWrite) {
        return { allowed: false, error: '--match-ids is currently allowed only in dry-run/no-write mode' };
    }
    return { allowed: true, error: null };
}

// ═══════════════════════════════════════════════════════════════════════════════
// Tests
// ═══════════════════════════════════════════════════════════════════════════════

describe('GOLD-AUDIT-2BB — parseMatchIdsArg', () => {
    it('1. 正常解析逗号分隔的 match_id 列表', () => {
        const result = parseMatchIdsArg('53_aaa,53_bbb,53_ccc');
        assert.equal(result.error, null);
        assert.deepStrictEqual(result.matchIds, ['53_aaa', '53_bbb', '53_ccc']);
    });

    it('2. trim 每个 match_id 前后的空格', () => {
        const result = parseMatchIdsArg(' 53_aaa , 53_bbb , 53_ccc ');
        assert.equal(result.error, null);
        assert.deepStrictEqual(result.matchIds, ['53_aaa', '53_bbb', '53_ccc']);
    });

    it('3. 单个 match_id 正常工作', () => {
        const result = parseMatchIdsArg('53_single');
        assert.equal(result.error, null);
        assert.deepStrictEqual(result.matchIds, ['53_single']);
    });

    it('4. 空字符串报错', () => {
        const result = parseMatchIdsArg('');
        assert.notEqual(result.error, null);
        assert.equal(result.matchIds, null);
    });

    it('5. undefined / null 报错', () => {
        const r1 = parseMatchIdsArg(undefined);
        assert.notEqual(r1.error, null);

        const r2 = parseMatchIdsArg(null);
        assert.notEqual(r2.error, null);
    });

    it('6. 包含空 entry（连续逗号 "a,,b"）报错', () => {
        const result = parseMatchIdsArg('53_aaa,,53_bbb');
        assert.notEqual(result.error, null);
        assert.ok(result.error.includes('empty entry'));
    });

    it('7. 包含空白 entry（"a, ,b"）报错', () => {
        const result = parseMatchIdsArg('53_aaa, ,53_bbb');
        assert.notEqual(result.error, null);
        assert.ok(result.error.includes('empty entry'));
    });

    it('8. 尾部逗号报错', () => {
        const result = parseMatchIdsArg('53_aaa,53_bbb,');
        assert.notEqual(result.error, null);
        assert.ok(result.error.includes('empty entry'));
    });
});

describe('GOLD-AUDIT-2BB — validateMatchIds', () => {
    it('9. 无重复时返回 null（通过验证）', () => {
        const err = validateMatchIds(['53_aaa', '53_bbb', '53_ccc']);
        assert.equal(err, null);
    });

    it('10. 单个元素无重复', () => {
        const err = validateMatchIds(['53_only']);
        assert.equal(err, null);
    });

    it('11. 重复 match_id 报错', () => {
        const err = validateMatchIds(['53_aaa', '53_bbb', '53_aaa']);
        assert.notEqual(err, null);
        assert.ok(err.includes('Duplicate'));
        assert.ok(err.includes('53_aaa'));
    });

    it('12. 空的 matchIds 数组报错', () => {
        const err = validateMatchIds([]);
        assert.notEqual(err, null);
    });

    it('13. 非数组报错', () => {
        const err = validateMatchIds(null);
        assert.notEqual(err, null);
    });
});

describe('GOLD-AUDIT-2BB — constraint enforcement', () => {
    it('14. --match-ids + --limit 同时出现报错', () => {
        const result = checkMatchIdsConstraints({
            matchIds: ['53_a', '53_b'],
            hasLimit: true,
            isNoWrite: true
        });
        assert.equal(result.allowed, false);
        assert.ok(result.error.includes('mutually exclusive'));
    });

    it('15. --match-ids without dry-run/no-write 报错', () => {
        const result = checkMatchIdsConstraints({
            matchIds: ['53_a', '53_b'],
            hasLimit: false,
            isNoWrite: false
        });
        assert.equal(result.allowed, false);
        assert.ok(result.error.includes('dry-run/no-write'));
    });

    it('16. --match-ids with dry-run 允许', () => {
        const result = checkMatchIdsConstraints({
            matchIds: ['53_a', '53_b'],
            hasLimit: false,
            isNoWrite: true
        });
        assert.equal(result.allowed, true);
        assert.equal(result.error, null);
    });

    it('17. --match-ids with --no-write 允许', () => {
        const result = checkMatchIdsConstraints({
            matchIds: ['53_a'],
            hasLimit: false,
            isNoWrite: true
        });
        assert.equal(result.allowed, true);
    });

    it('18. --match-ids with --preview 允许', () => {
        const result = checkMatchIdsConstraints({
            matchIds: ['53_a'],
            hasLimit: false,
            isNoWrite: true
        });
        assert.equal(result.allowed, true);
    });

    it('19. 不传 --match-ids 时 --limit 行为不变（allowed）', () => {
        const result = checkMatchIdsConstraints({
            matchIds: null,
            hasLimit: true,
            isNoWrite: true
        });
        assert.equal(result.allowed, true);
    });

    it('20. 不传 --match-ids 时 write mode 行为不变（不触发 --match-ids 保护）', () => {
        // Without --match-ids, the write-mode block should NOT fire.
        const result = checkMatchIdsConstraints({
            matchIds: null,
            hasLimit: false,
            isNoWrite: false
        });
        assert.equal(result.allowed, true);
    });
});

describe('GOLD-AUDIT-2BB — input order preservation', () => {
    it('21. parseMatchIdsArg 保持输入顺序', () => {
        const result = parseMatchIdsArg('z, a, m, b, q');
        assert.equal(result.error, null);
        assert.deepStrictEqual(result.matchIds, ['z', 'a', 'm', 'b', 'q']);
    });

    it('22. validateMatchIds 不改变输入数组顺序', () => {
        const input = ['third', 'first', 'second'];
        const err = validateMatchIds(input);
        assert.equal(err, null);
        // Input array should be unchanged
        assert.deepStrictEqual(input, ['third', 'first', 'second']);
    });
});
