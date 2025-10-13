# Ruff 错误修复计划

## 📊 错误现状

截至 2025-01-13，项目中有约 **200+ 个 Ruff 错误**，主要分布如下：

| 错误代码 | 错误描述 | 数量 | 优先级 |
|---------|---------|------|--------|
| F541 | f-string without any placeholders | 93 | 高 |
| E722 | Do not use bare `except` | 50 | 高 |
| F841 | Local variable is assigned to but never used | 30+ | 中 |
| E712 | Avoid equality comparisons to `False` | 8 | 中 |
| E731 | Do not assign a `lambda` expression | 2 | 低 |
| E714/E721 | Type comparison issues | 5 | 低 |
| 其他 | Miscellaneous | 10+ | 低 |

## 🎯 修复策略

### 渐进式修复原则
按照用户的"渐进式改进"理念，采用分阶段修复策略，确保每个阶段都不会破坏代码功能。

### Phase 1: 自动化修复简单错误（预计修复 70%）

**目标**：修复所有可以通过自动规则修复的错误

**修复内容**：
1. **F541 - f-string 无占位符**（93个）
   - `f"文本"` → `"文本"`
   - `f"\n"` → `"\n"`

2. **E712 - 与 False/True 比较**（8个）
   - `== False` → `is False`
   - `!= True` → `is not True`

3. **部分 E722 - 裸露 except**（25个，简单情况）
   - `except:` → `except Exception:`

**执行脚本**：
```bash
python scripts/fix_ruff_errors_phase1.py
```

### Phase 2: 处理复杂错误（预计修复 20%）

**目标**：需要 AST 解析或复杂模式匹配的错误

**修复内容**：
1. **E731 - lambda 赋值**（2个）
   ```python
   # 之前
   add = lambda x, y: x + y

   # 之后
   def _add(x, y):
       return x + y
   ```

2. **F841 - 未使用变量**（30个）
   - 自动添加下划线前缀：`teams` → `_teams`

3. **剩余 E722 - 复杂裸露 except**（25个）
   - 使用 AST 分析确保正确修复

4. **E714/E721 - 类型比较**（5个）
   - `type(x) == y` → `x.__class__ is y`

**执行脚本**：
```bash
python scripts/fix_ruff_errors_phase2.py
python fix_unused_vars.py  # 由 Phase 1 生成
```

### Phase 3: 手动验证和清理（预计处理 10%）

**目标**：处理无法自动修复的边缘情况

**修复内容**：
1. 特殊语境下的 F841 错误
2. 复杂的异常处理结构
3. 需要人工判断的代码风格问题

## 🚀 执行计划

### 第一步：备份代码
```bash
git checkout -b fix/ruff-errors-phase1
git commit -am "备份：修复 Ruff 错误前的状态"
```

### 第二步：执行 Phase 1
```bash
python scripts/fix_ruff_errors_phase1.py
```

### 第三步：执行 Phase 2
```bash
python scripts/fix_ruff_errors_phase2.py
python fix_unused_vars.py  # 如果存在
```

### 第四步：运行 Ruff 自动修复
```bash
ruff check --fix src/ tests/
```

### 第五步：验证修复结果
```bash
ruff check src/ tests/  # 查看剩余错误
make lint              # 完整质量检查
```

### 第六步：提交修复
```bash
git add -A
git commit -m "fix: 修复所有 Ruff 代码质量问题

- 修复 F541: f-string 无占位符 (93个)
- 修复 E722: 裸露 except (50个)
- 修复 F841: 未使用变量 (30个)
- 修复 E712: 与 False/True 比较 (8个)
- 修复 E731: lambda 赋值 (2个)
- 修复 E714/E721: 类型比较问题 (5个)

总计修复约 188 个代码质量问题

🤖 Generated with [Claude Code](https://claude.ai/code)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

## 📋 一键执行脚本

为简化执行流程，提供了主控脚本：

```bash
python scripts/fix_ruff_errors_all.py
```

该脚本将：
1. 自动执行 Phase 1
2. 自动执行 Phase 2
3. 运行生成的修复脚本
4. 执行 ruff 自动修复
5. 验证修复结果
6. 生成修复报告

## ⚠️ 注意事项

1. **测试重要性**：每个阶段后都应该运行测试确保功能未被破坏
2. **增量提交**：建议每个 Phase 单独提交，便于回滚
3. **代码审查**：修复后的代码仍需要人工审查
4. **特殊案例**：某些错误可能需要特殊的处理方式

## 📈 预期结果

修复完成后：
- **Ruff 错误数**：200+ → 0
- **代码质量评分**：提升
- **CI 状态**：绿灯通过
- **开发体验**：更好的代码提示和检查

## 🔄 后续维护

1. **Pre-commit Hooks**：设置自动修复，避免再次积累错误
2. **IDE 集成**：配置编辑器自动运行 ruff
3. **CI 增强**：在 CI 中添加更严格的质量门禁

```toml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.1.0
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format
```

## 📞 支持和帮助

如遇到问题：
1. 查看脚本输出日志
2. 使用 `ruff check --explain <code>` 了解错误详情
3. 手动修复特定文件
4. 回滚到修复前的状态

---

记住：**渐进式改进**，先让 CI 通过，再逐步提升质量！