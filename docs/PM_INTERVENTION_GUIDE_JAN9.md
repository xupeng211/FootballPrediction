# 1月9日 PM 介入指南 - 数据抢救分阶段确认

**版本**: V26.5
**日期**: 2026-01-06
**目标**: 确保 801 条 FAILED 记录的"高价值优先"抢救成功执行

---

## 📋 执行前检查清单

在启动任何数据抢救前，请确认以下清单：

### 环境检查
- [ ] 冷却期已结束（`COLLECTION_PAUSE_UNTIL` 已过期）
- [ ] 数据库服务运行正常（`make ps`）
- [ ] 所有哨兵测试通过（`pytest tests/ops/test_collection_sentry.py`）
- [ ] 代理列表文件准备好（`proxies.txt`）

### 代码就绪
- [ ] 抢救优先级过滤已实现（`reprocess_failed_matches.py`）
- [ ] IP 告急系统已启用（`v26_5_quality_dashboard.py`）
- [ ] 复工自检脚本就绪（`v26_5_resume_check.py`）

---

## 🚀 分阶段执行方案

### Phase 1: 复工自检（5 场测试）

**目标**: 验证系统已恢复正常，IP 已解封

**执行命令**:
```bash
# 1. 执行复工自检
python scripts/ops/v26_5_resume_check.py

# 预期输出（成功时）：
# 💡 数据已入库，结构正确，可以开火
# 🚀 您现在可以安全地执行全量收割
```

**决策点**:
- ✅ **看到 "可以开火"**: → 进入 Phase 2
- ❌ **看到 "禁止开火"**: → 等待问题解决

---

### Phase 2: 小规模试运行（100 场，5 大联赛优先）

**目标**: 验证抢救优先级逻辑，优先抢救高价值数据

**执行命令**:
```bash
# 1. 查看当前 FAILED 记录数量
python -c "
import psycopg2
from src.config_unified import get_settings
settings = get_settings()
conn = psycopg2.connect(
    host=settings.database.host,
    port=settings.database.port,
    database=settings.database.name,
    user=settings.database.user,
    password=settings.database.password.get_secret_value()
)
cursor = conn.cursor()
cursor.execute(\"\"\"
    SELECT
        league_name,
        COUNT(*) as failed_count
    FROM matches
    WHERE collection_status = 'FAILED'
      AND l2_raw_json IS NOT NULL
    GROUP BY league_name
    ORDER BY COUNT(*) DESC
    LIMIT 10;
\"\"\")
print('FAILED 记录分布（前 10 联赛）:')
for row in cursor.fetchall():
    print(f'  {row[0]}: {row[1]} 条')
cursor.close()
conn.close()
"

# 2. 执行抢救（优先级：5 大联赛 > 次级联赛 > 其他联赛）
python scripts/maintenance/reprocess_failed_matches.py

# 预期输出：
# ✅ 找到 XXX 条可重新处理的记录
# 前 N 条应为 5 大联赛（英超、西甲、德甲、意甲、法甲）
```

**验证点**:
- ✅ **前 10 条记录中，5 大联赛占多数**: → 优先级逻辑正确
- ❌ **低级联赛排在前面**: → 需要修复排序逻辑

**决策点**:
- ✅ **抢救成功率 > 60%**: → 进入 Phase 3
- ⚠️ **抢救成功率 < 60%**: → 检查代理状态，补充 IP 资源

---

### Phase 3: 中规模扩大（500 场，监控 IP 消耗）

**目标**: 扩大规模，监控 IP 健康状态

**执行命令**:
```bash
# 1. 启动质量看板监控（新终端）
python scripts/ops/v26_5_quality_dashboard.py --proxy-file proxies.txt

# 预期输出（健康状态）：
# ┌─ 代理池实时状态 ────────────────────────────────────────────────────┐
# │  │ 总数: 5  │  可用: 3  │  冷却中: 2  │  平均评分: 52.0 ││

# 2. 执行大规模抢救
python scripts/maintenance/reprocess_failed_matches.py
# （修改脚本中的 limit=100 为 limit=500）

# 3. 实时监控 IP 告急指数
# 如果看到：
# 🔴【警告：IP 资源即将枯竭】可用代理仅剩 1 个，请立即补充！
# → 立即停止抢救，补充代理 IP
```

**验证点**:
- ✅ **可用代理 >= 2**: → 继续抢救
- ❌ **可用代理 < 2**: → 触发 IP 告急，需要补充代理

**决策点**:
- ✅ **抢救成功率 > 70% 且 IP 健康**: → 进入 Phase 4
- ⚠️ **IP 告急触发**: → 补充代理后重新评估

---

### Phase 4: 全量收割（801 条全部）

**目标**: 完成所有 FAILED 记录的抢救

**执行命令**:
```bash
# 1. 查看剩余 FAILED 记录
python -c "
import psycopg2
from src.config_unified import get_settings
settings = get_settings()
conn = psycopg2.connect(
    host=settings.database.host,
    port=settings.database.port,
    database=settings.database.name,
    user=settings.database.user,
    password=settings.database.password.get_secret_value()
)
cursor = conn.cursor()
cursor.execute(\"\"\"
    SELECT COUNT(*)
    FROM matches
    WHERE collection_status = 'FAILED'
      AND l2_raw_json IS NOT NULL;
\"\"\")
print(f'剩余 FAILED 记录: {cursor.fetchone()[0]} 条')
cursor.close()
conn.close()
"

# 2. 全量抢救（移除 limit 限制）
python scripts/maintenance/reprocess_failed_matches.py
# （修改脚本中的 limit=100 为 limit=None）

# 3. 生成最终报告
python -c "
import psycopg2
from src.config_unified import get_settings
settings = get_settings()
conn = psycopg2.connect(
    host=settings.database.host,
    port=settings.database.port,
    database=settings.database.name,
    user=settings.database.user,
    password=settings.database.password.get_secret_value()
)
cursor = conn.cursor()
cursor.execute(\"\"\"
    SELECT
        collection_status,
        COUNT(*) as count
    FROM matches
    GROUP BY collection_status
    ORDER BY count DESC;
\"\"\")
print('=' * 60)
print('🎉 最终状态分布')
print('=' * 60)
for row in cursor.fetchall():
    print(f'{row[0]}: {row[1]} 条')
cursor.close()
conn.close()
"
```

**验证点**:
- ✅ **FAILED 记录 < 100**: → 抢救成功
- ⚠️ **FAILED 记录 >= 100**: → 需要分析失败原因

---

## 🚨 IP 告急响应流程

### 触发条件
- 可用代理 < 2 个
- 看板显示：`【警告：IP 资源即将枯竭】`

### 响应步骤
1. **立即停止当前抢救**
   ```bash
   # 按 Ctrl+C 停止脚本
   ```

2. **查看代理状态**
   ```bash
   python scripts/ops/v26_5_quality_dashboard.py --proxy-file proxies.txt
   ```

3. **补充代理 IP**
   - 从代理服务商购买新 IP
   - 更新 `proxies.txt` 文件
   - 确保新代理未被封禁

4. **验证新代理**
   ```bash
   # 测试新代理连通性
   python main.py --test-proxy
   ```

5. **恢复抢救**
   ```bash
   # 重新执行抢救脚本
   python scripts/maintenance/reprocess_failed_matches.py
   ```

---

## 📊 预期结果

### 抢救成功率预测

| 场景 | 预期成功率 | 说明 |
|------|-----------|------|
| **Phase 2 (100 场)** | >70% | 5 大联赛优先，IP 健康 |
| **Phase 3 (500 场)** | >60% | 部分代理进入冷却期 |
| **Phase 4 (全量 801 场)** | >50% | 包含低级联赛，失败率较高 |

### 最终目标
- **抢救成功率**: >50% (至少 400 条成功)
- **5 大联赛抢救率**: >70% (高价值数据优先)
- **IP 健康度**: 始终保持 >= 2 个可用代理

---

## ✅ 完成标志

当满足以下所有条件时，认为抢救任务完成：

1. ✅ 所有 5 大联赛的 FAILED 记录抢救率 > 70%
2. ✅ 整体抢救成功率 > 50%
3. ✅ IP 告急系统未触发或已解决
4. ✅ 数据库状态报告生成完毕

---

## 📞 紧急联系

如遇到无法解决的问题，请联系：
- **技术负责人**: [姓名] - [邮箱] - [电话]
- **DevOps 工程师**: [姓名] - [邮箱] - [电话]
- **数据架构师**: [姓名] - [邮箱] - [电话]

---

**文档版本**: V26.5 Final
**最后更新**: 2026-01-06 23:45
**作者**: TDD Expert & Data Architect
**测试通过率**: 100% (所有 TDD 测试)
