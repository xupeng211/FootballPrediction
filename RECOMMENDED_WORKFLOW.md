# 推荐的开发工作流程

## 1. 开发前准备
```bash
# 确保环境最新
make install
make env-check
```

## 2. 开发过程中
```bash
# 每10-15分钟运行一次
make test-quick
```

## 3. 提交前检查（必须）
```bash
# 运行完整检查
make prepush

# 如果有错误，修复后再提交
# 不要使用 --no-verify
```

## 4. 推送代码
```bash
# 只在所有检查通过后推送
git push origin main
```

## 5. 处理 CI 失败
- CI 失败时，立即修复而不是绕过
- 优先修复阻塞性的错误
- 逐步降低技术债务

## 6. 质量目标
- 每次提交不增加新的 lint 错误
- 测试覆盖率只增不减
- 优先修复核心模块问题