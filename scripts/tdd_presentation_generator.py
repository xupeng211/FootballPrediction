#!/usr/bin/env python3
"""TDD分享会演示文稿生成器
快速生成Markdown格式的演示文稿，支持不同主题
"""

import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

class TDDPresentationGenerator:
    """TDD演示文稿生成器"""

    def __init__(self):
        self.templates_dir = Path("docs/tdd_presentations")
        self.templates_dir.mkdir(parents=True, exist_ok=True)

    def generate_presentation(self, topic: str, presenter: str, date: str,
                            template_type: str = "standard") -> str:
        """生成演示文稿"""

        if template_type == "standard":
            return self._generate_standard_presentation(topic, presenter, date)
        elif template_type == "case_study":
            return self._generate_case_study(topic, presenter, date)
        elif template_type == "workshop":
            return self._generate_workshop(topic, presenter, date)
        else:
            raise ValueError(f"未知的模板类型: {template_type}")

    def _generate_standard_presentation(self, topic: str, presenter: str, date: str) -> str:
        """生成标准演示文稿"""
        content = f"""# TDD经验分享会：{topic}

**分享人**：{presenter}
**日期**：{date}
**时长**：15-20分钟

---

## 📋 目录

1. 背景介绍
2. 核心概念
3. 实践案例
4. 常见问题
5. 总结与建议

---

## 1. 背景介绍

### 为什么选择这个主题？

<!-- 在这里添加背景信息 -->
-
-
-

### 学习目标

<!-- 在这里添加学习目标 -->
-
-
-

---

## 2. 核心概念

### 主要知识点

<!-- 在这里添加主要概念 -->

**概念1：**
- 说明：
- 示例：
```python
# 代码示例
def example():
    pass
```

**概念2：**
- 说明：
- 示例：
```python
# 代码示例
def example():
    pass
```

---

## 3. 实践案例

### 案例1：问题描述

<!-- 在这里描述实际问题 -->

### 解决方案

<!-- 在这里描述解决方案 -->

#### 步骤1：Red（失败的测试）
```python
def test_feature():
    # 测试代码
    pass
```

#### 步骤2：Green（最小实现）
```python
def feature():
    # 实现代码
    pass
```

#### 步骤3：Refactor（重构优化）
```python
def feature():
    # 优化后的代码
    pass
```

### 案例2：进阶应用

<!-- 在这里添加第二个案例 -->

---

## 4. 常见问题

### 问题1：测试写起来很慢

**解决方案**：
-
-
-

### 问题2：不知道如何测试遗留代码

**解决方案**：
-
-
-

### 问题3：测试覆盖率很高但质量不高

**解决方案**：
-
-
-

---

## 5. 总结与建议

### 关键要点

1.
2.
3.

### 最佳实践

1.
2.
3.

### 推荐资源

- 📖 [书籍推荐]()
- 📹 [视频教程]()
- 🔗 [在线文档]()

---

## 🎯 互动讨论

### 思考题

1. 在你的项目中，如何应用今天学到的知识？
2. 遇到的最大挑战是什么？
3. 有什么好的实践愿意分享？

---

## ✨ Thank You!

**Q&A**

欢迎提问和讨论！
"""
        return content

    def _generate_case_study(self, topic: str, presenter: str, date: str) -> str:
        """生成案例研究演示文稿"""
        content = f"""# TDD案例研究：{topic}

**分享人**：{presenter}
**日期**：{date}
**类型**：案例研究

---

## 📖 案例背景

### 项目概述

<!-- 描述项目背景 -->

### 遇到的挑战

<!-- 描述遇到的TDD相关挑战 -->

---

## 🔍 问题分析

### 初始状态

- 测试覆盖率：
- 测试质量：
- 开发效率：

### 根本原因

<!-- 分析根本原因 -->

---

## 💡 解决方案

### 实施策略

<!-- 详细描述解决方案 -->

### 具体步骤

1.
2.
3.

---

## 📊 实施过程

### 第一阶段：准备

-
-
-

### 第二阶段：实施

-
-
-

### 第三阶段：优化

-
-
-

---

## 📈 结果展示

### 改进前后对比

| 指标 | 改进前 | 改进后 | 提升 |
|------|--------|--------|------|
| 覆盖率 |  |  |  |
| Bug数量 |  |  |  |
| 开发速度 |  |  |  |

### 经验教训

<!-- 总结经验教训 -->

---

## 🎯 可复用的模式

### 模式1：

<!-- 描述可复用的模式 -->

### 模式2：

<!-- 描述可复用的模式 -->

---

## 💬 交流讨论

### 讨论要点

1. 这个案例对你的项目有什么启发？
2. 如何将这些经验应用到实际工作中？
3. 有什么不同的看法或建议？

---

## ✨ Thank You!

**案例研究结束**
"""
        return content

    def _generate_workshop(self, topic: str, presenter: str, date: str) -> str:
        """生成工作坊演示文稿"""
        content = f"""# TDD实践工作坊：{topic}

**带领人**：{presenter}
**日期**：{date}
**时长**：60分钟

---

## 🎯 工作坊目标

通过动手实践，掌握：
1.
2.
3.

---

## ⚡ 快速回顾（10分钟）

### TDD核心循环

1. **Red** - 写一个失败的测试
2. **Green** - 让测试通过
3. **Refactor** - 重构代码

### 关键原则

- 测试先行
- 小步快跑
- 持续重构

---

## 🛠️ 实践任务（40分钟）

### 任务1：简单功能实现（15分钟）

**需求**：
<!-- 描述任务需求 -->

**步骤**：
1. 先写测试
2. 实现功能
3. 重构优化

**代码模板**：
```python
# 在这里编写代码
def solution():
    pass
```

### 任务2：边界情况处理（15分钟）

**需求**：
<!-- 描述任务需求 -->

### 任务3：重构优化（10分钟）

**目标**：
<!-- 描述优化目标 -->

---

## 👥 小组讨论（10分钟）

### 讨论要点

1. 遇到了哪些困难？
2. 有什么发现和感悟？
3. 如何应用到实际项目？

---

## 📝 成果展示

### 小组分享

每个小组展示：
- 解决方案
- 遇到的问题
- 学到的经验

---

## 🎉 总结

### 关键收获

1.
2.
3.

### 后续行动

-
-
-

---

## ✨ Thank You!

继续TDD之旅！
"""
        return content

    def save_presentation(self, content: str, filename: str) -> Path:
        """保存演示文稿"""
        file_path = self.templates_dir / filename
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return file_path

    def create_agenda_template(self, date: str) -> str:
        """创建会议议程模板"""
        content = f"""# TDD分享会议程 - {date}

## 时间安排

| 时间 | 内容 | 负责人 |
|------|------|--------|
| 16:00-16:05 | 开场 & 暖场 | 主持人 |
| 16:05-16:10 | TDD小贴士分享 | 志愿者 |
| 16:10-16:15 | 覆盖率报告 | QA |
| 16:15-16:35 | 主题分享 | 主讲人 |
| 16:35-16:45 | 自由讨论 | 全体 |
| 16:45-16:50 | 总结 & 行动项 | 主持人 |

## 本周主题分享

**主题**：待定
**分享人**：待定

## 上周行动项跟进

- [ ]
- [ ]
- [ ]

## 本周收集的问题

1.
2.
3.

## 下周安排

**主题预告**：待定
**分享人**：待定

---

*请提前准备，谢谢配合！*
"""
        return content

def main():
    """主函数 - 演示生成器使用"""
    generator = TDDPresentationGenerator()

    print("🚀 TDD演示文稿生成器")
    print("=" * 50)

    # 示例：生成标准演示文稿
    topic = "Mock与Stub在测试中的艺术"
    presenter = "张三"
    date = datetime.now().strftime("%Y-%m-%d")

    print(f"\n📝 生成演示文稿...")
    content = generator.generate_presentation(topic, presenter, date, "standard")
    file_path = generator.save_presentation(content, f"{date}_mock_stub_art.md")
    print(f"✅ 已生成：{file_path}")

    # 示例：生成案例研究
    topic = "遗留代码测试改造实践"
    content = generator.generate_presentation(topic, "李四", date, "case_study")
    file_path = generator.save_presentation(content, f"{date}_legacy_code.md")
    print(f"✅ 已生成：{file_path}")

    # 示例：生成工作坊
    topic = "TDD实战：计算器开发"
    content = generator.generate_presentation(topic, "王五", date, "workshop")
    file_path = generator.save_presentation(content, f"{date}_calculator_workshop.md")
    print(f"✅ 已生成：{file_path}")

    # 生成会议议程
    agenda = generator.create_agenda_template(date)
    agenda_path = generator.save_presentation(agenda, f"{date}_agenda.md")
    print(f"✅ 已生成议程：{agenda_path}")

    print("\n🎉 生成完成！")
    print(f"📁 文件位置：{generator.templates_dir}")
    print("\n使用方法：")
    print("1. 编辑生成的Markdown文件")
    print("2. 使用支持Markdown的演示工具（如Marp、Slidev）")
    print("3. 或直接在GitHub中查看和分享")

if __name__ == "__main__":
    main()
