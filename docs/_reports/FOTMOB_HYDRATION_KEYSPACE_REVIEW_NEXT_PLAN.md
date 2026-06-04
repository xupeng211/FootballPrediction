<!-- markdownlint-disable MD013 MD034 MD012 MD022 MD032 MD050 MD001 -->
# FotMob Hydration Keyspace Review Next Plan

- lifecycle: current-state
- phase: FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-HYDRATION-KEYSPACE-REVIEW-NO-WRITE
- source_phase: FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-MATCH-DETAIL-SUBTREE-REVIEW-FOLLOWUP-NO-WRITE

## Why Keyspace Review Is Needed

- #1447 只命中 props.pageProps.fallback.notableMatches:en:USA，且 score=-5。
- notableMatches 是 generic notable matches，不是 match detail；它缺少目标 match_id、球队名和详情模块 key。
- 继续只扫 fallback.notableMatches 会重复命中已排除路径，不能推进 raw write readiness。

## Next Scan Scope

- bounded __NEXT_DATA__ keyspace metadata review。
- 记录 key path、data type、depth、approximate size、key name、marker flags、score、classification、route variant。
- 不保存 value，不保存 subtree values，不保存 full JSON，不保存 full HTML。

## Route Variants

| Variant | Recommendation | Reason |
|---|---|---|
| /matches/{route_code}/{match_id} | keep | current working route parses __NEXT_DATA__/pageProps/fallback but only found generic notableMatches |
| /zh-Hans/matches/{route_code}/{match_id} | review next | target user seeds were supplied with zh-Hans locale and should be compared as metadata only |
| /en/matches/{route_code}/{match_id} | review next | English locale variant may change hydration keyspace or fallback cache keys |
| original user URL path without fragment | review next | seed slug paths provide canonical slug evidence without using the fragment as a request path |

## Bounds

- max_samples: 2
- max_network_requests: <= 2
- max_body_bytes: <= 524288
- max_key_paths_recorded: <= 500
- max_value_preview_chars: 0
- max_scan_depth: <= 12

## Forbidden

- 不保存 full HTML
- 不保存 full NEXT_DATA
- 不保存 raw JSON
- 不保存 subtree values
- 不写 DB
- 不启用 scheduler
- 不使用 browser automation
- 不绕过反爬

## Success Criteria

- 找到非 notableMatches 的 candidate key path metadata。
- 发现含 match/detail/header/content/general/stats/events/lineup/matchFacts marker 的路径。
- 仍保持 json_validated_count=0 和 raw_write_eligible_count=0。

## Failure Criteria

- 两个样本仍只出现 generic notableMatches / translations / static config。
- route variants 没有增加任何 detail keyspace evidence。

## Recommended Next Step

- **FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-HYDRATION-KEYSPACE-REVIEW-NO-WRITE**
