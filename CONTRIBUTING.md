# Contributing Guidelines

感谢为本项目做出贡献！  
为确保文档长期健康，请遵循以下规范：

## 📚 文档规范

1. **必须通过 Docs Guard 检查**
   - 本地执行：
     ```bash
     make docs.check
     ```
   - CI 会自动运行相同检查，未通过将无法合并 PR。

2. **文档目录结构**
   - 只允许以下顶层目录：
     `architecture/`, `how-to/`, `reference/`, `testing/`, `data/`, `ml/`, `ops/`, `release/`, `staging/`, `legacy/`, `_reports/`, `_meta/`
   - 其他目录会被自动拒绝。

3. **孤儿文档处理**
   - 所有新文档必须添加到 `INDEX.md` 或在现有文档中有引用。
   - 否则会被 Docs Guard 报告为孤儿。

4. **坏链防护**
   - 外部链接可用 `http(s)`。
   - 内部相对链接必须指向实际存在文件。

5. **归档策略**
   - 过时或历史文档请放入 `legacy/`。

---

✅ 按照以上规范提交文档，CI 会保持文档长期高质量。
