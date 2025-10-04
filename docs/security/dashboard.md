# 安全监控面板

## 每周检查清单

- [ ] 运行 `./scripts/security-check.sh`
- [ ] 检查依赖漏洞
- [ ] 检查代码安全问题
- [ ] 验证敏感文件保护
- [ ] 检查日志文件大小

## 安全指标

### 依赖漏洞数
- 严重: 0
- 高危: 0
- 中危: 0
- 低危: 0

### 代码安全问题
- 严重: 0
- 高危: 1 (MD5哈希 - 已标记为非安全用途)
- 中危: 5 (SQL注入 - 已部分修复)
- 低危: 31 (主要是try-except-pass模式)

### 文件权限
- .env.production: 600 ✓
- 其他配置文件: 644 ✓

## 快速命令

```bash
# 运行完整安全检查
./scripts/security-check.sh

# 只检查依赖漏洞
pip-audit -r requirements.txt

# 只检查代码安全
bandit -r src/ -f txt

# 检查敏感文件
find . -name "*.env*" -not -path "./.git/*"

# 检查大文件
find . -type f -size +10M
```

## 最近的安全活动

{{ 在这里记录安全检查结果 }}

---

最后更新: 2025-10-04
