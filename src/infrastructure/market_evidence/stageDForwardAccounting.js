'use strict';

// lifecycle: permanent
// 只读核验跨历史缺口后的记账起点与指定的一次请求。

const fs = require('node:fs');
const path = require('node:path');
const { createHash } = require('node:crypto');
const stage = require('./stageDOperations');
const { openMarketEvidenceAuthoritySnapshot } = require('./authorityReader');

const SCHEMA = 'footballprediction-stage-d-forward-opening/v1';
const DAY_MS = 86_400_000;
const DIGEST = /^[a-f0-9]{64}$/;
const TOKEN = /^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$/;

function requireFact(holds, detail) {
    if (!holds) throw Object.assign(new Error(detail), { code: 'FORWARD_ACCOUNTING_BLOCKED' });
}

function exact(value, keys) {
    requireFact(value && Object.getPrototypeOf(value) === Object.prototype &&
        Object.keys(value).length === keys.length && keys.every(key => Object.hasOwn(value, key)),
    '记账凭据字段无效');
}

function utc(value) {
    const ms = Date.parse(value);
    requireFact(typeof value === 'string' && /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{3})?Z$/.test(value) &&
        Number.isFinite(ms) && new Date(ms).toISOString() === value.replace(/Z$/, value.length === 20 ? '.000Z' : 'Z'),
    '记账凭据时间无效');
    return ms;
}

function count(value) {
    return Number.isSafeInteger(value) && value >= 0;
}

function readBoundFile(filename, expected, limit = 1024 * 1024) {
    requireFact(typeof filename === 'string' && path.isAbsolute(filename) && DIGEST.test(expected || ''), '缺少独立固定的文件摘要或绝对路径');
    const fd = fs.openSync(filename, fs.constants.O_RDONLY | fs.constants.O_NOFOLLOW | fs.constants.O_NONBLOCK);
    try {
        const stat = fs.fstatSync(fd);
        requireFact(stat.isFile() && stat.size <= limit && !(stat.mode & 0o222), '凭据必须是大小受限的只读普通文件');
        // 读不超过既定上限。固定摘要绑定同一份已打开文件的原始字节。
        const bytes = Buffer.alloc(stat.size + 1);
        let n = 0;
        while (n < bytes.length) {
            const size = fs.readSync(fd, bytes, n, bytes.length - n, null);
            if (size === 0) break;
            n += size;
        }
        const content = bytes.subarray(0, n);
        requireFact(n === stat.size && createHash('sha256').update(content).digest('hex') === expected, '凭据文件摘要不符');
        return JSON.parse(content.toString('utf8'));
    } finally {
        fs.closeSync(fd);
    }
}

function sameLedger(ledger, binding) {
    exact(binding, ['epoch_id', 'genesis', 'entries', 'tail', 'consumed']);
    return ledger.epoch.epoch_id === binding.epoch_id &&
        ledger.epoch.genesis_entry_hash === binding.genesis &&
        ledger.entries.length === binding.entries &&
        ledger.last_entry_hash === binding.tail &&
        stage.ledgerUsageSummary(ledger).consumed_request_count === binding.consumed;
}

function verifyHistory(history, ledger, evidence, accountObservedAt) {
    exact(history, ['retained', 'reported_entries', 'reported_tail', 'reported_consumed', 'provider_effect', 'missing_entries']);
    const usage = stage.ledgerUsageSummary(ledger);
    requireFact(sameLedger(ledger, history.retained) &&
        usage.ambiguous_consumed_request_ids.length === 0 &&
        ledger.entries.every(entry => utc(entry.recorded_at) <= utc(accountObservedAt)) &&
        ledger.requests.every(row => row.terminal_state !== null),
    '旧账本与已核验前缀不符或仍有未终止请求');
    const prior = evidence.runtime_bindings;
    requireFact(evidence.candidate_status === 'PREPARED_NOT_AUTHORIZED' &&
        prior?.accounting_epoch_id === ledger.epoch.epoch_id &&
        prior?.ledger_entries === history.reported_entries &&
        prior?.ledger_last_entry_hash === history.reported_tail &&
        utc(evidence.prepared_at) < utc(accountObservedAt) &&
        prior?.consumed_requests === history.reported_consumed,
    '历史候选原件与已记载的尾部不符');
    requireFact(history.provider_effect === 'UNKNOWN' && history.missing_entries === true &&
        count(history.reported_entries) && history.reported_entries > ledger.entries.length &&
        count(history.reported_consumed) && history.reported_consumed >= usage.consumed_request_count &&
        DIGEST.test(history.reported_tail), '历史缺口或未知扣费标记缺失');
}

function verifyAccount(account, opening, config) {
    exact(account, ['provider', 'account_identity_sha256', 'period_id', 'period_start_at', 'period_end_at', 'observed_at', 'used', 'remaining']);
    requireFact(account.provider === stage.PROVIDER &&
        account.account_identity_sha256 === opening.account_identity_sha256 &&
        DIGEST.test(account.account_identity_sha256) &&
        account.period_id === config.billing_period_id &&
        utc(account.period_start_at) === utc(config.period_start_at) &&
        utc(account.period_end_at) === utc(config.period_end_at) &&
        count(account.used) && count(account.remaining) &&
        account.used + account.remaining === config.monthly_quota_limit,
    '账户身份、账期或额度原件无法绑定');
    requireFact(config.monthly_quota_limit === 500 && config.automated_spend_limit === 450 &&
        config.reserved_safety_buffer === 50 && config.expected_request_cost_credits === 1 &&
        config.max_provider_requests_per_cycle === 1, '请求预算超出试点范围');
}

function verifyOpening(opening, account, config, ledger, now) {
    exact(opening, [
        'schema_version', 'account_identity_sha256', 'account_sha256', 'history_sha256',
        'quota_config_sha256', 'history', 'segment', 'approved_at', 'expires_at',
        'run_id', 'request_id', 'account_exclusive', 'account_prior_usage_reconciled',
    ]);
    exact(opening.segment, ['epoch_id', 'genesis', 'head', 'state_hash']);
    requireFact(opening.schema_version === SCHEMA && opening.account_exclusive === true &&
        opening.account_prior_usage_reconciled === true, '缺少账户独占和已有消费归属记录');
    requireFact([opening.run_id, opening.request_id].every(value => typeof value === 'string' && TOKEN.test(value)),
        '缺少当次请求身份');
    verifyAccount(account, opening, config);
    const observed = utc(account.observed_at);
    const approved = utc(opening.approved_at);
    const started = utc(ledger.epoch.started_at);
    const expires = utc(opening.expires_at);
    requireFact(observed >= utc(config.period_start_at) && observed <= approved && approved <= started &&
        started <= utc(now) && started < expires && expires <= Math.min(observed + DAY_MS, utc(config.period_end_at)),
    '时点超出证据、账期或批准窗口');
    requireFact(ledger.epoch.epoch_id !== opening.history.retained.epoch_id &&
        ledger.epoch.epoch_id === opening.segment.epoch_id &&
        ledger.epoch.genesis_entry_hash === opening.segment.genesis &&
        ledger.epoch.start_authority_head === opening.segment.head &&
        ledger.epoch.start_authority_state_hash === opening.segment.state_hash, '后续账本不是已绑定的记账段');
}

function verifySingleRequest(ledger, opening, account, config, now) {
    if (ledger.entries.length === 0) return { state: 'PENDING', quota_receipt: null };
    requireFact(ledger.requests.length === 1 && ledger.requests[0].request_id === opening.request_id &&
        ledger.requests[0].run_id === opening.run_id &&
        ledger.entries.every(entry => utc(entry.recorded_at) >= utc(ledger.epoch.started_at) &&
            utc(entry.recorded_at) <= utc(now)), '后续账本包含超出试点的活动');
    const request = ledger.requests[0];
    if (request.terminal_state !== 'RESPONSE_RECEIVED' || request.transmitted_at === null ||
        request.provider_quota === null || request.receipt_evidence_reference === null) {
        return { state: 'STOPPED', quota_receipt: null };
    }
    requireFact(utc(request.transmitted_at) >= utc(ledger.epoch.started_at) &&
        utc(request.transmitted_at) < utc(opening.expires_at) &&
        request.response_received_at && utc(request.response_received_at) < utc(config.period_end_at),
    '传输或回执超出绑定账期');
    const reconciled = stage.reconcileProviderQuotaHeaders({
        headers: request.provider_quota.raw_headers,
        quotaConfig: config,
        expectedRequestCostCredits: 1,
        localConsumedAfterRequest: account.used + 1,
        previousProviderQuota: { reported_used: account.used, reported_remaining: account.remaining },
    });
    return { state: 'RECONCILED', quota_receipt: reconciled };
}

function verifyIdleAndCurrent(input, opening, pending) {
    for (const root of [input.priorLedgerRoot, input.ledgerRoot]) {
        const lock = stage.inspectStageDRunLock({ operationRoot: root, runLockTrustRoot: input.runLockTrustRoot });
        requireFact(lock.state === 'ABSENT', `存在运行锁或待核对的运行状态 (${lock.error_code || lock.state})`);
    }
    if (!pending) return;
    const authority = openMarketEvidenceAuthoritySnapshot({
        storeRoot: input.authorityRoot,
        allocationArtifactPath: input.allocationAuthorityPath,
    });
    requireFact(authority.head_transaction_id === opening.segment.head &&
        authority.state_hash === opening.segment.state_hash, '交易状态已偏离记账起点');
}

function inspectForwardAccounting(input) {
    for (const root of [input.priorLedgerRoot, input.ledgerRoot, input.authorityRoot, input.allocationAuthorityPath, input.runLockTrustRoot]) {
        requireFact(typeof root === 'string' && path.isAbsolute(root), '必须显式指定隔离目录的绝对路径');
    }
    const opening = readBoundFile(input.openingPath, input.openingSha256);
    const account = readBoundFile(input.accountPath, opening.account_sha256);
    const history = readBoundFile(input.historyPath, opening.history_sha256);
    const config = stage.validateQuotaConfiguration(readBoundFile(input.quotaConfigPath, opening.quota_config_sha256));
    const prior = stage.readRequestLedger({ ledgerRoot: input.priorLedgerRoot });
    const forward = stage.readRequestLedger({ ledgerRoot: input.ledgerRoot });
    verifyHistory(opening.history, prior, history, account.observed_at);
    verifyOpening(opening, account, config, forward, input.now);
    const checkpoint = readBoundFile(input.checkpointPath, input.checkpointSha256);
    exact(checkpoint, ['opening_sha256', 'ledger']);
    requireFact(checkpoint.opening_sha256 === input.openingSha256 &&
        sameLedger(forward, checkpoint.ledger), '后续账本与独立锚点不符');
    requireFact(account.used + 1 <= config.automated_spend_limit &&
        account.remaining - 1 >= config.reserved_safety_buffer, '预留一次请求会超过预算');
    const reviewed = verifySingleRequest(forward, opening, account, config, input.now);
    const fresh = utc(input.now) < utc(opening.expires_at);
    const wouldReserve = reviewed.state === 'PENDING' && fresh;
    verifyIdleAndCurrent(input, opening, wouldReserve);
    return {
        mode: 'OFFLINE_FORWARD_ACCOUNTING',
        opening_sha256: input.openingSha256,
        state: reviewed.state,
        would_reserve_one: wouldReserve,
        forward_ledger_entries: forward.entries.length,
        forward_ledger_tail: forward.last_entry_hash,
        starting_used: account.used,
        starting_remaining: account.remaining,
        quota_receipt: reviewed.quota_receipt,
        provider_requests: 0,
        transmission_permitted: false,
    };
}

module.exports = { inspectForwardAccounting };
