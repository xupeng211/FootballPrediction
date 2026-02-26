# V171 生产环境运行手册

> **版本**: V171.2.0 | **更新**: 2026-02-25 | **状态**: 生产就绪

---

## 每日操作 (1 分钟)

```bash
# 查看今日收割结果
npm run harvest:status

# 查看黄金名单
docker-compose exec db psql -U football_user -d football_db -c "
SELECT match_id, home_team, away_team, predicted_result,
       ROUND(final_confidence*100,1) as confidence
FROM predictions
WHERE prediction_date >= CURRENT_DATE
ORDER BY final_confidence DESC LIMIT 10"
```

---

## 启动/停止

```bash
# 启动 (后台)
nohup npm run scheduler > logs/scheduler.log 2>&1 &

# 停止
kill $(cat logs/scheduler.pid)

# 使用 PM2 (推荐)
pm2 start npm --name "v171-scheduler" -- run scheduler
pm2 logs v171-scheduler
pm2 stop v171-scheduler
```

---

## 告警检查

```bash
# 查看错误日志
cat logs/critical.log | grep $(date +%Y-%m-%d)

# 查看系统状态
docker-compose ps
```

---

## 快速命令

| 任务 | 命令 |
|------|------|
| 手动收割 10 场 | `npm run harvest:limit 10` |
| 提取 URL | `npm run extract-urls` |
| 查看日志 | `tail -f logs/scheduler.log` |
| 健康检查 | `curl http://localhost:8000/health` |

---

## 故障处理

| 问题 | 解决 |
|------|------|
| 代理熔断 | `docker-compose restart dev` |
| 数据库超时 | `docker-compose restart db` |
| 内存过高 | 重启调度器 |

---

**V171 - 静静收割，坐等收成** 🌾
