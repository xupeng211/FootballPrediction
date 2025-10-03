# Legacy Quarantine

以下目录暂时隔离，不参与当前稳定化阶段的 lint、测试或打包流程：

- `docs/legacy/`
- `examples/`
- `notebooks/`
- `playground/`
- `tests/legacy/`

## 后续回收计划
1. 对隔离目录进行资产清点，梳理仍需维护的脚本或文档，形成优先级列表。
2. 为仍需保留的模块编写最小化回归测试或示例，并逐步移出隔离区。
3. 对确认淘汰的示例/脚本执行归档或删除，确保仓库体积可控。
4. 在完成回收后，更新 lint/测试配置，恢复对应目录的常规质量门禁。

> 注：该列表需在每个迭代评审时复盘，避免遗留区长期存在。

## Phase 7 更新（分类与清理）

- `tests/legacy/test_assertion_quality_examples.py`：文件内容严重损坏（符号替换、断裂的字符串），已从仓库移除，待后续重写后再纳入回归集。
- `tests/legacy/monitoring/`：仅保留空初始化文件，目录已移除，后续若需恢复需重新编写监控相关测试。
- `tests/legacy/slow/`：子目录仅含占位 `__init__.py`，目录已移除，后续视需要重建对应慢速用例。
- `tests/legacy/lineage/`：无测试内容，目录已移除，待后续确认是否需要新用例。
