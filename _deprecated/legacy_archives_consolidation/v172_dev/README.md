# V172 开发归档

本目录包含 V172 开发过程中产生的临时测试脚本和调试文件。

## 归档时间
2026-02-27

## 归档内容

### scripts_ops/
开发阶段的测试脚本，用于验证功能：
- `test_debug_api.js` - API 调试
- `test_direct_api.js` - 直接 API 测试
- `test_final.js` - 最终测试
- `test_final_xg.js` - xG 提取测试
- `test_historical_match.js` - 历史比赛测试
- `test_identity.js` - 身份验证测试
- `test_l2_engine.js` - L2 引擎测试
- `test_schema_validation.js` - Schema 验证
- `test_session_mirror.js` - 会话镜像测试
- `test_simple_xg.js` - 简单 xG 测试
- `test_stealth_v2.js` - Stealth 2.0 测试
- `test_xg_final.js` - xG 最终测试

## 注意事项

这些文件已从生产环境移除，仅作历史记录保留。
如需恢复某个脚本，请将其复制回 `scripts/ops/` 目录。
