# 废弃文件依赖引用报告
# Deprecated Files Dependency Issues Report

**检查时间**: 2025-12-08 23:42:00

以下文件包含对已废弃采集器的引用，需要用户手动处理：

---

## 🔴 需要立即处理的核心引用

### src/services/data_sync_service.py
```python
from src.collectors.match_collector import MatchCollector
```
**影响**: 可能导致服务启动失败
**建议**: 如果此服务仍在使用，请更新为使用FotMob采集器；如果不再需要，请移除

### src/tasks/data_collection_tasks.py
```python
def get_odds_collector(config):
    from src.data.collectors.odds_collector import OddsCollector
```
**影响**: 任务调度可能失败
**建议**: 如果odds功能仍需要，请重新实现基于FotMob的版本

---

## 🟡 验证和测试文件（可以暂时忽略）

### scripts/validate_async_migration.py
包含多个测试函数引用废弃文件：
- `test_football_data_collector()`
- `test_league_collector()`
- `test_match_collector()`

**影响**: 仅影响迁移验证，不影响生产运行
**建议**: 如果不再需要验证，可以删除此脚本

### src/data/collectors/ 目录下的文件
看起来是旧版本的数据采集器实现
**影响**: 如果未被导入，无影响
**建议**: 可以整个目录移除或归档

---

## ✅ 已修复的问题

### src/collectors/__init__.py
- ✅ 已移除对 `base_collector`、`football_data_collector`、`match_collector` 的引用
- ✅ 已更新为仅导出FotMob相关采集器和通用工具

---

## 🔧 推荐的修复优先级

1. **高优先级**: 修复 `src/services/data_sync_service.py` 和 `src/tasks/data_collection_tasks.py`
2. **中优先级**: 决定 `src/data/collectors/` 目录的用途
3. **低优先级**: 清理测试和验证文件

---

## 🚀 验证步骤

修复完成后，运行以下命令验证：
```bash
python -c "import src.collectors.fotmob_api_collector; print('✅ FotMob Collector OK')"
python -c "import src.collectors; print('✅ Collectors Module OK')"
```
