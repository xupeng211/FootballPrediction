# 🔄 GitHub Actions 文档CI/CD指南

## 🎯 概述

本项目配置了完整的GitHub Actions文档CI/CD流水线，实现文档的自动化构建、测试和部署。

## 📋 工作流概览

### 主要工作流

1. **📚 Documentation CI/CD** - 主要文档CI/CD流水线
2. **📚 Documentation Preview** - PR预览和评论

### 触发条件

#### 自动触发
- **推送到分支**: `main`, `develop`, `docs/**`
- **Pull Request**: 针对 `main`, `develop` 分支
- **文档变更**: `docs/**`, `mkdocs.yml`

#### 手动触发
- **工作流触发**: 可选择部署环境和参数

## 🔄 工作流详解

### 📚 Documentation CI/CD 流水线

#### 阶段 1: 文档检查 (docs-check)
```yaml
目的: 验证文档健康状态
- 检查文档目录结构
- 验证MkDocs配置
- 检查文档链接
- 生成文档统计
```

**检查项目**:
- docs/ 目录存在性
- mkdocs.yml 配置正确性
- Markdown文件统计
- 链接有效性

#### 阶段 2: 构建文档 (docs-build)
```yaml
目的: 构建静态文档站点
- 清理之前的构建
- 执行MkDocs构建
- 验证构建结果
- 上传构建产物
```

**输出**:
- HTML页面数量统计
- 站点大小信息
- 构建报告JSON

#### 阶段 3: 部署到GitHub Pages (docs-deploy)
```yaml
目的: 自动部署到GitHub Pages
- 配置GitHub Pages
- 部署静态文件
- 提供访问URL
```

**部署条件**:
- main分支（自动部署）
- develop分支（自动部署）
- 手动触发（可选部署）

#### 阶段 4: 质量检查 (docs-quality)
```yaml
目的: 文档质量分析
- 页面大小检查
- 资源文件统计
- 生成质量报告
```

#### 阶段 5: 通知 (docs-notify)
```yaml
目的: 部署状态通知
- 成功部署通知
- 失败状态警报
```

### 📚 Documentation Preview 流水线

#### 构建预览 (preview)
```yaml
目的: 为PR构建预览站点
- 构建文档
- 添加预览标识
- 上传预览文件
```

#### PR评论 (pr-comment)
```yaml
目的: 在PR中添加预览链接
- 查找现有评论
- 创建或更新预览链接
```

#### 质量检查 (quality-check)
```yaml
目的: 预览质量验证
- HTML有效性检查
- 关键页面验证
- 资源文件统计
```

#### 状态检查 (status)
```yaml
目的: 综合状态报告
- 检查各阶段状态
- 生成状态报告
```

## 🛠️ 本地开发工具

### Makefile命令

#### 基础命令
```bash
# 本地CI检查（模拟GitHub Actions）
make docs-ci-local

# 测试文档链接
make docs-test-links

# 部署前测试
make docs-deploy-dry

# 查看部署状态
make docs-status
```

#### 管理命令
```bash
# 清理所有文档产物
make docs-clean-all

# 查看版本信息
make docs-version

# MkDocs基础命令
make docs-install
make docs-serve
make docs-build
make docs-deploy
```

### 本地测试流程

#### 1. 本地CI模拟
```bash
# 运行完整的本地CI检查
make docs-ci-local
```

**预期输出**:
```
📋 1. Checking documentation structure...
✅ Structure check passed
🔧 2. Validating MkDocs configuration...
✅ Configuration valid
🔨 3. Building documentation...
✅ Build successful
📊 4. Generating report...
📄 Generated 25 HTML pages
📦 Site size: 2.5M
✅ Local CI checks completed successfully
```

#### 2. 链接测试
```bash
# 测试所有文档链接
make docs-test-links
```

#### 3. 部署测试
```bash
# 部署前测试
make docs-deploy-dry

# 检查状态
make docs-status
```

## 🔧 配置文件

### GitHub Actions配置

#### 主要配置文件
- `.github/workflows/docs.yml` - 主CI/CD流水线
- `.github/workflows/docs-preview.yml` - PR预览流水线
- `.mlc_config.json` - 链接检查配置

#### 配置特点
- **并发控制**: 避免重复运行
- **超时设置**: 防止无限等待
- **权限控制**: 最小权限原则
- **错误处理**: 完善的失败处理

### MkDocs配置

#### 构建配置
```yaml
# mkdocs.yml
site_name: 足球预测系统文档
theme:
  name: material
  language: zh
plugins:
  - search:
      lang:
        - zh
        - en
```

## 📊 监控和报告

### 构建报告

#### 自动生成报告
- `docs-stats.json` - 文档统计信息
- `build-report.json` - 构建报告
- `quality-report.json` - 质量分析报告

#### 报告内容
```json
{
  "timestamp": "2025-10-23T15:00:00Z",
  "total_files": 25,
  "total_lines": 5000,
  "directories": 10,
  "git_commit": "abc123",
  "git_branch": "main"
}
```

### 质量指标

#### 构建指标
- **HTML页面数量**: 生成的HTML文件总数
- **站点大小**: 站点占用的磁盘空间
- **构建时间**: 完整构建的耗时
- **成功率**: 构建成功的百分比

#### 质量指标
- **大型页面**: 超过50KB的HTML页面数量
- **图片优化**: 图片文件数量和大小
- **链接有效性**: 无效链接的统计

## 🚀 部署流程

### 自动部署

#### 触发条件
- **main分支推送**: 自动部署到生产环境
- **develop分支推送**: 自动部署到预发布环境
- **手动触发**: 可选择环境和参数

#### 部署步骤
1. **代码检出**: 获取最新代码
2. **环境准备**: 设置Python和依赖
3. **文档构建**: 生成静态站点
4. **GitHub Pages配置**: 设置部署环境
5. **文件部署**: 推送到GitHub Pages
6. **访问验证**: 确认部署成功

### 手动部署

#### 本地部署
```bash
# 1. 构建文档
make docs-build

# 2. 本地预览
make docs-serve

# 3. 手动部署
mkdocs gh-deploy --force
```

#### 部署验证
```bash
# 检查部署状态
make docs-status

# 访问站点
open https://username.github.io/repository/
```

## 🔍 故障排除

### 常见问题

#### 1. 构建失败
```bash
# 检查配置文件
python -c "import yaml; yaml.safe_load(open('mkdocs.yml'))"

# 查看详细错误
mkdocs build --verbose
```

#### 2. 部署失败
```bash
# 检查权限
gh auth status

# 检查仓库设置
gh repo view --json | jq '.pages'

# 手动部署测试
mkdocs gh-deploy --dry-run --force
```

#### 3. 链接检查失败
```bash
# 跳过特定链接
echo "skip_patterns:" >> .mlc_config.json
echo "- 'http://localhost'" >> .mlc_config.json

# 重新检查
make docs-test-links
```

### 调试技巧

#### 本地调试
```bash
# 启用详细日志
mkdocs build --verbose

# 严格模式构建
mkdocs build --strict

# 检查特定文件
mkdocs build --clean --quiet
```

#### GitHub Actions调试
```yaml
# 添加调试步骤
- name: Debug
  run: |
    echo "Current directory: $(pwd)"
    echo "Files in docs:"
    ls -la docs/
    echo "MkDocs version:"
    mkdocs --version
```

## 📈 最佳实践

### 文档管理

#### 版本控制
- 文档变更自动触发构建
- PR自动生成预览
- 版本标签自动部署

#### 质量保证
- 自动化链接检查
- 构建前验证
- 质量报告生成

### 性能优化

#### 构建优化
- 缓存依赖安装
- 并行化构建步骤
- 优化构建时间

#### 站点优化
- 压缩静态资源
- 启用CDN加速
- 优化加载性能

## 🔗 相关资源

### 文档链接
- **MkDocs官方文档**: https://www.mkdocs.org/
- **Material主题文档**: https://squidfunk.github.io/mkdocs-material/
- **GitHub Actions文档**: https://docs.github.com/en/actions

### 配置参考
- **工作流配置**: `.github/workflows/docs.yml`
- **MkDocs配置**: `mkdocs.yml`
- **链接检查配置**: `.mlc_config.json`

### 工具文档
- **Makefile工具**: 参考 `docs/MKDOCS_README.md`
- **GitHub Actions**: 参考 GitHub官方文档

---

**最后更新**: 2025-10-23
**文档版本**: v1.0
**维护者**: 开发团队