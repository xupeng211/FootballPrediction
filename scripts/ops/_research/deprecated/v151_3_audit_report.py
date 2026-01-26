#!/usr/bin/env python3
"""
V151.3 生产效能与成本审计报告
Production Performance & Cost Audit Report

审计日期: 2026-01-11
审计人: 高级数据运维架构师
版本: V151.3

---

## 执行摘要 (Executive Summary)

⚠️ **关键发现**:
1. 搜索模式成本过高 - 1,900 场西甲需要 ~12 小时连续运行
2. 存在无限重试风险 - 缺少 retry_count 上限
3. 单线程采集速度不足 - 实测 ~160s/场

---

## 1. 搜索模式压力测试 (Search Cost Audit)

### 1.1 时间成本分析

基于 `search_match_url()` 代码分析：

| 步骤 | 预计耗时 | 说明 |
|------|----------|------|
| 访问搜索页面 | 2-5s | page.goto with timeout=60s |
| 等待搜索结果 | 5s | 硬编码 await asyncio.sleep(5) |
| 查找比赛链接 | 1-3s | 多选择器查询 |
| 点击链接 | 1s | match_link.click() |
| 等待跳转 | 3s | 硬编码 await asyncio.sleep(3) |
| **单场搜索小计** | **12-17s** | 平均 ~15s |
| 场间延迟 | 5-10s | delay_range 默认值 |
| **单场总耗时** | **17-27s** | 平均 ~22s |

### 1.2 西甲全量搜索成本

```
比赛数量: 1,900 场 (La Liga)
单场耗时: ~22s
总耗时: 1,900 × 22s = 41,800s ≈ 11.6 小时

代理压力:
- 单线程连续运行 12 小时
- 请求频率: ~158 次/小时
- 风险评级: 🔴 HIGH (单 IP 长时间高频请求)
```

### 1.3 意甲全量搜索成本

```
比赛数量: 1,901 场 (Serie A)
总耗时: ~11.6 小时

西甲 + 意甲合计:
- 总场次: 3,801 场
- 总耗时: ~23.2 小时 (连续运行)
- 代理风险: 🔴 CRITICAL
```

### 1.4 英超复活数据搜索成本

```
已复活记录: 1,868 场 (Premier League)
预计耗时: ~11.5 小时

三大联赛合计:
- 总场次: 5,669 场
- 总耗时: ~34.7 小时
```

---

## 2. 熔断与死循环检查 (Infinite Loop Protection)

### 2.1 当前重试逻辑分析

**V151.2 SQL 查询**:
```sql
SELECT ... FROM matches_mapping
WHERE status = 'malformed'
  AND updated_at < NOW() - INTERVAL '1 hour'
```

**问题诊断**:
| 风险点 | 严重程度 | 描述 |
|--------|----------|------|
| ❌ 无重试次数上限 | 🔴 CRITICAL | 永久无数据记录会无限重试 |
| ❌ 无 abandoned 状态 | 🔴 CRITICAL | 无法标记"放弃采集"的记录 |
| ✅ 有时间窗口保护 | 🟢 MEDIUM | 1小时冷却期 |

### 2.2 无限重试场景模拟

```
场景: 某场比赛数据已从 OddsPortal 下线

Round 1: 14:00 采集失败 → status='malformed', updated_at=14:00
Round 2: 15:01 重试失败 → status='malformed', updated_at=15:01
Round 3: 16:02 重试失败 → status='malformed', updated_at=16:02
...
Round N: 永久循环 → 浪费代理额度 + 日志膨胀
```

### 2.3 推荐修复方案

**数据库 Schema 变更**:
```sql
-- 添加 retry_count 字段
ALTER TABLE matches_mapping
ADD COLUMN retry_count INTEGER DEFAULT 0;

-- 添加 status='abandoned' 状态
ALTER TYPE mapping_status ADD VALUE 'abandoned' AFTER 'malformed';
```

**修改 SQL 查询**:
```sql
SELECT ... FROM matches_mapping
WHERE (
    -- 未采集的比赛
    l2_raw_json IS NULL
    OR
    -- 可重试的 malformed 记录
    (status = 'malformed'
     AND updated_at < NOW() - INTERVAL '1 hour'
     AND retry_count < 3)  -- V151.3: 最多重试 3 次
  )
```

---

## 3. 并发收割建议 (Parallelization Strategy)

### 3.1 当前性能基线

**实际采集速度** (从日志分析):
```
平均耗时: 155-160s/场
包含延迟: 20-40s/场
```

**存量数据规模**:
```
英超: 1,868 场 (已复活，待补充哈希)
西甲: 1,900 场
意甲: 1,901 场
总计: 5,669 场

单线程预估: 5,669 × 160s = 907,040s ≈ 252 小时 ≈ 10.5 天
```

### 3.2 并发方案设计

#### 方案 A: 多进程 + 代理独占 (推荐)

```
架构:
  - 10 个独立进程 (ProcessPoolExecutor)
  - 每个进程绑定 1 个代理端口 (7890-7899)
  - 进程间通过数据库队列通信

优点:
  ✅ 代理池利用率 100%
  ✅ 进程隔离，单点故障不影响其他
  ✅ 无 GIL 限制

缺点:
  ⚠️ 资源消耗较大 (10 个浏览器实例)

预估性能提升:
  - 单进程: ~160s/场
  - 10 进程: ~16s/场 (理论上)
  - 实际: ~20-25s/场 (考虑协调开销)
  - 总耗时: 5,669 × 25s = 141,725s ≈ 39 小时

加速比: 10.5 天 → 1.6 天 (6.5x 提升)
```

#### 方案 B: 多进程 + 分批处理 (保守)

```
架构:
  - 3 个独立进程
  - 每个进程动态选择可用代理
  - 分批处理，每批 500 场

优点:
  ✅ 资源消耗适中
  ✅ 可控风险

预估性能:
  - 总耗时: ~85 小时
  - 加速比: 3x

建议使用场景:
  - 测试并发可行性
  - 代理池稳定性验证阶段
```

### 3.3 实现建议

**V151.3 并发收割器架构**:

```python
# scripts/ops/harvest_pinnacle_concurrent.py

from concurrent.futures import ProcessPoolExecutor
import multiprocessing as mp

PROXY_PORTS = list(range(7890, 7900))  # 10 个代理
BATCH_SIZE = 500
MAX_WORKERS = len(PROXY_PORTS)

def worker_process(proxy_port: int, match_batch: List[Dict]):
    \"\"\"
    独立进程，绑定单个代理
    \"\"\"
    # 设置环境变量
    os.environ['PROXY_PORT'] = str(proxy_port)

    # 独立数据库连接
    # 独立浏览器实例
    # 处理 match_batch

    return results

def main():
    # 从数据库获取待采集列表
    matches = fetch_pending_matches()

    # 分批
    batches = [matches[i:i+BATCH_SIZE]
               for i in range(0, len(matches), BATCH_SIZE)]

    # 启动进程池
    with ProcessPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = []
        for batch_idx, batch in enumerate(batches):
            proxy_port = PROXY_PORTS[batch_idx % MAX_WORKERS]
            future = executor.submit(worker_process, proxy_port, batch)
            futures.append(future)

        # 收集结果
        for future in as_completed(futures):
            result = future.result()
```

---

## 4. 风险评估与准入红线

### 4.1 搜索模式风险评估

| 风险类别 | 等级 | 缓解措施 |
|----------|------|----------|
| 代理 IP 封禁 | 🔴 HIGH | 分批执行 + 夜间窗口 |
| 成本过高 | 🟡 MEDIUM | 限制每日搜索上限 |
| 数据质量 | 🟢 LOW | 搜索置信度 0.7 |

### 4.2 并发收割风险评估

| 风险类别 | 等级 | 缓解措施 |
|----------|------|----------|
| 数据库连接池耗尽 | 🟡 MEDIUM | 每进程独立连接 |
| 内存溢出 | 🟡 MEDIUM | 限制并发数为 10 |
| 代理池竞争 | 🟢 LOW | 代理独占模式 |

---

## 5. 执行建议

### 5.1 短期行动 (1-2 天)

1. ✅ **禁止全量搜索** - 在证明安全前
2. 🔧 **修复无限重试** - 添加 retry_count 和 abandoned 状态
3. 🧪 **小规模搜索测试** - 50 场英超测试搜索稳定性

### 5.2 中期行动 (3-7 天)

1. 🚀 **实施方案 B** - 3 进程并发收割
2. 📊 **监控代理健康** - 每小时检查代理可用性
3. 📝 **完善审计日志** - 记录每场比赛的采集历史

### 5.3 长期行动 (1-2 周)

1. 🎯 **实施方案 A** - 10 进程全速收割
2. 🔄 **自动化调度** - 夜间窗口自动运行
3. 📈 **建立性能基线** - 持续优化采集速度

---

## 6. 准入红线检查清单

在开启西甲/意甲全量搜索前，必须确认：

- [ ] 搜索模式已通过 50 场测试（成功率 >80%）
- [ ] 代理池健康检查通过（10/10 可用）
- [ ] retry_count 字段已添加并生效
- [ ] abandoned 状态已实现
- [ ] 并发收割器已测试（3 进程 100 场验证）
- [ ] 夜间运行窗口已配置（00:00-06:00）
- [ ] 告警机制已配置（成功率 <50% 自动停止）

---

**审计结论**: 🔴 **禁止开启全量搜索，需先完成短期行动项**

**建议优先级**:
1. P0: 修复无限重试风险
2. P0: 50 场搜索测试
3. P1: 实现 3 进程并发
4. P2: 评估全量搜索可行性

Author: 高级数据运维架构师
Date: 2026-01-11
"""

if __name__ == "__main__":
    print(__doc__)
