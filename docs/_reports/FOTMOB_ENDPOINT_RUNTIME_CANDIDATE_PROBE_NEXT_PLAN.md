<!-- markdownlint-disable MD013 MD034 MD012 MD022 MD032 MD050 MD001 -->
# FotMob Endpoint Runtime Candidate Probe Next Plan

- lifecycle: current-state
- phase: FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-ENDPOINT-RUNTIME-CANDIDATE-PROBE-NO-WRITE
- source_phase: FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-ENDPOINT-RUNTIME-REQUEST-DISCOVERY-PLAN-NO-WRITE

## Why Endpoint/Runtime Discovery

- HTML hydration 路线已正式耗尽（#1451 decision）。
- 所有 page-level 路径（default, zh-Hans, /en, slug）均无 match detail JSON。
- Direct API（/api/matchDetails=404, /api/data/matchDetails=403）被阻断。
- 必须转向 endpoint/runtime request 方向寻找真实数据入口。

## Candidate Endpoints for Next Probe

最多测试 3 个候选 endpoint：

1. **_next/data route with buildId**:
   - /_next/data/{buildId}/en/match/{match_id}.json
   - 来源: Next.js ISR data route pattern
   - confidence: 5/10, risk: 6/10
   - 预期: JSON, 可能包含 pageProps

2. **_next/data matches route**:
   - /_next/data/{buildId}/en/matches/{route_code}/{match_id}.json
   - 来源: 基于 #1449 已确认的 Next.js page route
   - confidence: 5/10, risk: 6/10
   - 预期: JSON, 与 HTML page route 对应的 data endpoint

3. **FotMob match listing API**:
   - /api/matches?date={date} or similar pattern
   - 来源: FotMobApiClient.js 历史使用模式
   - confidence: 3/10, risk: 7/10
   - 预期: JSON, match list with possible detail links

## Next Probe Limits

- max_candidates: 3
- max_samples: 2
- max_network_requests: 6
- max_body_bytes: 262144

## Next Probe Success Criteria

- status_code=200
- content_type JSON or JSON-like
- target match_id appears in response metadata/path
- match detail signal score >= 8

## Next Probe Stop Conditions

- 403 Forbidden
- 429 Too Many Requests
- captcha/bot page detected
- body limit exceeded
- repeated 404

## Safety Constraints

- 不保存 full HTML
- 不保存 full NEXT_DATA
- 不保存 raw JSON
- 不保存 values
- 不写 DB
- 不启用 scheduler
- 不使用 browser automation
- 不绕反爬
- 不抓 cookie
- 不旋转代理
