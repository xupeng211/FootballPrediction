<!-- markdownlint-disable MD013 MD012 -->
# FotMob Payload Shape Reconstruction Next Plan

- lifecycle: current-state
- phase: HISTORICAL-FOTMOB-PAYLOAD-SHAPE-RECONSTRUCTION-READONLY
- source_phase: SAFE-PARSER-SCHEMA-REUSE-PLAN-NO-WRITE

## Why Payload Shape Reconstruction

- 历史有 2,501 条 raw JSON 但没有 canonical shape 文档。
- 测试 fixture (match_success.json) 只覆盖部分结构。
- 不同 FotMob API 版本的 payload 形状可能不同。
- 需要系统性地重构 canonical payload shape 作为未来所有 parser 的接口契约。

## Reconstruction Tasks

1. Validate canonical shape against match_success.json fixture
2. Validate canonical shape against FotMobRawDetailFetcher hash/validation expectations
3. Document field aliases (matchId vs external_id vs id)
4. Document type constraints (numeric IDs, score strings, coordinate types)
5. Create lightweight canonical schema definition (JSON Schema or TypeScript interface)
6. Ensure parser tests cover all canonical sections

## Safety

- 不访问网络
- 不读 DB
- 不写 DB
- 不使用 browser automation
- 不抓 cookie
- 不绕反爬
- 只基于 repo 内已有 fixture/report/代码
