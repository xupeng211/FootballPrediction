# 🧩 TYPECHECK_MAINTENANCE_GUIDE.md
> 类型检查维护手册（MyPy 分层策略指引）

---

## 🧭 一、执行摘要

本项目采用 **分层类型防御体系（Layered Type Defense System）**：
- ✅ 核心模块：零错误（严格类型检查）
- ⚙️ 辅助模块：宽松检查（允许部分缺失）
- 💤 非核心模块：忽略检查（延后清理）

这种结构既保证了 **生产安全性**，又兼顾 **迭代效率**。

---

## ⚙️ 二、配置规范

### 1. 文件结构

| 文件 | 作用 |
|------|------|
| `mypy.ini` | 主配置文件（分层规则定义） |
| `Makefile` | 提供一键执行 `make typecheck` |
| `.github/workflows/ci-pipeline.yml` | 集成到 CI 流程 |
| `docs/TYPECHECK_MAINTENANCE_GUIDE.md` | 本维护手册 |

### 2. 检查命令分层

```bash
# 严格模式：核心逻辑必须零错误
mypy src/core src/services src/api --strict

# 宽松模式：辅助逻辑可容忍错误
mypy src/utils src/tasks src/monitoring || true
```

### 3. 忽略规则（见 mypy.ini）

```ini
exclude = (?x)(
    ^examples/|
    ^scripts/|
    _simple\.py$
)
```

---

## 🧩 三、核心维护原则

| 原则        | 说明                   |
| --------- | -------------------- |
| **零错误原则** | 核心模块必须保持 MyPy 全绿     |
| **渐进增强**  | 从内向外扩展类型覆盖率          |
| **可读性优先** | 类型注解清晰可读，不盲目复杂化      |
| **自动化防御** | 所有检查纳入 CI，禁止手动跳过核心错误 |
| **技术债跟踪** | 记录类型错误数量趋势，纳入质量指标    |

---

## 🔍 四、常见问题与修复策略

| 问题类型             | 示例                                           | 推荐处理方式                                              |
| ---------------- | -------------------------------------------- | --------------------------------------------------- |
| **缺少类型注解**       | `def func(x): ...`                           | 添加注解：`def func(x: int) -> None:`                    |
| **类型推断失败**       | "Incompatible types in assignment"           | 显式声明变量类型                                            |
| **导入类型缺失**       | "Cannot find implementation or library stub" | 使用 `# type: ignore` 或 `ignore_missing_imports=True` |
| **外部库无 stub 文件** | 第三方包报错                                       | 安装补丁包：`pip install types-requests` 等                |
| **Union 类型不兼容**  | "Item of type None not callable"             | 使用 `Optional[T]` 或显式判空                              |

---

## 🧱 五、持续改进路线图

| 阶段      | 目标                 | 说明                  |
| ------- | ------------------ | ------------------- |
| Phase 1 | 核心模块零错误            | 已完成                 |
| Phase 2 | 辅助模块补全类型           | 针对 utils/tasks 增强注解 |
| Phase 3 | 清理 examples/simple | 可延后处理               |
| Phase 4 | 启用全局 strict 模式     | 长期目标，类型全覆盖          |

---

## 🧠 六、辅助工具推荐

| 工具                | 功能               | 安装命令                        |
| ----------------- | ---------------- | --------------------------- |
| **mypy**          | 主类型检查工具          | `pip install mypy`          |
| **ruff**          | 快速静态检查 + 类型提示    | `pip install ruff`          |
| **pyright**       | VS Code 实时类型检查   | `npm install -g pyright`    |
| **mypy-protobuf** | 自动生成类型定义（如 gRPC） | `pip install mypy-protobuf` |

---

## 📈 七、CI 集成检查项

* 核心模块出错 → **阻断构建**
* 辅助模块出错 → 仅记录日志
* 报告输出到 `docs/_reports/TYPECHECK_REPORT.md`
* 可与测试覆盖率、lint 报告一同纳入质量仪表板

---

## 🧩 八、长期维护建议

1. 每次合并分支前执行：

   ```bash
   make typecheck
   ```
2. 每季度执行一次全面类型检查审计；
3. 若新模块添加到核心路径（如 `src/models`），请更新 mypy.ini；
4. CI 若出现类型警告，优先修复核心模块；
5. 未来可考虑开启：

   ```ini
   disallow_any_generics = True
   strict_concatenate = True
   ```

---

## 🧾 附录：诊断与修复命令

```bash
# 查看类型错误总数
mypy src | grep "error:" | wc -l

# 导出详细报告
mypy src --txt-report docs/_reports/mypy_report

# 仅检测核心模块
mypy src/core src/services src/api --strict

# 全项目扫描（不推荐在CI中使用）
mypy src
```

### 修复模板

```python
# 修复前
def calculate_stats(data):
    total = sum(data)
    return total

# 修复后
from typing import List, Union

def calculate_stats(data: List[Union[int, float]]) -> float:
    """计算统计数据"""
    total = sum(data)
    return total
```

### 忽略策略

```python
# 短期忽略（添加TODO注释）
result = complex_function()  # TODO: 添加类型注解

# 长期忽略（外部库问题）
import third_party_lib
value = third_party_lib.magic()  # type: ignore

# 模块级忽略（遗留代码）
# mypy: disable-error-code=no-untyped-def
```

---

## 📊 类型检查指标看板

| 指标                  | 当前值 | 目标值 | 状态   |
| ------------------- | ----- | ----- | ---- |
| 核心模块错误数        | 0     | 0     | ✅    |
| 辅助模块错误数        | 1480  | <500  | ⚠️   |
| 类型覆盖率            | 65%   | 85%   | 📈   |
| 新增代码类型注解率     | 80%   | 95%   | 📈   |
| CI 类型检查通过率     | 100%  | 100%  | ✅    |

---

## 🔄 版本更新日志

| 版本   | 日期       | 更新内容                     |
| ----- | --------- | -------------------------- |
| v1.0  | 2025-01-14 | 初始版本，建立分层类型检查体系      |
| v1.1  | TBD       | 计划：完善辅助模块类型注解         |
| v2.0  | TBD       | 计划：启用全局 strict 模式      |

---

**最后更新日期**：2025-01-14

**维护人**：类型防御小组（Type Defense Team）
