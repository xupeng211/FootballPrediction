# Score Backfill Write Verification
- lifecycle: phase-artifact
- scope: authorized real score backfill write for Ligue 1 2025/2026
- date: 2026-06-19
- branch: `data/score-backfill-write`
- parent: `data/score-backfill-dry-run`

## Authorization

用户已明确授权执行真实 score backfill write。This report documents the execution, verification, and outcomes.

## Preflight 结果

| 指标 | 预期 | 实际 | 匹配 |
| --- | ---: | ---: | --- |
| `total_matches_scanned` | 60 | 60 | ✓ |
| `target_ligue1_count` | 58 | 58 | ✓ |
| `would_update_count` | 58 | 58 | ✓ |
| `would_skip_count` | 2 | 2 | ✓ |
| `scoreStr` 可用 | 58/58 | 58/58 | ✓ |
| `teams[0].score` 可用 | 58/58 | 58/58 | ✓ |
| `teams[1].score` 可用 | 58/58 | 58/58 | ✓ |
| `scoreStr` 与 `teams score` 一致 | 58/58 | 58/58 | ✓ |
| `mismatch_count` | 0 | 0 | ✓ |
| `actual_result` 分布 | H=23/D=17/A=18 | H=23/D=17/A=18 | ✓ |

2 条 no-raw excluded 已确认跳过：
- `47_20242025_900002` — Segunda 2024/2025, synthetic, 已有 scores
- `140_20252026_4837496` — Segunda División 2025/2026, scheduled, pending

Preflight 全部通过，进入真实写入。

## 写入范围

仅写入 `matches` 表的三个字段：
- `matches.home_score`
- `matches.away_score`
- `matches.actual_result`

目标范围：
- 58 条 Ligue 1 / 2025/2026
- `status=finished`, `pipeline_status=harvested`
- `source_type=fotmob_live_fetch`, `evidence_level=strong`
- `raw_match_data.data_version=fotmob_live_v1`
- 写入前 `home_score/away_score/actual_result` 全部为 NULL

## 写入 SQL 安全边界

使用单条参数化 VALUES-based UPDATE，单事务执行：

```sql
UPDATE matches m SET
  home_score = v.home_score,
  away_score = v.away_score,
  actual_result = v.actual_result
FROM (VALUES
  ($1::integer, $2::integer, $3, $4::text),
  ...
  ($229::integer, $230::integer, $231, $232::text)
) AS v(home_score, away_score, actual_result, match_id)
WHERE m.match_id = v.match_id
  AND m.home_score IS NULL
  AND m.away_score IS NULL
  AND m.actual_result IS NULL
RETURNING m.match_id
```

防误写措施：
1. `WHERE m.match_id = v.match_id` — 精确 match_id 命中
2. `AND m.home_score IS NULL` — 防止覆盖已有 score
3. `AND m.away_score IS NULL` — 防止覆盖已有 score
4. `AND m.actual_result IS NULL` — 防止覆盖已有 result
5. 单事务 — 任何失败自动 ROLLBACK
6. `RETURNING m.match_id` — 验证实际更新行数

## 写入结果

- `updated_count`: **58** (与 expected_count=58 完全一致)
- `write_result.success`: **true**

## Post-Write Verification

| 校验项 | 预期 | 实际 | 状态 |
| --- | ---: | ---: | --- |
| `updated_count` | 58 | 58 | ✓ |
| `matches` 总行数 | 60 | 60 | ✓ |
| `raw_match_data` 总行数 | 76 | 76 | ✓ |
| `pipeline_status=harvested` | 58 | 58 | ✓ |
| `pipeline_status=pending` | 2 | 2 | ✓ |
| `is_training_eligible=true` | 0 | 0 | ✓ |
| `is_training_eligible=false` | 60 | 60 | ✓ |
| 58 条法甲 score/result 非空 | 58 | 58 | ✓ |
| `actual_result` 分布 | H=23/D=17/A=18 | H=23/D=17/A=18 | ✓ |

## actual_result 编码

全部使用 `home_win / draw / away_win`，来源规则：

```
home_score > away_score => home_win
home_score = away_score => draw
home_score < away_score => away_win
```

分布：home_win=23, draw=17, away_win=18。

## 2 条 no-raw excluded 未写入

| `match_id` | home_score | away_score | actual_result | 被本次写入修改 |
| --- | --- | --- | --- | --- |
| `47_20242025_900002` | 1 (已有) | 0 (已有) | home_win (已有) | 否 |
| `140_20252026_4837496` | NULL | NULL | NULL | 否 |

`47_20242025_900002` 在写入前已有 synthetic scores — 本次未修改。
`140_20252026_4837496` 保持 NULL — 本次未修改。

## 安全确认

| 项目 | 状态 |
| --- | --- |
| 无 migration | ✓ |
| 无 schema change | ✓ |
| 无 raw_match_data 写入 | ✓ |
| 无 live fetch | ✓ |
| 无 raw payload 输出 | ✓ |
| 无 parser 变更 | ✓ |
| 无 training 变更 | ✓ |
| 无 prediction 变更 | ✓ |
| 无 pipeline_status 变更 | ✓ |
| 无 is_training_eligible 变更 | ✓ |
| 单事务 | ✓ |
| 严格 WHERE 条件 | ✓ |

## 下一步

真实 score backfill write 已完成。下一步必须用户确认：
1. 是否需要对写入数据进行进一步验证
2. 是否需要将 `is_training_eligible` 设为 true（不在本次范围）
3. 是否进入其他联赛的 score backfill（不在本次范围）
