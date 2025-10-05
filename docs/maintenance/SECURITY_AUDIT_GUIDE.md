# 🧩 安全审计运维手册 (Security Audit Maintenance Guide)

> **版本**: v1.0
> **适用项目**: FootballPrediction
> **最后更新**: 2025-01-04
> **维护团队**: FootballPrediction 开发团队

---

## 🎯 目标与原则

本手册旨在指导团队：
- 定期检测依赖安全漏洞
- 统一漏洞响应与修复流程
- 确保 CI 与人工审计机制协同
- 建立持续的安全防护体系

### 核心原则

1. **自动化优先** - 依赖安全审计主要通过 CI 自动执行
2. **快速响应** - 高危漏洞必须在 24 小时内响应
3. **透明可追溯** - 所有审计报告必须保存并可查询
4. **预防为主** - 通过定期审计防患于未然

---

## 🏗️ 安全审计体系结构

```
.github/workflows/
└─ DEPENDENCY_AUDIT_AUTOMATION.yml   # 自动执行审计
docs/_reports/security/
├─ pip_audit_YYYY-MM-DD_HH-MM-SS.md  # 审计报告
├─ archives/                         # 历史归档
│  └─ pip_audit_YYYY-MM-DD_HH-MM-SS.json
└─ README.md                         # 报告索引页
docs/maintenance/
├─ SECURITY_AUDIT_GUIDE.md           # 本手册
└─ DEPENDENCY_GUARDIAN_MAINTENANCE_GUIDE.md  # 依赖维护指南
```

### 工具链说明

- **pip-audit**: PyPA 官方依赖安全审计工具
- **GitHub Actions**: 自动化执行平台
- **Issue 自动告警**: 高危漏洞自动创建 Issue
- **Markdown 报告**: 人类可读的审计结果

---

## 📆 审计执行计划

| 类型 | 频率 | 触发方式 | 负责人 | 说明 |
|------|------|-----------|--------|------|
| **自动审计** | 每周一 17:00 (北京时间) | CI 定时任务 | 系统自动 | 无需人工干预 |
| **手动审计** | 任意时间 | `make audit` 或命令行 | 任意开发者 | 临时检查需求 |
| **PR 触发审计** | 依赖变更时 | GitHub PR | CI 自动 | 阻止有漏洞的依赖合并 |
| **紧急审计** | 发现 0-day 漏洞后 | 手动触发 | Tech Lead | 快速评估影响 |

### 审计覆盖率

- ✅ **生产依赖**: `requirements/base.lock`
- ✅ **开发依赖**: `requirements/dev.lock`
- ✅ **完整依赖**: `requirements/requirements.lock`
- ✅ **间接依赖**: 所有传递性依赖

---

## 🔎 手动执行安全审计

### 1️⃣ 环境准备

```bash
# 激活虚拟环境
source .venv/bin/activate

# 确保使用最新版本的 pip-audit
pip install --upgrade pip-audit[toml]
```

### 2️⃣ 执行扫描

#### 基础扫描（快速检查）
```bash
# 扫描基础依赖
pip-audit -r requirements/base.lock

# 扫描完整依赖
pip-audit -r requirements/requirements.lock
```

#### 生成正式报告
```bash
# 生成 Markdown 报告（推荐）
pip-audit -r requirements/requirements.lock \
  --format markdown \
  --output docs/_reports/security/pip_audit_manual.md

# 生成 JSON 报告（用于分析）
pip-audit -r requirements/requirements.lock \
  --format json \
  --output docs/_reports/security/archives/pip_audit_manual.json
```

#### 严格模式扫描
```bash
# 发现漏洞立即失败
pip-audit -r requirements/requirements.lock \
  --strict \
  --format markdown \
  --output docs/_reports/security/pip_audit_strict.md
```

### 3️⃣ 查看结果

```bash
# 查看最新报告
ls -la docs/_reports/security/pip_audit_*.md | tail -1

# 打开报告内容
cat docs/_reports/security/pip_audit_最新报告.md

# 搜索特定漏洞
grep -i "CRITICAL\|HIGH" docs/_reports/security/pip_audit_*.md
```

---

## ⚙️ 修复流程 (漏洞响应标准)

### 🚨 高危漏洞响应 (CRITICAL/HIGH)

**响应时间**: 24 小时内

```bash
# 1. 确认漏洞详情
pip-audit -r requirements/requirements.lock -v

# 2. 查找受影响的包
grep -B 2 -A 2 "CVE-YYYY-XXXX" 报告文件

# 3. 检查是否有安全版本
pip-audit -r requirements/requirements.lock --fix

# 4. 手动更新依赖
vim requirements/base.in
# 修改: package==x.y.z -> package==x.y.(z+1)

# 5. 重新生成锁定文件
make lock-deps

# 6. 验证修复
make verify-deps
pip-audit -r requirements/requirements.lock

# 7. 运行测试确保兼容性
make test-quick

# 8. 提交修复
git add requirements/
git commit -m "fix(security): upgrade vulnerable_package to x.y.(z+1)

- Fixes CVE-YYYY-XXXX (CRITICAL)
- Fixes CVE-YYYY-XXXX (HIGH)"
git push
```

### ⚡ 中危漏洞响应 (MEDIUM)

**响应时间**: 7 天内

```bash
# 评估影响
grep -B 1 -A 3 "MEDIUM" 报告文件

# 如果包未被实际使用，可以移除
# 检查是否在代码中使用
grep -r "package_name" src/ || echo "未使用，可移除"

# 移除依赖
vim requirements/base.in
# 删除或注释掉相应行

# 重新生成锁定文件
make lock-deps
```

### ℹ️ 低危漏洞响应 (LOW)

**响应时间**: 下个版本发布前

```bash
# 记录但不立即修复
echo "低危漏洞记录:" >> docs/_reports/security/low_vulnerabilities.log
echo "- CVE-YYYY-XXXX: package (LOW)" >> docs/_reports/security/low_vulnerabilities.log
```

---

## 📊 审计结果分级处理策略

| 风险级别 | 响应时限 | 处理动作 | 负责人 | 验证要求 |
|----------|----------|----------|--------|----------|
| **CRITICAL** | 24小时内 | 立即升级并验证 | Tech Lead | 完整回归测试 |
| **HIGH** | 3天内 | 优先修复并测试 | 维护者 | 核心功能测试 |
| **MEDIUM** | 一周内 | 可并入日常依赖更新 | 开发者 | 基础功能测试 |
| **LOW** | 按需 | 记录即可 | 任意 | 无需测试 |

### 修复优先级矩阵

```
高影响 + 高利用可能 = CRITICAL → 立即处理
高影响 + 低利用可能 = HIGH → 3天内
低影响 + 高利用可能 = MEDIUM → 一周内
低影响 + 低利用可能 = LOW → 下个版本
```

---

## 📈 报告留存与归档

### 报告生命周期

```
生成 → 存储 → 分析 → 归档 → 删除
  ↓      ↓      ↓      ↓      ↓
实时   90天   按需   1年    2年
```

### 报告管理规范

#### 1. 存储结构
```
docs/_reports/security/
├── current/                  # 当前年度报告
│   ├── 2025-01-06_09-00-00.md
│   └── 2025-01-13_09-00-00.md
├── archives/                 # 历史归档
│   ├── 2024/
│   └── 2023/
└── README.md                # 索引文件
```

#### 2. 归档规则

```bash
# 每月1号自动归档上月报告
mkdir -p docs/_reports/security/archives/$(date -d '1 month ago' +%Y)
mv docs/_reports/security/pip_audit_$(date -d '1 month ago' +%Y-%m)*.md \
   docs/_reports/security/archives/$(date -d '1 month ago' +%Y)/
```

#### 3. 汇总报告生成

创建 `scripts/generate_security_summary.sh`:

```bash
#!/bin/bash
# 生成月度安全汇总报告

month=$(date -d '1 month ago' +%Y-%m)
report_file="docs/_reports/security/SECURITY_SUMMARY_$month.md"

cat > "$report_file" << EOF
# 安全审计月度汇总 - $month

## 统计数据

- 总扫描次数: $(ls docs/_reports/security/pip_audit_$month*.md 2>/dev/null | wc -l)
- 发现漏洞总数: $(grep -h "CVE-" docs/_reports/security/pip_audit_$month*.md 2>/dev/null | wc -l)
- 修复漏洞数: $(git log --oneline --since="$month-01" --until="${month}-31" | grep -c "fix(security)")
- 未处理漏洞: $(grep -c "CVE-" docs/_reports/security/pip_audit_latest.md 2>/dev/null || echo 0)

## 漏洞趋势

[插入趋势图或表格]

## 处理建议

EOF

echo "月度汇总报告已生成: $report_file"
```

---

## 🔔 安全审计常见问题

| 问题 | 原因 | 解决方案 |
|------|------|----------|
| **CI 未生成报告** | 权限不足或 pip-audit 安装失败 | 检查 workflow 权限配置 |
| **报告空白** | 未检测到漏洞 | 属正常现象，无需处理 |
| **重复 Issue** | 多次触发审计 | 合并或关闭旧 Issue |
| **pip-audit 超时** | 网络不稳定 | 改为手动扫描并上传报告 |
| **误报漏洞** | CVE 数据库错误 | 在 Issue 中说明并标记误报 |
| **依赖无修复版本** | 厂商未发布修复 | 寻找替代方案或临时缓解措施 |

### 故障排查步骤

1. **检查 CI 日志**
   ```bash
   # GitHub Actions 页面查看详细日志
   # 关注错误信息和警告
   ```

2. **本地重现问题**
   ```bash
   # 使用相同环境重现
   docker run -it python:3.11 bash
   pip install pip-audit
   # 复制依赖文件并运行
   ```

3. **验证工具版本**
   ```bash
   pip-audit --version
   # 确保使用最新版本
   pip install --upgrade pip-audit
   ```

---

## 🛡️ 与其他安全工具集成

### Dependabot 集成

创建 `.github/dependabot.yml`:

```yaml
version: 2
updates:
  - package-ecosystem: "pip"
    directory: "/requirements"
    schedule:
      interval: "weekly"
      day: "monday"
      time: "10:00"
    open-pull-requests-limit: 5
    reviewers:
      - "security-team"
    commit-message:
      prefix: "chore"
      include: "scope"
    # 自动合并补丁版本
    auto-merge: true
    # 忽略某些包的更新
    ignore:
      - dependency-name: "package-with-known-issues"
        versions: ["x.y.z"]
```

### CodeQL 集成

添加到 `.github/workflows/`:

```yaml
name: CodeQL Security Analysis

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  analyze:
    runs-on: ubuntu-latest
    permissions:
      actions: read
      contents: read
      security-events: write
    strategy:
      matrix:
        language: [python]
    steps:
      - uses: actions/checkout@v4
      - uses: github/codeql-action/init@v3
        with:
          languages: ${{ matrix.language }}
      - uses: github/codeql-action/autobuild@v3
      - uses: github/codeql-action/analyze@v3
```

---

## 🧭 最佳实践与建议

### 日常实践

1. **定期检查**
   ```bash
   # 每周一查看自动审计报告
   # 每月生成安全汇总
   # 每季度评估整体安全态势
   ```

2. **依赖管理**
   ```bash
   # 保持最小依赖原则
   # 定期清理未使用的依赖
   # 优先使用活跃维护的包
   ```

3. **版本控制**
   ```bash
   # 始终锁定依赖版本
   # 使用语义化版本控制
   # 记录所有安全修复
   ```

### 团队协作

1. **角色分工**
   - **安全负责人**: 监督整体安全策略
   - **维护者**: 处理日常漏洞修复
   - **开发者**: 遵循安全开发规范
   - **测试者**: 验证安全修复

2. **沟通机制**
   - 高危漏洞立即通知全团队
   - 定期安全会议（月度）
   - 安全知识分享（季度）

3. **知识传承**
   - 记录所有漏洞处理过程
   - 建立安全知识库
   - 新人安全培训

### 持续改进

1. **指标监控**
   - 平均修复时间 (MTTR)
   - 漏洞发现率
   - 重复漏洞率

2. **流程优化**
   - 简化报告流程
   - 提高自动化程度
   - 减少人工干预

3. **工具升级**
   - 跟进 pip-audit 新功能
   - 评估新的安全工具
   - 集成更多检查点

---

## 🏁 结语

安全审计不是一次性工作，而是持续性防御机制。通过本手册指导的流程和工具，团队可以：

- **及时发现** 依赖中的安全漏洞
- **快速响应** 高危安全威胁
- **系统化管理** 依赖安全风险
- **持续改进** 安全防护能力

本体系与 **Dependency Guardian** 配合使用，可确保依赖安全、版本一致、风险可控，实现从"冲突防御"到"安全防御"的完整闭环。

记住：**安全是团队共同的责任**，每个人都应该在日常开发中保持安全意识！

---

## 📞 联系与支持

- **安全问题**: 创建 Issue 并标记 `security` 标签
- **紧急事件**: 直接联系 Tech Lead 或安全负责人
- **手册更新**: 提交 PR 改进本文档

---

*本文档最后更新：2025-01-04*
*下次审查日期：2025-04-04*
*维护负责人：项目安全团队*
