<!-- markdownlint-disable MD013 MD034 MD012 MD022 MD032 MD050 MD001 -->
# FotMob Endpoint Runtime Request Discovery Next Plan

- lifecycle: current-state
- phase: FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-ENDPOINT-RUNTIME-REQUEST-DISCOVERY-PLAN-NO-WRITE
- source_phase: FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-FOTMOB-PAGE-NO-EMBEDDED-DETAIL-DECISION-NO-WRITE

## Why HTML Hydration Route Is Exhausted

- 所有 /matches/{route_code}/{match_id} 变体（default, zh-Hans, /en）均解析 __NEXT_DATA__ 成功，
  但 pageProps 内只有 fetchingLeagueData / translations / notableMatches / ssr。
- 没有 header / general / content / matchFacts / stats / lineup / events / teams 等 match detail key。
- target match_id 从未在 key path 中出现。
- strong/weak path candidate count = 0。
- 原始 slug path 甚至不包含 __NEXT_DATA__。

## Why Page-Level NEXT_DATA Has No Match Detail

- FotMob 的 Next.js ISR/fetch-based 架构在服务端从 CDN/API 获取 match detail JSON，
  但通过 pageProps.fallback 注入到页面的只是 notableMatches 这类通用推荐数据。
- 实际的 match detail 数据（header/content/general/matchFacts/stats/lineup/events）
  很可能通过客户端 fetch / streaming / WebSocket 动态加载，并不出现在服务端渲染的 HTML 中。
- Direct API 路径 /api/matchDetails 返回 404、/api/data/matchDetails 返回 403，
  说明 API 不通过简单 GET 暴露。

## 下一阶段目标

- 不使用浏览器、不绕反爬、不抓 cookie。
- 只做 repo 内历史线索和公开 endpoint pattern 的 no-network plan。
- 明确可能的 endpoint/runtime request discovery 方向。

## 可能方向

1. **historical endpoint pattern review**:
   审查 FotMobRawDetailFetcher / FotMob client / ADG 历史文档，找出曾经可用的 endpoint 模板。
2. **Next.js buildId data route review**:
   审查 Next.js _next/data/{buildId} 和 ISR data route 模式。
3. **public/static JSON route review**:
   审查 FotMob 是否在某些路径下暴露 static JSON。
4. **alternative source fallback**:
   评估其他数据源（ESPN, SofaScore, FlashScore, 官方 API 等）。
5. **paid data source evaluation**:
   评估 paid API（SportMonks, API-Football, Opta 等）作为 fallback。

## 保守限制

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
