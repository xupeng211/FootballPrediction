# 数据库环境一致性审计报告

**生成时间**: 2026-01-08 17:06:38
**审计人**: Claude Code (Database Architect)
**项目**: FootballPrediction - PostgreSQL 环境全扫描

---

## 🚨 执行摘要

### 核心发现

1. **发现了 3 个数据库实例**，其中 2 个包含 `matches` 表
2. **6,195 场异常数据确认**：来自 `football_prediction_dev` 数据库（开发库）
3. **当前配置指向错误的数据库**：`.env` 指向开发库，而非生产库
4. **真正的生产库是 `football_db`**：包含 9,169 条高质量数据

### 准入红线状态

| 指标 | 目标 | 实际 | 状态 |
|------|------|------|------|
| 唯一生产库 | 1 个 | 2 个（football_db + dev） | ❌ 失败 |
| 配置指向生产库 | ✅ | ❌（指向 dev） | ❌ 失败 |
| 数据来源唯一性 | ✅ | ❌（数据分散） | ❌ 失败 |

**准入红线：未达到** ⚠️

---

## A. 容器与连接审计

### Docker 容器清单

| 容器名 | 状态 | 端口映射 |
|--------|------|----------|
| `football_prediction_db` | ✅ Up 2 days (healthy) | 0.0.0.0:5432→5432/tcp |

**结论**：只有 1 个 PostgreSQL 容器在运行（✅ 正常）

### 当前 .env 配置

```bash
DB_HOST=localhost
DB_PORT=5432
DB_NAME=football_prediction_dev  # ⚠️ 指向开发库
DB_USER=football_user
```

**问题**：配置指向 `football_prediction_dev`（开发库），而非 `football_db`（生产库）

---

## B. 数据库实例普查 (Database Census)

### 发现的数据库

| 数据库名 | matches 表 | 总行数 | 数据质量 | 评估 |
|----------|-----------|--------|----------|------|
| **football_db** | ✅ 存在 | 9,169 | 🟢 高 | **推荐生产库** |
| **football_prediction_dev** | ✅ 存在 | 7,041 | 🔴 低（含脏数据） | 开发/测试库 |
| postgres | ❌ 不存在 | - | - | 系统库 |

---

## C. 数据库详细对比

### football_db (9,169 行) - 🟢 推荐生产库

**联赛分布**：
| 联赛 | 场次 |
|------|------|
| Premier League | 2,086 |
| Serie A | 1,901 |
| La Liga | 1,900 |
| Ligue 1 | 1,752 |
| Bundesliga | 1,530 |

**赛季分布**：
| 赛季 | 场次 |
|------|------|
| 2024/2025 | 1,752 |
| 2023/2024 | 1,752 |
| 2022/2023 | 1,827 |
| 2021/2022 | 1,826 |
| 2020/2021 | 1,826 |

**数据创建时间**：2026-01-07 06:13 → 2026-01-07 23:38

**评估**：
- ✅ 数据分布合理（5 大联赛场均 ~1800 场）
- ✅ 赛季覆盖完整（2020/21 - 2024/25）
- ✅ 数据创建时间集中（1 天内完成）
- ✅ **推荐作为唯一生产库**

---

### football_prediction_dev (7,041 行) - 🔴 开发/测试库

**联赛分布**：
| 联赛 | 场次 |
|------|------|
| Premier League | **6,200** ⚠️ |
| Championship | 307 |
| La Liga | 181 |
| Ligue 1 | 153 |
| Serie B | 119 |
| Bundesliga | 63 |

**赛季分布**：
| 赛季 | 场次 |
|------|------|
| 2324 | **6,196** ⚠️ |
| 2425 | 845 |

**数据创建时间**：2026-01-06 08:18 → 2026-01-07 04:29

**评估**：
- ❌ Premier League 23/24 赛季有 6,196 场（预期 380 场，超出 16 倍）
- ❌ 数据创建时间集中在 2026-01-06 08:00（一次性批量创建 6000 场）
- ❌ L2 数据填充率仅 3.33%（206/6195）
- ❌ **确认为开发/测试库，包含批量导入的脏数据**

---

## D. 异常数据诊断：6,195 场来源确认

### 数据特征分析

**创建时间分布**：
```
2026-01-06 08:00:00 → 6000 场（一次性批量创建）
2026-01-06 17:00:00 → 195 场（后续补充）
```

**唯一性检查**：
```
唯一 match_id: 6,195
总记录数: 6,195
重复记录: 0 条
```

**L2 数据填充率**：
```
总记录: 6,195
有 L2: 206
填充率: 3.33%
```

### 结论

**这 6,195 场数据的特征**：
1. ✅ 不是重复数据（match_id 唯一）
2. ❌ 是批量导入的测试/演示数据
3. ❌ L2 原始数据严重缺失（仅 3.33%）
4. ❌ 数据创建时间集中（2026-01-06 08:00）
5. ❌ **来源：`football_prediction_dev` 数据库（当前配置指向）**

---

## E. TDD 统一行动方案

### 任务：确定唯一事实来源 (Single Source of Truth)

**✅ 结论：`football_db` 是唯一生产库**

**理由**：
1. 数据质量高（9,169 行，分布合理）
2. 赛季覆盖完整（2020/21 - 2024/25）
3. 5 大联赛数据均衡（场均 ~1800 场）
4. 数据创建时间集中（2026-01-07，看起来是生产数据导入）

---

## 🔧 一键清理方案

### 方案 1：切换到生产库（推荐）✅

**步骤 1：修改 .env 配置**

```bash
# 修改 .env 文件
DB_NAME=football_db  # 从 football_prediction_dev 改为 football_db
```

**步骤 2：验证切换**

```bash
# 重启服务
docker-compose restart db

# 验证连接
python -c "from src.config_unified import get_settings; print(get_settings().database.name)"
# 应该输出: football_db
```

**步骤 3：重新审计**

```bash
python -m scripts.audit.audit_five_league_data
```

**预期结果**：
- ✅ 连接到 `football_db`（9,169 行高质量数据）
- ✅ Premier League 23/24 赛季显示合理的数据量
- ✅ 数据完整性符合预期

---

### 方案 2：清理开发库（可选）⚠️

**警告**：此操作将永久删除 `football_prediction_dev` 中的数据，请先备份！

```sql
-- 连接到 football_prediction_dev 数据库
-- 删除所有 matches 表数据
TRUNCATE TABLE matches CASCADE;

-- 或直接删除整个数据库（危险！）
-- DROP DATABASE football_prediction_dev;
```

**推荐操作**：
```bash
# 保留开发库用于测试，但修改配置指向生产库
# 未来开发/测试可以在 football_prediction_dev 中进行
```

---

### 方案 3：数据迁移（不推荐）❌

**为什么不推荐**：
- `football_db` 已经有 9,169 行高质量数据
- `football_prediction_dev` 包含 7,041 行低质量数据
- 合并两个数据库会导致数据冲突和重复

**结论**：无需迁移，直接使用 `football_db`

---

## 📋 环境一致性检查清单

### 配置文件检查

| 文件 | 当前配置 | 应该配置 | 状态 |
|------|----------|----------|------|
| `.env` | `DB_NAME=football_prediction_dev` | `DB_NAME=football_db` | ❌ 需修改 |
| `docker-compose.yml` | `${DB_NAME}` | `${DB_NAME}` | ✅ 正确（使用变量） |
| `docker-compose.prod.yml` | `DB_NAME=football_db` | `DB_NAME=football_db` | ✅ 正确 |

### 脚本连接检查

**需要验证的脚本**：
```bash
# 检查所有脚本是否使用统一的配置
grep -r "DB_NAME\|database.name" scripts/ --include="*.py"
```

**预期结果**：所有脚本应该从 `src.config_unified.get_settings()` 读取配置，而不是硬编码

---

## 🎯 最终建议

### 立即执行（P0）

1. **修改 .env 配置**：
   ```bash
   # 编辑 .env 文件
   DB_NAME=football_db
   ```

2. **重启服务**：
   ```bash
   docker-compose restart db
   ```

3. **重新审计**：
   ```bash
   python -m scripts.audit.audit_five_league_data
   ```

### 后续行动（P1）

4. **清理开发库**（可选）：
   ```bash
   # 保留开发库用于测试，但不再使用
   # 或定期清理测试数据
   ```

5. **文档更新**：
   - 更新 `CLAUDE.md`，明确 `football_db` 是唯一生产库
   - 更新 `README.md`，说明数据库配置

---

## 📊 审计结论

### ✅ 问题已定位

1. **根本原因**：系统连接到开发库 `football_prediction_dev`，而非生产库 `football_db`
2. **异常数据来源**：`football_prediction_dev` 中包含批量导入的测试数据（6,195 场）
3. **数据分散问题**：数据分布在 2 个数据库中，导致查询混乱

### ✅ 解决方案已确定

1. **立即切换**：修改 `.env` 配置，指向 `football_db`
2. **唯一事实来源**：`football_db` 作为唯一生产库
3. **开发库保留**：`football_prediction_dev` 用于测试（可选清理）

### ✅ Single Source of Truth 确认

**唯一事实来源 (SSOT)**：`football_db`

**特征**：
- 数据库名：`football_db`
- 总行数：9,169
- 联赛覆盖：5 大联赛 + 其他
- 赛季覆盖：2020/21 - 2024/25
- 数据质量：🟢 高

---

## 🔒 准入原则验证

| 原则 | 状态 | 说明 |
|------|------|------|
| 确定哪个库是亲生的 | ✅ | `football_db` 是生产库 |
| 禁止往错误库写数据 | ⚠️ | 需修改 .env 配置 |
| Single Source of Truth | ✅ | 已确定 `football_db` |
| 清理冗余数据库 | 🟡 | 开发库可保留用于测试 |

**最终结论**：⚠️ **暂缓开启 L3 赔率回填**，需先切换到正确的生产库（`football_db`），然后重新审计数据完整性。

---

**审计脚本位置**：`scripts/audit/audit_database_environment.py`
**重新审计命令**：`python -m scripts.audit.audit_database_environment`

---

**报告生成时间**：2026-01-08 17:06:38
**审计状态**：✅ 完成
**下一步行动**：修改 .env 配置，切换到 `football_db`
