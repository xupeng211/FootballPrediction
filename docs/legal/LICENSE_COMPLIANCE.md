# 许可证合规文档

## 概述

本文档说明Football Prediction系统的开源许可证合规策略和实施指南。

## 许可证政策

### 允许的许可证

我们允许使用以下开源许可证：

#### 宽松许可证（Permissive）
- **MIT License** - 完全允许，商业友好
- **BSD License** (2-clause/3-clause) - 完全允许
- **Apache License 2.0** - 完全允许，包含专利保护
- **ISC License** - 完全允许，类似MIT的简化版
- **Python Software Foundation License (PSF)** - 完全允许
- **Unlicense** - 完全允许，公共领域
- **CC0 1.0** - 完全允许，公共领域

#### Copyleft许可证（需要特别注意）
- **GNU General Public License (GPL)** - ⚠️ 需要法律审核
- **GNU Lesser General Public License (LGPL)** - ⚠️ 需要法律审核
- **GNU Affero General Public License (AGPL)** - ❌ 原则上禁止
- **Mozilla Public License 2.0 (MPL 2.0)** - ⚠️ 需要法律审核
- **Eclipse Public License (EPL)** - ⚠️ 需要法律审核

### 禁止的许可证

- **Commercial License** - 严格禁止
- **Proprietary License** - 严格禁止
- **Shareware** - 严格禁止
- **Freeware with Restrictions** - 需要审核

## 合规要求

### 1. 许可证识别

所有依赖必须明确标识其许可证：

```bash
# 检查所有依赖的许可证
pip-licenses --from=mixed --format=table

# 生成JSON格式的详细报告
pip-licenses --from=mixed --format=json > licenses.json
```

### 2. 署名要求

使用以下许可证的包必须在NOTICE文件中署名：

- MIT License
- BSD License
- Apache License 2.0

NOTICE文件模板：
```
NOTICE

Football Prediction System

本软件使用了以下开源软件包：

Package Name v1.0.0
Copyright (c) 2024 Author Name
License: MIT
Source: https://github.com/author/package

...
```

### 3. 源代码可用性

使用Copyleft许可证的包必须确保：

- 任何修改后的源代码必须可用
- 提供获取源代码的方式
- 在分发时包含许可证文本

## 实施流程

### 自动化检查

我们使用自动化工具确保许可证合规：

1. **每日扫描** - GitHub Actions自动检查
2. **PR检查** - 每次提交都进行许可证验证
3. **月度审计** - 人工审查许可证报告

### 添加新依赖

在添加新依赖时，必须：

1. 检查许可证兼容性
2. 更新依赖文档
3. 如果需要，更新NOTICE文件
4. 运行合规检查

```bash
# 添加新依赖后的检查流程
pip install new-package
make license-check  # 检查许可证合规
make update-deps    # 更新依赖文档
```

### 处理不合规的依赖

发现不合规的依赖时：

1. **立即评估** - 评估风险和影响
2. **寻找替代** - 查找兼容的替代方案
3. **申请例外** - 如无替代方案，申请法律例外
4. **记录决策** - 记录决策过程和理由

## 特殊情况处理

### GPL许可证

GPL许可证由于其对派生作品的要求，需要特别处理：

- **评估使用方式**：动态链接还是静态链接
- **考虑分发方式**：是否分发二进制文件
- **咨询法律意见**：必要时寻求专业法律意见

### 双重许可证

某些包提供双重许可证（如GPL或商业许可）：

- **选择兼容的许可证**：通常选择商业许可
- **记录选择**：明确记录选择的许可证
- **保存证明**：保留许可证选择的相关文件

### 许可证变更

上游许可证可能变更：

- **监控变更**：订阅上游更新通知
- **评估影响**：评估新许可证的影响
- **及时响应**：必要时更换依赖或调整使用方式

## 工具和资源

### 许可证检查工具

- `pip-licenses` - Python包许可证检查工具
- `FOSSA` - 商业许可证合规工具
- `Black Duck` - 商业开源安全与合规工具
- `Snyk` - 开源安全与许可证检查

### 许可证数据库

- [SPDX License List](https://spdx.org/licenses/)
- [Open Source Initiative](https://opensource.org/licenses/)
- [ChooseALicense](https://choosealicense.com/)

### 文档模板

- NOTICE文件模板位于项目根目录
- 许可证文本存储在 `docs/legal/licenses/`
- 依赖列表生成在 `docs/operations/DEPENDENCIES.md`

## 审计和报告

### 月度审计

每月生成许可证合规报告：

1. 依赖清单更新
2. 许可证变更跟踪
3. 合规问题识别
4. 改进建议

### 季度审查

季度进行全面审查：

1. 许可证政策评估
2. 新依赖风险评估
3. 合规流程优化
4. 团队培训更新

### 年度报告

年度总结报告包括：

1. 全年许可证合规状况
2. 重大合规事件
3. 政策更新建议
4. 下年度计划

## 培训和意识

### 开发团队培训

- 许可证基础知识
- 合规要求说明
- 工具使用培训
- 案例研究讨论

### 最佳实践

1. **早期识别** - 在选择依赖时检查许可证
2. **文档记录** - 保持准确的许可证记录
3. **定期审查** - 定期检查许可证变更
4. **寻求帮助** - 不确定时寻求法律意见

## 联系信息

- **合规负责人**: compliance@football-prediction.com
- **法务部门**: legal@football-prediction.com
- **技术支持**: tech@football-prediction.com

## 附录

### A. 常见许可证对比

| 许可证 | 商业使用 | 分发 | 修改 | 专利保护 | 源码披露 |
|--------|----------|------|------|----------|----------|
| MIT | ✅ | ✅ | ✅ | ❌ | ❌ |
| Apache 2.0 | ✅ | ✅ | ✅ | ✅ | ❌ |
| GPL v3 | ✅ | ✅ | ✅ | ✅ | ✅ |
| BSD | ✅ | ✅ | ✅ | ❌ | ❌ |
| LGPL | ✅ | ✅ | ✅ | ✅ | 部分 |

### B. 许可证兼容性矩阵

详见 `docs/legal/LICENSE_COMPATIBILITY_MATRIX.md`

### C. 紧急响应流程

详见 `docs/legal/LICENSE_EMERGENCY_RESPONSE.md`

---

最后更新: 2025-01-02
版本: 1.0.0
审核人: 合规团队