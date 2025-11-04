#!/usr/bin/env python3
"""
GitHub Issues 批量创建脚本 (单标签版本)
Create GitHub Issues for optimization tasks (single label version)

使用方法:
python3 create_issues_single_label.py
"""

import subprocess
import json
import sys

class GitHubIssueCreator:
    """GitHub Issue 创建器"""

    def __init__(self):
        # 自动检测仓库信息
        try:
            result = subprocess.run([
                "gh", "repo", "view", "--json", "name,owner"
            ], capture_output=True, text=True, check=True)
            repo_data = json.loads(result.stdout)
            self.repo_owner = repo_data["owner"]["login"]
            self.repo_name = repo_data["name"]
            print(f"✅ 仓库信息: {self.repo_owner}/{self.repo_name}")
        except (subprocess.CalledProcessError, KeyError, json.JSONDecodeError):
            print("❌ 无法获取仓库信息，请确保已安装并认证GitHub CLI")
            print("安装GitHub CLI: https://cli.github.com/")
            print("认证GitHub CLI: gh auth login")
            sys.exit(1)

    def create_issue(self, title: str, body: str, labels: list):
        """创建单个Issue - 使用主要的optimization标签"""
        # 只使用optimization主标签
        main_label = "optimization"

        cmd = [
            "gh", "issue", "create",
            "--title", title,
            "--body", body,
            "--label", main_label
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            # 提取Issue URL
            issue_url = result.stdout.strip()
            print(f"✅ Issue创建成功: {title}")
            print(f"   🔗 {issue_url}")

            # 为已创建的Issue添加其他标签
            issue_number = self._extract_issue_number(issue_url)
            if issue_number:
                self._add_additional_labels(issue_number, labels)

            return issue_url
        except subprocess.CalledProcessError as e:
            print(f"❌ Issue创建失败: {title}")
            print(f"   错误信息: {e.stderr}")
            return None

    def _extract_issue_number(self, issue_url: str) -> int:
        """从Issue URL中提取Issue编号"""
        try:
            # URL格式: https://github.com/owner/repo/issues/123
            return int(issue_url.split('/')[-1])
        except (ValueError, IndexError):
            return None

    def _add_additional_labels(self, issue_number: int, labels: list):
        """为Issue添加额外的标签"""
        for label in labels:
            if label == "optimization":
                continue  # 主标签已添加

            try:
                subprocess.run([
                    "gh", "issue", "edit", str(issue_number),
                    "--add-label", label
                ], capture_output=True, check=True)
                print(f"   ✓ 已添加标签: {label}")
            except subprocess.CalledProcessError:
                print(f"   ⚠️ 标签添加失败: {label}")

    def create_all_optimization_issues(self):
        """创建所有优化Issues"""
        issues = [
            {
                "title": "[OPT] 修复所有代码质量问题",
                "labels": ["optimization", "code-quality", "week1", "high-priority"],
                "body": self._generate_code_quality_issue_body()
            },
            {
                "title": "[OPT] 提升用户管理模块测试覆盖率至30%",
                "labels": ["optimization", "testing", "coverage", "week1", "high-priority"],
                "body": self._generate_test_coverage_issue_body()
            },
            {
                "title": "[OPT] 修复安全漏洞并更新依赖",
                "labels": ["optimization", "security", "dependencies", "week1", "medium-priority"],
                "body": self._generate_security_issue_body()
            },
            {
                "title": "[OPT] 数据库查询性能优化50%",
                "labels": ["optimization", "performance", "database", "week2", "high-priority"],
                "body": self._generate_database_issue_body()
            },
            {
                "title": "[OPT] 实现Redis缓存系统",
                "labels": ["optimization", "performance", "caching", "week2", "medium-priority"],
                "body": self._generate_cache_issue_body()
            },
            {
                "title": "[OPT] 实现Docker容器化部署",
                "labels": ["optimization", "deployment", "docker", "week3", "high-priority"],
                "body": self._generate_docker_issue_body()
            },
            {
                "title": "[OPT] 实现CI/CD自动化流水线",
                "labels": ["optimization", "ci-cd", "automation", "week3", "medium-priority"],
                "body": self._generate_cicd_issue_body()
            }
        ]

        print("🚀 开始创建优化Issues...")
        print(f"📋 总计需要创建 {len(issues)} 个Issues\n")

        created_issues = []
        failed_issues = []

        for i, issue in enumerate(issues, 1):
            print(f"[{i}/{len(issues)}] 正在创建: {issue['title']}")

            result = self.create_issue(
                title=issue["title"],
                body=issue["body"],
                labels=issue["labels"]
            )

            if result:
                created_issues.append({
                    "title": issue["title"],
                    "url": result
                })
            else:
                failed_issues.append(issue["title"])

        print(f"\n🎊 Issues创建完成!")
        print(f"✅ 成功创建: {len(created_issues)}/{len(issues)} 个Issues")
        print(f"❌ 创建失败: {len(failed_issues)} 个Issues")

        if failed_issues:
            print("\n❌ 创建失败的Issues:")
            for issue in failed_issues:
                print(f"   - {issue}")

        if created_issues:
            print(f"\n📋 成功创建的Issues:")
            for issue in created_issues:
                print(f"   ✅ {issue['title']}")
                print(f"      {issue['url']}")

        return created_issues, failed_issues

    def _generate_code_quality_issue_body(self):
        """生成代码质量Issue内容"""
        return """## 🎯 任务目标
修复所有代码质量问题，确保代码质量检查100%通过

## 📋 具体任务
- [ ] 修复Ruff检查发现的15个质量问题
- [ ] 清理6个语法错误文件
- [ ] 移除未使用的导入
- [ ] 确保代码格式100%符合规范

## 🔧 使用工具
```bash
# 必备命令
make fix-code          # 自动修复
ruff check src/ --fix  # 手动修复
black src/ tests/      # 格式化
```

## ✅ 验收标准
- [ ] ruff检查 0 issues
- [ ] black检查 100%通过
- [ ] 清理6个语法错误文件
- [ ] 移除未使用的导入

## 📋 执行步骤
1. 运行 `make fix-code`
2. 手动修复异常处理问题 (14个)
3. 清理无用文件
4. 验证修复结果
5. 提交代码

## 🕐 预估时间
**估时**: 1天

## 📊 参考资源
- [优化路线图](project-optimization-roadmap.md)
- [执行计划](optimization-execution-plan.md)
- [质量策略](quality-improvement-strategy.md)

## 💡 实现提示
常见问题修复模式：
1. 异常处理链: `raise HTTPException(detail=str(e)) from e`
2. 未使用导入: 删除或注释
3. 类型注解: 添加缺失的类型注解

## 🆘 获取帮助
- 查看项目文档: `cat CLAUDE.md`
- 运行帮助命令: `make help`
- 查看质量报告: `python3 scripts/generate_quality_report.py`"""

    def _generate_test_coverage_issue_body(self):
        """生成测试覆盖率Issue内容"""
        return """## 🎯 任务目标
提升用户管理模块测试覆盖率从当前水平到30%+

## 📋 具体任务
- [ ] 分析当前测试覆盖率
- [ ] 识别未覆盖的代码路径
- [ ] 编写缺失的测试用例
- [ ] 优化现有测试用例
- [ ] 确保边界条件测试覆盖

## 🔧 使用工具
```bash
# 测试工具
pytest tests/unit/services/test_user_management_service.py --cov=src/services/user_management_service
python3 scripts/coverage_optimizer.py
make coverage
```

## ✅ 验收标准
- [ ] 用户管理服务覆盖率 ≥ 30%
- [ ] 所有测试用例通过
- [ ] 边界条件测试覆盖
- [ ] 异常处理测试覆盖

## 📋 执行步骤
1. 运行覆盖率分析
2. 识别未覆盖代码
3. 编写缺失的测试用例
4. 运行测试验证
5. 生成覆盖率报告

## 🕐 预估时间
**估时**: 2天

## 📊 参考资源
- [测试覆盖策略](quality-improvement-strategy.md#测试覆盖率)
- [覆盖率优化器](scripts/coverage_optimizer.py)
- [测试最佳实践](CLAUDE.md#测试规范)

## 💡 实现提示
测试用例类型：
1. 功能测试: 正常业务流程
2. 边界测试: 极值情况处理
3. 异常测试: 错误场景处理
4. 性能测试: 响应时间验证"""

    def _generate_security_issue_body(self):
        """生成安全Issue内容"""
        return """## 🎯 任务目标
修复所有安全漏洞并更新依赖包到最新稳定版本

## 📋 具体任务
- [ ] 运行安全审计扫描
- [ ] 修复发现的安全漏洞
- [ ] 更新过期的依赖包
- [ ] 添加安全扫描到CI流程
- [ ] 实施安全编码规范

## 🔧 使用工具
```bash
# 安全工具
pip-audit                    # 检查漏洞
bandit -r src/               # 静态安全分析
safety check                 # 依赖安全检查
```

## ✅ 验收标准
- [ ] pip-audit 0 vulnerabilities
- [ ] bandit扫描 0 high severity issues
- [ ] 所有依赖更新到最新稳定版
- [ ] 安全扫描集成到CI

## 📋 执行步骤
1. 运行安全审计
2. 修复发现的漏洞
3. 更新依赖包
4. 验证修复效果
5. 更新CI配置

## 🕐 预估时间
**估时**: 1天

## 📊 参考资源
- [安全最佳实践](quality-improvement-strategy.md#安全策略)
- [安全工具文档](https://bandit.readthedocs.io/)
- [依赖安全检查](https://pyup.io/safety/)

## 💡 实现提示
常见安全问题：
1. SQL注入: 使用参数化查询
2. XSS攻击: 输入验证和输出编码
3. 硬编码密钥: 使用环境变量
4. 弱密码策略: 实施密码强度要求"""

    def _generate_database_issue_body(self):
        """生成数据库优化Issue内容"""
        return """## 🎯 任务目标
优化数据库查询性能，目标提升50%查询效率

## 📋 具体任务
- [ ] 分析慢查询日志
- [ ] 优化用户相关数据库查询
- [ ] 添加必要的数据库索引
- [ ] 实现查询结果缓存
- [ ] 性能基准测试

## 🔧 使用工具
```sql
-- 数据库分析工具
EXPLAIN ANALYZE SELECT * FROM users WHERE email = 'test@example.com';
EXPLAIN ANALYZE SELECT * FROM users WHERE is_active = true;

-- 索引创建
CREATE INDEX CONCURRENTLY idx_users_email ON users(email);
CREATE INDEX CONCURRENTLY idx_users_active ON users(is_active);
CREATE INDEX CONCURRENTLY idx_users_username ON users(username);
```

## ✅ 验收标准
- [ ] 用户查询响应时间 < 100ms
- [ ] 数据库索引优化完成
- [ ] 查询缓存命中率 > 80%
- [ ] 性能基准测试通过

## 📋 执行步骤
1. 分析慢查询
2. 创建优化索引
3. 实现缓存层
4. 性能测试验证
5. 监控部署效果

## 🕐 预估时间
**估时**: 3天

## 📊 参考资源
- [性能优化策略](quality-improvement-strategy.md#性能优化)
- [PostgreSQL性能指南](https://wiki.postgresql.org/wiki/Performance_Optimization)
- [索引最佳实践](https://www.postgresql.org/docs/current/indexes-best-practices.html)

## 💡 实现提示
优化技巧：
1. 索引策略: 为WHERE、JOIN、ORDER BY字段创建索引
2. 查询优化: 避免SELECT *，使用具体字段
3. 连接池: 配置合适的连接池大小
4. 分页优化: 使用LIMIT/OFFSET或游标分页"""

    def _generate_cache_issue_body(self):
        """生成缓存Issue内容"""
        return """## 🎯 任务目标
实现Redis缓存系统，提升系统整体性能

## 📋 具体任务
- [ ] 设计缓存架构
- [ ] 实现用户信息缓存
- [ ] 实现API响应缓存
- [ ] 添加缓存失效策略
- [ ] 缓存性能测试

## 🔧 使用工具
```python
# 缓存实现示例
from redis import Redis
import json
from typing import Optional

class UserCache:
    def __init__(self, redis_client: Redis):
        self.redis = redis_client
        self.ttl = 3600  # 1小时

    async def get_user(self, user_id: int) -> Optional[dict]:
        cached = await self.redis.get(f"user:{user_id}")
        return json.loads(cached) if cached else None

    async def set_user(self, user_id: int, user_data: dict):
        await self.redis.setex(
            f"user:{user_id}",
            self.ttl,
            json.dumps(user_data, default=str)
        )
```

## ✅ 验收标准
- [ ] Redis缓存系统正常运行
- [ ] 用户信息缓存命中率 > 80%
- [ ] 缓存失效策略正常工作
- [ ] 缓存性能测试通过

## 📋 执行步骤
1. 设计缓存架构
2. 实现缓存服务
3. 集成到现有代码
4. 测试缓存功能
5. 监控缓存效果

## 🕐 预估时间
**估时**: 2天

## 📊 参考资源
- [Redis最佳实践](https://redis.io/documentation/)
- [缓存策略设计](https://docs.djangoproject.com/en/4.0/topics/cache/)
- [Python Redis库](https://redis-py.readthedocs.io/)

## 💡 实现提示
缓存策略：
1. 缓存键设计: 使用清晰的命名规范
2. TTL设置: 根据数据更新频率设置过期时间
3. 缓存预热: 系统启动时预加载热点数据
4. 缓存雪崩: 设置随机过期时间避免集中过期"""

    def _generate_docker_issue_body(self):
        """生成Docker Issue内容"""
        return """## 🎯 任务目标
实现生产级Docker容器化部署方案

## 📋 具体任务
- [ ] 创建多阶段Dockerfile
- [ ] 配置docker-compose.yml
- [ ] 实现健康检查机制
- [ ] 优化镜像大小和启动时间
- [ ] 配置生产环境变量

## 🔧 使用工具
```dockerfile
# Dockerfile.prod
FROM python:3.11-slim as builder
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

FROM python:3.11-slim as runtime
WORKDIR /app
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY src/ ./src/
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \\
    CMD curl -f http://localhost:8000/health || exit 1
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

## ✅ 验收标准
- [ ] Docker镜像构建成功
- [ ] 容器启动正常
- [ ] 健康检查通过
- [ ] 资源使用合理

## 📋 执行步骤
1. 创建多阶段Dockerfile
2. 配置docker-compose
3. 实现健康检查
4. 测试容器部署
5. 优化镜像大小

## 🕐 预估时间
**估时**: 3天

## 📊 参考资源
- [Docker最佳实践](https://docs.docker.com/develop/dev-best-practices/)
- [多阶段构建](https://docs.docker.com/build/building/multi-stage/)
- [健康检查](https://docs.docker.com/engine/reference/builder/#healthcheck)

## 💡 实现提示
优化技巧：
1. 镜像大小: 使用多阶段构建，删除不必要文件
2. 安全性: 使用非root用户运行
3. 性能: 优化层缓存，减少重复构建
4. 监控: 添加日志收集和健康检查"""

    def _generate_cicd_issue_body(self):
        """生成CI/CD Issue内容"""
        return """## 🎯 任务目标
实现完整的CI/CD自动化流水线

## 📋 具体任务
- [ ] 配置GitHub Actions工作流
- [ ] 实现自动化测试和部署
- [ ] 添加质量门禁
- [ ] 配置通知和报告
- [ ] 设置环境管理

## 🔧 使用工具
```yaml
# .github/workflows/ci.yml
name: CI/CD Pipeline
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: Run tests
        run: make test.unit

      - name: Check quality
        run: make check-quality

      - name: Upload coverage
        uses: codecov/codecov-action@v3

  deploy:
    needs: test
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    steps:
      - name: Deploy
        run: echo "Deploy to production"
```

## ✅ 验收标准
- [ ] CI流水线正常运行
- [ ] 自动化测试100%通过
- [ ] 质量门禁正常工作
- [ ] 自动部署功能正常

## 📋 执行步骤
1. 配置GitHub Actions
2. 设置测试环境
3. 配置质量检查
4. 设置部署环境
5. 测试完整流水线

## 🕐 预估时间
**估时**: 2天

## 📊 参考资源
- [GitHub Actions文档](https://docs.github.com/en/actions)
- [CI/CD最佳实践](https://docs.github.com/en/actions/guides)
- [工作流语法](https://docs.github.com/en/actions/using-workflows/workflow-syntax-for-github-actions)

## 💡 实现提示
流水线设计：
1. 并行执行: 独立任务并行运行提升效率
2. 缓存策略: 缓存依赖减少构建时间
3. 环境隔离: 不同环境使用不同配置
4. 失败处理: 配置通知和回滚机制"""

def main():
    """主函数"""
    print("🚀 GitHub Issues 创建工具 (单标签版本)")
    print("="*50)

    creator = GitHubIssueCreator()

    print("📋 即将创建以下优化Issues:")
    for i, issue in enumerate([
        "[OPT] 修复所有代码质量问题",
        "[OPT] 提升用户管理模块测试覆盖率至30%",
        "[OPT] 修复安全漏洞并更新依赖",
        "[OPT] 数据库查询性能优化50%",
        "[OPT] 实现Redis缓存系统",
        "[OPT] 实现Docker容器化部署",
        "[OPT] 实现CI/CD自动化流水线"
    ], 1):
        print(f"{i}. {issue}")
    print()

    # 创建Issues
    created_issues, failed_issues = creator.create_all_optimization_issues()

    if created_issues:
        print(f"\n🎊 成功创建 {len(created_issues)} 个Issues!")
        print("📋 你可以在GitHub仓库中查看这些Issues")
        print(f"🔗 使用 'gh issue list --label optimization' 查看所有优化Issues")
        print(f"🌐 仓库地址: https://github.com/{creator.repo_owner}/{creator.repo_name}/issues")

        # 生成Issue摘要
        print("\n📊 Issues摘要:")
        for issue in created_issues:
            print(f"   ✅ {issue['title']}")
            print(f"      {issue['url']}")

    if failed_issues:
        print(f"\n⚠️  {len(failed_issues)} 个Issues创建失败")
        print("请检查GitHub CLI权限和网络连接")

if __name__ == "__main__":
    main()