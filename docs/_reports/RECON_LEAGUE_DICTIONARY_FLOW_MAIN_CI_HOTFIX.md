# Recon League Dictionary Flow Main CI Hotfix

## Main CI Failure

- **Run ID**: 25635881128
- **Job**: Environment / Proxy / Static / Unit Gate
- **Failed step**: Run Gatekeeper (npm run test:coverage)
- **Failed test**: Recon League Dictionary Flow > 应支持组合对阵与占位赛程在先回源后通过本地字典候选完成自愈
- **File**: tests/unit/ReconLeagueDictionaryFlow.test.js:314
- **Actual**: `'exact'`
- **Expected**: `'dictionary'`

## Root Cause

测试依赖 `savedMappings` 数组中映射的顺序。但 `Promise.all` 并发
处理多场比赛，映射持久化顺序取决于异步完成时间，不保证与输入顺序
一致。

测试中 Match 2（占位赛程 `Winner SF 1 vs Winner SF 2`）的映射处理
比 Match 1（组合对阵 `Sporting Cp Arsenal vs Barcelona Atletico Madrid`）
更快完成，因此匹配结果中 `mapping[0].mapping_method === 'exact'`、
`mapping[1].mapping_method === 'dictionary'`。

测试原来假设 `mapping[0]` 一定是字典匹配，属于不稳定的顺序依赖。

## Fix

不再按数组索引断言，改为按 `match_id` 查找对应映射：

- `'42_20252026_5205814'` → `mapping_method = 'dictionary'`（组合对阵，通过字典解析）
- `'42_20252026_5205834'` → `mapping_method = 'exact'`（占位赛程，队名完全相等）

## Why This Is Not Lowering Test Quality

- 修改前后覆盖的断言完全相同：两种 mapping_method 各出现一次，
  各有 confidence=1，各对应正确的 match_id
- 新写法消除了不稳定的排序假设，使测试在任何异步调度下都可复现
- 没有修改被测代码逻辑，没有 skip/delete 测试，没有降低覆盖率阈值
- 没有绕过 gatekeeper

## Validation

- ReconLeagueDictionaryFlow.test.js 3/3 通过（连续 5 次）
- npm test 48/48 通过
- npm run test:coverage 通过
- npm run test:integration 19 pass, 5 skipped, 0 fail
- eslint / prettier / git diff --check 通过

## Explicit Non-Execution

未执行：coverage 阈值修改、skip/delete 测试、gatekeeper 绕过、DB writes、
non-SELECT SQL、curl/wget/git clone、外部数据访问、scraping、browser automation、
proxy runtime、harvest/ingest/backfill、network dry-run、staging write、
source manifest write、packet file write、runtime file writes、pg_dump/pg_restore、
model training、real prediction、model artifact loading、Docker volume cleanup、
force push、git fetch --all、git pull、file deletion
