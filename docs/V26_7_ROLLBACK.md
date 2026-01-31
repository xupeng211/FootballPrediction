# 🔄 V26.7 回滚方案 (Rollback Manual)

**版本**: V26.7
**创建日期**: 2026-01-07
**负责人**: 首席 DevOps 工程师
**状态**: ✅ 已验证

---

## 📋 执行摘要

本文档提供了 V26.7 合并到 main 分支后，如果出现系统异常的快速回滚步骤。

**回滚优先级**:
1. **P0 - 数据库回滚**（影响最大，需要优先处理）
2. **P1 - 代码版本回滚**（影响业务逻辑）
3. **P2 - 配置回滚**（环境变量和配置文件）

---

## 🚨 P0: 数据库回滚（最关键）

### 场景 1: 6000 维特征数据异常

**症状**:
- `matches.l2_extracted_features` 字段包含错误数据
- 特征维度不足或包含 NaN/Null
- 数据损坏导致预测失败

**回滚步骤**:

#### 1.1 快速验证数据异常

```bash
# 连接到数据库
docker-compose exec db psql -U football_user -d football_db

# 检查最近 10 场比赛的特征数据
SELECT
    match_id,
    jsonb_array_length(l2_extracted_features) as feature_count,
    l2_extracted_features ? 'adaptive_features' as has_adaptive
FROM matches
ORDER BY match_id DESC
LIMIT 10;
```

#### 1.2 创建数据快照（回滚前备份）

```bash
# 备份受影响的比赛数据
docker-compose exec db psql -U football_user -d football_db \
  -c "COPY (
    SELECT match_id, l2_extracted_features
    FROM matches
    WHERE match_id >= 4813569  -- V26.7 第一场比赛 ID
  ) TO '/tmp/v26_7_backup.csv' WITH CSV;"

# 导出快照到宿主机
docker-compose exec db cat /tmp/v26_7_backup.csv > backup/v26_7_data_$(date +%Y%m%d_%H%M%S).csv
```

#### 1.3 恢复到 V26.6 状态（清空 V26.7 数据）

```bash
# 方案 A: 如果有备份，从备份恢复
docker-compose exec db psql -U football_user -d football_db \
  -c "DELETE FROM matches WHERE match_id >= 4813569;"

# 方案 B: 重置 l2_extracted_features 字段（如果只想重置特征）
docker-compose exec db psql -U football_user -d football_db \
  -c "UPDATE matches SET l2_extracted_features = NULL WHERE match_id >= 4813569;"
```

#### 1.4 验证数据恢复

```bash
# 确认数据已清理
docker-compose exec db psql -U football_user -d football_db \
  -c "SELECT COUNT(*) FROM matches WHERE match_id >= 4813569;"

# 预期结果: 0（如果使用方案 A）或 NULL（如果使用方案 B）
```

---

### 场景 2: 代理轮换机制失效

**症状**:
- 所有代理连接失败
- IP 被封禁，无法进行数据采集
- 9/10 端口不可用

**回滚步骤**:

#### 2.1 检查代理池状态

```bash
# 运行代理健康测试
pytest tests/ops/test_proxy_health.py -v

# 预期结果: test_at_least_one_proxy_working 通过
```

#### 2.2 恢复到单代理模式（临时）

```bash
# 编辑 proxies.txt，只保留一个可用代理
echo "http://172.25.16.1:7891" > proxies.txt

# 或者禁用代理（直连模式）
export NO_PROXY=true
```

#### 2.3 重启采集服务

```bash
# 重启收割服务
docker-compose restart pipeline_worker

# 验证代理恢复
python main.py --test-proxy
```

---

## 📦 P1: 代码版本回滚

### 场景 1: Git 版本回滚

**症状**:
- 代码逻辑错误导致系统崩溃
- 功能异常或性能严重下降
- 测试失败率 > 10%

**回滚步骤**:

#### 1.1 快速回滚到上一个版本

```bash
# 查看 V26.7 之前的提交
git log --oneline -10

# 回滚到 V26.6（假设是 commit_hash）
git reset --hard <commit_hash>

# 或者使用 revert（保留历史）
git revert HEAD

# 强制推送到远程（谨慎使用！）
git push origin main --force
```

#### 1.2 回滚特定文件（如果只需要回滚部分代码）

```bash
# 查看特定文件的修改
git diff HEAD~1 src/api/collectors/fotmob_core.py

# 回滚单个文件
git checkout HEAD~1 -- src/api/collectors/fotmob_core.py

# 提交回滚
git add src/api/collectors/fotmob_core.py
git commit -m "回滚: V26.7 fotmob_core.py 到 V26.6 版本"
```

#### 1.3 验证代码回滚

```bash
# 运行全量测试
pytest tests/ -v --tb=short

# 预期结果: 100% 通过（或回到 V26.6 的通过率）
```

---

### 场景 2: Docker 容器回滚

**症状**:
- 容器无法启动
- 容器频繁崩溃
- 容器内代码版本错误

**回滚步骤**:

#### 2.1 重建容器（使用旧代码）

```bash
# 停止所有容器
docker-compose down

# 清理容器和镜像（谨慎！）
docker-compose rm -f
docker rmi footballprediction_app

# 重新构建（会使用当前代码）
docker-compose build --no-cache

# 启动服务
docker-compose up -d
```

#### 2.2 回滚到特定 Docker 镜像

```bash
# 查看可用镜像
docker images | grep footballprediction

# 回滚到旧镜像
docker tag footballprediction_app:<old_tag> footballprediction_app:latest

# 重启容器
docker-compose up -d
```

---

## ⚙️ P2: 配置回滚

### 场景 1: 环境变量配置错误

**症状**:
- 应用无法连接数据库
- 代理配置错误
- 端口冲突

**回滚步骤**:

#### 1.1 检查环境变量

```bash
# 查看当前环境变量
docker-compose exec app env | grep -E "(DB_|PROXY_|PORT_)"

# 对比 .env.example
diff .env .env.example
```

#### 1.2 恢复默认配置

```bash
# 从 .env.example 重新创建 .env
cp .env.example .env

# 编辑关键配置
vim .env

# 重启服务
docker-compose restart
```

---

## 🔍 回滚验证清单

回滚完成后，必须执行以下验证步骤：

### 1. 数据库验证

- [ ] `matches` 表数据完整性
- [ ] `l2_extracted_features` 字段格式正确
- [ ] 没有新增的异常数据

### 2. 代码验证

- [ ] Git 版本正确
- [ ] 全量测试通过率 ≥ 95%
- [ ] 关键功能测试通过

### 3. 服务验证

- [ ] Docker 容器全部运行正常
- [ ] API 服务响应正常
- [ ] 数据采集功能正常

### 4. 性能验证

- [ ] 内存占用稳定（无泄漏）
- [ ] CPU 使用率正常
- [ ] 响应时间在可接受范围

---

## 📞 紧急联系

**如果回滚失败或出现其他问题，请联系**:

- **技术负责人**: [待填写]
- **DevOps 团队**: [待填写]
- **DBA 团队**: [待填写]

---

## 📚 附录

### A. 常用回滚命令速查

```bash
# Git 回滚
git reset --hard HEAD~1                    # 回滚 1 个提交
git revert HEAD                            # 撤销最新提交（保留历史）
git checkout <branch> -- <file>            # 从其他分支恢复文件

# 数据库回滚
docker-compose exec db psql -c "SELECT version();"  # 查看数据库版本
pg_dump football_db > backup.sql           # 备份数据库
psql football_db < backup.sql              # 恢复数据库

# Docker 回滚
docker-compose down                        # 停止所有服务
docker-compose up -d --force-recreate      # 强制重建容器
docker system prune -f                     # 清理未使用资源
```

### B. V26.7 关键变更记录

| 文件 | 变更类型 | 风险等级 | 回滚影响 |
|------|---------|---------|---------|
| `src/api/collectors/fotmob_core.py` | 日志净化 | 低 | 低 |
| `tests/unit/core/test_circuit_breaker.py` | 测试隔离 | 低 | 无 |
| `.gitignore` | 安全加固 | 低 | 无 |
| `CHANGELOG.md` | 文档更新 | 无 | 无 |
| `README.md` | 版本升级 | 无 | 无 |

---

**文档版本**: 1.0
**最后更新**: 2026-01-07
**审核状态**: ✅ 待审核
