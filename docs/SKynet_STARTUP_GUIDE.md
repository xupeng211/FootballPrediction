# 天网计划启动指南 - CEO强制版

## 📋 概述

**CEO命令**: 强制修正脚本，启动真正的全域采集

**状态**: ✅ 所有准备工作已完成
- ✅ 强制重写脚本：数据库动态加载327个联赛
- ✅ 清理进度文件：确保从头开始
- ✅ 修复数据库连接：支持容器内和localhost
- ✅ 提供验证工具：完整的实时监控系统

---

## 🚀 启动命令

### 方法1：标准启动（推荐）

```bash
cd /home/user/projects/FootballPrediction

# 清理旧进度
rm -f logs/coverage_progress.json
rm -f logs/failed_leagues.log

# 启动脚本
nohup python scripts/launch_robust_coverage.py > logs/robust_coverage.log 2>&1 &

# 保存PID
echo $! > logs/skynet.pid

echo "✅ 天网计划已启动"
echo "🆔 进程ID: $(cat logs/skynet.pid)"
echo "📄 日志: logs/robust_coverage.log"
```

### 方法2：增强启动（带验证）

```bash
cd /home/user/projects/FootballPrediction

# 使用增强启动脚本
bash scripts/start_skynet_with_verification.sh
```

### 方法3：通过Docker容器启动

```bash
cd /home/user/projects/FootballPrediction

# 进入容器
make shell

# 在容器内启动
nohup python scripts/launch_robust_coverage.py > logs/robust_coverage.log 2>&1 &
```

---

## 🔍 实时验证

### 1. 预启动验证

检查数据库和联赛加载情况：

```bash
# 通过Docker容器运行验证
docker-compose exec -T app python scripts/verify_skynet_realtime.py
```

**期望结果**:
```
✅ 联赛数据: 数据库中有 327 个联赛，符合要求
⚠️  比赛数据: 已采集 6 场比赛，数据量较少 (预期)
⚠️  运行状态: 天网计划脚本未运行，需要启动
```

### 2. 启动后验证

#### 验证脚本是否加载联赛

```bash
# 查看启动日志
tail -f logs/robust_coverage.log

# 查找关键日志
grep "成功从数据库加载" logs/robust_coverage.log
```

**期望看到**:
```
🔍 正在从数据库加载联赛列表...
✅ 成功从数据库加载 327 个联赛
📊 联赛列表已保存到进度文件
```

#### 验证数据库连接

```bash
# 直接查询数据库
docker-compose exec -T db psql -U postgres -d football_prediction -c "
  SELECT
    COUNT(*) as total_leagues,
    COUNT(CASE WHEN fbref_url IS NOT NULL THEN 1 END) as leagues_with_url
  FROM leagues;
"
```

**期望结果**:
```
 total_leagues | leagues_with_url
---------------+------------------
           327 |              327
```

### 3. 实时监控数据流

#### 监控比赛数增长

```bash
# 持续监控比赛数量
watch -n 60 'docker-compose exec -T db psql -U postgres -d football_prediction -c "SELECT COUNT(*) FROM matches;"'

# 监控联赛采集进度
watch -n 60 'docker-compose exec -T db psql -U postgres -d football_prediction -c "SELECT COUNT(*) FROM matches WHERE data_source = \"fbref\";"'
```

#### 监控采集进度

```bash
# 查看进度文件
cat logs/coverage_progress.json | jq .

# 查看失败记录
cat logs/failed_leagues.log

# 实时查看采集日志
tail -f logs/robust_coverage.log | grep -E "(✅|❌|进度|⏳)"
```

---

## 📊 关键监控指标

### 1. 数据库层面

```sql
-- 联赛总数
SELECT COUNT(*) FROM leagues;
-- 预期: 327

-- 有FBref URL的联赛
SELECT COUNT(*) FROM leagues WHERE fbref_url IS NOT NULL;
-- 预期: 327

-- 总比赛数
SELECT COUNT(*) FROM matches;
-- 预期: 持续增长

-- FBref数据比赛数
SELECT COUNT(*) FROM matches WHERE data_source = 'fbref';
-- 预期: 持续增长
```

### 2. 进程层面

```bash
# 检查进程是否运行
ps aux | grep launch_robust_coverage

# 检查进程详细信息
cat logs/skynet.pid
ps -p $(cat logs/skynet.pid) -o pid,cmd,etime,pcpu,pmem
```

### 3. 日志层面

```bash
# 查看最近100行日志
tail -n 100 logs/robust_coverage.log

# 查找错误
grep -i error logs/robust_coverage.log

# 查找成功记录
grep -i "✅" logs/robust_coverage.log | tail -n 20
```

---

## ⚠️ 故障排除

### 问题1: 数据库连接失败

**症状**: 脚本启动后立即退出，日志显示连接失败

**解决方案**:
```bash
# 检查数据库是否运行
docker-compose ps | grep db

# 测试数据库连接
docker-compose exec -T db psql -U postgres -d football_prediction -c "SELECT 1;"

# 检查密码是否正确
grep POSTGRES_PASSWORD docker-compose.yml
```

### 问题2: 联赛加载失败

**症状**: 日志显示"❌ 无法从数据库加载联赛列表"

**解决方案**:
```bash
# 直接查询数据库验证数据
docker-compose exec -T db psql -U postgres -d football_prediction -c "
  SELECT COUNT(*) FROM leagues;
  SELECT name FROM leagues LIMIT 5;
"

# 检查权限
docker-compose exec -T db psql -U postgres -d football_prediction -c "
  GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO postgres;
"
```

### 问题3: 采集被反爬虫

**症状**: 大量403错误或被限制访问

**解决方案**:
- 脚本已经实现15-40秒随机延迟
- 已实现curl_cffi隐身模式
- 如需调整延迟，修改`_wait_between_requests()`方法

### 问题4: 进度卡住

**症状**: 长时间无新数据

**解决方案**:
```bash
# 查看当前处理进度
tail -n 50 logs/robust_coverage.log | grep "进度"

# 检查是否有失败记录
cat logs/failed_leagues.log

# 强制重启（保留进度）
kill $(cat logs/skynet.pid)
nohup python scripts/launch_robust_coverage.py > logs/robust_coverage.log 2>&1 &
```

---

## 🎯 成功标准

### 短期目标（启动后1小时）
- [ ] 脚本成功加载327个联赛
- [ ] 开始采集第一个联赛
- [ ] 数据库比赛数 > 10
- [ ] 无严重错误（403可接受）

### 中期目标（启动后24小时）
- [ ] 完成10+个联赛采集
- [ ] 数据库比赛数 > 500
- [ ] 成功率 > 80%
- [ ] 数据时效性更新（最新比赛日期 > 2025-08-18）

### 长期目标（启动后1周）
- [ ] 完成50+个联赛采集
- [ ] 数据库比赛数 > 5000
- [ ] 覆盖主要联赛（英超、西甲、德甲等）
- [ ] xG数据质量 > 90%

---

## 📞 紧急联系人

如遇到问题，按以下顺序处理：

1. **查看日志**: `tail -f logs/robust_coverage.log`
2. **运行验证**: `docker-compose exec -T app python scripts/verify_skynet_realtime.py`
3. **检查进程**: `ps aux | grep launch_robust`
4. **终止进程**: `kill $(cat logs/skynet.pid)` 或 `pkill -f launch_robust`
5. **重新启动**: 执行本指南的启动命令

---

## 📈 数据流验证

启动后30分钟，运行以下命令验证数据流：

```bash
# 1. 检查是否开始采集
echo "=== 检查是否开始采集 ==="
grep "正在采集联赛" logs/robust_coverage.log | tail -n 5

# 2. 检查数据库增长
echo "=== 检查数据库增长 ==="
docker-compose exec -T db psql -U postgres -d football_prediction -c "
  SELECT
    'Total Matches' as metric,
    COUNT(*) as count
  FROM matches
  UNION ALL
  SELECT
    'FBref Matches' as metric,
    COUNT(*) as count
  FROM matches
  WHERE data_source = 'fbref';
"

# 3. 检查采集进度
echo "=== 检查采集进度 ==="
grep "进度更新" logs/robust_coverage.log | tail -n 5

# 4. 检查是否有错误
echo "=== 检查错误 ==="
grep -i "error\|exception\|failed" logs/robust_coverage.log | tail -n 5
```

---

## 🏆 CEO验收标准

当以下条件全部满足时，向CEO汇报：

1. ✅ 脚本成功启动，无致命错误
2. ✅ 数据库中有327个联赛待采集
3. ✅ 开始采集第一个联赛
4. ✅ 实时日志显示采集进度
5. ✅ 数据库比赛数开始增长
6. ✅ 进度文件正常更新

**汇报格式**:
```
报告CEO：天网计划全域采集已启动
✅ 数据库联赛数: 327
✅ 当前状态: 采集中 (第X个联赛)
✅ 已采集比赛: Y场
✅ 成功率: Z%
⏰ 预计完成时间: T小时
```

---

**启动命令总结**:

```bash
cd /home/user/projects/FootballPrediction
rm -f logs/coverage_progress.json
nohup python scripts/launch_robust_coverage.py > logs/robust_coverage.log 2>&1 &
echo $! > logs/skynet.pid
tail -f logs/robust_coverage.log
```

🎉 **CEO命令执行完毕，数据洪水即将汹涌而来！**
