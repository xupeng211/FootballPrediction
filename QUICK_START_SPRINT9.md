# 🚀 Sprint 9 快速启动指南

**5分钟完成生产环境部署**

---

## ⚡ 一键启动（推荐）

```bash
# Step 1: 环境准备
cd /home/user/projects/FootballPrediction
chmod +x scripts/*.py

# Step 2: API配置
python scripts/setup_api_keys.py
# 输入你的FotMob API密钥

# Step 3: 一键部署
python scripts/deploy_production.py

# Step 4: 启动首周观察模式
python scripts/start_first_week.py

# Step 5: 验证部署
curl http://localhost:8000/health
```

**🎉 完成！** 访问 http://localhost:3000 查看监控面板

---

## 🔍 手动验证部署

```bash
# 检查服务状态
docker-compose ps

# 验证API健康
curl http://localhost:8000/health

# 检查监控服务
curl http://localhost:9090/-/healthy  # Prometheus
curl http://localhost:3000/api/health  # Grafana (admin/admin123)

# 验证外部API连接
python scripts/verify_live_connection.py
```

---

## 📊 关键信息

| 服务 | 地址 | 用途 |
|------|------|------|
| **主应用** | http://localhost:8000 | API服务和健康检查 |
| **Grafana监控** | http://localhost:3000 | 性能监控面板 |
| **Prometheus** | http://localhost:9090 | 指标收集 |
| **API文档** | http://localhost:8000/docs | 交互式API文档 |

---

## ⚙️ 首周安全配置

- **Kelly倍数**: 0.1x (极保守)
- **单日限额**: ¥10 (风险可控)
- **自动观察**: Brier Score偏离>15%自动切换
- **监控频率**: 5分钟实时检查

---

## 🚨 如果出现问题

```bash
# 查看日志
docker-compose logs -f app

# 重新部署
docker-compose down
docker-compose up -d

# 紧急停止
docker-compose down && docker-compose -f docker-compose.monitoring.yml down
```

---

## 📞 快速帮助

- **完整文档**: `docs/SPRINT9_OPERATIONS_MANUAL.md`
- **配置文件**: `.env.production`
- **日志位置**: `logs/`
- **监控地址**: http://localhost:3000

---

**🎯 首周目标**: 安全观察，数据收集，系统稳定性验证