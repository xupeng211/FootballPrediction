# Manifest Management

`docs/_manifests` 保存 source-controlled metadata，不是无限增长的 phase snapshot 仓库。

## Rules

- 优先维护 current effective state。
- phase artifact 只记录本阶段 delta、输入、输出、hash 和 blocker。
- 不复制完整历史 manifest，除非 reviewer 无法用较小 delta 重建必要上下文。
- 不保存 full body、full JSON、full raw_data 或 full pageProps。
- 大型 artifact 默认不进入 `main`；优先使用 hash、row count、schema summary、sample path 或 CI artifact。
- manifest 字段必须有 reader、gate 或 review 价值；不得为了测试 allowlist 继续堆字段。
- historical artifact 清理或 archive 重构必须单独授权，不和普通 implementation PR 混做。

## Preferred Shape

- current batch/source/route/data_version/hash_strategy
- current per-target identity/baseline/blocker state
- accepted baseline hash or proposal hash, with status
- next required action
- short references to historical reports or phase artifacts
