# TEP-001: Titan 历史数据大宗装卸蓝图 (CSV Bulk Loader)

> 状态: Draft  
> 分支: `docs/tep-001-csv-bulk-loader`  
> 作者角色: Chief Architect  
> 最后更新: `2026-04-22`

---

## 1. 背景与战略目标

Titan 现阶段已经验证了一条重要结论: 依赖高风险外网抓取、浏览器伪装、代理漂移与临时反制逻辑的历史回补路线，工程代价高、复现性差、合规风险大、交付吞吐不稳定。对于大宗历史赔率与赛果资产，继续把主链路压在外网抓取上，不符合工业化数据工厂的长期方向。

TEP-001 的目标，是将历史数据摄取能力从“高耦合外网拉取”转向“合规离线大文件装载”:

- 以 CSV 为主输入介质，支持供应商导出文件、人工整理文件、合规采购数据包。
- 以流式处理替代一次性全量载入，确保数十万行历史数据在受控内存下稳定运行。
- 以批量落库替代逐行写入，提高导入吞吐并减少数据库事务开销。
- 以 EntityMapper V2 统一处理历史 CSV 中不规范的联赛名、队名、博彩公司名。
- 以脏数据隔离和异常旁路为原则，确保单行错误不拖垮整批任务。

战略上，这不是“补一个脚本”，而是给 Titan 建立一条可重复执行、可审计、可回放的历史数据装卸底座。

---

## 2. 设计范围与非目标

### 2.1 设计范围

- 定义 `scripts/ops/csv_bulk_loader.js` 的流式导入骨架。
- 定义 CSV -> 标准化对象 -> 批量 UPSERT 的处理链。
- 定义 `EntityMapper V2` 的字典、别名、模糊匹配与人工回填机制。
- 定义脏数据隔离、异常日志、批处理熔断与恢复策略。
- 定义与 `matches`、`raw_match_data`、`bookmaker_odds_history` 等表的对接边界。

### 2.2 非目标

- 本 TEP 不引入 Puppeteer、Playwright 或任何隐藏浏览器抓取方案。
- 本 TEP 不要求首版接入 ML 模型做队名实体消歧。
- 本 TEP 不试图一次性解决所有历史供应商格式，只定义统一装载骨架与扩展点。

---

## 3. 核心流式架构 (Streaming & Batching)

### 3.1 总体原则

`csv_bulk_loader.js` 必须采用 Node.js Stream API，以“逐块读取、逐行解析、分批提交、显式背压”为一等公民。禁止 `readFile()` 将整个 CSV 一次性读入内存。

设计约束:

- 单文件处理规模目标: `100,000+` 行。
- 进程常驻内存目标: 常态 `< 300MB`，峰值可观测且可限流。
- 批量写入目标: 单批 `500-2,000` 行可配置。
- 导入语义: 幂等，可重复执行，已存在记录可 `UPSERT`。

### 3.2 推荐处理拓扑

```text
fs.createReadStream(csv)
  -> CSV Parser Transform
  -> Row Validator Transform
  -> EntityMapper V2 Transform
  -> Batch Aggregator Writable
  -> Postgres Batch UPSERT
```

各阶段职责:

1. `ReadStream`
   - 只负责按块读取文件。
   - `highWaterMark` 可调，避免过大缓冲。

2. `CSV Parser`
   - 将文本流转为对象流。
   - 负责表头识别、字段拆分、类型初步转换。

3. `Row Validator`
   - 校验必填列、日期格式、赔率字段、主键候选列。
   - 对格式损坏行直接旁路到异常通道。

4. `EntityMapper V2`
   - 将原始联赛名、队名、博彩公司名标准化。
   - 输出 `mappingConfidence`、`mappingMethod`、`reviewRequired`。

5. `Batch Aggregator`
   - 聚合到指定 batch size 后写库。
   - 必须等待批量事务结束后再继续推进，利用 backpressure 防止内存堆积。

### 3.3 `csv_bulk_loader.js` 骨架

```javascript
// scripts/ops/csv_bulk_loader.js
const fs = require('fs');
const { pipeline } = require('stream/promises');
const csv = require('csv-parser');

async function runBulkLoad(options) {
  const source = fs.createReadStream(options.inputPath, {
    encoding: 'utf8',
    highWaterMark: options.highWaterMark || 64 * 1024,
  });

  const parser = csv({
    separator: options.delimiter || ',',
    strict: false,
    skipLines: 0,
  });

  const validator = createRowValidatorTransform(options);
  const mapper = createEntityMapperTransform(options);
  const batchWriter = createBatchWriter({
    batchSize: options.batchSize || 1000,
    flushIntervalMs: options.flushIntervalMs || 2000,
  });

  await pipeline(source, parser, validator, mapper, batchWriter);
}
```

### 3.4 Batch Insert 设计

首版优先使用批量 `INSERT ... ON CONFLICT DO UPDATE`，而不是单行写入。

推荐策略:

- 一批一事务，降低长事务风险。
- 只在批次边界持有连接，避免导入全程占满连接池。
- 按目标表拆分批次:
  - `matches`
  - `raw_match_data`
  - `bookmaker_odds_history`
- 记录每批 `batchIndex / rowCount / inserted / updated / failed / latencyMs`。

伪代码:

```javascript
async function flushBatch(client, rows) {
  await client.query('BEGIN');
  try {
    await upsertMatches(client, rows);
    await upsertRawData(client, rows);
    await upsertOddsHistory(client, rows);
    await client.query('COMMIT');
  } catch (error) {
    await client.query('ROLLBACK');
    throw error;
  }
}
```

### 3.5 防 OOM 关键点

- 使用对象流，不保留完整历史数组。
- batch flush 后立即清空缓冲区。
- 禁止在 mapper 中缓存整文件级别的原始行对象。
- 映射字典常驻内存，但需是预热后的只读索引结构，不得按行追加无限增长。
- 导入进度、异常样本、统计日志使用滚动写盘或增量输出，禁止积压到内存再统一打印。

### 3.6 数据库并发建议

默认不追求极限并行写库，优先稳定:

- 单文件导入默认 `writerConcurrency = 1`
- 多文件批处理可做“文件级并行、文件内串行批次”
- 当数据库 CPU 或 WAL 压力上升时，通过配置降低 `batchSize`

首版判断标准不是“跑得最快”，而是“不会炸、可回放、吞吐稳定”。

---

## 4. EntityMapper V2: 字典升级机制

### 4.1 问题定义

历史 CSV 中常见脏数据包括:

- 队名别称: `Man Utd`, `Manchester Utd`, `Manchester United FC`
- 联赛缩写: `EPL`, `Premier`, `Premier League`
- 多语言变体: `Segunda`, `Segunda División`
- 供应商噪声: 多余年份、地区、括号、青年队后缀

如果没有统一映射层，批量导入只会把历史脏数据更快地污染进主库。

### 4.2 V2 总体结构

`EntityMapper V2` 拆为四层:

1. 规则归一化层
   - 小写化、去重音、去标点、去括号、标准化空白符。

2. 精确别名字典层
   - 基于 `Map<normalizedAlias, canonicalName>` 做 O(1) 命中。

3. 候选召回层
   - 前缀召回、token overlap、trigram/Jaccard 相似度。

4. 人工校正回流层
   - 未命中或低置信候选输出到 review 队列，确认后回灌 alias dictionary。

### 4.3 建议数据结构

```text
EntityMapperV2
├── teamAliasMap
├── leagueAliasMap
├── bookmakerAliasMap
├── normalizedTokenIndex
├── fuzzyCandidateScorer
└── reviewQueueWriter
```

### 4.4 置信度分层

建议输出统一结构:

```json
{
  "canonicalName": "Manchester United",
  "mappingMethod": "alias_exact",
  "mappingConfidence": 1.0,
  "reviewRequired": false
}
```

分层建议:

- `alias_exact`: 1.00，直接通过
- `normalized_exact`: 0.98，直接通过
- `token_match`: 0.85-0.95，可通过但需审计采样
- `fuzzy_match`: 0.70-0.85，默认进入 review
- `unresolved`: 0.00，不入主表实体字段，只写异常与待处理队列

### 4.5 冷启动路径

在没有 ML 的前提下，V2 不应空等“未来模型”，而应先做高性价比字典:

- 从现有 `matches` 表提取历史 canonical team / league 名单。
- 从 `data/raw_json/`、既有 RECON mapping、手工 CSV 中反向收集 alias。
- 为高频联赛先建立人工维护白名单。
- 把每次人工修正都沉淀回 alias registry，形成可持续增量资产。

### 4.6 不可直接写死在代码中的内容

以下内容不应在实现里散落硬编码:

- 联赛别名
- 球队别名
- 博彩公司映射
- 模糊匹配阈值

这些必须进入配置或数据字典文件，成为可审计、可版本化资产。

---

## 5. 容错、熔断与脏数据隔离

### 5.1 脏数据隔离原则

核心红线:

- 单行损坏不得导致整个文件失败。
- 单批失败不得直接吞掉上下文，必须可诊断。
- 结构性错误和数据质量错误要分开记录。

### 5.2 异常分级

1. `ROW_FORMAT_ERROR`
   - CSV 列数不一致
   - 日期无法解析
   - 必填列缺失

2. `ENTITY_UNRESOLVED`
   - 队名或联赛名无法可靠映射

3. `DB_CONSTRAINT_ERROR`
   - 外键、唯一键、长度约束失败

4. `SYSTEM_ERROR`
   - 数据库连接失败
   - 文件损坏
   - 写盘失败

### 5.3 隔离与降级策略

对于单行错误:

- 记录到 `logs/csv_bulk_loader_errors.jsonl` 或同类结构化日志。
- 保留 `filePath`, `rowNumber`, `rawRow`, `errorCode`, `errorMessage`。
- 主流程继续。

对于批次错误:

- 先回滚该批事务。
- 自动降级到“行级重试模式”或“二分排障模式”，找出坏行。
- 将坏行隔离，其余正常行继续装载。

对于系统性错误:

- 当数据库不可用、连接池耗尽、错误率超过阈值时触发熔断。
- 熔断后停止后续批次，输出未处理行数和最后成功 offset。

### 5.4 推荐熔断阈值

- 连续批次失败 `>= 3` 次: 停止任务
- 单文件坏行比例 `> 5%`: 标记为 degraded，要求人工复核
- 批次平均写入延迟连续飙升 `> 3x baseline`: 自动下调 batch size

### 5.5 恢复能力

必须支持 checkpoint:

- 记录 `filePath`, `byteOffset` 或 `rowNumber`, `lastCommittedBatch`
- 支持从最近成功批次继续
- 不依赖人工从头重跑整个大文件

---

## 6. 数据落库策略

### 6.1 推荐落库顺序

1. 标准化并确认 `match_id`
2. UPSERT `matches`
3. 写入 `raw_match_data`
4. 写入 `bookmaker_odds_history`
5. 输出导入审计记录

### 6.2 幂等要求

所有装载必须满足:

- 重跑同一 CSV 不产生重复脏记录
- 同一 `match_id + bookmaker_name + market_type` 采用 UPSERT
- 可通过 `source_digest` 识别相同数据载荷

### 6.3 审计字段建议

建议为装载记录增加以下审计字段:

- `source_file`
- `source_row_number`
- `import_run_id`
- `source_digest`
- `loaded_at`
- `mapping_method`
- `mapping_confidence`

---

## 7. 可观测性与运维接口

### 7.1 运行指标

必须输出:

- `rowsRead`
- `rowsValidated`
- `rowsMapped`
- `rowsInserted`
- `rowsUpdated`
- `rowsSkipped`
- `rowErrorCount`
- `batchLatencyP50/P95`
- `currentMemoryRssMb`

### 7.2 运行日志

日志必须结构化，至少带:

- `import_run_id`
- `file_path`
- `batch_index`
- `row_number`
- `stage`
- `event`
- `duration_ms`

### 7.3 成功定义

首版成功标准:

- 100k 行 CSV 在受控内存下跑完
- 无 OOM
- 单行坏数据不会中断全局任务
- 可重复执行且主表无重复污染

---

## 8. 实施建议

### 8.1 Phase 1

- 只支持单文件 CSV
- 只支持 `matches` + `bookmaker_odds_history`
- 只上 alias exact + normalized exact
- 提供 dry-run 与 commit 模式

### 8.2 Phase 2

- 支持多文件批处理
- 增加 checkpoint resume
- 增加 unresolved review queue
- 增加 token match / trigram match

### 8.3 Phase 3

- 支持更多供应商 schema
- 支持批量审计报表
- 视价值再评估是否接入轻量 ML reranker

---

## 9. 架构结论

TEP-001 的核心价值，不是把 CSV 更快地塞进数据库，而是把 Titan 的历史资产装载从“高风险、一次性、人工盯盘”升级为“可复现、可旁路、可治理”的工业化链路。

真正的关键点只有三个:

1. 流式处理，保证大文件不炸内存。
2. EntityMapper V2，保证历史脏名称不会污染主库。
3. 脏数据隔离，保证坏数据被拦截而不是拖垮全批。

只要这三点守住，Titan 才有资格把历史 CSV 装载能力定义为正式生产资产，而不是临时导入脚本。
